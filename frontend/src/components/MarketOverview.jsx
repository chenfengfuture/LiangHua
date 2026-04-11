export default function MarketOverview({ overview }) {
  if (!overview) return null
  const { up = 0, down = 0, flat = 0, total = 0, date } = overview
  const upPct   = total ? Math.round(up   / total * 100) : 0
  const downPct = total ? Math.round(down / total * 100) : 0

  return (
    <div style={{ padding: '8px 16px', display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
      <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>市场总览 {date}</span>
      <div style={{ display: 'flex', gap: 12 }}>
        <span style={{ color: '#FF0000', fontSize: 13 }}>
          <strong>{up}</strong> <span style={{ fontSize: 11 }}>涨 ({upPct}%)</span>
        </span>
        <span style={{ color: '#00B050', fontSize: 13 }}>
          <strong>{down}</strong> <span style={{ fontSize: 11 }}>跌 ({downPct}%)</span>
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          <strong>{flat}</strong> <span style={{ fontSize: 11 }}>平</span>
        </span>
      </div>
      {/* 涨跌分布条 */}
      <div style={{ flex: 1, minWidth: 120, maxWidth: 240, height: 8, borderRadius: 4, overflow: 'hidden', background: 'var(--border)', display: 'flex' }}>
        <div style={{ width: `${upPct}%`, background: '#FF0000', transition: 'width 0.5s' }} />
        <div style={{ width: `${downPct}%`, background: '#00B050', transition: 'width 0.5s' }} />
      </div>
    </div>
  )
}
