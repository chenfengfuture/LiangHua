import axios from 'axios'

const BASE = 'http://localhost:8001'

const api = axios.create({ baseURL: BASE, timeout: 15000 })

export const searchStocks = (q, limit = 20) =>
  api.get('/api/stocks/search', { params: { q, limit } }).then(r => r.data)

export const listStocks = (page = 1, pageSize = 50, market) =>
  api.get('/api/stocks/list', { params: { page, page_size: pageSize, market } }).then(r => r.data)

export const getKlines = (symbol, startDate, endDate, limit = 500) =>
  api.get(`/api/klines/${symbol}`, {
    params: { start_date: startDate, end_date: endDate, limit }
  }).then(r => r.data)

export const getMA = (symbol, startDate, endDate, periods = '5,10,20,60,120,250', limit = 500) =>
  api.get(`/api/klines/${symbol}/ma`, {
    params: { start_date: startDate, end_date: endDate, periods, limit }
  }).then(r => r.data)

export const getStockInfo = (symbol) =>
  api.get(`/api/stock/${symbol}/info`).then(r => r.data)

export const getMarketOverview = () =>
  api.get('/api/market/overview').then(r => r.data)

export const getHotStocks = (dateStr, limit = 20) =>
  api.get('/api/stocks/hot', { params: { date_str: dateStr, limit } }).then(r => r.data)

export const getKlineDetail = (symbol, dateStr) =>
  api.get(`/api/klines/${symbol}/detail`, { params: { date_str: dateStr } }).then(r => r.data)

export const getIntradayMinutes = (symbol, dateStr) =>
  api.get(`/api/intraday/${symbol}/minutes`, { params: { date_str: dateStr } }).then(r => r.data)

export const getIntradayTransactions = (symbol, dateStr, limit = 0) =>
  api.get(`/api/intraday/${symbol}/transactions`, { params: { date_str: dateStr, limit } }).then(r => r.data)

// ── 每日收盘采集接口 ────────────────────────────────────────────────────────
export const triggerCollect = (dateStr = null, symbols = null) =>
  api.post('/api/collect/trigger', null, {
    params: { ...(dateStr ? { date_str: dateStr } : {}), ...(symbols ? { symbols } : {}) },
    timeout: 10000,
  }).then(r => r.data)

export const getCollectStatus = () =>
  api.get('/api/collect/status', { timeout: 5000 }).then(r => r.data)

// ── 压力位 / 支撑位接口 ──────────────────────────────────────────────────────
export const getPriceLevels = (symbol, nLocal = 60, nData = 120) =>
  api.get(`/api/klines/${symbol}/levels`, {
    params: { n_local: nLocal, n_data: nData },
    timeout: 10000,
  }).then(r => r.data)

// ═══════════════════════════════════════════════════════════════════════════════
// 新闻分表查询接口（重构版）- 直接查询数据库分表
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * 获取公司动态新闻（news_company_YYYYMM 表）
 * @param {string} yearMonth - 年月，格式：YYYYMM，如：202604
 * @param {Object} options - 查询选项
 * @param {string} options.symbol - 股票代码过滤
 * @param {string} options.eventType - 事件类型过滤
 * @param {number} options.limit - 返回条数限制
 */
export const getCompanyNewsDB = (yearMonth, options = {}) =>
  api.get('/api/news/db/company', {
    params: { 
      year_month: yearMonth,
      symbol: options.symbol || null,
      event_type: options.eventType || null,
      limit: options.limit || 100,
    },
    timeout: 15000,
  }).then(r => r.data)

/**
 * 获取财联社新闻（news_cls_YYYYMM 表）
 * @param {string} yearMonth - 年月，格式：YYYYMM
 * @param {Object} options - 查询选项
 * @param {string} options.tag - 标签过滤
 * @param {number} options.limit - 返回条数限制
 */
export const getCLSNewsDB = (yearMonth, options = {}) =>
  api.get('/api/news/db/cls', {
    params: { 
      year_month: yearMonth,
      tag: options.tag || null,
      limit: options.limit || 100,
    },
    timeout: 15000,
  }).then(r => r.data)

/**
 * 获取全球新闻（news_global_YYYYMM 表）
 * @param {string} yearMonth - 年月，格式：YYYYMM
 * @param {Object} options - 查询选项
 * @param {string} options.source - 来源过滤
 * @param {number} options.limit - 返回条数限制
 */
