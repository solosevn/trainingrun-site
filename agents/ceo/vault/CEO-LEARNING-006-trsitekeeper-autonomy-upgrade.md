# CEO-LEARNING-006: TRSitekeeper Autonomy Upgrade
## Fix #8 — Agent Was a Reporter, Not an Employee

**Date:** March 9, 2026
**Severity:** Architectural — agent running but not doing its job
**Duration:** Multi-session (March 7-9, 2026)
**Commits:** `52c1836`, `3544da4`, `4f67cd6`, `4406b24` + 2 delete commits

---

## 1. THE INCIDENT

TRSitekeeper had a 24-check audit suite that ran at 6 AM daily. It would fire all 24 checks, count pass/fail, send a Telegram summary, and go back to sleep. That's all it did.

During the V10 repo restructure (March 8), the site broke in multiple ways — news.html was duplicated, DDP pipeline paths were wrong, status.json moved — and TRSitekeeper caught NONE of it. David found and fixed every problem manually across 3+ sessions.

The question: Why does a 24-check audit system not catch real problems?

---

## 2. ROOT CAUSES (Multiple)

### 2a. Half the code never made it to GitHub
The 1,335-line version of sitekeeper_audit.py with all 24 checks, dynamic remediation, and learning memory existed only on David's Mac. GitHub had a 407-line version with ~7 checks. Everything built in the March 7 session was running locally but never pushed. The agent on GitHub was brain-dead.

**Lesson for CEO Agent:** After every coding session, verify the code was actually pushed to GitHub. "Committed" and "pushed" are not the same thing in a local-first workflow. Run `git log origin/main..HEAD` to check for unpushed commits.

### 2b. Checks were looking for files that don't exist
Multiple checks were hardcoded to look for files that either never existed on TrainingRun or were artifacts from a different site concept:

| Check | Expected | Reality |
|-------|----------|---------|
| check_001 | ticker.json, leaderboard.json, ddp_status.json in web_agent/ | Real DDP outputs are trscode-data.json etc. in repo root |
| check_006 | 9 JSON vault files in vault/ (vault_config.json, vault_keys.json, etc.) | Real vault is Core 7 markdown files in context-vault/trainingrun/agents/trsitekeeper/ |
| check_014 | belt.html, mythology.html, terms.html, charter.html | "Belt" and "mythology" are meaningless for TrainingRun. These pages never existed. |
| check_022 | ticker.json + leaderboard.json in web_agent/ | Same phantom files as check_001 |
| check_023 | leaderboard.json + ddp_status.json in web_agent/ | Same phantom files |
| check_024 | leaderboard.json in web_agent/ | Same phantom files |

**Lesson for CEO Agent:** Before trusting any audit check, verify the check's expectations match reality. Don't create stub files to satisfy bad checks — fix the checks. The check must reflect the actual system, not the other way around.

