# KAIHARA OS

> Personal AI Super-Intelligence & Agentic OS — a brain that remembers everything, a fantastic orchestrator, a deep researcher, a guardian, and a voice.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/React-19-cyan)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-orange)]()

---

## What is Kaihara?

Kaihara is a self-hosted, multi-agent AI super-intelligence built from scratch. It is **not** a chatbot — it is an **Agentic OS** that manages itself, orchestrates a fleet of specialized agents, learns from its own operations, and communicates via voice, text, and messaging channels.

Inspired by the best open-source AI projects:
- **OpenHuman** — Memory Tree, Subconscious loop, TokenJuice, Split brain
- **OpenCode** — Multi-model routing, 75+ providers, variants, privacy mode
- **Odysseus** — SearXNG, MCP servers, Docker+GPU, Email, Calendar
- **OpenClaw / CowAgent** — SOUL.md, 3-tier memory, Deep Dream, Self-Evolution
- **Ngoding Pake AI** — PRD generation pipeline (Idea → PRD → Specs → Tasks → Code → Deploy)
- **Ponytail Pro Max** — 61 skills from 62 curated source repos
- **AI Town (a16z)** — Agent visualization with live movement and speech bubbles

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Command Center** | Intent parser + split brain (reflex vs deep) + fleet manager |
| **7 Agent Fleet** | kaihara, coding, marketing, security, deploy, research, meta |
| **3-Tier Memory** | Context (short) → Daily (mid) → Core (long) + Deep Dream nightly distillation |
| **Hybrid Recall** | BM25 (keyword) + Vector (semantic) + Graph (topic) + RRF fusion |
| **TokenJuice** | Output compression (Caveman) + Input compression (Headroom) + Shell compression (RTK) — up to 80% fewer tokens |
| **Multi-Model** | 75+ providers, per-agent model routing, variants, privacy mode |
| **PRD Pipeline** | Idea → PRD → Feature Specs → Task Breakdown → Kanban → Code → Deploy |
| **61 Skills** | Auto-loaded SKILL.md files across 9 categories, conversational authoring |
| **Voice (Jarvis)** | Wake word detection + Whisper STT + Piper TTS — fully local |
| **Security** | 6-step approval gate, Docker sandbox, audit trail, staged pentest (recon → scan → exploit → report) |
| **Channels** | Telegram + WhatsApp (Baileys) + Email (SMTP/IMAP) — two-way |
| **OS Kernel** | 7 background agents: file, process, network, backup, update, health, cost |
| **Meta Agent** | Learns from all agents, suggests optimizations, corrects inefficiencies, prevents repetition via cache |
| **Agent Map** | Live Canvas visualization (ai-town style) — agents move between stations with speech bubbles |
| **Dashboard** | HUD-style UI with 7 tabs: chat, map, tasks, skills, security, memory |
| **Proxmox LXC** | 6 isolated containers for production deployment |
| **Docker** | Full docker-compose.yml with Traefik, Grafana, Gitea, SearXNG |
| **Obsidian Vault** | All memory mirrored to a local Obsidian vault you can edit |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        KAIHARA OS                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  INTERFACE: Voice + HUD Dashboard + Channels           │     │
│  └──────────────────────────┬─────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────┐     │
│  │  KAIHARA CORE (SOUL.md)                                 │     │
│  │  Proactive · Memory · Subconscious · Goals              │     │
│  └──────────────────────────┬─────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────┐     │
│  │  ORCHESTRATOR                                           │     │
│  │  Command Center → Split Brain → Fleet Manager           │     │
│  │  Checkpoint Graphs (LangGraph) · Approval Gate           │     │
│  └──────────────────────────┬─────────────────────────────┘     │
│                             │                                    │
│  ┌──────────┬───────────┬────────────┬──────────┬──────────┐  │
│  │ BRAIN &  │ SKILLS &  │ PLANNING   │ SECURITY │ OS KERNEL│  │
│  │ MEMORY   │ PROMPTS   │ PIPELINE   │ DEFENDER │ AGENTS   │  │
│  │          │           │            │          │          │  │
│  │ 3-tier   │ 61 skills │ PRD→Specs  │ Gate     │ 7 agents │  │
│  │ BM25+Vec │ SOUL.md   │ →Tasks     │ Sandbox  │ 24/7     │  │
│  │ RRF+Deep │ Authoring │ →Kanban    │ Pentest  │          │  │
│  │ Dream    │           │ →Code      │ Audit    │          │  │
│  │ Obsidian │           │ →Deploy   │          │          │  │
│  └──────────┴───────────┴────────────┴──────────┴──────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  AGENT FLEET (7 agents, each with SOUL.md)              │     │
│  │  kaihara · coding · marketing · security · deploy       │     │
│  │  research · meta (optimizer)                             │     │
│  └──────────────────────────┬─────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────┐     │
│  │  CHANNELS · VOICE · VIZ · INTEGRATIONS                  │     │
│  │  Telegram · WhatsApp · Email · Whisper · Piper          │     │
│  │  Agent Map (Canvas) · MCP · Webhooks · REST              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  INFRASTRUCTURE: Proxmox LXC · Docker · Traefik · Grafana      │
│                 Gitea · SearXNG · Obsidian                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
# Python deps
cd kaihara
pip install -r requirements.txt

