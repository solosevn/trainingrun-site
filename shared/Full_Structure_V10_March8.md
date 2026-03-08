# David's AI Company — Full Operational Structure

> **Version:** V10 — March 8, 2026
> **Status:** Working document — David + Claude finalizing
> **Purpose:** Single source of truth for every agent, non-agent, process, and cadence that powers David's AI Company (TrainingRun.AI + TS Arena)

---

## Company Hierarchy

```
David's AI Company
├── CEO Agent (future)
├── Security Agent (future)
├── TrainingRun.AI Site ─── TRSitekeeper (Site Manager) ✅ LIVE
│   ├── Daily News Agent ✅ BUILT
│   │   └── Content Scout (sub-agent) ✅ LIVE v1.2.0
│   └── DDP Pipeline (5 scrapers) ✅ ACTIVE
└── TS Arena Site ─── Arena Ops (Site Manager) ⚠️ PLANNED
    ├── Battle Generator ⚠️ PARTIALLY BUILT
    ├── Model Manager ❌ NOT BUILT
    ├── Prompt Curator ❌ NOT BUILT
    ├── Vote Counter ⚠️ ACTIVE BUT UNDOCUMENTED
    └── Site Builder ❌ NOT BUILT
```

**Key principle:** Each site has a Site Manager agent. All agents within a site report to their Site Manager. Both Site Managers will eventually report up through Security and CEO agents. Each GitHub repo is a property the company owns — not the top of the hierarchy.

---

## Agent File Standard

**Every agent gets the Core 7 files.** Established with the Daily News Agent build (March 5, 2026). Applies to all agents. Agents may have additional role-specific files on top of the Core 7.

| # | File | Purpose |
|---|---|---|
| 1 | **SOUL.md** | Identity, mission, ownership, boundaries, relationships, how I think, learning mandate, REASONING-CHECKLIST integration |
| 2 | **CONFIG.md** | Every technical detail the agent needs — APIs, endpoints, Telegram bots, file paths, security notes |
| 3 | **PROCESS.md** | Complete step-by-step workflow with diagram, human gates, exception handling, file dependencies |
| 4 | **CADENCE.md** | When it runs, what triggers it, daily/weekly/monthly/quarterly rhythms, exception handling |
| 5 | **RUN-LOG.md** | Log of every execution — structured data, append-only, never modified |
| 6 | **LEARNING-LOG.md** | Raw memory — post-mortems, process metrics, approval data, reflections, monthly summaries |
| 7 | **STYLE-EVOLUTION.md** | Curated rules distilled from LEARNING-LOG — confidence levels (hypothesis → emerging → strong), retired rules |

**Every SOUL.md** includes the REASONING-CHECKLIST.md integration reference from `shared/REASONING-CHECKLIST.md`.

**V9/V10 KEY CHANGE: Unified vault per agent.** Each agent's vault (Core 7 + role-specific files) lives inside the agent's own folder alongside its code, memory, and skills. No more separate context-vault directory. Code reads from, writes to, and audits the same location.

**Sub-agents** (like Content Scout under Daily News Agent) get their own folder under agents/ with their own vault/. They have their own Core 7 but operate under the parent agent's authority.

**Non-agents** (scripts, scrapers, bots) are documented inside their parent agent's CONFIG.md and PROCESS.md but remain visible on the directory tree with their parent agent noted.

---

## PART 1: TrainingRun.AI

---

### TrainingRun Directory Tree (V9/V10 — Restructured March 8, 2026)

