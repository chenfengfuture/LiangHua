import React from 'react';
import { Table, Tag, Progress } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { useTheme } from '../../themes';
import { mockSectorData } from '../../utils/mockData';
import { safeNum, safeToFixed } from '../../utils/format';

const SectorList: React.FC = () => {
  const { colors } = useTheme();

  const columns = [
    {
      title: '板块名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <span style={{ color: colors.textPrimary, fontWeight: 500 }}>{text}</span>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change',
      key: 'change',
      render: (value: number) => (
        <span style={{ color: safeNum(value) >= 0 ? '#ff4d4f' : '#52c41a', fontWeight: 600 }}>
          {safeNum(value) >= 0 ? '+' : ''}{safeToFixed(value, 2)}%
        </span>
      ),
      sorter: (a: any, b: any) => a.change - b.change,
    },
    {
      title: '上涨/下跌',
      key: 'updown',
      render: (_: any, record: any) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Progress
            percent={Math.round((record.upCount / record.count) * 100)}
            showInfo={false}
            strokeColor="#ff4d4f"
            railColor="#52c41a"
            size="small"
            style={{ width: '80px' }}
          />
          <span style={{ fontSize: '12px', color: colors.textTertiary }}>
            {record.upCount}/{record.downCount}
          </span>
        </div>
      ),
    },
    {
      title: '龙头股',
      dataIndex: 'leader',
      key: 'leader',
      render: (text: string) => (
        <Tag color="purple" style={{ margin: 0 }}>
          {text}
        </Tag>
      ),
    },
  ];

  return (
    <DashboardCard title="行业板块" subtitle="实时板块涨跌">
      <Table
        columns={columns}
        dataSource={mockSectorData}
        pagination={false}
        size="small"
        rowKey="name"
        style={{ background: 'transparent' }}
        scroll={{ y: 240 }}
        rowClassName={() => 'table-row-transparent'}
      />
    </DashboardCard>
  );
};

export default SectorList;
