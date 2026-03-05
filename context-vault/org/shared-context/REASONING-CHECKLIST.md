# REASONING-CHECKLIST.md
## Agentic Code Reasoning — Mandatory Discipline Layer
*Based on: "Agentic Code Reasoning" — Ugare & Chandra, Meta, 2026 (arXiv: 2603.01896)*

---

## Why This Exists

Standard chain-of-thought lets an agent sound confident while being wrong. This checklist forces the agent to gather evidence BEFORE concluding. It acts as a certificate: every claim must be traceable, every conclusion must be supported, and uncertainty must be admitted rather than papered over.

**This checklist is required any time an agent is:**
- Writing, reviewing, or modifying code
- Making a scoring or ranking decision
- Generating content that will be published or acted on
- Making a prediction or recommendation
- Comparing two or more options and choosing one

---

## THE CHECKLIST

### STEP 1 — PREMISES
*State every fact and assumption you are working from. Be explicit.*

```
PREMISE P1: [What you know for certain — cite the source]
PREMISE P2: [What you are assuming — flag it as an assumption]
PREMISE P3: [Any constraints or dependencies that affect this task]
...
```
> Rule: If you can't state it as a premise, you don't actually know it. Do not proceed until premises are listed.

---

### STEP 2 — EXECUTION TRACE
*Walk through exactly what will happen, step by step, without executing or publishing anything yet.*

```
TRACE T1: [First thing that happens — what triggers it, what it touches]
TRACE T2: [Second thing — what changes, what depends on it]
TRACE T3: [Edge case or failure path — what could go wrong here]
...
```
> Rule: Trace must follow actual logic paths, not assumed behavior. If you don't know what a function/process does, read it first.

---

### STEP 3 — CLAIMS WITH EVIDENCE
*State your conclusions. Each claim must cite a specific premise or trace step as evidence.*

```
CLAIM C1: [Conclusion] — supported by [P# or T#]
CLAIM C2: [Conclusion] — supported by [P# or T#]
```
> Rule: No claim without a citation. "I believe" and "likely" are not evidence.

---

### STEP 4 — UNCERTAINTY CHECK
*If anything is unclear, say so explicitly. Do not guess through it.*

```
UNCERTAIN: [What you cannot verify] — because [specific reason]
ACTION NEEDED: [What information would resolve this]
```
> Rule: Flagging uncertainty is correct behavior. Confident wrong answers are the failure mode this checklist prevents. If uncertain, STOP and surface it to David before proceeding.

---

### STEP 5 — FORMAL CONCLUSION
*Only after completing Steps 1–4, state your final output.*

```
CONCLUSION: [What you are doing / recommending / outputting]
BASIS: [Which claims support this]
HUMAN REVIEW NEEDED: [YES / NO — and why if YES]
```

---

## TASK-SPECIFIC GUIDANCE

### For Code Tasks
Pay special attention to: function shadowing, dependency behavior, edge case inputs. Trace must follow actual execution paths through the codebase, not assumed standard library behavior.

### For Scoring / Ranking Tasks
Premises must cite actual data points. Claims must show the comparison logic explicitly. Tie-breaking rules must be stated as premises, not assumed.

### For Content / Publishing Tasks
Premises include: source material, factual claims, image assets, approval status. Conclusion must include explicit `HUMAN REVIEW NEEDED: YES` until David approves.

### For Predictions / Forecasts
Premises state known signals. Trace walks the inference chain. Conclusion must include a confidence level and what evidence would falsify the prediction.

---

## INTEGRATION REFERENCE

**Add to SOUL.md:**
> I follow the REASONING-CHECKLIST.md for any technical, scoring, content, or decision-making task. I do not output conclusions until I have completed the checklist. If I reach STEP 4 and cannot resolve uncertainty, I surface it to David before proceeding.

**Add to HEARTBEAT.md:**
> - Reasoning discipline: REASONING-CHECKLIST.md active ✓

**Add to CONFIG.md (for agents with high-stakes outputs):**
> All outputs must include the completed checklist as an attached evidence block before delivery.

---

*Last updated: March 2026 | Source paper: arXiv 2603.01896*
