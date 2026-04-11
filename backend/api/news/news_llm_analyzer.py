"""
================================================================================
api/news/news_llm_analyzer.py — 8线程并行新闻 LLM 分析引擎
================================================================================

【模块职责】
  从 Redis news:pending_llm（Set）中消费待分析新闻 id，
  批量调用 LLM 进行结构化分析，结果写回 Redis 并推入持久化队列。

【工作流程（每个线程独立循环）】
  1. SPOP  news:pending_llm        → 原子弹出最多 BATCH_SIZE 个待分析项
                                     格式: "table_name:news_id" 或 "news_id"
  2. GET   news:data:{table}:{id}  → 批量读取完整新闻 JSON
  3. 过滤  need_analyze==0 或 ai_analyze_time 已有值 → 跳过（已处理）
  4. 构造  [{"id":..,"title":..,"content":..},...] 数组格式 → 调用 LLM
  5. 校验  LLM 输出字段类型、范围、枚举合法性
  6. 写回  news_data_update(id, ai_result) → 更新 Redis String
  7. 推入  news:pending_persist（List）→ 供持久化线程批量写 MySQL

【线程安全设计】
  - SPOP 原子操作：Redis Set 保证同一 id 不被多线程重复弹出
  - 8 线程共享同一个 LLM 客户端实例（HTTP 连接是无状态的，天然线程安全）
  - 无任务时 event.wait(IDLE_WAIT_SECONDS)，低 CPU 占用
  - 超时 25 秒，失败重试 1 次，重试仍失败直接跳过（不丢数据，下次重新入队时再处理）

【LLM 输入/输出格式】
  输入：JSON 数组 [{"id": 1001, "title": "...", "content": "...", "source": "..."}, ...]
  输出：JSON 数组 [{"id": 1001, "ai_interpretation": "...", ...}, ...]
  字段：共 12 个 AI 分析字段（见 SYSTEM_PROMPT）

【对外公开接口】
  get_news_analyzer() → NewsLLMAnalyzer 全局单例
  analyzer.start_background()  → 启动 8 条后台线程（被 routes.py start_scheduler 调用）
  analyzer.stop()              → 优雅停止所有线程
  analyzer.get_status()        → 返回引擎运行状态字典

【依赖关系】
  utils/redis_client.py  → pending_llm_spop / news_data_get / news_data_update
                           pending_persist_push_batch / _unpack_pending_item
  utils/llm.py           → LLM 客户端（火山方舟 ARK API）
================================================================================
"""

import json
import time
import threading
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger("news_llm")


# ═══════════════════════════════════════════════════════════════════
#  System Prompt（统一系统提示，适用全部 8 线程）
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是专业金融量化分析师。

## 任务
对财经新闻列表做结构化分析，**严格按照输入顺序输出 JSON 数组**。

## 强制规则
1. 输入是 JSON 数组，输出必须也是 JSON 数组，每个元素对应输入中的同一条新闻
2. 每个输出元素必须包含原始 id 字段（与输入 id 严格对应）
3. 只输出 JSON 数组，禁止任何额外文字、解释、注释、markdown 格式符
4. 未知字段填 null，字符串空值填 ""
5. 数字为数字类型，分数保留 2 位小数
6. 严禁虚构个股、板块、指数

## 每条输出字段（13个，含原始 id）
{
  "id": <原始输入的id，整数>,
  "ai_interpretation": "200字内核心解读",
  "ai_event_type": "财报/并购/政策/研发/诉讼/高管变动/战略合作/产能扩张/业务调整/风险事件/其他",
  "ai_impact_level": 1,
  "ai_impact_direction": 1,
  "ai_risk_level": 1,
  "ai_benefit_sectors": "受益板块，逗号分隔",
  "ai_benefit_stocks": "受益个股，逗号分隔，严禁虚构",
  "ai_keywords": "3-6个关键词，逗号分隔",
  "sentiment": 0.0,
  "sentiment_label": 1,
  "is_official": 1,
  "is_breaking": 0
}

