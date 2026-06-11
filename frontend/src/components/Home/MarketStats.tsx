import React, { useState } from 'react';
import { Row, Col, Typography, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

const marketData = [
  { name: '上证指数', code: '000001.SH', value: 3128.82, change: 12.45, changePercent: 0.40, volume: '2856亿' },
  { name: '深证成指', code: '399001.SZ', value: 10245.68, change: 45.23, changePercent: 0.44, volume: '3542亿' },
  { name: '创业板指', code: '399006.SZ', value: 2056.34, change: 18.56, changePercent: 0.91, volume: '1823亿' },
  { name: '科创50', code: '000688.SH', value: 956.78, change: -3.45, changePercent: -0.36, volume: '456亿' },
];

const MarketStats: React.FC = () => {
  const { colors, theme } = useTheme();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  return (
    <Row gutter={[16, 0]}>
      {marketData.map((item, index) => {
        const isUp = item.change >= 0;
        const isHovered = hoveredIndex === index;

        return (
          <Col xs={24} sm={12} lg={6} key={item.code}>
            <div
              style={{
                background: colors.bgCard,
                border: `1px solid ${isHovered ? 'rgba(86, 164, 255, 0.4)' : colors.borderColor}`,
                borderRadius: '12px',
                padding: '20px',
                height: '100%',
                cursor: 'pointer',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                transform: isHovered ? 'translateY(-4px) scale(1.02)' : 'translateY(0) scale(1)',
                boxShadow: isHovered
                  ? (theme === 'dark'
                    ? '0 8px 30px rgba(86, 164, 255, 0.15), 0 0 40px rgba(81, 78, 189, 0.1)'
                    : '0 8px 30px rgba(86, 164, 255, 0.1)')
                  : 'none',
                position: 'relative',
                overflow: 'hidden',
              }}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onMouseDown={() => setHoveredIndex(null)}
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
                  background: isUp
                    ? 'linear-gradient(90deg, transparent 0%, #EF4444 50%, transparent 100%)'
                    : 'linear-gradient(90deg, transparent 0%, #10B981 50%, transparent 100%)',
                  opacity: isHovered ? 0.8 : 0.4,
                  filter: 'blur(4px)',
                  transition: 'all 0.3s ease',
                }}
              />

              {/* 侧边光效 */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: isHovered ? '3px' : '0px',
                  height: isHovered ? '60%' : '0%',
                  background: isUp
                    ? 'linear-gradient(180deg, transparent 0%, #EF4444 50%, transparent 100%)'
                    : 'linear-gradient(180deg, transparent 0%, #10B981 50%, transparent 100%)',
                  filter: 'blur(3px)',
                  transition: 'all 0.3s ease',
                }}
              />

              <Space orientation="vertical" style={{ width: '100%', position: 'relative', zIndex: 1 }} size={8}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
                    {item.name}
                  </Text>
                  <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                    {item.code}
                  </Text>
                </div>

                <Text
                  style={{
                    color: colors.textPrimary,
                    fontSize: '26px',
                    fontWeight: 800,
                    lineHeight: '1.2',
                    letterSpacing: '-1px',
                  }}
                >
                  {item.value.toFixed(2)}
                </Text>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Space>
                    {isUp ? (
                      <ArrowUpOutlined style={{ color: '#EF4444', fontSize: '12px' }} />
                    ) : (
                      <ArrowDownOutlined style={{ color: '#10B981', fontSize: '12px' }} />
                    )}
                    <Text style={{ color: isUp ? '#EF4444' : '#10B981', fontSize: '14px', fontWeight: 700 }}>
                      {isUp ? '+' : ''}{item.change.toFixed(2)}
                    </Text>
                    <Text style={{ color: isUp ? '#EF4444' : '#10B981', fontSize: '13px' }}>
                      ({isUp ? '+' : ''}{item.changePercent.toFixed(2)}%)
                    </Text>
                  </Space>
                </div>

                <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                  成交额: {item.volume}
                </Text>
              </Space>
            </div>
          </Col>
        );
      })}
    </Row>
  );
};

export default MarketStats;
