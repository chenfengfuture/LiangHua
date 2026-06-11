# -*- coding: utf-8 -*-
"""
板块概念模块
包含板块指数、行业信息、概念信息、股票热度、盘口异动等查询接口

统一格式：
1. 所有函数返回统一格式：{"success": bool, "data": list, "message": str}
2. 使用request_akshare_data进行安全调用和重试
3. 异常处理：任何错误都返回success=False，不抛出异常
4. 统一日志记录（logger.info / logger.error）
"""

import logging
from typing import Any, Dict, List
from datetime import date
from system_service.service_result import error_result, success_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import (
    map_board_concept_index,
    map_board_industry_index,
    map_board_industry_summary,
    map_board_concept_info,
    map_stock_hot_follow,
    map_stock_hot_rank_detail,
    map_stock_stat_date,
    map_stock_changes,
    map_board_change
)

logger = logging.getLogger(__name__)


def get_stock_board_concept_index_ths(params) -> Dict[str, Any]:
    """
    查询同花顺概念板块指数日频率数据

    接口: akshare.stock_board_concept_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 概念板块名称，如 "阿里巴巴概念"
            - start_date (str): 开始日期，格式为 "YYYYMMDD"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 概念板块指数数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    symbol = params.get('symbol')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    
    logger.info(f"[同花顺概念板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    # 调用AKShare接口
    df = request_akshare_data(
        ak.stock_board_concept_index_ths,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        log_prefix="同花顺概念板块指数"
    )
    if not df:
        return error_result(message=f"[同花顺概念板块指数] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[同花顺概念板块指数] symbol={symbol} 查询成功，数据条数={len(df.get('data', []))}")

    # 应用映射函数
    result = map_board_concept_index(df)
    for item in result.get('data', []):
        item['concept_name'] = symbol
    print('1111', result.get('data')[0])
    return result


def get_stock_board_industry_summary_ths(params) -> Dict[str, Any]:
    """
    查询同花顺行业一览表

    接口: akshare.stock_board_industry_summary_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业一览表数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 行业一览表数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[同花顺行业一览表] 开始查询")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_industry_summary_ths,
        log_prefix="同花顺行业一览表"
    )
    
    if not result:
        return error_result(message="[同花顺行业一览表] 查询失败，数据为空")
    
    logger.info(f"[同花顺行业一览表] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_board_industry_summary(result)
    return mapped_result


def get_stock_board_concept_info_ths(params) -> Dict[str, Any]:
    """
    查询同花顺概念板块简介
    
    接口: akshare.stock_board_concept_info_ths
    目标地址: https://data.10jqka.com.cn/funds/gn/（以实际为准）
    描述: 获取同花顺概念板块简介数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 概念板块名称，如 "阿里巴巴概念"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 概念板块简介数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    symbol = params.get('symbol')
    
    logger.info(f"[同花顺概念板块简介] 开始查询 symbol={symbol}")
    
    # 参数验证
    if not symbol:
        return error_result(message="概念板块名称不能为空")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_concept_info_ths,
        symbol=symbol,
        log_prefix="同花顺概念板块简介"
    )
    if not result:
        return error_result(message=f"[同花顺概念板块简介] symbol={symbol} 查询失败，数据为空")

    if len(result.get('data')) > 0:
        result['data'] = [{item["项目"]: item["值"] for item in result['data']}]

    logger.info(f"[同花顺概念板块简介] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_board_concept_info(result)
    return mapped_result


def get_stock_board_industry_index_ths(params) -> Dict[str, Any]:
    """
    查询同花顺行业板块指数日频率数据
    
    接口: akshare.stock_board_industry_index_ths
    目标地址: https://data.10jqka.com.cn/funds/hy/（以实际为准）
    描述: 获取同花顺行业板块指数日频率数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 行业板块名称，如 "元件"
            - start_date (str): 开始日期，格式为 "YYYYMMDD"
            - end_date (str): 结束日期，格式为 "YYYYMMDD"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 行业板块指数数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    symbol = params.get('symbol')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    
    logger.info(f"[同花顺行业板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")
    
    # 参数验证
    if not symbol:
        return error_result(message="行业板块名称不能为空")
    
    if not start_date or not end_date:
        return error_result(message="开始日期和结束日期不能为空")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_industry_index_ths,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        log_prefix="同花顺行业板块指数"
    )
    
    if not result:
        return error_result(message=f"[同花顺行业板块指数] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[同花顺行业板块指数] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    
    # 应用映射函数
    mapped_result = map_board_industry_index(result)
    return mapped_result

today = date.today().isoformat()

def get_stock_hot_follow_xq(params) -> Dict[str, Any]:
    """
    查询雪球关注排行榜
    
    接口: akshare.stock_hot_follow_xq
    目标地址: 雪球网站
    描述: 获取雪球关注排行榜数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 选择类型，可选值: {"本周新增", "最热门"}，默认: "最热门"
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 关注排行榜数据
            "message": str        # 成功或错误信息
        }
"""
    import akshare as ak
    symbol = params.get('symbol', '最热门')

    logger.info(f"[雪球关注排行榜] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_hot_follow_xq,
        symbol=symbol,
        log_prefix="雪球关注排行榜"
    )
    if not result:
        return error_result(message=f"[雪球关注排行榜] symbol={symbol} 查询失败，数据为空")
    
    logger.info(f"[雪球关注排行榜] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_hot_follow(result)
    print('mapped_result', mapped_result['data'][0])
    for idx, item in enumerate(mapped_result['data'], start=1):
        item['rank_type'] = symbol
        item['hot_type'] = '雪球'
        item['hot_info'] = '关注'
        item['follow_rank'] = idx
        item['rank_date'] = today
    return mapped_result


def get_stock_hot_tweet_xq(params) -> Dict[str, Any]:
    """
    查询雪球 沪深股市 热度排行榜-讨论排行榜

    接口: akshare.stock_hot_tweet_xq
    目标地址: 雪球网站
    描述: 获取雪球热度排行榜-讨论排行榜

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 选择类型，可选值: {"本周新增", "最热门"}，默认: "最热门"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 关注排行榜数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    symbol = params.get('symbol', '最热门')

    logger.info(f"[雪球讨论排行榜] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_hot_tweet_xq,
        symbol=symbol,
        log_prefix="雪球讨论排行榜"
    )
    if not result:
        return error_result(message=f"[雪球讨论排行榜] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[雪球讨论排行榜] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_hot_follow(result)

    for idx, item in enumerate(mapped_result['data'], start=1):
        item['rank_type'] = symbol
        item['hot_type'] = '雪球'
        item['hot_info'] = '讨论'
        item['discuss_rank'] = idx
        item['discuss_count'] = item['follow_count']
        item['rank_date'] = today
    return mapped_result


def get_stock_hot_deal_xq(params) -> Dict[str, Any]:
    """
    查询雪球-沪深股市-热度排行榜-交易排行榜

    接口: akshare.stock_hot_deal_xq
    目标地址: 雪球网站
    描述: 雪球-沪深股市-热度排行榜-交易排行榜

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 选择类型，可选值: {"本周新增", "最热门"}，默认: "最热门"

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 关注排行榜数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    symbol = params.get('symbol', '最热门')

    logger.info(f"[雪球交易排行榜] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_hot_tweet_xq,
        symbol=symbol,
        log_prefix="雪球交易排行榜"
    )
    if not result:
        return error_result(message=f"[雪球交易排行榜] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[雪球交易排行榜] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    # 应用映射函数
    mapped_result = map_stock_hot_follow(result)

    for idx, item in enumerate(mapped_result['data'], start=1):
        item['rank_type'] = symbol
        item['hot_type'] = '雪球'
        item['hot_info'] = '交易'
        item['discuss_rank'] = idx
        item['trade_rank'] = item['follow_count']
        item['rank_date'] = today
    return mapped_result


def get_stock_hot_keyword_em(params) -> Dict[str, Any]:
    """
    查询东方财富个股人气榜热门关键词
    
    接口: akshare.stock_hot_keyword_em
    目标地址: 东方财富网站
    描述: 获取东方财富个股人气榜热门关键词数据
    
    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码，如 "SZ000665"（需带市场前缀）

    """
    import akshare as ak
    symbol = params.get('symbol')

    logger.info(f"[东方财富个股人气榜] 开始查询 symbol={symbol}")
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_hot_keyword_em,
        symbol=symbol,
        log_prefix="东方财富个股人气榜"
    )
    if not result:
        return error_result(message=f"[东方财富个股人气榜] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[东方财富个股人气榜] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_stat_date(result)
    return mapped_result

def get_stock_changes_em(params) -> Dict[str, Any]:
    """
    查询东方财富盘口异动数据
    """
    import akshare as ak
    symbol = params.get('symbol')
    logger.info(f"[东方财富盘口异动数据] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_changes_em,
        symbol=symbol,
        log_prefix="东方财富盘口异动数据"
    )
    if not result:
        return error_result(message=f"[东方财富盘口异动数据] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[东方财富盘口异动数据] symbol={symbol} 查询成功，原始数据条数={len(result.get('data', []))}")
    # ========== 新增：解析每条数据 ==========
    mapped_data = []
    def parse_related_info(change_type: str, info_str: str) -> dict:
        """根据异动类型解析相关信息字符串"""
        parts = info_str.split(",")
        map_info = ["火箭发射", "高台跳水", "快速反弹", "竞价上涨", "高开5日线", "向上缺口", "60日大幅上涨",
                    "加速下跌", '高台跳水', '竞价下跌', '低开5日线', '向下缺口',]
        # 四段型：成交量(手),价格,涨跌幅,成交额
        if change_type in ("大笔买入", "大笔卖出", "有大买盘", "封跌停板", "有大卖盘") and len(parts) == 4:
            if change_type == '封跌停板':
                return {
                    "price": float(parts[2]),
                    "volume_lot": int(float(parts[1])),
                    "change_percent": float(parts[3]),
                }
            return {
                "volume_lot": int(float(parts[0])),  # 手
                "price": float(parts[1]),
                "change_percent": float(parts[2]),
                "amount": float(parts[3]),
            }
        # 三段型：涨跌幅,价格,强度（火箭发射等）
        elif change_type in map_info and len(parts) == 3:
            return {
                "change_percent": float(parts[0]),
                "price": float(parts[1]),
                "strength": float(parts[2]),
            }
        elif change_type in ["60日新高"] and len(parts) == 3:
            return {
                "price": float(parts[0]),
                "change_percent": float(parts[1]),
            }
        # 一段型：价格或涨跌幅
        elif len(parts) == 2:
            val = float(parts[0])
            if change_type in ("封涨停板", "打开跌停板", "打开涨停板", "60日新高", "60日新低"):
                return {"price": val, 'change_percent': float(parts[1])}
            else:  # 默认为涨跌幅
                return {"change_percent": val}
        else:
            # 未知格式，保留原始数据
            return {"raw": info_str}

    for item in result['data']:
        # item 结构示例：{'时间': '14:55:42', '代码': '600152', '名称': '维科技术', '板块': '大笔买入', '相关信息': '540000,14.52,-0.077757,7840800'}
        change_type = item['板块']
        info_str = item['相关信息']

        # 解析相关信息
        parsed = parse_related_info(change_type, info_str)

        # 构建数据库记录（字段匹配您的表结构）
        record = {
            'change_type': change_type,
            'occur_time': item['时间'],
            'stat_date': today,
            'symbol': item['代码'],
            'name': item['名称'],
            'price': parsed.get('price'),
            'change_percent': parsed.get('change_percent'),
            'volume': parsed.get('volume_lot') * 100 if parsed.get('volume_lot') else None,  # 手转股
            'amount': parsed.get('amount'),
            'strength_level': parsed.get('strength'),
            'change_reason': None,
            'description': parsed.get('raw'),  # 未知格式时保留原始字符串
            'raw_info': info_str
        }
        mapped_data.append(record)
    logger.info(f"[东方财富盘口异动数据] symbol={symbol} 转换完成，有效数据条数={len(mapped_data)}")
    return success_result(data=mapped_data)


def get_all_stock_board_industry(params) -> Dict[str, Any]:
    """
        查询同花顺行业一览表（行业名称、代码等）

        接口: akshare.stock_board_industry_name_ths

        Args:
            params: 参数字典（此接口不需要参数，但为了统一格式保留）

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据
                "message": str        # 成功或错误信息
            }
        """
    import akshare as ak
    logger.info("[同花顺行业一览表] 开始查询")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_industry_name_ths,
        log_prefix="同花顺行业一览表"
    )

    if not result.get('data'):
        return error_result(message="[同花顺行业一览表] 查询失败，数据为空")

    logger.info(f"[同花顺行业一览表] 查询成功，数据条数={len(result.get('data', []))}")
    for idx, item in enumerate(result['data']):
        item['board_name'] = item.pop('name')
        item['board_code'] = item.pop('code')
        item['serial_number'] = idx + 1
    return result


def get_stock_board_change_em(params) -> Dict[str, Any]:
    """
    查询东方财富当日板块异动详情
    
    接口: akshare.stock_board_change_em
    目标地址: 东方财富网站
    描述: 获取东方财富当日板块异动详情数据
    
    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）
        
    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 板块异动详情数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[东方财富板块异动] 开始查询")
    
    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_board_change_em,
        log_prefix="东方财富板块异动"
    )
    
    if not result:
        return error_result(message="[东方财富板块异动] 查询失败，数据为空")
    
    logger.info(f"[东方财富板块异动] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_board_change(result)
    return mapped_result


