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


# ══ SCRAPERS ══════════════════════════════════════════════════════

def scrape_forecastbench() -> tuple[dict[str, float], dict[str, float]]:
    """
    ForecastBench baseline leaderboard (forecastbench.org/baseline/).
    Returns two dicts (both use the same Overall Brier score):
    - baseline Brier scores (0.0-1.0, lower is better)
    - tournament Brier scores (same source, reused for calibration)
    """
    baseline_scores = {}
    tournament_scores = {}
    try:
        log.info("Scraping ForecastBench...")
        # Table is JS-rendered -- use page.evaluate() to extract from live DOM
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
            page = ctx.new_page()
            try:
                page.goto("https://forecastbench.org/baseline/",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            try:
                page.wait_for_selector("table", timeout=30_000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            rows = page.evaluate("""() => {
                const table = document.querySelector('table');
                if (!table) return [];
                const allRows = Array.from(table.querySelectorAll('tr'));
                const headers = Array.from(allRows[0].querySelectorAll('th,td'))
                    .map(el => el.textContent.trim());
                const modelIdx = headers.indexOf('Model');
                const overallIdx = headers.indexOf('Overall (N)');
                if (modelIdx === -1) return [];
                return allRows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {
                        model: cells[modelIdx] || '',
                        overall: overallIdx >= 0 ? cells[overallIdx] || '' : ''
                    };
                }).filter(r => r.model);
            }""")
            browser.close()

        SKIP = {"Superforecaster median forecast", "Public median forecast"}
        for row in rows:
            name = row.get("model", "")
            if not name or name in SKIP:
                continue
            overall_raw = row.get("overall", "")
            if not overall_raw:
                continue
            clean = overall_raw.split(" ")[0].replace(",", "").strip()
            try:
                val = float(clean)
                if 0 < val <= 1:
                    baseline_scores[name] = val
                    tournament_scores[name] = val  # reuse for calibration pillar
            except ValueError:
                pass

        log.info(f"  ✅ ForecastBench: {len(baseline_scores)} baseline, {len(tournament_scores)} tournament")
    except Exception as e:
        log.error(f"  ❌ ForecastBench: {e}")

    return baseline_scores, tournament_scores


def scrape_rallies() -> tuple[dict[str, float], dict[str, float]]:
    """
    Rallies.ai Arena leaderboard (rallies.ai/arena). Returns two dicts:
    - return_pct: portfolio Return % (column "Return %")
    - win_rate_pct: Win Rate % (column "Win Rate")
    """
    return_scores = {}
    winrate_scores = {}
    try:
        log.info("Scraping Rallies.ai...")
        # NOTE: old URL rallies.ai/ has no table -- leaderboard is at rallies.ai/arena
        html = playwright_get("https://rallies.ai/arena", wait_ms=10000)
        rows = parse_first_table(html)

        for row in rows:
            name = row.get("Model", "")
            if not name:
                vals = list(row.values())
                name = vals[1] if len(vals) > 1 else ""  # col 0 is rank emoji
            if not name:
                continue
            # Return % -- may start with "up" or "down" or be plain number
            ret_raw = row.get("Return %", "")
            try:
                val = float(ret_raw.replace("%", "").replace("+", "").strip())
                if -1000 <= val <= 10000:
                    return_scores[name] = val
            except ValueError:
                pass
            # Win Rate
            wr_raw = row.get("Win Rate", "")
            try:
                val = float(wr_raw.replace("%", "").strip())
                if 0 <= val <= 100:
                    winrate_scores[name] = val
            except ValueError:
                pass

        log.info(f"  Rallies.ai: {len(return_scores)} returns, {len(winrate_scores)} win rates")
    except Exception as e:
        log.error(f"  Rallies.ai: {e}")

    return return_scores, winrate_scores
def scrape_alpha_arena() -> tuple[dict[str, float], dict[str, float]]:
    """
    Alpha Arena (nof1.ai/leaderboard) leaderboard. Returns two dicts:
    - return_pct: portfolio Return % (best per base model)
    - sharpe_ratio: Sharpe ratio (best per base model)
    Model names have strategy suffixes stripped: "GROK-4.20 - 3: SITUATIONAL AWARENESS" -> "GROK-4.20"
    """
    return_scores = {}
    sharpe_scores = {}
    try:
        log.info("Scraping Alpha Arena...")
        # NOTE: old URL nof1.ai/ has no table -- leaderboard is at nof1.ai/leaderboard
        html = playwright_get("https://nof1.ai/leaderboard", wait_ms=10000)
        rows = parse_first_table(html)

        for row in rows:
            raw_name = row.get("MODEL", "")
            if not raw_name:
                vals = list(row.values())
                raw_name = vals[1] if len(vals) > 1 else ""  # col 0 is rank
            if not raw_name:
                continue
            # Strip strategy suffix: "GROK-4.20 - 3: SITUATIONAL AWARENESS" -> "GROK-4.20"
            name = re.sub(r'\s*-\s*\d+:\s*.+$', '', raw_name).strip()
            if not name:
                continue
            # Return %: "+34.59%" or "-10.45%"
            ret_raw = row.get("RETURN %", "")
            try:
                val = float(ret_raw.replace("%", "").replace("+", "").strip())
                if name not in return_scores or val > return_scores[name]:
                    return_scores[name] = val
            except ValueError:
                pass
            # Sharpe ratio (can be negative)
            sharpe_raw = row.get("SHARPE", "")
            try:
                val = float(sharpe_raw.strip())
                if name not in sharpe_scores or val > sharpe_scores[name]:
                    sharpe_scores[name] = val
            except ValueError:
                pass

        log.info(f"  Alpha Arena: {len(return_scores)} returns, {len(sharpe_scores)} Sharpe")
    except Exception as e:
        log.error(f"  Alpha Arena: {e}")

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
                     and normalized[k].get(model_name, 0.0) > 0]
        if available:
            w_sum = sum(w for _, w in available)
            pillar_scores[pillar] = round(
                sum(normalized[k].get(model_name, 0.0) * (w / w_sum) for k, w in available), 2
            )
        else:
            pillar_scores[pillar] = None
    return pillar_scores


def calculate_composite(model_name: str, normalized: dict) -> float:
    """Composite score using Option A: proportional normalization over 9 sub-metrics."""
    total = 0.0
    for mkey, weight in WEIGHTS.items():
        total += normalized.get(mkey, {}).get(model_name, 0.0) * weight
    return round(total, 2)


def generate_checksum(data: dict) -> str:
    """Bible V1.0 canonical: names|...|:scores,...  with .1f formatting."""
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(
        f"{s:.1f}" if s is not None else "null"
        for m in data["models"] for s in m["scores"]
    )
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def match_name(scraped: str, existing: list[str]) -> str | None:
    s = scraped.lower().strip()
    for name in existing:
        if name.lower() == s:
            return name
    for name in existing:
        n = name.lower()
        if s in n or n in s:
            return name
    s_tok = set(s.replace("-", " ").replace("_", " ").split())
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

        sources_hit = sum(1 for s in source_summary if ", 0 matched" not in s and "0 scraped" not in s)

        sdata["last_updated"] = now_iso
        sdata["agents"]["trfcast"] = {
            "name":             "TRFcast DDP",
            "label":            "Forecast Leaderboard",
            "emoji":            "🔮",
            "enabled":          True,
            "last_run":         now_iso,
            "last_run_date":    TODAY,
            "status":           status,
            "duration_seconds": duration_sec,
            "sources_total":    4,
            "sources_hit":      sources_hit,
            "models_qualified": len(ranked),
            "top_model":        ranked[0]["name"] if ranked else None,
            "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5":             top5,
            "leaderboard_url":  "/trfcast.html",
            "next_run":         (TODAY + "T05:00:00").replace(TODAY, _next_day()),
            "error":            error,
        }

        with open(status_file, "w") as f:
            json.dump(sdata, f, indent=2)
        log.info("✅ status.json updated")
    except Exception as e:
        log.warning(f"Could not write status.json: {e}")


def _next_day() -> str:
    from datetime import datetime, timedelta
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def update_index_timestamp() -> None:
    """Rewrite var LAST_PUSH_TIME in index.html with the current local time."""
    index_file = REPO_PATH / "index.html"
    if not index_file.exists():
        log.warning("index.html not found — skipping timestamp update")
        return
    try:
        from datetime import datetime
        now = datetime.now()
        # Format as "4:16 AM CST" (no leading zero on hour)
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
            log.info(f"✅ index.html timestamp updated → {push_time}")
        else:
            log.warning("index.html: LAST_PUSH_TIME pattern not found — timestamp not updated")
    except Exception as e:
        log.warning(f"Could not update index.html timestamp: {e}")


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "trf-data.json", "status.json", "index.html"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit — data unchanged.")
                return True
            log.error(f"Commit failed:\n{r.stderr}")
            return False
        subprocess.run(["git", "push"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        log.info("✅ Pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e.stderr}")
        return False


# ══ MAIN ══════════════════════════════════════════════════════════

def main():
    import time as _time
    main._start_time = _time.time()

    if TEST_TELEGRAM:
        notify("✅ <b>TRFcast DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN 🔍" if DRY_RUN else "LIVE 🚀"
    log.info(f"TRFcast DDP | {TODAY} | {mode}")
    notify(f"🤖 <b>TRFcast DDP starting</b>\n📅 {TODAY}\n⚙️ {mode}\n4 sources → trf-data.json")

    # ── Load data ──
    if not DATA_FILE.exists():
        msg = f"trf-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"❌ {msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"📂 Loaded. Models: {len(models)} | Dates: {dates[0]} → {dates[-1]}")

    # ── Date slot ──
    if TODAY in dates:
        date_is_new = False
        today_idx   = dates.index(TODAY)
        notify(f"ℹ️ {TODAY} exists at index {today_idx}. Refreshing.")
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1
        notify(f"➕ New date: {TODAY} (slot {today_idx})")

    # ── Scrape all 4 sources (9 sub-metrics total) ──
    log.info("Scraping 4 sources...")
    
    baseline_brier, tournament_brier = scrape_forecastbench()
    rallies_returns, rallies_winrate = scrape_rallies()
    alpha_returns, alpha_sharpe = scrape_alpha_arena()
    finance_qa, finance_elo = scrape_financearena()

    # ── Merge results into models' raw_data ──
    source_summary = []
    total_matched = 0

    scrapers = {
        "forecastbench_baseline_brier": baseline_brier,
        "forecastbench_tournament_brier": tournament_brier,
        "rallies_return_pct": rallies_returns,
        "rallies_win_rate": rallies_winrate,
        "alpha_arena_return_pct": alpha_returns,
        "alpha_arena_sharpe": alpha_sharpe,
        "financearena_qa_pct": finance_qa,
        "financearena_elo": finance_elo,
    }

    for raw_field, results in scrapers.items():
        matched = 0
        for scraped_name, val in results.items():
            canonical = match_name(scraped_name, names)
            if canonical:
                m = next(x for x in models if x["name"] == canonical)
                m["raw_data"][raw_field] = val
                matched += 1
        total_matched += matched
        source_summary.append(f"{raw_field}: {len(results)} scraped, {matched} matched")
        log.info(f"  {raw_field}: {matched}/{len(results)} matched")

    notify("📊 <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # ── Normalize + score ──
    normalized = {}
    for mkey, raw_field in RAW_KEYS.items():
        inverted = mkey in INVERTED_KEYS
        normalized[mkey] = normalize_across_models(models, raw_field, inverted=inverted)

    for model in models:
        n = model["name"]
        
        # Calculate pillar scores
        model["pillar_scores"] = calculate_pillar_scores(n, normalized)
        
        # Calculate composite score
        sc = calculate_composite(n, normalized)
        
        # Count non-null pillars
        model["source_count"] = sum(
            1 for pillar_score in model["pillar_scores"].values()
            if pillar_score is not None
        )
        
        # Update scores array
        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(sc)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = sc
            else:
                model["scores"].append(sc)

    # ── Qualification filter (3+ pillars) ──
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified = [m for m in models if m["source_count"] >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if m["source_count"] < QUALIFICATION_MIN_PILLARS]
    if disqualified:
        log.info(f"Disqualified (< {QUALIFICATION_MIN_PILLARS} pillars): "
                 f"{[m['name'] for m in disqualified]}")

    # ── Update ranks ──
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"🏆 <b>TRFcast Top 5 — {TODAY}</b>\n{top5_lines}")

    # ── Checksum ──
    data["checksum"] = generate_checksum(data)
    log.info(f"Checksum: {data['checksum'][:20]}...")

    if DRY_RUN:
        notify(f"🔍 <b>DRY RUN complete</b>\nWould score {len(qualified)} models.\nNothing written.")
        log.info("Dry run complete. Nothing written.")
        return

    # ── Write + push ──
    import time as _time
    _t0 = getattr(main, "_start_time", _time.time())
    duration = int(_time.time() - _t0)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    write_status("success", ranked, source_summary, duration)
    update_index_timestamp()

    ok = git_push(f"TRFcast daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRFcast DDP done!</b>\n📅 {TODAY}\n📊 {len(qualified)} models\n🌐 → trainingrun.ai/trfcast")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
