#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
  AGENT TRSCODE — TRScode Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRScode V1.0 (Feb 14, 2026)
════════════════════════════════════════════════════════════════════
  8 sources scraped:
    1. SWE-bench Verified   swebench.com                    17%
    2. SWE-rebench          swe-rebench.com                 13%
    3. LiveCodeBench        livecodebench.github.io         15%
    4. BigCodeBench         bigcode-bench.github.io         10%
    5. Terminal-Bench Hard  tbench.ai                       12%
    6. SWE-bench Pro        scale.com/leaderboard/...        8%
    7. SciCode              scicode-bench.github.io         15%
    8. Chatbot Arena Code   arena.ai/leaderboard/code       10%

  Qualification: 2+ pillars with non-null scores.
  Scoring: Option B — null sub-metrics contribute 0, not normalized away.

  Usage:
    python3 agent_trscode.py                  # live run
    python3 agent_trscode.py --dry-run        # scrape + calculate, no push
    python3 agent_trscode.py --test-telegram  # test Telegram connection only

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
log = logging.getLogger("trscode")

# ══ CONFIG ════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trscode-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ── TRScode Bible V1.0 weights ────────────────────────────────────
WEIGHTS = {
    "swebench_verified":   0.17,
    "swe_rebench":         0.13,
    "livecodebench":       0.15,
    "bigcodebench":        0.10,
    "terminal_bench_hard": 0.12,
    "swebench_pro":        0.08,
    "scicode":             0.15,
    "arena_code_elo":      0.10,
}

# Maps weight keys → raw_data field names in trscode-data.json
RAW_KEYS = {
    "swebench_verified":   "swebench_verified_pct",
    "swe_rebench":         "swe_rebench_pass1",
    "livecodebench":       "livecodebench_pct",
    "bigcodebench":        "bigcodebench_pct",
    "terminal_bench_hard": "terminalbench_hard_pct",
    "swebench_pro":        "swebench_pro_pct",
    "scicode":             "scicode_pct",
    "arena_code_elo":      "arena_code_elo",
}

QUALIFICATION_MIN_PILLARS = 2   # Bible: 2-pillar minimum

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
        page.goto(url, wait_until="networkidle", timeout=90_000)
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

