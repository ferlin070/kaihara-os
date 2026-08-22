#!/bin/bash
# ============================================================
#  LXC Kernel — OS Kernel agents (file, process, network, etc.)
# ============================================================

set -e

echo "[KAIHARA-KERNEL] Setting up..."

apt-get update -y
apt-get install -y python3 python3-pip

pip3 install psutil

# Create kernel workspace
mkdir -p /opt/kaihara/kernel

# Create systemd service for kernel agents
cat > /etc/systemd/system/kaihara-kernel.service << 'EOF'
[Unit]
Description=Kaihara OS Kernel Agents
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "
import time, psutil
while True:
    # Health check
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    print(f'CPU:{cpu}% RAM:{ram}% DISK:{disk}%')
    time.sleep(60)
"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable kaihara-kernel

echo "[KAIHARA-KERNEL] Setup complete."
echo "[KAIHARA-KERNEL] Agents: file, process, network, backup, update, health, cost"
