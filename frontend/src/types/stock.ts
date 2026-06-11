/**
 * 龙虎榜相关类型定义
 *
 * 对应后端 DDL（lhb_models.py）和 API（routes.py LHB 区块）
 */

// ─── 通用 API 响应包裹 ─────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

// ─── 龙虎榜机构买卖每日统计 ─────────────────────────────────────
export interface LhbInstitutionTrading {
  serial_number: number;
  symbol: string;
  name: string;
  close_price: number;
  change_percent: number;
  buy_institution_count: number;
  sell_institution_count: number;
  institution_buy_amount: number;
  institution_sell_amount: number;
  institution_net_amount: number;
  total_trade_amount: number;
  institution_net_ratio: number;
  turnover_rate: number;
  circulating_market_cap: number;
  reason: string;
  trade_date: string;
  start_date: string;
  end_date: string;
}

// ─── 龙虎榜详情 ─────────────────────────────────────────────────
export interface LhbDetail {
  serial_number: number;
  symbol: string;
  name: string;
  trade_date: string;
  interpretation: string;
  close_price: number;
  change_percent: number;
  lhb_net_amount: number;
  lhb_buy_amount: number;
  lhb_sell_amount: number;
  lhb_turnover_amount: number;
  total_trade_amount: number;
  net_amount_ratio: number;
  turnover_ratio: number;
  turnover_rate: number;
  circulating_market_cap: number;
  reason: string;
  after_1d_pct_change: number | null;
  after_2d_pct_change: number | null;
  after_5d_pct_change: number | null;
  after_10d_pct_change: number | null;
  start_date: string;
  end_date: string;
}

// ─── 个股上榜统计 ───────────────────────────────────────────────
export interface LhbStockStatistic {
  serial_number: number;
  symbol: string;
  name: string;
  data_type: string;
  latest_trade_date: string;
  close_price: string;
  change_percent: string;
  total_lhb_times: number;
  lhb_net_amount: string;
  lhb_buy_amount: string;
  lhb_sell_amount: string;
  lhb_total_amount: string;
  buy_institution_times: number;
  sell_institution_times: number;
  institution_net_amount: string;
  institution_buy_amount: string;
  institution_sell_amount: string;
  pct_change_1m: string;
  pct_change_3m: string;
  pct_change_6m: string;
  pct_change_1y: string;
}

// ─── 每日活跃营业部 ─────────────────────────────────────────────
export interface LhbBrokerDaily {
  serial_number: number;
  broker_name: string;
  trade_date: string;
  buy_stock_count: number;
  sell_stock_count: number;
  total_buy_amount: number;
  total_sell_amount: number;
  net_buy_amount: number;
  buy_stocks: string;
  broker_code: string;
}

// ─── 营业部排行 ─────────────────────────────────────────────────
export interface LhbBrokerPerformance {
  serial_number: number;
  broker_name: string;
  data_type: string;
  buy_count_1d: number;
  avg_return_1d: string;
  up_prob_1d: string;
  buy_count_2d: number;
  avg_return_2d: string;
  up_prob_2d: string;
  buy_count_3d: number;
  avg_return_3d: string;
  up_prob_3d: string;
  buy_count_5d: number;
  avg_return_5d: string;
  up_prob_5d: string;
  buy_count_10d: number;
  avg_return_10d: string;
  up_prob_10d: string;
}

// ─── 营业部综合统计 ─────────────────────────────────────────────
export interface LhbBrokerSummary {
  serial_number: number;
  broker_name: string;
  data_type: string;
  total_lhb_amount: number;
  total_lhb_times: number;
  total_buy_amount: number;
  total_buy_times: number;
  total_sell_amount: number;
  total_sell_times: number;
}

// ─── 上榜次数最多 ───────────────────────────────────────────────
export interface LhbBrokerMost {
  serial_number: number;
  broker_name: string;
  total_lhb_times: number;
  total_fund_amount: string;
  year_total_times: number;
  year_buy_stock_count: number;
  year_3d_success_rate: string;
}

