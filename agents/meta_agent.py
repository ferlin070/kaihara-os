"""
Meta Agent - learns from other agents, suggests optimizations,
corrects inefficiencies, prevents repetition.
"""

import json
import time
from datetime import datetime, date
from typing import Any

from agents.base_agent import BaseAgent
from core.brain.learning_cache import LearningCache


class MetaAgent(BaseAgent):
    """Observe, learn, optimize all other agents."""

    AGENT_TYPE = "meta"
    SOUL_FILE = "meta.md"

    # Thresholds
    TOKEN_WASTE_THRESHOLD = 2000     # tokens for a simple task
    FAILED_RETRY_LIMIT = 3           # max retries before suggest change
    BUDGET_ALERT_PERCENT = 80        # alert at 80% budget
    DUPLICATE_OUTPUT_THRESHOLD = 0.95  # 95% similar = duplicate

    def __init__(self, config, memory=None, model_router=None,
                 token_juice=None, approval_gate=None):
        super().__init__(config, memory, model_router,
                         token_juice, approval_gate)
        db_path = config.get("db_path", "./data/kaihara.db")
        self.cache = LearningCache(db_path)
        self._observing = True

    async def run(self, task: str, context: dict = None) -> dict:
        """Main: analyze fleet, return suggestions."""
        analysis = await self.analyze_fleet()
        suggestions = await self.generate_suggestions(analysis)
        corrections = await self.generate_corrections(analysis)
        return {
            "agent": self.AGENT_TYPE,
            "analysis": analysis,
            "suggestions": suggestions,
            "corrections": corrections,
            "message": self._summarize(suggestions, corrections),
        }

    async def analyze_fleet(self) -> dict:
        """Analyze all agent activity for patterns."""
        stats = self.cache.get_agent_stats()
        cache_stats = self.cache.get_cache_stats()
        patterns = self.cache.get_patterns()
        return {
            "agent_stats": stats,
            "cache_stats": cache_stats,
            "patterns": patterns,
            "timestamp": datetime.now().isoformat(),
        }

    async def observe_run(self, agent: str, task: str,
                           result: dict, tokens_used: int = 0,
                           time_taken: float = 0,
                           model_used: str = "",
                           success: bool = True) -> dict:
        """Called after every agent run. Learn from it."""
        task_type = self._classify_task(task)

        # 1. Record stats
        self.cache.record_stats(
            agent, task_type, model_used,
            tokens_used, time_taken, success
        )

        # 2. Store result in cache
        cache_id = self.cache.store_result(
            task, agent, result,
            tokens_used, time_taken, model_used, success
        )

        # 3. Detect patterns
        detected = []
        detected.append(self._check_token_waste(
            agent, task_type, tokens_used, task
        ))
        detected.append(self._check_failure_pattern(
            agent, task_type, success
        ))
        detected.append(self._check_duplicate_output(
            agent, task, result
        ))
        detected.append(self._check_slow_agent(
            agent, task_type, time_taken
        ))
        detected.append(self._check_budget(agent, tokens_used))

        detected = [d for d in detected if d is not None]

        return {
            "observed": True,
            "agent": agent,
            "cache_id": cache_id,
            "patterns_detected": detected,
        }

    def check_before_run(self, task: str, agent: str = "") -> dict:
        """Check cache before agent runs. Prevent repetition."""
        cached = self.cache.check_cache(task, agent)
        if cached:
            return {
                "should_skip": True,
                "reason": "Task found in cache",
                "cached_result": cached["result"],
                "tokens_saved": cached.get("tokens_saved", 0),
                "similarity": cached.get("similarity", 1.0),
                "fuzzy": cached.get("fuzzy", False),
            }
        return {"should_skip": False}

    async def generate_suggestions(self, analysis: dict) -> list[dict]:
        """Generate optimization suggestions from analysis."""
        suggestions = []
        stats = analysis.get("agent_stats", [])

        for stat in stats:
            agent = stat.get("agent", "")
            total_tokens = stat.get("total_tokens", 0)
            total_runs = stat.get("total_runs", 0)
            success_count = stat.get("success_count", 0)
            avg_time = stat.get("avg_time", 0)
            model = stat.get("model", "")

            # Token waste suggestion
            if total_runs > 0:
                avg_tokens = total_tokens / total_runs
                if avg_tokens > self.TOKEN_WASTE_THRESHOLD:
                    suggestions.append({
                        "type": "token_waste",
                        "agent": agent,
                        "model": model,
                        "issue": (f"{agent} averages {int(avg_tokens)} "
                                  f"tokens per task"),
                        "suggestion": ("Use shorter prompts or switch to "
                                        "cheaper model for simple tasks"),
                        "severity": "warning",
                    })

            # Success rate suggestion
            if total_runs > 2:
                success_rate = success_count / total_runs
                if success_rate < 0.5:
                    suggestions.append({
                        "type": "low_success",
                        "agent": agent,
                        "model": model,
                        "issue": (f"{agent} success rate: "
                                  f"{int(success_rate * 100)}%"),
                        "suggestion": (f"Try different model or approach. "
                                        f"Current: {model}"),
                        "severity": "critical",
                    })

            # Slow agent suggestion
            if avg_time and avg_time > 60:
                suggestions.append({
                    "type": "slow_agent",
                    "agent": agent,
                    "model": model,
                    "issue": (f"{agent} averages "
                              f"{int(avg_time)}s per task"),
                    "suggestion": "Use faster model or simplify task",
                    "severity": "warning",
                })

        # Cache suggestions
        cache_stats = analysis.get("cache_stats", {})
        if cache_stats.get("cache_hits", 0) > 0:
            suggestions.append({
                "type": "cache_working",
                "agent": "all",
                "issue": (f"Cache saved {cache_stats['cache_hits']} "
                          f"repeated runs"),
                "suggestion": "Cache is active and saving tokens",
                "severity": "info",
            })

        return suggestions

    async def generate_corrections(self, analysis: dict) -> list[dict]:
        """Generate corrections for detected patterns."""
        patterns = analysis.get("patterns", [])
        corrections = []
        for p in patterns:
            if p.get("frequency", 0) >= 2:
                corrections.append({
                    "pattern": p["pattern_type"],
                    "agent": p.get("agent", ""),
                    "issue": p["description"],
                    "correction": p.get("suggestion", "Review approach"),
                    "frequency": p["frequency"],
                    "severity": p.get("severity", "info"),
                })
        return corrections

    def _classify_task(self, task: str) -> str:
        """Classify task type from text."""
        t = task.lower()
        if any(k in t for k in ["code", "bina", "build", "function"]):
            return "coding"
        if any(k in t for k in ["scrape", "market", "analisis"]):
            return "marketing"
        if any(k in t for k in ["pentest", "scan", "security"]):
            return "security"
        if any(k in t for k in ["deploy", "docker", "server"]):
            return "deploy"
        if any(k in t for k in ["search", "cari", "research"]):
            return "research"
        return "general"

    def _check_token_waste(self, agent: str, task_type: str,
                             tokens: int, task: str) -> dict | None:
        """Detect token waste."""
        if tokens > self.TOKEN_WASTE_THRESHOLD and task_type == "general":
            return self.cache.detect_pattern(
                "token_waste", agent,
                f"{agent} used {tokens} tokens for simple task",
                "warning",
                f"Shorten prompt or use smaller model (llama3.1:1b)"
            )
        return None

    def _check_failure_pattern(self, agent: str, task_type: str,
                                 success: bool) -> dict | None:
        """Detect repeated failures."""
        if not success:
            stats = self.cache.get_agent_stats(agent=agent)
            fail_count = sum(
                1 for s in stats
                if s.get("total_runs", 0) > 0
                and s.get("success_count", 0) < s["total_runs"] / 2
            )
            if fail_count >= self.FAILED_RETRY_LIMIT:
                return self.cache.detect_pattern(
                    "repeated_failure", agent,
                    f"{agent} failed {fail_count}x on {task_type}",
                    "critical",
                    f"Switch model or restructure task for {agent}"
                )
        return None

    def _check_duplicate_output(self, agent: str, task: str,
                                  result: dict) -> dict | None:
        """Detect if output is duplicate of previous."""
        cached = self.cache.check_cache(task, agent)
        if cached and cached.get("access_count", 0) > 3:
            return self.cache.detect_pattern(
                "duplicate_task", agent,
                f"Task '{task[:50]}' done {cached['access_count']}x",
                "warning",
                "Use cached result. Skip agent run."
            )
        return None

    def _check_slow_agent(self, agent: str, task_type: str,
                           time_taken: float) -> dict | None:
        """Detect slow agents."""
        if time_taken > 120:
            return self.cache.detect_pattern(
                "slow_agent", agent,
                f"{agent} took {int(time_taken)}s for {task_type}",
                "warning",
                "Use faster model or simplify task"
            )
        return None

    def _check_budget(self, agent: str, tokens: int) -> dict | None:
        """Check token budget."""
        # This would connect to CostAgent in production
        return None

    def _summarize(self, suggestions: list,
                    corrections: list) -> str:
        """Summarize findings in ADHD-friendly format."""
        if not suggestions and not corrections:
            return "Fleet running efficiently. No issues detected."
        parts = []
        crit = [c for c in corrections if c.get("severity") == "critical"]
        warn = [c for c in corrections if c.get("severity") == "warning"]
        if crit:
            parts.append(f"{len(crit)} critical issues need attention.")
        if warn:
            parts.append(f"{len(warn)} warnings to review.")
        if suggestions:
            parts.append(f"{len(suggestions)} optimizations suggested.")
        cache = self.cache.get_cache_stats()
        if cache["cache_hits"] > 0:
            parts.append(f"Cache saved {cache['cache_hits']} repeated runs.")
        return " ".join(parts)

    def status(self) -> dict:
        base = super().status()
        cache_stats = self.cache.get_cache_stats()
        patterns = self.cache.get_patterns()
        return {
            **base,
            "observing": self._observing,
            "cache": cache_stats,
            "patterns_detected": len(patterns),
            "suggestions_available": len(
                self.cache.get_suggestions()
            ),
        }
