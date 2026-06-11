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

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Callable, Tuple
# 导入基类
from stock_services.services.basic_services import BaseStockService, ConcurrentTaskService
# 导入基础服务接口
from stock_services.unity import *
from stock_services.utils.field_mapper import normalize_symbol
from stock_services.common.validation import StockValidator, default_validator
from system_service.service_result import error_result, success_result
# 导入线程池模块
from system_service.thread_pool import run_concurrent_tasks


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
        self.date_str = date.today().strftime('%Y%m%d')
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
            params={'symbol': symbol, 'key_type': 'em'},
            fetch_func=get_stock_info_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_long,
            ttl_db=90
        )

    def get_stock_info_xq(self, symbol: str) -> Dict[str, Any]:
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
            params={'symbol': symbol, 'key_type': 'xq'},
            fetch_func=get_stock_individual_basic_info_xq,
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

    def get_all_stock_list(self) -> Dict[str, Any]:
        """
        查询全市场A股股票代码列表

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
            params={'akshare': 'sh_stocks', 'key_type': 'all'},
            fetch_func=get_all_stocks,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 列表数据缓存90天
        )

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
            params={'symbol': symbol, 'key_type': 'sh'},
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
            params={'symbol': symbol, 'key_type': 'sz'},
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
            params={'symbol': None, 'key_type': 'bj'},
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
            params={'symbol': symbol, 'key_type': 'sz_delist'},
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
            params={'symbol': symbol, 'key_type': 'sh_delist'},
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
            params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date, 'key_type': 'board_concept_index_ths'},
            fetch_func=get_stock_board_concept_index_ths,
            validate_rules={
                "symbol": "no_empty",
                "start_date": "date_format",
                "end_date": "date_format"
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
            table_name="board_industry_summary",
            params={'key_type': 'board_industry_summary_ths'},  # 无参数
            fetch_func=get_stock_board_industry_summary_ths,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.redis_ttl_more_long,
            ttl_db=90  # 行业列表数据缓存90天
        )

    def get_stock_board_concept_info_ths_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块简介  废弃
        
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
            params={'symbol': symbol, 'key_type': 'board_concept_info_ths'},
            fetch_func=lambda params: get_stock_board_concept_info_ths(params),
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
            params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date, 'key_type': 'board_industry_index_ths'},
            fetch_func=lambda params: get_stock_board_industry_index_ths(params),
            validate_rules={
                "symbol": "required",
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
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
            params={'symbol': symbol, 'key_type': 'hot_follow_xq'},
            fetch_func=lambda params: get_stock_hot_follow_xq(params),
            validate_rules={
                "symbol": ["本周新增", "最热门"]
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7  # 热门数据缓存7天
        )

    def get_stock_hot_tweet_xq_service(self, symbol: str = "最热门") -> Dict[str, Any]:
        """
        查询雪球 沪深股市 热度排行榜-讨论排行榜

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
            params={'symbol': symbol, 'key_type': 'hot_tweet_xq'},
            fetch_func=get_stock_hot_tweet_xq,
            validate_rules={
                "symbol": ["本周新增", "最热门"]
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7  # 热门数据缓存7天
        )

    def get_stock_hot_tweet_deal_service(self, symbol: str = "最热门") -> Dict[str, Any]:
        """
        查询雪球 沪深股市 热度排行榜-讨论排行榜

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
            params={'symbol': symbol, 'key_type': 'hot_tweet_deal'},
            fetch_func=get_stock_hot_deal_xq,
            validate_rules={
                "symbol": ["本周新增", "最热门"]
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7  # 热门数据缓存7天
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

        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_hot_keyword",
            params={'symbol': symbol, 'key_type': 'hot_keyword_em'},
            fetch_func=get_stock_hot_keyword_em,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
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
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7  # 热度数据缓存7天
        )

    def get_all_stock_board_industry_service(self)-> Dict[str, Any]:
        """
         查询同花顺行业一览表（行业名称、代码等）
        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 盘口异动数据，已映射到stock_changes表结构
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="board_industry_summary",
            params={'key_type': 'all_stock_board'},
            fetch_func=get_all_stock_board_industry,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 异动数据缓存1天（实时性要求高）
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
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_changes",
            params={'symbol': symbol, 'key_type': 'stock_changes'},
            fetch_func=get_stock_changes_em,
            validate_rules={
                "symbol": ['火箭发射', '快速反弹', '大笔买入', '封涨停板', '打开跌停板', '有大买盘',
                           '竞价上涨', '高开5日线', '向上缺口', '60日新高', '60日大幅上涨', '加速下跌',
                           '高台跳水', '大笔卖出', '封跌停板', '打开涨停板', '有大卖盘', '竞价下跌', '低开5日线',
                           '向下缺口', '60日新低', '60日大幅下跌']
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
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
            params={'key_type': 'board_change'},
            fetch_func=get_stock_board_change_em,
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )

    def get_stock_zt_pool_em_service(self, date_str: str) -> Dict[str, Any]:
        """
        查询东方财富涨停板行情

        Args:
            date_str	str	date_str='20241008'

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        date_str = self.date_str if not date_str else date_str
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_zt_pool",
            params={"date": date_str, 'key_type': 'stock_zt_pool_em'},
            fetch_func=get_stock_zt_pool_em,
            validate_rules={"date": "date"},
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )
    def get_stock_zt_pool_previous_em_service(self, date_str: str) -> Dict[str, Any]:
        """
        东方财富昨日涨停股池数据查询接口

        Args:
            date_str	str	date_str='20241008'

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        date_str = self.date_str if not date_str else date_str
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_zt_pool_previous",
            params={"date": date_str, 'key_type': 'zt_pool_previous'},
            fetch_func=get_stock_zt_pool_previous_em,
            validate_rules={"date": 'date'},
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )

    def get_stock_zt_pool_strong_em_service(self, date_str: str) -> Dict[str, Any]:
        """
        东方财富强势股池数据查询接口

        Args:
            date_str	str	date_str='20241008'

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        date_str = self.date_str if not date_str else date_str
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_zt_pool_strong",
            params={"date": date_str, 'key_type': 'zt_pool_strong'},
            fetch_func=get_stock_zt_pool_strong_em,
            validate_rules={"date": 'date'},
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )

    def get_stock_zt_pool_zbgc_em_service(self, date_str: str) -> Dict[str, Any]:
        """
        东方财富炸板股池数据查询接口

        Args:
            date_str	str	date_str='20241008'

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        date_str = self.date_str if not date_str else date_str
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_zt_pool_zbgc",
            params={"date": date_str, 'key_type': 'zt_pool_zbgc'},
            fetch_func=get_stock_zt_pool_zbgc_em,
            validate_rules={"date": 'date'},
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )

    def get_stock_zt_pool_dtgc_em_service(self, date_str: str) -> Dict[str, Any]:
        """
        东方财富跌停股池数据查询接口

        Args:
            date_str	str	date_str='20241008'

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        date_str = self.date_str if not date_str else date_str
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name="stock_zt_pool_dtgc",
            params={"date": date_str, 'key_type': 'zt_pool_dtgc'},
            fetch_func=get_stock_zt_pool_dtgc_em,
            validate_rules={"date": 'date'},
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1  # 板块异动数据缓存1天（实时性要求高）
        )

    def get_stock_financial_report_sina_service(self, stock: str, symbol: str) -> Dict[str, Any]:
        """
        新浪财经-财务报表-三大报表

        Args:
            stock: str - 带市场标识的股票代码，如 "sh600600"（沪市）或 "sz000001"（深市）
            symbol: str - 报表类型，可选值："资产负债表"、"利润表"、"现金流量表"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """

        stock = normalize_symbol(stock, 2)
        table_name_map = {
            "资产负债表": "financial_balance_sheet",
            "利润表": "financial_income_statement",
            "现金流量表": "financial_cash_flow_statement",
        }
        table_name = table_name_map.get(symbol, '')


        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name=table_name,
            params={"stock": stock, "symbol": symbol, 'key_type': 'financial_info'},
            fetch_func=get_stock_financial_report_sina,
            validate_rules={
                "symbol": ["资产负债表", "利润表", "现金流量表"],
            },
            async_write=True,
            cache_empty=False,
            ttl_redis=self.REDIS_TTL_MEDIUM,
            ttl_db=1,
        )


    def get_stock_profit_forecast_ths_service(self, symbol: str, indicator: str) -> Dict[str, Any]:
        """
        同花顺盈利预测数据查询接口

        Args:
             symbol: str - 股票代码，如 "000001"
             indicator: str - 指标类型，choice of {
                "预测年报每股收益",
                "预测年报净利润",
                "业绩预测详表-机构",
                "业绩预测详表-详细指标预测"
             }

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 板块异动详情数据，已映射到board_change表结构
                "message": str        # 成功或错误信息
            }
        """
        table_name_map = {
            "预测年报每股收益": "financial_forecast_summary",
            "预测年报净利润": "financial_forecast_summary",
            "业绩预测详表-机构": "financial_forecast_institution_detail",
            "业绩预测详表-详细指标预测": "financial_indicator_trend",
        }
        table_name = table_name_map.get(indicator, '')
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name=table_name,
            params={"indicator": indicator, "symbol": symbol, 'key_type': 'profit_forecast'},
            fetch_func=get_stock_profit_forecast_ths,
            validate_rules={
                "symbol": "stock",
                "indicator": ["预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", '业绩预测详表-详细指标预测'],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_fund_flow_individual_service(self, symbol: str, limits: str) -> Dict[str, Any]:
        """
        同花顺-数据中心-资金流向-个股资金流

        Args:
             symbol: str - 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
             limits:  获取前多少名的数据  截断数据的长度
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_stock_flow',
            params={"symbol": symbol, "limits": limits, 'key_type': 'fund_flow_individual'},
            fetch_func=get_stock_fund_flow_individual,
            validate_rules={
                "symbol": ["即时", "3日排行", "5日排行", "10日排行", "20日排行"],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_fund_flow_concept_service(self, symbol: str, limits: str) -> Dict[str, Any]:
        """
        同花顺-数据中心-资金流向-概念资金流

        Args:
             symbol: str - 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
             limits:  获取前多少名的数据  截断数据的长度
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='industry_funds_flow_individual',
            params={"symbol": symbol, "limits": limits, 'key_type': 'fund_flow_concept'},
            fetch_func=get_stock_fund_flow_concept,
            validate_rules={
                "symbol": ["即时", "3日排行", "5日排行", "10日排行", "20日排行"],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_individual_fund_flow_service(self, stock: str) -> Dict[str, Any]:
        """
        同花顺-数据中心-资金流向-概念资金流

        Args:
            stock: 股票代码，如 "000425"
        """

        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_individual_fund_flow',
            params={"stock": stock, 'key_type': 'fund_flow_concept'},
            fetch_func=get_stock_individual_fund_flow,
            validate_rules={
                "stock": "stock",
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_individual_fund_flow_rank_service(self, indicator: str) -> Dict[str, Any]:
        """
        同花顺-数据中心-资金流向-概念资金流

        Args:
            indicator: 时间周期，choice of {"今日", "3日", "5日", "10日"}
        """

        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_rank_fund_flow',
            params={"indicator": indicator, 'key_type': 'individual_fund'},
            fetch_func=get_stock_individual_fund_flow_rank,
            validate_rules={
                "indicator": ["今日", "3日", "5日", "10日"],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_market_fund_flow_service(self) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-大盘资金流向

        Args:

        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='market_fund_flow',
            params={'key_type': 'market_fund_flow'},
            fetch_func=get_stock_market_fund_flow,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )
    def get_stock_sector_fund_flow_rank_service(self, indicator: str, sector_type: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-板块资金流排名

        Args:

        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='market_fund_flow',
            params={ "indicator": indicator, "sector_type": sector_type, 'key_type': 'sector_fund'},
            fetch_func=get_stock_sector_fund_flow_rank,
            validate_rules={
                "indicator": ["今日", "3日", "5日", "10日"],
                "sector_type": ["行业资金流", "概念资金流", "地域资金流"],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_sector_fund_flow_summary_service(self, indicator: str, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-行业个股资金流

        Args:
            symbol: 行业板块名称，如 "电源设备"
            indicator: 时间周期，choice of {"今日", "5日", "10日"}

        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='market_fund_flow',
            params={ "indicator": indicator, "symbol": symbol, 'key_type': 'sector_fund_flow'},
            fetch_func=get_stock_sector_fund_flow_summary,
            validate_rules={
                "indicator": ["今日", "5日", "10日"],
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=1,
        )

    def get_stock_account_statistics_em_service(self) -> Dict[str, Any]:
        """
        股票账户统计月度数据查询接口（东方财富接口）

        接口: stock_account_statistics_em
        目标地址: https://data.eastmoney.com/cjsj/gpkhsj.html
        描述: 东方财富网-数据中心-特色数据-股票账户统计（月度）
        限量: 单次返回从 201504 开始至最新的所有历史数据

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股票账户统计数据
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='investor_market_stats',
            params={'key_type': 'account_statistics'},
            fetch_func=get_stock_account_statistics_em,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 账户统计数据缓存90天
        )

    def get_stock_comment_em_service(self) -> Dict[str, Any]:
        """
        千股千评数据查询接口（东方财富接口）

        接口: stock_comment_em
        目标地址: https://data.eastmoney.com/stockcomment/
        描述: 东方财富网-数据中心-特色数据-千股千评
        限量: 单次获取所有股票当日评分数据
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_comment_em',
            params={'key_type': 'stock_comment_em'},
            fetch_func=get_stock_comment_em,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 千股千评数据缓存90天
        )

    def get_stock_comment_detail_scrd_focus_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        千股千评-用户关注指数查询接口（东方财富接口）

        接口: stock_comment_detail_scrd_focus_em
        目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
        描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
        限量: 单次获取所有数据

        Args:
            symbol: 股票代码，如 "600000"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 用户关注指数数据
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_comment_detail',
            params={'symbol': symbol, 'key_type': 'comment_focus'},
            fetch_func=get_stock_comment_detail_scrd_focus_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 用户关注指数数据缓存90天
        )

    def get_stock_comment_detail_scrd_desire_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        千股千评-市场参与意愿查询接口（东方财富接口）

        接口: stock_comment_detail_scrd_desire_em
        目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
        描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
        限量: 单次获取所有数据

        Args:
            symbol: 股票代码，如 "600000"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 市场参与意愿数据
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_comment_detail_em',
            params={'symbol': symbol, 'key_type': 'comment_desire_em'},
            fetch_func=get_stock_comment_detail_scrd_desire_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 市场参与意愿数据缓存90天
        )

    def get_stock_zh_a_gdhs_service(self, date: str) -> Dict[str, Any]:
        """
        股东户数查询接口（东方财富接口）

        接口: stock_zh_a_gdhs
        目标地址: http://data.eastmoney.com/gdhs/
        描述: 东方财富网-数据中心-特色数据-股东户数数据
        限量: 单次获取返回所有数据

        Args:
            date: 查询日期，可选值：
                  "最新" - 获取最新一期股东户数数据
                  季度末日期 - 格式为 "YYYYMMDD"，如 "20240930"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股东户数数据
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_zh_a_gdhs',
            params={'date': date, 'key_type': 'gdhs'},
            fetch_func=get_stock_zh_a_gdhs,
            validate_rules={
                "date": "no_empty"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 股东户数数据缓存90天
        )

    def get_stock_zh_a_gdhs_detail_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        股东户数详情查询接口（东方财富接口）

        接口: stock_zh_a_gdhs_detail_em
        目标地址: https://data.eastmoney.com/gdhs/detail/000002.html
        描述: 东方财富网-数据中心-特色数据-股东户数详情
        限量: 单次获取指定 symbol 的所有数据

        Args:
            symbol: 股票代码，如 "000001"（平安银行），不带市场前缀

        Returns:
            统一格式的响应数据：
            {
                "success": bool,      # 调用是否成功
                "data": list,         # 股东户数详情数据
                "message": str        # 成功或错误信息
            }
        """
        # 调用通用模板方法
        return self.execute_cached_fetch(
            table_name='stock_holder_num',
            params={'symbol': symbol, 'key_type': 'gdhs_detail_em'},
            fetch_func=get_stock_zh_a_gdhs_detail_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90  # 股东户数详情数据缓存90天
        )

    # ============================================================================
    # LHB 模块服务函数
    # ============================================================================

    def get_stock_lhb_jgmmtj_em_service(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        龙虎榜机构买卖每日统计查询接口（东方财富接口）

        接口: stock_lhb_jgmmtj_em
        目标地址: https://data.eastmoney.com/stock/jgmmtj.html
        描述: 东方财富网-数据中心-龙虎榜单-机构买卖每日统计
        限量: 单次返回所有历史数据

        Args:
            start_date: 开始日期，格式为 "YYYYMMDD"，如 "20240417"
            end_date: 结束日期，格式为 "YYYYMMDD"，如 "20240430"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='lhb_institution_trading',
            params={'start_date': start_date, 'end_date': end_date, 'key_type': 'lhb_jgmmtj'},
            fetch_func=get_stock_lhb_jgmmtj_em,
            validate_rules={
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90,
            cache_key_exclude_fields=['start_date', 'end_date'],
            dedup_keys=['symbol', 'trade_date'],
        )

    def get_stock_lhb_detail_em_service(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        龙虎榜详情查询接口（东方财富接口）

        接口: stock_lhb_detail_em
        目标地址: https://data.eastmoney.com/stock/tradedetail.html
        描述: 东方财富网-数据中心-龙虎榜单-龙虎榜详情
        限量: 单次返回所有历史数据

        Args:
            start_date: 开始日期，格式为 "YYYYMMDD"，如 "20220314"
            end_date: 结束日期，格式为 "YYYYMMDD"，如 "20220315"
        """
        return self.execute_cached_fetch(
            table_name='lhb_detail_em',
            params={'start_date': start_date, 'end_date': end_date, 'key_type': 'lhb_detail'},
            fetch_func=get_stock_lhb_detail_em,
            validate_rules={
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90,
            dedup_keys=['symbol', 'trade_date'],
        )


    def get_stock_lhb_stock_statistic_em_service(self, symbol: str = "近一月") -> Dict[str, Any]:
        """
        个股上榜统计查询接口（东方财富接口）

        接口: stock_lhb_stock_statistic_em
        目标地址: https://data.eastmoney.com/stock/tradedetail.html
        描述: 东方财富网-数据中心-龙虎榜单-个股上榜统计
        限量: 单次返回所有历史数据

        Args:
            symbol: 时间范围，可选值：{"近一月", "近三月", "近六月", "近一年"}，默认 "近一月"

        """
        return self.execute_cached_fetch(
            table_name='lhb_dragon_tiger_summary',
            params={'symbol': symbol, 'key_type': 'lhb_stock_statistic'},
            fetch_func=get_stock_lhb_stock_statistic_em,
            validate_rules={
                "symbol": ["近一月", "近三月", "近六月", "近一年"]
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_lhb_hyyyb_em_service(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        每日活跃营业部查询接口（东方财富接口）

        接口: stock_lhb_hyyyb_em
        目标地址: https://data.eastmoney.com/stock/hyyyb.html
        描述: 东方财富网-数据中心-龙虎榜单-每日活跃营业部
        限量: 单次返回所有历史数据

        Args:
            start_date: 开始日期，格式为 "YYYYMMDD"，如 "20220311"
            end_date: 结束日期，格式为 "YYYYMMDD"，如 "20220315"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='lhb_broker_daily_stat',
            params={'start_date': start_date, 'end_date': end_date, 'key_type': 'lhb_hyyyb'},
            fetch_func=get_stock_lhb_hyyyb_em,
            validate_rules={
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90,
            cache_key_exclude_fields=['start_date', 'end_date'],
            dedup_keys=['symbol', 'trade_date'],
        )

    def get_stock_lhb_yyb_detail_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        营业部详情数据查询接口（东方财富接口）

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:
            symbol: 营业部代码，如 "10026729"
        """
        return self.execute_cached_fetch(
            table_name='stock_lhb_yyb_detail',
            params={'symbol': symbol, 'key_type': 'lhb_yyb_detail'},
            fetch_func=get_stock_lhb_yyb_detail_em,
            validate_rules={
                "symbol": "no_empty"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )


    def get_stock_lhb_yybph_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        营业部详情数据查询接口（东方财富接口）

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:
            symbol: "近一月"; choice of {"近一月", "近三月", "近六月", "近一年"}
        """
        return self.execute_cached_fetch(
            table_name='lhb_broker_performance_stat',
            params={'symbol': symbol, 'key_type': 'lhb_yybph'},
            fetch_func=get_stock_lhb_yybph_em,
            validate_rules={
                "symbol": ["近一月", "近三月", "近六月", "近一年"]
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_lhb_traderstatistic_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        营业部详情数据查询接口（东方财富接口）

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:
            symbol: "近一月"; choice of {"近一月", "近三月", "近六月", "近一年"}
        """
        return self.execute_cached_fetch(
            table_name='lhb_broker_summary_stat',
            params={'symbol': symbol, 'key_type': 'lhb_traderstatistic'},
            fetch_func=get_stock_lhb_traderstatistic_em,
            validate_rules={
                "symbol": ["近一月", "近三月", "近六月", "近一年"]
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_lhb_stock_detail_em_service(self, symbol: str, date: str, flag: str) -> Dict[str, Any]:
        """
        营业部详情数据查询接口（东方财富接口）

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:
            - symbol="600077";
            - date="20220310"; 需要通过 ak.stock_lhb_stock_detail_date_em(symbol="600077") 接口获取相应股票的有龙虎榜详情数据的日期
            - flag="卖出"; choice of {"买入", "卖出"}
        """
        return self.execute_cached_fetch(
            table_name='lhb_broker_summary_stat',
            params={'symbol': symbol, "date": date, "flag": flag, 'key_type': 'lhb_stock_detail'},
            fetch_func=get_stock_lhb_stock_detail_em,
            validate_rules={
                "symbol": 'stock',
                "flag": ["买入", "卖出"],
                "date": 'date'
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_lhb_stock_detail_date_em_service(self, symbol: str,) -> Dict[str, Any]:
        """
        个股龙虎榜日期列表

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:
            - symbol="600077";
            - date="20220310"; 需要通过 ak.stock_lhb_stock_detail_date_em(symbol="600077") 接口获取相应股票的有龙虎榜详情数据的日期
            - flag="卖出"; choice of {"买入", "卖出"}
        """
        return self.execute_cached_fetch(
            table_name='lhb_stock_detail_date',
            params={'symbol': symbol, 'key_type': 'stock_detail_date'},
            fetch_func=get_stock_lhb_stock_detail_date_em,
            validate_rules={
                "symbol": 'stock',
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_lh_yyb_most_service(self) -> Dict[str, Any]:
        """
        个股龙虎榜日期列表

        接口: stock_lhb_yyb_detail_em
        目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
        描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
        限量: 单次返回指定营业部的所有历史数据

        Args:

        """
        return self.execute_cached_fetch(
            table_name='lhb_broker_league_stat',
            params={'key_type': 'lh_yyb_most'},
            fetch_func=get_stock_lh_yyb_most,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )



    # ============================================================================
    # Margin 模块服务函数
    # ============================================================================

    def get_stock_margin_account_info_service(self) -> Dict[str, Any]:
        """
        两融账户信息查询接口（东方财富接口）

        接口: stock_margin_account_info
        目标地址: https://data.eastmoney.com/rzrq/txt.html
        描述: 东方财富网-数据中心-融资融券-两融账户
        限量: 单次返回所有数据

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='margin_trading_daily_stat',
            params={'key_type': 'margin_account'},
            fetch_func=get_stock_margin_account_info,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_margin_sse_service(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        上交所融资融券汇总查询接口（东方财富接口）

        接口: stock_margin_sse
        目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
        描述: 上海证券交易所-融资融券数据
        限量: 单次返回指定日期区间的所有数据

        Args:
            start_date: 开始日期，格式为 "YYYYMMDD"，如 "20240901"
            end_date: 结束日期，格式为 "YYYYMMDD"，如 "20240930"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='margin_trading_daily_detail',
            params={'start_date': start_date, 'end_date': end_date, 'key_type': 'margin_sse'},
            fetch_func=get_stock_margin_sse,
            validate_rules={
                "start_date": "date",
                "end_date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_margin_detail_szse_service(self, date: str) -> Dict[str, Any]:
        """
        深交所融资融券明细查询接口（东方财富接口）

        接口: stock_margin_detail_szse
        目标地址: https://www.szse.cn/market/dealingdata/margin/index.html
        描述: 深圳证券交易所-融资融券明细
        限量: 单次返回指定日期的所有数据

        Args:
            date: 查询日期，格式为 "YYYYMMDD"，如 "20240930"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_margin_detail_szse',
            params={'date': date, 'key_type': 'margin_detail_szse'},
            fetch_func=get_stock_margin_detail_szse,
            validate_rules={
                "date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_margin_detail_sse_service(self, date: str) -> Dict[str, Any]:
        """
        上交所融资融券明细查询接口（东方财富接口）

        接口: stock_margin_detail_sse
        目标地址: https://www.sse.com.cn/market/dealingdata/overview/margin/
        描述: 上海证券交易所-融资融券明细
        限量: 单次返回指定日期的所有数据

        Args:
            date: 查询日期，格式为 "YYYYMMDD"，如 "20240930"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_margin_detail_sse',
            params={'date': date, 'key_type': 'margin_detail_sse'},
            fetch_func=get_stock_margin_detail_sse,
            validate_rules={
                "date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    # ============================================================================
    # Pledge 模块服务函数
    # ============================================================================

    def get_stock_gpzy_profile_em_service(self) -> Dict[str, Any]:
        """
        股权质押市场概况查询接口（东方财富接口）

        接口: stock_gpzy_profile_em
        目标地址: https://data.eastmoney.com/gpzy/marketProfile.aspx
        描述: 东方财富网-数据中心-特色数据-股权质押-股权质押市场概况
        限量: 单次所有历史数据

        """
        return self.execute_cached_fetch(
            table_name='market_pledge_daily_stat',
            params={'key_type': 'gpzy_profile'},
            fetch_func=get_stock_gpzy_profile_em,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_gpzy_pledge_ratio_em_service(self, date: str) -> Dict[str, Any]:
        """
        上市公司质押比例查询接口（东方财富接口）

        接口: stock_gpzy_pledge_ratio_em
        目标地址: https://data.eastmoney.com/gpzy/pledgeRatio.aspx
        描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例
        限量: 单次返回指定交易日的所有历史数据

        Args:
            date: 交易日，格式为 "YYYYMMDD"，如 "20240906"

        """
        return self.execute_cached_fetch(
            table_name='stock_gpzy_pledge_ratio',
            params={'date': date, 'key_type': 'gpzy_pledge_ratio'},
            fetch_func=get_stock_gpzy_pledge_ratio_em,
            validate_rules={
                "date": "date"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_gpzy_individual_pledge_ratio_detail_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        个股重要股东股权质押明细查询接口（东方财富接口）

        接口: stock_gpzy_company_em
        目标地址: https://data.eastmoney.com/gpzy/
        描述: 东方财富网-数据中心-股权质押-个股质押明细
        限量: 单次所有历史数据

        Args:
            symbol: 股票代码，如 "603132"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_gpzy_individual_detail',
            params={'symbol': symbol, 'key_type': 'gpzy_individual'},
            fetch_func=get_stock_gpzy_individual_pledge_ratio_detail_em,
            validate_rules={
                "symbol": "stock"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )

    def get_stock_gpzy_industry_data_em_service(self) -> Dict[str, Any]:
        """
        上市公司质押比例-行业数据查询接口（东方财富接口）

        接口: stock_gpzy_industry_data_em
        目标地址: https://data.eastmoney.com/gpzy/industryData.aspx
        描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据
        限量: 单次返回所有历史数据

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_gpzy_industry',
            params={'key_type': 'gpzy_industry'},
            fetch_func=get_stock_gpzy_industry_data_em,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=90
        )
    # ============================================================================
    # 技术选股排名服务函数
    # ============================================================================

    def get_stock_rank_cxg_ths_service(self, symbol: str = "创月新高") -> Dict[str, Any]:
        """
        同花顺技术指标-创新高数据查询接口

        接口: stock_rank_cxg_ths
        目标地址: https://data.10jqka.com.cn/rank/cxg/
        描述: 同花顺-数据中心-技术选股-创新高
        限量: 单次指定 symbol 的所有数据

        Args:
            symbol: 创新高类型，可选值: "创月新高", "半年新高", "一年新高", "历史新高"

        """
        return self.execute_cached_fetch(
            table_name='stock_rank_cxg',
            params={'symbol': symbol, 'key_type': 'rank_cxg'},
            fetch_func=get_stock_rank_cxg_ths,
            validate_rules={
                "symbol": "rank_cxg"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )

    def get_stock_rank_cxd_ths_service(self, symbol: str = "创月新高") -> Dict[str, Any]:
        """
        同花顺技术指标-创新高数据查询接口

        接口: stock_rank_cxg_ths
        目标地址: https://data.10jqka.com.cn/rank/cxg/
        描述: 同花顺-数据中心-技术选股-创新高
        限量: 单次指定 symbol 的所有数据

        Args:
            symbol: 创新高类型，可选值: "创月新高", "半年新高", "一年新高", "历史新高"

        """
        return self.execute_cached_fetch(
            table_name='stock_rank_cxg',
            params={'symbol': symbol, 'key_type': 'rank_cxd_ths'},
            fetch_func=get_stock_rank_cxd_ths,
            validate_rules={
                "symbol": "rank_cxg"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    def get_stock_rank_lxsz_ths_service(self) -> Dict[str, Any]:
        """
        同花顺技术选股-连续上涨数据查询接口

        接口: stock_rank_lxsz_ths
        目标地址: https://data.10jqka.com.cn/rank/lxsz/
        描述: 同花顺-数据中心-技术选股-连续上涨
        限量: 单次返回所有数据

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_continuous_stats',
            params={'key_type': 'rank_lxsz'},
            fetch_func=get_stock_rank_lxsz_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )

    def get_stock_rank_lxxd_ths_service(self) -> Dict[str, Any]:
        """
        同花顺技术选股-连续下跌数据查询接口

        接口: stock_rank_lxsz_ths
        目标地址: https://data.10jqka.com.cn/rank/lxsz/
        描述: 同花顺-数据中心-技术选股-连续上涨
        限量: 单次返回所有数据

        """
        return self.execute_cached_fetch(
            table_name='stock_continuous_stats',
            params={'key_type': 'rank_lxxd'},
            fetch_func=get_stock_rank_lxxd_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    def get_stock_rank_cxfl_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺技术选股-持续放量数据

        接口: akshare.stock_rank_cxsl_ths
        目标地址: https://data.10jqka.com.cn/rank/cxsl/

        """
        return self.execute_cached_fetch(
            table_name='stock_volume_stats',
            params={'key_type': 'rank_cxfl'},
            fetch_func=get_stock_rank_cxfl_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    def get_stock_rank_cxsl_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺技术选股-持续缩量数据

        接口: akshare.stock_rank_cxsl_ths
        目标地址: https://data.10jqka.com.cn/rank/cxsl/

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_volume_stats',
            params={'key_type': 'rank_cxsl'},
            fetch_func=get_stock_rank_cxsl_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    def get_stock_rank_xstp_ths_service(self, symbol: str = "500日均线") -> Dict[str, Any]:
        """
        查询同花顺技术选股-向上突破数据

        接口: akshare.stock_rank_xstp_ths
        目标地址: https://data.10jqka.com.cn/rank/xstp/

        Args:
            symbol: 均线周期类型，可选值: "5日均线", "10日均线", "20日均线", 
                   "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"
        """
        return self.execute_cached_fetch(
            table_name='stock_breakthrough_stats',
            params={'symbol': symbol, 'key_type': 'rank_xstp'},
            fetch_func=get_stock_rank_xstp_ths,
            validate_rules={
                "symbol": ["5日均线", "10日均线", "20日均线",
                   "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"]
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )

    def get_stock_rank_xxtp_ths_service(self, symbol: str = "500日均线") -> Dict[str, Any]:
        """
        查询同花顺技术选股-向下突破数据

        接口: akshare.stock_rank_xstp_ths
        目标地址: https://data.10jqka.com.cn/rank/xstp/

        Args:
            symbol: 均线周期类型，可选值: "5日均线", "10日均线", "20日均线",
                   "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"
        """
        return self.execute_cached_fetch(
            table_name='stock_breakthrough_stats',
            params={'symbol': symbol, 'key_type': 'rank_xstp'},
            fetch_func=get_stock_rank_xxtp_ths,
            validate_rules={
                "symbol": ["5日均线", "10日均线", "20日均线",
                   "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"]
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    def get_stock_rank_ljqs_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺技术选股-量价齐升数据

        接口: akshare.stock_rank_ljqs_ths
        目标地址: https://data.10jqka.com.cn/rank/ljqs/

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_volume_price_trend_stats',
            params={'key_type': 'rank_ljqs'},
            fetch_func=get_stock_rank_ljqs_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )

    def get_stock_rank_ljqd_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺技术选股-量价齐跌数据

        接口: akshare.stock_rank_ljqd_ths
        目标地址: https://data.10jqka.com.cn/rank/ljqd/

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_volume_price_trend_stats',
            params={'key_type': 'rank_ljqd'},
            fetch_func=get_stock_rank_ljqd_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )

    def get_stock_rank_xzjp_ths_service(self) -> Dict[str, Any]:
        """
        查询同花顺技术选股-险资举牌数据

        接口: akshare.stock_rank_xzjp_ths
        目标地址: https://data.10jqka.com.cn/financial/xzjp/

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_announcement_holding',
            params={'key_type': 'rank_xzjp'},
            fetch_func=get_stock_rank_xzjp_ths,
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7
        )


    # ============================================================================
    # 历史行情数据服务函数
    # ============================================================================

    def get_stock_zh_a_spot_service(self) -> Dict[str, Any]:
        """
        查询新浪财经-沪深京 A 股实时行情数据

        接口: akshare.stock_zh_a_spot
        目标地址: https://vip.stock.finance.sina.com.cn/mkt/#hs_a
        描述: 新浪财经-沪深京 A 股数据, 重复运行本函数会被新浪暂时封 IP, 建议增加时间间隔
        限量: 单次返回沪深京 A 股上市公司的实时行情数据
        """
        return self.execute_cached_fetch(
            table_name='stock_real_time_quotes',
            params={'key_type': 'zh_a_spot'},
            fetch_func=get_stock_zh_a_spot,
            async_write=True,
            ttl_redis=self.REDIS_TTL_SHORT,
            ttl_db=1
        )

    def get_stock_individual_spot_xq_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询雪球-个股实时行情数据

        接口: akshare.stock_individual_spot_xq
        目标地址: https://xueqiu.com/S/SH513520
        描述: 雪球-行情中心-个股，单次获取指定 symbol 的最新行情数据
        限量: 单次获取指定 symbol 的最新行情数据

        Args:
            symbol: 证券代码，例如 "SH600000"、"SZ000001"、"HK00700"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_real_time_quotes',
            params={'symbol': symbol, 'key_type': 'individual_spot_xq'},
            fetch_func=get_stock_individual_spot_xq,
            validate_rules={
                "symbol": "no_empty"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_SHORT,
            ttl_db=1
        )

    # ── 个股信息查询-东财 ──────────────────────────────────────────

    def get_stock_individual_info_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富-个股-股票信息。

        接口: akshare.stock_individual_info_em
        目标地址: http://quote.eastmoney.com/concept/sh603777.html?from=classic
        描述: 东方财富-个股-股票信息（含股票代码、简称、总股本、流通股、行业、总市值、流通市值、上市日期、最新价）

        Args:
            symbol: 股票代码, 例: "603777"

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": dict,       # 扁平化股票信息字典
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_individual_info',
            params={'symbol': symbol, 'key_type': 'stock_individual_info'},
            fetch_func=get_stock_individual_info_em,
            validate_rules={
                "symbol": "stock",
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=7,
        )

    def get_stock_zh_a_hist_service(self, symbol: str, period: str = "daily", 
                                   start_date: str = "", end_date: str = "", 
                                   adjust: str = "") -> Dict[str, Any]:
        """
        查询东方财富-沪深京 A 股日频率历史行情数据

        接口: akshare.stock_zh_a_hist
        目标地址: https://quote.eastmoney.com/concept/sh603777.html?from=classic
        描述: 东方财富-沪深京 A 股日频率数据; 历史数据按日频率更新, 当日收盘价请在收盘后获取
        限量: 单次返回指定沪深京 A 股上市公司、指定周期和指定日期间的历史行情日频率数据

        Args:
            symbol: 股票代码, 例: "603777"
            period: 周期, 可选值: daily, weekly, monthly; 默认: daily
            start_date: 开始日期, 格式: yyyymmdd, 例: "20210301"
            end_date: 结束日期, 格式: yyyymmdd, 例: "20210616"
            adjust: 复权类型, 可选值: 空(不复权), qfq(前复权), hfq(后复权); 默认: 不复权

        """
        return self.execute_cached_fetch(
            table_name='stock_daily_history',
            params={'symbol': symbol, 'period': period, 'start_date': start_date, 
                   'end_date': end_date, 'adjust': adjust, 'key_type': 'zh_a_hist'},
            fetch_func=get_stock_zh_a_hist,
            validate_rules={
                "symbol": "stock",
                "period": ["daily", "weekly", "monthly"],
                "start_date": "date_optional",
                "end_date": "date_optional"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=30
        )

    def get_stock_zh_a_daily_service(self, symbol: str, start_date: str = "", 
                                    end_date: str = "", adjust: str = "") -> Dict[str, Any]:
        """
        查询新浪财经-沪深京 A 股历史行情日频率数据
        注意：多次获取容易封禁 IP，建议优先使用 stock_zh_a_hist 接口

        接口: akshare.stock_zh_a_daily
        目标地址: https://finance.sina.com.cn/realstock/company/sh600006/nc.shtml
        描述: 新浪财经-沪深京 A 股的数据, 历史数据按日频率更新
        限量: 单次返回指定沪深京 A 股上市公司指定日期间的历史行情日频率数据

        Args:
            symbol: 股票代码, 例: "sh600000"
            start_date: 开始日期, 格式: yyyymmdd, 例: "20201103"
            end_date: 结束日期, 格式: yyyymmdd, 例: "20201116"
            adjust: 复权类型, 可选值: 空(不复权), qfq, hfq, hfq-factor, qfq-factor; 默认: 空

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_daily_history',
            params={'symbol': symbol, 'start_date': start_date, 'end_date': end_date,
                   'adjust': adjust, 'key_type': 'zh_a_daily'},
            fetch_func=get_stock_zh_a_daily,
            validate_rules={
                "symbol": "stock_with_prefix",
                "start_date": "date_optional",
                "end_date": "date_optional"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_LONG,
            ttl_db=30
        )

    def get_stock_zh_a_hist_min_em_service(self, symbol: str, period: str = "1",
                                          start_date: str = "", end_date: str = "",
                                          adjust: str = "") -> Dict[str, Any]:
        """
        查询东方财富-沪深京 A 股分时/分钟级历史行情数据

        接口: akshare.stock_zh_a_hist_min_em
        目标地址: https://quote.eastmoney.com/concept/sh603777.html
        描述: 东方财富网-行情首页-沪深京 A 股-每日分时行情; 该接口只能获取近期的分时数据，注意时间周期的设置
        限量: 单次返回指定股票、频率、复权调整和时间区间的分时数据, 其中 1 分钟数据只返回近 5 个交易日数据且不复权

        Args:
            symbol: 股票代码, 例: "603777"
            period: 周期, 可选值: 1, 5, 15, 30, 60; 默认: 1
            start_date: 开始日期, 格式: yyyy-mm-dd, 例: "2025-01-01"
            end_date: 结束日期, 格式: yyyy-mm-dd, 例: "2025-01-15"
            adjust: 复权类型, 可选值: "", "qfq", "hfq"; 默认: ""

        Returns:
            统一格式的响应数据：
            {
                "success": bool,
                "data": list,
                "message": str
            }
        """
        return self.execute_cached_fetch(
            table_name='stock_minute_history',
            params={'symbol': symbol, 'period': period, 'start_date': start_date,
                   'end_date': end_date, 'adjust': adjust, 'key_type': 'zh_a_hist_min_em'},
            fetch_func=get_stock_zh_a_hist_min_em,
            validate_rules={
                "symbol": "stock",
                "period": ["1", "5", "15", "30", "60"],
                "start_date": "date_format",
                "end_date": "date_format"
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_SHORT,
            ttl_db=7
        )

    def get_stock_board_industry_cons_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富-板块板块-行业板块-行业成份股

        接口: akshare.stock_board_industry_cons_em
        目标地址: https://data.eastmoney.com/bkzj/hy.html

        Args:
            symbol: 行业板块名称，如 "元件"
        """
        return self.execute_cached_fetch(
            table_name='board_industry_cons',
            params={'symbol': symbol, 'key_type': 'board_industry_cons'},
            fetch_func=get_stock_board_industry_cons_em,
            validate_rules={
                "symbol": "no_empty",
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=30
        )

    def get_stock_board_concept_cons_em_service(self, symbol: str) -> Dict[str, Any]:
        """
        查询东方财富-板块板块-概念板块-概念成份股

        接口: akshare.stock_board_concept_cons_em
        目标地址: https://data.eastmoney.com/bkzj/gn.html

        Args:
            symbol: 概念板块名称，如 "阿里巴巴概念"
        """
        return self.execute_cached_fetch(
            table_name='board_concept_cons',
            params={'symbol': symbol, 'key_type': 'board_concept_cons'},
            fetch_func=get_stock_board_concept_cons_em,
            validate_rules={
                "symbol": "no_empty",
            },
            async_write=True,
            ttl_redis=self.REDIS_TTL_MORE_LONG,
            ttl_db=30
        )

    # ── 昨日涨幅筛选 ─────────────────────────────────────────────

    def get_yesterday_surge_stocks_service(
        self,
        min_pct: float = 3.0,
        max_pct: Optional[float] = None,
        limit: int = 50,
        sort: str = "desc",
    ) -> Dict[str, Any]:
        """
        获取昨日涨幅超过指定阈值的股票列表。

        数据来源: stock_klines.stock_klines_{year} 分年表
        计算方式: change_percent = (close - prev_close) / prev_close * 100

        Args:
            min_pct:  最小涨幅（%），默认 3.0
            max_pct:  最大涨幅（%），None=不限制
            limit:    返回条数，默认 50
            sort:     排序方向 desc/asc，默认 desc

        Returns:
            {success, data: [{symbol, name, close, prev_close, change_percent, volume, amount}, ...]}
        """
        try:
            import pymysql
            from utils.db import get_conn as _get_main_conn

            # 1. 确定昨天和前天（向前回溯找最近交易日）
            today = date.today()
            yesterday = today
            for _ in range(5):
                yesterday = yesterday - timedelta(days=1)
                if yesterday.weekday() < 5:
                    break
            prev_day = yesterday
            for _ in range(5):
                prev_day = prev_day - timedelta(days=1)
                if prev_day.weekday() < 5:
                    break

            yesterday_str = yesterday.strftime("%Y-%m-%d")
            prev_str = prev_day.strftime("%Y-%m-%d")
            year = yesterday.year

            # 2. 构建 SQL（单次 JOIN 完成）
            order_dir = "DESC" if sort == "desc" else "ASC"
            max_pct_clause = "AND ROUND((t.close - y.close) / y.close * 100, 2) <= %s" if max_pct is not None else ""

            sql = f"""
                SELECT
                    t.symbol,
                    s.name,
                    t.close AS yesterday_close,
                    y.close AS prev_close,
                    ROUND((t.close - y.close) / y.close * 100, 2) AS change_percent,
                    t.vol AS volume,
                    t.amount
                FROM stock_klines.stock_klines_{year} t
                JOIN stock_klines.stock_klines_{year} y
                    ON t.symbol = y.symbol
                    AND DATE(y.datetime) = %s
                LEFT JOIN lianghua.stocks_info s ON t.symbol = s.symbol
                WHERE DATE(t.datetime) = %s
                  AND y.close > 0
                  AND (t.close - y.close) / y.close * 100 >= %s
                  {max_pct_clause}
                ORDER BY change_percent {order_dir}
                LIMIT %s
            """

            params = [prev_str, yesterday_str, float(min_pct)]
            if max_pct is not None:
                params.append(float(max_pct))
            params.append(int(limit))

            # 3. 执行查询（get_conn 使用 DictCursor，返回已是 dict）
            conn = _get_main_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            finally:
                conn.close()

            # 4. 格式化输出（Decimal → float）
            result = []
            for row in rows:
                item = {}
                for k, v in row.items():
                    if v is not None and hasattr(v, "__float__"):
                        item[k] = float(v)
                    else:
                        item[k] = v
                result.append(item)

            self.logger.info(
                "[yesterday_surge] %s~%s | min=%.1f%% | 命中 %d 条",
                prev_str, yesterday_str, min_pct, len(result),
            )
            return success_result(data=result, message=f"昨日涨幅>={min_pct}% 股票 {len(result)} 条")

        except Exception as e:
            self.logger.exception("[yesterday_surge] 查询异常: %s", e)
            return error_result(message=f"查询失败: {str(e)}")

# 全局服务实例
stock_basic_service = StockBasicService()



# 导出 
__all__ = [
    "StockBasicService",
    "stock_basic_service",
]


