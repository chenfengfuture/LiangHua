/**
 * K线分析模块 API
 *
 * 对接后端接口：
 *   - GET /api/stock/indicators               技术指标（MA/MACD/KDJ/RSI 等13个）
 *   - GET /api/stock/indicators/meta          指标元信息
 *   - GET /api/stock/indicators/batch         批量指标查询
 *   - GET /api/stock/get-kline                三层缓存K线查询
 *   - GET /api/stock/get-stock-zh-a-hist-min-em  分钟级K线（mootdx）
 *   - GET /api/stock/realtime-quotes          实时行情
 *   - GET /api/stock/get-minute-tick          分时Tick
 *   - GET /api/stock/get-kline/ws-trigger     全市场K线采集触发
 */

import http from './http';
import { unwrap } from './utils';
import { STOCK_API, SLOW_API_TIMEOUT, MINUTE_TICK_API } from '../config';
import { makeKey, readTTLCache, TTL, writeTTLCache } from '../utils/dailyCache';
import type {
  ApiResponse,
  IndicatorData,
  IndicatorMeta,
  RealtimeQuoteDict,
  StockKlineDaily,
  StockKlineMinute,
  MinuteTickItem,
  TransactionItem,
  VolumeVwmaPoint,
  VolumeVrPoint,
  VolumeBiasPoint,
} from '../types/stock';

