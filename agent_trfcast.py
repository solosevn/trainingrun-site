#!/usr/bin/env python3
"""
agent_trfcast.py - TRFcast Daily Scraper
trainingrun.ai | solosevn/trainingrun-site
Bible: TRFcast V1.1 (Feb 2026)

4 sources | 9 sub-metrics | 5 pillars:
  1. ForecastBench   forecastbench.org      Forecasting Accuracy (30%) + Calibration (20%)
  2. Rallies.ai      rallies.ai             Trading Performance (15%) + Market Intel (5%)
  3. Alpha Arena     nof1.ai                Trading Performance (10%) + Market Intel (5%)
  4. FinanceArena    financearena.ai        Financial Reasoning (15%)

Qualification: 3+ of 5 pillars non-null.

Usage:
  python3 agent_trfcast.py
  python3 agent_trfcast.py --dry-run
  python3 agent_trfcast.py --test-telegram

Env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, REPO_PATH
Deps: pip3 install playwright python-telegram-bot beautifulsoup4
      python3 -m playwright install chromium
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re
from datetime import date
from pathlib import Path

for pkg, hint in [
    ("playwright", "pip3 install playwright && python3 -m playwright install chromium"),
    ("bs4",        "pip3 install beautifulsoup4"),
    ("telegram",   "pip3 install python-telegram-bot"),
]:
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: {hint}")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from telegram import Bot

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("trfcast")

# == CONFIG
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trf-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# -- TRFcast Bible V1.0 weights (9 sub-metrics, sums to 1.0)
WEIGHTS = {
    "forecasting_baseline":        0.20,
    "forecasting_tournament":      0.10,
    "trading_rallies":             0.15,
    "trading_alpha_arena":         0.10,
    "calibration_forecastbench":   0.20,
    "financial_reasoning_qa":      0.08,
    "financial_reasoning_compare": 0.07,
    "market_intel_sharpe":         0.05,
    "market_intel_winrate":        0.05,
}

RAW_KEYS = {
    "forecasting_baseline":        "forecastbench_baseline_brier",
    "forecasting_tournament":      "forecastbench_tournament_brier",
    "trading_rallies":             "rallies_return_pct",
    "trading_alpha_arena":         "alpha_arena_return_pct",
    "calibration_forecastbench":   "forecastbench_calibration",
    "financial_reasoning_qa":      "financearena_qa_pct",
    "financial_reasoning_compare": "financearena_elo",
    "market_intel_sharpe":         "alpha_arena_sharpe",
    "market_intel_winrate":        "rallies_win_rate",
}

PILLARS = ["forecasting", "trading", "calibration", "financial_reasoning", "market_intelligence"]
QUALIFICATION_MIN = 3
LOWER_IS_BETTER = {"forecastbench_baseline_brier", "forecastbench_tournament_brier"}


# == TELEGRAM
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


# == PLAYWRIGHT HELPER
def playwright_get(url: str, wait_ms: int = 6000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=90_000)
        page.wait_for_timeout(wait_ms)
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


# == SCRAPERS

def scrape_forecastbench() -> dict:
    results = {}
    try:
        log.info("Scraping ForecastBench...")
        html = playwright_get("https://forecastbench.org/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            for script in soup.find_all("script"):
                if script.string and "brier" in script.string.lower():
                    try:
                        m = re.search(r'\[(.+?)\]', script.string, re.DOTALL)
                        if m:
                            entries = json.loads("[" + m.group(1) + "]")
                            for e in entries:
                                name = e.get("model") or e.get("name", "")
                                if name:
                                    results[name] = {
                                        "baseline_brier":   e.get("brier") or e.get("baseline_brier"),
                                        "tournament_brier": e.get("tournament_brier"),
                                        "calibration":      e.get("calibration"),
                                    }
                            if results:
                                break
                    except Exception:
                        pass
        else:
            target = max(tables, key=lambda t: len(t.find_all("tr")))
            rows = target.find_all("tr")
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col  = next((i for i, h in enumerate(headers) if "model" in h or "name" in h), 0)
            brier_col = next((i for i, h in enumerate(headers) if "brier" in h or "baseline" in h), 1)
            tourn_col = next((i for i, h in enumerate(headers) if "tournament" in h), None)
            calib_col = next((i for i, h in enumerate(headers) if "calibr" in h), None)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                name = cells[name_col].get_text(strip=True) if name_col < len(cells) else ""
                if not name:
                    continue
                def _float(i):
                    if i is None or i >= len(cells):
                        return None
                    try:
                        return float(cells[i].get_text(strip=True).replace("%","").strip())
                    except ValueError:
                        return None
                results[name] = {
                    "baseline_brier":   _float(brier_col),
                    "tournament_brier": _float(tourn_col),
                    "calibration":      _float(calib_col),
                }
        log.info(f"  forecastbench: {len(results)} models")
    except Exception as e:
        log.error(f"  ForecastBench error: {e}")
    return results


def scrape_rallies() -> dict:
    results = {}
    try:
        log.info("Scraping Rallies.ai...")
        html = playwright_get("https://rallies.ai/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "return" in text.lower() and "model" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            if name:
                                results[name] = {
                                    "return_pct": e.get("return") or e.get("return_pct"),
                                    "win_rate":   e.get("win_rate") or e.get("winRate"),
                                }
                        if results:
                            break
                except Exception:
                    pass
        if not results:
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
                    continue
                name = vals[0]
                ret_val, win_val = None, None
                for k, v in row.items():
                    kl = k.lower()
                    if "return" in kl:
                        try: ret_val = float(v.replace("%","").strip())
                        except ValueError: pass
                    if "win" in kl:
                        try: win_val = float(v.replace("%","").strip())
                        except ValueError: pass
                if name and (ret_val is not None or win_val is not None):
                    results[name] = {"return_pct": ret_val, "win_rate": win_val}
        log.info(f"  rallies: {len(results)} models")
    except Exception as e:
        log.error(f"  Rallies error: {e}")
    return results


def scrape_alpha_arena() -> dict:
    results = {}
    try:
        log.info("Scraping Alpha Arena (nof1.ai)...")
        html = playwright_get("https://nof1.ai/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "sharpe" in text.lower() or "alpha" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            if name:
                                results[name] = {
                                    "return_pct": e.get("return") or e.get("return_pct"),
                                    "sharpe":     e.get("sharpe") or e.get("sharpe_ratio"),
                                }
                        if results:
                            break
                except Exception:
                    pass
        if not results:
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
#!/usr/bin/env python3
                  """
                  ════════════════════════════════════════════════════════════════════
                    AGENT TRFCAST — TRFcast Daily Scraper
                      trainingrun.ai | solosevn/trainingrun-site
                        Bible: TRFcast V1.0 (Feb 21, 2026)
                        ════════════════════════════════════════════════════════════════════
                          4 source platforms scraped (9 sub-metrics):
                              1. ForecastBench         forecastbench.org                20%
                                     - Baseline Brier (INVERTED)
                                            - Tournament Brier (INVERTED)
                                                2. Rallies.ai            rallies.ai                       20%
                                                       - Portfolio Returns, Win Rate
                                                           3. Alpha Arena           nof1.ai                          15%
                                                                  - Returns, Sharpe Ratio
                                                                      4. FinanceArena          financearena.ai                  15%
                                                                             - QA Accuracy, ELO Rating
                                                                                 Plus Calibration on ForecastBench Baseline (20%)
                                                                                     Plus Financial Reasoning QA/Compare (15%)
                                                                                         Plus Market Intelligence Sharpe/Winrate (10%)
                                                                                         
                                                                                           Qualification: 3+ of 5 pillars with non-null scores.
                                                                                             Scoring: Option A — proportional normalization over 9 sub-metrics.
                                                                                             
                                                                                               Usage:
                                                                                                   python3 agent_trfcast.py                  # live run
                                                                                                       python3 agent_trfcast.py --dry-run        # scrape + calculate, no push
                                                                                                           python3 agent_trfcast.py --test-telegram  # test Telegram connection only
                                                                                                           
                                                                                                             Env vars:
                                                                                                                 TELEGRAM_TOKEN     BotFather token
                                                                                                                     TELEGRAM_CHAT_ID   Your numeric chat ID
                                                                                                                         REPO_PATH          Path to local trainingrun-site clone
                                                                                                                                                Default: ~/trainingrun-site
                                                                                                                                                
                                                                                                                                                  Dependencies:
                                                                                                                                                      pip3 install playwright python-telegram-bot beautifulsoup4 requests
                                                                                                                                                          python3 -m playwright install chromium
                                                                                                                                                          ════════════════════════════════════════════════════════════════════
                                                                                                                                                          """
                  
                  import os, sys, json, hashlib, subprocess, asyncio, logging, re
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

# ── logging ───────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                                        format="%(asctime)s  %(levelname)-7s  %(message)s",
                                        datefmt="%H:%M:%S")
log = logging.getLogger("trfcast")

# ══ CONFIG ════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                                                               str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trf-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ── TRFcast Bible V1.0 weights (9 sub-metrics) ────────────────────
WEIGHTS = {
      "forecasting_baseline":       0.20,  # ForecastBench Brier (INVERTED)
      "forecasting_tournament":     0.10,  # ForecastBench Tournament (INVERTED)
      "trading_rallies":            0.15,  # Rallies.ai returns
      "trading_alpha_arena":        0.10,  # Alpha Arena returns
      "calibration_forecastbench":  0.20,  # ForecastBench calibration (INVERTED)
      "financial_reasoning_qa":     0.08,  # FinanceArena QA %
      "financial_reasoning_compare":0.07,  # FinanceArena ELO
      "market_intel_sharpe":        0.05,  # Alpha Arena Sharpe ratio
      "market_intel_winrate":       0.05,  # Rallies.ai win rate
}

# Maps weight keys to raw_data field names
RAW_KEYS = {
      "forecasting_baseline":        "forecastbench_baseline_brier",
      "forecasting_tournament":      "forecastbench_tournament_brier",
      "trading_rallies":             "rallies_return_pct",
      "trading_alpha_arena":         "alpha_arena_return_pct",
      "calibration_forecastbench":   "forecastbench_baseline_brier",  # reuses baseline
      "financial_reasoning_qa":      "financearena_qa_pct",
      "financial_reasoning_compare": "financearena_elo",
      "market_intel_sharpe":         "alpha_arena_sharpe",
      "market_intel_winrate":        "rallies_win_rate",
}

# Brier scores: lower = better (inverted normalization)
INVERTED_KEYS = {"forecasting_baseline", "forecasting_tournament", "calibration_forecastbench"}

# Maps sub-metrics to pillars
PILLAR_MAP = {
      "forecasting": ["forecasting_baseline", "forecasting_tournament"],
      "trading": ["trading_rallies", "trading_alpha_arena"],
      "calibration": ["calibration_forecastbench"],
      "financial_reasoning": ["financial_reasoning_qa", "financial_reasoning_compare"],
      "market_intelligence": ["market_intel_sharpe", "market_intel_winrate"],
}

QUALIFICATION_MIN_PILLARS = 3   # Must have 3 of 5 pillars


# ══ TELEGRAM ══════════════════════════════════════════════════════
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


# ══ PLAYWRIGHT HELPER ═════════════════════════════════════════════
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


# ══ SCRAPERS ══════════════════════════════════════════════════════

def scrape_forecastbench() -> tuple[dict[str, float], dict[str, float]]:
      """
          ForecastBench leaderboard. Returns two dicts:
              - baseline Brier scores (0.0-1.0, lower is better)
                  - tournament Brier scores (0.0-1.0, lower is better)
                      """
    baseline_scores = {}
    tournament_scores = {}
    try:
              log.info("Scraping ForecastBench...")
        html = playwright_get("https://forecastbench.org/leaderboard", wait_ms=10000)
        rows = parse_first_table(html)
        
        for row in rows:
                      vals = list(row.values())
                      if len(vals) < 2:
                                        continue
                                    name = vals[0]
            
            # Try to extract baseline and tournament Brier scores
            # Typical columns: Model, Baseline Brier, Tournament Brier, ...
            if len(vals) > 1:
                              try:
                                                    val = float(vals[1].replace("%", "").strip())
                                                    if 0 <= val <= 1:
                                                                              baseline_scores[name] = val
                              except (ValueError, IndexError):
                                                    pass
                                            if len(vals) > 2:
                                                              try:
                                                                                    val = float(vals[2].replace("%", "").strip())
                                                                                    if 0 <= val <= 1:
                                                                                                              tournament_scores[name] = val
                                                                except (ValueError, IndexError):
                    pass
        
        log.info(f"  ✅ ForecastBench: {len(baseline_scores)} baseline, {len(tournament_scores)} tournament")
except Exception as e:
        log.error(f"  ❌ ForecastBench: {e}")
    
    return baseline_scores, tournament_scores


def scrape_rallies() -> tuple[dict[str, float], dict[str, float]]:
      """
          Rallies.ai portfolio leaderboard. Returns two dicts:
              - return_pct: portfolio returns (%)
                  - win_rate_pct: win rate (%)
                      """
    return_scores = {}
    winrate_scores = {}
    try:
              log.info("Scraping Rallies.ai...")
        html = playwright_get("https://rallies.ai/", wait_ms=8000)
        rows = parse_first_table(html)
        
        for row in rows:
                      vals = list(row.values())
            if len(vals) < 2:
                              continue
            name = vals[0]
            
            # Try to extract returns and win rate
            if len(vals) > 1:
                              try:
                                                    val = float(vals[1].replace("%", "").strip())
                    if -1000 <= val <= 10000:  # Allow wide range for returns
                                              return_scores[name] = val
except (ValueError, IndexError):
                    pass
            if len(vals) > 2:
                              try:
                                                    val = float(vals[2].replace("%", "").strip())
                    if 0 <= val <= 100:
                                              winrate_scores[name] = val
except (ValueError, IndexError):
                    pass
        
        log.info(f"  ✅ Rallies.ai: {len(return_scores)} returns, {len(winrate_scores)} win rates")
except Exception as e:
        log.error(f"  ❌ Rallies.ai: {e}")
    
    return return_scores, winrate_scores


def scrape_alpha_arena() -> tuple[dict[str, float], dict[str, float]]:
      """
          Alpha Arena (nof1.ai) leaderboard. Returns two dicts:
              - return_pct: portfolio returns (%)
                  - sharpe_ratio: Sharpe ratio
                      """
    return_scores = {}
    sharpe_scores = {}
    try:
              log.info("Scraping Alpha Arena...")
        html = playwright_get("https://nof1.ai/", wait_ms=8000)
        rows = parse_first_table(html)
        
        for row in rows:
                      vals = list(row.values())
            if len(vals) < 2:
                              continue
            name = vals[0]
            
            # Try to extract returns and Sharpe
            if len(vals) > 1:
                              try:
                                                    val = float(vals[1].replace("%", "").strip())
                    if -1000 <= val <= 10000:
                                              return_scores[name] = val
except (ValueError, IndexError):
                    pass
            if len(vals) > 2:
                              try:
                                                    val = float(vals[2].replace("%", "").strip())
                    if -100 <= val <= 100:  # Sharpe can be negative
                                              sharpe_scores[name] = val
except (ValueError, IndexError):
                    pass
        
        log.info(f"  ✅ Alpha Arena: {len(return_scores)} returns, {len(sharpe_scores)} Sharpe")
except Exception as e:
        log.error(f"  ❌ Alpha Arena: {e}")
    
    return return_scores, sharpe_scores


def scrape_financearena() -> tuple[dict[str, float], dict[str, float]]:
      """
          FinanceArena leaderboard. Returns two dicts:
              - qa_pct: QA accuracy (%)
                  - elo_score: ELO rating
                      """
    qa_scores = {}
    elo_scores = {}
    try:
              log.info("Scraping FinanceArena...")
        html = playwright_get("https://financearena.ai/", wait_ms=8000)
        rows = parse_first_table(html)
        
        for row in rows:
                      vals = list(row.values())
            if len(vals) < 2:
                              continue
            name = vals[0]
            
            # Try to extract QA accuracy and ELO
            if len(vals) > 1:
                              try:
                                                    val = float(vals[1].replace("%", "").strip())
                    if 0 <= val <= 100:
                                              qa_scores[name] = val
except (ValueError, IndexError):
                    pass
            if len(vals) > 2:
                              try:
                                                    val = float(vals[2].replace("%", "").strip())
                    if 0 <= val <= 3000:  # Typical ELO range
                                              elo_scores[name] = val
except (ValueError, IndexError):
                    pass
        
        log.info(f"  ✅ FinanceArena: {len(qa_scores)} QA, {len(elo_scores)} ELO")
except Exception as e:
        log.error(f"  ❌ FinanceArena: {e}")
    
    return qa_scores, elo_scores


# ══ SCORING ENGINE ════════════════════════════════════════════════

def normalize_across_models(models: list, raw_key: str, inverted: bool = False) -> dict[str, float]:
      """
          Top performer = 100. Others proportional.
              If inverted: lower raw value = better (for Brier scores).
                  """
    vals = {m["name"]: m["raw_data"].get(raw_key) for m in models}
    vals = {k: v for k, v in vals.items() if v is not None and v >= 0}
    
    if not vals:
              return {}
    
    if inverted:
              min_val = min(vals.values())
        if min_val <= 0:
                      return {k: 0.0 for k in vals}
        return {k: round((min_val / v) * 100.0, 4) for k, v in vals.items()}
else:
        top = max(vals.values())
        if top == 0:
                      return {k: 0.0 for k in vals}
        return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def calculate_pillar_scores(model_name: str, normalized: dict) -> dict[str, float | None]:
      """Calculate per-pillar weighted average scores."""
    pillar_scores = {}
    for pillar, sub_keys in PILLAR_MAP.items():
              available = [(k, WEIGHTS[k]) for k in sub_keys 
                                                if normalized.get(k, {}).get(model_name) is not None
                                                and normalized[k].get(model_name, 0.continue
                name = vals[0]
                ret_val, sharpe_val = None, None
                for k, v in row.items():
                    kl = k.lower()
                    if "return" in kl:
                        try: ret_val = float(v.replace("%","").strip())
                        except ValueError: pass
                    if "sharpe" in kl:
                        try: sharpe_val = float(v.strip())
                        except ValueError: pass
                if name:
                    results[name] = {"return_pct": ret_val, "sharpe": sharpe_val}
        log.info(f"  alpha_arena: {len(results)} models")
    except Exception as e:
        log.error(f"  Alpha Arena error: {e}")
    return results


def scrape_financearena() -> dict:
    results = {}
    try:
        log.info("Scraping FinanceArena...")
        html = playwright_get("https://financearena.ai/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "elo" in text.lower() and ("model" in text.lower() or "qa" in text.lower()):
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            if name:
                                results[name] = {
                                    "qa_pct": e.get("qa_pct") or e.get("accuracy"),
                                    "elo":    e.get("elo") or e.get("rating"),
                                }
                        if results:
                            break
                except Exception:
                    pass
        if not results:
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
                    continue
                name = vals[0]
                qa_val, elo_val = None, None
                for k, v in row.items():
                    kl = k.lower()
                    if "qa" in kl or "accuracy" in kl:
                        try: qa_val = float(v.replace("%","").strip())
                        except ValueError: pass
                    if "elo" in kl or "rating" in kl:
                        try: elo_val = float(v.replace(",","").strip())
                        except ValueError: pass
                if name:
                    results[name] = {"qa_pct": qa_val, "elo": elo_val}
        log.info(f"  financearena: {len(results)} models")
    except Exception as e:
        log.error(f"  FinanceArena error: {e}")
    return results


# == SCORING

def normalize(models: list, raw_key: str) -> dict:
    vals = {m["name"]: (m["raw_data"].get(raw_key) or 0.0) for m in models}
    if raw_key in LOWER_IS_BETTER:
        non_zero = {k: v for k, v in vals.items() if v > 0}
        if not non_zero:
            return {k: 0.0 for k in vals}
        worst = max(non_zero.values())
        return {k: round((1 - v / worst) * 100 if v > 0 else 0.0, 4)
                for k, v in vals.items()}
    else:
        top = max(vals.values(), default=0.0)
        if top == 0.0:
            return {k: 0.0 for k in vals}
        return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def _avg_notnull(vals: list):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def calc_pillar_scores(model: dict) -> dict:
    rd = model["raw_data"]
    return {
        "forecasting":         _avg_notnull([rd.get("forecastbench_baseline_brier"),
                                              rd.get("forecastbench_tournament_brier")]),
        "trading":             _avg_notnull([rd.get("rallies_return_pct"),
                                              rd.get("alpha_arena_return_pct")]),
        "calibration":         rd.get("forecastbench_calibration"),
        "financial_reasoning": _avg_notnull([rd.get("financearena_qa_pct"),
                                              rd.get("financearena_elo")]),
        "market_intelligence": _avg_notnull([rd.get("alpha_arena_sharpe"),
                                              rd.get("rallies_win_rate")]),
    }


def count_nonnull_pillars(model: dict) -> int:
    return sum(1 for v in model.get("pillar_scores", {}).values() if v is not None)


def calculate_composite(model_name: str, normalized: dict) -> float:
    total = 0.0
    for mkey, weight in WEIGHTS.items():
        total += normalized.get(mkey, {}).get(model_name, 0.0) * weight
    return round(total, 2)


def generate_checksum(data: dict) -> str:
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(
        f"{s:.1f}" if s is not None else "null"
        for m in data["models"] for s in m["scores"]
    )
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def match_name(scraped: str, existing: list) -> str:
    s = scraped.lower().strip()
    for name in existing:
        if name.lower() == s: return name
    for name in existing:
        n = name.lower()
        if s in n or n in s: return name
    s_tok = set(s.replace("-"," ").replace("_"," ").split())
    for name in existing:
        n_tok = set(name.lower().replace("-"," ").replace("_"," ").split())
        if len(s_tok & n_tok) >= 2: return name
    return None


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "trf-data.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit."); return True
            log.error(f"Commit failed: {r.stderr}"); return False
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        log.info("Pushed")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}"); return False


# == MAIN
def main():
    if TEST_TELEGRAM:
        notify("Agent TRFcast online. Telegram works!")
        print("Telegram test sent."); return

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(f"Agent TRFcast | {TODAY} | {mode}")
    notify(f"Agent TRFcast starting | {TODAY} | {mode} | 4 sources -> trf-data.json")

    if not DATA_FILE.exists():
        msg = f"trf-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"ERROR: {msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]

    if TODAY in dates:
        date_is_new = False
        today_idx = dates.index(TODAY)
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1

    fb_data = scrape_forecastbench()
    rallies = scrape_rallies()
    alpha   = scrape_alpha_arena()
    finance = scrape_financearena()

    for scraped_name, vals in fb_data.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["forecastbench_baseline_brier"]   = vals.get("baseline_brier")
            m["raw_data"]["forecastbench_tournament_brier"] = vals.get("tournament_brier")
            m["raw_data"]["forecastbench_calibration"]      = vals.get("calibration")

    for scraped_name, vals in rallies.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["rallies_return_pct"] = vals.get("return_pct")
            m["raw_data"]["rallies_win_rate"]   = vals.get("win_rate")

    for scraped_name, vals in alpha.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["alpha_arena_return_pct"] = vals.get("return_pct")
            m["raw_data"]["alpha_arena_sharpe"]     = vals.get("sharpe")

    for scraped_name, vals in finance.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["financearena_qa_pct"] = vals.get("qa_pct")
            m["raw_data"]["financearena_elo"]    = vals.get("elo")

    for model in models:
        model["pillar_scores"] = calc_pillar_scores(model)
        model["source_count"]  = count_nonnull_pillars(model)

    normalized = {}
    for mkey, raw_field in RAW_KEYS.items():
        normalized[mkey] = normalize(models, raw_field)

    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    for model in models:
        sc = calculate_composite(model["name"], normalized)
        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(sc)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = sc
            else:
                model["scores"].append(sc)

    qualified    = [m for m in models if m["source_count"] >= QUALIFICATION_MIN]
    disqualified = [m for m in models if m["source_count"] <  QUALIFICATION_MIN]
    ranked       = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5 = "\n".join(f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
                      for m in ranked[:5])
    notify(f"TRFcast Top 5 - {TODAY}\n{top5}")

    data["checksum"] = generate_checksum(data)

    if DRY_RUN:
        notify("DRY RUN complete. Nothing written."); return

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    ok = git_push(f"TRFcast daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"TRFcast done! {TODAY} | {len(qualified)} models | trainingrun.ai/trfcast")
    else:
        notify(f"JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
