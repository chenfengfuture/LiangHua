import { useEffect, useRef, useCallback, useState } from 'react'
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from 'lightweight-charts'
import { prefetchIntraday } from './IntradayModal'

// 默认均线配置（固定 4 条，不含 MA120/MA250）
const DEFAULT_MA_CONFIG = [
  { key: 'MA5',  period: 5,  color: '#ff9800' },
  { key: 'MA10', period: 10, color: '#2196f3' },
  { key: 'MA20', period: 20, color: '#e91e63' },
  { key: 'MA60', period: 60, color: '#9c27b0' },
]

/**
 * lightweight-charts v5：数据 time 为字符串（'YYYY-MM-DD'）时，
 * subscribeClick/subscribeCrosshairMove 回调中 param.time 会变成
 * BusinessDay 对象 { year, month, day }，需转回字符串。
 */
function paramTimeToStr(t) {
  if (!t) return null
  if (typeof t === 'string') return t
  if (typeof t === 'number') {
    const d = new Date(t * 1000)
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
    const dd = String(d.getUTCDate()).padStart(2, '0')
    return `${d.getUTCFullYear()}-${mm}-${dd}`
  }
  // BusinessDay 对象
  if (t.year != null && t.month != null && t.day != null) {
    return `${t.year}-${String(t.month).padStart(2,'0')}-${String(t.day).padStart(2,'0')}`
  }
  return null
}

// 格式化数字
function fmt(v, digits = 2) {
  if (v == null) return '--'
  return typeof v === 'number' ? v.toFixed(digits) : String(v)
}

function fmtVol(v) {
  if (v == null || v === 0) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿手'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万手'
  return v.toFixed(0) + '手'
}

function fmtAmt(v) {
  if (v == null || v === 0) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(0)
}

// ── 悬停浮动 Tooltip 组件 ────────────────────────────────────────────
function KLineTooltip({ data, pos, containerRef }) {
  if (!data || !pos) return null

  const { open, high, low, close, vol, amount, prev_close, time } = data

  // 涨跌计算
  const base = prev_close ?? open
  const change     = (close != null && base != null) ? close - base : null
  const changePct  = (change != null && base && base !== 0) ? (change / base * 100) : null
  const isUp       = change != null ? change >= 0 : close >= open
  const priceColor = isUp ? '#FF0000' : '#00B050'
  const changeSign = change >= 0 ? '+' : ''

  // 振幅
  const amplitude  = (high != null && low != null && base && base !== 0)
    ? Math.abs((high - low) / base * 100)
    : null

  // Tooltip 位置：跟随鼠标，智能避边
  const TW = 188  // tooltip width
  const TH = 220  // tooltip height (estimated)
  const PAD = 14  // 距离鼠标的偏移

  const containerRect = containerRef.current?.getBoundingClientRect?.()
  const containerW = containerRect?.width ?? 800
  const containerH = containerRect?.height ?? 500

  let left = pos.x + PAD
  let top  = pos.y - TH / 2

  // 右侧越界 → 显示在鼠标左侧
  if (left + TW > containerW - 4) {
    left = pos.x - TW - PAD
  }
  // 上方越界
  if (top < 4) top = 4
  // 下方越界
  if (top + TH > containerH - 4) top = containerH - TH - 4

  const rows = [
    { label: '开盘', value: fmt(open), color: null },
    { label: '收盘', value: fmt(close), color: priceColor },
    { label: '最高', value: fmt(high), color: '#FF0000' },
    { label: '最低', value: fmt(low),  color: '#00B050' },
    { label: '涨跌额', value: change != null ? `${changeSign}${fmt(change)}` : '--', color: priceColor },
    { label: '涨跌幅', value: changePct != null ? `${changeSign}${fmt(changePct)}%` : '--', color: priceColor },
    { label: '振  幅', value: amplitude != null ? `${fmt(amplitude)}%` : '--', color: null },
    { label: '成交量', value: fmtVol(vol), color: null },
    { label: '成交额', value: fmtAmt(amount), color: null },
  ]

  return (
    <div style={{
      position: 'absolute',
      left,
      top,
      zIndex: 50,
      width: TW,
      background: 'rgba(14, 20, 32, 0.92)',
      border: `1px solid ${priceColor}40`,
      borderRadius: 6,
      padding: '8px 10px',
      pointerEvents: 'none',
      boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
    }}>
      {/* 日期标题 */}
      <div style={{
        color: '#8b949e',
        fontSize: 10,
        marginBottom: 6,
        paddingBottom: 5,
        borderBottom: `1px solid rgba(255,255,255,0.08)`,
        letterSpacing: 0.5,
      }}>
        {time}
      </div>

      {/* 数据行 */}
      {rows.map(({ label, value, color }) => (
        <div key={label} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '2.5px 0',
          fontSize: 11,
        }}>
          <span style={{ color: '#6e7681', minWidth: 42 }}>{label}</span>
          <span style={{
            color: color ?? '#c9d1d9',
            fontWeight: color ? 600 : 400,
            fontVariantNumeric: 'tabular-nums',
          }}>{value}</span>
        </div>
      ))}
    </div>
  )
}

