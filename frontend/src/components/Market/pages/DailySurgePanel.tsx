/**
 * 核心动态 - 当日涨幅榜单
 *
 * 对接接口：
 *   - GET /api/stock/get-yesterday-surge-stocks
 *     params: min_pct, max_pct, limit, sort
 *
 * 功能：
 *   - 可配置涨幅区间（min_pct / max_pct）
 *   - 可配置排序方式和条数
 *   - 支持缓存（当天内，TTL=5分钟）
 *   - 一键刷新
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Table, Typography, Space, Button, InputNumber, Select, message, Tag, Card, Row, Col,
} from 'antd';
import { ReloadOutlined, RiseOutlined } from '@ant-design/icons';
import { useTheme } from '@/themes';
import { stockCenterApi } from '@/api/stock';
import { readDailyCache, writeDailyCache, makeKey } from '@/utils/dailyCache';
import StockDetailDrawer from '../StockDetailDrawer';
import type { SurgeStockItem } from '@/types/stock';
import type { StockDetailItem } from '../StockDetailDrawer';

const { Text } = Typography;

/** 涨跌色 */
const pctColor = (v: number): string => {
  if (v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

/** 金额格式化 */
const fmtAmount = (v: number): string => {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(2);
};

/** 成交量格式化 */
const fmtVolume = (v: number): string => {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万';
  return v.toFixed(0);
};

const DailySurgePanel: React.FC = () => {
  const { colors } = useTheme();

  // 筛选参数
  const [minPct, setMinPct] = useState<number>(3);
  const [maxPct, setMaxPct] = useState<number>(10);
  const [limit, setLimit] = useState<number>(50);
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');

  const [data, setData] = useState<SurgeStockItem[]>([]);
  const [loading, setLoading] = useState(false);

  // 个股详情抽屉
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [drawerStocks, setDrawerStocks] = useState<StockDetailItem[]>([]);
  const [drawerIndex, setDrawerIndex] = useState(0);

  const openStockDetail = (symbol: string, name: string, allItems: SurgeStockItem[]) => {
    const list: StockDetailItem[] = allItems.map((item) => ({ symbol: item.symbol, name: item.name }));
    const idx = list.findIndex((s) => s.symbol === symbol);
    setDrawerStocks(list);
    setDrawerIndex(idx >= 0 ? idx : 0);
    setDrawerVisible(true);
  };

  const cacheKey = makeKey('stockCenter:surge', { min: minPct, max: maxPct, limit, sort: sortDir });

  const fetchData = useCallback(async (force = false) => {
    if (!force) {
      const cached = readDailyCache<SurgeStockItem[]>(cacheKey, { ttlMs: 5 * 60_000 });
      if (cached && cached.length > 0) {
        setData(cached);
        return;
      }
      if (cached) { /* 空数组缓存，忽略并重新请求 */ }
    }

    setLoading(true);
    try {
      const result = await stockCenterApi.getSurgeStocks({ min_pct: minPct, max_pct: maxPct, limit, sort: sortDir });
      if (result && result.length > 0) {
        setData(result);
        writeDailyCache(cacheKey, result);
      } else {
        setData([]);
        message.warning('暂无满足条件的涨幅股票');
      }
    } catch (e: any) {
      message.error('查询失败: ' + (e.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [minPct, maxPct, limit, sortDir, cacheKey]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '排名', key: 'rank', width: 55, align: 'center' as const,
      render: (_: any, __: any, i: number) => {
        const rank = i + 1;
        let color = colors.textPrimary;
        if (rank <= 3) color = '#ff4d4f';
        else if (rank <= 5) color = '#F59E0B';
        return <Text style={{ fontWeight: 700, color, fontSize: rank <= 3 ? 14 : 12 }}>{rank}</Text>;
      },
    },
    { title: '股票代码', dataIndex: 'symbol', width: 100,
      render: (v: string, r: SurgeStockItem) => (
        <a
          style={{ fontFamily: 'monospace', fontSize: 12, cursor: 'pointer', color: '#56A4FF' }}
          onClick={() => openStockDetail(v, r.name, data)}
        >
          {v}
        </a>
      ),
    },
    { title: '名称', dataIndex: 'name', width: 90,
      render: (v: string, r: SurgeStockItem) => (
        <a
          style={{ fontWeight: 600, cursor: 'pointer', color: colors.textPrimary }}
          onClick={() => openStockDetail(r.symbol, v, data)}
        >
          {v}
        </a>
      ),
    },
    { title: '昨日收盘', dataIndex: 'yesterday_close', width: 100, align: 'right' as const,
      render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary }}>{v.toFixed(2)}</Text>,
    },
    { title: '前日收盘', dataIndex: 'prev_close', width: 100, align: 'right' as const,
      render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textTertiary }}>{v.toFixed(2)}</Text>,
    },
    {
      title: '涨幅', dataIndex: 'change_percent', width: 90, align: 'right' as const,
      sorter: (a: SurgeStockItem, b: SurgeStockItem) => a.change_percent - b.change_percent,
      render: (v: number) => (
        <Tag color={v >= 0 ? 'red' : 'green'} style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </Tag>
      ),
    },
    { title: '成交量', dataIndex: 'volume', width: 100, align: 'right' as const,
      render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary, fontSize: 12 }}>{fmtVolume(v)}</Text>,
    },
    { title: '成交额', dataIndex: 'amount', width: 110, align: 'right' as const,
      render: (v: number) => <Text style={{ fontFamily: 'monospace', color: colors.textPrimary, fontSize: 12 }}>{fmtAmount(v)}</Text>,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 筛选工具栏 */}
      <Card
        size="small"
        style={{
          marginBottom: 12, background: colors.bgCard, borderColor: colors.borderColor, flexShrink: 0,
        }}
      >
        <Row gutter={16} align="middle">
          <Col>
            <Space size={6}>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>涨幅区间</Text>
              <InputNumber
                size="small" style={{ width: 65 }}
                min={0} max={maxPct} value={minPct}
                onChange={(v) => v != null && setMinPct(v)}
                formatter={(v) => `${v}%`}
                parser={(v) => Number(v?.replace('%', '') || 3) as any}
              />
              <Text style={{ color: colors.textTertiary }}>~</Text>
              <InputNumber
                size="small" style={{ width: 65 }}
                min={minPct} max={30} value={maxPct}
                onChange={(v) => v != null && setMaxPct(v)}
                formatter={(v) => `${v}%`}
                parser={(v) => Number(v?.replace('%', '') || 10) as any}
              />
            </Space>
          </Col>
          <Col>
            <Space size={6}>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>条数</Text>
              <Select size="small" value={limit} onChange={setLimit} style={{ width: 70 }}
                options={[
                  { value: 20, label: '20' },
                  { value: 50, label: '50' },
                  { value: 100, label: '100' },
                  { value: 200, label: '200' },
                ]}
              />
            </Space>
          </Col>
          <Col>
            <Space size={6}>
              <Text style={{ color: colors.textSecondary, fontSize: 12 }}>排序</Text>
              <Select size="small" value={sortDir} onChange={setSortDir} style={{ width: 70 }}
                options={[
                  { value: 'desc', label: '降序' },
                  { value: 'asc', label: '升序' },
                ]}
              />
            </Space>
          </Col>
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => fetchData(true)}
              loading={loading}
            >
              刷新
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <Table
          size="small"
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="symbol"
          scroll={{ x: 750, y: 'calc(100vh - 340px)' as any }}
          pagination={{
            pageSize: 30,
            showSizeChanger: true,
            pageSizeOptions: ['20', '30', '50', '100'],
            showTotal: (t) => `共 ${t} 条`,
            style: { marginBottom: 0 },
          }}
          locale={{ emptyText: '暂无数据，试试调整涨幅区间' }}
        />
      </div>

      {/* 个股详情抽屉 */}
      <StockDetailDrawer
        visible={drawerVisible}
        stockList={drawerStocks}
        currentIndex={drawerIndex}
        onClose={() => setDrawerVisible(false)}
        onNavigate={(idx) => setDrawerIndex(idx)}
      />
    </div>
  );
};

export default React.memo(DailySurgePanel);