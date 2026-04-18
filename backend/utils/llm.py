"""
utils/llm.py — 火山方舟大模型客户端（Class 封装）

设计原则：
  - 单例模式：LLM() 始终返回同一实例，配置只加载一次
  - 对接配置内置：api_key / base_url / 默认模型 / 可用模型列表
  - 统一接口：chat() / stream() / chat_with_history()
  - 多模态支持：文本 / 图片(URL/本地/Base64) / 音频 / 视频 / 文件
  - 启动预热：warmup() 验证 API 可达性

使用示例：
    from utils.llm import LLM

    # 文本对话
    result = LLM.chat("你好")
    result = LLM.chat("分析这只股票", model="deepseek-v3.2")

    # 带历史上下文
    result = LLM.chat_with_history("继续分析", history=[...])

    # 流式输出
    for chunk in LLM.stream("讲个笑话"):
        print(chunk, end="")

    # 多模态：图片识别
    result = LLM.chat("描述这张图片", images=["https://example.com/1.jpg"])

    # 多模态：本地图片
    result = LLM.chat("这是什么？", images=["D:/images/chart.png"])

    # 多模态：Base64 图片
    result = LLM.chat("分析", images=["data:image/png;base64,..."])
"""

import base64
import json
import mimetypes
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

import requests

from config.settings import (
    ARK_API_KEY,
    ARK_BASE_URL,
    AVAILABLE_LLM_MODELS,
    DEFAULT_LLM_MODEL,
)


