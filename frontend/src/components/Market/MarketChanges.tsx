import React from 'react';
import { Tag, Typography } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { mockMarketChanges } from '../../utils/mockData';
import { ThunderboltOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import { safeToFixed } from '../../utils/format';

const { Text } = Typography;

const MarketChanges: React.FC = () => {
  const { colors } = useTheme();

  const getTypeIcon = (type: string) => {
    switch (type) {
      case '火箭发射':
        return <ThunderboltOutlined style={{ color: '#ff4d4f' }} />;
      case '快速反弹':
        return <ArrowUpOutlined style={{ color: '#ff7875' }} />;
      case '封涨停板':
        return <Tag color="red" style={{ margin: 0, padding: '0 4px' }}>涨停</Tag>;
      case '打开跌停板':
        return <Tag color="green" style={{ margin: 0, padding: '0 4px' }}>开板</Tag>;
      default:
        return <ArrowUpOutlined />;
    }
  };

  return (
    <DashboardCard title="行情异动" subtitle="实时盘口异动监控">
      <div style={{ maxHeight: '240px', overflow: 'auto' }}>
        {mockMarketChanges.map((item, index) => (
          <div
            key={index}
            style={{
              padding: '8px 0',
              borderBottom: `1px solid ${colors.borderColor}`,
            }}
          >
            <div style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {getTypeIcon(item.type)}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Text style={{ color: colors.textPrimary, fontWeight: 500 }}>{item.name}</Text>
                    <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                      {item.code}
                    </Text>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                    <Tag color="purple" style={{ margin: 0, padding: '0 6px', fontSize: '11px' }}>
                      {item.type}
                    </Tag>
                    <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                      {item.time}
                    </Text>
                  </div>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Text style={{ color: colors.textPrimary, fontWeight: 600, fontSize: '14px' }}>
                  {safeToFixed(item.price, 2)}
                </Text>
                <div>
                  <Text className="text-up" style={{ fontSize: '12px' }}>
                    +{item.change}%
                  </Text>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
};

export default MarketChanges;