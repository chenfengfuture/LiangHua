import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Typography, Space, Statistic } from 'antd';
import { ArrowUpOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import dayjs from 'dayjs';

const { Text } = Typography;

const generateEquityData = (days: number = 90) => {
  const data = [];
  let equity = 100000;
  let benchmark = 100000;
  
  for (let i = days; i >= 0; i--) {
    const date = dayjs().subtract(i, 'day').format('MM-DD');
    const dailyChange = (Math.random() - 0.45) * 2000;
    const benchmarkChange = (Math.random() - 0.48) * 1500;
    
    equity = Math.max(equity + dailyChange, 80000);
    benchmark = Math.max(benchmark + benchmarkChange, 80000);
    
    data.push({
      date,
      equity: Math.round(equity),
      benchmark: Math.round(benchmark),
    });
  }
  
  return data;
};

const EquityCurve: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const { colors, theme } = useTheme();

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);

    const data = generateEquityData(90);
    const dates = data.map(item => item.date);
    const equity = data.map(item => item.equity);
    const benchmark = data.map(item => item.benchmark);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: theme === 'dark' ? 'rgba(20,20,24,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: colors.borderColor,
        borderWidth: 1,
        textStyle: {
          color: colors.textPrimary,
        },
        formatter: (params: any) => {
          const date = params[0].axisValue;
          const equityVal = params[0].value.toLocaleString();
          const benchmarkVal = params[1].value.toLocaleString();
          return `
            <div style="padding: 8px;">
              <div style="font-weight: 600; margin-bottom: 8px;">${date}</div>
              <div style="color: #56A4FF;">策略净值: ¥${equityVal}</div>
              <div style="color: #ACA9CC;">基准净值: ¥${benchmarkVal}</div>
            </div>
          `;
        },
      },
      legend: {
        data: ['策略净值', '基准指数'],
        textStyle: {
          color: colors.textSecondary,
        },
        top: 0,
        right: 20,
      },
      grid: {
        left: '60px',
        right: '40px',
        top: '50px',
        bottom: '30px',
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: {
          lineStyle: {
            color: colors.borderColor,
          },
        },
        axisLabel: {
          color: colors.textTertiary,
          fontSize: 10,
        },
        splitLine: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          show: false,
        },
        axisLabel: {
          color: colors.textTertiary,
          fontSize: 10,
          formatter: (value: number) => `¥${(value / 10000).toFixed(0)}万`,
        },
        splitLine: {
          lineStyle: {
            color: colors.borderColor,
            type: 'dashed',
            opacity: 0.5,
          },
        },
      },
      series: [
        {
          name: '策略净值',
          type: 'line',
          data: equity,
          smooth: true,
          lineStyle: {
            width: 3,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#56A4FF' },
              { offset: 0.5, color: '#546ACF' },
              { offset: 1, color: '#514EBD' },
            ]),
          },
          itemStyle: {
            color: '#56A4FF',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(86, 164, 255, 0.25)' },
              { offset: 1, color: 'rgba(86, 164, 255, 0.01)' },
            ]),
          },
          symbol: 'none',
        },
        {
          name: '基准指数',
          type: 'line',
          data: benchmark,
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#ACA9CC',
            type: 'dashed',
          },
          itemStyle: {
            color: '#ACA9CC',
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
  }, [theme, colors]);

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        padding: '16px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 顶部光效 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '50%',
          height: '2px',
          background: 'linear-gradient(90deg, transparent 0%, #56A4FF 50%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
          zIndex: 1,
        }}
      />

      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div>
            <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
              净值曲线
            </Text>
            <div style={{ marginTop: '4px' }}>
              <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                近90天策略表现
              </Text>
            </div>
          </div>

          <Space size="large">
            <Statistic
              title={<span style={{ color: colors.textTertiary, fontSize: '12px' }}>累计收益</span>}
              value={42.8}
              precision={2}
              suffix="%"
              styles={{ content: { color: '#10B981', fontSize: '20px', fontWeight: 700 } }}
              prefix={<ArrowUpOutlined />}
            />
            <Statistic
              title={<span style={{ color: colors.textTertiary, fontSize: '12px' }}>夏普比率</span>}
              value={2.34}
              precision={2}
              styles={{ content: { color: '#56A4FF', fontSize: '20px', fontWeight: 700 } }}
            />
            <Statistic
              title={<span style={{ color: colors.textTertiary, fontSize: '12px' }}>最大回撤</span>}
              value={8.2}
              precision={2}
              suffix="%"
              styles={{ content: { color: '#EF4444', fontSize: '20px', fontWeight: 700 } }}
            />
          </Space>
        </div>

        <div ref={chartRef} style={{ width: '100%', height: '220px' }} />
      </div>
    </div>
  );
};

export default EquityCurve;
