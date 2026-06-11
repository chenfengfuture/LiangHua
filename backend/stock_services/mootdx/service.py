#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    mootdx K线服务
  · 日/周/月线 get_kline()
        - 支持 单股 / 多股 / 全市场（symbol=None）
        - 写入路径：Redis Hash（TTL 30 天） + 直接批量 upsert（跳过通用 schema 层）
        - 跨年分表通过 ensure_kline_year_table() 懒建

  · 分钟线 get_minute_kline()
        - 强制单股，symbol 必传
        - 写入路径：Redis Hash（TTL 24 小时），不入库
        - freq ∈ {1, 5, 15, 30, 60}

"""

import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any, Dict

from utils.db import get_cursor
from stock_services.common.date_utils import get_trading_days

from stock_services.common.connection import DatabaseContext
from stock_services.common.response import ok_result, fail_result as _common_fail_result

from .base_service import MootdxBaseService, FREQ_MAP, DAILY_FREQ_CODES, HARDCODED_WORKERS, MINUTE_BARS_OFFSET
from .kline_redis import kline_redis_service
from .table_helper import (
    ensure_kline_year_table,
    ensure_kline_year_tables,
    get_kline_full_table_name,
)

log = logging.getLogger("mootdx_kline")


class MootdxKlineService(MootdxBaseService):
    """mootdx K 线服务（日/周/月 + 分钟线双轨），继承 MootdxBaseService"""

    FREQ_MAP = FREQ_MAP
    LOGGER_NAME = "mootdx_kline"

    def __init__(self):
        super().__init__(service_name="MootdxKlineService")

    # ─── 股票基础数据 ───────────────────────────────────────────────

    def _load_active_stocks(self):
        """加载全市场活跃股票（剔除退市 + 北交所 BJ，mootdx 不支持北交所）"""
        with DatabaseContext(commit=False) as cur:
            cur.execute(
                "SELECT symbol, name FROM stocks_info "
                "WHERE is_active = 1 AND market IS NOT NULL ORDER BY symbol"
            )
            return [(r["symbol"], r["name"]) for r in cur.fetchall()]

    def _load_existing_complete_stocks(self, start_d: date, end_d: date, freq: str) -> set:
        """
        【方案B】预检查哪些股票在目标日期范围已有完整数据。

        仅在日线且单一年份时生效。一次 SQL 查询所有已完整覆盖的 symbol，
        后续全量采集时跳过这些股票，减少 mootdx 请求 ~90%。

        Returns:
            已有完整数据的 symbol set（如 {'000001','000002',...}）
        """
        if freq != "day":
            return set()

        trading_result = get_trading_days(start_d, end_d)
        trading_days = trading_result.get('data', {}).get('trading_day', [])
        if not trading_days:
            return set()

        # 确定涉及的年表（仅单一年份支持，跨年跳过预检）
        years = {d.year for d in trading_days}
        if len(years) != 1:
            return set()

        year = years.pop()
        table = get_kline_full_table_name(year)
        tgt_count = len(trading_days)
        start_str = start_d.isoformat()
        end_str = end_d.isoformat()

        try:
            with DatabaseContext(commit=False) as cur:
                sql = f"""
                    SELECT symbol
                    FROM {table}
                    WHERE DATE(datetime) >= %s AND DATE(datetime) <= %s
                    GROUP BY symbol
                    HAVING COUNT(DISTINCT DATE(datetime)) >= %s
                """
                cur.execute(sql, (start_str, end_str, tgt_count))
                return {r["symbol"] for r in cur.fetchall()}
        except Exception as e:
            log.warning(f"[mootdx] 预查已有数据失败（不影响主流程）: {e}")
            return set()

    def _get_stock_name(self, symbol):
        """单股查名称"""
        with DatabaseContext(commit=False) as cur:
            cur.execute("SELECT name FROM stocks_info WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
            return row["name"] if row else ""

    # ─── 核心拉取 ────────────────────────────────────────────────────

    def _fetch_one_raw(self, symbol, freq_code, offset):
        """单股 bars() 调用 → DataFrame 或 None"""
        client = self._get_mootdx_client()
        if not client:
            return None

        try:
            df = client.bars(symbol=symbol, frequency=freq_code, start=0, offset=offset)
            self._reset_timeout()
            return df
        except Exception:
            self._inc_timeout()
            return None

    # ─── DataFrame → records 转换 ────────────────────────────────────

    def _df_to_records(self, df, symbol, name, start_d, end_d):
        """日/周/月线 DataFrame → records（含日期过滤）"""
        if df is None or (hasattr(df, "empty") and df.empty):
            return []

        records = []
        for _, row in df.iterrows():
            dt_val = row.get("datetime", "")
            if not dt_val:
                continue

            dt_str = str(dt_val)[:10]
            try:
                row_date = datetime.strptime(dt_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if row_date < start_d or row_date > end_d:
                continue

            try:
                vol_v = float(row.get("vol", 0) or row.get("volume", 0) or 0)
                records.append({
                    "symbol": symbol,
                    "name": name,
                    "datetime": datetime(row_date.year, row_date.month, row_date.day, 15, 0, 0),
                    "year": row_date.year,
                    "month": row_date.month,
                    "day": row_date.day,
                    "hour": 15,
                    "minute": 0,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "vol": vol_v,
                    "amount": float(row.get("amount", 0) or 0),
                    "volume": vol_v,
                })
            except Exception:
                continue

        return records

    def _df_to_records_minute(self, df, symbol, name, start_d, end_d):
        """分钟线 DataFrame → records（含 hour/minute + 日期过滤）"""
        if df is None or (hasattr(df, "empty") and df.empty):
            return []

        records = []
        for _, row in df.iterrows():
            dt_val = row.get("datetime", "")
            if not dt_val:
                continue

            dt_str = str(dt_val)
            try:
                dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt = datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")
                except ValueError:
                    continue

            row_date = dt.date()
            if row_date < start_d or row_date > end_d:
                continue

            try:
                vol_v = float(row.get("vol", 0) or row.get("volume", 0) or 0)
                records.append({
                    "symbol": symbol,
                    "name": name,
                    "datetime": dt,
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": dt.hour,
                    "minute": dt.minute,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "vol": vol_v,
                    "amount": float(row.get("amount", 0) or 0),
                    "volume": vol_v,
                })
            except Exception:
                continue

        return records

    # ─── 异步入库辅助 ───────────────────────────────────────────────

    # K 线表硬编码字段（跳过 schema_cache 通用查询）
    KLINE_COLS = [
        'symbol', 'name', 'datetime', 'open', 'high', 'low', 'close',
        'vol', 'amount', 'volume', 'year', 'month', 'day', 'hour', 'minute',
    ]
    KLINE_BATCH_SIZE = 1000

    def _batch_upsert_kline(self, table_name: str, records: list) -> int:
        """
        【方案A+B】K 线专用批量 upsert，跳过通用 schema_cache 层。
        （增加异常重试机制）

        - 硬编码字段列表（KLINE_COLS），无 INFORMATION_SCHEMA 查询
        - 分 1000 条/批执行 executemany（KLINE_BATCH_SIZE）
        - INSERT ... ON DUPLICATE KEY UPDATE 幂等覆盖
        - 每批最多重试 1 次，应对 MySQL 连接闪断

        Args:
            table_name: "stock_klines.stock_klines_YYYY"
            records: K 线记录列表

        Returns:
            写入条数
        """
        if not records:
            return 0

        cols = self.KLINE_COLS
        q_cols = ', '.join(f'`{c}`' for c in cols)
        placeholders = ', '.join(['%s'] * len(cols))
        # 仅主键字段不更新（symbol+datetime 是 UNIQUE KEY）
        update_part = ', '.join(
            f'`{c}`=VALUES(`{c}`)' for c in cols if c not in ('symbol', 'datetime')
        )

        sql = (
            f"INSERT INTO {table_name} ({q_cols}) "
            f"VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_part}"
        )

        total = 0
        bs = self.KLINE_BATCH_SIZE
        for i in range(0, len(records), bs):
            batch = records[i:i + bs]
            params = [[r.get(c) for c in cols] for r in batch]
            try:
                with get_cursor(commit=True) as cur:
                    cur.executemany(sql, params)
                    total += len(batch)
            except Exception as e:
                # 单次重试，应对 MySQL 连接闪断
                log.warning(f"[mootdx] upsert 失败（重试1次）: {e}")
                try:
                    time.sleep(0.5)
                    with get_cursor(commit=True) as cur:
                        cur.executemany(sql, params)
                        total += len(batch)
                        log.info(f"[mootdx] upsert 重试成功: {table_name} batch_size={len(batch)}")
                except Exception as e2:
                    log.error(f"[mootdx] upsert 重试也失败: {e2}")

        return total

    def _async_persist_kline(self, records, freq):
        """
        日/周/月线直接批量入库到 stock_klines_{year}

        方案A+B：不再走 AsyncWriter 通用路径，直接 executemany
        硬编码字段 + 每批 1000 条，写入 5 万条 < 2s

        Returns:
            (写入条数, 年份数)
        """
        if not records:
            return 0, 0

        by_year = defaultdict(list)
        for r in records:
            try:
                by_year[int(r["year"])].append(r)
            except Exception:
                continue

        if not by_year:
            return 0, 0

        # 提前建表
        ensure_kline_year_tables(by_year.keys())

        total_written = 0
        for year, year_records in by_year.items():
            table_name = get_kline_full_table_name(year)
            written = self._batch_upsert_kline(table_name, year_records)
            total_written += written
            log.info(f"[mootdx] 批量入库 {table_name} {written}/{len(year_records)} 条")

        return total_written, len(by_year)

    # ─── 全市场并发（仅日/周/月线）─────────────────────────────────

    def _get_kline_full_market(self, start_d, end_d, freq, freq_code, offset, t0):
        """
        全市场 K 线并发拉取（仅日/周/月线）

        策略（已优化）：
          1. 加载活跃股票列表（is_active=1）
          2. 【方案B】预查 DB 已有完整数据的股票 → 跳过，减少 ~90% mootdx 请求
          3. 【方案A】32 线程池并发 → 纯拉取 + 基础转换
          4. 【方案D】精确 offset 按天数倒推（已实现）
          5. 后置统一写 Redis + 直接批量 upsert（方案A+B）
        """
        stocks = self._load_active_stocks()
        if not stocks:
            return {"success": False, "error": "未找到活跃股票"}

        total_all = len(stocks)

        # ★ 方案B：预检查已有数据的股票，跳过 mootdx
        existing_set = self._load_existing_complete_stocks(start_d, end_d, freq)
        stocks_to_fetch = [(s, n) for s, n in stocks if s not in existing_set]
        skip_count = len(existing_set)
        total_fetch = len(stocks_to_fetch)

        log.info(
            f"[mootdx] ★ 全市场 K 线采集开始 "
            f"stocks={total_all} workers={HARDCODED_WORKERS} "
            f"freq={freq} range=[{start_d},{end_d}] offset={offset} "
            f"[方案B]skip_existing={skip_count} to_fetch={total_fetch}"
        )

        all_records = []
        failed_list = []
        lock = threading.Lock()
        done_count = 0

        def worker(sym, name):
            nonlocal done_count
            df = self._fetch_one_raw(sym, freq_code, offset)
            if df is None:
                with lock:
                    failed_list.append(sym)
                    done_count += 1
                return

            recs = self._df_to_records(df, sym, name, start_d, end_d)

            with lock:
                all_records.extend(recs)
                done_count += 1
                if done_count % 200 == 0 or done_count == total_fetch:
                    elapsed = time.time() - t0
                    log.info(
                        f"[mootdx] 进度 {done_count}/{total_fetch}  "
                        f"records={len(all_records)} failed={len(failed_list)}  "
                        f"elapsed={elapsed:.1f}s"
                    )

        if total_fetch > 0:
            with ThreadPoolExecutor(max_workers=HARDCODED_WORKERS) as executor:
                futures = {executor.submit(worker, s, n): (s, n) for s, n in stocks_to_fetch}
                for _ in as_completed(futures):
                    pass

        # 1. 写 Redis Hash（压缩版）
        h_cached = kline_redis_service.kline_hset_batch(all_records, freq)

        # 2. 异步入库
        queued, year_cnt = self._async_persist_kline(all_records, freq)

        elapsed = time.time() - t0
        log.info(
            f"[mootdx] ★ 全市场采集完成 "
            f"stocks={total_all} fetched={total_fetch} "
            f"skip_existing={skip_count} records={len(all_records)} "
            f"redis_hash={h_cached} queued_to_db={queued}(years={year_cnt}) "
            f"failed={len(failed_list)} elapsed={elapsed:.1f}s"
        )

        return {
            "success": True,
            "total": total_all,
            "fetched": total_fetch,
            "skipped_existing": skip_count,
            "records": len(all_records),
            "redis_hash": h_cached,
            "queued_to_db": queued,
            "year_count": year_cnt,
            "failed": len(failed_list),
            "failed_list": failed_list,
            "elapsed_s": round(elapsed, 2),
        }

    # ─── 主入口 1：日/周/月线 ─────────────────────────────────────

    def get_kline(self, symbol=None, freq="day", start_date=None, end_date=None, **kwargs):
        """
        获取日/周/月 K 线 + Redis 缓存 + 异步入库

        Args:
            symbol:     None=全市场 / "000001"=单股 / "000001,600519"=多股 / list
            freq:       day / week / month
            start_date: YYYYMMDD 或 YYYY-MM-DD（不传=30天前）
            end_date:   YYYYMMDD 或 YYYY-MM-DD（不传=今天）

        Returns:
            {success, total, records, redis_cached, queued_to_db, failed, elapsed_s}
        """
        t0 = time.time()

        freq_code = FREQ_MAP.get(freq)
        if freq_code is None:
            return {"success": False, "error": f"未知频率: {freq}"}

        # get_kline 只接受日/周/月线，分钟线请走 get_minute_kline
        if freq_code not in DAILY_FREQ_CODES:
            return {
                "success": False,
                "error": f"freq={freq} 不属于日/周/月线，请使用 get_minute_kline",
            }

        start_d = self._parse_date(start_date, 30)
        end_d = self._parse_date(end_date, 0)

        # ★ 交易日验证：过滤非交易日，只采集有效交易日的数据
        valid_start, valid_end, skipped_days = self._validate_date_range(start_d, end_d, freq)
        if skipped_days > 0:
            log.info(
                f"[mootdx] 日期范围 {start_d}~{end_d} 包含 {skipped_days} 个非交易日，"
                f"已过滤为 {valid_start}~{valid_end}（仅交易日报表）"
            )
        if valid_start is None:
            return {
                "success": False,
                "error": f"日期范围 {start_d}~{end_d} 内无交易日，请重新选择日期",
                "skipped_non_trading_days": skipped_days,
            }


        start_d, end_d = valid_start, valid_end

        offset = self._calc_offset(start_d, end_d, freq_code)


        # ── 全市场（symbol=None）─────────────────────────────────
        if symbol is None:
            return self._get_kline_full_market(start_d, end_d, freq, freq_code, offset, t0)

        # ── 单股 / 多股 ─────────────────────────────────────────
        if isinstance(symbol, list):
            syms = [str(s).strip() for s in symbol if str(s).strip()]
        elif isinstance(symbol, str) and "," in symbol:
            syms = [s.strip() for s in symbol.split(",") if s.strip()]
        else:
            syms = [str(symbol).strip()]

        all_records = []
        failed = []

        for sym in syms:
            name = self._get_stock_name(sym)
            df = self._fetch_one_raw(sym, freq_code, offset)
            if df is None:
                failed.append(sym)
                continue
            recs = self._df_to_records(df, sym, name, start_d, end_d)
            all_records.extend(recs)

        # 写 Redis Hash + 异步入库
        h_cached = kline_redis_service.kline_hset_batch(all_records, freq)
        queued, year_cnt = self._async_persist_kline(all_records, freq)

        elapsed = time.time() - t0
        log.info(
            f"[mootdx] 单股/多股完成 syms={len(syms)} records={len(all_records)} "
            f"redis_hash={h_cached} queued_to_db={queued} "
            f"failed={len(failed)} elapsed={elapsed:.2f}s"
        )

        return {
            "success": True,
            "total": len(syms),
            "data": all_records,
            "records": len(all_records),
            "redis_hash": h_cached,
            "queued_to_db": queued,
            "year_count": year_cnt,
            "failed": len(failed),
            "failed_list": failed,
            "elapsed_s": round(elapsed, 2),
        }


    # ─── 主入口 2：分钟线 ────────────────────────────────────────

    def get_minute_kline(self, symbol, freq="5", start_date=None, end_date=None, **kwargs):
        """
        获取分钟 K 线 — 仅 Redis 缓存（TTL 24h），不入库

        Args:
            symbol:     必传，单股代码
            freq:       1 / 5 / 15 / 30 / 60
            start_date: YYYYMMDD 或 YYYY-MM-DD
            end_date:   YYYYMMDD 或 YYYY-MM-DD

        Returns:
            {success, data: [...records...], redis_cached, elapsed_s}
        """
        t0 = time.time()

        # ★ symbol 必传校验
        if not symbol or (isinstance(symbol, str) and not symbol.strip()):
            return {"success": False, "error": "分钟线必须传入 symbol（股票代码）"}

        # 仅取单股（即使传 list 也只取第一个）
        if isinstance(symbol, list):
            sym = str(symbol[0]).strip() if symbol else ""
        elif isinstance(symbol, str) and "," in symbol:
            sym = symbol.split(",")[0].strip()
        else:
            sym = str(symbol).strip()

        if not sym:
            return {"success": False, "error": "分钟线必须传入 symbol（股票代码）"}

        freq_code = FREQ_MAP.get(str(freq))
        if freq_code is None or freq_code in DAILY_FREQ_CODES:
            return {
                "success": False,
                "error": f"freq={freq} 不是有效的分钟线频率（1/5/15/30/60）",
            }

        start_d = self._parse_date(start_date, 30)
        end_d = self._parse_date(end_date, 0)
        offset = self._calc_offset(start_d, end_d, freq_code)

        name = self._get_stock_name(sym)
        df = self._fetch_one_raw(sym, freq_code, offset)
        if df is None:
            return {
                "success": False,
                "error": f"mootdx 拉取失败: {sym}",
                "symbol": sym,
                "elapsed_s": round(time.time() - t0, 2),
            }

        records = self._df_to_records_minute(df, sym, name, start_d, end_d)

        # 仅写 Redis Hash（TTL 24h），不入库
        h_cached = kline_redis_service.minute_hset_batch(records, str(freq))

        elapsed = time.time() - t0
        log.info(
            f"[mootdx] 分钟线完成 symbol={sym} freq={freq} "
            f"records={len(records)} redis_hash={h_cached} elapsed={elapsed:.2f}s"
        )

        # 序列化 datetime 为字符串方便前端使用
        data_out = []
        for r in records:
            r_out = dict(r)
            if isinstance(r_out.get("datetime"), datetime):
                r_out["datetime"] = r_out["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            data_out.append(r_out)

        return {
            "success": True,
            "symbol": sym,
            "name": name,
            "freq": str(freq),
            "data": data_out,
            "records": len(data_out),
            "redis_hash": h_cached,
            "elapsed_s": round(elapsed, 2),
        }


# ═══════════════════════════════════════════════════════════════════
#  模块级单例 & 包装函数
# ═══════════════════════════════════════════════════════════════════

mootdx_kline_service = MootdxKlineService()


def get_kline_data(symbol=None, period="day", start_date=None, end_date=None, **kwargs):
    """
    路由 /api/stock/get-stock-zh-a-hist-min-em 的入口函数

    根据 period 自动分流：
      · day/week/month → get_kline（日/周/月线，可全市场，异步入库）
      · 1/5/15/30/60   → get_minute_kline（分钟线，必传 symbol，仅 Redis）
    """
    p = str(period)
    freq_code = FREQ_MAP.get(p)

    if freq_code is None:
        return {"success": False, "error": f"未知 period: {period}"}

    if freq_code in DAILY_FREQ_CODES:
        return mootdx_kline_service.get_kline(
            symbol=symbol, freq=p, start_date=start_date, end_date=end_date,
        )
    else:
        return mootdx_kline_service.get_minute_kline(
            symbol=symbol, freq=p, start_date=start_date, end_date=end_date,
        )


def get_mootdx_minute_kline(symbol, period="5", start_date=None, end_date=None, **kwargs):
    """分钟线专用入口（薄包装 get_minute_kline）"""
    return mootdx_kline_service.get_minute_kline(
        symbol=symbol, freq=str(period),
        start_date=start_date, end_date=end_date,
    )


# ─── 统一响应格式（委派至 common/response）────────────────────────

def _ok(data: Any) -> Dict:
    """成功响应"""
    return ok_result(data=data)


def _fail(msg: str) -> Dict:
    """失败响应"""
    return _common_fail_result(message=msg)


# ─── 三层缓存查询 & WS 采集（路由层调用的服务入口）───────────────

# 全市场采集并发锁（避免同时跑多个任务）
_full_market_lock = threading.Lock()
_full_market_running = False


def query_kline_with_cache(
    symbol=None, freq="day", start_date=None, end_date=None, mode="overwrite",
    use_sse=True,
):
    """
    三层缓存 K 线查询（路由层统一入口）。

    所有返回路径统一包裹为 {success, message, data} 格式。

    根据 symbol 自动分流：
      · None / 空字符串 → 全市场三层查询（可选 SSE 流式返回）
      · 单股            → KlineQueryLayer.get_kline_with_cache()
      · 多股(逗号分隔)  → 每只独立三层查询，合并结果

    Args:
        use_sse: 全市场采集时是否使用 SSE 流式返回
                 True 时返回 {'task_id': ...}，前端通过 SSE 端点接收流式数据
    """
    from .kline_query import kline_query_layer as _ql
    from .kline_sse_streamer import kline_sse_streamer

    try:
        # ── 全市场采集（symbol=None 或 空字符串）─────────────
        if symbol is None or (isinstance(symbol, str) and not symbol.strip()):
            global _full_market_running

            # 防并发：同一时间只跑一个全市场采集
            with _full_market_lock:
                if _full_market_running:
                    return _fail("全市场采集正在进行中，请稍后再试")
                _full_market_running = True

            try:
                # 创建 SSE 任务
                task_id = kline_sse_streamer.create_task({
                    "freq": freq, "start_date": start_date, "end_date": end_date
                })

                # 启动后台采集线程（不阻塞 HTTP 响应）
                def _collect_worker():
                    global _full_market_running
                    try:
                        kline_sse_streamer.set_status(task_id, "running")
                        _ql.get_kline_full_market_with_cache(
                            freq=freq, start_date=start_date, end_date=end_date,
                            task_id=task_id,
                        )
                    except Exception as e:
                        log.error(f"[全市场采集] 后台线程异常: {e}")
                        kline_sse_streamer.add_error(task_id, str(e))
                        kline_sse_streamer.set_status(task_id, "failed")
                    finally:
                        _full_market_running = False

                t = threading.Thread(target=_collect_worker, daemon=True, name=f"kline-sse-{task_id}")
                t.start()

                # 立即返回 task_id，前端通过 SSE 端点订阅
                return _ok({
                    "task_id": task_id,
                    "mode": "sse_stream",
                    "hint": "请调用 SSE 端点 /api/stock/get-kline/sse/{task_id} 接收流式数据",
                })

            except Exception as e:
                _full_market_running = False
                raise e

        # ── 单股 / 多股（原有逻辑不变）─────────────────────────
        s = str(symbol).strip()
        parts = [x.strip() for x in s.split(",") if x.strip()]

        if len(parts) == 1:
            result = _ql.get_kline_with_cache(
                symbol=parts[0], freq=freq,
                start_date=start_date, end_date=end_date,
            )
            if not result.get("success"):
                return _fail(result.get("error", "查询失败"))
            return _ok(result)
        else:
            all_records = []
            failed = []
            for sym in parts:
                r = _ql.get_kline_with_cache(
                    symbol=sym, freq=freq,
                    start_date=start_date, end_date=end_date,
                )
                if r.get("success"):
                    all_records.extend(r.get("records", []))
                else:
                    failed.append(sym)
            return _ok({
                "total": len(parts),
                "total_records": len(all_records),
                "records": all_records,
                "failed": len(failed),
                "failed_list": failed,
            })

    except Exception as e:
        log.error(f"query_kline_with_cache 异常: {e}")
        return _fail(str(e))


def trigger_ws_kline_collect(freq="day", start_date=None, end_date=None):
    """
    启动 WebSocket 流式采集（路由层入口）。

    返回 task_id，前端订阅 kline 频道接收进度推送。
    """
    from .kline_ws_collector import kline_ws_collector as _wsc
    try:
        task_id = _wsc.start_collect({
            "symbol": None,
            "freq": freq,
            "start_date": start_date,
            "end_date": end_date,
        })
        return _ok({
            "task_id": task_id,
            "freq": freq,
            "hint": "前端请先订阅 kline 频道接收进度",
        })
    except Exception as e:
        log.error(f"trigger_ws_kline_collect 异常: {e}")
        return _fail(str(e))


# ═══════════════════════════════════════════════════════════════════
#  自愈型收盘采集线程
# ═══════════════════════════════════════════════════════════════════

_kline_collector_started = False
_kline_collector_lock = threading.Lock()


def start_daily_kline_collector():
    """
    启动后台 daemon 线程：收盘后自动采集当日 K 线数据。

    自愈特性：
      - 进程在任何时间重启 → 检查是否已过 16:00 → 立即触发补采
      - 非交易日 → 静默跳过
      - 已有数据的日期 → 预检跳过，不重复拉 mootdx
      - 每小时检查一次，确保当天数据无论如何都会被采集

    在 FastAPI lifespan 中调用，不阻塞启动。
    """
    global _kline_collector_started
    with _kline_collector_lock:
        if _kline_collector_started:
            return
        _kline_collector_started = True

    def _loop():
        log.info("[自动采集] 后台线程已启动，每小时检查一次收盘状态")
        while True:
            now = datetime.now()
            today_str = now.strftime("%Y%m%d")

            # 只有收盘后（>=16:00）且是交易日才触发
            if now.hour >= 16 and MootdxKlineService.is_trading_day(now.date()):
                log.info(f"[自动采集] 开始检查 {today_str} 日K线数据...")
                try:
                    result = mootdx_kline_service.get_kline(
                        symbol=None, freq="day",
                        start_date=today_str, end_date=today_str,
                    )
                    if not result.get("success"):
                        log.warning(f"[自动采集] {today_str} 采集失败: {result.get('error')}")
                    else:
                        log.info(
                            f"[自动采集] {today_str} 完成: "
                            f"skip={result.get('skipped_existing', 0)} "
                            f"records={result.get('records', 0)} "
                            f"queued={result.get('queued_to_db', 0)} "
                            f"elapsed={result.get('elapsed_s', 0):.1f}s"
                        )
                        # 采集完成 → 触发指标计算（事件驱动，替代轮询）
                        try:
                            from stock_services.services.stock_indicator_service import stock_indicator_service
                            log.info("[自动采集] 触发指标计算...")
                            stock_indicator_service.compute_today()
                        except Exception as e:
                            log.warning(f"[自动采集] 指标计算触发失败: {e}")

                        # 写入 Redis 采集完成标记（供指标安全网等组件检测）
                        try:
                            from utils.redis_client_compat import _get_client as _rc_get
                            _rc = _rc_get()
                            if _rc:
                                _rc.set(f"kline:collect:done:{today_str}", "1", ex=86400)
                                log.debug(f"[自动采集] Redis标记: kline:collect:done:{today_str}")
                        except Exception as e:
                            log.debug(f"[自动采集] Redis标记写入失败（不影响后续）: {e}")
                except Exception as e:
                    log.error(f"[自动采集] {today_str} 异常: {e}")

            # 每小时检查一次
            time.sleep(3600)

    t = threading.Thread(target=_loop, daemon=True, name="kline-auto-collect")
    t.start()
