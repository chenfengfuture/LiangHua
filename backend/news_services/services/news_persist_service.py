"""
news_services/services/news_persist_service.py — 新闻持久化服务

新闻 AI 结果持久化层（从原 api/news/news_persist.py 整合迁移）。
消费 Redis news:pending_persist（List）中已完成 LLM 分析的新闻 id，
批量读取 Redis String 中的完整 JSON，将 AI 字段批量更新到 MySQL 对应分表。

【工作流程】（单线程定时循环，每 PERSIST_INTERVAL 秒一次）
  1. LRANGE + LTRIM 原子批量取出 pending_persist 最多 PERSIST_BATCH_SIZE 个项
  2. MGET 批量读取 news:data:{table}:{id}
  3. 过滤：必须有 ai_analyze_time 才持久化；无 ai_analyze_time 放回队列
  4. 按 table_name 分组
  5. CASE 语法批量 UPDATE MySQL（一次 SQL 处理同一表所有记录）
  6. 失败时将 id 放回 pending_persist 队列，保证最终一致性

【设计优势】
  - 单线程：绝对无竞争，无需任何锁
  - LRANGE + LTRIM：Redis 原子操作，保证不丢失、不重复消费
  - CASE 批量更新：单次 SQL 处理 N 条记录，大幅减少 MySQL 往返次数
  - news:data:{id} 永久保留（不会被持久化层删除）
  - 失败自动入队：保证最终一致性，不存在"丢数据"场景
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.redis_client_compat import pending_finbert_size, pending_persist_size

from news_services.config import FINBERT_ENABLED, PERSIST_BATCH_SIZE, PERSIST_INTERVAL
from news_services.services.base_news_service import BaseNewsService


logger = logging.getLogger("news_persist_service")


# ═══════════════════════════════════════════════════════════════════
#  AI 字段列表（与 MySQL 表中 AI 相关列保持一致）
# ═══════════════════════════════════════════════════════════════════

_AI_FIELDS = [
    # LLM 输出（12 字段）
    "ai_interpretation", "ai_event_type", "ai_impact_level",
    "ai_impact_direction", "ai_risk_level", "ai_benefit_sectors",
    "ai_benefit_stocks", "ai_keywords", "sentiment", "sentiment_label",
    "is_official", "is_breaking",
    # FinBERT
    "title_sentiment", "title_sentiment_label",
    "sentiment_confidence", "sentiment_volatility",
]


# ═══════════════════════════════════════════════════════════════════
#  持久化批次执行函数
# ═══════════════════════════════════════════════════════════════════

def _persist_once() -> int:
    """
    执行一次完整的持久化批次。

    Returns:
        本次成功持久化到 MySQL 的记录数（0 表示无任务或全部跳过）
    """
    from models.news_models import batch_update_ai_case
    from utils.redis_client_compat import (
        _unpack_pending_item,
        news_data_batch_get,
        pending_finbert_push,
        pending_persist_pop_batch,
        pending_persist_push,
        pending_persist_push_batch,
    )

    # Step 1: 原子批量取出（"table:news_id" 或 "news_id"）
    raw_items = pending_persist_pop_batch(PERSIST_BATCH_SIZE)
    if not raw_items:
        return 0

    # 解包为 (news_id, table_name) 列表
    id_table_pairs: List[tuple] = []
    for item in raw_items:
        news_id, table_name = _unpack_pending_item(item)
        if news_id is not None:
            id_table_pairs.append((news_id, table_name))

    if not id_table_pairs:
        return 0

    ids = [pair[0] for pair in id_table_pairs]
    table_names = [pair[1] for pair in id_table_pairs]

    logger.debug("[持久化] 取出 %d 条 id 准备持久化", len(ids))

    # Step 2: 批量读取 Redis String
    news_list = news_data_batch_get(ids, table_names)
    if not news_list:
        logger.warning("[持久化] Redis 批量读取为空，id前5=%s", ids[:5])
        return 0

    # Step 3: 过滤 + 构建持久化数据列表
    persist_items: List[Dict] = []
    skip_count = 0

    for record in news_list:
        news_id = record.get("id")
        if not news_id:
            skip_count += 1
            continue

        ai_analyze_time = record.get("ai_analyze_time")
        if not ai_analyze_time or str(ai_analyze_time).strip() in ("", "None", "null"):
            # LLM 未分析完成，放回 persist 队列稍后重试
            logger.debug("[持久化] id=%d 尚未 LLM 分析，放回队列", news_id)
            try:
                pending_persist_push(news_id, record.get("table_name"))
            except Exception:
                pass
            skip_count += 1
            continue

        # 启用 FinBERT 时：必须等 FinBERT 完成（sentiment_confidence 有值）才能持久化
        if FINBERT_ENABLED:
            sc = record.get("sentiment_confidence")
            if sc is None or str(sc).strip() in ("", "None", "null"):
                logger.debug("[持久化] id=%d 尚未 FinBERT 分析，放回 pending_finbert", news_id)
                try:
                    pending_finbert_push(news_id, record.get("table_name"))
                except Exception:
                    pass
                skip_count += 1
                continue

        table_name = record.get("table_name")
        if not table_name:
            logger.warning("[持久化] id=%d 缺少 table_name，跳过", news_id)
            skip_count += 1
            continue

        ai_result = {
            field: record[field]
            for field in _AI_FIELDS
            if record.get(field) is not None
        }

        persist_items.append({
            "table_name": table_name,
            "news_id":    int(news_id),
            "result":     ai_result,
        })

    if not persist_items:
        logger.debug("[持久化] 过滤后无有效记录（跳过:%d）", skip_count)
        return 0

    # Step 4 + 5: 按 table_name 分组 → CASE 批量更新
    try:
        success_count = batch_update_ai_case(persist_items)
        logger.info(
            "[持久化] 批量更新完成 | 取出:%d 有效:%d 成功:%d 跳过:%d",
            len(ids), len(persist_items), success_count, skip_count,
        )
        return success_count
    except Exception as e:
        logger.error("[持久化] batch_update_ai_case 异常: %s", e)
        # 失败回滚到队列
        try:
            failed_ids = [item["news_id"] for item in persist_items]
            failed_table_names = [item["table_name"] for item in persist_items]
            pending_persist_push_batch(failed_ids, failed_table_names)
            logger.info("[持久化] 已将 %d 条失败 id 放回队列", len(failed_ids))
        except Exception as re_e:
            logger.error("[持久化] 放回队列失败: %s", re_e)
        return 0


# ═══════════════════════════════════════════════════════════════════
#  服务类（单线程定时工作器）
# ═══════════════════════════════════════════════════════════════════

class NewsPersistService(BaseNewsService):
    """
    新闻持久化服务（合并原 NewsPersistWorker）

    职责：
      - 启动/停止 1 线程持久化（每 PERSIST_INTERVAL 秒批量）
      - 查询状态、待持久化队列长度

    特性：
      - 单线程：无锁、无竞争，每次只有一个持久化批次在执行
      - 使用 event.wait 休眠，空闲时 CPU 占用接近于零
      - 优雅停止：stop_event 置位后，线程在当前批次结束时退出
      - 运行时统计：记录总持久化条数和启动时间
    """

    def __init__(self):
        super().__init__(service_name="NewsPersistService")
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._total_persisted = 0
        self._start_time: Optional[datetime] = None

    # ─────────────────────────────────────────────────────────────
    #  线程主循环
    # ─────────────────────────────────────────────────────────────

    def _worker_loop(self):
        self.logger.info("[news_persist] 线程启动，每 %ds 执行一次批量持久化", PERSIST_INTERVAL)
        while not self._stop_event.is_set():
            try:
                count = _persist_once()
                if count > 0:
                    self._total_persisted += count
            except Exception as e:
                self.logger.error("[news_persist] _persist_once 异常（继续运行）: %s", e)
            self._stop_event.wait(timeout=PERSIST_INTERVAL)
        self.logger.info("[news_persist] 线程退出")

    # ─────────────────────────────────────────────────────────────
    #  对外接口
    # ─────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        try:
            if self._thread is not None and self._thread.is_alive():
                self.logger.info("[news_persist] 后台线程已在运行，跳过")
                return self.wrap_success(message="already running")

            self._stop_event.clear()
            self._running = True
            self._start_time = datetime.now()
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="news-persist",
                daemon=True,
            )
            self._thread.start()
            self.logger.info(
                "[news_persist] 持久化线程已启动（间隔: %ds，批量: %d条）",
                PERSIST_INTERVAL, PERSIST_BATCH_SIZE,
            )
            return self.wrap_success(
                message=f"started interval={PERSIST_INTERVAL}s batch={PERSIST_BATCH_SIZE}"
            )
        except Exception as e:
            self.log_exception("启动持久化", e)
            return self.wrap_error(f"启动失败: {e}")

    def stop(self) -> Dict[str, Any]:
        try:
            self._stop_event.set()
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=10)
            self._thread = None
            self.logger.info(
                "[news_persist] 线程已停止 | 累计持久化: %d 条", self._total_persisted
            )
            return self.wrap_success(message="stopped")
        except Exception as e:
            self.log_exception("停止持久化", e)
            return self.wrap_error(f"停止失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        uptime_seconds = None
        if self._start_time:
            uptime_seconds = int((datetime.now() - self._start_time).total_seconds())

        return self.wrap_success(data={
            "running":                  self._thread is not None and self._thread.is_alive(),
            "total_persisted":          self._total_persisted,
            "persist_interval_seconds": PERSIST_INTERVAL,
            "batch_size":               PERSIST_BATCH_SIZE,
            "pending_persist_size":     pending_persist_size(),
            "pending_finbert_size":     pending_finbert_size() if FINBERT_ENABLED else 0,
            "finbert_enabled":          FINBERT_ENABLED,
            "uptime_seconds":           uptime_seconds,
        })

    def get_pending_count(self) -> int:
        try:
            return pending_persist_size()
        except Exception as e:
            self.log_exception("获取 pending_persist_size", e)
            return 0


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_persist_service = NewsPersistService()
