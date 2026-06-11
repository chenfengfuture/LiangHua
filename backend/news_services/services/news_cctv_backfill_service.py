"""
news_services/services/news_cctv_backfill_service.py — CCTV 历史数据补全服务

职责：
  - 项目启动后自动扫描 news_data 数据库中 CCTV 新闻的日期覆盖情况
  - 找出缺失的历史日期（从 7 天前到昨天），逐日回补
  - 不对当天数据进行补采
  - 不修改现有采集流程，独立运行

健壮性设计：
  - Redis 持久化回补标记，避免重复扫描
  - 线程锁防止并发执行
  - 单日期失败自动重试 1 次
  - 最大执行时间兜底
  - 每日期之间间隔 2 秒防限流
"""

import logging
import time
import threading
from datetime import date, datetime, timedelta
from typing import Set

from models.news_models import ensure_table_exists, insert_news_with_content_hash
from utils.redis_client_compat import news_data_set
from utils.db import get_news_cursor

logger = logging.getLogger("CCTVBackfillService")

# ── 常量配置 ──────────────────────────────────────────────────────
# 回补窗口：最多补最近 N 天
BACKFILL_DAYS = 7
# 单日期采集超时（秒）
FETCH_TIMEOUT = 120
# 日期间间隔（秒，防限流）
INTERVAL_SECONDS = 2
# 失败重试次数
MAX_RETRIES = 1
# 总回补超时（秒，兜底防止无限运行）
TOTAL_TIMEOUT = 600  # 10 分钟
# Redis key：记录最近回补到的日期（格式 YYYY-MM-DD）
_CCTV_BACKFILL_MARKER_KEY = "news:cctv_backfill_marker"

# ── 运行时状态 ────────────────────────────────────────────────────
_backfill_lock = threading.Lock()
_backfill_started = False


def _get_backfill_marker() -> date | None:
    """读取 Redis 中最近回补到的日期"""
    try:
        from utils.redis_client_compat import _get_client
        r = _get_client()
        if not r:
            return None
        val = r.get(_CCTV_BACKFILL_MARKER_KEY)
        if val:
            return date.fromisoformat(val.decode())
    except Exception:
        pass
    return None


def _set_backfill_marker(d: date):
    """在 Redis 中记录最近回补到的日期（7 天过期）"""
    try:
        from utils.redis_client_compat import _get_client
        r = _get_client()
        if r:
            r.set(_CCTV_BACKFILL_MARKER_KEY, d.isoformat(), ex=86400 * 7)
    except Exception:
        pass


def _get_existing_cctv_dates() -> Set[date]:
    """查询 news_data 库中所有 CCTV 新闻表的日期集合"""
    dates: set = set()
    try:
        with get_news_cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'news_cctv_%'")
            tables_raw = cur.fetchall() or []
            tables = []
            for row in tables_raw:
                if isinstance(row, dict):
                    val = list(row.values())[0]
                elif isinstance(row, (list, tuple)):
                    val = row[0]
                else:
                    val = str(row)
                tables.append(val)

            for tbl in tables:
                cur.execute(
                    f"SELECT DISTINCT DATE(publish_time) AS d "
                    f"FROM `{tbl}` WHERE publish_time IS NOT NULL"
                )
                for row in cur.fetchall() or []:
                    d = row.get("d") if isinstance(row, dict) else row[0]
                    if d:
                        if isinstance(d, date):
                            dates.add(d)
                        else:
                            dates.add(date.fromisoformat(str(d)[:10]))
    except Exception as e:
        logger.warning("[cctv_backfill] 查询已有日期失败: %s", e)
    return dates


