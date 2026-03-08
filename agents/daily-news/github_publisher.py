"""
Daily News Agent — GitHub Publisher
=====================================
Commits article HTML and updates news.html via GitHub REST API.
No git CLI needed — pure API calls.
"""

import base64
import requests

from config import GITHUB_TOKEN, GITHUB_API_BASE, REPO_BRANCH, NEWS_INDEX_PATH


def _headers() -> dict:
    """GitHub API request headers."""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }


def get_file(path: str) -> dict:
    """
    Get a file from the repo.
    Returns dict with 'content' (decoded) and 'sha'.
    """
    url = f"{GITHUB_API_BASE}/contents/{path}?ref={REPO_BRANCH}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code == 404:
        return {"content": "", "sha": None}
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return {"content": content, "sha": data["sha"]}


def create_or_update_file(path: str, content: str, message: str, sha: str = None) -> dict:
    """
    Create or update a file in the repo via GitHub API.
    If sha is provided, it's an update. Otherwise, it's a create.
    """
    url = f"{GITHUB_API_BASE}/contents/{path}"
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": message,
        "content": encoded,
        "branch": REPO_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def publish_article(article_filename: str, article_html: str,
                    paper_number: int, title: str,
                    article_data: dict = None) -> dict:
    """
    Publish the article to GitHub:
      1. Create day-NNN.html
      2. Update news.html with new card at top
    Returns dict with status and URLs.
    """
    results = {"steps": [], "errors": []}

    if not GITHUB_TOKEN:
        return {"errors": ["GITHUB_TOKEN not set"]}

    # Step 1: Commit the article HTML
    try:
        commit_msg = f"Paper {paper_number:03d}: {title}"
        result = create_or_update_file(
            path=article_filename,
            content=article_html,
            message=commit_msg,
        )
        article_url = f"https://trainingrun.ai/{article_filename}"
        results["steps"].append(f"\u2705 Committed {article_filename}")
        results["article_url"] = article_url
    except Exception as e:
        results["errors"].append(f"Failed to commit article: {e}")
        return results

    # Step 2: Update news.html with card from build_news_card (V2.0)
    try:
        update_news_index(article_filename, paper_number, title,
                          article_data=article_data)
        results["steps"].append("\u2705 Updated news.html")
    except Exception as e:
        results["errors"].append(f"Failed to update news.html: {e}")

    return results


def update_news_index(article_filename: str, paper_number: int, title: str,
                      subtitle: str = "", category: str = "AI Research",
                      article_data: dict = None) -> None:
    """
    Add a new card at the TOP of news.html for the published article.

    Uses build_news_card from html_stager.py for the V2.0 card format
    (matching Papers 001-007 standard structure). Falls back to inline
    template only if html_stager import fails.
    """
    from html_stager import build_news_card

    # Get current news.html
    file_data = get_file(NEWS_INDEX_PATH)
    if not file_data["content"]:
        raise RuntimeError("news.html not found in repo")

    current_html = file_data["content"]
    sha = file_data["sha"]

    # Build article_data dict for build_news_card
    if article_data is None:
        article_data = {}
    # Ensure required fields are present
    article_data.setdefault("category", category)
    article_data.setdefault("headline", title)
    article_data.setdefault("subtitle", subtitle)

    # Use the V2.0 card builder from html_stager.py (single source of truth)
    new_card = build_news_card(article_data, paper_number)

    # Find the insertion point — after the container opening tag
    insertion_patterns = [
        ('<!-- Paper ', new_card + "\n"),
        ('<!-- PAPER ', new_card + "\n"),
        ('<a href="day-', new_card + "\n"),
        ('<div class="paper-card">', new_card + "\n"),
        ('<div class="papers-container">', None),
    ]

    inserted = False
    for pattern, replacement in insertion_patterns:
        idx = current_html.find(pattern)
        if idx != -1:
            if replacement:
                updated_html = current_html[:idx] + replacement + current_html[idx:]
            else:
                end_idx = current_html.find(">", idx) + 1
                updated_html = current_html[:end_idx] + "\n" + new_card + current_html[end_idx:]
            inserted = True
            break

    if not inserted:
        raise RuntimeError("Could not find insertion point in news.html")

    # Commit updated news.html
    create_or_update_file(
        path=NEWS_INDEX_PATH,
        content=updated_html,
        message=f"Update news.html: add Paper {paper_number:03d}",
        sha=sha,
    )


def commit_vault_file(path: str, content: str, message: str) -> dict:
    """
    Commit an updated vault file (e.g., RUN-LOG.md, LEARNING-LOG.md).
    """
    file_data = get_file(path)
    return create_or_update_file(
        path=path,
        content=content,
        message=message,
        sha=file_data.get("sha"),
    )


# ──────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────
def test_github_connection():
    """Quick test: verify GitHub API works by reading a file."""
    if not GITHUB_TOKEN:
        print("[GitHubPublisher] \u274c GITHUB_TOKEN not set")
        return False
    try:
        file_data = get_file("README.md")
        if file_data.get("sha"):
            print(f"[GitHubPublisher] \u2705 GitHub API connected (README.md sha: {file_data['sha'][:8]})")
            return True
        # Try news.html instead
        file_data = get_file(NEWS_INDEX_PATH)
        if file_data.get("sha"):
            print(f"[GitHubPublisher] \u2705 GitHub API connected (news.html found)")
            return True
        print("[GitHubPublisher] \u274c Could not read any files from repo")
        return False
    except Exception as e:
        print(f"[GitHubPublisher] \u274c GitHub API failed: {e}")
        return False


if __name__ == "__main__":
    test_github_connection()
