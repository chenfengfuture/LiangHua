/**
 * useECharts — ECharts 实例生命周期管理 Hook
 *
 * 统一封装 echarts.init / setOption / resize / dispose 样板代码。
 * 所有使用 ECharts 的组件通过此 hook 消除重复逻辑。
 *
 * 使用方式：
 *   const chartRef = useECharts(chartContainerRef, option, [theme, colors]);
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

/**
 * 初始化并管理 ECharts 实例
 * @param containerRef 图表容器 DOM ref
 * @param option       图表配置项
 * @param deps         依赖数组，变化时重新 setOption
 * @param theme        'dark' | undefined
 * @returns            无返回值，图表实例内部管理
 */
export function useECharts(
  containerRef: React.RefObject<HTMLDivElement | null>,
  option: echarts.EChartsOption | null,
  deps: any[] = [],
  theme?: string,
) {
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // 只初始化一次
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(el, theme);
    }

    if (option) {
      instanceRef.current.setOption(option, true);
    }

    const handleResize = () => {
      instanceRef.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      // dispose 由外层组件在 unmount 时处理
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  // 组件卸载时销毁实例
  useEffect(() => {
    return () => {
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, []);
}

/**
 * 获取 ECharts 实例（用于需要直接操作实例的场景）
 */
export function useEChartsInstance() {
  return useRef<echarts.ECharts | null>(null);
}