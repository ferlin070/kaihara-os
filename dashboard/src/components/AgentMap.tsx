import { useState, useEffect, useRef, useCallback } from 'react'
import { getMapState, type MapState } from '../lib/api'

// Agent character config
const AGENT_CHARS: Record<string, { emoji: string; color: string; label: string }> = {
  kaihara:   { emoji: '🤖', color: '#3b82f6', label: 'Kaihara' },
  coding:    { emoji: '👨‍💻', color: '#10b981', label: 'Coder' },
  marketing: { emoji: '📈', color: '#f59e0b', label: 'Marketer' },
  security:  { emoji: '🛡️', color: '#ef4444', label: 'Guard' },
  deploy:    { emoji: '🚀', color: '#8b5cf6', label: 'Deployer' },
  research:  { emoji: '🔍', color: '#06b6d4', label: 'Researcher' },
  meta:      { emoji: '👁️', color: '#ec4899', label: 'Meta' },
}

// Building types → draw function
function drawBuilding(ctx: CanvasRenderingContext2D, x: number, y: number,
                       w: number, h: number, type: string, color: string) {
  const left = x - w / 2
  const top = y - h / 2

  // Shadow
  ctx.fillStyle = 'rgba(0,0,0,0.3)'
  ctx.fillRect(left + 3, top + 3, w, h)

  // Building base
  ctx.fillStyle = color + '30'
  ctx.fillRect(left, top, w, h)
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.strokeRect(left, top, w, h)

  // Roof based on type
  ctx.fillStyle = color
  if (type === 'hq') {
    // Command center — big building with antenna
    ctx.fillRect(left, top - 8, w, 8)
    ctx.fillRect(x - 2, top - 20, 4, 12)
    ctx.beginPath(); ctx.arc(x, top - 22, 3, 0, Math.PI * 2); ctx.fill()
  } else if (type === 'fort') {
    // Security — battlements
    for (let i = 0; i < 4; i++) {
      ctx.fillRect(left + i * (w / 4), top - 6, w / 8, 6)
    }
  } else if (type === 'tower') {
    // Observatory — dome
    ctx.beginPath()
    ctx.arc(x, top, w / 3, Math.PI, 0)
    ctx.fill()
  } else if (type === 'library') {
    // Library — peaked roof
    ctx.beginPath()
    ctx.moveTo(left, top)
    ctx.lineTo(x, top - 12)
    ctx.lineTo(left + w, top)
    ctx.fill()
  } else {
    // Default — flat roof line
    ctx.fillRect(left, top - 4, w, 4)
  }

  // Windows
  ctx.fillStyle = color + '60'
  const winSize = 6
  const winSpacing = 12
  for (let wx = left + 8; wx < left + w - winSize; wx += winSpacing) {
    for (let wy = top + 10; wy < top + h - winSize; wy += winSpacing) {
      ctx.fillRect(wx, wy, winSize, winSize)
    }
  }
}

