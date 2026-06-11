/**
 * 个股详情抽屉组件
 *
 * 从龙虎榜/其他表格点击股票后，以 Drawer 形式展示个股详情。
 * 支持在已打开的股票间切换（prev/next）。
 *
 * Tab 结构：
 *   1. 概况 — 所属概念/热度 + 股东户数概览
 *   2. K线行情 — 日K线图
 *   3. 财务报表 — 资产负债/利润/现金流三表
 *   4. 千股千评 — 关注指数 + 参与意愿
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Drawer, Tabs, Typography, Space, Button, Tag, Card, Row, Col, Statistic, Table, Empty, Spin } from 'antd';
import {
  LeftOutlined,
  RightOutlined,
  ReloadOutlined,
  TeamOutlined,
  FireOutlined,
  FundOutlined,
  CommentOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';
import { stockCenterApi } from '@/api/stock';
import { safeToFixed } from '@/utils/format';
import type {
  StockHotKeyword,
  StockKlineDaily,
  StockHolderDetail,
  StockCommentFocus,
  StockCommentDesire,
  StockBalanceSheet,
} from '../../types/stock';

const { Text } = Typography;

// ─── 工具函数 ───────────────────────────────────────────────────────

const pctColor = (v: number | null | undefined): string => {
  if (v == null || v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

const fmtYi = (v: number | null | undefined): string => {
  if (v == null || isNaN(Number(v))) return '--';
  const n = Number(v);
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万';
  return n.toFixed(2);
};

const fmtThousand = (v: number | null | undefined): string => {
  if (v == null || isNaN(Number(v))) return '--';
  return Number(v).toLocaleString('zh-CN');
};

/** 提取纯 6 位代码 */
const stripMarket = (code: string): string => {
  return code.replace(/^(sh|sz|bj|SH|SZ|BJ)/i, '');
};

/** 自动识别市场前缀 */
const toUpperMarket = (code: string): string => {
  const c = code.trim().toUpperCase();
  if (/^(SH|SZ|BJ|HK|US)/.test(c)) return c;
  if (!/^\d+$/.test(c)) return c;
  const padded = c.padStart(6, '0');
  const first = padded.charAt(0);
  if (first === '6' || padded.startsWith('688') || padded.startsWith('900')) return 'SH' + padded;
  if (first === '0' || first === '3' || padded.startsWith('200')) return 'SZ' + padded;
  if (first === '8' || first === '4') return 'BJ' + padded;
  return padded;
};

// ─── Props ──────────────────────────────────────────────────────────

export interface StockDetailItem {
  symbol: string;   // 纯 6 位代码
  name: string;     // 股票名称
}

interface StockDetailDrawerProps {
  visible: boolean;
  stockList: StockDetailItem[];    // 所有已打开的股票列表
  currentIndex: number;            // 当前查看的股票索引
  onClose: () => void;
  onNavigate: (index: number) => void;
}

// ─── 主组件 ─────────────────────────────────────────────────────────

const StockDetailDrawer: React.FC<StockDetailDrawerProps> = ({
  visible,
  stockList,
  currentIndex,
  onClose,
  onNavigate,
}) => {
  const { colors } = useTheme();
  const current = stockList[currentIndex];
  const symbol = current?.symbol || '';
  const name = current?.name || '';
  const [activeTab, setActiveTab] = useState<string>('overview');

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Button
            type="text"
            size="small"
            icon={<LeftOutlined />}
            disabled={currentIndex <= 0}
            onClick={() => onNavigate(currentIndex - 1)}
          />
          <Space size={4}>
            <Text strong style={{ fontSize: 15 }}>{name}</Text>
            <Text style={{ color: colors.textTertiary, fontFamily: 'monospace', fontSize: 13 }}>
              {toUpperMarket(symbol)}
            </Text>
          </Space>
          <Button
            type="text"
            size="small"
            icon={<RightOutlined />}
            disabled={currentIndex >= stockList.length - 1}
            onClick={() => onNavigate(currentIndex + 1)}
          />
          <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
            {currentIndex + 1}/{stockList.length}
          </Text>
        </div>
      }
      placement="right"
      width={760}
      open={visible}
      onClose={onClose}
      destroyOnClose
      styles={{ body: { padding: '12px 16px' } }}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="small"
        type="card"
        destroyInactiveTabPane
        items={[
          {
            key: 'overview',
            label: <span><FireOutlined /> 概况</span>,
            children: <OverviewTab symbol={symbol} />,
          },
          {
            key: 'kline',
            label: <span><LineChartOutlined /> K线行情</span>,
            children: <KlineTab symbol={symbol} />,
          },
          {
            key: 'finance',
            label: <span><FundOutlined /> 财务报表</span>,
            children: <FinanceTab symbol={symbol} />,
          },
          {
            key: 'comment',
            label: <span><CommentOutlined /> 千股千评</span>,
            children: <CommentTab symbol={symbol} />,
          },
        ]}
      />
    </Drawer>
  );
};

