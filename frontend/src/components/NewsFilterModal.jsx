import { useState, useMemo } from 'react'

// 重大利好/利空筛选弹窗
export default function NewsFilterModal({ news, type, date, onClose }) {
  const [minConfidence, setMinConfidence] = useState(0.9) // 默认置信度阈值90%
  const [activeTab, setActiveTab] = useState('all') // all, positive, negative

  // 筛选重大利好/利空
  const filteredNews = useMemo(() => {
    return news.filter(item => {
      const confidence = item.sentiment_confidence || 0
      const sentiment = item.sentiment
      
      // 置信度必须达到阈值
      if (confidence < minConfidence) return false
      
      // 根据标签页筛选
      if (activeTab === 'positive') return sentiment === 'positive'
      if (activeTab === 'negative') return sentiment === 'negative'
      return sentiment === 'positive' || sentiment === 'negative'
    }).sort((a, b) => (b.sentiment_confidence || 0) - (a.sentiment_confidence || 0))
  }, [news, minConfidence, activeTab])

  // 统计
  const stats = useMemo(() => {
    const majorPositive = news.filter(n => n.sentiment === 'positive' && (n.sentiment_confidence || 0) >= 0.9).length
    const majorNegative = news.filter(n => n.sentiment === 'negative' && (n.sentiment_confidence || 0) >= 0.9).length
    return { majorPositive, majorNegative }
  }, [news])

  const getSentimentConfig = (sentiment) => {
    switch (sentiment) {
      case 'positive':
        return { label: '重大利好', color: '#ff4d4f', bgColor: 'rgba(255,77,79,0.15)', icon: '📈' }
      case 'negative':
        return { label: '重大利空', color: '#00b578', bgColor: 'rgba(0,181,120,0.15)', icon: '📉' }
      default:
        return { label: '中性', color: '#8b949e', bgColor: 'rgba(139,148,158,0.15)', icon: '😐' }
    }
  }

  const getEventTypeColor = (type) => {
    const colors = {
      '资产重组': '#f0b429',
      '股权转让': '#58a6ff',
      '对外担保': '#a78bfa',
      '投资设立': '#3ddc84',
      '股份回购': '#ff6b6b',
      '股权激励': '#ff9f43',
      '重大合同': '#00d2d3',
      '诉讼仲裁': '#ff4757',
      '违规处罚': '#ff6348',
    }
    for (const [key, color] of Object.entries(colors)) {
      if (type?.includes(key)) return color
    }
    return '#8b949e'
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 1000,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
    }} onClick={onClose}>
      <div style={{
        background: 'var(--bg-surface)',
        borderRadius: 12,
        width: '100%',
        maxWidth: 800,
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid var(--border)',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
      }} onClick={e => e.stopPropagation()}>
        {/* 头部 */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>⚡</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 16 }}>
              重大利好/利空筛选
            </span>
            <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>
              {date} · 共 {filteredNews.length} 条
            </span>
          </div>
          <button onClick={onClose} style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            fontSize: 20,
            cursor: 'pointer',
            padding: '4px 8px',
          }}>×</button>
        </div>

        {/* 统计卡片 */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          gap: 16,
          background: 'var(--bg-base)',
        }}>
          <div style={{
            flex: 1,
            padding: 12,
            background: 'rgba(255,77,79,0.1)',
            borderRadius: 8,
            border: '1px solid rgba(255,77,79,0.3)',
          }}>
            <div style={{ fontSize: 12, color: '#ff7875' }}>重大利好 (置信度≥90%)</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#ff4d4f', marginTop: 4 }}>
              {stats.majorPositive}
            </div>
          </div>
          <div style={{
            flex: 1,
            padding: 12,
            background: 'rgba(0,181,120,0.1)',
            borderRadius: 8,
            border: '1px solid rgba(0,181,120,0.3)',
          }}>
            <div style={{ fontSize: 12, color: '#36cfc9' }}>重大利空 (置信度≥90%)</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#00b578', marginTop: 4 }}>
              {stats.majorNegative}
            </div>
          </div>
        </div>

        {/* 筛选控制 */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
        }}>
          {/* 标签切换 */}
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { key: 'all', label: '全部', color: 'var(--accent)' },
              { key: 'positive', label: '重大利好', color: '#ff4d4f' },
              { key: 'negative', label: '重大利空', color: '#00b578' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '6px 14px',
                  background: activeTab === tab.key ? tab.color + '20' : 'var(--bg-elevated)',
                  border: '1px solid ' + (activeTab === tab.key ? tab.color : 'var(--border-muted)'),
                  color: activeTab === tab.key ? tab.color : 'var(--text-muted)',
                  borderRadius: 6,
                  fontSize: 12,
                  cursor: 'pointer',
                  fontWeight: activeTab === tab.key ? 600 : 400,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 置信度滑块 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
            <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>置信度阈值:</span>
            <input
              type="range"
              min="0.7"
              max="0.99"
              step="0.01"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              style={{ width: 100 }}
            />
            <span style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 600, minWidth: 40 }}>
              {(minConfidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* 新闻列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px' }}>
          {filteredNews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-faint)' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
              <div>暂无符合条件的新闻</div>
              <div style={{ fontSize: 12, marginTop: 8 }}>尝试降低置信度阈值</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {filteredNews.map((item, idx) => {
                const config = getSentimentConfig(item.sentiment)
                return (
                  <div key={idx} style={{
                    padding: 12,
                    background: 'var(--bg-base)',
                    borderRadius: 8,
                    border: '1px solid var(--border)',
                    borderLeft: `3px solid ${config.color}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 14 }}>{config.icon}</span>
                      <span style={{
                        padding: '2px 8px',
                        background: config.bgColor,
                        color: config.color,
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {config.label}
                      </span>
                      <span style={{ color: 'var(--accent)', fontSize: 11, fontWeight: 600 }}>
                        {((item.sentiment_confidence || 0) * 100).toFixed(1)}%
                      </span>
                      {type === 'company' && item.event_type && (
                        <span style={{
                          padding: '2px 8px',
                          background: `${getEventTypeColor(item.event_type)}20`,
                          color: getEventTypeColor(item.event_type),
                          borderRadius: 4,
                          fontSize: 11,
                        }}>
                          {item.event_type}
                        </span>
                      )}
                      <span style={{ color: 'var(--text-faintest)', fontSize: 11, marginLeft: 'auto' }}>
                        {item.event_date || item.publish_time || item.date}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500, lineHeight: 1.5 }}>
                      {type === 'company' ? `${item.name || item.symbol} - ${item.event_type}` : item.title}
                    </div>
                    {item.content && (
                      <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6, lineHeight: 1.6 }}>
                        {item.content.length > 150 ? item.content.slice(0, 150) + '...' : item.content}
                      </div>
                    )}
                    {type === 'company' && (
                      <div style={{ marginTop: 6, display: 'flex', gap: 8 }}>
                        <span style={{ color: 'var(--text-faint)', fontSize: 11 }}>代码: {item.symbol}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
