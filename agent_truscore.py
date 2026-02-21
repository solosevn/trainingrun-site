#!/usr/bin/env python3
"""
agent_truscore.py - TRUscore Daily Scraper (Truth & Neutrality)
trainingrun.ai | solosevn/trainingrun-site
Bible: TRUscore V1.1 (Feb 2026)

7 sources across 4 pillars:
  1. SimpleQA          kaggle.com              Factuality (Correct %)
  2. NewsGuard         newsguardtech.com       Misinformation resistance
  3. TrackingAI.org    trackingai.org          Political neutrality
  4. Anthropic Paired  anthropic.com/research  Even-handedness
  5. Vectara           huggingface.co/spaces   Hallucination rate
  6. AA Omniscience    artificialanalysis.ai   Factual recall
  7. SimpleQA Calib.   kaggle.com              Not-attempted % (calibration)

Qualification: 5 of 7 sources minimum.

Usage:
  python3 agent_truscore.py
  python3 agent_truscore.py --dry-run
  python3 agent_truscore.py --test-telegram

Env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, REPO_PATH
"""

import os, sys, json, hashlib, subprocess, asyncio, logging, re
from datetime import date
from pathlib import Path

for pkg, hint in [
    ("playwright", "pip3 install playwright && python3 -m playwright install chromium"),
    ("bs4",        "pip3 install beautifulsoup4"),
    ("telegram",   "pip3 install python-telegram-bot"),
]:
    try: __import__(pkg)
    except ImportError: sys.exit(f"Missing: {hint}")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from telegram import Bot

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("truscore")

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "truscore-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

WEIGHTS = {
    "factuality":     0.30,
    "neutrality":     0.25,
    "hallucination":  0.25,
    "calibration":    0.20,
}

RAW_KEYS = {
    "factuality":    "simpleqa_correct_pct",
    "neutrality":    "trackingai_neutrality",
    "hallucination": "vectara_halluc_inv",
    "calibration":   "simpleqa_not_attempted_pct",
}

SOURCE_FIELDS = [
    "simpleqa_correct_pct",
    "newsguard_score",
    "trackingai_neutrality",
    "anthropic_paired_score",
    "vectara_halluc_inv",
    "aa_omniscience",
    "simpleqa_not_attempted_pct",
]

QUALIFICATION_MIN = 5


def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text}"); return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try: asyncio.run(_send())
    except Exception as e: log.warning(f"Telegram: {e}")


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


def parse_table(html: str, name_hints: list, score_hints: list) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2: continue
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th","td"])]
        nc = next((i for i, h in enumerate(headers) if any(kw in h for kw in name_hints)), 0)
        sc = next((i for i, h in enumerate(headers) if any(kw in h for kw in score_hints)), 1)
        result = {}
        for row in rows[1:]:
            cells = row.find_all(["td","th"])
            if len(cells) <= max(nc, sc): continue
            name = cells[nc].get_text(strip=True)
            val  = cells[sc].get_text(strip=True).replace("%","").replace(",","").strip()
            try:
                v = float(val)
                if name: result[name] = v
            except ValueError: pass
        if result: return result
    return {}


# == SCRAPERS