/**
 * KLineChart
 *
 * Props:
 *   candles       – [{ time, open, high, low, close, vol?, amount?, prev_close? }]
 *   volumes       – [{ time, value, color }]
 *   maData        – { MA5: [...], MA10: [...], ... }
 *   maConfig      – [{ key, period, color }]  动态均线配置（含自定义均线）
 *   loading       – boolean
 *   priceLevels   – { resistance:[{price,label,method}], support:[{price,label,method}] } | null
 *   onCandleHover – (bar | null) => void
 *   onCandleClick – (bar, allCandles) => void   ← 同时传全量数组，方便查昨收
 */
export default function KLineChart({
  symbol   = '',
  candles  = [],
  volumes  = [],
  maData   = {},
  maConfig = DEFAULT_MA_CONFIG,
  loading  = false,
  priceLevels = null,
  onCandleHover,
  onCandleClick,
}) {
  const containerRef  = useRef(null)
  const chartRef      = useRef(null)
  const seriesRef     = useRef({})
  const candlesRef    = useRef([])       // 始终指向最新 candles 数组
  const symbolRef     = useRef(symbol)   // 用于 prefetch，避免闭包失效
  const onHoverRef    = useRef(onCandleHover)
  const onClickRef    = useRef(onCandleClick)
  const maConfigRef   = useRef(maConfig) // 保存最新 maConfig（避免闭包失效）

  // Tooltip 状态
  const [tooltipData, setTooltipData] = useState(null)  // 当前悬停 K 线数据
  const [tooltipPos,  setTooltipPos]  = useState(null)  // 鼠标在容器内的坐标

  // 压力位/支撑位线引用（用于清除重绘）
  const priceLinesRef = useRef([])  // [{ series, priceLine }]

  // 用 ref 同步最新值，避免闭包过期
  useEffect(() => { onHoverRef.current  = onCandleHover }, [onCandleHover])
  useEffect(() => { onClickRef.current  = onCandleClick }, [onCandleClick])
  useEffect(() => { symbolRef.current   = symbol        }, [symbol])
  useEffect(() => { maConfigRef.current = maConfig      }, [maConfig])

  // ── 初始化图表（只执行一次）─────────────────────────────────────
  const initChart = useCallback(() => {
    if (!containerRef.current) return

    // 如有旧实例先销毁
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      seriesRef.current = {}
    }

    // 读取当前主题的 CSS 变量
    const css = (name, fb) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb
    const bgBase    = css('--bg-base',     '#0d1117')
    const textNorm  = css('--text-normal', '#c9d1d9')
    const border    = css('--border',      '#21262d')
    const accent    = css('--accent',      '#58a6ff')
    const accentHov = css('--accent-hover','#1f6feb')
    const textFaint = css('--text-faint',  '#6e7681')
    const borderMut = css('--border-muted','#30363d')

    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth  || 800,
      height: containerRef.current.clientHeight || 500,
      layout: {
        background: { type: ColorType.Solid, color: bgBase },
        textColor: textNorm,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: border },
        horzLines: { color: border },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: accent, width: 1, style: 2, labelBackgroundColor: accentHov },
        horzLine: { color: textFaint, labelBackgroundColor: accentHov },
      },
      rightPriceScale: {
        borderColor: borderMut,
        scaleMargins: { top: 0.08, bottom: 0.28 },
      },
      timeScale: {
        borderColor: borderMut,
        timeVisible: true,
        secondsVisible: false,
        // fixLeftEdge / fixRightEdge 关掉，否则两端锁死导致滚轮无法缩放
        fixLeftEdge: false,
        fixRightEdge: false,
        rightOffset: 5,          // 右侧留 5 根K线的空白，看起来更自然
        barSpacing: 8,            // 默认柱宽 8px
        minBarSpacing: 2,         // 最小缩小到 2px（可看大范围）
      },
      // 明确开启滚轮缩放 & 拖拽平移
      handleScroll: {
        mouseWheel:    true,   // 鼠标滚轮左右滚动
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel:  true,   // Ctrl + 滚轮 或 直接滚轮缩放时间轴
        pinch:       true,   // 触控板双指缩放
        axisPressedMouseMove: {
          time:  true,       // 拖拽时间轴缩放
          price: true,
        },
      },
    })

    // K线主图
    seriesRef.current.candle = chart.addSeries(CandlestickSeries, {
      upColor:         '#FF0000',
      downColor:       '#00B050',
      borderUpColor:   '#FF0000',
      borderDownColor: '#00B050',
      wickUpColor:     '#FF0000',
      wickDownColor:   '#00B050',
    })

    // 成交量子图（默认色，实际由 volumes 数组中每条的 color 字段覆盖）
    seriesRef.current.volume = chart.addSeries(HistogramSeries, {
      color: '#00B050',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.80, bottom: 0 },
    })

    // 均线（根据当前 maConfigRef 动态创建）
    maConfigRef.current.forEach(({ key, color }) => {
      seriesRef.current[key] = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
    })

    // ── crosshairMove：更新 Tooltip 数据 ────────────────────────
    let prefetchTimer = null   // 防抖定时器
    chart.subscribeCrosshairMove(param => {
      if (!param.time) {
        setTooltipData(null)
        if (onHoverRef.current) onHoverRef.current(null)
        return
      }

      const timeStr = paramTimeToStr(param.time)
      if (!timeStr) {
        setTooltipData(null)
        if (onHoverRef.current) onHoverRef.current(null)
        return
      }

      const bar = candlesRef.current.find(c => c.time === timeStr)
      if (!bar) {
        setTooltipData(null)
        if (onHoverRef.current) onHoverRef.current(null)
        return
      }

      // 更新 Tooltip 数据
      setTooltipData({
        time:       timeStr,
        open:       bar.open,
        high:       bar.high,
        low:        bar.low,
        close:      bar.close,
        vol:        bar.vol        ?? null,
        amount:     bar.amount     ?? null,
        prev_close: bar.prev_close ?? null,
      })

      // 更新右侧面板（onCandleHover）
      if (onHoverRef.current) {
        onHoverRef.current({
          time:  timeStr,
          open:  bar.open,
          high:  bar.high,
          low:   bar.low,
          close: bar.close,
          vol:   bar.vol ?? null,
        })
      }

      // 悬停超过 300ms → 预取当日日内数据（加速后续点击弹窗）
      clearTimeout(prefetchTimer)
      prefetchTimer = setTimeout(() => {
        const sym = symbolRef.current
        if (sym && timeStr) prefetchIntraday(sym, timeStr)
      }, 300)
    })

    // ── 单击K线 → onCandleClick(bar, allCandles) ──────────────
    chart.subscribeClick(param => {
      if (!onClickRef.current) return
      if (!param.time) return

      const timeStr = paramTimeToStr(param.time)
      if (!timeStr) return

      // 从 candlesRef（最新快照）中查找，找不到说明点的是空白区域
      const bar = candlesRef.current.find(c => c.time === timeStr)
      if (!bar) return

      // 把 bar 和完整 candles 数组都传出去（上层用来求昨收等）
      onClickRef.current(bar, candlesRef.current)
    })

    chartRef.current = chart

    // 自动跟随容器尺寸
    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width:  containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, []) // 空依赖：只初始化一次

  useEffect(() => {
    const cleanup = initChart()
    return () => {
      cleanup && cleanup()
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = {}
      }
    }
  }, [initChart])

  // ── 数据更新 ────────────────────────────────────────────────────
  const prevCandlesLenRef = useRef(0)   // 记录上次 candles 长度，判断是否首次加载

  useEffect(() => {
    candlesRef.current = candles   // 同步最新快照

    if (!chartRef.current) return
    const { candle, volume } = seriesRef.current
    if (!candle || !volume || candles.length === 0) return

    candle.setData(candles)
    volume.setData(volumes)

    // 更新均线数据（只更新 maConfig 中有的 key）
    maConfig.forEach(({ key }) => {
      const s = seriesRef.current[key]
      if (s) s.setData(maData[key] || [])
    })

    // 只在首次加载（或切换股票/时间范围导致数据量变化较大）时 fitContent
    // 避免用户用滚轮缩放后被强制复位
    const prev = prevCandlesLenRef.current
    const curr = candles.length
    if (prev === 0 || Math.abs(curr - prev) > 10) {
      chartRef.current.timeScale().fitContent()
    }
    prevCandlesLenRef.current = curr
  }, [candles, volumes, maData, maConfig])

  // ── maConfig 变化时：销毁旧均线 series，重建新 series ────────
  useEffect(() => {
    if (!chartRef.current) return

    // 找出已有的 MA series keys
    const existingMAKeys = Object.keys(seriesRef.current).filter(
      k => k !== 'candle' && k !== 'volume'
    )
    // 找出新 maConfig 的 keys
    const newKeys = maConfig.map(m => m.key)

    // 移除不再需要的 series
    existingMAKeys.forEach(k => {
      if (!newKeys.includes(k)) {
        try { chartRef.current.removeSeries(seriesRef.current[k]) } catch {}
        delete seriesRef.current[k]
      }
    })

    // 添加新增的 series
    maConfig.forEach(({ key, color }) => {
      if (!seriesRef.current[key]) {
        seriesRef.current[key] = chartRef.current.addSeries(LineSeries, {
          color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        })
        // 立即填充已有数据
        seriesRef.current[key].setData(maData[key] || [])
      }
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maConfig])

  // ── priceLevels 变化时：清旧线，绘新线 ─────────────────────────
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current.candle) return

    // 清除旧的压力位线
    priceLinesRef.current.forEach(({ series, priceLine }) => {
      try { series.removePriceLine(priceLine) } catch {}
    })
    priceLinesRef.current = []

    if (!priceLevels) return

    const candleSeries = seriesRef.current.candle

    // 方法 → 颜色映射
    const methodColor = {
      pivot: '#f0b429',   // 枢轴点：金黄
      local: '#ffffff',   // 局部极值：白色
      ma:    '#00bcd4',   // 均线：青色
      fib:   '#ce93d8',   // 斐波那契：淡紫
    }

    const drawLine = (level, isResistance) => {
      const color = methodColor[level.method] ?? '#888888'
      const priceLine = candleSeries.createPriceLine({
        price:       level.price,
        color:       color,
        lineWidth:   1,
        lineStyle:   2,        // Dashed
        axisLabelVisible: true,
        title:       `${isResistance ? '▲' : '▽'} ${level.label} ${level.price.toFixed(2)}`,
      })
      priceLinesRef.current.push({ series: candleSeries, priceLine })
    }

    // 只绘制最近的3个压力位 + 3个支撑位（避免图面太乱）
    const resistances = (priceLevels.resistance || []).slice(0, 3)
    const supports    = (priceLevels.support    || []).slice(0, 3)

    resistances.forEach(lvl => drawLine(lvl, true))
    supports.forEach(lvl    => drawLine(lvl, false))

  }, [priceLevels])

  // ── 鼠标移动：更新 Tooltip 坐标 ────────────────────────────────
  const handleMouseMove = useCallback((e) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    setTooltipPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    })
  }, [])

  const handleMouseLeave = useCallback(() => {
    setTooltipData(null)
    setTooltipPos(null)
  }, [])

  // ── 渲染 ────────────────────────────────────────────────────────
  return (
    <div
      style={{ position: 'relative', width: '100%', height: '100%' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {loading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.55)',
          color: 'var(--accent)', fontSize: 14, letterSpacing: 1,
        }}>
          ⟳ 加载中...
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* 均线图例（动态，根据 maConfig 渲染） */}
      <div style={{
        position: 'absolute', top: 8, left: 8, zIndex: 5,
        display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 11,
        pointerEvents: 'none',
      }}>
        {maConfig.map(({ key, color }) => (
          <span key={key} style={{ color, display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ display:'inline-block', width:14, height:2, background:color, borderRadius:1 }} />
            {key}
          </span>
        ))}
      </div>

      {/* 悬停浮动 Tooltip */}
      <KLineTooltip
        data={tooltipData}
        pos={tooltipPos}
        containerRef={containerRef}
      />
    </div>
  )
}
