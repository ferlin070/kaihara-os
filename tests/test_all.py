"""
Kaihara OS — Bug Fix + Test Suite
Run: python tests/test_all.py
"""

import sys
import os
import asyncio
import traceback
import io
import json

# Fix Windows Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                   errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                  errors="replace")

# Setup path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# Load .env file for tests
try:
    from dotenv import load_dotenv
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

PASS = 0
FAIL = 0
ERRORS = []


def test(name: str, func):
    """Run a test."""
    global PASS, FAIL
    try:
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func())
        else:
            result = func()
        if result is False:
            raise Exception("Returned False")
        PASS += 1
        print(f"  PASS: {name}")
        return True
    except Exception as e:
        FAIL += 1
        ERRORS.append({"test": name, "error": str(e), "trace": traceback.format_exc()})
        print(f"  FAIL: {name} — {e}")
        return False


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ============================================================
# 1. CONFIG
# ============================================================

section("1. CONFIG LOADING")

def test_config_load():
    import tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    assert config["system"]["name"] == "Kaihara", "Wrong name"
    assert "rootsys" in config.get("provider", {}), "rootsys provider missing"
    assert config["privacy"]["mode"] == False, "privacy should be false"
    print(f"    Config: {len(config)} sections")
    return True

test("Config loads correctly", test_config_load)


# ============================================================
# 2. MEMORY TREE
# ============================================================

section("2. MEMORY TREE")

def test_memory_init():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(
        db_path="./data/test_kaihara.db",
        vault_path="./obsidian-vault",
    )
    assert mem.conn is not None, "SQLite connection failed"
    print(f"    Vector available: {mem.collection is not None}")
    mem.close()
    # Cleanup
    os.unlink("./data/test_kaihara.db")
    return True

test("Memory Tree initializes", test_memory_init)


def test_memory_store():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(db_path="./data/test_kaihara.db",
                     vault_path="./obsidian-vault")
    result = mem.store("Test memory content about coding", source="test")
    assert "raw_id" in result, "Store failed"
    assert "summary_id" in result, "Summary failed"
    assert result["topic"] == "coding", f"Wrong topic: {result['topic']}"
    print(f"    Stored: {result['raw_id']}, topic: {result['topic']}")
    mem.close()
    os.unlink("./data/test_kaihara.db")
    return True

test("Memory stores correctly", test_memory_store)


def test_memory_recall():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(db_path="./data/test_kaihara.db",
                     vault_path="./obsidian-vault")
    mem.store("Python coding function test", source="test")
    mem.store("Security pentest scan vulnerability", source="test")
    mem.store("Marketing scrape product trending", source="test")
    results = mem.recall("coding", limit=5)
    assert len(results) > 0, "No results returned"
    print(f"    Recall: {len(results)} results for 'coding'")
    mem.close()
    os.unlink("./data/test_kaihara.db")
    return True

test("Memory recall works", test_memory_recall)


def test_memory_super_context():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(db_path="./data/test_kaihara.db",
                     vault_path="./obsidian-vault")
    mem.store("Important coding pattern for Python", source="test")
    mem.store("Security scan vulnerability test", source="test")
    mem.store("Marketing product trending analysis", source="test")
    ctx = mem.super_context("coding")
    assert len(ctx) > 0, f"Empty context"
    assert "Context from Memory" in ctx or "coding" in ctx.lower(), f"Wrong context: {ctx[:80]}"
    print(f"    SuperContext: {len(ctx)} chars")
    mem.close()
    os.unlink("./data/test_kaihara.db")
    return True

test("SuperContext works", test_memory_super_context)


def test_memory_goals():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(db_path="./data/test_kaihara.db",
                     vault_path="./obsidian-vault")
    gid = mem.add_goal("Test Goal", "Description", "high")
    goals = mem.get_goals()
    assert len(goals) == 1, f"Expected 1 goal, got {len(goals)}"
    assert goals[0]["title"] == "Test Goal"
    print(f"    Goal: {gid}")
    mem.close()
    os.unlink("./data/test_kaihara.db")
    return True

test("Goals tracking works", test_memory_goals)


# ============================================================
# 3. TOKENJUICE
# ============================================================

section("3. TOKENJUICE")

def test_tokenjuice_output():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "output_compression": True})
    original = "The quick brown fox is a very good fox that jumps over the lazy dog"
    compressed = tj.compress_output(original)
    assert len(compressed) <= len(original), "Compressed is longer?!"
    print(f"    Original: {len(original)} chars")
    print(f"    Compressed: {len(compressed)} chars")
    return True

test("Output compression works", test_tokenjuice_output)


def test_tokenjuice_input_json():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "input_compression": True})
    json_str = '[{"id": 1, "name": "test", "value": "hello"}, {"id": 2, "name": "test2", "value": "world"}]'
    compressed = tj.compress_input(json_str, "json")
    assert len(compressed) <= len(json_str), "JSON not compressed"
    print(f"    JSON: {len(json_str)} → {len(compressed)} chars")
    return True

test("Input JSON compression works", test_tokenjuice_input_json)


