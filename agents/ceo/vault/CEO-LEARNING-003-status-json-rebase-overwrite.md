# CEO-LEARNING-003: status.json Rebase Overwrite — Mission Control Shows 2 of 5 Scores

## Classification
- **Severity:** High — Mission Control dashboard missing 60% of DDP score data
- **Category:** Multi-agent git conflict / race condition
- **Related to:** CEO-LEARNING-002 (DDP pipeline restructure breakage)
- **Date:** March 9, 2026

---

## 1. Incident Timeline

| Time | Event |
|------|-------|
| Feb 26, 6:23 AM | TRSitekeeper "Status" command shows ALL 5 DDPs working: trscode 74.8, trfcast 62.3, truscore 97.8, tragents 79.4, trsbench 76.8. Everything healthy. |
| Mar 8, 2026 | V10 repo restructure performed — agents moved to `agents/` hierarchy, files reorganized |
| Mar 8, ~evening | CEO-LEARNING-002 fixes deployed — DDP pipeline path resolution restored |
| Mar 9, 4:00 AM CST | Cron fires daily_runner.py — all 5 scrapers execute sequentially on David's Mac |
| Mar 9, 6:07 AM | David types "Status" in TRSitekeeper — response: **"status.json not found"** (paths still broken at this point) |
| Mar 9, 7:49 AM | TrainingRun Bot posts TRAgents Top 5 and "DDP done!" — scrapers completed their run |
| Mar 9, 8:46 AM | David types "Status" in TRSitekeeper — response shows **only 2 DDPs**: truscore 88.9, tragents 78.5. Three missing. |
| Mar 9, ~8:50 AM | Investigation begins. Mission Control confirms: 2 LIVE agents, not 5 |
| Mar 9, ~9:00 AM | Root cause identified: `-X theirs` rebase overwrite in each scraper's `git_push()` |
| Mar 9, 8:53 AM | Fix deployed: `git pull` on Mac pulled 6 commits, live test run started |
| Mar 9, 9:10 AM | Live test completes. Terminal shows: "status.json pushed to GitHub". Mission Control shows **4 LIVE agents** (TRSbench excluded — timed out at 300s, pre-existing issue) |

---

## 2. Infrastructure Context — How the DDP Pipeline Works

**A CEO agent MUST know this. There is no excuse for not knowing how the scrapers run.**

### The Cron Job
- **Schedule:** `0 4 * * *` — runs daily at 4:00 AM CST
- **Location:** David's MacBook Pro, configured via `crontab -e`
- **Crontab entry:**
```
TELEGRAM_TOKEN=8575280567:AAFeI4t5ZTMPe...
TELEGRAM_CHAT_ID=8054313621
0 4 * * * cd ~/trainingrun-site/agents/ddp && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_runner.py >> ~/trainingrun-site/ddp.log 2>&1
```
- **Why the full Python path:** Cron has a minimal PATH and won't find Playwright otherwise
- **Why env vars in crontab header:** Cron doesn't source `.zshrc`, so Telegram bot tokens must be set explicitly
- **Git auth in cron:** PAT (Personal Access Token) embedded in the remote URL because cron can't access macOS Keychain
- **The cron is NOT in the GitHub repo.** It's a system-level cron on David's Mac. This is important — you can't find it by searching the codebase.

### The Run Sequence
1. `daily_runner.py` is the orchestrator. It runs all 5 scrapers sequentially via `subprocess.run()`.
2. Run order: TRScode → TRFcast → TRSbench → TRUscore → TRAgents
3. Each scraper is a separate Python process launched by daily_runner.py
4. Each scraper: scrapes data → writes its JSON data file → writes to status.json `agents` section → pushes its data file to GitHub
5. After each scraper, daily_runner.py calls `update_status()` to write the `ddp` section of status.json
6. After ALL scrapers, daily_runner.py does one final push of status.json (this is our new fix)

