"""
Kaihara Kernel Runner — standalone for CT 207.
Runs system maintenance on THIS container:
- Daily 3AM: backup Kaihara core (via API) to /mnt/kaihara-backup
- Hourly: health check, report to core audit endpoint if reachable
- Keep-alive ping to core
"""

import os
import sys
import tarfile
import asyncio
import httpx
from datetime import datetime, time as dtime
from pathlib import Path

CORE_API = os.environ.get("KAIHARA_API", "http://192.168.1.211:7000")
BACKUP_DIR = Path("/mnt/kaihara-backup/kaihara")
KEEP_DAYS = 7

sys.path.insert(0, "/mnt/kaihara-core")  # shared codebase mount (read-only)


async def ping_core():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{CORE_API}/api/status")
            return r.status_code == 200
    except Exception:
        return False


def backup_core():
    """Pull a snapshot of core data via API and store locally."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = BACKUP_DIR / f"snapshot_{ts}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        import json
        with httpx.Client(timeout=120) as c:
            # Memory recall snapshot (top summaries)
            r = c.get(f"{CORE_API}/api/memory/recall", params={"q": "all", "limit": 100})
            (dest_dir / "memory_snapshot.json").write_text(r.text)
            # Goals + tasks + costs
            for name, path in [("goals", "/api/goals"),
                               ("tasks", "/api/planning/tasks"),
                               ("kernel", "/api/kernel/status"),
                               ("meta", "/api/meta/status")]:
                try:
                    (dest_dir / f"{name}.json").write_text(c.get(f"{CORE_API}{path}").text)
                except Exception:
                    pass
        # Compress
        tgz = BACKUP_DIR / f"kaihara_snapshot_{ts}.tar.gz"
        with tarfile.open(tgz, "w:gz") as tar:
            tar.add(dest_dir, arcname=f"snapshot_{ts}")
        # Remove raw dir + old backups
        import shutil
        shutil.rmtree(dest_dir)
        cutoff = datetime.now().timestamp() - KEEP_DAYS * 86400
        for f in BACKUP_DIR.glob("kaihara_snapshot_*.tar.gz"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
        print(f"[backup] OK -> {tgz.name}", flush=True)
    except Exception as e:
        print(f"[backup] ERROR: {e}", flush=True)


async def loop():
    last_backup_date = None
    last_hour = None
    print("Kaihara kernel runner started", flush=True)
    while True:
        now = datetime.now()
        alive = await ping_core()
        if not alive:
            print(f"[{now}] core unreachable", flush=True)
        # Daily backup at 3AM
        if now.hour == 3 and last_backup_date != now.date():
            backup_core()
            last_backup_date = now.date()
        # Hourly health log
        if now.hour != last_hour:
            cpu = open("/proc/loadavg").read().split()[0]
            mem = [l.split()[1] for l in open("/proc/meminfo") if l.startswith(("MemTotal", "MemAvailable"))]
            print(f"[health] load={cpu} mem={mem}", flush=True)
            last_hour = now.hour
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(loop())
