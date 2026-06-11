import React from 'react';
import { Tag, Typography, Avatar } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { mockQuantSignals } from '../../utils/mockData';
import { ArrowUpOutlined, ArrowDownOutlined, PauseOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

const QuantSignals: React.FC = () => {
  const { colors } = useTheme();

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'buy':
        return <ArrowUpOutlined style={{ color: '#ff4d4f' }} />;
      case 'sell':
        return <ArrowDownOutlined style={{ color: '#52c41a' }} />;
      default:
        return <PauseOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getSignalTag = (type: string) => {
    switch (type) {
      case 'buy':
        return <Tag color="red">买入</Tag>;
      case 'sell':
        return <Tag color="green">卖出</Tag>;
      default:
        return <Tag color="gold">持有</Tag>;
    }
  };

  return (
    <DashboardCard title="量化信号" subtitle="实时策略信号提示">
      <div style={{ maxHeight: '240px', overflow: 'auto' }}>
        {mockQuantSignals.map((item, index) => (
          <div
            key={index}
            style={{
              padding: '10px 0',
              borderBottom: `1px solid ${colors.borderColor}`,
            }}
          >
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Avatar
                    size={28}
                    style={{
                      background: item.type === 'buy' ? 'rgba(255,77,79,0.2)' : item.type === 'sell' ? 'rgba(82,196,26,0.2)' : 'rgba(250,173,20,0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {getSignalIcon(item.type)}
                  </Avatar>
                  <div>
                    <Text style={{ color: colors.textPrimary, fontWeight: 500 }}>{item.name}</Text>
                    <div style={{ marginTop: '2px' }}>
                      {getSignalTag(item.type)}
                      <Text style={{ color: colors.textTertiary, fontSize: '11px', marginLeft: '8px' }}>
                        {item.time}
                      </Text>
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Text style={{ color: colors.textPrimary, fontWeight: 600 }}>{item.stock}</Text>
                  <div>
                    <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>
                      ¥{item.price.toFixed(2)}
                    </Text>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
};

export default QuantSignals;