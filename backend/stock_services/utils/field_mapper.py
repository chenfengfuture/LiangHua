#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块概念字段映射工具模块

专门处理板块概念相关接口的字段映射，对应 board/service.py 中的9个接口。
重构优化：使用统一映射框架，减少代码重复，保持向上兼容。
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import date

from system_service.service_result import success_result

logger = logging.getLogger(__name__)

# 全市场统一分类映射表
STOCK_TYPE_MAP = {
    # 上交所
    "主板A股": "A股",
    "主板B股": "B股",
    "科创板": "科创板",
    # 深交所
    "A股列表": "A股",
    "B股列表": "B股",
    "CDR列表": "CDR",
    "北交所": '北交所A股'
}


# ============================================================================
# 基础字段映射常量
# ============================================================================

# 通用日期字段映射
DATE_FIELDS = {
    "日期": "trade_date",
    "交易日期": "trade_date",
    "date": "trade_date",
    "stat_date": "stat_date",
    "rank_date": "rank_date",
    "change_date": "change_date",
    "occur_time": "occur_time",
    "time": "occur_time"
}

# 通用股票字段映射
STOCK_FIELDS = {
    "股票代码": "symbol",
    "代码": "symbol",
    "code": "symbol",
    "symbol": "symbol",
    "股票名称": "name",
    "名称": "name",
    "股票简称": "name",
    "stock_name": "name",
    "name": "name",
    "当前价格": "current_price",
    "price": "current_price",
    "涨跌幅": "change_percent",
    "pct_chg": "change_percent",
    "change_pct": "change_percent",
    "change_percent": "change_percent",
    "涨跌额": "change_amount",
    "change": "change_amount",
    "change_amount": "change_amount",
    "成交量": "volume",
    "vol": "volume",
    "volume": "volume",
    "成交额": "amount",
    "amount": "amount",
    "振幅": "amplitude",
    "amp": "amplitude",
    "amplitude": "amplitude",
    "换手率": "turnover_rate",
    # "累计换手率": "turnover_rate",
    "turnover": "turnover_rate",
    "turnover_rate": "turnover_rate",
    "主力净流入": "main_net_inflow",
    "流通市值": "circulating_market_cap",
    "成交额占总成交比": "turnover_ratio",
    "流入资金": "outflow_amount",
    "流出资金": "inflow_amount",
    "净额": "net_amount",
    "资金流入净额": "net_amount",
    "阶段涨跌幅": "phase_change",
    "量价齐升天数": "volume_price_up_days",
    "量价齐跌天数": "volume_price_down_days",
    "阶段涨幅": "stage_pct_change",
}

STOCK_ANNOUNCEMENT_HOLDING_MAPPING = {
    "举牌公告日": "announce_date",
    "现价": "current_price",
    "举牌方": "raider_name",
    "增持数量": "increase_volume",
    "交易均价": "avg_price",
    "增持数量占总股本比例": "increase_ratio",
    "变动后持股总数": "total_holding",
    "变动后持股比例": "holding_ratio",
}
# 价格字段映射
PRICE_FIELDS = {
    "开盘": "open_price",
    "开盘价": "open_price",
    "open": "open_price",
    "最高": "high_price",
    "最高价": "high_price",
    "high": "high_price",
    "最低": "low_price",
    "最低价": "low_price",
    "low": "low_price",
    "收盘": "close_price",
    "收盘价": "close_price",
    "close": "close_price",
    "净流入": "net_inflow",
    "均价": "avg_price",
    "市盈率": "pe_ratio",
    "主力成本": "main_cost",
    "机构参与度": "institution_participation",
    "综合得分": "composite_score",
    "上升": "trend",
    "目前排名": "current_rank",
    "关注指数": "attention_index",
    "交易日": "trade_date"
}

ZT_FIELDS = {
    "封板资金": "limit_fund",
    "首次封板时间": "first_limit_time",
    "最后封板时间": "last_limit_time",
    "炸板次数": "open_count",
    "涨停统计": "limit_statistic",
    "所属行业": "industry",
    "连板数": "limit_times",
    "涨停价": "limit_up_price",
    "涨速": "speed",
    "昨日封板时间": "prev_limit_time",
    "昨日连板数": "prev_limit_times",
    "是否新高": "is_new_high",
    "量比": "volume_ratio",
    "入选理由": "selection_reason",

}


# 板块字段映射
BOARD_FIELDS = {
    "板块类型": "board_type",
    "type": "board_type",
    "板块名称": "board_name",
    "board_name": "board_name",
    "异动方向": "change_direction",
    "direction": "change_direction",
    "异动原因": "change_reason",
    "reason": "change_reason",
    "强度级别": "strength_level",
    "strength": "strength_level",
    "板块异动总次数": "total_change_count",
    "板块异动最频繁个股及所属类型-股票代码": "most_frequent_stock_code",
    "板块异动最频繁个股及所属类型-股票名称": "most_frequent_stock_name",
    "板块异动最频繁个股及所属类型-买卖方向": "most_frequent_trade_direction",
    "板块具体异动类型列表及出现次数": "change_type_list",
}

