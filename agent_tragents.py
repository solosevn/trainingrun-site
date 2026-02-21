#!/usr/bin/env python3
"""
====================================================================
  AGENT TRAGENTS -- TRAgents Daily Scraper (Autonomous Agents)
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRAgents V1.0 (Feb 16, 2026)
====================================================================
  6 pillars | 22 sources:

  Pillar 1: Task Completion (25%)
    - GAIA            hal.cs.princeton.edu/gaia          8%
    - SWE-bench       swebench.com                       7%
    - OSWorld         os-world.github.io                 5%
    - tau-bench       taubench.com                       5%

  Pillar 2: Cost Efficiency (20%)
    - HAL Cost        hal.cs.princeton.edu               8%
    - ARC-AGI Cost    arcprize.org/arc-agi-2             5%
    - Galileo         huggingface.co/spaces/galileo-ai   4%
    - AA Pricing      artificialanalysis.ai              3%

  Pillar 3: Tool Reliability (20%)
    - SEAL Tool Use   scale.com/leaderboard              8%
    - MCPToolBench    arxiv (static data)                5%
    - Docker Eval     docker.com/blog                    4%
    - ToolComp        scale.com/leaderboard              3%

  Pillar 4: Safety & Security (15%)
    - ToolEmu         toolemu.github.io                  5%
    - ST-WebAgent     arxiv (static data)                4%
    - OS-Harm         arxiv (static data)                3%
    - PASB            arxiv (static data)                3%

  Pillar 5: Accessibility (10%)
    - HuggingFace     huggingface.co                     4%
    - Ollama          ollama.com/library                 3%
    - OpenRouter      openrouter.ai/rankings             3%

  Pillar 6: Multi-Model Efficiency (10%)
    - NVIDIA Orch.    Static research data               5%
    - HAL Scaffold    hal.cs.princeton.edu               3%
    - AA Token Eff.   artificialanalysis.ai              2%

  Qualification: 3 of 6 pillars minimum.

  Usage:
    python3 agent_tragents.py
    python3 agent_tragents.py --dry-run
    python3 agent_tragents.py --test-telegram

  Env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, REPO_PATH
  Deps: pip3 install playwright python-telegram-bot beautifulsoup4
        python3 -m playwright install chromium
====================================================================
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
log = logging.getLogger("tragents")

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "tragent-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# -- TRAgents V1.0 pillar weights ----------------------------------
WEIGHTS = {
    "task_completion":    0.25,
    "cost_efficiency":    0.20,
    "tool_reliability":   0.20,
    "safety_security":    0.15,
    "accessibility":      0.10,
    "multi_model":        0.10,
}

# Sub-metric weights within each pillar
SUB_WEIGHTS = {
    # Task Completion
    "gaia_pct":          0.08,
    "swebench_pct":      0.07,
    "osworld_pct":       0.05,
    "taubench_pct":      0.05,
    # Cost Efficiency
    "hal_cost_inv":      0.08,   # inverted: lower cost = higher score
    "arcagi_cost_inv":   0.05,
    "galileo_cost_inv":  0.04,
    "aa_pricing_inv":    0.03,
    # Tool Reliability
    "seal_tool_pct":     0.08,
    "mcp_tool_pct":      0.05,
    "docker_tool_pct":   0.04,
    "toolcomp_pct":      0.03,
    # Safety
    "toolemu_pct":       0.05,
    "st_webagent_pct":   0.04,
    "osharm_pct":        0.03,
    "pasb_pct":          0.03,
    # Accessibility
    "openweight_score":  0.04,
    "hardware_inv":      0.03,   # inverted: lower VRAM req = higher score
    "framework_score":   0.03,
    # Multi-Model
    "router_perf":       0.05,
    "hal_scaffold_pct":  0.03,
    "token_eff_inv":     0.02,   # inverted: fewer tokens = higher score
}

QUALIFICATION_MIN = 3   # 3 of 6 pillars
LOWER_IS_BETTER = {"hal_cost_inv", "arcagi_cost_inv", "galileo_cost_inv",
                   "aa_pricing_inv", "hardware_inv", "token_eff_inv"}

PILLAR_FIELDS = {
    "task_completion":  ["gaia_pct", "swebench_pct", "osworld_pct", "taubench_pct"],
    "cost_efficiency":  ["hal_cost_inv", "arcagi_cost_inv", "galileo_cost_inv", "aa_pricing_inv"],
    "tool_reliability": ["seal_tool_pct", "mcp_tool_pct", "docker_tool_pct", "toolcomp_pct"],
    "safety_security":  ["toolemu_pct", "st_webagent_pct", "osharm_pct", "pasb_pct"],
    "accessibility":    ["openweight_score", "hardware_inv", "framework_score"],
    "multi_model":      ["router_perf", "hal_scaffold_pct", "token_eff_inv"],
}


# == HELPERS =======================================================
def notify(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info(f"[TG] {text}"); return
    async def _send():
        await Bot(token=TELEGRAM_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
    try: asyncio.run(_send())
    except Exception as e: log.warning(f"Telegram: {e}")


def playwright_get(url: str, wait_ms: int = 8000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def parse_table(html: str, name_hints: list, score_hints: list) -> dict[str, float]:
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2: continue
        headers = [h.get_text(strip=True).lower() for h in rows[0].find_all(["th", "td"])]
        nc = next((i for i, h in enumerate(headers) if any(kw in h for kw in name_hints)), 0)
        sc = next((i for i, h in enumerate(headers) if any(kw in h for kw in score_hints)), 1)
        result = {}
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(nc, sc): continue
            name = cells[nc].get_text(strip=True)
            val  = cells[sc].get_text(strip=True).replace("%", "").replace(",", "").strip()
            try:
                v = float(val)
                if name: result[name] = v
            except ValueError: pass
        if result: return result
    return {}
# == SCRAPERS -- PILLAR 1: TASK COMPLETION =========================

def scrape_gaia() -> dict[str, float]:
    """hal.cs.princeton.edu/gaia -- GAIA benchmark. Returns {model: overall_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping GAIA (Princeton HAL)...")
        html = playwright_get("https://hal.cs.princeton.edu/gaia", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        # HAL often has a table with model, overall%, level1%, level2%, level3%
        result = parse_table(html,
                              name_hints=["model", "agent", "name"],
                              score_hints=["overall", "avg", "score"])
        scores = result
        log.info(f"  ✅ GAIA: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ GAIA: {e}")
    return scores


def scrape_swebench_agents() -> dict[str, float]:
    """swebench.com -- verified % resolved (same source as TRScode, different weight)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SWE-bench (agents context)...")
        html = playwright_get("https://www.swebench.com/", wait_ms=6000)
        scores = parse_table(html,
                              name_hints=["model", "name", "agent"],
                              score_hints=["resolve", "%", "score"])
        log.info(f"  ✅ SWE-bench: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SWE-bench: {e}")
    return scores


def scrape_osworld() -> dict[str, float]:
    """os-world.github.io -- desktop agent benchmark. Returns {model: success_rate}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping OSWorld...")
        html = playwright_get("https://os-world.github.io/", wait_ms=8000)
        scores = parse_table(html,
                              name_hints=["model", "agent", "name"],
                              score_hints=["success", "score", "rate", "%"])
        log.info(f"  ✅ OSWorld: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ OSWorld: {e}")
    return scores


def scrape_taubench() -> dict[str, float]:
    """taubench.com -- tau-bench customer service agent. Returns {model: pass_rate}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping tau-bench...")
        html = playwright_get("https://taubench.github.io/", wait_ms=8000)
        scores = parse_table(html,
                              name_hints=["model", "agent", "name"],
                              score_hints=["pass", "score", "rate", "%"])
        log.info(f"  ✅ tau-bench: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ tau-bench: {e}")
    return scores


# == SCRAPERS -- PILLAR 2: COST EFFICIENCY ==========================

def scrape_hal_cost() -> dict[str, float]:
    """hal.cs.princeton.edu -- cost per task. Lower = better. Returns $/task."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping HAL cost-per-task...")
        html = playwright_get("https://hal.cs.princeton.edu/", wait_ms=10000)
        result = parse_table(html,
                              name_hints=["model", "agent"],
                              score_hints=["cost", "$", "dollar"])
        scores = result
        log.info(f"  ✅ HAL cost: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ HAL cost: {e}")
    return scores


def scrape_arcagi_cost() -> dict[str, float]:
    """arcprize.org/arc-agi-2 -- cost per task reported alongside scores."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping ARC-AGI-2 cost...")
        html = playwright_get("https://arcprize.org/arc-agi-2", wait_ms=8000)
        result = parse_table(html,
                              name_hints=["model"],
                              score_hints=["cost", "$", "task"])
        scores = result
        log.info(f"  ✅ ARC-AGI cost: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ ARC-AGI cost: {e}")
    return scores


def scrape_galileo() -> dict[str, float]:
    """Galileo agent leaderboard -- cost per session. Returns $/session."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Galileo Agent Leaderboard...")
        url = "https://huggingface.co/spaces/galileo-ai/agent-leaderboard"
        html = playwright_get(url, wait_ms=10000)
        result = parse_table(html,
                              name_hints=["model", "name"],
                              score_hints=["cost", "$", "session"])
        scores = result
        log.info(f"  ✅ Galileo: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Galileo: {e}")
    return scores


