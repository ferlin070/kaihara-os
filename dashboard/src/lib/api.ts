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
  provider?: string
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
  tier?: string
  raw_content?: string
  mermaid?: string
}

export interface MemoryStats {
  total_memories: number
  raw_count: number
  summary_count: number
  canvas_count: number
  topics: Record<string, number>
  daily_count: number
  goals_count: number
  vector_available: boolean
  vector_count: number
}

export async function getStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`)
  return res.json()
}

export async function sendMessage(message: string, source = 'dashboard', convId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, source, conv_id: convId || localStorage.getItem('kaihara_active_conv') || 'dashboard' }),
  })
  return res.json()
}

// ============================================================
// Conversation Management
// ============================================================

export interface Conversation {
  conv_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export async function getConversations(limit = 50): Promise<{ conversations: Conversation[] }> {
  const res = await fetch(`${API_BASE}/chat/conversations?limit=${limit}`)
  return res.json()
}

export async function newConversation(title = 'New Chat'): Promise<{ conv_id: string; title: string }> {
  const res = await fetch(`${API_BASE}/chat/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return res.json()
}

export async function renameConversation(convId: string, title: string): Promise<any> {
  const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return res.json()
}

export async function deleteConversation(convId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
    method: 'DELETE',
  })
  return res.json()
}

// ============================================================
// Persistent Chat History
// ============================================================

export interface HistoryMsg {
  role: string
  text: string
  timestamp?: string
}

export async function getChatHistory(convId = 'dashboard', limit = 100): Promise<{ messages: HistoryMsg[] }> {
  const res = await fetch(`${API_BASE}/chat/history?conv_id=${encodeURIComponent(convId)}&limit=${limit}`)
  return res.json()
}

export async function clearChatHistory(convId = 'dashboard'): Promise<any> {
  const res = await fetch(`${API_BASE}/chat/history?conv_id=${encodeURIComponent(convId)}`, {
    method: 'DELETE',
  })
  return res.json()
}

export async function recallMemory(q: string, limit = 5): Promise<{ results: MemoryResult[] }> {
  const res = await fetch(`${API_BASE}/memory/recall?q=${encodeURIComponent(q)}&limit=${limit}`)
  return res.json()
}

export async function getMemoryStats(): Promise<MemoryStats> {
  const res = await fetch(`${API_BASE}/memory/stats`)
  return res.json()
}

export async function getMemoryBrowse(topic?: string, limit = 50): Promise<{ results: MemoryResult[] }> {
  const params = new URLSearchParams()
  if (topic) params.set('topic', topic)
  params.set('limit', String(limit))
  const res = await fetch(`${API_BASE}/memory/browse?${params}`)
  return res.json()
}

export async function deleteMemory(summaryId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/memory/${summaryId}`, { method: 'DELETE' })
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
// Prompt Storage
// ============================================================

export interface Prompt {
  id: string
  name: string
  content: string
  category: string
  tags: string[]
  description: string
  uses: number
  created_at: string
}

export async function getPrompts(category?: string, q?: string): Promise<{ prompts: Prompt[] }> {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (q) params.set('q', q)
  const res = await fetch(`${API_BASE}/prompts?${params}`)
  return res.json()
}

export async function savePrompt(name: string, content: string, category = 'general', tags: string[] = [], description = ''): Promise<any> {
  const res = await fetch(`${API_BASE}/prompts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, content, category, tags, description }),
  })
  return res.json()
}

export async function deletePrompt(promptId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/prompts/${promptId}`, { method: 'DELETE' })
  return res.json()
}

export async function usePrompt(promptId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/prompts/${promptId}/use`, { method: 'POST' })
  return res.json()
}

// ============================================================
// Repo Skill Extraction
// ============================================================

export interface ExtractResult {
  repo: string
  found: number
  installed: number
  skills: { id: string; path: string; name: string }[]
  error?: string
}

export async function extractRepoSkills(repoUrl: string): Promise<ExtractResult> {
  const res = await fetch(`${API_BASE}/skills/extract-repo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
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
// Security Agent (real tool capabilities)
// ============================================================

export interface SecurityAgentStatus {
  agent_type: string
  tools: string[]
  sandbox_available: boolean
  audit_enabled: boolean
  approval_gate_enabled: boolean
  pentest_available: boolean
  soul_loaded: boolean
  skills: string[]
}

export async function getSecurityAgentStatus(): Promise<SecurityAgentStatus> {
  const res = await fetch(`${API_BASE}/security/agent/status`)
  return res.json()
}

export async function runSecurityAgent(task: string, context?: any): Promise<any> {
  const res = await fetch(`${API_BASE}/security/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, context }),
  })
  return res.json()
}

