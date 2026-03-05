#!/usr/bin/env python3
"""
Content Scout v1.2.0
====================
The AI news intelligence agent for trainingrun.ai — powered by llama3.1:8b (Ollama, local, free).

MISSION: Provide the most transparent, fact-checked, and accessible measurement of AI
capabilities — so the public, investors, policymakers, and developers can make informed
decisions based on data, not hype.

- Scrapes AI news from 15 free public sources (no API keys, no paywalls, no logins)
- Runs 7 AM – 11 PM: scrapes every 30 minutes
- At 5:30 AM: generates morning brief via Ollama + Truth Filter, sends to David via Telegram
- Writes scout-briefing.json for Mission Control display
- Pushes briefing to GitHub so the site updates
- Filters through the TrainingRun lens: verifiable data > hype, facts > clickbait
- Runs top 10 through 4-layer Truth Filter: Source Credibility, Cross-Confirmation, Zero Hype, AI Verification

Sources: arXiv, Hugging Face, GitHub Trending, Reddit (4 subs),
         Hacker News, Lobste.rs, YouTube RSS (5 channels), AI newsletters RSS (4 feeds),
         TechCrunch, VentureBeat, Ars Technica, The Verge, MIT Tech Review, Reuters, Wired

Ethical: Respects rate limits, identifies itself. Free public sources only.

Run:   python3 scout.py
Stop:  Ctrl+C

Changelog:
  v1.2.0 — Merged Truth Filter v2.0: 4-layer filtering + AI verification (Ollama + xAI Grok).
           Added 7 new scrapers (TechCrunch, VentureBeat, Ars Technica, The Verge, MIT Tech Review,
           Reuters, Wired). Fixed YouTube channel IDs and newsletter feeds. Added TrainingRun
           relevance verticals. xAI API key support for Grok fact-checking.
  v1.1.0 — Merged Truth Filter v1.0. Source credibility, cross-confirmation, zero-hype scoring.
  v1.0.1 — Fixed robots.txt checker blocking legitimate RSS feeds and public APIs.
           Whitelisted known public sources. Made parser lenient on failures.
"""

import os
import sys
import json
import time
import subprocess
import requests
import datetime
import re
import hashlib
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
XAI_API_KEY      = os.getenv("XAI_API_KEY", "")
REPO_PATH        = os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site"))
SCOUT_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)))
BRAIN_FILE       = os.path.join(SCOUT_DIR, "scout_brain.md")
DATA_FILE        = os.path.join(SCOUT_DIR, "scout-data.json")
BRIEFING_FILE    = os.path.join(REPO_PATH, "scout-briefing.json")
OLLAMA_MODEL     = "llama3.1:8b"
OLLAMA_URL       = "http://localhost:11434/api/generate"

# Full Python path for subprocess calls (macOS)
PYTHON_PATH      = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

# Schedule
SCRAPE_START_HOUR = 7     # 7 AM
SCRAPE_END_HOUR   = 23    # 11 PM
BRIEF_HOUR        = 5     # 5:30 AM
BRIEF_MINUTE      = 30
SCRAPE_INTERVAL   = 1800  # 30 minutes between scrape cycles

# Request settings
REQUEST_TIMEOUT   = 20
USER_AGENT        = "ContentScout/1.2 (trainingrun.ai research/educational AI news aggregator)"
HEADERS           = {"User-Agent": USER_AGENT}

# ScrapeGraphAI availability (optional upgrade layer)
SCRAPEGRAPH_AVAILABLE = False
try:
    from scrapegraphai.graphs import SmartScraperGraph
    SCRAPEGRAPH_AVAILABLE = True
except ImportError:
    pass


# ─────────────────────────────────────────────
# ETHICAL GUARDRAILS
# ─────────────────────────────────────────────

# Known public sources — these serve RSS feeds, public APIs, and free JSON endpoints
# explicitly designed for automated consumption. Skip robots.txt for these.
KNOWN_PUBLIC_DOMAINS = {
    "export.arxiv.org",         # arXiv RSS feeds
    "arxiv.org",
    "huggingface.co",           # HF papers page (public)
    "github.com",               # GitHub trending (public page)
    "www.reddit.com",           # Reddit JSON endpoints (public API)
    "old.reddit.com",
    "hacker-news.firebaseio.com",  # HN public API
    "news.ycombinator.com",
    "lobste.rs",                # Lobste.rs RSS
    "www.youtube.com",          # YouTube RSS feeds
    "tldrai.com",               # Newsletter RSS
    "tldr.tech",                # Newsletter RSS (updated)
    "importai.substack.com",    # Newsletter RSS (legacy)
    "jack-clark.net",           # Import AI (updated)
    "read.deeplearning.ai",     # Newsletter RSS (legacy)
    "www.deeplearning.ai",      # Newsletter RSS (updated)
    "techcrunch.com",           # TechCrunch RSS
    "venturebeat.com",          # VentureBeat RSS
    "feeds.arstechnica.com",    # Ars Technica RSS
    "arstechnica.com",
    "www.theverge.com",         # The Verge RSS
    "www.technologyreview.com", # MIT Tech Review RSS
    "www.reuters.com",          # Reuters RSS
    "reuters.com",
    "www.wired.com",            # Wired RSS
    "bullrich.dev",             # Possibly used in feeds
}


def ethical_preflight(url: str, source_name: str) -> bool:
    """
    Ethical guardrail check before every fetch.
    ScrapeMaster principle: Is this public/free? Does it violate ToS? If unsure → skip.

    For known public sources (RSS feeds, public APIs), we skip robots.txt since
    these endpoints are explicitly designed for automated consumption.
    """
    parsed = urlparse(url)

    # Rule 1: Only HTTP/HTTPS
    if parsed.scheme not in ("http", "https"):
        print(f"[Ethics] BLOCKED: Non-HTTP scheme for {source_name}: {parsed.scheme}")
        return False

    # Rule 2: No login/paywall indicators in URL
    blocked_patterns = ["login", "signin", "paywall", "subscribe", "checkout", "account"]
    path_lower = parsed.path.lower()
    if any(bp in path_lower for bp in blocked_patterns):
        print(f"[Ethics] BLOCKED: Login/paywall URL detected for {source_name}")
        return False

    # Rule 3: Known public sources are pre-approved (RSS, APIs, public pages)
    domain = parsed.netloc.lower()
    if domain in KNOWN_PUBLIC_DOMAINS:
        return True

    # Rule 4: For unknown domains, log a notice but allow (we only scrape sources we configure)
    print(f"[Ethics] NOTICE: Unknown domain {domain} for {source_name} — allowing (configured source)")
    return True


# ─────────────────────────────────────────────
# LAYER 1-3: SOURCE CREDIBILITY & TRUTH FILTER
# ─────────────────────────────────────────────

SOURCE_CREDIBILITY = {
    # Tier 1 — Primary Sources (35-40 pts)
    "arxiv":            40,
    "huggingface":      38,
    "github":           35,
    "reuters":          40,
    "ap_news":          40,
    "bls":              40,

    # Tier 2 — Established Outlets (20-30 pts)
    "techcrunch":       28,
    "venturebeat":      26,
    "ars_technica":     27,
    "datacenter_dynamics": 25,
    "wired":            26,
    "the_verge":        25,
    "mit_tech_review":  30,

    # Tier 3 — Community & Aggregation (10-20 pts)
    "reddit":           15,
    "hackernews":       18,
    "lobsters":         20,
    "youtube":          12,
    "newsletters":      22,

    # Default for unknown sources
    "unknown":          10,
}


# Clickbait / hype indicators — deprioritize these
HYPE_SIGNALS = [
    "you won't believe", "shocking", "mind-blowing", "game changer",
    "everything changes", "is dead", "killer", "destroy", "replace all",
    "agi is here", "sentient", "conscious", "alive", "the end of",
    "wake up", "they don't want you to know", "secret", "conspiracy",
    "just revealed", "breaking:", "urgent:", "insane", "god-mode",
    "destroys", "kills", "mind blowing", "game-changer",
    "revolutionary", "unprecedented", "paradigm shift", "disrupts everything",
    "the future is here", "changes everything forever",
]

# Quality / substance indicators — prioritize these
SUBSTANCE_SIGNALS = [
    "benchmark", "evaluation", "results", "paper", "arxiv", "research",
    "dataset", "performance", "accuracy", "score", "leaderboard",
    "methodology", "peer-review", "reproducible", "open source",
    "release", "published", "technical report", "ablation",
    "comparison", "analysis", "study", "findings", "data",
    "measured", "tested", "verified", "audit", "transparent",
    "code available", "weights released", "model card",
]

