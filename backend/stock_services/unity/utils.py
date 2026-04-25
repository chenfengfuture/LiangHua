"""
统一工具模块 - 股票数据服务工具函数

包含所有模块共用的工具函数：
- 日志配置
- 网络请求重试
- DataFrame 转换
- 响应创建
- 错误处理
"""

import logging
import random
import time
import re
from typing import Any, Callable, Dict, List

import pandas as pd
from system_service.service_result import error_result, success_result, wrap_service_result


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
        return error_result(message=last_exception)

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

def request_akshare_data(api_func, log_prefix, *args, **kwargs):
    safe_kwargs = kwargs.copy()
    df = safe_call_with_retry(api_func, max_retries=3, *args, **safe_kwargs)
    if df is None or (hasattr(df, 'empty') and df.empty):
        return None  # 或空列表
    dataframe_to_list = _convert_dataframe_to_list(df, log_prefix)
    return success_result(data=dataframe_to_list)


class StockValidateService:
    @wrap_service_result
    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        验证股票代码格式 - 通用工具方法

        Args:
            symbol: 股票代码

        Returns:
            验证结果，如果成功返回成功结果，失败返回错误结果
        """
        if not symbol or not isinstance(symbol, str):

            return error_result(
                message="股票代码不能为空且必须是字符串",
                data={"symbol": symbol}
            )

        # 标准化symbol格式（确保大写）
        symbol = symbol.strip().upper()

        # 基本格式验证：至少包含字母和数字
        if not re.match(r'^[A-Z]{1,4}\d{6}$', symbol):
            # 尝试添加市场前缀
            if symbol.startswith(('SH', 'SZ')):
                if not re.match(r'^(SH|SZ)\d{6}$', symbol):
                    return error_result(
                        message=f"股票代码格式不正确: {symbol}",
                        data={"symbol": symbol}
                    )
            else:
                # 尝试自动添加市场前缀
                if len(symbol) == 6:
                    # 简单规则：6位数字，0/3开头为深圳，6开头为上海
                    if symbol[0] in ('0', '3'):
                        symbol = f"SZ{symbol}"
                    elif symbol[0] in ('6', '9'):
                        symbol = f"SH{symbol}"
                    else:
                        return error_result(
                            message=f"无法识别股票代码市场: {symbol}",
                            data={"symbol": symbol}
                        )
                else:
                    return error_result(
                        message=f"股票代码格式不正确: {symbol}",
                        data={"symbol": symbol}
                    )

        return success_result(
            message="股票代码验证成功",
            data={"symbol": symbol}
        )

    @wrap_service_result
    def validate_required_params(self, params: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        """
        验证必需参数是否存在 - 通用工具方法

        Args:
            params: 参数字典
            required_keys: 必需参数键列表

        Returns:
            验证结果，如果成功返回成功结果，失败返回错误结果
        """
        missing_keys = []
        for key in required_keys:
            if key not in params or params[key] is None:
                missing_keys.append(key)

        if missing_keys:
            return error_result(
                message=f"缺少必需参数: {', '.join(missing_keys)}",
                data={"missing_keys": missing_keys, "params": params}
            )

        return success_result(
            message="参数验证成功",
            data={"params": params}
        )

    def validate_sh_symbol_type(self, symbol: str) -> Dict[str, Any]:
        """
        验证上交所股票列表查询参数

        Args:
            params: 参数字典，包含symbol字段

        Returns:
            验证结果字典
        """
        # 验证参数不能为空
        if not symbol or not isinstance(symbol, str):
            return error_result(
                message="板块类型参数不能为空且必须是字符串",
                data={"symbol": symbol}
            )

        # 验证板块类型
        valid_types = {"主板A股", "主板B股", "科创板"}
        if symbol not in valid_types:
            return error_result(
                message=f"板块类型参数必须为以下值之一: {', '.join(sorted(valid_types))}",
                data={"symbol": symbol, "valid_types": list(valid_types)}
            )

        return success_result(
            message="板块类型参数验证成功",
            data={"symbol": symbol}
        )


stock_validate_service = StockValidateService()

__all__ = [
    'stock_validate_service',
    'StockValidateService',
    'request_akshare_data'
]