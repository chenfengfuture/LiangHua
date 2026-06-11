/**
 * 资金流向页面 - 市场概览子页面
 *
 * 对接后端接口（仅保留实测可用的两个）：
 *   - GET /api/stock/get-stock-fund-flow-individual  个股资金流（即时/3/5/10/20日排行）
 *   - GET /api/stock/get-stock-fund-concept          行业/概念资金流（即时/3/5/10/20日排行）
 *
 * Tab 布局：
 *   1. 个股即时         — 即时资金流入流出 TOP N
 *   2. 个股历史排行     — 3/5/10/20 日阶段净流入排行
 *   3. 行业/概念即时    — 行业概念资金净流入排行 + 龙头股
 *   4. 行业/概念历史排行 — 行业概念阶段净流入排行
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Tabs, Table, Typography, Space, Select, Spin, message, Button, Tag } from 'antd';
import {
  DollarOutlined,
  StockOutlined,
  AppstoreOutlined,
  ReloadOutlined,
  FundOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import { fundFlowApi } from '@/api/stock';
import { safeNum, safeToFixed } from '@/utils/format';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { readDailyCache, writeDailyCache, makeKey, TTL } from '@/utils/dailyCache';
import type {
  FundFlowIndividualImmediate,
  FundFlowIndividualHistory,
  FundFlowConceptImmediate,
  FundFlowConceptHistory,
  FundFlowPeriod,
} from '../../../types/stock';

const { Text, Title } = Typography;

// ─── 工具函数 ─────────────────────────────────────────────────────────

/** 解析"X亿"/"X万"/纯数字字符串 → number（单位：亿） */
const parseAmountToYi = (v: string | number | null | undefined): number => {
  if (v == null) return 0;
  if (typeof v === 'number') return v;
  const s = String(v).trim();
  if (!s) return 0;
  if (s.endsWith('亿')) return parseFloat(s.replace('亿', '')) || 0;
  if (s.endsWith('万')) return (parseFloat(s.replace('万', '')) || 0) / 1e4;
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
};

/** 解析百分号字符串 "20.02%" → 20.02 */
const parsePct = (v: string | number | null | undefined): number => {
  if (v == null) return 0;
  if (typeof v === 'number') return v;
  const n = parseFloat(String(v).replace('%', ''));
  return isNaN(n) ? 0 : n;
};

