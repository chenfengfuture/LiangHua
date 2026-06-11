/**
 * 总览仪表盘页面 - 市场概览默认子页面
 *
 * 数据来源：
 *   - GET /api/stock/get-stock-market-fund-flow        大盘行情（指数+资金流向）
 *   - GET /api/stock/get_stock_changes_em              盘口异动
 *   - GET /api/stock/get-stock-board                   行业一览（热力图）
 *   - GET /api/stock/get-stock-fund-flow-individual    个股资金流（主力TOP）
 *   - GET /api/stock/get-stock-zt-pool-em              涨停股池（连板+涨停数）
 *   - GET /api/stock/get-stock-zt-pool-dtgc-em         跌停股池（跌停数）
 *   - GET /api/stock/get-stock-lhb-detail              龙虎榜详情
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Row, Col, Tabs, Table, Typography, Space, Button, Spin, message, Modal } from 'antd';
import { ReloadOutlined, DownloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useTheme } from '@/themes';
import dayjs from 'dayjs';
import { getDefaultTradingDate, getPrevTradingDay, isTradingDay } from '@/utils/tradingDate';
import { marketApi, limitUpApi, sectorApi, fundFlowApi, dragonTigerApi } from '@/api/stock';
import { safeNum, safeToFixed } from '@/utils/format';
import { readDailyCache, writeDailyCache, clearDailyCache, purgeExpiredDailyCache } from '@/utils/dailyCache';
import type {
  MarketFundFlow,
  StockChangeItem,
  IndustryBoardSummary,
  FundFlowIndividualImmediate,
  LimitUpPoolItem,
  LhbDetail,
} from '../../../types/stock';

const { Text } = Typography;

// ─── 工具函数 ───────────────────────────────────────────────────

const fmtYi = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(2);
};

const fmtYiRaw = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '0.00';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2);
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2);
  return v.toFixed(2);
};

const pctColor = (v: number | null | undefined): string => {
  if (v == null || isNaN(v) || v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

/** 解析金额字符串 "1150.70万" → number（单位亿） */
const parseAmountToYi = (v: string | number | null | undefined): number => {
  if (v == null) return 0;
  if (typeof v === 'number') return v;
  const s = v.trim();
  if (s.endsWith('亿')) return parseFloat(s) * 1e8;
  if (s.endsWith('万')) return parseFloat(s) * 1e4;
  return parseFloat(s) || 0;
};

/** 盘口异动百分比是小数(0.046681=4.67%)，转显示用百分比数字 */
const parseChangePct = (v: any): number => {
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (isNaN(n)) return 0;
  // stock_changes returns decimal (0.0466 = 4.66%), fund_flow returns already-percentage
  // heuristic: if |v| < 1 and it's from stock_changes endpoint, multiply by 100
  return Math.abs(n) < 1 ? n * 100 : n;
};

/** 获取涨停池中最高连板数 */
const getMaxLimitTimes = (list: LimitUpPoolItem[]): number => {
  return list.reduce((max, r) => Math.max(max, r.limit_times || 0), 0);
};

/** 按连板数分组统计 */
const groupByLimitTimes = (list: LimitUpPoolItem[]): { times: number; count: number; items: LimitUpPoolItem[] }[] => {
  const map = new Map<number, LimitUpPoolItem[]>();
  for (const item of list) {
    const t = item.limit_times || 0;
    if (!map.has(t)) map.set(t, []);
    map.get(t)!.push(item);
  }
  return Array.from(map.entries())
    .filter(([t]) => t > 0)
    .sort(([a], [b]) => b - a)
    .map(([times, items]) => ({ times, count: items.length, items }));
};

// ─── Tab 配置 ──
const marketChangeTabs = [
  { key: 'rocket', label: '🚀 火箭发射' },
  { key: 'rebound', label: '快速反弹' },
  { key: 'bigbuy', label: '大笔买入' },
  { key: 'limitup', label: '封涨停板' },
];

const heatmapTabs = [
  { key: 'industry', label: '行业' },
];

// ─── 组件 ───────────────────────────────────────────────────────

