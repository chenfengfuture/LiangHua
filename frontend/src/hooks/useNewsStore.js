import { useReducer, useCallback, useRef, useEffect } from 'react'

/**
 * 新闻数据状态管理 - 使用 useReducer 模式
 * 
 * 设计理念：
 * 1. 单一数据源 - 所有状态集中管理
 * 2. 不可变更新 - 所有状态变更通过 action 触发
 * 3. 副作用分离 - 纯状态管理，不涉及网络请求
 */

// 初始状态
const initialState = {
  // 数据状态
  sections: {
    company: { data: [], loading: false, error: null, stats: null },
    cctv: { data: [], loading: false, error: null, stats: null },
    caixin: { data: [], loading: false, error: null, stats: null },
    global: { data: [], loading: false, error: null, stats: null },
  },
  // 全局状态
  overallLoading: false,
  overallError: null,
  // 采集状态
  collectionStatus: 'idle', // idle | collecting | ready | error
  collectingSections: [],
  pendingAnalysis: 0,
  // 重试状态
  retryStatus: {
    count: 0,
    isRetrying: false,
    nextRetryIn: 0,
  },
  // 弹窗状态
  showEmptyModal: false,
  hasShownModalThisSession: false,
}

// Action Types
export const ACTIONS = {
  // 数据加载
  SET_LOADING: 'SET_LOADING',
  SET_DATA: 'SET_DATA',
  SET_ERROR: 'SET_ERROR',
  UPDATE_SECTION: 'UPDATE_SECTION',
  
  // 采集状态
  SET_COLLECTION_STATUS: 'SET_COLLECTION_STATUS',
  ADD_COLLECTING_SECTION: 'ADD_COLLECTING_SECTION',
  REMOVE_COLLECTING_SECTION: 'REMOVE_COLLECTING_SECTION',
  SET_PENDING_ANALYSIS: 'SET_PENDING_ANALYSIS',
  
  // 重试状态
  SET_RETRY_STATUS: 'SET_RETRY_STATUS',
  INCREMENT_RETRY: 'INCREMENT_RETRY',
  RESET_RETRY: 'RESET_RETRY',
  
  // 弹窗
  SHOW_EMPTY_MODAL: 'SHOW_EMPTY_MODAL',
  HIDE_EMPTY_MODAL: 'HIDE_EMPTY_MODAL',
  
  // 重置
  RESET_STATE: 'RESET_STATE',
}

// Reducer
function newsReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SET_LOADING:
      return {
        ...state,
        overallLoading: action.payload,
        overallError: action.payload ? null : state.overallError,
      }

    case ACTIONS.SET_DATA:
      return {
        ...state,
        sections: action.payload.sections,
        overallLoading: false,
        overallError: null,
        collectionStatus: action.payload.status || 'ready',
        collectingSections: action.payload.collectingSections || [],
      }

    case ACTIONS.SET_ERROR:
      return {
        ...state,
        overallError: action.payload,
        overallLoading: false,
      }

    case ACTIONS.UPDATE_SECTION:
      return {
        ...state,
        sections: {
          ...state.sections,
          [action.payload.key]: {
            ...state.sections[action.payload.key],
            ...action.payload.data,
          },
        },
      }

    case ACTIONS.SET_COLLECTION_STATUS:
      return {
        ...state,
        collectionStatus: action.payload,
      }

    case ACTIONS.ADD_COLLECTING_SECTION:
      return {
        ...state,
        collectingSections: state.collectingSections.includes(action.payload)
          ? state.collectingSections
          : [...state.collectingSections, action.payload],
      }

    case ACTIONS.REMOVE_COLLECTING_SECTION:
      return {
        ...state,
        collectingSections: state.collectingSections.filter(s => s !== action.payload),
      }

    case ACTIONS.SET_PENDING_ANALYSIS:
      return {
        ...state,
        pendingAnalysis: action.payload,
      }

    case ACTIONS.SET_RETRY_STATUS:
      return {
        ...state,
        retryStatus: { ...state.retryStatus, ...action.payload },
      }

    case ACTIONS.INCREMENT_RETRY:
      return {
        ...state,
        retryStatus: {
          ...state.retryStatus,
          count: state.retryStatus.count + 1,
          isRetrying: true,
        },
      }

    case ACTIONS.RESET_RETRY:
      return {
        ...state,
        retryStatus: { count: 0, isRetrying: false, nextRetryIn: 0 },
      }

    case ACTIONS.SHOW_EMPTY_MODAL:
      return {
        ...state,
        showEmptyModal: true,
        hasShownModalThisSession: true,
      }

    case ACTIONS.HIDE_EMPTY_MODAL:
      return {
        ...state,
        showEmptyModal: false,
      }

    case ACTIONS.RESET_STATE:
      return {
        ...initialState,
        hasShownModalThisSession: state.hasShownModalThisSession,
      }

    default:
      return state
  }
}

