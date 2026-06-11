import React, { useState, useCallback } from 'react';
import { message } from 'antd';
import NewsStats from './NewsStats';
import NewsList from './NewsList';
import { useNewsWebSocket } from '../../hooks/useNewsWebSocket';

const NewsDashboard: React.FC = () => {
  const [statsRefreshKey, setStatsRefreshKey] = useState(0);
  const [listRefreshKey, setListRefreshKey] = useState(0);

  const handleNewsCollected = useCallback(() => {
    setStatsRefreshKey(k => k + 1);
    setListRefreshKey(k => k + 1);
    message.info('收到新新闻，自动刷新中...');
  }, []);

  // 初始化 WebSocket 实时推送
  useNewsWebSocket({
    onNewsCollected: handleNewsCollected,
  });

  return (
    <div style={{ padding: '0 8px' }}>
      {/* 新闻统计卡片（含情绪分析和情感分布） */}
      <div style={{ marginBottom: '20px' }}>
        <NewsStats refreshKey={statsRefreshKey} />
      </div>

      {/* 新闻中心 */}
      <NewsList refreshKey={listRefreshKey} />
    </div>
  );
};

export default NewsDashboard;