export const klineAnalysisApi = {
  /**
   * 获取技术指标（13个核心指标）
   * GET /api/stock/indicators
   */
  async getIndicators(
    symbol: string,
    startDate?: string,
    endDate?: string,
  ): Promise<IndicatorData[]> {
    const params: Record<string, string> = { symbol };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<IndicatorData[]>>(
      STOCK_API.INDICATORS,
      { params },
    );
    return unwrap<IndicatorData[]>(resp, []);
  },

  /**
   * 指标元信息（支持的指标清单、参数、字段名）
   * GET /api/stock/indicators/meta
   */
  async getIndicatorsMeta(): Promise<{ indicators: IndicatorMeta[] } | null> {
    const resp = await http.get<ApiResponse<{ indicators: IndicatorMeta[] }>>(
      STOCK_API.INDICATORS_META,
    );
    if (resp?.success === false) return null;
    return resp?.data || null;
  },

  /**
   * 批量查询多只股票技术指标
   * GET /api/stock/indicators/batch
   */
  async getBatchIndicators(
    symbols: string[],
    startDate?: string,
    endDate?: string,
  ): Promise<Record<string, IndicatorData[]>> {
    const params: Record<string, any> = { symbols: symbols.join(',') };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<Record<string, IndicatorData[]>>>(
      STOCK_API.INDICATORS_BATCH,
      { params },
    );
    if (resp?.success === false) return {};
    return resp?.data || {};
  },

  /**
   * 三层缓存K线查询
   * GET /api/stock/get-kline
   *   period: daily/weekly/monthly
   */
  async getKline(
    symbol: string,
    period: 'daily' | 'weekly' | 'monthly' = 'daily',
    startDate?: string,
    endDate?: string,
    force = false,
  ): Promise<StockKlineDaily[]> {
    const params: Record<string, string> = { period };
    if (symbol) params.symbol = symbol;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const cacheKey = makeKey('kline-analysis:kline', { symbol, period, startDate, endDate });
    if (!force) {
      const cached = readTTLCache<StockKlineDaily[]>(cacheKey, TTL.SEVEN_DAYS);
      if (cached) return cached;
    }

    const raw = await http.get<any>(STOCK_API.KLINE_DAILY, { params });
    const inner = unwrap<any>(raw, { records: [] });
    const records: any[] = inner.records || [];
    const data = records.map((r: any) => ({
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
    writeTTLCache(cacheKey, data);
    return data;
  },

  /**
   * 分钟级K线（mootdx）
   * GET /api/stock/get-stock-zh-a-hist-min-em
   *   period: 1/5/15/30/60/day/week/month
   */
  async getMinuteKline(
    symbol: string,
    period: string = '5',
    startDate?: string,
    endDate?: string,
    force = false,
  ): Promise<StockKlineMinute[]> {
    const params: Record<string, string> = { symbol, period };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const cacheKey = makeKey('kline-analysis:minute-kline', { symbol, period, startDate, endDate });
    if (!force) {
      const cached = readTTLCache<StockKlineMinute[]>(cacheKey, TTL.SEVEN_DAYS);
      if (cached) return cached;
    }

    const resp = await http.get<ApiResponse<StockKlineMinute[]>>(
      STOCK_API.KLINE_MINUTE,
      { params },
    );
    // success === false 时抛出异常，让调用方 catch 块捕获并显示错误
    if (resp?.success === false) {
      throw new Error((resp as any)?.error || resp?.message || '分钟K线数据请求失败');
    }
    const data = unwrap<StockKlineMinute[]>(resp, []);
    writeTTLCache(cacheKey, data);
    return data;
  },

  /**
   * 实时行情（mootdx + Redis，不入库，TTL=30min）
   * GET /api/stock/realtime-quotes
   *
   * 返回完整响应 {success, data, source, update_time}，由调用方自行解构。
   */
  async getRealtimeQuotes(
    symbols: string[],
    force = false,
  ): Promise<{
    success: boolean;
    data: RealtimeQuoteDict;
    source: string;
    update_time: string;
    elapsed_s?: number;
  }> {
    const resp = await http.get<{
      success: boolean;
      data: RealtimeQuoteDict;
      source: string;
      update_time: string;
      elapsed_s?: number;
    }>(STOCK_API.REALTIME_QUOTES, {
      params: { symbols: symbols.join(','), force },
    });
    return resp;
  },

  /**
   * 获取个股分时Tick数据
   * GET /api/stock/get-minute-tick
   */
  async getMinuteTick(
    symbol: string,
    date: string,
  ): Promise<MinuteTickItem[]> {
    const resp = await http.get<ApiResponse<MinuteTickItem[]>>(
      STOCK_API.MINUTE_TICK,
      { params: { symbol, date } },
    );
    return unwrap<MinuteTickItem[]>(resp, []);
  },

  /**
   * [新接口] 获取逐笔交易数据（替代原有 transaction/history-transaction）
   * GET /get-minute-tick?symbol=000001&date=20260604
   *
   * 接口规范：
   *   约定正常响应 code=0，data 为数组。
   *   单条记录字段（兼容二义命名）：
   *     time/minute    → 时间（HHmmss 或 HH:mm:ss）
   *     price/close    → 价格
   *     volume/vol     → 成交量
   *     amount/money   → 成交额
   *     direction/buyorsell → 交易方向（0=中性/1=主动买入/2=主动卖出）
   */
  async getMinuteTickTransactions(
    symbol: string,
    date: string,
  ): Promise<{
    success: boolean;
    data: TransactionItem[];
    errorMsg: string;
  }> {
    // 接口要求纯6位数字代码
    const pureCode = symbol.replace(/^(sh|sz|bj|SH|SZ|BJ)/i, '');

    try {
      const resp = await http.get<any>(MINUTE_TICK_API, {
        params: { symbol: pureCode, date },
        timeout: SLOW_API_TIMEOUT,
      });

      // === 第一层校验：响应非空 + 非JSON处理（http 拦截器已处理，走到这里说明至少不是网络错误） ===
      if (resp == null) {
        return { success: false, data: [], errorMsg: '接口返回数据为空' };
      }

      // === 第二层校验：code 状态 ===
      // 200 系接口可能直接返回数组，跳过 code 校验
      if (typeof resp === 'object' && resp !== null && 'code' in resp) {
        const r = resp as Record<string, any>;
        if (r.code !== 0) {
          const msg = r.msg || r.message || `业务异常(code=${r.code})`;
          return { success: false, data: [], errorMsg: msg };
        }
      }

      // === 第三层校验：data 字段必须是数组 ===
      const rawData = resp?.data !== undefined ? resp.data : resp;
      if (rawData == null) {
        return { success: false, data: [], errorMsg: '暂无逐笔交易数据' };
      }
      const rawArray = Array.isArray(rawData) ? rawData : (rawData.records || rawData.items || rawData.list || rawData.rows || []);
      if (!Array.isArray(rawArray) || rawArray.length === 0) {
        return { success: true, data: [], errorMsg: '' };
      }

      // === 第四层：逐条校验与字段适配 ===
      const normalized: TransactionItem[] = rawArray.map((item: any, idx: number) => {
        // 时间字段：兼容 time/minute，支持 HHmmss / HH:mm:ss / HHmm
        const rawTime = String(item.time ?? item.minute ?? item.datetime ?? item.time_label ?? '');
        const timeLabel = rawTime.length >= 4
          ? rawTime.replace(/:/g, '').slice(0, 4)
          : rawTime;
        const displayTime = timeLabel.length === 4
          ? `${timeLabel.slice(0, 2)}:${timeLabel.slice(2, 4)}`
          : timeLabel;

        // 价格字段：兼容 price/close
        const price = Number(item.price ?? item.close ?? 0);

        // 成交量字段：兼容 volume/vol
        const volume = Number(item.volume ?? item.vol ?? 0);

        // 成交额字段：兼容 amount/money
        const amount = Number(item.amount ?? item.money ?? 0);

        // 交易方向：兼容 direction/buyorsell
        // 后端约定：0=中性 1=主动买入 2=主动卖出
        const rawDir = item.direction ?? item.buyorsell ?? 0;
        let direction = 0;
        if (rawDir === 'B' || rawDir === 'buy' || rawDir === 1 || rawDir === '1' || rawDir === '买') {
          direction = 1; // 主动买入
        } else if (rawDir === 'S' || rawDir === 'sell' || rawDir === 2 || rawDir === '2' || rawDir === '卖') {
          direction = 2; // 主动卖出
        } else if (rawDir === '-' || rawDir === '0' || rawDir === 0) {
          direction = 0; // 中性
        } else if (typeof rawDir === 'number') {
          direction = rawDir; // 直接使用 0/1/2
        }

        return {
          symbol: pureCode,
          trade_date: date,
          seq: idx + 1,
          time_label: displayTime,
          price,
          vol: volume,
          volume,
          amount,
          num: null,
          buyorsell: direction,
          market: 0,
          data_type: 'history',
        };
      });

      return { success: true, data: normalized, errorMsg: '' };
    } catch (e: any) {
      const msg = e.message || '逐笔交易数据请求失败';
      return { success: false, data: [], errorMsg: msg };
    }
  },

  /**
   * 触发全市场K线采集
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
   * VWMA (成交量加权移动平均)
   * GET /api/stock/volume/vwma
   */
  async getVwma(
    symbol: string,
    period: number = 20,
    startDate?: string,
    endDate?: string,
  ): Promise<VolumeVwmaPoint[]> {
    const params: Record<string, any> = { symbol, period };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<VolumeVwmaPoint[]>>(
      STOCK_API.VOLUME_VWMA,
      { params },
    );
    return unwrap<VolumeVwmaPoint[]>(resp, []).map((r) => ({
      ...r,
      trade_date: r.trade_date ? r.trade_date.replace(/-/g, '') : r.trade_date,
    }));
  },

  /**
   * VR (成交量比率 - 基于涨跌方向的加权指标)
   * GET /api/stock/volume/vr
   */
  async getVr(
    symbol: string,
    period: number = 26,
    startDate?: string,
    endDate?: string,
  ): Promise<VolumeVrPoint[]> {
    const params: Record<string, any> = { symbol, period };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<VolumeVrPoint[]>>(
      STOCK_API.VOLUME_VR,
      { params },
    );
    return unwrap<VolumeVrPoint[]>(resp, []).map((r) => ({
      ...r,
      trade_date: r.trade_date ? r.trade_date.replace(/-/g, '') : r.trade_date,
    }));
  },

  /**
   * Volume Bias (成交量乖离率)
   * GET /api/stock/volume/volume-bias
   */
  async getVolumeBias(
    symbol: string,
    periods: string = '5,10,20',
    startDate?: string,
    endDate?: string,
  ): Promise<VolumeBiasPoint[]> {
    const params: Record<string, any> = { symbol, periods };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const resp = await http.get<ApiResponse<VolumeBiasPoint[]>>(
      STOCK_API.VOLUME_BIAS,
      { params },
    );
    return unwrap<VolumeBiasPoint[]>(resp, []).map((r) => ({
      ...r,
      trade_date: r.trade_date ? r.trade_date.replace(/-/g, '') : r.trade_date,
    }));
  },
};