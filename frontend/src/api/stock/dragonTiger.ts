/**
 * 龙虎榜模块 API
 *
 * 对应后端 routes.py LHB 区块：
 *   GET /api/stock/get-stock-lhb-jgmmtj-em         机构买卖每日统计
 *   GET /api/stock/get-stock-lhb-detail             龙虎榜详情
 *   GET /api/stock/get-stock-lhb-stock-statistic-em 个股上榜统计
 *   GET /api/stock/get-stock-lhb-hyyyb-em          每日活跃营业部
 *   GET /api/stock/get-stock-yybph-em-service      营业部排行
 *   GET /api/stock/get-stock-traderstatistic-em    营业部综合统计
 *   GET /api/stock/get-stock-lh-yyh-most           上榜次数最多
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  LhbInstitutionTrading,
  LhbDetail,
  LhbStockStatistic,
  LhbBrokerDaily,
  LhbBrokerPerformance,
  LhbBrokerSummary,
  LhbBrokerMost,
} from '../../types/stock';

export const dragonTigerApi = {
  /** 机构买卖每日统计 */
  async getInstitutionTrading(
    startDate: string,
    endDate: string,
  ): Promise<LhbInstitutionTrading[]> {
    const resp = await http.get<ApiResponse<LhbInstitutionTrading[]>>(
      STOCK_API.LHB_INSTITUTION_TRADING,
      { params: { start_date: startDate, end_date: endDate } },
    );
    return unwrap<LhbInstitutionTrading[]>(resp, []);
  },

  /** 龙虎榜详情 */
  async getLhbDetail(
    startDate: string,
    endDate: string,
  ): Promise<LhbDetail[]> {
    const resp = await http.get<ApiResponse<LhbDetail[]>>(
      STOCK_API.LHB_DETAIL,
      { params: { start_date: startDate, end_date: endDate } },
    );
    return unwrap<LhbDetail[]>(resp, []);
  },

  /** 个股上榜统计 */
  async getStockStatistic(
    symbol: '近一月' | '近三月' | '近六月' | '近一年' = '近一月',
  ): Promise<LhbStockStatistic[]> {
    const resp = await http.get<ApiResponse<LhbStockStatistic | LhbStockStatistic[]>>(
      STOCK_API.LHB_STOCK_STATISTIC,
      { params: { symbol } },
    );
    const data = unwrap<LhbStockStatistic | LhbStockStatistic[]>(resp, []);
    return Array.isArray(data) ? data : [data];
  },

  /** 每日活跃营业部 */
  async getBrokerDaily(
    startDate: string,
    endDate: string,
  ): Promise<LhbBrokerDaily[]> {
    const resp = await http.get<ApiResponse<LhbBrokerDaily[]>>(
      STOCK_API.LHB_BROKER_DAILY,
      { params: { start_date: startDate, end_date: endDate } },
    );
    return unwrap<LhbBrokerDaily[]>(resp, []);
  },

  /** 营业部排行 */
  async getBrokerPerformance(
    symbol: '近一月' | '近三月' | '近六月' | '近一年' = '近三月',
  ): Promise<LhbBrokerPerformance[]> {
    const resp = await http.get<ApiResponse<LhbBrokerPerformance | LhbBrokerPerformance[]>>(
      STOCK_API.LHB_BROKER_PERFORMANCE,
      { params: { symbol } },
    );
    const data = unwrap<LhbBrokerPerformance | LhbBrokerPerformance[]>(resp, []);
    return Array.isArray(data) ? data : [data];
  },

  /** 营业部综合统计 */
  async getBrokerSummary(
    symbol: '近一月' | '近三月' | '近六月' | '近一年' = '近一月',
  ): Promise<LhbBrokerSummary[]> {
    const resp = await http.get<ApiResponse<LhbBrokerSummary[]>>(
      STOCK_API.LHB_BROKER_SUMMARY,
      { params: { symbol } },
    );
    return unwrap<LhbBrokerSummary[]>(resp, []);
  },

  /** 上榜次数最多 */
  async getBrokerMost(): Promise<LhbBrokerMost[]> {
    const resp = await http.get<ApiResponse<LhbBrokerMost | LhbBrokerMost[]>>(
      STOCK_API.LHB_BROKER_MOST,
    );
    const data = unwrap<LhbBrokerMost | LhbBrokerMost[]>(resp, []);
    return Array.isArray(data) ? data : [data];
  },
};