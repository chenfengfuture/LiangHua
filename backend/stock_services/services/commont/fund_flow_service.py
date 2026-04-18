# -*- coding: utf-8 -*-
"""
资金流向模块 - 服务层封装

本模块提供资金流向相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供资金流向数据查询服务，包括个股资金流、概念资金流、资金流向排名、大盘资金流向等。

接口数量：8个
接口分类：
1.  get_stock_fund_flow_individual_service() - 查询同花顺个股资金流
2.  get_stock_fund_flow_concept_service() - 查询同花顺概念资金流
3.  get_stock_individual_fund_flow_service() - 查询东方财富个股资金流向
4.  get_stock_individual_fund_flow_rank_service() - 查询东方财富资金流向排名
5.  get_stock_market_fund_flow_service() - 查询东方财富大盘资金流向
6.  get_stock_sector_fund_flow_rank_service() - 查询东方财富板块资金流排名
7.  get_stock_sector_fund_flow_summary_service() - 查询东方财富行业个股资金流
8.  get_stock_main_fund_flow_service() - 查询东方财富主力净流入排名

API路由地址：
- GET  /api/stock/{symbol}/fund_flow/individual    # 同花顺个股资金流
- GET  /api/stock/fund_flow/concept/{concept_code} # 同花顺概念资金流
- GET  /api/stock/{symbol}/fund_flow               # 东方财富个股资金流向
- GET  /api/stock/fund_flow/rank                   # 东方财富资金流向排名
- GET  /api/stock/fund_flow/market                 # 东方财富大盘资金流向
- GET  /api/stock/fund_flow/sector_rank            # 东方财富板块资金流排名
- GET  /api/stock/fund_flow/sector_summary         # 东方财富行业个股资金流
- GET  /api/stock/fund_flow/main                   # 东方财富主力净流入排名

数据来源：同花顺（ths）、东方财富（em）接口
数据特点：
1. 个股资金流：包含个股主力资金、散户资金、机构资金流向
2. 概念资金流：包含概念板块的资金流向
3. 资金排名：包含资金流入流出排名数据
4. 大盘资金：包含大盘资金流向数据
5. 板块资金：包含板块资金流向排名
6. 主力资金：包含主力资金净流入排名

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
    get_stock_fund_flow_individual,
    get_stock_fund_flow_concept,
    get_stock_individual_fund_flow,
    get_stock_individual_fund_flow_rank,
    get_stock_market_fund_flow,
    get_stock_sector_fund_flow_rank,
    get_stock_sector_fund_flow_summary,
    get_stock_main_fund_flow,
)

logger = logging.getLogger(__name__)


def get_stock_fund_flow_individual_service(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-个股资金流 - 服务层封装
    
    Args:
        symbol: 时间范围，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺个股资金流 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_fund_flow_individual(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺个股资金流查询失败")
            logger.error(f"[股票Unity服务] 同花顺个股资金流查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺个股资金流查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺个股资金流查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_fund_flow_concept_service(symbol: str) -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-概念资金流 - 服务层封装
    
    Args:
        symbol: 时间范围，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺概念资金流 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_fund_flow_concept(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺概念资金流查询失败")
            logger.error(f"[股票Unity服务] 同花顺概念资金流查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺概念资金流查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"同花顺概念资金流查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_individual_fund_flow_service(stock: str, market: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-个股资金流向（近100交易日） - 服务层封装
    
    Args:
        stock: 股票代码，如 "000425"
        market: 市场类型，choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富个股资金流向 stock={stock}, market={market}")
    
    try:
        # 调用底层unity接口
        result = get_stock_individual_fund_flow(stock, market)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富个股资金流向查询失败")
            logger.error(f"[股票Unity服务] 东方财富个股资金流向查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": stock}
        
        logger.info(f"[股票Unity服务] 东方财富个股资金流向查询成功")
        return result
        
    except Exception as e:
        error_msg = f"东方财富个股资金流向查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": stock}


def get_stock_individual_fund_flow_rank_service(indicator: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-资金流向排名 - 服务层封装
    
    Args:
        indicator: 时间范围，choice of {"今日", "3日", "5日", "10日"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富资金流向排名 indicator={indicator}")
    
    try:
        # 调用底层unity接口
        result = get_stock_individual_fund_flow_rank(indicator)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富资金流向排名查询失败")
            logger.error(f"[股票Unity服务] 东方财富资金流向排名查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": indicator}
        
        logger.info(f"[股票Unity服务] 东方财富资金流向排名查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富资金流向排名查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": indicator}


def get_stock_market_fund_flow_service() -> Dict[str, Any]:
    """
    查询东方财富-数据中心-大盘资金流向 - 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富大盘资金流向")
    
    try:
        # 调用底层unity接口
        result = get_stock_market_fund_flow()
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富大盘资金流向查询失败")
            logger.error(f"[股票Unity服务] 东方财富大盘资金流向查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "market_fund_flow"}
        
        logger.info(f"[股票Unity服务] 东方财富大盘资金流向查询成功")
        return result
        
    except Exception as e:
        error_msg = f"东方财富大盘资金流向查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "market_fund_flow"}


def get_stock_sector_fund_flow_rank_service(indicator: str, sector_type: str) -> Dict[str, Any]:
    """
    查询东方财富+数据中心+板块资金流排名 - 服务层封装
    
    Args:
        indicator: 时间范围，choice of {"今日", "5日", "10日"}
        sector_type: 板块类型，choice of {"行业资金流", "概念资金流", "地域资金流"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富板块资金流排名 indicator={indicator}, sector_type={sector_type}")
    
    try:
        # 调用底层unity接口
        result = get_stock_sector_fund_flow_rank(indicator, sector_type)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富板块资金流排名查询失败")
            logger.error(f"[股票Unity服务] 东方财富板块资金流排名查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": f"{indicator}_{sector_type}"}
        
        logger.info(f"[股票Unity服务] 东方财富板块资金流排名查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富板块资金流排名查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": f"{indicator}_{sector_type}"}


def get_stock_sector_fund_flow_summary_service(symbol: str, indicator: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-行业个股资金流 - 服务层封装
    
    Args:
        symbol: 行业板块名称，如 "电源设备"
        indicator: 时间范围，choice of {"今日", "5日", "10日"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富行业个股资金流 symbol={symbol}, indicator={indicator}")
    
    try:
        # 调用底层unity接口
        result = get_stock_sector_fund_flow_summary(symbol, indicator)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富行业个股资金流查询失败")
            logger.error(f"[股票Unity服务] 东方财富行业个股资金流查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富行业个股资金流查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富行业个股资金流查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_main_fund_flow_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-主力净流入排名 - 服务层封装
    
    Args:
        symbol: 市场类型，choice of {"全部股票", "沪深A股", "沪市A股", "科创板", "深市A股", "创业板", "沪市B股", "深市B股"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富主力净流入排名 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_main_fund_flow(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富主力净流入排名查询失败")
            logger.error(f"[股票Unity服务] 东方财富主力净流入排名查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富主力净流入排名查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"东方财富主力净流入排名查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}