STOCK_LHB_MAPPING = {
    "买方机构数": "buy_institution_count",
    "卖方机构数": "sell_institution_count",
    "机构买入总额": "institution_buy_amount",
    "机构卖出总额": "institution_sell_amount",
    "机构买入净额": "institution_net_amount",
    "市场总成交额": "total_trade_amount",
    "机构净买额占总成交额比": "institution_net_ratio",
    "上榜原因": "reason",
    "上榜日": "trade_date",
    "上榜日期": "trade_date",
    "最近上榜日": "latest_trade_date",
    "上榜次数": "total_lhb_times",
    "上榜后1日": "after_1d_pct_change",
    "上榜后2日": "after_2d_pct_change",
    "上榜后5日": "after_5d_pct_change",
    "上榜后10日": "after_10d_pct_change",
    "解读": "interpretation",
    "龙虎榜净买额": "lhb_net_amount",
    "龙虎榜买入额": "lhb_buy_amount",
    "龙虎榜卖出额": "lhb_sell_amount",
    "龙虎榜成交额": "lhb_turnover_amount",
    "净买额占总成交比": "net_amount_ratio",
    "龙虎榜总成交额": "lhb_total_amount",
    "买方机构次数": "buy_institution_times",

    "卖方机构次数": "sell_institution_times",
    "近1个月涨跌幅": "pct_change_1m",
    "近3个月涨跌幅": "pct_change_3m",
    "近6个月涨跌幅": "pct_change_6m",
    "近1年涨跌幅": "pct_change_1y",
    "营业部名称": "broker_name",
    "买入个股数": "buy_stock_count",
    "卖出个股数": "sell_stock_count",
    "买入总金额": "total_buy_amount",
    "卖出总金额": "total_sell_amount",
    "总买卖净额": "net_buy_amount",
    "买入股票": "buy_stocks",
    "营业部代码": "broker_code",


    "上榜后1天-买入次数": "buy_count_1d",
    "上榜后1天-平均涨幅": "avg_return_1d",
    "上榜后1天-上涨概率": "up_prob_1d",
    "上榜后2天-买入次数": "buy_count_2d",
    "上榜后2天-平均涨幅": "avg_return_2d",
    "上榜后2天-上涨概率": "up_prob_2d",
    "上榜后3天-买入次数": "buy_count_3d",
    "上榜后3天-平均涨幅": "avg_return_3d",
    "上榜后3天-上涨概率": "up_prob_3d",
    "上榜后5天-买入次数": "buy_count_5d",
    "上榜后5天-平均涨幅": "avg_return_5d",
    "上榜后5天-上涨概率": "up_prob_5d",
    "上榜后10天-买入次数": "buy_count_10d",
    "上榜后10天-平均涨幅": "avg_return_10d",
    "上榜后10天-上涨概率": "up_prob_10d",
    "龙虎榜成交金额": "total_lhb_amount",
    "买入额": "total_buy_amount",
    "买入次数": "total_buy_times",
    "卖出额": "total_sell_amount",
    "卖出次数": "total_sell_times",
    "合计动用资金": "total_fund_amount",
    "年内上榜次数": "year_total_times",
    "年内买入股票只数": "year_buy_stock_count",
    "年内3日跟买成功率": "year_3d_success_rate",

}


STOCK_CONTINUOUS_UP_STATS_MAPPING = {
    "连涨天数": "consecutive_up_days",
    "连续涨跌幅": "consecutive_up_pct",
    "累计换手率": "cumulative_turnover_rate",
    "所属行业": "industry",
}

# 融资融券
MARGIN_TRADING_DAILY_STAT_MAPPING = {
    "融资余额": "margin_balance",
    "融券余额": "short_balance",
    "融资买入额": "margin_buy_amount",
    "融券卖出额": "short_sell_amount",
    "证券公司数量": "securities_company_count",
    "营业部数量": "branch_office_count",
    "个人投资者数量": "individual_investor_count",
    "机构投资者数量": "institution_investor_count",
    "参与交易的投资者数量": "active_trader_count",
    "有融资融券负债的投资者数量": "liability_investor_count",
    "担保物总价值": "collateral_value",
    "平均维持担保比例": "avg_maintenance_ratio",
    "信用交易日期": "trade_date",
    "融券余量": "short_volume",
    "融券余量金额": "short_balance",
    "融券卖出量": "short_sell_volume",
    "融资融券余额": "margin_short_balance",

    "A股质押总比例": "total_pledge_ratio",
    "质押公司数量": "pledge_company_count",
    "质押笔数": "pledge_record_count",
    "质押总股数": "total_pledge_shares",
    "质押总市值": "total_pledge_market_value",
    "沪深300指数": "hs300_index",
}


# STOCK_RANK_FUND_FLOW_MAPPING = {
#     "今日涨跌幅": "pct_change_today",
#     "今日主力净流入-净额": "main_net_inflow",
#     "今日主力净流入-净占比": "main_net_inflow_pct",
#     "今日超大单净流入-净额": "super_large_net_inflow",
#     "今日超大单净流入-净占比": "super_large_net_inflow_pct",
#     "今日大单净流入-净额": "large_net_inflow",
#     "今日大单净流入-净占比": "large_net_inflow_pct",
#     "今日中单净流入-净额": "medium_net_inflow",
#     "今日中单净流入-净占比": "medium_net_inflow_pct",
#     "今日小单净流入-净额": "small_net_inflow",
#     "今日小单净流入-净占比": "small_net_inflow_pct",
# }

# 行业/概念字段映射
INDUSTRY_CONCEPT_FIELDS = {
    "时间": "stat_date",
    "行业代码": "industry_code",
    "industry_code": "industry_code",
    "行业名称": "industry_name",
    "industry_name": "industry_name",
    "概念代码": "concept_code",
    "concept_code": "concept_code",
    "板块": "board_name",
    "概念名称": "concept_name",
    "concept_name": "concept_name",
    "概念简介": "introduction",
    "desc": "introduction",
    "introduction": "introduction",
    "相关股票": "related_stocks",
    "stocks": "related_stocks",
    "related_stocks": "related_stocks",
    "股票数量": "stock_count",
    "count": "stock_count",
    "stock_count": "stock_count",
    "总市值": "total_market_cap",
    "market_cap": "total_market_cap",
    "total_market_cap": "total_market_cap",
    "主要公司": "main_companies",
    "companies": "main_companies",
    "main_companies": "main_companies",
    "热度级别": "hot_level",
    "hot": "hot_level",
    "hot_level": "hot_level",
    "趋势方向": "trend_direction",
    "trend": "trend_direction",
    "trend_direction": "trend_direction",
    "行业": "industry",
    "行业指数": "index_price",
    "行业-涨跌幅": "change_ratio",
    "概念": "concept_name",
    "地域": "region_name",
    "板块资金流向": "fund_flow_direction",
    # 概念板块简介字段（来自 stock_board_concept_info_ths 的"项目"列）
    "相关个股": "related_stocks",
    "相关介绍": "introduction",
    "行业类别": "industry_category",
    "发布时间": "publish_date",
    "浏览指数": "browse_index",
    "发布日期": "publish_date",
    # 概念板块简介 THS 实时数据字段
    "今开": "open_price",
    "昨收": "pre_close",
    "成交量(万手)": "volume",
    "板块涨幅": "board_change_percent",
    "涨幅排名": "rank_position",
    "涨跌家数": "up_down_count",
    "资金净流入(亿)": "net_inflow",
    "成交额(亿)": "amount",
}

