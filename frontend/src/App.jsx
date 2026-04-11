import { useState, useEffect, useCallback, useRef } from 'react'
import KLineChart       from './components/KLineChart'
import StockSearch      from './components/StockSearch'
import StockInfoBar     from './components/StockInfoBar'
import HotStocksPanel   from './components/HotStocksPanel'
import MarketOverview   from './components/MarketOverview'
import NewsPage         from './components/NewsPage'
import {
  getKlines, getMA, getStockInfo,
  getMarketOverview, getHotStocks,
  triggerCollect, getCollectStatus,
  getPriceLevels,
} from './api/stocks'

// ── 预设主题 ───────────────────────────────────────────────────────────────
const THEMES = [
  {
    id: 'dark',
    name: '暗夜',
    icon: '🌑',
    vars: {
      '--bg-base':      '#0d1117',
      '--bg-surface':   '#161b22',
      '--bg-elevated':  '#21262d',
      '--bg-input':     '#0d1117',
      '--border':       '#21262d',
      '--border-muted': '#30363d',
      '--text-primary': '#f0f6fc',
      '--text-normal':  '#c9d1d9',
      '--text-muted':   '#8b949e',
      '--text-faint':   '#6e7681',
      '--text-faintest':'#444c56',
      '--accent':       '#58a6ff',
      '--accent-hover': '#1f6feb',
      '--scrollbar-track': '#161b22',
      '--scrollbar-thumb': '#30363d',
      '--scrollbar-thumb-hover': '#484f58',
    },
  },
  {
    id: 'blue',
    name: '深蓝',
    icon: '🌊',
    vars: {
      '--bg-base':      '#060d18',
      '--bg-surface':   '#0a1628',
      '--bg-elevated':  '#122035',
      '--bg-input':     '#060d18',
      '--border':       '#112035',
      '--border-muted': '#1a3050',
      '--text-primary': '#e8f4fd',
      '--text-normal':  '#b8d4f0',
      '--text-muted':   '#6a9cc0',
      '--text-faint':   '#3d6080',
      '--text-faintest':'#2a4060',
      '--accent':       '#4db8ff',
      '--accent-hover': '#0d7ed4',
      '--scrollbar-track': '#0a1628',
      '--scrollbar-thumb': '#1a3050',
      '--scrollbar-thumb-hover': '#2a4870',
    },
  },
  {
    id: 'green',
    name: '墨绿',
    icon: '🌿',
    vars: {
      '--bg-base':      '#060f0a',
      '--bg-surface':   '#0a1810',
      '--bg-elevated':  '#102218',
      '--bg-input':     '#060f0a',
      '--border':       '#102218',
      '--border-muted': '#1a3828',
      '--text-primary': '#e8f5ec',
      '--text-normal':  '#a8d8b8',
      '--text-muted':   '#5a9870',
      '--text-faint':   '#376050',
      '--text-faintest':'#204030',
      '--accent':       '#3ddc84',
      '--accent-hover': '#0d8c44',
      '--scrollbar-track': '#0a1810',
      '--scrollbar-thumb': '#1a3828',
      '--scrollbar-thumb-hover': '#2a5840',
    },
  },
  {
    id: 'purple',
    name: '深紫',
    icon: '🔮',
    vars: {
      '--bg-base':      '#0c0814',
      '--bg-surface':   '#150e22',
      '--bg-elevated':  '#1e1530',
      '--bg-input':     '#0c0814',
      '--border':       '#1e1530',
      '--border-muted': '#2e2048',
      '--text-primary': '#f0eaff',
      '--text-normal':  '#c8b8e8',
      '--text-muted':   '#8070a8',
      '--text-faint':   '#504070',
      '--text-faintest':'#342850',
      '--accent':       '#a78bfa',
      '--accent-hover': '#6d28d9',
      '--scrollbar-track': '#150e22',
      '--scrollbar-thumb': '#2e2048',
      '--scrollbar-thumb-hover': '#4e3868',
    },
  },
  {
    id: 'eyecare',
    name: '护眼',
    icon: '🍃',
    vars: {
      '--bg-base':      '#1a1f1a',
      '--bg-surface':   '#222820',
      '--bg-elevated':  '#2a3028',
      '--bg-input':     '#1a1f1a',
      '--border':       '#2a3028',
      '--border-muted': '#384038',
      '--text-primary': '#e8ede0',
      '--text-normal':  '#c0cbb8',
      '--text-muted':   '#7a8c70',
      '--text-faint':   '#506050',
      '--text-faintest':'#384038',
      '--accent':       '#8ec07c',
      '--accent-hover': '#5a8c4a',
      '--scrollbar-track': '#222820',
      '--scrollbar-thumb': '#384038',
      '--scrollbar-thumb-hover': '#4a584a',
    },
  },
  {
    id: 'light',
    name: '浅色',
    icon: '☀️',
    vars: {
      '--bg-base':      '#f6f8fa',
      '--bg-surface':   '#ffffff',
      '--bg-elevated':  '#eaeef2',
      '--bg-input':     '#ffffff',
      '--border':       '#d0d7de',
      '--border-muted': '#c6cdd4',
      '--text-primary': '#1f2328',
      '--text-normal':  '#30363d',
      '--text-muted':   '#636c76',
      '--text-faint':   '#8c959f',
      '--text-faintest':'#adb5bd',
      '--accent':       '#0969da',
      '--accent-hover': '#0550ae',
      '--scrollbar-track': '#eaeef2',
      '--scrollbar-thumb': '#c6cdd4',
      '--scrollbar-thumb-hover': '#9ea7b0',
    },
  },
]

const STORED_THEME_KEY = 'lhTheme'
const STORED_HUE_KEY   = 'lhHueShift'
const STORED_BRIGHT_KEY = 'lhBrightness'

