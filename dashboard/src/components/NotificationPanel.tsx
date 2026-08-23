import { useState, useEffect } from 'react'
import { getAuditLog } from '../lib/api'

interface Notif {
  type: string
  text: string
  timestamp?: string
}

function timeAgo(ts: string): string {
  if (!ts) return ''
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function NotificationPanel({ notifications }: { notifications: Notif[] }) {
  const [notifs, setNotifs] = useState<Notif[]>(notifications)

  const fetchNotifications = async () => {
    try {
      const audit = await getAuditLog(8)
      const items = audit.entries.map((e: any) => ({
        type: e.severity === 'high' ? 'error' : e.severity === 'medium' ? 'warning' : 'info',
        text: `${e.agent}: ${e.action}`,
        timestamp: e.timestamp,
      }))
      setNotifs(items.length > 0 ? items : [{ type: 'info', text: 'System initialized.' }])
    } catch {
      setNotifs([{ type: 'info', text: 'System initialized.' }])
    }
  }

  useEffect(() => {
    if (notifications.length === 0) {
      fetchNotifications()
    }
    const interval = setInterval(fetchNotifications, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [notifications])

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
      <div className="space-y-1.5 max-h-40 overflow-y-auto">
        {notifs.map((n, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span>{typeIcons[n.type] || '•'}</span>
            <div className="flex-1 min-w-0">
              <span className={typeColors[n.type] || ''}>{n.text}</span>
              {n.timestamp && (
                <span className="text-kaihara-muted ml-1">({timeAgo(n.timestamp)})</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
