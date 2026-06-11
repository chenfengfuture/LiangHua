/**
 * 模拟交易 - 账户概览卡片
 */

import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import {
  WalletOutlined,
  DollarOutlined,
  StockOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import type { SimAccount } from '@/types/stock';

interface Props {
  account: SimAccount;
  totalProfit: number;
  totalProfitPct: number;
}

const pctColor = (v: number): string => {
  if (v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

const AccountSummary: React.FC<Props> = ({ account, totalProfit, totalProfitPct }) => {
  const { colors } = useTheme();

  const items = [
    {
      title: '总资产',
      value: account.total_assets.toFixed(2),
      prefix: '¥',
      color: colors.textPrimary,
      icon: <WalletOutlined style={{ color: '#3B82F6' }} />,
    },
    {
      title: '可用资金',
      value: account.available_cash.toFixed(2),
      prefix: '¥',
      color: colors.textPrimary,
      icon: <DollarOutlined style={{ color: '#10B981' }} />,
    },
    {
      title: '持仓市值',
      value: (account.total_assets - account.available_cash).toFixed(2),
      prefix: '¥',
      color: colors.textPrimary,
      icon: <StockOutlined style={{ color: '#F59E0B' }} />,
    },
    {
      title: '总盈亏',
      value: `${totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}`,
      suffix: <span style={{ fontSize: 13, color: pctColor(totalProfitPct), marginLeft: 4 }}>{totalProfitPct >= 0 ? '+' : ''}{totalProfitPct.toFixed(2)}%</span>,
      prefix: '¥',
      color: pctColor(totalProfit),
      icon: <RiseOutlined style={{ color: pctColor(totalProfit) }} />,
    },
  ];

  return (
    <Row gutter={12} style={{ marginBottom: 16 }}>
      {items.map((item) => (
        <Col span={6} key={item.title}>
          <Card
            size="small"
            style={{ background: colors.bgCard, borderColor: colors.borderColor }}
          >
            <Statistic
              title={<span>{item.icon} <span style={{ marginLeft: 4 }}>{item.title}</span></span>}
              value={item.value}
              prefix={item.prefix}
              suffix={item.suffix}
              valueStyle={{ color: item.color, fontSize: 22, fontWeight: 700 } as any}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

export default React.memo(AccountSummary);