/** 将主题 vars + 亮度应用到 :root（不做色调旋转，避免影响 K 线涨红跌绿） */
function applyTheme(themeId, _hueShift, brightness) {
  const theme = THEMES.find(t => t.id === themeId) || THEMES[0]
  const root  = document.documentElement
  Object.entries(theme.vars).forEach(([k, v]) => {
    root.style.setProperty(k, v)
  })
  root.style.setProperty('--theme-brightness', brightness ?? 1)
  // 仅做亮度调整，不做色调旋转（hue-rotate 会让涨红/跌绿变色）
  const rootEl = document.getElementById('root')
  if (rootEl) {
    const b = brightness ?? 1
    rootEl.style.filter = b !== 1 ? `brightness(${b})` : ''
  }
}

const RANGE_OPTIONS = [
  { label: '1月',  days: 30   },
  { label: '3月',  days: 90   },
  { label: '6月',  days: 180  },
  { label: '1年',  days: 365  },
  { label: '3年',  days: 1095 },
  { label: '5年',  days: 1825 },
  { label: '全部', days: 9999 },
]

// 固定均线定义（MA5/10/20/60）
const FIXED_MA = [
  { key: 'MA5',  period: 5,   color: '#ff9800' },
  { key: 'MA10', period: 10,  color: '#2196f3' },
  { key: 'MA20', period: 20,  color: '#e91e63' },
  { key: 'MA60', period: 60,  color: '#9c27b0' },
]

// 自定义均线可选颜色
const CUSTOM_MA_COLORS = ['#00e5ff', '#69f0ae', '#ffeb3b', '#ff4081', '#b39ddb', '#ff6d00']

// 默认自定义均线列表（取代 MA120/MA250）
const DEFAULT_CUSTOM_MAS = [
  { period: 55, color: '#00e5ff', enabled: true },
]

function dateOffsetStr(days) {
  const d = new Date()
  if (days >= 9999) return '1990-01-01'
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function fmt(v, digits = 2) {
  if (v == null) return '--'
  return typeof v === 'number' ? v.toFixed(digits) : v
}

function fmtVol(v) {
  if (v == null) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿手'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万手'
  return v.toFixed(0) + '手'
}

function fmtAmt(v) {
  if (v == null) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(0)
}

// 悬停/点击后右侧面板显示的日线详情
function DetailPanel({ hoverBar, loading, stockName, priceLevels, levelsLoading }) {
  const display = hoverBar

  if (!display && !loading) {
    return (
      <div style={{ overflowY: 'auto', height: '100%' }}>
        <div style={{ padding: 20, color: 'var(--text-faint)', fontSize: 12, textAlign: 'center', lineHeight: 2 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📊</div>
          <div>移动鼠标到K线上查看数据</div>
          <div style={{ color: 'var(--text-faintest)', marginTop: 4 }}>点击K线查看日内行情</div>
        </div>
        {/* 压力位面板（即使没有悬停也显示） */}
        <LevelsSidePanel priceLevels={priceLevels} levelsLoading={levelsLoading} />
      </div>
    )
  }

  const isUp = (display?.close ?? 0) >= (display?.open ?? 0)
  const priceColor = isUp ? '#FF0000' : '#00B050'

  const rows = [
    ['开盘', fmt(display?.open)],
    ['收盘', fmt(display?.close)],
    ['最高', fmt(display?.high)],
    ['最低', fmt(display?.low)],
    ['成交量', fmtVol(display?.vol)],
  ]

  return (
    <div style={{ overflowY: 'auto', height: '100%' }}>
      <div style={{
        padding: '10px 14px 6px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{display?.time}</div>
          <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600 }}>{stockName}</div>
        </div>
        <div style={{ color: priceColor, fontSize: 20, fontWeight: 700 }}>
          {fmt(display?.close)}
        </div>
      </div>
      <div style={{ padding: '6px 14px' }}>
        {rows.map(([k, v]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '4px 0', borderBottom: '1px solid var(--bg-base)', fontSize: 12,
          }}>
            <span style={{ color: 'var(--text-faint)' }}>{k}</span>
            <span style={{ color: 'var(--text-normal)' }}>{v}</span>
          </div>
        ))}
      </div>
      {display?.maValues && (
        <div style={{ padding: '8px 14px 0' }}>
          <div style={{ color: 'var(--text-faintest)', fontSize: 11, marginBottom: 4 }}>均线</div>
          {Object.entries(display.maValues).map(([name, val]) => {
            const fixedDef = FIXED_MA.find(m => m.key === name)
            const color = fixedDef?.color ?? 'var(--text-muted)'
            if (val == null) return null
            return (
              <div key={name} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '3px 0', borderBottom: '1px solid var(--bg-base)', fontSize: 12,
              }}>
                <span style={{ color }}>{name}</span>
                <span style={{ color: 'var(--text-normal)' }}>{fmt(val)}</span>
              </div>
            )
          })}
        </div>
      )}
      {loading && (
        <div style={{ padding: 12, color: 'var(--accent)', fontSize: 12, textAlign: 'center' }}>⟳ 加载中...</div>
      )}
      {/* 压力位面板 */}
      <LevelsSidePanel priceLevels={priceLevels} levelsLoading={levelsLoading} />
    </div>
  )
}