# 股东数据
STOCK_HOLDER_NUM_MAPPING = {
    "股东户数统计截止日": "end_date",
    "区间涨跌幅": "interval_pct_change",
    "股东户数-本次": "holder_num_current",
    "股东户数-上次": "holder_num_previous",
    "股东户数-增减": "holder_num_change",
    "股东户数-增减比例": "holder_num_change_pct",
    "户均持股市值": "avg_market_cap_per_holder",
    "户均持股数量": "avg_share_per_holder",
    "总股本": "total_shares",
    "股本变动": "share_change",
    "股本变动原因": "share_change_reason",
    "股东户数公告日期": "announce_date",
}

# 热度相关字段映射
HEAT_FIELDS = {
    "热度": "heat",
    "热度排名": "hot_rank",
    "rank": "hot_rank",
    "hot_rank": "hot_rank",
    "热度得分": "heat_score",
    "score": "heat_score",
    "heat": "heat_score",
    "heat_score": "heat_score",
    "搜索次数": "search_count",
    "search": "search_count",
    "search_count": "search_count",
    "讨论次数": "discussion_count",
    "discuss": "discussion_count",
    "discussion_count": "discussion_count",
    "阅读次数": "read_count",
    "read": "read_count",
    "read_count": "read_count",
    "提及次数": "mention_count",
    "mention": "mention_count",
    "mention_count": "mention_count",
    "关键词": "keyword",
    "keyword": "keyword",
    "趋势": "trend",
    "trend": "trend",
    "讨论数": "discussion_count",
    "discussions": "discussion_count"
}

# 关注/粉丝字段映射
FOLLOW_FIELDS = {
    "关注": "follow_count",
    "followers": "follow_count",
    "follow_count": "follow_count",
    "关注增长": "follow_increase",
    "follow_growth": "follow_increase",
    "follow_increase": "follow_increase",
    "粉丝数量": "follower_count",
    "follower_count": "follower_count",
    "粉丝增长": "follower_increase",
    "follower_growth": "follower_increase",
    "follower_increase": "follower_increase",
    "男性比例": "male_ratio",
    "male": "male_ratio",
    "male_ratio": "male_ratio",
    "女性比例": "female_ratio",
    "female": "female_ratio",
    "female_ratio": "female_ratio",
    "年龄分布": "age_distribution",
    "age": "age_distribution",
    "age_distribution": "age_distribution",
    "地区分布": "region_distribution",
    "region": "region_distribution",
    "region_distribution": "region_distribution",
    "参与意愿": "desire_value",
    # "用户关注指数":
    "5日平均参与意愿": "avg_5_desire",
    "参与意愿变化": "desire_change",
    "5日平均变化": "avg_5_change",
}

# 排名字段映射
RANK_FIELDS = {
    "排名": "rank_position",
    "rank_position": "rank_position",
    "位置": "rank_position",
    "position": "rank_position"
}

# 统计字段映射
STATISTICS_FIELDS = {
    "公司家数": "company_count",
    "company_count": "company_count",
    "平均市盈率": "avg_pe",
    "pe": "avg_pe",
    "avg_pe": "avg_pe",
    "平均市净率": "avg_pb",
    "pb": "avg_pb",
    "avg_pb": "avg_pb",
    "平均涨跌幅": "avg_change_percent",
    "avg_change_percent": "avg_change_percent",
    "上涨家数": "rise_count",
    "up": "rise_count",
    "rise_count": "rise_count",
    "下跌家数": "fall_count",
    "down": "fall_count",
    "fall_count": "fall_count",
    "平盘家数": "flat_count",
    "flat": "flat_count",
    "flat_count": "flat_count"
}

# 9. 当日板块异动详情数据
BOARD_CHANGE_MAPPING = {
    "上证-收盘价": "sh_close",
    "上证-涨跌幅": "sh_pct_change",
    "深证-收盘价": "sz_close",
    "深证-涨跌幅": "sz_pct_change",
    "序号": "serial_number",
    "最新价": "latest_price",
    "领涨股票": "leader_stock",
    "leader_code": "leader_stock",
    "领涨股票名称": "leader_name",
    "领涨股": "leading_stock_name",
    "领涨股-最新价": "leading_stock_price",
    "领涨股-涨跌幅": "leading_stock_change",
    "leader_name": "leader_name",
    "领涨跌幅": "leader_change_percent",
    "leader_change": "leader_change_percent",
    "总成交量": "total_volume",
    "total_volume": "total_volume",
    "总成交额": "total_amount",
    "total_amount": "total_amount",
    "异动类型": "change_type",
    "change_type": "change_type",
    "当前价": "current_price",
    "基准日成交量": "base_volume",
    "放量天数": "surge_days",
    "缩量天数": "shrink_days",
}

