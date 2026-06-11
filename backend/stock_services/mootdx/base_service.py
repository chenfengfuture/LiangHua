#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MootdxBaseService — mootdx 模块统一基类

继承 RedisServiceBase，整合以下公共能力：
1. mootdx 客户端管理（线程本地 + 自动超时重置）
2. Redis 客户端（继承自 RedisServiceBase）
3. 日期工具（_parse_date、交易日验证）
4. 统一日志格式
5. DB 连接管理
6. 统一响应格式

所有 mootdx 子服务类继承此基类，消除跨文件重复代码。

🔁 方法委派说明：
  本类中的核心方法已委派至 stock_services/common/ 模块。
  保持同名方法以维持向后兼容，现有子类无需修改。
  新代码请直接使用 common 模块中的对应函数。
"""

from datetime import date, timedelta
from typing import Any, Dict, Optional

from system_service.redis_service import RedisServiceBase
from utils.db import get_conn

from stock_services.common.connection import MootdxClientManager
from stock_services.common.date_utils import (
    parse_date as _common_parse_date,
    calc_offset as _common_calc_offset,
    is_trading_day as _common_is_trading_day,
    get_trading_days as _common_get_trading_days,
    validate_date_range as _common_validate_date_range,
)
from stock_services.common.response import ok_result, fail_result
from stock_services.common.logging import get_module_logger

log = get_module_logger("mootdx_kline")

# ─── 公共常量 ─────────────────────────────────────────────────────
# (保持模块级，供子类直接引用)

FREQ_MAP = {
    "day": 9,
    "week": 7,
    "month": 8,
    "1": 0,
    "5": 1,
    "15": 2,
    "30": 3,
    "60": 4,
}

DAILY_FREQ_CODES = {7, 8, 9}
HARDCODED_WORKERS = 16

# _A_HOLIDAYS 已迁移至 stock_services/common/date_utils.py
# MINUTE_BARS_OFFSET 保留为模块级常量（被 service.py 直接引用）
from stock_services.common.date_utils import MINUTE_BARS_OFFSET_DEFAULT as MINUTE_BARS_OFFSET


class MootdxBaseService(RedisServiceBase):
    """mootdx 模块统一基类"""

    LOGGER_NAME = "mootdx_kline"

    def __init__(self, service_name: str = "MootdxBaseService"):
        super().__init__(service_name=service_name)
        self.log = get_module_logger(self.LOGGER_NAME)

    # ══════════════════════════════════════════════════════════════
    #  1. mootdx 客户端管理（委派至 common/connection）
    # ══════════════════════════════════════════════════════════════

    def _get_mootdx_client(self):
        """
        获取 mootdx 客户端
        """
        return MootdxClientManager.get_client()


    def _inc_timeout(self):
        """
        超时计数器 +1（委派至 MootdxClientManager）。
        """
        MootdxClientManager.inc_timeout()

    def _reset_timeout(self):
        """
        超时计数器归零（委派至 MootdxClientManager）。
        """
        MootdxClientManager.reset_timeout()

    # ══════════════════════════════════════════════════════════════
    #  2. 日期工具（委派至 common/date_utils）
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_date(date_str, default_delta_days=0) -> date:
        """
        日期归一化（委派至 common/date_utils）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.date_utils import parse_date
        """
        return _common_parse_date(date_str, default_delta_days)


    @staticmethod
    def _calc_offset(start_d: date, end_d: date, freq_code: int) -> int:
        """
        计算 bars() offset（委派至 common/date_utils）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.date_utils import calc_offset
        """
        return _common_calc_offset(start_d, end_d, freq_code)

    @staticmethod
    def is_trading_day(d: date) -> bool:
        """
        判断是否为交易日（委派至 common/date_utils）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.date_utils import is_trading_day
        """
        return _common_is_trading_day(d)


    def _validate_date_range(self, start_d: date, end_d: date, freq: str):
        """
        校验日期范围（委派至 common/date_utils）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.date_utils import validate_date_range
        """
        return _common_validate_date_range(start_d, end_d, freq)

    # ══════════════════════════════════════════════════════════════
    #  3. DB 连接管理（委派至 common/connection）
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _get_db_conn():
        """获取 DB 连接（默认 lianghua 库）"""
        return get_conn()

    # ══════════════════════════════════════════════════════════════
    #  4. 统一响应格式（委派至 common/response）
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _ok(data: Any) -> Dict:
        """
        成功响应（委派至 common/response）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.response import ok_result
        """
        return ok_result(data=data)

    @staticmethod
    def _fail(msg: str) -> Dict:
        """
        失败响应（委派至 common/response）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.response import fail_result
        """
        return fail_result(message=msg)