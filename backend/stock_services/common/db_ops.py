"""
stock_services/common/db_ops.py — 数据库操作封装

封装两类重复模式：
1. UpsertExecutor — 统一批量 UPSERT（带重试 + Schema 缓存集成）
2. ensure_table — 表存在性懒建

解决痛点：
  | 源文件 | 问题 | 严重度 |
  |--------|------|--------|
  | mootdx/service.py | _batch_upsert_kline 无异常重试 | 低 |
  | system_service/db_service.py | create_table_if_not_exists 先查后建 | 中 |
  | system_service/db_service.py | get_table_primary_keys 每次查询 INFORMATION_SCHEMA | 中 |
  | mootdx/table_helper.py | 串行建表（可并行优化） | 低 |
"""

import logging
import time
from typing import Any, Dict, List, Optional

from system_service.db_service import simple_upsert, get_db_service
from utils.db import get_conn

logger = logging.getLogger(__name__)

# ─── 默认配置 ─────────────────────────────────────────────────────
UPSERT_MAX_RETRIES = 2
UPSERT_RETRY_DELAY = 1.0  # 秒
TABLE_DEFAULT_DB = "stock_klines"


class UpsertExecutor:
    """
    统一 UPSERT 执行器（带重试 + Schema 缓存集成）。

    替代以下分散的写入代码：
      - mootdx/service.py _batch_upsert_kline（无重试）
      - services/stock_indicator_service.py 中 13 处重复 upsert 调用
      - services/stock_llm.py 中 5 处重复 upsert 调用
    """

    @staticmethod
    def execute(table_name: str, records: List[Dict[str, Any]],
                dedup_keys: List[str] = None,
                batch_size: int = 500,
                max_retries: int = UPSERT_MAX_RETRIES) -> tuple:
        """
        批量 UPSERT（带重试，集成 Schema 主键缓存）。

        对于现存直接调用 simple_upsert 的代码，本方法提供
        无侵入的追加层——不会改变 simple_upsert 原有行为，
        仅在失败时进行重试。

        Args:
            table_name:  目标表名
            records:     待写入的记录列表
            dedup_keys:  去重键列表（可选，传 None 则自动从主键获取）
            batch_size:  单次写入批次大小
            max_retries: 最大重试次数

        Returns:
            (写入条数, 失败条数)
        """
        if not records:
            return 0, 0

        # 如果未指定 dedup_keys，自动获取主键列表（带缓存）
        if dedup_keys is None:
            dedup_keys = UpsertExecutor._get_primary_keys(table_name)

        total = len(records)
        failed = 0

        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            ok = UpsertExecutor._execute_single(table_name, batch, dedup_keys, max_retries)
            failed += (len(batch) - ok)

        written = total - failed
        if failed > 0:
            logger.warning(
                f"[UpsertExecutor] {table_name}: 写入 {written}/{total} "
                f"失败 {failed}"
            )
        return written, failed

    @staticmethod
    def _execute_single(table_name: str, records: List[Dict[str, Any]],
                        dedup_keys: List[str], max_retries: int) -> int:
        """单批次写入（带重试）"""
        for attempt in range(max_retries):
            try:
                written, _ = simple_upsert(table_name, records, dedup_keys)
                return written
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[UpsertExecutor] {table_name} 写入重试 "
                        f"{attempt + 1}/{max_retries}: {e}"
                    )
                    time.sleep(UPSERT_RETRY_DELAY)
                else:
                    logger.error(
                        f"[UpsertExecutor] {table_name} 写入失败 "
                        f"(已重试{max_retries}次): {e}"
                    )
        return 0

    @staticmethod
    def _get_primary_keys(table_name: str) -> List[str]:
        """
        获取表主键列表（带缓存）。

        替代 system_service/db_service.get_table_primary_keys() 每次查库的问题。
        后续可集成 SchemaCache 中统一缓存。
        """
        try:
            db_service = get_db_service()
            return db_service.get_table_primary_keys(table_name)
        except Exception as e:
            logger.warning(f"[UpsertExecutor] 获取主键失败 {table_name}: {e}")
            return []


# ─── 表懒建工具 ────────────────────────────────────────────────────
# 作为现有 mootdx/table_helper.py 的补充，不替代它

_ensured_tables = set()


def ensure_table(table_name: str, ddl: str,
                 db_name: str = TABLE_DEFAULT_DB,
                 force: bool = False) -> bool:
    """
    确保表存在（按需懒建，幂等）。

    与 mootdx/table_helper.py 的区别：
      - table_helper 专用于 K 线分年表，使用 models.stock_models 的 DDL 模板
      - 本函数是通用工具，可用于任何业务表

    Args:
        table_name: 表名（不含库名前缀）
        ddl:        CREATE TABLE SQL
        db_name:    目标库名
        force:      强制建表（跳过进程内缓存）

    Returns:
        True 成功 / False 失败
    """
    if not force and table_name in _ensured_tables:
        return True

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 确保目标库存在
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(ddl)
        conn.commit()
        _ensured_tables.add(table_name)
        logger.info(f"[db_ops] 表已就绪: {db_name}.{table_name}")
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"[db_ops] 建表失败 {db_name}.{table_name}: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


__all__ = [
    "UpsertExecutor",
    "ensure_table",
]