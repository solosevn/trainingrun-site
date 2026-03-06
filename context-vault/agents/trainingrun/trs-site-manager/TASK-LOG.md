# TASK-LOG — TRS Site Manager (TRSitekeeper)

> **Format:** Tracks pending, in-progress, and completed capability upgrades
> **Updated:** As tasks are assigned, started, or completed
> **Started:** March 6, 2026

---

## Active Tasks

### TASK-001: Enable Image-Based Fix Requests
- **Status:** 📋 Planned
- **Priority:** HIGH
- **Description:** Add Claude vision capability to agent.py so David can send screenshots of site issues and Sitekeeper can parse them, identify the problem, and fix it
- **Requirements:**
  - Update agent.py Telegram handler to accept image messages
  - Pass images to Claude API with vision enabled
  - Add image-to-fix pipeline: receive image → identify page → identify element → locate code → fix
- **Acceptance criteria:** David sends a screenshot, Sitekeeper identifies the issue and proposes/executes a fix
- **Assigned:** 2026-03-06

### TASK-002: Build Autonomous Daily Audit Loop
- **Status:** 📋 Planned
- **Priority:** HIGH
- **Description:** Implement the autonomous audit system defined in PROCESS.md. Agent systematically reviews the site daily (~1 hour), checks visual quality, data integrity, structural integrity.
- **Requirements:**
  - New audit function in agent.py (or separate audit module)
  - Scheduled trigger separate from DDP cron
  - Audit checklist implementation (from PROCESS.md)
  - Findings report generation and Telegram delivery
  - Integration with RUN-LOG.md for logging
- **Acceptance criteria:** Agent runs daily audit, finds real issues, fixes what it can, reports findings to David
- **Assigned:** 2026-03-06

### TASK-003: Build Vault Integration (Context Loader + Logger)
- **Status:** 📋 Planned
- **Priority:** HIGH
- **Description:** Build context_loader and learning_logger so this vault is actually used by the agent — not just documentation sitting in a folder. Every startup loads vault files. Every session end writes back to them.
- **Requirements:**
  - `sitekeeper_context_loader.py` — loads all 9 vault files from GitHub on startup
  - `sitekeeper_learning_logger.py` — appends to RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION on session end
  - Integration into agent.py main loop
  - Follows same pattern as Content Scout's `scout_context_loader.py`
- **Acceptance criteria:** Agent reads vault files before acting, writes logs after acting, learning data accumulates over time. Vault is operational, not decorative.
- **Assigned:** 2026-03-06

### TASK-004: Proactive Improvement Suggestions
- **Status:** 📋 Planned
- **Priority:** MEDIUM
- **Description:** After audits, generate improvement suggestions (not just bug fixes). Compare site against best practices, identify UX enhancements, layout improvements, missing features.
- **Requirements:**
  - Suggestion generation logic in audit loop
  - Suggestion template (what, why, effort, impact)
  - Telegram delivery with David approval workflow
- **Acceptance criteria:** David receives actionable suggestions with reasoning after audits
- **Assigned:** 2026-03-06

### TASK-005: Voice Message Processing
- **Status:** 📋 Planned
- **Priority:** MEDIUM
- **Description:** Handle Telegram voice messages from David — transcribe and process as fix requests
- **Requirements:**
  - Telegram voice message handler in agent.py
  - Speech-to-text integration
- **Acceptance criteria:** David sends a voice message, Sitekeeper transcribes and acts on it
- **Assigned:** 2026-03-06

---

## Completed Tasks

### TASK-000: Vault Establishment
- **Status:** ✅ Complete
- **Completed:** 2026-03-06
- **Description:** Created 9-file context vault for TRS Site Manager (Core 7 + CAPABILITIES.md + TASK-LOG.md)
- **Outcome:** Structured memory and learning framework established

---

## Task Priority Matrix

| Priority | Tasks | Next Action |
|---|---|---|
| HIGH | TASK-001 (Image fixes), TASK-002 (Daily audit), TASK-003 (Vault integration) | Implement in agent.py |
| MEDIUM | TASK-004 (Suggestions), TASK-005 (Voice) | After HIGH tasks done |
| LOW | Visual regression detection, performance monitoring | Future planning |