// ═══════════════════════════════════════════════════════════════
// 资金流向相关类型定义（对应 /api/stock/get-stock-fund-*）
// ═══════════════════════════════════════════════════════════════

/** 个股资金流-即时（period_type=即时） */
export interface FundFlowIndividualImmediate {
  serial_number: number;
  symbol: string | number;
  name: string;
  latest_price: number;
  change_percent: string;       // 例 "20.02%"
  turnover_rate: string;        // 例 "13.80%"
  outflow_amount: string;       // 例 "6.22亿"
  inflow_amount: string;        // 例 "6.10亿"
  net_amount: string;           // 例 "1150.70万"
  amount: string;               // 例 "12.32亿"
  stat_date: string;
  period_type: string;
  cache_key?: string;
}

/** 个股资金流-历史排行（period_type=3日/5日/10日/20日排行） */
export interface FundFlowIndividualHistory {
  serial_number: number;
  symbol: string | number;
  name: string;
  latest_price: number;
  phase_change: string;         // 阶段涨跌幅
  net_amount: string;           // 阶段净流入
  stat_date: string;
  period_type: string;
  cache_key?: string;
}

/** 行业/概念资金流-即时 */
export interface FundFlowConceptImmediate {
  serial_number: number;
  industry: string;             // 行业/概念名
  index_price: number;
  change_ratio: number;         // 涨跌幅 %
  outflow_amount: number;       // 亿
  inflow_amount: number;        // 亿
  net_amount: number;           // 亿
  company_count: number;
  leading_stock_name: string;
  leading_stock_change: number; // 龙头股涨幅 %
  current_price: number;        // 龙头股现价
  stat_date: string;
  period_type: string;
  cache_key?: string;
}

/** 行业/概念资金流-历史排行 */
export interface FundFlowConceptHistory {
  serial_number: number;
  industry: string;
  company_count: number;
  index_price: number;
  phase_change: string;         // 阶段涨跌幅 "1.93%"
  outflow_amount: number;       // 亿
  inflow_amount: number;        // 亿
  net_amount: number;           // 亿（可负）
  stat_date: string;
  period_type: string;
  cache_key?: string;
}

export type FundFlowPeriod = '即时' | '3日排行' | '5日排行' | '10日排行' | '20日排行';

// ═══════════════════════════════════════════════════════════════
// 行业 / 概念板块（Sector）类型定义
//
// 对应后端接口（实测于 2026-05-30 13:55）：
//   - /api/stock/get-stock-board                       行业一览（汇总，含 leading_stock_*）
//   - /api/stock/get_all_stock_board_industry          行业名称+代码
//   - /api/stock/get-stock-board-concept-info?symbol=  概念简介（单条）
//   - /api/stock/get-stock-board-change-em             今日板块异动
//   - /api/stock/get_stock_changes_em?symbol=异动类型  盘口异动详细
//   - /api/stock/get-stock-fund-concept?symbol=即时    同花顺概念资金流（即时/3/5/10/20日）
// ═══════════════════════════════════════════════════════════════

/** 行业一览（同花顺，含领涨股） */
export interface IndustryBoardSummary {
  serial_number: number;
  board_name: string;            // 板块名称
  change_percent: number;        // 涨跌幅 %
  total_volume: number;          // 总成交量（万手）
  total_amount: number;          // 总成交额（亿元）
  net_inflow: number;            // 净流入（亿元）
  rise_count: number;
  fall_count: number;
  avg_price: number;             // 板块均价
  leading_stock_name: string;
  leading_stock_price: number;
  leading_stock_change: number;
  stat_date: string;
  cache_key?: string;
}

/** 行业名称+代码（用于筛选/联想） */
export interface IndustryBoardCode {
  serial_number: number;
  board_name: string;
  board_code: string;
  cache_key?: string;
}

