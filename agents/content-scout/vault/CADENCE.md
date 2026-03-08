# Content Scout — CADENCE.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Daily Schedule (CST)

| Time | Action | Details |
|------|--------|---------|
| 5:30 AM | Morning Brief | Run truth filter → select top 10 → AI verify → generate narrative → send to David via Telegram → write scout-briefing.json → push to GitHub |
| 7:30 AM | Scraping begins | First scrape cycle of the day |
| 7:30 AM – 11:00 PM | Scrape every 30 min | All 8 scrapers run, dedup, score, save |
| 11:00 AM | Status update | Item count + category breakdown → Telegram |
| 3:00 PM | Status update | Item count + category breakdown → Telegram |
| 7:00 PM | Status update | Item count + category breakdown → Telegram |
| 11:00 PM | Final status + scraping stops | Last scrape cycle, final status update |

---

## Learning Cycle (Event-Driven)

| Trigger | Action |
|---------|--------|
| Daily News Agent publishes a story | Writes `scout-feedback.json` to repo |
| Next scrape cycle after publish | Content Scout reads feedback, logs selection, updates source weights |
| After weight update | Commits updated LEARNING-LOG.md + STYLE-EVOLUTION.md to GitHub |

---

## Maintenance Rhythms

| Frequency | Action |
|-----------|--------|
| Every cycle | Prune items >3 days from scout-data.json |
| Every cycle | Check for scout-feedback.json (learning trigger) |
| Every briefing | Reload vault files (SOUL, CONFIG, SOURCES, TRUTH-FILTER, STYLE-EVOLUTION) |
| Every briefing | Apply current source weights from STYLE-EVOLUTION.md |
| Continuous | Staleness filter: >3 days deprioritize, >7 days drop |

---

## Service Configuration

| Key | Value |
|-----|-------|
| Service | launchd (`com.trainingrun.scout`) |
| RunAtLoad | true (starts on boot) |
| KeepAlive | true (restarts on crash) |
| ThrottleInterval | 30 seconds |
| Log file | `content_scout/scout.log` |

---

## Coordination Rules

1. **Never run heavy Ollama tasks when TRSitekeeper is doing heavy operations** — check for Ollama availability, skip narrative if busy
2. **Always pull --rebase before pushing** to avoid git conflicts with cron jobs or TRSitekeeper
3. **Morning brief at 5:30 AM gives David time** to review before the Daily News Agent runs story selection

---

*Read by Content Scout via scout_context_loader.py. Defines when everything runs.*
