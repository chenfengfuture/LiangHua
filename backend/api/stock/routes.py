#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票模块路由 - 简化版本
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from stock_services.mootdx import (
    get_kline_data,
    query_kline_with_cache, trigger_ws_kline_collect,
    kline_sse_streamer,
    get_realtime_quotes,
)

from stock_services.services.stock_indicator_service import stock_indicator_service
from stock_services.services.transaction_service import transaction_service
from stock_services.services.volume_indicator_service import volume_indicator_service
from stock_services.unity import *
from utils.db import get_conn, get_cursor
from stock_services.services.stock_basic import stock_basic_service
from stock_services.common.date_utils import get_trading_days
from stock_services.mootdx.mootdx_service import mootdx_service

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
    """东方财富-个股-股票信息 """
    result = stock_basic_service.get_stock_info_em(symbol)
    return result


@router.get("/get-stock-info-xq")
def get_stock_info_xq(
        symbol: str = Query("603777", description="股票代码，如 603777、000001")
) -> Dict[str, Any]:
    """查询雪球财经-个股1公司概况 """
    result = stock_basic_service.get_stock_info_xq(symbol)
    return result


@router.get("/get-stock-all")
def get_all_stocks() -> Dict[str, Any]:
    """查询全市场A股股票代码列表 """
    result = stock_basic_service.get_all_stock_list()
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
        symbol: str = Query("A股列表",
                            description="深交所列表类型，可选值：A股列表、B股列表、AB股列表、CDR列表，默认：A股列表")
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
        symbol: str = Query("终止上市公司",
                            description="深交所退市股票状态类型，可选值：终止上市公司、暂停上市公司，默认：终止上市公司")
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
def get_stock_board_concept_index_ths_api(
        symbol: str = Query("阿里巴巴概念", description="概念板块名称，如 阿里巴巴概念、人工智能概念"),
        start_date: str = Query(datetime.now().strftime("%Y%m%d"),
                                description="开始日期，格式为 YYYYMMDD，默认同结束日期"),
        end_date: str = Query(datetime.now().strftime("%Y%m%d"), description="结束日期，格式为 YYYYMMDD，默认今天"),
) -> Dict[str, Any]:
    """ 查询同花顺概念板块指数日频率数据 """
    result = stock_basic_service.get_stock_board_concept_index_ths_service(symbol, start_date, end_date)
    return result


@router.get("/get-stock-board-industry-index-ths")
def get_stock_board_industry_index_ths_api(
        symbol: str = Query("元件", description="行业板块名称，如 元件、饮料制造"),
        start_date: str = Query(datetime.now().strftime("%Y%m%d"), description="开始日期，格式为 YYYYMMDD"),
        end_date: str = Query(datetime.now().strftime("%Y%m%d"), description="结束日期，格式为 YYYYMMDD"),
) -> Dict[str, Any]:
    """ 查询同花顺行业板块指数日频率数据 """
    result = stock_basic_service.get_stock_board_industry_index_ths_service(symbol, start_date, end_date)
    return result


@router.get("/get-stock-board-industry-cons")
def get_stock_board_industry_cons_em_api(
        symbol: str = Query("元件", description="行业板块名称，如 元件、饮料制造"),
) -> Dict[str, Any]:
    """ 查询东方财富行业板块成份股 """
    result = stock_basic_service.get_stock_board_industry_cons_em_service(symbol)
    return result


@router.get("/get-stock-board-concept-cons")
def get_stock_board_concept_cons_em_api(
        symbol: str = Query("阿里巴巴概念", description="概念板块名称，如 阿里巴巴概念、人工智能概念"),
) -> Dict[str, Any]:
    """ 查询东方财富概念板块成份股 """
    result = stock_basic_service.get_stock_board_concept_cons_em_service(symbol)
    return result


@router.get("/get-stock-board-concept-info")
def get_stock_board_industry_summary_ths_api(
        symbol: str = Query("阿里巴巴概念", description="阿里巴巴概念 同花顺-板块-概念板块-板块简介"),
) -> Dict[str, Any]:
    """ 查询同花顺概念板块简介 """
    result = stock_basic_service.get_stock_board_concept_info_ths_service(symbol)
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
    """ 查询雪球关注排行榜 """
    result = stock_basic_service.get_stock_hot_follow_xq_service(symbol)
    return result


@router.get("/get-stock-hot-tweet_xq")
def get_stock_hot_follow_xq_service_api(
        symbol: str = Query("最热门", description="选择类型，可选值: {本周新增, 最热门}，默认: 最热门"),
) -> Dict[str, Any]:
    """ 询雪球 沪深股市 热度排行榜-讨论排行榜 """
    result = stock_basic_service.get_stock_hot_tweet_xq_service(symbol)
    return result


@router.get("/get-stock-hot-deal_xq")
def get_stock_hot_deal_service_api(
        symbol: str = Query("最热门", description="选择类型，可选值: {本周新增, 最热门}，默认: 最热门"),
) -> Dict[str, Any]:
    """ 查询雪球-沪深股市-热度排行榜-交易排行榜 """
    result = stock_basic_service.get_stock_hot_tweet_deal_service(symbol)
    return result


@router.get("/get-stock_hot_keyword_em")
def get_stock_hot_keyword_em_api(
        symbol: str = Query("SZ000665", description="symbol: 股票代码，如 SZ000665（需带市场前缀）"),
) -> Dict[str, Any]:
    """ 查询东方财富个股人气榜热门关键词 """
    result = stock_basic_service.get_stock_hot_keyword_em_service(symbol)
    return result


@router.get("/get_all_stock_board_industry")
def get_all_stock_board_industry_api() -> Dict[str, Any]:
    """ 查询同花顺行业一览表 """
    result = stock_basic_service.get_all_stock_board_industry_service()
    return result