# Dashboard deps
cd dashboard
npm install
```

### 2. Configure LLM Provider

Edit `config.toml`:

```toml
[provider.rootsys]
name = "RootSys Cloud"
base_url = "https://rootsys.cloud/v1"
api_key = "your-api-key-here"
api_key_header = "X-API-Key"

[provider.ollama]
name = "Ollama (local)"
base_url = "http://localhost:11434/v1"

[privacy]
mode = false  # true = local only, false = allow cloud

[model]
default = "rootsys/glm-5.2"
small_model = "rootsys/deepseek-v4-flash"
```

### 3. Run Kaihara

```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Dashboard
cd dashboard && npm run dev

# Open: http://localhost:5173
```

### CLI Mode

```bash
python main.py --chat     # Interactive chat
python main.py --status   # System status
python main.py            # Server mode (http://localhost:7000)
```

---

## Configuration

### Model Routing (per agent)

```toml
[agent.kaihara]       model = "rootsys/glm-5.2"
[agent.coding]        model = "rootsys/kimi-k3"
[agent.security]      model = "rootsys/glm-5.3"
[agent.reflex]        model = "rootsys/deepseek-v4-flash"
[agent.meta]          model = "rootsys/deepseek-v4-flash"
```

### Available RootSys Models

| Model | Context | Best For |
|-------|---------|----------|
| glm-5.2 | 1M | General, balanced |
| glm-5.3 | 1M | Complex reasoning |
| deepseek-v4-pro | 1M | Deep tasks |
| deepseek-v4-flash | — | Fast, cheap |
| kimi-k3 | 1M | Coding, vision |
| minimax-m3 | — | Vision |
| gpt-5.6-sol | — | Specialized |

### Other Providers

```toml
[provider.openai]      # OPENAI_API_KEY env var
[provider.anthropic]   # ANTHROPIC_API_KEY env var
[provider.gemini]      # GEMINI_API_KEY env var (free tier)
[provider.openrouter]  # OPENROUTER_API_KEY env var (100+ models)
```

---

## Agent Fleet

| Agent | SOUL.md | Station | Model | Role |
|-------|---------|---------|-------|------|
| **kaihara** | kaihara.md | Command Center | glm-5.2 | Main personality, proactive, voice |
| **coding** | coding.md | Coding Desk | kimi-k3 | Write & debug code |
| **marketing** | — | Marketing Hub | glm-5.2 | Scrape, analyze, $$$ focus |
| **security** | security.md | Security Terminal | glm-5.3 | Pentest, defend, audit |
| **deploy** | — | Deploy Station | deepseek-v4-flash | CI/CD, Docker, Proxmox |
| **research** | — | Research Desk | glm-5.2 | Web search, deep research |
| **meta** | meta.md | Meta Observatory | deepseek-v4-flash | Learn, suggest, correct, dedup |

---

## OS Kernel (7 Background Agents)

| Agent | Interval | Function |
|-------|----------|----------|
| File Agent | 10min | Clean temp, disk usage, find duplicates |
| Process Agent | 2min | Kill zombies, find CPU hogs |
| Network Agent | 3min | Monitor connections, check ports, bandwidth |
| Backup Agent | 1hour | Auto backup at 3AM, verify, cleanup old |
| Update Agent | daily | Check OS/pip/Ollama updates |
| Health Agent | 1min | CPU/RAM/disk/temp, alert on thresholds |
| Cost Agent | 5min | Track API spend, budget alerts, switch to local |

---

## Skills (61 SKILL.md files)

| Category | Count | Examples |
|----------|-------|----------|
| skills | 11 | Agent templates, self-improving, creative coding |
| tools | 11 | Browser automation, data sync, scraping, docs retrieval |
| ui-ux | 15 | shadcn/ui, animation, design systems, anti-slop |
| coding | 7 | a11y, headless CRUD, code graph, TDD, sprint workflow |
| security | 8 | Kill-chain, PoC validation, pentest, scanner, red-team |
| memory | 4 | Layered memory, token compression (output/shell/input) |
| output | 1 | ADHD-friendly output style |
| workflow | 2 | Provider abstraction, 6-step approval gate |
| finance | 2 | Risk-first trading, tested finance math |

---

## API Endpoints

### Core
```
GET  /api/status                    — System status
POST /api/chat                      — Send message to Kaihara
POST /api/webhook                    — Receive webhook
GET  /api/memory/recall?q=...        — Search memory
GET  /api/goals                      — List goals
POST /api/goals                      — Add goal
WS   /ws                             — Real-time bidirectional
```

### Planning Pipeline
```
POST /api/planning/plan              — Full pipeline (idea → tasks)
POST /api/planning/prd               — Generate PRD only
GET  /api/planning/tasks             — List tasks (kanban)
POST /api/planning/tasks/:id/status  — Update task status
GET  /api/planning/progress          — Progress summary
```

### Skills
```
GET  /api/skills                     — List skills (filter/search)
GET  /api/skills/:id                 — Get skill content
POST /api/skills/create              — Create skill from description
DELETE /api/skills/:id              — Remove skill
```

### Security & Pentest
```
GET  /api/security/status            — All security components
GET  /api/security/approvals         — Pending approvals
POST /api/security/approvals/:id/approve  — Approve action
POST /api/security/approvals/:id/deny     — Deny action
GET  /api/security/audit             — Audit log
POST /api/pentest/run               — Run pentest pipeline
GET  /api/pentest/sessions           — List pentest sessions
```

### OS Kernel
```
GET  /api/kernel/status              — All 7 agent statuses
POST /api/kernel/start               — Start all agents
POST /api/kernel/:name/run           — Run agent once
```

### Meta Agent
```
GET  /api/meta/status                — Meta agent + cache stats
GET  /api/meta/suggestions           — Optimization suggestions
GET  /api/meta/patterns             — Detected patterns
POST /api/meta/analyze               — Run full fleet analysis
```

### Voice
```
GET  /api/voice/status               — STT/TTS/wake word status
POST /api/voice/start                — Start voice loop
POST /api/voice/speak                — Speak text via TTS
```

### Channels
```
GET  /api/channels                   — All channel status
POST /api/channels/start             — Start all channels
POST /api/channels/:name/send        — Send message via channel
```

### Visualization
```
GET  /api/viz/map                    — Full agent map state
POST /api/viz/move                   — Move agent to station
POST /api/viz/speech                 — Set agent speech bubble
POST /api/viz/interaction            — Record A2A interaction
```

---

## Project Structure

```
kaihara/
├── main.py                          # Entry point (CLI + server)
├── config.toml                      # Main configuration
├── requirements.txt                 # Python dependencies
│
├── agents/                          # Worker agent fleet
│   ├── base_agent.py                # Base class + SOUL.md loader
│   └── meta_agent.py                # Meta agent (learn, optimize, dedup)
│
├── config/
│   ├── soul/                        # Agent identities (SOUL.md)
│   │   ├── kaihara.md                # Kaihara personality (ADHD output style)
│   │   ├── coding.md                 # Coding agent
│   │   ├── security.md               # Security agent
│   │   └── meta.md                   # Meta agent
│   └── skills/                      # 61 SKILL.md files
│       ├── index.json                # Skill catalog
│       └── *.md                      # Skill definitions
│
├── core/
│   ├── orchestrator/
│   │   ├── command_center.py        # Entry + router + split brain + fleet
│   │   └── model_router.py          # Multi-model routing (75+ providers)
│   │
│   ├── brain/
│   │   ├── memory_tree.py           # 3-tier memory + BM25 + Vector + RRF
│   │   ├── token_juice.py           # Compression (Caveman + RTK + Headroom)
│   │   └── learning_cache.py        # Cache results, prevent repetition
│   │
│   ├── planning/                    # PRD pipeline (Ngoding Pake AI)
│   │   ├── pipeline.py              # Coordinator
│   │   ├── prd_agent.py             # Idea → PRD
│   │   ├── spec_agent.py            # PRD → feature specs
│   │   ├── task_agent.py            # Specs → ordered tasks
│   │   ├── task_tracker.py          # SQLite kanban
│   │   └── templates/               # PRD, spec, task templates
│   │
│   ├── skills/
│   │   ├── registry.py              # Skill registry + search + install
│   │   └── skill_authoring.py       # Conversational skill creation
│   │
│   ├── security/
│   │   ├── approval_gate.py         # 6-step approval (Claude Ads #39)
│   │   ├── sandbox.py               # Docker sandbox execution
│   │   ├── audit.py                 # Append-only audit trail
│   │   └── pentest/
│   │       ├── recon.py             # nmap + DNS + subdomain (CAI #14)
│   │       ├── vuln_scan.py         # nikto + sqlmap + custom (Medusa #24)
│   │       ├── exploit.py           # PoC validation (Strix #15)
│   │       └── pipeline.py          # Staged pentest (PentestGPT #17)
│   │
│   ├── os/                          # Agentic OS kernel (7 agents)
│   │   ├── kernel.py                # Kernel manager
│   │   ├── file_agent.py            # Clean temp, disk, dedupe
│   │   ├── process_agent.py         # Kill zombies, CPU hogs
│   │   ├── network_agent.py         # Connections, ports, bandwidth
│   │   ├── backup_agent.py          # Auto 3AM backup
│   │   ├── update_agent.py          # OS/pip/Ollama updates
│   │   ├── health_agent.py          # CPU/RAM/disk/temp alerts
│   │   └── cost_agent.py           # API spend tracking
│   │
│   ├── voice/                       # Jarvis-style voice pipeline
│   │   ├── pipeline.py              # Wake → STT → agent → TTS
│   │   ├── stt.py                   # Whisper (local, free)
│   │   ├── tts.py                   # Piper (local, natural voice)
│   │   └── wake_word.py             # OpenWakeWord detection
│   │
│   ├── channels/                    # Messaging channels (two-way)
│   │   ├── base.py                  # Abstract channel interface
│   │   ├── telegram.py              # Telegram bot
│   │   ├── whatsapp.py              # WhatsApp (Baileys bridge)
│   │   ├── email_channel.py         # Email (SMTP + IMAP)
│   │   ├── manager.py               # Channel manager
│   │   └── whatsapp_bridge/         # Node.js Baileys bridge
│   │       └── whatsapp_bridge.js
│   │
│   ├── viz/                         # Visualization (ai-town style)
│   │   └── agent_map.py             # Agent positions, movements, speech
│   │
│   └── server/
│       └── api.py                   # FastAPI REST + WebSocket
│
├── dashboard/                       # KAIHARA HUD (React + Vite + Tailwind)
│   ├── src/
│   │   ├── App.tsx                  # Main layout (3-column HUD)
│   │   ├── lib/api.ts               # API client (all endpoints)
│   │   └── components/
│   │       ├── KaiharaStatus.tsx    # Online/thinking indicator
│   │       ├── Conversation.tsx     # Chat (text + voice + waveform)
│   │       ├── AgentActivity.tsx    # Real-time agent progress bars
│   │       ├── SystemStatus.tsx     # Models/agents/memory/tokenjuice
│   │       ├── MorningBriefing.tsx  # Daily summary
│   │       ├── GoalsTracker.tsx     # Task goals with priority
│   │       ├── NotificationPanel.tsx# Alerts
│   │       ├── TaskBoard.tsx        # Kanban (PRD pipeline)
│   │       ├── SkillBrowser.tsx     # Browse/search/create skills
│   │       ├── SecurityView.tsx     # Approvals + audit + pentest
│   │       ├── ChannelStatus.tsx    # Telegram/WhatsApp/Email status
│   │       ├── KernelStatus.tsx     # OS kernel 7 agents
│   │       ├── MetaPanel.tsx        # Meta agent suggestions + patterns
│   │       └── AgentMap.tsx         # Canvas visualization (ai-town style)
│   └── package.json
│
├── docker/                          # Docker alternative setup
│   ├── docker-compose.yml           # All-in-one (core + LLM + dashboard + traefik)
│   ├── Dockerfile.core              # Python app container
│   ├── Dockerfile.dashboard         # React build → nginx
│   ├── Dockerfile.whatsapp         # WhatsApp bridge container
│   ├── nginx.conf                   # Dashboard nginx config
│   └── traefik-labels.txt           # Traefik SSL + routing labels
│
├── proxmox/                         # Proxmox LXC setup scripts
│   ├── main.sh                      # Master setup (6 containers)
│   ├── lxc-core.sh                  # CT 201: Kaihara Core + API
│   ├── lxc-llm.sh                   # CT 202: Ollama LLM
│   ├── lxc-dashboard.sh             # CT 203: Dashboard (nginx)
│   ├── lxc-channels.sh              # CT 204: Telegram + WhatsApp + Email
│   ├── lxc-security.sh              # CT 205: Pentest tools
│   └── lxc-kernel.sh                # CT 206: OS Kernel agents
│
├── obsidian-vault/                  # Synced Obsidian vault
│   ├── memory/                      # 3-tier: context/daily/core
│   ├── knowledge/                   # By topic (coding, marketing, security)
│   ├── goals/                       # Long-term goal tracking
│   ├── briefings/                   # Morning briefings
│   └── prd/                         # Generated PRDs
│
├── scripts/
│   └── generate_skills.py          # Generate 61 SKILL.md from 62 sources
│
└── data/                           # Runtime data
    ├── kaihara.db                  # SQLite (memory + tasks + audit)
    ├── chroma/                     # ChromaDB vector store
    ├── audit.log                   # Append-only audit trail
    ├── api_costs.json              # API usage + cost tracking
    └── backups/                    # Auto tar.gz backups
