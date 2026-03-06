"""
Content Scout — Learning Logger
=================================
Logs scrape cycle data, briefing results, and Daily News Agent feedback.
Follows the same pattern as daily_news_agent/learning_logger.py.

Functions:
  log_scrape_cycle()       — Appends to RUN-LOG.md after each scrape cycle
  log_briefing_result()    — Appends to LEARNING-LOG.md after morning brief
  log_selection_feedback() — Appends to LEARNING-LOG.md when Daily News Agent selects a story
  update_source_weights()  — Recalculates source weights → updates STYLE-EVOLUTION.md
  commit_logs()            — Pushes updated vault files to GitHub

Version: 1.0 | Created: March 6, 2026
"""

import os
import re
import json
import logging
import datetime
import subprocess
from pathlib import Path

logger = logging.getLogger("ContentScout.LearningLogger")

# ─── Configuration ───────────────────────────────────────────────

REPO_PATH = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
VAULT_BASE = "context-vault/agents/trainingrun/daily-news/content-scout"

RUN_LOG_PATH = os.path.join(REPO_PATH, VAULT_BASE, "RUN-LOG.md")
LEARNING_LOG_PATH = os.path.join(REPO_PATH, VAULT_BASE, "LEARNING-LOG.md")
STYLE_EVOLUTION_PATH = os.path.join(REPO_PATH, VAULT_BASE, "STYLE-EVOLUTION.md")

ALL_SOURCES = [
    "arXiv", "Hugging Face", "GitHub Trending", "Reddit",
    "Hacker News", "Lobste.rs", "YouTube", "Newsletters"
]

WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.0
WEIGHT_STEP = 0.1
MIN_FEEDBACK_FOR_SMALL_ADJUST = 5
MIN_FEEDBACK_FOR_LARGE_ADJUST = 10


# ─── RUN-LOG.md — Scrape Cycle Logging ──────────────────────

