import { useState, useEffect } from 'react'
import { getApprovals, type Approval } from '../lib/api'

export default function PendingApprovals() {
  const [pending, setPending] = useState<Approval[]>([])

  useEffect(() => {
    async function fetchApprovals() {
      try {
        const data = await getApprovals()
        setPending(data.pending || [])
      } catch {
        setPending([])
      }
    }
    fetchApprovals()
    const interval = setInterval(fetchApprovals, 30000) // Check every 15s
    return () => clearInterval(interval)
  }, [])

  if (pending.length === 0) return null

  return (
    <div className="hud-panel border-kaihara-warning/50">
      <div className="flex items-center justify-between mb-2">
        <div className="hud-title text-kaihara-warning">Pending Approvals</div>
        <span className="text-xs bg-kaihara-warning/20 text-kaihara-warning px-1.5 py-0.5 rounded font-mono">
          {pending.length}
        </span>
      </div>
      <div className="space-y-1.5">
        {pending.slice(0, 3).map((item) => (
          <div key={item.id} className="text-xs">
            <span className="text-kaihara-text">{item.action}</span>
            <span className="text-kaihara-muted ml-1">by {item.agent}</span>
          </div>
        ))}
        {pending.length > 3 && (
          <p className="text-xs text-kaihara-muted">+{pending.length - 3} more</p>
        )}
      </div>
      <a href="#security" className="block mt-2 text-xs text-kaihara-accent hover:underline">
        Review in Security tab →
      </a>
    </div>
  )
}
