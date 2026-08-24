#!/bin/bash
# ============================================================
#  KAIHARA OS — Deploy to nakhodacloud.top
# ============================================================
#  Usage: ./deploy.sh [server_ip]
# ============================================================

set -e

SERVER=${1:-"nakhodacloud.top"}
REMOTE_USER="root"
REMOTE_DIR="/opt/kaihara-os"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Deploying Kaihara OS to $SERVER..."
echo "📁 Local: $LOCAL_DIR"
echo "📁 Remote: $REMOTE_DIR"

# 1. Create remote directory
echo "📦 Creating remote directory..."
ssh $REMOTE_USER@$SERVER "mkdir -p $REMOTE_DIR"

# 2. Sync files (exclude large dirs)
echo "📤 Syncing files..."
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  --exclude 'data/*.db' \
  --exclude 'data/*.log' \
  "$LOCAL_DIR/" "$REMOTE_USER@$SERVER:$REMOTE_DIR/"

# 3. Build and start on server
echo "🔨 Building and starting services..."
ssh $REMOTE_USER@$SERVER << 'EOF'
cd /opt/kaihara-os/docker

# Build images
docker compose -f docker-compose.prod.yml build

# Stop existing containers
docker compose -f docker-compose.prod.yml down

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

echo ""
echo "✅ Deployment complete!"
echo "🌐 Dashboard: http://nakhodacloud.top"
echo "🔌 API: http://nakhodacloud.top/api/"
EOF

echo ""
echo "✅ Deployed to $SERVER"
echo "🌐 http://$SERVER"
