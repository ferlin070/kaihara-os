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
from core.tools.pdf_generator import generate_pdf_report
from core.tools.notify_tools import send_telegram_message, send_telegram_document, telegram_status

# Tasks matching these patterns get live web data injected
WEB_TRIGGER = re.compile(
    r"\b(cari|mencari|search|scrape|senarai|list|telefon|no\.|nombor|alamat|"
    r"address|email|emel|kedai|restoran|restaurant|bakery|perniagaan|"
    r"business|syarikat|company|pasaran|market|pesaing|competitor|"
    r"berita|news|harga|price|trend|review|google maps|maps)\b", re.I)
WEB_AGENTS = {"marketing", "research", "kaihara"}

# PDF / report triggers
PDF_TRIGGER = re.compile(
    r"\b(pdf|report|laporan|dokumen|document|Invoice|resume|borang|form)\b", re.I)
PDF_AGENTS = {"kaihara", "marketing", "research", "deploy", "editor", "meta", "security"}

# Telegram / notification triggers
TG_TRIGGER = re.compile(
    r"\b(hantar|mesej|message|notify|notification|bagitahu|inform)"
    r"[^\n]{0,40}\btelegram\b|\btelegram\b[^\n]{0,40}\b"
    r"(hantar|mesej|message|notify|bagitahu)\b", re.I | re.S)


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
        self._skill_registry = None

    def set_skill_registry(self, registry):
        """Set the skill registry for skill loading."""
        self._skill_registry = registry

    def _find_relevant_skills(self, task: str) -> list[str]:
        """Find skills relevant to the task based on keywords."""
        task_lower = task.lower()
        relevant = []

        # Keyword-to-skill mapping
        skill_keywords = {
            "pentest": ["staged-pentest", "recon-automation", "security-killchain"],
            "scan": ["staged-pentest", "recon-automation"],
            "security": ["security-killchain", "staged-pentest", "poc-validation"],
            "deploy": ["approval-gate"],
            "animation": ["animation-first", "gsap-skills", "animated-components"],
            "design": ["design-dna", "impeccable-design-rules", "anti-slop-design"],
            "ui": ["tailwind-shadcn-motion", "zero-dep-components"],
            "test": ["tdd-engineering"],
            "report": ["token-compression-output"],
            "memory": ["layered-memory"],
            "workflow": ["sprint-workflow", "task-kanban-workspace"],
            "code": ["dead-code-elimination", "code-templates-frontend"],
            "3d": ["threejs-skills"],
            "motion": ["gsap-skills", "motion-design"],
            "form": ["visual-form-builder"],
            "markdown": ["token-compression-output"],
        }

        for keyword, skill_ids in skill_keywords.items():
            if keyword in task_lower:
                relevant.extend(skill_ids)

        # Also check skill registry if available
        if self._skill_registry:
            try:
                all_skills = self._skill_registry.list_skills()
                for skill in all_skills:
                    tags = skill.get("tags", [])
                    name = skill.get("name", "").lower()
                    desc = skill.get("description", "").lower()
                    skill_id = skill.get("id", "")

                    # Check if any tag matches task keywords
                    task_words = set(task_lower.split())
                    tag_words = set(t.lower() for t in tags)

                    if task_words & tag_words and skill_id not in relevant:
                        relevant.append(skill_id)
                    elif any(t in task_lower for t in tags) and skill_id not in relevant:
                        relevant.append(skill_id)
            except Exception:
                pass

        return list(set(relevant))[:3]  # Max 3 skills

    def _load_skills_content(self, skill_ids: list[str]) -> str:
        """Load content from multiple skills."""
        contents = []
        for skill_id in skill_ids:
            content = self.load_skill(skill_id)
            if content:
                # Extract key sections only (not full file)
                lines = content.split("\n")
                key_sections = []
                in_section = False
                for line in lines:
                    if line.startswith("## ") or line.startswith("---"):
                        in_section = True
                        key_sections.append(line)
                    elif in_section and line.strip():
                        key_sections.append(line)
                    elif line.startswith("## "):
                        in_section = False

                if key_sections:
                    skill_text = "\n".join(key_sections[:20])
                    if len(skill_text) > 2000:
                        skill_text = skill_text[:2000] + "\n[SKILL TRUNCATED]"
                    contents.append(f"[SKILL: {skill_id}]\n" + skill_text)

        return "\n\n".join(contents)

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
        """Execute task using SOUL.md personality + skills + live web tools."""
        try:
            # Build context from memory if available
            memory_context = ""
            if self.memory:
                memory_context = self.memory.super_context(task)

            # Load relevant skills
            skill_context = ""
            relevant_skills = self._find_relevant_skills(task)
            if relevant_skills:
                skill_context = self._load_skills_content(relevant_skills)

            # Live web injection for research/marketing tasks
            web_context = ""
            if self.AGENT_TYPE in WEB_AGENTS and WEB_TRIGGER.search(task):
                web_context = self._gather_web_context(task)

            full_context = "\n\n".join(
                x for x in (skill_context, memory_context, web_context) if x)
            # Hard cap on context to prevent token explosion
            if len(full_context) > 6000:
                full_context = full_context[:6000] + "\n[CONTEXT TRUNCATED]"

            # Telegram send: only for pure messaging tasks (skip if PDF requested)
            # Research/web tasks: skip (CommandCenter delivers final answer)
            if TG_TRIGGER.search(task) and not WEB_TRIGGER.search(task) and not PDF_TRIGGER.search(task):
                st = telegram_status()
                if st.get("configured"):
                    tg_result = send_telegram_message(f"Kaihara: {task}")
                    if tg_result.get("ok"):
                        chat_ids = ", ".join(
                            str(d["chat_id"]) for d in tg_result["details"])
                        response_text = (
                            f"✅ Mesej dihantar ke Telegram "
                            f"({st.get('bot_username', 'bot')}):\n\n"
                            f"\"{task}\"\n\nDihantar ke chat ID: {chat_ids}")
                        if self.memory:
                            self.memory.store(
                                f"Telegram sent: {task[:80]}",
                                source="agent", agent=self.AGENT_TYPE)
                        return {
                            "agent": self.AGENT_TYPE,
                            "text": response_text,
                            "telegram": tg_result,
                            "status": "ok",
                        }
                    full_context += ("\n\n[TELEGRAM ERROR] Gagal hantar: "
                                     + str(tg_result))


            # Use think() which applies SOUL.md as system prompt
            response = await self.think(task, context=full_context)


            # PDF generation: generate branded report and send to Telegram
            if PDF_TRIGGER.search(task) and self.AGENT_TYPE in PDF_AGENTS:
                try:
                    from core.tools.pdf_generator import generate_pdf_report

                    # Parse response into structured content blocks
                    blocks = []
                    lines = response.split("\n")
                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            blocks.append({"type": "spacer", "height": 3*mm})
                        elif stripped.startswith("# "):
                            blocks.append({"type": "heading", "text": stripped[2:], "level": 2})
                        elif stripped.startswith("## "):
                            blocks.append({"type": "heading", "text": stripped[3:], "level": 3})
                        elif stripped.startswith("### "):
                            blocks.append({"type": "heading", "text": stripped[4:], "level": 4})
                        elif stripped.startswith("| ") and "---" not in stripped:
                            # Parse table rows
                            cells = [c.strip() for c in stripped.split("|")[1:-1]]
                            if not blocks or blocks[-1].get("type") != "table":
                                blocks.append({"type": "table", "headers": cells, "rows": []})
                            else:
                                blocks[-1]["rows"].append(cells)
                        elif stripped.startswith("- ") or stripped.startswith("* "):
                            if not blocks or blocks[-1].get("type") != "bullet":
                                blocks.append({"type": "bullet", "items": []})
                            blocks[-1]["items"].append(stripped[2:])
                        elif stripped.startswith("> "):
                            blocks.append({"type": "highlight", "text": stripped[2:]})
                        elif stripped.startswith("---"):
                            blocks.append({"type": "divider"})
                        else:
                            blocks.append({"type": "paragraph", "text": stripped})

                    if not blocks:
                        blocks = [{"type": "paragraph", "text": response}]

                    # Clean up empty tables
                    blocks = [b for b in blocks if not (b.get("type") == "table" and not b.get("rows"))]

                    pdf_path = generate_pdf_report(
                        title=task[:60],
                        content=blocks,
                        subtitle=f"Route: {self.AGENT_TYPE} | Kaihara OS",
                        output_filename=f"report_{self.AGENT_TYPE}"
                    )
                    # Send to Telegram
                    tg_status = telegram_status()
                    if tg_status.get("configured"):
                        doc_result = send_telegram_document(
                            file_path=pdf_path,
                            caption=f"📊 {task[:100]}"
                        )
                        if doc_result.get("ok"):
                            return {
                                "agent": self.AGENT_TYPE,
                                "text": f"✅ PDF telah dijana dan dihantar ke Telegram:\n{pdf_path}",
                                "pdf_path": pdf_path,
                                "telegram": doc_result,
                                "status": "ok",
                            }
                except Exception as e:
                    import traceback
                    full_context += f"\n[PDF ERROR] {traceback.format_exc()}"

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
                "skills_used": relevant_skills,
                "web_used": bool(web_context),
                "status": "ok"
            }
        except Exception as e:
            return {
                "agent": self.AGENT_TYPE,
                "text": f"Error: {str(e)}",
                "status": "error"
            }
