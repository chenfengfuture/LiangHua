import { useEffect, useRef, useCallback, useState } from 'react'

/**
 * 新闻 WebSocket Hook V2
 *
 * 修复要点（2026-03-31）：
 * - connect() 不再依赖 isConnecting state，改用 isConnectingRef
 *   → 避免 state 变化触发 useEffect → 无限重建 WebSocket
 * - useEffect 依赖只有 [enabled, date]，不再依赖 connect/disconnect 函数
 * - 日期切换通过独立 useEffect 完成，不重建连接
 *
 * @param {Object} options
 * @param {string}   options.date        - 订阅日期 YYYY-MM-DD
 * @param {boolean}  options.enabled     - 是否启用
 * @param {Function} options.onMessage   - 消息回调 (message) => void
 * @param {Function} options.onConnect   - 连接成功回调
 * @param {Function} options.onDisconnect- 断开连接回调
 * @param {Function} options.onError     - 错误回调
 */
export function useNewsWebSocketV2(options = {}) {
  const { date, enabled = true, onMessage, onConnect, onDisconnect, onError } = options

  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)

  // 所有 mutable 状态用 ref，避免 closure 捕获旧值
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const pingTimerRef = useRef(null)
  const reconnectCountRef = useRef(0)
  const isMountedRef = useRef(true)
  const subscribedDateRef = useRef(null)
  const isConnectingRef = useRef(false)   // ← 替代 isConnecting state，供 connect() 内部判断

  // 回调 ref，避免依赖变化导致重连
  const callbacksRef = useRef({ onMessage, onConnect, onDisconnect, onError })
  useEffect(() => {
    callbacksRef.current = { onMessage, onConnect, onDisconnect, onError }
  }, [onMessage, onConnect, onDisconnect, onError])

  const RECONNECT_DELAY = 3000
  const PING_INTERVAL = 30000
  // 间隔3秒无限重连（用户要求）

  // ── 清理定时器
  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
      pingTimerRef.current = null
    }
  }, [])

  // ── 发送消息
  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
      return true
    }
    return false
  }, [])

  // ── 订阅
  const subscribe = useCallback((targetDate) => {
    if (!targetDate) return false
    const ok = send({
      action: 'subscribe',
      date: targetDate,
      sections: ['company', 'cctv', 'caixin', 'global'],
    })
    if (ok) subscribedDateRef.current = targetDate
    return ok
  }, [send])

  // ── 取消订阅
  const unsubscribe = useCallback((targetDate) => {
    send({ action: 'unsubscribe', date: targetDate })
    if (subscribedDateRef.current === targetDate) subscribedDateRef.current = null
  }, [send])

  // ── 建立连接（注意：不依赖任何 state，只用 ref）
  const connect = useCallback(() => {
    if (!isMountedRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (isConnectingRef.current) return   // ← 用 ref 判断，不依赖 state

    isConnectingRef.current = true
    setIsConnecting(true)

    try {
      const wsUrl = `ws://${window.location.hostname}:8001/ws`
      console.log('[WS] Connecting...', { date: subscribedDateRef.current, attempt: reconnectCountRef.current + 1 })

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (!isMountedRef.current) return
        console.log('[WS] Connected')

        isConnectingRef.current = false
        setIsConnected(true)
        setIsConnecting(false)
        reconnectCountRef.current = 0

        // 订阅当前日期（从 ref 读，不从 closure 读）
        if (subscribedDateRef.current) {
          subscribe(subscribedDateRef.current)
        }

        // 启动心跳
        pingTimerRef.current = setInterval(() => {
          send({ action: 'ping' })
        }, PING_INTERVAL)

        callbacksRef.current.onConnect?.()
      }

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return
        try {
          const message = JSON.parse(event.data)
          callbacksRef.current.onMessage?.(message)
        } catch (err) {
          console.error('[WS] Parse error:', err)
        }
      }

      ws.onerror = (err) => {
        console.error('[WS] Error:', err)
        isConnectingRef.current = false
        if (isMountedRef.current) {
          setIsConnecting(false)
          callbacksRef.current.onError?.(err)
        }
      }

      ws.onclose = (event) => {
        console.log('[WS] Closed:', event.code)
        isConnectingRef.current = false

        if (!isMountedRef.current) return

        setIsConnected(false)
        setIsConnecting(false)
        wsRef.current = null
        clearTimers()

        callbacksRef.current.onDisconnect?.(event.code)

        // 非正常关闭则自动重连
        if (event.code !== 1000 && event.code !== 1001 && reconnectCountRef.current < MAX_RECONNECT) {
          reconnectCountRef.current += 1
          console.log(`[WS] Reconnecting in ${RECONNECT_DELAY}ms... (${reconnectCountRef.current}/${MAX_RECONNECT})`)
          reconnectTimerRef.current = setTimeout(() => {
            if (isMountedRef.current) connect()
          }, RECONNECT_DELAY)
        }
      }
    } catch (err) {
      console.error('[WS] Failed to create:', err)
      isConnectingRef.current = false
      setIsConnecting(false)
      callbacksRef.current.onError?.(err)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // ← 故意空依赖：connect 是稳定函数，内部全用 ref

  // ── 断开连接
  const disconnect = useCallback(() => {
    clearTimers()
    isConnectingRef.current = false
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, 'Client disconnect')
      }
      wsRef.current = null
    }
    if (isMountedRef.current) {
      setIsConnected(false)
      setIsConnecting(false)
    }
    reconnectCountRef.current = 0
  }, [clearTimers])

  // ── 初次挂载 / enabled 变化：建立或断开连接
  useEffect(() => {
    isMountedRef.current = true

    if (enabled && date) {
      // 把当前日期写入 ref，供 connect() 的 onopen 订阅时读取
      subscribedDateRef.current = date
      connect()
    }

    return () => {
      isMountedRef.current = false
      disconnect()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])   // ← 只依赖 enabled；date 的变化由下面的 effect 处理

  // ── 日期变化：更新订阅（不重建连接）
  useEffect(() => {
    if (!date) return
    subscribedDateRef.current = date  // 始终保持最新

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // 已连接 → 切换订阅
      const old = subscribedDateRef.current
      if (old && old !== date) unsubscribe(old)
      subscribe(date)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date])

  return {
    isConnected,
    isConnecting,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
  }
}

export default useNewsWebSocketV2
