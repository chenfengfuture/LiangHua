"""
统一工具模块 - 股票数据服务工具函数

包含所有模块共用的工具函数：
- 日志配置
- 网络请求重试
- DataFrame 转换
- 响应创建
- 错误处理

🔁 StockValidateService 已委派至 stock_services/common/validation:
    StockValidator 提供统一的参数验证，消除两套验证器功能重叠。
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List

import pandas as pd
from system_service.service_result import error_result, success_result, wrap_service_result

from stock_services.common.validation import StockValidator as _CommonValidator


# 配置日志
logger = logging.getLogger(__name__)

# 需要重试的网络异常类型
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# ─── AKShare 全局配置（延迟初始化） ────────────────────────────────────
# 在首次调用 request_akshare_data 时执行，避免模块加载时触发 akshare 导入

_akshare_initialized = False
_AKSHARE_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _ensure_akshare_config():
    """首次调用 AKShare 时初始化全局配置（随机UA + 请求延时 + 超时）"""
    global _akshare_initialized
    if _akshare_initialized:
        return
    _akshare_initialized = True
    try:
        from akshare.request import requests as ak_requests
        SessionClass = ak_requests.Session
        _original_session_init = SessionClass.__init__
        _original_get = SessionClass.get

        def _patched_session_init(self, *args, **kwargs):
            _original_session_init(self, *args, **kwargs)
            self.headers['User-Agent'] = random.choice(_AKSHARE_USER_AGENTS)

        def _patched_get(self, url, **kwargs):
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 15
            delay = random.uniform(3, 5)
            time.sleep(delay)
            return _original_get(self, url, **kwargs)

        SessionClass.__init__ = _patched_session_init
        SessionClass.get = _patched_get
        logger.info("[AKShare] 已启用随机UA + 3~5秒请求延时 + 15秒超时")
    except ImportError:
        logger.warning("[AKShare] 缺少依赖，跳过全局配置")
    except Exception as e:
        logger.warning(f"[AKShare] 全局配置失败: {e}")


def safe_call_with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    timeout: int = 30,
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
    _ensure_akshare_config()  # 首次调用时初始化 AKShare 全局配置
    safe_kwargs = kwargs.copy()
    df = safe_call_with_retry(api_func, max_retries=3, *args, **safe_kwargs)
    if df is None or (hasattr(df, 'empty') and df.empty):
        return None  # 或空列表
    dataframe_to_list = _convert_dataframe_to_list(df, log_prefix)
    if not dataframe_to_list:
        return None
    return success_result(data=dataframe_to_list)


class StockValidateService:
    """
    股票代码验证服务 — 委派至 common/validation.StockValidator。

    保持类名和方法签名以维持向后兼容（现有代码通过 stock_validate_service 引用）。
    新代码请直接使用 stock_services.common.validation.StockValidator。
    """

    @wrap_service_result
    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        return _CommonValidator.validate_symbol_result(symbol)

    @wrap_service_result
    def validate_required_params(self, params: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        return _CommonValidator.validate_required_params_result(params, required_keys)

    def validate_sh_symbol_type(self, symbol: str) -> Dict[str, Any]:
        return _CommonValidator.validate_sh_symbol_type_result(symbol)


stock_validate_service = StockValidateService()

__all__ = [
    'stock_validate_service',
    'StockValidateService',
    'request_akshare_data'
]