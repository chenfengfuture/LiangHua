import React from 'react';
import { Row, Col } from 'antd';
import StatCard from '../Common/StatCard';
import { mockIndexData } from '../../utils/mockData';
import { safeToFixed } from '../../utils/format';

const IndexCards: React.FC = () => {
  return (
    <Row gutter={[16, 16]}>
      {mockIndexData.map((index) => (
        <Col xs={24} sm={12} md={6} key={index.code}>
          <StatCard
            title={index.name}
            value={safeToFixed(index.value, 2)}
            change={index.change}
            changePercent={index.changePercent}
            suffix={
              <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.5)' }}>
                成交量: {index.volume}万手
              </div>
            }
          />
        </Col>
      ))}
    </Row>
  );
};

export default IndexCards;
