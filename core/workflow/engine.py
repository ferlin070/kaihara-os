"""
Workflow Engine — DAG-based workflow executor.
Orchestrates multi-step business automation workflows.
"""

import asyncio
import uuid
import json
import logging
from datetime import datetime
from typing import Any

from core.workflow.state_machine import WorkflowState, StateMachine
from core.workflow.workflow_store import WorkflowStore
from core.workflow.step_runner import StepRunner, BaseStep

logger = logging.getLogger("kaihara.workflow")


class WorkflowDefinition:
    """Defines a workflow template with steps and dependencies."""

    def __init__(self, name: str, description: str,
                 steps: list[BaseStep], dependencies: dict = None):
        self.name = name
        self.description = description
        self.steps = steps
        self.dependencies = dependencies or {}

    def get_step_order(self) -> list[list[int]]:
        """Return execution order as list of levels.
        Each level contains step indices that can run in parallel."""
        n = len(self.steps)
        in_degree = [0] * n
        for step_idx, deps in self.dependencies.items():
            for dep in deps:
                in_degree[step_idx] += 1

        levels = []
        visited = set()
        while len(visited) < n:
            level = []
            for i in range(n):
                if i not in visited and in_degree[i] == 0:
                    level.append(i)
            if not level:
                break
            levels.append(level)
            for idx in level:
                visited.add(idx)
                for next_idx in range(n):
                    if idx in self.dependencies.get(next_idx, []):
                        in_degree[next_idx] -= 1
        return levels


