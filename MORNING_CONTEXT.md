# MORNING CONTEXT — TrainingRun.AI + TS Arena
## Upload this file at the start of every Claude session. Read it FIRST. No exceptions.

> **Version:** 3.0
> **Last Updated:** March 9, 2026 — 11:00 AM CST
> **Updated by:** Claude session (V10 restructure fix marathon — Fixes #1-10 completed)
> **Repo:** github.com/solosevn/trainingrun-site (GitHub Pages → trainingrun.ai)
> **Operator:** David Solomon (solosevn@gmail.com)

> **UPDATE RULE:** This file MUST be updated at the end of every Claude session. It is the handoff document. If you don't update it, the next session starts with a wrong map. Push the updated version to GitHub before ending the session.

---

## 1. OPERATING RULES (NON-NEGOTIABLE)

**David does NOT write code. Ever.**
- David does not run sed, awk, echo, or any code-editing terminal commands
- David approves changes. That's it.

**Claude makes ALL code changes via the Chrome extension.**
- Claude edits files directly on GitHub using the web editor
- Claude commits changes through the GitHub web UI
- For large files (>1000 lines): Claude saves to outputs folder, David uploads via GitHub's drag-and-drop upload page at `/upload/main/<path>`
- If Chrome/GitHub disconnects, troubleshoot — do NOT fall back to terminal commands

**The Process (every code change):**
1. Claude identifies the change and explains it
2. Claude writes the fix and shows before/after
3. David reviews and approves ("yes", "k", "do it")
4. Claude commits to GitHub with a clear message
5. David runs `git pull` on his machine
6. David restarts the affected agent if needed

**Communication Rules:**
- No sugarcoating. State facts. If something is broken, say it's broken.
- No filler ("Great question", "Good catch") — just answer
- "Working" means it actually does the thing, not "the code exists"
- Don't move on until the current item actually works
- If you don't know, say "I don't know yet, let me investigate"
- Don't repeat information David already knows
- Don't over-explain. Don't ask questions you can figure out.
- When David catches a contradiction, own it immediately
- "k" = acknowledged/approved. "yes" / "do it" = approved.
- David is direct. When frustrated, it's because time is being wasted.

**GitHub is the source of truth.** No local-only fixes. No temporary fixes. No sed hacks.

**Never operate in the Cowork VM for code changes.** VM is only for documents/presentations David specifically requests. All code/config/agent work goes through Chrome → GitHub.

**CEO Learning Documents:** Required for EVERY fix. Stored at `agents/ceo/vault/`. Must be detailed enough that a future agent can replicate all work. Currently CEO-LEARNING-001 through 007.

---

## 2. THE SYSTEM ARCHITECTURE

Two websites, one repo, 8 agents total:

### V10 Repo Structure (as of March 9, 2026)
```
trainingrun-site/
├── agents/
│   ├── ceo/vault/              # CEO Learning Documents (001-007)
│   ├── content-scout/          # Content Scout agent code
│   ├── daily-news/             # Daily News Agent code
│   │   └── staging/            # day-NNN.html drafts, .last_processed_date
│   ├── ddp/                    # DDP Pipeline (daily_runner.py + 5 scrapers)
│   └── trsitekeeper/           # TRSitekeeper agent code
│       ├── sitekeeper_audit.py # 23-check audit (1,497 lines)
│       ├── sitekeeper_context_loader.py # Vault loader (567 lines)
│       ├── sitekeeper_learning_logger.py
│       └── memory/             # Runtime memory files
├── content_scout/              # Content Scout data (scout-data.json)
├── context-vault/
│   └── trainingrun/
│       ├── agents/
│       │   ├── daily-news/     # Daily News Core 7
│       │   │   └── content-scout/ # Content Scout Core 7
│       │   └── trsitekeeper/   # TRSitekeeper Core 7 (SOUL.md, CONFIG.md, etc.)
│       │       └── ddp-pipeline/ # DDP Pipeline Core 7
│       ├── shared-context/     # REASONING-CHECKLIST.md, THESIS.md, etc.
│       └── org/                # SOUL.md, USER.md, HEARTBEAT.md, MEMORY.md
├── shared/                     # Shared utilities
├── archive/                    # Archived old files
├── assets/                     # Site assets
├── [site HTML files]           # index.html, scores.html, news.html, etc.
├── [DDP data files]            # trscode-data.json, truscore-data.json, etc.
├── status.json                 # DDP pipeline status
├── scout-briefing.json         # Content Scout daily brief
├── agent_activity.json         # Agent run tracking
└── restructure.sh              # V10 restructure script (historical)
```

### TrainingRun.AI — AI news + data site
| Agent | Bot | Token Env Var | Code Location | Status |
|-------|-----|---------------|---------------|--------|
| Content Scout (sub-agent of Daily News) | @trainingrun_david_bot | `TELEGRAM_TOKEN` | `agents/content-scout/` (scout.py, 2217 lines) | ✅ LIVE |
| Daily News Agent | @TRnewzBot | `TRNEWZ_BOT_TOKEN` | `agents/daily-news/` (main.py, 664 lines) | ⚠️ Running but timing issues |
| TRSitekeeper v3.0 | @TRSiteKeeperBot | `TRSITEKEEPER_BOT_TOKEN` | `agents/trsitekeeper/` (agent.py + sitekeeper_audit.py) | ✅ Upgraded March 9 |
| DDP Pipeline (5 scrapers) | @trainingrun_david_bot | (shares with Scout) | `agents/ddp/` (daily_runner.py + 5 agent_*.py) | ✅ LIVE |

### TS Arena — AI safety arena
| Agent | Bot | Status |
|-------|-----|--------|
| Battle Generator | @BattleGenBot | ✅ Active (weekly Sunday cron) |
| Vote Counter | @TSarenaVbot | ✅ Active (real-time) |
| Arena Ops | — | ❌ Not built |
| Model Manager | — | ❌ Not built |
| Prompt Curator | — | ❌ Not built |
| Site Builder | — | ❌ Not built |

---

## 3. TELEGRAM BOT MAP

### TrainingRun.AI (3 bots):

**Bot 1: @trainingrun_david_bot (TrainingRun Bot)** — The delivery channel
- Token: `TELEGRAM_TOKEN`
- Direction: One-way (send only)
- Carries: All 5 DDP scraper results (4 AM daily) + Content Scout updates (scrapes every 30 min 7AM-11PM, morning brief 5:30 AM, status updates at 11AM/3PM/7PM/11PM)

**Bot 2: @TRnewzBot (TRNewsAgentBot)** — Daily News Agent
- Token: `TRNEWZ_BOT_TOKEN`
- Direction: Two-way (sends article drafts, listens for David's push/edit/kill responses)
- Commands David can send: "push it", "edit: [notes]", "kill it", "status", "run", "go"
- Launchd: `com.trainingrun.daily-news.plist` (KeepAlive: true, RunAtLoad: true)

**Bot 3: @TRSiteKeeperBot (TRSiteKeeper)** — TRSitekeeper
- Token: `TRSITEKEEPER_BOT_TOKEN`
- Direction: Two-way (audit reports, remediation approval, freeform Claude chat)
- Commands: status, health, audit/run audit, pending fixes, approve [check], reject [check], vault, brain, log, plus freeform messages → Claude Sonnet 4.6

### TS Arena (2 bots):
- **@BattleGenBot** — Battle generation control
- **@TSarenaVbot** — Vote monitoring alerts

All bots send to same `TELEGRAM_CHAT_ID`: David's chat (`8054313621`)

---

## 4. KEY ENVIRONMENT VARIABLES (in ~/.zshrc)

| Variable | Purpose | Used By |
|----------|---------|---------|
| `TELEGRAM_TOKEN` | Content Scout + DDP bot token | scout.py, DDP scrapers |
| `TRSITEKEEPER_BOT_TOKEN` | TRSitekeeper bot token | agent.py |
| `TRNEWZ_BOT_TOKEN` | Daily News Agent bot token | main.py |
| `TELEGRAM_CHAT_ID` | David's chat ID: 8054313621 | All bots |
| `ANTHROPIC_API_KEY` | Claude API key (trskey-v2, generated March 7) | agent.py, sitekeeper_audit.py |
| `XAI_API_KEY` | Grok API key | daily_news_agent (story selection, article writing, image gen) |
| `GITHUB_TOKEN` | GitHub API access | daily_news_agent (publishing) |
| `TR_REPO_PATH` | Defaults to ~/trainingrun-site | daily_news_agent |

**API Details:**
- Anthropic: Claude Sonnet 4.6 (`claude-sonnet-4-6-20250514`), Tier 1, 50 req/min, $100/month limit, trskey-v2
- Grok: grok-3 (writing), grok-3-mini (story selection), grok-imagine-image (image generation)
- GitHub: solosevn/trainingrun-site, main branch

**Security note:** .env files were audited (Fix #7, CEO-LEARNING-005). No secrets committed to repo. All tokens in ~/.zshrc only.

---

## 5. DAILY SCHEDULE (CST)

| Time | What | Agent | Bot |
|------|------|-------|-----|
| 4:00 AM | DDP scrapers run (all 5), update *-data.json files, push to GitHub | DDP Pipeline | @trainingrun_david_bot |
| 5:30 AM | Content Scout generates morning brief, writes scout-briefing.json locally + pushes to GitHub | Content Scout | @trainingrun_david_bot |
| 5:35+ AM | Daily News Agent detects fresh briefing, selects story, writes article, sends draft to David | Daily News Agent | @TRnewzBot |
| 5:45 AM | Deadline alert if no briefing detected | Daily News Agent | @TRnewzBot |
| 6:00 AM | TRSitekeeper 23-check autonomous audit fires | TRSitekeeper | @TRSiteKeeperBot |
| 6:00-8:00 AM | TRSitekeeper work window: auto-fix high-confidence items, re-audit, escalate rest to David | TRSitekeeper | @TRSiteKeeperBot |
| 7:00 AM–11:00 PM | Content Scout scrapes every 30 minutes | Content Scout | @trainingrun_david_bot |
| On-demand | TRSitekeeper responds to Telegram commands | TRSitekeeper | @TRSiteKeeperBot |

---

## 6. AGENT DEEP DIVE: CONTENT SCOUT

**File:** `agents/content-scout/scout.py` (2217 lines)
**Model:** llama3.1:8b (local Ollama, free) + xAI Grok (verification)
**Architecture:** Simple `while True` loop with `time.sleep()`. Raw HTTP Telegram calls. One-way only.

**What it does:**
- 15 scrapers: arXiv, Hugging Face, GitHub Trending, Reddit (r/singularity, r/MachineLearning), Hacker News, Lobsters, YouTube, Newsletters, TechCrunch, VentureBeat, Ars Technica, The Verge, MIT Tech Review, Reuters, Wired
- Truth Filter: 4 layers (Source Credibility, Cross-Confirmation, Zero Hype, AI Verification)
- Writes `scout-briefing.json` locally then pushes to GitHub
- Morning brief at 5:30 AM with top 10 stories scored and filtered

**Key files:**
- `agents/content-scout/scout.py` — Main orchestrator + all 15 scrapers
- `agents/content-scout/scout_context_loader.py` — Loads 9 vault files + source weights
- `agents/content-scout/scout_learning_logger.py` — Logs cycles, updates weights, commits
- `agents/content-scout/patch_mission_control.py` — Patches mission-control.html with scout data

---

## 7. AGENT DEEP DIVE: DAILY NEWS AGENT

**File:** `agents/daily-news/main.py` (664 lines)
**Model:** Grok-3 (writing) + Grok-3-mini (story selection) + grok-imagine (images)
**Architecture:** `python-telegram-ext` Application with `job_queue.run_repeating(handle_scout_check, interval=300, first=30)`. Two-way Telegram.
**Launchd:** `com.trainingrun.daily-news.plist` — KeepAlive: true, RunAtLoad: true

**Workflow (PROCESS.md V3.0 steps 1-15):**
1. Content Scout delivers stories (scout-briefing.json)
2. Load context vault (SOUL.md, CONFIG.md, PROCESS.md, etc.)
3. Read Content Scout briefing — check freshness (today's date)
4. If past 5:45 AM with no briefing → send deadline alert
5. Select best story via Grok-3-mini (5-filter test + REASONING-CHECKLIST)
6. Write article via Grok-3 in David's voice
7. Generate article image via grok-imagine
8. Stage HTML (day-NNN.html from day-template.html)
9. Send Telegram review request to David with draft preview
10. Wait for David's response: "push it" / "edit: [notes]" / "kill it"
11. If edit → revise via Grok → re-send for approval
12. If push → publish to GitHub (day-NNN.html + update news.html)
13. Send publish confirmation
14. Log to RUN-LOG.md and LEARNING-LOG.md
15. Write scout-feedback.json for Content Scout learning loop

**Known issue:** Timing gap — Content Scout delivers at 5:35 AM but Daily News Agent sometimes doesn't pick up for 3+ hours. Possible cause: agent crash/respawn or .last_processed_date blocking.

---

## 8. AGENT DEEP DIVE: TRSITEKEEPER v3.0

**Main agent:** `agents/trsitekeeper/agent.py`
**Audit module:** `agents/trsitekeeper/sitekeeper_audit.py` (1,497 lines, 23 checks)
**Context loader:** `agents/trsitekeeper/sitekeeper_context_loader.py` (567 lines)
**Model:** Claude Sonnet 4.6 (Anthropic API, trskey-v2)
**Architecture:** Raw HTTP polling loop (while True + tg_get_updates). Threaded audit scheduler at 6 AM.

**v3.0 Upgrades (March 9, 2026 — Fix #8):**
- ✅ Vault context loading before every audit (Core 7 files + memory files)
- ✅ 6-8 AM work window with auto-fix cycles (max 3 per window)
- ✅ Structured Claude diagnosis with JSON output parsing
- ✅ Learning memory via tried_fixes.jsonl
- ✅ All 23 checks point to correct V10 paths and real data files
- ✅ check_014 (belt/mythology nonsense) removed entirely

**23-Check Audit:**

Category 1 — Local File Checks (6):
- check_001: Site health — expects real DDP files in repo root (trscode-data.json, truscore-data.json, trf-data.json, tragent-data.json, trs-data.json)
- check_002: DDP status — reads status.json from repo root
- check_003: Data file integrity — validates real DDP files exist and have content
- check_004: HTML page check
- check_005: Git status
- check_006: Vault integrity — checks `context-vault/trainingrun/agents/trsitekeeper/` for Core 7 markdown files (SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md, RUN-LOG.md, LEARNING-LOG.md, STYLE-EVOLUTION.md)
- check_007: Agent activity

Category 2 — Live Site Checks (4):
- check_008: URL crawl
- check_009: Internal links
- check_010: SSL certificate
- check_011: Response times

Category 3 — Content Integrity (4):
- check_012: Logo branding
- check_013: Navigation
- check_015: Score display (strip script blocks before counting nulls — fixed March 7)
- check_016: Dead buttons

Category 4 — Security (4):
- check_017: Secrets scan
- check_018: HTTPS redirect
- check_019: External scripts
- check_020: File permissions

Category 5 — Intelligence (4):
- check_021: Comparative audit
- check_022: Validates all 5 real DDP data files exist and have content
- check_023: Scans real DDP data files for suspicious perfect scores
- check_024: Checks real DDP file modification times (flags >48h stale)

**Work Window (6-8 AM):**
1. Run full 23-check audit
2. If failures found, Claude diagnoses each with vault + memory context
3. High-confidence auto-fixes execute automatically
4. Record every fix attempt to tried_fixes.jsonl
5. Wait 30s, re-audit
6. Max 3 fix cycles per window
7. Remaining low-confidence items escalated to David via Telegram

**Telegram commands (keyword_intercept):**
- status / s → check_status
- health → site_health
- audit / run audit / full scan → triggers 23-check audit
- pending fixes → show pending remediations
- approve [check_name] → execute approved remediation
- reject [check_name] → clear remediation
- vault / memory → vault status
- brain → reads brain.md
- Any other text → sent to Claude Sonnet 4.6 for reasoning

**Memory System (6 layers, loaded at boot):**
| Layer | File | Purpose |
|-------|------|---------|
| 1. Kernel | brain.md | Identity, rules, autonomy gates |
| 2. Operational | memory/site_knowledge.json | Full page map, quirks, data dependencies |
| 3. Episodes | memory/error_log.jsonl + memory/fix_patterns.json | Recent errors + seeded fix patterns |
| 4. Local Memory | Git log + status.json | Recent changes, deploy state |
| 5. Skills | skills/*.md | CSS diagnosis, data staleness, git safety |
| 6. Theory-of-Mind | memory/david_model.json | David's identity, priorities, communication style |

---

## 9. THE 5 DDPs (Data-Driven Products)

All run daily at 4 AM CST via `agents/ddp/daily_runner.py`. Each scraper writes a JSON file to the repo root and pushes to GitHub.

| DDP | Scraper | Output File | Sources | Models Tracked |
|-----|---------|-------------|---------|----------------|
| TRScode | agent_trscode.py | trscode-data.json | 8 sources (SWE-bench, LiveCodeBench, BigCodeBench, etc.) | 38 |
| TRFcast | agent_trfcast.py | trf-data.json | 4 platforms (ForecastBench, Rallies, AlphaArena, FinanceArena) | 11 |
| TRSbench | agent_trs.py | trs-data.json | 18 sources across 7 pillars (safety, reasoning, coding, etc.) | 53 |
| TRUscore | agent_truscore.py | truscore-data.json | 9 sub-metrics, 5 pillars (truthfulness, hallucination, reasoning, neutrality, quality) | 18 |
| TRAgents | agent_tragents.py | tragent-data.json | 22+ sources, 6 pillars (task completion, cost efficiency, tool reliability, safety, accessibility, multi-model) | 20 |

**Real data files (repo root):** trscode-data.json, trf-data.json, trs-data.json, truscore-data.json, tragent-data.json, status.json

**Deleted stubs (March 9):** ticker.json, leaderboard.json, ddp_status.json were empty `[]` stubs mistakenly created. Now deleted. Nothing references them.

---

## 10. CONTEXT VAULT SYSTEM

**Every agent gets Core 7 files:**
1. SOUL.md — Identity, mission, boundaries
2. CONFIG.md — Technical details, APIs, endpoints
3. PROCESS.md — Step-by-step workflow
4. CADENCE.md — When it runs, triggers, rhythms
5. RUN-LOG.md — Every execution logged
6. LEARNING-LOG.md — Raw memory, post-mortems
7. STYLE-EVOLUTION.md — Curated rules, confidence levels

**Vault location:** `context-vault/trainingrun/agents/`
- `daily-news/` — Daily News Agent Core 7 ✅ Complete
- `daily-news/content-scout/` — Content Scout Core 7 ✅ Complete (9 files including SOURCES.md, TRUTH-FILTER.md)
- `trsitekeeper/` — TRSitekeeper Core 7 + CAPABILITIES.md + TASK-LOG.md ✅ Complete
- `trsitekeeper/ddp-pipeline/` — DDP Pipeline Core 7 + SCORING-RULES.md ✅ Complete

**Shared context:** `context-vault/trainingrun/shared-context/`
- REASONING-CHECKLIST.md — All agents reference this
- THESIS.md, SIGNALS.md, PRODUCTION-BIBLE.md, PROJECTS.md

**Org-level:** `context-vault/trainingrun/org/`
- SOUL.md, USER.md, HEARTBEAT.md, MEMORY.md

---

## 11. CURRENT STATE — WHAT'S WORKING (as of March 9, 2026)

### V10 Restructure Fixes: ALL 10 COMPLETED ✅

| Fix # | Issue | Status | CEO Learning |
|-------|-------|--------|-------------|
| 1 | DDP import paths broken after restructure | ✅ Fixed | CEO-LEARNING-001, 002 |
| 2 | DDP daily_runner.py broken imports | ✅ Fixed | CEO-LEARNING-002 |
| 3 | status.json overwritten by git rebase | ✅ Fixed | CEO-LEARNING-003 |
| 4 | news.html duplicate entries | ✅ Fixed | CEO-LEARNING-004 |
| 5 | news.html article display issues | ✅ Fixed | CEO-LEARNING-004 |
| 6 | news.html link/formatting cleanup | ✅ Fixed | CEO-LEARNING-004 |
| 7 | .env files security audit | ✅ Fixed | CEO-LEARNING-005 |
| 8 | TRSitekeeper not autonomous | ✅ Fixed | CEO-LEARNING-006 |
| 9 | 9 uncommitted local files | ✅ Fixed | CEO-LEARNING-007 |
| 10 | MORNING_CONTEXT.md outdated | ✅ This update | CEO-LEARNING-008 |

### DDP Pipeline: ✅ Running
- March 9 run: Passed 4/5 (TRSBench timed out >300s, all others passed)
- status.json pushed to GitHub automatically

### TRSitekeeper: ✅ Upgraded to v3.0
- 23 checks (was 24 — removed check_014 belt/mythology)
- All checks point to correct V10 paths
- Vault context loading active
- Work window 6-8 AM with auto-fix cycles
- Learning memory via tried_fixes.jsonl

### Content Scout: ✅ Running
- Scraping every 30 minutes 7AM-11PM
- Morning brief at 5:30 AM

### Daily News Agent: ⚠️ Running but with timing issues
- Paper number duplication risk (Paper 009 incident)
- 3+ hour delay between scout briefing and article draft

### Known remaining items to monitor:
- TRSBench timeout — may need increased timeout or optimization
- Daily News Agent timing gap — needs investigation
- check_005 (git status) — files keep getting re-dirtied by scraper runs, may always show dirty
- Agent output files should be auto-committed after runs (currently manual)

---

## 12. CEO LEARNING DOCUMENTS

All stored at `agents/ceo/vault/` on GitHub:

| Doc | Title | Fix | Date |
|-----|-------|-----|------|
| CEO-LEARNING-001 | Debugging multi-agent systems | Fix #1 | Mar 8 |
| CEO-LEARNING-002 | DDP pipeline restructure breakage | Fix #1-2 | Mar 9 |
| CEO-LEARNING-003 | status.json rebase overwrite | Fix #3 | Mar 9 |
| CEO-LEARNING-004 | news.html duplication fix | Fix #4-6 | Mar 9 |
| CEO-LEARNING-005 | .env files security audit | Fix #7 | Mar 9 |
| CEO-LEARNING-006 | TRSitekeeper autonomy upgrade | Fix #8 | Mar 9 |
| CEO-LEARNING-007 | Uncommitted local files | Fix #9 | Mar 9 |

---

## 13. RECENT COMMITS (as of March 9, 2026)

| SHA | Message | Date |
|-----|---------|------|
| c9aa5ac | Add files via upload (CEO-LEARNING-007) | Mar 9 |
| a876e04 | Add 9 uncommitted agent output files and restructure script | Mar 9 |
| 8b4df69 | Add files via upload (CEO-LEARNING-006) | Mar 9 |
| 4406b24 | Add files via upload (sitekeeper_audit.py v3.0 — vault + work window) | Mar 9 |
| 3544da4 | Add files via upload (sitekeeper_audit.py — fixed checks) | Mar 9 |
| 52c1836 | Add files via upload (sitekeeper_audit.py 1,335 lines) | Mar 9 |
| Various | Delete ticker.json, leaderboard.json, ddp_status.json | Mar 9 |
| Various | CEO-LEARNING-003, 004, 005 uploads | Mar 9 |
| 5caffb | Content Scout briefing 2026-03-08 | Mar 8 |

---

## 14. FILE LOCATIONS QUICK REFERENCE

### Agent Code (V10 paths)
| Agent | Main File | Key Supporting Files |
|-------|-----------|---------------------|
| TRSitekeeper | agents/trsitekeeper/agent.py | sitekeeper_audit.py (1,497 lines), sitekeeper_context_loader.py (567 lines), sitekeeper_learning_logger.py |
| Daily News Agent | agents/daily-news/main.py (664 lines) | config.py, context_loader.py, story_selector.py, article_writer.py, html_stager.py, github_publisher.py, telegram_handler.py, learning_logger.py, image_generator.py |
| Content Scout | agents/content-scout/scout.py (2217 lines) | scout_context_loader.py, scout_learning_logger.py, patch_mission_control.py |
| DDP Pipeline | agents/ddp/daily_runner.py + 5 agent_*.py scrapers | Each ~30-65K |
| CEO Vault | agents/ceo/vault/ | CEO-LEARNING-001 through 007 |

### Data Files (repo root)
| File | Updated By | Frequency |
|------|-----------|-----------|
| trscode-data.json | agent_trscode.py | Daily 4 AM |
| trf-data.json | agent_trfcast.py | Daily 4 AM |
| trs-data.json | agent_trs.py | Daily 4 AM |
| truscore-data.json | agent_truscore.py | Daily 4 AM |
| tragent-data.json | agent_tragents.py | Daily 4 AM |
| status.json | DDP Pipeline | Daily 4 AM |
| scout-briefing.json | Content Scout | Daily 5:30 AM |
| agent_activity.json | TRSitekeeper | On audit runs |

### Site Pages (repo root)
index.html, scores.html, trscode-scores.html, truscore-scores.html, trfcast-scores.html, tragents-scores.html, news.html, about.html, sources.html, hq.html, mission-control.html, churn.html, deep-thought.html, frontier.html, gigaburn.html, global-race.html, specialists.html, day-001.html through day-011.html, day-template.html (DO NOT EDIT)

### Memory & Learning (agents/trsitekeeper/)
| File | Purpose |
|------|---------|
| memory/tried_fixes.jsonl | Append-only log of every fix attempt + outcome |
| memory/fix_patterns.json | Seeded fix patterns with diagnostic steps |
| memory/error_log.jsonl | Append-only error log |
| memory/site_knowledge.json | Full page map |
| memory/david_model.json | David's identity, priorities, communication style |
| audit_history.json | Audit run history |

---

## 15. DAVID'S MACHINE

- macOS with zsh shell
- Environment variables in `~/.zshrc`
- Python 3.13 installed at /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
- Working directory: `~/trainingrun-site/`
- Agents run from terminal: `python3 <agent>.py`
- Launchd services in ~/Library/LaunchAgents/

---

## 16. DESIGN PHILOSOPHY

**Agent-First:** Every fix should answer "How does this work autonomously without David manually intervening?"
- Build approval gates into agents (Telegram approve/reject)
- Build self-healing and self-diagnosing capabilities
- Goal: David gives thumbs up or down via Telegram. That's his only job.

**No Circular Fixes:** If git pull undoes it, it's not a fix. If it depends on untracked files, it will break.

**Permanent Over Quick:** 10 extra minutes to do it right beats 2 hours debugging a workaround later.

**"Done" = Actually Working:** Code committed is "deployed." "Done" means tested and the feature does what it's supposed to do.

---

## 17. CRITICAL LESSONS LEARNED

1. **Question the audit checks themselves** — don't create stub files to satisfy bad expectations. "Belt" and "mythology" were nonsense. Fix the check, not the data.
2. **Don't approve things you haven't verified** — check if expected files/pages actually make sense before telling David to approve.
3. **The API key was dead for 6 days** (March 1-7) — trskey was invalid. trskey-v2 was generated March 7. Every Claude API call from TRSitekeeper was silently failing with 401s.
4. **GitHub web upload creates a sync gap** — When files are pushed via the browser upload UI, the local git repo doesn't know. Always `git pull` after web upload sessions.
5. **Agent output without auto-commit is invisible work** — Agents write files locally but don't push. 9 files sat uncommitted. Every agent that writes files needs a push mechanism.
6. **The learning system works:** tried_fixes.jsonl records attempts, Claude reads past failures before proposing new fixes, escalation triggers after 2+ failed attempts.
7. **Content Scout writes scout-briefing.json locally AND pushes to GitHub.** Daily News Agent reads the local copy. Both run on David's Mac.
8. **Large files (>1000 lines): Don't paste in GitHub editor.** Save to outputs folder, David drags to GitHub upload page at `/upload/main/<path>`. Much faster and reliable.

---

## 18. SESSION START CHECKLIST

1. ✅ Read this file (MORNING_CONTEXT.md)
2. Read OPERATING_INSTRUCTIONS.md if uploaded
3. Ask David what's on the agenda (or check for active fix list)
4. Check Chrome extension: `tabs_context_mcp`
5. Review where we left off (check Section 11 for current state)

---

## 19. SESSION END CHECKLIST

1. Update this file (MORNING_CONTEXT.md) with everything that changed
2. Increment version number, update timestamp and "Updated by" line
3. Push updated version to GitHub
4. Give David a copy for his local folder
5. Write detailed recap with: commit SHAs, pending items, agent states, exact file paths, what was tested vs assumed

---

*This file is the single source of truth for every new Claude session. It replaces: OPERATING_INSTRUCTIONS.md + SESSION_RECAP + V8 structure doc + screenshots + code reading. Keep it updated at end of every session. Push to GitHub so it's always accessible.*