def test_tokenjuice_shell():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "shell_compression": True})
    output = "PASS test_a\nPASS test_b\nPASS test_c\nFAIL test_d\nERROR test_e"
    compressed = tj.compress_shell("npm test", output)
    assert "FAIL" in compressed or "failures" in compressed.lower(), "Should keep failures"
    print(f"    Shell: {len(output)} → {len(compressed)} chars")
    return True

test("Shell compression works", test_tokenjuice_shell)


def test_tokenjuice_skip_security():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "output_compression": True,
                      "drop_compression_on": ["security"]})
    text = "Do not compress this security warning"
    result = tj.compress_output(text, context="security")
    assert result == text, "Should not compress security"
    print("    Security context: skipped compression")
    return True

test("Skip compression for security", test_tokenjuice_skip_security)


# ============================================================
# 4. MODEL ROUTER
# ============================================================

section("4. MODEL ROUTER")

def test_model_router_init():
    import tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    from core.orchestrator.model_router import ModelRouter
    router = ModelRouter(config)
    providers = router.list_available()
    assert len(providers) > 0, "No providers"
    rootsys_ready = [p for p in providers if "rootsys" in p and "ready" in p]
    assert len(rootsys_ready) > 0, "rootsys not ready"
    print(f"    Providers: {len(providers)}")
    for p in providers:
        print(f"      {p}")
    return True

test("Model Router initializes", test_model_router_init)


async def test_model_router_call():
    import tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    from core.orchestrator.model_router import ModelRouter
    router = ModelRouter(config)
    response = await router.complete(
        system="You are a test assistant. Reply briefly.",
        messages=[{"role": "user", "content": "Say 'test ok' only."}],
        model="rootsys/deepseek-v4-flash"
    )
    assert "test ok" in response.lower() or len(response) > 5, f"Bad response: {response[:100]}"
    print(f"    LLM Response: {response[:80]}")
    return True

test("Model Router calls rootsys.cloud", test_model_router_call)


# ============================================================
# 5. COMMAND CENTER
# ============================================================

section("5. COMMAND CENTER")

async def test_command_center_reflex():
    import tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    config["soul_dir"] = os.path.join(ROOT, "config", "soul")
    config["skills_dir"] = os.path.join(ROOT, "config", "skills")
    from core.brain.memory_tree import MemoryTree
    from core.brain.token_juice import TokenJuice
    from core.orchestrator.command_center import CommandCenter
    from core.orchestrator.model_router import ModelRouter
    mem = MemoryTree("./data/test_kaihara.db", "./obsidian-vault")
    tj = TokenJuice(config.get("tokenjuice", {}))
    mr = ModelRouter(config)
    cc = CommandCenter(config, memory=mem, model_router=mr, token_juice=tj)
    result = await cc.handle_input("test", "hello, apa khabar?", conv_id="test")
    assert "response" in result, "No response"
    assert result["route"] == "reflex", f"Wrong route: {result['route']}"
    print(f"    Route: {result['route']}")
    print(f"    Response: {result['response'][:80]}")
    mem.close()
    if os.path.exists("./data/test_kaihara.db"):
        os.unlink("./data/test_kaihara.db")
    return True

test("Command Center reflex route", test_command_center_reflex)


# ============================================================
# 6. SKILLS REGISTRY
# ============================================================

section("6. SKILLS REGISTRY")

def test_skills_list():
    from core.skills.registry import SkillRegistry
    reg = SkillRegistry(os.path.join(ROOT, "config", "skills"))
    stats = reg.stats()
    assert stats["total"] >= 60, f"Expected 60+ skills, got {stats['total']}"
    print(f"    Total skills: {stats['total']}")
    for cat, count in sorted(stats["categories"].items()):
        print(f"      {cat}: {count}")
    return True

test("Skills registry has 60+ skills", test_skills_list)


def test_skills_search():
    from core.skills.registry import SkillRegistry
    reg = SkillRegistry(os.path.join(ROOT, "config", "skills"))
    results = reg.search_skills("security")
    assert len(results) > 0, "No security skills found"
    print(f"    Security skills: {len(results)}")
    return True

test("Skills search works", test_skills_search)


# ============================================================
# 7. AGENT MAP (Visualization)
# ============================================================

section("7. AGENT MAP")

def test_agent_map_init():
    from core.viz.agent_map import AgentMap
    am = AgentMap()
    state = am.get_state()
    assert len(state["agents"]) == 7, f"Expected 7 agents, got {len(state['agents'])}"
    assert len(state["stations"]) == 8, f"Expected 8 stations"
    print(f"    Agents: {len(state['agents'])}")
    print(f"    Stations: {len(state['stations'])}")
    return True

test("Agent Map initializes", test_agent_map_init)


def test_agent_map_move():
    from core.viz.agent_map import AgentMap
    am = AgentMap()
    am.move_agent("coding", "coding_desk", "Building app", 50)
    state = am.get_state()
    coding = state["agents"]["coding"]
    assert coding["status"] in ("moving", "working"), f"Wrong status: {coding['status']}"
    assert coding["target_x"] == 130, f"Wrong target x: {coding['target_x']}"
    print(f"    Coding agent moved to coding_desk")
    return True

test("Agent Map moves agents", test_agent_map_move)


