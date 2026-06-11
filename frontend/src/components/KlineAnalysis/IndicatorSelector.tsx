import React, { useMemo, useState } from 'react';
import { Select, Space, Tag, Typography } from 'antd';
import { useTheme } from '@/themes';

const { Text } = Typography;

export type IndicatorCategory = 'all' | 'trend' | 'oscillator' | 'volume' | 'overlay' | 'subchart';
export type TechnicalIndicatorKey = 'ma' | 'boll' | 'macd' | 'kdj' | 'rsi' | 'vol';
export type IndicatorPanelType = 'main' | 'sub';

export interface TechnicalIndicatorConfig {
  key: TechnicalIndicatorKey;
  label: string;
  name: string;
  category: Exclude<IndicatorCategory, 'all'>[];
  panel: IndicatorPanelType;
  params: string;
  description: string;
}

export const TECHNICAL_INDICATORS: TechnicalIndicatorConfig[] = [
  {
    key: 'ma',
    label: 'MA',
    name: '移动平均线',
    category: ['trend', 'overlay'],
    panel: 'main',
    params: '5,10,20,60',
    description: '主图叠加均线，识别价格趋势和支撑压力。',
  },
  {
    key: 'boll',
    label: 'BOLL',
    name: '布林带',
    category: ['trend', 'overlay'],
    panel: 'main',
    params: '20,2',
    description: '主图叠加中轨、上轨、下轨，观察波动区间。',
  },
  {
    key: 'macd',
    label: 'MACD',
    name: '指数平滑异同移动平均线',
    category: ['trend', 'subchart'],
    panel: 'sub',
    params: '12,26,9',
    description: 'DIF、DEA 与红绿柱，衡量趋势动能变化。',
  },
  {
    key: 'kdj',
    label: 'KDJ',
    name: '随机指标',
    category: ['oscillator', 'subchart'],
    panel: 'sub',
    params: '9,3,3',
    description: 'K、D、J 三线，衡量超买超卖和短线拐点。',
  },
  {
    key: 'rsi',
    label: 'RSI',
    name: '相对强弱指标',
    category: ['oscillator', 'subchart'],
    panel: 'sub',
    params: '6,12,24',
    description: '多周期相对强弱曲线，识别强弱切换。',
  },
  {
    key: 'vol',
    label: 'VOL',
    name: '成交量（含量能指标）',
    category: ['volume', 'subchart'],
    panel: 'sub',
    params: 'VWMA+VR+BIAS',
    description: '成交量柱 + VWMA (成交量加权均线) + VR (成交量比率) + Volume Bias (成交量乖离率)。',
  },
];

const CATEGORY_OPTIONS: Array<{ label: string; value: IndicatorCategory }> = [
  { label: '全部', value: 'all' },
  { label: '趋势类', value: 'trend' },
  { label: '震荡类', value: 'oscillator' },
  { label: '成交量类', value: 'volume' },
  { label: '主图叠加', value: 'overlay' },
  { label: '副图指标', value: 'subchart' },
];

interface IndicatorSelectorProps {
  value: TechnicalIndicatorKey;
  onChange: (value: TechnicalIndicatorKey) => void;
  dataCount: number;
  periodLabel?: string;
  symbol: string;
}

const IndicatorSelector: React.FC<IndicatorSelectorProps> = ({ value, onChange, dataCount, periodLabel, symbol }) => {
  const { colors } = useTheme();
  const [category, setCategory] = useState<IndicatorCategory>('all');
  const activeIndicator = TECHNICAL_INDICATORS.find((item) => item.key === value) ?? TECHNICAL_INDICATORS[0];

  const filteredIndicators = useMemo(() => {
    if (category === 'all') return TECHNICAL_INDICATORS;
    return TECHNICAL_INDICATORS.filter((item) => item.category.includes(category));
  }, [category]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 12, alignItems: 'center', marginBottom: 8 }}>
      <Space size={8} wrap>
        <Select
          size="small"
          value={category}
          onChange={setCategory}
          options={CATEGORY_OPTIONS}
          style={{ width: 110 }}
        />
        <Select
          size="small"
          value={value}
          onChange={onChange}
          style={{ width: 190 }}
          options={filteredIndicators.map((item) => ({
            value: item.key,
            label: `${item.label} - ${item.name}`,
          }))}
        />
        <Tag color={activeIndicator.panel === 'main' ? 'blue' : 'purple'}>
          {activeIndicator.panel === 'main' ? '主图叠加' : '副图指标'}
        </Tag>
        <Tag>{activeIndicator.label}({activeIndicator.params})</Tag>
        <Text style={{ color: colors.textSecondary, fontSize: 12 }}>
          {activeIndicator.description}
        </Text>
      </Space>
      <Text style={{ color: colors.textSecondary, fontSize: 12, whiteSpace: 'nowrap' }}>
        {symbol} — {periodLabel}{dataCount > 0 ? ` (${dataCount}条)` : ''}
      </Text>
    </div>
  );
};

export default IndicatorSelector;
