/**
 * Kaihara OS - WhatsApp Bridge (Baileys)
 *
 * Protocol:
 *   INBOUND (WhatsApp -> Python): stdout JSON lines
 *     {"type":"message","from":"60123456789","text":"hello"}
 *     {"type":"status","status":"connected"}
 *     {"type":"qr","qr":"<qr_string>"}
 *     {"type":"error","error":"message"}
 *
 *   OUTBOUND (Python -> WhatsApp): stdin JSON lines
 *     {"type":"send","recipient":"60123456789","text":"reply"}
 *     {"type":"stop"}
 *
 * Usage:
 *   node whatsapp_bridge.js
 *   # Scan QR with WhatsApp phone
 *   # Then send/receive via stdin/stdout
 */

import makeWASocket from '@whiskeysockets/baileys'
import { useMultiFileAuthState } from '@whiskeysockets/baileys'
import { fetchLatestBaileysVersion } from '@whiskeysockets/baileys'
import { DisconnectReason } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import pino from 'pino'
import qrcode from 'qrcode-terminal'
import { readFileSync } from 'fs'

const logger = pino({ level: 'silent' })

const AUTH_DIR = './data/whatsapp_auth'

// Send JSON to stdout (for Python to read)
function sendToPython(data) {
  process.stdout.write(JSON.stringify(data) + '\n')
}

// Read JSON from stdin (from Python)
function readFromPython(sock) {
  let buffer = ''
  process.stdin.setEncoding('utf-8')
  process.stdin.on('data', async (chunk) => {
    buffer += chunk
    let lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const msg = JSON.parse(line)
        await handlePythonMessage(msg, sock)
      } catch (e) {
        sendToPython({ type: 'error', error: `Parse error: ${e.message}` })
      }
    }
  })
}

async function handlePythonMessage(msg, sock) {
  if (msg.type === 'send') {
    // Send message to WhatsApp
    try {
      const jid = msg.recipient.includes('@s.whatsapp.net')
        ? msg.recipient
        : `${msg.recipient}@s.whatsapp.net`
      await sock.sendMessage(jid, { text: msg.text })
      sendToPython({ type: 'sent', recipient: msg.recipient })
    } catch (e) {
      sendToPython({ type: 'error', error: `Send failed: ${e.message}` })
    }
  } else if (msg.type === 'stop') {
    sendToPython({ type: 'status', status: 'stopping' })
    await sock.logout()
    process.exit(0)
  }
}

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)

  const { version } = await fetchLatestBaileysVersion()
  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger,
    version,
    browser: ['Kaihara OS', 'Chrome', '1.0.0'],
  })

  // QR code for authentication
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      // Display QR in terminal
      qrcode.generate(qr, { small: true })
      // Also send to Python
      sendToPython({ type: 'qr', qr })
    }

    if (connection === 'close') {
      const shouldReconnect =
        lastDisconnect?.error instanceof Boom &&
        lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut
      if (shouldReconnect) {
        sendToPython({ type: 'status', status: 'reconnecting' })
        connectToWhatsApp()
      } else {
        sendToPython({ type: 'status', status: 'disconnected' })
        sendToPython({
          type: 'error',
          error: 'Logged out. Delete auth folder and restart.',
        })
        process.exit(1)
      }
    } else if (connection === 'open') {
      sendToPython({ type: 'status', status: 'connected' })
    }
  })

  // Save credentials on update
  sock.ev.on('creds.update', saveCreds)

  // Incoming messages
  sock.ev.on('messages.upsert', async (m) => {
    for (const msg of m.messages) {
      if (!msg.message) continue

      // Skip if from self
      if (msg.key.fromMe) continue

      // Extract text
      let text = ''
      if (msg.message.conversation) {
        text = msg.message.conversation
      } else if (msg.message.extendedTextMessage?.text) {
        text = msg.message.extendedTextMessage.text
      } else if (msg.message.imageMessage?.caption) {
        text = msg.message.imageMessage.caption
      }

      if (!text) continue

      // Extract sender (phone number)
      const from = msg.key.remoteJid.split('@')[0]

      // Send to Python via stdout
      sendToPython({
        type: 'message',
        from,
        text,
        timestamp: msg.messageTimestamp,
        messageId: msg.key.id,
      })
    }
  })

  // Start reading from stdin
  readFromPython(sock)

  return sock
}

// Start
connectToWhatsApp().catch((err) => {
  sendToPython({ type: 'error', error: `Connection failed: ${err.message}` })
  process.exit(1)
})
