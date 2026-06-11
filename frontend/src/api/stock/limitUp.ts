/**
 * 涨停股池模块 API
 *
 * 对接后端接口（GET）：
 *   - /api/stock/get-stock-zt-pool-em           当日涨停股池
 *   - /api/stock/get-stock-zt-pool-previous-em   昨日涨停股池
 *   - /api/stock/get-stock-zt-pool-strong-em     强势股池
 *   - /api/stock/get-stock-zt-pool-zbgc-em       炸板股池
 *   - /api/stock/get-stock-zt-pool-dtgc-em       跌停股池
 *
 * 参数：date（YYYYMMDD，可选，默认当天）
 * 响应：{ success, message, data: LimitUpPoolItem[] }
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  LimitUpPoolItem,
} from '../../types/stock';

export const limitUpApi = {
  /** 当日涨停股池 */
  async getLimitUpPool(date?: string): Promise<LimitUpPoolItem[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    const resp = await http.get<ApiResponse<LimitUpPoolItem[]>>(
      STOCK_API.LIMIT_UP_POOL,
      { params },
    );
    return unwrap<LimitUpPoolItem[]>(resp, []);
  },

  /** 昨日涨停股池 */
  async getPreviousLimitUp(date?: string): Promise<LimitUpPoolItem[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    const resp = await http.get<ApiResponse<LimitUpPoolItem[]>>(
      STOCK_API.LIMIT_UP_PREVIOUS,
      { params },
    );
    return unwrap<LimitUpPoolItem[]>(resp, []);
  },

  /** 强势股池 */
  async getStrongPool(date?: string): Promise<LimitUpPoolItem[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    const resp = await http.get<ApiResponse<LimitUpPoolItem[]>>(
      STOCK_API.LIMIT_UP_STRONG,
      { params },
    );
    return unwrap<LimitUpPoolItem[]>(resp, []);
  },

  /** 炸板股池 */
  async getZbgcPool(date?: string): Promise<LimitUpPoolItem[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    const resp = await http.get<ApiResponse<LimitUpPoolItem[]>>(
      STOCK_API.LIMIT_UP_ZBGC,
      { params },
    );
    return unwrap<LimitUpPoolItem[]>(resp, []);
  },

  /** 跌停股池 */
  async getDtgcPool(date?: string): Promise<LimitUpPoolItem[]> {
    const params: Record<string, string> = {};
    if (date) params.date = date;
    const resp = await http.get<ApiResponse<LimitUpPoolItem[]>>(
      STOCK_API.LIMIT_UP_DTGC,
      { params },
    );
    return unwrap<LimitUpPoolItem[]>(resp, []);
  },
};