#!/bin/bash
# Kaihara OS cron setup

# Daily maintenance (Deep Dream + backup) at 3AM
(crontab -l 2>/dev/null; echo "0 3 * * * cd /opt/kaihara-os && /opt/kaihara-os/venv/bin/python scripts/daily_maintenance.py >> /var/log/kaihara-maintenance.log 2>&1") | crontab -

# Kernel keep-alive check every 5 min
(crontab -l 2>/dev/null; echo "*/5 * * * * curl -s -X POST http://localhost:7000/api/kernel/start > /dev/null 2>&1") | crontab -

echo "Cron jobs installed:"
crontab -l | grep kaihara
