"""
stock_services/unity/transaction/service.py — 分笔成交数据 Unity 层

基于 mootdx.Quotes.transaction() / Quotes.transactions() 获取实时与历史分笔成交数据。

🔁 mootdx 客户端获取已委派至 stock_services/common/connection:
    MootdxClientManager.get_client_safe() 提供线程安全、带重试的客户端管理
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from system_service.service_result import success_result, error_result
from stock_services.common.connection import MootdxClientManager

logger = logging.getLogger(__name__)


def _detect_market(symbol: str) -> int:
    """推断市场 0=深圳 1=上海"""
    prefix = symbol[:2] if len(symbol) >= 2 else ""
    if prefix in ("60", "68", "50", "51", "90", "11", "13"):
        return 1
    if prefix in ("00", "30", "12", "15", "18", "20"):
        return 0
    return -1


def _normalize_positive_int(value: Any, default: int, field: str, min_value: int = 0, max_value: int = 1000):
    try:
        number = int(value)
    except Exception:
        return None, f"{field} 必须是整数"
    if number < min_value or number > max_value:
        return None, f"{field} 必须在 {min_value}~{max_value} 范围内"
    return number, None


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


def _calc_expire_date(date_str: str, retention_days: int):
    try:
        base_date = datetime.strptime(date_str, "%Y%m%d").date()
        return (base_date + timedelta(days=retention_days)).strftime("%Y-%m-%d")
    except Exception:
        return None


def _normalize_transaction_records(
    df,
    symbol: str,
    date_str: str,
    start: int,
    market: int,
    history: bool,
    auto_clean: bool = True,
    retention_days: int = 30,
):
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


def get_transaction(params: dict) -> Dict[str, Any]:
    """查询实时分笔成交。"""
    symbol = params.get("symbol", "").strip()
    start, start_err = _normalize_positive_int(params.get("start", 0), 0, "start")
    offset, offset_err = _normalize_positive_int(params.get("offset", 800), 800, "offset", min_value=1)

    if not symbol:
        return error_result(message="参数缺失: symbol 必填")
    if len(symbol) != 6 or not symbol.isdigit():
        return error_result(message="symbol 必须是 6 位纯数字股票代码")
    if start_err:
        return error_result(message=start_err)
    if offset_err:
        return error_result(message=offset_err)

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
    records = _normalize_transaction_records(
        df=df,
        symbol=symbol,
        date_str=today,
        start=start,
        market=_detect_market(symbol),
        history=False,
    )
    return success_result(data=records)


def get_history_transaction(params: dict) -> Dict[str, Any]:
    """查询历史分笔成交。"""
    symbol = params.get("symbol", "").strip()
    date_str = params.get("date", "").strip()
    start, start_err = _normalize_positive_int(params.get("start", 0), 0, "start")
    offset, offset_err = _normalize_positive_int(params.get("offset", 800), 800, "offset", min_value=1)
    auto_clean = _normalize_bool(params.get("auto_clean"), True)
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
    if start_err:
        return error_result(message=start_err)
    if offset_err:
        return error_result(message=offset_err)
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
        market=_detect_market(symbol),
        history=True,
        auto_clean=auto_clean,
        retention_days=retention_days,
    )
    return success_result(data=records)
