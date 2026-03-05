# CONFIG.md — Daily News Agent
## Technical Configuration
> **Location:** context-vault/agents/trainingrun/daily-news/CONFIG.md
> **Version:** 1.0 — March 5, 2026
> **Owner:** David Solomon
> **Status:** Active

---

## Telegram Bot

| Field | Value |
|---|---|
| **Bot Name** | TRNewsAgentBot |
| **Bot Username** | @TRnewzBot |
| **Bot Token** | Stored in `.env` as `TRNEWZ_BOT_TOKEN` — NEVER commit to repo |
| **David's Chat ID** | Stored in `.env` as `DAVID_CHAT_ID` — NEVER commit to repo |
| **Notification Style** | Direct message to David's personal chat (not a group) |

### Telegram Message Templates

**Story ready for review:**
```
📰 TRNewzBot — Article Ready for Review

Title: [article title]
Source: [paper title + authors]
Paper: [paper number, e.g. Paper 008]

Preview: [link to staged draft or GitHub preview]

Reply with:
✅ "push it" — publish as-is
✏️ "edit: [your notes]" — I'll revise and re-send
❌ "kill it" — skip this story today
```

**Edit cycle response:**
```
✏️ Revision ready — Paper [NNN]

Changes made: [summary of edits]
Preview: [updated link]

Reply ✅ to publish or ✏️ for more edits.
```

**Publish confirmation:**
```
✅ Paper [NNN] published!

Title: [title]
URL: https://trainingrun.ai/day-[NNN].html
news.html updated ✓

Post-publish tracking active — I'll log performance in 24-48 hours.
```

---

## Article Configuration

| Field | Value |
|---|---|
| **Template File** | `day-template.html` (repo root) |
| **Article Pattern** | `day-NNN.html` (e.g., `day-008.html`) |
| **Numbering** | Sequential, zero-padded to 3 digits. Check last published article and increment by 1. |
| **News Index Page** | `news.html` — add new card at TOP of article list |
| **Image Directory** | `assets/news/` |
| **Signature Image** | `assets/signature.png` |
| **Site URL** | `https://trainingrun.ai` |
| **Repository** | `solosevn/trainingrun-site` (GitHub Pages, `main` branch) |

### Article HTML Structure Notes

- Each article is a standalone HTML file generated from `day-template.html`
- Image tag uses original filename from the source paper (no renaming)
- Use `?v=NNN` suffix on image URLs for CDN cache busting (increment on each publish)
- Category badges use the `article-tag` CSS class (amber pill style)
- David's signature block appears at the bottom of every article
- Meta tags: `og:title`, `og:description`, `og:image` for social sharing on X

### news.html Card Format

Each new article gets a card entry at the top of the article list in `news.html`:
- Thumbnail image (links to article)
- Title (links to article)
- Date published
- Category tag(s)
- Brief description (1-2 sentences)

---

## Content Scout Integration

| Field | Value |
|---|---|
| **Source** | Content Scout's Mission Control output |
| **Delivery Time** | ~5:30am CST daily |
| **Delivery Signal** | Telegram notification from Content Scout to David |
| **Stories Per Day** | 3-8 filtered stories (varies) |
| **Agent Activation** | ~10 minutes after Content Scout's Telegram ping |

### Future: SCOUT-DIRECTIVE.md

When activated, the Daily News Agent will write a `SCOUT-DIRECTIVE.md` file that Content Scout reads before its next scraping run. This file will contain:
- Priority topics (based on audience engagement patterns from LEARNING-LOG.md)
- Gap areas (categories or topics underrepresented in recent coverage)
- Specific labs, authors, or arXiv categories to monitor
- Keywords to prioritize or deprioritize

**Status:** PLANNED — not yet active. Content Scout currently runs independently.

---

## Source Citation Format

Every article must include a citation block with the following fields:

```
Source Paper: [full paper title]
Authors: [all authors, institution(s)]
Published: [date] | [venue/journal if applicable]
arXiv: [arXiv ID with link, e.g. arXiv:2603.01896]
Institution: [primary institution(s)]
```

### Citation Rules
- Always link to the original paper (arXiv, conference page, or publisher)
- List ALL authors — do not truncate with "et al." unless there are 10+
- Include institution names
- If the story comes from a news source rather than a paper, cite the journalist, publication, and date
- Never present someone else's work as our own

---

## Performance Tracking Configuration

### Metrics to Capture (per article, logged to LEARNING-LOG.md)

**Process Metrics:**
| Metric | How to Measure |
|---|---|
| Story selection time | Timestamp: Content Scout delivery → story selected |
| Article writing time | Timestamp: story selected → draft complete |
| Total cycle time | Timestamp: Content Scout delivery → Telegram sent to David |
| Edit requests | Count of revision cycles before approval |
| First-pass approval | YES/NO — did David approve on first review? |
| Edit categories | What type of edits? (tone, accuracy, length, angle, other) |

**Audience Metrics (24-48 hours post-publish):**
| Metric | Source |
|---|---|
| Page views | TrainingRun.AI analytics (if available) |
| X post impressions | X/Twitter analytics for the article's post |
| X engagements | Likes, reposts, replies, bookmarks |
| X click-through rate | Clicks on the article link from X |
| Referral sources | Where traffic came from (X, direct, search, other) |

### Learning Cycle
- **After publish:** Log process metrics immediately
- **After 24-48 hours:** Log audience metrics
- **Weekly (Sunday):** Review LEARNING-LOG.md → update STYLE-EVOLUTION.md
- **Before each cycle:** Read STYLE-EVOLUTION.md to apply latest learnings

---

## GitHub Workflow

| Step | Method |
|---|---|
| **File creation** | GitHub web UI → "Add file" → "Create new file" |
| **Content editing** | GitHub web UI → edit file → `.cm-content` (CodeMirror selector) |
| **Image upload** | GitHub drag-drop into `assets/news/` directory (NOT file attachment, NOT inline paste) |
| **Commit messages** | Descriptive: "Publish day-NNN: [article title]" |
| **Branch** | Always commit to `main` (GitHub Pages auto-deploys) |
| **Commit message for JS** | Use `.cm-content` element, set value via `document.execCommand('insertText')` |

---

## Security Notes

- **Bot tokens:** NEVER stored in repository files. Use `.env` or GitHub Secrets only.
- **API keys:** Same rule — no keys in committed files. Reference by environment variable name only.
- **The repo is PUBLIC.** Every file committed is visible to the world. Treat all committed content accordingly.

---

## File Dependencies

```
CONFIG.md reads from:
  └── (no dependencies — this is a reference file)

CONFIG.md is read by:
  ├── SOUL.md (references technical config)
  ├── PROCESS.md (references templates, paths, Telegram formats)
  └── Any script or agent that executes the daily news workflow
```

---

*Last updated: March 5, 2026*
