/**
 * 融资融券模块 API
 *
 * 对应后端 routes.py Margin 区块：
 *   GET /api/stock/get-stock-margin-account-info       两融账户信息（东方财富）
 *   GET /api/stock/get-stock-margin-sse                上交所融资融券汇总
 *   GET /api/stock/get-stock-margin-detail-szse        深交所融资融券明细（按日）
 *   GET /api/stock/get-stock-margin-detail-sse         上交所融资融券明细（按日）
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  MarginAccountInfo,
  MarginSseSummary,
  MarginDetailSzse,
  MarginDetailSse,
} from '../../types/stock';

export const marginApi = {
  /** 两融账户信息（全市场逐日时间序列，无入参） */
  async getAccountInfo(): Promise<MarginAccountInfo[]> {
    const resp = await http.get<ApiResponse<MarginAccountInfo | MarginAccountInfo[]>>(
      STOCK_API.MARGIN_ACCOUNT_INFO,
    );
    const data = unwrap<MarginAccountInfo | MarginAccountInfo[]>(resp, []);
    return Array.isArray(data) ? data : [data];
  },

  /** 上交所融资融券汇总（按日期区间） */
  async getSseSummary(
    startDate: string,
    endDate: string,
  ): Promise<MarginSseSummary[]> {
    const resp = await http.get<ApiResponse<MarginSseSummary[]>>(
      STOCK_API.MARGIN_SSE_SUMMARY,
      { params: { start_date: startDate, end_date: endDate } },
    );
    return unwrap<MarginSseSummary[]>(resp, []);
  },

  /** 深交所融资融券明细（按交易日，单日全部标的） */
  async getDetailSzse(date: string): Promise<MarginDetailSzse[]> {
    const resp = await http.get<ApiResponse<MarginDetailSzse[]>>(
      STOCK_API.MARGIN_DETAIL_SZSE,
      { params: { date } },
    );
    return unwrap<MarginDetailSzse[]>(resp, []);
  },

  /** 上交所融资融券明细（按交易日，单日全部标的） */
  async getDetailSse(date: string): Promise<MarginDetailSse[]> {
    const resp = await http.get<ApiResponse<MarginDetailSse[]>>(
      STOCK_API.MARGIN_DETAIL_SSE,
      { params: { date } },
    );
    return unwrap<MarginDetailSse[]>(resp, []);
  },
};