/** 涨跌色（中国规则：红涨绿跌） */
const pctColor = (v: number): string => {
  if (v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

/** 安全显示原始字符串/数字 */
const safeStr = (v: any): string => (v == null ? '--' : String(v));

/** 格式化股票代码（补零到6位） */
const fmtSymbol = (v: string | number): string => {
  const s = String(v);
  return /^\d+$/.test(s) ? s.padStart(6, '0') : s;
};

const HISTORY_PERIODS: Array<Exclude<FundFlowPeriod, '即时'>> = [
  '3日排行',
  '5日排行',
  '10日排行',
  '20日排行',
];

const LIMIT_OPTIONS = [50, 100, 200, 500];

// ─── 主组件 ─────────────────────────────────────────────────────────

const FundFlow: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState<string>('individual-now');

  return (
    <div className="page-layout">
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
          gap: '8px',
          flexShrink: 0,
        }}
      >
        <Space size="small" align="center">
          <DollarOutlined style={{ color: '#F59E0B', fontSize: '18px' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>
            资金流向
          </Title>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>·</Text>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>
            数据源：东方财富 / 同花顺（个股 + 行业概念）
          </Text>
        </Space>
      </div>

      {/* Tab 切换 */}
      <div className="flex-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="middle"
          style={{ height: '100%' }}
          items={[
          {
            key: 'individual-now',
            label: (
              <span>
                <StockOutlined /> 个股即时
              </span>
            ),
            children: <IndividualImmediatePanel />,
          },
          {
            key: 'individual-hist',
            label: (
              <span>
                <FundOutlined /> 个股历史排行
              </span>
            ),
            children: <IndividualHistoryPanel />,
          },
          {
            key: 'concept-now',
            label: (
              <span>
                <AppstoreOutlined /> 行业/概念即时
              </span>
            ),
            children: <ConceptImmediatePanel />,
          },
          {
            key: 'concept-hist',
            label: (
              <span>
                <AppstoreOutlined /> 行业/概念历史排行
              </span>
            ),
            children: <ConceptHistoryPanel />,
          },
        ]}
      />
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════
//  Panel 1: 个股即时资金流
// ═══════════════════════════════════════════════════════════════════

const IndividualImmediatePanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [data, setData] = useState<FundFlowIndividualImmediate[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(200);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('fundflow:individualImmediate', { limit });
    // 即时数据 → 短 TTL（60s）
    if (!force) {
      const c = readDailyCache<FundFlowIndividualImmediate[]>(CK, { ttlMs: TTL.REALTIME });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const result = await fundFlowApi.getIndividualImmediate(limit);
      setData(result || []);
      writeDailyCache(CK, result || []);
      if (!result || result.length === 0) message.warning('个股即时资金流数据为空（非交易日或数据源故障）');
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = useMemo(() => [
    {
      title: '#',
      dataIndex: 'serial_number',
      width: 48,
      render: (v: number) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
    {
      title: '代码',
      dataIndex: 'symbol',
      width: 80,
      render: (v: string | number) => (
        <Text style={{ color: '#56A4FF', fontSize: '12px', fontFamily: 'monospace' }}>{fmtSymbol(v)}</Text>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 100,
      render: (v: string) => <Text style={{ color: colors.textPrimary, fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '最新价',
      dataIndex: 'latest_price',
      width: 80,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: colors.textPrimary }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_percent',
      width: 90,
      align: 'right' as const,
      sorter: (a: FundFlowIndividualImmediate, b: FundFlowIndividualImmediate) =>
        parsePct(a.change_percent) - parsePct(b.change_percent),
      render: (v: string) => {
        const n = parsePct(v);
        return <Text style={{ color: pctColor(n), fontWeight: 600 }}>{v}</Text>;
      },
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      width: 80,
      align: 'right' as const,
      render: (v: string) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
    {
      title: '流入',
      dataIndex: 'inflow_amount',
      width: 90,
      align: 'right' as const,
      sorter: (a: FundFlowIndividualImmediate, b: FundFlowIndividualImmediate) =>
        parseAmountToYi(a.inflow_amount) - parseAmountToYi(b.inflow_amount),
      render: (v: string) => <Text style={{ color: '#ff4d4f' }}>{v}</Text>,
    },
    {
      title: '流出',
      dataIndex: 'outflow_amount',
      width: 90,
      align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#52c41a' }}>{v}</Text>,
    },
    {
      title: '净流入',
      dataIndex: 'net_amount',
      width: 100,
      align: 'right' as const,
      defaultSortOrder: 'descend' as const,
      sorter: (a: FundFlowIndividualImmediate, b: FundFlowIndividualImmediate) =>
        parseAmountToYi(a.net_amount) - parseAmountToYi(b.net_amount),
      render: (v: string) => {
        const n = parseAmountToYi(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 700 }}>
            {n >= 0 ? '+' : ''}{v}
          </Text>
        );
      },
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      width: 90,
      align: 'right' as const,
      render: (v: string) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
  ], [colors]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <Space size="small">
          <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>显示条数</Text>
          <Select
            value={limit}
            onChange={setLimit}
            size="small"
            style={{ width: 80 }}
            options={LIMIT_OPTIONS.map(n => ({ value: n, label: String(n) }))}
          />
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey={(r) => String(r.symbol) + r.serial_number}
          size="small"
          scroll={{ x: 950, y: scrollY }}
          pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
        />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 2: 个股历史排行（3/5/10/20 日）
// ═══════════════════════════════════════════════════════════════════

const IndividualHistoryPanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [data, setData] = useState<FundFlowIndividualHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState<Exclude<FundFlowPeriod, '即时'>>('5日排行');
  const [limit, setLimit] = useState(200);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('fundflow:individualHistory', { period, limit });
    if (!force) {
      const c = readDailyCache<FundFlowIndividualHistory[]>(CK);
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const result = await fundFlowApi.getIndividualHistory(period, limit);
      setData(result || []);
      writeDailyCache(CK, result || []);
      if (!result || result.length === 0) message.warning(`个股${period}数据为空`);
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [period, limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = useMemo(() => [
    {
      title: '#',
      dataIndex: 'serial_number',
      width: 48,
      render: (v: number) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
    {
      title: '代码',
      dataIndex: 'symbol',
      width: 80,
      render: (v: string | number) => (
        <Text style={{ color: '#56A4FF', fontSize: '12px', fontFamily: 'monospace' }}>{fmtSymbol(v)}</Text>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 100,
      render: (v: string) => <Text style={{ color: colors.textPrimary, fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '最新价',
      dataIndex: 'latest_price',
      width: 80,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: colors.textPrimary }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: `阶段涨跌幅（${period}）`,
      dataIndex: 'phase_change',
      width: 140,
      align: 'right' as const,
      sorter: (a: FundFlowIndividualHistory, b: FundFlowIndividualHistory) =>
        parsePct(a.phase_change) - parsePct(b.phase_change),
      render: (v: string) => {
        const n = parsePct(v);
        return <Text style={{ color: pctColor(n), fontWeight: 600 }}>{v}</Text>;
      },
    },
    {
      title: `阶段净流入（${period}）`,
      dataIndex: 'net_amount',
      width: 160,
      align: 'right' as const,
      defaultSortOrder: 'descend' as const,
      sorter: (a: FundFlowIndividualHistory, b: FundFlowIndividualHistory) =>
        parseAmountToYi(a.net_amount) - parseAmountToYi(b.net_amount),
      render: (v: string) => {
        const n = parseAmountToYi(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 700 }}>
            {n >= 0 ? '+' : ''}{v}
          </Text>
        );
      },
    },
    {
      title: '统计日期',
      dataIndex: 'stat_date',
      width: 110,
      align: 'right' as const,
      render: (v: string) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
  ], [colors, period]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <Space size="small">
          <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>周期</Text>
          <Select
            value={period}
            onChange={(v) => setPeriod(v)}
            size="small"
            style={{ width: 110 }}
            options={HISTORY_PERIODS.map(p => ({ value: p, label: p }))}
          />
          <Text style={{ color: colors.textSecondary, fontSize: '12px', marginLeft: 12 }}>显示条数</Text>
          <Select
            value={limit}
            onChange={setLimit}
            size="small"
            style={{ width: 80 }}
            options={LIMIT_OPTIONS.map(n => ({ value: n, label: String(n) }))}
          />
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey={(r) => String(r.symbol) + r.serial_number}
          size="small"
          scroll={{ x: 800, y: scrollY }}
          pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
        />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 3: 行业/概念即时资金流
// ═══════════════════════════════════════════════════════════════════

const ConceptImmediatePanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [data, setData] = useState<FundFlowConceptImmediate[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(100);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('fundflow:conceptImmediate', { limit });
    if (!force) {
      const c = readDailyCache<FundFlowConceptImmediate[]>(CK, { ttlMs: TTL.REALTIME });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const result = await fundFlowApi.getConceptImmediate(limit);
      setData(result || []);
      writeDailyCache(CK, result || []);
      if (!result || result.length === 0) message.warning('行业/概念即时资金流数据为空');
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = useMemo(() => [
    {
      title: '#',
      dataIndex: 'serial_number',
      width: 48,
      render: (v: number) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
    {
      title: '行业/概念',
      dataIndex: 'industry',
      width: 120,
      render: (v: string) => (
        <Tag color="blue" style={{ fontWeight: 500 }}>{v}</Tag>
      ),
    },
    {
      title: '指数点位',
      dataIndex: 'index_price',
      width: 100,
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.textPrimary }}>
          {safeToFixed(v, 2)}
        </Text>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_ratio',
      width: 90,
      align: 'right' as const,
      sorter: (a: FundFlowConceptImmediate, b: FundFlowConceptImmediate) => safeNum(a.change_ratio) - safeNum(b.change_ratio),
      render: (v: number) => (
        <Text style={{ color: pctColor(safeNum(v)), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{safeToFixed(v, 2)}%
        </Text>
      ),
    },
    {
      title: '成份数',
      dataIndex: 'company_count',
      width: 80,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
    {
      title: '流入(亿)',
      dataIndex: 'inflow_amount',
      width: 100,
      align: 'right' as const,
      sorter: (a: FundFlowConceptImmediate, b: FundFlowConceptImmediate) => safeNum(a.inflow_amount) - safeNum(b.inflow_amount),
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: '流出(亿)',
      dataIndex: 'outflow_amount',
      width: 100,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: '净流入(亿)',
      dataIndex: 'net_amount',
      width: 110,
      align: 'right' as const,
      defaultSortOrder: 'descend' as const,
      sorter: (a: FundFlowConceptImmediate, b: FundFlowConceptImmediate) => safeNum(a.net_amount) - safeNum(b.net_amount),
      render: (v: number) => (
        <Text style={{ color: pctColor(safeNum(v)), fontWeight: 700 }}>
          {safeNum(v) >= 0 ? '+' : ''}{safeToFixed(v, 2)}
        </Text>
      ),
    },
    {
      title: '龙头股',
      key: 'leading',
      width: 160,
      render: (_: any, r: FundFlowConceptImmediate) => (
        <Space size={4}>
          <Text style={{ color: colors.textPrimary, fontSize: '12px', fontWeight: 500 }}>
            {r.leading_stock_name}
          </Text>
          <Text style={{ color: pctColor(safeNum(r.leading_stock_change)), fontSize: '11px' }}>
            {safeNum(r.leading_stock_change) >= 0 ? '+' : ''}{safeToFixed(r.leading_stock_change, 2)}%
          </Text>
        </Space>
      ),
    },
    {
      title: '龙头现价',
      dataIndex: 'current_price',
      width: 90,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: colors.textSecondary }}>{safeToFixed(v, 2)}</Text>,
    },
  ], [colors]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <Space size="small">
          <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>显示条数</Text>
          <Select
            value={limit}
            onChange={setLimit}
            size="small"
            style={{ width: 80 }}
            options={LIMIT_OPTIONS.map(n => ({ value: n, label: String(n) }))}
          />
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey={(r) => r.industry + r.serial_number}
          size="small"
          scroll={{ x: 1100, y: scrollY }}
          pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
        />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 4: 行业/概念历史排行
// ═══════════════════════════════════════════════════════════════════

const ConceptHistoryPanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [data, setData] = useState<FundFlowConceptHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState<Exclude<FundFlowPeriod, '即时'>>('5日排行');
  const [limit, setLimit] = useState(100);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('fundflow:conceptHistory', { period, limit });
    if (!force) {
      const c = readDailyCache<FundFlowConceptHistory[]>(CK);
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const result = await fundFlowApi.getConceptHistory(period, limit);
      setData(result || []);
      writeDailyCache(CK, result || []);
      if (!result || result.length === 0) message.warning(`行业/概念${period}数据为空`);
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [period, limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = useMemo(() => [
    {
      title: '#',
      dataIndex: 'serial_number',
      width: 48,
      render: (v: number) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
    {
      title: '行业/概念',
      dataIndex: 'industry',
      width: 140,
      render: (v: string) => <Tag color="purple" style={{ fontWeight: 500 }}>{v}</Tag>,
    },
    {
      title: '成份数',
      dataIndex: 'company_count',
      width: 80,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: colors.textSecondary }}>{v}</Text>,
    },
    {
      title: '指数点位',
      dataIndex: 'index_price',
      width: 100,
      align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: colors.textPrimary }}>
          {safeToFixed(v, 2)}
        </Text>
      ),
    },
    {
      title: `阶段涨跌幅（${period}）`,
      dataIndex: 'phase_change',
      width: 150,
      align: 'right' as const,
      sorter: (a: FundFlowConceptHistory, b: FundFlowConceptHistory) =>
        parsePct(a.phase_change) - parsePct(b.phase_change),
      render: (v: string) => {
        const n = parsePct(v);
        return <Text style={{ color: pctColor(n), fontWeight: 600 }}>{v}</Text>;
      },
    },
    {
      title: '流入(亿)',
      dataIndex: 'inflow_amount',
      width: 100,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: '流出(亿)',
      dataIndex: 'outflow_amount',
      width: 100,
      align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{safeToFixed(v, 2)}</Text>,
    },
    {
      title: `净流入（${period}，亿）`,
      dataIndex: 'net_amount',
      width: 160,
      align: 'right' as const,
      defaultSortOrder: 'descend' as const,
      sorter: (a: FundFlowConceptHistory, b: FundFlowConceptHistory) => safeNum(a.net_amount) - safeNum(b.net_amount),
      render: (v: number) => (
        <Text style={{ color: pctColor(safeNum(v)), fontWeight: 700 }}>
          {safeNum(v) >= 0 ? '+' : ''}{safeToFixed(v, 2)}
        </Text>
      ),
    },
    {
      title: '统计日期',
      dataIndex: 'stat_date',
      width: 110,
      align: 'right' as const,
      render: (v: string) => <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</Text>,
    },
  ], [colors, period]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <Space size="small">
          <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>周期</Text>
          <Select
            value={period}
            onChange={(v) => setPeriod(v)}
            size="small"
            style={{ width: 110 }}
            options={HISTORY_PERIODS.map(p => ({ value: p, label: p }))}
          />
          <Text style={{ color: colors.textSecondary, fontSize: '12px', marginLeft: 12 }}>显示条数</Text>
          <Select
            value={limit}
            onChange={setLimit}
            size="small"
            style={{ width: 80 }}
            options={LIMIT_OPTIONS.map(n => ({ value: n, label: String(n) }))}
          />
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey={(r) => r.industry + r.serial_number}
          size="small"
          scroll={{ x: 1000, y: scrollY }}
          pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }}
        />
      </div>
    </div>
  );
};

export default React.memo(FundFlow);
