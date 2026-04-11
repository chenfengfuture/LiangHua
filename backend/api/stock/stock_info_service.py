"""
stock_info_service.py — 东方财富股票数据查询服务

基于 akshare 接口，提供以下查询服务：
设计原则：独立自治、零改动现有代码、异常捕获不崩溃、日志清晰、返回标准JSON。

接口列表：
1. get_stock_info(symbol: str) -> dict
   基于 akshare.stock_individual_info_em 接口，查询个股基础信息。
   返回统一结构：{ "success": bool, "data": dict | None, "error": str | None, "symbol": str }

2. get_stock_gpzy_profile_em() -> dict
   基于 akshare.stock_gpzy_profile_em 接口，查询股权质押市场概况（全量历史）。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "gpzy_profile" }

3. get_stock_gpzy_pledge_ratio_em(date: str) -> dict
   基于 akshare.stock_gpzy_pledge_ratio_em 接口，查询指定交易日上市公司质押比例。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "gpzy_pledge_ratio" }

4. get_stock_gpzy_individual_pledge_ratio_detail_em(symbol: str) -> dict
   基于 akshare.stock_gpzy_individual_pledge_ratio_detail_em 接口，查询个股重要股东股权质押明细（全量历史）。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

5. get_stock_gpzy_industry_data_em() -> dict
   基于 akshare.stock_gpzy_industry_data_em 接口，查询各行业质押比例汇总数据（全量）。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "gpzy_industry" }

6. get_stock_account_statistics_em() -> dict
   基于 akshare.stock_account_statistics_em 接口，查询月度股票账户统计数据（201504 起全量）。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "account_statistics" }

7. get_stock_comment_em() -> dict
   基于 akshare.stock_comment_em 接口，查询千股千评数据（全部股票当日评分）。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "stock_comment" }

8. get_stock_comment_detail_scrd_focus_em(symbol: str) -> dict
   基于 akshare.stock_comment_detail_scrd_focus_em 接口，查询千股千评-用户关注指数。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

9. get_stock_comment_detail_scrd_desire_em(symbol: str) -> dict
   基于 akshare.stock_comment_detail_scrd_desire_em 接口，查询千股千评-市场参与意愿。
   返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

10. get_stock_cyq_em(symbol: str, adjust: str) -> dict
    基于 akshare.stock_cyq_em 接口，查询个股筹码分布数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

11. get_stock_gddh_em() -> dict
    基于 akshare.stock_gddh_em 接口，查询股东大会列表数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "gddh" }

12. get_stock_zdhtmx_em(start_date: str, end_date: str) -> dict
    基于 akshare.stock_zdhtmx_em 接口，查询重大合同明细数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zdht" }

13. get_stock_financial_report_sina(stock: str, symbol: str) -> dict
    基于 akshare.stock_financial_report_sina 接口，查询新浪财经财务报表。
    symbol 参数：choice of {"资产负债表", "利润表", "现金流量表"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

14. get_stock_balance_sheet_by_yearly_em(symbol: str) -> dict
    基于 akshare.stock_balance_sheet_by_yearly_em 接口，查询东方财富资产负债表（按年度）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

15. get_stock_profit_sheet_by_report_em(symbol: str) -> dict
    基于 akshare.stock_profit_sheet_by_report_em 接口，查询东方财富利润表（按报告期）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

16. get_stock_profit_sheet_by_yearly_em(symbol: str) -> dict
    基于 akshare.stock_profit_sheet_by_yearly_em 接口，查询东方财富利润表（按年度）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

17. get_stock_cash_flow_sheet_by_report_em(symbol: str) -> dict
    基于 akshare.stock_cash_flow_sheet_by_report_em 接口，查询东方财富现金流量表（按报告期）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

18. get_stock_gdfx_free_top_10_em(symbol: str, date: str) -> dict
    基于 akshare.stock_gdfx_free_top_10_em 接口，查询个股十大流通股东数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

19. get_stock_zh_a_gdhs(date: str) -> dict
    基于 akshare.stock_zh_a_gdhs 接口，查询全市场股东户数数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "gdhs" }

20. get_stock_zh_a_gdhs_detail_em(symbol: str) -> dict
    基于 akshare.stock_zh_a_gdhs_detail_em 接口，查询个股股东户数详情。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

21. get_stock_lhb_jgmmtj_em(start_date: str, end_date: str) -> dict
    基于 akshare.stock_lhb_jgmmtj_em 接口，查询龙虎榜机构买卖每日统计。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "jgmmtj" }

22. get_stock_lhb_detail_em(start_date: str, end_date: str) -> dict
    基于 akshare.stock_lhb_detail_em 接口，查询龙虎榜详情数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_detail" }

23. get_stock_lhb_stock_statistic_em(symbol: str) -> dict
    基于 akshare.stock_lhb_stock_statistic_em 接口，查询个股上榜统计数据。
    symbol 参数：choice of {"近一月", "近三月", "近六月", "近一年"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_stock_statistic" }

24. get_stock_lhb_hyyyb_em(start_date: str, end_date: str) -> dict
    基于 akshare.stock_lhb_hyyyb_em 接口，查询每日活跃营业部数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_hyyyb" }

25. get_stock_lhb_yyb_detail_em(symbol: str) -> dict
    基于 akshare.stock_lhb_yyb_detail_em 接口，查询营业部历史交易明细。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

26. get_stock_lh_yyb_most() -> dict
    基于 akshare.stock_lh_yyb_most 接口，查询营业部排行-上榜次数最多。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_yyb_most" }

27. get_stock_lh_yyb_capital() -> dict
    基于 akshare.stock_lh_yyb_capital 接口，查询营业部排行-资金实力最强。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_yyb_capital" }

28. get_stock_lh_yyb_control() -> dict
    基于 akshare.stock_lh_yyb_control 接口，查询营业部排行-抱团操作实力。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lhb_yyb_control" }

29. get_stock_repurchase_em() -> dict
    基于 akshare.stock_repurchase_em 接口，查询股票回购数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "repurchase" }

30. get_stock_dzjy_sctj() -> dict
    基于 akshare.stock_dzjy_sctj 接口，查询大宗交易市场统计（东方财富）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "dzjy_sctj" }

31. get_stock_margin_account_info() -> dict
    基于 akshare.stock_margin_account_info 接口，查询两融账户信息（东方财富）。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "margin_account" }

32. get_stock_margin_sse(start_date: str, end_date: str) -> dict
    基于 akshare.stock_margin_sse 接口，查询上交所融资融券汇总数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "margin_sse" }

33. get_stock_margin_detail_szse(date: str) -> dict
    基于 akshare.stock_margin_detail_szse 接口，查询深交所融资融券明细数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "margin_detail_szse" }

34. get_stock_margin_detail_sse(date: str) -> dict
    基于 akshare.stock_margin_detail_sse 接口，查询上交所融资融券明细数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "margin_detail_sse" }

35. get_stock_profit_forecast_ths(symbol: str, indicator: str) -> dict
    基于 akshare.stock_profit_forecast_ths 接口，查询同花顺盈利预测数据。
    indicator 参数：choice of {"预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", "业绩预测详表-详细指标预测"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

36. get_stock_board_concept_index_ths(symbol: str, start_date: str, end_date: str) -> dict
    基于 akshare.stock_board_concept_index_ths 接口，查询同花顺概念板块指数日频率数据。
    symbol 参数：概念板块名称，如 "阿里巴巴概念"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

37. get_stock_board_industry_summary_ths() -> dict
    基于 akshare.stock_board_industry_summary_ths 接口，查询同花顺行业一览表。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "industry_summary" }

38. get_stock_board_concept_info_ths(symbol: str) -> dict
    基于 akshare.stock_board_concept_info_ths 接口，查询同花顺概念板块简介。
    symbol 参数：概念板块名称，如 "阿里巴巴概念"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

39. get_stock_board_industry_index_ths(symbol: str, start_date: str, end_date: str) -> dict
    基于 akshare.stock_board_industry_index_ths 接口，查询同花顺行业板块指数日频率数据。
    symbol 参数：行业板块名称，如 "元件"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

40. get_stock_hot_follow_xq(symbol: str) -> dict
    基于 akshare.stock_hot_follow_xq 接口，查询雪球关注排行榜。
    symbol 参数：choice of {"本周新增", "最热门"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

41. get_stock_hot_rank_detail_em(symbol: str) -> dict
    基于 akshare.stock_hot_rank_detail_em 接口，查询东方财富股票热度历史趋势及粉丝特征。
    symbol 参数：股票代码，如 "SZ000665"（需带市场前缀）
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

42. get_stock_hot_keyword_em(symbol: str) -> dict
    基于 akshare.stock_hot_keyword_em 接口，查询东方财富个股人气榜热门关键词。
    symbol 参数：股票代码，如 "SZ000665"（需带市场前缀）
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

43. get_stock_changes_em(symbol: str) -> dict
    基于 akshare.stock_changes_em 接口，查询东方财富盘口异动数据。
    symbol 参数：choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

44. get_stock_board_change_em() -> dict
    基于 akshare.stock_board_change_em 接口，查询东方财富当日板块异动详情。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "board_change" }

45. get_stock_zt_pool_em(date: str) -> dict
    基于 akshare.stock_zt_pool_em 接口，查询东方财富涨停股池数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zt_pool" }

46. get_stock_zt_pool_previous_em(date: str) -> dict
    基于 akshare.stock_zt_pool_previous_em 接口，查询东方财富昨日涨停股池数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zt_pool_previous" }

47. get_stock_zt_pool_strong_em(date: str) -> dict
    基于 akshare.stock_zt_pool_strong_em 接口，查询东方财富强势股池数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zt_pool_strong" }

48. get_stock_zt_pool_zbgc_em(date: str) -> dict
    基于 akshare.stock_zt_pool_zbgc_em 接口，查询东方财富炸板股池数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zt_pool_zbgc" }

49. get_stock_zt_pool_dtgc_em(date: str) -> dict
    基于 akshare.stock_zt_pool_dtgc_em 接口，查询东方财富跌停股池数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "zt_pool_dtgc" }

50. get_stock_rank_cxg_ths(symbol: str) -> dict
    基于 akshare.stock_rank_cxg_ths 接口，查询同花顺技术指标-创新高数据。
    symbol 参数：choice of {"创月新高", "半年新高", "一年新高", "历史新高"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

51. get_stock_rank_lxsz_ths() -> dict
    基于 akshare.stock_rank_lxsz_ths 接口，查询同花顺技术选股-连续上涨数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "lxsz" }

52. get_stock_rank_cxfl_ths() -> dict
    基于 akshare.stock_rank_cxfl_ths 接口，查询同花顺技术选股-持续放量数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxfl" }

53. get_stock_rank_cxsl_ths() -> dict
    基于 akshare.stock_rank_cxsl_ths 接口，查询同花顺技术选股-持续缩量数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxsl" }

54. get_stock_rank_xstp_ths(symbol: str) -> dict
    基于 akshare.stock_rank_xstp_ths 接口，查询同花顺技术选股-向上突破数据。
    symbol 参数：choice of {"5日均线", "10日均线", "20日均线", "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

55. get_stock_rank_ljqs_ths() -> dict
    基于 akshare.stock_rank_ljqs_ths 接口，查询同花顺技术选股-量价齐升数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqs" }

56. get_stock_rank_ljqd_ths() -> dict
    基于 akshare.stock_rank_ljqd_ths 接口，查询同花顺技术选股-量价齐跌数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqd" }

57. get_stock_rank_xzjp_ths() -> dict
    基于 akshare.stock_rank_xzjp_ths 接口，查询同花顺技术选股-险资举牌数据。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "xzjp" }

58. get_stock_zh_growth_comparison_em(symbol: str) -> dict
    基于 akshare.stock_zh_growth_comparison_em 接口，查询东方财富-行情中心-同行比较-成长性比较。
    symbol 参数：股票代码，需带市场前缀，如 "SZ000895"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

59. get_stock_zh_valuation_comparison_em(symbol: str) -> dict
    基于 akshare.stock_zh_valuation_comparison_em 接口，查询东方财富-行情中心-同行比较-估值比较。
    symbol 参数：股票代码，需带市场前缀，如 "SZ000895"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

60. get_stock_zh_dupont_comparison_em(symbol: str) -> dict
    基于 akshare.stock_zh_dupont_comparison_em 接口，查询东方财富-行情中心-同行比较-杜邦分析比较。
    symbol 参数：股票代码，需带市场前缀，如 "SZ000895"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

61. get_stock_individual_basic_info_xq(symbol: str) -> dict
    基于 akshare.stock_individual_basic_info_xq 接口，查询雪球财经-个股-公司概况。
    symbol 参数：股票代码，需带市场前缀，如 "SH601127"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

62. get_stock_fund_flow_individual(symbol: str) -> dict
    基于 akshare.stock_fund_flow_individual 接口，查询同花顺-数据中心-资金流向-个股资金流。
    symbol 参数：choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

63. get_stock_fund_flow_concept(symbol: str) -> dict
    基于 akshare.stock_fund_flow_concept 接口，查询同花顺-数据中心-资金流向-概念资金流。
    symbol 参数：choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

64. get_stock_individual_fund_flow(stock: str, market: str) -> dict
    基于 akshare.stock_individual_fund_flow 接口，查询东方财富-数据中心-个股资金流向（近100交易日）。
    stock 参数：股票代码，如 "000425"
    market 参数：choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

65. get_stock_individual_fund_flow_rank(indicator: str) -> dict
    基于 akshare.stock_individual_fund_flow_rank 接口，查询东方财富-数据中心-资金流向排名。
    indicator 参数：choice of {"今日", "3日", "5日", "10日"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

66. get_stock_market_fund_flow() -> dict
    基于 akshare.stock_market_fund_flow 接口，查询东方财富-数据中心-大盘资金流向。
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "market_fund_flow" }

67. get_stock_sector_fund_flow_rank(indicator: str, sector_type: str) -> dict
    基于 akshare.stock_sector_fund_flow_rank 接口，查询东方财富-数据中心-板块资金流排名。
    indicator 参数：choice of {"今日", "5日", "10日"}
    sector_type 参数：choice of {"行业资金流", "概念资金流", "地域资金流"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

68. get_stock_sector_fund_flow_summary(symbol: str, indicator: str) -> dict
    基于 akshare.stock_sector_fund_flow_summary 接口，查询东方财富-数据中心-行业个股资金流。
    symbol 参数：行业板块名称，如 "电源设备"
    indicator 参数：choice of {"今日", "5日", "10日"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

69. get_stock_main_fund_flow(symbol: str) -> dict
    基于 akshare.stock_main_fund_flow 接口，查询东方财富-数据中心-主力净流入排名。
    symbol 参数：choice of {"全部股票", "沪深A股", "沪市A股", "科创板", "深市A股", "创业板", "沪市B股", "深市B股"}
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

70. get_stock_research_report_em(symbol: str) -> dict
    基于 akshare.stock_research_report_em 接口，查询东方财富-数据中心-个股研报。
    symbol 参数：股票代码，如 "000001"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

71. get_stock_gsrl_gsdt_em(date: str) -> dict
    基于 akshare.stock_gsrl_gsdt_em 接口，查询东方财富-数据中心-股市日历-公司动态。
    date 参数：交易日，格式 "YYYYMMDD"，如 "20230808"
    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

"""


import json
import logging
import traceback
import time
import random
from typing import Dict, Any, Optional, Callable
from functools import wraps

import akshare as ak
import pandas as pd

# 配置日志
logger = logging.getLogger(__name__)

# ==================== 网络请求重试装饰器 ====================
# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# 需要重试的网络异常类型
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

def get_random_user_agent() -> str:
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)

def network_retry(max_retries: int = 3, timeout: int = 15, base_delay: float = 1.0):
    """
    网络请求重试装饰器
    
    Args:
        max_retries: 最大重试次数，默认3次
        timeout: 请求超时时间（秒），默认15秒
        base_delay: 基础延迟时间（秒），重试时使用指数退避
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # 设置请求头（使用随机User-Agent）
                    import requests
                    headers = {'User-Agent': get_random_user_agent()}
                    
                    # 第三次尝试才设置全局默认（避免影响正常请求）
                    if attempt == 2:
                        requests.adapters.DEFAULT_RETRIES = max_retries
                    
                    # 执行函数
                    return func(*args, **kwargs)
                    
                except NETWORK_EXCEPTIONS as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"[网络重试] {func.__name__} 第{attempt + 1}次失败，{delay:.1f}秒后重试: {str(e)}")
                        time.sleep(delay)
                    continue
                    
                except Exception as e:
                    # 非网络异常不重试，直接抛出
                    raise
            
            # 所有重试都失败
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator

def safe_call_with_retry(func: Callable, *args, max_retries: int = 3, 
                          timeout: int = 15, logger_name: str = "", **kwargs) -> Any:
    """
    安全调用函数（带重试机制）
    
    Args:
        func: 要调用的函数
        *args: 函数位置参数
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        logger_name: 日志名称前缀
        **kwargs: 函数关键字参数
    
    Returns:
        函数返回值
    """
    last_exception = None
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except NETWORK_EXCEPTIONS as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                log_prefix = f"[{logger_name}]" if logger_name else ""
                logger.warning(f"{log_prefix} 第{attempt + 1}次失败，{delay:.1f}秒后重试: {str(e)}")
                time.sleep(delay)
            continue
        except Exception as e:
            # 非网络异常不重试
            last_exception = e
            break
    
    # 所有重试都失败，抛出最后一个异常
    if last_exception:
        raise last_exception


def _convert_dataframe_to_list(df: pd.DataFrame, log_prefix: str = "") -> list:
    """
    安全地将DataFrame转换为字典列表
    
    Args:
        df: pandas DataFrame对象
        log_prefix: 日志前缀
    
    Returns:
        字典列表
    """
    data_list = []
    
    # 检查DataFrame是否为空或无效
    if df is None:
        logger.warning(f"{log_prefix} DataFrame为None")
        return data_list
    
    if not hasattr(df, 'empty') or df.empty:
        logger.warning(f"{log_prefix} DataFrame为空")
        return data_list
    
    if not hasattr(df, 'columns') or df.columns is None or len(df.columns) == 0:
        logger.warning(f"{log_prefix} DataFrame没有列")
        return data_list
    
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            try:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
            except Exception as e:
                # 单个字段转换失败，使用None
                logger.debug(f"{log_prefix} 字段转换失败 col={col}: {str(e)}")
                value = None
            record[col] = value
        data_list.append(record)
    
    return data_list


def get_stock_info(symbol: str) -> Dict[str, Any]:
    """
    查询指定股票代码的个股基础信息（东方财富接口）
    
    Args:
        symbol: 股票代码，如 "000001"（平安银行），"603777"（来伊份）
    
    Returns:
        统一结构字典：
        {
            "success": True/False,
            "data": {
                "item": ...,
                "value": ...,
                // 其他字段根据 akshare 返回的 DataFrame 转换
            },
            "error": None 或错误信息,
            "symbol": symbol
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }
    
    # 日志记录查询开始
    logger.info(f"[个股信息查询] 开始查询 symbol={symbol}")
    
    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            # 调用 akshare 接口（带重试机制）
            df = safe_call_with_retry(
                ak.stock_individual_info_em, 
                symbol=symbol,
                max_retries=1,  # 内部重试由外层控制
                logger_name="个股信息查询"
            )
            
            # 将 DataFrame 转换为便于 JSON 序列化的结构
            # 假设 DataFrame 有两列：'item' 和 'value'
            # 转换为字典列表，然后合并为单个字典
            data_list = []
            if df is not None and not df.empty:
                # 确保列名正确
                if 'item' in df.columns and 'value' in df.columns:
                    for _, row in df.iterrows():
                        item = row['item']
                        value = row['value']
                        # 尝试将 value 转换为合适的 Python 类型（如数字、字符串）
                        if isinstance(value, (int, float, str, bool, type(None))):
                            pass  # 保持原样
                        else:
                            # 其他类型（如 pandas 特定类型）转换为字符串
                            value = str(value)
                        data_list.append({"item": item, "value": value})
                else:
                    # 如果列名不是预期的，将整个 DataFrame 转换为字典
                    data_list = df.to_dict(orient='records')
            
            # 将列表转换为嵌套字典，方便前端使用
            # 例如：{"股票代码": "000001", "股票简称": "平安银行", ...}
            data_dict = {}
            for entry in data_list:
                if isinstance(entry, dict) and 'item' in entry and 'value' in entry:
                    key = entry['item']
                    val = entry['value']
                    data_dict[key] = val
                elif isinstance(entry, dict):
                    # 直接合并字典
                    data_dict.update(entry)
            
            # 补充 symbol
            data_dict['symbol'] = symbol
            
            logger.info(f"[个股信息查询] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")
            
            return {
                "success": True,
                "data": data_dict,
                "error": None,
                "symbol": symbol
            }
            
        except Exception as e:
            error_msg = f"查询个股信息失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[个股信息查询] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[个股信息查询] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[个股信息查询] 异常详情: {traceback.format_exc()}")
                
                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_info_json(symbol: str) -> str:
    """
    查询个股信息并返回 JSON 字符串（方便直接返回 HTTP 响应）
    
    Args:
        symbol: 股票代码
    
    Returns:
        JSON 字符串，包含统一结构
    """
    result = get_stock_info(symbol)
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_stock_gpzy_profile_em() -> Dict[str, Any]:
    """
    股权质押市场概况查询接口（东方财富接口）
    
    接口: stock_gpzy_profile_em
    目标地址: https://data.eastmoney.com/gpzy/marketProfile.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-股权质押市场概况
    限量: 单次所有历史数据, 由于数据量比较大需要等待一定时间
    
    输入参数:
        无（该接口无需输入参数）
    
    输出参数（返回的 DataFrame 列说明）:
        - 交易日期 (object): 数据发布日期
        - A股质押总比例 (float64): A股市场质押总比例，单位: %
        - 质押公司数量 (float64): 当前进行质押的公司数量
        - 质押笔数 (float64): 质押交易笔数，单位: 笔
        - 质押总股数 (float64): 质押总股数，单位: 股
        - 质押总市值 (float64): 质押总市值，单位: 元
        - 沪深300指数 (float64): 沪深300指数收盘价
        - 涨跌幅 (float64): 沪深300指数涨跌幅，单位: %
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "交易日期": "2023-01-01",
                    "A股质押总比例": 5.23,
                    "质押公司数量": 1234.0,
                    "质押笔数": 5678.0,
                    "质押总股数": 123456789.0,
                    "质押总市值": 9876543210.0,
                    "沪深300指数": 4000.0,
                    "涨跌幅": 0.5
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "gpzy_profile"  # 固定标识
        }
    
    注意: 数据量可能较大，调用时请耐心等待。
    """
    # 日志记录查询开始
    logger.info(f"[股权质押概况] 开始查询市场概况")
    
    try:
        # 调用 akshare 接口
        df = ak.stock_gpzy_profile_em()
        
        # 检查 DataFrame 是否为空
        if df.empty:
            logger.warning("[股权质押概况] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_profile"
            }
        
        # 将 DataFrame 转换为便于 JSON 序列化的列表字典
        # 保持列名原样（中文），避免类型问题
        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                # 处理 pandas 特殊类型（如 Timestamp、NaN）
                if hasattr(value, 'isoformat'):  # Timestamp 类型
                    value = value.isoformat()
                elif pd.isna(value):  # 检查 NaN
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass  # 保持原样
                else:
                    # 其他类型转换为字符串
                    value = str(value)
                record[col] = value
            data_list.append(record)
        
        logger.info(f"[股权质押概况] 查询成功，数据条数={len(data_list)}")
        
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_profile"
        }
        
    except Exception as e:
        error_msg = f"查询股权质押市场概况失败: {str(e)}"
        logger.error(f"[股权质押概况] 异常 error={error_msg}")
        logger.debug(f"[股权质押概况] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_profile"
        }


