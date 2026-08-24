"""
Step Runner — executes individual workflow steps via agents.
"""

import asyncio
import traceback
from typing import Any

from core.workflow.state_machine import WorkflowState
from core.workflow.workflow_store import WorkflowStore


class BaseStep:
    """Abstract base class for workflow steps."""

    NAME: str = "unnamed"
    AGENT: str = "kaihara"
    MAX_RETRIES: int = 3
    REQUIRES_APPROVAL: bool = False

    async def run(self, context: dict) -> dict:
        """Execute the step. Must return dict with 'output' key."""
        raise NotImplementedError

    def get_description(self) -> str:
        return self.NAME


class StepRunner:
    """Executes steps with retry, approval, and error handling."""

    def __init__(self, store: WorkflowStore, approval_gate=None,
                 notify_fn=None):
        self.store = store
        self.approval_gate = approval_gate
        self.notify_fn = notify_fn

    async def execute(self, step: BaseStep, step_id: str,
                      workflow_id: str, context: dict,
                      max_retries: int = 3) -> dict:
        """Run a step with retry logic and approval gates."""
        # Check approval gate
        if step.REQUIRES_APPROVAL:
            approval_ok = await self._request_approval(step, workflow_id, context)
            if not approval_ok:
                self.store.update_step_state(
                    step_id, WorkflowState.CANCELLED.value,
                    error="Approval rejected"
                )
                return {
                    "status": "cancelled",
                    "error": "Approval rejected by user"
                }

        self.store.update_step_state(step_id, WorkflowState.RUNNING.value)
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await step.run(context)

                if not isinstance(result, dict):
                    result = {"output": str(result)}

                self.store.update_step_state(
                    step_id, WorkflowState.COMPLETED.value,
                    output_data=result
                )
                return {
                    "status": "completed",
                    "output": result,
                    "step_id": step_id,
                    "attempt": attempt + 1,
                }
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                if attempt < max_retries:
                    self.store.increment_retry(step_id)
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.store.update_step_state(
                        step_id, WorkflowState.FAILED.value,
                        error=last_error
                    )

        return {
            "status": "failed",
            "error": last_error,
            "step_id": step_id,
        }

    async def _request_approval(self, step: BaseStep, workflow_id: str,
                                context: dict) -> bool:
        """Request approval via ApprovalGate or fallback to auto-approve."""
        if not self.approval_gate:
            return True

        try:
            request = {
                "action": f"workflow_step:{step.NAME}",
                "agent": step.AGENT,
                "workflow_id": workflow_id,
                "description": step.get_description(),
                "context_preview": str(context)[:200],
            }
            result = await self.approval_gate.request(request)
            return result.get("approved", False)
        except Exception:
            return True