```

---

## Deployment

### Option 1: Local Development

```bash
pip install -r requirements.txt
python main.py              # Backend on :7000
cd dashboard && npm run dev  # Frontend on :5173
```

### Option 2: Docker Compose

```bash
cd docker
docker compose up -d

# Services:
#   kaihara-core      :7000  (API)
#   kaihara-llm       :11434 (Ollama)
#   kaihara-dashboard :5173  (HUD)
#   traefik           :80/:443 (SSL)
#   grafana           :3000  (Monitoring)
#   gitea             :3001  (Git)
#   whatsapp-bridge          (WhatsApp)
#   searxng           :8888  (Search)
```

### Option 3: Proxmox LXC

```bash
# On Proxmox host:
scp -r kaihara/ root@proxmox:/root/
ssh root@proxmox
cd /root/kaihara
bash proxmox/main.sh

# 6 LXC containers created:
#   CT 201: kaihara-core      10.10.10.10  (API)
#   CT 202: kaihara-llm       10.10.10.11  (Ollama)
#   CT 203: kaihara-dashboard 10.10.10.12  (Dashboard)
#   CT 204: kaihara-channels  10.10.10.13  (Telegram/WA/Email)
#   CT 205: kaihara-security  10.10.10.14  (Pentest tools)
#   CT 206: kaihara-kernel    10.10.10.15  (OS agents)
```

---

## SOUL.md — Agent Identity

Each agent has a SOUL.md file that defines its identity, personality, capabilities, tools, model routing, memory access, and approval requirements.

```markdown
# SOUL.md — Coding Agent

