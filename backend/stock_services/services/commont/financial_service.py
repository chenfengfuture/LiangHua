# -*- coding: utf-8 -*-
"""
财务报表模块 - 服务层封装

本模块提供财务报表相关数据的服务层封装，调用底层unity接口，提供统一的错误处理和响应格式。

模块功能：提供财务报表数据查询服务，包括资产负债表、利润表、现金流量表、盈利预测等。

接口数量：6个
接口分类：
1.  get_stock_financial_report_sina_service() - 查询新浪财经财务报表
2.  get_stock_balance_sheet_by_yearly_em_service() - 查询东方财富资产负债表
3.  get_stock_profit_sheet_by_report_em_service() - 查询东方财富利润表（报告期）
4.  get_stock_profit_sheet_by_yearly_em_service() - 查询东方财富利润表（年度）
5.  get_stock_cash_flow_sheet_by_report_em_service() - 查询东方财富现金流量表
6.  get_stock_profit_forecast_ths_service() - 查询同花顺盈利预测

API路由地址：
- GET  /api/stock/{symbol}/financial_report/{date}     # 新浪财经财务报表
- GET  /api/stock/{symbol}/balance_sheet               # 东方财富资产负债表
- GET  /api/stock/{symbol}/profit_sheet/report         # 东方财富利润表（报告期）
- GET  /api/stock/{symbol}/profit_sheet/yearly         # 东方财富利润表（年度）
- GET  /api/stock/{symbol}/cash_flow                   # 东方财富现金流量表
- GET  /api/stock/{symbol}/profit_forecast             # 同花顺盈利预测

数据来源：
1. 新浪财经（sina）接口：提供资产负债表、利润表、现金流量表
2. 东方财富（em）接口：提供资产负债表、利润表、现金流量表
3. 同花顺（ths）接口：提供盈利预测数据

数据特点：
1. 资产负债表：包含资产、负债、所有者权益等科目
2. 利润表：包含营业收入、营业利润、净利润等科目
3. 现金流量表：包含经营活动、投资活动、筹资活动现金流量
4. 盈利预测：包含预测机构、预测值、预测日期等信息

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
    get_stock_balance_sheet_by_yearly_em,
    get_stock_cash_flow_sheet_by_report_em,
    get_stock_financial_report_sina,
    get_stock_profit_forecast_ths,
    get_stock_profit_sheet_by_report_em,
    get_stock_profit_sheet_by_yearly_em,
)

logger = logging.getLogger(__name__)


def get_stock_financial_report_sina_service(stock: str, symbol: str) -> Dict[str, Any]:
    """
    查询新浪财经财务报表 - 服务层封装
    
    Args:
        stock: 股票代码，如 "600519"
        symbol: 报表类型，choice of {"资产负债表", "利润表", "现金流量表"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询新浪财经财务报表 stock={stock}, symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_financial_report_sina(stock, symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "新浪财经财务报表查询失败")
            logger.error(f"[股票Unity服务] 新浪财经财务报表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": stock}
        
        logger.info(f"[股票Unity服务] 新浪财经财务报表查询成功 stock={stock}, type={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"新浪财经财务报表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": stock}


def get_stock_balance_sheet_by_yearly_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富资产负债表（按年度）- 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富资产负债表 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_balance_sheet_by_yearly_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富资产负债表查询失败")
            logger.error(f"[股票Unity服务] 东方财富资产负债表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富资产负债表查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"东方财富资产负债表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_profit_sheet_by_report_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富利润表（按报告期）- 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富利润表（报告期） symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_profit_sheet_by_report_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富利润表查询失败")
            logger.error(f"[股票Unity服务] 东方财富利润表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富利润表查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"东方财富利润表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_profit_sheet_by_yearly_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富利润表（按年度）- 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富利润表（年度） symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_profit_sheet_by_yearly_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富年度利润表查询失败")
            logger.error(f"[股票Unity服务] 东方财富年度利润表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富年度利润表查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"东方财富年度利润表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_cash_flow_sheet_by_report_em_service(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富现金流量表（按报告期）- 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询东方财富现金流量表 symbol={symbol}")
    
    try:
        # 调用底层unity接口
        result = get_stock_cash_flow_sheet_by_report_em(symbol)
        
        if not result.get("success", False):
            error_msg = result.get("error", "东方财富现金流量表查询失败")
            logger.error(f"[股票Unity服务] 东方财富现金流量表查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 东方财富现金流量表查询成功 symbol={symbol}")
        return result
        
    except Exception as e:
        error_msg = f"东方财富现金流量表查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}


def get_stock_profit_forecast_ths_service(symbol: str, indicator: str) -> Dict[str, Any]:
    """
    查询同花顺盈利预测数据 - 服务层封装
    
    Args:
        symbol: 股票代码，如 "000001" 或 "000001.SZ"
        indicator: 预测类型，choice of {"预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", "业绩预测详表-详细指标预测"}
        
    Returns:
        统一格式的响应数据
    """
    logger.info(f"[股票Unity服务] 开始查询同花顺盈利预测数据 symbol={symbol}, indicator={indicator}")
    
    try:
        # 调用底层unity接口
        result = get_stock_profit_forecast_ths(symbol, indicator)
        
        if not result.get("success", False):
            error_msg = result.get("error", "同花顺盈利预测查询失败")
            logger.error(f"[股票Unity服务] 同花顺盈利预测查询失败: {error_msg}")
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
        
        logger.info(f"[股票Unity服务] 同花顺盈利预测查询成功 symbol={symbol}, indicator={indicator}")
        return result
        
    except Exception as e:
        error_msg = f"同花顺盈利预测查询失败: {str(e)}"
        logger.error(f"[股票Unity服务] {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "data": None, "error": error_msg, "symbol": symbol}