"""
Task Tracker - track task status across phases (kanban style).
Inspired by Vibe Kanban #18: Plan to Build to Ship.
"""

import sqlite3
import json
import os
from datetime import datetime


class TaskTracker:
    STATUSES = ["todo", "doing", "review", "done", "blocked"]

    def __init__(self, db_path: str = "./data/kaihara.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                phase TEXT DEFAULT 'Foundation',
                status TEXT DEFAULT 'todo',
                dependencies TEXT,
                complexity TEXT DEFAULT 'medium',
                criteria TEXT,
                assigned_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                prd_id TEXT
            );
            CREATE TABLE IF NOT EXISTS prds (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                parsed TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_phase ON tasks(phase);
        """)
        self.conn.commit()

    def save_prd(self, title: str, content: str,
                 parsed: dict | None = None) -> str:
        import hashlib
        prd_id = f"prd_{hashlib.sha256(title.encode()).hexdigest()[:8]}"
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO prds VALUES (?,?,?,?,?,?)",
            (prd_id, title, content,
             json.dumps(parsed or {}), "approved", now)
        )
        self.conn.commit()
        return prd_id

    def get_prd(self, prd_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM prds WHERE id = ?", (prd_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_prds(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM prds ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def save_tasks(self, tasks: list[dict], prd_id: str = None):
        now = datetime.now().isoformat()
        for task in tasks:
            tid = task.get("id", f"T{now}")
            self.conn.execute(
                "INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, task["title"], task.get("description", ""),
                 task.get("phase", "Foundation"), task.get("status", "todo"),
                 json.dumps(task.get("dependencies", [])),
                 task.get("complexity", "medium"),
                 json.dumps(task.get("criteria", [])),
                 task.get("assigned_agent"), now, now, prd_id)
            )
        self.conn.commit()

    def update_status(self, task_id: str, status: str):
        if status not in self.STATUSES:
            return False
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, task_id)
        )
        self.conn.commit()
        return True

    def get_tasks(self, prd_id: str = None,
                 status: str = None) -> list[dict]:
        query = "SELECT * FROM tasks"
        params = []
        conditions = []
        if prd_id:
            conditions.append("prd_id = ?")
            params.append(prd_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY phase, id"
        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            task = dict(r)
            task["dependencies"] = json.loads(
                task.get("dependencies") or "[]")
            task["criteria"] = json.loads(
                task.get("criteria") or "[]")
            result.append(task)
        return result

    def get_next_task(self, agent_type: str = None) -> dict | None:
        tasks = self.get_tasks(status="todo")
        for task in tasks:
            deps = task.get("dependencies", [])
            if not deps:
                return task
            all_done = True
            for dep_id in deps:
                dep = self.conn.execute(
                    "SELECT status FROM tasks WHERE id = ?",
                    (dep_id,)
                ).fetchone()
                if not dep or dep["status"] != "done":
                    all_done = False
                    break
            if all_done:
                return task
        return None

    def get_progress(self, prd_id: str = None) -> dict:
        tasks = self.get_tasks(prd_id=prd_id)
        total = len(tasks)
        if total == 0:
            return {"total": 0, "done": 0, "doing": 0, "todo": 0,
                    "blocked": 0, "phases": {}, "percent": 0}
        counts = {"todo": 0, "doing": 0, "review": 0,
                  "done": 0, "blocked": 0}
        phases: dict[str, dict] = {}
        for t in tasks:
            s = t["status"]
            counts[s] = counts.get(s, 0) + 1
            p = t["phase"]
            if p not in phases:
                phases[p] = {"total": 0, "done": 0, "doing": 0}
            phases[p]["total"] += 1
            if s == "done":
                phases[p]["done"] += 1
            elif s == "doing":
                phases[p]["doing"] += 1
        return {
            "total": total,
            "done": counts["done"],
            "doing": counts["doing"],
            "todo": counts["todo"],
            "blocked": counts["blocked"],
            "phases": phases,
            "percent": round(counts["done"] / total * 100),
        }

    def close(self):
        self.conn.close()
