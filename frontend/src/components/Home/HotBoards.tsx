import React from 'react';
import { Typography, Row, Col } from 'antd';
import { ArrowUpOutlined, FundOutlined, RiseOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

interface BoardData {
  id: string;
  name: string;
  changePercent: number;
  netInflow: number;
  leadStock: string;
  stockCount: number;
}

const mockHotBoards: BoardData[] = [
  { id: '1', name: '半导体', changePercent: 3.85, netInflow: 28.5, leadStock: '北方华创', stockCount: 156 },
  { id: '2', name: '新能源汽车', changePercent: 2.67, netInflow: 19.8, leadStock: '比亚迪', stockCount: 89 },
  { id: '3', name: '人工智能', changePercent: 2.45, netInflow: 15.2, leadStock: '科大讯飞', stockCount: 124 },
  { id: '4', name: '光伏储能', changePercent: 1.98, netInflow: 12.6, leadStock: '隆基绿能', stockCount: 78 },
  { id: '5', name: '医药生物', changePercent: 1.56, netInflow: 8.9, leadStock: '恒瑞医药', stockCount: 234 },
  { id: '6', name: '白酒', changePercent: 1.23, netInflow: 6.5, leadStock: '贵州茅台', stockCount: 45 },
];

const HotBoards: React.FC = () => {
  const { colors, theme } = useTheme();

  return (
    <div
      style={{
        background: colors.bgCard,
        border: `1px solid ${colors.borderColor}`,
        borderRadius: '12px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 标题栏 */}
      <div
        style={{
          padding: '16px 20px 12px',
          borderBottom: `1px solid ${colors.borderColor}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <RiseOutlined style={{ color: '#56A4FF', fontSize: '16px' }} />
          <Text style={{ color: colors.textPrimary, fontSize: '15px', fontWeight: 700 }}>
            今日热门板块
          </Text>
        </div>
        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
          实时更新 · 按资金流入排序
        </Text>
      </div>

      {/* 板块网格 - 2行3列 */}
      <div style={{ padding: '16px 20px' }}>
        <Row gutter={[12, 12]}>
          {mockHotBoards.map((board, index) => {
            const isUp = board.changePercent >= 0;
            
            return (
              <Col xs={24} sm={12} md={8} key={board.id}>
                <div
                  style={{
                    background: colors.bgSecondary,
                    border: `1px solid ${colors.borderColor}`,
                    borderRadius: '10px',
                    padding: '14px 16px',
                    position: 'relative',
                  }}
                >
                  {/* 排名标签 */}
                  <div
                    style={{
                      position: 'absolute',
                      top: '8px',
                      right: '10px',
                      width: '22px',
                      height: '22px',
                      borderRadius: '6px',
                      background: index < 3 
                        ? 'linear-gradient(135deg, #56A4FF 0%, #514EBD 100%)' 
                        : colors.borderColor,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontWeight: 700,
                      color: '#fff',
                    }}
                  >
                    {index + 1}
                  </div>

                  {/* 板块名称 */}
                  <div style={{ marginBottom: '10px' }}>
                    <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 700 }}>
                      {board.name}
                    </Text>
                    <Text style={{ color: colors.textTertiary, fontSize: '11px', marginLeft: '6px' }}>
                      {board.stockCount}只股票
                    </Text>
                  </div>

                  {/* 涨幅 */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <ArrowUpOutlined style={{ color: '#EF4444', fontSize: '10px' }} />
                      <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                        涨幅
                      </Text>
                    </div>
                    <Text
                      style={{
                        color: '#EF4444',
                        fontSize: '13px',
                        fontWeight: 700,
                      }}
                    >
                      +{board.changePercent.toFixed(2)}%
                    </Text>
                  </div>

                  {/* 资金流入 */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FundOutlined style={{ color: '#56A4FF', fontSize: '10px' }} />
                      <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                        资金净流入
                      </Text>
                    </div>
                    <Text
                      style={{
                        color: '#56A4FF',
                        fontSize: '13px',
                        fontWeight: 700,
                      }}
                    >
                      +{board.netInflow}亿
                    </Text>
                  </div>

                  {/* 领涨股 */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                      领涨股
                    </Text>
                    <Text
                      style={{
                        color: colors.textSecondary,
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      {board.leadStock}
                    </Text>
                  </div>
                </div>
              </Col>
            );
          })}
        </Row>
      </div>
    </div>
  );
};

export default HotBoards;
