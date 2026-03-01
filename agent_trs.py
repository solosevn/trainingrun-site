#!/usr/bin/env python3
"""
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  AGENT TRS â TRSbench Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRSbench V2.5 (Feb 2026)
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  18 sources scraped across 7 weighted pillars:
    1. Safety (21%)      HELM Safety + AIR-Bench
    2. Reasoning (20%)   ARC-AGI-2 + LiveBench + HELM Capabilities
    3. Coding (20%)      SWE-bench + EvalPlus + LiveCodeBench + SWE-rebench
    4. Human Pref (18%)  Arena Overall + Arena Text + AlpacaEval
    5. Knowledge (8%)    MMLU-Pro + HELM MMLU + SimpleQA
    6. Efficiency (7%)   Artificial Analysis + PricePerToken
    7. Usage (6%)        OpenRouter Rankings

  Qualification: 4+ categories with non-null scores.
  Scoring: Within each pillar, each source is normalized to 0â100,
           then averaged. Composite = weighted average across pillars,
           renormalized to 1.0 using available weights only.

  Usage:
    python3 agent_trs.py                  # live run
    python3 agent_trs.py --dry-run        # scrape + calculate, no push
    python3 agent_trs.py --test-telegram  # test Telegram connection only

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
from model_names import match_name, canonicalize

# ââ logging âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("trsbench")

# ââ CONFIG ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trs-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ââ TRSbench Bible V2.5 weights âââââââââââââââââââââââââââââââââââ
WEIGHTS = {
    "safety":           0.21,
    "reasoning":        0.20,
    "coding":           0.20,
    "human_preference": 0.18,
    "knowledge":        0.08,
    "efficiency":       0.07,
    "usage_adoption":   0.06,
}

QUALIFICATION_MIN_CATEGORIES = 1   # need 1+ pillar with non-null score to appear on board

# ââ Total sources count (for status.json) âââââââââââââââââââââââââ
TOTAL_SOURCES = 18

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


# ââ PLAYWRIGHT HELPERS ââââââââââââââââââââââââââââââââââââââââââââ
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


def _parse_helm_leaderboard(url: str, source_name: str, wait_ms: int = 10000) -> dict[str, float]:
    """
    Generic parser for Stanford CRFM HELM leaderboards.
    All HELM leaderboards share the same Vue table structure:
      col0 = model name, col1 = mean score (0.0-1.0 float)
    Returns {model: score_0_to_100}.
    """
    scores: dict[str, float] = {}
    try:
        log.info(f"Scraping {source_name} (HELM)...")
        html = playwright_get(url, wait_ms=wait_ms)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers) if "model" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "mean" in h or "score" in h or "average" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                raw_name = cells[model_col].get_text(strip=True)
                name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
                if not name or len(name) < 2:
                    continue
                score_raw = cells[score_col].get_text(strip=True)
                try:
                    val = float(score_raw)
                    if 0 < val <= 1.0:
                        val = round(val * 100, 4)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â {source_name}: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ {source_name} not available: {e}")
    return scores


# ââ SCRAPERS â SAFETY (21%) âââââââââââââââââââââââââââââââââââââââ

def scrape_helm_safety() -> dict[str, float]:
    """HELM Safety leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/safety/latest/#/leaderboard
    Measures: HarmBench, SimpleSafetyTests, BBQ, Anthropic Red Team, XSTest.
    87 models. Higher score = safer. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/safety/latest/#/leaderboard",
        "HELM Safety",
        wait_ms=12000,
    )