function drawCharacter(ctx: CanvasRenderingContext2D, x: number, y: number,
                        emoji: string, color: string, status: string,
                        speech: string, selected: boolean) {
  // Shadow
  ctx.beginPath()
  ctx.ellipse(x, y + 14, 10, 4, 0, 0, Math.PI * 2)
  ctx.fillStyle = 'rgba(0,0,0,0.3)'
  ctx.fill()

  // Body circle
  ctx.beginPath()
  ctx.arc(x, y, 12, 0, Math.PI * 2)
  ctx.fillStyle = color
  ctx.fill()
  ctx.strokeStyle = selected ? '#ffffff' : color + 'aa'
  ctx.lineWidth = selected ? 3 : 1.5
  ctx.stroke()

  // Emoji on body
  ctx.font = '14px serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(emoji, x, y + 1)

  // Status ring
  if (status === 'working') {
    ctx.beginPath()
    ctx.arc(x, y, 16, 0, Math.PI * 2)
    ctx.strokeStyle = '#10b981'
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.stroke()
  } else if (status === 'moving') {
    ctx.beginPath()
    ctx.arc(x, y, 16, 0, Math.PI * 2)
    ctx.strokeStyle = '#f59e0b'
    ctx.lineWidth = 2
    ctx.setLineDash([4, 4])
    ctx.stroke()
    ctx.setLineDash([])
  }

  // Speech bubble
  if (speech) {
    const text = speech.length > 28 ? speech.slice(0, 25) + '...' : speech
    ctx.font = '11px monospace'
    const tw = ctx.measureText(text).width + 16
    const bx = x - tw / 2
    const by = y - 38
    // Bubble bg
    ctx.fillStyle = '#1f2937'
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    roundRect(ctx, bx, by, tw, 22, 6)
    ctx.fill()
    ctx.stroke()
    // Tail
    ctx.beginPath()
    ctx.moveTo(x - 5, by + 22)
    ctx.lineTo(x, by + 28)
    ctx.lineTo(x + 5, by + 22)
    ctx.fillStyle = '#1f2937'
    ctx.fill()
    // Text
    ctx.fillStyle = '#e5e7eb'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(text, x, by + 11)
  }
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

export default function AgentMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [state, setState] = useState<MapState | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)

  const fetchState = useCallback(async () => {
    try { setState(await getMapState()) } catch {}
  }, [])

  useEffect(() => {
    fetchState()
    const i = setInterval(fetchState, 1000)
    return () => clearInterval(i)
  }, [fetchState])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !state) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 800, H = 600

    // Background — grass + paths
    // Grass
    ctx.fillStyle = '#0d1117'
    ctx.fillRect(0, 0, W, H)

    // Grass texture (dots)
    ctx.fillStyle = '#161b22'
    for (let i = 0; i < 200; i++) {
      const gx = (i * 37) % W
      const gy = (i * 53) % H
      ctx.fillRect(gx, gy, 2, 2)
    }

    // Paths between buildings
    ctx.strokeStyle = '#1c2128'
    ctx.lineWidth = 20
    ctx.lineCap = 'round'
    const stations = state.stations || {}
    // Horizontal path
    ctx.beginPath()
    ctx.moveTo(130, 300)
    ctx.lineTo(670, 300)
    ctx.stroke()
    // Vertical path
    ctx.beginPath()
    ctx.moveTo(400, 80)
    ctx.lineTo(400, 520)
    ctx.stroke()
    // Diagonals
    ctx.lineWidth = 12
    ctx.beginPath(); ctx.moveTo(130, 130); ctx.lineTo(400, 280); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(670, 130); ctx.lineTo(400, 280); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(130, 470); ctx.lineTo(400, 280); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(670, 470); ctx.lineTo(400, 280); ctx.stroke()

    // Draw buildings
    Object.entries(stations).forEach(([name, s]) => {
      drawBuilding(ctx, s.x, s.y, s.w || 90, s.h || 70, s.type || 'default', s.color)
      // Label
      ctx.fillStyle = s.color
      ctx.font = 'bold 10px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(s.label, s.x, (s.y || 0) + ((s.h || 70) / 2) + 4)
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

    // Draw agents (characters)
    Object.entries(state.agents || {}).forEach(([name, a]) => {
      const char = AGENT_CHARS[name] || { emoji: '?', color: a.color, label: name }
      const isSelected = selected === name
      const isHovered = hovered === name
      const displaySize = isSelected || isHovered ? 14 : 12

      // Movement trail
      if (a.moving) {
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(a.target_x, a.target_y)
        ctx.strokeStyle = char.color + '40'
        ctx.lineWidth = 1.5
        ctx.setLineDash([2, 4])
        ctx.stroke()
        ctx.setLineDash([])
      }

      drawCharacter(ctx, a.x, a.y, char.emoji, char.color,
                     a.status, a.speech, isSelected)

      // Name label below
      ctx.fillStyle = isSelected ? '#fff' : '#6b7280'
      ctx.font = `${isSelected ? 'bold ' : ''}10px monospace`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(char.label, a.x, a.y + 18)

      // Progress bar
      if (a.progress > 0 && a.status === 'working') {
        ctx.fillStyle = '#1f2937'
        ctx.fillRect(a.x - 15, a.y + 30, 30, 3)
        ctx.fillStyle = char.color
        ctx.fillRect(a.x - 15, a.y + 30, 30 * a.progress / 100, 3)
      }
    })

    // Title
    ctx.fillStyle = '#6b7280'
    ctx.font = '10px monospace'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText('KAIHARA TOWN — Live Agent Activity', 10, 8)
  }, [state, selected, hovered])

  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas || !state) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvas.width / rect.width)
    const y = (e.clientY - rect.top) * (canvas.height / rect.height)
    for (const [name, a] of Object.entries(state.agents || {})) {
      const dist = Math.sqrt((a.x - x) ** 2 + (a.y - y) ** 2)
      if (dist < 16) {
        setSelected(selected === name ? null : name)
        return
      }
    }
    setSelected(null)
  }

  const handleMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas || !state) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvas.width / rect.width)
    const y = (e.clientY - rect.top) * (canvas.height / rect.height)
    let found = null
    for (const [name, a] of Object.entries(state.agents || {})) {
      const dist = Math.sqrt((a.x - x) ** 2 + (a.y - y) ** 2)
      if (dist < 16) { found = name; break }
    }
    setHovered(found)
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="flex-shrink-0 px-4 py-2 border-b border-kaihara-border flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide">Kaihara Town</h2>
        <div className="flex items-center gap-3 text-xs">
          {Object.entries(AGENT_CHARS).map(([name, char]) => (
            <span key={name} className="flex items-center gap-1">
              <span>{char.emoji}</span>
              <span className="text-kaihara-muted">{char.label}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center overflow-hidden p-4">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          onClick={handleClick}
          onMouseMove={handleMove}
          className="border border-kaihara-border rounded-lg cursor-pointer"
          style={{ maxWidth: '100%', maxHeight: '100%', imageRendering: 'auto' }}
        />
      </div>
      {selected && state?.agents[selected] && (
        <div className="flex-shrink-0 px-4 py-2 border-t border-kaihara-border text-xs flex items-center gap-3">
          <span className="text-lg">{AGENT_CHARS[selected]?.emoji}</span>
          <span className="text-kaihara-accent font-bold">{AGENT_CHARS[selected]?.label || selected}</span>
          <span className="text-kaihara-muted">— {state.agents[selected].status}</span>
          {state.agents[selected].task && (
            <span className="text-kaihara-muted truncate">— {state.agents[selected].task}</span>
          )}
          <span className="text-kaihara-muted ml-auto">at {state.agents[selected].station}</span>
        </div>
      )}
    </div>
  )
}
