/**
 * 模拟交易 - 委托列表
 */

import React from 'react';
import { Table, Tag, Typography } from 'antd';
import { useTheme } from '@/themes';
import type { SimOrder } from '@/types/stock';

const { Text } = Typography;

interface Props {
  orders: SimOrder[];
  loading?: boolean;
}

const statusMap: Record<string, { label: string; color: string }> = {
  filled: { label: '已成交', color: '#10B981' },
  pending: { label: '待成交', color: '#F59E0B' },
  partial: { label: '部分成交', color: '#3B82F6' },
  cancelled: { label: '已撤单', color: '#999' },
};

const OrderList: React.FC<Props> = ({ orders, loading }) => {
  const { colors } = useTheme();

  const columns = [
    { title: '委托编号', dataIndex: 'id', width: 130, render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11, color: colors.textTertiary }}>{v}</Text> },
    { title: '股票', dataIndex: 'name', width: 100, render: (_: string, r: SimOrder) => <Text style={{ color: colors.textPrimary }}>{r.name}<Text style={{ color: colors.textTertiary, fontSize: 11, marginLeft: 4 }}>{r.symbol}</Text></Text> },
    {
      title: '方向', dataIndex: 'direction', width: 60,
      render: (v: string) => <Tag color={v === 'buy' ? 'red' : 'green'} style={{ margin: 0 }}>{v === 'buy' ? '买入' : '卖出'}</Tag>,
    },
    { title: '委托价', dataIndex: 'price', width: 90, align: 'right' as const, render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary }}>{v.toFixed(2)}</Text> },
    { title: '委托量', dataIndex: 'quantity', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary }}>{v.toLocaleString()}</Text> },
    { title: '成交量', dataIndex: 'filled_qty', width: 80, align: 'right' as const, render: (v: number) => <Text style={{ color: colors.textPrimary }}>{v.toLocaleString()}</Text> },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const s = statusMap[v] || { label: v, color: '#999' };
        return <Tag color={s.color} style={{ margin: 0 }}>{s.label}</Tag>;
      },
    },
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v: string) => <Text style={{ fontSize: 11, color: colors.textTertiary, fontFamily: 'monospace' }}>{v.slice(0, 19).replace('T', ' ')}</Text> },
  ];

  return (
    <Table
      size="small"
      columns={columns}
      dataSource={orders}
      rowKey="id"
      loading={loading}
      scroll={{ x: 850 }}
      pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50'] }}
      locale={{ emptyText: '暂无委托记录' }}
    />
  );
};

export default React.memo(OrderList);