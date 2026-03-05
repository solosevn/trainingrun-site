# The Safety Arena — Full Operational Structure

> **Version:** Draft 2 — March 5, 2026
> **Status:** Working document — David + Claude finalizing
> **Purpose:** Single source of truth for every agent, process, and cadence that powers TSArena + TrainingRun.AI

---

## Directory Tree

```
trainingrun-site/
├── context-vault/
│   ├── org/                                    # ← Global / cross-site
│   │   ├── SOUL.md                             # Identity, voice, boundaries
│   │   ├── USER.md                             # David's prefs, CST timezone, Telegram style
│   │   ├── HEARTBEAT.md                        # Cross-site dashboard (status, reminders, health)
│   │   ├── MEMORY.md                           # Long-term curated knowledge
│   │   └── shared-context/
│   │       ├── THESIS.md                       # What we believe (truth + safety)
│   │       ├── SIGNALS.md                      # Reference intel
│   │       ├── FEEDBACK-LOG.md                 # Style corrections
│   │       ├── PRODUCTION-BIBLE.md             # Production standards
│   │       ├── PROJECTS.md                     # High-level overview of both sites
│   │       └── REASONING-CHECKLIST.md          # 🆕 Shared truth engine — all agents reference this
│   │
│   ├── agents/
│   │   ├── trainingrun/                        # ── TrainingRun.AI agents ──
│   │   │   ├── trs-site-manager/
│   │   │   │   └── SOUL.md
│   │   │   ├── content-scout/
│   │   │   │   └── SOUL.md
│   │   │   ├── ddp-pipeline/
│   │   │   │   └── SOUL.md
│   │   │   │
│   │   │   └── daily-news/                     # 📰 DAILY NEWS AGENT (NEW)
│   │   │       ├── SOUL.md                     # Mission: research, write, and stage daily articles
│   │   │       ├── CONFIG.md                   # arXiv sources, article format, image handling
│   │   │       ├── PROCESS.md                  # Full publish workflow with human approval gate
│   │   │       ├── CADENCE.md                  # Daily schedule + Telegram notification triggers
│   │   │       └── RUN-LOG.md                  # Log of every article: paper, status, publish date
│   │   │
│   │   └── tsarena/                            # ── TS Arena agents ──
│   │       │
│   │       ├── arena-ops/                      # 🎯 CHIEF OF OPERATIONS
│   │       │   ├── SOUL.md                     # Mission: orchestrate all TSArena agents
│   │       │   ├── HEARTBEAT.md                # Weekly health check across all agents
│   │       │   ├── CADENCE.md                  # Master schedule (what runs when)
│   │       │   └── STATUS.md                   # Current state of every system
│   │       │
│   │       ├── battle-generator/               # ⚔️ BATTLE GENERATION PIPELINE
│   │       │   ├── SOUL.md                     # Mission: generate fresh battles weekly
│   │       │   ├── CONFIG.md                   # API endpoints, rate limits, batch sizes
│   │       │   ├── API-KEYS.md                 # Key status per provider (DO NOT COMMIT KEYS)
│   │       │   ├── RUN-LOG.md                  # Log of every generation run
│   │       │   ├── PAIRING-RULES.md            # How models are matched (random, round-robin, etc.)
│   │       │   └── scripts/
│   │       │       └── generate_battles.py     # The actual batch script
│   │       │
│   │       ├── model-manager/                  # 🤖 MODEL ROSTER & EXPANSION
│   │       │   ├── SOUL.md                     # Mission: maintain and grow the model roster
│   │       │   ├── ROSTER.md                   # Master list of all models (current + target)
│   │       │   ├── EXPANSION-TRACKER.md        # Models to add, API access status, blockers
│   │       │   ├── PROVIDER-MAP.md             # Which API/provider serves each model
│   │       │   └── CHANGELOG.md                # When models were added/removed and why
│   │       │
│   │       ├── prompt-curator/                 # 📝 PROMPT POOL MANAGEMENT
│   │       │   ├── SOUL.md                     # Mission: maintain quality prompt pool
│   │       │   ├── COVERAGE-MAP.md             # Category balance tracker
│   │       │   ├── PROMPT-BANK.md              # All prompts with categories and status
│   │       │   ├── REVIEW-QUEUE.md             # Community submissions (future)
│   │       │   └── RETIREMENT-LOG.md           # Prompts retired from active pool and why
│   │       │
│   │       ├── vote-counter/                   # 🗳️ VOTE MONITORING
│   │       │   ├── SOUL.md                     # Mission: track votes, alert on milestones
│   │       │   ├── SKILLS.md                   # Supabase polling, 5-vote logic, Telegram alerts
│   │       │   └── HEARTBEAT.md                # Voting activity health
│   │       │
│   │       └── site-builder/                   # 🏗️ FRONTEND & PAGES
│   │           ├── SOUL.md                     # Mission: maintain and build site pages
│   │           ├── PAGES.md                    # Every page on tsarena.ai + status
│   │           ├── BACKLOG.md                  # Features and pages to build
│   │           └── DESIGN-SYSTEM.md            # Colors, fonts, components, CSS vars
│   │
│   └── memory/
│       ├── 2026-03-02.md                       # Daily logs with ## TrainingRun.AI and ## TS Arena
│       ├── ...
│       └── curated/                            # Summarized weekly/monthly takeaways
│
├── ... (existing trainingrun files)
│
└── tsarena/                                    # ← The live site repo (GitHub Pages)
    ├── index.html                              # Landing page
    ├── vote.html                               # Arena voting page
    ├── leaderboard.html                        # Leaderboard
    ├── prompts.html                            # Our Prompts (transparency)
    ├── models.html                             # ✅ Our Models (transparency) — LIVE
    ├── charter.html                            # Charter page
    ├── mission-control.html                    # Internal dashboard
    ├── models.json                             # Model-to-company mapping
    └── assets/
        ├── logos/                              # Lab logos
        ├── news/                               # Article images (e.g. GxyPU.jpg)
        └── signature.png                       # David's signature for articles
```

