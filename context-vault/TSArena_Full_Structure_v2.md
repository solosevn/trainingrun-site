# The Safety Arena — Full Operational Structure

**Version:** Draft 3 — March 5, 2026  
**Status:** Working document — David + Claude finalizing  
**Purpose:** Single source of truth for every agent, process, and cadence that powers TSArena + TrainingRun.AI

---

## Directory Tree

```
trainingrun-site/
├── context-vault/
│   ├── org/                              # ← Global / cross-site
│   │   ├── SOUL.md
│   │   ├── USER.md
│   │   ├── HEARTBEAT.md
│   │   ├── MEMORY.md
│   │   └── shared-context/
│   │       ├── THESIS.md
│   │       ├── SIGNALS.md
│   │       ├── FEEDBACK-LOG.md
│   │       ├── PRODUCTION-BIBLE.md
│   │       ├── PROJECTS.md
│   │       └── REASONING-CHECKLIST.md
│   ├── agents/
│   │   ├── trainingrun/
│   │   │   ├── trs-site-manager/ (SOUL.md)
│   │   │   ├── content-scout/ (SOUL.md)
│   │   │   ├── ddp-pipeline/ (SOUL.md)
│   │   │   └── daily-news/ ✅ BUILT+TESTED
│   │   │       ├── SOUL.md, CONFIG.md, PROCESS.md
│   │   │       ├── CADENCE.md, RUN-LOG.md
│   │   │       ├── LEARNING-LOG.md
│   │   │       └── STYLE-EVOLUTION.md
│   │   └── tsarena/ (arena-ops, battle-generator, model-manager, prompt-curator, vote-counter, site-builder)
│   └── memory/
├── content_scout/ 🔍 v1.2.0 ✅ LIVE
│   ├── scout.py (15 scrapers, 4-layer Truth Filter)
│   ├── patch_mission_control.py
│   └── scout_brain.md
├── daily_news_agent/ 📰 v1.0 ✅ BUILT+TESTED
│   ├── main.py (orchestrator + Telegram bot)
│   ├── config.py, context_loader.py
│   ├── story_selector.py (grok-3-mini)
│   ├── article_writer.py (grok-3)
│   ├── html_stager.py, github_publisher.py
│   ├── telegram_handler.py, learning_logger.py
│   ├── requirements.txt, .env.example
│   └── com.trainingrun.daily-news.plist
├── web_agent/, scripts/
└── (HTML files, assets, tsarena/)
```

---

## Agent Status Summary

| # | Agent | Status | Model |
|---|-------|--------|-------|
| 1 | Arena Ops | Planned | - |
| 2 | Battle Generator | Planned | - |
| 3 | Model Manager | Planned | - |
| 4 | Prompt Curator | Planned | - |
| 5 | Vote Counter | ✅ Live | Supabase |
| 6 | Site Builder | ✅ Live | - |
| 7 | Content Scout | ✅ Live v1.2.0 | llama3.1:8b + xAI Grok |
| 8 | Daily News Agent | ✅ Built+Tested | xAI Grok-3 + Grok-3-mini |

---

## 8. Daily News Agent — The Journalist ✅ BUILT+TESTED

**Telegram:** @TRnewzBot
**Commands:** "push it" / "edit: [notes]" / "kill it" / "status"

Workflow:
1. Reads scout-briefing.json from Content Scout
2. Grok-3-mini selects best story (5-filter test + vault personality)
3. Grok-3 writes article in David's voice (SOUL.md, USER.md, STYLE-EVOLUTION.md)
4. Stages as day-NNN.html
5. Sends draft to David via Telegram
6. David approves -> publishes to GitHub + updates news.html
7. Logs to RUN-LOG.md and LEARNING-LOG.md

**Human approval gate:** NEVER publishes without David's "push it"

## 7. Content Scout — Intelligence Gatherer ✅ LIVE v1.2.0

15 scrapers | 4-layer Truth Filter | Scrapes 7AM-11PM every 30min
Morning brief at 5:30 AM | Feeds Daily News Agent

---

## Priority Build Order

| # | Item | Status |
|---|------|--------|
| 4 | Build Daily News Agent | ✅ COMPLETE #127 |
| 6 | Build models.html | ✅ DONE |
| 10 | REASONING-CHECKLIST.md | ✅ DONE |
| 1 | Battle generation pipeline | ❌ Not started |
| 2 | Weekly battle schedule | ❌ Not started |
| 3 | API key audit | ❌ Not started |
| 5 | Add 12 missing models | ❌ Not started |
| 7-9 | Model/prompt expansion | ❌ Not started |

---

## Credentials Map

| Service | Used By | Location |
|---------|---------|----------|
| xAI API (Grok) | Scout, Daily News | plist env, .env |
| Telegram @TrainingRunBot | Scout, Sitekeeper | plist env |
| Telegram @TRnewzBot | Daily News Agent | .env |
| GitHub PAT (fine-grained) | Daily News Agent | .env |
| Ollama (local) | Scout | local, no key |
| Supabase | TS Arena | web_agent configs |
