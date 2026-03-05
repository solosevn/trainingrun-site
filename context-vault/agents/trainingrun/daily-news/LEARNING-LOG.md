# LEARNING-LOG.md — Daily News Agent
## Performance & Process Data — The Agent's Raw Memory
> **Location:** context-vault/agents/trainingrun/daily-news/LEARNING-LOG.md
> **Version:** 1.0 — March 5, 2026
> **Owner:** David Solomon
> **Status:** Active — entries begin with Paper 008

---

## Purpose

This is the Daily News Agent's raw memory. Every article gets a post-mortem entry that captures what happened, how long it took, what David changed, how the audience responded, and what the agent would do differently. This data feeds STYLE-EVOLUTION.md — where patterns are distilled into actionable rules.

**This file is append-only.** Entries are never modified after they're written. The raw data stays raw.

---

## Entry Template

Each article published by the agent gets one entry using this format:

```
---

## Paper [NNN] — [Title]
**Date:** [publish date]
**Source:** [paper/article cited]

### Process Metrics
| Phase | Time (min) | Notes |
|---|---|---|
| Content Scout delivery -> Story selected | | |
| Story selected -> Draft complete | | |
| Draft complete -> Telegram sent | | |
| Telegram sent -> David responds | | (wait time — not agent's control) |
| David responds -> Published | | |
| **Total cycle time** | | |

### Approval Data
| Field | Value |
|---|---|
| First-pass approval | YES / NO |
| Edit requests | [count] |
| Edit types | [tone / accuracy / length / angle / framing / other] |
| David's specific feedback | "[quote David's edit notes]" |

### Audience Metrics (captured 24-48 hours post-publish)
| Metric | Value |
|---|---|
| Page views (trainingrun.ai) | |
| X post impressions | |
| X engagements (likes + reposts + replies) | |
| X bookmarks | |
| X click-through rate | |
| Notable comments/shares | |

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
```

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
- Edit request trend: [improving / stable / declining]
- Key learning: [one sentence]
- STYLE-EVOLUTION rules added: [count]
- Process improvements identified: [list]
```

*No monthly summaries yet. First summary will be generated April 1, 2026.*

---

## How This File Is Used

1. **Step 14 of PROCESS.md:** Agent logs process metrics and approval data immediately after publish
2. **Step 15 of PROCESS.md:** Agent logs audience metrics 24-48 hours after publish, writes reflection
3. **Sunday weekly review (CADENCE.md):** Agent reads this file, looks for patterns, updates STYLE-EVOLUTION.md
4. **1st of month (CADENCE.md):** Agent writes monthly summary
5. **STYLE-EVOLUTION.md:** Curated patterns are distilled FROM this file INTO that file

**The flow:** Raw data lands here -> Patterns are spotted -> Rules move to STYLE-EVOLUTION.md -> Rules feed back into the next cycle at Step 2

---

*This file grows with every article. It is the agent's memory. The more it writes, the more it remembers. The more it remembers, the better it gets.*
