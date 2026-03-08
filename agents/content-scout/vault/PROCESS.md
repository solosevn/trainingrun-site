# Content Scout — PROCESS.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Overview

Content Scout runs a continuous loop with two primary modes: **Scrape Cycle** (7:30 AM – 11 PM every 30 min) and **Morning Brief** (5:30 AM daily). A third mode — **Learning Cycle** — runs after the Daily News Agent publishes a story to close the feedback loop.

---

## Phase 1: Startup

1. Validate environment variables (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, XAI_API_KEY, TR_REPO_PATH)
2. Load vault files via `scout_context_loader.load_all_context()`
   - Read SOUL.md (identity + principles)
   - Read CONFIG.md (runtime settings)
   - Read SOURCES.md (scraper list + reliability data)
   - Read TRUTH-FILTER.md (verification methodology)
   - Read STYLE-EVOLUTION.md (source weight adjustments)
   - Read LEARNING-LOG.md (historical patterns)
3. Load existing `scout-data.json` (local data store)
4. Prune items older than 3 days from data store
5. Send startup notification to David via Telegram

---

## Phase 2: Scrape Cycle (Every 30 Minutes, 7:30 AM – 11 PM)

### Step 1: Run All 8 Scrapers
Execute in sequence with error handling per scraper:

| # | Scraper | Sources | Method |
|---|---------|---------|--------|
| 1 | arXiv | cs.AI, cs.LG, cs.CL | RSS feeds |
| 2 | Hugging Face | Daily Papers | HTTP GET |
| 3 | GitHub Trending | Python + All (daily) | HTTP GET |
| 4 | Reddit | r/MachineLearning, r/LocalLLaMA, r/artificial, r/singularity | JSON endpoint |
| 5 | Hacker News | Top 30 stories | Firebase API |
| 6 | Lobste.rs | AI tag | RSS feed |
| 7 | YouTube | AI Explained, Two Minute Papers, Yannic Kilcher, Matthew Berman | RSS feeds |
| 8 | Newsletters | TLDR AI, Import AI, The Batch | RSS feeds |

### Step 2: Deduplicate
- Hash-based dedup (title + URL)
- Cross-source similarity check (>50% word overlap = same story)
- Keep the version from the highest-credibility source

### Step 3: Quality Score
- Apply TrainingRun relevance keywords (+20-30 pts per vertical match)
- Apply substance/hype scoring

### Step 4: Staleness Filter (NEW)
- Check item's original publish date (from RSS `published`/`created` fields)
- Items >3 days old: multiply score by 0.5 (deprioritize)
- Items >7 days old: drop entirely regardless of score
- Log dropped items for transparency

### Step 5: Save & Log
- Save updated data to `scout-data.json`
- Call `scout_learning_logger.log_scrape_cycle()` → appends to RUN-LOG.md
- Send status update to Telegram every 4 hours (11 AM, 3 PM, 7 PM, 11 PM)

---

## Phase 3: Morning Brief Generation (5:30 AM Daily)

### Step 1: Load Context
- Reload vault files via `scout_context_loader.load_all_context()`
- Read STYLE-EVOLUTION.md for current source weight adjustments

### Step 2: Run 4-Layer Truth Filter
1. **Layer 1 — Source Credibility (0-40 pts):** Score based on source tier (arXiv=40, Reddit=15, etc.)
2. **Layer 2 — Cross-Confirmation (0-20 pts):** How many different sources carry this story? (3+ = 20 pts)
3. **Layer 3 — Zero Hype / Substance (-10 to +20 pts):** Hype words penalize, substance words boost
4. **Layer 4 — AI Verification (Dual Model):** Ollama llama3.1:8b + Grok-3-Mini independently assess each headline

### Step 3: Apply Source Weights
- Read current weights from STYLE-EVOLUTION.md
- Multiply each item's truth score by its source weight (0.5x – 2.0x)
- Default weight: 1.0x (neutral)

### Step 4: Select Top 10
- Minimum truth score: 50 pts
- Max 3 items per category (diversity)
- Max 2 items per source (avoid echo chambers)
- Prefer cross-confirmed stories
- Backfill from candidates 11-15 if AI verification drops items

### Step 5: Generate Narrative
- Send top 10 to Ollama with TrainingRun-aligned system prompt
- Format: 2-3 sentences per story (what happened, why it matters, citation)
- If Ollama unavailable: send bullet list only (no narrative)

### Step 6: Deliver
- Write `scout-briefing.json` to repo root (Daily News Agent reads this)
- Git commit + push to GitHub
- Send formatted Telegram message to David
- Call `scout_learning_logger.log_briefing_result()` → appends to LEARNING-LOG.md

---

## Phase 4: Learning Cycle (After Daily News Agent Publishes)

### Trigger
- Daily News Agent publishes a story and writes `scout-feedback.json` to repo
- Content Scout detects `scout-feedback.json` on next scrape cycle

### Step 1: Read Feedback
- Parse `scout-feedback.json`: which story was selected, from which source, which were rejected

### Step 2: Log Selection
- Call `scout_learning_logger.log_selection_feedback()`
- Record: selected story title, source, rejected candidates, paper number, date

### Step 3: Update Source Weights
- Call `scout_learning_logger.update_source_weights()`
- Calculate: which sources produce stories that get selected vs. which are dead weight
- Write weight adjustments to STYLE-EVOLUTION.md
- Over time: productive sources get boosted (up to 2.0x), dead sources get deprioritized (down to 0.5x)

### Step 4: Commit Learning Data
- Push updated vault files (RUN-LOG.md, LEARNING-LOG.md, STYLE-EVOLUTION.md) to GitHub

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Scraper fails | Log error, skip that source, continue with remaining scrapers |
| Ollama down | Skip narrative generation, send bullet list only |
| xAI down | Mark items as UNVERIFIED, continue without Layer 4b |
| GitHub push fails | Log error, retry once, continue (data still in local JSON) |
| Telegram fails | Log error, data still saved locally and to GitHub |
| All scrapers fail | Send alert to David, wait for next cycle |
| scout-feedback.json missing | No learning update this cycle (normal if Daily News Agent hasn't published) |

---

*Read by Content Scout via scout_context_loader.py. Defines the complete operational workflow.*
