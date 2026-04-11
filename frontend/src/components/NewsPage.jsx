import { useState, useEffect } from 'react'
import { useNewsData } from '../hooks/useNewsData'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'

// 情感标签配置 - 中国股市：利好=红色，利空=绿色
const SENTIMENT_CONFIG = {
  positive: { 
    label: '利好', 
    color: '#ff4d4f',           // 红色 - 重大利好
    bgColor: 'rgba(255,77,79,0.15)', 
    icon: '📈',
    titleColor: '#ff4d4f',      // 标题用标准红
    detailBg: 'rgba(255,77,79,0.08)',  // 详情背景浅红
    detailBorder: 'rgba(255,77,79,0.3)', // 详情边框
    detailText: '#ff7875',      // 详情文字粉红
  },
  neutral: { 
    label: '中性', 
    color: '#8b949e', 
    bgColor: 'rgba(139,148,158,0.15)', 
    icon: '😐',
    titleColor: '#8b949e',
    detailBg: 'rgba(139,148,158,0.08)',
    detailBorder: 'rgba(139,148,158,0.3)',
    detailText: '#b0b8c4',
  },
  negative: { 
    label: '利空', 
    color: '#00b578',           // 绿色 - 重大利空
    bgColor: 'rgba(0,181,120,0.15)', 
    icon: '📉',
    titleColor: '#00b578',      // 标题用标准绿
    detailBg: 'rgba(0,181,120,0.08)',  // 详情背景浅绿
    detailBorder: 'rgba(0,181,120,0.3)', // 详情边框
    detailText: '#36cfc9',      // 详情文字青绿
  },
}

// 获取情感标签配置
function getSentimentConfig(sentiment) {
  return SENTIMENT_CONFIG[sentiment] || SENTIMENT_CONFIG.neutral
}

// 事件类型颜色映射
const EVENT_TYPE_COLORS = {
  '资产重组': '#f0b429',
  '股权转让': '#58a6ff',
  '对外担保': '#a78bfa',
  '投资设立': '#3ddc84',
  '股份回购': '#ff6b6b',
  '股权激励': '#ff9f43',
  '重大合同': '#00d2d3',
  '诉讼仲裁': '#ff4757',
  '违规处罚': '#ff6348',
  '股份质押': '#ff6b9d',
  '资产收购': '#4ecdc4',
  '其他': '#8b949e',
}

// 财新新闻标签配置
const CAIXIN_TAG_CONFIG = {
  '市场动态': { color: '#58a6ff', icon: '📊' },
  '周刊提前读': { color: '#a78bfa', icon: '📖' },
  '华尔街原声': { color: '#f0b429', icon: '🏦' },
  '今日热点': { color: '#ff6b6b', icon: '🔥' },
  '商圈': { color: '#3ddc84', icon: '🏢' },
  '公司速递': { color: '#ff9f43', icon: '🚀' },
  '数据图解': { color: '#00d2d3', icon: '📈' },
  'CCI快报': { color: '#ff4757', icon: '⚡' },
  '市场洞察': { color: '#ce93d8', icon: '🔍' },
  '大宗经纬': { color: '#8bc34a', icon: '🌾' },
  '权益周观察': { color: '#ff9800', icon: '👁' },
  '行业洞察': { color: '#00bcd4', icon: '🏭' },
  '行业速递': { color: '#795548', icon: '📰' },
}

// 全球新闻来源配置
const GLOBAL_SOURCE_CONFIG = {
  'em': { label: '东方财富', color: '#ff6b6b', icon: '📈' },
  'cls': { label: '财联社', color: '#58a6ff', icon: '📰' },
}

// 获取事件类型颜色
function getEventTypeColor(type) {
  for (const [key, color] of Object.entries(EVENT_TYPE_COLORS)) {
    if (type?.includes(key)) return color
  }
  return EVENT_TYPE_COLORS['其他']
}

// 格式化日期为 YYYY-MM-DD
function formatDate(date) {
  return date.toISOString().slice(0, 10)
}

