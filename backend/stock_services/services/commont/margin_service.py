# -*- coding: utf-8 -*-
"""
融资融券模块 - 服务层封装

本模块提供融资融券相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供融资融券数据查询服务，包括两融账户信息、上交所融资融券汇总、深交所融资融券明细等。

接口数量：4个
接口分类：
1.  get_stock_margin_account_info_service() - 查询两融账户信息
2.  get_stock_margin_sse_service() - 查询上交所融资融券汇总
3.  get_stock_margin_detail_szse_service() - 查询深交所融资融券明细
4.  get_stock_margin_detail_sse_service() - 查询上交所融资融券明细

API路由地址：
- GET  /api/stock/margin/account                # 两融账户信息
- GET  /api/stock/margin/sse                    # 上交所融资融券汇总
- GET  /api/stock/margin/szse_detail            # 深交所融资融券明细
- GET  /api/stock/margin/sse_detail             # 上交所融资融券明细

数据来源：东方财富（em）接口、交易所官方数据
数据特点：
1. 两融账户：包含融资融券账户数量、余额等统计信息
2. 上交所汇总：包含上交所融资买入额、融券卖出额等汇总数据
3. 深交所明细：包含深交所个股融资融券明细数据
4. 上交所明细：包含上交所个股融资融券明细数据

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
    get_stock_margin_account_info,
    get_stock_margin_detail_sse,
    get_stock_margin_detail_szse,
    get_stock_margin_sse,
)

logger = logging.getLogger(__name__)


def get_stock_margin_account_info_service() -> Dict[str, Any]:
    """
    查询两融账户信息（东方财富）- 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询两融账户信息")
    
    try:
        # 调用底层unity接口
        result = get_stock_margin_account_info()
        
        if not result.get("success", False):
            error_msg = result.get("error", "两融账户信息查询失败")
            logger.error(f"[股票Unity服务] 两融账户信息查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_account"}
        
        logger.info(f"[股票Unity服务] 两融账户信息查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"两融账户信息查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "margin_account"}


def get_stock_margin_sse_service(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    查询上交所融资融券汇总数据 - 服务层封装
    
    Args:
        start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询上交所融资融券汇总数据 start_date={start_date}, end_date={end_date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_margin_sse(start_date, end_date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "上交所融资融券汇总查询失败")
            logger.error(f"[股票Unity服务] 上交所融资融券汇总查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_sse"}
        
        logger.info(f"[股票Unity服务] 上交所融资融券汇总查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"上交所融资融券汇总查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "margin_sse"}


def get_stock_margin_detail_szse_service(date: str) -> Dict[str, Any]:
    """
    查询深交所融资融券明细数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询深交所融资融券明细数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_margin_detail_szse(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "深交所融资融券明细查询失败")
            logger.error(f"[股票Unity服务] 深交所融资融券明细查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_szse"}
        
        logger.info(f"[股票Unity服务] 深交所融资融券明细查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"深交所融资融券明细查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_szse"}


def get_stock_margin_detail_sse_service(date: str) -> Dict[str, Any]:
    """
    查询上交所融资融券明细数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询上交所融资融券明细数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_margin_detail_sse(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "上交所融资融券明细查询失败")
            logger.error(f"[股票Unity服务] 上交所融资融券明细查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_sse"}
        
        logger.info(f"[股票Unity服务] 上交所融资融券明细查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"上交所融资融券明细查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_sse"}