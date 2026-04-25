#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据服务基类模块 - BaseStockService

设计目标：为所有股票数据服务提供统一的数据获取流程编排
核心功能：通过标准化的"缓存优先 → 分布式锁防击穿 → 调用数据源 → 异步持久化"流程
消除重复代码，确保所有数据接口行为一致。

架构分层：
1. 底层：system_service 提供原子能力（Redis、分布式锁、数据库 upsert、异步队列）
2. 中层：BaseStockService 基类提供流程编排
3. 上层：具体业务服务（如 StockBasicService）实现参数验证、数据源调用、数据映射
"""


import json
import logging
import time
import hashlib
from typing import Any, Dict, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from system_service.exception_handler import ValidationException

from system_service import (
    success_result,
    error_result,
    submit_async_upsert,
    simple_upsert,
)

# 导入 Redis 服务基类
from system_service.redis_service import RedisServiceBase

# 导入工具层
from utils.db import get_conn, get_cursor

logger = logging.getLogger(__name__)


class BaseStockService(RedisServiceBase):
    """
    股票数据服务基类（抽象基类）
    
    为所有股票数据服务提供统一的数据获取流程编排，通过标准化的
    "缓存优先 → 分布式锁防击穿 → 调用数据源 → 异步持久化"流程，
    消除重复代码，确保所有数据接口行为一致。
    
    核心方法：execute_cached_fetch - 完整的缓存获取模板方法
    
    执行流程：
    1. 参数校验（可选）：调用子类提供的验证函数，失败则直接返回错误
    2. 生成缓存键与锁键：根据 table_name 和参数字典生成唯一标识
    3. 查 Redis 缓存（一级）：若命中，立即返回数据（毫秒级响应）
    4. 查数据库缓存（二级）：若 Redis 未命中，查询业务表，检查 update_time 是否在 TTL 内
    5. 获取分布式锁：使用 Redis 锁防止缓存击穿，失败则重试
    6. Double-check：获得锁后，再次查询数据库缓存（防止在等待锁期间被其他线程更新）
    7. 调用数据源（fetch_func）：执行子类传入的获取数据函数
    8. 处理空数据：若数据为空且 cache_empty=False，直接返回空结果
    9. 写入数据库：根据 async_write 参数决定异步或同步写入
    10. 更新 Redis 缓存：将数据写入 Redis，设置 TTL
    11. 释放分布式锁：在 finally 中确保释放
    12. 返回结果：统一格式 {success, data, message}
    """
    
    # Redis TTL 常量（秒）
    REDIS_TTL_SHORT = 300      # 5分钟 - 短期缓存
    REDIS_TTL_MEDIUM = 1800    # 30分钟 - 中期缓存  
    REDIS_TTL_LONG = 86400     # 24小时 - 长期缓存
    REDIS_TTL_EMPTY = 60       # 1分钟 - 空数据缓存
    
    # 分布式锁配置
    LOCK_TIMEOUT = 30          # 锁超时时间（秒）
    LOCK_RETRY_COUNT = 3       # 获取锁重试次数
    LOCK_RETRY_DELAY = 0.1     # 重试间隔（秒）
    
    # 数据库缓存配置
    DB_CACHE_TTL_DAYS = 1      # 数据库缓存默认TTL（天）
    
    def __init__(self, service_name: str):
        """
        初始化股票数据服务基类
        
        Args:
            service_name: 服务名称，用于日志和缓存前缀
        """
        # 调用父类 RedisServiceBase 的初始化
        super().__init__(service_name)
        
        # 数据库缓存配置
        self.db_cache_ttl_days = self.DB_CACHE_TTL_DAYS
        
        self.logger.info(f"股票数据服务基类初始化完成: {service_name}")
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息（抽象方法，子类必须实现）
        
        Returns:
            服务信息字典，包含服务名称、描述、配置等
        """
        pass
    
    def generate_cache_key(self, table_name: str, params: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            table_name: 缓存前缀
            params: 参数字典
            
        Returns:
            缓存键字符串
        """
        # 将参数字典序列化为字符串
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        # 生成MD5哈希
        params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()[:8]
        # 组合缓存键
        cache_key = f"stock:{table_name}:{params_hash}"
        
        self.logger.debug(f"生成缓存键: {cache_key}, 参数: {params}")
        return cache_key
    
    def generate_lock_key(self, cache_key: str) -> str:
        """
        生成分布式锁键
        
        Args:
            cache_key: 缓存键
            
        Returns:
            锁键字符串
        """
        lock_key = f"lock:{cache_key}"
        return lock_key
    
    def acquire_distributed_lock(self, lock_key: str) -> bool:
        """
        获取分布式锁（Redis SETNX 实现）
        
        Args:
            lock_key: 锁键
            
        Returns:
            是否成功获取锁
        """
        # 使用父类的私有方法获取锁
        return self._acquire_lock(lock_key)
    
    def release_distributed_lock(self, lock_key: str) -> bool:
        """
        释放分布式锁
        
        Args:
            lock_key: 锁键
            
        Returns:
            是否成功释放锁
        """
        # 使用父类的私有方法释放锁
        return self._release_lock(lock_key)

    def query_db_cache(self, table_name: str, cache_key: str, ttl_days: int = 1) -> Optional[Dict[str, Any]]:
        """
        查询数据库缓存
        """
        try:
            if not table_name:
                self.logger.warning(f"表名不能为空: {cache_key}")
                return None
            conn = get_conn()
            with conn.cursor() as cursor:
                ttl_date = datetime.now() - timedelta(days=ttl_days)
                query = f"""
                    SELECT * FROM `{table_name}` 
                    WHERE cache_key = %s AND update_time >= %s
                    ORDER BY update_time DESC
                    LIMIT 1
                """

                cursor.execute(query, (cache_key, ttl_date))
                result = cursor.fetchone()

                if result:
                    self.logger.debug(f"数据库缓存命中: {cache_key} 表={table_name}")
                    return dict(result)
                else:
                    self.logger.debug(f"数据库缓存未命中或已过期: {cache_key}")
                    return None

        except Exception as e:
            self.logger.error(f"查询数据库缓存异常: {cache_key}, 错误: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def write_db_async(self, table_name: str, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> bool:
        """
        异步写入数据库
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键字段列表
            
        Returns:
            是否成功提交异步写入任务
        """
        try:
            success = submit_async_upsert(
                table_name=table_name,
                data_list=data_list,
                unique_keys=unique_keys or ["symbol"]
            )
            
            if success:
                self.logger.debug(f"成功提交异步写入任务: {table_name}, 数据条数: {len(data_list)}")
            else:
                self.logger.warning(f"提交异步写入任务失败: {table_name}")
            
            return success
        except Exception as e:
            self.logger.error(f"提交异步写入任务时发生异常: {table_name}, 错误: {e}")
            return False
    
    def write_db_sync(self, table_name: str, data_list: List[Dict[str, Any]], unique_keys: List[str] = None) -> bool:
        """
        同步写入数据库
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键字段列表
            
        Returns:
            是否成功写入
        """
        try:
            result = simple_upsert(
                table_name=table_name,
                data_list=data_list,
                unique_keys=unique_keys or ["symbol"]
            )
            
            success = result.get("success", False)
            
            if success:
                self.logger.debug(f"成功同步写入数据库: {table_name}, 数据条数: {len(data_list)}")
            else:
                self.logger.warning(f"同步写入数据库失败: {table_name}, 错误: {result.get('message', '未知错误')}")
            
            return success
        except Exception as e:
            self.logger.error(f"同步写入数据库时发生异常: {table_name}, 错误: {e}")
            return False

    def _validate_stock_symbol(self, field: str, val: Any) -> None:
        """股票代码专用验证：必须 6 位数字"""
        if not val:
            raise ValidationException(message=f"{field} 不能为空", details={field: val})
        if not (isinstance(val, str) and len(val) == 6 and val.isdigit()):
            raise ValidationException(message=f"{field} 必须是 6 位数字股票代码", details={field: val})

    def _validate_enum(self, field: str, value: Any, val: List) -> None:
        """
        枚举值验证
        
        注意：此方法采用旧式错误处理（返回 error_result 而非 raise），
        调用方需自行检查返回值，不会触发全局异常处理器。
        如需抛出异常，请直接 raise ValidationException。
        """
        if not value:
            return error_result(message=f"{field} 不能为空", data={field: value})
        if value not in val:
            valid_str = ", ".join(sorted(val))
            return error_result(
                message=f"{field} 必须为：{valid_str}",
                data={field: value, "valid_values": val}
            )


    def validate(self, val, field: str, rule: Any)-> Dict[str, Any]:
        """
        🔥 统一验证入口（万能简化版）
        :param val: 参数
        :param field: 参数字段名
        :param rule: 规则
            - 传列表 = 枚举验证
            - 传 ["stock"] = 股票代码 6 位验证
            - 传函数 = 自定义验证
        """
        # 1. 股票代码验证
        if rule == "stock":
            self._validate_stock_symbol(field, val)
        # 2. 枚举列表验证
        elif isinstance(rule, list):
            self._validate_enum(field, val, rule)
        # 3. 自定义函数验证（可扩展）
        elif callable(rule):
            rule(val)
        return success_result()


    def execute_cached_fetch(
        self,
        table_name: str,
        params: Dict[str, Any],
        fetch_func: Callable[..., Dict[str, Any]],
        validate_rules: Optional[Dict[str, Any]] = None,
        async_write: bool = True,
        cache_empty: bool = False,
        ttl_redis: Optional[int] = None,
        ttl_db: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        完整流程：
        1. 参数校验（可选）
        2. 生成缓存键与锁键
        3. 查Redis缓存（一级）
        4. 查数据库缓存（二级）
        5. 获取分布式锁
        6. Double-check
        7. 调用数据源
        8. 处理空数据
        9. 写入数据库（异步/同步）
        10. 更新Redis缓存
        11. 释放分布式锁（finally 块保证一定执行）
        12. 返回结果
        
        Args:
            table_name: 目标数据表名，同时作为缓存前缀
            params: 参数字典
            fetch_func: 数据获取函数，必须返回 {success, data, message} 格式
            validate_rules: 参数验证规则字典（可选），key 为字段名，value 为规则
                - "stock": 6位数字股票代码验证
                - list: 枚举值验证
                - callable: 自定义验证函数
            async_write: 是否异步写入数据库，默认True
            cache_empty: 是否缓存空数据，默认False
            ttl_redis: Redis缓存TTL（秒），默认使用服务配置
            ttl_db: 数据库缓存TTL（天），默认使用服务配置
            
        Returns:
            统一格式的响应数据：{success, data, message}
        """
        if validate_rules and isinstance(validate_rules, dict):
            for field, rule in validate_rules.items():
                val = params.get(field)
                res = self.validate(val, field, rule)
                if not res.get("success"):
                    raise ValidationException(message="请求参数错误", details=params)

        # 步骤2: 生成缓存键与锁键
        cache_key = self.generate_cache_key(table_name, params)
        lock_key = self.generate_lock_key(cache_key)
        # 步骤3: 查Redis缓存（一级）
        try:
            cached_data = self._cache_get(cache_key)
            if cached_data is not None:
                try:
                    data = json.loads(cached_data)
                    self.logger.info(f"Redis缓存命中: {cache_key}")
                    return success_result(
                        message="数据获取成功（来自Redis缓存）",
                        data=data
                    )
                except json.JSONDecodeError:
                    self.logger.warning(f"Redis缓存数据JSON格式错误: {cache_key}")
        except Exception as e:
            self.logger.warning(f"查询Redis缓存时发生异常: {cache_key}, 错误: {e}")
        
        # 步骤4: 查数据库缓存（二级）
        db_cache_ttl = ttl_db or self.db_cache_ttl_days
        db_cached_data = self.query_db_cache(table_name, cache_key, db_cache_ttl)
        if db_cached_data:
            # 回填Redis缓存
            try:
                self._cache_set(cache_key, json.dumps(db_cached_data, ensure_ascii=False, default=str))
                self._cache_expire(cache_key, ttl_redis or self.redis_ttl_medium)
                self.logger.info(f"数据库缓存命中并回填Redis: {cache_key}")
            except Exception as e:
                self.logger.warning(f"回填Redis缓存时发生异常: {cache_key}, 错误: {e}")
            
            return success_result(
                message="数据获取成功（来自数据库缓存）",
                data=db_cached_data
            )
        
        # 步骤5: 获取分布式锁
        lock_acquired = False
        try:
            lock_acquired = self.acquire_distributed_lock(lock_key)
            if not lock_acquired:
                return error_result(
                    message="系统繁忙，请稍后重试",
                    data={"cache_key": cache_key, "lock_key": lock_key}
                )
            
            # 步骤6: Double-check（再次查询数据库缓存）
            db_cached_data = self.query_db_cache(table_name, cache_key, db_cache_ttl)
            if db_cached_data:
                # 回填Redis缓存
                try:
                    self._cache_set(cache_key, json.dumps(db_cached_data, ensure_ascii=False))
                    self._cache_expire(cache_key, ttl_redis or self.redis_ttl_medium)
                except Exception as e:
                    self.logger.warning(f"Double-check回填Redis缓存时发生异常: {cache_key}, 错误: {e}")
                
                return success_result(
                    message="数据获取成功（来自数据库缓存，Double-check）",
                    data=db_cached_data
                )
            # 步骤7: 调用数据源
            fetch_result = fetch_func(params)
            # 检查数据获取结果
            if not fetch_result.get("success", False):
                return fetch_result
            
            data = fetch_result.get("data")

            if isinstance(data, list):
                for item in data:
                    item["cache_key"] = cache_key


            # 步骤8: 处理空数据
            if not data:
                if cache_empty:
                    # 缓存空数据标记
                    try:
                        self._cache_set(cache_key, json.dumps({"empty": True}, ensure_ascii=False))
                        self._cache_expire(cache_key, self.redis_ttl_empty)
                        self.logger.info(f"缓存空数据标记: {cache_key}")
                    except Exception as e:
                        self.logger.warning(f"缓存空数据标记时发生异常: {cache_key}, 错误: {e}")
                else:
                    self.logger.info(f"数据为空，不写入缓存: {cache_key}")
                
                return success_result(
                    message="查询成功，但数据为空",
                    data=data or []
                )
            
            # 步骤9: 写入数据库（异步/同步）
            if async_write:
                # 异步写入
                write_success = self.write_db_async(
                    table_name=table_name,
                    data_list=[data] if isinstance(data, dict) else data,
                    unique_keys=["symbol"]
                )
                
                if not write_success:
                    self.logger.warning(f"异步写入任务提交失败，但数据已获取: {cache_key}")
            else:
                # 同步写入
                # 注意：此处 table_name 硬编码为 "stocks_info"，只适用于股票信息场景
                write_success = self.write_db_sync(
                    table_name="stocks_info",
                    data_list=[data] if isinstance(data, dict) else data,
                    unique_keys=["symbol"]
                )
                
                if not write_success:
                    self.logger.error(f"同步写入数据库失败: {cache_key}")
                    # 即使写入失败，也返回获取到的数据
                    # 但记录错误日志
            
            # 步骤10: 更新Redis缓存
            try:
                self._cache_set(cache_key, json.dumps(data, ensure_ascii=False))
                self._cache_expire(cache_key, ttl_redis or self.redis_ttl_long)
                self.logger.info(f"更新Redis缓存: {cache_key}")
            except Exception as e:
                self.logger.warning(f"更新Redis缓存时发生异常: {cache_key}, 错误: {e}")
            
            # 步骤11: 返回结果（步骤11 释放分布式锁在 finally 块中执行）
            return success_result(
                message="数据获取成功",
                data=data
            )
            
        finally:
            # 步骤11（补充）: 释放分布式锁（确保在finally中释放，无论是否发生异常）
            if lock_acquired:
                self.release_distributed_lock(lock_key)
    
    def get_redis_cache(self, cache_key: str) -> Optional[Any]:
        """
        获取Redis缓存（快捷方法）
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存数据，如果未命中则返回None
        """
        # 使用父类的私有方法获取JSON缓存
        return self._json_get(cache_key)
    
    def set_redis_cache(self, cache_key: str, data: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        设置Redis缓存（快捷方法）
        
        Args:
            cache_key: 缓存键
            data: 要缓存的数据
            ttl_seconds: 缓存时间（秒），默认使用服务配置
            
        Returns:
            是否成功设置缓存
        """
        # 使用父类的私有方法设置JSON缓存
        return self._json_set(cache_key, data, ttl_seconds or self.redis_ttl_long)
    
    def clear_redis_cache(self, cache_key: str) -> bool:
        """
        清除Redis缓存（快捷方法）
        
        Args:
            cache_key: 缓存键
            
        Returns:
            是否成功清除缓存
        """
        try:
            r = self._get_client()
            if r:
                result = r.delete(cache_key)
                success = result > 0
                if success:
                    self.logger.debug(f"成功清除Redis缓存: {cache_key}")
                return success
            return False
        except Exception as e:
            self.logger.error(f"清除Redis缓存时发生异常: {cache_key}, 错误: {e}")
            return False


class ConcurrentTaskService(BaseStockService):
    """
    通用并发任务服务类
    
    提供多线程并发执行任务的通用功能，包括：
    1. 并发执行多个独立任务
    2. 自动合并任务结果
    3. 统一错误处理
    4. 统计信息生成
    
    设计原则：
    - 继承自 BaseStockService，复用基础功能
    - 统一返回格式：{success: bool, data: any, message: str}
    - 内部捕获异常，记录日志，不向外抛出异常
    """
    
    def __init__(self):
        """初始化并发任务服务"""
        super().__init__(service_name="ConcurrentTaskService")
        
        # 服务特定配置
        self.default_max_workers = 5  # 默认最大并发线程数
        self.default_timeout = 60     # 默认整体超时时间（秒）
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        from system_service.service_result import success_result
        
        return success_result(
            message="并发任务服务信息",
            data={
                "service_name": self.service_name,
                "description": "通用并发任务执行服务，提供多线程并发执行任务的通用功能",
                "features": [
                    "多线程并发执行",
                    "自动结果合并",
                    "统一错误处理",
                    "统计信息生成"
                ],
                "config": {
                    "default_max_workers": self.default_max_workers,
                    "default_timeout": self.default_timeout
                }
            }
        )
    
    def execute_concurrent_tasks(self, base_func: Callable, param_list: List[Dict[str, Any]], 
                                max_workers: int = None, timeout: int = None) -> Dict[str, Any]:
        """
        通用多线程并发调用函数
        
        功能：接收一个基础函数和一组参数列表，利用线程池并发执行多个任务，
              合并所有任务的返回结果，处理异常，单个任务失败不影响其他任务。
        
        Args:
            base_func: 基础函数（如获取上交所股票数据的函数）
            param_list: 参数列表，每个元素为字典，包含：
                        - args: 位置参数元组（可选）
                        - kwargs: 关键字参数字典（可选）
                        - name: 任务名称（可选，默认使用函数名+索引）
            max_workers: 最大并发线程数，默认使用类默认值
            timeout: 整体超时时间（秒），默认使用类默认值
        
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 整体调用是否成功（至少有一个任务成功）
                "data": {
                    "all_results": list,     # 所有任务的原始结果
                    "success_results": list, # 成功的任务数据
                    "failed_results": list,  # 失败的任务信息
                    "merged_data": any       # 合并后的数据（根据任务类型）
                },
                "message": str        # 成功或错误信息（包含统计信息）
            }
        """
        from system_service.service_result import error_result, success_result
        from system_service.thread_pool import run_concurrent_tasks
        
        # 验证参数
        if not callable(base_func):
            self.logger.error("基础函数必须是可调用对象")
            return error_result(
                message="基础函数必须是可调用对象",
                data={"base_func": str(base_func)}
            )
        
        if not param_list or not isinstance(param_list, list):
            self.logger.error("参数列表不能为空且必须是列表")
            return error_result(
                message="参数列表不能为空且必须是列表",
                data={"param_list": param_list}
            )
        
        # 使用默认值或传入值
        max_workers = max_workers or self.default_max_workers
        timeout = timeout or self.default_timeout
        
        self.logger.info(f"开始执行并发任务，函数: {base_func.__name__}，任务数: {len(param_list)}")
        
        try:
            # 构建任务列表，符合 thread_pool.run_concurrent_tasks 要求的格式
            tasks = []
            for i, params in enumerate(param_list):
                # 提取参数
                args = params.get("args", ())
                kwargs = params.get("kwargs", {})
                task_name = params.get("name", f"{base_func.__name__}_{i}")
                
                # 验证参数类型
                if not isinstance(args, tuple):
                    self.logger.warning(f"任务 {task_name} 的 args 不是元组，已自动转换")
                    args = (args,) if args is not None else ()
                
                if kwargs is not None and not isinstance(kwargs, dict):
                    self.logger.warning(f"任务 {task_name} 的 kwargs 不是字典，已忽略")
                    kwargs = {}
                
                # 添加到任务列表
                tasks.append({
                    "func": base_func,
                    "args": args,
                    "kwargs": kwargs,
                    "name": task_name
                })
            
            # 调用线程池执行并发任务
            thread_results = run_concurrent_tasks(
                tasks=tasks,
                max_workers=max_workers,
                timeout=timeout
            )
            
            # 处理结果：分离成功和失败的任务
            success_results = []
            failed_results = []
            all_results = []
            
            for result in thread_results:
                all_results.append(result)
                
                if result["success"]:
                    success_results.append({
                        "name": result["name"],
                        "data": result["result"]
                    })
                else:
                    failed_results.append({
                        "name": result["name"],
                        "error": result["error"]
                    })
            
            # 合并成功任务的数据
            merged_data = self._merge_concurrent_results(success_results)
            
            # 构建统计信息
            total_tasks = len(param_list)
            success_count = len(success_results)
            fail_count = len(failed_results)
            
            # 整体成功判断：至少有一个任务成功
            overall_success = success_count > 0
            
            if overall_success:
                message = f"并发任务执行完成，成功 {success_count} 个，失败 {fail_count} 个"
                self.logger.info(message)
            else:
                message = f"并发任务执行失败，所有 {total_tasks} 个任务均失败"
                self.logger.warning(message)
            
            return success_result(
                message=message,
                data={
                    "all_results": all_results,
                    "success_results": success_results,
                    "failed_results": failed_results,
                    "merged_data": merged_data,
                    "statistics": {
                        "total_tasks": total_tasks,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "success_rate": success_count / total_tasks if total_tasks > 0 else 0
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"执行并发任务异常: {e}")
            return error_result(
                message=f"执行并发任务异常: {str(e)}",
                data={
                    "base_func": base_func.__name__,
                    "param_list_count": len(param_list) if param_list else 0
                }
            )
    
    def _merge_concurrent_results(self, success_results: List[Dict[str, Any]]) -> Any:
        """
        合并并发任务的结果
        
        根据任务返回的数据类型自动选择合适的合并策略：
        1. 如果所有结果都是列表，则合并为一个列表
        2. 如果所有结果都是字典，则合并为一个字典（可能覆盖相同键）
        3. 其他情况，返回原始结果列表
        
        Args:
            success_results: 成功任务的结果列表，每个元素为 {"name": str, "data": any}
        
        Returns:
            合并后的数据
        """
        if not success_results:
            return []
        
        # 提取所有数据
        all_data = [result["data"] for result in success_results]
        
        # 检查数据类型
        if all(isinstance(data, list) for data in all_data):
            # 所有结果都是列表，合并为一个列表
            merged = []
            for data in all_data:
                merged.extend(data)
            return merged
        
        elif all(isinstance(data, dict) for data in all_data):
            # 所有结果都是字典，合并为一个字典
            merged = {}
            for data in all_data:
                merged.update(data)
            return merged
        
        else:
            # 数据类型不一致，返回原始结果列表
            return all_data

# 导出
__all__ = [
    "BaseStockService",
    "ConcurrentTaskService",
]