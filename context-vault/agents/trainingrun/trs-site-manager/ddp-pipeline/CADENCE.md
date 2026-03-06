# CADENCE — DDP Pipeline

> **Version:** 1.0 — March 6, 2026

---

## Daily Schedule

| Time (CST) | Action |
|---|---|
| **4:00 AM** | `daily_runner.py` triggered by launchd |
| ~4:01 AM | TRScode scraping begins (8 sources) |
| ~4:10 AM | TRFcast scraping begins (4 platforms) |
| ~4:20 AM | TRSbench scraping begins (18 sources) |
| ~4:40 AM | TRUscore scraping begins (9 sources) |
| ~4:55 AM | TRAgents scraping begins (22+ sources) |
| ~5:15 AM | All DDPs complete, 5 JSON files pushed to GitHub |
| ~5:15 AM | Telegram notifications sent (one per DDP) |

*Times are approximate — actual duration depends on source response times.*

---

## Trigger

- **Primary:** macOS launchd service (runs daily at 4:00 AM CST)
- **Manual:** `python3 daily_runner.py` from terminal
- **Single DDP:** `python3 daily_runner.py --score truscore`
- **Dry run:** `python3 daily_runner.py --dry-run`

---

## Weekly / Monthly Rhythms

| Cadence | Action |
|---|---|
| **Daily** | Full 5-DDP scrape and score cycle |
| **Weekly (Sunday)** | Review scraper failure logs, check for new benchmark sources |
| **Monthly (1st)** | Full scraper audit — are all sources still live? Any methodology changes? |
| **Quarterly** | Bible version reviews — do weights still reflect relative importance? |

---

## Exception Handling

| Scenario | Response |
|---|---|
| Individual source down | Skip source, score with remaining data, log failure |
| Entire DDP fails | Log failure, continue to next DDP, Telegram alert |
| All DDPs fail | Log critical error, Telegram alert to David |
| launchd misfire | Manual trigger: `python3 ~/trainingrun-site/daily_runner.py` |
| Stale data (source not updating) | Flag in LEARNING-LOG, investigate source status |

---

## Upstream Dependencies

- Content Scout finishes morning brief at 5:30 AM → Daily News Agent may reference DDP data
- DDP data must be fresh before Daily News Agent's morning cycle
- Current schedule (4AM) ensures data is ready well before the news pipeline starts

---

## Downstream Consumers

| Consumer | What it uses | When |
|---|---|---|
| **index.html** (TrainingRun.AI) | All 5 `-data.json` files | On page load (fetches from GitHub Pages) |
| **truscore.html** | `truscore-data.json` | On page load |
| **mission-control.html** | `agent_activity.json` | On page load |
| **Daily News Agent** | May reference scores in articles | Morning cycle |