def get_stock_gpzy_pledge_ratio_em(date: str) -> Dict[str, Any]:
    """
    上市公司质押比例查询接口（东方财富接口）
    
    接口: stock_gpzy_pledge_ratio_em
    目标地址: https://data.eastmoney.com/gpzy/pledgeRatio.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例
    限量: 单次返回指定交易日的所有历史数据; 其中的交易日需要根据网站提供的为准;
          请访问 http://data.eastmoney.com/gpzy/pledgeRatio.aspx 查询具体交易日
    
    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240906"
              请访问 http://data.eastmoney.com/gpzy/pledgeRatio.aspx 查询具体交易日
    
    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 交易日期 (object): 交易日期
        - 所属行业 (object): 所属行业
        - 质押比例 (float64): 质押比例，单位: %
        - 质押股数 (float64): 质押股数，单位: 万股
        - 质押市值 (float64): 质押市值，单位: 万元
        - 质押笔数 (float64): 质押笔数
        - 无限售股质押数 (float64): 无限售股质押数，单位: 万股
        - 限售股质押数 (float64): 限售股质押数，单位: 万股
        - 近一年涨跌幅 (float64): 近一年涨跌幅，单位: %
        - 所属行业代码 (object): 所属行业代码
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "股票代码": "000001",
                    "股票简称": "平安银行",
                    "交易日期": "2024-09-06",
                    "所属行业": "银行",
                    "质押比例": 5.23,
                    "质押股数": 1234.56,
                    "质押市值": 56789.01,
                    "质押笔数": 12.0,
                    "无限售股质押数": 1000.0,
                    "限售股质押数": 234.56,
                    "近一年涨跌幅": 15.5,
                    "所属行业代码": "银行"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "gpzy_pledge_ratio"  # 固定标识
        }
    
    注意: 日期参数需要根据网站提供的交易日为准，否则可能返回空数据。
    """
    # 参数验证
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期参数必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "gpzy_pledge_ratio"
        }
    
    # 日志记录查询开始
    logger.info(f"[上市公司质押比例] 开始查询 date={date}")
    
    try:
        # 调用 akshare 接口
        df = ak.stock_gpzy_pledge_ratio_em(date=date)
        
        # 检查 DataFrame 是否为空
        if df.empty:
            logger.warning(f"[上市公司质押比例] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_pledge_ratio"
            }
        
        # 将 DataFrame 转换为便于 JSON 序列化的列表字典
        # 保持列名原样（中文），避免类型问题
        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                # 处理 pandas 特殊类型（如 Timestamp、NaN）
                if hasattr(value, 'isoformat'):  # Timestamp 类型
                    value = value.isoformat()
                elif pd.isna(value):  # 检查 NaN
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass  # 保持原样
                else:
                    # 其他类型转换为字符串
                    value = str(value)
                record[col] = value
            data_list.append(record)
        
        logger.info(f"[上市公司质押比例] 查询成功 date={date}, 数据条数={len(data_list)}")
        
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_pledge_ratio"
        }
        
    except Exception as e:
        error_msg = f"查询上市公司质押比例失败: {str(e)}"
        logger.error(f"[上市公司质押比例] 异常 date={date}, error={error_msg}")
        logger.debug(f"[上市公司质押比例] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_pledge_ratio"
        }