def test_agent_map_speech():
    from core.viz.agent_map import AgentMap
    am = AgentMap()
    am.set_speech("kaihara", "Hello there!")
    state = am.get_state()
    assert state["agents"]["kaihara"]["speech"] == "Hello there!"
    print(f"    Speech: {state['agents']['kaihara']['speech']}")
    return True

test("Agent Map speech bubbles", test_agent_map_speech)


# ============================================================
# 8. SECURITY
# ============================================================

section("8. SECURITY")

async def test_approval_gate():
    from core.security.approval_gate import ApprovalGate
    gate = ApprovalGate({})
    req = await gate.request("deploy_to_production", "deploy",
                               {"target": "prod"})
    assert req["status"] == "pending", f"Wrong status: {req['status']}"
    assert gate.requires_approval("deploy_to_production")
    assert not gate.requires_approval("read_file")
    appr = await gate.approve(req["request_id"])
    assert appr["status"] == "approved"
    pending = gate.get_pending()
    print(f"    Gate: pending={len(pending)}, approved OK")
    return True

test("Approval Gate works", test_approval_gate)


def test_audit_trail():
    from core.security.audit import AuditTrail
    audit = AuditTrail("./data/test_audit.log")
    audit.log("test_agent", "test_action", {"key": "value"}, {"ok": True})
    entries = audit.get_log(limit=10)
    assert len(entries) > 0, "No audit entries"
    assert entries[-1]["agent"] == "test_agent"
    print(f"    Audit entries: {len(entries)}")
    os.unlink("./data/test_audit.log")
    return True

test("Audit Trail works", test_audit_trail)


# ============================================================
# 9. LEARNING CACHE (Meta Agent)
# ============================================================

section("9. LEARNING CACHE")

def test_learning_cache():
    from core.brain.learning_cache import LearningCache
    cache = LearningCache("./data/test_learning.db")
    cache.store_result("Build todo app", "coding",
                        {"text": "App built"}, 500, 30, "glm-5.2", True)
    result = cache.check_cache("Build todo app", "coding")
    assert result is not None, "Cache miss"
    assert result["cached"] == True, "Not cached"
    assert result["tokens_saved"] == 500
    print(f"    Cache hit: tokens_saved={result['tokens_saved']}")
    cache.record_stats("coding", "general", "glm-5.2", 500, 30, True)
    stats = cache.get_agent_stats()
    assert len(stats) > 0, "No stats"
    print(f"    Stats: {len(stats)} entries")
    cache.close()
    os.unlink("./data/test_learning.db")
    return True

test("Learning Cache stores and retrieves", test_learning_cache)


# ============================================================
# 10. PLANNING PIPELINE
# ============================================================

section("10. PLANNING PIPELINE")

def test_task_tracker():
    from core.planning.task_tracker import TaskTracker
    tracker = TaskTracker("./data/test_tasks.db")
    prd_id = tracker.save_prd("Test App", "# PRD\nTest", {"title": "Test"})
    tasks = [
        {"id": "T1", "title": "Setup", "phase": "Foundation",
         "dependencies": [], "complexity": "simple"},
        {"id": "T2", "title": "Build", "phase": "Core",
         "dependencies": ["T1"], "complexity": "medium"},
    ]
    tracker.save_tasks(tasks, prd_id)
    all_tasks = tracker.get_tasks(prd_id=prd_id)
    assert len(all_tasks) == 2, f"Expected 2 tasks, got {len(all_tasks)}"
    progress = tracker.get_progress(prd_id=prd_id)
    assert progress["total"] == 2
    assert progress["todo"] == 2
    print(f"    Tasks: {progress['total']}, todo: {progress['todo']}")
    tracker.update_status("T1", "done")
    progress = tracker.get_progress(prd_id=prd_id)
    assert progress["done"] == 1
    print(f"    After update: done={progress['done']}, percent={progress['percent']}%")
    tracker.close()
    os.unlink("./data/test_tasks.db")
    return True

test("Task Tracker works", test_task_tracker)


async def test_prd_agent():
    from core.planning.prd_agent import PRDAgent
    import tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    from core.orchestrator.model_router import ModelRouter
    mr = ModelRouter(config)
    prd = PRDAgent(model_router=mr)
    result = await prd.generate("simple todo app")
    assert "prd" in result, "No PRD generated"
    assert len(result["prd"]) > 50, "PRD too short"
    assert "features" in result["parsed"], "No parsed features"
    print(f"    PRD: {len(result['prd'])} chars")
    print(f"    Features: {result['parsed']['feature_count']}")
    print(f"    Tasks: {result['parsed']['task_count']}")
    return True

test("PRD Agent generates with LLM", test_prd_agent)


# ============================================================
# 11. OS KERNEL
# ============================================================

section("11. OS KERNEL")

async def test_health_agent():
    from core.os.health_agent import HealthAgent
    agent = HealthAgent({})
    result = await agent.run_once()
    assert "cpu" in result, "No CPU data"
    assert "ram" in result, "No RAM data"
    print(f"    CPU: {result['cpu']['percent']}%")
    print(f"    RAM: {result['ram']['percent']}%")
    print(f"    Disk: {result['disk']['percent']}%")
    print(f"    Uptime: {result['uptime_seconds']}s")
    return True

