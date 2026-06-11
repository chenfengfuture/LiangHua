/**
 * 模拟交易 - 持仓列表
 */

import React from 'react';
import { Table, Tag, Typography } from 'antd';
import { useTheme } from '@/themes';
import type { SimPosition } from '@/types/stock';

const { Text } = Typography;

const pctColor = (v: number): string => {
  if (v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

interface Props {
  positions: SimPosition[];
  loading?: boolean;
  onSell: (symbol: string, name: string) => void;
}

const Portfolio: React.FC<Props> = ({ positions, loading, onSell }) => {
  const { colors } = useTheme();

  const columns = [
    { title: '股票代码', dataIndex: 'symbol', width: 100, render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 12, color: colors.textPrimary }}>{v}</Text> },
    { title: '股票名称', dataIndex: 'name', width: 100, render: (v: string) => <Text style={{ fontWeight: 600, color: colors.textPrimary }}>{v}</Text> },
    { title: '持仓数量', dataIndex: 'quantity', width: 90, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary }}>{v.toLocaleString()}</Text> },
    { title: '成本价', dataIndex: 'cost_price', width: 90, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary, fontFamily: 'monospace' }}>{v.toFixed(2)}</Text> },
    { title: '现价', dataIndex: 'current_price', width: 90, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary, fontFamily: 'monospace' }}>{v.toFixed(2)}</Text> },
    { title: '市值', dataIndex: 'market_value', width: 100, align: 'right' as const, render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary }}>¥{v.toFixed(2)}</Text> },
    {
      title: '盈亏', dataIndex: 'profit_loss', width: 100, align: 'right' as const,
      render: (v: number) => <Text style={{ color: pctColor(v), fontFamily: 'monospace', fontWeight: 600 }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}</Text>,
    },
    {
      title: '盈亏%', dataIndex: 'profit_loss_pct', width: 90, align: 'right' as const,
      render: (v: number) => <Tag color={v >= 0 ? 'red' : 'green'} style={{ margin: 0, fontSize: 12 }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Tag>,
    },
    {
      title: '操作', width: 70, align: 'center' as const,
      render: (_: any, r: SimPosition) => (
        <a style={{ color: '#52c41a', fontSize: 12, cursor: 'pointer' }} onClick={() => onSell(r.symbol, r.name)}>卖出</a>
      ),
    },
  ];

  return (
    <Table
      size="small"
      columns={columns}
      dataSource={positions}
      rowKey="symbol"
      loading={loading}
      scroll={{ x: 850 }}
      pagination={false}
      locale={{ emptyText: '暂无持仓' }}
    />
  );
};

export default React.memo(Portfolio);