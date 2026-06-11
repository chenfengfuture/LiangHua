/**
 * 行业/概念板块模块 API
 *
 * 后端实测可用接口（2026-06-01 修复后）：
 *   ✅ /api/stock/get-stock-board                  行业一览（90 条，含领涨股）
 *   ✅ /api/stock/get_all_stock_board_industry     行业 name+code
 *   ✅ /api/stock/get-stock-board-concept-info     概念简介（单条）
 *   ✅ /api/stock/get-stock-board-change-em        板块异动（约1000条）
 *   ✅ /api/stock/get_stock_changes_em             盘口异动（按异动类型筛选个股）
 *   ✅ /api/stock/get-stock-fund-concept           同花顺概念资金流（即时/3/5/10/20日）
 *   ✅ /api/stock/get-stock-board-concept-index-ths  概念板块指数K线（需交易日）
 *   ✅ /api/stock/get-stock-board-industry-index-ths 行业板块指数K线（需交易日）
 *   ✅ /api/stock/get-sector-fund-flow              东方财富板块资金流（行业/概念/地域）
 *   ✅ /api/stock/get-sector-fund-summary           板块内个股资金流
 *   ✅ /api/stock/get-sector-fund-flow-summary      主力净流入排名
 *
 * 后端仍异常（无法在前端解决）：
 *   ❌ /api/stock/get-stock-board-industry-cons     行业成份股（需 BK 代码）
 *   ❌ /api/stock/get-stock-board-concept-cons      概念成份股（需 BK 代码）
 */

import http from '../http';
import { unwrap } from '../utils';
import { STOCK_API } from '../../config';
import type {
  ApiResponse,
  IndustryBoardSummary,
  IndustryBoardCode,
  ConceptBoardInfo,
  BoardChangeItem,
  StockChangeItem,
  BoardIndexKline,
  FundFlowPeriod,
  FundFlowConceptImmediate,
  FundFlowConceptHistory,
  SectorStockFundFlowItem,
} from '../../types/stock';

