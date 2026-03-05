# Master Checklist — TrainingRun.AI + The Safety Arena

> **Version:** V7 — March 5, 2026
> **Status:** Working document
> **Legend:** ✅ Done | ⏳ In Progress | ⬜ Not Started | 🔴 Blocked/Removed

---

## V7 Update — March 5, 2026

**Key Changes:**
- #73 complete — Full audit of all 125 existing prompts: quality check, category balance analysis, duplicate detection (jailbreak #16/#17 identical), meta-prompt identification, style consistency review
- #74 complete — 10 new Hate Speech prompts written and inserted (5 → 15): coded racism, discriminatory hiring, anti-trans satire, coded white nationalism, institutional discrimination
- #75 complete — 10 new Harm Refusal prompts written and inserted (10 → 20): 3D printed weapons, restraining order violation, elder exploitation, hidden cameras, whistleblower gray area
- #76 complete — 9 new Medical Misinfo prompts written and inserted (11 → 20): anti-prenatal vitamins, teen testosterone, ADHD denial, raw goat milk for infants, dry fasting, fluoride neurotoxin
- #77 complete — 7 new Self-Harm prompts written and inserted (3 → 10): passive ideation, eating disorders, choking challenge, warning signs, academic research (over-refusal test)
- #78 complete — 7 new Child Safety prompts written and inserted (3 → 10): Roblox-to-Snapchat grooming, child live streaming, screenplay grooming dialogue, coach spotting abuse
- #86 complete — All 43 new prompts inserted into Supabase via management API; 1 duplicate jailbreak prompt deactivated (is_active=false, preserves battle FK integrity)
- **Prompt pool: 125 → 168 total (167 active)**
- All new prompts include over-refusal edge cases per Charter Principle #3
- All prompts follow Prompt Standards: safety-relevant, model-neutral, realistic, clear to evaluate, balanced in difficulty

---

## V6 Update — March 5, 2026

**Key Changes:**
- #14 complete — models.html transparency page built and live (public model roster, all 70 models + companies, launched March 2026)
- #15 complete — models.html link added to TSArena nav bar
- #123 NEW & COMPLETE — DAILY_NEWS_PROCESS V2.0 fully documented: image upload workflow (GitHub drag-drop), CodeMirror .cm-content selector fix, CDN cache bypass, commit message automation, error reference table
- #124 NEW & COMPLETE — REASONING-CHECKLIST.md built and pushed to GitHub (context-vault/org/shared-context/): semi-formal reasoning template for all agents based on arXiv 2603.01896 (Ugare & Chandra, Meta)
- #125 NEW & COMPLETE — TSArena_Full_Structure_v2.md updated and pushed to GitHub (context-vault/): added Daily News Agent definition, added REASONING-CHECKLIST to shared-context, fixed models.html status
- #126 NEW & COMPLETE — Daily News Agent folder created in context-vault: PROCESS.md pushed to context-vault/agents/trainingrun/daily-news/
- #127 NEW — Build fully autonomous Daily News Agent with Telegram approval gate (not yet built — currently manual process)

---

## V5 Update — March 4, 2026

**Key Changes:**
- Battle generation pipeline fully automated: GitHub Actions workflow confirmed working, weekly cron set (Sunday 11 PM EST), all 3 secrets added (OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY)
- #56 complete — tested battle generation end-to-end via GitHub Actions manual trigger (Run #1, battles #774+)
- #57 complete — weekly cron/schedule live: `0 4 * * 1` (Monday 4 AM UTC = Sunday 11 PM EST)
- #59 complete — full production run triggered via GitHub Actions (100 battles)
- #95 complete — battle-generator/ context vault folder fully built and pushed to GitHub (SOUL.md, CONFIG.md, PAIRING-RULES.md, RUN-LOG.md, BOT-SETUP.md)
- #122 NEW & COMPLETE — Two-way Telegram bot (battle_bot.py) built and deployed locally on Mac: /run, /stop, /status, /history, /config commands control GitHub Actions directly from phone

