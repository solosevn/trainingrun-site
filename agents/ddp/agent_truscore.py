#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
AGENT TRUSCORE — TRUscore Daily Scraper  V1.4  TEST BUILD
trainingrun.ai | solosevn/trainingrun-site
Bible: TRUscore V1.4 (March 2026)
════════════════════════════════════════════════════════════════════

9 sub-metrics, 5 pillars:

  TRUTHFULNESS (35%)
    1. SimpleQA Correct %              llm-stats.com          0.13
    2. FACTS Benchmark Average         kaggle/google/facts    0.12
    3. TruthfulQA MC Score             llm-stats.com          0.10

  HALLUCINATION (20%)
    4. HalluHard Rate (inverted)       halluhard.com          0.12
    5. Vectara Hallucination (inverted)huggingface.co         0.08

  REASONING (20%)
    6. HLE Accuracy                    lastexam.ai            0.10
    7. LiveBench Global Avg            livebench.ai           0.10

  NEUTRALITY (15%)
    8. Anthropic Paired Prompts        anthropic.com          0.15

  RESPONSE QUALITY (10%)
    9. TSArena Human Preference        trainingrun.ai/tsarena 0.10

Qualification: ≥4 of 9 sub-metrics with non-null scores.
Scoring: Option A — null sources excluded, weights renormalized.
Inversion: Hallucination rates INVERTED (lower rate = higher score).

Usage:
  python3 agent_truscore.py              # live run (push to GitHub)
  python3 agent_truscore.py --dry-run    # scrape + print, NO write/push
  python3 agent_truscore.py --test-telegram  # test Telegram only

DRY RUN TEST: python3 ~/trainingrun-site/agent_truscore.py --dry-run
════════════════════════════════════════════════════════════════════
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re, time
from datetime import date
from pathlib import Path

# ── dependency guard ──────────────────────────────────────────────
for pkg, hint in [
    ("playwright", "pip3 install playwright && python3 -m playwright install chromium"),
    ("bs4",        "pip3 install beautifulsoup4"),
    ("telegram",   "pip3 install python-telegram-bot"),
    ("requests",   "pip3 install requests"),
]:
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: {hint}")

import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from telegram import Bot

# ── try to import model_names (optional for standalone test) ──────
try:
    from model_names import match_name, canonicalize
    HAS_MODEL_NAMES = True
except ImportError:
    HAS_MODEL_NAMES = False
    def match_name(name, existing):
        """Fallback: case-insensitive + substring + fuzzy match."""
        import difflib as _dl
        nl = name.lower().strip()
        el = [e.lower().strip() for e in existing]
        # 1. exact case-insensitive
        for i, e in enumerate(el):
            if nl == e:
                return existing[i]
        # 2. substring (scraped name contained in roster name or vice versa)
        for i, e in enumerate(el):
            if nl and e and (nl in e or e in nl) and min(len(nl), len(e)) >= 4:
                return existing[i]
        # 3. fuzzy (difflib, threshold 0.82)
        close = _dl.get_close_matches(nl, el, n=1, cutoff=0.82)
        if close:
            return existing[el.index(close[0])]
        return None
    def canonicalize(name):
        return name


def _normalize_model_name(raw: str) -> str:
    """
    Strip API-version cruft so "gpt-4o-2024-08-06" → "gpt-4o" and
    "claude-3-5-sonnet-20241022" → "claude-3-5-sonnet".
    """
    n = raw.strip()
    if '/' in n:
        n = n.split('/')[-1]
    n = re.sub(r'[-_]\d{4}[-_]\d{2}[-_]\d{2}$', '', n)
    n = re.sub(r'[-_]\d{8}$', '', n)
    n = re.sub(
        r'[-_](instruct|chat|base|it|preview|latest|exp|hf|gguf|awq|gptq)$',
        '', n, flags=re.IGNORECASE)
    return n.strip()


def remap_to_roster_names(
        raw_values: dict,
        roster_names: list) -> dict:
    """
    Translate scraped model names → canonical roster names before scoring.
    Filters pure-numeric entries (chart coordinates, etc.).
    """
    result: dict = {}
    for scraped, score in raw_values.items():
        if re.match(r'^-?\d+\.?\d*$', scraped.strip()):
            continue
        canonical = match_name(scraped, roster_names)
        if canonical is None:
            cleaned = _normalize_model_name(scraped)
            if cleaned and cleaned != scraped:
                canonical = match_name(cleaned, roster_names)
        # Extra pass: try replacing hyphens with spaces
        # e.g. "Claude-Opus-4.5" → "Claude Opus 4.5" to match roster
        if canonical is None:
            spaced = re.sub(r'(?<=[A-Za-z])-(?=[A-Za-z])', ' ', scraped)
            if spaced != scraped:
                canonical = match_name(spaced, roster_names)
        result[canonical if canonical else scraped] = score
    return result

# ── logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("truscore_v14")

# ── CONFIG ────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH", str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "data" / "data/truscore-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run" in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ── TRUscore Bible V1.4 weights ───────────────────────────────────
WEIGHTS = {
    # Pillar 1: Truthfulness (35%)
    "truthfulness_simpleqa":    0.13,
    "truthfulness_facts":       0.12,
    "truthfulness_truthfulqa":  0.10,
    # Pillar 2: Hallucination (20%)
    "hallucination_halluhard":  0.12,
    "hallucination_vectara":    0.08,
    # Pillar 3: Reasoning (20%)
    "reasoning_hle":            0.10,
    "reasoning_livebench":      0.10,
    # Pillar 4: Neutrality (15%)
    "neutrality_anthropic":     0.15,
    # Pillar 5: Response Quality (10%)
    "quality_tsarena":          0.10,
}

_wsum = round(sum(WEIGHTS.values()), 10)
assert abs(_wsum - 1.0) < 1e-9, f"Weights sum to {_wsum}, not 1.0!"

