#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票Unity模块路由 - 独立路由文件

本文件包含所有股票Unity模块的API路由，按照业务分类组织。
参考龙虎榜接口模式，保持项目结构清晰明了，具有后续的可扩展性。

路由结构：
- /api/stock/unity/basic/...     - 股票基本信息
- /api/stock/unity/pledge/...    - 股权质押
- /api/stock/unity/financial/... - 财务报表
- /api/stock/unity/holder/...    - 股东数据
- /api/stock/unity/lhb/...       - 龙虎榜
- /api/stock/unity/fund_flow/... - 资金流向
- /api/stock/unity/margin/...    - 融资融券
- /api/stock/unity/board/...     - 板块概念
- /api/stock/unity/zt/...        - 涨跌停
- /api/stock/unity/rank/...      - 技术选股排名
"""

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
# 创建独立的路由器
router = APIRouter(prefix="/api/stock/unity", tags=["stock-unity"])

# ═══════════════════════════════════════════════════════════════════════════════
#  服务实例获取函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_unity_service():
    """获取股票Unity服务实例"""
    from stock_services.services.commont.basic_service import unity_service
    return unity_service


# ═══════════════════════════════════════════════════════════════════════════════
#  路由根路径
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
def root() -> Dict[str, Any]:
    """Unity模块根路径"""
    return {
        "success": True,
        "module": "stock-unity",
        "message": "量华量化平台股票Unity API运行中",
        "timestamp": datetime.now().isoformat(),
        "modules": [
            "basic - 股票基本信息",
            "pledge - 股权质押",
            "financial - 财务报表",
            "holder - 股东数据",
            "lhb - 龙虎榜",
            "fund_flow - 资金流向",
            "margin - 融资融券",
            "board - 板块概念",
            "zt - 涨跌停",
            "rank - 技术选股排名"
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：股票基本信息模块 (basic/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/basic/info/{symbol}")
def get_stock_info_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """获取股票基本信息"""
    return unity_service.get_stock_info(symbol)


@router.get("/basic/all-stocks")
def get_all_stock_codes_endpoint( unity_service = Depends(get_unity_service)) -> Dict[str, Any]:
    """获取全市场A股股票代码列表 - 数据库优先模式"""
    return unity_service.get_all_stock_codes()


@router.get("/basic/all-stocks/json")
def get_all_stock_codes_json_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """获取全市场A股股票代码列表（JSON格式）- 数据库优先模式"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    return unity_service.get_all_stock_codes_json()


@router.get("/basic/sh-stocks")
def get_sh_stock_codes_endpoint() -> Dict[str, Any]:
    """获取上海证券交易所股票代码和简称数据 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_basic_service import StockBasicService
        result = StockBasicService.get_sh_stock_codes()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "上交所股票代码获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上交所股票代码获取失败: {str(e)}")


@router.get("/basic/sz-stocks")
def get_sz_stock_codes_endpoint() -> Dict[str, Any]:
    """获取深圳证券交易所股票代码和简称数据 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_basic_service import StockBasicService
        result = StockBasicService.get_sz_stock_codes()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "深交所股票代码获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"深交所股票代码获取失败: {str(e)}")


@router.get("/basic/bj-stocks")
def get_bj_stock_codes_endpoint() -> Dict[str, Any]:
    """获取北京证券交易所股票代码和简称数据 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_basic_service import StockBasicService
        result = StockBasicService.get_bj_stock_codes()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "北交所股票代码获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"北交所股票代码获取失败: {str(e)}")


@router.get("/basic/sh-delist")
def get_sh_delist_stocks_endpoint() -> Dict[str, Any]:
    """获取上海证券交易所暂停/终止上市股票 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_basic_service import StockBasicService
        result = StockBasicService.get_sh_delist_stock_codes()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "上交所退市股票获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上交所退市股票获取失败: {str(e)}")


@router.get("/basic/sz-delist")
def get_sz_delist_stocks_endpoint() -> Dict[str, Any]:
    """获取深圳证券交易所终止/暂停上市股票 - 数据库优先模式"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    from backend.api.stock.services.stock_basic_service import StockBasicService
    return StockBasicService.get_sz_delist_stock_codes()


@router.get("/basic/xq-info/{symbol}")
def get_xq_stock_info_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """查询雪球财经-个股-公司概况 - 数据库优先模式"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    from backend.api.stock.services.stock_basic_service import StockBasicService
    return StockBasicService.get_xq_stock_info(symbol)


