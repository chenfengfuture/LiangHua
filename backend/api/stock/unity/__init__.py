# -*- coding: utf-8 -*-
"""
Stock Unity 模块 - 股票数据统一接口

本模块将所有股票相关接口按照业务分类组织成独立的子模块，
保持接口函数名、输入参数、输出格式完全不变。

模块结构：
- basic: 股票基本信息
- pledge: 股权质押
- financial: 财务报表
- holder: 股东数据
- lhb: 龙虎榜
- fund_flow: 资金流向
- margin: 融资融券
- board: 板块概念
- zt: 涨跌停
- rank: 技术选股排名

使用示例：
    from api.stock.unity import get_stock_info
    result = get_stock_info("000001")
"""

# ============================================================================
# 全局 AKShare 配置 - 请求延时 + 随机UA + 超时设置
# ============================================================================
import random
import time
import logging
import requests

# 配置日志
_logger = logging.getLogger(__name__)

# 常用 User-Agent 列表
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _get_random_ua():
    """获取随机 User-Agent"""
    return random.choice(_USER_AGENTS)

def _init_akshare_global_config():
    """
    初始化 AKShare 全局配置：
    1. 随机 User-Agent（随机切换请求头）
    2. 15秒超时
    3. 全局请求钩子（3~5秒延时）
    """
    try:
        from akshare.request import requests as ak_requests
        
        # 获取 Session 类
        SessionClass = ak_requests.Session
        
        # 保存原始方法
        _original_session_init = SessionClass.__init__
        _original_get = SessionClass.get
        
        # 1. 设置随机 UA - patch Session.__init__
        def _patched_session_init(self, *args, **kwargs):
            """为每个 Session 实例设置随机 UA"""
            _original_session_init(self, *args, **kwargs)
            self.headers['User-Agent'] = _get_random_ua()
        
        # 2. 全局请求钩子 - patch Session.get (延时 + 超时)
        _DEFAULT_TIMEOUT = 15  # 默认超时 15 秒
        
        def _patched_get(self, url, **kwargs):
            """全局请求钩子：在每个请求前强制等待 3~5 秒"""
            # 强制添加 15 秒超时
            if 'timeout' not in kwargs:
                kwargs['timeout'] = _DEFAULT_TIMEOUT
            
            # 强制延时 3~5 秒
            delay = random.uniform(3, 5)
            time.sleep(delay)
            
            return _original_get(self, url, **kwargs)
        
        # 应用补丁
        SessionClass.__init__ = _patched_session_init
        SessionClass.get = _patched_get
        
        _logger.info("[AKShare 全局] 已启用随机UA + 3~5秒请求延时 + 15秒超时")
        
    except ImportError as e:
        _logger.warning(f"[AKShare 全局] 缺少依赖: {e}")
    except Exception as e:
        _logger.warning(f"[AKShare 全局] 配置失败: {e}")

# 模块加载时自动执行全局配置
_init_akshare_global_config()

# ============================================================================
# 导出所有业务模块接口
# ============================================================================
from .basic import (
    get_stock_info,
    get_stock_info_json,
    get_stock_individual_basic_info_xq,
)

from .pledge import (
    get_stock_gpzy_profile_em,
    get_stock_gpzy_pledge_ratio_em,
    get_stock_gpzy_individual_pledge_ratio_detail_em,
    get_stock_gpzy_industry_data_em,
)

from .financial import (
    get_stock_financial_report_sina,
    get_stock_balance_sheet_by_yearly_em,
    get_stock_profit_sheet_by_report_em,
    get_stock_profit_sheet_by_yearly_em,
    get_stock_cash_flow_sheet_by_report_em,
    get_stock_profit_forecast_ths,
)

from .holder import (
    get_stock_account_statistics_em,
    get_stock_comment_em,
    get_stock_comment_detail_scrd_focus_em,
    get_stock_comment_detail_scrd_desire_em,
    get_stock_zh_a_gdhs,
    get_stock_zh_a_gdhs_detail_em,
)

from .lhb import (
    get_stock_lhb_jgmmtj_em,
    get_stock_lhb_detail_em,
    get_stock_lhb_stock_statistic_em,
    get_stock_lhb_hyyyb_em,
    get_stock_lhb_yyb_detail_em,
)

