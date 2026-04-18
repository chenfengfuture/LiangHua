# -*- coding: utf-8 -*-
"""
板块概念模块 - 服务层封装

本模块提供板块概念相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供板块概念数据查询服务，包括概念板块指数、行业一览表、概念板块简介、行业板块指数等。

接口数量：9个
接口分类：
1.  get_stock_board_concept_index_ths_service() - 查询同花顺概念板块指数
2.  get_stock_board_industry_summary_ths_service() - 查询同花顺行业一览表
3.  get_stock_board_concept_info_ths_service() - 查询同花顺概念板块简介
4.  get_stock_board_industry_index_ths_service() - 查询同花顺行业板块指数
5.  get_stock_hot_follow_xq_service() - 查询雪球关注排行榜
6.  get_stock_hot_rank_detail_em_service() - 查询东方财富股票热度
7.  get_stock_hot_keyword_em_service() - 查询东方财富个股人气榜关键词
8.  get_stock_changes_em_service() - 查询东方财富盘口异动
9.  get_stock_board_change_em_service() - 查询东方财富当日板块异动

API路由地址：
- GET  /api/stock/board/concept_index           # 同花顺概念板块指数
- GET  /api/stock/board/industry_summary        # 同花顺行业一览表
- GET  /api/stock/board/concept_info            # 同花顺概念板块简介
- GET  /api/stock/board/industry_index          # 同花顺行业板块指数
- GET  /api/stock/hot/follow                    # 雪球关注排行榜
- GET  /api/stock/hot/rank                      # 东方财富股票热度
- GET  /api/stock/{symbol}/hot/keyword          # 东方财富个股人气榜关键词
- GET  /api/stock/changes                       # 东方财富盘口异动
- GET  /api/stock/board/change                  # 东方财富当日板块异动

数据来源：同花顺（ths）、雪球（xq）、东方财富（em）接口
数据特点：
1. 概念板块：包含概念板块指数、简介、成分股等信息
2. 行业板块：包含行业板块指数、行业一览表等信息
3. 热度排名：包含股票关注度、人气榜、关键词等热度数据
4. 盘口异动：包含个股盘口异动、板块异动等实时数据

返回格式：
{
    "success": bool,      # 查询是否成功
    "data": any,          # 查询结果数据
    "error": str | None,  # 错误信息（成功时为None）
    "symbol": str         # 查询的股票代码或标识
}

版本：1.0.0
创建时间：2026-04-17
"""

import logging
import traceback
from typing import Any, Dict

from stock_services.unity import (
    get_stock_board_change_em,
    get_stock_board_concept_index_ths,
    get_stock_board_concept_info_ths,
    get_stock_board_industry_index_ths,
    get_stock_board_industry_summary_ths,
    get_stock_changes_em,
    get_stock_hot_follow_xq,
    get_stock_hot_keyword_em,
    get_stock_hot_rank_detail_em,
)

logger = logging.getLogger(__name__)


def get_stock_board_concept_index_ths_service(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询同花顺概念板块指数日频率数据 - 服务层封装
    
    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"
        start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺概念板块指数 symbol={symbol}, start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_board_concept_index_ths(symbol, start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺概念板块指数查询失败")
            logger.error(f"[股票Unity服务] 同花顺概念板块指数查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺概念板块指数查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺概念板块指数查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_board_industry_summary_ths_service() -> Dict[str, Any]:
    """
    查询同花顺行业一览表 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺行业一览表")
    
    try:
        # 调用底层unity接口
        result = get_stock_board_industry_summary_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺行业一览表查询失败")
            logger.error(f"[股票Unity服务] 同花顺行业一览表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}
        
        logger.info(f"[股票Unity服务] 同花顺行业一览表查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺行业一览表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}


def get_stock_board_concept_info_ths_service(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介 - 服务层封装
    
    Args:
        symbol: 概念板块名称，如 "阿里巴巴概念"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺概念板块简介 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_board_concept_info_ths(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺概念板块简介查询失败")
            logger.error(f"[股票Unity服务] 同花顺概念板块简介查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺概念板块简介查询成功")
        return result
        
    except Exception as e:
        error_msg = f"同花顺概念板块简介查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_board_industry_index_ths_service(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据 - 服务层封装
    
    Args:
        symbol: 行业板块名称，如 "元件"
        start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺行业板块指数 symbol={symbol}, start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_board_industry_index_ths(symbol, start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺行业板块指数查询失败")
            logger.error(f"[股票Unity服务] 同花顺行业板块指数查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺行业板块指数查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺行业板块指数查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_hot_follow_xq_service(symbol: str) -> Dict[str, Any]:
    """
    查询雪球关注排行榜 - 服务层封装
    
    Args:
        symbol: 排行榜类型，choice of {"本周新增", "最热门"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询雪球关注排行榜 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_hot_follow_xq(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "雪球关注排行榜查询失败")
            logger.error(f"[股票Unity服务] 雪球关注排行榜查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 雪球关注排行榜查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"雪球关注排行榜查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_hot_rank_detail_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富股票热度历史趋势及粉丝特征 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富股票热度 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_hot_rank_detail_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富股票热度查询失败")
            logger.error(f"[股票Unity服务] 东方财富股票热度查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富股票热度查询成功")
        return result
        
    except Exception as e:
        error_msg = f"东方财富股票热度查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_hot_keyword_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "SZ000665"（需带市场前缀）
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富个股人气榜热门关键词 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_hot_keyword_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富个股人气榜热门关键词查询失败")
            logger.error(f"[股票Unity服务] 东方财富个股人气榜热门关键词查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富个股人气榜热门关键词查询成功")
        return result
        
    except Exception as e:
        error_msg = f"东方财富个股人气榜热门关键词查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_changes_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据 - 服务层封装
    
    Args:
        symbol: 异动类型，choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富盘口异动数据 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_changes_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富盘口异动查询失败")
            logger.error(f"[股票Unity服务] 东方财富盘口异动查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富盘口异动查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富盘口异动查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_board_change_em_service() -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富当日板块异动详情")
    
    try:
        # 调用底层unity接口
        result = get_stock_board_change_em()
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富当日板块异动查询失败")
            logger.error(f"[股票Unity服务] 东方财富当日板块异动查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}
        
        logger.info(f"[股票Unity服务] 东方财富当日板块异动查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富当日板块异动查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}