"""
Workflow State Machine — defines states and valid transitions.
"""

from enum import Enum


class WorkflowState(str, Enum):
    """All possible states for a workflow or step."""
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

    def can_transition_to(self, target: "WorkflowState") -> bool:
        return target in TRANSITIONS.get(self, set())


TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.PENDING: {
        WorkflowState.RUNNING,
        WorkflowState.CANCELLED,
        WorkflowState.SKIPPED,
    },
    WorkflowState.WAITING_APPROVAL: {
        WorkflowState.RUNNING,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.RUNNING: {
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.PAUSED,
        WorkflowState.WAITING_APPROVAL,
    },
    WorkflowState.PAUSED: {
        WorkflowState.RUNNING,
        WorkflowState.CANCELLED,
    },
    WorkflowState.COMPLETED: set(),
    WorkflowState.FAILED: {
        WorkflowState.PENDING,
        WorkflowState.CANCELLED,
    },
    WorkflowState.CANCELLED: set(),
    WorkflowState.SKIPPED: set(),
}


class StateMachine:
    """Tracks and enforces state transitions for workflow instances."""

    def __init__(self, workflow_id: str, store=None):
        self.workflow_id = workflow_id
        self.store = store
        self._state = WorkflowState.PENDING

    @property
    def state(self) -> WorkflowState:
        return self._state

    def transition(self, target: WorkflowState, reason: str = "") -> bool:
        if not self._state.can_transition_to(target):
            return False
        old = self._state
        self._state = target
        if self.store:
            self.store.update_workflow_state(
                self.workflow_id, target.value, reason
            )
        return True

    def pause(self) -> bool:
        return self.transition(WorkflowState.PAUSED, "User paused")

    def resume(self) -> bool:
        return self.transition(WorkflowState.RUNNING, "User resumed")

    def cancel(self) -> bool:
        return self.transition(WorkflowState.CANCELLED, "User cancelled")

    def fail(self, reason: str = "") -> bool:
        return self.transition(WorkflowState.FAILED, reason)

    def complete(self) -> bool:
        return self.transition(WorkflowState.COMPLETED, "All steps done")
