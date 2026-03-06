# CONFIG — DDP Pipeline

> **Version:** 1.0 — March 6, 2026

---

## Execution Environment

| Setting | Value |
|---|---|
| **Runtime** | Python 3.x on David's Mac |
| **Schedule** | Daily 4:00 AM CST via launchd |
| **Orchestrator** | `daily_runner.py` (repo root) |
| **Repo path** | `~/trainingrun-site/` |
| **Browser** | Playwright Chromium (headless) |

---

## Dependencies

```
playwright
python-telegram-bot
beautifulsoup4
requests
```

Plus: `python3 -m playwright install chromium`

Optional: `model_names.py` (for roster name matching — `match_name()`, `canonicalize()`)

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `TELEGRAM_TOKEN` | BotFather token for notifications |
| `TELEGRAM_CHAT_ID` | David's numeric chat ID |
| `REPO_PATH` | Path to local repo clone (default: `~/trainingrun-site`) |

---

## Agent Scripts & Output Files

| DDP | Script | Output JSON | Bible |
|---|---|---|---|
| TRSbench | `agent_trs.py` (64K) | `trs-data.json` | TRSbench V2.5 |
| TRUscore | `agent_truscore.py` (63K) | `truscore-data.json` | TRUscore V1.4 |
| TRScode | `agent_trscode.py` (36K) | `trscode-data.json` | TRScode V1.0 |
| TRFcast | `agent_trfcast.py` (34K) | `trf-data.json` | TRFcast V1.0 |
| TRAgents | `agent_tragents.py` (49K) | `tragent-data.json` | TRAgents V1.0 |

---

## Enable/Disable Switches (in daily_runner.py)

```python
ENABLED = {
    "trscode":  True,
    "trfcast":  True,
    "trs":      True,
    "truscore": True,
    "tragents": True,
}
```

Set any to `False` to skip that DDP during daily run.

---

## Run Modes

```bash
python3 daily_runner.py                    # run all enabled agents
python3 daily_runner.py --dry-run          # scrape but don't push
python3 daily_runner.py --score trs        # run one score only
python3 daily_runner.py --score trs --dry-run

# Individual agent runs:
python3 agent_truscore.py                  # live run (push to GitHub)
python3 agent_truscore.py --dry-run        # scrape + print, NO write/push
python3 agent_truscore.py --test-telegram  # test Telegram only
```

---

## Telegram Notifications

- Bot: Uses same `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` as other agents
- Each agent sends completion notification with model count and any failures
- Non-fatal: if Telegram fails, the agent still completes its run

---

## Git Push Behavior

Each agent independently:
1. Writes its `-data.json` file to repo root
2. Runs `git add <file>`, `git commit`, `git push`
3. Commit message format: auto-generated with date and score name

---

## Model Name Matching

All agents use `model_names.py` (when available) for fuzzy matching:
1. Exact match (case-insensitive)
2. Substring containment (min 4 chars)
3. Fuzzy match via `difflib.get_close_matches()` (threshold 0.82)

Plus `_normalize_model_name()` strips API version suffixes like `-2024-08-06` and `-instruct`.

---

## Playwright Configuration

- **Headless:** Always `True` (runs without display)
- **User-Agent:** Chrome 122 on macOS
- **Default wait:** 5000ms after page load
- **HuggingFace Spaces:** Special handler with 15000ms wait + iframe detection
- **Timeout:** 90 seconds per page load

---

## Data File Locations (all at repo root)

| File | Updated by | Consumed by |
|---|---|---|
| `trs-data.json` | agent_trs.py | index.html (TRSbench leaderboard) |
| `truscore-data.json` | agent_truscore.py | index.html (TRUscore leaderboard) |
| `trscode-data.json` | agent_trscode.py | index.html (TRScode leaderboard) |
| `trf-data.json` | agent_trfcast.py | index.html (TRFcast leaderboard) |
| `tragent-data.json` | agent_tragents.py | index.html (TRAgents leaderboard) |
| `agent_activity.json` | TRS Site Manager | mission-control.html |
