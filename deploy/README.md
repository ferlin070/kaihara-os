# Kaihara OS — Production Deployment (CT-Based)

> Senibina distributed: 5 LXC containers di Proxmox. Migrasi selesai 2026-08-23.

## Peta CT

| VMID | Nama | IP | Spec | Fungsi |
|------|------|-----|------|--------|
| 203 | kaihara-core | 192.168.1.211 | 4c/4GB/30GB | API :7000, orchestrator, brain, memory, voice |
| 204 | kaihara-dashboard | 192.168.1.212 | 1c/1GB/8GB | nginx static + proxy `/api` & `/ws` → core |
| 205 | kaihara-channels | 192.168.1.213 | 1c/1GB/8GB | Telegram bot runner (`deploy/channels_runner.py`) |
| 206 | kaihara-security | 192.168.1.214 | 2c/2GB/15GB | nmap, nikto, sqlmap, hydra, masscan |
| 207 | kaihara-kernel | 192.168.1.215 | 1c/1GB/10GB | kernel runner (`deploy/kernel_runner.py`) + backup |

CT dikekal: 100 (web), 101 (storage01), 104 (obsidian), 107 (9router), 201 (ai-stack/Ollama lama), 300 (mara).

## DNS — PENTING

DNS UDP dari dalam LXC adalah flaky (packet loss).
**Solusi:** dnsmasq berjalan di HOST (192.168.1.99:53) sebagai relay.
Semua CT mesti guna `nameserver 192.168.1.99`:

```bash
pct set <vmid> --nameserver "192.168.1.99" --searchdomain local
```

Config dnsmasq di host: `/etc/dnsmasq.d/kaihara.conf`.

## Setup CT 203 (kaihara-core)

```bash
# 1. Copy codebase (tanpa .git/venv/node_modules)
tar -C /opt -czf /tmp/kaihara.tar.gz --exclude='kaihara-os/.git' \
    --exclude='kaihara-os/venv' --exclude='kaihara-os/node_modules' kaihara-os
pct push 203 /tmp/kaihara.tar.gz /tmp/kaihara.tar.gz
pct exec 203 -- bash -c "cd /opt && tar xzf /tmp/kaihara.tar.gz"

# 2. Venv + dependencies
pct exec 203 -- bash -c "cd /opt/kaihara-os && python3 -m venv venv && \
  ./venv/bin/pip install -r requirements.txt edge-tts psutil"

# 3. .env (API keys)
pct push 203 /opt/kaihara-os/.env /opt/kaihara-os/.env

# 4. Ollama backup: host bind 0.0.0.0
#    /etc/systemd/system/ollama.service.d/override.conf:
#    [Service]
#    Environment="OLLAMA_HOST=0.0.0.0"
#    config.toml: base_url = "http://192.168.1.99:11434/v1"

# 5. Systemd service
#    /etc/systemd/system/kaihara.service (After=network-online.target)

# 6. Cron: Deep Dream + backup 3AM, GDrive sync 3:30AM
```

## Setup CT 204 (dashboard)

```bash
# Build dashboard di mana-mana, copy dist/ ke CT
pct push 204 dash-dist.tar.gz /tmp/dash-dist.tar.gz
pct exec 204 -- bash -c "mkdir -p /var/www/kaihara && tar xzf /tmp/dash-dist.tar.gz -C kaihara --strip-components=1"
# nginx config: root /var/www/kaihara; proxy /api -> http://192.168.1.211:7000
# Full config dalam panduan asal (proxy ws juga)
```

## Setup CT 205 (channels)

```bash
pct push 205 deploy/channels_runner.py /opt/channels_runner.py
pct exec 205 -- bash -c "apt install -y python3-venv && python3 -m venv /opt/venv && \
  /opt/venv/bin/pip install python-telegram-bot httpx"
# Env file /opt/.telegram.env:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_ALLOWED_IDS=8275355102
# systemd: kaihara-channels.service (EnvironmentFile=/opt/.telegram.env)
#   Environment=KAIHARA_API=http://192.168.1.211:7000
```

Nota: Telegram **disabled** dalam config.toml core (`[channel.telegram] enabled = false`)
untuk elak dua bot polling serentak. Bot hanya jalan di CT 205.

## Setup CT 206 (security tools)

```bash
pct exec 206 -- bash -c "apt update && apt install -y nmap nikto sqlmap hydra masscan"
```

## Setup CT 207 (kernel runner)

```bash
# Mount HDD + codebase read-only
pct set 207 --mp0 volume=/mnt/hdd-2tb-backup,mp=/mnt/kaihara-backup
pct set 207 -mp1 /opt/kaihara-os,mp=/mnt/kaihara-core,ro=1
pct push 207 deploy/kernel_runner.py /opt/kernel_runner.py
pct exec 207 -- apt install -y python3-httpx
# systemd: kaihara-kernel.service (KAIHARA_API=http://192.168.1.211:7000)
```

## GDrive (rclone di CT 203)

```bash
# Copy rclone.conf dari storage01 (CT 101):
pct exec 101 -- cat /root/.config/rclone/rclone.conf > rclone.conf
# Rename [mygdrive] -> [gdrive], BUANG line "team_drive =" yang kosong
pct push 203 rclone.conf /root/.config/rclone/rclone.conf

# JANGAN run pelbagai rclone serentak — config boleh corrupt bila token refresh.

# Cron 3:30AM di CT 203:
# rclone copy /opt/kaihara-os/obsidian-vault gdrive:kaihara-vault --create-empty-src-dirs
# rclone copy /opt/kaihara-os/data/kaihara.db gdrive:kaihara-backup
```

## Cloudflare Tunnel (di HOST)

`/root/.cloudflared/kaihara.yml`:

```yaml
tunnel: <uuid>
credentials-file: /root/.cloudflared/<uuid>.json
ingress:
  - hostname: kaihara-ai.nakhodacloud.top
    service: http://192.168.1.212:80      # CT 204
  - hostname: kaihara-api.nakhodacloud.top
    service: http://192.168.1.211:7000    # CT 203
  - service: http_status:404
```

## Arahan Operasi Harian

```bash
pct list                                        # status semua CT
pct exec 203 -- systemctl restart kaihara       # restart core
pct exec 205 -- systemctl restart kaihara-channels
pct exec 203 -- journalctl -u kaihara -f        # logs core
curl http://192.168.1.211:7000/api/status       # health check
```
