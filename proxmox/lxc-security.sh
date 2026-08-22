#!/bin/bash
# ============================================================
#  LXC Security — Pentest tools (nmap, nikto, sqlmap, etc.)
# ============================================================

set -e

echo "[KAIHARA-SECURITY] Installing pentest tools..."

apt-get update -y
apt-get install -y nmap nikto sqlmap hydra masscan dnsutils \
    netcat-openbsd curl wget python3 python3-pip git

# Python security deps
pip3 install httpx psutil

# Create pentest workspace
mkdir -p /opt/kaihara/security/{sessions,reports,wordlists}

# Download common wordlists
cd /opt/kaihara/security/wordlists
if [ ! -f "rockyou.txt" ]; then
    echo "[KAIHARA-SECURITY] Downloading wordlists..."
    wget -q https://github.com/danielmiessler/SecLists/raw/master/Passwords/Common-Credentials/10-million-password-list-top-1000.txt -O top1000.txt
fi

echo "[KAIHARA-SECURITY] Tools installed:"
echo "  nmap, nikto, sqlmap, hydra, masscan, dnsutils, netcat"
echo "[KAIHARA-SECURITY] Workspace: /opt/kaihara/security/"
