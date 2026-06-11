"""
stock_services/unity/mootdx/service.py — 历史分时TICK数据 Unity 层

基于 mootdx.Quotes.minutes() 获取 240 条/日的 1 分钟粒度分时数据。

🔁 mootdx 客户端获取已委派至 stock_services/common/connection:
    MootdxClientManager.get_client_safe() 提供线程安全、带重试的客户端管理
"""

import logging
from typing import Dict, Any
from datetime import date, timedelta, datetime

from system_service.service_result import success_result, error_result
from stock_services.common.connection import MootdxClientManager
import time
from stock_services.common.date_utils import get_trading_days, get_stock_market

logger = logging.getLogger("mootdx_kline")

FREQ_MAP = {
    "day": 9, "week": 7, "month": 8, "1": 0, "5": 1,
    "15": 2,"30": 3,"60": 4,
}

DAILY_FREQ_CODES = {7, 8, 9}
HARDCODED_WORKERS = 16


# ─── 交易日分钟序列预计算 ──────────────────────────────────────
# 240 个槽位: 0~119=09:30~11:29, 120~239=13:00~14:59
_TRADING_SLOTS = []
for i in range(240):
    if i < 120:          # 上午
        total_minutes = 9 * 60 + 30 + i
    else:                 # 下午（跳过 11:30~13:00 午休 90 分钟）
        total_minutes = 13 * 60 + (i - 120)
    h, m = divmod(total_minutes, 60)
    _TRADING_SLOTS.append((h, m))


def _idx_to_time(minute_idx: int) -> str:
    """分钟序号 → HH:MM 字符串，O(1) 查表"""
    if 0 <= minute_idx < len(_TRADING_SLOTS):
        h, m = _TRADING_SLOTS[minute_idx]
        return f"{h:02d}:{m:02d}"
    return ""


def get_transaction_service( params: dict, history: bool = False, auto_clean:bool = True, retention_days: int = 30) -> Dict[str, Any]:
    """查询实时分笔成交。"""
    symbol = params.get("symbol", "").strip()
    start = params.get('start') if params.get('start') else 0
    offset = params.get('offset') if params.get('offset') else 800

    try:
        client = MootdxClientManager.get_client_safe()
        if client is None:
            return error_result(message="mootdx 客户端不可用")
        df = client.transaction(symbol=symbol, start=start, offset=offset)
    except Exception as e:
        logger.error(f"[transaction] mootdx 查询失败 symbol={symbol} start={start} offset={offset}: {e}")
        return error_result(message=f"mootdx 查询失败: {str(e)}")

    if df is None or df.empty:
        return success_result(data=[], message="无分笔成交数据")

    today = datetime.now().strftime("%Y%m%d")
    def _calc_expire_date(date_str: str, retention_days: int):
        try:
            base_date = datetime.strptime(date_str, "%Y%m%d").date()
            return (base_date + timedelta(days=retention_days)).strftime("%Y-%m-%d")
        except Exception:
            return None
    today = datetime.now().strftime("%Y%m%d")
    records = _normalize_transaction_records(
        df=df,
        symbol=symbol,
        date_str=today,
        start=start,
        market=get_stock_market(symbol),
        history=False,
    )

    return success_result(data=records)


