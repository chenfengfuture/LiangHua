import React, { useState, useEffect } from 'react';
import { Tag, Typography, Avatar, Space, Button, Divider, Spin } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import NewsDetail from './NewsDetail';
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  FireOutlined, 
  SafetyCertificateOutlined,
  RiseOutlined, 
  FallOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import type { NewsItem, NewsSection } from '../../types/news';
import { NEWS_SECTION_NAMES } from '../../types/news';
import { newsService } from '@/api/news';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;

interface NewsListProps {
  /** 外部触发的刷新版本号，变化时重新拉取数据（不重置筛选状态） */
  refreshKey?: number;
}

const NewsList: React.FC<NewsListProps> = ({ refreshKey: externalRefreshKey = 0 }) => {
  const { colors } = useTheme();
  const [selectedSection, setSelectedSection] = useState<NewsSection | 'all'>('all');
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null);
  const [allNews, setAllNews] = useState<NewsItem[]>([]);
  const [filteredNews, setFilteredNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<'all' | 'breaking' | 'official' | 'highImpact'>('all');

  const [localRefreshKey, setLocalRefreshKey] = useState(0);

  const loadNews = async () => {
    setLoading(true);
    try {
      const items = await newsService.getAllNews();
      setAllNews([...items]);
    } catch {
      setAllNews([]);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载 + 本地刷新（不会被筛选变化触发，因为筛选不再改 refreshKey）
  useEffect(() => {
    loadNews();
  }, [localRefreshKey]);

  // 外部 WebSocket 推送：重新拉取数据，但保留筛选/分类状态
  useEffect(() => {
    if (externalRefreshKey > 0) {
      loadNews();
    }
  }, [externalRefreshKey]);

  // 筛选变化时：仅修改筛选状态，不重新请求数据（数据已经在内存中）
  const handleFilterChange = (filter: 'all' | 'breaking' | 'official' | 'highImpact') => {
    setActiveFilter(filter);
  };

  const handleSectionChange = (section: NewsSection | 'all') => {
    setSelectedSection(section);
  };

  // allNews 变化时重新计算筛选
  useEffect(() => {
    let news = [...allNews];
    if (selectedSection !== 'all') {
      news = news.filter(n => n.news_type === selectedSection);
    }
    if (activeFilter === 'breaking') {
      news = news.filter(n => n.is_breaking === 1);
    } else if (activeFilter === 'official') {
      news = news.filter(n => n.is_official === 1);
    } else if (activeFilter === 'highImpact') {
      news = news.filter(n => (n.ai_impact_level || 0) >= 4);
    }
    news.sort((a, b) => dayjs(b.publish_time).valueOf() - dayjs(a.publish_time).valueOf());
    setFilteredNews(news);
  }, [allNews, selectedSection, activeFilter]);

  // 获取情感图标
  const getSentimentIcon = (sentimentLabel?: number) => {
    switch (sentimentLabel) {
      case 1:
        return <RiseOutlined style={{ color: '#ff4d4f' }} />;
      case -1:
        return <FallOutlined style={{ color: '#52c41a' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  // 获取情感颜色
  const getSentimentColor = (sentimentLabel?: number) => {
    switch (sentimentLabel) {
      case 1:
        return '#ff4d4f';
      case -1:
        return '#52c41a';
      default:
        return '#faad14';
    }
  };

  // 获取情感标签
  const getSentimentTag = (sentimentLabel?: number) => {
    switch (sentimentLabel) {
      case 1:
        return <Tag color="red" icon={<RiseOutlined />}>利好</Tag>;
      case -1:
        return <Tag color="green" icon={<FallOutlined />}>利空</Tag>;
      default:
        return <Tag color="gold" icon={<InfoCircleOutlined />}>中性</Tag>;
    }
  };

  // 获取影响等级标签
  const getImpactLevelTag = (level?: number) => {
    if (!level) return null;
    const colors = ['blue', 'cyan', 'orange', 'orange', 'red'];
    const texts = ['轻微', '一般', '中等', '较大', '重大'];
    return (
      <Tag color={colors[level - 1]} style={{ margin: 0 }}>
        {texts[level - 1]}影响
      </Tag>
    );
  };

  // 获取新闻卡片背景色（基于情感）
  const getCardBgColor = (sentimentLabel?: number) => {
    switch (sentimentLabel) {
      case 1:
        return 'rgba(255,77,79,0.03)';
      case -1:
        return 'rgba(82,196,26,0.03)';
      default:
        return 'transparent';
    }
  };

  return (
    <DashboardCard 
      title="新闻中心" 
      subtitle="AI驱动的智能新闻分析系统"
      extra={
        <Space wrap size="small">
          <Button 
            type={selectedSection === 'all' ? 'primary' : 'text'}
            size="small"
            onClick={() => handleSectionChange('all')}
          >
            全部
          </Button>
          {(Object.keys(NEWS_SECTION_NAMES) as NewsSection[]).map(section => (
            <Button 
              key={section}
              type={selectedSection === section ? 'primary' : 'text'}
              size="small"
              onClick={() => handleSectionChange(section)}
            >
              {NEWS_SECTION_NAMES[section]}
            </Button>
          ))}
          <Divider orientation="vertical" />
          <Button
            icon={<ReloadOutlined />}
            size="small"
            onClick={() => setLocalRefreshKey(k => k + 1)}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin description="加载新闻数据..." />
        </div>
      ) : (
        <>
      {/* 快速统计栏 — 点击分类筛选 */}
      <div style={{ display: 'flex', gap: '16px', padding: '12px 0', borderBottom: `1px solid ${colors.borderColor}`, marginBottom: '12px', alignItems: 'center' }}>
        <Space size={12}>
          <Button
            icon={<ThunderboltOutlined />}
            size="small"
            danger={activeFilter === 'breaking'}
            type={activeFilter === 'breaking' ? 'primary' : 'default'}
            onClick={() => handleFilterChange(activeFilter === 'breaking' ? 'all' : 'breaking')}
          >
            突发 ({allNews.filter(n => n.is_breaking === 1).length})
          </Button>
          <Button
            icon={<SafetyCertificateOutlined />}
            size="small"
            type={activeFilter === 'official' ? 'primary' : 'default'}
            onClick={() => handleFilterChange(activeFilter === 'official' ? 'all' : 'official')}
          >
            官方 ({allNews.filter(n => n.is_official === 1).length})
          </Button>
          <Button
            icon={<FireOutlined />}
            size="small"
            danger={activeFilter === 'highImpact'}
            type={activeFilter === 'highImpact' ? 'primary' : 'default'}
            onClick={() => handleFilterChange(activeFilter === 'highImpact' ? 'all' : 'highImpact')}
          >
            重大影响 ({allNews.filter(n => (n.ai_impact_level || 0) >= 4).length})
          </Button>
        </Space>
        <Text style={{ color: colors.textTertiary, marginLeft: 'auto' }}>
          共 {filteredNews.length} 条新闻
        </Text>
      </div>

      <div style={{ maxHeight: '600px', overflow: 'auto' }}>
        {filteredNews.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text style={{ color: colors.textTertiary }}>暂无符合条件的新闻</Text>
          </div>
        ) : (
          filteredNews.map((item) => (
            <div
              key={item.id}
              style={{
                padding: '16px 12px',
                borderBottom: `1px solid ${colors.borderColor}`,
                background: getCardBgColor(item.sentiment_label),
                borderRadius: '8px',
                marginBottom: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = colors.hoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = getCardBgColor(item.sentiment_label);
              }}
              onClick={() => setSelectedNews(item)}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  {/* 情感图标 */}
                  <Avatar
                    size={48}
                    style={{
                      background: item.sentiment_label === 1 
                        ? 'rgba(255,77,79,0.15)' 
                        : item.sentiment_label === -1 
                          ? 'rgba(82,196,26,0.15)' 
                          : 'rgba(250,173,20,0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      border: `1px solid ${getSentimentColor(item.sentiment_label)}30`,
                    }}
                  >
                    {getSentimentIcon(item.sentiment_label)}
                  </Avatar>

                  {/* 主内容 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* 标题和标签 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                      {item.is_breaking === 1 && (
                        <Tag icon={<ThunderboltOutlined />} color="red" style={{ margin: 0 }}>
                          突发
                        </Tag>
                      )}
                      {item.is_official === 1 && (
                        <Tag icon={<SafetyCertificateOutlined />} color="blue" style={{ margin: 0 }}>
                          官方
                        </Tag>
                      )}
                      {getImpactLevelTag(item.ai_impact_level)}
                      <Text
                        style={{
                          color: colors.textPrimary,
                          fontWeight: 500,
                          fontSize: '15px',
                          lineHeight: '1.5',
                        }}
                      >
                        {item.title}
                      </Text>
                    </div>

                    {/* AI解读 */}
                    {item.ai_interpretation && (
                      <Paragraph
                        style={{
                          color: colors.textSecondary,
                          fontSize: '13px',
                          marginBottom: '10px',
                          padding: '8px 12px',
                          background: 'rgba(86,164,255,0.05)',
                          borderRadius: '6px',
                          borderLeft: '3px solid #56a4ff',
                        }}
                        ellipsis={{ rows: 2, expandable: false }}
                      >
                        <FileTextOutlined style={{ marginRight: '6px', color: '#56a4ff' }} />
                        <Text style={{ color: '#56a4ff', fontWeight: 500, marginRight: '4px' }}>
                          AI解读：
                        </Text>
                        {item.ai_interpretation}
                      </Paragraph>
                    )}

                    {/* 元信息和标签 */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <Space size="small" wrap>
                        {/* 来源和时间 */}
                        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                          {item.source}
                        </Text>
                        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>|</Text>
                        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                          {dayjs(item.publish_time).format('HH:mm')}
                        </Text>
                        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>|</Text>
                        <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                          {NEWS_SECTION_NAMES[item.news_type]}
                        </Text>
                      </Space>

                      <Space size="small" wrap>
                        {/* 受益板块标签 */}
                        {item.ai_benefit_sectors && item.ai_benefit_sectors.split(',').slice(0, 3).map((sector, idx) => (
                          <Tag key={idx} color="purple" style={{ margin: 0, fontSize: '11px', padding: '0 6px' }}>
                            {sector}
                          </Tag>
                        ))}
                        
                        {/* 情感标签 */}
                        {getSentimentTag(item.sentiment_label)}

                        {/* 查看详情按钮 */}
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<EyeOutlined />}
                          style={{ color: '#56a4ff', fontSize: '12px' }}
                        >
                          详情
                        </Button>
                      </Space>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      </>
      )}

      {/* 新闻详情弹窗 */}
      <NewsDetail
        visible={selectedNews !== null}
        news={selectedNews}
        onClose={() => setSelectedNews(null)}
      />
    </DashboardCard>
  );
};

export default React.memo(NewsList);
