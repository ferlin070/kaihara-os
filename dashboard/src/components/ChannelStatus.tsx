import { getChannelsStatus, type ChannelStatus } from '../lib/api'
import { useState, useEffect } from 'react'

const channelIcons: Record<string, string> = {
  telegram: 'TG',
  whatsapp: 'WA',
  email: 'MAIL',
}

export default function ChannelStatus() {
  const [channels, setChannels] = useState<Record<string, ChannelStatus>>({})

  useEffect(() => {
    getChannelsStatus().then(setChannels).catch(() => {})
    const i = setInterval(() => {
      getChannelsStatus().then(setChannels).catch(() => {})
    }, 15000)
    return () => clearInterval(i)
  }, [])

  const entries = Object.entries(channels)
  if (entries.length === 0) {
    return (
      <div className="hud-panel">
        <div className="hud-title">Channels</div>
        <p className="text-xs text-kaihara-muted">No channels configured.</p>
      </div>
    )
  }

  return (
    <div className="hud-panel">
      <div className="hud-title">Channels</div>
      <div className="space-y-2">
        {entries.map(([name, ch]) => (
          <div key={name} className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-2">
              <span className="font-mono text-kaihara-accent w-8">
                {channelIcons[name] || name.slice(0, 3).toUpperCase()}
              </span>
              <span className="capitalize">{name}</span>
            </span>
            <span className="flex items-center gap-1.5">
              {ch.running ? (
                <span className="flex items-center gap-1 text-kaihara-success">
                  <span className="status-dot bg-kaihara-success animate-pulse" />
                  ON
                </span>
              ) : ch.enabled ? (
                <span className="flex items-center gap-1 text-kaihara-warning">
                  <span className="status-dot bg-kaihara-warning" />
                  IDLE
                </span>
              ) : (
                <span className="flex items-center gap-1 text-kaihara-muted">
                  <span className="status-dot bg-kaihara-muted" />
                  OFF
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
