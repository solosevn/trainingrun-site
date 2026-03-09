# CEO-LEARNING-004: news.html Duplication, Missing Paper 011, Wrong Paper Count

**Date:** March 9, 2026
**Issues Covered:** Fix #4 (news.html doubled), Fix #5 (Paper 011 card format wrong), Fix #6 (Paper count says 9, should be 11)
**Severity:** HIGH — Live production page broken, visible to all visitors
**Root Cause:** V10 repo restructure appended new content instead of replacing existing file
**Status:** RESOLVED — Commit `276a17a` on `main`, verified live at trainingrun.ai/news.html

---

## 1. What Happened

After the V10 repo restructure on March 8, 2026, the `news.html` file contained **two complete HTML documents stacked on top of each other**. The file was 644 lines / 34.9 KB when it should have been ~326 lines / ~18 KB.

**Structure of the broken file:**
- **Copy 1 (lines 1–316):** First complete `<!DOCTYPE html>` through `</html>`. Had Papers 010 through 001 (missing Paper 011). Had stale "coming soon" placeholder divs for Papers 010 and 011. Paper count said "9 papers published."
- **Copy 2 (lines 317–644):** Second complete `<!DOCTYPE html>` through `</html>`. Had Paper 011 (new card, but with empty description), a differently-formatted Paper 010, then Papers 008 through 001. Also said "9 papers published."

**What visitors saw:** The page rendered Copy 1 first (Papers 010–001), then the footer, then the entire page repeated with Copy 2 below it (Paper 011, 010, 008–001). It looked like the page was duplicated. The count said "9 papers" even though 11 existed.