# 财务报表字段
FINANCIAL_MAPPING = {
    # ==================== 公共头部 ====================
    "报告日": "report_date",
    "数据源": "data_source",
    "是否审计": "is_audited",
    "公告日期": "announcement_date",
    "币种": "currency",
    "类型": "statement_type",
    "更新日期": "update_datetime",

    # ==================== 资产负债表特有 ====================
    "流动资产": "current_assets",
    "货币资金": "monetary_funds",
    "结算备付金": "settlement_provision",
    "拆出资金": "lent_funds",
    "交易性金融资产": "trading_financial_assets",
    "买入返售金融资产": "buy_resale_financial_assets",
    "衍生金融资产": "derivative_financial_assets",
    "应收票据及应收账款": "notes_and_accounts_receivable",
    "应收票据": "notes_receivable",
    "应收账款": "accounts_receivable",
    "应收款项融资": "financing_receivables",
    "预付款项": "prepayments",
    "应收股利": "dividends_receivable",
    "应收利息": "interest_receivable",
    "应收保费": "premiums_receivable",
    "应收分保账款": "reinsurance_receivable",
    "应收分保合同准备金": "reinsurance_contract_reserve_receivable",
    "应收出口退税": "export_tax_rebate_receivable",
    "应收补贴款": "subsidy_receivable",
    "应收保证金": "margin_receivable",
    "内部应收款": "internal_receivable",
    "其他应收款": "other_receivables",
    "其他应收款(合计)": "other_receivables_total",
    "存货": "inventories",
    "划分为持有待售的资产": "assets_held_for_sale",
    "待摊费用": "deferred_expenses",
    "待处理流动资产损益": "pending_disposal_current_asset_loss",
    "一年内到期的非流动资产": "non_current_assets_due_within_one_year",
    "其他流动资产": "other_current_assets",
    "流动资产合计": "total_current_assets",
    "非流动资产": "non_current_assets",
    "发放贷款及垫款": "loans_and_advances_to_customers",
    "债权投资": "debt_investments",
    "其他债权投资": "other_debt_investments",
    "以公允价值计量且其变动计入其他综合收益的金融资产": "fvoci_financial_assets",
    "以摊余成本计量的金融资产": "amortized_cost_financial_assets",
    "可供出售金融资产": "available_for_sale_financial_assets",
    "长期股权投资": "long_term_equity_investments",
    "投资性房地产": "investment_properties",
    "长期应收款": "long_term_receivables",
    "其他权益工具投资": "other_equity_instruments",
    "其他非流动金融资产": "other_non_current_financial_assets",
    "其他长期投资": "other_long_term_investments",
    "固定资产原值": "fixed_assets_original_cost",
    "累计折旧": "accumulated_depreciation",
    "固定资产净值": "fixed_assets_net_book_value",
    "固定资产减值准备": "fixed_assets_impairment",
    "在建工程合计": "construction_in_progress_total",
    "在建工程": "construction_in_progress",
    "工程物资": "engineering_materials",
    "固定资产净额": "fixed_assets_net_amount",
    "固定资产清理": "fixed_assets_clearance",
    "固定资产及清理合计": "fixed_assets_and_clearance_total",
    "生产性生物资产": "productive_biological_assets",
    "公益性生物资产": "public_welfare_biological_assets",
    "油气资产": "oil_and_gas_assets",
    "合同资产": "contract_assets",
    "使用权资产": "right_of_use_assets",
    "无形资产": "intangible_assets",
    "开发支出": "development_costs",
    "商誉": "goodwill",
    "长期待摊费用": "long_term_prepaid_expenses",
    "股权分置流通权": "equity_split_circulation_rights",
    "递延所得税资产": "deferred_tax_assets",
    "其他非流动资产": "other_non_current_assets",
    "非流动资产合计": "total_non_current_assets",
    "资产总计": "total_assets",
    "流动负债": "current_liabilities",
    "短期借款": "short_term_borrowings",
    "向中央银行借款": "borrowings_from_central_bank",
    "吸收存款及同业存放": "deposits_and_interbank_deposits",
    "拆入资金": "interbank_borrowings",
    "交易性金融负债": "trading_financial_liabilities",
    "衍生金融负债": "derivative_financial_liabilities",
    "应付票据及应付账款": "notes_and_accounts_payable",
    "应付票据": "notes_payable",
    "应付账款": "accounts_payable",
    "预收款项": "advances_from_customers",
    "合同负债": "contract_liabilities",
    "卖出回购金融资产款": "repurchase_of_financial_assets_sold",
    "应付手续费及佣金": "fees_and_commissions_payable",
    "应付职工薪酬": "employee_benefits_payable",
    "应交税费": "taxes_and_surcharges_payable",
    "应付利息": "interest_payable",
    "应付股利": "dividends_payable",
    "应付保证金": "margin_payable",
    "内部应付款": "internal_payable",
    "其他应付款": "other_payables",
    "其他应付款合计": "other_payables_total",
    "其他应交款": "other_levies_payable",
    "担保责任赔偿准备金": "guarantee_liability_reserve",
    "应付分保账款": "reinsurance_payable",
    "保险合同准备金": "insurance_contract_reserves",
    "代理买卖证券款": "securities_trading_agency_funds",
    "代理承销证券款": "underwriting_agency_funds",
    "国际票证结算": "international_bill_settlement",
    "国内票证结算": "domestic_bill_settlement",
    "预提费用": "accrued_expenses",
    "预计流动负债": "estimated_current_liabilities",
    "应付短期债券": "short_term_bonds_payable",
    "划分为持有待售的负债": "liabilities_held_for_sale",
    "一年内的递延收益": "deferred_income_due_within_one_year",
    "一年内到期的非流动负债": "non_current_liabilities_due_within_one_year",
    "其他流动负债": "other_current_liabilities",
    "流动负债合计": "total_current_liabilities",
    "非流动负债": "non_current_liabilities",
    "长期借款": "long_term_borrowings",
    "应付债券": "bonds_payable",
    "应付债券：优先股": "preferred_stock_payable",
    "应付债券：永续债": "perpetual_bonds_payable",
    "租赁负债": "lease_liabilities",
    "长期应付职工薪酬": "long_term_employee_benefits_payable",
    "长期应付款": "long_term_accounts_payable",
    "长期应付款合计": "long_term_payables_total",
    "专项应付款": "special_payables",
    "预计非流动负债": "estimated_non_current_liabilities",
    "长期递延收益": "long_term_deferred_income",
    "递延所得税负债": "deferred_tax_liabilities",
    "其他非流动负债": "other_non_current_liabilities",
    "非流动负债合计": "total_non_current_liabilities",
    "负债合计": "total_liabilities",
    "所有者权益": "owners_equity",
    "实收资本(或股本)": "paid_in_capital",
    "其他权益工具": "other_equity_instruments_total",
    "优先股": "preferred_stock",
    "永续债": "perpetual_bonds",
    "资本公积": "capital_reserve",
    "减:库存股": "treasury_stock",
    "其他综合收益": "other_comprehensive_income",
    "专项储备": "specific_reserve",
    "盈余公积": "surplus_reserve",
    "一般风险准备": "general_risk_reserve",
    "未确定的投资损失": "unrecognized_investment_loss",
    "未分配利润": "retained_earnings",
    "拟分配现金股利": "proposed_cash_dividends",
    "外币报表折算差额": "foreign_currency_translation_difference",
    "归属于母公司股东权益合计": "total_equity_attributable_to_parent",
    "少数股东权益": "minority_interests",
    "所有者权益(或股东权益)合计": "total_owners_equity",
    "负债和所有者权益(或股东权益)总计": "total_liabilities_and_equity",

    # ==================== 利润表特有 ====================
    "营业总收入": "operating_revenue",
    "营业收入": "revenue",
    "利息收入": "interest_income",
    "已赚保费": "earned_premium",
    "手续费及佣金收入": "fee_and_commission_income",
    "房地产销售收入": "real_estate_sales_income",
    "其他业务收入": "other_business_income",
    "营业总成本": "operating_cost_total",
    "营业成本": "operating_cost",
    "手续费及佣金支出": "fee_and_commission_expense",
    "房地产销售成本": "real_estate_sales_cost",
    "退保金": "surrender_refund",
    "赔付支出净额": "net_claim_payout",
    "提取保险合同准备金净额": "net_insurance_contract_reserve_withdrawal",
    "保单红利支出": "policy_dividend_expense",
    "分保费用": "reinsurance_expense",
    "其他业务成本": "other_business_cost",
    "营业税金及附加": "taxes_and_surcharges",
    "研发费用": "rd_expense",
    "销售费用": "sales_expense",
    "管理费用": "admin_expense",
    "财务费用": "finance_expense",
    "利息费用": "interest_expense",
    "利息支出": "interest_paid",
    "投资收益": "investment_income",
    "对联营企业和合营企业的投资收益": "investment_income_from_associates",
    "以摊余成本计量的金融资产终止确认产生的收益": "gain_from_amortized_cost_financial_assets_termination",
    "汇兑收益": "exchange_gain",
    "净敞口套期收益": "net_hedging_income",
    "公允价值变动收益": "fair_value_change_gain",
    "期货损益": "futures_gain_loss",
    "托管收益": "custody_income",
    "补贴收入": "subsidy_income",
    "其他收益": "other_gains",
    "资产减值损失": "asset_impairment_loss",
    "信用减值损失": "credit_impairment_loss",
    "其他业务利润": "other_business_profit",
    "资产处置收益": "asset_disposal_gain",
    "营业利润": "operating_profit",
    "营业外收入": "non_operating_income",
    "非流动资产处置利得": "gain_on_disposal_of_non_current_assets",
    "营业外支出": "non_operating_expense",
    "非流动资产处置损失": "loss_on_disposal_of_non_current_assets",
    "利润总额": "profit_before_tax",
    "所得税费用": "income_tax_expense",
    "未确认投资损失": "unrecognized_investment_loss",
    "净利润": "net_profit",
    "持续经营净利润": "net_profit_continuing_operations",
    "终止经营净利润": "net_profit_discontinued_operations",
    "归属于母公司所有者的净利润": "net_profit_parent_owners",
    "被合并方在合并前实现净利润": "net_profit_acquiree_before_combination",
    "少数股东损益": "minority_profit_share",
    "归属于母公司所有者的其他综合收益": "parent_other_comprehensive_income",
    "（一）以后不能重分类进损益的其他综合收益": "oci_not_reclassified_to_pl",
    "重新计量设定受益计划变动额": "remeasurement_of_defined_benefit_plan",
    "权益法下不能转损益的其他综合收益": "oci_equity_method_not_reclassified",
    "其他权益工具投资公允价值变动": "fvoci_equity_instruments",
    "企业自身信用风险公允价值变动": "credit_risk_fair_value_change",
    "（二）以后将重分类进损益的其他综合收益": "oci_will_be_reclassified_to_pl",
    "权益法下可转损益的其他综合收益": "equity_method_oci_reclassified",
    "可供出售金融资产公允价值变动损益": "available_for_sale_fv_change",
    "其他债权投资公允价值变动": "other_debt_investments_fv_change",
    "金融资产重分类计入其他综合收益的金额": "reclassified_from_fvoci_to_pl",
    "其他债权投资信用减值准备": "other_debt_investments_credit_impairment",
    "持有至到期投资重分类为可供出售金融资产损益": "reclassified_from_htm_to_afs",
    "现金流量套期储备": "cash_flow_hedge_reserve",
    "现金流量套期损益的有效部分": "effective_cash_flow_hedge",
    "外币财务报表折算差额": "foreign_currency_translation_reserve",
    "其他": "other_oci",
    "归属于少数股东的其他综合收益": "minority_other_comprehensive_income",
    "综合收益总额": "total_comprehensive_income",
    "归属于母公司所有者的综合收益总额": "parent_total_comprehensive_income",
    "归属于少数股东的综合收益总额": "minority_total_comprehensive_income",
    "基本每股收益": "basic_eps",
    "稀释每股收益": "diluted_eps",

    # ==================== 现金流量表特有 ====================
    "经营活动产生的现金流量": "operating_cash_flow",
    "销售商品、提供劳务收到的现金": "cash_received_from_sales",
    "客户存款和同业存放款项净增加额": "net_increase_deposits_interbank",
    "向中央银行借款净增加额": "net_increase_central_bank_borrowings",
    "向其他金融机构拆入资金净增加额": "net_increase_interbank_borrowings",
    "收到原保险合同保费取得的现金": "cash_received_from_insurance_premiums",
    "收到再保险业务现金净额": "net_cash_received_from_reinsurance",
    "保户储金及投资款净增加额": "net_increase_policyholder_funds",
    "处置交易性金融资产净增加额": "net_increase_trading_financial_assets_disposal",
    "收取利息、手续费及佣金的现金": "cash_received_from_fees_and_commissions",
    "拆入资金净增加额": "net_increase_borrowed_funds",
    "回购业务资金净增加额": "net_increase_repurchase_funds",
    "收到的税费返还": "tax_refund_received",
    "收到的其他与经营活动有关的现金": "other_cash_received_operating",
    "经营活动现金流入小计": "subtotal_cash_inflows_operating",
    "购买商品、接受劳务支付的现金": "cash_paid_for_goods_and_services",
    "客户贷款及垫款净增加额": "net_increase_loans_and_advances",
    "存放中央银行和同业款项净增加额": "net_increase_deposits_central_bank",
    "支付原保险合同赔付款项的现金": "cash_paid_for_insurance_claims",
    "支付利息、手续费及佣金的现金": "cash_paid_for_fees_and_commissions",
    "支付保单红利的现金": "cash_paid_for_policy_dividends",
    "支付给职工以及为职工支付的现金": "cash_paid_to_employees",
    "支付的各项税费": "cash_paid_for_taxes",
    "支付的其他与经营活动有关的现金": "other_cash_paid_operating",
    "经营活动现金流出小计": "subtotal_cash_outflows_operating",
    "经营活动产生的现金流量净额": "net_cash_flow_operating",
    "投资活动产生的现金流量": "investing_cash_flow",
    "收回投资所收到的现金": "cash_received_from_disposal_investments",
    "取得投资收益收到的现金": "cash_received_from_investment_income",
    "处置固定资产、无形资产和其他长期资产所收回的现金净额": "cash_received_from_disposal_fixed_assets",
    "处置子公司及其他营业单位收到的现金净额": "cash_received_from_disposal_subsidiaries",
    "收到的其他与投资活动有关的现金": "other_cash_received_investing",
    "减少质押和定期存款所收到的现金": "cash_received_from_reduction_pledged_deposits",
    "处置可供出售金融资产净增加额": "cash_received_from_disposal_afs",
    "投资活动现金流入小计": "subtotal_cash_inflows_investing",
    "购建固定资产、无形资产和其他长期资产所支付的现金": "cash_paid_for_acquisition_fixed_assets",
    "投资所支付的现金": "cash_paid_for_investments",
    "质押贷款净增加额": "net_increase_pledged_loans",
    "取得子公司及其他营业单位支付的现金净额": "cash_paid_for_acquisition_subsidiaries",
    "增加质押和定期存款所支付的现金": "cash_paid_for_increase_pledged_deposits",
    "支付的其他与投资活动有关的现金": "other_cash_paid_investing",
    "投资活动现金流出小计": "subtotal_cash_outflows_investing",
    "投资活动产生的现金流量净额": "net_cash_flow_investing",
    "筹资活动产生的现金流量": "financing_cash_flow",
    "吸收投资收到的现金": "cash_received_from_equity_investments",
    "子公司吸收少数股东投资收到的现金": "cash_received_from_minority_equity",
    "取得借款收到的现金": "cash_received_from_borrowings",
    "发行债券收到的现金": "cash_received_from_bond_issuance",
    "收到其他与筹资活动有关的现金": "other_cash_received_financing",
    "筹资活动现金流入小计": "subtotal_cash_inflows_financing",
    "偿还债务支付的现金": "cash_paid_for_debt_repayment",
    "分配股利、利润或偿付利息所支付的现金": "cash_paid_for_dividends_interest",
    "子公司支付给少数股东的股利、利润": "cash_paid_to_minority_shareholders",
    "支付其他与筹资活动有关的现金": "other_cash_paid_financing",
    "筹资活动现金流出小计": "subtotal_cash_outflows_financing",
    "筹资活动产生的现金流量净额": "net_cash_flow_financing",
    "汇率变动对现金及现金等价物的影响": "effect_of_exchange_rate_changes",
    "现金及现金等价物净增加额": "net_increase_cash_equivalents",
    "期初现金及现金等价物余额": "beginning_cash_equivalents",
    "现金的期末余额": "ending_cash",
    "现金的期初余额": "beginning_cash",
    "现金等价物的期末余额": "ending_cash_equivalents",
    "现金等价物的期初余额": "cash_equivalents",
    "期末现金及现金等价物余额": "ending_cash_and_equivalents",
}