## 字段说明
- ai_impact_level:     1=轻微 2=一般 3=中等 4=较大 5=重大
- ai_impact_direction: 1=利好 0=中性 -1=利空
- ai_risk_level:       1=低 2=较低 3=中等 4=较高 5=高
- sentiment:           -1.0(极度负面) ~ 1.0(极度正面)
- sentiment_label:     1=正面 0=中性 -1=负面
- is_official:         1=是官方公告 0=否
- is_breaking:         1=突发新闻 0=普通

## 示例
输入：[{"id":1001,"title":"某公司季报超预期","content":"..."}]
输出：[{"id":1001,"ai_interpretation":"...","ai_event_type":"财报","ai_impact_level":3,...}]
"""


# ═══════════════════════════════════════════════════════════════════
#  LLM 输出字段校验规则
# ═══════════════════════════════════════════════════════════════════

# 期望字段 → (Python类型, 是否允许null)
_EXPECTED_FIELDS: Dict[str, tuple] = {
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
_VALID_ENUMS: Dict[str, set] = {
    "ai_event_type": {
        "财报", "并购", "政策", "研发", "诉讼", "高管变动",
        "战略合作", "产能扩张", "业务调整", "风险事件", "其他",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  LLM 输出解析 & 字段校验
# ═══════════════════════════════════════════════════════════════════

def _extract_json_array(text: str) -> list:
    """
    从 LLM 返回文本中提取 JSON 数组。

    兼容以下情况：
      - 纯 JSON 数组文本
      - ```json ... ``` 或 ``` ... ``` 包裹
      - 数组前后有少量文字

    Returns:
        解析出的 list；失败时抛出 json.JSONDecodeError
    """
    text = text.strip()

    # 剥离 markdown 代码块包裹
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl == -1:
            first_nl = len(text)
        text = text[first_nl + 1:]
        last_bt = text.rfind("```")
        if last_bt != -1:
            text = text[:last_bt]
        text = text.strip()

    # 定位最外层 [ ... ]
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        text = text[bracket_start:bracket_end + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return []
    return parsed


def _validate_single(data: dict) -> dict:
    """
    校验并清洗单条 LLM 输出 dict。

    处理逻辑：
      - 类型转换（str/int/float）
      - NUL 字节清除（MySQL 不允许 \\x00）
      - 枚举合法性校验（ai_event_type）
      - 数值范围钳位（sentiment [-1,1]、level [1,5] 等）

    Returns:
        清洗后的字典（仅包含合法字段，非法值设为 None）
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
#  LLM 批量调用（含重试）
# ═══════════════════════════════════════════════════════════════════

LLM_TIMEOUT    = 25  # 单次 LLM 请求超时（秒）
MAX_RETRIES    = 1   # 失败重试次数（共最多尝试 MAX_RETRIES+1 次）


def _call_llm_batch(llm_client, news_batch: list) -> list:
    """
    调用 LLM 统一接口 analyze_news_items 进行批量新闻分析。
    使用线程启动时固定的系统提示词和模型配置。

    Args:
        llm_client: LLM 客户端实例（utils/llm.py 中的 LLM 类）
        news_batch: [{"id": 1001, "title": "...", "content": "..."}, ...]

    Returns:
        LLM 解析后的结果列表（每条含 id + AI字段）；失败时抛出异常

    Note:
        使用新的统一接口 analyze_news_items，该接口使用固定配置，
        自动处理单条/批量输入，返回已验证的结果列表。
    """
    # 防御性检查：确保 llm_client 有效
    if llm_client is None:
        raise ValueError("LLM 客户端未初始化，无法调用 API")
    
    # 检查 analyze_news_items 方法是否存在
    if not hasattr(llm_client, "analyze_news_items"):
        raise AttributeError("LLM 客户端缺少 analyze_news_items 方法，请更新 llm.py")
    
    # 调用统一接口
    results = llm_client.analyze_news_items(news_batch)
    
    # analyze_news_items 返回的是已验证的结果列表，每个元素包含 id 和所有 AI 字段
    # 但为了保持向后兼容，我们需要返回与旧版本相同的格式（原始 LLM 输出数组）
    # 实际上，analyze_news_items 内部已经调用了 _parse_batch_news_response，
    # 返回的是清理后的字典。我们可以直接返回这个结果。
    return results


