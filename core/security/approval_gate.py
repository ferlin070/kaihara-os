"""
Approval Gate - 6-step approval/rollback/verification (Claude Ads #39).
Human-in-the-loop for all dangerous actions.
PERSISTENT: approvals survive restarts (SQLite).
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
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
        db_path = self.config.get("db_path", "./data/kaihara.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                agent TEXT,
                details TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                result TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_appr_status "
            "ON approvals(status, created_at)")
        self.conn.commit()
        # In-memory callbacks only (cannot persist functions)
        self._callbacks: dict[str, Any] = {}

    def requires_approval(self, action: str) -> bool:
        return action in self.REQUIRES_APPROVAL

    async def request(self, action: str, agent_type: str,
                       details: dict, callback=None) -> dict:
        """Step 1-2: Request approval for an action."""
        if not self.requires_approval(action):
            return {"status": "auto_approved", "action": action}

        request_id = f"appr_{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}_{action[:8]}"
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO approvals "
            "(id, action, agent, details, status, created_at) VALUES (?,?,?,?,?,?)",
            (request_id, action, agent_type,
             json.dumps(details or {}), ApprovalStatus.PENDING.value, now)
        )
        self.conn.commit()
        if callback:
            self._callbacks[request_id] = callback
        return {
            "status": "pending",
            "request_id": request_id,
            "action": action,
            "agent": agent_type,
            "details": details,
            "message": f"Approval required for: {action}",
        }

    def _get(self, request_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM approvals WHERE id = ?", (request_id,)
        ).fetchone()
        if not row:
            return None
        entry = dict(row)
        entry["details"] = json.loads(entry.get("details") or "{}")
        if entry.get("result"):
            try:
                entry["result"] = json.loads(entry["result"])
            except Exception:
                pass
        return entry

    def _update(self, request_id: str, **fields):
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [request_id]
        self.conn.execute(f"UPDATE approvals SET {sets} WHERE id = ?", vals)
        self.conn.commit()

    async def approve(self, request_id: str) -> dict:
        """Step 3: User approves the action."""
        entry = self._get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        if entry["status"] != ApprovalStatus.PENDING.value:
            return {"error": f"Request already {entry['status']}"}
        now = datetime.now().isoformat()
        self._update(request_id, status=ApprovalStatus.APPROVED.value,
                     resolved_at=now)
        return {
            "status": "approved",
            "request_id": request_id,
            "action": entry["action"],
            "message": "Proceeding with action.",
        }

    async def deny(self, request_id: str, reason: str = "") -> dict:
        entry = self._get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        if entry["status"] != ApprovalStatus.PENDING.value:
            return {"error": f"Request already {entry['status']}"}
        now = datetime.now().isoformat()
        self._update(request_id, status=ApprovalStatus.DENIED.value,
                     reason=reason, resolved_at=now)
        self._callbacks.pop(request_id, None)
        return {"status": "denied", "request_id": request_id, "reason": reason}

    async def verify(self, request_id: str, result: dict) -> dict:
        """Step 5: Verify the action succeeded."""
        entry = self._get(request_id)
        if not entry:
            return {"error": "Approval request not found"}
        now = datetime.now().isoformat()
        status = (ApprovalStatus.VERIFIED if result.get("success")
                  else ApprovalStatus.FAILED).value
        self._update(request_id, status=status,
                     result=json.dumps(result), resolved_at=now)
        self._callbacks.pop(request_id, None)
        return {"status": status, "request_id": request_id, "result": result}

    async def rollback(self, request_id: str, rollback_fn=None) -> dict:
        entry = self._get(request_id)
        if not entry:
            return {"error": "Approval request not found in history"}
        if rollback_fn:
            try:
                await rollback_fn()
                self._update(request_id,
                             status=ApprovalStatus.ROLLED_BACK.value,
                             resolved_at=datetime.now().isoformat())
            except Exception as e:
                return {"error": f"Rollback failed: {e}"}
        return {"status": "rolled_back", "request_id": request_id}

    def get_pending(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM approvals WHERE status = ? "
            "ORDER BY created_at DESC",
            (ApprovalStatus.PENDING.value,)
        ).fetchall()
        out = []
        for r in rows:
            e = dict(r)
            e["details"] = json.loads(e.get("details") or "{}")
            out.append(e)
        return out

    def get_history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM approvals WHERE status != ? "
            "ORDER BY resolved_at DESC LIMIT ?",
            (ApprovalStatus.PENDING.value, limit)
        ).fetchall()
        out = []
        for r in rows:
            e = dict(r)
            e["details"] = json.loads(e.get("details") or "{}")
            out.append(e)
        return out

    def status(self) -> dict:
        pending = self.get_pending()
        history = self.get_history()
        return {
            "pending_count": len(pending),
            "history_count": len(history),
            "requires_approval": self.REQUIRES_APPROVAL,
        }