# == SCRAPERS -- PILLAR 3: TOOL RELIABILITY =========================

def scrape_seal_tool() -> dict[str, float]:
    """scale.com/leaderboard -- SEAL Agentic Tool Use. Returns {model: pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping SEAL Agentic Tool Use...")
        html = playwright_get("https://scale.com/leaderboard", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        # Scale AI leaderboard may have multiple tabs -- look for "agentic" or "tool"
        result = parse_table(html,
                              name_hints=["model", "name"],
                              score_hints=["score", "accuracy", "tool", "%"])
        scores = result
        log.info(f"  ✅ SEAL Tool Use: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ SEAL: {e}")
    return scores


def scrape_toolemu() -> dict[str, float]:
    """toolemu.github.io -- tool emulation safety. Returns {model: safety_pct}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping ToolEmu...")
        html = playwright_get("https://toolemu.github.io/", wait_ms=8000)
        result = parse_table(html,
                              name_hints=["model", "name"],
                              score_hints=["safe", "score", "rate", "%"])
        scores = result
        log.info(f"  ✅ ToolEmu: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ ToolEmu: {e}")
    return scores


# == SCRAPERS -- PILLAR 5: ACCESSIBILITY ============================

def scrape_openrouter_access() -> dict[str, float]:
    """openrouter.ai/rankings -- API accessibility (same source as TRSbench usage)."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping OpenRouter (accessibility)...")
        html = playwright_get("https://openrouter.ai/rankings", wait_ms=8000)
        # For accessibility: any model on OpenRouter = accessible via API (25 points)
        soup = BeautifulSoup(html, "html.parser")
        rank = 1
        for item in soup.select("tr, li, [data-model]"):
            name = item.get_text(strip=True).split("\n")[0].strip()
            if name and len(name) > 3:
                scores[name] = 25.0  # API-accessible = 25/100 score (per Bible)
                rank += 1
                if rank > 100: break
        log.info(f"  ✅ OpenRouter access: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ OpenRouter access: {e}")
    return scores


def scrape_ollama() -> dict[str, float]:
    """ollama.com/library -- local model availability. Returns {model: vram_gb}."""
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Ollama library...")
        html = playwright_get("https://ollama.com/library", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        # Ollama lists model sizes; lower VRAM = more accessible
        result = parse_table(html,
                              name_hints=["model", "name"],
                              score_hints=["size", "gb", "param"])
        # Store raw VRAM GB (will be inverted in normalize)
        scores = result
        log.info(f"  ✅ Ollama: {len(scores)} models")
    except Exception as e:
        log.error(f"  ❌ Ollama: {e}")
    return scores

# == SCORING ENGINE ================================================

def normalize(models: list, raw_key: str) -> dict[str, float]:
    vals = {m["name"]: (m["raw_data"].get(raw_key) or 0.0) for m in models}
    if raw_key in LOWER_IS_BETTER:
        non_zero = {k: v for k, v in vals.items() if v > 0}
        if not non_zero: return {k: 0.0 for k in vals}
        worst = max(non_zero.values())
        return {k: round((1 - v / worst) * 100 if v > 0 else 0.0, 4) for k, v in vals.items()}
    top = max(vals.values(), default=0.0)
    if top == 0.0: return {k: 0.0 for k in vals}
    return {k: round((v / top) * 100.0, 4) for k, v in vals.items()}


def count_nonnull_pillars(model: dict) -> int:
    count = 0
    for pillar, fields in PILLAR_FIELDS.items():
        if any(model["raw_data"].get(f) is not None for f in fields):
            count += 1
    return count


def calculate_composite(model_name: str, normalized: dict) -> float:
    return round(sum(normalized.get(mkey, {}).get(model_name, 0.0) * w
                     for mkey, w in SUB_WEIGHTS.items()), 2)


def generate_checksum(data: dict) -> str:
    names  = "|".join(m["name"] for m in data["models"])
    scores = ",".join(f"{s:.1f}" if s is not None else "null"
                      for m in data["models"] for s in m["scores"])
    return hashlib.sha256((names + ":" + scores).encode()).hexdigest()


def match_name(scraped: str, existing: list[str]) -> str | None:
    s = scraped.lower().strip()
    for name in existing:
        if name.lower() == s: return name
    for name in existing:
        n = name.lower()
        if s in n or n in s: return name
    s_tok = set(s.replace("-", " ").replace("_", " ").split())
    for name in existing:
        n_tok = set(name.lower().replace("-", " ").replace("_", " ").split())
        if len(s_tok & n_tok) >= 2: return name
    return None


def git_push(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "tragent-data.json"],
                       cwd=REPO_PATH, check=True, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", commit_msg],
                           cwd=REPO_PATH, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log.info("Nothing to commit."); return True
            log.error(f"Commit:\n{r.stderr}"); return False
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e.stderr}"); return False


# == MAIN ==========================================================
def main():
    if TEST_TELEGRAM:
        notify("✅ <b>TRAgents Agent online</b>"); print("Telegram OK."); return

    mode = "DRY RUN 🔍" if DRY_RUN else "LIVE 🚀"
    log.info(f"Agent TRAgents | {TODAY} | {mode}")
    notify(f"🤖 <b>Agent TRAgents starting</b>\n📅 {TODAY}\n⚙️ {mode}\n22 sources → tragent-data.json")

    if not DATA_FILE.exists():
        msg = f"tragent-data.json not found at {DATA_FILE}"
        log.error(msg); notify(f"❌ {msg}"); return

    with open(DATA_FILE) as f: data = json.load(f)
    models = data["models"]
    names  = [m["name"] for m in models]

    if TODAY in data["dates"]:
        date_is_new = False; today_idx = data["dates"].index(TODAY)
    else:
        date_is_new = True; data["dates"].append(TODAY); today_idx = len(data["dates"]) - 1

    notify(f"📂 {len(models)} models | {data['dates'][0]} → {data['dates'][-1]}")

    # -- Scrape all pillars --
    def apply(src_dict: dict, field: str):
        for sn, val in src_dict.items():
            canon = match_name(sn, names)
            if canon:
                m = next(x for x in models if x["name"] == canon)
                m["raw_data"][field] = val

    # Pillar 1: Task Completion
    apply(scrape_gaia(),            "gaia_pct")
    apply(scrape_swebench_agents(), "swebench_pct")
    apply(scrape_osworld(),         "osworld_pct")
    apply(scrape_taubench(),        "taubench_pct")
    notify("✅ Pillar 1: Task Completion scraped")

    # Pillar 2: Cost Efficiency
    apply(scrape_hal_cost(),   "hal_cost_inv")
    apply(scrape_arcagi_cost(),"arcagi_cost_inv")
    apply(scrape_galileo(),    "galileo_cost_inv")
    notify("✅ Pillar 2: Cost Efficiency scraped")

    # Pillar 3: Tool Reliability
    apply(scrape_seal_tool(), "seal_tool_pct")
    notify("✅ Pillar 3: Tool Reliability scraped (SEAL only; others = static research data)")

    # Pillar 4: Safety
    apply(scrape_toolemu(), "toolemu_pct")
    notify("✅ Pillar 4: Safety scraped (ToolEmu live; others = static research data)")

    # Pillar 5: Accessibility
    apply(scrape_openrouter_access(), "openweight_score")
    apply(scrape_ollama(),            "hardware_inv")
    notify("✅ Pillar 5: Accessibility scraped")

    # -- Count pillars --
    for model in models:
        model["source_count"] = count_nonnull_pillars(model)

    # -- Normalize --
    all_raw_fields = [f for fields in PILLAR_FIELDS.values() for f in fields]
    normalized = {f: normalize(models, f) for f in all_raw_fields}

    # Map sub-weight keys to raw fields for composite calculation
    sub_to_raw = {k: k for k in SUB_WEIGHTS}  # keys match raw field names

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
    notify(f"🏆 <b>TRAgents Top 5 -- {TODAY}</b>\n{top5}\n\n📊 Qualified: {len(qualified)}")

    data["checksum"] = generate_checksum(data)

    if DRY_RUN:
        notify("🔍 <b>DRY RUN</b> -- nothing written."); return

    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

    ok = git_push(f"TRAgents daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRAgents done!</b>\n📅 {TODAY}\n🌐 → trainingrun.ai/tragents")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
