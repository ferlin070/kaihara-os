"""
Health Agent — monitor system health: CPU, RAM, disk, temperature, load.
Upgraded: per-core CPU, swap, disk I/O, system uptime, Windows compatible.
"""

import os
import time
import psutil
from core.os.base_os_agent import BaseOSAgent


class HealthAgent(BaseOSAgent):
    """Monitor system health metrics."""

    AGENT_TYPE = "health"
    INTERVAL = 60  # Every 60 seconds

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self._boot_time = psutil.boot_time()
        self._prev_disk_io = None
        self._prev_net_io = None
        self._prev_time = None

    def _get_alerts(self, cpu, ram, disk, temp) -> list:
        alerts = []
        if cpu > 90:
            alerts.append({"action": "high_cpu", "severity": "high",
                           "message": f"CPU at {cpu:.1f}%"})
        if ram > 90:
            alerts.append({"action": "high_ram", "severity": "high",
                           "message": f"RAM at {ram:.1f}%"})
        if disk > 90:
            alerts.append({"action": "high_disk", "severity": "high",
                           "message": f"Disk at {disk:.1f}%"})
        if temp and temp > 80:
            alerts.append({"action": "high_temp", "severity": "high",
                           "message": f"Temperature at {temp:.0f}C"})
        return alerts

    async def run_task(self) -> dict:
        # CPU
        cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
        cpu_avg = sum(cpu_per_core) / len(cpu_per_core) if cpu_per_core else 0

        # Load average (Linux/Mac only)
        try:
            load = list(os.getloadavg())
        except (AttributeError, OSError):
            load = [cpu_avg / 100 * (psutil.cpu_count() or 1), 0, 0]

        # Memory
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage("/")

        # Disk I/O rate
        disk_io = None
        now = time.time()
        try:
            current_io = psutil.disk_io_counters()
            if self._prev_disk_io and self._prev_time:
                dt = now - self._prev_time
                if dt > 0:
                    disk_io = {
                        "read_bytes_per_sec": round(
                            (current_io.read_bytes - self._prev_disk_io.read_bytes) / dt
                        ),
                        "write_bytes_per_sec": round(
                            (current_io.write_bytes - self._prev_disk_io.write_bytes) / dt
                        ),
                    }
            self._prev_disk_io = current_io
        except Exception:
            pass

        # Network rate
        net_io = None
        try:
            current_net = psutil.net_io_counters()
            if self._prev_net_io and self._prev_time:
                dt = now - self._prev_time
                if dt > 0:
                    net_io = {
                        "sent_bytes_per_sec": round(
                            (current_net.bytes_sent - self._prev_net_io.bytes_sent) / dt
                        ),
                        "recv_bytes_per_sec": round(
                            (current_net.bytes_recv - self._prev_net_io.bytes_recv) / dt
                        ),
                    }
            self._prev_net_io = current_net
        except Exception:
            pass

        self._prev_time = now

        # Temperature
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            for entries in temps.values():
                if entries:
                    temp = entries[0].current
                    break
        except Exception:
            pass

        # Uptime
        uptime_sec = int(time.time() - self._boot_time)

        # Alerts
        alerts = self._get_alerts(cpu_avg, ram.percent, disk.percent, temp)

        return {
            "cpu": {
                "percent": round(cpu_avg, 1),
                "per_core": [round(c, 1) for c in cpu_per_core],
                "count": psutil.cpu_count(),
            },
            "ram": {
                "total_gb": round(ram.total / (1024**3), 1),
                "used_gb": round(ram.used / (1024**3), 1),
                "available_gb": round(ram.available / (1024**3), 1),
                "percent": ram.percent,
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 1),
                "used_gb": round(swap.used / (1024**3), 1),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": disk.percent,
            },
            "disk_io": disk_io,
            "network_io": net_io,
            "temperature": temp,
            "load": {
                "1m": round(load[0], 2),
                "5m": round(load[1], 2),
                "15m": round(load[2], 2),
            },
            "uptime_seconds": uptime_sec,
            "alerts": alerts,
        }
