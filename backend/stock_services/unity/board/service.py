# -*- coding: utf-8 -*-
"""
板块概念模块 - 重构版本
包含板块指数、行业信息、概念信息、股票热度、盘口异动等查询接口

重构说明：
1. 使用全局异常处理器处理所有异常
2. 服务函数直接抛出异常，由全局异常处理器捕获
3. 使用统一的工具函数，避免重复代码
4. 移除无效的try-except包装
"""

import logging
import traceback
from typing import Any, Dict, List

import akshare as ak

from stock_services.unity.utils import (
    safe_call_with_retry,
    _convert_dataframe_to_list,
)

logger = logging.getLogger(__name__)


def get_stock_board_concept_index_ths(symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    查询同花顺概念板块指数日频率数据

    接口: akshare.stock_board_concept_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）

    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"
        start_date: 开始日期，格式为 "YYYYMMDD"
        end_date: 结束日期，格式为 "YYYYMMDD"

    Returns:
        概念板块指数数据列表
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        # 如果参数验证失败，返回空列表
        return []
    
    if not start_date or not end_date:
        # 如果参数验证失败，返回空列表
        return []
    
    # 调用AKShare API
    try:
        df = ak.stock_board_concept_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)
        
        # 检查数据是否为空
        if df is None or df.empty:
            return []
        
        # 转换数据格式
        data_list = _convert_dataframe_to_list(df, "[同花顺概念板块指数]")
        return data_list
        
    except Exception as e:
        logger.error(f"[同花顺概念板块指数] 查询失败: {symbol}, 错误: {e}")
        return []


def get_stock_board_industry_summary_ths() -> List[Dict[str, Any]]:
    """
    查询同花顺行业一览表

    接口: akshare.stock_board_industry_summary_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业一览表数据

    Returns:
        行业一览表数据列表
    """
    # 调用AKShare API
    try:
        df = ak.stock_board_industry_summary_ths()
        
        # 检查数据是否为空
        if df is None or df.empty:
            return []
        
        # 转换数据格式
        data_list = _convert_dataframe_to_list(df, "[同花顺行业一览表]")
        return data_list
        
    except Exception as e:
        logger.error(f"[同花顺行业一览表] 查询失败, 错误: {e}")
        return []


def get_stock_board_concept_info_ths(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介
    
    接口: akshare.stock_board_concept_info_ths
    目标地址: https://data.10jqka.com.cn/funds/gn/（以实际为准）
    描述: 获取同花顺概念板块简介数据
    
    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "板块名称不能为空",
            "symbol": ""
        }
    
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_board_concept_info_ths,
        context="同花顺概念板块简介",
        symbol=symbol
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": symbol
        }
    
    return api_result


def get_stock_board_industry_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据
    
    接口: akshare.stock_board_industry_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业板块指数日频率数据
    
    Args:
        symbol: 行业板块名称，如 "元件"
        start_date: 开始日期，格式为 "YYYYMMDD"
        end_date: 结束日期，格式为 "YYYYMMDD"
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "板块名称不能为空",
            "symbol": ""
        }
    
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_board_industry_index_ths,
        context="同花顺行业板块指数",
        symbol=symbol,
        start_date=start_date,
        end_date=end_date
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": symbol
        }
    
    return api_result


def get_stock_hot_follow_xq(symbol: str = "最热门") -> Dict[str, Any]:
    """
    查询雪球关注排行榜
    
    接口: akshare.stock_hot_follow_xq
    目标地址: 雪球网站
    描述: 获取雪球关注排行榜数据
    
    Args:
        symbol: choice of {"本周新增", "最热门"}
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    valid_symbols = ["本周新增", "最热门"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"参数必须为以下值之一: {', '.join(valid_symbols)}",
            "symbol": symbol
        }
    
    # 调用AKShare API
    try:
        df = ak.stock_hot_follow_xq(symbol=symbol)
        
        # 检查数据是否为空
        if df is None or df.empty:
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }
        
        # 转换数据格式
        data_list = _convert_dataframe_to_list(df, "[雪球关注排行榜]")
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }
        
    except Exception as e:
        logger.error(f"[雪球关注排行榜] 查询失败: {symbol}, 错误: {e}")
        return {
            "success": False,
            "data": None,
            "error": f"查询失败: {str(e)}",
            "symbol": symbol
        }


def get_stock_hot_rank_detail_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富股票热度历史趋势及粉丝特征
    
    接口: akshare.stock_hot_rank_detail_em
    目标地址: 东方财富网站
    描述: 获取东方财富股票热度历史趋势及粉丝特征数据
    
    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }
    
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_hot_rank_detail_em,
        context="东方财富股票热度详情",
        symbol=symbol
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": symbol
        }
    
    return api_result


def get_stock_hot_keyword_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词
    
    接口: akshare.stock_hot_keyword_em
    目标地址: 东方财富网站
    描述: 获取东方财富个股人气榜热门关键词数据
    
    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }
    
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_hot_keyword_em,
        context="东方财富人气榜关键词",
        symbol=symbol
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": symbol
        }
    
    return api_result


def get_stock_changes_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据
    
    接口: akshare.stock_changes_em
    目标地址: 东方财富网站
    描述: 获取东方财富盘口异动数据
    
    Args:
        symbol: choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
        
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": str}
    """
    # 参数验证
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "异动类型不能为空",
            "symbol": ""
        }
    
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_changes_em,
        context="东方财富盘口异动",
        symbol=symbol
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": symbol
        }
    
    return api_result


def get_stock_board_change_em() -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情
    
    接口: akshare.stock_board_change_em
    目标地址: 东方财富网站
    描述: 获取东方财富当日板块异动详情数据
    
    Returns:
        统一格式的响应字典: {"success": bool, "data": List[Dict[str, Any]] | None, "error": str | None, "symbol": "board_change"}
    """
    # 调用标准化的AKShare API
    api_result = call_akshare_api(
        api_func=ak.stock_board_change_em,
        context="东方财富板块异动"
    )
    
    # 检查调用是否成功
    if not api_result.get("success", False):
        # 如果调用失败，返回失败格式
        return {
            "success": False,
            "data": None,
            "error": api_result.get("error", "查询失败"),
            "symbol": "board_change"
        }
    
    return api_result
