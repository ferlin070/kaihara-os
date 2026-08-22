#!/bin/bash
# ============================================================
#  LXC Core — Kaihara Core + API Server
#  Runs: Python app.py (FastAPI on :7000)
# ============================================================

set -e

echo "[KAIHARA-CORE] Setting up..."

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y python3 python3-pip python3-venv git curl

# Create app directory
mkdir -p /opt/kaihara
cd /opt/kaihara

# Clone Kaihara (or copy from host)
if [ ! -f "main.py" ]; then
    echo "[KAIHARA-CORE] Cloning Kaihara..."
    git clone https://github.com/your-repo/kaihara.git .
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install fastapi uvicorn pydantic httpx rank-bm25 chromadb
pip install langgraph openai anthropic tiktoken rich click PyYAML markdown
pip install python-telegram-bot aiosmtplib playwright beautifulsoup4
pip install psutil cryptography

# Install Playwright browsers
playwright install chromium 2>/dev/null || true

# Create systemd service
cat > /etc/systemd/system/kaihara.service << 'EOF'
[Unit]
Description=Kaihara OS Core
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/kaihara
Environment=PYTHONPATH=/opt/kaihara
ExecStart=/opt/kaihara/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable kaihara
systemctl start kaihara

# Config Ollama endpoint
cat > /opt/kaihara/.env << EOF
OLLAMA_HOST=http://10.10.10.11:11434
KAIHARA_HOST=0.0.0.0
KAIHARA_PORT=7000
EOF

echo "[KAIHARA-CORE] Setup complete."
echo "[KAIHARA-CORE] API: http://10.10.10.10:7000"
echo "[KAIHARA-CORE] Docs: http://10.10.10.10:7000/docs"
