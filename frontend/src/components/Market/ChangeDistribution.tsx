import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import DashboardCard from '../Common/DashboardCard';
import { mockChangeDistribution } from '../../utils/mockData';

const ChangeDistribution: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const data = mockChangeDistribution;
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
        backgroundColor: 'rgba(20, 20, 40, 0.9)',
        borderColor: 'rgba(102, 126, 234, 0.5)',
        textStyle: {
          color: '#fff',
        },
      },
      grid: {
        left: '3%',
        right: '3%',
        top: '10%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: ['跌停', '-5%~-3%', '-3%~0%', '0%~3%', '3%~5%', '5%~涨停', '涨停'],
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.2)',
          },
        },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 10,
          rotate: 30,
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
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
      },
      series: [
        {
          type: 'bar',
          data: [
            { value: data.limitDown, itemStyle: { color: '#00a854' } },
            { value: data.down5, itemStyle: { color: '#389e0d' } },
            { value: data.down3, itemStyle: { color: '#52c41a' } },
            { value: data.up0, itemStyle: { color: '#8c8c8c' } },
            { value: data.up3, itemStyle: { color: '#ff7875' } },
            { value: data.up5, itemStyle: { color: '#ff4d4f' } },
            { value: data.limitUp, itemStyle: { color: '#cf1322' } },
          ],
          barWidth: '60%',
          itemStyle: {
            borderRadius: [4, 4, 0, 0],
          },
          label: {
            show: true,
            position: 'top',
            color: '#fff',
            fontSize: 10,
          },
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
    <DashboardCard title="涨跌分布" subtitle="今日个股涨跌幅统计">
      <div ref={chartRef} style={{ width: '100%', height: '200px' }} />
    </DashboardCard>
  );
};

export default ChangeDistribution;