def _backfill_date(target_date: date) -> int:
    """
    回补单日 CCTV 数据，返回写入条数。

    包含重试逻辑：如果首次失败，自动重试 1 次。
    """
    from news_services.sources.cctv import _do_fetch

    date_str = target_date.strftime("%Y%m%d")
    logger.info("[cctv_backfill] 开始回补: %s", date_str)

    # 带重试的采集
    rows = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            rows = _do_fetch(date_str)
            break  # 成功则跳出重试
        except Exception as e:
            logger.warning("[cctv_backfill] %s 采集失败 (第%d次): %s",
                           date_str, attempt + 1, e)
            if attempt < MAX_RETRIES:
                time.sleep(5)

    if not rows:
        logger.info("[cctv_backfill] %s 无数据，跳过", date_str)
        return 0

    try:
        # 复用现有清洗流程
        from news_services.utils import clean_news_rows
        rows = clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
            row.pop("cache_key", None)

        if not rows:
            logger.info("[cctv_backfill] %s 清洗后无可用数据", date_str)
            return 0

        year_month = date_str[:6]
        ensure_table_exists("cctv", year_month)
        inserted = insert_news_with_content_hash("cctv", year_month, rows)

        # 写入 Redis news:data
        write_count = 0
        for record in inserted or []:
            news_id = record.get("id")
            if news_id:
                news_data_set(news_id, record)
                write_count += 1

        logger.info("[cctv_backfill] %s 完成 | 获取:%d 入库:%d Redis:%d",
                    date_str, len(rows), len(inserted or []), write_count)
        return write_count

    except Exception as e:
        logger.warning("[cctv_backfill] %s 入库异常: %s", date_str, e)
        return 0


def _run_backfill():
    """
    扫描并回补缺失日期。

    执行策略：
      1. 检查 Redis 中最近回补标记 → 跳过已补区间
      2. 查询数据库已有日期
      3. 从昨天往前扫描，发现缺失就补
      4. 每日期间隔 2 秒防限流
      5. 完成后更新 Redis 标记
      6. 总执行时间超过 TOTAL_TIMEOUT 自动退出
    """
    # 防止并发
    if not _backfill_lock.acquire(blocking=False):
        logger.info("[cctv_backfill] 已有回补任务在运行，跳过")
        return

    try:
        start_ts = time.time()
        today = date.today()

        # 步骤 1: 检查 Redis 标记
        marker = _get_backfill_marker()
        if marker:
            logger.info("[cctv_backfill] 上次回补到 %s，跳过已补区间", marker)

        # 步骤 2: 查询已有数据
        existing = _get_existing_cctv_dates()
        logger.info("[cctv_backfill] 已有 %d 天 CCTV 数据，扫描 %d 天内缺失...",
                    len(existing), BACKFILL_DAYS)

        # 步骤 3: 逐日扫描
        total_missing = 0
        total_ok = 0
        for offset in range(1, BACKFILL_DAYS + 1):
            # 检查总超时
            if time.time() - start_ts > TOTAL_TIMEOUT:
                logger.warning("[cctv_backfill] 执行超时 %ds，提前退出", TOTAL_TIMEOUT)
                break

            d = today - timedelta(days=offset)

            # 跳过标记之后（已补过）
            if marker and d <= marker:
                logger.debug("[cctv_backfill] %s 已在标记 %s 之前，跳过", d, marker)
                continue

            # 跳过已有数据
            if d in existing:
                logger.debug("[cctv_backfill] %s 已有数据，跳过", d)
                continue

            total_missing += 1
            count = _backfill_date(d)
            if count > 0:
                total_ok += 1

            # 每日期间隔
            time.sleep(INTERVAL_SECONDS)

        # 步骤 4: 更新 Redis 标记
        if total_missing > 0:
            _set_backfill_marker(today - timedelta(days=1))
            logger.info("[cctv_backfill] 回补完成 | 缺失:%d 已补:%d", total_missing, total_ok)
        else:
            logger.info("[cctv_backfill] 扫描完成，无缺失日期")

    except Exception as e:
        logger.warning("[cctv_backfill] 整体异常: %s", e)
    finally:
        _backfill_lock.release()


def start_cctv_backfill():
    """
    启动 CCTV 历史数据回补（后台 daemon 线程，不阻塞启动）。

    启动规则：
      - 有锁保护，防止热重载多次调用
      - daemon=True，不阻塞进程退出
      - 不触发当天数据的回补

    在 FastAPI lifespan 中调用。
    """
    global _backfill_started
    if _backfill_started:
        logger.info("[cctv_backfill] 服务已在运行，跳过重复启动")
        return
    _backfill_started = True

    t = threading.Thread(
        target=_run_backfill,
        daemon=True,
        name="cctv-backfill",
    )
    t.start()
    logger.info("[cctv_backfill] 后台回补线程已启动")
