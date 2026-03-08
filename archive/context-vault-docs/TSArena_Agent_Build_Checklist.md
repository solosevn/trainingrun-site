# TSArena + TrainingRun.AI — Full Build Checklist

> **Version:** V1 — March 5, 2026
> **Purpose:** Track every file that needs to be built for all 10 agents + all non-agents
> **Standard:** Core 7 files per agent + role-specific files + non-agent execution code

---

## Legend

- ✅ = Built and pushed to GitHub
- ⚠️ = Exists but needs upgrade/rewrite
- ⬜ = Not started
- 🔵 = Future (not in current sprint)

---

## TrainingRun.AI Agents

### 1. Daily News Agent — ✅ COMPLETE (Gold Standard)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ✅ | Mission, identity, REASONING-CHECKLIST ref |
| 2 | CONFIG.md | ✅ | arXiv sources, article format, image handling |
| 3 | PROCESS.md | ✅ | Full 15-step workflow with human approval gate |
| 4 | CADENCE.md | ✅ | Daily schedule + Telegram triggers + rhythms |
| 5 | RUN-LOG.md | ✅ | Paper-by-paper publish history (001–007) |
| 6 | LEARNING-LOG.md | ✅ | Raw memory — post-mortems starting Paper 008 |
| 7 | STYLE-EVOLUTION.md | ✅ | Curated improvement rules + confidence levels |

**Core 7: 7/7 ✅**

---

### 2. Content Scout — ❌ UNDOCUMENTED (Agent is LIVE v1.2.0)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: scrape, verify, deliver AI news |
| 2 | CONFIG.md | ⬜ | 15 scrapers, Ollama + Grok config, Telegram |
| 3 | PROCESS.md | ⬜ | Scrape → filter → verify → deliver workflow |
| 4 | CADENCE.md | ⬜ | Every 30 min (7AM–11PM CST), morning brief 5:30AM |
| 5 | RUN-LOG.md | ⬜ | Log of every scrape cycle |
| 6 | LEARNING-LOG.md | ⬜ | Source reliability tracking, filter accuracy |
| 7 | STYLE-EVOLUTION.md | ⬜ | Story selection quality patterns |
| 8 | SOURCES.md | ⬜ | All 15 scrapers: URLs, reliability, refresh rates |
| 9 | TRUTH-FILTER.md | ⬜ | 4-layer verification process documented |

**Core 7: 0/7 | Role-specific: 0/2**

---

### 3. DDP Pipeline — ❌ UNDOCUMENTED (Agent is ACTIVE)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: scrape benchmarks, calculate scores |
| 2 | CONFIG.md | ⬜ | All 5 scrapers, sources, API endpoints, cron |
| 3 | PROCESS.md | ⬜ | Scrape → score → push workflow |
| 4 | CADENCE.md | ⬜ | Daily 4AM cron via daily_runner.py |
| 5 | RUN-LOG.md | ⬜ | Log of every scoring run |
| 6 | LEARNING-LOG.md | ⬜ | Scraper failures, data quality issues |
| 7 | STYLE-EVOLUTION.md | ⬜ | Scoring methodology improvements |
| 8 | SCORING-RULES.md | ⬜ | How scores are calculated per DDP, formulas |

**Core 7: 0/7 | Role-specific: 0/1**

---

### 4. TRS Site Manager — ❌ UNDOCUMENTED (Agent is ACTIVE)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: maintain and manage TrainingRun.AI |
| 2 | CONFIG.md | ⬜ | Sonnet 4.5 config, web_agent setup, capabilities |
| 3 | PROCESS.md | ⬜ | How site management tasks are executed |
| 4 | CADENCE.md | ⬜ | When it runs, task triggers |
| 5 | RUN-LOG.md | ⬜ | Log of every task executed |
| 6 | LEARNING-LOG.md | ⬜ | Task outcomes, efficiency tracking |
| 7 | STYLE-EVOLUTION.md | ⬜ | Site management patterns learned |
| 8 | CAPABILITIES.md | ⬜ | What this Sonnet 4.5 agent can do + limits |
| 9 | TASK-LOG.md | ⬜ | What it's been asked to do vs. should be doing |