def get_stock_gpzy_individual_pledge_ratio_detail_em(symbol: str) -> Dict[str, Any]:
    """
    个股重要股东股权质押明细查询接口（东方财富接口）
    
    接口: stock_gpzy_company_em (原 stock_gpzy_individual_pledge_ratio_detail_em 已停用)
    目标地址: https://data.eastmoney.com/gpzy/
    描述: 东方财富网-数据中心-股权质押-个股质押明细
    限量: 单次所有历史数据
    
    输入参数:
        symbol: str - 股票代码，如 "603132"
    
    输出参数（返回的 DataFrame 列说明）:
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 公告日期 (object): 公告日期
        - 质押机构 (object): 质押机构名称
        - 质押数量 (float64): 质押数量
        - 质押起始日期 (object): 质押开始日期
        - 质押结束日期 (object): 质押结束日期
        - 解除日期 (object): 解除日期
        - 质押方式 (object): 质押方式
        - 用途 (object): 用途
        - 是否解压 (object): 是否解压
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "603132",
                    "股票简称": "xxx",
                    "公告日期": "2023-01-01",
                    "质押机构": "xxx银行",
                    "质押数量": 1000000.0,
                    "质押起始日期": "2023-01-01",
                    "质押结束日期": "2024-01-01",
                    "解除日期": None,
                    "质押方式": "质押式回购",
                    "用途": "个人",
                    "是否解压": "否"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }
    
    logger.info(f"[个股质押明细] 开始查询 symbol={symbol}")
    
    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            # 优先使用 stock_gpzy_company_em（新的可用接口）
            # 备用 stock_gpzy_individual_pledge_ratio_detail_em（可能已停用）
            try:
                df = ak.stock_gpzy_company_em(symbol=symbol)
                logger.info(f"[个股质押明细] 使用 stock_gpzy_company_em 接口 symbol={symbol}")
            except (AttributeError, TypeError) as ae:
                # 接口不可用时使用备用接口
                logger.warning(f"[个股质押明细] stock_gpzy_company_em 不可用，尝试备用接口 symbol={symbol}")
                df = ak.stock_gpzy_individual_pledge_ratio_detail_em(symbol=symbol)
            
            if df is None or df.empty:
                logger.warning(f"[个股质押明细] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }
            
            data_list = _convert_dataframe_to_list(df, "[个股质押明细]")

            logger.info(f"[个股质押明细] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")
            
            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }
            
        except Exception as e:
            error_msg = f"查询个股质押明细失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[个股质押明细] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[个股质押明细] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[个股质押明细] 异常详情: {traceback.format_exc()}")
                
                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_gpzy_industry_data_em() -> Dict[str, Any]:
    """
    上市公司质押比例-行业数据查询接口（东方财富接口）
    
    接口: stock_gpzy_industry_data_em
    目标地址: https://data.eastmoney.com/gpzy/industryData.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据
    限量: 单次返回所有历史数据
    
    输入参数:
        无（该接口无需输入参数）
    
    输出参数（返回的 DataFrame 列说明）:
        - 行业 (object): 行业名称
        - 平均质押比例 (float64): 平均质押比例，单位: %
        - 公司家数 (float64): 该行业有质押的公司家数
        - 质押总笔数 (float64): 质押交易总笔数
        - 质押总股本 (float64): 质押总股本数量
        - 最新质押市值 (float64): 最新质押市值
        - 统计时间 (object): 统计时间
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "行业": "银行",
                    "平均质押比例": 5.23,
                    "公司家数": 12.0,
                    "质押总笔数": 56.0,
                    "质押总股本": 987654321.0,
                    "最新质押市值": 1234567890.0,
                    "统计时间": "2024-09-06"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "gpzy_industry"  # 固定标识
        }
    """
    logger.info("[行业质押数据] 开始查询行业质押数据")
    
    try:
        df = ak.stock_gpzy_industry_data_em()
        
        if df.empty:
            logger.warning("[行业质押数据] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_industry"
            }
        
        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)
        
        logger.info(f"[行业质押数据] 查询成功，数据条数={len(data_list)}")
        
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_industry"
        }
        
    except Exception as e:
        error_msg = f"查询行业质押数据失败: {str(e)}"
        logger.error(f"[行业质押数据] 异常 error={error_msg}")
        logger.debug(f"[行业质押数据] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_industry"
        }


def get_stock_account_statistics_em() -> Dict[str, Any]:
    """
    股票账户统计月度数据查询接口（东方财富接口）
    
    接口: stock_account_statistics_em
    目标地址: https://data.eastmoney.com/cjsj/gpkhsj.html
    描述: 东方财富网-数据中心-特色数据-股票账户统计（月度）
    限量: 单次返回从 201504 开始至最新的所有历史数据
    
    输入参数:
        无（该接口无需输入参数）
    
    输出参数（返回的 DataFrame 列说明）:
        - 数据日期 (object): 数据统计月份（格式如 "202308"）
        - 新增投资者-数量 (float64): 当月新增投资者数量，单位: 万户
        - 新增投资者-环比 (float64): 新增投资者数量环比变化
        - 新增投资者-同比 (float64): 新增投资者数量同比变化
        - 期末投资者-总量 (float64): 期末投资者总量，单位: 万户
        - 期末投资者-A股账户 (float64): 期末 A 股账户数量，单位: 万户
        - 期末投资者-B股账户 (float64): 期末 B 股账户数量，单位: 万户
        - 沪深总市值 (float64): 沪深两市总市值
        - 沪深户均市值 (float64): 沪深两市户均市值，单位: 万
        - 上证指数-收盘 (float64): 上证指数月末收盘价
        - 上证指数-涨跌幅 (float64): 上证指数当月涨跌幅
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "数据日期": "202308",
                    "新增投资者-数量": 234.56,
                    "新增投资者-环比": 5.3,
                    "新增投资者-同比": 10.2,
                    "期末投资者-总量": 22000.0,
                    "期末投资者-A股账户": 21000.0,
                    "期末投资者-B股账户": 20.5,
                    "沪深总市值": 850000.0,
                    "沪深户均市值": 3.86,
                    "上证指数-收盘": 3200.5,
                    "上证指数-涨跌幅": 2.3
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "account_statistics"  # 固定标识
        }
    """
    logger.info("[股票账户统计] 开始查询月度账户统计数据")
    
    try:
        df = ak.stock_account_statistics_em()
        
        if df.empty:
            logger.warning("[股票账户统计] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "account_statistics"
            }
        
        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)
        
        logger.info(f"[股票账户统计] 查询成功，数据条数={len(data_list)}")
        
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "account_statistics"
        }
        
    except Exception as e:
        error_msg = f"查询股票账户统计失败: {str(e)}"
        logger.error(f"[股票账户统计] 异常 error={error_msg}")
        logger.debug(f"[股票账户统计] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "account_statistics"
        }


def get_stock_comment_em() -> Dict[str, Any]:
    """
    千股千评数据查询接口（东方财富接口）
    
    接口: stock_comment_em
    目标地址: https://data.eastmoney.com/stockcomment/
    描述: 东方财富网-数据中心-特色数据-千股千评
    限量: 单次获取所有股票当日评分数据
    
    输入参数:
        无（该接口无需输入参数）
    
    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称
        - 最新价 (float64): 最新价格
        - 涨跌幅 (float64): 涨跌幅
        - 换手率 (float64): 换手率，单位: %
        - 市盈率 (float64): 市盈率（TTM）
        - 主力成本 (float64): 主力成本价
        - 机构参与度 (float64): 机构参与度评分
        - 综合得分 (float64): 综合评分（0-100分）
        - 上升 (int64): 排名变动，正数上升、负数下降
        - 目前排名 (int64): 当前综合排名
        - 关注指数 (float64): 市场关注指数
        - 交易日 (float64): 交易日期
    
    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000001",
                    "名称": "平安银行",
                    "最新价": 12.5,
                    "涨跌幅": 2.3,
                    "换手率": 1.5,
                    "市盈率": 5.8,
                    "主力成本": 11.2,
                    "机构参与度": 68.5,
                    "综合得分": 75.0,
                    "上升": 5,
                    "目前排名": 120,
                    "关注指数": 88.6,
                    "交易日": 20240906.0
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "stock_comment"  # 固定标识
        }
    
    注意: 该接口数据量较大（全市场股票），请耐心等待。
    """
    logger.info("[千股千评] 开始查询千股千评数据")
    
    try:
        df = ak.stock_comment_em()
        
        if df.empty:
            logger.warning("[千股千评] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "stock_comment"
            }
        
        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)
        
        logger.info(f"[千股千评] 查询成功，数据条数={len(data_list)}")
        
        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "stock_comment"
        }
        
    except Exception as e:
        error_msg = f"查询千股千评数据失败: {str(e)}"
        logger.error(f"[千股千评] 异常 error={error_msg}")
        logger.debug(f"[千股千评] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "stock_comment"
        }


def get_stock_comment_detail_scrd_focus_em(symbol: str) -> Dict[str, Any]:
    """
    千股千评-用户关注指数查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_focus_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
    限量: 单次获取所有数据

    输入参数:
        symbol: str - 股票代码，如 "600000"

    输出参数（返回的 DataFrame 列说明）:
        - 交易日 (object): 交易日期
        - 用户关注指数 (float64): 市场用户对该股票的关注程度指数

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "交易日": "2024-09-06",
                    "用户关注指数": 12345.67
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[用户关注指数] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_comment_detail_scrd_focus_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[用户关注指数] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[用户关注指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询用户关注指数失败: {str(e)}"
        logger.error(f"[用户关注指数] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[用户关注指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_comment_detail_scrd_desire_em(symbol: str) -> Dict[str, Any]:
    """
    千股千评-市场参与意愿查询接口（东方财富接口）

    接口: stock_comment_detail_scrd_desire_em
    目标地址: https://data.eastmoney.com/stockcomment/stock/600000.html
    描述: 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
    限量: 单次获取所有数据

    输入参数:
        symbol: str - 股票代码，如 "600000"

    输出参数（返回的 DataFrame 列说明）:
        - 交易日期 (object): 交易日期
        - 股票代码 (object): 股票代码
        - 参与意愿 (float64): 市场参与意愿指数
        - 5日平均参与意愿 (float64): 5日平均参与意愿
        - 参与意愿变化 (float64): 参与意愿变化值
        - 5日平均变化 (float64): 5日平均变化值

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "交易日期": "2024-09-06",
                    "股票代码": "600000",
                    "参与意愿": 78.5,
                    "5日平均参与意愿": 75.3,
                    "参与意愿变化": 3.2,
                    "5日平均变化": 0.8
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[市场参与意愿] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_comment_detail_scrd_desire_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[市场参与意愿] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[市场参与意愿] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询市场参与意愿失败: {str(e)}"
        logger.error(f"[市场参与意愿] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[市场参与意愿] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_cyq_em(symbol: str, adjust: str = "") -> Dict[str, Any]:
    """
    筹码分布查询接口（东方财富接口）

    接口: stock_cyq_em
    目标地址: https://quote.eastmoney.com/concept/sz000001.html
    描述: 东方财富网-概念板-行情中心-日K-筹码分布
    限量: 单次返回指定 symbol 和 adjust 的近 90 个交易日数据

    输入参数:
        symbol: str - 股票代码，如 "000001"（需带市场前缀如 sz/sz/sh 等）
        adjust: str - 复权类型，可选值：
                    "qfq": 前复权
                    "hfq": 后复权
                    "": 不复权（默认）

    输出参数（返回的 DataFrame 列说明）:
        - 日期 (object): 交易日期
        - 获利比例 (float64): 获利筹码比例，单位: %
        - 平均成本 (float64): 平均持仓成本
        - 90成本-低 (float64): 90%筹码的最低价格
        - 90成本-高 (float64): 90%筹码的最高价格
        - 90集中度 (float64): 90%筹码的集中度
        - 70成本-低 (float64): 70%筹码的最低价格
        - 70成本-高 (float64): 70%筹码的最高价格
        - 70集中度 (float64): 70%筹码的集中度

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "日期": "2024-09-06",
                    "获利比例": 65.5,
                    "平均成本": 12.35,
                    "90成本-低": 10.50,
                    "90成本-高": 15.20,
                    "90集中度": 0.35,
                    "70成本-低": 11.00,
                    "70成本-高": 14.50,
                    "70集中度": 0.28
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "sz000001" 表示深圳平安银行
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    # adjust 参数验证
    valid_adjusts = ["qfq", "hfq", ""]
    if adjust not in valid_adjusts:
        adjust = ""  # 默认不复权

    logger.info(f"[筹码分布] 开始查询 symbol={symbol}, adjust={adjust}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_cyq_em,
                symbol=symbol,
                adjust=adjust,
                max_retries=1,
                logger_name="筹码分布"
            )

            if df is None or df.empty:
                logger.warning(f"[筹码分布] 返回数据为空 symbol={symbol}, adjust={adjust}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[筹码分布]")

            logger.info(f"[筹码分布] 查询成功 symbol={symbol}, adjust={adjust}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询筹码分布失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[筹码分布] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[筹码分布] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[筹码分布] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_gddh_em() -> Dict[str, Any]:
    """
    股东大会列表查询接口（东方财富接口）

    接口: stock_gddh_em
    目标地址: https://data.eastmoney.com/gddh/
    描述: 东方财富网-数据中心-股东大会
    限量: 单次返回所有数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 代码 (object): 股票代码
        - 简称 (object): 股票简称
        - 股东大会名称 (object): 股东大会名称
        - 召开开始日 (object): 股东大会召开开始日期
        - 股权登记日 (object): 股权登记日期
        - 现场登记日 (object): 现场登记日期
        - 网络投票时间-开始日 (object): 网络投票开始日期
        - 网络投票时间-结束日 (object): 网络投票结束日期
        - 决议公告日 (object): 决议公告日期
        - 公告日 (object): 公告发布日期
        - 序列号 (object): 序列号
        - 提案 (object): 股东大会提案内容

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "代码": "600000",
                    "简称": "浦发银行",
                    "股东大会名称": "2024年第一次临时股东大会",
                    "召开开始日": "2024-09-15",
                    "股权登记日": "2024-09-10",
                    "现场登记日": "2024-09-14",
                    "网络投票时间-开始日": "2024-09-15",
                    "网络投票时间-结束日": "2024-09-15",
                    "决议公告日": "2024-09-16",
                    "公告日": "2024-09-01",
                    "序列号": "12345",
                    "提案": "关于修改公司章程的议案"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "gddh"  # 固定标识
        }
    """
    logger.info("[股东大会] 开始查询股东大会数据")

    try:
        df = ak.stock_gddh_em()

        if df.empty:
            logger.warning("[股东大会] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gddh"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[股东大会] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gddh"
        }

    except Exception as e:
        error_msg = f"查询股东大会数据失败: {str(e)}"
        logger.error(f"[股东大会] 异常 error={error_msg}")
        logger.debug(f"[股东大会] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gddh"
        }


def get_stock_zdhtmx_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    重大合同明细查询接口（东方财富接口）

    接口: stock_zdhtmx_em
    目标地址: https://data.eastmoney.com/zdht/mx.html
    描述: 东方财富网-数据中心-重大合同-重大合同明细
    限量: 单次返回指定 start_date 和 end_date 的所有数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20200819"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20230819"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 签署主体 (object): 合同签署主体
        - 签署主体-与上市公司关系 (object): 签署主体与上市公司的关系
        - 其他签署方 (object): 其他签署方
        - 其他签署方-与上市公司关系 (object): 其他签署方与上市公司的关系
        - 合同类型 (object): 合同类型
        - 合同名称 (object): 合同名称
        - 合同金额 (float64): 合同金额，单位: 元
        - 上年度营业收入 (float64): 上年度营业收入，单位: 元
        - 占上年度营业收入比例 (float64): 占上年度营业收入比例
        - 最新财务报表的营业收入 (float64): 最新财务报表营业收入
        - 签署日期 (object): 合同签署日期
        - 公告日期 (object): 公告发布日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "股票代码": "600000",
                    "股票简称": "浦发银行",
                    "签署主体": "浦发银行",
                    "签署主体-与上市公司关系": "上市公司本身",
                    "其他签署方": "XXX公司",
                    "其他签署方-与上市公司关系": "第三方",
                    "合同类型": "采购合同",
                    "合同名称": "IT设备采购合同",
                    "合同金额": 5000000.0,
                    "上年度营业收入": 100000000.0,
                    "占上年度营业收入比例": 5.0,
                    "最新财务报表的营业收入": 110000000.0,
                    "签署日期": "2023-06-15",
                    "公告日期": "2023-06-16"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zdht"  # 固定标识
        }
    """
    # 参数验证
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zdht"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "zdht"
        }

    logger.info(f"[重大合同] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_zdhtmx_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[重大合同] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zdht"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[重大合同] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zdht"
        }

    except Exception as e:
        error_msg = f"查询重大合同明细失败: {str(e)}"
        logger.error(f"[重大合同] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[重大合同] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zdht"
        }


def get_stock_financial_report_sina(stock: str, symbol: str = "资产负债表") -> Dict[str, Any]:
    """
    新浪财经财务报表查询接口（新浪财经）

    接口: stock_financial_report_sina
    目标地址: https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/600600/displaytype/4.phtml
    描述: 新浪财经-财务报表-三大报表
    限量: 单次获取指定报表的所有年份数据的历史数据

    注意: 原始数据中有 国内票证结算 和 内部应收款 字段重复，返回数据中已经剔除

    输入参数:
        stock: str - 带市场标识的股票代码，如 "sh600600"（沪市）或 "sz000001"（深市）
        symbol: str - 报表类型，可选值：
                    "资产负债表"
                    "利润表"
                    "现金流量表"
                    默认: "资产负债表"

    输出参数（返回的 DataFrame 列说明）:
        - 报告日 (object): 报告日期
        - 流动资产 (float64): 流动资产金额
        - 非流动资产 (float64): 非流动资产金额
        - 资产总计 (float64): 资产总计
        - 流动负债 (float64): 流动负债金额
        - 非流动负债 (float64): 非流动负债金额
        - 负债合计 (float64): 负债合计
        - 所有者权益 (float64): 所有者权益
        - ... (其他财务报表字段，字段数量众多)
        - 类型 (object): 报表类型标识
        - 更新日期 (object): 数据更新日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "报告日": "2024-06-30",
                    "流动资产": 1234567890.0,
                    "非流动资产": 987654321.0,
                    "资产总计": 2222222211.0,
                    "流动负债": 500000000.0,
                    "非流动负债": 200000000.0,
                    "负债合计": 700000000.0,
                    "所有者权益": 1522222211.0,
                    "类型": "资产负债表",
                    "更新日期": "2024-08-30"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": stock  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "sh600600" 表示沪市浦发银行
    """
    # 参数验证
    if not stock or not isinstance(stock, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 sh600600",
            "symbol": stock or ""
        }

    valid_symbols = ["资产负债表", "利润表", "现金流量表"]
    if symbol not in valid_symbols:
        symbol = "资产负债表"  # 默认资产负债表

    logger.info(f"[新浪财务报表] 开始查询 stock={stock}, symbol={symbol}")

    try:
        df = ak.stock_financial_report_sina(stock=stock, symbol=symbol)

        if df.empty:
            logger.warning(f"[新浪财务报表] 返回数据为空 stock={stock}, symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": stock
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[新浪财务报表] 查询成功 stock={stock}, symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": stock
        }

    except Exception as e:
        error_msg = f"查询新浪财务报表失败: {str(e)}"
        logger.error(f"[新浪财务报表] 异常 stock={stock}, error={error_msg}")
        logger.debug(f"[新浪财务报表] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": stock
        }


def get_stock_balance_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富资产负债表（按年度）查询接口

    接口: stock_balance_sheet_by_yearly_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
    描述: 东方财富-股票-财务分析-资产负债表-按年度
    限量: 单次获取指定 symbol 的资产负债表-按年度数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

    输出参数（返回的 DataFrame 列说明）:
        该接口返回 319 项资产负债表字段，数量较多，常见字段包括：
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 审计意见 (object): 审计意见类型
        - 报告类型 (object): 报告类型（年度/季度）
        - 报告日期 (object): 报告日期
        - 流动资产合计 (float64): 流动资产合计
        - 非流动资产合计 (float64): 非流动资产合计
        - 资产总计 (float64): 资产总计
        - 流动负债合计 (float64): 流动负债合计
        - 非流动负债合计 (float64): 非流动负债合计
        - 负债合计 (float64): 负债合计
        - 所有者权益合计 (float64): 所有者权益合计
        - ... (其他300+字段)

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "报告日期": "2024-12-31",
                    "流动资产合计": 1234567890.0,
                    "非流动资产合计": 987654321.0,
                    "资产总计": 2222222211.0,
                    "...": "..."
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "SH600519" 表示沪市贵州茅台
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富资产负债表] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)

            # 修复空数据判断
            if df is None or len(df) == 0:
                logger.warning(f"[东方财富资产负债表] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[东方财富资产负债表]")

            logger.info(f"[东方财富资产负债表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富资产负债表失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[东方财富资产负债表] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[东方财富资产负债表] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[东方财富资产负债表] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_profit_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按报告期）查询接口

    接口: stock_profit_sheet_by_report_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
    描述: 东方财富-股票-财务分析-利润表-报告期
    限量: 单次获取指定 symbol 的利润表-报告期数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

    输出参数（返回的 DataFrame 列说明）:
        该接口返回 203 项利润表字段，数量较多，常见字段包括：
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 审计意见 (object): 审计意见类型
        - 报告类型 (object): 报告类型（年度/季度/中期）
        - 报告日期 (object): 报告日期
        - 净利润 (float64): 净利润
        - 营业总收入 (float64): 营业总收入
        - 营业总成本 (float64): 营业总成本
        - 营业利润 (float64): 营业利润
        - 利润总额 (float64): 利润总额
        - 所得税费用 (float64): 所得税费用
        - 投资收益 (float64): 投资收益
        - 公允价值变动收益 (float64): 公允价值变动收益
        - 营业外收入 (float64): 营业外收入
        - 营业外支出 (float64): 营业外支出
        - 基本每股收益 (float64): 基本每股收益
        - 稀释每股收益 (float64): 稀释每股收益
        - ... (其他190+字段)

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "报告日期": "2024-06-30",
                    "净利润": 1234567890.0,
                    "营业总收入": 9876543210.0,
                    "营业总成本": 8000000000.0,
                    "营业利润": 2000000000.0,
                    "利润总额": 2100000000.0,
                    "所得税费用": 500000000.0,
                    "基本每股收益": 35.0,
                    "稀释每股收益": 35.0,
                    "...": "..."
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "SH600519" 表示沪市贵州茅台
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富利润表] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富利润表] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富利润表]")

        logger.info(f"[东方财富利润表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富利润表失败: {str(e)}"
        logger.error(f"[东方财富利润表] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[东方财富利润表] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_profit_sheet_by_yearly_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富利润表（按年度）查询接口

    接口: stock_profit_sheet_by_yearly_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519#lrb-0
    描述: 东方财富-股票-财务分析-利润表-按年度
    限量: 单次获取指定 symbol 的利润表-按年度数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

    输出参数（返回的 DataFrame 列说明）:
        该接口返回 203 项利润表字段，数量较多，常见字段包括：
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 审计意见 (object): 审计意见类型
        - 报告类型 (object): 报告类型（年度）
        - 报告日期 (object): 报告日期
        - 净利润 (float64): 净利润
        - 营业总收入 (float64): 营业总收入
        - 营业总成本 (float64): 营业总成本
        - 营业利润 (float64): 营业利润
        - 利润总额 (float64): 利润总额
        - 所得税费用 (float64): 所得税费用
        - 投资收益 (float64): 投资收益
        - 公允价值变动收益 (float64): 公允价值变动收益
        - 营业外收入 (float64): 营业外收入
        - 营业外支出 (float64): 营业外支出
        - 基本每股收益 (float64): 基本每股收益
        - 稀释每股收益 (float64): 稀释每股收益
        - ... (其他190+字段)

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "报告日期": "2024-12-31",
                    "净利润": 1234567890.0,
                    "营业总收入": 9876543210.0,
                    "营业总成本": 8000000000.0,
                    "营业利润": 2000000000.0,
                    "利润总额": 2100000000.0,
                    "所得税费用": 500000000.0,
                    "基本每股收益": 35.0,
                    "稀释每股收益": 35.0,
                    "...": "..."
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "SH600519" 表示沪市贵州茅台
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富利润表(年度)] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富利润表(年度)] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[东方财富利润表(年度)]")

        logger.info(f"[东方财富利润表(年度)] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富利润表(年度)失败: {str(e)}"
        logger.error(f"[东方财富利润表(年度)] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[东方财富利润表(年度)] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_cash_flow_sheet_by_report_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富现金流量表（按报告期）查询接口

    接口: stock_cash_flow_sheet_by_report_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519#lrb-0
    描述: 东方财富-股票-财务分析-现金流量表-按报告期
    限量: 单次获取指定 symbol 的现金流量表-按报告期数据

    输入参数:
        symbol: str - 股票代码，需带市场前缀，如 "SH600519"（沪市茅台）或 "SZ000001"（深市平安银行）

    输出参数（返回的 DataFrame 列说明）:
        该接口返回 252 项现金流量表字段，数量较多，常见字段包括：
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 审计意见 (object): 审计意见类型
        - 报告类型 (object): 报告类型（年度/季度/中期）
        - 报告日期 (object): 报告日期
        - 经营活动产生的现金流量净额 (float64): 经营活动产生的现金流量净额
        - 经营活动现金流入小计 (float64): 经营活动现金流入小计
        - 经营活动现金流出小计 (float64): 经营活动现金流出小计
        - 投资活动产生的现金流量净额 (float64): 投资活动产生的现金流量净额
        - 投资活动现金流入小计 (float64): 投资活动现金流入小计
        - 投资活动现金流出小计 (float64): 投资活动现金流出小计
        - 筹资活动产生的现金流量净额 (float64): 筹资活动产生的现金流量净额
        - 筹资活动现金流入小计 (float64): 筹资活动现金流入小计
        - 筹资活动现金流出小计 (float64): 筹资活动现金流出小计
        - 汇率变动对现金的影响 (float64): 汇率变动对现金的影响
        - 现金及现金等价物净增加额 (float64): 现金及现金等价物净增加额
        - 期末现金及现金等价物余额 (float64): 期末现金及现金等价物余额
        - ... (其他237+字段)

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "报告日期": "2024-06-30",
                    "经营活动产生的现金流量净额": 5000000000.0,
                    "经营活动现金流入小计": 8000000000.0,
                    "经营活动现金流出小计": 3000000000.0,
                    "投资活动产生的现金流量净额": -1000000000.0,
                    "投资活动现金流入小计": 500000000.0,
                    "投资活动现金流出小计": 1500000000.0,
                    "筹资活动产生的现金流量净额": -2000000000.0,
                    "筹资活动现金流入小计": 1000000000.0,
                    "筹资活动现金流出小计": 3000000000.0,
                    "现金及现金等价物净增加额": 2000000000.0,
                    "期末现金及现金等价物余额": 15000000000.0,
                    "...": "..."
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意: symbol 参数需要带市场前缀，如 "SH600519" 表示沪市贵州茅台
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 SH600519",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富现金流量表] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)

            if df is None or len(df) == 0:
                logger.warning(f"[东方财富现金流量表] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[东方财富现金流量表]")

            logger.info(f"[东方财富现金流量表] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富现金流量表失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[东方财富现金流量表] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[东方财富现金流量表] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[东方财富现金流量表] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_gdfx_free_top_10_em(symbol: str, date: str) -> Dict[str, Any]:
    """
    十大流通股东查询接口（东方财富接口）

    接口: stock_gdfx_free_top_10_em
    目标地址: https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/Index?type=web&code=SH688686#sdltgd-0
    描述: 东方财富网-个股-十大流通股东
    限量: 单次返回指定 symbol 和 date 的所有数据

    输入参数:
        symbol: str - 带市场标识的股票代码，如 "sh688686"（沪市亚虹医药）
        date: str - 财报发布季度最后日，格式为 "YYYYMMDD"，如 "20240930"

    输出参数（返回的 DataFrame 列说明）:
        - 名次 (int64): 股东排名
        - 股东名称 (object): 股东名称
        - 股东性质 (object): 股东性质（机构/个人等）
        - 股份类型 (object): 股份类型（A股/B股等）
        - 持股数 (int64): 持股数量（注意单位: 股）
        - 占总流通股本持股比例 (float64): 占总流通股本持股比例（注意单位: %）
        - 增减 (object): 持股变动情况（注意单位: 股）
        - 变动比率 (float64): 变动比率（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "名次": 1,
                    "股东名称": "中国证券金融股份有限公司",
                    "股东性质": "一般法人",
                    "股份类型": "流通A股",
                    "持股数": 123456789,
                    "占总流通股本持股比例": 5.23,
                    "增减": "不变",
                    "变动比率": 0.0
                },
                {
                    "名次": 2,
                    "股东名称": "中央汇金资产管理有限责任公司",
                    "股东性质": "国家队",
                    "股份类型": "流通A股",
                    "持股数": 98765432,
                    "占总流通股本持股比例": 2.15,
                    "增减": "增持",
                    "变动比率": 0.35
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意:
        1. symbol 参数需要带市场前缀，如 "sh688686" 表示沪市
        2. date 参数为季度末日期，如需2024年三季报则用 "20240930"
    """
    # 参数验证
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串，格式如 sh688686",
            "symbol": symbol or ""
        }

    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": symbol
        }

    # 修正date参数格式：akshare需要YYYYMMDD格式，尝试多种格式兼容
    # 如果date长度不是8位，尝试修正
    date_formats = [date]
    if len(date) == 10 and date.count('-') == 2:
        # 尝试将 YYYY-MM-DD 转换为 YYYYMMDD
        date_formats.append(date.replace('-', ''))
    elif len(date) == 8 and date.isdigit():
        # 已经是YYYYMMDD格式
        pass
    
    logger.info(f"[十大流通股东] 开始查询 symbol={symbol}, date={date}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = None
            last_error = None
            
            # 尝试多种date格式
            for date_fmt in date_formats:
                try:
                    df = ak.stock_gdfx_free_top_10_em(symbol=symbol, date=date_fmt)
                    if df is not None and len(df) > 0:
                        break
                except Exception as fmt_error:
                    last_error = fmt_error
                    continue
            
            if df is None or len(df) == 0:
                logger.warning(f"[十大流通股东] 返回数据为空 symbol={symbol}, date={date}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[十大流通股东]")

            logger.info(f"[十大流通股东] 查询成功 symbol={symbol}, date={date}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询十大流通股东失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[十大流通股东] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[十大流通股东] 最终失败 symbol={symbol}, date={date}, error={error_msg}")
                logger.debug(f"[十大流通股东] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_zh_a_gdhs(date: str) -> Dict[str, Any]:
    """
    股东户数查询接口（东方财富接口）

    接口: stock_zh_a_gdhs
    目标地址: http://data.eastmoney.com/gdhs/
    描述: 东方财富网-数据中心-特色数据-股东户数数据
    限量: 单次获取返回所有数据

    输入参数:
        date: str - 查询日期，可选值：
              "最新" - 获取最新一期股东户数数据
              季度末日期 - 格式为 "YYYYMMDD"，如 "20240930"

    输出参数（返回的 DataFrame 列说明）:
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称
        - 最新价 (float64): 最新价格（注意单位: 元）
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 股东户数-本次 (int64): 本期股东户数
        - 股东户数-上次 (int64): 上期股东户数
        - 股东户数-增减 (int64): 股东户数增减变动
        - 股东户数-增减比例 (float64): 股东户数增减比例（注意单位: %）
        - 区间涨跌幅 (float64): 区间涨跌幅（注意单位: %）
        - 股东户数统计截止日-本次 (object): 本期统计截止日
        - 股东户数统计截止日-上次 (object): 上期统计截止日
        - 户均持股市值 (float64): 户均持股市值
        - 户均持股数量 (float64): 户均持股数量
        - 总市值 (float64): 总市值
        - 总股本 (float64): 总股本
        - 公告日期 (object): 公告发布日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "代码": "600519",
                    "名称": "贵州茅台",
                    "最新价": 1680.0,
                    "涨跌幅": 1.5,
                    "股东户数-本次": 158000,
                    "股东户数-上次": 162000,
                    "股东户数-增减": -4000,
                    "股东户数-增减比例": -2.47,
                    "区间涨跌幅": 5.3,
                    "股东户数统计截止日-本次": "2024-09-30",
                    "股东户数统计截止日-上次": "2024-06-30",
                    "户均持股市值": 285000.0,
                    "户均持股数量": 150.0,
                    "总市值": 2100000000000.0,
                    "总股本": 1256198500.0,
                    "公告日期": "2024-10-25"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "gdhs"  # 固定标识
        }

    注意:
        1. 该接口返回全市场A股股东户数数据，数据量较大
        2. 股东户数减少通常意味着筹码集中，户数增加意味着筹码分散
        3. 可结合区间涨跌幅分析主力动向
    """
    # 参数验证
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期必须为非空字符串，可选值: '最新' 或 'YYYYMMDD' 格式",
            "symbol": "gdhs"
        }

    logger.info(f"[股东户数] 开始查询 date={date}")

    try:
        df = ak.stock_zh_a_gdhs(symbol=date)

        if df.empty:
            logger.warning(f"[股东户数] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gdhs"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[股东户数] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gdhs"
        }

    except Exception as e:
        error_msg = f"查询股东户数失败: {str(e)}"
        logger.error(f"[股东户数] 异常 date={date}, error={error_msg}")
        logger.debug(f"[股东户数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gdhs"
        }


def get_stock_zh_a_gdhs_detail_em(symbol: str) -> Dict[str, Any]:
    """
    股东户数详情查询接口（东方财富接口）

    接口: stock_zh_a_gdhs_detail_em
    目标地址: https://data.eastmoney.com/gdhs/detail/000002.html
    描述: 东方财富网-数据中心-特色数据-股东户数详情
    限量: 单次获取指定 symbol 的所有数据

    输入参数:
        symbol: str - 股票代码，如 "000001"（平安银行），不带市场前缀

    输出参数（返回的 DataFrame 列说明）:
        - 股东户数统计截止日 (object): 统计截止日期
        - 区间涨跌幅 (float64): 区间涨跌幅（注意单位: %）
        - 股东户数-本次 (int64): 本期股东户数
        - 股东户数-上次 (int64): 上期股东户数
        - 股东户数-增减 (int64): 股东户数增减变动
        - 股东户数-增减比例 (float64): 股东户数增减比例（注意单位: %）
        - 户均持股市值 (float64): 户均持股市值
        - 户均持股数量 (float64): 户均持股数量
        - 总市值 (float64): 总市值
        - 总股本 (int64): 总股本
        - 股本变动 (int64): 股本变动数量
        - 股本变动原因 (object): 股本变动原因
        - 股东户数公告日期 (object): 公告发布日期
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股东户数统计截止日": "2024-09-30",
                    "区间涨跌幅": 5.3,
                    "股东户数-本次": 158000,
                    "股东户数-上次": 162000,
                    "股东户数-增减": -4000,
                    "股东户数-增减比例": -2.47,
                    "户均持股市值": 285000.0,
                    "户均持股数量": 150.0,
                    "总市值": 2100000000000.0,
                    "总股本": 1256198500,
                    "股本变动": 0,
                    "股本变动原因": "-",
                    "股东户数公告日期": "2024-10-25",
                    "代码": "600519",
                    "名称": "贵州茅台"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 查询的股票代码
        }

    注意:
        1. 该接口返回单个股票的历史股东户数数据
        2. symbol 参数不需要带市场前缀，直接使用股票代码
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[股东户数详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_zh_a_gdhs_detail_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[股东户数详情] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[股东户数详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询股东户数详情失败: {str(e)}"
        logger.error(f"[股东户数详情] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[股东户数详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_lhb_jgmmtj_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    龙虎榜机构买卖每日统计查询接口（东方财富接口）

    接口: stock_lhb_jgmmtj_em
    目标地址: https://data.eastmoney.com/stock/jgmmtj.html
    描述: 东方财富网-数据中心-龙虎榜单-机构买卖每日统计
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20240417"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20240430"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称
        - 收盘价 (float64): 收盘价格
        - 涨跌幅 (float64): 涨跌幅
        - 买方机构数 (float64): 买方机构数量
        - 卖方机构数 (float64): 卖方机构数量
        - 机构买入总额 (float64): 机构买入总额（注意单位: 元）
        - 机构卖出总额 (float64): 机构卖出总额（注意单位: 元）
        - 机构买入净额 (float64): 机构买入净额（注意单位: 元）
        - 市场总成交额 (float64): 市场总成交额（注意单位: 元）
        - 机构净买额占总成交额比 (float64): 机构净买额占总成交额比例
        - 换手率 (float64): 换手率
        - 流通市值 (float64): 流通市值（注意单位: 亿元）
        - 上榜原因 (object): 上榜原因
        - 上榜日期 (object): 上榜日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000001",
                    "名称": "平安银行",
                    "收盘价": 12.5,
                    "涨跌幅": 10.05,
                    "买方机构数": 3.0,
                    "卖方机构数": 2.0,
                    "机构买入总额": 1234567890.0,
                    "机构卖出总额": 987654321.0,
                    "机构买入净额": 246913569.0,
                    "市场总成交额": 5000000000.0,
                    "机构净买额占总成交额比": 4.94,
                    "换手率": 15.5,
                    "流通市值": 230.5,
                    "上榜原因": "日涨幅偏离值达7%",
                    "上榜日期": "2024-04-25"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "jgmmtj"  # 固定标识
        }

    注意:
        1. 日期参数格式为 "YYYYMMDD"，如 "20240417"
        2. 机构买入净额 = 机构买入总额 - 机构卖出总额
        3. 正值表示机构净买入，负值表示机构净卖出
    """
    # 参数验证
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "jgmmtj"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "jgmmtj"
        }

    logger.info(f"[机构买卖统计] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_jgmmtj_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[机构买卖统计] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "jgmmtj"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[机构买卖统计] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "jgmmtj"
        }

    except Exception as e:
        error_msg = f"查询机构买卖统计失败: {str(e)}"
        logger.error(f"[机构买卖统计] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[机构买卖统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "jgmmtj"
        }


def get_stock_lhb_detail_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    龙虎榜详情查询接口（东方财富接口）

    接口: stock_lhb_detail_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-龙虎榜详情
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20220314"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20220315"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称
        - 上榜日 (object): 上榜日期
        - 解读 (object): 龙虎榜解读信息
        - 收盘价 (float64): 收盘价格
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 龙虎榜净买额 (float64): 龙虎榜净买额（注意单位: 元）
        - 龙虎榜买入额 (float64): 龙虎榜买入额（注意单位: 元）
        - 龙虎榜卖出额 (float64): 龙虎榜卖出额（注意单位: 元）
        - 龙虎榜成交额 (float64): 龙虎榜成交额（注意单位: 元）
        - 市场总成交额 (int64): 市场总成交额（注意单位: 元）
        - 净买额占总成交比 (float64): 净买额占总成交比例（注意单位: %）
        - 成交额占总成交比 (float64): 成交额占总成交比例（注意单位: %）
        - 换手率 (float64): 换手率（注意单位: %）
        - 流通市值 (float64): 流通市值（注意单位: 元）
        - 上榜原因 (object): 上榜原因
        - 上榜后1日 (float64): 上榜后1日涨跌幅（注意单位: %）
        - 上榜后2日 (float64): 上榜后2日涨跌幅（注意单位: %）
        - 上榜后5日 (float64): 上榜后5日涨跌幅（注意单位: %）
        - 上榜后10日 (float64): 上榜后10日涨跌幅（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000001",
                    "名称": "平安银行",
                    "上榜日": "2024-04-25",
                    "解读": "龙虎榜资金净流出",
                    "收盘价": 12.5,
                    "涨跌幅": 10.05,
                    "龙虎榜净买额": -50000000.0,
                    "龙虎榜买入额": 100000000.0,
                    "龙虎榜卖出额": 150000000.0,
                    "龙虎榜成交额": 250000000.0,
                    "市场总成交额": 5000000000,
                    "净买额占总成交比": -1.0,
                    "成交额占总成交比": 5.0,
                    "换手率": 15.5,
                    "流通市值": 2305000000.0,
                    "上榜原因": "日涨幅偏离值达7%",
                    "上榜后1日": 2.5,
                    "上榜后2日": -1.2,
                    "上榜后5日": 5.8,
                    "上榜后10日": 10.3
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_detail"  # 固定标识
        }

    注意:
        1. 日期参数格式为 "YYYYMMDD"，如 "20220314"
        2. 龙虎榜净买额 = 龙虎榜买入额 - 龙虎榜卖出额
        3. 正值表示资金净买入，负值表示资金净卖出
        4. 上榜后N日涨跌幅反映股票后续走势，可用于评估机构选股能力
    """
    # 参数验证
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_detail"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_detail"
        }

    logger.info(f"[龙虎榜详情] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[龙虎榜详情] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_detail"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[龙虎榜详情] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_detail"
        }

    except Exception as e:
        error_msg = f"查询龙虎榜详情失败: {str(e)}"
        logger.error(f"[龙虎榜详情] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[龙虎榜详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_detail"
        }


def get_stock_lhb_stock_statistic_em(symbol: str = "近一月") -> Dict[str, Any]:
    """
    个股上榜统计查询接口（东方财富接口）

    接口: stock_lhb_stock_statistic_em
    目标地址: https://data.eastmoney.com/stock/tradedetail.html
    描述: 东方财富网-数据中心-龙虎榜单-个股上榜统计
    限量: 单次返回所有历史数据

    输入参数:
        symbol: str - 时间范围，可选值：
                    "近一月" - 近一个月数据（默认）
                    "近三月" - 近三个月数据
                    "近六月" - 近六个月数据
                    "近一年" - 近一年数据

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票名称
        - 最近上榜日 (object): 最近一次上榜日期
        - 收盘价 (float64): 最新收盘价
        - 涨跌幅 (float64): 涨跌幅
        - 上榜次数 (int64): 上榜总次数
        - 龙虎榜净买额 (float64): 龙虎榜净买额
        - 龙虎榜买入额 (float64): 龙虎榜买入额
        - 龙虎榜卖出额 (float64): 龙虎榜卖出额
        - 龙虎榜总成交额 (float64): 龙虎榜总成交额
        - 买方机构次数 (int64): 买方机构次数
        - 卖方机构次数 (int64): 卖方机构次数
        - 机构买入净额 (float64): 机构买入净额
        - 机构买入总额 (float64): 机构买入总额
        - 机构卖出总额 (float64): 机构卖出总额
        - 近1个月涨跌幅 (float64): 近1个月涨跌幅
        - 近3个月涨跌幅 (float64): 近3个月涨跌幅
        - 近6个月涨跌幅 (float64): 近6个月涨跌幅
        - 近1年涨跌幅 (float64): 近1年涨跌幅

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000001",
                    "名称": "平安银行",
                    "最近上榜日": "2024-04-25",
                    "收盘价": 12.5,
                    "涨跌幅": 10.05,
                    "上榜次数": 15,
                    "龙虎榜净买额": 500000000.0,
                    "龙虎榜买入额": 1000000000.0,
                    "龙虎榜卖出额": 500000000.0,
                    "龙虎榜总成交额": 1500000000.0,
                    "买方机构次数": 8,
                    "卖方机构次数": 5,
                    "机构买入净额": 300000000.0,
                    "机构买入总额": 600000000.0,
                    "机构卖出总额": 300000000.0,
                    "近1个月涨跌幅": 15.5,
                    "近3个月涨跌幅": 25.3,
                    "近6个月涨跌幅": 30.8,
                    "近1年涨跌幅": 45.2
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_stock_statistic"  # 固定标识
        }
    """
    if not symbol or not isinstance(symbol, str):
        symbol = "近一月"  # 默认值

    valid_symbols = ["近一月", "近三月", "近六月", "近一年"]
    if symbol not in valid_symbols:
        symbol = "近一月"

    logger.info(f"[个股上榜统计] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_lhb_stock_statistic_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[个股上榜统计] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_stock_statistic"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[个股上榜统计] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_stock_statistic"
        }

    except Exception as e:
        error_msg = f"查询个股上榜统计失败: {str(e)}"
        logger.error(f"[个股上榜统计] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[个股上榜统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_stock_statistic"
        }


def get_stock_lhb_hyyyb_em(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    每日活跃营业部查询接口（东方财富接口）

    接口: stock_lhb_hyyyb_em
    目标地址: https://data.eastmoney.com/stock/hyyyb.html
    描述: 东方财富网-数据中心-龙虎榜单-每日活跃营业部
    限量: 单次返回所有历史数据

    输入参数:
        start_date: str - 开始日期，格式为 "YYYYMMDD"，如 "20220311"
        end_date: str - 结束日期，格式为 "YYYYMMDD"，如 "20220315"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 营业部名称 (object): 营业部完整名称
        - 上榜日 (object): 上榜日期
        - 买入个股数 (float64): 买入股票数量
        - 卖出个股数 (float64): 卖出股票数量
        - 买入总金额 (float64): 买入总金额（注意单位: 元）
        - 卖出总金额 (float64): 卖出总金额（注意单位: 元）
        - 总买卖净额 (float64): 总买卖净额（注意单位: 元）
        - 买入股票 (object): 买入的股票列表

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "营业部名称": "招商证券股份有限公司上海牡丹江路证券营业部",
                    "上榜日": "2024-04-25",
                    "买入个股数": 5.0,
                    "卖出个股数": 3.0,
                    "买入总金额": 123456789.0,
                    "卖出总金额": 98765432.0,
                    "总买卖净额": 24691357.0,
                    "买入股票": "平安银行,万科A,格力电器,比亚迪,宁德时代"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_hyyyb"  # 固定标识
        }

    注意:
        1. 日期参数格式为 "YYYYMMDD"
        2. 总买卖净额 = 买入总金额 - 卖出总金额
        3. 可结合营业部历史表现分析游资偏好
    """
    # 参数验证
    if not start_date or not isinstance(start_date, str):
        return {
            "success": False,
            "data": None,
            "error": "开始日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_hyyyb"
        }

    if not end_date or not isinstance(end_date, str):
        return {
            "success": False,
            "data": None,
            "error": "结束日期必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "lhb_hyyyb"
        }

    logger.info(f"[每日活跃营业部] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_lhb_hyyyb_em(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning(f"[每日活跃营业部] 返回数据为空 start_date={start_date}, end_date={end_date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_hyyyb"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[每日活跃营业部] 查询成功 start_date={start_date}, end_date={end_date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_hyyyb"
        }

    except Exception as e:
        error_msg = f"查询每日活跃营业部失败: {str(e)}"
        logger.error(f"[每日活跃营业部] 异常 start_date={start_date}, end_date={end_date}, error={error_msg}")
        logger.debug(f"[每日活跃营业部] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_hyyyb"
        }


def get_stock_lhb_yyb_detail_em(symbol: str) -> Dict[str, Any]:
    """
    营业部详情数据查询接口（东方财富接口）

    接口: stock_lhb_yyb_detail_em
    目标地址: https://data.eastmoney.com/stock/lhb/yyb/10188715.html
    描述: 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细
    限量: 单次返回指定营业部的所有历史数据

    输入参数:
        symbol: str - 营业部代码，如 "10026729"
              可通过 get_stock_lhb_hyyyb_em() 接口获取营业部代码

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 营业部代码 (object): 营业部代码
        - 营业部名称 (object): 营业部完整名称
        - 营业部简称 (object): 营业部简称
        - 交易日期 (object): 交易日期
        - 股票代码 (object): 股票代码
        - 股票名称 (object): 股票名称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 买入金额 (float64): 买入金额（注意单位: 元）
        - 卖出金额 (float64): 卖出金额（注意单位: 元）
        - 净额 (float64): 买卖净额（注意单位: 元）
        - 上榜原因 (object): 上榜原因
        - 1日后涨跌幅 (float64): 1日后涨跌幅（注意单位: %）
        - 2日后涨跌幅 (float64): 2日后涨跌幅（注意单位: %）
        - 3日后涨跌幅 (float64): 3日后涨跌幅（注意单位: %）
        - 5日后涨跌幅 (float64): 5日后涨跌幅（注意单位: %）
        - 10日后涨跌幅 (float64): 10日后涨跌幅（注意单位: %）
        - 20日后涨跌幅 (float64): 20日后涨跌幅（注意单位: %）
        - 30日后涨跌幅 (float64): 30日后涨跌幅（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "营业部代码": "10026729",
                    "营业部名称": "招商证券股份有限公司上海牡丹江路证券营业部",
                    "营业部简称": "招商上海牡丹江路",
                    "交易日期": "2024-04-25",
                    "股票代码": "000001",
                    "股票名称": "平安银行",
                    "涨跌幅": 10.05,
                    "买入金额": 123456789.0,
                    "卖出金额": 0.0,
                    "净额": 123456789.0,
                    "上榜原因": "日涨幅偏离值达7%",
                    "1日后涨跌幅": 2.5,
                    "2日后涨跌幅": -1.2,
                    "3日后涨跌幅": 3.8,
                    "5日后涨跌幅": 5.8,
                    "10日后涨跌幅": 10.3,
                    "20日后涨跌幅": 15.2,
                    "30日后涨跌幅": 20.5
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": symbol  # 营业部代码
        }

    注意:
        1. 营业部代码可通过 get_stock_lhb_hyyyb_em() 接口获取
        2. 净额 = 买入金额 - 卖出金额
        3. 上榜后N日涨跌幅反映该营业部的选股和操盘能力
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "营业部代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[营业部详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_lhb_yyb_detail_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[营业部详情] 返回数据为空 symbol={symbol}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[营业部详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询营业部详情失败: {str(e)}"
        logger.error(f"[营业部详情] 异常 symbol={symbol}, error={error_msg}")
        logger.debug(f"[营业部详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_lh_yyb_most() -> Dict[str, Any]:
    """
    营业部排行-上榜次数最多查询接口（东方财富接口）

    接口: stock_lh_yyb_most
    目标地址: https://data.10jqka.com.cn/market/longhu/
    描述: 龙虎榜-营业部排行-上榜次数最多
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 营业部名称 (object): 营业部完整名称
        - 上榜次数 (int64): 历史总上榜次数
        - 合计动用资金 (object): 合计动用资金（格式为字符串，如 "12.5亿"）
        - 年内上榜次数 (int64): 本年内上榜次数
        - 年内买入股票只数 (int64): 年内买入股票只数
        - 年内3日跟买成功率 (object): 年内3日跟买成功率

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "营业部名称": "东方财富证券股份有限公司拉萨东环路第二证券营业部",
                    "上榜次数": 1250,
                    "合计动用资金": "256.8亿",
                    "年内上榜次数": 85,
                    "年内买入股票只数": 120,
                    "年内3日跟买成功率": "68.5%"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_yyb_most"  # 固定标识
        }

    注意:
        1. 该接口返回全市场营业部排名，按上榜次数降序
        2. "年内3日跟买成功率"反映该营业部选股能力
        3. 知名游资营业部如"温州帮"、"深圳帮"等经常上榜
    """
    logger.info("[营业部排行] 开始查询上榜次数最多的营业部")

    try:
        df = ak.stock_lh_yyb_most()

        if df.empty:
            logger.warning("[营业部排行] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_yyb_most"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[营业部排行] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_yyb_most"
        }

    except Exception as e:
        error_msg = f"查询营业部排行失败: {str(e)}"
        logger.error(f"[营业部排行] 异常 error={error_msg}")
        logger.debug(f"[营业部排行] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_yyb_most"
        }


def get_stock_lh_yyb_capital() -> Dict[str, Any]:
    """
    营业部排行-资金实力最强查询接口（东方财富接口）

    接口: stock_lh_yyb_capital
    目标地址: https://data.10jqka.com.cn/market/longhu/
    描述: 龙虎榜-营业部排行-资金实力最强
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 营业部名称 (object): 营业部完整名称
        - 今日最高操作 (int64): 今日最高操作次数
        - 今日最高金额 (object): 今日最高金额（格式为字符串，如 "5.2亿"）
        - 今日最高买入金额 (object): 今日最高买入金额
        - 累计参与金额 (object): 累计参与金额（格式为字符串）
        - 累计买入金额 (object): 累计买入金额（格式为字符串）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "营业部名称": "东方财富证券股份有限公司拉萨东环路第二证券营业部",
                    "今日最高操作": 15,
                    "今日最高金额": "5.2亿",
                    "今日最高买入金额": "4.8亿",
                    "累计参与金额": "856.3亿",
                    "累计买入金额": "425.6亿"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_yyb_capital"  # 固定标识
        }

    注意:
        1. 该接口反映营业部的资金实力和操作规模
        2. "今日最高金额"反映该营业部当日的最大单笔操作规模
        3. 累计数据可分析营业部的历史交易偏好
    """
    logger.info("[营业部资金实力] 开始查询资金实力最强的营业部")

    try:
        df = ak.stock_lh_yyb_capital()

        if df.empty:
            logger.warning("[营业部资金实力] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_yyb_capital"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[营业部资金实力] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_yyb_capital"
        }

    except Exception as e:
        error_msg = f"查询营业部资金实力失败: {str(e)}"
        logger.error(f"[营业部资金实力] 异常 error={error_msg}")
        logger.debug(f"[营业部资金实力] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_yyb_capital"
        }


def get_stock_lh_yyb_control() -> Dict[str, Any]:
    """
    营业部排行-抱团操作实力查询接口（东方财富接口）

    接口: stock_lh_yyb_control
    目标地址: https://data.10jqka.com.cn/market/longhu/
    描述: 龙虎榜-营业部排行-抱团操作实力
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 营业部名称 (object): 营业部完整名称
        - 携手营业部家数 (int64): 与该营业部合作的营业部数量
        - 年内最佳携手对象 (object): 年内合作最成功的营业部名称
        - 年内最佳携手股票数 (int64): 年内合作买入的股票数量
        - 年内最佳携手成功率 (object): 年内合作成功率（格式为字符串，如 "72.5%"）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "营业部名称": "东方财富证券股份有限公司拉萨东环路第二证券营业部",
                    "携手营业部家数": 85,
                    "年内最佳携手对象": "华鑫证券有限责任公司上海红宝石路证券营业部",
                    "年内最佳携手股票数": 25,
                    "年内最佳携手成功率": "72.5%"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lhb_yyb_control"  # 固定标识
        }

    注意:
        1. "抱团"指多个营业部协同操作同一只股票
        2. 携手营业部家数反映该营业部的合作网络
        3. "年内最佳携手成功率"反映营业部间的协同作战能力
    """
    logger.info("[营业部抱团实力] 开始查询抱团操作实力最强的营业部")

    try:
        df = ak.stock_lh_yyb_control()

        if df.empty:
            logger.warning("[营业部抱团实力] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lhb_yyb_control"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[营业部抱团实力] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lhb_yyb_control"
        }

    except Exception as e:
        error_msg = f"查询营业部抱团实力失败: {str(e)}"
        logger.error(f"[营业部抱团实力] 异常 error={error_msg}")
        logger.debug(f"[营业部抱团实力] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lhb_yyb_control"
        }


def get_stock_repurchase_em() -> Dict[str, Any]:
    """
    股票回购数据查询接口（东方财富接口）

    接口: stock_repurchase_em
    目标地址: https://data.eastmoney.com/gphg/hglist.html
    描述: 东方财富网-数据中心-股票回购-股票回购数据
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 最新价 (float64): 最新价格
        - 计划回购价格区间 (float64): 计划回购价格区间（注意单位: 元）
        - 计划回购数量区间-下限 (float64): 计划回购数量下限（注意单位: 股）
        - 计划回购数量区间-上限 (float64): 计划回购数量上限（注意单位: 股）
        - 占公告前一日总股本比例-下限 (float64): 占总股本比例下限（注意单位: %）
        - 占公告前一日总股本比例-上限 (float64): 占总股本比例上限（注意单位: %）
        - 计划回购金额区间-下限 (float64): 计划回购金额下限（注意单位: 元）
        - 计划回购金额区间-上限 (float64): 计划回购金额上限（注意单位: 元）
        - 回购起始时间 (object): 回购计划起始时间
        - 实施进度 (object): 实施进度状态（如"实施中"、"已完成"等）
        - 已回购股份价格区间-下限 (float64): 已回购价格下限（注意单位: %）
        - 已回购股份价格区间-上限 (float64): 已回购价格上限（注意单位: %）
        - 已回购股份数量 (float64): 已回购股份数量（注意单位: 股）
        - 已回购金额 (float64): 已回购金额（注意单位: 元）
        - 最新公告日期 (object): 最新公告发布日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "最新价": 1680.0,
                    "计划回购价格区间": 1500.0,
                    "计划回购数量区间-下限": 1000000.0,
                    "计划回购数量区间-上限": 2000000.0,
                    "占公告前一日总股本比例-下限": 0.08,
                    "占公告前一日总股本比例-上限": 0.16,
                    "计划回购金额区间-下限": 1500000000.0,
                    "计划回购金额区间-上限": 3000000000.0,
                    "回购起始时间": "2024-01-15",
                    "实施进度": "实施中",
                    "已回购股份价格区间-下限": 1520.0,
                    "已回购股份价格区间-上限": 1650.0,
                    "已回购股份数量": 1500000.0,
                    "已回购金额": 2400000000.0,
                    "最新公告日期": "2024-03-20"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "repurchase"  # 固定标识
        }

    注意:
        1. 股票回购通常被视为利好信号，表明公司认为股价被低估
        2. 实施进度包括：预披露、董事会预案、股东大会通过、实施中、已完成、终止等
        3. 已回购金额占计划上限比例可反映回购执行力度
    """
    logger.info("[股票回购] 开始查询股票回购数据")

    try:
        df = ak.stock_repurchase_em()

        if df.empty:
            logger.warning("[股票回购] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "repurchase"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[股票回购] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "repurchase"
        }

    except Exception as e:
        error_msg = f"查询股票回购数据失败: {str(e)}"
        logger.error(f"[股票回购] 异常 error={error_msg}")
        logger.debug(f"[股票回购] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "repurchase"
        }


def get_stock_dzjy_sctj() -> Dict[str, Any]:
    """
    大宗交易市场统计查询接口（东方财富接口）

    接口: stock_dzjy_sctj
    目标地址: https://data.eastmoney.com/dzjy/dzjy_sctj.html
    描述: 东方财富网-数据中心-大宗交易-市场统计
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 交易日期 (object): 大宗交易日期
        - 上证指数 (float64): 当日上证指数点位
        - 上证指数涨跌幅 (float64): 上证指数涨跌幅（注意单位: %）
        - 大宗交易成交总额 (float64): 大宗交易成交总额（注意单位: 元）
        - 溢价成交总额 (float64): 溢价成交总额（注意单位: 元）
        - 溢价成交总额占比 (float64): 溢价成交总额占比（注意单位: %）
        - 折价成交总额 (float64): 折价成交总额（注意单位: 元）
        - 折价成交总额占比 (float64): 折价成交总额占比（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "交易日期": "2024-03-20",
                    "上证指数": 3080.56,
                    "上证指数涨跌幅": 0.55,
                    "大宗交易成交总额": 123456789.0,
                    "溢价成交总额": 80000000.0,
                    "溢价成交总额占比": 64.82,
                    "折价成交总额": 43456789.0,
                    "折价成交总额占比": 35.18
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "dzjy_sctj"  # 固定标识
        }

    注意:
        1. 大宗交易通常指单笔成交金额较大的股票交易
        2. 溢价成交可能暗示买方看好后市，折价成交可能暗示卖方急于套现
        3. 溢价/折价成交总额占比可反映市场整体情绪
    """
    logger.info("[大宗交易市场统计] 开始查询大宗交易市场统计数据")

    try:
        df = ak.stock_dzjy_sctj()

        if df.empty:
            logger.warning("[大宗交易市场统计] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "dzjy_sctj"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[大宗交易市场统计] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "dzjy_sctj"
        }

    except Exception as e:
        error_msg = f"查询大宗交易市场统计数据失败: {str(e)}"
        logger.error(f"[大宗交易市场统计] 异常 error={error_msg}")
        logger.debug(f"[大宗交易市场统计] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "dzjy_sctj"
        }


def get_stock_margin_account_info() -> Dict[str, Any]:
    """
    两融账户信息查询接口（东方财富接口）

    接口: stock_margin_account_info
    目标地址: https://data.eastmoney.com/rzrq/zhtjday.html
    描述: 东方财富网-数据中心-融资融券-融资融券账户统计-两融账户信息
    限量: 单次返回所有历史数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 日期 (object): 统计日期
        - 融资余额 (float64): 融资余额（注意单位: 亿）
        - 融券余额 (float64): 融券余额（注意单位: 亿）
        - 融资买入额 (float64): 融资买入额（注意单位: 亿）
        - 融券卖出额 (float64): 融券卖出额（注意单位: 亿）
        - 证券公司数量 (float64): 开展融资融券业务的证券公司数量（注意单位: 家）
        - 营业部数量 (float64): 开展融资融券业务的营业部数量（注意单位: 家）
        - 个人投资者数量 (float64): 个人投资者数量（注意单位: 万名）
        - 机构投资者数量 (float64): 机构投资者数量（注意单位: 家）
        - 参与交易的投资者数量 (float64): 当日参与融资融券交易的投资者数量（注意单位: 名）
        - 有融资融券负债的投资者数量 (float64): 有融资融券负债的投资者数量（注意单位: 名）
        - 担保物总价值 (float64): 担保物总价值（注意单位: 亿）
        - 平均维持担保比例 (float64): 平均维持担保比例（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "日期": "2024-03-20",
                    "融资余额": 12345.67,
                    "融券余额": 987.65,
                    "融资买入额": 234.56,
                    "融券卖出额": 45.67,
                    "证券公司数量": 100.0,
                    "营业部数量": 5000.0,
                    "个人投资者数量": 600.0,
                    "机构投资者数量": 1200.0,
                    "参与交易的投资者数量": 50000.0,
                    "有融资融券负债的投资者数量": 30000.0,
                    "担保物总价值": 15000.0,
                    "平均维持担保比例": 180.5
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "margin_account"  # 固定标识
        }

    注意:
        1. 融资余额增加通常被视为市场做多情绪升温
        2. 融券余额增加通常被视为市场做空情绪升温
        3. 维持担保比例低于130%时会触发强制平仓
        4. 两融数据是观察市场杠杆水平和情绪的重要指标
    """
    logger.info("[两融账户信息] 开始查询两融账户统计数据")

    try:
        df = ak.stock_margin_account_info()

        if df.empty:
            logger.warning("[两融账户信息] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_account"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[两融账户信息] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_account"
        }

    except Exception as e:
        error_msg = f"查询两融账户数据失败: {str(e)}"
        logger.error(f"[两融账户信息] 异常 error={error_msg}")
        logger.debug(f"[两融账户信息] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_account"
        }


def get_stock_margin_sse(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    上交所融资融券汇总数据查询接口

    接口: stock_margin_sse
    目标地址: http://www.sse.com.cn/market/othersdata/margin/sum/
    描述: 上海证券交易所-融资融券数据-融资融券汇总数据
    限量: 单次返回指定时间段内的所有历史数据

    输入参数:
        start_date: str, 起始日期，格式为 "YYYYMMDD"，例如 "20010106"
        end_date: str, 结束日期，格式为 "YYYYMMDD"，例如 "20210208"

    输出参数（返回的 DataFrame 列说明）:
        - 信用交易日期 (object): 信用交易日期
        - 融资余额 (int64): 融资余额（注意单位: 元）
        - 融资买入额 (int64): 融资买入额（注意单位: 元）
        - 融券余量 (int64): 融券余量
        - 融券余量金额 (int64): 融券余量金额（注意单位: 元）
        - 融券卖出量 (int64): 融券卖出量
        - 融资融券余额 (int64): 融资融券余额（注意单位: 元）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "信用交易日期": "2024-03-20",
                    "融资余额": 1234567890,
                    "融资买入额": 123456789,
                    "融券余量": 98765432,
                    "融券余量金额": 987654321,
                    "融券卖出量": 12345678,
                    "融资融券余额": 2234567890
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "margin_sse"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20010106" 表示 2001年1月6日
        2. 上交所融资融券数据从2001年开始发布
        3. 融资余额反映市场做多力量，融券余额反映市场做空力量
        4. 融资融券余额 = 融资余额 + 融券余额
    """
    # 验证日期格式
    if not start_date or not isinstance(start_date, str) or len(start_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "start_date 必须为8位字符串，格式为 YYYYMMDD，如 '20010106'",
            "symbol": "margin_sse"
        }
    
    if not end_date or not isinstance(end_date, str) or len(end_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "end_date 必须为8位字符串，格式为 YYYYMMDD，如 '20210208'",
            "symbol": "margin_sse"
        }

    logger.info(f"[上交所融资融券] 开始查询 start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_margin_sse(start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning("[上交所融资融券] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_sse"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[上交所融资融券] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_sse"
        }

    except Exception as e:
        error_msg = f"查询上交所融资融券数据失败: {str(e)}"
        logger.error(f"[上交所融资融券] 异常 error={error_msg}")
        logger.debug(f"[上交所融资融券] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_sse"
        }


def get_stock_margin_detail_szse(date: str) -> Dict[str, Any]:
    """
    深交所融资融券明细数据查询接口

    接口: stock_margin_detail_szse
    目标地址: https://www.szse.cn/disclosure/margin/margin/index.html
    描述: 深证证券交易所-融资融券数据-融资融券交易明细数据
    限量: 单次返回指定 date 的所有历史数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20230925"

    输出参数（返回的 DataFrame 列说明）:
        - 证券代码 (object): 证券代码
        - 证券简称 (object): 证券简称
        - 融资买入额 (int64): 融资买入额（注意单位: 元）
        - 融资余额 (int64): 融资余额（注意单位: 元）
        - 融券卖出量 (int64): 融券卖出量（注意单位: 股/份）
        - 融券余量 (int64): 融券余量（注意单位: 股/份）
        - 融券余额 (int64): 融券余额（注意单位: 元）
        - 融资融券余额 (int64): 融资融券余额（注意单位: 元）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "证券代码": "000001",
                    "证券简称": "平安银行",
                    "融资买入额": 123456789,
                    "融资余额": 1234567890,
                    "融券卖出量": 123456,
                    "融券余量": 987654,
                    "融券余额": 9876543,
                    "融资融券余额": 1332222333
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "margin_detail_szse"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20230925"
        2. 该接口返回指定日期深交所所有融资融券标的的明细数据
        3. 融资余额反映投资者向券商借钱买入股票的总额
        4. 融券余额反映投资者向券商借券卖出的总额
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20230925'",
            "symbol": "margin_detail_szse"
        }

    logger.info(f"[深交所融资融券明细] 开始查询 date={date}")

    try:
        df = ak.stock_margin_detail_szse(date=date)

        if df.empty:
            logger.warning("[深交所融资融券明细] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "margin_detail_szse"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[深交所融资融券明细] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "margin_detail_szse"
        }

    except Exception as e:
        error_msg = f"查询深交所融资融券明细失败: {str(e)}"
        logger.error(f"[深交所融资融券明细] 异常 error={error_msg}")
        logger.debug(f"[深交所融资融券明细] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "margin_detail_szse"
        }


def get_stock_margin_detail_sse(date: str) -> Dict[str, Any]:
    """
    上交所融资融券明细数据查询接口

    接口: stock_margin_detail_sse
    目标地址: http://www.sse.com.cn/market/othersdata/margin/detail/
    描述: 上海证券交易所-融资融券数据-融资融券明细数据
    限量: 单次返回交易日的所有历史数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20230922"

    输出参数（返回的 DataFrame 列说明）:
        - 信用交易日期 (object): 信用交易日期
        - 标的证券代码 (object): 标的证券代码
        - 标的证券简称 (object): 标的证券简称
        - 融资余额 (int64): 融资余额（注意单位: 元）
        - 融资买入额 (int64): 融资买入额（注意单位: 元）
        - 融资偿还额 (int64): 融资偿还额（注意单位: 元）
        - 融券余量 (int64): 融券余量
        - 融券卖出量 (int64): 融券卖出量
        - 融券偿还量 (int64): 融券偿还量

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "信用交易日期": "2023-09-22",
                    "标的证券代码": "600519",
                    "标的证券简称": "贵州茅台",
                    "融资余额": 1234567890,
                    "融资买入额": 123456789,
                    "融资偿还额": 98765432,
                    "融券余量": 987654,
                    "融券卖出量": 123456,
                    "融券偿还量": 98765
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "margin_detail_sse"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20230922"
        2. 该接口返回指定日期上交所所有融资融券标的的明细数据
        3. 融资买入额和融资偿还额的差额反映当日融资净买入情况
        4. 融券卖出量和融券偿还量的差额反映当日融券净卖出情况
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20230922'",
            "symbol": "margin_detail_sse"
        }

    logger.info(f"[上交所融资融券明细] 开始查询 date={date}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_margin_detail_sse(date=date)

            # 修复空轴判断：检查df是否为空或无效
            if df is None:
                logger.warning("[上交所融资融券明细] 返回None")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "margin_detail_sse"
                }
            
            # 检查DataFrame是否为空
            if hasattr(df, 'empty') and df.empty:
                logger.warning("[上交所融资融券明细] 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "margin_detail_sse"
                }
            
            # 检查DataFrame列数（标准为9列）
            expected_columns = 9
            if hasattr(df, 'columns') and df.columns is not None and len(df.columns) < expected_columns:
                logger.warning(f"[上交所融资融券明细] 列数异常: {len(df.columns)}，期望: {expected_columns}")

            data_list = _convert_dataframe_to_list(df, "[上交所融资融券明细]")

            logger.info(f"[上交所融资融券明细] 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "margin_detail_sse"
            }

        except Exception as e:
            error_msg = f"查询上交所融资融券明细失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[上交所融资融券明细] 第{attempt + 1}次失败 date={date}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[上交所融资融券明细] 最终失败 date={date}, error={error_msg}")
                logger.debug(f"[上交所融资融券明细] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "margin_detail_sse"
                }


def get_stock_profit_forecast_ths(symbol: str, indicator: str = "预测年报每股收益") -> Dict[str, Any]:
    """
    同花顺盈利预测数据查询接口

    接口: stock_profit_forecast_ths
    目标地址: http://basic.10jqka.com.cn/new/600519/worth.html
    描述: 同花顺-盈利预测
    限量: 单次返回指定 symbol 和 indicator 的数据

    输入参数:
        symbol: str, 股票代码，例如 "600519"（贵州茅台）
        indicator: str, 指标类型，choice of {
            "预测年报每股收益",
            "预测年报净利润",
            "业绩预测详表-机构",
            "业绩预测详表-详细指标预测"
        }

    输出参数-预测年报每股收益（当 indicator="预测年报每股收益" 时）:
        - 年度 (object): 预测年度
        - 预测机构数 (int64): 参与预测的机构数量
        - 最小值 (float64): 预测最小值
        - 均值 (float64): 预测均值
        - 最大值 (float64): 预测最大值
        - 行业平均数 (float64): 行业平均预测值

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "年度": "2024",
                    "预测机构数": 42,
                    "最小值": 65.5,
                    "均值": 68.8,
                    "最大值": 72.3,
                    "行业平均数": 1.25
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "600519"  # 传入的股票代码
        }

    注意:
        1. 盈利预测数据反映机构对该股票未来业绩的一致预期
        2. 预测机构数越多，说明市场关注度越高，预测可靠性相对较高
        3. 均值是最具参考价值的指标，最大值和最小值可了解预期分歧
        4. 与行业平均数对比可了解该公司在行业中的相对位置
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }
    
    valid_indicators = ["预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", "业绩预测详表-详细指标预测"]
    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"indicator 必须为以下值之一: {valid_indicators}",
            "symbol": symbol
        }

    logger.info(f"[同花顺盈利预测] 开始查询 symbol={symbol}, indicator={indicator}")

    try:
        df = ak.stock_profit_forecast_ths(symbol=symbol, indicator=indicator)

        if df.empty:
            logger.warning("[同花顺盈利预测] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺盈利预测] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺盈利预测失败: {str(e)}"
        logger.error(f"[同花顺盈利预测] 异常 error={error_msg}")
        logger.debug(f"[同花顺盈利预测] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_concept_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    同花顺概念板块指数日频率数据查询接口

    接口: stock_board_concept_index_ths
    目标地址: https://q.10jqka.com.cn/gn/detail/code/301558
    描述: 同花顺-板块-概念板块-指数日频率数据
    限量: 单次返回所有日频指数数据

    输入参数:
        symbol: str, 概念板块名称，例如 "阿里巴巴概念"
                 可通过调用 ak.stock_board_concept_name_ths() 查看同花顺的所有概念名称
        start_date: str, 开始时间，格式为 "YYYYMMDD"，例如 "20200101"
        end_date: str, 结束时间，格式为 "YYYYMMDD"，例如 "20250228"

    输出参数（返回的 DataFrame 列说明）:
        - 日期 (object): 交易日期
        - 开盘价 (float64): 开盘价
        - 最高价 (float64): 最高价
        - 最低价 (float64): 最低价
        - 收盘价 (float64): 收盘价
        - 成交量 (int64): 成交量
        - 成交额 (float64): 成交额

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "日期": "2024-03-20",
                    "开盘价": 1200.5,
                    "最高价": 1235.8,
                    "最低价": 1195.2,
                    "收盘价": 1228.6,
                    "成交量": 12345678,
                    "成交额": 98765432.5
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "阿里巴巴概念"  # 传入的概念板块名称
        }

    注意:
        1. 日期格式必须为 YYYYMMDD
        2. 该接口返回指定概念板块的历史日K线数据
        3. 可用于分析特定概念板块的整体走势
        4. 成交额是该概念板块内所有股票当日成交额的总和
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "概念板块名称必须为非空字符串",
            "symbol": symbol or ""
        }
    
    if not start_date or len(start_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "start_date 必须为8位字符串，格式为 YYYYMMDD",
            "symbol": symbol
        }
    
    if not end_date or len(end_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "end_date 必须为8位字符串，格式为 YYYYMMDD",
            "symbol": symbol
        }

    logger.info(f"[同花顺概念板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_board_concept_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning("[同花顺概念板块指数] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺概念板块指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念板块指数失败: {str(e)}"
        logger.error(f"[同花顺概念板块指数] 异常 error={error_msg}")
        logger.debug(f"[同花顺概念板块指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_industry_summary_ths() -> Dict[str, Any]:
    """
    同花顺行业一览表查询接口

    接口: stock_board_industry_summary_ths
    目标地址: https://q.10jqka.com.cn/thshy/
    描述: 同花顺-同花顺行业一览表
    限量: 单次返回当前时刻同花顺行业一览表

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 板块 (object): 行业板块名称
        - 涨跌幅 (object): 涨跌幅（注意单位: %）
        - 总成交量 (float64): 总成交量（注意单位: 万手）
        - 总成交额 (float64): 总成交额（注意单位: 亿元）
        - 净流入 (float64): 净流入金额（注意单位: 亿元）
        - 上涨家数 (float64): 上涨股票数量
        - 下跌家数 (float64): 下跌股票数量
        - 均价 (float64): 加权平均价格
        - 领涨股 (float64): 领涨股代码
        - 领涨股-最新价 (object): 领涨股最新价
        - 领涨股-涨跌幅 (object): 领涨股涨跌幅（注意单位: %）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "板块": "银行",
                    "涨跌幅": "1.25",
                    "总成交量": 1234.56,
                    "总成交额": 567.89,
                    "净流入": 12.34,
                    "上涨家数": 35.0,
                    "下跌家数": 5.0,
                    "均价": 5.67,
                    "领涨股": 601988,
                    "领涨股-最新价": "4.56",
                    "领涨股-涨跌幅": "5.67"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "industry_summary"  # 固定标识
        }

    注意:
        1. 该接口返回当前时刻所有同花顺行业板块的实时行情
        2. 净流入 = 上涨板块流入 - 下跌板块流出，正值表示资金净流入
        3. 领涨股反映该行业板块中最强势的股票
        4. 可用于追踪热点行业轮动
    """
    logger.info("[同花顺行业一览表] 开始查询同花顺行业一览表")

    try:
        df = ak.stock_board_industry_summary_ths()

        if df.empty:
            logger.warning("[同花顺行业一览表] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "industry_summary"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺行业一览表] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "industry_summary"
        }

    except Exception as e:
        error_msg = f"查询同花顺行业一览表失败: {str(e)}"
        logger.error(f"[同花顺行业一览表] 异常 error={error_msg}")
        logger.debug(f"[同花顺行业一览表] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "industry_summary"
        }


def get_stock_board_concept_info_ths(symbol: str) -> Dict[str, Any]:
    """
    同花顺概念板块简介查询接口

    接口: stock_board_concept_info_ths
    目标地址: http://q.10jqka.com.cn/gn/detail/code/301558/
    描述: 同花顺-板块-概念板块-板块简介
    限量: 单次返回所有数据

    输入参数:
        symbol: str, 概念板块名称，例如 "阿里巴巴概念"
                 可通过调用 ak.stock_board_concept_name_ths() 查看同花顺的所有概念名称

    输出参数（返回的 DataFrame 列说明）:
        - 项目 (object): 简介项目名称
        - 值 (float64): 简介项目内容

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "项目": "板块名称",
                    "值": "阿里巴巴概念"
                },
                {
                    "项目": "成分股数量",
                    "值": 86.0
                },
                {
                    "项目": "主要上市公司",
                    "值": "..."
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "阿里巴巴概念"  # 传入的概念板块名称
        }

    注意:
        1. 该接口返回指定概念板块的详细信息
        2. 包含板块简介、成分股数量、主要上市公司等内容
        3. 可配合概念板块指数使用，全面了解板块情况
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "概念板块名称必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[同花顺概念板块简介] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_board_concept_info_ths(symbol=symbol)

        if df.empty:
            logger.warning("[同花顺概念板块简介] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺概念板块简介] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念板块简介失败: {str(e)}"
        logger.error(f"[同花顺概念板块简介] 异常 error={error_msg}")
        logger.debug(f"[同花顺概念板块简介] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_industry_index_ths(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    同花顺行业板块指数日频率数据查询接口

    接口: stock_board_industry_index_ths
    目标地址: https://q.10jqka.com.cn/thshy/detail/code/881270/
    描述: 同花顺-板块-行业板块-指数日频率数据
    限量: 单次返回所有日频指数数据

    输入参数:
        symbol: str, 行业板块名称，例如 "元件"
                 可通过调用 ak.stock_board_industry_name_ths() 查看同花顺的所有行业名称
        start_date: str, 开始时间，格式为 "YYYYMMDD"，例如 "20200101"
        end_date: str, 结束时间，格式为 "YYYYMMDD"，例如 "20211027"

    输出参数（返回的 DataFrame 列说明）:
        - 日期 (object): 交易日期
        - 开盘价 (float64): 开盘价
        - 最高价 (float64): 最高价
        - 最低价 (float64): 最低价
        - 收盘价 (float64): 收盘价
        - 成交量 (int64): 成交量
        - 成交额 (float64): 成交额

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "日期": "2024-03-20",
                    "开盘价": 1200.5,
                    "最高价": 1235.8,
                    "最低价": 1195.2,
                    "收盘价": 1228.6,
                    "成交量": 12345678,
                    "成交额": 98765432.5
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "元件"  # 传入的行业板块名称
        }

    注意:
        1. 日期格式必须为 YYYYMMDD
        2. 该接口返回指定行业板块的历史日K线数据
        3. 可用于分析特定行业板块的整体走势
        4. 与概念板块指数接口配合，可全面分析各类板块行情
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "行业板块名称必须为非空字符串",
            "symbol": symbol or ""
        }
    
    if not start_date or len(start_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "start_date 必须为8位字符串，格式为 YYYYMMDD",
            "symbol": symbol
        }
    
    if not end_date or len(end_date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "end_date 必须为8位字符串，格式为 YYYYMMDD",
            "symbol": symbol
        }

    logger.info(f"[同花顺行业板块指数] 开始查询 symbol={symbol}, start_date={start_date}, end_date={end_date}")

    try:
        df = ak.stock_board_industry_index_ths(symbol=symbol, start_date=start_date, end_date=end_date)

        if df.empty:
            logger.warning("[同花顺行业板块指数] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺行业板块指数] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺行业板块指数失败: {str(e)}"
        logger.error(f"[同花顺行业板块指数] 异常 error={error_msg}")
        logger.debug(f"[同花顺行业板块指数] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_follow_xq(symbol: str = "最热门") -> Dict[str, Any]:
    """
    雪球关注排行榜查询接口

    接口: stock_hot_follow_xq
    目标地址: https://xueqiu.com/hq
    描述: 雪球-沪深股市-热度排行榜-关注排行榜
    限量: 单次返回指定 symbol 的排行数据

    输入参数:
        symbol: str, 排行类型，choice of {"本周新增", "最热门"}
               - "本周新增": 本周新增关注最多的股票排行
               - "最热门": 累计关注最多的股票排行

    输出参数（返回的 DataFrame 列说明）:
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 关注 (float64): 关注数量
        - 最新价 (float64): 最新价格（注意单位: 元）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "股票代码": "000665",
                    "股票简称": "湖北广电",
                    "关注": 123456.0,
                    "最新价": 8.56
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "最热门"  # 传入的排行类型
        }

    注意:
        1. 该接口反映雪球用户对股票的关注程度
        2. "本周新增"可反映短期市场热点
        3. "最热门"可反映长期市场关注度高的股票
        4. 关注度高的股票通常具有较高的市场流动性和波动性
    """
    valid_symbols = ["本周新增", "最热门"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"symbol 必须为以下值之一: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[雪球关注排行榜] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_follow_xq(symbol=symbol)

        if df.empty:
            logger.warning("[雪球关注排行榜] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[雪球关注排行榜] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询雪球关注排行榜失败: {str(e)}"
        logger.error(f"[雪球关注排行榜] 异常 error={error_msg}")
        logger.debug(f"[雪球关注排行榜] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_rank_detail_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富股票热度历史趋势及粉丝特征查询接口

    接口: stock_hot_rank_detail_em
    目标地址: http://guba.eastmoney.com/rank/stock?code=000665
    描述: 东方财富网-股票热度-历史趋势及粉丝特征
    限量: 单次返回指定 symbol 的股票近期历史数据

    输入参数:
        symbol: str, 股票代码，需带市场前缀，例如 "SZ000665"（湖北广电）
                SZ表示深圳，SH表示上海

    输出参数（返回的 DataFrame 列说明）:
        - 时间 (object): 数据时间
        - 排名 (int64): 人气排名
        - 证券代码 (object): 证券代码
        - 新晋粉丝 (float64): 当期新晋粉丝数量
        - 铁杆粉丝 (float64): 铁杆粉丝数量

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "时间": "2024-03-20",
                    "排名": 1,
                    "证券代码": "SZ000665",
                    "新晋粉丝": 12345.0,
                    "铁杆粉丝": 98765.0
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "SZ000665"  # 传入的股票代码
        }

    注意:
        1. 股票代码必须带市场前缀，SZ表示深圳，SH表示上海
        2. 新晋粉丝反映该股吸引新投资者的能力
        3. 铁杆粉丝反映核心投资者的忠诚度
        4. 排名变化可用于判断股票热度趋势
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串（需带市场前缀，如 SZ000665）",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富热度详情] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_rank_detail_em(symbol=symbol)

        if df.empty:
            logger.warning("[东方财富热度详情] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富热度详情] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富热度详情失败: {str(e)}"
        logger.error(f"[东方财富热度详情] 异常 error={error_msg}")
        logger.debug(f"[东方财富热度详情] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_hot_keyword_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富个股人气榜热门关键词查询接口

    接口: stock_hot_keyword_em
    目标地址: http://guba.eastmoney.com/rank/stock?code=000665
    描述: 东方财富-个股人气榜-热门关键词
    限量: 单次返回指定 symbol 的最近交易日时点数据

    输入参数:
        symbol: str, 股票代码，需带市场前缀，例如 "SZ000665"（湖北广电）
                SZ表示深圳，SH表示上海

    输出参数（返回的 DataFrame 列说明）:
        - 时间 (object): 数据时间
        - 股票代码 (object): 股票代码
        - 概念名称 (object): 相关概念名称
        - 概念代码 (object): 相关概念代码
        - 热度 (int64): 热度值

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "时间": "2024-03-20",
                    "股票代码": "SZ000665",
                    "概念名称": "元宇宙",
                    "概念代码": "BK1000",
                    "热度": 123456
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "SZ000665"  # 传入的股票代码
        }

    注意:
        1. 股票代码必须带市场前缀，SZ表示深圳，SH表示上海
        2. 该接口返回与该股票相关的热门概念关键词
        3. 热度值反映该概念在当前市场的受关注程度
        4. 可用于分析个股与热门概念的关联度
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串（需带市场前缀，如 SZ000665）",
            "symbol": symbol or ""
        }

    logger.info(f"[东方财富热门关键词] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_hot_keyword_em(symbol=symbol)

        if df.empty:
            logger.warning("[东方财富热门关键词] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富热门关键词] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富热门关键词失败: {str(e)}"
        logger.error(f"[东方财富热门关键词] 异常 error={error_msg}")
        logger.debug(f"[东方财富热门关键词] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_changes_em(symbol: str) -> Dict[str, Any]:
    """
    东方财富盘口异动数据查询接口

    接口: stock_changes_em
    目标地址: http://quote.eastmoney.com/changes/
    描述: 东方财富-行情中心-盘口异动数据
    限量: 单次指定 symbol 的最近交易日的盘口异动数据

    输入参数:
        symbol: str, 异动类型，choice of {
            "火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板",
            "有大买盘", "竞价上涨", "高开5日线", "向上缺口", "60日新高",
            "60日大幅上涨", "加速下跌", "高台跳水", "大笔卖出", "封跌停板",
            "打开涨停板", "有大卖盘", "竞价下跌", "低开5日线", "向下缺口",
            "60日新低", "60日大幅下跌"
        }

    输出参数（返回的 DataFrame 列说明）:
        - 时间 (object): 异动发生时间
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 板块 (object): 所属板块
        - 相关信息 (object): 异动相关信息（注意: 不同的 symbol 单位不同）

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "时间": "10:25:32",
                    "代码": "000665",
                    "名称": "湖北广电",
                    "板块": "元宇宙",
                    "相关信息": "成交量: 125678手"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "大笔买入"  # 传入的异动类型
        }

    注意:
        1. 该接口反映盘口出现的各类异动情况
        2. 火箭发射、封涨停板等属于利好信号
        3. 高台跳水、封跌停板等属于利空信号
        4. 60日新高/新低反映股票的中长期趋势变化
    """
    valid_symbols = [
        "火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板",
        "有大买盘", "竞价上涨", "高开5日线", "向上缺口", "60日新高",
        "60日大幅上涨", "加速下跌", "高台跳水", "大笔卖出", "封跌停板",
        "打开涨停板", "有大卖盘", "竞价下跌", "低开5日线", "向下缺口",
        "60日新低", "60日大幅下跌"
    ]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"symbol 必须为以下值之一: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[盘口异动] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_changes_em(symbol=symbol)

        if df.empty:
            logger.warning("[盘口异动] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[盘口异动] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询盘口异动失败: {str(e)}"
        logger.error(f"[盘口异动] 异常 error={error_msg}")
        logger.debug(f"[盘口异动] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_board_change_em() -> Dict[str, Any]:
    """
    东方财富板块异动详情查询接口

    接口: stock_board_change_em
    目标地址: https://quote.eastmoney.com/changes/
    描述: 东方财富-行情中心-当日板块异动详情
    限量: 返回最近交易日的数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 板块名称 (object): 板块名称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 主力净流入 (float64): 主力净流入金额（注意单位: 万元）
        - 板块异动总次数 (float64): 当日板块异动总次数
        - 板块异动最频繁个股及所属类型-股票代码 (object): 最频繁异动个股代码
        - 板块异动最频繁个股及所属类型-股票名称 (object): 最频繁异动个股名称
        - 板块异动最频繁个股及所属类型-买卖方向 (object): 买卖方向
        - 板块具体异动类型列表及出现次数 (object): 具体异动类型及次数

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "板块名称": "半导体",
                    "涨跌幅": 3.25,
                    "主力净流入": 12345.67,
                    "板块异动总次数": 15.0,
                    "板块异动最频繁个股及所属类型-股票代码": "600584",
                    "板块异动最频繁个股及所属类型-股票名称": "长电科技",
                    "板块异动最频繁个股及所属类型-买卖方向": "买入",
                    "板块具体异动类型列表及出现次数": "大笔买入: 5次, 封涨停板: 2次"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "board_change"  # 固定标识
        }

    注意:
        1. 该接口返回当日各板块的异动汇总情况
        2. 主力净流入为正则表示资金净流入，为负则表示资金净流出
        3. 板块异动总次数反映该板块的活跃程度
        4. 可用于追踪当日市场热点板块
    """
    logger.info("[板块异动详情] 开始查询板块异动详情数据")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_board_change_em()

            # 修复空数据判断：使用len()检查而非布尔值判断
            if df is None or len(df) == 0:
                logger.warning("[板块异动详情] 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "board_change"
                }

            data_list = _convert_dataframe_to_list(df, "[板块异动详情]")

            logger.info(f"[板块异动详情] 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "board_change"
            }

        except Exception as e:
            error_msg = f"查询板块异动详情失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[板块异动详情] 第{attempt + 1}次失败，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[板块异动详情] 最终失败 error={error_msg}")
                logger.debug(f"[板块异动详情] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "board_change"
                }


def get_stock_zt_pool_em(date: str) -> Dict[str, Any]:
    """
    东方财富涨停股池查询接口

    接口: stock_zt_pool_em
    目标地址: https://quote.eastmoney.com/ztb/detail#type=ztgc
    描述: 东方财富网-行情中心-涨停板行情-涨停股池
    限量: 单次返回指定 date 的涨停股池数据；该接口只能获取近期的数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20241008"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 最新价 (float64): 最新价格
        - 成交额 (int64): 成交额
        - 流通市值 (float64): 流通市值
        - 总市值 (float64): 总市值
        - 换手率 (float64): 换手率（注意单位: %）
        - 封板资金 (int64): 封板资金
        - 首次封板时间 (object): 首次封板时间（注意格式: 09:25:00）
        - 最后封板时间 (object): 最后封板时间（注意格式: 09:25:00）
        - 炸板次数 (int64): 炸板次数
        - 涨停统计 (object): 涨停统计信息
        - 连板数 (int64): 连板数（注意格式: 1 为首板）
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000665",
                    "名称": "湖北广电",
                    "涨跌幅": 10.05,
                    "最新价": 9.87,
                    "成交额": 123456789,
                    "流通市值": 987654321.0,
                    "总市值": 1234567890.0,
                    "换手率": 15.67,
                    "封板资金": 12345678,
                    "首次封板时间": "09:25:00",
                    "最后封板时间": "09:25:00",
                    "炸板次数": 0,
                    "涨停统计": "连续3天涨停",
                    "连板数": 3,
                    "所属行业": "文化传媒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zt_pool"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20241008"
        2. 该接口只能获取近期的涨停数据，历史数据可能无法获取
        3. 涨停股池是短线交易者关注的重要数据
        4. 连板数反映股票的连板能力，连板越多越强势
        5. 炸板次数反映涨停板稳定性，炸板次数多说明抛压较大
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20241008'",
            "symbol": "zt_pool"
        }

    logger.info(f"[涨停股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_em(date=date)

        if df.empty:
            logger.warning("[涨停股池] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[涨停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool"
        }

    except Exception as e:
        error_msg = f"查询涨停股池失败: {str(e)}"
        logger.error(f"[涨停股池] 异常 error={error_msg}")
        logger.debug(f"[涨停股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool"
        }


def get_stock_zt_pool_previous_em(date: str) -> Dict[str, Any]:
    """
    东方财富昨日涨停股池查询接口

    接口: stock_zt_pool_previous_em
    目标地址: https://quote.eastmoney.com/ztb/detail#type=zrzt
    描述: 东方财富网-行情中心-涨停板行情-昨日涨停股池
    限量: 单次返回指定 date 的昨日涨停股池数据；该接口只能获取近期的数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20240415"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int32): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 最新价 (int64): 最新价格
        - 涨停价 (int64): 涨停价格
        - 成交额 (int64): 成交额
        - 流通市值 (float64): 流通市值
        - 总市值 (float64): 总市值
        - 换手率 (float64): 换手率（注意单位: %）
        - 涨速 (float64): 涨速（注意单位: %）
        - 振幅 (float64): 振幅（注意单位: %）
        - 昨日封板时间 (int64): 昨日封板时间（注意格式: 09:25:00）
        - 昨日连板数 (int64): 昨日连板数（注意格式: 1 为首板）
        - 涨停统计 (object): 涨停统计信息
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000665",
                    "名称": "湖北广电",
                    "涨跌幅": 5.23,
                    "最新价": 10.38,
                    "涨停价": 9.87,
                    "成交额": 234567890,
                    "流通市值": 1234567890.0,
                    "总市值": 3456789012.0,
                    "换手率": 18.45,
                    "涨速": 2.35,
                    "振幅": 8.67,
                    "昨日封板时间": 92500,
                    "昨日连板数": 2,
                    "涨停统计": "昨日涨停",
                    "所属行业": "文化传媒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zt_pool_previous"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20240415"
        2. 该接口返回昨日涨停股的今日表现情况
        3. 可用于观察涨停股的接力情况
        4. 高开高走表示强势延续，高开低走则需警惕
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20240415'",
            "symbol": "zt_pool_previous"
        }

    logger.info(f"[昨日涨停股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_previous_em(date=date)

        if df.empty:
            logger.warning("[昨日涨停股池] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool_previous"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[昨日涨停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool_previous"
        }

    except Exception as e:
        error_msg = f"查询昨日涨停股池失败: {str(e)}"
        logger.error(f"[昨日涨停股池] 异常 error={error_msg}")
        logger.debug(f"[昨日涨停股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool_previous"
        }


def get_stock_zt_pool_strong_em(date: str) -> Dict[str, Any]:
    """
    东方财富强势股池查询接口

    接口: stock_zt_pool_strong_em
    目标地址: https://quote.eastmoney.com/ztb/detail#type=qsgc
    描述: 东方财富网-行情中心-涨停板行情-强势股池
    限量: 单次返回指定 date 的强势股池数据；该接口只能获取近期的数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20241009"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 最新价 (float64): 最新价格
        - 涨停价 (float64): 涨停价格
        - 成交额 (int64): 成交额
        - 流通市值 (float64): 流通市值
        - 总市值 (float64): 总市值
        - 换手率 (float64): 换手率（注意单位: %）
        - 涨速 (float64): 涨速（注意单位: %）
        - 是否新高 (object): 是否创历史新高
        - 量比 (float64): 量比
        - 涨停统计 (object): 涨停统计信息
        - 入选理由 (object): 入围强势股池的理由
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000665",
                    "名称": "湖北广电",
                    "涨跌幅": 9.97,
                    "最新价": 10.58,
                    "涨停价": 10.58,
                    "成交额": 345678901,
                    "流通市值": 2345678901.0,
                    "总市值": 5678901234.0,
                    "换手率": 22.34,
                    "涨速": 3.45,
                    "是否新高": "是",
                    "量比": 2.35,
                    "涨停统计": "涨停",
                    "入选理由": "股价创历史新高",
                    "所属行业": "文化传媒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zt_pool_strong"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20241009"
        2. 强势股池反映当日表现强势的股票
        3. 入选理由说明股票强势的具体原因
        4. 是否新高反映股票是否创历史新高
        5. 强势股通常是市场热点和资金追逐的对象
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20241009'",
            "symbol": "zt_pool_strong"
        }

    logger.info(f"[强势股池] 开始查询 date={date}")

    try:
        df = ak.stock_zt_pool_strong_em(date=date)

        if df.empty:
            logger.warning("[强势股池] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "zt_pool_strong"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[强势股池] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "zt_pool_strong"
        }

    except Exception as e:
        error_msg = f"查询强势股池失败: {str(e)}"
        logger.error(f"[强势股池] 异常 error={error_msg}")
        logger.debug(f"[强势股池] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "zt_pool_strong"
        }


