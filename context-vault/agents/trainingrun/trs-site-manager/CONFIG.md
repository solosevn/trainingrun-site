# CONFIG — TRS Site Manager (TRSitekeeper)

> **Version:** 1.0 — March 6, 2026
> **Purpose:** Technical configuration, execution environment, tools, and thresholds

---

## Execution Environment

| Parameter | Value |
|---|---|
| Model | Claude Sonnet 4.6 (`claude-sonnet-4-6`) |
| Previous model | Ollama / llama (upgraded Feb 24, 2026) |
| Runtime | Python 3 — `agent.py` via Telegram bot |
| Host | David's Mac (local execution) |
| API | Anthropic Claude API (direct) |
| Communication | Telegram Bot API |
| Repo | `solosevn/trainingrun-site` (GitHub Pages) |
| Branch | `main` (single branch — pushes go live immediately) |
| Site URL | https://trainingrun.ai |

---

## File Locations

| Component | Path |
|---|---|
| Agent script | `web_agent/agent.py` |
| Brain file | `web_agent/brain.md` |
| Agent README | `web_agent/README_AGENT.md` |
| Activity tracker | `agent_activity.json` |
| DDP orchestrator | `daily_runner.py` |
| Main site page | `index.html` |
| Vault (this dir) | `context-vault/agents/trainingrun/trs-site-manager/` |
| DDP Pipeline vault | `context-vault/agents/trainingrun/trs-site-manager/ddp-pipeline/` |

---

## Managed File Inventory (49 files)

### Core HTML Pages
- `index.html` — Main leaderboard page (THE critical file)
- `tsarena.html` — The Safety Arena battle/voting page
- `tsarena-leaderboard.html` — TSArena rankings
- `methodology.html` — Scoring methodology explainer
- `news.html` — Daily news display
- `about.html` — About page

### Python Scripts
- `web_agent/agent.py` — This agent's execution file
- `daily_runner.py` — DDP cron orchestrator
- `agent_trs.py` — TRSbench DDP agent
- `agent_truscore.py` — TRUscore DDP agent
- `agent_trscode.py` — TRScode DDP agent
- `agent_trfcast.py` — TRFcast DDP agent
- `agent_tragents.py` — TRAgents DDP agent
- `model_names.py` — Fuzzy model name matching

### Data Files (DDP outputs)
- `trs-data.json` — TRSbench scores
- `truscore-data.json` — TRUscore scores
- `trscode-data.json` — TRScode scores
- `trf-data.json` — TRFcast scores
- `tragent-data.json` — TRAgents scores

### Supporting Files
- `styles.css` — Global styles
- `CNAME` — Domain configuration
- `robots.txt` — Search engine directives
- Various image/asset files

---

## Brand DNA (Never Break)

| Element | Value |
|---|---|
| Primary cyan | `#00d4ff` |
| TRAgents red | `#ff3333` |
| Background | `#0a0f1a` |
| Font stack | System fonts (no external CDN) |
| Design language | Dark, data-dense, terminal-inspired |

---

## Autonomy Rules

### Auto-Execute (No Permission Needed)
- Reading any file in the repo
- Status checks (git status, site checks)
- Creating backups via `backup_file()`
- Editing files (with backup first)
- Git commit + push
- Daily audit cycles
- Sending findings/suggestions to David via Telegram

### Ask David First
- Running DDP agents (triggers data refresh)
- Deleting any file
- Structural changes (adding/removing pages)
- Any irreversible action
- Changes to agent.py itself

---

## Git Workflow

```
1. git pull --rebase          # Always first
2. backup_file(target)        # Before any edit
3. Edit file                  # One file at a time
4. git add <specific-file>    # Never git add -A
5. git commit -m "descriptive message"
6. git push
```

---

## Backup Protocol

Every file edit triggers: `backup_file(filename)` → saves to `backups/` directory with timestamp. No exceptions.

---

## Cost Controls

| Parameter | Value |
|---|---|
| Daily audit budget | ~1 hour active processing |
| Audit priority | High-traffic pages first (index.html, tsarena.html) |
| Batch non-urgent findings | Yes — daily summary to David |
| Immediate alerts | Site down, data corruption, broken layout only |
