"""
stock_services/common/connection.py — 连接管理统一封装

封装三类高频连接管理，消除分散在 mootdx/*、unity/*/service.py、services/* 中的重复代码：

1. MootdxClientManager — mootdx 客户端统一管理器（线程本地 + 指数退避重试 + 超时自动重置）
   替代：mootdx/base_service.py._get_mootdx_client()、unity/mootdx/service.py 裸导入、unity/transaction/service.py 裸导入

2. DatabaseContext — DB 连接上下文管理器，统一 try→cursor→commit→rollback→close 模板
   替代：mootdx/table_helper.py（约30行模板）、mootdx/service.py 中15+处分散处理

3. RedisClientManager — Redis 客户端统一管理器（智能心跳，每60s ping一次）
   改进：RedisServiceBase._get_client() 每次调用都 ping() 的高频开销问题
"""

import logging
import random
import threading
import time
from typing import Any, Optional

from utils.db import get_conn

logger = logging.getLogger(__name__)


# =══════════════════════════════════════════════════════════════════
#  MootdxClientManager — mootdx 客户端统一管理器
# =══════════════════════════════════════════════════════════════════

class MootdxClientManager:
    """
    mootdx 客户端统一管理器。

    设计目标：
      替代 mootdx/base_service.py._get_mootdx_client() 和
      unity/mootdx/service.py、unity/transaction/service.py 中
      直接 `from mootdx.quotes import Quotes` 的裸创建方式。

    特性：
      - 线程本地（threading.local）隔离，线程安全
      - 指数退避重试（最多3次，间隔 1s/2s/4s），网络抖动可恢复
      - 连续3次超时自动重置客户端
      - 创建后验证 stock_count > 0 确保连接有效
    """

    _local = threading.local()

    # 重试配置
    MAX_RETRIES = 3
    BASE_DELAY = 1.0     # 指数退避基值（秒）
    TIMEOUT_RESET_THRESHOLD = 3  # 连续超时次数阈值

    @classmethod
    def get_client(cls, market: str = "std") -> Optional[Any]:
        """
        获取当前线程的 mootdx 客户端（带指数退避重试 + 自动超时重置）。

        Args:
            market: 市场参数，默认 "std"

        Returns:
            Quotes 客户端实例，失败返回 None
        """
        # 检查是否需要重置（连续超时 ≥ 阈值）
        c = getattr(cls._local, "mootdx_client", None)
        timeout_cnt = getattr(cls._local, "timeout_cnt", 0)

        if c is not None and timeout_cnt >= cls.TIMEOUT_RESET_THRESHOLD:
            cls._local.mootdx_client = None
            cls._local.timeout_cnt = 0
            c = None
            logger.warning("[MootdxClientManager] 客户端超时次数达阈值，已自动重置")

        # 已有有效客户端
        if c is not None:
            return c

        # 创建新客户端（带重试）
        last_exc = None
        for attempt in range(cls.MAX_RETRIES):
            try:
                from mootdx.quotes import Quotes
                c = Quotes.factory(market=market)
                if c and c.stock_count(market=1) > 0:
                    cls._local.mootdx_client = c
                    cls._local.timeout_cnt = 0
                    return c
                else:
                    last_exc = RuntimeError("连接已建立但查询无数据返回")
            except Exception as e:
                last_exc = e
                if attempt < cls.MAX_RETRIES - 1:
                    delay = cls.BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        f"[MootdxClientManager] 第{attempt + 1}次创建失败，"
                        f"{delay:.1f}秒后重试: {e}"
                    )
                    time.sleep(delay)

        logger.error(f"[MootdxClientManager] 创建客户端失败（已重试{cls.MAX_RETRIES}次）: {last_exc}")
        return None

    @classmethod
    def get_client_safe(cls, market: str = "std") -> Optional[Any]:
        """
        安全的客户端获取，永不抛出异常（与 unity 层兼容）。

        Args:
            market: 市场参数

        Returns:
            Quotes 客户端实例，失败返回 None
        """
        try:
            return cls.get_client(market)
        except Exception as e:
            logger.error(f"[MootdxClientManager] 获取客户端异常: {e}")
            return None

    @classmethod
    def reset_client(cls):
        """强制重置当前线程的 mootdx 客户端。"""
        cls._local.mootdx_client = None
        cls._local.timeout_cnt = 0

    @classmethod
    def inc_timeout(cls):
        """超时计数器 +1"""
        cls._local.timeout_cnt = getattr(cls._local, "timeout_cnt", 0) + 1

    @classmethod
    def reset_timeout(cls):
        """超时计数器归零"""
        cls._local.timeout_cnt = 0


