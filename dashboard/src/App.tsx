import { useState, useEffect, useCallback } from 'react'
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
import { getStatus, sendMessage, getMapState, type SystemStatus as Status } from './lib/api'

export type Msg = { role: 'user' | 'kaihara'; text: string; route?: string }

export default function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [thinking, setThinking] = useState(false)
  const [agents, setAgents] = useState<{name: string; status: string; task: string; progress: number}[]>([])
  const [notifications, setNotifications] = useState<{type: string; text: string}[]>([])
  const [activeTab, setActiveTab] = useState<'chat' | 'map' | 'tasks' | 'skills' | 'security' | 'memory'>('chat')

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getStatus()
      setStatus(s)
      if (s.fleet_agents) {
        // Fetch real agent status from agent map
        const mapData = await getMapState()
        const agentStatus = s.fleet_agents.map(name => {
          const mapAgent = mapData.agents[name]
          return {
            name,
            status: mapAgent?.status || 'idle',
            task: mapAgent?.task || '',
            progress: mapAgent?.progress || 0,
          }
        })
        setAgents(agentStatus)
      }
    } catch {
      setStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleSend = async (text: string) => {
    setMessages(prev => [...prev, { role: 'user', text }])
    setThinking(true)
    try {
      const res = await sendMessage(text)
      setMessages(prev => [...prev, {
        role: 'kaihara',
        text: res.response,
        route: res.route,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'kaihara',
        text: '[Connection error. Is Kaihara server running on :7000?]',
      }])
    }
    setThinking(false)
  }

  return (
    <div className="min-h-screen bg-kaihara-bg text-kaihara-text">
      {/* Header */}
      <header className="border-b border-kaihara-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent
                          flex items-center justify-center text-white font-bold text-sm">
            K
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wide">KAIHARA OS</h1>
            <p className="text-xs text-kaihara-muted">Personal AI Super-Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {status?.kaihara_online ? (
            <span className="flex items-center gap-2 text-xs text-kaihara-success">
              <span className="status-dot bg-kaihara-success animate-pulse" />
              ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-2 text-xs text-kaihara-danger">
              <span className="status-dot bg-kaihara-danger" />
              OFFLINE
            </span>
          )}
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex h-[calc(100vh-57px)]">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-kaihara-border p-3 overflow-y-auto space-y-3">
          <KaiharaStatus thinking={thinking} online={!!status?.kaihara_online} />
          <ChannelStatus />
          <KernelStatus />
          <MetaPanel />
          <SystemStatus status={status} />
          <AgentActivity agents={agents} />
        </aside>

        {/* Center — Tabbed */}
        <main className="flex-1 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-kaihara-border">
            {(['chat', 'map', 'tasks', 'skills', 'security', 'memory'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-2 text-sm font-medium uppercase tracking-wide transition-colors ${
                  activeTab === tab
                    ? 'text-kaihara-accent border-b-2 border-kaihara-accent'
                    : 'text-kaihara-muted hover:text-kaihara-text'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'chat' && (
            <Conversation messages={messages} thinking={thinking} onSend={handleSend} />
          )}
          {activeTab === 'map' && <AgentMap />}
          {activeTab === 'tasks' && <TaskBoard />}
          {activeTab === 'skills' && <SkillBrowser />}
          {activeTab === 'security' && <SecurityView />}
          {activeTab === 'memory' && <MemoryView />}
        </main>

        {/* Right Sidebar */}
        <aside className="w-72 border-l border-kaihara-border p-3 overflow-y-auto space-y-3">
          <MorningBriefing />
          <GoalsTracker />
          <NotificationPanel notifications={notifications} />
        </aside>
      </div>
    </div>
  )
}

// Simple memory view placeholder
function MemoryView() {
  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <h2 className="hud-title">Memory Tree</h2>
      <div className="hud-panel">
        <p className="text-kaihara-muted text-sm">
          Memory viewer — search and browse stored memories.
        </p>
        <p className="text-kaihara-muted text-xs mt-2">
          Use /api/memory/recall?q=your_query to search.
        </p>
      </div>
    </div>
  )
}
