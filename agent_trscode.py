#!/usr/bin/env python3
"""
agent_trscode.py - TRScode Daily Scraper
trainingrun.ai | solosevn/trainingrun-site
Bible: TRScode V1.0 (Feb 14, 2026)

8 sources scraped:
  1. SWE-bench Verified   swebench.com                    17%
  2. SWE-rebench          swe-rebench.com                 13%
  3. LiveCodeBench        livecodebench.github.io         15%
  4. BigCodeBench         bigcode-bench.github.io         10%
  5. Terminal-Bench Hard  tbench.ai                       12%
  6. SWE-bench Pro        scale.com/leaderboard/...        8%
  7. SciCode              scicode-bench.github.io         15%
  8. Chatbot Arena Code   lmarena.ai (code filter)        10%

Qualification: 2+ pillars with non-null scores.
Scoring: Option B - null sub-metrics contribute 0, not normalized away.

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
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re
from datetime import date
from pathlib import Path

# -- dependency guard
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

# -- logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("trscode")

# == CONFIG
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trscode-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# -- TRScode Bible V1.0 weights
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

QUALIFICATION_MIN_PILLARS = 2

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
def playwright_get(url: str, wait_ms: int = 5000) -> str:
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

def scrape_swebench_verified() -> dict:
    scores = {}
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
        log.info(f"  swebench_verified: {len(scores)} models")
    except Exception as e:
        log.error(f"  SWE-bench error: {e}")
    return scores


def scrape_swe_rebench() -> dict:
    scores = {}
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
        log.info(f"  swe_rebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  SWE-rebench error: {e}")
    return scores


def scrape_livecodebench() -> dict:
    scores = {}
    try:
        log.info("Scraping LiveCodeBench...")
        html = playwright_get("https://livecodebench.github.io/leaderboard.html", wait_ms=6000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
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
        log.info(f"  livecodebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  LiveCodeBench error: {e}")
    return scores


def scrape_bigcodebench() -> dict:
    scores = {}
    try:
        log.info("Scraping BigCodeBench...")
        html = playwright_get("https://bigcode-bench.github.io/", wait_ms=6000)
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
        log.info(f"  bigcodebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  BigCodeBench error: {e}")
    return scores


def scrape_terminal_bench() -> dict:
    scores = {}
    try:
        log.info("Scraping Terminal-Bench Hard...")
        html = playwright_get("https://tbench.ai/", wait_ms=5000)
        rows = parse_first_table(html)
        if rows:
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
                    continue
                name = vals[0]
                hard_val = None
                for k, v in row.items():
                    if "hard" in k.lower():
                        hard_val = v
                        break
                if hard_val is None:
                    hard_val = vals[1]
                clean = hard_val.replace("%", "").strip()
                try:
                    pct = float(clean)
                    if name and 0 <= pct <= 100:
                        scores[name] = pct
                except ValueError:
                    pass
        else:
            match = re.search(r'window.__datas*=s*({.*?});', html, re.DOTALL)
            if match:
                try:
                    embedded = json.loads(match.group(1))
                    for entry in embedded.get("models", []):
                        name  = entry.get("name", "")
                        score = entry.get("hard_pct") or entry.get("score")
                        if name and score is not None:
                            scores[name] = float(score)
                except Exception:
                    pass
        log.info(f"  terminal_bench_hard: {len(scores)} models")
    except Exception as e:
        log.error(f"  Terminal-Bench error: {e}")
    return scores


def scrape_swebench_pro() -> dict:
    scores = {}
    try:
        log.info("Scraping SWE-bench Pro...")
        url = "https://scale.com/leaderboard/swe_bench_pro_public"
        html = playwright_get(url, wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and ("models" in script.string or "leaderboard" in script.string):
                try:
                    m = re.search(r'{.*"models".*}', script.string, re.DOTALL)
                    if m:
                        data = json.loads(m.group(0))
                        for entry in data.get("models", []):
                            name  = entry.get("name") or entry.get("model", "")
                            score = entry.get("score") or entry.get("pass_rate")
                            if name and score is not None:
                                scores[name] = float(score) * (100 if float(score) <= 1 else 1)
                        if scores:
                            break
                except Exception:
                    pass
        if not scores:
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
        log.info(f"  swebench_pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  SWE-bench Pro error: {e}")
    return scores


def scrape_scicode() -> dict:
    scores = {}
    try:
        log.info("Scraping SciCode...")
        html = playwright_get("https://scicode-bench.github.io/", wait_ms=5000)
        rows = parse_first_table(html)
        for row in rows:
            vals = list(row.values())
            if len(vals) < 2:
                continue
            name = vals[0]
            for v in vals[1:]:
                clean = v.replace("%", "").strip()
                try:
                    val = float(clean)
                    pct = val * 100 if val <= 1.0 else val
                    if name and 0 <= pct <= 100:
                        scores[name] = round(pct, 2)
                        break
                except ValueError:
                    pass
        log.info(f"  scicode: {len(scores)} models")
    except Exception as e:
        log.error(f"  SciCode error: {e}")
    return scores


def scrape_arena_code() -> dict:
    scores = {}
    try:
        log.info("Scraping Chatbot Arena Code...")
        url = "https://lmarena.ai/?leaderboard=coding"
        html = playwright_get(url, wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            if script.string and "elo" in script.string.lower():
                try:
                    m = re.search(r'[(s*{.*?"model".*?}[s,]*)+]',
                                  script.string, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(0).lstrip("["))
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            elo  = e.get("elo") or e.get("score")
                            if name and elo:
                                scores[name] = float(elo)
                        if scores:
                            break
                except Exception:
                    pass
        if not scores:
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) < 2:
                    continue
                name = vals[0]
                elo_col = None
                for k, v in row.items():
                    if "elo" in k.lower() or "rating" in k.lower():
                        elo_col = v
                        break
                raw = elo_col or vals[1]
                clean = raw.replace(",", "").strip()
                try:
                    scores[name] = float(clean)
                except ValueError:
                    pass
        log.info(f"  arena_code_elo: {len(scores)} models")
    except Exception as e:
        log.error(f"  Arena Code error: {e}")
    return scores


# == SCORING ENGINE

def normalize_across_models(models: list, raw_key: str) -> dict:
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
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(
        f"{s:.1f}" if s is not None else "null"
        for m in data["models"] for s in m["scores"]
    )
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def match_name(scraped: str, existing: list) -> str:
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
                 duration_sec: int, error=None) -> None:
    """Update status.json with this agent's latest run info."""
    status_file = REPO_PATH / "status.json"
    try:
        if status_file.exists():
            with open(status_file) as fj: sdata = __import__("json").load(fj)
        else:
            sdata = {"last_updated": TODAY, "agents": {}}
        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        top5 = []
        for m in ranked[:5]:
            sc = m["scores"][-1] if m["scores"] else None
            if sc is not None: top5.append({"rank": m["rank"], "name": m["name"], "score": sc})
        sources_hit = sum(1 for s in source_summary if ": 0 matched" not in s and "0 scraped" not in s)
        sdata["last_updated"] = now_iso
        sdata["agents"]["trscode"] = {
            "name": "TRScode", "label": "Coding Leaderboard", "emoji": "\U0001f4bb",
            "enabled": True, "last_run": now_iso, "last_run_date": TODAY,
            "status": status, "duration_seconds": duration_sec,
            "sources_total": 8, "sources_hit": sources_hit,
            "models_qualified": len(ranked),
            "top_model": ranked[0]["name"] if ranked else None,
            "top_score": (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5": top5, "leaderboard_url": "/trscode.html",
            "next_run": _next_day() + "T05:00:00", "error": error,
        }
        with open(status_file, "w") as fj: __import__("json").dump(sdata, fj, indent=2)
        log.info("status.json updated")
    except Exception as e: log.warning(f"Could not write status.json: {e}")


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
                log.info("Nothing to commit.")
                return True
            log.error(f"Commit failed: {r.stderr}")
            return False
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        log.info("Pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}")
        return False


# == MAIN

def main():
    import time as _t; main._s = _t.time()
    if TEST_TELEGRAM:
        notify("Agent TRScode online. Telegram works!")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(f"Agent TRScode | {TODAY} | {mode}")
    notify(f"Agent TRScode starting | {TODAY} | {mode} | 8 sources -> trscode-data.json")

    if not DATA_FILE.exists():
        msg = f"trscode-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"ERROR: {msg}"); return

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    names  = [m["name"] for m in models]
    dates  = data["dates"]
    notify(f"Loaded. Models: {len(models)} | Dates: {dates[0]} to {dates[-1]}")

    if TODAY in dates:
        date_is_new = False
        today_idx   = dates.index(TODAY)
    else:
        date_is_new = True
        data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1

    scrapers = {
        "swebench_verified_pct":  scrape_swebench_verified,
        "swe_rebench_pass1":      scrape_swe_rebench,
        "livecodebench_pct":      scrape_livecodebench,
        "bigcodebench_pct":       scrape_bigcodebench,
        "terminalbench_hard_pct": scrape_terminal_bench,
        "swebench_pro_pct":       scrape_swebench_pro,
        "scicode_pct":            scrape_scicode,
        "arena_code_elo":         scrape_arena_code,
    }

    all_results   = {}
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
        source_summary.append(f"{raw_field}: {len(results)} scraped, {matched} matched")

    notify("Scraping complete\n" + "\n".join(source_summary))

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

    qualified    = [m for m in models if m.get("source_count", 0) >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if m.get("source_count", 0) < QUALIFICATION_MIN_PILLARS]
    if disqualified:
        log.info(f"Disqualified: {[m['name'] for m in disqualified]}")

    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5 = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"TRScode Top 5 - {TODAY}\n{top5}")

    data["checksum"] = generate_checksum(data)

    if DRY_RUN:
        notify(f"DRY RUN complete. Would score {len(qualified)} models. Nothing written.")
        log.info("Dry run complete. Nothing written.")
        return

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    import time as _t; duration = int(_t.time() - getattr(main, "_s", _t.time()))
    write_status("success", ranked, source_summary, duration)

        ok = git_push(f"TRScode daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"TRScode done! {TODAY} | {len(qualified)} models | trainingrun.ai/trscode")
    else:
        notify(f"JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
