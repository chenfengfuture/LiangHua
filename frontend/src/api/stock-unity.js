import axios from 'axios'

const BASE = 'http://localhost:8001'
const api = axios.create({ baseURL: BASE, timeout: 15000 })

// ============================================================================
// 统一响应格式处理
// ============================================================================

/**
 * 统一响应格式处理函数
 * @param {Object} response - axios响应对象
 * @returns {Object} - 标准化响应格式
 */
const normalizeResponse = (response) => {
  const data = response.data
  // 如果后端已经返回统一格式，直接返回
  if (data && typeof data === 'object' && 'success' in data) {
    return data
  }
  // 否则包装成统一格式
  return {
    success: true,
    data: data,
    error: null,
    timestamp: new Date().toISOString()
  }
}

/**
 * 统一错误处理函数
 * @param {Error} error - axios错误对象
 * @returns {Object} - 标准化错误响应格式
 */
const normalizeError = (error) => {
  console.error('API请求失败:', error)
  return {
    success: false,
    data: null,
    error: error.response?.data?.error || error.message || '网络请求失败',
    timestamp: new Date().toISOString()
  }
}

/**
 * 创建统一封装的API函数
 * @param {Function} apiCall - axios调用函数
 * @returns {Function} - 封装后的API函数
 */
const createApiFunction = (apiCall) => {
  return async (...args) => {
    try {
      const response = await apiCall(...args)
      return normalizeResponse(response)
    } catch (error) {
      return normalizeError(error)
    }
  }
}

// ============================================================================
// 股票基本信息模块 (basic/)
// ============================================================================

/**
 * 查询个股基础信息（东方财富接口）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockInfo = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/basic/info/${symbol}`))

/**
 * 查询个股基础信息并返回JSON字符串
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回JSON字符串格式
 */
export const getStockInfoJson = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/basic/info-json/${symbol}`))

/**
 * 查询雪球财经-个股-公司概况
 * @param {string} symbol - 股票代码，需带市场前缀，如 "SH601127"
 * @returns {Promise<Object>} - 返回统一格式
 */
export const getStockIndividualBasicInfoXq = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/basic/individual-basic-info-xq/${symbol}`))

/**
 * 查询全市场A股股票代码列表
 * @returns {Promise<Object>} - 返回股票代码列表
 */
export const getAllStockCodes = createApiFunction(() =>
  api.get('/api/stock/unity/basic/all-stock-codes'))

/**
 * 查询全市场A股股票代码列表并返回JSON
 * @returns {Promise<Object>} - 返回JSON格式的股票代码列表
 */
export const getAllStockCodesJson = createApiFunction(() =>
  api.get('/api/stock/unity/basic/all-stock-codes-json'))

/**
 * 上海证券交易所股票代码和简称数据
 * @returns {Promise<Object>} - 返回上交所股票列表
 */
export const stockInfoShNameCode = createApiFunction(() =>
  api.get('/api/stock/unity/basic/sh-name-code'))

/**
 * 深圳证券交易所股票代码和简称数据
 * @returns {Promise<Object>} - 返回深交所股票列表
 */
export const stockInfoSzNameCode = createApiFunction(() =>
  api.get('/api/stock/unity/basic/sz-name-code'))

/**
 * 北京证券交易所股票代码和简称数据
 * @returns {Promise<Object>} - 返回北交所股票列表
 */
export const stockInfoBjNameCode = createApiFunction(() =>
  api.get('/api/stock/unity/basic/bj-name-code'))

/**
 * 上海证券交易所暂停/终止上市股票
 * @returns {Promise<Object>} - 返回上交所退市股票列表
 */
export const stockInfoShDelist = createApiFunction(() =>
  api.get('/api/stock/unity/basic/sh-delist'))

/**
 * 深圳证券交易所终止/暂停上市股票
 * @returns {Promise<Object>} - 返回深交所退市股票列表
 */
export const stockInfoSzDelist = createApiFunction(() =>
  api.get('/api/stock/unity/basic/sz-delist'))

// ============================================================================
// 股权质押模块 (pledge/)
// ============================================================================

/**
 * 查询股权质押市场概况（全量历史）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "gpzy_profile" }
 */
export const getStockGpzyProfileEm = createApiFunction(() =>
  api.get('/api/stock/unity/pledge/gpzy-profile'))

/**
 * 查询指定交易日上市公司质押比例
 * @param {string} date - 交易日，格式 "YYYYMMDD"，如 "20240417"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "gpzy_pledge_ratio" }
 */
