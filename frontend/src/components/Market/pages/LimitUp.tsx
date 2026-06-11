/**
 * 涨停池页面 - 独立子分类视图
 *
 * 对接后端接口：
 *   - GET /api/stock/get-stock-zt-pool-em           当日涨停股池
 *   - GET /api/stock/get-stock-zt-pool-previous-em   昨日涨停股池
 *   - GET /api/stock/get-stock-zt-pool-strong-em     强势股池
 *   - GET /api/stock/get-stock-zt-pool-zbgc-em       炸板股池
 *   - GET /api/stock/get-stock-zt-pool-dtgc-em       跌停股池
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Tabs, Table, Tag, Typography, Space, DatePicker, Spin, message, Button } from 'antd';
import {
  FireOutlined,
  ThunderboltOutlined,
  RiseOutlined,
  ExclamationCircleOutlined,
  FallOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Dayjs } from 'dayjs';
import { useTheme } from '@/themes';
import { limitUpApi } from '@/api/stock';
import { safeNum, safeToFixed } from '@/utils/format';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { readDailyCache, writeDailyCache, makeKey, TTL } from '@/utils/dailyCache';
import type { LimitUpPoolItem } from '../../../types/stock';

const { Text, Title } = Typography;

// 表格分页统一配置：使用 defaultPageSize，避免受控 pageSize 未更新导致“切换每页条数无效”
const LIMIT_UP_TABLE_PAGE_SIZE_OPTIONS = ['10', '20', '30', '50', '100', '200'];
const createLimitUpTablePagination = (defaultPageSize = 20) => ({
  defaultPageSize,
  showSizeChanger: true,
  pageSizeOptions: LIMIT_UP_TABLE_PAGE_SIZE_OPTIONS,
  showTotal: (total: number) => `共 ${total} 条`,
});

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

/** 安全格式化数值 */
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

/** 格式化时间为 HH:MM:SS */
const fmtTime = (t: string | null | undefined): string => {
  if (!t || t.length < 6) return '--';
  return `${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}`;
};

/** 格式化日期为 YYYYMMDD */
const fmtDateStr = (d: Dayjs) => d.format('YYYYMMDD');

/** 连板数颜色 Tag */
const limitTimesTag = (count: number | null | undefined) => {
  if (count == null || count <= 0) return null;
  if (count >= 5) return <Tag color="red">{count}连板</Tag>;
  if (count >= 3) return <Tag color="orange">{count}连板</Tag>;
  if (count >= 2) return <Tag color="gold">{count}连板</Tag>;
  return <Tag>{count}连板</Tag>;
};

/** 封板强度 Tag */
const sealTag = (openCount: number | null | undefined) => {
  if (openCount == null) return null;
  if (openCount === 0) return <Tag color="green">硬板</Tag>;
  if (openCount <= 3) return <Tag color="orange">开{openCount}次</Tag>;
  return <Tag color="red">烂板({openCount}次)</Tag>;
};

// ─── Tab 配置 ───────────────────────────────────────────────────

interface TabConfig {
  key: string;
  label: string;
  icon: React.ReactNode;
  apiMethod: (date?: string) => Promise<LimitUpPoolItem[]>;
  color: string;
}

const TAB_CONFIGS: TabConfig[] = [
  { key: 'limit-up', label: '涨停池', icon: <FireOutlined />, apiMethod: limitUpApi.getLimitUpPool, color: '#ff4d4f' },
  { key: 'previous', label: '昨日涨停', icon: <ThunderboltOutlined />, apiMethod: limitUpApi.getPreviousLimitUp, color: '#fa8c16' },
  { key: 'strong', label: '强势股池', icon: <RiseOutlined />, apiMethod: limitUpApi.getStrongPool, color: '#52c41a' },
  { key: 'zbgc', label: '炸板股池', icon: <ExclamationCircleOutlined />, apiMethod: limitUpApi.getZbgcPool, color: '#722ed1' },
  { key: 'dtgc', label: '跌停股池', icon: <FallOutlined />, apiMethod: limitUpApi.getDtgcPool, color: '#52c41a' },
];

// ─── 组件 ───────────────────────────────────────────────────────

