"""
统一工具模块 - 股票数据服务工具函数

包含所有模块共用的工具函数：
- 日志配置
- 网络请求重试
- DataFrame 转换
- 响应创建
- 错误处理
"""

import json
import logging
import time
import random
import traceback
from typing import Dict, Any, Optional, Callable, Tuple

import pandas as pd

# 配置日志
logger = logging.getLogger(__name__)

# 需要重试的网络异常类型
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def safe_call_with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    timeout: int = 15,
    logger_name: str = "",
    **kwargs
) -> Any:
    """
    安全调用函数（带重试机制）

    Args:
        func: 要调用的函数
        *args: 函数位置参数
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        logger_name: 日志名称前缀
        **kwargs: 函数关键字参数

    Returns:
        函数返回值
    """
    last_exception = None
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except NETWORK_EXCEPTIONS as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                log_prefix = f"[{logger_name}]" if logger_name else ""
                logger.warning(
                    f"{log_prefix} 第{attempt + 1}次失败，{delay:.1f}秒后重试: {str(e)}"
                )
                time.sleep(delay)
            continue
        except Exception as e:
            # 非网络异常不重试
            last_exception = e
            break

    # 所有重试都失败，抛出最后一个异常
    if last_exception:
        raise last_exception


def _convert_dataframe_to_list(
    df: pd.DataFrame, log_prefix: str = ""
) -> list:
    """
    安全地将DataFrame转换为字典列表

    Args:
        df: pandas DataFrame对象
        log_prefix: 日志前缀

    Returns:
        字典列表
    """
    data_list = []

    # 检查DataFrame是否为空或无效
    if df is None:
        logger.warning(f"{log_prefix} DataFrame为None")
        return data_list

    if not hasattr(df, "empty") or df.empty:
        logger.warning(f"{log_prefix} DataFrame为空")
        return data_list

    if not hasattr(df, "columns") or df.columns is None or len(df.columns) == 0:
        logger.warning(f"{log_prefix} DataFrame没有列")
        return data_list

    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            try:
                value = row[col]
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
            except Exception as e:
                # 单个字段转换失败，使用None
                logger.debug(f"{log_prefix} 字段转换失败 col={col}: {str(e)}")
                value = None
            record[col] = value
        data_list.append(record)

    return data_list


def create_success_response(
    data: Any, symbol: str = "", error: str = None
) -> Dict[str, Any]:
    """创建成功响应"""
    return {
        "success": True,
        "data": data,
        "error": error,
        "symbol": symbol,
    }


def create_error_response(
    error: str, symbol: str = "", data: Any = None
) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "success": False,
        "data": data,
        "error": error,
        "symbol": symbol,
    }


def log_and_handle_error(
    error_msg: str,
    log_prefix: str,
    symbol: str = "",
    max_retries: int = 3,
    base_delay: float = 2.0,
    attempt: int = 0,
    exc_info: str = None,
) -> Tuple[Dict[str, Any], bool]:
    """
    通用错误日志和响应处理

    Args:
        error_msg: 错误信息
        log_prefix: 日志前缀
        symbol: 股票代码
        max_retries: 最大重试次数
        base_delay: 基础延迟
        attempt: 当前尝试次数
        exc_info: 异常详情

    Returns:
        (响应字典, 是否应该继续重试)
    """
    if attempt < max_retries - 1:
        delay = base_delay * (2**attempt) + random.uniform(0, 1)
        logger.warning(
            f"{log_prefix} 第{attempt + 1}次失败 {symbol}，{delay:.1f}秒后重试: {error_msg}"
        )
        time.sleep(delay)
        return create_error_response(error_msg, symbol), True
    else:
        logger.error(f"{log_prefix} 最终失败 {symbol}, error={error_msg}")
        if exc_info:
            logger.debug(f"{log_prefix} 异常详情: {exc_info}")
        return create_error_response(error_msg, symbol), False
