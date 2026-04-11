import { useCallback, useRef, useEffect, useState } from 'react'
import { getAllNewsSections } from '../api/stocks'
import { useNewsStore, ACTIONS } from './useNewsStore'
import { useNewsIncrementalStore } from './useNewsIncrementalStore'
import { useNewsWebSocketV2 } from './useNewsWebSocketV2'
import axios from 'axios'

const BASE = 'http://localhost:8001'
const api = axios.create({ baseURL: BASE, timeout: 10000 })

/**
 * 新闻数据管理 Hook - 增量实时版
 *
 * 数据流：
 * 1. 初始化：全量拉取 /api/news/fetch → setSection()
 * 2. WS add → 按 ID 拉取单条 → addNews()（顶部插入，去重）
 * 3. WS update → 按 ID 拉取单条 → updateNews()
 * 4. WS delete → deleteNews()
 * 5. WS bulk → 标记 count 变化，状态 ready 后增量拉取 incremental
 * 6. WS 断开 → 3s 重连；重连成功后按 maxId 补全增量
 */
export function useNewsData(options = {}) {
  const {
    date,
    symbol = null,
    eventType = null,
    tag = null,
    source = null,
    limit = 500,
    autoLoad = true,
    onDataChange = null,
  } = options

  // ── 旧 Store（全局状态：loading/error/采集状态/重试） ────────────────────
  const {
    state,
    setLoading,
    setData,
    setError,
    updateSection: updateSectionStore,
    addCollectingSection,
    removeCollectingSection,
    setPendingAnalysis,
    incrementRetry,
    resetRetry,
    showEmptyModal,
    hideEmptyModal,
    totalCount,
    hasData,
  } = useNewsStore({ date, autoLoad })

  // ── 新增量 Store ──────────────────────────────────────────────────────────
  const {
    getSection,
    setSection,
    addNews,
    updateNews,
    deleteNews,
    mergeNews,
    markRead,
    markAllRead,
    resetSection,
    totalNewCount,
  } = useNewsIncrementalStore()

  // 用 ref 持有最新的 store 方法，供 WS 回调（useCallback）内部使用，
  // 避免依赖变化导致 WS 回调重建（进而触发 useEffect 重建 WS 连接）
  const storeRef = useRef({})
  useEffect(() => {
    storeRef.current = { getSection, addNews, updateNews, deleteNews, mergeNews }
  })

  // ── Refs ──────────────────────────────────────────────────────────────────
  const isLoadingRef = useRef(false)
  const hasLoadedRef = useRef(false)
  const prevDateRef = useRef(null)
  const retryTimerRef = useRef(null)
  const isMountedRef = useRef(true)
  const pendingIncrementalRef = useRef({})  // { sectionKey: bool } 待增量拉取标记
  const loadStartedRef = useRef(false)
  // state 的快照 ref，供稳定的 useCallback 读取，避免它们作为 deps 触发重建
  const stateRef = useRef(state)
  useEffect(() => { stateRef.current = state })

  // 重试配置
  const MAX_RETRY = 10
  const RETRY_INTERVAL = 5 * 60 * 1000

  // ── 清理 ──────────────────────────────────────────────────────────────────
  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
  }, [])

  // ── 全量加载（首次 / 手动刷新） ───────────────────────────────────────────
  const loadData = useCallback(async (force = false) => {
    if (isLoadingRef.current) return
    if (!date || !isMountedRef.current) return
    if (!force && hasLoadedRef.current && prevDateRef.current === date && hasData) return

    isLoadingRef.current = true
    setLoading(true)

    try {
      const apiOptions = { symbol, eventType, tag, source, limit }
      const result = await getAllNewsSections(date, apiOptions)
      if (!isMountedRef.current) return

      resetRetry()
      clearRetryTimer()

      // 更新各板块增量 store
      const sectionKeys = ['company', 'cctv', 'caixin', 'global']
      const newSections = {}
      sectionKeys.forEach(key => {
        const sd = result.sections?.[key] || { data: [], count: 0 }
        const sectionData = sd.data || []
        const stats = {
          count: sd.count || 0,
          source: sd.source || 'unknown',
          pending_analysis: sd.pending_analysis || 0,
        }
        // 全量写入增量 store（重置 ID set）
        setSection(key, sectionData, stats)
        newSections[key] = { data: sectionData, loading: false, error: sd.error || null, stats }
      })

      // 更新旧 store 的采集状态
      const collectingSections = Object.entries(result.sections || {})
        .filter(([_, d]) => d.source === 'collecting')
        .map(([k]) => k)

      setData({
        sections: newSections,
        status: result.status || 'ready',
        collectingSections,
      })

      hasLoadedRef.current = true
      prevDateRef.current = date

      if (result.total_count === 0 && !stateRef.current.hasShownModalThisSession) {
        showEmptyModal()
      }

      onDataChange?.(newSections, result)
    } catch (err) {
      if (!isMountedRef.current) return
      const errMsg = formatErrorMessage(err)
      setError(errMsg)

      if (shouldRetry(err) && stateRef.current.retryStatus.count < MAX_RETRY) {
        incrementRetry()
        retryTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            isLoadingRef.current = false
            loadData(false)
          }
        }, RETRY_INTERVAL)
      }
    } finally {
      isLoadingRef.current = false
      if (isMountedRef.current) setLoading(false)
    }
  }, [
    date, symbol, eventType, tag, source, limit,
    setLoading, setData, setError, resetRetry, clearRetryTimer,
    incrementRetry, showEmptyModal, onDataChange, hasData, setSection,
    // stateRef 是 ref 不需要加入 deps
  ])

  // ── 增量拉取（断线重连补数据 / bulk 推送后补全） ──────────────────────────
  const fetchIncremental = useCallback(async (sectionKey, afterId) => {
    if (!isMountedRef.current) return
    const currentDate = prevDateRef.current
    if (!currentDate) return
    try {
      const resp = await api.get(`/api/news/fetch/${sectionKey}`, {
        params: { date: currentDate, limit: 100 },
      })
      const { data = [] } = resp.data
      // 过滤出 id > afterId 的项（如果 afterId 为 null 或 undefined，则包含所有项）
      const filtered = afterId != null ? data.filter(item => item.id > afterId) : data
      if (filtered.length > 0 && isMountedRef.current) {
        storeRef.current.mergeNews?.(sectionKey, filtered)
      }
    } catch (err) {
      console.warn(`[NewsData] 增量拉取失败 ${sectionKey}:`, err.message)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // 用 ref 读 date/mergeNews，不依赖它们

  // ── 按 ID 拉取单条 ─────────────────────────────────────────────────────────
  const fetchSingleNews = useCallback(async (sectionKey, newsId) => {
    if (!isMountedRef.current) return null
    const currentDate = prevDateRef.current
    if (!currentDate) return null
    try {
      const resp = await api.get(`/api/news/fetch/${sectionKey}`, {
        params: { date: currentDate, limit: 100 },
      })
      const { data = [] } = resp.data
      const found = data.find(item => item.id == newsId)
      return found || null
    } catch {
      return null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // 用 ref 读 date

  // ── WS 消息处理 ───────────────────────────────────────────────────────────
  const handleWebSocketMessage = useCallback((message) => {
    const store = storeRef.current
    switch (message.type) {

      case 'news_updated': {
        const { section: sec, op = 'bulk', news_id, data } = message

        if (op === 'add' && news_id) {
          fetchSingleNews(sec, news_id).then(item => {
            if (item && isMountedRef.current) store.addNews?.(sec, item)
          })
        } else if (op === 'update' && news_id) {
          fetchSingleNews(sec, news_id).then(item => {
            if (item && isMountedRef.current) store.updateNews?.(sec, item)
          })
        } else if (op === 'delete' && news_id) {
          store.deleteNews?.(sec, news_id)
        } else {
          // bulk：标记待增量拉取，等 collection_status=ready 后执行
          if (sec) {
            updateSectionStore(sec, {
              stats: {
                ...store.getSection?.(sec)?.stats,
                count: data?.count,
                source: data?.source,
              },
            })
            pendingIncrementalRef.current[sec] = true
          }
        }
        break
      }

      case 'collection_status': {
        const { section: sec, status, progress } = message
        if (status === 'collecting' || status === 'analyzing') {
          addCollectingSection(sec)
        } else {
          removeCollectingSection(sec)
        }

        if (progress?.pending_count) {
          setPendingAnalysis(progress.pending_count)
        } else if (status === 'ready') {
          setPendingAnalysis(0)
        }

        if (status === 'ready' && progress?.count > 0 && pendingIncrementalRef.current[sec]) {
          pendingIncrementalRef.current[sec] = false
          const currentMaxId = store.getSection?.(sec)?.maxId || 0
          setTimeout(() => {
            if (isMountedRef.current) fetchIncremental(sec, currentMaxId)
          }, 500)
        }
        break
      }

      case 'sentiment_complete':
      case 'subscribed':
      case 'pong':
        break

      case 'error':
        console.error('[NewsData] WS Error:', message.message)
        break

      default:
        break
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])  // 所有外部依赖均通过 ref 访问，deps 稳定为空

  // ── 重连成功回调：按各板块 maxId 补数据 ──────────────────────────────────
  const handleWsConnect = useCallback(() => {
    if (!hasLoadedRef.current) return  // 首次连接不需要补，全量拉即可
    const sections = ['company', 'cctv', 'caixin', 'global']
    sections.forEach(sec => {
      const maxId = storeRef.current.getSection?.(sec)?.maxId || 0
      fetchIncremental(sec, maxId)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── WebSocket 连接 ────────────────────────────────────────────────────────
  const { isConnected: wsConnected } = useNewsWebSocketV2({
    date,
    enabled: autoLoad && !!date,
    onMessage: handleWebSocketMessage,
    onConnect: handleWsConnect,
  })

  // ── 初始化加载 ────────────────────────────────────────────────────────────
  useEffect(() => {
    isMountedRef.current = true

    if (autoLoad && date) {
      const isDateChanged = prevDateRef.current !== date
      if (isDateChanged || !hasLoadedRef.current) {
        // 日期切换时重置所有板块增量 store
        if (isDateChanged && prevDateRef.current) {
          ;['company', 'cctv', 'caixin', 'global'].forEach(k => resetSection(k))
          pendingIncrementalRef.current = {}
        }
        loadData(true)
      }
    }

    return () => {
      isMountedRef.current = false
      clearRetryTimer()
    }
  }, [date, autoLoad]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 手动刷新 ──────────────────────────────────────────────────────────────
  const refresh = useCallback(() => {
    resetRetry()
    clearRetryTimer()
    hasLoadedRef.current = false
    loadData(true)
  }, [resetRetry, clearRetryTimer, loadData])

  // ── 计算 totalCount（基于增量 store 中实际数据）─────────────────────────
  const realTotalCount = ['company', 'cctv', 'caixin', 'global']
    .reduce((sum, k) => sum + (getSection(k)?.data?.length || 0), 0)

  // ── 获取统计 ──────────────────────────────────────────────────────────────
  const getStats = useCallback(() => {
    const stats = {}
    ;['company', 'cctv', 'caixin', 'global'].forEach(key => {
      const sec = getSection(key)
      stats[key] = { count: sec.data?.length || 0, ...sec.stats }
    })
    return stats
  }, [getSection])

  return {
    // 数据 - 优先从增量 store 读
    sections: state.sections,  // 保持旧格式兼容（主组件可能用）
    overallLoading: state.overallLoading,
    overallError: state.overallError,

    // 采集状态
    collectionStatus: state.collectionStatus,
    collectingSections: state.collectingSections,
    pendingAnalysis: state.pendingAnalysis,

    // WebSocket
    wsConnected,

    // 弹窗
    showEmptyModal: state.showEmptyModal,
    hideEmptyModal,

    // 重试
    retryStatus: state.retryStatus,

    // 计算属性
    totalCount: realTotalCount,
    hasData: realTotalCount > 0,
    totalNewCount,  // 未读新消息总数

    // 方法
    refresh,
    getSection,     // 从增量 store 读（含 newIds/updatedIds/maxId）
    getStats,
    loadData,
    markRead,
    markAllRead,
    fetchIncremental,
  }
}

// ── 工具函数 ─────────────────────────────────────────────────────────────────

function formatErrorMessage(err) {
  const msg = err?.message || ''
  if (msg.includes('Network Error') || msg.includes('ERR_INSUFFICIENT_RESOURCES')) return '网络资源不足，请稍后重试'
  if (msg.includes('timeout')) return '请求超时，后端处理时间过长'
  if (msg.includes('Failed to fetch') || msg.includes('ECONNREFUSED')) return '无法连接到服务器'
  if (msg.includes('aborted')) return '请求被取消'
  return msg.length > 100 ? msg.substring(0, 100) + '...' : msg || '数据加载失败'
}

function shouldRetry(err) {
  const msg = err?.message || ''
  return msg.includes('Network') || msg.includes('timeout') ||
    msg.includes('ERR_INSUFFICIENT_RESOURCES') ||
    msg.includes('Failed to fetch') || msg.includes('ECONNREFUSED')
}

export default useNewsData
