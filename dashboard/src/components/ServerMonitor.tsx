import { useState, useEffect, useCallback } from 'react'

interface MonServer {
  name: string
  role: string
  ip: string | null
  via: string | null
  status: 'UP' | 'DOWN'
  latency_ms: number | null
  tailscale_online: boolean | null
}

interface MonitorData {
  servers: MonServer[]
  summary: { total: number; up: number; down: number }
  internet: { internet_up: boolean; avg_latency_ms?: number; dns_ok?: boolean } | null
  host_system: {
    cpu_percent: number
    ram_percent: number
    ram_used_gb: number
    ram_total_gb: number
    disk_percent: number
    disk_free_gb: number
    load: { '1m': number }
    net_mb_sent: number
    net_mb_recv: number
  } | null
  proxmox_guests: { running: number; total: number } | null
  timestamp: number
}

function getApiBase() {
  if (window.location.hostname === 'kaihara-ai.nakhodacloud.top') {
    return 'https://kaihara-api.nakhodacloud.top/api'
  }
  return '/api'
}

export default function ServerMonitor() {
  const [data, setData] = useState<MonitorData | null>(null)
  const [error, setError] = useState(false)

  const fetchServers = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBase()}/monitor/servers`)
      if (!res.ok) throw new Error('fail')
      setData(await res.json())
      setError(false)
    } catch {
      setError(true)
    }
  }, [])

  useEffect(() => {
    fetchServers()
    const i = setInterval(fetchServers, 10000)
    return () => clearInterval(i)
  }, [fetchServers])

  if (error && !data) {
    return (
      <div className="hud-panel">
        <div className="hud-title">🖥️ Server Monitor</div>
        <p className="text-xs text-kaihara-danger">Connection error.</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="hud-panel">
        <div className="hud-title">🖥️ Server Monitor</div>
        <p className="text-xs text-kaihara-muted">Loading...</p>
      </div>
    )
  }

  const { summary, internet, host_system, proxmox_guests } = data
  const mainServers = data.servers.filter(s =>
    !s.role.startsWith('CT'))
  const ctServers = data.servers.filter(s => s.role.startsWith('CT'))

  return (
    <div className="space-y-3">
      {/* Header + Internet */}
      <div className="hud-panel">
        <div className="flex items-center justify-between mb-2">
          <div className="hud-title">🖥️ Server Monitor</div>
          <span className={`text-xs font-bold ${internet?.internet_up ? 'text-kaihara-success' : 'text-kaihara-danger'}`}>
            🌐 INTERNET {internet?.internet_up ? 'UP' : 'DOWN'}
            {internet?.avg_latency_ms ? ` (${internet.avg_latency_ms}ms)` : ''}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="bg-kaihara-bg rounded p-2">
            <div className="text-kaihara-success font-bold">{summary.up}</div>
            <div className="text-kaihara-muted">UP</div>
          </div>
          <div className="bg-kaihara-bg rounded p-2">
            <div className="text-kaihara-danger font-bold">{summary.down}</div>
            <div className="text-kaihara-muted">DOWN</div>
          </div>
          <div className="bg-kaihara-bg rounded p-2">
            <div className="text-kaihara-accent font-bold">{summary.total}</div>
            <div className="text-kaihara-muted">TOTAL</div>
          </div>
        </div>
      </div>

      {/* Host system (cloudhosting) */}
      {host_system && (
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold">☁️ cloudhosting (Proxmox)</span>
            <span className="text-[10px] text-kaihara-muted">
              load {host_system.load['1m'].toFixed(1)}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <div className="flex justify-between text-kaihara-muted mb-0.5">
                <span>CPU</span><span>{host_system.cpu_percent}%</span>
              </div>
              <div className="h-1.5 bg-kaihara-border rounded overflow-hidden">
                <div className="h-full bg-kaihara-primary" style={{ width: `${host_system.cpu_percent}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-kaihara-muted mb-0.5">
                <span>RAM</span><span>{host_system.ram_used_gb}/{host_system.ram_total_gb}G</span>
              </div>
              <div className="h-1.5 bg-kaihara-border rounded overflow-hidden">
                <div className="h-full bg-kaihara-warning" style={{ width: `${host_system.ram_percent}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-kaihara-muted mb-0.5">
                <span>Disk</span><span>{host_system.disk_free_gb}G free</span>
              </div>
              <div className="h-1.5 bg-kaihara-border rounded overflow-hidden">
                <div className="h-full bg-kaihara-success" style={{ width: `${host_system.disk_percent}%` }} />
              </div>
            </div>
          </div>
          {proxmox_guests && (
            <p className="text-[10px] text-kaihara-muted mt-1.5">
              📦 Guests: {proxmox_guests.running}/{proxmox_guests.total} running
              {' • '}↑{host_system.net_mb_sent}MB ↓{host_system.net_mb_recv}MB
            </p>
          )}
        </div>
      )}

      {/* Main servers */}
      <div className="hud-panel space-y-1.5">
        <div className="hud-title mb-1">🖧 Servers</div>
        {mainServers.map(s => (
          <ServerRow key={s.name} s={s} />
        ))}
      </div>

      {/* CT group */}
      <div className="hud-panel space-y-1.5">
        <div className="hud-title mb-1">📦 Containers</div>
        {ctServers.map(s => (
          <ServerRow key={s.name} s={s} compact />
        ))}
      </div>

      <p className="text-[10px] text-kaihara-muted text-center">
        Refresh setiap 10 saat • TS = Tailscale presence
      </p>
    </div>
  )
}

function ServerRow({ s, compact }: { s: MonServer; compact?: boolean }) {
  const up = s.status === 'UP'
  return (
    <div className={`flex items-center justify-between ${compact ? 'py-0.5' : 'py-1'} px-2 rounded ${up ? 'bg-kaihara-success/5' : 'bg-kaihara-danger/10'}`}>
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${up ? 'bg-kaihara-success animate-pulse' : 'bg-kaihara-danger'}`} />
        <div className="min-w-0">
          <span className={`text-xs truncate block ${up ? '' : 'text-kaihara-danger line-through'}`}>
            {s.name}
          </span>
          {!compact && <span className="text-[10px] text-kaihara-muted">{s.role}</span>}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0 text-[10px]">
        {s.tailscale_online !== null && (
          <span className={s.tailscale_online ? 'text-kaihara-accent' : 'text-kaihara-muted'}>
            TS{s.tailscale_online ? '✓' : '✗'}
          </span>
        )}
        {s.latency_ms != null && (
          <span className="text-kaihara-muted">{s.latency_ms}ms</span>
        )}
        <span className={`font-mono font-bold px-1.5 py-0.5 rounded ${up ? 'bg-kaihara-success/15 text-kaihara-success' : 'bg-kaihara-danger/20 text-kaihara-danger'}`}>
          {s.status}
        </span>
      </div>
    </div>
  )
}
