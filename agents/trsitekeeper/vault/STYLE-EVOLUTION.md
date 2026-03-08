# STYLE-EVOLUTION â TRS Site Manager (TRSitekeeper)

> **Format:** Curated rules distilled from LEARNING-LOG and operational experience
> **Confidence levels:** Hypothesis â Emerging â Strong â Retired
> **Started:** March 6, 2026

---

## Active Rules

### Strong Confidence

| # | Rule | Source | Date |
|---|---|---|---|
| S1 | Always `backup_file()` before ANY edit â no exceptions, even for "trivial" changes | brain.md v2.0 | 2026-02 |
| S2 | Always `git pull --rebase` before starting any work â prevents merge conflicts on GitHub Pages | brain.md v2.0 | 2026-02 |
| S3 | Never use `git add -A` â always add specific files to avoid committing debug artifacts or temp files | brain.md v2.0 | 2026-02 |
| S4 | Edit one file at a time, commit after each â isolates changes and makes rollback possible | brain.md v2.0 | 2026-02 |
| S5 | Brand colors are sacred: cyan `#00d4ff`, red `#ff3333`, background `#0a0f1a` â never deviate | brain.md design rules | 2026-02 |
| S6 | Never add external font CDN links â system fonts only, keeps load time fast | brain.md design rules | 2026-02 |
| S7 | DDP JSON files must never be pushed empty or corrupt â verify content before committing | DDP Pipeline operations | 2026-02 |
| S8 | When fixing alignment, check the parent flex/grid container first â 90% of alignment issues are parent-level, not child-level | Common fix patterns | 2026-02 |

### Emerging Confidence

| # | Rule | Source | Date |
|---|---|---|---|
| E1 | Audit high-traffic pages (index.html, tsarena.html) first â visitors hit these most | Audit framework design | 2026-03 |
| E2 | Batch non-urgent findings into daily reports â don't flood David with minor issues throughout the day | Communication design | 2026-03 |
| E3 | When David sends an image, identify the page before the element â context narrows the search | Reactive fix design | 2026-03 |
| E4 | Check model name rendering after every DDP update â new models with unusual names cause display issues | model_names.py experience | 2026-02 |

### Hypothesis

| # | Rule | Source | Date |
|---|---|---|---|
| H1 | Consider tracking "time since last human-reported issue" as a site health metric â longer gaps = better autonomous coverage | Observation | 2026-03-06 |
| H2 | Consider a "visitor perspective walkthrough" on Saturdays â browse the entire site as if seeing it for the first time | Audit design | 2026-03-06 |
| H3 | Consider lighthouse/performance audits as part of weekly cycle â page load speed affects user trust | Observation | 2026-03-06 |

---

## Retired Rules

*(None yet â agent is still young)*

---

## Design Rules (From brain.md â Never Break)

1. Dark background `#0a0f1a` â never use white or light backgrounds
2. Cyan `#00d4ff` for primary accents â links, highlights, borders
3. Red `#ff3333` reserved for TRAgents branding and warning states
4. System font stack â no external font imports
5. Data-dense layouts â maximize information per viewport
6. Terminal-inspired aesthetic â monospace for data, clean sans-serif for prose
7. No decorative elements that don't serve a function
8. Consistent spacing â use the existing spacing scale, don't invent new values

---

## Content Rules (From David's Philosophy â Never Break)

1. Truth first â no clickbait, no misleading data presentations, just facts
2. Always credit the source â every benchmark, every data point traces back to its origin
3. Layman accessibility â if a regular person can't understand what a page is showing them, simplify it
4. Every page should answer: "What problem is this solving for the person reading it?"
5. David's name is on this site â quality standard is personal, not corporate
