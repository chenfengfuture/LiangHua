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

import logging
from typing import Any, Dict, List

from system_service.service_result import error_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import map_stock_basic, set_stock_delist


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
    import akshare as ak
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


def get_stock_individual_basic_info_xq(params) -> List[Dict[str, Any]]:
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
    import akshare as ak
    symbol = params.get('symbol')
    logger.info(f"[雪球公司概况] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_individual_basic_info_xq,
        symbol=symbol,
        token=None, timeout=None,
        log_prefix="雪球公司概况"
    )
    print('12121', df)
    if not df:
        return error_result(message=f"[雪球公司概况] symbol={symbol} 查询失败")

    logger.info(f"[雪球公司概况] symbol={symbol} 查询成功")
    # 返回业务数据
    result = map_stock_basic(df, 'sh', '主板A股')
    return result

def get_all_stocks(params) -> List[Dict[str, str]]:
    """
    查询全市场A股股票代码列表（东方财富接口）
    
    接口: akshare.stock_info_a_code_name
    目标地址: 东方财富数据中心
    描述: 获取所有A股上市公司的代码和名称列表
    
    Returns:
        股票代码列表，格式: [{"code": "000001", "name": "平安银行"}, ...]
    
    注意: 数据量较大（约5500+条记录），调用时请耐心等待。
    """
    import akshare as ak
    logger.info("[全市场股票代码] 开始查询所有A股代码")

    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_info_a_code_name,
        log_prefix="全市场A股股票代码"
    )

    if not df:
        return error_result(message=f"[全市场股票代码] 查询失败，数据条数={len(df['data'])}")
    print('df', df['data'][0])
    logger.info(f"[全市场股票代码] 查询成功，共获取 {len(df)} 条A股代码")
    # 返回业务数据
    all_stocks = map_stock_basic(df, 'all')
    return all_stocks


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
    """
    import akshare as ak
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
    result = map_stock_basic(df, 'sh', '主板A股')
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

    """
    import akshare as ak
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

    """
    import akshare as ak
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

    """
    import akshare as ak
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
    """
    import akshare as ak
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
