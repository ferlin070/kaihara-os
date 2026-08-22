export default function GoalsTracker() {
  const goals = [
    { title: 'Build Kaihara Dashboard', status: 'doing', priority: 'high' },
    { title: 'Install Ollama + test chat', status: 'todo', priority: 'high' },
    { title: 'Build Planning Pipeline (PRD)', status: 'todo', priority: 'medium' },
    { title: 'Setup Telegram channel', status: 'todo', priority: 'low' },
  ]

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

  return (
    <div className="hud-panel">
      <div className="hud-title">Today's Goals</div>
      <div className="space-y-1.5">
        {goals.map((goal, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span>{statusIcon[goal.status]}</span>
            <span className={`flex-1 ${goal.status === 'done' ? 'line-through text-kaihara-muted' : ''}`}>
              {goal.title}
            </span>
            <span className={`text-xs ${priorityColor[goal.priority]}`}>
              {goal.priority}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
