# The Safety Arena + TrainingRun.AI — Full Operational Structure

> **Version:** V4 — March 5, 2026
> **Status:** Working document — David + Claude finalizing
> **Purpose:** Single source of truth for every agent, non-agent, process, and cadence that powers TSArena + TrainingRun.AI

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

**Every SOUL.md** includes the REASONING-CHECKLIST.md integration reference from `shared-context/REASONING-CHECKLIST.md`.

**Non-agents** (scripts, scrapers, bots) are documented inside their parent agent's CONFIG.md and PROCESS.md but remain visible on the directory tree with their parent agent noted.

---

## Directory Tree

```
trainingrun-site/                                        # ← REPO ROOT
│
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            TRAININGRUN.AI                            ║
│ ╚══════════════════════════════════════════════════════╝
│
├── context-vault/
│   ├── trainingrun/                                     # ── TrainingRun.AI Context Vault ──
│   │   │
│   │   ├── org/                                         # Global identity + shared resources
│   │   │   ├── SOUL.md                                  # Identity, voice, boundaries
│   │   │   ├── USER.md                                  # David's prefs, CST timezone, Telegram style
│   │   │   ├── HEARTBEAT.md                             # Cross-site dashboard (status, reminders, health)
│   │   │   └── MEMORY.md                                # Long-term curated knowledge
│   │   │
│   │   ├── shared-context/                              # Shared docs (used by both TrainingRun + TSArena)
│   │   │   ├── THESIS.md                                # What we believe (truth + safety)
│   │   │   ├── SIGNALS.md                               # Reference intel
│   │   │   ├── FEEDBACK-LOG.md                          # Style corrections
│   │   │   ├── PRODUCTION-BIBLE.md                      # Production standards
│   │   │   ├── PROJECTS.md                              # High-level overview of both sites
│   │   │   ├── REASONING-CHECKLIST.md                   # ✅ Shared truth engine — all agents reference this
│   │   │   └── TSArena_Master_Checklist_V7.md           # ✅ Master checklist — source of truth
│   │   │
│   │   ├── agents/                                      # ── TrainingRun Agents ──
│   │   │   │
│   │   │   ├── daily-news/                              # 📰 DAILY NEWS AGENT ✅ BUILT+TESTED
│   │   │   │   ├── SOUL.md                              # ✅ Mission: research, write, stage daily articles
│   │   │   │   ├── CONFIG.md                            # ✅ arXiv sources, article format, image handling
│   │   │   │   ├── PROCESS.md                           # ✅ Full 15-step workflow with human approval gate
│   │   │   │   ├── CADENCE.md                           # ✅ Daily schedule + Telegram triggers + rhythms
│   │   │   │   ├── RUN-LOG.md                           # ✅ Paper-by-paper publish history (001–007)
│   │   │   │   ├── LEARNING-LOG.md                      # ✅ Raw memory — post-mortems starting Paper 008
│   │   │   │   └── STYLE-EVOLUTION.md                   # ✅ Curated improvement rules + confidence levels
│   │   │   │
│   │   │   ├── content-scout/                           # 🔍 CONTENT SCOUT v1.2.0 ✅ LIVE
│   │   │   │   ├── SOUL.md                              # Mission: scrape, verify, deliver AI news
│   │   │   │   ├── CONFIG.md                            # 15 scrapers, Ollama + Grok config, Telegram
│   │   │   │   ├── PROCESS.md                           # Scrape → filter → verify → deliver workflow
│   │   │   │   ├── CADENCE.md                           # Every 30 min (7AM–11PM CST), morning brief 5:30AM
│   │   │   │   ├── RUN-LOG.md                           # Log of every scrape cycle
│   │   │   │   ├── LEARNING-LOG.md                      # Source reliability tracking, filter accuracy
│   │   │   │   ├── STYLE-EVOLUTION.md                   # Story selection quality patterns
│   │   │   │   ├── SOURCES.md                           # All 15 scrapers: URLs, reliability, refresh rates
│   │   │   │   └── TRUTH-FILTER.md                      # 4-layer verification process documented
│   │   │   │
│   │   │   ├── ddp-pipeline/                            # 📊 DDP PIPELINE (5 Data-Driven Pillars)
│   │   │   │   ├── SOUL.md                              # Mission: scrape benchmarks, calculate scores
│   │   │   │   ├── CONFIG.md                            # All 5 scrapers, sources, API endpoints, cron
│   │   │   │   ├── PROCESS.md                           # Scrape → score → push workflow
│   │   │   │   ├── CADENCE.md                           # Daily 4AM cron via daily_runner.py
│   │   │   │   ├── RUN-LOG.md                           # Log of every scoring run
│   │   │   │   ├── LEARNING-LOG.md                      # Scraper failures, data quality issues
│   │   │   │   ├── STYLE-EVOLUTION.md                   # Scoring methodology improvements
│   │   │   │   └── SCORING-RULES.md                     # How scores are calculated per DDP, formulas
│   │   │   │
│   │   │   └── trs-site-manager/                        # 🌐 TRS SITE MANAGER (Sonnet 4.5)
│   │   │       ├── SOUL.md                              # Mission: maintain and manage TrainingRun.AI
│   │   │       ├── CONFIG.md                            # Sonnet 4.5 config, web_agent setup, capabilities
│   │   │       ├── PROCESS.md                           # How site management tasks are executed
│   │   │       ├── CADENCE.md                           # When it runs, task triggers
│   │   │       ├── RUN-LOG.md                           # Log of every task executed
│   │   │       ├── LEARNING-LOG.md                      # Task outcomes, efficiency tracking
│   │   │       ├── STYLE-EVOLUTION.md                   # Site management patterns learned
│   │   │       ├── CAPABILITIES.md                      # What this Sonnet 4.5 agent can do + limits
│   │   │       └── TASK-LOG.md                          # What it's been asked to do vs. should be doing
│   │   │
│   │   ├── non-agents/                                  # ── TrainingRun Non-Agents ──
│   │   │   │                                            # (Scripts, scrapers, bots — no Core 7)
│   │   │   │                                            # (Documented in parent agent's CONFIG + PROCESS)
│   │   │   │
│   │   │   ├── daily_news_agent/                        # 📰 Execution files for Daily News Agent
│   │   │   │   │                                        #    Parent: trainingrun/agents/daily-news/
│   │   │   │   ├── main.py                              # Orchestrator + Telegram bot (@TRnewzBot)
│   │   │   │   ├── config.py                            # All settings, paths, API config
│   │   │   │   ├── context_loader.py                    # Reads vault files (SOUL.md, USER.md, etc.)
│   │   │   │   ├── story_selector.py                    # Grok-3-mini selects best story
│   │   │   │   ├── article_writer.py                    # Grok-3 writes article in David's voice
│   │   │   │   ├── html_stager.py                       # Generates day-NNN.html from template
│   │   │   │   ├── github_publisher.py                  # Publishes via GitHub REST API
│   │   │   │   ├── telegram_handler.py                  # Sends drafts, receives approval commands
│   │   │   │   ├── learning_logger.py                   # Logs runs + learns from feedback
│   │   │   │   ├── requirements.txt                     # Python dependencies
│   │   │   │   ├── .env.example                         # Template for credentials
│   │   │   │   └── com.trainingrun.daily-news.plist     # macOS launchd service definition
│   │   │   │
│   │   │   ├── content_scout/                           # 🔍 Execution files for Content Scout
│   │   │   │   │                                        #    Parent: trainingrun/agents/content-scout/
│   │   │   │   ├── scout.py                             # 15 scrapers, 4-layer Truth Filter (2084 lines)
│   │   │   │   ├── patch_mission_control.py             # Patches mission-control.html with scout data
│   │   │   │   └── scout_brain.md                       # Scout operational instructions
│   │   │   │
│   │   │   ├── ddp-scripts/                             # 📊 Execution files for DDP Pipeline
│   │   │   │   │                                        #    Parent: trainingrun/agents/ddp-pipeline/
│   │   │   │   ├── agent_truscore.py                    # TRUscore V1.4 scraper/scorer
│   │   │   │   ├── agent_trs.py                         # TRS DDP scraper
│   │   │   │   ├── agent_trfcast.py                     # TRFcast DDP scraper
│   │   │   │   ├── agent_tragents.py                    # TRAgents DDP scraper
│   │   │   │   ├── agent_trscode.py                     # TRScode DDP scraper
│   │   │   │   └── daily_runner.py                      # Orchestrator — runs all 5 DDPs daily
│   │   │   │
│   │   │   └── web_agent/                               # 🌐 Execution files for TRS Site Manager
│   │   │       │                                        #    Parent: trainingrun/agents/trs-site-manager/
│   │   │       └── (Sonnet 4.5 web agent runtime)       # Browser automation, site management
│   │   │
│   │   └── memory/                                      # ── TrainingRun Memory ──
│   │       ├── 2026-03-02.md                            # Daily memory logs
│   │       ├── ...
│   │       └── curated/                                 # Summarized weekly/monthly takeaways
│   │
│   │
│   │ ╔══════════════════════════════════════════════════╗
│   │ ║            TS ARENA                              ║
│   │ ╚══════════════════════════════════════════════════╝
│   │
│   └── tsarena/                                         # ── TS Arena Context Vault ──
│       │
│       ├── agents/                                      # ── TS Arena Agents ──
│       │   │
│       │   ├── arena-ops/                               # 🎯 CHIEF OF OPERATIONS
│       │   │   ├── SOUL.md                              # Mission: orchestrate all TSArena agents
│       │   │   ├── CONFIG.md                            # Supabase, GitHub, Telegram, monitoring tools
│       │   │   ├── PROCESS.md                           # How health checks and escalations work
│       │   │   ├── CADENCE.md                           # Master schedule (what runs when)
│       │   │   ├── RUN-LOG.md                           # Log of every health check and status report
│       │   │   ├── LEARNING-LOG.md                      # Operational patterns, failure analysis
│       │   │   ├── STYLE-EVOLUTION.md                   # Reporting and coordination improvements
│       │   │   ├── HEARTBEAT.md                         # Weekly cross-agent health check with thresholds
│       │   │   └── STATUS.md                            # Current state of every system (real-time)
│       │   │
│       │   ├── battle-generator/                        # ⚔️ BATTLE GENERATION PIPELINE ✅ ACTIVE
│       │   │   ├── SOUL.md                              # ✅ Mission: generate fresh battles weekly
│       │   │   ├── CONFIG.md                            # ✅ API endpoints, rate limits, batch sizes
│       │   │   ├── PROCESS.md                           # How battle generation works end-to-end
│       │   │   ├── CADENCE.md                           # Weekly Sunday night + manual triggers
│       │   │   ├── RUN-LOG.md                           # ✅ Log of every generation run
│       │   │   ├── LEARNING-LOG.md                      # API failures, model refusal patterns
│       │   │   ├── STYLE-EVOLUTION.md                   # Generation strategy improvements
│       │   │   └── PAIRING-RULES.md                     # ✅ How models are matched (A/B assignment)
│       │   │
│       │   ├── model-manager/                           # 🤖 MODEL ROSTER & EXPANSION
│       │   │   ├── SOUL.md                              # Mission: maintain and grow the model roster
│       │   │   ├── CONFIG.md                            # OpenRouter setup, Supabase models table
│       │   │   ├── PROCESS.md                           # How models are added, verified, deactivated
│       │   │   ├── CADENCE.md                           # Bi-weekly reviews + ad-hoc on new launches
│       │   │   ├── RUN-LOG.md                           # Log of every roster change
│       │   │   ├── LEARNING-LOG.md                      # Provider reliability, API access patterns
│       │   │   ├── STYLE-EVOLUTION.md                   # Expansion strategy improvements
│       │   │   ├── ROSTER.md                            # Master list of all 70 models with status
│       │   │   ├── EXPANSION-TRACKER.md                 # 19 models in outreach pipeline + blockers
│       │   │   ├── PROVIDER-MAP.md                      # OpenRouter slugs, API type, cost tier
│       │   │   └── CHANGELOG.md                         # When models were added/removed and why
│       │   │
│       │   ├── prompt-curator/                          # 📝 PROMPT POOL MANAGEMENT
│       │   │   ├── SOUL.md                              # Mission: maintain quality prompt pool
│       │   │   ├── CONFIG.md                            # Supabase prompts table, category definitions
│       │   │   ├── PROCESS.md                           # How prompts are written, audited, retired
│       │   │   ├── CADENCE.md                           # Monthly audit + ad-hoc on new batches
│       │   │   ├── RUN-LOG.md                           # Log of every prompt batch and audit
│       │   │   ├── LEARNING-LOG.md                      # Prompt quality patterns, voter feedback
│       │   │   ├── STYLE-EVOLUTION.md                   # Prompt writing improvements
│       │   │   ├── COVERAGE-MAP.md                      # Category balance: current vs. target
│       │   │   ├── PROMPT-BANK.md                       # All 167 active prompts with categories
│       │   │   ├── REVIEW-QUEUE.md                      # Community submissions pipeline (future)
│       │   │   └── RETIREMENT-LOG.md                    # Prompts retired + duplicates deactivated
│       │   │
│       │   ├── vote-counter/                            # 🗳️ VOTE MONITORING ✅ ACTIVE
│       │   │   ├── SOUL.md                              # Mission: track votes, alert on milestones
│       │   │   ├── CONFIG.md                            # Supabase polling, Telegram bot config
│       │   │   ├── PROCESS.md                           # How votes are monitored and alerts triggered
│       │   │   ├── CADENCE.md                           # Real-time / continuous
│       │   │   ├── RUN-LOG.md                           # Log of milestone alerts and anomalies
│       │   │   ├── LEARNING-LOG.md                      # Voting pattern analysis
│       │   │   ├── STYLE-EVOLUTION.md                   # Alert tuning and threshold improvements
│       │   │   ├── SKILLS.md                            # Supabase polling logic, 5-vote threshold
│       │   │   └── HEARTBEAT.md                         # Voting activity health dashboard
│       │   │
│       │   └── site-builder/                            # 🏷️ FRONTEND & PAGES
│       │       ├── SOUL.md                              # Mission: maintain and build site pages
│       │       ├── CONFIG.md                            # GitHub Pages setup, deploy process, CDN
│       │       ├── PROCESS.md                           # How pages are built, tested, deployed
│       │       ├── CADENCE.md                           # Sprint-based / as needed
│       │       ├── RUN-LOG.md                           # Log of every page build and deploy
│       │       ├── LEARNING-LOG.md                      # UX patterns, build process improvements
│       │       ├── STYLE-EVOLUTION.md                   # Design and code pattern improvements
│       │       ├── PAGES.md                             # Every page on tsarena.ai + status
│       │       ├── BACKLOG.md                           # Features and pages to build (prioritized)
│       │       └── DESIGN-SYSTEM.md                     # Colors, fonts, components, CSS vars, brand
│       │
│       ├── non-agents/                                  # ── TS Arena Non-Agents ──
│       │   │                                            # (Scripts, bots — no Core 7)
│       │   │                                            # (Documented in parent agent's CONFIG + PROCESS)
│       │   │
│       │   ├── generate_battles.py                      # ⚔️ Battle generation script
│       │   │                                            #    Parent: tsarena/agents/battle-generator/
│       │   └── battle_bot.py                            # ⚔️ Telegram bot (2-way battle control)
│       │                                                #    Parent: tsarena/agents/battle-generator/
│       │
│       └── memory/                                      # ── TS Arena Memory ──
│           ├── 2026-03-02.md                            # Daily memory logs
│           ├── ...
│           └── curated/                                 # Summarized weekly/monthly takeaways
│
│
│ ╔══════════════════════════════════════════════════════╗
│ ║            SITE FILES                                ║
│ ╚══════════════════════════════════════════════════════╝
│
├── day-template.html                                    # Article HTML template (Daily News Agent)
├── news.html                                            # Article index page (Daily News Agent)
│
└── tsarena/                                             # ← TSArena live site (GitHub Pages)
    ├── index.html                                       # Landing page
    ├── vote.html                                        # Arena voting page
    ├── leaderboard.html                                 # Leaderboard
    ├── prompts.html                                     # Our Prompts (transparency)
    ├── models.html                                      # ✅ Our Models (transparency) — LIVE
    ├── charter.html                                     # Charter page
    ├── mission-control.html                             # Internal dashboard
    ├── models.json                                      # Model-to-company mapping
    └── assets/
        ├── logos/                                       # Lab logos
        ├── news/                                        # Article images
        └── signature.png                                # David's signature for articles
```

