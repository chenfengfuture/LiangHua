# -*- coding: utf-8 -*-
"""
涨跌停模块
包含涨停股池、跌停股池、炸板股等查询接口
"""

import logging
import random
import time
import traceback
from datetime import datetime, timedelta, date
from typing import Any, Dict

from system_service import error_result
from ..utils import _convert_dataframe_to_list, request_akshare_data
from ...utils.field_mapper import map_board_change, map_stock_ask, map_stock_stat_date

logger = logging.getLogger(__name__)

today = date.today().isoformat()


def get_stock_zt_pool_em(params: dict) -> Dict[str, Any]:
    """
    查询东方财富涨停板行情

    接口: akshare.stock_zt_pool_em
    目标地址: 东方财富网站
    描述: 东方财富网-行情中心-涨停板行情-涨停股池 单次返回指定 date 的涨停股池数据; 该接口只能获取近期的数据

    Args:
        params: date	str	date='20241008'

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 板块异动详情数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[东方财富涨停板行情] 开始查询")
    date_param = today.replace('-', '')
    date_re = params.get('date', date_param)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zt_pool_em,
        date=date_re,
        log_prefix="东方财富涨停板行情"
    )

    if not result:
        return error_result(message="[东方财富涨停板行情] 查询失败，数据为空")
    logger.info(f"[东方财富涨停板行情] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_zt_pool_previous_em(params: dict) -> Dict[str, Any]:
    """
    东方财富昨日涨停股池数据查询接口
    查询日期 前一个交易日涨停的股票 , 返回查询日期的数据

    接口: stock_zt_pool_previous_em
    目标地址: https://data.eastmoney.com/datas.shtml

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240418"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "zt_pool_previous"
        }
    """
    import akshare as ak
    logger.info("[东方财富昨日涨停股池数据] 开始查询")
    date_param = today.replace('-', '')
    date_re = params.get('date', date_param)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zt_pool_previous_em,
        date=date_re,
        log_prefix="东方财富昨日涨停股池数据"
    )

    if not result:
        return error_result(message="[东方财富昨日涨停股池数据] 查询失败，数据为空")
    logger.info(f"[东方财富昨日涨停股池数据] 查询成功，数据条数={len(result.get('data', []))}")
    print('11111',result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_zt_pool_strong_em(params: dict) -> Dict[str, Any]:
    """
    东方财富强势股池数据查询接口

    接口: stock_zt_pool_strong_em
    目标地址: https://data.eastmoney.com/datas.shtml

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240418"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "zt_pool_strong"
        }
    """
    import akshare as ak

    logger.info("[东方财富强势股池数据] 开始查询")
    date_param = today.replace('-', '')
    date_re = params.get('date', date_param)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zt_pool_strong_em,
        date=date_re,
        log_prefix="东方财富强势股池数据"
    )

    if not result:
        return error_result(message="[东方财富强势股池数据] 查询失败，数据为空")
    logger.info(f"[东方财富强势股池数据] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_zt_pool_zbgc_em(params: dict) -> Dict[str, Any]:
    """
    东方财富炸板股池数据查询接口

    接口: stock_zt_pool_zbgc_em
    目标地址: https://data.eastmoney.com/datas.shtml
    描述: 查询当日炸板股票（涨停后打开涨停板的股票）

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240418"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "zt_pool_zbgc"
        }

    注意:
        1. 炸板股指曾经涨停但未能封住涨停的股票
        2. 炸板率 = 炸板股数 / 涨停股数
        3. 高炸板率可能表示市场情绪不稳或主力诱多
    """
    import akshare as ak
    logger.info("[东方财富板股池数据] 开始查询")
    date_param = today.replace('-', '')
    date_re = params.get('date', date_param)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zt_pool_zbgc_em,
        date=date_re,
        log_prefix="东方财富板股池数据"
    )

    if not result:
        return error_result(message="[东方财富板股池数据] 查询失败，数据为空")
    logger.info(f"[东方财富板股池数据] 查询成功，数据条数={len(result.get('data', []))}")
    print('11111', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result



def get_stock_zt_pool_dtgc_em(params: dict) -> Dict[str, Any]:
    """
    东方财富跌停股池数据查询接口

    接口: stock_zt_pool_dtgc_em
    目标地址: https://data.eastmoney.com/datas.shtml
    描述: 查询当日跌停股票

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240418"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "zt_pool_dtgc"
        }

    注意:
        1. 跌停股反映市场恐慌情绪
        2. 连续跌停股可能存在流动性风险
        3. 可结合公司基本面分析是否存在错杀
    """
    import akshare as ak
    logger.info("[东方财富跌停股池数据] 开始查询")
    date_param = today.replace('-', '')
    date_re = params.get('date', date_param)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zt_pool_dtgc_em,
        date=date_re,
        log_prefix="东方财富跌停股池数据"
    )

    if not result:
        return error_result(message="[东方财富跌停股池数据] 查询失败，数据为空")
    logger.info(f"[东方财富跌停股池数据] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result