**Core 7: 0/7 | Role-specific: 0/2**

---

## TS Arena Agents

### 5. Arena Ops — ❌ NOT BUILT

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: orchestrate all TSArena agents |
| 2 | CONFIG.md | ⬜ | Supabase, GitHub, Telegram, monitoring tools |
| 3 | PROCESS.md | ⬜ | How health checks and escalations work |
| 4 | CADENCE.md | ⬜ | Master schedule (what runs when) |
| 5 | RUN-LOG.md | ⬜ | Log of every health check and status report |
| 6 | LEARNING-LOG.md | ⬜ | Operational patterns, failure analysis |
| 7 | STYLE-EVOLUTION.md | ⬜ | Reporting and coordination improvements |
| 8 | HEARTBEAT.md | ⬜ | Weekly cross-agent health check with thresholds |
| 9 | STATUS.md | ⬜ | Current state of every system (real-time) |

**Core 7: 0/7 | Role-specific: 0/2**

---

### 6. Battle Generator — ⚠️ PARTIALLY BUILT (Agent is ACTIVE)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ✅ | Mission: generate fresh battles weekly |
| 2 | CONFIG.md | ✅ | API endpoints, rate limits, batch sizes |
| 3 | PROCESS.md | ⬜ | How battle generation works end-to-end |
| 4 | CADENCE.md | ⬜ | Weekly Sunday night + manual triggers |
| 5 | RUN-LOG.md | ✅ | Log of every generation run |
| 6 | LEARNING-LOG.md | ⬜ | API failures, model refusal patterns |
| 7 | STYLE-EVOLUTION.md | ⬜ | Generation strategy improvements |
| 8 | PAIRING-RULES.md | ✅ | How models are matched (A/B assignment) |

**Core 7: 3/7 | Role-specific: 1/1**

---

### 7. Model Manager — ❌ NOT BUILT

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: maintain and grow model roster |
| 2 | CONFIG.md | ⬜ | OpenRouter setup, Supabase models table |
| 3 | PROCESS.md | ⬜ | How models are added, verified, deactivated |
| 4 | CADENCE.md | ⬜ | Bi-weekly reviews + ad-hoc on new launches |
| 5 | RUN-LOG.md | ⬜ | Log of every roster change |
| 6 | LEARNING-LOG.md | ⬜ | Provider reliability, API access patterns |
| 7 | STYLE-EVOLUTION.md | ⬜ | Expansion strategy improvements |
| 8 | ROSTER.md | ⬜ | Master list of all 70 models with status |
| 9 | EXPANSION-TRACKER.md | ⬜ | 19 models in outreach pipeline + blockers |
| 10 | PROVIDER-MAP.md | ⬜ | OpenRouter slugs, API type, cost tier |
| 11 | CHANGELOG.md | ⬜ | When models were added/removed and why |

**Core 7: 0/7 | Role-specific: 0/4**

---

### 8. Prompt Curator — ❌ NOT BUILT

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: maintain quality prompt pool |
| 2 | CONFIG.md | ⬜ | Supabase prompts table, category definitions |
| 3 | PROCESS.md | ⬜ | How prompts are written, audited, retired |
| 4 | CADENCE.md | ⬜ | Monthly audit + ad-hoc on new batches |
| 5 | RUN-LOG.md | ⬜ | Log of every prompt batch and audit |
| 6 | LEARNING-LOG.md | ⬜ | Prompt quality patterns, voter feedback |
| 7 | STYLE-EVOLUTION.md | ⬜ | Prompt writing improvements |
| 8 | COVERAGE-MAP.md | ⬜ | Category balance: current vs. target |
| 9 | PROMPT-BANK.md | ⬜ | All 167 active prompts with categories |
| 10 | REVIEW-QUEUE.md | 🔵 | Community submissions pipeline (future) |
| 11 | RETIREMENT-LOG.md | ⬜ | Prompts retired + duplicates deactivated |

