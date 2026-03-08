# LEARNING-LOG.md — Daily News Agent
## Performance & Process Data — The Agent's Raw Memory
> **Location:** context-vault/agents/trainingrun/daily-news/LEARNING-LOG.md
> **Version:** 1.1 — March 6, 2026
> **Owner:** David Solomon
> **Status:** Active — entries begin with Paper 008
> **Previous:** V1.0 defined the entry template and monthly summary format. V1.1 adds the /feedback command structure, recommendation tracking, and engagement cross-reference — closing the loop so the agent reads this file at cycle start, not just writes to it.

---

## Purpose

This is the Daily News Agent's raw memory. Every article gets a post-mortem entry that captures what happened, how long it took, what David changed, how the audience responded, and what the agent would do differently. This data feeds STYLE-EVOLUTION.md — where patterns are distilled into actionable rules.

**This file is append-only.** Entries are never modified after they're written. The raw data stays raw.

**[V1.1] This file is now read at the start of every cycle (Step 2 of PROCESS.md).** The agent loads the last ~8k tokens of this file into its context before selecting a story or writing an article. The agent sees its own recent mistakes and wins before it starts working.

---

## Entry Template

Each article published by the agent gets one entry using this format:

```
---

## Paper [NNN] — [Title]
**Date:** [publish date]
**Source:** [paper/article cited]
**Category:** [topic category]

### Process Metrics
| Phase | Time (min) | Notes |
|---|---|---|
| Content Scout delivery → Story selected | | |
| Story selected → Draft complete | | |
| Draft complete → Telegram sent | | |
| Telegram sent → David responds | | (wait time — not agent's control) |
| David responds → Published | | |
| **Total cycle time** | | |

### Approval Data
| Field | Value |
|---|---|
| First-pass approval | YES / NO |
| Edit requests | [count] |
| Edit types | [tone / accuracy / length / angle / framing / structure / other] |
| David's specific feedback | "[quote David's edit notes]" |

### David's /feedback Tags (V1.1)
| Field | Value |
|---|---|
| Command received | YES / NO |
| Tags | [e.g., tone, accuracy, length, angle, framing, structure] |
| David's notes | "[raw /feedback message]" |

*If David sends \`/feedback NNN [tags and notes]\` via Telegram after editing, that structured data is captured here. This accelerates pattern detection — the agent doesn't have to infer what David changed, David tells it directly.*

### Audience Metrics (captured 24-48 hours post-publish)
| Metric | Value |
|---|---|
| Page views (trainingrun.ai) | |
| X post impressions | |
| X engagements (likes + reposts + replies) | |
| X bookmarks | |
| X click-through rate | |
| Notable comments/shares | |

*See ENGAGEMENT-LOG.md for full engagement detail. Summary metrics are cross-referenced here.*

### Reasoning Checklist Outcome
| Step | Result |
|---|---|
| Premises stated? | YES / NO |
| Execution trace complete? | YES / NO |
| Claims cited evidence? | YES / NO |
| Uncertainty flagged? | YES / NO — [what was uncertain] |
| Conclusion supported? | YES / NO |

### Agent Reflection
**What went well:**
[what worked in this cycle]

**What I'd do differently:**
[specific improvement for next time]

**Pattern spotted:**
[any emerging trend — topic preference, writing style, timing, etc.]

### Recommendation Status (V1.1)
**Pattern surfaced to David?** YES / NO
**If yes — what was recommended:** [describe]
**David's response:** APPROVED / REJECTED / PENDING
**If approved — STYLE-EVOLUTION rule added:** [rule reference]
```

---

## /feedback Command Reference (V1.1)

David can send structured feedback via Telegram at any point after reviewing an article:

```
/feedback NNN tag1, tag2, tag3 — optional notes
```

**Examples:**
```
/feedback 008 tone, length — too assertive on the policy angle, cut the last two paragraphs
/feedback 009 angle — good writing but wrong angle, should have led with the business impact
/feedback 010 — perfect, no notes (first-pass approval)
```

**Valid tags:** tone, accuracy, length, angle, framing, structure, voice, pacing, sourcing, headline, other

