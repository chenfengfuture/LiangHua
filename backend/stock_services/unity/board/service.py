# -*- coding: utf-8 -*-
"""
板块概念模块
包含板块指数、行业信息、概念信息、股票热度、盘口异动等查询接口
"""

import logging
import traceback
from typing import Any, Dict

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_board_concept_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询同花顺概念板块指数日频率数据

    接口: akshare.stock_board_concept_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）

    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"
        start_date: 开始日期，格式为 "YYYYMMDD"
        end_date: 结束日期，格式为 "YYYYMMDD"

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "板块名称不能为空",
            "symbol": ""
        }

    logger.info(f"[同花顺概念板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_board_concept_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[同花顺概念板块指数] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺概念板块指数]")

        logger.info(f"[同花顺概念板块指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念板块指数失败: {str(e)}"
        logger.error(f"[同花顺概念板块指数] 异常 error={error_msg}")
        logger.debug(f"[同花顺概念板块指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_industry_summary_ths() -> Dict[str, Any]:
    """
    查询同花顺行业一览表

    接口: akshare.stock_board_industry_summary_ths

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "industry_summary" }
    """
    logger.info("[同花顺行业一览] 开始查询行业一览表")

    try:
        df = ak.stock_board_industry_summary_ths()

        if df.empty:
            logger.warning("[同花顺行业一览] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "industry_summary"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺行业一览]")

        logger.info(f"[同花顺行业一览] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "industry_summary"
        }

    except Exception as e:
        error_msg = f"查询同花顺行业一览失败: {str(e)}"
        logger.error(f"[同花顺行业一览] 异常 error={error_msg}")
        logger.debug(f"[同花顺行业一览] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "industry_summary"
        }


def get_stock_board_concept_info_ths(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介

    接口: akshare.stock_board_concept_info_ths

    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "板块名称不能为空",
            "symbol": ""
        }

    logger.info(f"[同花顺概念板块简介] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_board_concept_info_ths(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺概念板块简介] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺概念板块简介]")

        logger.info(f"[同花顺概念板块简介] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念板块简介失败: {str(e)}"
        logger.error(f"[同花顺概念板块简介] 异常 error={error_msg}")
        logger.debug(f"[同花顺概念板块简介] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_industry_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据

    接口: akshare.stock_board_industry_index_ths

    Args:
        symbol: 行业板块名称，如 "元件"
        start_date: 开始日期，格式为 "YYYYMMDD"
        end_date: 结束日期，格式为 "YYYYMMDD"

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "板块名称不能为空",
            "symbol": ""
        }

    logger.info(f"[同花顺行业板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_board_industry_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[同花顺行业板块指数] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺行业板块指数]")

        logger.info(f"[同花顺行业板块指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺行业板块指数失败: {str(e)}"
        logger.error(f"[同花顺行业板块指数] 异常 error={error_msg}")
        logger.debug(f"[同花顺行业板块指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_follow_xq(symbol: str = "最热门") -> Dict[str, Any]:
    """
    查询雪球关注排行榜

    接口: akshare.stock_hot_follow_xq

    Args:
        symbol: choice of {"本周新增", "最热门"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_symbols = ["本周新增", "最热门"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[雪球关注排行] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_follow_xq(symbol=symbol)

        if df.empty:
            logger.warning(f"[雪球关注排行] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[雪球关注排行]")

        logger.info(f"[雪球关注排行] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询雪球关注排行失败: {str(e)}"
        logger.error(f"[雪球关注排行] 异常 error={error_msg}")
        logger.debug(f"[雪球关注排行] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_rank_detail_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富股票热度历史趋势及粉丝特征

    接口: akshare.stock_hot_rank_detail_em

    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富股票热度详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_rank_detail_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富股票热度详情] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富股票热度详情]")

        logger.info(f"[东方财富股票热度详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富股票热度详情失败: {str(e)}"
        logger.error(f"[东方财富股票热度详情] 异常 error={error_msg}")
        logger.debug(f"[东方财富股票热度详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_keyword_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词

    接口: akshare.stock_hot_keyword_em

    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富人气榜关键词] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_keyword_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富人气榜关键词] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富人气榜关键词]")

        logger.info(f"[东方财富人气榜关键词] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富人气榜关键词失败: {str(e)}"
        logger.error(f"[东方财富人气榜关键词] 异常 error={error_msg}")
        logger.debug(f"[东方财富人气榜关键词] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_changes_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据

    接口: akshare.stock_changes_em

    Args:
        symbol: choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "异动类型不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富盘口异动] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_changes_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富盘口异动] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富盘口异动]")

        logger.info(f"[东方财富盘口异动] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富盘口异动失败: {str(e)}"
        logger.error(f"[东方财富盘口异动] 异常 error={error_msg}")
        logger.debug(f"[东方财富盘口异动] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_change_em() -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情

    接口: akshare.stock_board_change_em

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "board_change" }
    """
    logger.info("[东方财富板块异动] 开始查询板块异动数据")

    try:
        df = ak.stock_board_change_em()

        if df.empty:
            logger.warning("[东方财富板块异动] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "board_change"
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富板块异动]")

        logger.info(f"[东方财富板块异动] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "board_change"
        }

    except Exception as e:
        error_msg = f"查询东方财富板块异动失败: {str(e)}"
        logger.error(f"[东方财富板块异动] 异常 error={error_msg}")
        logger.debug(f"[东方财富板块异动] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "board_change"
        }
