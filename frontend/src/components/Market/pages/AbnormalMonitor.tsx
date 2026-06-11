/**
 * 异动监控页面 - 市场概览子页面
 *
 * 对接后端接口：
 *   - GET /api/stock/get_stock_changes_em?symbol=<异动类型>
 *     按异动类型查询个股盘口异动数据（22种异动类型全部接入）
 *
 * 后端解析逻辑（board/service.py:parse_related_info）：
 *   - 四段型（大笔买入/大笔卖出/有大买盘/封跌停板/有大卖盘）：成交量(手),价格,涨跌幅,成交额
 *   - 三段型（火箭发射/快速反弹/高台跳水/竞价上涨/高开5日线/向上缺口/60日大幅上涨/加速下跌/竞价下跌/低开5日线/向下缺口）：涨跌幅,价格,强度
 *   - 二段型（封涨停板/打开跌停板/打开涨停板/60日新高/60日新低）：价格,涨跌幅
 *   - 一段型：未知格式保留原始字符串
 *
 * 注意：
 *   - 二段型（封涨停板等）无成交量/成交额/强度字段
 *   - 四段型有完整的量价额数据
 *   - 三段型有价格/涨跌幅/强度，无成交量数据
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Table, Typography, Space, Button, Tag, Card, Row, Col, Statistic, message, Select,
} from 'antd';
import {
  ReloadOutlined, WarningOutlined,
  ArrowUpOutlined, ArrowDownOutlined, ShoppingCartOutlined, StopOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import { sectorApi } from '@/api/stock';
import { readDailyCache, writeDailyCache, makeKey } from '@/utils/dailyCache';
import { safeToFixed, fmtVolume, fmtNumber } from '@/utils/format';
import StockDetailDrawer from '../StockDetailDrawer';
import type { StockChangeItem } from '@/types/stock';
import type { StockDetailItem } from '../StockDetailDrawer';

const { Text, Title } = Typography;

/** 涨跌色 */
const pctColor = (v: number): string => {
  if (v === 0) return '#999';
  return v > 0 ? '#ff4d4f' : '#52c41a';
};

