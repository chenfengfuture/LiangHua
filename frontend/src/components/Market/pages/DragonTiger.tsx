/**
 * 龙虎榜页面 - 独立子分类视图
 *
 * 对接后端接口：
 *   - GET /api/stock/get-stock-lhb-detail          龙虎榜详情
 *   - GET /api/stock/get-stock-lhb-jgmmtj-em       机构买卖每日统计
 *   - GET /api/stock/get-stock-lhb-stock-statistic-em 个股上榜统计
 *   - GET /api/stock/get-stock-lhb-hyyyb-em        每日活跃营业部
 *   - GET /api/stock/get-stock-yybph-em-service     营业部排行
 *   - GET /api/stock/get-stock-traderstatistic-em   营业部综合统计
 *   - GET /api/stock/get-stock-lh-yyh-most          上榜次数最多营业部
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Tabs, Table, Tag, Typography, Space, DatePicker, Spin, message, Row, Col, Card, Statistic, Button, Select } from 'antd';
import {
  TrophyOutlined,
  SwapOutlined,
  BankOutlined,
  FireOutlined,
  RiseOutlined,
  TeamOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Dayjs } from 'dayjs';
import { useTheme } from '@/themes';
import { dragonTigerApi } from '@/api/stock';
import { safeNum, safeToFixed } from '@/utils/format';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { readDailyCache, writeDailyCache, makeKey } from '@/utils/dailyCache';
import { getDefaultTradingDate } from '@/utils/tradingDate';
import StockDetailDrawer from '@/components/Market/StockDetailDrawer';
import type { StockDetailItem } from '@/components/Market/StockDetailDrawer';
import type {
  LhbDetail,
  LhbInstitutionTrading,
  LhbStockStatistic,
  LhbBrokerDaily,
  LhbBrokerPerformance,
  LhbBrokerSummary,
  LhbBrokerMost,
} from '../../../types/stock';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;

// ─── 工具函数 ───────────────────────────────────────────────────

/** 格式化金额（元 → 亿元，保留2位） */
const fmtYi = (v: number | string | null | undefined): string => {
  if (v == null) return '--';
  const n = safeNum(v, NaN);
  if (isNaN(n)) return '--';
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万';
  return n.toFixed(2);
};

/** 格式化百分比 */
const fmtPct = (v: number | string | null | undefined): string => {
  const s = safeToFixed(v, 2, '');
  return s ? s + '%' : '--';
};

/** 安全格式化数值（兼容字符串输入） */
const fmtNum = (v: number | string | null | undefined, digits = 2): string => {
  return safeToFixed(v, digits);
};

/** 涨跌色 */
const pctColor = (v: number | string | null | undefined): string => {
  if (v == null) return '#999';
  const n = safeNum(v, NaN);
  if (isNaN(n) || n === 0) return '#999';
  return n > 0 ? '#ff4d4f' : '#52c41a';
};

/** 格式化日期为 YYYYMMDD */
const fmtDate = (d: Dayjs) => d.format('YYYYMMDD');

/**
 * 按日期范围过滤数据（客户端过滤）
 * 后端因缓存共享可能返回全部数据，前端按 trade_date 做二次筛选
 */
const filterByDateRange = <T extends { trade_date?: string }>(
  data: T[],
  start: Dayjs,
  end: Dayjs,
): T[] => {
  if (!data || !data.length) return data || [] as T[];
  const startStr = fmtDate(start);
  const endStr = fmtDate(end);
  return data.filter((r) => {
    const td = r.trade_date?.replace(/-/g, '');
    return !!td && td >= startStr && td <= endStr;
  });
};

