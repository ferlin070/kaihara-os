"""
DaemonManager - Wraps KernelManager with watchdog, auto-restart,
process registry, and health monitoring.

Provides a supervisory layer over the 7 kernel agents.
"""

import asyncio
import time
import psutil
from datetime import datetime
from typing import Any

from core.os.kernel import KernelManager


class DaemonManager:
    """Supervisory daemon manager with watchdog and auto-restart."""

    def __init__(self, kernel: KernelManager, config: dict = None):
        self.kernel = kernel
        self.config = config or {}
        self._watchdog_running = False
        self._watchdog_task = None
        self._watchdog_interval = self.config.get("watchdog_interval", 30)
        self._max_restarts = self.config.get("max_restarts", 3)
        self._restart_counts: dict[str, int] = {}
        self._restart_history: list[dict] = []
        self._process_info: dict[str, Any] = {}
        self._service_registry: list[dict] = []

    async def start_watchdog(self) -> dict:
        """Start the watchdog that monitors and auto-restarts crashed agents."""
        if self._watchdog_running:
            return {"status": "already_running"}
        self._watchdog_running = True
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        return {"status": "started", "interval": self._watchdog_interval}

    async def stop_watchdog(self) -> dict:
        """Stop the watchdog."""
        self._watchdog_running = False
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        return {"status": "stopped"}

    async def _watchdog_loop(self):
        """Watchdog loop: check agent health and restart if needed."""
        while self._watchdog_running:
            try:
                status = self.kernel.status()
                for name, info in status.items():
                    if info.get("running") and info.get("error"):
                        # Agent is running but errored — attempt restart
                        restarts = self._restart_counts.get(name, 0)
                        if restarts < self._max_restarts:
                            await self._restart_agent(name, info)
                        else:
                            # Max restarts exceeded — stop the agent
                            await self.kernel.stop_agent(name)
                            self._restart_history.append({
                                "agent": name,
                                "action": "stopped_max_restarts",
                                "error": info.get("error"),
                                "time": datetime.now().isoformat(),
                            })
            except Exception as e:
                self._restart_history.append({
                    "agent": "watchdog",
                    "action": "watchdog_error",
                    "error": str(e),
                    "time": datetime.now().isoformat(),
                })
            await asyncio.sleep(self._watchdog_interval)

    async def _restart_agent(self, name: str, prev_info: dict):
        """Restart a crashed agent."""
        self._restart_counts[name] = self._restart_counts.get(name, 0) + 1
        self._restart_history.append({
            "agent": name,
            "action": "restart",
            "attempt": self._restart_counts[name],
            "error": prev_info.get("error"),
            "time": datetime.now().isoformat(),
        })
        await self.kernel.stop_agent(name)
        await asyncio.sleep(2)  # Brief cooldown
        await self.kernel.start_agent(name)

    async def restart_agent(self, name: str) -> dict:
        """Manually restart a specific agent."""
        self._restart_counts[name] = 0  # Reset count on manual restart
        await self.kernel.stop_agent(name)
        await asyncio.sleep(1)
        result = await self.kernel.start_agent(name)
        self._restart_history.append({
            "agent": name,
            "action": "manual_restart",
            "time": datetime.now().isoformat(),
        })
        return result

    async def restart_all(self) -> dict:
        """Restart all agents."""
        results = {}
        for name in self.kernel.agents:
            results[name] = await self.restart_agent(name)
        return results

    def get_process_info(self) -> dict:
        """Get system process info."""
        try:
            p = psutil.Process()
            mem = p.memory_info()
            return {
                "pid": p.pid,
                "cpu_percent": p.cpu_percent(interval=0.1),
                "memory_mb": round(mem.rss / (1024 * 1024), 1),
                "threads": p.num_threads(),
                "uptime_seconds": time.time() - p.create_time(),
                "status": p.status(),
                "cpu_affinity": len(p.cpu_affinity()),
            }
        except Exception:
            return {"error": "Could not get process info"}

    def get_service_registry(self) -> list[dict]:
        """Get registry of all managed services."""
        services = []
        for name, agent in self.kernel.agents.items():
            agent_status = agent.status()
            services.append({
                "name": name,
                "type": agent.AGENT_TYPE,
                "running": agent_status.get("running", False),
                "interval": agent.INTERVAL,
                "last_run": agent_status.get("last_run"),
                "run_count": agent_status.get("run_count", 0),
                "error": agent_status.get("error"),
                "restarts": self._restart_counts.get(name, 0),
            })
        return services

    def status(self) -> dict:
        """Full daemon manager status."""
        kernel_status = self.kernel.status()
        running = sum(1 for s in kernel_status.values() if s.get("running"))
        errored = sum(1 for s in kernel_status.values() if s.get("error"))
        total = len(kernel_status)

        return {
            "watchdog_running": self._watchdog_running,
            "agents": {
                "total": total,
                "running": running,
                "errored": errored,
                "stopped": total - running,
            },
            "process": self.get_process_info(),
            "services": self.get_service_registry(),
            "restart_history": self._restart_history[-20:],  # Last 20
            "restart_counts": dict(self._restart_counts),
        }

    def get_alerts(self) -> list[dict]:
        """Get all active alerts from agents."""
        alerts = []
        for name, agent in self.kernel.agents.items():
            info = agent.status()
            if info.get("error"):
                alerts.append({
                    "agent": name,
                    "type": "error",
                    "message": info["error"],
                    "severity": "critical",
                })
            if not info.get("running"):
                alerts.append({
                    "agent": name,
                    "type": "stopped",
                    "message": f"{name} agent is not running",
                    "severity": "warning",
                })
        return alerts
