"""
stock_services/common/logging.py — 统一日志工厂

为 stock_services 全模块 200+ 日志提供统一入口。
通过自动 [prefix] 前缀过滤器，消除每个文件手动拼接前缀的代码。

使用方式：
    from stock_services.common.logging import get_logger

    logger = get_logger("my_module", prefix="my_prefix")
    logger.info("查询成功，条数=100")
    # 输出: [my_prefix] 查询成功，条数=100
"""

import logging
from typing import Optional


class PrefixFilter(logging.Filter):
    """日志前缀过滤器，自动为每条日志添加 [prefix] 标记。"""

    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix

    def filter(self, record: logging.LogRecord) -> bool:
        if self.prefix:
            record.msg = f"[{self.prefix}] {record.msg}"
        return True


def get_logger(name: str, prefix: Optional[str] = None,
               level: int = logging.DEBUG) -> logging.Logger:
    """
    统一日志工厂。

    Args:
        name:   日志器名称（建议 __name__）
        prefix: 日志前缀标记（如 "kline_redis", "indicator"），
                自动添加 [] 包围
        level:  日志级别，默认 DEBUG

    Returns:
        配置好的 Logger 实例

    特性：
      - 自动添加 [prefix] 前缀，消除手动拼接
      - 防止重复添加 Filter（通过 filter name 去重）
      - 兼容现有代码，可无缝替换 logger = logging.getLogger(name)

    Examples:
        # 替换前:
        logger = logging.getLogger("kline_redis")
        logger.info(f"[kline_redis] 写入成功")

        # 替换后:
        logger = get_logger("kline_redis", prefix="kline_redis")
        logger.info("写入成功")
        # 自动输出: [kline_redis] 写入成功
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if prefix:
        # 避免重复添加相同的 Filter
        filter_name = f"prefix_{prefix}"
        existing = {f.name for f in logger.filters}
        if filter_name not in existing:
            f = PrefixFilter(prefix)
            f.name = filter_name
            logger.addFilter(f)

    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """
    便捷版：直接用模块短名作前缀。

    Example:
        logger = get_module_logger("kline_redis")
        # 等价于 get_logger("stock_services.mootdx.kline_redis", prefix="kline_redis")
    """
    return get_logger(f"stock_services.{module_name}", prefix=module_name)


__all__ = [
    "get_logger",
    "get_module_logger",
    "PrefixFilter",
]