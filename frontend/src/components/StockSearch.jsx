import { useState, useEffect, useRef } from 'react'
import { searchStocks } from '../api/stocks'

export default function StockSearch({ onSelect }) {
  const [query, setQuery]       = useState('')
  const [results, setResults]   = useState([])
  const [loading, setLoading]   = useState(false)
  const [show, setShow]         = useState(false)
  const debounceRef             = useRef(null)
  const wrapRef                 = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setShow(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleInput = (val) => {
    setQuery(val)
    if (!val.trim()) { setResults([]); setShow(false); return }
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await searchStocks(val.trim(), 15)
        setResults(res.data || [])
        setShow(true)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
  }

  const handleSelect = (stock) => {
    setQuery(`${stock.symbol} ${stock.name}`)
    setShow(false)
    onSelect && onSelect(stock)
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: 280 }}>
      <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-surface)', border: '1px solid var(--border-muted)', borderRadius: 6, padding: '6px 12px', gap: 8 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          value={query}
          onChange={e => handleInput(e.target.value)}
          onFocus={() => results.length && setShow(true)}
          placeholder="搜索股票代码 / 名称"
          style={{
            background: 'none', border: 'none', outline: 'none',
            color: 'var(--text-normal)', fontSize: 13, width: '100%'
          }}
        />
        {loading && <span style={{ color: 'var(--accent)', fontSize: 11 }}>...</span>}
      </div>

      {show && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          background: 'var(--bg-surface)', border: '1px solid var(--border-muted)', borderRadius: 6,
          marginTop: 4, maxHeight: 280, overflowY: 'auto', zIndex: 100,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          {results.map(s => (
            <div
              key={s.symbol}
              onClick={() => handleSelect(s)}
              style={{
                padding: '8px 14px', cursor: 'pointer', display: 'flex',
                justifyContent: 'space-between', alignItems: 'center',
                borderBottom: '1px solid var(--border)', transition: 'background 0.1s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 13 }}>{s.symbol}</span>
              <span style={{ color: 'var(--text-normal)', fontSize: 13 }}>{s.name}</span>
              <span style={{
                color: s.market === 'SH' ? '#FF0000' : '#00B050',
                fontSize: 11, background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: 3
              }}>{s.market}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
