"""
Generate all 58 SKILL.md files from Ponytail Pro Max 62 sources.
Run: python generate_skills.py
"""

import json
import os
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "config" / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

SKILLS = [
    # Skills (11)
    {"id": "agent-templates", "name": "Agent Templates", "category": "skills",
     "tags": ["agents", "templates", "commands"],
     "source": "#2 claude-code-templates",
     "description": "Agent personas (frontend-developer, build-checker, deployer) and commands"},
    {"id": "plugin-architecture", "name": "Plugin Architecture", "category": "skills",
     "tags": ["plugins", "self-install", "queue"],
     "source": "#12 OmniGet",
     "description": "Self-installing plugins, SHA256 verify, queue reliability, global hotkey"},
    {"id": "self-improving-skills", "name": "Self-Improving Skills", "category": "skills",
     "tags": ["skills", "self-improve", "templates"],
     "source": "#13 Awesome LLM Apps",
     "description": "100+ AI agent templates, multi-agent teams, CRAG, generative UI"},
    {"id": "threejs-skills", "name": "Three.js Skills", "category": "skills",
     "tags": ["3d", "threejs", "context-activated"],
     "source": "#29 Three.js Skills",
     "description": "Context-activated 3D skill loading, verified API references"},
    {"id": "gsap-skills", "name": "GSAP Skills", "category": "skills",
     "tags": ["animation", "gsap", "lifecycle"],
     "source": "#30 GSAP Skills",
     "description": "GSAP animation patterns, registerPlugin, React cleanup"},
    {"id": "creative-coding", "name": "Creative Coding Skills", "category": "skills",
     "tags": ["creative", "interaction", "design"],
     "source": "#33 Genjutsu",
     "description": "Interaction-thesis-before-code, MASTER.md design system"},
    {"id": "mcp-installation-surface", "name": "MCP Installation Surface", "category": "skills",
     "tags": ["mcp", "components", "audit"],
     "source": "#43 Shadcn Dashboard MCP",
     "description": "Components as typed MCP tools, get_audit_checklist"},
    {"id": "agent-pattern-taxonomy", "name": "Agent Pattern Taxonomy", "category": "skills",
     "tags": ["patterns", "taxonomy", "full-stack"],
     "source": "#49 Cult UI",
     "description": "92+ AI agent patterns, full-stack templates, agent taxonomy by role"},
    {"id": "tdd-engineering", "name": "TDD Engineering Discipline", "category": "skills",
     "tags": ["tdd", "testing", "debugging"],
     "source": "#54 Matt Pocock Skills",
     "description": "Grilling, TDD, debugging loops, deep-module architecture, CONTEXT.md"},
    {"id": "progressive-skill-loading", "name": "Progressive Skill Loading", "category": "skills",
     "tags": ["skills", "progressive", "config"],
     "source": "#56 CyberStrikeAI",
     "description": "Progressive skill loading, config-as-template, YAML tool recipes"},
    {"id": "anti-slop-design", "name": "Anti-Slop Design Skills", "category": "skills",
     "tags": ["design", "anti-slop", "variants"],
     "source": "#61 Taste",
     "description": "3 design dials, 8 specialized skill variants, redesign audit protocol"},

    # Tools (12)
    {"id": "capability-layer", "name": "Capability Layer", "category": "tools",
     "tags": ["routing", "capability", "doctor"],
     "source": "#10 Agent Reach",
     "description": "Multi-backend routing, default read-only, doctor command, select/route don't wrap"},
    {"id": "data-sync-connector", "name": "Data Sync Connector", "category": "tools",
     "tags": ["sync", "integration", "reverse-proxy"],
     "source": "#20 OpenConnector",
     "description": "Hash-based sync, field mapping, reverse proxy, CloudEvents, rate limit handling"},
    {"id": "docs-retrieval", "name": "Docs Retrieval", "category": "tools",
     "tags": ["docs", "version-specific", "hallucination"],
     "source": "#26 Context7",
     "description": "Version-specific documentation retrieval, hallucination countermeasures"},
    {"id": "prompt-first-scraping", "name": "Prompt-First Scraping", "category": "tools",
     "tags": ["scraping", "firecrawl", "interact"],
     "source": "#28 Firecrawl",
     "description": "Prompt-first not URL-first, 10 SDKs, interact API, robots.txt"},
    {"id": "secrets-convention", "name": "Secrets Convention", "category": "tools",
     "tags": ["secrets", "config", "multi-tenant"],
     "source": "#40 LeadPlus",
     "description": "__PLACEHOLDER__ searchable secrets, profile-based config, multi-tenant subdomain"},
    {"id": "visual-form-builder", "name": "Visual Form Builder", "category": "tools",
     "tags": ["forms", "builder", "codegen"],
     "source": "#52 FormsCN",
     "description": "Visual form builder, class-based state, multi-tier storage, framework-toggle codegen"},
    {"id": "ai-browser-automation", "name": "AI Browser Automation", "category": "tools",
     "tags": ["browser", "automation", "model-agnostic"],
     "source": "#53 Browser Use",
     "description": "Model-agnostic agent core, pluggable tools, @tools.action registry, dual CLI/library"},
    {"id": "yaml-tool-recipes", "name": "YAML Tool Recipes", "category": "tools",
     "tags": ["yaml", "tools", "rbac"],
     "source": "#56 CyberStrikeAI",
     "description": "100+ YAML tools with role-scoped access, capped output governance"},
    {"id": "link-attribution", "name": "Link Attribution", "category": "tools",
     "tags": ["links", "analytics", "full-stack"],
     "source": "#59 Dub",
     "description": "Open-source link attribution, open-core, full-stack reference architecture"},
    {"id": "find-existing-solutions", "name": "Find Existing Solutions", "category": "tools",
     "tags": ["directory", "discovery", "reference"],
     "source": "#60 github-repos",
     "description": "Curated directory of GitHub repos, awesome-list style, consult before building"},
    {"id": "fingerprint-hardening", "name": "Fingerprint Hardening", "category": "tools",
     "tags": ["security", "fingerprint", "config"],
     "source": "#3 Camoufox",
     "description": "Security fingerprint hardening, config validation, isolated scope logic"},

    # UI/UX (18)
    {"id": "ui-clones-reference", "name": "UI Clones Reference", "category": "ui-ux",
     "tags": ["clones", "reference", "patterns"],
     "source": "#9 Clone Wars",
     "description": "100+ open-source UI clones (Airbnb, Netflix, Spotify), check before designing"},
    {"id": "design-system-md", "name": "DESIGN.md System", "category": "ui-ux",
     "tags": ["design-system", "markdown", "tokens"],
     "source": "#19 Awesome DESIGN.md",
     "description": "9-section design system, 73 design language references, markdown = free bytes"},
    {"id": "video-as-html", "name": "Video as HTML", "category": "ui-ux",
     "tags": ["video", "html", "deterministic"],
     "source": "#25 HyperFrames",
     "description": "Video-as-HTML, deterministic rendering, adapter-based animation, reusable blocks"},
    {"id": "design-dna", "name": "Design DNA", "category": "ui-ux",
     "tags": ["design", "json", "tokens"],
     "source": "#31 Design DNA",
     "description": "Design as portable JSON, tokens + qualitative style + visual effects"},
    {"id": "motion-design", "name": "Motion Design", "category": "ui-ux",
     "tags": ["motion", "animation", "disney"],
     "source": "#32 Motion Design",
     "description": "8-step checklist, Disney principles for UI, emotion-to-motion mapping"},
    {"id": "visual-to-code", "name": "Visual to Code", "category": "ui-ux",
     "tags": ["codegen", "visual", "ai-layout"],
     "source": "#35 VibeUI Studio",
     "description": "Visual draft to logic bind, AI layout engine, skeleton-not-skin, multi-framework export"},
    {"id": "zero-dep-components", "name": "Zero-Dependency Components", "category": "ui-ux",
     "tags": ["components", "zero-dep", "copy-paste"],
     "source": "#41 Square UI",
     "description": "Zero-dependency copy-paste templates, no build step, HTML works standalone"},
    {"id": "design-system-monorepo", "name": "Design System Monorepo", "category": "ui-ux",
     "tags": ["monorepo", "turborepo", "base-ui"],
     "source": "#42 COSS",
     "description": "Turborepo design system, Base UI + Tailwind, copy-paste philosophy, cross-app linking"},
    {"id": "animated-components", "name": "Animated Components", "category": "ui-ux",
     "tags": ["components", "animated", "tree-shakeable"],
     "source": "#44 React Bits",
     "description": "165+ animated components, 4-variant matrix, minimal dependencies, tree-shakeable"},
    {"id": "canvas-components", "name": "Canvas Components", "category": "ui-ux",
     "tags": ["canvas", "webgl", "engine"],
     "source": "#45 Canvas UI",
     "description": "Canvas-drawn components, engine + thin wrappers, WebGL fallback, MCP-ready registry"},
    {"id": "copy-paste-own", "name": "Copy-Paste-Own", "category": "ui-ux",
     "tags": ["philosophy", "open-code", "primitives"],
     "source": "#47 shadcn/ui",
     "description": "Copy-paste-own philosophy, open code, composable accessible primitives"},
    {"id": "animation-first", "name": "Animation-First", "category": "ui-ux",
     "tags": ["animation", "motion", "modern-stack"],
     "source": "#48 Animate UI",
     "description": "Motion as core not add-on, React+TS+Tailwind+Motion stack, animation-first distribution"},
    {"id": "tailwind-shadcn-motion", "name": "Tailwind + shadcn + Motion", "category": "ui-ux",
     "tags": ["tailwind", "shadcn", "motion"],
     "source": "#50 Kokonut UI",
     "description": "Components built on Tailwind + shadcn/ui + Motion, community-first"},
    {"id": "folder-by-domain", "name": "Folder by Domain", "category": "ui-ux",
     "tags": ["structure", "theming", "mobile-first"],
     "source": "#51 Skiper UI",
     "description": "Folder-by-domain structure, CSS-variable theme system, mobile-first responsive"},
    {"id": "impeccable-design-rules", "name": "Impeccable Design Rules", "category": "ui-ux",
     "tags": ["design", "rules", "anti-patterns"],
     "source": "#62 Impeccable",
     "description": "23 commands, 59 deterministic detector rules, design hook, build path, explicit anti-patterns"},

    # Coding (8)
    {"id": "a11y-accessibility", "name": "Accessibility (a11y)", "category": "coding",
     "tags": ["a11y", "aria", "landmarks"],
     "source": "#1 Competition Real",
     "description": "a11y is #1 score-killer. Landmarks, ARIA labels, focus trap, modal management"},
    {"id": "headless-crud", "name": "Headless CRUD", "category": "coding",
     "tags": ["crud", "headless", "provider"],
     "source": "#11 Refine",
     "description": "Headless CRUD architecture, provider pattern, auto-gen UI, mutation invalidation"},
    {"id": "task-kanban-workspace", "name": "Task Kanban + Workspace", "category": "coding",
     "tags": ["kanban", "worktree", "isolation"],
     "source": "#18 Vibe Kanban",
     "description": "Plan-Build-Ship, workspace isolation (worktree+terminal+dev server), inline diff comments"},
    {"id": "code-graph-explore", "name": "Code Graph Explore", "category": "coding",
     "tags": ["codegraph", "context", "impact"],
     "source": "#21 CodeGraph",
     "description": "1 call replaces 28-43 grep+read, surgical context, impact analysis, 100% local SQLite"},
    {"id": "dead-code-elimination", "name": "Dead Code Elimination", "category": "coding",
     "tags": ["knip", "dead-code", "deps"],
     "source": "#22 Knip",
     "description": "Aggressive dead-code elimination, unused dependency detection, multi-surface architecture"},
    {"id": "sprint-workflow", "name": "Sprint Workflow", "category": "coding",
     "tags": ["sprint", "think-plan-build", "review"],
     "source": "#27 gstack",
     "description": "Think-Plan-Build-Review-Test-Ship-Reflect, 23 specialist commands, cross-model second opinion"},
    {"id": "code-templates-frontend", "name": "Code Templates (Frontend)", "category": "coding",
     "tags": ["templates", "frontend", "terminal"],
     "source": "#2 claude-code-templates",
     "description": "Component-first thinking, terminal aesthetics, self-review, build verification"},

    # Security (10)
    {"id": "security-killchain", "name": "Security Kill-Chain", "category": "security",
     "tags": ["killchain", "guardrails", "react"],
     "source": "#14 CAI",
     "description": "Agent per kill-chain phase (recon, exploit, privesc, lateral, exfil, C2), handoffs, guardrails"},
    {"id": "poc-validation", "name": "PoC Validation", "category": "security",
     "tags": ["poc", "sast", "dast", "compliance"],
     "source": "#15 Strix",
     "description": "Every finding = working PoC, SAST+DAST, AI patches as PRs, compliance (SOC2, ISO27001)"},
    {"id": "multi-agent-supervision", "name": "Multi-Agent Supervision", "category": "security",
     "tags": ["supervision", "mentor", "memory"],
     "source": "#16 PentAGI",
     "description": "Execution monitoring, loop detection, auto-invoke mentor, chain summarization, memory systems"},
    {"id": "staged-pentest", "name": "Staged Pentest", "category": "security",
     "tags": ["pentest", "staged", "session"],
     "source": "#17 PentestGPT",
     "description": "Staged phases, session save/resume, 3 cooperating LLM: reasoning/generation/parsing"},
    {"id": "recon-automation", "name": "Recon Automation", "category": "security",
     "tags": ["recon", "scope-check", "triage"],
     "source": "#23 ReconForge",
     "description": "Recon automation, scope-checking gate, AI triage prompts, concurrent thread pools"},
    {"id": "scanner-registry", "name": "Scanner Registry", "category": "security",
     "tags": ["scanner", "40k-rules", "caching"],
     "source": "#24 Medusa",
     "description": "40k+ rules, BaseScanner+ScannerRegistry, content-hash caching (22x faster), CI gate"},
    {"id": "diff-aware-security", "name": "Diff-Aware Security", "category": "security",
     "tags": ["diff", "pr-scan", "modular"],
     "source": "#55 Claude Code Security Review",
     "description": "Only scan changed files, modular pipeline, explicit denylist, prompt-injection limitations"},
    {"id": "red-team-sdk", "name": "Red-Team SDK", "category": "security",
     "tags": ["redteam", "attack", "judge"],
     "source": "#58 HackAgent",
     "description": "Generator-Target-Judge LLM pipeline, pluggable attack strategies, multi-framework adapters"},

    # Token/Memory (4)
    {"id": "layered-memory", "name": "Layered Memory", "category": "memory",
     "tags": ["layered", "raw-summary-canvas", "traceability"],
     "source": "#5 TencentDB Agent Memory",
     "description": "Never flat-store, layer it (raw-summary-canvas), symbolic memory (Mermaid), hybrid recall BM25+vector+RRF"},
    {"id": "token-compression-output", "name": "Output Token Compression", "category": "memory",
     "tags": ["compression", "output", "caveman"],
     "source": "#6 Caveman",
     "description": "Drop articles/filler/hedging, never invent abbreviations, originals cached, measure before compressing"},
    {"id": "token-compression-shell", "name": "Shell Token Compression", "category": "memory",
     "tags": ["compression", "shell", "rtk"],
     "source": "#7 RTK",
     "description": "Smart filtering+grouping+truncation+dedup, per-command targets, failure recovery"},
    {"id": "token-compression-input", "name": "Input Token Compression", "category": "memory",
     "tags": ["compression", "input", "headroom"],
     "source": "#8 Headroom",
     "description": "Content-aware compression, reversible CCR, cache alignment, output token reduction, failure learning"},

    # Output Style (1)
    {"id": "adhd-output-style", "name": "ADHD Output Style", "category": "output",
     "tags": ["adhd", "output", "action-first"],
     "source": "#4 i-have-adhd",
     "description": "Lead with next action, number steps, restate state, specific time estimates, cap lists at 5"},

    # Workflow (2)
    {"id": "provider-abstraction", "name": "Provider Abstraction", "category": "workflow",
     "tags": ["provider", "run-control", "sandbox"],
     "source": "#38 LibreChat",
     "description": "Unified provider abstraction, interrupt/steer/queue/resume, sandboxed code interpreter, generative UI"},
    {"id": "approval-gate", "name": "6-Step Approval Gate", "category": "workflow",
     "tags": ["approval", "gate", "rollback"],
     "source": "#39 Claude Ads",
     "description": "6-step approval/rollback/verification gate, versioned JSON canonical, no X without Y, SHA-256 release"},

    # Finance (2)
    {"id": "risk-first-trading", "name": "Risk-First Trading", "category": "finance",
     "tags": ["trading", "risk", "structured"],
     "source": "#36 AutoHedge",
     "description": "Director-Quant-Risk-Execution, risk agent = gate not afterthought, JSON outputs, modular framework"},
    {"id": "tested-finance-math", "name": "Tested Finance Math", "category": "finance",
     "tags": ["finance", "tested", "audit"],
     "source": "#37 Vibe-Trading",
     "description": "Refuse answers without evidence, 249+ tested functions, hash-chained ledger, sandbox evasion testing"},
]


