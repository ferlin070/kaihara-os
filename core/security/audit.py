"""
Audit Trail - log every agent action for traceability.
Inspired by CyberStrikeAI (#56) human-in-the-loop audit.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class AuditTrail:
    """Append-only audit log for all agent actions."""

    def __init__(self, log_path: str = "./data/audit.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, agent: str, action: str, details: dict,
            result: dict | None = None, severity: str = "info"):
        """Log an action to the audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "details": details,
            "result": result,
            "severity": severity,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def get_log(self, limit: int = 100,
                agent: str = None,
                action: str = None,
                severity: str = None) -> list[dict]:
        """Read audit log with optional filters."""
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if agent and entry.get("agent") != agent:
                        continue
                    if action and entry.get("action") != action:
                        continue
                    if severity and entry.get("severity") != severity:
                        continue
                    entries.append(entry)
                except Exception:
                    continue
        return entries[-limit:]

    def get_stats(self) -> dict:
        """Get audit log statistics."""
        entries = self.get_log(limit=10000)
        if not entries:
            return {"total": 0, "by_agent": {}, "by_severity": {}}
        by_agent: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for e in entries:
            a = e.get("agent", "unknown")
            by_agent[a] = by_agent.get(a, 0) + 1
            s = e.get("severity", "info")
            by_severity[s] = by_severity.get(s, 0) + 1
        return {
            "total": len(entries),
            "by_agent": by_agent,
            "by_severity": by_severity,
        }

    def status(self) -> dict:
        return {
            "log_path": str(self.log_path),
            "exists": self.log_path.exists(),
            "size_bytes": self.log_path.stat().st_size if self.log_path.exists() else 0,
            **self.get_stats(),
        }
