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

from stock_services.unity.utils import request_akshare_data
from system_service import error_result
from stock_services.utils.field_mapper import *

logger = logging.getLogger(__name__)


def get_stock_fund_flow_individual(params: dict) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-个股资金流

    接口: akshare.stock_fund_flow_individual
    目标地址: https://data.10jqka.com.cn/funds/ggzjl/

    Args:
        params:  symbol参数 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    """
    import akshare as ak

    symbol = params.get('symbol')
    limits = max(1, min(500, int(params.get('limits', 200) or 200)))
    logger.info(f"[资金流向-个股资金流] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_fund_flow_individual,
        symbol=symbol,
        log_prefix="资金流向-个股资金流"
    )
    if not result:
        return error_result(message=f"[资金流向-个股资金流] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[资金流向-个股资金流] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    # 截取前200的数据
    mapped_result['data'] = mapped_result.get('data', [])[:limits]
    for item in mapped_result['data']:
        item['period_type'] = symbol
    return mapped_result



def get_stock_fund_flow_concept(params: dict) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-概念资金流

    接口: akshare.stock_fund_flow_concept
    目标地址: https://data.10jqka.com.cn/funds/gnzjl/

    Args:
        symbol: 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    """
    import akshare as ak
    symbol = params.get('symbol')
    limits = max(1, min(40, int(params.get('limits', 40) or 40)))
    logger.info(f"[资金流向-个股资金流] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_fund_flow_concept,
        symbol=symbol,
        log_prefix="资金流向-个股资金流"
    )
    if not result:
        return error_result(message=f"[资金流向-个股资金流] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[资金流向-个股资金流] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    # 截取前200的数据
    mapped_result['data'] = mapped_result.get('data', [])[:limits]
    for item in mapped_result['data']:
        item['period_type'] = symbol
    return mapped_result



def get_stock_individual_fund_flow(params: dict) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-个股资金流向（近100交易日）

    接口: akshare.stock_individual_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/detail.html

    Args:
        stock: 股票代码，如 "000425"
        market: 市场标识，choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    import akshare as ak
    symbol = params.get('stock')
    logger.info(f"[东方财富-个股资金流向] 开始查询 symbol={symbol}")
    market = ""
    if len(symbol) == 6:
        if symbol.startswith('6'):
            market = "sh"
        elif symbol.startswith('0') or symbol.startswith('3'):
            market = "sz"
        elif symbol.startswith('8'):
            market = "bj"
        else:
            return error_result(message=f"[方财富-个股资金流向] symbol={symbol} 参数错误")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_individual_fund_flow,
        stock=symbol, market=market,
        log_prefix="方财富-个股资金流向"
    )
    if not result:
        return error_result(message=f"[方财富-个股资金流向] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[方财富-个股资金流] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    for item in result['data']:
        item['symbol']=symbol
    # 应用映射函数
    mapped_result = map_stock_change_symbol(result)

    return mapped_result



def get_stock_individual_fund_flow_rank(params: dict) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-资金流向-排名

    接口失败中..

    接口: akshare.stock_individual_fund_flow_rank
    目标地址: http://data.eastmoney.com/zjlx/detail.html

    Args:
        indicator: 时间周期，choice of {"今日", "3日", "5日", "10日"}

    """
    import akshare as ak
    indicator = params.get('indicator')
    logger.info(f"[东方财富-资金流向排名] 开始查询 symbol={indicator}")

    result = request_akshare_data(
        ak.stock_individual_fund_flow_rank,
        indicator=indicator,
        log_prefix="方财富-资金流向排名"
    )
    if not result:
        return error_result(message=f"[方财富-资金流向排名] symbol={indicator} 查询失败，数据为空")

    logger.info(f"[方财富-资金流向排名] symbol={indicator} 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_ask(result)

    return mapped_result


def get_stock_market_fund_flow(params: dict) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-大盘资金流向

    接口: akshare.stock_market_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/dpzjlx.html
    """
    import akshare as ak
    logger.info("[东方财富大盘资金流] 开始查询大盘资金流向数据")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_market_fund_flow,
        log_prefix="东方财富大盘资金流"
    )
    if not result:
        return error_result(message=f"[东方财富大盘资金流] 查询失败，数据为空")

    logger.info(f"[东方财富大盘资金流]  查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result



def get_stock_sector_fund_flow_rank(params: dict) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-板块资金流排名（替代东方财富push2已封接口）

    行业资金流: akshare.stock_fund_flow_industry
    目标地址: https://data.10jqka.com.cn/funds/hyzjl/

    概念资金流: akshare.stock_fund_flow_concept
    目标地址: https://data.10jqka.com.cn/funds/gnzjl/

    Args:
        indicator: 时间周期，EM格式 {"今日", "3日", "5日", "10日"} → 自动转为THS格式
        sector_type: 板块类型，choice of {"行业资金流", "概念资金流", "地域资金流"}

    Returns:
        统一结构：{ "success": bool, "data": list[dict] | None, "message": str }
    """
    import akshare as ak
    indicator = params.get('indicator', '今日')
    sector_type = params.get('sector_type', '行业资金流')

    # EM → THS 时间周期映射
    _INDICATOR_MAP = {"今日": "即时", "3日": "3日排行", "5日": "5日排行", "10日": "10日排行"}
    ths_indicator = _INDICATOR_MAP.get(indicator, "即时")

    logger.info(f"[板块资金流排名] 开始查询 {indicator}(->{ths_indicator})-{sector_type}")

    if sector_type == "行业资金流":
        result = request_akshare_data(
            ak.stock_fund_flow_industry,
            symbol=ths_indicator,
            log_prefix="板块资金流排名-行业"
        )
    elif sector_type == "概念资金流":
        result = request_akshare_data(
            ak.stock_fund_flow_concept,
            symbol=ths_indicator,
            log_prefix="板块资金流排名-概念"
        )
    else:
        return error_result(message=f"[板块资金流排名] 暂不支持的板块类型: {sector_type}（同花顺仅支持行业/概念）")

    if not result:
        return error_result(message=f"[板块资金流排名] {sector_type} 查询失败，数据为空")

    logger.info(f"[板块资金流排名] {sector_type} 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_sector_fund_flow_summary(params: dict) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-个股资金流（替代东方财富行业个股资金流）

    接口: akshare.stock_fund_flow_individual
    目标地址: https://data.10jqka.com.cn/funds/ggzjl/

    注意：同花顺接口不按板块过滤，返回全市场个股资金流数据。
    客户端可自行按板块名称筛选。

    Args:
        symbol: 板块名称（仅用于日志，同花顺接口不按板块过滤）
        indicator: 时间周期，EM格式 {"今日", "5日", "10日"} → 自动转为THS格式

    Returns:
        统一结构：{ "success": bool, "data": list[dict] | None, "message": str }
    """
    import akshare as ak
    indicator = params.get('indicator', '今日')
    symbol = params.get('symbol', '')
    # EM → THS 时间周期映射
    _INDICATOR_MAP = {"今日": "即时", "5日": "5日排行", "10日": "10日排行"}
    ths_indicator = _INDICATOR_MAP.get(indicator, "即时")
    logger.info(f"[行业个股资金流] 开始查询 {symbol}-{indicator}(->{ths_indicator})")

    result = request_akshare_data(
        ak.stock_fund_flow_individual,
        symbol=ths_indicator,
        log_prefix="行业个股资金流"
    )
    if not result:
        return error_result(message=f"[行业个股资金流] 查询失败，数据为空")

    logger.info(f"[行业个股资金流] 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_main_fund_flow(params: dict) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-个股资金流向排名（替代东方财富主力净流入排名）

    接口: akshare.stock_fund_flow_individual
    目标地址: https://data.10jqka.com.cn/funds/ggzjl/

    Args:
        symbol: 原为市场筛选，现仅用于日志记录

    Returns:
        统一结构：{ "success": bool, "data": list[dict] | None, "message": str }
    """
    import akshare as ak

    symbol = params.get('symbol', '全部股票')
    logger.info(f"[主力净流入排名] 开始查询 {symbol}->同花顺个股资金流")
    # 调用AKShare同花顺接口
    result = request_akshare_data(
        ak.stock_fund_flow_individual,
        symbol="即时",
        log_prefix="主力净流入排名"
    )
    if not result:
        return error_result(message=f"[主力净流入排名] 查询失败，数据为空")

    logger.info(f"[主力净流入排名]  查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result