import { useState, useEffect, useCallback, useRef } from 'react'
import { ThemeProvider, useTheme } from './lib/ThemeContext'
import Conversation from './components/Conversation'
import TaskBoard from './components/TaskBoard'
import SecurityView from './components/SecurityView'
import MemoryTree from './components/MemoryTree'
import {
  getStatus, sendMessage, getChatHistory,
  getConversations, newConversation, renameConversation, deleteConversation,
  type SystemStatus as Status, type Conversation as Conv,
} from './lib/api'

export type Msg = { role: 'user' | 'kaihara'; text: string; route?: string; provider?: string; images?: Array<{url: string; source?: string}> }

const ACTIVE_CONV_KEY = 'kaihara_active_conv'

const TABS = [
  { id: 'chat' as const, label: 'Chat', icon: '💬' },
  { id: 'tasks' as const, label: 'Tasks', icon: '📋' },
  { id: 'security' as const, label: 'Security', icon: '🔒' },
  { id: 'memory' as const, label: 'Memory', icon: '🧠' },
]

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg hover:bg-white/10 transition-colors text-kaihara-muted hover:text-kaihara-text"
      title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}

function AppContent() {
  const [status, setStatus] = useState<Status | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [thinking, setThinking] = useState(false)
  const [activeTab, setActiveTab] = useState<typeof TABS[number]['id']>('chat')
  const [activeConvId, setActiveConvId] = useState<string>(
    () => localStorage.getItem(ACTIVE_CONV_KEY) || 'dashboard')
  const [conversations, setConversations] = useState<Conv[]>([])
  const [showSidebar, setShowSidebar] = useState(false)

  const failCountRef = useRef(0)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getStatus()
      failCountRef.current = 0
      setStatus(s)
    } catch {
      failCountRef.current += 1
      if (failCountRef.current >= 4) setStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
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
    setShowSidebar(false)
  }

  const handleRenameConv = async (convId: string, newTitle: string) => {
    await renameConversation(convId, newTitle)
    fetchConversations()
  }

  const handleDeleteConv = async (convId: string) => {
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
      setMessages(prev => [...prev, { role: 'kaihara', text: res.response, route: res.route, provider: (res as any).provider, images: (res as any).images }])
      fetchConversations()
    } catch {
      setMessages(prev => [...prev, { role: 'kaihara', text: '[Connection error. Is Kaihara server running?]' }])
    }
    setThinking(false)
  }

  const activeConv = conversations.find(c => c.conv_id === activeConvId)

  return (
    <div className="h-screen w-screen flex flex-col bg-kaihara-bg text-kaihara-text">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-4 border-b border-kaihara-border flex-shrink-0 bg-kaihara-surface">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-sm">
            K
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">KAIHARA</h1>
            <p className="text-[10px] text-kaihara-muted">AI Super-Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status?.kaihara_online && (
            <span className="text-xs text-kaihara-success flex items-center gap-1">
              <span className="w-2 h-2 bg-kaihara-success rounded-full animate-pulse" />
              Online
            </span>
          )}
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Sidebar - Chat List */}
        <aside className={`${showSidebar ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 absolute md:relative z-40 w-64 h-full flex-shrink-0 border-r border-kaihara-border bg-kaihara-surface transition-transform duration-200`}>
          <div className="p-3 h-full flex flex-col">
            <button
              onClick={handleNewChat}
              className="w-full py-2 px-3 rounded-lg bg-kaihara-primary text-white text-sm font-medium hover:bg-kaihara-primary/90 transition-colors mb-3"
            >
              + New Chat
            </button>
            <div className="flex-1 overflow-y-auto space-y-1">
              {conversations.map(c => (
                <div
                  key={c.conv_id}
                  className={`group flex items-center rounded-lg text-sm transition-colors ${
                    c.conv_id === activeConvId
                      ? 'bg-kaihara-accent/20 text-kaihara-text'
                      : 'text-kaihara-muted hover:bg-kaihara-border/50'
                  }`}
                >
                  <button
                    onClick={() => handleSelectConv(c.conv_id)}
                    className="flex-1 text-left px-3 py-2 min-w-0"
                  >
                    <div className="truncate">{c.title}</div>
                    <div className="text-[10px] text-kaihara-muted">{c.message_count} msgs</div>
                  </button>
                  <div className="hidden group-hover:flex items-center gap-1 pr-2">
                    <button
                      onClick={() => {
                        const newTitle = prompt('Rename chat:', c.title)
                        if (newTitle?.trim()) handleRenameConv(c.conv_id, newTitle.trim())
                      }}
                      className="p-1 hover:bg-kaihara-border rounded text-xs"
                      title="Rename"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this chat?')) handleDeleteConv(c.conv_id)
                      }}
                      className="p-1 hover:bg-kaihara-danger/20 rounded text-xs"
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Overlay for mobile */}
        {showSidebar && (
          <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={() => setShowSidebar(false)} />
        )}

        {/* Content Area */}
        <main className="flex-1 min-w-0 flex flex-col">
          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-kaihara-border bg-kaihara-surface/50">
            <div className="flex px-2">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
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

          {/* Tab Content */}
          <div className="flex-1 min-h-0 overflow-y-auto">
            {activeTab === 'chat' && <Conversation messages={messages} thinking={thinking} onSend={handleSend} />}
            {activeTab === 'tasks' && <TaskBoard />}
            {activeTab === 'security' && <SecurityView />}
            {activeTab === 'memory' && <MemoryTree />}
          </div>
        </main>
      </div>
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