export const getStockGpzyPledgeRatioEm = createApiFunction((date) =>
  api.get('/api/stock/unity/pledge/gpzy-pledge-ratio', { params: { date } }))

/**
 * 查询个股重要股东股权质押明细（全量历史）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockGpzyIndividualPledgeRatioDetailEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/pledge/individual-pledge-ratio/${symbol}`))

/**
 * 查询各行业质押比例汇总数据（全量）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "gpzy_industry" }
 */
export const getStockGpzyIndustryDataEm = createApiFunction(() =>
  api.get('/api/stock/unity/pledge/industry-data'))

// ============================================================================
// 财务报表模块 (financial/)
// ============================================================================

/**
 * 查询新浪财经财务报表
 * @param {string} stock - 股票代码，如 "sh600000"
 * @param {string} symbol - 报表类型：choice of {"资产负债表", "利润表", "现金流量表"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockFinancialReportSina = createApiFunction((stock, symbol) =>
  api.get('/api/stock/unity/financial/report-sina', { params: { stock, symbol } }))

/**
 * 查询东方财富资产负债表（按年度）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockBalanceSheetByYearlyEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/financial/balance-sheet-yearly/${symbol}`))

/**
 * 查询东方财富利润表（按报告期）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockProfitSheetByReportEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/financial/profit-sheet-report/${symbol}`))

/**
 * 查询东方财富利润表（按年度）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockProfitSheetByYearlyEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/financial/profit-sheet-yearly/${symbol}`))

/**
 * 查询东方财富现金流量表（按报告期）
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockCashFlowSheetByReportEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/financial/cash-flow-sheet-report/${symbol}`))

/**
 * 查询同花顺盈利预测数据
 * @param {string} symbol - 股票代码，如 "000001"
 * @param {string} indicator - 指标类型：choice of {"预测年报每股收益", "预测年报净利润", "业绩预测详表-机构", "业绩预测详表-详细指标预测"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockProfitForecastThs = createApiFunction((symbol, indicator) =>
  api.get('/api/stock/unity/financial/profit-forecast-ths', { params: { symbol, indicator } }))

// ============================================================================
// 股东数据模块 (holder/)
// ============================================================================

/**
 * 查询月度股票账户统计数据（201504 起全量）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "account_statistics" }
 */
export const getStockAccountStatisticsEm = createApiFunction(() =>
  api.get('/api/stock/unity/holder/account-statistics'))

/**
 * 查询千股千评数据（全部股票当日评分）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "stock_comment" }
 */
export const getStockCommentEm = createApiFunction(() =>
  api.get('/api/stock/unity/holder/stock-comment'))

/**
 * 查询千股千评-用户关注指数
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockCommentDetailScrdFocusEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/holder/comment-focus/${symbol}`))

/**
 * 查询千股千评-市场参与意愿
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockCommentDetailScrdDesireEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/holder/comment-desire/${symbol}`))

/**
 * 查询全市场股东户数数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "gdhs" }
 */
export const getStockZhAGdhs = createApiFunction((date) =>
  api.get('/api/stock/unity/holder/zh-a-gdhs', { params: { date } }))

/**
 * 查询个股股东户数详情
 * @param {string} symbol - 股票代码，如 "000001"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockZhAGdhsDetailEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/holder/zh-a-gdhs-detail/${symbol}`))

// ============================================================================
// 龙虎榜模块 (lhb/)
// ============================================================================

/**
 * 查询龙虎榜机构买卖每日统计
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"，如 "20240417"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"，如 "20240430"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "jgmmtj" }
 */
export const getStockLhbJgmmtjEm = createApiFunction((startDate, endDate) =>
  api.get('/api/stock/unity/lhb/jgmmtj', { params: { start_date: startDate, end_date: endDate } }))

/**
 * 查询龙虎榜详情数据
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"，如 "20240417"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"，如 "20240430"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "lhb_detail" }
 */
export const getStockLhbDetailEm = createApiFunction((startDate, endDate) =>
  api.get('/api/stock/unity/lhb/detail', { params: { start_date: startDate, end_date: endDate } }))

/**
 * 查询个股上榜统计数据
 * @param {string} symbol - 时间范围：choice of {"近一月", "近三月", "近六月", "近一年"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "lhb_stock_statistic" }
 */