const LimitUp: React.FC = () => {
  const { colors } = useTheme();
  // 涨停池表格位于 Tabs 内，需要同时预留 Tabs 头、表头、分页器和底部留白高度
  const { containerRef, scrollY } = useTableScrollY(152);
  const [activeTab, setActiveTab] = useState('limit-up');
  const [dataMap, setDataMap] = useState<Record<string, LimitUpPoolItem[]>>({});
  const [loading, setLoading] = useState(false);
  const [date, setDate] = useState<Dayjs | null>(null);

  // ─── 数据加载 ─────────────────────────────────────────────────

  const currentConfig = TAB_CONFIGS.find(t => t.key === activeTab);

  const loadData = useCallback(async (tabKey: string, queryDate?: string, force = false) => {
    const config = TAB_CONFIGS.find(t => t.key === tabKey);
    if (!config) return;
    const cacheKey = makeKey('limitup:tab', { tab: tabKey, date: queryDate || 'today' });
    // 涨停池是盘中数据，使用短 TTL（5分钟）避免一直拿到首次加载的快照
    if (!force) {
      const cached = readDailyCache<LimitUpPoolItem[]>(cacheKey, { ttlMs: TTL.SHORT });
      if (cached) {
        setDataMap(prev => ({ ...prev, [tabKey]: cached }));
        return;
      }
    }
    setLoading(true);
    try {
      const data = await config.apiMethod(queryDate);
      setDataMap(prev => ({ ...prev, [tabKey]: data }));
      writeDailyCache(cacheKey, data || []);
    } catch (e: any) {
      message.error(`${config.label}加载失败: ` + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!dataMap[activeTab]) {
      const queryDate = date ? fmtDateStr(date) : undefined;
      loadData(activeTab, queryDate);
    }
  }, [activeTab, date, dataMap, loadData]);

  // ─── 通用列定义 ───────────────────────────────────────────────

  const commonColumns = useMemo(() => [
    { title: '序号', dataIndex: 'serial_number', width: 50, align: 'center' as const,
      render: (_v: any, _r: any, idx: number) => idx + 1 },
    { title: '代码', dataIndex: 'symbol', width: 85, fixed: 'left' as const,
      render: (v: string) => <Text style={{ color: colors.textPrimary, fontFamily: 'monospace' }}>{v}</Text> },
    { title: '名称', dataIndex: 'name', width: 90, fixed: 'left' as const,
      render: (v: string) => <Text strong style={{ color: colors.textPrimary }}>{v}</Text> },
    { title: '最新价', dataIndex: 'latest_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '涨跌幅', dataIndex: 'change_percent', width: 80, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtPct(v)}</Text> },
    { title: '成交额', dataIndex: 'amount', width: 95, align: 'right' as const,
      render: (v: number) => fmtYi(v) },
    { title: '换手率', dataIndex: 'turnover_rate', width: 75, align: 'right' as const,
      render: (v: number) => fmtPct(v) },
    { title: '流通市值', dataIndex: 'circulating_market_cap', width: 105, align: 'right' as const,
      render: (v: number) => fmtYi(v) },
    { title: '所属行业', dataIndex: 'industry', width: 85,
      render: (v: string) => <Tag style={{ margin: 0 }}>{v || '--'}</Tag> },
  ], [colors]);

  // ─── 各 Tab 专属列 ────────────────────────────────────────────

  const limitUpColumns = useMemo(() => [
    ...commonColumns,
    { title: '连板', dataIndex: 'limit_times', width: 65, align: 'center' as const,
      render: (v: number) => limitTimesTag(v) },
    { title: '涨停统计', dataIndex: 'limit_statistic', width: 80, align: 'center' as const },
    { title: '封板资金', dataIndex: 'limit_fund', width: 100, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f', fontWeight: 600 }}>{fmtYi(v)}</Text> },
    { title: '封板', dataIndex: 'open_count', width: 65, align: 'center' as const,
      render: (_v: number, r: LimitUpPoolItem) => sealTag(r.open_count) },
    { title: '首次封板', dataIndex: 'first_limit_time', width: 75, align: 'center' as const,
      render: (v: string) => fmtTime(v) },
    { title: '最后封板', dataIndex: 'last_limit_time', width: 75, align: 'center' as const,
      render: (v: string) => fmtTime(v) },
  ], [commonColumns]);

  const previousColumns = useMemo(() => [
    ...commonColumns,
    { title: '昨连板', dataIndex: 'prev_limit_times', width: 65, align: 'center' as const,
      render: (v: number) => limitTimesTag(v) },
    { title: '涨停价', dataIndex: 'limit_up_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '涨速', dataIndex: 'speed', width: 70, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '振幅', dataIndex: 'amplitude', width: 70, align: 'right' as const,
      render: (v: number) => fmtPct(v) },
    { title: '昨封板', dataIndex: 'prev_limit_time', width: 75, align: 'center' as const,
      render: (v: string) => fmtTime(v) },
    { title: '涨停统计', dataIndex: 'limit_statistic', width: 80, align: 'center' as const },
  ], [commonColumns]);

  const strongColumns = useMemo(() => [
    ...commonColumns,
    { title: '涨停统计', dataIndex: 'limit_statistic', width: 80, align: 'center' as const },
    { title: '涨速', dataIndex: 'speed', width: 70, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '量比', dataIndex: 'volume_ratio', width: 70, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '新高', dataIndex: 'is_new_high', width: 60, align: 'center' as const,
      render: (v: string) => v === '是' ? <Tag color="red">新高</Tag> : '--' },
    { title: '入选理由', dataIndex: 'selection_reason', width: 120, ellipsis: true },
  ], [commonColumns]);

  const zbgcColumns = useMemo(() => [
    ...commonColumns,
    { title: '涨停价', dataIndex: 'limit_up_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '涨速', dataIndex: 'speed', width: 70, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '炸板次数', dataIndex: 'open_count', width: 75, align: 'center' as const,
      render: (v: number) => sealTag(v) },
    { title: '振幅', dataIndex: 'amplitude', width: 70, align: 'right' as const,
      render: (v: number) => fmtPct(v) },
    { title: '首次封板', dataIndex: 'first_limit_time', width: 75, align: 'center' as const,
      render: (v: string) => fmtTime(v) },
    { title: '涨停统计', dataIndex: 'limit_statistic', width: 80, align: 'center' as const },
  ], [commonColumns]);

  const dtgcColumns = useMemo(() => [
    ...commonColumns,
    { title: '封板时间', dataIndex: 'last_limit_time', width: 75, align: 'center' as const,
      render: (v: string) => fmtTime(v) },
  ], [commonColumns]);

  const columnMap: Record<string, any[]> = {
    'limit-up': limitUpColumns,
    'previous': previousColumns,
    'strong': strongColumns,
    'zbgc': zbgcColumns,
    'dtgc': dtgcColumns,
  };

  // ─── 统计摘要 ─────────────────────────────────────────────────

  const tabStats = useMemo(() => {
    const list = dataMap[activeTab] || [];
    if (!list.length) return null;
    const upCount = list.filter(r => safeNum(r.change_percent) > 0).length;
    const downCount = list.filter(r => safeNum(r.change_percent) < 0).length;
    const avgChange = list.reduce((s, r) => s + safeNum(r.change_percent), 0) / list.length;
    const totalAmount = list.reduce((s, r) => s + safeNum(r.amount), 0);
    return { total: list.length, upCount, downCount, avgChange, totalAmount };
  }, [dataMap, activeTab]);

  // ─── 渲染 ─────────────────────────────────────────────────────

  const tableProps = {
    size: 'small' as const,
    scroll: { x: 1200, y: scrollY },
    pagination: createLimitUpTablePagination(20),
    style: { fontSize: 13, '--limit-up-scroll-y': `${scrollY}px` } as React.CSSProperties,
    rowKey: (r: any, i?: number) => `${r.symbol}-${r.stat_date || ''}-${i}`,
  };

  return (
    <div className="page-layout limit-up-page" style={{ padding: '0 4px 8px' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexShrink: 0 }}>
        <Space>
          <FireOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>涨停池</Title>
          <Tag color="red" style={{ marginLeft: 8 }}>东方财富</Tag>
        </Space>
      </div>

      {/* 统计摘要 */}
      {tabStats && (
        <div style={{
          display: 'flex', gap: 24, marginBottom: 16, flexShrink: 0,
          padding: '10px 16px', background: colors.bgCard,
          border: `1px solid ${colors.borderColor}`,
          borderRadius: 6, fontSize: 13,
        }}>
          <span>共 <strong style={{ color: colors.textPrimary }}>{tabStats.total}</strong> 只</span>
          <span>上涨 <strong style={{ color: '#ff4d4f' }}>{tabStats.upCount}</strong> 只</span>
          <span>下跌 <strong style={{ color: '#52c41a' }}>{tabStats.downCount}</strong> 只</span>
          <span>平均涨幅 <strong style={{ color: pctColor(tabStats.avgChange) }}>{fmtPct(tabStats.avgChange)}</strong></span>
          <span>总成交额 <strong>{fmtYi(tabStats.totalAmount)}</strong></span>
        </div>
      )}

      {/* 日期选择 + 刷新 */}
      <div style={{ flexShrink: 0 }}>
        <Space style={{ marginBottom: 12 }}>
          <DatePicker
          value={date}
          onChange={(v) => {
            setDate(v);
            setDataMap({}); // 清空缓存，触发重新加载
          }}
          placeholder="选择日期(默认当天)"
          format="YYYY-MM-DD"
          size="small"
          style={{ width: 180 }}
          allowClear
        />
        <Button
          type="primary"
          size="small"
          ghost
          icon={<ReloadOutlined />}
          onClick={() => {
            setDataMap(prev => {
              const next = { ...prev };
              delete next[activeTab];
              return next;
            });
            const queryDate = date ? fmtDateStr(date) : undefined;
            loadData(activeTab, queryDate, true);
          }}
        >
          刷新
        </Button>
      </Space>
      </div>

      {/* Tab 切换 */}
      <div ref={containerRef} className="flex-content limit-up-table-box">
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key)}
          size="small"
          type="card"
          style={{ height: '100%' }}
          items={TAB_CONFIGS.map(config => ({
            key: config.key,
            label: (
              <span>
                <span style={{ color: config.color }}>{config.icon}</span>
                {' '}{config.label}
              </span>
            ),
            children: (
              <div className="table-wrapper">
                <Spin spinning={loading && !dataMap[activeTab]} style={{ height: '100%' }}>
                  <Table
                    {...tableProps}
                    className="limit-up-table"
                    columns={columnMap[config.key]}
                    dataSource={dataMap[config.key] || []}
                  />
                </Spin>
              </div>
            ),
          }))}
        />
      </div>
    </div>
  );
};

export default React.memo(LimitUp);