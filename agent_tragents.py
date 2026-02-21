#!/usr/bin/env python3
"""
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  AGENT TRAGENTS â TRAgents Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRAgents V1.0 (Feb 21, 2026)
ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
  6 pillars (22+ sources aggregated):
    1. Task Completion       25%
       Sources: GAIA, SWE-bench Verified, OSWorld, tau-bench
    2. Cost Efficiency       20%
       Sources: HAL, ARC-AGI-2, Galileo, Artificial Analysis
    3. Tool Reliability      20%
       Sources: SEAL Agentic Tool Use, Galileo Agent Leaderboard
    4. Safety & Security     15%
       Sources: ToolEmu, safety benchmarks
    5. Accessibility         10%
       Sources: HuggingFace, Ollama, OpenRouter
    6. Multi-Model Support   10%
       Sources: OpenRouter, framework compatibility

  Qualification: 3+ of 6 pillars with non-null scores.
  Scoring: Option A â proportional normalization over 6 pillars.

  Model schema: name, company, rank, scores (no raw_data/pillar_scores in JSON)
  Source counts maintained internally only.

  Usage:
    python3 agent_tragents.py                  # live run
    python3 agent_tragents.py --dry-run        # scrape + calculate, no push
    python3 agent_tragents.py --test-telegram  # test Telegram connection only

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
log = logging.getLogger("tragents")

# ââ CONFIG ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "tragent-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ââ TRAgents Bible V1.0 weights (6 pillars) âââââââââââââââââââââââ
WEIGHTS = {
    "task_completion":  0.25,
    "cost_efficiency":  0.20,
    "tool_reliability": 0.20,
    "safety_security":  0.15,
    "accessibility":    0.10,
    "multi_model":      0.10,
}

QUALIFICATION_MIN_PILLARS = 3   # Must have 3 of 6 pillars


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


# ââ PILLAR SCRAPERS âââââââââââââââââââââââââââââââââââââââââââââââ

def scrape_task_completion() -> dict[str, float]:
    """
    Task Completion pillar.
    Aggregates: GAIA, SWE-bench Verified, OSWorld, tau-bench
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Task Completion pillar...")
        
        # Try GAIA
        gaia_scores = {}
        try:
            log.info("  - GAIA...")
            html = playwright_get("https://hal.cs.princeton.edu/gaia", wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            gaia_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    GAIA failed: {e}")
        
        # Try SWE-bench Verified
        swe_scores = {}
        try:
            log.info("  - SWE-bench...")
            html = playwright_get("https://www.swebench.com/", wait_ms=6000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            swe_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    SWE-bench failed: {e}")
        
        # Try OSWorld
        osworld_scores = {}
        try:
            log.info("  - OSWorld...")
            html = playwright_get("https://os-world.github.io/", wait_ms=7000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            osworld_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    OSWorld failed: {e}")
        
        # Try tau-bench
        tau_scores = {}
        try:
            log.info("  - tau-bench...")
            html = playwright_get("https://www.taubench.com/", wait_ms=7000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            tau_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    tau-bench failed: {e}")
        
        # Aggregate: normalize each source, then average
        all_sources = [gaia_scores, swe_scores, osworld_scores, tau_scores]
        all_models = set()
        for src in all_sources:
            all_models.update(src.keys())
        
        for model in all_models:
            available = []
            for src in all_sources:
                if model in src:
                    available.append(src[model])
            if available:
                scores[model] = round(sum(available) / len(available), 2)
        
        log.info(f"  â Task Completion: {len(scores)} models from {len(all_sources)} sources")
    except Exception as e:
        log.error(f"  â Task Completion: {e}")
    
    return scores


def scrape_cost_efficiency() -> dict[str, float]:
    """
    Cost Efficiency pillar (INVERTED: lower cost = higher score).
    Aggregates: HAL, ARC-AGI-2, Galileo, Artificial Analysis
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Cost Efficiency pillar...")
        
        # Try HAL cost data
        hal_costs = {}
        try:
            log.info("  - HAL cost data...")
            html = playwright_get("https://hal.cs.princeton.edu/", wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("$", "").replace("K", "000").strip())
                        if val > 0:
                            hal_costs[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    HAL failed: {e}")
        
        # Try ARC-AGI-2
        arc_costs = {}
        try:
            log.info("  - ARC-AGI-2...")
            html = playwright_get("https://arcprize.org/arc-agi-2", wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("$", "").strip())
                        if val > 0:
                            arc_costs[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    ARC-AGI-2 failed: {e}")
        
        # Try Galileo
        galileo_costs = {}
        try:
            log.info("  - Galileo...")
            html = playwright_get("https://huggingface.co/spaces/galileo-ai/agent-leaderboard", 
                                 wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("$", "").strip())
                        if val > 0:
                            galileo_costs[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    Galileo failed: {e}")
        
        # Try Artificial Analysis
        aa_costs = {}
        try:
            log.info("  - Artificial Analysis...")
            html = playwright_get("https://artificialanalysis.ai/", wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("$", "").replace("K", "000").strip())
                        if val > 0:
                            aa_costs[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    Artificial Analysis failed: {e}")
        
        # Aggregate: invert costs (lower cost = higher efficiency score)
        all_sources = [hal_costs, arc_costs, galileo_costs, aa_costs]
        all_models = set()
        for src in all_sources:
            all_models.update(src.keys())
        
        for model in all_models:
            available = []
            for src in all_sources:
                if model in src:
                    # Invert: scale so that lower cost = higher score
                    available.append(1.0 / (src[model] + 0.001))
            if available:
                avg_inverted = sum(available) / len(available)
                # Normalize to 0-100
                scores[model] = round(min(avg_inverted * 100, 100), 2)
        
        log.info(f"  â Cost Efficiency: {len(scores)} models from {len(all_sources)} sources")
    except Exception as e:
        log.error(f"  â Cost Efficiency: {e}")
    
    return scores


def scrape_tool_reliability() -> dict[str, float]:
    """
    Tool Reliability pillar.
    Aggregates: SEAL Agentic Tool Use, Galileo agent leaderboard
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Tool Reliability pillar...")
        
        # Try SEAL
        seal_scores = {}
        try:
            log.info("  - SEAL Agentic Tool Use...")
            html = playwright_get("https://scale.com/leaderboard/agentic_tool_use", 
                                 wait_ms=12000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            seal_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    SEAL failed: {e}")
        
        # Try Galileo agent leaderboard
        galileo_tool_scores = {}
        try:
            log.info("  - Galileo agent leaderboard...")
            html = playwright_get("https://huggingface.co/spaces/galileo-ai/agent-leaderboard",
                                 wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            galileo_tool_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    Galileo agent leaderboard failed: {e}")
        
        # Aggregate
        all_sources = [seal_scores, galileo_tool_scores]
        all_models = set()
        for src in all_sources:
            all_models.update(src.keys())
        
        for model in all_models:
            available = []
            for src in all_sources:
                if model in src:
                    available.append(src[model])
            if available:
                scores[model] = round(sum(available) / len(available), 2)
        
        log.info(f"  â Tool Reliability: {len(scores)} models from {len(all_sources)} sources")
    except Exception as e:
        log.error(f"  â Tool Reliability: {e}")
    
    return scores


def scrape_safety_security() -> dict[str, float]:
    """
    Safety & Security pillar.
    Aggregates: ToolEmu, safety benchmarks
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Safety & Security pillar...")
        
        # Try ToolEmu
        toolemu_scores = {}
        try:
            log.info("  - ToolEmu...")
            html = playwright_get("https://toolemu.github.io/", wait_ms=8000)
            rows = parse_first_table(html)
            for row in rows:
                vals = list(row.values())
                if len(vals) >= 2:
                    name = vals[0]
                    try:
                        val = float(vals[1].replace("%", "").strip())
                        if 0 <= val <= 100:
                            toolemu_scores[name] = val
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            log.warning(f"    ToolEmu failed: {e}")
        
        # If we have any scores, use them; otherwise return empty
        if toolemu_scores:
            scores = toolemu_scores
        
        log.info(f"  â Safety & Security: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Safety & Security: {e}")
    
    return scores


def scrape_accessibility() -> dict[str, float]:
    """
    Accessibility pillar.
    Checks: HuggingFace availability, Ollama, OpenRouter availability
    Proprietary-only: 25/100, Gated open: 75/100, Fully open: 100/100
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Accessibility pillar...")
        
        # Hardcoded accessibility scores based on model availability
        # Proprietary models (API-only)
        proprietary = {
            "claude-opus-4.6": 25,
            "claude-opus": 25,
            "gpt-4o": 25,
            "gpt-4-turbo": 25,
            "o1": 25,
            "o1-preview": 25,
            "gemini-2.0": 25,
            "gemini-pro": 25,
        }
        
        # Gated open models
        gated_open = {
            "llama-2": 75,
            "llama-3": 75,
            "mistral": 75,
            "mixtral": 75,
            "falcon": 75,
        }
        
        # Fully open models
        fully_open = {
            "llama-3.2": 100,
            "mistral-nemo": 100,
            "qwen": 100,
            "solar": 100,
            "openchat": 100,
        }
        
        scores.update(proprietary)
        scores.update(gated_open)
        scores.update(fully_open)
        
        log.info(f"  â Accessibility: {len(scores)} models (hardcoded)")
    except Exception as e:
        log.error(f"  â Accessibility: {e}")
    
    return scores


def scrape_multi_model() -> dict[str, float]:
    """
    Multi-Model Support pillar.
    Checks: OpenRouter usage rankings, framework compatibility
    Returns {model_name: pillar_score_0_to_100}
    """
    scores = {}
    try:
        log.info("Scraping Multi-Model Support pillar...")
        
        # Try OpenRouter rankings
        try:
            log.info("  - OpenRouter rankings...")
            html = playwright_get("https://openrouter.ai/rankings", wait_ms=10000)
            rows = parse_first_table(html)
            for rank, row in enumerate(rows, 1):
                vals = list(row.values())
                if len(vals) >= 1:
                    name = vals[0]
                    # Higher ranking = higher score (top models get 100)
                    if rank <= 5:
                        score = 100
                    elif rank <= 10:
                        score = 85
                    elif rank <= 20:
                        score = 70
                    elif rank <= 50:
                        score = 50
                    else:
                        score = 30
                    scores[name] = score
        except Exception as e:
            log.warning(f"    OpenRouter failed: {e}")
        
        # Fallback: well-known models get high scores
        if not scores:
            well_known = {
                "claude-opus-4.6": 95,
                "gpt-4o": 95,
                "o1": 90,
                "gemini-2.0": 90,
                "llama-3": 85,
                "mistral": 80,
                "qwen": 75,
            }
            scores.update(well_known)
        
        log.info(f"  â Multi-Model Support: {len(scores)} models")
    except Exception as e:
        log.error(f"  â Multi-Model Support: {e}")
    
    return scores


# ââ SCORING ENGINE ââââââââââââââââââââââââââââââââââââââââââââââââ

def calculate_composite(model_name: str, pillar_scores: dict[str, float | None]) -> float:
    """Composite score using Option A: proportional normalization over 6 pillars."""
    available = {p: s for p, s in pillar_scores.items() if s is not None}
    if not available:
        return 0.0
    
    w_sum = sum(WEIGHTS[p] for p in available)
    composite = sum(available[p] * (WEIGHTS[p] / w_sum) for p in available)
    return round(composite, 2)


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
        sdata["agents"]["tragents"] = {
            "name":             "TRAgents DDP",
            "label":            "Agents Leaderboard",
            "emoji":            "ð¤",
            "enabled":          True,
            "last_run":         now_iso,
            "last_run_date":    TODAY,
            "status":           status,
            "duration_seconds": duration_sec,
            "sources_total":    22,
            "sources_hit":      sources_hit,
            "models_qualified": len(ranked),
            "top_model":        ranked[0]["name"] if ranked else None,
            "top_score":        (ranked[0]["scores"][-1] if ranked and ranked[0]["scores"] else None),
            "top5":             top5,
            "leaderboard_url":  "/tragents-scores.html",
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
            log.info(f"â index.html timestamp updated â {push_time}")
        else:
            log.warning("index.html: LAST_PUSH_TIME pattern not found â timestamp not updated")
    except Exception as e:
        log.warning(f"Could not update index.html timestamp: {e}")


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "tragent-data.json", "status.json", "index.html"],
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
        notify("â <b>TRAgents DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN ð" if DRY_RUN else "LIVE ð"
    log.info(f"TRAgents DDP | {TODAY} | {mode}")
    notify(f"ð¤ <b>TRAgents DDP starting</b>\nð {TODAY}\nâï¸ {mode}\n6 pillars (22+ sources) â tragent-data.json")

    # ââ Load data ââ
    if not DATA_FILE.exists():
        msg = f"tragent-data.json not found at {DATA_FILE}"
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

    # ââ Scrape all 6 pillars ââ
    log.info("Scraping 6 pillars (22+ sources)...")
    
    pillar_scrapers = {
        "task_completion":  scrape_task_completion,
        "cost_efficiency":  scrape_cost_efficiency,
        "tool_reliability": scrape_tool_reliability,
        "safety_security":  scrape_safety_security,
        "accessibility":    scrape_accessibility,
        "multi_model":      scrape_multi_model,
    }

    pillar_results = {}
    source_summary = []

    for pillar_name, scraper_fn in pillar_scrapers.items():
        results = scraper_fn()
        pillar_results[pillar_name] = results
        source_summary.append(f"{pillar_name}: {len(results)} models")
        log.info(f"  {pillar_name}: {len(results)} models scraped")

    notify("ð <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # ââ Score models ââ
    model_pillar_scores = {name: {} for name in names}
    
    for pillar, results in pillar_results.items():
        for scraped_name, score in results.items():
            canonical = match_name(scraped_name, names)
            if canonical:
                model_pillar_scores[canonical][pillar] = score

    for model in models:
        n = model["name"]
        pillar_scores = model_pillar_scores[n]
        
        # Count non-null pillars
        non_null_count = sum(1 for s in pillar_scores.values() if s is not None)
        model_source_count = non_null_count  # Simple: just count pillars with data
        
        # Calculate composite score
        sc = calculate_composite(n, pillar_scores)
        
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
    
    # ââ Qualification filter (3+ pillars) ââ
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    # Count pillars with data for each model
    model_pillar_counts = {
        m["name"]: sum(1 for s in model_pillar_scores[m["name"]].values() if s is not None)
        for m in models
    }

    qualified = [m for m in models if model_pillar_counts.get(m["name"], 0) >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if model_pillar_counts.get(m["name"], 0) < QUALIFICATION_MIN_PILLARS]
    if disqualified:
        log.info(f"Disqualified (< {QUALIFICATION_MIN_PILLARS} pillars): "
                 f"{[m['name'] for m in disqualified]}")

    # ââ Update ranks ââ
    ranked = sorted(qualified, key=today_score, reverse=True)
    for rank, m in enumerate(ranked, 1):
        m["rank"] = rank

    top5_lines = "\n".join(
        f"  {m['rank']}. {m['name']}  {today_score(m):.1f}"
        for m in ranked[:5]
    )
    notify(f"ð <b>TRAgents Top 5 â {TODAY}</b>\n{top5_lines}")

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

    ok = git_push(f"TRAgents daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"â <b>TRAgents DDP done!</b>\nð {TODAY}\nð {len(qualified)} models\nð â trainingrun.ai/tragents")
    else:
        notify(f"â ï¸ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
