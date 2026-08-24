"""
Command Center — entry point, intent parser, split brain, fleet manager.
The brain of Kaihara OS.
"""

import asyncio
import re
from typing import Any

from agents.base_agent import BaseAgent
from core.orchestrator.model_router import ModelRouter
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
        """Fast lane: simple questions answered directly."""
        system = self._kaihara_system_prompt()
        if context:
            system = f"{system}\n\n{context}"
        conv_history = ""
        if self.memory:
            history = self.memory.get_context(conv_id)
            if history:
                conv_history = "\n".join(
                    f"{m['role']}: {m['content']}" for m in history[-10:]
                )
        prompt = message
        if conv_history:
            prompt = f"Conversation history:\n{conv_history}\n\nUser: {message}"
        response = await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"text": response, "agent": "reflex"}

    async def _workflow(self, intent: dict) -> dict:
        """Workflow lane: trigger or propose automation."""
        return {
            "text": ("Workflow detected. I can set up an automation for this. "
                     "Shall I design the workflow?"),
            "agent": "workflow",
            "intent": intent,
        }

    def _kaihara_system_prompt(self) -> str:
        """Load Kaihara SOUL.md as system prompt."""
        soul_path = self.config.get("soul_dir", "config/soul")
        import os
        path = os.path.join(soul_path, "kaihara.md")
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ("You are Kaihara, a personal AI assistant. "
                    "Be concise, proactive, and action-oriented.")

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
