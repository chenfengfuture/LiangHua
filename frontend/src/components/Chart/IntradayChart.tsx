/**
 * 分时图组件 — 同花顺风格个股日内曲线
 *
 * 展示个股日内价格走势，包含：
 *   - 价格线（涨红跌绿）
 *   - 均价线（黄色，基于 close 的移动平均）
 *   - 昨收参考线（灰色虚线）
 *   - 红绿渐变填充
 *   - 成交量柱（涨红跌绿）
 *
 * 数据来源（已确认工作）：
 *   GET /api/stock/get-stock-zh-a-hist-min-em?period=1 → StockKlineMinute[]
 */

import React, { useRef, useEffect, useMemo } from 'react';
import * as echarts from 'echarts';
import { Empty, Spin } from 'antd';
import { useTheme } from '@/themes';
import type { StockKlineMinute } from '../../types/stock';

interface IntradayChartProps {
  /** 1分钟 K 线数据（从 getMinuteKline 获取） */
  data: StockKlineMinute[];
  /** 昨收价（从实时行情中取） */
  prevClose: number;
  /** 股票代码 */
  symbol: string;
  /** 日期 */
  date: string;
  loading?: boolean;
}

/** "YYYY-MM-DD HH:MM" → "HH:MM" 时间字符串 */
const extractTime = (dt: string): string => {
  // 格式可能为 "2026-06-05 09:31:00" 或 "2026-06-05 09:31"
  const parts = dt.split(' ');
  if (parts.length < 2) return dt;
  return parts[1].slice(0, 5);
};

/** 是否显示该时间标签（整点或半点，或首尾） */
const shouldShowLabel = (t: string, idx: number, total: number): boolean => {
  if (idx === 0 || idx === total - 1) return true;
  if (t.endsWith(':00') || t.endsWith(':30')) {
    const hour = parseInt(t.split(':')[0], 10);
    const min = parseInt(t.split(':')[1], 10);
    if (hour === 9 && min === 30) return true;
    if (hour === 10 && min === 30) return true;
    if (hour === 11 && min === 30) return true;
    if (hour === 13 && min === 0) return true;
    if (hour === 14 && min === 0) return true;
    if (hour === 14 && min === 30) return true;
    if (hour === 15 && min === 0) return true;
  }
  return false;
};