def get_stock_zt_pool_zbgc_em(date: str) -> Dict[str, Any]:
    """
    东方财富炸板股池查询接口

    接口: stock_zt_pool_zbgc_em
    目标地址: https://quote.eastmoney.com/ztb/detail#type=zbgc
    描述: 东方财富网-行情中心-涨停板行情-炸板股池
    限量: 单次返回指定 date 的炸板股池数据；该接口只能获取近期的数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20241011"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int32): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 最新价 (float64): 最新价格
        - 涨停价 (float64): 涨停价格
        - 成交额 (int64): 成交额
        - 流通市值 (float64): 流通市值
        - 总市值 (float64): 总市值
        - 换手率 (float64): 换手率（注意单位: %）
        - 涨速 (int64): 涨速
        - 首次封板时间 (object): 首次封板时间（注意格式: 09:25:00）
        - 炸板次数 (int64): 炸板次数
        - 涨停统计 (int64): 涨停统计信息
        - 振幅 (object): 振幅
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000665",
                    "名称": "湖北广电",
                    "涨跌幅": 5.23,
                    "最新价": 10.38,
                    "涨停价": 9.87,
                    "成交额": 234567890,
                    "流通市值": 1234567890.0,
                    "总市值": 3456789012.0,
                    "换手率": 18.45,
                    "涨速": 2,
                    "首次封板时间": "09:25:00",
                    "炸板次数": 3,
                    "涨停统计": 1,
                    "振幅": "10.25%",
                    "所属行业": "文化传媒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zt_pool_zbgc"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20241011"
        2. 炸板股是指曾经涨停但随后打开涨停板的股票
        3. 炸板次数反映涨停板的不稳定性
        4. 炸板后能否回封是判断股票强弱的重要指标
        5. 炸板股通常意味着上方抛压较大
        6. 该接口只能获取近30个交易日的数据，超过会自动截断
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20241011'",
            "symbol": "zt_pool_zbgc"
        }

    # 自动校验日期：超过30天限制时自动截断为最近30天
    from datetime import datetime, timedelta
    try:
        input_date = datetime.strptime(date, '%Y%m%d')
        today = datetime.now()
        days_diff = (today - input_date).days
        
        if days_diff > 30:
            adjusted_date = (today - timedelta(days=30)).strftime('%Y%m%d')
            logger.warning(f"[炸板股池] 日期超过30天限制 {date}，自动截断为 {adjusted_date}")
            date = adjusted_date
    except ValueError:
        return {
            "success": False,
            "data": None,
            "error": f"日期格式错误: {date}，应为 YYYYMMDD 格式",
            "symbol": "zt_pool_zbgc"
        }

    logger.info(f"[炸板股池] 开始查询 date={date}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_zt_pool_zbgc_em(date=date)

            if df is None or len(df) == 0:
                logger.warning(f"[炸板股池] 返回数据为空 date={date}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "zt_pool_zbgc"
                }

            data_list = _convert_dataframe_to_list(df, "[炸板股池]")

            logger.info(f"[炸板股池] 查询成功 date={date}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "zt_pool_zbgc"
            }

        except Exception as e:
            error_msg = f"查询炸板股池失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[炸板股池] 第{attempt + 1}次失败 date={date}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[炸板股池] 最终失败 date={date}, error={error_msg}")
                logger.debug(f"[炸板股池] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "zt_pool_zbgc"
                }


def get_stock_zt_pool_dtgc_em(date: str) -> Dict[str, Any]:
    """
    东方财富跌停股池查询接口

    接口: stock_zt_pool_dtgc_em
    目标地址: https://quote.eastmoney.com/ztb/detail#type=zbgc
    描述: 东方财富网-行情中心-涨停板行情-跌停股池
    限量: 单次返回指定 date 的跌停股池数据；该接口只能获取近期的数据

    输入参数:
        date: str, 日期，格式为 "YYYYMMDD"，例如 "20241011"

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 代码 (object): 股票代码
        - 名称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 最新价 (float64): 最新价格
        - 成交额 (int64): 成交额
        - 流通市值 (float64): 流通市值
        - 总市值 (float64): 总市值
        - 动态市盈率 (float64): 动态市盈率
        - 换手率 (float64): 换手率（注意单位: %）
        - 封单资金 (int64): 跌停封单资金
        - 最后封板时间 (object): 最后封板时间（注意格式: 09:25:00）
        - 板上成交额 (int64): 板上成交额
        - 连续跌停 (int64): 连续跌停天数
        - 开板次数 (int64): 开板次数
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "代码": "000665",
                    "名称": "湖北广电",
                    "涨跌幅": -10.05,
                    "最新价": 8.88,
                    "成交额": 123456789,
                    "流通市值": 987654321.0,
                    "总市值": 2345678901.0,
                    "动态市盈率": 25.6,
                    "换手率": 5.23,
                    "封单资金": 9876543,
                    "最后封板时间": "09:35:00",
                    "板上成交额": 12345678,
                    "连续跌停": 1,
                    "开板次数": 2,
                    "所属行业": "文化传媒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "zt_pool_dtgc"  # 固定标识
        }

    注意:
        1. 日期格式必须为 YYYYMMDD，如 "20241011"
        2. 跌停股池反映当日跌停的股票
        3. 连续跌停天数反映股票的弱势程度
        4. 封单资金反映空方力量，封单越大跌停越稳
        5. 开板次数反映是否有资金尝试撬板
        6. 该接口只能获取近30个交易日的数据，超过会自动截断
    """
    if not date or not isinstance(date, str) or len(date) != 8:
        return {
            "success": False,
            "data": None,
            "error": "date 必须为8位字符串，格式为 YYYYMMDD，如 '20241011'",
            "symbol": "zt_pool_dtgc"
        }

    # 自动校验日期：超过30天限制时自动截断为最近30天
    from datetime import datetime, timedelta
    try:
        input_date = datetime.strptime(date, '%Y%m%d')
        today = datetime.now()
        days_diff = (today - input_date).days
        
        if days_diff > 30:
            adjusted_date = (today - timedelta(days=30)).strftime('%Y%m%d')
            logger.warning(f"[跌停股池] 日期超过30天限制 {date}，自动截断为 {adjusted_date}")
            date = adjusted_date
    except ValueError:
        return {
            "success": False,
            "data": None,
            "error": f"日期格式错误: {date}，应为 YYYYMMDD 格式",
            "symbol": "zt_pool_dtgc"
        }

    logger.info(f"[跌停股池] 开始查询 date={date}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_zt_pool_dtgc_em(date=date)

            if df is None or len(df) == 0:
                logger.warning(f"[跌停股池] 返回数据为空 date={date}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": "zt_pool_dtgc"
                }

            data_list = _convert_dataframe_to_list(df, "[跌停股池]")

            logger.info(f"[跌停股池] 查询成功 date={date}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": "zt_pool_dtgc"
            }

        except Exception as e:
            error_msg = f"查询跌停股池失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[跌停股池] 第{attempt + 1}次失败 date={date}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[跌停股池] 最终失败 date={date}, error={error_msg}")
                logger.debug(f"[跌停股池] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": "zt_pool_dtgc"
                }


def get_stock_rank_cxg_ths(symbol: str = "创月新高") -> Dict[str, Any]:
    """
    同花顺技术指标-创新高数据查询接口

    接口: stock_rank_cxg_ths
    目标地址: https://data.10jqka.com.cn/rank/cxg/
    描述: 同花顺-数据中心-技术选股-创新高
    限量: 单次指定 symbol 的所有数据

    输入参数:
        symbol: str, 创新高类型，choice of {
            "创月新高",   # 创一个月内新高
            "半年新高",   # 创半年内新高
            "一年新高",   # 创一年内新高
            "历史新高"    # 创历史新高
        }

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 涨跌幅 (float64): 涨跌幅（注意单位: %）
        - 换手率 (float64): 换手率（注意单位: %）
        - 最新价 (float64): 最新价格（注意单位: 元）
        - 前期高点 (float64): 前期高点价格
        - 前期高点日期 (object): 前期高点日期

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "涨跌幅": 3.25,
                    "换手率": 0.85,
                    "最新价": 1850.5,
                    "前期高点": 1800.0,
                    "前期高点日期": "2024-02-15"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "创月新高"  # 传入的创新高类型
        }

    注意:
        1. 创新高股票通常代表市场对其价值的重新评估
        2. 创历史新高表示股票进入新的价值区间
        3. 创月新高/半年新高/一年新高反映不同时间维度的突破
        4. 创新高后回踩确认是较好的介入时机
        5. 需结合换手率和成交量判断突破的有效性
    """
    valid_symbols = ["创月新高", "半年新高", "一年新高", "历史新高"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"symbol 必须为以下值之一: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺创新高] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_rank_cxg_ths(symbol=symbol)

            if df is None or df.empty:
                logger.warning(f"[同花顺创新高] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            # 动态适配列数处理 - 同花顺接口可能返回不同列数
            data_list = []
            
            # 定义标准列名（如果接口返回额外列则忽略）
            standard_columns = ['序号', '股票代码', '股票简称', '涨跌幅', '换手率', 
                               '最新价', '前期高点', '前期高点日期']
            
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    # 只处理标准列，忽略额外列
                    if col not in standard_columns:
                        logger.debug(f"[同花顺创新高] 忽略额外列: {col}")
                        continue
                    
                    value = row[col]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    elif pd.isna(value):
                        value = None
                    elif isinstance(value, (int, float, str, bool)):
                        pass
                    else:
                        value = str(value)
                    record[col] = value
                
                # 只添加有数据的记录
                if record:
                    data_list.append(record)

            logger.info(f"[同花顺创新高] 查询成功 symbol={symbol}, 数据条数={len(data_list)}, 列数={len(df.columns)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询同花顺创新高失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[同花顺创新高] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[同花顺创新高] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[同花顺创新高] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_rank_lxsz_ths() -> Dict[str, Any]:
    """
    同花顺技术选股-连续上涨数据查询接口

    接口: stock_rank_lxsz_ths
    目标地址: https://data.10jqka.com.cn/rank/lxsz/
    描述: 同花顺-数据中心-技术选股-连续上涨
    限量: 单次返回所有数据

    输入参数:
        无（该接口无需输入参数）

    输出参数（返回的 DataFrame 列说明）:
        - 序号 (int64): 序号
        - 股票代码 (object): 股票代码
        - 股票简称 (object): 股票简称
        - 收盘价 (float64): 收盘价（注意单位: 元）
        - 最高价 (float64): 最高价（注意单位: 元）
        - 最低价 (float64): 最低价（注意单位: 元）
        - 连涨天数 (int64): 连续上涨天数
        - 连续涨跌幅 (float64): 连续涨跌幅（注意单位: %）
        - 累计换手率 (float64): 累计换手率（注意单位: %）
        - 所属行业 (object): 所属行业

    返回统一结构:
        {
            "success": True/False,
            "data": [
                {
                    "序号": 1,
                    "股票代码": "600519",
                    "股票简称": "贵州茅台",
                    "收盘价": 1850.5,
                    "最高价": 1865.8,
                    "最低价": 1820.3,
                    "连涨天数": 5,
                    "连续涨跌幅": 12.35,
                    "累计换手率": 3.25,
                    "所属行业": "白酒"
                },
                ...
            ],
            "error": None 或错误信息,
            "symbol": "lxsz"  # 固定标识
        }

    注意:
        1. 连续上涨反映股票短期强势表现
        2. 连涨天数越多表示趋势越强，但回调风险也越大
        3. 累计换手率反映筹码换手情况，高换手率可能意味着分歧加大
        4. 连续涨跌幅反映连续上涨的总幅度
        5. 连续上涨后需关注是否有高位出货迹象
    """
    logger.info("[同花顺连续上涨] 开始查询连续上涨数据")

    try:
        df = ak.stock_rank_lxsz_ths()

        if df.empty:
            logger.warning("[同花顺连续上涨] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lxsz"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺连续上涨] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lxsz"
        }

    except Exception as e:
        error_msg = f"查询同花顺连续上涨失败: {str(e)}"
        logger.error(f"[同花顺连续上涨] 异常 error={error_msg}")
        logger.debug(f"[同花顺连续上涨] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lxsz"
        }


def get_stock_rank_cxfl_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续放量数据

    接口: akshare.stock_rank_cxfl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxfl/

    描述: 同花顺-数据中心-技术选股-持续放量

    返回字段包括：序号、股票代码、股票简称、涨跌幅(%)、最新价(元)、
    成交量(股)、基准日成交量(股)、放量天数、阶段涨跌幅(%)、所属行业

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxfl" }

    使用说明：
        1. 持续放量表示资金持续流入，可能是主力建仓或拉升信号
        2. 放量天数越多，趋势信号越强
        3. 需结合涨跌幅判断是温和放量还是异常放量
        4. 持续放量后若出现滞涨，需警惕回调风险
    """
    logger.info("[同花顺持续放量] 开始查询持续放量数据")

    try:
        df = ak.stock_rank_cxfl_ths()

        if df.empty:
            logger.warning("[同花顺持续放量] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "cxfl"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺持续放量] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "cxfl"
        }

    except Exception as e:
        error_msg = f"查询同花顺持续放量失败: {str(e)}"
        logger.error(f"[同花顺持续放量] 异常 error={error_msg}")
        logger.debug(f"[同花顺持续放量] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "cxfl"
        }


