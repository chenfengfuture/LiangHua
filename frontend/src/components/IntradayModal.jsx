/**
 * IntradayModal.jsx
 *
 * 日内行情弹窗：
 *   - 分时行情（折线图 + 成交量）
 *   - 逐笔成交（虚拟滚动列表）
 *
 * Props:
 *   symbol    – 股票代码
 *   name      – 股票名称
 *   date      – 'YYYY-MM-DD'
 *   prevClose – 昨收价（可为 null）
 *   onClose   – 关闭回调
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart, ColorType, CrosshairMode, LineSeries, HistogramSeries,
} from 'lightweight-charts'

const SSE_BASE = 'http://localhost:8001'

// ── 从 CSS 变量读取颜色（在图表初始化时调用）─────────────────
function getCSSVar(name, fallback = '') {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

// ── SSE 流式请求：返回 { cancel, promise }
// promise resolve({ minutes, transactions })，分时先到先 resolve 分时部分
// ─────────────────────────────────────────────────────────────
function openIntradayStream(symbol, date, limit = 0, callbacks = {}) {
  /**
   * callbacks:
   *   onMinutes(data)      – 分时数据就绪（先到）
   *   onTransactions(data) – 分笔数据就绪（后到）
   *   onDone(ms)           – 全部完成
   *   onError(msg)         – 错误
   * limit=0 表示获取全部分笔数据
   */
  const url = `${SSE_BASE}/api/intraday/${symbol}/stream?date_str=${encodeURIComponent(date)}&limit=${limit}`
  const es = new EventSource(url)

  es.addEventListener('minutes', e => {
    try {
      const payload = JSON.parse(e.data)
      callbacks.onMinutes?.(payload)
    } catch {}
  })

  es.addEventListener('transactions', e => {
    try {
      const payload = JSON.parse(e.data)
      callbacks.onTransactions?.(payload)
    } catch {}
  })

  es.addEventListener('done', e => {
    try {
      const payload = JSON.parse(e.data)
      callbacks.onDone?.(payload.ms)
    } catch {}
    es.close()
  })

  es.onerror = () => {
    callbacks.onError?.('SSE 连接失败')
    es.close()
  }

  return { cancel: () => es.close() }
}

// ── 预取缓存（鼠标悬停时提前触发，点击时直接用缓存结果）──────
// 预取时用 Promise 包装 SSE，结果 resolve 完整 { minutes, transactions }
const prefetchCache = new Map()   // key: `${symbol}|${date}` → Promise<{minutes,transactions}>

export function prefetchIntraday(symbol, date) {
  const key = `${symbol}|${date}`
  if (prefetchCache.has(key)) return

  const promise = new Promise((resolve) => {
    let minData = null, txData = null
    const tryResolve = () => {
      if (minData && txData) resolve({ minutes: minData, transactions: txData })
    }
    const { cancel } = openIntradayStream(symbol, date, 0, {  // limit=0 获取全部数据
      onMinutes:      d => { minData = d; tryResolve() },
      onTransactions: d => { txData  = d; tryResolve() },
      onDone:         () => {
        // 兜底：万一某路失败也要 resolve
        resolve({ minutes: minData || { data: [], error: '无数据' }, transactions: txData || { data: [], error: '无数据' } })
      },
      onError: () => {
        resolve({ minutes: { data: [], error: '连接失败' }, transactions: { data: [], error: '连接失败' } })
      },
    })
    // 20 秒超时兜底
    setTimeout(() => {
      cancel()
      resolve({ minutes: minData || { data: [], error: '超时' }, transactions: txData || { data: [], error: '超时' } })
    }, 20000)
  })

  prefetchCache.set(key, promise)

  // LRU：最多 30 条
  if (prefetchCache.size > 30) {
    prefetchCache.delete(prefetchCache.keys().next().value)
  }
}