---

## TrainingRun.AI — Agent Definitions

### 1. Daily News Agent — The Journalist ✅ COMPLETE

| Field | Detail |
|---|---|
| **Role** | Research AI papers daily, write article, stage for David's approval, publish |
| **Cadence** | Daily — event-driven by Content Scout's Telegram delivery |
| **Owns** | Story selection, article writing, staging, learning, post-publish tracking |
| **Core 7** | ✅ All 7 files built and pushed to GitHub |
| **Role-specific** | None — Core 7 only |
| **Non-agents** | `daily_news_agent/` (12 execution files), `@TRnewzBot` (Telegram bot) |
| **Models** | Grok-3 (writing) + Grok-3-mini (story selection) |
| **Status** | ✅ Context vault complete — the gold standard. All other agents modeled on this build. |

---

### 2. Content Scout — Intelligence Gatherer ✅ LIVE v1.2.0

| Field | Detail |
|---|---|
| **Role** | Scrape AI news sources, verify with Truth Filter, produce daily briefing |
| **Cadence** | Every 30 minutes (7AM–11PM CST), morning brief 5:30AM |
| **Owns** | News scraping, truth verification, scout-briefing.json, mission-control patches |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | SOURCES.md, TRUTH-FILTER.md |
| **Non-agents** | `content_scout/scout.py`, `patch_mission_control.py` |
| **Models** | llama3.1:8b (local Ollama) + xAI Grok (verification) |
| **Telegram** | @TrainingRunBot |
| **Status** | ❌ Context vault folder not built (agent is active but undocumented) |

