import { useState } from 'react'
import {
  type Conversation,
} from '../lib/api'

export default function ChatSessions({
  conversations,
  activeConvId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: {
  conversations: Conversation[]
  activeConvId: string
  onSelect: (id: string) => void
  onNewChat: () => void
  onRename: (id: string) => void
  onDelete: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [menuFor, setMenuFor] = useState<string | null>(null)

  const active = conversations.find(c => c.conv_id === activeConvId)
  const activeTitle = active?.title || 'Current Chat'

  return (
    <div className="hud-panel">
      <div className="flex items-center justify-between mb-1.5">
        <div className="hud-title">Chats</div>
        <button
          onClick={onNewChat}
          className="text-xs px-2 py-0.5 rounded bg-kaihara-accent text-white hover:opacity-80 transition-opacity"
          title="Start new chat"
        >
          + New
        </button>
      </div>

      {/* Active chat name — click to toggle list */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between text-xs text-left px-2 py-1.5 rounded bg-kaihara-bg border border-kaihara-border hover:border-kaihara-accent transition-colors"
      >
        <span className="truncate">{activeTitle}</span>
        <span className="text-kaihara-muted ml-2">{open ? '▲' : '▼'}</span>
      </button>

      {/* Conversation list */}
      {open && (
        <div className="mt-1.5 max-h-56 overflow-y-auto space-y-0.5">
          {conversations.length === 0 && (
            <p className="text-xs text-kaihara-muted px-2 py-1">No saved chats.</p>
          )}
          {conversations.map(c => (
            <div
              key={c.conv_id}
              className={`group flex items-center rounded text-xs ${
                c.conv_id === activeConvId ? 'bg-kaihara-accent/20' : 'hover:bg-kaihara-border/50'
              }`}
            >
              <button
                onClick={() => { onSelect(c.conv_id); setOpen(false) }}
                className="flex-1 text-left px-2 py-1.5 truncate min-w-0"
                title={c.title}
              >
                <span className="block truncate">{c.title}</span>
                <span className="block text-[10px] text-kaihara-muted">
                  {c.message_count} msgs • {new Date(c.updated_at).toLocaleDateString()}
                </span>
              </button>
              <div className="relative flex-shrink-0 pr-1">
                <button
                  onClick={() => setMenuFor(menuFor === c.conv_id ? null : c.conv_id)}
                  className="px-1.5 py-1 text-kaihara-muted hover:text-kaihara-text"
                >
                  ⋮
                </button>
                {menuFor === c.conv_id && (
                  <div className="absolute right-0 top-full mt-0.5 z-10 bg-kaihara-surface border border-kaihara-border rounded shadow-lg w-28">
                    <button
                      onClick={() => { onRename(c.conv_id); setMenuFor(null) }}
                      className="block w-full text-left px-3 py-1.5 hover:bg-kaihara-border/50"
                    >
                      ✏️ Rename
                    </button>
                    <button
                      onClick={() => { onDelete(c.conv_id); setMenuFor(null) }}
                      className="block w-full text-left px-3 py-1.5 text-kaihara-danger hover:bg-kaihara-border/50"
                    >
                      🗑 Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
