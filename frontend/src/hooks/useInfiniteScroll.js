/**
 * useInfiniteScroll - 基于 IntersectionObserver 的无限滚动分页 Hook
 *
 * 特点：
 * - 使用 IntersectionObserver 监听哨兵元素，零 scroll 事件、零性能损耗
 * - 前端内存分页（数据全量在内存，每次 slice 展示一部分）
 * - news 数据变化时自动重置到第一页
 * - 支持自定义 pageSize 和 threshold（提前触发距离）
 *
 * @param {Array}  allItems   - 全量数据数组
 * @param {Object} options
 *   @param {number} options.pageSize    - 每页条数（默认 30）
 *   @param {number} options.threshold  - 触发提前量（0.0~1.0，默认 0.1 即底部 10% 进入视口时触发）
 * @returns {{
 *   visibleItems: Array,    // 当前可见的条目
 *   hasMore: boolean,       // 是否还有更多
 *   sentinelRef: Function,  // 哨兵元素的 ref callback（挂在列表末尾的占位 div 上）
 *   total: number,          // 数据总量
 *   displayCount: number,   // 当前展示数量
 * }}
 */
import { useEffect, useRef, useState, useCallback } from 'react'

export function useInfiniteScroll(allItems = [], { pageSize = 30, threshold = 0.1 } = {}) {
  const [displayCount, setDisplayCount] = useState(pageSize)
  const observerRef = useRef(null)
  const sentinelNodeRef = useRef(null)

  // 数据变化时重置展示数量
  useEffect(() => {
    setDisplayCount(pageSize)
  }, [allItems, pageSize])

  // 哨兵元素 callback ref
  const sentinelRef = useCallback((node) => {
    // 先断开旧的观察
    if (observerRef.current) {
      observerRef.current.disconnect()
      observerRef.current = null
    }
    sentinelNodeRef.current = node
    if (!node) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setDisplayCount(prev => prev + pageSize)
        }
      },
      { threshold }
    )
    observerRef.current.observe(node)
  }, [pageSize, threshold])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [])

  const total = allItems.length
  const visibleItems = allItems.slice(0, displayCount)
  const hasMore = displayCount < total

  return { visibleItems, hasMore, sentinelRef, total, displayCount }
}
