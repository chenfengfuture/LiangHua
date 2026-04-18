# -*- coding: utf-8 -*-
"""
财务报表模块
包含新浪财经财务报表、东方财富财务报表等查询接口
"""

import logging
import random
import time
import traceback
from typing import Any, Dict

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_financial_report_sina(stock: str, symbol: str = "资产负债表") -> Dict[str, Any]:
    """
    新浪财经财务报表查询接口（新浪财经）

    接口: stock_financial_report_sina
    目标地址: https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/600600/displaytype/4.phtml
    描述: 新浪财经-财务报表-三大报表
    限量: 单次获取指定报表的所有年份数据的历史数据

    输入参数:
        stock: str - 带市场标识的股票代码，如 "sh600600"（沪市）或 "sz000001"（深市）
        symbol: str - 报表类型，可选值："资产负债表"、"利润表"、"现金流量表"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": stock
        }
    """
    if not stock or not isinstance(stock, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 sh600600",
            "symbol": stock or ""
        }

    valid_symbols = ["资产负债表", "利润表", "现金流量表"]
    if symbol not in valid_symbols:
        symbol = "资产负债表"

    logger.info(f"[新浪财务报表] 开始查询 stock={stock}, symbol={symbol}")

    try:
        df = ak.stock_financial_report_sina(stock=stock, symbol=symbol)

        if df.empty:
            logger.warning(f"[新浪财务报表] 返回数据为空 stock={stock}, symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": stock
            }

        data_list = _convert_dataframe_to_list(df, "[新浪财务报表]")

        logger.info(f"[新浪财务报表] 查询成功 stock={stock}, symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": stock
        }

    except Exception as e:
        error_msg = f"查询新浪财务报表失败: {str(e)}"
        logger.error(f"[新浪财务报表] 异常 stock={stock}, error={error_msg}")
        logger.debug(f"[新浪财务报表] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": stock
        }


def get_stock_balance_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富资产负债表（按年度）查询接口

    接口: stock_balance_sheet_by_yearly_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
    描述: 东方财富-股票-财务分析-资产负债表-按年度
    限量: 单次获取指定 symbol 的资产负债表-按年度数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

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
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富资产负债表] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)

            if df is None or len(df) == 0:
                logger.warning(f"[东方财富资产负债表] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[东方财富资产负债表]")

            logger.info(f"[东方财富资产负债表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富资产负债表失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[东方财富资产负债表] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[东方财富资产负债表] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[东方财富资产负债表] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_profit_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按报告期）查询接口

    接口: stock_profit_sheet_by_report_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
    描述: 东方财富-股票-财务分析-利润表-报告期
    限量: 单次获取指定 symbol 的利润表-报告期数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

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
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富利润表] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富利润表] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富利润表]")

        logger.info(f"[东方财富利润表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富利润表失败: {str(e)}"
        logger.error(f"[东方财富利润表] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[东方财富利润表] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_profit_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按年度）查询接口

    接口: stock_profit_sheet_by_yearly_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519#lrb-0
    描述: 东方财富-股票-财务分析-利润表-按年度
    限量: 单次获取指定 symbol 的利润表-按年度数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

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
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富利润表(年度)] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富利润表(年度)] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富利润表(年度)]")

        logger.info(f"[东方财富利润表(年度)] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富利润表(年度)失败: {str(e)}"
        logger.error(f"[东方财富利润表(年度)] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[东方财富利润表(年度)] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_cash_flow_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富现金流量表（按报告期）查询接口

    接口: stock_cash_flow_sheet_by_report_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519#lrb-0
    描述: 东方财富-股票-财务分析-现金流量表-按报告期
    限量: 单次获取指定 symbol 的现金流量表-按报告期数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

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
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富现金流量表] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)

            if df is None or len(df) == 0:
                logger.warning(f"[东方财富现金流量表] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[东方财富现金流量表]")

            logger.info(f"[东方财富现金流量表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富现金流量表失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[东方财富现金流量表] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[东方财富现金流量表] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[东方财富现金流量表] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_profit_forecast_ths(symbol: str, indicator: str = "预测年报每股收益") -> Dict[str, Any]:
    """
    同花顺盈利预测数据查询接口

    接口: stock_profit_forecast_ths
    目标地址: https://data.10jqka.com.cn/fundamental/ipo/#
    描述: 同花顺-数据中心-盈利预测

    输入参数:
        symbol: str - 股票代码，如 "000001"
        indicator: str - 指标类型，choice of {
            "预测年报每股收益",
            "预测年报净利润",
            "业绩预测详表-机构",
            "业绩预测详表-详细指标预测"
        }

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

    valid_indicators = ["预测年报每股收益", "预测年报净利润",
                        "业绩预测详表-机构", "业绩预测详表-详细指标预测"]
    if indicator not in valid_indicators:
        indicator = "预测年报每股收益"

    logger.info(f"[同花顺盈利预测] 开始查询 symbol={symbol}, indicator={indicator}")

    try:
        df = ak.stock_profit_forecast_ths(symbol=symbol, indicator=indicator)

        if df.empty:
            logger.warning(f"[同花顺盈利预测] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺盈利预测]")

        logger.info(f"[同花顺盈利预测] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺盈利预测失败: {str(e)}"
        logger.error(f"[同花顺盈利预测] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[同花顺盈利预测] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }
