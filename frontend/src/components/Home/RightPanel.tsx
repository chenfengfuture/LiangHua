import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Typography, Space, Progress, Tag, List } from 'antd';
import { ArrowUpOutlined, FireOutlined, InfoCircleOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import dayjs from 'dayjs';

const { Text } = Typography;

const mockNewsData = [
  { id: 1, title: '央行宣布降准0.5个百分点，释放长期流动性约1万亿元', time: '12:15', type: 'positive', source: '央视新闻' },
  { id: 2, title: '人工智能板块持续走强，多只概念股创下历史新高', time: '11:45', type: 'positive', source: '东方财富' },
  { id: 3, title: '新能源汽车销量再创新高，产业链景气度提升', time: '11:30', type: 'positive', source: '财联社' },
  { id: 4, title: '医药板块集体调整，集采政策影响持续发酵', time: '11:15', type: 'negative', source: '证券时报' },
  { id: 5, title: '科创板注册制改革深化，资本市场迎来新机遇', time: '11:00', type: 'neutral', source: '上海证券报' },
];

const RealTimeNews: React.FC<{ colors: any; theme: string }> = ({ colors, theme }) => {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '10px',
        padding: '12px',
        transition: 'all 0.3s ease',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
          paddingBottom: '10px',
          borderBottom: `1px solid ${colors.borderColor}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FireOutlined style={{ color: '#EF4444', fontSize: '14px' }} />
          <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 700 }}>
            实时新闻
          </Text>
        </div>
        <Tag color="blue" style={{ margin: 0, fontSize: '10px', padding: '1px 6px', background: 'rgba(86, 164, 255, 0.1)', borderColor: 'rgba(86, 164, 255, 0.3)' }}>
          {dayjs().format('HH:mm:ss')}
        </Tag>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {mockNewsData.map((news, index) => (
          <div
            key={news.id}
            onMouseEnter={() => setHoveredId(news.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              padding: '8px 10px',
              borderRadius: '6px',
              marginBottom: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              background: hoveredId === news.id ? colors.hoverBg : 'transparent',
              transform: hoveredId === news.id ? 'translateX(3px)' : 'translateX(0)',
              borderLeft: `2px solid ${news.type === 'positive' ? '#EF4444' : news.type === 'negative' ? '#10B981' : '#F59E0B'}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <Text style={{ color: colors.textPrimary, fontSize: '12px', fontWeight: 500, lineHeight: '1.4' }}>
                  {news.title}
                </Text>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                  <Text style={{ color: colors.textTertiary, fontSize: '10px' }}>
                    {news.source}
                  </Text>
                  <Tag
                    color={news.type === 'positive' ? 'red' : news.type === 'negative' ? 'green' : 'orange'}
                    style={{ margin: 0, fontSize: '9px', padding: '0 4px', height: '16px', lineHeight: '14px' }}
                  >
                    {news.type === 'positive' ? '利好' : news.type === 'negative' ? '利空' : '中性'}
                  </Tag>
                </div>
              </div>
              <Text style={{ color: colors.textTertiary, fontSize: '10px', whiteSpace: 'nowrap' }}>
                {news.time}
              </Text>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const PortfolioOverview: React.FC<{ colors: any; theme: string }> = ({ colors, theme }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      series: [
        {
          type: 'pie',
          radius: ['60%', '80%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: colors.bgCard,
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold',
              color: colors.textPrimary,
            },
          },
          labelLine: {
            show: false,
          },
          data: [
            { value: 35, name: '股票', itemStyle: { color: '#56A4FF' } },
            { value: 25, name: '基金', itemStyle: { color: '#546ACF' } },
            { value: 20, name: '债券', itemStyle: { color: '#514EBD' } },
            { value: 20, name: '现金', itemStyle: { color: '#ACA9CC' } },
          ],
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
        borderRadius: '10px',
        padding: '12px',
        transition: 'all 0.3s ease',
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
          width: '40%',
          height: '2px',
          background: 'linear-gradient(90deg, transparent 0%, #56A4FF 50%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ marginBottom: '10px' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 700 }}>
            持仓概览
          </Text>
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <Text style={{ color: colors.textSecondary, fontSize: '11px' }}>总资产</Text>
            <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 800 }}>
              ¥1,843,256.00
            </Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <Text style={{ color: colors.textSecondary, fontSize: '11px' }}>可用资金</Text>
            <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 600 }}>
              ¥452,320.50
            </Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ color: colors.textSecondary, fontSize: '11px' }}>今日盈亏</Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ArrowUpOutlined style={{ color: '#EF4444', fontSize: '11px' }} />
              <Text style={{ color: '#EF4444', fontSize: '13px', fontWeight: 700 }}>
                +¥1,680.50
              </Text>
            </div>
          </div>
        </div>

        {/* 环形图和仓位 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around' }}>
          <div ref={chartRef} style={{ width: '100px', height: '100px' }} />
          <div style={{ textAlign: 'center' }}>
            <Progress
              type="circle"
              percent={75}
              size={70}
              strokeColor={{
                '0%': '#56A4FF',
                '50%': '#546ACF',
                '100%': '#514EBD',
              }}
              railColor={colors.borderColor}
              format={() => (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: colors.textPrimary }}>
                    75.6%
                  </div>
                </div>
              )}
            />
            <div style={{ marginTop: '4px', color: colors.textTertiary, fontSize: '10px' }}>
              仓位使用率
            </div>
          </div>
        </div>

        {/* 资产分布图例 */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '12px' }}>
          {[
            { name: '股票', color: '#56A4FF', percent: '35%' },
            { name: '基金', color: '#546ACF', percent: '25%' },
            { name: '债券', color: '#514EBD', percent: '20%' },
            { name: '现金', color: '#ACA9CC', percent: '20%' },
          ].map((item) => (
            <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '2px',
                  background: item.color,
                }}
              />
              <Text style={{ color: colors.textSecondary, fontSize: '10px' }}>
                {item.name} {item.percent}
              </Text>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const RightPanel: React.FC = () => {
  const { colors, theme } = useTheme();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
      {/* 实时新闻 - 上方 */}
      <RealTimeNews colors={colors} theme={theme} />

      {/* 持仓概览 - 下方 */}
      <PortfolioOverview colors={colors} theme={theme} />
    </div>
  );
};

export default RightPanel;
