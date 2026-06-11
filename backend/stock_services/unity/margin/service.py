# -*- coding: utf-8 -*-
"""
融资融券模块
包含两融账户信息、融资融券汇总、融资融券明细等查询接口
"""

import logging
import traceback
from typing import Any, Dict

from system_service.service_result import error_result
from ..utils import _convert_dataframe_to_list, request_akshare_data
from ...utils.field_mapper import map_stock_stat_date, map_stock_ask

logger = logging.getLogger(__name__)


def get_stock_margin_account_info(params) -> Dict[str, Any]:
    """
    两融账户信息查询接口（东方财富接口）

    接口: stock_margin_account_info
    目标地址: https://data.eastmoney.com/rzrq/txt.html
    描述: 东方财富网-数据中心-融资融券-两融账户
    限量: 单次返回所有数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 两融账户信息数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[两融账户信息] 开始查询两融账户数据")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_margin_account_info,
        log_prefix="两融账户信息"
    )
    
    if not result:
        return error_result(message="[两融账户信息] 查询失败，数据为空")
    
    logger.info(f"[两融账户信息] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)

    return mapped_result


def get_stock_margin_sse(params) -> Dict[str, Any]:
    """
    上交所融资融券汇总查询接口（东方财富接口）

    接口: stock_margin_sse
    目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
    描述: 上海证券交易所-融资融券数据
    限量: 单次返回指定日期区间的所有数据

    Args:
        params: 参数字典，包含以下字段：
            - start_date (str): 开始日期，格式为 "YYYYMMDD"，如 "20240901"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"，如 "20240930"
    """
    import akshare as ak
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    logger.info(f"[上交所融资融券] 开始查询 start_date={start_date}, end_date={end_date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_margin_sse,
        start_date=start_date,
        end_date=end_date,
        log_prefix="上交所融资融券"
    )
    
    if not result:
        return error_result(message=f"[上交所融资融券] start_date={start_date}, end_date={end_date} 查询失败，数据为空")
    
    logger.info(f"[上交所融资融券] start_date={start_date}, end_date={end_date} 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_margin_detail_szse(params) -> Dict[str, Any]:
    """
    深交所融资融券明细查询接口（东方财富接口）

    接口: stock_margin_detail_szse
    目标地址: https://www.szse.cn/market/dealingdata/margin/index.html
    描述: 深圳证券交易所-融资融券明细
    限量: 单次返回指定日期的所有数据

    Args:
        params: 参数字典，包含以下字段：
            - date (str): 查询日期，格式为 "YYYYMMDD"，如 "20240930"
    """
    import akshare as ak
    date = params.get('date')
    
    if not date or not isinstance(date, str):
        return error_result(message="日期必须为非空字符串，格式为 YYYYMMDD")

    logger.info(f"[深交所融资融券明细] 开始查询 date={date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_margin_detail_szse,
        date=date,
        log_prefix="深交所融资融券明细"
    )
    
    if not result:
        return error_result(message=f"[深交所融资融券明细] date={date} 查询失败，数据为空")
    
    logger.info(f"[深交所融资融券明细] date={date} 查询成功，数据条数={len(result.get('data', []))}")

    return result


def get_stock_margin_detail_sse(params) -> Dict[str, Any]:
    """
    上交所融资融券明细查询接口（东方财富接口）

    接口: stock_margin_detail_sse
    目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
    描述: 上海证券交易所-融资融券明细
    限量: 单次返回指定日期的所有数据

    Args:
        params: 参数字典，包含以下字段：
            - date (str): 查询日期，格式为 "YYYYMMDD"，如 "20240930"

    """
    import akshare as ak
    date = params.get('date')
    
    if not date or not isinstance(date, str):
        return error_result(message="日期必须为非空字符串，格式为 YYYYMMDD")

    logger.info(f"[上交所融资融券明细] 开始查询 date={date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_margin_detail_sse,
        date=date,
        log_prefix="上交所融资融券明细"
    )
    
    if not result:
        return error_result(message=f"[上交所融资融券明细] date={date} 查询失败，数据为空")
    
    logger.info(f"[上交所融资融券明细] date={date} 查询成功，数据条数={len(result.get('data', []))}")

    return result
