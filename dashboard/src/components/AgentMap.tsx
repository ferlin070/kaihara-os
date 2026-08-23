import { useState, useEffect, useRef, useCallback } from 'react'
import { getMapState, type MapState } from '../lib/api'

// ============================================================
// Pixel Agents Style — Character sprites + tile-based office
// Sprite sheet: 112x96px, 7 frames x 16px wide, 3 rows x 32px tall
// Row 0=down, Row 1=up, Row 2=right (left=flipped right)
// Frame order: walk1, walk2, walk3, type1, type2, read1, read2
// ============================================================

const TILE = 16 // pixel-art tile size (original pixel-agents use 16px)

const AGENT_CONFIG: Record<string, { palette: number; label: string; emoji: string }> = {
  kaihara:   { palette: 0, label: 'Kaihara', emoji: 'K' },
  coding:    { palette: 1, label: 'Coder', emoji: 'C' },
  marketing: { palette: 2, label: 'Marketer', emoji: 'M' },
  security:  { palette: 3, label: 'Guard', emoji: 'S' },
  deploy:    { palette: 4, label: 'Deployer', emoji: 'D' },
  research:  { palette: 5, label: 'Researcher', emoji: 'R' },
  meta:      { palette: 0, label: 'Meta', emoji: '?' }, // reuse palette 0
}

const STATE_FRAMES: Record<string, number[]> = {
  walk: [0, 1, 2],
  type: [3, 4],
  read: [5, 6],
  idle: [0],
}

const DIR_ROW: Record<string, number> = {
  down: 0, up: 1, right: 2, left: 2, // left = flipped right
}

// Office layout — desks arranged in a room
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
const ZOOM = 3 // 3x zoom = 48px per tile

interface CharState {
  name: string
  palette: number
  x: number  // pixel position (in tile-pixel space, not screen)
  y: number
  targetX: number
  targetY: number
  dir: string
  state: string
  frame: number
  frameTimer: number
  speech: string
  speechTimer: number
  task: string
  progress: number
  moving: boolean
}

