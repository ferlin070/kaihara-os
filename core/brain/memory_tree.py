"""
Memory Tree — 3-tier memory + layered recall (TencentDB #5 pattern)

Architecture:
  RAW → SUMMARY → CANVAS (3 layers, never flat store)
  Hybrid recall: BM25 + Vector + RRF fusion
  Full traceability: symbol → index → raw text

Tiers:
  1. Context (short-term, per conversation, in-memory)
  2. Daily (mid-term, compressed nightly, SQLite)
  3. Core (long-term, MEMORY.md + Obsidian vault)
"""

import sqlite3
import json
import hashlib
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

try:
    import chromadb
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False


class MemoryTree:
    """3-tier memory with layered storage and hybrid recall."""

    def __init__(self, db_path: str, vault_path: str, config: dict | None = None):
        self.db_path = db_path
        self.vault_path = Path(vault_path)
        self.config = config or {}
        self._init_db()
        self._init_vector()
        self._init_vault_dirs()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS raw (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                agent TEXT,
                content TEXT NOT NULL,
                metadata TEXT,
                hash TEXT
            );
            CREATE TABLE IF NOT EXISTS summary (
                id TEXT PRIMARY KEY,
                raw_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                topic TEXT,
                importance INTEGER DEFAULT 5,
                FOREIGN KEY (raw_id) REFERENCES raw(id)
            );
            CREATE TABLE IF NOT EXISTS canvas (
                id TEXT PRIMARY KEY,
                summary_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                mermaid TEXT,
                symbols TEXT,
                topic TEXT,
                FOREIGN KEY (summary_id) REFERENCES summary(id)
            );
            CREATE TABLE IF NOT EXISTS daily_memory (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                compressed BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_raw_ts ON raw(timestamp);
            CREATE INDEX IF NOT EXISTS idx_summary_topic ON summary(topic);
            CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_memory(date);
        """)
        self.conn.commit()

    def _init_vector(self):
        self.collection = None
        if not CHROMA_AVAILABLE:
            return
        chroma_path = os.path.join(os.path.dirname(self.db_path), "chroma")
        try:
            self.chroma = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.chroma.get_or_create_collection("kaihara_memory")
        except Exception:
            try:
                self.chroma = chromadb.EphemeralClient()
                self.collection = self.chroma.get_or_create_collection("kaihara_memory")
            except Exception:
                self.collection = None

    def _init_vault_dirs(self):
        for d in ["memory/context", "memory/daily", "memory/core",
                  "knowledge", "goals", "briefings", "prd"]:
            (self.vault_path / d).mkdir(parents=True, exist_ok=True)

    # ============================================================
    # WRITE: store memory (raw → summary → canvas)
    # ============================================================

    def store(self, content: str, source: str = "user",
              agent: str | None = None, metadata: dict | None = None) -> dict:
        """Store memory through 3-layer pipeline."""
        timestamp = datetime.now().isoformat()
        mem_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        raw_id = f"raw_{mem_hash}"

        # Layer 1: RAW — full original text
        self.conn.execute(
            "INSERT OR REPLACE INTO raw VALUES (?,?,?,?,?,?,?)",
            (raw_id, timestamp, source, agent, content,
             json.dumps(metadata or {}), mem_hash)
        )

        # Layer 2: SUMMARY — compressed version + tags + topic
        summary_text = self._summarize(content)
        tags = self._extract_tags(content)
        topic = self._classify_topic(content)
        summary_id = f"sum_{mem_hash}"
        self.conn.execute(
            "INSERT OR REPLACE INTO summary VALUES (?,?,?,?,?,?,?)",
            (summary_id, raw_id, timestamp, summary_text,
             json.dumps(tags), topic, 5)
        )

        # Layer 3: CANVAS — symbolic representation (Mermaid diagram)
        canvas_id = f"cnv_{mem_hash}"
        mermaid = self._to_mermaid(content, topic)
        symbols = self._extract_symbols(content)
        self.conn.execute(
            "INSERT OR REPLACE INTO canvas VALUES (?,?,?,?,?,?)",
            (canvas_id, summary_id, timestamp, mermaid,
             json.dumps(symbols), topic)
        )

        # Vector store for semantic search
        if self.collection:
            try:
                self.collection.upsert(
                    ids=[summary_id],
                    documents=[summary_text],
                    metadatas=[{
                        "raw_id": raw_id, "topic": topic,
                        "tags": ",".join(tags), "source": source
                    }]
                )
            except Exception:
                pass

        # Mirror to Obsidian vault
        self._sync_to_vault(summary_text, topic, tags, timestamp)

        self.conn.commit()
        return {
            "raw_id": raw_id, "summary_id": summary_id,
            "canvas_id": canvas_id, "topic": topic, "tags": tags
        }

    # ============================================================
    # READ: hybrid recall (BM25 + Vector + RRF)
    # ============================================================

    def recall(self, query: str, limit: int = 10) -> list[dict]:
        """Hybrid recall: BM25 (keyword) + Vector (semantic) + RRF fusion."""
        w_bm25 = self.config.get("recall", {}).get("bm25_weight", 0.4)
        w_vec = self.config.get("recall", {}).get("vector_weight", 0.4)
        w_graph = self.config.get("recall", {}).get("graph_weight", 0.2)

        # BM25 search
        bm25_results = self._bm25_search(query, limit * 2)
        # Vector search
        vec_results = self._vector_search(query, limit * 2)
        # Graph search (topic-based connections)
        graph_results = self._graph_search(query, limit)

        # RRF (Reciprocal Rank Fusion)
        rrf_k = self.config.get("recall", {}).get("rrf_k", 60)
        scores: dict[str, float] = {}
        all_items: dict[str, dict] = {}

        for rank, item in enumerate(bm25_results):
            sid = item["summary_id"]
            scores[sid] = scores.get(sid, 0) + w_bm25 / (rrf_k + rank + 1)
            all_items[sid] = item

        for rank, item in enumerate(vec_results):
            sid = item["summary_id"]
            scores[sid] = scores.get(sid, 0) + w_vec / (rrf_k + rank + 1)
            if sid not in all_items:
                all_items[sid] = item

        for rank, item in enumerate(graph_results):
            sid = item["summary_id"]
            scores[sid] = scores.get(sid, 0) + w_graph / (rrf_k + rank + 1)
            if sid not in all_items:
                all_items[sid] = item

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for sid, score in ranked[:limit]:
            item = all_items[sid]
            item["score"] = round(score, 4)
            # Full traceability: summary → raw
            raw = self.conn.execute(
                "SELECT * FROM raw WHERE id=?",
                (item.get("raw_id"),)
            ).fetchone()
            if raw:
                item["raw_content"] = raw["content"]
                item["raw_timestamp"] = raw["timestamp"]
            results.append(item)
        return results

    def _bm25_search(self, query: str, limit: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT s.id as summary_id, s.raw_id, s.content, s.topic, "
            "s.tags FROM summary s"
        ).fetchall()
        if not rows:
            return []
        docs = [r["content"].split() for r in rows]
        bm25 = BM25Okapi(docs)
        scores = bm25.get_scores(query.split())
        ranked = sorted(zip(rows, scores), key=lambda x: x[1], reverse=True)
        results = []
        for row, score in ranked[:limit]:
            if score <= 0:
                continue
            results.append({
                "summary_id": row["summary_id"],
                "raw_id": row["raw_id"],
                "content": row["content"],
                "topic": row["topic"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "source": "bm25"
            })
        return results

    def _vector_search(self, query: str, limit: int) -> list[dict]:
        if not self.collection:
            return []
        try:
            results = self.collection.query(
                query_texts=[query], n_results=limit
            )
        except Exception:
            return []
        items = []
        if not results["ids"] or not results["ids"][0]:
            return items
        for i, sid in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            doc = results["documents"][0][i]
            items.append({
                "summary_id": sid,
                "raw_id": meta.get("raw_id"),
                "content": doc,
                "topic": meta.get("topic"),
                "tags": meta.get("tags", "").split(",") if meta.get("tags") else [],
                "source": "vector"
            })
        return items

    def _graph_search(self, query: str, limit: int) -> list[dict]:
        topic = self._classify_topic(query)
        rows = self.conn.execute(
            "SELECT s.id as summary_id, s.raw_id, s.content, s.topic, s.tags "
            "FROM summary s WHERE s.topic = ? LIMIT ?",
            (topic, limit)
        ).fetchall()
        return [{
            "summary_id": r["summary_id"],
            "raw_id": r["raw_id"],
            "content": r["content"],
            "topic": r["topic"],
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "source": "graph"
        } for r in rows]

    # ============================================================
    # SuperContext: pre-sweep memory before LLM reads
    # ============================================================

    def super_context(self, query: str) -> str:
        """Pre-sweep memory before model reads message. No cold starts."""
        results = self.recall(query, limit=5)
        if not results:
            # Fallback: graph search by topic
            results = self._graph_search(query, limit=5)
        if not results:
            # Fallback: latest memories
            rows = self.conn.execute(
                "SELECT s.id as summary_id, s.raw_id, s.content, s.topic, "
                "s.tags FROM summary s ORDER BY s.timestamp DESC LIMIT 3"
            ).fetchall()
            results = [{
                "summary_id": r["summary_id"],
                "raw_id": r["raw_id"],
                "content": r["content"],
                "topic": r["topic"],
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "score": 0.0,
            } for r in rows]
        if not results:
            return ""
        lines = ["## Context from Memory:"]
        for r in results:
            lines.append(
                f"- [{r.get('topic', 'general')}] "
                f"{r.get('content', '')[:200]}... "
                f"(score: {r.get('score', 0)})"
            )
        return "\n".join(lines)

    # ============================================================
    # Context tier (in-memory, per conversation)
    # ============================================================

    _context_cache: dict[str, list[dict]] = {}

    def add_context(self, conv_id: str, role: str, content: str):
        """Add to short-term context (in-memory, per conversation)."""
        if conv_id not in self._context_cache:
            self._context_cache[conv_id] = []
        self._context_cache[conv_id].append({
            "role": role, "content": content,
            "timestamp": datetime.now().isoformat()
        })
        max_msgs = self.config.get("context_window", 20)
        if len(self._context_cache[conv_id]) > max_msgs:
            self._context_cache[conv_id] = self._context_cache[conv_id][-max_msgs:]

    def get_context(self, conv_id: str) -> list[dict]:
        return self._context_cache.get(conv_id, [])

    def clear_context(self, conv_id: str):
        self._context_cache.pop(conv_id, None)

    # ============================================================
    # Deep Dream: nightly distillation (CowAgent pattern)
    # ============================================================

    def deep_dream(self):
        """Nightly distillation: compress daily memories, update knowledge graph."""
        today = date.today().isoformat()
        rows = self.conn.execute(
            "SELECT * FROM raw WHERE date(timestamp) = ? AND "
            "id NOT IN (SELECT raw_id FROM daily_memory)",
            (today,)
        ).fetchall()
        if not rows:
            return {"distilled": 0, "date": today}
        summary_parts = []
        for r in rows:
            summary_parts.append(f"- [{r['source']}] {r['content'][:100]}")
        distilled = f"# Daily Memory — {today}\n\n" + "\n".join(summary_parts)
        mem_id = f"daily_{today}_{hashlib.sha256(distilled.encode()).hexdigest()[:8]}"
        self.conn.execute(
            "INSERT OR REPLACE INTO daily_memory VALUES (?,?,?,?,?)",
            (mem_id, today, distilled, True, datetime.now().isoformat())
        )
        self._sync_to_vault(distilled, "daily", ["distilled"], datetime.now().isoformat())
        self.conn.commit()
        return {"distilled": len(rows), "date": today, "id": mem_id}

    # ============================================================
    # Goals tracking
    # ============================================================

    def add_goal(self, title: str, description: str = "",
                 priority: str = "medium") -> str:
        goal_id = f"goal_{hashlib.sha256(title.encode()).hexdigest()[:8]}"
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO goals VALUES (?,?,?,?,?,?,?)",
            (goal_id, title, description, "active", priority, now, now)
        )
        self.conn.commit()
        return goal_id

    def get_goals(self, status: str = "active") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM goals WHERE status = ?", (status,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_goal(self, goal_id: str, **kwargs):
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [datetime.now().isoformat(), goal_id]
        self.conn.execute(
            f"UPDATE goals SET {sets}, updated_at = ? WHERE id = ?", vals
        )
        self.conn.commit()

    # ============================================================
    # Obsidian vault sync
    # ============================================================

    def _sync_to_vault(self, content: str, topic: str,
                       tags: list[str], timestamp: str):
        safe_topic = topic.replace(" ", "_").lower()
        vault_dir = self.vault_path / "memory" / "core" / safe_topic
        vault_dir.mkdir(parents=True, exist_ok=True)
        filename = f"mem_{hashlib.sha256(content.encode()).hexdigest()[:8]}.md"
        filepath = vault_dir / filename
        frontmatter = "---\n"
        frontmatter += f"timestamp: {timestamp}\n"
        frontmatter += f"topic: {topic}\n"
        frontmatter += f"tags: [{', '.join(tags)}]\n"
        frontmatter += "---\n\n"
        filepath.write_text(frontmatter + content, encoding="utf-8")

    # ============================================================
    # Helpers (stub — replace with LLM calls in production)
    # ============================================================

    def _summarize(self, content: str) -> str:
        if len(content) <= 200:
            return content
        return content[:197] + "..."

    def _extract_tags(self, content: str) -> list[str]:
        words = [w.lower().strip(".,!?") for w in content.split()]
        keywords = [w for w in words if len(w) > 4]
        seen = set()
        tags = []
        for w in keywords:
            if w not in seen and len(tags) < 5:
                seen.add(w)
                tags.append(w)
        return tags

    def _classify_topic(self, content: str) -> str:
        content_lower = content.lower()
        topics_map = {
            "coding": ["code", "python", "api", "function", "bug", "deploy",
                        "git", "build", "test", "refactor"],
            "security": ["security", "pentest", "vuln", "exploit", "scan",
                          "hack", "firewall", "encrypt"],
            "marketing": ["market", "product", "trending", "scrape",
                           "sales", "revenue", "content", "ad"],
            "research": ["research", "search", "find", "analyze",
                          "report", "data", "study"],
            "personal": ["saya", "suk", "nak", "buat", "bina", "tolong"],
        }
        for topic, kws in topics_map.items():
            if any(k in content_lower for k in kws):
                return topic
        return "general"

    def _to_mermaid(self, content: str, topic: str) -> str:
        return f"graph LR\n  A[{topic}] --> B[Memory]"

    def _extract_symbols(self, content: str) -> list[str]:
        return [w for w in content.split() if len(w) > 6][:5]

    def close(self):
        self.conn.close()
