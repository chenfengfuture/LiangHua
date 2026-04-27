#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块概念字段映射工具模块

专门处理板块概念相关接口的字段映射，对应 board/service.py 中的9个接口。
重构优化：使用统一映射框架，减少代码重复，保持向上兼容。
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import date
from functools import wraps

from system_service.service_result import success_result

logger = logging.getLogger(__name__)


# ============================================================================
# 基础字段映射常量（提取公共字段）
# ============================================================================

# 通用日期字段映射
DATE_FIELDS = {
    "日期": "trade_date",
    "date": "trade_date",
    "stat_date": "stat_date",
    "rank_date": "rank_date",
    "change_date": "change_date",
    "occur_time": "occur_time",
    "time": "occur_time"
}

# 通用股票字段映射
STOCK_FIELDS = {
    "股票代码": "symbol",
    "code": "symbol",
    "symbol": "symbol",
    "股票名称": "name",
    "stock_name": "name",
    "name": "name",
    "当前价格": "current_price",
    "price": "current_price",
    "涨跌幅": "change_percent",
    "pct_chg": "change_percent",
    "change_pct": "change_percent",
    "change_percent": "change_percent",
    "涨跌额": "change_amount",
    "change": "change_amount",
    "change_amount": "change_amount",
    "成交量": "volume",
    "vol": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "振幅": "amplitude",
    "amp": "amplitude",
    "amplitude": "amplitude",
    "换手率": "turnover_rate",
    "turnover": "turnover_rate",
    "turnover_rate": "turnover_rate"
}

# 价格字段映射
PRICE_FIELDS = {
    "开盘": "open_price",
    "开盘价": "open_price",
    "open": "open_price",
    "最高": "high_price",
    "最高价": "high_price",
    "high": "high_price",
    "最低": "low_price",
    "最低价": "low_price",
    "low": "low_price",
    "收盘": "close_price",
    "收盘价": "close_price",
    "close": "close_price",
    "净流入": "net_inflow",
}

# 板块字段映射
BOARD_FIELDS = {
    "板块类型": "board_type",
    "type": "board_type",
    "板块名称": "board_name",
    "board_name": "board_name",
    "异动方向": "change_direction",
    "direction": "change_direction",
    "异动原因": "change_reason",
    "reason": "change_reason",
    "强度级别": "strength_level",
    "strength": "strength_level",
}

# 行业/概念字段映射
INDUSTRY_CONCEPT_FIELDS = {
    "行业代码": "industry_code",
    "industry_code": "industry_code",
    "行业名称": "industry_name",
    "industry_name": "industry_name",
    "概念代码": "concept_code",
    "concept_code": "concept_code",
    "板块": "board_name",
    "概念名称": "concept_name",
    "concept_name": "concept_name",
    "概念简介": "introduction",
    "desc": "introduction",
    "introduction": "introduction",
    "相关股票": "related_stocks",
    "stocks": "related_stocks",
    "related_stocks": "related_stocks",
    "股票数量": "stock_count",
    "count": "stock_count",
    "stock_count": "stock_count",
    "总市值": "total_market_cap",
    "market_cap": "total_market_cap",
    "total_market_cap": "total_market_cap",
    "主要公司": "main_companies",
    "companies": "main_companies",
    "main_companies": "main_companies",
    "热度级别": "hot_level",
    "hot": "hot_level",
    "hot_level": "hot_level",
    "趋势方向": "trend_direction",
    "trend": "trend_direction",
    "trend_direction": "trend_direction"
}

# 热度相关字段映射
HEAT_FIELDS = {
    "热度排名": "hot_rank",
    "rank": "hot_rank",
    "hot_rank": "hot_rank",
    "热度得分": "heat_score",
    "score": "heat_score",
    "heat": "heat_score",
    "heat_score": "heat_score",
    "搜索次数": "search_count",
    "search": "search_count",
    "search_count": "search_count",
    "讨论次数": "discussion_count",
    "discuss": "discussion_count",
    "discussion_count": "discussion_count",
    "阅读次数": "read_count",
    "read": "read_count",
    "read_count": "read_count",
    "提及次数": "mention_count",
    "mention": "mention_count",
    "mention_count": "mention_count"
}

# 关注/粉丝字段映射
FOLLOW_FIELDS = {
    "关注人数": "follow_count",
    "followers": "follow_count",
    "follow_count": "follow_count",
    "关注增长": "follow_increase",
    "follow_growth": "follow_increase",
    "follow_increase": "follow_increase",
    "粉丝数量": "follower_count",
    "follower_count": "follower_count",
    "粉丝增长": "follower_increase",
    "follower_growth": "follower_increase",
    "follower_increase": "follower_increase",
    "男性比例": "male_ratio",
    "male": "male_ratio",
    "male_ratio": "male_ratio",
    "女性比例": "female_ratio",
    "female": "female_ratio",
    "female_ratio": "female_ratio",
    "年龄分布": "age_distribution",
    "age": "age_distribution",
    "age_distribution": "age_distribution",
    "地区分布": "region_distribution",
    "region": "region_distribution",
    "region_distribution": "region_distribution"
}

