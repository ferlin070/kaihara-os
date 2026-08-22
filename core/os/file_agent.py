"""
File Agent - organize files, clean temp, dedupe, auto-tag.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

from core.os.base_os_agent import BaseOSAgent


class FileAgent(BaseOSAgent):
    """Manage filesystem: organize, clean, dedupe."""

    AGENT_TYPE = "os_file"
    INTERVAL = 600  # 10 minutes

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.temp_dirs = config.get("temp_dirs", ["./data/tmp", "./tmp"])
        self.max_temp_age_hours = config.get("max_temp_age_hours", 24)
        self.data_dir = config.get("data_dir", "./data")

    async def run_task(self) -> dict:
        cleaned = self._clean_temp()
        stats = self._disk_usage()
        duplicates = self._find_duplicates()
        return {
            "agent": self.AGENT_TYPE,
            "temp_cleaned": cleaned,
            "disk_usage": stats,
            "duplicates_found": len(duplicates),
            "alerts": [
                {"action": "temp_cleaned", "severity": "info",
                 "files": cleaned}
            ] if cleaned else [],
        }

    def _clean_temp(self) -> int:
        """Clean files older than max_temp_age_hours in temp dirs."""
        cleaned = 0
        cutoff = datetime.now() - timedelta(hours=self.max_temp_age_hours)
        for temp_dir in self.temp_dirs:
            p = Path(temp_dir)
            if not p.exists():
                continue
            for f in p.rglob("*"):
                if f.is_file():
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime < cutoff:
                            f.unlink()
                            cleaned += 1
                    except Exception:
                        continue
        return cleaned

    def _disk_usage(self) -> dict:
        """Get disk usage stats."""
        try:
            stat = os.statvfs(self.data_dir)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            return {
                "total_gb": round(total / 1e9, 2),
                "used_gb": round(used / 1e9, 2),
                "free_gb": round(free / 1e9, 2),
                "percent": round(used / total * 100, 1) if total else 0,
            }
        except Exception:
            return {"error": "could not get disk usage"}

    def _find_duplicates(self) -> list[dict]:
        """Find duplicate files by hash in data dir."""
        hashes: dict[str, list[str]] = {}
        data_path = Path(self.data_dir)
        if not data_path.exists():
            return []
        for f in data_path.rglob("*"):
            if f.is_file() and f.stat().st_size < 10 * 1024 * 1024:
                try:
                    h = hashlib.md5(
                        f.read_bytes()
                    ).hexdigest()
                    hashes.setdefault(h, []).append(str(f))
                except Exception:
                    continue
        return [
            {"hash": h, "files": paths}
            for h, paths in hashes.items()
            if len(paths) > 1
        ]

    def status(self) -> dict:
        return {**super().status(),
                "temp_dirs": self.temp_dirs,
                "last_result": self._last_result}
