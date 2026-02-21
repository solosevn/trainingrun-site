#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
  AGENT TRSBENCH — TRSbench Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRSbench V2.4 (Feb 21, 2026)
════════════════════════════════════════════════════════════════════
  7 sources scraped:
    1. Safety Bench        huggingface.co/spaces           0.21
    2. Reasoning (ARC)     arcprize.org/arc-agi-2          0.20
    3. Coding              swebench.com                    0.20
    4. Human Preference    lmarena.ai                      0.18
    5. Knowledge (MMLU)    huggingface.co/MMLU-Pro         0.08
    6. Efficiency          artificialanalysis.ai           0.07
    7. Usage Adoption      openrouter.ai/rankings          0.06

  Qualification: 5+ categories with non-null scores.
  Scoring: Option A — null categories excluded, available weights renormalized to 1.0.

  Usage:
    python3 agent_trsbench.py                  # live run
    python3 agent_trsbench.py --dry-run        # scrape + calculate, no push
    python3 agent_trsbench.py --test-telegram  # test Telegram connection only

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
log = logging.getLogger("trsbench")

# ══ CONFIG ════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trs-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ── TRSbench Bible V2.4 weights ───────────────────────────────────
WEIGHTS = {
    "safety":           0.21,
    "reasoning":        0.20,
    "coding":           0.20,
    "human_preference": 0.18,
    "knowledge":        0.08,
    "efficiency":       0.07,
    "usage_adoption":   0.06,
}

QUALIFICATION_MIN_CATEGORIES = 4   # Lowered 5→4: safety benchmarks lag new model releases

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


# ══ SCRAPERS ══════════════════════════════════════════════════════

def scrape_arena_overall() -> dict[str, float]:
    """lmarena.ai overall ELO ratings. Returns {model: elo_float}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Arena Overall (human preference)...")
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

        log.info(f"  ✅ Arena Overall: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Arena Overall: {e}")
    return scores


def scrape_arc_agi2() -> dict[str, float]:
    """arcprize.org/leaderboard — ARC-AGI-2 column. Returns {model: score_pct}."""
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
            # Strip parenthetical qualifiers: "Claude Opus 4.6 (120K, High)" -> "Claude Opus 4.6"
            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            # Trailing footnote markers
            name = re.sub(r'[^\x00-\x7F]+$', '', name).strip()
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
        log.info(f"  ✅ ARC-AGI-2: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ ARC-AGI-2: {e}")
    return scores


def scrape_swebench_verified() -> dict[str, float]:
    """swebench.com — verified split leaderboard. Returns {model: pct_resolved}."""
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

        log.info(f"  ✅ SWE-bench Verified: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SWE-bench: {e}")
    return scores


def scrape_mmlu_pro() -> dict[str, float]:
    """huggingface.co/spaces/TIGER-Lab/MMLU-Pro — knowledge leaderboard (via iframe)."""
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
        log.info(f"  ✅ MMLU-Pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ MMLU-Pro: {e}")
    return scores


def scrape_artificial_analysis() -> dict[str, float]:
    """artificialanalysis.ai/leaderboards/models -- efficiency (Median Tokens/s)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Artificial Analysis (efficiency)...")
        # NOTE: /leaderboard and /models have no scores; use /leaderboards/models
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
                // col indices: 0=Model, 5=Median Tokens/s
                return allRows.slice(2).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {model: cells[0] || '', speed: cells[5] || ''};
                }).filter(r => r.model && r.speed);
            }""")
            browser.close()

        for row in rows:
            name = row.get("model", "")
            # Strip quality suffix: "Claude Opus 4.6 (max)" -> "Claude Opus 4.6"
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
        log.info(f"  ✅ Artificial Analysis: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Artificial Analysis: {e}")
    return scores
def scrape_openrouter_usage() -> dict[str, float]:
    """openrouter.ai/rankings — usage adoption scores (innerText parse, no <table>)."""
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
        log.info(f"  ✅ OpenRouter Rankings: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ OpenRouter Rankings: {e}")
    return scores


def scrape_safebench() -> dict[str, float]:
    """Scale SEAL MASK leaderboard -- model honesty under pressure (safety proxy).
    Higher score = safer/more honest. source: scale.com/leaderboard/mask
    Uses playwright innerText parsing: rank lines followed by name then score."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SafeBench (safety)...")
        url = "https://scale.com/leaderboard/mask"
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
                        val = float(m.group(1))
                        if 0 < val <= 100:
                            if name not in scores or val > scores[name]:
                                scores[name] = val
                            i += 3
                            continue
                    except ValueError:
                        pass
            i += 1
        log.info(f"  \u2705 SafeBench (SEAL MASK): {len(scores)} models")
    except Exception as e:
        log.warning(f"  \u26a0\ufe0f SafeBench not available: {e}")
    return scores
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
    """Option A: null categories excluded, available weights renormalized to sum 1.0."""
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
    """Bible V2.4 canonical: names|...|:scores,...  with .1f formatting."""
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

        sources_hit = sum(1 for s in source_summary if "0 scraped" not in s and "0 matched" not in s)

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
            "sources_total":    7,
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
        subprocess.run(["git", "add", "trs-data.json", "status.json", "index.html"],
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
        notify("✅ <b>TRSbench DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN 🔍" if DRY_RUN else "LIVE 🚀"
    log.info(f"TRSbench DDP | {TODAY} | {mode}")
    notify(f"🤖 <b>TRSbench DDP starting</b>\n📅 {TODAY}\n⚙️ {mode}\n7 sources → trs-data.json")

    # ── Load data ──
    if not DATA_FILE.exists():
        msg = f"trs-data.json not found at {DATA_FILE}"
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

    # ── Scrape all 7 sources ──
    scrapers = {
        "safety":           (scrape_safebench, {}),
        "reasoning":        (scrape_arc_agi2, {}),
        "coding":           (scrape_swebench_verified, {}),
        "human_preference": (scrape_arena_overall, {}),
        "knowledge":        (scrape_mmlu_pro, {}),
        "efficiency":       (scrape_artificial_analysis, {}),
        "usage_adoption":   (scrape_openrouter_usage, {}),
    }

    all_results  = {}
    total_matched = 0
    source_summary = []

    for category, (scraper_fn, _) in scrapers.items():
        results = scraper_fn()
        all_results[category] = results
        matched = 0
        for scraped_name, val in results.items():
            canonical = match_name(scraped_name, names)
            if canonical:
                # Store in normalized dict, not raw_data (simple schema)
                # We'll normalize after all scraping
                matched += 1
        total_matched += matched
        source_summary.append(f"{category}: {len(results)} scraped, {matched} matched")
        log.info(f"  {category}: {matched}/{len(results)} matched")

    notify("📊 <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # ── Normalize + score ──
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

    # ── Qualification filter (5+ categories) ──
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified = [m for m in models if m["category_count"] >= QUALIFICATION_MIN_CATEGORIES]
    disqualified = [m for m in models if m["category_count"] < QUALIFICATION_MIN_CATEGORIES]
    if disqualified:
        log.info(f"Disqualified (< {QUALIFICATION_MIN_CATEGORIES} categories): "
                 f"{[m['name'] for m in disqualified]}")

    # ── Update ranks ──
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"🏆 <b>TRSbench Top 5 — {TODAY}</b>\n{top5_lines}")

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

    ok = git_push(f"TRSbench daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRSbench DDP done!</b>\n📅 {TODAY}\n📊 {len(qualified)} models\n🌐 → trainingrun.ai/scores")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