# 排名字段映射
RANK_FIELDS = {
    "排名": "rank_position",
    "rank_position": "rank_position",
    "位置": "rank_position",
    "position": "rank_position"
}

# 统计字段映射
STATISTICS_FIELDS = {
    "公司家数": "company_count",
    "company_count": "company_count",
    "平均市盈率": "avg_pe",
    "pe": "avg_pe",
    "avg_pe": "avg_pe",
    "平均市净率": "avg_pb",
    "pb": "avg_pb",
    "avg_pb": "avg_pb",
    "平均涨跌幅": "avg_change_percent",
    "avg_change_percent": "avg_change_percent",
    "上涨家数": "rise_count",
    "up": "rise_count",
    "rise_count": "rise_count",
    "下跌家数": "fall_count",
    "down": "fall_count",
    "fall_count": "fall_count",
    "平盘家数": "flat_count",
    "flat": "flat_count",
    "flat_count": "flat_count"
}

# 9. 当日板块异动详情数据
BOARD_CHANGE_MAPPING = {
    **BOARD_FIELDS,
    **STOCK_FIELDS,
    **STATISTICS_FIELDS,
    "领涨股票": "leader_stock",
    "leader_code": "leader_stock",
    "领涨股票名称": "leader_name",
    "领涨股": "leading_stock_name",
    "领涨股-最新价": "leading_stock_price",
    "领涨股-涨跌幅(%)": "leading_stock_change",
    "leader_name": "leader_name",
    "领涨跌幅": "leader_change_percent",
    "leader_change": "leader_change_percent",
    "总成交量": "total_volume",
    "total_volume": "total_volume",
    "总成交额": "total_amount",
    "total_amount": "total_amount"

}
# ============================================================================
# 各接口专用映射配置
# ============================================================================

# 1. 概念板块指数日频率数据
BOARD_CONCEPT_INDEX_MAPPING = {
    **DATE_FIELDS,
    **PRICE_FIELDS,
    **STOCK_FIELDS
}

# 2. 行业板块指数日频率数据  
BOARD_INDUSTRY_INDEX_MAPPING = {
    **DATE_FIELDS,
    **PRICE_FIELDS,
    **STOCK_FIELDS
}

# 3. 行业一览表数据
BOARD_INDUSTRY_SUMMARY_MAPPING = {
    **INDUSTRY_CONCEPT_FIELDS,
    **STATISTICS_FIELDS,
    **BOARD_CHANGE_MAPPING,
    "总成交量": "total_volume",
    "总成交额": "total_amount",
}

# 4. 概念板块简介数据
BOARD_CONCEPT_INFO_MAPPING = {
    **INDUSTRY_CONCEPT_FIELDS
}

# 5. 雪球关注排行榜数据
STOCK_HOT_FOLLOW_MAPPING = {
    **RANK_FIELDS,
    **STOCK_FIELDS,
    **FOLLOW_FIELDS,
    "讨论数": "discussion_count",
    "discussions": "discussion_count"
}

# 6. 股票热度历史趋势及粉丝特征数据
STOCK_HOT_RANK_DETAIL_MAPPING = {
    **DATE_FIELDS,
    **HEAT_FIELDS,
    **FOLLOW_FIELDS,
    "code": "symbol"  # 特殊处理：code映射到symbol
}

# 7. 个股人气榜热门关键词数据
STOCK_HOT_KEYWORD_MAPPING = {
    **HEAT_FIELDS,
    **RANK_FIELDS,
    "关键词": "keyword",
    "keyword": "keyword",
    "趋势": "trend",
    "trend": "trend"
}

# 8. 盘口异动数据
STOCK_CHANGES_MAPPING = {
    **BOARD_FIELDS,
    **STOCK_FIELDS,
    **DATE_FIELDS,
    "异动类型": "change_type",
    "change_type": "change_type"
}



# ============================================================================
# 工具函数
# ============================================================================

