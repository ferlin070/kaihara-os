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

      <div className="space-y-1">
        {conversations.length === 0 && (
          <p className="text-xs text-kaihara-muted py-2 text-center">No saved chats.</p>
        )}
        {conversations.map(c => (
          <div
            key={c.conv_id}
            className={`group flex items-center rounded-lg text-xs ${
              c.conv_id === activeConvId 
                ? 'bg-kaihara-primary/10 border border-kaihara-primary/30' 
                : 'hover:bg-kaihara-surface border border-transparent'
            }`}
          >
            <button
              onClick={() => onSelect(c.conv_id)}
              className="flex-1 text-left px-3 py-2 truncate min-w-0"
              title={c.title}
            >
              <span className="block truncate font-medium">{c.title}</span>
              <span className="block text-[10px] text-kaihara-muted mt-0.5">
                {c.message_count} msgs
              </span>
            </button>
            <div className="relative flex-shrink-0 pr-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  const action = prompt('Rename or delete? (r/d)')
                  if (action === 'r') onRename(c.conv_id)
                  else if (action === 'd') onDelete(c.conv_id)
                }}
                className="p-1 text-kaihara-muted hover:text-kaihara-text rounded"
              >
                ⋮
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
