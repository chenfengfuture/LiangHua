"""
================================================================================
api/news/llm_analyzer.py — 新闻 LLM 分析工具函数（单条/批量，备用模式）
================================================================================

【模块说明】
  本模块提供单条新闻 LLM 分析的工具函数，属于"同步调用"模式：
  调用方直接获得分析结果，适用于：
    - 手动调试分析效果
    - 临时触发单条新闻的 LLM 分析
    - 与数据库直连的批量补偿处理（fetch_need_analyze → analyze_news → update_ai_result）

  ⚠️  注意：项目日常运行不依赖本模块。
      正式生产环境的 LLM 分析由 news_llm_analyzer.py（8线程异步引擎）负责，
      通过 Redis 三层管道（pending_llm → LLM → pending_persist）高并发处理。
      本模块作为备用工具保留，不影响主流程。

【与 news_llm_analyzer.py 的区别】
  ┌─────────────────────┬──────────────────────────────────────────┐
  │  本模块 (llm_analyzer) │  news_llm_analyzer.py (主模块)          │
  ├─────────────────────┼──────────────────────────────────────────┤
  │  同步单条调用         │  8线程异步批量处理                         │
  │  直接返回分析结果      │  结果写入 Redis，持久化层异步写库           │
  │  适合调试/补偿        │  适合生产高并发采集场景                     │
  │  无外部引用（备用）    │  被 routes.py start_scheduler 调用        │
  └─────────────────────┴──────────────────────────────────────────┘

【对外公开函数】
  analyze_news(title, content, ...)  → 同步分析单条新闻，返回结构化字段字典
  batch_analyze(limit, ...)          → 批量拉取待分析新闻并逐条处理，回写数据库

【LLM 输出字段（12个）】
  AI 分析（10个）：
    ai_interpretation, ai_event_type, ai_impact_level, ai_impact_direction,
    ai_risk_level, ai_benefit_sectors, ai_benefit_stocks, ai_keywords,
    is_official, is_breaking
  情感分析（2个）：
    sentiment, sentiment_label

【依赖关系】
  utils/llm.py           → LLM().chat()（同步单次调用）
  models/news_models.py  → fetch_need_analyze() / update_ai_result()（仅 batch_analyze 使用）
================================================================================
"""

import json
from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
#  系统提示词（单条模式，输出 JSON 对象）
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是专业金融量化分析师，只输出精简JSON，无任何多余内容。

## 任务
对财经新闻做结构化分析，**仅返回JSON对象**，无解释、无注释、无格式符。

## 强制规则
1. 只输出JSON，禁止任何额外文字
2. 字段不可增减，未知填null
3. 列表用中文逗号分隔，空值填""
4. 数字为数字类型，分数保留2位小数
5. 严禁虚构个股、板块、指数

