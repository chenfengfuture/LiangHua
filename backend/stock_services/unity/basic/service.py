# -*- coding: utf-8 -*-
"""
股票基本信息模块
包含个股基础信息查询接口

统一格式：
1. 所有函数返回统一格式：{"success": bool, "data": list, "message": str}
2. 使用request_akshare_data进行安全调用和重试
3. 异常处理：任何错误都返回success=False，不抛出异常
4. 统一日志记录（logger.info / logger.error）
"""

import json
import logging
from typing import Any, Dict, List

import akshare as ak

from system_service.service_result import error_result, success_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import *


logger = logging.getLogger(__name__)


def get_stock_info_em(params) -> Dict[str, Any]:
    """
    查询指定股票代码的个股基础信息（东方财富接口）

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "000001"（平安银行），"603777"（来伊份）

    Returns:
        业务数据字典，包含股票信息
    """
    symbol = params.get('symbol')
    logger.info(f"[个股信息查询] 开始查询 symbol={symbol}")
    # 调用AKShare接口获取个股信息
    df = request_akshare_data(
        ak.stock_individual_info_em,
        symbol=symbol,
        log_prefix="个股信息查询"
    )
    print('df', df)
    # 处理数据
    data_list = []
    if 'item' in df.columns and 'value' in df.columns:
        for _, row in df.iterrows():
            item = row['item']
            value = row['value']
            if not isinstance(value, (int, float, str, bool, type(None))):
                value = str(value)
            data_list.append({"item": item, "value": value})
    else:
        data_list = df.to_dict(orient='records')
    print('data_list', data_list)
    # 转换为字典格式
    data_dict = {}
    for entry in data_list:
        if isinstance(entry, dict) and 'item' in entry and 'value' in entry:
            key = entry['item']
            val = entry['value']
            data_dict[key] = val
        elif isinstance(entry, dict):
            data_dict.update(entry)

    data_dict['symbol'] = symbol

    logger.info(f"[个股信息查询] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

    mapped_data = map_stock_basic(data_dict)

    # 返回业务数据，由全局异常处理器处理异常
    return mapped_data


def get_stock_info_json(symbol: str) -> str:
    """
    查询个股信息并返回 JSON 字符串（方便直接返回 HTTP 响应）

    Args:
        symbol: 股票代码

    Returns:
        JSON 字符串，包含业务数据
    """
    # 调用 get_stock_info 获取业务数据
    data = get_stock_info_em(symbol)
    
    # 返回 JSON 字符串
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_stock_individual_basic_info_xq(symbol: str) -> List[Dict[str, Any]]:
    """
    查询雪球财经-个股1公司概况

    接口: akshare.stock_individual_basic_info_xq
    目标地址: https://xueqiu.com/snowman/S/SH601127/detail#/GSJJ

    描述: 雪球财经-个股-公司概况-公司简介

    Args:
        symbol: 股票代码，需带市场前缀，如 "SH601127"

    Returns:
        公司概况数据列表
    """
    logger.info(f"[雪球公司概况] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = ak.stock_individual_basic_info_xq(symbol=symbol)

    # 处理返回结果
    data_list = []
    
    if result is None:
        logger.warning(f"[雪球公司概况] symbol={symbol} 返回为None")
        return data_list  # 返回空列表

    elif isinstance(result, dict):
        data_list = [result] if result else []

    elif isinstance(result, list):
        data_list = result

    logger.info(f"[雪球公司概况] symbol={symbol} 查询成功，数据条数={len(data_list)}")

    # 返回业务数据
    return data_list


def get_all_stock_codes() -> List[Dict[str, str]]:
    """
    查询全市场A股股票代码列表（东方财富接口）
    
    接口: akshare.stock_info_a_code_name
    目标地址: 东方财富数据中心
    描述: 获取所有A股上市公司的代码和名称列表
    
    Returns:
        股票代码列表，格式: [{"code": "000001", "name": "平安银行"}, ...]
    
    注意: 数据量较大（约5500+条记录），调用时请耐心等待。
    """
    logger.info("[全市场股票代码] 开始查询所有A股代码")
    
    # 调用AKShare接口获取所有A股代码
    df = ak.stock_info_a_code_name()
    
    if df.empty:
        logger.warning("[全市场股票代码] 返回数据为空")
        return []  # 返回空列表
    
    # 转换为字典列表
    data_list = []
    for _, row in df.iterrows():
        record = {
            "code": str(row['code']).strip(),
            "name": str(row['name']).strip() if pd.notna(row['name']) else ""
        }
        data_list.append(record)
    
    logger.info(f"[全市场股票代码] 查询成功，共获取 {len(data_list)} 条A股代码")
    
    # 返回业务数据
    return data_list


def get_all_stock_codes_json() -> str:
    """
    查询全市场A股股票代码列表并返回JSON字符串
    
    Returns:
        JSON字符串，包含股票代码列表
    """
    # 调用 get_all_stock_codes 获取业务数据
    data = get_all_stock_codes()
    
    # 返回 JSON 字符串
    return json.dumps(data, ensure_ascii=False, indent=2)


def stock_info_sh_name_code(params) -> Dict[str, Any]:
    """
    上海证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_sh_name_code
    目标地址: https://www.sse.com.cn/assortment/stock/list/share/
    描述: 获取上海证券交易所股票代码和简称数据
    限量: 单次获取所有上海证券交易所股票代码和简称数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票板块类型，可选值：
                - "主板A股": 主板A股
                - "主板B股": 主板B股  
                - "科创板": 科创板
                默认: "主板A股"
    
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股票列表数据，已映射到stocks_info表结构
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol', '主板A股')
    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_sh_name_code,
        symbol=symbol,
        log_prefix="上交所股票列表"
    )
    
    if not df:
        return error_result(message=f"[上交所股票列表] symbol={symbol} 查询失败，数据条数={len(df)}")
    
    logger.info(f"[上交所股票列表] symbol={symbol} 查询成功，数据条数={len(df['data'])}")
    # 返回业务数据
    result = map_stock_basic(df, '主板A股', 'sh')
    
    return result


def stock_info_sz_name_code(params: dict) -> Dict[str, Any]:
    """
    深圳证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_sz_name_code
    目标地址: https://www.szse.cn/market/product/stock/list/index.html
    描述: 获取深圳证券交易所股票代码和简称数据
    限量: 单次获取深圳证券交易所股票代码和简称数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票列表类型，可选值：
                - "A股列表": A股列表
                - "B股列表": B股列表
                - "AB股列表": AB股列表
                - "CDR列表": CDR列表
                默认: "A股列表"
    
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股票列表数据，已映射到stocks_info表结构
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol', 'A股列表')
    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_sz_name_code,
        symbol=symbol,
        log_prefix="深交所股票列表"
    )
    
    if not df:
        return error_result(message=f"[深交所股票列表] symbol={symbol} 查询失败，数据条数={len(df)}")
    
    logger.info(f"[深交所股票列表] symbol={symbol} 查询成功，数据条数={len(df['data'])}")
    # 返回业务数据
    result = map_stock_basic(df, 'sz', symbol)
    
    return result


def stock_info_bj_name_code(params: dict) -> Dict[str, Any]:
    """
    北京证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_bj_name_code
    目标地址: https://www.bse.cn/nq/listedcompany.html
    描述: 获取北京证券交易所股票代码和简称数据
    限量: 单次获取北京证券交易所所有的股票代码和简称数据
    
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 股票列表数据，已映射到stocks_info表结构
            "message": str        # 成功或错误信息
        }
    """
    logger.info("[北交所股票列表] 开始查询")
    
    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_bj_name_code,
        log_prefix="北交所股票列表"
    )
    
    if not df:
        return error_result(message="[北交所股票列表] 查询失败")
    
    logger.info(f"[北交所股票列表] 查询成功，数据条数={len(df['data'])}")
    # 返回业务数据
    result = map_stock_basic(df, 'bj', '北交所')
    return result


