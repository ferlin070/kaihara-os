"""
Command Center — entry point, intent parser, split brain, fleet manager.
The brain of Kaihara OS.
"""

import asyncio
import re
from typing import Any

from agents.base_agent import BaseAgent
from core.orchestrator.model_router import ModelRouter
from core.orchestrator.orchestrator_brain import brain as orchestrator_brain
from core.orchestrator.intent_parser import IntentParser


TELEGRAM_CONV_PREFIX = "telegram_"
TG_SEND_TRIGGER = re.compile(
    r"\b(hantar|mesej|message|notify|bagitahu|send|inform)\b"
    r"[^\n]{0,50}\btelegram\b|\btelegram\b[^\n]{0,50}"
    r"(terus|hantar|send|bagi|ke\s+saya)", re.IGNORECASE)


def _is_telegram_conv(conv_id: str) -> bool:
    return str(conv_id).startswith(TELEGRAM_CONV_PREFIX)


class SplitBrain:
    """Decide: reflex (fast) or deep (thorough) or workflow."""

    async def decide(self, intent: dict) -> str:
        if intent.get("is_workflow"):
            return "workflow"
        complexity = intent.get("complexity", "simple")
        if complexity in ("medium", "complex"):
            return "deep"
        return "reflex"


class FleetManager:
    """Spawn, monitor, and recover agents."""

    AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}
    AGENT_STATIONS = {
        "coding": "coding_desk",
        "marketing": "marketing_hub",
        "security": "security_terminal",
        "deploy": "deploy_station",
        "research": "research_desk",
        "meta": "meta_observatory",
        "kaihara": "command_center",
    }

    @classmethod
    def register(cls, agent_type: str, agent_class: type[BaseAgent]):
        cls.AGENT_REGISTRY[agent_type] = agent_class

    def __init__(self, config: dict, memory, model_router, token_juice,
                 approval_gate=None, agent_map=None, skill_registry=None):
        self.config = config
        self.memory = memory
        self.model = model_router
        self.token_juice = token_juice
        self.approval_gate = approval_gate
        self.skill_registry = skill_registry
        self.agent_map = agent_map
        self.active_agents: dict[str, BaseAgent] = {}

    async def dispatch(self, intent: dict) -> dict:
        agents_needed = intent.get("agents", ["kaihara"])
        tasks = []
        for agent_type in agents_needed:
            agent = self._spawn(agent_type)
            if agent:
                tasks.append(self._run_with_recovery(agent, intent))

        if not tasks:
            return {"error": "No agents available for this task"}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return await self._aggregate(results, intent)

    def _spawn(self, agent_type: str) -> BaseAgent | None:
        if agent_type in self.active_agents:
            return self.active_agents[agent_type]
        agent_class = self.AGENT_REGISTRY.get(agent_type)
        if not agent_class:
            return None
        agent = agent_class(
            config=self.config,
            memory=self.memory,
            model_router=self.model,
            token_juice=self.token_juice,
            approval_gate=self.approval_gate,
        )
        # Pass skill registry to agent if it supports it
        if hasattr(agent, 'set_skill_registry') and self.skill_registry:
            agent.set_skill_registry(self.skill_registry)
        self.active_agents[agent_type] = agent
        return agent

    async def _run_with_recovery(self, agent: BaseAgent,
                                  intent: dict) -> dict:
        # Update agent map: agent moves to station
        if self.agent_map:
            station = self.AGENT_STATIONS.get(
                agent.AGENT_TYPE, "command_center"
            )
            self.agent_map.move_agent(
                agent.AGENT_TYPE, station,
                intent["text"][:50], 0
            )
            self.agent_map.set_speech(
                agent.AGENT_TYPE, f"Working: {intent['text'][:40]}"
            )
        try:
            result = await asyncio.wait_for(
                agent.run(intent["text"]), timeout=300
            )
            if self.agent_map:
                self.agent_map.set_agent_status(
                    agent.AGENT_TYPE, "idle"
                )
                self.agent_map.set_speech(
                    agent.AGENT_TYPE, "Done.", 5
                )
            return {"agent": agent.AGENT_TYPE, "result": result, "status": "ok"}
        except asyncio.TimeoutError:
            return {
                "agent": agent.AGENT_TYPE,
                "result": "Agent timed out — root cause: task too complex or stuck",
                "status": "timeout",
            }
        except Exception as e:
            return {
                "agent": agent.AGENT_TYPE,
                "result": f"Agent failed — {e}",
                "status": "error",
            }

    async def _aggregate(self, results: list, intent: dict) -> dict:
        outputs = []
        for r in results:
            if isinstance(r, Exception):
                outputs.append({"error": str(r), "status": "exception"})
            else:
                outputs.append(r)
        if self.memory:
            combined = json.dumps(outputs)
            self.memory.store(combined, source="fleet", agent="fleet_manager")
        return {
            "intent": intent["text"],
            "results": outputs,
            "agents_used": [r.get("agent") for r in outputs if isinstance(r, dict)],
        }