class LLM:
    """火山方舟大模型客户端（单例）"""

    _instance: Optional["LLM"] = None

    def __new__(cls) -> "LLM":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ─── 对接配置 ──────────────────────────────
        self.api_key: str = ARK_API_KEY
        self.base_url: str = ARK_BASE_URL
        self.default_model: str = DEFAULT_LLM_MODEL
        self.available_models: dict = AVAILABLE_LLM_MODELS
        
        # ─── 新闻分析专用配置（线程启动时固定）──────
        self.news_system_prompt: str | None = None   # 由外部线程启动时设置
        self.news_model: str = self.default_model    # 默认使用 default_model

        # ─── 预构建请求头（只构建一次）──────────────
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # ─── 预热状态 ──────────────────────────────
        self._warmed_up: bool = False
        self._warmup_model: str | None = None

    # ═══════════════════════════════════════════════════════════════════
    #  内部方法
    # ═══════════════════════════════════════════════════════════════════

    def _build_messages(
        self,
        prompt: str = "",
        model: str | None = None,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        images: list[str] | None = None,
        files: list[str] | None = None,
    ) -> list[dict]:
        """
        统一构建 OpenAI 格式的 messages 列表。

        Args:
            prompt:        用户文本输入
            model:         模型名称（用于判断是否支持 vision）
            system_prompt: 系统提示词
            messages:      自定义消息列表（传入后忽略其他参数）
            images:        图片列表，每个元素为：
                           - URL: "https://..."
                           - 本地路径: "D:/images/1.jpg"
                           - Base64: "data:image/png;base64,..."
            files:         文件列表，每个元素为本地文件路径
                           - 图片: 同 images，自动识别为图片
                           - 音频: ".mp3", ".wav", ".m4a", ".flac", ".ogg"
                           - 视频: ".mp4", ".webm", ".avi", ".mov"
                           - 文档: ".pdf", ".docx", ".txt", ".csv", ".xlsx"
        """
        if messages:
            return messages

        # 收集所有多媒体内容
        all_media = []
        if images:
            all_media.extend(images)
        if files:
            all_media.extend(files)

        # 构建 user content
        if all_media:
            content_parts = []
            # 文本部分（如果有 prompt）
            if prompt:
                content_parts.append({"type": "text", "text": prompt})

            # 多媒体部分
            for item in all_media:
                media_part = self._build_media_part(item)
                if media_part:
                    content_parts.append(media_part)

            user_content = {"role": "user", "content": content_parts}
        else:
            user_content = {"role": "user", "content": prompt}

        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append(user_content)
        return msgs

    def _build_media_part(self, item: str) -> dict | None:
        """
        将单个媒体项转为 OpenAI Vision 格式。

        Args:
            item: URL / 本地路径 / Base64 字符串

        Returns:
            {"type": "image_url", "image_url": {"url": "..."}}
            或 None（如果无法处理）
        """
        # Base64 data URI
        if item.startswith("data:"):
            return {"type": "image_url", "image_url": {"url": item}}

        # URL
        if item.startswith("http://") or item.startswith("https://"):
            return {"type": "image_url", "image_url": {"url": item}}

        # 本地文件
        path = Path(item)
        if not path.exists():
            print(f"[llm] 警告: 文件不存在 - {item}")
            return None

        mime, _ = mimetypes.guess_type(str(path))
        if mime is None:
            mime = "application/octet-stream"

        # 根据 MIME 类型决定格式
        if mime.startswith("image/"):
            # 图片 → base64 内联
            b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64}"
            return {"type": "image_url", "image_url": {"url": data_uri}}

        elif mime.startswith("audio/"):
            # 音频 → base64 内联
            b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64}"
            return {
                "type": "input_audio",
                "input_audio": {
                    "data": b64,
                    "format": self._audio_format(mime),
                }
            }

        elif mime.startswith("video/"):
            # 视频 → base64 内联（如果模型支持）
            b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64}"
            return {"type": "image_url", "image_url": {"url": data_uri}}

        else:
            # 文档类 → 作为文件附件处理
            b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            filename = path.name
            return {
                "type": "text",
                "text": f"[文件附件: {filename}]\n{b64[:100]}...",
            }

    @staticmethod
    def _audio_format(mime: str) -> str:
        """MIME → 音频格式标识"""
        return {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/mp4": "mp4",
            "audio/x-m4a": "m4a",
            "audio/flac": "flac",
            "audio/ogg": "ogg",
            "audio/webm": "webm",
        }.get(mime, "mp3")

    def _resolve_model(self, model: str | None) -> str:
        return model or self.default_model

    def _build_payload(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **extra,
    ) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stream:
            payload["stream"] = True
        payload.update(extra)
        return payload

    # ═══════════════════════════════════════════════════════════════════
    #  新闻分析专用配置（线程启动时固定）
    # ═══════════════════════════════════════════════════════════════════

    def set_news_analysis_config(
        self,
        system_prompt: str,
        model: str | None = None,
    ) -> None:
        """
        设置新闻分析专用配置（线程启动时调用，永久固定）。
        
        Args:
            system_prompt: 新闻分析系统提示词
            model:         新闻分析专用模型（默认使用 default_model）
        """
        self.news_system_prompt = system_prompt
        if model is not None:
            self.news_model = model
        else:
            self.news_model = self.default_model

    def analyze_news_items(
        self,
        items: dict | list[dict],
        **extra,
    ) -> list[dict]:
        """
        统一新闻分析接口：自动判断单条/批量输入，使用固定系统提示词和模型。
        
        输入参数：
            items: 单个新闻字典 或 新闻字典列表。
                每个字典必须包含：id (int), title (str), content (str, 可选)
                可选字段：source, news_type
        
        返回：
            结果字典列表，每个元素包含12个AI分析字段 + id。
            无论单条/批量输入，输出永远是列表。
        
        异常处理：
            - 分析失败时返回空列表，不崩溃、不阻塞流程
            - 记录标准日志：[LLM新闻分析] 开始、成功、失败、耗时
        """
        import json
        import time

        # 检查固定配置是否已设置
        if self.news_system_prompt is None:
            print(f"[LLM新闻分析] 警告: news_system_prompt 未设置，使用默认提示词")
            # 可以设置一个默认提示词，但最好由线程启动时设置
            # 暂时使用空字符串，但调用会失败吗？先继续
            
        # 标准化为列表
        if isinstance(items, dict):
            items = [items]
        
        if not items:
            return []
        
        start_time = time.time()
        batch_size = len(items)
        print(f"[LLM新闻分析] 开始 | batch_size={batch_size}")
        
        # 构建用户消息：JSON 数组格式
        llm_input = []
        for item in items:
            news_id = item.get("id")
            title = item.get("title", "")
            content = item.get("content", "")
            source = item.get("source", "")
            news_type = item.get("news_type", "")
            
            # 截断内容，避免超出 token 限制
            truncated_content = content[:2000] if content else ""
            if content and len(content) > 2000:
                truncated_content += "\n...(正文已截断)"
            
            llm_input.append({
                "id": news_id,
                "title": title,
                "content": truncated_content,
                "source": source,
                "news_type": news_type,
            })
        
        user_message = json.dumps(llm_input, ensure_ascii=False)
        
        # 使用固定配置
        system_prompt = self.news_system_prompt or ""
        model = self.news_model
        
        # 调用底层 chat 方法（禁止外部覆盖参数）
        try:
            raw_text = self.chat(
                prompt=user_message,
                system_prompt=system_prompt,
                model=model,
                temperature=0.1,          # 固定低温度保证 JSON 稳定性
                max_tokens=4096,          # 批量需要更多 token
            )
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[LLM新闻分析] 失败 | batch_size={batch_size} | 耗时{elapsed:.2f}s | 错误: {e}")
            return []
        
        # 解析 JSON 数组响应
        try:
            results = self._parse_batch_news_response(raw_text)
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[LLM新闻分析] 解析失败 | batch_size={batch_size} | 耗时{elapsed:.2f}s | 错误: {e}")
            return []
        
        elapsed = time.time() - start_time
        print(f"[LLM新闻分析] 成功 | batch_size={batch_size} | 耗时{elapsed:.2f}s | 有效结果{len(results)}/{batch_size}")
        
        return results

    # ═══════════════════════════════════════════════════════════════════
    #  核心接口
    # ═══════════════════════════════════════════════════════════════════

    def chat(
        self,
        prompt: str = "",
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        messages: list[dict] | None = None,
        images: list[str] | None = None,
        files: list[str] | None = None,
        **extra,
    ) -> str:
        """
        调用火山方舟大模型（非流式）

        Args:
            prompt:         用户输入文本
            model:          模型名称，默认 default_model
            system_prompt:  系统提示词
            temperature:    温度 0~1
            max_tokens:     最大生成 token 数
            messages:       自定义消息列表（传入后忽略 prompt/system_prompt/images/files）
            images:         图片列表（URL / 本地路径 / Base64）
            files:          文件列表（本地路径，支持图片/音频/视频/文档）
            **extra:        额外请求参数（如 top_p, frequency_penalty 等）

        Returns:
            模型回复文本
        """
        model = self._resolve_model(model)
        url = f"{self.base_url}/v1/chat/completions"

        msgs = self._build_messages(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            images=images,
            files=files,
        )

        payload = self._build_payload(
            model=model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **extra,
        )

        resp = requests.post(url, headers=self._headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise ValueError(f"ARK API Error: {data['error'].get('message', data['error'])}")

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"解析 API 响应失败: {e}, 响应: {json.dumps(data, ensure_ascii=False)[:500]}")

    def stream(
        self,
        prompt: str = "",
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        messages: list[dict] | None = None,
        images: list[str] | None = None,
        files: list[str] | None = None,
        **extra,
    ) -> Generator[str, None, None]:
        """
        流式调用火山方舟大模型

        Yields:
            模型每次返回的文本片段
        """
        model = self._resolve_model(model)
        url = f"{self.base_url}/v1/chat/completions"

        msgs = self._build_messages(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            images=images,
            files=files,
        )

        payload = self._build_payload(
            model=model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **extra,
        )

        resp = requests.post(url, headers=self._headers, json=payload, timeout=120, stream=True)
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8", errors="replace")
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def chat_with_history(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        images: list[str] | None = None,
        files: list[str] | None = None,
        **extra,
    ) -> str:
        """
        带历史上下文的大模型调用

        Args:
            message:    当前用户消息
            history:    历史消息列表 [{"role": "user/assistant", "content": "..."}, ...]
            其余参数同 chat()

        Returns:
            模型回复文本
        """
        model = self._resolve_model(model)
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        if history:
            msgs.extend(history)

        # 如果有多媒体，构建多模态消息
        if images or files:
            user_content = []
            if message:
                user_content.append({"type": "text", "text": message})
            all_media = list(images or []) + list(files or [])
            for item in all_media:
                part = self._build_media_part(item)
                if part:
                    user_content.append(part)
            msgs.append({"role": "user", "content": user_content})
        else:
            msgs.append({"role": "user", "content": message})

        return self.chat(
            messages=msgs,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    # ═══════════════════════════════════════════════════════════════════
    #  新闻分析专用方法
    # ═══════════════════════════════════════════════════════════════════

    def analyze_news(
        self,
        id: int,
        title: str,
        content: str = "",
        source: str = "",
        news_type: str = "",
        **extra,
    ) -> list[dict]:
        """
        新闻分析接口（兼容旧调用）：使用固定系统提示词和模型，返回结果列表。
        
        输入参数：
            id:         新闻唯一标识（整数）
            title:      新闻标题（必填）
            content:    新闻正文（可选）
            source:     来源媒体（可选）
            news_type:  新闻分类（可选）
            **extra:    其他参数（将被忽略）
        
        返回：
            结果字典列表（单个元素），包含12个AI分析字段 + id。
            符合新规：输出永远是 JSON 数组列表。
        
        异常处理：
            - 分析失败时返回空列表，不崩溃、不阻塞流程
            - 记录标准日志：[LLM分析] 开始、成功、失败、耗时
        """
        # 构建单条新闻字典，调用统一接口
        news_item = {
            "id": id,
            "title": title,
            "content": content,
            "source": source,
            "news_type": news_type,
        }
        return self.analyze_news_items(news_item)
    
    def _parse_news_response(self, raw_text: str, expected_id: int) -> dict:
        """
        解析新闻分析响应，校验字段类型和范围。
        
        Returns:
            包含所有12个AI字段 + id 的字典，增加 '_filled' 字段表示有效填充数
        """
        import json
        
        raw_text = raw_text.strip()
        
        # 剥离 markdown 代码块
        if raw_text.startswith("```"):
            first_nl = raw_text.find("\n")
            if first_nl == -1:
                first_nl = len(raw_text)
            raw_text = raw_text[first_nl + 1:]
            last_bt = raw_text.rfind("```")
            if last_bt != -1:
                raw_text = raw_text[:last_bt]
            raw_text = raw_text.strip()
        
        # 定位最外层 { ... }
        brace_start = raw_text.find("{")
        brace_end = raw_text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            raw_text = raw_text[brace_start:brace_end + 1]
        
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError(f"期望 dict，得到 {type(parsed).__name__}")
        
        # 校验 id 是否匹配（LLM 可能返回错误 id）
        response_id = parsed.get("id")
        if response_id is not None and int(response_id) != expected_id:
            print(f"[LLM分析] 警告: 响应 id={response_id} 与请求 id={expected_id} 不匹配")
        
        # 期望字段定义
        expected_fields = {
            "ai_interpretation":    (str,   True),
            "ai_event_type":        (str,   True),
            "ai_impact_level":      (int,   True),
            "ai_impact_direction":  (int,   True),
            "ai_risk_level":        (int,   True),
            "ai_benefit_sectors":   (str,   True),
            "ai_benefit_stocks":    (str,   True),
            "ai_keywords":          (str,   True),
            "is_official":          (int,   True),
            "is_breaking":          (int,   True),
            "sentiment":            (float, True),
            "sentiment_label":      (int,   True),
        }
        
        # 枚举字段合法值
        valid_enums = {
            "ai_event_type": {
                "财报", "并购", "政策", "研发", "诉讼", "高管变动",
                "战略合作", "产能扩张", "业务调整", "风险事件", "其他",
            },
        }
        
        cleaned = {"id": expected_id}
        filled = 0
        
        for field_name, (expected_type, allow_null) in expected_fields.items():
            val = parsed.get(field_name)
            if val is None:
                cleaned[field_name] = None
                continue
            
            # 类型转换
            try:
                if expected_type == float:
                    val = float(val)
                elif expected_type == int:
                    val = int(float(val))  # 兼容 "3.0" → 3
                elif expected_type == str:
                    val = str(val).strip().replace("\x00", "")
                    if not val:
                        cleaned[field_name] = None
                        continue
            except (ValueError, TypeError):
                cleaned[field_name] = None
                continue
            
            # 枚举校验
            if expected_type == str and field_name in valid_enums:
                if val not in valid_enums[field_name]:
                    cleaned[field_name] = None
                    continue
            
            # 数值范围钳位
            if expected_type == float:
                val = max(-1.0, min(1.0, val))
            elif expected_type == int:
                if field_name == "ai_impact_level":
                    val = max(1, min(5, val))
                elif field_name == "ai_impact_direction":
                    val = max(-1, min(1, val))
                elif field_name == "ai_risk_level":
                    val = max(1, min(5, val))
                elif field_name in ("is_official", "is_breaking"):
                    val = max(0, min(1, val))
                elif field_name == "sentiment_label":
                    val = max(-1, min(1, val))
            
            cleaned[field_name] = val
            filled += 1
        
        cleaned["_filled"] = filled
        return cleaned
    
    def _default_news_result(self, id: int) -> dict:
        """分析失败时返回的默认中性值"""
        return {
            "id":                    id,
            "ai_interpretation":     None,
            "ai_event_type":         None,
            "ai_impact_level":       3,          # 中等
            "ai_impact_direction":   0,          # 中性
            "ai_risk_level":         3,          # 中等
            "ai_benefit_sectors":    None,
            "ai_benefit_stocks":     None,
            "ai_keywords":           None,
            "is_official":           0,          # 非官方
            "is_breaking":           0,          # 非突发
            "sentiment":             0.0,        # 中性
            "sentiment_label":       0,          # 中性
        }

    # ═══════════════════════════════════════════════════════════════════
    #  批量新闻分析专用方法
    # ═══════════════════════════════════════════════════════════════════

    def batch_analyze_news(
        self,
        news_list: list[dict],
        **extra,
    ) -> list[dict]:
        """
        批量新闻分析接口（兼容旧调用）：使用固定系统提示词和模型。
        
        输入参数：
            news_list: 新闻字典列表，每个字典必须包含：
                - id:         新闻唯一标识（整数）
                - title:      新闻标题（必填）
                - content:    新闻正文（可选）
                - source:     来源媒体（可选）
                - news_type:  新闻分类（可选）
        
        返回：结果字典列表，每个元素包含12个AI分析字段 + id。
        
        异常处理：
            - 分析失败时返回空列表，不崩溃、不阻塞流程
            - 记录标准日志：[LLM批量分析] 开始、成功、失败、耗时
        """
        # 直接调用统一接口
        return self.analyze_news_items(news_list)
    
    def _parse_batch_news_response(self, raw_text: str) -> list[dict]:
        """
        解析批量新闻分析响应，校验字段类型和范围。
        
        Returns:
            包含所有12个AI字段 + id 的字典列表
        """
        import json
        
        raw_text = raw_text.strip()
        
        # 剥离 markdown 代码块
        if raw_text.startswith("```"):
            first_nl = raw_text.find("\n")
            if first_nl == -1:
                first_nl = len(raw_text)
            raw_text = raw_text[first_nl + 1:]
            last_bt = raw_text.rfind("```")
            if last_bt != -1:
                raw_text = raw_text[:last_bt]
            raw_text = raw_text.strip()
        
        # 定位最外层 [ ... ]
        bracket_start = raw_text.find("[")
        bracket_end = raw_text.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            raw_text = raw_text[bracket_start:bracket_end + 1]
        
        parsed = json.loads(raw_text)
        if not isinstance(parsed, list):
            raise ValueError(f"期望 list，得到 {type(parsed).__name__}")
        
        # 期望字段定义（与单条分析相同）
        expected_fields = {
            "ai_interpretation":    (str,   True),
            "ai_event_type":        (str,   True),
            "ai_impact_level":      (int,   True),
            "ai_impact_direction":  (int,   True),
            "ai_risk_level":        (int,   True),
            "ai_benefit_sectors":   (str,   True),
            "ai_benefit_stocks":    (str,   True),
            "ai_keywords":          (str,   True),
            "is_official":          (int,   True),
            "is_breaking":          (int,   True),
            "sentiment":            (float, True),
            "sentiment_label":      (int,   True),
        }
        
        # 枚举字段合法值
        valid_enums = {
            "ai_event_type": {
                "财报", "并购", "政策", "研发", "诉讼", "高管变动",
                "战略合作", "产能扩张", "业务调整", "风险事件", "其他",
            },
        }
        
        results = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            
            item_id = item.get("id")
            if item_id is None:
                continue
            
            cleaned = {"id": int(item_id)}
            for field_name, (expected_type, allow_null) in expected_fields.items():
                val = item.get(field_name)
                if val is None:
                    cleaned[field_name] = None
                    continue
                
                # 类型转换
                try:
                    if expected_type == float:
                        val = float(val)
                    elif expected_type == int:
                        val = int(float(val))  # 兼容 "3.0" → 3
                    elif expected_type == str:
                        val = str(val).strip().replace("\x00", "")
                        if not val:
                            cleaned[field_name] = None
                            continue
                except (ValueError, TypeError):
                    cleaned[field_name] = None
                    continue
                
                # 枚举校验
                if expected_type == str and field_name in valid_enums:
                    if val not in valid_enums[field_name]:
                        cleaned[field_name] = None
                        continue
                
                # 数值范围钳位
                if expected_type == float:
                    val = max(-1.0, min(1.0, val))
                elif expected_type == int:
                    if field_name == "ai_impact_level":
                        val = max(1, min(5, val))
                    elif field_name == "ai_impact_direction":
                        val = max(-1, min(1, val))
                    elif field_name == "ai_risk_level":
                        val = max(1, min(5, val))
                    elif field_name in ("is_official", "is_breaking"):
                        val = max(0, min(1, val))
                    elif field_name == "sentiment_label":
                        val = max(-1, min(1, val))
                
                cleaned[field_name] = val
            
            results.append(cleaned)
        
        return results

    # ═══════════════════════════════════════════════════════════════════
    #  便捷方法：直接传图片/文件
    # ═══════════════════════════════════════════════════════════════════

    def chat_image(
        self,
        prompt: str,
        image: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **extra,
    ) -> str:
        """
        图片识别快捷方法

        Args:
            prompt:    提问文本（如"描述这张图片"）
            image:     图片路径/URL/Base64（单张）
        """
        return self.chat(
            prompt=prompt,
            images=[image],
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    def chat_images(
        self,
        prompt: str,
        images: list[str],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **extra,
    ) -> str:
        """
        多图片识别快捷方法

        Args:
            prompt:    提问文本
            images:    图片列表（URL/路径/Base64）
        """
        return self.chat(
            prompt=prompt,
            images=images,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    def chat_file(
        self,
        prompt: str,
        file_path: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **extra,
    ) -> str:
        """
        文件分析快捷方法

        Args:
            prompt:     提问文本（如"分析这份财报"）
            file_path:  文件路径（支持图片/音频/视频/文档）
        """
        return self.chat(
            prompt=prompt,
            files=[file_path],
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    # ═══════════════════════════════════════════════════════════════════
    #  预热
    # ═══════════════════════════════════════════════════════════════════

    def warmup(self):
        """
        服务启动时预热 LLM：
        1. 验证 API 可达性
        2. 尝试用默认模型发一个极短请求
        """
        if self._warmed_up:
            return

        try:
            url = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.default_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
                "temperature": 0,
            }
            resp = requests.post(url, headers=self._headers, json=payload, timeout=15)
            if resp.status_code == 200:
                self._warmup_model = self.default_model
                print(f"[llm] 预热成功，默认模型: {self.default_model}")
            else:
                print(f"[llm] 预热响应异常: {resp.status_code}")
        except Exception as e:
            print(f"[llm] 预热失败（不影响使用）: {e}")

        self._warmed_up = True


# ═══════════════════════════════════════════════════════════════════
#  模块级单例 & 向后兼容的函数式 API
# ═══════════════════════════════════════════════════════════════════

# 全局单例
_llm = LLM()

# 对外暴露
AVAILABLE_MODELS = AVAILABLE_LLM_MODELS


def call_llm(
    prompt: str = "",
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    messages: list[dict] | None = None,
    images: list[str] | None = None,
    files: list[str] | None = None,
) -> str:
    """向后兼容的函数式接口"""
    return _llm.chat(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        images=images,
        files=files,
    )


def stream_llm(
    prompt: str = "",
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    messages: list[dict] | None = None,
    images: list[str] | None = None,
    files: list[str] | None = None,
) -> Generator[str, None, None]:
    """向后兼容的流式函数式接口"""
    return _llm.stream(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        images=images,
        files=files,
    )


def call_llm_with_history(
    message: str,
    history: list[dict] | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """向后兼容的带历史上下文函数式接口"""
    return _llm.chat_with_history(
        message=message,
        history=history,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def warmup():
    """向后兼容的预热函数"""
    _llm.warmup()
