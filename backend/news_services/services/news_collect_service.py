"""
news_services/services/news_collect_service.py — 新闻采集服务

封装原 utils/akshare.py 的采集编排逻辑：
  - 频率控制
  - 增量时间范围计算
  - 调用数据源（sources/）
  - 清洗、入库、Redis 推送、WS 广播
  - APScheduler 定时调度

不修改任何采集的实际抓取实现，仅做编排层封装。
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from models.news_models import (
    ensure_table_exists,
    get_table_name,
    insert_news_with_content_hash,
)
from utils.redis_client_compat import (
    get_last_collect_time,
    news_data_set,
    pending_llm_add_batch,
    seconds_since_last_collect,
    set_last_collect_time,
)
from utils.websocket_manager import ws_manager

from news_services.config import (
    COLLECT_INTERVAL,
    COLLECT_TIMEOUT,
    COLLECT_WORKERS,
)
from news_services.services.base_news_service import BaseNewsService
from news_services.sources import (
    fetch_cctv,
    fetch_cls,
    fetch_company,
    fetch_global,
    fetch_report,
)
from news_services.utils import TIME_FMT, clean_news_rows


logger = logging.getLogger("news_collect_service")


class NewsCollectService(BaseNewsService):
    """
    新闻采集服务（5 大板块 + APScheduler 定时调度）
    """

    # 数据源函数映射
    _FETCH_MAP = {
        "company": fetch_company,
        "cls": fetch_cls,
        "global": fetch_global,
        "cctv": fetch_cctv,
        "report": fetch_report,
    }

    def __init__(self):
        super().__init__(service_name="NewsCollectService")
        self._scheduler: Optional[BackgroundScheduler] = None

    # ─────────────────────────────────────────────────────────────
    #  Redis 增量时间范围
    # ─────────────────────────────────────────────────────────────

    def _get_incremental_range(self, news_type: str) -> tuple:
        """
        根据 Redis 中上次采集时间计算增量采集时间范围。

        兜底规则：
          - global               → 当前时间 -24 小时
          - 其他（company/cls/report） → 当天 00:00:00
          - cctv                 → 由 fetch_cctv 内部独立控制
        """
        now = datetime.now()
        last_str = get_last_collect_time(news_type)

        if last_str:
            try:
                last_dt = datetime.strptime(last_str, TIME_FMT)
                start_time = last_dt + timedelta(seconds=1)
                return start_time, now
            except ValueError:
                self.logger.warning(
                    f"[{news_type}] Redis 时间解析失败: {last_str}，进入兜底"
                )

        if news_type == "global":
            start_time = now - timedelta(hours=24)
            self.logger.info(
                f"[{news_type}] 初始化兜底 → 从 {start_time.strftime(TIME_FMT)} 开始（-24h）"
            )
        else:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self.logger.info(
                f"[{news_type}] 初始化兜底 → 从 {start_time.strftime(TIME_FMT)} 开始（当天 00:00:00）"
            )

        return start_time, now

    # ─────────────────────────────────────────────────────────────
    #  Redis 写入 + pending_llm 推送
    # ─────────────────────────────────────────────────────────────

    def _push_to_redis(self, news_type: str, year_month: str, rows: list) -> int:
        """
        基于 content_hash 去重 → MySQL → Redis news:data:{id} → news:pending_llm
        """
        if not rows:
            return 0

        try:
            inserted_records = insert_news_with_content_hash(news_type, year_month, rows)
            if not inserted_records:
                self.logger.info(f"[{news_type}] 无有效入库记录（可能全部重复）")
                return 0

            pending_ids = []
            written = 0

            for record in inserted_records:
                news_id = record.get("id")
                if not news_id:
                    continue

                redis_data = {
                    **record,
                    "table_name": get_table_name(news_type, year_month),
                    "news_type": record.get("news_type", news_type),
                }
                if isinstance(redis_data.get("publish_time"), datetime):
                    redis_data["publish_time"] = redis_data["publish_time"].strftime(TIME_FMT)
                if isinstance(redis_data.get("collect_time"), datetime):
                    redis_data["collect_time"] = str(redis_data["collect_time"])

                if news_data_set(news_id, redis_data):
                    written += 1
                    if record.get("need_analyze", 1) == 1:
                        pending_ids.append(news_id)

            if pending_ids:
                table_names = [get_table_name(news_type, year_month)] * len(pending_ids)
                pushed = pending_llm_add_batch(pending_ids, table_names)
                self.logger.info(
                    f"[{news_type}] 去重后唯一:{written} | news:data:{written} | pending_llm:{pushed}"
                )
            else:
                self.logger.info(
                    f"[{news_type}] 去重后唯一:{written} | news:data:{written} | 无待分析"
                )

            return written

        except Exception as e:
            self.log_exception(f"{news_type} _push_to_redis", e)
            return 0

    # ─────────────────────────────────────────────────────────────
    #  WS 推送
    # ─────────────────────────────────────────────────────────────

    def _push_to_ws(self, news_type: str, rows: list) -> int:
        """采集入库后通过 WebSocket 广播原始新闻到 news 频道。"""
        try:
            items = []
            for row in rows:
                if row.get("need_analyze") == 1:
                    items.append({
                        "title": row.get("title", ""),
                        "content": (row.get("content", "") or "")[:200],
                        "url": row.get("url"),
                        "source": row.get("source", ""),
                        "news_type": news_type,
                        "publish_time": str(row.get("publish_time", "")),
                    })

            if not items:
                return 0

            payload = {
                "type": "news_collected",
                "news_type": news_type,
                "count": len(items),
                "items": items,
                "timestamp": datetime.now().strftime(TIME_FMT),
            }
            ws_manager.broadcast_sync("news", payload)
            self.logger.info(f"[ws] 推送 {news_type} 原始新闻 {len(items)} 条")
            return len(items)
        except Exception as e:
            self.log_exception(f"WS 推送 {news_type}", e)
            return 0

    # ─────────────────────────────────────────────────────────────
    #  单板块采集（模板方法）
    # ─────────────────────────────────────────────────────────────

    def _collect_one(self, news_type: str) -> int:
        """
        单板块采集（模板方法）：频率控制 → 增量范围 → 抓取 → 清洗 → 入库 → 推送
        """
        try:
            # 频率控制（cctv 由内部独立控制，不在外层判断）
            if news_type != "cctv":
                interval = COLLECT_INTERVAL.get(news_type, 3600)
                elapsed = seconds_since_last_collect(news_type)
                if elapsed is not None and elapsed < interval:
                    self.logger.info(
                        f"[{news_type}] 跳过: 距上次采集 {elapsed:.0f}s < {interval}s"
                    )
                    return 0

            start_time, end_time = self._get_incremental_range(news_type)

            fetch_func = self._FETCH_MAP.get(news_type)
            if not fetch_func:
                self.logger.warning(f"[{news_type}] 未注册的板块")
                return 0

            rows = fetch_func(start_time, end_time)
            if not rows:
                # global / report 无数据也要更新时间戳（保持原行为）
                if news_type in ("global", "report"):
                    set_last_collect_time(news_type)
                self.logger.info(f"[{news_type}] 无增量数据")
                return 0

            rows = clean_news_rows(rows)
            for row in rows:
                row.pop("_skip_reason", None)

            year_month = date.today().strftime("%Y%m")
            ensure_table_exists(news_type, year_month)
            count = self._push_to_redis(news_type, year_month, rows)
            set_last_collect_time(news_type)

            self.logger.info(f"[{news_type}] 完成 | 拉取:{len(rows)} Redis写入:{count}")
            if count > 0:
                self._push_to_ws(news_type, rows)
            return count

        except Exception as e:
            self.log_exception(f"{news_type} 采集", e)
            return 0

    # ─────────────────────────────────────────────────────────────
    #  对外接口
    # ─────────────────────────────────────────────────────────────

    def collect_section(self, section: str) -> Dict[str, Any]:
        """
        采集指定板块（供 fetch_routes 按需触发）
        """
        if section not in self._FETCH_MAP:
            return self.wrap_error(f"未知板块: {section}", data={"count": 0})

        count = self._collect_one(section)
        return self.wrap_success(data={"section": section, "count": count})

    def collect_all(self) -> Dict[str, Any]:
        """
        5 大板块并行采集（纯采集，不含 LLM 分析）

        Returns:
            {success, data: {"company": n, "cls": n, ...}, message}
        """
        results: Dict[str, int] = {}
        results_lock = threading.Lock()

        def _run(section: str):
            try:
                count = self._collect_one(section)
                with results_lock:
                    results[section] = count
            except Exception as e:
                self.log_exception(f"{section} 线程", e)
                with results_lock:
                    results[section] = 0

        sections = list(self._FETCH_MAP.keys())
        self.logger.info(f"[news_collect] 启动 {COLLECT_WORKERS} 线程并行采集...")

        executor = ThreadPoolExecutor(max_workers=COLLECT_WORKERS)
        try:
            futures = [executor.submit(_run, s) for s in sections]
            for future in futures:
                try:
                    future.result(timeout=COLLECT_TIMEOUT)
                except Exception as e:
                    self.log_exception("线程等待", e)
        finally:
            # wait=False 防止卡住的线程阻塞整个任务
            executor.shutdown(wait=False)

        total = sum(results.values())
        self.logger.info(f"[news_collect] 完成: {results}, 共 {total} 条")
        return self.wrap_success(data=results, message=f"采集完成 共{total}条")

    # ─────────────────────────────────────────────────────────────
    #  生命周期：APScheduler 定时调度
    # ─────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        """
        启动 APScheduler 定时采集（每 3 分钟一次，内部根据板块频率自动跳过）
        """
        if self._scheduler is not None:
            self.logger.info("[news_collect] 调度器已在运行，跳过")
            return self.wrap_success(message="scheduler already running")

        self._scheduler = BackgroundScheduler()

        def _task():
            try:
                # 给单次采集总时间设上限，防止卡住影响后续调度
                res = self.collect_all()
                data = res.get("data") or {}
                total = sum(v for v in data.values() if isinstance(v, int))
                if total > 0:
                    self.logger.info(f"[news_collect] 定时采集完成: {data} 共{total}条")
            except Exception as e:
                self.log_exception("定时采集", e)

        self._scheduler.add_job(
            _task,
            trigger=CronTrigger(minute="*/3"),
            id="news_collector",
            name="新闻定时采集",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()
        self.logger.info("[news_collect] 定时采集任务已启动（每 3 分钟）")
        return self.wrap_success(message="scheduler started")

    def stop(self) -> Dict[str, Any]:
        """停止 APScheduler"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            self.logger.info("[news_collect] 定时采集已停止")
        return self.wrap_success(message="scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """采集服务状态"""
        return self.wrap_success(data={
            "scheduler_running": self._scheduler is not None,
            "interval_config": COLLECT_INTERVAL,
            "workers": COLLECT_WORKERS,
        })


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_collect_service = NewsCollectService()
