/**
 * 行情与 K 线页面 - 独立子分类视图
 *
 * 对接后端接口：
 *   - GET /api/stock/get-stock-market-fund-flow        大盘资金流向（含指数行情）
 *   - GET /api/stock/get-stock-rank-lxsz-ths           连续上涨
 *   - GET /api/stock/get-stock-rank-lxxd-ths           连续下跌
 *   - GET /api/stock/get-stock-rank-ljqs-ths           量价齐升
 *   - GET /api/stock/get-stock-rank-ljqd-ths           量价齐跌
 *   - GET /api/stock/get-stock-account-statistics-em   股票账户月度统计
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Tabs, Table, Tag, Typography, Space, Spin, message, Button, Card, Row, Col, Statistic, Segmented } from 'antd';
import {
  LineChartOutlined,
  RiseOutlined,
  FallOutlined,
  StockOutlined,
  ReloadOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  TeamOutlined,
  DollarOutlined,
  BarChartOutlined,
  TableOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';
import { marketApi } from '@/api/stock';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { readDailyCache, writeDailyCache, clearDailyCache, TTL } from '@/utils/dailyCache';
import type {
  MarketFundFlow,
  StockConsecutiveStats,
  StockVolumePriceStats,
  InvestorMarketStats,
  BoardIndexKline,
} from '../../../types/stock';

const { Text, Title } = Typography;

// ─── 工具函数 ───────────────────────────────────────────────────

const fmtYi = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(2);
};

const fmtPct = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  return v.toFixed(2) + '%';
};

const fmtNum = (v: number | null | undefined, digits = 2): string => {
  if (v == null || isNaN(v)) return '--';
  return v.toFixed(digits);
};

const pctColor = (v: number | null | undefined): string => {
  if (v == null || isNaN(v) || v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

const fmtYiRaw = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2);
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2);
  return v.toFixed(2);
};

// ─── 大盘行情面板 ───────────────────────────────────────────────

const MarketIndexPanel: React.FC = () => {
  const { colors } = useTheme();
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(600);
  const [data, setData] = useState<MarketFundFlow[]>([]);
  const [klineData, setKlineData] = useState<BoardIndexKline[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [subIndicator, setSubIndicator] = useState<'volume' | 'macd' | 'kdj' | 'rsi'>('volume');

  const load = useCallback(async (force = false) => {
    const CK = 'kline:marketIndex';
    const KLINE_CK = 'kline:indexCandle';

    if (!force) {
      const cf = readDailyCache<MarketFundFlow[]>(CK);
      const ck = readDailyCache<BoardIndexKline[]>(KLINE_CK);
      if (cf) setData(cf);
      // 只当缓存有真实数据（非空数组）时才恢复 + 跳过请求
      if (ck && ck.length > 0) {
        setKlineData(ck);
        if (cf) return; // 两份都真实命中才跳过
      }
      // 缓存为空数组（以前的无参数请求遗留），清除它重新请求
      if (ck && ck.length === 0) clearDailyCache(KLINE_CK);
    }

    setLoading(true);
    try {
      const endDate = dayjs().format('YYYYMMDD');
      const startDate = dayjs().subtract(2, 'year').format('YYYYMMDD');
      const [list, kline] = await Promise.all([
        marketApi.getMarketFundFlow(),
        marketApi.getZhADaily('sh000001', startDate, endDate),
      ]);

      const sliced = [...(list || [])]
        .sort((a, b) => (b.trade_date || '').localeCompare(a.trade_date || ''))
        .slice(0, 120);
      const sortedKline = [...(kline || [])]
        .sort((a, b) => (a.trade_date || '').localeCompare(b.trade_date || ''));

      setData(sliced);
      setKlineData(sortedKline);
      writeDailyCache(CK, sliced);
      writeDailyCache(KLINE_CK, sortedKline);
    } catch (e: any) {
      message.error('大盘行情加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const latest = data[0];

  // ── 按 StockCenter 模式处理 K 线数据 ──
  const chartData = useMemo(() => {
    const sorted = [...klineData].sort((a, b) =>
      String(a.trade_date).localeCompare(String(b.trade_date))
    );
    return {
      dates: sorted.map((r) => r.trade_date),
      ohlc: sorted.map((r) => [r.open_price, r.close_price, r.low_price, r.high_price]),
      volumes: sorted.map((r) => r.volume || 0),
    };
  }, [klineData]);

  // ── 技术指标计算（前端侧，基于 OHLC 数据） ──
  const calcMA = (n: number, closes: number[]): (number | string)[] => {
    const result: (number | string)[] = [];
    for (let i = 0; i < closes.length; i++) {
      if (i < n - 1) { result.push('-'); continue; }
      let sum = 0;
      for (let j = 0; j < n; j++) sum += closes[i - j];
      result.push(+(sum / n).toFixed(2));
    }
    return result;
  };

  const indicators = useMemo(() => {
    const closes = chartData.ohlc.map((o) => o[1]); // close
    const highs = chartData.ohlc.map((o) => o[3]);
    const lows = chartData.ohlc.map((o) => o[2]);

    // MA
    const ma5 = calcMA(5, closes);
    const ma10 = calcMA(10, closes);
    const ma20 = calcMA(20, closes);
    const ma60 = calcMA(60, closes);

    // MACD (12, 26, 9)
    const ema12: number[] = [];
    const ema26: number[] = [];
    const dif: (number | string)[] = [];
    const dea: (number | string)[] = [];
    const macdBar: (number | string)[] = [];
    const a12 = 2 / 13, a26 = 2 / 27, a9 = 2 / 10;
    for (let i = 0; i < closes.length; i++) {
      ema12[i] = i === 0 ? closes[i] : a12 * closes[i] + (1 - a12) * ema12[i - 1];
      ema26[i] = i === 0 ? closes[i] : a26 * closes[i] + (1 - a26) * ema26[i - 1];
      const d = ema12[i] - ema26[i];
      dif[i] = i < 25 ? '-' : +d.toFixed(4);
      if (i < 25) { dea[i] = '-'; macdBar[i] = '-'; continue; }
      const prevDea = i === 25 ? d : (dea[i - 1] as number);
      const curDea = a9 * d + (1 - a9) * prevDea;
      dea[i] = +curDea.toFixed(4);
      macdBar[i] = +((d - curDea) * 2).toFixed(4);
    }

    // KDJ (9, 3, 3)
    const k: (number | string)[] = [];
    const d: (number | string)[] = [];
    const j: (number | string)[] = [];
    for (let i = 0; i < closes.length; i++) {
      if (i < 8) { k[i] = '-'; d[i] = '-'; j[i] = '-'; continue; }
      const hh = Math.max(...highs.slice(i - 8, i + 1));
      const ll = Math.min(...lows.slice(i - 8, i + 1));
      const rsv = hh === ll ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
      const prevK = i === 8 ? 50 : (k[i - 1] as number);
      const prevD = i === 8 ? 50 : (d[i - 1] as number);
      const curK = (2 / 3) * prevK + (1 / 3) * rsv;
      const curD = (2 / 3) * prevD + (1 / 3) * curK;
      k[i] = +curK.toFixed(2);
      d[i] = +curD.toFixed(2);
      j[i] = +(3 * curK - 2 * curD).toFixed(2);
    }

    // RSI (6, 12, 24)
    const calcRSI = (n: number): (number | string)[] => {
      const r: (number | string)[] = [];
      let upSum = 0, downSum = 0;
      for (let i = 0; i < closes.length; i++) {
        if (i === 0) { r[i] = '-'; continue; }
        const chg = closes[i] - closes[i - 1];
        const up = chg > 0 ? chg : 0;
        const down = chg < 0 ? -chg : 0;
        if (i < n) { upSum += up; downSum += down; r[i] = '-'; continue; }
        if (i === n) { upSum += up; downSum += down; }
        else {
          upSum = (upSum * (n - 1) + up) / n;
          downSum = (downSum * (n - 1) + down) / n;
        }
        const rs = downSum === 0 ? 100 : upSum / downSum;
        r[i] = +(100 - 100 / (1 + rs)).toFixed(2);
      }
      return r;
    };
    const rsi6 = calcRSI(6);
    const rsi12 = calcRSI(12);
    const rsi24 = calcRSI(24);

    return { ma5, ma10, ma20, ma60, dif, dea, macdBar, k, d, j, rsi6, rsi12, rsi24 };
  }, [chartData]);

  // ── 参考 StockCenter 模式：直接 ECharts init ──
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (viewMode !== 'chart' || !chartRef.current || chartData.dates.length === 0) return;
    const { dates, ohlc, volumes } = chartData;
    const { ma5, ma10, ma20, ma60, dif, dea, macdBar, k, d, j, rsi6, rsi12, rsi24 } = indicators;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const inst = chartInstance.current;

    // 副图数据（根据 subIndicator 切换）
    const hasSub = subIndicator !== 'volume';
    const subGrid = hasSub
      ? { left: 50, right: 20, top: '60%', height: '18%' }
      : { left: 50, right: 20, top: '72%', height: '20%' };

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: false,
      legend: {
        data: hasSub ? [] : ['MA5', 'MA10', 'MA20', 'MA60'],
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
          const d = klineData[idx];
          if (!d) return '';
          const color = d.close_price >= d.open_price ? '#ff4d4f' : '#52c41a';
          const prev = idx > 0 ? klineData[idx - 1] : null;
          const pct = prev ? ((d.close_price - prev.close_price) / prev.close_price * 100) : 0;
          const pctColor = pct >= 0 ? '#ff4d4f' : '#52c41a';
          const pctSign = pct >= 0 ? '+' : '';
          return `<div style="padding:8px">
            <div style="font-weight:600;margin-bottom:6px">${d.trade_date}</div>
            <div style="display:flex;justify-content:space-between;gap:20px">
              <span>开: <span style="color:${color};font-weight:600">${d.open_price.toFixed(2)}</span></span>
              <span>收: <span style="color:${color};font-weight:600">${d.close_price.toFixed(2)}</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:20px;margin-top:4px">
              <span>高: <span style="color:#ff4d4f;font-weight:600">${d.high_price.toFixed(2)}</span></span>
              <span>低: <span style="color:#52c41a;font-weight:600">${d.low_price.toFixed(2)}</span></span>
            </div>
            <div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
              涨跌幅: <span style="color:${pctColor};font-weight:700;font-size:14px">${pctSign}${pct.toFixed(2)}%</span>
              ${prev ? `<span style="color:${colors.textTertiary};margin-left:8px">昨收 ${prev.close_price.toFixed(2)}</span>` : ''}
            </div>
          </div>`;
        },
      },
      grid: [
        { left: 50, right: 20, top: 30, height: hasSub ? '50%' : '62%' },
        subGrid,
        ...(hasSub ? [{ left: 50, right: 20, top: '82%', height: '12%' }] : []),
      ],
      xAxis: [
        {
          type: 'category', data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10, showMaxLabel: true },
          splitLine: { show: false },
        },
        {
          type: 'category', gridIndex: 1, data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        ...(hasSub ? [{
          type: 'category' as const, gridIndex: 2, data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { show: false },
          splitLine: { show: false },
        }] : []),
      ],
      yAxis: [
        {
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10, formatter: (v: number) => v.toFixed(2) },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        },
        {
          gridIndex: 1, scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10,
            formatter: (v: number) => {
              if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '亿';
              if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万';
              return String(v);
            },
          },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        },
        ...(hasSub ? [{
          gridIndex: 2, scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10 },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        }] : []),
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1], start: 50, end: 100 },
        {
          type: 'slider', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1], start: 50, end: 100,
          height: 18, bottom: 4,
          textStyle: { color: colors.textTertiary, fontSize: 10 },
        },
      ],
      series: [
        {
          name: '上证指数',
          type: 'candlestick',
          data: ohlc,
          itemStyle: { color: '#ff4d4f', color0: '#52c41a', borderColor: '#ff4d4f', borderColor0: '#52c41a' },
        },
        // MA 均线（仅在 volume 副图模式下显示）
        ...(subIndicator === 'volume' ? [
          { name: 'MA5', type: 'line' as const, data: ma5, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'MA10', type: 'line' as const, data: ma10, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'MA20', type: 'line' as const, data: ma20, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
          { name: 'MA60', type: 'line' as const, data: ma60, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#34D399' } },
        ] : []),
        // 副图
        ...(subIndicator === 'volume' ? [{
          name: '成交量',
          type: 'bar' as const, xAxisIndex: 1, yAxisIndex: 1,
          data: volumes.map((v, i) => ({
            value: v,
            itemStyle: { color: ohlc[i][1] >= ohlc[i][0] ? '#ff4d4f' : '#52c41a', opacity: 0.75 },
          })),
        }] : []),
        ...(subIndicator === 'macd' ? [
          { name: 'DIF', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: dif, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'DEA', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: dea, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'MACD', type: 'bar' as const, xAxisIndex: 2, yAxisIndex: 2, data: macdBar.map((v, i) => ({
            value: v,
            itemStyle: { color: (typeof v === 'number' && v >= 0) ? '#ff4d4f' : '#52c41a', opacity: 0.8 },
          })) },
        ] : []),
        ...(subIndicator === 'kdj' ? [
          { name: 'K', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: k, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'D', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: d, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'J', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: j, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
        ] : []),
        ...(subIndicator === 'rsi' ? [
          { name: 'RSI6', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi6, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'RSI12', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi12, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'RSI24', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi24, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
        ] : []),
      ],
    };

    inst.setOption(option, true);
  }, [viewMode, chartData, colors, klineData, indicators, subIndicator]);

  // 视图切换 → 销毁实例，避免残留
  useEffect(() => {
    if (viewMode !== 'chart' && chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
    }
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, [viewMode]);

  // 卸载时清理
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  // ── 表格容器 ResizeObserver（解决条件渲染导致 useTableScrollY 丢失绑定） ──
  // 当 viewMode 切到 'table' 时，表格 div 才挂载，此时才绑定 observer
  useEffect(() => {
    if (viewMode !== 'table') return;
    const el = tableContainerRef.current;
    if (!el) return;

    const update = () => {
      const rect = el.getBoundingClientRect();
      // offset = 分页器高度(~40px) + 底部安全间距(~16px) + ant-table-header(~38px)
      const available = rect.height - 94;
      setScrollY(Math.max(200, Math.floor(available)));
    };

    update();
    const observer = new ResizeObserver(() => requestAnimationFrame(update));
    observer.observe(el);
    return () => observer.disconnect();
  }, [viewMode]);

  const columns = useMemo(() => [
    { title: '日期', dataIndex: 'trade_date', width: 100 },
    { title: '上证收盘', dataIndex: 'sh_close', width: 100, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '上证涨跌幅', dataIndex: 'sh_pct_change', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtPct(v)}</Text> },
    { title: '深证收盘', dataIndex: 'sz_close', width: 100, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '深证涨跌幅', dataIndex: 'sz_pct_change', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtPct(v)}</Text> },
    { title: '主力净流入', dataIndex: 'main_net_inflow', width: 110, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '主力净占比', dataIndex: 'main_net_inflow_pct', width: 95, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> },
    { title: '超大单净流入', dataIndex: 'super_large_net_inflow', width: 110, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '大单净流入', dataIndex: 'large_net_inflow', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '中单净流入', dataIndex: 'medium_net_inflow', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
    { title: '小单净流入', dataIndex: 'small_net_inflow', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v) }}>{fmtYi(v)}</Text> },
  ], []);

  return (
    <div className="kline-panel">
      <Spin spinning={loading} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {/* 最新交易日概览卡片 */}
        {latest && (
          <Row gutter={12} style={{ marginBottom: 12 }}>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="上证指数"
                  value={latest.sh_close?.toFixed(2)}
                  suffix={
                    <span style={{ fontSize: 14, color: pctColor(latest.sh_pct_change), marginLeft: 8 }}>
                      {latest.sh_pct_change != null && (latest.sh_pct_change > 0 ? '+' : '') + latest.sh_pct_change.toFixed(2) + '%'}
                    </span>
                  }
                  styles={{ content: { color: pctColor(latest.sh_pct_change), fontSize: 24, fontWeight: 700 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="深证成指"
                  value={latest.sz_close?.toFixed(2)}
                  suffix={
                    <span style={{ fontSize: 14, color: pctColor(latest.sz_pct_change), marginLeft: 8 }}>
                      {latest.sz_pct_change != null && (latest.sz_pct_change > 0 ? '+' : '') + latest.sz_pct_change.toFixed(2) + '%'}
                    </span>
                  }
                  styles={{ content: { color: pctColor(latest.sz_pct_change), fontSize: 24, fontWeight: 700 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="主力净流入"
                  value={fmtYiRaw(latest.main_net_inflow)}
                  suffix={latest.main_net_inflow != null ? <>
                    <span style={{ fontSize: 13, color: pctColor(latest.main_net_inflow_pct), marginLeft: 4 }}>
                      {fmtPct(latest.main_net_inflow_pct)}
                    </span>
                    <span style={{ fontSize: 12, color: colors.textTertiary, marginLeft: 4 }}>亿</span>
                  </> : ''}
                  styles={{ content: { color: pctColor(latest.main_net_inflow), fontSize: 22 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="交易日"
                  value={latest.trade_date || '--'}
                  styles={{ content: { color: colors.textPrimary, fontSize: 20 } }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 视图切换 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Space>
            <Segmented
              value={viewMode}
              onChange={(v) => setViewMode(v as 'chart' | 'table')}
              options={[
                { label: <span><BarChartOutlined /> K线图</span>, value: 'chart' },
                { label: <span><TableOutlined /> 数据表</span>, value: 'table' },
              ]}
              size="small"
            />
            <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
              {viewMode === 'chart' ? '上证指数日K线' : '历史资金流向（近120个交易日）'}
            </Text>
          </Space>
          {viewMode === 'chart' && (
            <Segmented
              value={subIndicator}
              onChange={(v) => setSubIndicator(v as 'volume' | 'macd' | 'kdj' | 'rsi')}
              options={[
                { label: '成交量', value: 'volume' },
                { label: 'MACD', value: 'macd' },
                { label: 'KDJ', value: 'kdj' },
                { label: 'RSI', value: 'rsi' },
              ]}
              size="small"
            />
          )}
          <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>
        </div>

        {/* K线图 — 始终渲染 chart div 确保 ref 绑定 */}
        {viewMode === 'chart' && (
          <div style={{ position: 'relative', height: 540 }}>
            {/* 叠加提示：数据还没加载好时显示 */}
            {chartData.dates.length === 0 && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex', zIndex: 1,
                alignItems: 'center', justifyContent: 'center',
                color: colors.textTertiary,
                background: colors.bgCard,
                borderRadius: 6, border: `1px solid ${colors.borderColor}`,
              }}>
                {loading ? '加载中...' : '暂无 K 线数据'}
              </div>
            )}
            {/* chart div 始终存在，保证 chartRef 从一开始就绑定 */}
            <div
              ref={chartRef}
              style={{
                width: '100%',
                height: 540,
                background: colors.bgCard,
                border: '1px solid ' + colors.borderColor,
                borderRadius: 6,
                padding: 4,
              }}
            />
          </div>
        )}

        {/* 数据表 — 撑满剩余视口高度，分页器紧贴底部 */}
        {viewMode === 'table' && (
          <div ref={tableContainerRef} className="kline-table-box">
            <Table
              size="small"
              columns={columns}
              dataSource={data}
              scroll={{ x: 1200, y: scrollY }}
              pagination={{
                defaultPageSize: 20,
                showSizeChanger: true,
                pageSizeOptions: ['10', '20', '30', '50', '100'],
                showTotal: (t) => `共 ${t} 条`,
                style: { marginBottom: 0 },
              }}
              rowKey={(r) => r.trade_date || ''}
              className="kline-fixed-table"
              style={{ fontSize: 13, '--kline-scroll-y': `${scrollY}px` } as React.CSSProperties}
            />
          </div>
        )}
      </Spin>
    </div>
  );
};

// ─── 连续涨跌面板 ───────────────────────────────────────────────

const ConsecutivePanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(104);
  const [upList, setUpList] = useState<StockConsecutiveStats[]>([]);
  const [downList, setDownList] = useState<StockConsecutiveStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'up' | 'down'>('up');

  const loadAll = useCallback(async (force = false) => {
    const CK = 'kline:consecutive';
    if (!force) {
      const c = readDailyCache<{ up: StockConsecutiveStats[]; down: StockConsecutiveStats[] }>(CK);
      if (c) { setUpList(c.up || []); setDownList(c.down || []); return; }
    }
    setLoading(true);
    try {
      const [up, down] = await Promise.all([
        marketApi.getConsecutiveUp(),
        marketApi.getConsecutiveDown(),
      ]);
      // 按连涨天数降序
      (up || []).sort((a, b) => b.consecutive_up_days - a.consecutive_up_days);
      (down || []).sort((a, b) => b.consecutive_up_days - a.consecutive_up_days);
      setUpList(up || []);
      setDownList(down || []);
      writeDailyCache(CK, { up: up || [], down: down || [] });
    } catch (e: any) {
      message.error('连续涨跌加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const list = mode === 'up' ? upList : downList;

  const columns = useMemo(() => [
    { title: '代码', dataIndex: 'symbol', width: 85,
      render: (v: string) => <Text style={{ fontFamily: 'monospace' }}>{v}</Text> },
    { title: '名称', dataIndex: 'name', width: 90,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '收盘价', dataIndex: 'close_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: mode === 'up' ? '连涨天数' : '连跌天数', dataIndex: 'consecutive_up_days', width: 85, align: 'center' as const,
      render: (v: number) => (
        <Tag color={mode === 'up'
          ? (v >= 10 ? 'red' : v >= 5 ? 'orange' : 'blue')
          : (v >= 10 ? 'purple' : v >= 5 ? 'volcano' : 'geekblue')}
        >
          {v}天
        </Tag>
      ) },
    { title: '阶段涨跌幅', dataIndex: 'consecutive_up_pct', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtPct(v)}</Text> },
    { title: '最高价', dataIndex: 'high_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '最低价', dataIndex: 'low_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: '累计换手率', dataIndex: 'cumulative_turnover_rate', width: 100, align: 'right' as const,
      render: (v: number) => fmtPct(v) },
    { title: '行业', dataIndex: 'industry', width: 85,
      render: (v: string) => <Tag style={{ margin: 0 }}>{v || '--'}</Tag> },
  ], [mode]);

  return (
    <div className="kline-panel">
      <Spin spinning={loading} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Segmented
            value={mode}
            onChange={(v) => setMode(v as 'up' | 'down')}
            options={[
              { label: <span><RiseOutlined style={{ color: '#ff4d4f' }} /> 连续上涨 ({upList.length})</span>, value: 'up' },
              { label: <span><FallOutlined style={{ color: '#52c41a' }} /> 连续下跌 ({downList.length})</span>, value: 'down' },
            ]}
          />
          <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => loadAll(true)}>刷新</Button>
        </div>

        {/* 极端行情显示 */}
        {mode === 'up' && upList.length > 0 && (
          <div style={{
            padding: '8px 12px', marginBottom: 10, borderRadius: 4,
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            fontSize: 13, color: colors.textSecondary,
          }}>
            最长连涨：<Text strong style={{ color: '#ff4d4f' }}>{upList[0].name}</Text>
            （<Text style={{ color: '#ff4d4f' }}>{upList[0].consecutive_up_days}天</Text>，
            涨幅 {fmtPct(upList[0].consecutive_up_pct)}）
          </div>
        )}
        {mode === 'down' && downList.length > 0 && (
          <div style={{
            padding: '8px 12px', marginBottom: 10, borderRadius: 4,
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            fontSize: 13, color: colors.textSecondary,
          }}>
            最长连跌：<Text strong style={{ color: '#52c41a' }}>{downList[0].name}</Text>
            （<Text style={{ color: '#52c41a' }}>{downList[0].consecutive_up_days}天</Text>，
            跌幅 {fmtPct(downList[0].consecutive_up_pct)}）
          </div>
        )}

        <div ref={containerRef} className="kline-table-box">
          <Table
            size="small"
            columns={columns}
            dataSource={list}
            scroll={{ x: 900, y: scrollY }}
            pagination={{ defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '30', '50', '100'], showTotal: (t) => `共 ${t} 条` }}
            rowKey={(r, i) => `${r.symbol}-${i}`}
            className="kline-fixed-table"
            style={{ fontSize: 13, '--kline-scroll-y': `${scrollY}px` } as React.CSSProperties}
          />
        </div>
      </Spin>
    </div>
  );
};

// ─── 量价变化面板 ───────────────────────────────────────────────

const VolumePricePanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(104);
  const [upList, setUpList] = useState<StockVolumePriceStats[]>([]);
  const [downList, setDownList] = useState<StockVolumePriceStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'up' | 'down'>('up');

  const loadAll = useCallback(async (force = false) => {
    const CK = 'kline:volumePrice';
    if (!force) {
      const c = readDailyCache<{ up: StockVolumePriceStats[]; down: StockVolumePriceStats[] }>(CK);
      if (c) { setUpList(c.up || []); setDownList(c.down || []); return; }
    }
    setLoading(true);
    try {
      const [up, down] = await Promise.all([
        marketApi.getVolumePriceUp(),
        marketApi.getVolumePriceDown(),
      ]);
      const sortKey = mode === 'up' ? 'volume_price_up_days' : 'volume_price_up_days';
      (up || []).sort((a, b) => (b as any)[sortKey] - (a as any)[sortKey]);
      (down || []).sort((a, b) => (b as any)[sortKey] - (a as any)[sortKey]);
      setUpList(up || []);
      setDownList(down || []);
      writeDailyCache(CK, { up: up || [], down: down || [] });
    } catch (e: any) {
      message.error('量价变化加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const list = mode === 'up' ? upList : downList;

  const columns = useMemo(() => [
    { title: '代码', dataIndex: 'symbol', width: 85,
      render: (v: string) => <Text style={{ fontFamily: 'monospace' }}>{v}</Text> },
    { title: '名称', dataIndex: 'name', width: 90,
      render: (v: string) => <Text strong>{v}</Text> },
    { title: '最新价', dataIndex: 'latest_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v) },
    { title: mode === 'up' ? '量价齐升天数' : '量价齐跌天数', dataIndex: 'volume_price_up_days', width: 100, align: 'center' as const,
      render: (v: number) => (
        <Tag color={mode === 'up'
          ? (v >= 8 ? 'red' : v >= 5 ? 'orange' : 'blue')
          : (v >= 8 ? 'purple' : v >= 5 ? 'volcano' : 'geekblue')}
        >
          {v}天
        </Tag>
      ) },
    { title: '阶段涨跌幅', dataIndex: 'stage_pct_change', width: 105, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtPct(v)}</Text> },
    { title: '累计换手率', dataIndex: 'cumulative_turnover_rate', width: 100, align: 'right' as const,
      render: (v: number) => fmtPct(v) },
    { title: '行业', dataIndex: 'industry', width: 85,
      render: (v: string) => <Tag style={{ margin: 0 }}>{v || '--'}</Tag> },
  ], [mode]);

  return (
    <div className="kline-panel">
      <Spin spinning={loading} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Segmented
            value={mode}
            onChange={(v) => {
              setMode(v as 'up' | 'down');
              setUpList([]);
              setDownList([]);
            }}
            options={[
              { label: <span><BarChartOutlined style={{ color: '#ff4d4f' }} /> 量价齐升</span>, value: 'up' },
              { label: <span><BarChartOutlined style={{ color: '#52c41a' }} /> 量价齐跌</span>, value: 'down' },
            ]}
          />
          <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => loadAll(true)}>刷新</Button>
        </div>

        {mode === 'up' && upList.length > 0 && (
          <div style={{
            padding: '8px 12px', marginBottom: 10, borderRadius: 4,
            background: colors.bgCard, border: `1px solid ${colors.borderColor}`,
            fontSize: 13, color: colors.textSecondary,
          }}>
            量价齐升最强：<Text strong style={{ color: '#ff4d4f' }}>{upList[0].name}</Text>
            （连续{upList[0].volume_price_up_days}天，涨幅 {fmtPct(upList[0].stage_pct_change)}）
          </div>
        )}

        <div ref={containerRef} className="kline-table-box">
          <Table
            size="small"
            columns={columns}
            dataSource={list}
            scroll={{ x: 800, y: scrollY }}
            pagination={{ defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '30', '50', '100'], showTotal: (t) => `共 ${t} 条` }}
            rowKey={(r, i) => `${r.symbol}-${i}`}
            className="kline-fixed-table"
            style={{ fontSize: 13, '--kline-scroll-y': `${scrollY}px` } as React.CSSProperties}
          />
        </div>
      </Spin>
    </div>
  );
};

// ─── 市场统计面板 ───────────────────────────────────────────────

const MarketStatsPanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(104);
  const [data, setData] = useState<InvestorMarketStats[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (force = false) => {
    const CK = 'kline:accountStats';
    if (!force) {
      const c = readDailyCache<InvestorMarketStats[]>(CK);
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await marketApi.getAccountStatistics();
      (list || []).sort((a, b) => (b.stat_date || '').localeCompare(a.stat_date || ''));
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('市场统计加载失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const latest = data[0];

  const columns = useMemo(() => [
    { title: '月份', dataIndex: 'stat_date', width: 90 },
    { title: '新增投资者(万户)', dataIndex: 'new_investor_count', width: 120, align: 'right' as const,
      render: (v: number | null) => v != null ? fmtNum(v, 2) : '--' },
    { title: '环比', dataIndex: 'new_investor_mom', width: 75, align: 'right' as const,
      render: (v: number | null) => v != null ? <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> : '--' },
    { title: '同比', dataIndex: 'new_investor_yoy', width: 75, align: 'right' as const,
      render: (v: number | null) => v != null ? <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> : '--' },
    { title: '投资者总量(万户)', dataIndex: 'total_investor_amount', width: 125, align: 'right' as const,
      render: (v: number | null) => v != null ? fmtNum(v, 2) : '--' },
    { title: '沪深总市值(亿)', dataIndex: 'total_market_cap', width: 120, align: 'right' as const,
      render: (v: number | null) => v != null ? fmtNum(v, 2) : '--' },
    { title: '户均市值(万)', dataIndex: 'avg_market_cap_per_investor', width: 115, align: 'right' as const,
      render: (v: number | null) => v != null ? fmtNum(v, 4) : '--' },
    { title: '上证收盘', dataIndex: 'sh_index_close', width: 95, align: 'right' as const,
      render: (v: number | null) => v != null ? fmtNum(v, 2) : '--' },
    { title: '上证涨跌幅', dataIndex: 'sh_index_pct_change', width: 100, align: 'right' as const,
      render: (v: number | null) => v != null ? <Text style={{ color: pctColor(v) }}>{fmtPct(v)}</Text> : '--' },
  ], []);

  return (
    <div className="kline-panel">
      <Spin spinning={loading} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {latest && (
          <Row gutter={12} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title={<span><TeamOutlined /> 投资者总量</span>}
                  value={latest.total_investor_amount != null ? fmtNum(latest.total_investor_amount, 2) : '--'}
                  suffix="万户"
                  styles={{ content: { color: colors.textPrimary, fontSize: 22 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="新增投资者"
                  value={latest.new_investor_count != null ? fmtNum(latest.new_investor_count, 2) : '--'}
                  suffix="万户"
                  styles={{ content: { color: '#56A4FF', fontSize: 22 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title={<span><DollarOutlined /> 沪深总市值</span>}
                  value={latest.total_market_cap != null ? fmtNum(latest.total_market_cap, 1) : '--'}
                  suffix="亿"
                  styles={{ content: { color: '#F59E0B', fontSize: 22 } }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
                <Statistic
                  title="数据月份"
                  value={latest.stat_date || '--'}
                  styles={{ content: { color: colors.textPrimary, fontSize: 20 } }}
                />
              </Card>
            </Col>
          </Row>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Text style={{ color: colors.textSecondary, fontSize: 13 }}>历史月度统计</Text>
          <Button size="small" ghost icon={<ReloadOutlined />} onClick={() => load(true)}>刷新</Button>
        </div>
        <div ref={containerRef} className="kline-table-box">
          <Table
            size="small"
            columns={columns}
            dataSource={data}
            scroll={{ x: 1000, y: scrollY }}
            pagination={{ defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '30', '50', '100'], showTotal: (t) => `共 ${t} 条` }}
            rowKey={(r) => r.stat_date || ''}
            className="kline-fixed-table"
            style={{ fontSize: 13, '--kline-scroll-y': `${scrollY}px` } as React.CSSProperties}
          />
        </div>
      </Spin>
    </div>
  );
};

// ─── 主组件 ─────────────────────────────────────────────────────

const Kline: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState('market-index');

  return (
    <div className="page-layout kline-page" style={{ padding: '0 4px 8px' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
        <Space>
          <LineChartOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>行情与 K 线</Title>
          <Tag color="red" style={{ marginLeft: 8 }}>同花顺</Tag>
        </Space>
      </div>

      <div className="flex-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="small"
          type="card"
          style={{ height: '100%' }}
          items={[
            {
              key: 'market-index',
              label: <span><StockOutlined /> 大盘行情</span>,
              children: <MarketIndexPanel />,
            },
            {
              key: 'consecutive',
              label: <span><ArrowUpOutlined style={{ color: '#ff4d4f' }} /> 连续涨跌</span>,
              children: <ConsecutivePanel />,
            },
            {
              key: 'volume-price',
              label: <span><BarChartOutlined /> 量价变化</span>,
              children: <VolumePricePanel />,
            },
            {
              key: 'stats',
              label: <span><TeamOutlined /> 市场统计</span>,
              children: <MarketStatsPanel />,
            },
          ]}
        />
      </div>
    </div>
  );
};

export default React.memo(Kline);