@router.get("/get_stock_changes_em")
def get_stock_changes_em_api(
        symbol: str = Query("火箭发射", description="火箭发射, 快速反弹, 大笔买入, 封涨停板, 打开跌停板, ..."),
) -> Dict[str, Any]:
    """ 查询东方财富盘口异动数据 """
    result = stock_basic_service.get_stock_changes_em_service(symbol)
    return result


@router.get("/get-stock-board-change-em")
def get_stock_board_change_em_api(
) -> Dict[str, Any]:
    """ 查询东方财富当日板块异动详情 """
    result = stock_basic_service.get_stock_board_change_em_service()
    return result


@router.get("/get-stock-zt-pool-em")
def get_stock_zt_pool_em_api(
        date: Optional[str] = Query(None, description="日期，格式YYYYMMDD，默认为当天"),
) -> Dict[str, Any]:
    """ 查询东方财富当日板块异动详情 """
    result = stock_basic_service.get_stock_zt_pool_em_service(date)
    return result


@router.get("/get-stock-zt-pool-previous-em")
def get_stock_zt_pool_previous_em_api(
        date: Optional[str] = Query(None, description="日期，格式YYYYMMDD，默认为当天"),
) -> Dict[str, Any]:
    """ 东方财富昨日涨停股池数据查询接口 """
    result = stock_basic_service.get_stock_zt_pool_previous_em_service(date)
    return result


@router.get("/get-stock-zt-pool-strong-em")
def get_stock_zt_pool_strong_em_api(
        date: Optional[str] = Query(None, description="日期，格式YYYYMMDD，默认为当天"),
) -> Dict[str, Any]:
    """ 东方财富强势股池数据查询接口 """
    result = stock_basic_service.get_stock_zt_pool_strong_em_service(date)
    return result


@router.get("/get-stock-zt-pool-zbgc-em")
def get_stock_zt_pool_zbgc_em_api(
        date: Optional[str] = Query(None, description="日期，格式YYYYMMDD，默认为当天"),
) -> Dict[str, Any]:
    """ 东方财富炸板股池数据查询接口 """
    result = stock_basic_service.get_stock_zt_pool_zbgc_em_service(date)
    return result


@router.get("/get-stock-zt-pool-dtgc-em")
def get_stock_zt_pool_dtgc_em_api(
        date: Optional[str] = Query(None, description="日期，格式YYYYMMDD，默认为当天"),
) -> Dict[str, Any]:
    """ 东方财富跌停股池数据查询接口 """
    result = stock_basic_service.get_stock_zt_pool_dtgc_em_service(date)
    return result


@router.get("/get-stock-financial-report-sina")
def get_stock_financial_report_sina_api(
        stock: Optional[str] = Query(None, description="带市场标识的股票代码，如 sh600600（沪市）或 sz000001（深市）"),
        symbol: Optional[str] = Query("资产负债表", description="报表类型，可选值：资产负债表、利润表、现金流量表"),
) -> Dict[str, Any]:
    """ 东方财富跌停股池数据查询接口 """
    result = stock_basic_service.get_stock_financial_report_sina_service(stock, symbol)
    return result


@router.get("/get-stock-balance-sheet")
def get_stock_balance_sheet_by_yearly_api(
        symbol: Optional[str] = Query(None, description="带市场标识的股票代码，如 sh600600（沪市）或 sz000001（深市）"),
) -> Dict[str, Any]:
    """ 东方财富资产负债表 （按年度） """
    result = get_stock_balance_sheet_by_yearly_em(symbol)
    return result


@router.get("/get-stock-profit-sheet")
def get_stock_profit_sheet_by_repor_api(
        symbol: Optional[str] = Query(None, description="带市场标识的股票代码，如 sh600600（沪市）或 sz000001（深市）"),
) -> Dict[str, Any]:
    """ 东方财富利润表（按报告期）   """
    result = get_stock_profit_sheet_by_report(symbol)
    return result


@router.get("/get-stock-profit-sheet-year")
def get_stock_profit_sheet_by_yearly_api(
        symbol: Optional[str] = Query(None, description="带市场标识的股票代码，如 sh600600（沪市）或 sz000001（深市）"),
) -> Dict[str, Any]:
    """ 东方财富利润表（按年度）   """
    result = get_stock_profit_sheet_by_yearly_em(symbol)
    return result


@router.get("/get-stock-profit-forecast")
def get_stock_profit_forecast_api(
        symbol: Optional[str] = Query(None, description="带市场标识的股票代码，如 sh600600（沪市）或 sz000001（深市）"),
        indicator: Optional[str] = Query("预测年报每股收益",
                                         description="指标类型，choice of: 预测年报每股收益, 预测年报净利润, 业绩预测详表-机构,业绩预测详表-详细指标预测"),
) -> Dict[str, Any]:
    """ 同花顺盈利预测数据查询接口   """
    result = stock_basic_service.get_stock_profit_forecast_ths_service(symbol, indicator)
    return result


@router.get("/get-stock-fund-flow-individual")
def get_stock_fund_flow_individual_api(
        symbol: Optional[str] = Query("即时", description="即时, 3日排行, 5日排行, 10日排行, 20日排行"),
        limits: Optional[str] = Query("200", description="获取数据数量"),
) -> Dict[str, Any]:
    """ 资金流向-个股资金流   """
    result = stock_basic_service.get_stock_fund_flow_individual_service(symbol, limits)
    return result


@router.get("/get-stock-fund-concept")
def get_stock_fund_flow_concept_api(
        symbol: Optional[str] = Query("即时", description="即时, 3日排行, 5日排行, 10日排行, 20日排行"),
        limits: Optional[str] = Query("200", description="获取数据数量"),
) -> Dict[str, Any]:
    """ 资金流向-概念资金流   """
    result = stock_basic_service.get_stock_fund_flow_concept_service(symbol, limits)
    return result


