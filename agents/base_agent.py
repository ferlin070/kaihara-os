"""
Base Agent — all agents inherit from this.
Loads SOUL.md identity, connects to memory, model router, tools.
"""

import os
import re
from pathlib import Path
from typing import Any


class BaseAgent:
    """Base class for all Kaihara agents. Each agent has a SOUL.md."""

    AGENT_TYPE = "base"
    SOUL_FILE = "base.md"

    def __init__(self, config: dict, memory=None, model_router=None,
                 token_juice=None, approval_gate=None):
        self.config = config
        self.memory = memory
        self.model = model_router
        self.token_juice = token_juice
        self.approval_gate = approval_gate
        self.soul = self._load_soul()
        self.tools: dict[str, Any] = {}
        self.skills: list[str] = []

    def _load_soul(self) -> dict[str, str]:
        """Load SOUL.md — agent identity, personality, capabilities."""
        soul_dir = Path(self.config.get("soul_dir", "config/soul"))
        soul_path = soul_dir / self.SOUL_FILE
        if not soul_path.exists():
            return {"identity": "base agent", "system_prompt": ""}
        content = soul_path.read_text(encoding="utf-8")
        return {
            "raw": content,
            "identity": self._extract_section(content, "Identity"),
            "personality": self._extract_section(content, "Personality"),
            "system_prompt": content,
        }

    def _extract_section(self, content: str, section: str) -> str:
        pattern = rf"## {section}\s*\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute a task. Override in subclasses."""
        raise NotImplementedError("Subclass must implement run()")

    async def think(self, prompt: str, context: str = "") -> str:
        """Send prompt to LLM with SOUL.md system prompt."""
        if not self.model:
            return "[no model configured]"
        system = self.soul.get("system_prompt", "You are a helpful agent.")
        # Don't compress SOUL.md — it's the personality
        if context:
            prompt = f"{context}\n\n---\n\n{prompt}"
        response = await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response

    def register_tool(self, name: str, func):
        self.tools[name] = func

    async def use_tool(self, name: str, **kwargs) -> Any:
        """Use a registered tool."""
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found"}
        return await self.tools[name](**kwargs)

    def load_skill(self, skill_name: str) -> str | None:
        """Load a SKILL.md file by name."""
        skills_dir = Path(self.config.get("skills_dir", "config/skills"))
        skill_path = skills_dir / f"{skill_name}.md"
        if skill_path.exists():
            content = skill_path.read_text(encoding="utf-8")
            self.skills.append(skill_name)
            return content
        return None

    def status(self) -> dict:
        return {
            "agent_type": self.AGENT_TYPE,
            "soul_loaded": bool(self.soul.get("raw")),
            "tools": list(self.tools.keys()),
            "skills": self.skills,
        }


class GenericAgent(BaseAgent):
    """Generic agent that uses SOUL.md as personality."""

    def __init__(self, agent_type: str, soul_file: str, **kwargs):
        self.AGENT_TYPE = agent_type
        self.SOUL_FILE = soul_file
        super().__init__(**kwargs)

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute task using SOUL.md personality."""
        try:
            # Build context from memory if available
            memory_context = ""
            if self.memory:
                memory_context = self.memory.super_context(task)

            # Use think() which applies SOUL.md as system prompt
            response = await self.think(task, context=memory_context)

            # Store result in memory
            if self.memory:
                self.memory.store(
                    f"Agent {self.AGENT_TYPE} completed: {task[:100]}",
                    source="agent",
                    agent=self.AGENT_TYPE,
                    topic=self.AGENT_TYPE
                )

            return {
                "agent": self.AGENT_TYPE,
                "text": response,
                "status": "ok"
            }
        except Exception as e:
            return {
                "agent": self.AGENT_TYPE,
                "text": f"Error: {str(e)}",
                "status": "error"
            }
