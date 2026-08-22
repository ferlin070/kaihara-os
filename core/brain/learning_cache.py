"""
Learning Cache - cache agent results to prevent repetition.
Hash-based: similar tasks return cached results instead of re-running.
"""

import sqlite3
import json
import hashlib
import os
from datetime import datetime, date
from typing import Any


class LearningCache:
    """Cache agent results. Prevent doing the same thing twice."""

    def __init__(self, db_path: str = "./data/kaihara.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_cache (
                id TEXT PRIMARY KEY,
                task_hash TEXT NOT NULL,
                agent TEXT NOT NULL,
                task_text TEXT NOT NULL,
                result TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                time_taken REAL DEFAULT 0,
                model_used TEXT,
                success BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS agent_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                task_type TEXT,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                time_taken REAL DEFAULT 0,
                success BOOLEAN DEFAULT 1,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                agent TEXT,
                description TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                severity TEXT DEFAULT 'info',
                suggestion TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cache_hash ON task_cache(task_hash);
            CREATE INDEX IF NOT EXISTS idx_stats_agent ON agent_stats(agent);
            CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
        """)
        self.conn.commit()

    def _hash_task(self, task: str, agent: str = "") -> str:
        """Hash a task string for cache lookup."""
        normalized = task.strip().lower()
        return hashlib.sha256(
            f"{agent}:{normalized}".encode()
        ).hexdigest()[:16]

    def check_cache(self, task: str, agent: str = "",
                     similarity_threshold: float = 0.9) -> dict | None:
        """Check if task was done before. Return cached result if found."""
        task_hash = self._hash_task(task, agent)
        row = self.conn.execute(
            "SELECT * FROM task_cache WHERE task_hash = ? AND success = 1 "
            "ORDER BY created_at DESC LIMIT 1",
            (task_hash,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE task_cache SET last_accessed = ?, "
                "access_count = access_count + 1 WHERE id = ?",
                (datetime.now().isoformat(), row["id"])
            )
            self.conn.commit()
            return {
                "cached": True,
                "result": json.loads(row["result"]),
                "original_task": row["task_text"],
                "cached_at": row["created_at"],
                "access_count": row["access_count"] + 1,
                "tokens_saved": row["tokens_used"],
            }
        # Try fuzzy match by keywords
        fuzzy = self._fuzzy_match(task, agent)
        if fuzzy:
            return fuzzy
        return None

    def _fuzzy_match(self, task: str, agent: str) -> dict | None:
        """Fuzzy match task by keywords."""
        task_lower = task.lower().strip()
        task_words = set(task_lower.split())
        if len(task_words) < 3:
            return None
        rows = self.conn.execute(
            "SELECT * FROM task_cache WHERE agent = ? AND success = 1 "
            "ORDER BY created_at DESC LIMIT 20",
            (agent,)
        ).fetchall()
        for row in rows:
            cached_words = set(row["task_text"].lower().split())
            if not cached_words:
                continue
            overlap = len(task_words & cached_words)
            similarity = overlap / max(len(task_words), len(cached_words))
            if similarity >= 0.7:
                self.conn.execute(
                    "UPDATE task_cache SET last_accessed = ?, "
                    "access_count = access_count + 1 WHERE id = ?",
                    (datetime.now().isoformat(), row["id"])
                )
                self.conn.commit()
                return {
                    "cached": True,
                    "fuzzy": True,
                    "similarity": round(similarity, 2),
                    "result": json.loads(row["result"]),
                    "original_task": row["task_text"],
                    "cached_at": row["created_at"],
                    "tokens_saved": row["tokens_used"],
                    "note": "Similar task found in cache. Review before use.",
                }
        return None

    def store_result(self, task: str, agent: str, result: dict,
                      tokens_used: int = 0, time_taken: float = 0,
                      model_used: str = "", success: bool = True) -> str:
        """Store an agent result in cache."""
        task_hash = self._hash_task(task, agent)
        cache_id = f"cache_{task_hash}"
        self.conn.execute(
            "INSERT OR REPLACE INTO task_cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (cache_id, task_hash, agent, task,
             json.dumps(result, ensure_ascii=False),
             tokens_used, time_taken, model_used, success,
             datetime.now().isoformat(), datetime.now().isoformat(), 0)
        )
        self.conn.commit()
        return cache_id

    def record_stats(self, agent: str, task_type: str,
                      model: str, tokens: int,
                      time_taken: float, success: bool):
        """Record agent run statistics."""
        self.conn.execute(
            "INSERT INTO agent_stats (agent, task_type, model, "
            "tokens_used, time_taken, success, timestamp) "
            "VALUES (?,?,?,?,?,?,?)",
            (agent, task_type, model, tokens, time_taken,
             success, datetime.now().isoformat())
        )
        self.conn.commit()

    def detect_pattern(self, pattern_type: str, agent: str,
                        description: str, severity: str = "info",
                        suggestion: str = "") -> dict:
        """Detect and record a pattern."""
        pattern_id = hashlib.sha256(
            f"{pattern_type}:{agent}:{description}".encode()
        ).hexdigest()[:16]
        existing = self.conn.execute(
            "SELECT * FROM patterns WHERE id = ?", (pattern_id,)
        ).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE patterns SET frequency = frequency + 1, "
                "last_seen = ? WHERE id = ?",
                (datetime.now().isoformat(), pattern_id)
            )
        else:
            self.conn.execute(
                "INSERT INTO patterns VALUES (?,?,?,?,?,?,?,?,?)",
                (pattern_id, pattern_type, agent, description,
                 1, severity, suggestion,
                 datetime.now().isoformat(),
                 datetime.now().isoformat())
            )
        self.conn.commit()
        return {
            "pattern_id": pattern_id,
            "type": pattern_type,
            "agent": agent,
            "description": description,
            "severity": severity,
            "suggestion": suggestion,
        }

    def get_patterns(self, pattern_type: str = None,
                      severity: str = None) -> list[dict]:
        """Get detected patterns."""
        query = "SELECT * FROM patterns"
        conditions = []
        params = []
        if pattern_type:
            conditions.append("pattern_type = ?")
            params.append(pattern_type)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY frequency DESC, last_seen DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_agent_stats(self, agent: str = None,
                         days: int = 7) -> list[dict]:
        """Get agent statistics."""
        cutoff = date.today().isoformat()
        query = ("SELECT agent, task_type, model, "
                 "SUM(tokens_used) as total_tokens, "
                 "AVG(time_taken) as avg_time, "
                 "SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count, "
                 "COUNT(*) as total_runs "
                 "FROM agent_stats WHERE timestamp >= ? ")
        params = [cutoff]
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        query += " GROUP BY agent, task_type, model"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        total = self.conn.execute(
            "SELECT COUNT(*) as c FROM task_cache"
        ).fetchone()["c"]
        hits = self.conn.execute(
            "SELECT SUM(access_count) as c FROM task_cache"
        ).fetchone()["c"] or 0
        tokens_saved = self.conn.execute(
            "SELECT SUM(tokens_used * access_count) as c FROM task_cache"
        ).fetchone()["c"] or 0
        return {
            "cached_tasks": total,
            "cache_hits": hits,
            "tokens_saved": tokens_saved,
            "estimated_savings": round(tokens_saved * 0.00001, 4),
        }

    def get_suggestions(self) -> list[dict]:
        """Get optimization suggestions based on patterns."""
        patterns = self.get_patterns()
        suggestions = []
        for p in patterns:
            if p.get("suggestion"):
                suggestions.append({
                    "type": p["pattern_type"],
                    "agent": p["agent"],
                    "issue": p["description"],
                    "suggestion": p["suggestion"],
                    "frequency": p["frequency"],
                    "severity": p["severity"],
                })
        return suggestions

    def close(self):
        self.conn.close()