@router.get("/basic/info-json/{symbol}")
def get_stock_info_json_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """查询个股信息并返回JSON字符串 - 数据库优先模式"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    from backend.api.stock.services.stock_basic_service import StockBasicService
    return StockBasicService.get_stock_info_json(symbol)


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：股权质押模块 (pledge/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/pledge/profile")
def get_gpzy_profile_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询股权质押市场概况（全量历史）"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    return unity_service.get_stock_gpzy_profile_em()


@router.get("/pledge/ratio/{date}")
def get_gpzy_pledge_ratio_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询指定交易日上市公司质押比例"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    return unity_service.get_stock_gpzy_pledge_ratio_em(date)


@router.get("/pledge/individual/{symbol}")
def get_gpzy_individual_pledge_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询个股重要股东股权质押明细（全量历史）"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    return unity_service.get_stock_gpzy_individual_pledge_ratio_detail_em(symbol)


@router.get("/pledge/industry")
def get_gpzy_industry_data_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询各行业质押比例汇总数据（全量）"""
    # 直接调用服务，路由层不做任何业务逻辑处理
    return unity_service.get_stock_gpzy_industry_data_em()


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：财务报表模块 (financial/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/financial/sina/{stock}/{symbol}")
def get_sina_financial_report_endpoint(
    stock: str,
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询新浪财经财务报表"""
    try:
        result = unity_service.get_stock_financial_report_sina(stock, symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "新浪财经财务报表获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新浪财经财务报表获取失败: {str(e)}")


@router.get("/financial/balance-sheet/{symbol}")
def get_balance_sheet_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富资产负债表（按年度）"""
    try:
        result = unity_service.get_stock_balance_sheet_by_yearly_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "资产负债表获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资产负债表获取失败: {str(e)}")


@router.get("/financial/profit-sheet-report/{symbol}")
def get_profit_sheet_report_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富利润表（按报告期）"""
    try:
        result = unity_service.get_stock_profit_sheet_by_report_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "利润表（报告期）获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"利润表（报告期）获取失败: {str(e)}")


@router.get("/financial/profit-sheet-yearly/{symbol}")
def get_profit_sheet_yearly_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富利润表（按年度）"""
    try:
        result = unity_service.get_stock_profit_sheet_by_yearly_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "利润表（年度）获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"利润表（年度）获取失败: {str(e)}")


@router.get("/financial/cash-flow/{symbol}")
def get_cash_flow_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富现金流量表（按报告期）"""
    try:
        result = unity_service.get_stock_cash_flow_sheet_by_report_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "现金流量表获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"现金流量表获取失败: {str(e)}")


@router.get("/financial/profit-forecast/{symbol}/{indicator}")
def get_profit_forecast_endpoint(
    symbol: str,
    indicator: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺盈利预测数据"""
    try:
        result = unity_service.get_stock_profit_forecast_ths(symbol, indicator)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "盈利预测数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"盈利预测数据获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：股东数据模块 (holder/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/holder/account-statistics")
def get_account_statistics_endpoint() -> Dict[str, Any]:
    """查询月度股票账户统计数据（201504 起全量）- 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_account_statistics()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "月度股票账户统计获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"月度股票账户统计获取失败: {str(e)}")


@router.get("/holder/stock-comment")
def get_stock_comment_endpoint() -> Dict[str, Any]:
    """查询千股千评数据（全部股票当日评分）- 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_comment()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "千股千评数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"千股千评数据获取失败: {str(e)}")


@router.get("/holder/comment-focus/{symbol}")
def get_comment_focus_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """查询千股千评-用户关注指数 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_comment_focus(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "千股千评用户关注指数获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"千股千评用户关注指数获取失败: {str(e)}")


@router.get("/holder/comment-desire/{symbol}")
def get_comment_desire_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """查询千股千评-市场参与意愿 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_comment_desire(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "千股千评市场参与意愿获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"千股千评市场参与意愿获取失败: {str(e)}")


@router.get("/holder/gdhs/{date}")
def get_gdhs_endpoint(
    date: str
) -> Dict[str, Any]:
    """查询全市场股东户数数据 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_gdhs_all(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "全市场股东户数获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全市场股东户数获取失败: {str(e)}")


@router.get("/holder/gdhs-detail/{symbol}")
def get_gdhs_detail_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """查询个股股东户数详情 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_holder_service import StockHolderService
        result = StockHolderService.get_stock_gdhs_detail(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "个股股东户数详情获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股股东户数详情获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：龙虎榜模块 (lhb/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/lhb/institution")
def get_lhb_institution_endpoint(
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD"),
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询龙虎榜机构买卖每日统计"""
    try:
        result = unity_service.get_stock_lhb_jgmmtj_em(start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "龙虎榜机构买卖统计获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"龙虎榜机构买卖统计获取失败: {str(e)}")


@router.get("/lhb/detail")
def get_lhb_detail_endpoint(
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD"),
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询龙虎榜详情数据"""
    try:
        result = unity_service.get_stock_lhb_detail_em(start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "龙虎榜详情获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"龙虎榜详情获取失败: {str(e)}")


@router.get("/lhb/stock-statistic/{symbol}")
def get_lhb_stock_statistic_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询个股上榜统计数据"""
    try:
        result = unity_service.get_stock_lhb_stock_statistic_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "个股上榜统计获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股上榜统计获取失败: {str(e)}")


@router.get("/lhb/active-brokers")
def get_lhb_active_brokers_endpoint(
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD"),
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询每日活跃营业部数据"""
    try:
        result = unity_service.get_stock_lhb_hyyyb_em(start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "每日活跃营业部获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"每日活跃营业部获取失败: {str(e)}")


@router.get("/lhb/broker-detail/{symbol}")
def get_lhb_broker_detail_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询营业部历史交易明细"""
    try:
        result = unity_service.get_stock_lhb_yyb_detail_em(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "营业部历史交易明细获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"营业部历史交易明细获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：融资融券模块 (margin/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/margin/account-info")
def get_margin_account_info_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询两融账户信息（东方财富）"""
    try:
        result = unity_service.get_stock_margin_account_info()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "两融账户信息获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"两融账户信息获取失败: {str(e)}")


@router.get("/margin/sse-summary")
def get_margin_sse_endpoint(
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD"),
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询上交所融资融券汇总数据"""
    try:
        result = unity_service.get_stock_margin_sse(start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "上交所融资融券汇总获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上交所融资融券汇总获取失败: {str(e)}")


@router.get("/margin/szse-detail/{date}")
def get_margin_szse_detail_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询深交所融资融券明细数据"""
    try:
        result = unity_service.get_stock_margin_detail_szse(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "深交所融资融券明细获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"深交所融资融券明细获取失败: {str(e)}")


@router.get("/margin/sse-detail/{date}")
def get_margin_sse_detail_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询上交所融资融券明细数据"""
    try:
        result = unity_service.get_stock_margin_detail_sse(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "上交所融资融券明细获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上交所融资融券明细获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：板块概念模块 (board/) - 数据库优先模式
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/board/concept-index/{symbol}")
def get_board_concept_index_endpoint(
    symbol: str,
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD")
) -> Dict[str, Any]:
    """
    查询同花顺概念板块指数日频率数据 - 数据库优先模式
    
    Args:
        symbol: 概念板块代码
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_concept_index_service(symbol, start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "概念板块指数获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"概念板块指数获取失败: {str(e)}")


@router.get("/board/industry-summary")
def get_board_industry_summary_endpoint() -> Dict[str, Any]:
    """
    查询同花顺行业一览表 - 数据库优先模式
    
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_industry_summary_service()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "行业一览表获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"行业一览表获取失败: {str(e)}")


@router.get("/board/concept-info/{symbol}")
def get_board_concept_info_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介 - 数据库优先模式
    
    Args:
        symbol: 概念板块代码
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_concept_info_service(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "概念板块简介获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"概念板块简介获取失败: {str(e)}")


@router.get("/board/industry-index/{symbol}")
def get_board_industry_index_endpoint(
    symbol: str,
    start_date: str = Query(..., description="开始日期 YYYYMMDD"),
    end_date: str = Query(..., description="结束日期 YYYYMMDD")
) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据 - 数据库优先模式
    
    Args:
        symbol: 行业板块代码
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_industry_index_service(symbol, start_date, end_date)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "行业板块指数获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"行业板块指数获取失败: {str(e)}")


@router.get("/board/hot-follow/{symbol}")
def get_board_hot_follow_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """
    查询雪球关注排行榜 - 数据库优先模式
    
    Args:
        symbol: 股票代码
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_hot_follow_service(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "雪球关注排行榜获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"雪球关注排行榜获取失败: {str(e)}")


@router.get("/board/hot-rank/{symbol}")
def get_board_hot_rank_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """
    查询东方财富股票热度历史趋势及粉丝特征 - 数据库优先模式
    
    Args:
        symbol: 股票代码
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_hot_rank_service(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "股票热度历史趋势获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"股票热度历史趋势获取失败: {str(e)}")


@router.get("/board/hot-keyword/{symbol}")
def get_board_hot_keyword_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词 - 数据库优先模式
    
    Args:
        symbol: 股票代码
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_hot_keyword_service(symbol)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "个股人气榜热门关键词获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股人气榜热门关键词获取失败: {str(e)}")


@router.get("/board/changes/{symbol}")
def get_board_changes_endpoint(
    symbol: str
) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据 - 数据库优先模式
    
    Args:
        symbol: 股票代码
        
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_changes_service(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "盘口异动数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"盘口异动数据获取失败: {str(e)}")


@router.get("/board/board-change")
def get_board_change_endpoint() -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情 - 数据库优先模式
    
    Returns:
        统一格式的响应数据
    """
    try:
        result = StockBoardService.get_board_change_service()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "当日板块异动获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"当日板块异动获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：涨跌停模块 (zt/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/zt/pool/{date}")
def get_zt_pool_endpoint(
    date: str
) -> Dict[str, Any]:
    """查询东方财富涨停股池数据 - 数据库优先模式"""
    try:
        from backend.api.stock.services.stock_zt_service import StockZTService
        result = StockZTService.get_zt_pool(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "涨停股池获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"涨停股池获取失败: {str(e)}")


@router.get("/zt/previous-pool/{date}")
def get_zt_previous_pool_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富昨日涨停股池数据"""
    try:
        result = unity_service.get_stock_zt_pool_previous_em(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "昨日涨停股池获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"昨日涨停股池获取失败: {str(e)}")


@router.get("/zt/strong-pool/{date}")
def get_zt_strong_pool_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富强势股池数据"""
    try:
        result = unity_service.get_stock_zt_pool_strong_em(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "强势股池获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"强势股池获取失败: {str(e)}")


@router.get("/zt/zbgc-pool/{date}")
def get_zt_zbgc_pool_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富炸板股池数据"""
    try:
        result = unity_service.get_stock_zt_pool_zbgc_em(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "炸板股池获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"炸板股池获取失败: {str(e)}")


@router.get("/zt/dtgc-pool/{date}")
def get_zt_dtgc_pool_endpoint(
    date: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富跌停股池数据"""
    try:
        result = unity_service.get_stock_zt_pool_dtgc_em(date)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "跌停股池获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"跌停股池获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：技术选股排名模块 (rank/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rank/cxg/{symbol}")
def get_rank_cxg_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """
    查询同花顺技术指标-创新高数据
    
    Args:
        symbol: 创新高类型，可选值:
            - "创月新高": 创月新高股票
            - "半年新高": 创半年新高股票
            - "一年新高": 创一年新高股票
            - "历史新高": 创历史新高股票
    
    Returns:
        统一格式的响应数据，包含创新高股票列表
    """
    try:
        result = unity_service.get_stock_rank_cxg_ths(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "创新高数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创新高数据获取失败: {str(e)}")


@router.get("/rank/lxsz")
def get_rank_lxsz_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-连续上涨数据"""
    try:
        result = unity_service.get_stock_rank_lxsz_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "连续上涨数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连续上涨数据获取失败: {str(e)}")


@router.get("/rank/cxfl")
def get_rank_cxfl_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-持续放量数据"""
    try:
        result = unity_service.get_stock_rank_cxfl_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "持续放量数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"持续放量数据获取失败: {str(e)}")


@router.get("/rank/cxsl")
def get_rank_cxsl_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-持续缩量数据"""
    try:
        result = unity_service.get_stock_rank_cxsl_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "持续缩量数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"持续缩量数据获取失败: {str(e)}")


@router.get("/rank/xstp/{symbol}")
def get_rank_xstp_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """
    查询同花顺技术选股-向上突破数据
    
    Args:
        symbol: 均线类型，可选值:
            - "5日均线": 突破5日均线股票
            - "10日均线": 突破10日均线股票
            - "20日均线": 突破20日均线股票
            - "30日均线": 突破30日均线股票
            - "60日均线": 突破60日均线股票
            - "90日均线": 突破90日均线股票
            - "250日均线": 突破250日均线股票
            - "500日均线": 突破500日均线股票
    
    Returns:
        统一格式的响应数据，包含向上突破股票列表
    """
    try:
        result = unity_service.get_stock_rank_xstp_ths(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "向上突破数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向上突破数据获取失败: {str(e)}")


@router.get("/rank/ljqs")
def get_rank_ljqs_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-量价齐升数据"""
    try:
        result = unity_service.get_stock_rank_ljqs_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "量价齐升数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"量价齐升数据获取失败: {str(e)}")


@router.get("/rank/ljqd")
def get_rank_ljqd_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-量价齐跌数据"""
    try:
        result = unity_service.get_stock_rank_ljqd_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "量价齐跌数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"量价齐跌数据获取失败: {str(e)}")


@router.get("/rank/xzjp")
def get_rank_xzjp_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺技术选股-险资举牌数据"""
    try:
        result = unity_service.get_stock_rank_xzjp_ths()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "险资举牌数据获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"险资举牌数据获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：资金流向模块 (fund_flow/)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/fund-flow/individual/{symbol}")
def get_fund_flow_individual_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺-数据中心-资金流向-个股资金流"""
    try:
        result = unity_service.get_stock_fund_flow_individual(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "个股资金流获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股资金流获取失败: {str(e)}")


@router.get("/fund-flow/concept/{symbol}")
def get_fund_flow_concept_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询同花顺-数据中心-资金流向-概念资金流"""
    try:
        result = unity_service.get_stock_fund_flow_concept(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "概念资金流获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"概念资金流获取失败: {str(e)}")


@router.get("/fund-flow/individual-flow/{stock}/{market}")
def get_individual_fund_flow_endpoint(
    stock: str,
    market: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富-数据中心-个股资金流向（近100交易日）"""
    try:
        result = unity_service.get_stock_individual_fund_flow(stock, market)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "个股资金流向获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"个股资金流向获取失败: {str(e)}")


@router.get("/fund-flow/individual-rank/{indicator}")
def get_individual_fund_flow_rank_endpoint(
    indicator: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富-数据中心-资金流向排名"""
    try:
        result = unity_service.get_stock_individual_fund_flow_rank(indicator)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "资金流向排名获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资金流向排名获取失败: {str(e)}")


@router.get("/fund-flow/market-flow")
def get_market_fund_flow_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富-数据中心-大盘资金流向"""
    try:
        result = unity_service.get_stock_market_fund_flow()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "大盘资金流向获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"大盘资金流向获取失败: {str(e)}")


@router.get("/fund-flow/sector-rank/{indicator}/{sector_type}")
def get_sector_fund_flow_rank_endpoint(
    indicator: str,
    sector_type: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富+数据中心+板块资金流排名"""
    try:
        result = unity_service.get_stock_sector_fund_flow_rank(indicator, sector_type)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "板块资金流排名获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"板块资金流排名获取失败: {str(e)}")


@router.get("/fund-flow/sector-summary/{symbol}/{indicator}")
def get_sector_fund_flow_summary_endpoint(
    symbol: str,
    indicator: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富-数据中心-行业个股资金流"""
    try:
        result = unity_service.get_stock_sector_fund_flow_summary(symbol, indicator)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "行业个股资金流获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"行业个股资金流获取失败: {str(e)}")


@router.get("/fund-flow/main-flow/{symbol}")
def get_main_fund_flow_endpoint(
    symbol: str,
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """查询东方财富-数据中心-主力净流入排名"""
    try:
        result = unity_service.get_stock_main_fund_flow(symbol)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "主力净流入排名获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"主力净流入排名获取失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  批量查询接口
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/batch/all-basic-info")
def get_all_basic_info_endpoint(
    unity_service = Depends(get_unity_service)
) -> Dict[str, Any]:
    """批量获取所有基本信息"""
    try:
        result = unity_service.get_all_basic_info()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "批量基本信息获取失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量基本信息获取失败: {str(e)}")