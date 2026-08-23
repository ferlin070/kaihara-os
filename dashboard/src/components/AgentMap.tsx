import { useState, useEffect, useRef, useCallback } from 'react'
import { getMapState, type MapState } from '../lib/api'

// Character config — map agent names ke character palettes
const AGENT_CONFIG: Record<string, { palette: number; label: string; emoji: string }> = {
  kaihara:   { palette: 0, label: 'Kaihara', emoji: '🤖' },
  coding:    { palette: 1, label: 'Coder', emoji: '👨‍💻' },
  marketing: { palette: 2, label: 'Marketer', emoji: '📈' },
  security:  { palette: 3, label: 'Guard', emoji: '🛡️' },
  deploy:    { palette: 4, label: 'Deployer', emoji: '🚀' },
  research:  { palette: 5, label: 'Researcher', emoji: '🔍' },
  meta:      { palette: 0, label: 'Meta', emoji: '👁️' }, // reuse palette 0 with hue
}

// Tile size for the office grid
const TILE = 32

// Character sprite: 7 frames x 16px wide, 3 rows x 32px tall
const CHAR_W = 16
const CHAR_H = 32

// Animation states
const STATE_FRAMES: Record<string, number[]> = {
  walk: [0, 1, 2],
  type: [3, 4],
  read: [5, 6],
  idle: [0],
}

// Direction rows in sprite sheet
const DIR_ROW: Record<string, number> = {
  down: 0, up: 1, right: 2,
}

// Office layout — simple grid with desks
const OFFICE_LAYOUT = {
  cols: 20,
  rows: 11,
  // Desk positions (tile coordinates) — where agents sit
  desks: [
    { x: 4, y: 3, agent: 'kaihara', label: 'HQ' },
    { x: 4, y: 5, agent: 'coding', label: 'Code Desk' },
    { x: 4, y: 7, agent: 'marketing', label: 'Market' },
    { x: 10, y: 3, agent: 'security', label: 'Security' },
    { x: 10, y: 5, agent: 'deploy', label: 'Deploy' },
    { x: 10, y: 7, agent: 'research', label: 'Research' },
    { x: 15, y: 5, agent: 'meta', label: 'Meta' },
  ],
}

// Convert tile coords to pixel coords (center of tile)
function tileToPx(col: number, row: number) {
  return { x: col * TILE + TILE / 2, y: row * TILE + TILE / 2 }
}

// Convert pixel coords to tile coords
function pxToTile(x: number, y: number) {
  return { col: Math.floor(x / TILE), row: Math.floor(y / TILE) }
}

interface CharState {
  name: string
  palette: number
  x: number
  y: number
  targetX: number
  targetY: number
  dir: string
  state: string // idle, walk, type, read
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
  const imagesRef = useRef<HTMLImageElement[]>([])
  const animRef = useRef<number>(0)

  const fetchState = useCallback(async () => {
    try { setMapState(await getMapState()) } catch {}
  }, [])

  useEffect(() => {
    fetchState()
    const i = setInterval(fetchState, 1000)
    return () => clearInterval(i)
  }, [fetchState])

  // Load character sprite images
  useEffect(() => {
    const images: HTMLImageElement[] = []
    for (let i = 0; i < 6; i++) {
      const img = new Image()
      img.src = `/assets/characters/char_${i}.png`
      images.push(img)
    }
    imagesRef.current = images
  }, [])

