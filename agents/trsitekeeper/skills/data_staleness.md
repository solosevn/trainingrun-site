# Skill: Data Staleness Diagnosis

## When to activate
Any time data appears old, scores aren't updating, status shows stale dates, or David asks "why hasn't the data updated?"

## Reasoning pattern
1. **CHECK STATUS.JSON FIRST:** Read `status.json` â each DDP writes a timestamp and status after running. If the timestamp is old, the DDP didn't run.
2. **CHECK THE DATA FILE:** Read the relevant `*-data.json` file. Look at the `dates[]` array â what's the latest date? If it's yesterday or older, data is stale.
3. **CHECK GIT LOG:** Did the data file get pushed? Run `git log --oneline -5` to see recent commits. If the DDP ran but didn't push, the data exists locally but isn't live.
4. **CHECK CRON:** Was the Mac awake at 4AM? Cron schedule is `0 4 * * *`. If the Mac was sleeping, cron didn't fire. Check `ddp.log` for the last run timestamp.
5. **CHECK DDP LOG:** Read `ddp.log` tail for errors. Common: Playwright timeout (website was slow), API rate limit, network error.
6. **TRACE THE PIPELINE:** Data flows: DDP script â JSON file â git push â GitHub Pages deploy (~60s). Break at any point means stale data on the live site.

## Common fixes
- DDP didn't run: Check `crontab -l`, verify schedule. Check if daily_runner.py exists and is executable.
- Data exists but not pushed: Run `git add *.json && git commit -m "fix: manual data push" && git push` manually.
- DDP errored: Check the specific DDP's log output. Usually Playwright timeout â re-run the specific DDP.
- Mac was sleeping: Nothing to fix retroactively. Consider adding a wake schedule (`pmset`) before 4AM.

## Known data bugs
- `trf-data.json`: rank field is always 999 (sentinel â DDP never computes rank). Always use live score calculation.
- `tragent-data.json`: 133 models, many with null latest scores. Stored rank is stale â compute live.

## Key files
- `daily_runner.py` â master cron script, runs all 5 DDPs sequentially
- `agent_trs.py`, `agent_trscode.py`, `agent_truscore.py`, `agent_trfcast.py`, `agent_tragents.py` â individual DDPs
- `status.json` â DDP run status, read by mission-control.html
- Python path for cron: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`

## Source
Seeded from brain.md CRON AUTOMATION + COMMON FIX PATTERNS. Version 1.0.