---

### 3. DDP Pipeline — The Scoring Engine ✅ ACTIVE

| Field | Detail |
|---|---|
| **Role** | Scrape benchmark data from 9 sources, calculate TRUscore V1.4 + other DDPs |
| **Cadence** | Daily 4AM CST via `daily_runner.py` |
| **Owns** | All 5 DDP scrapers, scoring formulas, data pipeline |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | SCORING-RULES.md |
| **Non-agents** | `agent_truscore.py`, `agent_trs.py`, `agent_trfcast.py`, `agent_tragents.py`, `agent_trscode.py`, `daily_runner.py` |
| **Status** | ❌ Context vault folder not built (agent is active but undocumented) |

---

### 4. TRS Site Manager — The Web Agent ✅ ACTIVE

| Field | Detail |
|---|---|
| **Role** | Maintain and manage TrainingRun.AI via browser automation |
| **Cadence** | On-demand / task-driven |
| **Owns** | Site management tasks, page updates, deployment verification |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | CAPABILITIES.md, TASK-LOG.md |
| **Non-agents** | `web_agent/` (Sonnet 4.5 runtime) |
| **Model** | Claude Sonnet 4.5 |
| **Status** | ❌ Context vault folder not built (agent is active but underutilized) |

---

## TS Arena — Agent Definitions

