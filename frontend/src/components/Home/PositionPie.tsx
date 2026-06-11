import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Typography, Space, Avatar } from 'antd';
import { useTheme } from '../../themes';

const { Text } = Typography;

const positionData = [
  { name: '贵州茅台', code: '600519', value: 25, color: '#56A4FF', change: 1.85 },
  { name: '宁德时代', code: '300750', value: 20, color: '#546ACF', change: 2.34 },
  { name: '比亚迪', code: '002594', value: 18, color: '#514EBD', change: -1.45 },
  { name: '腾讯控股', code: '00700', value: 22, color: '#ACA9CC', change: 0.89 },
  { name: '现金', code: 'CASH', value: 15, color: '#F59E0B', change: 0 },
];

const PositionPie: React.FC = () => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const { colors, theme } = useTheme();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: theme === 'dark' ? 'rgba(20,20,24,0.95)' : 'rgba(255,255,255,0.95)',
        borderColor: colors.borderColor,
        textStyle: {
          color: colors.textPrimary,
        },
        formatter: '{b}: {c}%',
      },
      series: [
        {
          name: '仓位分布',
          type: 'pie',
          radius: ['50%', '75%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: colors.bgCard,
            borderWidth: 3,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
              color: colors.textPrimary,
            },
            itemStyle: {
              shadowBlur: 20,
              shadowColor: 'rgba(86, 164, 255, 0.3)',
            },
          },
          labelLine: {
            show: false,
          },
          data: positionData.map((item, index) => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                { offset: 0, color: item.color },
                { offset: 1, color: item.color + 'CC' },
              ]),
            },
          })),
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
        height: '100%',
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
          background: 'linear-gradient(90deg, transparent 0%, #56A4FF 30%, #514EBD 70%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
          zIndex: 1,
        }}
      />

      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{ marginBottom: '12px' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
            仓位分布
          </Text>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* 环形图 */}
          <div style={{ width: '180px', height: '180px', flexShrink: 0 }}>
            <div ref={chartRef} style={{ width: '100%', height: '100%' }} />
          </div>

          {/* 持仓列表 */}
          <div style={{ flex: 1 }}>
            {positionData.map((item, index) => (
              <div
                key={item.code}
                style={{
                  padding: '8px 10px',
                  borderRadius: '8px',
                  marginBottom: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  background: hoveredIndex === index
                    ? (theme === 'dark' ? 'rgba(86, 164, 255, 0.1)' : 'rgba(86, 164, 255, 0.05)')
                    : 'transparent',
                }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Space>
                    <Avatar
                      size={10}
                      style={{ backgroundColor: item.color, flexShrink: 0 }}
                    />
                    <div>
                      <div>
                        <Text style={{ color: colors.textPrimary, fontSize: '12px', fontWeight: 600 }}>
                          {item.name}
                        </Text>
                      </div>
                      <Text style={{ color: colors.textTertiary, fontSize: '10px' }}>
                        {item.code}
                      </Text>
                    </div>
                  </Space>
                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 700 }}>
                      {item.value}%
                    </Text>
                    {item.change !== 0 && (
                      <div>
                        <Text style={{ color: item.change > 0 ? '#10B981' : '#EF4444', fontSize: '11px' }}>
                          {item.change > 0 ? '+' : ''}{item.change}%
                        </Text>
                      </div>
                    )}
                  </div>
                </Space>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PositionPie;