// 错误显示组件
function ErrorDisplay({ error, retryStatus, onRetry }) {
  const { count, isRetrying, nextRetryIn, maxRetries, currentCycle, maxCycles } = retryStatus || {}
  
  // 格式化倒计时
  const formatTime = (ms) => {
    if (!ms || ms <= 0) return ''
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    return minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`
  }
  
  return (
    <div style={{ 
      padding: 60, 
      textAlign: 'center',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 16,
    }}>
      <div style={{ 
        fontSize: 48, 
        marginBottom: 8,
        opacity: 0.8,
      }}>⚠️</div>
      
      <div style={{ 
        color: '#f85149', 
        fontSize: 15, 
        fontWeight: 600,
        maxWidth: 400,
        lineHeight: 1.6,
      }}>
        {error}
      </div>
      
      {/* 重试状态显示 */}
      {count > 0 && (
        <div style={{
          padding: '12px 20px',
          background: 'rgba(255,193,7,0.08)',
          border: '1px solid rgba(255,193,7,0.25)',
          borderRadius: 10,
          fontSize: 12,
          color: '#e6ac00',
          maxWidth: 360,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            {isRetrying ? (
              <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>↻</span>
            ) : (
              <span>⏱️</span>
            )}
            <span style={{ fontWeight: 600 }}>
              {isRetrying ? '正在自动重试...' : `第 ${count}/${maxRetries} 次重试`}
            </span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
            周期 {currentCycle || 0}/{maxCycles || 3} · 
            {isRetrying 
              ? `将在 ${formatTime(nextRetryIn)} 后再次尝试`
              : '已达到最大重试次数'
            }
          </div>
        </div>
      )}
      
      <button 
        onClick={onRetry} 
        className="news-btn news-btn-primary"
        disabled={isRetrying}
        style={{ opacity: isRetrying ? 0.6 : 1 }}
      >
        {isRetrying ? (
          <><span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>↻</span> 重试中...</>
        ) : (
          '立即重试'
        )}
      </button>
    </div>
  )
}

// 刷新按钮组件
function RefreshButton({ onRefresh, loading }) {
  return (
    <button
      onClick={onRefresh}
      disabled={loading}
      className="news-btn news-btn-ghost"
      style={{ opacity: loading ? 0.6 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
    >
      <span style={{
        display: 'inline-block',
        animation: loading ? 'spin 1s linear infinite' : 'none',
        fontSize: 14,
      }}>↻</span>
      {loading ? '刷新中...' : '刷新'}
    </button>
  )
}

// 筛选弹窗组件
function FilterModal({ 
  activeTab, 
  symbolFilter, setSymbolFilter,
  eventTypeFilter, setEventTypeFilter,
  caixinTagFilter, setCaixinTagFilter,
  globalSourceFilter, setGlobalSourceFilter,
  onConfirm, onCancel, onReset 
}) {
  // 本地状态，确认时才更新
  const [localSymbol, setLocalSymbol] = useState(symbolFilter)
  const [localEventType, setLocalEventType] = useState(eventTypeFilter)
  const [localCaixinTag, setLocalCaixinTag] = useState(caixinTagFilter)
  const [localGlobalSource, setLocalGlobalSource] = useState(globalSourceFilter)
  
  // 公司动态事件类型列表（从数据库实际数据）
  const eventTypes = ['资产重组', '股权转让', '对外担保', '股份质押', '资产收购', '投资设立', '股份回购', '股权激励', '重大合同', '诉讼仲裁', '违规处罚']
  
  // 财新新闻标签列表
  const caixinTags = Object.keys(CAIXIN_TAG_CONFIG)
  
  // 全球新闻来源列表
  const globalSources = [
    { key: 'em', label: '东方财富', icon: '📈' },
    { key: 'cls', label: '财联社', icon: '📰' },
  ]
  
  const handleConfirm = () => {
    onConfirm(localSymbol, localEventType, localCaixinTag, localGlobalSource)
  }
  
  const handleReset = () => {
    setLocalSymbol('')
    setLocalEventType('')
    setLocalCaixinTag('')
    setLocalGlobalSource('')
    onReset()
  }
  
  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        animation: 'fadeIn 0.2s ease',
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: 'linear-gradient(145deg, var(--bg-elevated) 0%, var(--bg-card) 100%)',
          borderRadius: 16,
          padding: 28,
          maxWidth: 480,
          width: '92%',
          maxHeight: '85vh',
          overflow: 'auto',
          boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)',
          border: '1px solid var(--border-muted)',
          animation: 'slideUp 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* 弹窗头部 */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 10,
          marginBottom: 24,
          paddingBottom: 16,
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <span style={{ fontSize: 22 }}>🔍</span>
          <span style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-primary)' }}>筛选条件</span>
          {(localSymbol || localEventType || localCaixinTag || localGlobalSource) && (
            <span style={{
              marginLeft: 'auto',
              padding: '4px 10px',
              background: 'var(--accent)',
              color: 'white',
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 700,
            }}>
              已筛选
            </span>
          )}
        </div>
        
        {/* 公司动态筛选 */}
        {(activeTab === 'company' || activeTab === 'all') && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ 
              fontSize: 12, 
              color: 'var(--text-muted)', 
              marginBottom: 12, 
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span>🏢</span> 公司动态筛选
            </div>
            
            {/* 股票代码 */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ 
                fontSize: 11, 
                color: 'var(--text-faint)', 
                marginBottom: 6, 
                fontWeight: 600, 
                letterSpacing: '0.5px', 
                textTransform: 'uppercase' 
              }}>
                股票代码
              </div>
              <input
                type="text"
                value={localSymbol}
                onChange={(e) => setLocalSymbol(e.target.value)}
                placeholder="例如：600519"
                className="news-input"
              />
            </div>
            
            {/* 事件类型 */}
            <div>
              <div style={{ 
                fontSize: 11, 
                color: 'var(--text-faint)', 
                marginBottom: 8, 
                fontWeight: 600, 
                letterSpacing: '0.5px', 
                textTransform: 'uppercase' 
              }}>
                事件类型
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {eventTypes.map(type => (
                  <span
                    key={type}
                    onClick={() => setLocalEventType(localEventType === type ? '' : type)}
                    style={{
                      padding: '5px 12px',
                      background: localEventType === type 
                        ? `linear-gradient(135deg, ${getEventTypeColor(type)}30, ${getEventTypeColor(type)}10)` 
                        : 'var(--bg-muted)',
                      color: localEventType === type ? getEventTypeColor(type) : 'var(--text-faint)',
                      border: `1px solid ${localEventType === type ? getEventTypeColor(type) + '70' : 'var(--border-muted)'}`,
                      borderRadius: 20,
                      fontSize: 11.5,
                      cursor: 'pointer',
                      fontWeight: localEventType === type ? 700 : 500,
                      transition: 'all 0.2s',
                      boxShadow: localEventType === type ? `0 2px 8px ${getEventTypeColor(type)}30` : 'none',
                    }}
                  >
                    {type}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* 财新新闻筛选 */}
        {(activeTab === 'caixin' || activeTab === 'all') && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ 
              fontSize: 12, 
              color: 'var(--text-muted)', 
              marginBottom: 12, 
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span>📰</span> 财新新闻筛选
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {caixinTags.map(tag => {
                const config = CAIXIN_TAG_CONFIG[tag] || { color: '#8b949e', icon: '📄' }
                const isSelected = localCaixinTag === tag
                return (
                  <span
                    key={tag}
                    onClick={() => setLocalCaixinTag(isSelected ? '' : tag)}
                    style={{
                      padding: '5px 12px',
                      background: isSelected 
                        ? `linear-gradient(135deg, ${config.color}30, ${config.color}10)` 
                        : 'var(--bg-muted)',
                      color: isSelected ? config.color : 'var(--text-faint)',
                      border: `1px solid ${isSelected ? config.color + '70' : 'var(--border-muted)'}`,
                      borderRadius: 20,
                      fontSize: 11.5,
                      cursor: 'pointer',
                      fontWeight: isSelected ? 700 : 500,
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      boxShadow: isSelected ? `0 2px 8px ${config.color}30` : 'none',
                    }}
                  >
                    <span>{config.icon}</span>
                    <span>{tag}</span>
                  </span>
                )
              })}
            </div>
          </div>
        )}
        
        {/* 全球新闻筛选 */}
        {(activeTab === 'global' || activeTab === 'all') && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ 
              fontSize: 12, 
              color: 'var(--text-muted)', 
              marginBottom: 12, 
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span>🌍</span> 全球新闻筛选
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {globalSources.map(source => {
                const isSelected = localGlobalSource === source.key
                return (
                  <span
                    key={source.key}
                    onClick={() => setLocalGlobalSource(isSelected ? '' : source.key)}
                    style={{
                      padding: '5px 12px',
                      background: isSelected 
                        ? `linear-gradient(135deg, ${source.key === 'em' ? '#ff6b6b' : '#58a6ff'}30, ${source.key === 'em' ? '#ff6b6b' : '#58a6ff'}10)` 
                        : 'var(--bg-muted)',
                      color: isSelected ? (source.key === 'em' ? '#ff6b6b' : '#58a6ff') : 'var(--text-faint)',
                      border: `1px solid ${isSelected ? (source.key === 'em' ? '#ff6b6b' : '#58a6ff') + '70' : 'var(--border-muted)'}`,
                      borderRadius: 20,
                      fontSize: 11.5,
                      cursor: 'pointer',
                      fontWeight: isSelected ? 700 : 500,
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      boxShadow: isSelected ? `0 2px 8px ${source.key === 'em' ? '#ff6b6b' : '#58a6ff'}30` : 'none',
                    }}
                  >
                    <span>{source.icon}</span>
                    <span>{source.label}</span>
                  </span>
                )
              })}
            </div>
          </div>
        )}
        
        {/* 按钮组 */}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
          <button
            onClick={handleReset}
            className="news-btn news-btn-ghost"
            style={{ padding: '10px 18px' }}
          >
            重置
          </button>
          <button
            onClick={onCancel}
            className="news-btn news-btn-ghost"
            style={{ padding: '10px 18px' }}
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            className="news-btn news-btn-primary"
            style={{ padding: '10px 22px' }}
          >
            应用筛选
          </button>
        </div>
      </div>
    </div>
  )
}

// 空数据弹窗组件
function EmptyDataModal({ date, onConfirm, onCancel }) {
  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--bg-primary)',
        borderRadius: 12,
        padding: 24,
        maxWidth: 400,
        width: '90%',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        border: '1px solid var(--border-muted)',
      }}>
        <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
          ⚠ 暂无数据
        </div>
        <div style={{ color: 'var(--text-muted)', marginBottom: 20 }}>
          当前日期 {date} 没有新闻数据，是否立即采集？
        </div>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '8px 16px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-muted)',
              borderRadius: 6,
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: '8px 16px',
              background: 'var(--accent)',
              border: '1px solid var(--accent)',
              borderRadius: 6,
              color: 'white',
              cursor: 'pointer',
            }}
          >
            立即采集
          </button>
        </div>
      </div>
    </div>
  )
}

// 新闻卡片组件
function NewsCard({ item, type, isNew = false, isUpdated = false, onClick }) {
  const sentimentConfig = getSentimentConfig(item.sentiment)
  const eventColor = type === 'company' ? getEventTypeColor(item.event_type) : 'var(--accent)'
  
  return (
    <div
      onClick={onClick}
      className="news-card"
      style={{
        background: isNew
          ? 'linear-gradient(145deg, rgba(31,111,235,0.08) 0%, var(--bg-elevated) 100%)'
          : 'linear-gradient(145deg, var(--bg-card) 0%, var(--bg-elevated) 100%)',
        border: isNew
          ? '1px solid rgba(31,111,235,0.35)'
          : isUpdated
            ? '1px solid rgba(255,193,7,0.3)'
            : '1px solid var(--border-muted)',
        borderLeft: `4px solid ${isNew ? '#1f6feb' : isUpdated ? '#ffc107' : eventColor}`,
        borderRadius: 12,
        padding: '16px 18px',
        cursor: 'pointer',
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        boxShadow: isNew
          ? '0 2px 12px rgba(31,111,235,0.2), 0 0 0 1px rgba(255,255,255,0.02)'
          : '0 2px 8px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.02)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* NEW 标识 */}
      {isNew && (
        <span style={{
          position: 'absolute',
          top: 8,
          right: 8,
          padding: '2px 8px',
          background: 'linear-gradient(135deg, #1f6feb, #0d47a1)',
          color: 'white',
          fontSize: 9,
          fontWeight: 900,
          borderRadius: 4,
          letterSpacing: '1px',
          boxShadow: '0 2px 8px rgba(31,111,235,0.5)',
          zIndex: 10,
          animation: 'pulse 2s infinite',
        }}>NEW</span>
      )}
      {/* UPDATE 标识 */}
      {!isNew && isUpdated && (
        <span style={{
          position: 'absolute',
          top: 8,
          right: 8,
          padding: '2px 8px',
          background: 'linear-gradient(135deg, #ffc107, #f57c00)',
          color: '#1a1a1a',
          fontSize: 9,
          fontWeight: 900,
          borderRadius: 4,
          letterSpacing: '0.5px',
          boxShadow: '0 2px 8px rgba(255,193,7,0.4)',
          zIndex: 10,
        }}>UPD</span>
      )}
      
      {/* 背景光效 */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        background: `linear-gradient(135deg, ${eventColor}08 0%, transparent 50%)`,
        pointerEvents: 'none',
        opacity: 0.5,
      }}/>
      
      {/* 顶部行：主标题 + 情感标签 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, gap: 12, position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
          {type === 'company' && (
            <>
              <span style={{
                flexShrink: 0,
                padding: '4px 10px',
                background: `linear-gradient(135deg, ${eventColor}20, ${eventColor}08)`,
                color: eventColor,
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 700,
                border: `1px solid ${eventColor}40`,
                letterSpacing: '0.5px',
                textShadow: `0 0 10px ${eventColor}30`,
              }}>
                {item.event_type || '其他'}
              </span>
              <span style={{ 
                fontWeight: 800, 
                color: 'var(--text-primary)', 
                fontSize: 14, 
                whiteSpace: 'nowrap',
                letterSpacing: '0.3px',
              }}>
                {item.symbol}
              </span>
              <span style={{ 
                color: 'var(--text-muted)', 
                fontSize: 13, 
                overflow: 'hidden', 
                textOverflow: 'ellipsis', 
                whiteSpace: 'nowrap',
                fontWeight: 500,
              }}>
                {item.name}
              </span>
            </>
          )}
          {(type === 'cctv' || type === 'caixin' || type === 'global') && (
            <span style={{ 
              fontWeight: 700, 
              color: 'var(--text-primary)', 
              fontSize: 14.5, 
              lineHeight: 1.5,
              letterSpacing: '0.2px',
            }}>
              {item.title}
            </span>
          )}
        </div>
        
        {item.sentiment && (
          <span style={{
            flexShrink: 0,
            padding: '4px 12px',
            background: `linear-gradient(135deg, ${sentimentConfig.bgColor}, transparent)`,
            color: sentimentConfig.color,
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 700,
            border: `1px solid ${sentimentConfig.detailBorder}`,
            whiteSpace: 'nowrap',
            boxShadow: `0 2px 8px ${sentimentConfig.color}15`,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}>
            <span style={{ fontSize: 12 }}>{sentimentConfig.icon}</span>
            <span>{sentimentConfig.label}</span>
          </span>
        )}
      </div>
      
      {/* 内容摘要 */}
      <div style={{ 
        color: 'var(--text-muted)', 
        fontSize: 13, 
        lineHeight: 1.7, 
        marginBottom: 12,
        position: 'relative',
        zIndex: 1,
      }}>
        {item.content || item.summary ? (
          (item.content || item.summary).length > 120 ? `${(item.content || item.summary).substring(0, 120)}…` : (item.content || item.summary)
        ) : (
          <span style={{ color: 'var(--text-faintest)', fontStyle: 'italic' }}>暂无内容摘要</span>
        )}
      </div>
      
      {/* AI 利好板块/个股摘要（有数据时才显示）*/}
      {(item.ai_benefit_sectors || item.ai_benefit_stocks) && (
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 5,
          marginBottom: 10,
          position: 'relative',
          zIndex: 1,
        }}>
          {/* 利好板块 */}
          {item.ai_benefit_sectors && item.ai_benefit_sectors.split(/[,，、]/).slice(0, 3).map((s, i) => s.trim() && (
            <span key={`sector-${i}`} style={{
              padding: '2px 8px',
              background: 'rgba(255,77,79,0.1)',
              border: '1px solid rgba(255,77,79,0.25)',
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 600,
              color: '#ff7875',
            }}>📈 {s.trim()}</span>
          ))}
          {/* 利好个股 */}
          {item.ai_benefit_stocks && item.ai_benefit_stocks.split(/[,，、]/).slice(0, 2).map((s, i) => s.trim() && (
            <span key={`stock-${i}`} style={{
              padding: '2px 8px',
              background: 'rgba(240,180,41,0.1)',
              border: '1px solid rgba(240,180,41,0.25)',
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 600,
              color: '#f0b429',
            }}>🏆 {s.trim()}</span>
          ))}
        </div>
      )}

      {/* AI 大模型解读（有数据时才显示）*/}
      {item.ai_interpretation && (
        <div style={{
          marginBottom: 8,
          padding: '8px 10px',
          background: 'linear-gradient(135deg, rgba(114,137,218,0.08), rgba(114,137,218,0.02))',
          border: '1px solid rgba(114,137,218,0.15)',
          borderRadius: 8,
          position: 'relative',
          zIndex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#7289da', letterSpacing: '0.3px' }}>AI</span>
            <span style={{ fontSize: 10, color: 'var(--text-faint)' }}>大模型解读</span>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12.5, lineHeight: 1.6 }}>
            {item.ai_interpretation}
          </div>
          {item.ai_key_suppliers && item.ai_key_suppliers !== '未提及' && (
            <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-faint)' }}>
              关键供应商: {item.ai_key_suppliers}
            </div>
          )}
        </div>
      )}

      {/* FinBERT 情感分析指标（有情感数据时才显示）*/}
      {item.sentiment_confidence && (
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 6,
          alignItems: 'center',
          marginBottom: 8,
          position: 'relative',
          zIndex: 1,
          fontSize: 10.5,
        }}>
          {/* 置信度 */}
          <span style={{
            padding: '2px 7px',
            background: 'rgba(150,150,150,0.08)',
            border: '1px solid rgba(150,150,150,0.15)',
            borderRadius: 10,
            color: 'var(--text-faint)',
            fontWeight: 500,
          }}>
            置信度 {(item.sentiment_confidence * 100).toFixed(1)}%
          </span>
          {/* 多空比 */}
          {item.bull_bear_ratio != null && (
            <span style={{
              padding: '2px 7px',
              background: item.bull_bear_ratio >= 1 ? 'rgba(255,77,79,0.08)' : 'rgba(82,196,26,0.08)',
              border: `1px solid ${item.bull_bear_ratio >= 1 ? 'rgba(255,77,79,0.2)' : 'rgba(82,196,26,0.2)'}`,
              borderRadius: 10,
              color: item.bull_bear_ratio >= 1 ? '#ff7875' : '#52c41a',
              fontWeight: 600,
            }}>
              多空比 {item.bull_bear_ratio >= 1000 ? item.bull_bear_ratio.toFixed(0) : item.bull_bear_ratio.toFixed(2)}
            </span>
          )}
          {/* 空头风险 */}
          {item.bear_risk_score != null && item.bear_risk_score > 0 && (
            <span style={{
              padding: '2px 7px',
              background: 'rgba(82,196,26,0.08)',
              border: '1px solid rgba(82,196,26,0.2)',
              borderRadius: 10,
              color: '#52c41a',
              fontWeight: 500,
            }}>
              空头风险 {item.bear_risk_score.toFixed(4)}
            </span>
          )}
          {/* 多头风险 */}
          {item.bull_risk_score != null && item.bull_risk_score > 0 && (
            <span style={{
              padding: '2px 7px',
              background: 'rgba(255,77,79,0.08)',
              border: '1px solid rgba(255,77,79,0.2)',
              borderRadius: 10,
              color: '#ff7875',
              fontWeight: 500,
            }}>
              多头风险 {item.bull_risk_score.toFixed(4)}
            </span>
          )}
          {/* 情感波动 */}
          {item.sentiment_volatility != null && item.sentiment_volatility > 0 && (
            <span style={{
              padding: '2px 7px',
              background: 'rgba(250,173,20,0.08)',
              border: '1px solid rgba(250,173,20,0.2)',
              borderRadius: 10,
              color: '#faad14',
              fontWeight: 500,
            }}>
              波动 {item.sentiment_volatility.toFixed(4)}
            </span>
          )}
          {/* 三维情感条 */}
          {item.sentiment_score_pos != null && (
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3,
              padding: '2px 7px',
              background: 'rgba(150,150,150,0.06)',
              border: '1px solid rgba(150,150,150,0.12)',
              borderRadius: 10,
              color: 'var(--text-faint)',
            }}>
              <span style={{ color: '#ff4d4f', fontWeight: 700 }}>{(item.sentiment_score_neg * 100).toFixed(1)}</span>
              <span>/</span>
              <span style={{ fontWeight: 700 }}>{(item.sentiment_score_neu * 100).toFixed(1)}</span>
              <span>/</span>
              <span style={{ color: '#52c41a', fontWeight: 700 }}>{(item.sentiment_score_pos * 100).toFixed(1)}</span>
            </span>
          )}
        </div>
      )}

      {/* 底部行：日期 + 发布时间 + 查看 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        paddingTop: 10,
        borderTop: '1px solid var(--border-subtle)',
        color: 'var(--text-faint)',
        fontSize: 11.5,
        position: 'relative',
        zIndex: 1,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ opacity: 0.7, fontSize: 12 }}>🕐</span>
          {(() => {
            // 统一获取发布时间（兼容 pub_time / publish_time）
            const pubTime = item.pub_time || item.publish_time
            let dateStr = ''
            let timeStr = ''
            if (type === 'company') {
              dateStr = item.event_date || ''
            } else {
              dateStr = item.news_date || ''
            }
            // 从 pub_time 提取日期和时间
            if (pubTime) {
              const pt = String(pubTime)
              if (pt.includes(' ')) {
                // 格式 "2026-04-01 13:30:00"
                const parts = pt.split(' ')
                if (!dateStr || dateStr.length <= 5) dateStr = parts[0]
                timeStr = parts[1].substring(0, 5) // "13:30"
              } else if (pt.includes('T')) {
                // 格式 "2026-04-01T13:30:00"
                const parts = pt.split('T')
                if (!dateStr || dateStr.length <= 5) dateStr = parts[0]
                timeStr = parts[1].substring(0, 5)
              }
            }
            return (
              <span>
                <span style={{ fontWeight: 500 }}>{dateStr}</span>
                {timeStr && (
                  <span style={{ marginLeft: 6, fontSize: 10.5, opacity: 0.75 }}>{timeStr}</span>
                )}
              </span>
            )
          })()}
        </span>
        <span style={{ 
          color: 'var(--accent-dim)', 
          fontSize: 11.5, 
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 3,
        }}>
          查看详情 <span style={{ fontSize: 14, transition: 'transform 0.2s' }} className="arrow-icon">›</span>
        </span>
      </div>
    </div>
  )
}

// 新闻详情弹窗组件
function NewsDetailModal({ news, type, onClose }) {
  const sentimentConfig = getSentimentConfig(news.sentiment)
  const eventColor = type === 'company' ? getEventTypeColor(news.event_type) : 'var(--accent)'
  
  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-elevated)',
          borderRadius: 14,
          padding: 0,
          maxWidth: 640,
          width: '92%',
          maxHeight: '82vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          border: '1px solid var(--border-muted)',
          overflow: 'hidden',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* 弹窗头部 */}
        <div style={{
          padding: '18px 20px 16px',
          borderBottom: '1px solid var(--border-muted)',
          borderLeft: `4px solid ${eventColor}`,
          background: 'var(--bg-header)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1, paddingRight: 12 }}>
              {type === 'company' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    padding: '3px 10px',
                    background: `${eventColor}20`,
                    color: eventColor,
                    borderRadius: 5,
                    fontSize: 12,
                    fontWeight: 700,
                    border: `1px solid ${eventColor}50`,
                  }}>
                    {news.event_type || '其他'}
                  </span>
                  <span style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '0.5px' }}>
                    {news.symbol}
                  </span>
                  <span style={{ fontSize: 15, color: 'var(--text-muted)' }}>{news.name}</span>
                </div>
              )}
              {(type === 'cctv' || type === 'caixin' || type === 'global') && (
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                  {news.title}
                </div>
              )}
              <div style={{ color: 'var(--text-faint)', fontSize: 12, marginTop: 6, display: 'flex', gap: 12 }}>
                {(() => {
                  const pubTime = news.pub_time || news.publish_time
                  let dateStr = type === 'company' ? (news.event_date || '') : (news.news_date || '')
                  let timeStr = ''
                  if (pubTime) {
                    const pt = String(pubTime)
                    if (pt.includes(' ')) {
                      const parts = pt.split(' ')
                      if (!dateStr || dateStr.length <= 5) dateStr = parts[0]
                      timeStr = parts[1].substring(0, 5)
                    } else if (pt.includes('T')) {
                      const parts = pt.split('T')
                      if (!dateStr || dateStr.length <= 5) dateStr = parts[0]
                      timeStr = parts[1].substring(0, 5)
                    }
                  }
                  return (
                    <span>🕐 {dateStr}{timeStr && <span style={{ opacity: 0.7 }}> {timeStr}</span>}</span>
                  )
                })()}
                {news.source && <span>📡 {news.source}</span>}
              </div>
            </div>
            
            <button
              onClick={onClose}
              style={{
                flexShrink: 0,
                background: 'var(--bg-muted)',
                border: '1px solid var(--border-muted)',
                borderRadius: 8,
                width: 30,
                height: 30,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14,
                color: 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              ✕
            </button>
          </div>
          
          {/* 情感标签 */}
          {news.sentiment && (
            <div style={{
              marginTop: 10,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 12px',
              background: sentimentConfig.bgColor,
              border: `1px solid ${sentimentConfig.detailBorder}`,
              borderRadius: 20,
            }}>
              <span>{sentimentConfig.icon}</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: sentimentConfig.color }}>
                {sentimentConfig.label}
              </span>
              {news.sentiment_confidence && (
                <span style={{ fontSize: 11, color: sentimentConfig.detailText }}>
                  置信度 {(news.sentiment_confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          )}
        </div>
        
        {/* 正文内容 + AI 分析 */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '20px',
          color: 'var(--text-primary)',
          lineHeight: 1.75,
          fontSize: 14,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}>
          {/* 正文 */}
          <div style={{ whiteSpace: 'pre-wrap' }}>
            {news.content || news.summary || <span style={{ color: 'var(--text-faint)', fontStyle: 'italic' }}>暂无详细内容</span>}
          </div>

          {/* AI 分析区块 */}
          {(news.ai_interpretation || news.ai_benefit_sectors || news.ai_benefit_stocks || news.ai_key_suppliers) && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(47,129,247,0.06) 0%, rgba(139,92,246,0.04) 100%)',
              border: '1px solid rgba(47,129,247,0.2)',
              borderRadius: 12,
              padding: '16px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}>
              {/* 标题行 */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                paddingBottom: 10,
                borderBottom: '1px solid rgba(47,129,247,0.15)',
              }}>
                <span style={{ fontSize: 16 }}>🤖</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#58a6ff', letterSpacing: '0.5px' }}>
                  AI 智能解读
                </span>
              </div>

              {/* AI 解读正文 */}
              {news.ai_interpretation && (
                <div style={{
                  fontSize: 13.5,
                  color: 'var(--text-secondary, #c9d1d9)',
                  lineHeight: 1.8,
                  whiteSpace: 'pre-wrap',
                }}>
                  {news.ai_interpretation}
                </div>
              )}

              {/* 利好板块 */}
              {news.ai_benefit_sectors && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span style={{ fontSize: 11.5, color: 'var(--text-faint)', fontWeight: 600, letterSpacing: '0.5px' }}>
                    📈 利好板块
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {news.ai_benefit_sectors.split(/[,，、]/).map((s, i) => s.trim() && (
                      <span key={i} style={{
                        padding: '3px 10px',
                        background: 'rgba(255,77,79,0.12)',
                        border: '1px solid rgba(255,77,79,0.3)',
                        borderRadius: 20,
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#ff7875',
                      }}>{s.trim()}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* 利好股票 */}
              {news.ai_benefit_stocks && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span style={{ fontSize: 11.5, color: 'var(--text-faint)', fontWeight: 600, letterSpacing: '0.5px' }}>
                    🏆 利好个股
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {news.ai_benefit_stocks.split(/[,，、]/).map((s, i) => s.trim() && (
                      <span key={i} style={{
                        padding: '3px 10px',
                        background: 'rgba(240,180,41,0.12)',
                        border: '1px solid rgba(240,180,41,0.3)',
                        borderRadius: 20,
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#f0b429',
                      }}>{s.trim()}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* 核心供应商 */}
              {news.ai_key_suppliers && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span style={{ fontSize: 11.5, color: 'var(--text-faint)', fontWeight: 600, letterSpacing: '0.5px' }}>
                    🔗 核心供应商/关联方
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {news.ai_key_suppliers.split(/[,，、]/).map((s, i) => s.trim() && (
                      <span key={i} style={{
                        padding: '3px 10px',
                        background: 'rgba(0,188,212,0.1)',
                        border: '1px solid rgba(0,188,212,0.3)',
                        borderRadius: 20,
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#00bcd4',
                      }}>{s.trim()}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* 底部按钮 */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid var(--border-muted)',
          display: 'flex',
          justifyContent: 'flex-end',
          background: 'var(--bg-header)',
        }}>
          <button
            onClick={onClose}
            className="news-btn news-btn-primary"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

// 公司动态标签页 - 纯展示组件，数据由父组件传入
function CompanyNewsTab({ 
  date, news = [], loading = false, error = null, stats = null,
  newIds = new Set(), updatedIds = new Set(), onMarkRead,
  collectionStatus, collectingSections = [], pendingAnalysis = 0,
  showEmptyModal, hideEmptyModal, retryStatus, onRefresh,
}) {
  const [selectedNews, setSelectedNews] = useState(null)
  const PAGE_SIZE = 30

  // 基于 IntersectionObserver 的无限滚动（零 scroll 事件）
  const { visibleItems: displayedNews, hasMore, sentinelRef, total, displayCount } = useInfiniteScroll(news, { pageSize: PAGE_SIZE })

  const handleRefresh = () => {
    onRefresh?.()
  }

  // 采集状态提示组件
  const CollectionStatusBar = () => {
    const isCollecting = collectionStatus === 'collecting' || collectingSections.includes('company')
    
    if (pendingAnalysis > 0) {
      return (
        <div style={{
          padding: '8px 14px',
          background: 'rgba(47,129,247,0.08)',
          border: '1px solid rgba(47,129,247,0.25)',
          borderRadius: 8,
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          fontSize: 12,
          color: '#58a6ff',
        }}>
          <span>🧠</span>
          <span>AI情感分析中 ({pendingAnalysis}条)...</span>
          <span style={{ marginLeft: 'auto', color: 'var(--text-faint)', fontSize: 11 }}>完成后自动更新</span>
        </div>
      )
    }
    
    return null
  }

  if (loading && news.length === 0) {
    return (
      <div style={{ 
        padding: 80, 
        textAlign: 'center', 
        color: 'var(--text-muted)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
      }}>
        <div style={{ 
          width: 60, 
          height: 60, 
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--bg-muted), var(--bg-card))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05)',
        }}>
          <div style={{ 
            fontSize: 28, 
            animation: 'spin 1s linear infinite',
            filter: 'drop-shadow(0 0 8px var(--accent-dim))',
          }}>↻</div>
        </div>
        <div style={{ fontSize: 15, fontWeight: 500 }}>正在加载公司动态...</div>
        <div style={{ fontSize: 12, color: 'var(--text-faint)' }}>请稍候，正在获取最新数据</div>
      </div>
    )
  }

  if (error && news.length === 0) {
    return (
      <ErrorDisplay 
        error={error} 
        retryStatus={retryStatus}
        onRetry={handleRefresh} 
      />
    )
  }

  return (
    <div style={{ padding: '14px 16px' }}>
      {/* 空数据弹窗 - 由统一Hook控制 */}
      {showEmptyModal && (
        <EmptyDataModal
          date={date}
          onConfirm={hideEmptyModal}
          onCancel={hideEmptyModal}
        />
      )}

      {/* 详情弹窗 */}
      {selectedNews && (
        <NewsDetailModal
          news={selectedNews}
          type="company"
          onClose={() => setSelectedNews(null)}
        />
      )}

      {/* 采集状态提示 */}
      <CollectionStatusBar />

      {/* 统计栏 */}
      <div style={{ 
        marginBottom: 12, 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 12, color: 'var(--text-faint)',
            padding: '3px 10px',
            background: 'var(--bg-muted)',
            borderRadius: 20,
            border: '1px solid var(--border-muted)',
          }}>
            {news.length} 条 · {date}
          </span>
          {stats?.source && (
            <span style={{ fontSize: 11, color: 'var(--text-faintest)', padding: '3px 8px', background: 'var(--bg-muted)', borderRadius: 20 }}>
              {stats.source}
            </span>
          )}
        </div>
        <RefreshButton onRefresh={handleRefresh} loading={loading || collectionStatus === 'collecting'} />
      </div>

      {news.length === 0 ? (
        <div style={{ 
          padding: 80, 
          textAlign: 'center', 
          color: 'var(--text-faint)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{ 
            fontSize: 48, 
            marginBottom: 8,
            opacity: 0.8,
            filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))',
          }}>📭</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-muted)' }}>暂无公司动态数据</div>
          <div style={{ fontSize: 12, color: 'var(--text-faintest)' }}>系统已自动触发数据采集</div>
          <button
            onClick={handleRefresh}
            className="news-btn news-btn-ghost"
            style={{ marginTop: 16 }}
          >
            <span>↻</span> 重新加载
          </button>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {displayedNews.map((item, idx) => (
              <div key={item.id || `company-${idx}`} className="news-list-item" style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s` }}>
                <NewsCard
                  item={item}
                  type="company"
                  isNew={newIds?.has?.(item.id)}
                  isUpdated={updatedIds?.has?.(item.id)}
                  onClick={() => {
                    setSelectedNews(item)
                    if (item.id && onMarkRead) onMarkRead(item.id)
                  }}
                />
              </div>
            ))}
          </div>
          
          {/* 无限滚动哨兵 + 状态提示 */}
          <div ref={sentinelRef} style={{ padding: '12px 0', textAlign: 'center', color: 'var(--text-faintest)', fontSize: 11 }}>
            {hasMore
              ? <span style={{ opacity: 0.5 }}>↓ 滚动加载更多（{displayCount} / {total}）</span>
              : total > 0 && <span>已全部加载 · 共 {total} 条</span>
            }
          </div>
        </>
      )}
    </div>
  )
}

