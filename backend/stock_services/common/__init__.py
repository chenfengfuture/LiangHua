"""
stock_services/common/ — stock_services 公共子模块

统一封装高频复用的基础能力：
  - connection: mootdx 客户端、Redis 连接、DB 连接上下文管理器
  - date_utils: 日期解析、交易日判断、统计日期填充
  - response:  统一响应格式（复用 system_service.service_result）
  - cache:     缓存 Key 构建、Redis Hash 批量读写工具
  - db_ops:    批量 UPSERT 执行器（带重试）、表存在性懒建
  - validation: 股票代码、日期、参数统一验证
  - logging:   统一日志工厂（自动 [prefix] 前缀）

使用示例：
    from stock_services.common.connection import MootdxClientManager, DatabaseContext
    from stock_services.common.date_utils import parse_date, add_stat_date
    from stock_services.common.response import ok_result, fail_result
    from stock_services.common.cache import CacheKeyBuilder, RedisHashHelper
    from stock_services.common.db_ops import UpsertExecutor
    from stock_services.common.validation import StockValidator
    from stock_services.common.logging import get_logger
"""

from .connection import MootdxClientManager, DatabaseContext, RedisClientManager
from .date_utils import (
    parse_date, calc_offset, is_trading_day, ensure_trading_day,
    get_trading_days, validate_date_range,
    add_stat_date, add_rank_date, add_change_date,
)
from .response import ok_result, fail_result
from .cache import CacheKeyBuilder, RedisHashHelper
from .db_ops import UpsertExecutor
from .validation import StockValidator
from .logging import get_logger

__all__ = [
    # connection
    "MootdxClientManager",
    "DatabaseContext",
    "RedisClientManager",
    # date_utils
    "parse_date",
    "calc_offset",
    "is_trading_day",
    "ensure_trading_day",
    "get_trading_days",
    "validate_date_range",
    "add_stat_date",
    "add_rank_date",
    "add_change_date",
    # response
    "ok_result",
    "fail_result",
    # cache
    "CacheKeyBuilder",
    "RedisHashHelper",
    # db_ops
    "UpsertExecutor",
    # validation
    "StockValidator",
    # logging
    "get_logger",
]