import { useState, useEffect, useCallback } from 'react'
import { getSystemStats, type SystemStats } from '../lib/api'

function formatUptime(sec: number): string {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function Bar({ value, max = 100, color = 'kaihara-accent' }: { value: number; max?: number; color?: string }) {
  const pct = Math.min((value / max) * 100, 100)
  const barColor = pct > 90 ? 'bg-kaihara-danger' : pct > 70 ? 'bg-kaihara-warning' : `bg-${color}`
  return (
    <div className="w-full h-1.5 bg-kaihara-border rounded-full overflow-hidden">
      <div className={`h-full ${barColor} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function CoreBars({ cores }: { cores: number[] }) {
  return (
    <div className="grid grid-cols-4 gap-x-2 gap-y-0.5">
      {cores.slice(0, 16).map((c, i) => (
        <div key={i} className="flex items-center gap-1">
          <span className="text-[10px] text-kaihara-muted w-4">C{i}</span>
          <div className="flex-1 h-1 bg-kaihara-border rounded-full overflow-hidden">
            <div className={`h-full ${c > 90 ? 'bg-kaihara-danger' : c > 70 ? 'bg-kaihara-warning' : 'bg-kaihara-accent'} transition-all`}
              style={{ width: `${Math.min(c, 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function SystemStatsWidget() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const data = await getSystemStats()
      setStats(data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000) // Refresh every 3s
    return () => clearInterval(interval)
  }, [fetchStats])

  if (loading || !stats) {
    return (
      <div className="hud-panel">
        <div className="text-xs text-kaihara-muted animate-pulse">Loading system stats...</div>
      </div>
    )
  }

  return (
    <div className="hud-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-kaihara-muted uppercase">System Monitor</h3>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-kaihara-success animate-pulse" />
          <span className="text-[10px] text-kaihara-muted">LIVE</span>
        </div>
      </div>

      {/* CPU */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">CPU</span>
          <span className="font-mono text-kaihara-text">{stats.cpu.percent}%</span>
        </div>
        <Bar value={stats.cpu.percent} color="kaihara-accent" />
        <div className="flex justify-between text-[10px] text-kaihara-muted mt-0.5">
          <span>{stats.cpu.count_logical} cores</span>
          <span>Load: {stats.cpu.load_1m}</span>
        </div>
        {stats.cpu.per_core.length > 0 && (
          <div className="mt-1">
            <CoreBars cores={stats.cpu.per_core} />
          </div>
        )}
      </div>

      {/* RAM */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">RAM</span>
          <span className="font-mono text-kaihara-text">{stats.memory.ram_used_gb}/{stats.memory.ram_total_gb} GB ({stats.memory.ram_percent}%)</span>
        </div>
        <Bar value={stats.memory.ram_percent} color="kaihara-success" />
        {stats.memory.swap_total_gb > 0 && (
          <div className="flex justify-between text-[10px] text-kaihara-muted mt-0.5">
            <span>Swap: {stats.memory.swap_used_gb}/{stats.memory.swap_total_gb} GB</span>
            <span>{stats.memory.swap_percent}%</span>
          </div>
        )}
      </div>

      {/* Disk */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">Disk</span>
          <span className="font-mono text-kaihara-text">{stats.disk.used_gb}/{stats.disk.total_gb} GB ({stats.disk.percent}%)</span>
        </div>
        <Bar value={stats.disk.percent} color="kaihara-warning" />
        {stats.disk.io && (
          <div className="flex justify-between text-[10px] text-kaihara-muted mt-0.5">
            <span>Read: {(stats.disk.io.read_mb / 1024).toFixed(1)} GB</span>
            <span>Write: {(stats.disk.io.write_mb / 1024).toFixed(1)} GB</span>
          </div>
        )}
      </div>

      {/* Network */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">Network</span>
          <span className="font-mono text-kaihara-text">{stats.network.established} conn</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div>
            <span className="text-kaihara-muted">↑ Sent: </span>
            <span className="text-kaihara-text">{stats.network.total_sent_mb} MB</span>
          </div>
          <div>
            <span className="text-kaihara-muted">↓ Recv: </span>
            <span className="text-kaihara-text">{stats.network.total_recv_mb} MB</span>
          </div>
          <div>
            <span className="text-kaihara-muted">↑ Pkts: </span>
            <span className="text-kaihara-text">{stats.network.total_packets_sent}</span>
          </div>
          <div>
            <span className="text-kaihara-muted">↓ Pkts: </span>
            <span className="text-kaihara-text">{stats.network.total_packets_recv}</span>
          </div>
        </div>
        {(stats.network.errin > 0 || stats.network.errout > 0) && (
          <div className="text-[10px] text-kaihara-danger mt-0.5">
            Errors: in={stats.network.errin} out={stats.network.errout}
          </div>
        )}
        {stats.network.interfaces.length > 0 && (
          <div className="mt-1 space-y-0.5">
            {stats.network.interfaces.slice(0, 3).map((nic: any, i: number) => (
              <div key={i} className="flex justify-between text-[10px] text-kaihara-muted">
                <span>{nic.name}</span>
                <span>↑{nic.sent_mb}MB ↓{nic.recv_mb}MB</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Processes */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">Processes</span>
          <span className="font-mono text-kaihara-text">{stats.processes.total}</span>
        </div>
        {stats.processes.top_cpu.length > 0 && (
          <div className="space-y-0.5">
            {stats.processes.top_cpu.slice(0, 3).map((p: any, i: number) => (
              <div key={i} className="flex justify-between text-[10px]">
                <span className="text-kaihara-text truncate max-w-24">{p.name}</span>
                <span className="text-kaihara-warning font-mono">{p.cpu}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex justify-between text-[10px] text-kaihara-muted border-t border-kaihara-border pt-2">
        <span>{stats.system.platform} • {stats.system.hostname}</span>
        <span>Up: {formatUptime(stats.system.uptime_seconds)}</span>
      </div>
      {stats.temperature && (
        <div className="text-[10px] text-kaihara-muted">
          Temp: {stats.temperature}°C
        </div>
      )}
    </div>
  )
}
