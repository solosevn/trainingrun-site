# PROCESS.md — Daily News Agent
## Autonomous Workflow — 15-Step Pipeline
> **Location:** context-vault/agents/trainingrun/daily-news/PROCESS.md
> **Version:** 3.1 — March 6, 2026
> **Owner:** David Solomon
> **Status:** Active
> **Previous:** V3.0 defined the full autonomous 15-step pipeline. V3.1 closes the learning loop — the agent now reads its own history, recommends improvements, and tracks audience engagement.

---

## Overview

This document defines the complete end-to-end autonomous workflow for the Daily News Agent. The agent executes Steps 1-8 and 11-15 independently. Steps 9-10 require human input. Step 12 requires human action (image upload).

**Autonomy model:** The agent is autonomous for everything except the publish decision and image upload. David gates the output. The agent fills the space between with autonomous work.

**Target cycle time:** Under 30 minutes from Content Scout delivery to "Article ready for review" Telegram (Steps 1-8).

**Learning model (V3.1):** The agent reads its own history at the start of every cycle, actively recommends improvements via Telegram, and tracks audience engagement to learn what readers respond to. Three loops feed continuous improvement:
- **Loop 1 — Read:** Agent reads LEARNING-LOG.md, RUN-LOG.md, and ENGAGEMENT-LOG.md at cycle start (Step 2)
- **Loop 2 — Recommend:** Agent surfaces pattern-based suggestions via Telegram for David's approval (Step 2b)
- **Loop 3 — Engage:** Agent logs and reads audience metrics to connect editorial choices to reader response (Step 15)

---

## THE 15-STEP WORKFLOW

### STEP 1 — Content Scout Delivers
**Trigger:** Content Scout's Telegram notification arrives (~5:30am CST)
**What happens:** Content Scout has scraped, filtered, and delivered 3-8 AI news stories to Mission Control.
**Agent action:** None yet — this is the trigger event.

---

### STEP 2 — Agent Activates + Reads History
**Timing:** ~10 minutes after Content Scout's Telegram ping
**What happens:** The Daily News Agent wakes up and begins its cycle. Before doing any work, it reads its full context — identity, style rules, AND its own recent performance history.
**Agent action:**
1. Read `context-vault/org/USER.md` — internalize David's personality and decision criteria
2. Read `context-vault/agents/trainingrun/daily-news/STYLE-EVOLUTION.md` — apply latest learnings
3. Read Mission Control output — all stories delivered by Content Scout
4. **[V3.1] Read tail of `LEARNING-LOG.md` (~last 8k tokens)** — what happened in recent cycles, what edits David requested, what the agent reflected on
5. **[V3.1] Read last 5 entries from `RUN-LOG.md`** — recent publish history, approval rates, cycle times
6. **[V3.1] Read tail of `ENGAGEMENT-LOG.md` (~last 10k tokens)** — what readers actually responded to, which topics and formats performed

**The agent now has full context: who David is, what the style rules are, what stories are available, what it did recently, how David reacted, and what readers engaged with.**

---

### STEP 2b — Recommendation Check (V3.1)
**Timing:** After Step 2 context load, before story selection
**What happens:** The agent scans its loaded history for actionable patterns and surfaces recommendations to David via Telegram.
**Agent action:**
1. Analyze recent LEARNING-LOG entries for repeating patterns (e.g., "3 of last 5 articles needed tone edits," "policy articles consistently need angle adjustment")
2. Cross-reference with ENGAGEMENT-LOG data (e.g., "articles with comparison tables got 2x engagement," "technical deep-dives underperform short explainers")
3. If a clear, evidence-backed pattern is found, send a Telegram recommendation:

```
💡 TRNewzBot — Learning Recommendation

Pattern detected: [describe the pattern with evidence]
Example: "My last 3 AI safety articles got first-pass approval, but both policy pieces needed tone edits — David softened the language each time."

Suggested action: [specific proposed change]
Example: "Adjust policy article tone to be more measured, less assertive. Draft a new STYLE-EVOLUTION rule?"

Reply:
✅ "yes" — I'll add this as a new rule to STYLE-EVOLUTION.md
❌ "no" — noted, I won't bring this up again unless new evidence emerges
```