// 新闻联播标签页 - 纯展示组件，数据由父组件传入
function CCTVNewsTab({ news = [], loading = false, error = null, 
  date, newIds = new Set(), updatedIds = new Set(), onMarkRead,
  retryStatus, collectionStatus, collectingSections = [], onRefresh }) {
  const [selectedNews, setSelectedNews] = useState(null)
  const { visibleItems, hasMore, sentinelRef, total, displayCount } = useInfiniteScroll(news, { pageSize: 30 })

  const handleRefresh = () => {
    onRefresh?.()
  }

  if (loading && news.length === 0) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 28, marginBottom: 12, animation: 'spin 1.2s linear infinite', display: 'inline-block' }}>↻</div>
        <div style={{ fontSize: 14 }}>正在加载新闻联播...</div>
      </div>
    )
  }
  
  if (error && news.length === 0) {
    return (
      <ErrorDisplay 
        error={error} 
        retryStatus={retryStatus}
        onRetry={handleRefresh} 
      />
    )
  }

  return (
    <div style={{ padding: '14px 16px' }}>
      {selectedNews && (
        <NewsDetailModal
          news={selectedNews}
          type="cctv"
          onClose={() => setSelectedNews(null)}
        />
      )}

      <div style={{ 
        marginBottom: 12, 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 12, color: 'var(--text-faint)',
            padding: '3px 10px',
            background: 'var(--bg-muted)',
            borderRadius: 20,
            border: '1px solid var(--border-muted)',
          }}>
            {news.length} 条{date ? ` · ${date}` : ''}
          </span>
        </div>
        <RefreshButton 
          onRefresh={handleRefresh} 
          loading={loading || (collectionStatus === 'collecting' && collectingSections.includes('cctv'))} 
        />
      </div>

      {news.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-faint)' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📺</div>
          <div style={{ fontSize: 14 }}>暂无新闻联播数据</div>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {visibleItems.map((item, idx) => (
              <div key={item.id || `cctv-${idx}`} className="news-list-item" style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s` }}>
                <NewsCard
                  item={item}
                  type="cctv"
                  isNew={newIds?.has?.(item.id)}
                  isUpdated={updatedIds?.has?.(item.id)}
                  onClick={() => {
                    setSelectedNews(item)
                    if (item.id && onMarkRead) onMarkRead(item.id)
                  }}
                />
              </div>
            ))}
          </div>
          <div ref={sentinelRef} style={{ padding: '12px 0', textAlign: 'center', color: 'var(--text-faintest)', fontSize: 11 }}>
            {hasMore
              ? <span style={{ opacity: 0.5 }}>↓ 滚动加载更多（{displayCount} / {total}）</span>
              : total > 0 && <span>已全部加载 · 共 {total} 条</span>
            }
          </div>
        </>
      )}
    </div>
  )
}

// 财新新闻标签页 - 纯展示组件，数据由父组件传入
function CaixinNewsTab({ news = [], loading = false, error = null, 
  newIds = new Set(), updatedIds = new Set(), onMarkRead,
  retryStatus, onRefresh }) {
  const [selectedNews, setSelectedNews] = useState(null)
  const { visibleItems, hasMore, sentinelRef, total, displayCount } = useInfiniteScroll(news, { pageSize: 30 })

  const handleRefresh = () => {
    onRefresh?.()
  }

  if (loading && news.length === 0) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 28, marginBottom: 12, animation: 'spin 1.2s linear infinite', display: 'inline-block' }}>↻</div>
        <div style={{ fontSize: 14 }}>正在加载财新新闻...</div>
      </div>
    )
  }
  
  if (error && news.length === 0) {
    return (
      <ErrorDisplay 
        error={error} 
        retryStatus={retryStatus}
        onRetry={handleRefresh} 
      />
    )
  }

  return (
    <div style={{ padding: '14px 16px' }}>
      {selectedNews && (
        <NewsDetailModal
          news={selectedNews}
          type="caixin"
          onClose={() => setSelectedNews(null)}
        />
      )}

      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: 'var(--text-faint)', padding: '3px 10px', background: 'var(--bg-muted)', borderRadius: 20, border: '1px solid var(--border-muted)' }}>
          {news.length} 条财新新闻
        </span>
        <RefreshButton onRefresh={handleRefresh} loading={loading} />
      </div>

      {news.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-faint)' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📰</div>
          <div style={{ fontSize: 14 }}>暂无财新新闻数据</div>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {visibleItems.map((item, idx) => (
              <div key={item.id || `caixin-${idx}`} className="news-list-item" style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s` }}>
                <NewsCard
                  item={item}
                  type="caixin"
                  isNew={newIds?.has?.(item.id)}
                  isUpdated={updatedIds?.has?.(item.id)}
                  onClick={() => {
                    setSelectedNews(item)
                    if (item.id && onMarkRead) onMarkRead(item.id)
                  }}
                />
              </div>
            ))}
          </div>
          <div ref={sentinelRef} style={{ padding: '12px 0', textAlign: 'center', color: 'var(--text-faintest)', fontSize: 11 }}>
            {hasMore
              ? <span style={{ opacity: 0.5 }}>↓ 滚动加载更多（{displayCount} / {total}）</span>
              : total > 0 && <span>已全部加载 · 共 {total} 条</span>
            }
          </div>
        </>
      )}
    </div>
  )
}

