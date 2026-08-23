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
    assert coding["target_x"] == 150, f"Wrong target x: {coding['target_x']}"
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
    assert "cpu_percent" in result, "No CPU data"
    assert "ram" in result, "No RAM data"
    print(f"    CPU: {result['cpu_percent']}%")
    print(f"    RAM: {result['ram']['percent']}%")
    print(f"    Disk: {result['disk']['percent']}%")
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
# SUMMARY
# ============================================================

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
