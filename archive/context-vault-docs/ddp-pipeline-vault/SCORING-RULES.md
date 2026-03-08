# SCORING-RULES — DDP Pipeline

> **Version:** 1.0 — March 6, 2026
> **Purpose:** How scores are calculated per DDP — formulas, weights, sources, qualification rules

---

## 1. TRSbench (Overall Model Quality)

**Bible:** TRSbench V2.5 (Feb 2026)
**Script:** `agent_trs.py` → `trs-data.json`
**Sources:** 18 across 7 pillars
**Qualification:** 4+ pillars with non-null scores

| Pillar | Weight | Sources |
|---|---|---|
| Safety | 21% | HELM Safety, AIR-Bench |
| Reasoning | 20% | ARC-AGI-2, LiveBench, HELM Capabilities |
| Coding | 20% | SWE-bench, EvalPlus, LiveCodeBench, SWE-rebench |
| Human Preference | 18% | Arena Overall, Arena Text, AlpacaEval |
| Knowledge | 8% | MMLU-Pro, HELM MMLU, SimpleQA |
| Efficiency | 7% | Artificial Analysis, PricePerToken |
| Usage | 6% | OpenRouter Rankings |

**Scoring method:** Within each pillar, each source is normalized to 0-100, then averaged. Composite = weighted average across pillars, renormalized to 1.0 using available weights only.

---

## 2. TRUscore (Truth & Neutrality)

**Bible:** TRUscore V1.4 (March 2026)
**Script:** `agent_truscore.py` → `truscore-data.json`
**Sources:** 9 sub-metrics across 5 pillars
**Qualification:** 3+ of 9 sub-metrics with non-null scores (raise to 4 when coverage improves)

| Pillar | Weight | Sub-metrics | Source |
|---|---|---|---|
| Truthfulness | 35% | SimpleQA Correct % (0.13) | llm-stats.com |
| | | FACTS Benchmark Avg (0.12) | kaggle/google/facts |
| | | TruthfulQA MC Score (0.10) | llm-stats.com |
| Hallucination | 20% | HalluHard Rate - INVERTED (0.12) | halluhard.com |
| | | Vectara Hallucination - INVERTED (0.08) | huggingface.co |
| Reasoning | 20% | HLE Accuracy (0.10) | lastexam.ai |
| | | LiveBench Global Avg (0.10) | livebench.ai |
| Neutrality | 15% | Anthropic Paired Prompts (0.15) | anthropic.com |
| Response Quality | 10% | TSArena Human Preference (0.10) | trainingrun.ai/tsarena |

**Scoring method:** Option A - null sources excluded, weights renormalized to 1.0. Hallucination metrics inverted (lower rate = higher score).

**Weights validation:** `assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9`

**Pillar groupings:**
```python
PILLAR_SOURCES = {
    "truthfulness":     ["truthfulness_simpleqa", "truthfulness_facts", "truthfulness_truthfulqa"],
    "hallucination":    ["hallucination_halluhard", "hallucination_vectara"],
    "reasoning":        ["reasoning_hle", "reasoning_livebench"],
    "neutrality":       ["neutrality_anthropic"],
    "response_quality": ["quality_tsarena"],
}
```

---

## 3. TRScode (Coding Ability)

**Bible:** TRScode V1.0 (Feb 14, 2026)
**Script:** `agent_trscode.py` → `trscode-data.json`
**Sources:** 8
**Qualification:** 2+ sources with non-null scores

| # | Source | URL | Weight |
|---|---|---|---|
| 1 | SWE-bench Verified | swebench.com | 17% |
| 2 | SWE-rebench | swe-rebench.com | 13% |
| 3 | LiveCodeBench | livecodebench.github.io | 15% |
| 4 | BigCodeBench | bigcode-bench.github.io | 10% |
| 5 | Terminal-Bench Hard | tbench.ai | 12% |
| 6 | SWE-bench Pro | scale.com/leaderboard | 8% |
| 7 | SciCode | scicode-bench.github.io | 15% |
| 8 | Chatbot Arena Code | lmarena.ai (code filter) | 10% |

**Scoring method:** Option B - null sub-metrics contribute 0, not normalized away.

---

## 4. TRFcast (Forecasting & Financial Reasoning)

**Bible:** TRFcast V1.0 (Feb 21, 2026)
**Script:** `agent_trfcast.py` → `trf-data.json`
**Sources:** 4 platforms / 9 sub-metrics
**Qualification:** 3+ of 5 pillars with non-null scores

| # | Platform | URL | Weight | Sub-metrics |
|---|---|---|---|---|
| 1 | ForecastBench | forecastbench.org | 20% | Baseline Brier (INVERTED), Tournament Brier (INVERTED) |
| 2 | Rallies.ai | rallies.ai | 20% | Portfolio Returns, Win Rate |
| 3 | Alpha Arena | nof1.ai | 15% | Returns, Sharpe Ratio |
| 4 | FinanceArena | financearena.ai | 15% | QA Accuracy, ELO Rating |

**Additional pillars:**
- Calibration on ForecastBench Baseline (20%)
- Financial Reasoning QA/Compare (15%)
- Market Intelligence Sharpe/Winrate (10%)

**Note:** Brier scores INVERTED (lower Brier = better calibration = higher score).

---

## 5. TRAgents (Autonomous Agent Capabilities)

**Bible:** TRAgents V1.0 (Feb 21, 2026)
**Script:** `agent_tragents.py` → `tragent-data.json`
**Sources:** 22+ aggregated across 6 pillars
**Qualification:** 3+ of 6 pillars with non-null scores

| Pillar | Weight | Sources |
|---|---|---|
| Task Completion | 25% | SWE-bench Verified, GAIA, OSWorld, tau-bench |
| Cost Efficiency | 20% | ARC-AGI-2, Artificial Analysis |
| Tool Reliability | 20% | SEAL Agentic Tool Use, Galileo Agent Leaderboard |
| Safety & Security | 15% | SEAL MASK |
| Accessibility | 10% | Ollama library |
| Multi-Model Support | 10% | OpenRouter rankings |

**Scoring method:** Option A - proportional normalization over 6 pillars.

---

## Universal Rules (All DDPs)

1. **Normalization:** All raw scores normalized to 0-100 scale before weighting
2. **Inversion:** Metrics where lower is better (hallucination rates, Brier scores) are inverted: `score = 100 - raw_rate`
3. **Qualification:** Every DDP has a minimum source/pillar count - models below threshold are excluded from leaderboard
4. **Model matching:** Fuzzy name matching via `model_names.py` (exact → substring → difflib at 0.82 threshold)
5. **Null handling:** Varies by DDP - Option A (renormalize) or Option B (zero-fill) as documented above
6. **Weight validation:** All weight dictionaries must sum to 1.0 (asserted in code)
7. **Git push:** Each agent independently commits and pushes its data file after scoring
