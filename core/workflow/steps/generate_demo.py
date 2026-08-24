"""
Step 3: Generate Demo Website
Uses LLM to generate a complete HTML demo website based on business analysis.
Deploys to nakhodacloud.top for demo.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.generate_demo")


class GenerateDemoStep(BusinessStep):
    """Generate demo website HTML and deploy to nakhodacloud.top."""

    NAME = "generate_demo"
    AGENT = "coding"
    MAX_RETRIES = 2
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Generate demo website untuk perniagaan"

    async def run(self, context: dict) -> dict:
        analyzed = context.get("analyze_business_result", {}).get(
            "high_priority", []
        )
        if not analyzed:
            analyzed = context.get("analyze_business_result", {}).get(
                "analyzed", []
            )[:3]

        if not analyzed:
            return {"output": {"demos": [], "message": "Tiada perniagaan untuk generate demo"}}

        from core.tools.html_generator import generate_website_html
        from core.tools.deploy_tools import deploy_landing

        demos = []
        for biz in analyzed:
            name = biz.get("name", "Business")
            business_type = biz.get("business_type", "general")
            features = biz.get("suggested_features", [])
            contacts = biz.get("contacts", {})
            socials = biz.get("social_media", [])

            try:
                # Generate HTML
                html = generate_website_html(
                    business_name=name,
                    business_type=business_type,
                    features=features,
                    phone=contacts.get("phone", ""),
                    email=contacts.get("email", ""),
                    address=biz.get("address", ""),
                    social_media=socials,
                )

                # Deploy to nakhodacloud.top
                slug = name.lower().replace(" ", "-")[:20]
                deploy_result = deploy_landing(slug, html, overwrite=True)

                demos.append({
                    "name": name,
                    "slug": slug,
                    "business_type": business_type,
                    "deployed": deploy_result.get("ok", False),
                    "url": deploy_result.get("url", ""),
                    "demo_url": deploy_result.get("url", ""),
                    "error": deploy_result.get("error", ""),
                })
            except Exception as e:
                logger.error(f"Demo generation failed for {name}: {e}")
                demos.append({
                    "name": name,
                    "deployed": False,
                    "error": str(e),
                })

        successful = [d for d in demos if d.get("deployed")]

        return {
            "output": {
                "demos": demos,
                "total_generated": len(demos),
                "successful": len(successful),
                "demo_urls": [d["url"] for d in successful if d.get("url")],
            }
        }
