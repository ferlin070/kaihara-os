"""
Base Step — abstract class for workflow steps.
"""

from core.workflow.step_runner import BaseStep


class BusinessStep(BaseStep):
    """Base class for business automation workflow steps."""

    CATEGORY = "business"
