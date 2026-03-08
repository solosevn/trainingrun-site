# LEARNING-LOG â TRS Site Manager (TRSitekeeper)

> **Format:** Raw memory â site issues, fix patterns, audit discoveries, operational lessons
> **Updated:** After notable events, recurring issues, or methodology changes
> **Started:** March 6, 2026

---

## Entry Format

```
### YYYY-MM-DD â [Topic]

**What happened:**
**Impact:**
**Action taken:**
**Lesson:**
```

---

## Entries

### 2026-03-08 — Audit Check Fixes (001, 006, 014, 022)

**What happened:** 4 of 24 audit checks were failing — but the failures were caused by wrong expectations in the checks, not real site problems. check_001 looked for phantom files (ticker.json, leaderboard.json, ddp_status.json) that never existed. check_006 pointed to a vault/ directory with 9 JSON files that don't exist — real vault is at context-vault/trainingrun/agents/trsitekeeper/ with 9 markdown files. check_014 checked for pages (terms.html, charter.html, belt.html, mythology.html) that trainingrun.ai doesn't have. check_022 cross-checked ticker/leaderboard files that don't exist.

**Impact:** False positives wasted diagnostic cycles. Claude API was given wrong context in the diagnostic prompt, causing bad fix proposals. 3 stub files had been created as band-aids instead of fixing the root cause.

**Action taken:** Rewrote check_001 to verify real infrastructure (agent.py, sitekeeper_audit.py, memory/ dir, 5 DDP data files with JSON validation). Fixed check_006 vault path to real location with real 9 .md files. Passed check_014 and check_022 by default since features don't exist. Fixed diagnostic prompt to reference correct files. Deleted 3 stub files. Site verified before and after — no impact.

**Lesson:** A failing check is only useful if it detects a real problem. If a check fails because it looks for something that doesn't exist and shouldn't exist, the check is broken — fix the check, not the site. Never create stub files to satisfy broken checks. The diagnostic prompt must match the actual repo structure or Claude API will waste cycles on wrong fixes.

---

### 2026-03-06 â Context Vault Established

**What happened:** TRS Site Manager vault created. Agent has been operational since Feb 2026 with brain.md v2.0 as its knowledge base. Vault now formalizes the autonomous audit framework and learning system.

**Impact:** No operational change yet. Vault provides structured memory that brain.md doesn't have â run logs, learning patterns, style rules.

**Action taken:** 9 vault files created. Autonomous audit checklist formalized. Daily schedule defined.

**Lesson:** The agent was running for weeks with only brain.md â a flat file with no append-only logs or learning structure. Vault files add the memory layer needed for true autonomy.

---

### 2026-02-24 â Model Upgrade: Ollama â Claude Sonnet 4.6

**What happened:** TRSitekeeper upgraded from local Ollama/llama model to Claude Sonnet 4.6 via Anthropic API. This was a fundamental capability upgrade.

**Impact:** Dramatically improved code understanding, HTML/CSS reasoning, and multi-step problem solving. Agent went from "basic text edits" to "autonomous site management."

**Action taken:** agent.py rewritten to use Claude API. brain.md updated to v2.0.

**Lesson:** Model quality is the ceiling for agent capability. The upgrade from Ollama to Sonnet was the single biggest improvement in agent effectiveness.

---

### 2026-02-26 â Brain v2.0 Written

**What happened:** Comprehensive brain.md v2.0 created with full file inventory (49 files), index.html deep architecture, DDP data format, git workflow, backup workflow, design rules, and common fix patterns.

**Impact:** Agent gained deep knowledge of the entire codebase. Could now make targeted fixes without needing to re-learn the file structure each time.

**Action taken:** brain.md expanded from basic identity doc to 12,000+ character operational manual.

**Lesson:** For a site management agent, the brain file IS the capability. The more detailed the file inventory and architecture documentation, the faster and more accurate the fixes.

---

## Known Issues (as of March 6, 2026)

- **Audit mode not yet active** â Agent currently operates in reactive-only mode. Autonomous daily audits are defined in PROCESS.md but need to be implemented in agent.py
- **Image parsing not yet implemented** â David wants to send screenshots of issues. agent.py needs Claude's vision capability enabled to parse images
- **No learning loop yet** â RUN-LOG and LEARNING-LOG exist but agent.py doesn't read or write them yet
- **agent_activity.json** shows last active Feb 28 â may need troubleshooting if agent isn't running

---
