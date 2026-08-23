"""
FastAPI Server — Kaihara OS HTTP API + WebSocket.
Entry point for all channels (dashboard, telegram, whatsapp, etc).
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import asyncio
import json


class ChatRequest(BaseModel):
    message: str
    source: str = "dashboard"
    conv_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    route: str
    intent: dict
    source: str
    provider: str = ""


def create_app(command_center) -> FastAPI:
    """Create FastAPI app with all routes."""
    app = FastAPI(title="Kaihara OS", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_tasks():
        """Start kernel + channels inside the running event loop."""
        import asyncio
        import logging
        log = logging.getLogger("kaihara.startup")
        kernel = getattr(command_center, "_kernel", None)
        if kernel:
            asyncio.create_task(kernel.start_all())
            log.info("OS Kernel: 7 agents starting")

        # Start daemon watchdog
        daemon = getattr(command_center, "_daemon_manager", None)
        if daemon:
            asyncio.create_task(daemon.start_watchdog())
            log.info("Daemon Manager: watchdog started")

        channels = getattr(command_center, "_channel_manager", None)
        if channels:
            results = await channels.start_all()
            for name, res in results.items():
                if "error" in res:
                    log.warning(f"Channel {name}: {res['error']}")
                else:
                    log.info(f"Channel {name}: started")

    @app.get("/")
    async def root():
        return {
            "name": "Kaihara OS",
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
        }

    @app.get("/api/status")
    async def status():
        return command_center.status()

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        result = await command_center.handle_input(
            source=req.source,
            message=req.message,
            conv_id=req.conv_id,
        )
        return ChatResponse(
            response=result["response"],
            route=result["route"],
            intent=result["intent"],
            source=result["source"],
            provider=getattr(command_center.model, "last_provider", "")
            if command_center.model else "",
        )

    @app.post("/api/webhook")
    async def webhook(payload: dict):
        event = payload.get("event", "unknown")
        data = payload.get("data", {})
        message = f"Webhook event: {event}. Data: {json.dumps(data)}"
        result = await command_center.handle_input(
            source="webhook", message=message
        )
        return {"status": "processed", "result": result["response"]}

    @app.get("/api/memory/recall")
    async def memory_recall(q: str, limit: int = 5):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        results = command_center.memory.recall(q, limit)
        return {"query": q, "results": results}

    @app.get("/api/memory/context/{conv_id}")
    async def memory_context(conv_id: str):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        return {"conv_id": conv_id,
                "context": command_center.memory.get_context(conv_id)}

    @app.get("/api/memory/stats")
    async def memory_stats():
        """Get memory system statistics."""
        if not command_center.memory:
            return {"error": "memory not initialized"}
        mem = command_center.memory
        try:
            raw_count = mem.conn.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
            summary_count = mem.conn.execute("SELECT COUNT(*) FROM summary").fetchone()[0]
            canvas_count = mem.conn.execute("SELECT COUNT(*) FROM canvas").fetchone()[0]
            daily_count = mem.conn.execute("SELECT COUNT(*) FROM daily_memory").fetchone()[0]
            goals_count = mem.conn.execute("SELECT COUNT(*) FROM goals WHERE status='active'").fetchone()[0]
            # Topic distribution
            topic_rows = mem.conn.execute(
                "SELECT topic, COUNT(*) as cnt FROM summary GROUP BY topic ORDER BY cnt DESC"
            ).fetchall()
            topics = {r["topic"]: r["cnt"] for r in topic_rows}
            # Vector DB stats
            vector_available = mem.collection is not None
            vector_count = 0
            if vector_available:
                try:
                    vector_count = mem.collection.count()
                except Exception:
                    vector_count = 0
            return {
                "total_memories": summary_count,
                "raw_count": raw_count,
                "summary_count": summary_count,
                "canvas_count": canvas_count,
                "topics": topics,
                "daily_count": daily_count,
                "goals_count": goals_count,
                "vector_available": vector_available,
                "vector_count": vector_count,
            }
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/memory/browse")
    async def memory_browse(topic: str = "", limit: int = 50):
        """Browse memories by topic."""
        if not command_center.memory:
            return {"error": "memory not initialized"}
        mem = command_center.memory
        try:
            if topic:
                rows = mem.conn.execute(
                    "SELECT s.id, s.content, s.topic, s.tags, s.importance, "
                    "c.mermaid, c.symbols "
                    "FROM summary s LEFT JOIN canvas c ON s.id = c.summary_id "
                    "WHERE s.topic = ? ORDER BY s.timestamp DESC LIMIT ?",
                    (topic, limit)
                ).fetchall()
            else:
                rows = mem.conn.execute(
                    "SELECT s.id, s.content, s.topic, s.tags, s.importance, "
                    "c.mermaid, c.symbols "
                    "FROM summary s LEFT JOIN canvas c ON s.id = c.summary_id "
                    "ORDER BY s.timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            results = []
            for r in rows:
                results.append({
                    "summary_id": r["id"],
                    "content": r["content"],
                    "topic": r["topic"],
                    "tags": json.loads(r["tags"]) if r["tags"] else [],
                    "score": 1.0,
                    "tier": "summary",
                    "mermaid": r["mermaid"] or "",
                })
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    @app.delete("/api/memory/{summary_id}")
    async def delete_memory(summary_id: str):
        """Delete a memory by summary_id."""
        if not command_center.memory:
            return {"error": "memory not initialized"}
        mem = command_center.memory
        try:
            # Get raw_id before deleting
            row = mem.conn.execute(
                "SELECT raw_id FROM summary WHERE id = ?", (summary_id,)
            ).fetchone()
            if not row:
                return {"error": "not_found"}
            raw_id = row["raw_id"]
            # Delete from all tiers
            mem.conn.execute("DELETE FROM canvas WHERE summary_id = ?", (summary_id,))
            mem.conn.execute("DELETE FROM summary WHERE id = ?", (summary_id,))
            mem.conn.execute("DELETE FROM raw WHERE id = ?", (raw_id,))
            # Delete from vector DB
            if mem.collection:
                try:
                    mem.collection.delete(ids=[summary_id])
                except Exception:
                    pass
            mem.conn.commit()
            return {"status": "deleted", "summary_id": summary_id}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/chat/history")
    async def chat_history(conv_id: str = "dashboard", limit: int = 100):
        """Persistent chat history (survives refresh & restart)."""
        if not command_center.memory:
            return {"error": "memory not initialized"}
        msgs = command_center.memory.get_chat_history(conv_id, limit)
        return {"conv_id": conv_id, "messages": [
            {"role": m["role"], "text": m["content"],
             "timestamp": m["timestamp"]} for m in msgs
        ]}

    @app.delete("/api/chat/history")
    async def clear_chat(conv_id: str = "dashboard"):
        """Clear persistent history for a conversation."""
        if not command_center.memory:
            return {"error": "memory not initialized"}
        command_center.memory.clear_chat_history(conv_id)
        return {"status": "cleared", "conv_id": conv_id}

    # ============================================================
    # Conversation Management
    # ============================================================

    @app.get("/api/chat/conversations")
    async def list_conversations(limit: int = 50):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        return {"conversations":
                command_center.memory.list_conversations(limit)}

    @app.post("/api/chat/new")
    async def new_conversation(payload: dict = None):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        payload = payload or {}
        title = payload.get("title", "New Chat")
        source = payload.get("source", "dashboard")
        conv_id = command_center.memory.create_conversation(title, source)
        return {"conv_id": conv_id, "title": title}

    @app.patch("/api/chat/conversations/{conv_id}")
    async def rename_conversation(conv_id: str, payload: dict):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        ok = command_center.memory.rename_conversation(
            conv_id, payload.get("title", "").strip() or "Untitled")
        return {"status": "renamed" if ok else "not_found", "conv_id": conv_id}

    @app.delete("/api/chat/conversations/{conv_id}")
    async def delete_conversation(conv_id: str):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        ok = command_center.memory.delete_conversation(conv_id)
        return {"status": "deleted" if ok else "not_found",
                "conv_id": conv_id}

    @app.get("/api/goals")
    async def get_goals():
        if not command_center.memory:
            return {"error": "memory not initialized"}
        goals = command_center.memory.get_goals()
        return {"goals": goals}

    @app.post("/api/goals")
    async def add_goal(payload: dict):
        if not command_center.memory:
            return {"error": "memory not initialized"}
        goal_id = command_center.memory.add_goal(
            title=payload.get("title", ""),
            description=payload.get("description", ""),
            priority=payload.get("priority", "medium"),
        )
        return {"goal_id": goal_id, "status": "created"}

    # ============================================================
    # WebSocket — real-time bidirectional communication
    # ============================================================

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({
            "type": "status",
            "data": {"kaihara": "online", "message": "Kaihara online."}
        })
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    message = msg.get("message", data)
                    conv_id = msg.get("conv_id", "default")
                    source = msg.get("source", "dashboard")
                except json.JSONDecodeError:
                    message = data
                    conv_id = "default"
                    source = "dashboard"

                await websocket.send_json({
                    "type": "thinking",
                    "data": {"message": "Processing..."}
                })
                result = await command_center.handle_input(
                    source=source, message=message, conv_id=conv_id
                )
                await websocket.send_json({
                    "type": "response",
                    "data": {
                        "response": result["response"],
                        "route": result["route"],
                        "intent": result["intent"],
                    }
                })
        except WebSocketDisconnect:
            pass

    # ============================================================
    # Planning Pipeline endpoints
    # ============================================================

    @app.post("/api/planning/plan")
    async def plan(payload: dict):
        """Full pipeline: idea -> PRD -> specs -> tasks."""
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        result = await pipeline.plan(
            payload.get("idea", ""),
            payload.get("context", "")
        )
        return result

    @app.post("/api/planning/prd")
    async def generate_prd(payload: dict):
        """Generate PRD only."""
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return await pipeline.plan_prd_only(
            payload.get("idea", ""),
            payload.get("context", "")
        )

    @app.get("/api/planning/prds")
    async def list_prds():
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return {"prds": pipeline.get_prds()}

    @app.get("/api/planning/prds/{prd_id}")
    async def get_prd(prd_id: str):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        prd = pipeline.get_prd(prd_id)
        if not prd:
            return {"error": "PRD not found"}
        return prd

    @app.get("/api/planning/tasks")
    async def get_tasks(prd_id: str = None, status: str = None):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return {"tasks": pipeline.get_tasks(prd_id=prd_id, status=status)}

    @app.delete("/api/planning/tasks/{task_id}")
    async def delete_task(task_id: str):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return pipeline.tracker.delete_task(task_id)

    @app.post("/api/planning/tasks/bulk")
    async def bulk_update_tasks(payload: dict):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        task_ids = payload.get("task_ids", [])
        status = payload.get("status", "")
        results = {}
        for tid in task_ids:
            results[tid] = pipeline.tracker.update_task(tid, status=status)
        return {"updated": len(results), "results": results}

    @app.post("/api/planning/tasks/{task_id}/assign")
    async def assign_task(task_id: str, payload: dict):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        agent = payload.get("agent", "")
        return pipeline.tracker.update_task(task_id, assigned_agent=agent)

    @app.delete("/api/planning/prds/{prd_id}")
    async def delete_prd(prd_id: str):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return pipeline.tracker.delete_prd(prd_id)

    @app.post("/api/planning/prds/{prd_id}/approve")
    async def approve_prd(prd_id: str, payload: dict):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        approved = payload.get("approved", True)
        status = "approved" if approved else "rejected"
        return pipeline.tracker.update_prd(prd_id, status=status)

    @app.get("/api/planning/progress")
    async def get_progress(prd_id: str = None):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        return pipeline.get_progress(prd_id=prd_id)

    @app.post("/api/planning/tasks/{task_id}/status")
    async def update_task_status(task_id: str, payload: dict):
        pipeline = getattr(command_center, "_planning", None)
        if not pipeline:
            return {"error": "Planning pipeline not initialized"}
        success = pipeline.update_task_status(task_id, payload.get("status", ""))
        return {"updated": success, "task_id": task_id, "status": payload.get("status")}

    # ============================================================
    # Skills endpoints
    # ============================================================

    @app.get("/api/skills")
    async def list_skills(category: str = None, q: str = None):
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        if q:
            return {"skills": registry.search_skills(q)}
        return {"skills": registry.list_skills(category=category)}

    @app.get("/api/skills/stats")
    async def skills_stats():
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        return registry.stats()

    @app.get("/api/skills/categories")
    async def skills_categories():
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        return {"categories": registry.get_categories()}

    @app.get("/api/skills/{skill_id}")
    async def get_skill(skill_id: str):
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        skill = registry.get_skill(skill_id)
        if not skill:
            return {"error": "Skill not found"}
        return skill

    @app.post("/api/skills/create")
    async def create_skill(payload: dict):
        authoring = getattr(command_center, "_skill_authoring", None)
        if not authoring:
            return {"error": "Skill authoring not initialized"}
        return await authoring.create_skill(
            payload.get("description", ""),
            payload.get("context", "")
        )

    @app.delete("/api/skills/{skill_id}")
    async def remove_skill(skill_id: str):
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        success = registry.remove_skill(skill_id)
        return {"removed": success, "skill_id": skill_id}

    # ============================================================
    # Prompt Storage endpoints
    # ============================================================

    @app.get("/api/prompts")
    async def list_prompts(category: str = "", q: str = ""):
        """List all saved prompts."""
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        prompts = registry.list_prompts(category=category or None, query=q or None)
        return {"prompts": prompts}

    @app.post("/api/prompts")
    async def save_prompt(payload: dict):
        """Save a new prompt."""
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        result = registry.save_prompt(
            name=payload.get("name", ""),
            content=payload.get("content", ""),
            category=payload.get("category", "general"),
            tags=payload.get("tags", []),
            description=payload.get("description", ""),
        )
        return result

    @app.delete("/api/prompts/{prompt_id}")
    async def delete_prompt(prompt_id: str):
        """Delete a saved prompt."""
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        success = registry.delete_prompt(prompt_id)
        return {"removed": success, "prompt_id": prompt_id}

    @app.post("/api/prompts/{prompt_id}/use")
    async def use_prompt(prompt_id: str):
        """Mark a prompt as used (increment counter)."""
        registry = getattr(command_center, "_skill_registry", None)
        if not registry:
            return {"error": "Skill registry not initialized"}
        result = registry.use_prompt(prompt_id)
        return result

    # ============================================================
    # Repo Skill Extraction endpoints
    # ============================================================

    @app.post("/api/skills/extract-repo")
    async def extract_repo_skills(payload: dict):
        """Extract SKILL.md files from a GitHub repo."""
        import httpx
        repo_url = payload.get("repo_url", "")
        if not repo_url:
            return {"error": "No repo URL provided"}

        # Parse GitHub URL
        # Handle: https://github.com/owner/repo or owner/repo
        repo_url = repo_url.strip().rstrip("/")
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            if len(parts) < 2:
                return {"error": "Invalid GitHub URL format"}
            owner, repo = parts[0], parts[1]
        else:
            parts = repo_url.split("/")
            if len(parts) != 2:
                return {"error": "Format: owner/repo or full GitHub URL"}
            owner, repo = parts[0], parts[1]

        # Fetch repo tree via GitHub API
        try:
            async with httpx.AsyncClient() as client:
                # Get default branch
                resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    timeout=10
                )
                if resp.status_code != 200:
                    return {"error": f"Repository not found: {owner}/{repo}"}
                default_branch = resp.json().get("default_branch", "main")

                # Get file tree
                resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
                    timeout=15
                )
                if resp.status_code != 200:
                    return {"error": "Could not fetch repo tree"}

                tree = resp.json().get("tree", [])

                # Find SKILL.md files
                skill_files = []
                for item in tree:
                    path = item.get("path", "")
                    if path.endswith(".md") and ("skill" in path.lower() or "SKILL" in path):
                        skill_files.append(path)
                    elif path.endswith("/SKILL.md"):
                        skill_files.append(path)

                if not skill_files:
                    # Also look for any .md files that might be skills
                    md_files = [item.get("path", "") for item in tree if item.get("path", "").endswith(".md")]
                    # Filter for likely skill files
                    skill_keywords = ["skill", "guide", "instruction", "pattern", "workflow"]
                    for md in md_files:
                        filename = md.split("/")[-1].lower()
                        if any(kw in filename for kw in skill_keywords):
                            skill_files.append(md)

                if not skill_files:
                    return {"error": "No skill files found in repository", "total_files": len(tree)}

                # Download and install each skill
                installed = []
                for skill_path in skill_files[:10]:  # Max 10 skills
                    try:
                        resp = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/contents/{skill_path}",
                            timeout=10
                        )
                        if resp.status_code == 200:
                            import base64
                            content = base64.b64decode(resp.json().get("content", "")).decode("utf-8")

                            # Generate skill ID from filename
                            filename = skill_path.split("/")[-1].replace(".md", "")
                            skill_id = f"{repo}-{filename}".lower().replace(" ", "-")

                            # Install skill
                            registry = getattr(command_center, "_skill_registry", None)
                            if registry:
                                # Parse metadata from content
                                import re
                                metadata = {"name": filename, "description": f"From {owner}/{repo}"}
                                frontmatter = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
                                if frontmatter:
                                    for line in frontmatter.group(1).split("\n"):
                                        if ":" in line:
                                            key, val = line.split(":", 1)
                                            key = key.strip().lower()
                                            val = val.strip()
                                            if key in ("name", "description", "category", "tags", "version"):
                                                if val.startswith("["):
                                                    val = [v.strip() for v in val[1:-1].split(",")]
                                                metadata[key] = val

                                registry.install_skill(skill_id, content, {
                                    **metadata,
                                    "source": f"github:{owner}/{repo}",
                                    "version": metadata.get("version", "1.0.0"),
                                })
                                installed.append({"id": skill_id, "path": skill_path, "name": metadata.get("name", filename)})
                    except Exception as e:
                        continue

                return {
                    "repo": f"{owner}/{repo}",
                    "found": len(skill_files),
                    "installed": len(installed),
                    "skills": installed,
                }

        except httpx.TimeoutException:
            return {"error": "GitHub API timeout. Try again."}
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}

    # ============================================================
    # Voice endpoints
    # ============================================================

    @app.get("/api/voice/status")
    async def voice_status():
        voice = getattr(command_center, "_voice", None)
        if not voice:
            return {"enabled": False, "error": "Voice not initialized"}
        return voice.status()

    @app.post("/api/voice/start")
    async def voice_start():
        voice = getattr(command_center, "_voice", None)
        if not voice:
            return {"error": "Voice not initialized"}
        asyncio.create_task(voice.start())
        return {"status": "starting"}

    @app.post("/api/voice/stop")
    async def voice_stop():
        voice = getattr(command_center, "_voice", None)
        if not voice:
            return {"error": "Voice not initialized"}
        voice.stop()
        return {"status": "stopped"}

    @app.post("/api/voice/speak")
    async def voice_speak(payload: dict):
        """Speak text via TTS. Returns audio/mpeg stream (Edge Neural)."""
        voice = getattr(command_center, "_voice", None)
        if not voice:
            return {"error": "Voice not initialized"}
        text = payload.get("text", "")
        if not text:
            return {"error": "No text provided"}
        voice_name = payload.get("voice")  # yasmin | osman
        # Strip markdown for cleaner speech
        import re as _re
        clean = _re.sub(r"```[\s\S]*?```", " kod. ", text)
        clean = _re.sub(r"[*_`#>\[\]]", "", clean)
        clean = _re.sub(r"\s+", " ", clean).strip()[:800]

        from fastapi.responses import Response
        result = await voice.tts.synthesize_async(clean, voice_name)
        audio = result.get("audio", b"")
        if not audio:
            return {"error": result.get("error", "TTS failed")}
        return Response(
            content=audio,
            media_type="audio/mpeg"
            if result.get("format") == "mp3"
            else "audio/wav",
            headers={
                "X-TTS-Engine": result.get("engine", "none"),
                "X-TTS-Voice": result.get("voice", ""),
            },
        )

    @app.get("/api/voice/voices")
    async def voice_voices():
        """List available neural voices."""
        return {
            "voices": [
                {"id": "yasmin", "name": "Yasmin",
                 "lang": "ms-MY", "gender": "female"},
                {"id": "osman", "name": "Osman",
                 "lang": "ms-MY", "gender": "male"},
            ],
            "default": "yasmin",
        }

    # ============================================================
    # Security & Pentest endpoints
    # ============================================================

    @app.get("/api/security/status")
    async def security_status():
        gate = getattr(command_center, "_approval_gate", None)
        sandbox = getattr(command_center, "_sandbox", None)
        audit = getattr(command_center, "_audit", None)
        pentest = getattr(command_center, "_pentest", None)
        return {
            "approval_gate": gate.status() if gate else None,
            "sandbox": sandbox.status() if sandbox else None,
            "audit": audit.status() if audit else None,
            "pentest": pentest.status() if pentest else None,
        }

    @app.get("/api/security/approvals")
    async def approvals_pending():
        gate = getattr(command_center, "_approval_gate", None)
        if not gate:
            return {"error": "Approval gate not initialized"}
        return {"pending": gate.get_pending(), "history": gate.get_history(20)}

    @app.post("/api/security/approvals/{request_id}/approve")
    async def approval_approve(request_id: str):
        gate = getattr(command_center, "_approval_gate", None)
        if not gate:
            return {"error": "Approval gate not initialized"}
        return await gate.approve(request_id)

    @app.post("/api/security/approvals/{request_id}/deny")
    async def approval_deny(request_id: str, payload: dict = None):
        gate = getattr(command_center, "_approval_gate", None)
        if not gate:
            return {"error": "Approval gate not initialized"}
        reason = (payload or {}).get("reason", "")
        return await gate.deny(request_id, reason)

    @app.get("/api/security/audit")
    async def audit_log(limit: int = 50, agent: str = None,
                         severity: str = None):
        audit = getattr(command_center, "_audit", None)
        if not audit:
            return {"error": "Audit not initialized"}
        return {"entries": audit.get_log(limit=limit, agent=agent,
                                          severity=severity)}

    @app.get("/api/security/audit/stats")
    async def audit_stats():
        audit = getattr(command_center, "_audit", None)
        if not audit:
            return {"error": "Audit not initialized"}
        return audit.get_stats()

    @app.post("/api/pentest/run")
    async def pentest_run(payload: dict):
        """Run pentest pipeline on target."""
        pentest = getattr(command_center, "_pentest", None)
        if not pentest:
            return {"error": "Pentest not initialized"}
        target = payload.get("target", "")
        if not target:
            return {"error": "No target specified"}
        approved = payload.get("approved", False)
        phases = payload.get("phases")
        return await pentest.run(target, phases=phases, approved=approved)

    @app.get("/api/pentest/sessions")
    async def pentest_sessions():
        pentest = getattr(command_center, "_pentest", None)
        if not pentest:
            return {"error": "Pentest not initialized"}
        return {"sessions": pentest.list_sessions()}

    @app.get("/api/pentest/sessions/{session_id}")
    async def pentest_session(session_id: str):
        pentest = getattr(command_center, "_pentest", None)
        if not pentest:
            return {"error": "Pentest not initialized"}
        session = pentest.load_session(session_id)
        if not session:
            return {"error": "Session not found"}
        return session

    @app.post("/api/pentest/recon")
    async def pentest_recon(payload: dict):
        """Run recon only on target."""
        pentest = getattr(command_center, "_pentest", None)
        if not pentest:
            return {"error": "Pentest not initialized"}
        target = payload.get("target", "")
        return await pentest.recon.full_recon(target)

    @app.post("/api/pentest/scan")
    async def pentest_scan(payload: dict):
        """Run vulnerability scan only."""
        pentest = getattr(command_center, "_pentest", None)
        if not pentest:
            return {"error": "Pentest not initialized"}
        target = payload.get("target", "")
        return await pentest.scanner.scan_custom(target)

    # ============================================================
    # Security Agent endpoints (real tool capabilities)
    # ============================================================

    @app.get("/api/security/agent/status")
    async def security_agent_status():
        """Get security agent status with tool info."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        return agent.status()

    @app.post("/api/security/agent/run")
    async def security_agent_run(payload: dict):
        """Run a task through the security agent with real tools."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        task = payload.get("task", "")
        if not task:
            return {"error": "No task specified"}
        context = payload.get("context", {})
        result = await agent.run(task, context=context)
        return result

    @app.post("/api/security/agent/dns")
    async def security_agent_dns(payload: dict):
        """DNS lookup via security agent."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        target = payload.get("target", "")
        if not target:
            return {"error": "No target specified"}
        result = await agent.use_tool("dns_lookup", target=target)
        return result

    @app.post("/api/security/agent/portscan")
    async def security_agent_portscan(payload: dict):
        """Port scan via security agent."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        target = payload.get("target", "")
        if not target:
            return {"error": "No target specified"}
        ports = payload.get("ports", "1-1000")
        scan_type = payload.get("scan_type", "fast")
        result = await agent.use_tool("port_scan", target=target, ports=ports, scan_type=scan_type)
        return result

    @app.post("/api/security/agent/vulnscan")
    async def security_agent_vulnscan(payload: dict):
        """Vulnerability scan via security agent."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        target = payload.get("target", "")
        if not target:
            return {"error": "No target specified"}
        result = await agent.use_tool("vuln_scan", target=target)
        return result

    @app.post("/api/security/agent/fullrecon")
    async def security_agent_fullrecon(payload: dict):
        """Full recon via security agent."""
        agent = getattr(command_center, "_security_agent", None)
        if not agent:
            return {"error": "Security agent not initialized"}
        target = payload.get("target", "")
        if not target:
            return {"error": "No target specified"}
        result = await agent.use_tool("full_recon", target=target)
        return result

    # ============================================================
    # Channels endpoints
    # ============================================================

    @app.get("/api/channels")
    async def channels_status():
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        return mgr.status()

    @app.post("/api/channels/start")
    async def channels_start_all():
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        return await mgr.start_all()

    @app.post("/api/channels/stop")
    async def channels_stop_all():
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        return await mgr.stop_all()

    @app.post("/api/channels/{name}/start")
    async def channel_start(name: str):
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        return await mgr.start_channel(name)

    @app.post("/api/channels/{name}/stop")
    async def channel_stop(name: str):
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        return await mgr.stop_channel(name)

    @app.post("/api/channels/{name}/send")
    async def channel_send(name: str, payload: dict):
        mgr = getattr(command_center, "_channel_manager", None)
        if not mgr:
            return {"error": "Channel manager not initialized"}
        recipient = payload.get("recipient", "")
        text = payload.get("text", "")
        return await mgr.send_to_channel(name, recipient, text)

    # ============================================================
    # Notification Service endpoints
    # ============================================================

    @app.get("/api/notifications/status")
    async def notification_status():
        svc = getattr(command_center, "_notification_service", None)
        if not svc:
            return {"error": "Notification service not initialized"}
        return svc.status()

    @app.post("/api/notifications/send")
    async def notification_send(payload: dict):
        svc = getattr(command_center, "_notification_service", None)
        if not svc:
            return {"error": "Notification service not initialized"}
        return await svc.send(
            message=payload.get("message", ""),
            priority=payload.get("priority", "normal"),
            title=payload.get("title", ""),
            channels=payload.get("channels"),
            recipient=payload.get("recipient"),
            quiet_ok=payload.get("quiet_ok", False),
        )

    @app.post("/api/notifications/routing")
    async def notification_routing(payload: dict):
        svc = getattr(command_center, "_notification_service", None)
        if not svc:
            return {"error": "Notification service not initialized"}
        return svc.update_routing(payload.get("routing", {}))

    # ============================================================
    # Marketing System endpoints
    # ============================================================

    # --- Leads ---
    @app.get("/api/marketing/leads")
    async def marketing_leads(status: str = "", q: str = ""):
        from core.marketing.leads import get_leads
        return {"leads": get_leads(status=status or None, search=q or None)}

    @app.post("/api/marketing/leads")
    async def marketing_create_lead(payload: dict):
        from core.marketing.leads import create_lead
        return create_lead(
            name=payload.get("name", ""),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
            company=payload.get("company", ""),
            source=payload.get("source", "manual"),
            notes=payload.get("notes", ""),
            tags=payload.get("tags", []),
        )

    @app.put("/api/marketing/leads/{lead_id}")
    async def marketing_update_lead(lead_id: int, payload: dict):
        from core.marketing.leads import update_lead
        return update_lead(lead_id, **payload) or {"error": "Lead not found"}

    @app.delete("/api/marketing/leads/{lead_id}")
    async def marketing_delete_lead(lead_id: int):
        from core.marketing.leads import delete_lead
        return {"removed": delete_lead(lead_id)}

    @app.post("/api/marketing/leads/{lead_id}/convert")
    async def marketing_convert_lead(lead_id: int):
        from core.marketing.leads import convert_lead_to_client
        result = convert_lead_to_client(lead_id)
        return result or {"error": "Lead not found"}

    @app.post("/api/marketing/leads/{lead_id}/score")
    async def marketing_score_lead(lead_id: int):
        from core.marketing.leads import score_lead
        return {"lead_id": lead_id, "score": score_lead(lead_id)}

    @app.get("/api/marketing/leads/stats")
    async def marketing_lead_stats():
        from core.marketing.leads import lead_stats
        return lead_stats()

    # --- Clients ---
    @app.get("/api/marketing/clients")
    async def marketing_clients(status: str = "", tier: str = "", q: str = ""):
        from core.marketing.clients import get_clients
        return {"clients": get_clients(status=status or None, tier=tier or None, search=q or None)}

    @app.post("/api/marketing/clients")
    async def marketing_create_client(payload: dict):
        from core.marketing.clients import create_client
        return create_client(
            name=payload.get("name", ""),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
            company=payload.get("company", ""),
            address=payload.get("address", ""),
            lead_id=payload.get("lead_id"),
            tier=payload.get("tier", "basic"),
            notes=payload.get("notes", ""),
            tags=payload.get("tags", []),
        )

    @app.put("/api/marketing/clients/{client_id}")
    async def marketing_update_client(client_id: int, payload: dict):
        from core.marketing.clients import update_client
        return update_client(client_id, **payload) or {"error": "Client not found"}

    @app.delete("/api/marketing/clients/{client_id}")
    async def marketing_delete_client(client_id: int):
        from core.marketing.clients import delete_client
        return {"removed": delete_client(client_id)}

    @app.get("/api/marketing/clients/stats")
    async def marketing_client_stats():
        from core.marketing.clients import client_stats
        return client_stats()

    @app.post("/api/marketing/clients/{client_id}/approve")
    async def marketing_client_approve(client_id: int, payload: dict):
        from core.marketing.clients import send_approval_request
        return send_approval_request(
            client_id=client_id,
            approval_type=payload.get("type", "service"),
            ref_id=payload.get("ref_id", client_id),
            message=payload.get("message", ""),
            channels=payload.get("channels", ["email"]),
        )

    # --- Approvals ---
    @app.get("/api/marketing/approvals")
    async def marketing_approvals():
        from core.marketing.clients import get_pending_approvals
        return {"pending": get_pending_approvals()}

    @app.post("/api/marketing/approvals/{approval_id}/respond")
    async def marketing_respond_approval(approval_id: int, payload: dict):
        from core.marketing.clients import respond_to_approval
        return respond_to_approval(
            approval_id,
            response=payload.get("response", ""),
            approved=payload.get("approved", False),
        )

    # --- Campaigns ---
    @app.get("/api/marketing/campaigns")
    async def marketing_campaigns(status: str = ""):
        from core.marketing.campaigns import get_campaigns
        return {"campaigns": get_campaigns(status=status or None)}

    @app.post("/api/marketing/campaigns")
    async def marketing_create_campaign(payload: dict):
        from core.marketing.campaigns import create_campaign
        return create_campaign(
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            campaign_type=payload.get("type", "general"),
            budget=payload.get("budget", 0),
            target_audience=payload.get("target_audience", ""),
            channels=payload.get("channels", []),
            start_date=payload.get("start_date", ""),
            end_date=payload.get("end_date", ""),
        )

    @app.put("/api/marketing/campaigns/{campaign_id}")
    async def marketing_update_campaign(campaign_id: int, payload: dict):
        from core.marketing.campaigns import update_campaign
        return update_campaign(campaign_id, **payload) or {"error": "Campaign not found"}

    @app.delete("/api/marketing/campaigns/{campaign_id}")
    async def marketing_delete_campaign(campaign_id: int):
        from core.marketing.campaigns import delete_campaign
        return {"removed": delete_campaign(campaign_id)}

    @app.get("/api/marketing/campaigns/stats")
    async def marketing_campaign_stats():
        from core.marketing.campaigns import campaign_stats
        return campaign_stats()

    # --- Content ---
    @app.get("/api/marketing/content")
    async def marketing_content(status: str = "", platform: str = ""):
        from core.marketing.campaigns import get_content
        return {"content": get_content(status=status or None, platform=platform or None)}

    @app.post("/api/marketing/content")
    async def marketing_create_content(payload: dict):
        from core.marketing.campaigns import create_content
        return create_content(
            title=payload.get("title", ""),
            body=payload.get("body", ""),
            content_type=payload.get("content_type", "post"),
            platform=payload.get("platform", "instagram"),
            campaign_id=payload.get("campaign_id"),
            hashtags=payload.get("hashtags", []),
            scheduled_at=payload.get("scheduled_at", ""),
        )

    @app.put("/api/marketing/content/{content_id}")
    async def marketing_update_content(content_id: int, payload: dict):
        from core.marketing.campaigns import update_content
        return update_content(content_id, **payload) or {"error": "Content not found"}

    @app.post("/api/marketing/content/{content_id}/publish")
    async def marketing_publish_content(content_id: int):
        from core.marketing.campaigns import publish_content
        return publish_content(content_id) or {"error": "Content not found"}

    @app.post("/api/marketing/content/generate")
    async def marketing_generate_content(payload: dict):
        """AI-generated marketing content."""
        agent = getattr(command_center, "_marketing_agent", None)
        if not agent:
            return {"error": "Marketing agent not initialized"}
        topic = payload.get("topic", "")
        platform = payload.get("platform", "instagram")
        content_type = payload.get("content_type", "post")
        language = payload.get("language", "ms")
        task = f"""Generate {content_type} content for {platform} about: {topic}
Language: {language}
Include: headline, body, hashtags, call-to-action
Format as JSON with keys: title, body, hashtags, cta"""
        result = await agent.run(task)
        return {"generated": result.get("text", ""), "agent": "marketing"}

    # --- SEO ---
    @app.get("/api/marketing/seo")
    async def marketing_seo(url: str = ""):
        from core.marketing.seo import get_seo_tracking
        return {"tracking": get_seo_tracking(url=url or None)}

    @app.post("/api/marketing/seo")
    async def marketing_add_seo(payload: dict):
        from core.marketing.seo import add_seo_tracking
        return add_seo_tracking(
            url=payload.get("url", ""),
            keyword=payload.get("keyword", ""),
            position=payload.get("position", 0),
            search_volume=payload.get("search_volume", 0),
            competition=payload.get("competition", ""),
            page_score=payload.get("page_score", 0),
        )

    @app.post("/api/marketing/seo/{tracking_id}/update")
    async def marketing_update_seo(tracking_id: int, payload: dict):
        from core.marketing.seo import update_seo_position
        return update_seo_position(
            tracking_id,
            position=payload.get("position", 0),
            page_score=payload.get("page_score"),
        ) or {"error": "Not found"}

    @app.delete("/api/marketing/seo/{tracking_id}")
    async def marketing_delete_seo(tracking_id: int):
        from core.marketing.seo import delete_seo_tracking
        return {"removed": delete_seo_tracking(tracking_id)}

    @app.get("/api/marketing/seo/stats")
    async def marketing_seo_stats():
        from core.marketing.seo import seo_stats
        return seo_stats()

    @app.post("/api/marketing/seo/audit")
    async def marketing_seo_audit(payload: dict):
        """Run SEO audit on a URL."""
        from core.tools.web_tools import seo_audit
        import json
        url = payload.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        result = json.loads(seo_audit(url))
        return result

    @app.post("/api/marketing/seo/keywords")
    async def marketing_seo_keywords(payload: dict):
        """Research keywords."""
        from core.tools.web_tools import keyword_research
        import json
        topic = payload.get("topic", "")
        if not topic:
            return {"error": "No topic provided"}
        result = json.loads(keyword_research(topic))
        return result

    @app.post("/api/marketing/seo/competitor")
    async def marketing_seo_competitor(payload: dict):
        """Analyze competitor website."""
        from core.tools.web_tools import analyze_competitor
        import json
        url = payload.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        result = json.loads(analyze_competitor(url))
        return result

    # --- Invoices ---
    @app.get("/api/marketing/invoices")
    async def marketing_invoices(client_id: int = 0, status: str = ""):
        from core.marketing.invoices import get_invoices
        return {"invoices": get_invoices(client_id=client_id or None, status=status or None)}

    @app.post("/api/marketing/invoices")
    async def marketing_create_invoice(payload: dict):
        from core.marketing.invoices import create_invoice
        return create_invoice(
            client_id=payload.get("client_id", 0),
            amount=payload.get("amount", 0),
            description=payload.get("description", ""),
            items=payload.get("items", []),
            tax_rate=payload.get("tax_rate", 0),
            currency=payload.get("currency", "MYR"),
            due_days=payload.get("due_days", 30),
        )

    @app.post("/api/marketing/invoices/{invoice_id}/pay")
    async def marketing_pay_invoice(invoice_id: int, payload: dict):
        from core.marketing.invoices import mark_invoice_paid
        return mark_invoice_paid(
            invoice_id,
            payment_method=payload.get("method", ""),
            payment_ref=payload.get("ref", ""),
        ) or {"error": "Invoice not found"}

    @app.delete("/api/marketing/invoices/{invoice_id}")
    async def marketing_delete_invoice(invoice_id: int):
        from core.marketing.invoices import delete_invoice
        return {"removed": delete_invoice(invoice_id)}

    @app.get("/api/marketing/invoices/stats")
    async def marketing_invoice_stats():
        from core.marketing.invoices import invoice_stats
        return invoice_stats()

    # --- Marketing Dashboard ---
    @app.get("/api/marketing/dashboard")
    async def marketing_dashboard():
        from core.marketing.leads import lead_stats
        from core.marketing.clients import client_stats
        from core.marketing.campaigns import campaign_stats
        from core.marketing.seo import seo_stats
        from core.marketing.invoices import invoice_stats
        from core.marketing.clients import get_activity_log
        return {
            "leads": lead_stats(),
            "clients": client_stats(),
            "campaigns": campaign_stats(),
            "seo": seo_stats(),
            "invoices": invoice_stats(),
            "activity": get_activity_log(10),
        }

    @app.post("/api/marketing/chat")
    async def marketing_chat(payload: dict):
        """Chat with marketing agent."""
        agent = getattr(command_center, "_marketing_agent", None)
        if not agent:
            return {"error": "Marketing agent not initialized"}
        message = payload.get("message", "")
        result = await agent.run(message)
        return {"response": result.get("text", ""), "tools_used": result.get("tools_used", [])}

    # ============================================================
    # OS Kernel endpoints
    # ============================================================

    @app.get("/api/kernel/status")
    async def kernel_status():
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return kernel.status()

    @app.post("/api/kernel/start")
    async def kernel_start_all():
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return await kernel.start_all()

    @app.post("/api/kernel/stop")
    async def kernel_stop_all():
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return await kernel.stop_all()

    @app.post("/api/kernel/{name}/start")
    async def kernel_start_one(name: str):
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return await kernel.start_agent(name)

    @app.post("/api/kernel/{name}/stop")
    async def kernel_stop_one(name: str):
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return await kernel.stop_agent(name)

    @app.post("/api/kernel/{name}/run")
    async def kernel_run_once(name: str):
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return await kernel.run_once(name)

    @app.get("/api/kernel/agents")
    async def kernel_list():
        kernel = getattr(command_center, "_kernel", None)
        if not kernel:
            return {"error": "Kernel not initialized"}
        return {"agents": kernel.list_agents()}

    # ============================================================
    # Daemon Manager endpoints
    # ============================================================

    @app.get("/api/daemon/status")
    async def daemon_status():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return daemon.status()

    @app.get("/api/daemon/alerts")
    async def daemon_alerts():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return {"alerts": daemon.get_alerts()}

    @app.get("/api/daemon/services")
    async def daemon_services():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return {"services": daemon.get_service_registry()}

    @app.post("/api/daemon/watchdog/start")
    async def daemon_watchdog_start():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return await daemon.start_watchdog()

    @app.post("/api/daemon/watchdog/stop")
    async def daemon_watchdog_stop():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return await daemon.stop_watchdog()

    @app.post("/api/daemon/restart/{name}")
    async def daemon_restart_agent(name: str):
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return await daemon.restart_agent(name)

    @app.post("/api/daemon/restart-all")
    async def daemon_restart_all():
        daemon = getattr(command_center, "_daemon_manager", None)
        if not daemon:
            return {"error": "Daemon manager not initialized"}
        return await daemon.restart_all()

    # ============================================================
    # Meta Agent endpoints
    # ============================================================

    @app.get("/api/meta/status")
    async def meta_status():
        meta = getattr(command_center, "_meta_agent", None)
        if not meta:
            return {"error": "Meta agent not initialized"}
        return meta.status()

    @app.get("/api/meta/suggestions")
    async def meta_suggestions():
        meta = getattr(command_center, "_meta_agent", None)
        if not meta:
            return {"error": "Meta agent not initialized"}
        return {"suggestions": meta.cache.get_suggestions()}

    @app.get("/api/meta/patterns")
    async def meta_patterns(pattern_type: str = None,
                             severity: str = None):
        meta = getattr(command_center, "_meta_agent", None)
        if not meta:
            return {"error": "Meta agent not initialized"}
        return {"patterns": meta.cache.get_patterns(
            pattern_type=pattern_type, severity=severity
        )}

    @app.get("/api/meta/stats")
    async def meta_stats(agent: str = None):
        meta = getattr(command_center, "_meta_agent", None)
        if not meta:
            return {"error": "Meta agent not initialized"}
        return {
            "agent_stats": meta.cache.get_agent_stats(agent=agent),
            "cache_stats": meta.cache.get_cache_stats(),
        }

    @app.post("/api/meta/analyze")
    async def meta_analyze():
        """Run full fleet analysis."""
        meta = getattr(command_center, "_meta_agent", None)
        if not meta:
            return {"error": "Meta agent not initialized"}
        analysis = await meta.analyze_fleet()
        suggestions = await meta.generate_suggestions(analysis)
        corrections = await meta.generate_corrections(analysis)
        return {
            "analysis": analysis,
            "suggestions": suggestions,
            "corrections": corrections,
            "message": meta._summarize(suggestions, corrections),
        }

    # ============================================================
    # Visualization endpoints (ai-town style)
    # ============================================================

    @app.get("/api/viz/map")
    async def viz_map():
        """Get full agent map state for rendering."""
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        return am.get_state()

    @app.get("/api/viz/status")
    async def viz_status():
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        return am.status()

    @app.post("/api/viz/move")
    async def viz_move(payload: dict):
        """Move agent to a station."""
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        am.move_agent(
            payload.get("agent", ""),
            payload.get("station", ""),
            payload.get("task", ""),
            payload.get("progress", 0),
        )
        return {"status": "moved", "agent": payload.get("agent")}

    @app.post("/api/viz/speech")
    async def viz_speech(payload: dict):
        """Set agent speech bubble."""
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        am.set_speech(
            payload.get("agent", ""),
            payload.get("text", ""),
            payload.get("duration", 10),
        )
        return {"status": "set", "agent": payload.get("agent")}

    @app.post("/api/viz/interaction")
    async def viz_interaction(payload: dict):
        """Record agent-to-agent interaction."""
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        am.add_interaction(
            payload.get("agent_a", ""),
            payload.get("agent_b", ""),
            payload.get("type", "message"),
            payload.get("details", ""),
        )
        return {"status": "recorded"}

    @app.post("/api/viz/reset")
    async def viz_reset():
        """Reset all agents to home."""
        am = getattr(command_center, "_agent_map", None)
        if not am:
            return {"error": "Agent map not initialized"}
        am.reset()
        return {"status": "reset"}

    # ============================================================
    # Google Drive endpoints
    # ============================================================

    @app.get("/api/gdrive/status")
    async def gdrive_status():
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return gdrive.status()

    @app.post("/api/gdrive/backup")
    async def gdrive_backup(payload: dict):
        """Backup data to Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        source = payload.get("source", "./data")
        subfolder = payload.get("subfolder", "")
        return gdrive.backup(source, subfolder)

    @app.post("/api/gdrive/backup-all")
    async def gdrive_backup_all():
        """Full backup: database + config + vault."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return gdrive.backup_all(
            data_dir="./data",
            config_dir="./config",
            vault_dir="./obsidian-vault"
        )

    @app.get("/api/gdrive/files")
    async def gdrive_list_files(path: str = ""):
        """List files on Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return gdrive.list_files(path)

    @app.post("/api/gdrive/upload")
    async def gdrive_upload(payload: dict):
        """Upload a file to Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        local_path = payload.get("local_path", "")
        remote_path = payload.get("remote_path", "")
        return gdrive.upload_file(local_path, remote_path)

    @app.post("/api/gdrive/download")
    async def gdrive_download(payload: dict):
        """Download a file from Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        remote_path = payload.get("remote_path", "")
        local_path = payload.get("local_path", "./downloads")
        return gdrive.download_file(remote_path, local_path)

    @app.get("/api/gdrive/read")
    async def gdrive_read_file(remote_path: str):
        """Read a text file from Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return gdrive.read_file(remote_path)

    @app.post("/api/gdrive/sync-vault")
    async def gdrive_sync_vault(payload: dict):
        """Sync Obsidian vault with Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        direction = payload.get("direction", "bidirectional")
        vault_dir = payload.get("vault_dir", "./obsidian-vault")
        return gdrive.sync_vault(vault_dir, direction)

    @app.post("/api/gdrive/upload-report")
    async def gdrive_upload_report(payload: dict):
        """Upload a report to Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        local_path = payload.get("local_path", "")
        report_name = payload.get("report_name", "")
        return gdrive.upload_report(local_path, report_name)

    @app.get("/api/gdrive/reports")
    async def gdrive_list_reports():
        """List reports on Google Drive."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return gdrive.list_reports()

    @app.get("/api/gdrive/setup")
    async def gdrive_setup():
        """Get setup instructions."""
        gdrive = getattr(command_center, "_gdrive", None)
        if not gdrive:
            return {"error": "GDrive not initialized"}
        return {"instructions": gdrive.setup_instructions()}

    return app
