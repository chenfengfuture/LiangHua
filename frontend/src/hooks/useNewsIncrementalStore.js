/**
 * 新闻增量状态管理
 * 
 * 核心设计：
 * 1. 用 Set 维护已加载的新闻 ID，严格去重
 * 2. 支持 add / update / delete 增量操作，不全量重载
 * 3. 追踪每个板块的 maxId 和 lastTimestamp，供断线重连后补数据
 * 4. 已读状态和"NEW"标识独立管理
 */

import { useReducer, useCallback, useRef } from 'react'

// ─── Action Types ─────────────────────────────────────────────────────────────

export const INC_ACTIONS = {
  // 批量设置（首次加载 / 手动刷新）
  SET_SECTION: 'SET_SECTION',
  // 增量：插入一条（顶部）
  ADD_NEWS: 'ADD_NEWS',
  // 增量：更新一条
  UPDATE_NEWS: 'UPDATE_NEWS',
  // 增量：删除一条
  DELETE_NEWS: 'DELETE_NEWS',
  // 批量增量合并（重连补数据）
  MERGE_NEWS: 'MERGE_NEWS',
  // 标记已读
  MARK_READ: 'MARK_READ',
  // 标记全部已读
  MARK_ALL_READ: 'MARK_ALL_READ',
  // 重置板块
  RESET_SECTION: 'RESET_SECTION',
}

// ─── Section 初始状态 ─────────────────────────────────────────────────────────

function createSection() {
  return {
    data: [],           // 新闻数组（按时间倒序，最新在前）
    idSet: new Set(),   // 已加载 ID 集合（去重用）
    maxId: 0,           // 当前最大 ID（增量拉取起点）
    loading: false,
    error: null,
    stats: null,
    newIds: new Set(),  // 未读"NEW"标识
    updatedIds: new Set(), // 刚更新的条目标识
  }
}

