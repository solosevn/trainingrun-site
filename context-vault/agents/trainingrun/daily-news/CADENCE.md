# CADENCE.md — Daily News Agent
## Schedule, Triggers & Rhythms
> **Location:** context-vault/agents/trainingrun/daily-news/CADENCE.md
> **Version:** 1.0 — March 5, 2026
> **Owner:** David Solomon
> **Status:** Active

---

## Daily Cycle

The Daily News Agent runs once per day, every day. The cycle is triggered by Content Scout's morning delivery, not by a fixed clock.

### Timeline (all times CST)

| Time | Event | Agent |
|---|---|---|
| **~5:30am** | Content Scout delivers 3-8 filtered stories to Mission Control | Content Scout |
| **~5:30am** | Content Scout sends Telegram to David: "Mission Control updated" | Content Scout |
| **~5:40am** | Daily News Agent activates — reads Mission Control output | **Daily News Agent** |
| **~5:45am** | Story selection complete — best story chosen using USER.md criteria | **Daily News Agent** |
| **~6:00am** | Article draft complete — staged as `day-NNN.html` | **Daily News Agent** |
| **~6:05am** | Telegram sent to David: "Article ready for review" | **Daily News Agent** |
| **~6:05am–?** | **HUMAN GATE** — Agent waits for David's response | David |
| **On approval** | Agent commits article + updates `news.html` | **Daily News Agent** |
| **On approval** | Agent sends publish confirmation via Telegram | **Daily News Agent** |
| **+24-48 hours** | Agent logs article performance metrics to LEARNING-LOG.md | **Daily News Agent** |

### Trigger: What Starts the Cycle

The agent does NOT run on a cron schedule. It activates when Content Scout's Telegram notification arrives. This ensures:
- The agent never runs before stories are available
- If Content Scout is late (server issue, scrape delay), the agent waits
- If Content Scout doesn't run (holiday, outage), the agent doesn't produce an empty cycle

**Future state:** When the agent directs Content Scout via SCOUT-DIRECTIVE.md, the trigger may shift to a scheduled time with Content Scout as a dependency check.

---

## Weekly Rhythm

| Day | Activity |
|---|---|
| **Sunday** | Weekly learning review — agent reads LEARNING-LOG.md, updates STYLE-EVOLUTION.md with patterns from the past 7 articles |
| **Monday–Saturday** | Normal daily cycle |

### Sunday Learning Review Includes:
- Which topics got the most engagement this week?
- What edits did David request? Any repeated patterns?
- How did first-pass approval rate trend? (target: 90%+)
- Process timing — are we getting faster? Where are the bottlenecks?
- Any new writing rules to add to STYLE-EVOLUTION.md?

---

## Monthly Rhythm

| When | Activity |
|---|---|
| **1st of month** | Monthly performance summary logged to LEARNING-LOG.md |
| **1st of month** | STYLE-EVOLUTION.md gets a full review — retire stale rules, promote proven ones |
| **1st of month** | Agent self-audits: Am I still writing in David's voice? Compare recent articles to USER.md. |

### Monthly Summary Template (logged to LEARNING-LOG.md):
```
## Monthly Summary — [Month Year]
- Articles published: [count]
- First-pass approval rate: [%]
- Average cycle time: [minutes]
- Top performing article: [title] — [metric]
- Most common edit type: [category]
- Key learning: [one sentence]
- STYLE-EVOLUTION rules added: [count]
```

---

## Quarterly Rhythm

| When | Activity |
|---|---|
| **Quarter start** | Agent reviews 3 months of LEARNING-LOG.md data |
| **Quarter start** | Proposes coverage expansion to David (new topics, new sources, Content Scout directives) |
| **Quarter start** | Reviews whether article format, length, or style needs evolution |

---

## Exception Handling

### Content Scout doesn't deliver
If no Mission Control update arrives by 7:00am CST:
- Agent sends Telegram to David: "Content Scout hasn't delivered today. Want me to source a story independently, or skip today?"
- Agent waits for David's response before acting

### David doesn't respond to review request
If no response from David within 4 hours of the review Telegram:
- Agent sends a gentle follow-up: "Just checking — Paper [NNN] is still waiting for your review. No rush."
- Agent does NOT publish. The human gate holds.

### Multiple strong stories in one day
If the agent identifies 2+ stories that all pass the 5-filter test:
- Agent selects the strongest one for the daily article
- Agent notes the other stories in a "runner-up" section in the Telegram message
- David may choose to override the selection or bank the story for tomorrow

### Breaking news / urgent story
If a story is exceptionally timely (major model release, safety incident, policy announcement):
- Agent flags it as "urgent" in the Telegram message
- Agent may propose publishing outside the normal morning window
- David decides timing — agent never pushes early without approval

---

## Dependencies

```
CADENCE.md depends on:
  ├── Content Scout's Telegram notification (trigger)
  ├── David's availability for review (human gate)
  └── LEARNING-LOG.md / STYLE-EVOLUTION.md (weekly/monthly rhythms)

CADENCE.md is referenced by:
  ├── SOUL.md (agent knows its schedule)
  ├── PROCESS.md (workflow timing)
  └── Arena Ops CADENCE.md (master schedule awareness)
```

---

*The Daily News Agent is event-driven, not clock-driven. Content Scout triggers the cycle. David gates the output. The agent fills the space between with autonomous work.*
