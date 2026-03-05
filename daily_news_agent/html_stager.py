"""
Daily News Agent — HTML Stager
================================
Creates day-NNN.html from the article template.
Reads news.html to determine the next paper number.
Prepares the news.html card update.
"""

import re
import datetime
import requests
from pathlib import Path
from config import (
    GITHUB_RAW_BASE, GITHUB_TOKEN, STAGING_DIR,
    ARTICLE_TEMPLATE_PATH, NEWS_INDEX_PATH, ARTICLE_PREFIX,
    IMAGE_DIR, SIGNATURE_PATH, TR_REPO_PATH
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
            return 8  # Safe default: Paper 008 (7 exist)

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
        return _fallback_template()


def stage_article(article_data: dict, paper_number: int) -> dict:
    """
    Create the day-NNN.html file from template + article data.

    article_data should contain:
      - headline, subtitle, category, date, article_html, citation

    Returns dict with:
      - html_content: the full HTML page
      - filename: "day-008.html"
      - paper_number: 8
      - local_path: path to staged file
    """
    template = get_article_template()
    today = datetime.date.today()
    date_str = article_data.get("date", today.strftime("%B %d, %Y"))
    filename = f"{ARTICLE_PREFIX}{paper_number:03d}.html"
    cache_bust = int(today.strftime("%Y%m%d"))

    # Build citation HTML
    citation_html = ""
    if article_data.get("citation"):
        citation_lines = article_data["citation"].strip().split("\n")
        citation_html = '<div class="sources">\n<h3>Sources & Further Reading</h3>\n'
        for line in citation_lines:
            line = line.strip()
            if line:
                # Convert URLs to links
                line = re.sub(
                    r'(https?://\S+)',
                    r'<a href="\1" target="_blank" rel="noopener">\1</a>',
                    line
                )
                citation_html += f"<p>{line}</p>\n"
        citation_html += "</div>"

    # Build the full article body
    article_body = article_data.get("article_html", "")

    # Replace image placeholders with proper tags
    article_body = re.sub(
        r'<!--\s*IMAGE:\s*(.*?)\s*-->',
        f'<div class="article-image"><img src="{IMAGE_DIR}paper-{paper_number:03d}.jpg?v={cache_bust}" '
        r'alt="\1" /><p class="image-caption">\1</p></div>',
        article_body
    )

    # Template substitutions
    html = template
    replacements = {
        "{{TITLE}}": article_data.get("headline", "Daily News"),
        "{{SUBTITLE}}": article_data.get("subtitle", ""),
        "{{CATEGORY}}": article_data.get("category", "AI Research"),
        "{{DATE}}": date_str,
        "{{PAPER_NUMBER}}": f"{paper_number:03d}",
        "{{ARTICLE_BODY}}": article_body,
        "{{CITATION}}": citation_html,
        "{{SIGNATURE}}": f'<img src="{SIGNATURE_PATH}?v={cache_bust}" alt="David Solomon" class="signature" />',
        "{{CACHE_BUST}}": str(cache_bust),
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # If template didn't have our placeholders, build from scratch
    if "{{TITLE}}" in html or not template.strip():
        html = _build_article_html(article_data, paper_number, date_str, cache_bust)

    # Save to staging
    staged_path = STAGING_DIR / filename
    staged_path.write_text(html, encoding="utf-8")

    return {
        "html_content": html,
        "filename": filename,
        "paper_number": paper_number,
        "local_path": str(staged_path),
    }


def build_news_card(article_data: dict, paper_number: int) -> str:
    """
    Build the news.html card HTML for this article.
    This gets inserted at the TOP of the card list.
    """
    today = datetime.date.today().strftime("%B %d, %Y")
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
                <a href="{filename}" class="read-more">Read Article →</a>
            </div>"""

    return card


def _build_article_html(article_data: dict, paper_number: int, date_str: str, cache_bust: int) -> str:
    """
    Fallback: build article HTML from scratch if template has no placeholders.
    Follows the same structure as existing day-001 through day-007.
    """
    headline = article_data.get("headline", "Daily News")
    subtitle = article_data.get("subtitle", "")
    category = article_data.get("category", "AI Research")
    body = article_data.get("article_html", "")
    citation = article_data.get("citation", "")

    # Build citation HTML
    citation_html = ""
    if citation:
        citation_lines = citation.strip().split("\n")
        citation_html = '<div class="sources">\n<h3>Sources & Further Reading</h3>\n'
        for line in citation_lines:
            line = line.strip()
            if line:
                line = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', line)
                citation_html += f"<p>{line}</p>\n"
        citation_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper {paper_number:03d}: {headline} | TrainingRun.AI</title>
    <meta name="description" content="{subtitle}">
    <meta property="og:title" content="Paper {paper_number:03d}: {headline}">
    <meta property="og:description" content="{subtitle}">
    <meta property="og:image" content="https://trainingrun.ai/{IMAGE_DIR}paper-{paper_number:03d}.jpg">
    <meta property="og:type" content="article">
    <link rel="stylesheet" href="assets/style.css?v={cache_bust}">
</head>
<body>
    <nav class="article-nav">
        <a href="news.html" class="back-link">← Back to News</a>
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

        {citation_html}

        <footer class="article-footer">
            <div class="signature-block">
                <img src="{SIGNATURE_PATH}?v={cache_bust}" alt="David Solomon" class="signature" />
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


def _fallback_template() -> str:
    """Return empty template if day-template.html can't be loaded."""
    return ""


if __name__ == "__main__":
    num = get_next_paper_number()
    print(f"[HTMLStager] Next paper number: {num:03d}")
