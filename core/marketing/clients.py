"""
Client Management — client database with email/WhatsApp approval flow.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.marketing.leads import _get_db


def create_client(name: str, email: str = "", phone: str = "",
                  company: str = "", address: str = "", lead_id: int = None,
                  tier: str = "basic", notes: str = "",
                  tags: list[str] = None) -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO clients (lead_id, name, email, phone, company, address, tier, notes, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lead_id, name, email, phone, company, address, tier, notes, json.dumps(tags or []))
    )
    client_id = cur.lastrowid
    conn.commit()
    client = dict(conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone())
    conn.close()
    return client


def get_clients(status: str = None, tier: str = None, search: str = None,
                limit: int = 50, offset: int = 0) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM clients WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if tier:
        query += " AND tier=?"
        params.append(tier)
    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR company LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    clients = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return clients


def get_client(client_id: int) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_client(client_id: int, **kwargs) -> Optional[dict]:
    conn = _get_db()
    allowed = {"name", "email", "phone", "company", "address", "status",
               "tier", "total_paid", "total_invoiced", "notes", "tags",
               "whatsapp_verified", "email_verified"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return None
    updates["updated_at"] = datetime.now().isoformat()
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [client_id]
    conn.execute(f"UPDATE clients SET {set_clause} WHERE id=?", values)
    conn.commit()
    client = dict(conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone())
    conn.close()
    return client


def delete_client(client_id: int) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    return True


def client_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM clients GROUP BY status"):
        by_status[row["status"]] = row["cnt"]
    by_tier = {}
    for row in conn.execute("SELECT tier, COUNT(*) as cnt FROM clients GROUP BY tier"):
        by_tier[row["tier"]] = row["cnt"]
    revenue = conn.execute("SELECT COALESCE(SUM(total_paid), 0) FROM clients").fetchone()[0]
    invoiced = conn.execute("SELECT COALESCE(SUM(total_invoiced), 0) FROM clients").fetchone()[0]
    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "by_tier": by_tier,
        "total_revenue": revenue,
        "total_invoiced": invoiced,
    }


# ============================================================
# Approval Flow — Email/WhatsApp
# ============================================================

def create_approval(approval_type: str, ref_id: int, requested_by: str = "marketing",
                    channel: str = "email", message: str = "") -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO approvals (type, ref_id, requested_by, channel, message)
           VALUES (?, ?, ?, ?, ?)""",
        (approval_type, ref_id, requested_by, channel, message)
    )
    approval_id = cur.lastrowid
    conn.commit()
    approval = dict(conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone())
    conn.close()
    return approval


def get_pending_approvals() -> list[dict]:
    conn = _get_db()
    approvals = [dict(r) for r in conn.execute(
        "SELECT * FROM approvals WHERE status='pending' ORDER BY created_at DESC"
    ).fetchall()]
    conn.close()
    return approvals


def respond_to_approval(approval_id: int, response: str, approved: bool) -> Optional[dict]:
    conn = _get_db()
    status = "approved" if approved else "denied"
    conn.execute(
        """UPDATE approvals SET status=?, response=?, responded_at=?
           WHERE id=?""",
        (status, response, datetime.now().isoformat(), approval_id)
    )
    conn.commit()
    approval = dict(conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone())
    conn.close()
    return approval


def send_approval_request(client_id: int, approval_type: str,
                          ref_id: int, message: str,
                          channels: list[str] = None) -> dict:
    """Create approval and send via notification service."""
    channels = channels or ["email"]
    approval = create_approval(approval_type, ref_id, "marketing", channels[0], message)

    # Log activity
    conn = _get_db()
    conn.execute(
        """INSERT INTO activity_log (entity_type, entity_id, action, details)
           VALUES (?, ?, ?, ?)""",
        ("approval", approval["id"], "request_sent",
         json.dumps({"client_id": client_id, "channels": channels}))
    )
    conn.commit()
    conn.close()

    return {
        "approval_id": approval["id"],
        "status": "pending",
        "channels": channels,
        "message": message,
    }


# ============================================================
# Activity Log
# ============================================================

def log_activity(entity_type: str, entity_id: int, action: str,
                 details: dict = None, agent: str = "marketing"):
    conn = _get_db()
    conn.execute(
        """INSERT INTO activity_log (entity_type, entity_id, action, details, agent)
           VALUES (?, ?, ?, ?, ?)""",
        (entity_type, entity_id, action, json.dumps(details or {}), agent)
    )
    conn.commit()
    conn.close()


def get_activity_log(limit: int = 20) -> list[dict]:
    conn = _get_db()
    logs = [dict(r) for r in conn.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()]
    conn.close()
    return logs
