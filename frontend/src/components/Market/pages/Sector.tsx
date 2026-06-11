/**
 * 行业 / 概念板块 页面 - 市场概览子页面
 *
 * 后端实测可用接口（2026-06-01 修复后）：
 *   ✅ /api/stock/get-stock-board                      行业一览（90条 + 领涨股）
 *   ✅ /api/stock/get_all_stock_board_industry         行业 name+code（用于代码联想）
 *   ✅ /api/stock/get-stock-board-concept-info         概念简介（按 symbol 单条）
 *   ✅ /api/stock/get-stock-board-change-em            板块异动汇总
 *   ✅ /api/stock/get_stock_changes_em                 盘口异动（按异动类型筛个股）
 *   ✅ /api/stock/get-stock-fund-concept               同花顺概念资金流（即时/3/5/10/20日）
 *   ✅ /api/stock/get-stock-board-concept-index-ths    概念板块指数K线
 *   ✅ /api/stock/get-stock-board-industry-index-ths   行业板块指数K线
 *   ✅ /api/stock/get-sector-fund-flow                 板块资金流（行业/概念/地域）
 *   ✅ /api/stock/get-sector-fund-summary              板块内个股资金流
 *   ✅ /api/stock/get-sector-fund-flow-summary         主力净流入排名
 *
 * 后端仍异常（数据源问题，前端无法解决）：
 *   ❌ /api/stock/get-stock-board-industry-cons        行业成份股 → 需 BK 代码
 *
 * Tab 布局：
 *   1. 行业一览       — 表格 + 涨跌幅 Top10
 *   2. 板块K线        — 行业/概念 切换 + candlestick + 成交量
 *   3. 板块资金流     — 行业/概念/地域资金流排行
 *   4. 概念资金流     — 即时/3/5/10/20日 排行 + 龙头股
 *   5. 个股资金流     — 查板块内个股资金流
 *   6. 主力净流入     — 按市场范围排名
 *   7. 板块异动       — 今日异动汇总
 *   8. 盘口异动       — 按异动类型筛个股
 *   9. 概念简介       — 输入概念名查询简介
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
  Alert,
  Empty,
  message,
  Card,
  Row,
  Col,
  Descriptions,
  DatePicker,
  Radio,
} from 'antd';
import {
  AppstoreOutlined,
  FundOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';
import * as echarts from 'echarts';
import { useTheme } from '@/themes';
import { useTableScrollY } from '@/hooks/useTableScrollY';
import { sectorApi } from '@/api/stock';
import { safeNum, safeToFixed } from '@/utils/format';
import { readDailyCache, writeDailyCache, makeKey, TTL } from '@/utils/dailyCache';
import type {
  IndustryBoardSummary,
  BoardChangeItem,
  StockChangeItem,
  ConceptBoardInfo,
  FundFlowConceptImmediate,
  FundFlowPeriod,
  BoardIndexKline,
  SectorStockFundFlowItem,
} from '../../../types/stock';

const { RangePicker } = DatePicker;

const { Text, Title } = Typography;

// ─── 工具函数 ───────────────────────────────────────────────────────
const pctColor = (v: number | string | null | undefined): string => {
  if (v == null) return '#999';
  const n = safeNum(v, 0);
  if (n === 0) return '#999';
  return n > 0 ? '#ff4d4f' : '#52c41a';
};

const fmtNum = (v: number | string | null | undefined, digits = 2): string => {
  return safeToFixed(v, digits);
};

const fmtYi = (v: number | string | null | undefined): string => {
  if (v == null) return '--';
  const n = safeNum(v, NaN);
  if (isNaN(n)) return '--';
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万';
  return n.toFixed(2);
};

const parsePct = (v: string | number | null | undefined): number => {
  if (v == null) return 0;
  if (typeof v === 'number') return v;
  const n = parseFloat(String(v).replace('%', ''));
  return isNaN(n) ? 0 : n;
};

// 异动类型预设（来自 akshare stock_changes_em 枚举）
const CHANGE_TYPES = [
  '火箭发射', '快速反弹', '大笔买入', '封涨停板', '打开跌停板',
  '高台跳水', '加速下跌', '大笔卖出', '封跌停板', '打开涨停板',
  '60日新高', '60日新低', '向上缺口', '向下缺口',
  '60日大幅上涨', '60日大幅下跌',
  '竞价上涨', '竞价下跌', '高开5日线', '低开5日线',
  '有大买盘', '有大卖盘',
];

// 同花顺概念资金流周期
const PERIODS: FundFlowPeriod[] = ['即时', '3日排行', '5日排行', '10日排行', '20日排行'];

// 表格分页统一配置：使用 defaultPageSize，避免受控 pageSize 未更新导致“切换每页条数无效”
const TABLE_PAGE_SIZE_OPTIONS = ['10', '20', '30', '40', '50', '100', '200'];
const createTablePagination = (defaultPageSize = 30, pageSizeOptions: string[] = TABLE_PAGE_SIZE_OPTIONS) => ({
  defaultPageSize,
  showSizeChanger: true,
  pageSizeOptions,
  showTotal: (total: number) => `共 ${total} 条`,
});

// ═══════════════════════════════════════════════════════════════
// 1. 行业一览 Panel
// ═══════════════════════════════════════════════════════════════
const IndustryPanel: React.FC = () => {
  const { colors } = useTheme();
  const { containerRef, scrollY } = useTableScrollY(52);
  const [data, setData] = useState<IndustryBoardSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const CK = 'sector:industrySummary';
    if (!force) {
      const c = readDailyCache<IndustryBoardSummary[]>(CK, { ttlMs: TTL.MEDIUM });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getIndustrySummary();
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('行业一览加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Top10 涨跌幅榜
  const top10 = useMemo(() => {
    return [...data]
      .sort((a, b) => safeNum(b.change_percent) - safeNum(a.change_percent))
      .slice(0, 10);
  }, [data]);

  const bottom10 = useMemo(() => {
    return [...data]
      .sort((a, b) => safeNum(a.change_percent) - safeNum(b.change_percent))
      .slice(0, 10);
  }, [data]);

  const columns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '板块名称', dataIndex: 'board_name', width: 110, fixed: 'left' as const,
      render: (v: string) => <Text strong style={{ color: colors.textPrimary }}>{v}</Text>,
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 90, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.change_percent) - safeNum(b.change_percent),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '净流入(亿)', dataIndex: 'net_inflow', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.net_inflow) - safeNum(b.net_inflow),
      render: (v: number) => (
        <Text style={{ color: pctColor(v) }}>{safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}</Text>
      ),
    },
    {
      title: '总成交量(万手)', dataIndex: 'total_volume', width: 120, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '总成交额(亿)', dataIndex: 'total_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.total_amount) - safeNum(b.total_amount),
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '上涨/下跌', width: 100, align: 'right' as const,
      render: (_: any, r: IndustryBoardSummary) => (
        <Text>
          <Text style={{ color: '#ff4d4f' }}>{r.rise_count}</Text>
          {' / '}
          <Text style={{ color: '#52c41a' }}>{r.fall_count}</Text>
        </Text>
      ),
    },
    {
      title: '均价', dataIndex: 'avg_price', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '领涨股', dataIndex: 'leading_stock_name', width: 100,
      render: (v: string) => <Tag color="red">{v}</Tag>,
    },
    {
      title: '领涨价', dataIndex: 'leading_stock_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '领涨涨跌幅', dataIndex: 'leading_stock_change', width: 100, align: 'right' as const,
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, flexShrink: 0 }}>
        <Space>
          <Tag color="blue">行业板块数：{data.length}</Tag>
          <Tag color="red">上涨 {data.filter(x => safeNum(x.change_percent) > 0).length}</Tag>
          <Tag color="green">下跌 {data.filter(x => safeNum(x.change_percent) < 0).length}</Tag>
          {data[0]?.stat_date && <Tag>统计日 {data[0].stat_date}</Tag>}
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>

      <Row gutter={12} style={{ marginBottom: 12, flexShrink: 0 }}>
        <Col span={12}>
          <Card size="small" title={<Text strong style={{ color: '#ff4d4f' }}>📈 涨幅 Top 10</Text>} bodyStyle={{ padding: 8 }}>
            {top10.map((r) => (
              <div key={r.board_name} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 4px', fontSize: 12 }}>
                <span style={{ color: colors.textSecondary }}>{r.board_name}</span>
                <span style={{ color: '#ff4d4f', fontWeight: 600 }}>+{fmtNum(r.change_percent, 2)}%</span>
              </div>
            ))}
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title={<Text strong style={{ color: '#52c41a' }}>📉 跌幅 Top 10</Text>} bodyStyle={{ padding: 8 }}>
            {bottom10.map((r) => (
              <div key={r.board_name} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 4px', fontSize: 12 }}>
                <span style={{ color: colors.textSecondary }}>{r.board_name}</span>
                <span style={{ color: '#52c41a', fontWeight: 600 }}>{fmtNum(r.change_percent, 2)}%</span>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      <div ref={containerRef} style={{ flex: 1, minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="board_name"
          size="small"
          scroll={{ x: 1100, y: scrollY }}
          pagination={createTablePagination(30, ['20', '30', '50', '100'])}
        />
      </div>
    </div>
  );
};
// ═══════════════════════════════════════════════════════════════
// 2. 概念资金流 Panel（同花顺）
// ═══════════════════════════════════════════════════════════════
const ConceptFundFlowPanel: React.FC = () => {
  const [period, setPeriod] = useState<FundFlowPeriod>('即时');
  const [limit, setLimit] = useState<number>(50);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('sector:conceptFundFlow', { period, limit });
    // 即时模式：盘中变化频繁 → 短 TTL；N日排行：当天稳定
    const ttlMs = period === '即时' ? TTL.SHORT : undefined;
    if (!force) {
      const c = readDailyCache<any[]>(CK, { ttlMs });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getConceptFundFlow(period, limit);
      setData((list as any[]) || []);
      writeDailyCache(CK, (list as any[]) || []);
    } catch (e: any) {
      message.error('概念资金流加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [period, limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // 即时模式和N日排行模式字段不同：即时有龙头股，N日排行有 phase_change
  const isImmediate = period === '即时';

  const immediateColumns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '概念', dataIndex: 'industry', width: 130, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '指数', dataIndex: 'index_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_ratio', width: 90, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.change_ratio) - safeNum(b.change_ratio),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '流入(亿)', dataIndex: 'inflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '流出(亿)', dataIndex: 'outflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '净流入(亿)', dataIndex: 'net_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.net_amount) - safeNum(b.net_amount),
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}
        </Text>
      ),
    },
    { title: '公司数', dataIndex: 'company_count', width: 80, align: 'right' as const },
    {
      title: '龙头股', dataIndex: 'leading_stock_name', width: 100,
      render: (v: string) => v ? <Tag color="red">{v}</Tag> : '--',
    },
    {
      title: '龙头涨幅', dataIndex: 'leading_stock_change', width: 100, align: 'right' as const,
      render: (v: number) => v == null ? '--' : (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '龙头现价', dataIndex: 'current_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
  ];

  const historyColumns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '概念', dataIndex: 'industry', width: 130, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    { title: '公司数', dataIndex: 'company_count', width: 80, align: 'right' as const },
    {
      title: '指数', dataIndex: 'index_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '阶段涨跌幅', dataIndex: 'phase_change', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => parsePct(a.phase_change) - parsePct(b.phase_change),
      defaultSortOrder: 'descend' as const,
      render: (v: string) => {
        const n = parsePct(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 600 }}>{v || '--'}</Text>
        );
      },
    },
    {
      title: '流入(亿)', dataIndex: 'inflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '流出(亿)', dataIndex: 'outflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '净流入(亿)', dataIndex: 'net_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.net_amount) - safeNum(b.net_amount),
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}
        </Text>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Text>周期：</Text>
          <Select
            value={period}
            onChange={(v) => setPeriod(v)}
            size="small"
            style={{ width: 110 }}
            options={PERIODS.map(p => ({ label: p, value: p }))}
          />
          <Text>数量：</Text>
          <Select
            value={limit}
            onChange={(v) => setLimit(v)}
            size="small"
            style={{ width: 90 }}
            options={[10, 20, 30, 50, 100].map(n => ({ label: `Top ${n}`, value: n }))}
          />
          {data[0]?.stat_date && <Tag>{data[0].stat_date}</Tag>}
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Table
        columns={(isImmediate ? immediateColumns : historyColumns) as any}
        dataSource={data}
        loading={loading}
        rowKey={(r: any, i?: number) => `${r.industry}_${i}`}
        size="small"
        scroll={{ x: 1000, y: 660 }}
        pagination={{
          pageSize: limit,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条，当前显示 Top ${limit}`,
        }}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 3. 板块异动汇总 Panel
// ═══════════════════════════════════════════════════════════════
const BoardChangePanel: React.FC = () => {
  const { colors } = useTheme();
  const [data, setData] = useState<BoardChangeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');

  const fetchData = useCallback(async (force = false) => {
    const CK = 'sector:boardChange';
    if (!force) {
      const c = readDailyCache<BoardChangeItem[]>(CK, { ttlMs: TTL.SHORT });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getBoardChange();
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('板块异动加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = useMemo(() => {
    if (!keyword.trim()) return data;
    const k = keyword.trim();
    return data.filter((r) =>
      (r.board_name || '').includes(k) ||
      (r.most_frequent_stock_name || '').includes(k)
    );
  }, [data, keyword]);

  const columns = [
    {
      title: '板块名称', dataIndex: 'board_name', width: 130, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.change_percent) - safeNum(b.change_percent),
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '主力净流入', dataIndex: 'main_net_inflow', width: 130, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.main_net_inflow) - safeNum(b.main_net_inflow),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>{fmtYi(v)}</Text>
      ),
    },
    {
      title: '异动次数', dataIndex: 'total_change_count', width: 100, align: 'right' as const,
      sorter: (a: any, b: any) => (a.total_change_count || 0) - (b.total_change_count || 0),
    },
    {
      title: '最频股票', dataIndex: 'most_frequent_stock_name', width: 110,
      render: (v: string, r: BoardChangeItem) => v ? (
        <span>
          <Tag color="purple">{v}</Tag>
          <Text style={{ fontSize: 11, color: colors.textTertiary }}>{r.most_frequent_stock_code}</Text>
        </span>
      ) : '--',
    },
    {
      title: '最频方向', dataIndex: 'most_frequent_trade_direction', width: 110,
      render: (v: string) => v ? <Tag>{v}</Tag> : '--',
    },
    {
      title: '日期', dataIndex: 'change_date', width: 110,
      render: (v: string) => <Text style={{ fontSize: 12, color: colors.textTertiary }}>{v}</Text>,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Input
            placeholder="搜索板块/个股名"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            size="small"
            style={{ width: 200 }}
            prefix={<SearchOutlined />}
            allowClear
          />
          <Tag color="blue">共 {data.length} 条</Tag>
          {keyword && <Tag color="orange">匹配 {filtered.length} 条</Tag>}
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Table
        columns={columns as any}
        dataSource={filtered}
        loading={loading}
        rowKey={(r) => `${r.board_name}_${r.change_date}`}
        size="small"
        scroll={{ x: 900, y: 660 }}
        pagination={createTablePagination(30, ['20', '30', '50', '100'])}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 4. 盘口异动 Panel（按异动类型筛个股）
// ═══════════════════════════════════════════════════════════════
const StockChangesPanel: React.FC = () => {
  const [changeType, setChangeType] = useState<string>('火箭发射');
  const [data, setData] = useState<StockChangeItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('sector:stockChanges', { type: changeType });
    if (!force) {
      const c = readDailyCache<StockChangeItem[]>(CK, { ttlMs: TTL.SHORT });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getStockChanges(changeType);
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('盘口异动加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [changeType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    {
      title: '时间', dataIndex: 'occur_time', width: 90, fixed: 'left' as const,
      render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '代码', dataIndex: 'symbol', width: 90,
      render: (v: string) => <Text style={{ fontFamily: 'monospace' }}>{v}</Text>,
    },
    {
      title: '股票', dataIndex: 'name', width: 130,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '现价', dataIndex: 'price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.change_percent) - safeNum(b.change_percent),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => {
        // 后端返回的是小数（如0.046681 = 4.67%）
        const pct = safeNum(v) * 100;
        return (
          <Text style={{ color: pctColor(pct), fontWeight: 600 }}>
            {pct >= 0 ? '+' : ''}{fmtNum(pct, 2)}%
          </Text>
        );
      },
    },
    {
      title: '异动类型', dataIndex: 'change_type', width: 110,
      render: (v: string) => <Tag color="orange">{v}</Tag>,
    },
    {
      title: '强度', dataIndex: 'strength_level', width: 80, align: 'right' as const,
      render: (v: number) => fmtNum(v, 4),
    },
    {
      title: '成交量', dataIndex: 'volume', width: 100, align: 'right' as const,
      render: (v: number | null) => v == null ? '--' : fmtYi(v),
    },
    {
      title: '成交额', dataIndex: 'amount', width: 100, align: 'right' as const,
      render: (v: number | null) => v == null ? '--' : fmtYi(v),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space wrap>
          <Text>异动类型：</Text>
          <Select
            value={changeType}
            onChange={(v) => setChangeType(v)}
            size="small"
            style={{ width: 160 }}
            options={CHANGE_TYPES.map(t => ({ label: t, value: t }))}
            showSearch
          />
          <Tag color="blue">共 {data.length} 条</Tag>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="说明：后端返回的 change_percent 为小数（如 0.0466 = 4.66%），前端已自动 ×100。volume/amount 部分异动类型不返回（显示 --）。"
      />
      <Table
        columns={columns as any}
        dataSource={data}
        loading={loading}
        rowKey={(r, i) => `${r.symbol}_${r.occur_time}_${i}`}
        size="small"
        scroll={{ x: 1000, y: 640 }}
        pagination={createTablePagination(30, ['20', '30', '50', '100', '200'])}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 5. 概念简介 Panel
// ═══════════════════════════════════════════════════════════════
const ConceptInfoPanel: React.FC = () => {
  const { colors } = useTheme();
  const [symbol, setSymbol] = useState('');
  const [inputVal, setInputVal] = useState('');
  const [data, setData] = useState<ConceptBoardInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDefault, setLoadingDefault] = useState(true);
  const initRef = useRef(false);

  const fetchData = useCallback(async (force = false) => {
    if (!symbol.trim()) return;
    const CK = makeKey('sector:conceptInfo', { symbol });
    if (!force) {
      const c = readDailyCache<ConceptBoardInfo[]>(CK);
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getConceptInfo(symbol);
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('概念简介加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { if (symbol) fetchData(); }, [fetchData]);

  // ── 首次挂载：从概念资金流数据中提取净流入排名第一的概念作为默认值 ──
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    (async () => {
      let conceptName = '光刻机'; // 兜底
      try {
        // 先尝试读缓存（与 ConceptFundFlowPanel 共享缓存）
        const cacheKey = makeKey('sector:conceptFundFlow', { period: '即时', limit: 50 });
        let fundList = readDailyCache<any[]>(cacheKey);
        // 缓存未命中则实时请求
        if (!fundList || fundList.length === 0) {
          fundList = await sectorApi.getConceptFundFlow('即时', 50);
        }
        if (fundList && fundList.length > 0) {
          // 按净流入降序取第一
          fundList.sort((a: any, b: any) => (b.net_amount ?? 0) - (a.net_amount ?? 0));
          conceptName = fundList[0].industry || conceptName;
        }
      } catch {
        // 请求失败则使用兜底值
      }
      setSymbol(conceptName);
      setInputVal(conceptName);
      setLoadingDefault(false);
    })();
  }, []);

  const info = data[0] || {} as ConceptBoardInfo;

  // 从 board_change_percent 解析数值用于颜色
  const parsePct = (v: string | undefined): number => {
    if (!v) return 0;
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  };

  const pctColor = (v: number): string => {
    if (v === 0) return '#999';
    return v > 0 ? '#ff4d4f' : '#52c41a';
  };

  return (
    <div>
      <div style={{ display: 'flex', marginBottom: 12 }}>
        <Space>
          <Text>概念名称：</Text>
          <Input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onPressEnter={() => setSymbol(inputVal.trim())}
            size="small"
            style={{ width: 220 }}
            placeholder="如：人工智能、白酒、光刻机"
          />
          <Button
            type="primary"
            size="small"
            icon={<SearchOutlined />}
            onClick={() => setSymbol(inputVal.trim())}
            loading={loading}
          >
            查询
          </Button>
          {!loading && data.length > 0 && (
            <Tag color="blue">数据源：同花顺</Tag>
          )}
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>

      {data.length === 0 && !loading ? (
        loadingDefault
          ? <div style={{ textAlign: 'center', padding: 40, color: colors.textTertiary }}>正在加载默认概念...</div>
          : <Empty description="暂无数据，请确认概念名称是否正确（如：人工智能、白酒、光刻机）" />
      ) : (
        <Card size="small" title={<Text strong style={{ fontSize: 16 }}>{symbol}</Text>}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="开盘价">
              <Text style={{ fontFamily: 'monospace' }}>{info.open_price || '--'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="昨收">
              <Text style={{ fontFamily: 'monospace' }}>{info.pre_close || '--'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="最高价" span={1}>
              <Text style={{ color: '#ff4d4f', fontFamily: 'monospace' }}>
                {info.high_price || '--'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="最低价" span={1}>
              <Text style={{ color: '#52c41a', fontFamily: 'monospace' }}>
                {info.low_price || '--'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="涨跌幅">
              <Text style={{ color: pctColor(parsePct(info.board_change_percent)), fontWeight: 600 }}>
                {info.board_change_percent || '--'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="成交额(亿)">
              <Text style={{ fontFamily: 'monospace' }}>{info.amount || '--'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="成交量(万手)">
              <Text style={{ fontFamily: 'monospace' }}>{info.volume || '--'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="净流入(亿)">
              <Text style={{
                color: pctColor(parseFloat(info.net_inflow)),
                fontFamily: 'monospace', fontWeight: 600,
              }}>
                {info.net_inflow ? (parseFloat(info.net_inflow) >= 0 ? '+' : '') + info.net_inflow : '--'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="排名">
              <Text style={{ fontFamily: 'monospace' }}>{info.rank_position || '--'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="涨跌家数">
              {info.up_down_count ? (
                <span>
                  <Text style={{ color: '#ff4d4f' }}>
                    {info.up_down_count.split('/')[0]}
                  </Text>
                  <Text style={{ color: colors.textTertiary }}> / </Text>
                  <Text style={{ color: '#52c41a' }}>
                    {info.up_down_count.split('/')[1]}
                  </Text>
                </span>
              ) : '--'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 7. 板块资金流排名 Panel（行业/概念/地域，东方财富）
// ═══════════════════════════════════════════════════════════════
const SectorFundFlowPanel: React.FC = () => {
  const [indicator, setIndicator] = useState<'今日' | '5日' | '10日'>('今日');
  const [sectorType, setSectorType] = useState<'行业资金流' | '概念资金流' | '地域资金流'>('行业资金流');
  const [data, setData] = useState<FundFlowConceptImmediate[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('sector:fundFlowRank', { indicator, sectorType });
    const ttlMs = indicator === '今日' ? TTL.SHORT : undefined;
    if (!force) {
      const c = readDailyCache<FundFlowConceptImmediate[]>(CK, { ttlMs });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getSectorFundFlowRank(indicator, sectorType);
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('板块资金流加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [indicator, sectorType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '板块名称', dataIndex: 'industry', width: 130, fixed: 'left' as const,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '指数', dataIndex: 'index_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_ratio', width: 90, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.change_ratio) - safeNum(b.change_ratio),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '流入(亿)', dataIndex: 'inflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '流出(亿)', dataIndex: 'outflow_amount', width: 90, align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text>,
    },
    {
      title: '净流入(亿)', dataIndex: 'net_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => safeNum(a.net_amount) - safeNum(b.net_amount),
      render: (v: number) => (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}
        </Text>
      ),
    },
    { title: '公司数', dataIndex: 'company_count', width: 80, align: 'right' as const },
    {
      title: '龙头股', dataIndex: 'leading_stock_name', width: 100,
      render: (v: string) => v ? <Tag color="red">{v}</Tag> : '--',
    },
    {
      title: '龙头涨幅', dataIndex: 'leading_stock_change', width: 100, align: 'right' as const,
      render: (v: number) => v == null ? '--' : (
        <Text style={{ color: pctColor(v), fontWeight: 600 }}>
          {safeNum(v) >= 0 ? '+' : ''}{fmtNum(v, 2)}%
        </Text>
      ),
    },
    {
      title: '龙头现价', dataIndex: 'current_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Text>板块类型：</Text>
          <Select
            value={sectorType}
            onChange={(v) => setSectorType(v)}
            size="small"
            style={{ width: 120 }}
            options={[
              { label: '行业资金流', value: '行业资金流' },
              { label: '概念资金流', value: '概念资金流' },
              { label: '地域资金流', value: '地域资金流' },
            ]}
          />
          <Text>周期：</Text>
          <Select
            value={indicator}
            onChange={(v) => setIndicator(v)}
            size="small"
            style={{ width: 90 }}
            options={[
              { label: '今日', value: '今日' },
              { label: '5日', value: '5日' },
              { label: '10日', value: '10日' },
            ]}
          />
          <Tag color="blue">共 {data.length} 条</Tag>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Table
        columns={columns as any}
        dataSource={data}
        loading={loading}
        rowKey={(r: any, i?: number) => `${r.industry}_${i}`}
        size="small"
        scroll={{ x: 1050, y: 660 }}
        pagination={createTablePagination(30)}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 8. 板块内个股资金流 Panel
// ═══════════════════════════════════════════════════════════════
const SectorStockFundPanel: React.FC = () => {
  const [symbol, setSymbol] = useState('白酒');
  const [inputVal, setInputVal] = useState('白酒');
  const [indicator, setIndicator] = useState<'今日' | '5日' | '10日'>('今日');
  const [data, setData] = useState<SectorStockFundFlowItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    if (!symbol.trim()) return;
    const CK = makeKey('sector:stockFundFlow', { symbol, indicator });
    const ttlMs = indicator === '今日' ? TTL.SHORT : undefined;
    if (!force) {
      const c = readDailyCache<SectorStockFundFlowItem[]>(CK, { ttlMs });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getSectorStockFundFlow(symbol, indicator);
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('板块个股资金流加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [symbol, indicator]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '代码', dataIndex: 'symbol', width: 90,
      render: (v: number) => <Text style={{ fontFamily: 'monospace' }}>{v}</Text>,
    },
    {
      title: '名称', dataIndex: 'name', width: 120,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '最新价', dataIndex: 'latest_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100, align: 'right' as const,
      sorter: (a: any, b: any) => parseFloat(a.change_percent) - parseFloat(b.change_percent),
      defaultSortOrder: 'descend' as const,
      render: (v: string) => {
        const n = parseFloat(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 600 }}>
            {n >= 0 ? '+' : ''}{v}
          </Text>
        );
      },
    },
    {
      title: '换手率', dataIndex: 'turnover_rate', width: 90, align: 'right' as const,
      render: (v: string) => v || '--',
    },
    {
      title: '流入', dataIndex: 'inflow_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#ff4d4f' }}>{v || '--'}</Text>,
    },
    {
      title: '流出', dataIndex: 'outflow_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#52c41a' }}>{v || '--'}</Text>,
    },
    {
      title: '净流入', dataIndex: 'net_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => parseFloat(a.net_amount) - parseFloat(b.net_amount),
      render: (v: string) => {
        const n = parseFloat(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 600 }}>
            {n > 0 ? '+' : ''}{v || '--'}
          </Text>
        );
      },
    },
    {
      title: '成交额', dataIndex: 'amount', width: 110, align: 'right' as const,
      render: (v: string) => v || '--',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Text>板块名称：</Text>
          <Input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onPressEnter={() => setSymbol(inputVal.trim())}
            size="small"
            style={{ width: 180 }}
            placeholder="如：白酒、半导体、保险"
          />
          <Button
            type="primary"
            size="small"
            icon={<SearchOutlined />}
            onClick={() => setSymbol(inputVal.trim())}
            loading={loading}
          >
            查询
          </Button>
          <Text>周期：</Text>
          <Select
            value={indicator}
            onChange={(v) => setIndicator(v)}
            size="small"
            style={{ width: 90 }}
            options={[
              { label: '今日', value: '今日' },
              { label: '5日', value: '5日' },
              { label: '10日', value: '10日' },
            ]}
          />
          <Tag color="blue">共 {data.length} 条</Tag>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 8 }}
        message="说明：资金流数据为字符串格式（带亿/万后缀），net_amount 含正负号，后端自动排序。"
      />
      <Table
        columns={columns as any}
        dataSource={data}
        loading={loading}
        rowKey={(r: any, i?: number) => `${r.symbol}_${i}`}
        size="small"
        scroll={{ x: 1050, y: 660 }}
        pagination={createTablePagination(30)}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// 9. 主力净流入排名 Panel
// ═══════════════════════════════════════════════════════════════
const MainFundFlowPanel: React.FC = () => {
  const [marketRange, setMarketRange] = useState<'全部股票' | '沪深A股' | '沪市A股' | '科创板' | '深市A股' | '创业板' | '沪市B股' | '深市B股'>('沪深A股');
  const [data, setData] = useState<SectorStockFundFlowItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    const CK = makeKey('sector:mainFundFlow', { marketRange });
    if (!force) {
      const c = readDailyCache<SectorStockFundFlowItem[]>(CK, { ttlMs: TTL.SHORT });
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = await sectorApi.getMainFundFlowSummary(marketRange);
      setData(list || []);
      writeDailyCache(CK, list || []);
    } catch (e: any) {
      message.error('主力净流入排名加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [marketRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const MARKET_OPTIONS: { label: string; value: typeof marketRange }[] = [
    { label: '全部股票', value: '全部股票' },
    { label: '沪深A股', value: '沪深A股' },
    { label: '沪市A股', value: '沪市A股' },
    { label: '科创板', value: '科创板' },
    { label: '深市A股', value: '深市A股' },
    { label: '创业板', value: '创业板' },
    { label: '沪市B股', value: '沪市B股' },
    { label: '深市B股', value: '深市B股' },
  ];

  const columns = [
    { title: '#', dataIndex: 'serial_number', width: 50, fixed: 'left' as const },
    {
      title: '代码', dataIndex: 'symbol', width: 90,
      render: (v: number) => <Text style={{ fontFamily: 'monospace' }}>{v}</Text>,
    },
    {
      title: '名称', dataIndex: 'name', width: 120,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '最新价', dataIndex: 'latest_price', width: 90, align: 'right' as const,
      render: (v: number) => fmtNum(v, 2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 100, align: 'right' as const,
      sorter: (a: any, b: any) => parseFloat(a.change_percent) - parseFloat(b.change_percent),
      defaultSortOrder: 'descend' as const,
      render: (v: string) => {
        const n = parseFloat(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 600 }}>
            {n >= 0 ? '+' : ''}{v}
          </Text>
        );
      },
    },
    {
      title: '换手率', dataIndex: 'turnover_rate', width: 90, align: 'right' as const,
      render: (v: string) => v || '--',
    },
    {
      title: '流入', dataIndex: 'inflow_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#ff4d4f' }}>{v || '--'}</Text>,
    },
    {
      title: '流出', dataIndex: 'outflow_amount', width: 100, align: 'right' as const,
      render: (v: string) => <Text style={{ color: '#52c41a' }}>{v || '--'}</Text>,
    },
    {
      title: '净流入', dataIndex: 'net_amount', width: 110, align: 'right' as const,
      sorter: (a: any, b: any) => parseFloat(a.net_amount) - parseFloat(b.net_amount),
      render: (v: string) => {
        const n = parseFloat(v);
        return (
          <Text style={{ color: pctColor(n), fontWeight: 600 }}>
            {n > 0 ? '+' : ''}{v || '--'}
          </Text>
        );
      },
    },
    {
      title: '成交额', dataIndex: 'amount', width: 110, align: 'right' as const,
      render: (v: string) => v || '--',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Text>市场范围：</Text>
          <Select
            value={marketRange}
            onChange={(v) => setMarketRange(v)}
            size="small"
            style={{ width: 120 }}
            options={MARKET_OPTIONS}
          />
          <Tag color="blue">共 {data.length} 条</Tag>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>
          刷新
        </Button>
      </div>
      <Table
        columns={columns as any}
        dataSource={data}
        loading={loading}
        rowKey={(r: any, i?: number) => `${r.symbol}_${i}`}
        size="small"
        scroll={{ x: 1050, y: 660 }}
        pagination={createTablePagination(30)}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════
// 6. 板块K线 Panel（行业/概念 切换 + candlestick + 成交量）
// ═══════════════════════════════════════════════════════════════

/** 计算 K 线移动平均线（基于收盘价） */
const boardCalcMA = (n: number, ohlc: number[][]): (number | string)[] => {
  const result: (number | string)[] = [];
  for (let i = 0; i < ohlc.length; i++) {
    if (i < n - 1) { result.push('-'); continue; }
    let sum = 0;
    for (let j = 0; j < n; j++) sum += ohlc[i - j][1] || 0;
    result.push(+(sum / n).toFixed(2));
  }
  return result;
};

