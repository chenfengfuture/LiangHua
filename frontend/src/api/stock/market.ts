/**
 * 行情与K线模块 API
 *
 * 对接后端接口（GET）：
 *   - /api/stock/get-stock-market-fund-flow        大盘资金流向（含指数行情）
 *   - /api/stock/get-stock-rank-lxsz-ths           连续上涨
 *   - /api/stock/get-stock-rank-lxxd-ths           连续下跌
 *   - /api/stock/get-stock-rank-ljqs-ths           量价齐升
 *   - /api/stock/get-stock-rank-ljqd-ths           量价齐跌
 *   - /api/stock/get-stock-account-statistics-em   股票账户月度统计
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  MarketFundFlow,
  StockConsecutiveStats,
  StockVolumePriceStats,
  InvestorMarketStats,
  BoardIndexKline,
  RealtimeQuoteDict,
} from '../../types/stock';

export const marketApi = {
  /** 大盘资金流向（含上证/深证指数行情） */
  async getMarketFundFlow(): Promise<MarketFundFlow[]> {
    const resp = await http.get<ApiResponse<MarketFundFlow[]>>(
      STOCK_API.MARKET_FUND_FLOW,
    );
    return unwrap<MarketFundFlow[]>(resp, []);
  },

  /** 上证指数日K线（新浪财经，含 OHLC） */
  async getZhADaily(
    symbol: string = 'sh000001',
    start_date: string,
    end_date: string,
  ): Promise<BoardIndexKline[]> {
    const params: Record<string, string> = { symbol, start_date, end_date };
    const resp = await http.get<ApiResponse<BoardIndexKline[]>>(
      STOCK_API.ZH_A_DAILY,
      { params },
    );
    return unwrap<BoardIndexKline[]>(resp, []);
  },

  /** 连续上涨 */
  async getConsecutiveUp(): Promise<StockConsecutiveStats[]> {
    const resp = await http.get<ApiResponse<StockConsecutiveStats[]>>(
      STOCK_API.RANK_CONSECUTIVE_UP,
    );
    return unwrap<StockConsecutiveStats[]>(resp, []);
  },

  /** 连续下跌 */
  async getConsecutiveDown(): Promise<StockConsecutiveStats[]> {
    const resp = await http.get<ApiResponse<StockConsecutiveStats[]>>(
      STOCK_API.RANK_CONSECUTIVE_DOWN,
    );
    return unwrap<StockConsecutiveStats[]>(resp, []);
  },

  /** 量价齐升 */
  async getVolumePriceUp(): Promise<StockVolumePriceStats[]> {
    const resp = await http.get<ApiResponse<StockVolumePriceStats[]>>(
      STOCK_API.RANK_VOLUME_PRICE_UP,
    );
    return unwrap<StockVolumePriceStats[]>(resp, []);
  },

  /** 量价齐跌 */
  async getVolumePriceDown(): Promise<StockVolumePriceStats[]> {
    const resp = await http.get<ApiResponse<StockVolumePriceStats[]>>(
      STOCK_API.RANK_VOLUME_PRICE_DOWN,
    );
    return unwrap<StockVolumePriceStats[]>(resp, []);
  },

  /** 股票账户月度统计 */
  async getAccountStatistics(): Promise<InvestorMarketStats[]> {
    const resp = await http.get<ApiResponse<InvestorMarketStats[]>>(
      STOCK_API.ACCOUNT_STATISTICS,
    );
    return unwrap<InvestorMarketStats[]>(resp, []);
  },

  // ─── 全量采集与回填 ─────────────────────────────────────────

  /**
   * 触发全市场 K 线采集
   * POST /api/stock/get-kline/ws-trigger
   */
  async triggerKlineCollect(
    freq: string = 'day',
    startDate?: string,
    endDate?: string,
  ): Promise<any> {
    const params: Record<string, string> = { freq };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.post<ApiResponse<any>>(
      STOCK_API.TRIGGER_KLINE_COLLECT,
      null,
      { params },
    );
    return resp?.data || resp;
  },

  /**
   * 批量回填历史指标数据
   * POST /api/stock/indicators/backfill
   *   symbol: 可选，单只股票代码
   *   year: 可选，指定年份
   *   batch_size: 每批股票数，默认 50
   *   parallel: 并行线程数，默认 4
   */
  async backfillIndicators(
    symbol?: string,
    year?: number,
    batchSize: number = 50,
    parallel: number = 4,
  ): Promise<any> {
    const params: Record<string, any> = { batch_size: batchSize, parallel };
    if (symbol) params.symbol = symbol;
    if (year) params.year = year;
    const resp = await http.post<ApiResponse<any>>(
      STOCK_API.BACKFILL_INDICATORS,
      null,
      { params },
    );
    return resp?.data || resp;
  },

  /** 实时行情（mootdx + Redis，不入库，TTL=30min） */
  async getRealtimeQuotes(
    symbols: string[],
    force = false,
  ): Promise<RealtimeQuoteDict> {
    const resp = await http.get<{
      success: boolean;
      data: RealtimeQuoteDict;
      source: string;
      update_time: string;
    }>(STOCK_API.REALTIME_QUOTES, {
      params: { symbols: symbols.join(','), force },
    });
    return (resp as any)?.data || {};
  },
};