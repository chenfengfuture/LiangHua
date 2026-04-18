# -*- coding: utf-8 -*-
"""
股权质押模块 - 服务层封装

本模块提供股权质押相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供股权质押市场数据查询服务，包括市场概况、上市公司质押比例、个股质押明细、行业质押汇总等。

接口数量：4个
接口分类：
1.  get_stock_gpzy_profile_em_service() - 查询股权质押市场概况（全量历史）
2.  get_stock_gpzy_pledge_ratio_em_service() - 查询指定交易日上市公司质押比例
3.  get_stock_gpzy_individual_pledge_ratio_detail_em_service() - 查询个股重要股东股权质押明细（全量历史）
4.  get_stock_gpzy_industry_data_em_service() - 查询各行业质押比例汇总数据（全量）

API路由地址：
- GET  /api/stock/gpzy/profile                              # 股权质押市场概况
- GET  /api/stock/gpzy/pledge_ratio?date=YYYY-MM-DD         # 上市公司质押比例
- GET  /api/stock/{symbol}/gpzy_detail                      # 个股股权质押明细
- GET  /api/stock/gpzy/industry                             # 行业质押比例汇总

数据来源：东方财富（gpzy_em）接口
数据特点：
1. 市场概况：包含全市场质押总股数、质押总市值、质押率等历史数据
2. 公司质押：按交易日统计的上市公司质押比例排名
3. 个股明细：具体到每个重要股东的质押明细、质押数量、质押率等
4. 行业汇总：按行业统计的质押比例、质押公司数量等数据

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
    get_stock_gpzy_individual_pledge_ratio_detail_em,
    get_stock_gpzy_industry_data_em,
    get_stock_gpzy_pledge_ratio_em,
    get_stock_gpzy_profile_em,
)

logger = logging.getLogger(__name__)


def get_stock_gpzy_profile_em_service() -> Dict[str, Any]:
    """
    查询股权质押市场概况（全量历史）- 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询股权质押市场概况")
    
    try:
        # 调用底层unity接口
        result = get_stock_gpzy_profile_em()
        
        if not result.get("success", False):
            error_msg = result.get("error", "股权质押市场概况查询失败")
            logger.error(f"[股票Unity服务] 股权质押市场概况查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_profile"}
        
        logger.info(f"[股票Unity服务] 股权质押市场概况查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"股权质押市场概况查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_profile"}


def get_stock_gpzy_pledge_ratio_em_service(date: str) -> Dict[str, Any]:
    """
    查询指定交易日上市公司质押比例 - 服务层封装
    
    Args:
        date: 交易日，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询上市公司质押比例 date={date}")
    
    try:
        # 调用底层unity接口
        result = get_stock_gpzy_pledge_ratio_em(date)
        
        if not result.get("success", False):
            error_msg = result.get("error", "上市公司质押比例查询失败")
            logger.error(f"[股票Unity服务] 上市公司质押比例查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_pledge_ratio"}
        
        logger.info(f"[股票Unity服务] 上市公司质押比例查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"上市公司质押比例查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_pledge_ratio"}


def get_stock_gpzy_individual_pledge_ratio_detail_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询个股重要股东股权质押明细（全量历史）- 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询个股股权质押明细 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_gpzy_individual_pledge_ratio_detail_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "个股股权质押明细查询失败")
            logger.error(f"[股票Unity服务] 个股股权质押明细查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 个股股权质押明细查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"个股股权质押明细查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_gpzy_industry_data_em_service() -> Dict[str, Any]:
    """
    查询各行业质押比例汇总数据（全量）- 服务层封装
    
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询各行业质押比例汇总数据")
    
    try:
        # 调用底层unity接口
        result = get_stock_gpzy_industry_data_em()
        
        if not result.get("success", False):
            error_msg = result.get("error", "行业质押比例汇总查询失败")
            logger.error(f"[股票Unity服务] 行业质押比例汇总查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_industry"}
        
        logger.info(f"[股票Unity服务] 行业质押比例汇总查询成功，共 {len(result.get('data', []))} 条记录")
        return result
        
    except Exception as e:
        error_msg = f"行业质押比例汇总查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_industry"}