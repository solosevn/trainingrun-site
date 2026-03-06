# Content Scout — TRUTH-FILTER.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Overview

The 4-Layer Truth Filter is Content Scout's core quality engine. Every item scraped from any source passes through all 4 layers before it can appear in a morning briefing. The filter produces a composite **Truth Score (0-100)** that determines ranking and inclusion.

Minimum score to appear in briefing: **50 pts**

---

## Layer 1: Source Credibility (0-40 pts, 40% weight)

Each source has a fixed credibility score based on editorial standards, verification practices, and track record.

| Source | Score | Tier | Rationale |
|--------|-------|------|-----------|
| arXiv | 40 | 1 | Peer-submitted papers, methodology documented |
| Reuters | 40 | 1 | Wire service, fact-checked editorial standards |
| AP News | 40 | 1 | Wire service, fact-checked editorial standards |
| Hugging Face | 38 | 1 | Curated by ML researchers |
| GitHub | 35 | 1 | Verifiable code artifacts |
| MIT Tech Review | 30 | 2 | Established tech journalism |
| TechCrunch | 28 | 2 | Tech journalism, some hype |
| VentureBeat | 26 | 2 | AI coverage, occasional vendor bias |
| Newsletters | 22 | 3 | Curated but editorial bias possible |
| Lobste.rs | 20 | 3 | Small high-quality community |
| Hacker News | 18 | 3 | Community curation, variable quality |
| Reddit | 15 | 3 | Community, high noise, low barrier |
| YouTube | 12 | 3 | Individual creators, variable rigor |

---

## Layer 2: Cross-Confirmation (0-20 pts, 20% weight)

Measures how many independent sources carry the same story. Uses word overlap >50% between titles/summaries to detect related items.

| Cross-Sources | Score | Interpretation |
|---------------|-------|----------------|
| 0 (single source) | 0 pts | Unconfirmed — may be real but no independent validation |
| 1 other source | 8 pts | Some confirmation |
| 2 other sources | 15 pts | Well-confirmed across outlets |
| 3+ other sources | 20 pts | Widely reported, high confidence |

---

## Layer 3: Zero Hype / Substance Analysis (-10 to +20 pts, 20% weight)

### Hype Signals (-8 pts each, max penalty -50)
Patterns that indicate marketing, clickbait, or speculation:
```
you won't believe, shocking, mind-blowing, game changer,
everything changes, is dead, killer, destroy,
agi is here, sentient, conscious, wake up,
revolutionary, paradigm shift, disrupts everything
```
Also penalizes emoji-heavy headlines.

### Substance Signals (+4 pts each, max bonus +50)
Patterns that indicate real, verifiable content:
```
benchmark, evaluation, results, paper, arxiv, research,
dataset, performance, accuracy, leaderboard, methodology,
peer-review, reproducible, open source, weights released,
measured, tested, verified, audit, transparent
```

### Speculation Signals (-4 pts each)
Patterns indicating opinion without data:
```
i think, my prediction, hot take, rumor, supposedly,
unconfirmed, sources say, could potentially, some believe
```

---

## Layer 4: AI Verification (Dual Model)

Two independent AI models assess each headline for truthfulness.

### Model A: Ollama llama3.1:8b (Local, Free)
- Runs locally on David's Mac
- No API cost, no rate limits
- Prompt: Assess if headline is VERIFIED, SUSPICIOUS, or MISLEADING
- Output: JSON with verdict, confidence (1-10), reason

### Model B: xAI Grok-3-Mini (API, Free Tier)
- Cloud API via xAI
- Free tier usage
- Same prompt and output format as Model A

### Decision Matrix

| Model A (Ollama) | Model B (xAI) | Final Verdict | Action |
|-------------------|---------------|---------------|--------|
| VERIFIED | VERIFIED | AI_VERIFIED | Boost confidence, keep |
| VERIFIED | SUSPICIOUS | LIKELY_TRUE | Keep with caution |
| VERIFIED | MISLEADING | WARNING | Keep, tag with warning |
| SUSPICIOUS | VERIFIED | LIKELY_TRUE | Keep with caution |
| SUSPICIOUS | SUSPICIOUS | SUSPICIOUS | Keep, flag as unconfirmed |
| SUSPICIOUS | MISLEADING | WARNING | Keep, tag with warning |
| MISLEADING | VERIFIED | WARNING | Keep, tag with warning |
| MISLEADING | SUSPICIOUS | WARNING | Keep, tag with warning |
| MISLEADING | MISLEADING | **DROP** | Remove from briefing |
| Unavailable | Unavailable | UNVERIFIED | Pass through (no AI check) |

---

## Composite Truth Score Formula

```
Truth Score = (
    Source Credibility [0-40] * 0.40 +
    Cross-Confirmation [0-20] * 0.20 +
    Substance Score [0-20] * 0.20 +
    Relevance Score [0-20] * 0.20
) * Source Weight [0.5-2.0]
```

### Thresholds
| Score Range | Classification | Action |
|-------------|---------------|--------|
| 70-100 | High confidence | Top priority for briefing |
| 50-69 | Moderate confidence | Include if space in top 10 |
| 30-49 | Low confidence | Exclude from briefing |
| 0-29 | Very low / hype | Drop entirely |

---

## TrainingRun Relevance Verticals (0-20 pts)

Items are categorized into 9 TrainingRun content verticals based on keyword matching. Higher-relevance verticals get more points:

| Vertical | Points | Keywords (sample) |
|----------|--------|-------------------|
| TRSBench | 30 | benchmark, leaderboard, evaluation, MMLU, HumanEval |
| TRUscore | 28 | hallucination, bias, safety, truthfulness, factuality |
| TRAgents | 27 | autonomous agent, tool use, function calling, MCP |
| GARI | 26 | AI regulation, China AI, EU AI Act, policy |
| TRScode | 25 | code generation, SWE-bench, Copilot, coding model |
| Open vs Closed | 25 | open source, open weights, proprietary, Llama, Mistral |
| Churn | 24 | AI jobs, workforce, automation, displacement |
| GigaBurn | 23 | GPU, compute, data center, energy, training cost |
| TRFcast | 22 | AGI timeline, forecasting, prediction, capability |

---

*Read by Content Scout via scout_context_loader.py. Defines the complete verification methodology. This is the standard — no item enters the briefing without passing through all 4 layers.*
