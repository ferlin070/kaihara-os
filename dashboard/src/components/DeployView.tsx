import { useState, useEffect, useCallback } from 'react'
import {
  getDeployStatus, getDockerPs, dockerCompose, getDockerLogs,
  getGitStatus, gitPullDeploy, gitDeploy, gitRollback,
  getLxcList, lxcManage, getDeployHealth, deployRollback,
  getDeployHistory, type DeployStatus, type DockerContainer, type DeployHistoryEntry,
} from '../lib/api'

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`w-1.5 h-1.5 rounded-full inline-block ${ok ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
}

function Badge({ text, color = 'bg-kaihara-accent/20 text-kaihara-accent' }: { text: string; color?: string }) {
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${color}`}>{text}</span>
}

export default function DeployView() {
  const [status, setStatus] = useState<DeployStatus | null>(null)
  const [containers, setContainers] = useState<DockerContainer[]>([])
  const [lxc, setLxc] = useState<any[]>([])
  const [gitInfo, setGitInfo] = useState<any>(null)
  const [history, setHistory] = useState<DeployHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLog, setActionLog] = useState<string[]>([])
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null)
  const [containerLogs, setContainerLogs] = useState<string>('')

  const addLog = (msg: string) => setActionLog(prev => [`${new Date().toLocaleTimeString()} ${msg}`, ...prev.slice(0, 19)])

  const refresh = useCallback(async () => {
    try {
      const [s, d, g, l, h] = await Promise.all([
        getDeployStatus(),
        getDockerPs(true).catch(() => ({ containers: [], count: 0 })),
        getGitStatus().catch(() => null),
        getLxcList().catch(() => ({ containers: [] })),
        getDeployHistory().catch(() => ({ history: [] })),
      ])
      setStatus(s)
      setContainers(d.containers)
      setGitInfo(g)
      setLxc(l.containers)
      setHistory(h.history)
    } catch (e) { addLog(`Error: ${e}`) }
    setLoading(false)
  }, [])

  useEffect(() => { refresh(); const i = setInterval(refresh, 15000); return () => clearInterval(i) }, [refresh])

  const handleDockerAction = async (action: string, service?: string) => {
    addLog(`docker compose ${action}${service ? ` ${service}` : ''}...`)
    const r = await dockerCompose(action, service)
    addLog(r.ok ? `✓ ${action} done` : `✗ ${action} failed: ${r.stderr || r.error}`)
    refresh()
  }

  const handleGitDeploy = async () => {
    addLog('Starting git deploy...')
    const r = await gitDeploy()
    addLog(r.ok ? '✓ Deploy complete' : '✗ Deploy failed')
    refresh()
  }

  const handleGitRollback = async () => {
    if (!confirm('Rollback 1 commit?')) return
    addLog('Rolling back...')
    const r = await gitRollback(1)
    addLog(r.ok ? `✓ Rolled back to ${r.to}` : '✗ Rollback failed')
    refresh()
  }

  const handleLxcAction = async (vmid: string, action: string) => {
    addLog(`LXC ${action} ${vmid}...`)
    const r = await lxcManage(vmid, action)
    addLog(r.ok ? `✓ LXC ${action} done` : `✗ LXC ${action} failed`)
    refresh()
  }

  const handleViewLogs = async (container: string) => {
    setSelectedContainer(container)
    const r = await getDockerLogs(container, 100)
    setContainerLogs(r.logs || r.error || 'No logs')
  }

  if (loading) return <div className="hud-panel"><div className="text-xs text-kaihara-muted animate-pulse">Loading deploy...</div></div>

  return (
    <div className="flex flex-col gap-4 p-4 max-w-7xl mx-auto">
      <h2 className="text-sm font-bold text-kaihara-text flex items-center gap-2">
        <span className="text-kaihara-accent">🚀</span> Deploy Agent
      </h2>

      {/* Health + Disk + Git */}
      <div className="grid grid-cols-3 gap-3">
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-2">HEALTH</h4>
          {status?.health?.checks?.map((c: any, i: number) => (
            <div key={i} className="flex items-center justify-between text-xs mb-0.5">
              <span className="text-kaihara-muted">{c.check}</span>
              <StatusDot ok={c.ok} />
            </div>
          ))}
        </div>
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-2">DISK</h4>
          <div className="text-xs text-kaihara-text">{status?.disk?.used_gb}/{status?.disk?.total_gb} GB</div>
          <div className="w-full h-1.5 bg-kaihara-border rounded-full mt-1">
            <div className={`h-full rounded-full ${(status?.disk?.percent || 0) > 90 ? 'bg-kaihara-danger' : 'bg-kaihara-accent'}`}
              style={{ width: `${status?.disk?.percent || 0}%` }} />
          </div>
          <div className="text-[10px] text-kaihara-muted mt-0.5">{status?.disk?.percent}% used</div>
        </div>
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-2">GIT</h4>
          <div className="text-xs text-kaihara-text">Branch: {gitInfo?.branch || '-'}</div>
          <div className="text-[10px] text-kaihara-muted">{gitInfo?.modified_files || 0} modified files</div>
          <div className="flex gap-2 mt-2">
            <button onClick={handleGitDeploy} className="kaihara-btn text-[10px] px-2 py-1">Deploy</button>
            <button onClick={handleGitRollback} className="kaihara-btn text-[10px] px-2 py-1 text-kaihara-warning">Rollback</button>
          </div>
        </div>
      </div>

      {/* Docker Containers */}
      <div className="hud-panel">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-[10px] text-kaihara-muted">DOCKER CONTAINERS ({containers.length})</h4>
          <div className="flex gap-1">
            <button onClick={() => handleDockerAction('ps')} className="kaihara-btn text-[10px] px-2 py-0.5">Refresh</button>
            <button onClick={() => handleDockerAction('restart')} className="kaihara-btn text-[10px] px-2 py-0.5">Restart All</button>
            <button onClick={() => handleDockerAction('down')} className="kaihara-btn text-[10px] px-2 py-0.5 text-kaihara-danger">Stop All</button>
          </div>
        </div>
        {containers.length === 0 ? (
          <div className="text-[10px] text-kaihara-muted">No containers found</div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            {containers.map((c) => (
              <div key={c.ID} className="bg-kaihara-bg/50 border border-kaihara-border rounded p-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-kaihara-text font-mono truncate">{c.Names}</span>
                  <StatusDot ok={c.State === 'running'} />
                </div>
                <div className="text-[10px] text-kaihara-muted mt-0.5">{c.Image}</div>
                <div className="text-[10px] text-kaihara-muted">{c.Status}</div>
                <div className="flex gap-1 mt-1">
                  <button onClick={() => handleDockerAction('restart', c.Names)}
                    className="text-[9px] px-1 py-0.5 bg-kaihara-accent/10 text-kaihara-accent rounded hover:bg-kaihara-accent/20">restart</button>
                  <button onClick={() => handleViewLogs(c.Names)}
                    className="text-[9px] px-1 py-0.5 bg-kaihara-border text-kaihara-muted rounded hover:bg-kaihara-accent/20">logs</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Container Logs */}
      {selectedContainer && (
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[10px] text-kaihara-muted">LOGS: {selectedContainer}</h4>
            <button onClick={() => setSelectedContainer(null)} className="text-[10px] text-kaihara-muted hover:text-kaihara-text">✕</button>
          </div>
          <pre className="text-[10px] text-kaihara-text bg-black/30 rounded p-2 max-h-48 overflow-auto font-mono whitespace-pre-wrap">{containerLogs}</pre>
        </div>
      )}

      {/* Proxmox LXC */}
      <div className="hud-panel">
        <h4 className="text-[10px] text-kaihara-muted mb-2">PROXMOX LXC ({lxc.length})</h4>
        {lxc.length === 0 ? (
          <div className="text-[10px] text-kaihara-muted">No LXC containers</div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {lxc.map((c: any) => (
              <div key={c.vmid} className="bg-kaihara-bg/50 border border-kaihara-border rounded p-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-kaihara-text">CT {c.vmid}</span>
                  <Badge text={c.status} color={c.status === 'running' ? 'bg-kaihara-success/20 text-kaihara-success' : 'bg-kaihara-danger/20 text-kaihara-danger'} />
                </div>
                <div className="text-[10px] text-kaihara-muted">{c.name}</div>
                <div className="flex gap-1 mt-1">
                  {c.status !== 'running' && (
                    <button onClick={() => handleLxcAction(c.vmid, 'start')}
                      className="text-[9px] px-1 py-0.5 bg-kaihara-success/10 text-kaihara-success rounded">start</button>
                  )}
                  {c.status === 'running' && (
                    <button onClick={() => handleLxcAction(c.vmid, 'stop')}
                      className="text-[9px] px-1 py-0.5 bg-kaihara-danger/10 text-kaihara-danger rounded">stop</button>
                  )}
                  <button onClick={() => handleLxcAction(c.vmid, 'restart')}
                    className="text-[9px] px-1 py-0.5 bg-kaihara-accent/10 text-kaihara-accent rounded">restart</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Deploy History */}
      <div className="hud-panel">
        <h4 className="text-[10px] text-kaihara-muted mb-2">DEPLOY HISTORY</h4>
        {history.length === 0 ? (
          <div className="text-[10px] text-kaihara-muted">No history yet</div>
        ) : (
          <div className="space-y-0.5 max-h-32 overflow-auto">
            {history.map((h, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <StatusDot ok={h.ok} />
                <span className="text-kaihara-muted">{h.timestamp.split('T')[1]?.split('.')[0]}</span>
                <span className="text-kaihara-text">{h.action}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action Log */}
      {actionLog.length > 0 && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-2">ACTION LOG</h4>
          <div className="space-y-0.5 max-h-32 overflow-auto">
            {actionLog.map((l, i) => (
              <div key={i} className="text-[10px] text-kaihara-text font-mono">{l}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
