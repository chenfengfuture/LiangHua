#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K 线三层查询层 — Redis → DB → mootdx

数据读取优先级：
  1. Redis Hash（最快，无网络 I/O 瓶颈）
  2. MySQL（数据持久层，作为 Redis 未命中时的回填源）
  3. mootdx 行情直连（兜底，仅前两者均缺失时触发）

完整性校验：
  - 每个查询先计算预期交易日数（get_trading_days）
  - Redis/DB 中的实际记录数 >= 预期数 → 判定完整
"""

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from utils.db import get_conn

from .base_service import MootdxBaseService
from .kline_redis import kline_redis_service
from .service import mootdx_kline_service
from .table_helper import get_kline_full_table_name
from stock_services.common.date_utils import get_trading_days
from stock_services.common.logging import get_module_logger

log = get_module_logger("kline_query")

# K 线表字段列表（与 service.py 中的 KLINE_COLS 保持一致）
KLINE_COLS = [
    'symbol', 'name', 'datetime', 'open', 'high', 'low', 'close',
    'vol', 'amount', 'volume', 'year', 'month', 'day', 'hour', 'minute',
]

# ── 交易日列表内存缓存 ──────────────────────────────────────────
_TRADING_DAYS_CACHE: Dict[str, List[date]] = {}
_MAX_CACHE_ENTRIES = 20


class KlineQueryLayer(MootdxBaseService):
    """
    K 线三层查询层

    职责：
      · 对前端查询请求提供统一入口
      · 自动选择最优数据源（Redis > DB > mootdx）
      · 逐级降级，确保数据最终可用
    """

    def __init__(self):
        pass

    # ─── 公开入口 ──────────────────────────────────────────────────

    def get_kline_with_cache(
        self,
        symbol: str,
        freq: str = "day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mode: str = "standard",
    ) -> Dict[str, Any]:
        """
        三层缓存查询入口（单股专用）。

        Args:
            symbol:     单股代码，如 "000001"
            freq:       day / week / month
            start_date: YYYYMMDD 或 YYYY-MM-DD（默认 30 天前）
            end_date:   YYYYMMDD 或 YYYY-MM-DD（默认今天）
            mode:       "standard"=标准三层降级 | "compute"=仅Redis+DB，跳过mootdx

        Returns:
            {
                "success": True,
                "symbol": "000001",
                "name": "...",
                "freq": "day",
                "source": "redis|db|mootdx|partial",
                "records": [...],
                "total": N,
                "elapsed_s": 0.05,
            }
        """
        t0 = time.time()
        symbol = str(symbol).strip()
        if not symbol:
            return {"success": False, "error": "symbol 不可为空"}

        freq = str(freq).strip().lower()
        start_d = self._parse_date(start_date or "", 30)
        end_d = self._parse_date(end_date or "", 0)

        if start_d > end_d:
            return {"success": False, "error": "start_date 不能晚于 end_date"}

        # 计算预期交易日数（日线精确，周/月线粗略）
        expected = self._calc_expected_count(start_d, end_d, freq)
        if expected == 0:
            return {
                "success": True, "symbol": symbol, "freq": freq,
                "source": "none", "records": [], "total": 0,
                "elapsed_s": round(time.time() - t0, 3),
            }

        # ── 1. 尝试 Redis Hash ─────────────────────────────────
        result = self._try_redis(symbol, freq, start_d, end_d, expected)
        if result is not None:
            result["elapsed_s"] = round(time.time() - t0, 3)
            return result

        # ── 2. 尝试 DB ─────────────────────────────────────────
        result = self._try_db(symbol, freq, start_d, end_d, expected, t0)
        if result is not None:
            result["elapsed_s"] = round(time.time() - t0, 3)
            return result

        # ── compute 模式：跳过 mootdx 兜底，返回已有部分数据 ───
        if mode == "compute":
            partial = self._try_db_partial(symbol, start_d, end_d)
            if partial:
                log.info(f"[kline_query] compute 模式: {symbol} 返回部分数据 {len(partial)} 条")
                return {
                    "success": True, "symbol": symbol,
                    "name": partial[0].get("name", ""),
                    "freq": freq, "source": "partial",
                    "records": partial, "total": len(partial),
                    "elapsed_s": round(time.time() - t0, 3),
                }
            return {
                "success": True, "symbol": symbol, "freq": freq,
                "source": "none", "records": [], "total": 0,
                "elapsed_s": round(time.time() - t0, 3),
            }

        # ── 3. mootdx 兜底（含数据合并） ───────────────────────
        result = self._try_mootdx_with_merge(symbol, freq, start_d, end_d, t0)
        return result

    def _calc_expected_count(self, start_d: date, end_d: date, freq: str) -> int:
        """计算预期数据条数（带交易日列表缓存）"""
        total = (end_d - start_d).days + 1
        if total <= 0:
            return 0

        if freq == "day":
            cache_key = f"{start_d.isoformat()}-{end_d.isoformat()}"
            if cache_key in _TRADING_DAYS_CACHE:
                trading_days = _TRADING_DAYS_CACHE[cache_key]
            else:
                trading_result = get_trading_days(start_d, end_d)
                trading_days = trading_result.get('data', {}).get('trading_day', [])
                if len(_TRADING_DAYS_CACHE) < _MAX_CACHE_ENTRIES:
                    _TRADING_DAYS_CACHE[cache_key] = trading_days
            return len(trading_days)
        elif freq == "week":
            return max(total // 7 + 1, 1)
        elif freq == "month":
            return max((end_d.year - start_d.year) * 12 + end_d.month - start_d.month + 1, 1)
        return total

    # ─── 第 1 层：Redis Hash ──────────────────────────────────────

    def _try_redis(self, symbol: str, freq: str,
                   start_d: date, end_d: date, expected: int) -> Optional[Dict]:
        """尝试从 Redis Hash 读取完整数据"""
        # 计算涉及年份
        years = set()
        cur = start_d
        while cur <= end_d:
            years.add(cur.year)
            cur += timedelta(days=1)

        # 检查每一年是否完整
        all_complete = True
        for yr in sorted(years):
            status = kline_redis_service.kline_hcheck_complete(symbol, freq, yr, expected)
            if status is None:
                return None  # Redis 不可用，降级
            if not status:
                all_complete = False

        if not all_complete:
            return None  # 数据不完整，降级

        # 全部完整，读取数据
        records = kline_redis_service.kline_hget_range(symbol, freq, start_d, end_d)
        if records:
            name = records[0].get("name", "")
            log.info(f"[kline_query] Redis 命中: {symbol} {freq} [{start_d}~{end_d}] "
                     f"records={len(records)}")
            return {
                "success": True, "symbol": symbol, "name": name,
                "freq": freq, "source": "redis",
                "records": records, "total": len(records),
            }

        return None

    # ─── 第 2 层：DB ──────────────────────────────────────────────

    def _try_db(self, symbol: str, freq: str,
                start_d: date, end_d: date, expected: int,
                t0: float) -> Optional[Dict]:
        """尝试从 MySQL 读取完整数据"""
        try:
            records = self._db_query(symbol, start_d, end_d)
        except Exception as e:
            log.warning(f"[kline_query] DB 查询失败: {e}")
            return None

        if not records:
            return None

        if len(records) < expected:
            log.info(f"[kline_query] DB 数据不完整: {symbol} {freq} "
                     f"got={len(records)} expected={expected}")
            return None

        # DB 数据完整 → 回填 Redis Hash
        try:
            h_cached = kline_redis_service.kline_hset_batch(records, freq)
            # 标记完整性
            for yr in {r.get("year") for r in records if r.get("year")}:
                kline_redis_service.kline_hset_complete(symbol, freq, int(yr), expected)
            log.info(f"[kline_query] DB → Redis 回填: {symbol} hset={h_cached}")
        except Exception as e:
            log.warning(f"[kline_query] DB→Redis 回填失败: {e}")

        name = records[0].get("name", "") if records else ""
        log.info(f"[kline_query] DB 命中: {symbol} {freq} [{start_d}~{end_d}] "
                 f"records={len(records)}")
        return {
            "success": True, "symbol": symbol, "name": name,
            "freq": freq, "source": "db",
            "records": records, "total": len(records),
        }

    def _db_query(self, symbol: str, start_d: date, end_d: date) -> List[Dict]:
        """从 MySQL 分年表查询 K 线数据"""
        years = set()
        cur = start_d
        while cur <= end_d:
            years.add(cur.year)
            cur += timedelta(days=1)

        all_records = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                for yr in sorted(years):
                    table = get_kline_full_table_name(yr)
                    sql = (
                        f"SELECT {', '.join(f'`{c}`' for c in KLINE_COLS)} "
                        f"FROM {table} "
                        f"WHERE symbol = %s "
                        f"AND DATE(datetime) >= %s AND DATE(datetime) <= %s "
                        f"ORDER BY datetime ASC"
                    )
                    cur.execute(sql, (symbol, start_d.isoformat(), end_d.isoformat()))
                    for row in cur.fetchall():
                        rec = dict(row)
                        # 类型归一化
                        for num_f in ("open", "high", "low", "close", "vol", "amount", "volume"):
                            if num_f in rec:
                                rec[num_f] = float(rec[num_f]) if rec[num_f] is not None else 0.0
                        all_records.append(rec)
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return all_records

    # ─── 第 3 层：mootdx 兜底 ────────────────────────────────────

    def _try_mootdx_with_merge(self, symbol: str, freq: str,
                                start_d: date, end_d: date,
                                t0: float) -> Dict:
        """mootdx 兜底：先拉取已有部分数据，再与 mootdx 新数据合并去重"""
        # 1. 先尝试从 DB 获取已有部分数据（即使不完整）
        existing = self._try_db_partial(symbol, start_d, end_d)
        existing_dates: Set[str] = set()
        for r in existing or []:
            dt = r.get("datetime") or r.get("trade_date")
            if hasattr(dt, "strftime"):
                existing_dates.add(dt.strftime("%Y-%m-%d"))
            elif dt:
                existing_dates.add(str(dt)[:10])

        # 2. 从 mootdx 拉取（可缩小 offset 范围，只补缺失部分）
        log.info(f"[kline_query] mootdx 兜底 + 合并: {symbol} {freq} [{start_d}~{end_d}] "
                 f"已有 {len(existing_dates)} 条，待补 {(end_d - start_d).days + 1 - len(existing_dates)} 天")

        try:
            name = mootdx_kline_service._get_stock_name(symbol)
            freq_code = mootdx_kline_service.FREQ_MAP.get(freq)
            if freq_code is None:
                return {"success": False, "error": f"未知频率: {freq}"}

            offset = mootdx_kline_service._calc_offset(start_d, end_d, freq_code)
            df = mootdx_kline_service._fetch_one_raw(symbol, freq_code, offset)
            if df is None:
                # mootdx 失败但有部分数据 → 仍然返回部分数据
                if existing:
                    log.info(f"[kline_query] mootdx 拉取失败，返回部分数据 {len(existing)} 条")
                    return {
                        "success": True, "symbol": symbol, "name": name,
                        "freq": freq, "source": "partial",
                        "records": existing, "total": len(existing),
                        "elapsed_s": round(time.time() - t0, 3),
                    }
                return {
                    "success": False, "error": f"mootdx 拉取失败: {symbol}",
                    "symbol": symbol, "freq": freq,
                    "elapsed_s": round(time.time() - t0, 3),
                }

            new_records = mootdx_kline_service._df_to_records(df, symbol, name, start_d, end_d)

            # 3. 合并去重：已有数据优先，mootdx 数据补充缺失
            merged = list(existing) if existing else []
            merged_dates = set(existing_dates)
            for rec in new_records:
                dt = rec.get("datetime") or rec.get("trade_date")
                date_key = None
                if hasattr(dt, "strftime"):
                    date_key = dt.strftime("%Y-%m-%d")
                elif dt:
                    date_key = str(dt)[:10]
                if date_key and date_key not in merged_dates:
                    merged.append(rec)
                    merged_dates.add(date_key)

            # 4. 双写 DB + Redis
            if merged:
                queued, year_cnt = mootdx_kline_service._async_persist_kline(merged, freq)
                h_cached = kline_redis_service.kline_hset_batch(merged, freq)

                # 标记完整性
                for yr in {r.get("year") for r in merged if r.get("year")}:
                    yr_expected = self._calc_expected_count(
                        date(int(yr), 1, 1), date(int(yr), 12, 31), freq
                    )
                    kline_redis_service.kline_hset_complete(symbol, freq, int(yr), yr_expected)
            else:
                queued, year_cnt, h_cached = 0, 0, 0

            source = "mootdx" if not existing else "mootdx_merged"
            log.info(f"[kline_query] mootdx+合并完成: {symbol} records={len(merged)} "
                     f"(new={len(new_records)}, existing={len(existing_dates)}) "
                     f"db={queued} redis_hash={h_cached}")

            return {
                "success": True, "symbol": symbol, "name": name,
                "freq": freq, "source": source,
                "records": merged, "total": len(merged),
                "queued_to_db": queued, "redis_hash": h_cached,
                "elapsed_s": round(time.time() - t0, 3),
            }

        except Exception as e:
            log.error(f"[kline_query] mootdx+合并异常: {e}")
            # 异常时返回已有部分数据
            if existing:
                return {
                    "success": True, "symbol": symbol,
                    "name": existing[0].get("name", ""),
                    "freq": freq, "source": "partial",
                    "records": existing, "total": len(existing),
                    "elapsed_s": round(time.time() - t0, 3),
                }
            return {"success": False, "error": str(e)}


    def _try_db_partial(self, symbol: str, start_d: date, end_d: date) -> List[Dict]:
        """从 DB 读取已有数据（不检查完整性），供合并场景使用"""
        try:
            records = self._db_query(symbol, start_d, end_d)
            return records
        except Exception:
            return []

    def _try_mootdx(self, symbol: str, freq: str,
                    start_d: date, end_d: date,
                    t0: float) -> Dict:
        """最后兜底：从 mootdx 获取数据"""
        log.info(f"[kline_query] mootdx 兜底: {symbol} {freq} [{start_d}~{end_d}]")

        try:
            # 获取股票名称
            name = mootdx_kline_service._get_stock_name(symbol)

            # 调用 mootdx 获取
            freq_code = mootdx_kline_service.FREQ_MAP.get(freq)
            if freq_code is None:
                return {"success": False, "error": f"未知频率: {freq}"}

            offset = mootdx_kline_service._calc_offset(start_d, end_d, freq_code)
            df = mootdx_kline_service._fetch_one_raw(symbol, freq_code, offset)
            if df is None:
                return {
                    "success": False, "error": f"mootdx 拉取失败: {symbol}",
                    "symbol": symbol, "freq": freq,
                    "elapsed_s": round(time.time() - t0, 3),
                }

            records = mootdx_kline_service._df_to_records(df, symbol, name, start_d, end_d)
            if not records:
                return {
                    "success": True, "symbol": symbol, "name": name,
                    "freq": freq, "source": "mootdx",
                    "records": [], "total": 0,
                    "elapsed_s": round(time.time() - t0, 3),
                }

            # 写 DB
            queued, year_cnt = mootdx_kline_service._async_persist_kline(records, freq)

            # 写 Redis Hash（双写）
            h_cached = kline_redis_service.kline_hset_batch(records, freq)

            # 标记完整性
            for yr in {r.get("year") for r in records if r.get("year")}:
                yr_expected = self._calc_expected_count(
                    date(int(yr), 1, 1), date(int(yr), 12, 31), freq
                )
                kline_redis_service.kline_hset_complete(symbol, freq, int(yr), yr_expected)

            log.info(f"[kline_query] mootdx 完成: {symbol} records={len(records)} "
                     f"db={queued} redis_hash={h_cached}")

            return {
                "success": True, "symbol": symbol, "name": name,
                "freq": freq, "source": "mootdx",
                "records": records, "total": len(records),
                "queued_to_db": queued, "redis_hash": h_cached,
                "elapsed_s": round(time.time() - t0, 3),
            }

        except Exception as e:
            log.error(f"[kline_query] mootdx 兜底异常: {e}")
            return {"success": False, "error": str(e)}


    # ─── 全市场三层查询 ────────────────────────────────────────────

    def get_kline_full_market_with_cache(
        self,
        freq: str = "day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        全市场三层缓存查询主入口（Redis → DB → mootdx）

        Args:
            freq: day / week / month
            start_date: 起始日期
            end_date: 结束日期
            task_id: SSE 任务 ID（用于进度推送，不传则不推送）

        Returns:
            全市场 K 线数据汇总
        """
        from concurrent.futures import ThreadPoolExecutor
        from .kline_sse_streamer import kline_sse_streamer

        t0 = time.time()
        log.info(f"[全市场采集] 开始: freq={freq}, range=[{start_date}~{end_date}]")

        # 1. 日期解析与交易日校验
        start_d = self._parse_date(start_date or "", 30)
        end_d = self._parse_date(end_date or "", 0)

        if start_d > end_d:
            return {"success": False, "error": "start_date 不能晚于 end_date"}

        # 计算预期交易日数
        trading_result = get_trading_days(start_d, end_d)
        trading_days = trading_result.get('data', {}).get('trading_day', [])
        if not trading_days:
            result = {
                "success": True, "mode": "full_market",
                "total_stocks": 0, "total_records": 0,
                "message": "日期范围内无交易日",
                "elapsed_s": round(time.time() - t0, 3),
            }
            if task_id:
                kline_sse_streamer.set_status(task_id, "completed")
            return result

        expected_per_stock = len(trading_days)

        # 2. 加载全市场活跃股票列表
        stocks = mootdx_kline_service._load_active_stocks()  # [(symbol, name), ...]
        total_stocks = len(stocks)
        log.info(f"[全市场采集] 加载到 {total_stocks} 只活跃股票")

        if task_id:
            kline_sse_streamer.update_progress(
                task_id, total=total_stocks, current=0,
                message="已加载股票列表，开始检查 Redis 缓存"
            )

        # 3. 第1层：按年份检查 Redis 完整性
        years = sorted({d.year for d in trading_days})
        redis_complete_stocks = set()
        redis_results = {}

        try:
            r = kline_redis_service._get_client()
            if r:
                for yr in years:
                    # 方案B：批量检查完整性标记（避免 5000 次 hget）
                    pipe = r.pipeline()
                    for symbol, _ in stocks:
                        key = kline_redis_service._build_hash_key(freq, symbol, yr)
                        pipe.hget(key, "__complete__")
                    results = pipe.execute()

                    for i, (symbol, name) in enumerate(stocks):
                        if symbol in redis_complete_stocks:
                            continue
                        if results[i] and int(results[i]) >= expected_per_stock:
                            # Redis 完整，读取数据
                            records = kline_redis_service.kline_hget_range(symbol, freq, start_d, end_d)
                            if records:
                                redis_complete_stocks.add(symbol)
                                redis_results[symbol] = records
                                if task_id:
                                    kline_sse_streamer.add_stock_result(task_id, symbol, records, "redis")
        except Exception as e:
            log.warning(f"[全市场采集] Redis 层异常: {e}")

        redis_count = len(redis_complete_stocks)
        log.info(f"[全市场采集] Redis 命中: {redis_count}/{total_stocks}")

        if task_id:
            kline_sse_streamer.update_progress(task_id, redis_done=redis_count)
            if redis_count == total_stocks:
                # 全部命中 Redis，直接返回
                result = {
                    "success": True, "mode": "full_market",
                    "total_stocks": total_stocks,
                    "completed_stocks": total_stocks,
                    "total_records": sum(len(r) for r in redis_results.values()),
                    "source": "redis",
                    "results": redis_results,
                    "elapsed_s": round(time.time() - t0, 3),
                }
                kline_sse_streamer.set_status(task_id, "completed")
                return result

        # 4. 第2层：DB 查询（仅 Redis 不完整的股票）
        remaining_stocks = [(s, n) for s, n in stocks if s not in redis_complete_stocks]
        db_complete_stocks = set()
        db_results = {}

        if remaining_stocks:
            log.info(f"[全市场采集] DB 查询: {len(remaining_stocks)} 只")
            if task_id:
                kline_sse_streamer.update_progress(
                    task_id, current=redis_count,
                    message=f"Redis 命中 {redis_count} 只，开始 DB 查询"
                )

            # 按年份批量查询（避免 N+1）
            for yr in years:
                table_name = get_kline_full_table_name(yr)
                symbols_in_year = [s for s, _ in remaining_stocks if s not in db_complete_stocks]

                if not symbols_in_year:
                    continue

                try:
                    # 批量聚合查询完整性
                    conn = get_conn()
                    try:
                        with conn.cursor() as cur:
                            placeholders = ", ".join(["%s"] * len(symbols_in_year))
                            sql = f"""
                                SELECT symbol, COUNT(DISTINCT DATE(datetime)) as cnt
                                FROM {table_name}
                                WHERE symbol IN ({placeholders})
                                  AND DATE(datetime) >= %s AND DATE(datetime) <= %s
                                GROUP BY symbol
                            """
                            params = symbols_in_year + [start_d.isoformat(), end_d.isoformat()]
                            cur.execute(sql, params)
                            completeness = {row["symbol"]: row["cnt"] for row in cur.fetchall()}
                    finally:
                        conn.close()

                    # 找出 DB 完整的股票，读取详细数据
                    db_complete_this_year = {
                        s for s, cnt in completeness.items() if cnt >= expected_per_stock
                    }

                    # 批量读取这些股票的详细数据
                    if db_complete_this_year:
                        for symbol in db_complete_this_year:
                            if symbol in db_complete_stocks:
                                continue
                            records = self._db_query(symbol, start_d, end_d)
                            if records:
                                db_complete_stocks.add(symbol)
                                db_results[symbol] = records
                                # 回填 Redis
                                kline_redis_service.kline_hset_batch(records, freq)
                                kline_redis_service.kline_hset_complete(symbol, freq, yr, expected_per_stock)

                                if task_id:
                                    kline_sse_streamer.add_stock_result(task_id, symbol, records, "db")
                except Exception as e:
                    log.warning(f"[全市场采集] DB 层异常 year={yr}: {e}")

            db_count = len(db_complete_stocks)
            log.info(f"[全市场采集] DB 命中: {db_count}/{len(remaining_stocks)}")

            if task_id:
                kline_sse_streamer.update_progress(task_id, db_done=db_count)

        # 5. 第3层：mootdx 兜底采集（仅 Redis+DB 都不完整的股票）
        mootdx_stocks = [
            (s, n) for s, n in remaining_stocks
            if s not in db_complete_stocks
        ]
        mootdx_results = {}
        failed_stocks = []
        total_records = sum(len(r) for r in redis_results.values()) + sum(len(r) for r in db_results.values())

        if mootdx_stocks:
            log.info(f"[全市场采集] mootdx 兜底: {len(mootdx_stocks)} 只")
            if task_id:
                kline_sse_streamer.update_progress(
                    task_id, current=redis_count + db_count,
                    message=f"DB 命中 {db_count} 只，开始 mootdx 采集"
                )

            # 复用现有 16 线程并发逻辑
            def worker(sym, name):
                nonlocal total_records
                try:
                    freq_code = mootdx_kline_service.FREQ_MAP.get(freq)
                    if freq_code is None:
                        failed_stocks.append(sym)
                        return

                    offset = mootdx_kline_service._calc_offset(start_d, end_d, freq_code)
                    df = mootdx_kline_service._fetch_one_raw(sym, freq_code, offset)
                    if df is None:
                        failed_stocks.append(sym)
                        return

                    records = mootdx_kline_service._df_to_records(df, sym, name, start_d, end_d)
                    if not records:
                        return

                    # 双写 DB + Redis
                    mootdx_kline_service._async_persist_kline(records, freq)
                    kline_redis_service.kline_hset_batch(records, freq)

                    # 标记完整
                    for yr in {r["year"] for r in records}:
                        yr_result = get_trading_days(
                            date(yr, 1, 1), date(yr, 12, 31)
                        )
                        yr_trading = yr_result.get('data', {}).get('trading_day', [])
                        kline_redis_service.kline_hset_complete(sym, freq, yr, len(yr_trading))

                    mootdx_results[sym] = records
                    total_records += len(records)

                    if task_id:
                        kline_sse_streamer.add_stock_result(task_id, sym, records, "mootdx")
                        kline_sse_streamer.update_progress(
                            task_id,
                            mootdx_done=len(mootdx_results),
                            failed=len(failed_stocks),
                            records=total_records,
                            current=redis_count + db_count + len(mootdx_results),
                        )
                except Exception as e:
                    log.error(f"[全市场采集] {sym} 失败: {e}")
                    failed_stocks.append(sym)

            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(worker, s, n) for s, n in mootdx_stocks]
                for f in futures:
                    try:
                        f.result(timeout=15)
                    except Exception as e:
                        log.warning(f"[全市场采集] 线程异常: {e}")

        # 6. 结果汇总
        log.info(
            f"[全市场采集] 完成: total={total_stocks}, "
            f"redis={redis_count}, db={len(db_complete_stocks)}, mootdx={len(mootdx_results)}, "
            f"failed={len(failed_stocks)}, records={total_records}, "
            f"elapsed={time.time() - t0:.2f}s"
        )

        if task_id:
            kline_sse_streamer.set_status(task_id, "completed")

        return {
            "success": True,
            "mode": "full_market",
            "total_stocks": total_stocks,
            "completed_stocks": redis_count + len(db_complete_stocks) + len(mootdx_results),
            "failed_stocks": len(failed_stocks),
            "failed_list": failed_stocks[:20],
            "total_records": total_records,
            "source_breakdown": {
                "redis": redis_count,
                "db": len(db_complete_stocks),
                "mootdx": len(mootdx_results),
            },
            "elapsed_s": round(time.time() - t0, 3),
        }


# 模块级单例
kline_query_layer = KlineQueryLayer()