"""
Base OS Agent - abstract base for all kernel agents.
Each OS agent runs on a schedule (interval) and reports status.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseOSAgent(ABC):
    """Abstract base for OS kernel agents. Runs on interval."""

    AGENT_TYPE = "os_base"
    INTERVAL = 300  # 5 minutes default

    def __init__(self, config: dict | None = None, audit=None):
        self.config = config or {}
        self.audit = audit
        self._running = False
        self._task = None
        self._last_run = None
        self._last_result = None
        self._error = None
        self._run_count = 0

    async def start(self) -> dict:
        """Start the agent loop."""
        if self._running:
            return {"status": "already_running", "agent": self.AGENT_TYPE}
        self._running = True
        self._task = asyncio.create_task(self._loop())
        return {"status": "started", "agent": self.AGENT_TYPE}

    async def stop(self) -> dict:
        """Stop the agent loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        return {"status": "stopped", "agent": self.AGENT_TYPE}

    async def _loop(self):
        """Main loop: run task on interval."""
        while self._running:
            try:
                self._last_run = datetime.now().isoformat()
                result = await self.run_task()
                self._last_result = result
                self._run_count += 1
                self._error = None
                if self.audit and result and result.get("alerts"):
                    for alert in result["alerts"]:
                        self.audit.log(
                            self.AGENT_TYPE, alert.get("action", "monitor"),
                            alert, None, alert.get("severity", "info")
                        )
            except Exception as e:
                self._error = str(e)
            await asyncio.sleep(self.INTERVAL)

    @abstractmethod
    async def run_task(self) -> dict:
        """Run the agent task. Override in subclass."""
        pass

    async def run_once(self) -> dict:
        """Run task once without starting the loop."""
        return await self.run_task()

    def status(self) -> dict:
        return {
            "agent": self.AGENT_TYPE,
            "running": self._running,
            "interval": self.INTERVAL,
            "last_run": self._last_run,
            "run_count": self._run_count,
            "error": self._error,
        }
