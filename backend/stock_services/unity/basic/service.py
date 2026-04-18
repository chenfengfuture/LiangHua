# -*- coding: utf-8 -*-
"""
股票基本信息模块
包含个股基础信息查询接口

重构说明：
1. 使用全局异常处理器处理所有异常
2. 服务函数直接抛出异常，由全局异常处理器捕获
3. 返回结果使用service_result模块统一构建
"""

import json
import logging
from typing import Any, Dict, List

import akshare as ak
import pandas as pd

from stock_services.unity.utils import _convert_dataframe_to_list, safe_call_with_retry
from system_service.exception_handler import (
    ValidationException,
    DataNotFoundError,
    ExternalServiceException,
    DatabaseException
)
from system_service.service_result import success_result, error_result

logger = logging.getLogger(__name__)


def get_stock_info(symbol: str) -> Dict[str, Any]:
    """
    查询指定股票代码的个股基础信息（东方财富接口）

    Args:
        symbol: 股票代码，如 "000001"（平安银行），"603777"（来伊份）

    Returns:
        业务数据字典，包含股票信息
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValidationException(
            message="股票代码必须为非空字符串",
            details={"symbol": symbol or ""}
        )

    logger.info(f"[个股信息查询] 开始查询 symbol={symbol}")

    # 调用AKShare接口获取个股信息
    df = safe_call_with_retry(
        ak.stock_individual_info_em,
        symbol=symbol,
        max_retries=3,
        logger_name="个股信息查询"
    )

    # 数据验证
    if df is None or df.empty:
        raise DataNotFoundError(
            message=f"未找到股票代码 {symbol} 的信息",
            details={"symbol": symbol}
        )

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

    # 返回业务数据，由全局异常处理器处理异常
    return data_dict


def get_stock_info_json(symbol: str) -> str:
    """
    查询个股信息并返回 JSON 字符串（方便直接返回 HTTP 响应）

    Args:
        symbol: 股票代码

    Returns:
        JSON 字符串，包含业务数据
    """
    # 调用 get_stock_info 获取业务数据
    data = get_stock_info(symbol)
    
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
    # 参数验证
    if not symbol:
        raise ValidationException(
            message="股票代码不能为空",
            details={"symbol": symbol}
        )

    logger.info(f"[雪球公司概况] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = ak.stock_individual_basic_info_xq(symbol=symbol)

    # 处理返回结果
    data_list = []
    
    if result is None:
        logger.warning(f"[雪球公司概况] symbol={symbol} 返回为None")
        return data_list  # 返回空列表

    if hasattr(result, 'empty'):
        df = result
        if df is None or len(df) == 0:
            logger.warning(f"[雪球公司概况] symbol={symbol} 返回数据为空")
            return data_list
        data_list = _convert_dataframe_to_list(df, "[雪球公司概况]")

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


def stock_info_sh_name_code(symbol: str = "主板A股") -> List[Dict[str, Any]]:
    """
    上海证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_sh_name_code
    目标地址: https://www.sse.com.cn/assortment/stock/list/share/
    描述: 获取上海证券交易所股票代码和简称数据
    限量: 单次获取所有上海证券交易所股票代码和简称数据
    
    Args:
        symbol: 股票板块类型，可选值：
            - "主板A股": 主板A股
            - "主板B股": 主板B股  
            - "科创板": 科创板
            默认: "主板A股"
    
    Returns:
        股票列表数据，格式: [{"证券代码": "600000", "证券简称": "浦发银行", "上市日期": "1999-11-10", ...}, ...]
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValidationException(
            message="symbol参数必须为非空字符串",
            details={"symbol": symbol or ""}
        )
    
    valid_symbols = {"主板A股", "主板B股", "科创板"}
    if symbol not in valid_symbols:
        raise ValidationException(
            message=f"symbol参数必须为以下值之一: {', '.join(sorted(valid_symbols))}",
            details={"symbol": symbol}
        )
    
    logger.info(f"[上交所股票列表] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    df = safe_call_with_retry(
        ak.stock_info_sh_name_code,
        symbol=symbol,
        max_retries=3,
        logger_name="上交所股票列表"
    )
    
    # 数据验证
    if df is None:
        logger.warning(f"[上交所股票列表] symbol={symbol} 返回为None")
        return []  # 返回空列表
    
    if df.empty:
        logger.warning(f"[上交所股票列表] symbol={symbol} 返回数据为空")
        return []  # 返回空列表
    
    # 转换数据格式
    data_list = _convert_dataframe_to_list(df, "[上交所股票列表]")
    
    logger.info(f"[上交所股票列表] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    
    # 返回业务数据
    return data_list


def stock_info_sz_name_code(symbol: str = "A股列表") -> List[Dict[str, Any]]:
    """
    深圳证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_sz_name_code
    目标地址: https://www.szse.cn/market/product/stock/list/index.html
    描述: 获取深圳证券交易所股票代码和简称数据
    限量: 单次获取深圳证券交易所股票代码和简称数据
    
    Args:
        symbol: 股票列表类型，可选值：
            - "A股列表": A股列表
            - "B股列表": B股列表
            - "AB股列表": AB股列表
            - "CDR列表": CDR列表
            默认: "A股列表"
    
    Returns:
        股票列表数据，格式: [{"A股代码": "000001", "A股简称": "平安银行", "A股上市日期": "1991-04-03", ...}, ...]
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValidationException(
            message="symbol参数必须为非空字符串",
            details={"symbol": symbol or ""}
        )
    
    valid_symbols = {"A股列表", "B股列表", "AB股列表", "CDR列表"}
    if symbol not in valid_symbols:
        raise ValidationException(
            message=f"symbol参数必须为以下值之一: {', '.join(sorted(valid_symbols))}",
            details={"symbol": symbol}
        )
    
    logger.info(f"[深交所股票列表] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    df = safe_call_with_retry(
        ak.stock_info_sz_name_code,
        symbol=symbol,
        max_retries=3,
        logger_name="深交所股票列表"
    )
    
    # 数据验证
    if df is None:
        logger.warning(f"[深交所股票列表] symbol={symbol} 返回为None")
        return []  # 返回空列表
    
    if df.empty:
        logger.warning(f"[深交所股票列表] symbol={symbol} 返回数据为空")
        return []  # 返回空列表
    
    # 转换数据格式
    data_list = _convert_dataframe_to_list(df, "[深交所股票列表]")
    
    logger.info(f"[深交所股票列表] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    
    # 返回业务数据
    return data_list


def stock_info_bj_name_code() -> List[Dict[str, Any]]:
    """
    北京证券交易所股票代码和简称数据
    
    接口: akshare.stock_info_bj_name_code
    目标地址: https://www.bse.cn/nq/listedcompany.html
    描述: 获取北京证券交易所股票代码和简称数据
    限量: 单次获取北京证券交易所所有的股票代码和简称数据
    
    Returns:
        股票列表数据，格式: [{"证券代码": "430047", "证券简称": "诺思兰德", "总股本(万股)": "12345", ...}, ...]
    
    使用说明：
        1. 该接口获取北京证券交易所所有股票列表
        2. 包含证券代码、证券简称、总股本等基本信息
        3. 数据来源为北京证券交易所官网
        4. 可用于获取北交所股票基础数据
        5. 注意：北交所股票代码以8开头
    """
    logger.info("[北交所股票列表] 开始查询")
    
    # 调用AKShare接口
    df = safe_call_with_retry(
        ak.stock_info_bj_name_code,
        max_retries=3,
        logger_name="北交所股票列表"
    )
    
    # 数据验证
    if df is None:
        logger.warning("[北交所股票列表] 返回为None")
        return []  # 返回空列表
    
    if df.empty:
        logger.warning("[北交所股票列表] 返回数据为空")
        return []  # 返回空列表
    
    # 转换数据格式
    data_list = _convert_dataframe_to_list(df, "[北交所股票列表]")
    
    logger.info(f"[北交所股票列表] 查询成功，数据条数={len(data_list)}")
    
    # 返回业务数据
    return data_list


def stock_info_sz_delist(symbol: str = "终止上市公司") -> List[Dict[str, Any]]:
    """
    深圳证券交易所终止/暂停上市股票
    
    接口: akshare.stock_info_sz_delist
    目标地址: https://www.szse.cn/market/stock/suspend/index.html
    描述: 获取深圳证券交易所终止/暂停上市股票数据
    限量: 单次获取深圳证券交易所终止/暂停上市数据
    
    Args:
        symbol: 股票状态类型，可选值：
            - "终止上市公司": 终止上市公司
            - "暂停上市公司": 暂停上市公司
            默认: "终止上市公司"
    
    Returns:
        退市股票列表数据，格式: [{"公司代码": "000003", "公司简称": "PT金田A", "终止上市日期": "2002-09-05", ...}, ...]
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValidationException(
            message="symbol参数必须为非空字符串",
            details={"symbol": symbol or ""}
        )
    
    valid_symbols = {"终止上市公司", "暂停上市公司"}
    if symbol not in valid_symbols:
        raise ValidationException(
            message=f"symbol参数必须为以下值之一: {', '.join(sorted(valid_symbols))}",
            details={"symbol": symbol}
        )
    
    logger.info(f"[深交所退市股票] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    df = safe_call_with_retry(
        ak.stock_info_sz_delist,
        symbol=symbol,
        max_retries=3,
        logger_name="深交所退市股票"
    )
    
    # 数据验证
    if df is None:
        logger.warning(f"[深交所退市股票] symbol={symbol} 返回为None")
        return []  # 返回空列表
    
    if df.empty:
        logger.warning(f"[深交所退市股票] symbol={symbol} 返回数据为空")
        return []  # 返回空列表
    
    # 转换数据格式
    data_list = _convert_dataframe_to_list(df, "[深交所退市股票]")
    
    logger.info(f"[深交所退市股票] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    
    # 返回业务数据
    return data_list


def stock_info_sh_delist(symbol: str = "全部") -> List[Dict[str, Any]]:
    """
    上海证券交易所暂停/终止上市股票
    
    接口: akshare.stock_info_sh_delist
    目标地址: https://www.sse.com.cn/assortment/stock/list/delisting/
    描述: 获取上海证券交易所暂停/终止上市股票数据
    限量: 单次获取上海证券交易所暂停/终止上市股票
    
    Args:
        symbol: 市场类型，可选值：
            - "全部": 全部市场
            - "沪市": 沪市主板
            - "科创板": 科创板
            默认: "全部"
    
    Returns:
        退市股票列表数据，格式: [{"公司代码": "600001", "公司简称": "邯郸钢铁", "终止上市日期": "2009-12-29", ...}, ...]
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        raise ValidationException(
            message="symbol参数必须为非空字符串",
            details={"symbol": symbol or ""}
        )
    
    valid_symbols = {"全部", "沪市", "科创板"}
    if symbol not in valid_symbols:
        raise ValidationException(
            message=f"symbol参数必须为以下值之一: {', '.join(sorted(valid_symbols))}",
            details={"symbol": symbol}
        )
    
    logger.info(f"[上交所退市股票] 开始查询 symbol={symbol}")
    
    # 调用AKShare接口
    df = safe_call_with_retry(
        ak.stock_info_sh_delist,
        symbol=symbol,
        max_retries=3,
        logger_name="上交所退市股票"
    )
    
    # 数据验证
    if df is None:
        logger.warning(f"[上交所退市股票] symbol={symbol} 返回为None")
        return []  # 返回空列表
    
    if df.empty:
        logger.warning(f"[上交所退市股票] symbol={symbol} 返回数据为空")
        return []  # 返回空列表
    
    # 转换数据格式
    data_list = _convert_dataframe_to_list(df, "[上交所退市股票]")
    
    logger.info(f"[上交所退市股票] symbol={symbol} 查询成功，数据条数={len(data_list)}")
    
    # 返回业务数据
    return data_list
