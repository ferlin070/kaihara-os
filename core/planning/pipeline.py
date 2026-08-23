"""
Planning Pipeline — coordinator.
Idea -> PRD -> Specs -> Tasks -> Kanban -> Code -> Deploy
"""

from core.planning.prd_agent import PRDAgent
from core.planning.spec_agent import SpecAgent
from core.planning.task_agent import TaskAgent
from core.planning.task_tracker import TaskTracker


class PlanningPipeline:
    """Coordinate the full planning pipeline."""

    def __init__(self, model_router=None, memory=None,
                 token_juice=None, db_path="./data/kaihara.db"):
        self.prd_agent = PRDAgent(model_router, memory, token_juice)
        self.spec_agent = SpecAgent(model_router, memory, token_juice)
        self.task_agent = TaskAgent(model_router, memory, token_juice)
        self.tracker = TaskTracker(db_path)

    async def plan(self, idea: str, context: str = "") -> dict:
        """Full pipeline: idea -> PRD -> specs -> tasks."""
        # 1. Generate PRD
        prd_result = await self.prd_agent.generate(idea, context)
        prd_text = prd_result["prd"]
        parsed = prd_result["parsed"]

        # 2. Save PRD
        prd_id = self.tracker.save_prd(
            parsed.get("title", idea[:50]),
            prd_text, parsed
        )

        # 3. Generate specs
        specs = await self.spec_agent.generate_specs(prd_text, parsed)

        # 4. Generate tasks
        tasks = await self.task_agent.generate_tasks(prd_text, specs)

        # 5. Save tasks
        self.tracker.save_tasks(tasks, prd_id)

        return {
            "prd_id": prd_id,
            "prd": prd_text,
            "parsed": parsed,
            "specs": specs,
            "tasks": tasks,
            "progress": self.tracker.get_progress(prd_id),
            "message": (
                f"PRD generated: {parsed.get('feature_count', 0)} features, "
                f"{parsed.get('task_count', 0)} tasks. "
                f"Review and approve to proceed."
            ),
        }

    async def plan_prd_only(self, idea: str, context: str = "") -> dict:
        """Generate PRD only (step 1)."""
        prd_result = await self.prd_agent.generate(idea, context)
        prd_text = prd_result["prd"]
        parsed = prd_result["parsed"]
        prd_id = self.tracker.save_prd(
            parsed.get("title", idea[:50]), prd_text, parsed
        )
        return {
            "prd_id": prd_id,
            "prd": prd_text,
            "parsed": parsed,
            "message": "PRD generated. Review and approve.",
        }

    async def generate_specs_from_prd(self, prd_id: str) -> dict:
        """Generate specs from existing PRD (step 2)."""
        prd = self.tracker.get_prd(prd_id)
        if not prd:
            return {"error": "PRD not found"}
        import json
        parsed = json.loads(prd.get("parsed") or "{}")
        specs = await self.spec_agent.generate_specs(
            prd["content"], parsed
        )
        return {
            "prd_id": prd_id,
            "specs": specs,
            "message": f"Generated {len(specs)} feature specs.",
        }

    async def generate_tasks_from_specs(self, prd_id: str,
                                         specs: list[dict]) -> dict:
        """Generate tasks from specs (step 3)."""
        prd = self.tracker.get_prd(prd_id)
        if not prd:
            return {"error": "PRD not found"}
        tasks = await self.task_agent.generate_tasks(
            prd["content"], specs
        )
        self.tracker.save_tasks(tasks, prd_id)
        return {
            "prd_id": prd_id,
            "tasks": tasks,
            "progress": self.tracker.get_progress(prd_id),
            "message": f"Generated {len(tasks)} tasks.",
        }

    def get_tasks(self, prd_id: str = None, status: str = None) -> list[dict]:
        return self.tracker.get_tasks(prd_id=prd_id, status=status)

    def get_progress(self, prd_id: str = None) -> dict:
        return self.tracker.get_progress(prd_id=prd_id)

    def update_task_status(self, task_id: str, status: str) -> bool:
        return self.tracker.update_status(task_id, status)

    def get_prds(self) -> list[dict]:
        return self.tracker.get_prds()

    def get_prd(self, prd_id: str) -> dict | None:
        return self.tracker.get_prd(prd_id)
