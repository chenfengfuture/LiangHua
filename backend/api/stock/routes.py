#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票模块路由 - 简化版本
"""

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from utils.db import get_conn
from system_service.stock_service import get_stock_info_service, get_stock_llm_service, get_stock_lhb_service
from stock_services.services.stock_basic import stock_basic_service

router = APIRouter(prefix="/api/stock", tags=["stock"])


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：股票基础
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
def root() -> Dict[str, Any]:
    """根路径"""
    return {
        "success": True,
        "module": "stock",
        "message": "量华量化平台股票API运行中",
        "timestamp": datetime.now().isoformat()
    }




@router.get("/get-stock-info")
def get_stock_info(
        symbol: str = Query("603777", description="股票代码，如 603777、000001")
) -> Dict[str, Any]:
    result = stock_basic_service.get_stock_info_em(symbol)
    return result


@router.get("/get-stock-info-sh")
def get_sh_stocks(
        symbol: str = Query("主板A股", description="上交所板块类型，可选值：主板A股、主板B股、科创板，默认：主板A股")
) -> Dict[str, Any]:
    """查询上海证券交易所股票列表"""
    result = stock_basic_service.get_sh_stock_list(symbol)
    return result


@router.get("/get-stock-info-sz")
def get_sz_stocks(
        symbol: str = Query("A股列表", description="深交所列表类型，可选值：A股列表、B股列表、AB股列表、CDR列表，默认：A股列表")
) -> Dict[str, Any]:
    """查询深圳证券交易所股票列表"""
    result = stock_basic_service.get_sz_stock_list(symbol)
    return result


@router.get("/get-stock-info-bj")
def get_bj_stocks(
) -> Dict[str, Any]:
    """查询北京证券交易所股票列表（无参数，直接返回全量数据）"""
    result = stock_basic_service.get_bj_stock_list()
    return result


@router.get("/get-stock-info-sz-delist")
def get_sz_delist_stocks(
    symbol: str = Query("终止上市公司", description="深交所退市股票状态类型，可选值：终止上市公司、暂停上市公司，默认：终止上市公司")
) -> Dict[str, Any]:
    """查询深圳证券交易所终止/暂停上市股票"""
    result = stock_basic_service.get_stock_sz_delist(symbol)
    return result

@router.get("/get-stock-info-sh-delist")
def get_sh_delist_stocks(
    symbol: str = Query("全部", description="上交所退市股票市场范围，可选值：全部、沪市、科创板，默认：全部")
) -> Dict[str, Any]:
    """查询上海证券交易所暂停/终止上市股票"""
    result = stock_basic_service.get_stock_sh_delist(symbol)
    return result

@router.get("/get-stock-board-concept-index-ths")
def get_sh_delist_stocks(
    symbol: str = Query("全部", description="上交所退市股票市场范围，可选值：全部、沪市、科创板，默认：全部"),
    start_date: str = Query(datetime.now().strftime("%Y%m%d"), description="开始日期，格式为 YYYYMMDD，默认同结束日期"),
    end_date: str = Query(datetime.now().strftime("%Y%m%d"), description="结束日期，格式为 YYYYMMDD，默认今天"),
) -> Dict[str, Any]:
    """ 查询同花顺概念板块指数日频率数据 """
    result = stock_basic_service.get_stock_board_concept_index_ths_service(symbol, start_date, end_date)
    return result


@router.get("/get-stock-board")
def get_stock_board_industry_summary_ths_api(
) -> Dict[str, Any]:
    """ 查询同花顺行业一览表 """
    result = stock_basic_service.get_stock_board_industry_summary_ths_service()
    return result

@router.get("/get-stock-hot_follow_xq")
def get_stock_hot_follow_xq_service_api(
    symbol: str = Query("最热门", description="选择类型，可选值: {本周新增, 最热门}，默认: 最热门"),
) -> Dict[str, Any]:
    """ 查询同花顺行业一览表 """
    result = stock_basic_service.get_stock_hot_follow_xq_service(symbol)
    return result