```
trainingrun-site/                                        # ← REPO ROOT (one property of David's AI Company)
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            AGENTS                                    ║
│ ╚══════════════════════════════════════════════════════╝
│
├── agents/
│   │
│   ├── trsitekeeper/                                    # 🧠 TRSITEKEEPER v2.0 — SITE MANAGER
│   │   ├── vault/                                       # ✅ THE vault — read + write + audit (unified)
│   │   │   ├── SOUL.md
│   │   │   ├── CONFIG.md
│   │   │   ├── PROCESS.md
│   │   │   ├── CADENCE.md
│   │   │   ├── CAPABILITIES.md
│   │   │   ├── TASK-LOG.md
│   │   │   ├── RUN-LOG.md
│   │   │   ├── LEARNING-LOG.md
│   │   │   └── STYLE-EVOLUTION.md
│   │   ├── memory/                                      # ✅ V2.0 memory (filesystem-backed)
│   │   │   ├── david_model.json                         # Theory-of-Mind
│   │   │   ├── site_knowledge.json                      # Full page map
│   │   │   ├── fix_patterns.json                        # 9 seeded patterns
│   │   │   ├── error_log.jsonl                          # Append-only error log
│   │   │   ├── tried_fixes.jsonl                        # Tried-and-failed memory
│   │   │   ├── memory_log.jsonl                         # Interaction log
│   │   │   └── AUDIT_FIX_TRAINING_2026-03-08.md         # Training doc from audit fixes
│   │   ├── skills/                                      # ✅ Reasoning templates
│   │   │   ├── css_diagnosis.md
│   │   │   ├── data_staleness.md
│   │   │   └── git_safety.md
│   │   ├── agent.py                                     # ✅ Main orchestrator (Telegram + Claude API)
│   │   ├── brain.md                                     # ✅ System prompt
│   │   ├── sitekeeper_audit.py                          # ✅ 24-check autonomous audit
│   │   ├── sitekeeper_context_loader.py                 # ✅ Boot sequence — loads vault/ into 6-layer context
│   │   ├── sitekeeper_learning_logger.py                # ✅ Writes to vault/ and memory/
│   │   ├── audit_history.json                           # Audit run history
│   │   └── README_AGENT.md                              # Setup documentation
│   │
│   ├── daily-news/                                      # 📰 DAILY NEWS AGENT — The Journalist
│   │   ├── vault/                                       # ✅ THE vault (unified)
│   │   │   ├── SOUL.md
│   │   │   ├── CONFIG.md
│   │   │   ├── PROCESS.md
│   │   │   ├── CADENCE.md
│   │   │   ├── RUN-LOG.md
│   │   │   ├── LEARNING-LOG.md
│   │   │   ├── STYLE-EVOLUTION.md
│   │   │   └── ENGAGEMENT-LOG.md
│   │   ├── staging/                                     # Draft papers + .last_processed_date
│   │   ├── main.py                                      # ✅ Orchestrator + Telegram bot
│   │   ├── config.py                                    # ✅ Settings, paths, API config
│   │   ├── context_loader.py                            # ✅ Reads from vault/ (local → GitHub fallback)
│   │   ├── story_selector.py                            # ✅ Grok-3-mini selects best story
│   │   ├── article_writer.py                            # ✅ Grok-3 writes article
│   │   ├── html_stager.py                               # ✅ Generates day-NNN.html
│   │   ├── github_publisher.py                          # ✅ Publishes via GitHub REST API
│   │   ├── telegram_handler.py                          # ✅ Sends drafts, receives approval
│   │   ├── learning_logger.py                           # ✅ Logs runs + learns from feedback
│   │   ├── image_generator.py                           # Image generation for articles
│   │   ├── requirements.txt                             # Python dependencies
│   │   ├── .env.example                                 # Credential template
│   │   └── com.trainingrun.daily-news.plist             # macOS launchd service
│   │
│   ├── content-scout/                                   # 🔍 CONTENT SCOUT v1.2.0 — Intelligence Gatherer
│   │   ├── vault/                                       # ✅ THE vault (unified, 9 files)
│   │   │   ├── SOUL.md
│   │   │   ├── CONFIG.md
│   │   │   ├── PROCESS.md
│   │   │   ├── CADENCE.md
│   │   │   ├── RUN-LOG.md
│   │   │   ├── LEARNING-LOG.md
│   │   │   ├── STYLE-EVOLUTION.md
│   │   │   ├── SOURCES.md                               # All 15 scrapers
│   │   │   └── TRUTH-FILTER.md                          # 4-layer verification
│   │   ├── .vault-cache/                                # Local cache (24h TTL)
│   │   ├── scout.py                                     # ✅ 15 scrapers + Truth Filter
│   │   ├── scout_brain.md                               # Operational instructions
│   │   ├── scout_context_loader.py                      # ✅ Loads vault/ + source weights
│   │   ├── scout_learning_logger.py                     # ✅ Logs cycles, updates weights, commits
│   │   ├── scout-data.json                              # Scrape data
│   │   └── patch_mission_control.py                     # Patches mission-control.html
│   │
│   └── ddp/                                             # 📊 DDP PIPELINE — 5 Scoring Scrapers
│       ├── vault/                                       # ⬜ Future: Core 7 + SCORING-RULES.md
│       ├── daily_runner.py                              # ✅ Orchestrator — runs all 5 DDPs
│       ├── agent_trscode.py                             # ✅ TRScode V1.0
│       ├── agent_truscore.py                            # ✅ TRUscore V1.4
│       ├── agent_trfcast.py                             # ✅ TRFcast V1.0
│       ├── agent_tragents.py                            # ✅ TRAgents V1.0
│       ├── agent_trs.py                                 # ✅ TRSbench V2.5
│       ├── model_names.py                               # Model name mappings
│       └── models.json                                  # Model definitions
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            SHARED + DATA + ARCHIVE                   ║
│ ╚══════════════════════════════════════════════════════╝
│
├── shared/                                              # Shared across all agents
│   ├── USER.md                                          # David's prefs, CST timezone, Telegram style
│   ├── REASONING-CHECKLIST.md                           # ✅ Shared truth engine — all agents reference
│   ├── OPERATING_INSTRUCTIONS.md                        # V2.0 — Telegram pings, commit standards
│   ├── PRODUCTION_BIBLE.md                              # Production standards
│   └── TSArena_Master_Checklist_V7.md                   # Master checklist
│
├── data/                                                # DDP output data (site HTML reads these)
│   ├── trscode-data.json
│   ├── truscore-data.json
│   ├── trf-data.json
│   ├── tragent-data.json
│   ├── trs-data.json
│   └── status.json
│
├── archive/                                             # Reference docs (not actively read by agents)
│   ├── context-vault-docs/
│   │   ├── TSArena_Agent_Build_Checklist.md
│   │   ├── TSArena_Full_Structure_V4.md
│   │   ├── ddp-pipeline-vault/                          # DDP vault files (to migrate to agents/ddp/vault/)
│   │   └── tsarena-battle-generator/                    # TSArena battle-gen vault files
│   └── scripts/                                         # Old utility scripts
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            SITE FILES (GitHub Pages)                 ║
│ ╚══════════════════════════════════════════════════════╝
│
├── index.html                                           # TrainingRun.AI homepage
├── about.html
├── scores.html
├── truscore.html, trfcast.html, tragents.html           # DDP score pages
├── *-methodology.html, *-scores.html                    # DDP methodology + detailed scores
├── hq.html, mission-control.html                        # Internal dashboards
├── news.html                                            # Article index
├── day-template.html                                    # Article HTML template
├── day-001.html through day-009.html                    # Published articles
├── churn.html, deep-thought.html, frontier.html, etc.   # Special pages
├── styles.css, nav-v2.js                                # Shared CSS/JS
├── assets/                                              # Images, logos
│   ├── news/                                            # Article images
│   └── signature.png                                    # David's signature
├── scout-briefing.json                                  # Scout → Daily News handoff
├── agent_activity.json                                  # TRSitekeeper status
├── CNAME                                                # trainingrun.ai domain config
└── .gitignore
```

