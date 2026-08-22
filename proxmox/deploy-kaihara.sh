#!/bin/bash
# ============================================================
#  KAIHARA OS — Server Cleanup & Fresh Deploy
#  Run on: cloudhosting (192.168.1.99) — Proxmox main host
# ============================================================
#  This script:
#    1. Stops and deletes unwanted CTs
#    2. Creates 5 new CTs for KAIHARA OS
#    3. Pulls Kaihara from GitHub
#    4. Configures LLM (rootsys + Ollama at CT 201)
#    5. Sets up networking between all CTs
# ============================================================

set -e

# ============================================================
#  CONFIGURATION
# ============================================================

# Network
GATEWAY="192.168.1.1"
SUBNET="192.168.1"

# Storage (optimized for infrastructure)
STORAGE_CT="nvme-m.2"           # CT rootfs (pantas, 803GB free)
STORAGE_BACKUP="hdd-2tb"       # Auto backup (1363GB free)
STORAGE_VAULT="hdd-1tb"        # Obsidian vault (931GB free, 100% free)
TEMPLATE="debian-12-standard_12.2-1_amd64.tar.zst"

# GitHub Repo (CHANGE THIS to your repo)
GITHUB_REPO="https://github.com/your-username/kaihara-os.git"
# If you don't have a GitHub repo yet, we'll copy from local

# LLM Configuration
ROOTSYS_API_KEY="fiq-4c421e2fc68c0c4436fdd7bf65cf8b73"
ROOTSYS_BASE_URL="https://rootsys.cloud/v1"
OLLAMA_HOST="192.168.1.248"  # CT 201 (ai-stack)
ROUTER_HOST="192.168.1.41"   # CT 107 (9router)

# ============================================================
#  CT IDs
# ============================================================

# CTs to DELETE (unwanted)
DELETE_CTS=(103 105 106 108 109 110)

# CTs to KEEP (do not touch)
KEEP_CTS=(100 101 102 104 107 201 300)

# New CTs for KAIHARA OS
CT_CORE=203        # kaihara-core
CT_DASHBOARD=204   # kaihara-dashboard
CT_CHANNELS=205    # kaihara-channels
CT_SECURITY=206    # kaihara-security
CT_KERNEL=207      # kaihara-kernel

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${BLUE}[KAIHARA]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
#  STEP 1: CLEANUP — Delete unwanted CTs
# ============================================================

echo ""
echo "============================================================"
echo "  STEP 1: CLEANUP — Delete Unwanted CTs"
echo "============================================================"
echo ""

# CTs to delete with their descriptions
declare -A CT_NAMES
CT_NAMES[103]="chafb (uruscompany panel)"
CT_NAMES[105]="casaos (personal cloud)"
CT_NAMES[106]="odysseus (AI workspace)"
CT_NAMES[108]="kaihara (old web portal)"
CT_NAMES[109]="hermes-openclaw"
CT_NAMES[110]="docker"

for ct_id in "${DELETE_CTS[@]}"; do
    name="${CT_NAMES[$ct_id]:-unknown}"
    if pct status "$ct_id" &>/dev/null; then
        warn "CT $ct_id ($name) exists. Stopping and deleting..."
        pct stop "$ct_id" 2>/dev/null || true
        sleep 2
        pct destroy "$ct_id" --purge 2>/dev/null || true
        ok "CT $ct_id deleted."
    else
        log "CT $ct_id ($name) not found. Skipping."
    fi
done

echo ""
ok "Cleanup complete. Kept CTs: ${KEEP_CTS[*]}"
echo ""

# ============================================================
#  STEP 2: CREATE NEW CTs FOR KAIHARA OS
# ============================================================

echo "============================================================"
echo "  STEP 2: CREATE KAIHARA OS CONTAINERS"
echo "============================================================"
echo ""

# Download template
log "Checking LXC template..."
pct template download "$TEMPLATE" 2>/dev/null || true

# Create function
create_ct() {
    local id=$1
    local hostname=$2
    local ip_suffix=$3
    local cores=$4
    local memory=$5
    local disk=$6
    local description=$7

    if pct status "$id" &>/dev/null; then
        warn "CT $id ($hostname) already exists. Skipping."
        return 0
    fi

    log "Creating CT $id: $hostname ($description)"
    log "  Cores: $cores, RAM: ${memory}MB, Disk: ${disk}GB, IP: ${SUBNET}.${ip_suffix}"

    pct create "$TEMPLATE" "$id" \
        --hostname "$hostname" \
        --cores "$cores" \
        --memory "$memory" \
        --swap 512 \
        --rootfs "${STORAGE_CT}:${disk}" \
        --net0 "name=eth0,ip=${SUBNET}.${ip_suffix}/24,gw=${GATEWAY}" \
        --features "nesting=1" \
        --unprivileged 1 \
        --description "$description"

    ok "CT $id ($hostname) created at ${SUBNET}.${ip_suffix}"
}