/** 后端全部22种异动类型（按解析模式分组） */
const ALL_TYPES: Record<string, { key: string; label: string; color: string; icon: React.ReactNode; group: string }> = {
  // ── 三段型：涨跌幅,价格,强度 ──
  '火箭发射': { key: '火箭发射', label: '火箭发射', color: '#ff4d4f', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '快速反弹': { key: '快速反弹', label: '快速反弹', color: '#ff7875', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '竞价上涨': { key: '竞价上涨', label: '竞价上涨', color: '#ff9a3c', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '高开5日线': { key: '高开5日线', label: '高开5日线', color: '#ff9a3c', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '向上缺口': { key: '向上缺口', label: '向上缺口', color: '#ff4d4f', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '60日新高': { key: '60日新高', label: '60日新高', color: '#ff4d4f', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '60日大幅上涨': { key: '60日大幅上涨', label: '60日大涨', color: '#ff4d4f', icon: <ArrowUpOutlined />, group: '拉升异动' },
  '加速下跌': { key: '加速下跌', label: '加速下跌', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '高台跳水': { key: '高台跳水', label: '高台跳水', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '竞价下跌': { key: '竞价下跌', label: '竞价下跌', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '低开5日线': { key: '低开5日线', label: '低开5日线', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '向下缺口': { key: '向下缺口', label: '向下缺口', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '60日新低': { key: '60日新低', label: '60日新低', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  '60日大幅下跌': { key: '60日大幅下跌', label: '60日大跌', color: '#52c41a', icon: <ArrowDownOutlined />, group: '下跌异动' },
  // ── 四段型：成交量,价格,涨跌幅,成交额 ──
  '大笔买入': { key: '大笔买入', label: '大笔买入', color: '#F59E0B', icon: <ShoppingCartOutlined />, group: '大单异动' },
  '大笔卖出': { key: '大笔卖出', label: '大笔卖出', color: '#722ed1', icon: <ShoppingCartOutlined />, group: '大单异动' },
  '有大买盘': { key: '有大买盘', label: '有大买盘', color: '#F59E0B', icon: <ShoppingCartOutlined />, group: '大单异动' },
  '有大卖盘': { key: '有大卖盘', label: '有大卖盘', color: '#722ed1', icon: <ShoppingCartOutlined />, group: '大单异动' },
  // ── 二段型：价格,涨跌幅 ──
  '封涨停板': { key: '封涨停板', label: '封涨停板', color: '#ff4d4f', icon: <StopOutlined />, group: '涨跌停' },
  '打开跌停板': { key: '打开跌停板', label: '打开跌停板', color: '#52c41a', icon: <StopOutlined />, group: '涨跌停' },
  '封跌停板': { key: '封跌停板', label: '封跌停板', color: '#52c41a', icon: <StopOutlined />, group: '涨跌停' },
  '打开涨停板': { key: '打开涨停板', label: '打开涨停板', color: '#ff4d4f', icon: <StopOutlined />, group: '涨跌停' },
};

/** 分组标签配置 */
const GROUP_CONFIG = [
  { key: '拉升异动', label: '拉升异动', color: '#ff4d4f' },
  { key: '下跌异动', label: '下跌异动', color: '#52c41a' },
  { key: '大单异动', label: '大单异动', color: '#F59E0B' },
  { key: '涨跌停', label: '涨跌停', color: '#ff4d4f' },
];

const AbnormalMonitor: React.FC = () => {
  const { colors } = useTheme();

  // 当前选中类型（默认火箭发射，与后端一致）
  const [activeType, setActiveType] = useState<string>('火箭发射');
  // 当前选中分组
  const [activeGroup, setActiveGroup] = useState<string>('拉升异动');

  // 各类型数据 Map
  const [dataMap, setDataMap] = useState<Record<string, StockChangeItem[]>>({});
  const [loading, setLoading] = useState(false);

  // 个股详情抽屉
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [drawerStocks, setDrawerStocks] = useState<StockDetailItem[]>([]);
  const [drawerIndex, setDrawerIndex] = useState(0);

  const openStockDetail = (symbol: string, _name: string, allItems: StockChangeItem[]) => {
    const list: StockDetailItem[] = allItems.map((item) => ({ symbol: item.symbol, name: item.name }));
    const idx = list.findIndex((s) => s.symbol === symbol);
    setDrawerStocks(list);
    setDrawerIndex(idx >= 0 ? idx : 0);
    setDrawerVisible(true);
  };

  /** 获取单个类型数据 */
  const fetchTypeData = useCallback(async (type: string, force = false) => {
    const cacheKey = makeKey('abnormal:stockChanges', { type });

    if (!force) {
      const cached = readDailyCache<StockChangeItem[]>(cacheKey, { ttlMs: 5 * 60_000 });
      if (cached && cached.length > 0) {
        setDataMap((prev) => ({ ...prev, [type]: cached }));
        return true;
      }
    }

    try {
      const result = await sectorApi.getStockChanges(type);
      if (result && result.length > 0) {
        setDataMap((prev) => ({ ...prev, [type]: result }));
        writeDailyCache(cacheKey, result);
      } else {
        setDataMap((prev) => ({ ...prev, [type]: [] }));
      }
      return true;
    } catch (e: any) {
      message.error(`[${type}] 查询失败: ${e.message || '未知错误'}`);
      return false;
    }
  }, []);

  /** 切换分组：自动选中该组第一个类型 */
  const handleGroupChange = (groupKey: string) => {
    setActiveGroup(groupKey);
    const firstType = Object.values(ALL_TYPES).find((t) => t.group === groupKey);
    if (firstType) {
      setActiveType(firstType.key);
    }
  };

  /** 首次加载 + 类型切换 */
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchTypeData(activeType);
      setLoading(false);
    };
    if (!dataMap[activeType]) {
      load();
    }
  }, [activeType, fetchTypeData, dataMap]);

  /** 全部刷新 */
  const handleRefreshAll = async () => {
    setLoading(true);
    const uniqueTypes = [...new Set(Object.values(ALL_TYPES).map((t) => t.key))];
    for (const type of uniqueTypes) {
      await fetchTypeData(type, true);
    }
    setLoading(false);
    message.success('已刷新全部异动数据');
  };

  /** 当前数据 */
  const currentData = dataMap[activeType] || [];
  const typeCfg = ALL_TYPES[activeType];

  /** 聚合统计（部分类型无强度/成交量，统计时处理 null） */
  const itemsWithStrength = currentData.filter((item) => item.strength_level != null);
  const itemsWithAmount = currentData.filter((item) => item.amount != null);
  const avgStrength = itemsWithStrength.length > 0
    ? itemsWithStrength.reduce((s, item) => s + (item.strength_level || 0), 0) / itemsWithStrength.length
    : 0;
  const avgChange = currentData.length > 0
    ? currentData.reduce((s, item) => s + (item.change_percent || 0), 0) / currentData.length
    : 0;
  const totalAmount = itemsWithAmount.reduce((s, item) => s + (item.amount || 0), 0);

  /** 当前选中的分组下有哪些类型（给 Select 用） */
  const groupTypes = Object.values(ALL_TYPES).filter((t) => t.group === activeGroup);

  /** 表格列定义 */
  const columns = [
    {
      title: '时间', dataIndex: 'occur_time', width: 85, align: 'center' as const,
      render: (v: string) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 12, color: colors.textPrimary }}>{v}</Text>
      ),
    },
    {
      title: '代码', dataIndex: 'symbol', width: 105,
      render: (v: string, r: StockChangeItem) => (
        <a
          style={{ fontFamily: 'monospace', fontSize: 12, cursor: 'pointer', color: '#56A4FF' }}
          onClick={() => openStockDetail(v, r.name, currentData)}
        >
          {v}
        </a>
      ),
    },
    {
      title: '名称', dataIndex: 'name', width: 85,
      render: (v: string, r: StockChangeItem) => (
        <a
          style={{ fontWeight: 600, cursor: 'pointer', color: colors.textPrimary }}
          onClick={() => openStockDetail(r.symbol, v, currentData)}
        >
          {v}
        </a>
      ),
    },
    {
      title: '价格', dataIndex: 'price', width: 80, align: 'right' as const,
      render: (v: number | null) => (
        <Text style={{ fontFamily: 'monospace', color: colors.textPrimary, fontSize: 12 }}>
          {v != null ? safeToFixed(v, 2) : '--'}
        </Text>
      ),
    },
    {
      title: '涨跌幅', dataIndex: 'change_percent', width: 85, align: 'right' as const,
      sorter: (a: StockChangeItem, b: StockChangeItem) => a.change_percent - b.change_percent,
      render: (v: number | null) => {
        if (v == null) return <Text style={{ color: colors.textTertiary }}>--</Text>;
        return (
          <Tag color={pctColor(v)} style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}%
          </Tag>
        );
      },
    },
    {
      title: '成交量', dataIndex: 'volume', width: 95, align: 'right' as const,
      render: (v: number | null) => (
        <Text style={{ fontFamily: 'monospace', color: colors.textPrimary, fontSize: 12 }}>
          {v != null ? fmtVolume(v) : '--'}
        </Text>
      ),
    },
    {
      title: '成交额', dataIndex: 'amount', width: 105, align: 'right' as const,
      render: (v: number | null) => (
        <Text style={{ fontFamily: 'monospace', color: colors.textPrimary, fontSize: 12 }}>
          {v != null ? `${fmtNumber(v)}万` : '--'}
        </Text>
      ),
    },
    {
      title: '强度', dataIndex: 'strength_level', width: 75, align: 'right' as const,
      sorter: (a: StockChangeItem, b: StockChangeItem) => (a.strength_level || 0) - (b.strength_level || 0),
      render: (v: number | null) => {
        if (v == null) return <Text style={{ color: colors.textTertiary }}>--</Text>;
        const color = v >= 1 ? '#ff4d4f' : v >= 0.5 ? '#F59E0B' : colors.textSecondary;
        return (
          <Text style={{ fontFamily: 'monospace', color, fontWeight: 600, fontSize: 12 }}>
            {v.toFixed(2)}
          </Text>
        );
      },
    },
  ];

  return (
    <div className="page-layout" style={{ padding: '0 4px 8px' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <WarningOutlined style={{ fontSize: 20, color: '#ff4d4f', marginRight: 8 }} />
        <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>异动监控</Title>
      </div>

      <div className="flex-content" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* 分组按钮 + 类型选择 + 刷新 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexShrink: 0, flexWrap: 'wrap' }}>
          {/* 4个分组按钮 */}
          <Space size={4}>
            {GROUP_CONFIG.map((g) => (
              <Button
                key={g.key}
                size="small"
                type={activeGroup === g.key ? 'primary' : 'default'}
                danger={g.color === '#ff4d4f'}
                onClick={() => handleGroupChange(g.key)}
                style={{
                  fontSize: 12,
                  ...(activeGroup === g.key
                    ? {}
                    : { color: g.color, borderColor: g.color }),
                }}
              >
                {g.label}
              </Button>
            ))}
          </Space>

          {/* 当前分组下的具体类型 Select */}
          <Select
            size="small"
            value={activeType}
            onChange={setActiveType}
            style={{ width: 140 }}
            options={groupTypes.map((t) => ({
              value: t.key,
              label: t.label,
            }))}
          />

          <div style={{ flex: 1 }} />

          <Space>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={handleRefreshAll}
              loading={loading}
            >
              刷新全部
            </Button>
          </Space>
        </div>

        {/* 统计卡片行 */}
        <Row gutter={12} style={{ marginBottom: 12, flexShrink: 0 }}>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic
                title={<Text style={{ fontSize: 11, color: colors.textTertiary }}>当前类型</Text>}
                value={activeType}
                valueStyle={{ fontSize: 14, fontWeight: 600, color: typeCfg?.color || colors.textPrimary }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic
                title={<Text style={{ fontSize: 11, color: colors.textTertiary }}>异动笔数</Text>}
                value={currentData.length}
                suffix="笔"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: colors.textPrimary }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic
                title={<Text style={{ fontSize: 11, color: colors.textTertiary }}>平均涨跌幅</Text>}
                value={avgChange}
                precision={2}
                suffix="%"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: avgChange >= 0 ? '#ff4d4f' : '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: colors.bgCard, borderColor: colors.borderColor }}>
              <Statistic
                title={<Text style={{ fontSize: 11, color: colors.textTertiary }}>平均强度 / 总成交额</Text>}
                value={avgStrength}
                precision={2}
                suffix={
                  <span style={{ fontSize: 11, color: colors.textTertiary, fontWeight: 400 }}>
                    &nbsp;/&nbsp;{fmtNumber(totalAmount)}万
                  </span>
                }
                valueStyle={{ fontSize: 20, fontWeight: 700, color: avgStrength >= 1 ? '#ff4d4f' : '#F59E0B' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 数据表格 */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <Table
            size="small"
            columns={columns}
            dataSource={currentData}
            loading={loading}
            rowKey={(record, idx) => `${record.symbol}_${record.occur_time}_${idx}`}
            scroll={{ x: 750, y: 'calc(100vh - 380px)' as any }}
            pagination={{
              pageSize: 30,
              showSizeChanger: true,
              pageSizeOptions: ['20', '30', '50', '100'],
              showTotal: (t) => `共 ${t} 条`,
              style: { marginBottom: 0 },
            }}
            locale={{ emptyText: '暂无异动数据' }}
          />
        </div>
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

export default React.memo(AbnormalMonitor);