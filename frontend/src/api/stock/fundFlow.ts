/**
 * 资金流向模块 API
 *
 * 对接后端接口（实测可用）：
 *   - GET /api/stock/get-stock-fund-flow-individual  个股资金流（即时/3/5/10/20日排行）
 *   - GET /api/stock/get-stock-fund-concept          行业/概念资金流（即时/3/5/10/20日排行）
 *
 * 实测说明：
 *   * 大盘资金流（get-stock-market-fund-flow）当前返回空，不接入
 *   * 板块/资金流排名（get-sector-fund-flow / get-stock-individual-flow）当前空
 *   * 个股资金流向（get-stock-fund-flow?stock=xxx）当前空
 *   * 仅 fund-flow-individual / fund-concept 两个接口可用
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  FundFlowIndividualImmediate,
  FundFlowIndividualHistory,
  FundFlowConceptImmediate,
  FundFlowConceptHistory,
  FundFlowPeriod,
} from '../../types/stock';

export const fundFlowApi = {
  /**
   * 个股资金流-即时
   * GET /api/stock/get-stock-fund-flow-individual?symbol=即时
   */
  async getIndividualImmediate(
    limit: number = 200,
  ): Promise<FundFlowIndividualImmediate[]> {
    const resp = await http.get<ApiResponse<FundFlowIndividualImmediate[]>>(
      STOCK_API.FUND_FLOW_INDIVIDUAL,
      { params: { symbol: '即时', limits: String(limit) } },
    );
    return unwrap<FundFlowIndividualImmediate[]>(resp, []);
  },

  /**
   * 个股资金流-历史排行（3日/5日/10日/20日）
   * GET /api/stock/get-stock-fund-flow-individual?symbol=Xd排行
   */
  async getIndividualHistory(
    period: Exclude<FundFlowPeriod, '即时'> = '5日排行',
    limit: number = 200,
  ): Promise<FundFlowIndividualHistory[]> {
    const resp = await http.get<ApiResponse<FundFlowIndividualHistory[]>>(
      STOCK_API.FUND_FLOW_INDIVIDUAL,
      { params: { symbol: period, limits: String(limit) } },
    );
    return unwrap<FundFlowIndividualHistory[]>(resp, []);
  },

  /**
   * 行业/概念资金流-即时
   * GET /api/stock/get-stock-fund-concept?symbol=即时
   */
  async getConceptImmediate(
    limit: number = 100,
  ): Promise<FundFlowConceptImmediate[]> {
    const resp = await http.get<ApiResponse<FundFlowConceptImmediate[]>>(
      STOCK_API.FUND_FLOW_CONCEPT,
      { params: { symbol: '即时', limits: String(limit) } },
    );
    return unwrap<FundFlowConceptImmediate[]>(resp, []);
  },

  /**
   * 行业/概念资金流-历史排行（3日/5日/10日/20日）
   * GET /api/stock/get-stock-fund-concept?symbol=Xd排行
   */
  async getConceptHistory(
    period: Exclude<FundFlowPeriod, '即时'> = '5日排行',
    limit: number = 100,
  ): Promise<FundFlowConceptHistory[]> {
    const resp = await http.get<ApiResponse<FundFlowConceptHistory[]>>(
      STOCK_API.FUND_FLOW_CONCEPT,
      { params: { symbol: period, limits: String(limit) } },
    );
    return unwrap<FundFlowConceptHistory[]>(resp, []);
  },
};