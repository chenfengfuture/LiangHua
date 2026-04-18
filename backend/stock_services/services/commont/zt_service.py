# -*- coding: utf-8 -*-
"""
涨跌停模块 - 服务层封装

本模块提供涨跌停相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供涨跌停数据查询服务，包括涨停股池、昨日涨停股池、强势股池、炸板股池、跌停股池等。

接口数量：5个
接口分类：
1.  get_stock_zt_pool_em_service() - 查询涨停股池数据
2.  get_stock_zt_pool_previous_em_service() - 查询昨日涨停股池
3.  get_stock_zt_pool_strong_em_service() - 查询强势股池数据
4.  get_stock_zt_pool_zbgc_em_service() - 查询炸板股池数据
5.  get_stock_zt_pool_dtgc_em_service() - 查询跌停股池数据

API路由地址：
- GET  /api/stock/zt/pool/{date}               # 涨停股池数据
- GET  /api/stock/zt/previous/{date}           # 昨日涨停股池
- GET  /api/stock/zt/strong/{date}             # 强势股池数据
- GET  /api/stock/zt/zbgc/{date}               # 炸板股池数据
- GET  /api/stock/zt/dtgc/{date}               # 跌停股池数据

数据来源：东方财富（em）接口
数据特点：
1. 涨停股池：包含当日涨停个股的详细信息
2. 昨日涨停：包含昨日涨停个股的后续表现
3. 强势股池：包含连续上涨的强势个股
4. 炸板股池：包含涨停后开板的个股
5. 跌停股池：包含当日跌停个股的详细信息

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
    get_stock_zt_pool_em,
    get_stock_zt_pool_previous_em,
    get_stock_zt_pool_strong_em,
    get_stock_zt_pool_zbgc_em,
    get_stock_zt_pool_dtgc_em,
)

logger = logging.getLogger(__name__)


def get_stock_zt_pool_em_service(date: str) -> Dict[str, Any]:
    """
    查询东方财富涨停股池数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富涨停股池数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zt_pool_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富涨停股池查询失败")
            logger.error(f"[股票Unity服务] 东方财富涨停股池查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool"}
        
        logger.info(f"[股票Unity服务] 东方财富涨停股池查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富涨停股池查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool"}


def get_stock_zt_pool_previous_em_service(date: str) -> Dict[str, Any]:
    """
    查询东方财富昨日涨停股池数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富昨日涨停股池数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zt_pool_previous_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富昨日涨停股池查询失败")
            logger.error(f"[股票Unity服务] 东方财富昨日涨停股池查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_previous"}
        
        logger.info(f"[股票Unity服务] 东方财富昨日涨停股池查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富昨日涨停股池查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_previous"}


def get_stock_zt_pool_strong_em_service(date: str) -> Dict[str, Any]:
    """
    查询东方财富强势股池数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富强势股池数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zt_pool_strong_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富强势股池查询失败")
            logger.error(f"[股票Unity服务] 东方财富强势股池查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_strong"}
        
        logger.info(f"[股票Unity服务] 东方财富强势股池查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富强势股池查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_strong"}


def get_stock_zt_pool_zbgc_em_service(date: str) -> Dict[str, Any]:
    """
    查询东方财富炸板股池数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富炸板股池数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zt_pool_zbgc_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富炸板股池查询失败")
            logger.error(f"[股票Unity服务] 东方财富炸板股池查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_zbgc"}
        
        logger.info(f"[股票Unity服务] 东方财富炸板股池查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富炸板股池查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_zbgc"}


def get_stock_zt_pool_dtgc_em_service(date: str) -> Dict[str, Any]:
    """
    查询东方财富跌停股池数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富跌停股池数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zt_pool_dtgc_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富跌停股池查询失败")
            logger.error(f"[股票Unity服务] 东方财富跌停股池查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_dtgc"}
        
        logger.info(f"[股票Unity服务] 东方财富跌停股池查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富跌停股池查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_dtgc"}