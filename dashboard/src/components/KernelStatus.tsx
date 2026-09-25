import { useState, useEffect, useCallback } from 'react'
import {
  getKernelStatus,
  startAllKernel,
  stopAllKernel,
  runKernelOnce,
  type OSAgentStatus,
} from '../lib/api'

const agentIcons: Record<string, string> = {
  os_file: 'F', os_process: 'P', os_network: 'N',
  os_backup: 'B', os_update: 'U', os_health: 'H', os_cost: '$',
}

const agentLabels: Record<string, string> = {
  os_file: 'File', os_process: 'Process', os_network: 'Network',
  os_backup: 'Backup', os_update: 'Update', os_health: 'Health',
  os_cost: 'Cost',
}

export default function KernelStatus() {
  const [agents, setAgents] = useState<Record<string, OSAgentStatus>>({})

  const fetchStatus = useCallback(async () => {
    try { setAgents(await getKernelStatus()) } catch {}
  }, [])

  useEffect(() => {
    fetchStatus()
    const i = setInterval(fetchStatus, 15000)
    return () => clearInterval(i)
  }, [fetchStatus])

  const entries = Object.entries(agents)
  const runningCount = entries.filter(([, a]) => a.running).length

  return (
    <div className="hud-panel">
      <div className="flex items-center justify-between mb-2">
        <div className="hud-title mb-0">OS Kernel</div>
        <div className="flex gap-1">
          <button onClick={() => startAllKernel()}
            className="text-xs px-2 py-0.5 rounded bg-kaihara-success text-white hover:opacity-80">
            Start
          </button>
          <button onClick={() => stopAllKernel()}
            className="text-xs px-2 py-0.5 rounded bg-kaihara-danger text-white hover:opacity-80">
            Stop
          </button>
        </div>
      </div>

      {entries.length === 0 ? (
        <p className="text-xs text-kaihara-muted">No kernel agents.</p>
      ) : (
        <>
          <div className="text-xs text-kaihara-muted mb-2">
            {runningCount}/{entries.length} running
          </div>
          <div className="space-y-1.5">
            {entries.map(([name, agent]) => (
              <div key={name} className="flex items-center justify-between text-xs group">
                <span className="flex items-center gap-2">
                  <span className="font-mono w-5 text-center text-kaihara-accent font-bold">
                    {agentIcons[name] || '?'}
                  </span>
                  <span>{agentLabels[name] || name}</span>
                </span>
                <span className="flex items-center gap-2">
                  {agent.running ? (
                    <span className="status-dot bg-kaihara-success animate-pulse" />
                  ) : (
                    <span className="status-dot bg-kaihara-muted" />
                  )}
                  <button
                    onClick={() => runKernelOnce(name)}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-kaihara-border hover:bg-kaihara-accent hover:text-white transition-colors"
                    title="Run once"
                  >
                    Run
                  </button>
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