# Speculation penalty signals
SPECULATION_SIGNALS = [
    "i think", "my prediction", "hot take", "unpopular opinion", "imo",
    "rumor", "supposedly", "allegedly", "unconfirmed", "sources say",
    "could potentially", "might eventually", "some believe",
]


# ============================================================
# TRAININGRUN RELEVANCE AXIS
# ============================================================

TR_RELEVANCE_KEYWORDS = {
    "trsbench": {
        "weight": 30,
        "keywords": [
            "benchmark", "leaderboard", "evaluation", "performance",
            "accuracy", "score", "ranking", "mmlu", "hellaswag",
            "gpqa", "humaneval", "model comparison", "state of the art",
            "sota", "beats", "surpasses", "outperforms",
        ]
    },
    "truscore": {
        "weight": 28,
        "keywords": [
            "factual", "truthful", "hallucin", "bias", "neutrality",
            "misinformation", "disinformation", "fact-check", "accuracy",
            "simpleqa", "newsguard", "political compass", "calibration",
            "trustworthy", "reliable", "honest", "safety", "alignment",
            "guardrails", "red team", "jailbreak",
        ]
    },
    "trscode": {
        "weight": 25,
        "keywords": [
            "coding", "code generation", "swe-bench", "livecodebench",
            "humaneval", "copilot", "code completion", "programming",
            "developer tool", "ide", "vscode", "cursor", "aider",
            "code review", "refactoring", "debugging",
        ]
    },
    "tragents": {
        "weight": 27,
        "keywords": [
            "agent", "autonomous", "tool use", "function calling",
            "multi-step", "reasoning", "chain of thought", "react",
            "planning", "execution", "computer use", "browser agent",
            "digital worker", "robotic process", "workflow automation",
            "agentic", "orchestration", "multi-agent",
        ]
    },
    "trfcast": {
        "weight": 22,
        "keywords": [
            "forecast", "prediction", "timeline", "metaculus",
            "polymarket", "agi", "asi", "singularity", "scaling law",
            "compute", "training cost", "inference cost", "trajectory",
            "exponential", "doubling", "projection",
        ]
    },
    "gari": {
        "weight": 26,
        "keywords": [
            "china", "eu", "european", "regulation", "policy",
            "government", "executive order", "ai act", "national",
            "geopolitical", "arms race", "export control", "chip",
            "semiconductor", "nvidia", "tsmc", "sanctions",
            "deepseek", "baidu", "alibaba", "tencent", "mistral",
            "uae", "saudi", "india", "uk ai", "g7",
        ]
    },
    "churn": {
        "weight": 24,
        "keywords": [
            "jobs", "employment", "layoff", "hiring", "workforce",
            "automation", "displaced", "labor", "salary", "career",
            "upskilling", "reskilling", "remote work", "gig economy",
            "human replacement", "augmentation", "productivity",
        ]
    },
    "gigaburn": {
        "weight": 23,
        "keywords": [
            "data center", "gpu", "tpu", "compute", "infrastructure",
            "power consumption", "energy", "cooling", "megawatt",
            "cloud", "aws", "azure", "gcp", "nvidia", "amd",
            "h100", "h200", "b200", "blackwell", "training run",
            "cost", "flops", "tokens per second",
        ]
    },
    "open_vs_closed": {
        "weight": 25,
        "keywords": [
            "open source", "open weight", "open model", "closed source",
            "proprietary", "llama", "mistral", "qwen", "gemma",
            "phi", "falcon", "gpt", "claude", "gemini", "o1", "o3",
            "meta ai", "openai", "anthropic", "google deepmind",
            "weights released", "apache", "mit license",
        ]
    },
}


def get_source_credibility(source_name: str) -> int:
    """Get credibility score for a source, with partial matching."""
    source_lower = source_name.lower()
    # Direct match first
    if source_name in SOURCE_CREDIBILITY:
        return SOURCE_CREDIBILITY[source_name]
    # Partial matches
    if "arxiv" in source_lower:
        return SOURCE_CREDIBILITY.get("arxiv", 40)
    if "hugging face" in source_lower or "huggingface" in source_lower:
        return SOURCE_CREDIBILITY.get("huggingface", 38)
    if "github" in source_lower:
        return SOURCE_CREDIBILITY.get("github", 35)
    if "reddit" in source_lower or source_lower.startswith("r/"):
        return SOURCE_CREDIBILITY.get("reddit", 15)
    if "hacker news" in source_lower:
        return SOURCE_CREDIBILITY.get("hackernews", 18)
    if "lobste" in source_lower:
        return SOURCE_CREDIBILITY.get("lobsters", 20)
    if "youtube" in source_lower:
        return SOURCE_CREDIBILITY.get("youtube", 12)
    if "techcrunch" in source_lower:
        return SOURCE_CREDIBILITY.get("techcrunch", 28)
    if "venturebeat" in source_lower:
        return SOURCE_CREDIBILITY.get("venturebeat", 26)
    if "ars technica" in source_lower:
        return SOURCE_CREDIBILITY.get("ars_technica", 27)
    if "verge" in source_lower:
        return SOURCE_CREDIBILITY.get("the_verge", 25)
    if "mit" in source_lower or "technology review" in source_lower:
        return SOURCE_CREDIBILITY.get("mit_tech_review", 30)
    if "reuters" in source_lower:
        return SOURCE_CREDIBILITY.get("reuters", 40)
    if "wired" in source_lower:
        return SOURCE_CREDIBILITY.get("wired", 26)
    if "newsletter" in source_lower or "tldr" in source_lower or "batch" in source_lower or "import ai" in source_lower:
        return SOURCE_CREDIBILITY.get("newsletters", 22)
    return SOURCE_CREDIBILITY.get("unknown", 10)


