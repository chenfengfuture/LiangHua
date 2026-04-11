# -*- coding: utf-8 -*-
"""
融资融券模块
包含两融账户信息、融资融券汇总、融资融券明细等查询接口
"""

import logging
import traceback
from typing import Dict, Any

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_margin_account_info() -> Dict[str, Any]:
    """
    两融账户信息查询接口（东方财富接口）

    接口: stock_margin_account_info
    目标地址: https://data.eastmoney.com/rzrq/txt.html
    描述: 东方财富网-数据中心-融资融券-两融账户
    限量: 单次返回所有数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "margin_account"
        }
    """
    logger.info("[两融账户信息] 开始查询两融账户数据")

    try:
        df = ak.stock_margin_account_info()

        if df.empty:
            logger.warning("[两融账户信息] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_account"
            }

        data_list = _convert_dataframe_to_list(df, "[两融账户信息]")

        logger.info(f"[两融账户信息] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_account"
        }

    except Exception as e:
        error_msg = f"查询两融账户信息失败: {str(e)}"
        logger.error(f"[两融账户信息] 异常 error={error_msg}")
        logger.debug(f"[两融账户信息] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_account"
        }


def get_stock_margin_sse(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    上交所融资融券汇总查询接口（东方财富接口）

    接口: stock_margin_sse
    目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
    描述: 上海证券交易所-融资融券数据
    限量: 单次返回指定日期区间的所有数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20240901"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20240930"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "margin_sse"
        }
    """
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "margin_sse"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "margin_sse"
        }

    logger.info(f"[上交所融资融券] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[上交所融资融券] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_sse"
            }

        data_list = _convert_dataframe_to_list(df, "[上交所融资融券]")

        logger.info(f"[上交所融资融券] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_sse"
        }

    except Exception as e:
        error_msg = f"查询上交所融资融券数据失败: {str(e)}"
        logger.error(f"[上交所融资融券] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[上交所融资融券] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_sse"
        }


def get_stock_margin_detail_szse(date: str) -> Dict[str, Any]:
    """
    深交所融资融券明细查询接口（东方财富接口）

    接口: stock_margin_detail_szse
    目标地址: https://www.szse.cn/market/dealingdata/margin/index.html
    描述: 深圳证券交易所-融资融券明细
    限量: 单次返回指定日期的所有数据

    输入参数:
        date: str - 查询日期，格式为 "YYYYMMDD"，如 "20240930"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "margin_detail_szse"
        }
    """
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "margin_detail_szse"
        }

    logger.info(f"[深交所融资融券明细] 开始查询 date={date}")

    try:
        df = ak.stock_margin_detail_szse(date=date)

        if df.empty:
            logger.warning(f"[深交所融资融券明细] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_detail_szse"
            }

        data_list = _convert_dataframe_to_list(df, "[深交所融资融券明细]")

        logger.info(f"[深交所融资融券明细] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_detail_szse"
        }

    except Exception as e:
        error_msg = f"查询深交所融资融券明细失败: {str(e)}"
        logger.error(f"[深交所融资融券明细] 异常 date={date}, error={error_msg}")
        logger.debug(f"[深交所融资融券明细] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_detail_szse"
        }


def get_stock_margin_detail_sse(date: str) -> Dict[str, Any]:
    """
    上交所融资融券明细查询接口（东方财富接口）

    接口: stock_margin_detail_sse
    目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
    描述: 上海证券交易所-融资融券明细
    限量: 单次返回指定日期的所有数据

    输入参数:
        date: str - 查询日期，格式为 "YYYYMMDD"，如 "20240930"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "margin_detail_sse"
        }
    """
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "margin_detail_sse"
        }

    logger.info(f"[上交所融资融券明细] 开始查询 date={date}")

    try:
        df = ak.stock_margin_detail_sse(date=date)

        # 修复空数据判断
        if df is None or len(df) == 0:
            logger.warning(f"[上交所融资融券明细] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_detail_sse"
            }

        data_list = _convert_dataframe_to_list(df, "[上交所融资融券明细]")

        logger.info(f"[上交所融资融券明细] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_detail_sse"
        }

    except Exception as e:
        error_msg = f"查询上交所融资融券明细失败: {str(e)}"
        logger.error(f"[上交所融资融券明细] 异常 date={date}, error={error_msg}")
        logger.debug(f"[上交所融资融券明细] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_detail_sse"
        }