const Dashboard: React.FC = () => {
  const { colors } = useTheme();

  // ── 各板块数据状态 ──
  const [marketFundFlow, setMarketFundFlow] = useState<MarketFundFlow[]>([]);
  const [ztPool, setZtPool] = useState<LimitUpPoolItem[]>([]);
  const [dtPool, setDtPool] = useState<LimitUpPoolItem[]>([]);
  const [rocketChanges, setRocketChanges] = useState<StockChangeItem[]>([]);
  const [reboundChanges, setReboundChanges] = useState<StockChangeItem[]>([]);
  const [bigBuyChanges, setBigBuyChanges] = useState<StockChangeItem[]>([]);
  const [limitUpChanges, setLimitUpChanges] = useState<StockChangeItem[]>([]);
  const [industryList, setIndustryList] = useState<IndustryBoardSummary[]>([]);
  const [fundTop10, setFundTop10] = useState<FundFlowIndividualImmediate[]>([]);
  const [lhbDetail, setLhbDetail] = useState<LhbDetail[]>([]);

  const [loading, setLoading] = useState(false);
  const [activeChangeTab, setActiveChangeTab] = useState<string>('rocket');
  const [heatmapTab, setHeatmapTab] = useState<string>('industry');
  const [queryDateStr, setQueryDateStr] = useState<string>(''); // 当前查询的交易日
  const [syncing, setSyncing] = useState(false); // 全量同步中
  const [ztPoolModalVisible, setZtPoolModalVisible] = useState(false);
  const [industryDetailVisible, setIndustryDetailVisible] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState<IndustryBoardSummary | null>(null);
  const didInitRef = useRef(false);
  const loadingRef = useRef(false);

  // ── 加载所有数据 ──
  const loadAll = useCallback(async (force = false) => {
    if (loadingRef.current) return; // 防止并发重复请求

    // 判断交易日：若非交易日则自动取上一个交易日
    const tradingDate = getDefaultTradingDate();
    const today = tradingDate.format('YYYYMMDD');
    const yesterday = getPrevTradingDay(tradingDate).format('YYYYMMDD');
    setQueryDateStr(tradingDate.format('YYYY-MM-DD'));

    const CACHE_PREFIX = `dashboard:${today}`;

    // 1) 逐个读取当日缓存（拆分为独立小 key，避免单 key 超 localStorage 配额）
    if (!force) {
      const cachedFundFlow = readDailyCache<MarketFundFlowItem[]>(`${CACHE_PREFIX}:fundFlow`);
      const cachedZt = readDailyCache<LimitUpPoolItem[]>(`${CACHE_PREFIX}:zt`);
      const cachedDt = readDailyCache<LimitUpPoolItem[]>(`${CACHE_PREFIX}:dt`);
      const cachedRocket = readDailyCache<StockChangeItem[]>(`${CACHE_PREFIX}:rocket`);
      const cachedRebound = readDailyCache<StockChangeItem[]>(`${CACHE_PREFIX}:rebound`);
      const cachedBigBuy = readDailyCache<StockChangeItem[]>(`${CACHE_PREFIX}:bigBuy`);
      const cachedLimitup = readDailyCache<StockChangeItem[]>(`${CACHE_PREFIX}:limitup`);
      const cachedIndustry = readDailyCache<IndustryBoardSummary[]>(`${CACHE_PREFIX}:industry`);
      const cachedFundTop = readDailyCache<FundFlowIndividualImmediate[]>(`${CACHE_PREFIX}:fundTop`);
      const cachedLhb = readDailyCache<LhbDetail[]>(`${CACHE_PREFIX}:lhb`);

      if (cachedFundFlow && cachedZt && cachedDt && cachedRocket && cachedRebound &&
          cachedBigBuy && cachedLimitup && cachedIndustry && cachedFundTop && cachedLhb) {
        setMarketFundFlow(cachedFundFlow);
        setZtPool(cachedZt);
        setDtPool(cachedDt);
        setRocketChanges(cachedRocket);
        setReboundChanges(cachedRebound);
        setBigBuyChanges(cachedBigBuy);
        setLimitUpChanges(cachedLimitup);
        setIndustryList(cachedIndustry);
        setFundTop10(cachedFundTop);
        setLhbDetail(cachedLhb);
        return;
      }
    }

    loadingRef.current = true;
    setLoading(true);
    try {
      const [
        fundFlow,
        zt,
        dt,
        rocket,
        rebound,
        bigBuy,
        limitup,
        industry,
        fundTop,
        lhb,
      ] = await Promise.all([
        marketApi.getMarketFundFlow(),
        limitUpApi.getLimitUpPool(today),
        limitUpApi.getDtgcPool(today),
        sectorApi.getStockChanges('火箭发射'),
        sectorApi.getStockChanges('快速反弹'),
        sectorApi.getStockChanges('大笔买入'),
        sectorApi.getStockChanges('封涨停板'),
        sectorApi.getIndustrySummary(),
        fundFlowApi.getIndividualImmediate(10),
        dragonTigerApi.getLhbDetail(yesterday, today).catch(() => [] as LhbDetail[]),
      ]);

      // 大盘资金流向：按日期降序（防御：即使某接口返回 null 也安全）
      (fundFlow || []).sort((a, b) => (b.trade_date || '').localeCompare(a.trade_date || ''));
      setMarketFundFlow(fundFlow || []);

      setZtPool(zt || []);
      setDtPool(dt || []);
      setRocketChanges(rocket || []);
      setReboundChanges(rebound || []);
      setBigBuyChanges(bigBuy || []);
      setLimitUpChanges(limitup || []);
      setIndustryList(industry || []);
      setFundTop10(fundTop || []);
      setLhbDetail(lhb || []);

      // 2) 逐个写入当日缓存（拆分为独立小 key，避免单 key 超 localStorage 配额）
      writeDailyCache(`${CACHE_PREFIX}:fundFlow`, fundFlow || []);
      writeDailyCache(`${CACHE_PREFIX}:zt`, zt || []);
      writeDailyCache(`${CACHE_PREFIX}:dt`, dt || []);
      writeDailyCache(`${CACHE_PREFIX}:rocket`, rocket || []);
      writeDailyCache(`${CACHE_PREFIX}:rebound`, rebound || []);
      writeDailyCache(`${CACHE_PREFIX}:bigBuy`, bigBuy || []);
      writeDailyCache(`${CACHE_PREFIX}:limitup`, limitup || []);
      writeDailyCache(`${CACHE_PREFIX}:industry`, industry || []);
      writeDailyCache(`${CACHE_PREFIX}:fundTop`, fundTop || []);
      writeDailyCache(`${CACHE_PREFIX}:lhb`, lhb || []);
    } catch (e: any) {
      message.error('数据加载失败: ' + e.message);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (didInitRef.current) return;
    didInitRef.current = true;
    // 启动时清理过期的 dailyCache（其它日期的旧 key）
    purgeExpiredDailyCache();
    // 清理旧的单一大 key 残骸（合并式缓存拆分前遗留，key = dashboard:YYYYMMDD）
    clearDailyCache(`dashboard:${dayjs().format('YYYYMMDD')}`);
    loadAll();
  }, [loadAll]);

  // ── 全量同步处理（先 K 线后指标） ──
  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      // 第1步：触发全市场K线采集
      message.loading({ content: '正在触发全市场 K 线采集...', key: 'sync', duration: 0 });
      const klineResult = await marketApi.triggerKlineCollect('day');
      message.success({ content: `K 线采集已触发 (task: ${klineResult?.data?.task_id || '--'})`, key: 'sync', duration: 3 });

      // 第2步：等待片刻后回填指标数据
      message.loading({ content: '正在回填全市场指标数据...', key: 'sync2', duration: 0 });
      await new Promise(r => setTimeout(r, 1500));
      const indicatorResult = await marketApi.backfillIndicators();
      const data = indicatorResult?.data || indicatorResult;
      const total = data?.total ?? 0;
      const ok = data?.ok ?? 0;
      const failed = data?.failed ?? 0;
      const elapsed = data?.elapsed_s ?? 0;
      message.success({
        content: `指标回填完成：成功 ${ok}/${total} 只，失败 ${failed} 只，耗时 ${elapsed}s`,
        key: 'sync2',
        duration: 5,
      });
    } catch (e: any) {
      message.error({ content: '全量同步失败: ' + (e.message || '未知错误'), key: 'sync', duration: 5 });
    } finally {
      setSyncing(false);
    }
  }, []);

  // ── 最新的一条大盘资金流向 ──
  const latestFundFlow = marketFundFlow[0];

  // ── 涨停/跌停统计 ──
  const maxLimitTimes = useMemo(() => getMaxLimitTimes(ztPool), [ztPool]);
  const limitUpCount = ztPool.length;
  const limitDownCount = dtPool.length;

  // ── 连板梯队 ──
  const boardGroups = useMemo(() => groupByLimitTimes(ztPool), [ztPool]);
  const topBoard = boardGroups[0];

  // ── 行业热力图取涨跌幅前12 ──
  const heatmapData = useMemo(() => {
    const sorted = [...industryList].sort((a, b) => Math.abs(safeNum(b.change_percent)) - Math.abs(safeNum(a.change_percent)));
    return sorted.slice(0, 16);
  }, [industryList]);

  // ── 龙虎榜取前5 ──
  const lhbTop5 = useMemo(() => lhbDetail.slice(0, 5), [lhbDetail]);

  // ── Tab 配置 ──
  // (moved outside component)

  const getChangeData = useCallback((key: string): StockChangeItem[] => {
    const map: Record<string, StockChangeItem[]> = {
      rocket: rocketChanges,
      rebound: reboundChanges,
      bigbuy: bigBuyChanges,
      limitup: limitUpChanges,
    };
    return map[key] || [];
  }, [rocketChanges, reboundChanges, bigBuyChanges, limitUpChanges]);

  // ── 指数卡片渲染 ──
  const renderIndexCard = (name: string, value: number, pctIn: number, showAmount?: { amount: number, up: number, down: number }) => {
    const pct = safeNum(pctIn);
    const change = (pct / 100) * safeNum(value); // 粗略计算涨跌点数
    return (
      <div style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        padding: '14px 16px',
        height: '100%',
      }}>
        <Text style={{ color: colors.textSecondary, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
          {name}
        </Text>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '24px', fontWeight: 700, letterSpacing: '0.5px' }}>
            {safeToFixed(value, 2)}
          </Text>
          <Text style={{ color: pctColor(pct), fontSize: '12px', fontWeight: 600 }}>
            {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
          </Text>
        </div>
        {showAmount && (
          <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
            成交 {fmtYi(showAmount.amount)} · 上涨 {showAmount.up} 下跌 {showAmount.down}
          </Text>
        )}
      </div>
    );
  };

  // ── 盘口异动表格列 ──
  const marketChangeColumns = useMemo(() => [
    {
      title: '股票', key: 'name',
      render: (_: any, record: StockChangeItem) => (
        <div>
          <div style={{ color: colors.textPrimary, fontWeight: 500, fontSize: '13px' }}>
            {record.name} ({record.symbol})
          </div>
        </div>
      ),
    },
    {
      title: '最新价', dataIndex: 'price', key: 'price', align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 500 }}>
          {safeToFixed(v, 2)}
        </span>
      ),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', key: 'change_percent', align: 'right' as const,
      render: (v: number) => {
        const pct = parseChangePct(v);
        return (
          <span style={{ color: pctColor(pct), fontSize: '13px', fontWeight: 600 }}>
            {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '异动时间', dataIndex: 'occur_time', key: 'occur_time', align: 'right' as const,
      render: (v: string) => (
        <span style={{ color: colors.textTertiary, fontSize: '12px', fontStyle: 'italic' }}>{v || '--'}</span>
      ),
    },
  ], [colors]);

  // ── 主力TOP10表格列 ──
  const mainForceColumns = useMemo(() => [
    {
      title: '代码 / 名称', key: 'name',
      render: (_: any, record: FundFlowIndividualImmediate) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{record.symbol}</Text>
          <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 500 }}>{record.name}</Text>
        </div>
      ),
    },
    {
      title: '涨幅%', dataIndex: 'change_percent', key: 'change_percent', align: 'right' as const,
      render: (v: string) => {
        const n = parseFloat(v) || 0;
        return (
          <span style={{ color: pctColor(n), fontSize: '13px', fontWeight: 500 }}>
            {n >= 0 ? '+' : ''}{n.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '主力/亿', dataIndex: 'net_amount', key: 'net_amount', align: 'right' as const,
      render: (v: string) => {
        const val = parseAmountToYi(v);
        return (
          <span style={{ color: pctColor(val), fontSize: '13px', fontWeight: 600 }}>
            {val >= 0 ? '+' : ''}{fmtYiRaw(val)}
          </span>
        );
      },
    },
  ], [colors]);

  // ── 热力图颜色 ──
  // ── 完整涨停池弹窗表格列 ──
  const ztPoolColumns = useMemo(() => [
    {
      title: '代码', key: 'symbol', width: 80,
      render: (_: any, record: LimitUpPoolItem) => (
        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>{record.symbol}</Text>
      ),
    },
    {
      title: '名称', key: 'name', width: 100,
      render: (_: any, record: LimitUpPoolItem) => (
        <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 500 }}>{record.name}</Text>
      ),
    },
    {
      title: '最新价', dataIndex: 'latest_price', key: 'latest_price', width: 80, align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: colors.textPrimary, fontSize: '13px' }}>{safeToFixed(v, 2)}</span>
      ),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', key: 'change_percent', width: 80, align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: pctColor(v), fontSize: '13px', fontWeight: 600 }}>
          +{safeToFixed(v, 2)}%
        </span>
      ),
    },
    {
      title: '封板资金', dataIndex: 'limit_fund', key: 'limit_fund', width: 100, align: 'right' as const,
      sorter: (a: LimitUpPoolItem, b: LimitUpPoolItem) => (a.limit_fund ?? 0) - (b.limit_fund ?? 0),
      defaultSortOrder: 'descend' as const,
      render: (v: number | null | undefined) => (
        <span style={{ color: colors.textPrimary, fontSize: '12px' }}>
          {v != null ? '¥' + (v / 1e8).toFixed(2) + '亿' : '--'}
        </span>
      ),
    },
    {
      title: '首次封板', dataIndex: 'first_limit_time', key: 'first_limit_time', width: 80, align: 'center' as const,
      render: (v: string) => (
        <span style={{ color: colors.textSecondary, fontSize: '12px' }}>{v ? `${v.slice(0, 2)}:${v.slice(2, 4)}:${v.slice(4, 6)}` : '--'}</span>
      ),
    },
    {
      title: '最后封板', dataIndex: 'last_limit_time', key: 'last_limit_time', width: 80, align: 'center' as const,
      render: (v: string) => (
        <span style={{ color: colors.textSecondary, fontSize: '12px' }}>{v ? `${v.slice(0, 2)}:${v.slice(2, 4)}:${v.slice(4, 6)}` : '--'}</span>
      ),
    },
    {
      title: '开板', dataIndex: 'open_count', key: 'open_count', width: 50, align: 'center' as const,
      render: (v: number | null | undefined) => (
        <span style={{ color: v ? '#fa8c16' : colors.textTertiary, fontSize: '12px' }}>{v ?? 0}</span>
      ),
    },
    {
      title: '连板', dataIndex: 'limit_times', key: 'limit_times', width: 50, align: 'center' as const,
      render: (v: number | null | undefined) => (
        <span style={{ color: '#ff4d4f', fontSize: '13px', fontWeight: 700 }}>{v ?? 0}</span>
      ),
    },
    {
      title: '涨停统计', dataIndex: 'limit_statistic', key: 'limit_statistic', width: 80, align: 'center' as const,
      render: (v: string) => (
        <span style={{ color: colors.textSecondary, fontSize: '12px' }}>{v || '--'}</span>
      ),
    },
    {
      title: '行业', dataIndex: 'industry', key: 'industry', width: 80,
      render: (v: string) => (
        <span style={{ color: colors.textTertiary, fontSize: '12px' }}>{v}</span>
      ),
    },
  ], [colors]);

  const getHeatmapColor = (change: number) => {
    if (change > 5) return { bg: 'rgba(255, 77, 79, 0.45)', border: 'rgba(255, 77, 79, 0.7)' };
    if (change > 2) return { bg: 'rgba(255, 77, 79, 0.28)', border: 'rgba(255, 77, 79, 0.5)' };
    if (change >= 0) return { bg: 'rgba(255, 77, 79, 0.15)', border: 'rgba(255, 77, 79, 0.3)' };
    if (change > -3) return { bg: 'rgba(82, 196, 26, 0.18)', border: 'rgba(82, 196, 26, 0.35)' };
    return { bg: 'rgba(82, 196, 26, 0.32)', border: 'rgba(82, 196, 26, 0.55)' };
  };

  return (
    <Spin spinning={loading} delay={0} style={{ height: 'calc(100vh - 60px)', overflowY: 'auto' }}>
      {/* 注：antd v5 Spin 已废弃 tip 用于非 wrapper 场景；包裹模式下保留 description 替代见各局部 Spin */}
      {/* 顶部标题栏 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '14px', flexWrap: 'wrap', gap: '8px',
      }}>
        <Space size="small" align="center">
          <Text style={{ color: colors.textPrimary, fontSize: '16px', fontWeight: 700 }}>总览仪表盘</Text>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>·</Text>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>
            {queryDateStr || dayjs().format('YYYY-MM-DD')}
          </Text>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>·</Text>
          <Text style={{ color: colors.textSecondary, fontSize: '13px' }}>
            {latestFundFlow
              ? `数据: ${latestFundFlow.trade_date}${!isTradingDay(dayjs()) ? ` (非交易日→取${queryDateStr})` : ''}`
              : '加载中...'}
          </Text>
        </Space>
        <Space size="small">
          <Button size="small" icon={<ReloadOutlined />} onClick={() => loadAll(true)}
            style={{ background: colors.bgCard, borderColor: colors.borderColor, color: colors.textSecondary, fontSize: '12px', borderRadius: '6px' }}>
            手动刷新
          </Button>
          <Button size="small" icon={<DownloadOutlined />}
            style={{ background: colors.bgCard, borderColor: colors.borderColor, color: colors.textSecondary, fontSize: '12px', borderRadius: '6px' }}>
            导出 CSV
          </Button>
          <Button size="small" type="primary" icon={<SyncOutlined />} onClick={handleSync} loading={syncing}
            style={{ background: syncing ? undefined : 'linear-gradient(135deg, #56A4FF 0%, #546ACF 100%)', border: 'none', fontSize: '12px', borderRadius: '6px' }}>
            {syncing ? '同步中...' : '一键同步 K 线 + 指标'}
          </Button>
        </Space>
      </div>

      {/* 第一行：5 个统计卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '14px' }}>
        {/* 上证指数 */}
        <Col xs={24} sm={12} md={12} lg={5} xl={5}>
          {renderIndexCard('上证指数', latestFundFlow?.sh_close ?? 0, latestFundFlow?.sh_pct_change ?? 0)}
        </Col>

        {/* 深证成指 */}
        <Col xs={24} sm={12} md={12} lg={5} xl={5}>
          {renderIndexCard('深证成指', latestFundFlow?.sz_close ?? 0, latestFundFlow?.sz_pct_change ?? 0)}
        </Col>

        {/* 主力净流入卡片 */}
        <Col xs={24} sm={12} md={12} lg={5} xl={5}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', padding: '14px 16px', height: '100%',
          }}>
            <Text style={{ color: colors.textSecondary, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              主力净流入·今日
            </Text>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
              <Text style={{ color: pctColor(safeNum(latestFundFlow?.main_net_inflow)), fontSize: '24px', fontWeight: 700 }}>
                {safeNum(latestFundFlow?.main_net_inflow) >= 0 ? '+' : ''}
                {fmtYiRaw(safeNum(latestFundFlow?.main_net_inflow))}
                <span style={{ fontSize: 14, marginLeft: 2 }}>亿</span>
              </Text>
              <Text style={{ color: '#ff4d4f', fontSize: '11px', fontWeight: 500 }}>
                超大单 {latestFundFlow?.super_large_net_inflow != null
                  ? `${(safeNum(latestFundFlow.super_large_net_inflow) >= 0 ? '+' : '')}${fmtYiRaw(safeNum(latestFundFlow.super_large_net_inflow))}亿`
                  : '--'}
              </Text>
            </div>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
              中单 {latestFundFlow?.medium_net_inflow != null
                ? `${(safeNum(latestFundFlow.medium_net_inflow) >= 0 ? '+' : '')}${fmtYiRaw(safeNum(latestFundFlow.medium_net_inflow))}亿`
                : '--'}
              · 小单 {latestFundFlow?.small_net_inflow != null
                ? `${(safeNum(latestFundFlow.small_net_inflow) >= 0 ? '+' : '')}${fmtYiRaw(safeNum(latestFundFlow.small_net_inflow))}亿`
                : '--'}
            </Text>
          </div>
        </Col>

        {/* 涨跌停卡片 */}
        <Col xs={24} sm={12} md={24} lg={4} xl={4}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', padding: '14px 16px', height: '100%',
          }}>
            <Text style={{ color: colors.textSecondary, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              涨停 / 跌停·最高连板
            </Text>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '4px' }}>
              <Text style={{ color: '#ff4d4f', fontSize: '24px', fontWeight: 700 }}>{limitUpCount}</Text>
              <Text style={{ color: colors.textTertiary, fontSize: '14px' }}>/</Text>
              <Text style={{ color: '#52c41a', fontSize: '20px', fontWeight: 600 }}>{limitDownCount}</Text>
              <Text style={{ color: colors.textTertiary, fontSize: '11px', marginLeft: '4px' }}>
                连板高 {maxLimitTimes} ↑
              </Text>
            </div>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
              {topBoard && topBoard.items[0]
                ? `最高连板：${topBoard.items[0].name} (${topBoard.items[0].symbol}) ${maxLimitTimes}连↑`
                : '暂无连板数据'}
            </Text>
          </div>
        </Col>

        {/* 市场概况卡片 */}
        <Col xs={24} sm={12} md={12} lg={5} xl={5}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', padding: '14px 16px', height: '100%',
          }}>
            <Text style={{ color: colors.textSecondary, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              行业 / 概念概况
            </Text>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
              <Text style={{ color: '#56A4FF', fontSize: '20px', fontWeight: 700 }}>{industryList.length}</Text>
              <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>个行业</Text>
            </div>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
              {heatmapData.length > 0 ? (
                <>最强：<span style={{ color: '#ff4d4f' }}>{heatmapData[0].board_name}</span>
                  {' '}{safeNum(heatmapData[0].change_percent) >= 0 ? '+' : ''}{safeToFixed(heatmapData[0].change_percent, 2)}%
                  · 最弱：<span style={{ color: '#52c41a' }}>{heatmapData[heatmapData.length - 1].board_name}</span>
                  {' '}{safeNum(heatmapData[heatmapData.length - 1].change_percent) >= 0 ? '+' : ''}{safeToFixed(heatmapData[heatmapData.length - 1].change_percent, 2)}%
                </>
              ) : '加载中...'}
            </Text>
          </div>
        </Col>
      </Row>

      {/* 第二行：盘口异动 + 行业热力图 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '14px' }}>
        <Col xs={24} lg={10}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', overflow: 'hidden', height: '100%',
          }}>
            <div style={{ padding: '12px 16px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                盘口异动·实时
              </Text>
            </div>
            <Tabs
              activeKey={activeChangeTab}
              onChange={setActiveChangeTab}
              size="small"
              style={{ padding: '0 12px' }}
              items={marketChangeTabs.map((tab) => ({
                key: tab.key,
                label: <span style={{ fontSize: '12px' }}>{tab.label}</span>,
              }))}
            />
            <div style={{ padding: '0 16px 16px' }}>
              <Table
                columns={marketChangeColumns}
                dataSource={getChangeData(activeChangeTab).slice(0, 8)}
                pagination={false}
                size="small"
                rowKey={(record: StockChangeItem) =>
                  `${record.symbol}_${record.change_type ?? ''}_${record.occur_time ?? ''}_${record.stat_date ?? ''}`
                }
                showHeader={true}
                style={{ background: 'transparent' }}
              />
            </div>
          </div>
        </Col>

        <Col xs={24} lg={14}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', overflow: 'hidden', height: '100%',
          }}>
            <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                行业热力图·今日（涨跌幅强度）
              </Text>
              <Space size="small">
                {heatmapTabs.map((tab) => (
                  <span key={tab.key}
                    onClick={() => setHeatmapTab(tab.key)}
                    style={{
                      cursor: 'pointer', fontSize: '12px', padding: '2px 10px', borderRadius: '4px',
                      background: heatmapTab === tab.key ? 'rgba(86, 164, 255, 0.15)' : 'transparent',
                      color: heatmapTab === tab.key ? '#56A4FF' : colors.textSecondary,
                      border: `1px solid ${heatmapTab === tab.key ? '#56A4FF' : 'transparent'}`,
                    }}>
                    {tab.label}
                  </span>
                ))}
              </Space>
            </div>
            <div style={{ padding: '0 16px 12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                {heatmapData.map((item) => {
                  const cp = safeNum(item.change_percent);
                  const colorStyle = getHeatmapColor(cp);
                  return (
                    <div key={item.board_name}
                      style={{
                        background: colorStyle.bg, border: `1px solid ${colorStyle.border}`,
                        borderRadius: '8px', padding: '14px 12px', textAlign: 'center',
                        transition: 'all 0.2s ease', cursor: 'pointer',
                      }}
                      onClick={() => { setSelectedIndustry(item); setIndustryDetailVisible(true); }}
                      onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.03)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}>
                      <div style={{ color: colors.textPrimary, fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>
                        {item.board_name}
                      </div>
                      <div style={{ fontSize: '11px' }}>
                        <span style={{ color: pctColor(cp), fontWeight: 600, marginRight: '6px' }}>
                          {cp >= 0 ? '+' : ''}{safeToFixed(cp, 2)}%
                        </span>
                        <span style={{ color: colors.textSecondary }}>
                          {item.net_inflow != null
                            ? `净${safeNum(item.net_inflow) >= 0 ? '流入' : '流出'}${safeToFixed(Math.abs(safeNum(item.net_inflow)), 1)}亿`
                            : ''}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Col>
      </Row>

      {/* 第三行：主力净流入 TOP10 + 涨停连板 + 龙虎榜 */}
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={8}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', overflow: 'hidden', height: '100%',
          }}>
            <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              borderBottom: `1px solid ${colors.borderColor}` }}>
              <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                主力净流入 TOP10
              </Text>
              <Text style={{ color: '#56A4FF', fontSize: '12px', cursor: 'pointer' }}>
                今日·全市场
              </Text>
            </div>
            <div style={{ padding: '0 16px 12px' }}>
              <Table
                columns={mainForceColumns}
                dataSource={fundTop10}
                pagination={false}
                size="small"
                rowKey={(record: FundFlowIndividualImmediate) =>
                  `${record.symbol}_${record.period_type ?? ''}`
                }
                showHeader={true}
                style={{ background: 'transparent' }}
              />
            </div>
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', overflow: 'hidden', height: '100%',
          }}>
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${colors.borderColor}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                  涨停连板·连板梯队
                </Text>
                <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                  {topBoard ? `${maxLimitTimes}连以上 ${topBoard.count}只` : '暂无数据'}
                </Text>
              </div>
            </div>
            <div style={{ padding: '12px 16px' }}>
              {boardGroups.length === 0 && (
                <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>当日暂无涨停数据</Text>
              )}
              {boardGroups.slice(0, 10).map((group) => {
                // 连板数大标签色系：1蓝、2青、3绿、4黄、5橙、6粉、7紫、≥8红
                const bigTagMap: Record<number, { grad: string; glow: string }> = {
                  1: { grad: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)', glow: 'rgba(24,144,255,0.6)' },
                  2: { grad: 'linear-gradient(135deg, #13c2c2 0%, #36cfc9 100%)', glow: 'rgba(19,194,194,0.6)' },
                  3: { grad: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)', glow: 'rgba(82,196,26,0.6)' },
                  4: { grad: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)', glow: 'rgba(250,173,20,0.6)' },
                  5: { grad: 'linear-gradient(135deg, #fa8c16 0%, #ffa940 100%)', glow: 'rgba(250,140,22,0.6)' },
                  6: { grad: 'linear-gradient(135deg, #eb2f96 0%, #f759ab 100%)', glow: 'rgba(235,47,150,0.6)' },
                  7: { grad: 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)', glow: 'rgba(114,46,209,0.6)' },
                };
                const bigTag = bigTagMap[group.times] || { grad: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)', glow: 'rgba(255,77,79,0.6)' };
                const displayItems = group.items.slice(0, 2);
                return (
                  <div key={group.times} style={{
                    display: 'flex', alignItems: 'flex-start', padding: '8px 0',
                    borderBottom: `1px solid ${colors.borderColor}`,
                  }}>
                    {/* 连板数标签（带光影） */}
                    <div style={{
                      background: bigTag.grad,
                      borderRadius: '6px', padding: '6px 10px', marginRight: '10px',
                      minWidth: '52px', textAlign: 'center', flexShrink: 0,
                      boxShadow: `0 0 8px ${bigTag.glow}`,
                    }}>
                      <Text style={{ color: '#fff', fontSize: '12px', fontWeight: 700 }}>{group.times}连板</Text>
                    </div>
                    {/* 右侧：最多2只股票列表 */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {displayItems.map((item, idx) => (
                        <div key={item.symbol} style={{
                          marginBottom: idx < displayItems.length - 1 ? '8px' : 0,
                        }}>
                          {/* 第一行：名称代码 + 涨跌幅 */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {/* 股票名 */}
                            <Text style={{
                              color: colors.textPrimary, fontSize: '12px', fontWeight: 500,
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flexShrink: 0, maxWidth: 70,
                            }}>{item.name}</Text>
                            {/* 代码 */}
                            <Text style={{
                              color: colors.textTertiary, fontSize: '10px', flexShrink: 0, maxWidth: 55,
                              overflow: 'hidden', textOverflow: 'ellipsis',
                            }}>{item.symbol}</Text>
                            {/* 涨跌幅 */}
                            <Text style={{
                              color: '#ff4d4f', fontSize: '11px', fontWeight: 600, marginLeft: 'auto', flexShrink: 0,
                            }}>+{safeToFixed(item.change_percent, 2, '0')}%</Text>
                          </div>
                          {/* 第二行：封板资金（红色带边框） + 行业（带边框） */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                            {item.limit_fund != null && (
                              <span style={{
                                fontSize: '10px', color: '#ff4d4f', fontWeight: 600,
                                border: '1px solid rgba(255,77,79,0.4)', borderRadius: '4px',
                                padding: '1px 6px', background: 'rgba(255,77,79,0.08)',
                                lineHeight: '16px',
                              }}>
                                封板 ¥{(safeNum(item.limit_fund) / 1e8).toFixed(1)}亿
                              </span>
                            )}
                            {item.industry && (
                              <span style={{
                                fontSize: '10px', color: colors.textSecondary,
                                border: `1px solid ${colors.borderColor}`, borderRadius: '4px',
                                padding: '1px 6px', background: 'rgba(255,255,255,0.03)',
                                lineHeight: '16px',
                              }}>
                                {item.industry}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
              <div style={{ marginTop: '8px', paddingTop: '8px', textAlign: 'center' }}>
                <Text style={{ color: '#56A4FF', fontSize: '12px', cursor: 'pointer' }}
                  onClick={() => setZtPoolModalVisible(true)}>
                  查看完整涨停池·开板梯 →
                </Text>
              </div>
            </div>
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <div style={{
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            borderRadius: '12px', overflow: 'hidden', height: '100%',
          }}>
            <div style={{
              padding: '12px 16px', display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', borderBottom: `1px solid ${colors.borderColor}`,
            }}>
              <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                龙虎榜·今日热名
              </Text>
              <Text
                style={{ color: '#56A4FF', fontSize: '11px', cursor: 'pointer' }}
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('market:navigate', { detail: { key: 'dragon-tiger' } }));
                }}
              >
                详情 →
              </Text>
            </div>
            <div style={{ padding: '6px 16px' }}>
              {lhbTop5.length === 0 && (
                <Text style={{ color: colors.textTertiary, fontSize: '13px', display: 'block', padding: '12px 0' }}>
                  暂无龙虎榜数据
                </Text>
              )}
              {lhbTop5.map((item, idx) => {
                const netBuy = safeNum(item.lhb_net_amount);
                const isBuy = netBuy > 0;
                return (
                  <div key={idx} style={{
                    padding: '12px 0',
                    borderBottom: idx < lhbTop5.length - 1 ? `1px solid ${colors.borderColor}` : 'none',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}>
                        <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 500 }}>
                          {item.name} ({item.symbol})
                        </Text>
                        <div style={{ fontSize: '11px', color: colors.textTertiary, marginTop: '4px' }}>
                          {item.reason || item.interpretation || '--'}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', marginLeft: '8px' }}>
                        <div style={{ fontSize: '10px', color: colors.textTertiary }}>
                          {isBuy ? '净买' : '净卖'}
                        </div>
                        <Text style={{ color: pctColor(netBuy), fontSize: '15px', fontWeight: 700 }}>
                          {isBuy ? '+' : '-'}¥{Math.abs(netBuy) > 1e8
                            ? (Math.abs(netBuy) / 1e8).toFixed(2)
                            : (Math.abs(netBuy) / 1e4).toFixed(2)}
                          亿
                        </Text>
                        <div style={{ fontSize: '10px', color: colors.textTertiary, marginTop: '2px' }}>
                          涨幅 {safeNum(item.change_percent) >= 0 ? '+' : ''}{safeToFixed(item.change_percent, 2, '0')}%
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Col>
      </Row>
    {/* Modal：完整涨停池弹窗 */}
      <Modal
        title={<span style={{ fontSize: '16px', fontWeight: 600 }}>完整涨停池·连板梯队（共 {ztPool.length} 只）</span>}
        open={ztPoolModalVisible}
        onCancel={() => setZtPoolModalVisible(false)}
        footer={null}
        width={1000}
        destroyOnHidden
      >
        {/* 行业分布统计 */}
        {(() => {
          const industryMap = new Map<string, number>();
          ztPool.forEach((it) => {
            const ind = it.industry || '未分类';
            industryMap.set(ind, (industryMap.get(ind) || 0) + 1);
          });
          const industryStats = Array.from(industryMap.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
          const totalIndustryCount = industryMap.size;
          // 色板（循环使用）
          const colorPalette = [
            { bg: 'rgba(255,77,79,0.12)', border: 'rgba(255,77,79,0.4)', text: '#ff4d4f' },
            { bg: 'rgba(250,140,22,0.12)', border: 'rgba(250,140,22,0.4)', text: '#fa8c16' },
            { bg: 'rgba(250,173,20,0.12)', border: 'rgba(250,173,20,0.4)', text: '#faad14' },
            { bg: 'rgba(82,196,26,0.12)', border: 'rgba(82,196,26,0.4)', text: '#52c41a' },
            { bg: 'rgba(19,194,194,0.12)', border: 'rgba(19,194,194,0.4)', text: '#13c2c2' },
            { bg: 'rgba(24,144,255,0.12)', border: 'rgba(24,144,255,0.4)', text: '#1890ff' },
            { bg: 'rgba(114,46,209,0.12)', border: 'rgba(114,46,209,0.4)', text: '#722ed1' },
            { bg: 'rgba(235,47,150,0.12)', border: 'rgba(235,47,150,0.4)', text: '#eb2f96' },
          ];
          return (
            <div style={{
              marginBottom: 12, padding: '10px 12px',
              border: `1px solid ${colors.borderColor}`, borderRadius: 6,
              background: 'rgba(255,255,255,0.02)',
              maxHeight: 110, overflowY: 'auto',
            }}>
              <div style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 8, fontWeight: 600 }}>
                行业分布 TOP10（共 {totalIndustryCount} 个行业）
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {industryStats.map(([ind, count], idx) => {
                  const c = colorPalette[idx % colorPalette.length];
                  return (
                    <span key={ind} style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 4,
                      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
                      fontWeight: 500, lineHeight: '18px',
                    }}>
                      {ind} <span style={{ fontWeight: 700, marginLeft: 2 }}>{count}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })()}
        <div style={{ height: 480, display: 'flex', flexDirection: 'column' }}>
          <Table
            columns={ztPoolColumns}
            dataSource={ztPool}
            rowKey={(record: LimitUpPoolItem) =>
              `${record.symbol}_${record.first_limit_time ?? ''}_${record.limit_times ?? 0}`
            }
            size="small"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              pageSizeOptions: ['20', '50', '100'],
              showTotal: (total) => `共 ${total} 只`,
            }}
            scroll={{ x: 900, y: 350 }}
            style={{ background: 'transparent' }}
          />
        </div>
      </Modal>

      {/* Modal：行业热力图详细信息弹窗 */}
      <Modal
        title={
          <span style={{ fontSize: '16px', fontWeight: 600 }}>
            行业详细信息 ·{' '}
            <span style={{ color: '#56A4FF' }}>{selectedIndustry?.board_name}</span>
          </span>
        }
        open={industryDetailVisible}
        onCancel={() => setIndustryDetailVisible(false)}
        footer={null}
        width={680}
        destroyOnHidden
      >
        {selectedIndustry && (() => {
          const cp = safeNum(selectedIndustry.change_percent);
          const inflow = safeNum(selectedIndustry.net_inflow);
          const rise = safeNum(selectedIndustry.rise_count);
          const fall = safeNum(selectedIndustry.fall_count);
          const total = rise + fall;
          const risePct = total > 0 ? (rise / total) * 100 : 0;
          const leaderChg = safeNum(selectedIndustry.leading_stock_change);
          return (
            <div>
              {/* 顶部：核心指标卡片 */}
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16,
              }}>
                <div style={{
                  padding: '12px', borderRadius: 8,
                  background: cp >= 0 ? 'rgba(255,77,79,0.10)' : 'rgba(82,196,26,0.10)',
                  border: `1px solid ${cp >= 0 ? 'rgba(255,77,79,0.35)' : 'rgba(82,196,26,0.35)'}`,
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: colors.textTertiary, marginBottom: 4 }}>涨跌幅</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: pctColor(cp) }}>
                    {cp >= 0 ? '+' : ''}{safeToFixed(cp, 2)}%
                  </div>
                </div>
                <div style={{
                  padding: '12px', borderRadius: 8,
                  background: inflow >= 0 ? 'rgba(255,77,79,0.10)' : 'rgba(82,196,26,0.10)',
                  border: `1px solid ${inflow >= 0 ? 'rgba(255,77,79,0.35)' : 'rgba(82,196,26,0.35)'}`,
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: colors.textTertiary, marginBottom: 4 }}>主力净{inflow >= 0 ? '流入' : '流出'}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: pctColor(inflow) }}>
                    ¥{safeToFixed(Math.abs(inflow), 2)}亿
                  </div>
                </div>
                <div style={{
                  padding: '12px', borderRadius: 8,
                  background: 'rgba(86,164,255,0.08)',
                  border: '1px solid rgba(86,164,255,0.30)',
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: colors.textTertiary, marginBottom: 4 }}>总成交额</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#56A4FF' }}>
                    ¥{safeToFixed(safeNum(selectedIndustry.total_amount), 2)}亿
                  </div>
                </div>
                <div style={{
                  padding: '12px', borderRadius: 8,
                  background: 'rgba(250,173,20,0.08)',
                  border: '1px solid rgba(250,173,20,0.30)',
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: 11, color: colors.textTertiary, marginBottom: 4 }}>总成交量</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#faad14' }}>
                    {safeToFixed(safeNum(selectedIndustry.total_volume), 2)}万手
                  </div>
                </div>
              </div>

              {/* 涨跌家数比例条 */}
              <div style={{
                padding: 12, borderRadius: 8,
                border: `1px solid ${colors.borderColor}`,
                background: 'rgba(255,255,255,0.02)', marginBottom: 12,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: colors.textSecondary, fontWeight: 600 }}>涨跌家数对比</span>
                  <span style={{ fontSize: 12, color: colors.textTertiary }}>共 {total} 只</span>
                </div>
                <div style={{
                  display: 'flex', height: 24, borderRadius: 4, overflow: 'hidden',
                  background: 'rgba(255,255,255,0.05)',
                }}>
                  <div style={{
                    width: `${risePct}%`, background: 'linear-gradient(90deg, #ff4d4f, #ff7875)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: 11, fontWeight: 600,
                    transition: 'width 0.5s ease',
                  }}>
                    {rise > 0 ? `↑${rise}` : ''}
                  </div>
                  <div style={{
                    width: `${100 - risePct}%`, background: 'linear-gradient(90deg, #73d13d, #52c41a)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: 11, fontWeight: 600,
                    transition: 'width 0.5s ease',
                  }}>
                    {fall > 0 ? `${fall}↓` : ''}
                  </div>
                </div>
                <div style={{ marginTop: 6, fontSize: 11, color: colors.textTertiary, textAlign: 'center' }}>
                  上涨占比 {risePct.toFixed(1)}% · 下跌占比 {(100 - risePct).toFixed(1)}%
                </div>
              </div>

              {/* 龙头股信息 */}
              <div style={{
                padding: 12, borderRadius: 8,
                border: '1px solid rgba(255,77,79,0.30)',
                background: 'rgba(255,77,79,0.06)', marginBottom: 12,
              }}>
                <div style={{ fontSize: 12, color: colors.textSecondary, fontWeight: 600, marginBottom: 8 }}>
                  🔥 龙头股
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: 16, color: colors.textPrimary, fontWeight: 700, marginRight: 10 }}>
                      {selectedIndustry.leading_stock_name || '--'}
                    </span>
                    <span style={{ fontSize: 12, color: colors.textTertiary }}>
                      现价 ¥{safeToFixed(safeNum(selectedIndustry.leading_stock_price), 2)}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 16, fontWeight: 700, color: pctColor(leaderChg),
                  }}>
                    {leaderChg >= 0 ? '+' : ''}{safeToFixed(leaderChg, 2)}%
                  </span>
                </div>
              </div>

              {/* 其他详情 */}
              <div style={{
                padding: 12, borderRadius: 8,
                border: `1px solid ${colors.borderColor}`,
                background: 'rgba(255,255,255,0.02)',
              }}>
                <div style={{ fontSize: 12, color: colors.textSecondary, fontWeight: 600, marginBottom: 8 }}>
                  其他信息
                </div>
                <Row gutter={[8, 8]}>
                  <Col span={12}>
                    <span style={{ fontSize: 12, color: colors.textTertiary }}>排名：</span>
                    <span style={{ fontSize: 12, color: colors.textPrimary, fontWeight: 600 }}>
                      第 {selectedIndustry.serial_number} 位
                    </span>
                  </Col>
                  <Col span={12}>
                    <span style={{ fontSize: 12, color: colors.textTertiary }}>行业均价：</span>
                    <span style={{ fontSize: 12, color: colors.textPrimary, fontWeight: 600 }}>
                      ¥{safeToFixed(safeNum(selectedIndustry.avg_price), 2)}
                    </span>
                  </Col>
                  <Col span={12}>
                    <span style={{ fontSize: 12, color: colors.textTertiary }}>统计日期：</span>
                    <span style={{ fontSize: 12, color: colors.textPrimary, fontWeight: 600 }}>
                      {selectedIndustry.stat_date || '--'}
                    </span>
                  </Col>
                  <Col span={12}>
                    <span style={{ fontSize: 12, color: colors.textTertiary }}>资金流向：</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: pctColor(inflow) }}>
                      {inflow >= 0 ? '净流入' : '净流出'}
                    </span>
                  </Col>
                </Row>
              </div>
            </div>
          );
        })()}
      </Modal>
    </Spin>
  );
};

export default React.memo(Dashboard);