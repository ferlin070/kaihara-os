import React, { useState, useRef, useEffect } from 'react'
import type { Msg } from '../App'
import { getVoiceStatus, speak, type VoiceStatus } from '../lib/api'
import MarkdownRenderer from './MarkdownRenderer'

interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  onresult: ((e: any) => void) | null
  onerror: ((e: any) => void) | null
  onend: (() => void) | null
}

function getRecognition(): SpeechRecognitionLike | null {
  const w = window as any
  const SR = w.SpeechRecognition || w.webkitSpeechRecognition
  if (!SR) return null
  const rec = new SR()
  rec.lang = 'ms-MY'
  rec.continuous = false
  rec.interimResults = true
  return rec
}

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
  const [interim, setInterim] = useState('')
  const [speakReplies, setSpeakReplies] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const sttAvailable =
    typeof window !== 'undefined' &&
    !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, thinking])

  useEffect(() => {
    getVoiceStatus().then(setVoiceStatus).catch(() => {})
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

  const lastCountRef = useRef(0)
  useEffect(() => {
    if (!speakReplies) {
      lastCountRef.current = messages.length
      return
    }
    if (messages.length > lastCountRef.current && !thinking) {
      const last = messages[messages.length - 1]
      if (last?.role === 'kaihara' && last.text) {
        speak(last.text).catch(() => {})
      }
    }
    lastCountRef.current = messages.length
  }, [messages, thinking, speakReplies])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || thinking) return
    onSend(input.trim())
    setInput('')
  }

  const shouldListenRef = useRef(false)
  const transcriptRef = useRef('')

  const startListening = () => {
    shouldListenRef.current = true
    transcriptRef.current = ''
    setInterim('')
    setInput('')

    const createAndStart = () => {
      const rec = getRecognition()
      if (!rec) return
      recognitionRef.current = rec
      rec.continuous = true

      rec.onresult = (e: any) => {
        let interimText = ''
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript
          if (e.results[i].isFinal) {
            transcriptRef.current += t.trim() + ' '
          } else {
            interimText += t
          }
        }
        setInput((transcriptRef.current + interimText).trim())
        setInterim(interimText)
      }

      rec.onerror = (e: any) => {
        if (e?.error === 'not-allowed' || e?.error === 'service-not-allowed') {
          shouldListenRef.current = false
          setListening(false)
        }
      }

      rec.onend = () => {
        if (shouldListenRef.current) {
          setTimeout(() => {
            if (shouldListenRef.current) {
              try { rec.start() } catch {}
            }
          }, 250)
        }
      }

      try {
        rec.start()
        setListening(true)
      } catch {}
    }

    createAndStart()
  }

  const stopListening = () => {
    shouldListenRef.current = false
    try { recognitionRef.current?.stop() } catch {}
    setListening(false)
    setInterim('')
    const full = transcriptRef.current.trim()
    transcriptRef.current = ''
    if (full) {
      onSend(full)
    }
    setInput('')
  }

  const handleSpeak = (text: string) => speak(text).catch(() => {})

  const voiceAvailable = voiceStatus?.tts?.available

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Voice status bar */}
      {voiceStatus && voiceStatus.available && (
        <div className="flex-shrink-0 px-6 py-2 border-b border-kaihara-border flex items-center justify-between text-xs bg-kaihara-surface/50">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-2">
              <span className={`status-dot ${sttAvailable ? 'bg-kaihara-success' : voiceStatus.stt.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
              <span className="text-kaihara-muted">STT:</span> {sttAvailable ? 'browser' : voiceStatus.stt.engine}
            </span>
            <span className="flex items-center gap-2">
              <span className={`status-dot ${voiceStatus.tts.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
              <span className="text-kaihara-muted">TTS:</span> {voiceStatus.tts.engine}
            </span>
          </div>
          <label className="flex items-center gap-2 cursor-pointer select-none text-kaihara-muted hover:text-kaihara-text transition-colors">
            <input
              type="checkbox"
              checked={speakReplies}
              onChange={(e) => setSpeakReplies(e.target.checked)}
              className="w-4 h-4 rounded border-kaihara-border bg-kaihara-surface text-kaihara-primary focus:ring-kaihara-primary/20"
            />
            Auto-speak replies
          </label>
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0 p-6">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center animate-fade-in">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-3xl shadow-glow">
                K
              </div>
              <h2 className="text-xl font-semibold mb-2">Kaihara Online</h2>
              <p className="text-kaihara-muted text-sm max-w-xs mx-auto">
                Your personal AI super-intelligence. Ask me anything.
              </p>
              {sttAvailable && (
                <p className="text-kaihara-subtle text-xs mt-4">
                  Click the mic button to speak
                </p>
              )}
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}>
              <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>
                {msg.role === 'kaihara' && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">
                      K
                    </div>
                    <span className="text-xs font-medium text-kaihara-muted">Kaihara</span>
                  </div>
                )}
                <div className={`rounded-2xl px-5 py-3 ${
                  msg.role === 'user'
                    ? 'bg-kaihara-primary text-white rounded-br-md'
                    : 'bg-kaihara-surface border border-kaihara-border rounded-bl-md'
                }`}>
                  {msg.role === 'kaihara' ? (
                    <MarkdownRenderer content={msg.text} />
                  ) : (
                    <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{msg.text}</p>
                  )}
                  {(msg.route || msg.provider) && (
                    <p className="text-xs opacity-50 mt-2 pt-2 border-t border-current/10">
                      {msg.route && <>route: {msg.route}</>}
                      {msg.route && msg.provider && ' · '}
                      {msg.provider && <>via {msg.provider}</>}
                    </p>
                  )}
                </div>
                {msg.role === 'kaihara' && msg.text && (
                  <button 
                    onClick={() => handleSpeak(msg.text)} 
                    className="mt-2 ml-9 text-xs text-kaihara-subtle hover:text-kaihara-primary transition-colors flex items-center gap-1"
                  >
                    <span>🔊</span> Listen
                  </button>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">K</div>
              </div>
              <div className="bg-kaihara-surface border border-kaihara-border rounded-2xl rounded-bl-md px-5 py-4 ml-9">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-kaihara-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-kaihara-border p-4 bg-kaihara-surface/30">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <button 
              type="button" 
              onClick={listening ? stopListening : startListening}
              disabled={!sttAvailable}
              className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
                listening 
                  ? 'bg-kaihara-danger text-white animate-pulse' 
                  : sttAvailable 
                    ? 'bg-kaihara-surface border border-kaihara-border text-kaihara-muted hover:text-kaihara-primary hover:border-kaihara-primary/30' 
                    : 'bg-kaihara-surface border border-kaihara-border text-kaihara-muted opacity-50 cursor-not-allowed'
              }`} 
              title={listening ? 'Stop listening' : sttAvailable ? 'Speak (browser mic)' : 'Browser does not support speech recognition'}
            >
              🎙️
            </button>
            <input 
              type="text" 
              value={input} 
              onChange={(e) => { if (!listening) setInput(e.target.value) }}
              placeholder={listening ? 'Recording... press stop to send' : 'Message Kaihara...'}
              className="input flex-1"
              autoFocus 
            />
            <button 
              type="submit" 
              disabled={!input.trim() || thinking} 
              className="flex-shrink-0 btn-primary disabled:opacity-40 disabled:cursor-not-allowed h-10 px-5"
            >
              Send
            </button>
          </form>
          {listening && (
            <div className="mt-3 flex items-center justify-center gap-1 h-8">
              {Array.from({ length: 30 }).map((_, i) => (
                <span key={i} className="waveform-bar" style={{ animationDelay: `${i * 40}ms` }} />
              ))}
              <span className="ml-3 text-xs text-kaihara-danger animate-pulse font-medium">REC{interim ? '' : '...'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