/** 按指定字段去重（兜底：即使后端 Redis 有重复数据，前端保证渲染唯一） */
const dedupByKeys = <T extends Record<string, any>>(
  data: T[],
  keys: (keyof T)[],
): T[] => {
  const seen = new Set<string>();
  return data.filter((item) => {
    const key = keys.map((k) => String(item[k] ?? '')).join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

// ─── 组件 ───────────────────────────────────────────────────────

const DragonTiger: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState('detail');

  // 日期范围
  // 默认：单日 — 当天是交易日且 >=17:00 取当天，否则取上一交易日
  // RangePicker 的 start=end（用户再手动展开选择范围）
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>(() => {
    const d = getDefaultTradingDate();
    return [d, d];
  });

  // 时间维度（个股统计/营业部排行用）
  const [period, setPeriod] = useState<'近一月' | '近三月' | '近六月' | '近一年'>('近一月');

  // 数据状态
  const [detailList, setDetailList] = useState<LhbDetail[]>([]);
  const [instList, setInstList] = useState<LhbInstitutionTrading[]>([]);
  const [stockStatList, setStockStatList] = useState<LhbStockStatistic[]>([]);
  const [brokerDailyList, setBrokerDailyList] = useState<LhbBrokerDaily[]>([]);
  const [brokerPerfList, setBrokerPerfList] = useState<LhbBrokerPerformance[]>([]);
  const [brokerSummaryList, setBrokerSummaryList] = useState<LhbBrokerSummary[]>([]);
  const [brokerMostList, setBrokerMostList] = useState<LhbBrokerMost[]>([]);

  const [loading, setLoading] = useState(false);

  // 个股详情抽屉状态
  const [stockPages, setStockPages] = useState<StockDetailItem[]>([]);
  const [activeStockIndex, setActiveStockIndex] = useState<number>(0);
  const [drawerVisible, setDrawerVisible] = useState(false);

  // ─── 数据加载 ─────────────────────────────────────────────────

  const loadDetail = useCallback(async (force = false) => {
    const CK = makeKey('lhb:detail', { start: fmtDate(dateRange[0]), end: fmtDate(dateRange[1]) });
    if (!force) {
      const c = readDailyCache<LhbDetail[]>(CK);
      if (c) { setDetailList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getLhbDetail(
        fmtDate(dateRange[0]),
        fmtDate(dateRange[1]),
      );
      const filtered = filterByDateRange(data, dateRange[0], dateRange[1]);
      const dedup = dedupByKeys(filtered, ['symbol', 'trade_date']);
      setDetailList(dedup);
      writeDailyCache(CK, dedup);
    } catch (e: any) {
      message.error('龙虎榜详情加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  const loadInst = useCallback(async (force = false) => {
    const CK = makeKey('lhb:institution', { start: fmtDate(dateRange[0]), end: fmtDate(dateRange[1]) });
    if (!force) {
      const c = readDailyCache<LhbInstitutionTrading[]>(CK);
      if (c) { setInstList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getInstitutionTrading(
        fmtDate(dateRange[0]),
        fmtDate(dateRange[1]),
      );
      const filtered = filterByDateRange(data, dateRange[0], dateRange[1]);
      const dedup = dedupByKeys(filtered, ['symbol', 'trade_date']);
      setInstList(dedup);
      writeDailyCache(CK, dedup);
    } catch (e: any) {
      message.error('机构买卖统计加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  const loadStockStat = useCallback(async (force = false) => {
    const CK = makeKey('lhb:stockStat', { period });
    if (!force) {
      const c = readDailyCache<LhbStockStatistic[]>(CK);
      if (c) { setStockStatList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getStockStatistic(period);
      setStockStatList(data || []);
      writeDailyCache(CK, data || []);
    } catch (e: any) {
      message.error('个股上榜统计加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  const loadBrokerDaily = useCallback(async (force = false) => {
    const CK = makeKey('lhb:brokerDaily', { start: fmtDate(dateRange[0]), end: fmtDate(dateRange[1]) });
    if (!force) {
      const c = readDailyCache<LhbBrokerDaily[]>(CK);
      if (c) { setBrokerDailyList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getBrokerDaily(
        fmtDate(dateRange[0]),
        fmtDate(dateRange[1]),
      );
      const filtered = filterByDateRange(data, dateRange[0], dateRange[1]);
      const dedup = dedupByKeys(filtered, ['broker_name', 'trade_date']);
      setBrokerDailyList(dedup);
      writeDailyCache(CK, dedup);
    } catch (e: any) {
      message.error('活跃营业部加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  const loadBrokerPerf = useCallback(async (force = false) => {
    const CK = makeKey('lhb:brokerPerf', { period });
    if (!force) {
      const c = readDailyCache<LhbBrokerPerformance[]>(CK);
      if (c) { setBrokerPerfList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getBrokerPerformance(period);
      setBrokerPerfList(data || []);
      writeDailyCache(CK, data || []);
    } catch (e: any) {
      message.error('营业部排行加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  const loadBrokerSummary = useCallback(async (force = false) => {
    const CK = makeKey('lhb:brokerSummary', { period });
    if (!force) {
      const c = readDailyCache<LhbBrokerSummary[]>(CK);
      if (c) { setBrokerSummaryList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getBrokerSummary(period);
      setBrokerSummaryList(data || []);
      writeDailyCache(CK, data || []);
    } catch (e: any) {
      message.error('营业部综合统计加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  const loadBrokerMost = useCallback(async (force = false) => {
    const CK = 'lhb:brokerMost';
    if (!force) {
      const c = readDailyCache<LhbBrokerMost[]>(CK);
      if (c) { setBrokerMostList(c); return; }
    }
    setLoading(true);
    try {
      const data = await dragonTigerApi.getBrokerMost();
      setBrokerMostList(data || []);
      writeDailyCache(CK, data || []);
    } catch (e: any) {
      message.error('上榜次数最多加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Tab 切换时自动加载
  useEffect(() => {
    switch (activeTab) {
      case 'detail': loadDetail(); break;
      case 'institution': loadInst(); break;
      case 'stock-stat': loadStockStat(); break;
      case 'broker-daily': loadBrokerDaily(); break;
      case 'broker-perf': loadBrokerPerf(); break;
      case 'broker-summary': loadBrokerSummary(); break;
      case 'broker-most': loadBrokerMost(); break;
    }
  }, [activeTab, loadDetail, loadInst, loadStockStat, loadBrokerDaily, loadBrokerPerf, loadBrokerSummary, loadBrokerMost]);

  const handleRefresh = useCallback(() => {
    switch (activeTab) {
      case 'detail': loadDetail(true); break;
      case 'institution': loadInst(true); break;
      case 'stock-stat': loadStockStat(true); break;
      case 'broker-daily': loadBrokerDaily(true); break;
      case 'broker-perf': loadBrokerPerf(true); break;
      case 'broker-summary': loadBrokerSummary(true); break;
      case 'broker-most': loadBrokerMost(true); break;
    }
  }, [activeTab, loadDetail, loadInst, loadStockStat, loadBrokerDaily, loadBrokerPerf, loadBrokerSummary, loadBrokerMost]);

  // ─── 个股详情抽屉 ────────────────────────────────────────────

  /** 点击股票名称/代码，打开个股详情抽屉 */
  const handleStockClick = useCallback((symbol: string, name: string) => {
    const item: StockDetailItem = { symbol, name };
    setStockPages((prev) => {
      // 如果该股票已经打开过，直接跳转到对应位置
      const idx = prev.findIndex((s) => s.symbol === symbol);
      if (idx >= 0) {
        setActiveStockIndex(idx);
        return prev;
      }
      // 否则追加
      const newList = [...prev, item];
      setActiveStockIndex(newList.length - 1);
      return newList;
    });
    setDrawerVisible(true);
  }, []);

  /** 页面选择器切换 */
  const handlePageSelect = useCallback((index: number) => {
    setActiveStockIndex(index);
  }, []);

  /** 关闭抽屉 */
  const handleDrawerClose = useCallback(() => {
    setDrawerVisible(false);
  }, []);

  // ─── 表格列定义 ───────────────────────────────────────────────

  /** 龙虎榜详情列 */
  const detailColumns = useMemo(() => [
    { title: '代码', dataIndex: 'symbol', width: 80, fixed: 'left' as const,
      render: (v: string, r: LhbDetail) => (
        <a
          style={{ fontFamily: 'monospace', cursor: 'pointer' }}
          onClick={() => handleStockClick(v, r.name)}
        >
          {v}
        </a>
      ) },
    { title: '名称', dataIndex: 'name', width: 90, fixed: 'left' as const,
      render: (v: string, r: LhbDetail) => (
        <a
          style={{ fontWeight: 600, cursor: 'pointer' }}
          onClick={() => handleStockClick(r.symbol, v)}
        >
          {v}
        </a>
      ) },
    { title: '上榜日', dataIndex: 'trade_date', width: 100 },
    { title: '收盘价', dataIndex: 'close_price', width: 80, align: 'right' as const,
      render: (v: number | string) => fmtNum(v) },
    { title: '涨跌幅', dataIndex: 'change_percent', width: 80, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '净买额', dataIndex: 'lhb_net_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '买入额', dataIndex: 'lhb_buy_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => fmtYi(v) },
    { title: '卖出额', dataIndex: 'lhb_sell_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => fmtYi(v) },
    { title: '成交额', dataIndex: 'lhb_turnover_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => fmtYi(v) },
    { title: '换手率', dataIndex: 'turnover_rate', width: 75, align: 'right' as const,
      render: (v: number | string) => fmtPct(v) },
    { title: '解读', dataIndex: 'interpretation', width: 180, ellipsis: true },
    { title: '上榜原因', dataIndex: 'reason', width: 200, ellipsis: true },
    { title: '后1日', dataIndex: 'after_1d_pct_change', width: 70, align: 'right' as const,
      render: (v: number | string | null) => v != null ? <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> : '--' },
    { title: '后5日', dataIndex: 'after_5d_pct_change', width: 70, align: 'right' as const,
      render: (v: number | string | null) => v != null ? <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> : '--' },
  ], [colors]);

  /** 机构买卖统计列 */
  const instColumns = useMemo(() => [
    { title: '代码', dataIndex: 'symbol', width: 80, fixed: 'left' as const },
    { title: '名称', dataIndex: 'name', width: 90, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '上榜日', dataIndex: 'trade_date', width: 100 },
    { title: '收盘价', dataIndex: 'close_price', width: 80, align: 'right' as const,
      render: (v: number | string) => fmtNum(v) },
    { title: '涨跌幅', dataIndex: 'change_percent', width: 80, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '买方机构', dataIndex: 'buy_institution_count', width: 85, align: 'center' as const },
    { title: '卖方机构', dataIndex: 'sell_institution_count', width: 85, align: 'center' as const },
    { title: '机构净买', dataIndex: 'institution_net_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '机构买入', dataIndex: 'institution_buy_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => fmtYi(v) },
    { title: '机构卖出', dataIndex: 'institution_sell_amount', width: 100, align: 'right' as const,
      render: (v: number | string) => fmtYi(v) },
    { title: '净买占比', dataIndex: 'institution_net_ratio', width: 80, align: 'right' as const,
      render: (v: number | string) => fmtPct(v) },
    { title: '换手率', dataIndex: 'turnover_rate', width: 75, align: 'right' as const,
      render: (v: number | string) => fmtPct(v) },
    { title: '上榜原因', dataIndex: 'reason', width: 200, ellipsis: true },
  ], []);

  /** 个股上榜统计列 */
  const stockStatColumns = useMemo(() => [
    { title: '代码', dataIndex: 'symbol', width: 80 },
    { title: '名称', dataIndex: 'name', width: 90,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '最近上榜日', dataIndex: 'latest_trade_date', width: 100 },
    { title: '收盘价', dataIndex: 'close_price', width: 80, align: 'right' as const,
      render: (v: string) => safeToFixed(v, 2) },
    { title: '涨跌幅', dataIndex: 'change_percent', width: 80, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '上榜次数', dataIndex: 'total_lhb_times', width: 80, align: 'center' as const },
    { title: '净买额', dataIndex: 'lhb_net_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '机构净买', dataIndex: 'institution_net_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '近1月', dataIndex: 'pct_change_1m', width: 80, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '近3月', dataIndex: 'pct_change_3m', width: 80, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
  ], []);

  /** 每日活跃营业部列 */
  const brokerDailyColumns = useMemo(() => [
    { title: '营业部名称', dataIndex: 'broker_name', width: 260, fixed: 'left' as const,
      render: (v: string) => <Text strong style={{ color: colors.textPrimary }}>{v}</Text> },
    { title: '上榜日', dataIndex: 'trade_date', width: 100 },
    { title: '买入个股数', dataIndex: 'buy_stock_count', width: 90, align: 'center' as const },
    { title: '卖出个股数', dataIndex: 'sell_stock_count', width: 90, align: 'center' as const },
    { title: '买入总额', dataIndex: 'total_buy_amount', width: 110, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: '#ff4d4f' }}>{fmtYi(v)}</Text> },
    { title: '卖出总额', dataIndex: 'total_sell_amount', width: 110, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: '#52c41a' }}>{fmtYi(v)}</Text> },
    { title: '净买额', dataIndex: 'net_buy_amount', width: 110, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '买入股票', dataIndex: 'buy_stocks', width: 300, ellipsis: true },
  ], [colors]);

  /** 营业部排行列 */
  const brokerPerfColumns = useMemo(() => [
    { title: '营业部名称', dataIndex: 'broker_name', width: 260, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '1日-买入次数', dataIndex: 'buy_count_1d', width: 100, align: 'center' as const },
    { title: '1日-均涨幅', dataIndex: 'avg_return_1d', width: 95, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '1日-上涨率', dataIndex: 'up_prob_1d', width: 95, align: 'right' as const,
      render: (v: string) => fmtPct(v) },
    { title: '3日-买入次数', dataIndex: 'buy_count_3d', width: 100, align: 'center' as const },
    { title: '3日-均涨幅', dataIndex: 'avg_return_3d', width: 95, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '3日-上涨率', dataIndex: 'up_prob_3d', width: 95, align: 'right' as const,
      render: (v: string) => fmtPct(v) },
    { title: '5日-买入次数', dataIndex: 'buy_count_5d', width: 100, align: 'center' as const },
    { title: '5日-均涨幅', dataIndex: 'avg_return_5d', width: 95, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '5日-上涨率', dataIndex: 'up_prob_5d', width: 95, align: 'right' as const,
      render: (v: string) => fmtPct(v) },
    { title: '10日-均涨幅', dataIndex: 'avg_return_10d', width: 95, align: 'right' as const,
      render: (v: string) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
  ], []);

  /** 营业部综合统计列 */
  const brokerSummaryColumns = useMemo(() => [
    { title: '营业部名称', dataIndex: 'broker_name', width: 280, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '上榜次数', dataIndex: 'total_lhb_times', width: 90, align: 'center' as const,
      sorter: (a: LhbBrokerSummary, b: LhbBrokerSummary) =>
        (Number(a.total_lhb_times) || 0) - (Number(b.total_lhb_times) || 0) },
    { title: '龙虎榜成交额', dataIndex: 'total_lhb_amount', width: 120, align: 'right' as const,
      render: (v: number | string) => fmtYi(v),
      sorter: (a: LhbBrokerSummary, b: LhbBrokerSummary) =>
        (Number(a.total_lhb_amount) || 0) - (Number(b.total_lhb_amount) || 0) },
    { title: '买入总额', dataIndex: 'total_buy_amount', width: 110, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: '#ff4d4f' }}>{fmtYi(v)}</Text> },
    { title: '买入次数', dataIndex: 'total_buy_times', width: 85, align: 'center' as const },
    { title: '卖出总额', dataIndex: 'total_sell_amount', width: 110, align: 'right' as const,
      render: (v: number | string) => <Text style={{ color: '#52c41a' }}>{fmtYi(v)}</Text> },
    { title: '卖出次数', dataIndex: 'total_sell_times', width: 85, align: 'center' as const },
  ], []);

  /** 上榜次数最多营业部列 */
  const brokerMostColumns = useMemo(() => [
    { title: '营业部名称', dataIndex: 'broker_name', width: 300, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '上榜次数', dataIndex: 'total_lhb_times', width: 100, align: 'center' as const },
    { title: '动用资金', dataIndex: 'total_fund_amount', width: 110, align: 'right' as const,
      render: (v: string) => safeToFixed(v, 2) + '亿' },
    { title: '年内上榜', dataIndex: 'year_total_times', width: 100, align: 'center' as const },
    { title: '年内买入股票数', dataIndex: 'year_buy_stock_count', width: 120, align: 'center' as const },
    { title: '3日跟买成功率', dataIndex: 'year_3d_success_rate', width: 120, align: 'right' as const,
      render: (v: string) => fmtPct(v) },
  ], []);

  // ─── 顶部统计概览 ─────────────────────────────────────────────

  const summaryStats = useMemo(() => {
    const d = detailList;
    if (!d.length) return null;
    const netBuySum = d.reduce((s, r) => s + (Number(r.lhb_net_amount) || 0), 0);
    const buySum = d.reduce((s, r) => s + (Number(r.lhb_buy_amount) || 0), 0);
    const sellSum = d.reduce((s, r) => s + (Number(r.lhb_sell_amount) || 0), 0);
    const upCount = d.filter(r => (Number(r.change_percent) || 0) > 0).length;
    return { count: d.length, netBuy: netBuySum, buy: buySum, sell: sellSum, upCount };
  }, [detailList]);

  // ─── 渲染 ─────────────────────────────────────────────────────

  /** 日期选择器 + 时间维度选择 */
  const renderDateFilter = () => {
    const needDateRange = ['detail', 'institution', 'broker-daily'].includes(activeTab);
    const needPeriod = ['stock-stat', 'broker-perf', 'broker-summary'].includes(activeTab);

    return (
      <Space style={{ marginBottom: 16 }}>
        {needDateRange && (
          <RangePicker
            value={dateRange}
            onChange={(v) => {
              if (v && v[0] && v[1]) setDateRange([v[0], v[1]]);
            }}
            format="YYYY-MM-DD"
            size="small"
            style={{ width: 260 }}
          />
        )}
        {needPeriod && (
          <Space>
            <Text style={{ color: colors.textTertiary, fontSize: 13 }}>时间维度：</Text>
            {(['近一月', '近三月', '近六月', '近一年'] as const).map(p => (
              <Tag
                key={p}
                color={period === p ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => setPeriod(p)}
              >
                {p}
              </Tag>
            ))}
          </Space>
        )}
        <Button
          type="primary"
          size="small"
          ghost
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
        >
          刷新
        </Button>
      </Space>
    );
  };

  const { containerRef, scrollY } = useTableScrollY(52);

  const tableProps = {
    size: 'small' as const,
    scroll: { x: 1400, y: scrollY },
    pagination: { pageSize: 20, showSizeChanger: true, showTotal: (t: number) => `共 ${t} 条` },
    style: { fontSize: 13 },
    rowKey: (r: any, i?: number) => `${r.serial_number ?? i}-${r.symbol || r.broker_name || ''}-${r.trade_date || r.data_type || ''}`,
  };

  return (
    <div style={{ padding: '0 4px', height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexShrink: 0 }}>
        <Space>
          <TrophyOutlined style={{ fontSize: 20, color: '#56A4FF' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>龙虎榜</Title>
          <Tag color="blue" style={{ marginLeft: 8 }}>东方财富</Tag>
          {stockPages.length > 0 && (
            <Select
              value={activeStockIndex}
              onChange={handlePageSelect}
              size="small"
              style={{ width: 200, marginLeft: 12 }}
              options={stockPages.map((s, i) => ({
                label: `${s.name} (${s.symbol})`,
                value: i,
              }))}
            />
          )}
        </Space>
      </div>

      {/* 顶部概览（仅龙虎榜详情Tab显示） */}
      {activeTab === 'detail' && summaryStats && (
        <Row gutter={12} style={{ marginBottom: 16, flexShrink: 0 }}>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic title="上榜股票" value={summaryStats.count} suffix="只"
                valueStyle={{ color: colors.textPrimary, fontSize: 22 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic title="龙虎榜净买额" value={fmtYi(summaryStats.netBuy)}
                valueStyle={{ color: pctColor(summaryStats.netBuy), fontSize: 22 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic title="买入总额" value={fmtYi(summaryStats.buy)}
                valueStyle={{ color: '#ff4d4f', fontSize: 22 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic title="上涨占比" value={summaryStats.count ? (summaryStats.upCount / summaryStats.count * 100).toFixed(1) : 0}
                suffix="%" valueStyle={{ color: '#ff4d4f', fontSize: 22 }} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Tab 切换 */}
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="small"
          type="card"
          style={{ height: '100%' }}
          items={[
          {
            key: 'detail',
            label: <span><SwapOutlined /> 龙虎榜详情</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={detailColumns}
                    dataSource={detailList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'institution',
            label: <span><BankOutlined /> 机构买卖统计</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={instColumns}
                    dataSource={instList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'stock-stat',
            label: <span><RiseOutlined /> 个股上榜统计</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={stockStatColumns}
                    dataSource={stockStatList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'broker-daily',
            label: <span><TeamOutlined /> 每日活跃营业部</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={brokerDailyColumns}
                    dataSource={brokerDailyList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'broker-perf',
            label: <span><FireOutlined /> 营业部排行</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={brokerPerfColumns}
                    dataSource={brokerPerfList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'broker-summary',
            label: <span><BankOutlined /> 营业部综合统计</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={brokerSummaryColumns}
                    dataSource={brokerSummaryList}
                  />
                </Spin>
              </div>
            ),
          },
          {
            key: 'broker-most',
            label: <span><TrophyOutlined /> 上榜次数最多</span>,
            children: (
              <div style={{ height: '100%' }}>
                <Spin spinning={loading}>
                  {renderDateFilter()}
                  <Table
                    {...tableProps}
                    columns={brokerMostColumns}
                    dataSource={brokerMostList}
                  />
                </Spin>
              </div>
            ),
          },
        ]}
      />
      </div>
      {/* /flex-content */}

      {/* 个股详情抽屉 */}
      <StockDetailDrawer
        visible={drawerVisible}
        stockList={stockPages}
        currentIndex={activeStockIndex}
        onClose={handleDrawerClose}
        onNavigate={handlePageSelect}
      />
    </div>
  );
};

export default React.memo(DragonTiger);
