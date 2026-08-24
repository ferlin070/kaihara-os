"""
Biz Autopilot — 8-step business automation workflow template.
FIND → ANALYZE → GENERATE → OUTREACH → WIN → BUILD → DEPLOY → CLOSE
"""

from core.workflow.engine import WorkflowDefinition
from core.workflow.steps import (
    FindBusinessesStep,
    AnalyzeBusinessStep,
    GenerateDemoStep,
    OutreachStep,
    WinJobStep,
    BuildProjectStep,
    DeploySiteStep,
    ClosePaymentStep,
)


def create_biz_autopilot(
    niche: str = "restoran",
    location: str = "Johor Bahru",
    outreach_channel: str = "email",
    sender_name: str = "Kaihara",
) -> WorkflowDefinition:
    """Create a business autopilot workflow instance."""

    steps = [
        FindBusinessesStep(),      # 0
        AnalyzeBusinessStep(),     # 1
        GenerateDemoStep(),        # 2
        OutreachStep(),            # 3
        WinJobStep(),              # 4
        BuildProjectStep(),        # 5
        DeploySiteStep(),          # 6
        ClosePaymentStep(),        # 7
    ]

    dependencies = {
        1: [0],  # analyze depends on find
        2: [1],  # generate depends on analyze
        3: [2],  # outreach depends on generate
        4: [3],  # win depends on outreach
        5: [4],  # build depends on win
        6: [5],  # deploy depends on build
        7: [6],  # close depends on deploy
    }

    template = WorkflowDefinition(
        name="biz_autopilot",
        description=f"Cari kedai {niche} tanpa website di {location}, "
                    f"generate demo, outreach, close deal.",
        steps=steps,
        dependencies=dependencies,
    )

    return template


# Default context for the workflow
DEFAULT_CONTEXT = {
    "niche": "restoran",
    "location": "Johor Bahru",
    "outreach_channel": "email",
    "sender_name": "Kaihara",
    "max_results": 15,
}