---

### TrainingRun.AI — Agent Definitions

#### Agent 1. TRSitekeeper — The Autonomous Site Manager ✅ v2.0 LIVE

| Field | Detail |
|---|---|
| **Role** | Autonomous AI site manager — guard, maintain, improve trainingrun.ai. Diagnose issues, make surgical edits, push to GitHub, monitor DDPs, execute David's requests without babysitting. An employee, not a chatbot. |
| **Location** | `agents/trsitekeeper/` |
| **Cadence** | On-demand via Telegram + autonomous audit 6–8 AM daily |
| **Owns** | Site management, file edits, git workflow, backup/revert, DDP health monitoring, 24-check audit system, learning from every interaction |
| **Core 7** | ✅ All in `agents/trsitekeeper/vault/` |
| **Role-specific** | CAPABILITIES.md, TASK-LOG.md |
| **Sub-agents** | DDP Pipeline (`agents/ddp/`) |
| **Model** | **Claude Sonnet 4.6** (Anthropic API) — upgraded from Sonnet 4.5 Feb 24, 2026 |
| **Telegram** | @TRSitekeeperBot |
| **Status** | ✅ v2.0 live on Mac. 24-check audit running. Vault memory active. Boots from `agents/trsitekeeper/` as of March 8 restructure. |

**v2.0 Memory Architecture — 6 Layers (loaded at boot via `sitekeeper_context_loader.py`):**

| Layer | Source | What It Provides |
|---|---|---|
| 1. **Kernel** | `vault/SOUL.md`, `vault/CONFIG.md`, `vault/PROCESS.md` | Identity, rules, autonomy gates |
| 2. **Operational** | `vault/STYLE-EVOLUTION.md`, `vault/CAPABILITIES.md`, `vault/TASK-LOG.md` | Patterns learned, what it can do |
| 3. **Episodes** | `vault/RUN-LOG.md` (last 10), `vault/LEARNING-LOG.md` (last 5), `vault/CADENCE.md` | Recent history + scheduling |
| 4. **Local Memory** | `memory/fix_patterns.json`, `memory/site_knowledge.json`, `memory/error_log.jsonl` | Fix patterns, page map, errors |
| 5. **Skills** | `skills/*.md` | CSS diagnosis, data staleness, git safety |
| 6. **Theory-of-Mind** | `memory/david_model.json` | David's identity, priorities, triggers |

**24-Check Autonomous Audit (runs daily 6–8 AM):**
7 local file checks + 4 live site checks + 5 content integrity checks + 4 security checks + 4 intelligence checks. Reports via Telegram. Logs via learning_logger. Fixed checks 001/006/014/022 on March 8.

**v2.0 Execution Files (all ✅ in `agents/trsitekeeper/`):**
`agent.py`, `brain.md`, `sitekeeper_context_loader.py`, `sitekeeper_learning_logger.py`, `sitekeeper_audit.py`, `README_AGENT.md`, `memory/david_model.json`, `memory/site_knowledge.json`, `memory/fix_patterns.json`, `memory/error_log.jsonl`, `memory/tried_fixes.jsonl`, `memory/memory_log.jsonl`, `skills/css_diagnosis.md`, `skills/data_staleness.md`, `skills/git_safety.md`

---

#### Agent 1a. DDP Pipeline — Sub-Agent: The Scoring Engine ✅ ACTIVE

| Field | Detail |
|---|---|
| **Role** | Scrape benchmark data from 60+ sources, calculate 5 DDP composite scores, push to live site daily |
| **Location** | `agents/ddp/` |
| **Parent agent** | TRSitekeeper |
| **Cadence** | Daily 4AM CST via `daily_runner.py` (macOS launchd) |
| **Owns** | All 5 DDP scrapers, scoring formulas, data pipeline, 5 output JSON files |
| **Output** | `data/trscode-data.json`, `data/truscore-data.json`, `data/trf-data.json`, `data/tragent-data.json`, `data/trs-data.json` |
| **Core 7** | ⬜ Vault files archived at `archive/context-vault-docs/ddp-pipeline-vault/` — future: `agents/ddp/vault/` with Core 7 + SCORING-RULES.md |
| **Non-agents** | `agent_truscore.py` (63K), `agent_trs.py` (64K), `agent_trfcast.py` (34K), `agent_tragents.py` (49K), `agent_trscode.py` (36K), `daily_runner.py` (5K) |
| **The 5 DDPs** | TRSbench (18 src, 7 pillars), TRUscore (9 src, 5 pillars), TRScode (8 src), TRFcast (4 platforms), TRAgents (22+ src, 6 pillars) |
| **Status** | ✅ Scrapers running daily since February 2026. Code moved to `agents/ddp/` March 8. Vault build pending. |

**IMPORTANT:** These scrapers run at 4AM daily and update the live site. They work reliably. Any changes to scoring or scraper logic must be tested with `--dry-run` first. Do not modify live scrapers without David's approval.

---

#### Agent 2. Daily News Agent — The Journalist ✅ COMPLETE

| Field | Detail |
|---|---|
| **Role** | Research AI papers daily, write article, stage for David's approval, publish |
| **Location** | `agents/daily-news/` |
| **Cadence** | Daily — event-driven by Content Scout's briefing delivery |
| **Owns** | Story selection, article writing, staging, learning, post-publish tracking |
| **Core 7** | ✅ All in `agents/daily-news/vault/` |
| **Role-specific** | ENGAGEMENT-LOG.md |
| **Sub-agents** | Content Scout (`agents/content-scout/`) |
| **Non-agents** | 13 execution files in `agents/daily-news/` |
| **Models** | Grok-3 (writing) + Grok-3-mini (story selection) |
| **Telegram** | @TRnewzBot |
| **Status** | ✅ Context vault complete — the gold standard. All other agents modeled on this build. ⚠️ Agent process not running — Content Scout delivered 10 stories March 8 but no article was drafted. **NEEDS FIX.** |

