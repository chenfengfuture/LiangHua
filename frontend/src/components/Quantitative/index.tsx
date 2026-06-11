import React from 'react';
import { Row, Col } from 'antd';
import QuantIndicators from './QuantIndicators';
import QuantSignals from './QuantSignals';
import MovingAverages from './MovingAverages';
import BollingerChart from './BollingerChart';
import BacktestChart from './BacktestChart';

const QuantitativeDashboard: React.FC = () => {
  return (
    <div style={{ padding: '0 8px' }}>
      {/* 技术指标和量化信号 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '20px' }}>
        <Col xs={24} md={12}>
          <QuantIndicators />
        </Col>
        <Col xs={24} md={12}>
          <QuantSignals />
        </Col>
      </Row>

      {/* 均线系统 */}
      <div style={{ marginBottom: '20px' }}>
        <MovingAverages />
      </div>

      {/* 布林带和回测收益 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <BollingerChart />
        </Col>
        <Col xs={24} md={12}>
          <BacktestChart />
        </Col>
      </Row>
    </div>
  );
};

export default QuantitativeDashboard;
