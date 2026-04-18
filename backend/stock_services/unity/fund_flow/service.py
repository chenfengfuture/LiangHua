# -*- coding: utf-8 -*-
"""
资金流向模块
包含个股资金流、板块资金流、大盘资金流等查询接口
"""

import logging
import random
import time
import traceback
from typing import Any, Dict

import akshare as ak

from ..utils import _convert_dataframe_to_list, safe_call_with_retry

logger = logging.getLogger(__name__)


def get_stock_fund_flow_individual(symbol: str = "即时") -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-个股资金流

    接口: akshare.stock_fund_flow_individual
    目标地址: https://data.10jqka.com.cn/funds/ggzjl/

    Args:
        symbol: 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_symbols = ["即时", "3日排行", "5日排行", "10日排行", "20日排行"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺个股资金流] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_fund_flow_individual(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺个股资金流] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺个股资金流]")

        logger.info(f"[同花顺个股资金流] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺个股资金流失败: {str(e)}"
        logger.error(f"[同花顺个股资金流] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺个股资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_fund_flow_concept(symbol: str = "即时") -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-概念资金流

    接口: akshare.stock_fund_flow_concept
    目标地址: https://data.10jqka.com.cn/funds/gnzjl/

    Args:
        symbol: 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_symbols = ["即时", "3日排行", "5日排行", "10日排行", "20日排行"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺概念资金流] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_fund_flow_concept(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺概念资金流] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺概念资金流]")

        logger.info(f"[同花顺概念资金流] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念资金流失败: {str(e)}"
        logger.error(f"[同花顺概念资金流] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺概念资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_individual_fund_flow(stock: str, market: str = "sz") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-个股资金流向（近100交易日）

    接口: akshare.stock_individual_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/detail.html

    Args:
        stock: 股票代码，如 "000425"
        market: 市场标识，choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not stock:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    valid_markets = ["sh", "sz", "bj"]
    if market not in valid_markets:
        return {
            "success": False,
            "data": None,
            "error": f"无效的market参数，请选择: {valid_markets}",
            "symbol": stock
        }

    logger.info(f"[东方财富个股资金流] 开始查询 stock={stock}, market={market}")

    try:
        df = ak.stock_individual_fund_flow(stock=stock, market=market)

        if df.empty:
            logger.warning(f"[东方财富个股资金流] stock={stock} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": stock
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富个股资金流]")

        logger.info(f"[东方财富个股资金流] stock={stock} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": stock
        }

    except Exception as e:
        error_msg = f"查询东方财富个股资金流失败: {str(e)}"
        logger.error(f"[东方财富个股资金流] stock={stock} 异常 error={error_msg}")
        logger.debug(f"[东方财富个股资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": stock
        }


def get_stock_individual_fund_flow_rank(indicator: str = "今日") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-资金流向排名

    接口: akshare.stock_individual_fund_flow_rank
    目标地址: http://data.eastmoney.com/zjlx/detail.html

    Args:
        indicator: 时间周期，choice of {"今日", "3日", "5日", "10日"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_indicators = ["今日", "3日", "5日", "10日"]
    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": ""
        }

    logger.info(f"[东方财富资金流向排名] 开始查询 indicator={indicator}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_individual_fund_flow_rank,
                indicator=indicator,
                max_retries=1,
                logger_name="资金流向排名"
            )

            if df is None or df.empty:
                logger.warning(f"[东方财富资金流向排名] indicator={indicator} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": indicator
                }

            data_list = _convert_dataframe_to_list(df, "[资金流向排名]")

            logger.info(f"[东方财富资金流向排名] indicator={indicator} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": indicator
            }

        except Exception as e:
            error_msg = f"查询东方财富资金流向排名失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[资金流向排名] 第{attempt + 1}次失败 indicator={indicator}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[资金流向排名] 最终失败 indicator={indicator}, error={error_msg}")
                logger.debug(f"[资金流向排名] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": indicator
                }


def get_stock_market_fund_flow() -> Dict[str, Any]:
    """
    查询东方财富-数据中心-大盘资金流向

    接口: akshare.stock_market_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/dpzjlx.html

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "market_fund_flow" }
    """
    logger.info("[东方财富大盘资金流] 开始查询大盘资金流向数据")

    try:
        df = ak.stock_market_fund_flow()

        if df.empty:
            logger.warning("[东方财富大盘资金流] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "market_fund_flow"
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富大盘资金流]")

        logger.info(f"[东方财富大盘资金流] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "market_fund_flow"
        }

    except Exception as e:
        error_msg = f"查询东方财富大盘资金流失败: {str(e)}"
        logger.error(f"[东方财富大盘资金流] 异常 error={error_msg}")
        logger.debug(f"[东方财富大盘资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "market_fund_flow"
        }


def get_stock_sector_fund_flow_rank(indicator: str = "今日", sector_type: str = "行业资金流") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-板块资金流排名

    接口: akshare.stock_sector_fund_flow_rank
    目标地址: https://data.eastmoney.com/bkzj/hy.html

    Args:
        indicator: 时间周期，choice of {"今日", "5日", "10日"}
        sector_type: 板块类型，choice of {"行业资金流", "概念资金流", "地域资金流"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_indicators = ["今日", "5日", "10日"]
    valid_sector_types = ["行业资金流", "概念资金流", "地域资金流"]

    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": ""
        }

    if sector_type not in valid_sector_types:
        return {
            "success": False,
            "data": None,
            "error": f"无效的sector_type参数，请选择: {valid_sector_types}",
            "symbol": ""
        }

    logger.info(f"[板块资金流排名] 开始查询 indicator={indicator}, sector_type={sector_type}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_sector_fund_flow_rank,
                indicator=indicator,
                sector_type=sector_type,
                max_retries=1,
                logger_name="板块资金流排名"
            )

            if df is None or df.empty:
                logger.warning(f"[板块资金流排名] indicator={indicator} sector_type={sector_type} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": f"{indicator}_{sector_type}"
                }

            data_list = _convert_dataframe_to_list(df, "[板块资金流排名]")

            logger.info(f"[板块资金流排名] indicator={indicator} sector_type={sector_type} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": f"{indicator}_{sector_type}"
            }

        except Exception as e:
            error_msg = f"查询东方财富板块资金流排名失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[板块资金流排名] 第{attempt + 1}次失败 indicator={indicator}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[板块资金流排名] 最终失败 indicator={indicator}, sector_type={sector_type}, error={error_msg}")
                logger.debug(f"[板块资金流排名] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": f"{indicator}_{sector_type}"
                }


def get_stock_sector_fund_flow_summary(symbol: str, indicator: str = "今日") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-行业个股资金流

    接口: akshare.stock_sector_fund_flow_summary
    目标地址: https://data.eastmoney.com/bkzj/BK1034.html

    Args:
        symbol: 行业板块名称，如 "电源设备"
        indicator: 时间周期，choice of {"今日", "5日", "10日"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "行业板块名称不能为空",
            "symbol": ""
        }

    valid_indicators = ["今日", "5日", "10日"]
    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": symbol
        }

    logger.info(f"[行业个股资金流] 开始查询 symbol={symbol}, indicator={indicator}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_sector_fund_flow_summary,
                symbol=symbol,
                indicator=indicator,
                max_retries=1,
                logger_name="行业个股资金流"
            )

            if df is None or df.empty:
                logger.warning(f"[行业个股资金流] symbol={symbol} indicator={indicator} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[行业个股资金流]")

            logger.info(f"[行业个股资金流] symbol={symbol} indicator={indicator} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富行业个股资金流失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[行业个股资金流] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[行业个股资金流] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[行业个股资金流] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_main_fund_flow(symbol: str = "全部股票") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-主力净流入排名

    接口: akshare.stock_main_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/list.html

    Args:
        symbol: 市场筛选，choice of {"全部股票", "沪深A股", "沪市A股", "科创板",
                  "深市A股", "创业板", "沪市B股", "深市B股"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_symbols = ["全部股票", "沪深A股", "沪市A股", "科创板",
                     "深市A股", "创业板", "沪市B股", "深市B股"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[东方财富主力净流入排名] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_main_fund_flow(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富主力净流入排名] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富主力净流入排名]")

        logger.info(f"[东方财富主力净流入排名] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富主力净流入排名失败: {str(e)}"
        logger.error(f"[东方财富主力净流入排名] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富主力净流入排名] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }
