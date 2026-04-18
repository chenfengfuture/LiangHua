# -*- coding: utf-8 -*-
"""
股东数据模块 - 服务层封装

本模块提供股东相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供股东数据查询服务，包括股东户数、千股千评、用户关注指数、市场参与意愿等。

接口数量：6个
接口分类：
1.  get_stock_account_statistics_em_service() - 查询月度股票账户统计
2.  get_stock_comment_em_service() - 查询千股千评数据
3.  get_stock_comment_detail_scrd_focus_em_service() - 查询用户关注指数
4.  get_stock_comment_detail_scrd_desire_em_service() - 查询市场参与意愿
5.  get_stock_zh_a_gdhs_service() - 查询全市场股东户数
6.  get_stock_zh_a_gdhs_detail_em_service() - 查询个股股东户数详情

API路由地址：
- GET  /api/stock/account/statistics              # 月度股票账户统计
- GET  /api/stock/comment                         # 千股千评数据
- GET  /api/stock/{symbol}/comment/focus          # 用户关注指数
- GET  /api/stock/{symbol}/comment/desire         # 市场参与意愿
- GET  /api/stock/gdhs/all                        # 全市场股东户数
- GET  /api/stock/{symbol}/gdhs/detail            # 个股股东户数详情

数据来源：东方财富（em）接口
数据特点：
1. 股东户数：包含全市场和个股的股东户数变化
2. 千股千评：包含股票评分、评级、关注度等数据
3. 关注指数：反映用户对个股的关注程度
4. 参与意愿：反映市场参与交易的意愿强度

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
    get_stock_account_statistics_em,
    get_stock_comment_detail_scrd_desire_em,
    get_stock_comment_detail_scrd_focus_em,
    get_stock_comment_em,
    get_stock_zh_a_gdhs,
    get_stock_zh_a_gdhs_detail_em,
)

logger = logging.getLogger(__name__)


def get_stock_account_statistics_em_service() -> Dict[str, Any]:
    """
    查询月度股票账户统计数据（201504 起全量）- 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询月度股票账户统计数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_account_statistics_em()
        
        if not result.get("success", False):
            error_msg = result.get("error", "月度股票账户统计查询失败")
            logger.error(f"[股票Unity服务] 月度股票账户统计查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "account_statistics"}
        
        logger.info(f"[股票Unity服务] 月度股票账户统计查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"月度股票账户统计查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "account_statistics"}


def get_stock_comment_em_service() -> Dict[str, Any]:
    """
    查询千股千评数据（全部股票当日评分）- 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询千股千评数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_comment_em()
        
        if not result.get("success", False):
            error_msg = result.get("error", "千股千评数据查询失败")
            logger.error(f"[股票Unity服务] 千股千评数据查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "stock_comment"}
        
        logger.info(f"[股票Unity服务] 千股千评数据查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"千股千评数据查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "stock_comment"}


def get_stock_comment_detail_scrd_focus_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询千股千评-用户关注指数 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询千股千评用户关注指数 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_comment_detail_scrd_focus_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "千股千评用户关注指数查询失败")
            logger.error(f"[股票Unity服务] 千股千评用户关注指数查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 千股千评用户关注指数查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"千股千评用户关注指数查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_comment_detail_scrd_desire_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询千股千评-市场参与意愿 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询千股千评市场参与意愿 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_comment_detail_scrd_desire_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "千股千评市场参与意愿查询失败")
            logger.error(f"[股票Unity服务] 千股千评市场参与意愿查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 千股千评市场参与意愿查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"千股千评市场参与意愿查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_zh_a_gdhs_service(date: str) -> Dict[str, Any]:
    """
    查询全市场股东户数数据 - 服务层封装
    
    Args:
        date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询全市场股东户数数据 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zh_a_gdhs(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "全市场股东户数查询失败")
            logger.error(f"[股票Unity服务] 全市场股东户数查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "gdhs"}
        
        logger.info(f"[股票Unity服务] 全市场股东户数查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"全市场股东户数查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "gdhs"}


def get_stock_zh_a_gdhs_detail_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询个股股东户数详情 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询个股股东户数详情 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_zh_a_gdhs_detail_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "个股股东户数详情查询失败")
            logger.error(f"[股票Unity服务] 个股股东户数详情查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 个股股东户数详情查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"个股股东户数详情查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}