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
