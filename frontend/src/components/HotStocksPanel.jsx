export default function HotStocksPanel({ data = [], date, onSelect }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ color: 'var(--text-normal)', fontWeight: 600, fontSize: 13 }}>成交额 Top 20</span>
        <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>{date || '--'}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--bg-surface)', position: 'sticky', top: 0 }}>
              {['代码', '名称', '涨跌%', '收盘'].map(h => (
                <th key={h} style={{
                  color: 'var(--text-faint)', fontWeight: 500, padding: '6px 8px',
                  textAlign: h === '代码' ? 'left' : 'right', borderBottom: '1px solid var(--border)'
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((s, i) => {
              const chg = s.change_pct
              const color = chg == null ? 'var(--text-muted)' : chg >= 0 ? '#FF0000' : '#00B050'
              return (
                <tr
                  key={s.symbol}
                  onClick={() => onSelect && onSelect(s)}
                  style={{ cursor: 'pointer', borderBottom: '1px solid var(--border)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '7px 8px', color: 'var(--accent)', fontWeight: 600 }}>
                    <span style={{
                      display: 'inline-block', width: 16, color: 'var(--text-faint)',
                      fontSize: 10, marginRight: 4
                    }}>{i + 1}</span>
                    {s.symbol}
                  </td>
                  <td style={{ padding: '7px 8px', color: 'var(--text-normal)', textAlign: 'right', maxWidth: 70, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</td>
                  <td style={{ padding: '7px 8px', color, textAlign: 'right', fontWeight: 600 }}>
                    {chg == null ? '--' : `${chg >= 0 ? '+' : ''}${chg}%`}
                  </td>
                  <td style={{ padding: '7px 8px', color: 'var(--text-primary)', textAlign: 'right' }}>
                    {s.close ?? '--'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