def map_fields(data: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    批量字段映射：源key → 目标库字段
    
    Args:
        data: 原始数据列表
        mapping: 字段映射字典
        
    Returns:
        映射后的数据列表
    """
    return [
        {mapping.get(key, key): value for key, value in item.items() if key in mapping}
        for item in data
    ]


def normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码
    
    Args:
        symbol: 股票代码
        
    Returns:
        标准化的股票代码（带市场后缀）
    """
    if not symbol:
        return ""

    symbol = str(symbol).strip()

    # 如果没有市场后缀，尝试添加
    if '.' not in symbol:
        if symbol.startswith('6'):
            symbol = f"{symbol}.SH"
        elif symbol.startswith('0') or symbol.startswith('3'):
            symbol = f"{symbol}.SZ"
        elif symbol.startswith('8'):
            symbol = f"{symbol}.BJ"
        elif symbol.startswith('9'):
            symbol = f"{symbol}.SH"  # B股

    return symbol


def create_mapper(mapping: Dict[str, str], 
                  post_processors: Optional[List[Callable]] = None) -> Callable:
    """
    创建映射函数工厂
    
    Args:
        mapping: 字段映射字典
        post_processors: 后处理函数列表
        
    Returns:
        映射函数
    """
    def mapper(data: dict) -> dict:
        """
        通用映射函数
        
        Args:
            data: 原始数据字典
            
        Returns:
            处理后的结果字典
        """
        clean_data = data.get('data', [])
        if not clean_data:
            return success_result(data=[])
        
        # 应用字段映射
        result = map_fields(clean_data, mapping)
        
        # 应用后处理函数
        if post_processors:
            for processor in post_processors:
                result = processor(result)
        
        return success_result(data=result)
    
    return mapper


# ============================================================================
# 后处理函数
# ============================================================================

def add_concept_name(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加概念名称"""
    for item in result:
        if "concept_name" not in item and "symbol" in item:
            item["concept_name"] = item.get("symbol", "")
    return result


def add_industry_name(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加行业名称"""
    for item in result:
        if "industry_name" not in item and "symbol" in item:
            item["industry_name"] = item.get("symbol", "")
    return result


def add_stat_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加统计日期"""
    today = date.today().isoformat()
    for item in result:
        if "stat_date" not in item:
            item["stat_date"] = today
    return result


def add_rank_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加排名日期"""
    today = date.today().isoformat()
    for item in result:
        if "rank_date" not in item:
            item["rank_date"] = today
    return result


def add_change_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加异动日期"""
    today = date.today().isoformat()
    for item in result:
        if "change_date" not in item:
            item["change_date"] = today
    return result


def normalize_symbols(field_name: str = "symbol") -> Callable:
    """标准化股票代码"""
    def processor(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for item in result:
            if field_name in item:
                item[field_name] = normalize_symbol(item[field_name])
        return result
    return processor


def normalize_leader_stock(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化领涨股票代码"""
    for item in result:
        if "leader_stock" in item and item["leader_stock"]:
            item["leader_stock"] = normalize_symbol(item["leader_stock"])
    return result


def add_symbol_from_code(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从code字段添加symbol字段"""
    for item in result:
        if "symbol" not in item and "code" in item:
            item["symbol"] = normalize_symbol(item["code"])
    return result


# ============================================================================
# 映射函数定义（保持原有函数名和签名）
# ============================================================================

# 1. 概念板块指数日频率数据
map_board_concept_index = create_mapper(
    mapping=BOARD_CONCEPT_INDEX_MAPPING,
    post_processors=[add_concept_name]
)

# 2. 行业板块指数日频率数据
map_board_industry_index = create_mapper(
    mapping=BOARD_INDUSTRY_INDEX_MAPPING,
    post_processors=[add_industry_name]
)

# 3. 行业一览表数据
map_board_industry_summary = create_mapper(
    mapping=BOARD_INDUSTRY_SUMMARY_MAPPING,
    post_processors=[add_stat_date]
)

# 4. 概念板块简介数据
map_board_concept_info = create_mapper(
    mapping=BOARD_CONCEPT_INFO_MAPPING,
    post_processors=[]
)

# 5. 雪球关注排行榜数据
map_stock_hot_follow = create_mapper(
    mapping=STOCK_HOT_FOLLOW_MAPPING,
    post_processors=[
        normalize_symbols("symbol"),
        add_rank_date
    ]
)

# 6. 股票热度历史趋势及粉丝特征数据
map_stock_hot_rank_detail = create_mapper(
    mapping=STOCK_HOT_RANK_DETAIL_MAPPING,
    post_processors=[add_symbol_from_code]
)

# 7. 个股人气榜热门关键词数据
map_stock_hot_keyword = create_mapper(
    mapping=STOCK_HOT_KEYWORD_MAPPING,
    post_processors=[add_stat_date]
)

# 8. 盘口异动数据
map_stock_changes = create_mapper(
    mapping=STOCK_CHANGES_MAPPING,
    post_processors=[normalize_symbols("symbol")]
)

# 9. 当日板块异动详情数据
map_board_change = create_mapper(
    mapping=BOARD_CHANGE_MAPPING,
    post_processors=[
        add_change_date,
        normalize_leader_stock
    ]
)