def scrape_simpleqa() -> dict:
    results = {}
    try:
        log.info("Scraping SimpleQA...")
        urls = [
            "https://www.kaggle.com/code/jhoward/simpleqa-leaderboard",
            "https://simple-bench.com/",
        ]
        for url in urls:
            try:
                html = playwright_get(url, wait_ms=8000)
                soup = BeautifulSoup(html, "html.parser")
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    if len(rows) < 2: continue
                    headers = [h.get_text(strip=True).lower()
                               for h in rows[0].find_all(["th","td"])]
                    nc = next((i for i, h in enumerate(headers)
                               if "model" in h or "name" in h), 0)
                    correct_col = next((i for i, h in enumerate(headers)
                                        if "correct" in h), None)
                    notatt_col  = next((i for i, h in enumerate(headers)
                                        if "not" in h and "attempt" in h), None)
                    for row in rows[1:]:
                        cells = row.find_all(["td","th"])
                        if not cells: continue
                        name = cells[nc].get_text(strip=True)
                        def _v(col):
                            if col is None or col >= len(cells): return None
                            try: return float(cells[col].get_text(strip=True)
                                              .replace("%","").strip())
                            except ValueError: return None
                        correct = _v(correct_col)
                        notatt  = _v(notatt_col)
                        if name:
                            results[name] = {"correct_pct": correct,
                                             "not_attempted_pct": notatt}
                    if results: break
                if results: break
            except Exception: continue
        log.info(f"  simpleqa: {len(results)} models")
    except Exception as e:
        log.error(f"  SimpleQA error: {e}")
    return results


def scrape_newsguard() -> dict:
    scores = {}
    try:
        log.info("Scraping NewsGuard...")
        html = playwright_get("https://www.newsguardtech.com/misinformation-monitor/", wait_ms=8000)
        scores = parse_table(html,
            name_hints=["model","chatbot","ai"],
            score_hints=["score","rate","%"])
        log.info(f"  newsguard: {len(scores)} models")
    except Exception as e:
        log.error(f"  NewsGuard error: {e}")
    return scores