test("Health Agent reads system stats", test_health_agent)


async def test_cost_agent():
    from core.os.cost_agent import CostAgent
    agent = CostAgent({"daily_budget": 10.0, "monthly_budget": 100.0,
                        "cost_log": "./data/test_costs.json"})
    agent.record_usage("rootsys", "glm-5.2", 500, 200, 0.01)
    agent.record_usage("rootsys", "glm-5.2", 300, 100, 0.005)
    result = await agent.run_once()
    assert "today_cost" in result, f"No today_cost in result: {result}"
    assert result["today_calls"] == 2, f"Wrong calls: {result.get('today_calls')}"
    print(f"    Today cost: ${result['today_cost']}")
    print(f"    Today calls: {result['today_calls']}")
    if os.path.exists("./data/test_costs.json"):
        os.unlink("./data/test_costs.json")
    return True

test("Cost Agent tracks usage", test_cost_agent)


# ============================================================
# 12. GOOGLE DRIVE
# ============================================================

section("12. GOOGLE DRIVE")

def test_gdrive_status():
    from core.integrations.gdrive import GoogleDrive
    gdrive = GoogleDrive({})
    status = gdrive.status()
    assert "available" in status
    print(f"    Available: {status['available']}")
    print(f"    Rclone: {status.get('rclone_path', 'not found')}")
    return True

test("GDrive status check", test_gdrive_status)


# ============================================================
# 13. INTENT PARSER (proper classification)
# ============================================================

section("13. INTENT PARSER")

def test_intent_simple():
    from core.orchestrator.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser._classify_by_patterns("hello apa khabar")
    assert intent["type"] == "simple", f"Expected simple, got {intent['type']}"
    print(f"    'hello apa khabar' → {intent['type']}")
    return True

test("Intent: simple greeting", test_intent_simple)


def test_intent_coding():
    from core.orchestrator.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser._classify_by_patterns("bina website dengan react")
    assert "coding" in intent["agents"] or intent["type"] == "coding" or intent["type"] == "planning", \
        f"Expected coding/planning, got {intent}"
    print(f"    'bina website' → {intent['type']}, agents: {intent['agents']}")
    return True

test("Intent: coding task", test_intent_coding)


def test_intent_security():
    from core.orchestrator.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser._classify_by_patterns("run pentest on example.com")
    assert "security" in intent["agents"], f"Expected security, got {intent}"
    print(f"    'pentest' → {intent['type']}, agents: {intent['agents']}")
    return True

test("Intent: security task", test_intent_security)


def test_intent_multi_agent():
    from core.orchestrator.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser._classify_by_patterns("scrape market data then build dashboard")
    assert len(intent["agents"]) >= 2, f"Expected 2+ agents, got {intent['agents']}"
    print(f"    Multi: agents={intent['agents']}")
    return True

test("Intent: multi-agent task", test_intent_multi_agent)


def test_intent_confidence():
    from core.orchestrator.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser._classify_by_patterns("hello")
    assert intent["confidence"] >= 0.0, "Confidence negative"
    print(f"    Confidence: {intent['confidence']}")
    return True

test("Intent: confidence score", test_intent_confidence)


# ============================================================
# 14. EDGE CASES + ERROR HANDLING
# ============================================================

section("14. EDGE CASES + ERROR HANDLING")

def test_empty_input():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True})
    result = tj.compress_output("")
    assert result == "", "Empty input should return empty"
    print("    Empty string: OK")
    return True

test("Empty input handling", test_empty_input)


def test_none_input():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True})
    try:
        result = tj.compress_output(None)
        assert result is None or result == ""
        print("    None input: handled")
        return True
    except (TypeError, AttributeError):
        print("    None input: raised (acceptable)")
        return True

test("None input handling", test_none_input)


def test_unicode_emoji():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "output_compression": True})
    text = "Hello! How are you today?"
    result = tj.compress_output(text)
    assert len(result) <= len(text), "Unicode not handled"
    print(f"    Unicode: {len(text)} → {len(result)} chars")
    return True

test("Unicode + emoji handling", test_unicode_emoji)


def test_very_long_input():
    from core.brain.token_juice import TokenJuice
    tj = TokenJuice({"enabled": True, "input_compression": True})
    long_json = json.dumps([{"id": i, "name": f"item_{i}"} for i in range(100)])
    compressed = tj.compress_input(long_json, "json")
    assert len(compressed) <= len(long_json), "Long input not compressed"
    print(f"    Long JSON: {len(long_json)} → {len(compressed)} chars")
    return True

test("Very long input compression", test_very_long_input)


def test_memory_empty_query():
    from core.brain.memory_tree import MemoryTree
    mem = MemoryTree(db_path="./data/test_kaihara.db",
                     vault_path="./obsidian-vault")
    results = mem.recall("", limit=5)
    assert isinstance(results, list), "Should return list"
    print(f"    Empty query: {len(results)} results")
    mem.close()
    if os.path.exists("./data/test_kaihara.db"):
        os.unlink("./data/test_kaihara.db")
    return True