export const getStockLhbStockStatisticEm = createApiFunction((symbol) =>
  api.get('/api/stock/unity/lhb/stock-statistic', { params: { symbol } }))

/**
 * 查询每日活跃营业部数据
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"，如 "20240417"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"，如 "20240430"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "lhb_hyyyb" }
 */
export const getStockLhbHyyybEm = createApiFunction((startDate, endDate) =>
  api.get('/api/stock/unity/lhb/hyyyb', { params: { start_date: startDate, end_date: endDate } }))

/**
 * 查询营业部历史交易明细
 * @param {string} symbol - 营业部代码
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockLhbYybDetailEm = createApiFunction((symbol) =>
  api.get(`/api/stock/unity/lhb/yyb-detail/${symbol}`))

// ============================================================================
// 资金流向模块 (fund_flow/)
// ============================================================================

/**
 * 查询个股资金流向
 * @param {string} symbol - 时间范围：choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockFundFlowIndividual = createApiFunction((symbol) =>
  api.get('/api/stock/unity/fund-flow/individual', { params: { symbol } }))

/**
 * 查询概念板块资金流向
 * @param {string} symbol - 时间范围：choice of {"即时", "3日排行", "5日排行", "10日排行", "20日排行"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockFundFlowConcept = createApiFunction((symbol) =>
  api.get('/api/stock/unity/fund-flow/concept', { params: { symbol } }))

/**
 * 查询个股资金流向（东方财富，近100交易日）
 * @param {string} stock - 股票代码，如 "000425"
 * @param {string} market - 市场：choice of {"sh": "上海", "sz": "深圳", "bj": "北京"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockIndividualFundFlow = createApiFunction((stock, market) =>
  api.get('/api/stock/unity/fund-flow/individual-flow', { params: { stock, market } }))

/**
 * 查询个股资金流向排名
 * @param {string} indicator - 时间范围：choice of {"今日", "3日", "5日", "10日"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockIndividualFundFlowRank = createApiFunction((indicator) =>
  api.get('/api/stock/unity/fund-flow/individual-flow-rank', { params: { indicator } }))

/**
 * 查询市场资金流向
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "market_fund_flow" }
 */
export const getStockMarketFundFlow = createApiFunction(() =>
  api.get('/api/stock/unity/fund-flow/market-fund-flow'))

/**
 * 查询板块资金流向排名
 * @param {string} indicator - 时间范围：choice of {"今日", "5日", "10日"}
 * @param {string} sectorType - 板块类型：choice of {"行业资金流", "概念资金流", "地域资金流"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockSectorFundFlowRank = createApiFunction((indicator, sectorType) =>
  api.get('/api/stock/unity/fund-flow/sector-fund-flow-rank', { params: { indicator, sector_type: sectorType } }))

/**
 * 查询行业个股资金流
 * @param {string} symbol - 行业板块名称，如 "电源设备"
 * @param {string} indicator - 时间范围：choice of {"今日", "5日", "10日"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockSectorFundFlowSummary = createApiFunction((symbol, indicator) =>
  api.get('/api/stock/unity/fund-flow/sector-fund-flow-summary', { params: { symbol, indicator } }))

/**
 * 查询主力净流入排名
 * @param {string} symbol - 市场范围：choice of {"全部股票", "沪深A股", "沪市A股", "科创板", "深市A股", "创业板", "沪市B股", "深市B股"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockMainFundFlow = createApiFunction((symbol) =>
  api.get('/api/stock/unity/fund-flow/main-fund-flow', { params: { symbol } }))

// ============================================================================
// 融资融券模块 (margin/)
// ============================================================================

/**
 * 查询两融账户信息（东方财富）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "margin_account" }
 */
export const getStockMarginAccountInfo = createApiFunction(() =>
  api.get('/api/stock/unity/margin/account-info'))

/**
 * 查询上交所融资融券汇总数据
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "margin_sse" }
 */
export const getStockMarginSse = createApiFunction((startDate, endDate) =>
  api.get('/api/stock/unity/margin/sse', { params: { start_date: startDate, end_date: endDate } }))

/**
 * 查询深交所融资融券明细数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "margin_detail_szse" }
 */
export const getStockMarginDetailSzse = createApiFunction((date) =>
  api.get('/api/stock/unity/margin/detail-szse', { params: { date } }))

/**
 * 查询上交所融资融券明细数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "margin_detail_sse" }
 */