**What was missing from BOTH copies:** Paper 009 was missing from both. Copy 1 jumped from 010 to 008 (the HTML comment said "PAPER 008" but it was actually Paper 009's content at day-009.html). Copy 2 also went 008 to 007. Paper 009 was actually present in Copy 1 — it was just mislabeled in the HTML comment. The link `day-009.html` was correct.

---

## 2. How We Diagnosed It

### Step 1: Visual inspection of live page
Navigated to `trainingrun.ai/news.html`. Saw Papers 010 through 001, "9 papers published." Scrolled past Paper 001 and found the entire page duplicated below with a second copy starting from Paper 011.

### Step 2: Raw HTML analysis
Opened the file on GitHub. Key findings:
- **644 lines, 34.9 KB** — roughly double expected size
- Two `<!DOCTYPE html>` declarations (lines 1 and 317)
- Two `</html>` tags (lines 316 and 644)
- Paper count on line 84: `<span class="paper-count">9 papers published</span>`
- "Coming soon" placeholders at lines 299–306 for Papers 010 and 011
- Paper 011 card existed only in Copy 2 (lines 406–425) with an empty `paper-desc` div

### Step 3: Cross-reference with day-011.html
Read `day-011.html` (484 lines) to get the proper description for Paper 011. Title: "How Robots Are Learning to Remember Like Us." Meta description: "A new study shows robots getting better at memory for everyday tasks." Article content discusses the RoboMME benchmark.

---

## 3. Root Cause

The V10 restructure process **appended** the updated news.html content to the end of the existing file instead of **replacing** it. This is the same class of bug as the `git pull --rebase -X theirs` issue documented in CEO-LEARNING-003 — the restructure tooling did not properly handle file updates.

Specifically:
- Someone (likely TRSitekeeper or a manual process) generated an updated news.html with Paper 011 added
- Instead of overwriting the existing file, the new version was concatenated after the old version
- Both versions had different content: Copy 1 was the old version (no Paper 011, coming-soon placeholders), Copy 2 was the new version (has Paper 011, no placeholders, but different card formatting for Paper 010)

---

## 4. The Fix

**Strategy:** Take Copy 1 as the base (lines 1–316) since it had consistent card formatting, then surgically add what was missing and remove what was stale.

### Changes made:
1. **Added Paper 011 card** before Paper 010 (inserted after line 88, before `<!-- PAPER 010 -->`). Used proper card format matching all other papers. Wrote a full description based on day-011.html content: "A new study introduces RoboMME, a benchmark that tests whether robots can remember and apply knowledge across everyday tasks. Most robots today forget everything between jobs — this research measures how close we are to fixing that."

2. **Removed "coming soon" placeholders** (old lines 298–306). These were divs for Papers 010 and 011 that said "Next briefing coming soon" — both papers are now real published papers.

3. **Updated paper count** from `9 papers published` to `11 papers published` on line 84.

4. **Deleted entire Copy 2** (old lines 317–644). The complete second HTML document was removed.

### Result:
- **Before:** 644 lines / 34.9 KB / 2 DOCTYPE declarations / 2 `</html>` tags / duplicate page
- **After:** 326 lines / 17.8 KB / 1 DOCTYPE / 1 `</html>` / clean single page
- Papers in order: 011, 010, 009, 008, 007, 006, 005, 004, 003, 002, 001

---

## 5. How It Was Pushed — Critical Technical Lessons

This fix required editing a file through GitHub's web editor (CodeMirror 6). Several approaches were tried. **This section is critical for any agent working with GitHub's editor.**

### Approach 1: `document.execCommand('selectAll')` + `insertText` — FAILED
```javascript
cmContent.focus();
document.execCommand('selectAll', false, null);
document.execCommand('insertText', false, newContent);
```
**Result:** Created a 970-line file. The `selectAll` only selected the **visible/rendered portion** of the CodeMirror editor. CodeMirror 6 uses **virtual scrolling** — it only renders DOM nodes for lines visible in the viewport. Off-screen lines exist in CodeMirror's internal state but NOT in the DOM. So `selectAll` grabbed ~100 visible lines, `insertText` replaced only those, and the remaining ~545 off-screen lines stayed. The new content got prepended to the old content.

**Lesson:** NEVER use `document.execCommand('selectAll')` with CodeMirror 6. It operates on the DOM, not on CodeMirror's document model.

### Approach 2: `Selection API` with `range.selectNodeContents()` — FAILED
```javascript
const sel = window.getSelection();
const range = document.createRange();
range.selectNodeContents(cmContent);
sel.addRange(range);
```
**Result:** Only selected 9,933 chars (visible portion). Same virtual scrolling problem.

### Approach 3: Access CodeMirror view via `cmView` property — FAILED
```javascript
// Tried: element.cmView.view.dispatch({changes: {from: 0, to: docLength, insert: newContent}})
```
**Result:** `cmView` property was not accessible on any DOM element. GitHub's CodeMirror integration doesn't expose the view object to external scripts.

### Approach 4: GitHub REST API with PUT — FAILED
```javascript
fetch('https://api.github.com/repos/.../contents/news.html', {method: 'PUT', body: ...})
```
**Result:** "Requires authentication." The browser session cookies don't authenticate GitHub API calls. Would need a personal access token.

### Approach 5: Clipboard + Keyboard shortcuts — SUCCEEDED ✅
```javascript
// Step 1: Write fixed content to clipboard
navigator.clipboard.writeText(fixedContent);

// Step 2: Click inside the editor to focus it
// Step 3: Press Cmd+A (keyboard shortcut, handled by CodeMirror internally)
// Step 4: Press Cmd+V (paste from clipboard)
```
**Why this works:** When `Cmd+A` is pressed as a keyboard event (not a DOM API call), **CodeMirror intercepts it** and selects the entire document in its internal state — including all virtually-scrolled off-screen lines. Then `Cmd+V` pastes the clipboard content, replacing the full selection.

**This is the proven pattern for replacing content in GitHub's CodeMirror 6 editor:**
1. `navigator.clipboard.writeText(newContent)` — load content to clipboard
2. Click inside the editor to ensure focus
3. `Cmd+A` keyboard shortcut — CodeMirror selects ALL content (not just visible)
4. `Cmd+V` keyboard shortcut — paste replaces everything

### Important note on content reconstruction:
When navigating away from the edit page and back, `window` variables are lost. The fix content had to be rebuilt each time by:
1. Fetching raw file from `https://raw.githubusercontent.com/...` (note: has CDN cache delay)
2. Or fetching via GitHub API: `https://api.github.com/repos/.../contents/news.html` (real-time but returns base64)
3. Programmatically extracting/fixing the content in JavaScript
4. Storing in `window._fixedNews` for the clipboard step

---

## 6. Verification

After commit `276a17a` deployed to GitHub Pages (~60 seconds):

**Live page at trainingrun.ai/news.html:**
- "11 papers published" displays correctly in top right
- Paper 011 appears first: "How Robots Are Learning to Remember Like Us" with full description, AI + Research tags, "New" badge, March 9, 2026 date, links to day-011.html
- Paper 010 follows immediately: "GPT-5.4-PRO Shows Major Gains in Solving Physics Problems"
- Papers 009 through 001 in correct descending order
- Footer appears once at the bottom: "© 2026 TrainingRun.AI · Leaderboard · Independent AI Research"
- No duplicate content below Paper 001
- No "coming soon" placeholders visible

---

## 7. Prevention

### Immediate:
- Any process that updates `news.html` (TRSitekeeper, manual, or any agent) must **replace** the file, never append to it
- After any update to news.html, verify: single `<!DOCTYPE html>`, single `</html>`, correct paper count matches number of paper cards

### Structural:
- The news page should be generated from a data source (JSON/YAML of papers) rather than hand-edited HTML. This would prevent duplication, miscounts, and formatting inconsistencies.
- Add a pre-commit or CI check that validates: no duplicate DOCTYPE declarations in any HTML file, paper count matches actual paper card count

### Agent instructions:
- When adding a new paper to news.html: insert the new card HTML before the first existing paper card, update the count, and verify the file has exactly one `<!DOCTYPE>` and one `</html>` before committing
- Never append to HTML files. Always read the current file, modify in memory, and write the complete replacement.

---

## 8. Related Learning Documents

- **CEO-LEARNING-002:** DDP pipeline path breakage from V10 restructure
- **CEO-LEARNING-003:** status.json rebase overwrite (`git pull --rebase -X theirs` clobbering data)
- **Common thread:** The V10 restructure broke multiple systems through improper file handling — paths, overwrites, and appends instead of replacements. All three issues stem from the restructure tooling not accounting for existing file content.

---

## 9. Key Takeaways for Any Agent

1. **GitHub CodeMirror 6 editor:** Use clipboard + keyboard shortcuts (`Cmd+A`, `Cmd+V`), never DOM-level `selectAll`/`insertText`. Virtual scrolling means DOM operations only affect visible lines.

2. **File duplication detection:** If an HTML file is unexpectedly large, check for multiple `<!DOCTYPE>` or `</html>` tags. This indicates concatenation instead of replacement.

3. **Always verify live after pushing to GitHub Pages.** The repo IS the live site. Push to main = live in ~60 seconds. Check the actual rendered page, not just the source.

4. **Paper descriptions matter.** When adding a paper card to news.html, always read the corresponding `day-XXX.html` file to write a proper 2-sentence description. Don't leave `paper-desc` empty.

5. **Count what you see.** If the page says "N papers published," count the actual paper cards. They should match. If they don't, fix both the cards and the count.
