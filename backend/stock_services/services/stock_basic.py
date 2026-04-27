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
# 导入板块数据接口
from stock_services.unity.board import (
    get_stock_board_concept_index_ths,
    get_stock_board_industry_summary_ths,
    get_stock_board_concept_info_ths,
    get_stock_hot_follow_xq,
    get_stock_board_change_em,
    get_stock_board_industry_index_ths,
    get_stock_hot_rank_detail_em,
    get_stock_hot_keyword_em,
    get_stock_changes_em
)

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

    def get_stock_board_concept_index_ths_service(self, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块指数日频率数据
        
        Args:
            symbol: 概念板块名称，如 "阿里巴巴概念"
            start_date: 开始日期，格式为 "YYYYMMDD"
            end_date: 结束日期，格式为 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 概念板块指数数据，已映射到board_concept_index表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_concept_index",
            params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date},
            fetch_func=get_stock_board_concept_index_ths,
            validate_rules={
                "symbol": "no_empty",
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_long,
            ttl_db=30  # 指数数据缓存30天
        )

    def get_stock_board_industry_summary_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺行业一览表
        
        Args:
            无参数
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 行业一览表数据，已映射到board_industry_summary表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_industry_index",
            params={},  # 无参数
            fetch_func=get_stock_board_industry_summary_ths,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 行业列表数据缓存90天
        )

    def get_stock_board_concept_info_ths_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块简介
        
        Args:
            symbol: 概念板块名称，如 "阿里巴巴概念"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 概念板块简介数据，已映射到board_concept_info表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_concept_info",
            params={'symbol': symbol},
            fetch_func=lambda params: get_stock_board_concept_info_ths(params),
            validate_rules={
                "symbol": "required"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_long,
            ttl_db=90  # 概念信息缓存90天
        )

    def get_stock_board_industry_index_ths_service(self, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询同花顺行业板块指数日频率数据
        
        Args:
            symbol: 行业板块名称，如 "元件"
            start_date: 开始日期，格式为 "YYYYMMDD"
            end_date: 结束日期，格式为 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 行业板块指数数据，已映射到board_industry_index表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_industry_index",
            params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date},
            fetch_func=lambda params: get_stock_board_industry_index_ths(params),
            validate_rules={
                "symbol": "required",
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_long,
            ttl_db=30  # 指数数据缓存30天
        )

    def get_stock_hot_follow_xq_service(self, symbol: str = "最热门") -> Dict[str, Any]:
        """
        查询雪球关注排行榜
        
        Args:
            symbol: 选择类型，可选值: {"本周新增", "最热门"}，默认: "最热门"
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 关注排行榜数据，已映射到stock_hot_follow表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_hot_follow",
            params={'symbol': symbol},
            fetch_func=lambda params: get_stock_hot_follow_xq(params),
            validate_rules={
                "symbol": ["本周新增", "最热门"]
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_short,
            ttl_db=7  # 热门数据缓存7天
        )

    def get_stock_hot_rank_detail_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富股票热度历史趋势及粉丝特征
        
        Args:
            symbol: 股票代码，如 "SZ000665"（需带市场前缀）
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票热度详情数据，已映射到stock_hot_rank_detail表结构
                "message": str        # 成功或错误信息
            }
        """
        # 由于底层函数可能不完整，这里使用包装器确保返回正确格式
        def wrapped_fetch_func(params):
            result = get_stock_hot_rank_detail_em(params)
            # 如果底层函数返回的是字典格式，直接返回
            if isinstance(result, dict) and "success" in result:
                return result
            # 否则包装成统一格式
            from system_service.service_result import success_result
            return success_result(data=result if isinstance(result, list) else [])
        
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_hot_rank_detail",
            params={'symbol': symbol},
            fetch_func=wrapped_fetch_func,
            validate_rules={
                "symbol": "stock_with_prefix"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_short,
            ttl_db=7  # 热度数据缓存7天
        )

    def get_stock_hot_keyword_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富个股人气榜热门关键词
        
        Args:
            symbol: 股票代码，如 "SZ000665"（需带市场前缀）
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 热门关键词数据，已映射到stock_hot_keyword表结构
                "message": str        # 成功或错误信息
            }
        """
        # 由于底层函数可能不完整，这里使用包装器确保返回正确格式
        def wrapped_fetch_func(params):
            result = get_stock_hot_keyword_em(params)
            # 如果底层函数返回的是字典格式，直接返回
            if isinstance(result, dict) and "success" in result:
                return result
            # 否则包装成统一格式
            from system_service.service_result import success_result
            return success_result(data=result if isinstance(result, list) else [])
        
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_hot_keyword",
            params={'symbol': symbol},
            fetch_func=wrapped_fetch_func,
            validate_rules={
                "symbol": "stock_with_prefix"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_short,
            ttl_db=7  # 关键词数据缓存7天
        )

    def get_stock_changes_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富盘口异动数据
        
        Args:
            symbol: 异动类型，可选值: {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 盘口异动数据，已映射到stock_changes表结构
                "message": str        # 成功或错误信息
            }
        """
        # 由于底层函数可能不完整，这里使用包装器确保返回正确格式
        def wrapped_fetch_func(params):
            result = get_stock_changes_em(params)
            # 如果底层函数返回的是字典格式，直接返回
            if isinstance(result, dict) and "success" in result:
                return result
            # 否则包装成统一格式
            from system_service.service_result import success_result
            return success_result(data=result if isinstance(result, list) else [])
        
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_changes",
            params={'symbol': symbol},
            fetch_func=wrapped_fetch_func,
            validate_rules={
                "symbol": "required"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_short,
            ttl_db=1  # 异动数据缓存1天（实时性要求高）
        )

    def get_stock_board_change_em_service(self) -> Dict[str, Any]:
        """
        查询东方财富当日板块异动详情
        
        Args:
            无参数
            
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_change",
            params={},  # 无参数
            fetch_func=lambda params: get_stock_board_change_em(params),
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_short,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )


# 全局服务实例
stock_basic_service = StockBasicService()

# 导出 
__all__ = [
    "StockBasicService",
    "stock_basic_service",
]


