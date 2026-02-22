#!/usr/bin/env python3
"""
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  AGENT TRUSCORE â TRUscore Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRUscore V1.0 (Feb 21, 2026)
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  7 sources scraped:
    1. SimpleQA Factuality           kaggle/huggingface            0.20
    2. NewsGuard AI Misinformation   newsguardtech.com             0.20
    3. TrackingAI Neutrality         trackingai.org                0.25
    4. Anthropic Paired Eval         anthropic.com/research        0.05
    5. Vectara Hallucination         huggingface.co/vectara        0.15
    6. Artificial Analysis (Fact)    artificialanalysis.ai         0.05
    7. SimpleQA Calibration          kaggle/huggingface            0.10

  Qualification: 5+ sources with non-null scores.
  Scoring: Option A â null sources excluded, available weights renormalized to 1.0.
  Special: Hallucination rates are INVERTED (lower = better).

  Usage:
    python3 agent_truscore.py                  # live run
    python3 agent_truscore.py --dry-run        # scrape + calculate, no push
    python3 agent_truscore.py --test-telegram  # test Telegram connection only

  Env vars:
    TELEGRAM_TOKEN     BotFather token
    TELEGRAM_CHAT_ID   Your numeric chat ID
    REPO_PATH          Path to local trainingrun-site clone
                       Default: ~/trainingrun-site

  Dependencies:
    pip3 install playwright python-telegram-bot beautifulsoup4 requests
    python3 -m playwright install chromium
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re
from datetime import date
from pathlib import Path

# ââ dependency guard ââââââââââââââââââââââââââââââââââââââââââââââ
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

# ââ logging âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("truscore")

# ââ CONFIG ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "truscore-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ââ TRUscore Bible V1.0 weights âââââââââââââââââââââââââââââââââââ
WEIGHTS = {
    "factuality_simpleqa":            0.20,
    "factuality_newsguard":           0.20,
    "neutrality_trackingai":          0.25,
    "neutrality_anthropic":           0.05,
    "hallucination_vectara":          0.15,
    "hallucination_artificialanalysis": 0.05,
    "calibration_simpleqa":           0.10,
}

QUALIFICATION_MIN_SOURCES = 2   # Bible: 5-source minimum

# ââ TELEGRAM ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text}")
        return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try:
        asyncio.run(_send())
    except Exception as e:
        log.warning(f"Telegram non-fatal: {e}")


# ââ PLAYWRIGHT HELPER âââââââââââââââââââââââââââââââââââââââââââââ
def playwright_get(url: str, wait_ms: int = 5000) -> str:
    """Launch headless Chromium, load url, return page HTML."""
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
    """Load HuggingFace Space URL; returns inner .hf.space iframe HTML if present."""
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


def playwright_get_innertext(url: str, wait_ms: int = 8000) -> str:
    """Load url with Playwright, return body.innerText (for non-table JS pages)."""
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
        text = page.evaluate("document.body.innerText") or ""
        browser.close()
    return text


def parse_first_table(html: str) -> list[dict]:
    """Return rows as list of {col0, col1, col2...} dicts from the largest table."""
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


# ââ SCRAPERS ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def scrape_simpleqa() -> tuple[dict[str, float], dict[str, float]]:
    """
    llm-stats.com SimpleQA leaderboard (43 models).
    Scores are 0.0-1.0 decimals, multiplied by 100 to get %.
    Returns two dicts (same source):
      1. factuality_simpleqa: {model: correct_pct}
      2. calibration_simpleqa: {model: correct_pct}
    """
    factuality: dict[str, float] = {}
    calibration: dict[str, float] = {}
    try:
        log.info("Scraping SimpleQA (factuality + calibration)...")
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
                    if (cells.length < 3) return null;
                    const nameEl = cells[1].querySelector('a') || cells[1];
                    const name = nameEl.textContent.trim().split('\\n')[0].trim();
                    const score = parseFloat(cells[2].textContent.trim());
                    if (!name || isNaN(score)) return null;
                    return {name, score};
                }).filter(Boolean);
            }""")
            browser.close()
        for row in rows:
            name = row.get("name", "")
            score = row.get("score")
            if name and score is not None:
                pct = round(score * 100, 2)
                if 0 < pct <= 100:
                    factuality[name] = pct
                    calibration[name] = pct
        log.info(f"  \u2705 SimpleQA: {len(factuality)} factuality, {len(calibration)} calibration")
    except Exception as e:
        log.warning(f"  \u26a0\ufe0f SimpleQA: {e}")
    return factuality, calibration
