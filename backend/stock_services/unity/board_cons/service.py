# -*- coding: utf-8 -*-
"""
板块成份股模块
包含行业成份股、概念成份股等查询接口（已切换至datacenter-web + DB回填）
"""

import logging
import requests
from typing import Any, Dict

from system_service import error_result, success_result

logger = logging.getLogger(__name__)

# datacenter-web 公共配置
_DC_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://data.eastmoney.com/',
}
_DC_BASE = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

# 板块类型映射：行业=2, 概念=3
_BOARD_TYPE_MAP = {'行业': '2', '概念': '3'}


def _query_board_constituent(board_code_bk: str, board_type_new: str) -> list:
    """通过 datacenter-web 查询板块成份股"""
    params = {
        'reportName': 'RPT_BOARD_CONSTITUENT',
        'columns': 'SECURITY_CODE,SCODE,BOARD_CODE_BK,BOARD_NAME,SECUCODE',
        'pageNumber': '1',
        'pageSize': '5000',
        'sortTypes': '-1',
        'source': 'WEB',
        'client': 'WEB',
        'filter': f'(BOARD_TYPE_NEW=\"{board_type_new}\")(BOARD_CODE_BK=\"{board_code_bk}\")',
    }
    try:
        r = requests.get(_DC_BASE, params=params, headers=_DC_HEADERS, timeout=10)
        data = r.json()
        if data.get('success') and data.get('result') and data['result'].get('data'):
            return data['result']['data']
        return []
    except Exception as e:
        logger.warning(f"[成份股datacenter] 请求异常: {e}")
        return []


def _lookup_stock_names_from_db(codes: list) -> dict:
    """从本地DB stocks_info 表批量查询股票名称"""
    if not codes:
        return {}
    try:
        from system_service.db_service import DBService
        db = DBService()
        placeholders = ','.join(['%s'] * len(codes))
        sql = f"SELECT symbol, name FROM stocks_info WHERE symbol IN ({placeholders})"
        rows = db.execute_query(sql, tuple(codes))
        return {row['symbol']: row['name'] for row in rows}
    except Exception as e:
        logger.warning(f"[DB查询股票名称] 失败: {e}")
        return {}


def get_stock_board_industry_cons_em(params: dict) -> Dict[str, Any]:
    """
    查询行业板块成份股（datacenter-web + DB 名称回填替代已封 push2）

    Args:
        params: symbol - BK代码（推荐，如 BK0475）或申万行业板块名称（精确匹配）

    Returns:
        统一格式: {"success": bool, "data": list, "message": str}
    """
    symbol = params.get('symbol', '').strip()
    logger.info(f"[行业成份股] 开始查询 symbol={symbol}")

    raw_data = []
    board_name_display = symbol

    # 方式1: BK代码直接查询
    if symbol.upper().startswith('BK') and len(symbol) <= 8:
        raw_data = _query_board_constituent(symbol.upper(), _BOARD_TYPE_MAP['行业'])
        if raw_data:
            board_name_display = raw_data[0].get('BOARD_NAME', symbol)

    # 方式2: 按BOARD_NAME精确匹配
    if not raw_data:
        _bt = _BOARD_TYPE_MAP['行业']
        _filter = f'(BOARD_TYPE_NEW="{_bt}")(BOARD_NAME="{symbol}")'
        params_exact = {
            'reportName': 'RPT_BOARD_CONSTITUENT',
            'columns': 'SECURITY_CODE,SCODE,BOARD_CODE_BK,BOARD_NAME,SECUCODE',
            'pageNumber': '1',
            'pageSize': '5000',
            'sortTypes': '-1',
            'source': 'WEB',
            'client': 'WEB',
            'filter': _filter,
        }
        try:
            r = requests.get(_DC_BASE, params=params_exact, headers=_DC_HEADERS, timeout=10)
            data = r.json()
            if data.get('success') and data.get('result') and data['result'].get('data'):
                raw_data = data['result']['data']
                board_name_display = raw_data[0].get('BOARD_NAME', symbol)
        except Exception as e:
            logger.warning(f"[行业成份股] 名称查询失败: {e}")

    if not raw_data:
        return error_result(message=f"[行业成份股] symbol={symbol} 查询失败（推荐使用BK代码或申万行业名）")

    codes = [item['SECURITY_CODE'] for item in raw_data if item.get('SECURITY_CODE')]
    name_map = _lookup_stock_names_from_db(codes)

    data_list = []
    for item in raw_data:
        code = item.get('SECURITY_CODE', '')
        data_list.append({
            'symbol': code,
            'name': name_map.get(code, ''),
            'board_name': board_name_display,
            'board_type': '行业',
            'board_code': item.get('BOARD_CODE_BK', ''),
        })

    logger.info(f"[行业成份股] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    return success_result(data=data_list)


def get_stock_board_concept_cons_em(params: dict) -> Dict[str, Any]:
    """
    查询概念板块成份股（datacenter-web + DB 名称回填替代已封 push2）

    Args:
        params: symbol - BK代码（推荐，如 BK1071）或申万概念板块名称（精确匹配）

    Returns:
        统一格式: {"success": bool, "data": list, "message": str}
    """
    symbol = params.get('symbol', '').strip()
    logger.info(f"[概念成份股] 开始查询 symbol={symbol}")

    raw_data = []
    board_name_display = symbol

    # 方式1: BK代码直接查询
    if symbol.upper().startswith('BK') and len(symbol) <= 8:
        raw_data = _query_board_constituent(symbol.upper(), _BOARD_TYPE_MAP['概念'])
        if raw_data:
            board_name_display = raw_data[0].get('BOARD_NAME', symbol)

    # 方式2: 按BOARD_NAME精确匹配
    if not raw_data:
        _bt = _BOARD_TYPE_MAP['概念']
        _filter = f'(BOARD_TYPE_NEW="{_bt}")(BOARD_NAME="{symbol}")'
        params_exact = {
            'reportName': 'RPT_BOARD_CONSTITUENT',
            'columns': 'SECURITY_CODE,SCODE,BOARD_CODE_BK,BOARD_NAME,SECUCODE',
            'pageNumber': '1',
            'pageSize': '5000',
            'sortTypes': '-1',
            'source': 'WEB',
            'client': 'WEB',
            'filter': _filter,
        }
        try:
            r = requests.get(_DC_BASE, params=params_exact, headers=_DC_HEADERS, timeout=10)
            data = r.json()
            if data.get('success') and data.get('result') and data['result'].get('data'):
                raw_data = data['result']['data']
                board_name_display = raw_data[0].get('BOARD_NAME', symbol)
        except Exception as e:
            logger.warning(f"[概念成份股] 名称查询失败: {e}")

    if not raw_data:
        return error_result(message=f"[概念成份股] symbol={symbol} 查询失败（推荐使用BK代码或申万概念名）")

    codes = [item['SECURITY_CODE'] for item in raw_data if item.get('SECURITY_CODE')]
    name_map = _lookup_stock_names_from_db(codes)

    data_list = []
    for item in raw_data:
        code = item.get('SECURITY_CODE', '')
        data_list.append({
            'symbol': code,
            'name': name_map.get(code, ''),
            'board_name': board_name_display,
            'board_type': '概念',
            'board_code': item.get('BOARD_CODE_BK', ''),
        })

    logger.info(f"[概念成份股] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    return success_result(data=data_list)