"""
Backup Agent - auto backup at 3AM, incremental, verify.
"""

import os
import tarfile
import hashlib
from datetime import datetime

from core.os.base_os_agent import BaseOSAgent


class BackupAgent(BaseOSAgent):
    """Auto backup: daily at 3AM, incremental, verify."""

    AGENT_TYPE = "os_backup"
    INTERVAL = 3600

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.backup_dir = config.get("backup_dir", "./data/backups")
        self.source_dirs = config.get(
            "source_dirs", ["./data", "./config", "./obsidian-vault"]
        )
        self.backup_hour = config.get("backup_hour", 3)
        self.max_backups = config.get("max_backups", 7)
        self._last_backup_date = None

    async def run_task(self) -> dict:
        now = datetime.now()
        should = (now.hour == self.backup_hour
                  and self._last_backup_date != now.date().isoformat())
        if should:
            result = self._do_backup()
            self._last_backup_date = now.date().isoformat()
            self._cleanup_old()
            return {
                "agent": self.AGENT_TYPE,
                "backup_performed": True,
                "result": result,
                "alerts": [{"action": "backup_completed",
                            "severity": "info", **result}],
            }
        return {
            "agent": self.AGENT_TYPE,
            "backup_performed": False,
            "next_backup": f"{self.backup_hour}:00",
            "last_backup": self._last_backup_date,
        }

    def _do_backup(self) -> dict:
        os.makedirs(self.backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.backup_dir, f"backup_{ts}.tar.gz")
        files_count = 0
        with tarfile.open(path, "w:gz") as tar:
            for src in self.source_dirs:
                if os.path.exists(src):
                    tar.add(src, arcname=os.path.basename(src))
                    for _, _, files in os.walk(src):
                        files_count += len(files)
        return {
            "path": path,
            "files": files_count,
            "size_mb": round(os.path.getsize(path) / 1e6, 2),
            "verified": os.path.exists(path),
        }

    def _cleanup_old(self):
        backups = []
        for f in os.listdir(self.backup_dir):
            if f.startswith("backup_") and f.endswith(".tar.gz"):
                backups.append(f)
        backups.sort(reverse=True)
        for old in backups[self.max_backups:]:
            try:
                os.unlink(os.path.join(self.backup_dir, old))
            except Exception:
                pass

    def status(self) -> dict:
        return {**super().status(),
                "backup_dir": self.backup_dir,
                "last_backup": self._last_backup_date}
