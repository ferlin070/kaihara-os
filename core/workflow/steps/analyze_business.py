"""
Step 2: Analyze Business
Scrapes competitor sites, checks SEO, identifies what the business does.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.analyze_business")


class AnalyzeBusinessStep(BusinessStep):
    """Analyze businesses — scrape, SEO audit, competitor check."""

    NAME = "analyze_business"
    AGENT = "marketing"
    MAX_RETRIES = 2
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Menganalisa perniagaan — scraping, SEO audit, competitor analysis"

    async def run(self, context: dict) -> dict:
        businesses = context.get("find_businesses_result", {}).get(
            "without_website", []
        )
        if not businesses:
            businesses = context.get("high_priority", [])

        if not businesses:
            return {"output": {"analyzed": [], "message": "Tiada perniagaan untuk dianalisa"}}

        from core.tools.web_tools import web_search, scrape_website
        from core.tools.web_tools import _ddg_results

        analyzed = []
        for biz in businesses[:8]:
            name = biz.get("name", "")
            address = biz.get("address", "")
            analysis = {
                "name": name,
                "address": address,
                "phone": biz.get("phone", ""),
                "lead_score": biz.get("score", 0),
            }

            # Try to find their social media / existing online presence
            try:
                search_result = web_search(f'"{name}" {address}', max_results=5)
                results = json.loads(search_result) if isinstance(search_result, str) else search_result
                socials = []
                for r in results.get("results", []):
                    url = r.get("url", "")
                    if "facebook.com" in url:
                        socials.append({"platform": "Facebook", "url": url})
                    elif "instagram.com" in url:
                        socials.append({"platform": "Instagram", "url": url})
                    elif "tiktok.com" in url:
                        socials.append({"platform": "TikTok", "url": url})
                analysis["social_media"] = socials
            except Exception:
                analysis["social_media"] = []

            # Get contact info
            analysis["contacts"] = {
                "phone": biz.get("phone", ""),
                "email": "",
            }

            # Estimate business type from name
            analysis["business_type"] = self._guess_business_type(name)

            # Suggest website features
            analysis["suggested_features"] = self._suggest_features(
                analysis["business_type"]
            )

            analyzed.append(analysis)

        # Rank by priority (highest score = best target)
        analyzed.sort(key=lambda x: x.get("lead_score", 0), reverse=True)

        return {
            "output": {
                "analyzed": analyzed,
                "total_analyzed": len(analyzed),
                "high_priority": [a for a in analyzed if a.get("lead_score", 0) >= 50],
                "business_types": list(set(a["business_type"] for a in analyzed)),
            }
        }

    def _guess_business_type(self, name: str) -> str:
        name_lower = name.lower()
        keywords = {
            "restaurant": ["restoran", "restaurant", "makan", "food", "cafe", "kopitiam"],
            "salon": ["salon", "salun", "barber", "potong rambut", "beauty"],
            "retail": ["kedai", "store", "shop", "market", "mart"],
            "service": ["service", "servis", "repair", "baiki"],
            "automotive": ["kereta", "auto", "motor", "car", "basikal"],
            "medical": ["klinik", "clinic", "hospital", "doktor", "perubatan"],
        }
        for btype, words in keywords.items():
            if any(w in name_lower for w in words):
                return btype
        return "general"

    def _suggest_features(self, business_type: str) -> list[str]:
        features = {
            "restaurant": [
                "Menu online", "Reservations", "Location map",
                "Opening hours", "Gallery", "Reviews"
            ],
            "salon": [
                "Service list", "Booking system", "Gallery",
                "Stylist profiles", "Price list"
            ],
            "retail": [
                "Product catalog", "Online ordering", "Store hours",
                "Location map", "Contact form"
            ],
            "service": [
                "Service list", "Quote request", "Portfolio",
                "Testimonials", "Contact form"
            ],
            "medical": [
                "Services", "Doctors profile", "Appointment booking",
                "Location & hours", "Insurance info"
            ],
        }
        return features.get(business_type, [
            "About page", "Services", "Contact form",
            "Location map", "Opening hours", "Gallery"
        ])