export const getStockMarginDetailSse = createApiFunction((date) =>
  api.get('/api/stock/unity/margin/detail-sse', { params: { date } }))

// ============================================================================
// 板块概念模块 (board/)
// ============================================================================

/**
 * 查询同花顺概念板块指数日频率数据
 * @param {string} symbol - 概念板块名称，如 "阿里巴巴概念"
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockBoardConceptIndexThs = createApiFunction((symbol, startDate, endDate) =>
  api.get('/api/stock/unity/board/concept-index-ths', { params: { symbol, start_date: startDate, end_date: endDate } }))

/**
 * 查询同花顺行业一览表
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "industry_summary" }
 */
export const getStockBoardIndustrySummaryThs = createApiFunction(() =>
  api.get('/api/stock/unity/board/industry-summary-ths'))

/**
 * 查询同花顺概念板块简介
 * @param {string} symbol - 概念板块名称，如 "阿里巴巴概念"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockBoardConceptInfoThs = createApiFunction((symbol) =>
  api.get('/api/stock/unity/board/concept-info-ths', { params: { symbol } }))

/**
 * 查询同花顺行业板块指数日频率数据
 * @param {string} symbol - 行业板块名称，如 "元件"
 * @param {string} startDate - 开始日期，格式 "YYYYMMDD"
 * @param {string} endDate - 结束日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockBoardIndustryIndexThs = createApiFunction((symbol, startDate, endDate) =>
  api.get('/api/stock/unity/board/industry-index-ths', { params: { symbol, start_date: startDate, end_date: endDate } }))

/**
 * 查询雪球关注排行榜
 * @param {string} symbol - 排行榜类型：choice of {"本周新增", "最热门"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockHotFollowXq = createApiFunction((symbol) =>
  api.get('/api/stock/unity/board/hot-follow-xq', { params: { symbol } }))

/**
 * 查询东方财富股票热度历史趋势及粉丝特征
 * @param {string} symbol - 股票代码，如 "SZ000665"（需带市场前缀）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockHotRankDetailEm = createApiFunction((symbol) =>
  api.get('/api/stock/unity/board/hot-rank-detail', { params: { symbol } }))

/**
 * 查询东方财富个股人气榜热门关键词
 * @param {string} symbol - 股票代码，如 "SZ000665"（需带市场前缀）
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockHotKeywordEm = createApiFunction((symbol) =>
  api.get('/api/stock/unity/board/hot-keyword', { params: { symbol } }))

/**
 * 查询东方财富盘口异动数据
 * @param {string} symbol - 异动类型：choice of {"火箭发射", "快速反弹", "大笔买入", "封涨停板", "打开跌停板", ...}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockChangesEm = createApiFunction((symbol) =>
  api.get('/api/stock/unity/board/changes', { params: { symbol } }))

/**
 * 查询东方财富当日板块异动详情
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "board_change" }
 */
export const getStockBoardChangeEm = createApiFunction(() =>
  api.get('/api/stock/unity/board/board-change'))

// ============================================================================
// 涨跌停模块 (zt/)
// ============================================================================

/**
 * 查询东方财富涨停股池数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "zt_pool" }
 */
export const getStockZtPoolEm = createApiFunction((date) =>
  api.get('/api/stock/unity/zt/pool', { params: { date } }))

/**
 * 查询东方财富昨日涨停股池数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "zt_pool_previous" }
 */
export const getStockZtPoolPreviousEm = createApiFunction((date) =>
  api.get('/api/stock/unity/zt/pool-previous', { params: { date } }))

/**
 * 查询东方财富强势股池数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "zt_pool_strong" }
 */
export const getStockZtPoolStrongEm = createApiFunction((date) =>
  api.get('/api/stock/unity/zt/pool-strong', { params: { date } }))

/**
 * 查询东方财富炸板股池数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "zt_pool_zbgc" }
 */
export const getStockZtPoolZbgcEm = createApiFunction((date) =>
  api.get('/api/stock/unity/zt/pool-zbgc', { params: { date } }))

/**
 * 查询东方财富跌停股池数据
 * @param {string} date - 日期，格式 "YYYYMMDD"
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "zt_pool_dtgc" }
 */
export const getStockZtPoolDtgcEm = createApiFunction((date) =>
  api.get('/api/stock/unity/zt/pool-dtgc', { params: { date } }))

// ============================================================================
// 技术选股排名模块 (rank/)
// ============================================================================