STOCK_INDIVIDUAL_FUND_FLOW_MAPPING = {
    "主力净流入-净额": "main_net_inflow",
    "主力净流入-净占比": "main_net_inflow_pct",
    "超大单净流入-净额": "super_large_net_inflow",
    "超大单净流入-净占比": "super_large_net_inflow_pct",
    "大单净流入-净额": "large_net_inflow",
    "大单净流入-净占比": "large_net_inflow_pct",
    "中单净流入-净额": "medium_net_inflow",
    "中单净流入-净占比": "medium_net_inflow_pct",
    "小单净流入-净额": "small_net_inflow",
    "小单净流入-净占比": "small_net_inflow_pct",
    # 同花顺(10jqka)资金流列名（无"-净额/净占比"后缀）
    "主力净流入占比": "main_net_inflow_pct",
    "超大单净流入": "super_large_net_inflow",
    "超大单净流入占比": "super_large_net_inflow_pct",
    "大单净流入": "large_net_inflow",
    "大单净流入占比": "large_net_inflow_pct",
    "中单净流入": "medium_net_inflow",
    "中单净流入占比": "medium_net_inflow_pct",
    "小单净流入": "small_net_inflow",
    "小单净流入占比": "small_net_inflow_pct",
}

# 预测
FORECAST_SUMMARY_MAPPING = {
    "年度": "forecast_year",
    "预测机构数": "institution_count",
    "最小值": "forecast_min",
    "均值": "forecast_mean",
    "最大值": "forecast_max",
    "行业平均数": "industry_average",
    "forecast_type": "forecast_type",
    "机构名称": "institution_name",
    "研究员": "researcher",
    "预测年报每股收益2026预测": "forecast_eps_2026",
    "预测年报每股收益2027预测": "forecast_eps_2027",
    "预测年报每股收益2028预测": "forecast_eps_2028",
    "预测年报净利润2026预测": "forecast_net_profit_2026",
    "预测年报净利润2027预测": "forecast_net_profit_2027",
    "预测年报净利润2028预测": "forecast_net_profit_2028",
    "预测指标": "indicator",
    "2023-实际值": "actual_2023",
    "2024-实际值": "actual_2024",
    "2025-实际值": "actual_2025",
    "预测2026-平均": "forecast_2026_avg",
    "预测2027-平均": "forecast_2027_avg",
    "预测2028-平均": "forecast_2028_avg",
}

