#!/bin/bash
# ============================================================
#  LXC LLM — Ollama inference server
#  Runs: ollama serve (on :11434)
# ============================================================

set -e

echo "[KAIHARA-LLM] Setting up Ollama..."

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y curl

# Install Ollama
echo "[KAIHARA-LLM] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Create systemd service (auto-start)
systemctl enable ollama
systemctl start ollama

# Wait for Ollama to be ready
echo "[KAIHARA-LLM] Waiting for Ollama to start..."
sleep 5

# Pull default models
echo "[KAIHARA-LLM] Pulling models..."
ollama pull llama3.1:8b
ollama pull llama3.1:1b
ollama pull qwen2.5-coder:32b 2>/dev/null || true

# Set environment for network access
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment=OLLAMA_HOST=0.0.0.0:11434
EOF

systemctl daemon-reload
systemctl restart ollama

echo "[KAIHARA-LLM] Setup complete."
echo "[KAIHARA-LLM] Ollama: http://10.10.10.11:11434"
echo "[KAIHARA-LLM] Models:"
ollama list