def get_history_transaction_service(params: dict) -> Dict[str, Any]:
    """查询历史分笔成交。"""
    symbol = params.get("symbol", "").strip()
    date_str = params.get("date", "").strip()
    offset = params.get('offset') if params.get('offset') else 800
    auto_clean = _normalize_bool(params.get("auto_clean"), True)
    start =  params.get('start') if params.get('start') else 0

    retention_days, retention_err = _normalize_positive_int(
        params.get("retention_days", 30),
        30,
        "retention_days",
        min_value=1,
        max_value=3650,
    )

    if not symbol or not date_str:
        return error_result(message="参数缺失: symbol 和 date 必填")
    if len(symbol) != 6 or not symbol.isdigit():
        return error_result(message="symbol 必须是 6 位纯数字股票代码")
    if len(date_str) != 8 or not date_str.isdigit():
        return error_result(message="date 必须是 YYYYMMDD 格式的 8 位数字")
    if retention_err:
        return error_result(message=retention_err)

    try:
        client = MootdxClientManager.get_client_safe()
        if client is None:
            return error_result(message="mootdx 客户端不可用")
        df = client.transactions(symbol=symbol, start=start, offset=offset, date=date_str)
    except Exception as e:
        logger.error(f"[history_transaction] mootdx 查询失败 symbol={symbol} date={date_str} start={start} offset={offset}: {e}")
        return error_result(message=f"mootdx 查询失败: {str(e)}")

    if df is None or df.empty:
        return success_result(data=[], message="该日无历史分笔成交数据, 可能非交易日或数据未生成")

    records = _normalize_transaction_records(
        df=df,
        symbol=symbol,
        date_str=date_str,
        start=start,
        market=get_stock_market(symbol),
        history=True,
        auto_clean=auto_clean,
        retention_days=retention_days,
    )
    return success_result(data=records)


def get_minute_ticks(params: dict) -> Dict[str, Any]:
    """
    获取某只股票某天的历史分时 tick 数据（1 分钟粒度，240 条）。

    输入 params:
        symbol:   str   股票代码（6 位纯数字）
        date:     str   交易日期 YYYYMMDD

    返回:
        {success: bool, data: list[dict], message: str}
    """
    symbol = params.get("symbol", "").strip()
    date_str = params.get("date", "").strip()

    if not symbol or not date_str:
        return error_result(message="参数缺失: symbol 和 date 必填")
    if len(symbol) != 6 or not symbol.isdigit():
        return error_result(message="symbol 必须是 6 位纯数字股票代码")
    if len(date_str) != 8 or not date_str.isdigit():
        return error_result(message="date 必须是 YYYYMMDD 格式的 8 位数字")

    try:
        client = MootdxClientManager.get_client_safe()
        if client is None:
            return error_result(message="mootdx 客户端不可用")
        df = client.minutes(symbol=symbol, date=date_str)
    except Exception as e:
        logger.error(f"[mootdx] mootdx 查询失败 symbol={symbol} date={date_str}: {e}")
        return error_result(message=f"mootdx 查询失败: {str(e)}")

    if df is None or df.empty:
        return success_result(data=[], message=f"该日无分时数据, 可能非交易日或数据未生成")
    market = get_stock_market(symbol)
    records = []
    for idx, row in df.iterrows():
        records.append({
            "symbol":     symbol,
            "trade_date": date_str,
            "minute_idx": int(idx),
            "time_label": _idx_to_time(int(idx)),
            "price":      float(row.get("price", 0)),
            "vol":        int(row.get("vol", 0)),
            "volume":     int(row.get("volume", 0)),
            "market":     market,
        })

    return success_result(data=records)


