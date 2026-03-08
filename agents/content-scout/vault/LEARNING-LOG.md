# Content Scout — LEARNING-LOG.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Purpose

Raw learning data. Every morning briefing result and every feedback event from the Daily News Agent gets logged here. This is the unprocessed data that feeds STYLE-EVOLUTION.md (curated rules).

---

## Section 1: Briefing Results

Appended by `scout_learning_logger.log_briefing_result()` after each morning brief.

```
### Brief [YYYY-MM-DD]
- **Top 10 stories surfaced:**
  1. [title] | Source: [source] | Truth Score: [score] | AI Verdict: [verdict] | Category: [category]
  2. ...
- **Truth score range:** [min]-[max]
- **Categories represented:** [list]
- **Sources represented:** [list]
- **Items dropped by AI verification:** [count]
- **Ollama status:** [available/unavailable]
- **xAI status:** [available/unavailable]
```

---

## Section 2: Daily News Agent Feedback

Appended by `scout_learning_logger.log_selection_feedback()` when feedback is received.

```
### Feedback [YYYY-MM-DD] — Paper [NNN]
- **Selected story:** [title]
- **Selected source:** [source]
- **Selected truth score:** [score]
- **Selected category:** [category]
- **Rejected candidates:** [count]
- **Top 3 rejected:**
  1. [title] | Source: [source] | Score: [score]
  2. ...
  3. ...
- **Selection pattern:** [Was it the #1 ranked story? If not, what rank was it?]
```

---

## Section 3: Source Performance Tracking

Updated by `scout_learning_logger.update_source_weights()` after each feedback event.

```
### Source Stats [YYYY-MM-DD]
| Source | Stories Surfaced (30d) | Stories Selected (30d) | Selection Rate | Current Weight |
|--------|----------------------|----------------------|----------------|----------------|
| arXiv | [count] | [count] | [%] | [weight]x |
| Hugging Face | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
```

---

## Log Entries

*Entries will be appended below this line by scout_learning_logger.py*

---
