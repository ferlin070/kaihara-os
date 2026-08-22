import { useState, useEffect, useCallback } from 'react'
import {
  getSecurityStatus,
  getApprovals,
  approveAction,
  denyAction,
  getAuditLog,
  runPentest,
  getPentestSessions,
  type SecurityStatus,
  type Approval,
  type AuditEntry,
} from '../lib/api'

type Tab = 'overview' | 'approvals' | 'audit' | 'pentest'

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
    <div className="flex-1 flex flex-col">
      <div className="flex border-b border-kaihara-border">
        {(['overview', 'approvals', 'audit', 'pentest'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium uppercase tracking-wide transition-colors ${
              tab === t
                ? 'text-kaihara-accent border-b-2 border-kaihara-accent'
                : 'text-kaihara-muted hover:text-kaihara-text'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'overview' && <Overview status={status} />}
      {tab === 'approvals' && <Approvals />}
      {tab === 'audit' && <AuditLog />}
      {tab === 'pentest' && <Pentest />}
    </div>
  )
}

function Overview({ status }: { status: SecurityStatus | null }) {
  if (!status) {
    return <div className="p-6 text-kaihara-muted text-sm">Loading...</div>
  }
  const cards = [
    { label: 'Approval Gate', data: status.approval_gate,
      icon: '🔒', color: 'text-kaihara-warning' },
    { label: 'Sandbox', data: status.sandbox,
      icon: '📦', color: 'text-kaihara-accent' },
    { label: 'Audit Trail', data: status.audit,
      icon: '📋', color: 'text-kaihara-success' },
    { label: 'Pentest', data: status.pentest,
      icon: '🎯', color: 'text-kaihara-danger' },
  ]
  return (
    <div className="flex-1 p-4 overflow-y-auto">
      <div className="grid grid-cols-2 gap-3">
        {cards.map(card => (
          <div key={card.label} className="hud-panel">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">{card.icon}</span>
              <h3 className={`text-sm font-bold ${card.color}`}>{card.label}</h3>
            </div>
            {card.data && typeof card.data === 'object' ? (
              <div className="space-y-1 text-xs">
                {Object.entries(card.data).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-kaihara-muted">{k}</span>
                    <span>{String(v)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-kaihara-muted">Not available</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

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

  const handleApprove = async (id: string) => { await approveAction(id); fetch() }
  const handleDeny = async (id: string) => { await denyAction(id, 'Denied by user'); fetch() }

  return (
    <div className="flex-1 p-4 overflow-y-auto space-y-4">
      <div>
        <h3 className="hud-title">Pending Approvals ({pending.length})</h3>
        {pending.length === 0 ? (
          <p className="text-xs text-kaihara-muted">No pending approvals.</p>
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
                    <button onClick={() => handleApprove(a.id)} className="btn-primary text-xs">
                      Approve
                    </button>
                    <button onClick={() => handleDeny(a.id)} className="btn-ghost text-xs text-kaihara-danger">
                      Deny
                    </button>
                  </div>
                </div>
                <p className="text-xs text-kaihara-muted mt-1">{JSON.stringify(a.details)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <h3 className="hud-title">History ({history.length})</h3>
        {history.slice(0, 10).map(a => (
          <div key={a.id} className="hud-panel mb-1">
            <div className="flex items-center justify-between text-xs">
              <span>{a.action}</span>
              <span className={
                a.status === 'approved' ? 'text-kaihara-success' :
                a.status === 'denied' ? 'text-kaihara-danger' : 'text-kaihara-muted'
              }>{a.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])

  useEffect(() => {
    getAuditLog(50).then(res => setEntries(res.entries || [])).catch(() => {})
    const i = setInterval(() => {
      getAuditLog(50).then(res => setEntries(res.entries || []))
    }, 10000)
    return () => clearInterval(i)
  }, [])

  const severityColors: Record<string, string> = {
    info: 'text-kaihara-muted',
    warning: 'text-kaihara-warning',
    error: 'text-kaihara-danger',
    critical: 'text-kaihara-danger',
  }

  return (
    <div className="flex-1 p-4 overflow-y-auto">
      <h3 className="hud-title">Audit Log ({entries.length})</h3>
      <div className="space-y-1">
        {entries.length === 0 ? (
          <p className="text-xs text-kaihara-muted">No audit entries.</p>
        ) : (
          entries.map((e, i) => (
            <div key={i} className="hud-panel py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono text-kaihara-muted">
                  {e.timestamp.split('T')[1]?.split('.')[0]}
                </span>
                <span className={`uppercase ${severityColors[e.severity] || 'text-kaihara-muted'}`}>
                  {e.severity}
                </span>
              </div>
              <div className="mt-1">
                <span className="text-kaihara-accent">[{e.agent}]</span> {e.action}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

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
    try {
      const res = await runPentest(target.trim(), false)
      setResult(res)
      fetchSessions()
    } catch {}
    setRunning(false)
  }

  return (
    <div className="flex-1 p-4 overflow-y-auto space-y-4">
      <div>
        <h3 className="hud-title">Run Pentest</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRun()}
            placeholder="Target (e.g. example.com)"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={running}
          />
          <button
            onClick={handleRun}
            disabled={!target.trim() || running}
            className="btn-primary disabled:opacity-50"
          >
            {running ? 'Running...' : 'Scan'}
          </button>
        </div>
        <p className="text-xs text-kaihara-warning mt-2">
          WARNING: Only scan targets you own or have permission to test.
        </p>
      </div>

      {result && (
        <div className="hud-panel">
          <h4 className="text-sm font-bold mb-2">Result</h4>
          <pre className="text-xs text-kaihara-muted overflow-x-auto">
            {JSON.stringify(result, null, 2).slice(0, 2000)}
          </pre>
        </div>
      )}

      <div>
        <h3 className="hud-title">Sessions ({sessions.length})</h3>
        {sessions.length === 0 ? (
          <p className="text-xs text-kaihara-muted">No pentest sessions.</p>
        ) : (
          <div className="space-y-1">
            {sessions.map(s => (
              <div key={s.session_id} className="hud-panel text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-kaihara-accent">{s.session_id}</span>
                  <span className="text-kaihara-muted">{s.target}</span>
                </div>
                <div className="text-kaihara-muted mt-1">
                  {s.started_at?.split('T')[0]}
                  {s.completed_at ? ' → done' : ' → running'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