class WorkflowEngine:
    """Main workflow engine — creates, runs, pauses, resumes workflows."""

    def __init__(self, store: WorkflowStore = None, approval_gate=None,
                 notify_fn=None, fleet_manager=None, memory=None, config: dict = None):
        self.config = config or {}
        db_path = self.config.get("db_path")
        self.store = store or WorkflowStore(db_path)
        self.approval_gate = approval_gate
        self.notify_fn = notify_fn
        self.fleet = fleet_manager
        self.memory = memory
        self.runner = StepRunner(self.store, approval_gate, notify_fn)
        self._templates: dict[str, WorkflowDefinition] = {}
        self._running: dict[str, asyncio.Task] = {}
        self.max_concurrent = self.config.get("max_concurrent", 3)

    def register_template(self, template: WorkflowDefinition):
        """Register a workflow template."""
        self._templates[template.name] = template

    def get_template(self, name: str) -> WorkflowDefinition | None:
        return self._templates.get(name)

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    async def start(self, template_name: str, input_data: dict = None,
                    workflow_id: str = None) -> dict:
        """Start a new workflow run."""
        template = self._templates.get(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}

        workflow_id = workflow_id or f"wf-{uuid.uuid4().hex[:12]}"
        input_data = input_data or {}

        # Create workflow instance in DB
        approval_steps = [
            s.NAME for s in template.steps if s.REQUIRES_APPROVAL
        ]
        self.store.create_workflow(
            workflow_id=workflow_id,
            name=template.name,
            template=template_name,
            input_data=input_data,
            total_steps=len(template.steps),
            approval_steps=approval_steps,
        )

        # Create step records
        for i, step in enumerate(template.steps):
            step_id = f"{workflow_id}-step-{i}"
            self.store.create_step(
                step_id=step_id,
                workflow_id=workflow_id,
                step_index=i,
                name=step.NAME,
                agent=step.AGENT,
                max_retries=step.MAX_RETRIES,
                approval_required=step.REQUIRES_APPROVAL,
            )

        # Start execution in background
        task = asyncio.create_task(
            self._execute_workflow(workflow_id, template, input_data)
        )
        self._running[workflow_id] = task

        return {
            "workflow_id": workflow_id,
            "state": "pending",
            "total_steps": len(template.steps),
            "message": f"Workflow '{template_name}' started",
        }

    async def _execute_workflow(self, workflow_id: str,
                                template: WorkflowDefinition,
                                context: dict):
        """Execute all steps according to DAG order."""
        state = StateMachine(workflow_id, self.store)
        state.transition(WorkflowState.RUNNING)

        steps = template.steps
        order = template.get_step_order()
        completed = 0

        for level in order:
            # Run steps in this level (potentially parallel)
            tasks = []
            for step_idx in level:
                step = steps[step_idx]
                step_id = f"{workflow_id}-step-{step_idx}"

                # Check dependencies satisfied
                deps = template.dependencies.get(step_idx, [])
                deps_met = all(
                    self._is_step_completed(workflow_id, d) for d in deps
                )
                if not deps_met:
                    self.store.update_step_state(
                        step_id, WorkflowState.SKIPPED.value,
                        error="Dependencies not met"
                    )
                    completed += 1
                    continue

                # Build context from dependency outputs
                enriched_context = self._build_context(
                    workflow_id, context, template.steps, deps
                )

                tasks.append(
                    self._run_step_with_state(
                        step, step_id, workflow_id, enriched_context, state
                    )
                )

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, dict) and r.get("status") == "completed":
                        completed += 1
                    elif isinstance(r, Exception):
                        completed += 1

            self.store.update_workflow_progress(
                workflow_id, completed,
                f"level-{order.index(level)}"
            )

        # Final state
        if state.state != WorkflowState.CANCELLED:
            state.complete()

        # Cleanup
        self._running.pop(workflow_id, None)

        # Store result in memory
        if self.memory:
            result_summary = {
                "workflow": template.name,
                "status": state.state.value,
                "completed_steps": completed,
                "total_steps": len(steps),
            }
            self.memory.store(
                json.dumps(result_summary),
                source="workflow",
                agent="workflow_engine"
            )

    async def _run_step_with_state(self, step: BaseStep, step_id: str,
                                   workflow_id: str, context: dict,
                                   state: StateMachine) -> dict:
        """Run a step and update workflow state if needed."""
        result = await self.runner.execute(
            step, step_id, workflow_id, context, step.MAX_RETRIES
        )

        if result.get("status") == "failed":
            if state.state == WorkflowState.RUNNING:
                state.fail(result.get("error", "Step failed"))
            if self.notify_fn:
                await self.notify_fn(
                    f"Workflow step '{step.NAME}' failed: {result.get('error')}"
                )
        elif result.get("status") == "cancelled":
            if state.state == WorkflowState.RUNNING:
                state.cancel()

        return result

    def _is_step_completed(self, workflow_id: str, step_index: int) -> bool:
        """Check if a specific step has completed."""
        step_id = f"{workflow_id}-step-{step_index}"
        step_data = self.store.get_step(step_id)
        if not step_data:
            return False
        return step_data.get("state") == WorkflowState.COMPLETED.value

    def _build_context(self, workflow_id: str, base_context: dict,
                       steps: list, deps: list) -> dict:
        """Build enriched context with outputs from dependency steps."""
        ctx = dict(base_context)
        for dep_idx in deps:
            step_id = f"{workflow_id}-step-{dep_idx}"
            step_data = self.store.get_step(step_id)
            if step_data and step_data.get("output_data"):
                output = json.loads(step_data["output_data"])
                step_name = steps[dep_idx].NAME
                ctx[f"{step_name}_result"] = output
                ctx[f"step_{dep_idx}_output"] = output
        return ctx

    async def pause(self, workflow_id: str) -> dict:
        """Pause a running workflow."""
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        state = StateMachine(workflow_id, self.store)
        state._state = WorkflowState(wf["state"])

        if state.pause():
            task = self._running.get(workflow_id)
            if task:
                task.cancel()
            return {"workflow_id": workflow_id, "state": "paused"}
        return {"error": f"Cannot pause from state {wf['state']}"}

    async def resume(self, workflow_id: str) -> dict:
        """Resume a paused workflow."""
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        state = StateMachine(workflow_id, self.store)
        state._state = WorkflowState(wf["state"])

        if state.resume():
            template_name = wf.get("template", "")
            template = self._templates.get(template_name)
            input_data = json.loads(wf.get("input_data", "{}"))
            task = asyncio.create_task(
                self._execute_workflow(workflow_id, template, input_data)
            )
            self._running[workflow_id] = task
            return {"workflow_id": workflow_id, "state": "running"}
        return {"error": f"Cannot resume from state {wf['state']}"}

    async def cancel(self, workflow_id: str) -> dict:
        """Cancel a workflow."""
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        state = StateMachine(workflow_id, self.store)
        state._state = WorkflowState(wf["state"])

        if state.cancel():
            task = self._running.pop(workflow_id, None)
            if task:
                task.cancel()
            return {"workflow_id": workflow_id, "state": "cancelled"}
        return {"error": f"Cannot cancel from state {wf['state']}"}

    def get_status(self, workflow_id: str) -> dict:
        """Get current workflow status."""
        wf = self.store.get_workflow(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        steps = self.store.get_steps_for_workflow(workflow_id)
        return {
            "id": wf["id"],
            "name": wf["name"],
            "template": wf["template"],
            "state": wf["state"],
            "total_steps": wf["total_steps"],
            "completed_steps": wf["completed_steps"],
            "current_step": wf.get("current_step"),
            "error": wf.get("error"),
            "steps": [
                {
                    "index": s["step_index"],
                    "name": s["name"],
                    "agent": s["agent"],
                    "state": s["state"],
                    "approval_required": bool(s["approval_required"]),
                    "approval_status": s.get("approval_status"),
                    "retry_count": s["retry_count"],
                }
                for s in steps
            ],
            "created_at": wf["created_at"],
            "updated_at": wf["updated_at"],
        }

    def list_workflows(self, state: str = None) -> list[dict]:
        """List all workflow runs."""
        return self.store.list_workflows(state=state)

    async def approve_step(self, workflow_id: str, step_index: int,
                           approved: bool) -> dict:
        """Approve or reject a pending approval step."""
        step_id = f"{workflow_id}-step-{step_index}"
        step_data = self.store.get_step(step_id)
        if not step_data:
            return {"error": "Step not found"}

        self.store.approve_step(step_id, approved)

        if approved and step_data["state"] == WorkflowState.WAITING_APPROVAL.value:
            self.store.update_step_state(step_id, WorkflowState.RUNNING.value)

        return {
            "step_id": step_id,
            "approved": approved,
            "state": "running" if approved else "cancelled",
        }
