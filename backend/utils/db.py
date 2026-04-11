"""
utils/db.py — 全局数据库连接池（单例）

设计原则：
  - 进程内只创建一个 PooledDB 实例，永不重复建连
  - 所有模块统一通过 get_conn() 获取连接
  - 支持两种池模式：API 服务（默认）和采集器（高并发）

使用示例：
    from utils.db import get_conn

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        conn.close()
"""

import threading
from contextlib import contextmanager
import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB

from config.settings import DB_CONFIG, DB_POOL_CONFIG, DB_POOL_CONFIG_COLLECTOR
from config.settings import NEWS_DB_CONFIG, NEWS_DB_POOL_CONFIG


# ═══════════════════════════════════════════════════════════════════
#  全局连接池（单例）
# ═══════════════════════════════════════════════════════════════════

_pool: PooledDB | None = None
_pool_lock = threading.Lock()
_pool_type: str | None = None   # "api" | "collector"


def _init_pool(pool_type: str = "api") -> PooledDB:
    """
    创建全局连接池（线程安全，只创建一次）。

    Args:
        pool_type: "api"（默认，10 连接）或 "collector"（16 连接）
    """
    global _pool, _pool_type
    if _pool is not None:
        if _pool_type != pool_type:
            import warnings
            warnings.warn(
                f"连接池已初始化为 {_pool_type} 模式，忽略 {pool_type} 请求",
                RuntimeWarning,
                stacklevel=2,
            )
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        pool_cfg = DB_POOL_CONFIG_COLLECTOR if pool_type == "collector" else DB_POOL_CONFIG
        # 过滤掉 DB_CONFIG 中的 None 值和与 PooledDB 冲突的字段
        db_kwargs = {k: v for k, v in DB_CONFIG.items() if v is not None and k != "cursorclass"}
        # 强制 utf8mb4 + 禁止 NO_BACKSLASH_ESCAPES（避免反斜杠被转义）
        db_kwargs.setdefault("charset", "utf8mb4")
        db_kwargs.setdefault("init_command", "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        _pool = PooledDB(
            creator=pymysql,
            cursorclass=pymysql.cursors.DictCursor,
            **pool_cfg,
            **db_kwargs,
        )
        _pool_type = pool_type

        print(f"[db] 连接池已初始化（{pool_type}模式, "
              f"max={pool_cfg['maxconnections']}, "
              f"mincached={pool_cfg['mincached']}）")
        return _pool


def get_pool() -> PooledDB:
    """获取全局连接池（自动初始化默认 API 模式）"""
    if _pool is None:
        _init_pool("api")
    return _pool


def get_conn():
    """从全局连接池获取一个连接"""
    return get_pool().connection()


# ═══════════════════════════════════════════════════════════════════
#  news_data 连接池（独立单例）
# ═══════════════════════════════════════════════════════════════════

_news_pool: PooledDB | None = None
_news_pool_lock = threading.Lock()


def _init_news_pool() -> PooledDB:
    """创建 news_data 专用连接池（线程安全，只创建一次）"""
    global _news_pool
    if _news_pool is not None:
        return _news_pool

    with _news_pool_lock:
        if _news_pool is not None:
            return _news_pool

        db_kwargs = {k: v for k, v in NEWS_DB_CONFIG.items() if v is not None and k != "cursorclass"}
        # 强制 utf8mb4 + 禁止 NO_BACKSLASH_ESCAPES
        db_kwargs.setdefault("charset", "utf8mb4")
        db_kwargs.setdefault("init_command", "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        _news_pool = PooledDB(
            creator=pymysql,
            cursorclass=pymysql.cursors.DictCursor,
            **NEWS_DB_POOL_CONFIG,
            **db_kwargs,
        )
        print(f"[db] news_data 连接池已初始化（max={NEWS_DB_POOL_CONFIG['maxconnections']}）")
        return _news_pool


def get_news_conn():
    """从 news_data 连接池获取一个连接"""
    return _init_news_pool().connection()


@contextmanager
def get_news_cursor(commit: bool = False):
    """
    获取 news_data 游标的上下文管理器，自动释放连接。

    Args:
        commit: 是否在退出时自动 commit

    Yields:
        pymysql.cursors.DictCursor
    """
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  便捷上下文管理器
# ═══════════════════════════════════════════════════════════════════


@contextmanager
def get_cursor(commit: bool = False):
    """
    获取游标的上下文管理器，自动释放连接。

    Args:
        commit: 是否在退出时自动 commit

    Yields:
        pymysql.cursors.DictCursor

    使用示例：
        with get_cursor() as cur:
            cur.execute("SELECT * FROM stocks_info LIMIT 5")
            rows = cur.fetchall()

        with get_cursor(commit=True) as cur:
            cur.execute("INSERT INTO ...")
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  批量操作工具
# ═══════════════════════════════════════════════════════════════════

def batch_insert(sql: str, params: list[tuple], batch_size: int = 500) -> int:
    """
    高性能批量 INSERT（分批 executemany + 自动 commit）。

    Args:
        sql:     INSERT 语句（含 %s 占位符）
        params:  参数列表 [(v1, v2, ...), ...]
        batch_size: 每批行数（默认 500）

    Returns:
        总插入行数
    """
    if not params:
        return 0

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            total = 0
            for i in range(0, len(params), batch_size):
                batch = params[i:i + batch_size]
                cur.executemany(sql, batch)
                total += cur.rowcount
        conn.commit()
        return total
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def table_exists(table_name: str, database: str | None = None) -> bool:
    """检查表是否存在"""
    db = database or DB_CONFIG["database"]
    with get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (db, table_name),
        )
        return cur.fetchone() is not None


# ═══════════════════════════════════════════════════════════════════
#  启动预热
# ═══════════════════════════════════════════════════════════════════

def warmup(pool_type: str = "api"):
    """服务启动时预热连接池（创建 mincached 个连接）"""
    _init_pool(pool_type)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        conn.close()
    print(f"[db] 连接池预热完成")


# ═══════════════════════════════════════════════════════════════════
#  news_data 库自动初始化（懒建库，捕获 1049/1146 时触发）
# ═══════════════════════════════════════════════════════════════════

def init_news_db() -> None:
    """
    自动创建 news_data 数据库（若不存在）。

    使用裸连接（不指定 database），避免 ER_BAD_DB_ERROR(1049) 循环。
    由 insert_news / ensure_table_exists 在捕获到 1049 或 1146 时调用。
    完成后**不**重置连接池，调用方应直接重试业务操作。
    """
    from config.settings import NEWS_DB_CONFIG, NEWS_DB_NAME  # 延迟导入避免循环

    # 裸连接：去掉 database 参数，其余保持一致
    bare_cfg = {
        k: v
        for k, v in NEWS_DB_CONFIG.items()
        if k not in ("database", "cursorclass") and v is not None
    }
    bare_cfg.setdefault("charset", "utf8mb4")

    conn = pymysql.connect(
        cursorclass=pymysql.cursors.DictCursor,
        **bare_cfg,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{NEWS_DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[db] news_data 数据库已就绪（自动创建或已存在）")
    except Exception as e:
        print(f"[db] 创建 news_data 数据库失败: {e}")
        raise
    finally:
        conn.close()
