/**
 * 融资融券页面 - 市场概览子页面
 *
 * 对接后端接口：
 *   GET /api/stock/get-stock-margin-account-info       两融账户信息（无入参，全市场逐日时间序列）
 *   GET /api/stock/get-stock-margin-sse                上交所融资融券汇总（按 start_date/end_date）
 *   GET /api/stock/get-stock-margin-detail-szse        深交所融资融券明细（按交易日）
 *   GET /api/stock/get-stock-margin-detail-sse         上交所融资融券明细（按交易日）
 *
 * Tab 布局（参考 DragonTiger 模式）：
 *   - 唯一的 containerRef 放在主组件，所有 Tab 共享 scrollY
 *   - 顶部对比卡放在主组件层级，仅 account Tab 显示
 *   - 各 Tab 内部直接渲染 filter + Table，不再嵌套独立的 flex 容器
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Tabs, Table, Typography, Space, DatePicker, Spin, message,
  Row, Col, Card, Statistic, Button, Input, Tag,
} from 'antd';
import {
  BankOutlined, ReloadOutlined, SearchOutlined,
  AccountBookOutlined, LineChartOutlined, FileTextOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useTheme } from '@/themes';
import { marginApi } from '@/api/stock';
import { safeNum } from '@/utils/format';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { readDailyCache, writeDailyCache, makeKey, TTL } from '@/utils/dailyCache';
import { getDefaultTradingDate, getPrevTradingDay, isTradingDay } from '@/utils/tradingDate';
import type {
  MarginAccountInfo,
  MarginSseSummary,
  MarginDetailSzse,
  MarginDetailSse,
} from '../../../types/stock';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;

// ─── 工具函数 ───────────────────────────────────────────────────

/** 格式化为 YYYYMMDD */
const fmtDate = (d: Dayjs) => d.format('YYYYMMDD');

/** 单位换算：元 → 亿元 */
const yuanToYi = (v: number | string | null | undefined): string => {
  const n = safeNum(v, NaN);
  if (isNaN(n)) return '--';
  return (n / 1e8).toFixed(2) + '亿';
};

/** 万股/万手 展示（来自明细接口的股数） */
const showWan = (v: number | string | null | undefined): string => {
  const n = safeNum(v, NaN);
  if (isNaN(n)) return '--';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万';
  return n.toFixed(0);
};

/** 安全 toFixed */
const showFixed = (v: number | string | null | undefined, digits = 2): string => {
  const n = safeNum(v, NaN);
  if (isNaN(n)) return '--';
  return n.toFixed(digits);
};

/** 涨跌色（红涨绿跌） */
const deltaColor = (cur: number, prev: number): string => {
  if (cur > prev) return '#ff4d4f';
  if (cur < prev) return '#52c41a';
  return '#999';
};

// ─── 主组件 ─────────────────────────────────────────────────────

