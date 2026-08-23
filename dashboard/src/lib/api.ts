import React from 'react'

// Determine API base URL based on environment
const getApiBase = () => {
  // If we're on the dashboard domain, use the API domain
  if (window.location.hostname === 'kaihara-ai.nakhodacloud.top') {
    return 'https://kaihara-api.nakhodacloud.top/api'
  }
  // Otherwise use relative path (for local development)
  return '/api'
}

const API_BASE = getApiBase()

export interface ChatResponse {
  response: string
  route: string
  intent: { text: string; type: string; agents: string[]; is_workflow: boolean }
  source: string
}

export interface SystemStatus {
  kaihara_online: boolean
  model: string[]
  fleet_agents: string[]
  memory: boolean
  token_juice: boolean
}

export interface Goal {
  id: string
  title: string
  description: string
  status: string
  priority: string
  created_at: string
  updated_at: string
}

export interface MemoryResult {
  summary_id: string
  content: string
  topic: string
  tags: string[]
  score: number
}

export async function getStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`)
  return res.json()
}

export async function sendMessage(message: string, source = 'dashboard'): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, source }),
  })
  return res.json()
}

export async function recallMemory(q: string, limit = 5): Promise<{ results: MemoryResult[] }> {
  const res = await fetch(`${API_BASE}/memory/recall?q=${encodeURIComponent(q)}&limit=${limit}`)
  return res.json()
}

export async function getGoals(): Promise<{ goals: Goal[] }> {
  const res = await fetch(`${API_BASE}/goals`)
  return res.json()
}

export async function addGoal(title: string, description = '', priority = 'medium'): Promise<{ goal_id: string }> {
  const res = await fetch(`${API_BASE}/goals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description, priority }),
  })
  return res.json()
}

export function useWebSocket(onMessage: (data: any) => void) {
  const wsRef = React.useRef<WebSocket | null>(null)
  const [connected, setConnected] = React.useState(false)

  React.useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname === 'kaihara-ai.nakhodacloud.top' 
      ? 'kaihara-api.nakhodacloud.top' 
      : window.location.hostname
    const port = window.location.hostname === 'kaihara-ai.nakhodacloud.top' ? '' : ':7000'
    const ws = new WebSocket(`${protocol}//${host}${port}/ws`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        onMessage(data)
      } catch {}
    }

    return () => ws.close()
  }, [])

  const send = (msg: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: msg, source: 'dashboard' }))
    }
  }

  return { send, connected }
}

// ============================================================
// Planning Pipeline
// ============================================================

export interface Task {
  id: string
  title: string
  phase: string
  status: string
  dependencies: string[]
  complexity: string
  assigned_agent?: string
  prd_id?: string
}

export interface Progress {
  total: number
  done: number
  doing: number
  todo: number
  blocked: number
  phases: Record<string, { total: number; done: number; doing: number }>
  percent: number
}

export async function plan(idea: string, context = ''): Promise<any> {
  const res = await fetch(`${API_BASE}/planning/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idea, context }),
  })
  return res.json()
}

export async function getTasks(prdId?: string): Promise<{ tasks: Task[] }> {
  const params = prdId ? `?prd_id=${prdId}` : ''
  const res = await fetch(`${API_BASE}/planning/tasks${params}`)
  return res.json()
}

export async function getProgress(prdId?: string): Promise<Progress> {
  const params = prdId ? `?prd_id=${prdId}` : ''
  const res = await fetch(`${API_BASE}/planning/progress${params}`)
  return res.json()
}

export async function updateTaskStatus(taskId: string, status: string): Promise<any> {
  const res = await fetch(`${API_BASE}/planning/tasks/${taskId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
  return res.json()
}

// ============================================================
// Skills
// ============================================================

export interface Skill {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  source: string
  version: string
}

export async function getSkills(category?: string, q?: string): Promise<{ skills: Skill[] }> {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (q) params.set('q', q)
  const res = await fetch(`${API_BASE}/skills?${params}`)
  return res.json()
}

export async function getSkillStats(): Promise<{ total: number; categories: Record<string, number> }> {
  const res = await fetch(`${API_BASE}/skills/stats`)
  return res.json()
}

export async function createSkill(description: string): Promise<any> {
  const res = await fetch(`${API_BASE}/skills/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  })
  return res.json()
}

// ============================================================
// Voice
// ============================================================

export interface VoiceStatus {
  enabled: boolean
  wake_word: string
  listening: boolean
  stt: { engine: string; model: string; available: boolean }
  tts: { engine: string; voice: string; available: boolean }
  wake: { wake_word: string; engine: string; available: boolean }
  available: boolean
}

export async function getVoiceStatus(): Promise<VoiceStatus> {
  const res = await fetch(`${API_BASE}/voice/status`)
  return res.json()
}

export async function startVoice(): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/start`, { method: 'POST' })
  return res.json()
}

export async function stopVoice(): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/stop`, { method: 'POST' })
  return res.json()
}

export async function speak(text: string, voice?: string): Promise<void> {
  // Get audio from server (Edge Neural TTS — fluent Bahasa Malaysia)
  const base = getApiBase()
  const res = await fetch(`${base.replace('/api', '')}/api/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice }),
  })
  if (!res.ok) throw new Error('TTS failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  return new Promise((resolve, reject) => {
    const audio = new Audio(url)
    audio.onended = () => {
      URL.revokeObjectURL(url)
      resolve()
    }
    audio.onerror = reject
    audio.play()
  })
}

// ============================================================
// Security & Pentest
// ============================================================

export interface SecurityStatus {
  approval_gate: any
  sandbox: any
  audit: any
  pentest: any
}

