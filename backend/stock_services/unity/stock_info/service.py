"""
stock_services/unity/stock_info/service.py — 东方财富个股信息查询

接口: akshare.stock_individual_info_em
目标地址: https://quote.eastmoney.com/concept/sh603777.html?from=classic
描述: 东方财富-个股-股票信息

返回数据转换为标准列表格式（兼容 execute_cached_fetch）。
"""

import logging
from typing import Any, Dict

from system_service.service_result import error_result, success_result
from stock_services.unity.utils import request_akshare_data

logger = logging.getLogger(__name__)


def get_stock_individual_info_em(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    查询东方财富-个股-股票信息。

    接口: akshare.stock_individual_info_em
    目标地址: http://quote.eastmoney.com/concept/sh603777.html?from=classic
    描述: 东方财富-个股-股票信息
    限量: 单次返回指定股票的详细信息

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码, 例: "603777"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,
            "data": [dict],     # 单条记录的列表（兼容 execute_cached_fetch）
            "message": str
        }
    """
    import akshare as ak

    symbol = params.get("symbol", "")
    if not symbol:
        return error_result(message="[个股信息] symbol 参数不能为空")

    logger.info("[个股信息] 开始查询 symbol=%s", symbol)

    result = request_akshare_data(
        ak.stock_individual_info_em,
        symbol=symbol,
        timeout=15,
        log_prefix="个股信息",
    )

    if not result or not result.get("data"):
        return error_result(message=f"[个股信息] symbol={symbol} 查询失败，数据为空")

    # 原始数据是 [{item: "股票代码", value: "000001"}, {item: "股票简称", value: "平安银行"}, ...]
    # 转换为扁平字典 → 再包装为列表（兼容 execute_cached_fetch 的列表输入格式）
    raw_rows = result["data"]
    info_dict = {}
    for row in raw_rows:
        item_name = row.get("item", "")
        item_value = row.get("value", "")
        if item_name:
            info_dict[item_name] = item_value

    # 应用字段映射（中文 → 英文）
    from stock_services.utils.field_mapper import STOCK_INDIVIDUAL_INFO_MAPPING
    mapped: Dict[str, Any] = {}
    for cn_key, en_key in STOCK_INDIVIDUAL_INFO_MAPPING.items():
        if cn_key in info_dict:
            val = info_dict[cn_key]
            # 数值类型转换（字符串数字 → float）
            if en_key in ("total_shares", "float_shares", "total_market_cap", "float_market_cap", "latest_price"):
                try:
                    val = float(str(val).replace(",", ""))
                except (ValueError, TypeError):
                    pass
            mapped[en_key] = val

    # 补充原始 symbol 字段
    if "symbol" not in mapped:
        mapped["symbol"] = symbol

    logger.info("[个股信息] symbol=%s 查询成功，字段数=%d", symbol, len(mapped))

    # 包装为单条列表（execute_cached_fetch 需要 data 为列表）
    return success_result(data=[mapped], message=f"[个股信息] {symbol} 查询成功")
