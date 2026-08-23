"""
Invoice & Payment Tracking — generate invoices, track payments.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional

from core.marketing.leads import _get_db


def _generate_invoice_number() -> str:
    conn = _get_db()
    count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    conn.close()
    return f"INV-{datetime.now().strftime('%Y%m')}-{count + 1:04d}"


def create_invoice(client_id: int, amount: float, description: str = "",
                   items: list[dict] = None, tax_rate: float = 0,
                   currency: str = "MYR", due_days: int = 30) -> dict:
    tax_amount = round(amount * tax_rate / 100, 2) if tax_rate else 0
    total = round(amount + tax_amount, 2)
    due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")
    invoice_number = _generate_invoice_number()

    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO invoices (invoice_number, client_id, amount, currency,
           description, items, tax_rate, tax_amount, total, due_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (invoice_number, client_id, amount, currency, description,
         json.dumps(items or []), tax_rate, tax_amount, total, due_date)
    )
    invoice_id = cur.lastrowid
    conn.commit()

    # Update client invoiced total
    conn.execute(
        "UPDATE clients SET total_invoiced = total_invoiced + ? WHERE id=?",
        (total, client_id)
    )
    conn.commit()

    invoice = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())
    conn.close()
    return invoice


def get_invoices(client_id: int = None, status: str = None,
                 limit: int = 50) -> list[dict]:
    conn = _get_db()
    query = "SELECT * FROM invoices WHERE 1=1"
    params = []
    if client_id:
        query += " AND client_id=?"
        params.append(client_id)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    invoices = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return invoices


def get_invoice(invoice_id: int) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_invoice(invoice_id: int, **kwargs) -> Optional[dict]:
    conn = _get_db()
    allowed = {"amount", "currency", "status", "description", "items",
               "tax_rate", "tax_amount", "total", "due_date", "paid_at",
               "payment_method", "payment_ref", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        conn.close()
        return None
    updates["updated_at"] = datetime.now().isoformat()
    if "items" in updates and isinstance(updates["items"], list):
        updates["items"] = json.dumps(updates["items"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [invoice_id]
    conn.execute(f"UPDATE invoices SET {set_clause} WHERE id=?", values)
    conn.commit()
    invoice = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())
    conn.close()
    return invoice


def mark_invoice_paid(invoice_id: int, payment_method: str = "",
                      payment_ref: str = "") -> Optional[dict]:
    invoice = update_invoice(
        invoice_id,
        status="paid",
        paid_at=datetime.now().isoformat(),
        payment_method=payment_method,
        payment_ref=payment_ref,
    )
    if invoice and invoice.get("client_id"):
        conn = _get_db()
        conn.execute(
            "UPDATE clients SET total_paid = total_paid + ? WHERE id=?",
            (invoice["total"], invoice["client_id"])
        )
        conn.commit()
        conn.close()
    return invoice


def delete_invoice(invoice_id: int) -> bool:
    conn = _get_db()
    conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
    conn.commit()
    conn.close()
    return True


def invoice_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM invoices GROUP BY status"):
        by_status[row["status"]] = row["cnt"]
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status='paid'"
    ).fetchone()[0]
    total_outstanding = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status IN ('sent', 'overdue')"
    ).fetchone()[0]
    overdue = conn.execute(
        "SELECT COUNT(*) FROM invoices WHERE status='overdue'"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "total_revenue": total_revenue,
        "total_outstanding": total_outstanding,
        "overdue_count": overdue,
    }
