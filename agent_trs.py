#!/usr/bin/env python3
"""
agent_trs.py - TRSbench Daily Scraper (Main Overall Score)
trainingrun.ai | solosevn/trainingrun-site
Bible: TRSbench V1.1 (Feb 2026)

7 sources | 7 TRS categories:
  1. Chatbot Arena      lmarena.ai                Human Preference
  2. SWE-bench Verified swebench.com              Coding
  3. ARC-AGI-2          arcprize.org/arc-agi-2    Reasoning
  4. MMLU-Pro/GPQA      various                   Knowledge
  5. Artificial Analysis artificialanalysis.ai    Efficiency
  6. OpenRouter         openrouter.ai/rankings    Usage
  7. SafeBench/NIST     safebench.org             Safety

Qualification: 5 of 7 categories minimum.

Usage:
  python3 agent_trs.py
  python3 agent_trs.py --dry-run
  python3 agent_trs.py --test-telegram

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
    try: __import__(pkg)
    except ImportError: sys.exit(f"Missing: {hint}")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from telegram import Bot

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("trs")

# == CONFIG
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "trs-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# -- TRSbench V2.4 weights (7 categories)
WEIGHTS = {
    "safety":           0.10,
    "reasoning":        0.20,
    "coding":           0.20,
    "human_preference": 0.20,
    "knowledge":        0.15,
    "efficiency":       0.10,
    "usage":            0.05,
}

RAW_KEYS = {
    "safety":           "safebench_score",
    "reasoning":        "arc_agi2_pct",
    "coding":           "swebench_pct",
    "human_preference": "arena_elo",
    "knowledge":        "mmlu_pro_pct",
    "efficiency":       "aa_efficiency_index",
    "usage":            "openrouter_rank_inv",
}

QUALIFICATION_MIN = 5


# == TELEGRAM
def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text}"); return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try: asyncio.run(_send())
    except Exception as e: log.warning(f"Telegram non-fatal: {e}")


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


def parse_table_by_headers(html: str, name_hints: list, score_hints: list) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    scores = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True).lower()
                   for th in rows[0].find_all(["th", "td"])]
        name_col  = next((i for i, h in enumerate(headers)
                          if any(kw in h for kw in name_hints)), 0)
        score_col = next((i for i, h in enumerate(headers)
                          if any(kw in h for kw in score_hints)), 1)
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_col, score_col):
                continue
            name = cells[name_col].get_text(strip=True)
            val  = cells[score_col].get_text(strip=True).replace("%","").replace(",","").strip()
            try:
                v = float(val)
                if name: scores[name] = v
            except ValueError: pass
        if scores:
            break
    return scores


# == SCRAPERS

def scrape_chatbot_arena() -> dict:
    scores = {}
    try:
        log.info("Scraping Chatbot Arena...")
        html = playwright_get("https://lmarena.ai/", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "elo" in text.lower() and "model" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            elo  = e.get("elo") or e.get("rating") or e.get("arena_score")
                            if name and elo:
                                scores[name] = float(elo)
                        if scores: break
                except Exception: pass
        if not scores:
            scores = parse_table_by_headers(html,
                name_hints=["model","name"],
                score_hints=["elo","rating","arena","score"])
        log.info(f"  arena: {len(scores)} models")
    except Exception as e:
        log.error(f"  Arena error: {e}")
    return scores


def scrape_swebench() -> dict:
    scores = {}
    try:
        log.info("Scraping SWE-bench...")
        html = playwright_get("https://www.swebench.com/", wait_ms=6000)
        scores = parse_table_by_headers(html,
            name_hints=["model","name","instance"],
            score_hints=["resolve","%","score"])
        log.info(f"  swebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  SWE-bench error: {e}")
    return scores


def scrape_arc_agi2() -> dict:
    scores = {}
    try:
        log.info("Scraping ARC-AGI-2...")
        html = playwright_get("https://arcprize.org/arc-agi-2", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "score" in text.lower() and "model" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name  = e.get("model") or e.get("name", "")
                            score = e.get("score") or e.get("pass_rate")
                            if name and score is not None:
                                v = float(score)
                                scores[name] = v * 100 if v <= 1.0 else v
                        if scores: break
                except Exception: pass
        if not scores:
            scores = parse_table_by_headers(html,
                name_hints=["model","name"],
                score_hints=["score","pass","%","accuracy"])
        log.info(f"  arc_agi2: {len(scores)} models")
    except Exception as e:
        log.error(f"  ARC-AGI-2 error: {e}")
    return scores


def scrape_mmlu_pro() -> dict:
    scores = {}
    try:
        log.info("Scraping MMLU-Pro...")
        urls = [
            "https://huggingface.co/spaces/TIGER-Lab/MMLU-Pro",
            "https://paperswithcode.com/sota/multi-task-language-understanding-on-mmlu",
        ]
        for url in urls:
            try:
                html = playwright_get(url, wait_ms=8000)
                result = parse_table_by_headers(html,
                    name_hints=["model","name"],
                    score_hints=["accuracy","score","%"])
                if result:
                    scores.update(result)
                    break
            except Exception: continue
        log.info(f"  mmlu_pro: {len(scores)} models")
    except Exception as e:
        log.error(f"  MMLU-Pro error: {e}")
    return scores


def scrape_artificial_analysis() -> dict:
    scores = {}
    try:
        log.info("Scraping Artificial Analysis...")
        html = playwright_get("https://artificialanalysis.ai/", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "efficiency" in text.lower() or "index" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for e in entries:
                            name = e.get("model") or e.get("name", "")
                            idx  = (e.get("efficiency_index") or
                                    e.get("quality_index") or e.get("index"))
                            if name and idx is not None:
                                scores[name] = float(idx)
                        if scores: break
                except Exception: pass
        if not scores:
            scores = parse_table_by_headers(html,
                name_hints=["model","name"],
                score_hints=["efficiency","index","quality"])
        log.info(f"  aa_efficiency: {len(scores)} models")
    except Exception as e:
        log.error(f"  AA error: {e}")
    return scores


def scrape_openrouter() -> dict:
    scores = {}
    rank = 1
    try:
        log.info("Scraping OpenRouter...")
        html = playwright_get("https://openrouter.ai/rankings", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "rank" in text.lower() and "model" in text.lower():
                try:
                    m = re.search(r'\[(.+?)\]', text, re.DOTALL)
                    if m:
                        entries = json.loads("[" + m.group(1) + "]")
                        for i, e in enumerate(entries, 1):
                            name = e.get("model") or e.get("id", "")
                            if name:
                                scores[name] = 1000.0 - i
                        if scores: break
                except Exception: pass
        if not scores:
            for item in soup.select("li, tr, [data-model]"):
                name = item.get_text(strip=True).split("\n")[0]
                if name and len(name) > 3:
                    scores[name] = 1000.0 - rank
                    rank += 1
                    if rank > 50: break
        log.info(f"  openrouter: {len(scores)} models")
    except Exception as e:
        log.error(f"  OpenRouter error: {e}")
    return scores


def scrape_safebench() -> dict:
    scores = {}
    try:
        log.info("Scraping SafeBench...")
        urls = ["https://safebench.org/", "https://safebench.github.io/"]
        for url in urls:
            try:
                html = playwright_get(url, wait_ms=6000)
                result = parse_table_by_headers(html,
                    name_hints=["model","name"],
                    score_hints=["safe","score","pass","%"])
                if result:
                    scores.update(result); break
            except Exception: continue
        log.info(f"  safebench: {len(scores)} models")
    except Exception as e:
        log.error(f"  SafeBench error: {e}")
    return scores


# == SCORING
def normalize(models: list, raw_key: str) -> dict:
    vals = {m["name"]: (m["raw_data"].get(raw_key) or 0.0) for m in models}
    top  = max(vals.values(), default=0.0)
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
        subprocess.run(["git", "add", "trs-data.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit."); return True
            log.error(f"Commit failed: {r.stderr}"); return False
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}"); return False


# == MAIN
def main():
    if TEST_TELEGRAM:
        notify("Agent TRSbench online."); print("Telegram OK."); return

    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log.info(f"Agent TRSbench | {TODAY} | {mode}")
    notify(f"Agent TRSbench starting | {TODAY} | {mode} | 7 sources -> trs-data.json")

    if not DATA_FILE.exists():
        msg = f"trs-data.json not found at {DATA_FILE}"
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

    scrape_map = {
        "arena_elo":           scrape_chatbot_arena,
        "swebench_pct":        scrape_swebench,
        "arc_agi2_pct":        scrape_arc_agi2,
        "mmlu_pro_pct":        scrape_mmlu_pro,
        "aa_efficiency_index": scrape_artificial_analysis,
        "openrouter_rank_inv": scrape_openrouter,
        "safebench_score":     scrape_safebench,
    }

    for raw_field, scraper_fn in scrape_map.items():
        results = scraper_fn()
        for scraped_name, val in results.items():
            canon = match_name(scraped_name, names)
            if canon:
                m = next(x for x in models if x["name"] == canon)
                m["raw_data"][raw_field] = val

    normalized = {mkey: normalize(models, rf) for mkey, rf in RAW_KEYS.items()}

    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    for model in models:
        sc = calculate_composite(model["name"], normalized)
        model["source_count"] = sum(1 for rf in RAW_KEYS.values()
                                    if model["raw_data"].get(rf) is not None)
        while len(model["scores"]) < today_idx: model["scores"].append(None)
        if date_is_new: model["scores"].append(sc)
        elif today_idx < len(model["scores"]): model["scores"][today_idx] = sc
        else: model["scores"].append(sc)

    qualified = [m for m in models if m["source_count"] >= QUALIFICATION_MIN]
    ranked    = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1): m["rank"] = rank

    top5 = "\n".join(f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
                      for m in ranked[:5])
    notify(f"TRSbench Top 5 - {TODAY}\n{top5}\n\nQualified: {len(qualified)}")

    data["checksum"] = generate_checksum(data)

    if DRY_RUN:
        notify("DRY RUN - nothing written."); return

    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

    ok = git_push(f"TRSbench daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"TRSbench done! {TODAY} | {len(qualified)} models | trainingrun.ai/scores")
    else:
        notify(f"JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