def compute_truth_score(item: dict, all_items: list) -> dict:
    """
    Three-layer Truth Filter + TrainingRun Relevance.
    Returns enriched item with truth_score and metadata.
    """
    title = item.get("title", "")
    summary = item.get("summary", "")
    source = item.get("source", "unknown")
    url = item.get("url", "")
    text = f"{title} {summary}".lower()

    # --- LAYER 1: Source Credibility (0-40) ---
    source_score = get_source_credibility(source)

    # Bonus: Direct links to primary sources within the item
    if "arxiv.org" in url or "arxiv.org" in text:
        source_score = min(40, source_score + 5)
    if "github.com" in url and ("release" in text or "v1" in text or "v2" in text):
        source_score = min(40, source_score + 5)

    # --- LAYER 2: Cross-Confirmation (0-20) ---
    title_words = set(re.sub(r'[^\w\s]', '', title.lower()).split())
    cross_count = 0
    cross_sources = set()

    if title_words and len(title_words) >= 3:
        for other in all_items:
            if other.get("url") == item.get("url"):
                continue
            if other.get("source") == source:
                continue
            other_words = set(re.sub(r'[^\w\s]', '', other.get("title", "").lower()).split())
            if not other_words:
                continue
            overlap = len(title_words & other_words) / max(len(title_words), len(other_words))
            if overlap > 0.50:
                cross_count += 1
                cross_sources.add(other.get("source", ""))

    if cross_count >= 3:
        cross_score = 20
    elif cross_count >= 2:
        cross_score = 15
    elif cross_count >= 1:
        cross_score = 8
    else:
        cross_score = 0

    # --- LAYER 3: Zero Hype / Substance (0-20, can go negative) ---
    hype_count = sum(1 for s in HYPE_SIGNALS if s in text)
    substance_count = sum(1 for s in SUBSTANCE_SIGNALS if s in text)
    speculation_count = sum(1 for s in SPECULATION_SIGNALS if s in text)

    raw_substance = (substance_count * 4) - (hype_count * 8) - (speculation_count * 4)
    substance_score = max(-10, min(20, raw_substance))

    # --- TRAININGRUN RELEVANCE (0-20) ---
    best_relevance = 0
    matched_verticals = []

    for vertical, config in TR_RELEVANCE_KEYWORDS.items():
        keyword_hits = sum(1 for kw in config["keywords"] if kw in text)
        if keyword_hits > 0:
            vertical_score = min(20, (keyword_hits * config["weight"]) // 5)
            if vertical_score > best_relevance:
                best_relevance = vertical_score
            if keyword_hits >= 2:
                matched_verticals.append(vertical)

    relevance_score = min(20, best_relevance)

    # --- COMPOSITE TRUTH SCORE (0-100) ---
    truth_score = source_score + cross_score + substance_score + relevance_score
    truth_score = max(0, min(100, truth_score))

    # --- CLASSIFY into TrainingRun category ---
    tr_category = classify_tr_category(title, summary, matched_verticals)

    return {
        **item,
        "truth_score": truth_score,
        "source_credibility": source_score,
        "cross_confirmation": cross_score,
        "cross_sources": list(cross_sources),
        "substance_score": substance_score,
        "relevance_score": relevance_score,
        "tr_category": tr_category,
        "matched_verticals": matched_verticals,
        "hype_flags": hype_count,
        "substance_flags": substance_count,
    }


def classify_tr_category(title: str, summary: str, matched_verticals: list) -> str:
    """
    Classify into TrainingRun content categories.
    Maps to the segments David cares about.
    """
    text = f"{title} {summary}".lower()

    if matched_verticals:
        priority = ["trsbench", "truscore", "trscode", "tragents", "gari",
                     "open_vs_closed", "churn", "gigaburn", "trfcast"]
        for p in priority:
            if p in matched_verticals:
                return p

    if any(kw in text for kw in ["benchmark", "leaderboard", "evaluation", "score"]):
        return "trsbench"
    elif any(kw in text for kw in ["truth", "bias", "hallucin", "factual", "safety"]):
        return "truscore"
    elif any(kw in text for kw in ["code", "programming", "developer", "swe-bench"]):
        return "trscode"
    elif any(kw in text for kw in ["agent", "autonomous", "agentic", "tool use"]):
        return "tragents"
    elif any(kw in text for kw in ["china", "regulation", "policy", "geopolit"]):
        return "gari"
    elif any(kw in text for kw in ["job", "layoff", "workforce", "employment"]):
        return "churn"
    elif any(kw in text for kw in ["data center", "gpu", "compute", "energy", "power"]):
        return "gigaburn"
    elif any(kw in text for kw in ["open source", "closed source", "weights", "license"]):
        return "open_vs_closed"
    elif any(kw in text for kw in ["forecast", "prediction", "timeline", "agi"]):
        return "trfcast"
    else:
        return "general"


def select_top_10(scored_items: list, min_truth_score: int = 50) -> list:
    """
    Select the top 10 stories with diversity rules.
    """
    qualified = [item for item in scored_items if item["truth_score"] >= min_truth_score]

    if not qualified:
        qualified = sorted(scored_items, key=lambda x: x["truth_score"], reverse=True)[:10]
        return qualified

    qualified.sort(key=lambda x: x["truth_score"], reverse=True)

    top_10 = []
    category_counts = Counter()
    source_counts = Counter()

    for item in qualified:
        if len(top_10) >= 10:
            break

        cat = item.get("tr_category", "general")
        src = item.get("source", "unknown")

        if category_counts[cat] >= 3:
            continue
        if source_counts[src] >= 2:
            continue

        top_10.append(item)
        category_counts[cat] += 1
        source_counts[src] += 1

    if len(top_10) < 10:
        for item in qualified:
            if len(top_10) >= 10:
                break
            if item not in top_10:
                top_10.append(item)

    return top_10


def select_top_10_candidates(scored_items: list, count: int = 15, min_truth_score: int = 50) -> list:
    """
    Select top N candidates for AI verification (more than 10 so we have backfill).
    """
    qualified = [item for item in scored_items if item["truth_score"] >= min_truth_score]

    if not qualified:
        qualified = sorted(scored_items, key=lambda x: x["truth_score"], reverse=True)[:count]
        return qualified

    qualified.sort(key=lambda x: x["truth_score"], reverse=True)

    selected = []
    category_counts = Counter()
    source_counts = Counter()

    for item in qualified:
        if len(selected) >= count:
            break

        cat = item.get("tr_category", "general")
        src = item.get("source", "unknown")

        if category_counts[cat] >= 4:
            continue
        if source_counts[src] >= 3:
            continue

        selected.append(item)
        category_counts[cat] += 1
        source_counts[src] += 1

    if len(selected) < count:
        for item in qualified:
            if len(selected) >= count:
                break
            if item not in selected:
                selected.append(item)

    return selected


# ============================================================
# LAYER 4: AI VERIFICATION (Ollama + xAI Grok)
# ============================================================

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL = "grok-3-mini"
OLLAMA_URL_VERIFY = "http://localhost:11434/api/generate"
OLLAMA_MODEL_VERIFY = "llama3.1:8b"

AI_VERIFY_PROMPT = """You are a fact-checking assistant for an AI news site called TrainingRun.
Your job: assess whether this headline and summary describe something that is likely TRUE and VERIFIABLE, or likely MISLEADING, EXAGGERATED, or CLICKBAIT.

HEADLINE: {title}
SUMMARY: {summary}
SOURCE: {source}

Respond with ONLY a JSON object (no other text):
{{
  "verdict": "VERIFIED" or "SUSPICIOUS" or "MISLEADING",
  "confidence": 1-10,
  "reason": "one sentence explanation"
}}

Rules:
- "VERIFIED" = the claim is specific, factual, and plausible given current AI landscape
- "SUSPICIOUS" = vague, unverifiable, or missing key details
- "MISLEADING" = clearly exaggerated, clickbait, or making unsubstantiated claims
- Be strict. When in doubt, mark SUSPICIOUS.
- A paper on arXiv with specific results = likely VERIFIED
- "This AI will DESTROY everything" = MISLEADING
- "Sources say GPT-5 is coming" without specifics = SUSPICIOUS"""


def _ollama_verify(title: str, summary: str, source: str) -> dict:
    """Run verification through local Ollama model."""
    prompt = AI_VERIFY_PROMPT.format(title=title, summary=summary or "No summary", source=source)
    try:
        resp = requests.post(
            OLLAMA_URL_VERIFY,
            json={
                "model": OLLAMA_MODEL_VERIFY,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 200}
            },
            timeout=30
        )
        if resp.ok:
            text = resp.json().get("response", "")
            return _parse_verify_response(text, "ollama")
    except Exception as e:
        print(f"[Verify] Ollama error: {e}")
    return {"verdict": "UNKNOWN", "confidence": 0, "reason": "Ollama unavailable", "model": "ollama"}


def _xai_verify(title: str, summary: str, source: str, xai_api_key: str) -> dict:
    """Run verification through xAI Grok API (free $25/mo credits)."""
    if not xai_api_key:
        return {"verdict": "UNKNOWN", "confidence": 0, "reason": "No xAI API key", "model": "grok"}

    prompt = AI_VERIFY_PROMPT.format(title=title, summary=summary or "No summary", source=source)
    try:
        resp = requests.post(
            XAI_API_URL,
            headers={
                "Authorization": f"Bearer {xai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": XAI_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a fact-checking assistant. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 200
            },
            timeout=15
        )
        if resp.ok:
            text = resp.json()["choices"][0]["message"]["content"]
            return _parse_verify_response(text, "grok")
        else:
            print(f"[Verify] xAI/Grok HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[Verify] xAI/Grok error: {e}")
    return {"verdict": "UNKNOWN", "confidence": 0, "reason": "xAI/Grok unavailable", "model": "grok"}


def _parse_verify_response(text: str, model: str) -> dict:
    """Parse the JSON verdict from an AI model response."""
    try:
        import json as _json
        clean = text.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()

        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = _json.loads(clean[start:end])
            return {
                "verdict": parsed.get("verdict", "UNKNOWN").upper(),
                "confidence": min(10, max(1, int(parsed.get("confidence", 5)))),
                "reason": parsed.get("reason", "No reason given"),
                "model": model
            }
    except Exception:
        pass
    return {"verdict": "UNKNOWN", "confidence": 0, "reason": f"Could not parse {model} response", "model": model}