### 2c. Previous Claude created stub files instead of fixing checks
In the March 7 session, when check_001 failed because ticker.json didn't exist, the previous Claude told David to "approve check_001" and then created empty stub files (ticker.json = `[]`, leaderboard.json = `[]`, ddp_status.json = stub with DDP keys) in the REPO ROOT instead of in web_agent/ where the check expected them. This meant:
- The stubs were in the wrong location (check still failed)
- Empty array stubs serve no purpose on the production site
- The real problem (the check's expectations were wrong) was never addressed
- David had to stop the agent and point out that "belt" and "mythology" are nonsense

**Lesson for CEO Agent:** When a check fails, ask "Is the check correct?" before asking "How do I make the check pass?" Creating data to satisfy a bad check is worse than leaving it broken.

### 2d. Agent architecture was "reporter, not employee"
The fundamental architectural problem: TRSitekeeper's loop was Fire audit → Report score → Sleep. It had no:
- **Vault context loading** — didn't read its own memory before running checks
- **Remediation loop** — found failures but did nothing about them
- **Work window** — ran once and stopped, no "let me investigate and fix" cycle
- **Cross-agent awareness** — didn't check if other agents (Scout, Daily News) were running
- **Active memory retrieval** — logged to tried_fixes.jsonl but never read it back

The dynamic remediation added in the March 7 session (commits `60b5a7a`, `1c251f0`, `180ebc2`) partially fixed this by replacing the static REMEDIATION_MAP with Claude API calls. But:
- The Claude API key was dead since March 1 (sk-ant-api03 expired, nobody noticed for 6 days)
- `claude_chat()` was called without `system_prompt`, breaking the call format
- The 1,335-line version with these fixes never made it to GitHub

### 2e. Dead API key for 6 days
The Anthropic API key (sk-ant-api03) expired on or around March 1. Every Claude API call from TRSitekeeper was silently returning 401 errors. The agent kept running because the hardcoded Python checks don't need Claude — only the diagnosis step does. David discovered this on March 7, generated trskey-v2, and updated ~/.zshrc.

**Lesson for CEO Agent:** Monitor API key health. If `_get_claude_analysis()` returns None or errors for 24+ hours, alert David via Telegram immediately. Include API health in the audit checklist.

---

## 3. WHAT WE FIXED

### Phase 1: Get the real code to GitHub (commit `52c1836`)
Uploaded the 1,335-line version from David's Mac to `agents/trsitekeeper/sitekeeper_audit.py`. This was the foundation — without this, nothing else matters.

### Phase 2: Fix all broken checks (commit `3544da4`)

| Check | Before | After |
|-------|--------|-------|
| check_001 | ticker.json, leaderboard.json, ddp_status.json in web_agent/ | 5 real DDP files (trscode-data.json, etc.) in repo root |
| check_002 | web_agent/ddp_status.json | status.json in repo root |
| check_003 | ticker.json, leaderboard.json in web_agent/ | 5 real DDP files in repo root |
| check_006 | 9 imaginary JSON files in vault/ | Core 7 markdown files in context-vault/trainingrun/agents/trsitekeeper/ |
| check_014 | belt, mythology, terms, charter pages | **DELETED ENTIRELY** |
| check_022 | ticker.json vs leaderboard.json comparison | Validates all 5 real DDP data files exist and have content |
| check_023 | leaderboard.json + ddp_status.json | Scans real DDP data files for suspicious perfect scores |
| check_024 | leaderboard.json rankings | Checks real DDP file modification times for staleness (>48h) |

Total: 23 checks now (was 24). All point to files that actually exist.

### Phase 3: Delete bad stub files
Deleted ticker.json, leaderboard.json, ddp_status.json from repo root. All were empty stubs (`[]`) created by mistake in the March 7 session. No code references them anymore.

### Phase 4: Add vault context loading (commit `4406b24`)
New `_load_vault_context()` method runs BEFORE every audit:
- Reads Core 7 vault files (SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md) — first 2K chars each
- Loads site_knowledge.json, fix_patterns.json, david_model.json
- Loads last 20 entries from tried_fixes.jsonl
- Loads last 10 entries from error_log.jsonl

The agent now wakes up knowing who it is, what the site looks like, and what it tried before.

### Phase 5: Add work window with remediation loop (commit `4406b24`)
After the initial audit, if failures exist AND we're still in the 6-8 AM window:
1. Claude analyzes failures with full memory context → returns structured JSON (diagnosis, root cause, fix type, confidence, files involved)
2. High-confidence (80%+) auto-fixable items (rerun_scraper, git_commit) execute automatically
3. Every attempt records to tried_fixes.jsonl
4. Wait 30s, re-run audit to verify
5. Max 3 fix cycles per window
6. Low-confidence items escalated to David via Telegram with "approve check_name" instructions
7. Final status report when window closes

### Phase 6: Upgrade Claude analysis (commit `4406b24`)
`_get_claude_analysis()` now:
- Passes vault memory (past fix attempts, recent errors, site knowledge) to Claude
- Forces structured JSON response with guardrails ("do NOT propose creating stub files")
- Parses response and stores as `_pending_fixes` for the approve flow

---

## 4. INVESTIGATION METHODOLOGY

### How we diagnosed the problem:
1. Read all context from prior sessions — 4 uploaded files (sitekeeper_audit.py 1,335 lines, Grok Audit #2, Grok on Autonomy, SESSION_RECAP March 7) plus 10+ screenshots
2. Compared GitHub version (407 lines) vs Mac version (1,335 lines) — identified the "never pushed" gap
3. Traced every check's file expectations against actual repo contents
4. Identified 8 checks with wrong expectations
5. Reviewed the diagnostic prompt for bad information
6. Mapped the agent's boot-to-sleep lifecycle: no vault loading, no remediation, no work window

### Key questions that drove the diagnosis:
- "Why didn't 24 checks catch the real V10 breakages?"
- "What files do these checks actually look for?"
- "Do those files exist?"
- "What does the agent do AFTER finding failures?"
- "Does the agent read its own memory before acting?"

---

## 5. FAILED APPROACHES (From Prior Sessions)

1. **Creating stub files to pass checks** — Made check_001 "pass" but with empty useless data. Wrong approach entirely. Fix the check, not the data.
2. **Static REMEDIATION_MAP** — Hardcoded one-fix-per-check dictionary. When a fix failed, it repeated the same fix forever. Replaced with dynamic Claude diagnosis.
3. **OpenClaw/LangGraph/CrewAI** — Grok explicitly recommended against these frameworks. The native stack (agent.py + Claude API + filesystem memory + skills/) is lighter, cheaper, and already runs on David's Mac.

---

## 6. PREVENTION

### For the CEO Agent to enforce:
1. **Post-session push verification** — After any coding session, verify all changes are on GitHub: `git log origin/main..HEAD` should be empty
2. **Check validation** — When adding or reviewing audit checks, verify the expected files/pages actually exist. Run `ls` on the expected paths.
3. **API key monitoring** — If Claude API calls fail for 24+ hours, alert David. Include a simple health ping in the audit cycle.
4. **No stub file creation** — Never create empty data files to satisfy checks. If a check expects something that doesn't exist, the check is wrong.
5. **Memory retrieval before action** — Before proposing any fix, query tried_fixes.jsonl: "Have I tried this before? What happened?" This prevents infinite loops.

---

## 7. REUSABLE PLAYBOOK: Agent Autonomy Audit

When evaluating whether an agent is truly autonomous:

1. **Does it load context at boot?** Check if it reads its vault files before acting. An agent without context is just a script.
2. **Does it act on findings?** Reporting problems without fixing them is monitoring, not autonomy. Look for a remediation loop.
3. **Does it learn from failures?** Check for persistent memory (tried_fixes, error_log) that influences future decisions. Logging without retrieval is useless.
4. **Does it have a work window?** One-shot audit-and-sleep is a cron job. Real autonomy means "investigate until done or escalate."
5. **Are its checks grounded in reality?** Every check should reference files/pages that actually exist. Bad expectations create false failures and mask real problems.
6. **Is the live version the latest version?** Compare local code to what's on GitHub. Unpushed code doesn't count.
7. **Are API dependencies healthy?** Dead API keys, missing env vars, and broken imports silently disable features while the agent appears to run.

---

*CEO-LEARNING-006 — March 9, 2026*
*Fix #8 of V10 Restructure Fix List*
*Related: CEO-LEARNING-004 (news.html), CEO-LEARNING-005 (.env security audit)*
