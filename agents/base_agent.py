"""
Base Agent — all agents inherit from this.
Loads SOUL.md identity, connects to memory, model router, tools.
"""

import os
import re
import json
from pathlib import Path
from typing import Any

from core.tools.web_tools import web_search, scrape_website, search_places

# Tasks matching these patterns get live web data injected
WEB_TRIGGER = re.compile(
    r"\b(cari|mencari|search|scrape|senarai|list|telefon|no\.|nombor|alamat|"
    r"address|email|emel|kedai|restoran|restaurant|bakery|perniagaan|"
    r"business|syarikat|company|pasaran|market|pesaing|competitor|"
    r"berita|news|harga|price|trend|review|google maps|maps)\b", re.I)
WEB_AGENTS = {"marketing", "research", "kaihara"}


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

    def __init__(self, config: dict, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, **kwargs):
        super().__init__(config=config, memory=memory,
                         model_router=model_router,
                         token_juice=token_juice,
                         approval_gate=approval_gate)

    @staticmethod
    def _gather_web_context(task: str) -> str:
        """Fetch live web data relevant to the task (RAG-lite)."""
        parts = []
        try:
            search = json.loads(web_search(task[:150], 6))
            results = search.get("results", [])
            if results:
                lines = [f"- {r['title']} | {r['url']}\n  {r['snippet']}"
                         for r in results]
                parts.append("[REAL-TIME WEB SEARCH RESULTS]\n"
                             + "\n".join(lines))
        except Exception:
            pass
        try:
            places = json.loads(search_places(task[:120], 8))
            pr = places.get("results", [])
            if pr:
                plines = []
                for p in pr[:8]:
                    bits = [p.get("name", ""), p.get("address", ""),
                            p.get("snippet", "")]
                    plines.append("- " + " | ".join(b for b in bits if b))
                parts.append("[PLACE/BUSINESS DATA]\n" + "\n".join(plines))
        except Exception:
            pass
        return "\n\n".join(parts)

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute task using SOUL.md personality + live web tools."""
        try:
            # Build context from memory if available
            memory_context = ""
            if self.memory:
                memory_context = self.memory.super_context(task)

            # Live web injection for research/marketing tasks
            web_context = ""
            if self.AGENT_TYPE in WEB_AGENTS and WEB_TRIGGER.search(task):
                web_context = self._gather_web_context(task)

            full_context = "\n\n".join(
                x for x in (memory_context, web_context) if x)

            # Use think() which applies SOUL.md as system prompt
            response = await self.think(task, context=full_context)

            # Store result in memory
            if self.memory:
                self.memory.store(
                    f"Agent {self.AGENT_TYPE} completed: {task[:100]}",
                    source="agent",
                    agent=self.AGENT_TYPE,
                )

            return {
                "agent": self.AGENT_TYPE,
                "text": response,
                "web_used": bool(web_context),
                "status": "ok"
            }
        except Exception as e:
            return {
                "agent": self.AGENT_TYPE,
                "text": f"Error: {str(e)}",
                "status": "error"
            }