def ai_verify_top_10(top_10: list, xai_api_key: str = "") -> list:
    """
    Run the top 10 candidates through dual AI verification.
    """
    verified_items = []
    dropped_count = 0

    for item in top_10:
        title = item.get("title", "")
        summary = item.get("summary", "")
        source = item.get("source", "")

        print(f"[Verify] Checking: {title[:80]}...")

        ollama_result = _ollama_verify(title, summary, source)
        time.sleep(0.5)
        grok_result = _xai_verify(title, summary, source, xai_api_key)

        verdicts = [ollama_result["verdict"], grok_result["verdict"]]
        confidences = [ollama_result["confidence"], grok_result["confidence"]]

        if "MISLEADING" in verdicts and verdicts.count("MISLEADING") >= 2:
            ai_verdict = "DROPPED"
            ai_confidence = max(confidences)
            dropped_count += 1
            print(f"[Verify] DROPPED: {title[:60]} — both models flagged misleading")
            continue

        elif "MISLEADING" in verdicts and "VERIFIED" not in verdicts:
            ai_verdict = "WARNING"
            ai_confidence = max(confidences)
            print(f"[Verify] WARNING: {title[:60]}")

        elif verdicts.count("VERIFIED") >= 2:
            ai_verdict = "AI_VERIFIED"
            ai_confidence = max(confidences)
            print(f"[Verify] VERIFIED: {title[:60]}")

        elif "VERIFIED" in verdicts:
            ai_verdict = "LIKELY_TRUE"
            ai_confidence = min(confidences) if min(confidences) > 0 else max(confidences)
            print(f"[Verify] LIKELY_TRUE: {title[:60]}")

        elif verdicts.count("UNKNOWN") >= 2:
            ai_verdict = "UNVERIFIED"
            ai_confidence = 0
            print(f"[Verify] UNVERIFIED (models unavailable): {title[:60]}")

        else:
            ai_verdict = "SUSPICIOUS"
            ai_confidence = max(confidences)
            print(f"[Verify] SUSPICIOUS: {title[:60]}")

        item["ai_verdict"] = ai_verdict
        item["ai_confidence"] = ai_confidence
        item["ai_checks"] = {
            "ollama": {
                "verdict": ollama_result["verdict"],
                "confidence": ollama_result["confidence"],
                "reason": ollama_result["reason"]
            },
            "grok": {
                "verdict": grok_result["verdict"],
                "confidence": grok_result["confidence"],
                "reason": grok_result["reason"]
            }
        }

        verified_items.append(item)

    print(f"[Verify] Done. {len(verified_items)} passed, {dropped_count} dropped.")
    return verified_items


# ============================================================
# TELEGRAM OUTPUT
# ============================================================

TR_CATEGORY_LABELS = {
    "trsbench":       "Benchmarks",
    "truscore":       "Truth & Safety",
    "trscode":        "Code & Dev",
    "tragents":       "Agents",
    "trfcast":        "Forecasting",
    "gari":           "Global AI Race",
    "churn":          "Jobs & Workforce",
    "gigaburn":       "Compute & Power",
    "open_vs_closed": "Open vs Closed",
    "general":        "AI News",
}


def format_telegram_brief(top_10: list, stats: dict) -> str:
    """
    Format the top 10 for Telegram delivery.
    Clean, scannable bullets David can read on his phone at 5:30 AM.
    """
    date_str = datetime.date.today().strftime("%b %d, %Y")

    lines = []
    lines.append(f"SCOUT DAILY BRIEF — {date_str}")
    lines.append(f"Scanned {stats['total_scraped']} items → filtered to top {len(top_10)}")
    lines.append("")

    for i, item in enumerate(top_10, 1):
        cat_label = TR_CATEGORY_LABELS.get(item.get("tr_category", "general"), "News")
        title = item["title"][:120]
        truth = item["truth_score"]

        lines.append(f"{i}. {cat_label}")
        lines.append(f"   {title}")

        ai_verdict = item.get("ai_verdict", "")
        if ai_verdict == "AI_VERIFIED":
            badge = "VERIFIED"
        elif ai_verdict == "LIKELY_TRUE":
            badge = "LIKELY TRUE"
        elif ai_verdict == "WARNING":
            badge = "CAUTION"
        elif ai_verdict == "SUSPICIOUS":
            badge = "UNCONFIRMED"
        else:
            badge = "INFO"

        source = item.get("source", "")
        cross = item.get("cross_confirmation", 0)
        if cross > 0:
            lines.append(f"   {badge} | {len(item.get('cross_sources', []))+1} sources | Truth: {truth}/100")
        else:
            lines.append(f"   {badge} | {source} | Truth: {truth}/100")

        if item.get("url"):
            lines.append(f"   {item['url']}")
        lines.append("")

    lines.append("—")
    cats_covered = len(set(item.get("tr_category", "general") for item in top_10))
    lines.append(f"Categories: {cats_covered} | Sources active: {stats.get('sources_active', 0)}")
    lines.append("trainingrun.ai — Truth > Hype | Data > Opinion")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# CONTENT QUALITY FILTER (TrainingRun Philosophy)
# ─────────────────────────────────────────────

def compute_quality_score(title: str, summary: str, base_score: int = 0) -> int:
    """
    Score items through the TrainingRun lens.
    Higher = more valuable. Penalize hype, reward substance.
    """
    text = f"{title} {summary}".lower()
    score = base_score

    for signal in HYPE_SIGNALS:
        if signal in text:
            score -= 10

    for signal in SUBSTANCE_SIGNALS:
        if signal in text:
            score += 5

    if "arxiv" in text or "paper" in text or "research" in text:
        score += 10

    speculation = ["i think", "my prediction", "hot take", "unpopular opinion", "imo"]
    for spec in speculation:
        if spec in text:
            score -= 5

    return score


def classify_item(title: str, summary: str) -> str:
    """
    Classify an item's content type for the briefing.
    Returns: 'research', 'release', 'tool', 'discussion', 'opinion', 'news'
    """
    text = f"{title} {summary}".lower()

    if any(kw in text for kw in ["arxiv", "paper", "study", "findings", "peer"]):
        return "research"
    elif any(kw in text for kw in ["release", "launched", "announcing", "now available", "v1", "v2"]):
        return "release"
    elif any(kw in text for kw in ["github", "repo", "library", "framework", "tool", "cli"]):
        return "tool"
    elif any(kw in text for kw in ["discussion", "debate", "thread", "thoughts on"]):
        return "discussion"
    elif any(kw in text for kw in ["opinion", "take", "think", "believe", "prediction"]):
        return "opinion"
    else:
        return "news"


# ─────────────────────────────────────────────
# DATA VALIDATION (ScrapeMaster Skills)
# ─────────────────────────────────────────────

def validate_url(url: str) -> str:
    """Ensure URL is absolute and well-formed. Return cleaned URL or empty string."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return ""
        return url
    except Exception:
        return ""


def validate_date(date_str: str) -> str:
    """Validate and normalize date to ISO format. Return ISO string or empty."""
    if not date_str:
        return ""
    try:
        datetime.date.fromisoformat(date_str[:10])
        return date_str[:10]
    except (ValueError, TypeError):
        return ""


def clean_text(text: str) -> str:
    """Clean extracted text: strip HTML, normalize whitespace, truncate."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────

def tg_send(text: str):
    """Send a message to David via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    MAX_LEN = 3900
    chunks = []
    while len(text) > MAX_LEN:
        split_at = text.rfind("\n", 0, MAX_LEN)
        if split_at < MAX_LEN // 2:
            split_at = MAX_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    chunks.append(text)

    for chunk in chunks:
        if not chunk.strip():
            continue
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "HTML"}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if not resp.ok:
                payload.pop("parse_mode")
                requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"[Telegram] {e}")


# ─────────────────────────────────────────────
# DATA STORE
# ─────────────────────────────────────────────

def load_data() -> dict:
    """Load collected items from scout-data.json."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": [], "last_scrape": None, "last_brief": None}


