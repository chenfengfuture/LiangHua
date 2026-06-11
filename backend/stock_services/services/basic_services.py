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
import time
from typing import Any, Dict, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from system_service.exception_handler import ValidationException

import pandas_market_calendars as mcal

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

# 缓存 Key 统一构建
from stock_services.common.cache import CacheKeyBuilder
from stock_services.common.logging import get_module_logger

logger = get_module_logger("stock_services.basic_services")


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
    
    def generate_cache_key(self, table_name: str, params: Dict[str, Any], cache_key_type) -> str:
        """
        生成缓存键（委派至 common/cache.CacheKeyBuilder）。

        向后兼容包装，新代码请直接使用：
            from stock_services.common.cache import CacheKeyBuilder
            cache_key = CacheKeyBuilder.build("prefix", params=params)
        """
        return CacheKeyBuilder.build(table_name, simple=cache_key_type, params=params)


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

            # 根据 db_name 选择数据库连接
            if db_name == "news_data":
                from utils.db import get_news_conn
                conn = get_news_conn()
                qualified_table = f"`{table_name}`"
            elif db_name != "lianghua":
                # 非默认库，使用主连接池 + 限定表名 `db_name`.`table_name`
                conn = get_conn()
                qualified_table = f"`{db_name}`.`{table_name}`"
            else:
                conn = get_conn()
                qualified_table = f"`{table_name}`"

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

        db_name 仅用于选择连接池（"news_data" 使用独立连接池），
        表名限定由 DBService._resolve_table_qualified_name 自动发现，
        调用方无需关心表在哪个数据库。

        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键字段列表
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            是否成功提交异步写入任务
        """
        try:
            # 直接传纯表名，upsert_data_with_schema 内部自动发现所在数据库
            success = submit_async_upsert(
                table_name=table_name,
                data_list=data_list,
                unique_keys=unique_keys or ["symbol"]
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

        db_name 仅用于选择连接池（"news_data" 使用独立连接池），
        表名限定由 DBService._resolve_table_qualified_name 自动发现。

        Args:
            table_name: 表名
            data_list: 数据列表
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            是否成功写入
        """
        try:
            # 直接传纯表名，simple_upsert → upsert_data_with_schema 内部自动发现
            result = simple_upsert(
                table_name=table_name,
                data_list=data_list
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

    # ====================== 查库 =======================

    def _validate_not_empty(self, field: str, val: Any) -> None:
        """
        规则：必须是字符串 + 不能是空字符串 + 不能全是空格
        """
        # 1. 必须是字符串类型
        if not isinstance(val, str):
            raise ValidationException(message=f"{field} 必须是字符串类型", details={field: val})

        # 2. 不能是空/空白字符串
        if not val.strip():
            raise ValidationException(message=f"{field} 不能为空或空白字符", details={field: val})


    def _validate_date_yyyymmdd(self, field: str, val: Any) -> None:
        """
        自定义验证：日期必须是 8 位字符串，格式 YYYYMMDD
        例如：20250411
        """
        # 1. 必须是字符串
        if not isinstance(val, str):
            raise ValidationException(message=f"{field} 必须是字符串格式", details={field: val})

        # 2. 必须是 8 位
        if len(val) != 8:
            raise ValidationException(message=f"{field} 必须是 8 位数字，格式：YYYYMMDD", details={field: val})

        # 3. 必须全部是数字
        if not val.isdigit():
            raise ValidationException(message=f"{field} 必须是纯数字，格式：YYYYMMDD", details={field: val})

    def _validate_trading_day(self, field: str, val: Any) -> None:
        """验证日期格式为 YYYYMMDD 且为上海证券交易所交易日"""
        # 1. 复用格式验证（8位纯数字字符串）

        self._validate_date_yyyymmdd(field, val)
        # 2. 转换为 date 对象
        try:
            date_obj = datetime.strptime(val, '%Y%m%d').date()
        except Exception:
            raise ValidationException(
                message=f"{field} 日期转换失败，请输入有效的日期",
                details={field: val}
            )
        # 3. 交易日验证
        try:
            sse = mcal.get_calendar('SSE')
            schedule = sse.schedule(start_date=date_obj, end_date=date_obj)
            if schedule.empty:
                raise ValidationException(
                    message=f"{val} 不是交易日",
                    details={field: val}
                )
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(
                message=f"{field} 交易日验证失败: {e}",
                details={field: val}
            )

    def _validate_stock_symbol(self, field: str, val: Any) -> None:
        """股票代码专用验证：必须 6 位数字"""
        if not val:
            raise ValidationException(message=f"{field} 不能为空", details={field: val})
        if not (isinstance(val, str) and len(val) == 6 and val.isdigit()):
            raise ValidationException(message=f"{field} 必须是 6 位数字股票代码", details={field: val})


    def _validate_enum(self, field: str, value: Any, val: List) -> None:
        """
        枚举值验证

        验证失败时直接 raise ValidationException，由全局异常处理器统一捕获。
        """
        if not value:
            raise ValidationException(message=f"{field} 不能为空", details={field: value})
        if value not in val:
            valid_str = ", ".join(sorted(val))
            raise ValidationException(
                message=f"{field} 必须为：{valid_str}",
                details={field: value, "valid_values": val}
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
        elif rule == "no_empty":
            self._validate_not_empty(field, val)
        elif rule == "date":
            self._validate_trading_day(field, val)
        elif rule == "date_format":
            self._validate_date_yyyymmdd(field, val)
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
        ttl_db: Optional[int] = None,
        write_to_db: bool = True,
        read_from_db: bool = True,
        cache_key_exclude_fields: Optional[List[str]] = None,
        dedup_keys: Optional[List[str]] = None,
        cache_key_type: bool = False,
        db_name: str = "lianghua",
    ) -> Dict[str, Any]:
        """
        模板方法：缓存优先 → 分布式锁 → 获取数据 → 异步持久化。

        流程：校验 → 缓存键 → Redis → DB缓存 → 锁 → Double-check → fetch_func → 写入DB/Redis → 释放锁。

        Args:
            table_name: 表名（也用作缓存前缀）
            params: 请求参数字典
            fetch_func: 数据获取函数，需返回 {"success": bool, "data": any, "message": str}
            validate_rules: 参数字段校验规则，如 {"symbol": "stock"} 或 {"status": [0,1]}
            async_write: 是否异步写入数据库
            cache_empty: 空数据是否缓存
            ttl_redis: Redis缓存秒数，默认使用服务配置
            ttl_db: 数据库缓存天数，默认使用服务配置
            write_to_db: 是否写入数据库持久化
            read_from_db: 是否查询数据库二级缓存（独立于 write_to_db 控制）
            cache_key_exclude_fields: 生成缓存键时排除的参数字段（如日期范围）
            dedup_keys: 写入前去重字段列表
            cache_key_type: 缓存键写入方式 , MD5 / 直接键值对
            db_name: 数据库名称，默认 "lianghua"

        Returns:
            {"success": bool, "data": any, "message": str}
        """

        if validate_rules and isinstance(validate_rules, dict):
            for field, rule in validate_rules.items():
                val = params.get(field)
                res = self.validate(val, field, rule)
                if not res.get("success"):
                    raise ValidationException(message="请求参数错误", details=params)

        # 步骤2: 生成缓存键与锁键
        # 排除指定字段（如日期参数），使不同日期范围共享同一缓存键避免冗余
        effective_params = params.copy()
        if cache_key_exclude_fields:
            for f in cache_key_exclude_fields:
                effective_params.pop(f, None)

        cache_key = self.set_client_key(table_name, params=effective_params, simple=cache_key_type)
        lock_key = f"lock:{cache_key}"

        # 步骤3: 查Redis缓存（一级）
        try:
            cached_data = self._cache_get(cache_key)
            if cached_data is not None:
                try:
                    data = json.loads(cached_data)
                    # 识别空缓存标记 {"empty": True}，返回空列表而非字典
                    if isinstance(data, dict) and data.get("empty") is True:
                        self.logger.info(f"Redis缓存命中(空缓存标记): {cache_key}")
                        return success_result(
                            message="数据获取成功（来自Redis缓存）",
                            data=[]
                        )
                    self.logger.info(f"Redis缓存命中: {cache_key}")
                    return success_result(
                        message="数据获取成功（来自Redis缓存）",
                        data=data
                    )
                except json.JSONDecodeError:
                    self.logger.warning(f"Redis缓存数据JSON格式错误: {cache_key}")
        except Exception as e:
            self.logger.warning(f"查询Redis缓存时发生异常: {cache_key}, 错误: {e}")


        # 步骤4: 查数据库缓存（二级，由 read_from_db 独立控制）
        db_cache_ttl = ttl_db or self.db_cache_ttl_days
        if read_from_db:
            db_cached_data = self.query_db_cache(table_name, cache_key, db_cache_ttl, db_name=db_name)
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
            
            # 步骤6: Double-check（再次查询数据库缓存，由 read_from_db 独立控制）
            if read_from_db:
                db_cached_data = self.query_db_cache(table_name, cache_key, db_cache_ttl, db_name=db_name)
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
            success_message = fetch_result.get('message', '成功')
            if isinstance(data, list):
                for item in data:
                    item["cache_key"] = cache_key

                # 按指定字段去重（如 (symbol, trade_date)），确保 Redis 和 DB 数据一致
                if dedup_keys:
                    seen = set()
                    deduped = []
                    for item in data:
                        key = tuple(item.get(k) for k in dedup_keys)
                        if key not in seen:
                            seen.add(key)
                            deduped.append(item)
                    removed = len(data) - len(deduped)
                    if removed:
                        self.logger.info(f"数据去重: {table_name} 移除 {removed} 条重复行, 去重字段={dedup_keys}")
                    data = deduped


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
            if write_to_db:
                # 步骤9: 写入数据库（异步/同步）
                if async_write:
                    # 异步写入
                    write_success = self.write_db_async(
                        table_name=table_name,
                        data_list=[data] if isinstance(data, dict) else data,
                        unique_keys=dedup_keys or ["symbol"],
                        db_name=db_name
                    )

                    if not write_success:
                        self.logger.warning(f"异步写入任务提交失败，但数据已获取: {cache_key}, 库={db_name}")
                else:
                    # 同步写入
                    # 注意：此处 table_name 硬编码为 "stocks_info"，只适用于股票信息场景
                    write_success = self.write_db_sync(
                        table_name=table_name,
                        data_list=[data] if isinstance(data, dict) else data,
                        db_name=db_name
                    )

                    if not write_success:
                        self.logger.error(f"同步写入数据库失败: {cache_key}, 库={db_name}")


            # 步骤10: 更新Redis缓存（独立于 write_to_db 始终执行，即使不落库也要缓存）
            try:
                self._cache_set(cache_key, json.dumps(data, ensure_ascii=False))
                self._cache_expire(cache_key, ttl_redis or self.redis_ttl_long)
                self.logger.info(f"更新Redis缓存: {cache_key}")
            except Exception as e:
                self.logger.warning(f"更新Redis缓存时发生异常: {cache_key}, 错误: {e}")
            
            # 步骤11: 返回结果（步骤11 释放分布式锁在 finally 块中执行）
            return success_result(
                message=success_message,
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