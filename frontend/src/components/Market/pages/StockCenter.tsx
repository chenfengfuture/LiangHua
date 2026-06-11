/**
 * 个股中心页面 - 市场概览子页面
 *
 * 对接后端接口（仅保留实测可用）：
 *   - GET /api/stock/get-stock-zh-a-hist           日/周/月 K 线
 *   - GET /api/stock/get-stock-zh-a-hist-min-em    分钟级 K 线（mootdx）
 *   - GET /api/stock/get-stock-financial-report-sina  财务报表（资产/利润/现金流）
 *   - GET /api/stock/get-stock_hot_keyword_em      热门概念关键词
 *   - GET /api/stock/get-stock-comment-focus-em    用户关注指数
 *   - GET /api/stock/get-stock-comment-desire-em   市场参与意愿
 *   - GET /api/stock/get-stock-gdhs-detail-em      股东户数详情
 *
 * Tab 布局：
 *   1. K线行情：日/周/月线 + 分钟线
 *   2. 概况：股票输入 + 热门关键词 + 股东户数概览（最近5期）
 *   3. 财务报表：资产负债表/利润表/现金流量表
 *   4. 千股千评：关注指数 + 参与意愿
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Tabs,
  Table,
  Typography,
  Space,
  Select,
  Input,
  Button,
  Tag,
  Card,
  Row,
  Col,
  Statistic,
  message,
  DatePicker,
  Empty,
  Radio,
} from 'antd';
import {
  SearchOutlined,
  StockOutlined,
  LineChartOutlined,
  FundOutlined,
  CommentOutlined,
  ReloadOutlined,
  TeamOutlined,
  FireOutlined,
  BarChartOutlined,
  TableOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import dayjs, { Dayjs } from 'dayjs';
import { useTheme } from '@/themes';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { stockCenterApi } from '@/api/stock';
import { readDailyCache, writeDailyCache, clearDailyCache, makeKey, TTL } from '@/utils/dailyCache';
import type {
  StockHotKeyword,
  StockKlineDaily,
  StockKlineMinute,
  StockBalanceSheet,
  StockCommentFocus,
  StockCommentDesire,
  StockHolderDetail,
  KlinePeriod,
} from '../../../types/stock';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;

// ─── 工具函数 ─────────────────────────────────────────────────────────

/** 涨跌色（中国规则：红涨绿跌） */
const pctColor = (v: number | null | undefined): string => {
  if (v == null || v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

/** 安全数字格式化 */
const fmtNum = (v: number | null | undefined, digits = 2): string => {
  if (v == null || isNaN(v as number)) return '--';
  return Number(v).toFixed(digits);
};

/** 元 → 亿/万 */
const fmtYi = (v: number | null | undefined): string => {
  if (v == null || isNaN(v as number)) return '--';
  const n = Number(v);
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万';
  return n.toFixed(2);
};

/** 数字 → 千分位字符串 */
const fmtThousand = (v: number | null | undefined): string => {
  if (v == null || isNaN(v as number)) return '--';
  return Number(v).toLocaleString('zh-CN');
};

/**
 * 自动识别股票代码市场前缀
 * 输入 600519 → sh600519，000001 → sz000001，688xxx → sh，300xxx → sz，8xxxxx → bj
 */
const detectMarket = (code: string): string => {
  const c = code.trim().toUpperCase();
  // 已带前缀
  if (/^(SH|SZ|BJ|HK|US)/.test(c)) return c.toLowerCase();
  if (!/^\d+$/.test(c)) return c.toLowerCase();
  const padded = c.padStart(6, '0');
  const first = padded.charAt(0);
  if (first === '6' || padded.startsWith('688') || padded.startsWith('900')) return 'sh' + padded;
  if (first === '0' || first === '3' || padded.startsWith('200')) return 'sz' + padded;
  if (first === '8' || first === '4') return 'bj' + padded;
  return padded;
};

/** 转大写带前缀的雪球/EM 格式（SH600519） */
const toUpperMarket = (code: string): string => {
  const c = detectMarket(code);
  return c.toUpperCase();
};

/** 提取纯 6 位代码（去掉 sh/sz/bj 前缀） */
const stripMarket = (code: string): string => {
  return code.replace(/^(sh|sz|bj|SH|SZ|BJ)/i, '');
};

// 默认股票
const DEFAULT_SYMBOL = '600519';

/** 计算 K 线移动平均线（基于收盘价） */
const calcMA = (n: number, ohlc: number[][]): (number | string)[] => {
  const result: (number | string)[] = [];
  for (let i = 0; i < ohlc.length; i++) {
    if (i < n - 1) {
      result.push('-');
      continue;
    }
    let sum = 0;
    for (let j = 0; j < n; j++) {
      sum += ohlc[i - j][1] || 0; // close
    }
    result.push(+(sum / n).toFixed(2));
  }
  return result;
};

// ─── 主组件 ─────────────────────────────────────────────────────────
const StockCenter: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState<string>('kline');

  // 输入控制（输入框中的值）
  const [inputCode, setInputCode] = useState<string>(DEFAULT_SYMBOL);
  // 已生效的股票代码（点击查询/回车后才更新）
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);

  const handleSearch = useCallback(() => {
    const code = inputCode.trim();
    if (!code) {
      message.warning('请输入股票代码');
      return;
    }
    setSymbol(stripMarket(code));
  }, [inputCode]);

  return (
    <div className="page-layout">
      {/* 标题栏 + 股票搜索 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
          gap: '12px',
          flexShrink: 0,
        }}
      >
        <Space size="small" align="center">
          <StockOutlined style={{ color: '#ACA9CC', fontSize: '18px' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>
            个股中心
          </Title>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>·</Text>
          <Text style={{ color: colors.textTertiary, fontSize: '13px' }}>
            当前：<Text style={{ color: '#56A4FF', fontFamily: 'monospace', fontWeight: 600 }}>{toUpperMarket(symbol)}</Text>
          </Text>
        </Space>

        <Space size="small">
          <Input
            placeholder="输入股票代码（如 600519）"
            value={inputCode}
            onChange={(e) => setInputCode(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            size="middle"
            style={{ width: 220 }}
            prefix={<SearchOutlined style={{ color: colors.textTertiary }} />}
          />
          <Button type="primary" size="middle" onClick={handleSearch}>
            查询
          </Button>
        </Space>
      </div>

      {/* Tab 切换 */}
      <div className="flex-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="middle"
          style={{ height: '100%' }}
          items={[
          {
            key: 'kline',
            label: (
              <span>
                <LineChartOutlined /> K线行情
              </span>
            ),
            children: <KlinePanel symbol={symbol} />,
          },
          {
            key: 'overview',
            label: (
              <span>
                <FireOutlined /> 概况
              </span>
            ),
            children: <OverviewPanel symbol={symbol} />,
          },
          {
            key: 'finance',
            label: (
              <span>
                <FundOutlined /> 财务报表
              </span>
            ),
            children: <FinancePanel symbol={symbol} />,
          },
          {
            key: 'comment',
            label: (
              <span>
                <CommentOutlined /> 千股千评
              </span>
            ),
            children: <CommentPanel symbol={symbol} />,
          },
        ]}
      />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════

interface PanelProps { symbol: string }

const OverviewPanel: React.FC<PanelProps> = ({ symbol }) => {
  const { colors } = useTheme();
  const [keywords, setKeywords] = useState<StockHotKeyword[]>([]);
  const [holders, setHolders] = useState<StockHolderDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [stockName, setStockName] = useState<string>('');

  const fetchAll = useCallback(async (force = false) => {
    const cacheKey = makeKey('stockCenter:overview', { symbol });
    if (!force) {
      const cached = readDailyCache<{ keywords: StockHotKeyword[]; holders: StockHolderDetail[]; stockName: string }>(
        cacheKey,
        { ttlMs: TTL.MEDIUM },
      );
      if (cached) {
        setKeywords(cached.keywords);
        setHolders(cached.holders);
        setStockName(cached.stockName);
        return;
      }
    }
    setLoading(true);
    try {
      const upper = toUpperMarket(symbol);
      const [kw, hd] = await Promise.allSettled([
        stockCenterApi.getHotKeywords(upper),
        stockCenterApi.getHolderDetail(stripMarket(symbol)),
      ]);
      const kwData = kw.status === 'fulfilled' ? (kw.value || []) : [];
      const hdData = hd.status === 'fulfilled' ? (hd.value || []) : [];
      const name = hdData.length > 0 ? (hdData[0].name || '') : '';
      setKeywords(kwData);
      setHolders(hdData);
      if (name) setStockName(name);
      writeDailyCache(cacheKey, { keywords: kwData, holders: hdData, stockName: name });
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const latest = holders.length > 0 ? holders[holders.length - 1] : null;
  const recent5 = useMemo(() => holders.slice(-5).reverse(), [holders]);
  const upperSym = toUpperMarket(symbol);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Text style={{ color: colors.textPrimary, fontSize: '14px', fontWeight: 600 }}>
          {stockName ? (stockName + '（' + upperSym + '）') : ('股票代码：' + upperSym)}
        </Text>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchAll(true)} loading={loading}>
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            size="small"
            title={<Space size={6}><TeamOutlined style={{ color: '#56A4FF' }} /><span>股东户数概览</span></Space>}
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {latest ? (
              <>
                <Row gutter={[12, 12]}>
                  <Col span={8}>
                    <Statistic
                      title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>最新股东户数</Text>}
                      value={latest.holder_num_current}
                      formatter={(v) => fmtThousand(v as number)}
                      styles={{ content: { color: colors.textPrimary, fontSize: 20, fontWeight: 700 } }}
                    />
                    <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>截至 {latest.end_date}</Text>
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>户数变化</Text>}
                      value={latest.holder_num_change}
                      formatter={(v) => (Number(v) >= 0 ? '+' : '') + fmtThousand(v as number)}
                      styles={{ content: { color: pctColor(latest.holder_num_change), fontSize: 20, fontWeight: 700 } }}
                    />
                    <Text style={{ color: pctColor(latest.holder_num_change_pct), fontSize: '11px' }}>
                      {latest.holder_num_change_pct >= 0 ? '+' : ''}{fmtNum(latest.holder_num_change_pct, 2)}%
                    </Text>
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>户均持股市值</Text>}
                      value={latest.avg_market_cap_per_holder}
                      formatter={(v) => fmtYi(v as number)}
                      styles={{ content: { color: colors.textPrimary, fontSize: 20, fontWeight: 700 } }}
                    />
                    <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                      户均持股 {fmtThousand(Math.round(latest.avg_share_per_holder))} 股
                    </Text>
                  </Col>
                </Row>

                <div style={{ marginTop: 16 }}>
                  <Text style={{ color: colors.textSecondary, fontSize: '12px', fontWeight: 600 }}>近 5 期变化</Text>
                  <Table
                    columns={[
                      { title: '截止日', dataIndex: 'end_date', width: 100, render: (v: string) => <Text style={{ fontSize: '12px', color: colors.textPrimary }}>{v}</Text> },
                      { title: '股东户数', dataIndex: 'holder_num_current', align: 'right' as const, render: (v: number) => fmtThousand(v) },
                      { title: '变化', dataIndex: 'holder_num_change', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{fmtThousand(v)}</Text> },
                      { title: '变化幅度', dataIndex: 'holder_num_change_pct', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{fmtNum(v, 2)}%</Text> },
                      { title: '区间涨跌', dataIndex: 'interval_pct_change', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{fmtNum(v, 2)}%</Text> },
                    ]}
                    dataSource={recent5}
                    rowKey="end_date"
                    size="small"
                    pagination={false}
                    style={{ marginTop: 8 }}
                  />
                </div>
              </>
            ) : (
              <Empty description="暂无股东户数数据" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={<Space size={6}><FireOutlined style={{ color: '#F59E0B' }} /><span>所属概念 / 热度</span></Space>}
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {keywords.length > 0 ? (
              <>
                <Text style={{ color: colors.textTertiary, fontSize: '11px', display: 'block', marginBottom: 10 }}>
                  数据时间：{keywords[0]?.stat_date}
                </Text>
                <Space size={[8, 8]} wrap>
                  {keywords.map((k) => (
                    <Tag key={k.concept_code} color="orange" style={{ padding: '6px 12px', fontSize: '13px' }}>
                      {k.concept_name}
                      <Text style={{ color: '#fff', marginLeft: 8, fontSize: '11px', opacity: 0.9 }}>
                        🔥 {fmtThousand(k.heat)}
                      </Text>
                    </Tag>
                  ))}
                </Space>
              </>
            ) : (
              <Empty description="暂无关键词" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 2: K线行情（日/周/月 + 分钟）
// ═══════════════════════════════════════════════════════════════════

const KlinePanel: React.FC<PanelProps> = ({ symbol }) => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [klineType, setKlineType] = useState<'daily' | 'minute'>('daily');
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [subIndicator, setSubIndicator] = useState<'volume' | 'macd' | 'kdj' | 'rsi'>('volume');
  const [period, setPeriod] = useState<KlinePeriod>('daily');
  const [minutePeriod, setMinutePeriod] = useState<string>('15');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(1, 'year'),
    dayjs(),
  ]);
  const [adjust, setAdjust] = useState<string>('qfq');

  const [daily, setDaily] = useState<StockKlineDaily[]>([]);
  const [minute, setMinute] = useState<StockKlineMinute[]>([]);
  const [loading, setLoading] = useState(false);

  // K线图 echarts 容器
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const fetchData = useCallback(async (force = false) => {
    const pureSymbol = stripMarket(symbol);
    const start = dateRange[0].format('YYYYMMDD');
    const end = dateRange[1].format('YYYYMMDD');
    const cacheKey = klineType === 'daily'
      ? makeKey('stockCenter:kline:daily', { symbol: pureSymbol, period, start, end, adjust })
      : makeKey('stockCenter:kline:minute', { symbol: pureSymbol, minutePeriod, start, end });
    // K线一般日内不变（日线/分钟历史段），用 MEDIUM TTL；若 end 为今日，盘中可能有未收数据，TTL=SHORT 兜底
    const isToday = dateRange[1].isSame(dayjs(), 'day');
    const ttl = isToday ? TTL.SHORT : TTL.DAY;
    // ⚠️ 关键：cached 是 [] 时 Boolean([]) === true 会误命中。必须用 length 校验，
    // 否则一旦缓存了空数组（接口超时/首次失败/数据真为空），后续永远走不到 API。
    if (!force) {
      if (klineType === 'daily') {
        const cached = readDailyCache<StockKlineDaily[]>(cacheKey, { ttlMs: ttl });
        if (cached && cached.length > 0) {
          if (import.meta.env.DEV) console.debug('[KLine] 命中日线缓存', cacheKey, cached.length, '条');
          setDaily(cached); setMinute([]); return;
        }
        if (cached) {
          // 缓存是空数组 → 视为脏数据，清除后重新请求
          if (import.meta.env.DEV) console.debug('[KLine] 清除空缓存', cacheKey);
          clearDailyCache(cacheKey);
        }
      } else {
        const cached = readDailyCache<StockKlineMinute[]>(cacheKey, { ttlMs: ttl });
        if (cached && cached.length > 0) {
          if (import.meta.env.DEV) console.debug('[KLine] 命中分钟缓存', cacheKey, cached.length, '条');
          setMinute(cached); setDaily([]); return;
        }
        if (cached) {
          if (import.meta.env.DEV) console.debug('[KLine] 清除空缓存', cacheKey);
          clearDailyCache(cacheKey);
        }
      }
    }
    setLoading(true);
    try {
      if (klineType === 'daily') {
        const result = await stockCenterApi.getDailyKline(pureSymbol, period, start, end, adjust);
        const data = result || [];
        if (import.meta.env.DEV) console.debug('[KLine] 日线 API 返回', pureSymbol, data.length, '条');
        setDaily(data);
        setMinute([]);
        // 只缓存非空数据，避免脏缓存阻塞后续请求
        if (data.length > 0) writeDailyCache(cacheKey, data);
        else message.warning('日线数据为空，可尝试调整复权方式或日期');
      } else {
        const result = await stockCenterApi.getMinuteKline(pureSymbol, minutePeriod, start, end);
        const data = result || [];
        if (import.meta.env.DEV) console.debug('[KLine] 分钟 API 返回', pureSymbol, data.length, '条');
        setMinute(data);
        setDaily([]);
        if (data.length > 0) writeDailyCache(cacheKey, data);
        else message.warning('分钟数据为空');
      }
    } catch (e: any) {
      console.error('[KLine] 查询失败', e);
      message.error('查询失败: ' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [symbol, klineType, period, minutePeriod, adjust, dateRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ─── K线图（candlestick + 成交量）渲染 ─────────────────────────────
  // 数据源：日线模式用 daily（trade_date/open_price/...），分钟模式用 minute（datetime/open/...）
  const chartData = useMemo(() => {
    if (klineType === 'daily') {
      const sorted = [...daily].sort((a, b) =>
        String(a.trade_date).localeCompare(String(b.trade_date))
      );
      return {
        dates: sorted.map((r) => r.trade_date),
        ohlc: sorted.map((r) => [r.open_price, r.close_price, r.low_price, r.high_price]),
        volumes: sorted.map((r) => r.volume || 0),
      };
    }
    const sorted = [...minute].sort((a, b) =>
      String(a.datetime).localeCompare(String(b.datetime))
    );
    return {
      dates: sorted.map((r) => r.datetime),
      ohlc: sorted.map((r) => [r.open, r.close, r.low, r.high]),
      volumes: sorted.map((r) => r.volume || r.vol || 0),
    };
  }, [klineType, daily, minute]);

  // ── 技术指标计算（前端侧，基于 OHLC 数据） ──
  const indicators = useMemo(() => {
    const closes = chartData.ohlc.map((o) => o[1]);
    const highs = chartData.ohlc.map((o) => o[3]);
    const lows = chartData.ohlc.map((o) => o[2]);

    // MA60
    const ma60 = calcMA(60, chartData.ohlc);

    // MACD (12, 26, 9)
    const ema12: number[] = [];
    const ema26: number[] = [];
    const dif: (number | string)[] = [];
    const dea: (number | string)[] = [];
    const macdBar: (number | string)[] = [];
    const a12 = 2 / 13, a26 = 2 / 27, a9 = 2 / 10;
    for (let i = 0; i < closes.length; i++) {
      ema12[i] = i === 0 ? closes[i] : a12 * closes[i] + (1 - a12) * ema12[i - 1];
      ema26[i] = i === 0 ? closes[i] : a26 * closes[i] + (1 - a26) * ema26[i - 1];
      const dv = ema12[i] - ema26[i];
      dif[i] = i < 25 ? '-' : +dv.toFixed(4);
      if (i < 25) { dea[i] = '-'; macdBar[i] = '-'; continue; }
      const prevDea = i === 25 ? dv : (dea[i - 1] as number);
      const curDea = a9 * dv + (1 - a9) * prevDea;
      dea[i] = +curDea.toFixed(4);
      macdBar[i] = +((dv - curDea) * 2).toFixed(4);
    }

    // KDJ (9, 3, 3)
    const k: (number | string)[] = [];
    const d: (number | string)[] = [];
    const j: (number | string)[] = [];
    for (let i = 0; i < closes.length; i++) {
      if (i < 8) { k[i] = '-'; d[i] = '-'; j[i] = '-'; continue; }
      const hh = Math.max(...highs.slice(i - 8, i + 1));
      const ll = Math.min(...lows.slice(i - 8, i + 1));
      const rsv = hh === ll ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
      const prevK = i === 8 ? 50 : (k[i - 1] as number);
      const prevD = i === 8 ? 50 : (d[i - 1] as number);
      const curK = (2 / 3) * prevK + (1 / 3) * rsv;
      const curD = (2 / 3) * prevD + (1 / 3) * curK;
      k[i] = +curK.toFixed(2);
      d[i] = +curD.toFixed(2);
      j[i] = +(3 * curK - 2 * curD).toFixed(2);
    }

    // RSI (6, 12, 24)
    const calcRSI = (n: number): (number | string)[] => {
      const r: (number | string)[] = [];
      let upSum = 0, downSum = 0;
      for (let i = 0; i < closes.length; i++) {
        if (i === 0) { r[i] = '-'; continue; }
        const chg = closes[i] - closes[i - 1];
        const up = chg > 0 ? chg : 0;
        const down = chg < 0 ? -chg : 0;
        if (i < n) { upSum += up; downSum += down; r[i] = '-'; continue; }
        if (i === n) { upSum += up; downSum += down; }
        else { upSum = (upSum * (n - 1) + up) / n; downSum = (downSum * (n - 1) + down) / n; }
        const rs = downSum === 0 ? 100 : upSum / downSum;
        r[i] = +(100 - 100 / (1 + rs)).toFixed(2);
      }
      return r;
    };
    const rsi6 = calcRSI(6);
    const rsi12 = calcRSI(12);
    const rsi24 = calcRSI(24);

    return { ma60, dif, dea, macdBar, k, d, j, rsi6, rsi12, rsi24 };
  }, [chartData]);

  useEffect(() => {
    if (viewMode !== 'chart' || !chartRef.current) return;
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const inst = chartInstance.current;
    const { dates, ohlc, volumes } = chartData;
    const { ma60, dif, dea, macdBar, k, d, j, rsi6, rsi12, rsi24 } = indicators;

    const hasSub = subIndicator !== 'volume';
    const legendData = subIndicator === 'volume'
      ? ['K线', 'MA5', 'MA10', 'MA20', 'MA60']
      : subIndicator === 'macd' ? ['DIF', 'DEA', 'MACD']
      : subIndicator === 'kdj' ? ['K', 'D', 'J']
      : ['RSI6', 'RSI12', 'RSI24'];

    // 当 hasSub=true 时：grid[0]主图 + grid[1]成交量 + grid[2]指标线
    // 当 hasSub=false 时：grid[0]主图(含MA) + grid[1]成交量
    // 容器高度 600px，主图 top:40px
    // hasSub:   主图48% + 成交量18% + 指标14% + 间隙
    // volume:   主图62% + 成交量20% + 间隙
    const mainGridHeight = hasSub ? '48%' : '62%';
    const volGrid = hasSub
      ? { left: 50, right: 20, top: '56%', height: '18%' }
      : { left: 50, right: 20, top: '72%', height: '20%' };

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: false,
      legend: {
        data: legendData,
        textStyle: { color: colors.textSecondary, fontSize: 11 },
        top: 4,
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(20, 20, 40, 0.92)',
        borderColor: 'rgba(102, 126, 234, 0.5)',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0]?.dataIndex ?? 0;
          const sortedDaily = [...daily].sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
          const sortedMinute = [...minute].sort((a, b) => String(a.datetime).localeCompare(String(b.datetime)));
          const d = klineType === 'daily' ? sortedDaily[idx] : sortedMinute[idx];
          if (!d) return '';
          const isDaily = klineType === 'daily';
          const o = isDaily ? (d as StockKlineDaily).open_price : (d as StockKlineMinute).open;
          const c = isDaily ? (d as StockKlineDaily).close_price : (d as StockKlineMinute).close;
          const h = isDaily ? (d as StockKlineDaily).high_price : (d as StockKlineMinute).high;
          const l = isDaily ? (d as StockKlineDaily).low_price : (d as StockKlineMinute).low;
          const v = isDaily ? (d as StockKlineDaily).volume : ((d as StockKlineMinute).volume || (d as StockKlineMinute).vol || 0);
          const color = c >= o ? '#ff4d4f' : '#52c41a';
          const date = isDaily ? (d as StockKlineDaily).trade_date : (d as StockKlineMinute).datetime;
          return `<div style="padding:8px">
            <div style="font-weight:600;margin-bottom:6px">${date}</div>
            <div style="display:flex;justify-content:space-between;gap:20px">
              <span>开盘: <span style="color:${color};font-weight:600">${o.toFixed(2)}</span></span>
              <span>收盘: <span style="color:${color};font-weight:600">${c.toFixed(2)}</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:20px;margin-top:4px">
              <span>最高: <span style="color:#ff4d4f;font-weight:600">${h.toFixed(2)}</span></span>
              <span>最低: <span style="color:#52c41a;font-weight:600">${l.toFixed(2)}</span></span>
            </div>
            <div style="margin-top:4px">成交量: <span style="font-weight:600">${v >= 1e8 ? (v/1e8).toFixed(2)+'亿' : v >= 1e4 ? (v/1e4).toFixed(0)+'万' : v}</span></div>
          </div>`;
        },
      },
      grid: [
        { left: 50, right: 20, top: 40, height: mainGridHeight },
        volGrid,
        ...(hasSub ? [{ left: 50, right: 20, top: '78%', height: '14%' }] : []),
      ],
      xAxis: [
        {
          type: 'category', data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10 },
          splitLine: { show: false },
        },
        {
          type: 'category', gridIndex: 1, data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { show: false }, splitLine: { show: false },
        },
        ...(hasSub ? [{
          type: 'category' as const, gridIndex: 2, data: dates, boundaryGap: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { show: false }, splitLine: { show: false },
        }] : []),
      ],
      yAxis: [
        {
          scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10 },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        },
        {
          gridIndex: 1, scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10,
            formatter: (v: number) => {
              if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '亿';
              if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万';
              return String(v);
            },
          },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        },
        ...(hasSub ? [{
          gridIndex: 2, scale: true,
          axisLine: { lineStyle: { color: colors.borderColor } },
          axisLabel: { color: colors.textTertiary, fontSize: 10 },
          splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } },
        }] : []),
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1], start: 0, end: 100 },
        {
          type: 'slider', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1], start: 0, end: 100,
          height: 18, bottom: 4,
          textStyle: { color: colors.textTertiary, fontSize: 10 },
        },
      ],
      series: [
        {
          name: 'K线', type: 'candlestick', data: ohlc,
          itemStyle: { color: '#ff4d4f', color0: '#52c41a', borderColor: '#ff4d4f', borderColor0: '#52c41a' },
        },
        // MA 均线（仅在 volume 模式下显示）
        ...(subIndicator === 'volume' ? [
          { name: 'MA5', type: 'line' as const, data: calcMA(5, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'MA10', type: 'line' as const, data: calcMA(10, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'MA20', type: 'line' as const, data: calcMA(20, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
          { name: 'MA60', type: 'line' as const, data: ma60, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#34D399' } },
        ] : []),
        // 副图
        ...(subIndicator === 'volume' ? [{
          name: '成交量', type: 'bar' as const, xAxisIndex: 1, yAxisIndex: 1, data: volumes,
          itemStyle: {
            color: (params: any) => {
              const i = params.dataIndex;
              const o = ohlc[i]?.[0] ?? 0;
              const c = ohlc[i]?.[1] ?? 0;
              return c >= o ? '#ff4d4f' : '#52c41a';
            },
            opacity: 0.75,
          },
        }] : []),
        ...(subIndicator === 'macd' ? [
          { name: 'DIF', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: dif, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'DEA', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: dea, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'MACD', type: 'bar' as const, xAxisIndex: 2, yAxisIndex: 2, data: macdBar.map((v) => ({
            value: v,
            itemStyle: { color: (typeof v === 'number' && v >= 0) ? '#ff4d4f' : '#52c41a', opacity: 0.8 },
          })) },
        ] : []),
        ...(subIndicator === 'kdj' ? [
          { name: 'K', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: k, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'D', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: d, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'J', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: j, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
        ] : []),
        ...(subIndicator === 'rsi' ? [
          { name: 'RSI6', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi6, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
          { name: 'RSI12', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi12, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
          { name: 'RSI24', type: 'line' as const, xAxisIndex: 1, yAxisIndex: 1, data: rsi24, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
        ] : []),
      ],
    };

    inst.setOption(option, true);
  }, [viewMode, chartData, colors, indicators, subIndicator]);

  // 卸载或切换模式时清理 echarts 实例 + 监听窗口 resize
  useEffect(() => {
    if (viewMode !== 'chart' && chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
    }
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, [viewMode]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  // 日线表格数据：按 trade_date 升序排好后，前端基于相邻收盘价派生 涨跌额/涨跌幅/振幅
  //（后端 /api/stock/get-kline 返回仅 OHLC+成交量+成交额，缺失 4 个派生字段）
  const dailyTableData = useMemo(() => {
    const sorted = [...daily].sort((a, b) =>
      String(a.trade_date).localeCompare(String(b.trade_date))
    );
    const enriched = sorted.map((r, i) => {
      const prevClose = i > 0 ? sorted[i - 1].close_price : null;
      const changeAmt = prevClose != null && r.close_price != null
        ? r.close_price - prevClose : null;
      const changePct = prevClose && r.close_price != null
        ? ((r.close_price - prevClose) / prevClose) * 100 : null;
      const amplitude = prevClose && r.high_price != null && r.low_price != null
        ? ((r.high_price - r.low_price) / prevClose) * 100 : null;
      return {
        ...r,
        change_amount: changeAmt as any,
        change_percent: changePct as any,
        amplitude: amplitude as any,
      };
    });
    // 倒序展示（最新在前）
    return enriched.reverse();
  }, [daily]);

  // 日线列（换手率字段后端未提供，显示 --）
  const dailyColumns = [
    { title: '交易日', dataIndex: 'trade_date', width: 110, render: (v: string) => <Text style={{ fontSize: '12px', color: colors.textPrimary, fontFamily: 'monospace' }}>{v}</Text> },
    { title: '开盘', dataIndex: 'open_price', align: 'right' as const, width: 90, render: (v: number) => fmtNum(v, 2) },
    { title: '最高', dataIndex: 'high_price', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text> },
    { title: '最低', dataIndex: 'low_price', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text> },
    { title: '收盘', dataIndex: 'close_price', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ fontWeight: 600 }}>{fmtNum(v, 2)}</Text> },
    { title: '涨跌额', dataIndex: 'change_amount', align: 'right' as const, width: 90, render: (v: number | null) => v == null ? '--' : <Text style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{fmtNum(v, 2)}</Text> },
    { title: '涨跌幅', dataIndex: 'change_percent', align: 'right' as const, width: 90, render: (v: number | null) => v == null ? '--' : <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{fmtNum(v, 2)}%</Text> },
    { title: '振幅', dataIndex: 'amplitude', align: 'right' as const, width: 80, render: (v: number | null) => v == null ? '--' : fmtNum(v, 2) + '%' },
    { title: '成交量(手)', dataIndex: 'volume', align: 'right' as const, width: 110, render: (v: number) => fmtThousand(v) },
    { title: '成交额', dataIndex: 'amount', align: 'right' as const, width: 110, render: (v: number) => fmtYi(v) },
  ];

  // 分钟列
  const minuteColumns = [
    { title: '时间', dataIndex: 'datetime', width: 160, render: (v: string) => <Text style={{ fontSize: '12px', color: colors.textPrimary, fontFamily: 'monospace' }}>{v}</Text> },
    { title: '开盘', dataIndex: 'open', align: 'right' as const, width: 90, render: (v: number) => fmtNum(v, 2) },
    { title: '最高', dataIndex: 'high', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text> },
    { title: '最低', dataIndex: 'low', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text> },
    { title: '收盘', dataIndex: 'close', align: 'right' as const, width: 90, render: (v: number) => <Text style={{ fontWeight: 600 }}>{fmtNum(v, 2)}</Text> },
    { title: '成交量', dataIndex: 'vol', align: 'right' as const, width: 110, render: (v: number) => fmtThousand(v) },
    { title: '成交额', dataIndex: 'amount', align: 'right' as const, width: 110, render: (v: number) => fmtYi(v) },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8, flexShrink: 0 }}>
        <Space size="small" wrap>
          <Select
            value={klineType}
            onChange={setKlineType}
            size="small"
            style={{ width: 100 }}
            options={[
              { value: 'daily', label: '日线' },
              { value: 'minute', label: '分钟线' },
            ]}
          />
          {klineType === 'daily' ? (
            <Select
                value={adjust}
                onChange={setAdjust}
                size="small"
                style={{ width: 110 }}
                options={[
                  { value: '', label: '不复权' },
                  { value: 'qfq', label: '前复权' },
                  { value: 'hfq', label: '后复权' },
                ]}
              />
          ) : (
            <Select
              value={minutePeriod}
              onChange={setMinutePeriod}
              size="small"
              style={{ width: 110 }}
              options={[
                { value: '1', label: '1分钟' },
                { value: '5', label: '5分钟' },
                { value: '15', label: '15分钟' },
                { value: '30', label: '30分钟' },
                { value: '60', label: '60分钟' },
              ]}
            />
          )}
          <RangePicker
            value={dateRange}
            onChange={(v) => v && v[0] && v[1] && setDateRange([v[0], v[1]])}
            size="small"
            allowClear={false}
          />
          <Radio.Group
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value)}
            size="small"
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="chart"><BarChartOutlined /> K线图</Radio.Button>
            <Radio.Button value="table"><TableOutlined /> 数据行</Radio.Button>
          </Radio.Group>
          {viewMode === 'chart' && (
            <Select
              value={subIndicator}
              onChange={setSubIndicator}
              size="small"
              style={{ width: 90 }}
              options={[
                { value: 'volume', label: '成交量' },
                { value: 'macd', label: 'MACD' },
                { value: 'kdj', label: 'KDJ' },
                { value: 'rsi', label: 'RSI' },
              ]}
            />
          )}
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>

      {viewMode === 'chart' ? (
        <div style={{ position: 'relative', width: '100%', height: 600 }}>
          {/* 始终渲染 chart 容器，确保 chartRef 第一时间绑定，避免数据到达时 ref 为 null */}
          <div
            ref={chartRef}
            style={{
              width: '100%',
              height: '100%',
              background: colors.bgCard,
              border: '1px solid ' + colors.borderColor,
              borderRadius: 6,
              padding: 4,
            }}
          />
          {chartData.dates.length === 0 && !loading && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: colors.bgCard,
                pointerEvents: 'none',
              }}
            >
              <Empty description={klineType === 'daily' ? '暂无日线数据' : '暂无分钟数据'} />
            </div>
          )}
        </div>
      ) : klineType === 'daily' ? (
        <div ref={containerRef} style={{ flex: 1, minHeight: 400, display: 'flex', flexDirection: 'column' }}>
          {dailyTableData.length === 0 && !loading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty description="暂无日线数据（请尝试调整日期范围或刷新）" />
            </div>
          ) : (
            <Table
              columns={dailyColumns}
              dataSource={dailyTableData}
              loading={loading}
              rowKey={(r) => r.trade_date}
              size="small"
              scroll={{ x: 1100 }}
              pagination={{ pageSize: 30, showSizeChanger: true, pageSizeOptions: ['30', '50', '100', '200'] }}
            />
          )}
        </div>
      ) : (
        <div ref={containerRef} style={{ flex: 1, minHeight: 400, display: 'flex', flexDirection: 'column' }}>
          {minute.length === 0 && !loading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty description="暂无分钟数据" />
            </div>
          ) : (
            <Table
              columns={minuteColumns}
              dataSource={minute}
              loading={loading}
              rowKey={(r) => r.datetime}
              size="small"
              scroll={{ x: 760 }}
              pagination={{ pageSize: 30, showSizeChanger: true, pageSizeOptions: ['30', '50', '100', '200'] }}
            />
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 3: 财务报表（资产负债表 / 利润表 / 现金流量表）
// ═══════════════════════════════════════════════════════════════════

const FinancePanel: React.FC<PanelProps> = ({ symbol }) => {
  const { colors } = useTheme();
  const [sheetType, setSheetType] = useState<'资产负债表' | '利润表' | '现金流量表'>('资产负债表');
  const [reports, setReports] = useState<StockBalanceSheet[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const code = detectMarket(symbol);
    const cacheKey = makeKey('stockCenter:finance', { symbol: code, sheet: sheetType });
    if (!force) {
      const cached = readDailyCache<StockBalanceSheet[]>(cacheKey);
      if (cached) {
        setReports(cached);
        return;
      }
    }
    setLoading(true);
    try {
      const result = await stockCenterApi.getFinancialReport(code, sheetType);
      // 倒序：最新报告期在前
      const sorted = [...result].sort((a, b) =>
        String(b.report_date || '').localeCompare(String(a.report_date || ''))
      );
      setReports(sorted);
      writeDailyCache(cacheKey, sorted);
      if (sorted.length === 0) message.warning(sheetType + '数据为空');
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [symbol, sheetType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // 根据报表类型选择关键字段（仅展示常用字段，避免几百列爆表）
  const keyFieldsByType: Record<string, Array<{ key: string; label: string; isLiability?: boolean }>> = {
    '资产负债表': [
      { key: 'total_assets', label: '资产总计' },
      { key: 'total_current_assets', label: '流动资产合计' },
      { key: 'total_non_current_assets', label: '非流动资产合计' },
      { key: 'monetary_funds', label: '货币资金' },
      { key: 'accounts_receivable', label: '应收账款' },
      { key: 'inventories', label: '存货' },
      { key: 'fixed_assets_net_amount', label: '固定资产净额' },
      { key: 'total_liabilities', label: '负债合计', isLiability: true },
      { key: 'total_current_liabilities', label: '流动负债合计', isLiability: true },
      { key: 'total_non_current_liabilities', label: '非流动负债合计', isLiability: true },
      { key: 'short_term_borrowings', label: '短期借款', isLiability: true },
      { key: 'long_term_borrowings', label: '长期借款', isLiability: true },
      { key: 'accounts_payable', label: '应付账款', isLiability: true },
      { key: 'total_owners_equity', label: '股东权益合计' },
      { key: 'paid_in_capital', label: '实收资本' },
      { key: 'retained_earnings', label: '未分配利润' },
    ],
    '利润表': [
      { key: 'total_operating_revenue', label: '营业总收入' },
      { key: 'operating_revenue', label: '营业收入' },
      { key: 'total_operating_cost', label: '营业总成本' },
      { key: 'operating_cost', label: '营业成本' },
      { key: 'sales_expense', label: '销售费用' },
      { key: 'admin_expense', label: '管理费用' },
      { key: 'rd_expense', label: '研发费用' },
      { key: 'financial_expense', label: '财务费用' },
      { key: 'operating_profit', label: '营业利润' },
      { key: 'total_profit', label: '利润总额' },
      { key: 'income_tax_expense', label: '所得税费用' },
      { key: 'net_profit', label: '净利润' },
      { key: 'net_profit_attributable_to_parent', label: '归母净利润' },
      { key: 'basic_eps', label: '基本每股收益' },
    ],
    '现金流量表': [
      { key: 'cash_inflow_from_operating_activities', label: '经营现金流入' },
      { key: 'cash_outflow_from_operating_activities', label: '经营现金流出' },
      { key: 'net_cash_from_operating_activities', label: '经营活动现金流量净额' },
      { key: 'cash_inflow_from_investing_activities', label: '投资现金流入' },
      { key: 'cash_outflow_from_investing_activities', label: '投资现金流出' },
      { key: 'net_cash_from_investing_activities', label: '投资活动现金流量净额' },
      { key: 'cash_inflow_from_financing_activities', label: '筹资现金流入' },
      { key: 'cash_outflow_from_financing_activities', label: '筹资现金流出' },
      { key: 'net_cash_from_financing_activities', label: '筹资活动现金流量净额' },
      { key: 'net_increase_in_cash', label: '现金及现金等价物净增加额' },
      { key: 'ending_cash_balance', label: '期末现金及等价物余额' },
    ],
  };

  const recentReports = reports.slice(0, 5);
  const keyFields = keyFieldsByType[sheetType] || [];

  const transposed = useMemo(() => {
    return keyFields.map((field) => {
      const row: Record<string, any> = { metric: field.label, _key: field.key, _isLiability: field.isLiability };
      recentReports.forEach((r) => {
        row[r.report_date] = r[field.key];
      });
      return row;
    });
  }, [keyFields, recentReports, sheetType]);

  const columns = [
    {
      title: '指标',
      dataIndex: 'metric',
      width: 180,
      fixed: 'left' as const,
      render: (v: string, row: any) => (
        <Text style={{ color: row._isLiability ? '#F59E0B' : colors.textPrimary, fontWeight: 500 }}>{v}</Text>
      ),
    },
    ...recentReports.map((r) => ({
      title: r.report_date,
      dataIndex: r.report_date,
      align: 'right' as const,
      width: 130,
      render: (v: any) => (
        <Text style={{ color: colors.textPrimary, fontFamily: 'monospace', fontSize: '12px' }}>
          {fmtYi(v)}
        </Text>
      ),
    })),
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Space size="small">
          <Text style={{ color: colors.textSecondary, fontSize: '12px' }}>报表类型</Text>
          <Select
            value={sheetType}
            onChange={(v) => setSheetType(v)}
            size="small"
            style={{ width: 130 }}
            options={[
              { value: '资产负债表', label: '资产负债表' },
              { value: '利润表', label: '利润表' },
              { value: '现金流量表', label: '现金流量表' },
            ]}
          />
          <Text style={{ color: colors.textTertiary, fontSize: '12px', marginLeft: 8 }}>
            数据源：新浪财经 · 显示近 5 期 · 单位自动换算亿/万
          </Text>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>

      {reports.length === 0 && !loading ? (
        <Empty description={'暂无' + sheetType + '数据'} />
      ) : (
        <Table
          columns={columns}
          dataSource={transposed}
          loading={loading}
          rowKey="_key"
          size="small"
          scroll={{ x: 180 + recentReports.length * 130 }}
          pagination={false}
          bordered
        />
      )}

      {reports.length > 5 && (
        <Text style={{ color: colors.textTertiary, fontSize: '11px', display: 'block', marginTop: 8 }}>
          共 {reports.length} 期报告，仅展示最近 5 期
        </Text>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Panel 4: 千股千评（用户关注指数 + 市场参与意愿）
// ═══════════════════════════════════════════════════════════════════

const CommentPanel: React.FC<PanelProps> = ({ symbol }) => {
  const { colors } = useTheme();
  const [focus, setFocus] = useState<StockCommentFocus[]>([]);
  const [desire, setDesire] = useState<StockCommentDesire[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const pure = stripMarket(symbol);
    const cacheKey = makeKey('stockCenter:comment', { symbol: pure });
    if (!force) {
      const cached = readDailyCache<{ focus: StockCommentFocus[]; desire: StockCommentDesire[] }>(
        cacheKey,
        { ttlMs: TTL.MEDIUM },
      );
      if (cached) {
        setFocus(cached.focus);
        setDesire(cached.desire);
        return;
      }
    }
    setLoading(true);
    try {
      const [f, d] = await Promise.allSettled([
        stockCenterApi.getCommentFocus(pure),
        stockCenterApi.getCommentDesire(pure),
      ]);
      const fData = f.status === 'fulfilled' ? (f.value || []) : [];
      const dData = d.status === 'fulfilled' ? (d.value || []) : [];
      setFocus(fData);
      setDesire(dData);
      writeDailyCache(cacheKey, { focus: fData, desire: dData });
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // 关注指数：取近 30 天，倒序最新在前
  const focusRecent = useMemo(() => [...focus].reverse(), [focus]);
  // 平均关注度
  const avgFocus = focus.length > 0
    ? focus.reduce((acc, r) => acc + (r['用户关注指数'] || 0), 0) / focus.length
    : 0;
  const latestFocus = focus.length > 0 ? focus[focus.length - 1] : null;
  const latestDesire = desire.length > 0 ? desire[0] : null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {/* 用户关注指数 */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<Space size={6}><CommentOutlined style={{ color: '#56A4FF' }} /><span>用户关注指数</span></Space>}
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
              <Col span={12}>
                <Statistic
                  title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>最新关注指数</Text>}
                  value={latestFocus?.['用户关注指数']}
                  precision={0}
                  styles={{ content: { color: '#56A4FF', fontSize: 22, fontWeight: 700 } }}
                />
                {latestFocus && (
                  <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                    {latestFocus['交易日']}
                  </Text>
                )}
              </Col>
              <Col span={12}>
                <Statistic
                  title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>近 {focus.length} 日均值</Text>}
                  value={avgFocus}
                  precision={1}
                  styles={{ content: { color: colors.textPrimary, fontSize: 22, fontWeight: 700 } }}
                />
              </Col>
            </Row>
            <Table
              columns={[
                { title: '交易日', dataIndex: '交易日', width: 110, render: (v: string) => <Text style={{ fontSize: '12px', color: colors.textPrimary, fontFamily: 'monospace' }}>{v}</Text> },
                {
                  title: '关注指数',
                  dataIndex: '用户关注指数',
                  align: 'right' as const,
                  sorter: (a: StockCommentFocus, b: StockCommentFocus) =>
                    (a['用户关注指数'] || 0) - (b['用户关注指数'] || 0),
                  render: (v: number) => (
                    <Text style={{ color: v >= avgFocus ? '#ff4d4f' : colors.textPrimary, fontWeight: v >= avgFocus ? 600 : 400 }}>
                      {fmtNum(v, 0)}
                    </Text>
                  ),
                },
              ]}
              dataSource={focusRecent}
              loading={loading}
              rowKey={(r) => r['交易日']}
              size="small"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              scroll={{ y: 360 }}
            />
          </Card>
        </Col>

        {/* 市场参与意愿 */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<Space size={6}><FireOutlined style={{ color: '#F59E0B' }} /><span>市场参与意愿</span></Space>}
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {latestDesire ? (
              <>
                <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
                  <Col span={12}>
                    <Statistic
                      title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>最新意愿值</Text>}
                      value={latestDesire.desire_value}
                      precision={2}
                      styles={{ content: { color: '#F59E0B', fontSize: 22, fontWeight: 700 } }}
                    />
                    <Text style={{ color: pctColor(latestDesire.desire_change), fontSize: '11px' }}>
                      {latestDesire.desire_change >= 0 ? '+' : ''}{fmtNum(latestDesire.desire_change, 2)} 较上日
                    </Text>
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={<Text style={{ color: colors.textTertiary, fontSize: '12px' }}>5 日均值</Text>}
                      value={latestDesire.avg_5_desire}
                      precision={2}
                      styles={{ content: { color: colors.textPrimary, fontSize: 22, fontWeight: 700 } }}
                    />
                    <Text style={{ color: pctColor(latestDesire.avg_5_change), fontSize: '11px' }}>
                      {latestDesire.avg_5_change >= 0 ? '+' : ''}{fmtNum(latestDesire.avg_5_change, 2)} 较上日均值
                    </Text>
                  </Col>
                </Row>
                <Table
                  columns={[
                    { title: '日期', dataIndex: 'trade_date', width: 110, render: (v: string) => <Text style={{ fontSize: '12px', color: colors.textPrimary, fontFamily: 'monospace' }}>{v}</Text> },
                    { title: '意愿值', dataIndex: 'desire_value', align: 'right' as const, render: (v: number) => <Text style={{ color: '#F59E0B', fontWeight: 600 }}>{fmtNum(v, 2)}</Text> },
                    { title: '5日均值', dataIndex: 'avg_5_desire', align: 'right' as const, render: (v: number) => fmtNum(v, 2) },
                    {
                      title: '日内变动',
                      dataIndex: 'desire_change',
                      align: 'right' as const,
                      render: (v: number) => (
                        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
                          {v >= 0 ? '+' : ''}{fmtNum(v, 2)}
                        </Text>
                      ),
                    },
                  ]}
                  dataSource={desire}
                  loading={loading}
                  rowKey={(r) => r.trade_date}
                  size="small"
                  pagination={false}
                  scroll={{ y: 360 }}
                />
              </>
            ) : (
              <Empty description="暂无参与意愿数据" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default React.memo(StockCenter);
