import React from 'react';
import { Card, Typography, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Title, Text } = Typography;

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  change?: number;
  changePercent?: number;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  unit,
  change,
  changePercent,
  prefix,
  suffix,
  loading = false,
}) => {
  const { colors } = useTheme();
  const isPositive = change !== undefined && change >= 0;
  const isNegative = change !== undefined && change < 0;

  return (
    <Card
      className="card-hover"
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
      }}
      loading={loading}
    >
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ color: colors.textSecondary, fontSize: '14px' }}>
            {title}
          </Text>
          {prefix}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <Title
            level={2}
            className="count-animation"
            style={{
              margin: 0,
              color: colors.textPrimary,
              fontSize: '32px',
              fontWeight: 700,
            }}
          >
            {value}
          </Title>
          {unit && (
            <Text style={{ color: colors.textTertiary, fontSize: '14px' }}>
              {unit}
            </Text>
          )}
        </div>

        {change !== undefined && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Space>
              {isPositive && <ArrowUpOutlined style={{ color: '#ff4d4f' }} />}
              {isNegative && <ArrowDownOutlined style={{ color: '#52c41a' }} />}
              <Text style={{ color: isPositive ? '#ff4d4f' : '#52c41a', fontSize: '14px' }}>
                {isPositive ? '+' : ''}{change?.toFixed(2)}
              </Text>
              {changePercent !== undefined && (
                <Text style={{ color: isPositive ? '#ff4d4f' : '#52c41a', fontSize: '14px' }}>
                  ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
                </Text>
              )}
            </Space>
            {suffix}
          </div>
        )}
      </Space>
    </Card>
  );
};

export default StatCard;
