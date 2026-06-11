import React from 'react';
import { Row, Col, Space } from 'antd';
import { useTheme } from '@/themes';
import { ErrorBoundary } from '@/components/Common';
import IndexKLineCharts from './IndexKLineCharts';
import RightPanel from './RightPanel';
import HotBoards from './HotBoards';
import PerformancePanel from './PerformancePanel';
import StrategyList from './StrategyList';
import HotStocks from './HotStocks';
import TradeHistory from './TradeHistory';

const HomeDashboard: React.FC = () => {
  const { colors, theme } = useTheme();

  return (
    <div
      style={{
        background: colors.bgPrimary,
        minHeight: 'calc(100vh - 60px)',
        padding: '16px 20px',
        position: 'relative',
      }}
    >
      {/* 背景光效 */}
      <div
        style={{
          position: 'fixed',
          top: '80px',
          left: '50px',
          width: '500px',
          height: '500px',
          background: 'radial-gradient(circle, rgba(86, 164, 255, 0.1) 0%, transparent 60%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: 'fixed',
          bottom: '50px',
          right: '100px',
          width: '600px',
          height: '600px',
          background: 'radial-gradient(circle, rgba(81, 78, 189, 0.08) 0%, transparent 60%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <Space orientation="vertical" style={{ width: '100%', position: 'relative', zIndex: 1 }} size={16}>
        {/* 第一行：指数K线图 + 右侧面板 */}
        <Row gutter={[16, 0]}>
          <Col xs={24} lg={16}>
            <ErrorBoundary name="指数K线图"><IndexKLineCharts /></ErrorBoundary>
          </Col>
          <Col xs={24} lg={8}>
            <ErrorBoundary name="右侧面板"><RightPanel /></ErrorBoundary>
          </Col>
        </Row>

        {/* 第二行：今日热门板块 */}
        <Row gutter={[16, 0]}>
          <Col xs={24} lg={24}>
            <ErrorBoundary name="今日热门板块"><HotBoards /></ErrorBoundary>
          </Col>
        </Row>

        {/* 第三行：策略绩效面板 */}
        <ErrorBoundary name="策略绩效"><PerformancePanel /></ErrorBoundary>

        {/* 第四行：量化策略模块 */}
        <Row gutter={[16, 0]}>
          <Col xs={24} lg={24}>
            <ErrorBoundary name="策略列表"><StrategyList /></ErrorBoundary>
          </Col>
        </Row>

        {/* 第五行：热门股票 + 今日成交 */}
        <Row gutter={[16, 0]}>
          <Col xs={24} lg={10}>
            <ErrorBoundary name="热门股票"><HotStocks /></ErrorBoundary>
          </Col>
          <Col xs={24} lg={14}>
            <ErrorBoundary name="今日成交"><TradeHistory /></ErrorBoundary>
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default HomeDashboard;
