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

from system_service import error_result
from ..utils import _convert_dataframe_to_list, request_akshare_data
from stock_services.utils.field_mapper import *

logger = logging.getLogger(__name__)


def get_stock_financial_report_sina(params: dict) -> Dict[str, Any]:
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
    import akshare as ak

    logger.info("[新浪财务报表] 开始查询")
    stock = params.get('stock')
    symbol = params.get('symbol')
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_financial_report_sina,
        stock=stock,
        symbol=symbol,
        log_prefix="新浪财务报表"
    )

    if not result:
        return error_result(message="[新浪财务报表] 查询失败，数据为空")
    logger.info(f"[新浪财务报表] 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_balance_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富资产负债表（按年度）查询接口,  不进入数据库, redis

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
    import akshare as ak
    logger.info("[财务分析-资产负债表] 开始查询")
    symbol = normalize_symbol(symbol, 2)
    if not symbol:
        logger.info("[财务分析-资产负债表] symbol 参数缺失或者参数错误")
        return error_result('请求参数缺失')
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_balance_sheet_by_yearly_em,
        symbol=symbol,
        log_prefix="财务分析-资产负债表"
    )

    if not result:
        return error_result(message="[财务分析-资产负债表] 查询失败，数据为空")
    logger.info(f"[财务分析-资产负债表] 查询成功，数据条数={len(result.get('data', []))}")
    return result


def get_stock_profit_sheet_by_report(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按报告期）查询接口 不进入数据库, redis

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
    import akshare as ak
    logger.info("[东方财富利润表-报告期] 开始查询")

    symbol = normalize_symbol(symbol, 2)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_profit_sheet_by_report_em,
        symbol=symbol,
        log_prefix="东方财富利润表-报告期"
    )

    if not result:
        return error_result(message="[东方财富利润表-报告期] 查询失败，数据为空")
    logger.info(f"[东方财富利润表-报告期] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    return result


def get_stock_profit_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按年度）查询接口 不进入数据库, redis

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
    import akshare as ak

    logger.info("[东方财富利润表-年度] 开始查询")

    symbol = normalize_symbol(symbol, 2)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_profit_sheet_by_report_em,
        symbol=symbol,
        log_prefix="东方财富利润表-年度"
    )

    if not result:
        return error_result(message="[东方财富利润表-年度] 查询失败，数据为空")
    logger.info(f"[东方财富利润表-年度] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    return result


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
    import akshare as ak
    logger.info("[东方财富现金流量表-报告期] 开始查询")

    symbol = normalize_symbol(symbol, 2)
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_profit_sheet_by_report_em,
        symbol=symbol,
        log_prefix="东方财富现金流量表-报告期"
    )

    if not result:
        return error_result(message="[东方财富现金流量表-报告期] 查询失败，数据为空")
    logger.info(f"[东方财富现金流量表-报告期] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    return result



def get_stock_profit_forecast_ths(params: dict) -> Dict[str, Any]:
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
    """
    import akshare as ak

    indicator = params.get('indicator')
    symbol = params.get('symbol')
    print('111', symbol)
    logger.info(f"[同花顺盈利预测数据] {indicator}开始查询")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_profit_forecast_ths,
        indicator=indicator,
        symbol=symbol,
        log_prefix="同花顺盈利预测数据"
    )

    if not result:
        return error_result(message=f"[同花顺盈利预测数据] {indicator}查询失败，数据为空")
    logger.info(f"[同花顺盈利预测数据]{indicator} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    for item in result.get('data', []):
        item['symbol'] = symbol
        item['forecast_type'] = indicator
    # 应用映射函数
    mapped_result = map_stock_change_symbol(result)
    print('mapped_result', mapped_result['data'][0])
    return mapped_result


