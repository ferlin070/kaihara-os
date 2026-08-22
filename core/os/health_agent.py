"""
Health Agent - monitor uptime, disk space, temperature, alert.
"""

import psutil
import os
import socket
import time
from datetime import datetime

from core.os.base_os_agent import BaseOSAgent


class HealthAgent(BaseOSAgent):
    """Monitor system health: CPU, RAM, disk, temp."""

    AGENT_TYPE = "os_health"
    INTERVAL = 60  # every minute

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.cpu_threshold = config.get("cpu_threshold", 90)
        self.ram_threshold = config.get("ram_threshold", 90)
        self.disk_threshold = config.get("disk_threshold", 90)
        self.temp_threshold = config.get("temp_threshold", 80)
        self._start_time = time.time()

    async def run_task(self) -> dict:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        temp = self._get_temperature()
        load = self._get_load_average()

        alerts = []
        if cpu > self.cpu_threshold:
            alerts.append({"action": "cpu_high", "severity": "warning",
                            "value": cpu})
        if ram.percent > self.ram_threshold:
            alerts.append({"action": "ram_high", "severity": "warning",
                            "value": ram.percent})
        if disk.percent > self.disk_threshold:
            alerts.append({"action": "disk_high", "severity": "critical",
                            "value": disk.percent})
        if temp and temp > self.temp_threshold:
            alerts.append({"action": "temp_high", "severity": "critical",
                            "value": temp})

        return {
            "agent": self.AGENT_TYPE,
            "cpu_percent": cpu,
            "ram": {"total_gb": round(ram.total / 1e9, 1),
                    "used_gb": round(ram.used / 1e9, 1),
                    "percent": ram.percent},
            "disk": {"total_gb": round(disk.total / 1e9, 1),
                     "used_gb": round(disk.used / 1e9, 1),
                     "percent": disk.percent},
            "temperature": temp,
            "load_average": load,
            "uptime_seconds": round(time.time() - self._start_time),
            "alerts": alerts,
        }

    def _get_temperature(self) -> float | None:
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
        except (AttributeError, Exception):
            pass
        return None

    def _get_load_average(self) -> float | None:
        try:
            import os
            load = os.getloadavg()
            return {"1min": load[0], "5min": load[1], "15min": load[2]}
        except (AttributeError, OSError):
            return None

    def status(self) -> dict:
        return {**super().status(),
                "thresholds": {
                    "cpu": self.cpu_threshold,
                    "ram": self.ram_threshold,
                    "disk": self.disk_threshold,
                },
                "last_result": self._last_result}