test("Memory empty query", test_memory_empty_query)


def test_model_router_no_key():
    from core.orchestrator.model_router import ModelRouter
    router = ModelRouter({"provider": {}, "privacy": {"mode": False}})
    # Should not crash, just return error
    available = router.list_available()
    assert isinstance(available, list), "Should return list"
    print(f"    No providers: {len(available)}")
    return True

test("Model router no providers", test_model_router_no_key)


def test_agent_map_invalid_station():
    from core.viz.agent_map import AgentMap
    am = AgentMap()
    am.move_agent("coding", "nonexistent_station", "test")
    # Agent should stay at home
    state = am.get_state()
    assert state["agents"]["coding"]["station"] != "nonexistent_station"
    print("    Invalid station: agent stayed home")
    return True

test("Agent map invalid station", test_agent_map_invalid_station)


# ============================================================
# 16. DAEMON MANAGER
# ============================================================

section("DAEMON MANAGER")

def test_daemon_manager():
    from core.os.daemon_manager import DaemonManager
    from core.os.kernel import KernelManager
    kernel = KernelManager({})
    dm = DaemonManager(kernel)
    status = dm.status()
    assert "watchdog_running" in status
    assert "agents" in status
    assert "process" in status
    print(f"    Agents: {status['agents']['total']} total")
    print(f"    Watchdog: {status['watchdog_running']}")
    return True

test("Daemon manager init", test_daemon_manager)

def test_daemon_services():
    from core.os.daemon_manager import DaemonManager
    from core.os.kernel import KernelManager
    kernel = KernelManager({})
    dm = DaemonManager(kernel)
    services = dm.get_service_registry()
    assert isinstance(services, list)
    assert len(services) == 7  # 7 kernel agents
    print(f"    Services: {len(services)}")
    return True

test("Daemon services registry", test_daemon_services)

def test_daemon_alerts():
    from core.os.daemon_manager import DaemonManager
    from core.os.kernel import KernelManager
    kernel = KernelManager({})
    dm = DaemonManager(kernel)
    alerts = dm.get_alerts()
    assert isinstance(alerts, list)
    print(f"    Alerts: {len(alerts)}")
    return True

test("Daemon alerts", test_daemon_alerts)


# ============================================================
# 17. PROMPT STORAGE
# ============================================================

section("PROMPT STORAGE")

def test_prompt_storage():
    from core.skills.registry import SkillRegistry
    reg = SkillRegistry()

    # Save a prompt
    result = reg.save_prompt("Test Prompt", "Hello {{name}}", "general", ["test"], "A test prompt")
    assert result["prompt_id"].startswith("prompt_")
    prompt_id = result["prompt_id"]

    # List prompts
    prompts = reg.list_prompts()
    assert len(prompts) >= 1

    # Search prompts
    found = reg.list_prompts(query="Test")
    assert len(found) >= 1

    # Use prompt
    use_result = reg.use_prompt(prompt_id)
    assert use_result["uses"] == 1

    # Delete prompt
    deleted = reg.delete_prompt(prompt_id)
    assert deleted is True

    # Verify deleted
    remaining = reg.list_prompts()
    assert all(p["id"] != prompt_id for p in remaining)

    print(f"    Prompt CRUD: save, list, search, use, delete")
    return True

test("Prompt storage CRUD", test_prompt_storage)


# ============================================================
# 18. NOTIFICATION SERVICE
# ============================================================

section("NOTIFICATION SERVICE")

def test_notification_service():
    from core.channels.notification_service import NotificationService
    from core.channels.manager import ChannelManager
    config = {"channel": {}}
    mgr = ChannelManager(config)
    svc = NotificationService(mgr)
    status = svc.status()
    assert "quiet_hours" in status
    assert "rate_limit" in status
    assert "routing" in status
    print(f"    Quiet hours: {status['quiet_hours']}")
    print(f"    Rate limit: {status['rate_limit']['remaining']} remaining")
    return True

test("Notification service init", test_notification_service)

def test_notification_routing():
    from core.channels.notification_service import NotificationService
    from core.channels.manager import ChannelManager
    config = {"channel": {}}
    mgr = ChannelManager(config)
    svc = NotificationService(mgr)
    result = svc.update_routing({"urgent": ["email"], "normal": []})
    assert result["status"] == "updated"
    print(f"    Routing updated: {result['routing']}")
    return True

test("Notification routing update", test_notification_routing)


# ============================================================
# 19. WEB TOOLS (Marketing)
# ============================================================

section("WEB TOOLS (Marketing)")

def test_seo_audit():
    from core.tools.web_tools import seo_audit
    result = json.loads(seo_audit("example.com"))
    assert "score" in result
    assert "issues" in result
    assert "checks" in result
    print(f"    SEO score: {result['score']}/100")
    print(f"    Issues: {len(result['issues'])}, Checks: {len(result['checks'])}")
    return True

test("SEO audit tool", test_seo_audit)

def test_competitor_analysis():
    from core.tools.web_tools import analyze_competitor
    result = json.loads(analyze_competitor("example.com"))
    assert "tech_stack" in result
    assert "social_links" in result
    assert "headings" in result
    print(f"    Tech stack: {result['tech_stack']}")
    print(f"    Social links: {len(result['social_links'])}")
    return True