/**
 * 查询同花顺技术指标-创新高数据
 * @param {string} symbol - 时间范围：choice of {"创月新高", "半年新高", "一年新高", "历史新高"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockRankCxgThs = createApiFunction((symbol) =>
  api.get('/api/stock/unity/rank/cxg-ths', { params: { symbol } }))

/**
 * 查询同花顺技术选股-连续上涨数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "lxsz" }
 */
export const getStockRankLxszThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/lxsz-ths'))

/**
 * 查询同花顺技术选股-持续放量数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "cxfl" }
 */
export const getStockRankCxflThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/cxfl-ths'))

/**
 * 查询同花顺技术选股-持续缩量数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "cxsl" }
 */
export const getStockRankCxslThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/cxsl-ths'))

/**
 * 查询同花顺技术选股-向上突破数据
 * @param {string} symbol - 均线类型：choice of {"5日均线", "10日均线", "20日均线", "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol }
 */
export const getStockRankXstpThs = createApiFunction((symbol) =>
  api.get('/api/stock/unity/rank/xstp-ths', { params: { symbol } }))

/**
 * 查询同花顺技术选股-量价齐升数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "ljqs" }
 */
export const getStockRankLjqsThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/ljqs-ths'))

/**
 * 查询同花顺技术选股-量价齐跌数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "ljqd" }
 */
export const getStockRankLjqdThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/ljqd-ths'))

/**
 * 查询同花顺技术选股-险资举牌数据
 * @returns {Promise<Object>} - 返回统一格式：{ success, data, error, symbol: "xzjp" }
 */
export const getStockRankXzjpThs = createApiFunction(() =>
  api.get('/api/stock/unity/rank/xzjp-ths'))

// ============================================================================
// 导出所有API函数
// ============================================================================

// 导出所有函数
export default {
  // basic
  getStockInfo,
  getStockInfoJson,
  getStockIndividualBasicInfoXq,
  getAllStockCodes,
  getAllStockCodesJson,
  stockInfoShNameCode,
  stockInfoSzNameCode,
  stockInfoBjNameCode,
  stockInfoShDelist,
  stockInfoSzDelist,
  
  // pledge
  getStockGpzyProfileEm,
  getStockGpzyPledgeRatioEm,
  getStockGpzyIndividualPledgeRatioDetailEm,
  getStockGpzyIndustryDataEm,
  
  // financial
  getStockFinancialReportSina,
  getStockBalanceSheetByYearlyEm,
  getStockProfitSheetByReportEm,
  getStockProfitSheetByYearlyEm,
  getStockCashFlowSheetByReportEm,
  getStockProfitForecastThs,
  
  // holder
  getStockAccountStatisticsEm,
  getStockCommentEm,
  getStockCommentDetailScrdFocusEm,
  getStockCommentDetailScrdDesireEm,
  getStockZhAGdhs,
  getStockZhAGdhsDetailEm,
  
  // lhb
  getStockLhbJgmmtjEm,
  getStockLhbDetailEm,
  getStockLhbStockStatisticEm,
  getStockLhbHyyybEm,
  getStockLhbYybDetailEm,
  
  // fund_flow
  getStockFundFlowIndividual,
  getStockFundFlowConcept,
  getStockIndividualFundFlow,
  getStockIndividualFundFlowRank,
  getStockMarketFundFlow,
  getStockSectorFundFlowRank,
  getStockSectorFundFlowSummary,
  getStockMainFundFlow,
  
  // margin
  getStockMarginAccountInfo,
  getStockMarginSse,
  getStockMarginDetailSzse,
  getStockMarginDetailSse,
  
  // board
  getStockBoardConceptIndexThs,
  getStockBoardIndustrySummaryThs,
  getStockBoardConceptInfoThs,
  getStockBoardIndustryIndexThs,
  getStockHotFollowXq,
  getStockHotRankDetailEm,
  getStockHotKeywordEm,
  getStockChangesEm,
  getStockBoardChangeEm,
  
  // zt
  getStockZtPoolEm,
  getStockZtPoolPreviousEm,
  getStockZtPoolStrongEm,
  getStockZtPoolZbgcEm,
  getStockZtPoolDtgcEm,
  
  // rank
  getStockRankCxgThs,
  getStockRankLxszThs,
  getStockRankCxflThs,
  getStockRankCxslThs,
  getStockRankXstpThs,
  getStockRankLjqsThs,
  getStockRankLjqdThs,
  getStockRankXzjpThs
}