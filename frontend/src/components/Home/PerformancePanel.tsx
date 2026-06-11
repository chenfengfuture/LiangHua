import React from 'react';
import { Row, Col, Typography, Progress } from 'antd';
import { ArrowUpOutlined, TrophyOutlined, FallOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

const performanceData = [
  { label: '总收益率', value: 42.8, isPositive: true, icon: <ArrowUpOutlined /> },
  { label: '年化收益', value: 28.5, isPositive: true, icon: <ArrowUpOutlined /> },
  { label: '最大回撤', value: 8.2, isPositive: false, icon: <FallOutlined /> },
  { label: '胜率', value: 68.4, isPositive: true, icon: <TrophyOutlined /> },
];

const PerformancePanel: React.FC = () => {
  const { colors, theme } = useTheme();

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
      <div>
        <div style={{ marginBottom: '16px' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
            策略绩效
          </Text>
        </div>

        <Row gutter={[12, 12]}>
          {performanceData.map((item, index) => (
            <Col xs={12} sm={6} key={item.label}>
              <div
                style={{
                  padding: '14px',
                  borderRadius: '10px',
                  background: theme === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                  border: `1px solid ${colors.borderColor}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ color: item.isPositive ? '#10B981' : '#EF4444', fontSize: '16px' }}>
                    {item.icon}
                  </span>
                  <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>
                    {item.label}
                  </Text>
                </div>

                <div style={{ marginBottom: '6px' }}>
                  <Text
                    style={{
                      color: item.isPositive ? '#10B981' : '#EF4444',
                      fontSize: '22px',
                      fontWeight: 800,
                    }}
                  >
                    {item.isPositive ? '+' : ''}{item.value}%
                  </Text>
                </div>

                <Progress
                  percent={Math.min(item.value * 1.5, 100)}
                  showInfo={false}
                  strokeColor={{
                    '0%': item.isPositive ? '#10B981' : '#EF4444',
                    '100%': item.isPositive ? '#56A4FF' : '#F59E0B',
                  }}
                  railColor={colors.borderColor}
                  size={[4, 4]}
                />
              </div>
            </Col>
          ))}
        </Row>
      </div>
    </div>
  );
};

export default PerformancePanel;
