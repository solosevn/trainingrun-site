# CEO-LEARNING-002: DDP Pipeline Broke After V10 Restructure

**Incident Date:** March 8–9, 2026
**Severity:** Critical — all 5 DDP scrapers stopped producing live scores
**Time to Resolve:** ~3 hours debugging + fixing (across two Cowork sessions)
**Triggered By:** V10 repository restructure (`restructure.sh`)

---

## 1. INCIDENT TIMELINE

**March 8, 2026 — Morning:**
- David runs `restructure.sh` to reorganize the trainingrun-site repo into a V10 agent hierarchy
- The script moves all agent code from the repo root into `agents/` subdirectories (e.g., `daily_runner.py` → `agents/ddp/daily_runner.py`)
- The script also moves data JSON files from the repo root into a new `data/` directory (e.g., `trs-data.json` → `data/trs-data.json`)
- The restructure completes and is committed to GitHub

**March 8, 2026 — Later that day:**
- Someone notices the live site is broken — leaderboard pages can't find their data files
- A bandaid "fix" is applied: stale copies of all data JSON files are copied back to the repo root, along with `ticker.json`, `leaderboard.json`, and `ddp_status.json`
- The commit message is "Restore leaderboard data files deleted during restructure"
- The site appears to work again because the HTML pages can find the root-level JSON files
- **Nobody checks whether the DDP scrapers can still run.** The bandaid restored old data but didn't fix the pipeline that generates new data.

**March 9, 2026 — 4:00 AM CST:**
- Crontab fires the DDP job: `cd ~/trainingrun-site && python3 daily_runner.py`
- `daily_runner.py` no longer exists at the repo root — it was moved to `agents/ddp/daily_runner.py`
- Cron silently fails. No Telegram notification. No error in any visible log. The scrapers simply don't run.
- The data files on the site remain stale from March 8.

**March 9, 2026 — Morning (Cowork session):**
- David and Claude begin investigating. The investigation uncovers THREE compounding failures, not just one.
- All fixes are applied, tested via dry-run (4/5 pass, TRSbench times out — pre-existing issue), then tested live.
- All 5 scrapers run successfully in live mode. Fresh scores appear on the site.

---

## 2. THE THREE FAILURES

The restructure broke the DDP pipeline in three independent ways. Each one alone would have been enough to break it. All three had to be fixed for the pipeline to work.

### Failure 1: Crontab pointed to a file that no longer exists

**Before restructure:**
```
0 4 * * * cd ~/trainingrun-site && python3 daily_runner.py >> ~/trainingrun-site/ddp.log 2>&1
```

**After restructure:**
`daily_runner.py` was moved to `agents/ddp/daily_runner.py`. The crontab still pointed to the repo root. Cron ran, couldn't find the file, silently failed.

**Fix:**
```
0 4 * * * cd ~/trainingrun-site/agents/ddp && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daily_runner.py >> ~/trainingrun-site/ddp.log 2>&1
```

