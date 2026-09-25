import { useState, useEffect, useCallback } from 'react'
import ServerMonitor from './ServerMonitor'
import {
  getDaemonStatus, getDaemonAlerts,
  startDaemonWatchdog, stopDaemonWatchdog,
  restartDaemonAgent, restartAllDaemonAgents,
  type DaemonStatus, type DaemonAlert, type ServiceInfo,
} from '../lib/api'

function formatUptime(seconds: number): string {
  if (!seconds) return '--'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function getStatusColor(running: boolean, error: string | null): string {
  if (error) return 'text-kaihara-danger'
  if (running) return 'text-kaihara-success'
  return 'text-kaihara-muted'
}

function getStatusDot(running: boolean, error: string | null): string {
  if (error) return 'bg-kaihara-danger'
  if (running) return 'bg-kaihara-success'
  return 'bg-kaihara-muted'
}

const agentLabels: Record<string, string> = {
  health: 'System Health',
  process: 'Process Monitor',
  network: 'Network Watch',
  file: 'File Manager',
  backup: 'Backup Agent',
  cost: 'Cost Tracker',
  update: 'Update Checker',
}

const agentIcons: Record<string, string> = {
  health: '💓',
  process: '⚙️',
  network: '🌐',
  file: '📁',
  backup: '💾',
  cost: '💰',
  update: '🔄',
}

export default function DaemonView() {
  const [status, setStatus] = useState<DaemonStatus | null>(null)
  const [alerts, setAlerts] = useState<DaemonAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, alertsRes] = await Promise.all([
        getDaemonStatus(),
        getDaemonAlerts(),
      ])
      setStatus(statusRes)
      setAlerts(alertsRes.alerts || [])
    } catch {
      setStatus(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [fetchData])

  const handleWatchdog = async (start: boolean) => {
    setActionLoading('watchdog')
    try {
      start ? await startDaemonWatchdog() : await stopDaemonWatchdog()
      await fetchData()
    } catch {}
    setActionLoading(null)
  }

  const handleRestart = async (name: string) => {
    setActionLoading(name)
    try {
      await restartDaemonAgent(name)
      await fetchData()
    } catch {}
    setActionLoading(null)
  }

  const handleRestartAll = async () => {
    setActionLoading('all')
    try {
      await restartAllDaemonAgents()
      await fetchData()
    } catch {}
    setActionLoading(null)
  }

  if (!loading && !status) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-kaihara-muted text-sm">Daemon manager not available.</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">

      <ServerMonitor />
      {/* Top Row: Process + Agent Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Process Info */}
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-kaihara-muted uppercase">Process</h3>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${status?.watchdog_running ? 'bg-kaihara-success' : 'bg-kaihara-muted'}`} />
              <span className="text-xs text-kaihara-muted">
                Watchdog: {status?.watchdog_running ? 'ON' : 'OFF'}
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">PID</span>
              <span className="text-kaihara-text font-mono">{status?.process.pid || '--'}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">CPU</span>
              <span className="text-kaihara-text font-mono">{status?.process.cpu_percent?.toFixed(1) || '--'}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Memory</span>
              <span className="text-kaihara-text font-mono">{status?.process.memory_mb || '--'} MB</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Threads</span>
              <span className="text-kaihara-text font-mono">{status?.process.threads || '--'}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Uptime</span>
              <span className="text-kaihara-text font-mono">{formatUptime(status?.process?.uptime_seconds ?? 0)}</span>
            </div>
          </div>
        </div>

        {/* Agent Summary */}
        <div className="hud-panel">
          <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-3">Agent Fleet</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Total</span>
              <span className="text-kaihara-text font-mono">{status?.agents.total}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Running</span>
              <span className="text-kaihara-success font-mono">{status?.agents.running}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Errored</span>
              <span className="text-kaihara-danger font-mono">{status?.agents.errored}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">Stopped</span>
              <span className="text-kaihara-muted font-mono">{status?.agents.stopped}</span>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => handleWatchdog(!status?.watchdog_running)}
              disabled={actionLoading === 'watchdog'}
              className="flex-1 px-2 py-1.5 text-xs bg-kaihara-border text-kaihara-text rounded hover:bg-kaihara-border/80 disabled:opacity-50"
            >
              {status?.watchdog_running ? 'Stop Watchdog' : 'Start Watchdog'}
            </button>
            <button
              onClick={handleRestartAll}
              disabled={actionLoading === 'all'}
              className="flex-1 px-2 py-1.5 text-xs bg-kaihara-accent/20 text-kaihara-accent rounded hover:bg-kaihara-accent/30 disabled:opacity-50"
            >
              Restart All
            </button>
          </div>
        </div>

        {/* Alerts */}
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-kaihara-muted uppercase">Alerts</h3>
            <span className={`text-xs ${(alerts || []).length > 0 ? 'text-kaihara-danger' : 'text-kaihara-success'}`}>
              {(alerts || []).length} active
            </span>
          </div>
          <div className="space-y-1.5 max-h-32 overflow-y-auto">
            {(alerts || []).length === 0 ? (
              <p className="text-xs text-kaihara-muted">No active alerts.</p>
            ) : (
              (alerts || []).map((alert, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={alert.severity === 'critical' ? 'text-kaihara-danger' : 'text-kaihara-warning'}>!</span>
                  <div>
                    <span className="text-kaihara-text">{alert.agent}</span>
                    <span className="text-kaihara-muted ml-1">— {alert.message.slice(0, 60)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-3">Services</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {(status?.services || []).map((service: any) => (
            <ServiceCard
              key={service.name}
              service={service}
              restarting={actionLoading === service.name}
              onRestart={() => handleRestart(service.name)}
            />
          ))}
        </div>
      </div>

      {/* Restart History */}
      {(status?.restart_history || []).length > 0 && (
        <div className="hud-panel">
          <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-3">Restart History</h3>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {(status?.restart_history || []).slice().reverse().slice(0, 10).map((entry, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="text-kaihara-muted font-mono">{entry.time?.slice(11, 19)}</span>
                <span className="text-kaihara-accent">{entry.agent}</span>
                <span className={entry.action === 'restart' ? 'text-kaihara-warning' : 'text-kaihara-muted'}>
                  {entry.action}
                </span>
                {entry.error && <span className="text-kaihara-danger truncate max-w-48">{entry.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ServiceCard({ service, restarting, onRestart }: {
  service: ServiceInfo
  restarting: boolean
  onRestart: () => void
}) {
  const [showDetail, setShowDetail] = useState(false)

  return (
    <div className="bg-kaihara-bg border border-kaihara-border rounded p-3 hover:border-kaihara-accent/50 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${getStatusDot(service.running, service.error)}`} />
          <span className="text-sm font-medium">{agentIcons[service.name] || '🔧'} {agentLabels[service.name] || service.name}</span>
        </div>
        <button
          onClick={() => setShowDetail(!showDetail)}
          className="text-xs text-kaihara-muted hover:text-kaihara-text"
        >
          {showDetail ? '▾' : '▸'}
        </button>
      </div>

      <div className="flex justify-between text-xs mb-1">
        <span className="text-kaihara-muted">Status</span>
        <span className={getStatusColor(service.running, service.error)}>
          {service.error ? 'ERROR' : service.running ? 'RUNNING' : 'STOPPED'}
        </span>
      </div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-kaihara-muted">Interval</span>
        <span className="text-kaihara-text font-mono">{service.interval}s</span>
      </div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-kaihara-muted">Runs</span>
        <span className="text-kaihara-text font-mono">{service.run_count}</span>
      </div>
      {service.restarts > 0 && (
        <div className="flex justify-between text-xs mb-1">
          <span className="text-kaihara-muted">Restarts</span>
          <span className="text-kaihara-warning font-mono">{service.restarts}</span>
        </div>
      )}

      {showDetail && (
        <div className="mt-2 pt-2 border-t border-kaihara-border space-y-1">
          <div className="text-xs">
            <span className="text-kaihara-muted">Last Run: </span>
            <span className="text-kaihara-text font-mono">{service.last_run?.slice(11, 19) || 'never'}</span>
          </div>
          {service.error && (
            <div className="text-xs text-kaihara-danger break-words">{service.error.slice(0, 100)}</div>
          )}
        </div>
      )}

      <div className="flex gap-2 mt-2 pt-2 border-t border-kaihara-border">
        <button
          onClick={onRestart}
          disabled={restarting}
          className="flex-1 px-2 py-1 text-xs bg-kaihara-accent/20 text-kaihara-accent rounded hover:bg-kaihara-accent/30 disabled:opacity-50"
        >
          {restarting ? 'Restarting...' : 'Restart'}
        </button>
      </div>
    </div>
  )
}
