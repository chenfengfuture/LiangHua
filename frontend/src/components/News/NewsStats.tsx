import React, { useState, useEffect } from 'react';
import { Row, Col, Statistic, Typography, Space, Spin, Button, Tooltip } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import SentimentTrend from './SentimentTrend';
import SectorSentimentTop from './SectorSentimentTop';
import {
  RiseOutlined,
  FallOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  FireOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import type { NewsStats as NewsStatsType } from '../../types/news';
import { newsService } from '@/api/news';

const { Text } = Typography;

interface NewsStatsProps {
  /** 外部触发的刷新版本号，变化时重新拉取数据 */
  refreshKey?: number;
}

const COLLAPSE_KEY = 'news_analytics_collapsed';

const NewsStats: React.FC<NewsStatsProps> = ({ refreshKey = 0 }) => {
  const { colors } = useTheme();
  const [newsStats, setNewsStats] = useState<NewsStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === '1';
    } catch {
      return false;
    }
  });

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const stats = await newsService.fetchNewsStats();
        if (mounted) setNewsStats(stats);
      } catch {
        if (mounted) setNewsStats(null);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [refreshKey]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin description="加载新闻统计..." />
      </div>
    );
  }

  if (!newsStats || newsStats.totalToday === 0) {
    return (
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <DashboardCard padding={16}>
            <Text style={{ color: colors.textTertiary }}>暂无新闻数据，请稍后再试</Text>
          </DashboardCard>
        </Col>
      </Row>
    );
  }

  // 情感分布数据
  const sentimentData = [
    { name: '利好', value: newsStats.positive, color: '#ff4d4f', icon: <RiseOutlined /> },
    { name: '中性', value: newsStats.neutral, color: '#faad14', icon: <InfoCircleOutlined /> },
    { name: '利空', value: newsStats.negative, color: '#52c41a', icon: <FallOutlined /> },
  ];

  // 折叠按钮：放在三模块上方的右侧
  const collapseBar = (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 4px 2px',
      }}
    >
      <Space size={6}>
        <Text style={{ color: colors.textSecondary, fontSize: 13, fontWeight: 500 }}>
          舆情分析面板
        </Text>
        <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
          情感分布 · 板块情绪热度 · 情绪分析
        </Text>
      </Space>
      <Tooltip title={collapsed ? '展开三模块' : '折叠三模块'}>
        <Button
          type="text"
          size="small"
          icon={collapsed ? <DownOutlined /> : <UpOutlined />}
          onClick={toggleCollapsed}
          style={{ color: colors.textSecondary }}
        >
          {collapsed ? '展开' : '折叠'}
        </Button>
      </Tooltip>
    </div>
  );

  return (
    <Row gutter={[16, 12]}>
      {/* 顶部 4 个总览统计 */}
      <Col xs={24} sm={12} lg={6}>
        <DashboardCard padding={16}>
          <Statistic
            title={
              <Space>
                <FileTextOutlined style={{ color: '#56a4ff' }} />
                <Text style={{ color: colors.textSecondary }}>今日新闻</Text>
              </Space>
            }
            value={newsStats.totalToday}
            styles={{ content: { color: colors.textPrimary, fontSize: '32px', fontWeight: 600 } }}
            suffix={<Text style={{ fontSize: '14px', color: colors.textTertiary }}>条</Text>}
            prefix={<Text style={{ color: '#52c41a', fontSize: '16px' }}>+12.5%</Text>}
          />
        </DashboardCard>
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <DashboardCard padding={16}>
          <Statistic
            title={
              <Space>
                <FireOutlined style={{ color: '#ff4d4f' }} />
                <Text style={{ color: colors.textSecondary }}>重大影响</Text>
              </Space>
            }
            value={newsStats.highImpact}
            styles={{ content: { color: '#ff4d4f', fontSize: '32px', fontWeight: 600 } }}
            suffix={<Text style={{ fontSize: '14px', color: colors.textTertiary }}>条</Text>}
            prefix={
              <Text style={{ color: '#ff4d4f', fontSize: '14px' }}>
                {((newsStats.highImpact / newsStats.totalToday) * 100).toFixed(1)}%
              </Text>
            }
          />
        </DashboardCard>
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <DashboardCard padding={16}>
          <Statistic
            title={
              <Space>
                <RiseOutlined style={{ color: '#ff4d4f' }} />
                <Text style={{ color: colors.textSecondary }}>利好新闻</Text>
              </Space>
            }
            value={newsStats.positive}
            styles={{ content: { color: '#ff4d4f', fontSize: '32px', fontWeight: 600 } }}
            suffix={<Text style={{ fontSize: '14px', color: colors.textTertiary }}>条</Text>}
            prefix={
              <Text style={{ color: '#ff4d4f', fontSize: '14px' }}>
                {((newsStats.positive / newsStats.totalToday) * 100).toFixed(1)}%
              </Text>
            }
          />
        </DashboardCard>
      </Col>

      <Col xs={24} sm={12} lg={6}>
        <DashboardCard padding={16}>
          <Statistic
            title={
              <Space>
                <FallOutlined style={{ color: '#52c41a' }} />
                <Text style={{ color: colors.textSecondary }}>利空新闻</Text>
              </Space>
            }
            value={newsStats.negative}
            styles={{ content: { color: '#52c41a', fontSize: '32px', fontWeight: 600 } }}
            suffix={<Text style={{ fontSize: '14px', color: colors.textTertiary }}>条</Text>}
            prefix={
              <Text style={{ color: '#52c41a', fontSize: '14px' }}>
                {((newsStats.negative / newsStats.totalToday) * 100).toFixed(1)}%
              </Text>
            }
          />
        </DashboardCard>
      </Col>

      {/* 折叠控制条 */}
      <Col span={24}>{collapseBar}</Col>

      {/* 三模块并排：情感分布 | 板块情绪热度 TOP | 情绪分析 */}
      {!collapsed && (
        <>
          <Col xs={24} md={24} lg={7}>
            <DashboardCard title="情感分布" padding={12} height="100%">
              <Row gutter={[8, 8]} align="middle" style={{ height: '100%' }}>
                {sentimentData.map((item) => {
                  const percent = Math.round((item.value / newsStats.totalToday) * 100);
                  return (
                    <Col xs={8} key={item.name}>
                      <div style={{ textAlign: 'center' }}>
                        <div
                          style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: `${item.color}20`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 4px',
                            border: `2px solid ${item.color}40`,
                          }}
                        >
                          <span style={{ color: item.color, fontSize: '16px' }}>{item.icon}</span>
                        </div>
                        <Text style={{ color: colors.textSecondary, display: 'block', marginBottom: '2px', fontSize: '12px' }}>
                          {item.name}
                        </Text>
                        <Text style={{ color: item.color, fontSize: '18px', fontWeight: 600, display: 'block', lineHeight: 1.1 }}>
                          {percent}%
                        </Text>
                        <Text style={{ color: colors.textTertiary, fontSize: '11px' }}>
                          {item.value} 条
                        </Text>
                      </div>
                    </Col>
                  );
                })}
              </Row>
            </DashboardCard>
          </Col>

          <Col xs={24} md={12} lg={7}>
            <SectorSentimentTop refreshKey={refreshKey} />
          </Col>

          <Col xs={24} md={12} lg={10}>
            <SentimentTrend refreshKey={refreshKey} />
          </Col>
        </>
      )}
    </Row>
  );
};

export default React.memo(NewsStats);
