# TRAINING RUN — Production Bible
**Version 3.0 | Last Updated: February 2026**
**Website:** https://trainingrun.ai
**GitHub Repo:** https://github.com/solosevn/trainingrun-site
**Owner:** David Solomon | solosevn@gmail.com

---

## HOW TO USE THIS DOCUMENT

Read this entire file at the start of every session before touching anything. It tells you exactly what the project is, where every file lives, what every file does, what has been built, and what the standards are. Do not create new files without checking here first — everything almost certainly already exists.

---

## WHAT IS TRAINING RUN?

Training Run (trainingrun.ai) is a daily AI model scoreboard. It tracks and scores AI models across 5 independent benchmark categories, updated automatically every day. The site is a static GitHub Pages site — no server, no database. All data lives in JSON files in the repo. All pages are plain HTML/CSS/JS.

**The 5 Benchmarks:**
1. **TRSbench** — Overall AI capability composite (7 pillars, 18 sources)
2. **TRScode** — Coding ability (5 pillars, 8 sources)
3. **TRUscore** — Truthfulness / neutrality / factuality (4 pillars, 7 sources)
4. **TRFcast** — Forecasting and trading performance (5 pillars, 4 platforms)
5. **TRAgents** — Autonomous agent performance (6 pillars, 11 sources)

**Philosophy:** Independent, transparent, fact-checked. No hype. No sponsors. No ideology. Truth is verifiable or it isn't truth.

---

## ARCHITECTURE — HOW EVERYTHING CONNECTS

```
Your Mac (~/trainingrun-site)
    ↓ git push
GitHub (solosevn/trainingrun-site)
    ↓ auto-deploy (~1 min)
GitHub Pages → trainingrun.ai
```

- **Cowork/Claude** edits files in the repo, pushes to GitHub, site is live in ~1 minute
- **DDPs** (Python scrapers) run on your Mac via cron, update JSON files, push to GitHub
- **GitHub is the single source of truth** — every file lives there and is served from there
- **Your Mac's ~/trainingrun-site clone is a full backup** — git is distributed, your local copy is complete
- **The Cowork outputs folder is a scratch pad only** — never use it for project files

---

## COMPLETE FILE INVENTORY

### Python Files (The Data Pipeline)

| File | Purpose |
|------|---------|
| `daily_runner.py` | **Master orchestrator.** Runs all 5 agents in sequence. Use `python3 daily_runner.py` to run all. Use `--dry-run` to scrape without pushing. Use `--score trs` to run one agent. All 5 agents are currently ENABLED. |
| `agent_trs.py` | TRSbench scraper. Scrapes 18 sources across 7 pillars. Updates `trs-data.json`. Pushes to GitHub. Sends Telegram notification. |
| `agent_trscode.py` | TRScode scraper. Scrapes 8 sources across 5 pillars. Updates `trscode-data.json`. Pushes to GitHub. |
| `agent_truscore.py` | TRUscore scraper. Scrapes 7 sources across 4 pillars. Updates `truscore-data.json`. Pushes to GitHub. |
| `agent_trfcast.py` | TRFcast scraper. Scrapes 4 live platforms across 5 pillars. Updates `trf-data.json`. Pushes to GitHub. |
| `agent_tragents.py` | TRAgents scraper. Scrapes 11 sources across 6 pillars. Updates `tragent-data.json`. Pushes to GitHub. |
| `model_names.py` | Shared utility. Canonical model name mapping and normalization used by all agents. Do not edit without understanding all 5 agents. |
| `scripts/trs_scrapers.py` | Supporting scraper functions for TRS (older, used by agent_trs.py). |
| `scripts/trs_orchestrator.py` | Score normalization and checksum logic for TRS (older). |
| `scripts/test_scrapers.py` | Test suite for validating scrapers. Run to verify a scraper is working. |

**Agent dependencies (must be installed on your Mac):**
```
pip3 install playwright python-telegram-bot beautifulsoup4 requests
python3 -m playwright install chromium
```

