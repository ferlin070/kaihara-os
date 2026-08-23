import { useState, useEffect } from 'react'
import { getDaemonStatus, type DaemonStatus } from '../lib/api'

function formatUptime(seconds: number): string {
  if (!seconds) return '--'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export default function KaiharaStatus({ thinking, online }: { thinking: boolean; online: boolean }) {
  const [daemon, setDaemon] = useState<DaemonStatus | null>(null)
  const state = thinking ? 'thinking' : online ? 'online' : 'offline'
  const colors = {
    online: 'bg-kaihara-success',
    thinking: 'bg-kaihara-warning',
    offline: 'bg-kaihara-danger',
  }
  const labels = {
    online: 'ONLINE',
    thinking: 'THINKING',
    offline: 'OFFLINE',
  }

  useEffect(() => {
    getDaemonStatus().then(setDaemon).catch(() => {})
    const interval = setInterval(() => {
      getDaemonStatus().then(setDaemon).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="hud-panel">
      <div className="hud-title">Kaihara Status</div>
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent
                        flex items-center justify-center text-white font-bold text-xl">
          K
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className={`status-dot ${colors[state]} animate-pulse`} />
            <span className="text-sm font-bold">{labels[state]}</span>
          </div>
          <p className="text-xs text-kaihara-muted">kaihara-os v0.1.0</p>
        </div>
      </div>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-kaihara-muted">Mode</span>
          <span>Privacy (local)</span>
        </div>
        <div className="flex justify-between">
          <span className="text-kaihara-muted">Memory</span>
          <span className="text-kaihara-success">Active</span>
        </div>
        <div className="flex justify-between">
          <span className="text-kaihara-muted">TokenJuice</span>
          <span className="text-kaihara-success">On</span>
        </div>
        {daemon?.process && (
          <>
            <div className="flex justify-between">
              <span className="text-kaihara-muted">CPU</span>
              <span className="font-mono">{daemon.process.cpu_percent?.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-kaihara-muted">RAM</span>
              <span className="font-mono">{daemon.process.memory_mb} MB</span>
            </div>
            <div className="flex justify-between">
              <span className="text-kaihara-muted">Uptime</span>
              <span className="font-mono">{formatUptime(daemon.process.uptime_seconds)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-kaihara-muted">Agents</span>
              <span className="font-mono text-kaihara-success">{daemon.agents.running}/{daemon.agents.total}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