def _call_llm_batch_with_retry(llm_client, news_batch: list) -> list:
    """
    带重试的批量 LLM 调用（最多尝试 MAX_RETRIES+1 次，间隔 2 秒）。

    Returns:
        解析后的结果列表；所有尝试失败则返回 []
    """
    # 防御性检查：如果 LLM 客户端无效，直接返回空列表
    if llm_client is None:
        logger.warning("[LLM] LLM 客户端未初始化，跳过分析")
        return []
    
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            result = _call_llm_batch(llm_client, news_batch)
            if result:
                if attempt > 1:
                    logger.info("[LLM] 第%d次尝试成功 | batch_size=%d", attempt, len(news_batch))
                return result
            last_error = "LLM 返回空数组"
        except Exception as e:
            last_error = str(e)
            logger.warning("[LLM] 第%d次尝试失败: %s | batch_size=%d", attempt, e, len(news_batch))

        if attempt <= MAX_RETRIES:
            time.sleep(2)  # 重试前等待

    logger.error("[LLM] 重试后仍失败: %s | batch_size=%d", last_error, len(news_batch))
    return []


# ═══════════════════════════════════════════════════════════════════
#  8线程 LLM 分析引擎（核心类）
# ═══════════════════════════════════════════════════════════════════

BATCH_SIZE         = 6   # 每次从 news:pending_llm SPOP 的最大条数
IDLE_WAIT_SECONDS  = 6   # 无任务时线程休眠时间（秒），降低 CPU 和 Redis 轮询压力