/** 概念板块简介（同花顺，字段均为字符串） */
export interface ConceptBoardInfo {
  open_price: string;            // 开盘价 "2013.90"
  pre_close: string;             // 昨收 "2013.51"
  low_price: string;             // 最低价 "2011.09"
  high_price: string;            // 最高价 "2077.43"
  volume: string;                // 成交量(万手) "12019.90"
  board_change_percent: string;  // 涨跌幅 "2.02%"
  rank_position: string;         // 排名 "113/390"
  up_down_count: string;         // 涨跌家数 "261/82"
  net_inflow: string;            // 净流入(亿) "-6.53"
  amount: string;                // 成交额(亿) "3020.91"
  cache_key?: string;
}

/** 板块异动（东方财富，按 board_name 聚合） */
export interface BoardChangeItem {
  board_name: string;
  change_percent: number;        // 板块涨跌幅 %
  main_net_inflow: number;       // 主力净流入（元）
  total_change_count: number;    // 板块异动次数
  most_frequent_stock_code: string;
  most_frequent_stock_name: string;
  most_frequent_trade_direction: string;
  change_type_list: any;
  change_date: string;
  cache_key?: string;
}

/** 盘口异动单条（按异动类型筛选个股） */
export interface StockChangeItem {
  change_type: string;
  occur_time: string;
  stat_date: string;
  symbol: string;
  name: string;
  price: number;
  change_percent: number;
  volume: number | null;
  amount: number | null;
  strength_level: number;
  change_reason: string | null;
  description: string | null;
  raw_info: string;
  cache_key?: string;
}

/** 板块指数 K线（行业/概念通用，同花顺） */
export interface BoardIndexKline {
  trade_date: string;            // YYYY-MM-DD
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  amount: number;
  concept_name?: string;         // 仅概念K线返回
  cache_key?: string;
}

/** 板块内个股资金流 / 主力净流入排名（东方财富，字符串格式带亿/万/%后缀） */
export interface SectorStockFundFlowItem {
  serial_number: number;
  symbol: number;
  name: string;
  latest_price: number;
  change_percent: string;       // "15.72%" 带 % 后缀
  turnover_rate: string;        // "16.28%" 带 % 后缀
  outflow_amount: string;       // "15.18亿" / "5426.29万"
  inflow_amount: string;        // "11.21亿" / "3312.04万"
  net_amount: string;           // "3.97亿" / "-2760.14万"（含正负号）
  amount: string;               // "26.39亿" / "9047.79万"
  cache_key?: string;
}

// ═══════════════════════════════════════════════════════════════
// 个股中心相关类型定义
// ═══════════════════════════════════════════════════════════════

/** 雪球热门关键词 */
export interface StockHotKeyword {
  stat_date: string;
  symbol: string;
  concept_name: string;
  concept_code: string;
  heat: number;
  cache_key?: string;
}

/** 历史 K 线（日/周/月） */
export interface StockKlineDaily {
  trade_date: string;
  symbol: string;
  open_price: number;
  close_price: number;
  high_price: number;
  low_price: number;
  volume: number;
  amount: number;
  amplitude: number;
  change_percent: number;
  change_amount: number;
  turnover_rate: number;
  cache_key?: string;
}

/** 分钟级 K 线（mootdx） */
export interface StockKlineMinute {
  symbol: string;
  name: string;
  datetime: string;
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  open: number;
  high: number;
  low: number;
  close: number;
  vol: number;
  amount: number;
  volume: number;
}

/** 资产负债表行 */
export interface StockBalanceSheet {
  report_date: string;
  total_assets?: number | null;
  total_current_assets?: number | null;
  total_non_current_assets?: number | null;
  monetary_funds?: number | null;
  accounts_receivable?: number | null;
  inventories?: number | null;
  fixed_assets_net_amount?: number | null;
  total_liabilities?: number | null;
  total_current_liabilities?: number | null;
  total_non_current_liabilities?: number | null;
  short_term_borrowings?: number | null;
  long_term_borrowings?: number | null;
  accounts_payable?: number | null;
  total_owners_equity?: number | null;
  paid_in_capital?: number | null;
  retained_earnings?: number | null;
  currency?: string | null;
  is_audited?: string | null;
  announcement_date?: string | null;
  [key: string]: any;
}

