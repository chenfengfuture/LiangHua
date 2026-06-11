# -*- coding: utf-8 -*-
"""
龙虎榜模块
包含龙虎榜详情、机构买卖统计、营业部数据等查询接口
"""

import logging
import traceback
from typing import Any, Dict

from system_service.service_result import error_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import map_stock_ask, map_stock_change_symbol

logger = logging.getLogger(__name__)


def get_stock_lhb_jgmmtj_em(params) -> Dict[str, Any]:
    """
    龙虎榜机构买卖每日统计查询接口（东方财富接口）

    接口: stock_lhb_jgmmtj_em
    目标地址: https://data.eastmoney.com/stock/jgmmtj.html
    描述: 东方财富网-数据中心-龙虎榜单-机构买卖每日统计
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - start_date (str): 开始日期，格式为 "YYYYMMDD"，如 "20240417"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"，如 "20240430"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 机构买卖统计数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    logger.info(f"[机构买卖统计] 开始查询 start_date={start_date}, end_date={end_date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_jgmmtj_em,
        start_date=start_date,
        end_date=end_date,
        log_prefix="机构买卖统计"
    )
    
    if not result:
        return error_result(message=f"[机构买卖统计] start_date={start_date}, end_date={end_date} 查询失败，数据为空")
    
    logger.info(f"[机构买卖统计] start_date={start_date}, end_date={end_date} 查询成功，数据条数={len(result.get('data', []))}")

    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['start_date'] = start_date
        item['end_date'] = end_date
    return map_result


def get_stock_lhb_detail_em(params) -> Dict[str, Any]:
    """
    龙虎榜详情查询接口（东方财富接口）

    接口: stock_lhb_detail_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-龙虎榜详情
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - start_date (str): 开始日期，格式为 "YYYYMMDD"，如 "20220314"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"，如 "20220315"
    """
    import akshare as ak
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    logger.info(f"[龙虎榜详情] 开始查询 start_date={start_date}, end_date={end_date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_detail_em,
        start_date=start_date,
        end_date=end_date,
        log_prefix="龙虎榜详情"
    )
    
    if not result:
        return error_result(message=f"[龙虎榜详情] start_date={start_date}, end_date={end_date} 查询失败，数据为空")
    
    logger.info(f"[龙虎榜详情] start_date={start_date}, end_date={end_date} 查询成功，数据条数={len(result.get('data', []))}")
    print('map_result', result['data'][0])
    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['start_date'] = start_date
        item['end_date'] = end_date
    print('map_result', map_result['data'][0])
    return map_result


def get_stock_lhb_stock_statistic_em(params) -> Dict[str, Any]:
    """
    个股上榜统计查询接口（东方财富接口）

    接口: stock_lhb_stock_statistic_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-个股上榜统计
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 时间范围，可选值：
                  "近一月" - 近一个月数据（默认）
                  "近三月" - 近三个月数据
                  "近六月" - 近六个月数据
                  "近一年" - 近一年数据
    """
    import akshare as ak
    symbol = params.get('symbol', '近一月')
    logger.info(f"[个股上榜统计] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_stock_statistic_em,
        symbol=symbol,
        log_prefix="个股上榜统计"
    )
    
    if not result:
        return error_result(message=f"[个股上榜统计] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[个股上榜统计] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    map_result = map_stock_ask(result)

    for item in map_result['data']:
        item['data_type'] = symbol
    return map_result


def get_stock_lhb_hyyyb_em(params) -> Dict[str, Any]:
    """
    每日活跃营业部查询接口（东方财富接口）

    接口: stock_lhb_hyyyb_em
    目标地址: https://data.eastmoney.com/stock/hyyyb.html
    描述: 东方财富网-数据中心-龙虎榜单-每日活跃营业部
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - start_date (str): 开始日期，格式为 "YYYYMMDD"，如 "20220311"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"，如 "20220315"

    """
    import akshare as ak
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    logger.info(f"[每日活跃营业部] 开始查询 start_date={start_date}, end_date={end_date}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_hyyyb_em,
        start_date=start_date,
        end_date=end_date,
        log_prefix="每日活跃营业部"
    )
    
    if not result:
        return error_result(message=f"[每日活跃营业部] start_date={start_date}, end_date={end_date} 查询失败，数据为空")
    print('map_result', result['data'][0])
    logger.info(f"[每日活跃营业部] start_date={start_date}, end_date={end_date} 查询成功，数据条数={len(result.get('data', []))}")

    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['start_date'] = start_date
        item['end_date'] = end_date
    return map_result


def get_stock_lhb_yyb_detail_em(params) -> Dict[str, Any]:
    """
    营业部详情数据查询接口（东方财富接口）

    接口: stock_lhb_yyb_detail_em
    目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
    描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
    限量: 单次返回指定营业部的所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 营业部代码，如 "10026729"
    """
    import akshare as ak
    symbol = params.get('symbol')
    logger.info(f"[营业部详情] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_yyb_detail_em,
        symbol=symbol,
        log_prefix="营业部详情"
    )
    
    if not result:
        return error_result(message=f"[营业部详情] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[营业部详情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    map_result = map_stock_ask(result)

    # 应用映射函数（如果没有特定的映射函数，直接返回结果）
    return result


def get_stock_lhb_yybph_em(params) -> Dict[str, Any]:
    """
    东方财富网-数据中心-龙虎榜单-营业部排行

    接口: stock_lhb_yybph_em
    目标地址: https://data.eastmoney.com/stock/yybph.html
    描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol="近一月"; choice of {"近一月", "近三月", "近六月", "近一年"}

    """
    import akshare as ak
    symbol = params.get('symbol')

    if not symbol or not isinstance(symbol, str):
        return error_result(message="营业部代码必须为非空字符串")

    logger.info(f"[营业部排行] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_yybph_em,
        symbol=symbol,
        log_prefix="营业部排行"
    )

    if not result:
        return error_result(message=f"[营业部排行] symbol={symbol} 查询失败，数据为空")
    logger.info(f"[营业部排行] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['data_type'] = symbol

    return map_result

def get_stock_lhb_traderstatistic_em(params) -> Dict[str, Any]:
    """
    东方财富网-数据中心-龙虎榜单-营业部统计

    接口: stock_lhb_traderstatistic_em
    目目标地址: https://data.eastmoney.com/stock/traderstatistic.html
    描述: 东方财富网-数据中心-龙虎榜单-营业部统计
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol="近一月"; choice of {"近一月", "近三月", "近六月", "近一年"}

    """
    import akshare as ak
    symbol = params.get('symbol')

    logger.info(f"[营业部统计] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_traderstatistic_em,
        symbol=symbol,
        log_prefix="营业部统计"
    )

    if not result:
        return error_result(message=f"[营业部统计] symbol={symbol} 查询失败，数据为空")
    logger.info(f"[营业部统计] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('map_result', result['data'][0])
    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['data_type'] = symbol
    print('map_result', map_result['data'][0])
    return map_result


def get_stock_lhb_stock_detail_em(params) -> Dict[str, Any]:
    """
    东方财富网-龙虎榜单-个股龙虎榜详情
    接口: stock_lhb_stock_detail_em
    目标地址: https://data.eastmoney.com/stock/lhb/600077.html
    描述: 东方财富网-数据中心-龙虎榜单-个股龙虎榜详情
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol="600077";
            - date="20220310"; 需要通过 ak.stock_lhb_stock_detail_date_em(symbol="600077") 接口获取相应股票的有龙虎榜详情数据的日期
            - flag="卖出"; choice of {"买入", "卖出"}

    """
    import akshare as ak
    symbol = params.get('symbol')
    flag = params.get('flag')
    date = params.get('date')
    logger.info(f"[个股龙虎榜详情] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lhb_stock_detail_em,
        symbol=symbol, date=date, flag=flag,
        log_prefix="个股龙虎榜详情"
    )

    if not result:
        return error_result(message=f"[个股龙虎榜详情] symbol={symbol} 查询失败，数据为空")
    logger.info(f"[个股龙虎榜详情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('map_result', result['data'][0])
    map_result = map_stock_ask(result)
    for item in map_result['data']:
        item['data_type'] = symbol
    print('map_result', map_result['data'][0])
    return map_result



def get_stock_lhb_stock_detail_date_em(params) -> Dict[str, Any]:
    """
    东方财富网-龙虎榜单-个股龙虎榜日期列表
    接口: stock_lhb_stock_detail_date_em
    目标地址: https://data.eastmoney.com/stock/lhb/600077.html
    描述: 东方财富网-数据中心-龙虎榜单-获取指定个股**所有上过龙虎榜的日期列表**
    限量: 单次返回指定股票的所有龙虎榜历史日期

    Args:
        params: 参数字典，包含字段：
            - symbol: 股票代码，如 "600077"

    """
    import akshare as ak
    symbol = params.get('symbol')
    logger.info(f"[个股龙虎榜日期] 开始查询：股票代码={symbol}")

    # 调用AKShare接口获取龙虎榜日期列表
    result = request_akshare_data(
        ak.stock_lhb_stock_detail_date_em,
        symbol=symbol,
        log_prefix="个股龙虎榜日期"
    )

    if not result:
        return error_result(message=f"[个股龙虎榜日期] symbol={symbol} 查询失败，数据为空")
    logger.info(f"[个股龙虎榜日期] symbol={symbol} 查询成功，龙虎榜日期数量={len(result.get('data', []))}")
    print('map_result', result['data'][0])
    map_result = map_stock_change_symbol(result)
    print('map_result', map_result['data'][0])
    return map_result


def get_stock_lh_yyb_most(params) -> Dict[str, Any]:
    """
    龙虎榜-营业部排行-上榜次数最多
    接口: stock_lh_yyb_most
    目标地址: https://data.10jqka.com.cn/market/longhu/
    描述: 东方财富网/同花顺-数据中心-龙虎榜-营业部排行-上榜次数最多
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典（本接口无需传入参数）
    """
    import akshare as ak
    logger.info("[营业部排行-上榜次数最多] 开始查询")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_lh_yyb_most,
        log_prefix="营业部排行-上榜次数最多"
    )

    if not result:
        return error_result(message="[营业部排行-上榜次数最多] 查询失败，数据为空")
    logger.info(f"[营业部排行-上榜次数最多] 查询成功，数据条数={len(result.get('data', []))}")
    print('map_result', result['data'][0])
    # 数据格式化
    map_result = map_stock_ask(result)
    print('map_result', map_result['data'][0])
    return map_result



def get_stock_lh_yyb_capital() -> Dict[str, Any]:
    """
    龙虎榜-营业部排行-资金实力最强
    接口: stock_lh_yyb_capital
    目标地址: https://data.10jqka.com.cn/market/longhu/
    描述: 同花顺-数据中心-龙虎榜-营业部排行-资金实力最强
    限量: 单次返回所有历史数据

    Args:
        params: 参数字典（本接口无需传入参数）
    """
    import akshare as ak
    logger.info("[营业部排行-资金实力最强] 开始查询")

    # 调用 AKShare 接口
    result = request_akshare_data(
        ak.stock_lh_yyb_capital,
        log_prefix="营业部排行-资金实力最强"
    )

    if not result:
        return error_result(message="[营业部排行-资金实力最强] 查询失败，数据为空")

    logger.info(f"[营业部排行-资金实力最强] 查询成功，数据条数={len(result.get('data', []))}")

    # 数据格式化
    # map_result = map_stock_ask(result)
    return result