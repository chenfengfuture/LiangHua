# -*- coding: utf-8 -*-
"""
板块概念模块
包含板块指数、行业信息、概念信息、股票热度、盘口异动等查询接口

统一格式：
1. 所有函数返回统一格式：{"success": bool, "data": list, "message": str}
2. 使用request_akshare_data进行安全调用和重试
3. 异常处理：任何错误都返回success=False，不抛出异常
4. 统一日志记录（logger.info / logger.error）
"""

import logging
from typing import Any, Dict, List

import akshare as ak

from system_service.service_result import error_result, success_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.board_field_mapper import (
    map_board_concept_index,
    map_board_industry_index,
    map_board_industry_summary,
    map_board_concept_info,
    map_stock_hot_follow,
    map_stock_hot_rank_detail,
    map_stock_hot_keyword,
    map_stock_changes,
    map_board_change
)

logger = logging.getLogger(__name__)


def get_stock_board_concept_index_ths(params) -> Dict[str, Any]:
    """
    查询同花顺概念板块指数日频率数据

    接口: akshare.stock_board_concept_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 概念板块名称，如 "阿里巴巴概念"
            - start_date (str): 开始日期，格式为 "YYYYMMDD"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 概念板块指数数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    
    logger.info(f"[同花顺概念板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_board_concept_index_ths,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        log_prefix="同花顺概念板块指数"
    )
    if not df:
        return error_result(message=f"[同花顺概念板块指数] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[同花顺概念板块指数] symbol={symbol} 查询成功，数据条数={len(df.get('data', []))}")

    # 应用映射函数
    result = map_board_concept_index(df)
    for item in result.get('data', []):
        item['concept_name'] = symbol
    print('1111', result.get('data')[0])
    return result


def get_stock_board_industry_summary_ths(params) -> Dict[str, Any]:
    """
    查询同花顺行业一览表

    接口: akshare.stock_board_industry_summary_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业一览表数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 行业一览表数据
            "message": str        # 成功或错误信息
        }
    """
    logger.info("[同花顺行业一览表] 开始查询")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_industry_summary_ths,
        log_prefix="同花顺行业一览表"
    )
    
    if not result:
        return error_result(message="[同花顺行业一览表] 查询失败，数据为空")
    
    logger.info(f"[同花顺行业一览表] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_board_industry_summary(result)
    print('111', mapped_result.get('data')[0])
    return mapped_result


def get_stock_board_concept_info_ths(params) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介
    
    接口: akshare.stock_board_concept_info_ths
    目标地址: https://data.10jqka.com.cn/funds/gn/（以实际为准）
    描述: 获取同花顺概念板块简介数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 概念板块名称，如 "阿里巴巴概念"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 概念板块简介数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    
    logger.info(f"[同花顺概念板块简介] 开始查询 symbol={symbol}")
    
    # 参数验证
    if not symbol:
        return error_result(message="概念板块名称不能为空")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_concept_info_ths,
        symbol=symbol,
        log_prefix="同花顺概念板块简介"
    )
    
    if not result:
        return error_result(message=f"[同花顺概念板块简介] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[同花顺概念板块简介] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_board_concept_info(result)
    return mapped_result


def get_stock_board_industry_index_ths(params) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据
    
    接口: akshare.stock_board_industry_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业板块指数日频率数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 行业板块名称，如 "元件"
            - start_date (str): 开始日期，格式为 "YYYYMMDD"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 行业板块指数数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    
    logger.info(f"[同花顺行业板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")
    
    # 参数验证
    if not symbol:
        return error_result(message="行业板块名称不能为空")
    
    if not start_date or not end_date:
        return error_result(message="开始日期和结束日期不能为空")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_industry_index_ths,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        log_prefix="同花顺行业板块指数"
    )
    
    if not result:
        return error_result(message=f"[同花顺行业板块指数] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[同花顺行业板块指数] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_board_industry_index(result)
    return mapped_result


def get_stock_hot_follow_xq(params) -> Dict[str, Any]:
    """
    查询雪球关注排行榜
    
    接口: akshare.stock_hot_follow_xq
    目标地址: 雪球网站
    描述: 获取雪球关注排行榜数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 选择类型，可选值: {"本周新增", "最热门"}，默认: "最热门"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 关注排行榜数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol', '最热门')
    
    logger.info(f"[雪球关注排行榜] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_hot_follow_xq,
        symbol=symbol,
        log_prefix="雪球关注排行榜"
    )
    
    if not result:
        return error_result(message=f"[雪球关注排行榜] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[雪球关注排行榜] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('mapped_result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_hot_follow(result)

    return mapped_result


def get_stock_hot_rank_detail_em(params) -> Dict[str, Any]:
    """
    查询东方财富股票热度历史趋势及粉丝特征
    
    接口: akshare.stock_hot_rank_detail_em
    目标地址: 东方财富网站
    描述: 获取东方财富股票热度历史趋势及粉丝特征数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股票热度详情数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    
    logger.info(f"[detail em] 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_stock_hot_rank_detail(result)
    return mapped_result


def get_stock_hot_keyword_em(params) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词
    
    接口: akshare.stock_hot_keyword_em
    目标地址: 东方财富网站
    描述: 获取东方财富个股人气榜热门关键词数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 热门关键词数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    
    logger.info(f"[keyword em] 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_stock_hot_keyword(result)
    return mapped_result


def get_stock_changes_em(params) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据
    
    接口: akshare.stock_changes_em
    目标地址: 东方财富网站
    描述: 获取东方财富盘口异动数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 异动类型，可选值: {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 盘口异动数据
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol')
    
    logger.info(f"[changes em] 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_stock_changes(result)
    return mapped_result


def get_stock_board_change_em(params) -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情
    
    接口: akshare.stock_board_change_em
    目标地址: 东方财富网站
    描述: 获取东方财富当日板块异动详情数据
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 板块异动详情数据
            "message": str        # 成功或错误信息
        }
    """
    logger.info("[东方财富板块异动] 开始查询")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_change_em,
        log_prefix="东方财富板块异动"
    )
    
    if not result:
        return error_result(message="[东方财富板块异动] 查询失败，数据为空")
    
    logger.info(f"[change em] 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_board_change(result)
    return mapped_result
