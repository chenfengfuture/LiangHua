import React, { useState } from 'react';
import { Table, Typography, Tag, Space } from 'antd';
import { ArrowUpOutlined, StarOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

interface StockData {
  code: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  amount: number;
}

const mockHotStocks: StockData[] = [
  { code: '600519', name: '贵州茅台', price: 1568.50, change: 28.50, changePercent: 1.85, volume: 125600, amount: 19.8 },
  { code: '300750', name: '宁德时代', price: 198.56, change: 5.67, changePercent: 2.94, volume: 456780, amount: 9.1 },
  { code: '002594', name: '比亚迪', price: 245.80, change: -3.40, changePercent: -1.36, volume: 678900, amount: 16.7 },
  { code: '00700', name: '腾讯控股', price: 328.60, change: 8.20, changePercent: 2.56, volume: 345670, amount: 11.4 },
  { code: 'AAPL', name: '苹果', price: 178.45, change: 2.34, changePercent: 1.33, volume: 890120, amount: 15.8 },
  { code: '601318', name: '中国平安', price: 45.80, change: 0.92, changePercent: 2.05, volume: 234560, amount: 10.7 },
  { code: '600036', name: '招商银行', price: 35.67, change: 0.45, changePercent: 1.28, volume: 189450, amount: 6.8 },
  { code: '000001', name: '平安银行', price: 12.45, change: -0.15, changePercent: -1.19, volume: 567890, amount: 7.1 },
];

const HotStocks: React.FC = () => {
  const { colors, theme } = useTheme();
  const [favorites, setFavorites] = useState<string[]>(['600519', '300750']);
  const [activeTab, setActiveTab] = useState('up');
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  const toggleFavorite = (code: string) => {
    setFavorites(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const columns = [
    {
      title: '',
      key: 'star',
      width: 36,
      align: 'center' as const,
      render: (_: any, record: StockData) => (
        <StarOutlined
          style={{
            color: favorites.includes(record.code) ? '#FBBF24' : colors.textTertiary,
            cursor: 'pointer',
            fontSize: '14px',
            transition: 'all 0.2s ease',
          }}
          onClick={() => toggleFavorite(record.code)}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.2)';
            e.currentTarget.style.color = '#FBBF24';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.color = favorites.includes(record.code) ? '#FBBF24' : colors.textTertiary;
          }}
        />
      ),
    },
    {
      title: '股票',
      key: 'name',
      width: 120,
      render: (_: any, record: StockData) => (
        <div>
          <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 600 }}>
            {record.name}
          </Text>
          <div>
            <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
              {record.code}
            </Text>
          </div>
        </div>
      ),
    },
    {
      title: '现价',
      dataIndex: 'price',
      key: 'price',
      width: 80,
      align: 'right' as const,
      render: (value: number) => (
        <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 700 }}>
          {value.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '涨跌',
      key: 'change',
      width: 100,
      align: 'right' as const,
      render: (_: any, record: StockData) => {
        const isUp = record.change >= 0;
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
                  fontSize: '13px',
                  fontWeight: 700,
                }}
              >
                {isUp ? '+' : ''}{record.change.toFixed(2)}
              </Text>
            </div>
            <Text
              style={{
                color: isUp ? '#EF4444' : '#10B981',
                fontSize: '11px',
              }}
            >
              {isUp ? '+' : ''}{record.changePercent.toFixed(2)}%
            </Text>
          </div>
        );
      },
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      width: 80,
      align: 'right' as const,
      render: (value: number) => (
        <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>
          {(value / 10000).toFixed(1)}万
        </Text>
      ),
    },
    {
      title: '成交额(亿)',
      dataIndex: 'amount',
      key: 'amount',
      width: 90,
      align: 'right' as const,
      render: (value: number) => (
        <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>
          {value.toFixed(1)}
        </Text>
      ),
    },
  ];

  const tabs = [
    { key: 'up', label: '涨幅榜' },
    { key: 'down', label: '跌幅榜' },
    { key: 'amount', label: '成交额' },
  ];

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s ease',
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
          width: '50%',
          height: '2px',
          background: 'linear-gradient(90deg, transparent 0%, #56A4FF 50%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
          zIndex: 1,
        }}
      />

      <div
        style={{
          padding: '16px 20px',
          borderBottom: `1px solid ${colors.borderColor}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative',
          zIndex: 2,
        }}
      >
        <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
          热门股票
        </Text>
        <Space size="small">
          {tabs.map((tab) => (
            <Tag
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                margin: 0,
                fontSize: '12px',
                padding: '4px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                background: activeTab === tab.key 
                  ? (theme === 'dark' ? 'rgba(86, 164, 255, 0.15)' : 'rgba(86, 164, 255, 0.1)')
                  : 'transparent',
                border: `1px solid ${activeTab === tab.key ? 'rgba(86, 164, 255, 0.4)' : colors.borderColor}`,
                color: activeTab === tab.key ? '#56A4FF' : colors.textSecondary,
              }}
              onMouseEnter={(e) => {
                if (activeTab !== tab.key) {
                  e.currentTarget.style.borderColor = 'rgba(86, 164, 255, 0.3)';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== tab.key) {
                  e.currentTarget.style.borderColor = colors.borderColor;
                }
              }}
            >
              {tab.label}
            </Tag>
          ))}
        </Space>
      </div>

      <div style={{ flex: 1, overflow: 'auto', position: 'relative', zIndex: 2 }}>
        <Table
          columns={columns}
          dataSource={mockHotStocks}
          pagination={false}
          size="small"
          rowKey="code"
          showHeader={true}
          onRow={(record) => ({
            onMouseEnter: () => setHoveredRow(record.code),
            onMouseLeave: () => setHoveredRow(null),
            onMouseDown: (e) => {
              (e.currentTarget as HTMLElement).style.transform = 'scale(0.99)';
            },
            onMouseUp: (e) => {
              (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
            },
            style: {
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              background: hoveredRow === record.code
                ? (theme === 'dark' ? 'rgba(86, 164, 255, 0.08)' : 'rgba(86, 164, 255, 0.05)')
                : 'transparent',
              borderLeft: hoveredRow === record.code
                ? '3px solid #56A4FF'
                : '3px solid transparent',
            },
          })}
        />
      </div>
    </div>
  );
};

export default HotStocks;