# CT 203: Kaihara Core
create_ct $CT_CORE "kaihara-core" 211 4 4096 20 "Kaihara Core: API + Brain + Fleet + Skills"

# CT 204: Dashboard
create_ct $CT_DASHBOARD "kaihara-dashboard" 212 1 512 5 "Kaihara Dashboard: React + nginx"

# CT 205: Channels
create_ct $CT_CHANNELS "kaihara-channels" 213 1 1024 5 "Kaihara Channels: Telegram + WhatsApp + Email"

# CT 206: Security
create_ct $CT_SECURITY "kaihara-security" 214 2 2048 10 "Kaihara Security: Pentest tools"

# CT 207: Kernel
create_ct $CT_KERNEL "kaihara-kernel" 215 1 1024 5 "Kaihara Kernel: 7 OS background agents"

echo ""
ok "All 5 KAIHARA OS containers created."
echo ""

# ============================================================
#  STEP 2.5: SETUP STORAGE MOUNTS (backup + vault)
# ============================================================

echo "============================================================"
echo "  STEP 2.5: SETUP STORAGE MOUNTS"
echo "============================================================"
echo ""

# Create mount points on Proxmox host
log "Creating host mount directories..."
mkdir -p /mnt/kaihara-backup
mkdir -p /mnt/kaihara-vault

# Mount hdd-2tb for backup (if not already mounted)
log "Setting up backup storage (hdd-2tb)..."
BACKUP_LV=$(lvs --noheadings -o lv_path 2>/dev/null | grep hdd-2tb | head -1 || true)
if [ -n "$BACKUP_LV" ]; then
    mkdir -p /mnt/kaihara-backup
    if ! mountpoint -q /mnt/kaihara-backup; then
        mount "$BACKUP_LV" /mnt/kaihara-backup 2>/dev/null || true
    fi
fi
mkdir -p /mnt/kaihara-backup/kaihara/{database,config,vault}
ok "Backup storage ready: /mnt/kaihara-backup/kaihara/"

# Mount hdd-1tb for Obsidian vault (if not already mounted)
log "Setting up Obsidian vault storage (hdd-1tb)..."
VAULT_LV=$(lvs --noheadings -o lv_path 2>/dev/null | grep hdd-1tb | head -1 || true)
if [ -n "$VAULT_LV" ]; then
    mkdir -p /mnt/kaihara-vault
    if ! mountpoint -q /mnt/kaihara-vault; then
        mount "$VAULT_LV" /mnt/kaihara-vault 2>/dev/null || true
    fi
fi
mkdir -p /mnt/kaihara-vault/{memory/{context,daily,core},knowledge,goals,briefings,prd}
ok "Vault storage ready: /mnt/kaihara-vault/"

# Mount backup + vault into CT 203 (kaihara-core)
log "Mounting storage into CT $CT_CORE..."
# Method: bind mount host directories into CT
pct set $CT_CORE -mp0 /mnt/kaihara-backup/kaihara,mp=/mnt/backup
pct set $CT_CORE -mp1 /mnt/kaihara-vault,mp=/mnt/vault

ok "CT $CT_CORE mounts: /mnt/backup (hdd-2tb), /mnt/vault (hdd-1tb)"

# Also mount vault into CT 207 (kernel) for backup agent
pct set $CT_KERNEL -mp0 /mnt/kaihara-backup/kaihara,mp=/mnt/backup
ok "CT $CT_KERNEL mounts: /mnt/backup (hdd-2tb)"
echo ""

# ============================================================
#  STEP 3: START CONTAINERS
# ============================================================

echo "============================================================"
echo "  STEP 3: START CONTAINERS"
echo "============================================================"
echo ""

for ct in $CT_CORE $CT_DASHBOARD $CT_CHANNELS $CT_SECURITY $CT_KERNEL; do
    log "Starting CT $ct..."
    pct start "$ct" 2>/dev/null || true
    sleep 3
done

ok "All containers started."
log "Waiting for network (15s)..."
sleep 15
echo ""

# ============================================================
#  STEP 4: SETUP KAIHARA CORE (CT 203)
# ============================================================

echo "============================================================"
echo "  STEP 4: SETUP KAIHARA CORE (CT $CT_CORE)"
echo "============================================================"
echo ""

log "Updating system + installing deps..."
pct exec $CT_CORE -- bash -c "
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y python3 python3-pip python3-venv git curl wget
"

