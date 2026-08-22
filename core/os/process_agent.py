"""
Process Agent - schedule tasks, kill zombies, prioritize CPU.
"""

import psutil
import os
import subprocess
from datetime import datetime

from core.os.base_os_agent import BaseOSAgent


class ProcessAgent(BaseOSAgent):
    """Manage processes: kill zombies, monitor CPU."""

    AGENT_TYPE = "os_process"
    INTERVAL = 120  # 2 minutes

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.zombie_threshold = config.get("zombie_threshold", 5)
        self.cpu_threshold = config.get("cpu_threshold", 90)

    async def run_task(self) -> dict:
        zombies = self._find_zombies()
        cpu_hogs = self._find_cpu_hogs()
        alerts = []
        if len(zombies) > self.zombie_threshold:
            alerts.append({
                "action": "zombie_count_high",
                "severity": "warning",
                "count": len(zombies),
            })
        for hog in cpu_hogs:
            alerts.append({
                "action": "cpu_high",
                "severity": "warning",
                "pid": hog["pid"],
                "name": hog["name"],
                "cpu": hog["cpu"],
            })
        return {
            "agent": self.AGENT_TYPE,
            "zombie_count": len(zombies),
            "zombies": zombies[:10],
            "cpu_hogs": cpu_hogs[:5],
            "process_count": len(psutil.pids()),
            "alerts": alerts,
        }

    def _find_zombies(self) -> list[dict]:
        """Find zombie processes."""
        zombies = []
        for p in psutil.process_iter(["pid", "name", "status"]):
            try:
                if p.info["status"] == psutil.STATUS_ZOMBIE:
                    zombies.append({
                        "pid": p.info["pid"],
                        "name": p.info["name"],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return zombies

    def _find_cpu_hogs(self) -> list[dict]:
        """Find processes using too much CPU."""
        hogs = []
        for p in psutil.process_iter(
            ["pid", "name", "cpu_percent"]
        ):
            try:
                cpu = p.info["cpu_percent"] or 0
                if cpu > self.cpu_threshold:
                    hogs.append({
                        "pid": p.info["pid"],
                        "name": p.info["name"],
                        "cpu": round(cpu, 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(hogs, key=lambda x: x["cpu"], reverse=True)

    def status(self) -> dict:
        return {**super().status(),
                "last_result": self._last_result}