4. **If David says yes:** Append a new rule to STYLE-EVOLUTION.md with the evidence basis and date
5. **If David says no:** Log the rejection in LEARNING-LOG.md so the agent doesn't repeat the same suggestion without new supporting data
6. **If no clear pattern found:** Skip this step silently, proceed to Step 3

**This step is non-blocking.** If David doesn't respond within 10 minutes, the agent proceeds to Step 3 and handles the recommendation response asynchronously.

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

**[V3.1] Selection is now informed by history.** The agent weighs its recent performance data:
- Avoid repeating topic categories that underperformed recently (from ENGAGEMENT-LOG)
- Prefer angles that earned first-pass approval (from LEARNING-LOG)
- Note if David has been editing toward a certain direction — lean into it

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

**[V3.1] Writing is now informed by history.** The article_writer prompt includes:
- Recent LEARNING-LOG entries (what edits David made, what the agent reflected on)
- Recent ENGAGEMENT-LOG data (what formats and angles readers responded to)
- The agent applies these lessons in real-time, not just from STYLE-EVOLUTION rules

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

**[V3.1] /feedback command:** After editing, David can also reply with:
```
/feedback NNN [tags: tone, accuracy, length, angle, framing, structure, other]
```
This structured feedback is appended directly to LEARNING-LOG.md and accelerates the pattern detection in Step 2b.

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

### STEP 15 — Post-Publish Learning + Engagement Tracking
**What happens:** Agent monitors performance, logs learnings, and captures audience data.
**Agent action (24-48 hours after publish):**

1. **Capture audience metrics:**
   - Page views on trainingrun.ai (if analytics available)
   - X post: impressions, engagements, reposts, replies, bookmarks
   - Click-through rate from X to the article
   - Any notable comments or shares

2. **[V3.1] Log to ENGAGEMENT-LOG.md:**
   - Article identifier (Paper NNN, title, category)
   - Platform metrics (X impressions, engagements, bookmarks, CTR)
   - Notable reader feedback (comments, quote tweets, questions)
   - Format observations (what structural elements were used — tables, comparisons, deep-dive vs. explainer)

3. **Log to LEARNING-LOG.md:**
   - Full post-mortem entry for this article
   - Process timing per phase
   - Edit requests and types
   - Audience metrics summary
   - "What I'd do differently" reflection

4. **Check for patterns:**
   - Is this topic category performing above or below average?
   - Did a specific writing approach work better/worse?
   - Is my cycle time improving?
   - Am I making the same edit mistakes?
   - **[V3.1]** Which format elements correlate with higher engagement?
   - **[V3.1]** Are there topics readers keep asking for more of?

5. **Update STYLE-EVOLUTION.md if a new pattern emerges:**
   - New rule: "Articles about [topic] get [X]% more engagement"
   - Correction: "David corrected [pattern] — avoid in future"
   - Process: "Phase [X] can be optimized by [approach]"
   - **[V3.1]** Engagement rule: "Articles with [format element] get [X] more reader response"

6. **Feed learnings into tomorrow's cycle:**
   - STYLE-EVOLUTION.md is read at Step 2 of the next day's cycle
   - **[V3.1]** LEARNING-LOG.md is read at Step 2 — raw recent history
   - **[V3.1]** ENGAGEMENT-LOG.md is read at Step 2 — what readers actually loved
   - The improvement compounds

---

## WORKFLOW DIAGRAM