const initialState = {
  company: createSection(),
  cctv: createSection(),
  caixin: createSection(),
  global: createSection(),
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

function incrementalReducer(state, action) {
  const { section: sectionKey, payload } = action

  switch (action.type) {
    case INC_ACTIONS.SET_SECTION: {
      // 批量替换板块数据（首次加载 / 刷新）
      const { data = [], stats = null, loading = false, error = null } = payload
      const idSet = new Set(data.map(item => item.id))
      const maxId = data.reduce((max, item) => Math.max(max, item.id || 0), 0)
      return {
        ...state,
        [sectionKey]: {
          data,
          idSet,
          maxId,
          loading,
          error,
          stats,
          newIds: new Set(),   // 全量刷新时清空 new 标识
          updatedIds: new Set(),
        },
      }
    }

    case INC_ACTIONS.ADD_NEWS: {
      // 增量：在顶部插入一条新新闻（去重）
      const { item } = payload
      if (!item || !item.id) return state
      const sec = state[sectionKey]
      if (sec.idSet.has(item.id)) return state // 已存在，跳过

      const newIdSet = new Set(sec.idSet)
      newIdSet.add(item.id)
      const newNewIds = new Set(sec.newIds)
      newNewIds.add(item.id)

      return {
        ...state,
        [sectionKey]: {
          ...sec,
          data: [item, ...sec.data], // 顶部插入
          idSet: newIdSet,
          maxId: Math.max(sec.maxId, item.id),
          newIds: newNewIds,
        },
      }
    }

    case INC_ACTIONS.UPDATE_NEWS: {
      // 增量：更新一条
      const { item } = payload
      if (!item || !item.id) return state
      const sec = state[sectionKey]
      const updatedIds = new Set(sec.updatedIds)
      updatedIds.add(item.id)
      return {
        ...state,
        [sectionKey]: {
          ...sec,
          data: sec.data.map(d => d.id === item.id ? { ...d, ...item } : d),
          updatedIds,
        },
      }
    }

    case INC_ACTIONS.DELETE_NEWS: {
      // 增量：删除一条
      const { id } = payload
      if (!id) return state
      const sec = state[sectionKey]
      const newIdSet = new Set(sec.idSet)
      newIdSet.delete(id)
      const newNewIds = new Set(sec.newIds)
      newNewIds.delete(id)
      const newUpdatedIds = new Set(sec.updatedIds)
      newUpdatedIds.delete(id)
      return {
        ...state,
        [sectionKey]: {
          ...sec,
          data: sec.data.filter(d => d.id !== id),
          idSet: newIdSet,
          newIds: newNewIds,
          updatedIds: newUpdatedIds,
        },
      }
    }

    case INC_ACTIONS.MERGE_NEWS: {
      // 批量增量合并（断线重连后补数据，去重后顶部插入）
      const { items = [] } = payload
      if (!items.length) return state
      const sec = state[sectionKey]

      const newItems = items.filter(item => item?.id && !sec.idSet.has(item.id))
      if (!newItems.length) return state

      const newIdSet = new Set(sec.idSet)
      const newNewIds = new Set(sec.newIds)
      newItems.forEach(item => {
        newIdSet.add(item.id)
        newNewIds.add(item.id)
      })
      const maxId = newItems.reduce((m, i) => Math.max(m, i.id || 0), sec.maxId)

      // 按 id 降序合并
      const merged = [...newItems, ...sec.data].sort((a, b) => (b.id || 0) - (a.id || 0))

      return {
        ...state,
        [sectionKey]: {
          ...sec,
          data: merged,
          idSet: newIdSet,
          maxId,
          newIds: newNewIds,
        },
      }
    }

    case INC_ACTIONS.MARK_READ: {
      // 标记已读（清除 newIds / updatedIds 中的该 ID）
      const { id } = payload
      const sec = state[sectionKey]
      const newIds = new Set(sec.newIds)
      const updatedIds = new Set(sec.updatedIds)
      newIds.delete(id)
      updatedIds.delete(id)
      return {
        ...state,
        [sectionKey]: { ...sec, newIds, updatedIds },
      }
    }

    case INC_ACTIONS.MARK_ALL_READ: {
      // 全部标记已读
      const sec = state[sectionKey]
      return {
        ...state,
        [sectionKey]: { ...sec, newIds: new Set(), updatedIds: new Set() },
      }
    }

    case INC_ACTIONS.RESET_SECTION: {
      return { ...state, [sectionKey]: createSection() }
    }

    default:
      return state
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useNewsIncrementalStore() {
  const [state, dispatch] = useReducer(incrementalReducer, initialState)

  // ── 批量设置（首次加载）
  const setSection = useCallback((sectionKey, data, stats = null) => {
    dispatch({
      type: INC_ACTIONS.SET_SECTION,
      section: sectionKey,
      payload: { data, stats },
    })
  }, [])

  // ── 增量：新增一条（顶部插入）
  const addNews = useCallback((sectionKey, item) => {
    dispatch({ type: INC_ACTIONS.ADD_NEWS, section: sectionKey, payload: { item } })
  }, [])

  // ── 增量：更新一条
  const updateNews = useCallback((sectionKey, item) => {
    dispatch({ type: INC_ACTIONS.UPDATE_NEWS, section: sectionKey, payload: { item } })
  }, [])

  // ── 增量：删除一条
  const deleteNews = useCallback((sectionKey, id) => {
    dispatch({ type: INC_ACTIONS.DELETE_NEWS, section: sectionKey, payload: { id } })
  }, [])

  // ── 批量增量合并（重连补数据）
  const mergeNews = useCallback((sectionKey, items) => {
    dispatch({ type: INC_ACTIONS.MERGE_NEWS, section: sectionKey, payload: { items } })
  }, [])

  // ── 标记已读
  const markRead = useCallback((sectionKey, id) => {
    dispatch({ type: INC_ACTIONS.MARK_READ, section: sectionKey, payload: { id } })
  }, [])

  // ── 全部已读
  const markAllRead = useCallback((sectionKey) => {
    dispatch({ type: INC_ACTIONS.MARK_ALL_READ, section: sectionKey, payload: {} })
  }, [])

  // ── 重置板块
  const resetSection = useCallback((sectionKey) => {
    dispatch({ type: INC_ACTIONS.RESET_SECTION, section: sectionKey, payload: {} })
  }, [])

  // ── 获取板块（兼容旧接口格式）
  const getSection = useCallback((key) => {
    const sec = state[key] || createSection()
    return {
      data: sec.data,
      loading: sec.loading,
      error: sec.error,
      stats: sec.stats,
      maxId: sec.maxId,
      newIds: sec.newIds,
      updatedIds: sec.updatedIds,
    }
  }, [state])

  // ── 计算属性
  const totalNewCount = Object.values(state).reduce(
    (sum, sec) => sum + (sec.newIds?.size || 0), 0
  )

  return {
    state,
    setSection,
    addNews,
    updateNews,
    deleteNews,
    mergeNews,
    markRead,
    markAllRead,
    resetSection,
    getSection,
    totalNewCount,
  }
}

export default useNewsIncrementalStore
