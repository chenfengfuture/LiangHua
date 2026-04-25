#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表结构缓存模块

功能：
1. 加载目标表的所有字段名、字段类型、默认值
2. 提供方法：get_table_columns(table_name) -> List[str]
3. 提供方法：cast_value_by_column(table_name, col, value) 根据字段类型转换值
4. 缓存表结构，避免每次写入都查库

设计原则：
- 使用 pymysql 查询 INFORMATION_SCHEMA.COLUMNS
- 缓存到内存字典，TTL 可配置
- 线程安全
- 统一异常处理
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, date

from utils.db import get_cursor

logger = logging.getLogger(__name__)


class SchemaCache:
    """
    表结构缓存类
    """
    
    def __init__(self, cache_ttl_seconds: int = 600):
        """
        初始化表结构缓存
        
        Args:
            cache_ttl_seconds: 缓存过期时间（秒），默认10分钟
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # 缓存结构：table_name -> {"columns": Set[str], "column_types": Dict[str, str], "timestamp": float}
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 线程锁
        self._lock = threading.RLock()
        
        logger.info(f"表结构缓存初始化完成，缓存TTL: {cache_ttl_seconds}秒")
    
    def get_table_columns(self, table_name: str) -> Set[str]:
        """
        获取表的字段列表
        
        Args:
            table_name: 表名
            
        Returns:
            字段名集合
        """
        table_info = self._get_or_load_table_info(table_name)
        return table_info.get("columns", set())
    
    def get_column_type(self, table_name: str, column_name: str) -> str:
        """
        获取字段类型
        
        Args:
            table_name: 表名
            column_name: 字段名
            
        Returns:
            字段类型（如 "varchar", "int", "datetime"）
        """
        table_info = self._get_or_load_table_info(table_name)
        column_types = table_info.get("column_types", {})
        return column_types.get(column_name, "varchar")
    
    def cast_value_by_column(self, table_name: str, column_name: str, value: Any) -> Any:
        """
        根据字段类型转换值
        
        Args:
            table_name: 表名
            column_name: 字段名
            value: 原始值
            
        Returns:
            转换后的值
        """
        if value is None:
            return None
        
        column_type = self.get_column_type(table_name, column_name).lower()
        
        try:
            # 根据字段类型进行转换
            if column_type in ("int", "tinyint", "smallint", "mediumint", "bigint"):
                return self._cast_to_int(value)
            elif column_type in ("float", "double", "decimal", "numeric"):
                return self._cast_to_float(value)
            elif column_type in ("date", "datetime", "timestamp"):
                return self._cast_to_datetime(value)
            elif column_type in ("bool", "boolean"):
                return self._cast_to_bool(value)
            else:
                # 字符串类型
                return self._cast_to_string(value)
        except Exception as e:
            logger.warning(f"字段类型转换失败: {table_name}.{column_name}={value} -> {column_type}, 错误: {e}")
            return value
    
    def filter_record_by_schema(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据表结构过滤记录字段
        
        Args:
            table_name: 表名
            record: 原始记录
            
        Returns:
            过滤后的记录（深拷贝）
        """
        # 深拷贝原始记录
        filtered_record = record.copy()
        
        # 获取表的字段列表
        table_columns = self.get_table_columns(table_name)
        
        # 过滤掉不在表结构中的字段
        keys_to_remove = [key for key in filtered_record.keys() if key not in table_columns]
        for key in keys_to_remove:
            del filtered_record[key]
        
        # 对每个字段进行类型转换
        for key, value in filtered_record.items():
            if value is not None:
                filtered_record[key] = self.cast_value_by_column(table_name, key, value)
        
        return filtered_record
    
    def _get_or_load_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取或加载表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        with self._lock:
            # 检查缓存是否有效
            cache_entry = self._cache.get(table_name)
            if cache_entry and time.time() - cache_entry.get("timestamp", 0) < self.cache_ttl_seconds:
                return cache_entry
            
            # 加载表结构
            table_info = self._load_table_info_from_db(table_name)
            self._cache[table_name] = table_info
            return table_info
    
    def _load_table_info_from_db(self, table_name: str) -> Dict[str, Any]:
        """
        从数据库加载表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        try:
            with get_cursor() as cur:
                # 查询表结构
                query = """
                    SELECT 
                        COLUMN_NAME, 
                        DATA_TYPE,
                        COLUMN_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """
                cur.execute(query, (table_name,))
                columns = cur.fetchall()

                if not columns:
                    logger.warning(f"表 {table_name} 不存在，尝试自动创建...")

                    # 在这里创建表（你自己的 DBService 方法）
                    from system_service.db_service import DBService
                    db_service = DBService(use_lock=False)  # 临时实例，不影响锁
                    db_service.create_table_if_not_exists(table_name)
                    time.sleep(1)
                    # 表创建后，重新查询一次表结构
                    with get_cursor() as new_cur:
                        new_cur.execute(query, (table_name,))
                        columns = new_cur.fetchall()

                    # 如果还是没有，才真正返回空
                    if not columns:
                        logger.error(f"表 {table_name} 创建后仍然无法获取结构！")
                        return {
                            "columns": set(),
                            "column_types": {},
                            "timestamp": time.time()
                        }
                
                # 构建字段信息
                column_set = set()
                column_types = {}
                
                for col in columns:
                    column_name = col["COLUMN_NAME"]
                    data_type = col["DATA_TYPE"]
                    
                    column_set.add(column_name)
                    column_types[column_name] = data_type
                
                logger.info(f"加载表结构成功: {table_name}, 字段数: {len(column_set)}")
                
                return {
                    "columns": column_set,
                    "column_types": column_types,
                    "timestamp": time.time()
                }
                
        except Exception as e:
            logger.error(f"加载表结构失败: {table_name}, 错误: {e}")
            return {
                "columns": set(),
                "column_types": {},
                "timestamp": time.time()
            }
    
    def _cast_to_int(self, value: Any) -> Optional[int]:
        """转换为整数"""
        if isinstance(value, (int, float)):
            return int(value)
        elif isinstance(value, str):
            # 尝试提取数字
            import re
            match = re.search(r'[-+]?\d+', value)
            if match:
                return int(match.group())
            # 如果是空字符串或非数字字符串
            if not value.strip():
                return None
        return None
    
    def _cast_to_float(self, value: Any) -> Optional[float]:
        """转换为浮点数"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # 尝试提取数字（包括小数）
            import re
            match = re.search(r'[-+]?\d*\.?\d+', value)
            if match:
                return float(match.group())
            # 如果是空字符串或非数字字符串
            if not value.strip():
                return None
        return None
    
    def _cast_to_datetime(self, value: Any) -> Optional[str]:
        """转换为日期时间字符串"""
        if isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, str):
            # 尝试解析常见日期格式
            try:
                # 尝试 ISO 格式
                if "T" in value:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                # 尝试 YYYY-MM-DD HH:MM:SS 格式
                elif len(value) == 19 and value[4] == "-" and value[7] == "-":
                    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                # 尝试 YYYY-MM-DD 格式
                elif len(value) == 10 and value[4] == "-" and value[7] == "-":
                    dt = datetime.strptime(value, "%Y-%m-%d")
                else:
                    # 其他格式，尝试自动解析
                    from dateutil import parser
                    dt = parser.parse(value)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return value
        return None
    
    def _cast_to_bool(self, value: Any) -> Optional[int]:
        """转换为布尔值（存储为0/1）"""
        if isinstance(value, bool):
            return 1 if value else 0
        elif isinstance(value, int):
            return 1 if value != 0 else 0
        elif isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "yes", "1", "t", "y"):
                return 1
            elif value_lower in ("false", "no", "0", "f", "n"):
                return 0
        return None
    
    def _cast_to_string(self, value: Any) -> str:
        """转换为字符串"""
        if value is None:
            return ""
        return str(value)


# 全局表结构缓存实例
_schema_cache_instance: Optional[SchemaCache] = None
_schema_cache_lock = threading.Lock()


def get_schema_cache() -> SchemaCache:
    """
    获取表结构缓存实例（单例模式）
    
    Returns:
        SchemaCache实例
    """
    global _schema_cache_instance
    if _schema_cache_instance is None:
        with _schema_cache_lock:
            if _schema_cache_instance is None:
                _schema_cache_instance = SchemaCache()
    return _schema_cache_instance


# 导出函数
__all__ = [
    "SchemaCache",
    "get_schema_cache",
    "get_table_columns",
    "cast_value_by_column",
    "filter_record_by_schema",
]


# 便捷函数
def get_table_columns(table_name: str) -> Set[str]:
    """获取表的字段列表（便捷函数）"""
    return get_schema_cache().get_table_columns(table_name)


def cast_value_by_column(table_name: str, column_name: str, value: Any) -> Any:
    """根据字段类型转换值（便捷函数）"""
    return get_schema_cache().cast_value_by_column(table_name, column_name, value)


def filter_record_by_schema(table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """根据表结构过滤记录字段（便捷函数）"""
    return get_schema_cache().filter_record_by_schema(table_name, record)