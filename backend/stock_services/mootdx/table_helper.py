#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mootdx K 线分年表懒建工具

复用 models.stock_models.CREATE_KLINES_TABLE_DDL 模板（已修正库名为 `stock_klines`），
按年份渲染 + execute "CREATE TABLE IF NOT EXISTS"。幂等，跨年首次写入时触发建表。

K 线分年表统一建到 `stock_klines` 库下：stock_klines.stock_klines_YYYY

🔁 DB 连接管理已委派至 stock_services/common/connection:
    DatabaseContext 上下文管理器自动处理 commit/rollback/close
"""

import threading

from stock_services.common.connection import DatabaseContext
from stock_services.common.logging import get_module_logger
from models.stock_models import (
    CREATE_KLINES_TABLE_DDL,
    KLINE_YEAR_MAX,
    KLINE_YEAR_MIN,
)

log = get_module_logger("mootdx_kline.table_helper")

# K 线分年表所在的目标库（与 models.stock_models.CREATE_KLINES_TABLE_DDL 中的库名保持一致）
KLINE_DB_NAME = "stock_klines"

# 进程内已建表缓存，避免重复 execute DDL
_ensured_years = set()
_ensure_lock = threading.Lock()


def get_kline_full_table_name(year: int) -> str:
    """
    返回 K 线分年表的完整限定名（含库名）

    例：2026 → "stock_klines.stock_klines_2026"
    """
    return f"{KLINE_DB_NAME}.stock_klines_{year}"


def ensure_kline_year_table(year: int) -> bool:
    """
    确保 stock_klines.stock_klines_{year} 表存在（按需懒建）

    使用 models 中的 CREATE_KLINES_TABLE_DDL 模板渲染 + CREATE TABLE IF NOT EXISTS。
    幂等，重复调用安全。第一次执行时若 `stock_klines` 库不存在，会先 CREATE DATABASE。

    Args:
        year: 年份，必须在 [KLINE_YEAR_MIN, KLINE_YEAR_MAX]

    Returns:
        True 建表成功 / 已存在；False 失败
    """
    if not isinstance(year, int):
        try:
            year = int(year)
        except (ValueError, TypeError):
            log.error(f"[table_helper] year 不是整数: {year}")
            return False

    if year < KLINE_YEAR_MIN or year > KLINE_YEAR_MAX:
        log.error(f"[table_helper] year 越界 [{KLINE_YEAR_MIN}, {KLINE_YEAR_MAX}]: {year}")
        return False

    # 进程内缓存命中
    if year in _ensured_years:
        return True

    with _ensure_lock:
        if year in _ensured_years:
            return True

        table_name = f"stock_klines_{year}"
        try:
            ddl = CREATE_KLINES_TABLE_DDL.format(
                table_name=table_name,
                comment=f"K线数据{year}年",
            )
        except Exception as e:
            log.error(f"[table_helper] DDL 渲染失败 year={year}: {e}")
            return False

        try:
            with DatabaseContext(commit=True) as cur:
                # 1. 先确保目标库存在（连接 default 库即可执行 CREATE DATABASE）
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{KLINE_DB_NAME}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                # 2. 在 stock_klines 库下建分年表（DDL 已含库名前缀）
                cur.execute(ddl)
            _ensured_years.add(year)
            log.info(f"[table_helper] 表已就绪: {KLINE_DB_NAME}.{table_name}")
            return True
        except Exception as e:
            log.error(f"[table_helper] 建表失败 {KLINE_DB_NAME}.{table_name}: {e}")
            return False


def ensure_kline_year_tables(years) -> int:
    """
    批量确保多年份表存在

    Args:
        years: 可迭代的年份集合

    Returns:
        成功建表的年份数量
    """
    if not years:
        return 0

    ok = 0
    for y in set(years):
        if ensure_kline_year_table(y):
            ok += 1
    return ok
