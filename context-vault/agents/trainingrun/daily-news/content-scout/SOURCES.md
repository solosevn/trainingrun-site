# Content Scout — SOURCES.md
# Version: 1.0 | Created: March 6, 2026
# Parent Agent: Daily News Agent
# Location: context-vault/agents/trainingrun/daily-news/content-scout/

---

## Source Philosophy

All sources are free, public, no API keys required (except xAI for verification, not scraping), no logins, no paywalls. This is non-negotiable. Content Scout costs nothing to run.

---

## Tier 1 — Where News Breaks First (Credibility: 35-40)

### arXiv (cs.AI, cs.LG, cs.CL)
| Field | Value |
|-------|-------|
| Method | RSS feeds |
| URLs | `export.arxiv.org/rss/cs.AI`, `export.arxiv.org/rss/cs.LG`, `export.arxiv.org/rss/cs.CL` |
| Credibility Score | 40 |
| Refresh | Every 30 min during scrape window |
| Avg Items/Cycle | 15-30 |
| Selection Rate | TBD (tracking starts with learning loop) |
| Reliability | Very high — rarely down |
| Notes | Primary source for new papers before anyone covers them |

### Hugging Face Daily Papers
| Field | Value |
|-------|-------|
| Method | HTTP GET (HTML parse) |
| URL | `huggingface.co/papers` |
| Credibility Score | 38 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 5-10 |
| Selection Rate | TBD |
| Reliability | High — occasional layout changes require scraper updates |
| Notes | Curated top papers, good signal-to-noise |

### GitHub Trending
| Field | Value |
|-------|-------|
| Method | HTTP GET (HTML parse) |
| URLs | `github.com/trending/python?since=daily`, `github.com/trending?since=daily` |
| Credibility Score | 35 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 10-25 |
| Selection Rate | TBD |
| Reliability | High |
| Notes | New repos/tools gaining traction — AI-filtered by keywords |

---

## Tier 2 — Community Reaction (Credibility: 12-22)

### Reddit
| Field | Value |
|-------|-------|
| Method | JSON endpoint (`.json` suffix) |
| Subreddits | r/MachineLearning, r/LocalLLaMA, r/artificial, r/singularity |
| Credibility Score | 15 |
| Refresh | Every 30 min (2-sec delay between subreddits) |
| Avg Items/Cycle | 20-40 |
| Selection Rate | TBD |
| Reliability | Medium — rate limiting can block, occasional API changes |
| Notes | Hours before Twitter for breaking discussion |

### Hacker News
| Field | Value |
|-------|-------|
| Method | Firebase API |
| URL | `hacker-news.firebaseio.com/v0/topstories.json` |
| Credibility Score | 18 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 5-15 (AI-filtered from top 30) |
| Selection Rate | TBD |
| Reliability | Very high — Firebase API is rock solid |
| Notes | Tech community takes on AI news |

### Lobste.rs
| Field | Value |
|-------|-------|
| Method | RSS feed |
| URL | `lobste.rs/t/ai.rss` |
| Credibility Score | 20 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 2-5 |
| Selection Rate | TBD |
| Reliability | High — small but high-quality community |
| Notes | Higher signal-to-noise than Reddit/HN |

---

## Tier 3 — Deeper Context (Credibility: 12-22)

### YouTube Channels
| Field | Value |
|-------|-------|
| Method | RSS feeds |
| Channels | AI Explained, Two Minute Papers, Yannic Kilcher, Matthew Berman |
| Credibility Score | 12 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 0-3 (channels don't post every day) |
| Selection Rate | TBD |
| Reliability | High — YouTube RSS is stable |
| Notes | Deep dives on papers and model reviews |

### Newsletters
| Field | Value |
|-------|-------|
| Method | RSS feeds |
| Sources | TLDR AI (`tldrai.com`), Import AI (`importai.substack.com`), The Batch (`read.deeplearning.ai`) |
| Credibility Score | 22 |
| Refresh | Every 30 min |
| Avg Items/Cycle | 0-5 (weekly/daily depending on newsletter) |
| Selection Rate | TBD |
| Reliability | High |
| Notes | Curated digests — good for catching things scrapers miss |

---

## Ethical Guardrails

All scraped domains are pre-approved in `KNOWN_PUBLIC_DOMAINS`:
```
export.arxiv.org, huggingface.co, github.com, www.reddit.com,
hacker-news.firebaseio.com, news.ycombinator.com, lobste.rs,
www.youtube.com, tldrai.com, importai.substack.com, read.deeplearning.ai
```

Rules:
1. Only HTTP/HTTPS protocols
2. Reject any URL requiring login or paywall
3. Identify as ContentScout via User-Agent header
4. Respect rate limits (2-sec delay between Reddit calls)
5. No personal data scraping
6. If a site blocks us — report and stop, do not retry aggressively

---

## Source Performance Summary

*Updated automatically by scout_learning_logger.py after each feedback event.*

| Source | 30-Day Surfaced | 30-Day Selected | Selection Rate | Current Weight |
|--------|----------------|-----------------|----------------|----------------|
| arXiv | - | - | - | 1.0x |
| Hugging Face | - | - | - | 1.0x |
| GitHub Trending | - | - | - | 1.0x |
| Reddit | - | - | - | 1.0x |
| Hacker News | - | - | - | 1.0x |
| Lobste.rs | - | - | - | 1.0x |
| YouTube | - | - | - | 1.0x |
| Newsletters | - | - | - | 1.0x |

---

*Read by Content Scout via scout_context_loader.py. Defines all sources, their reliability, and tracks performance over time.*
