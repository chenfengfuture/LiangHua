# -*- coding: utf-8 -*-
"""
涨跌停模块
包含涨停股池、跌停股池、炸板股等查询接口
"""

import logging
import random
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_zt_pool_em(date: str) -> Dict[str, Any]:
    """
    东方财富涨停股池数据查询接口

    接口: stock_zt_pool_em
    目标地址: https://data.eastmoney.com/datas.shtml

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240418"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "zt_pool"
        }
    """
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zt_pool"
        }

    logger.info(f"[涨停股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_em(date=date)

        if df.empty:
            logger.warning(f"[涨停股池] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool"
            }

        data_list = _convert_dataframe_to_list(df, "[涨停股池]")

        logger.info(f"[涨停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool"
        }

    except Exception as e:
        error_msg = f"查询涨停股池失败: {str(e)}"
        logger.error(f"[涨停股池] 异常 date={date}, error={error_msg}")
        logger.debug(f"[涨停股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool"
        }


def get_stock_zt_pool_previous_em(date: str) -> Dict[str, Any]:
    """
    东方财富昨日涨停股池数据查询接口

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
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zt_pool_previous"
        }

    logger.info(f"[昨日涨停股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_previous_em(date=date)

        if df.empty:
            logger.warning(f"[昨日涨停股池] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool_previous"
            }

        data_list = _convert_dataframe_to_list(df, "[昨日涨停股池]")

        logger.info(f"[昨日涨停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool_previous"
        }

    except Exception as e:
        error_msg = f"查询昨日涨停股池失败: {str(e)}"
        logger.error(f"[昨日涨停股池] 异常 date={date}, error={error_msg}")
        logger.debug(f"[昨日涨停股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool_previous"
        }


def get_stock_zt_pool_strong_em(date: str) -> Dict[str, Any]:
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
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zt_pool_strong"
        }

    logger.info(f"[强势股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_strong_em(date=date)

        if df.empty:
            logger.warning(f"[强势股池] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool_strong"
            }

        data_list = _convert_dataframe_to_list(df, "[强势股池]")

        logger.info(f"[强势股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool_strong"
        }

    except Exception as e:
        error_msg = f"查询强势股池失败: {str(e)}"
        logger.error(f"[强势股池] 异常 date={date}, error={error_msg}")
        logger.debug(f"[强势股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool_strong"
        }


def get_stock_zt_pool_zbgc_em(date: str) -> Dict[str, Any]:
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
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zt_pool_zbgc"
        }

    # 自动校验日期：接口限制查询近30天数据
    try:
        query_date = datetime.strptime(date, "%Y%m%d")
        today = datetime.now()
        days_diff = (today - query_date).days

        if days_diff > 30:
            # 自动截断为最近30天
            adjusted_date = (today - timedelta(days=30)).strftime("%Y%m%d")
            logger.warning(f"[炸板股池] 日期超过30天限制，自动调整为 {adjusted_date}")
            date = adjusted_date
    except ValueError:
        return {
            "success": False,
            "data": None,
            "error": "日期格式错误，请使用 YYYYMMDD 格式",
            "symbol": "zt_pool_zbgc"
        }

    logger.info(f"[炸板股池] 开始查询 date={date}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = ak.stock_zt_pool_zbgc_em(date=date)

            if df.empty:
                logger.warning(f"[炸板股池] 返回数据为空 date={date}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "zt_pool_zbgc"
                }

            data_list = _convert_dataframe_to_list(df, "[炸板股池]")

            logger.info(f"[炸板股池] 查询成功 date={date}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "zt_pool_zbgc"
            }

        except Exception as e:
            error_msg = f"查询炸板股池失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[炸板股池] 第{attempt + 1}次失败 date={date}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[炸板股池] 最终失败 date={date}, error={error_msg}")
                logger.debug(f"[炸板股池] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "zt_pool_zbgc"
                }


def get_stock_zt_pool_dtgc_em(date: str) -> Dict[str, Any]:
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
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zt_pool_dtgc"
        }

    # 自动校验日期：接口限制查询近30天数据
    try:
        query_date = datetime.strptime(date, "%Y%m%d")
        today = datetime.now()
        days_diff = (today - query_date).days

        if days_diff > 30:
            # 自动截断为最近30天
            adjusted_date = (today - timedelta(days=30)).strftime("%Y%m%d")
            logger.warning(f"[跌停股池] 日期超过30天限制，自动调整为 {adjusted_date}")
            date = adjusted_date
    except ValueError:
        return {
            "success": False,
            "data": None,
            "error": "日期格式错误，请使用 YYYYMMDD 格式",
            "symbol": "zt_pool_dtgc"
        }

    logger.info(f"[跌停股池] 开始查询 date={date}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = ak.stock_zt_pool_dtgc_em(date=date)

            if df.empty:
                logger.warning(f"[跌停股池] 返回数据为空 date={date}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "zt_pool_dtgc"
                }

            data_list = _convert_dataframe_to_list(df, "[跌停股池]")

            logger.info(f"[跌停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "zt_pool_dtgc"
            }

        except Exception as e:
            error_msg = f"查询跌停股池失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[跌停股池] 第{attempt + 1}次失败 date={date}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[跌停股池] 最终失败 date={date}, error={error_msg}")
                logger.debug(f"[跌停股池] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "zt_pool_dtgc"
                }
