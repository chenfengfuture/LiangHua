import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Typography, Spin } from 'antd';
import DashboardCard from '../Common/DashboardCard';
import {
  InfoCircleOutlined,
  LineOutlined,
  CaretDownOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/themes';
import { newsService } from '@/api/news';
import type { NewsItem } from '../../types/news';
import dayjs from 'dayjs';

const { Text } = Typography;

interface SentimentTrendProps {
  /** 外部触发的刷新版本号，变化时重新拉取数据 */
  refreshKey?: number;
}

const SentimentTrend: React.FC<SentimentTrendProps> = ({ refreshKey = 0 }) => {
  const { theme, colors } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
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

  // 按小时统计情感趋势
  const trendData = React.useMemo(() => {
    const hours = Array.from({ length: 12 }, (_, i) => dayjs().subtract(11 - i, 'hour').format('HH:00'));
    const positive: number[] = [];
    const negative: number[] = [];
    const neutral: number[] = [];

    hours.forEach(hour => {
      const hourNews = allNews.filter(n =>
        dayjs(n.publish_time).format('HH:00') === hour
      );
      positive.push(hourNews.filter(n => n.sentiment_label === 1).length);
      negative.push(hourNews.filter(n => n.sentiment_label === -1).length);
      neutral.push(hourNews.filter(n => n.sentiment_label === 0).length);
    });

    return { hours, positive, negative, neutral };
  }, [allNews]);

  // 计算今日情绪指数
  const sentimentIndex = React.useMemo(() => {
    const positive = allNews.filter(n => n.sentiment_label === 1).length;
    const negative = allNews.filter(n => n.sentiment_label === -1).length;
    const total = allNews.length;
    return total > 0 ? ((positive - negative) / total * 100).toFixed(1) : '0';
  }, [allNews]);

  // 初始化图表
  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current, theme === 'dark' ? 'dark' : undefined);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: theme === 'dark' ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.9)',
        borderColor: 'rgba(86,164,255,0.3)',
        textStyle: { color: colors.textPrimary },
      },
      legend: {
        data: ['利好', '中性', '利空'],
        top: 0,
        right: 0,
        textStyle: { color: colors.textSecondary },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trendData.hours,
        axisLine: { lineStyle: { color: colors.borderColor } },
        axisLabel: { color: colors.textTertiary, fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: colors.textTertiary, fontSize: 11 },
        splitLine: { lineStyle: { color: colors.borderColor } },
      },
      series: [
        {
          name: '利好',
          type: 'line',
          smooth: true,
          data: trendData.positive,
          lineStyle: { color: '#ff4d4f', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(255,77,79,0.3)' },
              { offset: 1, color: 'rgba(255,77,79,0)' },
            ]),
          },
          itemStyle: { color: '#ff4d4f' },
        },
        {
          name: '中性',
          type: 'line',
          smooth: true,
          data: trendData.neutral,
          lineStyle: { color: '#faad14', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(250,173,20,0.2)' },
              { offset: 1, color: 'rgba(250,173,20,0)' },
            ]),
          },
          itemStyle: { color: '#faad14' },
        },
        {
          name: '利空',
          type: 'line',
          smooth: true,
          data: trendData.negative,
          lineStyle: { color: '#52c41a', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(82,196,26,0.2)' },
              { offset: 1, color: 'rgba(82,196,26,0)' },
            ]),
          },
          itemStyle: { color: '#52c41a' },
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, [trendData, theme, colors]);

  return (
    <DashboardCard title="情绪分析" subtitle="AI驱动的市场情绪指数" padding={12}>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin description="加载情绪数据..." />
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 10, alignItems: 'stretch', width: '100%' }}>
          {/* 左：今日情绪指数（紧凑） */}
          <div
            style={{
              flex: '0 0 110px',
              padding: '8px 6px',
              borderRadius: '8px',
              background: parseFloat(sentimentIndex) >= 0
                ? 'rgba(255,77,79,0.1)'
                : 'rgba(82,196,26,0.1)',
              border: `1px solid ${parseFloat(sentimentIndex) >= 0 ? 'rgba(255,77,79,0.3)' : 'rgba(82,196,26,0.3)'}`,
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
            }}
          >
            <Text style={{ color: colors.textSecondary, fontSize: '11px', display: 'block' }}>
              情绪指数
            </Text>
            <div style={{ fontSize: '22px', fontWeight: 700, color: parseFloat(sentimentIndex) >= 0 ? '#ff4d4f' : '#52c41a', lineHeight: 1.1, margin: '2px 0' }}>
              {parseFloat(sentimentIndex) >= 0 ? '+' : ''}{sentimentIndex}
            </div>
            <div style={{ fontSize: '11px', color: colors.textTertiary, lineHeight: 1.2 }}>
              {parseFloat(sentimentIndex) >= 20 ? (
                <><LineOutlined style={{ color: '#ff4d4f', marginRight: '2px' }} />乐观</>
              ) : parseFloat(sentimentIndex) <= -20 ? (
                <><CaretDownOutlined style={{ color: '#52c41a', marginRight: '2px' }} />谨慎</>
              ) : (
                <><InfoCircleOutlined style={{ color: '#faad14', marginRight: '2px' }} />平稳</>
              )}
            </div>
          </div>

          {/* 右：趋势图 */}
          <div ref={chartRef} style={{ height: '160px', flex: 1, minWidth: 0 }} />
        </div>
      )}
    </DashboardCard>
  );
};

export default SentimentTrend;
