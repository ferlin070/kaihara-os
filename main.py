"""
Kaihara OS — Entry Point

Usage:
    python main.py              # start server
    python main.py --chat       # CLI chat mode
    python main.py --status     # show status
"""

import sys
import os
import asyncio
import tomllib
from pathlib import Path

# Load .env file if exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.logging_config import setup_logging, get_logger

from core.brain.memory_tree import MemoryTree
from core.brain.token_juice import TokenJuice
from core.orchestrator.model_router import ModelRouter
from core.orchestrator.command_center import CommandCenter
from core.server.api import create_app
from agents.base_agent import BaseAgent

logger = get_logger("kaihara.main")


def load_config() -> dict:
    """Load config.toml."""
    config_path = ROOT / "config.toml"
    if not config_path.exists():
        logger.error("config.toml not found. Run from project root.")
        sys.exit(1)
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def init_kaihara() -> CommandCenter:
    """Initialize Kaihara OS core components."""
    config = load_config()

    # Add derived paths
    config["soul_dir"] = str(ROOT / "config" / "soul")
    config["skills_dir"] = str(ROOT / "config" / "skills")

    system_cfg = config.get("system", {})
    memory_cfg = config.get("memory", {})

    # Brain & Memory
    memory = MemoryTree(
        db_path=str(ROOT / memory_cfg.get("db_path", "./data/kaihara.db")),
        vault_path=str(ROOT / system_cfg.get("obsidian_vault", "./obsidian-vault")),
        config=memory_cfg,
    )

    # TokenJuice
    token_juice = TokenJuice(config.get("tokenjuice", {}))

    # Model Router
    model_router = ModelRouter(config)

    # Command Center
    cc = CommandCenter(
        config=config,
        memory=memory,
        model_router=model_router,
        token_juice=token_juice,
    )

    # Planning Pipeline
    from core.planning.pipeline import PlanningPipeline
    db_path = str(ROOT / memory_cfg.get("db_path", "./data/kaihara.db"))
    cc._planning = PlanningPipeline(
        model_router=model_router,
        memory=memory,
        token_juice=token_juice,
        db_path=db_path,
    )

    # Skill Registry
    from core.skills.registry import SkillRegistry
    from core.skills.skill_authoring import SkillAuthoring
    cc._skill_registry = SkillRegistry(
        skills_dir=str(ROOT / "config" / "skills")
    )
    cc._skill_authoring = SkillAuthoring(
        model_router=model_router,
        registry=cc._skill_registry,
    )
    # Connect skill registry to fleet manager for agent skill loading
    cc.fleet.skill_registry = cc._skill_registry

    # Voice Pipeline
    from core.voice.pipeline import VoicePipeline
    cc._voice = VoicePipeline(config, command_center=cc)

    # Security Components
    from core.security.approval_gate import ApprovalGate
    from core.security.sandbox import Sandbox
    from core.security.audit import AuditTrail
    from core.security.pentest.pipeline import PentestPipeline

    security_cfg = config.get("security", {})
    cc._approval_gate = ApprovalGate(security_cfg)
    cc._sandbox = Sandbox(security_cfg)
    audit_log_path = str(ROOT / security_cfg.get("audit_log", "./data/audit.log"))
    cc._audit = AuditTrail(audit_log_path)
    cc._pentest = PentestPipeline(
        sandbox=cc._sandbox,
        audit=cc._audit,
        approval_gate=cc._approval_gate,
        model_router=model_router,
    )

    # Channel Manager
    from core.channels.manager import ChannelManager
    cc._channel_manager = ChannelManager(config, command_center=cc)

    # Notification Service (multi-channel dispatch)
    from core.channels.notification_service import NotificationService
    cc._notification_service = NotificationService(
        cc._channel_manager,
        config.get("notification", {})
    )

    # OS Kernel
    from core.os.kernel import KernelManager
    cc._kernel = KernelManager(config, audit=cc._audit)

    # Daemon Manager (watchdog + auto-restart)
    from core.os.daemon_manager import DaemonManager
    cc._daemon_manager = DaemonManager(cc._kernel, config.get("daemon", {}))

    # Agent Map (visualization, ai-town style)
    from core.viz.agent_map import AgentMap
    cc._agent_map = AgentMap()
    cc.fleet.agent_map = cc._agent_map

    # Google Drive Integration
    from core.integrations.gdrive import GoogleDrive
    cc._gdrive = GoogleDrive(config.get("gdrive", {}))

    # Connect CostAgent to ModelRouter for usage tracking
    cost_agent = getattr(cc._kernel, "agents", {}).get("cost") \
        if hasattr(cc._kernel, "agents") else None
    if cost_agent:
        model_router._cost_agent = cost_agent

    # Register agents with proper SOUL.md files
    from agents.base_agent import GenericAgent

    def create_agent_class(agent_type: str, soul_file: str):
        """Factory to create agent class with proper type and soul."""
        class Agent(GenericAgent):
            AGENT_TYPE = agent_type
            SOUL_FILE = soul_file
        return Agent

    FleetManager = cc.fleet
    FleetManager.register("kaihara", create_agent_class("kaihara", "kaihara.md"))
    FleetManager.register("coding", create_agent_class("coding", "coding.md"))

    # Marketing Agent — specialized with real tools
    from agents.marketing_agent import MarketingAgent
    cc._marketing_agent = MarketingAgent(
        config={**config, "soul_dir": str(ROOT / "config" / "soul")},
        memory=memory,
        audit=cc._audit,
        skill_registry=cc._skill_registry,
    )
    FleetManager.register("marketing", MarketingAgent)

    # Security Agent — real tool capabilities, not generic
    from agents.security_agent import SecurityAgent
    cc._security_agent = SecurityAgent(
        config={**config, "soul_dir": str(ROOT / "config" / "soul")},
        memory=memory,
        model_router=model_router,
        token_juice=token_juice,
        approval_gate=cc._approval_gate,
        sandbox=cc._sandbox,
        audit=cc._audit,
        pentest=cc._pentest,
    )
    FleetManager.register("security", SecurityAgent)

    FleetManager.register("deploy", create_agent_class("deploy", "deploy.md"))
    FleetManager.register("research", create_agent_class("research", "research.md"))

    # Meta Agent (learns from all other agents)
    from agents.meta_agent import MetaAgent
    cc._meta_agent = MetaAgent(
        config={**config, "db_path": db_path,
                "soul_dir": str(ROOT / "config" / "soul")},
        memory=memory,
        model_router=model_router,
        token_juice=token_juice,
        approval_gate=cc._approval_gate,
    )
    FleetManager.register("meta", MetaAgent)

    return cc