def scrape_swebench_verified() -> dict[str, float]:
    """swebench.com — verified split leaderboard. Returns {model: pct_resolved}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench Verified...")
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


def scrape_swe_rebench() -> dict[str, float]:
    """swe-rebench.com — harder verified split. Returns {model: pass@1_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-rebench...")
        html = playwright_get("https://swe-rebench.com/", wait_ms=5000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    pct = float(clean)
                    if 0 <= pct <= 100:
                        scores[name] = pct
                        break
                except ValueError:
                    pass
        log.info(f"  ✅ SWE-rebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SWE-rebench: {e}")
    return scores


def scrape_livecodebench() -> dict[str, float]:
    """livecodebench.github.io — code generation leaderboard."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping LiveCodeBench...")
        html = playwright_get(
            "https://livecodebench.github.io/leaderboard.html", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            log.warning("  No table found on LiveCodeBench")
            return scores
        target = max(tables, key=lambda t: len(t.find_all("tr")))
        rows = target.find_all("tr")
        if len(rows) < 2:
            return scores
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        score_col = 1
        for i, h in enumerate(headers):
            if any(kw in h.lower() for kw in ["overall", "pass@1", "score"]):
                score_col = i
                break
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= score_col:
                continue
            name = cells[0].get_text(strip=True)
            val  = cells[score_col].get_text(strip=True).replace("%", "").strip()
            try:
                pct = float(val)
                if name and 0 <= pct <= 100:
                    scores[name] = pct
            except ValueError:
                pass
        log.info(f"  ✅ LiveCodeBench: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ LiveCodeBench: {e}")
    return scores


def scrape_bigcodebench() -> dict[str, float]:
    """bigcode-bench.github.io — function calling + instruction following."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping BigCodeBench...")
        html = playwright_get(
            "https://bigcode-bench.github.io/", wait_ms=6000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    pct = float(clean)
                    if 0 <= pct <= 100:
                        scores[name] = pct
                        break
                except ValueError:
                    pass
        log.info(f"  ✅ BigCodeBench: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ BigCodeBench: {e}")
    return scores


def scrape_terminal_bench() -> dict[str, float]:
    """tbench.ai — Terminal-Bench Hard subset. Returns {model: accuracy_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Terminal-Bench Hard...")
        html = playwright_get("https://tbench.ai/leaderboard/terminal-bench/2.0", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            model_col = next((i for i, h in enumerate(headers) if h == "model"), None)
            acc_col   = next((i for i, h in enumerate(headers)
                              if "accuracy" in h or "score" in h), None)
            if model_col is None:
                model_col = 2
            if acc_col is None:
                acc_col = 6
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(model_col, acc_col):
                    continue
                name = cells[model_col].get_text(strip=True)
                val  = cells[acc_col].get_text(strip=True)
                val = re.split(r'[±%]', val)[0].strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        if name not in scores or pct > scores[name]:
                            scores[name] = pct
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  ✅ Terminal-Bench Hard: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Terminal-Bench: {e}")
    return scores


def scrape_swebench_pro() -> dict[str, float]:
    """scale.com/leaderboard/swe_bench_pro_public — harder SWE-bench variant."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench Pro (Scale AI)...")
        url = "https://scale.com/leaderboard/swe_bench_pro_public"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")
        next_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_tag and next_tag.string:
            try:
                nd  = json.loads(next_tag.string)
                raw = json.dumps(nd)
                pairs = re.findall(
                    r'"(?:model_name|name|model)"\s*:\s*"([^"]{3,80})"'
                    r'(?:(?!"(?:model_name|name|model)").){0,300}'
                    r'"(?:score|pass_rate|resolved_pct|accuracy)"\s*:\s*([\d.]+)',
                    raw, re.DOTALL
                )
                for name, score in pairs:
                    try:
                        val = float(score)
                        val = val * 100 if val <= 1.0 else val
                        if 0 < val <= 100:
                            scores[name] = round(val, 2)
                    except ValueError:
                        pass
            except Exception:
                pass
        if not scores:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    for cell in cells[1:]:
                        raw_val = cell.get_text(strip=True)
                        clean = re.split(r'[±%]', raw_val)[0].strip()
                        try:
                            val = float(clean)
                            val = val * 100 if val <= 1.0 else val
                            if 0 < val <= 100:
                                scores[name] = round(val, 2)
                                break
                        except ValueError:
                            pass
                if scores:
                    break
        log.info(f"  ✅ SWE-bench Pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SWE-bench Pro: {e}")
    return scores


def scrape_scicode() -> dict[str, float]:
    """scicode-bench.github.io — scientific coding. Returns {model: main_resolve_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SciCode...")
        html = playwright_get("https://scicode-bench.github.io/leaderboard/", wait_ms=5000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h), 0)
            main_col = next((i for i, h in enumerate(headers) if "main" in h), None)
            if main_col is None:
                main_col = 1
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, main_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                val  = cells[main_col].get_text(strip=True).replace("%", "").strip()
                try:
                    pct = float(val)
                    if name and 0 <= pct <= 100:
                        scores[name] = round(pct, 2)
                except ValueError:
                    pass
            if scores:
                break
        log.info(f"  ✅ SciCode: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SciCode: {e}")
    return scores


def scrape_arena_code() -> dict[str, float]:
    """arena.ai/leaderboard/code — Code ELO. Returns {model: elo_score}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Chatbot Arena Code leaderboard...")
        url = "https://arena.ai/leaderboard/code"
        html = playwright_get(url, wait_ms=12000)
        soup = BeautifulSoup(html, "html.parser")
        next_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_tag and next_tag.string:
            try:
                nd  = json.loads(next_tag.string)
                raw = json.dumps(nd)
                pairs = re.findall(
                    r'"(?:model|name|model_name)"\s*:\s*"([^"]{2,80})"'
                    r'(?:(?!"(?:model|name|model_name)").){0,200}'
                    r'"(?:elo|score|rating|elo_rating)"\s*:\s*(\d{3,4}(?:\.\d+)?)',
                    raw, re.DOTALL
                )
                for name, elo in pairs:
                    try:
                        val = float(elo)
                        if 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
            except Exception:
                pass
        if not scores:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue
                headers = [th.get_text(strip=True).lower()
                           for th in rows[0].find_all(["th", "td"])]
                model_col = next((i for i, h in enumerate(headers)
                                  if "model" in h or "name" in h), 0)
                score_col = next((i for i, h in enumerate(headers)
                                  if "score" in h or "elo" in h or "rating" in h), 2)
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) <= max(model_col, score_col):
                        continue
                    name = cells[model_col].get_text(strip=True)
                    raw_val = cells[score_col].get_text(strip=True)
                    clean = raw_val.split()[0].replace(",", "").strip()
                    try:
                        val = float(clean)
                        if name and 900 <= val <= 2200:
                            scores[name] = val
                    except ValueError:
                        pass
                if scores:
                    break
        log.info(f"  ✅ Chatbot Arena Code: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Arena Code: {e}")
    return scores