def scrape_airbench() -> dict[str, float]:
    """AIR-Bench (Stanford CRFM) â refusal-rate safety leaderboard.
    Source: https://crfm.stanford.edu/helm/air-bench/latest/#/leaderboard
    87 models. Measures compliance with AI safety regulations (refusal rate).
    Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/air-bench/latest/#/leaderboard",
        "AIR-Bench",
        wait_ms=12000,
    )


# ââ SCRAPERS â REASONING (20%) ââââââââââââââââââââââââââââââââââââ

def scrape_arc_agi2() -> dict[str, float]:
    """arcprize.org/leaderboard â ARC-AGI-2 column. Returns {model: score_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping ARC-AGI-2 (reasoning)...")
        url = "https://arcprize.org/leaderboard"
        html = playwright_get(url, wait_ms=10000)
        rows = parse_first_table(html)
        for row in rows:
            raw_name = row.get("AI System", "")
            if not raw_name:
                vals = list(row.values())
                raw_name = vals[0] if vals else ""
            if not raw_name:
                continue
            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            name = re.sub(r'\s*[Â²Â³Â¹â´âµ]\s*$', '', name).strip()
            arc2_raw = row.get("ARC-AGI-2", "")
            if not arc2_raw:
                continue
            clean = arc2_raw.replace("%", "").strip()
            try:
                pct = float(clean)
                if 0 <= pct <= 100:
                    if name not in scores or pct > scores[name]:
                        scores[name] = pct
            except ValueError:
                pass
        log.info(f"  â ARC-AGI-2: {len(scores)} models")
    except Exception as e:
        log.error(f"  â ARC-AGI-2: {e}")
    return scores


def scrape_livebench_reasoning() -> dict[str, float]:
    """LiveBench â contamination-free reasoning subcategory.
    Source: https://livebench.ai
    55+ models. Uses 'Reasoning Average' column (0-100). Returns {model: score}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping LiveBench Reasoning...")
        html = playwright_get("https://livebench.ai", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 0)
            # Prefer "reasoning average"; fall back to "global average"
            reason_col = next((i for i, h in enumerate(headers)
                               if "reasoning" in h), None)
            if reason_col is None:
                reason_col = next((i for i, h in enumerate(headers)
                                   if "global" in h or "average" in h or "score" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, reason_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[reason_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â LiveBench Reasoning: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ LiveBench Reasoning not available: {e}")
    return scores


def scrape_helm_capabilities() -> dict[str, float]:
    """HELM Capabilities leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/capabilities/latest/#/leaderboard
    68 models. Broad capability benchmark. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/capabilities/latest/#/leaderboard",
        "HELM Capabilities",
        wait_ms=12000,
    )


# ââ SCRAPERS â CODING (20%) âââââââââââââââââââââââââââââââââââââââ

def scrape_swebench_verified() -> dict[str, float]:
    """swebench.com â verified split leaderboard. Returns {model: pct_resolved}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench Verified (coding)...")
        html = playwright_get("https://www.swebench.com/", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "instance" in h or "name" in h), 0)
            pct_col  = next((i for i, h in enumerate(headers)
                             if "resolve" in h or "%" in h or "score" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, pct_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                val  = cells[pct_col].get_text(strip=True).replace("%", "").strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        scores[name] = pct
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SWE-bench Verified: {len(scores)} models")
    except Exception as e:
        log.error(f"  â SWE-bench: {e}")
    return scores


def scrape_evalplus() -> dict[str, float]:
    """EvalPlus â HumanEval+ coding leaderboard.
    Source: https://evalplus.github.io/leaderboard.html
    250+ models. HumanEval+ pass@1 percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping EvalPlus (coding)...")
        html = playwright_get("https://evalplus.github.io/leaderboard.html", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            # Columns: rank | name | HumanEval+ | HumanEval++ | ...
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "humaneval" in h or "pass" in h or "score" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'[â¨ð¥ð¥ð¥ââ]', '', name).strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â EvalPlus: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ EvalPlus not available: {e}")
    return scores