QUALIFICATION_MIN_SOURCES = 3   # ≥3 of 9 sub-metrics (raise to 4 on live server with full scrapers)

PILLAR_SOURCES = {
    "truthfulness":     ["truthfulness_simpleqa", "truthfulness_facts",
                         "truthfulness_truthfulqa"],
    "hallucination":    ["hallucination_halluhard", "hallucination_vectara"],
    "reasoning":        ["reasoning_hle", "reasoning_livebench"],
    "neutrality":       ["neutrality_anthropic"],
    "response_quality": ["quality_tsarena"],
}

# ── TELEGRAM ──────────────────────────────────────────────────────
def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text[:120]}")
        return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try:
        asyncio.run(_send())
    except Exception as e:
        log.warning(f"Telegram non-fatal: {e}")

# ── PLAYWRIGHT HELPERS ────────────────────────────────────────────
def playwright_get(url: str, wait_ms: int = 5000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html

def playwright_get_hfspace(url: str, wait_ms: int = 15000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        for frame in page.frames:
            if "hf.space" in frame.url:
                try:
                    frame.wait_for_load_state("networkidle", timeout=30_000)
                except Exception:
                    pass
                page.wait_for_timeout(5000)
                html = frame.content()
                browser.close()
                return html
        html = page.content()
        browser.close()
    return html

def parse_first_table(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []
    target = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = target.find_all("tr")
    if len(rows) < 2:
        return []
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    result = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if cells:
            result.append(dict(zip(headers, cells)))
    return result


# ════════════════════════════════════════════════════════════════════
#  SCRAPERS
# ════════════════════════════════════════════════════════════════════

# ── 1: SimpleQA — Truthfulness ────────────────────────────────────
def scrape_simpleqa() -> dict:
    """
    llm-stats.com/benchmarks/simpleqa
    Returns factuality {model: correct_pct} — how often model answers correctly.
    """
    factuality: dict = {}
    try:
        log.info("Scraping SimpleQA (truthfulness)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://llm-stats.com/benchmarks/simpleqa",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                return trs.map(r => {
                    const cells = r.querySelectorAll('td');
                    if (cells.length < 4) return null;
                    const nameEl = cells[1].querySelector('a') || cells[1];
                    const name = nameEl.textContent.trim().split('\\n')[0].trim();
                    const correct = parseFloat(cells[2].textContent.trim());
                    if (!name || isNaN(correct)) return null;
                    return {name, correct};
                }).filter(Boolean);
            }""")
            browser.close()

        for row in rows:
            name = row.get("name", "")
            correct = row.get("correct")
            if name and correct is not None:
                pct = round(correct * 100, 2) if correct <= 1.0 else round(correct, 2)
                if 0 < pct <= 100:
                    factuality[name] = pct

        log.info(f"  ✅ SimpleQA: {len(factuality)} models")
    except Exception as e:
        log.warning(f"  ⚠️ SimpleQA: {e}")
    return factuality


# ── 2: FACTS Benchmark — Truthfulness ────────────────────────────
def scrape_facts() -> dict:
    """
    FACTS Benchmark Suite (Google DeepMind) — kaggle.com/benchmarks/google/facts
    4 sub-benchmarks: Parametric, Search, Multimodal, Grounding.
    Uses the overall Average score. Higher = more factually accurate.
    Last updated December 6, 2025. 15+ frontier models.
    Returns {model: average_score (0-100)}
    NOTE: Kaggle renders as a React SPA with no <table> elements in headless mode.
    Uses innerText name-then-scores extraction. KNOWN_VALUES always supplement.
    """
    scores: dict = {}
    # Last-known published values (December 6, 2025) — always used as supplement
    KNOWN_VALUES = {
        "Gemini 3 Pro Preview":         68.8,
        "Gemini 2.5 Pro":               62.1,
        "GPT-5":                        61.8,
        "Grok 4":                       53.6,
        "o3":                           52.0,
        "Claude Opus 4.5":              51.3,
        "GPT-4.1":                      50.5,
        "Gemini 2.5 Flash":             50.4,
        "GPT-5.1":                      49.4,
        "Claude Sonnet 4.5 (thinking)": 47.9,
        "Claude Opus 4.1":              46.5,
        "GPT-5 mini":                   45.9,
        "Claude Sonnet 4":              42.8,
        "o4 mini":                      37.6,
        "Grok 4 Fast Reasoning":        36.0,
    }
    try:
        log.info("Scraping FACTS Benchmark (Kaggle)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://www.kaggle.com/benchmarks/google/facts",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            # Kaggle is a React SPA — no <table> elements; wait for JS render
            page.wait_for_timeout(8000)

            rows = page.evaluate("""() => {
                // Kaggle FACTS renders as flex/grid, not <table>.
                // Model names and scores appear in innerText as two separate
                // sequential blocks: all N names first, then all N avg scores.
                // Strategy: extract names (follow rank integers), then pair
                // with the first percentage of each model's score block.
                const HEADERS = ['#','Model','Average','Grounding Score','info',
                                  'Multimodal Score','Search Score','Parametric Score'];
                const text = document.body.innerText;
                const start = text.indexOf('#\\nModel');
                if (start === -1) return [];
                const section = text.substring(start, start + 8000);
                const lines = section.split('\\n').map(l => l.trim()).filter(l => l);
                const names = [];
                const avgs  = [];
                let inNames = true;
                let prevWasRank = false;
                for (let i = 0; i < lines.length; i++) {
                    const l = lines[i];
                    if (HEADERS.includes(l)) continue;
                    if (/^\\d+$/.test(l)) { prevWasRank = true; continue; }
                    if (prevWasRank && inNames && !/^\\d+\\.\\d%$/.test(l) && !/^±/.test(l)) {
                        names.push(l);
                        prevWasRank = false;
                        continue;
                    }
                    prevWasRank = false;
                    if (/^\\d{1,3}\\.\\d%$/.test(l)) {
                        inNames = false;
                        avgs.push(parseFloat(l));
                        i += 8;  // skip 4 sub-scores + 4 ±margins
                    }
                }
                return names.slice(0, avgs.length).map((n, idx) => ({name: n, avg: avgs[idx]}));
            }""")
            browser.close()

        for row in rows:
            name = row.get("name", "").strip()
            avg  = row.get("avg")
            if name and avg is not None and 0 < avg <= 100:
                scores[name] = round(avg, 2)

        live_count = len(scores)
        # Always supplement with KNOWN_VALUES for models not captured live
        for model, avg in KNOWN_VALUES.items():
            if model not in scores:
                scores[model] = avg

        if live_count == 0:
            log.info(f"  FACTS: 0 scraped — using {len(scores)} known values")
        else:
            log.info(f"  ✅ FACTS: {len(scores)} models ({live_count} live + {len(scores)-live_count} known)")
    except Exception as e:
        log.warning(f"  ⚠️ FACTS: {e} — using known values")
        scores = {**KNOWN_VALUES, **scores}
    return scores


# ── 3: TruthfulQA ─────────────────────────────────────────────────
def scrape_truthfulqa() -> dict:
    """
    llm-stats.com/benchmarks/truthfulqa
    MC1 + MC2 scores (0-100). Returns average of available sub-scores.
    Tests whether models avoid well-known misconceptions and plausible falsehoods.
    """
    scores: dict = {}
    try:
        log.info("Scraping TruthfulQA...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://llm-stats.com/benchmarks/truthfulqa",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                return trs.map(r => {
                    const cells = r.querySelectorAll('td');
                    if (cells.length < 3) return null;
                    const nameEl = cells[1].querySelector('a') || cells[1];
                    const name = nameEl.textContent.trim().split('\\n')[0].trim();
                    const mc1 = parseFloat(cells[2].textContent.trim());
                    const mc2 = cells[3] ? parseFloat(cells[3].textContent.trim()) : NaN;
                    if (!name) return null;
                    return {name, mc1, mc2};
                }).filter(Boolean);
            }""")
            browser.close()

        def clean_tqa_name(raw: str) -> str:
            n = raw.strip().split('\n')[0].strip()
            if '/' in n:
                n = n.split('/')[-1]
            for pfx in ['meta-', 'google-', 'openai-', 'anthropic-', 'mistralai-',
                        'deepseek-ai-', 'Qwen-', 'microsoft-', 'nvidia-']:
                if n.lower().startswith(pfx.lower()):
                    n = n[len(pfx):]
            return n.strip()

        for row in rows:
            name = row.get("name", "")
            mc1  = row.get("mc1")
            mc2  = row.get("mc2")
            if not name:
                continue
            name = clean_tqa_name(name)
            if not name or len(name) < 2:
                continue
            values = []
            for v in [mc1, mc2]:
                if v is not None and not (isinstance(v, float) and (v != v)):
                    pct = round(v * 100, 2) if v <= 1.0 else round(v, 2)
                    if 0 < pct <= 100:
                        values.append(pct)
            if values:
                scores[name] = round(sum(values) / len(values), 2)

        log.info(f"  ✅ TruthfulQA: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ TruthfulQA: {e}")
    return scores


# ── 4: HalluHard — Hallucination ─────────────────────────────────
def scrape_halluhard() -> dict:
    """
    HalluHard — halluhard.com (EPFL-backed)
    Multi-turn hallucination benchmark across 4 domains:
    Legal Cases, Research Questions, Medical Guidelines, Coding.
    Score = Hallucination Rate (lower is better). INVERTED during normalization.
    Filters -Web-Search variants so only base model scores are used.
    Returns {model: hallucination_rate (0-100)}
    """
    scores: dict = {}
    # Last-known published values (March 2026) as fallback
    # NOTE: names must match roster format (spaces, not hyphens)
    KNOWN_VALUES = {
        "GPT-5.2":           58.8,
        "Gemini 3.1 Pro":    57.1,
        "Claude Opus 4.5":   60.0,
        "Claude Opus 4.6":   60.9,
        "Gemini 3 Pro":      61.9,
        "Claude Sonnet 4.6": 63.7,
        "GPT-5 thinking":    64.8,
        "Claude Sonnet 4.5": 65.6,
        "Gemini 3 Flash":    69.5,
        "GPT-5":             71.8,
        "Grok 4":            75.3,
        "GPT-5 mini":        75.9,
        "Claude Haiku 4.5":  79.6,
    }
    try:
        log.info("Scraping HalluHard (hallucination rate)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://halluhard.com/",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                # Wait for the bar chart leaderboard to render
                page.wait_for_selector(
                    "[class*='leaderboard'], [class*='rank'], table, [class*='bar']",
                    timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(6000)

            rows = page.evaluate("""() => {
                const results = [];

                // Strategy 1: standard <table>
                const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                for (const tr of trs) {
                    const cells = tr.querySelectorAll('td');
                    if (cells.length < 2) continue;
                    const name = (cells[0].textContent || '').trim() ||
                                 (cells[1] ? cells[1].textContent.trim() : '');
                    for (let i = 1; i < cells.length; i++) {
                        const v = parseFloat(cells[i].textContent.trim());
                        if (!isNaN(v) && v > 0 && v <= 100) {
                            results.push({name: name.trim(), rate: v});
                            break;
                        }
                    }
                }
                if (results.length >= 5) return results;

                // Strategy 2: parse inner-text line by line
                // HalluHard renders as: Rank | ModelName | Score | [domain scores]
                const allText = document.body.innerText;
                const lines = allText.split('\\n').map(l => l.trim()).filter(l => l);
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    // A score line is a standalone decimal like "30.2" or "60.9"
                    if (/^\\d{1,2}\\.\\d$/.test(line)) {
                        const rate = parseFloat(line);
                        if (rate > 0 && rate <= 100) {
                            // Model name is on the line before the score
                            for (let j = i - 1; j >= Math.max(0, i - 4); j--) {
                                const candidate = lines[j];
                                if (candidate && candidate.length >= 3 &&
                                    !/^\\d+$/.test(candidate) &&
                                    !/^(Domain|Turn|All|Average|DOMAIN|TURN|Overview)/i.test(candidate) &&
                                    candidate.length <= 80) {
                                    results.push({name: candidate, rate});
                                    break;
                                }
                            }
                        }
                    }
                }
                return results;
            }""")
            browser.close()

        # Deduplicate: skip Web-Search variants, keep lowest rate per model
        _SKIP_TOKENS = ["web-search", "websearch", "web search"]
        raw: dict = {}
        for row in rows:
            name = row.get("name", "").strip()
            rate = row.get("rate")
            if not name or rate is None or not (0 < rate <= 100):
                continue
            if any(tok in name.lower() for tok in _SKIP_TOKENS):
                log.debug(f"  HalluHard: skipping web-search variant '{name}'")
                continue
            # Keep lowest (best) hallucination rate if duplicate
            if name not in raw or rate < raw[name]:
                raw[name] = round(rate, 2)
        scores = raw

        # Always supplement with KNOWN_VALUES for any model not captured live
        live_count = len(scores)
        for model, rate in KNOWN_VALUES.items():
            if model not in scores:
                scores[model] = rate

        if live_count == 0:
            log.info(f"  HalluHard: 0 scraped — using {len(scores)} known values")
        else:
            log.info(f"  ✅ HalluHard: {len(scores)} models ({live_count} live + {len(scores)-live_count} known)")
    except Exception as e:
        log.warning(f"  ⚠️ HalluHard: {e} — using known values")
        if not scores:
            scores = KNOWN_VALUES.copy()
    return scores


# ── 5: Vectara Hallucination ──────────────────────────────────────
def scrape_vectara_hallucination() -> dict:
    """
    huggingface.co/spaces/vectara/leaderboard
    HHEM-2.3: % hallucination in summarization across 7,700+ articles.
    INVERTED during normalization (lower rate = better score).
    130+ models. Updated continuously.
    """
    scores: dict = {}
    try:
        log.info("Scraping Vectara Hallucination (inverted)...")
        html = playwright_get_hfspace(
            "https://huggingface.co/spaces/vectara/leaderboard", wait_ms=15000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    rate = float(clean)
                    if 0 <= rate <= 100:
                        scores[name] = rate
                        break
                except ValueError:
                    pass
        log.info(f"  ✅ Vectara: {len(scores)} models (raw halluc rates)")
    except Exception as e:
        log.warning(f"  ⚠️ Vectara: {e}")
    return scores


# ── 6: HLE — Reasoning ───────────────────────────────────────────
def scrape_hle() -> dict:
    """
    Humanity's Last Exam (HLE) — lastexam.ai
    2,500 expert-level questions across 100+ subjects. Published in Nature 2026.
    Metric: Accuracy (%) — how often model answers expert questions correctly.
    Returns {model: accuracy_pct (0-100)}
    """
    scores: dict = {}
    # Last-known published values (April 2025 dataset update) as fallback
    KNOWN_VALUES = {
        "Gemini 3 Pro":      38.3,
        "GPT-5":             25.3,
        "Grok 4":            24.5,
        "Gemini 2.5 Pro":    21.6,
        "GPT-5-mini":        19.4,
        "Claude Sonnet 4.5": 13.7,
        "Gemini 2.5 Flash":  12.1,
        "DeepSeek-R1":        8.5,
        "o1":                 8.0,
        "GPT-4o":             2.7,
    }
    try:
        log.info("Scraping HLE (Humanity's Last Exam)...")
        _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")

        # Strategy 1: plain requests — table may be in static HTML
        try:
            r = requests.get("https://lastexam.ai/", headers={
                "User-Agent": _ua, "Accept": "text/html,*/*"
            }, timeout=20)
            if r.ok and len(r.text) > 1000:
                soup = BeautifulSoup(r.text, "html.parser")
                for table in soup.find_all("table"):
                    rows_html = table.find_all("tr")
                    if len(rows_html) < 3:
                        continue
                    hdrs = [th.get_text(strip=True).lower()
                            for th in rows_html[0].find_all(["th", "td"])]
                    acc_col = next((i for i, h in enumerate(hdrs)
                                    if "accuracy" in h), None)
                    if acc_col is None:
                        acc_col = 1  # default: 2nd column
                    for row in rows_html[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) <= acc_col:
                            continue
                        name = cells[0].get_text(strip=True)
                        if not name or name.lower() in ("model", "#", "rank"):
                            continue
                        try:
                            v = float(cells[acc_col].get_text(strip=True)
                                      .replace("%", "").strip())
                            if 0 <= v <= 100:
                                scores[name] = round(v, 2)
                        except ValueError:
                            pass
                if scores:
                    log.info(f"  HLE: {len(scores)} via requests+BS4")
        except Exception as e:
            log.debug(f"  HLE requests: {e}")

        # Strategy 2: Playwright — SPA may need JS render
        if not scores:
            log.info("  HLE: trying Playwright...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=_ua)
                page = ctx.new_page()
                try:
                    page.goto("https://lastexam.ai/",
                              wait_until="networkidle", timeout=60_000)
                except Exception:
                    pass
                page.wait_for_timeout(6000)
                rows_js = page.evaluate("""() => {
                    // Look for the results table: Model | Accuracy (%) | CalibError (%)
                    const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                    const results = [];
                    for (const tr of trs) {
                        const cells = tr.querySelectorAll('td');
                        if (cells.length < 2) continue;
                        const name = cells[0].textContent.trim();
                        if (!name || name.length < 2) continue;
                        // First numeric column is accuracy
                        for (let i = 1; i < cells.length; i++) {
                            const v = parseFloat(
                                cells[i].textContent.trim().replace('%',''));
                            if (!isNaN(v) && v >= 0 && v <= 100) {
                                results.push({name, acc: v});
                                break;
                            }
                        }
                    }
                    return results;
                }""")
                browser.close()
                for row in rows_js:
                    name = row.get("name", "").strip()
                    acc  = row.get("acc")
                    if name and acc is not None and 0 <= acc <= 100:
                        scores[name] = round(acc, 2)
                if scores:
                    log.info(f"  HLE: {len(scores)} via Playwright")

        # Last resort: published values
        if not scores:
            log.info("  HLE: using last-known published values (Apr 2025)")
            scores = KNOWN_VALUES.copy()

        log.info(f"  ✅ HLE: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ HLE: {e} — using known values")
        if not scores:
            scores = KNOWN_VALUES.copy()
    return scores


# ── 7: LiveBench — Reasoning ──────────────────────────────────────
def scrape_livebench() -> dict:
    """
    livebench.ai — global average scores.
    Contamination-resistant: questions refreshed periodically, verifiable answers.
    Returns {model: global_average (0-100)}
    """
    scores: dict = {}
    try:
        log.info("Scraping LiveBench (reasoning/global avg)...")

        # Try HuggingFace space first
        html = playwright_get_hfspace(
            "https://huggingface.co/spaces/livebench/leaderboard", wait_ms=15000)

        rows = parse_first_table(html)
        if rows:
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
                    continue
                name = vals[0]
                for v in vals[1:]:
                    clean = v.replace("%", "").strip()
                    try:
                        score = float(clean)
                        if 0 < score <= 100:
                            scores[name] = round(score, 2)
                            break
                    except ValueError:
                        pass

        # Fallback: livebench.ai directly
        if not scores:
            log.info("  LiveBench HF fallback → trying livebench.ai...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
                page = ctx.new_page()
                try:
                    page.goto("https://livebench.ai/",
                              wait_until="networkidle", timeout=90_000)
                except Exception:
                    pass
                try:
                    page.wait_for_selector("table tr", timeout=25_000)
                except Exception:
                    pass
                page.wait_for_timeout(5000)
                rows_js = page.evaluate("""() => {
                    const trs = Array.from(document.querySelectorAll('tr')).slice(1);
                    return trs.map(r => {
                        const cells = r.querySelectorAll('td');
                        if (cells.length < 2) return null;
                        const name = (cells[0].textContent || cells[1].textContent || '').trim();
                        for (let i = 1; i < cells.length; i++) {
                            const v = parseFloat(cells[i].textContent.trim());
                            if (!isNaN(v) && v > 0 && v <= 100) return {name, score: v};
                        }
                        return null;
                    }).filter(Boolean);
                }""")
                browser.close()
                for row in rows_js:
                    name  = row.get("name", "")
                    score = row.get("score")
                    if name and score:
                        scores[name] = round(score, 2)

        log.info(f"  ✅ LiveBench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ LiveBench: {e}")
    return scores


# ── 8: Anthropic Paired Prompts — Neutrality ──────────────────────
def scrape_anthropic_paired() -> dict:
    """
    Anthropic's political even-handedness evaluation.
    Published periodically at anthropic.com/news/political-even-handedness.
    Falls back to last-known published values.
    """
    scores: dict = {}
    KNOWN_VALUES = {
        "Claude Sonnet 4.5": 94.0,
        "Gemini 2.5 Pro":    97.0,
        "Grok 4":            96.0,
        "GPT-5":             89.0,
        "Llama 4":           66.0,
    }
    try:
        log.info("Scraping Anthropic Paired Prompts (neutrality)...")
        html = playwright_get(
            "https://www.anthropic.com/news/political-even-handedness",
            wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()
        pattern = re.compile(
            r'([\w\s\.\-]+(?:Claude|GPT|Gemini|Grok|Llama|Mistral)[\w\s\.\-]+?)'
            r'\s*[:\-]\s*(\d{2,3})%')
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            pct  = float(match.group(2))
            if 0 < pct <= 100 and 3 < len(name) < 60:
                scores[name] = pct

        if not scores:
            log.info("  Anthropic: using last-known published values")
            scores = KNOWN_VALUES.copy()

        log.info(f"  ✅ Anthropic Paired: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ Anthropic Paired: {e} — using known values")
        scores = KNOWN_VALUES.copy()
    return scores


# ── 9: TSArena — Response Quality ────────────────────────────────
def scrape_tsarena() -> dict:
    """
    TSArena — trainingrun.ai's human preference arena leaderboard.
    Arena-style voting: users compare model outputs, vote for preferred response.
    Score: Elo rating or win-rate (higher = more preferred by real users).
    Returns {model: preference_score}  (normalised to 0-100 at scoring time)
    """
    scores: dict = {}
    try:
        log.info("Scraping TSArena (response quality / human preference)...")
        _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
        _headers = {"User-Agent": _ua, "Accept": "text/html,*/*"}

        candidate_urls = [
            "https://trainingrun.ai/tsarena",
            "https://tsarena.ai",
            "https://tsarena.ai/leaderboard",
            "https://trainingrun.ai/leaderboard",
            "https://trainingrun.ai/arena",
        ]

        # Strategy 1: plain requests (fast, works if SSR)
        for url in candidate_urls:
            try:
                r = requests.get(url, headers=_headers, timeout=20)
                if r.ok and len(r.text) > 500:
                    rows = parse_first_table(r.text)
                    if rows:
                        for row in rows:
                            vals = list(row.values())
                            if len(vals) < 2:
                                continue
                            name = str(vals[0]).strip()
                            if not name or name.lower() in ("#", "model", "rank"):
                                name = str(vals[1]).strip() if len(vals) > 1 else ""
                            if not name:
                                continue
                            for v in vals[1:]:
                                try:
                                    fv = float(str(v).replace(",", "")
                                               .replace("%", "").strip())
                                    if fv > 0:
                                        scores[name] = round(fv, 2)
                                        break
                                except (ValueError, TypeError):
                                    pass
                        if scores:
                            log.info(f"  TSArena: {len(scores)} via requests({url})")
                            break
            except Exception as e:
                log.debug(f"  TSArena requests {url}: {e}")

        # Strategy 2: Playwright SPA fallback
        if not scores:
            for url in candidate_urls:
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        ctx = browser.new_context(user_agent=_ua)
                        page = ctx.new_page()
                        try:
                            page.goto(url, wait_until="networkidle", timeout=60_000)
                        except Exception:
                            pass
                        page.wait_for_timeout(7000)
                        rows_js = page.evaluate("""() => {
                            const trs = Array.from(
                                document.querySelectorAll('tr')).slice(1);
                            return trs.map(r => {
                                const cells = r.querySelectorAll('td');
                                if (cells.length < 2) return null;
                                // TSArena: cells[0]=medal emoji, cells[1]=model+lab
                                // Use .model-name span for clean model name
                                const nameEl = cells[1].querySelector('.model-name')
                                             || cells[1].querySelector('span')
                                             || cells[1];
                                const name = nameEl.textContent.trim().split('\\n')[0].trim();
                                // Score is in cells[2]
                                for (let i = 2; i < cells.length; i++) {
                                    const v = parseFloat(
                                        cells[i].textContent.trim().replace(',',''));
                                    if (!isNaN(v) && v > 0) return {name, score: v};
                                }
                                return null;
                            }).filter(Boolean);
                        }""")
                        browser.close()
                        for row in rows_js:
                            name  = row.get("name", "").strip()
                            score = row.get("score")
                            if name and score is not None and score > 0:
                                scores[name] = round(score, 2)
                        if scores:
                            log.info(f"  TSArena: {len(scores)} via Playwright({url})")
                            break
                except Exception as e:
                    log.debug(f"  TSArena Playwright {url}: {e}")

        if not scores:
            log.info("  ℹ️  TSArena: 0 scraped — URL not yet live or structure unknown. "
                     "quality_tsarena excluded from scoring (proportional renorm applies).")

        log.info(f"  ✅ TSArena: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ TSArena: {e}")
    return scores


# ════════════════════════════════════════════════════════════════════
#  SCORING ENGINE
# ════════════════════════════════════════════════════════════════════

def normalize_across_models(
        raw_values: dict,
        is_inverted: bool = False) -> dict:
    """Top performer = 100. Others proportional. Inverted for hallucination rates."""
    vals = {k: v for k, v in raw_values.items() if v is not None and v > 0}
    if not vals:
        return {}
    if is_inverted:
        min_val = min(vals.values())
        if min_val == 0:
            min_val = 0.001
        return {k: round((min_val / v) * 100.0, 4) for k, v in vals.items()}
    else:
        max_val = max(vals.values())
        if max_val == 0:
            return {}
        return {k: round((v / max_val) * 100.0, 4) for k, v in vals.items()}


def calculate_composite(
        model_name: str,
        normalized: dict) -> tuple:
    """Option A: null sources excluded, available weights renormalized."""
    available = {
        k: WEIGHTS[k]
        for k in WEIGHTS
        if normalized.get(k, {}).get(model_name) is not None
        and normalized[k].get(model_name, 0.0) > 0
    }
    if not available:
        return 0.0, 0
    w_sum = sum(available.values())
    total = sum(
        normalized[k].get(model_name, 0.0) * (w / w_sum)
        for k, w in available.items()
    )
    return round(total, 2), len(available)


def calculate_pillar_scores(
        model_name: str,
        normalized: dict) -> dict:
    """
    Compute per-pillar composite score (0-100) for display on leaderboard.
    Each pillar uses proportional renormalization across its available sources.
    Returns {pillar_name: score_or_None}
    """
    result = {}
    for pillar, sources in PILLAR_SOURCES.items():
        available = {
            s: WEIGHTS[s]
            for s in sources
            if normalized.get(s, {}).get(model_name) is not None
            and normalized[s].get(model_name, 0.0) > 0
        }
        if not available:
            result[pillar] = None
        else:
            w_sum = sum(available.values())
            score = sum(
                normalized[s].get(model_name, 0.0) * (w / w_sum)
                for s, w in available.items()
            )
            result[pillar] = round(score, 1)
    return result


def generate_checksum(data: dict) -> str:
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(
        f"{s:.1f}" if s is not None else "null"
        for m in data["models"]
        for s in m["scores"]
    )
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def _infer_company(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["gpt", "o1-", "o3-", "o4-", "chatgpt"]): return "OpenAI"
    if any(x in n for x in ["claude", "opus", "sonnet", "haiku"]):    return "Anthropic"
    if any(x in n for x in ["gemini", "gemma", "bard"]):              return "Google"
    if any(x in n for x in ["grok"]):                                  return "xAI"
    if any(x in n for x in ["llama", "meta-"]):                        return "Meta"
    if any(x in n for x in ["mistral", "mixtral", "pixtral"]):        return "Mistral"
    if any(x in n for x in ["deepseek"]):                              return "DeepSeek"
    if any(x in n for x in ["qwen", "qwq"]):                          return "Alibaba"
    if any(x in n for x in ["glm", "chatglm", "zhipu"]):             return "Zhipu AI"
    if any(x in n for x in ["minimax"]):                               return "MiniMax"
    if any(x in n for x in ["command", "cohere", "aya"]):             return "Cohere"
    if any(x in n for x in ["moonshot", "kimi"]):                     return "Moonshot AI"
    if any(x in n for x in ["nova", "titan", "amazon"]):              return "Amazon"
    if any(x in n for x in ["phi-", "copilot"]):                      return "Microsoft"
    if any(x in n for x in ["nemotron", "nvidia"]):                   return "NVIDIA"
    if any(x in n for x in ["intellect"]):                            return "PrimeIntellect"
    if any(x in n for x in ["mercury", "inception"]):                 return "Inception"
    return "Unknown"


def auto_discover_models(data: dict, all_results: dict) -> list:
    existing = [m["name"] for m in data["models"]]
    newly_added = []
    all_scraped: set = set()
    for source_results in all_results.values():
        all_scraped.update(source_results.keys())
    for name in sorted(all_scraped):
        if not name or len(name) < 3:
            continue
        if match_name(name, existing) is not None:
            continue
        new_entry = {
            "name":          name,
            "company":       _infer_company(name),
            "rank":          999,
            "scores":        [None] * len(data["dates"]),
            "source_count":  0,
            "pillar_scores": {},
        }
        data["models"].append(new_entry)
        existing.append(name)
        newly_added.append(name)
        log.info(f"  ★ Auto-discovered: {name} ({new_entry['company']})")
    return newly_added


# ── Git push ───────────────────────────────────────────────────────
def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(
            ["git", "add", "data/truscore-data.json", "status.json"],
            cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit — data unchanged.")
                return True
            log.error(f"Commit failed:\n{r.stderr}")
            return False
        subprocess.run(["git", "stash", "--include-untracked"],
                       cwd=REPO_PATH, capture_output=True)
        pull = subprocess.run(
            ["git", "pull", "--rebase", "-X", "theirs", "origin", "main"],
            cwd=REPO_PATH, capture_output=True, text=True)
        if pull.returncode != 0:
            subprocess.run(["git", "rebase", "--abort"],
                           cwd=REPO_PATH, capture_output=True)
            subprocess.run(["git", "pull", "origin", "main"],
                           cwd=REPO_PATH, capture_output=True)
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        subprocess.run(["git", "stash", "pop"],
                       cwd=REPO_PATH, capture_output=True)
        log.info("✅ Pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}")
        return False


def write_status(status, ranked, source_summary, duration, error=None):
    """Write status.json."""
    status_file = REPO_PATH / "status.json"
    try:
        sdata = json.loads(status_file.read_text()) if status_file.exists() else {}
        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        top5 = []
        for m in ranked[:5]:
            sc = m["scores"][-1] if m["scores"] else None
            if sc is not None:
                top5.append({"rank": m["rank"], "name": m["name"], "score": sc})
        sources_hit = sum(1 for s in source_summary
                          if "0 scraped" not in s and "0 matched" not in s)
        sdata.setdefault("agents", {})["truscore"] = {
            "name": "TRUscore DDP", "label": "Truth & Reliability",
            "emoji": "🎯", "enabled": True,
            "last_run": now_iso, "last_run_date": TODAY,
            "status": status, "duration_seconds": duration,
            "sources_total": len(WEIGHTS),
            "sources_hit": sources_hit,
            "models_qualified": len(ranked),
            "top_model": ranked[0]["name"] if ranked else None,
            "top_score": (ranked[0]["scores"][-1]
                          if ranked and ranked[0]["scores"] else None),
            "top5": top5,
            "leaderboard_url": "/truscore-scores.html",
            "error": error,
            "formula_version": "V1.4",
        }
        status_file.write_text(json.dumps(sdata, indent=2))
        log.info("✅ status.json updated")
    except Exception as e:
        log.warning(f"Could not write status.json: {e}")


# ════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════
def main():
    t_start = time.time()

    if TEST_TELEGRAM:
        notify("✅ <b>TRUscore V1.4 online</b>\nTelegram works!")
        print("Telegram test sent.")
        return

    mode = "DRY RUN 🧪" if DRY_RUN else "LIVE 🚀"
    log.info(f"TRUscore V1.4 | {TODAY} | {mode}")
    notify(f"🤖 <b>TRUscore V1.4 starting</b>\n📅 {TODAY}\n⚙️ {mode}\n9 sub-metrics, 5 pillars")

    # ── Load data ──
    if not DATA_FILE.exists():
        msg = f"truscore-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"❌ {msg}"); return
    with open(DATA_FILE) as f:
        data = json.load(f)

    data["formula_version"] = "V1.4"
    data["weights"] = WEIGHTS

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"📂 Loaded: {len(models)} models | dates {dates[0]} → {dates[-1]}")

    # ── Date slot ──
    if TODAY in dates:
        date_is_new = False
        today_idx = dates.index(TODAY)
        notify(f"ℹ️ {TODAY} exists at index {today_idx}. Refreshing.")
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1
        notify(f"➕ New date: {TODAY} (slot {today_idx})")

    # ── Scrape all sources ──
    simpleqa_scores  = scrape_simpleqa()
    facts_scores     = scrape_facts()
    truthfulqa_scores = scrape_truthfulqa()
    halluhard_scores  = scrape_halluhard()
    vectara_scores    = scrape_vectara_hallucination()
    hle_scores        = scrape_hle()
    livebench_scores  = scrape_livebench()
    anthropic_scores  = scrape_anthropic_paired()
    tsarena_scores    = scrape_tsarena()

    all_results = {
        "truthfulness_simpleqa":   simpleqa_scores,
        "truthfulness_facts":      facts_scores,
        "truthfulness_truthfulqa": truthfulqa_scores,
        "hallucination_halluhard": halluhard_scores,
        "hallucination_vectara":   vectara_scores,
        "reasoning_hle":           hle_scores,
        "reasoning_livebench":     livebench_scores,
        "neutrality_anthropic":    anthropic_scores,
        "quality_tsarena":         tsarena_scores,
    }

    # ── Remap scraped names → canonical roster names ──────────────
    all_results = {
        key: remap_to_roster_names(raw, names)
        for key, raw in all_results.items()
    }

    # ── Match scraped names to roster ──
    source_summary = []
    for source_key, raw_values in all_results.items():
        matched = sum(1 for sn in raw_values if match_name(sn, names) is not None)
        source_summary.append(
            f"{source_key}: {len(raw_values)} scraped, {matched} matched")
        log.info(f"  {source_key}: {matched}/{len(raw_values)} matched")

    notify("📊 <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # ── Auto-discover new models ──
    new_models = auto_discover_models(data, all_results)
    if new_models:
        notify(f"★ <b>Auto-discovered {len(new_models)} new models</b>\n"
               + "\n".join(f"  • {n}" for n in new_models))
    models = data["models"]
    names  = [m["name"] for m in models]

    # ── Normalize (invert hallucination sources) ──
    INVERTED_SOURCES = {"hallucination_halluhard", "hallucination_vectara"}
    normalized = {}
    for source_key, raw_values in all_results.items():
        normalized[source_key] = normalize_across_models(
            raw_values, is_inverted=(source_key in INVERTED_SOURCES))

    # ── Score each model ──
    for model in models:
        n = model["name"]
        composite, source_count = calculate_composite(n, normalized)
        pillar_scores = calculate_pillar_scores(n, normalized)

        model["source_count"] = source_count
        model["pillar_scores"] = pillar_scores

        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(composite)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = composite
            else:
                model["scores"].append(composite)

    # ── Qualification filter ──
    def today_score(m):
        s = (m["scores"][today_idx]
             if today_idx < len(m["scores"]) else None)
        return s if s is not None else -1.0

    qualified    = [m for m in models if m["source_count"] >= QUALIFICATION_MIN_SOURCES]
    disqualified = [m for m in models if m["source_count"] < QUALIFICATION_MIN_SOURCES]

    if disqualified:
        log.info(f"Disqualified (<{QUALIFICATION_MIN_SOURCES} sources): "
                 f"{[m['name'] for m in disqualified[:10]]}"
                 f"{'...' if len(disqualified) > 10 else ''}")

    # ── Update ranks ──
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    # ── Print dry-run report ──
    if DRY_RUN:
        print("\n" + "═"*72)
        print(f"  TRUSCORE V1.4 — DRY RUN RESULTS  {TODAY}")
        print("═"*72)
        print(f"\n  PILLAR STRUCTURE (9 sub-metrics, 5 pillars):")
        print(f"    Truthfulness (35%):   SimpleQA, FACTS, TruthfulQA")
        print(f"    Hallucination (20%):  HalluHard, Vectara")
        print(f"    Reasoning (20%):      HLE, LiveBench")
        print(f"    Neutrality (15%):     Anthropic Paired")
        print(f"    Response Quality(10%):TSArena")
        print(f"\n  SOURCE COVERAGE:")
        for line in source_summary:
            print(f"    {line}")
        print(f"\n  QUALIFICATION: {len(qualified)} qualified "
              f"(≥{QUALIFICATION_MIN_SOURCES} sources) | "
              f"{len(disqualified)} disqualified")
        print(f"\n  TOP 20 QUALIFIED MODELS:")
        print(f"  {'#':<4} {'Model':<35} {'Score':>7} {'SC':>4} "
              f"{'Truth':>6} {'Hall':>6} {'Reas':>6} {'Neut':>6} {'Qual':>6}")
        print(f"  {'-'*77}")
        for m in ranked[:20]:
            sc   = today_score(m)
            ps   = m.get("pillar_scores", {})
            tru  = ps.get("truthfulness")
            hal  = ps.get("hallucination")
            rea  = ps.get("reasoning")
            neu  = ps.get("neutrality")
            qua  = ps.get("response_quality")
            def fmt(v): return f"{v:6.1f}" if v is not None else "     —"
            print(f"  {m['rank']:<4} {m['name']:<35} {sc:>7.2f} "
                  f"{m['source_count']:>4} "
                  f"{fmt(tru)} {fmt(hal)} {fmt(rea)} {fmt(neu)} {fmt(qua)}")
        if ranked:
            print(f"\n  🏆 #1: {ranked[0]['name']} — {today_score(ranked[0]):.2f}")
        print(f"\n  NEW models auto-discovered: {new_models or 'none'}")

        # ── NAME MATCH DIAGNOSTIC ─────────────────────────────────
        print("\n" + "─"*72)
        print("  NAME MATCH DIAGNOSTIC")
        print("─"*72)
        print(f"\n  ROSTER ({len(names)} models, first 15):")
        for n in names[:15]:
            print(f"    · {n}")
        print(f"\n  POST-REMAP KEYS (first 5 per source):")
        for sk, nd in normalized.items():
            sample = list(nd.keys())[:5]
            print(f"    {sk}: {sample}")
        model_src = sorted(
            [(m["name"], m.get("source_count", 0)) for m in models],
            key=lambda x: -x[1])
        with_sources = [(n, sc) for n, sc in model_src if sc > 0]
        print(f"\n  MODELS WITH ANY SOURCES (top 15):")
        if with_sources:
            for n, sc in with_sources[:15]:
                src_keys = [k for k in WEIGHTS
                            if normalized.get(k, {}).get(n, 0) > 0]
                print(f"    {n}: {sc} → {src_keys}")
        else:
            print("  ⚠️  ZERO roster models found in any normalized dict!")
        print("─"*72)

        print(f"\n  ✅ DRY RUN COMPLETE. Nothing written, nothing pushed.")
        print("═"*72 + "\n")
        notify(f"🧪 <b>TRUscore V1.4 DRY RUN complete</b>\n"
               f"📅 {TODAY}\n"
               f"✅ {len(qualified)} qualified models\n"
               f"🏆 #1: {ranked[0]['name'] if ranked else 'n/a'}")
        return

    # ── Write + push (live run only) ──
    duration = int(time.time() - t_start)
    from datetime import datetime as _dt
    data["run_at"]   = _dt.now().strftime("%-I:%M %p") + " CST"
    data["checksum"] = generate_checksum(data)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    write_status("success", ranked, source_summary, duration)

    ok = git_push(f"TRUscore V1.4 daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRUscore V1.4 done!</b>\n"
               f"📅 {TODAY}\n🏆 {len(qualified)} models\n"
               f"→ trainingrun.ai/truscore-scores")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