### 5. Arena Ops — Chief of Operations

| Field | Detail |
|---|---|
| **Role** | Orchestrator — makes sure every other TSArena agent runs on schedule |
| **Cadence** | Continuous / always-on awareness |
| **Owns** | Master schedule, cross-agent health checks, status reporting |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | HEARTBEAT.md (cross-agent health), STATUS.md (real-time system state) |
| **Status** | ❌ Context vault folder not built |

---

### 6. Battle Generator — The Engine ✅ ACTIVE

| Field | Detail |
|---|---|
| **Role** | Generate fresh AI-vs-AI battles by calling real model APIs via OpenRouter |
| **Cadence** | Weekly — Sunday 11PM EST via GitHub Actions (`0 4 * * 1`) |
| **Owns** | Battle generation script, API configs, model pairing, run logs |
| **Core 7** | SOUL ✅, CONFIG ✅, PROCESS ❌, CADENCE ❌, RUN-LOG ✅, LEARNING-LOG ❌, STYLE-EVOLUTION ❌ |
| **Role-specific** | PAIRING-RULES.md ✅ |
| **Non-agents** | `generate_battles.py`, `battle_bot.py` (Telegram 2-way control) |
| **Status** | ⚠️ Partially built — 4 of 8 files exist, needs Core 7 upgrade |