**Agent env vars (set in your Mac shell profile):**
```
TELEGRAM_TOKEN     — BotFather token for notifications
TELEGRAM_CHAT_ID   — Your numeric Telegram chat ID
REPO_PATH          — Path to repo (defaults to ~/trainingrun-site)
```

### JSON Files (The Live Data)

| File | Powers | Updated By |
|------|--------|-----------|
| `trs-data.json` | TRSbench leaderboard pages | `agent_trs.py` |
| `trscode-data.json` | TRScode leaderboard pages | `agent_trscode.py` |
| `truscore-data.json` | TRUscore leaderboard pages | `agent_truscore.py` |
| `trf-data.json` | TRFcast leaderboard pages | `agent_trfcast.py` |
| `tragent-data.json` | TRAgents leaderboard pages | `agent_tragents.py` |
| `status.json` | Site health/status indicator | Pipeline |

**JSON structure (all files follow same pattern):**
- `formula_version` — version string
- `weights` — pillar weights object
- `dates[]` — array of date strings
- `models[]` — array of model objects, each with daily scores and pillar breakdowns
- `checksum` — SHA-256 hash for data integrity verification (displayed on score pages)

### HTML Files (The Website Pages)

**Homepage:**
| File | URL | Notes |
|------|-----|-------|
| `index.html` | trainingrun.ai/ | The v2 homepage. Shows all 5 benchmark scores. Interactive model cards with trend chart modal. This IS v2.html — they are the same. Do not change index.html without understanding the v2 data architecture. |
| `index-v1.html` | (not linked) | The old homepage. Kept as backup. Do not delete. |
| `v2.html` | trainingrun.ai/v2 | Same as index.html. Original v2 design file. |

**Score/Leaderboard Pages:**
| File | URL | Notes |
|------|-----|-------|
| `scores.html` | trainingrun.ai/scores | TRSbench full leaderboard |
| `tragents.html` | trainingrun.ai/tragents | TRAgents leaderboard |
| `tragents-scores.html` | trainingrun.ai/tragents-scores | TRAgents detailed scores |
| `trscode.html` | trainingrun.ai/trscode | TRScode leaderboard |
| `trscode-scores.html` | trainingrun.ai/trscode-scores | TRScode detailed scores |
| `truscore.html` | trainingrun.ai/truscore | **TRUscore methodology page** (also serves as the score page for TRUscore) |
| `truscore-scores.html` | trainingrun.ai/truscore-scores | TRUscore detailed scores |
| `trfcast.html` | trainingrun.ai/trfcast | TRFcast leaderboard |
| `trfcast-scores.html` | trainingrun.ai/trfcast-scores | TRFcast detailed scores |

**Methodology Pages (all 5 have been updated — see standards below):**
| File | URL | Notes |
|------|-----|-------|
| `trsmethodology.html` | trainingrun.ai/trsmethodology | TRSbench methodology. Has TOC sidebar. Reference page for nav/style standards. |
| `tragents-methodology.html` | trainingrun.ai/tragents-methodology | TRAgents methodology. Has TOC sidebar. |
| `trscode-methodology.html` | trainingrun.ai/trscode-methodology | TRScode methodology. Has TOC sidebar. |
| `truscore.html` | trainingrun.ai/truscore | TRUscore methodology (doubles as score page). Has TOC sidebar. |
| `trfcast-methodology.html` | trainingrun.ai/trfcast-methodology | TRFcast methodology. Has TOC sidebar. |

**Other Pages:**
| File | URL | Notes |
|------|-----|-------|
| `about.html` | trainingrun.ai/about | About page |
| `churn.html` | trainingrun.ai/churn | Model churn tracker |
| `deep-thought.html` | trainingrun.ai/deep-thought | Deep analysis page |
| `frontier.html` | trainingrun.ai/frontier | Frontier models page |
| `gigaburn.html` | trainingrun.ai/gigaburn | Energy/power tracking |
| `global-race.html` | trainingrun.ai/global-race | Global AI race tracker |
| `mission-control.html` | trainingrun.ai/mission-control | Mission control dashboard |
| `news.html` | trainingrun.ai/news | AI news page |
| `sources.html` | trainingrun.ai/sources | All data sources listed |
| `specialists.html` | trainingrun.ai/specialists | Specialist models page |

