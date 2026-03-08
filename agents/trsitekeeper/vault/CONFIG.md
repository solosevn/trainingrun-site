# CONFIG â TRS Site Manager (TRSitekeeper)

> **Version:** 1.1 â March 6, 2026
> **Purpose:** Technical configuration, execution environment, tools, and thresholds

---

## Execution Environment

| Parameter | Value |
|---|---|
| Model | Claude Sonnet 4.6 (`claude-sonnet-4-6`) |
| Previous model | Ollama / llama (upgraded Feb 24, 2026) |
| Runtime | Python 3 â `agent.py` via Telegram bot |
| Host | David's Mac (local execution) |
| API | Anthropic Claude API (direct) |
| Communication | Telegram Bot API |
| Repo | `solosevn/trainingrun-site` (GitHub Pages) |
| Branch | `main` (single branch â pushes go live immediately) |
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

## Vault Loading Protocol

**CRITICAL: This vault is operational, not decorative.**

On every agent startup:
1. Load all 9 vault files from `context-vault/agents/trainingrun/trs-site-manager/`
2. Parse SOUL.md for mission alignment and David's principles
3. Parse CONFIG.md for current environment state
4. Parse PROCESS.md for operational procedures
5. Parse CADENCE.md for today's audit focus
6. Parse STYLE-EVOLUTION.md for active design rules
7. Check RUN-LOG.md for recent entries â know what happened last
8. Check LEARNING-LOG.md for known issues â don't repeat mistakes
9. Check CAPABILITIES.md for current vs. planned capabilities
10. Check TASK-LOG.md for active tasks

On every session end:
1. Append to RUN-LOG.md â what was done this session
2. Update LEARNING-LOG.md if a new lesson was learned
3. Promote rules in STYLE-EVOLUTION.md if confidence changed

This is not optional. An agent that doesn't read its own memory is just a stateless script.

---

## Managed File Inventory (49 files)

### Core HTML Pages
- `index.html` â Main leaderboard page (THE critical file)
- `tsarena.html` â The Safety Arena battle/voting page
- `tsarena-leaderboard.html` â TSArena rankings
- `methodology.html` â Scoring methodology explainer
- `news.html` â Daily news display
- `about.html` â About page

### Python Scripts
- `web_agent/agent.py` â This agent's execution file
- `daily_runner.py` â DDP cron orchestrator
- `agent_trs.py` â TRSbench DDP agent
- `agent_truscore.py` â TRUscore DDP agent
- `agent_trscode.py` â TRScode DDP agent
- `agent_trfcast.py` â TRFcast DDP agent
- `agent_tragents.py` â TRAgents DDP agent
- `model_names.py` â Fuzzy model name matching

### Data Files (DDP outputs)
- `trs-data.json` â TRSbench scores
- `truscore-data.json` â TRUscore scores
- `trscode-data.json` â TRScode scores
- `trf-data.json` â TRFcast scores
- `tragent-data.json` â TRAgents scores

### Supporting Files
- `styles.css` â Global styles
- `CNAME` â Domain configuration
- `robots.txt` â Search engine directives
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
- Reading and writing vault files (RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION)

### Ask David First
- Running DDP agents (triggers data refresh)
- Deleting any file
- Structural changes (adding/removing pages)
- Any irreversible action
- Changes to agent.py itself
- Anything that changes how data is presented to the public (David's name is on it)

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

Every file edit triggers: `backup_file(filename)` â saves to `backups/` directory with timestamp. No exceptions. Military discipline â no shortcuts.

---

## Cost Controls

| Parameter | Value |
|---|---|
| Daily audit budget | ~1 hour active processing |
| Audit priority | High-traffic pages first (index.html, tsarena.html) |
| Batch non-urgent findings | Yes â daily summary to David |
| Immediate alerts | Site down, data corruption, broken layout only |
