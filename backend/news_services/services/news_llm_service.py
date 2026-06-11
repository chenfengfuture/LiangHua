"""
news_services/services/news_llm_service.py — LLM 分析服务

8 线程并行新闻 LLM 分析引擎（从原 api/news/news_llm_analyzer.py 整合迁移）。

【工作流程（每个线程独立循环）】
  1. SPOP  news:pending_llm        → 原子弹出最多 BATCH_SIZE 个待分析项
  2. GET   news:data:{table}:{id}  → 批量读取完整新闻 JSON
  3. 过滤  need_analyze==0 或 ai_analyze_time 已有值 → 跳过
  4. 构造  [{"id":..,"title":..,"content":..},...] → 调用 LLM
  5. 校验  字段类型 / 范围 / 枚举合法性
  6. 写回  news_data_update(id, ai_result) → 更新 Redis String
  7. 推入  news:pending_persist（List）→ 供持久化线程批量写 MySQL

【线程安全】
  - SPOP 原子操作：Redis Set 保证同一 id 不被多线程重复弹出
  - 8 线程共享 LLM 单例（HTTP 客户端无状态）
  - event.wait 空闲休眠
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from utils.redis_client_compat import (
    _unpack_pending_item,
    news_data_get,
    news_data_update,
    pending_finbert_push_batch,
    pending_finbert_size,
    pending_llm_size,
    pending_llm_spop,
    pending_persist_push_batch,
    pending_persist_size,
)

from news_services.config import (
    FINBERT_ENABLED,
    LLM_BATCH_SIZE,
    LLM_IDLE_WAIT,
    LLM_MAX_RETRIES,
    LLM_THREADS,
    LLM_TIMEOUT,
)
from news_services.services.base_news_service import BaseNewsService


logger = logging.getLogger("news_llm_service")


# ═══════════════════════════════════════════════════════════════════
#  System Prompt
# ═══════════════════════════════════════════════════════════════════


SYSTEM_PROMPT =  """你是专业金融量化分析师,
## 任务
对财经新闻列表做结构化分析，**严格按照输入顺序输出 JSON 数组**。

## 强制规则
1. 输入是 JSON 数组，输出必须是 JSON 数组，每个元素对应输入中的同一条新闻
2. 每个输出元素必须包含原始 id 字段（与输入 id 严格对应）
3. 只输出 JSON 数组，禁止任何额外文字、解释、注释、markdown 格式符
4. 未知字段填 null，字符串空值填 ""
5. 数字为数字类型，分数保留 2 位小数
6. 根据新闻内容推断最相关、最可能受影响的 **3-5 个具体个股**（A股/港股/美股代码或名称），填入 `ai_benefit_stocks`，用逗号分隔。若新闻完全不涉及任何公司或行业，则填空字符串。

## 每条输出字段（13个，含原始 id）
{
  "id": <整数>,
  "ai_interpretation": "200字内核心解读，必须包含：①事件实质 ②影响的具体行业/技术方向（如MLCC、玻璃存储、HBM、碳化硅等） ③影响逻辑（供需/价格/政策） ④时间维度（短期/中期/长期） ⑤量化预期（如有）",
  "ai_event_type": "财报/并购/政策/研发/诉讼/高管变动/战略合作/产能扩张/业务调整/风险事件/其他",
  "ai_impact_level": 1,
  "ai_impact_direction": 1,
  "ai_impact_direction_reason": "简短说明为何利好/中性/利空",
  "ai_risk_level": 1,
  "ai_benefit_sectors": "受益的细分行业/技术领域，优先填入具体技术名词（如MLCC、玻璃存储），再填入传统板块",
  "ai_benefit_stocks": "根据新闻推断的最相关个股（名称或代码），最多5个，逗号分隔",
  "ai_keywords": "3-6个关键词，逗号分隔",
  "sentiment": 0.0,
  "sentiment_label": 1,
  "is_official": 1,
  "is_breaking": 0,
  "ai_impact_duration": "短期/中期/长期",
  "ai_key_suppliers": "推断的关键供应商或合作伙伴，最多5个，逗号分隔",
  "ai_topic_tags": "主题标签，3-5个，逗号分隔（如：涨价周期、国产替代、政策利好）",
  "ai_related_indices": "关联指数，1-3个，逗号分隔（如：沪深300、科创50、中证白酒）"
}