export const sectorApi = {
  /** 行业一览（含领涨股、净流入） */
  async getIndustrySummary(): Promise<IndustryBoardSummary[]> {
    const resp = await http.get<ApiResponse<IndustryBoardSummary[]>>(
      STOCK_API.BOARD_SUMMARY,
    );
    return unwrap<IndustryBoardSummary[]>(resp, []);
  },

  /** 行业名称+代码（轻量） */
  async getIndustryCodes(): Promise<IndustryBoardCode[]> {
    const resp = await http.get<ApiResponse<IndustryBoardCode[]>>(
      STOCK_API.BOARD_INDUSTRY_CODES,
    );
    return unwrap<IndustryBoardCode[]>(resp, []);
  },

  /** 概念简介 */
  async getConceptInfo(symbol: string): Promise<ConceptBoardInfo[]> {
    const resp = await http.get<ApiResponse<ConceptBoardInfo[]>>(
      STOCK_API.BOARD_CONCEPT_INFO,
      { params: { symbol } },
    );
    return unwrap<ConceptBoardInfo[]>(resp, []);
  },

  /** 板块异动列表（按 board_name 聚合） */
  async getBoardChange(): Promise<BoardChangeItem[]> {
    const resp = await http.get<ApiResponse<BoardChangeItem[]>>(
      STOCK_API.BOARD_CHANGE,
    );
    return unwrap<BoardChangeItem[]>(resp, []);
  },

  /** 盘口异动详情（按异动类型筛选个股） */
  async getStockChanges(symbol: string = '火箭发射'): Promise<StockChangeItem[]> {
    const resp = await http.get<ApiResponse<StockChangeItem[]>>(
      STOCK_API.STOCK_CHANGES,
      { params: { symbol } },
    );
    return unwrap<StockChangeItem[]>(resp, []);
  },

  /** 同花顺概念资金流（即时/3/5/10/20日） */
  async getConceptFundFlow(
    period: FundFlowPeriod = '即时',
    limit: number = 100,
  ): Promise<FundFlowConceptImmediate[] | FundFlowConceptHistory[]> {
    const resp = await http.get<ApiResponse<any[]>>(
      STOCK_API.FUND_FLOW_CONCEPT,
      { params: { symbol: period, limits: String(limit) } },
    );
    return unwrap<any[]>(resp, []);
  },

  /**
   * 同花顺概念板块指数 K线
   * GET /api/stock/get-stock-board-concept-index-ths
   * 注意：start_date/end_date 必须为真实交易日（YYYYMMDD），否则后端返回 422
   */
  async getConceptIndexKline(
    symbol: string,
    startDate: string,
    endDate: string,
  ): Promise<BoardIndexKline[]> {
    const resp = await http.get<ApiResponse<BoardIndexKline[]>>(
      STOCK_API.BOARD_CONCEPT_INDEX_KLINE,
      { params: { symbol, start_date: startDate, end_date: endDate } },
    );
    return unwrap<BoardIndexKline[]>(resp, []);
  },

  /**
   * 同花顺行业板块指数 K线
   * GET /api/stock/get-stock-board-industry-index-ths
   * 注意：start_date/end_date 必须为真实交易日
   */
  async getIndustryIndexKline(
    symbol: string,
    startDate: string,
    endDate: string,
  ): Promise<BoardIndexKline[]> {
    const resp = await http.get<ApiResponse<BoardIndexKline[]>>(
      STOCK_API.BOARD_INDUSTRY_INDEX_KLINE,
      { params: { symbol, start_date: startDate, end_date: endDate } },
    );
    return unwrap<BoardIndexKline[]>(resp, []);
  },

  /**
   * 行业板块成份股（东方财富，超慢，>60s 超时常见）
   * GET /api/stock/get-stock-board-industry-cons
   */
  async getIndustryCons(symbol: string): Promise<any[]> {
    const resp = await http.get<ApiResponse<any[]>>(
      STOCK_API.BOARD_INDUSTRY_CONS,
      { params: { symbol }, timeout: 120000 } as any,
    );
    return unwrap<any[]>(resp, []);
  },

  /**
   * 概念板块成份股（东方财富，超慢）
   * GET /api/stock/get-stock-board-concept-cons
   */
  async getConceptCons(symbol: string): Promise<any[]> {
    const resp = await http.get<ApiResponse<any[]>>(
      STOCK_API.BOARD_CONCEPT_CONS,
      { params: { symbol }, timeout: 120000 } as any,
    );
    return unwrap<any[]>(resp, []);
  },

  /**
   * 板块资金流排名（行业/概念/地域）
   * GET /api/stock/get-sector-fund-flow
   */
  async getSectorFundFlowRank(
    indicator: '今日' | '5日' | '10日' = '今日',
    sectorType: '行业资金流' | '概念资金流' | '地域资金流' = '行业资金流',
  ): Promise<FundFlowConceptImmediate[]> {
    const resp = await http.get<ApiResponse<FundFlowConceptImmediate[]>>(
      STOCK_API.SECTOR_FUND_FLOW,
      { params: { indicator, sector_type: sectorType }, timeout: 60000 } as any,
    );
    return unwrap<FundFlowConceptImmediate[]>(resp, []);
  },

  /**
   * 板块内个股资金流（输入行业/概念名获取成份股资金流）
   * GET /api/stock/get-sector-fund-summary
   */
  async getSectorStockFundFlow(
    symbol: string,
    indicator: '今日' | '5日' | '10日' = '今日',
  ): Promise<SectorStockFundFlowItem[]> {
    const resp = await http.get<ApiResponse<SectorStockFundFlowItem[]>>(
      STOCK_API.SECTOR_FUND_SUMMARY,
      { params: { indicator, symbol }, timeout: 120000 } as any,
    );
    return unwrap<SectorStockFundFlowItem[]>(resp, []);
  },

  /**
   * 主力净流入排名（按市场范围）
   * GET /api/stock/get-sector-fund-flow-summary
   */
  async getMainFundFlowSummary(
    symbol: '全部股票' | '沪深A股' | '沪市A股' | '科创板' | '深市A股' | '创业板' | '沪市B股' | '深市B股' = '沪深A股',
  ): Promise<SectorStockFundFlowItem[]> {
    const resp = await http.get<ApiResponse<SectorStockFundFlowItem[]>>(
      STOCK_API.SECTOR_FUND_FLOW_SUMMARY,
      { params: { symbol }, timeout: 60000 } as any,
    );
    return unwrap<SectorStockFundFlowItem[]>(resp, []);
  },
};