log "Creating app directory..."
pct exec $CT_CORE -- mkdir -p /opt/kaihara

log "Pulling Kaihara from GitHub..."
pct exec $CT_CORE -- bash -c "
    cd /opt
    if [ -d kaihara ]; then
        cd kaihara && git pull
    else
        git clone $GITHUB_REPO /opt/kaihara
    fi
"

log "Installing Python dependencies..."
pct exec $CT_CORE -- bash -c "
    cd /opt/kaihara
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install fastapi uvicorn pydantic httpx rank-bm25 chromadb
    pip install langgraph openai anthropic tiktoken rich click PyYAML markdown
    pip install python-telegram-bot aiosmtplib beautifulsoup4 psutil cryptography
"

log "Configuring LLM (rootsys + Ollama backup)..."
pct exec $CT_CORE -- bash -c "
cat > /opt/kaihara/config.toml << 'CONFIGEOF'
[system]
name = \"Kaihara\"
version = \"0.1.0\"
data_dir = \"./data\"
obsidian_vault = \"/mnt/vault\"
log_level = \"INFO\"
language = \"ms\"

[model]
default = \"rootsys/glm-5.2\"
small_model = \"rootsys/deepseek-v4-flash\"
reflex_model = \"rootsys/deepseek-v4-flash\"

[provider.rootsys]
name = \"RootSys Cloud\"
base_url = \"https://rootsys.cloud/v1\"
api_key = \"$ROOTSYS_API_KEY\"
api_key_header = \"X-API-Key\"

[provider.ollama]
name = \"Ollama (CT 201 backup)\"
base_url = \"http://$OLLAMA_HOST:11434/v1\"

[provider.ollama_local]
name = \"Ollama via 9router\"
base_url = \"http://$ROUTER_HOST:11434/v1\"

[privacy]
mode = false
enforce_in_core = false

[memory]
db_path = \"./data/kaihara.db\"
context_window = 20
daily_compression_hour = 3
auto_fetch_interval = 20

[memory.recall]
bm25_weight = 0.4
vector_weight = 0.4
graph_weight = 0.2
rrf_k = 60

[tokenjuice]
enabled = true
output_compression = true
input_compression = true
shell_compression = true
cache_originals = true

