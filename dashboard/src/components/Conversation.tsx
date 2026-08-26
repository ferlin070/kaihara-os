import React, { useState, useRef, useEffect } from 'react'
import type { Msg } from '../App'
import MarkdownRenderer from './MarkdownRenderer'

export default function Conversation({
  messages,
  thinking,
  onSend,
}: {
  messages: Msg[]
  thinking: boolean
  onSend: (text: string) => void
}) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, thinking])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || thinking) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0 p-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-2xl">
                K
              </div>
              <h2 className="text-lg font-semibold mb-1">Kaihara Online</h2>
              <p className="text-kaihara-muted text-sm">Ask me anything. I'm here to help.</p>
            </div>
          </div>
        )}

        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}
                style={{ animation: 'fadeIn 0.2s ease-out' }}>
                {msg.role === 'kaihara' && (
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">
                      K
                    </div>
                    <span className="text-xs text-kaihara-muted">Kaihara</span>
                  </div>
                )}
                <div className={`rounded-2xl px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-kaihara-primary text-white rounded-br-md'
                    : 'bg-kaihara-surface border border-kaihara-border rounded-bl-md'
                }`}>
                  {msg.role === 'kaihara' ? (
                    <MarkdownRenderer content={msg.text} />
                  ) : (
                    <p className="text-sm whitespace-pre-wrap break-words">{msg.text}</p>
                  )}
                </div>
                {msg.images && msg.images.length > 0 && (
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {msg.images.map((img: any, idx: number) => (
                      <a key={idx} href={img.url} target="_blank" rel="noopener noreferrer"
                        className="block rounded-xl overflow-hidden border border-kaihara-border hover:border-kaihara-accent transition-colors">
                        <img
                          src={img.url}
                          alt={`Gambar ${idx + 1}`}
                          className="w-full h-40 object-cover"
                          loading="lazy"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                        />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">K</div>
              </div>
              <div className="bg-kaihara-surface border border-kaihara-border rounded-2xl rounded-bl-md px-4 py-3 ml-8">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-kaihara-border p-3 bg-kaihara-surface/30">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Kaihara..."
              className="flex-1 bg-kaihara-bg border border-kaihara-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-kaihara-accent transition-colors"
              autoFocus
            />
            <button
              type="submit"
              disabled={!input.trim() || thinking}
              className="bg-kaihara-primary text-white rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-kaihara-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
