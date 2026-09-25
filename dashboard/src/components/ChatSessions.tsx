import {
  type Conversation,
} from '../lib/api'
import { useState, useRef, useEffect } from 'react'

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
  onRename: (id: string, newTitle: string) => void
  onDelete: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [menuConvId, setMenuConvId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const active = conversations.find(c => c.conv_id === activeConvId)
  const activeTitle = active?.title || 'Current Chat'

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editingId])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuConvId(null)
        setDeleteConfirm(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleRenameStart = (convId: string, currentTitle: string) => {
    setEditingId(convId)
    setEditValue(currentTitle)
    setMenuConvId(null)
  }

  const handleRenameSubmit = (convId: string) => {
    if (editValue.trim()) {
      onRename(convId, editValue.trim())
    }
    setEditingId(null)
  }

  const handleDeleteClick = (convId: string) => {
    setDeleteConfirm(convId)
  }

  const handleDeleteConfirm = (convId: string) => {
    onDelete(convId)
    setDeleteConfirm(null)
    setMenuConvId(null)
  }

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
        <div className="max-h-64 overflow-y-auto space-y-0.5" ref={menuRef}>
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
              {editingId === c.conv_id ? (
                <div className="flex-1 flex items-center gap-1 px-1 py-1">
                  <input
                    ref={inputRef}
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleRenameSubmit(c.conv_id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    onBlur={() => handleRenameSubmit(c.conv_id)}
                    className="flex-1 bg-kaihara-bg border border-kaihara-accent rounded px-1.5 py-0.5 text-xs focus:outline-none"
                  />
                </div>
              ) : deleteConfirm === c.conv_id ? (
                <div className="flex-1 flex items-center gap-1 px-1 py-1">
                  <span className="text-kaihara-danger text-[10px]">Delete?</span>
                  <button
                    onClick={() => handleDeleteConfirm(c.conv_id)}
                    className="px-1.5 py-0.5 bg-kaihara-danger text-white rounded text-[10px] hover:bg-kaihara-danger/80"
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="px-1.5 py-0.5 bg-kaihara-border text-kaihara-muted rounded text-[10px] hover:text-kaihara-text"
                  >
                    No
                  </button>
                </div>
              ) : (
                <>
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
                        setMenuConvId(menuConvId === c.conv_id ? null : c.conv_id)
                      }}
                      className="px-1.5 py-1 text-kaihara-muted hover:text-kaihara-text"
                    >
                      ⋮
                    </button>
                    {menuConvId === c.conv_id && (
                      <div className="absolute right-0 top-full mt-0.5 z-50 bg-kaihara-surface border border-kaihara-border rounded shadow-lg py-0.5 min-w-[100px]">
                        <button
                          onClick={() => handleRenameStart(c.conv_id, c.title)}
                          className="w-full text-left px-3 py-1.5 text-xs hover:bg-kaihara-accent/20 text-kaihara-text"
                        >
                          ✏️ Rename
                        </button>
                        <button
                          onClick={() => handleDeleteClick(c.conv_id)}
                          className="w-full text-left px-3 py-1.5 text-xs hover:bg-kaihara-danger/20 text-kaihara-danger"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