def log_scrape_cycle(
    sources_hit, items_found, items_after_dedup,
    items_dropped_stale, items_deprioritized,
    per_source, errors
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M CST")
    error_str = ", ".join(errors) if errors else "None"

    entry = f"\n### Cycle {now}\n"
    entry += f"- **Sources hit:** {sources_hit}/8\n"
    entry += f"- **Items found:** {items_found}\n"
    entry += f"- **Items after dedup:** {items_after_dedup}\n"
    entry += f"- **Items dropped (stale >7d):** {items_dropped_stale}\n"
    entry += f"- **Items deprioritized (stale >3d):** {items_deprioritized}\n"
    entry += f"- **Errors:** {error_str}\n"
    entry += "- **Per source:**\n"
    for source in ALL_SOURCES:
        count = per_source.get(source, 0)
        entry += f"  - {source}: {count} items\n"

    try:
        _append_to_file(RUN_LOG_PATH, entry)
        logger.info(f"[LearningLogger] Logged scrape cycle: {items_found} items from {sources_hit} sources")
    except Exception as e:
        logger.error(f"[LearningLogger] Failed to log scrape cycle: {e}")


# ─── LEARNING-LOG.md — Briefing Result Logging ──────────────

def log_briefing_result(
    top_stories, truth_score_range, categories,
    sources, items_dropped_by_ai, ollama_status, xai_status
):
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    entry = f"\n### Brief {now}\n"
    entry += "- **Top 10 stories surfaced:**\n"
    for i, story in enumerate(top_stories[:10], 1):
        title = story.get("title", "Unknown")
        source = story.get("source", "Unknown")
        score = story.get("truth_score", 0)
        verdict = story.get("ai_verdict", "UNVERIFIED")
        category = story.get("category", "general")
        entry += f"  {i}. {title} | Source: {source} | Truth Score: {score} | AI Verdict: {verdict} | Category: {category}\n"

    min_score, max_score = truth_score_range
    entry += f"- **Truth score range:** {min_score}-{max_score}\n"
    entry += f"- **Categories represented:** {', '.join(categories)}\n"
    entry += f"- **Sources represented:** {', '.join(sources)}\n"
    entry += f"- **Items dropped by AI verification:** {items_dropped_by_ai}\n"
    entry += f"- **Ollama status:** {ollama_status}\n"
    entry += f"- **xAI status:** {xai_status}\n"

    try:
        _append_to_file(LEARNING_LOG_PATH, entry)
        logger.info(f"[LearningLogger] Logged briefing result: {len(top_stories)} stories")
    except Exception as e:
        logger.error(f"[LearningLogger] Failed to log briefing result: {e}")


# ─── LEARNING-LOG.md — Selection Feedback Logging ────────────

def log_selection_feedback(feedback):
    date = feedback.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
    paper_num = feedback.get("paper_number", "???")
    selected_title = feedback.get("selected_story_title", "Unknown")
    selected_source = feedback.get("selected_source", "Unknown")
    selected_score = feedback.get("selected_truth_score", 0)
    selected_category = feedback.get("selected_category", "general")
    rejected = feedback.get("rejected_stories", [])

    entry = f"\n### Feedback {date} \u2014 Paper {paper_num}\n"
    entry += f"- **Selected story:** {selected_title}\n"
    entry += f"- **Selected source:** {selected_source}\n"
    entry += f"- **Selected truth score:** {selected_score}\n"
    entry += f"- **Selected category:** {selected_category}\n"
    entry += f"- **Rejected candidates:** {len(rejected)}\n"
    entry += "- **Top 3 rejected:**\n"
    for i, r in enumerate(rejected[:3], 1):
        r_title = r.get("title", "Unknown")
        r_source = r.get("source", "Unknown")
        r_score = r.get("truth_score", 0)
        entry += f"  {i}. {r_title} | Source: {r_source} | Score: {r_score}\n"

    selected_rank = feedback.get("selected_rank", "unknown")
    entry += f"- **Selection pattern:** Selected story was ranked #{selected_rank} in scout briefing\n"

    try:
        _append_to_file(LEARNING_LOG_PATH, entry)
        logger.info(f"[LearningLogger] Logged selection feedback: Paper {paper_num}")
    except Exception as e:
        logger.error(f"[LearningLogger] Failed to log selection feedback: {e}")


# ─── STYLE-EVOLUTION.md — Source Weight Updates ──────────────

def update_source_weights(learning_log_content):
    source_surfaced = {s: 0 for s in ALL_SOURCES}
    source_selected = {s: 0 for s in ALL_SOURCES}
    total_feedback_events = 0

    brief_pattern = re.compile(r"### Brief \\d{4}-\\d{2}-\\d{2}")
    story_pattern = re.compile(r"\\d+\\.\\s+.+\\|\\s+Source:\\s+(\\S+(?:\\s+\\S+)?)\\s+\\|")

    in_brief = False
    for line in learning_log_content.split("\n"):
        if brief_pattern.match(line.strip()):
            in_brief = True
            continue
        if in_brief and line.strip().startswith("- **Truth score"):
            in_brief = False
            continue
        if in_brief:
            match = story_pattern.search(line)
            if match:
                source = match.group(1).strip()
                for s in ALL_SOURCES:
                    if s.lower() == source.lower():
                        source_surfaced[s] += 1
                        break

    feedback_pattern = re.compile(r"### Feedback .+ \u2014 Paper")
    selected_source_pattern = re.compile(r"\\*\\*Selected source:\\*\\*\\s+(.+)")

    for line in learning_log_content.split("\n"):
        if feedback_pattern.search(line.strip()):
            total_feedback_events += 1
            continue
        match = selected_source_pattern.search(line)
        if match:
            source = match.group(1).strip()
            for s in ALL_SOURCES:
                if s.lower() == source.lower():
                    source_selected[s] += 1
                    break

    if total_feedback_events == 0:
        logger.info("[LearningLogger] No feedback events yet, skipping weight update")
        return

    new_weights = {}
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    for source in ALL_SOURCES:
        surfaced = source_surfaced[source]
        selected = source_selected[source]

        if surfaced == 0:
            new_weights[source] = {"weight": 1.0, "confidence": "baseline", "reason": "No stories surfaced yet"}
            continue

        selection_rate = selected / surfaced if surfaced > 0 else 0
        avg_rate = total_feedback_events / max(sum(source_surfaced.values()), 1)

        if selection_rate > avg_rate * 1.5:
            adjustment = WEIGHT_STEP * min(3, int((selection_rate / max(avg_rate, 0.01)) - 1))
            weight = 1.0 + adjustment
            confidence = "high" if total_feedback_events >= MIN_FEEDBACK_FOR_LARGE_ADJUST else "medium"
            reason = f"Selection rate {selection_rate:.1%} is above average ({avg_rate:.1%})"
        elif selection_rate < avg_rate * 0.5 and surfaced >= 5:
            adjustment = WEIGHT_STEP * min(3, int(1 - (selection_rate / max(avg_rate, 0.01))))
            weight = 1.0 - adjustment
            confidence = "high" if total_feedback_events >= MIN_FEEDBACK_FOR_LARGE_ADJUST else "medium"
            reason = f"Selection rate {selection_rate:.1%} is below average ({avg_rate:.1%})"
        else:
            weight = 1.0
            confidence = "low" if total_feedback_events < MIN_FEEDBACK_FOR_SMALL_ADJUST else "medium"
            reason = f"Selection rate {selection_rate:.1%} is near average"

        if total_feedback_events < MIN_FEEDBACK_FOR_SMALL_ADJUST:
            weight = max(0.8, min(1.2, weight))
        elif total_feedback_events < MIN_FEEDBACK_FOR_LARGE_ADJUST:
            weight = max(0.5, min(1.5, weight))

        weight = max(WEIGHT_MIN, min(WEIGHT_MAX, weight))
        new_weights[source] = {"weight": weight, "confidence": confidence, "reason": reason}

    _update_style_evolution_weights(new_weights, now)
    logger.info(f"[LearningLogger] Updated source weights based on {total_feedback_events} feedback events")


def _update_style_evolution_weights(weights, date):
    try:
        with open(STYLE_EVOLUTION_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        logger.error("[LearningLogger] STYLE-EVOLUTION.md not found")
        return

    new_table = "| Source | Weight | Confidence | Reason | Last Updated |\n"
    new_table += "|--------|--------|------------|--------|-------------|\n"
    for source in ALL_SOURCES:
        w = weights.get(source, {"weight": 1.0, "confidence": "baseline", "reason": "Default"})
        new_table += f"| {source} | {w['weight']:.1f}x | {w['confidence']} | {w['reason']} | {date} |\n"

    pattern = re.compile(
        r"(\\| Source \\| Weight \\| Confidence \\|.*?\n\\|[-| ]+\n)(.*?)(\n### Weight Rules)",
        re.DOTALL
    )
    match = pattern.search(content)
    if match:
        new_content = content[:match.start()] + new_table + match.group(3) + content[match.end():]
    else:
        new_content = content

    try:
        with open(STYLE_EVOLUTION_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        logger.error(f"[LearningLogger] Failed to write STYLE-EVOLUTION.md: {e}")


# ─── Git Commit & Push ──────────────────────────────────────────

def commit_logs(message=None):
    if message is None:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"[Content Scout] Learning log update {now}"

    vault_dir = os.path.join(REPO_PATH, VAULT_BASE)
    files_to_commit = [
        os.path.join(vault_dir, "RUN-LOG.md"),
        os.path.join(vault_dir, "LEARNING-LOG.md"),
        os.path.join(vault_dir, "STYLE-EVOLUTION.md"),
    ]

    try:
        subprocess.run(["git", "pull", "--rebase"], cwd=REPO_PATH, capture_output=True, timeout=30)

        changed = False
        for filepath in files_to_commit:
            if os.path.exists(filepath):
                result = subprocess.run(
                    ["git", "diff", "--name-only", filepath],
                    cwd=REPO_PATH, capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip():
                    subprocess.run(["git", "add", filepath], cwd=REPO_PATH, capture_output=True, timeout=10)
                    changed = True

        if not changed:
            logger.info("[LearningLogger] No vault file changes to commit")
            return

        subprocess.run(["git", "commit", "-m", message], cwd=REPO_PATH, capture_output=True, timeout=30)
        result = subprocess.run(["git", "push"], cwd=REPO_PATH, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info("[LearningLogger] Pushed vault file updates to GitHub")
        else:
            logger.error(f"[LearningLogger] Git push failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("[LearningLogger] Git operation timed out")
    except Exception as e:
        logger.error(f"[LearningLogger] Git commit/push failed: {e}")


# ─── Helper Functions ────────────────────────────────────────────

def _append_to_file(filepath, content):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)
