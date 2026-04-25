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

72. sync_all_stocks() -> dict
    全市场A股列表同步到 stocks_info 表。
    调用 unity.basic.get_all_stock_codes() 获取全市场代码，执行事务性批量 UPSERT + 退市标记。
    返回：{ "success": bool, "data": { total_fetched, inserted, updated, delisted, duration_ms }, "error": str | None }
    路由：POST /api/stocks/sync



使用示例：
    from stock_services.unity import get_stock_info
    result = get_stock_info("000001")
"""

import logging

# ============================================================================
# 全局 AKShare 配置 - 请求延时 + 随机UA + 超时设置
# ============================================================================
import random
import time

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
# 导出所有业务模块接口（按业务分类）
# ============================================================================

# ----------------------------------------------------------------------------
# 1. 股票基本信息模块 (basic/)
# 位置: backend/api/stock/unity/basic/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.basic import get_all_stock_codes  # 查询全市场A股股票代码列表
from stock_services.unity.basic import get_stock_individual_basic_info_xq  # 查询雪球财经-个股-公司概况
from stock_services.unity.basic import get_stock_info_em  # 查询个股基础信息（东方财富接口）
from stock_services.unity.basic import stock_info_bj_name_code  # 北京证券交易所股票代码和简称数据
from stock_services.unity.basic import stock_info_sh_delist  # 上海证券交易所暂停/终止上市股票
from stock_services.unity.basic import stock_info_sh_name_code  # 上海证券交易所股票代码和简称数据
from stock_services.unity.basic import stock_info_sz_delist  # 深圳证券交易所终止/暂停上市股票
from stock_services.unity.basic import stock_info_sz_name_code  # 深圳证券交易所股票代码和简称数据

# ----------------------------------------------------------------------------
# 8. 板块概念模块 (board/)
# 位置: backend/api/stock/unity/board/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.board import get_stock_board_change_em  # 东方财富当日板块异动详情
from stock_services.unity.board import get_stock_board_concept_index_ths  # 同花顺概念板块指数日频率数据
from stock_services.unity.board import get_stock_board_concept_info_ths  # 同花顺概念板块简介
from stock_services.unity.board import get_stock_board_industry_index_ths  # 同花顺行业板块指数日频率数据
from stock_services.unity.board import get_stock_board_industry_summary_ths  # 同花顺行业一览表
from stock_services.unity.board import get_stock_changes_em  # 东方财富盘口异动数据
from stock_services.unity.board import get_stock_hot_follow_xq  # 雪球关注排行榜
from stock_services.unity.board import get_stock_hot_keyword_em  # 东方财富个股人气榜热门关键词
from stock_services.unity.board import get_stock_hot_rank_detail_em  # 东方财富股票热度历史趋势及粉丝特征

# ----------------------------------------------------------------------------
# 3. 财务报表模块 (financial/)
# 位置: backend/api/stock/unity/financial/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.financial import (
    get_stock_balance_sheet_by_yearly_em,  # 东方财富资产负债表（按年度）
)
from stock_services.unity.financial import (
    get_stock_cash_flow_sheet_by_report_em,  # 东方财富现金流量表（按报告期）
)
from stock_services.unity.financial import get_stock_financial_report_sina  # 新浪财经财务报表
from stock_services.unity.financial import get_stock_profit_forecast_ths  # 同花顺盈利预测数据
from stock_services.unity.financial import (
    get_stock_profit_sheet_by_report_em,  # 东方财富利润表（按报告期）
)
from stock_services.unity.financial import (
    get_stock_profit_sheet_by_yearly_em,  # 东方财富利润表（按年度）
)

# ----------------------------------------------------------------------------
# 6. 资金流向模块 (fund_flow/)
# 位置: backend/api/stock/unity/fund_flow/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.fund_flow import get_stock_fund_flow_concept  # 概念板块资金流向
from stock_services.unity.fund_flow import get_stock_fund_flow_individual  # 个股资金流向
from stock_services.unity.fund_flow import get_stock_individual_fund_flow  # 个股资金流向（东方财富）
from stock_services.unity.fund_flow import get_stock_individual_fund_flow_rank  # 个股资金流向排名
from stock_services.unity.fund_flow import get_stock_main_fund_flow  # 主力资金流向
from stock_services.unity.fund_flow import get_stock_market_fund_flow  # 市场资金流向
from stock_services.unity.fund_flow import get_stock_sector_fund_flow_rank  # 板块资金流向排名
from stock_services.unity.fund_flow import get_stock_sector_fund_flow_summary  # 板块资金流向汇总

# ----------------------------------------------------------------------------
# 4. 股东数据模块 (holder/)
# 位置: backend/api/stock/unity/holder/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.holder import get_stock_account_statistics_em  # 月度股票账户统计数据
from stock_services.unity.holder import (
    get_stock_comment_detail_scrd_desire_em,  # 千股千评-市场参与意愿
)
from stock_services.unity.holder import get_stock_comment_detail_scrd_focus_em  # 千股千评-用户关注指数
from stock_services.unity.holder import get_stock_comment_em  # 千股千评数据（全部股票当日评分）
from stock_services.unity.holder import get_stock_zh_a_gdhs  # 全市场股东户数数据
from stock_services.unity.holder import get_stock_zh_a_gdhs_detail_em  # 个股股东户数详情

# ----------------------------------------------------------------------------
# 5. 龙虎榜模块 (lhb/)
# 位置: backend/api/stock/unity/lhb/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.lhb import get_stock_lhb_detail_em  # 龙虎榜详情数据
from stock_services.unity.lhb import get_stock_lhb_hyyyb_em  # 每日活跃营业部数据
from stock_services.unity.lhb import get_stock_lhb_jgmmtj_em  # 龙虎榜机构买卖每日统计
from stock_services.unity.lhb import get_stock_lhb_stock_statistic_em  # 个股上榜统计数据
from stock_services.unity.lhb import get_stock_lhb_yyb_detail_em  # 营业部历史交易明细

# ----------------------------------------------------------------------------
# 7. 融资融券模块 (margin/)
# 位置: backend/api/stock/unity/margin/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.margin import get_stock_margin_account_info  # 两融账户信息
from stock_services.unity.margin import get_stock_margin_detail_sse  # 上交所融资融券明细数据
from stock_services.unity.margin import get_stock_margin_detail_szse  # 深交所融资融券明细数据
from stock_services.unity.margin import get_stock_margin_sse  # 上交所融资融券汇总数据

# ----------------------------------------------------------------------------
# 2. 股权质押模块 (pledge/)
# 位置: backend/api/stock/unity/pledge/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.pledge import (
    get_stock_gpzy_individual_pledge_ratio_detail_em,  # 个股重要股东股权质押明细
)
from stock_services.unity.pledge import get_stock_gpzy_industry_data_em  # 各行业质押比例汇总数据
from stock_services.unity.pledge import get_stock_gpzy_pledge_ratio_em  # 指定交易日上市公司质押比例
from stock_services.unity.pledge import get_stock_gpzy_profile_em  # 股权质押市场概况查询

# ----------------------------------------------------------------------------
# 10. 技术选股排名模块 (rank/)
# 位置: backend/api/stock/unity/rank/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.rank import get_stock_rank_cxfl_ths  # 同花顺创新低股排名
from stock_services.unity.rank import get_stock_rank_cxg_ths  # 同花顺创新高股排名
from stock_services.unity.rank import get_stock_rank_cxsl_ths  # 同花顺持续缩量股排名
from stock_services.unity.rank import get_stock_rank_ljqd_ths  # 同花顺量价齐跌股排名
from stock_services.unity.rank import get_stock_rank_ljqs_ths  # 同花顺量价齐升股排名
from stock_services.unity.rank import get_stock_rank_lxsz_ths  # 同花顺连续上涨股排名
from stock_services.unity.rank import get_stock_rank_xstp_ths  # 同花顺向上突破股排名
from stock_services.unity.rank import get_stock_rank_xzjp_ths  # 同花顺向下击破股排名

# ----------------------------------------------------------------------------
# 9. 涨跌停模块 (zt/)
# 位置: backend/api/stock/unity/zt/service.py
# ----------------------------------------------------------------------------
from stock_services.unity.zt import get_stock_zt_pool_dtgc_em  # 东方财富跌停股池数据
from stock_services.unity.zt import get_stock_zt_pool_em  # 东方财富涨停股池数据
from stock_services.unity.zt import get_stock_zt_pool_previous_em  # 东方财富昨日涨停股池数据
from stock_services.unity.zt import get_stock_zt_pool_strong_em  # 东方财富强势股池数据
from stock_services.unity.zt import get_stock_zt_pool_zbgc_em  # 东方财富炸板股池数据


__all__ = [
    # basic
    "get_stock_info_em",
    "get_stock_individual_basic_info_xq",
    "get_all_stock_codes",
    "stock_info_sh_name_code",
    "stock_info_sz_name_code",
    "stock_info_bj_name_code",
    "stock_info_sz_delist",
    "stock_info_sh_delist",
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
