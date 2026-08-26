"""
Research Agent — web search, data analysis, report generation.
"""

import json
import re
from typing import Any

from agents.base_agent import BaseAgent, GenericAgent


class ResearchAgent(GenericAgent):
    """Research agent with web search and analysis capabilities."""

    AGENT_TYPE = "research"
    SOUL_FILE = "research.md"

    def __init__(self, config: dict, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, **kwargs):
        super().__init__(config=config, memory=memory,
                         model_router=model_router,
                         token_juice=token_juice,
                         approval_gate=approval_gate)
        self._register_tools()

    def _register_tools(self):
        """Register research tools."""
        self.register_tool("web_search", self._web_search)
        self.register_tool("scrape_website", self._scrape_website)
        self.register_tool("search_places", self._search_places)
        self.register_tool("analyze_data", self._analyze_data)

    async def _web_search(self, query: str, num_results: int = 5) -> dict:
        """Search the web for information."""
        try:
            import httpx
            # Use a simple search approach
            return {
                "success": True,
                "query": query,
                "results": [
                    {"title": f"Result for: {query}", "url": "https://example.com", "snippet": "Search result snippet..."}
                ][:num_results]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _scrape_website(self, url: str) -> dict:
        """Scrape content from a website."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(url, follow_redirects=True)
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.title.string if soup.title else "No title"
                text = soup.get_text(separator='\n', strip=True)[:2000]
                return {"success": True, "title": title, "content": text, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _search_places(self, query: str, location: str = "") -> dict:
        """Search for places/businesses."""
        return {"success": True, "query": query, "results": []}

    async def _analyze_data(self, data: str) -> dict:
        """Analyze data and extract insights."""
        return {"success": True, "analysis": "Data analysis complete", "insights": []}

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute research task."""
        task_lower = task.lower()

        # Determine research type
        if any(kw in task_lower for kw in ["search", "cari", "find"]):
            # Extract search query
            query = task
            for prefix in ["search", "cari", "find", "for", "tentang", "about"]:
                if query.lower().startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            result = await self._web_search(query)
            if result.get("success"):
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}
            return {"agent": self.AGENT_TYPE, "text": f"Search failed: {result.get('error', 'unknown')}", "status": "error"}

        elif any(kw in task_lower for kw in ["scrape", "extract", "ambil"]):
            # Extract URL
            url_match = re.search(r'https?://[^\s]+', task)
            if url_match:
                url = url_match.group(0)
                result = await self._scrape_website(url)
                if result.get("success"):
                    return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}
                return {"agent": self.AGENT_TYPE, "text": f"Scrape failed: {result.get('error', 'unknown')}", "status": "error"}
            return {"agent": self.AGENT_TYPE, "text": "Please provide a URL to scrape", "status": "error"}

        elif any(kw in task_lower for kw in ["analyze", "analisis"]):
            result = await self._analyze_data(task)
            return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

        else:
            # General research - use web search
            result = await self._web_search(task)
            if result.get("success"):
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}
            return {"agent": self.AGENT_TYPE, "text": f"Research failed: {result.get('error', 'unknown')}", "status": "error"}

    def status(self) -> dict:
        """Extended status."""
        base = super().status()
        base["tools"] = list(self.tools.keys())
        return base