## 字段详细说明
- ai_impact_level: 1=轻微 2=一般 3=中等 4=较大 5=重大（依据：是否改变供需格局、影响头部公司20%以上营收、引发价格剧烈波动）
- ai_impact_direction: 1=利好 0=中性 -1=利空
- ai_risk_level: 1=低 2=较低 3=中等 4=较高 5=高
- sentiment: -1.0(极度负面) ~ 1.0(极度正面)
- sentiment_label: 1=正面 0=中性 -1=负面
- is_official: 1=官方公告/监管披露/权威机构报告；0=媒体报道/自媒体
- is_breaking: 1=突发/今日重大事件；0=常规更新
- ai_impact_duration: 短期(1-4周) / 中期(1-3个月) / 长期(3个月以上)
- ai_key_suppliers: 新闻中明确提及或产业链上最相关的供应商/合作方（如“台积电”之于芯片设计公司）
- ai_topic_tags: 提炼事件的核心主题，用于后续分类聚合
- ai_related_indices: 该事件最可能影响的宽基或行业指数

## 个股推断原则
- 优先选择新闻中明确提到的公司；若未提到，则根据产业链关联度推断最可能受益/受损的龙头企业（例如MLCC新闻→风华高科、三环集团；猪肉价格下跌→牧原股份、温氏股份）。
- 避免罗列过多小市值或无关公司；宁可少而精。
- 若实在无法推断（如宏观数据无明确指向），填空字符串。

## 精细解读要求
- 识别细分技术/行业名词,（MLCC、玻璃存储、HBM、碳化硅、固态电池等），填入 `ai_benefit_sectors` 和 `ai_keywords`。
- 避免仅写“半导体”、“电子”等宽泛词。
- `ai_interpretation` 必须包含影响逻辑与时间维度。