from .fund_flow import (
    get_stock_fund_flow_individual,
    get_stock_fund_flow_concept,
    get_stock_individual_fund_flow,
    get_stock_individual_fund_flow_rank,
    get_stock_market_fund_flow,
    get_stock_sector_fund_flow_rank,
    get_stock_sector_fund_flow_summary,
    get_stock_main_fund_flow,
)

from .margin import (
    get_stock_margin_account_info,
    get_stock_margin_sse,
    get_stock_margin_detail_szse,
    get_stock_margin_detail_sse,
)

from .board import (
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

from .zt import (
    get_stock_zt_pool_em,
    get_stock_zt_pool_previous_em,
    get_stock_zt_pool_strong_em,
    get_stock_zt_pool_zbgc_em,
    get_stock_zt_pool_dtgc_em,
)

from .rank import (
    get_stock_rank_cxg_ths,
    get_stock_rank_lxsz_ths,
    get_stock_rank_cxfl_ths,
    get_stock_rank_cxsl_ths,
    get_stock_rank_xstp_ths,
    get_stock_rank_ljqs_ths,
    get_stock_rank_ljqd_ths,
    get_stock_rank_xzjp_ths,
)

__all__ = [
    # basic
    "get_stock_info",
    "get_stock_info_json",
    "get_stock_individual_basic_info_xq",
    # pledge
    "get_stock_gpzy_profile_em",
    "get_stock_gpzy_pledge_ratio_em",
    "get_stock_gpzy_individual_pledge_ratio_detail_em",
    "get_stock_gpzy_industry_data_em",
    # financial
    "get_stock_financial_report_sina",
    "get_stock_balance_sheet_by_yearly_em",
    "get_stock_profit_sheet_by_report_em",
    "get_stock_profit_sheet_by_yearly_em",
    "get_stock_cash_flow_sheet_by_report_em",
    "get_stock_profit_forecast_ths",
    # holder
    "get_stock_account_statistics_em",
    "get_stock_comment_em",
    "get_stock_comment_detail_scrd_focus_em",
    "get_stock_comment_detail_scrd_desire_em",
    "get_stock_zh_a_gdhs",
    "get_stock_zh_a_gdhs_detail_em",
    # lhb
    "get_stock_lhb_jgmmtj_em",
    "get_stock_lhb_detail_em",
    "get_stock_lhb_stock_statistic_em",
    "get_stock_lhb_hyyyb_em",
    "get_stock_lhb_yyb_detail_em",
    # fund_flow
    "get_stock_fund_flow_individual",
    "get_stock_fund_flow_concept",
    "get_stock_individual_fund_flow",
    "get_stock_individual_fund_flow_rank",
    "get_stock_market_fund_flow",
    "get_stock_sector_fund_flow_rank",
    "get_stock_sector_fund_flow_summary",
    "get_stock_main_fund_flow",
    # margin
    "get_stock_margin_account_info",
    "get_stock_margin_sse",
    "get_stock_margin_detail_szse",
    "get_stock_margin_detail_sse",
    # board
    "get_stock_board_concept_index_ths",
    "get_stock_board_industry_summary_ths",
    "get_stock_board_concept_info_ths",
    "get_stock_board_industry_index_ths",
    "get_stock_hot_follow_xq",
    "get_stock_hot_rank_detail_em",
    "get_stock_hot_keyword_em",
    "get_stock_changes_em",
    "get_stock_board_change_em",
    # zt
    "get_stock_zt_pool_em",
    "get_stock_zt_pool_previous_em",
    "get_stock_zt_pool_strong_em",
    "get_stock_zt_pool_zbgc_em",
    "get_stock_zt_pool_dtgc_em",
    # rank
    "get_stock_rank_cxg_ths",
    "get_stock_rank_lxsz_ths",
    "get_stock_rank_cxfl_ths",
    "get_stock_rank_cxsl_ths",
    "get_stock_rank_xstp_ths",
    "get_stock_rank_ljqs_ths",
    "get_stock_rank_ljqd_ths",
    "get_stock_rank_xzjp_ths",
]
