import { useState, useEffect, useCallback, useRef } from 'react'
import { ThemeProvider, useTheme } from './lib/ThemeContext'
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
import DaemonView from './components/DaemonView'
import PendingApprovals from './components/PendingApprovals'
import MarketingDashboard from './components/MarketingDashboard'
import SystemStatsWidget from './components/SystemStatsWidget'
import DeployView from './components/DeployView'
import EditorView from './components/EditorView'
import WorkflowDashboard from './components/WorkflowDashboard'
import KernelStatus from './components/KernelStatus'
import MetaPanel from './components/MetaPanel'
import AgentMap from './components/AgentMap'
import ChatSessions from './components/ChatSessions'
import MemoryTree from './components/MemoryTree'
import {
  getStatus, sendMessage, getMapState, getChatHistory,
  getConversations, newConversation, renameConversation, deleteConversation,
  type SystemStatus as Status, type Conversation as Conv,
} from './lib/api'

export type Msg = { role: 'user' | 'kaihara'; text: string; route?: string; provider?: string }

const ACTIVE_CONV_KEY = 'kaihara_active_conv'

const TABS = [
  { id: 'chat' as const, label: 'Chat', icon: '💬' },
  { id: 'map' as const, label: 'Map', icon: '🗺️' },
  { id: 'tasks' as const, label: 'Tasks', icon: '📋' },
  { id: 'skills' as const, label: 'Skills', icon: '⚡' },
  { id: 'security' as const, label: 'Security', icon: '🔒' },
  { id: 'memory' as const, label: 'Memory', icon: '🧠' },
  { id: 'daemon' as const, label: 'Daemon', icon: '⚙️' },
  { id: 'marketing' as const, label: 'Marketing', icon: '📈' },
  { id: 'deploy' as const, label: 'Deploy', icon: '🚀' },
  { id: 'editor' as const, label: 'Editor', icon: '✏️' },
  { id: 'workflows' as const, label: 'Workflows', icon: '🔄' },
]

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg hover:bg-kaihara-hover transition-colors text-kaihara-muted hover:text-kaihara-text"
      title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}

function AppContent() {
  const [status, setStatus] = useState<Status | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [thinking, setThinking] = useState(false)
  const [agents, setAgents] = useState<{name: string; status: string; task: string; progress: number}[]>([])
  const [notifications, setNotifications] = useState<{type: string; text: string}[]>([])
  const [activeTab, setActiveTab] = useState<typeof TABS[number]['id']>('chat')
  const [activeConvId, setActiveConvId] = useState<string>(
    () => localStorage.getItem(ACTIVE_CONV_KEY) || 'dashboard')
  const [conversations, setConversations] = useState<Conv[]>([])

  const failCountRef = useRef(0)

  const fetchStatus = useCallback(async () => {
    try {
      const [s, mapData] = await Promise.all([
        getStatus(),
        getMapState().catch(() => ({ agents: {} })),
      ])
      failCountRef.current = 0
      setStatus(s)
      if (s.fleet_agents) {
        const agentStatus = s.fleet_agents.map(name => {
          const mapAgent = (mapData.agents as Record<string, any>)?.[name]
          return { name, status: mapAgent?.status || 'idle', task: mapAgent?.task || '', progress: mapAgent?.progress || 0 }
        })
        setAgents(agentStatus)
      }
    } catch {
      failCountRef.current += 1
      if (failCountRef.current >= 4) setStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const fetchConversations = useCallback(async () => {
    try {
      const data = await getConversations()
      setConversations(data.conversations || [])
    } catch {}
  }, [])

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
      setMessages(prev => [...prev, { role: 'kaihara', text: res.response, route: res.route, provider: (res as any).provider }])
      fetchConversations()
    } catch {
      setMessages(prev => [...prev, { role: 'kaihara', text: '[Connection error. Is Kaihara server running on :7000?]' }])
    }
    setThinking(false)
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-kaihara-bg text-kaihara-text">
      {/* Left Sidebar — fixed width, no shrink */}
      <aside className="w-64 flex-shrink-0 h-full flex flex-col border-r border-kaihara-border overflow-hidden">
        {/* Logo */}
        <div className="h-14 flex items-center gap-3 px-4 border-b border-kaihara-border flex-shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            K
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-bold tracking-tight truncate">KAIHARA</h1>
            <p className="text-[10px] text-kaihara-muted truncate">AI Super-Intelligence</p>
          </div>
        </div>

        {/* Chat Sessions — scroll */}
        <div className="overflow-y-auto p-3 min-h-0 flex-shrink-0">
          <ChatSessions
            conversations={conversations}
            activeConvId={activeConvId}
            onSelect={handleSelectConv}
            onNewChat={handleNewChat}
            onRename={handleRenameConv}
            onDelete={handleDeleteConv}
          />
        </div>

        {/* Status — fills remaining space, scroll */}
        <div className="flex-1 border-t border-kaihara-border overflow-y-auto min-h-0">
          <div className="p-3 space-y-2">
            <KaiharaStatus thinking={thinking} online={!!status?.kaihara_online} />
            <SystemStatsWidget />
            <KernelStatus />
            <MetaPanel />
          </div>
        </div>
      </aside>

      {/* Center — flex-1, no shrink, column */}
      <div className="flex-1 min-w-0 h-full flex flex-col">
        {/* Top Bar */}
        <header className="h-12 flex items-center justify-between px-5 border-b border-kaihara-border flex-shrink-0">
          <div className="flex items-center gap-3">
            {status?.kaihara_online ? (
              <span className="badge-success">
                <span className="status-dot bg-kaihara-success animate-pulse mr-1.5" />
                Online
              </span>
            ) : (
              <span className="badge-danger">
                <span className="status-dot bg-kaihara-danger mr-1.5" />
                Offline
              </span>
            )}
          </div>
          <ThemeToggle />
        </header>

        {/* Tabs */}
        <div className="flex-shrink-0 border-b border-kaihara-border overflow-x-auto">
          <div className="flex px-3">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? 'text-kaihara-primary border-kaihara-primary'
                    : 'text-kaihara-muted border-transparent hover:text-kaihara-text'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content — flex-1, overflow hidden */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {activeTab === 'chat' && <Conversation messages={messages} thinking={thinking} onSend={handleSend} />}
          {activeTab === 'map' && <AgentMap />}
          {activeTab === 'tasks' && <TaskBoard />}
          {activeTab === 'skills' && <SkillBrowser />}
          {activeTab === 'security' && <SecurityView />}
          {activeTab === 'memory' && <MemoryTree />}
          {activeTab === 'daemon' && <DaemonView />}
          {activeTab === 'marketing' && <MarketingDashboard />}
          {activeTab === 'deploy' && <DeployView />}
          {activeTab === 'editor' && <EditorView />}
          {activeTab === 'workflows' && <WorkflowDashboard />}
        </div>
      </div>

      {/* Right Sidebar — fixed width, no shrink, scroll */}
      <aside className="w-72 flex-shrink-0 h-full border-l border-kaihara-border overflow-y-auto">
        <div className="p-3 space-y-3">
          <MorningBriefing />
          <PendingApprovals />
          <GoalsTracker />
          <NotificationPanel notifications={notifications} />
          <AgentActivity agents={agents} />
          <SystemStatus status={status} />
        </div>
      </aside>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  )
}
