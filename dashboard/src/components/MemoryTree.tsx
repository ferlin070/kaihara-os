import { useState, useEffect, useCallback, useRef } from 'react'
import {
  recallMemory,
  getMemoryStats,
  getMemoryBrowse,
  type MemoryResult,
  type MemoryStats,
} from '../lib/api'

const TOPICS = [
  { id: 'all', label: 'All', color: '#6b7280' },
  { id: 'coding', label: 'Coding', color: '#3b82f6' },
  { id: 'security', label: 'Security', color: '#ef4444' },
  { id: 'marketing', label: 'Marketing', color: '#10b981' },
  { id: 'research', label: 'Research', color: '#8b5cf6' },
  { id: 'personal', label: 'Personal', color: '#f59e0b' },
  { id: 'general', label: 'General', color: '#6b7280' },
  { id: 'daily', label: 'Daily', color: '#06b6d4' },
]

const TIERS = [
  { id: 'all', label: 'All Tiers', icon: '🌳' },
  { id: 'raw', label: 'Raw', icon: '📝' },
  { id: 'summary', label: 'Summary', icon: '📋' },
  { id: 'canvas', label: 'Canvas', icon: '🎨' },
]

export default function MemoryTree() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<MemoryResult[]>([])
  const [searching, setSearching] = useState(false)
  const [stats, setStats] = useState<MemoryStats | null>(null)
  const [selectedTopic, setSelectedTopic] = useState('all')
  const [selectedTier, setSelectedTier] = useState('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [browseResults, setBrowseResults] = useState<MemoryResult[]>([])
  const [activeView, setActiveView] = useState<'search' | 'browse' | 'stats'>('search')
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Load stats on mount
  useEffect(() => {
    getMemoryStats().then(setStats).catch(() => {})
  }, [])

  // Debounced search
  const handleSearch = useCallback((q: string) => {
    setQuery(q)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    if (!q.trim()) {
      setResults([])
      return
    }
    searchTimeoutRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const data = await recallMemory(q, 20)
        setResults(data.results || [])
      } catch {
        setResults([])
      }
      setSearching(false)
    }, 300)
  }, [])

  // Browse by topic
  useEffect(() => {
    if (activeView !== 'browse') return
    const topic = selectedTopic === 'all' ? undefined : selectedTopic
    getMemoryBrowse(topic, 50).then(data => {
      setBrowseResults(data.results || [])
    }).catch(() => setBrowseResults([]))
  }, [activeView, selectedTopic])

  // Filter results by topic and tier
  const filteredResults = (activeView === 'search' ? results : browseResults).filter(r => {
    if (selectedTopic !== 'all' && r.topic !== selectedTopic) return false
    if (selectedTier !== 'all' && r.tier !== selectedTier) return false
    return true
  })

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold uppercase tracking-wide">Memory Tree</h2>
            {stats && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-kaihara-border text-kaihara-muted">
                {stats.total_memories} memories
              </span>
            )}
          </div>
          <div className="flex gap-1">
            {(['search', 'browse', 'stats'] as const).map(v => (
              <button key={v} onClick={() => setActiveView(v)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  activeView === v
                    ? 'bg-kaihara-accent text-white'
                    : 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-text'
                }`}>
                {v === 'search' ? 'Search' : v === 'browse' ? 'Browse' : 'Stats'}
              </button>
            ))}
          </div>
        </div>

        {/* Search Input */}
        {activeView === 'search' && (
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Search memories... (e.g., 'how to deploy', 'agent architecture')"
              className="w-full bg-kaihara-bg border border-kaihara-border rounded-lg px-4 py-2.5 text-sm text-kaihara-text placeholder:text-kaihara-muted focus:outline-none focus:border-kaihara-accent"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-4 h-4 border-2 border-kaihara-accent border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
        )}

        {/* Topic Filter */}
        <div className="flex gap-1.5 mt-2 flex-wrap">
          {TOPICS.map(t => (
            <button key={t.id} onClick={() => setSelectedTopic(t.id)}
              className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                selectedTopic === t.id
                  ? 'text-white'
                  : 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-text'
              }`}
              style={selectedTopic === t.id ? { backgroundColor: t.color } : {}}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Tier Filter */}
        {activeView !== 'stats' && (
          <div className="flex gap-1.5 mt-2">
            {TIERS.map(t => (
              <button key={t.id} onClick={() => setSelectedTier(t.id)}
                className={`px-2 py-0.5 text-xs rounded transition-colors ${
                  selectedTier === t.id
                    ? 'bg-kaihara-accent text-white'
                    : 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-text'
                }`}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-2">
        {/* Search Results */}
        {activeView === 'search' && (
          <>
            {results.length === 0 && !searching && query && (
              <div className="text-center text-kaihara-muted text-sm py-8">
                No memories found for "{query}"
              </div>
            )}
            {results.length === 0 && !query && (
              <div className="text-center text-kaihara-muted text-sm py-8">
                Type something to search your memories
              </div>
            )}
            {filteredResults.map((r, i) => (
              <MemoryCard
                key={`${r.summary_id}-${i}`}
                memory={r}
                expanded={expandedId === r.summary_id}
                onToggle={() => setExpandedId(expandedId === r.summary_id ? null : r.summary_id)}
              />
            ))}
          </>
        )}

        {/* Browse View */}
        {activeView === 'browse' && (
          <>
            {browseResults.length === 0 && (
              <div className="text-center text-kaihara-muted text-sm py-8">
                No memories in this topic
              </div>
            )}
            {filteredResults.map((r, i) => (
              <MemoryCard
                key={`${r.summary_id}-${i}`}
                memory={r}
                expanded={expandedId === r.summary_id}
                onToggle={() => setExpandedId(expandedId === r.summary_id ? null : r.summary_id)}
              />
            ))}
          </>
        )}

        {/* Stats View */}
        {activeView === 'stats' && stats && (
          <StatsView stats={stats} />
        )}
      </div>
    </div>
  )
}

// ============================================================
// Memory Card Component
// ============================================================

function MemoryCard({ memory, expanded, onToggle }: {
  memory: MemoryResult
  expanded: boolean
  onToggle: () => void
}) {
  const topicColor = TOPICS.find(t => t.id === memory.topic)?.color || '#6b7280'
  const scorePercent = Math.round(memory.score * 100)

  return (
    <div className="border border-kaihara-border rounded-lg overflow-hidden hover:border-kaihara-accent/50 transition-colors">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full px-3 py-2.5 flex items-start gap-3 text-left hover:bg-kaihara-border/30"
      >
        {/* Topic Badge */}
        <span
          className="px-2 py-0.5 text-xs rounded-full text-white flex-shrink-0 mt-0.5"
          style={{ backgroundColor: topicColor }}
        >
          {memory.topic}
        </span>

        {/* Content Preview */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-kaihara-text line-clamp-2">{memory.content}</p>
          <div className="flex items-center gap-2 mt-1">
            {memory.tags.slice(0, 3).map(tag => (
              <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-kaihara-border text-kaihara-muted">
                {tag}
              </span>
            ))}
            {memory.tags.length > 3 && (
              <span className="text-xs text-kaihara-muted">+{memory.tags.length - 3}</span>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="flex-shrink-0 text-right">
          <div className="text-xs text-kaihara-muted">Score</div>
          <div className={`text-sm font-bold ${scorePercent > 70 ? 'text-kaihara-success' : scorePercent > 40 ? 'text-yellow-500' : 'text-kaihara-muted'}`}>
            {scorePercent}%
          </div>
        </div>

        {/* Expand Arrow */}
        <svg className={`w-4 h-4 text-kaihara-muted flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-3 py-2.5 border-t border-kaihara-border bg-kaihara-bg/50">
          <div className="grid grid-cols-2 gap-2 text-xs mb-2">
            <div>
              <span className="text-kaihara-muted">ID:</span>{' '}
              <span className="text-kaihara-text font-mono">{memory.summary_id}</span>
            </div>
            <div>
              <span className="text-kaihara-muted">Tier:</span>{' '}
              <span className="text-kaihara-text">{memory.tier || 'summary'}</span>
            </div>
            <div>
              <span className="text-kaihara-muted">Topic:</span>{' '}
              <span className="text-kaihara-text">{memory.topic}</span>
            </div>
            <div>
              <span className="text-kaihara-muted">Score:</span>{' '}
              <span className="text-kaihara-text">{memory.score.toFixed(3)}</span>
            </div>
          </div>
          {memory.raw_content && (
            <div className="mt-2">
              <div className="text-xs text-kaihara-muted mb-1">Raw Content:</div>
              <div className="text-xs text-kaihara-text bg-kaihara-bg p-2 rounded border border-kaihara-border max-h-32 overflow-y-auto font-mono">
                {memory.raw_content}
              </div>
            </div>
          )}
          <div className="mt-2">
            <div className="text-xs text-kaihara-muted mb-1">Summary:</div>
            <div className="text-xs text-kaihara-text">{memory.content}</div>
          </div>
          {memory.mermaid && (
            <div className="mt-2">
              <div className="text-xs text-kaihara-muted mb-1">Canvas (Mermaid):</div>
              <div className="text-xs text-kaihara-text bg-kaihara-bg p-2 rounded border border-kaihara-border font-mono">
                {memory.mermaid}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================
// Stats View
// ============================================================

function StatsView({ stats }: { stats: MemoryStats }) {
  return (
    <div className="space-y-4">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Total Memories" value={stats.total_memories} icon="🧠" />
        <StatCard label="Raw Tier" value={stats.raw_count} icon="📝" />
        <StatCard label="Summary Tier" value={stats.summary_count} icon="📋" />
        <StatCard label="Canvas Tier" value={stats.canvas_count} icon="🎨" />
      </div>

      {/* Topic Distribution */}
      <div className="border border-kaihara-border rounded-lg p-4">
        <h3 className="text-sm font-bold mb-3">Topic Distribution</h3>
        <div className="space-y-2">
          {Object.entries(stats.topics || {}).map(([topic, count]) => {
            const maxCount = Math.max(...Object.values(stats.topics || {}).map(Number))
            const percent = maxCount > 0 ? (count / maxCount) * 100 : 0
            const color = TOPICS.find(t => t.id === topic)?.color || '#6b7280'
            return (
              <div key={topic} className="flex items-center gap-3">
                <span className="text-xs text-kaihara-muted w-20 truncate">{topic}</span>
                <div className="flex-1 h-2 bg-kaihara-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${percent}%`, backgroundColor: color }}
                  />
                </div>
                <span className="text-xs text-kaihara-text w-8 text-right">{count}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Daily Memory */}
      <div className="border border-kaihara-border rounded-lg p-4">
        <h3 className="text-sm font-bold mb-2">Daily Memory</h3>
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌙</span>
          <div>
            <div className="text-sm text-kaihara-text">{stats.daily_count || 0} distilled days</div>
            <div className="text-xs text-kaihara-muted">Nightly deep dream compression</div>
          </div>
        </div>
      </div>

      {/* Goals */}
      <div className="border border-kaihara-border rounded-lg p-4">
        <h3 className="text-sm font-bold mb-2">Goals</h3>
        <div className="flex items-center gap-2">
          <span className="text-2xl">🎯</span>
          <div>
            <div className="text-sm text-kaihara-text">{stats.goals_count || 0} active goals</div>
            <div className="text-xs text-kaihara-muted">Tracked objectives</div>
          </div>
        </div>
      </div>

      {/* Vector DB */}
      <div className="border border-kaihara-border rounded-lg p-4">
        <h3 className="text-sm font-bold mb-2">Vector Database</h3>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{stats.vector_available ? '✅' : '❌'}</span>
          <div>
            <div className="text-sm text-kaihara-text">
              {stats.vector_available ? 'ChromaDB Connected' : 'ChromaDB Unavailable'}
            </div>
            <div className="text-xs text-kaihara-muted">
              {stats.vector_count || 0} vectors stored
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="border border-kaihara-border rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-kaihara-muted">{label}</span>
      </div>
      <div className="text-2xl font-bold text-kaihara-text">{value}</div>
    </div>
  )
}
