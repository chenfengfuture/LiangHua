import React from 'react';
import { Typography } from 'antd';
import {
  LineChartOutlined,
  SearchOutlined,
  DollarOutlined,
  TrophyOutlined,
  BankOutlined,
  AppstoreOutlined,
  FireOutlined,
  AimOutlined,
  DashboardOutlined,
  RiseOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useTheme } from '../../themes';

const { Text } = Typography;

interface SidebarProps {
  activeKey?: string;
  onChange?: (key: string) => void;
}

interface MenuItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  color?: string;
}

interface MenuGroup {
  title?: string;
  items: MenuItem[];
}

const Sidebar: React.FC<SidebarProps> = ({ activeKey = 'dashboard', onChange }) => {
  const { colors, theme } = useTheme();

  const menuGroups: MenuGroup[] = [
    {
      title: '概览',
      items: [
        { key: 'dashboard', label: '总览仪表盘', icon: <DashboardOutlined />, color: '#56A4FF' },
        { key: 'stock', label: '个股中心', icon: <SearchOutlined />, color: '#ACA9CC' },
        { key: 'abnormal-monitor', label: '异动监控', icon: <WarningOutlined />, color: '#ff4d4f' },
        { key: 'kline', label: '行情与 K 线', icon: <LineChartOutlined />, color: '#ff4d4f' },
        { key: 'core-dynamics', label: '核心动态', icon: <RiseOutlined />, color: '#ff4d4f' },
      ],
    },
    {
      title: '资金与龙虎榜',
      items: [
        { key: 'fund-flow', label: '资金流向', icon: <DollarOutlined />, color: '#F59E0B' },
        { key: 'dragon-tiger', label: '龙虎榜', icon: <TrophyOutlined />, color: '#10B981' },
        { key: 'margin-trade', label: '融资融券', icon: <BankOutlined />, color: '#ACA9CC' },
      ],
    },
    {
      title: '板块·涵股决策',
      items: [
        { key: 'sector', label: '行业 / 概念板块', icon: <AppstoreOutlined />, color: '#10B981' },
        { key: 'limit-up', label: '涨停池', icon: <FireOutlined />, color: '#ff4d4f' },
        { key: 'tech-select', label: '技术选股', icon: <AimOutlined />, color: '#EF4444' },
      ],
    },
  ];

  return (
    <div
      style={{
        width: '180px',
        height: 'calc(100vh - 60px)',
        background: colors.bgSecondary,
        borderRight: `1px solid ${colors.borderColor}`,
        padding: '16px 12px',
        position: 'sticky',
        top: '60px',
        overflowY: 'auto',
        flexShrink: 0,
      }}
    >
      {menuGroups.map((group, gIdx) => (
        <div key={gIdx} style={{ marginBottom: '20px' }}>
          {group.title && (
            <Text
              style={{
                color: colors.textTertiary,
                fontSize: '11px',
                fontWeight: 500,
                display: 'block',
                padding: '0 12px 8px',
                letterSpacing: '0.5px',
              }}
            >
              {group.title}
            </Text>
          )}
          {group.items.map((item) => {
            const isActive = activeKey === item.key;
            return (
              <div
                key={item.key}
                onClick={() => onChange?.(item.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '9px 12px',
                  marginBottom: '2px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: isActive
                    ? theme === 'dark'
                      ? 'linear-gradient(135deg, rgba(86, 164, 255, 0.15) 0%, rgba(81, 78, 189, 0.15) 100%)'
                      : 'linear-gradient(135deg, rgba(86, 164, 255, 0.1) 0%, rgba(81, 78, 189, 0.1) 100%)'
                    : 'transparent',
                  border: `1px solid ${isActive ? 'rgba(86, 164, 255, 0.3)' : 'transparent'}`,
                  transition: 'all 0.2s ease',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = colors.hoverBg;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                {isActive && (
                  <div
                    style={{
                      position: 'absolute',
                      left: '-12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      width: '3px',
                      height: '20px',
                      background: 'linear-gradient(180deg, #56A4FF 0%, #514EBD 100%)',
                      borderRadius: '0 2px 2px 0',
                    }}
                  />
                )}
                <span
                  style={{
                    color: isActive ? item.color : item.color,
                    fontSize: '15px',
                    opacity: isActive ? 1 : 0.85,
                  }}
                >
                  {item.icon}
                </span>
                <Text
                  style={{
                    color: isActive ? colors.textPrimary : colors.textSecondary,
                    fontSize: '13px',
                    fontWeight: isActive ? 600 : 500,
                  }}
                >
                  {item.label}
                </Text>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export default Sidebar;