/** 千股千评-用户关注指数 */
export interface StockCommentFocus {
  '交易日': string;
  '用户关注指数': number;
}

/** 千股千评-市场参与意愿 */
export interface StockCommentDesire {
  trade_date: string;
  symbol: string;
  desire_value: number;
  avg_5_desire: number;
  desire_change: number;
  avg_5_change: number;
  name: string;
  cache_key?: string;
}

/** 股东户数详情 */
export interface StockHolderDetail {
  end_date: string;
  interval_pct_change: number;
  holder_num_current: number;
  holder_num_previous: number;
  holder_num_change: number;
  holder_num_change_pct: number;
  avg_market_cap_per_holder: number;
  avg_share_per_holder: number;
  total_market_cap: number;
  total_shares: number;
  share_change: number;
  share_change_reason: string | null;
  announce_date: string;
  symbol: string;
  name: string;
  cache_key?: string;
}

/** K 线周期 */
export type KlinePeriod = 'daily' | 'weekly' | 'monthly';

/** 分钟周期（mootdx） */
export type MinutePeriod = '1' | '5' | '15' | '30' | '60' | 'day' | 'week' | 'month';

// ═══════════════════════════════════════════════════════════════
// 涨停股池相关类型定义
//
// 后端接口：
//   - GET /api/stock/get-stock-zt-pool-em           当日涨停股池
//   - GET /api/stock/get-stock-zt-pool-previous-em   昨日涨停股池
//   - GET /api/stock/get-stock-zt-pool-strong-em     强势股池
//   - GET /api/stock/get-stock-zt-pool-zbgc-em       炸板股池
//   - GET /api/stock/get-stock-zt-pool-dtgc-em       跌停股池
// ═══════════════════════════════════════════════════════════════

/** 涨停/跌停/强势股池 通用条目 */
export interface LimitUpPoolItem {
  serial_number: number;
  symbol: string;
  name: string;
  change_percent: number;        // 涨跌幅 %
  latest_price: number;           // 最新价
  amount: number;                 // 成交额
  circulating_market_cap: number; // 流通市值
  total_market_cap: number;       // 总市值
  turnover_rate: number;          // 换手率 %
  industry: string;               // 所属行业

  // 涨停池特有
  limit_fund?: number;            // 封板资金
  first_limit_time?: string;      // 首次封板时间 (HHMMSS)
  last_limit_time?: string;       // 最后封板时间 (HHMMSS)
  open_count?: number;            // 炸板次数
  limit_statistic?: string;       // 涨停统计 (如 "3/3")
  limit_times?: number;           // 连板数

  // 昨日涨停特有
  limit_up_price?: number;        // 涨停价
  speed?: number;                 // 涨速
  amplitude?: number;             // 振幅
  prev_limit_time?: string;       // 昨日封板时间
  prev_limit_times?: number;      // 昨日连板数

  // 强势股池特有
  is_new_high?: string;           // 是否新高 ("是"/"否")
  volume_ratio?: number;          // 量比
  selection_reason?: string;      // 入选理由

  // 通用
  stat_date?: string;
  cache_key?: string;
}

// ═══════════════════════════════════════════════════════════════
// 行情与K线相关类型定义
//
// 后端接口：
//   - GET /api/stock/get-stock-market-fund-flow    大盘资金流向（含指数行情）
//   - GET /api/stock/get-stock-rank-lxsz-ths       连续上涨
//   - GET /api/stock/get-stock-rank-lxxd-ths       连续下跌
//   - GET /api/stock/get-stock-rank-ljqs-ths       量价齐升
//   - GET /api/stock/get-stock-rank-ljqd-ths       量价齐跌
//   - GET /api/stock/get-stock-account-statistics-em 股票账户月度统计
// ═══════════════════════════════════════════════════════════════