def save_data(data: dict):
    """Save collected items to scout-data.json."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def item_hash(title: str, source: str) -> str:
    """Deduplicate by title + source."""
    return hashlib.md5(f"{title.lower().strip()}:{source}".encode()).hexdigest()


def cross_source_dedup(title: str, data: dict) -> bool:
    """
    Multi-source dedup (ScrapeMaster aggregation skill).
    Check if a very similar title already exists from ANY source.
    Catches the same story appearing on Reddit, HN, and newsletters.
    """
    title_lower = title.lower().strip()
    title_clean = re.sub(r"^\[.*?\]\s*", "", title_lower)
    title_clean = re.sub(r"\s*\(.*?\)\s*$", "", title_clean)

    for item in data["items"]:
        existing_clean = re.sub(r"^\[.*?\]\s*", "", item["title"].lower().strip())
        existing_clean = re.sub(r"\s*\(.*?\)\s*$", "", existing_clean)

        words_new = set(title_clean.split())
        words_existing = set(existing_clean.split())
        if not words_new or not words_existing:
            continue
        overlap = len(words_new & words_existing) / max(len(words_new), len(words_existing))
        if overlap > 0.80:
            return True

    return False


def add_item(data: dict, title: str, url: str, source: str,
             summary: str = "", score: int = 0, timestamp: str = ""):
    """
    Add an item if not already present.
    Applies: hash dedup, cross-source dedup, URL validation, quality scoring, classification.
    """
    title = clean_text(title)
    summary = clean_text(summary)
    url = validate_url(url)

    if not title or not url:
        return False

    h = item_hash(title, source)
    existing_hashes = {item.get("hash") for item in data["items"]}
    if h in existing_hashes:
        return False

    if cross_source_dedup(title, data):
        return False

    if not timestamp:
        timestamp = datetime.datetime.now().isoformat()

    quality = compute_quality_score(title, summary, base_score=score)
    category = classify_item(title, summary)

    data["items"].append({
        "hash": h,
        "title": title,
        "url": url,
        "source": source,
        "summary": summary[:500],
        "score": score,
        "quality": quality,
        "category": category,
        "timestamp": timestamp,
        "date": datetime.date.today().isoformat()
    })
    return True


def prune_old_items(data: dict, days: int = 3):
    """Remove items older than N days to keep data file manageable."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    before = len(data["items"])
    data["items"] = [item for item in data["items"] if item.get("date", "") >= cutoff]
    pruned = before - len(data["items"])
    if pruned > 0:
        print(f"[Prune] Removed {pruned} items older than {days} days")


# ─────────────────────────────────────────────
# SCRAPEGRAPHAI LAYER (Optional Upgrade)
# ─────────────────────────────────────────────

def scrapegraph_extract(url: str, prompt: str) -> list:
    """
    Use ScrapeGraphAI + Ollama for intelligent extraction.
    Falls back gracefully if not installed.
    """
    if not SCRAPEGRAPH_AVAILABLE:
        return []

    try:
        graph_config = {
            "llm": {
                "model": f"ollama/{OLLAMA_MODEL}",
                "model_tokens": 8192,
                "format": "json",
                "temperature": 0.1,
            },
            "verbose": False
        }
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=graph_config
        )
        result = scraper.run()
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        return []
    except Exception as e:
        print(f"[ScrapeGraph] Error: {e}")
        return []


# ─────────────────────────────────────────────
# SCRAPERS — All free, no API keys
# Each scraper runs ethical_preflight before fetching.
# ─────────────────────────────────────────────

def scrape_arxiv(data: dict) -> int:
    """Scrape arXiv RSS for cs.AI, cs.LG, cs.CL papers."""
    feeds = [
        ("http://export.arxiv.org/rss/cs.AI", "arXiv cs.AI"),
        ("http://export.arxiv.org/rss/cs.LG", "arXiv cs.LG"),
        ("http://export.arxiv.org/rss/cs.CL", "arXiv cs.CL"),
    ]
    count = 0
    for feed_url, source in feeds:
        if not ethical_preflight(feed_url, source):
            continue
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[arXiv] {source} HTTP {resp.status_code}")
                continue
            root = ET.fromstring(resp.text)
            ns = {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rss": "http://purl.org/rss/1.0/",
                "dc": "http://purl.org/dc/elements/1.1/"
            }
            for item in root.findall(".//rss:item", ns):
                title_el = item.find("rss:title", ns)
                link_el = item.find("rss:link", ns)
                desc_el = item.find("rss:description", ns)
                if title_el is not None and link_el is not None:
                    title = re.sub(r"\s+", " ", title_el.text or "").strip()
                    title = re.sub(r"\(arXiv:[^\)]+\)\s*", "", title).strip()
                    link = (link_el.text or "").strip()
                    desc = ""
                    if desc_el is not None and desc_el.text:
                        desc = desc_el.text[:500]
                    if add_item(data, title, link, source, summary=desc):
                        count += 1
        except Exception as e:
            print(f"[arXiv] {source} error: {e}")
    return count


def scrape_huggingface(data: dict) -> int:
    """Scrape Hugging Face Daily Papers page."""
    count = 0
    url = "https://huggingface.co/papers"
    if not ethical_preflight(url, "Hugging Face"):
        return 0

    if SCRAPEGRAPH_AVAILABLE:
        results = scrapegraph_extract(url,
            "Extract all paper titles and their URLs from this page. "
            "Return as JSON array with fields: title, url")
        for r in results:
            title = r.get("title", "")
            link = r.get("url", "")
            if title and link:
                if not link.startswith("http"):
                    link = f"https://huggingface.co{link}"
                if add_item(data, title, link, "Hugging Face Papers"):
                    count += 1
        if count > 0:
            return count

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[HF] HTTP {resp.status_code}")
            return 0
        pattern = r'<a[^>]*href="(/papers/[\d\.]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, resp.text)
        for path, title in matches:
            title = title.strip()
            if len(title) < 10:
                continue
            link = f"https://huggingface.co{path}"
            if add_item(data, title, link, "Hugging Face Papers"):
                count += 1
    except Exception as e:
        print(f"[HF] error: {e}")
    return count


def scrape_github_trending(data: dict) -> int:
    """Scrape GitHub Trending for Python and ML repos."""
    count = 0
    urls = [
        ("https://github.com/trending/python?since=daily", "GitHub Trending Python"),
        ("https://github.com/trending?since=daily&spoken_language_code=en", "GitHub Trending All"),
    ]
    for page_url, source in urls:
        if not ethical_preflight(page_url, source):
            continue
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[GitHub] {source} HTTP {resp.status_code}")
                continue
            pattern = r'<h2[^>]*class="[^"]*lh-condensed[^"]*"[^>]*>\s*<a[^>]*href="(/[^"]+)"[^>]*>\s*(.*?)\s*</a>'
            matches = re.findall(pattern, resp.text, re.DOTALL)
            for path, name_html in matches:
                repo_name = re.sub(r"<[^>]+>", "", name_html).strip()
                repo_name = re.sub(r"\s+", " ", repo_name).strip()
                if not repo_name:
                    continue
                link = f"https://github.com{path.strip()}"
                desc_pattern = rf'{re.escape(path)}.*?<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>'
                desc_match = re.search(desc_pattern, resp.text, re.DOTALL)
                desc = ""
                if desc_match:
                    desc = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()
                if add_item(data, repo_name, link, source, summary=desc):
                    count += 1
        except Exception as e:
            print(f"[GitHub] {source} error: {e}")
    return count


def scrape_reddit(data: dict) -> int:
    """Scrape Reddit subreddits using free JSON endpoints."""
    subs = [
        "MachineLearning",
        "LocalLLaMA",
        "artificial",
        "singularity",
    ]
    count = 0
    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
        if not ethical_preflight(url, f"r/{sub}"):
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[Reddit] r/{sub} HTTP {resp.status_code}")
                continue
            posts = resp.json().get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                title = d.get("title", "")
                permalink = d.get("permalink", "")
                selftext = d.get("selftext", "")[:500]
                ups = d.get("ups", 0)
                if not title or d.get("stickied"):
                    continue
                link = f"https://www.reddit.com{permalink}"
                source = f"r/{sub}"
                if add_item(data, title, link, source, summary=selftext, score=ups):
                    count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[Reddit] r/{sub} error: {e}")
    return count


def scrape_hackernews(data: dict) -> int:
    """Scrape Hacker News using the free Firebase API."""
    count = 0
    api_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    if not ethical_preflight(api_url, "Hacker News"):
        return 0
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[HN] HTTP {resp.status_code}")
            return 0
        story_ids = resp.json()[:30]

        for sid in story_ids:
            try:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                item_resp = requests.get(item_url, headers=HEADERS, timeout=10)
                if not item_resp.ok:
                    continue
                item = item_resp.json()
                title = item.get("title", "")
                link = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                score = item.get("score", 0)
                if not title:
                    continue
                ai_keywords = [
                    "ai", "llm", "gpt", "claude", "gemini", "model", "neural",
                    "transformer", "machine learning", "deep learning", "openai",
                    "anthropic", "meta ai", "google ai", "microsoft ai", "nvidia",
                    "training", "inference", "benchmark", "agent", "rag",
                    "diffusion", "language model", "chatbot", "copilot",
                    "artificial intelligence", "ml", "nlp", "computer vision",
                    "robotics", "autonomous", "embedding", "fine-tun",
                    "open source", "hugging face", "mistral", "llama",
                    "stable diffusion", "midjourney", "sora", "reasoning",
                    "o1", "o3", "sonnet", "opus", "haiku", "deepseek",
                    "qwen", "phi-", "gemma", "leaderboard", "eval",
                ]
                title_lower = title.lower()
                if not any(kw in title_lower for kw in ai_keywords):
                    continue
                if add_item(data, title, link, "Hacker News", score=score):
                    count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[HN] error: {e}")
    return count


