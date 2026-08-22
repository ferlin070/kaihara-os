export default function KaiharaStatus({ thinking, online }: { thinking: boolean; online: boolean }) {
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
      </div>
    </div>
  )
}
