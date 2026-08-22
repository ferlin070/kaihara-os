interface Notif {
  type: string
  text: string
}

export default function NotificationPanel({ notifications }: { notifications: Notif[] }) {
  const defaultNotifs: Notif[] = notifications.length > 0 ? notifications : [
    { type: 'info', text: 'Kaihara OS initialized.' },
    { type: 'warning', text: 'Ollama not running. Start with: ollama serve' },
  ]

  const typeIcons: Record<string, string> = {
    info: 'ℹ️',
    warning: '⚠️',
    error: '❌',
    success: '✅',
  }
  const typeColors: Record<string, string> = {
    info: 'text-kaihara-accent',
    warning: 'text-kaihara-warning',
    error: 'text-kaihara-danger',
    success: 'text-kaihara-success',
  }

  return (
    <div className="hud-panel">
      <div className="hud-title">Notifications</div>
      <div className="space-y-1.5">
        {defaultNotifs.map((n, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span>{typeIcons[n.type] || '•'}</span>
            <span className={typeColors[n.type] || ''}>{n.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