## 示例
输入：[{"id":1001,"title":"村田制作所部分MLCC产线因地震停产","content":"全球MLCC龙头村田表示，其日本福井工厂因强震受损，预计恢复需3个月，影响车规级MLCC供应约15%全球产能。"}]
输出：[{"id":1001,"ai_interpretation":"村田MLCC产线停产3个月，影响全球15%车规级MLCC供给，短期供需紧张，国内MLCC厂商有望获得转单及涨价机会。预计相关产品价格上调5-10%。","ai_event_type":"风险事件","ai_impact_level":4,"ai_impact_direction":1,"ai_risk_level":3,"ai_benefit_sectors":"MLCC,被动元件,车规级电容","ai_benefit_stocks":"风华高科,三环集团,火炬电子","ai_keywords":"MLCC,地震停产,国产替代","sentiment":0.65,"sentiment_label":1,"is_official":0,"is_breaking":1,"ai_impact_duration":"短期","ai_key_suppliers":"村田制作所,太阳诱电,国巨","ai_topic_tags":"供给冲击,涨价预期,国产替代","ai_related_indices":"半导体指数,电子元器件指数"}]
## 输出前自检
- 是否包含全部18个字段？
- `ai_interpretation` 是否超过200字？
- 数字格式是否正确（保留2位小数）？
- `ai_impact_duration` 是否为“短期/中期/长期”之一？
"""

# ═══════════════════════════════════════════════════════════════════
#  字段校验规则
# ═══════════════════════════════════════════════════════════════════

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
    "ai_impact_duration":  (str,   True),
    "ai_key_suppliers":  (str,   True),
    "ai_topic_tags":  (str,   True),
    "ai_related_indices":  (str,   True),
}

_VALID_ENUMS: Dict[str, set] = {
    "ai_event_type": {
        "财报", "并购", "政策", "研发", "诉讼", "高管变动",
        "战略合作", "产能扩张", "业务调整", "风险事件", "其他",
    },
}


def _extract_json_array(text: str) -> list:
    """从 LLM 返回文本中提取 JSON 数组（兼容 markdown 包裹）"""
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl == -1:
            first_nl = len(text)
        text = text[first_nl + 1:]
        last_bt = text.rfind("```")
        if last_bt != -1:
            text = text[:last_bt]
        text = text.strip()

    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        text = text[bracket_start:bracket_end + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return []
    return parsed


def _validate_single(data: dict) -> dict:
    """类型转换 + 枚举校验 + 数值钳位"""
    cleaned = {}
    for field_name, (expected_type, _) in _EXPECTED_FIELDS.items():
        val = data.get(field_name)
        if val is None:
            cleaned[field_name] = None
            continue
        try:
            if expected_type == float:
                val = float(val)
            elif expected_type == int:
                val = int(float(val))
            elif expected_type == str:
                val = str(val).strip().replace("\x00", "")
                if not val:
                    cleaned[field_name] = None
                    continue
        except (ValueError, TypeError):
            cleaned[field_name] = None
            continue

        if expected_type == str and field_name in _VALID_ENUMS:
            if val not in _VALID_ENUMS[field_name]:
                cleaned[field_name] = None
                continue

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
#  LLM 批量调用（带重试）
# ═══════════════════════════════════════════════════════════════════

def _call_llm_batch(llm_client, news_batch: list) -> list:
    if llm_client is None:
        raise ValueError("LLM 客户端未初始化")
    if not hasattr(llm_client, "analyze_news_items"):
        raise AttributeError("LLM 客户端缺少 analyze_news_items 方法")
    return llm_client.analyze_news_items(news_batch)


def _call_llm_batch_with_retry(llm_client, news_batch: list) -> list:
    if llm_client is None:
        logger.warning("[LLM] 客户端未初始化，跳过分析")
        return []

    last_error = ""
    for attempt in range(1, LLM_MAX_RETRIES + 2):
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
        if attempt <= LLM_MAX_RETRIES:
            time.sleep(2)

    logger.error("[LLM] 重试后仍失败: %s | batch_size=%d", last_error, len(news_batch))
    return []


# ═══════════════════════════════════════════════════════════════════
#  服务类（含 8 线程引擎）
# ═══════════════════════════════════════════════════════════════════

class NewsLLMService(BaseNewsService):
    """
    LLM 新闻分析服务（合并原 NewsLLMAnalyzer）

    职责：
      - 启动/停止 8 线程 LLM 分析引擎
      - 查询引擎状态、待分析队列长度
    """

    def __init__(self):
        super().__init__(service_name="NewsLLMService")
        self._llm_client = None
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._initialized = False
        self._init_lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────
    #  LLM 客户端初始化
    # ─────────────────────────────────────────────────────────────

    def _init_llm(self):
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            try:
                from utils.llm import LLM
                self._llm_client = LLM()
                self._llm_client.set_news_analysis_config(
                    system_prompt=SYSTEM_PROMPT,
                    model=None,
                )
                self._initialized = True
                self.logger.info("[news_llm] LLM 客户端初始化完成（单例）")
            except Exception as e:
                self.logger.error("[news_llm] LLM 客户端初始化失败: %s", e)
                self._llm_client = None
                self._initialized = True

    # ─────────────────────────────────────────────────────────────
    #  线程主循环
    # ─────────────────────────────────────────────────────────────

    def _worker_loop(self, thread_id: int):
        self.logger.info("[news_llm] 线程 %d 启动", thread_id)
        while not self._stop_event.is_set():
            try:
                processed = self._process_once(thread_id)
                if processed == 0:
                    self._stop_event.wait(timeout=LLM_IDLE_WAIT)
            except Exception as e:
                self.logger.error("[news_llm] 线程 %d 异常（继续运行）: %s", thread_id, e)
                self._stop_event.wait(timeout=LLM_IDLE_WAIT)
        self.logger.info("[news_llm] 线程 %d 已停止", thread_id)

    def _process_once(self, thread_id: int) -> int:
        # Step 1: SPOP
        raw_items = pending_llm_spop(LLM_BATCH_SIZE)
        if not raw_items:
            return 0

        id_table_pairs = []
        for item in raw_items:
            news_id, table_name = _unpack_pending_item(item)
            if news_id is not None:
                id_table_pairs.append((news_id, table_name))

        if not id_table_pairs:
            return 0

        # Step 2: 读取 Redis 并过滤
        news_list = []
        for news_id, table_name in id_table_pairs:
            data = news_data_get(news_id, table_name)
            if data is None:
                self.logger.warning(
                    "[news_llm] 线程%d: news:data:%s:%d 不存在，跳过",
                    thread_id, table_name or "?", news_id,
                )
                continue

            if data.get("need_analyze", 1) == 0:
                continue
            ai_analyze_time = data.get("ai_analyze_time")
            if ai_analyze_time and str(ai_analyze_time).strip() not in ("", "None", "null"):
                continue

            news_list.append({
                "id":         news_id,
                "title":      (data.get("title") or "").strip(),
                "content":    (data.get("content") or "")[:2000],
                "source":     data.get("source", ""),
                "news_type":  data.get("news_type", ""),
                "table_name": data.get("table_name", table_name or ""),
                "_data":      data,
            })

        if not news_list:
            return 0

        # Step 3: LLM
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
        self.logger.info("[news_llm] 线程%d: 开始 LLM 分析 %d 条", thread_id, len(llm_input))
        llm_results = _call_llm_batch_with_retry(self._llm_client, llm_input)

        if not llm_results:
            self.logger.warning("[news_llm] 线程%d: LLM 返回为空，跳过本批次", thread_id)
            return 0

        # Step 4: 构建 id → result 映射
        id_to_result: Dict[int, dict] = {}
        for item in llm_results:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("id"))
                ai_data = {k: v for k, v in item.items() if k != "id"}
                if ai_data:
                    id_to_result[item_id] = ai_data
            except (ValueError, TypeError):
                continue

        # Step 5: 写回 Redis
        success_ids = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in news_list:
            news_id = item["id"]
            ai_result = id_to_result.get(news_id)
            if ai_result is None:
                continue

            updates = {
                **ai_result,
                "need_analyze":    0,
                "ai_analyze_time": now_str,
                "table_name":      item.get("table_name", ""),
            }
            if news_data_update(news_id, updates):
                success_ids.append(news_id)

        # Step 6: 推入下游队列（FinBERT 开启时推 pending_finbert，否则推 pending_persist）
        if success_ids:
            success_table_names = []
            for item in news_list:
                if item["id"] in success_ids:
                    table_name = item.get("table_name", "") or "unknown"
                    success_table_names.append(table_name)
            if FINBERT_ENABLED:
                pushed = pending_finbert_push_batch(success_ids, success_table_names)
                self.logger.info(
                    "[news_llm] 线程%d: 完成 | 取:%d 有效:%d 成功:%d 推入finbert:%d",
                    thread_id, len(id_table_pairs), len(news_list), len(success_ids), pushed,
                )
            else:
                pushed = pending_persist_push_batch(success_ids, success_table_names)
                self.logger.info(
                    "[news_llm] 线程%d: 完成 | 取:%d 有效:%d 成功:%d 推入persist:%d",
                    thread_id, len(id_table_pairs), len(news_list), len(success_ids), pushed,
                )

        return len(success_ids)

    # ─────────────────────────────────────────────────────────────
    #  对外接口
    # ─────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        try:
            self._init_llm()
            if not self._initialized or self._llm_client is None:
                return self.wrap_error("LLM 客户端未初始化")

            alive_count = sum(1 for t in self._threads if t.is_alive())
            if alive_count >= LLM_THREADS:
                self.logger.info("[news_llm] 后台线程已全部运行（%d线程），跳过", alive_count)
                return self.wrap_success(message=f"already running with {alive_count} threads")

            self._stop_event.clear()
            self._threads = []
            for i in range(LLM_THREADS):
                t = threading.Thread(
                    target=self._worker_loop,
                    args=(i + 1,),
                    name=f"news-llm-{i + 1}",
                    daemon=True,
                )
                t.start()
                self._threads.append(t)

            self.logger.info("[news_llm] %d 条 LLM 分析线程已启动", LLM_THREADS)
            return self.wrap_success(message=f"started with {LLM_THREADS} threads")
        except Exception as e:
            self.log_exception("启动 LLM 引擎", e)
            return self.wrap_error(f"启动失败: {e}")

    def stop(self) -> Dict[str, Any]:
        try:
            self._stop_event.set()
            for t in self._threads:
                if t.is_alive():
                    t.join(timeout=5)
            self._threads = []
            self.logger.info("[news_llm] 所有 LLM 线程已停止")
            return self.wrap_success(message="stopped")
        except Exception as e:
            self.log_exception("停止 LLM 引擎", e)
            return self.wrap_error(f"停止失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        alive_threads = [t.name for t in self._threads if t.is_alive()]
        return self.wrap_success(data={
            "initialized":         self._initialized,
            "num_threads":         LLM_THREADS,
            "alive_threads":       len(alive_threads),
            "thread_names":        alive_threads,
            "pending_llm_size":    pending_llm_size(),
            "pending_finbert_size": pending_finbert_size() if FINBERT_ENABLED else 0,
            "pending_persist_size": pending_persist_size(),
            "batch_size":          LLM_BATCH_SIZE,
            "idle_wait_seconds":   LLM_IDLE_WAIT,
            "finbert_enabled":     FINBERT_ENABLED,
            "mode":                "redis_string_set_list",
        })

    def get_pending_count(self) -> int:
        try:
            return pending_llm_size()
        except Exception as e:
            self.log_exception("获取 pending_llm_size", e)
            return 0


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_llm_service = NewsLLMService()
