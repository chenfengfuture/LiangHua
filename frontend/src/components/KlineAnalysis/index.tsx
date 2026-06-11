/**
 * K线分析 - 顶部主分类页面
 *
 * 布局：左侧自选股侧列 + 右侧 Tab 内容区
 *
 * 对接后端接口：
 *   - GET /api/stock/indicators           技术指标
 *   - GET /api/stock/indicators/meta      指标元信息
 *   - GET /api/stock/get-kline            三层缓存K线
 *   - GET /api/stock/get-stock-zh-a-hist-min-em  分钟K线
 *   - GET /api/stock/realtime-quotes      实时行情
 *   - GET /api/stock/get-minute-tick      分时Tick
 *   - POST /api/stock/get-kline/ws-trigger   K线采集触发
 *
 * 内部 Tab 设计（参考主流量化平台）：
 *   1. 个股K线   — 多周期K线图 + 技术指标叠加
 *   2. 技术指标   — 全指标数据面板
 *   3. 实时行情   — 选中个股分时图 + 日内曲线（同花顺风格）
 *   4. K线采集   — 全市场K线采集管理
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Tabs, Input, Select, Button, Table, Tag, Typography, Space, Spin, Card, Row, Col, Statistic, Empty, Progress, Tooltip, Popconfirm, Alert, DatePicker, App } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  TableOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  SearchOutlined,
  FieldNumberOutlined,
  RiseOutlined,
  DollarOutlined,
  ApiOutlined,
  RightOutlined,
  LeftOutlined,
  PlusOutlined,
  CloseOutlined,
  StarOutlined,
  StarFilled,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { klineAnalysisApi } from '@/api/klineAnalysis';
import { STOCK_API } from '@/config';
import IntradayChart from '@/components/Chart/IntradayChart';
import IndicatorSelector, { type TechnicalIndicatorKey } from './IndicatorSelector';
import { calcBOLL, calcKDJ, calcMA, calcMACD, calcRSI, type OhlcPoint } from '@/utils/technicalIndicators';
import type {
  IndicatorData,
  IndicatorMeta,
  RealtimeQuote,
  RealtimeQuoteDict,
  StockKlineDaily,
  StockKlineMinute,
  MinuteTickItem,
  TransactionItem,
  VolumeVwmaPoint,
  VolumeVrPoint,
  VolumeBiasPoint,
} from '../../types/stock';

const { Text, Title } = Typography;

// ─── 工具函数 ───────────────────────────────────────────────────

const fmtPrice = (v: number | null | undefined, d = 2): string => {
  if (v == null || isNaN(v)) return '--';
  return v.toFixed(d);
};

const fmtPct = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
};

const pctColor = (v: number | null | undefined): string => {
  if (v == null || isNaN(v) || v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

const fmtVol = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(0);
};

/** 行情概览迷你字段组件（标题 + 值，紧凑布局） */
const QuoteMiniGroup: React.FC<{ title: string; value: string; color: string }> = ({ title, value, color }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 48 }}>
    <span style={{ fontSize: 10, color: '#6B6B70', lineHeight: 1.3 }}>{title}</span>
    <span style={{ fontSize: 14, fontWeight: 600, color, fontFamily: 'monospace', lineHeight: 1.3 }}>{value}</span>
  </div>
);

// ─── localStorage 自选股管理 ────────────────────────────────────

const WATCHLIST_KEY = 'kline_watchlist_symbols';

const getWatchlist = (): string[] => {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch { /* ignore */ }
  return ['000001', '600519', '000858', '002415', '300750'];
};

const saveWatchlist = (list: string[]) => {
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
};

// ═══════════════════════════════════════════════════════════════════
//  自选股侧列组件
// ═══════════════════════════════════════════════════════════════════

interface WatchlistSidebarProps {
  activeSymbol: string;
  onSelect: (symbol: string) => void;
}

