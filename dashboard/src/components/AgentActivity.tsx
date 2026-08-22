interface Agent {
  name: string
  status: string
  task: string
  progress: number
}

export default function AgentActivity({ agents }: { agents: Agent[] }) {
  const statusColors: Record<string, string> = {
    running: 'bg-kaihara-success',
    idle: 'bg-kaihara-muted',
    waiting: 'bg-kaihara-warning',
    error: 'bg-kaihara-danger',
  }
  const statusIcons: Record<string, string> = {
    running: '🟢',
    idle: '⚪',
    waiting: '🟡',
    error: '🔴',
  }

  return (
    <div className="hud-panel">
      <div className="hud-title">Agent Activity</div>
      {agents.length === 0 ? (
        <p className="text-xs text-kaihara-muted">No agents running.</p>
      ) : (
        <div className="space-y-2">
          {agents.map((agent) => (
            <div key={agent.name} className="text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="flex items-center gap-1.5">
                  <span>{statusIcons[agent.status] || '⚪'}</span>
                  <span className="capitalize font-medium">{agent.name}</span>
                </span>
                {agent.progress > 0 && (
                  <span className="text-kaihara-muted">{agent.progress}%</span>
                )}
              </div>
              {agent.task && (
                <p className="text-kaihara-muted truncate">{agent.task}</p>
              )}
              {agent.progress > 0 && (
                <div className="h-1 bg-kaihara-border rounded-full overflow-hidden mt-1">
                  <div
                    className="h-full bg-kaihara-accent transition-all duration-500"
                    style={{ width: `${agent.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