// ── 分时折线图 ───────────────────────────────────────────────────
function MinutesChart({ rows, date, prevClose }) {
  const containerRef = useRef(null)
  const chartRef     = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el || !rows || rows.length === 0) return

    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }

    // 从 CSS 变量读取当前主题颜色
    const bgBase    = getCSSVar('--bg-base',    '#0d1117')
    const textNorm  = getCSSVar('--text-normal','#c9d1d9')
    const border    = getCSSVar('--border',     '#21262d')
    const accent    = getCSSVar('--accent',     '#58a6ff')
    const accentHov = getCSSVar('--accent-hover','#1f6feb')
    const textFaint = getCSSVar('--text-faint', '#6e7681')

    const chart = createChart(el, {
      width:  el.clientWidth  || 680,
      height: el.clientHeight || 280,
      layout: { background: { type: ColorType.Solid, color: bgBase }, textColor: textNorm, fontSize: 11 },
      grid:   { vertLines: { color: border }, horzLines: { color: border } },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: accent, width: 1, style: 2, labelBackgroundColor: accentHov },
        horzLine: { color: textFaint, labelBackgroundColor: accentHov },
      },
      rightPriceScale: { borderColor: border, scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: {
        borderColor: border, timeVisible: true,
        tickMarkFormatter: (ts) => {
          const d = new Date(ts * 1000)
          return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`
        },
      },
    })

    const priceLine = chart.addSeries(LineSeries, {
      color: accent, lineWidth: 1.5,
      priceLineVisible: false, lastValueVisible: true,
      crosshairMarkerVisible: true, crosshairMarkerRadius: 3,
    })
    const avgLine = chart.addSeries(LineSeries, {
      color: '#f9c74f', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    })
    const volSeries = chart.addSeries(HistogramSeries, {
      color: '#00B050', priceFormat: { type: 'volume' }, priceScaleId: 'vol',
    })
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } })

    if (prevClose) {
      priceLine.createPriceLine({
        price: prevClose, color: textFaint, lineWidth: 1, lineStyle: 2,
        axisLabelVisible: true, title: '昨收',
      })
    }

    const [yyyy, mo, dd] = date.split('-').map(Number)
    const priceData = [], avgData = [], volData = []
    rows.forEach(row => {
      const [hh, min] = row.time.split(':').map(Number)
      const ts = Date.UTC(yyyy, mo - 1, dd, hh, min, 0) / 1000
      priceData.push({ time: ts, value: row.price })
      avgData.push(  { time: ts, value: row.avg_price })
      const isUp = row.price >= (prevClose ?? row.price)
      volData.push({ time: ts, value: row.vol, color: isUp ? 'rgba(239,83,80,0.5)' : 'rgba(38,166,154,0.5)' })
    })

    priceLine.setData(priceData)
    avgLine.setData(avgData)
    volSeries.setData(volData)
    chart.timeScale().fitContent()
    chartRef.current = chart

    const ro = new ResizeObserver(() => {
      if (el && chartRef.current) {
        chartRef.current.applyOptions({ width: el.clientWidth, height: el.clientHeight })
      }
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [rows, date, prevClose])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <div style={{ position:'absolute', top:6, left:6, zIndex:5, display:'flex', gap:10, fontSize:11, pointerEvents:'none' }}>
        <span style={{ color:'var(--accent)' }}>
          <span style={{ display:'inline-block',width:12,height:2,background:'var(--accent)',verticalAlign:'middle',marginRight:3 }} />价格
        </span>
        <span style={{ color:'#f9c74f' }}>
          <span style={{ display:'inline-block',width:12,height:2,background:'#f9c74f',verticalAlign:'middle',marginRight:3 }} />均价
        </span>
        {prevClose && <span style={{ color:'var(--text-faint)' }}>昨收 {prevClose}</span>}
      </div>
    </div>
  )
}

// ── 逐笔成交（虚拟滚动）────────────────────────────────────────
const ROW_H = 26

function TransactionTable({ rows }) {
  const scrollRef    = useRef(null)
  const [scrollTop,  setScrollTop]  = useState(0)
  const [viewHeight, setViewHeight] = useState(380)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    setViewHeight(el.clientHeight)
    const ro = new ResizeObserver(() => setViewHeight(el.clientHeight))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // 新数据到来时滚到底部（最新成交在下方）
  useEffect(() => {
    const el = scrollRef.current
    if (el && rows?.length > 0) el.scrollTop = el.scrollHeight
  }, [rows])

  const onScroll = useCallback(e => setScrollTop(e.currentTarget.scrollTop), [])

  if (!rows || rows.length === 0) {
    return <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100%', color:'var(--text-faint)', fontSize:12 }}>暂无分笔数据</div>
  }

  const start  = Math.max(0, Math.floor(scrollTop / ROW_H) - 5)
  const end    = Math.min(rows.length, Math.ceil((scrollTop + viewHeight) / ROW_H) + 5)
  const visible = rows.slice(start, end)
  const padTop  = start * ROW_H
  const padBot  = (rows.length - end) * ROW_H

  const COL = '64px 80px 72px 48px'

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      {/* 表头 */}
      <div style={{ display:'grid', gridTemplateColumns:COL, padding:'5px 10px', background:'var(--bg-surface)', borderBottom:'1px solid var(--border)', flexShrink:0, fontSize:11, color:'var(--text-faint)', fontWeight:600 }}>
        <span>时间</span>
        <span style={{ textAlign:'right' }}>价格</span>
        <span style={{ textAlign:'right' }}>手数</span>
        <span style={{ textAlign:'center' }}>买卖</span>
      </div>
      {/* 虚拟滚动体 */}
      <div ref={scrollRef} onScroll={onScroll} style={{ flex:1, overflowY:'auto' }}>
        {padTop > 0 && <div style={{ height: padTop }} />}
        {visible.map((row, i) => {
          const isB = row.side === 'B'
          const isS = row.side === 'S'
          const color = isB ? '#FF0000' : isS ? '#00B050' : 'var(--text-muted)'
          const idx = start + i
          return (
            <div key={idx} style={{
              display:'grid', gridTemplateColumns:COL,
              height:ROW_H, padding:'0 10px', fontSize:12,
              alignItems:'center', borderBottom:'1px solid var(--bg-base)',
              background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.018)',
            }}>
              <span style={{ color:'var(--text-muted)' }}>{row.time}</span>
              <span style={{ textAlign:'right', color }}>{row.price?.toFixed(2)}</span>
              <span style={{ textAlign:'right', color:'var(--text-normal)' }}>{row.vol}</span>
              <span style={{ textAlign:'center' }}>
                <span style={{
                  display:'inline-block', padding:'1px 5px',
                  background: isB ? 'rgba(239,83,80,0.15)' : isS ? 'rgba(38,166,154,0.15)' : 'transparent',
                  color, borderRadius:3, fontSize:11, fontWeight:600,
                }}>{isB ? '买' : isS ? '卖' : '中'}</span>
              </span>
            </div>
          )
        })}
        {padBot > 0 && <div style={{ height: padBot }} />}
      </div>
    </div>
  )
}

// ── 通用 Loading / Error ──────────────────────────────────────
function Loading({ text = '加载中...' }) {
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100%', color:'var(--accent)', fontSize:14, gap:8 }}>
      <span style={{ display:'inline-block', animation:'spin 1s linear infinite' }}>⟳</span>{text}
    </div>
  )
}
function Err({ text }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap:8 }}>
      <span style={{ fontSize:28 }}>⚠</span>
      <span style={{ color:'#f85149', fontSize:13 }}>{text}</span>
    </div>
  )
}

// ── 主弹窗 ───────────────────────────────────────────────────────
export default function IntradayModal({ symbol, name, date, prevClose, onClose }) {
  const [tab,          setTab]       = useState('minutes')
  const [minRows,      setMinRows]   = useState([])
  const [transRows,    setTransRows] = useState([])
  const [minLoading,   setMinLoading]   = useState(true)   // 分时 loading（独立）
  const [transLoading, setTransLoading] = useState(true)   // 分笔 loading（独立）
  const [minErr,       setMinErr]    = useState('')
  const [transErr,     setTransErr]  = useState('')
  const cancelRef = useRef(null)   // SSE cancel 句柄

  // ── 拉取数据：SSE 流式，分时先到先渲染 ──
  useEffect(() => {
    // 重置状态
    setMinRows([]); setTransRows([])
    setMinErr('');  setTransErr('')
    setMinLoading(true); setTransLoading(true)

    // 取消上一次未完成的 SSE
    cancelRef.current?.()

    const key = `${symbol}|${date}`

    if (prefetchCache.has(key)) {
      // ── 命中预取缓存：Promise 模式（可能已完成，也可能还在进行中）
      prefetchCache.get(key).then(res => {
        const mdata = res.minutes?.data || []
        const tdata = res.transactions?.data || []
        if (mdata.length === 0) setMinErr(res.minutes?.error || '暂无分时数据')
        else setMinRows(mdata)
        setMinLoading(false)
        if (tdata.length === 0) setTransErr(res.transactions?.error || '暂无分笔数据')
        else setTransRows(tdata)
        setTransLoading(false)
      }).catch(() => {
        setMinErr('获取失败'); setTransErr('获取失败')
        setMinLoading(false); setTransLoading(false)
      })
      return
    }

    // ── 未命中：直接开 SSE，分时先推先渲染
    const { cancel } = openIntradayStream(symbol, date, 0, {  // limit=0 获取全部数据
      onMinutes: (payload) => {
        const data = payload.data || []
        if (data.length === 0) setMinErr(payload.error || '暂无分时数据')
        else setMinRows(data)
        setMinLoading(false)   // ← 分时先 ready，立刻解除 loading
      },
      onTransactions: (payload) => {
        const data = payload.data || []
        if (data.length === 0) setTransErr(payload.error || '暂无分笔数据')
        else setTransRows(data)
        setTransLoading(false) // ← 分笔后 ready
      },
      onDone: () => {
        // 兜底：确保两个 loading 都关闭
        setMinLoading(false); setTransLoading(false)
      },
      onError: (msg) => {
        setMinErr(msg); setTransErr(msg)
        setMinLoading(false); setTransLoading(false)
      },
    })
    cancelRef.current = cancel

    return () => { cancel() }   // 弹窗关闭时取消 SSE
  }, [symbol, date])

  // ESC 关闭
  useEffect(() => {
    const h = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  // 买卖比
  const buyVol  = transRows.filter(r => r.side === 'B').reduce((s, r) => s + r.vol, 0)
  const sellVol = transRows.filter(r => r.side === 'S').reduce((s, r) => s + r.vol, 0)
  const buyRatio = Math.round(buyVol / ((buyVol + sellVol) || 1) * 100)

  return (
    <div
      style={{
        position:'fixed', inset:0, zIndex:2000,
        background:'rgba(0,0,0,0.78)',
        display:'flex', alignItems:'center', justifyContent:'center',
      }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        width:'84vw', maxWidth:1020, height:'82vh', maxHeight:720,
        background:'var(--bg-base)', borderRadius:10, border:'1px solid var(--border-muted)',
        display:'flex', flexDirection:'column', overflow:'hidden',
        boxShadow:'0 24px 80px rgba(0,0,0,0.85)',
      }}>

        {/* 头部 */}
        <div style={{
          display:'flex', alignItems:'center', justifyContent:'space-between',
          padding:'12px 20px', borderBottom:'1px solid var(--border)',
          background:'var(--bg-surface)', flexShrink:0,
        }}>
          <div style={{ display:'flex', alignItems:'center', gap:14 }}>
            <div>
              <span style={{ color:'var(--text-primary)', fontWeight:700, fontSize:16 }}>{name}</span>
              <span style={{ color:'var(--text-faint)', fontSize:12, marginLeft:8 }}>({symbol})</span>
            </div>
            <span style={{ color:'var(--text-faint)', fontSize:13 }}>📅 {date} · 日内行情</span>
            {prevClose && <span style={{ color:'var(--text-muted)', fontSize:12 }}>昨收 {prevClose?.toFixed(2)}</span>}
          </div>
          <button
            onClick={onClose}
            style={{ background:'none', border:'none', color:'var(--text-faint)', cursor:'pointer', fontSize:20, lineHeight:1, padding:'2px 8px', borderRadius:4 }}
            onMouseEnter={e => e.currentTarget.style.color='var(--text-primary)'}
            onMouseLeave={e => e.currentTarget.style.color='var(--text-faint)'}
          >✕</button>
        </div>

        {/* Tab 栏 */}
        <div style={{
          display:'flex', alignItems:'center',
          borderBottom:'1px solid var(--border)', padding:'0 20px',
          background:'var(--bg-surface)', flexShrink:0, gap:4,
        }}>
          {/* 分时 Tab：有自己的 loading 圈 */}
          <button onClick={() => setTab('minutes')} style={{
            background:'none', border:'none',
            borderBottom: tab === 'minutes' ? '2px solid var(--accent)' : '2px solid transparent',
            color: tab === 'minutes' ? 'var(--accent)' : 'var(--text-faint)',
            padding:'8px 16px', fontSize:13, cursor:'pointer',
            fontWeight: tab === 'minutes' ? 600 : 400,
            display:'flex', alignItems:'center', gap:4,
          }}>
            📈 分时行情
            {minLoading
              ? <span style={{ animation:'spin 1s linear infinite', display:'inline-block', fontSize:11 }}>⟳</span>
              : <span style={{ fontSize:11, opacity:0.7 }}>({minRows.length}条)</span>
            }
          </button>

          {/* 分笔 Tab：有自己的 loading 圈 */}
          <button onClick={() => setTab('trans')} style={{
            background:'none', border:'none',
            borderBottom: tab === 'trans' ? '2px solid var(--accent)' : '2px solid transparent',
            color: tab === 'trans' ? 'var(--accent)' : 'var(--text-faint)',
            padding:'8px 16px', fontSize:13, cursor:'pointer',
            fontWeight: tab === 'trans' ? 600 : 400,
            display:'flex', alignItems:'center', gap:4,
          }}>
            📋 逐笔成交
            {transLoading
              ? <span style={{ animation:'spin 1s linear infinite', display:'inline-block', fontSize:11 }}>⟳</span>
              : <span style={{ fontSize:11, opacity:0.7 }}>({transRows.length}条)</span>
            }
          </button>

          {/* 买卖比 */}
          {!transLoading && transRows.length > 0 && (
            <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8, fontSize:11, color:'var(--text-muted)' }}>
              <span style={{ color:'#FF0000' }}>买 {buyRatio}%</span>
              <div style={{ width:72, height:6, background:'#00B050', borderRadius:3, overflow:'hidden' }}>
                <div style={{ width:`${buyRatio}%`, height:'100%', background:'#FF0000' }} />
              </div>
              <span style={{ color:'#00B050' }}>卖 {100 - buyRatio}%</span>
            </div>
          )}
        </div>

        {/* 内容区：两个 Tab 各自独立 loading */}
        <div style={{ flex:1, overflow:'hidden', position:'relative' }}>
          {tab === 'minutes' && (
            minLoading ? <Loading text="加载分时数据..." />
            : minErr    ? <Err text={minErr} />
            : <div style={{ width:'100%', height:'100%' }}>
                <MinutesChart rows={minRows} date={date} prevClose={prevClose} />
              </div>
          )}
          {tab === 'trans' && (
            transLoading ? <Loading text="加载分笔数据..." />
            : transErr    ? <Err text={transErr} />
            : <div style={{ width:'100%', height:'100%' }}>
                <TransactionTable rows={transRows} />
              </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg) } }
      `}</style>
    </div>
  )
}
