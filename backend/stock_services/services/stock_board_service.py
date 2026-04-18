#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票板块概念模块 - 数据库优先服务类

参考龙虎榜详情接口的逻辑，实现数据库优先模式：
1. 数据库优先查询
2. 数据标准化入库
3. 异步写入机制
4. 统一错误处理

模块接口清单：
1. GET /api/stock/unity/board/concept-index/{symbol} - 概念板块指数
2. GET /api/stock/unity/board/industry-summary - 行业一览表
3. GET /api/stock/unity/board/concept-info/{symbol} - 概念板块简介
4. GET /api/stock/unity/board/industry-index/{symbol} - 行业板块指数
5. GET /api/stock/unity/board/hot-follow/{symbol} - 雪球关注排行榜
6. GET /api/stock/unity/board/hot-rank/{symbol} - 股票热度历史趋势
7. GET /api/stock/unity/board/hot-keyword/{symbol} - 个股人气榜热门关键词
8. GET /api/stock/unity/board/changes/{symbol} - 盘口异动数据
9. GET /api/stock/unity/board/board-change - 当日板块异动
"""

import logging
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import time
from stock_services.unity import *
from models.stock_models import (
    get_conn,
    ensure_all_base_tables,
    # 板块概念相关表
    fetch_board_industry_summary,
    save_board_industry_summary_batch,
    fetch_board_concept_info,
    save_board_concept_info_batch,
    fetch_board_hot_follow,
    save_board_hot_follow_batch,
    fetch_board_hot_rank,
    save_board_hot_rank_batch,
    fetch_board_hot_keyword,
    save_board_hot_keyword_batch,
    fetch_board_changes,
    save_board_changes_batch,
    fetch_board_change,
    save_board_change_batch,
    # 底层unity接口
    get_stock_board_concept_index_ths,
    get_stock_board_industry_summary_ths,
    get_stock_board_concept_info_ths,
    get_stock_board_industry_index_ths,
    get_stock_hot_follow_xq,
    get_stock_hot_rank_detail_em,
    get_stock_hot_keyword_em,
    get_stock_changes_em,
    get_stock_board_change_em,
)



logger = logging.getLogger(__name__)


class StockBoardService:
    """股票板块概念模块 - 数据库优先服务类"""
    
    # 最小数据条数阈值
    MIN_DATA_THRESHOLD = {
        'industry_summary': 10,      # 行业一览表
        'concept_info': 1,           # 概念板块简介
        'hot_follow': 10,            # 雪球关注排行榜
        'hot_rank': 30,              # 股票热度历史趋势
        'hot_keyword': 5,            # 热门关键词
        'changes': 5,                # 盘口异动数据
        'board_change': 5,           # 当日板块异动
    }
    
    @staticmethod
    def _standardize_symbol(symbol: str) -> str:
        """标准化股票代码"""
        if not symbol:
            return symbol
        
        # 如果是数字代码，添加交易所后缀
        if symbol.isdigit():
            if symbol.startswith('6'):
                return f"{symbol}.SH"
            elif symbol.startswith('0') or symbol.startswith('3'):
                return f"{symbol}.SZ"
            else:
                return symbol
        return symbol
    
    @staticmethod
    def _get_current_date() -> str:
        """获取当前日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")
    
    @staticmethod
    def _get_current_datetime() -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ============================================================================
    # 1. 概念板块指数接口
    # ============================================================================
    
    @staticmethod
    def get_board_concept_index_service(
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        查询同花顺概念板块指数日频率数据 - 数据库优先模式
        
        Args:
            symbol: 概念板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询概念板块指数数据 symbol={symbol}, start_date={start_date}, end_date={end_date}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 注意：此接口为时间序列数据，不适合数据库缓存
            # 直接调用底层接口
            result = get_stock_board_concept_index_ths(std_symbol, start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺概念板块指数查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            logger.info(f"[股票板块服务] 同花顺概念板块指数查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺概念板块指数查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 2. 行业一览表接口
    # ============================================================================
    
    @staticmethod
    def get_board_industry_summary_service() -> Dict[str, Any]:
        """
        查询同花顺行业一览表 - 数据库优先模式
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询同花顺行业一览表数据")
        
        try:
            # 1. 先查询数据库
            db_data = fetch_board_industry_summary()
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['industry_summary']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": "industry_summary"
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_board_industry_summary_ths()
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "同花顺行业一览表查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": "industry_summary"
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_industry_summary_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"同花顺行业一览表查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}
    
    # ============================================================================
    # 3. 概念板块简介接口
    # ============================================================================
    
    @staticmethod
    def get_board_concept_info_service(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块简介 - 数据库优先模式
        
        Args:
            symbol: 概念板块代码
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询同花顺概念板块简介数据 symbol={symbol}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 1. 先查询数据库
            db_data = fetch_board_concept_info(std_symbol)
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['concept_info']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": std_symbol
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_board_concept_info_ths(std_symbol)
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "同花顺概念板块简介查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": std_symbol
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_concept_info_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"同花顺概念板块简介查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 4. 行业板块指数接口
    # ============================================================================
    
    @staticmethod
    def get_board_industry_index_service(
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        查询同花顺行业板块指数日频率数据 - 数据库优先模式
        
        Args:
            symbol: 行业板块代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询行业板块指数数据 symbol={symbol}, start_date={start_date}, end_date={end_date}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 注意：此接口为时间序列数据，不适合数据库缓存
            # 直接调用底层接口
            result = get_stock_board_industry_index_ths(std_symbol, start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺行业板块指数查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            logger.info(f"[股票板块服务] 同花顺行业板块指数查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺行业板块指数查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 5. 雪球关注排行榜接口
    # ============================================================================
    
    @staticmethod
    def get_board_hot_follow_service(symbol: str) -> Dict[str, Any]:
        """
        查询雪球关注排行榜 - 数据库优先模式
        
        Args:
            symbol: 股票代码
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询雪球关注排行榜数据 symbol={symbol}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 1. 先查询数据库
            db_data = fetch_board_hot_follow(std_symbol)
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['hot_follow']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": std_symbol
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_hot_follow_xq(std_symbol)
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "雪球关注排行榜查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": std_symbol
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_hot_follow_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"雪球关注排行榜查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 6. 股票热度历史趋势接口
    # ============================================================================
    
    @staticmethod
    def get_board_hot_rank_service(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富股票热度历史趋势及粉丝特征 - 数据库优先模式
        
        Args:
            symbol: 股票代码
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询股票热度历史趋势数据 symbol={symbol}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 1. 先查询数据库
            db_data = fetch_board_hot_rank(std_symbol)
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['hot_rank']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": std_symbol
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_hot_rank_detail_em(std_symbol)
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "股票热度历史趋势查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": std_symbol
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_hot_rank_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"股票热度历史趋势查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 7. 个股人气榜热门关键词接口
    # ============================================================================
    
    @staticmethod
    def get_board_hot_keyword_service(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富个股人气榜热门关键词 - 数据库优先模式
        
        Args:
            symbol: 股票代码
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询个股人气榜热门关键词数据 symbol={symbol}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 1. 先查询数据库
            db_data = fetch_board_hot_keyword(std_symbol)
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['hot_keyword']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": std_symbol
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_hot_keyword_em(std_symbol)
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "个股人气榜热门关键词查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": std_symbol
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_hot_keyword_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"个股人气榜热门关键词查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 8. 盘口异动数据接口
    # ============================================================================
    
    @staticmethod
    def get_board_changes_service(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富盘口异动数据 - 数据库优先模式
        
        Args:
            symbol: 股票代码
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询盘口异动数据 symbol={symbol}")
        
        try:
            # 标准化符号
            std_symbol = StockBoardService._standardize_symbol(symbol)
            
            # 1. 先查询数据库
            db_data = fetch_board_changes(std_symbol)
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['changes']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": std_symbol
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_changes_em(std_symbol)
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "盘口异动数据查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": std_symbol
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": std_symbol}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_changes_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"盘口异动数据查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 9. 当日板块异动接口
    # ============================================================================
    
    @staticmethod
    def get_board_change_service() -> Dict[str, Any]:
        """
        查询当日板块异动 - 数据库优先模式
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票板块服务] 开始查询当日板块异动数据")
        
        try:
            # 1. 先查询数据库
            db_data = fetch_board_change()
            logger.info(f"[股票板块服务] 数据库查询结果: {len(db_data)} 条记录")
            
            # 2. 检查数据量是否足够
            min_threshold = StockBoardService.MIN_DATA_THRESHOLD['board_change']
            if db_data and len(db_data) >= min_threshold:
                logger.info(f"[股票板块服务] 数据库数据充足 ({len(db_data)} >= {min_threshold})，直接返回")
                return {
                    "success": True,
                    "data": db_data,
                    "error": None,
                    "symbol": "board_change"
                }
            
            # 3. 数据库数据不足，调用外部API
            logger.info(f"[股票板块服务] 数据库数据不足 ({len(db_data) if db_data else 0} < {min_threshold})，调用外部API")
            api_result = get_stock_board_change_em()
            
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "当日板块异动查询失败")
                logger.error(f"[股票板块服务] {error_msg}")
                # 如果外部API失败，尝试返回数据库数据（即使不足）
                if db_data:
                    logger.info(f"[股票板块服务] 外部API失败，返回数据库数据 ({len(db_data)} 条)")
                    return {
                        "success": True,
                        "data": db_data,
                        "error": None,
                        "symbol": "board_change"
                    }
                return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}
            
            api_data = api_result.get("data", [])
            logger.info(f"[股票板块服务] 外部API查询成功，共 {len(api_data)} 条记录")
            
            # 4. 异步保存到数据库
            if api_data:
                try:
                    save_board_change_batch(api_data)
                    logger.info(f"[股票板块服务] 异步保存到数据库成功，共 {len(api_data)} 条记录")
                except Exception as save_error:
                    logger.warning(f"[股票板块服务] 数据库保存失败: {save_error}")
            
            return api_result
            
        except Exception as e:
            error_msg = f"当日板块异动查询失败: {str(e)}"
            logger.error(f"[股票板块服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}