def scrape_livecodebench() -> dict[str, float]:
    """LiveCodeBench â contamination-free coding leaderboard.
    Source: https://livecodebench.github.io/leaderboard.html
    28+ models. PASS@1 percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping LiveCodeBench (coding)...")
        html = playwright_get("https://livecodebench.github.io/leaderboard.html", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "pass" in h or "score" in h or "overall" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â LiveCodeBench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ LiveCodeBench not available: {e}")
    return scores


def scrape_swe_rebench() -> dict[str, float]:
    """SWE-rebench â continuously decontaminated SWE benchmark.
    Source: https://swe-rebench.com/leaderboard
    84 models. Resolved rate percentage. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-rebench (coding)...")
        html = playwright_get("https://swe-rebench.com/leaderboard", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h or "system" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "resolve" in h or "%" in h or "score" in h or "pass" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SWE-rebench: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ SWE-rebench not available: {e}")
    return scores


# ââ SCRAPERS â HUMAN PREFERENCE (18%) ââââââââââââââââââââââââââââ

def scrape_arena_overall() -> dict[str, float]:
    """arena.ai main leaderboard â overall ELO across all task categories.
    Source: https://arena.ai/leaderboard  Returns {model: elo_float}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Arena Overall (human preference)...")
        url = "https://arena.ai/leaderboard"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)
            try:
                view_all = page.locator("text=View all").first
                if view_all.count():
                    view_all.click()
                    page.wait_for_timeout(4000)
            except Exception:
                pass
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 10:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 2)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "elo" in h or "rating" in h), 3)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                raw_val = cells[score_col].get_text(strip=True).replace(',', '')
                m = re.match(r'^(\d{3,4}(?:\.\d+)?)', raw_val)
                if m:
                    try:
                        val = float(m.group(1))
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            if scores:
                break
        log.info(f"  â Arena Overall: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Arena Overall: {e}")
    return scores


def scrape_arena_text() -> dict[str, float]:
    """Arena text-specific leaderboard â ELO for text/chat tasks only.
    Source: https://arena.ai/leaderboard/text  (313 models, text-specific ELO)
    Distinct from the overall multi-category ELO. Returns {model: elo_float}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Arena Text (human preference)...")
        url = "https://arena.ai/leaderboard/text"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 2)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "elo" in h or "rating" in h), 3)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                raw_val = cells[score_col].get_text(strip=True).replace(',', '')
                m = re.match(r'^(\d{3,4}(?:\.\d+)?)', raw_val)
                if m:
                    try:
                        val = float(m.group(1))
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            if scores:
                break
        log.info(f"  â Arena Text: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ Arena Text not available: {e}")
    return scores


def scrape_alpacaeval() -> dict[str, float]:
    """AlpacaEval 2.0 â LC (length-controlled) win rate leaderboard.
    Source: https://tatsu-lab.github.io/alpaca_eval/
    68 models. LC win rate % vs GPT-4 baseline. Returns {model: pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping AlpacaEval (human preference)...")
        html = playwright_get("https://tatsu-lab.github.io/alpaca_eval/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "lc" in h or "win" in h or "rate" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*ð.*$', '', name).strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â AlpacaEval: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ AlpacaEval not available: {e}")
    return scores


# ââ SCRAPERS â KNOWLEDGE (8%) âââââââââââââââââââââââââââââââââââââ

def scrape_mmlu_pro() -> dict[str, float]:
    """huggingface.co/spaces/TIGER-Lab/MMLU-Pro â knowledge leaderboard (via iframe)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping MMLU-Pro (knowledge)...")
        url = "https://huggingface.co/spaces/TIGER-Lab/MMLU-Pro"
        html = playwright_get_hfspace(url, wait_ms=15000)
        rows = parse_first_table(html)
        for row in rows:
            name = row.get("Models", "")
            if not name:
                vals = list(row.values())
                name = vals[0] if vals else ""
            if not name:
                continue
            overall_raw = row.get("Overall", "")
            if not overall_raw or overall_raw == "-":
                continue
            clean = overall_raw.replace("%", "").strip()
            try:
                val = float(clean)
                if 0 < val <= 1.0:
                    scores[name] = round(val * 100, 4)
                elif 1 < val <= 100:
                    scores[name] = val
            except ValueError:
                pass
        log.info(f"  â MMLU-Pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  â MMLU-Pro: {e}")
    return scores


def scrape_helm_mmlu() -> dict[str, float]:
    """HELM MMLU leaderboard (Stanford CRFM).
    Source: https://crfm.stanford.edu/helm/mmlu/latest/#/leaderboard
    Accuracy on MMLU knowledge benchmark. Returns {model: 0-100}."""
    return _parse_helm_leaderboard(
        "https://crfm.stanford.edu/helm/mmlu/latest/#/leaderboard",
        "HELM MMLU",
        wait_ms=12000,
    )