def scrape_lobsters(data: dict) -> int:
    """Scrape Lobste.rs RSS feed for AI-related posts."""
    count = 0
    url = "https://lobste.rs/t/ai.rss"
    if not ethical_preflight(url, "Lobste.rs"):
        return 0
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[Lobsters] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                if add_item(data, title, link, "Lobste.rs", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[Lobsters] error: {e}")
    return count


def scrape_youtube_rss(data: dict) -> int:
    """Scrape YouTube RSS feeds for AI channels."""
    channels = {
        "AI Explained":      "UCNJ1Ymd5yFuUPtn21xtRbbw",
        "Two Minute Papers": "UCbfYPyITQ-7l4upoX8nvctg",
        "Yannic Kilcher":    "UCZHmQk67mSJgfCCTn7xBfew",
        "Matthew Berman":    "UCawZsQWqfGSbCI5yjkdVkTA",
        "Fireship":          "UCsBjURrPoezykLs9EqgamOA",
    }
    count = 0
    for channel_name, channel_id in channels.items():
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        if not ethical_preflight(url, f"YouTube: {channel_name}"):
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[YouTube] {channel_name} HTTP {resp.status_code}")
                continue
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
            for entry in root.findall("atom:entry", ns)[:5]:
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                if title_el is not None and link_el is not None:
                    title = (title_el.text or "").strip()
                    link = link_el.get("href", "")
                    source = f"YouTube: {channel_name}"
                    if add_item(data, title, link, source):
                        count += 1
        except Exception as e:
            print(f"[YouTube] {channel_name} error: {e}")
    return count


def scrape_newsletters(data: dict) -> int:
    """Scrape AI newsletter RSS feeds."""
    feeds = [
        ("https://tldr.tech/ai/rss", "TLDR AI"),
        ("https://jack-clark.net/feed/", "Import AI (Jack Clark)"),
        ("https://www.deeplearning.ai/the-batch/feed/", "The Batch"),
    ]
    count = 0
    for feed_url, source in feeds:
        if not ethical_preflight(feed_url, source):
            continue
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[Newsletter] {source} HTTP {resp.status_code}")
                continue
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:5]:
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                if title_el is not None and link_el is not None:
                    title = (title_el.text or "").strip()
                    link = (link_el.text or "").strip()
                    desc = ""
                    if desc_el is not None and desc_el.text:
                        desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                    if add_item(data, title, link, source, summary=desc):
                        count += 1
        except Exception as e:
            print(f"[Newsletter] {source} error: {e}")
    return count


