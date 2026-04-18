# -*- coding: utf-8 -*-
"""
龙虎榜模块 - 服务层封装

本模块提供龙虎榜相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供龙虎榜数据查询服务，包括机构买卖统计、龙虎榜详情、个股上榜统计、活跃营业部等。

接口数量：5个
接口分类：
1.  get_stock_lhb_jgmmtj_em_service() - 查询龙虎榜机构买卖统计
2.  get_stock_lhb_detail_em_service() - 查询龙虎榜详情数据
3.  get_stock_lhb_stock_statistic_em_service() - 查询个股上榜统计
4.  get_stock_lhb_hyyyb_em_service() - 查询每日活跃营业部
5.  get_stock_lhb_yyb_detail_em_service() - 查询营业部历史交易明细

API路由地址：
- GET  /api/stock/lhb/institution                # 龙虎榜机构买卖统计
- GET  /api/stock/lhb/detail/{date}              # 龙虎榜详情数据
- GET  /api/stock/{symbol}/lhb/statistic         # 个股上榜统计
- GET  /api/stock/lhb/active/{date}              # 每日活跃营业部
- GET  /api/stock/{symbol}/lhb/yyb_detail        # 营业部历史交易明细

数据来源：东方财富（em）接口
数据特点：
1. 机构买卖：统计机构席位在龙虎榜上的买卖情况
2. 龙虎榜详情：包含上榜个股、买卖席位、买卖金额等详细信息
3. 个股上榜：统计个股在龙虎榜上的上榜次数、买卖金额等
4. 活跃营业部：统计每日交易最活跃的营业部

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
    get_stock_lhb_detail_em,
    get_stock_lhb_hyyyb_em,
    get_stock_lhb_jgmmtj_em,
    get_stock_lhb_stock_statistic_em,
    get_stock_lhb_yyb_detail_em,
)

logger = logging.getLogger(__name__)


def get_stock_lhb_jgmmtj_em_service(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询龙虎榜机构买卖每日统计 - 服务层封装
    
    Args:
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询龙虎榜机构买卖统计 start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_lhb_jgmmtj_em(start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "龙虎榜机构买卖统计查询失败")
            logger.error(f"[股票Unity服务] 龙虎榜机构买卖统计查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "jgmmtj"}
        
        logger.info(f"[股票Unity服务] 龙虎榜机构买卖统计查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"龙虎榜机构买卖统计查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "jgmmtj"}


def get_stock_lhb_detail_em_service(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询龙虎榜详情数据 - 服务层封装
    
    Args:
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询龙虎榜详情 start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_lhb_detail_em(start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "龙虎榜详情查询失败")
            logger.error(f"[股票Unity服务] 龙虎榜详情查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_detail"}
        
        logger.info(f"[股票Unity服务] 龙虎榜详情查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"龙虎榜详情查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_detail"}


def get_stock_lhb_stock_statistic_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询个股上榜统计数据 - 服务层封装
    
    Args:
        symbol: 时间范围，choice of {"近一月", "近三月", "近六月", "近一年"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询个股上榜统计 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_lhb_stock_statistic_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "个股上榜统计查询失败")
            logger.error(f"[股票Unity服务] 个股上榜统计查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_stock_statistic"}
        
        logger.info(f"[股票Unity服务] 个股上榜统计查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"个股上榜统计查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_stock_statistic"}


def get_stock_lhb_hyyyb_em_service(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询每日活跃营业部数据 - 服务层封装
    
    Args:
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询每日活跃营业部数据 start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_lhb_hyyyb_em(start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "每日活跃营业部查询失败")
            logger.error(f"[股票Unity服务] 每日活跃营业部查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_hyyyb"}
        
        logger.info(f"[股票Unity服务] 每日活跃营业部查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"每日活跃营业部查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_hyyyb"}


def get_stock_lhb_yyb_detail_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询营业部历史交易明细 - 服务层封装
    
    Args:
        symbol: 营业部代码，如 "10026729"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询营业部历史交易明细 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_lhb_yyb_detail_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "营业部历史交易明细查询失败")
            logger.error(f"[股票Unity服务] 营业部历史交易明细查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 营业部历史交易明细查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"营业部历史交易明细查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}