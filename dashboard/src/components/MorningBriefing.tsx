export default function MorningBriefing() {
  const now = new Date()
  const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  const date = now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' })

  return (
    <div className="hud-panel">
      <div className="hud-title">Morning Briefing</div>
      <p className="text-xs text-kaihara-muted mb-2">{date} • {time}</p>
      <div className="space-y-1.5 text-xs">
        <div className="flex items-start gap-2">
          <span className="text-kaihara-accent">▸</span>
          <span>System nominal. All agents online.</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-kaihara-accent">▸</span>
          <span>No security alerts overnight.</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-kaihara-accent">▸</span>
          <span>Memory backup completed at 3:00 AM.</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-kaihara-warning">▸</span>
          <span>3 pending tasks require review.</span>
        </div>
      </div>
    </div>
  )
}