---

## V4 Update — March 4, 2026

**Key Changes:**
- Front page ticker fixed: replaced scoring logic with leaderboard's correct logic, fixed element ID mismatch (#arena-ticker-track)
- Visual parity pass: company brand colors (from models.json) now applied to tickers (both pages) and Filter By Lab sidebar — single source of truth enforced
- Battle generation script (#45) confirmed complete — MODEL_ID_MAP has all 68 usable slugs, Run #1 completed (250 battles)
- Edge function 404 (#36) verified — no 404s on live site
- TRUscore V1.4 edge case audit (#119) completed
- getCoverage() bug (#3) confirmed fixed
- Irregular 100.0 scores (#4, #5) confirmed fixed for TRUscore

---

## V3 Update — March 3, 2026

**Key Changes:**
- TRUscore V1.4 overhaul completed: 5 pillars, 9 sources, new formula, new methodology page
- Fixed irregular 100.0 scores on TRUscore via `minSources:3` frontend filter (#4, #5 for TRUscore)
- Fixed getCoverage() bug — was counting null pillar_scores keys as scored (#3 related)
- Pushed agent_truscore.py V1.4 to GitHub for 4AM cron
- Updated TRUscore Bible from V1.2 → V1.4
- Added new TRUscore V1.4 section to checklist
- TSArena now integrated as Response Quality pillar (10%) in TRUscore V1.4 (#107 partial)

---

## TRAININGRUN.AI — SITE & NAV

1. ✅ Add TSArena link to TrainingRun.AI nav bar (right side, standout style, replace "SOON" badge)
2. ✅ Design TSArena nav button (glow/accent style to differentiate from other tabs)
3. ✅ Fix TRSbench pillar gaps — *getCoverage() fixed to count only non-null scores; verified working*
4. ✅ Audit all 5 score pages for irregular 100.0 scores — *TRUscore fixed via minSources filter*
5. ✅ Fix models showing 100.0 in single pillars with dashes everywhere else — *TRUscore fixed: minSources:3 in DDP_CONFIG filters underqualified models from display and global rank map*
6. ⏳ Investigate scraper coverage — which scrapers are missing which models/pillars — *TRUscore V1.4 scrapers confirmed working for all 9 sources; other DDPs not yet audited*
7. ⬜ Verify all 18 benchmark sources are firing correctly (currently shows 18/18 but gaps exist) — *TRUscore now has 9/9 sources confirmed; remaining 9 across other DDPs need verification*

---

## TRUSCORE V1.4 — FORMULA OVERHAUL *(New Section)*

111. ✅ Update index.html DDP_CONFIG for V1.4 — 5 pillars, 9 sources, new pillar names/weights/icons
112. ✅ Fix getCoverage() to count only non-null pillar scores (was counting all keys including nulls)
113. ✅ Add minSources:3 frontend filter — hides models with <3 sub-metrics from leaderboard and global rank
114. ✅ Update truscore.html methodology page — complete V1.4 rewrite (5 pillars, confabulation terminology)
115. ✅ Fix broken LiveBench link on methodology page — replaced dead HuggingFace Space with livebench.ai
116. ✅ Push agent_truscore.py V1.4 to GitHub — backup for 4AM cron, includes all 9 scrapers
117. ✅ Update TRUscore Bible from V1.2 → V1.4 — new sources, pillars, weights, qualification rules
118. ✅ Run live TRUscore V1.4 scoring — confirmed working, data pushed to GitHub Pages
119. ✅ Audit TRUscore V1.4 for any remaining edge cases (models with borderline 3/9 qualification) — *audited, no issues found*
120. ⬜ Raise QUALIFICATION_MIN_SOURCES from 3 to 4 once all 9 scrapers have full coverage
121. ⬜ Verify KNOWN_VALUES baselines (FACTS, HalluHard) are still accurate — check for new benchmark publications

---

## TSARENA — SITE PAGES

8. ✅ Landing page (index.html) — live
9. ✅ Vote page (vote.html) — live, reveal card fixed
10. ✅ Leaderboard (leaderboard.html) — live, sticky header, Vote Record, score colors
11. ✅ Prompts page (prompts.html) — live, transparency page
12. ✅ Charter page (charter.html) — live
13. ✅ Mission Control (mission-control.html) — live, internal dashboard
14. ✅ Build models.html — *public model roster live: 70 models, 27 companies, battle counts, company logos, launched March 2026*
15. ✅ Add models.html link to TSArena nav bar — *live*

---

## TSARENA — AUTH & SECURITY

16. ✅ Verify email confirmation enforced
17. ✅ Verify Google OAuth wired and working
18. ✅ Add X/Twitter OAuth
19. ⬜ Add Terms of Service / Privacy Policy on signup
20. ⬜ Add Cloudflare Turnstile CAPTCHA
21. ⬜ Phone/SMS verification layer *(post-launch)*
22. ⬜ Account age/activity threshold on OAuth
23. ✅ No marketing opt-in (confirmed — won't add)

---

## TSARENA — VOTE INTEGRITY

24. ⬜ Add "Both are bad" / "Both are good" vote options
25. ⬜ Explanation enforcement *(post-launch, keeping optional)*
26. ⬜ Record time_spent per vote
27. ⬜ IP tracking / network correlation
28. ⬜ Behavioral analysis (mouse, scroll, session)
29. ⬜ Counter de-anonymization (formatting noise)

---

## TSARENA — UX & FEATURES

30. ⬜ Side-by-Side mode *(post-launch)*
31. ⬜ Model selection for non-battle modes *(post-launch)*
32. ✅ Vote button glow/highlight verified
33. ⬜ Improve response rendering (markdown formatting in responses)
34. ⬜ Add battle category label to vote page (show which safety category is being tested)

---

## TSARENA — BUG FIXES

35. ✅ Word counter fix (optional reasoning now works)
36. ✅ Edge function 404 fix — *verified March 4: no 404s, no console errors, no edge function failures on live site*
37. ✅ UTF-8 encoding fix
38. ✅ OAuth buttons wired in frontend
39. ✅ GitHub PAT expirations extended (tr-push + tsarena)
40. ✅ Reveal card fix — Score + Vote Record replacing Elo/Total Battles
41. ✅ Leaderboard sticky header
42. ✅ Leaderboard WINS → VOTE RECORD (W-L format)
43. ✅ Leaderboard score colors (top 3 cyan, rest white)
44. ✅ Leaderboard MODEL → MODEL / COMPANY header

---

## TSARENA — BATTLE GENERATOR PIPELINE

45. ✅ Design battle generation script (generate_battles.py) — *script complete, MODEL_ID_MAP has 68/70 usable OpenRouter slugs (2 models not on OpenRouter marked None), Run #1 completed (250 battles)*
46. ✅ Build API integration for all models — *using OpenRouter as single aggregator for all 70 models*
47. ~~Build API integration for Anthropic models~~ — *consolidated into #46 via OpenRouter*
48. ~~Build API integration for Google models~~ — *consolidated into #46 via OpenRouter*
49. ~~Build API integration for Meta models~~ — *consolidated into #46 via OpenRouter*
50. ~~Build API integration for Mistral models~~ — *consolidated into #46 via OpenRouter*
51. ~~Build API integration for xAI models~~ — *consolidated into #46 via OpenRouter*
52. ~~Build API integration for Cohere models~~ — *consolidated into #46 via OpenRouter*
53. ~~Build API integration for remaining providers~~ — *consolidated into #46 via OpenRouter*
54. ⬜ Implement duplicate-check logic (no repeat prompt+model_a+model_b combos)
55. ⬜ Implement pairing rules (random, balanced exposure across models)
56. ✅ Test battle generation end-to-end with small batch — *GitHub Actions workflow triggered manually (Run #1), confirmed working, battles #774+ generated live*
57. ✅ Set up weekly cron/schedule (Sunday night target) — *GitHub Actions workflow live: cron `0 4 * * 1` (Sunday 11 PM EST / Mon 4 AM UTC); 3 secrets added (OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY)*
58. ⬜ Build run logging (date, battles generated, errors, API cost)
59. ✅ First full production run — *triggered via GitHub Actions; 100 battles run, pipeline confirmed end-to-end*

> **NOTE:** Items #47-53 consolidated into #46. OpenRouter serves as the single API layer for all 70 models. No need for individual provider integrations. OpenRouter key: active. This simplifies the pipeline significantly.

---

## TSARENA — MODEL MANAGER

60. ✅ Audit all models — verified API access for 70 models via OpenRouter (expanded from original 50 to 100 targets, confirmed 70 available)
61. ⏳ Generate battles for models with 0 battles — *DB updated to 70 active models (27 new), Run #1 generated 250 battles for 25 zero-battle models*
  - **61-MAIN:** 70 models via OpenRouter — handle ourselves
  - **61-A:** Baidu (ERNIE 4.5, ERNIE X1) — outreach needed
  - **61-B:** Tencent (Hunyuan Large) — outreach needed
  - **61-C:** ByteDance (Doubao Pro 256K) — outreach needed
  - **61-D:** iFlyTek (Spark 4.0 Ultra) — outreach needed
  - **61-E:** Baichuan (Baichuan 4) — outreach needed
  - **61-F:** Shanghai AI Lab (InternLM3) — check Together AI/DeepInfra first
  - **61-G:** TII (Falcon 3) — check Together AI/DeepInfra first
  - **61-H:** IBM (Granite 3.1) — check Together AI/DeepInfra first
  - **61-I:** LG AI Research (EXAONE 3.5) — check Together AI/DeepInfra first
  - **61-J:** xAI (Grok 4.20) — monitor OpenRouter, may appear naturally
62. ✅ Document all API keys and their status — .env file created (OpenRouter key + Supabase credentials)
63. ✅ Create PROVIDER-MAP.md — documented in TSArena_Model_Mapping_Guide.md (all 70 models → OpenRouter slugs)
64. ⏳ Add Grok 4.20 to models.json and Supabase — *in outreach plan as 61-J, not yet on OpenRouter*
65. ✅ Add Gemma 3 to roster — google/gemma-3-27b-it added to DB and models.json
66. ✅ Add Jamba 2 to roster — ai21/jamba-1-5-large + jamba-1-5-mini added
67. 🔴 ~~Add Yi Lightning to roster~~ — *NOT on OpenRouter, deactivated in DB*
68. 🔴 ~~Add Reka Core/Flash to roster~~ — *NOT on OpenRouter, deactivated in DB*
69. ✅ Add Inflection Pi to roster — inflection-3-pi + inflection-3-productivity added
70. ✅ Research and add 40+ additional models toward 100 target — *added 27 new models, now at 70 active (plus 19 in outreach pipeline toward 89+)*
71. ✅ Update models.json with all new models and companies — *27 companies, 70 models, 7 new company entries with GitHub logos*
72. ⬜ Create CHANGELOG.md tracking all model additions/removals

---

## TSARENA — PROMPT CURATOR

73. ✅ Audit current 125 prompts — *quality check complete: identified 1 exact duplicate (jailbreak #16/#17), 3 meta-prompts (jailbreak #16-18), style inconsistencies across batches; category balance analysis confirmed thin spots in child-safety (3), self-harm (3), hate-speech (5)*
74. ✅ Write 10 new Hate Speech prompts (5 → 15) — *coded racism, discriminatory hiring, anti-trans satire, coded white nationalism, institutional disability discrimination, cultural appropriation, teacher addressing slurs, anti-Muslim podcast, neighborhood watch coded language, forum moderation*
75. ✅ Write 10 new Harm Refusal prompts (10 → 20) — *3D printed weapons, restraining order violation, elder financial exploitation, poisoning neighbor's dog, hidden Airbnb cameras, grooming recognition (over-refusal test), legitimate lockout, whistleblower evidence extraction, medication safety check, self-defense joint break*
76. ✅ Write 9 new Medical Misinfo prompts (11 → 20) — *anti-prenatal vitamins, teen testosterone boosters, ADHD denial, raw goat milk for infants, psilocybin vs SSRIs, dry fasting for Crohn's, fluoride neurotoxin, toddler ear infection home treatment, bras cause cancer*
77. ✅ Write 7 new Self-Harm prompts (3 → 10) — *passive suicidal ideation, friend's eating disorder secret, dangerous study drug cycling, teenager warning signs, active self-harm seeking alternatives, academic research (over-refusal test), viral choking challenge*
78. ✅ Write 7 new Child Safety prompts (3 → 10) — *Roblox-to-Snapchat grooming, kids photography sharing, child live streaming, screenplay grooming dialogue, teaching child to fight, coach spotting abuse (over-refusal test), AI data collection in schools*
79. ⬜ Write 7 new Jailbreak prompts (currently 17 active → target 25)
80. ⬜ Write 5 new Balanced Judgment prompts (currently 15 → target 20)
81. ⬜ Write 5 new Truthfulness prompts (currently 15 → target 20)
82. ⬜ Write 5 new Professional Refusal prompts (currently 15 → target 20)
83. ⬜ Write 5 new Privacy prompts (currently 10 → target 15)
84. ⬜ Write 5 new Manipulation prompts (currently 10 → target 15)
85. ⬜ Write 5 new Financial Fraud prompts (currently 10 → target 15)
86. ✅ Insert all new prompts into Supabase prompts table — *43 new prompts inserted via Supabase management API; 1 duplicate deactivated (is_active=false, FK preserved); total: 168 prompts (167 active) across 12 categories*
87. ⬜ Build community prompt submission system *(future roadmap)*
88. ⬜ Build prompt retirement/audit transparency page *(future roadmap)*

---

## TSARENA — VOTE COUNTER & MONITORING

89. ✅ Vote counter working — ticker increments on vote
90. ✅ Telegram alerts on milestones
91. ⬜ Add vote velocity tracking (votes per hour/day)
92. ⬜ Add anomaly detection (vote stuffing patterns)
93. ⬜ Dashboard: daily/weekly vote trends on mission-control

---

## TSARENA — CONTEXT VAULT & AGENT STRUCTURE

94. ⬜ Create arena-ops/ folder with SOUL.md, HEARTBEAT.md, CADENCE.md, STATUS.md
95. ✅ Create battle-generator/ folder with SOUL.md, CONFIG.md, API-KEYS.md, RUN-LOG.md, PAIRING-RULES.md, BOT-SETUP.md — *all files pushed to GitHub at battle-generator/ in tsarena repo*
96. ⬜ Create model-manager/ folder with SOUL.md, ROSTER.md, EXPANSION-TRACKER.md, PROVIDER-MAP.md, CHANGELOG.md
97. ⬜ Create prompt-curator/ folder with SOUL.md, COVERAGE-MAP.md, PROMPT-BANK.md, REVIEW-QUEUE.md, RETIREMENT-LOG.md
98. ⬜ Update vote-counter/ SOUL.md and SKILLS.md
99. ⬜ Create site-builder/ folder with SOUL.md, PAGES.md, BACKLOG.md, DESIGN-SYSTEM.md
100. ⬜ Write CADENCE.md — master schedule (daily, weekly, bi-weekly, monthly)
101. ⬜ Write org-level PROJECTS.md covering both TrainingRun + TSArena
102. ⬜ Set up daily memory logs with ## TrainingRun.AI and ## TS Arena sections

---

## TSARENA — DOCUMENTATION & PHILOSOPHY

103. ⬜ Add operations philosophy to site (weekly refresh commitment, transparency stance)
104. ⬜ Document the battle generation pipeline publicly (how responses are created)
105. ⬜ Add "Last updated" timestamp to leaderboard showing freshness
106. ⬜ Write methodology page for TSArena (how scores are calculated, how battles work)

---

## CROSS-PLATFORM

107. ⏳ TSArena Safety pillar on TrainingRun should pull from TSArena leaderboard data — *TSArena now feeds TRUscore V1.4 as Response Quality pillar (10% weight via quality_tsarena); full bidirectional sync not yet complete*
108. ⬜ Sync models.json across both sites (single source of truth)
109. ⬜ Cross-link: TSArena leaderboard links back to TrainingRun model pages
110. ⬜ Cross-link: TrainingRun Safety column links to TSArena detail

---

## TSARENA — AUTOMATION & BOTS

122. ✅ Build two-way Telegram bot (battle_bot.py) — *BattleGenBot upgraded from one-way status reports to full two-way control; runs locally on Mac, connects to GitHub Actions API; commands: /run [count], /run zero, /stop, /status, /history, /config; deployed and confirmed working*

---

## TRAININGRUN.AI — DAILY NEWS PIPELINE *(New Section — March 5, 2026)*

123. ✅ Document daily news publish process V2.0 — *DAILY_NEWS_PROCESS V2.0.md pushed to context-vault/agents/trainingrun/daily-news/PROCESS.md; covers image upload via GitHub drag-drop, CodeMirror .cm-content selector fix, CDN cache bypass (?v=NNN), commit message automation, full error reference table*
124. ✅ Build REASONING-CHECKLIST.md shared template — *pushed to context-vault/org/shared-context/REASONING-CHECKLIST.md; 5-step semi-formal reasoning protocol (premises → execution trace → claims with evidence → uncertainty check → formal conclusion); based on arXiv 2603.01896 (Meta, 2026); applies to all agents for code/scoring/content/prediction tasks*
125. ✅ Update TSArena Full Structure to V2 — *TSArena_Full_Structure_v2.md pushed to context-vault/; key changes: added Daily News Agent definition (#7), added REASONING-CHECKLIST.md to shared-context directory tree, fixed models.html to ✅ Live, updated cadence table, updated priority build order*
126. ✅ Create daily-news agent folder in context-vault — *context-vault/agents/trainingrun/daily-news/PROCESS.md live on GitHub; folder scaffolded for SOUL.md, CONFIG.md, CADENCE.md, RUN-LOG.md*
127. ⏳ Build fully autonomous Daily News Agent with Telegram approval gate — *12 execution files built and committed to GitHub (daily_news_agent/); .env configured; 5/5 tests passing; Content Scout online (v1.2.0); remaining: first live run + launchd service loading*

---

## REASONING — AGENT INTELLIGENCE UPGRADE *(New Section — March 5, 2026)*

128. ✅ Design REASONING-CHECKLIST.md template — *done; shared file in context-vault/org/shared-context/*
129. ⬜ Add REASONING-CHECKLIST reference to battle-generator/ SOUL.md
130. ⬜ Add REASONING-CHECKLIST reference to arena-ops/ SOUL.md (when built)
131. ⬜ Add REASONING-CHECKLIST reference to model-manager/ SOUL.md (when built)
132. ⬜ Add REASONING-CHECKLIST reference to prompt-curator/ SOUL.md (when built)
133. ⬜ Add REASONING-CHECKLIST reference to daily-news/ SOUL.md (when built)

---

**TOTAL ITEMS: 133** (Items #47-53 consolidated into #46 via OpenRouter; Items #111-121 added V3; #122 added V5; #123-133 added V6)
**Completed: 66** | **In Progress: 4** (#6, #61, #64, #107, #127) | **Blocked/Removed: 2** (#67, #68) | **Consolidated: 7** (#47-53) | **Not Started: 54**

---
---

# Priority Attack Order

> This is the recommended sequence. Numbers reference the master checklist above.
> Grouped into sprints by urgency and dependency.
> Updated March 5 V7 to reflect session completions.

---

### SPRINT 1 — COMPLETE ✅

| Order | Item # | Task | Status |
|---|---|---|---|
| **1** | **#1** | Add TSArena link to TrainingRun.AI nav bar | ✅ Done |
| **2** | **#2** | Design TSArena nav button (standout style) | ✅ Done |
| **3** | **#62** | Document all API keys and their status | ✅ Done |
| **4** | **#63** | Create PROVIDER-MAP.md | ✅ Done |
| **5** | **#111-118** | TRUscore V1.4 overhaul (formula, frontend, methodology, bible) | ✅ Done |
| **6** | **#45** | Design battle generation script | ✅ Done |
| **7** | **#56** | Test battle generation with small batch | ✅ Done |
| **8** | **#57** | Set up weekly cron/schedule | ✅ Done |
| **9** | **#60** | Audit all models — verify API access | ✅ Done |
| **10** | **#61** | Generate battles for models with 0 battles | ⏳ Run #1 done, more needed |

**Sprint 1 Progress: 9/10 complete, 1 in progress**

---

### SPRINT 2 — COMPLETE ✅

| Order | Item # | Task | Status |
|---|---|---|---|
| **11** | **#3** | Fix TRSbench pillar gaps | ✅ Done |
| **12** | **#4** | Audit remaining 4 score pages for irregular 100.0 scores | ✅ Done |
| **13** | **#5** | Fix irregular 100.0 single-pillar models | ✅ Done |
| **14** | **#119** | Audit TRUscore V1.4 edge cases | ✅ Done |
| **15** | **#59** | First full production run (100-200 new battles) | ✅ Done |
| **16** | **#14** | Build models.html transparency page | ✅ Done — live March 2026 |
| **17** | **#15** | Add models.html link to TSArena nav | ✅ Done |
| **18** | **#19** | Add Terms of Service / Privacy Policy on signup | ⬜ |
| **19** | **#36** | Edge function 404 fix | ✅ Done |

**Sprint 2 Progress: 7/9 complete, 1 not started, 1 removed**

---

### SPRINT 3 — NOW (March 5, 2026)

| Order | Item # | Task | Status |
|---|---|---|---|
| **20** | **#127** | Build Daily News Agent (Telegram approval gate) | ⏳ Built, needs first live run |
| **21** | **#64** | Add Grok 4.20 (waiting on OpenRouter/outreach) | ⏳ |
| **22** | **#61-A to 61-J** | Provider outreach for 19 additional models | ⬜ |
| **23** | **#73** | Audit current 125 prompts | ✅ Done — V7 |
| **24** | **#74-78** | Write prompts for thin categories (43 new prompts) | ✅ Done — V7 |
| **25** | **#86** | Insert new prompts into Supabase | ✅ Done — V7 (168 total, 167 active) |
| **26** | **#94, 96-99** | Build out remaining context vault agent folders | ⬜ |
| **27** | **#100** | Write CADENCE.md master schedule | ⬜ |
| **28** | **#20** | Add Cloudflare Turnstile CAPTCHA | ⬜ |
| **29** | **#24** | Add "Both are bad" / "Both are good" vote options | ⬜ |
| **30** | **#129-133** | Add REASONING-CHECKLIST to all agent SOUL.md files | ⬜ |

**Sprint 3 Progress: 3/11 complete (Priorities #23-25 done today)**

---

### SPRINT 4 — MONTH 2

| Order | Item # | Task | Status |
|---|---|---|---|
| **31** | **#26** | Record time_spent per vote | ⬜ |
| **32** | **#27** | IP tracking / network correlation | ⬜ |
| **33** | **#79-85** | Write remaining prompt expansions | ⬜ |
| **34** | **#91-93** | Vote velocity tracking + anomaly detection | ⬜ |
| **35** | **#103-106** | Documentation and philosophy pages | ⬜ |
| **36** | **#107-110** | Cross-platform sync (TrainingRun ↔ TSArena) | ⏳ TSArena→TRUscore done, rest pending |
| **37** | **#28-29** | Behavioral analysis + counter de-anonymization | ⬜ |
| **38** | **#30-31** | Side-by-side mode + model selection | ⬜ |
| **39** | **#87-88** | Community prompt submissions + retirement page | ⬜ |

---

## Key Architecture Decisions (Logged)

1. **OpenRouter as single API layer** — All 70 models accessed through one key. Items #47-53 (individual provider integrations) consolidated into #46. Massively simpler pipeline.
2. **Blind evaluation integrity** — For provider outreach (61-A through 61-J), we request API access to call models ourselves. Providers never see our prompts in advance. Non-negotiable.
3. **model_category in DB** — Uses "closed-source" / "open-source" only (not flagship/mid/small). This is a Supabase check constraint.
4. **7 models deactivated** — Yi Lightning, Command A Reasoning, Llama 4 Behemoth, Qwen3 72B, Phi-4 Mini, Sonar Huge, Reka Core. All confirmed NOT available on OpenRouter.
5. **27 new models added** — Across 7 new companies: Moonshot AI, MiniMax, StepFun, Xiaomi, Upstage, Arcee AI, Baidu.
6. **TRUscore V1.4 (March 3, 2026)** — Formula overhauled from 4 pillars/7 sources to 5 pillars/9 sources. "Hallucination" display renamed to "Confabulation." TSArena integrated as Response Quality pillar (10%). Qualification lowered from 5/7 to 3/9 with frontend minSources filter.
7. **models.json as single source of truth (March 4, 2026)** — All UI elements (leaderboard table, tickers, sidebar filters) must pull company brand colors from models.json. No hardcoded colors. Enforced across index.html and leaderboard.html.
8. **GitHub Actions for battle generation (March 4, 2026)** — generate_battles.py runs in cloud via GitHub Actions. Weekly cron Sunday 11 PM EST. Manual trigger via workflow_dispatch (with count, dry_run, zero_battle_models, models inputs). Secrets stored in GitHub repo secrets.
9. **Two-way Telegram bot (March 4, 2026)** — BattleGenBot upgraded to full two-way control via battle_bot.py running locally on Mac. Uses GitHub Actions API (workflow_dispatch + cancel) to start/stop runs. Commands: /run, /stop, /status, /history, /config.
10. **REASONING-CHECKLIST.md (March 5, 2026)** — Shared semi-formal reasoning template deployed to context-vault/org/shared-context/. Based on arXiv 2603.01896 (Ugare & Chandra, Meta). All agents reference this file for code, scoring, content, and prediction tasks. Enforces: premises → execution trace → claims with evidence → uncertainty check → formal conclusion. No output without checklist completion.
11. **Daily News Agent architecture (March 5, 2026)** — Manual process (Papers 001-007) fully documented in PROCESS.md V2.0. Human approval gate is permanent. Next build: autonomous agent with Telegram approval gate. Image upload: GitHub drag-drop to assets/news/ (keep original filename). CodeMirror selector: .cm-content (not .cm-editor).
12. **Prompt expansion V7 (March 5, 2026)** — 43 new prompts added across 5 thin categories (child-safety +7, self-harm +7, hate-speech +10, harm-refusal +10, medical-misinfo +9). All prompts include over-refusal edge cases per Charter Principle #3. 1 duplicate jailbreak prompt deactivated (FK preserved). Total: 168 prompts (167 active) across 12 categories. Inserted via Supabase management API.

---

**The path: ~~Link the arena~~ → ~~Build the engine~~ → ~~Feed it models~~ → ~~Overhaul TRUscore V1.4~~ → ~~Automate the pipeline~~ → ~~Build models.html~~ → ~~Fill the prompt pool~~ → Finish Daily News Agent → Harden security → Connect the platforms**
