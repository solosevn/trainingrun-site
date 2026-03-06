"""
Daily News Agent — HTML Stager
================================
Creates day-NNN.html from the article template.
Reads news.html to determine the next paper number.
Prepares the news.html card update.

V2.0 — Rewritten to match day-template.html placeholders.
"""

import re
import datetime
import requests
from pathlib import Path
from urllib.parse import quote

from config import (
    GITHUB_RAW_BASE,
    GITHUB_TOKEN,
    STAGING_DIR,
    ARTICLE_TEMPLATE_PATH,
    NEWS_INDEX_PATH,
    ARTICLE_PREFIX,
    IMAGE_DIR,
    SIGNATURE_PATH,
    TR_REPO_PATH
)


def get_next_paper_number() -> int:
    """
    Read news.html to determine the next paper number.
    Finds highest day-NNN.html reference + 1.
    Tries local repo first, then GitHub.
    """
    news_html = ""

    # Try local
    local_path = TR_REPO_PATH / NEWS_INDEX_PATH
    if local_path.exists():
        news_html = local_path.read_text(encoding="utf-8")
    else:
        # Fetch from GitHub
        url = f"{GITHUB_RAW_BASE}/{NEWS_INDEX_PATH}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            news_html = resp.text
        except Exception as e:
            print(f"[HTMLStager] WARNING: Could not fetch news.html: {e}")
            return 8  # Safe default

    # Find all day-NNN references
    matches = re.findall(r'day-(\d{3})\.html', news_html)
    if matches:
        highest = max(int(m) for m in matches)
        return highest + 1
    return 8  # Fallback


def get_article_template() -> str:
    """
    Load day-template.html from the repo.
    """
    # Try local
    local_path = TR_REPO_PATH / ARTICLE_TEMPLATE_PATH
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")

    # Fetch from GitHub
    url = f"{GITHUB_RAW_BASE}/{ARTICLE_TEMPLATE_PATH}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[HTMLStager] WARNING: Could not fetch template: {e}")
        return ""