---

#### Agent 2a. Content Scout — Sub-Agent: Intelligence Gatherer ✅ LIVE v1.2.0

| Field | Detail |
|---|---|
| **Role** | Scrape AI news sources, verify with Truth Filter, produce daily briefing, learn from feedback |
| **Location** | `agents/content-scout/` |
| **Parent agent** | Daily News Agent |
| **Cadence** | Every 30 minutes (7:30AM–11PM CST), morning brief 5:30AM |
| **Owns** | News scraping, truth verification, scout-briefing.json, mission-control patches, source weight learning |
| **Core 7** | ✅ All 7 + SOURCES.md + TRUTH-FILTER.md in `agents/content-scout/vault/` |
| **Non-agents** | `scout.py`, `patch_mission_control.py`, `scout_brain.md`, `scout_context_loader.py`, `scout_learning_logger.py` |
| **Models** | llama3.1:8b (local Ollama) + xAI Grok (verification) |
| **Telegram** | @TrainingRunBot |
| **Learning loop** | Daily News Agent writes scout-feedback.json → Scout reads → logs selection → updates source weights → commits |
| **Status** | ✅ Context vault complete (9/9 files). Learning system wired and deployed March 6, 2026. Delivered 10 stories at 5:35 AM March 8. Code moved to `agents/content-scout/` March 8. |

---

### V9 Restructure Changes (March 8, 2026)

**What changed from V8:**

1. **Eliminated `context-vault/` entirely.** Each agent's vault now lives inside its own folder at `agents/*/vault/`. Code reads from, writes to, and audits the same location. No more sync issues.

2. **Unified agent directories.** Each agent folder contains vault + code + memory + skills together:
   - `web_agent/` → `agents/trsitekeeper/`
   - `daily_news_agent/` → `agents/daily-news/`
   - `content_scout/` → `agents/content-scout/`
   - Root DDP scrapers → `agents/ddp/`

3. **Resolved 4 critical path conflicts:**
   - TRSitekeeper was reading from `web_agent/vault/` but audit checked `context-vault/` → Now both point to `agents/trsitekeeper/vault/`
   - Daily News and Content Scout read from `context-vault/` while TRSitekeeper read from `web_agent/vault/` → Now each reads from its own `agents/*/vault/`
   - No sync mechanism between vault copies → Eliminated by having only one copy per agent
   - Training docs placed in unread locations → Now all agent files live where code reads them

4. **New shared/ directory** for cross-agent docs (USER.md, REASONING-CHECKLIST, OPERATING_INSTRUCTIONS).

5. **New data/ directory** for DDP output JSON files (previously at repo root).

6. **New archive/ directory** for reference docs not actively read by agents.

7. **HTML/CSS/JS stay at repo root** for GitHub Pages compatibility.

8. **Company hierarchy established:** David's AI Company at top, not the GitHub repo.

---

---

## PART 2: TS ARENA

---

### TS Arena Directory Tree (Future State — Same agents/ Pattern as TrainingRun)