// 压力位/支撑位侧面板子组件
function LevelsSidePanel({ priceLevels, levelsLoading }) {
  if (levelsLoading) {
    return (
      <div style={{ padding: '10px 14px', color: 'var(--accent)', fontSize: 11, textAlign: 'center' }}>
        ⟳ 正在计算压力位…
      </div>
    )
  }
  if (!priceLevels) return null

  const { summary, current } = priceLevels
  const resistance = summary?.resistance || []
  const support    = summary?.support    || []

  const methodColor = { pivot: '#f0b429', local: '#ffffff', ma: '#00bcd4', fib: '#ce93d8' }
  const methodLabel = { pivot: '枢轴', local: '极值', ma: '均线', fib: 'Fib' }

  const renderRow = (lvl, isRes) => {
    const color = methodColor[lvl.method] ?? '#888'
    const diff  = current ? ((lvl.price - current) / current * 100).toFixed(2) : null
    return (
      <div key={lvl.label + lvl.price} style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '4px 0', borderBottom: '1px solid var(--bg-base)', fontSize: 11,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
          <span style={{
            color, fontSize: 9, padding: '1px 4px',
            border: `1px solid ${color}40`, borderRadius: 3,
            flexShrink: 0,
          }}>{methodLabel[lvl.method] ?? lvl.method}</span>
          <span style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lvl.label}</span>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 4 }}>
          <span style={{ color: isRes ? '#FF0000' : '#00B050', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {lvl.price.toFixed(2)}
          </span>
          {diff != null && (
            <span style={{ color: 'var(--text-faintest)', fontSize: 9, display: 'block' }}>
              {isRes ? '+' : ''}{diff}%
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '8px 14px', borderTop: '1px solid var(--border)', marginTop: 4 }}>
      {resistance.length > 0 && (
        <>
          <div style={{ color: '#FF0000', fontSize: 10, fontWeight: 600, marginBottom: 5, letterSpacing: 0.5 }}>
            ▲ 上方压力位
          </div>
          {resistance.slice(0, 4).map(lvl => renderRow(lvl, true))}
        </>
      )}
      {support.length > 0 && (
        <>
          <div style={{ color: '#00B050', fontSize: 10, fontWeight: 600, margin: '8px 0 5px', letterSpacing: 0.5 }}>
            ▽ 下方支撑位
          </div>
          {support.slice(0, 4).map(lvl => renderRow(lvl, false))}
        </>
      )}
      <div style={{ color: 'var(--text-faintest)', fontSize: 9, marginTop: 6, lineHeight: 1.5 }}>
        枢轴: 同花顺Pivot法 | 极值: 近{priceLevels.n_local}日高低点 | Fib: 斐波那契
      </div>
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('chart') // 'chart' | 'news'
  const [symbol,     setSymbol]     = useState('300059')
  const [stockName,  setStockName]  = useState('东方财富')
  const [range,      setRange]      = useState(1)
  const [candles,    setCandles]    = useState([])
  const [volumes,    setVolumes]    = useState([])
  const [maData,     setMaData]     = useState({})
  const [stockInfo,  setStockInfo]  = useState(null)
  const [overview,   setOverview]   = useState(null)
  const [hot,        setHot]        = useState({ data: [], date: '' })
  const [loading,    setLoading]    = useState(false)
  const [sideTab,    setSideTab]    = useState('hot')
  const [hoverBar,   setHoverBar]   = useState(null)
  // 自定义均线列表
  const [customMAs,  setCustomMAs]  = useState(DEFAULT_CUSTOM_MAS)
  // 自定义均线编辑弹窗
  const [showMAEditor, setShowMAEditor] = useState(false)
  // 采集面板
  const [showCollect,    setShowCollect]    = useState(false)
  const [collectStatus,  setCollectStatus]  = useState(null)
  const [collectPolling, setCollectPolling] = useState(false)
  // 主题面板
  const [showTheme,  setShowTheme]  = useState(false)
  const [themeId,    setThemeId]    = useState(() => localStorage.getItem(STORED_THEME_KEY)    || 'dark')
  const [hueShift,   setHueShift]   = useState(() => Number(localStorage.getItem(STORED_HUE_KEY))    || 0)
  const [brightness, setBrightness] = useState(() => Number(localStorage.getItem(STORED_BRIGHT_KEY)) || 1)
  // chartKey：主题切换时自增，让 KLineChart 重新初始化（读取新的 CSS 变量颜色）
  const [chartKey,   setChartKey]   = useState(0)
  // 初始化主题（mount 时）
  useEffect(() => { applyTheme(themeId, hueShift, brightness) }, [])

  // 压力位 / 支撑位
  const [priceLevels,     setPriceLevels]     = useState(null)   // 当前已加载的压力位数据
  const [showLevels,      setShowLevels]      = useState(false)  // 是否在图上显示
  const [levelsLoading,   setLevelsLoading]   = useState(false)  // 请求中

  // ── 弹窗状态（全部集中在此，清晰管理）──
  const [modal, setModal] = useState({
    visible: false,
    symbol:  '',
    name:    '',
    date:    '',
    prevClose: null,
  })

  const symbolRef = useRef(symbol)
  const nameRef   = useRef(stockName)
  useEffect(() => { symbolRef.current = symbol    }, [symbol])
  useEffect(() => { nameRef.current   = stockName }, [stockName])

  // 加载K线（customMAs 变化也触发）
  const loadChart = useCallback(async (sym, rangeIdx, cMAs) => {
    if (!sym) return
    setLoading(true)
    try {
      const days      = RANGE_OPTIONS[rangeIdx].days
      const startDate = dateOffsetStr(days + 300)
      const endDate   = todayStr()
      const limit     = days >= 9999 ? 3000 : Math.min(days * 2, 3000)

      // 构建 periods 字符串：固定 MA + 启用的自定义 MA
      const fixedPeriods  = FIXED_MA.map(m => m.period)
      const customPeriods = (cMAs || []).filter(m => m.enabled).map(m => m.period)
      const allPeriods    = [...new Set([...fixedPeriods, ...customPeriods])].join(',')

      const [klineRes, maRes] = await Promise.all([
        getKlines(sym, startDate, endDate, limit),
        getMA(sym, startDate, endDate, allPeriods, limit),
      ])
      setCandles(klineRes.candles || [])
      setVolumes(klineRes.volumes || [])
      setMaData(maRes.ma || {})
    } catch (err) {
      console.error('加载K线失败', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadInfo = useCallback(async (sym) => {
    try {
      const info = await getStockInfo(sym)
      setStockInfo(info)
      setStockName(info.name || sym)
    } catch {}
  }, [])

  // 加载压力位（symbol 变化时清除旧数据）
  const loadLevels = useCallback(async (sym) => {
    setLevelsLoading(true)
    try {
      const data = await getPriceLevels(sym, 60, 120)
      setPriceLevels(data)
    } catch (err) {
      console.error('压力位加载失败', err)
      setPriceLevels(null)
    } finally {
      setLevelsLoading(false)
    }
  }, [])

  // symbol 切换时清除压力位显示
  useEffect(() => {
    setPriceLevels(null)
    setShowLevels(false)
  }, [symbol])

  useEffect(() => {
    getMarketOverview().then(setOverview).catch(() => {})
    getHotStocks(null, 20).then(res => setHot({ data: res.data || [], date: res.date || '' })).catch(() => {})
  }, [])

  useEffect(() => {
    loadChart(symbol, range, customMAs)
    loadInfo(symbol)
  }, [symbol, range, customMAs, loadChart, loadInfo])

  // 悬停 → 右侧面板实时更新
  const handleCandleHover = useCallback((barData) => {
    setHoverBar(barData)
  }, [])

  // 点击K线 → 打开弹窗
  const handleCandleClick = useCallback((barData, allCandles) => {
    const sym  = symbolRef.current
    const name = nameRef.current
    const date = barData.time

    // 从传入的 candles 里查昨收
    const idx       = allCandles.findIndex(c => c.time === date)
    const prevClose = idx > 0 ? allCandles[idx - 1].close : null

    setModal({ visible: true, symbol: sym, name, date, prevClose })
  }, [])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100vh',
      background: 'var(--bg-base)', color: 'var(--text-normal)',
      fontFamily: "'SF Pro Display', 'PingFang SC', sans-serif",
      overflow: 'hidden',
    }}>

      {/* ── 顶部导航 ── */}
      <header style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '0 16px', height: 48,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)', flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" stroke="var(--accent)" strokeWidth="2.5" fill="none"/>
            <polyline points="16 7 22 7 22 13"              stroke="var(--accent)" strokeWidth="2" fill="none"/>
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: 15, letterSpacing: 0.5 }}>量华</span>
            <span style={{ color: 'var(--text-faint)', fontSize: 9 }}>量化平台</span>
          </div>
        </div>

        {/* 导航按钮组 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
          {/* 股票板块按钮 */}
          <button
            onClick={() => setPage('chart')}
            style={{
              background: page === 'chart' ? 'var(--accent-hover)' : 'var(--bg-elevated)',
              border: '1px solid ' + (page === 'chart' ? 'var(--accent)' : 'var(--border-muted)'),
              color: page === 'chart' ? 'var(--text-primary)' : 'var(--text-muted)',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 13,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontWeight: page === 'chart' ? 600 : 400,
              transition: 'all 0.2s',
            }}
          >
            <span style={{ fontSize: 14 }}>📈</span>
            <span>股票</span>
          </button>

          {/* 新闻板块按钮 */}
          <button
            onClick={() => setPage('news')}
            style={{
              background: page === 'news' ? 'var(--accent-hover)' : 'var(--bg-elevated)',
              border: '1px solid ' + (page === 'news' ? 'var(--accent)' : 'var(--border-muted)'),
              color: page === 'news' ? 'var(--text-primary)' : 'var(--text-muted)',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 13,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontWeight: page === 'news' ? 600 : 400,
              transition: 'all 0.2s',
            }}
          >
            <span style={{ fontSize: 14 }}>📰</span>
            <span>新闻</span>
          </button>
        </div>

        <div style={{ marginLeft: 'auto' }}>
          <MarketOverview overview={overview} />
        </div>
      </header>

      {/* ── 主体 ── */}
      <div style={{ flex: 1, display: 'flex', overflow: page === 'news' ? 'auto' : 'hidden' }}>
        {page === 'news' ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <NewsPage onSwitchToChart={() => setPage('chart')} />
          </div>
        ) : (
        <>
        {/* 左侧面板 */}
        <div style={{
          width: 260, borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column',
          background: 'var(--bg-base)', flexShrink: 0,
        }}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <StockSearch onSelect={s => { setSymbol(s.symbol); setStockName(s.name) }} />
          </div>
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            {[['hot','热门榜'],['info','基本面'],['detail','日线']].map(([key, label]) => (
              <button key={key} onClick={() => setSideTab(key)} style={{
                flex: 1, padding: '9px 0', background: 'none', border: 'none',
                borderBottom: sideTab === key ? '2px solid var(--accent)' : '2px solid transparent',
                color: sideTab === key ? 'var(--accent)' : 'var(--text-faint)',
                fontSize: 13, cursor: 'pointer',
                fontWeight: sideTab === key ? 600 : 400,
              }}>{label}</button>
            ))}
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {sideTab === 'hot' && (
              <HotStocksPanel
                data={hot.data} date={hot.date} currentSymbol={symbol}
                onSelect={s => { setSymbol(s.symbol); setStockName(s.name) }}
              />
            )}
            {sideTab === 'info' && stockInfo && (
              <div style={{ padding: '12px 14px', fontSize: 13, lineHeight: 1.8, overflowY: 'auto', height: '100%' }}>
                {[
                  ['股票代码', stockInfo.symbol],
                  ['股票名称', stockInfo.name],
                  ['所属市场', stockInfo.market],
                  ['上市日期', stockInfo.list_date],
                  ['最新收盘', stockInfo.last_price],
                  ['最新日期', stockInfo.last_date],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', padding: '5px 0' }}>
                    <span style={{ color: 'var(--text-faint)' }}>{k}</span>
                    <span style={{ color: 'var(--text-normal)', fontWeight: 500 }}>{v ?? '--'}</span>
                  </div>
                ))}
              </div>
            )}
            {sideTab === 'info' && !stockInfo && (
              <div style={{ padding: 20, color: 'var(--text-faint)', fontSize: 13, textAlign: 'center' }}>暂无数据</div>
            )}
            {sideTab === 'detail' && (
              <DetailPanel hoverBar={hoverBar} loading={false} stockName={stockName} priceLevels={priceLevels} levelsLoading={levelsLoading} />
            )}
          </div>
        </div>

        {/* 右侧图表区 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <StockInfoBar info={stockInfo} />
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '8px 16px', background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)', flexShrink: 0,
          }}>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 14 }}>{stockName}</span>
            <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>({symbol}) · 日K线</span>
            <div style={{ display: 'flex', gap: 4, marginLeft: 8 }}>
              {RANGE_OPTIONS.map((opt, idx) => (
                <button key={idx} onClick={() => setRange(idx)} style={{
                  background: range === idx ? 'var(--accent-hover)' : 'transparent',
                  border: '1px solid ' + (range === idx ? 'var(--accent)' : 'var(--border-muted)'),
                  color: range === idx ? 'var(--text-primary)' : 'var(--text-muted)',
                  borderRadius: 4, padding: '3px 10px', fontSize: 12, cursor: 'pointer',
                }}>{opt.label}</button>
              ))}
            </div>
            {/* 均线设置按钮 */}
            <button
              onClick={() => setShowMAEditor(true)}
              title="均线设置"
              style={{
                background: 'transparent',
                border: '1px solid var(--border-muted)',
                color: 'var(--text-muted)', borderRadius: 4,
                padding: '3px 10px', fontSize: 12, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{ fontSize: 13 }}>〰</span> 均线
              {customMAs.filter(m => m.enabled).length > 0 && (
                <span style={{
                  background: 'var(--accent-hover)', color: 'var(--text-primary)',
                  borderRadius: 10, fontSize: 10,
                  padding: '0 4px', lineHeight: '14px',
                }}>
                  +{customMAs.filter(m => m.enabled).length}
                </span>
              )}
            </button>
            {/* 数据采集按钮 */}
            <button
              onClick={() => { setShowCollect(true); getCollectStatus().then(setCollectStatus).catch(() => {}) }}
              title="手动触发收盘数据采集"
              style={{
                background: collectStatus?.running ? '#1a3a1a' : 'transparent',
                border: '1px solid ' + (collectStatus?.running ? '#2ea043' : 'var(--border-muted)'),
                color: collectStatus?.running ? '#56d364' : 'var(--text-muted)',
                borderRadius: 4, padding: '3px 10px', fontSize: 12, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{ fontSize: 13 }}>⬇</span>
              {collectStatus?.running ? '采集中…' : '采集'}
            </button>
            {/* 主题切换按钮 */}
            <button
              onClick={() => setShowTheme(v => !v)}
              title="切换页面主题色调"
              style={{
                background: showTheme ? 'var(--accent-hover)' : 'transparent',
                border: '1px solid ' + (showTheme ? 'var(--accent)' : 'var(--border-muted)'),
                color: showTheme ? 'var(--text-primary)' : 'var(--text-muted)',
                borderRadius: 4, padding: '3px 10px', fontSize: 12, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{ fontSize: 13 }}>🎨</span> 主题
            </button>
            {/* 压力位/支撑位按钮 */}
            <button
              onClick={async () => {
                if (showLevels) {
                  setShowLevels(false)
                } else {
                  if (!priceLevels) {
                    await loadLevels(symbol)
                  }
                  setShowLevels(true)
                }
              }}
              disabled={levelsLoading}
              title="显示/隐藏压力位与支撑位（枢轴点/均线/斐波那契）"
              style={{
                background: showLevels ? 'rgba(240,180,41,0.18)' : 'transparent',
                border: '1px solid ' + (showLevels ? '#f0b429' : 'var(--border-muted)'),
                color: showLevels ? '#f0b429' : (levelsLoading ? 'var(--text-faintest)' : 'var(--text-muted)'),
                borderRadius: 4, padding: '3px 10px', fontSize: 12,
                cursor: levelsLoading ? 'wait' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{ fontSize: 13 }}>📐</span>
              {levelsLoading ? '计算中…' : (showLevels ? '压力位 ✓' : '压力位')}
            </button>
            {loading && <span style={{ color: 'var(--accent)', fontSize: 12, marginLeft: 8 }}>⟳ 加载中...</span>}
          </div>

          {/* 均线设置弹窗 */}
          {showMAEditor && (
            <MAEditorModal
              customMAs={customMAs}
              onChange={newMAs => setCustomMAs(newMAs)}
              onClose={() => setShowMAEditor(false)}
            />
          )}

          {/* 数据采集面板弹窗 */}
          {showCollect && (
            <CollectPanel
              status={collectStatus}
              polling={collectPolling}
              onTrigger={(dateStr, symbols) => {
                triggerCollect(dateStr || null, symbols || null)
                  .then(r => {
                    setCollectStatus(r.progress ?? { running: true, message: r.message })
                    // 开始轮询进度
                    setCollectPolling(true)
                    const iv = setInterval(() => {
                      getCollectStatus().then(s => {
                        setCollectStatus(s)
                        if (!s.running) { clearInterval(iv); setCollectPolling(false) }
                      }).catch(() => { clearInterval(iv); setCollectPolling(false) })
                    }, 1500)
                  })
                  .catch(err => setCollectStatus({ running: false, message: '触发失败: ' + (err.message || err) }))
              }}
              onRefresh={() => getCollectStatus().then(setCollectStatus).catch(() => {})}
              onClose={() => setShowCollect(false)}
            />
          )}

          {/* 主题设置面板（下拉式，贴工具栏） */}
          {showTheme && (
            <ThemePanel
              themeId={themeId}
              brightness={brightness}
              onChange={(tid, _hue, bright) => {
                setThemeId(tid)
                setHueShift(0)
                setBrightness(bright)
                applyTheme(tid, 0, bright)
                localStorage.setItem(STORED_THEME_KEY,   tid)
                localStorage.setItem(STORED_HUE_KEY,     0)
                localStorage.setItem(STORED_BRIGHT_KEY,  bright)
                // 主题切换后延迟重建图表（等 CSS 变量生效后再读取）
                setTimeout(() => setChartKey(k => k + 1), 50)
              }}
              onClose={() => setShowTheme(false)}
            />
          )}

          <div style={{ flex: 1, padding: 8 }}>
            <KLineChart
              key={chartKey}
              symbol={symbol}
              candles={candles}
              volumes={volumes}
              maData={maData}
              maConfig={[
                ...FIXED_MA,
                ...customMAs.filter(m => m.enabled).map(m => ({
                  key:    `MA${m.period}`,
                  period: m.period,
                  color:  m.color,
                })),
              ]}
              loading={loading}
              priceLevels={showLevels ? priceLevels?.summary ?? null : null}
              onCandleHover={handleCandleHover}
              onCandleClick={handleCandleClick}
            />
          </div>

          <div style={{
            padding: '6px 16px', background: 'var(--bg-surface)',
            borderTop: '1px solid var(--border)', display: 'flex', gap: 20,
            alignItems: 'center', flexShrink: 0,
          }}>
            <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>
              共 <span style={{ color: 'var(--accent)' }}>{candles.length}</span> 根K线
            </span>
            {candles.length > 0 && <>
              <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>
                起始 <span style={{ color: 'var(--text-muted)' }}>{candles[0]?.time}</span>
              </span>
              <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>
                最新 <span style={{ color: 'var(--text-muted)' }}>{candles[candles.length - 1]?.time}</span>
              </span>
            </>}
            <span style={{ color: 'var(--text-faintest)', fontSize: 11, marginLeft: 'auto' }}>
              💡 点击K线查看日内行情
            </span>
          </div>
        </div>
      </>
      )}
      </div>

      {/* ── 日内弹窗（独立挂载，不在图表树里）── */}
      {modal.visible && (
        <IntradayModalWrapper
          symbol={modal.symbol}
          name={modal.name}
          date={modal.date}
          prevClose={modal.prevClose}
          onClose={() => setModal(m => ({ ...m, visible: false }))}
        />
      )}
    </div>
  )
}

// ── 弹窗包装器：懒加载，避免循环引用 ──────────────────────────────
import IntradayModal from './components/IntradayModal'

function IntradayModalWrapper({ symbol, name, date, prevClose, onClose }) {
  return (
    <IntradayModal
      symbol={symbol}
      name={name}
      date={date}
      prevClose={prevClose}
      onClose={onClose}
    />
  )
}

// ── 均线设置弹窗 ───────────────────────────────────────────────────
function MAEditorModal({ customMAs, onChange, onClose }) {
  const [list, setList] = useState(customMAs.map((m, i) => ({ ...m, _id: i })))
  const [inputVal, setInputVal] = useState('')
  const [inputErr, setInputErr] = useState('')

  const toggle = (idx) => {
    setList(prev => prev.map((m, i) => i === idx ? { ...m, enabled: !m.enabled } : m))
  }

  const remove = (idx) => {
    setList(prev => prev.filter((_, i) => i !== idx))
  }

  const addMA = () => {
    const p = parseInt(inputVal)
    if (isNaN(p) || p < 2 || p > 999) {
      setInputErr('请输入 2~999 之间的整数'); return
    }
    if (list.some(m => m.period === p)) {
      setInputErr(`MA${p} 已存在`); return
    }
    const colorIdx = list.length % CUSTOM_MA_COLORS.length
    setList(prev => [...prev, { period: p, color: CUSTOM_MA_COLORS[colorIdx], enabled: true, _id: Date.now() }])
    setInputVal(''); setInputErr('')
  }

  const save = () => {
    // eslint-disable-next-line no-unused-vars
    onChange(list.map(({ _id, ...rest }) => rest))
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.6)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-muted)',
        borderRadius: 8, width: 340, padding: 20,
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 15 }}>均线设置</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 18, cursor: 'pointer' }}>×</button>
        </div>

        {/* 固定均线（只读，显示状态） */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: 'var(--text-faint)', fontSize: 11, marginBottom: 6 }}>默认均线（不可删除）</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {FIXED_MA.map(m => (
              <span key={m.key} style={{
                border: `1px solid ${m.color}`,
                color: m.color, borderRadius: 4,
                padding: '2px 8px', fontSize: 12,
              }}>{m.key}</span>
            ))}
          </div>
        </div>

        {/* 自定义均线列表 */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: 'var(--text-faint)', fontSize: 11, marginBottom: 6 }}>自定义均线</div>
          {list.length === 0 && (
            <div style={{ color: 'var(--text-faintest)', fontSize: 12, padding: '6px 0' }}>暂无自定义均线</div>
          )}
          {list.map((m, idx) => (
            <div key={m._id ?? idx} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '5px 0', borderBottom: '1px solid var(--border)',
            }}>
              {/* 颜色圆点 */}
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: m.color, flexShrink: 0 }} />
              {/* 周期标签 */}
              <span style={{ color: 'var(--text-normal)', fontSize: 13, flex: 1 }}>MA{m.period}</span>
              {/* 启用/禁用切换 */}
              <button onClick={() => toggle(idx)} style={{
                background: m.enabled ? 'var(--accent-hover)' : 'var(--bg-elevated)',
                border: '1px solid ' + (m.enabled ? 'var(--accent)' : 'var(--border-muted)'),
                color: m.enabled ? 'var(--text-primary)' : 'var(--text-muted)',
                borderRadius: 12,
                padding: '2px 10px', fontSize: 11, cursor: 'pointer',
              }}>{m.enabled ? '显示' : '隐藏'}</button>
              {/* 删除 */}
              <button onClick={() => remove(idx)} style={{
                background: 'none', border: 'none',
                color: 'var(--text-faint)', fontSize: 16, cursor: 'pointer', padding: '0 2px',
              }} title="删除">×</button>
            </div>
          ))}
        </div>

        {/* 添加自定义均线 */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: 'var(--text-faint)', fontSize: 11, marginBottom: 6 }}>添加自定义均线</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="number"
              value={inputVal}
              onChange={e => { setInputVal(e.target.value); setInputErr('') }}
              onKeyDown={e => e.key === 'Enter' && addMA()}
              placeholder="输入周期（如 55）"
              style={{
                flex: 1, background: 'var(--bg-input)',
                border: '1px solid var(--border-muted)', borderRadius: 4,
                color: 'var(--text-normal)', padding: '5px 8px', fontSize: 13,
                outline: 'none',
              }}
            />
            <button onClick={addMA} style={{
              background: '#238636', border: '1px solid #2ea043',
              color: '#fff', borderRadius: 4, padding: '5px 12px',
              fontSize: 13, cursor: 'pointer',
            }}>添加</button>
          </div>
          {inputErr && <div style={{ color: '#f85149', fontSize: 11, marginTop: 4 }}>{inputErr}</div>}
        </div>

        {/* 底部按钮 */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            background: 'transparent', border: '1px solid var(--border-muted)',
            color: 'var(--text-muted)', borderRadius: 4, padding: '6px 16px', fontSize: 13, cursor: 'pointer',
          }}>取消</button>
          <button onClick={save} style={{
            background: 'var(--accent-hover)', border: '1px solid var(--accent)',
            color: 'var(--text-primary)', borderRadius: 4, padding: '6px 16px', fontSize: 13, cursor: 'pointer',
          }}>应用</button>
        </div>
      </div>
    </div>
  )
}