**Core 7: 0/7 | Role-specific: 0/4**

---

### 9. Vote Counter — ❌ UNDOCUMENTED (Agent is ACTIVE)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: track votes, alert on milestones |
| 2 | CONFIG.md | ⬜ | Supabase polling, Telegram bot config |
| 3 | PROCESS.md | ⬜ | How votes are monitored and alerts triggered |
| 4 | CADENCE.md | ⬜ | Real-time / continuous |
| 5 | RUN-LOG.md | ⬜ | Log of milestone alerts and anomalies |
| 6 | LEARNING-LOG.md | ⬜ | Voting pattern analysis |
| 7 | STYLE-EVOLUTION.md | ⬜ | Alert tuning and threshold improvements |
| 8 | SKILLS.md | ⬜ | Supabase polling logic, 5-vote threshold |
| 9 | HEARTBEAT.md | ⬜ | Voting activity health dashboard |

**Core 7: 0/7 | Role-specific: 0/2**

---

### 10. Site Builder — ❌ NOT BUILT

| # | File | Status | Notes |
|---|---|---|---|
| 1 | SOUL.md | ⬜ | Mission: maintain and build site pages |
| 2 | CONFIG.md | ⬜ | GitHub Pages setup, deploy process, CDN |
| 3 | PROCESS.md | ⬜ | How pages are built, tested, deployed |
| 4 | CADENCE.md | ⬜ | Sprint-based / as needed |
| 5 | RUN-LOG.md | ⬜ | Log of every page build and deploy |
| 6 | LEARNING-LOG.md | ⬜ | UX patterns, build process improvements |
| 7 | STYLE-EVOLUTION.md | ⬜ | Design and code pattern improvements |
| 8 | PAGES.md | ⬜ | Every page on tsarena.ai + status |
| 9 | BACKLOG.md | ⬜ | Features and pages to build (prioritized) |
| 10 | DESIGN-SYSTEM.md | ⬜ | Colors, fonts, components, CSS vars, brand |

**Core 7: 0/7 | Role-specific: 0/3**

---

## Non-Agents (Scripts, Scrapers, Bots)

Non-agents are documented in their parent agent's CONFIG.md and PROCESS.md. They live in `non-agents/` directories under each product's context vault.

### TrainingRun Non-Agents

#### Daily News Agent Execution Files
Parent: `trainingrun/agents/daily-news/`
Location: `trainingrun/non-agents/daily_news_agent/`

| # | File | Status | Notes |
|---|---|---|---|
| 1 | main.py | ⬜ | Orchestrator + Telegram bot (@TRnewzBot) |
| 2 | config.py | ⬜ | All settings, paths, API config |
| 3 | context_loader.py | ⬜ | Reads vault files (SOUL.md, USER.md, etc.) |
| 4 | story_selector.py | ⬜ | Grok-3-mini selects best story |
| 5 | article_writer.py | ⬜ | Grok-3 writes article in David's voice |
| 6 | html_stager.py | ⬜ | Generates day-NNN.html from template |
| 7 | github_publisher.py | ⬜ | Publishes via GitHub REST API |
| 8 | telegram_handler.py | ⬜ | Sends drafts, receives approval commands |
| 9 | learning_logger.py | ⬜ | Logs runs + learns from feedback |
| 10 | requirements.txt | ⬜ | Python dependencies |
| 11 | .env.example | ⬜ | Template for credentials |
| 12 | com.trainingrun.daily-news.plist | ⬜ | macOS launchd service definition |

---

#### Content Scout Execution Files
Parent: `trainingrun/agents/content-scout/`
Location: `trainingrun/non-agents/content_scout/`

