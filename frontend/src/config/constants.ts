/**
 * 全局配置常量
 *
 * 集中管理 API 端点、超时、业务常量等所有硬编码值。
 * 避免在各模块中分散定义「魔数」。
 */

// ─── API 基础路径 ──────────────────────────────────────────────
export const API_BASE = '/api';

// ─── 超时 ──────────────────────────────────────────────────────
export const HTTP_TIMEOUT = 30000;
export const SLOW_API_TIMEOUT = 120_000;

// ─── 股票 API 端点 ────────────────────────────────────────────
export const STOCK_API = {
  // 龙虎榜
  LHB_INSTITUTION_TRADING: `${API_BASE}/stock/get-stock-lhb-jgmmtj-em`,
  LHB_DETAIL: `${API_BASE}/stock/get-stock-lhb-detail`,
  LHB_STOCK_STATISTIC: `${API_BASE}/stock/get-stock-lhb-stock-statistic-em`,
  LHB_BROKER_DAILY: `${API_BASE}/stock/get-stock-lhb-hyyyb-em`,
  LHB_BROKER_PERFORMANCE: `${API_BASE}/stock/get-stock-yybph-em-service`,
  LHB_BROKER_SUMMARY: `${API_BASE}/stock/get-stock-traderstatistic-em`,
  LHB_BROKER_MOST: `${API_BASE}/stock/get-stock-lh-yyh-most`,

  // 融资融券
  MARGIN_ACCOUNT_INFO: `${API_BASE}/stock/get-stock-margin-account-info`,
  MARGIN_SSE_SUMMARY: `${API_BASE}/stock/get-stock-margin-sse`,
  MARGIN_DETAIL_SZSE: `${API_BASE}/stock/get-stock-margin-detail-szse`,
  MARGIN_DETAIL_SSE: `${API_BASE}/stock/get-stock-margin-detail-sse`,

  // 资金流向
  FUND_FLOW_INDIVIDUAL: `${API_BASE}/stock/get-stock-fund-flow-individual`,
  FUND_FLOW_CONCEPT: `${API_BASE}/stock/get-stock-fund-concept`,

  // 涨停股池
  LIMIT_UP_POOL: `${API_BASE}/stock/get-stock-zt-pool-em`,
  LIMIT_UP_PREVIOUS: `${API_BASE}/stock/get-stock-zt-pool-previous-em`,
  LIMIT_UP_STRONG: `${API_BASE}/stock/get-stock-zt-pool-strong-em`,
  LIMIT_UP_ZBGC: `${API_BASE}/stock/get-stock-zt-pool-zbgc-em`,
  LIMIT_UP_DTGC: `${API_BASE}/stock/get-stock-zt-pool-dtgc-em`,

  // 行情与 K 线
  MARKET_FUND_FLOW: `${API_BASE}/stock/get-stock-market-fund-flow`,
  RANK_CONSECUTIVE_UP: `${API_BASE}/stock/get-stock-rank-lxsz-ths`,
  RANK_CONSECUTIVE_DOWN: `${API_BASE}/stock/get-stock-rank-lxxd-ths`,
  RANK_VOLUME_PRICE_UP: `${API_BASE}/stock/get-stock-rank-ljqs-ths`,
  RANK_VOLUME_PRICE_DOWN: `${API_BASE}/stock/get-stock-rank-ljqd-ths`,
  ACCOUNT_STATISTICS: `${API_BASE}/stock/get-stock-account-statistics-em`,
  TRIGGER_KLINE_COLLECT: `${API_BASE}/stock/get-kline/ws-trigger`,
  BACKFILL_INDICATORS: `${API_BASE}/stock/indicators/backfill`,

  // 行业 / 概念板块
  BOARD_SUMMARY: `${API_BASE}/stock/get-stock-board`,
  BOARD_INDUSTRY_CODES: `${API_BASE}/stock/get_all_stock_board_industry`,
  BOARD_CONCEPT_INFO: `${API_BASE}/stock/get-stock-board-concept-info`,
  BOARD_CHANGE: `${API_BASE}/stock/get-stock-board-change-em`,
  STOCK_CHANGES: `${API_BASE}/stock/get_stock_changes_em`,
  BOARD_CONCEPT_INDEX_KLINE: `${API_BASE}/stock/get-stock-board-concept-index-ths`,
  BOARD_INDUSTRY_INDEX_KLINE: `${API_BASE}/stock/get-stock-board-industry-index-ths`,
  BOARD_INDUSTRY_CONS: `${API_BASE}/stock/get-stock-board-industry-cons`,
  BOARD_CONCEPT_CONS: `${API_BASE}/stock/get-stock-board-concept-cons`,
  SECTOR_FUND_FLOW: `${API_BASE}/stock/get-sector-fund-flow`,
  SECTOR_FUND_SUMMARY: `${API_BASE}/stock/get-sector-fund-summary`,
  SECTOR_FUND_FLOW_SUMMARY: `${API_BASE}/stock/get-sector-fund-flow-summary`,

  // 个股中心
  KLINE_DAILY: `${API_BASE}/stock/get-kline`,
  KLINE_MINUTE: `${API_BASE}/stock/get-stock-zh-a-hist-min-em`,
  FINANCIAL_REPORT: `${API_BASE}/stock/get-stock-financial-report-sina`,
  HOT_KEYWORD: `${API_BASE}/stock/get-stock_hot_keyword_em`,
  COMMENT_FOCUS: `${API_BASE}/stock/get-stock-comment-focus-em`,
  COMMENT_DESIRE: `${API_BASE}/stock/get-stock-comment-desire-em`,
  HOLDER_DETAIL: `${API_BASE}/stock/get-stock-gdhs-detail-em`,

  // 股票历史日K（新浪财经）
  ZH_A_DAILY: `${API_BASE}/stock/get-stock-zh-a-daily`,

  // 核心动态
  SURGE_STOCKS: `${API_BASE}/stock/get-yesterday-surge-stocks`,

  // 实时行情（mootdx + Redis，不入库）
  REALTIME_QUOTES: `${API_BASE}/stock/realtime-quotes`,

  // 技术指标
  INDICATORS: `${API_BASE}/stock/indicators`,
  INDICATORS_META: `${API_BASE}/stock/indicators/meta`,
  INDICATORS_LATEST: `${API_BASE}/stock/indicators/latest`,
  INDICATORS_BATCH: `${API_BASE}/stock/indicators/batch`,

  // 历史分时Tick / 分笔成交
  MINUTE_TICK: `${API_BASE}/stock/get-minute-tick`,
  TRANSACTION: `${API_BASE}/stock/transaction`,
  HISTORY_TRANSACTION: `${API_BASE}/stock/history-transaction`,

  // K线SSE采集流
  KLINE_SSE: (taskId: string) => `${API_BASE}/stock/get-kline/sse/${taskId}`,

  // ─── 量能指标（后端新增） ──────────────────────────────
  VOLUME_VWMA: `${API_BASE}/stock/volume/vwma`,
  VOLUME_VR: `${API_BASE}/stock/volume/vr`,
  VOLUME_BIAS: `${API_BASE}/stock/volume/volume-bias`,
} as const;

// ─── 新逐笔交易接口（独立路径，无 /api 前缀） ────────────
export const MINUTE_TICK_API = '/get-minute-tick';

// ─── 新闻 API 端点 ────────────────────────────────────────────
export const NEWS_API = {
  FETCH_ALL: `${API_BASE}/news/fetch`,
  FETCH_SECTION: (section: string) => `${API_BASE}/news/fetch/${section}`,
  COLLECT_ALL: `${API_BASE}/news/collect_all`,
  STATUS: `${API_BASE}/news/status`,
} as const;

// ─── WebSocket ─────────────────────────────────────────────────
export const WS_DEFAULT_URL = 'ws://localhost:8001/ws';
export const WS_RECONNECT_INTERVAL = 5000;

// ─── 业务常量 ──────────────────────────────────────────────────
export const DEFAULT_FUND_FLOW_LIMIT = 200;
export const DEFAULT_CONCEPT_LIMIT = 100;
export const DEFAULT_NEWS_LIMIT = 500;

/** 龙虎榜数据出榜时间分界 */
export const LHB_DATA_HOUR = 17;

/** 默认日期范围天数 */
export const DEFAULT_DATE_RANGE_DAYS = 7;