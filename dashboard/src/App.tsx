import { useState, useEffect, useCallback, useRef } from 'react'
import KaiharaStatus from './components/KaiharaStatus'
import Conversation from './components/Conversation'
import AgentActivity from './components/AgentActivity'
import SystemStatus from './components/SystemStatus'
import MorningBriefing from './components/MorningBriefing'
import GoalsTracker from './components/GoalsTracker'
import NotificationPanel from './components/NotificationPanel'
import TaskBoard from './components/TaskBoard'
import SkillBrowser from './components/SkillBrowser'
import SecurityView from './components/SecurityView'
import ChannelStatus from './components/ChannelStatus'
import KernelStatus from './components/KernelStatus'
import MetaPanel from './components/MetaPanel'
import AgentMap from './components/AgentMap'
import ChatSessions from './components/ChatSessions'
import {
  getStatus, sendMessage, getMapState, getChatHistory,
  getConversations, newConversation, renameConversation, deleteConversation,
  type SystemStatus as Status, type Conversation as Conv,
} from './lib/api'

export type Msg = { role: 'user' | 'kaihara'; text: string; route?: string }

const ACTIVE_CONV_KEY = 'kaihara_active_conv'

export default function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [thinking, setThinking] = useState(false)
  const [agents, setAgents] = useState<{name: string; status: string; task: string; progress: number}[]>([])
  const [notifications, setNotifications] = useState<{type: string; text: string}[]>([])
  const [activeTab, setActiveTab] = useState<'chat' | 'map' | 'tasks' | 'skills' | 'security' | 'memory'>('chat')
  const [activeConvId, setActiveConvId] = useState<string>(
    () => localStorage.getItem(ACTIVE_CONV_KEY) || 'dashboard')
  const [conversations, setConversations] = useState<Conv[]>([])

  const failCountRef = useRef(0)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getStatus()
      failCountRef.current = 0
      setStatus(s)
      if (s.fleet_agents) {
        const mapData = await getMapState()
        const agentStatus = s.fleet_agents.map(name => {
          const mapAgent = mapData.agents[name]
          return { name, status: mapAgent?.status || 'idle', task: mapAgent?.task || '', progress: mapAgent?.progress || 0 }
        })
        setAgents(agentStatus)
      }
    } catch {
      // Keep last known status — only show OFFLINE after 4 consecutive failures (~1 min)
      failCountRef.current += 1
      if (failCountRef.current >= 4) setStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  // Load conversation list
  const fetchConversations = useCallback(async () => {
    try {
      const data = await getConversations()
      setConversations(data.conversations || [])
    } catch {}
  }, [])

  // Load chat history for active conversation: localStorage first, then server
  useEffect(() => {
    localStorage.setItem(ACTIVE_CONV_KEY, activeConvId)
    try {
      const cached = localStorage.getItem(`kaihara_chat_${activeConvId}`)
      if (cached) setMessages(JSON.parse(cached))
      else setMessages([])
    } catch { setMessages([]) }
    getChatHistory(activeConvId).then(({ messages }) => {
      if (messages && messages.length > 0) {
        const msgs = messages.map(m => ({
          role: m.role === 'assistant' ? 'kaihara' : 'user',
          text: m.text,
        })) as Msg[]
        setMessages(msgs)
      }
    }).catch(() => {})
    fetchConversations()
  }, [activeConvId, fetchConversations])

  // Persist to localStorage on every change
  useEffect(() => {
    try {
      localStorage.setItem(`kaihara_chat_${activeConvId}`, JSON.stringify(messages.slice(-200)))
    } catch {}
  }, [messages, activeConvId])

  const handleNewChat = async () => {
    try {
      const conv = await newConversation('New Chat')
      setActiveConvId(conv.conv_id)
      setMessages([])
      fetchConversations()
      setActiveTab('chat')
    } catch {
      // Offline fallback: temp local id
      setActiveConvId(`c_local_${Date.now()}`)
      setMessages([])
      setActiveTab('chat')
    }
  }

  const handleSelectConv = (convId: string) => {
    setActiveConvId(convId)
    setActiveTab('chat')
  }

  const handleRenameConv = async (convId: string) => {
    const title = prompt('Rename chat:')
    if (!title?.trim()) return
    await renameConversation(convId, title.trim())
    fetchConversations()
  }

  const handleDeleteConv = async (convId: string) => {
    if (!confirm('Delete this chat permanently?')) return
    await deleteConversation(convId)
    if (convId === activeConvId) {
      handleNewChat()
    } else {
      fetchConversations()
    }
  }

  const handleSend = async (text: string) => {
    setMessages(prev => [...prev, { role: 'user', text }])
    setThinking(true)
    try {
      const res = await sendMessage(text, 'dashboard', activeConvId)
      setMessages(prev => [...prev, { role: 'kaihara', text: res.response, route: res.route }])
      fetchConversations() // refresh order + message count + auto-title
    } catch {
      setMessages(prev => [...prev, { role: 'kaihara', text: '[Connection error. Is Kaihara server running on :7000?]' }])
    }
    setThinking(false)
  }

  return (
    // Root: full viewport, NO scroll on body
    <div className="h-screen flex flex-col bg-kaihara-bg text-kaihara-text overflow-hidden">
      {/* Header — fixed height */}
      <header className="flex-shrink-0 border-b border-kaihara-border px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-sm">K</div>
          <div>
            <h1 className="text-lg font-bold tracking-wide">KAIHARA OS</h1>
            <p className="text-xs text-kaihara-muted">Personal AI Super-Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {status?.kaihara_online ? (
            <span className="flex items-center gap-2 text-xs text-kaihara-success">
              <span className="status-dot bg-kaihara-success animate-pulse" />ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-2 text-xs text-kaihara-danger">
              <span className="status-dot bg-kaihara-danger" />OFFLINE
            </span>
          )}
        </div>
      </header>

      {/* Main — fills remaining height, NO page scroll */}
      <div className="flex-1 flex min-h-0">
        {/* Left Sidebar — scroll dalam diri sendiri */}
        <aside className="w-64 flex-shrink-0 border-r border-kaihara-border p-3 overflow-y-auto space-y-3">
          <ChatSessions
            conversations={conversations}
            activeConvId={activeConvId}
            onSelect={handleSelectConv}
            onNewChat={handleNewChat}
            onRename={handleRenameConv}
            onDelete={handleDeleteConv}
          />
          <KaiharaStatus thinking={thinking} online={!!status?.kaihara_online} />
          <ChannelStatus />
          <KernelStatus />
          <MetaPanel />
          <SystemStatus status={status} />
          <AgentActivity agents={agents} />
        </aside>

        {/* Center — flex-1, tab content manages own scroll */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Tabs — fixed height */}
          <div className="flex-shrink-0 flex border-b border-kaihara-border">
            {(['chat', 'map', 'tasks', 'skills', 'security', 'memory'] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-5 py-2.5 text-sm font-medium uppercase tracking-wide transition-colors ${
                  activeTab === tab ? 'text-kaihara-accent border-b-2 border-kaihara-accent' : 'text-kaihara-muted hover:text-kaihara-text'
                }`}>
                {tab}
              </button>
            ))}
          </div>

          {/* Tab content — fills remaining, each tab manages own scroll */}
          <div className="flex-1 min-h-0 flex flex-col">
            {activeTab === 'chat' && <Conversation messages={messages} thinking={thinking} onSend={handleSend} />}
            {activeTab === 'map' && <AgentMap />}
            {activeTab === 'tasks' && <TaskBoard />}
            {activeTab === 'skills' && <SkillBrowser />}
            {activeTab === 'security' && <SecurityView />}
            {activeTab === 'memory' && <MemoryView />}
          </div>
        </main>

        {/* Right Sidebar — scroll dalam diri sendiri */}
        <aside className="w-72 flex-shrink-0 border-l border-kaihara-border p-3 overflow-y-auto space-y-3">
          <MorningBriefing />
          <GoalsTracker />
          <NotificationPanel notifications={notifications} />
        </aside>
      </div>
    </div>
  )
}

function MemoryView() {
  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <h2 className="hud-title">Memory Tree</h2>
      <div className="hud-panel">
        <p className="text-kaihara-muted text-sm">Memory viewer — search and browse stored memories.</p>
        <p className="text-kaihara-muted text-xs mt-2">Use /api/memory/recall?q=your_query to search.</p>
      </div>
    </div>
  )
}