| # | File | Status | Notes |
|---|---|---|---|
| 1 | scout.py | ✅ | 15 scrapers, 4-layer Truth Filter (2084 lines) — LIVE |
| 2 | patch_mission_control.py | ✅ | Patches mission-control.html with scout data |
| 3 | scout_brain.md | ✅ | Scout operational instructions |

---

#### DDP Pipeline Execution Files
Parent: `trainingrun/agents/ddp-pipeline/`
Location: `trainingrun/non-agents/ddp-scripts/`

| # | File | Status | Notes |
|---|---|---|---|
| 1 | agent_truscore.py | ✅ | TRUscore V1.4 scraper/scorer |
| 2 | agent_trs.py | ✅ | TRS DDP scraper |
| 3 | agent_trfcast.py | ✅ | TRFcast DDP scraper |
| 4 | agent_tragents.py | ✅ | TRAgents DDP scraper |
| 5 | agent_trscode.py | ✅ | TRScode DDP scraper |
| 6 | daily_runner.py | ✅ | Orchestrator — runs all 5 DDPs daily |

---

#### TRS Site Manager Execution Files
Parent: `trainingrun/agents/trs-site-manager/`
Location: `trainingrun/non-agents/web_agent/`

| # | File | Status | Notes |
|---|---|---|---|
| 1 | (Sonnet 4.5 web agent runtime) | ✅ | Browser automation, site management — ACTIVE |

---

### TS Arena Non-Agents

#### Battle Generator Execution Files
Parent: `tsarena/agents/battle-generator/`
Location: `tsarena/non-agents/`

| # | File | Status | Notes |
|---|---|---|---|
| 1 | generate_battles.py | ✅ | Battle generation script — runs weekly via GitHub Actions |
| 2 | battle_bot.py | ✅ | Telegram bot (2-way battle control) — deployed on Mac |

---

## Summary Scorecard

### Agent Files

| Agent | Core 7 | Role-Specific | Total Files | Status |
|---|---|---|---|---|
| 1. Daily News | 7/7 | 0/0 | 7/7 | ✅ COMPLETE |
| 2. Content Scout | 0/7 | 0/2 | 0/9 | ❌ |
| 3. DDP Pipeline | 0/7 | 0/1 | 0/8 | ❌ |
| 4. TRS Site Manager | 0/7 | 0/2 | 0/9 | ❌ |
| 5. Arena Ops | 0/7 | 0/2 | 0/9 | ❌ |
| 6. Battle Generator | 3/7 | 1/1 | 4/8 | ⚠️ |
| 7. Model Manager | 0/7 | 0/4 | 0/11 | ❌ |
| 8. Prompt Curator | 0/7 | 0/4 | 0/11 | ❌ |
| 9. Vote Counter | 0/7 | 0/2 | 0/9 | ❌ |
| 10. Site Builder | 0/7 | 0/3 | 0/10 | ❌ |
| **TOTALS** | **10/70** | **1/21** | **11/91** | **12%** |

### Non-Agent Files

| Non-Agent Group | Files Done | Total | Status |
|---|---|---|---|
| Daily News Agent scripts | 0/12 | 12 | ⬜ |
| Content Scout scripts | 3/3 | 3 | ✅ |
| DDP Pipeline scripts | 6/6 | 6 | ✅ |
| TRS Site Manager runtime | 1/1 | 1 | ✅ |
| Battle Generator scripts | 2/2 | 2 | ✅ |
| **TOTALS** | **12/24** | **24** | **50%** |

### Grand Total

| Category | Done | Total | % |
|---|---|---|---|
| Agent files (Core 7 + role-specific) | 11 | 91 | 12% |
| Non-agent files (scripts, bots) | 12 | 24 | 50% |
| **ALL FILES** | **23** | **115** | **20%** |

---

*Checklist V1 — March 5, 2026. Tracks every file defined in TSArena_Full_Structure_V4.md.*