---

## Agent Definitions

### 1. Arena Ops — Chief of Operations
| Field | Detail |
|---|---|
| **Role** | Orchestrator — makes sure every other TSArena agent runs on schedule |
| **Cadence** | Continuous / always-on awareness |
| **Owns** | Master schedule, cross-agent health checks, status reporting |
| **Key files** | CADENCE.md, STATUS.md, HEARTBEAT.md |

**What CADENCE.md tracks:**
- Weekly battle generation (every Sunday night)
- Model roster review (bi-weekly)
- Prompt pool audit (monthly)
- Leaderboard health check (daily)
- Vote activity monitoring (real-time)

---

### 2. Battle Generator — The Engine
| Field | Detail |
|---|---|
| **Role** | Generate fresh AI-vs-AI battles by calling real model APIs |
| **Cadence** | Weekly (minimum) — target: every Sunday |
| **Owns** | Battle generation script, API configs, run logs |
| **Key files** | generate_battles.py, CONFIG.md, RUN-LOG.md |

**How it works:**
1. Pull active prompts from Supabase `prompts` table
2. Pull active models from Supabase `models` table
3. Generate random pairings (avoid duplicates already in `battles`)
4. For each pairing: send prompt to Model A's API → collect response
5. Send same prompt to Model B's API → collect response
6. Insert complete battle row into Supabase `battles` table
7. Log the run in RUN-LOG.md (date, battles generated, errors, cost)

**Current state:**
- ❌ Script does not exist yet — battles were bulk-loaded manually
- ❌ No automated schedule
- 🎯 **Priority: BUILD THIS FIRST**

**Target output per run:** 100-200 new battles/week

---

### 3. Model Manager — The Roster
| Field | Detail |
|---|---|
| **Role** | Maintain, expand, and track every AI model in the arena |
| **Cadence** | Bi-weekly review, ad-hoc when new models launch |
| **Owns** | Model roster, API access tracking, provider mapping |
| **Key files** | ROSTER.md, EXPANSION-TRACKER.md, PROVIDER-MAP.md |

**Current state:**
- 50 models in database
- 38 actively in battles (12 have zero battles)
- ❌ No tracking of which API keys we have
- ❌ No expansion pipeline
- 🎯 **Target: 100+ models**

**Models known to be missing (partial list):**
- Grok 4.20 (xAI)
- Gemma 3 (Google)
- Jamba 2 (AI21)
- Yi Lightning (01.AI)
- Reka Core / Flash (Reka)
- Inflection Pi (Inflection)
- Additional Cohere models
- Additional open-source (via Together, Fireworks, Replicate)

**PROVIDER-MAP.md will track:**
| Model | Provider | API Type | Key Status | Cost Tier |
|---|---|---|---|---|
| GPT-5 | OpenAI | Direct | ✅ Active | $$ |
| Claude Opus 4.6 | Anthropic | Direct | ✅ Active | $$ |
| Llama 4 Scout | Together AI | Inference | ✅ Active | $ |
| Grok 4.20 | xAI | Direct | ❌ Need key | $$ |
| ... | ... | ... | ... | ... |

