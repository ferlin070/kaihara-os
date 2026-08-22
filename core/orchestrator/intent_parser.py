"""
Intent Parser — proper intent classification.
Combines keyword heuristics + LLM classification for accuracy.
Two-stage: fast keyword pre-filter → LLM classification if ambiguous.
"""

import re
from typing import Any


class IntentParser:
    """Parse user input to understand intent + route to correct agents."""

    # Pattern-based intent rules (ordered by specificity)
    INTENT_RULES = [
        {
            "type": "coding",
            "agents": ["coding"],
            "patterns": [
                r"\b(bina|build|code|coding|program|function|api|debug|fix|refactor|deploy|git|commit)\b",
                r"\b(write|create|generate)\s+(code|app|website|api|function|component)\b",
                r"\b(test|lint|format|build)\b",
            ],
            "complexity": "complex",
        },
        {
            "type": "security",
            "agents": ["security"],
            "patterns": [
                r"\b(pentest|security|vuln|vulnerability|exploit|hack|scan|nmap|sqlmap|nikto)\b",
                r"\b(security\s+check|penetration\s+test|firewall|encrypt)\b",
            ],
            "complexity": "complex",
        },
        {
            "type": "marketing",
            "agents": ["marketing"],
            "patterns": [
                r"\b(market|marketing|scrape|trending|product|sales|revenue|content|ad|campaign)\b",
                r"\b(analyze|analysis)\s+(market|product|trend|competitor)\b",
            ],
            "complexity": "complex",
        },
        {
            "type": "research",
            "agents": ["research"],
            "patterns": [
                r"\b(research|search|find|cari|analyze|study|investigate)\b",
                r"\b(what|how|why|when|where|apa|bagaimana|kenapa|bila|mana)\b",
            ],
            "complexity": "medium",
        },
        {
            "type": "deploy",
            "agents": ["deploy"],
            "patterns": [
                r"\b(deploy|docker|container|server|kubernetes|k8s|nginx|traefik)\b",
                r"\b(setup|install|configure)\s+(server|docker|nginx)\b",
            ],
            "complexity": "complex",
        },
        {
            "type": "planning",
            "agents": ["kaihara"],
            "patterns": [
                r"\b(plan|prd|spec|requirements|design|architecture)\b",
                r"\b(bina|build|create)\s+(app|system|project|software)\b",
            ],
            "complexity": "complex",
        },
        {
            "type": "simple",
            "agents": ["kaihara"],
            "patterns": [
                r"\b(hello|hi|hey|hai|apa\s+khabar|thank|terima\s+kasih|bye|goodbye)\b",
                r"\b(status|help|what\s+can\s+you\s+do|bantuan)\b",
                r"^(yes|no|ya|tidak|ok|okay|sure)$",
            ],
            "complexity": "simple",
        },
    ]

    WORKFLOW_KEYWORDS = [
        "automate", "schedule", "every", "trigger", "workflow",
        "setiap", "jadual", "ulang", "automatik",
    ]

    def __init__(self, model_router=None):
        self.model = model_router

    async def parse(self, text: str) -> dict:
        """Parse intent from user text. Two-stage: rules → LLM if ambiguous."""
        text_lower = text.lower().strip()

        # Stage 1: Pattern-based classification
        intent = self._classify_by_patterns(text_lower)

        # Check workflow trigger
        is_workflow = any(k in text_lower for k in self.WORKFLOW_KEYWORDS)

        # Stage 2: If ambiguous, use LLM classification
        if intent["confidence"] < 0.6 and self.model:
            llm_intent = await self._classify_with_llm(text)
            if llm_intent:
                intent = llm_intent

        intent["text"] = text
        intent["is_workflow"] = is_workflow
        return intent

    def _classify_by_patterns(self, text: str) -> dict:
        """Classify intent using regex patterns."""
        scores: dict[str, int] = {}
        matched_agents = set()
        best_type = "simple"
        best_score = 0
        best_complexity = "simple"

        for rule in self.INTENT_RULES:
            score = 0
            for pattern in rule["patterns"]:
                matches = re.findall(pattern, text)
                score += len(matches)
            if score > 0:
                scores[rule["type"]] = score
                if score > best_score:
                    best_score = score
                    best_type = rule["type"]
                    best_complexity = rule["complexity"]
                    matched_agents = set(rule["agents"])

        # If multiple intents matched, combine agents
        if len(scores) > 1:
            for rule in self.INTENT_RULES:
                if rule["type"] in scores:
                    matched_agents.update(rule["agents"])

        total_score = sum(scores.values())
        confidence = min(best_score / max(total_score, 1), 1.0) if total_score > 0 else 0.0

        if total_score == 0:
            return {
                "type": "simple",
                "agents": ["kaihara"],
                "confidence": 0.0,
                "complexity": "simple",
            }

        return {
            "type": best_type,
            "agents": list(matched_agents) if matched_agents else ["kaihara"],
            "confidence": round(confidence, 2),
            "complexity": best_complexity,
            "scores": scores,
        }

    async def _classify_with_llm(self, text: str) -> dict | None:
        """Use LLM for ambiguous intents."""
        try:
            system = (
                "You are an intent classifier. Classify the user's message "
                "into one of: coding, security, marketing, research, deploy, "
                "planning, simple. Respond with JSON: "
                '{"type":"...","agents":["..."],"complexity":"simple|medium|complex"}'
            )
            response = await self.model.complete(
                system=system,
                messages=[{"role": "user", "content": text}],
                model=None,  # use default model
            )
            # Parse JSON from response
            import json
            match = re.search(r"\{.*\}", response)
            if match:
                data = json.loads(match.group(0))
                return {
                    "type": data.get("type", "simple"),
                    "agents": data.get("agents", ["kaihara"]),
                    "confidence": 0.8,
                    "complexity": data.get("complexity", "simple"),
                    "source": "llm",
                }
        except Exception:
            pass
        return None
