"""
Task Agent — break specs into ordered, executable tasks.
Each task: unique ID, phase, dependencies, acceptance criteria, complexity.
"""

import re


class TaskAgent:
    """Break feature specs into ordered task list."""

    def __init__(self, model_router=None, memory=None, token_juice=None):
        self.model = model_router
        self.memory = memory
        self.token_juice = token_juice

    async def generate_tasks(self, prd_text: str,
                              specs: list[dict]) -> list[dict]:
        """Generate ordered task list from PRD + specs."""
        if self.model:
            tasks = await self._generate_with_llm(prd_text, specs)
        else:
            tasks = self._generate_fallback(specs)

        # Ensure each task has required fields
        for i, task in enumerate(tasks):
            task.setdefault("id", f"T{i+1}")
            task.setdefault("status", "todo")
            task.setdefault("dependencies", [])
            task.setdefault("complexity", "medium")
            task.setdefault("phase", self._assign_phase(i, len(tasks)))

        return tasks

    async def _generate_with_llm(self, prd_text: str,
                                  specs: list[dict]) -> list[dict]:
        specs_summary = "\n".join(
            f"- {s['feature_id']}: {s['feature_name']} "
            f"({', '.join(s.get('endpoints', []))})"
            for s in specs
        )
        system = ("You are a task planner. Break down PRD features into "
                  "ordered, executable tasks for AI coding agents.")
        prompt = f"""
PRD:
{prd_text[:2000]}

Feature Specs:
{specs_summary}

Generate an ordered task list. Each task:
- Unique ID (T1, T2, ...)
- Phase (Foundation, Core, Frontend, Polish)
- Dependencies (which tasks must be done first)
- Acceptance criteria
- Complexity (simple/medium/complex)

Format as JSON array:
[{{"id": "T1", "title": "...", "phase": "...", 
   "dependencies": [], "complexity": "simple", 
   "criteria": ["..."]}}]
"""
        response = await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_tasks_from_response(response)

    def _generate_fallback(self, specs: list[dict]) -> list[dict]:
        """Generate basic tasks without LLM."""
        tasks = [
            {"id": "T1", "title": "Setup project structure + Docker",
             "phase": "Foundation", "dependencies": [],
             "complexity": "simple", "criteria": ["Docker compose runs"]},
            {"id": "T2", "title": "Setup database + migrations",
             "phase": "Foundation", "dependencies": ["T1"],
             "complexity": "simple", "criteria": ["Migrations apply"]},
        ]
        for i, spec in enumerate(specs):
            tid = f"T{len(tasks)+1}"
            tasks.append({
                "id": tid,
                "title": f"Build {spec['feature_name']} ({spec['feature_id']})",
                "phase": "Core",
                "dependencies": ["T2"],
                "complexity": "medium",
                "criteria": [f"{spec['feature_id']} endpoints work"],
            })
        tasks.append({
            "id": f"T{len(tasks)+1}",
            "title": "Build frontend UI",
            "phase": "Frontend",
            "dependencies": [t["id"] for t in tasks if t["phase"] == "Core"],
            "complexity": "medium",
            "criteria": ["UI renders", "Forms work"],
        })
        tasks.append({
            "id": f"T{len(tasks)+1}",
            "title": "Write tests + deploy",
            "phase": "Polish",
            "dependencies": [f"T{len(tasks)}"],
            "complexity": "medium",
            "criteria": ["Tests pass", "Deployed"],
        })
        return tasks

    def _parse_tasks_from_response(self, response: str) -> list[dict]:
        """Parse LLM response into task list."""
        import json
        try:
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
        return []

    def _assign_phase(self, index: int, total: int) -> str:
        ratio = index / max(total, 1)
        if ratio < 0.2:
            return "Foundation"
        elif ratio < 0.6:
            return "Core"
        elif ratio < 0.85:
            return "Frontend"
        else:
            return "Polish"
