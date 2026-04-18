# -*- coding: utf-8 -*-
"""
龙虎榜模块
包含龙虎榜详情、机构买卖统计、营业部数据等查询接口
"""

import logging
import traceback
from typing import Any, Dict

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_lhb_jgmmtj_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    龙虎榜机构买卖每日统计查询接口（东方财富接口）

    接口: stock_lhb_jgmmtj_em
    目标地址: https://data.eastmoney.com/stock/jgmmtj.html
    描述: 东方财富网-数据中心-龙虎榜单-机构买卖每日统计
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20240417"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20240430"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "jgmmtj"
        }
    """
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "jgmmtj"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "jgmmtj"
        }

    logger.info(f"[机构买卖统计] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_jgmmtj_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[机构买卖统计] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "jgmmtj"
            }

        data_list = _convert_dataframe_to_list(df, "[机构买卖统计]")

        logger.info(f"[机构买卖统计] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "jgmmtj"
        }

    except Exception as e:
        error_msg = f"查询机构买卖统计失败: {str(e)}"
        logger.error(f"[机构买卖统计] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[机构买卖统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "jgmmtj"
        }


def get_stock_lhb_detail_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    龙虎榜详情查询接口（东方财富接口）

    接口: stock_lhb_detail_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-龙虎榜详情
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20220314"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20220315"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "lhb_detail"
        }
    """
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_detail"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_detail"
        }

    logger.info(f"[龙虎榜详情] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[龙虎榜详情] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_detail"
            }

        data_list = _convert_dataframe_to_list(df, "[龙虎榜详情]")

        logger.info(f"[龙虎榜详情] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_detail"
        }

    except Exception as e:
        error_msg = f"查询龙虎榜详情失败: {str(e)}"
        logger.error(f"[龙虎榜详情] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[龙虎榜详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_detail"
        }


def get_stock_lhb_stock_statistic_em(symbol: str = "近一月") -> Dict[str, Any]:
    """
    个股上榜统计查询接口（东方财富接口）

    接口: stock_lhb_stock_statistic_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-个股上榜统计
    限量: 单次返回所有历史数据

    输入参数:
        symbol: str - 时间范围，可选值：
                    "近一月" - 近一个月数据（默认）
                    "近三月" - 近三个月数据
                    "近六月" - 近六个月数据
                    "近一年" - 近一年数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "lhb_stock_statistic"
        }
    """
    if not symbol or not isinstance(symbol, str):
        symbol = "近一月"

    valid_symbols = ["近一月", "近三月", "近六月", "近一年"]
    if symbol not in valid_symbols:
        symbol = "近一月"

    logger.info(f"[个股上榜统计] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_lhb_stock_statistic_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[个股上榜统计] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_stock_statistic"
            }

        data_list = _convert_dataframe_to_list(df, "[个股上榜统计]")

        logger.info(f"[个股上榜统计] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_stock_statistic"
        }

    except Exception as e:
        error_msg = f"查询个股上榜统计失败: {str(e)}"
        logger.error(f"[个股上榜统计] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[个股上榜统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_stock_statistic"
        }


def get_stock_lhb_hyyyb_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    每日活跃营业部查询接口（东方财富接口）

    接口: stock_lhb_hyyyb_em
    目标地址: https://data.eastmoney.com/stock/hyyyb.html
    描述: 东方财富网-数据中心-龙虎榜单-每日活跃营业部
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20220311"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20220315"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "lhb_hyyyb"
        }
    """
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_hyyyb"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_hyyyb"
        }

    logger.info(f"[每日活跃营业部] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_hyyyb_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[每日活跃营业部] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_hyyyb"
            }

        data_list = _convert_dataframe_to_list(df, "[每日活跃营业部]")

        logger.info(f"[每日活跃营业部] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_hyyyb"
        }

    except Exception as e:
        error_msg = f"查询每日活跃营业部失败: {str(e)}"
        logger.error(f"[每日活跃营业部] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[每日活跃营业部] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_hyyyb"
        }


def get_stock_lhb_yyb_detail_em(symbol: str) -> Dict[str, Any]:
    """
    营业部详情数据查询接口（东方财富接口）

    接口: stock_lhb_yyb_detail_em
    目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
    描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
    限量: 单次返回指定营业部的所有历史数据

    输入参数:
        symbol: str - 营业部代码，如 "10026729"

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
            "error": "营业部代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[营业部详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_lhb_yyb_detail_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[营业部详情] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[营业部详情]")

        logger.info(f"[营业部详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询营业部详情失败: {str(e)}"
        logger.error(f"[营业部详情] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[营业部详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }
