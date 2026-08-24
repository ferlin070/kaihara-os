"""
Step 1: Find Businesses Without Websites
Searches for businesses in a niche/location, filters out those that already have websites.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.find_businesses")


class FindBusinessesStep(BusinessStep):
    """Search businesses and identify those without websites."""

    NAME = "find_businesses"
    AGENT = "marketing"
    MAX_RETRIES = 2
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Mencari perniagaan dalam niche tanpa website"

    async def run(self, context: dict) -> dict:
        niche = context.get("niche", "")
        location = context.get("location", "Malaysia")
        max_results = context.get("max_results", 15)

        if not niche:
            raise ValueError("Parameter 'niche' diperlukan")

        # Import tools lazily
        from core.tools.web_tools import search_places, web_search, scrape_website

        # Search for businesses
        query = f"{niche} {location}"
        places_raw = search_places(query, max_results=max_results)
        places = json.loads(places_raw) if isinstance(places_raw, str) else places_raw

        # Filter businesses without websites
        no_website = []
        has_website = []

        for business in places:
            name = business.get("name", "")
            address = business.get("address", "")
            if not name:
                continue

            # Try to find website for this business
            has_site = await self._check_has_website(name, address)
            entry = {
                "name": name,
                "address": address,
                "phone": business.get("phone", ""),
                "has_website": has_site,
            }

            if has_site:
                has_website.append(entry)
            else:
                entry["score"] = self._score_lead(entry)
                no_website.append(entry)

        # Sort by score
        no_website.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Create leads in marketing DB
        created_leads = []
        try:
            from core.marketing.leads import create_lead
            for biz in no_website[:10]:
                lead = create_lead(
                    name=biz["name"],
                    phone=biz.get("phone", ""),
                    company=biz["name"],
                    source="workflow_find",
                    notes=f"Address: {biz['address']}. Score: {biz.get('score', 0)}",
                    tags=["no_website", niche],
                )
                created_leads.append(lead)
        except Exception as e:
            logger.warning(f"Failed to create leads: {e}")

        return {
            "output": {
                "niche": niche,
                "location": location,
                "total_found": len(places),
                "without_website": no_website,
                "with_website": has_website,
                "leads_created": len(created_leads),
                "leads": created_leads,
                "high_priority": [b for b in no_website if b.get("score", 0) >= 50],
            }
        }

    async def _check_has_website(self, name: str, address: str) -> bool:
        """Check if a business already has a website."""
        from core.tools.web_tools import web_search
        import json as _json

        try:
            result_raw = web_search(f'"{name}" {address} website', max_results=5)
            result = _json.loads(result_raw) if isinstance(result_raw, str) else result_raw

            for r in result.get("results", []):
                url = r.get("url", "")
                title = r.get("title", "").lower()
                snippet = r.get("snippet", "").lower()

                # Check if they have their own website (not directories)
                if any(d in url for d in [
                    "facebook.com", "instagram.com", "tiktok.com",
                    "waze.com", "google.com", "tripadvisor.com",
                    "foursquare.com", "yelp.com", "yellowpages"
                ]):
                    continue

                if name.lower() in title or name.lower() in snippet:
                    return True
        except Exception:
            pass

        return False

    def _score_lead(self, business: dict) -> int:
        """Score a lead based on available data."""
        score = 0
        if business.get("phone"):
            score += 15
        if business.get("address"):
            score += 10
        # Business without website = high opportunity
        score += 30
        return score