### Shared Asset Files

| File | Purpose |
|------|---------|
| `styles.css` | **Global stylesheet for the entire site.** All nav, back button, TOC sidebar, and shared component styles live here. Edit with care — changes affect every page. |
| `nav-v2.js` | Navigation JavaScript for v2 pages. |
| `CNAME` | GitHub Pages custom domain config. Contains `trainingrun.ai`. Do NOT edit. |
| `PRODUCTION_BIBLE.md` | This file. Update it every session. |

---

## DESIGN STANDARDS (DO NOT DEVIATE)

These standards were established through multiple sessions and apply to ALL pages. Any new page or edit must follow these exactly.

### Navigation Bar Standard (ALL pages)
```html
<nav>
    <a href="/" class="logo">Training Run</a>
    <ul class="nav-links">
        <li><a href="/about">About</a></li>
    </ul>
</nav>
```
- Logo is plain text "Training Run" — NO badge, NO hexagon, NO SVG icon
- Only ONE link in the nav: "About" pointing to /about
- No other links (no Verify Sources, no The Show, no Contact)
- Nav style comes from styles.css

### Back Button Standard (ALL non-homepage pages)
```html
<a href="#" onclick="history.back(); return false;" class="back-btn">
    <svg viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7"/></svg> Back
</a>
```
- Uses class `back-btn` (NOT `back-button`)
- Style comes from styles.css (fixed position, top: 80px, left: 24px)
- Goes OUTSIDE and AFTER the `<nav>` element, before the page content

### TOC Sidebar Standard (ALL methodology pages)
All 5 methodology pages have an "On This Page" fixed sidebar. Style is in styles.css.
```html
<aside class="toc-sidebar">
    <div class="toc-header">On This Page</div>
    <ul class="toc-list">
        <li><a class="toc-link" href="#section-id">Section Name</a></li>
        <li class="toc-divider"></li>
        <li><a class="toc-link" href="#section-id">Section Name</a></li>
    </ul>
</aside>
```
- Goes AFTER the back-btn, BEFORE the main content wrapper
- Hides automatically on screens ≤1100px (responsive CSS in styles.css)
- Main content wrapper needs `margin-left: 240px` at ≥1101px (added per-page)
- Each section being linked to needs an `id` attribute on the heading or section element

### Methodology Page H1 Color Standard
- Benchmark prefix (TRS, TRU, TRF, TRAgents): `color:#00d4ff` (cyan)
- Suffix and "Methodology" word: `color:#ffffff` (white)
- Example: `<span style="color:#00d4ff">TRS</span><span style="color:#ffffff">bench</span> <span style="color:#ffffff">Methodology</span>`
- NO gradient, NO `-webkit-text-fill-color`, NO `background-clip:text` on h1

### Color Palette
```
Cyan:       #00d4ff  (primary accent, links, highlights)
White:      #ffffff  (headings, primary text)
Dark BG:    #0a0a1a  (page background)
Darker BG:  #050510  (body background)
Muted text: #a0a0b0
Border:     rgba(0,212,255,0.15) subtle / rgba(0,212,255,0.3) accent
```

---

## THE DDP PIPELINE — HOW TO RUN IT

### Running Manually
```bash
cd ~/trainingrun-site

# Run all 5 agents (live — scrapes and pushes to GitHub):
python3 daily_runner.py

# Dry run (scrapes and calculates but does NOT push):
python3 daily_runner.py --dry-run

# Run just one agent:
python3 daily_runner.py --score trs
python3 daily_runner.py --score trscode
python3 daily_runner.py --score truscore
python3 daily_runner.py --score trfcast
python3 daily_runner.py --score tragents

# Check the log after a cron run:
tail -f ~/trainingrun-site/ddp.log
```

