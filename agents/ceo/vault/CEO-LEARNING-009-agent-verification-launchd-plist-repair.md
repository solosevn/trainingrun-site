# CEO-LEARNING-009: Agent Verification & launchd Plist Repair

**Date:** 2026-03-09
**Category:** Agent Operations / Infrastructure
**Status:** RESOLVED

---

## What Broke

After the V10 repo restructure (March 8), the macOS launchd plist files that auto-start Content Scout and TRSitekeeper were still pointing to pre-V10 paths. This meant:

- `com.trainingrun.scout.plist` referenced `content_scout/scout.py` — a path that no longer exists
- `com.trainingrun.sitekeeper.plist` referenced `web_agent/agent.py` — a path that no longer exists
- The sitekeeper plist also contained a dead API key (`sk-ant-api03-ACU700...`) that expired March 1

The agents happened to still be running from before the restructure, but the next time the Mac rebooted, **neither Content Scout nor TRSitekeeper would have started**. They would have silently failed with "No such file or directory" errors and David would have had no idea until he noticed stale content on the site.

The DDP pipeline (cron) and Daily News agent (launchd) were already on correct paths and confirmed operational.

---

## Root Cause

The V10 restructure moved agent code to new directories but only updated the code files and GitHub structure. The **local macOS service configurations** (launchd plists in `~/Library/LaunchAgents/`) were never touched. These are local-only files that don't live in the repo — they sit on David's Mac and tell macOS what to run at boot.

Nobody checked them because:
1. The agents were still running from their pre-reboot state
2. Running agents mask broken startup configs — everything looks fine until the next reboot
3. There was no checklist item for "update service configs" in the restructure plan

The dead API key was a separate issue — it expired March 1 and was never rotated in the plist, even though the new key (trskey-v2) was being used elsewhere.

---

## The Fix

### 1. Agent Status Audit
Before fixing anything, verified the actual state of all four agents:

| Agent | Status | Auto-Start Method | Path Status |
|-------|--------|-------------------|-------------|
| TRSitekeeper | Running (manual terminal) | launchd plist | **BROKEN** — old path |
| Content Scout | Running (from pre-V10) | launchd plist | **BROKEN** — old path |
| Daily News | Running | launchd plist | OK |
| DDP Pipeline | Runs via cron `0 4 * * *` | crontab | OK |

### 2. Fixed Content Scout Plist (`com.trainingrun.scout.plist`)
- `ProgramArguments`: `content_scout/scout.py` → `agents/content-scout/scout.py`
- `WorkingDirectory`: `content_scout` → `agents/content-scout`
- Log paths updated accordingly

### 3. Fixed TRSitekeeper Plist (`com.trainingrun.sitekeeper.plist`)
- `ProgramArguments`: `web_agent/agent.py` → `agents/trsitekeeper/agent.py`
- `WorkingDirectory`: updated to `agents/trsitekeeper`
- `ANTHROPIC_API_KEY`: replaced dead `sk-ant-api03-ACU700...` with live trskey-v2
- Log paths updated to `agents/trsitekeeper/sitekeeper.log`

### 4. Installed and Loaded
Both plists were copied to `~/Library/LaunchAgents/` and loaded with `launchctl load`. Verified with `launchctl list | grep trainingrun` — all three launchd services registered.

---

## Prevention

### Restructure Checklist (add to future restructures):
1. Move code files to new paths ✓ (was done)
2. Update imports and internal references ✓ (was done)
3. **Update launchd plists in `~/Library/LaunchAgents/`** ← was missed
4. **Update crontab entries** ← was checked, was fine
5. **Verify API keys in all service configs are live** ← was missed
6. Reboot-test: `launchctl unload` then `launchctl load` each service and confirm it starts

### Agent Health Check Protocol:
Don't assume agents are running just because they were running yesterday. Verify:
- `ps aux | grep [agent_name]` — is it actually running right now?
- `launchctl list | grep trainingrun` — is it registered to auto-start?
- Read the actual plist file — are the paths and env vars correct?
- Check the log file — any errors?

### API Key Rotation Rule:
When rotating API keys, grep every plist and env file for the old key:
```
grep -r "OLD_KEY_PREFIX" ~/Library/LaunchAgents/
grep -r "OLD_KEY_PREFIX" ~/trainingrun-site/
```

---

## Key Lesson

**Running agents mask broken configs.** An agent that was started before a restructure will keep running on the old paths from memory. Everything looks fine. Then the Mac reboots, launchd tries to start the agent using the plist, the plist points to a path that no longer exists, and the agent silently dies. No alert, no error visible to the user — just a site that stops getting updated.

**Service configs are not code — they live outside the repo.** launchd plists, crontab entries, and environment files don't get restructured when you restructure a repo. They have to be found and updated manually. Any restructure checklist must include "update all local service configs" as a mandatory step.

**Verify, don't assume.** When asked "are all agents running?", the answer is `ps aux` and reading the plist files — not "they should be." The 30 seconds it takes to check saves hours of debugging a silently dead agent.
