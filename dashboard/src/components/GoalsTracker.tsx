import { useState, useEffect } from 'react'
import { getGoals } from '../lib/api'

export default function GoalsTracker() {
  const [goals, setGoals] = useState<any[]>([])

  useEffect(() => {
    async function fetchGoals() {
      try {
        const data = await getGoals()
        setGoals(data.goals || [])
      } catch {
        setGoals([])
      }
    }
    fetchGoals()
    const interval = setInterval(fetchGoals, 60000) // Refresh every 60s
    return () => clearInterval(interval)
  }, [])

  const statusIcon: Record<string, string> = {
    done: '✅',
    doing: '🔄',
    todo: '□',
    blocked: '⛔',
  }
  const priorityColor: Record<string, string> = {
    high: 'text-kaihara-danger',
    medium: 'text-kaihara-warning',
    low: 'text-kaihara-muted',
  }

  const done = goals.filter(g => g.status === 'done').length
  const total = goals.length
  const pct = total > 0 ? (done / total) * 100 : 0

  if (goals.length === 0) {
    return (
      <div className="hud-panel">
        <div className="hud-title">Today's Goals</div>
        <p className="text-xs text-kaihara-muted">No goals set.</p>
      </div>
    )
  }

  return (
    <div className="hud-panel">
      <div className="hud-title">Today's Goals</div>

      {/* Progress summary */}
      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">{done}/{total} completed</span>
          <span className="text-kaihara-accent font-mono">{Math.round(pct)}%</span>
        </div>
        <div className="w-full h-1.5 bg-kaihara-border rounded overflow-hidden">
          <div
            className="h-full bg-kaihara-accent transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        {goals.map((goal, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span>{statusIcon[goal.status] || '□'}</span>
            <span className={`flex-1 ${goal.status === 'done' ? 'line-through text-kaihara-muted' : ''}`}>
              {goal.title}
            </span>
            <span className={`text-xs ${priorityColor[goal.priority] || 'text-kaihara-muted'}`}>
              {goal.priority}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
