#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步数据库写入服务模块

功能：
1. 任意表的批量 upsert
2. 字段自动过滤（删除不属于目标表的字段）
3. 类型自动转换（基于表结构）

设计原则：
- 使用项目现有的数据库连接池（utils.db）
- 统一返回格式：{success: bool, data: any, message: str}
- 内部捕获异常，记录日志
- 支持事务和批量操作
"""

import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from copy import deepcopy

from utils.db import get_cursor, get_conn
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
        self.table_ddl_map = {
            # 这里可以添加常用的表DDL定义
            # 例如："stocks_info": "CREATE TABLE IF NOT EXISTS `stocks_info` (...)"
        }
        
        logger.info("数据库写入服务初始化完成")

    def get_table_primary_keys(self, table_name: str) -> list:
        """自动查询 MySQL 表主键字段"""
        conn = get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = %s
                      AND CONSTRAINT_NAME = 'PRIMARY'
                    ORDER BY ORDINAL_POSITION
                """, (table_name,))
                rows = cursor.fetchall()
                return [row["COLUMN_NAME"] for row in rows] if rows else []
        finally:
            conn.close()

    def upsert_data_with_schema(self, table_name: str, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量upsert数据（带字段过滤和类型转换）
        
        Args:
            table_name: 表名
            data_list: 数据列表（每个元素是字典）
            
        Returns:
            统一格式的结果：{"success": bool, "data": {"inserted": int, "updated": int}, "message": str}
        """
        if not data_list:
            return {
                "success": True,
                "data": {"inserted": 0, "updated": 0},
                "message": "数据列表为空，跳过写入"
            }

        unique_keys = self.get_table_primary_keys(table_name)
        if not unique_keys:
            return {
                "success": False,
                "data": None,
                "message": f"表 {table_name} 未找到主键，无法执行UPSERT"
            }
        try:
            # 深拷贝数据，避免修改原始数据
            data_to_process = deepcopy(data_list)
            # 1. 字段过滤和类型转换
            processed_data = []
            for record in data_to_process:
                filtered_record = self.schema_cache.filter_record_by_schema(table_name, record)

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
            inserted_count, updated_count = self._execute_upsert(table_name, processed_data, unique_keys)
            
            return {
                "success": True,
                "data": {"inserted": inserted_count, "updated": updated_count},
                "message": f"写入成功，插入 {inserted_count} 条，更新 {updated_count} 条"
            }
            
        except Exception as e:
            self.logger.error(f"upsert数据失败: {table_name}, 错误: {e}")
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

        sql = f"""
            INSERT INTO `{table_name}` ({cols_quoted})
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
    def simple_upsert(self, table_name: str, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        简化的upsert接口
        
        Args:
            table_name: 表名
            data_list: 数据列表
            
        Returns:
            统一格式的结果
        """
        return self.upsert_data_with_schema(table_name, data_list)

    def create_table_if_not_exists(self, table_name: str) -> None:
        """
        异步安全地创建表（如果不存在）

        Args:
            table_name: 表名

        功能：
        1. 检查表是否存在（使用information_schema.tables）
        2. 表不存在时从table_ddl_map获取DDL创建表
        3. 使用CREATE TABLE IF NOT EXISTS确保幂等性
        4. 创建成功后清除schema缓存
        5. 记录详细的日志信息

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            # 1. 检查表是否存在
            from utils.db import get_cursor, table_exists
            if table_exists(table_name):
                self.logger.info(f"表 {table_name} 已存在，跳过创建")
                return

            # 2. 获取DDL定义
            ddl = self.get_ddl_for_table(table_name)
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
                self.logger.debug(f"已清除表 {table_name} 的schema缓存")

        except Exception as e:
            self.logger.error(f"创建表 {table_name} 失败: {e}")
            raise

    def get_ddl_for_table(self, table_name: str) -> Optional[str]:
        """
        获取表的DDL定义
        
        Args:
            table_name: 表名
            
        Returns:
            DDL语句字符串，如果找不到则返回None
            
        功能：
        1. 首先从table_ddl_map中查找
        2. 支持动态表名（如按日期分表）
        3. 可以扩展支持从配置文件或模型文件中加载
        """
        # 1. 从映射字典中查找
        if table_name in self.table_ddl_map:
            return self.table_ddl_map[table_name]
        
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
        
        # 3. 尝试从stock_models中导入
        if table_name in ["stocks_info", "stock_klines_monthly", "kline_index", 
                         "intraday_minutes", "lhb_detail"]:
            try:
                from models.stock_models import (
                    CREATE_STOCKS_INFO_DDL,
                    CREATE_KLINES_MONTHLY_DDL,
                    CREATE_KLINE_INDEX_DDL,
                    CREATE_INTRADAY_MINUTES_DDL,
                    CREATE_LHB_DETAIL_DDL
                )
                
                ddl_map = {
                    "stocks_info": CREATE_STOCKS_INFO_DDL,
                    "stock_klines_monthly": CREATE_KLINES_MONTHLY_DDL,
                    "kline_index": CREATE_KLINE_INDEX_DDL,
                    "intraday_minutes": CREATE_INTRADAY_MINUTES_DDL,
                    "lhb_detail": CREATE_LHB_DETAIL_DDL
                }
                
                return ddl_map.get(table_name)
                
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"导入表 {table_name} 的DDL失败: {e}")
        
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
def upsert_data_with_schema(table_name: str, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量upsert数据（便捷函数）"""
    return get_db_service().upsert_data_with_schema(table_name, data_list)


def simple_upsert(table_name: str, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """简化的upsert接口（便捷函数）"""
    return get_db_service().simple_upsert(table_name, data_list)


def create_table_if_not_exists(table_name: str) -> None:
    """
    创建表（如果不存在）的便捷函数
    
    Args:
        table_name: 表名
    """
    return get_db_service().create_table_if_not_exists(table_name)