import json


class CommandCenter:
    """The brain of Kaihara — routes input, delegates to agents."""

    def __init__(self, config: dict, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, skill_registry=None):
        self.config = config
        self.memory = memory
        self.model = model_router or ModelRouter(config)
        self.token_juice = token_juice
        self.intent_parser = IntentParser(model_router=self.model)
        self.split_brain = SplitBrain()
        self.fleet = FleetManager(
            config, memory, self.model, token_juice, approval_gate,
            skill_registry=skill_registry
        )
        self.kaihara_agent = None
        self._meta_agent = None
        self._agent_map = None
        self._skill_registry = skill_registry

    async def handle_input(self, source: str, message: str,
                            conv_id: str = "default") -> dict:
        """Main entry: parse intent → split brain → dispatch."""
        # Don't compress user input — preserve meaning

        # Meta agent: check cache before running
        cache_check = {"should_skip": False}
        if self._meta_agent:
            cache_check = self._meta_agent.check_before_run(
                message, intent_agent := ""
            )

        if self.memory:
            self.memory.add_context(conv_id, "user", message)
            context = self.memory.super_context(message)
            # Add relevant memories for personalization
            mem_results = self.memory.recall(message, limit=3)
            if mem_results:
                context += "

## Relevant Memories:
"
                for m in mem_results:
                    if m.get('score', 0) > 0.1:
                        context += f"- [{m.get('topic', 'general')}] {m.get('content', '')[:100]}