def scrape_newsguard() -> dict[str, float]:
    """Scale SEAL PropensityBench -- latent safety risk (lower propensity = safer).
    Scores are INVERTED: returned as (100 - propensity) so higher = safer.
    source: scale.com/leaderboard/propensitybench"""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping NewsGuard (safety propensity)...")
        url = "https://scale.com/leaderboard/propensitybench"
        text = playwright_get_innertext(url, wait_ms=10000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        i = 0
        while i < len(lines) - 2:
            if re.match(r'^\d+$', lines[i]):
                name = lines[i + 1]
                score_raw = lines[i + 2]
                m = re.match(r'^(\d+(?:\.\d+)?)', score_raw)
                if (m and 3 <= len(name) <= 80
                        and not re.match(r'^[\d\u00b1\.\+\-\s]+$', name)):
                    try:
                        propensity = float(m.group(1))
                        if 0 <= propensity <= 100:
                            safety = round(100.0 - propensity, 2)
                            if name not in scores or safety > scores[name]:
                                scores[name] = safety
                            i += 3
                            continue
                    except ValueError:
                        pass
            i += 1
        log.info(f"  \u2705 PropensityBench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  \u26a0\ufe0f PropensityBench: {e}")
    return scores
def scrape_trackingai() -> dict[str, float]:
    """trackingai.org â political neutrality scores."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping TrackingAI (neutrality)...")
        url = "https://trackingai.org/"
        html = playwright_get(url, wait_ms=8000)
        rows = parse_first_table(html)
        
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    score = float(clean)
                    if 0 <= score <= 100:
                        scores[name] = score
                        break
                except ValueError:
                    pass
        
        log.info(f"  â TrackingAI: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ TrackingAI: {e}")
    return scores


def scrape_anthropic_paired() -> dict[str, float]:
    """Anthropic paired evaluation â neutrality/evenhandedness scores (if publicly available)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Anthropic Paired Eval (neutrality)...")
        # This data may not be directly scrapable â return empty
        # Placeholder for future integration if Anthropic publishes benchmark
        log.info(f"  â ï¸ Anthropic data not publicly available yet")
    except Exception as e:
        log.warning(f"  â ï¸ Anthropic Paired: {e}")
    return scores


def scrape_vectara_hallucination() -> dict[str, float]:
    """
    huggingface.co/spaces/vectara/leaderboard â hallucination rates.
    IMPORTANT: Lower hallucination rate = better. Will be inverted during normalization.
    Returns {model: hallucination_rate}
    """
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Vectara Hallucination (inverted)...")
        url = "https://huggingface.co/spaces/vectara/leaderboard"
        html = playwright_get_hfspace(url, wait_ms=15000)
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
        
        log.info(f"  â Vectara: {len(scores)} models (raw rates)")
    except Exception as e:
        log.warning(f"  â ï¸ Vectara: {e}")
    return scores


def scrape_artificialanalysis_omniscience() -> dict[str, float]:
    """artificialanalysis.ai/leaderboards/models -- Intelligence Index (0-100)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Artificial Analysis (factuality)...")
        # NOTE: /models has no scores; use /leaderboards/models
        # Table is JS-rendered (row0=group headers, row1=col headers, row2+=data)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://artificialanalysis.ai/leaderboards/models",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table tr:nth-child(3)", timeout=30_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const table = document.querySelector('table');
                if (!table) return [];
                const allRows = Array.from(table.querySelectorAll('tr'));
                // row0=group headers, row1=col headers, row2+=data
                // col indices: 0=Model, 3=Intelligence Index
                return allRows.slice(2).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {model: cells[0] || '', intelligence: cells[3] || ''};
                }).filter(r => r.model && r.intelligence);
            }""")
            browser.close()

        for row in rows:
            name = row.get("model", "")
            # Strip quality suffix: "Claude Opus 4.6 (max)" -> "Claude Opus 4.6"
            name = re.sub(r'\s*\([^)]+\)\s*$', '', name).strip()
            if not name:
                continue
            intel_raw = row.get("intelligence", "")
            try:
                val = float(intel_raw.strip())
                if 0 <= val <= 100:
                    scores[name] = val
            except ValueError:
                pass
        log.info(f"  ✅ Artificial Analysis: {len(scores)} models")
    except Exception as e:
        log.warning(f"  ⚠️ Artificial Analysis: {e}")
    return scores