```
tsarena-site/                                            # ← REPO ROOT (second property of David's AI Company)
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            AGENTS                                    ║
│ ╚══════════════════════════════════════════════════════╝
│
├── agents/
│   │
│   ├── arena-ops/                                       # 🎯 ARENA OPS — SITE MANAGER (Chief of Operations)
│   │   ├── vault/                                       # THE vault — read + write + audit (unified)
│   │   │   ├── SOUL.md                                  # Mission: orchestrate all TSArena agents
│   │   │   ├── CONFIG.md                                # Supabase, GitHub, Telegram, monitoring tools
│   │   │   ├── PROCESS.md                               # How health checks and escalations work
│   │   │   ├── CADENCE.md                               # Master schedule (what runs when)
│   │   │   ├── RUN-LOG.md                               # Log of every health check and status report
│   │   │   ├── LEARNING-LOG.md                          # Operational patterns, failure analysis
│   │   │   ├── STYLE-EVOLUTION.md                       # Reporting and coordination improvements
│   │   │   ├── HEARTBEAT.md                             # Weekly cross-agent health check with thresholds
│   │   │   └── STATUS.md                                # Current state of every system (real-time)
│   │   ├── memory/                                      # Filesystem-backed memory
│   │   │   ├── agent_health.json                        # Cross-agent status tracker
│   │   │   ├── escalation_log.jsonl                     # When things got escalated to David
│   │   │   └── david_model.json                         # Theory-of-Mind (shared format)
│   │   ├── skills/                                      # Reasoning templates
│   │   │   ├── health_check.md                          # How to diagnose agent failures
│   │   │   └── escalation_rules.md                      # When to alert David vs. self-heal
│   │   ├── arena_ops.py                                 # Main orchestrator
│   │   ├── brain.md                                     # System prompt
│   │   ├── ops_context_loader.py                        # Boot sequence — loads vault/
│   │   └── ops_learning_logger.py                       # Writes to vault/ and memory/
│   │
│   ├── battle-generator/                                # ⚔️ BATTLE GENERATOR — The Engine
│   │   ├── vault/                                       # THE vault
│   │   │   ├── SOUL.md                                  # ✅ Mission: generate fresh battles weekly
│   │   │   ├── CONFIG.md                                # ✅ API endpoints, rate limits, batch sizes
│   │   │   ├── PROCESS.md                               # How battle generation works end-to-end
│   │   │   ├── CADENCE.md                               # Weekly Sunday night + manual triggers
│   │   │   ├── RUN-LOG.md                               # ✅ Log of every generation run
│   │   │   ├── LEARNING-LOG.md                          # API failures, model refusal patterns
│   │   │   ├── STYLE-EVOLUTION.md                       # Generation strategy improvements
│   │   │   └── PAIRING-RULES.md                         # ✅ How models are matched (A/B assignment)
│   │   ├── memory/                                      # Filesystem-backed memory
│   │   │   ├── api_failures.jsonl                       # OpenRouter API failure log
│   │   │   ├── refusal_patterns.json                    # Models that refuse certain prompts
│   │   │   └── generation_stats.json                    # Batch sizes, timing, success rates
│   │   ├── generate_battles.py                          # ✅ Battle generation script
│   │   ├── battle_bot.py                                # ✅ Telegram bot (2-way battle control)
│   │   ├── brain.md                                     # System prompt
│   │   ├── battle_context_loader.py                     # Boot sequence
│   │   └── battle_learning_logger.py                    # Writes to vault/ and memory/
│   │
│   ├── model-manager/                                   # 🤖 MODEL MANAGER — The Roster
│   │   ├── vault/                                       # THE vault
│   │   │   ├── SOUL.md                                  # Mission: maintain and grow the model roster
│   │   │   ├── CONFIG.md                                # OpenRouter setup, Supabase models table
│   │   │   ├── PROCESS.md                               # How models are added, verified, deactivated
│   │   │   ├── CADENCE.md                               # Bi-weekly reviews + ad-hoc on new launches
│   │   │   ├── RUN-LOG.md                               # Log of every roster change
│   │   │   ├── LEARNING-LOG.md                          # Provider reliability, API access patterns
│   │   │   ├── STYLE-EVOLUTION.md                       # Expansion strategy improvements
│   │   │   ├── ROSTER.md                                # Master list of all 70 models with status
│   │   │   ├── EXPANSION-TRACKER.md                     # 19 models in outreach pipeline + blockers
│   │   │   ├── PROVIDER-MAP.md                          # OpenRouter slugs, API type, cost tier
│   │   │   └── CHANGELOG.md                             # When models were added/removed and why
│   │   ├── memory/                                      # Filesystem-backed memory
│   │   │   ├── provider_reliability.json                # API uptime, latency tracking per provider
│   │   │   ├── model_changelog.jsonl                    # Append-only roster change log
│   │   │   └── outreach_status.json                     # Pipeline tracking for new models
│   │   ├── model_manager.py                             # Main roster management script
│   │   ├── brain.md                                     # System prompt
│   │   ├── model_context_loader.py                      # Boot sequence
│   │   └── model_learning_logger.py                     # Writes to vault/ and memory/
│   │
│   ├── prompt-curator/                                  # 📝 PROMPT CURATOR — The Quality Gate
│   │   ├── vault/                                       # THE vault
│   │   │   ├── SOUL.md                                  # Mission: maintain quality prompt pool
│   │   │   ├── CONFIG.md                                # Supabase prompts table, category definitions
│   │   │   ├── PROCESS.md                               # How prompts are written, audited, retired
│   │   │   ├── CADENCE.md                               # Monthly audit + ad-hoc on new batches
│   │   │   ├── RUN-LOG.md                               # Log of every prompt batch and audit
│   │   │   ├── LEARNING-LOG.md                          # Prompt quality patterns, voter feedback
│   │   │   ├── STYLE-EVOLUTION.md                       # Prompt writing improvements
│   │   │   ├── COVERAGE-MAP.md                          # Category balance: current vs. target
│   │   │   ├── PROMPT-BANK.md                           # All 167 active prompts with categories
│   │   │   ├── REVIEW-QUEUE.md                          # Community submissions pipeline (future)
│   │   │   └── RETIREMENT-LOG.md                        # Prompts retired + duplicates deactivated
│   │   ├── memory/                                      # Filesystem-backed memory
│   │   │   ├── category_analytics.json                  # Usage stats per category
│   │   │   ├── voter_feedback.jsonl                     # Feedback on prompt quality from voters
│   │   │   └── retirement_decisions.json                # Why prompts were retired
│   │   ├── prompt_curator.py                            # Main curation script
│   │   ├── brain.md                                     # System prompt
│   │   ├── curator_context_loader.py                    # Boot sequence
│   │   └── curator_learning_logger.py                   # Writes to vault/ and memory/
│   │
│   ├── vote-counter/                                    # 🗳️ VOTE COUNTER — The Pulse
│   │   ├── vault/                                       # THE vault
│   │   │   ├── SOUL.md                                  # Mission: track votes, alert on milestones
│   │   │   ├── CONFIG.md                                # Supabase polling, Telegram bot config
│   │   │   ├── PROCESS.md                               # How votes are monitored and alerts triggered
│   │   │   ├── CADENCE.md                               # Real-time / continuous
│   │   │   ├── RUN-LOG.md                               # Log of milestone alerts and anomalies
│   │   │   ├── LEARNING-LOG.md                          # Voting pattern analysis
│   │   │   ├── STYLE-EVOLUTION.md                       # Alert tuning and threshold improvements
│   │   │   ├── SKILLS.md                                # Supabase polling logic, 5-vote threshold
│   │   │   └── HEARTBEAT.md                             # Voting activity health dashboard
│   │   ├── memory/                                      # Filesystem-backed memory
│   │   │   ├── milestone_log.jsonl                      # Vote milestone events
│   │   │   ├── anomaly_log.jsonl                        # Suspicious voting patterns
│   │   │   └── threshold_config.json                    # Alert thresholds (configurable)
│   │   ├── vote_counter.py                              # Main monitoring script
│   │   ├── brain.md                                     # System prompt
│   │   ├── vote_context_loader.py                       # Boot sequence
│   │   └── vote_learning_logger.py                      # Writes to vault/ and memory/
│   │
│   └── site-builder/                                    # 🏗️ SITE BUILDER — The Storefront
│       ├── vault/                                       # THE vault
│       │   ├── SOUL.md                                  # Mission: maintain and build site pages
│       │   ├── CONFIG.md                                # GitHub Pages setup, deploy process, CDN
│       │   ├── PROCESS.md                               # How pages are built, tested, deployed
│       │   ├── CADENCE.md                               # Sprint-based / as needed
│       │   ├── RUN-LOG.md                               # Log of every page build and deploy
│       │   ├── LEARNING-LOG.md                          # UX patterns, build process improvements
│       │   ├── STYLE-EVOLUTION.md                       # Design and code pattern improvements
│       │   ├── PAGES.md                                 # Every page on tsarena.ai + status
│       │   ├── BACKLOG.md                               # Features and pages to build (prioritized)
│       │   └── DESIGN-SYSTEM.md                         # Colors, fonts, components, CSS vars, brand
│       ├── memory/                                      # Filesystem-backed memory
│       │   ├── deploy_log.jsonl                         # Every deploy with timing and status
│       │   ├── ux_patterns.json                         # Learned UX patterns from feedback
│       │   └── component_library.json                   # Reusable components catalog
│       ├── site_builder.py                              # Main build/deploy script
│       ├── brain.md                                     # System prompt
│       ├── builder_context_loader.py                    # Boot sequence
│       └── builder_learning_logger.py                   # Writes to vault/ and memory/
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            SHARED + DATA                             ║
│ ╚══════════════════════════════════════════════════════╝
│
├── shared/                                              # Shared across all TS Arena agents
│   ├── USER.md                                          # David's prefs (same format as TrainingRun)
│   ├── REASONING-CHECKLIST.md                           # Shared truth engine
│   └── OPERATING_INSTRUCTIONS.md                        # Rules of engagement
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            SITE FILES (GitHub Pages)                 ║
│ ╚══════════════════════════════════════════════════════╝
│
├── index.html                                           # ✅ Landing page
├── vote.html                                            # ✅ Arena voting page
├── leaderboard.html                                     # ✅ Leaderboard
├── prompts.html                                         # ✅ Our Prompts (transparency)
├── models.html                                          # ✅ Our Models (transparency) — LIVE
├── charter.html                                         # ✅ Charter page
├── mission-control.html                                 # ✅ Internal dashboard
├── models.json                                          # Model-to-company mapping
├── assets/
│   ├── logos/                                           # Lab logos
│   └── news/                                            # Article images
├── CNAME                                                # tsarena.ai domain config
└── .gitignore
```