export default function AgentMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [mapState, setMapState] = useState<MapState | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const charsRef = useRef<Record<string, CharState>>({})
  const charImgsRef = useRef<HTMLImageElement[]>([])
  const floorImgRef = useRef<HTMLImageElement | null>(null)
  const deskImgRef = useRef<HTMLImageElement | null>(null)
  const wallImgRef = useRef<HTMLImageElement | null>(null)
  const animRef = useRef<number>(0)
  const assetsLoadedRef = useRef(false)

  // Load sprite images
  useEffect(() => {
    if (assetsLoadedRef.current) return
    const imgs: HTMLImageElement[] = []
    let loaded = 0
    const total = 9 // 6 chars + floor + desk + wall

    const onAllLoaded = () => {
      loaded++
      if (loaded >= total) {
        assetsLoadedRef.current = true
      }
    }

    for (let i = 0; i < 6; i++) {
      const img = new Image()
      img.onload = onAllLoaded
      img.src = `/assets/characters/char_${i}.png`
      imgs.push(img)
    }
    charImgsRef.current = imgs

    const floor = new Image()
    floor.onload = onAllLoaded
    floor.src = '/assets/floors/floor_0.png'
    floorImgRef.current = floor

    const desk = new Image()
    desk.onload = onAllLoaded
    desk.src = '/assets/furniture/DESK/DESK_FRONT.png'
    deskImgRef.current = desk

    const wall = new Image()
    wall.onload = onAllLoaded
    wall.src = '/assets/walls/wall_0.png'
    wallImgRef.current = wall
  }, [])

  // Init characters at desk positions
  useEffect(() => {
    if (Object.keys(charsRef.current).length > 0) return
    const chars: Record<string, CharState> = {}
    for (const desk of DESKS) {
      const cfg = AGENT_CONFIG[desk.agent] || { palette: 0, label: desk.agent, emoji: '?' }
      chars[desk.agent] = {
        name: desk.agent,
        palette: cfg.palette,
        x: desk.col * TILE + TILE / 2,
        y: desk.row * TILE + TILE,
        targetX: desk.col * TILE + TILE / 2,
        targetY: desk.row * TILE + TILE,
        dir: 'down',
        state: 'idle',
        frame: 0,
        frameTimer: 0,
        speech: '',
        speechTimer: 0,
        task: '',
        progress: 0,
        moving: false,
      }
    }
    charsRef.current = chars
  }, [])

  // Update from API
  useEffect(() => {
    if (!mapState) return
    for (const [name, apiAgent] of Object.entries(mapState.agents || {})) {
      const char = charsRef.current[name]
      if (!char) continue
      const station = mapState.stations?.[apiAgent.station]
      if (station) {
        // Map station x,y (800x600 space) to tile space
        const targetCol = Math.round(station.x / (800 / COLS))
        const targetRow = Math.round(station.y / (600 / ROWS))
        const tx = targetCol * TILE + TILE / 2
        const ty = targetRow * TILE + TILE
        if (Math.abs(char.targetX - tx) > 2 || Math.abs(char.targetY - ty) > 2) {
          char.targetX = tx
          char.targetY = ty
          char.moving = true
          char.state = 'walk'
          const dx = tx - char.x
          const dy = ty - char.y
          char.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up')
        }
      }
      if (!char.moving) {
        char.state = apiAgent.status === 'working' ? 'type' : apiAgent.status === 'moving' ? 'walk' : 'idle'
      }
      if (apiAgent.speech && apiAgent.speech !== char.speech) {
        char.speech = apiAgent.speech
        char.speechTimer = 300
      }
      char.progress = apiAgent.progress || 0
      char.task = apiAgent.task || ''
    }
  }, [mapState])

  // Fetch map state
  const fetchState = useCallback(async () => {
    try { setMapState(await getMapState()) } catch {}
  }, [])
  useEffect(() => {
    fetchState()
    const i = setInterval(fetchState, 1000)
    return () => clearInterval(i)
  }, [fetchState])

  // Animation + render loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.imageSmoothingEnabled = false

    let lastTime = 0
    const ANIM_SPEED = 0.18

    const loop = (time: number) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1)
      lastTime = time

      const W = COLS * TILE
      const H = ROWS * TILE

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
        // Fallback: checker pattern
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) {
            ctx.fillStyle = (c + r) % 2 === 0 ? '#161b22' : '#111827'
            ctx.fillRect(c * TILE, r * TILE, TILE, TILE)
          }
        }
      }

      // Draw walls around the room (top + bottom + left + right)
      const wallImg = wallImgRef.current
      if (wallImg && wallImg.complete && wallImg.naturalWidth > 0) {
        // Top wall
        for (let c = 0; c < COLS; c++) {
          ctx.drawImage(wallImg, 0, 0, 16, 32, c * TILE, 0, TILE, 32)
        }
      } else {
        // Fallback wall
        ctx.fillStyle = '#1c2128'
        ctx.fillRect(0, 0, W, TILE)
        ctx.fillStyle = '#252b36'
        ctx.fillRect(0, 0, W, 2)
      }

      // Draw desks
      const deskImg = deskImgRef.current
      for (const desk of DESKS) {
        const dx = desk.col * TILE - 8
        const dy = desk.row * TILE - 16
        const cfg = AGENT_CONFIG[desk.agent]
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
        const color = colors[cfg?.palette || 0]

        if (deskImg && deskImg.complete && deskImg.naturalWidth > 0) {
          // Draw actual desk sprite (48x32, scaled to tile space)
          ctx.drawImage(deskImg, dx, dy, 48, 32)
        } else {
          // Fallback: colored rect
          ctx.fillStyle = color + '40'
          ctx.fillRect(dx, dy, 48, 32)
          ctx.strokeStyle = color
          ctx.lineWidth = 1
          ctx.strokeRect(dx, dy, 48, 32)
        }

        // Label
        ctx.fillStyle = color
        ctx.font = 'bold 7px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(desk.label, desk.col * TILE + 8, desk.row * TILE + 18)
      }

      // Update + draw characters (z-sorted by Y)
      const charList = Object.values(charsRef.current)
      charList.sort((a, b) => a.y - b.y)

      for (const char of charList) {
        // Movement
        if (char.moving) {
          const dx = char.targetX - char.x
          const dy = char.targetY - char.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 1) {
            char.x = char.targetX
            char.y = char.targetY
            char.moving = false
            char.state = 'idle'
          } else {
            const speed = 20 * dt
            char.x += (dx / dist) * speed
            char.y += (dy / dist) * speed
          }
        }

        // Animation
        char.frameTimer += dt
        if (char.frameTimer >= ANIM_SPEED) {
          char.frameTimer = 0
          const frames = STATE_FRAMES[char.state] || STATE_FRAMES.idle
          char.frame = (char.frame + 1) % frames.length
        }

        // Speech timer
        if (char.speechTimer > 0) {
          char.speechTimer--
          if (char.speechTimer === 0) char.speech = ''
        }

        // Draw character sprite
        const img = charImgsRef.current[char.palette]
        if (img && img.complete && img.naturalWidth > 0) {
          const frames = STATE_FRAMES[char.state] || STATE_FRAMES.idle
          const frameIdx = frames[char.frame % frames.length]
          const row = DIR_ROW[char.dir] ?? 0
          const srcX = frameIdx * 16
          const srcY = row * 32

          // Shadow
          ctx.fillStyle = 'rgba(0,0,0,0.3)'
          ctx.beginPath()
          ctx.ellipse(char.x, char.y, 6, 2, 0, 0, Math.PI * 2)
          ctx.fill()

          // Character sprite
          if (char.dir === 'left') {
            ctx.save()
            ctx.scale(-1, 1)
            ctx.drawImage(img, srcX, srcY, 16, 32,
              -(char.x - 8), char.y - 28, 16, 32)
            ctx.restore()
          } else {
            ctx.drawImage(img, srcX, srcY, 16, 32,
              char.x - 8, char.y - 28, 16, 32)
          }

          // Selection highlight
          if (selected === char.name) {
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 1
            ctx.setLineDash([2, 2])
            ctx.beginPath()
            ctx.arc(char.x, char.y - 12, 10, 0, Math.PI * 2)
            ctx.stroke()
            ctx.setLineDash([])
          }

          // Working ring
          if (char.state === 'type') {
            ctx.strokeStyle = '#10b981'
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.arc(char.x, char.y - 12, 9, 0, Math.PI * 2)
            ctx.stroke()
          }
        } else {
          // Fallback: colored dot
          const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
          ctx.fillStyle = colors[char.palette] || '#888'
          ctx.beginPath()
          ctx.arc(char.x, char.y - 12, 6, 0, Math.PI * 2)
          ctx.fill()
        }

        // Name label
        const cfg = AGENT_CONFIG[char.name]
        ctx.fillStyle = '#6b7280'
        ctx.font = 'bold 6px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(cfg?.label || char.name, char.x, char.y + 2)

        // Speech bubble
        if (char.speech) {
          const text = char.speech.length > 20 ? char.speech.slice(0, 17) + '...' : char.speech
          ctx.font = '6px monospace'
          const tw = ctx.measureText(text).width + 6
          const bx = char.x - tw / 2
          const by = char.y - 42
          ctx.fillStyle = '#1f2937'
          ctx.strokeStyle = '#3b82f6'
          ctx.lineWidth = 0.5
          ctx.fillRect(bx, by, tw, 10)
          ctx.strokeRect(bx, by, tw, 10)
          ctx.fillStyle = '#e5e7eb'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(text, char.x, by + 5)
        }

        // Progress bar
        if (char.progress > 0 && char.state === 'type') {
          ctx.fillStyle = '#1f2937'
          ctx.fillRect(char.x - 8, char.y + 10, 16, 1)
          ctx.fillStyle = '#10b981'
          ctx.fillRect(char.x - 8, char.y + 10, 16 * char.progress / 100, 1)
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
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    for (const [name, char] of Object.entries(charsRef.current)) {
      const dist = Math.sqrt((char.x - x) ** 2 + ((char.y - 12) - y) ** 2)
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
          {Object.entries(AGENT_CONFIG).map(([name, cfg]) => {
            const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
            return (
              <span key={name} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: colors[cfg.palette] }} />
                <span className="text-kaihara-muted">{cfg.label}</span>
              </span>
            )
          })}
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
      {selected && charsRef.current[selected] && (
        <div className="flex-shrink-0 px-4 py-2 border-t border-kaihara-border text-xs flex items-center gap-3">
          <span className="text-kaihara-accent font-bold">{AGENT_CONFIG[selected]?.label || selected}</span>
          <span className="text-kaihara-muted">— {charsRef.current[selected].state}</span>
          {charsRef.current[selected].task && (
            <span className="text-kaihara-muted truncate">— {charsRef.current[selected].task}</span>
          )}
        </div>
      )}
    </div>
  )
}
