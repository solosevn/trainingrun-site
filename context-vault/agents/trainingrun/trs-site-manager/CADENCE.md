# CADENCE — TRS Site Manager (TRSitekeeper)

> **Version:** 1.0 — March 6, 2026
> **Purpose:** When TRSitekeeper runs, audit schedule, reporting rhythms

---

## Daily Schedule

| Time (CST) | Activity |
|---|---|
| 4:00 AM | DDP Pipeline runs (`daily_runner.py` via cron) — Sitekeeper orchestrates |
| 4:30 AM | Post-DDP verification — check all 5 JSON files updated, spot-check scores |
| 6:00 AM | **Autonomous audit begins** — systematic site review (~1 hour) |
| 7:00 AM | Audit complete — daily findings report sent to David via Telegram |
| All day | **Reactive mode** — listening for David's Telegram messages |
| 11:00 PM | End of reactive window |

---

## Autonomous Audit Cycle (~1 hour/day)

### Weekly Rotation (Deep Audit Focus)

| Day | Deep Focus | Quick Check |
|---|---|---|
| Monday | index.html (full leaderboard audit) | All other pages |
| Tuesday | tsarena.html + tsarena-leaderboard.html | Data files |
| Wednesday | All 5 DDP JSON data files (integrity check) | HTML pages |
| Thursday | methodology.html + about.html + news.html | Leaderboards |
| Friday | CSS + responsive behavior + cross-browser | Data files |
| Saturday | Full site walkthrough (visitor perspective) | — |
| Sunday | Light check only — minimal processing | — |

### What "Deep Focus" Means
- Read the entire file line by line
- Check every visual element, every data point, every link
- Compare against brand DNA and design rules
- Log all findings, even minor ones

### What "Quick Check" Means
- Verify page loads without errors
- Spot-check 3-5 data points per leaderboard
- Check for obvious visual issues
- < 10 minutes per page

---

## DDP Pipeline Schedule

| DDP | Cron | Frequency |
|---|---|---|
| TRSbench | `0 4 * * *` | Daily at 4 AM CST |
| TRUscore | `0 4 * * *` | Daily at 4 AM CST |
| TRScode | `0 4 * * *` | Daily at 4 AM CST |
| TRFcast | `0 4 * * *` | Daily at 4 AM CST |
| TRAgents | `0 4 * * *` | Daily at 4 AM CST |

Orchestrated by `daily_runner.py` which runs all enabled DDPs sequentially.

---

## Reporting Cadence

| Frequency | Report | Delivery |
|---|---|---|
| Daily | Audit findings + suggestions | Telegram message after morning audit |
| Daily | Fix confirmations | Telegram after each reactive fix |
| Weekly (Monday) | Week-in-review summary | Telegram — issues found, fixes made, suggestions pending |
| Monthly | Site health scorecard | Telegram — trends, recurring issues, improvement ideas |

---

## Upstream Dependencies

| Source | What I Need | Frequency |
|---|---|---|
| DDP Pipeline | Fresh JSON data files | Daily (4 AM) |
| Daily News Agent | Published papers for news.html | Daily |
| TSArena agents | Battle results, vote data | Ongoing |
| David | Fix requests, approval for suggestions | Ad hoc |

## Downstream Dependencies

| Consumer | What I Provide | Frequency |
|---|---|---|
| trainingrun.ai visitors | Working, accurate, polished website | Always |
| David | Audit reports, fix confirmations, suggestions | Daily |
| DDP Pipeline | Orchestration trigger (daily_runner.py) | Daily |

---

## Cron Configuration

```cron
# DDP Pipeline — daily at 4 AM CST
0 4 * * * /usr/local/bin/python3 /path/to/daily_runner.py >> /path/to/logs/daily_runner.log 2>&1
```

Managed via macOS launchd plist: `com.trainingrun.daily_runner.plist`