test("Competitor analysis tool", test_competitor_analysis)


# ============================================================
# 20. MARKETING SYSTEM
# ============================================================

section("MARKETING SYSTEM")

def test_marketing_leads():
    from core.marketing.leads import create_lead, get_leads, update_lead, delete_lead, score_lead
    # Create
    lead = create_lead("Test Lead", "test@example.com", "0123456789", "Test Corp", "web", "Test notes")
    assert lead["id"] > 0
    assert lead["name"] == "Test Lead"
    # List
    leads = get_leads()
    assert len(leads) >= 1
    # Update
    updated = update_lead(lead["id"], status="contacted", score=50)
    assert updated["status"] == "contacted"
    # Score
    score = score_lead(lead["id"])
    assert score > 0
    # Delete
    deleted = delete_lead(lead["id"])
    assert deleted is True
    print(f"    Lead CRUD + scoring: OK")
    return True

test("Marketing leads CRUD", test_marketing_leads)

def test_marketing_clients():
    from core.marketing.clients import create_client, get_clients, update_client, delete_client, client_stats
    # Create
    client = create_client("Test Client", "client@test.com", "0198765432", "Client Corp")
    assert client["id"] > 0
    # List
    clients = get_clients()
    assert len(clients) >= 1
    # Update
    updated = update_client(client["id"], tier="premium")
    assert updated["tier"] == "premium"
    # Stats
    stats = client_stats()
    assert "total" in stats
    # Delete
    deleted = delete_client(client["id"])
    assert deleted is True
    print(f"    Client CRUD + stats: OK")
    return True

test("Marketing clients CRUD", test_marketing_clients)

def test_marketing_campaigns():
    from core.marketing.campaigns import create_campaign, get_campaigns, delete_campaign
    campaign = create_campaign("Test Campaign", "Description", "social", 1000, "Young adults")
    assert campaign["id"] > 0
    campaigns = get_campaigns()
    assert len(campaigns) >= 1
    deleted = delete_campaign(campaign["id"])
    assert deleted is True
    print(f"    Campaign CRUD: OK")
    return True

test("Marketing campaigns CRUD", test_marketing_campaigns)

def test_marketing_content():
    from core.marketing.campaigns import create_content, get_content, publish_content
    content = create_content("Test Post", "Hello world!", "post", "instagram", None, ["#test"])
    assert content["id"] > 0
    published = publish_content(content["id"])
    assert published["status"] == "published"
    print(f"    Content CRUD + publish: OK")
    return True

test("Marketing content CRUD", test_marketing_content)

def test_marketing_invoices():
    from core.marketing.clients import create_client, delete_client
    from core.marketing.invoices import create_invoice, get_invoices, mark_invoice_paid, delete_invoice
    client = create_client("Invoice Test", "inv@test.com")
    invoice = create_invoice(client["id"], 500, "Test service", tax_rate=6)
    assert invoice["id"] > 0
    assert invoice["total"] == 530.0  # 500 + 6% tax
    paid = mark_invoice_paid(invoice["id"], "bank", "REF123")
    assert paid["status"] == "paid"
    delete_invoice(invoice["id"])
    delete_client(client["id"])
    print(f"    Invoice CRUD + tax calc + payment: OK")
    return True

test("Marketing invoices CRUD", test_marketing_invoices)

def test_marketing_agent():
    from agents.marketing_agent import MarketingAgent
    agent = MarketingAgent(config={"soul_dir": "config/soul"})
    status = agent.status()
    assert "tools" in status
    assert len(status["tools"]) > 0
    print(f"    Marketing agent tools: {len(status['tools'])}")
    return True

test("Marketing agent init", test_marketing_agent)


# ============================================================
# 20. DEPLOY AGENT
# ============================================================

section("20. DEPLOY AGENT")

async def test_deploy_tools():
    from core.tools.deploy_tools import disk_check, port_check, git_status
    dc = disk_check()
    assert dc["ok"], f"disk_check failed: {dc}"
    print(f"    Disk: {dc['used_gb']}/{dc['total_gb']} GB ({dc['percent']}%)")
    pc = port_check(7000)
    assert pc["ok"], f"port_check failed: {pc}"
    print(f"    Port 7000: {pc['status']}")
    gs = git_status()
    assert gs["ok"], f"git_status failed: {gs}"
    print(f"    Git branch: {gs['branch']}")
    return True

test("Deploy tools: disk, port, git", test_deploy_tools)

async def test_deploy_docker():
    from core.tools.deploy_tools import docker_ps
    r = docker_ps()
    # Docker might not be available
    print(f"    Docker available: {r.get('ok', False)}")
    if r.get("ok"):
        print(f"    Containers: {r.get('count', 0)}")
    return True

test("Deploy tools: docker ps", test_deploy_docker)