const IntradayChart: React.FC<IntradayChartProps> = ({
  data,
  prevClose,
  symbol,
  date,
  loading = false,
}) => {
  const { colors } = useTheme();
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const toNumber = (value: any, fallback = 0): number => {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  };

  // 按 datetime 排序，并过滤无法绘制的异常记录
  const sortedData = useMemo<StockKlineMinute[]>(() => {
    if (!data || data.length === 0) return [];
    return [...data]
      .filter((item) => item?.datetime && Number.isFinite(Number(item.close)))
      .sort((a, b) => String(a.datetime).localeCompare(String(b.datetime)));
  }, [data]);

  // ── 工具：检测两个时间字符串之间的间隔分钟数 ──
  const timeGapMinutes = (a: string, b: string): number => {
    const [ah, am] = a.split(':').map(Number);
    const [bh, bm] = b.split(':').map(Number);
    return (bh * 60 + bm) - (ah * 60 + am);
  };

  // 提取绘图数据
  const chartInfo = useMemo<{
    times: string[];
    prices: (number | null)[];
    avgPrices: (number | null)[];
    volumes: number[];
    volMa5: (number | null)[];
    volMa10: (number | null)[];
    vr: (number | null)[];
    isUp: boolean;
    /** 显示索引 → sortedData 原始索引映射（-1 表示分隔符） */
    dataIndexMap: number[];
  } | null>(() => {
    if (sortedData.length === 0) return null;

    const rawTimes = sortedData.map(d => extractTime(String(d.datetime)));
    const rawPrices = sortedData.map(d => toNumber(d.close));
    const volumes = sortedData.map(d => toNumber(d.volume || d.vol || 0));

    // 均价：close 的简单移动平均（窗口 30，约30分钟）
    const windowSize = Math.min(30, Math.floor(sortedData.length / 3));
    const rawAvgPrices = rawPrices.map((_, i) => {
      const start = Math.max(0, i - windowSize + 1);
      let sum = 0;
      for (let j = start; j <= i; j++) sum += rawPrices[j];
      return sum / (i - start + 1);
    });

    // ── 成交量移动平均 MA5 / MA10 ──
    const calcSma = (data: number[], period: number): (number | null)[] =>
      data.map((_, i) => {
        if (i < period - 1) return null;
        let sum = 0;
        for (let j = i - period + 1; j <= i; j++) sum += data[j];
        return sum / period;
      });
    const volMa5 = calcSma(volumes, 5);
    const volMa10 = calcSma(volumes, 10);

    // ── 量比（成交量比率）：volume / SMA(volume, 20) ──
    const vrPeriod = Math.min(20, Math.max(5, Math.floor(volumes.length / 4)));
    const vr: (number | null)[] = volumes.map((_, i) => {
      if (i < vrPeriod - 1) return null;
      let sum = 0;
      for (let j = i - vrPeriod + 1; j <= i; j++) sum += volumes[j];
      const avg = sum / vrPeriod;
      return avg > 0 ? volumes[i] / avg : null;
    });

    // ── 构建显示数据：在午休断点处插入 null 分隔符 ──
    // 同时维护 dataIndexMap：显示索引 → 原始 sortedData 索引（-1=分隔符）
    const times: string[] = [];
    const prices: (number | null)[] = [];
    const avgPrices: (number | null)[] = [];
    const dataIndexMap: number[] = [];

    for (let i = 0; i < rawTimes.length; i++) {
      // 检测与前一个点的间隔是否 > 5 分钟（午休断点）
      if (i > 0 && timeGapMinutes(rawTimes[i - 1], rawTimes[i]) > 5) {
        times.push('');
        prices.push(null);
        avgPrices.push(null);
        dataIndexMap.push(-1);
      }
      times.push(rawTimes[i]);
      prices.push(rawPrices[i]);
      avgPrices.push(rawAvgPrices[i]);
      dataIndexMap.push(i);
    }

    const lastPrice = rawPrices[rawPrices.length - 1];
    const baseline = prevClose > 0 ? prevClose : rawPrices[0];
    const isUp = lastPrice >= baseline;

    return { times, prices, avgPrices, volumes, volMa5, volMa10, vr, isUp, dataIndexMap };
  }, [sortedData, prevClose]);

  useEffect(() => {
    if (!chartRef.current || !chartInfo) return;
    const { times, prices, avgPrices, volumes, volMa5, volMa10, vr, isUp, dataIndexMap } = chartInfo;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const inst = chartInstance.current;

    const priceLineColor = '#FFFFFF';
    const avgLineColor = '#FDE68A';

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: true,
      legend: {
        data: [
          { name: '分时', icon: 'line' },
          { name: '均价', icon: 'line' },
          { name: 'VOL MA5', icon: 'line' },
          { name: 'VOL MA10', icon: 'line' },
          { name: '量比(VR)', icon: 'line' },
        ],
        textStyle: { color: colors.textSecondary, fontSize: 11 },
        top: 2, left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(20,20,40,0.92)',
        borderColor: 'rgba(102,126,234,0.5)',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          const displayIdx = params[0]?.dataIndex ?? 0;
          const rawIdx = dataIndexMap[displayIdx];
          // 分隔符位置不显示 tooltip
          if (rawIdx < 0) return '';
          const bar = sortedData[rawIdx];
          if (!bar) return '';
          const baseline = prevClose > 0 ? prevClose : prices[0];
          const close = toNumber(bar.close);
          const color = close >= baseline ? '#ff4d4f' : '#52c41a';
          const chg = baseline > 0 ? ((close - baseline) / baseline * 100) : 0;
          return `<div style="padding:8px;min-width:220px">
            <div style="font-weight:600;margin-bottom:6px;color:#ccc">
              ${symbol} · ${bar.datetime}
            </div>
            <div style="display:flex;justify-content:space-between">
              <span style="color:#999">价格:</span>
              <span style="color:${color};font-weight:700">${close.toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:4px">
              <span style="color:#999">涨幅:</span>
              <span style="color:${color}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:4px">
              <span style="color:#999">均价:</span>
              <span style="color:${avgLineColor}">${avgPrices[displayIdx].toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:4px">
              <span style="color:#999">开/高/低:</span>
              <span>${toNumber(bar.open).toFixed(2)} / ${toNumber(bar.high).toFixed(2)} / ${toNumber(bar.low).toFixed(2)}</span>
            </div>
            <div style="margin-top:4px;border-top:1px solid rgba(255,255,255,0.15);padding-top:4px">
              <span style="color:#999">成交量:</span>
              <span>${volumes[rawIdx].toLocaleString()}</span>
            </div>
            ${volMa5[rawIdx] != null ? `<div style="display:flex;justify-content:space-between;margin-top:2px">
              <span style="color:#999">VOL MA5:</span>
              <span style="color:#60A5FA">${volMa5[rawIdx]!.toLocaleString(undefined, {maximumFractionDigits:0})}</span>
            </div>` : ''}
            ${volMa10[rawIdx] != null ? `<div style="display:flex;justify-content:space-between;margin-top:2px">
              <span style="color:#999">VOL MA10:</span>
              <span style="color:#A78BFA">${volMa10[rawIdx]!.toLocaleString(undefined, {maximumFractionDigits:0})}</span>
            </div>` : ''}
            ${vr[rawIdx] != null ? `<div style="display:flex;justify-content:space-between;margin-top:2px">
              <span style="color:#999">量比(VR):</span>
              <span style="color:#FBBF24">${vr[rawIdx]!.toFixed(2)}</span>
            </div>` : ''}
          </div>`;
        },
      },
      grid: [
        { left: 50, right: 60, top: 32, height: '58%' },
        { left: 50, right: 60, top: '68%', height: '22%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: times,
          boundaryGap: false,
          axisLine: { show: false },
          axisLabel: { show: false },
          splitLine: {
            show: true,
            lineStyle: { color: '#333', opacity: 0.25, type: 'dashed' },
          },
        },
        {
          type: 'category',
          gridIndex: 1,
          data: times,
          boundaryGap: false,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: {
            color: colors.textTertiary,
            fontSize: 10,
            interval: (idx: number) => shouldShowLabel(times[idx], idx, times.length),
          },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: {
            color: colors.textTertiary,
            fontSize: 10,
            formatter: (v: number) => v.toFixed(2),
          },
          splitLine: {
            lineStyle: { color: colors.borderColor, opacity: 0.3 },
          },
        },
        {
          gridIndex: 1,
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10 },
          splitLine: { show: false },
        },
        // 右侧 Y 轴（量比 VR）
        {
          gridIndex: 1,
          scale: true,
          position: 'right',
          axisLine: { show: false },
          axisLabel: { color: '#FBBF24', fontSize: 10 },
          splitLine: { show: false },
          name: '量比',
          nameTextStyle: { color: '#FBBF24', fontSize: 9 },
        },
      ],
      series: [
        // ── 价格线 + 渐变填充 ──
        {
          name: '分时',
          type: 'line',
          data: prices,
          smooth: 0.35,
          showSymbol: false,
          lineStyle: {
            width: 1.8,
            color: priceLineColor,
            shadowBlur: 8,
            shadowColor: 'rgba(255,255,255,0.3)',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: isUp ? 'rgba(255,77,79,0.15)' : 'rgba(82,196,26,0.15)' },
              { offset: 0.5, color: isUp ? 'rgba(255,77,79,0.05)' : 'rgba(82,196,26,0.05)' },
              { offset: 1, color: 'rgba(255,255,255,0)' },
            ]),
          },
          // 昨收参考线
          markLine: {
            silent: true,
            animation: false,
            label: {
              show: true,
              formatter: prevClose > 0 ? `昨收 ${prevClose.toFixed(2)}` : '基准价缺失',
              color: colors.textTertiary,
              fontSize: 10,
              position: 'insideEndTop',
            },
            data: prevClose > 0 ? [{ yAxis: prevClose }] : [],
            lineStyle: { color: '#999', type: 'dashed', width: 1 },
          },
        },
        // ── 均价线 ──
        {
          name: '均价',
          type: 'line',
          data: avgPrices,
          smooth: 0.35,
          showSymbol: false,
          lineStyle: { width: 1.5, color: avgLineColor },
        },
        // ── 成交量柱 ──
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes.map((v, i) => ({
            value: v,
            itemStyle: {
              color: prices[i] >= (prevClose > 0 ? prevClose : prices[0]) ? '#ff4d4f' : '#52c41a',
              opacity: 0.65,
            },
          })),
        },
        // ── 成交量移动平均 MA5 ──
        {
          name: 'VOL MA5',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volMa5,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#60A5FA' },
        },
        // ── 成交量移动平均 MA10 ──
        {
          name: 'VOL MA10',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volMa10,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#A78BFA' },
        },
        // ── 量比（成交量比率 VR）──
        {
          name: '量比(VR)',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 2,
          data: vr,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#FBBF24' },
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      ],
    };

    inst.setOption(option, true);
    requestAnimationFrame(() => inst.resize());
  }, [chartInfo, colors, prevClose, symbol, date, sortedData]);

  // ECharts 实例 + resize
  useEffect(() => {
    if (chartRef.current && !chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // 清理
  useEffect(() => {
    return () => {
      try { chartInstance.current?.dispose(); } catch {}
      chartInstance.current = null;
    };
  }, []);

  const hasData = chartInfo !== null;

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400, position: 'relative' }}>
      <Spin spinning={loading} style={{ width: '100%', height: '100%' }}>
        <div style={{ width: '100%', height: '100%', minHeight: 400, position: 'relative' }}>
          {!hasData ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: `1px solid ${colors.borderColor}`,
              borderRadius: 6,
              background: colors.bgCard,
            }}
          >
            <Empty description={loading ? '加载中...' : `暂无 ${symbol} 分时数据`} />
          </div>
          ) : (
            <div
              ref={chartRef}
              style={{
                width: '100%',
                height: '100%',
                minHeight: 400,
                background: colors.bgCard,
                border: `1px solid ${colors.borderColor}`,
                borderRadius: 6,
                padding: 4,
              }}
            />
          )}
        </div>
      </Spin>
    </div>
  );
};

export default React.memo(IntradayChart);