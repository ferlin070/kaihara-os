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
        return {"tasks": pipeline.get_tasks(prd_id=prd_id)}

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