```
Content Scout delivers (5:30am CST)
        │
        ▼
[STEP 1] Trigger received
        │
        ▼
[STEP 2] Agent activates — reads USER.md + STYLE-EVOLUTION.md + stories
         + LEARNING-LOG.md + RUN-LOG.md + ENGAGEMENT-LOG.md  ← [V3.1]
        │
        ▼
[STEP 2b] Recommendation check — surface patterns via Telegram  ← [V3.1]
        │
        ▼
[STEP 3] Read all stories from Mission Control
        │
        ▼
[STEP 4] Apply 5-filter selection test (informed by history)  ← [V3.1]
        │
        ▼
[STEP 5] Run REASONING-CHECKLIST on selected story
        │
        ▼
[STEP 6] Write article in David's voice (informed by history)  ← [V3.1]
        │
        ▼
[STEP 7] Stage draft (create day-NNN.html)
        │
        ▼
[STEP 8] Send Telegram: "Article ready for review"
        │
        ▼
[STEP 9] ██ HUMAN GATE — David reviews ██
        │                               │
    ✅ Approve                    ✏️ Edit requested
        │                               │
        │                       [STEP 10] Revise + /feedback → back to Step 9
        │
        ▼
[STEP 11] Approval received
        │
        ▼
[STEP 12] David uploads image (human action)
        │
        ▼
[STEP 13] Agent commits article + updates news.html
        │
        ▼
[STEP 14] Agent sends publish confirmation Telegram + logs to RUN-LOG.md
        │
        ▼
[STEP 15] Post-publish learning + engagement tracking  ← [V3.1]
        │
        ▼
    ┌─── NEXT DAY ───┐
    │  Back to Step 1  │
    └──────────────────┘
```

---

## THE THREE LEARNING LOOPS (V3.1)

```
LOOP 1 — SHORT-TERM MEMORY (every cycle)
  ┌─────────────────────────────────────────────┐
  │ Step 2: Read LEARNING-LOG + RUN-LOG         │
  │    ↓                                         │
  │ Steps 3-6: Selection + writing informed      │
  │    ↓                                         │
  │ Step 14-15: Log results back to both files   │
  │    ↓                                         │
  │ Next cycle reads the updated logs            │
  └─────────────────────────────────────────────┘

LOOP 2 — RECOMMENDATION LOOP (when patterns emerge)
  ┌─────────────────────────────────────────────┐
  │ Step 2b: Analyze history for patterns        │
  │    ↓                                         │
  │ Telegram: "David, I noticed [pattern]"       │
  │    ↓                                         │
  │ David says YES → new STYLE-EVOLUTION rule    │
  │ David says NO → logged, not repeated         │
  │    ↓                                         │
  │ Next cycle reads updated STYLE-EVOLUTION     │
  └─────────────────────────────────────────────┘

LOOP 3 — ENGAGEMENT LOOP (24-48 hours post-publish)
  ┌─────────────────────────────────────────────┐
  │ Step 15: Capture audience metrics            │
  │    ↓                                         │
  │ Log to ENGAGEMENT-LOG.md                     │
  │    ↓                                         │
  │ Next cycle reads engagement data (Step 2)    │
  │    ↓                                         │
  │ Selection + writing adapts to what works     │
  └─────────────────────────────────────────────┘
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
  ├── USER.md (Step 2, Step 4, Step 6)
  ├── REASONING-CHECKLIST.md (Step 5)
  ├── STYLE-EVOLUTION.md (Step 2, Step 2b, Step 15)
  ├── LEARNING-LOG.md (Step 2, Step 2b, Step 10, Step 14, Step 15)
  ├── RUN-LOG.md (Step 2, Step 14)
  ├── ENGAGEMENT-LOG.md (Step 2, Step 2b, Step 15)  ← [V3.1 NEW]
  ├── CONFIG.md (Steps 7, 8, 13, 14 — templates, paths, Telegram formats)
  ├── CADENCE.md (timing and triggers)
  └── day-template.html (Step 7)
```

---

*This process runs every day. It improves every day. The agent is autonomous for 13 of 15 steps. David holds the gate on Step 9 and Step 12. Everything else is the agent's job. V3.1 closes the loop — the agent doesn't just execute, it learns from every cycle and gets better.*
