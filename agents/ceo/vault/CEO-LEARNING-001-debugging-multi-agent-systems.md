# CEO-LEARNING-001: Debugging Multi-Agent Systems
## Incident: Paper 010 Wrong Card Format on news.html

**Date:** March 8, 2026
**Severity:** Medium — Visual bug on production site, no data loss
**Resolution Time:** ~2 hours across 2 sessions
**Systems Affected:** Daily News Agent, news.html (trainingrun.ai)

---

## 1. INCIDENT SUMMARY

Paper 010 ("OpenAI Shifts Strategy") was published by the Daily News Agent on March 8, 2026. The article page (day-010.html) rendered correctly, but the news card on news.html used an old V1 card format instead of the current V2.0 format. The V1 card was visually broken — wrong structure, missing elements, inconsistent with all other cards on the page.

---

## 2. THE THREE SEPARATE FAILURES

This incident involved three distinct failures that compounded each other:

### Failure 1: The V10 Restructure Broke File Paths
- During the V10 restructure (agents/ hierarchy migration), files were moved but some internal import paths were not updated
- This caused the Daily News Agent to fail on its first post-restructure run
- **Resolution:** Fixed import paths in the restructured files

### Failure 2: The Manual Card Fix Created a False Positive
- After the path fix, Paper 010's card on news.html was still wrong
- A manual fix was applied directly to news.html to correct the card HTML
- This fixed the visible symptom but DID NOT fix the root cause
- **Danger:** This created a false sense of "fixed" — the next paper would have the same problem

### Failure 3: The Root Cause — Duplicate Template in github_publisher.py
- The actual bug: `github_publisher.py` had its own hardcoded V1 card template in the `update_news_index()` function
- This template was NEVER updated when `html_stager.py` was upgraded to V2.0
- The publishing flow bypassed `build_news_card()` entirely — it was imported in main.py but never called during publishing

---

## 3. WRONG ASSUMPTION vs. ACTUAL ROOT CAUSE

### The Wrong Assumption
"The V10 restructure broke the card format because files were moved around."

**Why it seemed right:** The restructure DID break things (import paths), and the timing matched.

**Why it was wrong:** Git history proved the V2.0 template existed in html_stager.py TWO DAYS before Paper 010 ran. The restructure didn't cause the wrong template — the wrong template was hardcoded in a completely different file.

### The Actual Root Cause
`github_publisher.py` line ~180 had a hardcoded HTML card template (V1 format) inside `update_news_index()`. This function was called during every publish operation. It never imported or called `build_news_card()` from `html_stager.py`.

**The code path was:**
```
main.py: do_publish()
  → github_publisher.py: publish_article()
    → github_publisher.py: update_news_index()
      → HARDCODED V1 TEMPLATE (the bug)
      
NEVER CALLED:
  html_stager.py: build_news_card()  ← correct V2.0 template sitting unused
```

---

## 4. DEBUGGING METHODOLOGY (What Worked)

### Step 1: Verify the Timeline with Git History
- Checked `git log` for html_stager.py
- Found V2.0 was committed March 6 (commit a3889a7)
- Paper 010 ran March 8
- **Conclusion:** V2.0 existed before the paper ran, so the restructure wasn't the cause

### Step 2: Trace the Actual Code Path
- Started from the trigger: `do_publish()` in main.py
- Followed every function call: publish_article() → update_news_index()
- Found the hardcoded template in github_publisher.py
- Confirmed build_news_card() was imported but never called in the publish flow

### Step 3: Verify the Duplicate
- Compared the hardcoded template in github_publisher.py with the V2.0 template in html_stager.py
- Confirmed they were completely different — V1 vs V2.0 structure

### Step 4: Fix at the Source
- Removed the hardcoded template from github_publisher.py
- Added `from html_stager import build_news_card` 
- Made update_news_index() call build_news_card() with article data
- Single source of truth: html_stager.py is now the ONLY place card HTML is generated

### Step 5: Make the Fix Backward-Compatible
- Added `article_data: dict = None` parameter with defaults
- If article_data is None, function builds a minimal dict from existing parameters
- No breaking changes to any caller

---

## 5. CRITICAL LESSONS FOR CEO AGENT