# ══ SCORING ENGINE ════════════════════════════════════════════════

def normalize_across_models(raw_values: dict[str, float], is_inverted: bool = False) -> dict[str, float]:
    """
    Top performer = 100. Others proportional.
    If is_inverted=True: lower raw value = better (hallucination rates).
    Top performer = min(values), and score = (min / value) * 100.
    """
    vals = {k: v for k, v in raw_values.items() if v is not None and v > 0}
    if not vals:
        return {}
    
    if is_inverted:
        min_val = min(vals.values())
        return {k: round((min_val / v) * 100.0, 4) for k, v in vals.items()}
    else:
        max_val = max(vals.values())
        return {k: round((v / max_val) * 100.0, 4) for k, v in vals.items()}


def calculate_composite(model_name: str, normalized: dict) -> tuple[float, int]:
    """Option A: null sources excluded, available weights renormalized to sum 1.0."""
    available_weights = {k: WEIGHTS[k] for k in WEIGHTS 
                         if normalized.get(k, {}).get(model_name, None) is not None
                         and normalized[k].get(model_name, 0.0) > 0}
    if not available_weights:
        return 0.0, 0
    weight_sum = sum(available_weights.values())
    total = sum(normalized[k].get(model_name, 0.0) * (w / weight_sum) 
                for k, w in available_weights.items())
    return round(total, 2), len(available_weights)


def generate_checksum(data: dict) -> str:
    """Bible V1.0 canonical: names|...|:scores,...  with .1f formatting."""
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(
        f"{s:.1f}" if s is not None else "null"
        for m in data["models"] for s in m["scores"]
    )
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def _infer_company(name: str) -> str:
    """Best-effort company inference from model name keywords."""
    n = name.lower()
    if any(x in n for x in ["gpt", "o1-", "o3-", "o4-", "chatgpt", "davinci"]):
        return "OpenAI"
    if any(x in n for x in ["claude", "opus", "sonnet", "haiku"]):
        return "Anthropic"
    if any(x in n for x in ["gemini", "gemma", "bard"]):
        return "Google"
    if any(x in n for x in ["grok"]):
        return "xAI"
    if any(x in n for x in ["llama", "meta-", "turbo"]):
        return "Meta"
    if any(x in n for x in ["mistral", "mixtral", "pixtral", "codestral", "voxtral", "devstral"]):
        return "Mistral"
    if any(x in n for x in ["deepseek"]):
        return "DeepSeek"
    if any(x in n for x in ["qwen", "qwq"]):
        return "Alibaba"
    if any(x in n for x in ["glm", "chatglm", "zhipu"]):
        return "Zhipu AI"
    if any(x in n for x in ["minimax"]):
        return "MiniMax"
    if any(x in n for x in ["command", "cohere", "aya"]):
        return "Cohere"
    if any(x in n for x in ["moonshot", "kimi"]):
        return "Moonshot AI"
    if any(x in n for x in ["nova", "titan", "amazon"]):
        return "Amazon"
    if any(x in n for x in ["phi-", "copilot", "wizardlm"]):
        return "Microsoft"
    if any(x in n for x in ["nemotron", "nvidia"]):
        return "NVIDIA"
    if any(x in n for x in ["falcon"]):
        return "TII"
    if any(x in n for x in ["yi-", "01.ai"]):
        return "01.AI"
    if any(x in n for x in ["granite", "ibm"]):
        return "IBM"
    if any(x in n for x in ["olmo", "olmoe", "molmo", "tulu"]):
        return "AI2"
    if any(x in n for x in ["palmyra", "palm", "writer"]):
        return "Writer"
    if any(x in n for x in ["dbrx", "databricks"]):
        return "Databricks"
    if any(x in n for x in ["mercury", "inception"]):
        return "Inception"
    if any(x in n for x in ["intellect"]):
        return "PrimeIntellect"
    return "Unknown"