def get_stock_rank_cxsl_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续缩量数据

    接口: akshare.stock_rank_cxsl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxsl/

    描述: 同花顺-数据中心-技术选股-持续缩量

    返回字段包括：序号、股票代码、股票简称、涨跌幅(%)、最新价(元)、
    成交量(股)、基准日成交量(股)、缩量天数、阶段涨跌幅(%)、所属行业

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxsl" }

    使用说明：
        1. 持续缩量可能表示市场参与度降低，交投清淡
        2. 在底部区域的持续缩量可能预示筹码惜售
        3. 在高位持续缩量可能表示上涨动力衰竭
        4. 需结合股价位置和前期成交量变化综合判断
    """
    logger.info("[同花顺持续缩量] 开始查询持续缩量数据")

    try:
        df = ak.stock_rank_cxsl_ths()

        if df.empty:
            logger.warning("[同花顺持续缩量] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "cxsl"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺持续缩量] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "cxsl"
        }

    except Exception as e:
        error_msg = f"查询同花顺持续缩量失败: {str(e)}"
        logger.error(f"[同花顺持续缩量] 异常 error={error_msg}")
        logger.debug(f"[同花顺持续缩量] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "cxsl"
        }


def get_stock_rank_xstp_ths(symbol: str = "500日均线") -> Dict[str, Any]:
    """
    查询同花顺技术选股-向上突破数据

    接口: akshare.stock_rank_xstp_ths
    目标地址: https://data.10jqka.com.cn/rank/xstp/

    描述: 同花顺-数据中心-技术选股-向上突破

    Args:
        symbol: 均线周期类型，choice of {"5日均线", "10日均线", "20日均线",
                  "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}

    返回字段包括：序号、股票代码、股票简称、最新价(元)、成交额(元)、
    成交量(股)、涨跌幅(%)、换手率(%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 向上突破表示股价穿越均线压制，可能是买入信号
        2. 短周期均线突破信号更灵敏但假信号较多
        3. 长周期均线突破信号更可靠但滞后性较强
        4. 需结合成交量确认突破的有效性
    """
    # 参数验证
    valid_symbols = ["5日均线", "10日均线", "20日均线", "30日均线",
                     "60日均线", "90日均线", "250日均线", "500日均线"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺向上突破] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_rank_xstp_ths(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺向上突破] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺向上突破] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺向上突破失败: {str(e)}"
        logger.error(f"[同花顺向上突破] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺向上突破] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_rank_ljqs_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐升数据

    接口: akshare.stock_rank_ljqs_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqs/

    描述: 同花顺-数据中心-技术选股-量价齐升

    返回字段包括：序号、股票代码、股票简称、最新价(元)、
    量价齐升天数、阶段涨幅(%)、累计换手率(%)、所属行业

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqs" }

    使用说明：
        1. 量价齐升是最健康的上涨形态，表示量价配合良好
        2. 量价齐升天数越多，上涨趋势越强劲
        3. 累计换手率反映筹码换手充分程度
        4. 需关注是否出现量价背离的前兆信号
    """
    logger.info("[同花顺量价齐升] 开始查询量价齐升数据")

    try:
        df = ak.stock_rank_ljqs_ths()

        if df.empty:
            logger.warning("[同花顺量价齐升] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "ljqs"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺量价齐升] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "ljqs"
        }

    except Exception as e:
        error_msg = f"查询同花顺量价齐升失败: {str(e)}"
        logger.error(f"[同花顺量价齐升] 异常 error={error_msg}")
        logger.debug(f"[同花顺量价齐升] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "ljqs"
        }


def get_stock_rank_ljqd_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐跌数据

    接口: akshare.stock_rank_ljqd_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqd/

    描述: 同花顺-数据中心-技术选股-量价齐跌

    返回字段包括：序号、股票代码、股票简称、最新价(元)、
    量价齐跌天数、阶段涨幅(%)、累计换手率(%)、所属行业

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqd" }

    使用说明：
        1. 量价齐跌是最弱势的下跌形态，可能持续下行
        2. 量价齐跌天数越多，下跌趋势越明显
        3. 累计换手率低可能表示抛压未完全释放
        4. 抄底需谨慎，等待止跌信号出现
    """
    logger.info("[同花顺量价齐跌] 开始查询量价齐跌数据")

    try:
        df = ak.stock_rank_ljqd_ths()

        if df.empty:
            logger.warning("[同花顺量价齐跌] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "ljqd"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺量价齐跌] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "ljqd"
        }

    except Exception as e:
        error_msg = f"查询同花顺量价齐跌失败: {str(e)}"
        logger.error(f"[同花顺量价齐跌] 异常 error={error_msg}")
        logger.debug(f"[同花顺量价齐跌] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "ljqd"
        }


def get_stock_rank_xzjp_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-险资举牌数据

    接口: akshare.stock_rank_xzjp_ths
    目标地址: https://data.10jqka.com.cn/financial/xzjp/

    描述: 同花顺-数据中心-技术选股-险资举牌

    返回字段包括：序号、举牌公告日、股票代码、股票简称、现价(元)、
    涨跌幅(%)、举牌方、增持数量(股)、交易均价(元)、
    增持数量占总股本比例(%)、变动后持股总数(股)、变动后持股比例(%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "xzjp" }

    使用说明：
        1. 险资举牌通常具有中长期投资意图
        2. 举牌方信息反映机构对该股票的认可度
        3. 增持比例和持股比例反映机构持仓深度
        4. 可关注举牌成本与现价的差异
    """
    logger.info("[同花顺险资举牌] 开始查询险资举牌数据")

    try:
        df = ak.stock_rank_xzjp_ths()

        if df.empty:
            logger.warning("[同花顺险资举牌] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "xzjp"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺险资举牌] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "xzjp"
        }

    except Exception as e:
        error_msg = f"查询同花顺险资举牌失败: {str(e)}"
        logger.error(f"[同花顺险资举牌] 异常 error={error_msg}")
        logger.debug(f"[同花顺险资举牌] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "xzjp"
        }


def get_stock_zh_growth_comparison_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富-行情中心-同行比较-成长性比较

    接口: akshare.stock_zh_growth_comparison_em
    目标地址: https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=000895&color=b#/thbj/czxbj

    描述: 东方财富-行情中心-同行比较-成长性比较

    Args:
        symbol: 股票代码，需带市场前缀，如 "SZ000895"

    返回字段包括：代码、简称、基本每股收益增长率(3年复合/24A/TTM/25E/26E/27E)、
    营业收入增长率(3年复合/24A/TTM/25E/26E/27E)、净利润增长率(3年复合/24A/TTM/25E/26E/27E)等

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 成长性比较用于评估公司业绩增长能力
        2. 3年复合增长率反映长期成长性
        3. TTM为滚动12个月数据，反映近期情况
        4. E结尾表示预测数据
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富成长性比较] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_zh_growth_comparison_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富成长性比较] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富成长性比较] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富成长性比较失败: {str(e)}"
        logger.error(f"[东方财富成长性比较] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富成长性比较] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_zh_valuation_comparison_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富-行情中心-同行比较-估值比较

    接口: akshare.stock_zh_valuation_comparison_em
    目标地址: https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=000895&color=b#/thbj/gzbj

    描述: 东方财富-行情中心-同行比较-估值比较

    Args:
        symbol: 股票代码，需带市场前缀，如 "SZ000895"

    返回字段包括：排名、代码、简称、PEG、市盈率(24A/TTM/25E/26E/27E)、
    市销率(24A/TTM/25E/26E/27E)、市净率(24A/MRQ)、市现率(24A/TTM)、EV/EBITDA等

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 估值比较用于评估股票相对同行的估值水平
        2. PE、PB、PS是最常用的估值指标
        3. PEG综合考虑成长性，低于1可能被视为低估
        4. E结尾表示预测数据
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富估值比较] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_zh_valuation_comparison_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富估值比较] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富估值比较] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富估值比较失败: {str(e)}"
        logger.error(f"[东方财富估值比较] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富估值比较] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_zh_dupont_comparison_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富-行情中心-同行比较-杜邦分析比较

    接口: akshare.stock_zh_dupont_comparison_em
    目标地址: https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=000895&color=b#/thbj/dbfxbj

    描述: 东方财富-行情中心-同行比较-杜邦分析比较

    Args:
        symbol: 股票代码，需带市场前缀，如 "SZ000895"

    返回字段包括：代码、简称、ROE(3年平均/22A/23A/24A)、净利率(3年平均/22A/23A/24A)、
    总资产周转率(3年平均/22A/23A/24A)、权益乘数(3年平均/22A/23A/24A)等

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 杜邦分析将ROE分解为净利率、总资产周转率、权益乘数
        2. ROE是衡量股东回报的核心指标
        3. 3年平均数据更能反映公司稳定的盈利能力
        4. 可对比同行分析公司的盈利模式和竞争力
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富杜邦分析] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_zh_dupont_comparison_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富杜邦分析] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富杜邦分析] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富杜邦分析失败: {str(e)}"
        logger.error(f"[东方财富杜邦分析] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富杜邦分析] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_individual_basic_info_xq(symbol: str) -> Dict[str, Any]:
    """
    查询雪球财经-个股-公司概况

    接口: akshare.stock_individual_basic_info_xq
    目标地址: https://xueqiu.com/snowman/S/SH601127/detail#/GSJJ

    描述: 雪球财经-个股-公司概况-公司简介

    Args:
        symbol: 股票代码，需带市场前缀，如 "SH601127"

    返回字段：item（项目名称）、value（对应值）

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 提供公司基本信息、公司简介等数据
        2. 数据格式为键值对形式
        3. 可用于获取公司基本信息补充
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[雪球公司概况] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            result = ak.stock_individual_basic_info_xq(symbol=symbol)
            
            # 检查返回值是否为None
            if result is None:
                logger.warning(f"[雪球公司概况] symbol={symbol} 返回为None")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }
            
            # 如果返回的是DataFrame
            if hasattr(result, 'empty'):
                df = result
                if df is None or len(df) == 0:
                    logger.warning(f"[雪球公司概况] symbol={symbol} 返回数据为空")
                    return {
                        "success": True,
                        "data": [],
                        "error": None,
                        "symbol": symbol
                    }
                
                # 正常处理DataFrame
                data_list = _convert_dataframe_to_list(df, "[雪球公司概况]")
                
            elif isinstance(result, dict):
                # 如果返回的是字典
                data_list = [result] if result else []
                
            elif isinstance(result, list):
                # 如果返回的是列表
                data_list = result
                
            else:
                data_list = []
            
            logger.info(f"[雪球公司概况] symbol={symbol} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except KeyError as ke:
            # 雪球接口返回的JSON中没有data字段（常见问题）
            error_msg = f"雪球接口返回数据格式异常: {str(ke)}"
            logger.warning(f"[雪球公司概况] symbol={symbol} 接口返回格式异常: {error_msg}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }
        except Exception as e:
            error_msg = f"查询雪球公司概况失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[雪球公司概况] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[雪球公司概况] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[雪球公司概况] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_fund_flow_individual(symbol: str = "即时") -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-个股资金流

    接口: akshare.stock_fund_flow_individual
    目标地址: https://data.10jqka.com.cn/funds/ggzjl/

    描述: 同花顺-数据中心-资金流向-个股资金流

    Args:
        symbol: 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    返回字段包括：序号、股票代码、股票简称、最新价、涨跌幅(%)、换手率、
    流入资金(元)、流出资金(元)、净额(元)、成交额(元)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 即时数据获取当前正在流入流出的个股
        2. 排行数据获取某时间段内资金流向排名
        3. 净额为正表示主力净流入
        4. 可结合涨跌幅判断资金进出是否有效
    """
    valid_symbols = ["即时", "3日排行", "5日排行", "10日排行", "20日排行"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺个股资金流] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_fund_flow_individual(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺个股资金流] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺个股资金流] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺个股资金流失败: {str(e)}"
        logger.error(f"[同花顺个股资金流] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺个股资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_fund_flow_concept(symbol: str = "即时") -> Dict[str, Any]:
    """
    查询同花顺-数据中心-资金流向-概念资金流

    接口: akshare.stock_fund_flow_concept
    目标地址: https://data.10jqka.com.cn/funds/gnzjl/

    描述: 同花顺-数据中心-资金流向-概念资金流

    Args:
        symbol: 时间周期类型，choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}

    返回字段包括：序号、行业、行业指数、行业涨跌幅(%)、流入资金(亿)、
    流出资金(亿)、净额(亿)、公司家数、领涨股、领涨股涨跌幅(%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 按行业/概念分类统计资金流向
        2. 可追踪热点板块资金轮动
        3. 领涨股反映板块内最强个股
        4. 净额为正表示板块整体资金净流入
    """
    valid_symbols = ["即时", "3日排行", "5日排行", "10日排行", "20日排行"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺概念资金流] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_fund_flow_concept(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺概念资金流] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[同花顺概念资金流] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺概念资金流失败: {str(e)}"
        logger.error(f"[同花顺概念资金流] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺概念资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_individual_fund_flow(stock: str, market: str = "sz") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-个股资金流向（近100交易日）

    接口: akshare.stock_individual_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/detail.html

    描述: 东方财富网-数据中心-个股资金流向

    Args:
        stock: 股票代码，如 "000425"
        market: 市场标识，choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}

    返回字段包括：日期、收盘价、涨跌幅(%)、主力净流入(净额/净占比%)、
    超大单净流入(净额/净占比%)、大单净流入(净额/净占比%)、
    中单净流入(净额/净占比%)、小单净流入(净额/净占比%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 返回近100个交易日的日频资金流向数据
        2. 主力资金通常指超大单和大单的合计
        3. 净流入为正表示资金净买入
        4. 可分析资金进出节奏和趋势
    """
    if not stock:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    valid_markets = ["sh", "sz", "bj"]
    if market not in valid_markets:
        return {
            "success": False,
            "data": None,
            "error": f"无效的market参数，请选择: {valid_markets}",
            "symbol": stock
        }

    logger.info(f"[东方财富个股资金流] 开始查询 stock={stock}, market={market}")

    try:
        df = ak.stock_individual_fund_flow(stock=stock, market=market)

        if df.empty:
            logger.warning(f"[东方财富个股资金流] stock={stock} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": stock
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富个股资金流] stock={stock} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": stock
        }

    except Exception as e:
        error_msg = f"查询东方财富个股资金流失败: {str(e)}"
        logger.error(f"[东方财富个股资金流] stock={stock} 异常 error={error_msg}")
        logger.debug(f"[东方财富个股资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": stock
        }


def get_stock_individual_fund_flow_rank(indicator: str = "今日") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-资金流向排名

    接口: akshare.stock_individual_fund_flow_rank
    目标地址: http://data.eastmoney.com/zjlx/detail.html

    描述: 东方财富网-数据中心-资金流向-排名

    Args:
        indicator: 时间周期，choice of {"今日", "3日", "5日", "10日"}

    返回字段包括：序号、代码、名称、最新价、今日涨跌幅(%)、主力净流入(净额/净占比%)、
    超大单净流入(净额/净占比%)、大单净流入(净额/净占比%)、
    中单净流入(净额/净占比%)、小单净流入(净额/净占比%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 获取全市场个股资金流向排名
        2. 可发现当日/近期资金追逐的热点个股
        3. 主力净流入排名反映大资金动向
        4. 结合涨跌幅可判断资金推动效果
    """
    valid_indicators = ["今日", "3日", "5日", "10日"]
    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": ""
        }

    logger.info(f"[东方财富资金流向排名] 开始查询 indicator={indicator}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_individual_fund_flow_rank,
                indicator=indicator,
                max_retries=1,
                logger_name="资金流向排名"
            )

            if df is None or df.empty:
                logger.warning(f"[东方财富资金流向排名] indicator={indicator} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": indicator
                }

            data_list = _convert_dataframe_to_list(df, "[资金流向排名]")

            logger.info(f"[东方财富资金流向排名] indicator={indicator} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": indicator
            }

        except Exception as e:
            error_msg = f"查询东方财富资金流向排名失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[资金流向排名] 第{attempt + 1}次失败 indicator={indicator}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[资金流向排名] 最终失败 indicator={indicator}, error={error_msg}")
                logger.debug(f"[资金流向排名] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": indicator
                }