def generate_skill_md(skill: dict) -> str:
    """Generate SKILL.md content for a skill."""
    return f"""---
name: {skill['name']}
description: {skill['description']}
version: 1.0.0
category: {skill['category']}
tags: [{', '.join(skill['tags'])}]
source: {skill['source']}
---

# {skill['name']}

## Description
{skill['description']}

## Source
{skill['source']}

## Category
{skill['category']}

## Tags
{', '.join(skill['tags'])}

## When to Use
Load this skill when the task involves {skill['tags'][0].replace('-', ' ')}.

## Key Patterns
- Follow the patterns described in the source
- Adapt to the current context
- Apply only what is new beyond baseline rules

## Integration
This skill auto-loads when the agent detects relevant context keywords.
"""


def main():
    index = {"skills": []}
    for skill in SKILLS:
        content = generate_skill_md(skill)
        filepath = SKILLS_DIR / f"{skill['id']}.md"
        filepath.write_text(content, encoding="utf-8")
        index["skills"].append({
            "id": skill["id"],
            "name": skill["name"],
            "description": skill["description"],
            "category": skill["category"],
            "tags": skill["tags"],
            "source": skill["source"],
            "version": "1.0.0",
        })
    index_path = SKILLS_DIR / "index.json"
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Generated {len(SKILLS)} skills in {SKILLS_DIR}")
    print(f"Index: {index_path}")
    cats = {}
    for s in SKILLS:
        cats[s["category"]] = cats.get(s["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