class NewsLLMAnalyzer:
    """
    8线程并行新闻 LLM 分析引擎。

    设计要点：
      - 8 个独立线程，每线程独立循环（互不依赖）
      - Redis SPOP 保证同一 id 不被多线程重复处理（天然分布式锁）
      - 8 线程共享一个 LLM 客户端（HTTP 无状态，线程安全）
      - 无任务时 event.wait 休眠，不忙等
      - 优雅停止：设置 stop_event，各线程在下次循环开始前退出

    生命周期（由 routes.py start_scheduler 管理）：
      start_background() → 8线程启动 → 持续消费 pending_llm
      stop()             → 通知所有线程退出，等待最多 5s
    """

    NUM_THREADS = 8  # 并行线程数（固定值，与系统资源和 LLM 并发限制匹配）

    def __init__(self):
        self._llm_client = None
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._initialized = False
        self._init_lock = threading.Lock()

    # ───────────────────────────────────────────────────────────────
    #  LLM 客户端初始化（懒加载，仅初始化一次）
    # ───────────────────────────────────────────────────────────────

    def _init_llm(self):
        """
        线程安全地初始化 LLM 客户端（双重检查锁定模式）。
        8 个线程共享同一个客户端实例，在 start_background 时调用一次。
        直接使用 LLM 单例类，确保全局唯一实例。
        """
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            try:
                from utils.llm import LLM
                # LLM 是单例类，LLM() 返回全局唯一实例
                self._llm_client = LLM()
                # 设置新闻分析专用配置（线程启动时固定，永久不可修改）
                self._llm_client.set_news_analysis_config(
                    system_prompt=SYSTEM_PROMPT,
                    model=None,  # 使用默认模型（已在配置中定义）
                )
                self._initialized = True
                logger.info("[分析器] LLM 客户端初始化完成（单例模式），已固定系统提示词和模型")
            except Exception as e:
                logger.error("[分析器] LLM 客户端初始化失败: %s", e)
                # 初始化失败时设置占位符，避免后续重复尝试
                self._llm_client = None
                self._initialized = True  # 标记已初始化但失败，防止重复报错

    # ───────────────────────────────────────────────────────────────
    #  单线程工作循环
    # ───────────────────────────────────────────────────────────────

    def _worker_loop(self, thread_id: int):
        """
        单个 LLM 分析线程的永久循环。

        循环步骤：
          1. 调用 _process_once() 处理一个批次
          2. 无任务时 event.wait(IDLE_WAIT_SECONDS) 休眠
          3. 异常时同样休眠后继续（不崩溃）
          4. stop_event 被置位时退出循环
        """
        logger.info("[分析器] 线程 %d 启动", thread_id)

        while not self._stop_event.is_set():
            try:
                processed = self._process_once(thread_id)
                if processed == 0:
                    self._stop_event.wait(timeout=IDLE_WAIT_SECONDS)
            except Exception as e:
                logger.error("[分析器] 线程 %d 异常（继续运行）: %s", thread_id, e)
                self._stop_event.wait(timeout=IDLE_WAIT_SECONDS)

        logger.info("[分析器] 线程 %d 已停止", thread_id)

    def _process_once(self, thread_id: int) -> int:
        """
        执行一次完整的分析批次（SPOP → 过滤 → LLM → 写回 → 推入persist）。

        Returns:
            本次成功分析并写回的新闻条数（0 表示无任务或全部跳过）
        """
        from utils.redis_client import (
            pending_llm_spop,
            news_data_get,
            news_data_update,
            pending_persist_push_batch,
            _unpack_pending_item,
        )

        # Step 1: SPOP 获取待分析项（格式: "table_name:news_id" 或 "news_id"）
        raw_items = pending_llm_spop(BATCH_SIZE)
        if not raw_items:
            return 0

        # 解包为 (news_id, table_name) 列表
        id_table_pairs = []
        for item in raw_items:
            news_id, table_name = _unpack_pending_item(item)
            if news_id is not None:
                id_table_pairs.append((news_id, table_name))

        if not id_table_pairs:
            return 0

        # Step 2: 逐条读取 Redis String，过滤已处理的
        news_list = []
        for news_id, table_name in id_table_pairs:
            data = news_data_get(news_id, table_name)
            if data is None:
                logger.warning("[分析器] 线程%d: news:data:%s:%d 不存在，跳过",
                               thread_id, table_name or "?", news_id)
                continue

            # Step 3: 过滤——已标记无需分析 或 已有分析结果 → 跳过
            if data.get("need_analyze", 1) == 0:
                logger.debug("[分析器] 线程%d: id=%d need_analyze=0，跳过", thread_id, news_id)
                continue
            ai_analyze_time = data.get("ai_analyze_time")
            if ai_analyze_time and str(ai_analyze_time).strip() not in ("", "None", "null"):
                logger.debug("[分析器] 线程%d: id=%d 已有 ai_analyze_time，跳过", thread_id, news_id)
                continue

            news_list.append({
                "id":         news_id,
                "title":      (data.get("title") or "").strip(),
                "content":    (data.get("content") or "")[:2000],  # 截断避免超出 token 限制
                "source":     data.get("source", ""),
                "news_type":  data.get("news_type", ""),
                "table_name": data.get("table_name", table_name or ""),
                "_data":      data,  # 原始数据备用
            })

        if not news_list:
            return 0

        # Step 4: 构造 LLM 输入（只传必要字段，不传 _data）
        llm_input = [
            {
                "id":        item["id"],
                "title":     item["title"],
                "content":   item["content"],
                "source":    item.get("source", ""),
                "news_type": item.get("news_type", ""),
            }
            for item in news_list
        ]

        logger.info("[分析器] 线程%d: 开始 LLM 分析 %d 条", thread_id, len(llm_input))
        llm_results = _call_llm_batch_with_retry(self._llm_client, llm_input)

        if not llm_results:
            logger.warning("[分析器] 线程%d: LLM 返回为空，跳过本批次", thread_id)
            return 0

        # 构建 id → AI结果 映射（llm_results 已经是 analyze_news_items 验证后的结果）
        id_to_result: Dict[int, dict] = {}
        for item in llm_results:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("id"))
                # 复制除 id 外的所有字段作为 AI 结果
                ai_data = {k: v for k, v in item.items() if k != "id"}
                if ai_data:
                    id_to_result[item_id] = ai_data
            except (ValueError, TypeError):
                continue

        # Step 5: 写回 Redis String（合并 AI 结果 + 标记已分析）
        success_ids = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in news_list:
            news_id = item["id"]
            ai_result = id_to_result.get(news_id)
            if ai_result is None:
                logger.warning("[分析器] 线程%d: id=%d LLM输出中无对应结果，跳过", thread_id, news_id)
                continue

            updates = {
                **ai_result,
                "need_analyze":    0,         # 标记已处理，避免重复分析
                "ai_analyze_time": now_str,   # 记录分析时间
                "table_name":      item.get("table_name", ""),  # 确保 table_name 保留
            }

            if news_data_update(news_id, updates):
                success_ids.append(news_id)
            else:
                logger.warning("[分析器] 线程%d: id=%d 写回 Redis 失败", thread_id, news_id)

        # Step 6: 批量推入 news:pending_persist（供持久化线程消费）
        if success_ids:
            success_table_names = []
            for item in news_list:
                if item["id"] in success_ids:
                    table_name = item.get("table_name", "")
                    # 确保 table_name 不为空字符串
                    if not table_name or not table_name.strip():
                        # 尝试从其他字段获取
                        table_name = item.get("_table", item.get("table", "unknown"))
                        logger.warning("[分析器] 线程%d: id=%d table_name 为空，使用备用值: %s", 
                                     thread_id, item["id"], table_name)
                    success_table_names.append(table_name)
            pushed = pending_persist_push_batch(success_ids, success_table_names)
            logger.info(
                "[分析器] 线程%d: 完成 | 取:%d 有效:%d 成功:%d 推入persist:%d",
                thread_id, len(id_table_pairs), len(news_list), len(success_ids), pushed,
            )

        return len(success_ids)

    # ───────────────────────────────────────────────────────────────
    #  对外公开接口
    # ───────────────────────────────────────────────────────────────

    def start_background(self):
        """
        启动 NUM_THREADS 条后台 LLM 分析线程（幂等，已全部存活时跳过）。
        由 routes.py 的 start_scheduler() 在项目启动时调用一次。
        """
        self._init_llm()
        if not self._initialized:
            logger.error("[分析器] LLM 未初始化，无法启动后台线程")
            return

        # 已有足够存活线程则跳过
        alive_count = sum(1 for t in self._threads if t.is_alive())
        if alive_count >= self.NUM_THREADS:
            logger.info("[分析器] 后台线程已全部运行（%d线程），跳过重复启动", alive_count)
            return

        self._stop_event.clear()
        self._threads = []

        for i in range(self.NUM_THREADS):
            t = threading.Thread(
                target=self._worker_loop,
                args=(i + 1,),
                name=f"news-llm-{i + 1}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

        logger.info("[分析器] %d 条 LLM 分析线程已启动", self.NUM_THREADS)

    def stop(self):
        """
        优雅停止所有后台分析线程（最多等待 5s/线程）。
        由 routes.py 的 stop_scheduler() 在服务关闭时调用。
        """
        self._stop_event.set()
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=5)
        self._threads = []
        logger.info("[分析器] 所有 LLM 线程已停止")

    def get_status(self) -> dict:
        """
        返回分析引擎实时状态（供 /api/news/analyzer_status 接口使用）。

        Returns:
            包含线程数、存活线程、队列大小、配置参数的字典
        """
        from utils.redis_client import pending_llm_size, pending_persist_size

        alive_threads = [t.name for t in self._threads if t.is_alive()]
        return {
            "initialized":        self._initialized,
            "num_threads":        self.NUM_THREADS,
            "alive_threads":      len(alive_threads),
            "thread_names":       alive_threads,
            "pending_llm_size":   pending_llm_size(),
            "pending_persist_size": pending_persist_size(),
            "batch_size":         BATCH_SIZE,
            "idle_wait_seconds":  IDLE_WAIT_SECONDS,
            "mode":               "redis_string_set_list",
        }


# ═══════════════════════════════════════════════════════════════════
#  全局单例（模块级，项目生命周期内唯一）
# ═══════════════════════════════════════════════════════════════════

_analyzer: Optional[NewsLLMAnalyzer] = None


def get_news_analyzer() -> NewsLLMAnalyzer:
    """
    获取 NewsLLMAnalyzer 全局单例。
    线程安全（CPython GIL 保证模块级赋值的原子性）。
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = NewsLLMAnalyzer()
    return _analyzer
