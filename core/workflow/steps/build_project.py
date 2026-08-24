"""
Step 6: Build Project
Uses PlanningPipeline to plan and build the client's website.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.build_project")


class BuildProjectStep(BusinessStep):
    """Plan and build the client's website using PlanningPipeline."""

    NAME = "build_project"
    AGENT = "coding"
    MAX_RETRIES = 2
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Build website mengikut kehendak client"

    async def run(self, context: dict) -> dict:
        win_result = context.get("win_job_result", {})
        converted = win_result.get("converted", [])
        demo_data = context.get("generate_demo_result", {}).get("demos", [])
        analyzed = context.get("analyze_business_result", {}).get("analyzed", [])

        if not converted:
            return {"output": {"built": [], "message": "Tiada client untuk build website"}}

        built = []
        for client in converted:
            client_name = client.get("lead_name", "")
            business_type = "general"
            features = []

            # Find matching demo data
            for demo in demo_data:
                if demo.get("name") == client_name:
                    business_type = demo.get("business_type", "general")
                    break
            for biz in analyzed:
                if biz.get("name") == client_name:
                    features = biz.get("suggested_features", [])
                    break

            try:
                # Generate the actual website HTML
                from core.tools.html_generator import generate_website_html
                html = generate_website_html(
                    business_name=client_name,
                    business_type=business_type,
                    features=features,
                    is_full_website=True,  # Full website, not just demo
                )

                built.append({
                    "client_name": client_name,
                    "client_id": client.get("client_id"),
                    "business_type": business_type,
                    "features": features,
                    "html_length": len(html),
                    "html": html,
                    "status": "ready_to_deploy",
                })
            except Exception as e:
                logger.error(f"Build failed for {client_name}: {e}")
                built.append({
                    "client_name": client_name,
                    "status": "failed",
                    "error": str(e),
                })

        ready = [b for b in built if b.get("status") == "ready_to_deploy"]

        return {
            "output": {
                "built": built,
                "total_built": len(built),
                "ready_to_deploy": len(ready),
            }
        }
