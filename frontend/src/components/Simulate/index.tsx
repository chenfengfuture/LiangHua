/**
 * 模拟交易 - 主页面
 *
 * 功能：
 *   - 账户概览（总资产/可用资金/持仓市值/总盈亏）
 *   - 下单交易（买入/卖出，查价，费用计算）
 *   - 持仓列表（实时盈亏）
 *   - 委托记录
 *   - 成交历史
 *   - 权益曲线 + 交易统计
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Tabs, Row, Col, Button, message, Typography, Spin, Modal, Space,
} from 'antd';
import {
  WalletOutlined, SwapOutlined, PieChartOutlined,
  ClockCircleOutlined, CheckCircleOutlined, BarChartOutlined,
  DeleteOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import {
  getAccount, getPositions, getOrders, getTrades,
  getDailyRecords, refreshPositionsPrice, refreshTotalAssets,
  recordDailySnapshot, calcStats, resetAll,
} from '@/api/simulate';
import AccountSummary from './AccountSummary';
import Portfolio from './Portfolio';
import OrderForm from './OrderForm';
import OrderList from './OrderList';
import TradeHistory from './TradeHistory';
import EquityChart from './EquityChart';
import type {
  SimAccount, SimPosition, SimOrder, SimTrade, SimDailyRecord, SimStats,
} from '@/types/stock';

const { Text, Title } = Typography;

const SimulateDashboard: React.FC = () => {
  const { colors } = useTheme();
  const [activeTab, setActiveTab] = useState('trade');
  const [loading, setLoading] = useState(false);
  const [account, setAccount] = useState<SimAccount>(getAccount());
  const [positions, setPositions] = useState<SimPosition[]>([]);
  const [orders, setOrders] = useState<SimOrder[]>([]);
  const [trades, setTrades] = useState<SimTrade[]>([]);
  const [dailyRecords, setDailyRecords] = useState<SimDailyRecord[]>([]);
  const [stats, setStats] = useState<SimStats>(calcStats());

  const totalProfit = account.total_assets - account.initial_capital;
  const totalProfitPct = account.initial_capital > 0
    ? (totalProfit / account.initial_capital) * 100
    : 0;

  // 加载所有数据
  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      // 刷新持仓现价（并行）
      await refreshPositionsPrice();
      // 刷新总资产
      const acct = refreshTotalAssets();
      setAccount({ ...acct });
      setPositions([...getPositions()]);
      setOrders([...getOrders()]);
      setTrades([...getTrades()]);
      setDailyRecords([...getDailyRecords()]);
      setStats(calcStats());
      // 每日首次加载时记录资产快照
      recordDailySnapshot();
    } catch (e: any) {
      console.error('[Simulate] 加载失败', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // 下单成功回调
  const handleTradeSuccess = useCallback(() => {
    loadAll();
  }, [loadAll]);

  // 卖出按钮点击
  const handleSell = useCallback((symbol: string, name: string) => {
    setActiveTab('trade');

    // 通过自定义事件告知下单面板填入卖出信息
    window.dispatchEvent(new CustomEvent('simulate:sell', { detail: { symbol, name } }));
  }, []);

  // 重置账户
  const handleReset = useCallback(() => {
    Modal.confirm({
      title: '确认重置',
      content: '重置将清空所有模拟交易数据（账户、持仓、委托、成交记录），确认继续？',
      okText: '确认重置',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        resetAll();
        message.success('已重置账户');
        loadAll();
      },
    });
  }, [loadAll]);

  const tabItems = [
    {
      key: 'trade',
      label: <span><SwapOutlined /> 交易</span>,
      children: (
        <Row gutter={16}>
          <Col span={8}>
            <OrderForm account={account} positions={positions} onSuccess={handleTradeSuccess} />
          </Col>
          <Col span={16}>
            <div style={{ background: colors.bgCard, border: `1px solid ${colors.borderColor}`, borderRadius: 6, padding: 12 }}>
              <Text style={{ color: colors.textPrimary, fontWeight: 600, fontSize: 14, display: 'block', marginBottom: 8 }}>
                <PieChartOutlined /> 当前持仓
              </Text>
              <Portfolio positions={positions} loading={loading} onSell={handleSell} />
            </div>
          </Col>
        </Row>
      ),
    },
    {
      key: 'orders',
      label: <span><ClockCircleOutlined /> 委托</span>,
      children: <OrderList orders={orders} loading={loading} />,
    },
    {
      key: 'trades',
      label: <span><CheckCircleOutlined /> 成交</span>,
      children: <TradeHistory trades={trades} loading={loading} />,
    },
    {
      key: 'analysis',
      label: <span><BarChartOutlined /> 分析</span>,
      children: <EquityChart records={dailyRecords} stats={stats} />,
    },
  ];

  return (
    <div className="page-layout" style={{ padding: '0 4px 8px' }}>
      {/* 标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexShrink: 0 }}>
        <Space>
          <WalletOutlined style={{ fontSize: 20, color: '#3B82F6' }} />
          <Title level={4} style={{ margin: 0, color: colors.textPrimary }}>模拟交易</Title>
          <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
            初始本金 ¥{account.initial_capital.toLocaleString()}
          </Text>
        </Space>
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>刷新</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={handleReset}>重置</Button>
        </Space>
      </div>

      {/* 账户概览卡片 */}
      <AccountSummary account={account} totalProfit={totalProfit} totalProfitPct={totalProfitPct} />

      {/* 主内容区 */}
      <Spin spinning={loading} style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="small"
            type="card"
            items={tabItems}
            style={{ height: '100%' }}
          />
        </div>
      </Spin>
    </div>
  );
};

export default SimulateDashboard;