const WatchlistSidebar: React.FC<WatchlistSidebarProps> = ({ activeSymbol, onSelect }) => {
  const { colors } = useTheme();
  const { message } = App.useApp();
  const [collapsed, setCollapsed] = useState(false);
  const [symbols, setSymbols] = useState<string[]>(getWatchlist);
  const [addInput, setAddInput] = useState('');
  const [addVisible, setAddVisible] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    saveWatchlist(symbols);
  }, [symbols]);

  useEffect(() => {
    if (addVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [addVisible]);

  const handleAdd = () => {
    const code = addInput.trim().toUpperCase();
    if (!code) return;
    if (symbols.includes(code)) {
      message.info(`"${code}" 已在自选股中`);
      setAddInput('');
      return;
    }
    setSymbols(prev => [...prev, code]);
    setAddInput('');
    setAddVisible(false);
  };

  const handleRemove = (code: string) => {
    setSymbols(prev => prev.filter(s => s !== code));
  };

  const toggleCollapse = () => setCollapsed(v => !v);

  // 折叠状态：仅显示图标
  if (collapsed) {
    return (
      <div style={{
        width: 36, flexShrink: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        borderRight: `1px solid ${colors.borderColor}`,
        padding: '8px 0',
        background: colors.bgSecondary,
        userSelect: 'none',
      }}>
        <Tooltip title="展开自选股" placement="right">
          <Button
            type="text"
            size="small"
            icon={<RightOutlined />}
            onClick={toggleCollapse}
            style={{ color: colors.textSecondary, marginBottom: 8 }}
          />
        </Tooltip>
        {symbols.slice(0, 10).map(code => (
          <Tooltip key={code} title={code} placement="right">
            <div
              onClick={() => onSelect(code)}
              style={{
                width: 28, height: 28, lineHeight: '28px', textAlign: 'center',
                marginBottom: 4, borderRadius: 4,
                cursor: 'pointer', fontSize: 10, fontFamily: 'monospace',
                background: code === activeSymbol ? `${colors.accentBlue}33` : 'transparent',
                color: code === activeSymbol ? colors.accentBlue : colors.textTertiary,
                overflow: 'hidden',
              }}
            >
              {code}
            </div>
          </Tooltip>
        ))}
        <Tooltip title="展开" placement="right">
          <div
            onClick={toggleCollapse}
            style={{
              width: 28, height: 28, lineHeight: '28px', textAlign: 'center',
              marginTop: 4, cursor: 'pointer', fontSize: 12, color: colors.textTertiary,
            }}
          >
            <PlusOutlined />
          </div>
        </Tooltip>
      </div>
    );
  }

  return (
    <div style={{
      width: 180, flexShrink: 0,
      display: 'flex', flexDirection: 'column',
      borderRight: `1px solid ${colors.borderColor}`,
      background: colors.bgSecondary,
      overflow: 'hidden',
    }}>
      {/* 头部 */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 10px',
        borderBottom: `1px solid ${colors.borderColor}`,
      }}>
        <Space size={4}>
          <StarFilled style={{ fontSize: 14, color: '#F59E0B' }} />
          <Text style={{ fontSize: 13, fontWeight: 600, color: colors.textPrimary }}>自选股</Text>
          <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>{symbols.length}</Tag>
        </Space>
        <Space size={0}>
          <Tooltip title="添加股票">
            <Button
              type="text" size="small"
              icon={<PlusOutlined style={{ fontSize: 12 }} />}
              onClick={() => setAddVisible(v => !v)}
              style={{ color: colors.textSecondary }}
            />
          </Tooltip>
          <Tooltip title="折叠">
            <Button
              type="text" size="small"
              icon={<LeftOutlined style={{ fontSize: 12 }} />}
              onClick={toggleCollapse}
              style={{ color: colors.textSecondary }}
            />
          </Tooltip>
        </Space>
      </div>

      {/* 添加输入框 */}
      {addVisible && (
        <div style={{ padding: '4px 8px', borderBottom: `1px solid ${colors.borderColor}` }}>
          <Input
            ref={inputRef as any}
            size="small"
            placeholder="输入代码回车添加"
            value={addInput}
            onChange={e => setAddInput(e.target.value)}
            onPressEnter={handleAdd}
            suffix={
              addInput ? (
                <Button type="text" size="small" style={{ padding: 0, height: 18, minWidth: 18 }}
                  onClick={handleAdd}
                >+</Button>
              ) : null
            }
            style={{ fontSize: 12, height: 28 }}
          />
        </div>
      )}

      {/* 自选股列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '2px 0' }}>
        {symbols.length === 0 ? (
          <div style={{ padding: 16, textAlign: 'center', color: colors.textTertiary, fontSize: 12 }}>
            暂无自选股，点击上方 + 添加
          </div>
        ) : (
          symbols.map(code => (
            <div
              key={code}
              onClick={() => onSelect(code)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 10px', cursor: 'pointer', userSelect: 'none',
                fontSize: 13, fontFamily: 'monospace',
                background: code === activeSymbol
                  ? `${colors.accentBlue}22`
                  : 'transparent',
                borderLeft: code === activeSymbol
                  ? `3px solid ${colors.accentBlue}`
                  : '3px solid transparent',
                color: code === activeSymbol ? colors.accentBlue : colors.textSecondary,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                if (code !== activeSymbol) {
                  e.currentTarget.style.background = colors.hoverBg;
                }
              }}
              onMouseLeave={e => {
                if (code !== activeSymbol) {
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <Space size={4}>
                <StarOutlined style={{ fontSize: 11, color: code === activeSymbol ? '#F59E0B' : colors.textTertiary }} />
                <Text style={{ fontSize: 13, fontFamily: 'monospace', color: 'inherit' }}>{code}</Text>
              </Space>
              <Popconfirm
                title={`移除 ${code}?`}
                onConfirm={() => handleRemove(code)}
                okText="移除"
                cancelText="取消"
                placement="left"
                overlayStyle={{ fontSize: 12 }}
              >
                <CloseOutlined
                  style={{ fontSize: 10, color: colors.textTertiary, opacity: 0, transition: 'opacity 0.15s' }}
                  className="watchlist-close-icon"
                  onClick={e => e.stopPropagation()}
                />
              </Popconfirm>
            </div>
          ))
        )}
        <style>{`
          .watchlist-close-icon {
            opacity: 0 !important;
          }
          div[class*="flex"]:hover > .watchlist-close-icon,
          div[style*="position"]:hover .watchlist-close-icon,
          .ant-popconfirm-open .watchlist-close-icon {
            opacity: 0.6 !important;
          }
        `}</style>
      </div>

      {/* 底部提示 */}
      <div style={{
        padding: '4px 10px',
        borderTop: `1px solid ${colors.borderColor}`,
        fontSize: 11, color: colors.textTertiary, textAlign: 'center',
      }}>
        点击股票切换分析
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Tab 1: 个股K线 — 多周期K线图
// ═══════════════════════════════════════════════════════════════════

const PERIOD_OPTIONS = [
  { label: '日线', value: 'day' },
  { label: '周线', value: 'week' },
  { label: '月线', value: 'month' },
  { label: '1分', value: '1' },
  { label: '5分', value: '5' },
  { label: '15分', value: '15' },
  { label: '30分', value: '30' },
  { label: '60分', value: '60' },
];

interface KlineChartPanelProps {
  symbol: string;
  onSymbolChange: (s: string) => void;
}

const KlineChartPanel: React.FC<KlineChartPanelProps> = ({ symbol, onSymbolChange }) => {
  const { colors } = useTheme();
  const { message } = App.useApp();
  const [period, setPeriod] = useState('day');
  const [loading, setLoading] = useState(false);
  const [klineData, setKlineData] = useState<StockKlineDaily[]>([]);
  const [minuteData, setMinuteData] = useState<StockKlineMinute[]>([]);
  const [selectedIndicator, setSelectedIndicator] = useState<TechnicalIndicatorKey>('ma');
  const [vwmaData, setVwmaData] = useState<VolumeVwmaPoint[]>([]);
  const [vrData, setVrData] = useState<VolumeVrPoint[]>([]);
  const [volumeBiasData, setVolumeBiasData] = useState<VolumeBiasPoint[]>([]);

  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const periodRef = useRef(period);
  const [chartKey, setChartKey] = useState(0);

  const isMinute = ['1', '5', '15', '30', '60'].includes(period);

  /** 根据周期返回合适的起始日期范围，确保周线/月线有足够数据点 */
  const calcStartDate = (p: string): string => {
    if (p === 'month') return dayjs().subtract(5, 'year').format('YYYYMMDD');
    if (p === 'week') return dayjs().subtract(3, 'year').format('YYYYMMDD');
    if (isMinute) return dayjs().subtract(1, 'month').format('YYYYMMDD');
    return dayjs().subtract(1, 'year').format('YYYYMMDD');
  };

  // 周期切换：先同步清除旧数据 + 销毁 ECharts 实例，避免渲染帧承载脏数据
  const onPeriodChange = (val: string) => {
    try { chartInstance.current?.dispose(); } catch {}
    chartInstance.current = null;
    setKlineData([]);
    setMinuteData([]);
    setVwmaData([]);
    setVrData([]);
    setVolumeBiasData([]);
    setChartKey(k => k + 1);  // 自增 key 强制重建图表 DOM，彻底避免 ECharts 实例残留
    setPeriod(val);
  };

  const load = useCallback(async (force = false) => {
    if (!symbol) return;
    // 先清除旧数据，避免异步等待期间 chartData 仍携带上一周期/股票数据导致渲染脏数据
    setKlineData([]);
    setMinuteData([]);
    setVwmaData([]);
    setVrData([]);
    setVolumeBiasData([]);
    setLoading(true);
    try {
      const endDate = dayjs().format('YYYYMMDD');
      const startDate = calcStartDate(period);

      if (isMinute) {
        const data = await klineAnalysisApi.getMinuteKline(symbol, period, startDate, endDate, force);
        setMinuteData(data || []);
      } else {
        const freqMap: Record<string, 'daily' | 'weekly' | 'monthly'> = { day: 'daily', week: 'weekly', month: 'monthly' };
        const data = await klineAnalysisApi.getKline(symbol, freqMap[period], startDate, endDate, force);
        setKlineData(data || []);
      }
    } catch (e: any) {
      message.error('K线数据加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol, period, isMinute]);

  useEffect(() => { load(); }, [load]);

  // ── 量能指标数据加载（selectedIndicator === 'vol' 时并行加载全部后端量能指标） ──
  useEffect(() => {
    if (!symbol || isMinute) return;
    const endDate = dayjs().format('YYYYMMDD');
    const startDate = calcStartDate(period);

    const loadVolumeData = async () => {
      try {
        if (selectedIndicator === 'vol') {
          // 并行加载全部三个量能指标
          const [vwma, vr, bias] = await Promise.all([
            klineAnalysisApi.getVwma(symbol, 20, startDate, endDate),
            klineAnalysisApi.getVr(symbol, 26, startDate, endDate),
            klineAnalysisApi.getVolumeBias(symbol, '5,10,20', startDate, endDate),
          ]);
          setVwmaData(vwma || []);
          setVrData(vr || []);
          setVolumeBiasData(bias || []);
        }
      } catch (e: any) {
        // 静默失败，不阻塞主图表渲染
      }
    };
    loadVolumeData();
  }, [symbol, selectedIndicator, isMinute, period]);

  // ── 图表数据处理 ──
  const chartData = useMemo(() => {
    if (isMinute) {
      const m = minuteData;
      if (!m || m.length === 0) return { dates: [], ohlc: [] as number[][], volumes: [] as number[], amounts: [] as number[] };
      const sorted = [...m].sort((a, b) => String(a.datetime).localeCompare(String(b.datetime)));
      return {
        dates: sorted.map((r) => r.datetime || ''),
        ohlc: sorted.map((r) => [r.open ?? 0, r.close ?? 0, r.low ?? 0, r.high ?? 0]),
        volumes: sorted.map((r) => r.volume ?? 0),
        amounts: [] as number[],
      };
    }
    const k = klineData;
    if (!k || k.length === 0) return { dates: [], ohlc: [] as number[][], volumes: [] as number[], amounts: [] as number[] };
    const sorted = [...k].sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
    return {
      dates: sorted.map((r) => r.trade_date),
      ohlc: sorted.map((r) => [r.open_price, r.close_price, r.low_price, r.high_price]),
      volumes: sorted.map((r) => r.volume || 0),
      amounts: sorted.map((r) => r.amount || 0),
    };
  }, [klineData, minuteData, isMinute]);

  // ── 前端标准化技术指标计算 ──
  const indicators = useMemo(() => {
    const points: OhlcPoint[] = chartData.ohlc.map((item, index) => ({
      open: item[0],
      close: item[1],
      low: item[2],
      high: item[3],
      volume: chartData.volumes[index] ?? 0,
    }));
    const closes = points.map((item) => item.close);
    const macd = calcMACD(closes);
    const kdj = calcKDJ(points);
    const boll = calcBOLL(closes);

    return {
      ma5: calcMA(5, closes),
      ma10: calcMA(10, closes),
      ma20: calcMA(20, closes),
      ma60: calcMA(60, closes),
      bollMA: boll.middle,
      bollUpper: boll.upper,
      bollLower: boll.lower,
      dif: macd.dif,
      dea: macd.dea,
      macdBar: macd.histogram,
      k: kdj.k,
      d: kdj.d,
      j: kdj.j,
      rsi6: calcRSI(closes, 6),
      rsi12: calcRSI(closes, 12),
      rsi24: calcRSI(closes, 24),
    };
  }, [chartData]);

  useEffect(() => {
    if (!chartRef.current || chartData.dates.length === 0) return;

    // ── 周期切换检测：如果 period 变化，先销毁旧图表实例再重建 ──
    if (periodRef.current !== period) {
      periodRef.current = period;
      try { chartInstance.current?.dispose(); } catch {}
      chartInstance.current = null;
    }

    const { dates, ohlc, volumes } = chartData;
    const { ma5, ma10, ma20, ma60, dif, dea, macdBar, k, d, j, rsi6, rsi12, rsi24, bollMA, bollUpper, bollLower } = indicators;

    // ── 量能指标数据 → 日期索引 Map（用于 series 和 tooltip） ──
    const vwmaMap = new Map(vwmaData.map((r) => [r.trade_date, r.vwma]));
    const vrMap = new Map(vrData.map((r) => [r.trade_date, r.vr]));
    const volumeBiasMap5 = new Map(volumeBiasData.map((r) => [r.trade_date, r.volume_bias_5]));
    const volumeBiasMap10 = new Map(volumeBiasData.map((r) => [r.trade_date, r.volume_bias_10]));
    const volumeBiasMap20 = new Map(volumeBiasData.map((r) => [r.trade_date, r.volume_bias_20]));

    // 对齐 dates 的辅助函数：按 trade_date 从 map 取值
    const getMapped = (date: string, map: Map<string, number>): number | null => map.get(date) ?? null;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const inst = chartInstance.current;

    const isMainOverlay = isMinute || selectedIndicator === 'ma' || selectedIndicator === 'boll';
    const hasSub = !isMainOverlay;
    // 分钟模式下始终需要第二个 grid（成交量）
    const actualHasSub = isMinute ? true : hasSub;
    const mainGridHeight = actualHasSub ? '50%' : '78%';
    const subGridTop = '58%';
    const subGridHeight = '34%';
    // 需要主图右侧 Y 轴（非 MA/BOLL 且非分钟模式时，将指标曲线叠加到主图上）
    const needsMainRightAxis = hasSub;
    // Y轴索引偏移：当存在主图右轴时，副图 yAxisIndex 整体 +1
    const overlayYIndex = 1;                               // 主图叠加右轴索引
    const subYIndex = needsMainRightAxis ? 2 : 1;          // 副图左轴索引
    const subYRightIndex = needsMainRightAxis ? 3 : 2;     // 副图右轴索引（仅 VOL）

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: false,
      legend: {
        data: isMinute
          ? ['收盘价', '成交量']
          : selectedIndicator === 'ma'
            ? ['MA5', 'MA10', 'MA20', 'MA60']
            : selectedIndicator === 'boll'
              ? ['BOLL MID', 'BOLL UPPER', 'BOLL LOWER']
              : selectedIndicator === 'macd'
                ? ['DIF', 'DEA', 'MACD']
                : selectedIndicator === 'kdj'
                  ? ['K', 'D', 'J']
                  : selectedIndicator === 'rsi'
                    ? ['RSI6', 'RSI12', 'RSI24']
                    : ['VOL', 'VWMA', 'VR', 'BIAS5', 'BIAS10', 'BIAS20'],
        textStyle: { color: colors.textSecondary, fontSize: 11 },
        top: 0, left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(20,20,40,0.92)',
        borderColor: 'rgba(102,126,234,0.5)',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0]?.dataIndex ?? 0;
          const o = ohlc[idx];
          if (!o) return '';
          const color = o[1] >= o[0] ? '#ff4d4f' : '#52c41a';

          // 基础 K 线信息
          let html = `<div style="padding:8px">
            <div style="font-weight:600;margin-bottom:6px">${dates[idx]}</div>
            <div style="display:flex;justify-content:space-between;gap:20px">
              <span>开: <span style="color:${color}">${o[0].toFixed(2)}</span></span>
              <span>收: <span style="color:${color}">${o[1].toFixed(2)}</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:20px;margin-top:4px">
              <span>高: <span style="color:#ff4d4f">${o[3].toFixed(2)}</span></span>
              <span>低: <span style="color:#52c41a">${o[2].toFixed(2)}</span></span>
            </div>
            <div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
              量: ${fmtVol(volumes[idx])}
            </div>`;

          // 附加技术指标数值
          if (!isMinute && selectedIndicator === 'boll') {
            const mid = bollMA[idx];
            const upper = bollUpper[idx];
            const lower = bollLower[idx];
            if (mid != null) {
              html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
                <span style="color:#56A4FF">中轨</span>: <span>${mid.toFixed(2)}</span><br/>
                <span style="color:#A78BFA">上轨</span>: <span>${upper != null ? upper.toFixed(2) : '-'}</span><br/>
                <span style="color:#A78BFA">下轨</span>: <span>${lower != null ? lower.toFixed(2) : '-'}</span>
              </div>`;
            }
          }
          if (!isMinute && selectedIndicator === 'ma') {
            const v5 = ma5[idx];
            const v10 = ma10[idx];
            const v20 = ma20[idx];
            const v60 = ma60[idx];
            if (v5 != null) {
              html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
                <span style="color:#F59E0B">MA5</span>: ${v5.toFixed(2)}&nbsp;&nbsp;
                <span style="color:#56A4FF">MA10</span>: ${v10 != null ? v10.toFixed(2) : '-'}<br/>
                <span style="color:#A78BFA">MA20</span>: ${v20 != null ? v20.toFixed(2) : '-'}&nbsp;&nbsp;
                <span style="color:#10B981">MA60</span>: ${v60 != null ? v60.toFixed(2) : '-'}
              </div>`;
            }
          }
          if (!isMinute && selectedIndicator === 'macd') {
            const d = dif[idx];
            const e = dea[idx];
            const bar = macdBar[idx];
            if (d != null) {
              html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
                <span style="color:#F59E0B">DIF</span>: ${d.toFixed(4)}&nbsp;&nbsp;
                <span style="color:#56A4FF">DEA</span>: ${e != null ? e.toFixed(4) : '-'}<br/>
                MACD: <span style="${bar != null ? (bar >= 0 ? 'color:#ff4d4f' : 'color:#52c41a') : ''}">${bar != null ? bar.toFixed(4) : '-'}</span>
              </div>`;
            }
          }
          if (!isMinute && selectedIndicator === 'kdj') {
            const kv = k[idx];
            const dv = d[idx];
            const jv = j[idx];
            if (kv != null) {
              html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
                <span style="color:#F59E0B">K</span>: ${kv.toFixed(2)}&nbsp;&nbsp;
                <span style="color:#56A4FF">D</span>: ${dv != null ? dv.toFixed(2) : '-'}<br/>
                <span style="color:#A78BFA">J</span>: ${jv != null ? jv.toFixed(2) : '-'}
              </div>`;
            }
          }
          if (!isMinute && selectedIndicator === 'rsi') {
            const v6 = rsi6[idx];
            const v12 = rsi12[idx];
            const v24 = rsi24[idx];
            if (v6 != null) {
              html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
                <span style="color:#F59E0B">RSI6</span>: ${v6.toFixed(2)}&nbsp;&nbsp;
                <span style="color:#56A4FF">RSI12</span>: ${v12 != null ? v12.toFixed(2) : '-'}<br/>
                <span style="color:#A78BFA">RSI24</span>: ${v24 != null ? v24.toFixed(2) : '-'}
              </div>`;
            }
          }
          // vol 模式下附加全部量能指标数值
          if (!isMinute && selectedIndicator === 'vol') {
            const vw = getMapped(dates[idx], vwmaMap);
            const vr = getMapped(dates[idx], vrMap);
            const b5 = getMapped(dates[idx], volumeBiasMap5);
            const b10 = getMapped(dates[idx], volumeBiasMap10);
            const b20 = getMapped(dates[idx], volumeBiasMap20);
            html += `<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">`;
            if (vw != null) html += `<span style="color:#56A4FF">VWMA(20)</span>: ${vw.toFixed(2)}&nbsp;&nbsp;`;
            if (vr != null) html += `<span style="color:#F59E0B">VR(26)</span>: ${vr.toFixed(2)}<br/>`;
            if (b5 != null) html += `<span style="color:#F59E0B">BIAS5</span>: ${b5.toFixed(2)}%&nbsp;&nbsp;`;
            if (b10 != null) html += `<span style="color:#56A4FF">BIAS10</span>: ${b10.toFixed(2)}%<br/>`;
            if (b20 != null) html += `<span style="color:#A78BFA">BIAS20</span>: ${b20.toFixed(2)}%`;
            html += `</div>`;
          }

          html += `</div>`;
          return html;
        },
      },
      grid: [
        { left: 50, right: needsMainRightAxis ? 55 : 20, top: 30, height: mainGridHeight },
        ...(actualHasSub ? [{ left: 50, right: selectedIndicator === 'vol' ? 55 : 20, top: subGridTop, height: subGridHeight }] : []),
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { show: false } },
        ...(actualHasSub ? [{ type: 'category' as const, gridIndex: 1, data: dates, boundaryGap: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { show: false }, splitLine: { show: false } }] : []),
      ],
      yAxis: [
        { scale: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } } },
        ...(needsMainRightAxis
          ? [{ gridIndex: 0, scale: true, position: 'right' as const, axisLine: { show: false }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { show: false } }]
          : []),
        ...(actualHasSub
          ? selectedIndicator === 'vol'
            ? [
                // vol 模式：左 y 轴（成交量柱），右 y 轴（VWMA/VR/BIAS 曲线）
                { gridIndex: 1, scale: true, position: 'left', axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { show: false } },
                { gridIndex: 1, scale: true, position: 'right', axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { show: false } },
              ]
            : [{ gridIndex: 1, scale: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } } }]
          : []),
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: actualHasSub ? [0, 1] : [0], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: actualHasSub ? [0, 1] : [0], start: 0, end: 100, height: 18, bottom: 4, textStyle: { color: colors.textTertiary, fontSize: 10 } },
      ],
      series: (() => {
        const s: any[] = [];

        if (isMinute) {
          // 分钟级K线：展示收盘价的平滑曲线（数值型 smooth 提高贝塞尔插值力度）
          const closes = ohlc.map((o) => o[1]);
          s.push({
            name: '收盘价', type: 'line', data: closes, smooth: 0.45, symbol: 'none',
            lineStyle: { width: 2, color: '#ff4d4f' },
            areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(255,77,79,0.12)' }, { offset: 1, color: 'rgba(255,77,79,0)' }] } },
          });
          // 增加成交量柱状图（浅色，贴合分钟线场景）
          s.push({
            name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: subYIndex,
            data: volumes.map((v, i) => ({ value: v, itemStyle: { color: ohlc[i][1] >= ohlc[i][0] ? 'rgba(255,77,79,0.5)' : 'rgba(82,196,26,0.5)', opacity: 0.7 } })),
          });
        } else {
          s.push({ name: 'K线', type: 'candlestick', data: ohlc, itemStyle: { color: '#ff4d4f', color0: '#52c41a', borderColor: '#ff4d4f', borderColor0: '#52c41a' } });
        }

        if (selectedIndicator === 'ma') {
          s.push({ name: 'MA5', type: 'line', data: ma5, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'MA10', type: 'line', data: ma10, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'MA20', type: 'line', data: ma20, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } });
          s.push({ name: 'MA60', type: 'line', data: ma60, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#10B981' } });
        }
        if (selectedIndicator === 'boll') {
          s.push({ name: 'BOLL MID', type: 'line', data: bollMA, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'BOLL UPPER', type: 'line', data: bollUpper, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA', type: 'dashed' as const } });
          s.push({ name: 'BOLL LOWER', type: 'line', data: bollLower, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA', type: 'dashed' as const } });
        }
        if (selectedIndicator === 'vol') {
          s.push({ name: 'VOL', type: 'bar', xAxisIndex: 1, yAxisIndex: subYIndex, data: volumes.map((v, i) => ({ value: v, itemStyle: { color: ohlc[i][1] >= ohlc[i][0] ? '#ff4d4f' : '#52c41a', opacity: 0.75 } })) });
          // vol 模式下量能曲线副图全部走右轴
          const vwmaLine = dates.map((d) => getMapped(d, vwmaMap));
          const vrLine = dates.map((d) => getMapped(d, vrMap));
          const bias5Line = dates.map((d) => getMapped(d, volumeBiasMap5));
          const bias10Line = dates.map((d) => getMapped(d, volumeBiasMap10));
          const bias20Line = dates.map((d) => getMapped(d, volumeBiasMap20));
          // 副图：量能曲线走右轴
          s.push({ name: 'VWMA', type: 'line', xAxisIndex: 1, yAxisIndex: subYRightIndex, data: vwmaLine, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'VR', type: 'line', xAxisIndex: 1, yAxisIndex: subYRightIndex, data: vrLine, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#F59E0B' } });
          s.push({ name: 'BIAS5', type: 'line', xAxisIndex: 1, yAxisIndex: subYRightIndex, data: bias5Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'BIAS10', type: 'line', xAxisIndex: 1, yAxisIndex: subYRightIndex, data: bias10Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'BIAS20', type: 'line', xAxisIndex: 1, yAxisIndex: subYRightIndex, data: bias20Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } });
          // 主图叠加：量能曲线同步显示在上方 K 线图（右轴）
          s.push({ name: 'VWMA', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: vwmaLine, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'VR', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: vrLine, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#F59E0B' } });
          s.push({ name: 'BIAS5', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: bias5Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'BIAS10', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: bias10Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'BIAS20', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: bias20Line, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } });
        }
        if (selectedIndicator === 'macd') {
          s.push({ name: 'MACD', type: 'bar', xAxisIndex: 1, yAxisIndex: subYIndex, data: macdBar.map((v) => ({ value: v, itemStyle: { color: (typeof v === 'number' && v >= 0) ? '#ff4d4f' : '#52c41a', opacity: 0.8 } })) });
          // 主图叠加：DIF/DEA 曲线走主图右轴
          s.push({ name: 'DIF', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: dif, showSymbol: false, lineStyle: { width: 1.5, color: '#F59E0B' } });
          s.push({ name: 'DEA', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: dea, showSymbol: false, lineStyle: { width: 1.5, color: '#56A4FF' } });
          // 副图：DIF/DEA + 零轴（保持副图可读性）
          s.push({ name: 'DIF', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: dif, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'DEA', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: dea, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: '零轴', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: dates.map(() => 0), showSymbol: false, silent: true, lineStyle: { width: 1, color: colors.borderColor, type: 'dashed' as const } });
        }
        if (selectedIndicator === 'kdj') {
          // 主图叠加：K/D/J 曲线走主图右轴
          s.push({ name: 'K', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: k, showSymbol: false, lineStyle: { width: 1.5, color: '#F59E0B' } });
          s.push({ name: 'D', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: d, showSymbol: false, lineStyle: { width: 1.5, color: '#56A4FF' } });
          s.push({ name: 'J', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: j, showSymbol: false, lineStyle: { width: 1.5, color: '#A78BFA' } });
          // 副图：K/D/J 保持
          s.push({ name: 'K', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: k, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'D', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: d, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'J', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: j, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } });
        }
        if (selectedIndicator === 'rsi') {
          // 主图叠加：RSI 曲线走主图右轴
          s.push({ name: 'RSI6', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: rsi6, showSymbol: false, lineStyle: { width: 1.5, color: '#F59E0B' } });
          s.push({ name: 'RSI12', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: rsi12, showSymbol: false, lineStyle: { width: 1.5, color: '#56A4FF' } });
          s.push({ name: 'RSI24', type: 'line', xAxisIndex: 0, yAxisIndex: overlayYIndex, data: rsi24, showSymbol: false, lineStyle: { width: 1.5, color: '#A78BFA' } });
          // 副图：RSI 保持
          s.push({ name: 'RSI6', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: rsi6, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } });
          s.push({ name: 'RSI12', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: rsi12, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } });
          s.push({ name: 'RSI24', type: 'line', xAxisIndex: 1, yAxisIndex: subYIndex, data: rsi24, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } });
        }
        return s;
      })(),
    };

    inst.setOption(option, true);
  }, [chartData, colors, indicators, selectedIndicator, period, vwmaData, vrData, volumeBiasData]);

  useEffect(() => {
    // 仅管理 resize 事件（图表实例在渲染 effect 中按需销毁重建）
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); };
  }, []);

  useEffect(() => {
    return () => { try { chartInstance.current?.dispose(); } catch {} chartInstance.current = null; };
  }, []);

  return (
    <Spin spinning={loading} style={{ width: '100%' }}>
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        <Col span={8}>
          <Input
            prefix={<SearchOutlined style={{ color: colors.textTertiary }} />}
            placeholder="输入股票代码，如 000001"
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value)}
            onPressEnter={() => load(true)}
            style={{ width: '100%' }} size="middle"
          />
        </Col>
        <Col span={8}>
          <Space>
            <Select value={period} onChange={onPeriodChange} size="middle" style={{ width: 100 }}
              options={PERIOD_OPTIONS}
            />
          </Space>
        </Col>
        <Col span={8} style={{ textAlign: 'right' }}>
          <Space>
            <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>
          </Space>
        </Col>
      </Row>

      <IndicatorSelector
        value={selectedIndicator}
        onChange={setSelectedIndicator}
        symbol={symbol}
        periodLabel={PERIOD_OPTIONS.find((item) => item.value === period)?.label}
        dataCount={chartData.dates.length}
      />

      {chartData.dates.length === 0 ? (
        <div style={{ height: 560, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${colors.borderColor}`, borderRadius: 6, background: colors.bgCard }}>
          <Empty description="暂无K线数据，请输入股票代码" />
        </div>
      ) : (
        <div key={chartKey} ref={chartRef} style={{ width: '100%', height: 580, background: colors.bgCard, border: `1px solid ${colors.borderColor}`, borderRadius: 6, padding: 4 }} />
      )}
    </Spin>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Tab 2: 技术指标 — 全指标数据面板
// ═══════════════════════════════════════════════════════════════════

interface IndicatorsPanelProps {
  symbol: string;
  onSymbolChange: (s: string) => void;
}

const IndicatorsPanel: React.FC<IndicatorsPanelProps> = ({ symbol, onSymbolChange }) => {
  const { colors } = useTheme();
  const { message } = App.useApp();
  const { containerRef, scrollY } = useTableScrollY(140);
  const [loading, setLoading] = useState(false);
  const [indicatorData, setIndicatorData] = useState<IndicatorData[]>([]);
  const [latestIndicators, setLatestIndicators] = useState<IndicatorData | null>(null);

  const load = useCallback(async (force = false) => {
    if (!symbol) return;
    setLoading(true);
    try {
      const endDate = dayjs().format('YYYYMMDD');
      const startDate = dayjs().subtract(120, 'day').format('YYYYMMDD');
      const data = await klineAnalysisApi.getIndicators(symbol, startDate, endDate);
      const sorted = (data || []).sort((a, b) => String(b.trade_date).localeCompare(String(a.trade_date)));
      setIndicatorData(sorted);
      setLatestIndicators(sorted[0] || null);
    } catch (e: any) {
      message.error('技术指标加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { load(); }, [load]);

  const renderOverbought = (value: number | undefined | null, low = 20, high = 80) => {
    if (value == null) return null;
    return (
      <Tag color={value > high ? 'red' : value < low ? 'green' : 'blue'} style={{ marginLeft: 4 }}>
        {value > high ? '超买' : value < low ? '超卖' : '正常'}
      </Tag>
    );
  };

  const indicatorSummaryCards = useMemo(() => {
    if (!latestIndicators) return null;
    const l = latestIndicators;
    return (
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="MA5 / MA20" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 14, color: colors.textPrimary }}>{fmtPrice(l.ma_5)} / {fmtPrice(l.ma_20)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textTertiary }}>
                    {(l.ma_5 != null && l.ma_20 != null)
                      ? (l.ma_5 > l.ma_20 ? <span style={{ color: '#ff4d4f' }}>多头排列</span> : <span style={{ color: '#52c41a' }}>空头排列</span>)
                      : '--'}
                  </Text>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="MACD" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 14, color: pctColor(l.macd_bar) }}>{fmtPrice(l.macd_bar, 3)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textTertiary }}>
                    {l.macd_bar != null ? (l.macd_bar > 0 ? '多头' : '空头') : '--'}
                  </Text>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="KDJ(K/D/J)" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 13, color: colors.textPrimary }}>{fmtPrice(l.kdj_k)} / {fmtPrice(l.kdj_d)} / {fmtPrice(l.kdj_j)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textTertiary }}>{l.kdj_j != null && (l.kdj_j > 100 ? '超买' : l.kdj_j < 0 ? '超卖' : '正常')}</Text>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="RSI(6/12)" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 14, color: colors.textPrimary }}>{fmtPrice(l.rsi_6)} / {fmtPrice(l.rsi_12)}</Text>
                  <span>{renderOverbought(l.rsi_6)}</span>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="CCI" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 16, color: pctColor(l.cci) }}>{fmtPrice(l.cci)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textTertiary }}>
                    {l.cci != null ? (l.cci > 100 ? '超买' : l.cci < -100 ? '超卖' : '正常') : '--'}
                  </Text>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
            <Statistic title="BOLL(width)" value={'' as any} valueStyle={{ fontSize: 0 }}
              formatter={() => (
                <Space direction="vertical" size={2}>
                  <Text style={{ fontSize: 14, color: colors.textPrimary }}>{fmtPrice(l.boll_width, 3)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textTertiary }}>
                    {l.close_price != null && l.boll_upper != null && l.boll_lower != null
                      ? (l.close_price > l.boll_upper ? '突破上轨' : l.close_price < l.boll_lower ? '跌破下轨' : '轨内') : '--'}
                  </Text>
                </Space>
              )}
            />
          </Card>
        </Col>
      </Row>
    );
  }, [latestIndicators, colors]);

  const columns = useMemo(() => [
    { title: '日期', dataIndex: 'trade_date', width: 85, fixed: 'left' as const },
    { title: 'MA5', dataIndex: 'ma_5', width: 75, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'MA10', dataIndex: 'ma_10', width: 80, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'MA20', dataIndex: 'ma_20', width: 80, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'DIF', dataIndex: 'macd_dif', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPrice(v, 3)}</Text> },
    { title: 'DEA', dataIndex: 'macd_dea', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPrice(v, 3)}</Text> },
    { title: 'MACD', dataIndex: 'macd_bar', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPrice(v, 3)}</Text> },
    { title: 'K', dataIndex: 'kdj_k', width: 70, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'D', dataIndex: 'kdj_d', width: 70, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'J', dataIndex: 'kdj_j', width: 70, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v != null ? v - 50 : null) }}>{fmtPrice(v)}</Text> },
    { title: 'RSI6', dataIndex: 'rsi_6', width: 70, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'RSI12', dataIndex: 'rsi_12', width: 75, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'CCI', dataIndex: 'cci', width: 75, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPrice(v)}</Text> },
    { title: 'BIAS6', dataIndex: 'bias_6', width: 75, align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{v?.toFixed(2)}%</Text> },
    { title: 'BOLL上轨', dataIndex: 'boll_upper', width: 80, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'BOLL中轨', dataIndex: 'boll_ma', width: 80, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'BOLL下轨', dataIndex: 'boll_lower', width: 80, align: 'right' as const, render: (v: number) => fmtPrice(v) },
    { title: 'OBV', dataIndex: 'obv', width: 90, align: 'right' as const, render: (v: number) => fmtVol(v) },
  ], []);

  return (
    <Spin spinning={loading} style={{ width: '100%' }}>
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}>
          <Input
            prefix={<SearchOutlined style={{ color: colors.textTertiary }} />}
            placeholder="输入股票代码"
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value)}
            onPressEnter={() => load(true)} size="middle"
          />
        </Col>
        <Col>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>
        </Col>
      </Row>
      {indicatorSummaryCards}
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden' }}>
        <Table size="small" columns={columns} dataSource={indicatorData}
          scroll={{ x: 1400, y: scrollY }}
          pagination={{ defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '30', '50', '100'], showTotal: (t) => `共 ${t} 条` }}
          rowKey={(r) => r.trade_date} className="kline-fixed-table" style={{ fontSize: 12 }} />
      </div>
    </Spin>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Tab 3: 实时行情 — 选中个股日内分时曲线（同花顺风格）
// ═══════════════════════════════════════════════════════════════════

interface RealtimeQuotesPanelProps {
  symbol: string;
  onSymbolChange: (s: string) => void;
}

/** 截取 sh/sz/bj 前缀后的纯数字代码 */
const stripSymbolPrefix = (code: string): string =>
  code.replace(/^(sh|sz|bj|SH|SZ|BJ)/i, '');

const RealtimeQuotesPanel: React.FC<RealtimeQuotesPanelProps> = ({ symbol, onSymbolChange }) => {
  const { colors } = useTheme();

  // ── 状态 ──
  const [activeSymbol, setActiveSymbol] = useState<string>(symbol || '');
  const [activeName, setActiveName] = useState<string>('');
  const [quote, setQuote] = useState<any>(null);
  const [minuteKlineData, setMinuteKlineData] = useState<StockKlineMinute[]>([]);
  const [transactionData, setTransactionData] = useState<TransactionItem[]>([]);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [loadingChart, setLoadingChart] = useState(false);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [transactionLoadingText, setTransactionLoadingText] = useState('');
  const [updateTime, setUpdateTime] = useState('');
  const [tickDate, setTickDate] = useState(() => dayjs().format('YYYYMMDD'));
  const [errorMsg, setErrorMsg] = useState<string>('');
  /** 右侧逐笔交易面板展开/收起状态（默认收起） */
  const [transactionPanelVisible, setTransactionPanelVisible] = useState(false);
  /** 缓存已拉取的 (symbol_date)，避免重复请求 */
  const transactionCacheRef = useRef<string>('');
  /** 缓存拉取时的数据条数，用于避免 render-loop */
  const transactionCountRef = useRef<number>(0);

  // 当父级 symbol prop 变化时同步
  useEffect(() => {
    if (symbol) setActiveSymbol(symbol);
  }, [symbol]);

  // ── 加载选中股票实时行情（仅用于取 prevClose 等概览信息） ──
  const loadQuote = useCallback(async (force = false) => {
    if (!activeSymbol) return;
    setLoadingQuote(true);
    setErrorMsg('');
    try {
      const result = await klineAnalysisApi.getRealtimeQuotes([activeSymbol], force);
      if (result.success && result.data) {
        // API 返回的 key 不带 sh/sz 前缀，需同时尝试原始 key 和去前缀 key
        const q = result.data[activeSymbol] || result.data[stripSymbolPrefix(activeSymbol)];
        if (q) {
          setQuote(q);
          setActiveName(q?.name || activeName);
          if (result.update_time) setUpdateTime(result.update_time);
        } else {
          setQuote(null);
          setErrorMsg(`${activeSymbol} 暂无实时行情数据（非交易日或已收盘）`);
        }
      } else {
        setQuote(null);
        setErrorMsg('实时行情数据请求失败');
      }
    } catch (e: any) {
      setQuote(null);
      setErrorMsg('实时行情加载失败: ' + e.message);
    } finally {
      setLoadingQuote(false);
    }
  }, [activeSymbol]);

  // ── 加载选中股票的 1 分钟 K 线（分时曲线数据源） ──
  const loadMinuteKline = useCallback(async (sym?: string, date?: string) => {
    const targetSymbol = sym || activeSymbol;
    const targetDate = date || tickDate;
    if (!targetSymbol || !targetDate) return;
    setLoadingChart(true);
    setErrorMsg('');
    try {
      // 分钟K线 API 要求不带 sh/sz 前缀的纯数字代码
      const pureCode = stripSymbolPrefix(targetSymbol);
      const data = await klineAnalysisApi.getMinuteKline(pureCode, '1', targetDate, targetDate);
      setMinuteKlineData(data || []);
      if (!data || data.length === 0) {
        setErrorMsg(`${targetSymbol} ${targetDate} 无分时数据（非交易日或数据尚未生成）`);
      }
    } catch (e: any) {
      setMinuteKlineData([]);
      setErrorMsg('分时数据加载失败: ' + e.message);
    } finally {
      setLoadingChart(false);
    }
  }, [activeSymbol, tickDate]);

  // ── 加载逐笔交易数据（新接口 /get-minute-tick，仅面板展开时调用） ──
  const loadTransactions = useCallback(async (sym?: string, date?: string) => {
    const targetSymbol = sym || activeSymbol;
    const targetDate = date || tickDate;
    if (!targetSymbol || !targetDate) return;

    // 检查缓存：已拉取过相同股票+日期的数据，无需重复请求
    const cacheKey = `${stripSymbolPrefix(targetSymbol)}_${targetDate}`;
    if (transactionCacheRef.current === cacheKey && transactionCountRef.current > 0) {
      setTransactionLoadingText(`${transactionCountRef.current} 条`);
      return;
    }

    setLoadingTransactions(true);
    setTransactionLoadingText('正在加载逐笔交易数据...');
    setErrorMsg('');
    try {
      const pureCode = stripSymbolPrefix(targetSymbol);
      const result = await klineAnalysisApi.getMinuteTickTransactions(pureCode, targetDate);
      if (result.success) {
        setTransactionData(result.data);
        transactionCacheRef.current = cacheKey;
        transactionCountRef.current = result.data.length;
        setTransactionLoadingText(result.data.length > 0 ? `${result.data.length} 条` : '');
        if (result.data.length === 0) {
          setErrorMsg(`${targetSymbol} ${targetDate} 暂无逐笔交易数据`);
        }
      } else {
        setTransactionData([]);
        transactionCountRef.current = 0;
        setTransactionLoadingText('');
        setErrorMsg(result.errorMsg || '逐笔交易数据加载失败');
      }
    } catch (e: any) {
      setTransactionData([]);
      transactionCountRef.current = 0;
      setTransactionLoadingText('');
      setErrorMsg('逐笔成交加载失败: ' + e.message);
    } finally {
      setLoadingTransactions(false);
    }
  }, [activeSymbol, tickDate]);

  // ── 切换面板可见时触发数据请求 ──
  const toggleTransactionPanel = useCallback(() => {
    setTransactionPanelVisible((prev) => {
      const nextVisible = !prev;
      // 展开面板时触发数据加载
      if (nextVisible) {
        // 使用 setTimeout 让面板先展开，再加载数据（避免 UI 卡顿）
        setTimeout(() => {
          loadTransactions();
        }, 0);
      }
      return nextVisible;
    });
  }, [loadTransactions]);

  // ── 面板隐藏状态复用：仅当面板可见时才调用 loadTransactions ──
  const loadTransactionsIfVisible = useCallback((sym?: string, date?: string) => {
    if (transactionPanelVisible) {
      loadTransactions(sym, date);
    } else {
      // 面板收起时，清空缓存标记，下次展开时触发重新加载
      transactionCacheRef.current = '';
    }
  }, [transactionPanelVisible, loadTransactions]);

  // 初始加载（仅加载行情和分钟K线，交易面板默认收起不加载）
  useEffect(() => {
    loadQuote();
    if (activeSymbol) {
      loadMinuteKline(activeSymbol);
    }
  }, []);

  // activeSymbol 变化时重新加载
  useEffect(() => {
    if (!activeSymbol) return;
    loadQuote();
    loadMinuteKline(activeSymbol, tickDate);
    // 交易面板：缓存标记清空，下次展开时触发重新加载
    transactionCacheRef.current = '';
  }, [activeSymbol]);

  useEffect(() => {
    if (!activeSymbol) return;
    loadMinuteKline(activeSymbol, tickDate);
    // 切换日期时：面板可能可见，清空缓存标记后重新加载
    transactionCacheRef.current = '';
    loadTransactionsIfVisible(activeSymbol, tickDate);
  }, [tickDate]);

  const prevClose = quote?.last_close ?? 0;

  // ── 核心价格区数据 ──
  const priceChange = quote ? (Number(quote.price) - Number(quote.last_close)) : 0;
  const priceChangePct = quote?.change_percent ?? 0;
  const isUp = priceChangePct > 0;
  const isDown = priceChangePct < 0;
  const pColor = isUp ? '#ff4d4f' : isDown ? '#52c41a' : '#999';

  // ── 股票名称描述 ──
  const stockLabel = activeName
    ? `${activeSymbol} · ${activeName}`
    : activeSymbol;

  const selectedDate = tickDate.length === 8
    ? dayjs(`${tickDate.slice(0, 4)}-${tickDate.slice(4, 6)}-${tickDate.slice(6, 8)}`)
    : dayjs();

  const transactionColumns = [
    { title: '时间', dataIndex: 'time_label', width: 68, render: (_: any, r: TransactionItem) => r.time_label || '--' },
    {
      title: '价格', dataIndex: 'price', width: 66, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor((Number(v) || 0) - prevClose), fontFamily: 'monospace', fontWeight: 500 }}>{fmtPrice(Number(v) || 0)}</Text>,
    },
    {
      title: '成交量', dataIndex: 'volume', width: 70, align: 'right' as const,
      render: (_: any, r: TransactionItem) => <span style={{ fontFamily: 'monospace', color: '#A0A0A5' }}>{fmtVol(Number(r.volume ?? r.vol ?? 0))}</span>,
    },
    { title: '笔数', dataIndex: 'num', width: 44, align: 'right' as const, render: (v: number | null) => v != null ? <span style={{ fontFamily: 'monospace', color: '#A0A0A5' }}>{v}</span> : '--' },
    {
      title: '方向', dataIndex: 'buyorsell', width: 52, align: 'center' as const,
      render: (v: number) => {
        const n = Number(v);
        const label = n === 0 ? '买盘' : n === 1 ? '卖盘' : '中性';
        const color = n === 0 ? '#ff4d4f' : n === 1 ? '#52c41a' : '#999';
        return <Tag color={n === 0 ? 'red' : n === 1 ? 'green' : 'default'} style={{ fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>{label}</Tag>;
      },
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <style>{`
        .transaction-row-hover:hover { background: rgba(37,37,40,0.8); }
        .transaction-row-hover td { padding: 2px 6px !important; }
      `}</style>
      <Spin spinning={loadingQuote || loadingChart || loadingTransactions} style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* ── 顶栏：股票切换 + 操作区 ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexShrink: 0,
          padding: '6px 10px', background: colors.bgCard, borderRadius: 6,
          border: `1px solid ${colors.borderColor}`,
        }}>
          <Text style={{ color: colors.textSecondary, fontSize: 13, whiteSpace: 'nowrap', fontWeight: 600 }}>
            选中: {stockLabel}
          </Text>
          <div style={{ flex: 1 }} />
          <Space size={4}>
            <DatePicker
              size="small"
              allowClear={false}
              value={selectedDate}
              format="YYYYMMDD"
              disabledDate={(current) => !!current && current.startOf('day').isAfter(dayjs().startOf('day'))}
              onChange={(date) => {
                const nextDate = (date || dayjs()).format('YYYYMMDD');
                setTickDate(nextDate);
              }}
              style={{ width: 120 }}
            />
            <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => { loadQuote(true); loadMinuteKline(activeSymbol, tickDate); transactionCacheRef.current = ''; loadTransactionsIfVisible(activeSymbol, tickDate); }}>
              刷新
            </Button>
            {updateTime && (
              <Text style={{ color: colors.textTertiary, fontSize: 11 }}>{updateTime}</Text>
            )}
            <Button
              size="small"
              type={transactionPanelVisible ? 'primary' : 'default'}
              icon={transactionPanelVisible ? <RightOutlined /> : <LeftOutlined />}
              onClick={toggleTransactionPanel}
            >
              {transactionPanelVisible ? '收起逐笔' : '逐笔成交'}
            </Button>
          </Space>
        </div>

        {/* ── 选中股票行情概览：三组卡片式布局 ── */}
        {quote && (
          <div style={{
            display: 'flex', gap: 6, marginBottom: 8, flexShrink: 0,
            padding: 0,
          }}>
            {/* ① 核心价格区：代码 + 价格 + 涨跌幅 */}
            <div style={{
              flex: '0 0 200px', background: colors.bgCard, borderRadius: 6,
              border: `1px solid ${colors.borderColor}`, padding: '8px 14px',
              display: 'flex', flexDirection: 'column', justifyContent: 'center',
            }}>
              <div style={{ fontSize: 12, color: colors.textTertiary, marginBottom: 2 }}>
                {activeName || activeSymbol}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontSize: 26, fontWeight: 700, color: pColor, fontFamily: 'monospace', lineHeight: 1.2 }}>
                  {fmtPrice(quote.price)}
                </span>
                <span style={{ fontSize: 15, fontWeight: 600, color: pColor }}>
                  {fmtPct(priceChangePct)}
                </span>
              </div>
              <div style={{ fontSize: 11, color: colors.textTertiary, marginTop: 1 }}>
                昨收 {fmtPrice(quote.last_close)}
              </div>
            </div>

            {/* ② 基础行情区：今开/昨收、最高/最低、成交量/成交额 */}
            <div style={{
              flex: 1, background: colors.bgCard, borderRadius: 6,
              border: `1px solid ${colors.borderColor}`, padding: '6px 14px',
              display: 'flex', alignItems: 'center', gap: 16,
            }}>
              <QuoteMiniGroup title="今开" value={fmtPrice(quote.open)} color={pctColor(Number(quote.open) - Number(quote.last_close))} />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="昨收" value={fmtPrice(quote.last_close)} color={colors.textSecondary} />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="最高" value={fmtPrice(quote.high)} color="#ff4d4f" />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="最低" value={fmtPrice(quote.low)} color="#52c41a" />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="成交量" value={fmtVol(quote.volume)} color="#56A4FF" />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="成交额" value={fmtVol(quote.amount)} color="#F59E0B" />
            </div>

            {/* ③ 盘口数据区：买一/卖一 */}
            <div style={{
              flex: '0 0 160px', background: colors.bgCard, borderRadius: 6,
              border: `1px solid ${colors.borderColor}`, padding: '6px 14px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <QuoteMiniGroup title="买一" value={fmtPrice(quote.bid1)} color="#ff4d4f" />
              <div style={{ width: 1, height: 28, background: colors.borderColor, opacity: 0.4 }} />
              <QuoteMiniGroup title="卖一" value={fmtPrice(quote.ask1)} color="#52c41a" />
            </div>
          </div>
        )}

        {/* ── 暂无可选框时显示提示 ── */}
        {!activeSymbol && (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: `1px solid ${colors.borderColor}`, borderRadius: 6, background: colors.bgCard,
          }}>
            <Empty description="请从左侧自选股列表选择一只股票" />
          </div>
        )}

        {/* ── 分时图 + 逐笔成交面板（默认收起，点击展开） ── */}
        {activeSymbol && (
          <div style={{
            flex: 1, minHeight: 0, width: '100%',
            display: 'grid',
            gridTemplateColumns: transactionPanelVisible
              ? 'minmax(0, 2.33fr) minmax(300px, 1fr)'
              : '1fr',
            gap: 6,
            transition: 'grid-template-columns 0.3s ease',
          }}>
            {/* ── 左侧：分时图 ── */}
            <div style={{ minHeight: 0, position: 'relative' }}>
              <IntradayChart
                data={minuteKlineData}
                prevClose={prevClose}
                symbol={activeSymbol}
                date={tickDate}
                loading={loadingChart}
              />
            </div>

            {/* ── 右侧：逐笔成交面板 ── */}
            {transactionPanelVisible && (
              <Card
                size="small"
                title={<Text style={{ fontSize: 13, fontWeight: 600 }}>逐笔成交</Text>}
                extra={<Text style={{ color: colors.textTertiary, fontSize: 11 }}>{transactionLoadingText || (transactionData.length > 0 ? `${transactionData.length} 条` : '')}</Text>}
                styles={{ body: { padding: 0 } }}
                style={{ minHeight: 0, width: '100%', background: colors.bgCard, borderColor: colors.borderColor }}
              >
                <Table
                  size="small"
                  rowKey={(r, idx) => `${r.symbol || activeSymbol}-${r.trade_date || tickDate}-${r.seq}-${r.time_label}-${r.price}-${r.volume}-${idx}`}
                  columns={transactionColumns}
                  dataSource={transactionData}
                  pagination={false}
                  scroll={{ y: 520 }}
                  locale={{ emptyText: `${tickDate} 暂无逐笔交易数据` }}
                  style={{ fontSize: 12 }}
                  rowClassName={() => 'transaction-row-hover'}
                  onRow={() => ({
                    style: { cursor: 'default' },
                  })}
                />
              </Card>
            )}
          </div>
        )}

        {/* ── 错误说明（非交易日/后端异常时展示） ── */}
        {errorMsg && (
          <div style={{ flexShrink: 0, marginTop: 8 }}>
            <Alert
              title={errorMsg}
              type="warning"
              showIcon
              closable
              onClose={() => setErrorMsg('')}
              style={{ fontSize: 12 }}
            />
          </div>
        )}
      </Spin>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Tab 4: K线采集 — 全市场K线采集管理
// ═══════════════════════════════════════════════════════════════════

const KlineCollectPanel: React.FC = () => {
  const { colors } = useTheme();
  const [collecting, setCollecting] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const addLog = (msg: string) => {
    setLog(prev => [...prev.slice(-199), `[${dayjs().format('HH:mm:ss')}] ${msg}`]);
  };

  const handleStartCollect = async () => {
    if (collecting) return;
    setCollecting(true);
    setProgress(null);
    setLog([]);
    addLog('发起全市场K线采集请求...');
    try {
      const result = await klineAnalysisApi.triggerKlineCollect('day');
      const taskId = result?.task_id || result?.data?.task_id;
      if (taskId) {
        addLog(`获取采集任务ID: ${taskId}，开始SSE监听...`);
        const sseUrl = STOCK_API.KLINE_SSE(taskId);
        const es = new EventSource(sseUrl);
        eventSourceRef.current = es;
        es.addEventListener('progress', (e: MessageEvent) => {
          try { const data = JSON.parse(e.data); setProgress({ current: data.current || 0, total: data.total || 0 }); } catch { /* ignore */ }
        });
        es.addEventListener('stock', (e: MessageEvent) => {
          try { const data = JSON.parse(e.data); addLog(`完成: ${data.symbol} ${data.name || ''} (${data.period})`); } catch { /* ignore */ }
        });
        es.addEventListener('complete', (e: MessageEvent) => {
          try { const data = JSON.parse(e.data); addLog(`✅ 采集完成！共处理 ${data.total_processed || '?'} 只股票`); } catch { /* ignore */ }
          es.close(); setCollecting(false); setProgress(null);
        });
        es.onerror = () => { addLog('⚠️ SSE连接异常，已断开'); es.close(); setCollecting(false); };
      } else {
        addLog(`采集已触发: ${JSON.stringify(result)}`);
        setTimeout(() => setCollecting(false), 2000);
      }
    } catch (e: any) {
      addLog(`❌ 采集触发失败: ${e.message}`);
      setCollecting(false);
    }
  };

  const handleStop = () => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setCollecting(false); setProgress(null);
    addLog('🛑 已手动停止采集');
  };

  useEffect(() => { return () => { eventSourceRef.current?.close(); }; }, []);

  return (
    <div style={{ padding: 8 }}>
      <Card style={{ background: colors.bgCard, borderColor: colors.borderColor, marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <ThunderboltOutlined style={{ fontSize: 20, color: '#F59E0B' }} />
              <Title level={5} style={{ margin: 0, color: colors.textPrimary }}>全市场K线数据采集</Title>
              <Tag color="orange">日线</Tag>
            </Space>
            <Space>
              {collecting ? <Button danger size="small" onClick={handleStop}>停止采集</Button>
                : <Button type="primary" size="small" icon={<ThunderboltOutlined />} onClick={handleStartCollect}>开始采集</Button>}
            </Space>
          </div>
          {progress && (
            <div style={{ marginTop: 8 }}>
              <Progress percent={Math.round((progress.current / Math.max(progress.total, 1)) * 100)}
                format={() => `${progress.current} / ${progress.total}`} strokeColor="#F59E0B" />
            </div>
          )}
          <div style={{ fontSize: 12, color: colors.textTertiary, lineHeight: 1.8 }}>
            <div>• 数据源：mootdx 通达信行情直连</div>
            <div>• 缓存策略：Redis → MySQL 分年表（三层架构）</div>
            <div>• 全市场约5000只A股，耗时约10-30分钟</div>
            <div>• 支持增量覆盖：已有数据跳过，仅补充缺失</div>
          </div>
        </Space>
      </Card>
      <Card size="small" title={<Space><ApiOutlined /><span style={{ fontSize: 13 }}>采集日志</span></Space>}
        style={{ background: colors.bgCard, borderColor: colors.borderColor }}
        extra={log.length > 0 ? <Button size="small" onClick={() => setLog([])}>清空</Button> : null}>
        <div style={{ height: 300, overflowY: 'auto', fontFamily: 'monospace', fontSize: 12, color: colors.textSecondary, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
          {log.length === 0
            ? <Text style={{ color: colors.textTertiary }}>暂无日志，点击"开始采集"启动全市场K线数据采集</Text>
            : log.map((line, i) => <div key={i}>{line}</div>)}
        </div>
      </Card>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  主组件
// ═══════════════════════════════════════════════════════════════════

const KlineAnalysis: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState('kline-chart');
  const [activeSymbol, setActiveSymbol] = useState(() => {
    const list = getWatchlist();
    return list[0] || '000001';
  });

  const handleSymbolChange = useCallback((s: string) => {
    setActiveSymbol(s);
  }, []);

  return (
    <div className="page-layout kline-page" style={{ height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
      {/* 页面标题 */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px', flexShrink: 0,
        borderBottom: `1px solid ${colors.borderColor}`,
        background: colors.bgSecondary,
      }}>
        <Space>
          <LineChartOutlined style={{ fontSize: 20, color: '#3B82F6' }} />
          <Title level={5} style={{ margin: 0, color: colors.textPrimary }}>K线分析</Title>
          <Tag color="blue" style={{ marginLeft: 4, fontSize: 11, lineHeight: '18px' }}>mootdx + ECharts</Tag>
          {activeSymbol && (
            <Text style={{
              marginLeft: 12, fontSize: 14, fontWeight: 600,
              fontFamily: 'monospace', color: colors.accentBlue,
            }}>
              {activeSymbol}
            </Text>
          )}
        </Space>
      </div>

      {/* 主体：左侧自选股侧列 + 右侧内容 */}
      <div className="flex-content" style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <WatchlistSidebar activeSymbol={activeSymbol} onSelect={handleSymbolChange} />

        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="small"
            type="card"
            style={{ height: '100%', padding: '0 12px' }}
            items={[
              {
                key: 'kline-chart',
                label: <span><BarChartOutlined /> 个股K线</span>,
                children: <KlineChartPanel symbol={activeSymbol} onSymbolChange={handleSymbolChange} />,
              },
              {
                key: 'indicators',
                label: <span><FieldNumberOutlined /> 技术指标</span>,
                children: <IndicatorsPanel symbol={activeSymbol} onSymbolChange={handleSymbolChange} />,
              },
              {
                key: 'realtime',
                label: <span><DollarOutlined /> 实时行情</span>,
                children: <RealtimeQuotesPanel symbol={activeSymbol} onSymbolChange={handleSymbolChange} />,
              },
              {
                key: 'collect',
                label: <span><ThunderboltOutlined /> K线采集</span>,
                children: <KlineCollectPanel />,
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
};

export default React.memo(KlineAnalysis);