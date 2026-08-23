import { useState, useEffect, useCallback } from 'react'
import {
  getSecurityStatus,
  getApprovals,
  approveAction,
  createDemoApproval,
  denyAction,
  getAuditLog,
  runPentest,
  getPentestSessions,
  getSecurityAgentStatus,
  runSecurityAgent,
  securityDnsLookup,
  securityPortScan,
  securityVulnScan,
  securityFullRecon,
  type SecurityStatus,
  type Approval,
  type AuditEntry,
  type SecurityAgentStatus,
} from '../lib/api'

type Tab = 'overview' | 'agent' | 'approvals' | 'audit' | 'pentest'

export default function SecurityView() {
  const [tab, setTab] = useState<Tab>('overview')
  const [status, setStatus] = useState<SecurityStatus | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setStatus(await getSecurityStatus())
    } catch {}
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Tab Navigation */}
      <div className="flex-shrink-0 flex border-b border-kaihara-border">
        {(['overview', 'agent', 'approvals', 'audit', 'pentest'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-medium uppercase tracking-wide transition-colors ${
              tab === t
                ? 'text-kaihara-accent border-b-2 border-kaihara-accent'
                : 'text-kaihara-muted hover:text-kaihara-text'
            }`}
          >
            {t === 'agent' ? '🛡️ Agent' : t}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === 'overview' && <Overview status={status} />}
        {tab === 'agent' && <SecurityAgentTab />}
        {tab === 'approvals' && <Approvals />}
        {tab === 'audit' && <AuditLog />}
        {tab === 'pentest' && <Pentest />}
      </div>
    </div>
  )
}

// ============================================================
// Overview Tab — Clean status cards
// ============================================================

function Overview({ status }: { status: SecurityStatus | null }) {
  if (!status) {
    return <div className="p-6 text-kaihara-muted text-sm">Loading security status...</div>
  }

  return (
    <div className="p-4 space-y-4">
      {/* Status Summary Bar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-kaihara-border/30 rounded-lg">
        <StatusDot active={!!status.approval_gate} />
        <span className="text-xs">Approval Gate</span>
        <StatusDot active={!!status.sandbox?.available} />
        <span className="text-xs">Sandbox</span>
        <StatusDot active={!!status.audit?.exists} />
        <span className="text-xs">Audit Trail</span>
        <StatusDot active={!!status.pentest} />
        <span className="text-xs">Pentest</span>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Approval Gate Card */}
        <StatusCard
          icon="🔒"
          title="Approval Gate"
          color="warning"
          items={[
            { label: 'Pending', value: status.approval_gate?.pending_count ?? 0, highlight: (status.approval_gate?.pending_count ?? 0) > 0 },
            { label: 'Approved', value: status.approval_gate?.history_count ?? 0 },
            { label: 'Required Actions', value: status.approval_gate?.requires_approval?.length ?? 0, subtext: 'actions need approval' },
          ]}
        />

        {/* Sandbox Card */}
        <StatusCard
          icon="📦"
          title="Sandbox"
          color="accent"
          items={[
            { label: 'Status', value: status.sandbox?.available ? 'Ready' : 'Unavailable', ok: status.sandbox?.available },
            { label: 'Image', value: status.sandbox?.image || 'N/A', mono: true },
            { label: 'Memory', value: status.sandbox?.memory || 'N/A' },
            { label: 'CPU', value: status.sandbox?.cpu || 'N/A' },
          ]}
        />

        {/* Audit Trail Card */}
        <StatusCard
          icon="📋"
          title="Audit Trail"
          color="success"
          items={[
            { label: 'Status', value: status.audit?.exists ? 'Active' : 'Inactive', ok: status.audit?.exists },
            { label: 'Total Entries', value: status.audit?.total ?? 0 },
            { label: 'Log Size', value: formatBytes(status.audit?.size_bytes ?? 0) },
            { label: 'Path', value: status.audit?.log_path || 'N/A', mono: true, truncate: true },
          ]}
        />

        {/* Pentest Card */}
        <StatusCard
          icon="🎯"
          title="Pentest Pipeline"
          color="danger"
          items={[
            { label: 'Status', value: status.pentest ? 'Ready' : 'Unavailable', ok: !!status.pentest },
            { label: 'Phases', value: status.pentest?.phases?.length ?? 0, subtext: status.pentest?.phases?.join(', ') },
            { label: 'Sessions', value: status.pentest?.sessions ?? 0 },
            { label: 'Components', value: [
              status.pentest?.recon && 'Recon',
              status.pentest?.scanner && 'Scanner',
              status.pentest?.exploit && 'Exploit',
              status.pentest?.sandbox && 'Sandbox',
            ].filter(Boolean).join(', ') || 'None' },
          ]}
        />
      </div>

      {/* Audit Distribution (if data exists) */}
      {status.audit?.by_agent && Object.keys(status.audit.by_agent).length > 0 && (
        <div className="px-4 py-3 bg-kaihara-border/20 rounded-lg">
          <h4 className="text-xs font-bold text-kaihara-muted mb-2">Activity by Agent</h4>
          <div className="flex flex-wrap gap-3">
            {Object.entries(status.audit.by_agent).map(([agent, count]) => (
              <div key={agent} className="flex items-center gap-2">
                <span className="text-xs text-kaihara-accent">{agent}</span>
                <span className="text-xs font-mono">{String(count)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================
// Shared Components
// ============================================================

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className={`w-2 h-2 rounded-full ${active ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
  )
}

function StatusCard({ icon, title, color, items }: {
  icon: string
  title: string
  color: 'success' | 'warning' | 'danger' | 'accent'
  items: { label: string; value: any; ok?: boolean; highlight?: boolean; mono?: boolean; truncate?: boolean; subtext?: string }[]
}) {
  const colorMap = {
    success: 'text-kaihara-success',
    warning: 'text-kaihara-warning',
    danger: 'text-kaihara-danger',
    accent: 'text-kaihara-accent',
  }

  return (
    <div className="hud-panel">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-kaihara-border/50">
        <span className="text-lg">{icon}</span>
        <h3 className={`text-sm font-bold ${colorMap[color]}`}>{title}</h3>
      </div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className="text-kaihara-muted">{item.label}</span>
            <div className="text-right">
              <span className={
                item.ok !== undefined ? (item.ok ? 'text-kaihara-success' : 'text-kaihara-danger') :
                item.highlight ? 'text-kaihara-warning font-bold' :
                'text-kaihara-text'
              }>
                {typeof item.value === 'object' ? JSON.stringify(item.value) : String(item.value)}
              </span>
              {item.subtext && (
                <span className="text-kaihara-muted ml-1 text-[10px]">{item.subtext}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================
// Security Agent Tab — Real tool capabilities
// ============================================================

function SecurityAgentTab() {
  const [agentStatus, setAgentStatus] = useState<SecurityAgentStatus | null>(null)
  const [target, setTarget] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [taskInput, setTaskInput] = useState('')

  useEffect(() => {
    getSecurityAgentStatus().then(setAgentStatus).catch(() => {})
  }, [])

  const runTool = async (toolFn: (t: string) => Promise<any>) => {
    if (!target.trim() || running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await toolFn(target.trim())
      setResult(res)
    } catch (e) {
      setResult({ error: String(e) })
    }
    setRunning(false)
  }

  const handleRunTask = async () => {
    if (!taskInput.trim() || running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await runSecurityAgent(taskInput.trim())
      setResult(res)
    } catch (e) {
      setResult({ error: String(e) })
    }
    setRunning(false)
  }

  return (
    <div className="p-4 space-y-4">
      {/* Agent Status Bar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-kaihara-border/30 rounded-lg">
        <StatusDot active={agentStatus !== null} />
        <span className="text-xs font-bold">Security Agent</span>
        <span className="text-xs text-kaihara-muted">
          {agentStatus?.tools?.length ?? 0} tools
        </span>
        <StatusDot active={!!agentStatus?.sandbox_available} />
        <span className="text-xs">Sandbox</span>
        <StatusDot active={!!agentStatus?.audit_enabled} />
        <span className="text-xs">Audit</span>
        <StatusDot active={!!agentStatus?.approval_gate_enabled} />
        <span className="text-xs">Approval</span>
      </div>

      {/* Target Input */}
      <div className="hud-panel">
        <label className="text-xs text-kaihara-muted mb-2 block">TARGET</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="example.com or 192.168.1.1"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-sm focus:outline-none focus:border-kaihara-accent font-mono"
            disabled={running}
          />
        </div>
      </div>

      {/* Quick Tools Grid */}
      <div className="grid grid-cols-2 gap-3">
        <ToolButton
          icon="🔍"
          label="DNS Lookup"
          description="Resolve domain to IP"
          onClick={() => runTool(securityDnsLookup)}
          disabled={!target.trim() || running}
        />
        <ToolButton
          icon="🔌"
          label="Port Scan"
          description="Scan open ports"
          onClick={() => runTool(securityPortScan)}
          disabled={!target.trim() || running}
        />
        <ToolButton
          icon="🛡️"
          label="Vuln Scan"
          description="Check vulnerabilities"
          onClick={() => runTool(securityVulnScan)}
          disabled={!target.trim() || running}
        />
        <ToolButton
          icon="🎯"
          label="Full Recon"
          description="Complete reconnaissance"
          onClick={() => runTool(securityFullRecon)}
          disabled={!target.trim() || running}
        />
      </div>

      {/* Natural Language Task */}
      <div className="hud-panel">
        <label className="text-xs text-kaihara-muted mb-2 block">NATURAL LANGUAGE COMMAND</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRunTask()}
            placeholder='e.g., "scan port 80 on example.com"'
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={running}
          />
          <button
            onClick={handleRunTask}
            disabled={!taskInput.trim() || running}
            className="px-4 py-2 bg-kaihara-accent text-white text-sm rounded hover:bg-kaihara-accent/80 disabled:opacity-50 font-medium"
          >
            {running ? '...' : 'Run'}
          </button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-kaihara-muted">RESULT</h4>
            <StatusBadge status={result.status || (result.success ? 'ok' : 'error')} />
          </div>
          <pre className="text-xs text-kaihara-text overflow-x-auto max-h-48 overflow-y-auto bg-kaihara-bg p-3 rounded border border-kaihara-border font-mono">
            {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

function ToolButton({ icon, label, description, onClick, disabled }: {
  icon: string; label: string; description: string; onClick: () => void; disabled: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="hud-panel text-left hover:border-kaihara-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="text-xs text-kaihara-muted">{description}</p>
    </button>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ok: 'bg-kaihara-success/20 text-kaihara-success',
    error: 'bg-kaihara-danger/20 text-kaihara-danger',
    pending_approval: 'bg-kaihara-warning/20 text-kaihara-warning',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${colors[status] || 'bg-kaihara-border text-kaihara-muted'}`}>
      {status}
    </span>
  )
}

// ============================================================
// Approvals Tab
// ============================================================

function Approvals() {
  const [pending, setPending] = useState<Approval[]>([])
  const [history, setHistory] = useState<Approval[]>([])

  const fetch = useCallback(async () => {
    try {
      const res = await getApprovals()
      setPending(res.pending || [])
      setHistory(res.history || [])
    } catch {}
  }, [])

  useEffect(() => { fetch(); const i = setInterval(fetch, 5000); return () => clearInterval(i) }, [fetch])

  const [creatingDemo, setCreatingDemo] = useState(false)
  const handleApprove = async (id: string) => { await approveAction(id); fetch() }
  const handleCreateDemo = async () => {
    setCreatingDemo(true)
    try { await createDemoApproval(); fetch() } catch {}
    setCreatingDemo(false)
  }
  const handleDeny = async (id: string) => { await denyAction(id, 'Denied by user'); fetch() }

  return (
    <div className="p-4 space-y-4">
      {/* Pending Approvals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold">Pending Approvals</h3>
          <span className="text-xs px-2 py-0.5 bg-kaihara-warning/20 text-kaihara-warning rounded">
            {pending.length}
          </span>
        </div>
        {pending.length === 0 ? (
          <div className="hud-panel text-center py-6">
            <p className="text-sm text-kaihara-muted mb-2">No pending approvals</p>
            <button
              onClick={handleCreateDemo}
              disabled={creatingDemo}
              className="px-3 py-1.5 text-xs bg-kaihara-accent text-white rounded hover:bg-kaihara-accent/80 disabled:opacity-50"
            >
              {creatingDemo ? 'Creating...' : '🧪 Create Test Approval'}
            </button>
            <p className="text-xs text-kaihara-muted mt-1">Dangerous actions will appear here</p>
          </div>
        ) : (
          <div className="space-y-2">
            {pending.map(a => (
              <div key={a.id} className="hud-panel border-l-2 border-kaihara-warning">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{a.action}</p>
                    <p className="text-xs text-kaihara-muted">Agent: {a.agent}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleApprove(a.id)} className="px-3 py-1 text-xs bg-kaihara-success text-white rounded hover:bg-kaihara-success/80">
                      Approve
                    </button>
                    <button onClick={() => handleDeny(a.id)} className="px-3 py-1 text-xs bg-kaihara-danger/20 text-kaihara-danger rounded hover:bg-kaihara-danger/30">
                      Deny
                    </button>
                  </div>
                </div>
                {a.details && (
                  <pre className="text-xs text-kaihara-muted mt-2 p-2 bg-kaihara-bg rounded font-mono">
                    {JSON.stringify(a.details, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* History */}
      <div>
        <h3 className="text-sm font-bold mb-3">History</h3>
        {history.length === 0 ? (
          <div className="hud-panel text-center py-4">
            <p className="text-xs text-kaihara-muted">No history yet</p>
          </div>
        ) : (
          <div className="space-y-1">
            {history.slice(0, 20).map(a => (
              <div key={a.id} className="hud-panel py-2">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={a.status} />
                    <span>{a.action}</span>
                  </div>
                  <span className="text-kaihara-muted">{a.agent}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================
// Audit Log Tab
// ============================================================

function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    getAuditLog(100).then(res => setEntries(res.entries || [])).catch(() => {})
    const i = setInterval(() => {
      getAuditLog(100).then(res => setEntries(res.entries || []))
    }, 10000)
    return () => clearInterval(i)
  }, [])

  const filtered = filter === 'all' ? entries : entries.filter(e => e.severity === filter)

  const severityColors: Record<string, string> = {
    info: 'bg-kaihara-border text-kaihara-muted',
    warning: 'bg-kaihara-warning/20 text-kaihara-warning',
    error: 'bg-kaihara-danger/20 text-kaihara-danger',
    critical: 'bg-kaihara-danger/30 text-kaihara-danger',
  }

  return (
    <div className="p-4 space-y-4">
      {/* Filter Bar */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-kaihara-muted">Filter:</span>
        {['all', 'info', 'warning', 'error', 'critical'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              filter === f ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-text'
            }`}
          >
            {f}
          </button>
        ))}
        <span className="text-xs text-kaihara-muted ml-auto">{filtered.length} entries</span>
      </div>

      {/* Log Entries */}
      <div className="space-y-1">
        {filtered.length === 0 ? (
          <div className="hud-panel text-center py-6">
            <p className="text-sm text-kaihara-muted">No audit entries</p>
          </div>
        ) : (
          filtered.map((e, i) => (
            <div key={i} className="hud-panel py-2">
              <div className="flex items-center gap-3 text-xs">
                <span className="font-mono text-kaihara-muted w-16">
                  {e.timestamp.split('T')[1]?.split('.')[0]}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${severityColors[e.severity] || 'bg-kaihara-border text-kaihara-muted'}`}>
                  {e.severity}
                </span>
                <span className="text-kaihara-accent font-medium">{e.agent}</span>
                <span className="text-kaihara-text flex-1 truncate">{e.action}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ============================================================
// Pentest Tab
// ============================================================

function Pentest() {
  const [target, setTarget] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])

  const fetchSessions = useCallback(async () => {
    try {
      const res = await getPentestSessions()
      setSessions(res.sessions || [])
    } catch {}
  }, [])

  useEffect(() => { fetchSessions() }, [fetchSessions])

  const handleRun = async () => {
    if (!target.trim() || running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await runPentest(target.trim(), false)
      setResult(res)
      fetchSessions()
    } catch {}
    setRunning(false)
  }

  return (
    <div className="p-4 space-y-4">
      {/* Warning Banner */}
      <div className="px-4 py-2 bg-kaihara-warning/10 border border-kaihara-warning/30 rounded-lg">
        <p className="text-xs text-kaihara-warning">
          ⚠️ Only scan targets you own or have permission to test. Unauthorized scanning is illegal.
        </p>
      </div>

      {/* Target Input */}
      <div className="hud-panel">
        <label className="text-xs text-kaihara-muted mb-2 block">TARGET</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRun()}
            placeholder="example.com"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-sm focus:outline-none focus:border-kaihara-accent font-mono"
            disabled={running}
          />
          <button
            onClick={handleRun}
            disabled={!target.trim() || running}
            className="px-4 py-2 bg-kaihara-danger text-white text-sm rounded hover:bg-kaihara-danger/80 disabled:opacity-50 font-medium"
          >
            {running ? 'Running...' : 'Run Pentest'}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-kaihara-muted">RESULT</h4>
            <StatusBadge status={result.status || (result.success ? 'ok' : 'error')} />
          </div>
          <pre className="text-xs text-kaihara-text overflow-x-auto max-h-64 overflow-y-auto bg-kaihara-bg p-3 rounded border border-kaihara-border font-mono">
            {JSON.stringify(result, null, 2).slice(0, 3000)}
          </pre>
        </div>
      )}

      {/* Sessions */}
      <div>
        <h3 className="text-sm font-bold mb-3">Sessions</h3>
        {sessions.length === 0 ? (
          <div className="hud-panel text-center py-4">
            <p className="text-xs text-kaihara-muted">No pentest sessions</p>
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map(s => (
              <div key={s.session_id} className="hud-panel py-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-kaihara-accent">{s.session_id}</span>
                  <span className="text-kaihara-text">{s.target}</span>
                </div>
                <div className="flex items-center gap-2 mt-1 text-xs text-kaihara-muted">
                  <span>{s.started_at?.split('T')[0]}</span>
                  <StatusBadge status={s.completed_at ? 'ok' : 'running'} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