# ══ SCORING ENGINE ══# ══ SCORING ENGINE ════════════════════════════════════════════════

def normalize_across_models(models: list, raw_key: str) -> dict[str, float]:
    """Top performer = 100. Others proportional. Null/0 → 0 (Option B)."""
    vals = {m["name"]: (m["raw_data"].get(raw_key) or 0.0) for m in models}
    top  = max(vals.values(), default=0.0)
    if top == 0.0:
        return {k: 0.0 for k in vals}
    return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def calculate_composite(model_name: str, normalized: dict) -> float:
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
        sdata["agents"]["trscode"] = {
            "name":             "TRScode",
            "label":            "Coding Leaderboard",
            "emoji":            "💻",
            "enabled":          True,
            "last_run":         now_iso,
            "last_run_date":    TODAY,
            "status":           status,
            "duration_seconds": duration_sec,
            "sources_total":    8,
            "sources_hit":      sources_hit,
            "models_qualified": len(ranked),
            "top_model":        ranked[0]["name"] if ranked else None,
            "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5":             top5,
            "leaderboard_url":  "/trscode.html",
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


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "trscode-data.json", "status.json"],
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
        notify("✅ <b>TRScode Agent online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN 🔍" if DRY_RUN else "LIVE 🚀"
    log.info(f"Agent TRScode | {TODAY} | {mode}")
    notify(f"🤖 <b>Agent TRScode starting</b>\n📅 {TODAY}\n⚙️ {mode}\n8 sources → trscode-data.json")

    if not DATA_FILE.exists():
        msg = f"trscode-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"❌ {msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"📂 Loaded. Models: {len(models)} | Dates: {dates[0]} → {dates[-1]}")

    if TODAY in dates:
        date_is_new = False
        today_idx   = dates.index(TODAY)
        notify(f"ℹ️ {TODAY} exists at index {today_idx}. Refreshing.")
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1
        notify(f"➕ New date: {TODAY} (slot {today_idx})")

    scrapers = {
        "swebench_verified_pct": scrape_swebench_verified,
        "swe_rebench_pass1":     scrape_swe_rebench,
        "livecodebench_pct":     scrape_livecodebench,
        "bigcodebench_pct":      scrape_bigcodebench,
        "terminalbench_hard_pct":scrape_terminal_bench,
        "swebench_pro_pct":      scrape_swebench_pro,
        "scicode_pct":           scrape_scicode,
        "arena_code_elo":        scrape_arena_code,
    }

    all_results  = {}
    total_matched = 0
    source_summary = []

    for raw_field, scraper_fn in scrapers.items():
        results = scraper_fn()
        all_results[raw_field] = results
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

    normalized = {}
    for mkey, raw_field in RAW_KEYS.items():
        normalized[mkey] = normalize_across_models(models, raw_field)

    for model in models:
        n  = model["name"]
        sc = calculate_composite(n, normalized)
        model["source_count"] = sum(
            1 for rf in RAW_KEYS.values()
            if model["raw_data"].get(rf) is not None
        )
        while len(model["scores"]) < today_idx:
            model["scores"].append(None)
        if date_is_new:
            model["scores"].append(sc)
        else:
            if today_idx < len(model["scores"]):
                model["scores"][today_idx] = sc
            else:
                model["scores"].append(sc)

    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    qualified = [m for m in models if m["source_count"] >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if m["source_count"] < QUALIFICATION_MIN_PILLARS]
    if disqualified:
        log.info(f"Disqualified (< {QUALIFICATION_MIN_PILLARS} pillars): "
                 f"{[m['name'] for m in disqualified]}")

    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"🏆 <b>TRScode Top 5 — {TODAY}</b>\n{top5_lines}")

    data["checksum"] = generate_checksum(data)
    log.info(f"Checksum: {data['checksum'][:20]}...")

    if DRY_RUN:
        notify(f"🔍 <b>DRY RUN complete</b>\nWould score {len(qualified)} models.\nNothing written.")
        log.info("Dry run complete. Nothing written.")
        return

    import time as _time
    _t0 = getattr(main, "_start_time", _time.time())
    duration = int(_time.time() - _t0)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Wrote {DATA_FILE.name}")

    write_status("success", ranked, source_summary, duration)

    ok = git_push(f"TRScode daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRScode done!</b>\n📅 {TODAY}\n📊 {len(qualified)} models\n🌐 → trainingrun.ai/trscode")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