@router.get("/get-stock-fund-flow")
def get_stock_individual_fund_flow_api(
        stock: Optional[str] = Query(None, description="股票代码，如 000425"),
) -> Dict[str, Any]:
    """ 同花顺-数据中心-资金流向-概念资金流   """
    result = stock_basic_service.get_stock_individual_fund_flow_service(stock)
    return result


@router.get("/get-stock-individual-flow")
def get_stock_individual_fund_flow_rank_api(
        indicator: Optional[str] = Query(None, description="今日, 3日, 5日, 10日"),
) -> Dict[str, Any]:
    """ 同花顺-数据中心-资金流向-排名   """
    result = stock_basic_service.get_stock_individual_fund_flow_rank_service(indicator)
    return result


@router.get("/get-stock-market-fund-flow")
def get_stock_market_fund_flow_api() -> Dict[str, Any]:
    """ 查询东方财富-数据中心-大盘资金流向   """
    result = stock_basic_service.get_stock_market_fund_flow_service()
    return result


@router.get("/get-sector-fund-flow")
def get_stock_sector_fund_flow_rank_api(
        indicator: Optional[str] = Query("今日", description="今日, 3日, 5日, 10日"),
        sector_type: Optional[str] = Query("行业资金流", description="行业资金流, 概念资金流, 地域资金流")
) -> Dict[str, Any]:
    """ 板块资金流排名   """
    result = stock_basic_service.get_stock_sector_fund_flow_rank_service(indicator, sector_type)
    return result


@router.get("/get-sector-fund-summary")
def get_stock_sector_fund_flow_summary_api(
        indicator: Optional[str] = Query("今日", description="今日, 5日, 10日"),
        symbol: Optional[str] = Query("保险", description="行业板块名称，建议选小行业如 保险、旅游、酒店，避免大数据量超时")
) -> Dict[str, Any]:
    """ 行业个股资金流（建议选较小行业避免超时）   """
    result = stock_basic_service.get_stock_sector_fund_flow_summary_service(indicator, symbol)
    return result


@router.get("/get-sector-fund-flow-summary")
def stock_sector_fund_flow_summary_api(
        symbol: Optional[str] = Query("沪深A股",
                                      description="全部股票, 沪深A股, 沪市A股, 科创板, 深市A股, 创业板, 沪市B股, 深市B股")
) -> Dict[str, Any]:
    """ 主力净流入排名   """
    result = get_stock_main_fund_flow({"symbol": symbol})
    return result


@router.get("/get-stock-account-statistics-em")
def get_stock_account_statistics_em_api() -> Dict[str, Any]:
    """
    股票账户统计月度数据查询接口（东方财富接口）

    接口: stock_account_statistics_em
    目标地址: https://data.eastmoney.com/cjsj/gpkhsj.html
    描述: 东方财富网-数据中心-特色数据-股票账户统计（月度）
    限量: 单次返回从 201504 开始至最新的所有历史数据
    """
    result = stock_basic_service.get_stock_account_statistics_em_service()
    return result


@router.get("/get-stock-comment-em")
def get_stock_comment_em_api() -> Dict[str, Any]:
    """
    千股千评数据查询接口（东方财富接口）

    接口: stock_comment_em
    目标地址: https://data.eastmoney.com/stockcomment/
    描述: 东方财富网-数据中心-特色数据-千股千评
    限量: 单次获取所有股票当日评分数据
    """
    result = stock_basic_service.get_stock_comment_em_service()
    return result


@router.get("/get-stock-comment-focus-em")
def get_stock_comment_detail_scrd_focus_em_api(
        symbol: str = Query("600000", description="股票代码，如 600000")
) -> Dict[str, Any]:
    """
    千股千评-用户关注指数查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_focus_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
    限量: 单次获取所有数据
    """
    result = get_stock_comment_detail_scrd_focus_em({"symbol": symbol})
    return result


@router.get("/get-stock-comment-desire-em")
def get_stock_comment_detail_scrd_desire_em_api(
        symbol: str = Query("600000", description="股票代码，如 600000")
) -> Dict[str, Any]:
    """
    千股千评-市场参与意愿查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_desire_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
    限量: 单次获取所有数据
    """
    result = stock_basic_service.get_stock_comment_detail_scrd_desire_em_service(symbol)
    return result


@router.get("/get-stock-gdhs")
def get_stock_zh_a_gdhs_api(
        date: str = Query("最新", description="查询日期，可选值：最新 或 YYYYMMDD 格式，如 20240930")
) -> Dict[str, Any]:
    """
    股东户数查询接口（东方财富接口）

    接口: stock_zh_a_gdhs
    目标地址: http://data.eastmoney.com/gdhs/
    描述: 东方财富网-数据中心-特色数据-股东户数数据
    限量: 单次获取返回所有数据
    """
    result = stock_basic_service.get_stock_zh_a_gdhs_service(date)
    return result