def get_stock_market_fund_flow() -> Dict[str, Any]:
    """
    查询东方财富-数据中心-大盘资金流向

    接口: akshare.stock_market_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/dpzjlx.html

    描述: 东方财富网-数据中心-资金流向-大盘

    返回字段包括：日期、上证收盘价/涨跌幅、深证收盘价/涨跌幅、
    主力净流入(净额/净占比%)、超大单净流入(净额/净占比%)、
    大单净流入(净额/净占比%)、中单净流入(净额/净占比%)、
    小单净流入(净额/净占比%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "market_fund_flow" }

    使用说明：
        1. 反映大盘整体资金流向情况
        2. 沪深两市资金合计反映市场整体情绪
        3. 主力净流入可作为市场底部/顶部判断参考
        4. 连续净流出可能预示市场调整
    """
    logger.info("[东方财富大盘资金流] 开始查询大盘资金流向数据")

    try:
        df = ak.stock_market_fund_flow()

        if df.empty:
            logger.warning("[东方财富大盘资金流] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "market_fund_flow"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富大盘资金流] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "market_fund_flow"
        }

    except Exception as e:
        error_msg = f"查询东方财富大盘资金流失败: {str(e)}"
        logger.error(f"[东方财富大盘资金流] 异常 error={error_msg}")
        logger.debug(f"[东方财富大盘资金流] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "market_fund_flow"
        }


