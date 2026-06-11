import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import DashboardCard from '../Common/DashboardCard';
import { mockBacktestData } from '../../utils/mockData';

const BacktestChart: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const data = mockBacktestData;

    const calculateReturns = (arr: number[]) => {
      const base = arr[0];
      return arr.map((v) => ((v - base) / base) * 100);
    };

    const strategyReturns = calculateReturns(data.strategy);
    const benchmarkReturns = calculateReturns(data.benchmark);

    const totalReturn = strategyReturns[strategyReturns.length - 1];
    const benchmarkReturn = benchmarkReturns[benchmarkReturns.length - 1];
    const excessReturn = totalReturn - benchmarkReturn;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(20, 20, 40, 0.9)',
        borderColor: 'rgba(102, 126, 234, 0.5)',
        textStyle: {
          color: '#fff',
        },
        formatter: (params: any) => {
          let html = `<div>${params[0].axisValue}</div>`;
          params.forEach((item: any) => {
            html += `<div>${item.marker} ${item.seriesName}: ${item.value.toFixed(2)}%</div>`;
          });
          return html;
        },
      },
      legend: {
        data: ['策略收益', '基准收益'],
        textStyle: {
          color: 'rgba(255, 255, 255, 0.7)',
        },
        top: 0,
      },
      grid: {
        left: '3%',
        right: '3%',
        top: '15%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: data.dates,
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.2)',
          },
        },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 10,
        },
        splitLine: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.2)',
          },
        },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 10,
          formatter: '{value}%',
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
      },
      series: [
        {
          name: '策略收益',
          type: 'line',
          smooth: true,
          data: strategyReturns,
          lineStyle: {
            width: 2,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' },
            ]),
          },
          itemStyle: {
            color: '#667eea',
          },
          symbol: 'none',
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(102, 126, 234, 0.2)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.01)' },
            ]),
          },
          markLine: {
            data: [{ type: 'average', name: '均值' }],
            lineStyle: {
              color: 'rgba(255, 255, 255, 0.3)',
              type: 'dashed',
            },
            label: {
              color: 'rgba(255, 255, 255, 0.7)',
              fontSize: 10,
            },
          },
        },
        {
          name: '基准收益',
          type: 'line',
          smooth: true,
          data: benchmarkReturns,
          lineStyle: {
            width: 2,
            type: 'dashed',
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#f093fb' },
              { offset: 1, color: '#f5576c' },
            ]),
          },
          itemStyle: {
            color: '#f093fb',
          },
          symbol: 'none',
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, []);

  return (
    <DashboardCard title="回测收益" subtitle="策略vs基准对比">
      <div ref={chartRef} style={{ width: '100%', height: '220px' }} />
    </DashboardCard>
  );
};

export default BacktestChart;
