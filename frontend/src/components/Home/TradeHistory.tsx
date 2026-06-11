import React from 'react';
import { Typography, Tag, Avatar, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, ShoppingOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import dayjs from 'dayjs';

const { Text } = Typography;

const tradeData = [
  { id: 1, type: 'buy', stock: '贵州茅台', code: '600519', price: 1568.50, quantity: 100, amount: 156850, time: '13:45:32', profit: 2850 },
  { id: 2, type: 'sell', stock: '比亚迪', code: '002594', price: 245.80, quantity: 500, amount: 122900, time: '11:23:18', profit: -1450 },
  { id: 3, type: 'buy', stock: '宁德时代', code: '300750', price: 198.56, quantity: 300, amount: 59568, time: '10:15:42', profit: 1200 },
  { id: 4, type: 'buy', stock: '腾讯控股', code: '00700', price: 328.60, quantity: 200, amount: 65720, time: '09:45:10', profit: 890 },
  { id: 5, type: 'sell', stock: '招商银行', code: '600036', price: 35.67, quantity: 1000, amount: 35670, time: '09:30:05', profit: 560 },
];

const TradeHistory: React.FC = () => {
  const { colors, theme } = useTheme();

  const totalProfit = tradeData.reduce((sum, t) => sum + t.profit, 0);

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        padding: '16px',
        height: '100%',
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
          width: '40%',
          height: '2px',
          background: 'linear-gradient(90deg, transparent 0%, #10B981 50%, transparent 100%)',
          opacity: 0.5,
          filter: 'blur(4px)',
          zIndex: 1,
        }}
      />

      <div style={{ position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShoppingOutlined style={{ color: '#10B981', fontSize: '18px' }} />
            <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
              今日成交
            </Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Tag color="blue" style={{ margin: 0, fontSize: '11px', padding: '2px 8px' }}>
              {tradeData.length} 笔
            </Tag>
            <Text style={{ color: totalProfit >= 0 ? '#10B981' : '#EF4444', fontSize: '14px', fontWeight: 700 }}>
              {totalProfit >= 0 ? '+' : ''}¥{totalProfit.toLocaleString()}
            </Text>
          </div>
        </div>

        <div style={{ maxHeight: '280px', overflow: 'auto' }}>
          {tradeData.map((item) => (
            <div
              key={item.id}
              style={{
                padding: '12px 10px',
                borderRadius: '10px',
                marginBottom: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                border: `1px solid ${colors.borderColor}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = theme === 'dark' ? 'rgba(86, 164, 255, 0.08)' : 'rgba(86, 164, 255, 0.05)';
                e.currentTarget.style.transform = 'translateX(4px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.transform = 'translateX(0)';
              }}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Avatar
                      size={28}
                      style={{
                        background: item.type === 'buy'
                          ? 'linear-gradient(135deg, #10B981 0%, #34D399 100%)'
                          : 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '12px',
                      }}
                    >
                      {item.type === 'buy' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                    </Avatar>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 600 }}>
                          {item.stock}
                        </Text>
                        <Tag
                          color={item.type === 'buy' ? 'green' : 'red'}
                          style={{ margin: 0, fontSize: '10px', padding: '0 6px', height: '18px', lineHeight: '16px' }}
                        >
                          {item.type === 'buy' ? '买入' : '卖出'}
                        </Tag>
                      </div>
                      <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                        {item.code} · {item.time}
                      </Text>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <Text style={{ color: colors.textPrimary, fontSize: '13px', fontWeight: 700 }}>
                      ¥{item.price.toFixed(2)}
                    </Text>
                    <div>
                      <Text style={{ color: colors.textSecondary, fontSize: '11px' }}>
                        {item.quantity}股 · ¥{item.amount.toLocaleString()}
                      </Text>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div
                    style={{
                      padding: '3px 10px',
                      borderRadius: '6px',
                      background: item.profit >= 0
                        ? 'rgba(16, 185, 129, 0.15)'
                        : 'rgba(239, 68, 68, 0.15)',
                    }}
                  >
                    <Text
                      style={{
                        color: item.profit >= 0 ? '#10B981' : '#EF4444',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      {item.profit >= 0 ? '+' : ''}¥{item.profit.toLocaleString()}
                    </Text>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TradeHistory;
