/**
 * 市场概览入口 - 侧边栏 + 子页面路由
 *
 * sidebarKey 对应子页面：
 *   dashboard    → pages/Dashboard.tsx（总览仪表盘）
 *   dragon-tiger → pages/DragonTiger.tsx（龙虎榜）
 *   其余子页面后续扩展
 */

import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { Spin, Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';
import Sidebar from './Sidebar';

// 懒加载子页面
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DragonTiger = lazy(() => import('./pages/DragonTiger'));
const FundFlow = lazy(() => import('./pages/FundFlow'));
const StockCenter = lazy(() => import('./pages/StockCenter'));
const Sector = lazy(() => import('./pages/Sector'));
const LimitUp = lazy(() => import('./pages/LimitUp'));
const Kline = lazy(() => import('./pages/Kline'));
const MarginTrade = lazy(() => import('./pages/MarginTrade'));
const CoreDynamics = lazy(() => import('./pages/CoreDynamics'));
const AbnormalMonitor = lazy(() => import('./pages/AbnormalMonitor'));

/** 子页面映射 */
const pageMap: Record<string, React.LazyExoticComponent<React.FC>> = {
  dashboard: Dashboard,
  'dragon-tiger': DragonTiger,
  'fund-flow': FundFlow,
  stock: StockCenter,
  sector: Sector,
  'limit-up': LimitUp,
  kline: Kline,
  'margin-trade': MarginTrade,
  'core-dynamics': CoreDynamics,
  'abnormal-monitor': AbnormalMonitor,
};

/** 占位页面（尚未实现的子分类） */
const Placeholder: React.FC<{ title: string }> = ({ title }) => {
  const { colors } = useTheme();
  return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <h2 style={{ color: colors.textPrimary }}>{title}</h2>
      <p style={{ color: colors.textTertiary }}>该模块正在开发中，敬请期待…</p>
    </div>
  );
};

/** 子分类名称映射（sidebarKey → 中文名） */
const nameMap: Record<string, string> = {
  dashboard: '总览仪表盘',
  kline: '行情与 K 线',
  stock: '个股中心',
  'core-dynamics': '核心动态',
  'abnormal-monitor': '异动监控',
  'fund-flow': '资金流向',
  'dragon-tiger': '龙虎榜',
  'margin-trade': '融资融券',
  sector: '行业 / 概念板块',
  'limit-up': '涨停池',
  'tech-select': '技术选股',
};

const MarketDashboard: React.FC = () => {
  const { colors } = useTheme();
  const [sidebarKey, setSidebarKey] = useState<string>('dashboard');
  // 跳转历史栈：仅记录通过 market:navigate 自定义事件触发的跳转来源
  const historyRef = useRef<string[]>([]);
  const isNavigatingRef = useRef(false);
  const [canGoBack, setCanGoBack] = useState(false);

  // 监听 Dashboard 内部触发的子分类跳转事件（如龙虎榜详情按钮）
  useEffect(() => {
    const handler = (e: Event) => {
      const ce = e as CustomEvent<{ key: string }>;
      if (ce.detail?.key && pageMap[ce.detail.key]) {
        setSidebarKey((prev) => {
          if (prev !== ce.detail.key) {
            historyRef.current.push(prev);
            isNavigatingRef.current = true;
            setCanGoBack(true);
          }
          return ce.detail.key;
        });
      }
    };
    window.addEventListener('market:navigate', handler as EventListener);
    return () => window.removeEventListener('market:navigate', handler as EventListener);
  }, []);

  // 用户主动点击 Sidebar 切换：清空跳转历史（不算"跳转关系"）
  const handleSidebarChange = (key: string) => {
    if (isNavigatingRef.current) {
      // 来自自定义事件触发，已记录历史，跳过
      isNavigatingRef.current = false;
    } else {
      // 用户手动切换 → 清空历史栈
      historyRef.current = [];
      setCanGoBack(false);
    }
    setSidebarKey(key);
  };

  // 返回上一页
  const handleGoBack = () => {
    const prev = historyRef.current.pop();
    if (prev) {
      isNavigatingRef.current = true;
      setSidebarKey(prev);
      setCanGoBack(historyRef.current.length > 0);
    }
  };

  const PageComponent = pageMap[sidebarKey];

  return (
    <div
      style={{
        display: 'flex',
        background: colors.bgPrimary,
        minHeight: 'calc(100vh - 60px)',
      }}
    >
      <Sidebar activeKey={sidebarKey} onChange={handleSidebarChange} />
      <div
        style={{
          flex: 1,
          padding: '12px 20px 20px',
          minWidth: 0,
          position: 'relative',
        }}
      >
        {/* 返回按钮（仅在有跳转历史时显示） */}
        {canGoBack && (
          <div style={{ marginBottom: 10 }}>
            <Button
              type="default"
              size="small"
              icon={<ArrowLeftOutlined />}
              onClick={handleGoBack}
              style={{
                background: 'rgba(86,164,255,0.10)',
                border: '1px solid rgba(86,164,255,0.40)',
                color: '#56A4FF',
                fontWeight: 600,
              }}
            >
              返回 {nameMap[historyRef.current[historyRef.current.length - 1]] || '上一页'}
            </Button>
          </div>
        )}
        <Suspense
          fallback={
            <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
              <Spin size="large" />
            </div>
          }
        >
          {PageComponent ? (
            <PageComponent />
          ) : (
            <Placeholder title={nameMap[sidebarKey] || sidebarKey} />
          )}
        </Suspense>
      </div>
    </div>
  );
};

export default MarketDashboard;
