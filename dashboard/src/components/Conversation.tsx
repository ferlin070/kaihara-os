import React, { useState, useRef, useEffect } from 'react'
import type { Msg } from '../App'
import { getVoiceStatus, speak, type VoiceStatus } from '../lib/api'
import MarkdownRenderer from './MarkdownRenderer'

// Web Speech API types
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

  // Scroll only within chat container, not the page
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

  // Speak new Kaihara replies using server neural TTS when enabled
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
            // Accumulate — don't send yet
            transcriptRef.current += t.trim() + ' '
          } else {
            interimText += t
          }
        }
        // Show live preview in input box
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
    // Send everything that was said, once
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
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Voice status bar */}
      {voiceStatus && voiceStatus.available && (
        <div className="flex-shrink-0 px-4 py-1.5 border-b border-kaihara-border flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span className={`status-dot ${sttAvailable ? 'bg-kaihara-success' : voiceStatus.stt.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
              STT: {sttAvailable ? 'browser' : voiceStatus.stt.engine}
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`status-dot ${voiceStatus.tts.available ? 'bg-kaihara-success' : 'bg-kaihara-danger'}`} />
              TTS: {voiceStatus.tts.engine}
            </span>
          </div>
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={speakReplies}
              onChange={(e) => setSpeakReplies(e.target.checked)}
              className="accent-kaihara-accent"
            />
            Auto-speak replies
          </label>
        </div>
      )}

      {/* Messages — scroll dalam container ini sahaja */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0 p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-2xl">
                K
              </div>
              <p className="text-kaihara-muted text-sm">Kaihara online. How can I help?</p>
              {sttAvailable && <p className="text-kaihara-muted text-xs mt-2">Click MIC and speak — works from any device.</p>}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[75%]">
              {msg.role === 'kaihara' && (
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">
                    K
                  </div>
                  <span className="text-xs text-kaihara-muted">Kaihara</span>
                </div>
              )}
              <div className={`rounded-lg px-4 py-2.5 ${
                msg.role === 'user'
                  ? 'bg-kaihara-primary text-white'
                  : 'bg-kaihara-surface border border-kaihara-border'
              }`}>
                {msg.role === 'kaihara' ? (
                  <MarkdownRenderer content={msg.text} />
                ) : (
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.text}</p>
                )}
                {(msg.route || msg.provider) && <p className="text-xs opacity-60 mt-1.5">{msg.route && <>route: {msg.route}</>}{msg.route && msg.provider && ' · '}{msg.provider && <>via {msg.provider}</>}</p>}
              </div>
              {msg.role === 'kaihara' && msg.text && (
                <button onClick={() => handleSpeak(msg.text)} className="mt-1 ml-1 text-xs text-kaihara-muted hover:text-kaihara-accent transition-colors">
                  🔊 Say it
                </button>
              )}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-kaihara-primary to-kaihara-accent flex items-center justify-center text-white font-bold text-xs">K</div>
            </div>
            <div className="bg-kaihara-surface border border-kaihara-border rounded-lg px-4 py-3 ml-8">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-kaihara-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input — fixed di bawah */}
      <div className="flex-shrink-0 border-t border-kaihara-border p-3 bg-kaihara-bg">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <button type="button" onClick={listening ? stopListening : startListening}
            disabled={!sttAvailable}
            className={`flex-shrink-0 p-2.5 rounded-lg transition-colors ${
              listening ? 'bg-kaihara-danger text-white animate-pulse' : sttAvailable ? 'bg-kaihara-border text-kaihara-muted hover:text-kaihara-accent' : 'bg-kaihara-border text-kaihara-muted opacity-50 cursor-not-allowed'
            }`} title={listening ? 'Stop listening' : sttAvailable ? 'Speak (browser mic)' : 'Browser does not support speech recognition'}>
            🎙️
          </button>
          <input type="text" value={input} onChange={(e) => { if (!listening) setInput(e.target.value) }}
            placeholder={listening ? '🔴 Recording... tekan STOP untuk hantar' : 'Type message...'}
            className="flex-1 bg-kaihara-surface border border-kaihara-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-kaihara-accent min-w-0"
            autoFocus />
          <button type="submit" disabled={!input.trim() || thinking} className="flex-shrink-0 btn-primary disabled:opacity-50">
            Send
          </button>
        </form>
        {listening && (
          <div className="mt-2 flex items-center justify-center gap-1 h-8">
            {Array.from({ length: 30 }).map((_, i) => (
              <span key={i} className="waveform-bar" style={{ animationDelay: `${i * 40}ms` }} />
            ))}
            <span className="ml-3 text-xs text-kaihara-danger animate-pulse">REC{interim ? '' : '...'}</span>
          </div>
        )}
      </div>
    </div>
  )
}