/** 大盘资金流向（含上证/深证指数行情） */
export interface MarketFundFlow {
  trade_date: string;              // 交易日期
  sh_close: number;                // 上证-收盘价
  sh_pct_change: number;           // 上证-涨跌幅(%)
  sz_close: number;                // 深证-收盘价
  sz_pct_change: number;           // 深证-涨跌幅(%)
  main_net_inflow: number;         // 主力净流入-净额
  main_net_inflow_pct: number;     // 主力净流入-净占比(%)
  super_large_net_inflow: number;  // 超大单净流入-净额
  super_large_net_inflow_pct: number; // 超大单净流入-净占比(%)
  large_net_inflow: number;        // 大单净流入-净额
  large_net_inflow_pct: number;    // 大单净流入-净占比(%)
  medium_net_inflow: number;       // 中单净流入-净额
  medium_net_inflow_pct: number;   // 中单净流入-净占比(%)
  small_net_inflow: number;        // 小单净流入-净额
  small_net_inflow_pct: number;    // 小单净流入-净占比(%)
  cache_key?: string;
}

/** 连续上涨/下跌统计 */
export interface StockConsecutiveStats {
  serial_number: number;
  symbol: string;
  name: string;
  close_price: number;             // 最新收盘价
  high_price: number;              // 阶段最高价
  low_price: number;               // 阶段最低价
  consecutive_up_days: number;     // 连续涨跌天数
  consecutive_up_pct: number;      // 连续涨跌幅(%)
  cumulative_turnover_rate: number; // 累计换手率(%)
  industry: string;                // 所属行业
  stat_date: string;
  stats_type?: string;             // "连续上涨" / "连续下跌"
  cache_key?: string;
}

/** 量价齐升/齐跌统计 */
export interface StockVolumePriceStats {
  serial_number: number | string;
  symbol: string;
  name: string;
  latest_price: number;            // 最新价
  volume_price_up_days: number;    // 量价变化天数
  stage_pct_change: number;        // 阶段涨跌幅(%)
  cumulative_turnover_rate: number;// 累计换手率(%)
  industry: string;                // 所属行业
  stat_date: string;
  cache_key?: string;
}

