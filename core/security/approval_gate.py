"""
Approval Gate - 6-step approval/rollback/verification (Claude Ads #39).
Human-in-the-loop for all dangerous actions.
"""

import json
import os
from datetime import datetime
from typing import Any
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ROLLED_BACK = "rolled_back"
    VERIFIED = "verified"
    FAILED = "failed"


class ApprovalGate:
    """6-step gate: request -> review -> approve -> execute -> verify -> rollback-ready."""

    REQUIRES_APPROVAL = [
        "deploy_to_production",
        "push_to_git",
        "send_email",
        "send_whatsapp",
        "send_telegram",
        "run_pentest",
        "execute_exploit",
        "delete_file",
        "execute_shell",
        "spend_money",
        "install_package",
        "access_external_system",
        "modify_database",
        "stop_service",
        "restart_service",
    ]

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._pending: dict[str, dict] = {}
        self._history: list[dict] = []

    def requires_approval(self, action: str) -> bool:
        return action in self.REQUIRES_APPROVAL

    async def request(self, action: str, agent_type: str,
                       details: dict, callback=None) -> dict:
        """Step 1-2: Request approval for an action."""
        if not self.requires_approval(action):
            return {"status": "auto_approved", "action": action}

        request_id = f"appr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{action[:8]}"
        entry = {
            "id": request_id,
            "action": action,
            "agent": agent_type,
            "details": details,
            "status": ApprovalStatus.PENDING.value,
            "callback": callback,
            "created_at": datetime.now().isoformat(),
        }
        self._pending[request_id] = entry
        return {
            "status": "pending",
            "request_id": request_id,
            "action": action,
            "agent": agent_type,
            "details": details,
            "message": f"Approval required for: {action}",
        }

    async def approve(self, request_id: str) -> dict:
        """Step 3: User approves the action."""
        entry = self._pending.get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        entry["status"] = ApprovalStatus.APPROVED.value
        entry["approved_at"] = datetime.now().isoformat()
        return {
            "status": "approved",
            "request_id": request_id,
            "action": entry["action"],
            "message": "Proceeding with action.",
        }

    async def deny(self, request_id: str,
                    reason: str = "") -> dict:
        """User denies the action."""
        entry = self._pending.get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        entry["status"] = ApprovalStatus.DENIED.value
        entry["denied_at"] = datetime.now().isoformat()
        entry["reason"] = reason
        self._history.append(entry)
        del self._pending[request_id]
        return {
            "status": "denied",
            "request_id": request_id,
            "reason": reason,
        }

    async def verify(self, request_id: str,
                      result: dict) -> dict:
        """Step 5: Verify the action succeeded."""
        entry = self._pending.get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        if result.get("success"):
            entry["status"] = ApprovalStatus.VERIFIED.value
            entry["verified_at"] = datetime.now().isoformat()
        else:
            entry["status"] = ApprovalStatus.FAILED.value
            entry["failed_at"] = datetime.now().isoformat()
        entry["result"] = result
        self._history.append(entry)
        del self._pending[request_id]
        return {
            "status": entry["status"],
            "request_id": request_id,
            "result": result,
        }

    async def rollback(self, request_id: str,
                        rollback_fn=None) -> dict:
        """Step 6: Rollback if verification failed."""
        for entry in self._history:
            if entry["id"] == request_id:
                if rollback_fn:
                    try:
                        await rollback_fn()
                        entry["status"] = ApprovalStatus.ROLLED_BACK.value
                        entry["rolled_back_at"] = datetime.now().isoformat()
                    except Exception as e:
                        return {"error": f"Rollback failed: {e}"}
                return {
                    "status": "rolled_back",
                    "request_id": request_id,
                }
        return {"error": "Approval request not found in history"}

    def get_pending(self) -> list[dict]:
        return list(self._pending.values())

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]

    def status(self) -> dict:
        return {
            "pending_count": len(self._pending),
            "history_count": len(self._history),
            "requires_approval": self.REQUIRES_APPROVAL,
        }
