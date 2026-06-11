import logging
import traceback
from typing import Any, Dict

from system_service.service_result import error_result
from stock_services.unity.utils import request_akshare_data
from stock_services.utils.field_mapper import map_stock_ask, map_stock_change_symbol

from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_stock_zh_a_spot(params) -> Dict[str, Any]:
    """
    查询新浪财经-沪深京 A 股实时行情数据

    接口: akshare.stock_zh_a_spot
    目标地址: https://vip.stock.finance.sina.com.cn/mkt/#hs_a
    描述: 新浪财经-沪深京 A 股数据, 重复运行本函数会被新浪暂时封 IP, 建议增加时间间隔
    限量: 单次返回沪深京 A 股上市公司的实时行情数据

    Args:
        params: 参数字典（此接口不需要参数，但为了统一格式保留）

    Returns:
        统一格式的响应数据：
        {
            "success": bool,      # 调用是否成功
            "data": list,         # 实时行情数据
            "message": str        # 成功或错误信息
        }
    """
    import akshare as ak
    logger.info("[新浪沪深京A股实时行情] 开始查询")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_spot,
        log_prefix="新浪沪深京A股实时行情"
    )

    if not result:
        return error_result(message="[新浪沪深京A股实时行情] 查询失败，数据为空")

    logger.info(f"[新浪沪深京A股实时行情] 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_individual_spot_xq(params) -> Dict[str, Any]:
    """
    查询雪球-个股实时行情数据

    接口: akshare.stock_individual_spot_xq
    目标地址: https://xueqiu.com/S/SH513520
    描述: 雪球-行情中心-个股，单次获取指定 symbol 的最新行情数据
    限量: 单次获取指定 symbol 的最新行情数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 证券代码，例如 "SH600000"、"SZ000001"、"HK00700"
            - token (float, optional): 默认不设置token
            - timeout (float, optional): 默认不设置超时参数

    """
    import akshare as ak
    # 获取参数
    symbol = params.get('symbol', '')
    token = params.get('token', None)
    timeout = params.get('timeout', None)

    # 参数校验
    if not symbol:
        return error_result(message="[雪球个股行情] symbol 不能为空")

    logger.info(f"[雪球个股行情] 开始查询 symbol={symbol}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_individual_spot_xq,
        symbol=symbol,
        token=token,
        timeout=timeout,
        log_prefix="雪球个股行情"
    )

    if not result:
        return error_result(message=f"[雪球个股行情] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[雪球个股行情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_zh_a_hist(params) -> Dict[str, Any]:
    """
    查询东方财富-沪深京 A 股日频率历史行情数据

    接口: akshare.stock_zh_a_hist
    目标地址: https://quote.eastmoney.com/concept/sh603777.html?from=classic
    描述: 东方财富-沪深京 A 股日频率数据; 历史数据按日频率更新, 当日收盘价请在收盘后获取
    限量: 单次返回指定沪深京 A 股上市公司、指定周期和指定日期间的历史行情日频率数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码, 例: "603777"
            - period (str): 周期, 可选值: daily, weekly, monthly; 默认: daily
            - start_date (str): 开始日期, 格式: yyyymmdd, 例: "20210301"
            - end_date (str): 结束日期, 格式: yyyymmdd, 例: "20210616"
            - adjust (str): 复权类型, 可选值: 空(不复权), qfq(前复权), hfq(后复权); 默认: 不复权
            - timeout (float, optional): 超时参数, 默认不设置

    """
    import akshare as ak
    # 解析参数
    symbol = params.get('symbol', '')
    period = params.get('period', 'daily')
    start_date = params.get('start_date', '')
    end_date = params.get('end_date', '')
    adjust = params.get('adjust', '')
    timeout = params.get('timeout', None)

    logger.info(f"[东方财富历史行情] 开始查询 symbol={symbol}, 周期={period}, 日期={start_date}-{end_date}, 复权={adjust}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_hist,
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
        timeout=timeout,
        log_prefix="东方财富历史行情"
    )

    if not result:
        return error_result(message=f"[东方财富历史行情] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[东方财富历史行情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")
    print('k线', result['data'][0])
    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_zh_a_daily(params) -> Dict[str, Any]:
    """
    查询新浪财经-沪深京 A 股历史行情日频率数据
    注意：多次获取容易封禁 IP，建议优先使用 stock_zh_a_hist 接口

    接口: akshare.stock_zh_a_daily
    目标地址: https://finance.sina.com.cn/realstock/company/sh600006/nc.shtml
    描述: 新浪财经-沪深京 A 股的数据, 历史数据按日频率更新
    限量: 单次返回指定沪深京 A 股上市公司指定日期间的历史行情日频率数据

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码, 例: "sh600000"
            - start_date (str): 开始日期, 格式: yyyymmdd, 例: "20201103"
            - end_date (str): 结束日期, 格式: yyyymmdd, 例: "20201116"
            - adjust (str): 复权类型, 可选值: 空(不复权), qfq, hfq, hfq-factor, qfq-factor; 默认: 空

    """
    import akshare as ak
    # 解析参数
    symbol = params.get('symbol', '')
    start_date = params.get('start_date', '')
    end_date = params.get('end_date', '')
    adjust = params.get('adjust', '')

    logger.info(f"[新浪历史行情] 开始查询 symbol={symbol}, 日期={start_date}-{end_date}, 复权={adjust}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_daily,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
        log_prefix="新浪历史行情"
    )

    if not result:
        return error_result(message=f"[新浪历史行情] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[新浪历史行情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_ask(result)
    return mapped_result


def get_stock_zh_a_hist_min_em(params) -> Dict[str, Any]:
    """
    查询东方财富-沪深京 A 股分时/分钟级历史行情数据

    接口: akshare.stock_zh_a_hist_min_em
    目标地址: https://quote.eastmoney.com/concept/sh603777.html
    描述: 东方财富网-行情首页-沪深京 A 股-每日分时行情; 该接口只能获取近期的分时数据，注意时间周期的设置
    限量: 单次返回指定股票、频率、复权调整和时间区间的分时数据, 其中 1 分钟数据只返回近 5 个交易日数据且不复权

    Args:
        params: 参数字典，包含以下字段：
            - symbol (str): 股票代码, 例: "603777"
            - period (str): 周期, 可选值: 1, 5, 15, 30, 60; 默认: 1
            - start_date (str): 开始日期, 格式: yyyy-mm-dd, 例: "2025-01-01"
            - end_date (str): 结束日期, 格式: yyyy-mm-dd, 例: "2025-01-15"
            - adjust (str): 复权类型, 可选值: "", "qfq", "hfq"; 默认: ""

    """
    import akshare as ak
    # 解析参数
    symbol = params.get('symbol', '')
    period = params.get('period', '1')
    start_date = params.get('start_date', '')
    end_date = params.get('end_date', '')
    adjust = params.get('adjust', '')

    # 必填参数校验
    if not symbol:
        return error_result(message="[东方财富分时行情] 参数 symbol 不能为空")
    if not start_date:
        return error_result(message="[东方财富分时行情] 参数 start_date 不能为空")
    if not end_date:
        return error_result(message="[东方财富分时行情] 参数 end_date 不能为空")

    logger.info(f"[东方财富分时行情] 开始查询 symbol={symbol}, 周期={period}min, 日期={start_date}-{end_date}")

    # 调用AKShare接口
    result = request_akshare_data(
        ak.stock_zh_a_hist_min_em,
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
        log_prefix="东方财富分时行情"
    )

    if not result:
        return error_result(message=f"[东方财富分时行情] symbol={symbol} 查询失败，数据为空")

    logger.info(f"[东方财富分时行情] symbol={symbol} 查询成功，数据条数={len(result.get('data', []))}")

    # 应用映射函数
    mapped_result = map_stock_zh_a_hist_min_em(result)
    return mapped_result