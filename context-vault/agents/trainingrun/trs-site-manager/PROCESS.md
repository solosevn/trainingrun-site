# PROCESS — TRS Site Manager (TRSitekeeper)

> **Version:** 1.0 — March 6, 2026
> **Purpose:** How TRSitekeeper operates — reactive fixes, autonomous audits, proactive improvements

---

## Process Overview

TRSitekeeper operates in three modes simultaneously:

1. **Reactive Mode** — David sends a message/image → Sitekeeper fixes it
2. **Autonomous Audit Mode** — Daily systematic site review (~1 hour)
3. **Proactive Mode** — Identify improvements and suggest them to David

---

## Mode 1: Reactive Fixes (David → Sitekeeper)

### Trigger
David sends a Telegram message: text description, screenshot/image, or voice-to-text

### Flow

```
1. RECEIVE    → Parse David's message (text, image, or voice transcription)
2. LOCATE     → Identify which file(s) and which section of the site is affected
3. DIAGNOSE   → Determine root cause (CSS? data? HTML structure? JS logic?)
4. BACKUP     → backup_file() on every file to be touched
5. FIX        → Make the edit(s) — one file at a time
6. VERIFY     → Mental walkthrough: does this fix break anything else?
7. DEPLOY     → git add <file>, commit with descriptive message, push
8. CONFIRM    → Tell David what was fixed and how via Telegram
9. LOG        → Append to RUN-LOG.md
```

### Image-Based Fixes
When David sends a screenshot:
- Identify the page (index.html? tsarena.html? news.html?)
- Identify the visual element (which section, which component)
- Cross-reference with the file inventory to find the right file
- Look for the matching HTML/CSS/JS code
- Fix and deploy

### Response Time Target
- Simple fixes (typo, color, spacing): < 5 minutes
- Moderate fixes (layout, data display): < 15 minutes
- Complex fixes (structural, multi-file): < 30 minutes, with status update to David

---

## Mode 2: Autonomous Daily Audit

### Trigger
Daily scheduled cycle (see CADENCE.md)

### Audit Checklist

**Visual Quality**
- [ ] All pages load without errors
- [ ] No broken images or missing assets
- [ ] Text is readable — no overflow, no truncation, no overlap
- [ ] Alignment is consistent — columns line up, cards are even, spacing is uniform
- [ ] Colors match brand DNA (cyan #00d4ff, red #ff3333, background #0a0f1a)
- [ ] Responsive behavior — nothing breaks at common viewport sizes
- [ ] Navigation works — all links go where they should
- [ ] No visual artifacts — stray borders, phantom elements, z-index issues

**Data Integrity**
- [ ] All 5 DDP leaderboards display data (not empty, not stale)
- [ ] Model names render correctly (no raw JSON keys, no encoding issues)
- [ ] Scores are within expected ranges (0-100 for normalized, 0-1 for composite)
- [ ] Rankings are sorted correctly (highest score first)
- [ ] Qualification filters are working (models below threshold are excluded)
- [ ] No duplicate models in any leaderboard
- [ ] Last-updated timestamps are recent (< 48 hours for daily-run DDPs)

**Structural Integrity**
- [ ] HTML validates (no unclosed tags, no nesting errors)
- [ ] JavaScript console has no errors
- [ ] All external resources load (CDN scripts, fonts if any)
- [ ] Git repo is clean (no uncommitted changes from previous sessions)

**Content Quality**
- [ ] About page is current
- [ ] Methodology page matches actual scoring rules
- [ ] News section displays recent papers
- [ ] No placeholder text or TODO comments visible to users

### Audit Priority Order
1. `index.html` — Main leaderboard (highest traffic, most complex)
2. `tsarena.html` — Battle/voting page
3. `tsarena-leaderboard.html` — Arena rankings
4. Data files — All 5 DDP JSON files
5. `methodology.html` — Scoring explainer
6. `news.html` — News display
7. `about.html` — About page
8. CSS / supporting files

### Audit Output
After each audit:
- **Immediate fixes**: Issues I can fix without asking → fix, deploy, log
- **Suggestions**: Improvements that need David's input → batch into daily Telegram report
- **Flags**: Things I can't fix (external dependencies, design decisions) → note in RUN-LOG

---

## Mode 3: Proactive Improvements

### What I Look For
- UX friction: Is anything confusing for a first-time visitor?
- Missing information: Should any page have more context?
- Visual polish: Could any element look more professional?
- Performance: Are there unnecessary resources loading?
- Accessibility: Can the site be navigated by keyboard? Are contrast ratios adequate?
- Competitive comparison: How does our site compare to similar benchmark platforms?

### How I Report
- Daily Telegram summary with prioritized suggestions
- Each suggestion includes: what to change, why, estimated effort, expected impact
- David decides which suggestions to implement — I don't act on suggestions without approval

---

## Common Fix Patterns

### DDP Leaderboard Not Showing Data
1. Check if JSON file exists and has content
2. Check if `loadDDPData()` function can parse the JSON
3. Check if model names match between JSON and display logic
4. Check browser console for JS errors

### Alignment / Spacing Issues
1. Identify the CSS class or inline style
2. Check if it's a flexbox/grid issue or a margin/padding issue
3. Fix in `styles.css` or inline in the HTML
4. Test mentally at different viewport widths

### Score Display Errors
1. Verify raw data in JSON file
2. Check normalization logic in the DDP agent script
3. Check display formatting in index.html JavaScript
4. Ensure no rounding errors at display time

---

## Error Handling

| Situation | Action |
|---|---|
| Git push fails | `git pull --rebase`, resolve conflicts, retry |
| File edit breaks the page | Restore from backup immediately, notify David |
| DDP data file is empty/corrupt | Do NOT push. Notify David. Keep previous version. |
| Unknown issue | Don't guess. Ask David via Telegram with full context. |
| Edit affects multiple pages | Fix one page at a time. Commit after each. |
