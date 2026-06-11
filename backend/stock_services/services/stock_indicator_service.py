"""
stock_services/services/stock_indicator_service.py — 技术指标 Service 层

职责：
  - 读取K线数据（MySQL）→ 计算全部指标 → 写入 Redis Hash + MySQL
  - 提供查询接口（缓存优先）

Redis Key 设计（与K线缓存一致）:
  Key:   indicator:{symbol}:{YYYY}
  Field: MMDD
  Value: 全部指标的 JSON
  TTL:   30天
"""

import json
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from stock_services.indicators import compute_all, INDICATOR_VERSION as _CALC_VERSION
from system_service.redis_service import RedisServiceBase
from utils.db import get_cursor
from utils.redis_client_compat import _get_client
from models.indicator_models import ensure_indicator_year_table, INDICATOR_DB_NAME

from stock_services.common.cache import CacheKeyBuilder
from stock_services.common.logging import get_module_logger

logger = get_module_logger("StockIndicatorService")


# Redis Key 前缀（含版本后缀，参数变更后老版本数据自然隔离）
# 🔁 Key 构建已委派至 common/cache.CacheKeyBuilder.build_simple()
#    保持 _INDICATOR_KEY_PREFIX 不变以兼容外部引用（如 routes 层）
_INDICATOR_KEY_PREFIX = f"indicator:{_CALC_VERSION}"
_REDIS_TTL = 30 * 24 * 3600  # 30天


# ─── 兼容工具：生成 indicator Redis Key ───────────────────────────
def _build_indicator_key(symbol: str, year: int) -> str:
    """统一构建 indicator Redis Hash Key（委派至 CacheKeyBuilder）"""
    return CacheKeyBuilder.build_simple("indicator", _CALC_VERSION, symbol, str(year))


