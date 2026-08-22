import type { SystemStatus as Status } from '../lib/api'

export default function SystemStatus({ status }: { status: Status | null }) {
  if (!status) {
    return (
      <div className="hud-panel">
        <div className="hud-title">System Status</div>
        <p className="text-xs text-kaihara-muted">Connecting...</p>
      </div>
    )
  }

  return (
    <div className="hud-panel">
      <div className="hud-title">System Status</div>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-kaihara-muted">Models</span>
          <span className="text-kaihara-success">{status.model?.length || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-kaihara-muted">Agents</span>
          <span className="text-kaihara-success">{status.fleet_agents?.length || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-kaihara-muted">Memory</span>
          <span className={status.memory ? 'text-kaihara-success' : 'text-kaihara-danger'}>
            {status.memory ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-kaihara-muted">TokenJuice</span>
          <span className={status.token_juice ? 'text-kaihara-success' : 'text-kaihara-danger'}>
            {status.token_juice ? 'On' : 'Off'}
          </span>
        </div>
      </div>
      {status.model && status.model.length > 0 && (
        <div className="mt-3 pt-3 border-t border-kaihara-border">
          <p className="text-xs text-kaihara-muted mb-1">Providers:</p>
          <div className="space-y-0.5">
            {status.model.slice(0, 3).map((m, i) => (
              <p key={i} className="text-xs truncate">{m}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