def scrape_trackingai() -> dict:
    scores = {}
    try:
        log.info("Scraping TrackingAI...")
        html = playwright_get("https://trackingai.org/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "model" in text.lower() and ("bias" in text.lower() or "neutral" in text.lower()):
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name  = e.get("model") or e.get("name", "")
                            score = e.get("neutrality") or e.get("score")
                            if name and score is not None:
                                scores[name] = float(score)
                        if scores: break
                except Exception: pass
        if not scores:
            scores = parse_table(html,
                name_hints=["model","name","ai"],
                score_hints=["neutral","score","bias"])
        log.info(f"  trackingai: {len(scores)} models")
    except Exception as e:
        log.error(f"  TrackingAI error: {e}")
    return scores


def scrape_anthropic_paired() -> dict:
    scores = {}
    try:
        log.info("Scraping Anthropic Paired Prompts...")
        url = "https://www.anthropic.com/research/evaluating-ai-systems-for-bias"
        html = playwright_get(url, wait_ms=6000)
        scores = parse_table(html,
            name_hints=["model","name"],
            score_hints=["score","evenhanded","neutral","%"])
        log.info(f"  anthropic_paired: {len(scores)} models")
    except Exception as e:
        log.error(f"  Anthropic Paired error: {e}")
    return scores


def scrape_vectara() -> dict:
    scores = {}
    try:
        log.info("Scraping Vectara Hallucination Leaderboard...")
        url = "https://huggingface.co/spaces/vectara/leaderboard"
        html = playwright_get(url, wait_ms=10000)
        scores = parse_table(html,
            name_hints=["model","name"],
            score_hints=["hallucin","rate","%","score"])
        log.info(f"  vectara: {len(scores)} models")
    except Exception as e:
        log.error(f"  Vectara error: {e}")
    return scores


def scrape_aa_omniscience() -> dict:
    scores = {}
    try:
        log.info("Scraping AA Omniscience...")
        html = playwright_get("https://artificialanalysis.ai/", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "omniscience" in text.lower() or "factual" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            idx  = e.get("omniscience") or e.get("factual_index")
                            if name and idx is not None:
                                scores[name] = float(idx)
                        if scores: break
                except Exception: pass
        if not scores:
            scores = parse_table(html,
                name_hints=["model","name"],
                score_hints=["omniscience","factual","knowledge"])
        log.info(f"  aa_omniscience: {len(scores)} models")
    except Exception as e:
        log.error(f"  AA Omniscience error: {e}")
    return scores


# == SCORING
def normalize(models: list, raw_key: str) -> dict:
    vals = {m["name"]: (m["raw_data"].get(raw_key) or 0.0) for m in models}
    top = max(vals.values(), default=0.0)
    if top == 0.0: return {k: 0.0 for k in vals}
    return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def calculate_composite(model_name: str, normalized: dict) -> float:
    return round(sum(normalized.get(mkey, {}).get(model_name, 0.0) * w
                     for mkey, w in WEIGHTS.items()), 2)


def generate_checksum(data: dict) -> str:
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(f"{s:.1f}" if s is not None else "null"
                      for m in data["models"] for s in m["scores"])
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
        subprocess.run(["git", "add", "truscore-data.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit."); return True
            log.error(f"Commit: {r.stderr}"); return False
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}"); return False


# == MAIN
def main():
    if TEST_TELEGRAM:
        notify("Agent TRUscore online."); print("Telegram OK."); return

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(f"Agent TRUscore | {TODAY} | {mode}")
    notify(f"Agent TRUscore starting | {TODAY} | {mode} | 7 sources -> truscore-data.json")

    if not DATA_FILE.exists():
        msg = f"truscore-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"ERROR: {msg}"); return

    with open(DATA_FILE) as f: data = json.load(f)
    models = data["models"]
    names  = [m["name"] for m in models]

    if TODAY in data["dates"]:
        date_is_new = False; today_idx = data["dates"].index(TODAY)
    else:
        date_is_new = True; data["dates"].append(TODAY)
        today_idx = len(data["dates"]) - 1

    notify(f"{len(models)} models | {data['dates'][0]} to {data['dates'][-1]}")

    simpleqa_data = scrape_simpleqa()
    newsguard     = scrape_newsguard()
    trackingai    = scrape_trackingai()
    paired        = scrape_anthropic_paired()
    vectara       = scrape_vectara()
    aa_omni       = scrape_aa_omniscience()

    for scraped_name, vals in simpleqa_data.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["simpleqa_correct_pct"]       = vals.get("correct_pct")
            m["raw_data"]["simpleqa_not_attempted_pct"] = vals.get("not_attempted_pct")

    for src_dict, field in [
        (newsguard,  "newsguard_score"),
        (trackingai, "trackingai_neutrality"),
        (paired,     "anthropic_paired_score"),
        (aa_omni,    "aa_omniscience"),
    ]:
        for scraped_name, val in src_dict.items():
            canon = match_name(scraped_name, names)
            if canon:
                m = next(x for x in models if x["name"] == canon)
                m["raw_data"][field] = val

    for scraped_name, halluc_rate in vectara.items():
        canon = match_name(scraped_name, names)
        if canon:
            m = next(x for x in models if x["name"] == canon)
            m["raw_data"]["vectara_halluc_inv"] = max(0.0, 100.0 - halluc_rate)

    for model in models:
        model["source_count"] = sum(
            1 for f in SOURCE_FIELDS if model["raw_data"].get(f) is not None)

    normalized = {mkey: normalize(models, rf) for mkey, rf in RAW_KEYS.items()}

    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    for model in models:
        sc = calculate_composite(model["name"], normalized)
        while len(model["scores"]) < today_idx: model["scores"].append(None)
        if date_is_new: model["scores"].append(sc)
        elif today_idx < len(model["scores"]): model["scores"][today_idx] = sc
        else: model["scores"].append(sc)

    qualified = [m for m in models if m["source_count"] >= QUALIFICATION_MIN]
    ranked    = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1): m["rank"] = rank

    top5 = "\n".join(f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
                      for m in ranked[:5])
    notify(f"TRUscore Top 5 - {TODAY}\n{top5}\n\nQualified: {len(qualified)}")

    data["checksum"] = generate_checksum(data)

    if DRY_RUN:
        notify("DRY RUN - nothing written."); return

    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

    ok = git_push(f"TRUscore daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"TRUscore done! {TODAY} | {len(qualified)} models")
    else:
        notify(f"JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
