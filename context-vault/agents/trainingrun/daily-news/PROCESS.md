# PROCESS.md — Daily News Agent
## Autonomous Workflow — 15-Step Pipeline
> **Location:** context-vault/agents/trainingrun/daily-news/PROCESS.md
> **Version:** 3.0 — March 5, 2026
> **Owner:** David Solomon
> **Status:** Active
> **Previous:** V2.0 was the manual publishing bible. V3.0 wraps it in the autonomous agent workflow with learning loop.

---

## Overview

This document defines the complete end-to-end autonomous workflow for the Daily News Agent. The agent executes Steps 1-8 and 11-15 independently. Steps 9-10 require human input. Step 12 requires human action (image upload).

**Autonomy model:** The agent is autonomous for everything except the publish decision and image upload. David gates the output. The agent fills the space between with autonomous work.

**Target cycle time:** Under 30 minutes from Content Scout delivery to "Article ready for review" Telegram (Steps 1-8).

---

## THE 15-STEP WORKFLOW

### STEP 1 — Content Scout Delivers
**Trigger:** Content Scout's Telegram notification arrives (~5:30am CST)
**What happens:** Content Scout has scraped, filtered, and delivered 3-8 AI news stories to Mission Control.
**Agent action:** None yet — this is the trigger event.

---

### STEP 2 — Agent Activates
**Timing:** ~10 minutes after Content Scout's Telegram ping
**What happens:** The Daily News Agent wakes up and begins its cycle.
**Agent action:**
1. Read `context-vault/org/USER.md` — internalize David's personality and decision criteria
2. Read `context-vault/agents/trainingrun/daily-news/STYLE-EVOLUTION.md` — apply latest learnings
3. Read Mission Control output — all stories delivered by Content Scout

---

### STEP 3 — Read All Stories
**What happens:** Agent reads every story from Mission Control, not just headlines. Full content consumption.
**Agent action:**
- Read each story's source material (paper abstract, key findings, methodology if relevant)
- Note the source: arXiv paper? News article? Lab blog post?
- Flag any stories that seem unverifiable or clickbait-ish — these fail Filter 1 immediately

---

### STEP 4 — Apply Selection Criteria
**What happens:** Agent applies David's 5-filter test from USER.md to each story.
**Agent action — run each story through these filters in order:**

1. **Is it true?** — Can we verify the claims? Are the sources credible? If not, pass.
2. **Does it matter to real people?** — Not just researchers. Would a parent, teacher, worker care?
3. **What problem does it solve?** — Clear problem-solution framing must be possible.
4. **Is it timely?** — Are we ahead of the curve, or is this already everywhere?
5. **Can I explain it simply?** — If I can't explain it in layman's terms, it's not ready.

**Output:** Ranked list of stories that pass all 5 filters. Best story selected.

**If multiple stories pass:** Select the strongest. Note runner-ups in the Telegram message (Step 8).

**If zero stories pass:** Send Telegram to David: "None of today's stories passed the filter. Want me to dig deeper or skip today?"

---

### STEP 5 — Run Reasoning Checklist
**What happens:** Before writing, the agent runs the full REASONING-CHECKLIST.md on the selected story.
**Agent action — complete all 5 steps from `context-vault/org/shared-context/REASONING-CHECKLIST.md`:**

```
PREMISE P1: [Source paper / article — cite it]
PREMISE P2: [Key claims from the source — verified or assumed?]
PREMISE P3: [David's audience — what matters to them about this?]

TRACE T1: [Problem this paper addresses]
TRACE T2: [Solution or finding]
TRACE T3: [Why this matters to non-researchers]
TRACE T4: [Potential misinterpretation or nuance to handle carefully]

CLAIM C1: [This story is worth publishing because...] — supported by P1, P3, T3
CLAIM C2: [The key takeaway for David's audience is...] — supported by T2, T3

UNCERTAIN: [Anything I can't verify] — surface to David if critical
ACTION NEEDED: [What would resolve the uncertainty]

CONCLUSION: Write article on [topic] with focus on [angle]
BASIS: C1, C2
HUMAN REVIEW NEEDED: YES
```

