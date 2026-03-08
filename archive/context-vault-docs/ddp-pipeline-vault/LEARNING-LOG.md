# LEARNING-LOG — DDP Pipeline

> **Format:** Raw memory — scraper failures, data quality issues, methodology changes
> **Updated:** After notable events, scraper issues, or scoring changes
> **Started:** March 6, 2026

---

## Entry Format

```
### YYYY-MM-DD — [Topic]

**What happened:**
**Impact:**
**Action taken:**
**Lesson:**
```

---

## Entries

### 2026-03-06 — Context Vault Established

**What happened:** DDP Pipeline context vault created with Core 7 + SCORING-RULES.md. Pipeline has been running since February 2026 but was undocumented until now.

**Impact:** No operational impact — pipeline continues as-is. Documentation now exists for all 5 DDPs, their sources, weights, and scoring methodologies.

**Action taken:** 8 vault files created. DDP Pipeline classified as sub-agent under TRS Site Manager.

**Lesson:** Document agents early. The pipeline ran for weeks without a vault — this made it harder to track scraper reliability, source changes, and scoring methodology decisions.

---

### 2026-03-03 — TRUscore V1.4 Overhaul

**What happened:** TRUscore upgraded from V1.2 (4 pillars, 7 sources) to V1.4 (5 pillars, 9 sources). "Hallucination" display renamed to "Confabulation." TSArena integrated as Response Quality pillar (10%). Qualification lowered from 5/7 to 3/9.

**Impact:** Major scoring change — all TRUscore rankings reshuffled. Frontend updated to match.

**Action taken:** agent_truscore.py rewritten. WEIGHTS dict updated. Frontend DDP_CONFIG updated. minSources:3 filter added.

**Lesson:** When overhauling a scoring formula, update the Bible, the scraper, and the frontend in the same session. Don't leave any of the three out of sync.

---

### Known Issues (as of March 6, 2026)

- **QUALIFICATION_MIN_SOURCES** for TRUscore set to 3 — should be raised to 4 once all 9 scrapers have consistent coverage
- **KNOWN_VALUES baselines** (FACTS, HalluHard) need periodic verification against new benchmark publications
- **LiveBench link** was dead (HuggingFace Space) — replaced with livebench.ai in V1.4
- **Model name matching** sometimes misses new models with unusual naming conventions — model_names.py needs periodic updates

---
