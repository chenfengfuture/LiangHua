# -*- coding: utf-8 -*-
"""
股东数据模块
包含股票账户统计、千股千评、股东户数等查询接口
"""

import logging
import traceback
from typing import Any, Dict

import pandas as pd

from system_service.service_result import error_result
from ..utils import _convert_dataframe_to_list, request_akshare_data
from ...utils.field_mapper import map_board_concept_index, add_concept_name, map_stock_ask, \
    map_stock_change_symbol

logger = logging.getLogger(__name__)


def get_stock_account_statistics_em(params) -> Dict[str, Any]:
    """
    股票账户统计月度数据查询接口（东方财富接口）

    接口: stock_account_statistics_em
    目标地址: https://data.eastmoney.com/cjsj/gpkhsj.html
    描述: 东方财富网-数据中心-特色数据-股票账户统计（月度）
    限量: 单次返回从 201504 开始至最新的所有历史数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股票账户统计数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[股票账户统计] 开始查询月度账户统计数据")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_account_statistics_em,
        log_prefix="股票账户统计"
    )
    
    if not result:
        return error_result(message="[股票账户统计] 查询失败，数据为空")
    
    logger.info(f"[股票账户统计] 查询成功，数据条数={len(result.get('data', []))}")

    result = map_stock_ask(result)
    return result



def get_stock_comment_em(params) -> Dict[str, Any]:
    """
    千股千评数据查询接口（东方财富接口）

    接口: stock_comment_em
    目标地址: https://data.eastmoney.com/stockcomment/
    描述: 东方财富网-数据中心-特色数据-千股千评
    限量: 单次获取所有股票当日评分数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）
    """
    import akshare as ak
    logger.info("[千股千评] 开始查询千股千评数据")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_comment_em,
        log_prefix="千股千评"
    )

    if not result:
        return error_result(message="[千股千评] 查询失败，数据为空")

    logger.info(f"[千股千评] 查询成功，数据条数={len(result.get('data', []))}")
    result = map_stock_ask(result)
    return result


def get_stock_comment_detail_scrd_focus_em(params) -> Dict[str, Any]:
    """
    千股千评-用户关注指数查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_focus_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
    限量: 单次获取所有数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "600000"

    """
    import akshare as ak
    symbol = params.get('symbol')

    if not symbol or not isinstance(symbol, str):
        return error_result(message="股票代码必须为非空字符串")

    logger.info(f"[用户关注指数] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_comment_detail_scrd_focus_em,
        symbol=symbol,
        log_prefix="用户关注指数"
    )

    if not result:
        return error_result(message=f"[用户关注指数] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[用户关注指数] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    return result


def get_stock_comment_detail_scrd_desire_em(params) -> Dict[str, Any]:
    """
    千股千评-市场参与意愿查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_desire_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
    限量: 单次获取所有数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "600000"

    """
    import akshare as ak
    symbol = params.get('symbol')
    
    if not symbol or not isinstance(symbol, str):
        return error_result(message="股票代码必须为非空字符串")

    logger.info(f"[市场参与意愿] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_comment_detail_scrd_desire_em,
        symbol=symbol,
        log_prefix="市场参与意愿"
    )
    
    if not result:
        return error_result(message=f"[市场参与意愿] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[市场参与意愿] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'])
    map_result = map_stock_change_symbol(result)
    print('map_result', map_result['data'])
    return map_result


def get_stock_zh_a_gdhs(params) -> Dict[str, Any]:
    """
    股东户数查询接口（东方财富接口）

    接口: stock_zh_a_gdhs
    目标地址: http://data.eastmoney.com/gdhs/
    描述: 东方财富网-数据中心-特色数据-股东户数数据
    限量: 单次获取返回所有数据

    Args:
        params: 参数字典，包含以下字段：
            - date (str): 查询日期，可选值：
                  "最新" - 获取最新一期股东户数数据
                  季度末日期 - 格式为 "YYYYMMDD"，如 "20240930"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股东户数数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    date = params.get('date')
    
    if not date or not isinstance(date, str):
        return error_result(message="日期必须为非空字符串，可选值: '最新' 或 'YYYYMMDD' 格式")

    logger.info(f"[股东户数] 开始查询 date={date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_gdhs,
        symbol=date,
        log_prefix="股东户数"
    )
    
    if not result:
        return error_result(message=f"[股东户数] date={date} 查询失败，数据为空")
    
    logger.info(f"[股东户数] date={date} 查询成功，数据条数={len(result.get('data', []))}")

    print('result', result['data'])
    map_result = map_stock_ask(result)
    print('map_result', map_result['data'])
    return result


def get_stock_zh_a_gdhs_detail_em(params) -> Dict[str, Any]:
    """
    股东户数详情查询接口（东方财富接口）

    接口: stock_zh_a_gdhs_detail_em
    目标地址: https://data.eastmoney.com/gdhs/detail/000002.html
    描述: 东方财富网-数据中心-特色数据-股东户数详情
    限量: 单次获取指定 symbol 的所有数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "000001"（平安银行），不带市场前缀

    """
    import akshare as ak
    symbol = params.get('symbol')
    
    if not symbol or not isinstance(symbol, str):
        return error_result(message="股票代码必须为非空字符串")

    logger.info(f"[股东户数详情] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_gdhs_detail_em,
        symbol=symbol,
        log_prefix="股东户数详情"
    )
    
    if not result:
        return error_result(message=f"[股东户数详情] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[股东户数详情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    print('result', result['data'])
    map_result = map_stock_ask(result)
    print('map_result', map_result['data'])
    return map_result