# 月度数据
STOCK_ACCOUNT_MAPPING = {
    '数据日期': 'stat_date',
    '新增投资者-数量': 'new_investor_count',
    '新增投资者-环比': 'new_investor_mom',
    '新增投资者-同比': 'new_investor_yoy',
    '期末投资者-总量': 'total_investor_amount',
    '期末投资者-A股账户': 'total_investor_a_share',
    '期末投资者-B股账户': 'total_investor_b_share',
    '沪深总市值': 'total_market_cap',
    '沪深户均市值': 'avg_market_cap_per_investor',
    '上证指数-收盘': 'sh_index_close',
    '上证指数-涨跌幅': 'sh_index_pct_change'
}

ALL_FIELD_MAPPING = {
    **DATE_FIELDS, **STOCK_FIELDS, **PRICE_FIELDS, **BOARD_FIELDS,
    **INDUSTRY_CONCEPT_FIELDS, **HEAT_FIELDS,
    **FOLLOW_FIELDS, **RANK_FIELDS, **BOARD_CHANGE_MAPPING, **STATISTICS_FIELDS, **ZT_FIELDS,
    **FINANCIAL_MAPPING, **FORECAST_SUMMARY_MAPPING, **STOCK_INDIVIDUAL_FUND_FLOW_MAPPING,
    **STOCK_ACCOUNT_MAPPING, **STOCK_HOLDER_NUM_MAPPING, **STOCK_LHB_MAPPING, **MARGIN_TRADING_DAILY_STAT_MAPPING,
    **STOCK_CONTINUOUS_UP_STATS_MAPPING, **STOCK_ANNOUNCEMENT_HOLDING_MAPPING


}

