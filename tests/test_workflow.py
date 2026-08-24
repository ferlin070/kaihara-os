"""
Tests for Workflow Engine
"""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.workflow.state_machine import WorkflowState, StateMachine
from core.workflow.workflow_store import WorkflowStore
from core.workflow.step_runner import StepRunner, BaseStep
from core.workflow.engine import WorkflowEngine, WorkflowDefinition
from core.workflow.steps import ALL_STEPS
from core.workflow.templates.biz_autopilot import create_biz_autopilot


class MockStep(BaseStep):
    """Mock step for testing."""
    NAME = "mock_step"
    AGENT = "test"
    REQUIRES_APPROVAL = False

    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    async def run(self, context: dict) -> dict:
        if self.should_fail:
            raise ValueError("Mock step failed")
        return {"output": f"Mock completed with {len(context)} context items"}


class ApprovalStep(BaseStep):
    """Step that requires approval."""
    NAME = "approval_step"
    AGENT = "test"
    REQUIRES_APPROVAL = True

    async def run(self, context: dict) -> dict:
        return {"output": "Approved step completed"}


class TestStateMachine(unittest.TestCase):
    def test_initial_state(self):
        sm = StateMachine("test-1")
        self.assertEqual(sm.state, WorkflowState.PENDING)

    def test_valid_transition(self):
        sm = StateMachine("test-2")
        self.assertTrue(sm.transition(WorkflowState.RUNNING))
        self.assertEqual(sm.state, WorkflowState.RUNNING)

    def test_invalid_transition(self):
        sm = StateMachine("test-3")
        self.assertFalse(sm.transition(WorkflowState.COMPLETED))
        self.assertEqual(sm.state, WorkflowState.PENDING)

    def test_pause_resume(self):
        sm = StateMachine("test-4")
        sm.transition(WorkflowState.RUNNING)
        self.assertTrue(sm.pause())
        self.assertEqual(sm.state, WorkflowState.PAUSED)
        self.assertTrue(sm.resume())
        self.assertEqual(sm.state, WorkflowState.RUNNING)

    def test_cancel(self):
        sm = StateMachine("test-5")
        self.assertTrue(sm.cancel())
        self.assertEqual(sm.state, WorkflowState.CANCELLED)

    def test_fail(self):
        sm = StateMachine("test-6")
        sm.transition(WorkflowState.RUNNING)
        self.assertTrue(sm.fail("test error"))
        self.assertEqual(sm.state, WorkflowState.FAILED)


class TestWorkflowStore(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.store = WorkflowStore(self.db_path)

    def tearDown(self):
        self.store = None
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass

    def test_create_workflow(self):
        result = self.store.create_workflow(
            "wf-001", "test", "test_template", {}, 5, []
        )
        self.assertEqual(result["id"], "wf-001")

    def test_get_workflow(self):
        self.store.create_workflow("wf-002", "test", "test_template", {}, 5, [])
        wf = self.store.get_workflow("wf-002")
        self.assertIsNotNone(wf)
        self.assertEqual(wf["name"], "test")

    def test_create_step(self):
        self.store.create_workflow("wf-003", "test", "test_template", {}, 2, [])
        result = self.store.create_step(
            "step-001", "wf-003", 0, "test_step", "test"
        )
        self.assertEqual(result["id"], "step-001")

    def test_update_step_state(self):
        self.store.create_workflow("wf-004", "test", "test_template", {}, 1, [])
        self.store.create_step("step-002", "wf-004", 0, "test_step", "test")
        self.store.update_step_state("step-002", "completed", {"result": "ok"})
        step = self.store.get_step("step-002")
        self.assertEqual(step["state"], "completed")

    def test_list_workflows(self):
        self.store.create_workflow("wf-005", "test1", "test", {}, 1, [])
        self.store.create_workflow("wf-006", "test2", "test", {}, 1, [])
        workflows = self.store.list_workflows()
        self.assertEqual(len(workflows), 2)


class TestWorkflowEngine(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.store = WorkflowStore(self.db_path)
        self.engine = WorkflowEngine(store=self.store)

    def tearDown(self):
        self.engine = None
        self.store = None
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass

    def test_register_template(self):
        template = WorkflowDefinition(
            "test", "Test workflow", [MockStep()]
        )
        self.engine.register_template(template)
        self.assertIn("test", self.engine.list_templates())

    def test_start_workflow(self):
        template = WorkflowDefinition(
            "test", "Test workflow", [MockStep()]
        )
        self.engine.register_template(template)

        result = asyncio.run(self.engine.start("test", {"key": "value"}))
        self.assertIn("workflow_id", result)
        self.assertEqual(result["total_steps"], 1)

    def test_start_nonexistent_template(self):
        result = asyncio.run(self.engine.start("nonexistent"))
        self.assertIn("error", result)

    def test_workflow_execution(self):
        template = WorkflowDefinition(
            "test_exec", "Test execution",
            [MockStep(), MockStep()],
            dependencies={1: [0]}
        )
        self.engine.register_template(template)

        async def run():
            result = await self.engine.start("test_exec")
            # Wait for background task
            await asyncio.sleep(0.5)
            return self.engine.get_status(result["workflow_id"])

        status = asyncio.run(run())
        self.assertIn(status["state"], ["completed", "running"])

    def test_get_status(self):
        template = WorkflowDefinition(
            "test_status", "Test", [MockStep()]
        )
        self.engine.register_template(template)
        result = asyncio.run(self.engine.start("test_status"))
        status = self.engine.get_status(result["workflow_id"])
        self.assertEqual(status["total_steps"], 1)


class TestBizAutopilot(unittest.TestCase):
    def test_create_template(self):
        template = create_biz_autopilot(
            niche="restoran",
            location="Johor Bahru"
        )
        self.assertEqual(template.name, "biz_autopilot")
        self.assertEqual(len(template.steps), 8)

    def test_dependencies(self):
        template = create_biz_autopilot()
        order = template.get_step_order()
        # Should have 8 levels (one per step)
        self.assertEqual(len(order), 8)
        # Each level should have exactly one step
        for level in order:
            self.assertEqual(len(level), 1)


class TestAllSteps(unittest.TestCase):
    def test_all_steps_registered(self):
        self.assertEqual(len(ALL_STEPS), 8)

    def test_step_names(self):
        expected = [
            "find_businesses", "analyze_business", "generate_demo",
            "outreach", "win_job", "build_project", "deploy_site",
            "close_payment"
        ]
        for name in expected:
            self.assertIn(name, ALL_STEPS)

    def test_step_instances(self):
        for name, step_class in ALL_STEPS.items():
            step = step_class()
            self.assertEqual(step.NAME, name)
            self.assertIsNotNone(step.AGENT)


if __name__ == "__main__":
    unittest.main()
