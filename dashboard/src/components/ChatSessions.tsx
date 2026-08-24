import {
  type Conversation,
} from '../lib/api'
import { useState } from 'react'

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

  const active = conversations.find(c => c.conv_id === activeConvId)
  const activeTitle = active?.title || 'Current Chat'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-kaihara-muted">Chats</div>
        <button
          onClick={onNewChat}
          className="text-xs px-2 py-0.5 rounded bg-kaihara-primary text-white hover:bg-kaihara-primary/90 transition-colors"
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
        <div className="space-y-0.5">
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
                  {c.message_count} msgs
                </span>
              </button>
              <div className="relative flex-shrink-0 pr-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    const action = prompt('Rename or delete? (r/d)')
                    if (action === 'r') onRename(c.conv_id)
                    else if (action === 'd') onDelete(c.conv_id)
                  }}
                  className="px-1.5 py-1 text-kaihara-muted hover:text-kaihara-text"
                >
                  ⋮
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