  // Initialize character states from desk positions
  useEffect(() => {
    if (Object.keys(charsRef.current).length === 0) {
      const chars: Record<string, CharState> = {}
      for (const desk of OFFICE_LAYOUT.desks) {
        const px = tileToPx(desk.x, desk.y)
        const config = AGENT_CONFIG[desk.agent] || { palette: 0, label: desk.agent, emoji: '?' }
        chars[desk.agent] = {
          name: desk.agent,
          palette: config.palette,
          x: px.x,
          y: px.y,
          targetX: px.x,
          targetY: px.y,
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
    }
  }, [])

  // Update character states from map API data
  useEffect(() => {
    if (!mapState) return
    for (const [name, apiAgent] of Object.entries(mapState.agents || {})) {
      const char = charsRef.current[name]
      if (!char) continue

      // Update target position if agent moved to a station
      const station = mapState.stations?.[apiAgent.station]
      if (station) {
        const targetPx = { x: station.x, y: station.y }
        if (Math.abs(char.targetX - targetPx.x) > 5 || Math.abs(char.targetY - targetPx.y) > 5) {
          char.targetX = targetPx.x
          char.targetY = targetPx.y
          char.moving = true
          char.state = 'walk'
          // Determine direction
          const dx = targetPx.x - char.x
          const dy = targetPx.y - char.y
          if (Math.abs(dx) > Math.abs(dy)) {
            char.dir = dx > 0 ? 'right' : 'right' // left = flipped right
          } else {
            char.dir = dy > 0 ? 'down' : 'up'
          }
        }
      }

      // Update status
      if (!char.moving) {
        if (apiAgent.status === 'working') {
          char.state = 'type'
        } else if (apiAgent.status === 'moving') {
          char.state = 'walk'
        } else {
          char.state = 'idle'
        }
      }

      // Speech bubble
      if (apiAgent.speech && apiAgent.speech !== char.speech) {
        char.speech = apiAgent.speech
        char.speechTimer = 300 // ~5 seconds at 60fps
      }

      // Progress
      char.progress = apiAgent.progress || 0
      char.task = apiAgent.task || ''
    }
  }, [mapState])

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let lastTime = 0
    const ANIM_SPEED = 0.15 // seconds per frame

    const loop = (time: number) => {
      const dt = (time - lastTime) / 1000
      lastTime = time

      const W = canvas.width
      const H = canvas.height

      // Clear with floor color
      ctx.fillStyle = '#0d1117'
      ctx.fillRect(0, 0, W, H)

      // Draw floor tiles
      for (let r = 0; r < OFFICE_LAYOUT.rows; r++) {
        for (let c = 0; c < OFFICE_LAYOUT.cols; c++) {
          const x = c * TILE
          const y = r * TILE
          // Checker pattern
          if ((c + r) % 2 === 0) {
            ctx.fillStyle = '#111827'
          } else {
            ctx.fillStyle = '#0f1420'
          }
          ctx.fillRect(x, y, TILE, TILE)
        }
      }

      // Draw grid lines (subtle)
      ctx.strokeStyle = '#1a2030'
      ctx.lineWidth = 0.5
      for (let c = 0; c <= OFFICE_LAYOUT.cols; c++) {
        ctx.beginPath()
        ctx.moveTo(c * TILE, 0)
        ctx.lineTo(c * TILE, OFFICE_LAYOUT.rows * TILE)
        ctx.stroke()
      }
      for (let r = 0; r <= OFFICE_LAYOUT.rows; r++) {
        ctx.beginPath()
        ctx.moveTo(0, r * TILE)
        ctx.lineTo(OFFICE_LAYOUT.cols * TILE, r * TILE)
        ctx.stroke()
      }

      // Draw desks (furniture)
      for (const desk of OFFICE_LAYOUT.desks) {
        const x = desk.x * TILE
        const y = desk.y * TILE
        // Desk shadow
        ctx.fillStyle = 'rgba(0,0,0,0.3)'
        ctx.fillRect(x - 14, y - 10, 28, 20)
        // Desk body
        const config = AGENT_CONFIG[desk.agent]
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
        const color = colors[config?.palette || 0]
        ctx.fillStyle = color + '20'
        ctx.fillRect(x - 16, y - 12, 32, 24)
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        ctx.strokeRect(x - 16, y - 12, 32, 24)
        // Desk label
        ctx.fillStyle = color
        ctx.font = 'bold 8px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillText(desk.label, x, y + 14)
      }

      // Draw paths between desks (walkway)
      ctx.strokeStyle = '#1a2030'
      ctx.lineWidth = 16
      ctx.lineCap = 'round'
      ctx.beginPath()
      ctx.moveTo(4 * TILE, 3 * TILE)
      ctx.lineTo(15 * TILE, 5 * TILE)
      ctx.stroke()

      // Update + draw characters
      const charList = Object.values(charsRef.current)
      // Sort by Y for depth
      charList.sort((a, b) => a.y - b.y)

      for (const char of charList) {
        // Movement
        if (char.moving) {
          const dx = char.targetX - char.x
          const dy = char.targetY - char.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 3) {
            char.x = char.targetX
            char.y = char.targetY
            char.moving = false
            char.state = mapState?.agents?.[char.name]?.status === 'working' ? 'type' : 'idle'
          } else {
            const speed = 60 * dt // pixels per second
            char.x += (dx / dist) * speed
            char.y += (dy / dist) * speed
          }
        }

        // Animation frame
        char.frameTimer += dt
        if (char.frameTimer >= ANIM_SPEED) {
          char.frameTimer = 0
          const frames = STATE_FRAMES[char.state] || STATE_FRAMES.idle
          char.frame = (char.frame + 1) % frames.length
        }

        // Speech timer
        if (char.speechTimer > 0) {
          char.speechTimer--
          if (char.speechTimer === 0) {
            char.speech = ''
          }
        }

        // Draw character sprite
        const img = imagesRef.current[char.palette]
        if (img && img.complete && img.naturalWidth > 0) {
          const frames = STATE_FRAMES[char.state] || STATE_FRAMES.idle
          const frameIdx = frames[char.frame % frames.length]
          const row = DIR_ROW[char.dir] ?? 0

          const srcX = frameIdx * CHAR_W
          const srcY = row * CHAR_H

          // Draw shadow
          ctx.fillStyle = 'rgba(0,0,0,0.3)'
          ctx.beginPath()
          ctx.ellipse(char.x, char.y + 10, 8, 3, 0, 0, Math.PI * 2)
          ctx.fill()

          // Draw character (2x scale)
          const scale = 2
          const drawW = CHAR_W * scale
          const drawH = CHAR_H * scale
          const drawX = char.x - drawW / 2
          const drawY = char.y - drawH / 2

          // Flip for left direction
          if (char.dir === 'left') {
            ctx.save()
            ctx.scale(-1, 1)
            ctx.drawImage(img,
              srcX, srcY, CHAR_W, CHAR_H,
              -drawX - drawW, drawY, drawW, drawH
            )
            ctx.restore()
          } else {
            ctx.drawImage(img,
              srcX, srcY, CHAR_W, CHAR_H,
              drawX, drawY, drawW, drawH
            )
          }

          // Selection highlight
          if (selected === char.name) {
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 2
            ctx.setLineDash([3, 3])
            ctx.beginPath()
            ctx.arc(char.x, char.y, 18, 0, Math.PI * 2)
            ctx.stroke()
            ctx.setLineDash([])
          }

          // Status ring
          if (char.state === 'type') {
            ctx.strokeStyle = '#10b981'
            ctx.lineWidth = 1.5
            ctx.beginPath()
            ctx.arc(char.x, char.y, 16, 0, Math.PI * 2)
            ctx.stroke()
          }
        } else {
          // Fallback: draw colored circle
          const config = AGENT_CONFIG[char.name]
          const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
          ctx.fillStyle = colors[config?.palette || 0]
          ctx.beginPath()
          ctx.arc(char.x, char.y, 10, 0, Math.PI * 2)
          ctx.fill()
        }

        // Name label
        ctx.fillStyle = '#6b7280'
        ctx.font = 'bold 9px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        const config = AGENT_CONFIG[char.name]
        ctx.fillText(config?.label || char.name, char.x, char.y + 14)

        // Speech bubble
        if (char.speech) {
          const text = char.speech.length > 25 ? char.speech.slice(0, 22) + '...' : char.speech
          ctx.font = '10px monospace'
          const tw = ctx.measureText(text).width + 12
          const bx = char.x - tw / 2
          const by = char.y - 30
          ctx.fillStyle = '#1f2937'
          ctx.strokeStyle = '#3b82f6'
          ctx.lineWidth = 1
          // Rounded rect
          ctx.beginPath()
          ctx.moveTo(bx + 4, by)
          ctx.arcTo(bx + tw, by, bx + tw, by + 18, 4)
          ctx.arcTo(bx + tw, by + 18, bx, by + 18, 4)
          ctx.arcTo(bx, by + 18, bx, by, 4)
          ctx.arcTo(bx, by, bx + tw, by, 4)
          ctx.fill()
          ctx.stroke()
          // Tail
          ctx.beginPath()
          ctx.moveTo(char.x - 3, by + 18)
          ctx.lineTo(char.x, by + 22)
          ctx.lineTo(char.x + 3, by + 18)
          ctx.fillStyle = '#1f2937'
          ctx.fill()
          // Text
          ctx.fillStyle = '#e5e7eb'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(text, char.x, by + 9)
        }

        // Progress bar
        if (char.progress > 0 && char.state === 'type') {
          ctx.fillStyle = '#1f2937'
          ctx.fillRect(char.x - 12, char.y + 20, 24, 2)
          ctx.fillStyle = '#10b981'
          ctx.fillRect(char.x - 12, char.y + 20, 24 * char.progress / 100, 2)
        }
      }

      // Title
      ctx.fillStyle = '#374151'
      ctx.font = '9px monospace'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      ctx.fillText('KAIHARA OFFICE — Pixel Agents', 4, 2)

      animRef.current = requestAnimationFrame(loop)
    }

    animRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animRef.current)
  }, [mapState, selected])

  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvas.width / rect.width)
    const y = (e.clientY - rect.top) * (canvas.height / rect.height)
    for (const [name, char] of Object.entries(charsRef.current)) {
      const dist = Math.sqrt((char.x - x) ** 2 + (char.y - y) ** 2)
      if (dist < 16) {
        setSelected(selected === name ? null : name)
        return
      }
    }
    setSelected(null)
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="flex-shrink-0 px-4 py-2 border-b border-kaihara-border flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide">Pixel Office</h2>
        <div className="flex items-center gap-3 text-xs">
          {Object.entries(AGENT_CONFIG).map(([name, cfg]) => (
            <span key={name} className="flex items-center gap-1">
              <span>{cfg.emoji}</span>
              <span className="text-kaihara-muted">{cfg.label}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center overflow-hidden p-4">
        <canvas
          ref={canvasRef}
          width={OFFICE_LAYOUT.cols * TILE}
          height={OFFICE_LAYOUT.rows * TILE}
          onClick={handleClick}
          className="border border-kaihara-border rounded-lg cursor-pointer"
          style={{ imageRendering: 'pixelated', maxWidth: '100%', maxHeight: '100%' }}
        />
      </div>
      {selected && charsRef.current[selected] && (
        <div className="flex-shrink-0 px-4 py-2 border-t border-kaihara-border text-xs flex items-center gap-3">
          <span className="text-lg">{AGENT_CONFIG[selected]?.emoji}</span>
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
