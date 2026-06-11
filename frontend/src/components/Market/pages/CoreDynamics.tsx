/**
 * 核心动态页面 - 市场概览子页面
 *
 * 包含子模块：
 *   1. 当日涨幅榜单（DailySurgePanel）
 *
 * 独立于个股中心，与行情与K线、个股中心同层级。
 */

import React from 'react';
import { RiseOutlined } from '@ant-design/icons';
import { Typography } from 'antd';
import { useTheme } from '@/themes';
import DailySurgePanel from './DailySurgePanel';

const { Title } = Typography;

const CoreDynamics: React.FC = () => {
  const { colors } = useTheme();

  return (
    <div className="page-layout" style={{ padding: '0 4px 8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
        <RiseOutlined style={{ fontSize: 20, color: '#ff4d4f', marginRight: 8 }} />
        <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>核心动态</Title>
      </div>
      <div className="flex-content" style={{ overflow: 'hidden' }}>
        <DailySurgePanel />
      </div>
    </div>
  );
};

export default React.memo(CoreDynamics);