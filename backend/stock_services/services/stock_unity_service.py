# -*- coding: utf-8 -*-
"""
股票Unity数据服务模块 - 统一接口封装

本模块提供所有股票相关数据的统一调用接口，采用数据库优先模式：
1. 先查询数据库，存在则直接返回
2. 不存在则调用AKShare接口获取
3. 同步写入数据库

所有接口都遵循统一的返回格式：
{
    "success": True/False,
    "data": [...],
    "error": None 或错误信息,
    "symbol": 股票代码或标识符
}

模块结构对应 backend/api/stock/unity/ 下的10个子模块：
1. basic: 股票基本信息
2. pledge: 股权质押
3. financial: 财务报表
4. holder: 股东数据
5. lhb: 龙虎榜
6. fund_flow: 资金流向
7. margin: 融资融券
8. board: 板块概念
9. zt: 涨跌停
10. rank: 技术选股排名
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# 导入所有unity模块
from stock_services.unity import (
    # 股票基本信息模块
    get_all_stock_codes,
    get_all_stock_codes_json,
    get_stock_individual_basic_info_xq,
    get_stock_info,
    get_stock_info_json,
    stock_info_bj_name_code,
    stock_info_sh_delist,
    stock_info_sh_name_code,
    stock_info_sz_delist,
    stock_info_sz_name_code,
    
    # 股权质押模块
    get_stock_gpzy_individual_pledge_ratio_detail_em,
    get_stock_gpzy_industry_data_em,
    get_stock_gpzy_pledge_ratio_em,
    get_stock_gpzy_profile_em,
    
    # 财务报表模块
    get_stock_balance_sheet_by_yearly_em,
    get_stock_cash_flow_sheet_by_report_em,
    get_stock_financial_report_sina,
    get_stock_profit_forecast_ths,
    get_stock_profit_sheet_by_report_em,
    get_stock_profit_sheet_by_yearly_em,
    
    # 股东数据模块
    get_stock_account_statistics_em,
    get_stock_comment_detail_scrd_desire_em,
    get_stock_comment_detail_scrd_focus_em,
    get_stock_comment_em,
    get_stock_zh_a_gdhs,
    get_stock_zh_a_gdhs_detail_em,
    
    # 龙虎榜模块
    get_stock_lhb_detail_em,
    get_stock_lhb_hyyyb_em,
    get_stock_lhb_jgmmtj_em,
    get_stock_lhb_stock_statistic_em,
    get_stock_lhb_yyb_detail_em,
    
    # 融资融券模块
    get_stock_margin_account_info,
    get_stock_margin_detail_sse,
    get_stock_margin_detail_szse,
    get_stock_margin_sse,
    
    # 板块概念模块
    get_stock_board_change_em,
    get_stock_board_concept_index_ths,
    get_stock_board_concept_info_ths,
    get_stock_board_industry_index_ths,
    get_stock_board_industry_summary_ths,
    get_stock_changes_em,
    get_stock_hot_follow_xq,
    get_stock_hot_keyword_em,
    get_stock_hot_rank_detail_em,
    
    # 涨跌停模块
    get_stock_zt_pool_dtgc_em,
    get_stock_zt_pool_em,
    get_stock_zt_pool_previous_em,
    get_stock_zt_pool_strong_em,
    get_stock_zt_pool_zbgc_em,
    
    # 技术选股排名模块
    get_stock_rank_cxfl_ths,
    get_stock_rank_cxg_ths,
    get_stock_rank_cxsl_ths,
    get_stock_rank_ljqd_ths,
    get_stock_rank_ljqs_ths,
    get_stock_rank_lxsz_ths,
    get_stock_rank_xstp_ths,
    get_stock_rank_xzjp_ths,
    
    # 资金流向模块
    get_stock_fund_flow_concept,
    get_stock_fund_flow_individual,
    get_stock_individual_fund_flow,
    get_stock_individual_fund_flow_rank,
    get_stock_main_fund_flow,
    get_stock_market_fund_flow,
    get_stock_sector_fund_flow_rank,
    get_stock_sector_fund_flow_summary,
)

# 导入数据库工具
from utils.db import table_exists, get_conn

logger = logging.getLogger(__name__)


# ── 通用类型转换辅助（None 安全）─────────────────────────────────────────
def _to_float(v) -> Union[float, None]:
    """将任意值安全转为 float，None/空字符串 返回 None"""
    if v is None or v == '':
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v) -> Union[int, None]:
    """将任意值安全转为 int，None/空字符串 返回 None"""
    if v is None or v == '':
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class StockUnityService:
    """
    股票Unity数据服务类
    
    提供所有股票相关数据的统一调用接口，封装底层akshare调用，
    提供统一的错误处理和响应格式。
    """
    
    @staticmethod
    def _infer_market(symbol: str) -> str:
        """
        根据股票代码推断市场
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            "SH" - 上海
            "SZ" - 深圳
            "BJ" - 北京
        """
        # 如果已经包含后缀，直接提取
        if '.' in symbol:
            suffix = symbol.split('.')[-1].upper()
            if suffix == 'SH':
                return 'SH'
            elif suffix == 'SZ':
                return 'SZ'
            elif suffix == 'BJ':
                return 'BJ'
            else:
                return 'SH'  # 默认
        
        # 根据代码前缀推断
        code = symbol
        if code.startswith('6'):
            return 'SH'
        elif code.startswith('0') or code.startswith('3'):
            return 'SZ'
        elif code.startswith('4') or code.startswith('8'):
            return 'BJ'
        else:
            return 'SH'  # 默认
    
    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """
        标准化股票代码格式
        
        Args:
            symbol: 原始股票代码
            
        Returns:
            标准化格式，如 "000001.SZ"
        """
        # 去除可能的前后空格
        symbol = symbol.strip()
        
        # 如果已经包含后缀，直接返回
        if '.' in symbol:
            return symbol
        
        # 推断市场并添加后缀
        market = StockUnityService._infer_market(symbol)
        return f"{symbol}.{market}"
    
    @staticmethod
    def _ensure_table(table_name: str, ddl: str) -> None:
        """确保指定表存在，不存在则按 ddl 创建"""
        if not table_exists(table_name):
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(ddl)
                conn.commit()
                logger.info(f"[股票Unity服务] 表 {table_name} 创建成功")
            finally:
                conn.close()
    
    # ============================================================================
    # 股票基本信息模块 (basic/)
    # ============================================================================
    
    @staticmethod
    def get_stock_info(symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询股票基本信息 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_info(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "股票信息查询失败")
                logger.error(f"[股票Unity服务] 股票信息查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 股票信息查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"股票基本信息查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_all_stock_codes() -> Dict[str, Any]:
        """
        获取全市场A股股票代码列表
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询全市场股票代码列表")
        
        try:
            # 调用底层unity接口
            result = get_all_stock_codes()
            
            if not result.get("success", False):
                error_msg = result.get("error", "全市场股票代码查询失败")
                logger.error(f"[股票Unity服务] 全市场股票代码查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "all_stocks"}
            
            logger.info(f"[股票Unity服务] 全市场股票代码查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"全市场股票代码查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "all_stocks"}
    
    @staticmethod
    def get_all_stock_codes_json() -> Dict[str, Any]:
        """
        获取全市场A股股票代码列表（JSON格式）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询全市场股票代码列表（JSON格式）")
        
        try:
            # 调用底层unity接口
            result = get_all_stock_codes_json()
            
            if not result.get("success", False):
                error_msg = result.get("error", "全市场股票代码JSON查询失败")
                logger.error(f"[股票Unity服务] 全市场股票代码JSON查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "all_stocks_json"}
            
            logger.info(f"[股票Unity服务] 全市场股票代码JSON查询成功")
            return result
            
        except Exception as e:
            error_msg = f"全市场股票代码JSON查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "all_stocks_json"}
    
    @staticmethod
    def stock_info_sh_name_code() -> Dict[str, Any]:
        """
        获取上海证券交易所股票代码和简称数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询上交所股票代码列表")
        
        try:
            # 调用底层unity接口
            result = stock_info_sh_name_code()
            
            if not result.get("success", False):
                error_msg = result.get("error", "上交所股票代码查询失败")
                logger.error(f"[股票Unity服务] 上交所股票代码查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "sh_stocks"}
            
            logger.info(f"[股票Unity服务] 上交所股票代码查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"上交所股票代码查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "sh_stocks"}
    
    @staticmethod
    def stock_info_sz_name_code() -> Dict[str, Any]:
        """
        获取深圳证券交易所股票代码和简称数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询深交所股票代码列表")
        
        try:
            # 调用底层unity接口
            result = stock_info_sz_name_code()
            
            if not result.get("success", False):
                error_msg = result.get("error", "深交所股票代码查询失败")
                logger.error(f"[股票Unity服务] 深交所股票代码查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "sz_stocks"}
            
            logger.info(f"[股票Unity服务] 深交所股票代码查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"深交所股票代码查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "sz_stocks"}
    
    @staticmethod
    def stock_info_bj_name_code() -> Dict[str, Any]:
        """
        获取北京证券交易所股票代码和简称数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询北交所股票代码列表")
        
        try:
            # 调用底层unity接口
            result = stock_info_bj_name_code()
            
            if not result.get("success", False):
                error_msg = result.get("error", "北交所股票代码查询失败")
                logger.error(f"[股票Unity服务] 北交所股票代码查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "bj_stocks"}
            
            logger.info(f"[股票Unity服务] 北交所股票代码查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"北交所股票代码查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "bj_stocks"}
    
    @staticmethod
    def stock_info_sh_delist() -> Dict[str, Any]:
        """
        获取上海证券交易所暂停/终止上市股票
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询上交所退市股票列表")
        
        try:
            # 调用底层unity接口
            result = stock_info_sh_delist()
            
            if not result.get("success", False):
                error_msg = result.get("error", "上交所退市股票查询失败")
                logger.error(f"[股票Unity服务] 上交所退市股票查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "sh_delist"}
            
            logger.info(f"[股票Unity服务] 上交所退市股票查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"上交所退市股票查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "sh_delist"}
    
    @staticmethod
    def stock_info_sz_delist() -> Dict[str, Any]:
        """
        获取深圳证券交易所终止/暂停上市股票
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询深交所退市股票列表")
        
        try:
            # 调用底层unity接口
            result = stock_info_sz_delist()
            
            if not result.get("success", False):
                error_msg = result.get("error", "深交所退市股票查询失败")
                logger.error(f"[股票Unity服务] 深交所退市股票查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "sz_delist"}
            
            logger.info(f"[股票Unity服务] 深交所退市股票查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"深交所退市股票查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "sz_delist"}
    
    @staticmethod
    def get_stock_individual_basic_info_xq(symbol: str) -> Dict[str, Any]:
        """
        查询雪球财经-个股-公司概况
        
        Args:
            symbol: 股票代码，需带市场前缀，如 "SH601127"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询雪球个股概况 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_individual_basic_info_xq(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "雪球个股概况查询失败")
                logger.error(f"[股票Unity服务] 雪球个股概况查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 雪球个股概况查询成功 symbol={symbol}")
            return result
            
        except Exception as e:
            error_msg = f"雪球个股概况查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_info_json(symbol: str) -> Dict[str, Any]:
        """
        查询个股信息并返回JSON字符串
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询股票信息JSON symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_info_json(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "股票信息JSON查询失败")
                logger.error(f"[股票Unity服务] 股票信息JSON查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 股票信息JSON查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"股票信息JSON查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 股权质押模块 (pledge/)
    # ============================================================================
    
    @staticmethod
    def get_stock_gpzy_profile_em() -> Dict[str, Any]:
        """
        查询股权质押市场概况（全量历史）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询股权质押市场概况")
        
        try:
            # 调用底层unity接口
            result = get_stock_gpzy_profile_em()
            
            if not result.get("success", False):
                error_msg = result.get("error", "股权质押市场概况查询失败")
                logger.error(f"[股票Unity服务] 股权质押市场概况查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_profile"}
            
            logger.info(f"[股票Unity服务] 股权质押市场概况查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"股权质押市场概况查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_profile"}
    
    @staticmethod
    def get_stock_gpzy_pledge_ratio_em(date: str) -> Dict[str, Any]:
        """
        查询指定交易日上市公司质押比例
        
        Args:
            date: 交易日，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询上市公司质押比例 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_gpzy_pledge_ratio_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "上市公司质押比例查询失败")
                logger.error(f"[股票Unity服务] 上市公司质押比例查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_pledge_ratio"}
            
            logger.info(f"[股票Unity服务] 上市公司质押比例查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"上市公司质押比例查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_pledge_ratio"}
    
    @staticmethod
    def get_stock_gpzy_individual_pledge_ratio_detail_em(symbol: str) -> Dict[str, Any]:
        """
        查询个股重要股东股权质押明细（全量历史）
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询个股股权质押明细 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_gpzy_individual_pledge_ratio_detail_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "个股股权质押明细查询失败")
                logger.error(f"[股票Unity服务] 个股股权质押明细查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 个股股权质押明细查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"个股股权质押明细查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_gpzy_industry_data_em() -> Dict[str, Any]:
        """
        查询各行业质押比例汇总数据（全量）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询各行业质押比例汇总数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_gpzy_industry_data_em()
            
            if not result.get("success", False):
                error_msg = result.get("error", "行业质押比例汇总查询失败")
                logger.error(f"[股票Unity服务] 行业质押比例汇总查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_industry"}
            
            logger.info(f"[股票Unity服务] 行业质押比例汇总查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"行业质押比例汇总查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "gpzy_industry"}
    
    # ============================================================================
    # 财务报表模块 (financial/)
    # ============================================================================
    
    @staticmethod
    def get_stock_financial_report_sina(stock: str, symbol: str) -> Dict[str, Any]:
        """
        查询新浪财经财务报表
        
        Args:
            stock: 股票代码，如 "600519"
            symbol: 报表类型，choice of {"资产负债表", "利润表", "现金流量表"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询新浪财经财务报表 stock={stock}, symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_financial_report_sina(stock, symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "新浪财经财务报表查询失败")
                logger.error(f"[股票Unity服务] 新浪财经财务报表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": stock}
            
            logger.info(f"[股票Unity服务] 新浪财经财务报表查询成功 stock={stock}, type={symbol}")
            return result
            
        except Exception as e:
            error_msg = f"新浪财经财务报表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": stock}
    
    @staticmethod
    def get_stock_balance_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富资产负债表（按年度）
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富资产负债表 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_balance_sheet_by_yearly_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富资产负债表查询失败")
                logger.error(f"[股票Unity服务] 东方财富资产负债表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 东方财富资产负债表查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"东方财富资产负债表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_profit_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富利润表（按报告期）
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富利润表（报告期） symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_profit_sheet_by_report_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富利润表查询失败")
                logger.error(f"[股票Unity服务] 东方财富利润表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 东方财富利润表查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"东方财富利润表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_profit_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富利润表（按年度）
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富利润表（年度） symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_profit_sheet_by_yearly_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富年度利润表查询失败")
                logger.error(f"[股票Unity服务] 东方财富年度利润表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 东方财富年度利润表查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"东方财富年度利润表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_cash_flow_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富现金流量表（按报告期）
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富现金流量表 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_cash_flow_sheet_by_report_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富现金流量表查询失败")
                logger.error(f"[股票Unity服务] 东方财富现金流量表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 东方财富现金流量表查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"东方财富现金流量表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_profit_forecast_ths(symbol: str, indicator: str) -> Dict[str, Any]:
        """
        查询同花顺盈利预测数据
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            indicator: 预测类型，choice of {"预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", "业绩预测详表-详细指标预测"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺盈利预测数据 symbol={symbol}, indicator={indicator}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_profit_forecast_ths(normalized_symbol, indicator)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺盈利预测查询失败")
                logger.error(f"[股票Unity服务] 同花顺盈利预测查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 同花顺盈利预测查询成功 symbol={normalized_symbol}, indicator={indicator}")
            return result
            
        except Exception as e:
            error_msg = f"同花顺盈利预测查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 股东数据模块 (holder/)
    # ============================================================================
    
    @staticmethod
    def get_stock_account_statistics_em() -> Dict[str, Any]:
        """
        查询月度股票账户统计数据（201504 起全量）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询月度股票账户统计数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_account_statistics_em()
            
            if not result.get("success", False):
                error_msg = result.get("error", "月度股票账户统计查询失败")
                logger.error(f"[股票Unity服务] 月度股票账户统计查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "account_statistics"}
            
            logger.info(f"[股票Unity服务] 月度股票账户统计查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"月度股票账户统计查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "account_statistics"}
    
    @staticmethod
    def get_stock_comment_em() -> Dict[str, Any]:
        """
        查询千股千评数据（全部股票当日评分）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询千股千评数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_comment_em()
            
            if not result.get("success", False):
                error_msg = result.get("error", "千股千评数据查询失败")
                logger.error(f"[股票Unity服务] 千股千评数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "stock_comment"}
            
            logger.info(f"[股票Unity服务] 千股千评数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"千股千评数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "stock_comment"}
    
    @staticmethod
    def get_stock_comment_detail_scrd_focus_em(symbol: str) -> Dict[str, Any]:
        """
        查询千股千评-用户关注指数
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询千股千评用户关注指数 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_comment_detail_scrd_focus_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "千股千评用户关注指数查询失败")
                logger.error(f"[股票Unity服务] 千股千评用户关注指数查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 千股千评用户关注指数查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"千股千评用户关注指数查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_comment_detail_scrd_desire_em(symbol: str) -> Dict[str, Any]:
        """
        查询千股千评-市场参与意愿
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询千股千评市场参与意愿 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_comment_detail_scrd_desire_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "千股千评市场参与意愿查询失败")
                logger.error(f"[股票Unity服务] 千股千评市场参与意愿查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 千股千评市场参与意愿查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"千股千评市场参与意愿查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_zh_a_gdhs(date: str) -> Dict[str, Any]:
        """
        查询全市场股东户数数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询全市场股东户数数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zh_a_gdhs(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "全市场股东户数查询失败")
                logger.error(f"[股票Unity服务] 全市场股东户数查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "gdhs"}
            
            logger.info(f"[股票Unity服务] 全市场股东户数查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"全市场股东户数查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "gdhs"}
    
    @staticmethod
    def get_stock_zh_a_gdhs_detail_em(symbol: str) -> Dict[str, Any]:
        """
        查询个股股东户数详情
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询个股股东户数详情 symbol={symbol}")
        
        try:
            # 标准化股票代码
            normalized_symbol = StockUnityService._normalize_symbol(symbol)
            
            # 调用底层unity接口
            result = get_stock_zh_a_gdhs_detail_em(normalized_symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "个股股东户数详情查询失败")
                logger.error(f"[股票Unity服务] 个股股东户数详情查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": normalized_symbol}
            
            logger.info(f"[股票Unity服务] 个股股东户数详情查询成功 symbol={normalized_symbol}")
            return result
            
        except Exception as e:
            error_msg = f"个股股东户数详情查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 龙虎榜模块 (lhb/)
    # ============================================================================
    
    @staticmethod
    def get_stock_lhb_jgmmtj_em(start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询龙虎榜机构买卖每日统计
        
        Args:
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询龙虎榜机构买卖统计 start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_lhb_jgmmtj_em(start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "龙虎榜机构买卖统计查询失败")
                logger.error(f"[股票Unity服务] 龙虎榜机构买卖统计查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "jgmmtj"}
            
            logger.info(f"[股票Unity服务] 龙虎榜机构买卖统计查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"龙虎榜机构买卖统计查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "jgmmtj"}
    
    @staticmethod
    def get_stock_lhb_detail_em(start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询龙虎榜详情数据
        
        Args:
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询龙虎榜详情 start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_lhb_detail_em(start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "龙虎榜详情查询失败")
                logger.error(f"[股票Unity服务] 龙虎榜详情查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_detail"}
            
            logger.info(f"[股票Unity服务] 龙虎榜详情查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"龙虎榜详情查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_detail"}
    
    @staticmethod
    def get_stock_lhb_stock_statistic_em(symbol: str) -> Dict[str, Any]:
        """
        查询个股上榜统计数据
        
        Args:
            symbol: 时间范围，choice of {"近一月", "近三月", "近六月", "近一年"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询个股上榜统计 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_lhb_stock_statistic_em(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "个股上榜统计查询失败")
                logger.error(f"[股票Unity服务] 个股上榜统计查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_stock_statistic"}
            
            logger.info(f"[股票Unity服务] 个股上榜统计查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"个股上榜统计查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_stock_statistic"}
    
    @staticmethod
    def get_stock_lhb_hyyyb_em(start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询每日活跃营业部数据
        
        Args:
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询每日活跃营业部数据 start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_lhb_hyyyb_em(start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "每日活跃营业部查询失败")
                logger.error(f"[股票Unity服务] 每日活跃营业部查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_hyyyb"}
            
            logger.info(f"[股票Unity服务] 每日活跃营业部查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"每日活跃营业部查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "lhb_hyyyb"}
    
    @staticmethod
    def get_stock_lhb_yyb_detail_em(symbol: str) -> Dict[str, Any]:
        """
        查询营业部历史交易明细
        
        Args:
            symbol: 营业部代码，如 "10026729"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询营业部历史交易明细 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_lhb_yyb_detail_em(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "营业部历史交易明细查询失败")
                logger.error(f"[股票Unity服务] 营业部历史交易明细查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 营业部历史交易明细查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"营业部历史交易明细查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 融资融券模块 (margin/)
    # ============================================================================
    
    @staticmethod
    def get_stock_margin_account_info() -> Dict[str, Any]:
        """
        查询两融账户信息（东方财富）
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询两融账户信息")
        
        try:
            # 调用底层unity接口
            result = get_stock_margin_account_info()
            
            if not result.get("success", False):
                error_msg = result.get("error", "两融账户信息查询失败")
                logger.error(f"[股票Unity服务] 两融账户信息查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "margin_account"}
            
            logger.info(f"[股票Unity服务] 两融账户信息查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"两融账户信息查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_account"}
    
    @staticmethod
    def get_stock_margin_sse(start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询上交所融资融券汇总数据
        
        Args:
            start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询上交所融资融券汇总数据 start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_margin_sse(start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "上交所融资融券汇总查询失败")
                logger.error(f"[股票Unity服务] 上交所融资融券汇总查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "margin_sse"}
            
            logger.info(f"[股票Unity服务] 上交所融资融券汇总查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"上交所融资融券汇总查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_sse"}
    
    @staticmethod
    def get_stock_margin_detail_szse(date: str) -> Dict[str, Any]:
        """
        查询深交所融资融券明细数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询深交所融资融券明细数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_margin_detail_szse(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "深交所融资融券明细查询失败")
                logger.error(f"[股票Unity服务] 深交所融资融券明细查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_szse"}
            
            logger.info(f"[股票Unity服务] 深交所融资融券明细查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"深交所融资融券明细查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_szse"}
    
    @staticmethod
    def get_stock_margin_detail_sse(date: str) -> Dict[str, Any]:
        """
        查询上交所融资融券明细数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询上交所融资融券明细数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_margin_detail_sse(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "上交所融资融券明细查询失败")
                logger.error(f"[股票Unity服务] 上交所融资融券明细查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_sse"}
            
            logger.info(f"[股票Unity服务] 上交所融资融券明细查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"上交所融资融券明细查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "margin_detail_sse"}
    
    # ============================================================================
    # 板块概念模块 (board/)
    # ============================================================================
    
    @staticmethod
    def get_stock_board_concept_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块指数日频率数据
        
        Args:
            symbol: 概念板块名称，如 "阿里巴巴概念"
            start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺概念板块指数 symbol={symbol}, start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_board_concept_index_ths(symbol, start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺概念板块指数查询失败")
                logger.error(f"[股票Unity服务] 同花顺概念板块指数查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺概念板块指数查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺概念板块指数查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_board_industry_summary_ths() -> Dict[str, Any]:
        """
        查询同花顺行业一览表
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺行业一览表")
        
        try:
            # 调用底层unity接口
            result = get_stock_board_industry_summary_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺行业一览表查询失败")
                logger.error(f"[股票Unity服务] 同花顺行业一览表查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}
            
            logger.info(f"[股票Unity服务] 同花顺行业一览表查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺行业一览表查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "industry_summary"}
    
    @staticmethod
    def get_stock_board_concept_info_ths(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺概念板块简介
        
        Args:
            symbol: 概念板块名称，如 "阿里巴巴概念"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺概念板块简介 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_board_concept_info_ths(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺概念板块简介查询失败")
                logger.error(f"[股票Unity服务] 同花顺概念板块简介查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺概念板块简介查询成功")
            return result
            
        except Exception as e:
            error_msg = f"同花顺概念板块简介查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_board_industry_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        查询同花顺行业板块指数日频率数据
        
        Args:
            symbol: 行业板块名称，如 "元件"
            start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺行业板块指数 symbol={symbol}, start_date={start_date}, end_date={end_date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_board_industry_index_ths(symbol, start_date, end_date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺行业板块指数查询失败")
                logger.error(f"[股票Unity服务] 同花顺行业板块指数查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺行业板块指数查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺行业板块指数查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_hot_follow_xq(symbol: str) -> Dict[str, Any]:
        """
        查询雪球关注排行榜
        
        Args:
            symbol: 排行榜类型，choice of {"本周新增", "最热门"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询雪球关注排行榜 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_hot_follow_xq(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "雪球关注排行榜查询失败")
                logger.error(f"[股票Unity服务] 雪球关注排行榜查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 雪球关注排行榜查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"雪球关注排行榜查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_hot_rank_detail_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富股票热度历史趋势及粉丝特征
        
        Args:
            symbol: 股票代码，如 "SZ000665"（需带市场前缀）
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富股票热度 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_hot_rank_detail_em(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富股票热度查询失败")
                logger.error(f"[股票Unity服务] 东方财富股票热度查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 东方财富股票热度查询成功")
            return result
            
        except Exception as e:
            error_msg = f"东方财富股票热度查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_hot_keyword_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富个股人气榜热门关键词
        
        Args:
            symbol: 股票代码，如 "SZ000665"（需带市场前缀）
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富个股人气榜热门关键词 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_hot_keyword_em(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富个股人气榜热门关键词查询失败")
                logger.error(f"[股票Unity服务] 东方财富个股人气榜热门关键词查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 东方财富个股人气榜热门关键词查询成功")
            return result
            
        except Exception as e:
            error_msg = f"东方财富个股人气榜热门关键词查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_changes_em(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富盘口异动数据
        
        Args:
            symbol: 异动类型，choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富盘口异动数据 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_changes_em(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富盘口异动查询失败")
                logger.error(f"[股票Unity服务] 东方财富盘口异动查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 东方财富盘口异动查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富盘口异动查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_board_change_em() -> Dict[str, Any]:
        """
        查询东方财富当日板块异动详情
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富当日板块异动详情")
        
        try:
            # 调用底层unity接口
            result = get_stock_board_change_em()
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富当日板块异动查询失败")
                logger.error(f"[股票Unity服务] 东方财富当日板块异动查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}
            
            logger.info(f"[股票Unity服务] 东方财富当日板块异动查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富当日板块异动查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "board_change"}
    
    # ============================================================================
    # 涨跌停模块 (zt/)
    # ============================================================================
    
    @staticmethod
    def get_stock_zt_pool_em(date: str) -> Dict[str, Any]:
        """
        查询东方财富涨停股池数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富涨停股池数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zt_pool_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富涨停股池查询失败")
                logger.error(f"[股票Unity服务] 东方财富涨停股池查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool"}
            
            logger.info(f"[股票Unity服务] 东方财富涨停股池查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富涨停股池查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool"}
    
    @staticmethod
    def get_stock_zt_pool_previous_em(date: str) -> Dict[str, Any]:
        """
        查询东方财富昨日涨停股池数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富昨日涨停股池数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zt_pool_previous_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富昨日涨停股池查询失败")
                logger.error(f"[股票Unity服务] 东方财富昨日涨停股池查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_previous"}
            
            logger.info(f"[股票Unity服务] 东方财富昨日涨停股池查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富昨日涨停股池查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_previous"}
    
    @staticmethod
    def get_stock_zt_pool_strong_em(date: str) -> Dict[str, Any]:
        """
        查询东方财富强势股池数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富强势股池数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zt_pool_strong_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富强势股池查询失败")
                logger.error(f"[股票Unity服务] 东方财富强势股池查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_strong"}
            
            logger.info(f"[股票Unity服务] 东方财富强势股池查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富强势股池查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_strong"}
    
    @staticmethod
    def get_stock_zt_pool_zbgc_em(date: str) -> Dict[str, Any]:
        """
        查询东方财富炸板股池数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富炸板股池数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zt_pool_zbgc_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富炸板股池查询失败")
                logger.error(f"[股票Unity服务] 东方财富炸板股池查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_zbgc"}
            
            logger.info(f"[股票Unity服务] 东方财富炸板股池查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富炸板股池查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_zbgc"}
    
    @staticmethod
    def get_stock_zt_pool_dtgc_em(date: str) -> Dict[str, Any]:
        """
        查询东方财富跌停股池数据
        
        Args:
            date: 日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富跌停股池数据 date={date}")
        
        try:
            # 调用底层unity接口
            result = get_stock_zt_pool_dtgc_em(date)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富跌停股池查询失败")
                logger.error(f"[股票Unity服务] 东方财富跌停股池查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_dtgc"}
            
            logger.info(f"[股票Unity服务] 东方财富跌停股池查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富跌停股池查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "zt_pool_dtgc"}
    
    # ============================================================================
    # 技术选股排名模块 (rank/)
    # ============================================================================
    
    @staticmethod
    def get_stock_rank_cxg_ths(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺技术指标-创新高数据
        
        Args:
            symbol: 创新高类型，choice of {"创月新高", "半年新高", "一年新高", "历史新高"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺创新高数据 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_cxg_ths(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺创新高数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺创新高数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺创新高数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺创新高数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_rank_lxsz_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-连续上涨数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺连续上涨数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_lxsz_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺连续上涨数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺连续上涨数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "lxsz"}
            
            logger.info(f"[股票Unity服务] 同花顺连续上涨数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺连续上涨数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "lxsz"}
    
    @staticmethod
    def get_stock_rank_cxfl_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-持续放量数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺持续放量数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_cxfl_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺持续放量数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺持续放量数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "cxfl"}
            
            logger.info(f"[股票Unity服务] 同花顺持续放量数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺持续放量数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "cxfl"}
    
    @staticmethod
    def get_stock_rank_cxsl_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-持续缩量数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺持续缩量数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_cxsl_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺持续缩量数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺持续缩量数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "cxsl"}
            
            logger.info(f"[股票Unity服务] 同花顺持续缩量数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺持续缩量数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "cxsl"}
    
    @staticmethod
    def get_stock_rank_xstp_ths(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺技术选股-向上突破数据
        
        Args:
            symbol: 均线类型，choice of {"5日均线", "10日均线", "20日均线", "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺向上突破数据 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_xstp_ths(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺向上突破数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺向上突破数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺向上突破数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺向上突破数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_rank_ljqs_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-量价齐升数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺量价齐升数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_ljqs_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺量价齐升数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺量价齐升数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "ljqs"}
            
            logger.info(f"[股票Unity服务] 同花顺量价齐升数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺量价齐升数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "ljqs"}
    
    @staticmethod
    def get_stock_rank_ljqd_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-量价齐跌数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺量价齐跌数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_ljqd_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺量价齐跌数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺量价齐跌数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "ljqd"}
            
            logger.info(f"[股票Unity服务] 同花顺量价齐跌数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺量价齐跌数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "ljqd"}
    
    @staticmethod
    def get_stock_rank_xzjp_ths() -> Dict[str, Any]:
        """
        查询同花顺技术选股-险资举牌数据
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺险资举牌数据")
        
        try:
            # 调用底层unity接口
            result = get_stock_rank_xzjp_ths()
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺险资举牌数据查询失败")
                logger.error(f"[股票Unity服务] 同花顺险资举牌数据查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "xzjp"}
            
            logger.info(f"[股票Unity服务] 同花顺险资举牌数据查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺险资举牌数据查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "xzjp"}
    
    # ============================================================================
    # 资金流向模块 (fund_flow/)
    # ============================================================================
    
    @staticmethod
    def get_stock_fund_flow_individual(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺-数据中心-资金流向-个股资金流
        
        Args:
            symbol: 时间范围，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺个股资金流 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_fund_flow_individual(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺个股资金流查询失败")
                logger.error(f"[股票Unity服务] 同花顺个股资金流查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺个股资金流查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺个股资金流查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_fund_flow_concept(symbol: str) -> Dict[str, Any]:
        """
        查询同花顺-数据中心-资金流向-概念资金流
        
        Args:
            symbol: 时间范围，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询同花顺概念资金流 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_fund_flow_concept(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "同花顺概念资金流查询失败")
                logger.error(f"[股票Unity服务] 同花顺概念资金流查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 同花顺概念资金流查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"同花顺概念资金流查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_individual_fund_flow(stock: str, market: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-个股资金流向（近100交易日）
        
        Args:
            stock: 股票代码，如 "000425"
            market: 市场类型，choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富个股资金流向 stock={stock}, market={market}")
        
        try:
            # 调用底层unity接口
            result = get_stock_individual_fund_flow(stock, market)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富个股资金流向查询失败")
                logger.error(f"[股票Unity服务] 东方财富个股资金流向查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": stock}
            
            logger.info(f"[股票Unity服务] 东方财富个股资金流向查询成功")
            return result
            
        except Exception as e:
            error_msg = f"东方财富个股资金流向查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": stock}
    
    @staticmethod
    def get_stock_individual_fund_flow_rank(indicator: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-资金流向排名
        
        Args:
            indicator: 时间范围，choice of {"今日", "3日", "5日", "10日"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富资金流向排名 indicator={indicator}")
        
        try:
            # 调用底层unity接口
            result = get_stock_individual_fund_flow_rank(indicator)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富资金流向排名查询失败")
                logger.error(f"[股票Unity服务] 东方财富资金流向排名查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": indicator}
            
            logger.info(f"[股票Unity服务] 东方财富资金流向排名查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富资金流向排名查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": indicator}
    
    @staticmethod
    def get_stock_market_fund_flow() -> Dict[str, Any]:
        """
        查询东方财富-数据中心-大盘资金流向
        
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富大盘资金流向")
        
        try:
            # 调用底层unity接口
            result = get_stock_market_fund_flow()
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富大盘资金流向查询失败")
                logger.error(f"[股票Unity服务] 东方财富大盘资金流向查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": "market_fund_flow"}
            
            logger.info(f"[股票Unity服务] 东方财富大盘资金流向查询成功")
            return result
            
        except Exception as e:
            error_msg = f"东方财富大盘资金流向查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": "market_fund_flow"}
    
    @staticmethod
    def get_stock_sector_fund_flow_rank(indicator: str, sector_type: str) -> Dict[str, Any]:
        """
        查询东方财富+数据中心+板块资金流排名
        
        Args:
            indicator: 时间范围，choice of {"今日", "5日", "10日"}
            sector_type: 板块类型，choice of {"行业资金流", "概念资金流", "地域资金流"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富板块资金流排名 indicator={indicator}, sector_type={sector_type}")
        
        try:
            # 调用底层unity接口
            result = get_stock_sector_fund_flow_rank(indicator, sector_type)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富板块资金流排名查询失败")
                logger.error(f"[股票Unity服务] 东方财富板块资金流排名查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": f"{indicator}_{sector_type}"}
            
            logger.info(f"[股票Unity服务] 东方财富板块资金流排名查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富板块资金流排名查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": f"{indicator}_{sector_type}"}
    
    @staticmethod
    def get_stock_sector_fund_flow_summary(symbol: str, indicator: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-行业个股资金流
        
        Args:
            symbol: 行业板块名称，如 "电源设备"
            indicator: 时间范围，choice of {"今日", "5日", "10日"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富行业个股资金流 symbol={symbol}, indicator={indicator}")
        
        try:
            # 调用底层unity接口
            result = get_stock_sector_fund_flow_summary(symbol, indicator)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富行业个股资金流查询失败")
                logger.error(f"[股票Unity服务] 东方财富行业个股资金流查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 东方财富行业个股资金流查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富行业个股资金流查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    @staticmethod
    def get_stock_main_fund_flow(symbol: str) -> Dict[str, Any]:
        """
        查询东方财富-数据中心-主力净流入排名
        
        Args:
            symbol: 市场类型，choice of {"全部股票", "沪深A股", "沪市A股", "科创板", "深市A股", "创业板", "沪市B股", "深市B股"}
            
        Returns:
            统一格式的响应数据
        """
        logger.info(f"[股票Unity服务] 开始查询东方财富主力净流入排名 symbol={symbol}")
        
        try:
            # 调用底层unity接口
            result = get_stock_main_fund_flow(symbol)
            
            if not result.get("success", False):
                error_msg = result.get("error", "东方财富主力净流入排名查询失败")
                logger.error(f"[股票Unity服务] 东方财富主力净流入排名查询失败: {error_msg}")
                return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
            
            logger.info(f"[股票Unity服务] 东方财富主力净流入排名查询成功，共 {len(result.get('data', []))} 条记录")
            return result
            
        except Exception as e:
            error_msg = f"东方财富主力净流入排名查询失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            return {"success": False, "data": None, "error": error_msg, "symbol": symbol}
    
    # ============================================================================
    # 批量查询接口
    # ============================================================================
    
    @staticmethod
    def get_all_basic_info() -> Dict[str, Any]:
        """
        批量获取所有基本信息
        
        Returns:
            统一格式的响应数据，包含所有基本信息
        """
        logger.info(f"[股票Unity服务] 开始批量获取所有基本信息")
        
        try:
            # 并行查询所有基本信息
            all_stocks_result = StockUnityService.get_all_stock_codes()
            sh_stocks_result = StockUnityService.stock_info_sh_name_code()
            sz_stocks_result = StockUnityService.stock_info_sz_name_code()
            bj_stocks_result = StockUnityService.stock_info_bj_name_code()
            
            # 构建综合响应
            combined_data = {
                "all_stocks": all_stocks_result.get("data", []),
                "sh_stocks": sh_stocks_result.get("data", []),
                "sz_stocks": sz_stocks_result.get("data", []),
                "bj_stocks": bj_stocks_result.get("data", []),
                "all_stocks_success": all_stocks_result["success"],
                "sh_stocks_success": sh_stocks_result["success"],
                "sz_stocks_success": sz_stocks_result["success"],
                "bj_stocks_success": bj_stocks_result["success"]
            }
            
            # 检查是否有失败的查询
            all_success = (
                all_stocks_result["success"] and 
                sh_stocks_result["success"] and 
                sz_stocks_result["success"] and 
                bj_stocks_result["success"]
            )
            
            if all_success:
                logger.info(f"[股票Unity服务] 批量获取所有基本信息成功")
                return {
                    "success": True,
                    "data": combined_data,
                    "error": None,
                    "symbol": "all_basic_info"
                }
            else:
                # 部分成功，收集错误信息
                errors = []
                if not all_stocks_result["success"]:
                    errors.append(f"全市场股票: {all_stocks_result.get('error', '未知错误')}")
                if not sh_stocks_result["success"]:
                    errors.append(f"上交所股票: {sh_stocks_result.get('error', '未知错误')}")
                if not sz_stocks_result["success"]:
                    errors.append(f"深交所股票: {sz_stocks_result.get('error', '未知错误')}")
                if not bj_stocks_result["success"]:
                    errors.append(f"北交所股票: {bj_stocks_result.get('error', '未知错误')}")
                
                error_msg = "部分查询失败: " + "; ".join(errors)
                logger.warning(f"[股票Unity服务] 批量获取所有基本信息部分失败: {error_msg}")
                
                return {
                    "success": False,
                    "data": combined_data,
                    "error": error_msg,
                    "symbol": "all_basic_info"
                }
                
        except Exception as e:
            error_msg = f"批量获取所有基本信息失败: {str(e)}"
            logger.error(f"[股票Unity服务] {error_msg}")
            logger.debug(traceback.format_exc())
            
            return {
                "success": False,
                "data": None,
                "error": error_msg,
                "symbol": "all_basic_info"
            }


# 创建全局服务实例，方便直接使用
unity_service = StockUnityService()


if __name__ == "__main__":
    """
    股票Unity服务模块测试代码
    
    运行此模块可以测试所有股票Unity接口的功能。
    注意：测试时需要确保akshare库已正确安装，并且网络连接正常。
    """
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("股票Unity服务模块测试")
    print("=" * 80)
    
    try:
        # 测试股票基本信息
        print("\n1. 测试股票基本信息查询...")
        result = unity_service.get_stock_info("000001")
        print(f"   成功: {result['success']}")
        print(f"   数据条数: {len(result.get('data', []))}")
        print(f"   错误: {result.get('error', '无')}")
        
        # 测试全市场股票代码
        print("\n2. 测试全市场股票代码查询...")
        result = unity_service.get_all_stock_codes()
        print(f"   成功: {result['success']}")
        print(f"   数据条数: {len(result.get('data', []))}")
        print(f"   错误: {result.get('error', '无')}")
        
        # 测试股权质押概况
        print("\n3. 测试股权质押概况查询...")
        result = unity_service.get_stock_gpzy_profile_em()
        print(f"   成功: {result['success']}")
        print(f"   数据条数: {len(result.get('data', []))}")
        print(f"   错误: {result.get('error', '无')}")
        
        # 测试批量查询
        print("\n4. 测试批量查询所有基本信息...")
        result = unity_service.get_all_basic_info()
        print(f"   成功: {result['success']}")
        if result["success"] and result["data"]:
            data = result["data"]
            print(f"   全市场股票条数: {len(data.get('all_stocks', []))}")
            print(f"   上交所股票条数: {len(data.get('sh_stocks', []))}")
            print(f"   深交所股票条数: {len(data.get('sz_stocks', []))}")
            print(f"   北交所股票条数: {len(data.get('bj_stocks', []))}")
        print(f"   错误: {result.get('error', '无')}")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)