### Lesson 1: Single Source of Truth — ENFORCE IT
When the same output (HTML, JSON, config) is generated in multiple places, they WILL diverge. One gets updated, the other doesn't. The fix is architectural:
- **One function generates each output type**
- **Every other file imports and calls that function**
- **Never copy-paste templates between files**
- **Code review should flag any duplicate generation logic**

### Lesson 2: Trace Code Paths, Don't Assume
"The code exists" is not the same as "the code runs." build_news_card() existed and was even imported — but it was never called in the publishing flow. The CEO agent must:
- **Trace execution from trigger to output** for every critical flow
- **Verify functions are actually called**, not just imported
- **Map the full call chain** before diagnosing any bug

### Lesson 3: Git History is the Source of Truth for Timelines
When debugging "what broke what," git history provides definitive answers:
- `git log --oneline <file>` shows when each change was made
- `git show <commit>` shows exactly what changed
- **Never accept timeline assumptions** — verify with commits
- **This prevents blame attribution errors** (e.g., blaming restructure when the bug predated it)

### Lesson 4: Symptom Fixes Create Debt
Manually fixing Paper 010's card on news.html fixed what the user sees but:
- Did NOT fix the code that generated the wrong card
- The next paper would have had the exact same bug
- **Always ask: "What generates this output?" not just "What does the output look like?"**
- **Symptom fixes are acceptable ONLY as temporary measures while the root cause is being found**

### Lesson 5: Test After Every Fix
- Committing code is NOT the same as delivering a working feature
- After the github_publisher.py fix was committed, we should verify the next publish uses the correct template
- **"Done" = tested and confirmed working, not "code pushed to GitHub"**

### Lesson 6: Multi-File Bugs Are the Hardest to Find
- The bug spanned 3 files: main.py (orchestrator), html_stager.py (correct template), github_publisher.py (wrong template)
- No single file had an obvious error
- **The bug was in the relationship between files, not in any one file**
- CEO agent should maintain a map of which functions generate which outputs

---

## 6. AGENT ECOSYSTEM CONTEXT

### How the Daily News Agent Works
1. Content Scout sends morning briefing (scout-briefing.json) at 5:30 AM CST
2. Daily News Agent picks up briefing, selects top story
3. Agent writes full article using Grok 3 (xAI API)
4. html_stager.py generates the article HTML page AND the news card
5. github_publisher.py publishes article page to GitHub AND updates news.html index
6. **The bug was in step 5** — publisher had its own card template instead of using step 4's output

### File Relationships (Post-Fix)
```
html_stager.py
  └── build_news_card()  ← SINGLE SOURCE OF TRUTH for card HTML
  
github_publisher.py
  ├── from html_stager import build_news_card  ← imports the function
  ├── publish_article()  ← publishes the article page
  └── update_news_index()  ← now calls build_news_card() for the card
  
main.py
  └── do_publish()  ← orchestrates the flow
```

---

## 7. RESOLUTION VERIFICATION CHECKLIST

For any similar bug in the future, verify:

- [ ] Root cause identified (not just symptoms)
- [ ] Fix applied to the SOURCE of the problem (not the output)
- [ ] Git history reviewed to establish accurate timeline
- [ ] Code path traced from trigger to output
- [ ] No duplicate generation logic remains
- [ ] Fix is backward-compatible (existing callers don't break)
- [ ] Training entry added to affected agent's LEARNING-LOG.md
- [ ] CEO Learning Document created (this document)
- [ ] Next run tested to confirm fix works

---

## 8. WHAT THE CEO AGENT WOULD HAVE DONE DIFFERENTLY

If a CEO agent had been overseeing this system:

1. **Pre-deployment audit:** Before the V10 restructure, the CEO would have mapped all cross-file dependencies and verified no duplicate logic existed
2. **Automated template consistency check:** A scheduled check could compare card HTML output from html_stager.py vs what actually appears on news.html
3. **Post-publish verification:** After every paper publishes, automatically verify the news card HTML matches the expected V2.0 structure
4. **Import vs. usage audit:** Periodically check that imported functions are actually called in the expected code paths
5. **Immediate root cause investigation:** Instead of accepting the manual card fix as "done," the CEO would have flagged "the symptom is fixed but the code path hasn't been verified"

---

*Document created: March 8, 2026*
*Incident resolved: March 8, 2026*
*Author: Claude (via Cowork session with David Solomon)*
*Classification: Multi-Agent Debugging / Architecture / Code Quality*
