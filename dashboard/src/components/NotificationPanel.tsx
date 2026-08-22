import { useState, useEffect } from 'react'
import { getAuditLog } from '../lib/api'

interface Notif {
  type: string
  text: string
}

export default function NotificationPanel({ notifications }: { notifications: Notif[] }) {
  const [notifs, setNotifs] = useState<Notif[]>(notifications)

  useEffect(() => {
    async function fetchNotifications() {
      try {
        const audit = await getAuditLog(5)
        const items = audit.entries.map((e: any) => ({
          type: e.severity === 'high' ? 'error' : e.severity === 'medium' ? 'warning' : 'info',
          text: `${e.agent}: ${e.action}`
        }))
        setNotifs(items.length > 0 ? items : [{ type: 'info', text: 'System initialized.' }])
      } catch {
        setNotifs([{ type: 'info', text: 'System initialized.' }])
      }
    }
    if (notifications.length === 0) {
      fetchNotifications()
    }
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
      <div className="space-y-1.5">
        {notifs.map((n, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span>{typeIcons[n.type] || '•'}</span>
            <span className={typeColors[n.type] || ''}>{n.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
