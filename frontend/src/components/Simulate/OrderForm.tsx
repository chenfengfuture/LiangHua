/**
 * 模拟交易 - 下单面板
 */

import React, { useState } from 'react';
import {
  Card, Input, InputNumber, Select, Button, message, Radio, Space, Typography, Divider,
} from 'antd';
import { SwapOutlined, FundOutlined } from '@ant-design/icons';
import { useTheme } from '@/themes';
import { stockCenterApi } from '@/api/stock/stockCenter';
import { placeOrder } from '@/api/simulate';
import type { SimAccount, SimPosition } from '@/types/stock';

const { Text } = Typography;

interface Props {
  account: SimAccount;
  positions: SimPosition[];
  onSuccess: () => void;
}

const OrderForm: React.FC<Props> = ({ account, positions, onSuccess }) => {
  const { colors } = useTheme();
  const [direction, setDirection] = useState<'buy' | 'sell'>('buy');
  const [symbol, setSymbol] = useState('');
  const [stockName, setStockName] = useState('');
  const [price, setPrice] = useState<number | null>(null);
  const [quantity, setQuantity] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const handleQueryPrice = async () => {
    if (!symbol.trim()) { message.warning('请输入股票代码'); return; }
    const pure = symbol.trim().replace(/^(sh|sz|bj)/i, '');
    setLoading(true);
    try {
      const today = new Date();
      const end = `${today.getFullYear()}${String(today.getMonth()+1).padStart(2,'0')}${String(today.getDate()).padStart(2,'0')}`;
      const start = `${today.getFullYear()}${String(today.getMonth()+1).padStart(2,'0')}01`;
      const kline = await stockCenterApi.getDailyKline(pure, 'daily', start, end, 'qfq');
      if (kline.length > 0) {
        const last = kline[kline.length - 1];
        setPrice(last.close_price);
        setStockName(last.symbol === pure ? pure : last.symbol);
        message.success(`最新价: ¥${last.close_price.toFixed(2)}`);
      } else {
        message.warning('未找到该股票数据');
      }
    } catch {
      message.error('查价失败，请手动输入价格');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    if (!symbol.trim()) { message.warning('请输入股票代码'); return; }
    if (price == null || price <= 0) { message.warning('请输入有效价格'); return; }
    if (quantity == null || quantity <= 0 || !Number.isInteger(quantity)) { message.warning('请输入有效数量（整数股）'); return; }

    const pure = symbol.trim().replace(/^(sh|sz|bj)/i, '');
    const maxQty = direction === 'sell'
      ? (positions.find((p) => p.symbol === pure)?.available_qty || 0)
      : Math.floor(account.available_cash / (price * 1.003));

    if (direction === 'sell' && quantity > maxQty) {
      message.warning(`可卖数量不足，最多可卖 ${maxQty} 股`);
      return;
    }

    if (direction === 'buy' && quantity > maxQty) {
      message.warning(`资金不足，最多可买 ${maxQty} 股`);
      return;
    }

    const result = placeOrder({ symbol: pure, name: stockName || pure, direction, price, quantity });
    if (result.success) {
      message.success(`${direction === 'buy' ? '买入' : '卖出'}成功！${direction === 'buy' ? `成交额 ¥${(price * quantity).toFixed(2)}` : `回笼资金 ¥${(price * quantity * 0.997).toFixed(2)}`}`);
      setQuantity(null);
      onSuccess();
    } else {
      message.error(result.message);
    }
  };

  const sellPositions = positions.filter((p) => p.available_qty > 0);

  return (
    <Card
      size="small"
      title={<span><FundOutlined /> 下单交易</span>}
      style={{ background: colors.bgCard, borderColor: colors.borderColor, height: '100%' }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        {/* 买卖方向 */}
        <Radio.Group
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          size="small"
          style={{ width: '100%' }}
        >
          <Radio.Button value="buy" style={{ width: '50%', textAlign: 'center', color: direction === 'buy' ? '#fff' : '#ff4d4f', background: direction === 'buy' ? '#ff4d4f' : undefined, borderColor: '#ff4d4f' }}>
            买入
          </Radio.Button>
          <Radio.Button value="sell" style={{ width: '50%', textAlign: 'center', color: direction === 'sell' ? '#fff' : '#52c41a', background: direction === 'sell' ? '#52c41a' : undefined, borderColor: '#52c41a' }}>
            卖出
          </Radio.Button>
        </Radio.Group>

        {/* 股票代码 */}
        <div>
          <Text style={{ color: colors.textSecondary, fontSize: 12, display: 'block', marginBottom: 4 }}>股票代码</Text>
          <Input
            size="small"
            placeholder="例: 600519"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            suffix={
              <Button size="small" type="link" onClick={handleQueryPrice} loading={loading} style={{ padding: 0, fontSize: 12 }}>
                查价
              </Button>
            }
          />
        </div>

        {/* 快速选择持仓（卖出时） */}
        {direction === 'sell' && sellPositions.length > 0 && (
          <div>
            <Text style={{ color: colors.textTertiary, fontSize: 11, display: 'block', marginBottom: 4 }}>选择持仓</Text>
            <Select
              size="small"
              placeholder="选择持仓股票"
              style={{ width: '100%' }}
              showSearch
              onChange={(val: string) => {
                setSymbol(val);
                const pos = positions.find((p) => p.symbol === val);
                if (pos) {
                  setStockName(pos.name);
                  setPrice(pos.current_price);
                  setQuantity(null);
                }
              }}
              filterOption={(input, option) => (option?.label as string || '').toLowerCase().includes(input.toLowerCase())}
              options={sellPositions.map((p) => ({
                value: p.symbol,
                label: `${p.name} (${p.symbol}) 可卖 ${p.available_qty} 股`,
              }))}
            />
          </div>
        )}

        <Divider style={{ margin: '4px 0' }} />

        {/* 价格 */}
        <div>
          <Text style={{ color: colors.textSecondary, fontSize: 12, display: 'block', marginBottom: 4 }}>委托价格</Text>
          <InputNumber
            size="small"
            style={{ width: '100%' }}
            placeholder="自动获取或手动输入"
            value={price}
            onChange={setPrice}
            min={0.01}
            step={0.01}
            precision={2}
            prefix="¥"
          />
        </div>

        {/* 数量 */}
        <div>
          <Text style={{ color: colors.textSecondary, fontSize: 12, display: 'block', marginBottom: 4 }}>
            数量（股）
            {direction === 'buy' && price != null && price > 0 && (
              <Text style={{ color: colors.textTertiary, fontSize: 11, marginLeft: 8 }}>
                可买最多 {Math.floor(account.available_cash / (price * 1.003))} 股
              </Text>
            )}
          </Text>
          <InputNumber
            size="small"
            style={{ width: '100%' }}
            placeholder="输入股数"
            value={quantity}
            onChange={setQuantity}
            min={100}
            step={100}
            precision={0}
          />
        </div>

        {/* 快捷数量 */}
        {price != null && price > 0 && (
          <Space size={4}>
            {direction === 'buy'
              ? [100, 500, 1000, 5000].map((n) => (
                  <Button key={n} size="small" type="dashed" onClick={() => {
                    const maxQty = Math.floor(account.available_cash / (price * 1.003));
                    const q = Math.min(n, maxQty);
                    if (q >= 100) setQuantity(Math.floor(q / 100) * 100);
                  }} style={{ fontSize: 11, padding: '0 6px' }}>{n}</Button>
                ))
              : undefined
            }
          </Space>
        )}

        {/* 预计费用 */}
        {price != null && quantity != null && quantity > 0 && (
          <div style={{ background: colors.bgSecondary, padding: '6px 8px', borderRadius: 4, fontSize: 12 }}>
            <Text style={{ color: colors.textTertiary }}>
              预计成交额: ¥{(price * quantity).toFixed(2)}
              <br />
              {direction === 'buy'
                ? `佣金: ¥${Math.max(price * quantity * 0.0003, 5).toFixed(2)}`
                : `佣金+印花税: ¥${(Math.max(price * quantity * 0.0003, 5) + price * quantity * 0.001).toFixed(2)}`
              }
            </Text>
          </div>
        )}

        {/* 提交 */}
        <Button
          type="primary"
          size="small"
          block
          danger={direction === 'buy'}
          style={direction === 'sell' ? { background: '#52c41a', borderColor: '#52c41a' } : {}}
          onClick={handleSubmit}
          icon={<SwapOutlined />}
        >
          {direction === 'buy' ? '买入' : '卖出'}
        </Button>
      </Space>
    </Card>
  );
};

export default React.memo(OrderForm);