def auto_discover_models(data: dict, all_results: dict) -> list[str]:
    """
    Scan all scraped source results. Any model name that appears in the data
    but isn't already in the roster gets auto-added with null score history.
    Uses match_name() to avoid duplicates from name variations.
    Returns list of newly added model names.
    """
    existing_names = [m["name"] for m in data["models"]]
    newly_added = []

    all_scraped: set[str] = set()
    for source_results in all_results.values():
        all_scraped.update(source_results.keys())

    for name in sorted(all_scraped):
        if not name or len(name) < 3 or name.replace("-", "").replace("_", "").isdigit():
            continue
        if match_name(name, existing_names) is not None:
            continue
        new_entry = {
            "name":         name,
            "company":      _infer_company(name),
            "rank":         999,
            "scores":       [None] * len(data["dates"]),
            "source_count": 0,
        }
        data["models"].append(new_entry)
        existing_names.append(name)
        newly_added.append(name)
        log.info(f"  ★ Auto-discovered: {name} ({new_entry['company']})")

    return newly_added


def match_name(scraped: str, existing: list[str]) -> str | None:
    s = scraped.lower().strip()
    # Strip org prefix (e.g. "anthropic/claude-opus-4-6" -> "claude-opus-4-6")
    s_stripped = s.split("/")[-1] if "/" in s else s
    for name in existing:
        if name.lower() == s or name.lower() == s_stripped:
            return name
    for name in existing:
        n = name.lower()
        if s_stripped in n or n in s_stripped:
            return name
    s_tok = set(s_stripped.replace("-", " ").replace("_", " ").split())
    for name in existing:
        n_tok = set(name.lower().replace("-", " ").replace("_", " ").split())
        if len(s_tok & n_tok) >= 2:
            return name
    return None
def write_status(status: str, ranked: list, source_summary: list,
                 duration_sec: int, error: str | None = None) -> None:
    """Update status.json with this agent's latest run info."""
    status_file = REPO_PATH / "status.json"
    try:
        if status_file.exists():
            with open(status_file) as f:
                sdata = json.load(f)
        else:
            sdata = {"last_updated": TODAY, "agents": {}}

        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        top5 = []
        for m in ranked[:5]:
            sc = m["scores"][-1] if m["scores"] else None
            if sc is not None:
                top5.append({"rank": m["rank"], "name": m["name"], "score": sc})

        sources_hit = sum(1 for s in source_summary if "0 scraped" not in s and "0 matched" not in s)

        sdata["last_updated"] = now_iso
        sdata["agents"]["truscore"] = {
            "name":             "TRUscore DDP",
            "label":            "Truth & Neutrality",
            "emoji":            "ð¯",
            "enabled":          True,
            "last_run":         now_iso,
            "last_run_date":    TODAY,
            "status":           status,
            "duration_seconds": duration_sec,
            "sources_total":    7,
            "sources_hit":      sources_hit,
            "models_qualified": len(ranked),
            "top_model":        ranked[0]["name"] if ranked else None,
            "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5":             top5,
            "leaderboard_url":  "/truscore-scores.html",
            "next_run":         (TODAY + "T05:00:00").replace(TODAY, _next_day()),
            "error":            error,
        }

        with open(status_file, "w") as f:
            json.dump(sdata, f, indent=2)
        log.info("â status.json updated")
    except Exception as e:
        log.warning(f"Could not write status.json: {e}")


