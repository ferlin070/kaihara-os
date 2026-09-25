import { useState, useEffect, useRef, useCallback } from 'react'
import { getMapState, type MapState } from '../lib/api'

// ============================================================
// Pixel Agents Style — Backend-driven character animation
// Backend (agent_map.py) sends: anim_state, anim_frame, direction
// Frontend just renders sprites based on backend state
// ============================================================

const TILE = 16
const ZOOM = 3

const AGENT_CONFIG: Record<string, { palette: number; label: string }> = {
  kaihara:   { palette: 0, label: 'Kaihara' },
  coding:    { palette: 1, label: 'Coder' },
  marketing: { palette: 2, label: 'Marketer' },
  security:  { palette: 3, label: 'Guard' },
  deploy:    { palette: 4, label: 'Deployer' },
  research:  { palette: 5, label: 'Researcher' },
  meta:      { palette: 0, label: 'Meta' },
}

// Sprite sheet: 7 frames x 16px wide, 3 rows x 32px tall
// Row 0=down, Row 1=up, Row 2=right (left=flipped right)
// Frames: walk1(0), walk2(1), walk3(2), type1(3), type2(4), read1(5), read2(6)
const STATE_FRAME_OFFSET: Record<string, number[]> = {
  walk: [0, 1, 2],
  type: [3, 4],
  read: [5, 6],
  idle: [0],
}

const DIR_ROW: Record<string, number> = {
  down: 0, up: 1, right: 2, left: 2,
}

// Office layout — desks in a room
const DESKS = [
  { col: 3, row: 2, agent: 'kaihara', label: 'HQ' },
  { col: 3, row: 4, agent: 'coding', label: 'Code' },
  { col: 3, row: 6, agent: 'marketing', label: 'Mkt' },
  { col: 9, row: 2, agent: 'security', label: 'Sec' },
  { col: 9, row: 4, agent: 'deploy', label: 'Dep' },
  { col: 9, row: 6, agent: 'research', label: 'Rsc' },
  { col: 14, row: 4, agent: 'meta', label: 'Meta' },
]

const COLS = 18
const ROWS = 9

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']