**Current state (March 5, 2026):**
- ✅ `generate_battles.py` running via GitHub Actions weekly cron
- ✅ Two-way Telegram bot (`battle_bot.py`) deployed on Mac
- ✅ 250+ battles generated across multiple runs
- ✅ 70 active models, 68 with OpenRouter slugs
- Next: Upgrade vault folder to Core 7 standard

---

### 7. Model Manager — The Roster

| Field | Detail |
|---|---|
| **Role** | Maintain, expand, and track every AI model in the arena |
| **Cadence** | Bi-weekly review (1st & 15th), ad-hoc when new models launch |
| **Owns** | Model roster, API access tracking, provider mapping, expansion pipeline |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | ROSTER.md, EXPANSION-TRACKER.md, PROVIDER-MAP.md, CHANGELOG.md |
| **Status** | ❌ Context vault folder not built |

**Current state (March 5, 2026):**
- 70 active models in Supabase (expanded from 50, March 4)
- 27 companies represented
- All models accessed via OpenRouter (single API layer)
- 19 models in outreach pipeline (61-A through 61-J)
- 7 models deactivated (not on OpenRouter)

---

### 8. Prompt Curator — The Quality Gate

| Field | Detail |
|---|---|
| **Role** | Maintain prompt quality, balance categories, manage lifecycle |
| **Cadence** | Monthly audit (1st of month), ad-hoc when new prompts are written |
| **Owns** | Prompt pool, category coverage, retirement decisions, quality standards |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | COVERAGE-MAP.md, PROMPT-BANK.md, REVIEW-QUEUE.md, RETIREMENT-LOG.md |
| **Status** | ❌ Context vault folder not built |

