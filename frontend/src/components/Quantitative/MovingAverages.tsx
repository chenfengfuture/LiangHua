import React from 'react';
import { Row, Col, Typography, Space, Divider } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { mockQuantIndicators } from '../../utils/mockData';
import { useTheme } from '../../themes';

const { Text, Title } = Typography;

const MovingAverages: React.FC = () => {
  const { colors } = useTheme();
  const { ma5, ma10, ma20, ma60 } = mockQuantIndicators;
  const currentPrice = 100;

  const getMaStatus = (ma: number, price: number) => {
    const diff = ((price - ma) / ma) * 100;
    if (diff > 2) return { text: '强势', color: '#ff4d4f' };
    if (diff < -2) return { text: '弱势', color: '#52c41a' };
    return { text: '震荡', color: '#1890ff' };
  };

  return (
    <DashboardCard title="均线系统" subtitle="多周期均线状态">
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        {/* 当前价格 */}
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>当前价格</Text>
          <Title level={3} style={{ color: colors.textPrimary, margin: '4px 0 0 0' }}>
            ¥{currentPrice.toFixed(2)}
          </Title>
        </div>

        <Divider style={{ margin: '8px 0', borderColor: colors.borderColor }} />

        {/* 均线列表 */}
        <Row gutter={[16, 16]}>
          <Col xs={12}>
            <div
              style={{
                padding: '12px',
                background: 'rgba(102, 126, 234, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(102, 126, 234, 0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: '#667eea', fontWeight: 600 }}>MA5</Text>
                {getMaStatus(ma5, currentPrice).text === '强势' && (
                  <Text style={{ color: '#ff4d4f', fontSize: '11px' }}>↑ 多头</Text>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ color: colors.textPrimary, fontSize: '20px', fontWeight: 700 }}>
                  {ma5.toFixed(2)}
                </Text>
              </div>
              <div style={{ marginTop: '4px' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                  {(currentPrice - ma5 >= 0 ? '+' : '')}{(currentPrice - ma5).toFixed(2)}
                  ({((currentPrice - ma5) / ma5 * 100).toFixed(2)}%)
                </Text>
              </div>
            </div>
          </Col>

          <Col xs={12}>
            <div
              style={{
                padding: '12px',
                background: 'rgba(118, 75, 162, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(118, 75, 162, 0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: '#764ba2', fontWeight: 600 }}>MA10</Text>
                {ma5 > ma10 && (
                  <Text style={{ color: '#ff4d4f', fontSize: '11px' }}>↑ 多头</Text>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ color: colors.textPrimary, fontSize: '20px', fontWeight: 700 }}>
                  {ma10.toFixed(2)}
                </Text>
              </div>
              <div style={{ marginTop: '4px' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                  {(currentPrice - ma10 >= 0 ? '+' : '')}{(currentPrice - ma10).toFixed(2)}
                  ({((currentPrice - ma10) / ma10 * 100).toFixed(2)}%)
                </Text>
              </div>
            </div>
          </Col>

          <Col xs={12}>
            <div
              style={{
                padding: '12px',
                background: 'rgba(240, 147, 251, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(240, 147, 251, 0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: '#f093fb', fontWeight: 600 }}>MA20</Text>
                {ma10 > ma20 && (
                  <Text style={{ color: '#ff4d4f', fontSize: '11px' }}>↑ 多头</Text>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ color: colors.textPrimary, fontSize: '20px', fontWeight: 700 }}>
                  {ma20.toFixed(2)}
                </Text>
              </div>
              <div style={{ marginTop: '4px' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                  {(currentPrice - ma20 >= 0 ? '+' : '')}{(currentPrice - ma20).toFixed(2)}
                  ({((currentPrice - ma20) / ma20 * 100).toFixed(2)}%)
                </Text>
              </div>
            </div>
          </Col>

          <Col xs={12}>
            <div
              style={{
                padding: '12px',
                background: 'rgba(245, 87, 108, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(245, 87, 108, 0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: '#f5576c', fontWeight: 600 }}>MA60</Text>
                {ma20 > ma60 && (
                  <Text style={{ color: '#ff4d4f', fontSize: '11px' }}>↑ 多头</Text>
                )}
              </div>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ color: colors.textPrimary, fontSize: '20px', fontWeight: 700 }}>
                  {ma60.toFixed(2)}
                </Text>
              </div>
              <div style={{ marginTop: '4px' }}>
                <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                  {(currentPrice - ma60 >= 0 ? '+' : '')}{(currentPrice - ma60).toFixed(2)}
                  ({((currentPrice - ma60) / ma60 * 100).toFixed(2)}%)
                </Text>
              </div>
            </div>
          </Col>
        </Row>
      </Space>
    </DashboardCard>
  );
};

export default MovingAverages;