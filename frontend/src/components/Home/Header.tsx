import React from 'react';
import { Input, Badge, Switch, Avatar, Space, Typography } from 'antd';
import { SearchOutlined, BellOutlined, SunOutlined, MoonOutlined } from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

interface HeaderProps {
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

const Header: React.FC<HeaderProps> = ({ activeTab = 'home', onTabChange }) => {
  const { theme, colors, toggleTheme } = useTheme();

  const tabs = [
    { key: 'market', label: '市场概览' },
    { key: 'kline', label: 'K线分析' },
    { key: 'quant', label: '量化策略' },
    { key: 'news', label: '新闻舆情' },
    { key: 'simulate', label: '模拟交易' },
  ];

  return (
    <div
      style={{
        height: '60px',
        background: colors.bgSecondary,
        borderBottom: `1px solid ${colors.borderColor}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: theme === 'dark' 
          ? '0 4px 20px rgba(86, 164, 255, 0.08)' 
          : '0 4px 20px rgba(0, 0, 0, 0.05)',
      }}
    >
      {/* Logo区域 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: theme === 'dark' 
              ? 'linear-gradient(135deg, #1a1a1f 0%, #2a2a30 100%)' 
              : 'linear-gradient(135deg, #1E293B 0%, #334155 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${theme === 'dark' ? 'rgba(86, 164, 255, 0.3)' : 'rgba(84, 106, 207, 0.3)'}`,
            boxShadow: theme === 'dark' 
              ? '0 0 20px rgba(86, 164, 255, 0.15), 0 4px 12px rgba(0,0,0,0.3)' 
              : '0 0 20px rgba(84, 106, 207, 0.1), 0 4px 12px rgba(0,0,0,0.1)',
            transition: 'all 0.3s ease',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.boxShadow = theme === 'dark' 
              ? '0 0 30px rgba(86, 164, 255, 0.25), 0 6px 20px rgba(0,0,0,0.4)' 
              : '0 0 30px rgba(84, 106, 207, 0.2), 0 6px 20px rgba(0,0,0,0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = theme === 'dark' 
              ? '0 0 20px rgba(86, 164, 255, 0.15), 0 4px 12px rgba(0,0,0,0.3)' 
              : '0 0 20px rgba(84, 106, 207, 0.1), 0 4px 12px rgba(0,0,0,0.1)';
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <defs>
              <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#56A4FF" />
                <stop offset="50%" stopColor="#546ACF" />
                <stop offset="100%" stopColor="#514EBD" />
              </linearGradient>
            </defs>
            <path
              d="M3 13L9 7L15 11L21 5"
              stroke="url(#logoGradient)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M21 19V13H15"
              stroke="#56A4FF"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="12" cy="12" r="9" stroke="#546ACF" strokeWidth="1.5" opacity="0.4" />
          </svg>
        </div>
        <div>
          <Text 
            strong 
            style={{ 
              fontSize: '20px', 
              fontWeight: 800,
              background: 'linear-gradient(135deg, #56A4FF 0%, #546ACF 50%, #514EBD 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              display: 'block',
              lineHeight: '1.2',
              letterSpacing: '2px',
            }}
          >
            晨枫量化
          </Text>
        </div>
      </div>

      {/* 中间导航 */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {tabs.map((tab) => (
          <div
            key={tab.key}
            onClick={() => onTabChange?.(tab.key)}
            style={{
              padding: '10px 24px',
              borderRadius: '12px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === tab.key ? 700 : 500,
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              background: activeTab === tab.key 
                ? theme === 'dark'
                  ? 'linear-gradient(135deg, rgba(86, 164, 255, 0.15) 0%, rgba(81, 78, 189, 0.15) 100%)'
                  : 'linear-gradient(135deg, rgba(86, 164, 255, 0.1) 0%, rgba(81, 78, 189, 0.1) 100%)'
                : 'transparent',
              color: activeTab === tab.key 
                ? (theme === 'dark' ? '#56A4FF' : '#546ACF') 
                : colors.textSecondary,
              border: `1px solid ${activeTab === tab.key 
                ? (theme === 'dark' ? 'rgba(86, 164, 255, 0.3)' : 'rgba(84, 106, 207, 0.3)') 
                : 'transparent'}`,
              boxShadow: activeTab === tab.key 
                ? (theme === 'dark' 
                    ? '0 0 20px rgba(86, 164, 255, 0.2), inset 0 1px 0 rgba(255,255,255,0.05)' 
                    : '0 0 20px rgba(86, 164, 255, 0.15), inset 0 1px 0 rgba(255,255,255,0.5)')
                : 'none',
              position: 'relative',
              overflow: 'hidden',
            }}
            onMouseEnter={(e) => {
              if (activeTab !== tab.key) {
                e.currentTarget.style.background = colors.hoverBg;
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = theme === 'dark'
                  ? '0 4px 12px rgba(0,0,0,0.3)'
                  : '0 4px 12px rgba(0,0,0,0.1)';
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== tab.key) {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = 'scale(0.95)';
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = activeTab !== tab.key ? 'translateY(-2px)' : 'scale(1)';
            }}
          >
            {tab.label}
          </div>
        ))}
      </div>

      {/* 右侧操作区 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div
          style={{
            position: 'relative',
          }}
        >
          <Input
            prefix={<SearchOutlined style={{ color: colors.textTertiary }} />}
            placeholder="搜索股票/代码..."
            style={{
              width: '220px',
              background: colors.bgCard,
              border: `1px solid ${colors.borderColor}`,
              borderRadius: '10px',
            }}
            size="middle"
          />
        </div>

        <Badge count={3} size="small">
          <BellOutlined 
            style={{ 
              fontSize: '20px', 
              color: colors.textSecondary, 
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }} 
            onMouseEnter={(e) => {
              e.currentTarget.style.color = colors.accentBlue;
              e.currentTarget.style.transform = 'scale(1.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = colors.textSecondary;
              e.currentTarget.style.transform = 'scale(1)';
            }}
          />
        </Badge>

        {/* 主题切换 */}
        <Space style={{ gap: '8px', alignItems: 'center' }}>
          {theme === 'dark' ? (
            <MoonOutlined style={{ color: colors.textSecondary, fontSize: '18px' }} />
          ) : (
            <SunOutlined style={{ color: colors.textSecondary, fontSize: '18px' }} />
          )}
          <Switch
            checked={theme === 'light'}
            onChange={toggleTheme}
            size="small"
            style={{
              background: theme === 'dark' ? 'linear-gradient(135deg, #56A4FF 0%, #514EBD 100%)' : undefined,
            }}
          />
        </Space>

        <Avatar
          size={36}
          style={{
            background: 'linear-gradient(135deg, #56A4FF 0%, #546ACF 50%, #514EBD 100%)',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(86, 164, 255, 0.3)',
            transition: 'all 0.3s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(86, 164, 255, 0.4)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(86, 164, 255, 0.3)';
          }}
        >
          CF
        </Avatar>
      </div>
    </div>
  );
};

export default Header;
