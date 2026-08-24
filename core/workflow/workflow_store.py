"""
Workflow Store — SQLite persistence for workflow instances and step results.
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Any


class WorkflowStore:
    """Persist workflow runs and step results to SQLite."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(base, "data", "kaihara.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def close(self):
        """Close any open connections."""
        pass

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    template TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending',
                    input_data TEXT DEFAULT '{}',
                    output_data TEXT DEFAULT '{}',
                    context TEXT DEFAULT '{}',
                    error TEXT,
                    current_step TEXT,
                    total_steps INTEGER DEFAULT 0,
                    completed_steps INTEGER DEFAULT 0,
                    approval_required TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending',
                    input_data TEXT DEFAULT '{}',
                    output_data TEXT DEFAULT '{}',
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    approval_required INTEGER DEFAULT 0,
                    approval_status TEXT DEFAULT 'pending',
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_instances(id)
                )
            """)

    def create_workflow(self, workflow_id: str, name: str, template: str,
                        input_data: dict, total_steps: int,
                        approval_steps: list) -> dict:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO workflow_instances
                (id, name, template, state, input_data, context,
                 total_steps, approval_required, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, '{}', ?, ?, ?, ?)
            """, (workflow_id, name, template, json.dumps(input_data),
                  total_steps, json.dumps(approval_steps), now, now))
        return {"id": workflow_id, "state": "pending"}

    def create_step(self, step_id: str, workflow_id: str, step_index: int,
                    name: str, agent: str, max_retries: int = 3,
                    approval_required: bool = False) -> dict:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO workflow_steps
                (id, workflow_id, step_index, name, agent, state,
                 max_retries, approval_required, started_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """, (step_id, workflow_id, step_index, name, agent,
                  max_retries, 1 if approval_required else 0, now))
        return {"id": step_id, "state": "pending"}

    def update_workflow_state(self, workflow_id: str, state: str,
                              reason: str = ""):
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            if reason:
                conn.execute("""
                    UPDATE workflow_instances
                    SET state = ?, error = ?, updated_at = ?
                    WHERE id = ?
                """, (state, reason, now, workflow_id))
            else:
                conn.execute("""
                    UPDATE workflow_instances
                    SET state = ?, updated_at = ?
                    WHERE id = ?
                """, (state, now, workflow_id))

    def update_workflow_progress(self, workflow_id: str,
                                 completed_steps: int,
                                 current_step: str):
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE workflow_instances
                SET completed_steps = ?, current_step = ?, updated_at = ?
                WHERE id = ?
            """, (completed_steps, current_step, now, workflow_id))

    def update_step_state(self, step_id: str, state: str,
                          output_data: dict = None, error: str = None):
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            if output_data:
                conn.execute("""
                    UPDATE workflow_steps
                    SET state = ?, output_data = ?, completed_at = ?
                    WHERE id = ?
                """, (state, json.dumps(output_data), now, step_id))
            elif error:
                conn.execute("""
                    UPDATE workflow_steps
                    SET state = ?, error = ?, completed_at = ?
                    WHERE id = ?
                """, (state, error, now, step_id))
            else:
                conn.execute("""
                    UPDATE workflow_steps SET state = ? WHERE id = ?
                """, (state, step_id))

    def set_step_waiting_approval(self, step_id: str):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE workflow_steps
                SET state = 'waiting_approval', approval_status = 'pending'
                WHERE id = ?
            """, (step_id,))

    def approve_step(self, step_id: str, approved: bool):
        status = "approved" if approved else "rejected"
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE workflow_steps
                SET approval_status = ?
                WHERE id = ?
            """, (status, step_id))

    def increment_retry(self, step_id: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT retry_count FROM workflow_steps WHERE id = ?",
                (step_id,)
            ).fetchone()
            if not row:
                return 0
            new_count = row["retry_count"] + 1
            conn.execute("""
                UPDATE workflow_steps SET retry_count = ? WHERE id = ?
            """, (new_count, step_id))
            return new_count

    def get_workflow(self, workflow_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_instances WHERE id = ?",
                (workflow_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def get_step(self, step_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_steps WHERE id = ?",
                (step_id,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def get_steps_for_workflow(self, workflow_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_steps WHERE workflow_id = ? "
                "ORDER BY step_index",
                (workflow_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def list_workflows(self, state: str = None, limit: int = 50) -> list[dict]:
        with self._get_conn() as conn:
            if state:
                rows = conn.execute(
                    "SELECT * FROM workflow_instances WHERE state = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (state, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workflow_instances "
                    "ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_workflow(self, workflow_id: str):
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM workflow_steps WHERE workflow_id = ?",
                (workflow_id,)
            )
            conn.execute(
                "DELETE FROM workflow_instances WHERE id = ?",
                (workflow_id,)
            )
