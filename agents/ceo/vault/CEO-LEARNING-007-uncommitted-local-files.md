# CEO-LEARNING-007: Uncommitted Local Files

**Date:** 2026-03-09
**Fix Number:** 9 of 10
**Category:** Repository Hygiene / Deployment Gap
**Status:** RESOLVED
**Commit:** a876e04

---

## What Broke

9 files existed on David's local Mac (`~/trainingrun-site/`) but were never committed or pushed to GitHub. Since GitHub Pages IS the live site, these files were invisible to production. Some were agent output files (audit logs, run logs, news pages), meaning agent work was being done but never reaching the live repo.

Additionally, David's local repo was **12 commits behind origin/main** — all the commits pushed via GitHub's web upload UI during Fix #8 and prior sessions were on GitHub but not pulled down locally. This meant the local working copy was out of sync with production.

---

## Root Cause

Two factors:

1. **Upload workflow mismatch**: Fixes #1-8 were pushed via GitHub's web upload UI (David dragging files to the browser). This bypasses `git` on the local machine entirely, so `~/trainingrun-site/` never received those commits. No one ran `git pull` after the web uploads.

2. **Agent output not in commit flow**: The DDP agents, Daily News agent, Content Scout, and TRSitekeeper all write output files locally. But there was no automated `git add + commit + push` step after agent runs. The agents do their work, write files, and stop — nobody pushes.

---

## What Was Found

### Modified (changed but uncommitted):
| File | Purpose |
|------|---------|
| `agent_activity.json` | Tracks agent run times and status |
| `agents/daily-news/staging/.last_processed_date` | News agent bookmark for last processed date |
| `agents/trsitekeeper/audit_history.json` | TRSitekeeper audit result history |
| `agents/trsitekeeper/vault/RUN-LOG.md` | TRSitekeeper execution log |

### Untracked (new, never added to git):
| File | Purpose |
|------|---------|
| `agents/daily-news/staging/day-010.html` | Generated news page for day 10 |
| `agents/daily-news/staging/day-011.html` | Generated news page for day 11 |
| `content_scout/scout-data.json` | Content Scout scraped data |
| `context-vault/agents/trainingrun/daily-news/content-scout/RUN-LOG.md` | Content Scout run log |
| `restructure.sh` | The V10 restructure shell script (historical reference) |

---

## The Fix

Three-step terminal command (single paste):

```bash
cd ~/trainingrun-site && git pull origin main && git add [all 9 files] && git commit -m "Add 9 uncommitted agent output files and restructure script" && git push origin main
```

Execution order:
1. `git pull origin main` — fast-forwarded 12 commits from GitHub into local
2. `git add` — staged all 9 files
3. `git commit` — committed as a876e04 (9 files changed, 13491 insertions, 22 deletions)
4. `git push origin main` — pushed to GitHub/production

---

## Diagnosis Method

1. Ran comprehensive git status command on David's Mac terminal:
   ```bash
   cd ~/trainingrun-site && git fetch origin && git status && echo "---UNTRACKED---" && git ls-files --others --exclude-standard && echo "---MODIFIED---" && git diff --name-only && echo "---UNPUSHED COMMITS---" && git log origin/main..HEAD --oneline
   ```
2. Analyzed output: 4 modified files, 5 untracked files, 0 unpushed commits, 12 commits behind origin
3. Identified each file's purpose and confirmed all should be committed
4. Single combined command for pull + add + commit + push

---

## Prevention

### Immediate:
- After ANY GitHub web upload session, run `git pull origin main` on the local Mac to stay in sync
- After agent runs, check `git status` periodically to catch uncommitted output

### Longer term (for agent ecosystem):
- Agents should include a `git add + commit + push` step after writing output files
- Or: a scheduled job (cron/launchd) that runs `git add -A && git commit -m "Auto-commit agent output" && git push` every hour during agent work windows
- TRSitekeeper could include a check: "are there uncommitted files in the repo?"

---

## Key Lesson

**The GitHub web upload workflow creates a sync gap.** When files are pushed via the browser upload UI, the local git repo doesn't know about them. This is fine for the live site (GitHub Pages deploys from origin/main), but it means the local working copy drifts. Always `git pull` after web upload sessions.

**Agent output without auto-commit is invisible work.** Agents ran successfully (TRSBench even timed out doing real work), but their output files sat locally uncommitted. The work happened but never reached production. Every agent that writes files needs a push mechanism.

---

## Reusable Playbook: Finding Uncommitted Local Files

1. SSH/terminal into the machine running agents
2. `cd` to repo directory
3. Run the comprehensive status command (fetch + status + ls-files + diff + log)
4. Categorize: modified vs untracked vs unpushed commits
5. For each file: identify purpose, decide commit/delete/ignore
6. Pull first (if behind origin), then add + commit + push
7. Verify with `git status` after push shows clean working tree
