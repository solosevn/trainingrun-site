# Content Scout — STYLE-EVOLUTION.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Purpose

Curated improvement rules derived from LEARNING-LOG.md data. These are the actionable adjustments Content Scout reads before every briefing to improve story selection quality over time.

Unlike LEARNING-LOG.md (raw data), this file contains **distilled rules with confidence levels**.

---

## Source Weight Adjustments

Applied during ranking (Phase 3, Step 3 of PROCESS.md). All sources still get scraped — weights only affect final ranking.

| Source | Weight | Confidence | Reason | Last Updated |
|--------|--------|------------|--------|-------------|
| arXiv | 1.0x | baseline | Starting weight — no feedback data yet | 2026-03-06 |
| Hugging Face | 1.0x | baseline | Starting weight | 2026-03-06 |
| GitHub Trending | 1.0x | baseline | Starting weight | 2026-03-06 |
| Reddit | 1.0x | baseline | Starting weight | 2026-03-06 |
| Hacker News | 1.0x | baseline | Starting weight | 2026-03-06 |
| Lobste.rs | 1.0x | baseline | Starting weight | 2026-03-06 |
| YouTube | 1.0x | baseline | Starting weight | 2026-03-06 |
| Newsletters | 1.0x | baseline | Starting weight | 2026-03-06 |

### Weight Rules
- Range: 0.5x (heavily deprioritized) to 2.0x (heavily boosted)
- Adjustment step: ±0.1x per feedback event
- Minimum 5 feedback events before adjusting beyond ±0.2x
- Minimum 10 feedback events before adjusting beyond ±0.5x

---

## Story Selection Patterns

*Rules will be added here as patterns emerge from LEARNING-LOG.md data.*

```
### Pattern Template
- **Rule:** [What the scout should do differently]
- **Evidence:** [Data from LEARNING-LOG supporting this]
- **Confidence:** [low/medium/high] — based on [N] feedback events
- **Added:** [date]
```

---

## Anti-Patterns (Things That Don't Work)

*Will be populated as the learning loop identifies stories that get surfaced but never selected.*

---

## Staleness Observations

*Will track whether the staleness filter (>3d deprioritize, >7d drop) is catching old news effectively or needs tuning.*

---

*Read by Content Scout via scout_context_loader.py before every briefing. Source weights are applied during story ranking. Updated by scout_learning_logger.py after each feedback event from the Daily News Agent.*