---

### TS Arena — Agent Definitions

#### Agent 3. Arena Ops — Chief of Operations (Site Manager)

| Field | Detail |
|---|---|
| **Role** | Orchestrator — makes sure every other TSArena agent runs on schedule. Health checks, status reporting, escalation to David. The TRSitekeeper equivalent for TS Arena. |
| **Location** | `agents/arena-ops/` |
| **Cadence** | Continuous / always-on awareness |
| **Owns** | Master schedule, cross-agent health checks, status reporting, escalation decisions |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | HEARTBEAT.md (cross-agent health with thresholds), STATUS.md (real-time system state) |
| **Reports to** | David (Telegram) → future: CEO Agent |
| **Status** | ❌ Context vault folder not built |

---

#### Agent 4. Battle Generator — The Engine ⚠️ PARTIALLY BUILT

| Field | Detail |
|---|---|
| **Role** | Generate fresh AI-vs-AI battles by calling real model APIs via OpenRouter |
| **Location** | `agents/battle-generator/` (future) — currently `generate_battles.py` + `battle_bot.py` in repo |
| **Cadence** | Weekly — Sunday 11PM EST via GitHub Actions (`0 4 * * 1`) |
| **Owns** | Battle generation script, API configs, model pairing, run logs |
| **Core 7** | SOUL ✅, CONFIG ✅, PROCESS ❌, CADENCE ❌, RUN-LOG ✅, LEARNING-LOG ❌, STYLE-EVOLUTION ❌ |
| **Role-specific** | PAIRING-RULES.md ✅ |
| **Non-agents** | `generate_battles.py`, `battle_bot.py` (Telegram 2-way control) |
| **Reports to** | Arena Ops |
| **Status** | ⚠️ Partially built — 4 of 8 vault files exist, needs Core 7 upgrade + move to agents/ structure |

**Current state (March 8, 2026):**

- ✅ `generate_battles.py` running via GitHub Actions weekly cron
- ✅ Two-way Telegram bot (`battle_bot.py`) deployed on Mac
- ✅ 250+ battles generated across multiple runs
- ✅ 70 active models, 68 with OpenRouter slugs
- ❌ Missing: PROCESS.md, CADENCE.md, LEARNING-LOG.md, STYLE-EVOLUTION.md
- Next: Upgrade vault folder to Core 7 standard, move to `agents/battle-generator/`

---

#### Agent 5. Model Manager — The Roster

| Field | Detail |
|---|---|
| **Role** | Maintain, expand, and track every AI model in the arena |
| **Location** | `agents/model-manager/` (future) |
| **Cadence** | Bi-weekly review (1st & 15th), ad-hoc when new models launch |
| **Owns** | Model roster, API access tracking, provider mapping, expansion pipeline |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | ROSTER.md, EXPANSION-TRACKER.md, PROVIDER-MAP.md, CHANGELOG.md |
| **Reports to** | Arena Ops |
| **Status** | ❌ Context vault folder not built |

**Current state (March 8, 2026):**

- 70 active models in Supabase (expanded from 50, March 4)
- 27 companies represented
- All models accessed via OpenRouter (single API layer)
- 19 models in outreach pipeline (61-A through 61-J and beyond)
- 7 models deactivated (not on OpenRouter)