# ----------------------------------------------------------------
# CITATION PARSER - Extract paper title, authors, institutions
# ----------------------------------------------------------------
def parse_citation(citation_text: str) -> dict:
    """
    Parse the citation block from Grok's article output.
    Expected format:
        Source Paper: [title]
        Authors: [names, institution(s)]
        Published: [date] | [venue]
        Link: [url]
    Returns dict with: paper_title, authors, institutions, paper_url, citation_line
    """
    result = {
        "paper_title": "",
        "authors": "",
        "institutions": "",
        "paper_url": "",
        "citation_line": "",
    }

    if not citation_text:
        return result

    lines = citation_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        lower = line.lower()

        if lower.startswith("source paper:") or lower.startswith("paper:") or lower.startswith("title:"):
            result["paper_title"] = re.sub(r'^(source paper|paper|title)\s*:\s*', '', line, flags=re.IGNORECASE).strip()
        elif lower.startswith("authors:") or lower.startswith("author:"):
            raw = re.sub(r'^authors?\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            inst_match = re.search(r'[\(\[](.+?)[\)\]]', raw)
            if inst_match:
                result["institutions"] = inst_match.group(1).strip()
                result["authors"] = raw[:inst_match.start()].strip().rstrip(',').rstrip('\u2014').rstrip('-').strip()
            else:
                result["authors"] = raw
        elif lower.startswith("institution") or lower.startswith("affiliation"):
            result["institutions"] = re.sub(r'^(institutions?|affiliations?)\s*:\s*', '', line, flags=re.IGNORECASE).strip()
        elif lower.startswith("published:"):
            result["citation_line"] = re.sub(r'^published\s*:\s*', '', line, flags=re.IGNORECASE).strip()
        elif lower.startswith("link:") or lower.startswith("url:"):
            url = re.sub(r'^(link|url)\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            result["paper_url"] = url

    if not result["citation_line"] and result["paper_title"]:
        result["citation_line"] = result["paper_title"]

    return result


# ----------------------------------------------------------------
# TAG HTML BUILDER
# ----------------------------------------------------------------
def build_tags_html(category: str) -> str:
    """
    Generate <span> tags for the article meta section.
    Maps categories to relevant tag sets.
    """
    tag_map = {
        "AI Research": ["AI", "Research"],
        "AI Policy": ["AI", "Policy", "Regulation"],
        "Agents": ["Agents", "AI"],
        "Open Source": ["Open Source", "AI"],
        "Compute & Infrastructure": ["Compute", "Infrastructure"],
        "Safety": ["Safety", "AI"],
        "Training": ["Training", "AI"],
        "Inference": ["Inference", "AI"],
    }

    tags = tag_map.get(category, [category])
    spans = []
    for tag in tags:
        spans.append(f'<span class="article-tag">{tag}</span>')
    return " ".join(spans)


# ----------------------------------------------------------------
# URL SHORTENER (display only)
# ----------------------------------------------------------------
def shorten_url(url: str) -> str:
    """Create a short display version of a URL."""
    if not url:
        return ""
    short = re.sub(r'^https?://', '', url)
    short = short.rstrip('/')
    if len(short) > 50:
        short = short[:47] + "..."
    return short


# ----------------------------------------------------------------
# MAIN STAGER
# ----------------------------------------------------------------
def stage_article(article_data: dict, paper_number: int) -> dict:
    """
    Create the day-NNN.html file from template + article data.

    article_data should contain:
        - headline, subtitle, category, date, article_html, citation
        - story_url (from selected story)
        - story_title (from selected story)
        - image_url (from image generator, optional)
        - image_caption (from image generator, optional)

    Returns dict with:
        - html_content: the full HTML page
        - filename: "day-008.html"
        - paper_number: 8
        - local_path: path to staged file
    """
    template = get_article_template()
    today = datetime.date.today()

    # Date formats
    date_upper = today.strftime("%B %d, %Y").upper()
    date_upper = re.sub(r' 0(\d)', r' \1', date_upper)
    date_long = today.strftime("%B %d, %Y")
    date_long = re.sub(r' 0(\d)', r' \1', date_long)

    filename = f"{ARTICLE_PREFIX}{paper_number:03d}.html"

    # Article fields
    headline = article_data.get("headline", "Daily News")
    subtitle = article_data.get("subtitle", "")
    category = article_data.get("category", "AI Research")
    article_body = article_data.get("article_html", "")
    citation_raw = article_data.get("citation", "")
    story_url = article_data.get("story_url", "")
    story_title = article_data.get("story_title", headline)

    # Parse citation
    citation = parse_citation(citation_raw)
    paper_title = citation["paper_title"] or story_title
    paper_url = citation["paper_url"] or story_url
    paper_url_short = shorten_url(paper_url)
    paper_authors = citation["authors"] or "See original paper"
    paper_institutions = citation["institutions"] or "See original paper"
    paper_citation = citation["citation_line"] or ""

    # Build tags HTML
    tags_html = build_tags_html(category)

    # Build email share data
    email_subject = quote(f"Paper {paper_number:03d}: {headline} \u2014 TrainingRun.AI")
    email_body = quote(
        f"Check out this article from TrainingRun.AI:\n\n"
        f"{headline}\n{subtitle}\n\n"
        f"https://trainingrun.ai/{filename}"
    )

    # Previous article navigation
    if paper_number > 1:
        prev_num = paper_number - 1
        prev_url = f"{ARTICLE_PREFIX}{prev_num:03d}.html"
        prev_label = f"Paper {prev_num:03d}"
    else:
        prev_url = "news.html"
        prev_label = "All Articles"

    # Insert image into article body if image_url provided
    image_url = article_data.get("image_url", "")
    image_caption = article_data.get("image_caption", "")
    if image_url and article_body:
        figure_html = _build_figure_html(image_url, image_caption, paper_number)
        paragraphs = article_body.split("</p>")
        if len(paragraphs) > 2:
            paragraphs.insert(2, f"\n{figure_html}\n")
            article_body = "</p>".join(paragraphs)
        else:
            article_body = figure_html + "\n" + article_body

    # -- TEMPLATE SUBSTITUTIONS --
    # Match ALL 20 placeholders in day-template.html
    html = template
    replacements = {
        "{{META_TITLE}}":              headline,
        "{{META_DESCRIPTION}}":        subtitle,
        "{{DATE_UPPER}}":              date_upper,
        "{{ARTICLE_NUMBER}}":          f"{paper_number:03d}",
        "{{KICKER}}":                  category.upper(),
        "{{HEADLINE_HTML}}":           headline,
        "{{DECK}}":                    subtitle,
        "{{DATE_LONG}}":               date_long,
        "{{TAGS_HTML}}":               tags_html,
        "{{ARTICLE_BODY_HTML}}":       article_body,
        "{{PAPER_TITLE}}":             paper_title,
        "{{PAPER_URL}}":               paper_url,
        "{{PAPER_URL_SHORT}}":         paper_url_short,
        "{{PAPER_CITATION}}":          paper_citation,
        "{{PAPER_AUTHORS}}":           paper_authors,
        "{{PAPER_INSTITUTIONS}}":      paper_institutions,
        "{{EMAIL_SUBJECT_ENCODED}}":   email_subject,
        "{{EMAIL_BODY_ENCODED}}":      email_body,
        "{{PREV_URL}}":                prev_url,
        "{{PREV_LABEL}}":             prev_label,
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))

    # Verify all placeholders were replaced
    remaining = re.findall(r'\{\{[A-Z_]+\}\}', html)
    if remaining:
        print(f"[HTMLStager] WARNING: Unreplaced placeholders: {remaining}")
        if len(remaining) > 5:
            print("[HTMLStager] Too many unreplaced placeholders - using fallback HTML builder")
            html = _build_article_html(article_data, paper_number, date_long)

    # Save to staging
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    staged_path = STAGING_DIR / filename
    staged_path.write_text(html, encoding="utf-8")

    return {
        "html_content": html,
        "filename": filename,
        "paper_number": paper_number,
        "local_path": str(staged_path),
    }


def _build_figure_html(image_url: str, caption: str, paper_number: int) -> str:
    """Build the figure HTML block for an article image."""
    caption_text = caption or f"Visual representation for Paper {paper_number:03d}"
    return f"""
    <div class="article-figure">
        <div class="figure-img-wrap">
            <img src="{image_url}" alt="{caption_text}" />
        </div>
        <div class="figure-caption">
            <strong>Figure 1:</strong> {caption_text}
        </div>
    </div>"""


def build_news_card(article_data: dict, paper_number: int) -> str:
    """
    Build the news.html card HTML for this article.
    This gets inserted at the TOP of the card list.
    """
    today = datetime.date.today().strftime("%B %d, %Y")
    today = re.sub(r' 0(\d)', r' \1', today)
    filename = f"{ARTICLE_PREFIX}{paper_number:03d}.html"

    card = f"""
    <!-- Paper {paper_number:03d} -->
    <div class="paper-card">
        <div class="paper-header">
            <span class="article-tag">{article_data.get('category', 'AI Research')}</span>
            <span class="paper-date">{today}</span>
        </div>
        <h3><a href="{filename}">Paper {paper_number:03d}: {article_data.get('headline', 'Daily News')}</a></h3>
        <p class="paper-summary">{article_data.get('subtitle', '')}</p>
        <a href="{filename}" class="read-more">Read Article \u2192</a>
    </div>"""

    return card


def _build_article_html(article_data: dict, paper_number: int, date_str: str) -> str:
    """
    Fallback: build article HTML from scratch if template has issues.
    """
    headline = article_data.get("headline", "Daily News")
    subtitle = article_data.get("subtitle", "")
    category = article_data.get("category", "AI Research")
    body = article_data.get("article_html", "")
    citation_raw = article_data.get("citation", "")
    story_url = article_data.get("story_url", "")

    citation = parse_citation(citation_raw)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper {paper_number:03d}: {headline} | TrainingRun.AI</title>
    <meta name="description" content="{subtitle}">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <nav class="article-nav">
        <a href="news.html" class="back-link">\u2190 Back to News</a>
        <a href="index.html" class="home-link">TrainingRun.AI</a>
    </nav>
    <article class="daily-news">
        <header class="article-header">
            <span class="article-tag">{category}</span>
            <h1>{headline}</h1>
            <p class="article-subtitle">{subtitle}</p>
            <div class="article-meta">
                <span class="article-date">{date_str}</span>
                <span class="article-author">By David Solomon</span>
            </div>
        </header>
        <div class="article-body">
            {body}
        </div>
        <div class="credits">
            <h3>Credits &amp; Original Research</h3>
            <p>Source: <strong>{citation['paper_title']}</strong></p>
            <p><strong>Authors:</strong> {citation['authors']}</p>
            <p>Full paper \u2192 <a href="{citation['paper_url'] or story_url}" target="_blank">{shorten_url(citation['paper_url'] or story_url)}</a></p>
        </div>
        <footer class="article-footer">
            <div class="signature-block">
                <img src="{SIGNATURE_PATH}" alt="David Solomon" class="signature" />
                <p class="signature-name">David Solomon</p>
                <p class="signature-title">Founder, TrainingRun.AI</p>
            </div>
        </footer>
    </article>
    <footer class="site-footer">
        <p>&copy; 2026 TrainingRun.AI | <a href="about.html">About</a></p>
    </footer>
</body>
</html>"""


if __name__ == "__main__":
    num = get_next_paper_number()
    print(f"[HTMLStager] Next paper number: {num:03d}")
