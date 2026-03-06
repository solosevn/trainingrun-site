# CAPABILITIES — TRS Site Manager (TRSitekeeper)

> **Version:** 1.0 — March 6, 2026
> **Purpose:** What TRSitekeeper can and cannot do — current abilities, planned upgrades, limitations

---

## Current Capabilities (Live)

### 1. Reactive File Editing
- **Status:** ✅ Active
- **Description:** Receives text commands from David via Telegram, locates the relevant file, makes edits, commits, pushes
- **Tools:** `read_file()`, `write_file()`, `backup_file()`, `git_commit()`, `git_push()`
- **Strength:** Fast, reliable for known file types (HTML, CSS, JSON, Python)

### 2. DDP Pipeline Orchestration
- **Status:** ✅ Active
- **Description:** Triggers daily DDP runs via `daily_runner.py`. Monitors which DDPs are enabled/disabled. Verifies output JSON files.
- **Cron:** `0 4 * * * daily_runner.py`
- **Sub-agent:** DDP Pipeline handles the 5 individual scraper/scoring agents

### 3. Git Workflow Management
- **Status:** ✅ Active
- **Description:** Pull, edit, commit, push cycle with backup-first protocol
- **Safety:** Always pulls before pushing, always backs up before editing, never uses `git add -A`

### 4. Site Knowledge
- **Status:** ✅ Active
- **Description:** Deep knowledge of all 49 files in the repo, index.html architecture, DDP data format, CSS structure
- **Source:** brain.md v2.0

### 5. Telegram Communication
- **Status:** ✅ Active
- **Description:** Receives and sends messages via Telegram Bot API
- **Supports:** Text messages, status updates, fix confirmations

---

## Planned Capabilities (To Build)

### 6. Image-Based Fix Requests
- **Status:** 🔧 Planned
- **Description:** David sends a screenshot showing a visual issue. Sitekeeper uses Claude's vision to identify the problem, locate it in the code, and fix it.
- **Requirements:** Enable Claude vision API in agent.py, add image parsing to message handler
- **Priority:** HIGH — David specifically wants this

### 7. Autonomous Daily Audits
- **Status:** 🔧 Planned
- **Description:** ~1 hour daily systematic review of the entire site. Checks visual quality, data integrity, structural integrity, content quality. Fixes what it can, reports what it can't.
- **Requirements:** New audit loop in agent.py, scheduled trigger (separate from DDP cron), audit checklist from PROCESS.md
- **Priority:** HIGH — core to the autonomous agent vision

### 8. Proactive Improvement Suggestions
- **Status:** 🔧 Planned
- **Description:** After audits, identify not just problems but opportunities. Suggest UX improvements, layout enhancements, missing features, performance optimizations.
- **Requirements:** Comparison framework, suggestion template, David approval workflow
- **Priority:** MEDIUM — builds on audit capability

### 9. Learning Loop
- **Status:** 🔧 Planned
- **Description:** Read and write vault files (RUN-LOG, LEARNING-LOG, STYLE-EVOLUTION). Track which issues recur, which sources cause problems, which fix patterns work. Adapt behavior over time.
- **Requirements:** Context loader (like scout_context_loader.py), learning logger, vault file read/write integration in agent.py
- **Priority:** MEDIUM — enables long-term improvement

### 10. Voice-to-Text Processing
- **Status:** 🔧 Planned
- **Description:** David sends voice messages via Telegram. Sitekeeper transcribes and processes them as fix requests.
- **Requirements:** Telegram voice message handling, speech-to-text integration
- **Priority:** MEDIUM — David sometimes uses voice

### 11. Visual Regression Detection
- **Status:** 💡 Future
- **Description:** Take screenshots of each page before and after changes. Compare to detect unintended visual regressions.
- **Requirements:** Headless browser (Playwright), screenshot comparison library
- **Priority:** LOW — nice-to-have for quality assurance

### 12. Performance Monitoring
- **Status:** 💡 Future
- **Description:** Run Lighthouse audits, track page load times, monitor Core Web Vitals
- **Requirements:** Lighthouse CLI or API integration
- **Priority:** LOW — optimization layer

---

## Limitations

| Limitation | Workaround |
|---|---|
| Cannot see the live website visually (no browser) | Relies on HTML/CSS analysis — planned: Playwright screenshots |
| Cannot run JavaScript to test interactivity | Mental walkthroughs of JS logic |
| Cannot test on multiple devices/browsers | Tests CSS logic for common breakpoints |
| Cannot access external APIs directly | DDP Pipeline handles all external data fetching |
| Single branch (main) — no staging environment | Backup protocol + careful edits mitigate risk |
| Cost-constrained (~1 hour/day for audits) | Prioritized audit rotation (see CADENCE.md) |

---

## Capability Maturity Model

| Level | Description | Status |
|---|---|---|
| L1 — Reactive | Fix issues when David reports them | ✅ Current |
| L2 — Autonomous | Find and fix issues independently | 🔧 Building |
| L3 — Proactive | Suggest improvements before they're needed | 🔧 Planned |
| L4 — Learning | Adapt behavior based on patterns and feedback | 💡 Future |
| L5 — Self-Improving | Optimize own processes, reduce error rate over time | 💡 Future |
