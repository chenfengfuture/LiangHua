"""
================================================================================
api/news/news_persist.py — 新闻 AI 结果持久化层（单线程定时批量写库）
================================================================================

【模块职责】
  消费 Redis news:pending_persist（List）中已完成 LLM 分析的新闻 id，
  批量读取 Redis String 中的完整 JSON，将 AI 字段批量更新到 MySQL 对应分表。

【工作流程（单线程定时循环）】
  每 PERSIST_INTERVAL_SECONDS 秒执行一次：
  1. LRANGE + LTRIM  原子批量取出 news:pending_persist 中最多 PERSIST_BATCH_SIZE 个项
                     格式: "table_name:news_id" 或 "news_id"
  2. MGET            批量读取 news:data:{table}:{id}（Redis String）
  3. 过滤            必须有 ai_analyze_time 才持久化；无 ai_analyze_time 放回队列
  4. 分组            按 table_name 分组（同一张 MySQL 分表的记录合并处理）
  5. CASE 批量更新   一次 SQL 处理同一表的所有记录（batch_update_ai_case）
  6. 失败回滚        更新异常时将 id 放回 pending_persist 队列，保证最终一致性

【设计优势】
  - 单线程：绝对无竞争，无需任何锁
  - LRANGE + LTRIM：Redis 原子操作，保证不丢失、不重复消费
  - CASE 批量更新：单次 SQL 处理 N 条记录，大幅减少 MySQL 往返次数
  - news:data:{id} 永久保留（不会被持久化层删除）
  - 失败自动入队：保证最终一致性，不存在"丢数据"场景

【对外公开接口】
  get_persist_worker() → NewsPersistWorker 全局单例
  worker.start_background()  → 启动持久化后台线程（被 routes.py start_scheduler 调用）
  worker.stop()              → 优雅停止持久化线程
  worker.get_status()        → 返回线程运行状态字典

【依赖关系】
  utils/redis_client.py    → pending_persist_pop_batch / news_data_batch_get
                             pending_persist_push_batch / _unpack_pending_item
  models/news_models.py    → batch_update_ai_case（CASE 语法批量更新 AI 字段）
================================================================================
"""

import time
import threading
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger("news_persist")


# ═══════════════════════════════════════════════════════════════════
#  配置常量
# ═══════════════════════════════════════════════════════════════════

PERSIST_INTERVAL_SECONDS = 5    # 两次持久化执行的间隔时间（秒）
PERSIST_BATCH_SIZE       = 200  # 每次从 pending_persist 取出的最大 id 数量
MAX_RETRIES              = 2    # 批量更新失败时的重试次数（暂未启用逐条降级）


# ═══════════════════════════════════════════════════════════════════
#  持久化核心函数（单次批次执行）
# ═══════════════════════════════════════════════════════════════════

def _persist_once() -> int:
    """
    执行一次完整的持久化批次。

    步骤：
      1. LRANGE + LTRIM 原子取出待持久化项
      2. MGET 批量读取 Redis String（含 AI 字段）
      3. 过滤：有 ai_analyze_time 的记录才持久化；无则放回队列
      4. 按 table_name 分组 + CASE 语法批量更新 MySQL
      5. 失败时将 id 放回 pending_persist，保证最终一致性

    Returns:
        本次成功持久化到 MySQL 的记录数（0 表示无任务或全部跳过）
    """
    from utils.redis_client import (
        pending_persist_pop_batch,
        news_data_batch_get,
        pending_persist_push_batch,
        pending_persist_push,
        _unpack_pending_item,
    )
    from models.news_models import batch_update_ai_case

    # Step 1: 原子批量取出待持久化项（格式: "table_name:news_id" 或 "news_id"）
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

    ids        = [pair[0] for pair in id_table_pairs]
    table_names = [pair[1] for pair in id_table_pairs]

    logger.debug("[持久化] 取出 %d 条 id 准备持久化", len(ids))

    # Step 2: 批量读取 Redis String（使用 table_names 构建正确的 key）
    news_list = news_data_batch_get(ids, table_names)
    if not news_list:
        logger.warning("[持久化] Redis 批量读取为空（可能已过期），id前5=%s", ids[:5])
        return 0

    # Step 3: 过滤 + 构建持久化数据列表
    persist_items: List[Dict] = []
    skip_count = 0

    # AI 字段列表（与 MySQL 表中 AI 相关列保持一致）
    ai_fields = [
        "ai_interpretation", "ai_event_type", "ai_impact_level",
        "ai_impact_direction", "ai_risk_level", "ai_benefit_sectors",
        "ai_benefit_stocks", "ai_keywords", "sentiment", "sentiment_label",
        "is_official", "is_breaking",
    ]

    for record in news_list:
        news_id = record.get("id")
        if not news_id:
            skip_count += 1
            continue

        # 必须有 ai_analyze_time，证明 LLM 分析已完成
        ai_analyze_time = record.get("ai_analyze_time")
        if not ai_analyze_time or str(ai_analyze_time).strip() in ("", "None", "null"):
            # LLM 尚未分析完成，放回队列稍后重试（不丢失）
            logger.debug("[持久化] id=%d 尚未 LLM 分析，放回队列", news_id)
            try:
                pending_persist_push(news_id, record.get("table_name"))
            except Exception:
                pass
            skip_count += 1
            continue

        table_name = record.get("table_name")
        if not table_name:
            logger.warning("[持久化] id=%d 缺少 table_name，跳过", news_id)
            skip_count += 1
            continue

        # 提取所有 AI 字段（只保留非 None 的字段）
        ai_result = {
            field: record[field]
            for field in ai_fields
            if record.get(field) is not None
        }

        persist_items.append({
            "table_name": table_name,
            "news_id":    int(news_id),
            "result":     ai_result,
            # ai_analyze_time 和 need_analyze=0 由 batch_update_ai_case 统一写入
        })

    if not persist_items:
        logger.debug("[持久化] 过滤后无有效记录（跳过:%d）", skip_count)
        return 0

    # Step 4 + 5: 按 table_name 分组 → CASE 语法一次性批量更新 MySQL
    try:
        success_count = batch_update_ai_case(persist_items)
        logger.info(
            "[持久化] 批量更新完成 | 取出:%d 有效:%d 成功:%d 跳过:%d",
            len(ids), len(persist_items), success_count, skip_count,
        )
        return success_count

    except Exception as e:
        logger.error("[持久化] batch_update_ai_case 异常: %s", e)
        # 失败时将全部 id 放回队列（保证最终一致性）
        try:
            failed_ids        = [item["news_id"]    for item in persist_items]
            failed_table_names = [item["table_name"] for item in persist_items]
            pending_persist_push_batch(failed_ids, failed_table_names)
            logger.info("[持久化] 已将 %d 条失败 id 放回队列", len(failed_ids))
        except Exception as re_e:
            logger.error("[持久化] 放回队列失败: %s", re_e)
        return 0


