"""
Workflow Steps — business automation step implementations.
"""

from core.workflow.steps.base_step import BusinessStep
from core.workflow.steps.find_businesses import FindBusinessesStep
from core.workflow.steps.analyze_business import AnalyzeBusinessStep
from core.workflow.steps.generate_demo import GenerateDemoStep
from core.workflow.steps.outreach import OutreachStep
from core.workflow.steps.win_job import WinJobStep
from core.workflow.steps.build_project import BuildProjectStep
from core.workflow.steps.deploy_site import DeploySiteStep
from core.workflow.steps.close_payment import ClosePaymentStep

ALL_STEPS = {
    "find_businesses": FindBusinessesStep,
    "analyze_business": AnalyzeBusinessStep,
    "generate_demo": GenerateDemoStep,
    "outreach": OutreachStep,
    "win_job": WinJobStep,
    "build_project": BuildProjectStep,
    "deploy_site": DeploySiteStep,
    "close_payment": ClosePaymentStep,
}

__all__ = [
    "BusinessStep", "FindBusinessesStep", "AnalyzeBusinessStep",
    "GenerateDemoStep", "OutreachStep", "WinJobStep", "BuildProjectStep",
    "DeploySiteStep", "ClosePaymentStep", "ALL_STEPS",
]