def get_stock_sector_fund_flow_rank(indicator: str = "今日", sector_type: str = "行业资金流") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-板块资金流排名

    接口: akshare.stock_sector_fund_flow_rank
    目标地址: https://data.eastmoney.com/bkzj/hy.html

    描述: 东方财富网-数据中心-资金流向-板块资金流-排名

    Args:
        indicator: 时间周期，choice of {"今日", "5日", "10日"}
        sector_type: 板块类型，choice of {"行业资金流", "概念资金流", "地域资金流"}

    返回字段包括：序号、名称、今日涨跌幅(%)、主力净流入(净额/净占比%)、
    超大单净流入(净额/净占比%)、大单净流入(净额/净占比%)、
    中单净流入(净额/净占比%)、小单净流入(净额/净占比%)、主力净流入最大股

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 可按行业/概念/地域多维度分析资金流向
        2. 5日/10日数据更能反映中期趋势
        3. 主力净流入最大股反映板块内龙头
        4. 资金流向领先于股价涨跌
    """
    valid_indicators = ["今日", "5日", "10日"]
    valid_sector_types = ["行业资金流", "概念资金流", "地域资金流"]

    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": ""
        }

    if sector_type not in valid_sector_types:
        return {
            "success": False,
            "data": None,
            "error": f"无效的sector_type参数，请选择: {valid_sector_types}",
            "symbol": ""
        }

    logger.info(f"[板块资金流排名] 开始查询 indicator={indicator}, sector_type={sector_type}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_sector_fund_flow_rank,
                indicator=indicator,
                sector_type=sector_type,
                max_retries=1,
                logger_name="板块资金流排名"
            )

            if df is None or df.empty:
                logger.warning(f"[板块资金流排名] indicator={indicator} sector_type={sector_type} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": f"{indicator}_{sector_type}"
                }

            data_list = _convert_dataframe_to_list(df, "[板块资金流排名]")

            logger.info(f"[板块资金流排名] indicator={indicator} sector_type={sector_type} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": f"{indicator}_{sector_type}"
            }

        except Exception as e:
            error_msg = f"查询东方财富板块资金流排名失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[板块资金流排名] 第{attempt + 1}次失败 indicator={indicator}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[板块资金流排名] 最终失败 indicator={indicator}, sector_type={sector_type}, error={error_msg}")
                logger.debug(f"[板块资金流排名] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": f"{indicator}_{sector_type}"
                }


def get_stock_sector_fund_flow_summary(symbol: str, indicator: str = "今日") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-行业个股资金流

    接口: akshare.stock_sector_fund_flow_summary
    目标地址: https://data.eastmoney.com/bkzj/BK1034.html

    描述: 东方财富网-数据中心-资金流向-行业资金流-xx行业个股资金流

    Args:
        symbol: 行业板块名称，如 "电源设备"
        indicator: 时间周期，choice of {"今日", "5日", "10日"}

    返回字段包括：序号、代码、名称、最新价、今日涨跌幅(%)、
    主力净流入(净额/净占比%)、超大单净流入(净额/净占比%)、
    大单净流入(净额/净占比%)、中单净流入(净额/净占比%)、
    小单净流入(净额/净占比%)

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 获取特定行业内所有个股的资金流向
        2. 可对比行业内个股资金分化情况
        3. 识别行业内资金主要流向的个股
        4. 辅助行业选股决策
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "行业板块名称不能为空",
            "symbol": ""
        }

    valid_indicators = ["今日", "5日", "10日"]
    if indicator not in valid_indicators:
        return {
            "success": False,
            "data": None,
            "error": f"无效的indicator参数，请选择: {valid_indicators}",
            "symbol": symbol
        }

    logger.info(f"[行业个股资金流] 开始查询 symbol={symbol}, indicator={indicator}")

    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_sector_fund_flow_summary,
                symbol=symbol,
                indicator=indicator,
                max_retries=1,
                logger_name="行业个股资金流"
            )

            if df is None or df.empty:
                logger.warning(f"[行业个股资金流] symbol={symbol} indicator={indicator} 返回数据为空")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[行业个股资金流]")

            logger.info(f"[行业个股资金流] symbol={symbol} indicator={indicator} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询东方财富行业个股资金流失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[行业个股资金流] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[行业个股资金流] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[行业个股资金流] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_main_fund_flow(symbol: str = "全部股票") -> Dict[str, Any]:
    """
    查询东方财富-数据中心-主力净流入排名

    接口: akshare.stock_main_fund_flow
    目标地址: https://data.eastmoney.com/zjlx/list.html

    描述: 东方财富网-数据中心-资金流向-主力净流入排名

    Args:
        symbol: 市场筛选，choice of {"全部股票", "沪深A股", "沪市A股", "科创板",
                  "深市A股", "创业板", "沪市B股", "深市B股"}

    返回字段包括：序号、代码、名称、最新价、今日排行榜(主力净占比/排名/涨跌)、
    5日排行榜(主力净占比/排名/涨跌)、10日排行榜(主力净占比/排名/涨跌)、所属板块

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 多周期对比发现资金持续关注的个股
        2. 今日排名反映短期资金动向
        3. 5日/10日排名反映中期资金趋势
        4. 连续上榜的个股值得关注
    """
    valid_symbols = ["全部股票", "沪深A股", "沪市A股", "科创板",
                     "深市A股", "创业板", "沪市B股", "深市B股"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[东方财富主力净流入排名] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_main_fund_flow(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富主力净流入排名] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富主力净流入排名] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富主力净流入排名失败: {str(e)}"
        logger.error(f"[东方财富主力净流入排名] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富主力净流入排名] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_research_report_em(symbol: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-个股研报

    接口: akshare.stock_research_report_em
    目标地址: https://data.eastmoney.com/report/stock.jshtml

    描述: 东方财富网-数据中心-研究报告-个股研报

    Args:
        symbol: 股票代码，如 "000001"

    返回字段包括：序号、股票代码、股票简称、报告名称、东财评级、机构、
    近一月个股研报数、2024-2026年盈利预测(收益/市盈率)、行业、日期、报告PDF链接

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 提供机构研究报告汇总
        2. 东财评级反映机构整体态度
        3. 盈利预测数据供投资参考
        4. 可追踪机构关注度变化
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[东方财富个股研报] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_research_report_em(symbol=symbol)

        if df.empty:
            logger.warning(f"[东方财富个股研报] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富个股研报] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询东方财富个股研报失败: {str(e)}"
        logger.error(f"[东方财富个股研报] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[东方财富个股研报] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_gsrl_gsdt_em(date: str) -> Dict[str, Any]:
    """
    查询东方财富-数据中心-股市日历-公司动态

    接口: akshare.stock_gsrl_gsdt_em
    目标地址: https://data.eastmoney.com/gsrl/gsdt.html

    描述: 东方财富网-数据中心-股市日历-公司动态

    Args:
        date: 交易日，格式 "YYYYMMDD"，如 "20230808"

    返回字段包括：序号、代码、简称、事件类型、具体事项、交易日

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 提供上市公司重要事件公告信息
        2. 事件类型包括分红、业绩预告、重大事项等
        3. 可用于事件驱动策略研究
        4. 具体事项描述公司动态详情
    """
    if not date:
        return {
            "success": False,
            "data": None,
            "error": "交易日不能为空",
            "symbol": ""
        }

    # 日期格式校验
    if len(date) != 8 or not date.isdigit():
        return {
            "success": False,
            "data": None,
            "error": "日期格式错误，请使用 YYYYMMDD 格式",
            "symbol": date
        }

    logger.info(f"[东方财富公司动态] 开始查询 date={date}")

    try:
        df = ak.stock_gsrl_gsdt_em(date=date)

        if df.empty:
            logger.warning(f"[东方财富公司动态] date={date} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": date
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[东方财富公司动态] date={date} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": date
        }

    except Exception as e:
        error_msg = f"查询东方财富公司动态失败: {str(e)}"
        logger.error(f"[东方财富公司动态] date={date} 异常 error={error_msg}")
        logger.debug(f"[东方财富公司动态] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": date
        }


# 示例：直接运行测试
if __name__ == "__main__":
    # 配置基础日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试代码
    test_symbols = ["000001", "603777", "invalid"]
    
    for sym in test_symbols:
        print(f"\n=== 测试股票代码: {sym} ===")
        result = get_stock_info(sym)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result["success"]:
            print(f"查询成功，数据字段数: {len(result['data']) if result['data'] else 0}")
        else:
            print(f"查询失败: {result['error']}")