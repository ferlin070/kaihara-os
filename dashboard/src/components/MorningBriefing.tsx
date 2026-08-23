import { useState, useEffect } from 'react'
import { getKernelStatus, getTasks } from '../lib/api'

export default function MorningBriefing() {
  const [briefing, setBriefing] = useState<string[]>([])
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)
  const now = new Date()
  const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  const date = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })

  const fetchBriefing = async () => {
    setLoading(true)
    const items: string[] = []
    try {
      const kernel = await getKernelStatus()
      const running = Object.values(kernel).filter((a: any) => a.running).length
      items.push(`${running}/7 kernel agents running.`)

      const errors = Object.values(kernel).filter((a: any) => a.error).length
      if (errors > 0) {
        items.push(`${errors} kernel agents have errors.`)
      } else {
        items.push('No kernel errors detected.')
      }

      const tasks = await getTasks()
      const pending = tasks.tasks.filter((t: any) => t.status === 'todo').length
      if (pending > 0) {
        items.push(`${pending} pending tasks require review.`)
      } else {
        items.push('No pending tasks.')
      }
      setLastUpdate(new Date())
    } catch {
      items.push('System status unavailable.')
    }
    setBriefing(items)
    setLoading(false)
  }

  useEffect(() => {
    fetchBriefing()
    const interval = setInterval(fetchBriefing, 60000) // Refresh every 60s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="hud-panel">
      <div className="flex items-center justify-between">
        <div className="hud-title">Morning Briefing</div>
        <button
          onClick={fetchBriefing}
          disabled={loading}
          className="text-xs text-kaihara-muted hover:text-kaihara-accent disabled:opacity-50"
          title="Refresh"
        >
          {loading ? '⟳' : '↻'}
        </button>
      </div>
      <p className="text-xs text-kaihara-muted mb-2">{date} • {time}</p>
      <div className="space-y-1.5 text-xs">
        {briefing.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-kaihara-accent">▸</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
      {lastUpdate && (
        <p className="text-xs text-kaihara-muted mt-2 opacity-60">
          Updated {Math.floor((Date.now() - lastUpdate.getTime()) / 1000)}s ago
        </p>
      )}
    </div>
  )
}
