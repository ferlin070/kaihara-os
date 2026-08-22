#!/bin/bash
# ============================================================
#  LXC Channels — Telegram + WhatsApp + Email bridge
# ============================================================

set -e

echo "[KAIHARA-CHANNELS] Setting up..."

apt-get update -y
apt-get install -y python3 python3-pip nodejs npm

# Python deps for channels
pip3 install python-telegram-bot aiosmtplib

# Node.js for WhatsApp bridge
mkdir -p /opt/kaihara/whatsapp-bridge
cd /opt/kaihara/whatsapp-bridge
cat > package.json << 'EOF'
{"dependencies":{"@whiskeysockets/baileys":"latest","qrcode-terminal":"latest"}}
EOF
npm install

# Environment template
cat > /opt/kaihara/.env.channels << 'EOF'
# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# WhatsApp (Baileys auto-connects, scan QR)

# Email (SMTP + IMAP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EOF

echo "[KAIHARA-CHANNELS] Setup complete."
echo "[KAIHARA-CHANNELS] Edit /opt/kaihara/.env.channels with your credentials."
