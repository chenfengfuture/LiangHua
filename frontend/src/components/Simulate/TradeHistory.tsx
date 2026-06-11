/**
 * 模拟交易 - 成交记录
 */

import React from 'react';
import { Table, Tag, Typography } from 'antd';
import { useTheme } from '@/themes';
import type { SimTrade } from '@/types/stock';

const { Text } = Typography;

interface Props {
  trades: SimTrade[];
  loading?: boolean;
}

const TradeHistory: React.FC<Props> = ({ trades, loading }) => {
  const { colors } = useTheme();

  const columns = [
    { title: '成交编号', dataIndex: 'id', width: 130, render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11, color: colors.textTertiary }}>{v}</Text> },
    { title: '股票', dataIndex: 'name', width: 100, render: (_: string, r: SimTrade) => <Text style={{ color: colors.textPrimary }}>{r.name}<Text style={{ color: colors.textTertiary, fontSize: 11, marginLeft: 4 }}>{r.symbol}</Text></Text> },
    {
      title: '方向', dataIndex: 'direction', width: 60,
      render: (v: string) => <Tag color={v === 'buy' ? 'red' : 'green'} style={{ margin: 0 }}>{v === 'buy' ? '买入' : '卖出'}</Tag>,
    },
    { title: '成交价', dataIndex: 'price', width: 90, align: 'right' as const, render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary }}>{v.toFixed(2)}</Text> },
    { title: '成交量', dataIndex: 'quantity', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary }}>{v.toLocaleString()}</Text> },
    { title: '成交额', dataIndex: 'amount', width: 110, align: 'right' as const, render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary }}>¥{v.toFixed(2)}</Text> },
    { title: '佣金', dataIndex: 'commission', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textTertiary, fontSize: 11 }}>¥{v.toFixed(2)}</Text> },
    { title: '时间', dataIndex: 'trade_date', width: 160, render: (v: string) => <Text style={{ fontSize: 11, color: colors.textTertiary, fontFamily: 'monospace' }}>{v.slice(0, 19).replace('T', ' ')}</Text> },
  ];

  return (
    <Table
      size="small"
      columns={columns}
      dataSource={trades}
      rowKey="id"
      loading={loading}
      scroll={{ x: 850 }}
      pagination={{ pageSize: 15, showSizeChanger: true, pageSizeOptions: ['10', '15', '30', '50'] }}
      locale={{ emptyText: '暂无成交记录' }}
    />
  );
};

export default React.memo(TradeHistory);