// ── 数据采集面板 ────────────────────────────────────────────────────
function CollectPanel({ status, polling, onTrigger, onRefresh, onClose }) {
  const [dateInput, setDateInput] = useState('')
  const [symInput,  setSymInput]  = useState('')

  const s = status || {}
  const pct = s.total > 0 ? Math.round((s.done / s.total) * 100) : 0

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.6)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-muted)',
        borderRadius: 8, width: 380, padding: 20,
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        {/* 标题 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 15 }}>⬇ 收盘数据采集</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={onRefresh} title="刷新状态" style={{
              background: 'none', border: '1px solid var(--border-muted)', color: 'var(--text-muted)',
              borderRadius: 4, padding: '2px 8px', fontSize: 12, cursor: 'pointer',
            }}>↻ 刷新</button>
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 18, cursor: 'pointer' }}>×</button>
          </div>
        </div>

        {/* 当前状态 */}
        <div style={{
          background: 'var(--bg-elevated)', borderRadius: 6, padding: '10px 12px', marginBottom: 14,
          border: '1px solid ' + (s.running ? '#2ea043' : 'var(--border-muted)'),
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>状态</span>
            <span style={{
              color: s.running ? '#56d364' : (s.finished_at ? 'var(--accent)' : 'var(--text-faint)'),
              fontSize: 12, fontWeight: 600,
            }}>
              {s.running ? '⚡ 采集中' : (s.finished_at ? '✓ 已完成' : '待机')}
            </span>
          </div>

          {/* 进度条 */}
          {(s.running || s.finished_at) && s.total > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>进度 {s.done}/{s.total}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{pct}%</span>
              </div>
              <div style={{ background: 'var(--border)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                <div style={{
                  width: pct + '%', height: '100%',
                  background: s.running ? 'var(--accent-hover)' : '#2ea043',
                  transition: 'width 0.4s',
                  borderRadius: 4,
                }} />
              </div>
              {s.failed > 0 && (
                <div style={{ color: '#f85149', fontSize: 11, marginTop: 4 }}>
                  ⚠ 失败 {s.failed} 只
                </div>
              )}
            </div>
          )}

          {/* 最新消息 */}
          {s.message && (
            <div style={{ color: 'var(--text-muted)', fontSize: 11, wordBreak: 'break-all', lineHeight: 1.4 }}>
              {s.message}
            </div>
          )}

          {/* 时间信息 */}
          {(s.started_at || s.finished_at) && (
            <div style={{ marginTop: 6, display: 'flex', gap: 16 }}>
              {s.started_at   && <span style={{ color: 'var(--text-faintest)', fontSize: 10 }}>开始 {s.started_at}</span>}
              {s.finished_at  && <span style={{ color: 'var(--text-faintest)', fontSize: 10 }}>完成 {s.finished_at}</span>}
            </div>
          )}
        </div>

        {/* 触发配置 */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ color: 'var(--text-faint)', fontSize: 11, marginBottom: 6 }}>手动触发采集</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              value={dateInput}
              onChange={e => setDateInput(e.target.value)}
              placeholder="日期 YYYY-MM-DD（默认今日）"
              style={{
                flex: 1, background: 'var(--bg-input)', border: '1px solid var(--border-muted)',
                borderRadius: 4, color: 'var(--text-normal)', padding: '5px 8px', fontSize: 12, outline: 'none',
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input
              type="text"
              value={symInput}
              onChange={e => setSymInput(e.target.value)}
              placeholder="股票代码（留空=全市场，如 300059,600519）"
              style={{
                flex: 1, background: 'var(--bg-input)', border: '1px solid var(--border-muted)',
                borderRadius: 4, color: 'var(--text-normal)', padding: '5px 8px', fontSize: 12, outline: 'none',
              }}
            />
          </div>
          <button
            onClick={() => onTrigger(dateInput.trim(), symInput.trim())}
            disabled={s.running}
            style={{
              width: '100%',
              background: s.running ? 'var(--bg-elevated)' : '#238636',
              border: '1px solid ' + (s.running ? 'var(--border-muted)' : '#2ea043'),
              color: s.running ? 'var(--text-faint)' : '#fff',
              borderRadius: 4, padding: '7px 0', fontSize: 13,
              cursor: s.running ? 'not-allowed' : 'pointer',
              fontWeight: 600,
            }}
          >
            {s.running ? '⚡ 采集进行中，请稍候…' : '▶ 立即触发采集'}
          </button>
        </div>

        {/* 说明 */}
        <div style={{ color: 'var(--text-faintest)', fontSize: 10, lineHeight: 1.6 }}>
          • 默认全市场 ~3900 只股票，约需 2~4 分钟<br/>
          • 留空日期时，若今日为非交易日则自动跳过<br/>
          • 写库幂等安全，重复触发不会产生重复数据<br/>
          • 每个交易日 15:50 自动执行，此按钮用于补采或测试
        </div>
      </div>
    </div>
  )
}

