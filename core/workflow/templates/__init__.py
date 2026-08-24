"""
Workflow Templates — predefined workflow templates.
"""

from core.workflow.templates.biz_autopilot import create_biz_autopilot, DEFAULT_CONTEXT

TEMPLATES = {
    "biz_autopilot": create_biz_autopilot,
}

def get_template(name: str):
    return TEMPLATES.get(name)

def list_templates():
    return list(TEMPLATES.keys())
