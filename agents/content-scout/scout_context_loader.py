"""
Content Scout — Context Loader
================================
Loads vault files from the context-vault before each scrape cycle and briefing.
Follows the same pattern as daily_news_agent/context_loader.py.

Files loaded:
  SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md, RUN-LOG.md,
  LEARNING-LOG.md, STYLE-EVOLUTION.md, SOURCES.md, TRUTH-FILTER.md

Load priority: local repo → cache (24h TTL) → GitHub raw

Version: 1.0 | Created: March 6, 2026
"""

import os
import json
import time
import logging
import re
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger("ContentScout.ContextLoader")

# ─── Configuration ───────────────────────────────────────────────

REPO_PATH = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/solosevn/trainingrun-site/main"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".vault-cache")
CACHE_TTL = 86400  # 24 hours in seconds

# Vault file paths relative to repo root
SCOUT_VAULT_FILES = {
    "SOUL":             "agents/content-scout/vault/SOUL.md",
    "CONFIG":           "agents/content-scout/vault/CONFIG.md",
    "PROCESS":          "agents/content-scout/vault/PROCESS.md",
    "CADENCE":          "agents/content-scout/vault/CADENCE.md",
    "RUN_LOG":          "agents/content-scout/vault/RUN-LOG.md",
    "LEARNING_LOG":     "agents/content-scout/vault/LEARNING-LOG.md",
    "STYLE_EVOLUTION":  "agents/content-scout/vault/STYLE-EVOLUTION.md",
    "SOURCES":          "agents/content-scout/vault/SOURCES.md",
    "TRUTH_FILTER":     "agents/content-scout/vault/TRUTH-FILTER.md",
}

# Feedback file from Daily News Agent
SCOUT_FEEDBACK_PATH = "scout-feedback.json"


# ─── Cache Helpers ───────────────────────────────────────────────

def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    """Get the cache file path for a vault key."""
    return os.path.join(CACHE_DIR, f"{key}.md")


def _is_cache_valid(key: str) -> bool:
    """Check if cached file exists and is within TTL."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return False
    age = time.time() - os.path.getmtime(path)
    return age < CACHE_TTL


def _read_cache(key: str) -> str:
    """Read content from cache."""
    with open(_cache_path(key), "r", encoding="utf-8") as f:
        return f.read()


def _write_cache(key: str, content: str):
    """Write content to cache."""
    _ensure_cache_dir()
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        f.write(content)


# ─── Loading Functions ───────────────────────────────────────────

def load_vault_file(key: str) -> str:
    """
    Load a single vault file by key.

    Priority:
    1. Local repo file (freshest — reflects latest git pull)
    2. Cache (if local file missing, cache within 24h TTL)
    3. GitHub raw (fallback — fetch from GitHub directly)

    Returns the file content as a string, or empty string on failure.
    """
    if key not in SCOUT_VAULT_FILES:
        logger.error(f"[ContextLoader] Unknown vault key: {key}")
        return ""

    relative_path = SCOUT_VAULT_FILES[key]

    # Priority 1: Local repo file
    local_path = os.path.join(REPO_PATH, relative_path)
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
            _write_cache(key, content)  # Update cache
            logger.info(f"[ContextLoader] Loaded {key} from local repo")
            return content
        except Exception as e:
            logger.warning(f"[ContextLoader] Failed to read local {key}: {e}")

    # Priority 2: Cache
    if _is_cache_valid(key):
        try:
            content = _read_cache(key)
            logger.info(f"[ContextLoader] Loaded {key} from cache")
            return content
        except Exception as e:
            logger.warning(f"[ContextLoader] Failed to read cache {key}: {e}")

    # Priority 3: GitHub raw
    github_url = f"{GITHUB_RAW_BASE}/{relative_path}"
    try:
        req = urllib.request.Request(
            github_url,
            headers={"User-Agent": "ContentScout/1.2 (trainingrun.ai)"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode("utf-8")
        _write_cache(key, content)  # Update cache
        logger.info(f"[ContextLoader] Loaded {key} from GitHub raw")
        return content
    except Exception as e:
        logger.error(f"[ContextLoader] Failed to load {key} from all sources: {e}")
        return ""


def load_all_context() -> dict:
    """
    Load all 9 vault files. Called before each scrape cycle and briefing.

    Returns a dict: { \"SOUL\": \"...\", \"CONFIG\": \"...\", ... }
    """
    context = {}
    loaded = 0
    failed = 0

    for key in SCOUT_VAULT_FILES:
        content = load_vault_file(key)
        context[key] = content
        if content:
            loaded += 1
        else:
            failed += 1

    logger.info(f"[ContextLoader] Loaded {loaded}/9 vault files ({failed} failed)")
    return context


# ─── Source Weight Extraction ────────────────────────────────────

def get_source_weights(context: dict) -> dict:
    """
    Parse STYLE-EVOLUTION.md to extract current source weight adjustments.

    Returns dict: { \"arXiv\": 1.0, \"Reddit\": 0.8, ... }
    Defaults to 1.0 for any source not found.
    """
    defaults = {
        "arXiv": 1.0,
        "Hugging Face": 1.0,
        "GitHub Trending": 1.0,
        "Reddit": 1.0,
        "Hacker News": 1.0,
        "Lobste.rs": 1.0,
        "YouTube": 1.0,
        "Newsletters": 1.0,
    }

    style_content = context.get("STYLE_EVOLUTION", "")
    if not style_content:
        logger.info("[ContextLoader] No STYLE-EVOLUTION content, using default weights")
        return defaults

    weights = dict(defaults)

    # Parse the weight table from STYLE-EVOLUTION.md
    lines = style_content.split("\n")
    in_weight_table = False

    for line in lines:
        stripped = line.strip()

        if "Source Weight Adjustments" in stripped:
            in_weight_table = True
            continue

        if in_weight_table and stripped.startswith("|"):
            if "---" in stripped or "Source" in stripped and "Weight" in stripped:
                continue

            parts = [p.strip() for p in stripped.split("|") if p.strip()]
            if len(parts) >= 2:
                source_name = parts[0]
                weight_str = parts[1].replace("x", "").strip()
                try:
                    weight = float(weight_str)
                    weight = max(0.5, min(2.0, weight))
                    for key in weights:
                        if key.lower() == source_name.lower():
                            weights[key] = weight
                            break
                except ValueError:
                    continue

        if in_weight_table and stripped.startswith("##") and "Source Weight" not in stripped:
            in_weight_table = False

    logger.info(f"[ContextLoader] Source weights loaded: {weights}")
    return weights


# ─── Feedback Loader ─────────────────────────────────────────────

def load_scout_feedback() -> dict:
    """
    Load and consume scout-feedback.json if it exists.
    Returns the feedback dict, or None if no feedback available.
    After reading, the file is renamed to scout-feedback-processed.json.
    """
    feedback_path = os.path.join(REPO_PATH, SCOUT_FEEDBACK_PATH)

    if not os.path.exists(feedback_path):
        return None

    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            feedback = json.load(f)

        processed_path = feedback_path.replace(".json", "-processed.json")
        os.rename(feedback_path, processed_path)

        logger.info(f"[ContextLoader] Loaded scout feedback: {feedback.get('selected_story_title', 'unknown')}")
        return feedback
    except Exception as e:
        logger.error(f"[ContextLoader] Failed to load scout feedback: {e}")
        return None


# ─── Staleness Config ────────────────────────────────────────────

STALENESS_DEPRIORITIZE_DAYS = 3  # Items >3 days old get score * 0.5
STALENESS_DROP_DAYS = 7          # Items >7 days old get dropped entirely