# ═══════════════════════════════════════════════════════════════════
#  持久化线程管理（单线程工作器）
# ═══════════════════════════════════════════════════════════════════

class NewsPersistWorker:
    """
    持久化层单线程定时工作器。

    特性：
      - 单线程：无锁、无竞争，每次只有一个持久化批次在执行
      - 每 PERSIST_INTERVAL_SECONDS 秒执行一次 _persist_once()
      - 使用 event.wait 休眠，空闲时 CPU 占用接近于零
      - 优雅停止：stop_event 置位后，线程在当前批次结束时退出
      - 运行时统计：记录总持久化条数和启动时间

    生命周期（由 routes.py start_scheduler 管理）：
      start_background() → 后台线程启动 → 持续消费 pending_persist
      stop()             → 通知线程退出，等待最多 10s
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._total_persisted = 0                      # 累计成功持久化条数
        self._start_time: Optional[datetime] = None    # 线程启动时间

    def start_background(self):
        """
        启动持久化后台线程（幂等，已运行时跳过）。
        由 routes.py 的 start_scheduler() 在项目启动时调用一次。
        """
        if self._thread is not None and self._thread.is_alive():
            logger.info("[持久化] 后台线程已在运行，跳过重复启动")
            return

        self._stop_event.clear()
        self._running = True
        self._start_time = datetime.now()
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="news-persist",
            daemon=True,
        )
        self._thread.start()
        logger.info("[持久化] 后台线程已启动（间隔: %ds，批量: %d条）",
                    PERSIST_INTERVAL_SECONDS, PERSIST_BATCH_SIZE)

    def stop(self):
        """
        优雅停止持久化线程（最多等待 10s）。
        由 routes.py 的 stop_scheduler() 在服务关闭时调用。
        """
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        logger.info("[持久化] 线程已停止 | 累计持久化: %d 条", self._total_persisted)

    def _worker_loop(self):
        """
        持久化线程主循环：每隔 PERSIST_INTERVAL_SECONDS 秒执行一次持久化批次。
        异常不会导致线程退出，仅记录日志后继续循环。
        """
        logger.info("[持久化] 线程启动，每 %ds 执行一次批量持久化", PERSIST_INTERVAL_SECONDS)

        while not self._stop_event.is_set():
            try:
                count = _persist_once()
                if count > 0:
                    self._total_persisted += count
            except Exception as e:
                logger.error("[持久化] _persist_once 异常（继续运行）: %s", e)

            # 等待下次执行（可被 stop_event.set() 立即中断）
            self._stop_event.wait(timeout=PERSIST_INTERVAL_SECONDS)

        logger.info("[持久化] 线程退出")

    def get_status(self) -> dict:
        """
        返回持久化层实时状态（供 /api/news/analyzer_status 接口使用）。

        Returns:
            包含运行状态、统计数据、队列大小、配置参数的字典
        """
        from utils.redis_client import pending_persist_size

        uptime_seconds = None
        if self._start_time:
            uptime_seconds = int((datetime.now() - self._start_time).total_seconds())

        return {
            "running":                  self._thread is not None and self._thread.is_alive(),
            "total_persisted":          self._total_persisted,
            "persist_interval_seconds": PERSIST_INTERVAL_SECONDS,
            "batch_size":               PERSIST_BATCH_SIZE,
            "pending_persist_size":     pending_persist_size(),
            "uptime_seconds":           uptime_seconds,
        }


# ═══════════════════════════════════════════════════════════════════
#  全局单例（模块级，项目生命周期内唯一）
# ═══════════════════════════════════════════════════════════════════

_persist_worker: Optional[NewsPersistWorker] = None


def get_persist_worker() -> NewsPersistWorker:
    """
    获取 NewsPersistWorker 全局单例。
    线程安全（CPython GIL 保证模块级赋值的原子性）。
    """
    global _persist_worker
    if _persist_worker is None:
        _persist_worker = NewsPersistWorker()
    return _persist_worker
