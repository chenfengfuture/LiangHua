# Unity服务模块统一入口
"""
股票Unity服务模块 - 统一入口

本模块提供所有股票相关数据的服务层封装，
按照模块分类组织，提供统一的错误处理和响应格式。
"""

# 导入所有模块的服务函数
from .basic_service import unity_service

from .pledge_service import (
    get_stock_gpzy_profile_em_service,
    get_stock_gpzy_pledge_ratio_em_service,
    get_stock_gpzy_individual_pledge_ratio_detail_em_service,
    get_stock_gpzy_industry_data_em_service,
)

from .financial_service import (
    get_stock_financial_report_sina_service,
    get_stock_balance_sheet_by_yearly_em_service,
    get_stock_profit_sheet_by_report_em_service,
    get_stock_profit_sheet_by_yearly_em_service,
    get_stock_cash_flow_sheet_by_report_em_service,
    get_stock_profit_forecast_ths_service,
)

from .holder_service import (
    get_stock_account_statistics_em_service,
    get_stock_comment_em_service,
    get_stock_comment_detail_scrd_focus_em_service,
    get_stock_comment_detail_scrd_desire_em_service,
    get_stock_zh_a_gdhs_service,
    get_stock_zh_a_gdhs_detail_em_service,
)

from .lhb_service import (
    get_stock_lhb_jgmmtj_em_service,
    get_stock_lhb_detail_em_service,
    get_stock_lhb_stock_statistic_em_service,
    get_stock_lhb_hyyyb_em_service,
    get_stock_lhb_yyb_detail_em_service,
)

from .margin_service import (
    get_stock_margin_account_info_service,
    get_stock_margin_sse_service,
    get_stock_margin_detail_szse_service,
    get_stock_margin_detail_sse_service,
)

from .board_service import (
    get_stock_board_concept_index_ths_service,
    get_stock_board_industry_summary_ths_service,
    get_stock_board_concept_info_ths_service,
    get_stock_board_industry_index_ths_service,
    get_stock_hot_follow_xq_service,
    get_stock_hot_rank_detail_em_service,
    get_stock_hot_keyword_em_service,
    get_stock_changes_em_service,
    get_stock_board_change_em_service,
)

from .zt_service import (
    get_stock_zt_pool_em_service,
    get_stock_zt_pool_previous_em_service,
    get_stock_zt_pool_strong_em_service,
    get_stock_zt_pool_zbgc_em_service,
    get_stock_zt_pool_dtgc_em_service,
)

from .rank_service import (
    get_stock_rank_cxg_ths_service,
    get_stock_rank_lxsz_ths_service,
    get_stock_rank_cxfl_ths_service,
    get_stock_rank_cxsl_ths_service,
    get_stock_rank_xstp_ths_service,
    get_stock_rank_ljqs_ths_service,
    get_stock_rank_ljqd_ths_service,
    get_stock_rank_xzjp_ths_service,
)

from .fund_flow_service import (
    get_stock_fund_flow_individual_service,
    get_stock_fund_flow_concept_service,
    get_stock_individual_fund_flow_service,
    get_stock_individual_fund_flow_rank_service,
    get_stock_market_fund_flow_service,
    get_stock_sector_fund_flow_rank_service,
    get_stock_sector_fund_flow_summary_service,
    get_stock_main_fund_flow_service,
)

# 导出所有服务函数
__all__ = [
    # basic模块
    "unity_service",
    
    # pledge模块
    "get_stock_gpzy_profile_em_service",
    "get_stock_gpzy_pledge_ratio_em_service",
    "get_stock_gpzy_individual_pledge_ratio_detail_em_service",
    "get_stock_gpzy_industry_data_em_service",
    
    # financial模块
    "get_stock_financial_report_sina_service",
    "get_stock_balance_sheet_by_yearly_em_service",
    "get_stock_profit_sheet_by_report_em_service",
    "get_stock_profit_sheet_by_yearly_em_service",
    "get_stock_cash_flow_sheet_by_report_em_service",
    "get_stock_profit_forecast_ths_service",
    
    # holder模块
    "get_stock_account_statistics_em_service",
    "get_stock_comment_em_service",
    "get_stock_comment_detail_scrd_focus_em_service",
    "get_stock_comment_detail_scrd_desire_em_service",
    "get_stock_zh_a_gdhs_service",
    "get_stock_zh_a_gdhs_detail_em_service",
    
    # lhb模块
    "get_stock_lhb_jgmmtj_em_service",
    "get_stock_lhb_detail_em_service",
    "get_stock_lhb_stock_statistic_em_service",
    "get_stock_lhb_hyyyb_em_service",
    "get_stock_lhb_yyb_detail_em_service",
    
    # margin模块
    "get_stock_margin_account_info_service",
    "get_stock_margin_sse_service",
    "get_stock_margin_detail_szse_service",
    "get_stock_margin_detail_sse_service",
    
    # board模块
    "get_stock_board_concept_index_ths_service",
    "get_stock_board_industry_summary_ths_service",
    "get_stock_board_concept_info_ths_service",
    "get_stock_board_industry_index_ths_service",
    "get_stock_hot_follow_xq_service",
    "get_stock_hot_rank_detail_em_service",
    "get_stock_hot_keyword_em_service",
    "get_stock_changes_em_service",
    "get_stock_board_change_em_service",
    
    # zt模块
    "get_stock_zt_pool_em_service",
    "get_stock_zt_pool_previous_em_service",
    "get_stock_zt_pool_strong_em_service",
    "get_stock_zt_pool_zbgc_em_service",
    "get_stock_zt_pool_dtgc_em_service",
    
    # rank模块
    "get_stock_rank_cxg_ths_service",
    "get_stock_rank_lxsz_ths_service",
    "get_stock_rank_cxfl_ths_service",
    "get_stock_rank_cxsl_ths_service",
    "get_stock_rank_xstp_ths_service",
    "get_stock_rank_ljqs_ths_service",
    "get_stock_rank_ljqd_ths_service",
    "get_stock_rank_xzjp_ths_service",
    
    # fund_flow模块
    "get_stock_fund_flow_individual_service",
    "get_stock_fund_flow_concept_service",
    "get_stock_individual_fund_flow_service",
    "get_stock_individual_fund_flow_rank_service",
    "get_stock_market_fund_flow_service",
    "get_stock_sector_fund_flow_rank_service",
    "get_stock_sector_fund_flow_summary_service",
    "get_stock_main_fund_flow_service",
]