// ── 主题设置面板 ────────────────────────────────────────────────────
function ThemePanel({ themeId, brightness, onChange, onClose }) {
  const [localBright, setLocalBright] = useState(brightness)

  // 亮度实时预览
  const previewBright = (b) => applyTheme(themeId, 0, b)

  const apply = (tid, b) => onChange(tid, 0, b)

  const resetBright = () => {
    setLocalBright(1)
    apply(themeId, 1)
  }

  return (
    <div style={{
      position: 'absolute',
      top: 44, right: 16,
      zIndex: 300,
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-muted)',
      borderRadius: 10,
      width: 300,
      padding: 18,
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
    }}>
      {/* 标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 14 }}>🎨 页面主题</span>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: 18, cursor: 'pointer', lineHeight: 1,
        }}>×</button>
      </div>

      {/* 预设主题网格 */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ color: 'var(--text-faint)', fontSize: 11, marginBottom: 8 }}>背景 &amp; 按钮配色</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {THEMES.map(t => (
            <button
              key={t.id}
              onClick={() => apply(t.id, localBright)}
              style={{
                background: t.id === themeId ? 'var(--accent-hover)' : 'var(--bg-elevated)',
                border: '2px solid ' + (t.id === themeId ? 'var(--accent)' : 'var(--border-muted)'),
                borderRadius: 8,
                padding: '10px 4px',
                cursor: 'pointer',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
                transition: 'border-color 0.15s',
              }}
            >
              {/* 主题色板预览 */}
              <div style={{ display: 'flex', gap: 2, marginBottom: 2 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: t.vars['--bg-base'] }} />
                <div style={{ width: 10, height: 10, borderRadius: 2, background: t.vars['--bg-surface'] }} />
                <div style={{ width: 10, height: 10, borderRadius: 2, background: t.vars['--accent'] }} />
              </div>
              <span style={{ fontSize: 16 }}>{t.icon}</span>
              <span style={{
                color: t.id === themeId ? 'var(--text-primary)' : 'var(--text-muted)',
                fontSize: 11, fontWeight: t.id === themeId ? 600 : 400,
              }}>{t.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 亮度调节 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>亮度</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 600 }}>
              {localBright === 1 ? '标准' : localBright > 1 ? `+${Math.round((localBright-1)*100)}%` : `${Math.round((localBright-1)*100)}%`}
            </span>
            {localBright !== 1 && (
              <button onClick={resetBright} style={{
                background: 'none', border: '1px solid var(--border-muted)',
                color: 'var(--text-faint)', borderRadius: 3,
                padding: '1px 6px', fontSize: 10, cursor: 'pointer',
              }}>重置</button>
            )}
          </div>
        </div>
        <input
          type="range"
          min="0.6" max="1.4" step="0.02"
          value={localBright}
          onChange={e => {
            const v = Number(e.target.value)
            setLocalBright(v)
            previewBright(v)
          }}
          onMouseUp={e => apply(themeId, Number(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--accent)', cursor: 'pointer' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
          <span style={{ color: 'var(--text-faintest)', fontSize: 10 }}>😶‍🌫️ 暗</span>
          <span style={{ color: 'var(--text-faintest)', fontSize: 10 }}>☀️ 亮</span>
        </div>
      </div>

      {/* 确认按钮 */}
      <button
        onClick={onClose}
        style={{
          width: '100%',
          background: 'var(--accent-hover)',
          border: '1px solid var(--accent)',
          color: 'var(--text-primary)',
          borderRadius: 6, padding: '7px 0', fontSize: 13,
          cursor: 'pointer', fontWeight: 600,
        }}
      >✓ 完成</button>

      {/* 提示 */}
      <div style={{ marginTop: 10, color: 'var(--text-faintest)', fontSize: 10, lineHeight: 1.6 }}>
        • 主题仅调整页面背景与按钮配色<br/>
        • K线图涨红跌绿不受任何影响<br/>
        • 设置自动保存，下次打开生效
      </div>
    </div>
  )
}