**This checklist is NOT optional.** It's the quality gate. Skip it and you get confident wrong answers.

---

### STEP 6 — Write the Article
**What happens:** Agent writes the full article in David's voice.
**Agent action:**

**Voice rules (from USER.md):**
- Warm, direct, confident — not a press release
- First person where appropriate
- Short and simple — under 1000 words unless topic demands more
- Problem first, solution second, why it matters third
- Layman's terms — explain any technical term immediately
- If David's kids can't understand the gist, rewrite it

**Required elements:**
- Headline that tells you what you'll learn (not clickbait)
- Opening that states the problem in plain language
- Body that explains the solution/finding
- "Why this matters" section — connect it to real people's lives
- Full source citation block (see CONFIG.md for format)
- At least one visual callout (figure from paper, or note that image is needed)
- David's signature block at the bottom

**Article structure follows `day-template.html`:**
- Meta tags for social sharing (og:title, og:description, og:image)
- Category badge using `article-tag` CSS class
- Navigation links
- Responsive layout

---

### STEP 7 — Stage the Draft
**What happens:** Agent creates the article file and prepares it for review.
**Agent action:**
1. Check the last published paper number (scan `news.html` or repo files)
2. Increment to next number (e.g., `day-007.html` → `day-008.html`)
3. Create `day-NNN.html` from `day-template.html`
4. Populate with article content
5. Add image placeholder (David will upload the actual image)
6. Stage but DO NOT commit yet

---

### STEP 8 — Send Review Telegram
**What happens:** Agent notifies David that the article is ready.
**Agent action:** Send Telegram via TRNewzBot (@TRnewzBot):

```
📰 TRNewzBot — Article Ready for Review

Title: [article title]
Source: [paper title + authors]
Paper: Paper [NNN]

Preview: [link to staged draft or GitHub preview]

Runner-ups today: [list any other stories that passed the 5-filter test, or "none"]

Reply with:
✅ "push it" — publish as-is
✏️ "edit: [your notes]" — I'll revise and re-send
❌ "kill it" — skip this story today
```

---

### STEP 9 — HUMAN GATE (David Reviews)
**What happens:** Agent STOPS and WAITS. This is the one step that is never automated.
**David's options:**
- ✅ **"push it"** → proceed to Step 12
- ✏️ **"edit: [notes]"** → proceed to Step 10
- ❌ **"kill it"** → agent logs the skip in RUN-LOG.md, cycle ends
- **Override story selection** → David picks a different story from the runner-ups, agent goes back to Step 6

**The agent never publishes without David's explicit approval. Ever.**

---

### STEP 10 — Revision Cycle (if edits requested)
**What happens:** Agent revises the article based on David's feedback.
**Agent action:**
1. Read David's edit notes from Telegram
2. Make the requested changes
3. Log the edit type in LEARNING-LOG.md (tone? accuracy? length? angle? other?)
4. Send updated Telegram:

```
✏️ Revision ready — Paper [NNN]

Changes made: [summary of edits]
Preview: [updated link]

Reply ✅ to publish or ✏️ for more edits.
```

5. Return to Step 9 (wait for approval)

**Every edit David requests is a learning signal.** The agent logs the pattern so it can avoid the same correction in future articles.

---

### STEP 11 — Approval Received
**What happens:** David says "push it" — the article is approved.
**Agent action:** Prepare for publish. Move to Step 12.

---

### STEP 12 — Image Upload (David's Action)
**What happens:** David uploads the article image to `assets/news/` via GitHub drag-drop.
**David's action:**
- Navigate to `assets/news/` on GitHub
- Drag-drop the image file (keep original filename)
- Commit with descriptive message

**Agent note:** If David signals the image is uploaded, proceed to Step 13. If David says "use the paper's figure," agent can reference it directly.

---

### STEP 13 — Publish
**What happens:** Agent commits the article and updates the news index.
**Agent action:**
1. Update `day-NNN.html` with the correct image path (including `?v=NNN` cache buster)
2. Commit `day-NNN.html` with message: "Publish day-NNN: [article title]"
3. Add new card to TOP of `news.html` article list
4. Commit `news.html` with message: "Add Paper NNN to news listing"
5. Verify GitHub Pages deployment triggers