export default function AgentMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [mapState, setMapState] = useState<MapState | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const charImgsRef = useRef<HTMLImageElement[]>([])
  const floorImgRef = useRef<HTMLImageElement | null>(null)
  const deskImgRef = useRef<HTMLImageElement | null>(null)
  const animRef = useRef<number>(0)
  const assetsLoadedRef = useRef(false)

  // Load sprite images lazily (after 1s delay)
  useEffect(() => {
    if (assetsLoadedRef.current) return
    const timer = setTimeout(() => {
      const imgs: HTMLImageElement[] = []
      let loaded = 0
      const total = 8
      const onLoad = () => { loaded++; if (loaded >= total) assetsLoadedRef.current = true }
      for (let i = 0; i < 6; i++) {
        const img = new Image()
        img.onload = onLoad
        img.src = `/assets/characters/char_${i}.png`
        imgs.push(img)
      }
      charImgsRef.current = imgs
      const floor = new Image()
      floor.onload = onLoad
      floor.src = '/assets/floors/floor_0.png'
      floorImgRef.current = floor
      const desk = new Image()
      desk.onload = onLoad
      desk.src = '/assets/furniture/DESK/DESK_FRONT.png'
      deskImgRef.current = desk
    }, 1000)
    return () => clearTimeout(timer)
  }, [])

  // Fetch map state every 500ms (2fps for state, 60fps for rendering)
  const fetchState = useCallback(async () => {
    try { setMapState(await getMapState()) } catch {}
  }, [])

  useEffect(() => {
    fetchState()
    const i = setInterval(fetchState, 5000)
    return () => clearInterval(i)
  }, [fetchState])

  // Render loop — 60fps, always running
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.imageSmoothingEnabled = false

    const W = COLS * TILE
    const H = ROWS * TILE

    const loop = () => {
      // Clear
      ctx.fillStyle = '#0d1117'
      ctx.fillRect(0, 0, W, H)

      // Draw floor tiles
      const floorImg = floorImgRef.current
      if (floorImg && floorImg.complete && floorImg.naturalWidth > 0) {
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) {
            ctx.drawImage(floorImg, c * TILE, r * TILE, TILE, TILE)
          }
        }
      } else {
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) {
            ctx.fillStyle = (c + r) % 2 === 0 ? '#161b22' : '#111827'
            ctx.fillRect(c * TILE, r * TILE, TILE, TILE)
          }
        }
      }

      // Draw walls (top border)
      ctx.fillStyle = '#1c2128'
      ctx.fillRect(0, 0, W, TILE)
      ctx.fillStyle = '#252b36'
      ctx.fillRect(0, 0, W, 2)

      // Draw desks
      const deskImg = deskImgRef.current
      for (const desk of DESKS) {
        const dx = desk.col * TILE - 8
        const dy = desk.row * TILE - 16
        const palette = AGENT_CONFIG[desk.agent]?.palette || 0
        const color = COLORS[palette]

        if (deskImg && deskImg.complete && deskImg.naturalWidth > 0) {
          ctx.drawImage(deskImg, dx, dy, 48, 32)
        } else {
          ctx.fillStyle = color + '30'
          ctx.fillRect(dx, dy, 48, 32)
          ctx.strokeStyle = color
          ctx.lineWidth = 0.5
          ctx.strokeRect(dx, dy, 48, 32)
        }

        ctx.fillStyle = color
        ctx.font = 'bold 7px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(desk.label, desk.col * TILE + 8, desk.row * TILE + 18)
      }

      // Get agents from API state
      const agents = mapState?.agents || {}

      // Z-sort agents by Y
      const agentList = Object.entries(agents).sort(([, a], [, b]) => a.y - b.y)

      // Draw each agent
      for (const [name, agent] of agentList) {
        const cfg = AGENT_CONFIG[name]
        const palette = cfg?.palette || 0
        const color = COLORS[palette]

        // Convert API coords (800x600) to tile space (288x144)
        const x = (agent.x / 800) * W
        const y = (agent.y / 600) * H

        // Get animation state from backend
        const animState = (agent as any).anim_state || 'idle'
        const animFrame = (agent as any).anim_frame || 0
        const direction = (agent as any).direction || 'down'

        // Calculate sprite source from backend-provided frame
        const frames = STATE_FRAME_OFFSET[animState] || STATE_FRAME_OFFSET.idle
        const frameIdx = frames[animFrame % frames.length]
        const row = DIR_ROW[direction] ?? 0
        const srcX = frameIdx * 16
        const srcY = row * 32

        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.3)'
        ctx.beginPath()
        ctx.ellipse(x, y, 6, 2, 0, 0, Math.PI * 2)
        ctx.fill()

        // Draw character sprite
        const img = charImgsRef.current[palette]
        if (img && img.complete && img.naturalWidth > 0) {
          if (direction === 'left') {
            ctx.save()
            ctx.scale(-1, 1)
            ctx.drawImage(img, srcX, srcY, 16, 32,
              -(x - 8), y - 28, 16, 32)
            ctx.restore()
          } else {
            ctx.drawImage(img, srcX, srcY, 16, 32,
              x - 8, y - 28, 16, 32)
          }
        } else {
          // Fallback: colored circle
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(x, y - 12, 6, 0, Math.PI * 2)
          ctx.fill()
        }

        // Selection highlight
        if (selected === name) {
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth = 1
          ctx.setLineDash([2, 2])
          ctx.beginPath()
          ctx.arc(x, y - 12, 10, 0, Math.PI * 2)
          ctx.stroke()
          ctx.setLineDash([])
        }

        // Working ring
        if (animState === 'type') {
          ctx.strokeStyle = '#10b981'
          ctx.lineWidth = 0.5
          ctx.beginPath()
          ctx.arc(x, y - 12, 9, 0, Math.PI * 2)
          ctx.stroke()
        }

        // Name label
        ctx.fillStyle = '#6b7280'
        ctx.font = 'bold 6px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(cfg?.label || name, x, y + 2)

        // Speech bubble
        if (agent.speech) {
          const text = agent.speech.length > 20 ? agent.speech.slice(0, 17) + '...' : agent.speech
          ctx.font = '6px monospace'
          const tw = ctx.measureText(text).width + 8
          const bx = x - tw / 2
          const by = y - 42
          ctx.fillStyle = '#1f2937'
          ctx.strokeStyle = color
          ctx.lineWidth = 0.5
          ctx.fillRect(bx, by, tw, 10)
          ctx.strokeRect(bx, by, tw, 10)
          // Tail
          ctx.beginPath()
          ctx.moveTo(x - 2, by + 10)
          ctx.lineTo(x, by + 13)
          ctx.lineTo(x + 2, by + 10)
          ctx.fillStyle = '#1f2937'
          ctx.fill()
          ctx.fillStyle = '#e5e7eb'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(text, x, by + 5)
        }

        // Progress bar
        if (agent.progress > 0 && animState === 'type') {
          ctx.fillStyle = '#1f2937'
          ctx.fillRect(x - 8, y + 10, 16, 1.5)
          ctx.fillStyle = '#10b981'
          ctx.fillRect(x - 8, y + 10, 16 * agent.progress / 100, 1.5)
        }
      }

      // Title
      ctx.fillStyle = '#374151'
      ctx.font = '6px monospace'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      ctx.fillText('KAIHARA PIXEL OFFICE', 2, 2)

      animRef.current = requestAnimationFrame(loop)
    }

    animRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animRef.current)
  }, [mapState, selected])

  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas || !mapState) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    for (const [name, agent] of Object.entries(mapState.agents || {})) {
      const ax = (agent.x / 800) * (COLS * TILE)
      const ay = (agent.y / 600) * (ROWS * TILE)
      const dist = Math.sqrt((ax - x) ** 2 + ((ay - 12) - y) ** 2)
      if (dist < 12) {
        setSelected(selected === name ? null : name)
        return
      }
    }
    setSelected(null)
  }

  const canvasW = COLS * TILE
  const canvasH = ROWS * TILE

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="flex-shrink-0 px-4 py-2 border-b border-kaihara-border flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide">Pixel Office</h2>
        <div className="flex items-center gap-2 text-xs flex-wrap">
          {Object.entries(AGENT_CONFIG).map(([name, cfg]) => (
            <span key={name} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[cfg.palette] }} />
              <span className="text-kaihara-muted">{cfg.label}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center overflow-hidden p-4">
        <canvas
          ref={canvasRef}
          width={canvasW}
          height={canvasH}
          onClick={handleClick}
          className="border border-kaihara-border rounded"
          style={{
            imageRendering: 'pixelated',
            width: `${canvasW * ZOOM}px`,
            height: `${canvasH * ZOOM}px`,
            maxWidth: '100%',
            maxHeight: '100%',
          }}
        />
      </div>
      {selected && mapState?.agents?.[selected] && (
        <div className="flex-shrink-0 px-4 py-2 border-t border-kaihara-border text-xs flex items-center gap-3">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[AGENT_CONFIG[selected]?.palette || 0] }} />
          <span className="text-kaihara-accent font-bold">{AGENT_CONFIG[selected]?.label || selected}</span>
          <span className="text-kaihara-muted">— {mapState.agents[selected].status}</span>
          {mapState.agents[selected].task && (
            <span className="text-kaihara-muted truncate">— {mapState.agents[selected].task}</span>
          )}
        </div>
      )}
    </div>
  )
}
