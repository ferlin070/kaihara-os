"""
MarketingAgent — specialized agent with real marketing tools.
Handles lead generation, content creation, SEO analysis, campaign management.
"""

import json
from agents.base_agent import GenericAgent
from core.tools.web_tools import (
    web_search, scrape_website, search_places,
    analyze_competitor, social_monitor, seo_audit, keyword_research,
)


class MarketingAgent(GenericAgent):
    """Marketing agent with real tool capabilities."""

    AGENT_TYPE = "marketing"
    SOUL_FILE = "marketing.md"

    TOOLS = {
        "web_search": web_search,
        "scrape_website": scrape_website,
        "search_places": search_places,
        "analyze_competitor": analyze_competitor,
        "social_monitor": social_monitor,
        "seo_audit": seo_audit,
        "keyword_research": keyword_research,
    }

    def __init__(self, config=None, memory=None, audit=None, skill_registry=None):
        super().__init__(config, memory, audit, skill_registry)
        self._register_tools()

    def _register_tools(self):
        """Register marketing-specific tools."""
        for name, func in self.TOOLS.items():
            self.register_tool(name, func)

    async def run(self, task: str, context: dict = None) -> dict:
        """Run marketing task with tool selection."""
        context = context or {}
        task_lower = task.lower()

        # Auto-select tools based on task content
        tool_hints = []

        if any(w in task_lower for w in ["competitor", "pesaing", "analis pesaing"]):
            tool_hints.append("analyze_competitor")
        if any(w in task_lower for w in ["seo", "ranking", "search engine"]):
            tool_hints.append("seo_audit")
        if any(w in task_lower for w in ["keyword", "kata kunci", "search volume"]):
            tool_hints.append("keyword_research")
        if any(w in task_lower for w in ["social", "media sosial", "mention"]):
            tool_hints.append("social_monitor")
        if any(w in task_lower for w in ["scrape", "website", "laman web", "extract"]):
            tool_hints.append("scrape_website")
        if any(w in task_lower for w in ["search", "cari", "find", "temui"]):
            tool_hints.append("web_search")
        if any(w in task_lower for w in ["tempat", "location", "premis", "business"]):
            tool_hints.append("search_places")

        # If we identified specific tools, run them first
        tool_results = []
        for tool_name in tool_hints:
            tool_func = self.TOOLS.get(tool_name)
            if tool_func:
                try:
                    # Extract URL/keyword from task if present
                    import re
                    urls = re.findall(r'https?://[^\s]+', task)
                    keywords = re.findall(r'"([^"]+)"', task)

                    if tool_name in ("analyze_competitor", "seo_audit") and urls:
                        result = tool_func(urls[0])
                    elif tool_name == "keyword_research" and keywords:
                        result = tool_func(keywords[0])
                    elif tool_name == "social_monitor" and keywords:
                        result = tool_func(keywords[0])
                    elif tool_name == "web_search":
                        search_term = keywords[0] if keywords else task[:100]
                        result = tool_func(search_term)
                    elif tool_name == "scrape_website" and urls:
                        result = tool_func(urls[0])
                    elif tool_name == "search_places":
                        result = tool_func(task[:100])
                    else:
                        continue

                    tool_results.append({"tool": tool_name, "result": json.loads(result)})
                except Exception as e:
                    tool_results.append({"tool": tool_name, "error": str(e)})

        # Build enhanced context with tool results
        enhanced_context = dict(context)
        if tool_results:
            enhanced_context["tool_results"] = tool_results

        # Run the agent with enhanced context
        result = await super().run(task, enhanced_context)
        result["tools_used"] = [t["tool"] for t in tool_results if "result" in t]
        return result

    def status(self) -> dict:
        """Get marketing agent status with tool info."""
        base_status = super().status()
        base_status["tools"] = list(self.TOOLS.keys())
        base_status["agent_type"] = "marketing"
        return base_status
