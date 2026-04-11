export default function StockInfoBar({ info }) {
  if (!info) return null

  const chg = info.change_pct
  const chgColor = chg == null ? 'var(--text-muted)' : chg >= 0 ? '#FF0000' : '#00B050'
  const chgText  = chg == null ? '--' : `${chg >= 0 ? '+' : ''}${chg}%`

  const items = [
    { label: '代码', value: info.symbol, color: 'var(--accent)' },
    { label: '名称', value: info.name, color: 'var(--text-normal)' },
    { label: '市场', value: info.market, color: info.market === 'SH' ? '#FF0000' : '#00B050' },
    { label: '最新价', value: info.last_price ?? '--', color: 'var(--text-primary)' },
    { label: '涨跌幅', value: chgText, color: chgColor },
    { label: '上市日期', value: info.list_date ?? '--', color: 'var(--text-muted)' },
  ]

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap',
      padding: '8px 16px', background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border)',
    }}>
      {items.map(it => (
        <div key={it.label} style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <span style={{ color: 'var(--text-faint)', fontSize: 10 }}>{it.label}</span>
          <span style={{ color: it.color, fontSize: 14, fontWeight: 600 }}>{it.value}</span>
        </div>
      ))}
    </div>
  )
}