export async function securityDnsLookup(target: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/agent/dns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target }),
  })
  return res.json()
}

export async function securityPortScan(target: string, ports?: string, scan_type?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/agent/portscan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target, ports, scan_type }),
  })
  return res.json()
}

export async function securityVulnScan(target: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/agent/vulnscan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target }),
  })
  return res.json()
}

export async function securityFullRecon(target: string): Promise<any> {
  const res = await fetch(`${API_BASE}/security/agent/fullrecon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target }),
  })
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
// Notifications
// ============================================================

export interface NotificationStatus {
  quiet_hours: boolean
  rate_limit: { max_per_hour: number; sent_this_hour: number; remaining: number }
  routing: Record<string, string[]>
  history_count: number
  last_5: any[]
}

export async function getNotificationStatus(): Promise<NotificationStatus> {
  const res = await fetch(`${API_BASE}/notifications/status`)
  return res.json()
}

export async function sendNotification(message: string, priority = 'normal', title = '', channels?: string[]): Promise<any> {
  const res = await fetch(`${API_BASE}/notifications/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, priority, title, channels }),
  })
  return res.json()
}

export async function updateNotificationRouting(routing: Record<string, string[]>): Promise<any> {
  const res = await fetch(`${API_BASE}/notifications/routing`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ routing }),
  })
  return res.json()
}

// ============================================================
// Marketing System
// ============================================================

export interface Lead {
  id: number; name: string; email: string; phone: string; company: string
  source: string; status: string; score: number; notes: string; tags: string[]
  assigned_to: string | null; created_at: string; updated_at: string
}

export interface Client {
  id: number; lead_id: number | null; name: string; email: string; phone: string
  company: string; address: string; status: string; tier: string
  total_paid: number; total_invoiced: number; notes: string; tags: string[]
  whatsapp_verified: number; email_verified: number; created_at: string
}

export interface Campaign {
  id: number; name: string; description: string; type: string; status: string
  budget: number; spent: number; target_audience: string; channels: string[]
  start_date: string; end_date: string; metrics: Record<string, any>; created_at: string
}

export interface Content {
  id: number; campaign_id: number | null; title: string; body: string
  content_type: string; platform: string; status: string; scheduled_at: string
  published_at: string; hashtags: string[]; created_at: string
}

export interface Invoice {
  id: number; invoice_number: string; client_id: number; amount: number
  currency: string; status: string; description: string; items: any[]
  tax_rate: number; tax_amount: number; total: number; due_date: string
  paid_at: string | null; payment_method: string; created_at: string
}

// Leads
export async function getLeads(status?: string, q?: string): Promise<{ leads: Lead[] }> {
  const p = new URLSearchParams(); if (status) p.set('status', status); if (q) p.set('q', q)
  const res = await fetch(`${API_BASE}/marketing/leads?${p}`); return res.json()
}
export async function createLead(data: Partial<Lead>): Promise<Lead> {
  const res = await fetch(`${API_BASE}/marketing/leads`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function updateLead(id: number, data: Partial<Lead>): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/leads/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function deleteLead(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/leads/${id}`, { method: 'DELETE' }); return res.json()
}
export async function convertLead(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/leads/${id}/convert`, { method: 'POST' }); return res.json()
}
export async function scoreLead(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/leads/${id}/score`, { method: 'POST' }); return res.json()
}
export async function getLeadStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/leads/stats`); return res.json()
}

// Clients
export async function getClients(status?: string, tier?: string, q?: string): Promise<{ clients: Client[] }> {
  const p = new URLSearchParams(); if (status) p.set('status', status); if (tier) p.set('tier', tier); if (q) p.set('q', q)
  const res = await fetch(`${API_BASE}/marketing/clients?${p}`); return res.json()
}
export async function createClient(data: Partial<Client>): Promise<Client> {
  const res = await fetch(`${API_BASE}/marketing/clients`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function updateClient(id: number, data: Partial<Client>): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/clients/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function deleteClient(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/clients/${id}`, { method: 'DELETE' }); return res.json()
}
export async function getClientStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/clients/stats`); return res.json()
}
export async function approveClient(clientId: number, data: { type: string; ref_id?: number; message: string; channels?: string[] }): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/clients/${clientId}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}