@router.get("/get-stock-gdhs-detail-em")
def get_stock_zh_a_gdhs_detail_em_api(
        symbol: str = Query("000001", description="股票代码，如 000001（平安银行），不带市场前缀")
) -> Dict[str, Any]:
    """
    股东户数详情查询接口（东方财富接口）

    接口: stock_zh_a_gdhs_detail_em
    目标地址: https://data.eastmoney.com/gdhs/detail/000002.html
    描述: 东方财富网-数据中心-特色数据-股东户数详情
    限量: 单次获取指定 symbol 的所有数据
    """
    result = stock_basic_service.get_stock_zh_a_gdhs_detail_em_service(symbol)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：LHB 龙虎榜
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/get-stock-lhb-jgmmtj-em")
def get_stock_lhb_jgmmtj_em_api(
        start_date: str = Query("20240417", description="开始日期，格式 YYYYMMDD"),
        end_date: str = Query("20240430", description="结束日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 龙虎榜机构买卖每日统计查询接口 """
    result = stock_basic_service.get_stock_lhb_jgmmtj_em_service(start_date, end_date)
    return result


@router.get("/get-stock-lhb-detail")
def get_stock_lhb_detail_em_api(
        start_date: str = Query("20220314", description="开始日期，格式 YYYYMMDD"),
        end_date: str = Query("20220315", description="结束日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 龙虎榜详情查询接口 """

    result = stock_basic_service.get_stock_lhb_detail_em_service(start_date, end_date)
    return result


@router.get("/get-stock-lhb-stock-statistic-em")
def get_stock_lhb_stock_statistic_em_api(
        symbol: str = Query("近一月", description="时间范围，可选值：近一月、近三月、近六月、近一年")
) -> Dict[str, Any]:
    """ 个股上榜统计查询接口 """
    result = stock_basic_service.get_stock_lhb_stock_statistic_em_service(symbol)
    return result


@router.get("/get-stock-lhb-hyyyb-em")
def get_stock_lhb_hyyyb_em_api(
        start_date: str = Query("20220311", description="开始日期，格式 YYYYMMDD"),
        end_date: str = Query("20220315", description="结束日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 每日活跃营业部查询接口 """
    result = stock_basic_service.get_stock_lhb_hyyyb_em_service(start_date, end_date)
    return result


@router.get("/get-stock-lhb-yyb-detail-em")
def get_stock_lhb_yyb_detail_em_api(
        symbol: str = Query("10634757", description="营业部代码，如 10634757")
) -> Dict[str, Any]:
    """ 营业部详情数据查询接口 """
    result = stock_basic_service.get_stock_lhb_yyb_detail_em_service(symbol)
    return result


@router.get("/get-stock-yybph-em-service")
def get_stock_lhb_yybph_em_service_api(
        symbol: str = Query("近三月", description="")
) -> Dict[str, Any]:
    """ 龙虎榜单-营业部排行 """
    result = stock_basic_service.get_stock_lhb_yybph_em_service(symbol)
    return result


@router.get("/get-stock-traderstatistic-em")
def get_stock_lhb_traderstatistic_em_api(
        symbol: str = Query("近三月", description="")
) -> Dict[str, Any]:
    """ 龙虎榜单-营业部统计 """
    result = stock_basic_service.get_stock_lhb_traderstatistic_em_service(symbol)
    return result


@router.get("/get-stock-lhb-traderstatistic-em")
def get_stock_lhb_stock_detail_em_api(
        symbol: str = Query("600077", description=""),
) -> Dict[str, Any]:
    """ 龙虎榜单-个股龙虎榜日期列表 """
    result = stock_basic_service.get_stock_lhb_stock_detail_date_em_service(symbol)
    return result


@router.get("/get-stock-traderstatistic-em")
def get_stock_lhb_detail_em_api(
        symbol: str = Query("600077", description=""),
        date: str = Query("20220310", description="需要获取上榜的日期"),
        flag: str = Query("买入", description="买入, 卖出")
) -> Dict[str, Any]:
    """ 龙虎榜单-个股龙虎榜详情 """
    result = stock_basic_service.get_stock_lhb_stock_detail_em_service(symbol, date, flag)
    return result


@router.get("/get-stock-lh-yyh-most")
def get_stock_lh_yyb_most_service_api(
) -> Dict[str, Any]:
    """ 龙虎榜单-上榜次数最多 """
    result = stock_basic_service.get_stock_lh_yyb_most_service()
    return result


@router.get("/get-stock-lh-capital")
def get_stock_lh_yyb_capital_api(
) -> Dict[str, Any]:
    """ 龙虎榜单-资金实力最强 """
    result = get_stock_lh_yyb_capital()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：Margin 融资融券
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/get-stock-margin-account-info")
def get_stock_margin_account_info_api() -> Dict[str, Any]:
    """ 两融账户信息查询接口（东方财富接口） """
    result = stock_basic_service.get_stock_margin_account_info_service()
    return result


@router.get("/get-stock-margin-sse")
def get_stock_margin_sse_api(
        start_date: str = Query("20240901", description="开始日期，格式 YYYYMMDD"),
        end_date: str = Query("20240930", description="结束日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 上交所融资融券汇总查询接口 """
    result = stock_basic_service.get_stock_margin_sse_service(start_date, end_date)
    return result


@router.get("/get-stock-margin-detail-szse")
def get_stock_margin_detail_szse_api(
        date: str = Query("20240930", description="查询日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 深交所融资融券明细查询接口 """
    result = stock_basic_service.get_stock_margin_detail_szse_service(date)
    return result


@router.get("/get-stock-margin-detail-sse")
def get_stock_margin_detail_sse_api(
        date: str = Query("20240930", description="查询日期，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 上交所融资融券明细查询接口 """
    result = stock_basic_service.get_stock_margin_detail_sse_service(date)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：Pledge 股权质押
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/get-stock-gpzy-profile-em")
def get_stock_gpzy_profile_em_api() -> Dict[str, Any]:
    """ 股权质押市场概况查询接口（东方财富接口） """
    result = stock_basic_service.get_stock_gpzy_profile_em_service()
    return result


@router.get("/get-stock-gpzy-pledge-ratio-em")
def get_stock_gpzy_pledge_ratio_em_api(
        date: str = Query("20240906", description="交易日，格式 YYYYMMDD")
) -> Dict[str, Any]:
    """ 上市公司质押比例查询接口 """
    result = stock_basic_service.get_stock_gpzy_pledge_ratio_em_service(date)
    return result


@router.get("/get-stock-gpzy-individual-detail-em")
def get_stock_gpzy_individual_pledge_ratio_detail_em_api(
        symbol: str = Query("603132", description="股票代码，如 603132")
) -> Dict[str, Any]:
    """ 个股重要股东股权质押明细查询接口 """
    result = stock_basic_service.get_stock_gpzy_individual_pledge_ratio_detail_em_service(symbol)
    return result


@router.get("/get-stock-gpzy-industry-data-em")
def get_stock_gpzy_industry_data_em_api() -> Dict[str, Any]:
    """ 上市公司质押比例-行业数据查询接口（东方财富接口） """
    result = stock_basic_service.get_stock_gpzy_industry_data_em_service()
    return result


# ============================================================================
# 技术选股排名API接口
# ============================================================================

@router.get("/get-stock-rank-cxg-ths")
def get_stock_rank_cxg_ths_api(
        symbol: str = Query("创月新高", description="创新高类型，可选值: 创月新高, 半年新高, 一年新高, 历史新高")
) -> Dict[str, Any]:
    """ 同花顺技术指标-创新高数据查询接口 """
    result = stock_basic_service.get_stock_rank_cxg_ths_service(symbol)
    return result


@router.get("/get-stock-rank-cxd-ths")
def get_stock_rank_cxd_ths_api(
        symbol: str = Query("创月新低", description="创月新低, 半年新低, 一年新低, 历史新低")
) -> Dict[str, Any]:
    """ 同花顺技术指标-创新底数据查询接口 """
    result = stock_basic_service.get_stock_rank_cxd_ths_service(symbol)
    return result


@router.get("/get-stock-rank-lxsz-ths")
def get_stock_rank_lxsz_ths_api() -> Dict[str, Any]:
    """ 同花顺技术选股-连续上涨数据查询接口 """
    result = stock_basic_service.get_stock_rank_lxsz_ths_service()
    return result


@router.get("/get-stock-rank-lxxd-ths")
def get_stock_rank_lxxd_ths_api() -> Dict[str, Any]:
    """ 同花顺技术选股-连续下跌数据查询接口 """
    result = stock_basic_service.get_stock_rank_lxxd_ths_service()
    return result


@router.get("/get-stock-rank-cxfl-ths")
def get_stock_rank_cxfl_ths_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-持续放量数据 """
    result = stock_basic_service.get_stock_rank_cxfl_ths_service()
    return result


@router.get("/get-stock-rank-cxsl-ths")
def get_stock_rank_cxsl_ths_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-持续缩量数据 """
    result = stock_basic_service.get_stock_rank_cxsl_ths_service()
    return result


@router.get("/get-stock-rank-xstp-ths")
def get_stock_rank_xstp_ths_api(
        symbol: str = Query("500日均线",
                            description="均线周期类型，可选值: 5日均线, 10日均线, 20日均线, 30日均线, 60日均线, 90日均线, 250日均线, 500日均线")
) -> Dict[str, Any]:
    """ 查询同花顺技术选股-向上突破数据 """
    result = stock_basic_service.get_stock_rank_xstp_ths_service(symbol)
    return result


@router.get("/get-stock-rank-xxtp-ths")
def get_stock_rank_xxtp_ths_api(
        symbol: str = Query("500日均线",
                            description="均线周期类型，可选值: 5日均线, 10日均线, 20日均线, 30日均线, 60日均线, 90日均线, 250日均线, 500日均线")
) -> Dict[str, Any]:
    """ 查询同花顺技术选股-向下突破数据 """
    result = stock_basic_service.get_stock_rank_xxtp_ths_service(symbol)
    return result


@router.get("/get-stock-rank-ljqs-ths")
def get_stock_rank_ljqs_ths_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-量价齐升数据 """
    result = stock_basic_service.get_stock_rank_ljqs_ths_service()
    return result


@router.get("/get-stock-rank-ljqd-ths")
def get_stock_rank_ljqd_ths_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-量价齐跌数据 """
    result = stock_basic_service.get_stock_rank_ljqd_ths_service()
    return result


@router.get("/get-stock-rank-xzjp-ths")
def get_stock_rank_xzjp_ths_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-险资举牌数据 """
    result = stock_basic_service.get_stock_rank_xzjp_ths_service()
    return result


@router.get("/get-stock-history-k")
def get_stock_history_k_data_api() -> Dict[str, Any]:
    """ 查询同花顺技术选股-险资举牌数据 """
    result = get_stock_k()
    return result


@router.get("/get-stock-zh-a-spot")
def get_stock_zh_a_spot_api() -> Dict[str, Any]:
    """ 查询新浪财经-沪深京 A 股实时行情数据 """
    result = stock_basic_service.get_stock_zh_a_spot_service()
    return result


@router.get("/get-stock-individual-spot-xq")
def get_stock_individual_spot_xq_api(
        symbol: str = Query("SH600000", description="证券代码，例如 SH600000、SZ000001、HK00700")
) -> Dict[str, Any]:
    """ 查询雪球-个股实时行情数据 """
    result = stock_basic_service.get_stock_individual_spot_xq_service(symbol)
    return result


@router.get("/get-stock-zh-a-hist")
def get_stock_zh_a_hist_api(
        symbol: str = Query("603777", description="股票代码, 例: 603777"),
        period: str = Query("daily", description="周期, 可选值: daily, weekly, monthly; 默认: daily"),
        start_date: str = Query("", description="开始日期, 格式: yyyymmdd, 例: 20210301"),
        end_date: str = Query("", description="结束日期, 格式: yyyymmdd, 例: 20210616"),
        adjust: str = Query("", description="复权类型, 可选值: 空(不复权), qfq(前复权), hfq(后复权); 默认: 不复权")
) -> Dict[str, Any]:
    """ 查询东方财富-沪深京 A 股日频率历史行情数据 """
    result = stock_basic_service.get_stock_zh_a_hist_service(symbol, period, start_date, end_date, adjust)
    return result


@router.get("/get-stock-individual-info")
def get_stock_individual_info_api(
        symbol: str = Query("603777", description="股票代码, 例: 603777"),
) -> Dict[str, Any]:
    """ 查询东方财富-个股-股票信息 """
    result = stock_basic_service.get_stock_individual_info_em_service(symbol)
    return result


@router.get("/get-stock-zh-a-daily")
def get_stock_zh_a_daily_api(
        symbol: str = Query("sh600000", description="股票代码, 例: sh600000"),
        start_date: str = Query("", description="开始日期, 格式: yyyymmdd, 例: 20201103"),
        end_date: str = Query("", description="结束日期, 格式: yyyymmdd, 例: 20201116"),
        adjust: str = Query("", description="复权类型, 可选值: 空(不复权), qfq, hfq, hfq-factor, qfq-factor; 默认: 空")
) -> Dict[str, Any]:
    """ 查询新浪财经-沪深京 A 股历史行情日频率数据 """
    result = stock_basic_service.get_stock_zh_a_daily_service(symbol, start_date, end_date, adjust)
    return result


@router.get("/get-stock-zh-a-hist-min-em")
def get_stock_zh_a_hist_min_em_api(
        symbol: Optional[str] = Query(default=None,
                                      description="股票代码(6位纯数字), 例: 603777; 不传则获取全市场数据（仅支持 day/week/month）"),
        period: str = Query(default="day", description=(
        "K线周期: ""day=日K线(默认), week=周K线, month=月K线, ""1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟")),
        start_date: Optional[str] = Query(default=None,
                                          description="起始日期, YYYYMMDD 或 YYYY-MM-DD; 不传则默认30天前"),
        end_date: Optional[str] = Query(default=None, description="截止日期, YYYYMMDD 或 YYYY-MM-DD; 不传则默认今天"),
) -> Dict[str, Any]:
    """ 查询通达信K线数据（mootdx 直连）；symbol 不传=全市场，传入=单只个股 """
    return get_kline_data(symbol, period, start_date, end_date)


@router.get("/get-kline")
def get_kline_api(
        symbol: Optional[str] = Query(default=None,
                                      description="股票代码: 单只(000001) / 逗号分隔多只(000001,600519) / 不传=全市场"),
        freq: str = Query(default="day", description="K线周期: day(日线) / week(周线) / month(月线)"),
        period: Optional[str] = Query(default=None, description="(别名)freq，兼容前端 daily/weekly/monthly 传法"),
        start_date: Optional[str] = Query(default=None,
                                          description="起始日期, 格式 YYYYMMDD 或 YYYY-MM-DD, 默认30天前"),
        end_date: Optional[str] = Query(default=None, description="截止日期, 格式 YYYYMMDD 或 YYYY-MM-DD, 默认今天"),
        mode: str = Query(default="overwrite", description="写入模式: overwrite=全量覆盖 / incremental=增量跳过已有"),
        use_sse: bool = Query(default=True, description="全市场采集时是否使用 SSE 流式返回"),
) -> Dict[str, Any]:
    """获取K线数据（mootdx 行情源），自动三层缓存查询"""
    # 兼容前端 period 传法（daily→day, weekly→week, monthly→month）
    if period is not None:
        _period_map = {"daily": "day", "weekly": "week", "monthly": "month"}
        freq = _period_map.get(period.lower(), period.lower())
    return query_kline_with_cache(symbol, freq, start_date, end_date, mode, use_sse)


@router.get("/get-kline/sse/{task_id}")
async def get_kline_sse_stream(task_id: str):
    """
    全市场 K 线采集 SSE 流式端点

    前端调用方式：
    const es = new EventSource('/api/stock/get-kline/sse/{task_id}');
    es.addEventListener('progress', (e) => console.log('进度', JSON.parse(e.data)));
    es.addEventListener('stock', (e) => console.log('股票完成', JSON.parse(e.data)));
    es.addEventListener('complete', (e) => { console.log('完成', JSON.parse(e.data)); es.close(); });
    """
    return StreamingResponse(
        kline_sse_streamer.stream_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲，确保实时推送
        },
    )


@router.post("/get-kline/ws-trigger")
def trigger_kline_ws_collect(
        freq: str = "day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """HTTP 触发 WebSocket 全市场采集（调试用）"""
    return trigger_ws_kline_collect(freq, start_date, end_date)


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：历史分时TICK（mootdx 通达信行情源）
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/tick-ceshi")
def trigger_kline_ws_collect(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """HTTP 触发 WebSocket 全市场采集（调试用）"""
    return get_trading_days(start_date, end_date)


@router.get("/get-minute-tick")
def get_minute_tick_api(
        symbol: str = Query("000001", description="股票代码，6 位纯数字"),
        date: str = Query("20260604", description="交易日期 YYYYMMDD"),
) -> Dict[str, Any]:
    """获取个股历史分时 tick 数据（mootdx 通达信直连，1 分钟粒度 240 条/日）

    缓存策略：Redis 2 小时 → MySQL 365 天
    表结构：minute_ticks_YYYYMM 按月分表
    唯一键：(symbol, trade_date, minute_idx)
    """

    result = mootdx_service.get_minute_ticks(symbol=symbol, date=date)
    return result


@router.get("/transaction")
def get_transaction_api(
        symbol: str = Query("600036", description="股票代码，6 位纯数字"),
        start: int = Query(0, description="起始位置"),
        offset: int = Query(800, ge=1, le=1000, description="数量，最大1000"),
        persist: bool = Query(False, description="是否持久化到 MySQL，默认 False"),
) -> Dict[str, Any]:
    """查询实时分笔成交（mootdx transaction），默认仅 Redis 短缓存不落库"""
    return mootdx_service.get_transaction(symbol=symbol, start=start, offset=offset, persist=persist)


@router.get("/history-transaction")
def get_history_transaction_api(
        symbol: str = Query("600036", description="股票代码，6 位纯数字"),
        date: str = Query("20260605", description="交易日期 YYYYMMDD"),
        start: int = Query(0, description="起始位置"),
        offset: int = Query(800, ge=1, le=1000, description="数量，最大1000"),
        persist: bool = Query(True, description="是否持久化到 MySQL，默认 True"),
        auto_clean: bool = Query(True, description="是否允许未来自动清理，默认 True"),
        retention_days: int = Query(30, ge=1, le=3650, description="保留天数，默认30天"),
) -> Dict[str, Any]:
    """查询历史分笔成交（mootdx transactions），支持写入清理策略字段"""
    return mootdx_service.get_history_transaction(
        symbol=symbol,
        date=date,
        start=start,
        offset=offset,
        persist=persist,
        auto_clean=auto_clean,
        retention_days=retention_days,
    )


@router.get("/indicators")
def get_indicators_api(
        symbol: str = Query(..., description="股票代码，如 000001"),
        start_date: Optional[str] = Query(None, description="起始日期 YYYYMMDD 或 YYYY-MM-DD，默认60天前"),
        end_date: Optional[str] = Query(None, description="截止日期 YYYYMMDD 或 YYYY-MM-DD，默认今天"),
) -> Dict[str, Any]:
    """
    获取技术指标（MA/MACD/KDJ/RSI/BOLL 等13个核心指标）。
    缓存优先：Redis → MySQL → 实时计算。
    """
    return stock_indicator_service.get_indicators(
        symbol=symbol, start_date=start_date, end_date=end_date,
    )


@router.post("/indicators/compute-today")
def compute_today_indicators_api() -> Dict[str, Any]:
    """手动触发今日指标计算（采集完成后调用）"""
    return stock_indicator_service.compute_today()


@router.post("/indicators/backfill")
def backfill_indicators_api(
        symbol: Optional[str] = Query(None, description="单只股票代码，如 000001；为空则全市场"),
        year: Optional[int] = Query(None, ge=1990, le=2030, description="指定年份，如 2026；为空则全部年份"),
        batch_size: int = Query(50, ge=10, le=500, description="每批股票数（全市场模式）"),
        parallel: int = Query(4, ge=1, le=16, description="并行线程数"),
) -> Dict[str, Any]:
    """
    批量回填历史指标数据。

    - 指定 symbol: 只回填该股票全部历史指标
    - 不指定 symbol: 全市场回填（扫描所有有K线数据的股票）
    - 指定 year: 只处理该年份有数据的股票
    """
    if symbol:
        return stock_indicator_service.backfill_stock(symbol)
    return stock_indicator_service.backfill_all(
        year=year, batch_size=batch_size, parallel=parallel,
    )


@router.post("/indicators/batch")
def batch_indicators_api(
        symbols: List[str] = Query(..., description="股票代码列表，如 000001,600519"),
        start_date: Optional[str] = Query(None, description="起始日期 YYYYMMDD"),
        end_date: Optional[str] = Query(None, description="截止日期 YYYYMMDD"),
) -> Dict[str, Any]:
    """
    批量查询多只股票的技术指标。
    """
    results = {}
    for sym in symbols:
        r = stock_indicator_service.get_indicators(
            symbol=sym.strip(), start_date=start_date, end_date=end_date,
        )
        results[sym.strip()] = r.get("data", []) if r.get("success") else []
    return {"success": True, "data": results}


@router.get("/indicators/latest")
def latest_indicators_api(
        symbol: str = Query(..., description="股票代码，如 000001"),
) -> Dict[str, Any]:
    """
    查询最新一条技术指标（仪表盘概览卡片用）。
    """
    today = datetime.now().strftime("%Y%m%d")
    r = stock_indicator_service.get_indicators(
        symbol=symbol, start_date=None, end_date=today,
    )
    if r.get("success"):
        data = r.get("data", [])
        return {"success": True, "data": data[-1] if data else None}
    return r


@router.get("/indicators/meta")
def indicators_meta_api() -> Dict[str, Any]:
    """
    返回支持的指标清单、参数和输出字段名。
    """
    return {
        "success": True,
        "data": {
            "indicators": [
                {"name": "MA", "label": "移动均线", "params": {"periods": [5, 10, 20, 60, 120, 250]},
                 "fields": ["ma_5", "ma_10", "ma_20", "ma_60", "ma_120", "ma_250"]},
                {"name": "BOLL", "label": "布林带", "params": {"period": 20, "multiplier": 2.0},
                 "fields": ["boll_ma", "boll_upper", "boll_lower", "boll_width"]},
                {"name": "SAR", "label": "抛物线转向", "params": {"step": 0.02, "max_step": 0.2},
                 "fields": ["sar"]},
                {"name": "VOL", "label": "成交量均线", "params": {"periods": [5, 10, 20]},
                 "fields": ["vol", "vol_ma_5", "vol_ma_10", "vol_ma_20"]},
                {"name": "MACD", "label": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9},
                 "fields": ["macd_dif", "macd_dea", "macd_bar"]},
                {"name": "KDJ", "label": "KDJ", "params": {"n": 9, "k_smooth": 3, "d_smooth": 3},
                 "fields": ["kdj_k", "kdj_d", "kdj_j"]},
                {"name": "RSI", "label": "RSI", "params": {"periods": [6, 12, 24]},
                 "fields": ["rsi_6", "rsi_12", "rsi_24"]},
                {"name": "WR", "label": "威廉指标", "params": {"periods": [6, 10, 14]},
                 "fields": ["wr_6", "wr_10", "wr_14"]},
                {"name": "CCI", "label": "CCI", "params": {"period": 14},
                 "fields": ["cci"]},
                {"name": "BIAS", "label": "乖离率", "params": {"periods": [6, 12, 24]},
                 "fields": ["bias_6", "bias_12", "bias_24"]},
                {"name": "PSY", "label": "心理线", "params": {"periods": [12, 24]},
                 "fields": ["psy_12", "psy_24", "psy_ma_12", "psy_ma_24"]},
                {"name": "OBV", "label": "能量潮", "params": {},
                 "fields": ["obv", "obv_ma"]},
                {"name": "DMI", "label": "趋向指标", "params": {"period": 14, "adx_smooth": 6},
                 "fields": ["pdi", "mdi", "adx", "adxr"]},
                {"name": "ROC", "label": "变动率", "params": {"period": 12, "smooth": 6},
                 "fields": ["roc", "roc_ma"]},
            ],
            "version": "v1",
            "redis_key_prefix": "indicator:v1",
            "indicator_count": 14,
        },
    }


@router.get("/indicators/status")
def indicators_status_api(
        trade_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD，默认今天"),
) -> Dict[str, Any]:
    """
    查询指标计算进度。
    """
    try:
        td = trade_date or datetime.now().strftime("%Y-%m-%d")
        sql = (
            "SELECT status, COUNT(*) as cnt FROM indicator_compute_log "
            "WHERE trade_date = %s GROUP BY status"
        )
        with get_cursor() as cur:
            cur.execute(sql, (td,))
            rows = cur.fetchall() or []
        status_map = {r["status"]: r["cnt"] for r in rows}
        return {
            "success": True,
            "data": {
                "trade_date": td,
                "done": status_map.get("done", 0),
                "failed": status_map.get("failed", 0),
                "pending": status_map.get("pending", 0),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
#  路由：昨日涨幅筛选
# ═══════════════════════════════════════════════════════════════════

@router.get("/get-yesterday-surge-stocks")
def get_yesterday_surge_stocks_api(
        min_pct: float = Query(3.0, ge=0, description="最小涨幅（%），默认 3.0"),
        max_pct: Optional[float] = Query(None, description="最大涨幅（%），不传则不限制"),
        limit: int = Query(50, ge=1, le=500, description="返回条数，默认 50"),
        sort: str = Query("desc", description="排序方向 desc/asc，默认 desc"),
) -> Dict[str, Any]:
    """
    获取昨日涨幅超过指定阈值的股票列表。

    数据来源: stock_klines 分年表，基于收盘价计算涨跌幅。
    缓存: 无（每次实时查询 stock_klines，性能足够）。
    """
    return stock_basic_service.get_yesterday_surge_stocks_service(
        min_pct=min_pct, max_pct=max_pct, limit=limit, sort=sort,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：实时行情（mootdx + Redis 缓存，不入库）
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/realtime-quotes")
def get_realtime_quotes_api(
        symbols: str = Query(..., description="股票代码，逗号分隔，如 000001,600519"),
        force: bool = Query(False, description="是否强制从 mootdx 拉取，跳过 Redis 缓存"),
) -> Dict[str, Any]:
    """
    获取个股实时行情（mootdx 通达信直连）。

    - 缓存策略：Redis Hash（Key: realtime:quotes），TTL=30分钟
    - 数据源：mootdx.quotes.Quotes.quotes() → 通达信行情服务器
    - 不入库：仅存入临时 Redis 缓存
    - 批次查询：单次最多 50 只（超过的自动分批）
    """
    return get_realtime_quotes(symbols=symbols, force_refresh=force)


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：成交量指标（仅 Redis 缓存，不入库）
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/volume/vwma")
def get_vwma_api(
        symbol: str = Query(..., description="股票代码"),
        period: int = Query(20, ge=5, le=120, description="VWMA 周期"),
        start_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="起始日期 YYYYMMDD"),
        end_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="结束日期 YYYYMMDD"),
) -> Dict[str, Any]:
    """
    获取 VWMA 成交量加权移动平均。
    仅 Redis 缓存（8 小时），不写入 MySQL。
    """
    return volume_indicator_service.get_vwma(
        symbol=symbol, period=period, start_date=start_date, end_date=end_date,
    )


@router.get("/volume/vr")
def get_vr_api(
        symbol: str = Query(..., description="股票代码"),
        period: int = Query(26, ge=10, le=60, description="VR 周期"),
        start_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="起始日期 YYYYMMDD"),
        end_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="结束日期 YYYYMMDD"),
) -> Dict[str, Any]:
    """
    获取 VR 成交量变异率。
    仅 Redis 缓存（8 小时），不写入 MySQL。
    """
    return volume_indicator_service.get_vr(
        symbol=symbol, period=period, start_date=start_date, end_date=end_date,
    )


@router.get("/volume/volume-bias")
def get_volume_bias_api(
        symbol: str = Query(..., description="股票代码"),
        periods: str = Query("5,10,20", description="逗号分隔的周期列表，如 5,10,20"),
        start_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="起始日期 YYYYMMDD"),
        end_date: Optional[str] = Query(None, pattern=r"^\d{8}$", description="结束日期 YYYYMMDD"),
) -> Dict[str, Any]:
    """
    获取 Volume Bias 成交量乖离率。
    仅 Redis 缓存（8 小时），不写入 MySQL。
    """
    try:
        parsed_periods = [int(p.strip()) for p in periods.split(",") if p.strip()]
        parsed_periods = [p for p in parsed_periods if 2 <= p <= 120]
    except (ValueError, AttributeError):
        parsed_periods = [5, 10, 20]
    if not parsed_periods:
        parsed_periods = [5, 10, 20]

    return volume_indicator_service.get_volume_bias(
        symbol=symbol, periods=parsed_periods,
        start_date=start_date, end_date=end_date,
    )
