/**
 * useTableScrollY - 自动计算 Table scroll.y 的 Hook
 *
 * 通过 ResizeObserver 监听表格容器的高度变化，动态计算 scroll.y，
 * 使表格内容区填满视口剩余高度，分页器保持在底部。
 *
 * @param paginationHeight - 分页器占用高度（默认 52px，含间距和 antd 分页器高度）
 * @returns containerRef - 挂载到表格外层 div
 * @returns scrollY - 可在 Table scroll={{ y: scrollY }} 中使用的值
 * @returns setScrollY - 手动设置 scrollY 值（用于特殊场景覆盖）
 */

import { useRef, useState, useEffect, useCallback } from 'react';

export function useTableScrollY(paginationHeight = 52) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState<number>(400);

  const updateHeight = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const available = rect.height - paginationHeight;
      setScrollY(Math.max(200, Math.floor(available)));
    }
  }, [paginationHeight]);

  useEffect(() => {
    // 初始计算
    updateHeight();

    const element = containerRef.current;
    if (!element) return;

    // 使用 ResizeObserver 监听容器尺寸变化
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(updateHeight);
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [updateHeight]);

  return { containerRef, scrollY, setScrollY };
}