// Approvals
export async function getApprovalsMarketing(): Promise<{ pending: any[] }> {
  const res = await fetch(`${API_BASE}/marketing/approvals`); return res.json()
}
export async function respondApproval(approvalId: number, data: { response: string; approved: boolean }): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/approvals/${approvalId}/respond`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}

// Campaigns
export async function getCampaigns(status?: string): Promise<{ campaigns: Campaign[] }> {
  const p = new URLSearchParams(); if (status) p.set('status', status)
  const res = await fetch(`${API_BASE}/marketing/campaigns?${p}`); return res.json()
}
export async function createCampaign(data: Partial<Campaign>): Promise<Campaign> {
  const res = await fetch(`${API_BASE}/marketing/campaigns`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function updateCampaign(id: number, data: Partial<Campaign>): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/campaigns/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function deleteCampaign(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/campaigns/${id}`, { method: 'DELETE' }); return res.json()
}

// Content
export async function getContent(status?: string, platform?: string): Promise<{ content: Content[] }> {
  const p = new URLSearchParams(); if (status) p.set('status', status); if (platform) p.set('platform', platform)
  const res = await fetch(`${API_BASE}/marketing/content?${p}`); return res.json()
}
export async function createContent(data: Partial<Content>): Promise<Content> {
  const res = await fetch(`${API_BASE}/marketing/content`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function updateContent(id: number, data: Partial<Content>): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/content/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function publishContent(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/content/${id}/publish`, { method: 'POST' }); return res.json()
}
export async function generateContent(data: { topic: string; platform?: string; content_type?: string; language?: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/content/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}

// SEO
export async function getSeoTracking(url?: string): Promise<{ tracking: any[] }> {
  const p = new URLSearchParams(); if (url) p.set('url', url)
  const res = await fetch(`${API_BASE}/marketing/seo?${p}`); return res.json()
}
export async function addSeoTracking(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/seo`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function seoAudit(url: string): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/seo/audit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) }); return res.json()
}
export async function keywordResearch(topic: string): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/seo/keywords`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic }) }); return res.json()
}
export async function competitorAnalysis(url: string): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/seo/competitor`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) }); return res.json()
}

// Invoices
export async function getInvoices(clientId?: number, status?: string): Promise<{ invoices: Invoice[] }> {
  const p = new URLSearchParams(); if (clientId) p.set('client_id', String(clientId)); if (status) p.set('status', status)
  const res = await fetch(`${API_BASE}/marketing/invoices?${p}`); return res.json()
}
export async function createInvoice(data: Partial<Invoice> & { client_id: number; amount: number }): Promise<Invoice> {
  const res = await fetch(`${API_BASE}/marketing/invoices`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function payInvoice(id: number, data: { method: string; ref?: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/invoices/${id}/pay`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); return res.json()
}
export async function deleteInvoice(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/invoices/${id}`, { method: 'DELETE' }); return res.json()
}

// Marketing Dashboard
export async function getMarketingDashboard(): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/dashboard`); return res.json()
}
export async function marketingChat(message: string): Promise<any> {
  const res = await fetch(`${API_BASE}/marketing/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) }); return res.json()
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
// Daemon Manager
// ============================================================

export interface DaemonAlert {
  agent: string
  type: string
  message: string
  severity: string
}

export interface ServiceInfo {
  name: string
  type: string
  running: boolean
  interval: number
  last_run: string | null
  run_count: number
  error: string | null
  restarts: number
}

export interface DaemonStatus {
  watchdog_running: boolean
  agents: { total: number; running: number; errored: number; stopped: number }
  process: { pid: number; cpu_percent: number; memory_mb: number; threads: number; uptime_seconds: number }
  services: ServiceInfo[]
  restart_history: any[]
  restart_counts: Record<string, number>
}

export async function getDaemonStatus(): Promise<DaemonStatus> {
  const res = await fetch(`${API_BASE}/daemon/status`)
  return res.json()
}

export async function getDaemonAlerts(): Promise<{ alerts: DaemonAlert[] }> {
  const res = await fetch(`${API_BASE}/daemon/alerts`)
  return res.json()
}

export async function getDaemonServices(): Promise<{ services: ServiceInfo[] }> {
  const res = await fetch(`${API_BASE}/daemon/services`)
  return res.json()
}

export async function startDaemonWatchdog(): Promise<any> {
  const res = await fetch(`${API_BASE}/daemon/watchdog/start`, { method: 'POST' })
  return res.json()
}

export async function stopDaemonWatchdog(): Promise<any> {
  const res = await fetch(`${API_BASE}/daemon/watchdog/stop`, { method: 'POST' })
  return res.json()
}

export async function restartDaemonAgent(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/daemon/restart/${name}`, { method: 'POST' })
  return res.json()
}

export async function restartAllDaemonAgents(): Promise<any> {
  const res = await fetch(`${API_BASE}/daemon/restart-all`, { method: 'POST' })
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
