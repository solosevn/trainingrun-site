# TrainingRun Daily News — Article Publishing Process

**Version:** 2.0
**Last Updated:** March 5, 2026
**Owner:** David Solomon
**Site:** [trainingrun.ai](https://trainingrun.ai)

---

## What Changed in V2.0

- **Image upload workflow fully resolved** — documented in Step 6 below. This was the recurring blocker in V1.0. The working method is GitHub drag-drop, not file attachment or inline paste.
- **cmTile/cmView selector clarified** — `.cm-content` is the correct selector for GitHub's CodeMirror editor, not `.cm-editor`.
- **Commit message automation** — JS method to set commit message input value documented.
- **Daily News Agent noted** — this process is currently manual (Claude + David). Future state: autonomous agent with Telegram approval gate.

---

## Overview

This document defines the end-to-end process for publishing a daily research briefing article to the TrainingRun.AI website. The site is a static GitHub Pages site hosted from the `solosevn/trainingrun-site` repository. Each article is a standalone HTML file (`day-NNN.html`) generated from a master template.

The workflow is designed to be executed by a human operator or an autonomous AI agent. Every step is explicit. No assumptions. No shortcuts.

**Target time:** Under 10 minutes per article once content is provided.

---

## Inputs Required

Before starting, you need exactly these things:

1. **Article content** — one of:
   - A Markdown (.md) file with structured metadata and body text
   - Pasted text with the same structure
   - A file path pointing to the content

2. **Image** (optional but standard) — one image, typically the paper's key figure. David provides this. See Step 6 for the upload workflow.

3. **GitHub access** — the Chrome extension browser workflow is used for all edits (no PAT or git CLI required). The operator must be signed into GitHub in the browser with write access to `solosevn/trainingrun-site`.

---

## Content Format

The article content (MD or text) must contain these fields. If any are missing, infer them from context.

| Field | Marker | Example |
|---|---|---|
| Headline | `# HEADLINE` | `# Tool Use Just Became Native` |
| Deck | `## Deck:` or first line after headline | `Nous Research ships Hermes-Agent...` |
| Kicker | `**Kicker:**` | `RESEARCH WATCH` |
| Tags | `**Tags:**` | `Agents, Open Source, Tool Use` |
| Paper title | `**Paper:**` | `Hermes-Agent: An Open Toolkit...` |
| Authors | `**Authors:**` | `Teknium, Chen, et al.` |
| Institutions | `**Institutions:**` | `Nous Research` |
| Paper URL | `**Paper URL:**` | `https://arxiv.org/abs/2502.14923` |
| Date | `**Date:**` | `March 1, 2026` |
| Article body | Everything after the metadata block | Paragraphs, stats, callouts |

**Kicker rules:** Almost always use `RESEARCH WATCH`. Only use `ANALYSIS` for opinion/synthesis pieces that don't reference a specific paper.

---

## Repository Structure

```
solosevn/trainingrun-site/
├── index.html                  # Homepage
├── news.html                   # Article listing page (cards grid)
├── day-template.html           # Master article template (DO NOT EDIT)
├── day-001.html                # Published article
├── day-002.html                # Published article
├── ...
├── day-NNN.html                # Next article you create
└── assets/
    ├── signature.png           # David Solomon signature (used in every article)
    └── news/
        ├── GxyPU.jpg           # Example — images keep their original filename
        └── [original-name].jpg # Images are NOT renamed — keep filename as-is
```

**Image naming note (V2.0 update):** Images are committed with their original filename (e.g., `GxyPU.jpg`), not renamed to `paper004-fig1.jpg`. The article HTML references whatever filename was committed.

---

## Step-by-Step Workflow

### Step 1 — Determine the Next Article Number

Check the existing `day-*.html` files in the repo to find the highest number. The next article is that number + 1, zero-padded to 3 digits.

Example: If `day-007.html` exists, the next file is `day-008.html`.

### Step 2 — Parse the Article Content

Read the operator's MD file or pasted text. Extract every field from the Content Format table above. If a field is missing:

- **Deck missing:** Derive from the first paragraph of the body.
- **Date missing:** Use today's date.
- **Tags missing:** Infer 2–4 tags from the paper's subject matter.
- **Kicker missing:** Default to `RESEARCH WATCH`.

### Step 3 — Read the Template and Build the Article

Fetch `day-template.html` from the repo (raw URL or GitHub API). Build the complete article HTML by replacing all 20 placeholder tokens. Save locally for review.

### Step 4 — Fill All Template Placeholders

The template contains 20 placeholders. Replace every single one. Do not leave any `{{...}}` tokens in the final file.

| Placeholder | Value | Notes |
|---|---|---|
| `{{META_TITLE}}` | Short headline for browser tab | ≤60 characters |
| `{{META_DESCRIPTION}}` | One-sentence summary | ≤150 characters |
| `{{DATE_UPPER}}` | `MARCH 5, 2026` | ALL CAPS |
| `{{DATE_LONG}}` | `March 5, 2026` | Title case |
| `{{ARTICLE_NUMBER}}` | `008` | 3-digit, zero-padded |
| `{{KICKER}}` | `RESEARCH WATCH` | ALL CAPS |
| `{{HEADLINE_HTML}}` | Headline with cyan highlights | See Headline Styling below |
| `{{DECK}}` | Subtitle sentence | Plain text |
| `{{TAGS_HTML}}` | Tag badges | See Tag Format below |
| `{{ARTICLE_BODY_HTML}}` | Full article body | See Body Components below |
| `{{PAPER_TITLE}}` | Full paper title | Plain text |
| `{{PAPER_URL}}` | Full URL to paper | `https://arxiv.org/abs/...` |
| `{{PAPER_CITATION}}` | Citation line | `Author et al., arXiv, 2026` |
| `{{PAPER_AUTHORS}}` | Author list | Comma-separated |
| `{{PAPER_INSTITUTIONS}}` | Institution list | Comma-separated |
| `{{PAPER_URL_SHORT}}` | Display URL | `arxiv.org/abs/2502.14923` |
| `{{EMAIL_SUBJECT_ENCODED}}` | URL-encoded email subject | `TrainingRun%20Daily%20-%20Day%20008` |
| `{{EMAIL_BODY_ENCODED}}` | URL-encoded email body | Reference to `trainingrun.ai/day-008.html` |
| `{{PREV_URL}}` | Previous article filename | `day-007.html` |
| `{{PREV_LABEL}}` | Previous article label | `Day 007` |

Also add the `.cyan` CSS class to the `<style>` block if not already in the template:

```css
.cyan { color: var(--cyan); text-shadow: 0 0 20px rgba(0, 212, 255, 0.4); }
```

### Step 5 — Build the Article Body HTML

Replace `{{ARTICLE_BODY_HTML}}` with structured HTML. A typical article follows this structure:

1. Opening paragraph — hook with the key finding
2. Callout box — the single most important number or result
3. 2–3 body paragraphs — what they did, how, why it matters
4. Figure — image at the position David specifies *(see Step 6 for image first)*
5. Stats row — 3 key benchmark metrics
6. Highlight box — editorial take / implications
7. Pull quote — a memorable line from the paper or analysis
8. Closing paragraph — what to watch for next

Target **400–600 words** in the body.

### Step 6 — Handle the Image (CRITICAL — READ CAREFULLY)

**This is the step that used to block the process. Follow exactly.**

#### What does NOT work:
- Pasting an image inline in the Claude chat — Claude can see it visually but it never hits the filesystem and cannot be committed to GitHub
- Trying to upload via the GitHub "Add file" button from within the agent flow

#### What WORKS — the GitHub drag-drop method:

1. **David opens this URL in Chrome:**
   `https://github.com/solosevn/trainingrun-site/upload/main/assets/news`

2. **David drags the image file from Finder directly onto the GitHub drop zone** that appears on that page

3. The file appears staged with its original filename (e.g., `GxyPU.jpg`) — do NOT rename it

4. Claude sets the commit message to: `Add paper NNN image ([original-filename])`

5. Click "Commit changes" — image is now live at `assets/news/[original-filename]`

6. The article HTML references the image using that exact filename:
   ```html
   <img src="assets/news/GxyPU.jpg" alt="...">
   ```

**Timing:** Upload the image BEFORE committing the article HTML, so the image is live when the article is published.

**If no image is available yet:** Build and get approval on the article first. Upload image after approval. Update the `src` path in the article before the final commit.

### Step 7 — APPROVAL GATE

**STOP. Do not commit to main until David has reviewed and approved the article.**

Present the completed article for review. David must confirm:
- Headline and deck are accurate
- Body content is correct and complete
- Image is uploaded and path is correct
- Tags are appropriate
- No `{{...}}` placeholder tokens remain

Only proceed to Step 8 after receiving explicit approval.

### Step 8 — Commit the Article File

Using the GitHub web editor (via Chrome extension browser workflow):

1. Navigate to: `https://github.com/solosevn/trainingrun-site/new/main`
2. Type the filename: `day-NNN.html`
3. Inject the full article HTML into the CodeMirror editor using JS:
   ```javascript
   const view = document.querySelector('.cm-content').cmView.view;
   // Note: use .cmView.view OR .cmTile.view — check which is available
   view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: content } });
   ```
4. Click "Commit changes..." to open the dialog
5. Set commit message: `Publish day-NNN: [short headline]`
6. Select "Commit directly to the main branch"
7. Click the green "Commit changes" button

### Step 9 — Update news.html

After the article is committed, update `news.html`:

1. Navigate to: `https://github.com/solosevn/trainingrun-site/edit/main/news.html`
2. Replace full content with updated version that includes the new card

**New card goes at the TOP of `.papers-container`, before all existing cards:**

```html
<a href="day-008.html" class="paper-card">
  <div class="paper-meta">
    <span class="paper-badge">Paper 008</span>
    <span class="paper-date">March 6, 2026</span>
    <span class="paper-tag">[Topic]</span>
    <span class="paper-new">New</span>
  </div>
  <div class="paper-title">[Full headline]</div>
  <div class="paper-desc">[One-sentence description]</div>
  <div class="paper-footer">
    <div class="paper-stats">
      <div class="paper-stat"><strong>[Stat 1]</strong> [label]</div>
      <div class="paper-stat"><strong>[Stat 2]</strong> [label]</div>
      <div class="paper-stat"><strong>[Stat 3]</strong> [label]</div>
    </div>
    <div class="paper-cta">Read Briefing →</div>
  </div>
</a>
```

**Also update in news.html:**
1. Paper counter: `<span class="paper-count">N papers published</span>` — increment N
2. Remove `<span class="paper-new">New</span>` from the previous article's card
3. Advance coming-soon placeholders to next two unpublished numbers

Commit message: `Add Paper NNN to news listing, update count to N`

### Step 10 — Verify Deployment

GitHub Pages + Cloudflare CDN deploys within ~60–90 seconds. Verify:

- `trainingrun.ai/day-NNN.html` loads correctly
- Image displays (not broken)
- `trainingrun.ai/news.html` shows the new card at the top with NEW badge
- Previous article nav link works
- No `{{...}}` tokens visible anywhere

**CDN cache note:** If news.html still shows the old version, append `?v=NNN` to the URL to bypass cache and confirm the new content is actually deployed. The plain URL will clear within a few minutes.

---

## Branding Standards

### Color System

| Variable | Value | Usage |
|---|---|---|
| `--cyan` | `#00d4ff` | Primary accent, headline highlights, links |
| `--cyan-glow` | `rgba(0, 212, 255, 0.3)` | Glow effects |
| `--amber` | `#f59e0b` | Secondary accent, tag badges |
| `--bg-darker` | `#050510` | Page background |
| `--bg-dark` | `#0a0a1a` | Card/section backgrounds |
| `--bg-card` | `#111128` | Elevated card surfaces |
| `--text-primary` | `#e2e8f0` | Main body text |
| `--text-secondary` | `#94a3b8` | Subdued/meta text |

### Headline Styling

Every headline has 1–3 impactful words in cyan using `<span class="cyan">`:

```html
Coding Agents Just Got Much More <span class="cyan">Trustworthy</span>
```

The `.cyan` class must be defined in the article's `<style>` block:
```css
.cyan { color: var(--cyan); text-shadow: 0 0 20px rgba(0, 212, 255, 0.4); }
```

### Tag Badge Format

Use the `article-tag` class — NOT `tag`:

```html
<span class="article-tag">🧠 Agents</span>
<span class="article-tag">🔬 Research</span>
<span class="article-tag">🔒 Safety</span>
```

**Critical:** `article-tag` renders amber pill badges. `tag` renders plain white text. Always use `article-tag`.

### Standard Emoji-Tag Pairs

| Emoji | Tag | When to use |
|---|---|---|
| 🤖 | AI | General AI/ML topics |
| 🔬 | Research | Academic papers, experimental results |
| 🧠 | Agents | Autonomous agents, tool use, agentic systems |
| 📖 | Open Source | Open-source releases |
| ⚡ | Efficiency | Optimization, speed improvements |
| 🗺️ | Mobility | Navigation, spatial reasoning |
| 🏗️ | Infrastructure | Training infrastructure, compute |
| 💬 | NLP | Language models, text generation |
| 👁️ | Vision | Computer vision, multimodal |
| 🔒 | Safety | Alignment, safety, red-teaming |

---

## Article Body HTML Components

### Standard Paragraph
```html
<p>Your paragraph text here.</p>
```

### Callout Box (use once, near top)
```html
<div class="callout">
  <p><strong>KEY FINDING:</strong> The highlighted finding with specific numbers.</p>
</div>
```

### Stats Row
```html
<div class="stats-row">
  <div class="stat-card">
    <span class="stat-value">93%</span>
    <span class="stat-label">Accuracy on real patches</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">87%</span>
    <span class="stat-label">Code Q&A accuracy</span>
  </div>
  <div class="stat-card">
    <span class="stat-value">+12pp</span>
    <span class="stat-label">Fault localization gain</span>
  </div>
</div>
```

### Highlight Box
```html
<div class="highlight-box">
  <p>Editorial take or implication paragraph here.</p>
</div>
```

### Pull Quote
```html
<blockquote class="pull-quote">
  <p>"The memorable line from the paper or analysis."</p>
  <cite>— Author, Institution, Year</cite>
</blockquote>
```

### Article Figure
```html
<figure class="article-figure">
  <div class="figure-img-wrap">
    <img src="assets/news/GxyPU.jpg" alt="Brief description">
  </div>
  <div class="figure-caption"><strong>Figure 1:</strong> Caption text here.</div>
</figure>
```

---

## Voice and Tone

- **Direct** — Lead with the finding. First sentence tells you what happened.
- **Precise** — Cite specific numbers. "87.3% accuracy" not "strong performance."
- **Contextual** — Always explain why it matters for practitioners.
- **Honest** — Note limitations. One sentence is enough.
- **Short** — 400–600 words. Dense and readable beats long and padded.

**Never use:** "groundbreaking", "revolutionary", "significant improvement", "it's worth noting that"
**Always include:** 3+ specific numbers, the paper's key limitation, one forward-looking sentence

---

## Publishing via GitHub Web Editor (Chrome Extension Workflow)

All edits made through `github.com/solosevn/trainingrun-site`. No git CLI required.

### CodeMirror Editor — Correct Selector

```javascript
// CORRECT — use .cm-content, not .cm-editor
const cmContent = document.querySelector('.cm-content');
const view = cmContent.cmView?.view || cmContent.cmTile?.view;

view.dispatch({
  changes: { from: 0, to: view.state.doc.length, insert: newContent }
});
```

### Setting Commit Message Programmatically

```javascript
const input = document.querySelector('input[aria-label="Commit message"]');
input.value = 'Your commit message here';
input.dispatchEvent(new Event('input', { bubbles: true }));
```

---

## Full Checklist

```
[ ] Article content received and parsed
[ ] Next article number determined
[ ] Article HTML built from day-template.html
[ ] All 20 placeholders replaced — zero {{...}} tokens remain
[ ] .cyan class added to <style> block
[ ] Headline has 1-3 words in cyan using <span class="cyan">
[ ] Tags use article-tag class (NOT tag) with emoji prefixes
[ ] Image uploaded via GitHub drag-drop to assets/news/
[ ] Image src path in article matches exact committed filename
[ ] DAVID APPROVAL RECEIVED
[ ] Article committed: day-NNN.html → main branch
[ ] news.html updated:
    [ ] New card added at top of .papers-container
    [ ] Paper counter incremented
    [ ] "New" badge moved to latest article only
    [ ] Coming-soon placeholders advanced to next two numbers
[ ] news.html committed to main branch
[ ] Deployment verified:
    [ ] day-NNN.html loads with image
    [ ] news.html shows new card (use ?v=NNN if CDN cached)
    [ ] Nav links work (prev article)
    [ ] No broken placeholder tokens
```

---

## Error Reference

| Error | Cause | Fix |
|---|---|---|
| `{{...}}` visible on page | Placeholder not replaced | Search HTML for `{{` and fill all |
| Broken image after commit | CDN cache or wrong filename | Wait 90s; verify filename matches exactly (case-sensitive) |
| Cards stretched full-width | `.papers-container` wrapper broken | All cards must be inside this div |
| Tags show as plain white | Used `tag` instead of `article-tag` | Replace class name |
| "Trustworthy" not cyan | `.cyan` class missing from `<style>` | Add: `.cyan { color: var(--cyan); text-shadow: 0 0 20px rgba(0, 212, 255, 0.4); }` |
| news.html showing old version | Cloudflare CDN cache | Append `?v=NNN` to URL to verify; clears within ~2 min |
| cmTile not found | Wrong CodeMirror selector | Use `.cm-content` not `.cm-editor` |

---

## Future State — Daily News Agent

This process is currently run manually with Claude. The target state is a fully autonomous Daily News Agent that:

1. Sources a paper daily from arXiv or curated feed
2. Reads the paper in full
3. Writes the article using this process
4. Sends David a Telegram message: *"Paper NNN ready for review: [title] — [preview link]"*
5. Waits for David's approval signal
6. On approval: commits article, updates news.html, sends confirmation
7. Logs the run in RUN-LOG.md

**Human gate is permanent.** The agent never publishes without David's explicit sign-off.

See: `context-vault/agents/trainingrun/daily-news/` for agent file structure.

---

*This process is designed to take under 10 minutes per article once content and image are provided.*