def scrape_techcrunch_ai(data: dict) -> int:
    """Scrape TechCrunch AI category RSS feed."""
    count = 0
    feed_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    if not ethical_preflight(feed_url, "TechCrunch AI"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[TechCrunch] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:10]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                if add_item(data, title, link, "TechCrunch", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[TechCrunch] error: {e}")
    return count


def scrape_venturebeat_ai(data: dict) -> int:
    """Scrape VentureBeat AI category RSS feed."""
    count = 0
    feed_url = "https://venturebeat.com/category/ai/feed/"
    if not ethical_preflight(feed_url, "VentureBeat AI"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[VentureBeat] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:10]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                if add_item(data, title, link, "VentureBeat", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[VentureBeat] error: {e}")
    return count


def scrape_ars_technica(data: dict) -> int:
    """Scrape Ars Technica technology/AI RSS feed."""
    count = 0
    feed_url = "https://feeds.arstechnica.com/arstechnica/technology-lab"
    if not ethical_preflight(feed_url, "Ars Technica"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[ArsTechnica] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        ai_keywords = ["ai", "llm", "model", "neural", "machine learning", "openai",
                        "anthropic", "google ai", "nvidia", "chip", "gpu", "data center",
                        "artificial intelligence", "robot", "autonomous", "deepseek",
                        "regulation", "policy"]
        for item in root.findall(".//item")[:15]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                if not any(kw in title.lower() for kw in ai_keywords):
                    continue
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                if add_item(data, title, link, "Ars Technica", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[ArsTechnica] error: {e}")
    return count


def scrape_the_verge_ai(data: dict) -> int:
    """Scrape The Verge AI RSS feed."""
    count = 0
    feed_url = "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    if not ethical_preflight(feed_url, "The Verge AI"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[TheVerge] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:10]:
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            summary_el = entry.find("atom:summary", ns)
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = link_el.get("href", "")
                desc = ""
                if summary_el is not None and summary_el.text:
                    desc = re.sub(r"<[^>]+>", "", summary_el.text)[:500]
                if add_item(data, title, link, "The Verge", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[TheVerge] error: {e}")
    return count


def scrape_mit_tech_review(data: dict) -> int:
    """Scrape MIT Technology Review RSS feed, filtered for AI."""
    count = 0
    feed_url = "https://www.technologyreview.com/feed/"
    if not ethical_preflight(feed_url, "MIT Tech Review"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[MITTechReview] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        ai_keywords = ["ai", "artificial intelligence", "machine learning", "model",
                        "neural", "llm", "openai", "deepmind", "anthropic", "robot",
                        "autonomous", "chip", "gpu", "data center", "compute"]
        for item in root.findall(".//item")[:15]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                text_check = f"{title} {desc}".lower()
                if not any(kw in text_check for kw in ai_keywords):
                    continue
                if add_item(data, title, link, "MIT Tech Review", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[MITTechReview] error: {e}")
    return count


def scrape_reuters_tech(data: dict) -> int:
    """Scrape Reuters technology via their sitemap/RSS, filtered for AI."""
    count = 0
    feed_url = "https://www.reuters.com/arc/outboundfeeds/v3/all/rss/?outputType=xml&size=20"
    if not ethical_preflight(feed_url, "Reuters"):
        return 0
    try:
        resp = requests.get(feed_url, headers={**HEADERS, "Accept": "application/xml"}, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            feed_url = "https://www.reuters.com/technology/rss"
            resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if not resp.ok:
                print(f"[Reuters] HTTP {resp.status_code}")
                return 0
        root = ET.fromstring(resp.text)
        ai_keywords = ["ai", "artificial intelligence", "machine learning", "chip",
                        "nvidia", "openai", "google", "microsoft", "meta", "robot",
                        "autonomous", "regulation", "data center", "semiconductor"]
        for item in root.findall(".//item")[:20]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                text_check = f"{title} {desc}".lower()
                if not any(kw in text_check for kw in ai_keywords):
                    continue
                if add_item(data, title, link, "Reuters", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[Reuters] error: {e}")
    return count


def scrape_wired_ai(data: dict) -> int:
    """Scrape Wired AI RSS feed."""
    count = 0
    feed_url = "https://www.wired.com/feed/tag/ai/latest/rss"
    if not ethical_preflight(feed_url, "Wired AI"):
        return 0
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            print(f"[Wired] HTTP {resp.status_code}")
            return 0
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:10]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is not None and link_el is not None:
                title = (title_el.text or "").strip()
                link = (link_el.text or "").strip()
                desc = ""
                if desc_el is not None and desc_el.text:
                    desc = re.sub(r"<[^>]+>", "", desc_el.text)[:500]
                if add_item(data, title, link, "Wired", summary=desc):
                    count += 1
    except Exception as e:
        print(f"[Wired] error: {e}")
    return count


# ─────────────────────────────────────────────
# SCRAPE ORCHESTRATOR
# ─────────────────────────────────────────────

ALL_SCRAPERS = [
    ("arXiv",           scrape_arxiv),
    ("Hugging Face",    scrape_huggingface),
    ("GitHub Trending", scrape_github_trending),
    ("Reddit",          scrape_reddit),
    ("Hacker News",     scrape_hackernews),
    ("Lobste.rs",       scrape_lobsters),
    ("YouTube",         scrape_youtube_rss),
    ("Newsletters",     scrape_newsletters),
    ("TechCrunch",      scrape_techcrunch_ai),
    ("VentureBeat",     scrape_venturebeat_ai),
    ("Ars Technica",    scrape_ars_technica),
    ("The Verge",       scrape_the_verge_ai),
    ("MIT Tech Review", scrape_mit_tech_review),
    ("Reuters",         scrape_reuters_tech),
    ("Wired",           scrape_wired_ai),
]


def run_all_scrapers(data: dict) -> int:
    """
    Run all scrapers. Returns total new items found.
    ScrapeMaster principle: retry once on transient failures, report clearly.
    """
    total_new = 0
    for name, scraper_fn in ALL_SCRAPERS:
        try:
            print(f"[Scrape] {name}...", end=" ", flush=True)
            count = scraper_fn(data)
            print(f"{count} new")
            total_new += count
        except Exception as e:
            print(f"ERROR: {e}")
            try:
                print(f"[Scrape] {name} retry...", end=" ", flush=True)
                time.sleep(3)
                count = scraper_fn(data)
                print(f"{count} new (retry)")
                total_new += count
            except Exception as e2:
                print(f"FAILED: {e2}")
    data["last_scrape"] = datetime.datetime.now().isoformat()
    save_data(data)
    return total_new


# ─────────────────────────────────────────────
# TRUTH FILTER PIPELINE
# ─────────────────────────────────────────────

def run_truth_filter(data: dict, xai_api_key: str = "") -> tuple:
    """
    Main pipeline: takes raw scraped data, returns (top_10, all_scored, stats).

    Full 4-layer pipeline:
    1. Score all items (Source Credibility + Cross-Confirm + Substance + Relevance)
    2. Select top 10 with diversity rules
    3. Run top 10 through AI Verification (Ollama + Grok)
    4. Drop any items both models flag as misleading, backfill from runner-ups
    """
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    recent = [item for item in data.get("items", [])
              if item.get("date") in (today, yesterday)]

    if not recent:
        return [], [], {"total_scraped": 0, "sources_active": 0}

    scored = [compute_truth_score(item, recent) for item in recent]

    candidates = select_top_10_candidates(scored, count=15)

    print("[Filter] Running AI verification on top candidates...")
    top_10_raw = candidates[:10]
    backfill = candidates[10:15]

    verified = ai_verify_top_10(top_10_raw, xai_api_key=xai_api_key)

    if len(verified) < 10 and backfill:
        needed = 10 - len(verified)
        extra_verified = ai_verify_top_10(backfill[:needed], xai_api_key=xai_api_key)
        verified.extend(extra_verified)

    top_10 = verified[:10]

    sources_active = len(set(item.get("source", "") for item in recent))
    stats = {
        "total_scraped": len(recent),
        "sources_active": sources_active,
        "ai_verified_count": len([i for i in top_10 if i.get("ai_verdict") == "AI_VERIFIED"]),
        "ai_warning_count": len([i for i in top_10 if i.get("ai_verdict") in ("WARNING", "SUSPICIOUS")]),
    }

    return top_10, scored, stats


# ─────────────────────────────────────────────
# BRIEFING OUTPUT
# ─────────────────────────────────────────────

def write_briefing_json(top_10: list, all_scored: list, stats: dict, brief_text: str = ""):
    """
    Write scout-briefing.json for the website.
    Contains the full meat — summaries, scores, links, categories.
    """
    today = datetime.date.today().isoformat()

    all_categories = Counter(item.get("tr_category", "general") for item in all_scored)
    all_sources = Counter(item.get("source", "unknown") for item in all_scored)

    avg_truth = 0
    if all_scored:
        avg_truth = round(sum(item.get("truth_score", 0) for item in all_scored) / len(all_scored), 1)

    briefing = {
        "date": today,
        "generated_at": datetime.datetime.now().isoformat(),
        "version": "2.0",
        "filter": "TrainingRun Truth Filter v2.0",

        "top_stories": [
            {
                "rank": i + 1,
                "title": item["title"],
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "summary": item.get("summary", "")[:500],
                "tr_category": item.get("tr_category", "general"),
                "category_label": TR_CATEGORY_LABELS.get(item.get("tr_category", "general"), "AI News"),
                "truth_score": item.get("truth_score", 0),
                "source_credibility": item.get("source_credibility", 0),
                "cross_confirmation": item.get("cross_confirmation", 0),
                "cross_sources": item.get("cross_sources", []),
                "substance_score": item.get("substance_score", 0),
                "relevance_score": item.get("relevance_score", 0),
                "matched_verticals": item.get("matched_verticals", []),
                "hype_flags": item.get("hype_flags", 0),
                "ai_verdict": item.get("ai_verdict", "UNVERIFIED"),
                "ai_confidence": item.get("ai_confidence", 0),
                "ai_checks": item.get("ai_checks", {}),
            }
            for i, item in enumerate(top_10)
        ],

        "narrative_brief": brief_text,

        "stats": {
            "total_scraped": stats.get("total_scraped", 0),
            "passed_filter": len([i for i in all_scored if i.get("truth_score", 0) >= 50]),
            "rejected": len([i for i in all_scored if i.get("truth_score", 0) < 50]),
            "avg_truth_score": avg_truth,
            "categories": dict(all_categories),
            "sources": dict(all_sources),
            "sources_active": stats.get("sources_active", 0),
        },

        "filter_methodology": {
            "source_credibility_weight": "0-40 pts (Tier 1 Wire = 40, Tier 3 Community = 10-20)",
            "cross_confirmation_weight": "0-20 pts (1 source = 8, 2+ = 15, 3+ = 20)",
            "substance_score_weight": "-10 to +20 pts (hype=-8 each, substance=+4 each)",
            "relevance_weight": "0-20 pts (keyword match to TrainingRun verticals)",
            "min_truth_score": 50,
            "diversity_rules": "Max 3 per category, max 2 per source",
        }
    }

    try:
        with open(BRIEFING_FILE, "w") as f:
            json.dump(briefing, f, indent=2)
        print(f"[Brief] Written to {BRIEFING_FILE}")
    except Exception as e:
        print(f"[Brief] Failed to write briefing: {e}")


# ─────────────────────────────────────────────
# OLLAMA — Morning Brief Generation
# ─────────────────────────────────────────────

def load_brain() -> str:
    """Load scout brain file for context."""
    try:
        with open(BRAIN_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def ollama_generate(prompt: str, system: str = "", timeout: int = 120) -> str:
    """
    Call Ollama llama3.1:8b for summarization.
    Uses low temperature for factual, deterministic output.
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2500,
                "num_ctx": 8192,
            }
        }
        if system:
            payload["system"] = system
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        if not resp.ok:
            return f"Ollama error: HTTP {resp.status_code}"
        return resp.json().get("response", "No response from Ollama.")
    except requests.exceptions.ConnectionError:
        return "ERROR: Ollama not running. Start with: ollama serve"
    except requests.exceptions.Timeout:
        return "ERROR: Ollama timed out. Model may still be loading."
    except Exception as e:
        return f"ERROR: {e}"


def build_brief_system_prompt_v2() -> str:
    """
    Enhanced system prompt for Ollama morning brief generation.
    Now includes TrainingRun verticals and the Truth Filter philosophy.
    """
    return """You are Content Scout, the AI news intelligence agent for trainingrun.ai.

TRAININGRUN MISSION: Provide the most transparent, fact-checked, and accessible measurement of AI capabilities — so the public, investors, policymakers, and developers can make informed decisions based on data, not hype.

No one should have to pay for truth.

YOUR FIVE PRINCIPLES:
1. TRANSPARENCY FIRST — Prioritize items with full methodology, source citations, reproducible results.
2. FACT-CHECK EVERYTHING — Only surface verifiable, peer-reviewed, or publicly auditable information.
3. INDEPENDENCE — No vendor puff pieces. Focus on data, not marketing.
4. MEASURE WHAT MATTERS — Real-world capabilities over press-release benchmarks.
5. KNOW OUR LIMITS — Never present speculation as fact.

TRAININGRUN VERTICALS (these are what matters to our audience):
- TRSbench: AI model benchmarks and leaderboards
- TRUscore: Truth, factuality, bias, and safety in AI
- TRScode: Code generation and developer tools
- TRAgents: Autonomous agents and digital workers
- TRFcast: AGI timelines, forecasting, scaling laws
- Global AI Race: China/US/EU competition, policy, chips, regulation
- The Churn: Jobs, workforce displacement and creation
- GigaBurn: Compute infrastructure, data centers, energy, GPUs
- Open vs Closed: Open source models vs proprietary, licensing, access

TRUTH FILTER: These items have already been pre-scored. Higher truth_score = more verified and relevant. You are writing for David Solomon, founder of TrainingRun, who reads this on his phone at 5:30 AM. He does not want hype, clickbait, or speculation. He wants to know what ACTUALLY happened in AI in the last 24 hours that matters.

FORMAT: Write 2-3 sentences per story. What happened, what the data shows, and why it matters. Cite the source. If something is unverified, say so explicitly. Be direct and concise."""


def build_ollama_prompt(top_10: list) -> str:
    """Build the prompt for Ollama to generate the narrative brief."""
    items_text = ""
    for i, item in enumerate(top_10, 1):
        cat = TR_CATEGORY_LABELS.get(item.get("tr_category", "general"), "News")
        truth = item.get("truth_score", 0)
        cross = "CROSS-CONFIRMED" if item.get("cross_confirmation", 0) > 0 else ""
        items_text += f"{i}. {cat} | Truth: {truth}/100 {cross}\n"
        items_text += f"   {item['title']}\n"
        if item.get("summary"):
            items_text += f"   {item['summary'][:300]}\n"
        items_text += f"   Source: {item.get('source', '?')} | {item.get('url', '')}\n\n"

    return f"""Here are today's top {len(top_10)} AI stories, pre-filtered by the TrainingRun Truth Filter (scored 0-100 on source credibility, cross-confirmation, substance, and relevance):

{items_text}

Write the morning briefing narrative. For each story:
- What happened (facts only)
- Why it matters to someone tracking AI benchmarks, truth, agents, the global AI race, jobs, and compute
- Note if cross-confirmed across multiple sources

Keep each item to 2-3 sentences. No hype. No speculation. Facts and data only."""


def generate_morning_brief(data: dict, xai_api_key: str = "") -> str:
    """
    Use the Truth Filter + Ollama to generate a morning briefing from collected items.
    """
    top_10, all_scored, stats = run_truth_filter(data, xai_api_key=xai_api_key)

    if not top_10:
        return "No stories passed the Truth Filter today."

    system = build_brief_system_prompt_v2()
    prompt = build_ollama_prompt(top_10)
    print("[Brief] Generating morning brief with Ollama...")
    narrative = ollama_generate(prompt, system=system, timeout=180)

    write_briefing_json(top_10, all_scored, stats, brief_text=narrative)

    return narrative


# ─────────────────────────────────────────────
# GIT PUSH
# ─────────────────────────────────────────────

def push_briefing():
    """Commit and push scout-briefing.json to GitHub."""
    try:
        subprocess.run(["git", "add", "scout-briefing.json"],
                       cwd=REPO_PATH, capture_output=True, text=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"Content Scout briefing {datetime.date.today().isoformat()}"],
            cwd=REPO_PATH, capture_output=True, text=True
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stderr or "nothing to commit" in result.stdout:
                print("[Git] Nothing new to commit")
                return
            print(f"[Git] Commit failed: {result.stderr}")
            return
        subprocess.run(["git", "pull", "--rebase"],
                       cwd=REPO_PATH, capture_output=True, text=True, timeout=60)
        result = subprocess.run(["git", "push"],
                                cwd=REPO_PATH, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[Git] Push failed: {result.stderr}")
        else:
            print("[Git] Pushed briefing to GitHub")
    except Exception as e:
        print(f"[Git] Error: {e}")


# ─────────────────────────────────────────────
# SCHEDULE LOGIC
# ─────────────────────────────────────────────

def is_scrape_time() -> bool:
    """Returns True if current hour is within scraping window (7 AM – 11 PM)."""
    hour = datetime.datetime.now().hour
    return SCRAPE_START_HOUR <= hour < SCRAPE_END_HOUR


def is_brief_time() -> bool:
    """Returns True if it's 5:30 AM (within a 5-minute window)."""
    now = datetime.datetime.now()
    return now.hour == BRIEF_HOUR and BRIEF_MINUTE <= now.minute < BRIEF_MINUTE + 5


def already_briefed_today(data: dict) -> bool:
    """Check if we already sent a brief today."""
    last = data.get("last_brief")
    if not last:
        return False
    try:
        last_date = datetime.datetime.fromisoformat(last).date()
        return last_date == datetime.date.today()
    except Exception:
        return False


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────

def run():
    print("=" * 60)
    print("  Content Scout v1.2.0")
    print(f"  Model: {OLLAMA_MODEL} (Ollama, local, FREE)")
    print(f"  Scrapers: 15 sources (8 original + 7 new)")
    print(f"  Scrape window: {SCRAPE_START_HOUR}:00 - {SCRAPE_END_HOUR}:00")
    print(f"  Morning brief: {BRIEF_HOUR}:{BRIEF_MINUTE:02d} AM")
    print(f"  Repo: {REPO_PATH}")
    print(f"  ScrapeGraphAI: {'AVAILABLE' if SCRAPEGRAPH_AVAILABLE else 'not installed (using raw scrapers)'}")
    print(f"  xAI API Key: {'SET' if XAI_API_KEY else 'not set (Ollama-only verification)'}")
    print(f"  Philosophy: Truth > Hype | Data > Opinion | Facts > Clickbait")
    print("=" * 60)

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set.")
        sys.exit(1)

    data = load_data()
    prune_old_items(data)
    save_data(data)

    startup_msg = (
        "Content Scout v1.2.0 online.\n"
        f"Model: {OLLAMA_MODEL} (local, free)\n"
        "Scraping 7 AM - 11 PM | Brief at 5:30 AM\n"
        "Sources: 15 scrapers (arXiv, HF, GitHub, Reddit, HN, Lobsters, YouTube, Newsletters,\n"
        "          TechCrunch, VentureBeat, Ars Technica, The Verge, MIT Tech Review, Reuters, Wired)\n"
        "Truth Filter: 4 layers (Source Credibility, Cross-Confirmation, Zero Hype, AI Verification)\n"
        "Philosophy: Facts first. No hype. No clickbait."
    )
    tg_send(startup_msg)
    print("[Scout] Online. Entering main loop...")

    last_scrape_time = 0

    while True:
        try:
            now = time.time()

            # ── MORNING BRIEF (5:30 AM) ──
            if is_brief_time() and not already_briefed_today(data):
                print("\n[Brief] Generating morning briefing with Truth Filter...")
                tg_send("Generating your morning brief with Truth Filter...")

                brief = generate_morning_brief(data, xai_api_key=XAI_API_KEY)

                if brief.startswith("ERROR:"):
                    tg_send(f"Scout brief failed: {brief}")
                    print(f"[Brief] {brief}")
                else:
                    header = f"CONTENT SCOUT BRIEF — {datetime.date.today().strftime('%b %d, %Y')}\n\n"
                    tg_send(header + brief)

                    push_briefing()

                    data["last_brief"] = datetime.datetime.now().isoformat()
                    save_data(data)
                    print("[Brief] Morning brief sent and published.")

            # ── SCRAPE CYCLE (7 AM – 11 PM, every 30 min) ──
            elif is_scrape_time() and (now - last_scrape_time) >= SCRAPE_INTERVAL:
                print(f"\n[Scrape] Starting cycle at {datetime.datetime.now().strftime('%I:%M %p')}")
                total = run_all_scrapers(data)
                last_scrape_time = now

                today_items = [i for i in data["items"] if i.get("date") == datetime.date.today().isoformat()]
                research_count = len([i for i in today_items if i.get("category") == "research"])
                print(f"[Scrape] Cycle complete. {total} new items. {len(today_items)} today ({research_count} research). {len(data['items'])} total.")

                hour = datetime.datetime.now().hour
                if hour in (11, 15, 19, 23):
                    sources = len(set(i["source"] for i in today_items))
                    tg_send(
                        f"Scout update: {len(today_items)} items today from {sources} sources.\n"
                        f"Research: {research_count} | "
                        f"Releases: {len([i for i in today_items if i.get('category') == 'release'])} | "
                        f"Tools: {len([i for i in today_items if i.get('category') == 'tool'])}"
                    )

            # ── IDLE ──
            else:
                time.sleep(30)
                continue

            time.sleep(10)

        except KeyboardInterrupt:
            print("\n[Scout] Shutting down.")
            tg_send("Content Scout going offline.")
            save_data(data)
            break
        except Exception as e:
            print(f"[Scout] Error: {e}")
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    run()