---

### 4. Prompt Curator — The Quality Gate
| Field | Detail |
|---|---|
| **Role** | Maintain prompt quality, balance categories, manage lifecycle |
| **Cadence** | Monthly audit, ad-hoc when new prompts are written |
| **Owns** | Prompt pool, category coverage, retirement decisions |
| **Key files** | COVERAGE-MAP.md, PROMPT-BANK.md |

**Current state:**
- 125 prompts across 12 categories
- 123 of 125 are used in battles (2 unused)
- Each prompt used ~4 times on average across different matchups
- ⚠️ Some categories are thin: child-safety (3), self-harm (3), hate-speech (5)

**Category coverage (current → target):**
| Category | Current | Target | Gap |
|---|---|---|---|
| Jailbreak | 18 | 25 | +7 |
| Balanced Judgment | 15 | 20 | +5 |
| Truthfulness | 15 | 20 | +5 |
| Professional Refusal | 15 | 20 | +5 |
| Medical Misinfo | 11 | 20 | +9 |
| Harm Refusal | 10 | 20 | +10 |
| Privacy | 10 | 15 | +5 |
| Manipulation | 10 | 15 | +5 |
| Financial Fraud | 10 | 15 | +5 |
| Hate Speech | 5 | 15 | +10 |
| Self-Harm | 3 | 10 | +7 |
| Child Safety | 3 | 10 | +7 |
| **TOTAL** | **125** | **205** | **+80** |

---

### 5. Vote Counter — The Pulse
| Field | Detail |
|---|---|
| **Role** | Monitor voting activity, alert on milestones, flag anomalies |
| **Cadence** | Real-time / continuous |
| **Owns** | Vote tracking, Telegram alerts, mission-control updates |
| **Key files** | SKILLS.md, HEARTBEAT.md |

**Current state:**
- ✅ Exists and functional
- Monitors vote counts
- Updates mission-control.html
- Sends Telegram alerts on milestones

---

### 6. Site Builder — The Storefront
| Field | Detail |
|---|---|
| **Role** | Build and maintain all TSArena web pages |
| **Cadence** | As needed / sprint-based |
| **Owns** | All HTML pages, design system, feature backlog |
| **Key files** | PAGES.md, BACKLOG.md, DESIGN-SYSTEM.md |

**Page inventory:**
| Page | Status | Notes |
|---|---|---|
| index.html | ✅ Live | Landing page |
| vote.html | ✅ Live | Arena voting — reveal card recently fixed |
| leaderboard.html | ✅ Live | Sticky header, Vote Record, score colors |
| prompts.html | ✅ Live | Prompt transparency page |
| charter.html | ✅ Live | Charter page |
| mission-control.html | ✅ Live | Internal dashboard |
| models.html | ✅ Live | Public model roster — launched March 2026 |

---

### 7. Daily News Agent — The Journalist *(NEW)*
| Field | Detail |
|---|---|
| **Role** | Research AI papers daily, write article, stage for David's approval, publish on approval |
| **Cadence** | Daily — runs automatically, notifies David via Telegram when ready |
| **Owns** | Article drafts, paper sourcing, image staging, publish workflow |
| **Key files** | SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md, RUN-LOG.md |
| **Site** | TrainingRun.AI (`/day-NNN.html` + `news.html`) |

**How it works:**
1. Agent sources paper from arXiv or curated feed
2. Agent reads paper in full, writes article using `day-template.html`
3. Agent stages draft — sends Telegram message to David: *"Article ready for review: [title] — [link]"*
4. David reviews, approves content
5. David uploads image to `assets/news/` via GitHub drag-drop (current workflow)
6. David signals approval
7. Agent commits article HTML + updates `news.html` card list
8. Agent sends confirmation Telegram: *"Paper NNN published ✅"*

**Human approval gate:** Article is NEVER published without David's explicit sign-off. Agent stops at step 3 and waits.

**Current state:**
- ✅ Manual process established and working (Papers 001–007 published)
- ✅ DAILY_NEWS_PROCESS V1.0 documented
- ✅ Image upload workflow resolved (GitHub drag-drop)
- ❌ Agent not yet built — process currently run manually with Claude
- 🎯 **Next: Build autonomous agent with Telegram approval gate**

**Key files on trainingrun-site:**
- `day-template.html` — master article template
- `news.html` — article index page
- `assets/news/` — article images
- `assets/signature.png` — David's signature

---

## Operational Cadences

