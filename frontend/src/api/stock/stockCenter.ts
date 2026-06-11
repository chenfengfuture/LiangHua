/**
 * 个股中心模块 API
 *
 * 对接后端接口（实测可用）：
 *   - GET /api/stock/get-stock-zh-a-hist           日/周/月 K 线（不复权）
 *   - GET /api/stock/get-stock-zh-a-hist-min-em    分钟级 K 线（mootdx）
 *   - GET /api/stock/get-stock-financial-report-sina  财务报表（资产/利润/现金流）
 *   - GET /api/stock/get-stock_hot_keyword_em      东方财富热门关键词（symbol=SH600000）
 *   - GET /api/stock/get-stock-comment-focus-em    千股千评-用户关注指数
 *   - GET /api/stock/get-stock-comment-desire-em   千股千评-市场参与意愿
 *   - GET /api/stock/get-stock-gdhs-detail-em      股东户数详情
 *
 * 已弃用（后端返回 success=false / 空 / 500）：
 *   * get-stock-info / get-stock-info-xq / get-stock-individual-spot-xq
 *   * get-stock-balance-sheet / get-stock-profit-sheet（超时，改用 sina）
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  StockKlineDaily,
  StockKlineMinute,
  StockBalanceSheet,
  StockHotKeyword,
  StockCommentFocus,
  StockCommentDesire,
  StockHolderDetail,
  KlinePeriod,
  SurgeStockItem,
} from '../../types/stock';

export const stockCenterApi = {
  /**
   * 日/周/月 K 线
   * GET /api/stock/get-kline
   *
   * 新接口返回格式（嵌套）：
   *   { success, message, data: { success, symbol, name, freq, source, records: [...] } }
   * records 字段与原 StockKlineDaily 不同，在此层统一映射
   */
  async getDailyKline(
    symbol: string,
    period: KlinePeriod = 'daily',
    startDate: string = '',
    endDate: string = '',
    adjust: string = '',
  ): Promise<StockKlineDaily[]> {
    const raw = await http.get<any>(STOCK_API.KLINE_DAILY, {
      params: { symbol, period, start_date: startDate, end_date: endDate, adjust },
    });
    const inner = unwrap<any>(raw, { records: [] });
    const records: any[] = inner.records || [];
    return records.map((r: any) => ({
      trade_date: r.datetime ? r.datetime.slice(0, 10).replace(/-/g, '') : '',
      symbol: r.symbol || '',
      open_price: r.open,
      close_price: r.close,
      high_price: r.high,
      low_price: r.low,
      volume: r.volume ?? r.vol ?? 0,
      amount: r.amount ?? 0,
      amplitude: null as any,
      change_percent: null as any,
      change_amount: null as any,
      turnover_rate: null as any,
    })) as StockKlineDaily[];
  },

  /**
   * 分钟级 K 线（mootdx）
   * GET /api/stock/get-stock-zh-a-hist-min-em
   *   period: day/week/month/1/5/15/30/60
   */
  async getMinuteKline(
    symbol: string,
    period: string = '15',
    startDate?: string,
    endDate?: string,
  ): Promise<StockKlineMinute[]> {
    const params: Record<string, string> = { symbol, period };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<StockKlineMinute[]>>(
      STOCK_API.KLINE_MINUTE,
      { params },
    );
    return unwrap<StockKlineMinute[]>(resp, []);
  },

  /**
   * 财务报表（新浪）— 含资产负债表/利润表/现金流量表
   * GET /api/stock/get-stock-financial-report-sina
   *   stock: 带市场前缀（sh600519/sz000001）
   *   symbol: 资产负债表 / 利润表 / 现金流量表
   */
  async getFinancialReport(
    stock: string,
    sheetType: '资产负债表' | '利润表' | '现金流量表' = '资产负债表',
  ): Promise<StockBalanceSheet[]> {
    const resp = await http.get<ApiResponse<StockBalanceSheet[]>>(
      STOCK_API.FINANCIAL_REPORT,
      { params: { stock, symbol: sheetType } },
    );
    return unwrap<StockBalanceSheet[]>(resp, []);
  },

  /**
   * 东方财富个股热门关键词
   * GET /api/stock/get-stock_hot_keyword_em
   *   symbol: 必须带市场前缀（SH600000 / SZ000001）
   */
  async getHotKeywords(symbol: string): Promise<StockHotKeyword[]> {
    const resp = await http.get<ApiResponse<StockHotKeyword[]>>(
      STOCK_API.HOT_KEYWORD,
      { params: { symbol } },
    );
    return unwrap<StockHotKeyword[]>(resp, []);
  },

  /**
   * 千股千评-用户关注指数
   * GET /api/stock/get-stock-comment-focus-em
   */
  async getCommentFocus(symbol: string): Promise<StockCommentFocus[]> {
    const resp = await http.get<ApiResponse<StockCommentFocus[]>>(
      STOCK_API.COMMENT_FOCUS,
      { params: { symbol } },
    );
    return unwrap<StockCommentFocus[]>(resp, []);
  },

  /**
   * 千股千评-市场参与意愿
   * GET /api/stock/get-stock-comment-desire-em
   */
  async getCommentDesire(symbol: string): Promise<StockCommentDesire[]> {
    const resp = await http.get<ApiResponse<StockCommentDesire[]>>(
      STOCK_API.COMMENT_DESIRE,
      { params: { symbol } },
    );
    return unwrap<StockCommentDesire[]>(resp, []);
  },

  /**
   * 股东户数详情
   * GET /api/stock/get-stock-gdhs-detail-em
   */
  async getHolderDetail(symbol: string): Promise<StockHolderDetail[]> {
    const resp = await http.get<ApiResponse<StockHolderDetail[]>>(
      STOCK_API.HOLDER_DETAIL,
      { params: { symbol } },
    );
    return unwrap<StockHolderDetail[]>(resp, []);
  },

  /**
   * 昨日涨幅榜单
   * GET /api/stock/get-yesterday-surge-stocks
   *   min_pct: 最小涨幅（默认 3）
   *   max_pct: 最大涨幅（默认 10）
   *   limit: 返回条数（默认 50）
   *   sort: 排序 desc/asc（默认 desc）
   */
  async getSurgeStocks(params: {
    min_pct?: number;
    max_pct?: number;
    limit?: number;
    sort?: 'desc' | 'asc';
  } = {}): Promise<SurgeStockItem[]> {
    const resp = await http.get<{ success: boolean; data: SurgeStockItem[] }>(
      STOCK_API.SURGE_STOCKS,
      { params: { min_pct: 3, max_pct: 10, limit: 50, sort: 'desc', ...params } },
    );
    // 此接口返回格式为 { success, data: [...] }，直接取 data
    if (resp?.success === false) return [];
    return resp?.data || [];
  },
};