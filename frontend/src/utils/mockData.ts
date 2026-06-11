import dayjs from 'dayjs';

// 模拟指数数据
export const mockIndexData = [
  { name: '上证指数', code: '000001.SH', value: 3128.82, change: 0.85, changePercent: 0.027, volume: 2856, amount: 3421 },
  { name: '深证成指', code: '399001.SZ', value: 10245.68, change: 45.23, changePercent: 0.44, volume: 3542, amount: 4156 },
  { name: '创业板指', code: '399006.SZ', value: 2056.34, change: 18.56, changePercent: 0.91, volume: 1823, amount: 2234 },
  { name: '科创50', code: '000688.SH', value: 956.78, change: -3.45, changePercent: -0.36, volume: 456, amount: 678 },
];

// 模拟K线数据
export const generateKLineData = (days: number = 30) => {
  const data = [];
  let basePrice = 100;
  
  for (let i = days; i >= 0; i--) {
    const date = dayjs().subtract(i, 'day').format('YYYY-MM-DD');
    const volatility = Math.random() * 4 - 2;
    basePrice = basePrice + volatility;
    
    const open = basePrice + (Math.random() - 0.5) * 2;
    const close = basePrice + (Math.random() - 0.5) * 3;
    const high = Math.max(open, close) + Math.random() * 2;
    const low = Math.min(open, close) - Math.random() * 2;
    const volume = Math.floor(Math.random() * 1000000 + 500000);
    
    data.push({
      date,
      open: parseFloat(open.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      volume,
    });
  }
  
  return data;
};

// 模拟板块数据
export const mockSectorData = [
  { name: '人工智能', change: 3.45, count: 156, upCount: 142, downCount: 14, leader: '科大讯飞' },
  { name: '半导体', change: 2.87, count: 128, upCount: 115, downCount: 13, leader: '中芯国际' },
  { name: '新能源', change: 1.56, count: 245, upCount: 198, downCount: 47, leader: '宁德时代' },
  { name: '医药生物', change: -0.89, count: 312, upCount: 125, downCount: 187, leader: '恒瑞医药' },
  { name: '白酒', change: 2.34, count: 34, upCount: 31, downCount: 3, leader: '贵州茅台' },
  { name: '银行', change: 0.45, count: 42, upCount: 28, downCount: 14, leader: '招商银行' },
  { name: '证券', change: 1.23, count: 49, upCount: 41, downCount: 8, leader: '东方财富' },
  { name: '房地产', change: -1.56, count: 126, upCount: 35, downCount: 91, leader: '万科A' },
];

// 模拟热门股票
export const mockHotStocks = [
  { name: '贵州茅台', code: '600519', price: 1688.00, change: 28.50, changePercent: 1.72, volume: 23456 },
  { name: '宁德时代', code: '300750', price: 198.56, change: 5.67, changePercent: 2.94, volume: 45678 },
  { name: '比亚迪', code: '002594', price: 245.80, change: -3.40, changePercent: -1.36, volume: 67890 },
  { name: '腾讯控股', code: '00700', price: 328.60, change: 8.20, changePercent: 2.56, volume: 34567 },
  { name: '阿里巴巴', code: 'BABA', price: 85.45, change: 1.23, changePercent: 1.46, volume: 89012 },
  { name: '美团', code: '03690', price: 128.90, change: -2.30, changePercent: -1.75, volume: 23456 },
];

// 模拟涨跌分布
export const mockChangeDistribution = {
  limitUp: 68,
  up5: 125,
  up3: 234,
  up0: 890,
  down0: 780,
  down3: 345,
  down5: 156,
  limitDown: 23,
};

// 模拟资金流向
export const mockMoneyFlow = {
  date: Array.from({ length: 10 }, (_, i) => dayjs().subtract(9 - i, 'day').format('MM-DD')),
  mainForce: [45.6, 56.7, -23.4, 78.9, -12.3, 34.5, 67.8, -45.6, 89.0, 56.7],
  retail: [-23.4, -34.5, 12.6, -45.8, 8.9, -18.7, -38.9, 26.7, -52.3, -32.1],
};

// 模拟量化指标
export const mockQuantIndicators = {
  rsi: 58.5,
  macd: 2.34,
  signal: 1.89,
  kdj: { k: 62.3, d: 55.6, j: 75.8 },
  boll: { up: 112.5, mid: 100.0, down: 87.5 },
  ma5: 98.5,
  ma10: 95.2,
  ma20: 92.8,
  ma60: 88.6,
};

// 模拟量化信号
export const mockQuantSignals = [
  { type: 'buy', name: 'MACD金叉', time: '2026-05-08 10:30', stock: '贵州茅台', price: 1688.00 },
  { type: 'buy', name: 'RSI超卖反弹', time: '2026-05-08 09:45', stock: '宁德时代', price: 198.56 },
  { type: 'sell', name: 'KDJ死叉', time: '2026-05-08 11:15', stock: '比亚迪', price: 245.80 },
  { type: 'hold', name: '布林带中轨震荡', time: '2026-05-08 10:00', stock: '腾讯控股', price: 328.60 },
  { type: 'buy', name: '均线多头排列', time: '2026-05-07 14:30', stock: '招商银行', price: 35.67 },
];

// 模拟回测数据
export const mockBacktestData = {
  dates: Array.from({ length: 30 }, (_, i) => dayjs().subtract(29 - i, 'day').format('MM-DD')),
  strategy: Array.from({ length: 30 }, (_, i) => 100 + i * 0.8 + (Math.random() - 0.5) * 3),
  benchmark: Array.from({ length: 30 }, (_, i) => 100 + i * 0.3 + (Math.random() - 0.5) * 4),
};

// 模拟行情异动
export const mockMarketChanges = [
  { type: '火箭发射', name: '科大讯飞', code: '002230', time: '11:20:35', price: 58.67, change: 8.5 },
  { type: '快速反弹', name: '比亚迪', code: '002594', time: '11:18:22', price: 245.80, change: 2.3 },
  { type: '大笔买入', name: '贵州茅台', code: '600519', time: '11:15:10', price: 1688.00, change: 1.7 },
  { type: '封涨停板', name: '中芯国际', code: '688981', time: '11:10:45', price: 67.89, change: 20.0 },
  { type: '打开跌停板', name: '某ST股', code: '000001', time: '11:05:30', price: 5.67, change: -5.0 },
];

// 模拟盘口异动（按类型分类）
export const mockMarketChangesByType = {
  '火箭发射': [
    { name: '同源康', code: '300187', price: 38.65, change: 10.00, time: '13:42:46' },
    { name: '思特奇', code: '300608', price: 21.78, change: 7.48, time: '13:37:12' },
    { name: '宁德时代', code: '300750', price: 258.41, change: 4.26, time: '13:14:58' },
    { name: '寒武纪', code: '688256', price: 42.18, change: 2.83, time: '13:12:34' },
  ],
  '快速反弹': [
    { name: '比亚迪', code: '002594', price: 245.80, change: 2.3, time: '11:18:22' },
    { name: '贵州茅台', code: '600519', price: 1688.00, change: 1.7, time: '11:15:10' },
    { name: '招商银行', code: '600036', price: 35.67, change: 1.2, time: '11:10:45' },
  ],
  '大笔买入': [
    { name: '科大讯飞', code: '002230', price: 58.67, change: 8.5, time: '11:20:35' },
    { name: '中芯国际', code: '688981', price: 67.89, change: 20.0, time: '11:10:45' },
    { name: '隆基绿能', code: '601012', price: 28.56, change: 3.2, time: '11:05:30' },
  ],
  '封涨停板': [
    { name: '中芯国际', code: '688981', price: 67.89, change: 20.0, time: '11:10:45' },
    { name: '寒武纪', code: '688256', price: 42.18, change: 19.98, time: '11:05:30' },
    { name: '北方华创', code: '002371', price: 285.60, change: 10.0, time: '10:58:20' },
  ],
};

// 模拟行业/概念热力图数据
export const mockHeatmapData = [
  { name: '半导体', change: 4.62, fundFlow: 58.6, subItems: [] },
  { name: 'AI芯片', change: 3.85, fundFlow: 32.4, subItems: [] },
  { name: '重装车', change: 2.38, fundFlow: 18.5, subItems: [] },
  { name: '火电', change: 1.62, fundFlow: 12.3, subItems: [] },
  { name: '银行', change: 0.18, fundFlow: 5.6, subItems: [] },
  { name: '医药生物', change: -2.46, fundFlow: -28.1, subItems: [] },
  { name: '新能源', change: -3.21, fundFlow: -41.5, subItems: [] },
];

// 模拟主力净流入TOP10
export const mockMainForceTop10 = [
  { name: '宁德时代', code: '300750', changePercent: 4.86, mainForce: 18.6 },
  { name: '贵州茅台', code: '600519', changePercent: 2.34, mainForce: 14.2 },
  { name: '比亚迪', code: '002594', changePercent: 3.21, mainForce: 11.5 },
  { name: '科大讯飞', code: '002230', changePercent: 6.78, mainForce: 9.8 },
  { name: '卓尔智联', code: '02098', changePercent: 5.65, mainForce: 8.4 },
];

// 模拟连板梯队
export const mockLimitUpStreak = [
  { boardCount: 8, name: '同源康', code: '300187', industry: '医药', changePercent: 10.0 },
  { boardCount: 5, name: '成都先导', code: '688222', industry: '半导体', changePercent: 10.02 },
  { boardCount: 3, count: 41, upCount: 22, downCount: 19, changePercent: 0 },
];

// 模拟龙虎榜数据
export const mockDragonTigerList = [
  { name: '宁德时代', code: '300750', reason: '上榜原因：中信证券净买入达 5%', netBuy: 4.2, orgNetBuy: 4.2 },
  { name: '中金公司', code: '601995', reason: '上榜原因：安信证券净买：完成 0.95% 净买', netBuy: 2.8, deptNetBuy: 2.8 },
  { name: '果麦文化', code: '300690', reason: '上榜原因：跌幅偏离值：-11.6%', netBuy: -1.6, netSell: 1.6 },
];

// 模拟整体市场统计
export const mockMarketStats = {
  mainForceNetFlow: 182.46,
  mainForceChange: 96.52,
  superBigOrderChange: 96.05,
  bigOrderChange: 0.46,
  midOrderChange: -52.11,
  smallOrderChange: -130.35,
  limitUpCount: 82,
  limitDownCount: 14,
  yesterdayLimitUpTodayAvg: 3.8,
  todayOpenLimitUp: 49,
  upCount: 2816,
  downCount: 1802,
};
