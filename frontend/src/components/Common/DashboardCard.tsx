import React from 'react';
import { Card, Typography, Space } from 'antd';
import { useTheme } from '../../themes';

const { Title, Text } = Typography;

interface DashboardCardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  extra?: React.ReactNode;
  height?: number | string;
  loading?: boolean;
  padding?: number | string;
}

const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  subtitle,
  children,
  extra,
  height = '100%',
  loading = false,
  padding,
}) => {
  const { theme, colors } = useTheme();

  return (
    <Card
      className="card-hover"
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        height: height,
        display: 'flex',
        flexDirection: 'column',
      }}
      loading={loading}
      title={
        title ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Title
                level={5}
                style={{
                  margin: 0,
                  color: colors.textPrimary,
                  fontWeight: 600,
                }}
              >
                {title}
              </Title>
              {subtitle && (
                <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                  {subtitle}
                </Text>
              )}
            </Space>
            {extra}
          </div>
        ) : undefined
      }
      styles={{
        body: {
          flex: 1,
          padding: padding !== undefined ? padding : '16px',
          overflow: 'auto',
        },
      }}
    >
      {children}
    </Card>
  );
};

export default DashboardCard;
