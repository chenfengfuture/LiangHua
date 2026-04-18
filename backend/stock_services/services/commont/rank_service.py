# -*- coding: utf-8 -*-
"""
技术选股排名模块 - 服务层封装

本模块提供技术选股排名相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供技术选股排名数据查询服务，包括创新高、连续上涨、持续放量、向上突破等技术指标排名。

接口数量：8个
接口分类：
1.  get_stock_rank_cxg_ths_service() - 查询创新高数据
2.  get_stock_rank_lxsz_ths_service() - 查询连续上涨数据
3.  get_stock_rank_cxfl_ths_service() - 查询持续放量数据
4.  get_stock_rank_cxsl_ths_service() - 查询持续缩量数据
5.  get_stock_rank_xstp_ths_service() - 查询向上突破数据
6.  get_stock_rank_ljqs_ths_service() - 查询量价齐升数据
7.  get_stock_rank_ljqd_ths_service() - 查询量价齐跌数据
8.  get_stock_rank_xzjp_ths_service() - 查询险资举牌数据

API路由地址：
- GET  /api/stock/rank/cxg                    # 创新高数据
- GET  /api/stock/rank/lxsz                   # 连续上涨数据
- GET  /api/stock/rank/cxfl                   # 持续放量数据
- GET  /api/stock/rank/cxsl                   # 持续缩量数据
- GET  /api/stock/rank/xstp                   # 向上突破数据
- GET  /api/stock/rank/ljqs                   # 量价齐升数据
- GET  /api/stock/rank/ljqd                   # 量价齐跌数据
- GET  /api/stock/rank/xzjp                   # 险资举牌数据

数据来源：同花顺（ths）接口
数据特点：
1. 创新高：包含创近期新高的个股
2. 连续上涨：包含连续上涨的个股
3. 持续放量：包含持续放量的个股
4. 持续缩量：包含持续缩量的个股
5. 向上突破：包含向上突破的个股
6. 量价齐升：包含量价齐升的个股
7. 量价齐跌：包含量价齐跌的个股
8. 险资举牌：包含险资举牌的个股

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
    get_stock_rank_cxg_ths,
    get_stock_rank_lxsz_ths,
    get_stock_rank_cxfl_ths,
    get_stock_rank_cxsl_ths,
    get_stock_rank_xstp_ths,
    get_stock_rank_ljqs_ths,
    get_stock_rank_ljqd_ths,
    get_stock_rank_xzjp_ths,
)

logger = logging.getLogger(__name__)


def get_stock_rank_cxg_ths_service(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺技术指标-创新高数据 - 服务层封装
    
    Args:
        symbol: 创新高类型，choice of {"创月新高", "半年新高", "一年新高", "历史新高"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺创新高数据 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_cxg_ths(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺创新高数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺创新高数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺创新高数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺创新高数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_rank_lxsz_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-连续上涨数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺连续上涨数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_lxsz_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺连续上涨数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺连续上涨数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "lxsz"}
        
        logger.info(f"[股票Unity服务] 同花顺连续上涨数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺连续上涨数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "lxsz"}


def get_stock_rank_cxfl_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续放量数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺持续放量数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_cxfl_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺持续放量数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺持续放量数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "cxfl"}
        
        logger.info(f"[股票Unity服务] 同花顺持续放量数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺持续放量数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "cxfl"}


def get_stock_rank_cxsl_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续缩量数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺持续缩量数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_cxsl_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺持续缩量数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺持续缩量数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "cxsl"}
        
        logger.info(f"[股票Unity服务] 同花顺持续缩量数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺持续缩量数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "cxsl"}


def get_stock_rank_xstp_ths_service(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺技术选股-向上突破数据 - 服务层封装
    
    Args:
        symbol: 均线类型，choice of {"5日均线", "10日均线", "20日均线", "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺向上突破数据 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_xstp_ths(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺向上突破数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺向上突破数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺向上突破数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺向上突破数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_rank_ljqs_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐升数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺量价齐升数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_ljqs_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺量价齐升数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺量价齐升数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "ljqs"}
        
        logger.info(f"[股票Unity服务] 同花顺量价齐升数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺量价齐升数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "ljqs"}


def get_stock_rank_ljqd_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐跌数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺量价齐跌数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_ljqd_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺量价齐跌数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺量价齐跌数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "ljqd"}
        
        logger.info(f"[股票Unity服务] 同花顺量价齐跌数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺量价齐跌数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "ljqd"}


def get_stock_rank_xzjp_ths_service() -> Dict[str, Any]:
    """
    查询同花顺技术选股-险资举牌数据 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺险资举牌数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_rank_xzjp_ths()
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺险资举牌数据查询失败")
            logger.error(f"[股票Unity服务] 同花顺险资举牌数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "xzjp"}
        
        logger.info(f"[股票Unity服务] 同花顺险资举牌数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺险资举牌数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "xzjp"}