# STYLE-EVOLUTION.md — Daily News Agent
## Curated Improvement Rules — The Agent's Playbook
> **Location:** context-vault/agents/trainingrun/daily-news/STYLE-EVOLUTION.md
> **Version:** 1.0 — March 5, 2026
> **Owner:** David Solomon
> **Status:** Active — rules will be added starting with Paper 008

---

## Purpose

This is where the Daily News Agent's learning becomes actionable. LEARNING-LOG.md captures raw data. This file distills that data into rules the agent follows. Every rule here was earned through experience — audience feedback, David's edits, process improvements, and self-reflection.

**The agent reads this file at Step 2 of every daily cycle** — before selecting a story, before writing a word. These rules shape today's work based on yesterday's lessons.

---

## How Rules Get Here

1. Agent publishes an article -> logs data to LEARNING-LOG.md
2. Agent captures audience metrics 24-48 hours later -> updates LEARNING-LOG.md
3. Sunday weekly review -> Agent reads LEARNING-LOG.md, spots patterns
4. Pattern confirmed (not a one-time fluke) -> Agent writes a rule here
5. Monthly review -> Agent audits rules here, retires stale ones, promotes proven ones

**Rules require evidence.** "I think this works" is not a rule. "Articles about [topic] got 3x engagement over 4 consecutive weeks" is a rule.

---

## Rule Categories

### Audience Preferences
*What topics, angles, and formats David's audience actually engages with.*

> No rules yet. First rules will be added after Paper 008+ performance data is collected.

**Example future rules:**
- "Explainer articles outperform technical deep-dives by [X]% on average"
- "AI safety topics get [X]% more engagement than pure capability stories"
- "Articles under 800 words get higher completion rates than 1200+ word articles"

---

### Writing Corrections
*Patterns David has corrected — mistakes the agent should never repeat.*

> No rules yet. First corrections will be logged when David requests edits on agent-produced articles.

**Example future rules:**
- "David corrected jargon usage in Papers 008-010 — eliminated by Paper 012"
- "David prefers 'people' over 'users' when describing who benefits from AI"
- "Opening paragraphs should be 2-3 sentences max — David flagged long intros twice"

---

### Story Selection Patterns
*What makes a "best story" selection — learned from David's overrides and audience response.*

> No rules yet. First patterns will emerge from tracking which stories David approves vs. overrides.

**Example future rules:**
- "Stories with a clear 'this affects your family' angle get selected 80% of the time"
- "David overrides toward safety topics when multiple stories tie on the 5-filter test"
- "Papers from [specific labs] tend to produce stronger articles"

---

### Process Improvements
*How to get faster, more efficient, and more reliable.*

> No rules yet. First improvements will be identified from cycle time tracking.

**Example future rules:**
- "Staging time dropped from 12 min to 4 min after adopting [specific approach]"
- "Writing the citation block first (before the article body) reduces revision cycles"
- "Reading the full paper abstract before skimming the body improves story selection accuracy"

---

### Voice Calibration
*Fine-tuning how the agent writes in David's voice — learned from corrections and approvals.*

> No rules yet. Voice calibration will begin with the first agent-written article.

**Example future rules:**
- "David's voice is warmer than my default — increase personal anecdote frequency"
- "Use 'I found' and 'I learned' more often — David writes in first person"
- "Avoid academic hedging ('it appears that', 'one might argue') — David is direct"

---

## Retired Rules

Rules that were once active but are no longer relevant (audience shifted, process changed, etc.):

> No retired rules yet.

**When to retire a rule:**
- The pattern no longer holds (3+ consecutive data points contradict it)
- The process has changed and the rule no longer applies
- David explicitly says "stop doing this"

Retired rules stay in this section with a note explaining why they were retired. We don't delete history — we learn from it.

---

## Rule Confidence Levels

Each rule should include a confidence tag:

| Tag | Meaning | Minimum Evidence |
|---|---|---|
| **STRONG** | Proven pattern, consistently supported | 4+ data points over 2+ weeks |
| **EMERGING** | Pattern spotted, needs more data | 2-3 data points |
| **HYPOTHESIS** | Suspected pattern, untested | 1 data point or intuition from David's feedback |

Rules start as HYPOTHESIS, get promoted to EMERGING with evidence, and reach STRONG when consistently confirmed. Only STRONG rules should significantly influence story selection or writing approach.

---

## Self-Study Directive

The agent doesn't just learn from its own articles. It also studies:
- What good AI journalism looks like (format, tone, engagement patterns)
- Who consumes AI news and why (audience demographics, reading habits)
- What competitor publications do well (not to copy — to understand what works)
- David's past articles (Papers 001-007) as a voice baseline

Insights from self-study follow the same rule format and require the same evidence standards.

---

## File Dependencies

```
STYLE-EVOLUTION.md is fed by:
  |- LEARNING-LOG.md (raw data -> distilled into rules here)

STYLE-EVOLUTION.md is read by:
  |- PROCESS.md Step 2 (agent reads this before every cycle)
  |- SOUL.md (references learning mandate)

STYLE-EVOLUTION.md is reviewed:
  |- Weekly (Sunday) — new rules added from LEARNING-LOG.md patterns
  |- Monthly (1st) — full audit, retire stale rules, promote proven ones
```

---

*This file starts empty and grows smart. Every rule here was earned, not assumed. The agent reads it every morning and becomes a little better than it was yesterday.*