**What happens when /feedback is received:**
1. The agent appends the feedback to this article's entry in LEARNING-LOG.md
2. The tags are stored for pattern analysis (Step 2b of PROCESS.md)
3. If 3+ articles share the same tag, the agent surfaces a recommendation via Telegram
4. The recommendation goes through David's approval gate before becoming a STYLE-EVOLUTION rule

---

## Recommendation Log (V1.1)

Tracks all recommendations the agent has surfaced via Telegram (Step 2b of PROCESS.md) and their outcomes.

```
---

### Recommendation [R-NNN]
**Date:** [date surfaced]
**Pattern:** [describe the pattern with evidence]
**Evidence basis:** Papers [NNN, NNN, NNN]
**Suggested action:** [what the agent proposed]
**David's response:** APPROVED / REJECTED
**If approved — STYLE-EVOLUTION rule:** [rule text]
**If rejected — reason noted:** [why David said no]
```

*No recommendations yet. First recommendation will be surfaced when the agent detects a repeating pattern across 3+ articles.*

---

## Entries

*No entries yet. First agent-assisted article (Paper 008) will be the first entry.*

*Papers 001-007 were produced manually and do not have learning data. See RUN-LOG.md for their basic publish records.*

---

## Monthly Summaries

Monthly summaries are appended here on the 1st of each month (per CADENCE.md).

```
## Monthly Summary — [Month Year]
- Articles published: [count]
- First-pass approval rate: [%]
- Average cycle time: [minutes]
- Top performing article: [title] — [metric]
- Lowest performing article: [title] — [metric]
- Most common edit type: [category]
- Most common /feedback tag: [tag]  ← V1.1
- Edit request trend: [improving / stable / declining]
- Key learning: [one sentence]
- STYLE-EVOLUTION rules added: [count]
- Recommendations surfaced: [count] — approved: [count] / rejected: [count]  ← V1.1
- Process improvements identified: [list]
```

*No monthly summaries yet. First summary will be generated April 1, 2026.*

---

## How This File Is Used

1. **[V1.1] Step 2 of PROCESS.md:** Agent reads the tail of this file (~last 8k tokens) at cycle start — sees its own recent performance before selecting or writing
2. **[V1.1] Step 2b of PROCESS.md:** Agent analyzes this file for repeating patterns, surfaces recommendations to David via Telegram
3. **Step 10 of PROCESS.md:** Agent logs edit types immediately when David requests changes
4. **[V1.1] /feedback command:** David's structured feedback is appended to the relevant entry
5. **Step 14 of PROCESS.md:** Agent logs process metrics and approval data immediately after publish
6. **Step 15 of PROCESS.md:** Agent logs audience metrics 24-48 hours after publish, writes reflection
7. **Sunday weekly review (CADENCE.md):** Agent reads this file, looks for patterns, updates STYLE-EVOLUTION.md
8. **1st of month (CADENCE.md):** Agent writes monthly summary

**The flow:** Raw data lands here → /feedback adds David's direct input → Patterns are spotted → Recommendations go through David's gate → Approved rules move to STYLE-EVOLUTION.md → Rules feed back into the next cycle at Step 2

---

*This file grows with every article. It is the agent's memory. The more it writes, the more it remembers. The more it remembers, the better it gets. V1.1 closes the loop — the agent doesn't just write to this file, it reads it back every morning.*

---

## Paper 010 | March 08, 2026

### Process Metrics
| Phase | Time |
|---|---|
| Story Selection | 0.2 min |
| Article Writing | 0.3 min |
| HTML Staging | 0.1 min |
| Approval Wait | 0.2 min |
| **Total Cycle** | **0.7 min** |

### Approval Data
- **First-pass approval:** YES ✅
- **Edit cycles:** 0
- **David's edit notes:**
  - None — approved on first pass

### Audience Metrics (24-48h post-publish)
- Page views: _pending_
- X impressions: _pending_
- X engagements: _pending_
- Click-through rate: _pending_

### Reasoning Checklist
- Applied: YES
- Outcome: Story selected and article written using 5-filter test

### Agent Reflection
_Reflection will be added after performance data is collected._