## Identity
You are an expert software engineer agent in the Kaihara fleet.

## Personality
- Direct and concise
- Security-conscious
- Test-first mentality

## Workflow (Think → Plan → Build → Review → Test → Ship)
...

## Approval Required For
- push_to_git
- deploy_to_production
```

---

## Inspiration & Sources

Kaihara OS is built from scratch but draws patterns from:

| Project | What We Took |
|---------|-------------|
| OpenHuman (36.5k) | Memory Tree, Obsidian sync, Subconscious, TokenJuice, Split brain |
| OpenCode | Multi-model routing, 75+ providers, variants, privacy mode |
| Odysseus (85.9k) | SearXNG, MCP, Docker+GPU, Email, Calendar |
| OpenClaw / CowAgent (46.6k) | SOUL.md, 3-tier memory, Deep Dream, Self-Evolution |
| Hermes Agent | Self-learning, terminal-first concept |
| AgentTeams | Matrix rooms for A2A coordination |
| NemoClaw (NVIDIA) | Sandboxed execution pattern |
| Ngoding Pake AI | PRD pipeline (Idea → PRD → Code → Deploy) |
| Ponytail Pro Max (62 sources) | 61 skills: TokenJuice, Security, Workflow, Design, ADHD output |
| AI Town (a16z, 10.4k) | Agent visualization with movement and speech bubbles |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic |
| Frontend | React 19, Vite 6, Tailwind CSS 3 |
| Database | SQLite (memory, tasks, audit) |
| Vector Search | ChromaDB |
| Agent Graphs | LangGraph (checkpointed) |
| LLM | Ollama (local) / RootSys Cloud / OpenAI / Anthropic / 75+ providers |
| Voice | Whisper (STT) + Piper (TTS) + OpenWakeWord |
| Channels | python-telegram-bot + Baileys (WhatsApp) + aiosmtplib (Email) |
| Visualization | HTML5 Canvas (agent map) |
| Monitoring | psutil + Grafana |
| Reverse Proxy | Traefik |
| Git | Gitea (self-hosted) |
| Search | SearXNG (free, private) |
| Deployment | Proxmox LXC / Docker Compose |

---

## License

MIT — use it, build with it, make it yours.

---

## Author

Built from scratch as a personal AI super-intelligence.

---

> *"Good morning. You have 3 priority tasks today." — Kaihara*