### Cron Setup (Mac — run once in Terminal to install)
**Test run at 8 PM:**
```bash
(crontab -l 2>/dev/null; echo "0 20 * * * cd ~/trainingrun-site && python3 daily_runner.py >> ~/trainingrun-site/ddp.log 2>&1") | crontab -
```

**Daily morning run at 6 AM Central:**
```bash
(crontab -l 2>/dev/null; echo "0 6 * * * cd ~/trainingrun-site && python3 daily_runner.py >> ~/trainingrun-site/ddp.log 2>&1") | crontab -
```

**View current cron jobs:**
```bash
crontab -l
```

**Remove all cron jobs (to start fresh):**
```bash
crontab -r
```

### What Each Agent Does (sequence)
1. Launches Playwright browser (headless Chromium)
2. Scrapes each benchmark source URL
3. Parses scores using BeautifulSoup
4. Normalizes scores 0-100 (top model = 100, others proportional)
5. Computes weighted composite score
6. Generates SHA-256 checksum
7. Writes updated JSON file
8. `git add → git commit → git push` to GitHub
9. Sends Telegram notification (if token configured)
10. Site updates live within ~1 minute

---

## THE 5 BENCHMARK FORMULAS

### TRSbench (agent_trs.py → trs-data.json)
7 pillars, 18 sources. Qualification: 4+ pillars with non-null scores.
- Safety: 21% (HELM Safety + AIR-Bench)
- Reasoning: 20% (ARC-AGI-2 + LiveBench + HELM Capabilities)
- Coding: 20% (SWE-bench + EvalPlus + LiveCodeBench + SWE-rebench)
- Human Preference: 18% (Arena Overall + Arena Text + AlpacaEval)
- Knowledge: 8% (MMLU-Pro + HELM MMLU + SimpleQA)
- Efficiency: 7% (Artificial Analysis + PricePerToken)
- Usage: 6% (OpenRouter Rankings)

### TRScode (agent_trscode.py → trscode-data.json)
5 pillars, 8 sources.
- Real-World Issue Resolution: 30% (SWE-bench 17% + SWE-rebench 13%)
- Code Generation: 25% (LiveCodeBench 15% + BigCodeBench 10%)
- Agentic Coding: 20% (Terminal-Bench Hard 12% + SWE-bench Pro 8%)
- Scientific & Specialized: 15% (SciCode 15%)
- Human Preference: 10% (Chatbot Arena Code Elo 10%)

### TRUscore (agent_truscore.py → truscore-data.json)
4 pillars, 7 sources.
- Factuality: 40% (SimpleQA 20% + NewsGuard AI Monitor 20%)
- Neutrality: 30% (TrackingAI Political Compass 25% + Anthropic Paired Prompts 5%)
- Hallucination: 20% (Vectara Leaderboard 15% + Artificial Analysis Omniscience 5%)
- Calibration: 10% (SimpleQA Not Attempted Rate 10%)

### TRFcast (agent_trfcast.py → trf-data.json)
5 pillars, 4 platforms, 9 sub-metrics.
- Forecasting Accuracy: 30% (ForecastBench baseline 20% + tournament 10%)
- Trading Performance: 25% (Rallies.ai returns 15% + Alpha Arena returns 10%)
- Prediction Calibration: 20% (ForecastBench calibration 20%)
- Financial Reasoning: 15% (FinanceArena QA 8% + comparative ELO 7%)
- Market Intelligence: 10% (Alpha Arena Sharpe 5% + Rallies win rate 5%)

### TRAgents (agent_tragents.py → tragent-data.json)
6 pillars, 11 sources. Qualification: 3+ pillars with non-null scores.
- Task Completion: 25% (GAIA 8% + SWE-bench Verified 7% + tau-bench 5% + OSWorld 5%)
- Cost Efficiency: 20% (ARC-AGI-2 12% + Artificial Analysis 8%)
- Tool Reliability: 20% (MCP Atlas 12% + Galileo Agent Leaderboard 8%)
- Safety & Security: 15% (MASK Benchmark 15%)
- Accessibility: 10% (Ollama Library 10%)
- Multi-Model Efficiency: 10% (OpenRouter Rankings 10%)

