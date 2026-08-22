#!/bin/bash
# ============================================================
#  KAIHARA OS — Proxmox LXC Master Setup
#  Creates all LXC containers for Kaihara OS
# ============================================================
#  Run on Proxmox host: bash proxmox/main.sh
# ============================================================

set -e

# Config
KAIHARA_VERSION="0.1.0"
STORAGE="local-lvm"
TEMPLATE="debian-12-standard_12.2-1_amd64.tar.zst"
GATEWAY="10.10.10.1"
SUBNET="10.10.10"

# Container IDs
CT_CORE=201
CT_LLM=202
CT_DASHBOARD=203
CT_CHANNELS=204
CT_SECURITY=205
CT_KERNEL=206

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[KAIHARA]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    err "This script must be run on a Proxmox host."
    err "Install Proxmox VE from https://www.proxmox.com/"
    exit 1
fi

echo ""
echo "============================================================"
echo "  KAIHARA OS — Proxmox LXC Setup v${KAIHARA_VERSION}"
echo "============================================================"
echo ""

# Download template if needed
log "Checking LXC template..."
pct template download "${TEMPLATE}" 2>/dev/null || true

# Create containers
log "Creating LXC containers..."

# Function: create LXC
create_lxc() {
    local id=$1
    local name=$2
    local ip=$3
    local cores=$4
    local memory=$5
    local disk=$6

    # Check if already exists
    if pct status "$id" &> /dev/null; then
        warn "CT $id ($name) already exists. Skipping."
        return 0
    fi

    log "Creating CT $id: $name (${cores}c, ${memory}MB, ${disk}GB, ${ip})"
    pct create "$TEMPLATE" "$id" \
        --hostname "$name" \
        --cores "$cores" \
        --memory "$memory" \
        --rootfs "$STORAGE:$disk" \
        --net0 "name=eth0,ip=${SUBNET}.${ip}/24,gw=${GATEWAY}" \
        --features "nesting=1" \
        --unprivileged 1

    ok "CT $id ($name) created."
}

# Create all containers
create_lxc $CT_CORE "kaihara-core" 10 2 2048 10
create_lxc $CT_LLM "kaihara-llm" 11 4 8192 50
create_lxc $CT_DASHBOARD "kaihara-dashboard" 12 1 512 5
create_lxc $CT_CHANNELS "kaihara-channels" 13 1 1024 5
create_lxc $CT_SECURITY "kaihara-security" 14 2 2048 10
create_lxc $CT_KERNEL "kaihara-kernel" 15 1 1024 5

# Start containers
log "Starting containers..."
for ct in $CT_CORE $CT_LLM $CT_DASHBOARD $CT_CHANNELS $CT_SECURITY $CT_KERNEL; do
    pct start "$ct" 2>/dev/null || true
    sleep 2
done
ok "All containers started."

# Wait for network
log "Waiting for network..."
sleep 10

# Setup each container
log "Setting up containers..."

# CT_CORE: Kaihara Core + API
log "Setting up kaihara-core (CT $CT_CORE)..."
pct push "$CT_CORE" proxmox/lxc-core.sh /root/setup.sh
pct exec "$CT_CORE" -- bash /root/setup.sh

# CT_LLM: Ollama
log "Setting up kaihara-llm (CT $CT_LLM)..."
pct push "$CT_LLM" proxmox/lxc-llm.sh /root/setup.sh
pct exec "$CT_LLM" -- bash /root/setup.sh

# CT_DASHBOARD: Dashboard
log "Setting up kaihara-dashboard (CT $CT_DASHBOARD)..."
pct push "$CT_DASHBOARD" proxmox/lxc-dashboard.sh /root/setup.sh
pct exec "$CT_DASHBOARD" -- bash /root/setup.sh

# CT_CHANNELS: Channels
log "Setting up kaihara-channels (CT $CT_CHANNELS)..."
pct push "$CT_CHANNELS" proxmox/lxc-channels.sh /root/setup.sh
pct exec "$CT_CHANNELS" -- bash /root/setup.sh

# CT_SECURITY: Security tools
log "Setting up kaihara-security (CT $CT_SECURITY)..."
pct push "$CT_SECURITY" proxmox/lxc-security.sh /root/setup.sh
pct exec "$CT_SECURITY" -- bash /root/setup.sh

# CT_KERNEL: OS Kernel agents
log "Setting up kaihara-kernel (CT $CT_KERNEL)..."
pct push "$CT_KERNEL" proxmox/lxc-kernel.sh /root/setup.sh
pct exec "$CT_KERNEL" -- bash /root/setup.sh

ok "All containers set up."

# Summary
echo ""
echo "============================================================"
echo "  KAIHARA OS — SETUP COMPLETE"
echo "============================================================"
echo ""
echo "  Containers:"
echo "    CT $CT_CORE  - kaihara-core      ${SUBNET}.10  (API :7000)"
echo "    CT $CT_LLM   - kaihara-llm       ${SUBNET}.11  (Ollama :11434)"
echo "    CT $CT_DASHBOARD - kaihara-dashboard ${SUBNET}.12 (HTTP :80)"
echo "    CT $CT_CHANNELS  - kaihara-channels  ${SUBNET}.13"
echo "    CT $CT_SECURITY  - kaihara-security  ${SUBNET}.14"
echo "    CT $CT_KERNEL   - kaihara-kernel    ${SUBNET}.15"
echo ""
echo "  Access:"
echo "    Dashboard: http://${SUBNET}.12"
echo "    API docs:  http://${SUBNET}.10:7000/docs"
echo "    Ollama:    http://${SUBNET}.11:11434"
echo ""
echo "  Next steps:"
echo "    1. Set TELEGRAM_BOT_TOKEN in CT $CT_CHANNELS"
echo "    2. Pull Ollama models: pct exec $CT_LLM -- ollama pull llama3.1:8b"
echo "    3. Start Kaihara: pct exec $CT_CORE -- systemctl start kaihara"
echo ""
echo "============================================================"