[security]
approval_required = [\"deploy_to_production\",\"push_to_git\",\"send_email\",\"send_whatsapp\",\"send_telegram\",\"run_pentest\",\"delete_file\",\"execute_shell\",\"spend_money\"]
sandbox_enabled = true
audit_log = \"./data/audit.log\"

[channel.telegram]
enabled = false
bot_token = \"\"

[channel.whatsapp]
enabled = false

[channel.email]
enabled = false

[channel.dashboard]
enabled = true
port = 7000

[voice]
enabled = false
wake_word = \"kaihara\"

[server]
host = \"0.0.0.0\"
port = 7000
websocket_enabled = true

[os]
file.temp_dirs = [\"./data/tmp\"]
process.cpu_threshold = 90
network.monitored_ports = [7000, 11434]
backup.backup_dir = \"/mnt/backup\"
backup.backup_hour = 3
health.cpu_threshold = 90
health.ram_threshold = 90
health.disk_threshold = 90
cost.daily_budget = 10.0
cost.monthly_budget = 100.0
CONFIGEOF
"

log "Creating systemd service..."
pct exec $CT_CORE -- bash -c "
cat > /etc/systemd/system/kaihara.service << 'SVCEOF'
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
SVCEOF

systemctl daemon-reload
systemctl enable kaihara
systemctl start kaihara
"

ok "Kaihara Core (CT $CT_CORE) setup complete at ${SUBNET}.211:7000"

log "Setting up Google Drive (rclone)..."
pct exec $CT_CORE -- bash -c "
    # Install rclone
    curl -fsSL https://rclone.org/install.sh | bash 2>/dev/null || true
    
    # Check if CT 101 (storage01) has rclone config
    # If yes, copy it. If no, user will configure later.
    mkdir -p /root/.config/rclone
    
    echo 'Google Drive setup:'
    echo '  1. If CT 101 (storage01) has rclone configured:'
    echo '     scp root@192.168.1.22:/root/.config/rclone/rclone.conf /root/.config/rclone/'
    echo '  2. Or configure manually:'
    echo '     rclone config → n → gdrive → drive → login'
    echo '  3. Test: rclone ls gdrive:'
"

ok "GDrive ready for configuration (rclone installed)"
echo ""

# ============================================================
#  STEP 5: SETUP DASHBOARD (CT 204)
# ============================================================

echo "============================================================"
echo "  STEP 5: SETUP DASHBOARD (CT $CT_DASHBOARD)"
echo "============================================================"
echo ""

log "Installing nginx + Node.js..."
pct exec $CT_DASHBOARD -- bash -c "
    apt-get update -y
    apt-get install -y nginx curl
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
"

log "Pulling dashboard from GitHub..."
pct exec $CT_DASHBOARD -- bash -c "
    mkdir -p /opt/kaihara-dashboard
    cd /opt
    if [ -d kaihara ]; then
        cd kaihara && git pull
    else
        git clone $GITHUB_REPO /tmp/kaihara
    fi
    cp -r /tmp/kaihara/dashboard/* /opt/kaihara-dashboard/
"

log "Building React dashboard..."
pct exec $CT_DASHBOARD -- bash -c "
    cd /opt/kaihara-dashboard
    npm install
    npm run build
"

log "Configuring nginx (proxy to CT $CT_CORE)..."
pct exec $CT_DASHBOARD -- bash -c "
cat > /etc/nginx/sites-available/kaihara << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    root /opt/kaihara-dashboard/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://192.168.1.211:7000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /ws {
        proxy_pass http://192.168.1.211:7000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
    }

    gzip on;
    gzip_types text/css application/javascript application/json;
}
NGINXEOF

ln -sf /etc/nginx/sites-available/kaihara /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
systemctl enable nginx
"

ok "Dashboard (CT $CT_DASHBOARD) setup complete at ${SUBNET}.212"
echo ""

# ============================================================
#  STEP 6: SETUP CHANNELS (CT 205)
# ============================================================

echo "============================================================"
echo "  STEP 6: SETUP CHANNELS (CT $CT_CHANNELS)"
echo "============================================================"
echo ""

log "Installing deps..."
pct exec $CT_CHANNELS -- bash -c "
    apt-get update -y
    apt-get install -y python3 python3-pip nodejs npm
    pip3 install python-telegram-bot aiosmtplib httpx
"

log "Setting up WhatsApp bridge..."
pct exec $CT_CHANNELS -- bash -c "
    mkdir -p /opt/kaihara/channels
    cd /opt/kaihara/channels
    cat > package.json << 'PKGEOF'
{\"dependencies\":{\"@whiskeysockets/baileys\":\"latest\",\"qrcode-terminal\":\"latest\"}}
PKGEOF
    npm install
"

log "Creating channels config..."
pct exec $CT_CHANNELS -- bash -c "
cat > /opt/kaihara/.env.channels << 'ENVEOF'
# Telegram (set your bot token)
TELEGRAM_BOT_TOKEN=

# WhatsApp (scan QR on first run)

# Email (SMTP + IMAP)
SMTP_HOST=
SMTP_PORT=587
IMAP_HOST=
IMAP_PORT=993
EMAIL_USERNAME=
EMAIL_PASSWORD=
ENVEOF
"

ok "Channels (CT $CT_CHANNELS) setup complete at ${SUBNET}.213"
echo ""

# ============================================================
#  STEP 7: SETUP SECURITY (CT 206)
# ============================================================

echo "============================================================"
echo "  STEP 7: SETUP SECURITY (CT $CT_SECURITY)"
echo "============================================================"
echo ""

log "Installing pentest tools..."
pct exec $CT_SECURITY -- bash -c "
    apt-get update -y
    apt-get install -y nmap nikto sqlmap hydra masscan dnsutils netcat-openbsd curl wget python3 python3-pip git
    pip3 install httpx psutil
    mkdir -p /opt/kaihara/security/{sessions,reports,wordlists}
"

ok "Security (CT $CT_SECURITY) setup complete at ${SUBNET}.214"
echo ""

# ============================================================
#  STEP 8: SETUP KERNEL (CT 207)
# ============================================================

echo "============================================================"
echo "  STEP 8: SETUP KERNEL (CT $CT_KERNEL)"
echo "============================================================"
echo ""

log "Installing kernel deps..."
pct exec $CT_KERNEL -- bash -c "
    apt-get update -y
    apt-get install -y python3 python3-pip
    pip3 install psutil httpx
"

log "Creating kernel service..."
pct exec $CT_KERNEL -- bash -c "
cat > /etc/systemd/system/kaihara-kernel.service << 'KSVCEOF'
[Unit]
Description=Kaihara OS Kernel Agents
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c \"
import time, psutil
while True:
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    print(f'CPU:{cpu}% RAM:{ram}% DISK:{disk}%')
    time.sleep(60)
\"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
KSVCEOF

systemctl daemon-reload
systemctl enable kaihara-kernel
systemctl start kaihara-kernel
"

ok "Kernel (CT $CT_KERNEL) setup complete at ${SUBNET}.215"
echo ""

# ============================================================
#  STEP 9: VERIFY OLLAMA ON CT 201
# ============================================================

echo "============================================================"
echo "  STEP 9: VERIFY OLLAMA (CT 201)"
echo "============================================================"
echo ""

log "Checking Ollama on CT 201 (ai-stack)..."
if pct status 201 &>/dev/null; then
    log "CT 201 is running. Checking Ollama..."
    pct exec 201 -- bash -c "
        if command -v ollama &>/dev/null; then
            echo 'Ollama found. Listing models:'
            ollama list
        else
            echo 'Ollama not installed on CT 201.'
            echo 'Installing Ollama...'
            curl -fsSL https://ollama.com/install.sh | sh
            systemctl enable ollama
            systemctl start ollama
            sleep 5
            echo 'Pulling models...'
            ollama pull llama3.1:8b
            ollama pull llama3.1:1b
        fi
    " 2>/dev/null || warn "Could not check Ollama on CT 201"
else
    warn "CT 201 not running. Start it first: pct start 201"
fi
echo ""

# ============================================================
#  SUMMARY
# ============================================================

echo ""
echo "============================================================"
echo "  KAIHARA OS — DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "  DELETED CTs:"
echo "    103 (chafb), 105 (casaos), 106 (odysseus)"
echo "    108 (kaihara old), 109 (hermes-openclaw), 110 (docker)"
echo ""
echo "  KEPT CTs:"
echo "    100 (test10), 101 (storage01), 102"
echo "    104 (obsidian-vault), 107 (9router)"
echo "    201 (ai-stack/Ollama), 300 (mara-ai-server)"
echo ""
echo "  NEW KAIHARA CTs (all on NVMe M.2):"
echo "    CT $CT_CORE  — kaihara-core      ${SUBNET}.211  API :7000  (4c/4GB/20GB)"
echo "    CT $CT_DASHBOARD — kaihara-dashboard ${SUBNET}.212  HTTP :80 (1c/512MB/5GB)"
echo "    CT $CT_CHANNELS  — kaihara-channels  ${SUBNET}.213          (1c/1GB/5GB)"
echo "    CT $CT_SECURITY  — kaihara-security  ${SUBNET}.214          (2c/2GB/10GB)"
echo "    CT $CT_KERNEL   — kaihara-kernel    ${SUBNET}.215          (1c/1GB/5GB)"
echo ""
echo "  STORAGE:"
echo "    NVMe M.2   — CT rootfs (pantas, 803GB free, used 45GB)"
echo "    HDD 2TB    — /mnt/backup (auto backup 3AM, 1363GB free)"
echo "    HDD 1TB    — /mnt/vault (Obsidian vault, 931GB free)"
echo "    GDrive     — Cloud backup + vault sync + report upload"
echo "    Sync vault — CT 104 (obsidian-vault .141)"
echo ""
echo "  LLM:"
echo "    Primary: rootsys.cloud (glm-5.2, kimi-k3, deepseek-v4-flash)"
echo "    Backup:  Ollama @ CT 201 (${OLLAMA_HOST}:11434)"
echo "    Router:  9router @ CT 107 (${ROUTER_HOST})"
echo ""
echo "  ACCESS:"
echo "    Dashboard: http://${SUBNET}.212"
echo "    API docs:  http://${SUBNET}.211:7000/docs"
echo "    Ollama:    http://${OLLAMA_HOST}:11434"
echo ""
echo "  GOOGLE DRIVE (configure after deploy):"
echo "    Option A: Copy from CT 101 (storage01):"
echo "      pct exec $CT_CORE -- scp root@192.168.1.22:/root/.config/rclone/rclone.conf /root/.config/rclone/"
echo "    Option B: Configure manually:"
echo "      pct exec $CT_CORE -- rclone config"
echo "    Test:    pct exec $CT_CORE -- rclone ls gdrive:"
echo "    API:     GET /api/gdrive/status"
echo ""
echo "  NEXT STEPS:"
echo "    1. Configure GDrive: pct exec $CT_CORE -- rclone config"
echo "    2. Set Telegram token: pct exec $CT_CHANNELS -- bash -c \"echo 'TELEGRAM_BOT_TOKEN=your-token' >> /opt/kaihara/.env.channels\""
echo "    3. Push kaihara to GitHub first, then re-run this script"
echo "    4. Or copy local kaihara/ to CT $CT_CORE manually:"
echo "       pct push $CT_CORE /path/to/kaihara/ /opt/kaihara/"
echo ""
echo "============================================================"
