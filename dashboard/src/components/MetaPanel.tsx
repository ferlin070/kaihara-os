import { useState, useEffect, useCallback } from 'react'
import {
  getMetaStatus,
  getMetaSuggestions,
  getMetaPatterns,
  analyzeFleet,
  type MetaSuggestion,
  type MetaPattern,
} from '../lib/api'

const severityColors: Record<string, string> = {
  critical: 'text-kaihara-danger',
  warning: 'text-kaihara-warning',
  info: 'text-kaihara-accent',
}

const severityBorders: Record<string, string> = {
  critical: 'border-l-kaihara-danger',
  warning: 'border-l-kaihara-warning',
  info: 'border-l-kaihara-accent',
}

export default function MetaPanel() {
  const [status, setStatus] = useState<any>(null)
  const [suggestions, setSuggestions] = useState<MetaSuggestion[]>([])
  const [patterns, setPatterns] = useState<MetaPattern[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [message, setMessage] = useState('')

  const fetchAll = useCallback(async () => {
    try {
      const [st, sug, pat] = await Promise.all([
        getMetaStatus(),
        getMetaSuggestions(),
        getMetaPatterns(),
      ])
      setStatus(st)
      setSuggestions(sug.suggestions || [])
      setPatterns(pat.patterns || [])
    } catch {}
  }, [])

  useEffect(() => {
    fetchAll()
    const i = setInterval(fetchAll, 30000)
    return () => clearInterval(i)
  }, [fetchAll])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const res = await analyzeFleet()
      setMessage(res.message || '')
      fetchAll()
    } catch {}
    setAnalyzing(false)
  }

  const cache = status?.cache || {}
  const critCount = patterns.filter(p => p.severity === 'critical').length
  const warnCount = patterns.filter(p => p.severity === 'warning').length

  return (
    <div className="hud-panel">
      <div className="flex items-center justify-between mb-2">
        <div className="hud-title mb-0">Meta Agent</div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="text-xs px-2 py-0.5 rounded bg-kaihara-accent text-white hover:opacity-80 disabled:opacity-50"
        >
          {analyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {/* Cache stats */}
      <div className="grid grid-cols-3 gap-1 mb-3 text-xs">
        <div className="text-center">
          <div className="text-kaihara-accent font-bold">{cache.cached_tasks || 0}</div>
          <div className="text-kaihara-muted">Cached</div>
        </div>
        <div className="text-center">
          <div className="text-kaihara-success font-bold">{cache.cache_hits || 0}</div>
          <div className="text-kaihara-muted">Hits</div>
        </div>
        <div className="text-center">
          <div className="text-kaihara-warning font-bold">{cache.tokens_saved || 0}</div>
          <div className="text-kaihara-muted">Tokens Saved</div>
        </div>
      </div>

      {/* Alert summary */}
      {(critCount > 0 || warnCount > 0) && (
        <div className="mb-2 text-xs space-y-0.5">
          {critCount > 0 && (
            <div className="text-kaihara-danger">
              {critCount} critical issue{critCount > 1 ? 's' : ''}
            </div>
          )}
          {warnCount > 0 && (
            <div className="text-kaihara-warning">
              {warnCount} warning{warnCount > 1 ? 's' : ''}
            </div>
          )}
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="mb-2">
          <div className="text-xs text-kaihara-muted mb-1">Suggestions:</div>
          <div className="space-y-1">
            {suggestions.slice(0, 3).map((s, i) => (
              <div key={i} className={`text-xs pl-2 border-l-2 ${
                severityBorders[s.severity] || 'border-l-kaihara-muted'
              }`}>
                <span className={severityColors[s.severity]}>
                  [{s.agent}]
                </span>{' '}
                {s.suggestion}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patterns */}
      {patterns.length > 0 && (
        <div className="mb-2">
          <div className="text-xs text-kaihara-muted mb-1">Patterns:</div>
          <div className="space-y-1">
            {patterns.slice(0, 3).map(p => (
              <div key={p.id} className={`text-xs pl-2 border-l-2 ${
                severityBorders[p.severity] || 'border-l-kaihara-muted'
              }`}>
                <span className={severityColors[p.severity]}>
                  [{p.agent}] x{p.frequency}
                </span>{' '}
                {p.description}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className="text-xs text-kaihara-accent mt-2 pt-2 border-t border-kaihara-border">
          {message}
        </div>
      )}

      {/* Empty state */}
      {!suggestions.length && !patterns.length && (
        <p className="text-xs text-kaihara-muted">
          Fleet running efficiently. No issues detected.
        </p>
      )}
    </div>
  )
}