export interface Approval {
  id: string
  action: string
  agent: string
  details: any
  status: string
  created_at: string
}

export interface AuditEntry {
  timestamp: string
  agent: string
  action: string
  details: any
  result: any
  severity: string
}

export async function getSecurityStatus(): Promise<SecurityStatus> {
  const res = await fetch(`${API_BASE}/security/status`)
  return res.json()
}

export async function getApprovals(): Promise<{ pending: Approval[]; history: Approval[] }> {
  const res = await fetch(`${API_BASE}/security/approvals`)
  return res.json()
}

export async function approveAction(requestId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/approvals/${requestId}/approve`, { method: 'POST' })
  return res.json()
}

export async function denyAction(requestId: string, reason?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/approvals/${requestId}/deny`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  return res.json()
}

export async function getAuditLog(limit = 50): Promise<{ entries: AuditEntry[] }> {
  const res = await fetch(`${API_BASE}/security/audit?limit=${limit}`)
  return res.json()
}

export async function runPentest(target: string, approved = false): Promise<any> {
  const res = await fetch(`${API_BASE}/pentest/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target, approved }),
  })
  return res.json()
}

export async function getPentestSessions(): Promise<{ sessions: any[] }> {
  const res = await fetch(`${API_BASE}/pentest/sessions`)
  return res.json()
}

// ============================================================
// Channels
// ============================================================

export interface ChannelStatus {
  type: string
  enabled: boolean
  running: boolean
  [key: string]: any
}

export async function getChannelsStatus(): Promise<Record<string, ChannelStatus>> {
  const res = await fetch(`${API_BASE}/channels`)
  return res.json()
}

export async function startAllChannels(): Promise<any> {
  const res = await fetch(`${API_BASE}/channels/start`, { method: 'POST' })
  return res.json()
}

export async function stopAllChannels(): Promise<any> {
  const res = await fetch(`${API_BASE}/channels/stop`, { method: 'POST' })
  return res.json()
}

export async function startChannel(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/channels/${name}/start`, { method: 'POST' })
  return res.json()
}

export async function stopChannel(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/channels/${name}/stop`, { method: 'POST' })
  return res.json()
}

// ============================================================
// OS Kernel
// ============================================================

export interface OSAgentStatus {
  agent: string
  running: boolean
  interval: number
  last_run: string | null
  run_count: number
  error: string | null
  [key: string]: any
}

export async function getKernelStatus(): Promise<Record<string, OSAgentStatus>> {
  const res = await fetch(`${API_BASE}/kernel/status`)
  return res.json()
}

export async function startAllKernel(): Promise<any> {
  const res = await fetch(`${API_BASE}/kernel/start`, { method: 'POST' })
  return res.json()
}

export async function stopAllKernel(): Promise<any> {
  const res = await fetch(`${API_BASE}/kernel/stop`, { method: 'POST' })
  return res.json()
}

export async function startKernelAgent(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/kernel/${name}/start`, { method: 'POST' })
  return res.json()
}

export async function stopKernelAgent(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/kernel/${name}/stop`, { method: 'POST' })
  return res.json()
}

export async function runKernelOnce(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/kernel/${name}/run`, { method: 'POST' })
  return res.json()
}

// ============================================================
// Meta Agent
// ============================================================

export interface MetaSuggestion {
  type: string
  agent: string
  issue: string
  suggestion: string
  severity: string
  [key: string]: any
}

export interface MetaPattern {
  id: string
  pattern_type: string
  agent: string
  description: string
  frequency: number
  severity: string
  suggestion: string
}

export interface MetaStats {
  agent_stats: any[]
  cache_stats: { cached_tasks: number; cache_hits: number; tokens_saved: number }
}

export async function getMetaStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/meta/status`)
  return res.json()
}

export async function getMetaSuggestions(): Promise<{ suggestions: MetaSuggestion[] }> {
  const res = await fetch(`${API_BASE}/meta/suggestions`)
  return res.json()
}

export async function getMetaPatterns(): Promise<{ patterns: MetaPattern[] }> {
  const res = await fetch(`${API_BASE}/meta/patterns`)
  return res.json()
}

export async function getMetaStats(): Promise<MetaStats> {
  const res = await fetch(`${API_BASE}/meta/stats`)
  return res.json()
}

export async function analyzeFleet(): Promise<any> {
  const res = await fetch(`${API_BASE}/meta/analyze`, { method: 'POST' })
  return res.json()
}

// ============================================================
// Visualization (ai-town style)
// ============================================================

export interface MapAgent {
  name: string
  x: number
  y: number
  target_x: number
  target_y: number
  station: string
  status: string
  task: string
  speech: string
  color: string
  moving: boolean
  progress: number
}

export interface MapStation {
  x: number
  y: number
  w?: number
  h?: number
  label: string
  icon: string
  type?: string
  color: string
}

export interface MapState {
  agents: Record<string, MapAgent>
  stations: Record<string, MapStation>
  events: any[]
  interactions: any[]
}

export async function getMapState(): Promise<MapState> {
  const res = await fetch(`${API_BASE}/viz/map`)
  return res.json()
}

export async function moveAgentOnMap(agent: string, station: string, task?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/viz/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent, station, task }),
  })
  return res.json()
}

export async function setAgentSpeech(agent: string, text: string): Promise<any> {
  const res = await fetch(`${API_BASE}/viz/speech`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent, text }),
  })
  return res.json()
}

export async function resetMap(): Promise<any> {
  const res = await fetch(`${API_BASE}/viz/reset`, { method: 'POST' })
  return res.json()
}
