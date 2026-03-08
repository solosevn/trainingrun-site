# PROCESS — DDP Pipeline

> **Version:** 1.0 — March 6, 2026

---

## Overview

```
┌─────────────────────────────────────────────────────┐
│              DAILY RUNNER (4:00 AM CST)              │
│                                                      │
│  For each ENABLED DDP:                               │
│    1. Launch agent script as subprocess              │
│    2. Agent scrapes sources → normalizes → scores    │
│    3. Agent writes JSON → git commit → git push      │
│    4. Agent sends Telegram notification              │
│    5. Runner logs success/failure                    │
│                                                      │
│  Result: 5 updated leaderboard JSON files on GitHub  │
│  GitHub Pages serves them → live site updates        │
└─────────────────────────────────────────────────────┘
```

---

## Phase 1: Orchestration (daily_runner.py)

1. **Start** — daily_runner.py triggered by launchd at 4:00 AM CST
2. **Check ENABLED dict** — skip any DDP set to `False`
3. **For each enabled DDP:**
   - Verify script file exists at repo root
   - Launch as subprocess: `python3 agent_<name>.py [--dry-run]`
   - Capture return code (0 = success, non-zero = failure)
   - Log result with timestamp
4. **Supports single-score mode:** `--score trs` runs only one DDP
5. **Supports dry-run mode:** `--dry-run` passed through to each agent

---

## Phase 2: Individual Agent Execution (per DDP)

Each agent script follows the same pattern:

### Step 1: Scrape Sources
- Launch Playwright Chromium (headless)
- Navigate to each benchmark source URL
- Wait for page load (5-15 seconds depending on source)
- Parse HTML tables using BeautifulSoup
- Extract model names and scores
- Handle special cases: HuggingFace Spaces (iframe), inverted metrics

### Step 2: Name Resolution
- Map scraped model names to canonical roster names
- Use `model_names.py` fuzzy matching (exact → substring → difflib)
- Strip API version suffixes (`-2024-08-06`, `-instruct`, etc.)
- Filter out non-model entries (chart coordinates, headers)

### Step 3: Normalize Scores
- Each sub-metric normalized to 0–100 scale
- Inverted metrics flipped (lower raw = higher normalized)
- Known baseline values used where applicable (e.g., FACTS, HalluHard)

### Step 4: Calculate Composite Score
- Apply pillar weights from the DDP's Bible
- **Option A (TRUscore, TRAgents):** Null sources excluded, weights renormalized to 1.0
- **Option B (TRScode):** Null sub-metrics contribute 0, no renormalization
- **TRSbench, TRFcast:** Pillar averages, then weighted composite with renormalization
- Apply qualification gate (minimum source count)

### Step 5: Write Output
- Build JSON with model rankings, scores, metadata
- Write to `<name>-data.json` at repo root
- Git add → commit → push to GitHub
- GitHub Pages automatically serves the updated file

### Step 6: Notify
- Send Telegram notification with model count and any failures
- Non-fatal: pipeline continues if Telegram fails

---

## Phase 3: Site Update (automatic)

- GitHub Pages detects the push
- Updated JSON files are served at their URLs
- Frontend JavaScript on index.html fetches the JSON and renders leaderboards
- No manual intervention required

---

## Error Handling

| Error | Response |
|---|---|
| Scraper fails (timeout, 404, parse error) | Log error, skip that source, continue with remaining sources |
| All sources for a DDP fail | Agent exits with non-zero code, runner logs FAILED |
| Model name not matched | Keep original scraped name in output, log mismatch |
| Git push fails | Agent exits with error, data file still written locally |
| Playwright browser crash | Agent exits, runner catches and moves to next DDP |
| Telegram fails | Non-fatal, logged as warning, agent completes normally |

---

## Dry Run Mode

When `--dry-run` is passed:
- All scraping and scoring runs normally
- Results printed to console
- **No file write, no git commit, no git push**
- Useful for testing scraper changes before going live

---

## File Dependencies

```
daily_runner.py          # Orchestrator
├── agent_trs.py         # → trs-data.json
├── agent_truscore.py    # → truscore-data.json
├── agent_trscode.py     # → trscode-data.json
├── agent_trfcast.py     # → trf-data.json
├── agent_tragents.py    # → tragent-data.json
└── model_names.py       # Shared name matching (optional)
```