---

### STEP 14 — Publish Confirmation
**What happens:** Agent confirms publication to David.
**Agent action:** Send Telegram via TRNewzBot:

```
✅ Paper [NNN] published!

Title: [title]
URL: https://trainingrun.ai/day-[NNN].html
news.html updated ✓

Post-publish tracking active — I'll log performance in 24-48 hours.
```

**Also:** Log the full run to RUN-LOG.md:
- Date, paper number, title, source, category
- Process timing (each phase)
- Edit count and types
- First-pass approval: YES/NO

---

### STEP 15 — Post-Publish Learning
**What happens:** Agent monitors performance and logs learnings.
**Agent action (24-48 hours after publish):**

1. **Capture audience metrics:**
   - Page views on trainingrun.ai (if analytics available)
   - X post: impressions, engagements, reposts, replies, bookmarks
   - Click-through rate from X to the article
   - Any notable comments or shares

2. **Log to LEARNING-LOG.md:**
   - Full post-mortem entry for this article
   - Process timing per phase
   - Edit requests and types
   - Audience metrics
   - "What I'd do differently" reflection

3. **Check for patterns:**
   - Is this topic category performing above or below average?
   - Did a specific writing approach work better/worse?
   - Is my cycle time improving?
   - Am I making the same edit mistakes?

4. **Update STYLE-EVOLUTION.md if a new pattern emerges:**
   - New rule: "Articles about [topic] get [X]% more engagement"
   - Correction: "David corrected [pattern] — avoid in future"
   - Process: "Phase [X] can be optimized by [approach]"

5. **Feed learnings into tomorrow's cycle:**
   - STYLE-EVOLUTION.md is read at Step 2 of the next day's cycle
   - The improvement compounds

---

## WORKFLOW DIAGRAM

```
Content Scout delivers (5:30am CST)
        |
        v
[STEP 1] Trigger received
        |
        v
[STEP 2] Agent activates — reads USER.md + STYLE-EVOLUTION.md + stories
        |
        v
[STEP 3] Read all stories from Mission Control
        |
        v
[STEP 4] Apply 5-filter selection test
        |
        v
[STEP 5] Run REASONING-CHECKLIST on selected story
        |
        v
[STEP 6] Write article in David's voice
        |
        v
[STEP 7] Stage draft (create day-NNN.html)
        |
        v
[STEP 8] Send Telegram: "Article ready for review"
        |
        v
[STEP 9] == HUMAN GATE — David reviews ==
        |                               |
    Approve                       Edit requested
        |                               |
        |                       [STEP 10] Revise -> back to Step 9
        |
        v
[STEP 11] Approval received
        |
        v
[STEP 12] David uploads image (human action)
        |
        v
[STEP 13] Agent commits article + updates news.html
        |
        v
[STEP 14] Agent sends publish confirmation Telegram
        |
        v
[STEP 15] Post-publish learning (24-48 hours later)
        |
        v
    --- NEXT DAY ---
     Back to Step 1
```

---

## MECHANICAL REFERENCE

For detailed technical execution (CodeMirror selectors, GitHub UI steps, commit message automation, image upload mechanics), see:
- **CONFIG.md** — GitHub Workflow section
- **PRODUCTION_BIBLE.md** — repo root, full production standards

---

## FILE DEPENDENCIES

```
PROCESS.md references:
  |- USER.md (Step 2, Step 4, Step 6)
  |- REASONING-CHECKLIST.md (Step 5)
  |- STYLE-EVOLUTION.md (Step 2, Step 15)
  |- LEARNING-LOG.md (Step 10, Step 14, Step 15)
  |- RUN-LOG.md (Step 14)
  |- CONFIG.md (Steps 7, 8, 13, 14 — templates, paths, Telegram formats)
  |- CADENCE.md (timing and triggers)
  |- day-template.html (Step 7)
```

---

*This process runs every day. It improves every day. The agent is autonomous for 13 of 15 steps. David holds the gate on Step 9 and Step 12. Everything else is the agent's job.*