**Category coverage (March 5, 2026):**

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

### 9. Vote Counter — The Pulse ✅ ACTIVE

| Field | Detail |
|---|---|
| **Role** | Monitor voting activity, alert on milestones, flag anomalies |
| **Cadence** | Real-time / continuous |
| **Owns** | Vote tracking, Telegram alerts, mission-control updates |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | SKILLS.md, HEARTBEAT.md |
| **Status** | ❌ Context vault folder not built (agent is active but undocumented) |

---

### 10. Site Builder — The Storefront

| Field | Detail |
|---|---|
| **Role** | Build and maintain all TSArena web pages |
| **Cadence** | Sprint-based / as needed |
| **Owns** | All HTML pages, design system, feature backlog |
| **Core 7** | SOUL, CONFIG, PROCESS, CADENCE, RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION |
| **Role-specific** | PAGES.md, BACKLOG.md, DESIGN-SYSTEM.md |
| **Status** | ❌ Context vault folder not built |

**Page inventory (March 5, 2026):**

| Page | Status |
|---|---|
| index.html | ✅ Live |
| vote.html | ✅ Live |
| leaderboard.html | ✅ Live |
| prompts.html | ✅ Live |
| charter.html | ✅ Live |
| mission-control.html | ✅ Live |
| models.html | ✅ Live (launched March 2026) |

---

## Operational Cadences

