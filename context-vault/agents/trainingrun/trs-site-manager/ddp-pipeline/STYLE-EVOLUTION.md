# STYLE-EVOLUTION — DDP Pipeline

> **Format:** Curated rules distilled from LEARNING-LOG
> **Confidence levels:** Hypothesis → Emerging → Strong → Retired
> **Started:** March 6, 2026

---

## Active Rules

### Strong Confidence

| # | Rule | Source | Date |
|---|---|---|---|
| S1 | Always use Option A (renormalize weights) when sources can be null — prevents penalizing models for missing data | TRUscore V1.4 overhaul | 2026-03-03 |
| S2 | Invert hallucination/Brier metrics before scoring — all pillars must follow "higher = better" direction | TRUscore V1.4, TRFcast V1.0 | 2026-02 |
| S3 | Set minimum qualification threshold per DDP — never display models with insufficient data | TRUscore minSources:3 | 2026-03-03 |
| S4 | Use Playwright (not requests) for JavaScript-heavy sources — many benchmarks render data client-side | Early scraper failures | 2026-02 |
| S5 | Strip API version suffixes from model names before matching — `-2024-08-06` and `-instruct` cause false mismatches | model_names.py | 2026-02 |

### Emerging Confidence

| # | Rule | Source | Date |
|---|---|---|---|
| E1 | HuggingFace Spaces need 15s+ wait time and iframe detection — standard 5s is insufficient | TRUscore Vectara scraper | 2026-02 |
| E2 | When a source stops updating for 7+ days, flag it — may indicate benchmark retirement or URL change | Monitoring pattern | 2026-03 |
| E3 | Run dry-run before any scraper code change goes live — catch parsing errors before they corrupt data | Development practice | 2026-02 |

### Hypothesis

| # | Rule | Source | Date |
|---|---|---|---|
| H1 | Consider adding scraper version tracking to output JSON — would help debug when scores shift after code changes | Observation | 2026-03-06 |
| H2 | Consider logging raw scraped values alongside normalized scores — aids in auditing and debugging | Observation | 2026-03-06 |

---

## Retired Rules

*(None yet — pipeline is still young)*

---

## Bible Version History

| DDP | Current | Previous | Change Date | Key Changes |
|---|---|---|---|---|
| TRSbench | V2.5 | V2.0 | Feb 2026 | 18 sources across 7 pillars |
| TRUscore | V1.4 | V1.2 | Mar 3, 2026 | 5 pillars (was 4), 9 sources (was 7), +TSArena pillar |
| TRScode | V1.0 | — | Feb 14, 2026 | Initial release, 8 sources |
| TRFcast | V1.0 | — | Feb 21, 2026 | Initial release, 4 platforms / 9 sub-metrics |
| TRAgents | V1.0 | — | Feb 21, 2026 | Initial release, 6 pillars / 22+ sources |
