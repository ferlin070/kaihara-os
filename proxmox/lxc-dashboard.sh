#!/bin/bash
# ============================================================
#  LXC Dashboard — Kaihara HUD Dashboard (nginx static)
#  Runs: nginx serving React build on :80
# ============================================================

set -e

echo "[KAIHARA-DASHBOARD] Setting up..."

# Update system
apt-get update -y
apt-get install -y nginx curl

# Install Node.js (for building)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Create app directory
mkdir -p /opt/kaihara-dashboard
cd /opt/kaihara-dashboard

# Clone dashboard (or copy from host)
if [ ! -f "package.json" ]; then
    echo "[KAIHARA-DASHBOARD] Cloning dashboard..."
    git clone https://github.com/your-repo/kaihara.git /tmp/kaihara
    cp -r /tmp/kaihara/dashboard/* .
fi

# Install + build
npm install
npm run build

# Configure nginx
cat > /etc/nginx/sites-available/kaihara << 'EOF'
server {
    listen 80;
    server_name _;

    root /opt/kaihara-dashboard/dist;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy to core container
    location /api/ {
        proxy_pass http://10.10.10.10:7000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://10.10.10.10:7000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json;
}
EOF

ln -sf /etc/nginx/sites-available/kaihara /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
systemctl enable nginx

echo "[KAIHARA-DASHBOARD] Setup complete."
echo "[KAIHARA-DASHBOARD] URL: http://10.10.10.12"