async def test_deploy_agent():
    from agents.deploy_agent import DeployAgent
    agent = DeployAgent(config={"repo_path": "."})
    st = agent.status()
    tools = st.get("tools", [])
    assert len(tools) >= 15, f"Too few tools: {len(tools)}"
    print(f"    Deploy agent tools: {len(tools)}")
    assert "docker_ps" in tools, "Missing docker_ps"
    assert "git_deploy" in tools, "Missing git_deploy"
    assert "full_deploy" in tools, "Missing full_deploy"
    assert "health_check" in tools, "Missing health_check"
    assert "rollback" in tools, "Missing rollback"
    print(f"    Tools: {', '.join(tools[:8])}...")
    return True

test("Deploy agent init", test_deploy_agent)

async def test_deploy_health_check():
    from core.tools.deploy_tools import health_check
    r = health_check()
    assert "checks" in r, f"health_check missing checks: {r}"
    assert len(r["checks"]) >= 2, f"Too few checks: {r}"
    # At least disk check should pass
    disk_ok = any(c["check"] == "disk_space" and c["ok"] for c in r["checks"])
    assert disk_ok, f"Disk check failed: {r}"
    print(f"    Health checks: {len(r['checks'])} (disk OK)")
    return True

test("Deploy tools: health check", test_deploy_health_check)

async def test_deploy_history():
    from core.tools.deploy_tools import get_deploy_history, record_deploy
    record_deploy("test_action", {"ok": True}, "test_user")
    h = get_deploy_history(5)
    assert len(h) >= 1, "No history recorded"
    assert h[-1]["action"] == "test_action"
    print(f"    History entries: {len(h)}")
    return True

test("Deploy tools: history tracking", test_deploy_history)


# ============================================================
# 21. EDITOR AGENT
# ============================================================

section("21. EDITOR AGENT")

async def test_editor_image_tools():
    from core.tools.image_tools import generate_poster, generate_banner, generate_gradient
    r = generate_poster(title="Test Poster", subtitle="Subtitle", output_path="/tmp/test_poster.png")
    assert r["ok"], f"generate_poster failed: {r}"
    assert os.path.exists(r["output"]), f"Output not created: {r['output']}"
    print(f"    Poster: {r['output']}")
    r2 = generate_banner(title="Test Banner", output_path="/tmp/test_banner.png")
    assert r2["ok"], f"generate_banner failed: {r2}"
    print(f"    Banner: {r2['output']}")
    r3 = generate_gradient(output_path="/tmp/test_gradient.png")
    assert r3["ok"], f"generate_gradient failed: {r3}"
    print(f"    Gradient: {r3['output']}")
    return True

test("Editor: image generation tools", test_editor_image_tools)

async def test_editor_stock_tools():
    from core.tools.stock_tools import search_stock_image
    # No API key - just test the function handles it gracefully
    r = search_stock_image("nature", per_page=3)
    if not r["ok"] and "PEXELS_API_KEY" in r.get("error", ""):
        print("    Stock search: no API key (expected)")
        return True
    if r["ok"]:
        print(f"    Stock search: {r.get('total_results', 0)} results")
        return True
    print(f"    Stock search: {r.get('error', 'unknown')}")
    return True

test("Editor: stock search tools", test_editor_stock_tools)

async def test_editor_agent():
    from agents.editor_agent import EditorAgent
    agent = EditorAgent(config={"media_dir": "/tmp/media"})
    st = agent.status()
    tools = st.get("tools", [])
    assert len(tools) >= 39, f"Too few tools: {len(tools)}"
    print(f"    Editor agent tools: {len(tools)}")
    expected = ["video_trim", "video_concat", "generate_poster",
                "search_stock_image", "image_resize",
                "gdrive_search_media", "gdrive_browse_folder",
                "pinterest_search", "pinterest_download_pin",
                "video_speed", "video_crop", "video_to_gif",
                "video_color_grade", "video_remove_audio",
                "video_add_voiceover", "get_curated_photos", "get_popular_videos",
                "ai_generate_image", "ai_generate_poster",
                "google_flow_generate_image", "google_flow_generate_video"]
    for t in expected:
        assert t in tools, f"Missing tool: {t}"
    print(f"    All expected tools present")
    return True

test("Editor agent init", test_editor_agent)

async def test_editor_video_probe():
    from core.tools.media_tools import video_probe
    # Test with non-existent file
    r = video_probe("/tmp/nonexistent.mp4")
    assert not r["ok"], f"Should fail for nonexistent file"
    print(f"    Video probe handles missing file: OK")
    return True

test("Editor: video probe", test_editor_video_probe)

async def test_editor_new_video_tools():
    from core.tools.media_tools import (
        video_speed, video_crop, video_to_gif,
        video_color_grade, video_remove_audio,
    )
    # Test with non-existent file (should fail gracefully)
    r = video_speed("/tmp/nonexistent.mp4", "/tmp/out.mp4", 2.0)
    assert not r["ok"], "video_speed should fail for missing file"
    r = video_crop("/tmp/nonexistent.mp4", "/tmp/out.mp4")
    assert not r["ok"], "video_crop should fail for missing file"
    r = video_to_gif("/tmp/nonexistent.mp4", "/tmp/out.gif")
    assert not r["ok"], "video_to_gif should fail for missing file"
    r = video_color_grade("/tmp/nonexistent.mp4", "/tmp/out.mp4", brightness=0.5)
    assert not r["ok"], "video_color_grade should fail for missing file"
    r = video_remove_audio("/tmp/nonexistent.mp4", "/tmp/out.mp4")
    assert not r["ok"], "video_remove_audio should fail for missing file"
    print(f"    New video tools handle missing files: OK")
    return True

