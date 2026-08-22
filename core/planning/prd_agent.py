"""
PRD Agent — generate Product Requirements Document from idea.
Inspired by Ngoding Pake AI pipeline: Idea → PRD → Specs → Tasks → Code → Deploy
"""

import re
from pathlib import Path
from datetime import datetime


PRD_TEMPLATE = """# PRD: {title}

## Overview
{overview}

## Problem Statement
{problem}

## Target Users
{users}

## Features
{features}

## Tech Stack
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Frontend: React + Tailwind
- Auth: JWT
- Deployment: Docker / Proxmox LXC

## Database Schema
{schema}

## API Endpoints
{endpoints}

## User Flow
{flow}

## Non-Functional Requirements
- Response time < 200ms
- Support 1000 concurrent users
- 99.9% uptime

## Task Breakdown
{tasks}
"""


class PRDAgent:
    """Generate PRD from a natural language idea."""

    def __init__(self, model_router=None, memory=None, token_juice=None):
        self.model = model_router
        self.memory = memory
        self.token_juice = token_juice
        self.template_path = Path(__file__).parent / "templates" / "prd_template.md"

    async def generate(self, idea: str, context: str = "") -> dict:
        """Generate a complete PRD from an idea."""
        # 1. Get memory context if available
        mem_context = ""
        if self.memory:
            mem_context = self.memory.super_context(idea)

        # 2. Generate PRD using LLM or fallback to template
        if self.model:
            prd_text = await self._generate_with_llm(idea, context, mem_context)
        else:
            prd_text = self._generate_fallback(idea)

        # 3. Parse PRD into structured data
        parsed = self._parse_prd(prd_text)

        # 4. Save to Obsidian vault if memory available
        if self.memory:
            await self._save_to_vault(prd_text, parsed)

        return {
            "prd": prd_text,
            "parsed": parsed,
            "approval_needed": True,
        }

    async def _generate_with_llm(self, idea: str, context: str,
                                  mem_context: str) -> str:
        template = self.template_path.read_text(encoding="utf-8")
        system = ("You are a PRD generator. Generate a complete Product "
                  "Requirements Document in Markdown. Be specific and "
                  "actionable. Use the template provided.")
        prompt = f"""
Idea: {idea}

Context: {context}

Memory context: {mem_context}

Template:
{template}

Generate a complete PRD following the template structure.
Fill in every section with specific, actionable content.
Break features into numbered items (F1, F2, etc.).
Break tasks into phases (Foundation, Core, Frontend, Polish).
"""
        response = await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response

    def _generate_fallback(self, idea: str) -> str:
        """Generate a basic PRD without LLM (template fill)."""
        title = idea[:50]
        return PRD_TEMPLATE.format(
            title=title,
            overview=f"Application to: {idea}",
            problem=f"Need a solution for: {idea}",
            users="- Primary users\n- Secondary users",
            features="### F1: Core Feature\n- Sub-feature 1\n- Sub-feature 2",
            schema="- users (id, email, created_at)\n- items (id, user_id, title, created_at)",
            endpoints="- GET /items\n- POST /items\n- PUT /items/:id",
            flow="1. User registers\n2. User creates item\n3. User views items",
            tasks=("### Phase 1: Foundation\n- [ ] T1: Setup project\n"
                   "- [ ] T2: Setup database\n"
                   "### Phase 2: Core\n- [ ] T3: Build CRUD\n"
                   "### Phase 3: Frontend\n- [ ] T4: Build UI\n"
                   "### Phase 4: Polish\n- [ ] T5: Deploy"),
        )

    def _parse_prd(self, prd_text: str) -> dict:
        """Parse PRD markdown into structured data."""
        title = self._extract_section(prd_text, "Overview")[:100]
        features = self._extract_features(prd_text)
        tasks = self._extract_tasks(prd_text)
        phases = self._extract_phases(tasks)
        return {
            "title": title,
            "features": features,
            "tasks": tasks,
            "phases": phases,
            "feature_count": len(features),
            "task_count": len(tasks),
        }

    def _extract_section(self, text: str, section: str) -> str:
        pattern = rf"## {section}\s*\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_features(self, text: str) -> list[dict]:
        features = []
        pattern = r"### (F\d+):\s*(.+)"
        for match in re.finditer(pattern, text):
            features.append({
                "id": match.group(1),
                "name": match.group(2).strip(),
            })
        return features

    def _extract_tasks(self, text: str) -> list[dict]:
        tasks = []
        pattern = r"- \[ \] (T\d+):\s*(.+)"
        for match in re.finditer(pattern, text):
            tasks.append({
                "id": match.group(1),
                "title": match.group(2).strip(),
                "status": "todo",
            })
        return tasks

    def _extract_phases(self, tasks: list[dict]) -> list[str]:
        return ["Foundation", "Core", "Frontend", "Polish"]

    async def _save_to_vault(self, prd_text: str, parsed: dict):
        """Save PRD to Obsidian vault."""
        try:
            vault_dir = self.memory.vault_path / "prd"
            vault_dir.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^\w-]", "_", parsed["title"][:30]).lower()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prd_{slug}_{ts}.md"
            filepath = vault_dir / filename
            filepath.write_text(prd_text, encoding="utf-8")
        except Exception:
            pass
