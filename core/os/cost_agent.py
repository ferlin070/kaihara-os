"""
Cost Agent - track API spend, optimize model usage.
Switch to local models if overspending.
"""

import json
import os
from datetime import datetime, date
from typing import Any

from core.os.base_os_agent import BaseOSAgent


class CostAgent(BaseOSAgent):
    """Track and optimize LLM API costs."""

    AGENT_TYPE = "os_cost"
    INTERVAL = 300  # 5 minutes

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.log_path = config.get("cost_log", "./data/api_costs.json")
        self.daily_budget = config.get("daily_budget", 10.0)
        self.monthly_budget = config.get("monthly_budget", 100.0)
        self._costs: dict[str, dict] = {}
        self._load_costs()

    def _load_costs(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, encoding="utf-8") as f:
                    self._costs = json.load(f)
            except Exception:
                self._costs = {}

    def _save_costs(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self._costs, f, indent=2)

    def record_usage(self, provider: str, model: str,
                      input_tokens: int, output_tokens: int,
                      cost: float = 0.0):
        """Record an API usage."""
        today = date.today().isoformat()
        if today not in self._costs:
            self._costs[today] = {"total": 0.0, "calls": 0,
                                   "by_provider": {}}
        day = self._costs[today]
        day["total"] += cost
        day["calls"] += 1
        prov_key = f"{provider}/{model}"
        if prov_key not in day["by_provider"]:
            day["by_provider"][prov_key] = {"cost": 0.0, "calls": 0,
                                             "tokens": 0}
        p = day["by_provider"][prov_key]
        p["cost"] += cost
        p["calls"] += 1
        p["tokens"] += input_tokens + output_tokens
        self._save_costs()

    async def run_task(self) -> dict:
        today = date.today().isoformat()
        today_cost = self._costs.get(today, {}).get("total", 0.0)
        month_cost = self._get_month_cost()
        alerts = []
        if today_cost > self.daily_budget:
            alerts.append({
                "action": "daily_budget_exceeded",
                "severity": "critical",
                "spent": today_cost,
                "budget": self.daily_budget,
            })
        if month_cost > self.monthly_budget:
            alerts.append({
                "action": "monthly_budget_exceeded",
                "severity": "critical",
                "spent": month_cost,
                "budget": self.monthly_budget,
            })
        return {
            "agent": self.AGENT_TYPE,
            "today_cost": round(today_cost, 4),
            "month_cost": round(month_cost, 4),
            "daily_budget": self.daily_budget,
            "monthly_budget": self.monthly_budget,
            "today_calls": self._costs.get(today, {}).get("calls", 0),
            "alerts": alerts,
        }

    def _get_month_cost(self) -> float:
        now = date.today()
        total = 0.0
        for day_str, data in self._costs.items():
            try:
                d = date.fromisoformat(day_str)
                if d.year == now.year and d.month == now.month:
                    total += data.get("total", 0.0)
            except Exception:
                continue
        return total

    def should_switch_to_local(self) -> bool:
        """Check if we should switch to local models."""
        today = date.today().isoformat()
        today_cost = self._costs.get(today, {}).get("total", 0.0)
        return today_cost > self.daily_budget

    def status(self) -> dict:
        return {**super().status(),
                "daily_budget": self.daily_budget,
                "monthly_budget": self.monthly_budget,
                "last_result": self._last_result}
