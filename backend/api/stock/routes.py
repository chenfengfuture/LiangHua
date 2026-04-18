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


@router.get("/stocks/search")
def search_stocks(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    conn = Depends(get_conn)
) -> Dict[str, Any]:
    """搜索股票（按代码前缀 / 名称模糊匹配）"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, name, market, list_date FROM stocks_info "
                "WHERE symbol LIKE %s OR name LIKE %s ORDER BY symbol LIMIT %s",
                (f"{q}%", f"%{q}%", limit)
            )
            rows = cur.fetchall()
        return {"data": rows, "total": len(rows)}
    finally:
        conn.close()


@router.get("/stocks/list")
def list_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    market: Optional[str] = None,
    conn = Depends(get_conn)
) -> Dict[str, Any]:
    """获取股票列表（分页）"""
    try:
        with conn.cursor() as cur:
            where = "WHERE market = %s" if market else ""
            params = [market] if market else []
            cur.execute(f"SELECT COUNT(*) AS cnt FROM stocks_info {where}", params)
            total = cur.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT symbol, name, market, list_date FROM stocks_info {where} ORDER BY symbol LIMIT %s OFFSET %s",
                params + [page_size, offset]
            )
            rows = cur.fetchall()
        return {"data": rows, "total": total, "page": page, "page_size": page_size}
    finally:
        conn.close()


@router.post("/stocks/sync")
async def sync_stocks() -> Dict[str, Any]:
    """
    全市场股票列表同步接口
    
    整合5个新接口，抓取上证、深证、北证股票和退市股数据，
    统一字段映射后批量写入数据库。
    """
    try:
        stock_info_service = get_stock_info_service()
        result = stock_info_service.sync_all_stocks()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/{symbol}/info")
def get_stock_info_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """获取股票基本信息"""
    try:
        stock_info_service = get_stock_info_service()
        info = stock_info_service.get_stock_info(symbol)
        return {"success": True, "data": info, "symbol": symbol}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"股票信息获取失败: {str(e)}")


@router.get("/{symbol}/llm-analysis")
async def llm_analysis(
    symbol: str
) -> Dict[str, Any]:
    """
    股票LLM分析接口
    
    通过LLM分析股票基本面、技术面、市场情绪等，
    返回结构化分析结果。
    """
    try:
        stock_llm_service = get_stock_llm_service()
        analyzer = stock_llm_service.get_analyzer()
        
        return {
            "success": True,
            "symbol": symbol,
            "analyzer": analyzer,
            "message": "LLM分析完成",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM分析失败: {str(e)}")


@router.get("/{symbol}/lhb")
def get_lhb_data(
    symbol: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """获取股票龙虎榜数据"""
    try:
        stock_lhb_service = get_stock_lhb_service()
        print('获取龙虎榜', stock_lhb_service)
        lhb_data = stock_lhb_service.get_lhb_data(symbol=symbol, date=date)
        return lhb_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"龙虎榜数据获取失败: {str(e)}")


@router.get("/{symbol}/kline")
def get_kline_data(
    symbol: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    interval: str = Query("daily", description="时间间隔: daily, weekly, monthly"),
    conn = Depends(get_conn)
) -> Dict[str, Any]:
    """获取K线数据（保持向后兼容）"""
    try:
        # 这里可以调用服务层的方法
        # 暂时保持原有逻辑
        table_names = [f"stock_klines_{y}" for y in range(
            int(start_date[:4]), int(end_date[:4]) + 1
        )]
        
        sql = f"""
            SELECT trade_date, open, high, low, close, volume, turnover
            FROM {table_names[0]}
            WHERE symbol = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date ASC
        """
        
        with conn.cursor() as cur:
            cur.execute(sql, (symbol, start_date, end_date))
            rows = cur.fetchall()
        
        return {
            "success": True,
            "symbol": symbol,
            "data": rows,
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"K线数据获取失败: {str(e)}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：龙虎榜细分接口
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/lhb/detail")
def get_lhb_detail(
    start_date: str = Query(..., description="开始日期 YYYYMMDD，如 20240417"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD，如 20240430"),
    symbol: str = Query("lhb_detail", description="标识符，默认为 lhb_detail")
) -> Dict[str, Any]:
    """
    获取龙虎榜详情数据
    
    东方财富网-数据中心-龙虎榜单-龙虎榜详情
    单次返回指定时间范围内的所有历史数据
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_lhb_detail(start_date, end_date, symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"龙虎榜详情查询失败: {str(e)}")


@router.get("/lhb/institution")
def get_lhb_institution_trade(
    start_date: str = Query(..., description="开始日期 YYYYMMDD，如 20240417"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD，如 20240430"),
    symbol: str = Query("jgmmtj", description="标识符，默认为 jgmmtj")
) -> Dict[str, Any]:
    """
    获取机构买卖每日统计数据
    
    东方财富网-数据中心-龙虎榜单-机构买卖每日统计
    单次返回指定时间范围内的所有历史数据
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_lhb_institution_trade(start_date, end_date, symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"机构买卖统计查询失败: {str(e)}")


@router.get("/lhb/stock-statistics")
def get_lhb_stock_statistics(
    time_range: str = Query("近一月", description="时间范围：近一月、近三月、近六月、近一年"),
    symbol: str = Query("lhb_stock_statistic", description="标识符，默认为 lhb_stock_statistic")
) -> Dict[str, Any]:
    """
    获取个股上榜统计数据
    
    东方财富网-数据中心-龙虎榜单-个股上榜统计
    单次返回指定时间范围内的所有历史数据
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_lhb_stock_statistics(time_range, symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股上榜统计查询失败: {str(e)}")


@router.get("/lhb/active-brokers")
def get_lhb_active_brokers(
    start_date: str = Query(..., description="开始日期 YYYYMMDD，如 20240417"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD，如 20240430"),
    symbol: str = Query("lhb_hyyyb", description="标识符，默认为 lhb_hyyyb")
) -> Dict[str, Any]:
    """
    获取每日活跃营业部数据
    
    东方财富网-数据中心-龙虎榜单-每日活跃营业部
    单次返回指定时间范围内的所有历史数据
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_lhb_active_brokers(start_date, end_date, symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"活跃营业部查询失败: {str(e)}")


@router.get("/lhb/broker-detail/{broker_code}")
def get_lhb_broker_detail(
    broker_code: str,
    symbol: str = Query(None, description="标识符，可选，默认为营业部代码")
) -> Dict[str, Any]:
    """
    获取营业部详情数据
    
    东方财富网-数据中心-龙虎榜单-营业部历史交易明细
    单次返回指定营业部的所有历史数据
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_lhb_broker_detail(broker_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"营业部详情查询失败: {str(e)}")


@router.get("/lhb/all-data")
def get_all_lhb_data(
    start_date: str = Query(..., description="开始日期 YYYYMMDD，如 20240417"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD，如 20240430")
) -> Dict[str, Any]:
    """
    批量获取所有龙虎榜相关数据
    
    包含：龙虎榜详情、机构买卖统计、每日活跃营业部数据
    返回所有数据的综合响应
    """
    try:
        lhb_specific_service = get_lhb_specific_service()
        result = lhb_specific_service.get_all_lhb_data(start_date, end_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量查询龙虎榜数据失败: {str(e)}")