const BoardKlinePanel: React.FC = () => {
  const { colors } = useTheme();
  const [boardType, setBoardType] = useState<'industry' | 'concept'>('industry');
  const [symbol, setSymbol] = useState('元件');
  const [inputVal, setInputVal] = useState('元件');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(60, 'day'),
    dayjs(),
  ]);
  const [data, setData] = useState<BoardIndexKline[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const fetchData = useCallback(async (force = false) => {
    const fmt = (d: Dayjs) => d.format('YYYYMMDD');
    const start = fmt(dateRange[0]);
    const end = fmt(dateRange[1]);
    const CK = makeKey('sector:boardKline', { boardType, symbol, start, end });
    if (!force) {
      const c = readDailyCache<BoardIndexKline[]>(CK);
      if (c) { setData(c); return; }
    }
    setLoading(true);
    try {
      const list = boardType === 'industry'
        ? await sectorApi.getIndustryIndexKline(symbol, start, end)
        : await sectorApi.getConceptIndexKline(symbol, start, end);
      setData(list || []);
      writeDailyCache(CK, list || []);
      if (!list?.length) message.warning(`${symbol} K线数据为空`);
    } catch (e: any) {
      message.error('板块K线加载失败: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }, [boardType, symbol, dateRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const chartData = useMemo(() => {
    const sorted = [...data].sort((a, b) => a.trade_date.localeCompare(b.trade_date));
    return {
      dates: sorted.map((r) => r.trade_date),
      ohlc: sorted.map((r) => [r.open_price, r.close_price, r.low_price, r.high_price]),
      volumes: sorted.map((r) => r.volume || 0),
    };
  }, [data]);

  // 计算 ECharts option（useMemo 避免每次渲染重建）
  const chartOption = useMemo<echarts.EChartsOption>(() => {
    const { dates, ohlc, volumes } = chartData;
    return {
      backgroundColor: 'transparent',
      animation: false,
      legend: { data: ['K线', 'MA5', 'MA10', 'MA20'], textStyle: { color: colors.textSecondary, fontSize: 11 }, top: 4 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(20,20,40,0.92)', borderColor: 'rgba(102,126,234,0.5)', textStyle: { color: '#fff', fontSize: 12 } },
      grid: [
        { left: 50, right: 20, top: 40, height: '58%' },
        { left: 50, right: 20, top: '72%', height: '20%' },
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { show: false } },
        { type: 'category', gridIndex: 1, data: dates, boundaryGap: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { show: false }, splitLine: { show: false } },
      ],
      yAxis: [
        { scale: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10 }, splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } } },
        { gridIndex: 1, scale: true, axisLine: { lineStyle: { color: colors.borderColor } }, axisLabel: { color: colors.textTertiary, fontSize: 10, formatter: (v: number) => { if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '亿'; if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'; return String(v); } }, splitLine: { lineStyle: { color: colors.borderColor, opacity: 0.3 } } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100, height: 18, bottom: 4, textStyle: { color: colors.textTertiary, fontSize: 10 } },
      ],
      series: [
        { name: 'K线', type: 'candlestick', data: ohlc, itemStyle: { color: '#ff4d4f', color0: '#52c41a', borderColor: '#ff4d4f', borderColor0: '#52c41a' } },
        { name: 'MA5', type: 'line', data: boardCalcMA(5, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#F59E0B' } },
        { name: 'MA10', type: 'line', data: boardCalcMA(10, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#56A4FF' } },
        { name: 'MA20', type: 'line', data: boardCalcMA(20, ohlc), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#A78BFA' } },
        { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes, itemStyle: { color: (params: any) => { const i = params.dataIndex; const o = ohlc[i]?.[0] ?? 0; const c = ohlc[i]?.[1] ?? 0; return c >= o ? '#ff4d4f' : '#52c41a'; }, opacity: 0.75 } },
      ],
    };
  }, [chartData, colors]);

  useEffect(() => {
    if (viewMode !== 'chart' || !chartRef.current) return;
    if (!chartInstance.current) chartInstance.current = echarts.init(chartRef.current);
    chartInstance.current.setOption(chartOption, true);
  }, [viewMode, chartOption]);

  useEffect(() => {
    if (viewMode !== 'chart' && chartInstance.current) { chartInstance.current.dispose(); chartInstance.current = null; }
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); };
  }, [viewMode]);

  useEffect(() => { return () => { chartInstance.current?.dispose(); chartInstance.current = null; }; }, []);

  const tableData = useMemo(() => {
    return [...data].sort((a, b) => b.trade_date.localeCompare(a.trade_date)).map((r, i, arr) => {
      const prev = i < arr.length - 1 ? arr[i + 1]?.close_price : null;
      const changeAmt = prev != null && r.close_price != null ? r.close_price - prev : null;
      const changePct = prev && r.close_price != null ? ((r.close_price - prev) / prev) * 100 : null;
      return { ...r, change_amount: changeAmt as any, change_percent: changePct as any };
    });
  }, [data]);

  const columns = [
    { title: '日期', dataIndex: 'trade_date', width: 110, render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</Text> },
    { title: '开盘', dataIndex: 'open_price', align: 'right' as const, width: 100, render: (v: number) => fmtNum(v, 2) },
    { title: '最高', dataIndex: 'high_price', align: 'right' as const, width: 100, render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{fmtNum(v, 2)}</Text> },
    { title: '最低', dataIndex: 'low_price', align: 'right' as const, width: 100, render: (v: number) => <Text style={{ color: '#52c41a' }}>{fmtNum(v, 2)}</Text> },
    { title: '收盘', dataIndex: 'close_price', align: 'right' as const, width: 100, render: (v: number) => <Text style={{ fontWeight: 600 }}>{fmtNum(v, 2)}</Text> },
    { title: '涨跌幅', dataIndex: 'change_percent', align: 'right' as const, width: 100, render: (v: number | null) => v == null ? '--' : <Text style={{ color: pctColor(v), fontWeight: 600 }}>{v >= 0 ? '+' : ''}{fmtNum(v, 2)}%</Text> },
    { title: '成交量', dataIndex: 'volume', align: 'right' as const, width: 120, render: (v: number) => fmtYi(v) },
    { title: '成交额', dataIndex: 'amount', align: 'right' as const, width: 120, render: (v: number) => fmtYi(v) },
  ];

  const defaultIndustrySymbol = '元件';
  const defaultConceptSymbol = '阿里巴巴概念';

  const handleBoardTypeChange = (v: 'industry' | 'concept') => {
    setBoardType(v);
    const defaultSym = v === 'industry' ? defaultIndustrySymbol : defaultConceptSymbol;
    setSymbol(defaultSym);
    setInputVal(defaultSym);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <Space wrap>
          <Radio.Group value={boardType} onChange={(e) => handleBoardTypeChange(e.target.value)} size="small" optionType="button" buttonStyle="solid">
            <Radio.Button value="industry">行业</Radio.Button>
            <Radio.Button value="concept">概念</Radio.Button>
          </Radio.Group>
          <Input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onPressEnter={() => setSymbol(inputVal.trim())}
            size="small"
            style={{ width: 180 }}
            placeholder={boardType === 'industry' ? '如：元件、白酒、保险' : '如：阿里巴巴概念'}
          />
          <Button type="primary" size="small" icon={<SearchOutlined />} onClick={() => setSymbol(inputVal.trim())}>查询</Button>
          <RangePicker value={dateRange} onChange={(v) => v && v[0] && v[1] && setDateRange([v[0], v[1]])} size="small" allowClear={false} />
          <Radio.Group value={viewMode} onChange={(e) => setViewMode(e.target.value)} size="small" optionType="button" buttonStyle="solid">
            <Radio.Button value="chart"><LineChartOutlined /> K线图</Radio.Button>
            <Radio.Button value="table">数据行</Radio.Button>
          </Radio.Group>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(true)} loading={loading}>刷新</Button>
      </div>

      <Alert type="info" showIcon style={{ marginBottom: 8 }} message="行业K线默认板块：元件 / 概念K线默认板块：阿里巴巴概念。日期必须是真实交易日，否则后端返回 422。" />

      {viewMode === 'chart' ? (
        chartData.dates.length === 0 && !loading ? (
          <Empty description="暂无K线数据" />
        ) : (
          <div ref={chartRef} style={{ width: '100%', height: 640, background: colors.bgCard, border: '1px solid ' + colors.borderColor, borderRadius: 6, padding: 4 }} />
        )
      ) : (
        <Table columns={columns as any} dataSource={tableData} loading={loading} rowKey="trade_date" size="small" scroll={{ x: 950, y: 640 }} pagination={createTablePagination(30)} />
      )}
    </div>
  );
};

// 主容器：Tabs
// ═══════════════════════════════════════════════════════════════
const SectorPage: React.FC = () => {
  const { colors } = useTheme();
  const [activeKey, setActiveKey] = useState('industry');

  return (
    <div style={{ background: colors.bgPrimary, height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ marginBottom: 12, flexShrink: 0 }}>
        <Title level={4} style={{ color: colors.textPrimary, margin: 0 }}>
          <AppstoreOutlined style={{ color: '#10B981', marginRight: 8 }} />
          行业 / 概念板块
        </Title>
        <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
          数据源：同花顺（行业一览/板块K线/概念资金流/概念简介）+ 东方财富（板块资金流/板块异动/盘口异动/个股资金流/主力净流入），通过后端 Redis 缓存
        </Text>
      </div>

      <Alert
        type="warning"
        showIcon
        closable
        style={{ marginBottom: 12, flexShrink: 0 }}
        message="部分后端接口仍异常（数据源问题，前端无法解决）"
        description={
          <div style={{ fontSize: 12 }}>
            <div>❌ <Text code>/api/stock/get-stock-board-industry-cons</Text> 行业成份股 — 需BK代码，推荐用申万行业名（数据源问题）</div>
          </div>
        }
      />

<div className="flex-content">
        <Tabs
          activeKey={activeKey}
          onChange={setActiveKey}
          type="card"
          size="small"
          style={{ height: '100%' }}
          items={[
          {
            key: 'industry',
            label: <span><AppstoreOutlined /> 行业一览</span>,
            children: <IndustryPanel />,
          },
          {
            key: 'board-kline',
            label: <span><LineChartOutlined /> 板块K线</span>,
            children: <BoardKlinePanel />,
          },
          {
            key: 'sector-fund-flow',
            label: <span><FundOutlined /> 板块资金流</span>,
            children: <SectorFundFlowPanel />,
          },
          {
            key: 'concept-fund',
            label: <span><FundOutlined /> 概念资金流</span>,
            children: <ConceptFundFlowPanel />,
          },
          {
            key: 'sector-stock-fund',
            label: <span><FundOutlined /> 个股资金流</span>,
            children: <SectorStockFundPanel />,
          },
          {
            key: 'main-fund-flow',
            label: <span><RocketOutlined /> 主力净流入</span>,
            children: <MainFundFlowPanel />,
          },
          {
            key: 'board-change',
            label: <span><ThunderboltOutlined /> 板块异动</span>,
            children: <BoardChangePanel />,
          },
          {
            key: 'stock-changes',
            label: <span><RocketOutlined /> 盘口异动</span>,
            children: <StockChangesPanel />,
          },
          {
            key: 'concept-info',
            label: <span><InfoCircleOutlined /> 概念简介</span>,
            children: <ConceptInfoPanel />,
          },
        ]}
      />
      </div>
    </div>
  );
};

export default React.memo(SectorPage);
