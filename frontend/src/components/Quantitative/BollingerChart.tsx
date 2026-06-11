import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import DashboardCard from '../Common/DashboardCard';
import { generateKLineData, mockQuantIndicators } from '../../utils/mockData';

const BollingerChart: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const klineData = generateKLineData(30);
    const dates = klineData.map((item) => item.date);
    const prices = klineData.map((item) => item.close);

    const { boll } = mockQuantIndicators;

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
        data: ['价格', '上轨', '中轨', '下轨'],
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
        data: dates,
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
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
        },
      },
      series: [
        {
          name: '价格',
          type: 'line',
          smooth: true,
          data: prices,
          lineStyle: {
            width: 2,
            color: '#fff',
          },
          itemStyle: {
            color: '#fff',
          },
          symbol: 'none',
        },
        {
          name: '上轨',
          type: 'line',
          smooth: true,
          data: prices.map((p) => p * (boll.up / boll.mid)),
          lineStyle: {
            width: 1,
            type: 'dashed',
            color: '#ff4d4f',
          },
          itemStyle: {
            color: '#ff4d4f',
          },
          symbol: 'none',
        },
        {
          name: '中轨',
          type: 'line',
          smooth: true,
          data: prices.map((p) => p * (boll.mid / boll.mid)),
          lineStyle: {
            width: 1,
            type: 'dashed',
            color: '#1890ff',
          },
          itemStyle: {
            color: '#1890ff',
          },
          symbol: 'none',
        },
        {
          name: '下轨',
          type: 'line',
          smooth: true,
          data: prices.map((p) => p * (boll.down / boll.mid)),
          lineStyle: {
            width: 1,
            type: 'dashed',
            color: '#52c41a',
          },
          itemStyle: {
            color: '#52c41a',
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
    <DashboardCard title="布林带通道" subtitle="BOLL指标可视化">
      <div ref={chartRef} style={{ width: '100%', height: '220px' }} />
    </DashboardCard>
  );
};

export default BollingerChart;
