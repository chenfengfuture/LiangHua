# -*- coding: utf-8 -*-
"""
技术选股排名模块
包含创新高、连续上涨、持续放量、向上突破等技术选股指标
"""

import logging
from typing import Any, Dict

from system_service.service_result import error_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import map_stock_stat_date, map_stock_ask

logger = logging.getLogger(__name__)


def get_stock_rank_cxg_ths(params) -> Dict[str, Any]:
    """
    同花顺技术指标-创新高数据查询接口
    
    接口: stock_rank_cxg_ths
    目标地址: https://data.10jqka.com.cn/rank/cxg/
    描述: 同花顺-数据中心-技术选股-创新高
    限量: 单次指定 symbol 的所有数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 创新高类型，可选值: "创月新高", "半年新高", "一年新高", "历史新高"

    """
    import akshare as ak
    symbol = params.get('symbol', '创月新高')

    logger.info(f"[同花顺创新高] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_cxg_ths,
        symbol=symbol,
        log_prefix="同花顺创新高"
    )
    print('result', result)
    if not result:
        return error_result(message=f"[同花顺创新高] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[同花顺创新高] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_rank_cxd_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-创新低数据

    接口: akshare.stock_rank_cxd_ths
    目标地址: https://data.10jqka.com.cn/rank/cxd/

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 新低类型，可选值: "创月新低", "半年新低", "一年新低", "历史新低"

    """
    import akshare as ak
    symbol = params.get('symbol', '历史新低')

    logger.info(f"[同花顺创新低] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_cxd_ths,
        symbol=symbol,
        log_prefix="同花顺创新低"
    )
    if not result:
        return error_result(message=f"[同花顺创新低] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[同花顺创新低] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_rank_lxsz_ths(params) -> Dict[str, Any]:
    """
    同花顺技术选股-连续上涨数据查询接口
    
    接口: stock_rank_lxsz_ths
    目标地址: https://data.10jqka.com.cn/rank/lxsz/
    描述: 同花顺-数据中心-技术选股-连续上涨
    限量: 单次返回所有数据
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺连续上涨] 开始查询连续上涨数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_lxsz_ths,
        log_prefix="同花顺连续上涨"
    )
    if not result:
        return error_result(message="[同花顺连续上涨] 查询失败，数据为空")

    logger.info(f"[同花顺连续上涨] 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['stats_type']= '连续上涨'
    return mapped_result


def get_stock_rank_lxxd_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-连续下跌数据

    接口: akshare.stock_rank_lxxd_ths
    目标地址: https://data.10jqka.com.cn/rank/lxxd/

    Args:
        params: 参数字典（无实际参数，仅保持统一格式）
    """
    import akshare as ak
    logger.info("[同花顺连续下跌] 开始查询")

    # 调用AKShare接口（无参数）
    result = request_akshare_data(
        ak.stock_rank_lxxd_ths,
        log_prefix="同花顺连续下跌"
    )

    if not result:
        return error_result(message="[同花顺连续下跌] 查询失败，数据为空")

    logger.info(f"[同花顺连续下跌] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['stats_type']= '连续下跌'
    return mapped_result


def get_stock_rank_cxfl_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续放量数据
    
    接口: akshare.stock_rank_cxfl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxfl/
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺持续放量] 开始查询持续放量数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_cxfl_ths,
        log_prefix="同花顺持续放量"
    )
    if not result:
        return error_result(message="[同花顺持续放量] 查询失败，数据为空")

    logger.info(f"[同花顺持续放量] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['volume_type'] = "持续放量"
    return mapped_result


def get_stock_rank_cxsl_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续缩量数据
    
    接口: akshare.stock_rank_cxsl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxsl/
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺持续缩量] 开始查询持续缩量数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_cxsl_ths,
        log_prefix="同花顺持续缩量"
    )
    if not result:
        return error_result(message="[同花顺持续缩量] 查询失败，数据为空")

    logger.info(f"[同花顺持续缩量] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['volume_type'] = "持续缩量"
    return mapped_result


def get_stock_rank_xstp_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-向上突破数据
    
    接口: akshare.stock_rank_xstp_ths
    目标地址: https://data.10jqka.com.cn/rank/xstp/
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 均线周期类型，可选值: "5日均线", "10日均线", "20日均线", 
              "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"

    """
    import akshare as ak
    symbol = params.get('symbol', '500日均线')

    logger.info(f"[同花顺向上突破] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_xstp_ths,
        symbol=symbol,
        log_prefix="同花顺向上突破"
    )
    if not result:
        return error_result(message=f"[同花顺向上突破] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[同花顺向上突破] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['ma_period_type'] = symbol
        item['breakthrough_type'] = '向上突破'
    return mapped_result


def get_stock_rank_xxtp_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-向下突破数据

    接口: akshare.stock_rank_xxtp_ths
    目标地址: https://data.10jqka.com.cn/rank/xxtp/

    Args:
        params: 参数字典（无实际参数，仅保持统一格式）
    """
    import akshare as ak
    symbol = params.get('symbol', '500日均线')
    logger.info("[同花顺向下突破] 开始查询")

    result = request_akshare_data(
        ak.stock_rank_xstp_ths,
        symbol=symbol,
        log_prefix="同花顺向下突破"
    )
    if not result:
        return error_result(message="[同花顺向下突破] 查询失败，数据为空")

    logger.info(f"[同花顺向下突破] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    for item in mapped_result['data']:
        item['ma_period_type'] = symbol
        item['breakthrough_type'] = '向下突破'
    return mapped_result

def get_stock_rank_ljqs_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐升数据
    
    接口: akshare.stock_rank_ljqs_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqs/
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺量价齐升] 开始查询量价齐升数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_ljqs_ths,
        log_prefix="同花顺量价齐升"
    )
    if not result:
        return error_result(message="[同花顺量价齐升] 查询失败，数据为空")

    logger.info(f"[同花顺量价齐升] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_rank_ljqd_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐跌数据
    
    接口: akshare.stock_rank_ljqd_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqd/
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺量价齐跌] 开始查询量价齐跌数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_ljqd_ths,
        log_prefix="同花顺量价齐跌"
    )
    if not result:
        return error_result(message="[同花顺量价齐跌] 查询失败，数据为空")

    logger.info(f"[同花顺量价齐跌] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result


def get_stock_rank_xzjp_ths(params) -> Dict[str, Any]:
    """
    查询同花顺技术选股-险资举牌数据
    
    接口: akshare.stock_rank_xzjp_ths
    目标地址: https://data.10jqka.com.cn/financial/xzjp/
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    """
    import akshare as ak
    logger.info("[同花顺险资举牌] 开始查询险资举牌数据")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_rank_xzjp_ths,
        log_prefix="同花顺险资举牌"
    )
    if not result:
        return error_result(message="[同花顺险资举牌] 查询失败，数据为空")

    logger.info(f"[同花顺险资举牌] 查询成功，数据条数={len(result.get('data', []))}")
    print('result', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result