"
        else:
            context = ""

        intent = await self.intent_parser.parse(message)

        intent = await self.intent_parser.parse(message)

        # Telegram delivery: process task first, then SEND THE ANSWER
        # to user's Telegram (formatted), from non-telegram sources.
        if (source != "telegram" and not _is_telegram_conv(conv_id)
                and TG_SEND_TRIGGER.search(message)):
            try:
                from core.tools.notify_tools import (
                    send_telegram_message, telegram_status)
                st = telegram_status()
                if st.get("configured"):
                    # 0) Strip delivery phrase from the question
                    clean_q = _re.sub(
                        r"[,]?\s*(dan\s*)?(hantar|send)\s+(ke\s+)?"
                        r"(telegram(\s+saya)?|tg)\b[!.\s]*$",
                        "", message, flags=_re.IGNORECASE).strip() \
                            or message
                    # Re-parse intent on cleaned question
                    intent = await self.intent_parser.parse(clean_q)
                    # 1) Get the actual AI answer using normal pipeline
                    route = await self.split_brain.decide(intent)

                    context_tg = (self.memory.super_context(clean_q)
                                  if self.memory else "")
                    if route == "deep":
                        fleet_result = await self.fleet.dispatch(intent)
                        answer = self._format_response(fleet_result, route)
                    else:
                        refl = await self._reflex(clean_q, context_tg,
                                                  conv_id)
                        answer = refl.get("text", "")

                    # 2) Send the formatted ANSWER to Telegram
                    tg = send_telegram_message(answer)

                    if tg.get("ok"):
                        ids = ", ".join(
                            str(d["chat_id"]) for d in tg["details"])
                        response_text = (
                            f"✅ **Jawapan dihantar ke Telegram anda!**\n\n"
                            f"Soalan: \"{clean_q}\"\n"
                            f"Bot: {st.get('bot_username')} | Chat: {ids}\n\n"
                            f"--- Pratonton jawapan ---\n{answer[:600]}")
                        if self.memory:
                            self.memory.store(answer, source=source,
                                              agent="kaihara")
                            self.memory.add_context(conv_id, "user",
                                                    clean_q)
                            self.memory.add_context(conv_id, "assistant",
                                                    answer)
                        return {
                            "source": source, "route": "telegram_send",
                            "response": response_text, "intent": intent,
                            "cached": False, "tokens_saved": 0,
                        }
            except Exception:
                pass  # fall through to normal routing

        route = await self.split_brain.decide(intent)

        # Force reflex route for tool-capable tasks (PDF, Telegram, file ops)
        import re as _re
        _tool_triggers = _re.compile(
            r"\b(pdf|generate.*pdf|hantar.*telegram|send.*telegram|"
            r"send.*file|upload|download|report.*pdf|laporan.*pdf|"
            r"scan|pentest|recon|dns.*lookup|port.*scan|vuln|xss|sqli|security|"
            r"task|tugas|buat.*task|create.*task|add.*task|assign.*task)\b", _re.I)
        if _tool_triggers.search(message):
            route = "reflex"

        if cache_check.get("should_skip") and route != "reflex":
            result = {
                "text": cache_check.get("cached_result", {}).get(
                    "response", "[cached result]"
                ),
                "agent": "meta_cache",
                "cached": True,
                "tokens_saved": cache_check.get("tokens_saved", 0),
            }
        elif route == "reflex":
            result = await self._reflex(message, context, conv_id)
        elif route == "deep":
            result = await self.fleet.dispatch(intent)
        elif route == "workflow":
            result = await self._workflow(intent)
        else:
            result = await self._reflex(message, context, conv_id)

        # Meta agent: observe this run
        if self._meta_agent and not cache_check.get("should_skip"):
            try:
                import time
                start_time = time.time()
                await self._meta_agent.observe_run(
                    agent=result.get("agent", "kaihara"),
                    task=message,
                    result=result,
                    tokens_used=result.get("tokens_used", 0),
                    time_taken=time.time() - start_time,
                    model_used=self.model.default if self.model else "",
                    success=result.get("status") != "error",
                )
            except Exception:
                pass

        response = self._format_response(result, route)
        if self.memory:
            self.memory.store(response, source=source, agent="kaihara")
            self.memory.add_context(conv_id, "assistant", response)
        return {
            "source": source,
            "route": route,
            "response": response,
            "intent": intent,
            "cached": cache_check.get("should_skip", False),
            "tokens_saved": cache_check.get("tokens_saved", 0),
        }

    async def _reflex(self, message: str, context: str,
                       conv_id: str) -> dict:
        """Fast lane: simple questions answered directly. Intent-based tool execution."""
        import os, re, json, logging
        from pathlib import Path
        _log = logging.getLogger("kaihara.reflex")
        # Use agent-specific model for reflex
        reflex_model = self.model.agent_models.get("reflex", self.model.default)

        system = self._kaihara_system_prompt()
        if context:
            system = f"{system}\n\n{context}"

        conv_history = ""
        if self.memory:
            history = self.memory.get_context(conv_id)
            if history:
                conv_history = "\n".join(
                    f"{m['role']}: {m['content'][:200]}" for m in history[-5:]
                )
                if len(conv_history) > 2000:
                    conv_history = conv_history[-2000:]
        prompt = message
        if conv_history:
            prompt = f"Conversation history:\n{conv_history}\n\nUser: {message}"

        # ── INTENT DETECTION: PDF + Telegram ──
        msg_lower = message.lower()
        wants_pdf = bool(re.search(r'\b(pdf|report|laporan)\b', msg_lower))
        wants_telegram = bool(re.search(r'\b(telegram|tg|hantar.*telegram|send.*telegram)\b', msg_lower))
        wants_web = bool(re.search(r'\b(search|cari|google|web|research)\b', msg_lower))

        # ── EXECUTE TOOLS DIRECTLY ──
        if wants_pdf and wants_telegram:
            try:
                os.chdir("/opt/kaihara-os")
                # First get AI content
                response = await self.model.complete(model=reflex_model, 
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                # Generate PDF
                from core.tools.pdf_generator import generate_pdf_report
                from core.tools.notify_tools import send_telegram_document
                blocks = self._parse_md_to_blocks(response)
                pdf_path = generate_pdf_report(
                    title=message[:60],
                    content=blocks,
                    subtitle="Ghazwah Group — Kaihara OS",
                    output_filename=f"report_{message[:30].lower().replace(' ', '_')}"
                )
                # Send to Telegram
                doc_result = send_telegram_document(
                    file_path=pdf_path,
                    caption=f"📊 {message[:100]}"
                )
                if doc_result.get("ok"):
                    return {"text": f"✅ PDF telah dijana dan dihantar ke Telegram!\n📄 {pdf_path}", "agent": "reflex"}
                else:
                    err_msg = doc_result.get("error", "unknown")
                    return {"text": f"⚠️ PDF dijana tapi gagal hantar: {err_msg} | {pdf_path}", "agent": "reflex"}
            except Exception as e:
                _log.error(f"PDF+TG error: {e}")
                return {"text": f"❌ PDF error: {str(e)}", "agent": "reflex"}

        if wants_telegram and not wants_pdf:
            try:
                response = await self.model.complete(model=reflex_model, 
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                from core.tools.notify_tools import send_telegram_message
                result = send_telegram_message(response)
                if result.get("ok"):
                    return {"text": f"✅ Dihantar ke Telegram!\n\n{response[:400]}", "agent": "reflex"}
                return {"text": response, "agent": "reflex"}
            except Exception as e:
                return {"text": f"❌ Telegram error: {str(e)}", "agent": "reflex"}

        if wants_pdf and not wants_telegram:
            try:
                response = await self.model.complete(model=reflex_model, 
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                from core.tools.pdf_generator import generate_pdf_report
                blocks = self._parse_md_to_blocks(response)
                pdf_path = generate_pdf_report(
                    title=message[:60],
                    content=blocks,
                    subtitle="Ghazwah Group — Kaihara OS"
                )
                return {"text": f"✅ PDF dijana!\n📄 {pdf_path}\n\n{response[:400]}", "agent": "reflex"}
            except Exception as e:
                return {"text": f"❌ PDF error: {str(e)}", "agent": "reflex"}

        # ── INTENT: security scan ──
        wants_security = bool(re.search(r'\b(scan|pentest|pantest|recon|dns.*lookup|port.*scan|vuln|xss|sqli|security|celah|keselamatan)\b', msg_lower))
        wants_pentest = bool(re.search(r'\b(pentest|pantest|penetration|full.*scan|full.*recon)\b', msg_lower))

        if wants_security:
            import re as _re
            target_match = _re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})', message)
            if target_match:
                target = target_match.group(1)
                try:
                    import socket
                    scan_results = []
                    
                    if wants_pentest:
                        scan_results.append(f"🛡️ **Penetration Test: {target}**\n")
                    else:
                        scan_results.append(f"🔍 **Security Scan: {target}**\n")
                    
                    # DNS Lookup
                    try:
                        ip = socket.gethostbyname(target)
                        scan_results.append(f"✅ DNS: {target} → {ip}")
                    except Exception as e:
                        scan_results.append(f"❌ DNS failed: {e}")
                        ip = None
                    
                    # Port scan - more ports for pentest
                    import asyncio
                    if wants_pentest:
                        ports_to_scan = list(range(1, 1001))  # Full 1-1000 for pentest
                    else:
                        ports_to_scan = [80, 443, 22, 21, 25, 53, 8080, 3306]
                    
                    async def quick_port_scan(host, ports):
                        open_ports = []
                        async def check_port(port):
                            try:
                                _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=0.5)
                                writer.close()
                                await writer.wait_closed()
                                return port
                            except: return None
                        tasks = [check_port(p) for p in ports]
                        results = await asyncio.gather(*tasks)
                        return [p for p in results if p is not None]
                    
                    if ip:
                        open_ports = await quick_port_scan(ip, ports_to_scan)
                        if open_ports:
                            scan_results.append(f"✅ Open ports ({len(open_ports)}): {', '.join(map(str, open_ports[:20]))}" + ("..." if len(open_ports) > 20 else ""))
                        else:
                            scan_results.append("⚠️ No common ports open")
                    
                    # HTTP/HTTPS check
                    try:
                        import httpx
                        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                            r = await client.get(f"https://{target}")
                            server = r.headers.get('server', 'unknown')
                            scan_results.append(f"✅ HTTPS: {r.status_code} | Server: {server}")
                            # Check security headers
                            headers = r.headers
                            if 'strict-transport-security' in headers:
                                scan_results.append(f"  ✓ HSTS enabled")
                            if 'x-content-type-options' in headers:
                                scan_results.append(f"  ✓ X-Content-Type-Options: {headers['x-content-type-options']}")
                            if 'x-frame-options' in headers:
                                scan_results.append(f"  ✓ X-Frame-Options: {headers['x-frame-options']}")
                            else:
                                scan_results.append(f"  ✗ Missing X-Frame-Options")
                    except Exception as e:
                        scan_results.append(f"⚠️ HTTPS: {str(e)[:50]}")
                    
                    try:
                        import httpx
                        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                            r = await client.get(f"http://{target}")
                            scan_results.append(f"✅ HTTP: {r.status_code} | Server: {r.headers.get('server', 'unknown')}")
                    except Exception as e:
                        scan_results.append(f"⚠️ HTTP: {str(e)[:50]}")
                    
                    # Subdomain enumeration for pentest
                    if wants_pentest:
                        common_subs = ['www', 'mail', 'ftp', 'admin', 'api', 'dev', 'staging', 'test', 'blog', 'shop']
                        found_subs = []
                        for sub in common_subs:
                            try:
                                subdomain = f"{sub}.{target}"
                                socket.gethostbyname(subdomain)
                                found_subs.append(subdomain)
                            except: pass
                        if found_subs:
                            scan_results.append(f"✅ Subdomains found: {', '.join(found_subs[:10])}")
                    
                    scan_result = "\n".join(scan_results)
                    return {"text": scan_result, "agent": "security"}
                except Exception as e:
                    return {"text": f"❌ Scan error: {str(e)}", "agent": "security"}
            else:
                return {"text": "⚠️ Sila specify target domain (contoh: scan example.com)", "agent": "security"}

        # ── INTENT: task creation ──
        wants_task = bool(re.search(r'\b(task|tugas|buat.*task|create.*task|add.*task|assign.*task)\b', msg_lower))

        if wants_task:
            task_title = message.strip()
            for prefix in ["buat task", "create task", "add task", "task baru", "new task", "assign task"]:
                if task_title.lower().startswith(prefix):
                    task_title = task_title[len(prefix):].strip()
                    break
            if not task_title:
                task_title = message[:100]
            try:
                import hashlib
                from datetime import datetime
                task_id = f"T{hashlib.sha256(datetime.now().isoformat().encode()).hexdigest()[:8]}"
                planning = getattr(self, '_planning', None)
                if planning:
                    task = {
                        "id": task_id,
                        "title": task_title,
                        "description": f"Created from chat: {message[:200]}",
                        "phase": "General",
                        "status": "todo",
                        "complexity": "medium",
                    }
                    planning.tracker.save_tasks([task])
                    return {"text": f"✅ Task created: **{task_title}**\n📋 ID: {task_id}\n📊 Status: todo\n\nTask will appear in Dashboard → Task Board.", "agent": "kaihara"}
                else:
                    return {"text": "⚠️ Planning pipeline not initialized", "agent": "kaihara"}
            except Exception as e:
                return {"text": f"❌ Task error: {str(e)}", "agent": "kaihara"}

        # ── INTENT: system/agent queries ──
        wants_agent_info = bool(re.search(r'\b(agent|fleet|agent.*bawah|di bawah|tools.*ada|skills|capabiliti)\b', msg_lower))
        wants_channel_info = bool(re.search(r'\b(whatsapp|gmail|email|telegram|channel|saluran)\b', msg_lower))
        wants_system_info = bool(re.search(r'\b(server|dashboard|system|status|monitor|daemon|online|offline)\b', msg_lower))

        if wants_agent_info:
            # Answer about fleet agents from brain context
            agent_info = orchestrator_brain.get_fleet_summary()
            response = await self.model.complete(model=reflex_model, 
                system=system,
                messages=[{"role": "user", "content": f"{prompt}\n\n[AGENT DATA]\n{agent_info}"}]
            )
            return {"text": response, "agent": "kaihara"}

        if wants_channel_info:
            # Answer about communication channels
            channel_info = orchestrator_brain.get_channel_summary()
            response = await self.model.complete(model=reflex_model, 
                system=system,
                messages=[{"role": "user", "content": f"{prompt}\n\n[CHANNEL DATA]\n{channel_info}"}]
            )
            return {"text": response, "agent": "kaihara"}

        if wants_system_info:
            # Get live system status
            try:
                import httpx
                r = httpx.get("http://localhost:7000/api/monitor/servers", timeout=10)
                servers = r.json()
                sys_info = orchestrator_brain.get_system_summary()
                server_data = json.dumps(servers, indent=2, default=str)[:2000]
                response = await self.model.complete(model=reflex_model, 
                    system=system,
                    messages=[{"role": "user", "content": f"{prompt}\n\n[SYSTEM DATA]\n{sys_info}\n\n[LIVE SERVER STATUS]\n{server_data}"}]
                )
                return {"text": response, "agent": "kaihara"}
            except Exception:
                sys_info = orchestrator_brain.get_system_summary()
                response = await self.model.complete(model=reflex_model, 
                    system=system,
                    messages=[{"role": "user", "content": f"{prompt}\n\n[SYSTEM DATA]\n{sys_info}"}]
                )
                return {"text": response, "agent": "kaihara"}

        # ── DEFAULT: plain text response ──
        response = await self.model.complete(model=reflex_model, 
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        # Strip thinking process from model response
        try:
            from core.tools.notify_tools import _strip_thinking
            stripped = _strip_thinking(response)
            if stripped:
                response = stripped
        except: pass
        # Track last menu for context
        if "Langkah Seterusnya:" in response or "Pilih" in response:
            if hasattr(self, '_last_menu'):
                self._last_menu = response
        return {"text": response, "agent": "kaihara"}

    def _parse_md_to_blocks(self, md: str) -> list:
        """Parse markdown text into PDF content blocks."""
        blocks = []
        for line in md.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                blocks.append({"type": "heading", "text": stripped[2:], "level": 2})
            elif stripped.startswith("## "):
                blocks.append({"type": "heading", "text": stripped[3:], "level": 3})
            elif stripped.startswith("### "):
                blocks.append({"type": "heading", "text": stripped[4:], "level": 4})
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not blocks or blocks[-1].get("type") != "bullet":
                    blocks.append({"type": "bullet", "items": []})
                blocks[-1]["items"].append(stripped[2:])
            elif stripped.startswith("> "):
                blocks.append({"type": "highlight", "text": stripped[2:]})
            elif stripped.startswith("| ") and "---" not in stripped:
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if not blocks or blocks[-1].get("type") != "table":
                    blocks.append({"type": "table", "headers": cells, "rows": []})
                else:
                    blocks[-1]["rows"].append(cells)
            else:
                blocks.append({"type": "paragraph", "text": stripped})
        blocks = [b for b in blocks if not (b.get("type") == "table" and not b.get("rows"))]
        return blocks if blocks else [{"type": "paragraph", "text": md}]


    async def _execute_generate_and_send_pdf(self, args: dict) -> str:
        """Generate PDF from markdown and send to Telegram."""
        import os
        os.chdir("/opt/kaihara-os")
        from core.tools.pdf_generator import generate_pdf_report
        from core.tools.notify_tools import send_telegram_document
        from pathlib import Path

        title = args.get("title", "Report")
        content_md = args.get("content_md", "")

        # Parse markdown to content blocks
        blocks = []
        for line in content_md.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                blocks.append({"type": "heading", "text": stripped[2:], "level": 2})
            elif stripped.startswith("## "):
                blocks.append({"type": "heading", "text": stripped[3:], "level": 3})
            elif stripped.startswith("### "):
                blocks.append({"type": "heading", "text": stripped[4:], "level": 4})
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not blocks or blocks[-1].get("type") != "bullet":
                    blocks.append({"type": "bullet", "items": []})
                blocks[-1]["items"].append(stripped[2:])
            elif stripped.startswith("> "):
                blocks.append({"type": "highlight", "text": stripped[2:]})
            elif stripped.startswith("| ") and "---" not in stripped:
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if not blocks or blocks[-1].get("type") != "table":
                    blocks.append({"type": "table", "headers": cells, "rows": []})
                else:
                    blocks[-1]["rows"].append(cells)
            else:
                blocks.append({"type": "paragraph", "text": stripped})

        if not blocks:
            blocks = [{"type": "paragraph", "text": content_md}]

        # Clean empty tables
        blocks = [b for b in blocks if not (b.get("type") == "table" and not b.get("rows"))]

        pdf_path = generate_pdf_report(
            title=title,
            content=blocks,
            subtitle="Ghazwah Group — Kaihara OS",
            output_filename=f"report_{title[:30].lower().replace(' ', '_')}"
        )

        # Send to Telegram
        result = send_telegram_document(
            file_path=pdf_path,
            caption=f"📊 {title[:100]}"
        )

        if result.get("ok"):
            return f"✅ PDF dijana dan dihantar ke Telegram!\n📄 {pdf_path}"
        else:
            return f"⚠️ PDF dijana tapi gagal hantar: {result.get('error', 'unknown')}\n📄 {pdf_path}"

    async def _execute_send_telegram(self, args: dict) -> str:
        """Send text message to Telegram."""
        from core.tools.notify_tools import send_telegram_message
        message = args.get("message", "")
        result = send_telegram_message(message)
        if result.get("ok"):
            return f"✅ Mesej dihantar ke Telegram!"
        return f"⚠️ Gagal hantar: {result.get('error', 'unknown')}"

    async def _execute_generate_pdf(self, args: dict) -> str:
        """Generate PDF without sending."""
        import os
        os.chdir("/opt/kaihara-os")
        from core.tools.pdf_generator import generate_pdf_report
        title = args.get("title", "Report")
        content_md = args.get("content_md", "")
        blocks = [{"type": "paragraph", "text": content_md}]
        pdf_path = generate_pdf_report(title=title, content=blocks)
        return f"✅ PDF dijana: {pdf_path}"

    async def _execute_web_search(self, args: dict) -> str:
        """Web search."""
        from core.tools.web_tools import web_search
        query = args.get("query", "")
        result = web_search(query)
        if isinstance(result, dict):
            return json.dumps(result, indent=2, default=str)
        return str(result)

    async def _workflow(self, intent: dict) -> dict:
        """Workflow lane: trigger or propose automation."""
        from core.workflow.engine import WorkflowEngine
        from core.workflow.workflow_store import WorkflowStore
        from core.workflow.templates.biz_autopilot import create_biz_autopilot

        text = intent.get("text", "").lower()

        # Check if user wants to start a workflow
        workflow_keywords = ["cari kedai", "find business", "outreach",
                            "demo website", "auto workflow", "biz autopilot",
                            "cari perniagaan", "generate demo"]
        is_workflow_start = any(kw in text for kw in workflow_keywords)

        if is_workflow_start:
            # Extract parameters from text
            niche = "restoran"
            location = "Malaysia"
            channel = "email"

            # Simple extraction
            if "salon" in text or "kedai rambut" in text:
                niche = "salon"
            elif "kedai" in text or "shop" in text:
                niche = "kedai"
            elif "klinik" in text or "clinic" in text:
                niche = "klinik"
            elif "restoran" in text or "restaurant" in text or "makan" in text:
                niche = "restoran"

            if "johor" in text:
                location = "Johor Bahru"
            elif "kl" in text or "kuala lumpur" in text:
                location = "Kuala Lumpur"
            elif "penang" in text or "pulau pinang" in text:
                location = "Penang"
            elif "selangor" in text:
                location = "Selangor"

            if "whatsapp" in text or "wa" in text:
                channel = "whatsapp"
            elif "both" in text or "dua" in text:
                channel = "both"

            # Create and run workflow
            store = WorkflowStore()
            engine = WorkflowEngine(store=store, memory=self.memory)
            template = create_biz_autopilot(
                niche=niche,
                location=location,
                outreach_channel=channel,
            )
            engine.register_template(template)

            result = await engine.start(
                "biz_autopilot",
                input_data={
                    "niche": niche,
                    "location": location,
                    "outreach_channel": channel,
                }
            )

            return {
                "text": (
                    f"🚀 **Biz Autopilot Dimulakan!**\n\n"
                    f"**Niche:** {niche}\n"
                    f"**Lokasi:** {location}\n"
                    f"**Channel:** {channel}\n"
                    f"**ID:** `{result.get('workflow_id', 'N/A')}`\n"
                    f"**Langkah:** {result.get('total_steps', 8)} steps\n\n"
                    f"Workflow akan automatik:\n"
                    f"1. 🔍 Cari {niche} tanpa website di {location}\n"
                    f"2. 📊 Analisa perniagaan\n"
                    f"3. 🌐 Generate demo website\n"
                    f"4. 📧 Outreach via {channel}\n"
                    f"5. ✅ Convert lead kepada client\n"
                    f"6. 🏗️ Build website client\n"
                    f"7. 🚀 Deploy ke Vercel\n"
                    f"8. 💰 Buat invoice\n\n"
                    f"Cek status: `/api/workflow/{result.get('workflow_id', '')}`"
                ),
                "agent": "workflow",
                "intent": intent,
            }

        # Default: ask user what they want
        return {
            "text": (
                "🔧 **Workflow Engine Sedia!**\n\n"
                "Anda boleh:\n\n"
                "**1. Biz Autopilot** — Cari kedai tanpa website, buat demo, outreach:\n"
                "   `cari kedai makan di Johor Bahru`\n\n"
                "**2. Status Workflow** — Cek status workflow yang sedang jalan:\n"
                "   `status workflow [id]`\n\n"
                "**3. List Workflows** — Lihat semua workflows:\n"
                "   `list workflows`\n\n"
                "Contoh: `cari restoran tanpa website di KL, outreach email`"
            ),
            "agent": "workflow",
            "intent": intent,
        }

    def _kaihara_system_prompt(self) -> str:
        """Load Kaihara SOUL.md + orchestrator context as system prompt."""
        soul_path = self.config.get("soul_dir", "config/soul")
        import os
        path = os.path.join(soul_path, "kaihara.md")
        try:
            with open(path, encoding="utf-8") as f:
                soul = f.read()
        except FileNotFoundError:
            soul = ("You are Kaihara, a personal AI assistant. "
                    "Be concise, proactive, and action-oriented.")
        # Inject orchestrator context
        return soul + "\n\n" + orchestrator_brain.get_full_context()

    def _format_response(self, result: dict, route: str) -> str:
        if "text" in result:
            return result["text"]
        if "results" in result:
            parts = []
            for r in result["results"]:
                if isinstance(r, dict) and "result" in r:
                    inner = r["result"]
                    if isinstance(inner, dict) and "text" in inner:
                        parts.append(f"[{r.get('agent', '?')}] {inner['text']}")
                    else:
                        parts.append(f"[{r.get('agent', '?')}] {inner}")
            return "\n\n".join(parts) if parts else "Done."
        return str(result)

    def status(self) -> dict:
        return {
            "kaihara_online": True,
            "model": self.model.list_available() if self.model else [],
            "fleet_agents": list(self.fleet.AGENT_REGISTRY.keys()),
            "memory": self.memory is not None,
            "token_juice": self.token_juice is not None and self.token_juice.enabled,
        }