/**
 * 新闻状态管理 Hook
 * 
 * @param {Object} options - 配置选项
 * @param {string} options.date - 当前日期
 * @param {boolean} options.autoLoad - 是否自动加载
 */
export function useNewsStore(options = {}) {
  const { date, autoLoad = true } = options
  
  const [state, dispatch] = useReducer(newsReducer, initialState)
  
  // 使用 ref 存储 dispatch 的包装函数，避免循环依赖
  const actionsRef = useRef({})
  
  // 创建稳定的 action creators
  const setLoading = useCallback((loading) => {
    dispatch({ type: ACTIONS.SET_LOADING, payload: loading })
  }, [])
  
  const setData = useCallback((data) => {
    dispatch({ type: ACTIONS.SET_DATA, payload: data })
  }, [])
  
  const setError = useCallback((error) => {
    dispatch({ type: ACTIONS.SET_ERROR, payload: error })
  }, [])
  
  const updateSection = useCallback((key, data) => {
    dispatch({ type: ACTIONS.UPDATE_SECTION, payload: { key, data } })
  }, [])
  
  const setCollectionStatus = useCallback((status) => {
    dispatch({ type: ACTIONS.SET_COLLECTION_STATUS, payload: status })
  }, [])
  
  const addCollectingSection = useCallback((section) => {
    dispatch({ type: ACTIONS.ADD_COLLECTING_SECTION, payload: section })
  }, [])
  
  const removeCollectingSection = useCallback((section) => {
    dispatch({ type: ACTIONS.REMOVE_COLLECTING_SECTION, payload: section })
  }, [])
  
  const setPendingAnalysis = useCallback((count) => {
    dispatch({ type: ACTIONS.SET_PENDING_ANALYSIS, payload: count })
  }, [])
  
  const setRetryStatus = useCallback((status) => {
    dispatch({ type: ACTIONS.SET_RETRY_STATUS, payload: status })
  }, [])
  
  const incrementRetry = useCallback(() => {
    dispatch({ type: ACTIONS.INCREMENT_RETRY })
  }, [])
  
  const resetRetry = useCallback(() => {
    dispatch({ type: ACTIONS.RESET_RETRY })
  }, [])
  
  const showEmptyModal = useCallback(() => {
    dispatch({ type: ACTIONS.SHOW_EMPTY_MODAL })
  }, [])
  
  const hideEmptyModal = useCallback(() => {
    dispatch({ type: ACTIONS.HIDE_EMPTY_MODAL })
  }, [])
  
  const resetState = useCallback(() => {
    dispatch({ type: ACTIONS.RESET_STATE })
  }, [])
  
  // 更新 actionsRef
  useEffect(() => {
    actionsRef.current = {
      setLoading,
      setData,
      setError,
      updateSection,
      setCollectionStatus,
      addCollectingSection,
      removeCollectingSection,
      setPendingAnalysis,
      setRetryStatus,
      incrementRetry,
      resetRetry,
      showEmptyModal,
      hideEmptyModal,
      resetState,
    }
  }, [
    setLoading, setData, setError, updateSection,
    setCollectionStatus, addCollectingSection, removeCollectingSection,
    setPendingAnalysis, setRetryStatus, incrementRetry, resetRetry,
    showEmptyModal, hideEmptyModal, resetState,
  ])
  
  // 计算属性
  const totalCount = Object.values(state.sections).reduce(
    (sum, section) => sum + (section.data?.length || 0), 0
  )
  
  const hasData = totalCount > 0
  
  return {
    // 状态
    state,
    // Actions
    actions: actionsRef,
    // Action creators
    setLoading,
    setData,
    setError,
    updateSection,
    setCollectionStatus,
    addCollectingSection,
    removeCollectingSection,
    setPendingAnalysis,
    setRetryStatus,
    incrementRetry,
    resetRetry,
    showEmptyModal,
    hideEmptyModal,
    resetState,
    // 计算属性
    totalCount,
    hasData,
  }
}

export default useNewsStore
