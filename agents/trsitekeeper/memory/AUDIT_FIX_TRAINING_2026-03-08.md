# TRSitekeeper Training — Audit Check Fixes (March 8, 2026)

## Context
On March 8, 2026, the 24-check audit in `sitekeeper_audit.py` was scoring 18-20/24 — but 4 of the failures were caused by the checks themselves having wrong expectations, NOT by actual site problems. This document captures what was wrong, what was fixed, and the reasoning behind each change. TRSitekeeper should use this to understand its own audit system better and avoid false positives in the future.

## Key Principle
**A failing audit check is only useful if it detects a real problem.** If a check fails because it's looking for something that doesn't exist and shouldn't exist, that check is broken — not the site. Fix the check, not the site.

---

## Check 001: Site Health (`_check_site_health`)

### What was wrong
The check looked for three files in `web_agent/`:
- `ticker.json`
- `leaderboard.json`
- `ddp_status.json`

None of these files existed. They were never produced by any agent or scraper. They were phantom expectations — the check was written for a site concept that doesn't match trainingrun.ai.

### What it was changed to
Now checks for things that actually exist and matter:
- `web_agent/agent.py` and `web_agent/sitekeeper_audit.py` (core agent files)
- `web_agent/memory/` directory (agent memory system)
- All 5 DDP data files in repo root: `trscode-data.json`, `truscore-data.json`, `trf-data.json`, `tragent-data.json`, `trs-data.json`
- Validates that each DDP file contains valid JSON

### Why this is better
- Checks real infrastructure that TRSitekeeper depends on
- DDP file existence + JSON validity catches actual scraper failures
- check_002 already checks DDP freshness (staleness), so check_001 checking existence + validity is complementary, not redundant

### Did it break the site? No.
Site was verified before and after. trainingrun.ai loaded normally with all data intact.

---

## Check 006: Vault Integrity (`_check_vault_integrity`)

### What was wrong
The check looked for a `vault/` directory with 9 JSON files:
- `vault_config.json`, `vault_keys.json`, `vault_archive_1.json`, `vault_archive_2.json`, `vault_archive_3.json`, `vault_secrets.json`, `vault_audit_log.json`, `vault_backup.json`, `vault_metadata.json`

None of these files existed. The real vault uses markdown files in a completely different location.

### What it was changed to
Now checks the actual vault at `context-vault/trainingrun/agents/trsitekeeper/` for the real 9 files:
- `SOUL.md`, `CONFIG.md`, `PROCESS.md`, `CADENCE.md`, `RUN-LOG.md`, `LEARNING-LOG.md`, `STYLE-EVOLUTION.md`, `CAPABILITIES.md`, `TASK-LOG.md`

### Why this is better
- Points to the real vault that actually exists
- Checks for the 9 markdown files that contain TRSitekeeper's identity, process, and learning history
- If any of these files go missing, that's a real problem worth flagging

### Did it break the site? No.
Audit logic only — no HTML, CSS, or JS was changed.

---

## Check 014: Special Pages (`_check_special_pages`)

### What was wrong
The check looked for 4 HTML pages that don't exist on trainingrun.ai:
- `terms.html` / `tos.html` / `terms-of-service.html`
- `charter.html` / `code-of-conduct.html`
- `belt.html` / `ranks.html`
- `mythology.html` / `lore.html`

The "belt" and "mythology" pages were from a gaming/martial arts concept that was never part of Training Run. The "terms" and "charter" pages were never built.

### What it was changed to
The check now passes by default with a comment that trainingrun.ai does not use these pages. It can be repurposed later if new pages are added that should be monitored.

### Why this approach
Rather than checking for different pages, the decision was made to pass this check entirely because there are no "special pages" on trainingrun.ai that need existence monitoring. The core pages (index.html, scores.html, news.html) are already verified by other checks (check_008 URL crawl, check_009 internal links).

### Did it break the site? No.

---

## Check 022: Ticker/Leaderboard Consistency (`_check_ticker_leaderboard`)

### What was wrong
The check looked for `ticker.json` and `leaderboard.json` in `web_agent/`, then compared scores between them for discrepancies. Neither file exists. There is no ticker or leaderboard feature on trainingrun.ai — the site displays scores directly from the 5 DDP data files.

### What it was changed to
The check now passes by default with a comment that trainingrun.ai does not have separate ticker/leaderboard files. Score data lives in the 5 DDP `*-data.json` files checked elsewhere.

### Why this approach
There's nothing to cross-check. When/if a ticker or leaderboard feature is built, this check can be repurposed to validate it. Until then, it's a false positive that wastes diagnostic cycles.

### Did it break the site? No.

---

## Diagnostic Prompt Fix

### What was wrong
The diagnostic prompt (used when Claude API diagnoses audit failures) contained two incorrect lines:
1. `"ticker.json and leaderboard.json are NOT produced by scrapers - they may need separate generation"`
2. `"Special pages expected: terms.html, charter.html, belt.html, mythology.html"`

These fed wrong context to the Claude API, causing it to propose fixes for things that don't exist.

### What it was changed to
1. `"DDP data files: trscode-data.json, truscore-data.json, trf-data.json, tragent-data.json, trs-data.json (in repo root)"`
2. `"No special pages required (terms, charter, belt, mythology do not apply to trainingrun.ai)"`

The vault path reference was already correct in the prompt: `context-vault/trainingrun/agents/trsitekeeper/`

---

## Stub File Cleanup

### What was deleted
Three files were removed from the repo root:
- `ticker.json` — contained `[]` (empty array), 3 bytes
- `leaderboard.json` — contained `[]` (empty array), 3 bytes
- `ddp_status.json` — contained `{"trsbench": "unknown", "trscode": "unknown", ...}`, 126 bytes

### Why they were deleted
These were stub files created in a previous session to make check_001 pass temporarily. Now that check_001 has been rewritten to check for real files, these stubs serve no purpose and just clutter the repo. No agent reads them, no page references them.

---

## Summary of Commits

| # | Commit Message | What Changed |
|---|---------------|-------------|
| 877 | `Add: OPERATING_INSTRUCTIONS V2.0` | New operating instructions with Telegram pings + commit standards |
| 878 | `Fix check_001: replace phantom files with real agent infrastructure + DDP data checks` | Rewrote check_001 function |
| 879 | `Fix check_006 vault path + pass check_014/022 (not needed) + fix diagnostic prompt` | Fixed 3 checks + prompt in one commit |
| 880 | `Delete: remove ticker.json stub` | Removed stub file |
| 881 | `Delete: remove leaderboard.json stub` | Removed stub file |
| 882 | `Delete: remove ddp_status.json stub` | Removed stub file |

## Site Verification
- **Before changes**: trainingrun.ai loaded normally — leaderboard, DDP ticker bar, all scores displaying, data updated Mar 8 4:11 AM CST
- **After changes**: trainingrun.ai loaded identically — no visual or functional difference. All changes were to Python audit logic, not to HTML/CSS/JS

## Lessons for TRSitekeeper
1. **Always verify check expectations match reality.** If a check looks for files that don't exist, the check is wrong.
2. **Don't create stub files to satisfy broken checks.** Fix the check instead.
3. **The diagnostic prompt must reflect the actual repo structure.** Wrong context = wrong diagnosis = wasted fix attempts.
4. **Passing a check by default is valid** when the thing being checked doesn't apply to the site. Better to pass cleanly than fail on nonsense.
5. **Check the site before and after making changes.** Even if you're only changing Python logic, verify nothing unexpected happened.
6. **One logical change per commit with a descriptive message.** The commit history should tell the story.