# =══════════════════════════════════════════════════════════════════
#  DatabaseContext — DB 连接上下文管理器
# =══════════════════════════════════════════════════════════════════

class DatabaseContext:
    """
    DB 连接上下文管理器，统一以下重复模板（现存 7+ 文件）：

    | 文件 | 模式 |
    |------|------|
    | mootdx/table_helper.py | 自定义 conn → cur.execute → commit → rollback → close |
    | mootdx/service.py | get_cursor(commit=True) + 事务写入 |
    | services/stock_indicator_service.py | with get_cursor() + upsert |
    | services/stock_llm.py | with get_cursor() + query |

    使用方式：
        with DatabaseContext(commit=True) as cur:
            cur.execute(sql, params)

    对比旧模板（约 15 行）：
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        except Exception:
            try: conn.rollback()
            except: pass
            raise
        finally:
            try: conn.close()
            except: pass
    """

    def __init__(self, commit: bool = True, db_name: str = None):
        """
        Args:
            commit: 是否自动提交事务（默认 True）
            db_name: 目标数据库名（默认 None，使用默认库）
        """
        self.commit = commit
        self.db_name = db_name
        self._conn = None
        self._cursor = None

    def __enter__(self):
        self._conn = get_conn()
        self._cursor = self._conn.cursor()
        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常路径：回滚
            try:
                if self._conn:
                    self._conn.rollback()
            except Exception as e:
                logger.warning(f"[DatabaseContext] 回滚失败: {e}")
            return False  # 不吞没异常

        # 正常路径：提交
        try:
            if self.commit:
                self._conn.commit()
        except Exception as e:
            logger.error(f"[DatabaseContext] 提交失败: {e}")
            raise
        finally:
            try:
                if self._conn:
                    self._conn.close()
            except Exception as e:
                logger.warning(f"[DatabaseContext] 关闭连接失败: {e}")

    def __del__(self):
        """防御性清理"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass


# =══════════════════════════════════════════════════════════════════
#  RedisClientManager — Redis 统一管理器（智能心跳）
# =══════════════════════════════════════════════════════════════════

class RedisClientManager:
    """
    Redis 统一管理器（智能心跳）。

    解决痛点：
      现有 RedisServiceBase._get_client() 每次调用都执行 ping()，
      在 kline_hset_batch / kline_hget_all 等高频场景（每秒数十次）
      ping 开销累积明显。

    优化方案：
      - 首次连接时 ping 验证
      - 之后每 PING_INTERVAL 秒才执行一次 ping
      - 使用线程安全的类级字典记录上次 ping 时间
    """

    _lock = threading.Lock()
    # {thread_id: last_ping_timestamp}
    _last_ping: dict = {}

    PING_INTERVAL = 60  # 心跳检测间隔（秒）

    @classmethod
    def get_client(cls, force_ping: bool = False):
        """
        获取 Redis 客户端（智能心跳）。

        Args:
            force_ping: 强制 ping（默认 False，按 PING_INTERVAL 节流）

        Returns:
            Redis 客户端实例，或 None
        """
        # 延迟导入避免循环依赖
        from system_service.redis_service import RedisServiceBase

        client = RedisServiceBase._get_client()
        if client is None:
            return None

        if force_ping:
            return cls._ping_and_update(client)

        tid = threading.get_ident()
        now = time.time()
        last = cls._last_ping.get(tid, 0)

        if now - last >= cls.PING_INTERVAL:
            return cls._ping_and_update(client, tid)

        return client

    @classmethod
    def _ping_and_update(cls, client, tid: int = None):
        """执行 ping 并更新记录时间"""
        try:
            client.ping()
            if tid is not None:
                with cls._lock:
                    cls._last_ping[tid] = time.time()
            return client
        except Exception:
            logger.warning("[RedisClientManager] ping 失败，尝试重新连接")
            return None


# 模块级单例（供直接引用）
mootdx_client_manager = MootdxClientManager()
redis_client_manager = RedisClientManager()

__all__ = [
    "MootdxClientManager",
    "mootdx_client_manager",
    "DatabaseContext",
    "RedisClientManager",
    "redis_client_manager",
]