# ── 东方财富个股信息映射（stock_individual_info_em 专用） ────────

STOCK_INDIVIDUAL_INFO_MAPPING = {
    "股票代码": "symbol",
    "股票简称": "name",
    "总股本": "total_shares",
    "流通股": "float_shares",
    "行业": "industry",
    "总市值": "total_market_cap",
    "流通市值": "float_market_cap",
    "上市日期": "listing_date",
    "最新价": "latest_price",
}


# ============================================================================
# 工具函数
# ============================================================================

def map_fields(data: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    批量字段映射：源key → 目标库字段
    
    Args:
        data: 原始数据列表
        mapping: 字段映射字典
        
    Returns:
        映射后的数据列表
    """
    return [
        {mapping.get(key, key): value for key, value in item.items() if key in mapping}
        for item in data
    ]


def normalize_symbol(symbol: str, change_type: int = 1) -> str:
    """
    标准化股票代码
    
    Args:
        symbol: 股票代码
        change_type: 转换类型
        
    Returns:
        标准化的股票代码（带市场后缀）
    """
    if not symbol:
        return ""

    symbol = str(symbol).strip()
    if change_type == 1:
        if '.' not in symbol:
            if symbol.startswith('6'):
                symbol = f"{symbol}.SH"
            elif symbol.startswith('0') or symbol.startswith('3'):
                symbol = f"{symbol}.SZ"
            elif symbol.startswith('8'):
                symbol = f"{symbol}.BJ"
            elif symbol.startswith('9'):
                symbol = f"{symbol}.SH"  # B股
    if change_type == 2:
        if len(symbol) == 6:
            if symbol.startswith('6'):
                symbol = f"SH{symbol}"
            elif symbol.startswith('0') or symbol.startswith('3'):
                symbol = f"SZ{symbol}"
            elif symbol.startswith('8'):
                symbol = f"BJ{symbol}"
            elif symbol.startswith('9'):
                symbol = f"SH{symbol}"  # B股
    return symbol




def create_mapper(mapping: Dict[str, str], 
                  post_processors: Optional[List[Callable]] = None) -> Callable:
    """
    创建映射函数工厂
    
    Args:
        mapping: 字段映射字典
        post_processors: 后处理函数列表
        
    Returns:
        映射函数
    """
    def mapper(data: dict) -> dict:
        """
        通用映射函数
        
        Args:
            data: 原始数据字典
            
        Returns:
            处理后的结果字典
        """
        clean_data = data.get('data', [])
        if not clean_data:
            return success_result(data=[])
        
        # 应用字段映射
        result = map_fields(clean_data, mapping)
        
        # 应用后处理函数
        if post_processors:
            for processor in post_processors:
                result = processor(result)
        
        return success_result(data=result)
    
    return mapper


# ============================================================================
# 后处理函数
# ============================================================================

def add_concept_name(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加概念名称"""
    for item in result:
        if "concept_name" not in item and "symbol" in item:
            item["concept_name"] = item.get("symbol", "")
    return result


def add_industry_name(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加行业名称"""
    for item in result:
        if "industry_name" not in item and "symbol" in item:
            item["industry_name"] = item.get("symbol", "")
    return result


def add_stat_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加统计日期"""
    today = date.today().isoformat()
    for item in result:
        if "stat_date" not in item:
            item["stat_date"] = today
    return result


def add_rank_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加排名日期"""
    today = date.today().isoformat()
    for item in result:
        if "rank_date" not in item:
            item["rank_date"] = today
    return result


def add_change_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """添加异动日期"""
    today = date.today().isoformat()
    for item in result:
        if "change_date" not in item:
            item["change_date"] = today
    return result


def normalize_symbols(field_name: str = "symbol") -> Callable:
    """标准化股票代码"""
    def processor(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for item in result:
            if field_name in item:
                item[field_name] = normalize_symbol(item[field_name])
        return result
    return processor



def normalize_leader_stock(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化领涨股票代码"""
    for item in result:
        if "leader_stock" in item and item["leader_stock"]:
            item["leader_stock"] = normalize_symbol(item["leader_stock"])
    return result


def fill_stock_code_by_name(
    result: List[Dict[str, Any]],
    name_field: str = "name",      # 名称字段 symbol
    symbol_field: str = "symbol",   # 代码字段 name
) -> List[Dict[str, Any]]:
    """
    自动根据 股票名称 查询数据库，填充 symbol
    支持自定义字段名：name_field / symbol_field
    批量查询，高性能
    """
    from system_service.db_service import DBService
    db = DBService()

    # 1. 收集所有需要查询的股票名称
    name_list = []
    for item in result:
        stock_name = item.get(name_field, "").strip()
        if stock_name and symbol_field not in item:
            if stock_name not in name_list:
                name_list.append(stock_name)
    if not name_list:
        return result
    # 2. 批量查询（1次SQL）
    stock_map = db.query_batch(
        table_name="stocks_info",
        select_fields=['name', 'symbol'],
        where_field=name_field,
        where_values=name_list
    )
    # 转成字典：{股票名: 股票代码}
    name_to_code = {
        row[name_field]: row[symbol_field]
        for row in stock_map
    }
    # 3. 回填 code
    for item in result:
        stock_name = item.get(name_field, "").strip()
        code = name_to_code.get(stock_name)
        if code:
            item[symbol_field] = code
    return result



def add_symbol_from_code(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从code字段添加symbol字段"""
    for item in result:
        if "symbol" not in item and "code" in item:
            item["symbol"] = normalize_symbol(item["code"])
    return result


def get_stock_market(symbol: str) -> str:
    """
    根据股票代码判断所属市场
    返回：SH / SZ / BJ / SHB / SZB / None
    """
    if not symbol or not isinstance(symbol, str):
        return None
    symbol = symbol.strip()
    if symbol.startswith(('600', '601', '603', '605', '688', '689')):
        return 'SH'
    elif symbol.startswith(('000', '001', '002', '003', '300', '301')):
        return 'SZ'
    elif symbol.startswith(('8', '43')):
        return 'BJ'
    elif symbol.startswith('900'):
        return 'SHB'
    elif symbol.startswith('200'):
        return 'SZB'
    return None


def set_stock_delist(data: dict) -> dict:
    """将退市股票标记为 is_active=0"""
    stock_data = data.get('data', [])
    for item in stock_data:
        item["is_active"] = 0
    return success_result(data=stock_data)


def map_stock_basic(data: dict, source: str = "sh", source_symbol: str = None) -> dict:
    """
    股票基础信息专用映射（适配不同数据源的字段命名差异）

    :param data: 原始数据（含 'data' 键）
    :param source: 数据源标记 sh/sz/bj/delist/sz_delist/sh_delist/all
    :param source_symbol: stock_type（可选，用于填充 market_type）
    :return: 格式化后的结果字典
    """
    mapping_map = {
        "sh": {
            "证券代码": "symbol",
            "证券简称": "name",
            "公司全称": "full_name",
            "上市日期": "list_date"
        },
        "sz": {
            "A股代码": "symbol",
            "A股简称": "name",
            "公司全称": "full_name",
            "A股上市日期": "list_date",
            "所属行业": "industry",
        },
        "bj": {
            "证券代码": "symbol",
            "证券简称": "name",
            "上市日期": "list_date",
            "所属行业": "industry",
        },
        "delist": {
            "公司代码": "symbol",
            "公司简称": "name",
            "终止上市日期": "list_date",
            "暂停上市日期": "list_date",
            "上市日期": "list_date",
        },
        "sz_delist": {
            "证券代码": "symbol",
            "证券简称": "name",
        },
        "sh_delist": {
            "公司代码": "symbol",
            "公司简称": "name",
        },
        "all": {
            "code": "symbol",
            "name": "name"
        }
    }

    clean_data = data.get('data', [])
    if not clean_data:
        return success_result(data=[])

    result = map_fields(clean_data, mapping_map[source])

    if source in ['sh', 'sz', 'bj', 'all']:
        for item in result:
            item["market"] = get_stock_market(item.get("symbol", ""))
            if source_symbol:
                item["market_type"] = STOCK_TYPE_MAP.get(source_symbol, "")

    return success_result(data=result)


# ============================================================================
# 映射函数定义（保持原有函数名和签名）
# ============================================================================

# 通用函数
map_stock_ask = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[]
)

# 获取股票名称
map_stock_change_symbol = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[
        lambda res: fill_stock_code_by_name(
            result=res, name_field='symbol',  symbol_field='name'
        )
    ]
)

# 获取股票代码
map_stock_change_name = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[
        lambda res: fill_stock_code_by_name(
            result=res, name_field='name',  symbol_field='symbol'
        )
    ]
)


# 1. 概念板块指数日频率数据
map_board_concept_index = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[add_concept_name]
)


# 2. 行业板块指数日频率数据
map_board_industry_index = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[add_industry_name]
)

# 3. 行业一览表数据
map_board_industry_summary = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[
        add_stat_date,
        lambda res: fill_stock_code_by_name(
            result=res,
            name_field="leading_stock_name",  # 你要的名称字段
            symbol_field="leading_stock "    # 要填充的代码字段
        )
    ]
)

# 4. 概念板块简介数据
map_board_concept_info = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[]
)

# 5. 雪球关注排行榜数据
map_stock_hot_follow = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[
        normalize_symbols("symbol"),
        add_rank_date
    ]
)

# 6. 股票热度历史趋势及粉丝特征数据
map_stock_hot_rank_detail = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[add_symbol_from_code]
)

# 7. 个股人气榜热门关键词数据
map_stock_stat_date = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[add_stat_date]
)

# 8. 盘口异动数据
map_stock_changes = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[normalize_symbols("symbol")]
)


# 9. 当日板块异动详情数据
map_board_change = create_mapper(
    mapping=ALL_FIELD_MAPPING,
    post_processors=[
        add_change_date,
        normalize_leader_stock
    ]
)