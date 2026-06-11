/**
 * 模拟交易 - 权益曲线图（ECharts）
 */

import React, { useRef, useEffect } from 'react';
import { Card, Typography, Space } from 'antd';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';
import type { SimDailyRecord, SimStats } from '@/types/stock';

const { Text } = Typography;

interface Props {
  records: SimDailyRecord[];
  stats: SimStats;
}

const EquityChart: React.FC<Props> = ({ records, stats }) => {
  const { colors, theme } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || records.length === 0) return;
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);
    }
    const inst = chartInstance.current;

    const dates = records.map((r) => r.date);
    const assets = records.map((r) => +r.total_assets.toFixed(2));
    const base = records[0]?.total_assets || 1;
    const pctReturns = records.map((r) => +(((r.total_assets - base) / base) * 100).toFixed(2));

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(20,20,40,0.92)',
        borderColor: 'rgba(102,126,234,0.5)',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          const i = params[0]?.dataIndex ?? 0;
          const r = records[i];
          if (!r) return '';
          const profit = r.total_assets - base;
          const profitColor = profit >= 0 ? '#ff4d4f' : '#52c41a';
          const profitSign = profit >= 0 ? '+' : '';
          return `<div style="padding:6px">
            <div style="font-weight:600;margin-bottom:4px">${r.date}</div>
            <div>总资产: ¥${r.total_assets.toFixed(2)}</div>
            <div>可用资金: ¥${r.available_cash.toFixed(2)}</div>
            <div>持仓市值: ¥${r.market_value.toFixed(2)}</div>
            <div style="border-top:1px solid rgba(255,255,255,0.15);margin-top:4px;padding-top:4px">
              累计收益: <span style="color:${profitColor};font-weight:700">${profitSign}¥${profit.toFixed(2)} (${profitSign}${pctReturns[i].toFixed(2)}%)</span>
            </div>
          </div>`;
        },
      },
      grid: { left: 60, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: colors.borderColor } },
        axisLabel: { color: colors.textTertiary, fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: 'value',
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10, formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        },
        {
          type: 'value',
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10, formatter: (v: number) => `${v.toFixed(1)}%` },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '总资产',
          type: 'line',
          data: assets,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2, color: '#3B82F6' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(59,130,246,0.3)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }]) },
          markLine: {
            silent: true,
            data: [{ yAxis: base }],
            lineStyle: { color: colors.borderColor, type: 'dashed', width: 1 },
            label: { formatter: () => `初始 ¥${(base / 10000).toFixed(0)}万`, color: colors.textTertiary, fontSize: 10 },
          },
        },
        {
          name: '收益率',
          type: 'line',
          yAxisIndex: 1,
          data: pctReturns,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1, color: '#10B981' },
        },
      ],
    };

    inst.setOption(option, true);
    return () => { inst.dispose(); chartInstance.current = null; };
  }, [records, colors, theme, base]);

  // base 闭包问题，用 useRef
  const baseRef = useRef(0);
  baseRef.current = records[0]?.total_assets || 1;
  const base = baseRef.current;

  return (
    <Card
      size="small"
      title={<span style={{ color: colors.textPrimary }}>权益曲线</span>}
      style={{ background: colors.bgCard, borderColor: colors.borderColor }}
      extra={
        <Space size={16}>
          {stats ? (
            <>
              <Text style={{ color: colors.textTertiary, fontSize: 12 }}>胜率 <Text style={{ color: '#ff4d4f', fontWeight: 600 }}>{stats.win_rate}%</Text></Text>
              <Text style={{ color: colors.textTertiary, fontSize: 12 }}>最大回撤 <Text style={{ color: '#52c41a', fontWeight: 600 }}>{stats.max_drawdown_pct}%</Text></Text>
              <Text style={{ color: colors.textTertiary, fontSize: 12 }}>总交易 <Text style={{ color: colors.textPrimary, fontWeight: 600 }}>{stats.total_trades}</Text></Text>
            </>
          ) : null}
        </Space>
      }
    >
      {records.length > 0 ? (
        <div ref={chartRef} style={{ width: '100%', height: 320 }} />
      ) : (
        <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textTertiary, fontSize: 13 }}>
          暂无数据，开始交易后将自动记录权益曲线
        </div>
      )}
    </Card>
  );
};

export default React.memo(EquityChart);