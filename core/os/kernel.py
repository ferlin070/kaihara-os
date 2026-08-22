"""
Kernel Manager - start/stop/status for all OS kernel agents.
The Agentic OS kernel: 7 agents that manage the system 24/7.
"""

import asyncio
from typing import Any

from core.os.base_os_agent import BaseOSAgent
from core.os.file_agent import FileAgent
from core.os.process_agent import ProcessAgent
from core.os.network_agent import NetworkAgent
from core.os.backup_agent import BackupAgent
from core.os.update_agent import UpdateAgent
from core.os.health_agent import HealthAgent
from core.os.cost_agent import CostAgent


class KernelManager:
    """Manage all OS kernel agents. The Agentic OS layer."""

    def __init__(self, config: dict, audit=None):
        self.config = config
        self.audit = audit
        os_cfg = config.get("os", {})
        self.agents: dict[str, BaseOSAgent] = {
            "file": FileAgent(os_cfg.get("file", {}), audit),
            "process": ProcessAgent(os_cfg.get("process", {}), audit),
            "network": NetworkAgent(os_cfg.get("network", {}), audit),
            "backup": BackupAgent(os_cfg.get("backup", {}), audit),
            "update": UpdateAgent(os_cfg.get("update", {}), audit),
            "health": HealthAgent(os_cfg.get("health", {}), audit),
            "cost": CostAgent(os_cfg.get("cost", {}), audit),
        }

    async def start_all(self) -> dict:
        """Start all kernel agents."""
        results = {}
        for name, agent in self.agents.items():
            results[name] = await agent.start()
        return results

    async def stop_all(self) -> dict:
        """Stop all kernel agents."""
        results = {}
        for name, agent in self.agents.items():
            results[name] = await agent.stop()
        return results

    async def start_agent(self, name: str) -> dict:
        """Start a specific agent."""
        agent = self.agents.get(name)
        if not agent:
            return {"error": f"Agent '{name}' not found"}
        return await agent.start()

    async def stop_agent(self, name: str) -> dict:
        """Stop a specific agent."""
        agent = self.agents.get(name)
        if not agent:
            return {"error": f"Agent '{name}' not found"}
        return await agent.stop()

    async def run_once(self, name: str) -> dict:
        """Run a specific agent once without starting loop."""
        agent = self.agents.get(name)
        if not agent:
            return {"error": f"Agent '{name}' not found"}
        return await agent.run_once()

    def status(self) -> dict:
        """Get status of all kernel agents."""
        return {name: agent.status()
                for name, agent in self.agents.items()}

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())

    def get_cost_agent(self) -> CostAgent:
        """Get the cost agent for recording usage."""
        return self.agents.get("cost")
