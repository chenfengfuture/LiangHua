#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段映射工具模块

提供通用的字段映射功能，用于将不同数据源返回的字段映射到标准数据表结构。

主要功能：
1. 灵活的字段映射规则配置
2. 支持多种映射策略（精确匹配、模糊匹配、正则表达式、转换函数）
3. 支持字段值转换和格式化
4. 支持批量映射
5. 提供预设的映射规则库

设计原则：
- 配置驱动：通过配置规则实现映射，无需硬编码
- 可扩展：支持自定义映射规则和转换函数
- 可维护：集中管理映射关系，便于维护和更新
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from system_service.service_result import error_result, success_result


logger = logging.getLogger(__name__)

# 全市场统一分类映射表（只需定义一次，全局复用）
STOCK_TYPE_MAP = {
    # 上交所
    "主板A股": "A股",
    "主板B股": "B股",
    "科创板": "科创板",
    # 深交所
    "A股列表": "A股",
    "B股列表": "B股",
    "CDR列表": "CDR",
    "北交所": '北交所A股'
}

def map_fields(data: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    批量字段映射：源key → 目标库字段
    """
    return [
        {mapping[key]: value for key, value in item.items() if key in mapping}
        for item in data
    ]


def map_stock_basic(data: dict, source: str = "sh", source_symbol: str = None ) -> List[Dict[str, Any]]:
    """
    股票基础信息专用映射（适配你当前接口数据）
    源字段 → 数据库字段

    :param data: 原始数据
    :param source: 数据源标记 sh/sz/bj/delist
    :param source_symbol: stock_type
    :return: 格式化后的股票列表
    """
    # 映射字典统一管理
    mapping_map = {
        "sh": {
            "证券代码": "symbol",
            "证券简称": "name",
            "公司全称": "full_name",
            "上市日期": "list_date"
        },
        "sz": {
            "A股代码": "symbol",
            "A股简称": "name",
            "公司全称": "full_name",
            "A股上市日期": "list_date",
            "所属行业": "industry",
        },
        "bj": {
            "证券代码": "symbol",
            "证券简称": "name",
            "上市日期": "list_date",
            "所属行业": "industry",
        },
        "delist": {
            "公司代码": "symbol",
            "公司简称": "name",
            "终止上市日期": "list_date",
            "暂停上市日期": "list_date",
            "上市日期": "list_date",
        },
        "sz_delist": {
            "证券代码": "symbol",
            "证券简称": "name",
        },
        "sh_delist": {
            "公司代码": "symbol",
            "公司简称": "name",
        },
    }

    # 获取数据
    clean_data = data.get('data', [])
    if not clean_data:
        return success_result(data=[])

    # 根据 source 选择映射
    result = map_fields(clean_data, mapping_map[source])
    if source in ['sh', 'sz', 'bj']:
        # 设置市场
        for item in result:
            item["market"] = get_stock_market(item.get("symbol", ""))
            if source_symbol:
                item["market_type"] = STOCK_TYPE_MAP[source_symbol]

    return success_result(data=result)

def map_stock_bj_basic(data: dict) -> List[Dict[str, Any]]:
    """
    北交所股票基础信息专用映射
    源字段 → 数据库字段
    
    北交所接口返回字段示例（推测）：
    - "证券代码" → "symbol"
    - "证券简称" → "name"
    - "公司全称" → "full_name"
    - "上市日期" → "list_date"
    """
    # 北交所字段映射
    bj_mapping = {
        "证券代码": "symbol",
        "证券简称": "name",
        "公司全称": "full_name",
        "上市日期": "list_date",
        "所属行业": "industry",
    }
    
    clean_data = data.get('data', [])
    
    if clean_data:
        result = map_fields(clean_data, bj_mapping)
    else:
        result = []
    
    for item in result:
        symbol = item.get("symbol", "")
        item["market"] = get_stock_market(symbol)
    return success_result(data=result)


def set_stock_delist(data: dict):
    stock_data = data.get('data', [])
    for item in stock_data:
        item["is_active"] = 0
    return success_result(data=stock_data)

def map_stock_delist_basic(data: dict) -> List[Dict[str, Any]]:
    """
    退市股票基础信息专用映射
    源字段 → 数据库字段
    
    退市股票接口返回字段示例（推测）：
    - "公司代码" → "symbol"
    - "公司简称" → "name"
    - "终止上市日期" → "list_date"（但需要标记为退市）
    """
    # 退市股票字段映射
    delist_mapping = {
        "公司代码": "symbol",
        "公司简称": "name",
        "终止上市日期": "list_date",
        "暂停上市日期": "list_date",
        "上市日期": "list_date",
    }
    
    clean_data = data.get('data', [])
    
    if clean_data:
        result = map_fields(clean_data, delist_mapping)
        
        # 标记为退市股票
        for item in result:
            symbol = item.get("symbol", "")
            item["market"] = get_stock_market(symbol)
            item["is_active"] = 0  # 标记为退市
    else:
        result = []
    
    return success_result(data=result)


def get_stock_market(symbol: str) -> str:
    """
    根据股票代码判断所属市场
    返回：SH / SZ / BJ / None
    """
    if not symbol or not isinstance(symbol, str):
        return None
    symbol = symbol.strip()
    # 沪市 A 股
    if symbol.startswith(('600', '601', '603', '605', '688', '689')):
        return 'SH'
    # 深市 A 股（主板、创业板）
    elif symbol.startswith(('000', '001', '002', '003', '300', '301')):
        return 'SZ'
    # 北交所
    elif symbol.startswith(('8', '43')):
        return 'BJ'
    # 沪市 B 股
    elif symbol.startswith('900'):
        return 'SHB'
    # 深市 B 股
    elif symbol.startswith('200'):
        return 'SZB'
    return None