const MarginTrade: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState<string>('account');

  // ─── 状态：4 个 Panel 的数据集中放在主组件，统一管理高度 ───

  // Panel 1: 两融账户
  const [accountData, setAccountData] = useState<MarginAccountInfo[]>([]);
  const [accountLoading, setAccountLoading] = useState(false);

  // Panel 2: 上交所汇总
  //   - end 取默认交易日；start 取 end 之前的"30 个工作日近似"（再用 getPrevTradingDay 兜底为工作日）
  //   - 后端要求 start_date 和 end_date 都必须是交易日，否则 422
  const [sseSumDateRange, setSseSumDateRange] = useState<[Dayjs, Dayjs]>(() => {
    const end = getDefaultTradingDate();
    // 起点：往前数 ~42 天（保守覆盖 30 个交易日 + 节假日缓冲），再确保是工作日
    let start = end.subtract(42, 'day');
    if (!isTradingDay(start)) start = getPrevTradingDay(start.add(1, 'day'));
    return [start, end];
  });
  const [sseSumData, setSseSumData] = useState<MarginSseSummary[]>([]);
  const [sseSumLoading, setSseSumLoading] = useState(false);

  // Panel 3: 深交所明细
  const [szseDate, setSzseDate] = useState<Dayjs>(() => getPrevTradingDay(dayjs()));
  const [szseRaw, setSzseRaw] = useState<MarginDetailSzse[]>([]);
  const [szseLoading, setSzseLoading] = useState(false);
  const [szseSearch, setSzseSearch] = useState('');

  // Panel 4: 上交所明细
  const [sseDate, setSseDate] = useState<Dayjs>(() => getPrevTradingDay(dayjs()));
  const [sseRaw, setSseRaw] = useState<MarginDetailSse[]>([]);
  const [sseLoading, setSseLoading] = useState(false);
  const [sseSearch, setSseSearch] = useState('');

  // ─── 数据加载 ─────────────────────────────────────────────────

  const loadAccount = useCallback(async (force = false) => {
    const CK = 'margin:account';
    if (!force) {
      const c = readDailyCache<MarginAccountInfo[]>(CK, { ttlMs: TTL.MEDIUM });
      if (c) { setAccountData(c); return; }
    }
    setAccountLoading(true);
    try {
      const result = await marginApi.getAccountInfo();
      const sorted = (result || []).slice().sort((a, b) =>
        String(b.trade_date).localeCompare(String(a.trade_date)));
      setAccountData(sorted);
      writeDailyCache(CK, sorted);
      if (!sorted.length) message.warning('两融账户数据为空');
    } catch (e: any) {
      message.error('两融账户加载失败: ' + (e.message || '未知'));
    } finally {
      setAccountLoading(false);
    }
  }, []);

  const loadSseSum = useCallback(async (force = false) => {
    // 任何非交易日入参都会被后端 422 拒绝（"YYYYMMDD 不是交易日"），
    // 这里在请求前自动把起止日 snap 到最近的交易日（向前回退）。
    const startSafe = isTradingDay(sseSumDateRange[0])
      ? sseSumDateRange[0]
      : getPrevTradingDay(sseSumDateRange[0].add(1, 'day'));
    const endSafe = isTradingDay(sseSumDateRange[1])
      ? sseSumDateRange[1]
      : getPrevTradingDay(sseSumDateRange[1].add(1, 'day'));
    const startStr = fmtDate(startSafe);
    const endStr = fmtDate(endSafe);

    const CK = makeKey('margin:sseSummary', { start: startStr, end: endStr });
    if (!force) {
      const c = readDailyCache<MarginSseSummary[]>(CK);
      if (c) { setSseSumData(c); return; }
    }
    setSseSumLoading(true);
    try {
      const result = await marginApi.getSseSummary(startStr, endStr);
      const sorted = (result || []).slice().sort((a, b) =>
        String(b.trade_date).localeCompare(String(a.trade_date)));
      setSseSumData(sorted);
      writeDailyCache(CK, sorted);
      if (!sorted.length) message.warning('该区间无数据');
    } catch (e: any) {
      // http 拦截器已把后端 422 的 message（例如 "20240901 不是交易日"）提取到 e.message
      message.error('上交所融资融券汇总加载失败: ' + (e.message || '未知'));
    } finally {
      setSseSumLoading(false);
    }
  }, [sseSumDateRange]);

  const loadSzse = useCallback(async (force = false) => {
    // 非交易日 → snap 到上一个交易日
    const dateSafe = isTradingDay(szseDate) ? szseDate : getPrevTradingDay(szseDate.add(1, 'day'));
    const dateStr = fmtDate(dateSafe);
    const CK = makeKey('margin:szseDetail', { date: dateStr });
    if (!force) {
      const c = readDailyCache<MarginDetailSzse[]>(CK);
      if (c) { setSzseRaw(c); return; }
    }
    setSzseLoading(true);
    try {
      const result = await marginApi.getDetailSzse(dateStr);
      setSzseRaw(result || []);
      writeDailyCache(CK, result || []);
      if (!result || !result.length) message.warning('该交易日无数据');
    } catch (e: any) {
      message.error('深交所融资融券明细加载失败: ' + (e.message || '未知'));
    } finally {
      setSzseLoading(false);
    }
  }, [szseDate]);

  const loadSse = useCallback(async (force = false) => {
    const dateSafe = isTradingDay(sseDate) ? sseDate : getPrevTradingDay(sseDate.add(1, 'day'));
    const dateStr = fmtDate(dateSafe);
    const CK = makeKey('margin:sseDetail', { date: dateStr });
    if (!force) {
      const c = readDailyCache<MarginDetailSse[]>(CK);
      if (c) { setSseRaw(c); return; }
    }
    setSseLoading(true);
    try {
      const result = await marginApi.getDetailSse(dateStr);
      setSseRaw(result || []);
      writeDailyCache(CK, result || []);
      if (!result || !result.length) message.warning('该交易日无数据');
    } catch (e: any) {
      message.error('上交所融资融券明细加载失败: ' + (e.message || '未知'));
    } finally {
      setSseLoading(false);
    }
  }, [sseDate]);

  // Tab 切换自动加载
  useEffect(() => {
    switch (activeTab) {
      case 'account': loadAccount(); break;
      case 'sse-summary': loadSseSum(); break;
      case 'szse-detail': loadSzse(); break;
      case 'sse-detail': loadSse(); break;
    }
  }, [activeTab, loadAccount, loadSseSum, loadSzse, loadSse]);

  const handleRefresh = useCallback(() => {
    switch (activeTab) {
      case 'account': loadAccount(true); break;
      case 'sse-summary': loadSseSum(true); break;
      case 'szse-detail': loadSzse(true); break;
      case 'sse-detail': loadSse(true); break;
    }
  }, [activeTab, loadAccount, loadSseSum, loadSzse, loadSse]);

  // ─── 客户端过滤 ───────────────────────────────────────────────

  const szseData = useMemo(() => {
    if (!szseSearch.trim()) return szseRaw;
    const kw = szseSearch.trim().toLowerCase();
    return szseRaw.filter(r =>
      String(r['证券代码'] || '').toLowerCase().includes(kw) ||
      String(r['证券简称'] || '').toLowerCase().includes(kw)
    );
  }, [szseRaw, szseSearch]);

  const sseData = useMemo(() => {
    if (!sseSearch.trim()) return sseRaw;
    const kw = sseSearch.trim().toLowerCase();
    return sseRaw.filter(r =>
      String(r['标的证券代码'] || '').toLowerCase().includes(kw) ||
      String(r['标的证券简称'] || '').toLowerCase().includes(kw)
    );
  }, [sseRaw, sseSearch]);

  // ─── 两融账户对比卡 ───────────────────────────────────────────

  const accountSummary = useMemo(() => {
    if (accountData.length < 2) return null;
    const cur = accountData[0];
    const prev = accountData[1];
    return {
      cur, prev,
      mb: safeNum(cur.margin_balance),
      pmb: safeNum(prev.margin_balance),
      sb: safeNum(cur.short_balance),
      psb: safeNum(prev.short_balance),
      cv: safeNum(cur.collateral_value),
      pcv: safeNum(prev.collateral_value),
    };
  }, [accountData]);

  // ─── 表格列定义 ───────────────────────────────────────────────

  const accountColumns = useMemo(() => [
    { title: '信用交易日', dataIndex: 'trade_date', width: 110, fixed: 'left' as const,
      render: (v: string) => <Text style={{ color: colors.textPrimary, fontWeight: 600 }}>{v}</Text> },
    { title: '融资余额(亿)', dataIndex: 'margin_balance', width: 110, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#ff4d4f' }}>{showFixed(v)}</Text>,
      sorter: (a: MarginAccountInfo, b: MarginAccountInfo) => safeNum(a.margin_balance) - safeNum(b.margin_balance) },
    { title: '融券余额(亿)', dataIndex: 'short_balance', width: 110, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#52c41a' }}>{showFixed(v)}</Text> },
    { title: '融资买入额(亿)', dataIndex: 'margin_buy_amount', width: 120, align: 'right' as const,
      render: (v: string) => showFixed(v) },
    { title: '融券卖出额(亿)', dataIndex: 'short_sell_amount', width: 120, align: 'right' as const,
      render: (v: string) => showFixed(v) },
    { title: '担保物总值(亿)', dataIndex: 'collateral_value', width: 120, align: 'right' as const,
      render: (v: string) => showFixed(v) },
    { title: '维持担保比例(%)', dataIndex: 'avg_maintenance_ratio', width: 130, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#56A4FF', fontWeight: 600 }}>{showFixed(v)}</Text> },
    { title: '证券公司数', dataIndex: 'securities_company_count', width: 95, align: 'center' as const },
    { title: '营业部数', dataIndex: 'branch_office_count', width: 90, align: 'center' as const },
    { title: '个人投资者(万户)', dataIndex: 'individual_investor_count', width: 130, align: 'right' as const,
      render: (v: string) => showFixed(v, 2) },
    { title: '机构投资者(户)', dataIndex: 'institution_investor_count', width: 130, align: 'right' as const,
      render: (v: string) => showFixed(v, 0) },
    { title: '参与交易投资者(户)', dataIndex: 'active_trader_count', width: 150, align: 'right' as const,
      render: (v: string) => showFixed(v, 0) },
    { title: '有负债投资者(户)', dataIndex: 'liability_investor_count', width: 145, align: 'right' as const,
      render: (v: string) => showFixed(v, 0) },
  ], [colors]);

  const sseSumColumns = useMemo(() => [
    { title: '信用交易日', dataIndex: 'trade_date', width: 110, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '融资余额', dataIndex: 'margin_balance', width: 130, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{yuanToYi(v)}</Text>,
      sorter: (a: MarginSseSummary, b: MarginSseSummary) => safeNum(a.margin_balance) - safeNum(b.margin_balance) },
    { title: '融资买入额', dataIndex: 'margin_buy_amount', width: 130, align: 'right' as const,
      render: (v: number) => yuanToYi(v) },
    { title: '融券余额', dataIndex: 'short_balance', width: 130, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{yuanToYi(v)}</Text> },
    { title: '融券余量(股)', dataIndex: 'short_volume', width: 130, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融券卖出量(股)', dataIndex: 'short_sell_volume', width: 140, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融资融券余额合计', dataIndex: 'margin_short_balance', width: 150, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#56A4FF', fontWeight: 600 }}>{yuanToYi(v)}</Text> },
  ], []);

  const szseColumns = useMemo(() => [
    { title: '证券代码', dataIndex: '证券代码', width: 90, fixed: 'left' as const,
      render: (v: string) => <Text style={{ color: '#56A4FF', fontFamily: 'monospace' }}>{v}</Text> },
    { title: '证券简称', dataIndex: '证券简称', width: 110, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '融资买入额', dataIndex: '融资买入额', width: 130, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{yuanToYi(v)}</Text>,
      sorter: (a: MarginDetailSzse, b: MarginDetailSzse) => safeNum(a['融资买入额']) - safeNum(b['融资买入额']) },
    { title: '融资余额', dataIndex: '融资余额', width: 130, align: 'right' as const,
      render: (v: number) => yuanToYi(v),
      sorter: (a: MarginDetailSzse, b: MarginDetailSzse) => safeNum(a['融资余额']) - safeNum(b['融资余额']),
      defaultSortOrder: 'descend' as const },
    { title: '融券卖出量(股)', dataIndex: '融券卖出量', width: 130, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融券余量(股)', dataIndex: '融券余量', width: 130, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融券余额', dataIndex: '融券余额', width: 130, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{yuanToYi(v)}</Text> },
    { title: '融资融券余额合计', dataIndex: '融资融券余额', width: 150, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#56A4FF', fontWeight: 600 }}>{yuanToYi(v)}</Text>,
      sorter: (a: MarginDetailSzse, b: MarginDetailSzse) => safeNum(a['融资融券余额']) - safeNum(b['融资融券余额']) },
  ], []);

  const sseDetailColumns = useMemo(() => [
    { title: '信用交易日', dataIndex: '信用交易日期', width: 110, fixed: 'left' as const },
    { title: '证券代码', dataIndex: '标的证券代码', width: 90, fixed: 'left' as const,
      render: (v: string) => <Text style={{ color: '#56A4FF', fontFamily: 'monospace' }}>{v}</Text> },
    { title: '证券简称', dataIndex: '标的证券简称', width: 110, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '融资余额', dataIndex: '融资余额', width: 130, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{yuanToYi(v)}</Text>,
      sorter: (a: MarginDetailSse, b: MarginDetailSse) => safeNum(a['融资余额']) - safeNum(b['融资余额']),
      defaultSortOrder: 'descend' as const },
    { title: '融资买入额', dataIndex: '融资买入额', width: 130, align: 'right' as const,
      render: (v: number) => yuanToYi(v) },
    { title: '融资偿还额', dataIndex: '融资偿还额', width: 130, align: 'right' as const,
      render: (v: number) => yuanToYi(v) },
    { title: '融券余量(股)', dataIndex: '融券余量', width: 130, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融券卖出量(股)', dataIndex: '融券卖出量', width: 140, align: 'right' as const,
      render: (v: number) => showWan(v) },
    { title: '融券偿还量(股)', dataIndex: '融券偿还量', width: 140, align: 'right' as const,
      render: (v: number) => showWan(v) },
  ], []);

  // ─── 过滤条 ───────────────────────────────────────────────────

  const renderFilter = () => {
    if (activeTab === 'account') {
      return (
        <Space style={{ marginBottom: 8 }}>
          <Button type="primary" size="small" ghost icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          {accountData.length > 0 && (
            <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
              数据范围：{accountData[accountData.length - 1].trade_date} ~ {accountData[0].trade_date}（共 {accountData.length} 个交易日）
            </Text>
          )}
        </Space>
      );
    }
    if (activeTab === 'sse-summary') {
      return (
        <Space style={{ marginBottom: 8 }}>
          <RangePicker
            value={sseSumDateRange}
            onChange={(v) => { if (v && v[0] && v[1]) setSseSumDateRange([v[0], v[1]]); }}
            disabledDate={(d) => !!d && (!isTradingDay(d) || d.isAfter(dayjs(), 'day'))}
            format="YYYY-MM-DD"
            size="small"
            style={{ width: 260 }}
          />
          <Button type="primary" size="small" ghost icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
            注：周末/节假日已自动屏蔽
          </Text>
        </Space>
      );
    }
    if (activeTab === 'szse-detail') {
      return (
        <Space style={{ marginBottom: 8 }}>
          <DatePicker value={szseDate} onChange={(v) => { if (v) setSzseDate(v); }}
            disabledDate={(d) => !!d && (!isTradingDay(d) || d.isAfter(dayjs(), 'day'))}
            format="YYYY-MM-DD" size="small" style={{ width: 140 }} />
          <Input allowClear size="small" prefix={<SearchOutlined />}
            placeholder="搜索证券代码/简称" style={{ width: 200 }}
            value={szseSearch} onChange={(e) => setSzseSearch(e.target.value)} />
          <Button type="primary" size="small" ghost icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
            共 {szseRaw.length} 条，过滤后 {szseData.length} 条
          </Text>
        </Space>
      );
    }
    if (activeTab === 'sse-detail') {
      return (
        <Space style={{ marginBottom: 8 }}>
          <DatePicker value={sseDate} onChange={(v) => { if (v) setSseDate(v); }}
            disabledDate={(d) => !!d && (!isTradingDay(d) || d.isAfter(dayjs(), 'day'))}
            format="YYYY-MM-DD" size="small" style={{ width: 140 }} />
          <Input allowClear size="small" prefix={<SearchOutlined />}
            placeholder="搜索证券代码/简称" style={{ width: 200 }}
            value={sseSearch} onChange={(e) => setSseSearch(e.target.value)} />
          <Button type="primary" size="small" ghost icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
            共 {sseRaw.length} 条，过滤后 {sseData.length} 条
          </Text>
        </Space>
      );
    }
    return null;
  };

  // ─── 共享 scrollY（与龙虎榜同款） ────────────────────────────
  // 预留：底部分页器(~56) + 过滤条(~36) + Tab 头部(~40) + 余量(~28) = ~160px
  const { containerRef, scrollY } = useTableScrollY(160);

  const commonPagination = {
    pageSize: 30,
    showSizeChanger: true,
    placement: ['bottomEnd'] as ('bottomEnd')[],
    size: 'small' as const,
    showTotal: (t: number) => `共 ${t} 条`,
  };

  const tableProps = {
    size: 'small' as const,
    scroll: { x: 1200, y: scrollY },
    pagination: commonPagination,
    style: { fontSize: 12 },
  };

  return (
    <div className="margin-trade-page" style={{ padding: '0 4px', height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexShrink: 0 }}>
        <Space>
          <BankOutlined style={{ fontSize: 18, color: '#56A4FF' }} />
          <Title level={5} style={{ margin: 0, color: colors.textPrimary }}>融资融券</Title>
          <Tag color="blue" style={{ marginLeft: 4 }}>东方财富 / 沪深交易所</Tag>
        </Space>
      </div>

      {/* 顶部概览（仅两融账户Tab显示） */}
      {activeTab === 'account' && accountSummary && (
        <Row gutter={8} style={{ marginBottom: 8, flexShrink: 0 }}>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }} styles={{ body: { padding: '6px 10px' } }}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>{`融资余额（${accountSummary.cur.trade_date}）`}</span>}
                value={accountSummary.mb}
                precision={2}
                suffix="亿"
                styles={{ content: { color: deltaColor(accountSummary.mb, accountSummary.pmb), fontSize: 16, lineHeight: 1.2 } }}
              />
              <Text style={{ fontSize: 10, color: colors.textTertiary }}>
                环比：{(accountSummary.mb - accountSummary.pmb >= 0 ? '+' : '')}{(accountSummary.mb - accountSummary.pmb).toFixed(2)} 亿
              </Text>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }} styles={{ body: { padding: '6px 10px' } }}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>融券余额</span>}
                value={accountSummary.sb}
                precision={2}
                suffix="亿"
                styles={{ content: { color: deltaColor(accountSummary.sb, accountSummary.psb), fontSize: 16, lineHeight: 1.2 } }}
              />
              <Text style={{ fontSize: 10, color: colors.textTertiary }}>
                环比：{(accountSummary.sb - accountSummary.psb >= 0 ? '+' : '')}{(accountSummary.sb - accountSummary.psb).toFixed(2)} 亿
              </Text>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }} styles={{ body: { padding: '6px 10px' } }}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>担保物总值</span>}
                value={accountSummary.cv}
                precision={2}
                suffix="亿"
                styles={{ content: { color: deltaColor(accountSummary.cv, accountSummary.pcv), fontSize: 16, lineHeight: 1.2 } }}
              />
              <Text style={{ fontSize: 10, color: colors.textTertiary }}>
                环比：{(accountSummary.cv - accountSummary.pcv >= 0 ? '+' : '')}{(accountSummary.cv - accountSummary.pcv).toFixed(2)} 亿
              </Text>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }} styles={{ body: { padding: '6px 10px' } }}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>平均维持担保比例</span>}
                value={safeNum(accountSummary.cur.avg_maintenance_ratio)}
                precision={2}
                suffix="%"
                styles={{ content: { color: '#56A4FF', fontSize: 16, lineHeight: 1.2 } }}
              />
              <Text style={{ fontSize: 10, color: colors.textTertiary }}>
                上期：{showFixed(accountSummary.prev.avg_maintenance_ratio)}%
              </Text>
            </Card>
          </Col>
        </Row>
      )}

      {/* Tab 切换（containerRef 包裹整个 Tabs，由其测量高度） */}
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="small"
          type="card"
          style={{ height: '100%' }}
          items={[
            {
              key: 'account',
              label: <span><AccountBookOutlined /> 两融账户</span>,
              children: (
                <div className="margin-trade-tab-pane">
                  <Spin spinning={accountLoading}>
                    {renderFilter()}
                    <Table
                      {...tableProps}
                      rowKey={(r) => String(r.id ?? r.trade_date)}
                      columns={accountColumns}
                      dataSource={accountData}
                      scroll={{ x: 1500, y: scrollY }}
                      pagination={{ ...commonPagination, showTotal: (t) => `共 ${t} 个交易日` }}
                    />
                  </Spin>
                </div>
              ),
            },
            {
              key: 'sse-summary',
              label: <span><LineChartOutlined /> 上交所汇总</span>,
              children: (
                <div className="margin-trade-tab-pane">
                  <Spin spinning={sseSumLoading}>
                    {renderFilter()}
                    <Table
                      {...tableProps}
                      rowKey="trade_date"
                      columns={sseSumColumns}
                      dataSource={sseSumData}
                      scroll={{ x: 1000, y: scrollY }}
                      pagination={{ ...commonPagination, showTotal: (t) => `共 ${t} 个交易日` }}
                    />
                  </Spin>
                </div>
              ),
            },
            {
              key: 'szse-detail',
              label: <span><FileTextOutlined /> 深交所明细</span>,
              children: (
                <div className="margin-trade-tab-pane">
                  <Spin spinning={szseLoading}>
                    {renderFilter()}
                    <Table
                      {...tableProps}
                      rowKey={(r) => String(r['证券代码'])}
                      columns={szseColumns}
                      dataSource={szseData}
                      scroll={{ x: 1100, y: scrollY }}
                      pagination={{ ...commonPagination, pageSize: 50 }}
                    />
                  </Spin>
                </div>
              ),
            },
            {
              key: 'sse-detail',
              label: <span><FileTextOutlined /> 上交所明细</span>,
              children: (
                <div className="margin-trade-tab-pane">
                  <Spin spinning={sseLoading}>
                    {renderFilter()}
                    <Table
                      {...tableProps}
                      rowKey={(r) => String(r['标的证券代码'])}
                      columns={sseDetailColumns}
                      dataSource={sseData}
                      scroll={{ x: 1200, y: scrollY }}
                      pagination={{ ...commonPagination, pageSize: 50 }}
                    />
                  </Spin>
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default React.memo(MarginTrade);
