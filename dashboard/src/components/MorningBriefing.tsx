import { useState, useEffect } from 'react'
import { getKernelStatus, getTasks } from '../lib/api'

export default function MorningBriefing() {
  const [briefing, setBriefing] = useState<string[]>([])
  const now = new Date()
  const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  const date = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })

  useEffect(() => {
    async function fetchBriefing() {
      const items: string[] = []
      try {
        // Get kernel status
        const kernel = await getKernelStatus()
        const running = Object.values(kernel).filter((a: any) => a.running).length
        items.push(`${running}/7 kernel agents running.`)

        // Check for errors
        const errors = Object.values(kernel).filter((a: any) => a.error).length
        if (errors > 0) {
          items.push(`${errors} kernel agents have errors.`)
        } else {
          items.push('No kernel errors detected.')
        }

        // Get pending tasks
        const tasks = await getTasks()
        const pending = tasks.tasks.filter((t: any) => t.status === 'todo').length
        if (pending > 0) {
          items.push(`${pending} pending tasks require review.`)
        } else {
          items.push('No pending tasks.')
        }
      } catch {
        items.push('System status unavailable.')
      }
      setBriefing(items)
    }
    fetchBriefing()
  }, [])

  return (
    <div className="hud-panel">
      <div className="hud-title">Morning Briefing</div>
      <p className="text-xs text-kaihara-muted mb-2">{date} • {time}</p>
      <div className="space-y-1.5 text-xs">
        {briefing.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-kaihara-accent">▸</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
