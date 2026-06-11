/**
 * 统一 K 线图表组件
 *
 * 合并 Home 和 Market 两个页面的 K 线图表，消除重复的 ECharts 初始化/渲染逻辑。
 *
 * 使用方式：
 *   导入方式 import { KLineChart } from '@/components/Chart/KLineChart';
 */

import React, { useRef, useEffect } from 'react';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';

// ── 类型定义 ───────────────────────────────────────────────────

export interface KLineDataPoint {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}

export interface KLineChartProps {
  /** K 线数据（未传入则使用 mock 生成） */
  data?: KLineDataPoint[];
  /** 生成 mock 数据的数量（默认 60） */
  mockCount?: number;
  /** 图表高度（默认 320px） */
  height?: number | string;
  /** 是否显示标题（Market 版用 DashboardCard 包装，可隐藏） */
  showTitle?: boolean;
  /** 标题文字 */
  title?: string;
  /** 副标题 */
  subtitle?: string;
  /** 自定义头部（Home 版有股票信息 + 周期选择器，传入后会替换默认头部） */
  header?: React.ReactNode;
}

// ── Mock 数据生成 ──────────────────────────────────────────────

function generateMockKLineData(count: number, basePrice = 156.80): KLineDataPoint[] {
  const data: KLineDataPoint[] = [];
  let bp = basePrice;

  for (let i = count; i >= 0; i--) {
    const date = `2026-${String(Math.ceil(Math.random() * 12)).padStart(2, '0')}-${String(
      Math.ceil(Math.random() * 28),
    ).padStart(2, '0')}`;
    const volatility = Math.random() * 3 - 1.5;
    bp += volatility;

    const open = bp + (Math.random() - 0.5) * 2;
    const close = bp + (Math.random() - 0.5) * 3;
    const high = Math.max(open, close) + Math.random() * 1.5;
    const low = Math.min(open, close) - Math.random() * 1.5;

    data.push({
      date,
      open: parseFloat(open.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      volume: Math.floor(Math.random() * 500000 + 200000),
    });
  }

  return data;
}

// ── 组件 ───────────────────────────────────────────────────────

const KLineChart: React.FC<KLineChartProps> = ({
  data,
  mockCount = 60,
  height = 400,
  showTitle = false,
  title = 'K线走势',
  subtitle,
  header,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const { colors, theme } = useTheme();

  const klineData = data ?? generateMockKLineData(mockCount);

  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;

    instanceRef.current = echarts.init(el, theme === 'dark' ? 'dark' : undefined);

    const dates = klineData.map((d) => d.date);
    const values = klineData.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = klineData.map((d) => d.volume);

    const isUpBg = (idx: number) => values[idx][1] >= values[idx][0];

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: true,
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          lineStyle: {
            color: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            width: 1,
            type: 'dashed',
          },
        },
        backgroundColor: theme === 'dark' ? 'rgba(30,30,32,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: colors.borderColor,
        borderWidth: 1,
        textStyle: { color: colors.textPrimary },
        formatter: (params: any) => {
          const idx = params[0].dataIndex;
          const d = klineData[idx];
          const color = d.close >= d.open ? '#EF4444' : '#10B981';
          return `
            <div style="padding:8px">
              <div style="font-weight:600;margin-bottom:8px">${d.date}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
                <div>开: <span style="color:${color};font-weight:600">${d.open}</span></div>
                <div>收: <span style="color:${color};font-weight:600">${d.close}</span></div>
                <div>高: <span style="color:#EF4444;font-weight:600">${d.high}</span></div>
                <div>低: <span style="color:#10B981;font-weight:600">${d.low}</span></div>
                <div>成交量: <span style="font-weight:600">${(d.volume / 10000).toFixed(2)}万</span></div>
              </div>
            </div>`;
        },
      },
      grid: [
        { left: 60, right: 20, top: 20, height: '58%' },
        { left: 60, right: 20, top: '64%', height: '26%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          boundaryGap: false,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10, showMaxLabel: true },
          splitLine: { show: false },
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          boundaryGap: false,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          scale: true,
          position: 'right',
          axisLine: { show: false },
          axisLabel: { color: colors.textTertiary, fontSize: 10, formatter: (v: number) => v.toFixed(2) },
          splitLine: { lineStyle: { color: colors.borderColor, type: 'dashed' as const, opacity: 0.5 } },
        },
        {
          scale: true,
          gridIndex: 1,
          position: 'right',
          axisLine: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: values,
          itemStyle: {
            color: '#EF4444',
            color0: '#10B981',
            borderColor: '#EF4444',
            borderColor0: '#10B981',
          },
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: (params: any) => (isUpBg(params.dataIndex) ? '#EF4444' : '#10B981'),
            opacity: 0.7,
          },
        },
      ],
    };

    instanceRef.current.setOption(option);

    const handleResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, [theme, colors, klineData]);

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '10px',
        height: typeof height === 'number' ? `${height}px` : height,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 头部区域 — 由调用方通过 header prop 自定义 */}
      {(showTitle || header) && (
        <div
          style={{
            padding: '12px 16px',
            borderBottom: `1px solid ${colors.borderColor}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          {header ?? (
            <div>
              <span style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 700 }}>
                {title}
              </span>
              {subtitle && (
                <span style={{ color: colors.textTertiary, fontSize: '12px', marginLeft: '8px' }}>
                  {subtitle}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* 图表容器 */}
      <div ref={chartRef} style={{ flex: 1, minHeight: '280px' }} />
    </div>
  );
};

export default KLineChart;