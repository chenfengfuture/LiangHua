#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基础数据服务模块 - 类服务版本

主要功能：
1. StockBasicService 类 - 提供股票基础数据服务，继承自 BaseStockService
2. 东方财富个股信息查询（get_stock_info_em）
3. 沪深北三大交易所股票列表查询（get_sh/sz/bj_stock_list）
4. 沪深两大交易所退市/暂停上市股票查询（get_stock_sh/sz_delist）
5. 支持缓存、错误处理、日志等基础功能

设计原则：
- 继承自 BaseStockService，复用基础功能
- 统一返回格式：{success: bool, data: any, message: str}
- 内部捕获异常，记录日志，不向外抛出异常
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
import akshare as ak
# 导入基类
from stock_services.services.basic_services import BaseStockService, ConcurrentTaskService
from stock_services.utils.validate_params import default_validator
from system_service.service_result import error_result, success_result, wrap_service_result
from stock_services.unity.utils import request_akshare_data
# 导入线程池模块
from system_service.thread_pool import run_concurrent_tasks
# 导入底层unity接口
from stock_services.unity.basic import *
class StockBasicService(BaseStockService):
    """
    股票基础数据服务类
    
    提供股票基础数据查询服务，包括：
    1. 个股公司概况查询
    2. 基础信息查询
    3. 其他基础数据服务
    """
    
    def __init__(self):
        """初始化股票基础数据服务"""
        super().__init__(service_name="StockBasicService")
        
        # 服务特定配置
        self.cache_prefix = "stock_basic"  # 缓存前缀
        self.default_cache_ttl = self.redis_ttl_long  # 默认缓存时间24小时
        self.default_validator = default_validator
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return (success_result
        (
            message="股票基础数据服务信息",
            data={
                "service_name": self.service_name,
                "description": "股票基础数据查询服务，提供个股公司概况等基础信息",
                "features": [
                    "个股公司概况查询",
                    "雪球财经数据接口",
                    "缓存支持",
                    "错误自动处理"
                ],
                "config": {
                    "cache_prefix": self.cache_prefix,
                    "default_cache_ttl": self.default_cache_ttl,
                    "redis_ttl_more_long": self.redis_ttl_more_long,
                    "redis_ttl_long": self.redis_ttl_long
                }
            }
        ))
    
    def get_stock_info_em(self, symbol: str) -> Dict[str, Any]:
        """
        东方财富-个股-股票信息
        
        Args:
            symbol: 股票代码（纯数字，不带市场前缀），如 "000001"、"603777"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": any,          # 业务数据（成功时为字典，失败时为None）
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': symbol},
            fetch_func=get_stock_info_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_long,
            ttl_db=90
        )

    def batch_get_stock_individual(self, symbols: list) -> Dict[str, Any]:
        """
        批量查询个股数据
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            统一格式的响应数据，包含所有查询结果
        """
        if not symbols or not isinstance(symbols, list):
            return error_result(
                message="股票代码列表不能为空且必须是列表",
                data={"symbols": symbols}
            )
        
        results = {}
        errors = []
        
        for symbol in symbols:
            result = self.get_stock_individual(symbol)
            if result["success"]:
                results[symbol] = result["data"]
            else:
                errors.append({
                    "symbol": symbol,
                    "error": result["message"]
                })
        
        return (success_result
        (
            message=f"批量查询完成，成功 {len(results)} 个，失败 {len(errors)} 个",
            data={
                "success_results": results,
                "errors": errors
            }
        ))
    
    def get_sh_stock_list(self, symbol: str = "主板A股") -> Dict[str, Any]:
        """
        查询上海证券交易所股票列表

        Args:
            symbol: 股票板块类型，可选值：
                - "主板A股": 主板A股
                - "主板B股": 主板B股  
                - "科创板": 科创板
                默认: "主板A股"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票列表数据，已映射到stocks_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': symbol, 'akshare': 'sh_stocks'},
            fetch_func=stock_info_sh_name_code,
            validate_rules={
                "symbol": ["主板A股", "主板B股", "科创板"],
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存90天
        )

    def get_sz_stock_list(self, symbol: str = "A股列表") -> Dict[str, Any]:
        """
        查询深圳证券交易所股票列表
        Args:
            symbol: 股票列表类型，可选值：
                - "A股列表": A股列表
                - "B股列表": B股列表
                - "AB股列表": AB股列表
                - "CDR列表": CDR列表
                默认: "A股列表"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票列表数据，已映射到stocks_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': symbol, 'akshare': 'sz_stocks'},
            fetch_func=stock_info_sz_name_code,
            validate_rules={
                "symbol": ["A股列表", "B股列表", "AB股列表", "CDR列表"],
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存90天
        )

    def get_bj_stock_list(self) -> Dict[str, Any]:
        """
        查询北京证券交易所股票列表
        Args:
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票列表数据，已映射到stocks_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': None, 'akshare': 'bj_stocks'},
            fetch_func=stock_info_bj_name_code,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存
        )

    def get_stock_sz_delist(self, symbol: str = "股票状态类型") -> Dict[str, Any]:
        """
        深圳证券交易所终止/暂停上市股票
        Args:
            symbol: 深交所退市股票状态类型，可选值：
                - "终止上市公司": 终止上市公司
                - "暂停上市公司": 暂停上市公司
                默认: "终止上市公司"
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票列表数据，已映射到stocks_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': symbol, 'akshare': 'sz_stocks_delist'},
            fetch_func=stock_info_sz_delist,
            validate_rules={
                "symbol": ["终止上市公司", "暂停上市公司"],
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存90天
        )

    def get_stock_sh_delist(self, symbol: str = "股票状态类型") -> Dict[str, Any]:
        """
        上海证券交易所暂停/终止上市股票
        Args:
            symbol: 上交所退市股票市场范围，可选值：
                - "全部": 全部市场
                - "沪市": 沪市主板
                - "科创板": 科创板
                默认: "全部"
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票列表数据，已映射到stocks_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stocks_info",
            params={'symbol': symbol, 'akshare': 'sh_stocks_delist'},
            fetch_func=stock_info_sh_delist,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存90天
        )


# 全局服务实例
stock_basic_service = StockBasicService()

# 导出 
__all__ = [
    "StockBasicService",
    "stock_basic_service",
]