def _next_day() -> str:
    from datetime import datetime, timedelta
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def update_index_timestamp() -> None:
    """Rewrite var LAST_PUSH_TIME in index.html with the current local time."""
    index_file = REPO_PATH / "index.html"
    if not index_file.exists():
        log.warning("index.html not found â skipping timestamp update")
        return
    try:
        from datetime import datetime
        now = datetime.now()
        hour   = now.strftime("%I").lstrip("0") or "12"
        minute = now.strftime("%M")
        ampm   = now.strftime("%p")
        push_time = f"{hour}:{minute} {ampm} CST"

        content = index_file.read_text()
        new_content = re.sub(
            r"var LAST_PUSH_TIME\s*=\s*'[^']*';",
            f"var LAST_PUSH_TIME = '{push_time}';",
            content,
        )
        if new_content != content:
            index_file.write_text(new_content)
            log.info(f"â index.html timestamp updated â {push_time}")
        else:
            log.warning("index.html: LAST_PUSH_TIME pattern not found â timestamp not updated")
    except Exception as e:
        log.warning(f"Could not update index.html timestamp: {e}")


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "truscore-data.json", "status.json", "index.html"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit â data unchanged.")
                return True
            log.error(f"Commit failed:\n{r.stderr}")
            return False
        subprocess.run(["git", "push"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        log.info("â Pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e.stderr}")
        return False


# ââ MAIN ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def main():
    import time as _time
    main._start_time = _time.time()

    if TEST_TELEGRAM:
        notify("â <b>TRUscore DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN ð" if DRY_RUN else "LIVE ð"
    log.info(f"TRUscore DDP | {TODAY} | {mode}")
    notify(f"ð¤ <b>TRUscore DDP starting</b>\nð {TODAY}\nâï¸ {mode}\n7 sources â truscore-data.json")

    # ââ Load data ââ
    if not DATA_FILE.exists():
        msg = f"truscore-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"â {msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"ð Loaded. Models: {len(models)} | Dates: {dates[0]} â {dates[-1]}")

    # ââ Date slot ââ
    if TODAY in dates:
        date_is_new = False
        today_idx   = dates.index(TODAY)
        notify(f"â¹ï¸ {TODAY} exists at index {today_idx}. Refreshing.")
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1
        notify(f"â New date: {TODAY} (slot {today_idx})")

    # ââ Scrape all 7 sources ââ
    # SimpleQA returns 2 dicts; others return 1 dict each
    simpleqa_fact, simpleqa_calib = scrape_simpleqa()
    newsguard_scores = scrape_newsguard()
    trackingai_scores = scrape_trackingai()
    anthropic_scores = scrape_anthropic_paired()
    vectara_scores = scrape_vectara_hallucination()
    artanalysis_scores = scrape_artificialanalysis_omniscience()

    all_results = {
        "factuality_simpleqa":            simpleqa_fact,
        "factuality_newsguard":           newsguard_scores,
        "neutrality_trackingai":          trackingai_scores,
        "neutrality_anthropic":           anthropic_scores,
        "hallucination_vectara":          vectara_scores,
        "hallucination_artificialanalysis": artanalysis_scores,
        "calibration_simpleqa":           simpleqa_calib,
    }

    total_matched = 0
    source_summary = []

    for source_key, raw_values in all_results.items():
        matched = 0
        for scraped_name in raw_values.keys():
            canonical = match_name(scraped_name, names)
            if canonical:
                matched += 1
        total_matched += matched
        source_summary.append(f"{source_key}: {len(raw_values)} scraped, {matched} matched")
        log.info(f"  {source_key}: {matched}/{len(raw_values)} matched")

    notify("ð <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # -- Auto-discover new models --
    new_models = auto_discover_models(data, all_results)
    if new_models:
        log.info(f"★ Auto-discovered {len(new_models)} new models: {new_models}")
        notify(f"★ <b>Auto-discovered {len(new_models)} new models</b>\n" +
               "\n".join(f"  • {n}" for n in new_models))
        models = data["models"]
        names  = [m["name"] for m in models]

    # ââ Normalize + score ââ
    # Vectara uses inverted normalization (lower = better)
    normalized = {}
    for source_key, raw_values in all_results.items():
        is_inverted = "vectara" in source_key
        normalized[source_key] = normalize_across_models(raw_values, is_inverted=is_inverted)

    for model in models:
        n  = model["name"]
        sc, source_count = calculate_composite(n, normalized)
        model["source_count"] = source_count
        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(sc)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = sc
            else:
                model["scores"].append(sc)

    # ââ Qualification filter (5+ sources) ââ
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified = [m for m in models if m["source_count"] >= QUALIFICATION_MIN_SOURCES]
    disqualified = [m for m in models if m["source_count"] < QUALIFICATION_MIN_SOURCES]
    if disqualified:
        log.info(f"Disqualified (< {QUALIFICATION_MIN_SOURCES} sources): "
                 f"{[m['name'] for m in disqualified]}")

    # ââ Update ranks ââ
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"ð¯ <b>TRUscore Top 5 â {TODAY}</b>\n{top5_lines}")

    # ââ Checksum ââ
    data["checksum"] = generate_checksum(data)
    log.info(f"Checksum: {data['checksum'][:20]}...")

    if DRY_RUN:
        notify(f"ð <b>DRY RUN complete</b>\nWould score {len(qualified)} models.\nNothing written.")
        log.info("Dry run complete. Nothing written.")
        return

    # ââ Write + push ââ
    import time as _time
    _t0 = getattr(main, "_start_time", _time.time())
    duration = int(_time.time() - _t0)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    write_status("success", ranked, source_summary, duration)
    update_index_timestamp()

    ok = git_push(f"TRUscore daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"â <b>TRUscore DDP done!</b>\nð {TODAY}\nð {len(qualified)} models\nð â trainingrun.ai/truscore-scores")
    else:
        notify(f"â ï¸ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