David applied this via a one-liner sed command (crontab is local to his machine — can't be edited through GitHub).

### Failure 2: daily_runner.py used relative paths that broke when working directory changed

**The problem:** `daily_runner.py` used `os.path.exists("agent_trscode.py")` to check for scraper scripts. This only works if the working directory is the same directory the scripts are in. Before the restructure, everything was at the repo root and cron `cd`'d there. After the restructure, the scripts moved to `agents/ddp/` but the code still assumed they were findable via relative path from cwd.

**The fix:** Added `SCRIPT_DIR` pattern at the top of `daily_runner.py`:
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

Then all script lookups use absolute paths:
```python
script_path = os.path.join(SCRIPT_DIR, script)
if not os.path.exists(script_path):
    log(f"  SKIP {'{'}name{'}'}: {'{'}script_path{'}'} not found.")
    return False
cmd = [sys.executable, script_path]
```

And `subprocess.run()` uses `cwd=SCRIPT_DIR` so scrapers run from the correct directory.

Also added `update_status()` function that writes DDP run results to `status.json` at repo root (two levels up: `os.path.join(SCRIPT_DIR, "..", "..", "status.json")`), enabling Mission Control to show DDP pipeline status.

**Commit:** `da1d8f0` — "Fix daily_runner.py: use SCRIPT_DIR for absolute script paths"

### Failure 3: All 5 scrapers wrote data to wrong path AND used wrong git add path

**The problem:** The restructure script changed each scraper's `DATA_FILE` path. The intention was to point to the new `data/` directory. But the result was a doubled path:

```python
# What the restructure produced (WRONG):
REPO_PATH = Path(os.environ.get("REPO_PATH", str(Path.home() / "trainingrun-site")))
DATA_FILE = REPO_PATH / "data" / "data/trf-data.json"
# This resolves to: ~/trainingrun-site/data/data/trf-data.json — doesn't exist
```

The original code before restructure was:
```python
DATA_FILE = REPO_PATH / "trf-data.json"
# Resolves to: ~/trainingrun-site/trf-data.json — correct, where GitHub Pages serves from
```

The same doubled-path bug existed in EVERY scraper's `git add` command:
```python
# What the restructure produced (WRONG):
subprocess.run(["git", "add", "data/trf-data.json", "status.json"], cwd=REPO_PATH, ...)
# Tries to add data/trf-data.json which doesn't exist at repo root
```

Should be:
```python
subprocess.run(["git", "add", "trf-data.json", "status.json"], cwd=REPO_PATH, ...)
```

**Why this matters:** The HTML leaderboard pages fetch data via relative URLs from the repo root (e.g., `fetch('trf-data.json')`). GitHub Pages serves files from the repo root. If scrapers write to `data/trf-data.json`, the HTML pages can't find it. The data MUST live at the repo root.

**All 5 scrapers had the identical bug on two lines each:**

| Scraper | DATA_FILE line | git add line | Data file |
|---------|---------------|--------------|-----------|
| agent_trfcast.py | Line 75 | Line 636 | trf-data.json |
| agent_trscode.py | Line 71 | Line 685 | trscode-data.json |
| agent_truscore.py | Line 145 | Line 1139 | truscore-data.json |
| agent_trs.py | Line 72 | Line 1171 | trs-data.json |
| agent_tragents.py | Line 78 | Line 947 | tragent-data.json |

**Fix for each:** Change `REPO_PATH / "data" / "data/X.json"` → `REPO_PATH / "X.json"` and `"data/X.json"` → `"X.json"` in the git add command.

**Commits:** `4310ba5` (agent_trfcast.py) + 4 more commits for the other scrapers.

---

## 3. THE BANDAID FIX AND WHY IT MADE THINGS WORSE

**What the bandaid did:** Copied stale data JSON files back to the repo root, plus added `ticker.json`, `leaderboard.json`, and `ddp_status.json`.

**Why it was harmful:**
1. **It made the CEO think the system was working.** The site displayed data, so it looked OK. But the data was from March 8 and would never update because the scrapers were still broken.
2. **It delayed discovery of the real problem.** If the site had stayed visibly broken, the scraper failures would have been investigated immediately.
3. **It created stale data that silently degrades trust in the platform.** Users see leaderboard data but don't know it's frozen. The site looks "alive" but is actually serving day-old scores.
4. **It created confusion about where data lives.** Now there were JSON files at root (stale copies) AND in `data/` (where the restructure put them). Two copies, neither being updated.

**Rule: If a fix doesn't involve fixing the CODE that generates the output, it's a bandaid.** Copying old output files back is never a fix — it's life support.

---

## 4. THE WRONG ASSUMPTIONS

### Wrong Assumption 1: "The restructure only moved files"
**Reality:** The restructure also modified code inside the files. The `restructure.sh` script didn't just `mv` files — it ran sed-style replacements on paths inside the Python files. Those replacements introduced the doubled `data/data/` path bug in all 5 scrapers. Moving files is safe; modifying code inside files during a move is where bugs get introduced.

### Wrong Assumption 2: "Restoring the data files fixes the site"
**Reality:** Restoring stale data files makes the site LOOK fixed while the underlying pipeline remains broken. The data will never update. This is worse than a visibly broken site because it hides the problem.

### Wrong Assumption 3: "The cron job will just work from the new location"
**Reality:** Nobody updated the crontab after the restructure. The cron job still pointed to `cd ~/trainingrun-site && python3 daily_runner.py`. Since `daily_runner.py` no longer existed at the repo root, cron silently failed every morning at 4 AM. There was no launchd plist for DDPs — they ran via crontab, not launchd like the other agents.

### Wrong Assumption 4: "If the scrapers had a problem, we'd see an error"
**Reality:** The scrapers never ran at all. Cron couldn't find the script, so there was nothing to produce an error. `daily_runner.py` has logging and Telegram notifications, but those only fire if the script actually executes. A missing script produces zero output — no log, no notification, no error. Silent failure is the most dangerous failure mode.

---

## 5. DEBUGGING METHODOLOGY

### Step 1: Check what's actually running
```bash
launchctl list | grep trainingrun
```
Result: sitekeeper (status -2, crashed), daily-news (running), scout (running). **No DDP service at all.** This immediately told us DDPs don't run via launchd.

### Step 2: Check the crontab
```bash
crontab -l
```
Result: Found the old cron entry pointing to `cd ~/trainingrun-site && python3 daily_runner.py`. The file doesn't exist there anymore. Mystery of "why aren't DDPs running" solved in one command.

### Step 3: Read the actual code
Opened `agents/ddp/daily_runner.py` on GitHub to see how it finds and runs scraper scripts. Found `os.path.exists("agent_trscode.py")` — relative path, depends on working directory being the script's directory.

### Step 4: Trace the data flow end-to-end
Question: Where do scrapers write their output JSON?
- Opened `agent_trfcast.py`, found `DATA_FILE = REPO_PATH / "data" / "data/trf-data.json"` — doubled path
- Found `subprocess.run(["git", "add", "data/trf-data.json", ...])` — git add also wrong
- Checked all 5 scrapers — same pattern in every one

### Step 5: Trace what the HTML pages read
The HTML leaderboard pages use `fetch('trf-data.json')` — relative URL from repo root. GitHub Pages serves from repo root. So data MUST be at root, not in `data/`.

### Step 6: Understand the full picture before touching anything
Three independent failures identified:
1. Crontab → wrong path (script not found)
2. daily_runner.py → relative paths (scripts not found even if cron worked)
3. All scrapers → doubled DATA_FILE path + wrong git add path (data written to wrong location)

Plus one cleanup: stale `data/` directory with 6 old files serving no purpose.

### Step 7: Fix all three, then verify with dry-run before going live
- Fixed daily_runner.py with SCRIPT_DIR pattern (committed to GitHub)
- Fixed all 5 scrapers' DATA_FILE and git add paths (committed to GitHub)
- David updated crontab (local machine — can't be done via GitHub)
- David deleted stale `data/` directory files (6 files deleted via GitHub UI)
- David ran `git pull --rebase` to get all commits locally
- Dry-run: 4/5 passed (TRSbench timed out at 300s — pre-existing, unrelated)
- Live run: all 5 scrapers executed, scraped data, sent Telegram notifications, completed in ~17 minutes

---

## 6. CRITICAL LESSONS FOR THE CEO AGENT

### Lesson 1: Restructures Require End-to-End Pipeline Verification
Moving files is the easy part. After ANY restructure:
1. Check every cron job and launchd plist for path references
2. Check every script for relative path dependencies
3. Check every script for hardcoded paths to data files
4. Run every pipeline in dry-run mode
5. Verify the live site serves fresh data

The V10 restructure did NONE of this verification. The restructure was committed and assumed to work.

### Lesson 2: The SCRIPT_DIR Pattern is Non-Negotiable
Any Python script that can be called from different working directories MUST resolve paths relative to its own location:
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(SCRIPT_DIR, "subscript.py")
```
Never use `os.path.exists("subscript.py")` — this resolves against cwd, which varies.

### Lesson 3: Bandaid Fixes Are Lies
Copying stale data files back to make the site "look right" without fixing the pipeline that generates them:
- Makes the CEO think the system is working
- Delays discovery of the real problem
- Creates stale data that silently degrades trust in the platform
- **Rule: If a fix doesn't involve fixing the CODE that generates the output, it's a bandaid.**

### Lesson 4: GitHub Pages Serves from Repo Root
Data JSON files (`trs-data.json`, `trf-data.json`, etc.) are fetched by HTML pages using relative URLs like `fetch('trs-data.json')`. These resolve against the repo root because GitHub Pages serves from root. Moving data files to a subdirectory (`data/`) breaks every page that reads them. The data files MUST stay at root.

### Lesson 5: Silent Failures Are the Most Dangerous
- Cron failing to find a script produces NO output (unless you check `ddp.log`)
- `daily_runner.py` skipping a script only logs "SKIP" — doesn't alert anyone
- **Every failure should produce a Telegram notification or status.json update.**
- The new `daily_runner.py` includes `update_status()` for this reason.

### Lesson 6: Verify After Restructure, Not Just After Fix
The V10 restructure should have been followed by:
1. Running `daily_runner.py --dry-run` to verify DDPs still work
2. Checking `crontab -l` to verify cron paths match new locations
3. Checking each scraper's DATA_FILE path
4. Verifying the live site shows current data

None of this was done. The restructure was committed and assumed to work.

---

## 7. AGENT ECOSYSTEM CONTEXT

### How the DDP Pipeline Works
1. Crontab fires at 4:00 AM CST daily
2. `daily_runner.py` orchestrates all 5 scraper agents in sequence
3. Each scraper: scrapes real benchmark data from external sources, calculates scores, writes to JSON at repo root, git add + git commit + git push
4. GitHub Pages serves the updated JSON files
5. HTML leaderboard pages fetch and display the data
6. `status.json` is updated with run results for Mission Control

### The 5 DDP Agents

| Agent | Script | Output File |
|-------|--------|-------------|
| TRScode | agent_trscode.py | trscode-data.json |
| TRFcast | agent_trfcast.py | trf-data.json |
| TRSbench | agent_trs.py | trs-data.json |
| TRUscore | agent_truscore.py | truscore-data.json |
| TRAgents | agent_tragents.py | tragent-data.json |

### File Relationships (Post-Fix)

**crontab (4AM daily):**
```
cd ~/trainingrun-site/agents/ddp
python3 daily_runner.py
```

**daily_runner.py:**
- `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` → resolves to agents/ddp/
- Finds scripts via `os.path.join(SCRIPT_DIR, script)`
- Runs each with `cwd=SCRIPT_DIR`
- Updates status.json at repo root via relative path `../../status.json`

**Each scraper (e.g., agent_trfcast.py):**
- `DATA_FILE = REPO_PATH / "trf-data.json"` → repo root, where GitHub Pages serves it
- `git add "trf-data.json", "status.json"` → root-relative paths
- Sends Telegram notification on completion

---

## 8. RESOLUTION VERIFICATION CHECKLIST

- [x] Root cause identified (three compounding path failures from restructure)
- [x] Crontab updated to point to `agents/ddp`
- [x] `daily_runner.py` fixed with SCRIPT_DIR pattern
- [x] All 5 scrapers' DATA_FILE paths reverted to repo root
- [x] All 5 scrapers' git add paths reverted to repo root
- [x] Stale `data/` directory deleted from repo (6 files)
- [x] Dry-run verified: 4/5 passed (TRSbench timeout is pre-existing, 300s limit)
- [x] Telegram notifications received for all successful scrapers
- [x] Live run executed to update site with fresh scores
- [ ] TRSbench timeout investigated separately (not related to restructure)
- [x] CEO Learning Document created (this document)

---

## 9. WHAT THE CEO AGENT WOULD HAVE DONE DIFFERENTLY

If a CEO agent had been overseeing this system:

1. **Pre-restructure dependency audit:** Before running `restructure.sh`, the CEO would have mapped every path reference in every script, every cron job, every plist, and every HTML fetch URL. The restructure script would have been tested in a branch first.

2. **Post-restructure verification:** Immediately after restructure, run `daily_runner.py --dry-run` to verify the pipeline works. Don't wait until the next morning's cron job to find out.

3. **Crontab awareness:** The CEO would have flagged that crontab is NOT managed by git and requires manual updating after any path change. A checklist item: "Update crontab paths after restructure."

4. **Reject bandaid fixes:** When "Restore leaderboard data files" was proposed, the CEO would have asked: "Does this fix the scrapers, or just restore old data?" Restoring stale data without fixing the pipeline is not a fix.

5. **TRSitekeeper should have caught this:** The sitekeeper agent should verify that DDP data files have recent timestamps. If `trs-data.json` hasn't been updated in 24+ hours, that's an alert-worthy condition. This check doesn't exist yet.

6. **Status.json integration:** The new `daily_runner.py` writes DDP results to `status.json` so Mission Control can display pipeline health. This should have existed from day one.

7. **Silent failure detection:** The CEO agent would monitor for ABSENCE of expected events. If 4 AM passes and no Telegram DDP notifications arrive by 4:30 AM, something is wrong. Monitoring for missing events is harder than monitoring for errors, but it's the only way to catch "script never ran" failures.

---

## 10. COMMITS MADE FOR THIS FIX

| Commit | Description |
|--------|-------------|
| `da1d8f0` | Fix daily_runner.py: use SCRIPT_DIR for absolute script paths |
| `4310ba5` | Fix agent_trfcast.py: DATA_FILE and git add paths back to repo root |
| (committed) | Fix agent_trscode.py: DATA_FILE and git add paths back to repo root |
| (committed) | Fix agent_truscore.py: DATA_FILE and git add paths back to repo root |
| (committed) | Fix agent_trs.py: DATA_FILE and git add paths back to repo root |
| (committed) | Fix agent_tragents.py: DATA_FILE and git add paths back to repo root |
| (committed) | Remove stale data/status.json |
| (committed) | Delete data/tragent-data.json |
| (committed) | Delete data/trf-data.json |
| (committed) | Delete data/trs-data.json |
| (committed) | Delete data/trscode-data.json |
| (committed) | Delete data/truscore-data.json |

---

*Document created: March 9, 2026*
*Incident resolved: March 9, 2026*
*Author: Claude (via Cowork session with David Solomon)*
*Classification: Infrastructure / Pipeline Recovery / Restructure Post-Mortem*