/** 股票账户月度统计 */
export interface InvestorMarketStats {
  stat_date: string;               // 数据日期(按月)
  new_investor_count: number | null;    // 新增投资者数量(万户)
  new_investor_mom: number | null;      // 新增投资者-环比(%)
  new_investor_yoy: number | null;      // 新增投资者-同比(%)
  total_investor_amount: number | null; // 期末投资者总量(万户)
  total_investor_a_share: number | null; // 期末A股账户(万户)
  total_investor_b_share: number | null; // 期末B股账户(万户)
  total_market_cap: number | null;      // 沪深总市值(亿元)
  avg_market_cap_per_investor: number | null; // 沪深户均市值(万元/户)
  sh_index_close: number | null;        // 上证指数收盘价
  sh_index_pct_change: number | null;   // 上证指数涨跌幅(%)
  cache_key?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 融资融券（Margin Trading）
// 后端接口：
//   GET /api/stock/get-stock-margin-account-info       两融账户信息
//   GET /api/stock/get-stock-margin-sse                上交所融资融券汇总
//   GET /api/stock/get-stock-margin-detail-szse        深交所融资融券明细
//   GET /api/stock/get-stock-margin-detail-sse         上交所融资融券明细
// ═══════════════════════════════════════════════════════════════════════════════

/** 两融账户信息（东方财富，已映射为英文 key，数据库缓存返回） */
export interface MarginAccountInfo {
  id?: number;
  trade_date: string;                          // 信用交易日期 YYYY-MM-DD
  margin_balance: number | string;             // 融资余额（亿元）
  short_balance: number | string;              // 融券余额（亿元）
  margin_buy_amount: number | string;          // 融资买入额（亿元）
  short_sell_amount: number | string;          // 融券卖出额（亿元）
  securities_company_count: number;            // 证券公司数量
  branch_office_count: number;                 // 营业部数量
  individual_investor_count: number | string;  // 个人投资者数量（万户）
  institution_investor_count: number | string; // 机构投资者数量
  active_trader_count: number | string;        // 参与交易的投资者数量
  liability_investor_count: number | string;   // 有融资融券负债的投资者数量
  collateral_value: number | string;           // 担保物总价值（亿元）
  avg_maintenance_ratio: number | string;      // 平均维持担保比例（%）
  create_time?: string;
  update_time?: string;
  cache_key?: string;
  is_deleted?: number;
}

/** 上交所融资融券汇总（已映射为英文 key） */
export interface MarginSseSummary {
  trade_date: string;                  // 信用交易日期 YYYYMMDD
  margin_balance: number;              // 融资余额（元）
  margin_buy_amount: number;           // 融资买入额（元）
  short_volume: number;                // 融券余量（股）
  short_balance: number;               // 融券余额（元）
  short_sell_volume: number;           // 融券卖出量（股）
  margin_short_balance: number;        // 融资融券余额合计（元）
  cache_key?: string;
}

/** 深交所融资融券明细（保留中文 key，后端未做映射） */
export interface MarginDetailSzse {
  证券代码: string;
  证券简称: string;
  融资买入额: number;
  融资余额: number;
  融券卖出量: number;
  融券余量: number;
  融券余额: number;
  融资融券余额: number;
  cache_key?: string;
}

/** 上交所融资融券明细（保留中文 key，后端未做映射） */
export interface MarginDetailSse {
  信用交易日期: string;
  标的证券代码: string;
  标的证券简称: string;
  融资余额: number;
  融资买入额: number;
  融资偿还额: number;
  融券余量: number;
  融券卖出量: number;
  融券偿还量: number;
  cache_key?: string;
}

// ═══════════════════════════════════════════════════════════════════
//  模拟交易
// ═══════════════════════════════════════════════════════════════════

/** 模拟账户信息 */
export interface SimAccount {
  initial_capital: number;
  available_cash: number;
  frozen_cash: number;
  total_assets: number;
}

/** 模拟持仓 */
export interface SimPosition {
  symbol: string;
  name: string;
  quantity: number;
  cost_price: number;
  current_price: number;
  market_value: number;
  profit_loss: number;
  profit_loss_pct: number;
  available_qty: number;
  updated_at: string;
}

/** 模拟委托单 */
export interface SimOrder {
  id: string;
  symbol: string;
  name: string;
  direction: 'buy' | 'sell';
  price: number;
  quantity: number;
  filled_qty: number;
  status: 'pending' | 'filled' | 'cancelled' | 'partial';
  created_at: string;
  updated_at: string;
}

/** 模拟成交记录 */
export interface SimTrade {
  id: string;
  order_id: string;
  symbol: string;
  name: string;
  direction: 'buy' | 'sell';
  price: number;
  quantity: number;
  amount: number;
  commission: number;
  trade_date: string;
}

/** 每日资产快照（权益曲线用） */
export interface SimDailyRecord {
  date: string;
  total_assets: number;
  available_cash: number;
  market_value: number;
}

/** 下单请求参数 */
export interface SimPlaceOrderParams {
  symbol: string;
  name: string;
  direction: 'buy' | 'sell';
  price: number;
  quantity: number;
}

/** 账户统计摘要 */
export interface SimStats {
  total_trades: number;
  win_count: number;
  lose_count: number;
  win_rate: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  avg_hold_days: number;
  total_commission: number;
}

// ═══════════════════════════════════════════════════════════════════
//  核心动态
// ═══════════════════════════════════════════════════════════════════

/** 昨日涨幅股票条目（get-yesterday-surge-stocks 返回结构） */
export interface SurgeStockItem {
  symbol: string;             // 股票代码
  name: string;               // 股票名称
  yesterday_close: number;    // 昨日收盘价
  prev_close: number;         // 前日收盘价
  change_percent: number;     // 涨跌幅（%）
  volume: number;             // 成交量（股）
  amount: number;             // 成交额（元）
}

// ─── 实时行情（mootdx + Redis） ──────────────────────────────────

export interface RealtimeQuote {
  symbol: string;             // 股票代码
  name: string;               // 股票名称
  price: number;              // 当前价
  last_close: number;         // 昨收
  open: number;               // 今开
  high: number;               // 最高
  low: number;                // 最低
  volume: number;             // 成交量（手）
  amount: number;             // 成交额（元）
  change: number;             // 涨跌额
  change_percent: number;     // 涨跌幅（%）
  bid1: number;               // 买一价
  bid1_vol: number;           // 买一量（手）
  ask1: number;               // 卖一价
  ask1_vol: number;           // 卖一量（手）
  bid2?: number;
  ask2?: number;
  bid3?: number;
  ask3?: number;
  bid4?: number;
  ask4?: number;
  bid5?: number;
  ask5?: number;
  turnover: number;           // 换手率
  amplitude: number;          // 振幅
  update_time: string;        // 更新时间 HH:MM:SS
}

/** 实时行情字典 { symbol → RealtimeQuote } */
export type RealtimeQuoteDict = Record<string, RealtimeQuote>;

// ─── 技术指标 ──────────────────────────────────────────────────

/** 指标元信息 */
export interface IndicatorMeta {
  name: string;
  label: string;
  params: Record<string, any>;
  fields: string[];
}

/** 单日技术指标数据（后端 /indicators 接口 data 数组元素） */
export interface IndicatorData {
  trade_date: string;
  symbol: string;
  name?: string;
  // MA
  ma_5?: number;
  ma_10?: number;
  ma_20?: number;
  ma_60?: number;
  ma_120?: number;
  ma_250?: number;
  // BOLL
  boll_ma?: number;
  boll_upper?: number;
  boll_lower?: number;
  boll_width?: number;
  // SAR
  sar?: number;
  // VOL
  vol?: number;
  vol_ma_5?: number;
  vol_ma_10?: number;
  vol_ma_20?: number;
  // MACD
  macd_dif?: number;
  macd_dea?: number;
  macd_bar?: number;
  // KDJ
  kdj_k?: number;
  kdj_d?: number;
  kdj_j?: number;
  // RSI
  rsi_6?: number;
  rsi_12?: number;
  rsi_24?: number;
  // WR
  wr_6?: number;
  wr_10?: number;
  wr_14?: number;
  // CCI
  cci?: number;
  // BIAS
  bias_6?: number;
  bias_12?: number;
  bias_24?: number;
  // PSY
  psy_12?: number;
  psy_24?: number;
  psy_ma_12?: number;
  psy_ma_24?: number;
  // OBV
  obv?: number;
  obv_ma?: number;
  // DMI
  pdi?: number;
  mdi?: number;
  adx?: number;
  adxr?: number;
  // ROC
  roc?: number;
  roc_ma?: number;
  [key: string]: any;
}

/** 分时Tick数据 */
export interface MinuteTickItem {
  symbol: string;
  trade_date: string;
  minute_idx: number;
  price: number;
  volume: number;
  amount: number;
  avg_price: number;
  change_percent: number;
  direction: string;
}

/** 分笔成交数据（实时 / 历史） */
export interface TransactionItem {
  symbol: string;
  trade_date: string;
  seq: number;
  time_label: string;
  price: number;
  vol: number;
  volume: number;
  amount?: number;
  num?: number | null;
  buyorsell: number;
  market: number;
  data_type: 'history' | 'realtime' | string;
  auto_clean?: number;
  retention_days?: number;
  expire_date?: string | null;
}

// ─── 量能指标（后端新增） ──────────────────────────────────

/** VWMA (成交量加权移动平均) 数据点 */
export interface VolumeVwmaPoint {
  trade_date: string;
  symbol: string;
  vwma: number;
}

/** VR (成交量比率) 数据点 */
export interface VolumeVrPoint {
  trade_date: string;
  symbol: string;
  vr: number;
  vr_ma?: number;
}

/** Volume Bias (成交量乖离率) 数据点 */
export interface VolumeBiasPoint {
  trade_date: string;
  symbol: string;
  volume_bias_5: number;
  volume_bias_10: number;
  volume_bias_20: number;
}
