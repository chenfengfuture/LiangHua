/**
 * useNewsWebSocket — WebSocket 新闻实时推送 Hook
 *
 * 连接后端 /ws 端点，订阅 news 频道，
 * 收到 news_collected 事件后触发刷新回调。
 *
 * 使用方式：
 *   useNewsWebSocket({ onNewsCollected: () => loadNews() });
 */

import { useEffect, useRef, useCallback } from 'react';

type WSOptions = {
  /** 收到新新闻采集完成时的回调 */
  onNewsCollected?: () => void;
  /** 收到单条新闻分析完成时的回调 */
  onNewsUpdate?: (newsId: number, data: any) => void;
  /** 连接状态变化回调 */
  onStatusChange?: (connected: boolean) => void;
};

export function useNewsWebSocket(options: WSOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const isMounted = useRef(true);

  // 用 ref 存储回调，避免 useCallback 因回调变化导致重连
  const callbacksRef = useRef<WSOptions>({});
  callbacksRef.current = options;

  const connect = useCallback(() => {
    const url = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws';
    const ws = new WebSocket(url);

    ws.onopen = () => {
      if (import.meta.env.DEV) console.log('[WS] 已连接');
      callbacksRef.current.onStatusChange?.(true);

      // 订阅 news 频道
      ws.send(JSON.stringify({ action: 'subscribe', channels: ['news'] }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'news_collected') {
          callbacksRef.current.onNewsCollected?.();
        } else if (msg.type === 'news_update' || msg.type === 'news_batch') {
          callbacksRef.current.onNewsUpdate?.(msg.news_id, msg.data);
        }
      } catch {
        // 忽略解析失败
      }
    };

    ws.onclose = () => {
      if (import.meta.env.DEV) console.log('[WS] 断开');
      callbacksRef.current.onStatusChange?.(false);

      // 自动重连（5秒后）
      if (isMounted.current) {
        reconnectTimer.current = setTimeout(() => {
          if (isMounted.current) connect();
        }, 5000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []); // 空依赖：只连接一次，回调通过 ref 获取最新值

  useEffect(() => {
    isMounted.current = true;
    connect();

    return () => {
      isMounted.current = false;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
