import React from 'react';
import { Table } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { mockHotStocks } from '../../utils/mockData';
import { useTheme } from '../../themes';
import { safeNum, safeToFixed } from '../../utils/format';

const HotStocks: React.FC = () => {
  const { colors } = useTheme();

  const columns = [
    {
      title: '股票',
      key: 'name',
      render: (_: any, record: any) => (
        <div>
          <div style={{ color: colors.textPrimary, fontWeight: 500 }}>{record.name}</div>
          <div style={{ fontSize: '11px', color: colors.textTertiary }}>
            {record.code}
          </div>
        </div>
      ),
    },
    {
      title: '现价',
      dataIndex: 'price',
      key: 'price',
      render: (value: number) => (
        <span style={{ color: colors.textPrimary, fontWeight: 600 }}>
          {safeToFixed(value, 2)}
        </span>
      ),
    },
    {
      title: '涨跌',
      key: 'change',
      render: (_: any, record: any) => (
        <div style={{ textAlign: 'right' }}>
          <div
            className={safeNum(record.change) >= 0 ? 'text-up' : 'text-down'}
            style={{ fontWeight: 600 }}
          >
            {safeNum(record.change) >= 0 ? '+' : ''}{safeToFixed(record.change, 2)}
          </div>
          <div
            className={safeNum(record.changePercent) >= 0 ? 'text-up' : 'text-down'}
            style={{ fontSize: '11px' }}
          >
            {safeNum(record.changePercent) >= 0 ? '+' : ''}{safeToFixed(record.changePercent, 2)}%
          </div>
        </div>
      ),
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      render: (value: number) => (
        <span style={{ color: colors.textSecondary, fontSize: '12px' }}>
          {(value / 10000).toFixed(2)}万
        </span>
      ),
    },
  ];

  return (
    <DashboardCard title="热门股票" subtitle="实时热门个股">
      <Table
        columns={columns}
        dataSource={mockHotStocks}
        pagination={false}
        size="small"
        rowKey="code"
        style={{ background: 'transparent' }}
        scroll={{ y: 240 }}
      />
    </DashboardCard>
  );
};

export default HotStocks;