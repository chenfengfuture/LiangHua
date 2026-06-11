import React, { useState, useEffect, lazy, Suspense } from 'react';
import { ConfigProvider, Spin, theme as antTheme } from 'antd';
import { ThemeProvider, useTheme } from '@/themes';
import Header from '@/components/Home/Header';
import HomeDashboard from '@/components/Home';
import { ErrorBoundary } from '@/components/Common';
import zhCN from 'antd/locale/zh_CN';

// 懒加载非默认页面
const NewsDashboard = lazy(() => import('@/components/News'));
const MarketDashboard = lazy(() => import('@/components/Market'));
const KlineAnalysis = lazy(() => import('@/components/KlineAnalysis'));
const QuantitativeDashboard = lazy(() => import('@/components/Quantitative'));
const SimulateDashboard = lazy(() => import('@/components/Simulate'));

const PageFallback: React.FC<{ colors: any }> = ({ colors }) => (
  <div style={{ display: 'flex', justifyContent: 'center', padding: 80, background: colors.bgPrimary, minHeight: 'calc(100vh - 60px)' }}>
    <Spin size="large" />
  </div>
);

const AppContent: React.FC = () => {
  const { theme, colors } = useTheme();
  const [activeTab, setActiveTab] = useState('market');

  // 更新 body 背景色和文字颜色
  useEffect(() => {
    document.body.style.background = colors.bgPrimary;
    document.body.style.color = colors.textPrimary;
  }, [theme, colors]);

  const renderContent = () => {
    // 首页（home）保持同步加载
    if (activeTab === 'home') {
      return (
        <ErrorBoundary name="首页">
          <HomeDashboard />
        </ErrorBoundary>
      );
    }

    return (
      <Suspense fallback={<PageFallback colors={colors} />}>
        <ErrorBoundary name={activeTab} key={activeTab}>
          {activeTab === 'news' && <NewsDashboard />}
          {activeTab === 'market' && <MarketDashboard />}
          {activeTab === 'kline' && <KlineAnalysis />}
          {activeTab === 'quant' && <QuantitativeDashboard />}
          {activeTab === 'simulate' && <SimulateDashboard />}
        </ErrorBoundary>
      </Suspense>
    );
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: colors.bgPrimary,
        transition: 'all 0.3s ease',
      }}
    >
      <Header activeTab={activeTab} onTabChange={setActiveTab} />
      {renderContent()}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <ThemeConsumer />
    </ThemeProvider>
  );
};

const ThemeConsumer: React.FC = () => {
  const { theme } = useTheme();

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme === 'dark' ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        token: {
          colorPrimary: '#3B82F6',
          colorSuccess: '#10B981',
          colorWarning: '#F59E0B',
          colorError: '#EF4444',
          colorInfo: '#3B82F6',
          borderRadius: 6,
        },
        components: {
          Table: {
            headerBg: theme === 'dark' ? '#161618' : '#F8FAFC',
            rowHoverBg: theme === 'dark' ? '#252528' : '#F1F5F9',
            borderColor: theme === 'dark' ? '#2A2A2D' : '#E2E8F0',
          },
          Card: {
            colorBgContainer: theme === 'dark' ? '#1E1E20' : '#FFFFFF',
            colorBorderSecondary: theme === 'dark' ? '#2A2A2D' : '#E2E8F0',
          },
        },
      }}
    >
      <AppContent />
    </ConfigProvider>
  );
};

export default App;