### Telegram Notifications
- Each scraper posts progress to the **TrainingRun Bot** on Telegram as it runs:
  - "TRScode DDP starting" with date, mode, sources count
  - "Scraping complete" with per-source match counts
  - "TRScode Top 5" with top models and scores
  - "TRScode DDP done!" with model count and link
- David can type **"Status"** in the **TRSitekeeper** bot to get a Mission Control status readout showing all DDP scores
- TRSitekeeper's status monitoring was moved to TRSitekeeper from TrainingRun Bot during/after the V10 restructure

### How to Trigger a Manual Test Run
From David's Mac terminal:
```bash
cd ~/trainingrun-site && git pull
cd ~/trainingrun-site/agents/ddp && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_runner.py
```
The `git pull` is critical — it pulls any code changes from GitHub before running. Without it, old code runs.

For dry-run (scrape but don't push):
```bash
cd ~/trainingrun-site/agents/ddp && python3 daily_runner.py --dry-run
```

For a single score:
```bash
cd ~/trainingrun-site/agents/ddp && python3 daily_runner.py --score trscode
```

### The Repo = The Live Site
`trainingrun-site` is a GitHub Pages site. Push to `main` = live in ~60 seconds. The repo root IS the web root. `status.json` at repo root is served at `trainingrun.ai/status.json`.

---

## 3. Symptoms

- Mission Control at trainingrun.ai/mission-control.html showed **only 2 agent cards** (TRUscore and TRAgents) instead of all 5
- David typed "Status" in TRSitekeeper at 8:46 AM — got only 2 DDPs back (truscore, tragents)
- Compare to Feb 26: same "Status" command returned all 5 DDPs with scores
- The `status.json` file on GitHub contained:
  - `ddp` section: all 5 scrapers present with timestamps and success flags
  - `agents` section: only 2 scrapers present (TRUscore and TRAgents — the last two in run order)
- `last_updated` field was current (March 9), confirming the pipeline ran
- The `ddp` section having all 5 entries proves all scrapers executed — the data loss was specifically in the `agents` section

---

## 4. Wrong Assumptions

### Assumption 1: "status.json isn't loading"
**Reality:** status.json WAS loading. The CEO-LEARNING-002 fix resolved the path issues. The problem was that the file existed and loaded correctly — it just had incomplete data. This is a subtler failure mode: the system looks like it's working (no errors, file loads, some data shows) but is silently losing data.

### Assumption 2: "Each scraper independently manages its own section of status.json"
**Reality:** While each scraper's `write_status()` function correctly reads the existing status.json, merges its data into the `agents` section, and writes back — the **git push** step undoes this. The `git pull --rebase -X theirs` flag tells git "on any conflict, take the remote version" — which means each scraper's carefully-merged status.json gets replaced by whatever was on GitHub.

### Assumption 3: "The DDP section proves the pipeline works, so the agents section should too"
**Reality:** The `ddp` section survives because daily_runner.py writes it locally after each scraper and it just accumulates. The `agents` section gets clobbered at each push because the `-X theirs` rebase discards local changes in favor of the remote.

### Assumption 4: "This bug was introduced by the V10 restructure"
**Reality:** The `-X theirs` flag has always been in the scrapers' `git_push()` functions. Before the restructure, it didn't manifest because either: (a) the scrapers weren't all running reliably, or (b) the `agents` section of status.json wasn't being populated by all scrapers. The restructure restored full functionality, which exposed the pre-existing race condition. **Fixing one bug exposed a second, deeper bug.**

---

## 5. Actual Root Cause

### The Rebase Overwrite Race Condition

Each scraper has a `git_push()` function with this pattern:

```python
subprocess.run(["git", "add", "<data-file>.json", "status.json"], cwd=REPO_PATH, ...)
subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_PATH, ...)
subprocess.run(["git", "stash", "--include-untracked"], cwd=REPO_PATH, ...)
subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"], cwd=REPO_PATH, ...)
subprocess.run(["git", "push"], cwd=REPO_PATH, ...)
subprocess.run(["git", "stash", "pop"], cwd=REPO_PATH, ...)
```

The critical line is `git pull --rebase -X theirs`. The `-X theirs` strategy means: **"When there's a conflict during rebase, automatically resolve it by keeping the remote version."**

### Step-by-step destruction during a full DDP run:

**Scraper 1 (TRScode) runs:**
- `write_status()` adds `agents.trscode` to status.json locally
- `git_push()` adds status.json, commits, pushes
- GitHub now has: `{agents: {trscode: {...}}}`

**Scraper 2 (TRFcast) runs:**
- `write_status()` reads local status.json (has trscode from scraper 1), adds trfcast
- Local status.json: `{agents: {trscode: {...}, trfcast: {...}}}`
- `git_push()` does `git add status.json`, `git commit`
- Then `git pull --rebase -X theirs` — **CONFLICT** on status.json
- `-X theirs` resolves by keeping the REMOTE version: `{agents: {trscode: {...}}}` — trfcast data is **DISCARDED**
- `git push` pushes the remote's version — scraper 2's agent data is gone

**Scraper 3 (TRSbench)** — same pattern. Times out at 300s, no push.

**Scraper 4 (TRUscore)** — same rebase overwrite pattern, but...

**Scraper 5 (TRAgents)** — the LAST scraper. Its push doesn't get overwritten because no subsequent scraper does a `-X theirs` after it.

**Result:** Only the last 1-2 scrapers' agent data survives. In practice, TRUscore (#4) and TRAgents (#5) are the ones that show up — exactly what David saw.

### Why the `ddp` section survived
The `ddp` section is written by `daily_runner.py`'s `update_status()` function after each scraper completes. Since daily_runner.py doesn't push to git itself (before our fix), the `ddp` data just accumulates locally in status.json. The final scraper's push includes the complete `ddp` section because it was never subject to rebase conflict — it was always the same local accumulation.

### The deeper design flaw
The architecture assumed each scraper could independently push status.json without interfering. This is fundamentally broken when scrapers run sequentially and each does `git pull --rebase -X theirs`. The `-X theirs` flag was added to prevent push failures, but it created a worse problem: **silent data loss with no error messages.**

---

## 6. Debugging Methodology

### Step 1: Verify what Mission Control actually shows
Navigated to trainingrun.ai/mission-control.html. Confirmed: 2 agent cards (TRUscore 88.9, TRAgents 78.5), "Updated 9m ago." The file loads — data is incomplete.

### Step 2: Inspect the live status.json
Fetched `/status.json` from trainingrun.ai via JavaScript:
- `ddp` section: all 5 keys present (trs, trscode, trfcast, truscore, tragents)
- `agents` section: only 2 keys (truscore, tragents)
- This discrepancy between `ddp` (complete) and `agents` (incomplete) was the **critical clue**

### Step 3: Understand the two sections
- `ddp` section: written by daily_runner.py's `update_status()` — simple success/fail/timestamp per scraper
- `agents` section: written by each scraper's `write_status()` — rich card data (name, label, emoji, top5, scores)
- daily_runner.py doesn't push to git; individual scrapers do

### Step 4: Trace the git push flow
Read each scraper's `git_push()` function source code on GitHub. Found the `git pull --rebase -X theirs` pattern in all 5. Realized that including `status.json` in each scraper's `git add` combined with `-X theirs` rebase creates a destructive overwrite pattern.

### Step 5: Confirm hypothesis
The last two scrapers in the run order (TRUscore and TRAgents) are exactly the two that appear in the live `agents` section. This perfectly matches the theory: only the last scrapers' data survives the rebase chain.

### Step 6: Cross-reference with the Feb 26 working state
On Feb 26, TRSitekeeper's "Status" command showed all 5 DDPs working. This means either: the `-X theirs` bug wasn't present before, the scrapers weren't all writing to the `agents` section before, or the race condition wasn't triggering. The V10 restructure work likely changed how/when scrapers write to status.json, exposing the latent bug.

---

## 7. The Fix

### Part A: Remove status.json from individual scraper pushes (5 files)

Each scraper's `git_push()` function had:
```python
subprocess.run(["git", "add", "<data-file>.json", "status.json"], ...)
```

Changed to:
```python
subprocess.run(["git", "add", "<data-file>.json"], ...)
```

Files modified:
- `agents/ddp/agent_trscode.py` (line 685) — removed `"status.json"` from git add
- `agents/ddp/agent_trfcast.py` (line 636) — removed `"status.json"` from git add
- `agents/ddp/agent_trs.py` (line 1171) — removed `"status.json"` from git add
- `agents/ddp/agent_truscore.py` (line 1139) — removed `"status.json"` from git add
- `agents/ddp/agent_tragents.py` (line 947) — removed `"status.json"` from git add

Now each scraper only pushes its own data file (e.g., `trs-data.json`). status.json is modified locally by `write_status()` but NOT included in the git add/commit/push cycle.

### Part B: Add consolidated status.json push to daily_runner.py

Added to `daily_runner.py`:

1. **`REPO_PATH`** constant (line 65): `os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))` — points to repo root

2. **`push_status()` function** (lines 96-113):
```python
def push_status(dry_run: bool):
    """Git add, commit, and push status.json after all scrapers complete."""
    if dry_run:
        log("  [DRY RUN] Skipping status.json push")
        return
    try:
        subprocess.run(["git", "add", "status.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", "Update status.json after DDP run"],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if "nothing to commit" in (r.stdout + r.stderr):
            log("  status.json unchanged — nothing to push")
            return
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        log("  status.json pushed to GitHub")
    except Exception as e:
        log(f"  WARNING: Could not push status.json: {e}")
```

3. **`push_status(args.dry_run)`** called in both:
   - Single-score path (after `update_status`, before `sys.exit`)
   - All-scores path (after summary block, before function ends)

### Why this works
All 5 scrapers write their agent data to status.json locally via `write_status()`. Since they run sequentially on the same machine, the data accumulates correctly in the local file. After ALL scrapers finish, daily_runner.py does ONE push of the complete status.json. No rebase conflicts possible because status.json is only pushed once, not 5 times.

---

## 8. Live Test Verification — March 9, 2026

### Test execution
David ran these commands on his Mac at 8:53 AM:
```bash
cd ~/trainingrun-site && git pull
# Output: 6 files changed, 29 insertions(+), 5 deletions(-)
# All 5 scraper files + daily_runner.py updated

cd ~/trainingrun-site/agents/ddp && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_runner.py
```

### Terminal output
```
[2026-03-09 08:53:20] TrainingRun Daily Runner — starting
[2026-03-09 08:53:20]   Mode: LIVE
[2026-03-09 08:53:20]   START TRScode (agent_trscode.py)
[2026-03-09 08:56:15]   DONE  TRScode ✓
[2026-03-09 08:56:15]   START TRFcast (agent_trfcast.py)
[2026-03-09 08:57:01]   DONE  TRFcast ✓
[2026-03-09 08:57:01]   START TRSbench (agent_trs.py)
[2026-03-09 09:02:01]   TIMEOUT TRSbench (>300s)
[2026-03-09 09:02:01]   START TRUscore (agent_truscore.py)
[2026-03-09 09:05:37]   DONE  TRUscore ✓
[2026-03-09 09:05:37]   START TRAgents (agent_tragents.py)
[2026-03-09 09:10:32]   DONE  TRAgents ✓
[2026-03-09 09:10:32] SUMMARY
[2026-03-09 09:10:32]   Passed: 4  Failed: 1  Skipped: 0
[2026-03-09 09:10:32]   ✓ TRScode
[2026-03-09 09:10:32]   ✓ TRFcast
[2026-03-09 09:10:32]   ✗ TRSbench
[2026-03-09 09:10:32]   ✓ TRUscore
[2026-03-09 09:10:32]   ✓ TRAgents
[2026-03-09 09:10:32] status.json pushed to GitHub    ← OUR FIX WORKING
```

### Telegram confirmation
All scrapers posted their progress to TrainingRun Bot:
- TRScode: 8 sources, 38 models, Top 5 led by Claude Opus 4.6 (75.2) — done at 8:56 AM
- TRFcast: 4 sources, 11 models, Top 5 led by Claude Sonnet 4.5 (62.9) — done at 8:57 AM
- TRSbench: Started at 8:57 AM, loaded 66 models, but timed out at 300s (pre-existing issue)
- TRUscore V1.4: 9 sub-metrics, 18 models — done at 9:05 AM
- TRAgents: 6 pillars, 19 models, Top 5 led by Gemini 3 Flash (70.0) — done at 9:10 AM

### Mission Control result
After the run, Mission Control showed:
- **4 LIVE agents** (up from 2):
  - TRUscore DDP — 88.9
  - TRScode DDP — 75.2
  - TRFcast DDP — 62.9
  - TRAgents DDP — 70.0
- **"Updated 2m ago"** — timestamp working
- **Content Scout — 10 stories, LIVE**
- **TRSbench absent** — expected, it timed out (>300s). This is a separate pre-existing issue.

### Verdict: FIX VERIFIED
Before: 2 of 5 scores showing. After: 4 of 4 successful scrapers showing. The only missing score (TRSbench) is due to its timeout, not our fix. The `-X theirs` rebase overwrite bug is resolved.

---

## 9. Critical Lessons

### Lesson 1: `-X theirs` is a data-loss footgun in multi-writer pipelines
The `-X theirs` rebase strategy silently discards local changes when conflicts occur. In a pipeline where multiple agents write to the same file and push sequentially, this guarantees data loss for all but the last writer. **Never use `-X theirs` when multiple processes write to the same file.**

### Lesson 2: "File loads correctly" does not mean "file has correct data"
The initial symptom looked like "status.json might not be loading" but the real problem was silent data truncation. A CEO agent must check not just that files exist and load, but that they contain ALL expected data. 5 DDP scores expected, only 2 present = 60% data loss.

### Lesson 3: Sequential push patterns need centralized coordination
When multiple agents write to a shared resource, the push should happen ONCE from a coordinator (daily_runner.py), not independently from each agent. Writes accumulate locally, a single coordinator commits the aggregate. This is standard distributed systems practice.

### Lesson 4: The `ddp` vs `agents` section discrepancy is the diagnostic smoking gun
`ddp` had all 5 entries, `agents` only had 2. This immediately points to a write-path difference. `ddp` was written by daily_runner.py (centralized, local accumulation), `agents` was written by individual scrapers (distributed, each pushes and overwrites). **"Which section is complete vs incomplete and who writes each"** — this should be the CEO agent's first diagnostic question.

### Lesson 5: Silent failures are worse than loud failures
If `-X theirs` had failed loudly, the bug would have been caught immediately. Instead it "succeeded" by silently discarding data. **A CEO agent should prefer loud failures over silent data loss.**

### Lesson 6: Always test end-to-end, not just individual components
Each scraper's `write_status()` works perfectly in isolation. Each `git_push()` works in isolation. The bug only manifests when all 5 run in sequence. Testing must cover the full pipeline flow.

### Lesson 7: KNOW YOUR INFRASTRUCTURE
The CEO agent must know: where the cron is (David's Mac, `crontab -l`), how to trigger a manual run, how to verify via Telegram, how to check Mission Control. Not knowing how the pipeline runs is unacceptable. This is documented in TRSitekeeper's brain.md under "CRON AUTOMATION."

### Lesson 8: Fixing one bug often exposes a second
CEO-LEARNING-002 fixed the DDP pipeline paths. Once scrapers ran successfully again, the pre-existing `-X theirs` race condition became visible. **After any major fix, validate not just the fixed component but all downstream consumers.**

---

## 10. What the CEO Agent Would Have Done Differently

1. **Known the infrastructure from day one:** Read TRSitekeeper's brain.md during onboarding. Know the cron, the Telegram bots, the run sequence, the Mac setup. Never be caught saying "I don't know how the scrapers run."

2. **Pre-flight check on status.json completeness:** After each DDP run, automatically verify that the `agents` section contains entries for every enabled scraper. Alert immediately if count doesn't match enabled count.

3. **Detected the ddp/agents discrepancy automatically:** A simple comparison — "ddp has 5 keys, agents has 2 keys, these should match" — would have flagged this within minutes.

4. **Audited git conflict resolution strategies during V10 review:** Flagged `-X theirs` as dangerous for any file written by multiple agents. The correct question: "What happens when scraper 2 pushes after scraper 1, and both modified status.json?"

5. **Recommended centralized-push pattern from day one:** daily_runner.py should handle all shared-state coordination. Individual scrapers push only their own data files.

6. **Triggered a live test immediately after deploying fixes:** Don't wait for the next cron run. `git pull && python3 daily_runner.py` on David's Mac, watch the terminal output and Mission Control in real time. Verify the fix, don't assume.

7. **Set up a post-run validation check:** After daily_runner.py completes, fetch the live status.json from GitHub Pages and verify all expected sections are populated. If any are missing, alert David via Telegram.

---

## 11. Commits Made

| # | File | Commit Message | Change |
|---|------|---------------|--------|
| 1 | agents/ddp/agent_trscode.py | Fix: remove status.json from agent_trscode.py git add to prevent rebase overwrite | Removed `"status.json"` from git add on line 685 |
| 2 | agents/ddp/agent_trfcast.py | Fix: remove status.json from agent_trfcast.py git add to prevent rebase overwrite | Removed `"status.json"` from git add on line 636 |
| 3 | agents/ddp/agent_trs.py | Fix: remove status.json from agent_trs.py git add to prevent rebase overwrite | Removed `"status.json"` from git add on line 1171 |
| 4 | agents/ddp/agent_truscore.py | Fix: remove status.json from agent_truscore.py git add to prevent rebase overwrite | Removed `"status.json"` from git add on line 1139 |
| 5 | agents/ddp/agent_tragents.py | Fix: remove status.json from agent_tragents.py git add to prevent rebase overwrite | Removed `"status.json"` from git add on line 947 |
| 6 | agents/ddp/daily_runner.py | Fix: add push_status() to daily_runner.py — single consolidated status.json push after all scrapers | Added REPO_PATH, push_status() function, calls in both single-score and all-scores paths |

---

## 12. Remaining Issues (Not Part of This Fix)

- **TRSbench timeout (>300s):** Times out on both dry-run and live run. Data stuck on Mar 8. This is a separate investigation — likely a Playwright/scraping issue, not a git issue.
- **TRSitekeeper "status.json not found" at 6:07 AM:** TRSitekeeper was looking for status.json at the wrong path after the restructure. This ties into Issue #8 (TRSitekeeper not autonomous). The status command was later moved to TRSitekeeper from TrainingRun Bot.

---

## 13. Verification Checklist

- [x] `git pull` on David's Mac — pulled all 6 commits (6 files changed, 29 insertions, 5 deletions)
- [x] Live run of `daily_runner.py` — 4 passed, 1 failed (TRSbench timeout)
- [x] Terminal output shows "status.json pushed to GitHub" at end of run
- [x] Mission Control shows 4 LIVE agents (TRUscore, TRScode, TRFcast, TRAgents)
- [x] Each scraper still pushes its own data file correctly (confirmed via Telegram "DDP done!" messages)
- [x] TRSbench absence is due to timeout, not our fix
- [ ] Next 4 AM cron run (Mar 10) — verify it works unattended with no manual intervention

---

*CEO-LEARNING-003 — March 9, 2026*
*Incident: status.json rebase overwrite causing Mission Control to show 2 of 5 DDP scores*
*Root cause: `-X theirs` git rebase strategy in per-scraper git_push() silently discarding accumulated status.json data*
*Fix: Centralized status.json push in daily_runner.py after all scrapers complete*
*Verified: Live test run at 8:53 AM — 4/4 successful scrapers now show in Mission Control*
