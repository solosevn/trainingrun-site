# ENGAGEMENT-LOG.md — Daily News Agent
## Audience Response Data — What Readers Actually Love
> **Location:** context-vault/agents/trainingrun/daily-news/ENGAGEMENT-LOG.md
> **Version:** 1.0 — March 6, 2026
> **Owner:** David Solomon
> **Status:** Active — entries begin with Paper 008
> **Created by:** V3.1 learning loop upgrade. This file did not exist before the March 6, 2026 reflection on agent memory and continuous improvement.

---

## Purpose

This is the Daily News Agent's audience memory. LEARNING-LOG.md captures what the agent did and what David corrected. This file captures what readers actually responded to — the real-world signal that tells the agent whether its work landed.

**Why this file exists separately from LEARNING-LOG.md:** Learning data is about process (cycle time, edits, approval rate). Engagement data is about impact (did readers care?). They feed different decisions — learning data improves how the agent works, engagement data improves what the agent writes about and how it frames it.

**This file is append-only.** Entries are never modified after they're written. The raw data stays raw.

**This file is read at the start of every cycle (Step 2 of PROCESS.md).** The agent loads the last ~10k tokens into its context so it knows what readers responded to before selecting a story or writing an article.

---

## Data Collection — Two Modes

### Mode 1: Manual (Starting Here)
David sends engagement data via Telegram after posting:

```
/engagement NNN platform:metric1 metric2 — optional notes
```

**Examples:**
```
/engagement 008 X:42300 likes:1240 comments:more tech details — readers want deeper dives
/engagement 009 X:8500 likes:210 — low engagement, topic too niche
/engagement 010 X:31000 likes:890 bookmarks:340 — bookmarks high, people saving for reference
```

**What happens when /engagement is received:**
1. Agent appends the data to this article's entry below
2. Data becomes part of the context read at Step 2 of the next cycle
3. Cross-reference summary is added to the article's LEARNING-LOG entry

### Mode 2: Automated (Future)
\`engagement_collector.py\` — a cron job that runs nightly, pulls metrics from X (via API), summarizes notable comments with Grok, and appends to this log automatically. This replaces Mode 1 when David is ready to build it.

**Mode 2 is not built yet.** Start with Mode 1. When the manual process feels stable and the data format is proven, automate it.

---

## Entry Template

Each published article gets one entry. Created at Step 15 of PROCESS.md (24-48 hours post-publish), or earlier if David sends \`/engagement\` via Telegram.

```
---

## Paper [NNN] — [Title]
**Publish date:** [date]
**Category:** [topic category]
**Article format:** [explainer / deep-dive / news brief / comparison / tutorial / opinion]

### Platform Metrics
| Platform | Metric | Value |
|---|---|---|
| trainingrun.ai | Page views | |
| trainingrun.ai | Avg. time on page | |
| X | Impressions | |
| X | Likes | |
| X | Reposts | |
| X | Replies | |
| X | Bookmarks | |
| X | Click-through rate | |
| X | Quote tweets | |
| Reddit | Upvotes | |
| Reddit | Comments | |

### Reader Feedback
**Notable comments:**
- [quote or paraphrase notable reader responses]

**Questions asked by readers:**
- [what did readers want to know more about?]

**Sharing patterns:**
- [who shared it? tech community? general audience? specific influencers?]

### Format Analysis
**Structural elements used:**
- [comparison table? code examples? visual diagram? numbered list? pull quotes?]

**Length:** [word count]
**Images:** [count and type — paper figure? custom graphic? screenshot?]
**Call to action:** [did the article end with a question, a link, a "Part 2 coming"?]

### Engagement Assessment
**Performance vs. average:** ABOVE / AT / BELOW
**What likely drove engagement:** [hypothesis — topic? format? timing? headline?]
**What likely hurt engagement:** [hypothesis — if below average]
**Actionable takeaway:** [one sentence the agent carries forward]
```

---

## Entries

*No entries yet. First agent-assisted article (Paper 008) will be the first entry.*

*Papers 001-007 were produced manually and do not have engagement data. If David wants to backfill key metrics for high-performing early articles, those can be added here to give the agent a baseline.*

---

## Monthly Engagement Summaries

Appended on the 1st of each month (per CADENCE.md), alongside the LEARNING-LOG monthly summary.

```
## Engagement Summary — [Month Year]
- Articles published: [count]
- Total X impressions: [sum]
- Average X impressions per article: [avg]
- Highest performing: Paper [NNN] — [title] — [key metric]
- Lowest performing: Paper [NNN] — [title] — [key metric]
- Top category by engagement: [category]
- Weakest category by engagement: [category]
- Format that performed best: [format type]
- Average article length: [word count]
- Reader questions trend: [what are readers consistently asking for?]
- Key insight: [one sentence]
```

*No monthly summaries yet. First summary will be generated April 1, 2026.*

---

## Pattern Reference

As the agent accumulates data, engagement patterns are documented here before being promoted to STYLE-EVOLUTION.md rules.

**Pattern promotion criteria:** A pattern must appear across 3+ articles before it's surfaced as a recommendation (Step 2b of PROCESS.md). Single-article observations stay here as raw data.

```
### Pattern [E-NNN]
**Observed:** [date first noticed]
**Evidence:** Papers [NNN, NNN, NNN]
**Pattern:** [describe — e.g., "Articles with comparison tables get 2x bookmarks"]
**Confidence:** LOW / MEDIUM / HIGH
**Surfaced to David?** YES / NO
**Promoted to STYLE-EVOLUTION?** YES / NO — [rule reference if yes]
```

*No patterns yet. Patterns will emerge as engagement data accumulates.*

---

## How This File Is Used

1. **Step 2 of PROCESS.md:** Agent reads the tail of this file (~last 10k tokens) at cycle start — sees what readers responded to before selecting or writing
2. **Step 2b of PROCESS.md:** Agent cross-references engagement patterns with learning patterns to surface recommendations
3. **Step 4 of PROCESS.md:** Engagement data informs story selection — the agent weighs recent audience preferences
4. **Step 6 of PROCESS.md:** Engagement data informs writing — the agent applies format and framing lessons from what worked
5. **Step 15 of PROCESS.md:** Agent captures audience metrics and logs them here 24-48 hours post-publish
6. **Telegram /engagement command:** David's manual engagement data is appended to the relevant entry
7. **Sunday weekly review (CADENCE.md):** Agent reads this file alongside LEARNING-LOG for pattern analysis
8. **1st of month (CADENCE.md):** Agent writes monthly engagement summary

**The flow:** Article publishes → 24-48 hours pass → Metrics captured here → Next cycle reads engagement data → Selection and writing adapt → Better articles → Better engagement → The loop compounds

---

*This file is the bridge between what the agent produces and how the world responds. LEARNING-LOG tells the agent what David thinks. ENGAGEMENT-LOG tells the agent what readers think. Both matter. Both feed improvement.*
