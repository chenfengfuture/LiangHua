import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import DashboardCard from '../Common/DashboardCard';
import { mockMoneyFlow } from '../../utils/mockData';

const MoneyFlowChart: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const data = mockMoneyFlow;
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(20, 20, 40, 0.9)',
        borderColor: 'rgba(102, 126, 234, 0.5)',
        textStyle: {
          color: '#fff',
        },
      },
      legend: {
        data: ['主力资金', '散户资金'],
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
        data: data.date,
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
          formatter: '{value}亿',
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
      },
      series: [
        {
          name: '主力资金',
          type: 'line',
          smooth: true,
          data: data.mainForce,
          symbol: 'circle',
          symbolSize: 6,
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
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.01)' },
            ]),
          },
        },
        {
          name: '散户资金',
          type: 'line',
          smooth: true,
          data: data.retail,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#f093fb' },
              { offset: 1, color: '#f5576c' },
            ]),
          },
          itemStyle: {
            color: '#f093fb',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(240, 147, 251, 0.2)' },
              { offset: 1, color: 'rgba(240, 147, 251, 0.01)' },
            ]),
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
    <DashboardCard title="资金流向" subtitle="最近10个交易日资金变化">
      <div ref={chartRef} style={{ width: '100%', height: '200px' }} />
    </DashboardCard>
  );
};

export default MoneyFlowChart;
