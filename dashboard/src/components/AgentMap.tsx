import { useState, useEffect, useRef, useCallback } from 'react'
import { getMapState, type MapState } from '../lib/api'

export default function AgentMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [state, setState] = useState<MapState | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const fetchState = useCallback(async () => {
    try {
      setState(await getMapState())
    } catch {}
  }, [])

  useEffect(() => {
    fetchState()
    const i = setInterval(fetchState, 1000)
    return () => clearInterval(i)
  }, [fetchState])

  useEffect(() => {
    if (!state || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 800
    const H = 600

    // Clear
    ctx.fillStyle = '#0a0e1a'
    ctx.fillRect(0, 0, W, H)

    // Draw grid
    ctx.strokeStyle = '#111827'
    ctx.lineWidth = 1
    for (let x = 0; x < W; x += 40) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, H)
      ctx.stroke()
    }
    for (let y = 0; y < H; y += 40) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(W, y)
      ctx.stroke()
    }

    // Draw stations
    const stations = state.stations || {}
    Object.entries(stations).forEach(([name, s]) => {
      // Station circle
      ctx.beginPath()
      ctx.arc(s.x, s.y, 35, 0, Math.PI * 2)
      ctx.fillStyle = s.color + '20'
      ctx.fill()
      ctx.strokeStyle = s.color
      ctx.lineWidth = 1.5
      ctx.setLineDash([4, 4])
      ctx.stroke()
      ctx.setLineDash([])

      // Station label
      ctx.fillStyle = s.color
      ctx.font = 'bold 10px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(s.icon, s.x, s.y - 5)
      ctx.fillStyle = '#6b7280'
      ctx.font = '9px monospace'
      ctx.fillText(s.label, s.x, s.y + 15)
    })

    // Draw interactions (lines between agents)
    if (state.interactions) {
      state.interactions.slice(-5).forEach(inter => {
        const a = state.agents[inter.agent_a]
        const b = state.agents[inter.agent_b]
        if (a && b) {
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.strokeStyle = '#06b6d440'
          ctx.lineWidth = 2
          ctx.setLineDash([3, 3])
          ctx.stroke()
          ctx.setLineDash([])
        }
      })
    }

    // Draw agents
    const agents = state.agents || {}
    Object.entries(agents).forEach(([name, a]) => {
      const isSelected = selected === name

      // Movement trail
      if (a.moving) {
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(a.target_x, a.target_y)
        ctx.strokeStyle = a.color + '40'
        ctx.lineWidth = 1
        ctx.setLineDash([2, 4])
        ctx.stroke()
        ctx.setLineDash([])
      }

      // Agent circle
      ctx.beginPath()
      ctx.arc(a.x, a.y, isSelected ? 14 : 12, 0, Math.PI * 2)
      ctx.fillStyle = a.color
      ctx.fill()
      ctx.strokeStyle = isSelected ? '#fff' : a.color + '80'
      ctx.lineWidth = isSelected ? 3 : 2
      ctx.stroke()

      // Status ring
      if (a.status === 'working') {
        ctx.beginPath()
        ctx.arc(a.x, a.y, 16, 0, Math.PI * 2)
        ctx.strokeStyle = '#10b981'
        ctx.lineWidth = 1.5
        ctx.stroke()
      } else if (a.status === 'moving') {
        ctx.beginPath()
        ctx.arc(a.x, a.y, 16, 0, Math.PI * 2)
        ctx.strokeStyle = '#f59e0b'
        ctx.lineWidth = 1.5
        ctx.setLineDash([3, 3])
        ctx.stroke()
        ctx.setLineDash([])
      }

      // Agent name
      ctx.fillStyle = '#e5e7eb'
      ctx.font = 'bold 10px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(name, a.x, a.y + 28)

      // Speech bubble
      if (a.speech) {
        const text = a.speech.length > 30 ? a.speech.slice(0, 27) + '...' : a.speech
        ctx.font = '10px monospace'
        const tw = ctx.measureText(text).width + 12
        const bx = a.x - tw / 2
        const by = a.y - 35
        ctx.fillStyle = '#1f2937'
        ctx.strokeStyle = a.color
        ctx.lineWidth = 1
        roundRect(ctx, bx, by, tw, 20, 4)
        ctx.fill()
        ctx.stroke()
        // Bubble tail
        ctx.beginPath()
        ctx.moveTo(a.x - 4, by + 20)
        ctx.lineTo(a.x, by + 25)
        ctx.lineTo(a.x + 4, by + 20)
        ctx.fillStyle = '#1f2937'
        ctx.fill()
        // Text
        ctx.fillStyle = '#e5e7eb'
        ctx.textAlign = 'center'
        ctx.fillText(text, a.x, by + 13)
      }

      // Progress bar
      if (a.progress > 0 && a.status === 'working') {
        ctx.fillStyle = '#1f2937'
        ctx.fillRect(a.x - 15, a.y + 32, 30, 3)
        ctx.fillStyle = a.color
        ctx.fillRect(a.x - 15, a.y + 32, 30 * a.progress / 100, 3)
      }
    })

    // Draw title
    ctx.fillStyle = '#6b7280'
    ctx.font = '10px monospace'
    ctx.textAlign = 'left'
    ctx.fillText('KAIHARA CONTROL ROOM — Live Agent Activity', 10, 15)

  }, [state, selected])

  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas || !state) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvas.width / rect.width)
    const y = (e.clientY - rect.top) * (canvas.height / rect.height)
    for (const [name, a] of Object.entries(state.agents || {})) {
      const dist = Math.sqrt((a.x - x) ** 2 + (a.y - y) ** 2)
      if (dist < 15) {
        setSelected(selected === name ? null : name)
        return
      }
    }
    setSelected(null)
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="px-4 py-2 border-b border-kaihara-border flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide">Agent Map</h2>
        <span className="text-xs text-kaihara-muted">
          {state ? `${Object.keys(state.agents).length} agents` : 'Loading...'}
        </span>
      </div>
      <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          onClick={handleClick}
          className="border border-kaihara-border rounded-lg cursor-pointer max-w-full"
          style={{ imageRendering: 'pixelated' }}
        />
      </div>
      {selected && state?.agents[selected] && (
        <div className="px-4 py-2 border-t border-kaihara-border text-xs">
          <span className="text-kaihara-accent font-bold">{selected}</span>
          <span className="text-kaihara-muted"> — {state.agents[selected].status}</span>
          {state.agents[selected].task && (
            <span className="text-kaihara-muted"> — {state.agents[selected].task}</span>
          )}
          <span className="text-kaihara-muted"> — at {state.agents[selected].station}</span>
        </div>
      )}
    </div>
  )
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number,
                    w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