class StockIndicatorService(RedisServiceBase):
    """技术指标 Service（缓存+计算+存储）"""

    def __init__(self):
        super().__init__(service_name="StockIndicatorService")
        self._symbol_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

    # ─────────────────────────────────────────────────────────────
    #  公开接口
    # ─────────────────────────────────────────────────────────────

    def get_indicators(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取技术指标，缓存优先。

        Args:
            symbol:     股票代码（单只，如 "000001"）
            start_date: 起始日期 YYYYMMDD 或 YYYY-MM-DD，默认60天前
            end_date:   截止日期 YYYYMMDD 或 YYYY-MM-DD，默认今天

        Returns:
            {"success": True, "data": [{"trade_date":"...", ...}, ...]}
        """
        try:
            symbol = str(symbol).strip()
            end = self._parse_date(end_date or "", 0)
            start = self._parse_date(start_date or "", 60)

            if start > end:
                return {"success": False, "error": "start_date 不能晚于 end_date"}

            # 1. 尝试 Redis 逐日查询
            cached, missing_dates = self._try_redis(symbol, start, end)
            if not missing_dates:
                return {"success": True, "data": cached, "source": "redis"}

            # 2. 尝试 MySQL 查询缺失日期
            db_data, db_missing = self._try_db(symbol, missing_dates)
            cached.extend(db_data)

            if not db_missing:
                return {"success": True, "data": cached, "source": "db"}

            # 3. 缺失数据 → 计算（允许 mootdx 兜底获取K线）
            computed = self._compute_and_store(symbol, start, end, allow_mootdx=True)
            if computed.get("success"):
                # 合并计算结果
                all_data = {r["trade_date"]: r for r in cached}
                for r in computed.get("data", []):
                    all_data[r["trade_date"]] = r
                result = sorted(all_data.values(), key=lambda x: x["trade_date"])
                return {"success": True, "data": result, "source": "computed"}
            return computed

        except Exception as e:
            logger.exception("[indicator] get_indicators 异常: %s", e)
            return {"success": False, "error": str(e)}

    def compute_today(self, symbols: Optional[List[str]] = None,
                      parallel: int = 8) -> Dict[str, Any]:
        """
        采集完成后调用：计算今日指标（并行执行）。

        如果 symbols 为空，自动扫描今日有K线数据的所有股票。
        自动跳过已计算成功的股票（通过 indicator_compute_log 状态表）。

        Args:
            symbols:  指定股票列表，None=全市场
            parallel: 并行线程数（默认8）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            today_str = datetime.now().strftime("%Y%m%d")

            # 标记计算进行中（防重复启动，TTL=2h）
            r = self._get_client()
            if r:
                try:
                    if r.setnx(f"indicator:compute:running:{today_str}", "1"):
                        r.expire(f"indicator:compute:running:{today_str}", 7200)
                    else:
                        logger.info("[indicator] 计算已在执行中，跳过重复触发")
                        return {"success": True, "data": {"message": "计算已在执行中，跳过"}}
                except Exception:
                    pass

            if symbols is None:
                # 方案①: 单SQL合并查询待计算股票（替代两次查询+内存差集）
                pending, total_with_klines = self._get_pending_stocks(today)
                skipped = total_with_klines - len(pending)
                if skipped > 0:
                    logger.info("[indicator] 今日共 %d 只, 跳过已计算 %d 只, 待计算 %d 只",
                                total_with_klines, skipped, len(pending))
            else:
                pending = [s for s in symbols]
                skipped = 0
                total_with_klines = len(symbols)

            total = len(pending)

            # 方案②: 批量预加载K线到内存（单次批量SQL，消除个股独立查询Redis/DB的开销）
            klines_pool: Dict[str, List[Dict]] = {}
            if pending:
                logger.info("[indicator] 批量预加载 %d 只股票K线数据...", len(pending))
                klines_pool = self._batch_load_klines_for_compute(pending, today)

            ok = 0
            failed: List[str] = []
            futures: Dict = {}

            # 分批提交防止线程池任务数过多
            BATCH_SIZE = 1000
            for batch_start in range(0, total, BATCH_SIZE):
                batch = pending[batch_start:batch_start + BATCH_SIZE]
                with ThreadPoolExecutor(max_workers=parallel) as pool:
                    for sym in batch:
                        # 从预加载池获取K线，未命中时 fallback 到自行加载
                        preloaded_klines = klines_pool.get(sym)
                        fut = pool.submit(self._compute_single_stock, sym, today,
                                          preloaded_klines)
                        futures[fut] = sym
                    for fut in as_completed(futures):
                        sym = futures[fut]
                        try:
                            success, err_msg = fut.result()
                            if success:
                                ok += 1
                            else:
                                failed.append(f"{sym}({err_msg})")
                        except Exception as e:
                            failed.append(f"{sym}({e})")

            # 标记计算完成
            if r:
                try:
                    r.setex(f"indicator:compute:done:{today_str}", 86400, str(ok))
                except Exception:
                    pass

            logger.info(
                "[indicator] 今日指标计算完成 | 总计:%d 跳过:%d 成功:%d 失败:%d",
                total_with_klines, skipped, ok, len(failed),
            )
            return {
                "success": True,
                "data": {
                    "total": total_with_klines, "skipped": skipped,
                    "ok": ok, "failed": failed,
                },
            }

        except Exception as e:
            logger.exception("[indicator] compute_today 异常: %s", e)
            return {"success": False, "error": str(e)}

    def _compute_single_stock(self, symbol: str, today: str,
                              preloaded_klines: Optional[List[Dict]] = None) -> tuple:
        """计算单只股票今日指标（供线程池调用）

        Args:
            symbol:  股票代码
            today:   交易日 YYYY-MM-DD
            preloaded_klines: 预加载的K线数据（方案②批量加载优化），None=自行加载
        """
        try:
            result = self._compute_and_store(symbol, today, today, allow_mootdx=False,
                                             preloaded_klines=preloaded_klines)
            if result.get("success"):
                self._mark_compute_log(symbol, today, "done")
                return True, ""
            else:
                err_msg = result.get("error", "未知错误")
                self._mark_compute_log(symbol, today, "failed", err_msg)
                return False, err_msg
        except Exception as e:
            self._mark_compute_log(symbol, today, "failed", str(e))
            return False, str(e)

    def _batch_load_klines_for_compute(
        self, symbols: List[str], target_date: str,
    ) -> Dict[str, List[Dict]]:
        """
        批量预加载K线数据到内存 dict[symbol] = [kline_records]。

        在 compute_today 进入线程池之前调用，从 MySQL 一次性加载所有待计算股票的
        历史K线（370天窗口），消除每只股票独立查询 Redis/DB 的 30-75ms 开销。

        Args:
            symbols:    待计算股票代码列表
            target_date: 目标日期 YYYY-MM-DD

        Returns:
            {symbol: [{trade_date, open, high, low, close, vol, amount}, ...]}
        """
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        start_dt = target_dt - timedelta(days=370)
        start_s = start_dt.strftime("%Y-%m-%d")
        end_s = target_dt.strftime("%Y-%m-%d")

        # 涉及年份
        years = {str(y) for y in range(start_dt.year, target_dt.year + 1)}

        result: Dict[str, List[Dict]] = {}
        chunk_size = 500  # 每批股票数（避免IN列表过长）

        for year in sorted(years):
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i + chunk_size]
                placeholders = ",".join(["%s"] * len(chunk))
                sql = (
                    f"SELECT symbol, datetime, `open`, `high`, `low`, `close`, "
                    f"  vol, amount "
                    f"FROM `stock_klines`.`stock_klines_{year}` "
                    f"WHERE symbol IN ({placeholders}) "
                    f"AND datetime >= %s AND datetime <= %s "
                    f"ORDER BY symbol, datetime"
                )
                try:
                    with get_cursor() as cur:
                        cur.execute(sql, chunk + [start_s, end_s])
                        for row in cur.fetchall() or []:
                            sym = str(row["symbol"])
                            r = dict(row)
                            dt = r.get("datetime")
                            if hasattr(dt, "strftime"):
                                r["trade_date"] = dt.strftime("%Y-%m-%d")
                            else:
                                r["trade_date"] = str(dt)[:10]
                            result.setdefault(sym, []).append(r)
                except Exception as e:
                    logger.warning("[indicator] 批量K线加载失败 year=%s: %s", year, e)

        logger.info("[indicator] 批量预加载K线完成 | 股票:%d 涉及年份:%s 总记录数:%d",
                    len(result), list(years),
                    sum(len(v) for v in result.values()))
        return result

    # ─────────────────────────────────────────────────────────────
    #  批量回填（历史数据补算）
    # ─────────────────────────────────────────────────────────────

    def backfill_stock(self, symbol: str,
                       skip_computed: bool = True) -> Dict[str, Any]:
        """
        回填单只股票的全部历史指标。
        扫描该股所有年份的K线数据，计算全部指标后写入 Redis + MySQL。

        Args:
            skip_computed: 跳过已计算过的年份（通过查询 stock_indicators 表判断）
        """
        try:
            symbol = str(symbol).strip()
            logger.info("[indicator_backfill] 开始回填: %s", symbol)

            # 优化①: 单次 UNION ALL 查出该股所有有K线数据的年份
            years = self._get_stock_years(symbol)
            if not years:
                return {"success": False, "error": f"{symbol} 无K线数据"}

            # 优化④: 跳过已计算的年份
            if skip_computed:
                years_to_fill = self._filter_uncomputed_years(symbol, years)
                skipped_years = len(years) - len(years_to_fill)
                if skipped_years:
                    logger.info("[indicator_backfill] %s 跳过 %d 个已计算年份",
                                symbol, skipped_years)
            else:
                years_to_fill = years

            if not years_to_fill:
                return {"success": True, "data": {"symbol": symbol, "years": [], "days": 0,
                                                   "message": "所有年份已计算，跳过"}}

            total_days = 0
            for year in years_to_fill:
                start = f"{year}0101"
                end = f"{year}1231"
                result = self._compute_and_store(symbol, start, end, allow_mootdx=True)
                if result.get("success"):
                    total_days += len(result.get("data", []))

            logger.info("[indicator_backfill] %s 完成 | 年份:%d 已跳过:%d 天数:%d",
                        symbol, len(years_to_fill),
                        len(years) - len(years_to_fill), total_days)
            return {"success": True, "data": {"symbol": symbol, "years": years_to_fill,
                                               "days": total_days}}

        except Exception as e:
            logger.exception("[indicator_backfill] %s 异常: %s", symbol, e)
            return {"success": False, "error": str(e)}

    @staticmethod
    def _filter_uncomputed_years(symbol: str, years: List[int]) -> List[int]:
        """过滤掉 stock_indicators 中已有数据的年份，只返回需要回填的年份"""
        if not years:
            return []
        to_fill: List[int] = []
        for y in years:
            try:
                sql = (
                    f"SELECT 1 FROM `{INDICATOR_DB_NAME}`.`stock_indicators_{y}` "
                    f"WHERE symbol = %s LIMIT 1"
                )
                with get_cursor() as cur:
                    cur.execute(sql, (symbol,))
                    if not cur.fetchone():
                        to_fill.append(y)
            except Exception:
                # 表不存在 → 未计算，需要回填
                to_fill.append(y)
        return to_fill

    def backfill_all(self, year: Optional[int] = None,
                     batch_size: int = 100, parallel: int = 8) -> Dict[str, Any]:
        """
        全市场回填：扫描所有有K线数据的股票，逐个回填指标。

        Args:
            year: 指定年份，None=扫描所有年
            batch_size: 每批股票数
            parallel: 并行线程数

        Returns:
            {"total": N, "ok": N, "failed": [...], "elapsed_s": ...}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        t0 = time.time()
        try:
            symbols = self._get_all_kline_stocks(year)
            if not symbols:
                return {"success": False, "error": "未找到有K线数据的股票"}

            total = len(symbols)
            logger.info("[indicator_backfill] 全市场回填开始 | 股票:%d batch=%d parallel=%d",
                        total, batch_size, parallel)

            ok = 0
            failed: List[str] = []

            # 分批处理
            for batch_start in range(0, total, batch_size):
                batch = symbols[batch_start:batch_start + batch_size]
                logger.info("[indicator_backfill] 批次 %d/%d | %d~%d",
                            batch_start // batch_size + 1,
                            (total + batch_size - 1) // batch_size,
                            batch_start + 1, min(batch_start + batch_size, total))

                with ThreadPoolExecutor(max_workers=parallel) as pool:
                    fut_map = {pool.submit(self.backfill_stock, sym): sym for sym in batch}
                    for fut in as_completed(fut_map):
                        sym = fut_map[fut]
                        try:
                            r = fut.result()
                            if r.get("success"):
                                ok += 1
                            else:
                                failed.append(sym)
                        except Exception as e:
                            failed.append(f"{sym}({e})")

            elapsed = round(time.time() - t0, 1)
            logger.info("[indicator_backfill] 全市场回填完成 | 总计:%d 成功:%d 失败:%d 耗时:%.1fs",
                        total, ok, len(failed), elapsed)
            return {
                "success": True,
                "data": {
                    "total": total, "ok": ok, "failed": len(failed),
                    "failed_list": failed[:50],  # 只返回前50个
                    "elapsed_s": elapsed,
                },
            }

        except Exception as e:
            logger.exception("[indicator_backfill] 全市场回填异常: %s", e)
            return {"success": False, "error": str(e)}

    @staticmethod
    def _get_kline_year_tables() -> List[str]:
        """查询 stock_klines 数据库下所有已存在的年表名。"""
        try:
            sql = (
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_SCHEMA = 'stock_klines' "
                "AND TABLE_NAME LIKE 'stock_klines\\_%' "
                "ORDER BY TABLE_NAME"
            )
            with get_cursor() as cur:
                cur.execute(sql)
                return [row["TABLE_NAME"] for row in cur.fetchall() or []]
        except Exception:
            return [f"stock_klines_{y}" for y in range(1990, 2031)]

    def _get_stock_years(self, symbol: str) -> List[int]:
        """
        查询某只股票有哪些年份有K线数据。

        采用后向扫描（最近→最早），遇到第一个空表即停止。
        因为股票数据从上市至今是连续的（无跨年间隙），后向扫描最多只需检测
        (当年-上市年+2)次查询，且非空表查询走索引 < 5ms，远快于前向扫描
        （空表因全索引扫描需 200~900ms/次）。
        """
        tables = self._get_kline_year_tables()
        if not tables:
            return []

        # 提取年份并降序排列
        years_desc = sorted(
            [int(t.replace("stock_klines_", "")) for t in tables
             if t.replace("stock_klines_", "").isdigit()],
            reverse=True,
        )
        if not years_desc:
            return []

        result: List[int] = []
        found_data = False
        try:
            with get_cursor() as cur:
                for y in years_desc:
                    try:
                        cur.execute(
                            f"SELECT 1 FROM `stock_klines`.`stock_klines_{y}` "
                            f"WHERE symbol = %s LIMIT 1",
                            (symbol,),
                        )
                        if cur.fetchone():
                            result.append(y)
                            found_data = True
                        elif found_data:
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        return sorted(result)

    def _get_all_kline_stocks(self, year: Optional[int] = None) -> List[str]:
        """获取有K线数据的所有股票列表（单次 UNION 替代逐表查询）"""
        symbols: List[str] = []
        try:
            if year:
                tables = [f"stock_klines_{year}"]
            else:
                tables = self._get_kline_year_tables()

            unions: List[str] = []
            for table in tables:
                unions.append(
                    f"SELECT DISTINCT symbol FROM `stock_klines`.`{table}`"
                )

            if not unions:
                return []

            sql = " UNION ".join(unions)  # UNION 自带去重
            try:
                with get_cursor() as cur:
                    cur.execute(sql)
                    for row in cur.fetchall() or []:
                        sym = str(row["symbol"]).strip()
                        if sym:
                            symbols.append(sym)
            except Exception:
                pass
        except Exception:
            pass
        return symbols

    # ─────────────────────────────────────────────────────────────
    #  内部方法
    # ─────────────────────────────────────────────────────────────

    def _try_redis(self, symbol: str, start: datetime, end: datetime) -> tuple:
        """尝试从 Redis Hash 按年批量查询（hgetall + 内存过滤）"""
        results: List[Dict] = []
        missing: List[datetime] = []
        r = self._get_client()
        if not r:
            return results, [start + timedelta(days=i) for i in range((end - start).days + 1)]

        # 按年份 hgetall + 内存过滤（替代逐日 hget）
        years = set()
        cur = start
        while cur <= end:
            years.add(cur.strftime("%Y"))
            cur += timedelta(days=1)

        for year in sorted(years):
            key = _build_indicator_key(symbol, year)
            try:
                all_data = r.hgetall(key)
                if not all_data:
                    # 该年无数据 → 该年所有日期标记为缺失
                    yr_start = max(start, datetime(int(year), 1, 1))
                    yr_end = min(end, datetime(int(year), 12, 31))
                    while yr_start <= yr_end:
                        missing.append(yr_start)
                        yr_start += timedelta(days=1)
                    continue

                # 解析并过滤
                record_map = {}
                for field, raw in all_data.items():
                    field_str = field.decode() if isinstance(field, bytes) else field
                    if field_str == "__complete__":
                        continue
                    try:
                        val_str = raw.decode() if isinstance(raw, bytes) else raw
                        row = json.loads(val_str) if isinstance(val_str, str) else val_str
                        td = str(row.get("trade_date", ""))[:10]
                        record_map[td] = row
                    except Exception:
                        continue

                # 按日期范围过滤
                cur_d = max(start, datetime(int(year), 1, 1))
                yr_end = min(end, datetime(int(year), 12, 31))
                while cur_d <= yr_end:
                    date_key = cur_d.strftime("%Y-%m-%d")
                    if date_key in record_map:
                        results.append(record_map[date_key])
                    else:
                        missing.append(cur_d)
                    cur_d += timedelta(days=1)
            except Exception:
                # 异常时该年所有日期标记为缺失
                yr_start = max(start, datetime(int(year), 1, 1))
                yr_end = min(end, datetime(int(year), 12, 31))
                while yr_start <= yr_end:
                    missing.append(yr_start)
                    yr_start += timedelta(days=1)

        return results, missing

    def _try_db(self, symbol: str, dates: List[datetime]) -> tuple:
        """尝试从 MySQL 查询缺失日期（表不存在时静默跳过）"""
        results: List[Dict] = []
        still_missing: List[datetime] = dates[:]

        # 按年分组查询
        year_groups: Dict[str, List[str]] = defaultdict(list)
        for d in dates:
            year_groups[d.strftime("%Y")].append(d.strftime("%Y-%m-%d"))

        for year, date_list in year_groups.items():
            placeholders = ",".join(["%s"] * len(date_list))
            sql = (
                f"SELECT * FROM `{INDICATOR_DB_NAME}`.`stock_indicators_{year}` "
                f"WHERE symbol = %s AND trade_date IN ({placeholders})"
            )
            try:
                with get_cursor() as cur:
                    cur.execute(sql, [symbol] + date_list)
                    rows = cur.fetchall() or []
            except Exception as e:
                # 表不存在时静默跳过，触发计算逻辑
                logger.debug("[indicator] DB查询失败（可能表未创建）: %s", e)
                return results, still_missing

            db_map = {}
            for row in rows:
                d = row.get("trade_date")
                if hasattr(d, "strftime"):
                    d = d.strftime("%Y-%m-%d")
                db_map[str(d)] = dict(row)

            for date_str in date_list:
                if date_str in db_map:
                    results.append(db_map[date_str])
                else:
                    still_missing.append(
                        datetime.strptime(date_str, "%Y-%m-%d")
                    )

        return results, still_missing

    def _compute_and_store(
        self, symbol: str, start_date: str, end_date: str,
        allow_mootdx: bool = False,
        preloaded_klines: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """核心：读取K线 → 计算 → 写Redis → 写MySQL

        Args:
            allow_mootdx: 是否允许触发 mootdx 兜底读取K线
            preloaded_klines: 预加载的K线列表（方案②批量优化），None=自行加载
        """
        with self._symbol_locks[symbol]:
            try:
                # 1. 读取K线数据（优先使用预加载数据，其次走三层缓存）
                start_s = self._fmt_date(start_date)
                end_s = self._fmt_date(end_date)

                if preloaded_klines is not None:
                    klines = preloaded_klines
                else:
                    # 向前多取K线（指标计算需要足够历史窗口期）
                    # 最长指标周期为 MA250 ≈ 250个交易日 ≈ 350个日历日
                    extended_start = (
                        datetime.strptime(start_s, "%Y-%m-%d") - timedelta(days=370)
                    ).strftime("%Y%m%d")
                    extended_end = datetime.strptime(end_s, "%Y-%m-%d").strftime("%Y%m%d")
                    klines = self._load_klines(symbol, extended_start, extended_end,
                                               allow_mootdx=allow_mootdx)
                if not klines:
                    return {
                        "success": False,
                        "error": f"{symbol} 在 {start_s}~{end_s} 无K线数据",
                    }

                # 2. 计算指标
                all_results = compute_all(klines)

                # 过滤到目标日期范围
                filtered = [
                    r for r in all_results
                    if start_s <= str(r.get("trade_date", ""))[:10] <= end_s
                ]

                if not filtered:
                    return {
                        "success": True,
                        "data": [],
                        "message": "目标范围内无数据",
                    }

                # 3. 准备 Redis 写入数据（按年分组）
                year_batch: Dict[str, Dict[str, str]] = {}
                for row in filtered:
                    td = str(row.get("trade_date", ""))[:10]
                    if not td:
                        continue
                    year = td[:4]
                    mmdd = td[5:7] + td[8:10]
                    key = _build_indicator_key(symbol, int(year))
                    if key not in year_batch:
                        year_batch[key] = {}
                    year_batch[key][mmdd] = json.dumps(row, ensure_ascii=False)

                # 4. 写入 MySQL（持久化优先）
                self._batch_upsert(symbol, filtered)

                # 5. 写入 Redis Hash（pipeline 批量，失败不影响 MySQL）
                r = self._get_client()
                if r:
                    try:
                        pipe = r.pipeline(transaction=False)
                        for redis_key, fields in year_batch.items():
                            for field, val in fields.items():
                                pipe.hset(redis_key, field, val)
                            pipe.expire(redis_key, _REDIS_TTL)
                        pipe.execute()
                    except Exception as redis_err:
                        logger.warning("[indicator] Redis 写入失败（MySQL 已持久化）: %s", redis_err)

                return {"success": True, "data": filtered, "source": "computed"}

            except Exception as e:
                logger.exception("[indicator] _compute_and_store 异常: %s", e)
                return {"success": False, "error": str(e)}

    def _load_klines(
        self, symbol: str, start_date: str, end_date: str,
        allow_mootdx: bool = False,
    ) -> List[Dict]:
        """从 mootdx 三层缓存读取K线数据

        Args:
            allow_mootdx: 是否允许触发 mootdx 兜底（True=backfill等历史补算，False=compute_today）
        """
        from stock_services.mootdx.kline_query import kline_query_layer

        mode = "standard" if allow_mootdx else "compute"
        result = kline_query_layer.get_kline_with_cache(
            symbol=symbol, freq="day",
            start_date=start_date, end_date=end_date,
            mode=mode,
        )
        if not result.get("success"):
            return []
        records = result.get("records", [])
        # 统一字段名 trade_date
        for r in records:
            dt = r.get("datetime") or r.get("trade_date")
            if dt and hasattr(dt, "strftime"):
                r["trade_date"] = dt.strftime("%Y-%m-%d")
            elif dt:
                r["trade_date"] = str(dt)[:10]
        return records

    def _batch_upsert(self, symbol: str, rows: List[Dict]) -> None:
        """批量 UPSERT 到 MySQL（按年分表）"""
        if not rows:
            return
        # 按年份分组
        year_groups: Dict[str, List[Dict]] = {}
        for row in rows:
            td = str(row.get("trade_date", ""))[:10]
            year = td[:4] if len(td) >= 4 else "2026"
            year_groups.setdefault(year, []).append(row)

        for year, batch in year_groups.items():
            # 懒建：写前确保表存在
            try:
                ensure_indicator_year_table(int(year))
            except Exception:
                logger.warning(f"[indicator] 建表失败 year={year}，跳过该年写入")
                continue
            # 再按 200 条分批
            batch_size = 200
            for i in range(0, len(batch), batch_size):
                self._upsert_batch(symbol, year, batch[i:i + batch_size])

    def _upsert_batch(self, symbol: str, year: str, rows: List[Dict]) -> None:
        """单批 UPSERT"""
        if not rows:
            return

        # 构建 CASE WHEN 批量更新
        # 字段列表（排除 id, symbol, trade_date, 通用后缀）
        value_fields = [
            "ma_5", "ma_10", "ma_20", "ma_60", "ma_120", "ma_250",
            "boll_ma", "boll_upper", "boll_lower", "boll_width",
            "sar", "vol", "vol_ma_5", "vol_ma_10", "vol_ma_20",
            "macd_dif", "macd_dea", "macd_bar",
            "kdj_k", "kdj_d", "kdj_j",
            "rsi_6", "rsi_12", "rsi_24",
            "wr_6", "wr_10", "wr_14",
            "cci", "bias_6", "bias_12", "bias_24",
            "psy_12", "psy_24", "psy_ma_12", "psy_ma_24",
            "obv", "obv_ma",
            "pdi", "mdi", "adx", "adxr",
            "roc", "roc_ma",
            "indicator_version",
        ]

        try:
            from collections import OrderedDict

            # INSERT ... ON DUPLICATE KEY UPDATE
            cols = ["symbol", "trade_date"] + value_fields
            placeholders = ",".join(["%s"] * len(cols))
            update_parts = ", ".join(
                [f"`{f}`=VALUES(`{f}`)" for f in value_fields]
            )
            sql = (
                f"INSERT INTO `{INDICATOR_DB_NAME}`.`stock_indicators_{year}` "
                f"({','.join(['`' + c + '`' for c in cols])}) "
                f"VALUES ({placeholders}) "
                f"ON DUPLICATE KEY UPDATE {update_parts}"
            )

            with get_cursor(commit=True) as cur:
                params = []
                for row in rows:
                    params.append(symbol)
                    params.append(str(row.get("trade_date", ""))[:10])
                    for f in value_fields:
                        v = row.get(f)
                        params.append(v)
                cur.executemany(sql, [tuple(params[i:i + len(cols)])
                                      for i in range(0, len(params), len(cols))])

        except Exception as e:
            logger.warning("[indicator] _upsert_batch 失败: %s", e)

    @staticmethod
    def _get_pending_stocks(trade_date: str) -> tuple:
        """
        合并SQL：一次查询获取今日有K线但尚未计算指标的股票列表。

        替代 _get_today_stocks() + _get_done_symbols() 两次独立查询 + 内存差集。
        通过 LEFT JOIN + CASE WHEN 在一次查询中同时返回待计算列表和总股票数。

        Returns:
            (pending_list, total_with_klines)
        """
        year = trade_date[:4]
        sql = (
            f"SELECT k.symbol, "
            f"  CASE WHEN l.symbol IS NOT NULL THEN 1 ELSE 0 END as is_done "
            f"FROM `stock_klines`.`stock_klines_{year}` k "
            f"LEFT JOIN indicator_compute_log l "
            f"  ON k.symbol = l.symbol AND DATE(k.datetime) = l.trade_date AND l.status = 'done' "
            f"WHERE DATE(k.datetime) = %s "
            f"ORDER BY k.symbol"
        )
        try:
            with get_cursor() as cur:
                cur.execute(sql, (trade_date,))
                rows = cur.fetchall() or []
            all_symbols = [row["symbol"] for row in rows if row.get("symbol")]
            pending = [row["symbol"] for row in rows if row.get("is_done") == 0 and row.get("symbol")]
            return pending, len(all_symbols)
        except Exception:
            logger.warning("[indicator] 查询待计算股票列表失败")
            return [], 0

    @staticmethod
    def _parse_date(date_str: str, days_ago: int) -> datetime:
        """解析日期，空值返回 days_ago 天前/后"""
        s = str(date_str).strip().replace("-", "")
        if not s or s == "None":
            return datetime.now() + timedelta(days=days_ago)
        fmt = "%Y%m%d" if len(s) == 8 else "%Y-%m-%d"
        try:
            return datetime.strptime(s[:10], fmt)
        except ValueError:
            return datetime.now() + timedelta(days=days_ago)

    @staticmethod
    def _fmt_date(d: Any) -> str:
        """统一输出 YYYY-MM-DD"""
        if isinstance(d, datetime):
            return d.strftime("%Y-%m-%d")
        s = str(d).strip().replace("-", "")
        if len(s) >= 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return str(d)[:10]

    # ── 计算状态追踪 ─────────────────────────────────────────────

    @staticmethod
    def _get_done_symbols(trade_date: str) -> set:
        """查询指定日期已计算成功的股票集合"""
        try:
            sql = (
                "SELECT symbol FROM indicator_compute_log "
                "WHERE trade_date = %s AND status = 'done'"
            )
            with get_cursor() as cur:
                cur.execute(sql, (trade_date,))
                return {row["symbol"] for row in cur.fetchall() or []}
        except Exception:
            return set()

    @staticmethod
    def _mark_compute_log(symbol: str, trade_date: str, status: str, error_msg: str = ""):
        """记录计算状态到 indicator_compute_log"""
        try:
            sql = (
                "INSERT INTO indicator_compute_log (symbol, trade_date, status, error_msg, computed_at) "
                "VALUES (%s, %s, %s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE status=VALUES(status), error_msg=VALUES(error_msg), computed_at=NOW()"
            )
            with get_cursor(commit=True) as cur:
                cur.execute(sql, (symbol, trade_date, status, error_msg or None))
        except Exception as e:
            logger.warning("[indicator] 状态记录失败 %s/%s: %s", symbol, trade_date, e)


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

stock_indicator_service = StockIndicatorService()