**Model roster breakdown by provider:**

| Provider | Count | Notes |
|---|---|---|
| OpenAI | 8 | GPT-4o, o1, o3-mini, etc. |
| Anthropic | 6 | Claude 3.5 Sonnet through Opus 4 |
| Google DeepMind | 7 | Gemini 1.5/2.0/2.5 family |
| Meta | 5 | Llama 3.1/3.3 family |
| Mistral | 5 | Mistral Large, Small, Nemo, etc. |
| xAI | 3 | Grok-2, Grok-3, Grok-3-mini |
| DeepSeek | 3 | V3, R1, R1-distill |
| Others (19 companies) | 33 | Cohere, AI21, Perplexity, Qwen, etc. |
| **Total Active** | **70** | **27 companies** |

---

#### Agent 6. Prompt Curator — The Quality Gate

| Field | Detail |
|---|---|
| **Role** | Maintain prompt quality, balance categories, manage lifecycle |
| **Location** | `agents/prompt-curator/` (future) |
| **Cadence** | Monthly audit (1st of month), ad-hoc when new prompts are written |
| **Owns** | Prompt pool, category coverage, retirement decisions, quality standards |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | COVERAGE-MAP.md, PROMPT-BANK.md, REVIEW-QUEUE.md, RETIREMENT-LOG.md |
| **Reports to** | Arena Ops |
| **Status** | ❌ Context vault folder not built |

**Category coverage (March 8, 2026):**

| Category | Current | Target | Gap |
|---|---|---|---|
| Harm Refusal | 20 | 20 | ✅ |
| Medical Misinfo | 20 | 20 | ✅ |
| Jailbreak | 17 | 25 | +8 |
| Balanced Judgment | 15 | 20 | +5 |
| Truthfulness | 15 | 20 | +5 |
| Professional Refusal | 15 | 20 | +5 |
| Hate Speech | 15 | 15 | ✅ |
| Privacy | 10 | 15 | +5 |
| Manipulation | 10 | 15 | +5 |
| Financial Fraud | 10 | 15 | +5 |
| Child Safety | 10 | 10 | ✅ |
| Self-Harm | 10 | 10 | ✅ |
| **TOTAL** | **167** | **205** | **+38** |

---

#### Agent 7. Vote Counter — The Pulse ⚠️ ACTIVE BUT UNDOCUMENTED

| Field | Detail |
|---|---|
| **Role** | Monitor voting activity, alert on milestones, flag anomalies |
| **Location** | `agents/vote-counter/` (future) |
| **Cadence** | Real-time / continuous |
| **Owns** | Vote tracking, Telegram alerts, mission-control updates |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | SKILLS.md (Supabase polling logic, 5-vote threshold), HEARTBEAT.md (voting activity health) |
| **Reports to** | Arena Ops |
| **Status** | ❌ Context vault folder not built — agent is active but undocumented |

---

#### Agent 8. Site Builder — The Storefront

| Field | Detail |
|---|---|
| **Role** | Build and maintain all TSArena web pages |
| **Location** | `agents/site-builder/` (future) |
| **Cadence** | Sprint-based / as needed |
| **Owns** | All HTML pages, design system, feature backlog |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | PAGES.md, BACKLOG.md, DESIGN-SYSTEM.md |
| **Reports to** | Arena Ops |
| **Status** | ❌ Context vault folder not built |

**Page inventory (March 8, 2026):**

| Page | Status | Description |
|---|---|---|
| index.html | ✅ Live | Landing page |
| vote.html | ✅ Live | Arena voting page |
| leaderboard.html | ✅ Live | Model leaderboard |
| prompts.html | ✅ Live | Our Prompts (transparency) |
| charter.html | ✅ Live | Charter page |
| mission-control.html | ✅ Live | Internal dashboard |
| models.html | ✅ Live | Our Models (launched March 2026) |

---

## Operational Cadences (Both Sites)

| Cadence | What | Owner | Site | Day/Time |
|---|---|---|---|---|
| **Real-time** | Vote monitoring + Telegram alerts | Vote Counter | TS Arena | Always on |
| **Every 30 min** | AI news scraping + truth verification + learning | Content Scout | TrainingRun | 7:30AM–11PM CST |
| **Daily 4AM** | DDP scoring runs (all 5 scrapers) | DDP Pipeline | TrainingRun | 4AM CST |
| **Daily 6–8AM** | 24-check autonomous audit | TRSitekeeper | TrainingRun | 6AM CST |
| **Daily 5:30AM** | Morning intelligence brief | Content Scout → Daily News | TrainingRun | 5:30AM CST |
| **Daily morning** | Select story → write article → Telegram David | Daily News Agent | TrainingRun | ~5:40AM CST |
| **Daily morning** | Leaderboard health check | Arena Ops | TS Arena | Morning |
| **Weekly Sunday** | Generate 100+ new battles via GitHub Actions | Battle Generator | TS Arena | 11PM EST |
| **Weekly Monday** | Review battle logs, update HEARTBEAT.md | Arena Ops | TS Arena | Monday morning |
| **Weekly Sunday** | Agent learning reviews (each agent reviews own LEARNING-LOG) | All Agents | Both | Sunday |
| **Bi-weekly** | Model roster review — new models to add? | Model Manager | TS Arena | 1st & 15th |
| **Monthly** | Prompt category audit — gaps? retirements? | Prompt Curator | TS Arena | 1st of month |
| **Monthly** | Full system health report | Arena Ops | TS Arena | 1st of month |
| **Monthly** | Agent self-audits + STYLE-EVOLUTION full review | All Agents | Both | 1st of month |
| **Quarterly** | Expansion targets — model count, prompt count | Arena Ops + All | TS Arena | Quarter start |
| **On-demand** | Site fixes, edits, pushes via Telegram | TRSitekeeper | TrainingRun | Anytime (@TRSitekeeperBot) |

