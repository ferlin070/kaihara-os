"""
Update Agent - patch OS, update packages, update Ollama models.
"""

import subprocess
import os
from datetime import datetime

from core.os.base_os_agent import BaseOSAgent


class UpdateAgent(BaseOSAgent):
    """Check and apply updates: OS packages, Python deps, models."""

    AGENT_TYPE = "os_update"
    INTERVAL = 86400  # daily

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.auto_update = config.get("auto_update", False)
        self.update_ollama = config.get("update_ollama", True)

    async def run_task(self) -> dict:
        os_updates = self._check_os_updates()
        pip_updates = self._check_pip_updates()
        ollama_models = self._check_ollama_models()
        alerts = []
        if os_updates.get("available"):
            alerts.append({
                "action": "os_updates_available",
                "severity": "info",
                "count": os_updates.get("count", 0),
            })
        return {
            "agent": self.AGENT_TYPE,
            "os_updates": os_updates,
            "pip_updates": pip_updates,
            "ollama_models": ollama_models,
            "auto_update": self.auto_update,
            "alerts": alerts,
        }

    def _check_os_updates(self) -> dict:
        try:
            if os.path.exists("/usr/bin/apt"):
                r = subprocess.run(
                    ["apt", "list", "--upgradable"],
                    capture_output=True, text=True, timeout=30
                )
                lines = r.stdout.strip().split("\n")[1:]
                return {"available": len(lines) > 0,
                        "count": len(lines), "packages": lines[:10]}
            return {"available": False, "note": "not apt-based"}
        except Exception:
            return {"available": False, "error": "check failed"}

    def _check_pip_updates(self) -> dict:
        try:
            r = subprocess.run(
                ["pip", "list", "--outdated"],
                capture_output=True, text=True, timeout=30
            )
            lines = r.stdout.strip().split("\n")
            outdated = [l for l in lines if l.strip() and "---" not in l]
            return {"outdated": len(outdated) - 1 if outdated else 0,
                    "packages": outdated[1:6] if len(outdated) > 1 else []}
        except Exception:
            return {"error": "pip check failed"}

    def _check_ollama_models(self) -> dict:
        try:
            r = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode != 0:
                return {"available": False}
            lines = r.stdout.strip().split("\n")
            models = [l.split()[0] for l in lines[1:] if l.strip()]
            return {"available": True, "models": models,
                    "count": len(models)}
        except FileNotFoundError:
            return {"available": False, "note": "ollama not installed"}
        except Exception:
            return {"available": False, "error": "check failed"}

    def status(self) -> dict:
        return {**super().status(),
                "auto_update": self.auto_update}
