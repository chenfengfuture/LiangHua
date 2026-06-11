import React from 'react';
import { Table, Typography, Tag, Space, Switch, Button } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

interface StrategyData {
  id: string;
  name: string;
  pair: string;
  currentValue: number;
  totalProfit: number;
  dailyProfit: number;
  status: 'running' | 'stopped';
}

const mockStrategies: StrategyData[] = [
  { id: '1', name: '趋势跟踪策略', pair: 'BTC/USDT', currentValue: 258199, totalProfit: 8.92, dailyProfit: 0.52, status: 'running' },
  { id: '2', name: '网格交易策略', pair: 'ETH/USDT', currentValue: 156300, totalProfit: 12.45, dailyProfit: -0.87, status: 'running' },
  { id: '3', name: '均值回归策略', pair: 'SOL/USDT', currentValue: 98500, totalProfit: 5.67, dailyProfit: 1.23, status: 'running' },
  { id: '4', name: 'MACD策略', pair: 'BNB/USDT', currentValue: 142800, totalProfit: -2.34, dailyProfit: -1.56, status: 'stopped' },
  { id: '5', name: 'RSI超买超卖', pair: 'ADA/USDT', currentValue: 78600, totalProfit: 15.80, dailyProfit: 2.10, status: 'running' },
];

const StrategyList: React.FC = () => {
  const { colors, theme } = useTheme();

  const columns = [
    {
      title: '策略',
      key: 'name',
      width: 180,
      render: (_: any, record: StrategyData) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: record.status === 'running' 
                ? 'linear-gradient(135deg, #56A4FF 0%, #514EBD 100%)' 
                : 'linear-gradient(135deg, #ACA9CC 0%, #8B86A0 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ color: '#fff', fontSize: '12px', fontWeight: 700 }}>
              {record.name.charAt(0)}
            </span>
          </div>
          <div>
            <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 600 }}>
              {record.name}
            </Text>
            <div>
              <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                {record.pair}
              </Text>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '当前市值',
      dataIndex: 'currentValue',
      key: 'currentValue',
      width: 120,
      align: 'right' as const,
      render: (value: number) => (
        <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 700 }}>
          ¥{value.toLocaleString()}
        </Text>
      ),
    },
    {
      title: '累计收益',
      dataIndex: 'totalProfit',
      key: 'totalProfit',
      width: 100,
      align: 'right' as const,
      render: (value: number) => {
        const isUp = value >= 0;
        return (
          <div style={{ textAlign: 'right' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
              {isUp ? (
                <ArrowUpOutlined style={{ color: '#EF4444', fontSize: '10px' }} />
              ) : (
                <ArrowDownOutlined style={{ color: '#10B981', fontSize: '10px' }} />
              )}
              <Text
                style={{
                  color: isUp ? '#EF4444' : '#10B981',
                  fontSize: '12px',
                  fontWeight: 700,
                }}
              >
                {isUp ? '+' : ''}{value.toFixed(2)}%
              </Text>
            </div>
          </div>
        );
      },
    },
    {
      title: '今日收益',
      dataIndex: 'dailyProfit',
      key: 'dailyProfit',
      width: 100,
      align: 'right' as const,
      render: (value: number) => {
        const isUp = value >= 0;
        return (
          <Text
            style={{
              color: isUp ? '#EF4444' : '#10B981',
              fontSize: '12px',
              fontWeight: 700,
            }}
          >
            {isUp ? '+' : ''}{value.toFixed(2)}%
          </Text>
        );
      },
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: StrategyData) => (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
          <Tag
            color={record.status === 'running' ? 'blue' : 'default'}
            style={{
              margin: 0,
              fontSize: '11px',
              padding: '2px 10px',
              borderRadius: '6px',
            }}
            icon={record.status === 'running' ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
          >
            {record.status === 'running' ? '运行中' : '已停止'}
          </Tag>
          <Switch
            size="small"
            checked={record.status === 'running'}
          />
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      align: 'center' as const,
      render: () => (
        <Space size="small">
          <Button type="text" size="small" style={{ color: '#56A4FF', fontSize: '11px' }}>
            查看
          </Button>
          <Button type="text" size="small" style={{ color: '#546ACF', fontSize: '11px' }}>
            编辑
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '16px 20px', borderBottom: `1px solid ${colors.borderColor}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
            量化策略模块
          </Text>
          <div style={{ display: 'flex', gap: '6px' }}>
            {['全部', '运行中', '已停止', '股票', '期货'].map((tab, idx) => (
              <div
                key={tab}
                style={{
                  padding: '5px 14px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  background: idx === 1 
                    ? (theme === 'dark' ? 'rgba(86, 164, 255, 0.15)' : 'rgba(86, 164, 255, 0.1)')
                    : 'transparent',
                  color: idx === 1 ? '#56A4FF' : colors.textSecondary,
                  border: `1px solid ${idx === 1 ? 'rgba(86, 164, 255, 0.4)' : 'transparent'}`,
                }}
              >
                {tab}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <Table
          columns={columns}
          dataSource={mockStrategies}
          pagination={false}
          size="small"
          rowKey="id"
          showHeader={true}
        />
      </div>
    </div>
  );
};

export default StrategyList;