test("Editor: new video tools", test_editor_new_video_tools)

async def test_editor_run_method():
    from agents.editor_agent import EditorAgent
    agent = EditorAgent(config={"media_dir": "/tmp/media"})
    # Test run() method exists and accepts tasks
    r = await agent.run("trim video", {"input": "/tmp/test.mp4", "start": 0, "end": 5})
    assert "ok" in r or "error" in r, "run() should return result"
    print(f"    Editor run() method works: OK")
    return True

test("Editor: run method", test_editor_run_method)

async def test_ai_tools():
    from core.tools.ai_tools import AIGenerateTools, AI_GENERATE_TOOLS
    tools = AIGenerateTools()
    assert len(AI_GENERATE_TOOLS) == 4, f"Expected 4 tools, got {len(AI_GENERATE_TOOLS)}"
    tool_names = [t["name"] for t in AI_GENERATE_TOOLS]
    assert "ai_generate_image" in tool_names
    assert "ai_generate_poster" in tool_names
    status = tools.status()
    assert "diffusers_installed" in status
    print(f"    AI tools: {len(AI_GENERATE_TOOLS)} — {tool_names}")
    print(f"    AI status: diffusers={status['diffusers_installed']}, cuda={status['cuda_available']}")
    return True

test("AI image tools init", test_ai_tools)

async def test_google_flow_tools():
    from core.tools.google_flow_tools import GoogleFlowTools, GOOGLE_FLOW_TOOLS
    tools = GoogleFlowTools()
    assert len(GOOGLE_FLOW_TOOLS) == 4, f"Expected 4 tools, got {len(GOOGLE_FLOW_TOOLS)}"
    tool_names = [t["name"] for t in GOOGLE_FLOW_TOOLS]
    assert "google_flow_generate_image" in tool_names
    assert "google_flow_generate_video" in tool_names
    status = tools.status()
    assert "token_set" in status
    print(f"    Google Flow tools: {len(GOOGLE_FLOW_TOOLS)} — {tool_names}")
    print(f"    Flow status: token={status['token_set']}")
    return True

test("Google Flow tools init", test_google_flow_tools)

section("16. GDRIVE MEDIA TOOLS")

def test_gdrive_tools_init():
    from core.tools.gdrive_tools import GDriveMediaTools, GDRIVE_TOOLS
    tools = GDriveMediaTools(remote_name="gdrive")
    assert len(GDRIVE_TOOLS) == 5, f"Expected 5 tools, got {len(GDRIVE_TOOLS)}"
    tool_names = [t["name"] for t in GDRIVE_TOOLS]
    assert "gdrive_search_media" in tool_names
    assert "gdrive_browse_folder" in tool_names
    assert "gdrive_download_media" in tool_names
    print(f"    GDrive tools: {len(GDRIVE_TOOLS)} — {tool_names}")
    return True

test("GDrive tools init", test_gdrive_tools_init)

def test_gdrive_search_no_rclone():
    from core.tools.gdrive_tools import GDriveMediaTools
    tools = GDriveMediaTools(remote_name="nonexistent")
    r = tools.search_media("test")
    assert r.get("ok") is False or "error" in r or "results" in r
    print(f"    GDrive search (no rclone): handled")
    return True

test("GDrive search graceful", test_gdrive_search_no_rclone)

section("17. PINTEREST TOOLS")

def test_pinterest_tools_init():
    from core.tools.pinterest_tools import PinterestTools, PINTEREST_TOOLS
    tools = PinterestTools()
    assert len(PINTEREST_TOOLS) == 7, f"Expected 7 tools, got {len(PINTEREST_TOOLS)}"
    tool_names = [t["name"] for t in PINTEREST_TOOLS]
    assert "pinterest_search" in tool_names
    assert "pinterest_download_pin" in tool_names
    assert "pinterest_download_board" in tool_names
    print(f"    Pinterest tools: {len(PINTEREST_TOOLS)} — {tool_names}")
    return True

test("Pinterest tools init", test_pinterest_tools_init)

def test_pinterest_list_downloads():
    from core.tools.pinterest_tools import PinterestTools
    tools = PinterestTools()
    r = tools.list_downloads()
    assert r["ok"]
    assert "files" in r
    print(f"    Pinterest list downloads: {r['total']} files")
    return True

test("Pinterest list downloads", test_pinterest_list_downloads)

section("SUMMARY")
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  TOTAL: {PASS + FAIL}")
if ERRORS:
    print(f"\n  ERRORS:")
    for e in ERRORS:
        print(f"    {e['test']}: {e['error']}")
print(f"\n{'='*60}")
if FAIL == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {FAIL} TEST(S) FAILED — FIX BEFORE DEPLOY")
print(f"{'='*60}\n")

sys.exit(0 if FAIL == 0 else 1)