async def cli_chat(cc: CommandCenter):
    """Interactive CLI chat with Kaihara."""
    import sys, io
    # Fix Windows Unicode encoding
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                       errors="replace")
    print("\n" + "=" * 50)
    print("  KAIHARA OS — Personal AI Super-Intelligence")
    print("=" * 50)
    print("  Type 'exit' to quit. Type 'status' for system status.\n")

    conv_id = "cli"
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Kaihara: Goodbye.")
            break
        if user_input.lower() == "status":
            status = cc.status()
            print(f"\nKaihara Status:")
            print(f"  Online: {status['kaihara_online']}")
            print(f"  Models: {', '.join(status['model'])}")
            print(f"  Agents: {', '.join(status['fleet_agents'])}")
            print(f"  Memory: {'active' if status['memory'] else 'inactive'}")
            print(f"  TokenJuice: {'on' if status['token_juice'] else 'off'}\n")
            continue

        result = await cc.handle_input(
            source="cli", message=user_input, conv_id=conv_id
        )
        print(f"\nKaihara: {result['response']}")
        print(f"  [route: {result['route']}]\n")


def run_server(cc: CommandCenter):
    """Start FastAPI server. Kernel + channels start via app startup event."""
    import uvicorn

    app = create_app(cc)
    host = cc.config.get("server", {}).get("host", "0.0.0.0")
    port = cc.config.get("server", {}).get("port", 7000)
    logger.info(f"Kaihara OS starting on http://{host}:{port}")
    logger.info(f"Dashboard: http://localhost:{port}")
    logger.info(f"API docs: http://localhost:{port}/docs")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    # Setup logging
    config = load_config()
    log_level = config.get("system", {}).get("log_level", "INFO")
    setup_logging(log_level)

    cc = init_kaihara()
    if "--chat" in sys.argv or "-c" in sys.argv:
        asyncio.run(cli_chat(cc))
    elif "--status" in sys.argv or "-s" in sys.argv:
        status = cc.status()
        logger.info("Kaihara OS Status:")
        for k, v in status.items():
            logger.info(f"  {k}: {v}")
    else:
        run_server(cc)


if __name__ == "__main__":
    main()
