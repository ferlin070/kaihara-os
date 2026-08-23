"""
Campaign Management — create, track, and optimize marketing campaigns.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional

from core.marketing.leads import _get_db


def create_campaign(name: str, description: str = "", campaign_type: str = "general",
                    budget: float = 0, target_audience: str = "",
                    channels: list[str] = None, start_date: str = "",
                    end_date: str = "") -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO campaigns (name, description, type, budget, target_audience,
           channels, start_date, end_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, campaign_type, budget, target_audience,
         json.dumps(channels or []), start_date, end_date)
    )
    campaign_id = cur.lastrowid
    conn.commit()
    campaign = dict(conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone())
    conn.close()
    return campaign


def get_campaigns(status: str = None, limit: int = 50) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM campaigns WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    campaigns = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return campaigns


def get_campaign(campaign_id: int) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_campaign(campaign_id: int, **kwargs) -> Optional[dict]:
    conn = _get_db()
    allowed = {"name", "description", "type", "status", "budget", "spent",
               "target_audience", "channels", "content_ids", "start_date",
               "end_date", "metrics"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return None
    updates["updated_at"] = datetime.now().isoformat()
    for key in ("channels", "content_ids", "metrics"):
        if key in updates and isinstance(updates[key], (dict, list)):
            updates[key] = json.dumps(updates[key])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [campaign_id]
    conn.execute(f"UPDATE campaigns SET {set_clause} WHERE id=?", values)
    conn.commit()
    campaign = dict(conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone())
    conn.close()
    return campaign


def delete_campaign(campaign_id: int) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()
    return True


def campaign_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM campaigns GROUP BY status"):
        by_status[row["status"]] = row["cnt"]
    budget_total = conn.execute("SELECT COALESCE(SUM(budget), 0) FROM campaigns").fetchone()[0]
    spent_total = conn.execute("SELECT COALESCE(SUM(spent), 0) FROM campaigns").fetchone()[0]
    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "total_budget": budget_total,
        "total_spent": spent_total,
    }


# ============================================================
# Content Management (for campaigns)
# ============================================================

def create_content(title: str, body: str = "", content_type: str = "post",
                   platform: str = "instagram", campaign_id: int = None,
                   hashtags: list[str] = None, scheduled_at: str = "") -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO content (campaign_id, title, body, content_type, platform,
           hashtags, scheduled_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (campaign_id, title, body, content_type, platform,
         json.dumps(hashtags or []), scheduled_at)
    )
    content_id = cur.lastrowid
    conn.commit()
    content = dict(conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone())
    conn.close()
    return content


def get_content(status: str = None, platform: str = None,
                campaign_id: int = None, limit: int = 50) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM content WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if platform:
        query += " AND platform=?"
        params.append(platform)
    if campaign_id:
        query += " AND campaign_id=?"
        params.append(campaign_id)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    content = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return content


def update_content(content_id: int, **kwargs) -> Optional[dict]:
    conn = _get_db()
    allowed = {"title", "body", "content_type", "platform", "status",
               "scheduled_at", "published_at", "media_urls", "hashtags", "engagement"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return None
    updates["updated_at"] = datetime.now().isoformat()
    for key in ("media_urls", "hashtags", "engagement"):
        if key in updates and isinstance(updates[key], (dict, list)):
            updates[key] = json.dumps(updates[key])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [content_id]
    conn.execute(f"UPDATE content SET {set_clause} WHERE id=?", values)
    conn.commit()
    content = dict(conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone())
    conn.close()
    return content


def publish_content(content_id: int) -> Optional[dict]:
    return update_content(content_id, status="published",
                          published_at=datetime.now().isoformat())