export const getGlobalNewsDB = (yearMonth, options = {}) =>
  api.get('/api/news/db/global', {
    params: { 
      year_month: yearMonth,
      source: options.source || null,
      limit: options.limit || 100,
    },
    timeout: 15000,
  }).then(r => r.data)

/**
 * 获取研报新闻（news_report_YYYYMM 表）
 * @param {string} yearMonth - 年月，格式：YYYYMM
 * @param {Object} options - 查询选项
 * @param {number} options.limit - 返回条数限制
 */
export const getReportNewsDB = (yearMonth, options = {}) =>
  api.get('/api/news/db/report', {
    params: { 
      year_month: yearMonth,
      limit: options.limit || 100,
    },
    timeout: 15000,
  }).then(r => r.data)

/**
 * 获取 CCTV 新闻（news_cctv_YYYYMM 表）
 * CCTV 新闻不进入 LLM 分析队列
 * @param {string} yearMonth - 年月，格式：YYYYMM
 * @param {Object} options - 查询选项
 * @param {number} options.limit - 返回条数限制
 */
export const getCCTVNewsDB = (yearMonth, options = {}) =>
  api.get('/api/news/db/cctv', {
    params: { 
      year_month: yearMonth,
      limit: options.limit || 50,
    },
    timeout: 15000,
  }).then(r => r.data)

/**
 * 并行获取所有新闻分表数据
 * 重构版核心接口：一次性获取所有分表数据，前端合并去重
 * 
 * @param {string} yearMonth - 年月，格式：YYYYMM
 * @param {Object} options - 查询选项
 * @param {string} options.symbol - 股票代码过滤（仅对公司动态有效）
 * @param {string} options.eventType - 事件类型过滤（仅对公司动态有效）
 * @param {string} options.tag - 标签过滤（仅对财联社有效）
 * @param {string} options.source - 来源过滤（仅对全球新闻有效）
 * @param {number} options.limit - 每表返回条数限制
 * @returns {Promise<Object>} - 返回各分表数据 { company: [], cls: [], global: [], report: [] }
 */
export const getAllNewsSectionsDB = async (yearMonth, options = {}) => {
  const sections = ['company', 'cls', 'global', 'report']
  
  const requests = sections.map(section => {
    const sectionOptions = { limit: options.limit || 100 }
    
    // 根据板块添加特定过滤条件
    if (section === 'company') {
      sectionOptions.symbol = options.symbol
      sectionOptions.eventType = options.eventType
    } else if (section === 'cls') {
      sectionOptions.tag = options.tag
    } else if (section === 'global') {
      sectionOptions.source = options.source
    }
    
    switch (section) {
      case 'company':
        return getCompanyNewsDB(yearMonth, sectionOptions)
      case 'cls':
        return getCLSNewsDB(yearMonth, sectionOptions)
      case 'global':
        return getGlobalNewsDB(yearMonth, sectionOptions)
      case 'report':
        return getReportNewsDB(yearMonth, sectionOptions)
      default:
        return Promise.resolve({ data: [], count: 0 })
    }
  })

  const responses = await Promise.allSettled(requests)
  
  const result = {}
  sections.forEach((section, index) => {
    const response = responses[index]
    if (response.status === 'fulfilled') {
      result[section] = {
        data: response.value.data || [],
        count: response.value.count || response.value.data?.length || 0,
        error: null,
      }
    } else {
      result[section] = {
        data: [],
        count: 0,
        error: response.reason?.message || '请求失败',
      }
    }
  })
  
  return result
}

// 日期范围查询新闻（保留兼容）
export const getNewsByRange = (newsType, startDate, endDate, options = {}) =>
  api.get('/api/news/range', {
    params: {
      news_type: newsType,
      start_date: startDate,
      end_date: endDate,
      ...options
    },
    timeout: 15000,
  }).then(r => r.data)



// 统一获取所有4个板块的新闻数据 - 使用后端实际存在的 /api/news/fetch 接口
export const getAllNewsSections = (dateStr, options = {}) =>
  api.get('/api/news/fetch', {
    params: {
      date: dateStr,
      limit: options.limit || 500,
      // 注意：后端 /api/news/fetch 接口不支持 symbol/event_type/tag/source/offset 参数
      // 这些过滤需要在前端处理
    },
    timeout: 20000, // 稍长超时，因为获取4个板块数据且数据量更大
  }).then(r => r.data)


