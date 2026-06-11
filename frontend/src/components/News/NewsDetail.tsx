import React from 'react';
import { Modal, Typography, Tag, Space, Divider, Row, Col, Descriptions, Button } from 'antd';
import { 
  RiseOutlined, 
  FallOutlined, 
  InfoCircleOutlined,
  FireOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  FundOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useTheme } from '../../themes';
import type { NewsItem, NewsSection } from '../../types/news';
import { NEWS_SECTION_NAMES } from '../../types/news';
import dayjs from 'dayjs';

const { Text, Title, Paragraph } = Typography;

interface NewsDetailProps {
  visible: boolean;
  news: NewsItem | null;
  onClose: () => void;
}

const NewsDetail: React.FC<NewsDetailProps> = ({ visible, news, onClose }) => {
  const { colors } = useTheme();

  if (!news) return null;

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

  // 获取情感文本
  const getSentimentText = (sentimentLabel?: number) => {
    switch (sentimentLabel) {
      case 1:
        return '利好';
      case -1:
        return '利空';
      default:
        return '中性';
    }
  };

  // 获取影响等级
  const getImpactLevelText = (level?: number) => {
    const texts = ['轻微', '一般', '中等', '较大', '重大'];
    return level ? texts[level - 1] : '未知';
  };

  // 获取事件类型图标
  const getEventTypeIcon = (type?: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      '财报': <BarChartOutlined />,
      '并购': <FundOutlined />,
      '政策': <SafetyCertificateOutlined />,
      '研发': <FileTextOutlined />,
    };
    return iconMap[type || ''] || <InfoCircleOutlined />;
  };

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined style={{ color: '#56a4ff' }} />
          <Text style={{ color: colors.textPrimary, fontSize: '16px', fontWeight: 600 }}>
            新闻详情
          </Text>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Button 
            type="primary" 
            icon={<LinkOutlined />}
            onClick={() => window.open(news.url, '_blank')}
          >
            查看原文
          </Button>
        </Space>
      }
      width={800}
      styles={{
        body: { padding: '24px' },
        mask: { backdropFilter: 'blur(4px)' },
      }}
    >
      {/* 新闻标题 */}
      <div style={{ marginBottom: '20px' }}>
        <Title level={4} style={{ color: colors.textPrimary, marginBottom: '12px', lineHeight: '1.5' }}>
          {news.title}
        </Title>
        
        <Space wrap size="small">
          {/* 板块标签 */}
          <Tag color="blue" icon={<FileTextOutlined />}>
            {NEWS_SECTION_NAMES[news.news_type]}
          </Tag>
          
          {/* 情感标签 */}
          <Tag 
            color={news.sentiment_label === 1 ? 'red' : news.sentiment_label === -1 ? 'green' : 'gold'}
            icon={news.sentiment_label === 1 ? <RiseOutlined /> : news.sentiment_label === -1 ? <FallOutlined /> : <InfoCircleOutlined />}
          >
            {getSentimentText(news.sentiment_label)}
            {news.sentiment !== undefined && ` (${news.sentiment >= 0 ? '+' : ''}${(news.sentiment * 100).toFixed(1)}%)`}
          </Tag>

          {/* 影响等级 */}
          <Tag 
            icon={<FireOutlined />}
            color={news.ai_impact_level && news.ai_impact_level >= 4 ? 'red' : 'orange'}
          >
            {getImpactLevelText(news.ai_impact_level)}影响
          </Tag>

          {/* 突发/官方标签 */}
          {news.is_breaking === 1 && (
            <Tag color="red" icon={<ThunderboltOutlined />}>突发新闻</Tag>
          )}
          {news.is_official === 1 && (
            <Tag color="blue" icon={<SafetyCertificateOutlined />}>官方公告</Tag>
          )}

          {/* 事件类型 */}
          {news.ai_event_type && (
            <Tag color="purple" icon={getEventTypeIcon(news.ai_event_type)}>
              {news.ai_event_type}
            </Tag>
          )}
        </Space>
      </div>

      <Divider style={{ margin: '16px 0', borderColor: colors.borderColor }} />

      {/* 新闻内容 */}
      <div style={{ marginBottom: '24px' }}>
        <Text style={{ color: colors.textSecondary, fontSize: '13px', display: 'block', marginBottom: '8px' }}>
          新闻内容
        </Text>
        <Paragraph style={{ color: colors.textPrimary, fontSize: '14px', lineHeight: '1.8' }}>
          {news.content}
        </Paragraph>
      </div>

      {/* AI分析解读 */}
      {news.ai_interpretation && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, rgba(86,164,255,0.1) 0%, rgba(81,78,189,0.1) 100%)',
            border: '1px solid rgba(86,164,255,0.2)',
          }}>
            <Text style={{ color: '#56a4ff', fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              <FileTextOutlined style={{ marginRight: '6px' }} />
              AI智能解读
            </Text>
            <Paragraph style={{ color: colors.textPrimary, marginBottom: 0, fontSize: '14px', lineHeight: '1.7' }}>
              {news.ai_interpretation}
            </Paragraph>
          </div>
        </div>
      )}

      {/* 受益板块和个股 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {news.ai_benefit_sectors && (
          <Col xs={24} sm={12}>
            <div style={{
              padding: '16px',
              borderRadius: '8px',
              background: colors.bgSecondary,
              border: `1px solid ${colors.borderColor}`,
              height: '100%',
            }}>
              <Text style={{ color: colors.textSecondary, fontSize: '13px', display: 'block', marginBottom: '10px' }}>
                <FundOutlined style={{ color: '#722ed1', marginRight: '6px' }} />
                受益板块
              </Text>
              <Space wrap size="small">
                {news.ai_benefit_sectors.split(',').map((sector, idx) => (
                  <Tag key={idx} color="purple" style={{ margin: 0 }}>
                    {sector.trim()}
                  </Tag>
                ))}
              </Space>
            </div>
          </Col>
        )}

        {news.ai_benefit_stocks && (
          <Col xs={24} sm={12}>
            <div style={{
              padding: '16px',
              borderRadius: '8px',
              background: colors.bgSecondary,
              border: `1px solid ${colors.borderColor}`,
              height: '100%',
            }}>
              <Text style={{ color: colors.textSecondary, fontSize: '13px', display: 'block', marginBottom: '10px' }}>
                <BarChartOutlined style={{ color: '#52c41a', marginRight: '6px' }} />
                受益个股
              </Text>
              <Space wrap size="small">
                {news.ai_benefit_stocks.split(',').map((stock, idx) => (
                  <Tag key={idx} color="green" style={{ margin: 0 }}>
                    {stock.trim()}
                  </Tag>
                ))}
              </Space>
            </div>
          </Col>
        )}
      </Row>

      {/* 关键词 */}
      {news.ai_keywords && (
        <div style={{ marginBottom: '24px' }}>
          <Text style={{ color: colors.textSecondary, fontSize: '13px', display: 'block', marginBottom: '10px' }}>
            关键词标签
          </Text>
          <Space wrap size="small">
            {news.ai_keywords.split(',').map((keyword, idx) => (
              <Tag key={idx} style={{ margin: 0 }}>
                {keyword.trim()}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      <Divider style={{ margin: '16px 0', borderColor: colors.borderColor }} />

      {/* 元信息 */}
      <Descriptions 
        column={2} 
        size="small"
        labelStyle={{ color: colors.textTertiary, width: '80px' }}
        contentStyle={{ color: colors.textPrimary }}
      >
        <Descriptions.Item label="来源">
          {news.source}
        </Descriptions.Item>
        <Descriptions.Item label="来源分类">
          {news.source_category}
        </Descriptions.Item>
        <Descriptions.Item label="发布时间">
          <ClockCircleOutlined style={{ marginRight: '4px' }} />
          {dayjs(news.publish_time).format('YYYY-MM-DD HH:mm:ss')}
        </Descriptions.Item>
        <Descriptions.Item label="采集时间">
          {news.collect_time ? dayjs(news.collect_time).format('YYYY-MM-DD HH:mm:ss') : '-'}
        </Descriptions.Item>
        {news.ai_analyze_time && (
          <>
            <Descriptions.Item label="AI分析时间">
              {dayjs(news.ai_analyze_time).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="数据来源">
              {news._source === 'redis' ? '实时缓存' : '数据库'}
            </Descriptions.Item>
          </>
        )}
      </Descriptions>
    </Modal>
  );
};

export default NewsDetail;