// 全球新闻标签页 - 纯展示组件，数据由父组件传入
function GlobalNewsTab({ news = [], loading = false, error = null, 
  newIds = new Set(), updatedIds = new Set(), onMarkRead,
  retryStatus, onRefresh }) {
  const [selectedNews, setSelectedNews] = useState(null)
  const { visibleItems, hasMore, sentinelRef, total, displayCount } = useInfiniteScroll(news, { pageSize: 30 })

  const handleRefresh = () => {
    onRefresh?.()
  }

  if (loading && news.length === 0) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 28, marginBottom: 12, animation: 'spin 1.2s linear infinite', display: 'inline-block' }}>↻</div>
        <div style={{ fontSize: 14 }}>正在加载全球新闻...</div>
      </div>
    )
  }
  
  if (error && news.length === 0) {
    return (
      <ErrorDisplay 
        error={error} 
        retryStatus={retryStatus}
        onRetry={handleRefresh} 
      />
    )
  }

  return (
    <div style={{ padding: '14px 16px' }}>
      {selectedNews && (
        <NewsDetailModal
          news={selectedNews}
          type="global"
          onClose={() => setSelectedNews(null)}
        />
      )}

      {news.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-faint)' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🌍</div>
          <div style={{ fontSize: 14 }}>暂无全球新闻数据</div>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {visibleItems.map((item, idx) => (
              <div key={item.id || `global-${idx}`} className="news-list-item" style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s` }}>
                <NewsCard
                  item={item}
                  type="global"
                  isNew={newIds?.has?.(item.id)}
                  isUpdated={updatedIds?.has?.(item.id)}
                  onClick={() => {
                    setSelectedNews(item)
                    if (item.id && onMarkRead) onMarkRead(item.id)
                  }}
                />
              </div>
            ))}
          </div>
          <div ref={sentinelRef} />
        </>
      )}
    </div>
  )
}

// 主组件 - 新闻页面
export default function NewsPage() {
  const [activeTab, setActiveTab] = useState('caixin')
  const [date, setDate] = useState(formatDate(new Date()))
  const [showFilterModal, setShowFilterModal] = useState(false)
  const [symbolFilter, setSymbolFilter] = useState('')
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  
  // 子分类筛选状态
  const [caixinTagFilter, setCaixinTagFilter] = useState('')
  const [globalSourceFilter, setGlobalSourceFilter] = useState('')

  // AI 智能筛选状态（每个 tab 独立）
  // aiTags: Set 多选；confidenceThreshold: 0-100，默认 0 表示不过滤
  const [aiFilters, setAiFilters] = useState({
    caixin: { aiTags: new Set(), confidenceThreshold: 0 },
    global: { aiTags: new Set(), confidenceThreshold: 0 },
    company: { aiTags: new Set(), confidenceThreshold: 0 },
    cctv: { aiTags: new Set(), confidenceThreshold: 0 },
  })

  // 使用新的新闻数据Hook（全局唯一一个实例）
  const { 
    refresh, 
    sections, 
    overallLoading, 
    overallError, 
    collectionStatus,
    collectingSections,
    pendingAnalysis,
    retryStatus,
    wsConnected,
    showEmptyModal: showEmptyModalState,
    hideEmptyModal,
    getSection,
    markRead,
    markAllRead,
    totalNewCount,
  } = useNewsData({
    date,
    symbol: symbolFilter,
    eventType: eventTypeFilter,
    tag: caixinTagFilter,
    source: globalSourceFilter,
    autoLoad: true,
  })
  
  // 调试日志
  useEffect(() => {
    console.log('NewsPage数据状态:', {
      date,
      activeTab,
      sections: Object.keys(sections).reduce((acc, key) => {
        acc[key] = {
          count: sections[key]?.data?.length || 0,
          loading: sections[key]?.loading || false,
          source: sections[key]?.stats?.source || 'unknown'
        }
        return acc
      }, {}),
      overallLoading,
      overallError,
      collectionStatus
    })
  }, [date, activeTab, sections, overallLoading, overallError, collectionStatus])

  // 处理日期变化
  const handleDateChange = (newDate) => {
    setDate(newDate)
  }

  // 排除值列表
  const EXCLUDE_VALUES = ['未提及', '无明确利好', '无明确标的', '无', '', null, undefined]

  // 检查字段是否有有效值（排除空值/占位文本）
  const hasEffectiveValue = (val) => {
    if (val == null) return false
    const trimmed = String(val).trim()
    if (trimmed === '') return false
    return !EXCLUDE_VALUES.includes(trimmed)
  }

  // AI 筛选：切换标签（多选）
  const handleAiTagToggle = (tag) => {
    setAiFilters(prev => {
      const current = prev[activeTab]
      const newTags = new Set(current.aiTags)
      if (newTags.has(tag)) newTags.delete(tag)
      else newTags.add(tag)
      return { ...prev, [activeTab]: { ...current, aiTags: newTags } }
    })
  }

  // AI 筛选：置信度滑块变更
  const handleConfidenceChange = (value) => {
    setAiFilters(prev => {
      const current = prev[activeTab]
      return { ...prev, [activeTab]: { ...current, confidenceThreshold: value } }
    })
  }

  // AI 筛选：清除当前 tab 的所有 AI 筛选
  const handleClearAiFilter = () => {
    setAiFilters(prev => ({
      ...prev,
      [activeTab]: { aiTags: new Set(), confidenceThreshold: 0 },
    }))
  }

  // 前端 AI 过滤函数
  const getFilteredNews = (tabKey, newsData) => {
    if (!newsData || newsData.length === 0) return newsData
    const filter = aiFilters[tabKey]
    const hasTags = filter.aiTags.size > 0
    const hasConf = filter.confidenceThreshold > 0
    if (!hasTags && !hasConf) return newsData

    return newsData.filter(item => {
      // aiTag 筛选（多选，任一命中即保留）
      if (hasTags) {
        let tagMatch = false
        for (const tag of filter.aiTags) {
          if (tag === 'has_benefit' && hasEffectiveValue(item.ai_interpretation)) {
            tagMatch = true; break
          }
          if (tag === 'has_stocks' && hasEffectiveValue(item.ai_benefit_stocks)) {
            tagMatch = true; break
          }
          if (tag === 'has_suppliers' && hasEffectiveValue(item.ai_key_suppliers)) {
            tagMatch = true; break
          }
        }
        if (!tagMatch) return false
      }

      // 置信度筛选：滑到多少就显示 ≥ 该值 的新闻（无数据的不参与筛选）
      if (hasConf) {
        const conf = item.sentiment_confidence
        if (conf != null) {
          if (conf * 100 < filter.confidenceThreshold) return false
        }
      }

      return true
    })
  }

  // 处理过滤确认
  const handleFilterConfirm = (symbol, eventType, caixinTag, globalSource) => {
    setSymbolFilter(symbol)
    setEventTypeFilter(eventType)
    setCaixinTagFilter(caixinTag)
    setGlobalSourceFilter(globalSource)
    setShowFilterModal(false)
    refresh()
  }

  // 重置所有筛选
  const handleResetFilters = () => {
    setSymbolFilter('')
    setEventTypeFilter('')
    setCaixinTagFilter('')
    setGlobalSourceFilter('')
    setShowFilterModal(false)
    refresh()
  }

  // 获取当前标签页的新闻统计
  const getCurrentStats = () => {
    const section = sections[activeTab]
    if (section && section.stats) {
      return section.stats
    }
    return null
  }

  const stats = getCurrentStats()

  return (
    <div style={{ 
      background: 'var(--bg-primary)', 
      minHeight: '100vh',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* 过滤弹窗 */}
      {showFilterModal && (
        <FilterModal
          activeTab={activeTab}
          symbolFilter={symbolFilter}
          setSymbolFilter={setSymbolFilter}
          eventTypeFilter={eventTypeFilter}
          setEventTypeFilter={setEventTypeFilter}
          caixinTagFilter={caixinTagFilter}
          setCaixinTagFilter={setCaixinTagFilter}
          globalSourceFilter={globalSourceFilter}
          setGlobalSourceFilter={setGlobalSourceFilter}
          onConfirm={handleFilterConfirm}
          onCancel={() => setShowFilterModal(false)}
          onReset={handleResetFilters}
        />
      )}

      {/* ===== 固定顶部区域（头部 + 标签栏）===== */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border-muted)',
        boxShadow: '0 2px 16px rgba(0,0,0,0.25)',
      }}>
        {/* 头部 */}
        <div style={{
          padding: '14px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          background: 'linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-header) 100%)',
        }}>
          {/* 左侧：标题 + 信号灯 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #1f6feb 0%, #58a6ff 50%, #79b8ff 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, 
                boxShadow: '0 4px 16px rgba(31,111,235,0.5), inset 0 1px 0 rgba(255,255,255,0.2)',
                border: '1px solid rgba(255,255,255,0.1)',
              }}>📰</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <span style={{ 
                  fontSize: 17, 
                  fontWeight: 800, 
                  color: 'var(--text-primary)', 
                  letterSpacing: '0.8px',
                  textShadow: '0 1px 2px rgba(0,0,0,0.3)',
                }}>
                  新闻资讯
                </span>
                <span style={{
                  fontSize: 10,
                  color: 'var(--text-faintest)',
                  letterSpacing: '0.5px',
                }}>实时财经数据</span>
              </div>
            </div>
          </div>
          
            {/* 中间：日期选择 */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 10,
            padding: '6px 14px',
            background: 'var(--bg-muted)',
            borderRadius: 10,
            border: '1px solid var(--border-muted)',
          }}>
            <span style={{ fontSize: 12, color: 'var(--text-faint)', whiteSpace: 'nowrap' }}>📅</span>
            <input
              type="date"
              value={date}
              onChange={(e) => handleDateChange(e.target.value)}
              className="news-date-input"
              style={{ border: 'none', background: 'transparent', padding: 0 }}
            />
          </div>
          
          {/* 右侧：筛选 + 统计 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {stats && (
              <span style={{
                fontSize: 11.5, 
                color: 'var(--text-muted)',
                padding: '6px 14px',
                background: 'linear-gradient(135deg, var(--bg-muted), var(--bg-card))',
                borderRadius: 20,
                border: '1px solid var(--border-muted)',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span style={{ color: 'var(--accent)', fontWeight: 800 }}>
                  {Object.values(sections).reduce((s, sec) => s + (sec.data?.length || 0), 0)}
                </span>
                <span>条资讯</span>
              </span>
            )}
            
            {activeTab === 'company' && (
              <button
                onClick={() => setShowFilterModal(true)}
                className="news-btn news-btn-filter"
                style={{
                  background: (symbolFilter || eventTypeFilter) 
                    ? 'linear-gradient(135deg, rgba(31,111,235,0.2), rgba(31,111,235,0.08))' 
                    : 'var(--bg-muted)',
                  borderColor: (symbolFilter || eventTypeFilter) ? 'var(--accent)' : 'var(--border-muted)',
                  color: (symbolFilter || eventTypeFilter) ? 'var(--accent)' : 'var(--text-muted)',
                  boxShadow: (symbolFilter || eventTypeFilter) ? '0 2px 12px rgba(31,111,235,0.25)' : 'none',
                }}
              >
                <span style={{ fontSize: 13 }}>⚙</span>
                {symbolFilter || eventTypeFilter ? (
                  <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {symbolFilter ? symbolFilter : ''}
                    {symbolFilter && eventTypeFilter ? ' · ' : ''}
                    {eventTypeFilter ? eventTypeFilter : ''}
                  </span>
                ) : <span>筛选</span>}
              </button>
            )}
          </div>
        </div>

        {/* AI 智能筛选栏 */}
        {(() => {
          const currentAiFilter = aiFilters[activeTab]
          const hasFilter = currentAiFilter.aiTags.size > 0
            || currentAiFilter.confidenceThreshold > 0
          const tagActive = (tag) => currentAiFilter.aiTags.has(tag)
          return (
            <div style={{
              padding: '8px 24px',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              borderTop: '1px solid var(--border-subtle)',
              borderBottom: '1px solid var(--border-subtle)',
              background: hasFilter
                ? 'linear-gradient(135deg, rgba(47,129,247,0.04), rgba(139,92,246,0.03))'
                : 'var(--bg-header)',
              flexWrap: 'wrap',
            }}>
              {/* 筛选标签 */}
              <span style={{
                fontSize: 11,
                color: 'var(--text-faint)',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                whiteSpace: 'nowrap',
              }}>
                <span style={{ fontSize: 12 }}>🤖</span> AI筛选
              </span>

              {/* 明确利好 */}
              <span
                onClick={() => handleAiTagToggle('has_benefit')}
                style={{
                  padding: '4px 12px',
                  background: tagActive('has_benefit')
                    ? 'linear-gradient(135deg, rgba(255,77,79,0.15), rgba(255,77,79,0.05))'
                    : 'var(--bg-muted)',
                  color: tagActive('has_benefit') ? '#ff7875' : 'var(--text-faint)',
                  border: `1px solid ${tagActive('has_benefit') ? 'rgba(255,77,79,0.4)' : 'var(--border-muted)'}`,
                  borderRadius: 16,
                  fontSize: 11,
                  fontWeight: tagActive('has_benefit') ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  boxShadow: tagActive('has_benefit') ? '0 2px 8px rgba(255,77,79,0.2)' : 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                📈 明确利好
              </span>

              {/* 利好个股 */}
              <span
                onClick={() => handleAiTagToggle('has_stocks')}
                style={{
                  padding: '4px 12px',
                  background: tagActive('has_stocks')
                    ? 'linear-gradient(135deg, rgba(240,180,41,0.15), rgba(240,180,41,0.05))'
                    : 'var(--bg-muted)',
                  color: tagActive('has_stocks') ? '#f0b429' : 'var(--text-faint)',
                  border: `1px solid ${tagActive('has_stocks') ? 'rgba(240,180,41,0.4)' : 'var(--border-muted)'}`,
                  borderRadius: 16,
                  fontSize: 11,
                  fontWeight: tagActive('has_stocks') ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  boxShadow: tagActive('has_stocks') ? '0 2px 8px rgba(240,180,41,0.2)' : 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                🏆 利好个股
              </span>

              {/* 核心供应商 */}
              <span
                onClick={() => handleAiTagToggle('has_suppliers')}
                style={{
                  padding: '4px 12px',
                  background: tagActive('has_suppliers')
                    ? 'linear-gradient(135deg, rgba(0,188,212,0.15), rgba(0,188,212,0.05))'
                    : 'var(--bg-muted)',
                  color: tagActive('has_suppliers') ? '#00bcd4' : 'var(--text-faint)',
                  border: `1px solid ${tagActive('has_suppliers') ? 'rgba(0,188,212,0.4)' : 'var(--border-muted)'}`,
                  borderRadius: 16,
                  fontSize: 11,
                  fontWeight: tagActive('has_suppliers') ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  boxShadow: tagActive('has_suppliers') ? '0 2px 8px rgba(0,188,212,0.2)' : 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                🔗 核心供应商
              </span>

              {/* 分隔线 */}
              <span style={{
                width: 1,
                height: 16,
                background: 'var(--border-muted)',
                margin: '0 4px',
              }} />

              {/* 置信度滑块 */}
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 11,
                color: 'var(--text-faint)',
                fontWeight: 600,
                whiteSpace: 'nowrap',
              }}>
                <span>置信度</span>
                <span style={{
                  color: currentAiFilter.confidenceThreshold > 0 ? '#58a6ff' : 'var(--text-faint)',
                  fontWeight: currentAiFilter.confidenceThreshold > 0 ? 700 : 500,
                  minWidth: 32,
                  textAlign: 'center',
                }}>
                  ≥{currentAiFilter.confidenceThreshold}%
                </span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={currentAiFilter.confidenceThreshold}
                  onChange={(e) => handleConfidenceChange(Number(e.target.value))}
                  style={{
                    width: 80,
                    height: 4,
                    accentColor: '#58a6ff',
                    cursor: 'pointer',
                    verticalAlign: 'middle',
                  }}
                  title="筛选置信度达到该值的新闻"
                />
              </span>

              {/* 有筛选时显示清除按钮和匹配数 */}
              {hasFilter && (
                <>
                  <span style={{
                    fontSize: 10,
                    color: 'var(--text-faint)',
                    padding: '3px 8px',
                    background: 'var(--bg-muted)',
                    borderRadius: 10,
                    fontWeight: 600,
                  }}>
                    匹配 {getFilteredNews(activeTab, getSection(activeTab)?.data || []).length} 条
                  </span>
                  <span
                    onClick={handleClearAiFilter}
                    style={{
                      fontSize: 11,
                      color: 'var(--text-faint)',
                      cursor: 'pointer',
                      padding: '3px 8px',
                      borderRadius: 8,
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.target.style.color = '#ff6b6b'; e.target.style.background = 'rgba(255,107,107,0.1)' }}
                    onMouseLeave={e => { e.target.style.color = 'var(--text-faint)'; e.target.style.background = 'transparent' }}
                  >
                    ✕ 清除
                  </span>
                </>
              )}
            </div>
          )
        })()}

        {/* 标签页导航 */}
        <div style={{
          display: 'flex',
          padding: '4px 16px 0',
          gap: 6,
          background: 'linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-header) 100%)',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          {[
            { key: 'caixin', label: '财新新闻', icon: '📰', desc: '财经深度分析' },
            { key: 'global', label: '全球新闻', icon: '🌍', desc: '国际市场动态' },
            { key: 'company', label: '公司动态', icon: '🏢', desc: '上市公司公告' },
            { key: 'cctv', label: '新闻联播', icon: '📺', desc: '央视重要报道' },
          ].map(tab => {
            const isActive = activeTab === tab.key
            const count = getSection(tab.key)?.data?.length || 0
            const newCount = getSection(tab.key)?.newIds?.size || 0
            return (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key)
                  // 切换到此 tab 时全部标记已读
                  if (newCount > 0) markAllRead(tab.key)
                }}
                className={`tab-button ${isActive ? 'tab-active' : ''}`}
                style={{
                  position: 'relative',
                  padding: '12px 20px',
                  background: isActive 
                    ? 'linear-gradient(180deg, var(--bg-muted) 0%, var(--bg-card) 100%)' 
                    : 'transparent',
                  border: 'none',
                  borderRadius: '10px 10px 0 0',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-faint)',
                  fontSize: 13.5,
                  fontWeight: isActive ? 700 : 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  whiteSpace: 'nowrap',
                  flex: 1,
                  justifyContent: 'center',
                }}
              >
                {/* 激活态底部指示器 */}
                {isActive && (
                  <span style={{
                    position: 'absolute',
                    bottom: 0,
                    left: '15%',
                    right: '15%',
                    height: 3,
                    background: 'linear-gradient(90deg, transparent, var(--accent), transparent)',
                    borderRadius: '3px 3px 0 0',
                    boxShadow: '0 -2px 12px var(--accent)',
                  }}/>
                )}
                
                <span style={{ 
                  fontSize: 16,
                  filter: isActive ? 'drop-shadow(0 0 6px var(--accent-dim))' : 'none',
                  transition: 'all 0.25s',
                }}>{tab.icon}</span>
                <span style={{ letterSpacing: isActive ? '0.5px' : '0' }}>{tab.label}</span>
                {count > 0 && (
                  <span style={{
                    background: isActive 
                      ? 'linear-gradient(135deg, var(--accent), #1f6feb)' 
                      : 'var(--bg-muted)',
                    color: isActive ? 'white' : 'var(--text-faint)',
                    fontSize: 10.5,
                    fontWeight: 800,
                    padding: '2px 8px',
                    borderRadius: 12,
                    border: isActive ? 'none' : '1px solid var(--border-muted)',
                    minWidth: 24,
                    textAlign: 'center',
                    boxShadow: isActive ? '0 2px 8px rgba(47,129,247,0.4)' : 'none',
                    transition: 'all 0.25s',
                  }}>
                    {count > 99 ? '99+' : count}
                  </span>
                )}
                {/* 未读 NEW 红点 */}
                {newCount > 0 && !isActive && (
                  <span style={{
                    position: 'absolute',
                    top: 6,
                    right: 10,
                    minWidth: 16,
                    height: 16,
                    background: 'linear-gradient(135deg, #ff4444, #e53935)',
                    color: 'white',
                    fontSize: 9,
                    fontWeight: 800,
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '0 4px',
                    boxShadow: '0 2px 6px rgba(229,57,53,0.5)',
                    animation: 'pulse 1.5s infinite',
                  }}>
                    {newCount > 9 ? '9+' : newCount}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* ===== 内容区域（独立滚动）===== */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {activeTab === 'company' && (
          <CompanyNewsTab
            date={date}
            news={getFilteredNews('company', getSection('company').data)}
            loading={getSection('company').loading || overallLoading}
            error={getSection('company').error || overallError}
            stats={getSection('company').stats}
            newIds={getSection('company').newIds}
            updatedIds={getSection('company').updatedIds}
            collectionStatus={collectionStatus}
            collectingSections={collectingSections}
            pendingAnalysis={pendingAnalysis}
            showEmptyModal={showEmptyModalState}
            hideEmptyModal={hideEmptyModal}
            retryStatus={retryStatus}
            onRefresh={refresh}
            onMarkRead={(id) => markRead('company', id)}
          />
        )}
        {activeTab === 'cctv' && (
          <CCTVNewsTab
            date={date}
            news={getFilteredNews('cctv', getSection('cctv').data)}
            loading={getSection('cctv').loading || overallLoading}
            error={getSection('cctv').error || overallError}
            newIds={getSection('cctv').newIds}
            updatedIds={getSection('cctv').updatedIds}
            collectionStatus={collectionStatus}
            collectingSections={collectingSections}
            retryStatus={retryStatus}
            onRefresh={refresh}
            onMarkRead={(id) => markRead('cctv', id)}
          />
        )}
        {activeTab === 'caixin' && (
          <CaixinNewsTab
            news={getFilteredNews('caixin', getSection('caixin').data)}
            loading={getSection('caixin').loading || overallLoading}
            error={getSection('caixin').error || overallError}
            newIds={getSection('caixin').newIds}
            updatedIds={getSection('caixin').updatedIds}
            retryStatus={retryStatus}
            onRefresh={refresh}
            onMarkRead={(id) => markRead('caixin', id)}
          />
        )}
        {activeTab === 'global' && (
          <GlobalNewsTab
            news={getFilteredNews('global', getSection('global').data)}
            loading={getSection('global').loading || overallLoading}
            error={getSection('global').error || overallError}
            newIds={getSection('global').newIds}
            updatedIds={getSection('global').updatedIds}
            retryStatus={retryStatus}
            onRefresh={refresh}
            onMarkRead={(id) => markRead('global', id)}
          />
        )}
      </div>

      {/* 全局样式 */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.85); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 5px var(--accent-dim), 0 0 10px var(--accent-dim); }
          50% { box-shadow: 0 0 15px var(--accent), 0 0 25px var(--accent-dim); }
        }
        :root {
          --bg-primary: #0d1117;
          --bg-elevated: #161b22;
          --bg-card: #1a1f26;
          --bg-header: #13181f;
          --bg-muted: #21262d;
          --text-primary: #e6edf3;
          --text-muted: #8b949e;
          --text-faint: #6e7681;
          --text-faintest: #3d444d;
          --border-muted: #30363d;
          --border-subtle: #21262d;
          --accent: #2f81f7;
          --accent-dim: #388bfd88;
          --accent-hover: #1f6feb;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Roboto, sans-serif; }
        
        /* 通用按钮样式 */
        .news-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 12.5px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          white-space: nowrap;
          font-family: inherit;
          border: 1px solid transparent;
        }
        .news-btn-primary {
          background: linear-gradient(135deg, var(--accent), #1f6feb);
          border-color: var(--accent);
          color: #fff;
          box-shadow: 0 2px 8px rgba(47,129,247,0.35);
        }
        .news-btn-primary:hover {
          background: linear-gradient(135deg, #388bfd, #2f81f7);
          border-color: #388bfd;
          box-shadow: 0 4px 16px rgba(47,129,247,0.5);
          transform: translateY(-1px);
        }
        .news-btn-primary:active {
          transform: translateY(0);
          box-shadow: 0 2px 8px rgba(47,129,247,0.35);
        }
        .news-btn-ghost {
          background: var(--bg-muted);
          border: 1px solid var(--border-muted);
          color: var(--text-muted);
        }
        .news-btn-ghost:hover {
          background: linear-gradient(135deg, #2d333b, var(--bg-muted));
          border-color: #484f58;
          color: var(--text-primary);
          transform: translateY(-1px);
        }
        .news-btn-filter {
          background: var(--bg-muted);
          border: 1px solid var(--border-muted);
          color: var(--text-muted);
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 12px;
        }
        .news-btn-filter:hover {
          border-color: var(--accent);
          color: var(--accent);
          box-shadow: 0 0 12px rgba(47,129,247,0.2);
        }
        
        /* 日期输入框 */
        .news-date-input {
          padding: 6px 12px;
          background: transparent;
          border: none;
          border-radius: 6px;
          color: var(--text-primary);
          font-size: 13px;
          font-family: inherit;
          cursor: pointer;
          transition: all 0.15s;
          font-weight: 500;
        }
        .news-date-input:hover { background: var(--bg-elevated); }
        .news-date-input:focus { outline: none; background: var(--bg-card); }
        
        /* 文本输入框 */
        .news-input {
          width: 100%;
          padding: 12px 16px;
          background: linear-gradient(145deg, var(--bg-muted), var(--bg-elevated));
          border: 1px solid var(--border-muted);
          border-radius: 10px;
          color: var(--text-primary);
          font-size: 14px;
          font-family: inherit;
          transition: all 0.2s;
        }
        .news-input::placeholder { color: var(--text-faint); }
        .news-input:hover { border-color: #484f58; }
        .news-input:focus { 
          outline: none; 
          border-color: var(--accent); 
          background: linear-gradient(145deg, #1d2228, var(--bg-muted));
          box-shadow: 0 0 0 3px rgba(47,129,247,0.15);
        }
        
        /* 新闻卡片悬停 */
        .news-card {
          animation: fadeIn 0.3s ease both;
        }
        .news-card:hover {
          border-color: var(--accent) !important;
          transform: translateY(-2px) scale(1.005);
          box-shadow: 0 8px 32px rgba(47,129,247,0.2), 0 0 0 1px rgba(47,129,247,0.3) !important;
        }
        .news-card:hover .arrow-icon {
          transform: translateX(3px);
        }
        
        /* 标签按钮悬停 */
        .tab-button:hover {
          background: var(--bg-muted) !important;
          color: var(--text-muted) !important;
        }
        .tab-button.tab-active:hover {
          background: linear-gradient(180deg, var(--bg-muted) 0%, var(--bg-card) 100%) !important;
          color: var(--text-primary) !important;
        }
        
        /* 弹窗动画 */
        .filter-modal-overlay {
          animation: fadeIn 0.2s ease;
        }
        .filter-modal-content {
          animation: slideUp 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* 滚动条美化 */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { 
          background: linear-gradient(180deg, #30363d, #3d444d); 
          border-radius: 3px; 
        }
        ::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, #484f58, #555d66); }
        
        button:focus, input:focus { outline: none; }
        
        /* 新闻列表项动画 - 交错出现 */
        .news-list-item { 
          animation: fadeIn 0.3s ease both;
        }
        .news-list-item:nth-child(1) { animation-delay: 0.02s; }
        .news-list-item:nth-child(2) { animation-delay: 0.04s; }
        .news-list-item:nth-child(3) { animation-delay: 0.06s; }
        .news-list-item:nth-child(4) { animation-delay: 0.08s; }
        .news-list-item:nth-child(5) { animation-delay: 0.10s; }
        .news-list-item:nth-child(6) { animation-delay: 0.12s; }
        .news-list-item:nth-child(7) { animation-delay: 0.14s; }
        .news-list-item:nth-child(8) { animation-delay: 0.16s; }
        .news-list-item:nth-child(9) { animation-delay: 0.18s; }
        .news-list-item:nth-child(10) { animation-delay: 0.20s; }
      `}</style>
    </div>
  )
}