"""
SEO Tracking — monitor keyword positions, page scores, and history.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional

from core.marketing.leads import _get_db


def add_seo_tracking(url: str, keyword: str = "", position: int = 0,
                     search_volume: int = 0, competition: str = "",
                     page_score: int = 0) -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO seo_tracking (url, keyword, position, search_volume,
           competition, page_score)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (url, keyword, position, search_volume, competition, page_score)
    )
    tracking_id = cur.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM seo_tracking WHERE id=?", (tracking_id,)).fetchone())
    conn.close()
    return row


def get_seo_tracking(url: str = None, keyword: str = None) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM seo_tracking WHERE 1=1"
    params = []
    if url:
        query += " AND url=?"
        params.append(url)
    if keyword:
        query += " AND keyword LIKE ?"
        params.append(f"%{keyword}%")
    query += " ORDER BY last_checked DESC"
    results = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return results


def update_seo_position(tracking_id: int, position: int,
                        page_score: int = None) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM seo_tracking WHERE id=?", (tracking_id,)).fetchone()
    if not row:
        conn.close()
        return None

    history = json.loads(row["history"]) if row["history"] else []
    history.append({
        "date": datetime.now().isoformat(),
        "position": row["position"],
        "score": row["page_score"],
    })
    if len(history) > 30:
        history = history[-30:]

    updates = {
        "previous_position": row["position"],
        "position": position,
        "last_checked": datetime.now().isoformat(),
        "history": json.dumps(history),
    }
    if page_score is not None:
        updates["page_score"] = page_score

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [tracking_id]
    conn.execute(f"UPDATE seo_tracking SET {set_clause} WHERE id=?", values)
    conn.commit()
    result = dict(conn.execute("SELECT * FROM seo_tracking WHERE id=?", (tracking_id,)).fetchone())
    conn.close()
    return result


def delete_seo_tracking(tracking_id: int) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM seo_tracking WHERE id=?", (tracking_id,))
    conn.commit()
    conn.close()
    return True


def seo_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM seo_tracking").fetchone()[0]
    avg_score = conn.execute(
        "SELECT COALESCE(AVG(page_score), 0) FROM seo_tracking"
    ).fetchone()[0]
    top_10 = conn.execute(
        "SELECT COUNT(*) FROM seo_tracking WHERE position > 0 AND position <= 10"
    ).fetchone()[0]
    tracked_keywords = conn.execute(
        "SELECT COUNT(DISTINCT keyword) FROM seo_tracking WHERE keyword != ''"
    ).fetchone()[0]
    conn.close()
    return {
        "total_tracked": total,
        "avg_page_score": round(avg_score, 1),
        "top_10_count": top_10,
        "tracked_keywords": tracked_keywords,
    }
