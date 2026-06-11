import React, { useEffect, useState } from 'react';
import { Typography, Space, Tag, Spin } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import { RiseOutlined, FallOutlined } from '@ant-design/icons';
import { useTheme } from '@/themes';
import { newsService } from '@/api/news';
import type { NewsItem } from '../../types/news';

const { Text } = Typography;

interface SectorSentimentTopProps {
  /** 外部触发的刷新版本号，变化时重新拉取数据 */
  refreshKey?: number;
}

const SectorSentimentTop: React.FC<SectorSentimentTopProps> = ({ refreshKey = 0 }) => {
  const { colors } = useTheme();
  const [allNews, setAllNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const items = await newsService.getAllNews();
        if (mounted) setAllNews(items);
      } catch {
        if (mounted) setAllNews([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [refreshKey]);

  // 板块情感排行
  const sectorSentiment = React.useMemo(() => {
    const sectors: Record<string, { positive: number; negative: number; total: number }> = {};

    allNews.forEach(news => {
      if (news.ai_benefit_sectors) {
        news.ai_benefit_sectors.split(',').forEach(sector => {
          const s = sector.trim();
          if (!s) return;
          if (!sectors[s]) {
            sectors[s] = { positive: 0, negative: 0, total: 0 };
          }
          sectors[s].total++;
          if (news.sentiment_label === 1) sectors[s].positive++;
          if (news.sentiment_label === -1) sectors[s].negative++;
        });
      }
    });

    return Object.entries(sectors)
      .map(([name, data]) => ({
        name,
        score: data.total > 0 ? ((data.positive - data.negative) / data.total * 100).toFixed(1) : '0',
        total: data.total,
      }))
      .sort((a, b) => parseFloat(b.score) - parseFloat(a.score))
      .slice(0, 6);
  }, [allNews]);

  return (
    <DashboardCard title="板块情绪热度" subtitle="TOP 板块情绪指数" padding={10}>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin description="加载板块情绪..." />
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={4}>
          {sectorSentiment.length > 0 ? sectorSentiment.map((item) => (
            <div
              key={item.name}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 10px',
                borderRadius: '5px',
                background: colors.bgSecondary,
                border: `1px solid ${colors.borderColor}`,
              }}
            >
              <Space size="small" style={{ minWidth: 0, flex: 1 }}>
                <Tag
                  color={parseFloat(item.score) >= 0 ? 'red' : 'green'}
                  style={{ margin: 0, minWidth: '58px', textAlign: 'center', fontSize: '11px' }}
                >
                  {parseFloat(item.score) >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  {parseFloat(item.score) >= 0 ? '+' : ''}{item.score}
                </Tag>
                <Text
                  style={{
                    color: colors.textPrimary,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontSize: '13px',
                  }}
                  title={item.name}
                >
                  {item.name}
                </Text>
              </Space>
              <Text style={{ color: colors.textTertiary, fontSize: '11px', flexShrink: 0 }}>
                {item.total}条
              </Text>
            </div>
          )) : (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Text style={{ color: colors.textTertiary, fontSize: '12px' }}>
                暂无板块情绪数据
              </Text>
            </div>
          )}
        </Space>
      )}
    </DashboardCard>
  );
};

export default SectorSentimentTop;
