"""
Leads Management — track, score, and convert leads into clients.
SQLite-backed with CRUD operations.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent.parent / "data" / "marketing.db"


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize marketing database tables."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            source TEXT DEFAULT 'manual',
            status TEXT DEFAULT 'new',
            score INTEGER DEFAULT 0,
            notes TEXT,
            tags TEXT DEFAULT '[]',
            assigned_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            address TEXT,
            status TEXT DEFAULT 'active',
            tier TEXT DEFAULT 'basic',
            total_paid REAL DEFAULT 0,
            total_invoiced REAL DEFAULT 0,
            notes TEXT,
            tags TEXT DEFAULT '[]',
            whatsapp_verified INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT DEFAULT 'general',
            status TEXT DEFAULT 'draft',
            budget REAL DEFAULT 0,
            spent REAL DEFAULT 0,
            target_audience TEXT,
            channels TEXT DEFAULT '[]',
            content_ids TEXT DEFAULT '[]',
            start_date TEXT,
            end_date TEXT,
            metrics TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            title TEXT NOT NULL,
            body TEXT,
            content_type TEXT DEFAULT 'post',
            platform TEXT DEFAULT 'instagram',
            status TEXT DEFAULT 'draft',
            scheduled_at TEXT,
            published_at TEXT,
            media_urls TEXT DEFAULT '[]',
            hashtags TEXT DEFAULT '[]',
            engagement TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );

        CREATE TABLE IF NOT EXISTS seo_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            keyword TEXT,
            position INTEGER,
            previous_position INTEGER,
            search_volume INTEGER,
            competition TEXT,
            page_score INTEGER,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            history TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'MYR',
            status TEXT DEFAULT 'draft',
            description TEXT,
            items TEXT DEFAULT '[]',
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            total REAL DEFAULT 0,
            due_date TEXT,
            paid_at TEXT,
            payment_method TEXT,
            payment_ref TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            ref_id INTEGER,
            status TEXT DEFAULT 'pending',
            requested_by TEXT,
            approved_by TEXT,
            channel TEXT,
            message TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            responded_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT,
            entity_id INTEGER,
            action TEXT,
            details TEXT,
            agent TEXT DEFAULT 'marketing',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# Initialize on import
init_db()


# ============================================================
# Leads CRUD
# ============================================================

def create_lead(name: str, email: str = "", phone: str = "",
                company: str = "", source: str = "manual",
                notes: str = "", tags: list[str] = None) -> dict:
    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO leads (name, email, phone, company, source, notes, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, email, phone, company, source, notes, json.dumps(tags or []))
    )
    lead_id = cur.lastrowid
    conn.commit()
    lead = dict(conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone())
    conn.close()
    return lead


def get_leads(status: str = None, search: str = None,
              limit: int = 50, offset: int = 0) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM leads WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR company LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    leads = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return leads


def get_lead(lead_id: int) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_lead(lead_id: int, **kwargs) -> Optional[dict]:
    conn = _get_db()
    allowed = {"name", "email", "phone", "company", "status", "score",
               "notes", "tags", "assigned_to", "source"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return None
    updates["updated_at"] = datetime.now().isoformat()
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [lead_id]
    conn.execute(f"UPDATE leads SET {set_clause} WHERE id=?", values)
    conn.commit()
    lead = dict(conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone())
    conn.close()
    return lead


def delete_lead(lead_id: int) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    conn.commit()
    deleted = conn.total_changes > 0
    conn.close()
    return deleted


def convert_lead_to_client(lead_id: int) -> Optional[dict]:
    """Convert a lead to a client."""
    from core.marketing.clients import create_client
    lead = get_lead(lead_id)
    if not lead:
        return None
    client = create_client(
        name=lead["name"], email=lead["email"], phone=lead["phone"],
        company=lead["company"], lead_id=lead_id, notes=lead["notes"],
        tags=json.loads(lead["tags"]) if lead["tags"] else []
    )
    update_lead(lead_id, status="converted")
    return client


def lead_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status"):
        by_status[row["status"]] = row["cnt"]
    by_source = {}
    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM leads GROUP BY source"):
        by_source[row["source"]] = row["cnt"]
    conn.close()
    return {"total": total, "by_status": by_status, "by_source": by_source}


def score_lead(lead_id: int) -> int:
    """Auto-score lead based on data completeness and engagement."""
    lead = get_lead(lead_id)
    if not lead:
        return 0
    score = 0
    if lead.get("email"):
        score += 20
    if lead.get("phone"):
        score += 15
    if lead.get("company"):
        score += 25
    if lead.get("notes") and len(lead["notes"]) > 10:
        score += 10
    tags = json.loads(lead["tags"]) if lead["tags"] else []
    score += len(tags) * 5
    if lead["status"] == "contacted":
        score += 15
    elif lead["status"] == "qualified":
        score += 25
    elif lead["status"] == "converted":
        score += 40
    score = min(score, 100)
    update_lead(lead_id, score=score)
    return score