def scrape_simpleqa() -> dict[str, float]:
    """SimpleQA leaderboard via llm-stats.com.
    Source: https://llm-stats.com/benchmarks/simpleqa
    43 models. Factual accuracy 0-1 float. Returns {model: 0-100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SimpleQA (knowledge)...")
        html = playwright_get("https://llm-stats.com/benchmarks/simpleqa", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "accuracy" in h or "correct" in h), 2)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, score_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                val_raw = cells[score_col].get_text(strip=True).replace('%', '').strip()
                try:
                    val = float(val_raw)
                    if 0 < val <= 1.0:
                        val = round(val * 100, 4)
                    if 0 < val <= 100:
                        if name not in scores or val > scores[name]:
                            scores[name] = val
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  â SimpleQA: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ SimpleQA not available: {e}")
    return scores


# ââ SCRAPERS â EFFICIENCY (7%) ââââââââââââââââââââââââââââââââââââ

def scrape_artificial_analysis() -> dict[str, float]:
    """artificialanalysis.ai/leaderboards/models -- efficiency (Median Tokens/s)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Artificial Analysis (efficiency)...")
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
                return allRows.slice(2).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {model: cells[0] || '', speed: cells[5] || ''};
                }).filter(r => r.model && r.speed);
            }""")
            browser.close()

        for row in rows:
            name = row.get("model", "")
            name = re.sub(r'\s*\([^)]+\)\s*$', '', name).strip()
            if not name:
                continue
            speed_raw = row.get("speed", "")
            try:
                val = float(speed_raw.replace(",", "").strip())
                if val > 0:
                    scores[name] = val
            except ValueError:
                pass
        log.info(f"  â Artificial Analysis: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Artificial Analysis: {e}")
    return scores


def scrape_pricepertoken() -> dict[str, float]:
    """PricePerToken â $/M input tokens leaderboard.
    Source: https://pricepertoken.com
    298 models. Lower price = better efficiency. Score inverted: cheapest = 100.
    Returns {model: inverted_score_0_to_100}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping PricePerToken (efficiency)...")
        html = playwright_get("https://pricepertoken.com", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers)
                              if "model" in h or "name" in h), 1)
            # Prefer "input" pricing column ($/M tokens input)
            price_col = next((i for i, h in enumerate(headers)
                              if "input" in h), None)
            if price_col is None:
                price_col = next((i for i, h in enumerate(headers)
                                  if "price" in h or "$" in h or "cost" in h), 2)
            raw_prices: dict[str, float] = {}
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, price_col):
                    continue
                name = cells[model_col].get_text(separator='\n', strip=True).split('\n')[0].strip()
                name = re.sub(r'\s*\([^)]*\)', '', name).strip()
                if not name or len(name) < 2:
                    continue
                price_raw = cells[price_col].get_text(strip=True).replace('$', '').replace(',', '').strip()
                try:
                    price = float(price_raw)
                    if price >= 0:
                        raw_prices[name] = price
                except ValueError:
                    pass
            if raw_prices:
                # Invert: cheapest model gets highest score
                # Use log scale to handle wide price ranges (free to $$$)
                import math
                min_price = min(v for v in raw_prices.values() if v > 0) if any(v > 0 for v in raw_prices.values()) else 0.001
                for name, price in raw_prices.items():
                    effective = max(price, min_price * 0.1)
                    # Higher score = cheaper. Score = 100 * (min_price / price)
                    inv_score = round(100.0 * min_price / effective, 4)
                    scores[name] = min(inv_score, 100.0)
                break
        log.info(f"  â PricePerToken: {len(scores)} models")
    except Exception as e:
        log.warning(f"  â ï¸ PricePerToken not available: {e}")
    return scores


# ââ SCRAPERS â USAGE ADOPTION (6%) ââââââââââââââââââââââââââââââââ

