# -*- coding: utf-8 -*-
"""
股东数据模块
包含股票账户统计、千股千评、股东户数等查询接口
"""

import logging
import traceback
from typing import Dict, Any

import akshare as ak
import pandas as pd

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_account_statistics_em() -> Dict[str, Any]:
    """
    股票账户统计月度数据查询接口（东方财富接口）

    接口: stock_account_statistics_em
    目标地址: https://data.eastmoney.com/cjsj/gpkhsj.html
    描述: 东方财富网-数据中心-特色数据-股票账户统计（月度）
    限量: 单次返回从 201504 开始至最新的所有历史数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "account_statistics"
        }
    """
    logger.info("[股票账户统计] 开始查询月度账户统计数据")

    try:
        df = ak.stock_account_statistics_em()

        if df.empty:
            logger.warning("[股票账户统计] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "account_statistics"
            }

        data_list = _convert_dataframe_to_list(df, "[股票账户统计]")

        logger.info(f"[股票账户统计] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "account_statistics"
        }

    except Exception as e:
        error_msg = f"查询股票账户统计失败: {str(e)}"
        logger.error(f"[股票账户统计] 异常 error={error_msg}")
        logger.debug(f"[股票账户统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "account_statistics"
        }


def get_stock_comment_em() -> Dict[str, Any]:
    """
    千股千评数据查询接口（东方财富接口）

    接口: stock_comment_em
    目标地址: https://data.eastmoney.com/stockcomment/
    描述: 东方财富网-数据中心-特色数据-千股千评
    限量: 单次获取所有股票当日评分数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "stock_comment"
        }

    注意: 该接口数据量较大（全市场股票），请耐心等待。
    """
    logger.info("[千股千评] 开始查询千股千评数据")

    try:
        df = ak.stock_comment_em()

        if df.empty:
            logger.warning("[千股千评] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "stock_comment"
            }

        data_list = _convert_dataframe_to_list(df, "[千股千评]")

        logger.info(f"[千股千评] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "stock_comment"
        }

    except Exception as e:
        error_msg = f"查询千股千评数据失败: {str(e)}"
        logger.error(f"[千股千评] 异常 error={error_msg}")
        logger.debug(f"[千股千评] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "stock_comment"
        }


def get_stock_comment_detail_scrd_focus_em(symbol: str) -> Dict[str, Any]:
    """
    千股千评-用户关注指数查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_focus_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
    限量: 单次获取所有数据

    输入参数:
        symbol: str - 股票代码，如 "600000"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": symbol
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[用户关注指数] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_comment_detail_scrd_focus_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[用户关注指数] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[用户关注指数]")

        logger.info(f"[用户关注指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询用户关注指数失败: {str(e)}"
        logger.error(f"[用户关注指数] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[用户关注指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_comment_detail_scrd_desire_em(symbol: str) -> Dict[str, Any]:
    """
    千股千评-市场参与意愿查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_desire_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
    限量: 单次获取所有数据

    输入参数:
        symbol: str - 股票代码，如 "600000"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": symbol
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[市场参与意愿] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_comment_detail_scrd_desire_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[市场参与意愿] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[市场参与意愿]")

        logger.info(f"[市场参与意愿] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询市场参与意愿失败: {str(e)}"
        logger.error(f"[市场参与意愿] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[市场参与意愿] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_zh_a_gdhs(date: str) -> Dict[str, Any]:
    """
    股东户数查询接口（东方财富接口）

    接口: stock_zh_a_gdhs
    目标地址: http://data.eastmoney.com/gdhs/
    描述: 东方财富网-数据中心-特色数据-股东户数数据
    限量: 单次获取返回所有数据

    输入参数:
        date: str - 查询日期，可选值：
              "最新" - 获取最新一期股东户数数据
              季度末日期 - 格式为 "YYYYMMDD"，如 "20240930"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "gdhs"
        }
    """
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，可选值: '最新' 或 'YYYYMMDD' 格式",
            "symbol": "gdhs"
        }

    logger.info(f"[股东户数] 开始查询 date={date}")

    try:
        df = ak.stock_zh_a_gdhs(symbol=date)

        if df.empty:
            logger.warning(f"[股东户数] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gdhs"
            }

        data_list = _convert_dataframe_to_list(df, "[股东户数]")

        logger.info(f"[股东户数] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gdhs"
        }

    except Exception as e:
        error_msg = f"查询股东户数失败: {str(e)}"
        logger.error(f"[股东户数] 异常 date={date}, error={error_msg}")
        logger.debug(f"[股东户数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gdhs"
        }


def get_stock_zh_a_gdhs_detail_em(symbol: str) -> Dict[str, Any]:
    """
    股东户数详情查询接口（东方财富接口）

    接口: stock_zh_a_gdhs_detail_em
    目标地址: https://data.eastmoney.com/gdhs/detail/000002.html
    描述: 东方财富网-数据中心-特色数据-股东户数详情
    限量: 单次获取指定 symbol 的所有数据

    输入参数:
        symbol: str - 股票代码，如 "000001"（平安银行），不带市场前缀

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": symbol
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[股东户数详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_zh_a_gdhs_detail_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[股东户数详情] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[股东户数详情]")

        logger.info(f"[股东户数详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询股东户数详情失败: {str(e)}"
        logger.error(f"[股东户数详情] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[股东户数详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }
