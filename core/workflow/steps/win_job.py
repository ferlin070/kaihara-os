"""
Step 5: Win Job
Tracks responses, converts interested leads to clients.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.win_job")


class WinJobStep(BusinessStep):
    """Track responses and convert interested leads to clients."""

    NAME = "win_job"
    AGENT = "marketing"
    MAX_RETRIES = 1
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Trace response dan convert lead kepada client"

    async def run(self, context: dict) -> dict:
        outreach_result = context.get("outreach_result", {})
        sent = outreach_result.get("sent", [])

        # Check for responses (this would normally be event-driven)
        # For now, we track which leads need follow-up
        from core.marketing.leads import get_leads, update_lead
        from core.marketing.clients import create_client

        leads = get_leads(status="new")
        workflow_leads = []
        for lead in leads:
            if lead.get("source") == "workflow_find":
                workflow_leads.append(lead)

        # Simulate response tracking (in production, this would be event-driven)
        converted = []
        pending_followup = []

        for lead in workflow_leads[:10]:
            # Check if they have contact info
            has_email = bool(lead.get("email"))
            has_phone = bool(lead.get("phone"))

            if has_email or has_phone:
                # Create client entry
                try:
                    client = create_client(
                        lead_id=lead["id"],
                        name=lead["name"],
                        email=lead.get("email", ""),
                        phone=lead.get("phone", ""),
                        company=lead.get("company", ""),
                        notes=f"Auto-created from workflow. Score: {lead.get('score', 0)}",
                        tier="basic",
                    )
                    converted.append({
                        "lead_name": lead["name"],
                        "client_id": client.get("id") if isinstance(client, dict) else None,
                        "status": "pending_response",
                    })
                    # Update lead status
                    update_lead(lead["id"], status="contacted")
                except Exception as e:
                    logger.warning(f"Failed to convert lead {lead['name']}: {e}")
                    pending_followup.append({
                        "name": lead["name"],
                        "reason": str(e),
                    })
            else:
                pending_followup.append({
                    "name": lead["name"],
                    "reason": "No contact info",
                })

        return {
            "output": {
                "converted": converted,
                "pending_followup": pending_followup,
                "total_leads": len(workflow_leads),
                "total_converted": len(converted),
                "needs_followup": len(pending_followup),
            }
        }