| Cadence | What | Owner | Day/Time |
|---|---|---|---|
| **Real-time** | Vote monitoring + Telegram alerts | Vote Counter | Always on |
| **Every 30 min** | AI news scraping + truth verification | Content Scout | 7AM–11PM CST |
| **Daily 4AM** | DDP scoring runs (all 5 scrapers) | DDP Pipeline | 4AM CST |
| **Daily 5:30AM** | Morning intelligence brief | Content Scout | 5:30 AM CST |
| **Daily morning** | Select story → write article → Telegram David | Daily News Agent | ~5:40AM CST |
| **Daily morning** | Leaderboard health check | Arena Ops | Morning |
| **Weekly Sunday** | Generate 100+ new battles via GitHub Actions | Battle Generator | 11PM EST |
| **Weekly Monday** | Review battle logs, update HEARTBEAT.md | Arena Ops | Monday morning |
| **Weekly Sunday** | Agent learning reviews (each agent reviews own LEARNING-LOG) | All Agents | Sunday |
| **Bi-weekly** | Model roster review — new models to add? | Model Manager | 1st & 15th |
| **Monthly** | Prompt category audit — gaps? retirements? | Prompt Curator | 1st of month |
| **Monthly** | Full system health report | Arena Ops | 1st of month |
| **Monthly** | Agent self-audits + STYLE-EVOLUTION full review | All Agents | 1st of month |
| **Quarterly** | Expansion targets — model count, prompt count | Arena Ops + All | Quarter start |

---

## Database Schema (Supabase)

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

## Current Numbers (as of March 5, 2026)

| Metric | Count | Target |
|---|---|---|
| Active models in database | 70 | 100+ |
| Companies represented | 27 | 35+ |
| Models in outreach pipeline | 19 | — |
| Active prompts | 167 | 205+ |
| Prompt categories | 12 | 12+ |
| Total battles | 750+ | 1,000+ (growing weekly) |
| Daily news articles published | 7 | Daily cadence |
| Agents with Core 7 complete | 1 of 10 | 10 of 10 |

---

## Priority Build Order (Updated March 5, V4)

| # | Item | Agent | Status |
|---|---|---|---|
| 1 | ~~Build `generate_battles.py` pipeline~~ | Battle Generator | ✅ Complete |
| 2 | ~~Set up weekly cron/schedule~~ | Battle Generator | ✅ Complete |
| 3 | ~~Audit and document all API keys/access~~ | Model Manager | ✅ Complete |
| 4 | ~~Build Daily News Agent~~ | Daily News Agent | ✅ Complete |
| 5 | ~~Build `models.html` transparency page~~ | Site Builder | ✅ Complete |
| 6 | ~~Expand model roster to 70~~ | Model Manager | ✅ Complete |
| 7 | ~~Write 43 new prompts for thin categories~~ | Prompt Curator | ✅ Complete |
| 8 | **Build Core 7 for all 10 agents** | All Agents | 🔴 IN PROGRESS |
| 9 | Upgrade Battle Generator to Core 7 | Battle Generator | ⬝ Next |
| 10 | Add REASONING-CHECKLIST to all SOUL.md files | All Agents | ⬝ (part of Core 7 build) |
| 11 | First live Daily News Agent run | Daily News Agent | ⬝ Next |
| 12 | Write remaining 38 prompts | Prompt Curator | ⬝ Sprint 4 |
| 13 | Community prompt submission system | Prompt Curator + Site Builder | 🔵 Future |
| 14 | Public prompt retirement/audit page | Prompt Curator + Site Builder | 🔵 Future |

---

## Philosophy

> **The Safety Arena operates on a principle of structured transparency.** Our prompts are curated, our battles are generated from real AI model responses, and our model roster is public. We refresh our battle pool weekly to ensure the leaderboard reflects current model performance — not a one-time snapshot. Every model faces the same challenge pool under the same conditions. This is how you build safety data you can trust.

---

*This document is the single source of truth for the organization. Updated March 5, 2026 (V4) to reflect: clean TrainingRun / TS Arena separation, non-agents grouped under their product with parent agent references, separate context vaults and memory per product.*