def stock_info_sz_delist(params: dict) -> Dict[str, Any]:
    """
    深圳证券交易所终止/暂停上市股票
    
    接口: akshare.stock_info_sz_delist
    目标地址: https://www.szse.cn/market/stock/suspend/index.html
    描述: 获取深圳证券交易所终止/暂停上市股票数据
    限量: 单次获取深圳证券交易所终止/暂停上市数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票状态类型，可选值：
                - "终止上市公司": 终止上市公司
                - "暂停上市公司": 暂停上市公司
                默认: "终止上市公司"
    
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 退市股票列表数据，已映射到stocks_info表结构
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol', '终止上市公司')
    logger.info(f"[深交所退市股票] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_sz_delist,
        symbol=symbol,
        log_prefix="深交所股票列表"
    )
    if not df:
        return error_result(message=f"[深交所退市股票] symbol={symbol} 查询失败，数据条数={len(df)}")
    
    logger.info(f"[深交所退市股票] symbol={symbol} 查询成功，数据条数={len(df['data'])}")
    # 返回业务数据
    sz_delist = map_stock_basic(df, 'sz_delist')
    result = set_stock_delist(sz_delist)
    return result


def stock_info_sh_delist(params: dict) -> Dict[str, Any]:
    """
    上海证券交易所暂停/终止上市股票

    接口: akshare.stock_info_sh_delist
    目标地址: https://www.sse.com.cn/assortment/stock/list/delisting/
    描述: 获取上海证券交易所暂停/终止上市股票数据
    限量: 单次获取上海证券交易所暂停/终止上市股票
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 市场类型，可选值：
                - "全部": 全部市场
                - "沪市": 沪市主板
                - "科创板": 科创板
                默认: "全部"
    
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 退市股票列表数据，已映射到stocks_info表结构
            "message": str        # 成功或错误信息
        }
    """
    symbol = params.get('symbol', '全部')
    logger.info(f"[上交所退市股票] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_sh_delist,
        symbol=symbol,
        log_prefix="上交所退市股票"
    )
    
    if not df:
        return error_result(message=f"[上交所退市股票] symbol={symbol} 查询失败，数据条数={len(df['data'])}")
    
    logger.info(f"[上交所退市股票] symbol={symbol} 查询成功，数据条数={len(df['data'])}")
    # 返回业务数据
    sh_delist = map_stock_basic(df, 'sh_delist')
    result = set_stock_delist(sh_delist)
    return result
