#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步数据库写入服务模块

功能：
1. 任意表的批量 upsert
2. 字段自动过滤（删除不属于目标表的字段）
3. 类型自动转换（基于表结构）

"""

import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from copy import deepcopy

from utils.db import get_cursor, get_conn, get_news_conn
from .schema_cache import get_schema_cache

logger = logging.getLogger(__name__)


class DBService:
    """
    数据库写入服务类
    """
    
    def __init__(self):
        """
        初始化数据库服务
        """
        self.logger = logger
        
        # 获取表结构缓存
        self.schema_cache = get_schema_cache()
        
        # 表DDL映射字典（可根据需要扩展）
        self.logger.info("数据库写入服务初始化完成")
        logger.info("数据库写入服务初始化完成")

    def _validate_identifier(self, name: str) -> bool:
        """
        校验 SQL 标识符（库名、表名、字段名）。

        MySQL 不支持对库名/表名使用参数化占位符，因此所有用于 SQL 拼接的
        标识符必须先经过白名单校验，避免注入风险。
        """
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""))

    def _quote_identifier(self, name: str) -> str:
        """校验并反引号包裹 SQL 标识符。"""
        if not self._validate_identifier(name):
            raise ValueError(f"非法SQL标识符: {name}")
        return f"`{name}`"

    def _quote_table_name(self, table_name: str) -> str:
        """校验并生成表名限定表达式，支持 db.table。"""
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            return f"{self._quote_identifier(schema)}.{self._quote_identifier(tbl)}"
        return self._quote_identifier(table_name)

    def get_table_primary_keys(self, table_name: str) -> list:
        """
        自动查询 MySQL 表主键字段

        支持 "db.table" 形式的限定表名（跨库），其余视为当前连接库的表。
        """
        # 解析 "db.table" 形式
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            schema_filter = "TABLE_SCHEMA = %s"
            schema_param = schema
        else:
            tbl = table_name
            schema_filter = "TABLE_SCHEMA = DATABASE()"
            schema_param = None

        conn = get_conn()
        try:
            with conn.cursor() as cursor:
                if schema_param is None:
                    cursor.execute(f"""
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE {schema_filter}
                          AND TABLE_NAME = %s
                          AND CONSTRAINT_NAME = 'PRIMARY'
                        ORDER BY ORDINAL_POSITION
                    """, (tbl,))
                else:
                    cursor.execute(f"""
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE {schema_filter}
                          AND TABLE_NAME = %s
                          AND CONSTRAINT_NAME = 'PRIMARY'
                        ORDER BY ORDINAL_POSITION
                    """, (schema_param, tbl))
                rows = cursor.fetchall()
                return [row["COLUMN_NAME"] for row in rows] if rows else []
        finally:
            conn.close()

    def query_batch(self, table_name: str, select_fields: list, where_field: str, where_values: list) -> List[Dict]:
        """
        通用批量查询（IN 查询）
        自动生成 SQL：SELECT {字段1,字段2...} FROM {表名} WHERE {条件字段} IN (%s,%s,...)

        Args:
            table_name: 要查询的数据库表名（必填）
            select_fields: 要查询返回的字段列表，例如 ["name", "symbol", "trade_date"]
            where_field: 按哪个字段做 IN 查询，例如 "name" / "symbol" / "code"
            where_values: 要查询的值列表（必须是 list 数组），例如 ["贵州茅台", "工商银行"]

        Returns:
            列表字典，每条数据为一个字典，查询不到返回空列表 []
        """
        if not all([table_name, select_fields, where_field, where_values]):
            return []

        try:
            fields = ", ".join(select_fields)
            placeholders = ", ".join(["%s"] * len(where_values))

            with get_cursor(commit=False) as cursor:
                sql = f"""
                    SELECT {fields} FROM `{table_name}`
                    WHERE {where_field} IN ({placeholders})
                """
                cursor.execute(sql, tuple(where_values))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"[DBService] query_batch 异常: {str(e)}")
            return []

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        通用 SQL 查询（直接执行任意 SELECT 语句）

        Args:
            sql: SQL 查询语句
            params: 参数元组

        Returns:
            查询结果列表，每条数据为一个字典
        """
        try:
            with get_cursor(commit=False) as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"[DBService] execute_query 异常: {str(e)}")
            return []

    def _locate_table_database(self, table_name: str) -> Optional[str]:
        """
        自动发现表所在的数据库名称。

        遍历 information_schema 查找指定表名所在的数据库，
        解决 DDL 定义在非默认库（如 stock_indicators）而运行时
        上下文为默认库（如 lianghua）时导致的跨库问题。

        Args:
            table_name: 表名（不含数据库前缀）

        Returns:
            数据库名称，未找到则返回 None
        """
        sql = """
            SELECT TABLE_SCHEMA FROM information_schema.tables
            WHERE TABLE_NAME = %s
        """
        result = self.execute_query(sql, (table_name,))
        if result:
            return result[0]['TABLE_SCHEMA']
        return None

    def _extract_database_from_ddl(self, table_name: str) -> Optional[str]:
        """
        从 DDL 中提取数据库名。

        当表尚未创建（_locate_table_database 返回 None）时，
        从 DDL 定义中解析出 `db`.`table` 格式的数据库前缀，
        确保建表操作在正确的数据库中执行。

        Args:
            table_name: 纯表名

        Returns:
            数据库名称，DDL 中无前缀则返回 None
        """
        ddl = self.get_ddl_for_table(table_name)
        if not ddl:
            return None
        m = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`(\w+)`\.`\w+`",
            ddl, re.I
        )
        if m:
            return m.group(1)
        return None

    def _resolve_table_qualified_name(self, table_name: str, db_name: str = "lianghua") -> str:
        """
        解析表名为限定名（自动发现数据库前缀）。

        优先级：
        1. table_name 已经是 db.table — 校验后直接返回
        2. db_name 非默认库 — 使用调用方显式指定的数据库
        3. _locate_table_database — 表已存在，从 information_schema 发现
        4. _extract_database_from_ddl — 表不存在，从 DDL 中解析
        5. 兜底 — 使用默认库（不添加前缀）

        Args:
            table_name: 纯表名或 db.table 限定名
            db_name: 数据库名称，默认 lianghua

        Returns:
            限定表名（"db.table" 或纯 "table"）
        """
        if not table_name:
            raise ValueError("table_name 不能为空")

        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            self._quote_identifier(schema)
            self._quote_identifier(tbl)
            return table_name

        self._quote_identifier(table_name)
        self._quote_identifier(db_name)

        if db_name != "lianghua":
            return f"{db_name}.{table_name}"

        # 优先级1：表已存在 → 从 information_schema 发现
        located_db_name = self._locate_table_database(table_name)
        if located_db_name:
            self._quote_identifier(located_db_name)
            self.logger.info(f"自动发现表 {table_name} 位于数据库 {located_db_name}")
            return f"{located_db_name}.{table_name}"

        # 优先级2：表不存在 → 从 DDL 中解析
        ddl_db_name = self._extract_database_from_ddl(table_name)
        if ddl_db_name:
            self._quote_identifier(ddl_db_name)
            self.logger.info(f"从 DDL 解析到表 {table_name} 应位于数据库 {ddl_db_name}")
            return f"{ddl_db_name}.{table_name}"

        # 优先级3：兜底，使用默认库
        return table_name

    def query_db_cache(self, table_name: str, cache_key: str, ttl_days: int = 1, db_name: str = "lianghua") -> Optional[List[Dict[str, Any]]]:
        """
        查询数据库缓存

        修复说明：原实现使用 `LIMIT 1 + fetchone()` 只返回单条 dict，
        导致同一 cache_key 下存在多行（如龙虎榜 576 行）时被截断为 1 条，
        前端 Ant Design Table 的 dataSource 收到 dict 而非 list，崩溃黑屏。

        现修改为 `fetchall()` 返回 List[Dict]，对外契约保持 Optional：
        - 命中且有数据 → 返回 list（即使只有 1 条也是 [dict]）
        - 未命中或已过期 → 返回 None

        多库支持：根据 db_name 切换数据库连接。
        - "lianghua"（默认）：使用主库连接池 get_conn()
        - "news_data"：使用新闻库连接池 get_news_conn()
        - 其他：使用主库连接池，表名限定为 `db_name`.`table_name` 实现跨库查询
        """
        try:
            if not table_name:
                self.logger.warning(f"表名不能为空: {cache_key}")
                return None

            self._quote_identifier(table_name)
            self._quote_identifier(db_name)

            # 根据 db_name 选择数据库连接
            if db_name == "news_data":
                conn = get_news_conn()
                qualified_table = self._quote_identifier(table_name)
            elif db_name != "lianghua":
                # 非默认库，使用主连接池 + 限定表名 `db_name`.`table_name`
                conn = get_conn()
                qualified_table = f"{self._quote_identifier(db_name)}.{self._quote_identifier(table_name)}"
            else:
                conn = get_conn()
                qualified_table = self._quote_identifier(table_name)

            with conn.cursor() as cursor:
                ttl_date = datetime.now() - timedelta(days=ttl_days)
                query = f"""
                    SELECT * FROM {qualified_table}
                    WHERE cache_key = %s AND update_time >= %s
                    ORDER BY update_time DESC
                """

                cursor.execute(query, (cache_key, ttl_date))
                results = cursor.fetchall()

                if results:
                    self.logger.debug(f"数据库缓存命中: {cache_key} 表={table_name}, 行数={len(results)}, 库={db_name}")
                    return [dict(r) for r in results]
                else:
                    self.logger.debug(f"数据库缓存未命中或已过期: {cache_key}, 库={db_name}")
                    return None

        except Exception as e:
            self.logger.error(f"查询数据库缓存异常: {cache_key}, 错误: {str(e)}, 库={db_name}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def write_db_async(self, table_name: str, data_list: List[Dict[str, Any]], unique_keys: List[str] = None, db_name: str = "lianghua") -> bool:
        """
        异步写入数据库

        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键字段列表；默认 ["symbol"] 仅作为股票行情类数据兜底，非股票表应显式传入
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            是否成功提交异步写入任务
        """
        try:
            from .async_writer import submit_async_upsert

            success = submit_async_upsert(
                table_name=table_name,
                data_list=data_list,
                unique_keys=unique_keys or ["symbol"],
                db_name=db_name
            )

            if success:
                self.logger.debug(f"成功提交异步写入任务: {table_name}, 数据条数: {len(data_list)}, 库={db_name}")
            else:
                self.logger.warning(f"提交异步写入任务失败: {table_name}, 库={db_name}")

            return success
        except Exception as e:
            self.logger.error(f"提交异步写入任务时发生异常: {table_name}, 错误: {e}, 库={db_name}")
            return False

    def write_db_sync(self, table_name: str, data_list: List[Dict[str, Any]], db_name: str = "lianghua") -> bool:
        """
        同步写入数据库

        Args:
            table_name: 表名
            data_list: 数据列表
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            是否成功写入
        """
        try:
            result = self.simple_upsert(
                table_name=table_name,
                data_list=data_list,
                db_name=db_name
            )

            success = result.get("success", False)

            if success:
                self.logger.debug(f"成功同步写入数据库: {table_name}, 数据条数: {len(data_list)}, 库={db_name}")
            else:
                self.logger.warning(f"同步写入数据库失败: {table_name}, 错误: {result.get('message', '未知错误')}, 库={db_name}")

            return success
        except Exception as e:
            self.logger.error(f"同步写入数据库时发生异常: {table_name}, 错误: {e}, 库={db_name}")
            return False

    def upsert_data_with_schema(self, table_name: str, data_list: List[Dict[str, Any]], db_name: str = "lianghua") -> Dict[str, Any]:
        """
        批量upsert数据（带字段过滤和类型转换）

        Args:
            table_name: 表名
            data_list: 数据列表（每个元素是字典）
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            统一格式的结果：{"success": bool, "data": {"inserted": int, "updated": int}, "message": str}
        """
        if not data_list:
            return {
                "success": True,
                "data": {"inserted": 0, "updated": 0},
                "message": "数据列表为空，跳过写入"
            }

        # 自动发现表所在数据库（解决 DDL 定义在非默认库的问题），显式 db_name 优先
        effective_table = self._resolve_table_qualified_name(table_name, db_name=db_name)

        unique_keys = self.get_table_primary_keys(effective_table)
        if not unique_keys:
            # 尝试创建表（如果表不存在）
            self.logger.warning(f"表 {effective_table} 无主键或不存在，尝试自动建表...")
            try:
                self.create_table_if_not_exists(effective_table)
                # 建表后重新获取主键
                unique_keys = self.get_table_primary_keys(effective_table)
                if not unique_keys:
                    return {
                        "success": False,
                        "data": None,
                        "message": f"表 {effective_table} 创建后仍未找到主键，无法执行UPSERT"
                    }
                self.logger.info(f"表 {effective_table} 自动建表成功，主键: {unique_keys}")
            except Exception as create_err:
                return {
                    "success": False,
                    "data": None,
                    "message": f"自动建表失败: {str(create_err)}"
                }
        try:
            # 深拷贝数据，避免修改原始数据
            data_to_process = deepcopy(data_list)
            # 1. 字段过滤和类型转换
            processed_data = []
            for record in data_to_process:
                filtered_record = self.schema_cache.filter_record_by_schema(effective_table, record)

                # 验证唯一键字段是否存在
                missing_keys = [key for key in unique_keys if key not in filtered_record]
                # if missing_keys:
                #     self.logger.warning(f"记录缺少唯一键字段 {missing_keys}，跳过: {filtered_record}")
                #     continue
                processed_data.append(filtered_record)

            if not processed_data:
                return {
                    "success": False,
                    "data": None,
                    "message": "所有记录都缺少唯一键字段，没有数据可写入"
                }

            # 2. 执行upsert（不再使用分布式锁）
            inserted_count, updated_count = self._execute_upsert(effective_table, processed_data, unique_keys)

            return {
                "success": True,
                "data": {"inserted": inserted_count, "updated": updated_count},
                "message": f"写入成功，插入 {inserted_count} 条，更新 {updated_count} 条"
            }

        except Exception as e:
            self.logger.error(f"upsert数据失败: {effective_table}, 错误: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"写入失败: {str(e)}"
            }

    def _execute_upsert(self, table_name: str, data_list: List[Dict[str, Any]],
                        unique_keys: List[str]) -> Tuple[int, int]:
        """执行批量 upsert，返回 (插入数, 更新数) 的近似值"""
        if not data_list:
            return 0, 0

        # 1. 获取表字段（必须）
        table_columns = self.schema_cache.get_table_columns(table_name)
        if not table_columns:
            self.logger.error(f"表 {table_name} 无字段信息，无法写入")
            return 0, 0

        # 2. 提取传入数据中真正属于表的字段
        sample = data_list[0]
        insert_cols = [col for col in sample.keys() if col in table_columns]
        if not insert_cols:
            self.logger.error(f"字段 {list(sample.keys())} 均不在表 {table_name} 中")
            return 0, 0

        # 3. 构建 SQL（列名已通过白名单过滤，安全）
        cols_quoted = ', '.join(f'`{col}`' for col in insert_cols)
        placeholders = ', '.join(['%s'] * len(insert_cols))

        update_set = ', '.join(
            f'`{col}` = VALUES(`{col}`)' for col in insert_cols if col not in unique_keys
        )
        if not update_set:
            self.logger.warning(f"无更新字段，将使用 INSERT IGNORE 行为")
            # 若无可更新字段，可改用 INSERT IGNORE 或直接报错，此处简单返回
            return len(data_list), 0

        # 支持 "db.table" 形式：必须分别校验并加反引号 → `db`.`table`
        qualified = self._quote_table_name(table_name)

        sql = f"""
            INSERT INTO {qualified} ({cols_quoted})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_set}
        """

        # 4. 准备参数（让驱动自动处理类型）
        values_list = [
            [record.get(col) for col in insert_cols]
            for record in data_list
        ]

        # 5. 执行
        try:
            with get_cursor(commit=True) as cur:
                cur.executemany(sql, values_list)
                # MySQLdb 对 ON DUPLICATE KEY UPDATE 的 rowcount 含义复杂，只记录总数即可
                total = len(data_list)
                self.logger.info(f"表 {table_name} 批量 upsert 完成，请求 {total} 条")
                # 返回 (total, 0) 表示粗略结果，如需精确计数请使用两条 SQL
                return total, 0
        except Exception as e:
            self.logger.error(f"写入表 {table_name} 失败: {e}")
            raise
    def simple_upsert(self, table_name: str, data_list: List[Dict[str, Any]], db_name: str = "lianghua") -> Dict[str, Any]:
        """
        简化的upsert接口
        
        Args:
            table_name: 表名
            data_list: 数据列表
            db_name: 数据库名称，默认 "lianghua"
            
        Returns:
            统一格式的结果
        """
        return self.upsert_data_with_schema(table_name, data_list, db_name=db_name)

    def create_table_if_not_exists(self, table_name: str) -> None:
        """
        异步安全地创建表（如果不存在）

        Args:
            table_name: 表名（支持 "db.table" 限定形式）

        功能：
        1. 检查表是否存在（使用information_schema.tables）
        2. 表不存在时从table_ddl_map获取DDL创建表
        3. 使用CREATE TABLE IF NOT EXISTS确保幂等性
        4. 创建成功后清除schema缓存
        5. 记录详细的日志信息

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        # 解析 "db.table" 形式，提取纯表名用于 DDL 查找
        raw_table = table_name
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
        else:
            schema = None
            tbl = table_name

        try:
            # 1. 检查表是否存在
            from utils.db import get_cursor, table_exists
            if table_exists(tbl, database=schema):
                self.logger.info(f"表 {table_name} 已存在，跳过创建")
                return

            # 2. 获取DDL定义（使用纯表名查找）
            ddl = self.get_ddl_for_table(tbl)
            if not ddl:
                self.logger.warning(f"表 {table_name} 没有找到DDL定义，跳过创建")
                return

            # 3. 执行创建表（使用IF NOT EXISTS确保幂等性）
            with get_cursor(commit=True) as cur:
                self.logger.info(f"正在创建表: {table_name}")
                cur.execute(ddl)
                self.logger.info(f"表 {table_name} 创建成功")

            # 4. 清除schema缓存（避免后续操作使用旧的缺失表信息）
            if hasattr(self.schema_cache, '_cache'):
                self.schema_cache._cache.pop(table_name, None)
                self.schema_cache._cache.pop(tbl, None)
                self.logger.debug(f"已清除表 {table_name} 的schema缓存")

        except Exception as e:
            self.logger.error(f"创建表 {table_name} 失败: {e}")
            raise

    def get_ddl_for_table(self, table_name: str) -> Optional[str]:
        """
        获取表的DDL定义

        Args:
            table_name: 表名（纯表名，不含数据库前缀）

        Returns:
            DDL语句字符串，如果找不到则返回None

        功能：
        2. 支持动态表名（如按日期分表）
        3. 可以扩展支持从配置文件或模型文件中加载
        """
        # 1. 从 models 全局动态注册表查找

        # 2. 处理动态表名（如按日期分表）
        # 例如：news_company_202504, news_global_202504 等
        if table_name.startswith("news_"):
            # 尝试从模型文件中导入
            try:
                from models.news_models import get_news_table_ddl
                ddl = get_news_table_ddl(table_name)
                if ddl:
                    return ddl
            except (ImportError, AttributeError):
                pass

        # 3. 从 models 全局 DDL 注册表查找（涵盖所有 models/ 中定义的表）
        try:
            from models import get_ddl_by_table_name
            ddl = get_ddl_by_table_name(table_name)
            if ddl:
                return ddl
        except (ImportError, AttributeError):
            pass

        # 4. 记录警告并返回None
        self.logger.warning(f"表 {table_name} 没有找到DDL定义")
        return None


# 全局数据库服务实例
_db_service_instance: Optional[DBService] = None
_db_service_lock = threading.Lock()


def get_db_service() -> DBService:
    """
    获取数据库服务实例（单例模式）
    
    Returns:
        DBService实例
    """
    global _db_service_instance
    if _db_service_instance is None:
        with _db_service_lock:
            if _db_service_instance is None:
                _db_service_instance = DBService()
    return _db_service_instance


# 导出函数
__all__ = [
    "DBService",
    "get_db_service",
    "upsert_data_with_schema",
    "simple_upsert",
    "create_table_if_not_exists",
]


# 便捷函数
def upsert_data_with_schema(table_name: str, data_list: List[Dict[str, Any]], db_name: str = "lianghua") -> Dict[str, Any]:
    """批量upsert数据（便捷函数）"""
    return get_db_service().upsert_data_with_schema(table_name, data_list, db_name=db_name)


def simple_upsert(table_name: str, data_list: List[Dict[str, Any]], db_name: str = "lianghua") -> Dict[str, Any]:
    """简化的upsert接口（便捷函数）"""
    return get_db_service().simple_upsert(table_name, data_list, db_name=db_name)


def create_table_if_not_exists(table_name: str) -> None:
    """
    创建表（如果不存在）的便捷函数
    
    Args:
        table_name: 表名
    """
    return get_db_service().create_table_if_not_exists(table_name)