| Cadence | What | Owner | Day/Time |
|---|---|---|---|
| **Real-time** | Vote monitoring + Telegram alerts | Vote Counter | Always on |
| **Daily** | Leaderboard health check (scores updating?) | Arena Ops | Morning |
| **Daily** | Source paper → write article → Telegram David for review | Daily News Agent | Morning (CST) |
| **Weekly** | Generate 100-200 new battles via API calls | Battle Generator | Sunday night |
| **Weekly** | Review battle generation logs, flag errors | Arena Ops | Monday morning |
| **Bi-weekly** | Model roster review — new models to add? | Model Manager | 1st & 15th |
| **Monthly** | Prompt category audit — gaps? retirements? | Prompt Curator | 1st of month |
| **Monthly** | Full system health report | Arena Ops | 1st of month |
| **Quarterly** | Expansion targets — model count, prompt count | Arena Ops + All | Quarter start |

---

## Database Schema (Supabase)

### `models` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| name | text | Display name (e.g., "GPT-5") |
| lab | text | Company name (e.g., "OpenAI") |
| created_at | timestamp | When added |

### `prompts` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| text | text | The prompt scenario |
| category | text | Safety category |
| is_active | boolean | In active pool or retired |
| moderation_status | text | Review status |
| source | text | Who wrote it |
| tags | text | Additional tags |
| used_count | integer | Times used in battles |
| created_at | timestamp | When added |

### `battles` table
| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| battle_number | integer | Sequential ID |
| prompt_id | uuid | FK → prompts |
| model_a_id | uuid | FK → models |
| model_b_id | uuid | FK → models |
| model_a_response | text | **Pre-generated** response from Model A |
| model_b_response | text | **Pre-generated** response from Model B |
| votes_a | integer | Votes for A |
| votes_b | integer | Votes for B |
| votes_tie | integer | Tie votes |
| total_votes | integer | Sum of all votes |
| is_public | boolean | Visible to voters |
| created_at | timestamp | When battle was generated |

---

## Current Numbers (as of March 5, 2026)

| Metric | Count | Target |
|---|---|---|
| Models in database | 50 | 100+ |
| Models with battles | 38 | All models |
| Prompts | 125 | 205+ |
| Prompt categories | 12 | 12+ (expand as needed) |
| Total battles | 500 | 1,000+ (growing weekly) |
| Unique model pairings used | 332 | 500+ |
| Possible pairings (38 models) | 703 | — |
| Battles per prompt (avg) | 4.1 | 8-10 |
| Max battles per prompt | 9 | — |
| Null responses | 0 | 0 (always) |
| Daily news articles published | 7 | Daily cadence |

---

## Priority Build Order

| # | Item | Agent | Effort | Impact |
|---|---|---|---|---|
| 1 | Build `generate_battles.py` pipeline | Battle Generator | High | 🔴 Critical |
| 2 | Set up weekly cron/schedule for battle generation | Battle Generator + Arena Ops | Medium | 🔴 Critical |
| 3 | Audit and document all API keys/access | Model Manager | Medium | 🔴 Critical |
| 4 | Build Daily News Agent (Telegram approval gate) | Daily News Agent | High | 🔴 Critical |
| 5 | Add missing 12 models to battles (they exist but have 0) | Battle Generator | Low | 🟡 High |
| 6 | ~~Build `models.html` transparency page~~ ✅ DONE | Site Builder | — | ✅ Complete |
| 7 | Expand model roster toward 100 | Model Manager | High (ongoing) | 🟡 High |
| 8 | Write 80 new prompts to fill category gaps | Prompt Curator | High (ongoing) | 🟡 High |
| 9 | Document CADENCE.md with all schedules | Arena Ops | Low | 🟢 Medium |
| 10 | Add REASONING-CHECKLIST.md to all agent SOUL.md files | All Agents | Low | 🟢 Medium |
| 11 | Community prompt submission system (roadmap) | Prompt Curator + Site Builder | High | 🔵 Future |
| 12 | Public prompt retirement/audit page (roadmap) | Prompt Curator + Site Builder | Medium | 🔵 Future |

---

## Philosophy (to be added to site)

> **The Safety Arena operates on a principle of structured transparency.** Our prompts are curated, our battles are generated from real AI model responses, and our model roster is public. We refresh our battle pool weekly to ensure the leaderboard reflects current model performance — not a one-time snapshot. Every model faces the same challenge pool under the same conditions. This is how you build safety data you can trust.

---

*This document is the working blueprint. Every agent, every process, every cadence lives here until each piece has its own dedicated file in the vault.*
