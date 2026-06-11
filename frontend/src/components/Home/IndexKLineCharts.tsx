import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Row, Col, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import dayjs from 'dayjs';

const { Text } = Typography;

const indexData = [
  { name: '上证指数', code: '000001.SH', price: 3128.82, change: 12.45, changePercent: 0.40 },
  { name: '深证成指', code: '399001.SZ', price: 10245.68, change: 45.23, changePercent: 0.44 },
  { name: '创业板指', code: '399006.SZ', price: 2056.34, change: 18.56, changePercent: 0.91 },
  { name: '科创50', code: '000688.SH', price: 956.78, change: -3.45, changePercent: -0.36 },
];

const generateKLineData = (basePrice: number, count: number = 60) => {
  const data = [];
  let price = basePrice;
  
  for (let i = count; i >= 0; i--) {
    const date = dayjs().subtract(i, 'minute').format('HH:mm');
    const volatility = (Math.random() - 0.48) * basePrice * 0.0015;
    price = price + volatility;
    
    const open = price + (Math.random() - 0.5) * basePrice * 0.0008;
    const close = price + (Math.random() - 0.5) * basePrice * 0.001;
    const high = Math.max(open, close) + Math.random() * basePrice * 0.0006;
    const low = Math.min(open, close) - Math.random() * basePrice * 0.0006;
    
    data.push({ date, open, close, high, low });
  }
  
  return data;
};

const KLineCard: React.FC<{ index: typeof indexData[0]; colors: any; theme: string }> = ({ index, colors, theme }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);

    const klineData = generateKLineData(index.price, 60);
    const dates = klineData.map(item => item.date);
    const values = klineData.map(item => [item.open, item.close, item.low, item.high]);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: true,
      grid: {
        left: '45px',
        right: '15px',
        top: '10px',
        bottom: '20px',
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          color: colors.textTertiary,
          fontSize: 9,
          showMaxLabel: true,
          interval: 14,
        },
      },
      yAxis: {
        scale: true,
        position: 'right',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: {
          lineStyle: {
            color: colors.borderColor,
            type: 'dashed',
            opacity: 0.5,
          },
        },
        axisLabel: {
          color: colors.textTertiary,
          fontSize: 9,
          formatter: (value: number) => value.toFixed(0),
        },
      },
      series: [
        {
          type: 'candlestick',
          data: values,
          itemStyle: {
            color: '#EF4444',
            color0: '#10B981',
            borderColor: '#EF4444',
            borderColor0: '#10B981',
            borderWidth: 1,
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
  }, [theme, colors, index.price]);

  const isUp = index.change >= 0;

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '10px',
        padding: '12px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = theme === 'dark'
          ? '0 8px 30px rgba(86, 164, 255, 0.15), 0 0 40px rgba(81, 78, 189, 0.1)'
          : '0 8px 30px rgba(86, 164, 255, 0.1)';
        e.currentTarget.style.borderColor = 'rgba(86, 164, 255, 0.3)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.borderColor = colors.borderColor;
      }}
      onMouseDown={(e) => {
        e.currentTarget.style.transform = 'translateY(-1px) scale(0.99)';
      }}
      onMouseUp={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
    >
      {/* 顶部光效 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '40%',
          height: '2px',
          background: isUp
            ? 'linear-gradient(90deg, transparent 0%, #EF4444 50%, transparent 100%)'
            : 'linear-gradient(90deg, transparent 0%, #10B981 50%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
        }}
      />

      {/* 头部信息 - 紧凑布局 */}
      <div style={{ marginBottom: '8px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 700 }}>
            {index.name}
          </Text>
          <Text style={{ color: colors.textTertiary, fontSize: '10px' }}>
            {index.code}
          </Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
          <Text
            style={{
              color: colors.textPrimary,
              fontSize: '20px',
              fontWeight: 800,
              letterSpacing: '-0.5px',
            }}
          >
            {index.price.toFixed(2)}
          </Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {isUp ? (
              <ArrowUpOutlined style={{ color: '#EF4444', fontSize: '11px' }} />
            ) : (
              <ArrowDownOutlined style={{ color: '#10B981', fontSize: '11px' }} />
            )}
            <Text style={{ color: isUp ? '#EF4444' : '#10B981', fontSize: '12px', fontWeight: 700 }}>
              {isUp ? '+' : ''}{index.change.toFixed(2)}
            </Text>
            <Text style={{ color: isUp ? '#EF4444' : '#10B981', fontSize: '11px' }}>
              ({isUp ? '+' : ''}{index.changePercent.toFixed(2)}%)
            </Text>
          </div>
        </div>
      </div>

      {/* K线图容器 - 更紧凑的高度 */}
      <div ref={chartRef} style={{ flex: 1, minHeight: '130px', position: 'relative', zIndex: 1 }} />
    </div>
  );
};

const IndexKLineCharts: React.FC = () => {
  const { colors, theme } = useTheme();

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        padding: '14px',
        position: 'relative',
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 顶部光效 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '60%',
          height: '2px',
          background: 'linear-gradient(90deg, transparent 0%, #56A4FF 30%, #546ACF 50%, #514EBD 70%, transparent 100%)',
          opacity: 0.6,
          filter: 'blur(4px)',
          zIndex: 1,
        }}
      />

      {/* 标题 - 紧凑布局 */}
      <div style={{ marginBottom: '12px', position: 'relative', zIndex: 2 }}>
        <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
          大盘指数
        </Text>
        <Text style={{ color: colors.textTertiary, fontSize: '11px', marginLeft: '10px' }}>
          实时走势
        </Text>
      </div>

      {/* 2x2网格布局 - 更紧凑的间距 */}
      <Row gutter={[12, 12]} style={{ position: 'relative', zIndex: 2, flex: 1 }}>
        <Col xs={24} md={12}>
          <KLineCard index={indexData[0]} colors={colors} theme={theme} />
        </Col>
        <Col xs={24} md={12}>
          <KLineCard index={indexData[1]} colors={colors} theme={theme} />
        </Col>
        <Col xs={24} md={12}>
          <KLineCard index={indexData[2]} colors={colors} theme={theme} />
        </Col>
        <Col xs={24} md={12}>
          <KLineCard index={indexData[3]} colors={colors} theme={theme} />
        </Col>
      </Row>
    </div>
  );
};

export default IndexKLineCharts;