# def get_kline(symbol=None, freq="day", start_date=None, end_date=None, **kwargs):
#     """
#     获取日/周/月 K 线 + Redis 缓存 + 异步入库
#
#     Args:
#         symbol:     None=全市场 / "000001"=单股 / "000001,600519"=多股 / list
#         freq:       day / week / month
#         start_date: YYYYMMDD 或 YYYY-MM-DD（不传=30天前）
#         end_date:   YYYYMMDD 或 YYYY-MM-DD（不传=今天）
#
#     Returns:
#         {success, total, records, redis_cached, queued_to_db, failed, elapsed_s}
#     """
#     t0 = time.time()
#
#     freq_code = FREQ_MAP.get(freq)
#     if freq_code is None:
#         return {"success": False, "error": f"未知频率: {freq}"}
#
#     # get_kline 只接受日/周/月线，分钟线请走 get_minute_kline
#     if freq_code not in DAILY_FREQ_CODES:
#         return {
#             "success": False,
#             "error": f"freq={freq} 不属于日/周/月线，请使用 get_minute_kline",
#         }
#
#     trading_days = get_trading_days(start_date, end_date)
#     if trading_days['data']['count']> 0 and trading_days['success']:
#         logger.info(
#             f"[mootdx] 日期范围 {start_date}~{end_date} 包含 {trading_days['count']} 交易日，"
#         )
#     else:
#         return error_result(message=f"日期范围 {start_date}~{end_date} 内无交易日，请重新选择日期")
#     today = date.today()
#     trading_days_to_today = get_trading_days(start_date, today)
#     if trading_days_to_today.get('success'):
#         offset = trading_days_to_today['data']['count'] + 2  # +2 风险缓冲
#     else:
#         offset = 10  # 默认值 30个交易日
#     offset = max(offset, 10)
#
#
#     # ── 全市场（symbol=None）─────────────────────────────────
#     if symbol is None:
#         return get_kline_full_market(start_date, end_date, freq, freq_code, offset, t0)
#
#     # ── 单股 / 多股 ─────────────────────────────────────────
#     if isinstance(symbol, list):
#         syms = [str(s).strip() for s in symbol if str(s).strip()]
#     elif isinstance(symbol, str) and "," in symbol:
#         syms = [s.strip() for s in symbol.split(",") if s.strip()]
#     else:
#         syms = [str(symbol).strip()]
#
#     all_records = []
#     failed = []
#
#     for sym in syms:
#         name = self._get_stock_name(sym)
#         df = self._fetch_one_raw(sym, freq_code, offset)
#         if df is None:
#             failed.append(sym)
#             continue
#         recs = self._df_to_records(df, sym, name, start_d, end_d)
#         all_records.extend(recs)
#
#     # 写 Redis Hash + 异步入库
#     h_cached = kline_redis_service.kline_hset_batch(all_records, freq)
#     queued, year_cnt = self._async_persist_kline(all_records, freq)
#
#     elapsed = time.time() - t0
#     log.info(
#         f"[mootdx] 单股/多股完成 syms={len(syms)} records={len(all_records)} "
#         f"redis_hash={h_cached} queued_to_db={queued} "
#         f"failed={len(failed)} elapsed={elapsed:.2f}s"
#     )
#
#
#     return {
#         "success": True,
#         "total": len(syms),
#         "data": all_records,
#         "records": len(all_records),
#         "redis_hash": h_cached,
#         "queued_to_db": queued,
#         "year_count": year_cnt,
#         "failed": len(failed),
#         "failed_list": failed,
#         "elapsed_s": round(elapsed, 2),
#     }

def _normalize_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    return default

def _normalize_positive_int(value: Any, default: int, field: str, min_value: int = 0, max_value: int = 1000):
    try:
        number = int(value)
    except Exception:
        return None, f"{field} 必须是整数"
    if number < min_value or number > max_value:
        return None, f"{field} 必须在 {min_value}~{max_value} 范围内"
    return number, None


def _calc_expire_date(date_str: str, retention_days: int):
    try:
        base_date = datetime.strptime(date_str, "%Y%m%d").date()
        return (base_date + timedelta(days=retention_days)).strftime("%Y-%m-%d")
    except Exception:
        return None

def _normalize_transaction_records(df,symbol: str,date_str: str, start: int, market: str, history: bool,
                                   auto_clean: bool = True, retention_days: int = 30,):
    records = []
    expire_date = _calc_expire_date(date_str, retention_days) if history and auto_clean else None
    for idx, row in df.reset_index(drop=True).iterrows():
        seq = start + int(idx)
        item = {
            "symbol": symbol,
            "trade_date": date_str,
            "seq": seq,
            "time_label": str(row.get("time", "")),
            "price": float(row.get("price", 0) or 0),
            "vol": int(row.get("vol", 0) or 0),
            "volume": int(row.get("volume", row.get("vol", 0)) or 0),
            "num": int(row.get("num", 0) or 0) if "num" in row else None,
            "buyorsell": int(row.get("buyorsell", -1) or 0),
            "market": market,
            "data_type": "history" if history else "realtime",
        }
        if history:
            item["auto_clean"] = 1 if auto_clean else 0
            item["retention_days"] = retention_days
            item["expire_date"] = expire_date
        records.append(item)
    return records