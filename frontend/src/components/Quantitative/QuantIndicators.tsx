import React from 'react';
import { Row, Col, Progress, Space, Typography } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { mockQuantIndicators } from '../../utils/mockData';
import { useTheme } from '../../themes';

const { Text } = Typography;

const QuantIndicators: React.FC = () => {
  const { colors } = useTheme();
  const indicators = mockQuantIndicators;

  const getRSIStatus = (value: number) => {
    if (value >= 70) return { text: '超买', color: '#ff4d4f' };
    if (value <= 30) return { text: '超卖', color: '#52c41a' };
    return { text: '正常', color: '#1890ff' };
  };

  const rsiStatus = getRSIStatus(indicators.rsi);

  return (
    <DashboardCard title="技术指标" subtitle="当前量化指标状态">
      <Space orientation="vertical" style={{ width: '100%' }} size="large">
        {/* RSI指标 */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <Text style={{ color: colors.textPrimary }}>RSI (14)</Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Text style={{ color: rsiStatus.color, fontWeight: 600, fontSize: '20px' }}>
                {indicators.rsi.toFixed(1)}
              </Text>
              <Text style={{ color: rsiStatus.color, fontSize: '12px' }}>{rsiStatus.text}</Text>
            </div>
          </div>
          <Progress
            percent={indicators.rsi}
            showInfo={false}
            strokeColor={[
              {
                offset: 0,
                color: '#52c41a',
              },
              {
                offset: 0.3,
                color: '#52c41a',
              },
              {
                offset: 0.3,
                color: '#1890ff',
              },
              {
                offset: 0.7,
                color: '#1890ff',
              },
              {
                offset: 0.7,
                color: '#ff4d4f',
              },
              {
                offset: 1,
                color: '#ff4d4f',
              },
            ]}
            railColor={colors.borderColor}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>30</Text>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>50</Text>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>70</Text>
          </div>
        </div>

        {/* MACD */}
        <div>
          <Row gutter={16}>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>MACD</Text>
                <div>
                  <Text
                    style={{
                      color: indicators.macd >= 0 ? '#ff4d4f' : '#52c41a',
                      fontWeight: 600,
                      fontSize: '18px',
                    }}
                  >
                    {indicators.macd.toFixed(2)}
                  </Text>
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>SIGNAL</Text>
                <div>
                  <Text style={{ color: colors.textPrimary, fontWeight: 600, fontSize: '18px' }}>
                    {indicators.signal.toFixed(2)}
                  </Text>
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>柱状</Text>
                <div>
                  <Text
                    style={{
                      color: indicators.macd - indicators.signal >= 0 ? '#ff4d4f' : '#52c41a',
                      fontWeight: 600,
                      fontSize: '18px',
                    }}
                  >
                    {(indicators.macd - indicators.signal).toFixed(2)}
                  </Text>
                </div>
              </div>
            </Col>
          </Row>
        </div>

        {/* KDJ */}
        <div>
          <Text style={{ color: colors.textSecondary, fontSize: '13px' }}>KDJ 指标</Text>
          <Row gutter={16} style={{ marginTop: '8px' }}>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: '#667eea', fontSize: '12px' }}>K</Text>
                <div>
                  <Text style={{ color: '#667eea', fontWeight: 600, fontSize: '18px' }}>
                    {indicators.kdj.k.toFixed(1)}
                  </Text>
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: '#764ba2', fontSize: '12px' }}>D</Text>
                <div>
                  <Text style={{ color: '#764ba2', fontWeight: 600, fontSize: '18px' }}>
                    {indicators.kdj.d.toFixed(1)}
                  </Text>
                </div>
              </div>
            </Col>
            <Col span={8}>
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: '#f093fb', fontSize: '12px' }}>J</Text>
                <div>
                  <Text style={{ color: '#f093fb', fontWeight: 600, fontSize: '18px' }}>
                    {indicators.kdj.j.toFixed(1)}
                  </Text>
                </div>
              </div>
            </Col>
          </Row>
        </div>
      </Space>
    </DashboardCard>
  );
};

export default QuantIndicators;