def scrape_openrouter_usage() -> dict[str, float]:
    """openrouter.ai/rankings â usage adoption scores (innerText parse, no <table>)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping OpenRouter Rankings (usage adoption)...")
        url = "https://openrouter.ai/rankings"
        text = playwright_get_innertext(url, wait_ms=10000)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        rank_num = 0
        for i, line in enumerate(lines):
            if re.match(r'^\d+\.$', line):
                rank_num = int(line[:-1])
                if i + 1 < len(lines):
                    name = lines[i + 1]
                    if name and len(name) > 2 and not name.lower().startswith("by "):
                        rank_score = max(0, 100 - ((rank_num - 1) * 2))
                        if rank_score > 0:
                            scores[name] = rank_score
        log.info(f"  â OpenRouter Rankings: {len(scores)} models")
    except Exception as e:
        log.error(f"  â OpenRouter Rankings: {e}")
    return scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ

def normalize_sources_and_merge(scraper_list: list) -> tuple[dict[str, float], int]:
    """
    Run all scrapers for a pillar. For each source:
      1. Normalize to 0-100 (top model in that source = 100)
      2. Merge by averaging normalized scores across sources
    Returns merged {model: avg_normalized_score}.
    Models appearing in more sources get their scores averaged.
    """
    merged: dict[str, float] = {}
    counts: dict[str, int] = {}
    sources_hit = 0
    for scraper_fn in scraper_list:
        raw = scraper_fn()
        if not raw:
            continue
        top = max(raw.values())
        if top <= 0:
            continue
        sources_hit += 1
        for model, val in raw.items():
            norm = (val / top) * 100.0
            merged[model] = merged.get(model, 0.0) + norm
            counts[model] = counts.get(model, 0) + 1
    if not merged:
        return {}
    return {m: round(merged[m] / counts[m], 4) for m in merged}, sources_hit


def normalize_across_models(models: list, category: str, raw_values: dict[str, float]) -> dict[str, float]:
    """
    Top performer = 100. Others proportional.
    Only models with non-null/non-zero values are normalized.
    """
    vals = {m["name"]: raw_values.get(m["name"]) for m in models}
    vals = {k: v for k, v in vals.items() if v is not None and v > 0}
    if not vals:
        return {}
    top = max(vals.values())
    return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def calculate_composite(model_name: str, normalized: dict) -> tuple[float, int]:
    """
    Coverage-aware composite score.
    Step 1: Weighted average across available pillars (weights renormalized to sum 1.0).
    Step 2: Apply mild coverage dampener so new/sparse models rank below fully-covered ones.
            dampener = 0.70 + 0.30 * (covered_pillars / total_pillars)
            - 1/7 pillars covered → ×0.74  (shows up, clearly lower)
            - 4/7 pillars covered → ×0.87  (respectably scored)
            - 7/7 pillars covered → ×1.00  (no penalty, full score)
    Models with 0 pillars are excluded (score=0, not ranked).
    """
    total_pillars = len(WEIGHTS)
    available_weights = {k: WEIGHTS[k] for k in WEIGHTS
                         if normalized.get(k, {}).get(model_name, None) is not None
                         and normalized[k].get(model_name, 0.0) > 0}
    if not available_weights:
        return 0.0, 0
    weight_sum = sum(available_weights.values())
    raw_composite = sum(normalized[k].get(model_name, 0.0) * (w / weight_sum)
                        for k, w in available_weights.items())
    covered = len(available_weights)
    dampener = 0.70 + 0.30 * (covered / total_pillars)
    penalized = round(raw_composite * dampener, 2)
    return penalized, covered


def generate_checksum(data: dict) -> str:
    """Bible V2.5 canonical: names|...|:scores,...  with .1f formatting."""
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


AUTO_DISCOVER_MIN_SOURCES = 2  # model must appear in 2+ pillars to join roster

def auto_discover_models(data: dict, all_results: dict) -> list[str]:
    """
    Scan all scraped pillar results. A model must appear in at least
    AUTO_DISCOVER_MIN_SOURCES separate pillars before it is added to the roster.
    This filters out one-off fine-tunes and noise while letting legitimate
    multi-benchmark models through. Uses match_name() to avoid duplicates.
    Returns list of newly added model names.
    """
    existing_names = [m["name"] for m in data["models"]]
    newly_added = []

    # Count how many pillars each scraped name appears in
    pillar_counts: dict[str, int] = {}
    for pillar_results in all_results.values():
        for name in pillar_results:
            pillar_counts[name] = pillar_counts.get(name, 0) + 1

    for name in sorted(pillar_counts):
        # Basic sanity filter — skip obvious garbage
        if not name or len(name) < 3 or name.replace("-", "").replace("_", "").isdigit():
            continue
        # Must appear in 2+ separate pillars to qualify
        if pillar_counts[name] < AUTO_DISCOVER_MIN_SOURCES:
            continue
        # Skip if already in roster (exact or fuzzy match)
        if match_name(name, existing_names) is not None:
            continue
        # New model — build entry with null score history for all past dates
        new_entry = {
            "name":           name,
            "company":        _infer_company(name),
            "rank":           999,
            "scores":         [None] * len(data["dates"]),
            "category_count": 0,
            "pillar_scores":  {},
        }
        data["models"].append(new_entry)
        existing_names.append(name)
        newly_added.append(name)
        log.info(f"  ★ Auto-discovered: {name} ({new_entry['company']}) [{pillar_counts[name]} pillars]")

    return newly_added


# match_name and canonicalize imported from model_names

def write_status(status: str, ranked: list, source_summary: list,
                 duration_sec: int, sources_hit: int = 0, error: str | None = None) -> None:
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

        sdata["last_updated"] = now_iso
        sdata["agents"]["trsbench"] = {
            "name":             "TRSbench DDP",
            "label":            "Overall Rankings",
            "emoji":            "🏆",
            "enabled":          True,
            "last_run":         now_iso,
            "last_run_date":    TODAY,
            "status":           status,
            "duration_seconds": duration_sec,
            "sources_total":    TOTAL_SOURCES,
            "sources_hit":      sources_hit,
            "models_qualified": len(ranked),
            "top_model":        ranked[0]["name"] if ranked else None,
            "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5":             top5,
            "leaderboard_url":  "/scores.html",
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
    index_file = REPO_PATH  / "index.html"
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
        subprocess.run(["git", "add", "trs-data.json", "status.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit â data unchanged.")
                return True
            log.error(f"Commit failed:\n{r.stderr}")
            return False
        # Stash any dirty files so rebase can proceed
        subprocess.run(["git", "stash", "--include-untracked"], cwd=REPO_PATH, capture_output=True)
        pull = subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                              cwd=REPO_PATH, capture_output=True, text=True)
        if pull.returncode != 0:
            log.warning(f"pull --rebase failed: {pull.stderr}")
            subprocess.run(["git", "rebase", "--abort"], cwd=REPO_PATH, capture_output=True)
            subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, capture_output=True)
        subprocess.run(["git", "push"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        log.info("â Pushed to GitHub")
        subprocess.run(["git", "stash", "pop"], cwd=REPO_PATH, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e.stderr}")
        return False


# ââ PILLAR â SCRAPER REGISTRY ââââââââââââââââââââââââââââââââââââ
# Each pillar maps to an ordered list of scrapers.
# All scrapers for a pillar are run, normalized to 0-100 individually,
# then averaged. Models only need to appear in ONE source per pillar.

PILLAR_SCRAPERS = {
    "safety": [
        scrape_helm_safety,     # HELM Safety (Stanford CRFM) â 87 models
        scrape_airbench,        # AIR-Bench (Stanford CRFM)   â 87 models
    ],
    "reasoning": [
        scrape_arc_agi2,               # ARC-AGI-2 (arcprize.org)           â 100+ models
        scrape_livebench_reasoning,    # LiveBench Reasoning Average         â  55 models
        scrape_helm_capabilities,      # HELM Capabilities (Stanford CRFM)  â  68 models
    ],
    "coding": [
        scrape_swebench_verified,  # SWE-bench Verified (swebench.com)   â 40+ models
        scrape_evalplus,           # EvalPlus HumanEval+ (GitHub)         â 250 models
        scrape_livecodebench,      # LiveCodeBench (GitHub)               â  28 models
        scrape_swe_rebench,        # SWE-rebench decontaminated (Web)     â  84 models
    ],
    "human_preference": [
        scrape_arena_overall,  # Arena main ELO (arena.ai)          â 313 models
        scrape_arena_text,     # Arena text-specific ELO (arena.ai)  â 313 models
        scrape_alpacaeval,     # AlpacaEval 2.0 LC win rate          â  68 models
    ],
    "knowledge": [
        scrape_mmlu_pro,    # MMLU-Pro HF Space              â 50+ models
        scrape_helm_mmlu,   # HELM MMLU (Stanford CRFM)      â  10+ models
        scrape_simpleqa,    # SimpleQA via llm-stats.com      â  43 models
    ],
    "efficiency": [
        scrape_artificial_analysis,  # Artificial Analysis tokens/s  â 100+ models
        scrape_pricepertoken,        # PricePerToken $/M input        â 298 models
    ],
    "usage_adoption": [
        scrape_openrouter_usage,  # OpenRouter weekly token rankings â 50 models
    ],
}


# ââ MAIN ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def main():
    import time as _time
    main._start_time = _time.time()

    if TEST_TELEGRAM:
        notify("â <b>TRSbench DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN ð" if DRY_RUN else "LIVE ð"
    log.info(f"TRSbench DDP | {TODAY} | {mode}")
    notify(f"ð¤ <b>TRSbench DDP starting</b>\nð {TODAY}\nâï¸ {mode}\n{TOTAL_SOURCES} sources â trs-data.json")

    # ââ Load data ââ
    if not DATA_FILE.exists():
        msg = f"trs-data.json not found at {DATA_FILE}"
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
        notify(f"âµï¸ {TODAY} exists at index {today_idx}. Refreshing.")
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1
        notify(f"â New date: {TODAY} (slot {today_idx})")

    # ââ Scrape all pillars (multi-source per pillar) ââ
    all_results:   dict[str, dict[str, float]] = {}
    total_matched  = 0
    total_sources_hit = 0
    source_summary = []

    for category, scraper_list in PILLAR_SCRAPERS.items():
        log.info(f"\nââ {category.upper()} ({len(scraper_list)} sources) ââ")
        result, sources_hit = normalize_sources_and_merge(scraper_list)
        all_results[category] = result
        total_sources_hit += sources_hit

        matched = sum(1 for name in result if match_name(name, names))
        total_matched += matched
        source_summary.append(
            f"{category}: {sources_hit}/{len(scraper_list)} sources live, "
            f"{len(result)} scraped, {matched} matched to known models"
        )
        log.info(f"  â {sources_hit}/{len(scraper_list)} sources live | "
                 f"{len(result)} models scraped | {matched} matched")

    notify("ð <b>Scraping complete</b>\n" + "\n".join(source_summary))


    # ── Auto-discover new models ──
    new_models = auto_discover_models(data, all_results)
    if new_models:
        log.info(f"★ Auto-discovered {len(new_models)} new models: {new_models}")
        notify(f"★ <b>Auto-discovered {len(new_models)} new models</b>\n"
               + "\n".join(f"  • {n}" for n in new_models[:10])
               + (f"\n  ...and {len(new_models)-10} more" if len(new_models) > 10 else ""))
        models = data["models"]   # refresh reference after append
        names  = [m["name"] for m in models]

    # ââ Normalize + score ââ
    normalized = {}
    for category, raw_values in all_results.items():
        normalized[category] = normalize_across_models(models, category, raw_values)

    for model in models:
        n  = model["name"]
        sc, cat_count = calculate_composite(n, normalized)
        model["category_count"] = cat_count
        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(sc)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = sc
            else:
                model["scores"].append(sc)

        # ── Save latest per-pillar scores (for leaderboard display) ──
        pillar_scores = {}
        for cat, cat_scores in normalized.items():
            val = cat_scores.get(n)
            if val is not None:
                pillar_scores[cat] = round(val, 1)
        if pillar_scores:
            model["pillar_scores"] = pillar_scores

    # ââ Qualification filter ââ
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified    = [m for m in models if m["category_count"] >= QUALIFICATION_MIN_CATEGORIES]
    disqualified = [m for m in models if m["category_count"] < QUALIFICATION_MIN_CATEGORIES]
    if disqualified:
        log.info(f"Excluded (0 pillars today — no data): "
                 f"{[m['name'] for m in disqualified]}")

    # ââ Update ranks ââ
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"🏆 <b>TRSbench Top 5 â {TODAY}</b>\n{top5_lines}")

    # ââ Checksum ââ
    data["checksum"] = generate_checksum(data)
    log.info(f"Checksum: {data['checksum'][:20]}...")

    if DRY_RUN:
        notify(f"ð <b>DRY RUN complete</b>\nWould score {len(qualified)} models.\nNothing written.")
        log.info("Dry run complete. Nothing written.")
        return

    # ââ Write + push ââ
    _t0 = getattr(main, "_start_time", _time.time())
    duration = int(_time.time() - _t0)

    from datetime import datetime as _dt
    data["run_at"] = _dt.now().strftime("%-I:%M %p") + " CST"

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    write_status("success", ranked, source_summary, duration,
                 sources_hit=total_sources_hit)
    update_index_timestamp()

    ok = git_push(f"TRSbench daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"â <b>TRSbench DDP done!</b>\nð {TODAY}\nð {len(qualified)} models\nð â trainingrun.ai/scores")
    else:
        notify(f"â ï¸ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
