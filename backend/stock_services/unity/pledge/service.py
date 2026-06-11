# -*- coding: utf-8 -*-
"""
股权质押模块
包含股权质押相关查询接口
"""

import logging
import random
import time
import traceback
from typing import Any, Dict

import pandas as pd

from system_service.service_result import error_result
from ..utils import  request_akshare_data
from stock_services.utils.field_mapper import map_stock_ask, map_stock_stat_date

logger = logging.getLogger(__name__)


def get_stock_gpzy_profile_em(params) -> Dict[str, Any]:
    """
    股权质押市场概况查询接口（东方财富接口）
    
    接口: stock_gpzy_profile_em
    目标地址: https://data.eastmoney.com/gpzy/marketProfile.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-股权质押市场概况
    限量: 单次所有历史数据
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[股权质押概况] 开始查询市场概况")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_gpzy_profile_em,
        log_prefix="股权质押概况"
    )
    if not result:
        return error_result(message="[股权质押概况] 查询失败，数据为空")

    logger.info(f"[股权质押概况] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_gpzy_pledge_ratio_em(params) -> Dict[str, Any]:
    """
    上市公司质押比例查询接口（东方财富接口）
    
    接口: stock_gpzy_pledge_ratio_em
    目标地址: https://data.eastmoney.com/gpzy/pledgeRatio.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例
    限量: 单次返回指定交易日的所有历史数据
    
    Args:
        params: 参数字典，包含以下字段：
            - date (str): 交易日，格式为 "YYYYMMDD"，如 "20240906"

    """
    import akshare as ak
    date = params.get('date')

    if not date or not isinstance(date, str):
        return error_result(message="日期参数必须为非空字符串，格式为 YYYYMMDD")

    logger.info(f"[上市公司质押比例] 开始查询 date={date}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_gpzy_pledge_ratio_em,
        date=date,
        log_prefix="上市公司质押比例"
    )
    if not result:
        return error_result(message=f"[上市公司质押比例] date={date} 查询失败，数据为空")

    logger.info(f"[上市公司质押比例] date={date} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_gpzy_individual_pledge_ratio_detail_em(params) -> Dict[str, Any]:
    """
    个股重要股东股权质押明细查询接口（东方财富接口）
    
    接口: stock_gpzy_company_em (原 stock_gpzy_individual_pledge_ratio_detail_em 已停用)
    目标地址: https://data.eastmoney.com/gpzy/
    描述: 东方财富网-数据中心-股权质押-个股质押明细
    限量: 单次所有历史数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "603132"

    """
    import akshare as ak
    symbol = params.get('symbol')
    
    if not symbol or not isinstance(symbol, str):
        return error_result(message="股票代码必须为非空字符串")

    logger.info(f"[个股质押明细] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_gpzy_company_em,
        symbol=symbol,
        log_prefix="个股质押明细"
    )
    
    if not result:
        # 如果第一个接口失败，尝试备用接口
        logger.warning(f"[个股质押明细] stock_gpzy_company_em 接口失败，尝试备用接口 symbol={symbol}")
        result = request_akshare_data(
            ak.stock_gpzy_individual_pledge_ratio_detail_em,
            symbol=symbol,
            log_prefix="个股质押明细(备用)"
        )
    
    if not result:
        return error_result(message=f"[个股质押明细] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[个股质押明细] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_gpzy_industry_data_em(params) -> Dict[str, Any]:
    """
    上市公司质押比例-行业数据查询接口（东方财富接口）
    
    接口: stock_gpzy_industry_data_em
    目标地址: https://data.eastmoney.com/gpzy/industryData.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据
    限量: 单次返回所有历史数据
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[行业质押数据] 开始查询行业质押数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_gpzy_industry_data_em,
        log_prefix="行业质押数据"
    )
    if not result:
        return error_result(message="[行业质押数据] 查询失败，数据为空")

    logger.info(f"[行业质押数据] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result