export default React.memo(StockDetailDrawer);

// ═══════════════════════════════════════════════════════════════════
// Tab 1: 概况
// ═══════════════════════════════════════════════════════════════════

const OverviewTab: React.FC<{ symbol: string }> = ({ symbol }) => {
  const { colors } = useTheme();
  const [keywords, setKeywords] = useState<StockHotKeyword[]>([]);
  const [holders, setHolders] = useState<StockHolderDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [stockName, setStockName] = useState('');

  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const upper = toUpperMarket(symbol);
      const [kw, hd] = await Promise.allSettled([
        stockCenterApi.getHotKeywords(upper),
        stockCenterApi.getHolderDetail(stripMarket(symbol)),
      ]);
      const kwData = kw.status === 'fulfilled' ? (kw.value || []) : [];
      const hdData = hd.status === 'fulfilled' ? (hd.value || []) : [];
      setKeywords(kwData);
      setHolders(hdData);
      if (hdData.length > 0) setStockName(hdData[0].name || '');
    } catch (e: any) {
      // silent
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const latest = holders.length > 0 ? holders[holders.length - 1] : null;
  const recent5 = useMemo(() => holders.slice(-5).reverse(), [holders]);

  return (
    <Spin spinning={loading}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Text style={{ color: colors.textPrimary, fontWeight: 600 }}>
          {stockName || toUpperMarket(symbol)}
        </Text>
        <Button size="small" icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
      </div>

      <Row gutter={[12, 12]}>
        <Col xs={24}>
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
                      title="最新股东户数"
                      value={latest.holder_num_current}
                      formatter={(v) => fmtThousand(v as number)}
                      valueStyle={{ color: colors.textPrimary, fontSize: 20, fontWeight: 700 }}
                    />
                    <div><Text style={{ color: colors.textTertiary, fontSize: 11 }}>截至 {latest.end_date}</Text></div>
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="户数变化"
                      value={latest.holder_num_change}
                      formatter={(v) => (Number(v) >= 0 ? '+' : '') + fmtThousand(v as number)}
                      valueStyle={{ color: pctColor(latest.holder_num_change), fontSize: 20, fontWeight: 700 }}
                    />
                    <div>
                      <Text style={{ color: pctColor(latest.holder_num_change_pct), fontSize: 11 }}>
                        {latest.holder_num_change_pct >= 0 ? '+' : ''}{safeToFixed(latest.holder_num_change_pct, 2, '0')}%
                      </Text>
                    </div>
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="户均持股市值"
                      value={latest.avg_market_cap_per_holder}
                      formatter={(v) => fmtYi(v as number)}
                      valueStyle={{ color: colors.textPrimary, fontSize: 20, fontWeight: 700 }}
                    />
                    <div><Text style={{ color: colors.textTertiary, fontSize: 11 }}>户均持股 {fmtThousand(Math.round(latest.avg_share_per_holder))} 股</Text></div>
                  </Col>
                </Row>
                <div style={{ marginTop: 12 }}>
                  <Text style={{ color: colors.textSecondary, fontSize: 12, fontWeight: 600 }}>近 5 期变化</Text>
                  <Table
                    columns={[
                      { title: '截止日', dataIndex: 'end_date', width: 100, render: (v: string) => <Text style={{ fontSize: 12 }}>{v}</Text> },
                      { title: '股东户数', dataIndex: 'holder_num_current', align: 'right' as const, render: (v: number) => fmtThousand(v) },
                      { title: '变化', dataIndex: 'holder_num_change', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{v >= 0 ? '+' : ''}{fmtThousand(v)}</Text> },
                      { title: '变化幅度', dataIndex: 'holder_num_change_pct', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{safeToFixed(v, 2, '0')}%</Text> },
                      { title: '区间涨跌', dataIndex: 'interval_pct_change', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{safeToFixed(v, 2, '0')}%</Text> },
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
        <Col xs={24}>
          <Card
            size="small"
            title={<Space size={6}><FireOutlined style={{ color: '#F59E0B' }} /><span>所属概念 / 热度</span></Space>}
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {keywords.length > 0 ? (
              <>
                <Text style={{ color: colors.textTertiary, fontSize: 11, display: 'block', marginBottom: 8 }}>
                  数据时间：{keywords[0]?.stat_date}
                </Text>
                <Space size={[6, 6]} wrap>
                  {keywords.map((k) => (
                    <Tag key={k.concept_code} color="orange" style={{ padding: '4px 10px', fontSize: 12 }}>
                      {k.concept_name}
                      <Text style={{ color: '#fff', marginLeft: 6, fontSize: 10, opacity: 0.9 }}>
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
    </Spin>
  );
};

// ═══════════════════════════════════════════════════════════════════
// Tab 2: K 线行情（简化版）
// ═══════════════════════════════════════════════════════════════════

const KlineTab: React.FC<{ symbol: string }> = ({ symbol }) => {
  const { colors } = useTheme();
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [daily, setDaily] = useState<StockKlineDaily[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const pure = stripMarket(symbol);
      const now = new Date();
      const end = now.toISOString().slice(0, 10).replace(/-/g, '');
      const start = new Date(now.getTime() - 365 * 24 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, '');
      const result = await stockCenterApi.getDailyKline(pure, 'daily', start, end, 'qfq');
      setDaily(result || []);
    } catch (e: any) {
      // silent
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const chartData = useMemo(() => {
    if (!daily.length) return null;
    const sorted = [...daily].sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
    return {
      dates: sorted.map((r) => r.trade_date),
      ohlc: sorted.map((r) => [r.open_price, r.close_price, r.low_price, r.high_price]),
      volumes: sorted.map((r) => r.volume),
      ma5: (() => {
        const arr: (number | string)[] = [];
        for (let i = 0; i < sorted.length; i++) {
          if (i < 4) { arr.push('-'); continue; }
          let sum = 0;
          for (let j = 0; j < 5; j++) sum += sorted[i - j].close_price;
          arr.push(+(sum / 5).toFixed(2));
        }
        return arr;
      })(),
    };
  }, [daily]);

  useEffect(() => {
    if (!chartData || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.dispose();
    const inst = echarts.init(chartRef.current);
    chartInstance.current = inst;

    inst.setOption({
      animation: false,
      backgroundColor: 'transparent',
      grid: [{ left: 50, right: 16, top: 40, bottom: 85 }, { left: 50, right: 16, top: 320, bottom: 20 }],
      xAxis: [
        { type: 'category', data: chartData.dates, axisLabel: { fontSize: 10, color: colors.textTertiary }, gridIndex: 0, axisLine: { lineStyle: { color: colors.borderColor } } },
        { type: 'category', data: chartData.dates, axisLabel: { show: false }, gridIndex: 1, axisLine: { lineStyle: { color: colors.borderColor } } },
      ],
      yAxis: [
        { scale: true, gridIndex: 0, axisLabel: { fontSize: 10, color: colors.textTertiary }, splitLine: { lineStyle: { color: colors.borderColor, type: 'dashed' } } },
        { scale: true, gridIndex: 1, axisLabel: { fontSize: 10, color: colors.textTertiary }, splitLine: { show: false } },
      ],
      series: [
        {
          type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
          data: chartData.ohlc,
          itemStyle: { color: '#ff4d4f', color0: '#52c41a', borderColor: '#ff4d4f', borderColor0: '#52c41a' },
        },
        {
          type: 'line', xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none',
          data: chartData.ma5,
          lineStyle: { width: 1, color: '#f0ad4e' },
        },
        {
          type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
          data: chartData.volumes.map((v, i) => ({
            value: v,
            itemStyle: { color: chartData.ohlc[i][0] <= chartData.ohlc[i][1] ? '#ff4d4f' : '#52c41a' },
          })),
        },
      ],
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    });

    return () => { if (chartInstance.current) chartInstance.current.dispose(); };
  }, [chartData, colors]);

  return (
    <Spin spinning={loading}>
      <div ref={chartRef} style={{ width: '100%', height: 400 }} />
      {!chartData && !loading && <Empty description="暂无K线数据" />}
    </Spin>
  );
};

// ═══════════════════════════════════════════════════════════════════
// Tab 3: 财务报表（简化版）
// ═══════════════════════════════════════════════════════════════════

const FinanceTab: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [data, setData] = useState<StockBalanceSheet[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const pure = stripMarket(symbol);
      const result = await stockCenterApi.getFinancialReport(pure);
      setData(result || []);
    } catch (e: any) {
      // silent
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  /** 近 2 年内数据，按报告期正序排列 */
  const recent = useMemo(() => {
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
    const cutoff = twoYearsAgo.toISOString().slice(0, 7); // "YYYY-MM"
    return data
      .filter((r) => r.report_date && r.report_date >= cutoff)
      .sort((a, b) => String(a.report_date).localeCompare(String(b.report_date)));
  }, [data]);

  const columns = useMemo(() => [
    { title: '报告期', dataIndex: 'report_date', width: 100, fixed: 'left' as const, render: (v: string) => <Text style={{ fontSize: 12 }}>{v}</Text> },
    { title: '总资产', dataIndex: 'total_assets', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '流动资产', dataIndex: 'total_current_assets', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '非流动资产', dataIndex: 'total_non_current_assets', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '货币资金', dataIndex: 'monetary_funds', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '应收账款', dataIndex: 'accounts_receivable', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '存货', dataIndex: 'inventories', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '固定资产', dataIndex: 'fixed_assets_net_amount', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '总负债', dataIndex: 'total_liabilities', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '流动负债', dataIndex: 'total_current_liabilities', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '非流动负债', dataIndex: 'total_non_current_liabilities', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '短期借款', dataIndex: 'short_term_borrowings', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '长期借款', dataIndex: 'long_term_borrowings', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '应付账款', dataIndex: 'accounts_payable', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '净资产', dataIndex: 'total_owners_equity', width: 110, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '实收资本', dataIndex: 'paid_in_capital', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
    { title: '未分配利润', dataIndex: 'retained_earnings', width: 100, align: 'right' as const, render: (v: number | null) => v != null ? fmtYi(v) : '--' },
  ], []);

  return (
    <Spin spinning={loading}>
      {recent.length > 0 ? (
        <Table
          columns={columns}
          dataSource={recent}
          rowKey="report_date"
          size="small"
          pagination={false}
          scroll={{ x: 1800 }}
        />
      ) : (
        !loading && <Empty description="暂无财务报表数据" />
      )}
    </Spin>
  );
};

// ═══════════════════════════════════════════════════════════════════
// Tab 4: 千股千评
// ═══════════════════════════════════════════════════════════════════

const CommentTab: React.FC<{ symbol: string }> = ({ symbol }) => {
  const { colors } = useTheme();
  const [focus, setFocus] = useState<StockCommentFocus[]>([]);
  const [desire, setDesire] = useState<StockCommentDesire[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const pure = stripMarket(symbol);
      const [f, d] = await Promise.allSettled([
        stockCenterApi.getCommentFocus(pure),
        stockCenterApi.getCommentDesire(pure),
      ]);
      setFocus(f.status === 'fulfilled' ? (f.value || []) : []);
      setDesire(d.status === 'fulfilled' ? (d.value || []) : []);
    } catch (e: any) {
      // silent
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <Spin spinning={loading}>
      <Row gutter={[12, 12]}>
        <Col xs={24}>
          <Card
            size="small"
            title="用户关注指数"
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {focus.length > 0 ? (
              <Table
                columns={[
                  { title: '交易日', dataIndex: '交易日', width: 100 },
                  { title: '关注指数', dataIndex: '用户关注指数', align: 'right' as const },
                ]}
                dataSource={focus.slice(-10).reverse()}
                rowKey="交易日"
                size="small"
                pagination={false}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
        <Col xs={24}>
          <Card
            size="small"
            title="市场参与意愿"
            style={{ background: colors.bgCard, border: '1px solid ' + colors.borderColor }}
          >
            {desire.length > 0 ? (
              <Table
                columns={[
                  { title: '交易日', dataIndex: 'trade_date', width: 100 },
                  { title: '意愿值', dataIndex: 'desire_value', align: 'right' as const, render: (v: number) => safeToFixed(v, 2) },
                  { title: '5日均值', dataIndex: 'avg_5_desire', align: 'right' as const, render: (v: number) => safeToFixed(v, 2) },
                  { title: '变化', dataIndex: 'desire_change', align: 'right' as const, render: (v: number) => <Text style={{ color: pctColor(v) }}>{safeToFixed(v, 2)}</Text> },
                ]}
                dataSource={desire.slice(-10).reverse()}
                rowKey={(r) => r.trade_date + r.symbol}
                size="small"
                pagination={false}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};