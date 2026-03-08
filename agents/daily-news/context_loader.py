"""
Daily News Agent — Context Vault Loader
========================================
Reads the agent's instruction files from GitHub (or local cache).
These files tell the agent who it is, how to think, and what to do.
"""

import json
import time
import requests
from pathlib import Path
from config import GITHUB_RAW_BASE, VAULT_FILES, CACHE_DIR, TR_REPO_PATH, SCOUT_BRIEFING_PATH

CACHE_TTL_SECONDS = 86400


def _cache_path(key):
    return CACHE_DIR / f"{key}.cached"


def _is_cache_fresh(key):
    cp = _cache_path(key)
    if not cp.exists():
        return False
    age = time.time() - cp.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def load_vault_file(key, force_refresh=False):
    repo_path = VAULT_FILES.get(key)
    if not repo_path:
        raise ValueError(f"Unknown vault key: {key}")

    local_file = TR_REPO_PATH / repo_path
    if local_file.exists() and not force_refresh:
        content = local_file.read_text(encoding="utf-8")
        _cache_path(key).write_text(content, encoding="utf-8")
        return content

    if not force_refresh and _is_cache_fresh(key):
        return _cache_path(key).read_text(encoding="utf-8")

    url = f"{GITHUB_RAW_BASE}/{repo_path}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        content = resp.text
        _cache_path(key).write_text(content, encoding="utf-8")
        return content
    except requests.RequestException as e:
        cp = _cache_path(key)
        if cp.exists():
            print(f"[ContextLoader] WARNING: GitHub fetch failed for {key}, using stale cache: {e}")
            return cp.read_text(encoding="utf-8")
        raise RuntimeError(f"Cannot load vault file '{key}': {e}")


def load_all_context(force_refresh=False):
    context = {}
    for key in VAULT_FILES:
        try:
            context[key] = load_vault_file(key, force_refresh=force_refresh)
        except Exception as e:
            print(f"[ContextLoader] ERROR loading {key}: {e}")
            context[key] = ""
    return context


def load_scout_briefing():
    if SCOUT_BRIEFING_PATH.exists():
        try:
            with open(SCOUT_BRIEFING_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ContextLoader] ERROR reading local scout-briefing.json: {e}")

    url = f"{GITHUB_RAW_BASE}/scout-briefing.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ContextLoader] ERROR fetching scout-briefing.json from GitHub: {e}")
        return {}


def get_stories_from_briefing(briefing):
    stories = briefing.get("top_stories", [])
    if not stories:
        stories = briefing.get("top_10", [])
    return stories


def test_context_loader():
    try:
        content = load_vault_file("user_md")
        if content and len(content) > 100:
            print(f"[ContextLoader] ✅ USER.md loaded ({len(content)} chars)")
            return True
        else:
            print("[ContextLoader] ❌ USER.md loaded but seems empty")
            return False
    except Exception as e:
        print(f"[ContextLoader] ❌ Failed: {e}")
        return False


if __name__ == "__main__":
    test_context_loader()
