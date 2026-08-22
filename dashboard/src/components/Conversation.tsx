import React, { useState, useRef, useEffect } from 'react'
import type { Msg } from '../App'
import { getVoiceStatus, speak, type VoiceStatus } from '../lib/api'

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
  const [listening, setListening] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  useEffect(() => {
    getVoiceStatus().then(setVoiceStatus).catch(() => {})
    const interval = setInterval(() => {
      getVoiceStatus().then(setVoiceStatus).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || thinking) return
    onSend(input.trim())
    setInput('')
  }

  const toggleVoice = () => setListening(!listening)

  const handleSpeak = (text: string) => {
    speak(text).catch(() => {})
  }

  const voiceAvailable = voiceStatus?.tts?.available
  const sttAvailable = voiceStatus?.stt?.available

  return (
    <div className="flex-1 flex flex-col">
      {/* Voice status bar */}
      {voiceStatus && voiceStatus.available && (
        <div className="px-4 py-1.5 border-b border-kaihara-border flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span className={`status-dot ${
                voiceStatus.stt.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'
              }`} />
              STT: {voiceStatus.stt.engine}
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`status-dot ${
                voiceStatus.tts.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'
              }`} />
              TTS: {voiceStatus.tts.engine}
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`status-dot ${
                voiceStatus.wake.available ? 'bg-kaihara-success' : 'bg-kaihara-warning'
              }`} />
              Wake: "{voiceStatus.wake_word}"
            </span>
          </div>
          <span className="text-kaihara-muted">
            {voiceStatus.listening ? 'LISTENING' : 'idle'}
          </span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br
                              from-kaihara-primary to-kaihara-accent
                              flex items-center justify-center text-white font-bold text-2xl">
                K
              </div>
              <p className="text-kaihara-muted text-sm">
                Kaihara online. How can I help?
              </p>
              {voiceAvailable && (
                <p className="text-kaihara-muted text-xs mt-2">
                  Click the microphone to speak.
                </p>
              )}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[80%]">
              <div className={`rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-kaihara-primary text-white'
                  : 'bg-kaihara-surface border border-kaihara-border'
              }`}>
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                {msg.route && (
                  <p className="text-xs text-kaihara-muted mt-1">[route: {msg.route}]</p>
                )}
              </div>
              {msg.role === 'kaihara' && voiceAvailable && msg.text && (
                <button
                  onClick={() => handleSpeak(msg.text)}
                  className="mt-1 ml-1 text-xs text-kaihara-muted hover:text-kaihara-accent transition-colors"
                  title="Speak this response"
                >
                  Say it
                </button>
              )}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="bg-kaihara-surface border border-kaihara-border rounded-lg px-4 py-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-kaihara-border p-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleVoice}
            className={`p-2 rounded-lg transition-colors ${
              listening
                ? 'bg-kaihara-danger text-white animate-pulse'
                : sttAvailable
                ? 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-accent'
                : 'bg-kaihara-border text-kaihara-muted opacity-50 cursor-not-allowed'
            }`}
            title={listening ? 'Stop listening' : sttAvailable ? 'Voice input' : 'STT not available'}
            disabled={!sttAvailable && !listening}
          >
            {listening ? 'STOP' : 'MIC'}
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={listening ? 'Listening...' : 'Type message...'}
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded-lg px-4 py-2 text-sm
                       focus:outline-none focus:border-kaihara-accent"
            autoFocus
          />
          <button
            type="submit"
            disabled={!input.trim() || thinking}
            className="btn-primary disabled:opacity-50"
          >
            Send
          </button>
        </form>
        {listening && (
          <div className="mt-2 flex items-center justify-center gap-1 h-8">
            {Array.from({ length: 30 }).map((_, i) => (
              <span
                key={i}
                className="waveform-bar"
                style={{ animationDelay: `${i * 40}ms` }}
              />
            ))}
            <span className="ml-3 text-xs text-kaihara-danger animate-pulse">REC</span>
          </div>
        )}
      </div>
    </div>
  )
}