---

## HOMEPAGE (index.html / v2.html) — KEY FEATURES

The homepage uses a sophisticated v2 data architecture. Key things to know before touching it:

- Loads all 5 JSON files on page load
- Shows model cards with scores across all 5 benchmarks
- Each card has a modal with tabs: Overview, Performance Trend, Breakdown, Sources
- The **Performance Trend tab** has a custom Chart.js chart with:
  - Big white hero score at top that updates on hover/scrub
  - Floating tooltip following cursor/finger
  - Glow line effect (shadowBlur)
  - Gradient fill under the line
  - Touch support for mobile scrubbing
  - Board label at bottom in cyan/white
- The trend chart is built by `_buildV2TrendChart()` function in index.html's JS
- Data is stored in `V2_DATA` and `V2_BOARD_LABEL_HTML` objects

---

## GITHUB REPO SAFETY

**Is it safe?** Yes. Here's the full picture:

**What you have (3 copies of everything):**
1. GitHub servers (in the cloud)
2. Your Mac at `~/trainingrun-site` (local clone — this IS a full backup)
3. Cowork VM while sessions are active

**Real risks and how to handle them:**
- Account hack → **Enable 2FA on github.com immediately if not done**
- Accidental `git push --force` → would overwrite remote but local copy survives
- Mac crashes → GitHub copy survives
- GitHub goes down → your Mac copy survives; you can re-push when it's back

**For external drive backup**, run this anytime on your Mac:
```bash
cp -r ~/trainingrun-site /Volumes/YOUR_DRIVE_NAME/trainingrun-backup-$(date +%Y%m%d)
```

**Or clone to external drive directly:**
```bash
git clone ~/trainingrun-site /Volumes/YOUR_DRIVE_NAME/trainingrun-site
```

---

## HOW TO START A NEW SESSION WITH CLAUDE

Copy and paste this at the start of every new Cowork session:

---
*"Read the Production Bible at ~/trainingrun-site/PRODUCTION_BIBLE.md before doing anything. The repo is at /sessions/[session-id]/trainingrun-site — check the actual path. Do not create any new files without consulting the Bible first. Here's what I want to work on today: [YOUR TASK]"*

---

The session-id in the path changes every session. The easiest way to find the repo:
```bash
find /sessions -name "PRODUCTION_BIBLE.md" 2>/dev/null
```

---

## VERSION HISTORY

- **v3.0** (February 2026) — Complete rewrite. Full file inventory, design standards, DDP pipeline docs, benchmark formulas, GitHub safety, session startup guide. Reflects all work through February 2026.
- **v2.6** (February 12, 2026) — Added TRFcast methodology
- **v2.4** (February 9, 2026) — Updated TRS weights
- **v1.0** (January 30, 2026) — Initial bible

---

## RECENT WORK COMPLETED (February 2026)

- **Homepage:** Shipped v2.html as new index.html. Interactive model cards with 5-benchmark modal, trend chart with scrub/hover, touch support for mobile.
- **Trend chart redesign:** White hero score, floating tooltip, glow line, gradient fill, board label at bottom (cyan TRS + white bench).
- **Nav cleanup:** All pages standardized — plain "Training Run" text logo, only "About" in nav, no other links.
- **Back button standardized:** All pages use `.back-btn` class from styles.css, fixed position.
- **Methodology pages (all 5):** H1 colors standardized (cyan prefix + white suffix/Methodology). H1 gradient bug fixed on trscode.
- **TOC sidebar:** "On This Page" sidebar added to all 5 methodology pages. CSS in styles.css. Hides on mobile.
- **Old homepage saved** as index-v1.html.
- **DDP pipeline:** All 5 agents enabled in daily_runner.py. Cron setup documented above.