---

## Database Schema (Supabase — TS Arena)

### `models` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| name | text | Display name (e.g., "GPT-5") |
| lab | text | Company name (e.g., "OpenAI") |
| created_at | timestamp | When added |

### `prompts` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| text | text | The prompt scenario |
| category | text | Safety category (12 categories) |
| is_active | boolean | In active pool or retired |
| moderation_status | text | Review status |
| source | text | Who wrote it (curated / community) |
| tags | text | Additional tags |
| used_count | integer | Times used in battles |
| created_at | timestamp | When added |

### `battles` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| battle_number | integer | Sequential ID |
| prompt_id | uuid | FK → prompts |
| model_a_id | uuid | FK → models |
| model_b_id | uuid | FK → models |
| model_a_response | text | Pre-generated response from Model A |
| model_b_response | text | Pre-generated response from Model B |
| votes_a | integer | Votes for A |
| votes_b | integer | Votes for B |
| votes_tie | integer | Tie votes |
| total_votes | integer | Sum of all votes |
| is_public | boolean | Visible to voters |
| created_at | timestamp | When battle was generated |

---

## Current Numbers (as of March 8, 2026)

| Metric | Count | Target | Site |
|---|---|---|---|
| Active models in database | 70 | 100+ | TS Arena |
| Companies represented | 27 | 35+ | TS Arena |
| Models in outreach pipeline | 19 | — | TS Arena |
| Active prompts | 167 | 205+ | TS Arena |
| Prompt categories | 12 | 12+ | TS Arena |
| Total battles | 750+ | 1,000+ (growing weekly) | TS Arena |
| Daily news articles published | 9 | Daily cadence | TrainingRun |
| TrainingRun agents | 2 + 2 sub-agents | 2 + 2 sub-agents | TrainingRun |
| TSArena agents | 6 | 6 | TS Arena |
| Agents with Core 7 complete | 2 of 8 (+ 2 sub-agents) | 8 of 8 (+ sub-agents) | Both |

---

## Priority Build Order (Updated March 8, V10)

| # | Item | Agent | Status |
|---|---|---|---|
| 1–9a | Build all agents, scrapers, Content Scout, TRSitekeeper v2.0 | Multiple | ✅ Complete |
| 9b | ~~Activate TRSitekeeper on Mac~~ | TRSitekeeper | ✅ Complete (March 8) |
| 9c | ~~Restructure to agents/ hierarchy~~ | All TrainingRun | ✅ Complete (March 8) |
| 9d | ~~Fix audit checks 001/006/014/022~~ | TRSitekeeper | ✅ Complete (March 8) |
| **10** | **Fix Daily News Agent — not drafting articles** | Daily News Agent | 🔴 **NEXT** |
| 11 | TRSitekeeper autonomy improvements (Grok audit gaps) | TRSitekeeper | ⬜ After Daily News fix |
| 12 | Build DDP Pipeline vault (`agents/ddp/vault/`) | DDP Pipeline | ⬜ Sprint 4 |
| 13 | Upgrade Battle Generator to Core 7 + move to `agents/` | Battle Generator | ⬜ Sprint 4 |
| 14 | Build Core 7 for Arena Ops (TS Arena Site Manager) | Arena Ops | ⬜ Sprint 4 |
| 15 | Build Core 7 for Model Manager | Model Manager | ⬜ Sprint 4 |
| 16 | Build Core 7 for Prompt Curator | Prompt Curator | ⬜ Sprint 4 |
| 17 | Build Core 7 for Vote Counter (document the active agent) | Vote Counter | ⬜ Sprint 4 |
| 18 | Build Core 7 for Site Builder | Site Builder | ⬜ Sprint 4 |
| 19 | Write remaining 38 prompts | Prompt Curator | ⬜ Sprint 4 |
| 20 | Restructure tsarena-site repo to agents/ hierarchy | All TS Arena | ⬜ Sprint 5 |
| 21 | Community prompt submission system | Prompt Curator + Site Builder | 🔵 Future |
| 22 | Public prompt retirement/audit page | Prompt Curator + Site Builder | 🔵 Future |
| 23 | CEO / Security agents | Company-level | 🔵 Future |
| 24 | Cross-site shared context (both repos reading shared/) | Both Sites | 🔵 Future |

---

## Philosophy

> **David's AI Company operates on a principle of structured transparency and autonomous learning.** Every agent has a unified vault where it reads, writes, and audits from the same location. The file structure serves the learning loop — not the other way around. No files for the sake of files. Every file must be in a place where code actually reads it. Agents learn from their runs, improve their patterns, and escalate to David when they hit their limits. The goal is a self-sufficient ecosystem running on David's Mac, with GitHub as the source of truth and sync point.

> **The Safety Arena operates on a principle of structured transparency.** Our prompts are curated, our battles are generated from real AI model responses, and our model roster is public. We refresh our battle pool weekly to ensure the leaderboard reflects current model performance — not a one-time snapshot. Every model faces the same challenge pool under the same conditions. This is how you build safety data you can trust.

---

*This document is the single source of truth for the organization. Updated March 8, 2026 (V10) to reflect: full restructure to agents/ hierarchy for TrainingRun (V9), TS Arena restored to full detail with future-state agents/ directory tree matching TrainingRun pattern, all 6 TS Arena agents fully defined with vault + memory + skills + code structure, database schema preserved, prompt category coverage table preserved, model roster breakdown added, page inventory preserved, operational cadences merged for both sites, priority build order expanded to 24 items covering both sites, company hierarchy with build status indicators.*