## 输出字段（12个）
{
  "ai_interpretation": "200字内核心解读",
  "ai_event_type": "财报/并购/政策/研发/诉讼/高管变动/战略合作/产能扩张/业务调整/风险事件/其他",
  "ai_impact_level": 1,
  "ai_impact_direction": 1,
  "ai_risk_level": 1,
  "ai_benefit_sectors": "受益板块",
  "ai_benefit_stocks": "受益个股",
  "ai_keywords": "3-6个关键词",
  "sentiment": 0.0,
  "sentiment_label": 1,
  "is_official": 1,
  "is_breaking": 0
}"""


# ═══════════════════════════════════════════════════════════════════
#  期望字段校验规则
# ═══════════════════════════════════════════════════════════════════

# 字段名 → (Python类型, 是否允许null)
_EXPECTED_FIELDS = {
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
_VALID_ENUMS = {
    "ai_event_type": {
        "财报", "并购", "政策", "研发", "诉讼", "高管变动",
        "战略合作", "产能扩张", "业务调整", "风险事件", "其他",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  JSON 提取 & 字段校验
# ═══════════════════════════════════════════════════════════════════

def _extract_json(text: str) -> dict:
    """
    从 LLM 返回文本中提取 JSON 对象。

    兼容：
      - 纯 JSON 文本
      - ```json ... ``` 或 ``` ... ``` 包裹
      - JSON 前后有少量文字

    Returns:
        解析出的 dict；失败时抛出 json.JSONDecodeError
    """
    text = text.strip()

    # 剥离 markdown 代码块包裹
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline == -1:
            first_newline = len(text)
        text = text[first_newline + 1:]
        last_backtick = text.rfind("```")
        if last_backtick != -1:
            text = text[:last_backtick]
        text = text.strip()

    # 定位最外层 { ... }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]

    return json.loads(text)


def _validate_and_clean(data: dict) -> dict:
    """
    校验并清洗 LLM 返回的 JSON 字段。

    处理逻辑：
      - 移除期望字段列表之外的多余字段
      - 类型转换（str/int/float）
      - NUL 字节清除（MySQL TEXT 列不允许 \\x00）
      - 枚举合法性校验
      - 数值范围钳位

    Returns:
        清洗后的字典（仅包含合法字段）
    """
    cleaned = {}
    for field_name, (expected_type, allow_null) in _EXPECTED_FIELDS.items():
        val = data.get(field_name)
        if val is None:
            cleaned[field_name] = None
            continue

        # 类型转换
        try:
            if expected_type == float:
                val = float(val)
            elif expected_type == int:
                val = int(float(val))  # 兼容 "4.0" → 4
            elif expected_type == str:
                val = str(val).strip().replace("\x00", "")
                if not val:
                    cleaned[field_name] = None
                    continue
        except (ValueError, TypeError):
            cleaned[field_name] = None
            continue

        # 枚举校验
        if expected_type == str and field_name in _VALID_ENUMS:
            if val not in _VALID_ENUMS[field_name]:
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

    return cleaned


# ═══════════════════════════════════════════════════════════════════
#  公开工具函数
# ═══════════════════════════════════════════════════════════════════

def analyze_news(
    title: str,
    content: str = "",
    source: str = "",
    source_category: str = "",
    news_type: str = "",
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> dict:
    """
    同步调用 LLM 分析单条新闻，返回可直接入库的字段字典。

    适用场景：调试、手动触发单条分析、补偿处理。
    生产批量处理请使用 news_llm_analyzer.py 中的 8线程引擎。

    Args:
        title:           新闻标题（必填）
        content:         新闻正文（可选，有则分析更准确）
        source:          来源媒体（如"东方财富"）
        source_category: 来源分类（如"东方财富研报"）
        news_type:       新闻分类（company/cctv/caixin/global/notice/stock）
        model:           LLM 模型名称，默认使用配置中的默认模型
        temperature:     生成温度（建议 0.1~0.3，保证 JSON 输出稳定性）
        max_tokens:      最大生成 token 数

    Returns:
        {
            "success": True/False,
            "raw_text": "模型原始返回文本",
            "result":  { ...12个分析字段... },  # success=True 时
            "error":   "错误描述",               # success=False 时
            "stats":   {"filled_count": 10, "total_count": 12},
        }
    """
    from utils.llm import LLM

    if not title or not title.strip():
        return {"success": False, "raw_text": "", "result": None,
                "error": "标题为空", "stats": None}

    # 构建用户消息
    parts = [f"## 新闻标题\n{title}"]

    if content and content.strip():
        truncated = content.strip()[:3000]
        if len(content.strip()) > 3000:
            truncated += "\n...(正文已截断)"
        parts.append(f"## 新闻正文\n{truncated}")

    if source:
        parts.append(f"## 来源媒体\n{source}")
    if source_category:
        parts.append(f"## 来源分类\n{source_category}")
    if news_type:
        type_names = {
            "company": "公司动态", "cctv": "新闻联播", "caixin": "财新新闻",
            "global":  "国际新闻", "notice": "公告",   "stock":  "个股新闻",
        }
        parts.append(f"## 新闻类型\n{type_names.get(news_type, news_type)}")

    user_message = "\n\n".join(parts)

    # 调用 LLM
    try:
        raw_text = LLM().chat(
            prompt=user_message,
            system_prompt=SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        return {"success": False, "raw_text": "", "result": None,
                "error": f"LLM 调用失败: {type(e).__name__}: {e}", "stats": None}

    # 解析 JSON
    try:
        parsed = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        return {"success": False, "raw_text": raw_text, "result": None,
                "error": f"JSON 解析失败: {e}", "stats": None}

    if not isinstance(parsed, dict):
        return {"success": False, "raw_text": raw_text, "result": None,
                "error": f"返回格式异常: 期望 dict，得到 {type(parsed).__name__}", "stats": None}

    # 校验 & 清洗
    result = _validate_and_clean(parsed)
    filled = sum(1 for v in result.values() if v is not None)

    return {
        "success":  True,
        "raw_text": raw_text,
        "result":   result,
        "error":    None,
        "stats":    {"filled_count": filled, "total_count": len(result)},
    }


def batch_analyze(
    limit: int = 10,
    model: str | None = None,
    temperature: float = 0.3,
    dry_run: bool = False,
) -> dict:
    """
    批量拉取数据库中待分析新闻，逐条调用 LLM 并回写结果。

    适用场景：历史数据补偿分析、测试环境下的批量验证。
    生产环境请使用 news_llm_analyzer.py 中的 8线程引擎（基于 Redis 队列）。

    Args:
        limit:       最多处理条数
        model:       LLM 模型名称
        temperature: 生成温度
        dry_run:     True=仅分析不写库（用于测试）

    Returns:
        {
            "total_fetched": int,   # 从数据库拉取的条数
            "processed":     int,   # 实际处理条数（=total_fetched）
            "success":       int,   # 分析并写库成功的条数
            "failed":        int,   # 失败条数
            "results":       list,  # 每条的详细处理结果
        }
    """
    from models.news_models import fetch_need_analyze, update_ai_result

    # 拉取待分析新闻
    news_list = fetch_need_analyze(limit=limit)
    if not news_list:
        return {"total_fetched": 0, "processed": 0,
                "success": 0, "failed": 0, "results": []}

    total_fetched = len(news_list)
    success_count = 0
    fail_count = 0
    details = []

    for idx, news in enumerate(news_list, 1):
        news_id          = news["id"]
        table_name       = news["_table"]
        title            = news.get("title", "")
        content          = news.get("content", "") or ""
        source           = news.get("source", "") or ""
        source_category  = news.get("source_category", "") or ""
        news_type        = news.get("_news_type", "")

        print(f"[llm_analyzer] ({idx}/{total_fetched}) 分析: {title[:50]}...")

        resp = analyze_news(
            title=title,
            content=content,
            source=source,
            source_category=source_category,
            news_type=news_type,
            model=model,
            temperature=temperature,
        )

        detail = {
            "news_id": news_id,
            "table":   table_name,
            "title":   title[:80],
            "success": resp["success"],
            "stats":   resp["stats"],
            "error":   resp["error"],
        }
        details.append(detail)

        if resp["success"] and resp["result"]:
            success_count += 1
            if not dry_run:
                ok = update_ai_result(table_name, news_id, resp["result"])
                if not ok:
                    detail["db_error"] = "回写数据库失败"
                    success_count -= 1
                    fail_count += 1
        else:
            fail_count += 1
            print(f"  [WARN] 分析失败: {resp['error']}")

    print(f"[llm_analyzer] 批量分析完成: 拉取={total_fetched}，"
          f"成功={success_count}，失败={fail_count}")

    return {
        "total_fetched": total_fetched,
        "processed":     total_fetched,
        "success":       success_count,
        "failed":        fail_count,
        "results":       details,
    }
