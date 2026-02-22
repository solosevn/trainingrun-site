#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
  AGENT TRAGENTS — TRAgents Daily Scraper
  trainingrun.ai | solosevn/trainingrun-site
  Bible: TRAgents V1.0 (Feb 21, 2026)
════════════════════════════════════════════════════════════════════
  6 pillars (22+ sources aggregated):
    1. Task Completion       25%
       Sources: SWE-bench Verified, GAIA, OSWorld, tau-bench
    2. Cost Efficiency       20%
       Sources: ARC-AGI-2, Artificial Analysis
    3. Tool Reliability      20%
       Sources: SEAL Agentic Tool Use, Galileo Agent Leaderboard
    4. Safety & Security     15%
       Sources: SEAL MASK
    5. Accessibility         10%
       Sources: Ollama library
    6. Multi-Model Support   10%
       Sources: OpenRouter rankings

  Qualification: 3+ of 6 pillars with non-null scores.
  Scoring: Option A — proportional normalization over 6 pillars.

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
log = logging.getLogger("tragents")

# ══ CONFIG ════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
REPO_PATH        = Path(os.environ.get("REPO_PATH",
                        str(Path.home() / "trainingrun-site")))
DATA_FILE        = REPO_PATH / "tragent-data.json"
TODAY            = date.today().isoformat()
DRY_RUN          = "--dry-run"       in sys.argv
TEST_TELEGRAM    = "--test-telegram" in sys.argv

# ── TRAgents Bible V1.0 weights (6 pillars) ───────────────────────
WEIGHTS = {
    "task_completion":  0.25,
    "cost_efficiency":  0.20,
    "tool_reliability": 0.20,
    "safety_security":  0.15,
    "accessibility":    0.10,
    "multi_model":      0.10,
}

QUALIFICATION_MIN_PILLARS = 3   # Must have 3 of 6 pillars


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


# ══ PLAYWRIGHT HELPERS ════════════════════════════════════════════

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")


def playwright_get(url: str, wait_ms: int = 5000) -> str:
    """Launch headless Chromium, load url, return page HTML."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=_UA)
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
        ctx = browser.new_context(user_agent=_UA)
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
        ctx = browser.new_context(user_agent=_UA)
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


def _parse_seal_innertext(text: str) -> dict[str, float]:
    """Parse SEAL leaderboard innerText (rank/name/score format) → {model: score}."""
    scores = {}
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        # Match rank numbers: "1", "#1", "1.", "#1."
        m = re.match(r'^#?(\d+)\.?$', lines[i])
        if m:
            rank = int(m.group(1))
            if rank > 200:
                i += 1
                continue
            if i + 1 < len(lines):
                name = lines[i + 1]
                # Skip lines that look like ranks or headers
                if re.match(r'^#?\d+\.?$', name) or len(name) <= 2:
                    i += 1
                    continue
                # Look ahead up to 8 lines for a score
                found = False
                for j in range(i + 2, min(i + 9, len(lines))):
                    sm = re.match(r'^(\d+(?:\.\d+)?)\s*%?$', lines[j])
                    if sm:
                        val = float(sm.group(1))
                        if 0 < val <= 100 and name and len(name) > 2:
                            scores[name] = val
                            found = True
                            i = j + 1
                            break
                    # Stop if we hit another rank number
                    if re.match(r'^#?\d+\.?$', lines[j]) and int(re.match(r'^#?(\d+)', lines[j]).group(1)) > rank:
                        break
                if not found:
                    i += 2
            else:
                i += 1
        else:
            i += 1
    return scores


# ══ PILLAR SCRAPERS ═══════════════════════════════════════════════

def scrape_task_completion() -> dict[str, float]:
    """
    Task Completion pillar.
    Aggregates: SWE-bench Verified, GAIA, OSWorld, tau-bench
    Returns {model_name: pillar_score_0_to_100}
    """
    log.info("Scraping Task Completion pillar...")
    all_sources = []

    # ── 1. SWE-bench Verified ─────────────────────────────────────
    swe_scores: dict[str, float] = {}
    try:
        log.info("  - SWE-bench Verified...")
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
                        swe_scores[name] = pct
                except ValueError:
                    pass
            if swe_scores:
                break
        log.info(f"    SWE-bench: {len(swe_scores)} models")
        if swe_scores:
            all_sources.append(swe_scores)
    except Exception as e:
        log.warning(f"    SWE-bench failed: {e}")

    # ── 2. GAIA (HAL leaderboard) ─────────────────────────────────
    gaia_scores: dict[str, float] = {}
    try:
        log.info("  - GAIA...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
            page = ctx.new_page()
            try:
                page.goto("https://hal.cs.princeton.edu/gaia",
                          wait_until="networkidle", timeout=90_000)
            except Exception:
                pass
            page.wait_for_timeout(8000)
            rows = page.evaluate("""() => {
                const tables = document.querySelectorAll('table');
                if (!tables.length) return [];
                let best = tables[0];
                for (const t of tables) if (t.rows.length > best.rows.length) best = t;
                const allRows = Array.from(best.querySelectorAll('tr'));
                if (allRows.length < 2) return [];
                const headers = Array.from(allRows[0].querySelectorAll('th,td'))
                    .map(h => h.textContent.trim().toLowerCase());
                const nameIdx = Math.max(0, headers.findIndex(
                    h => h.includes('model') || h.includes('agent') || h.includes('system')));
                const scoreIdx = headers.findIndex(
                    h => h.includes('avg') || h.includes('overall') || h.includes('total'));
                if (scoreIdx === -1) return [];
                return allRows.slice(1).map(row => {
                    const cells = Array.from(row.querySelectorAll('td,th'))
                        .map(td => td.textContent.trim());
                    return {model: cells[nameIdx] || '', score: cells[scoreIdx] || ''};
                }).filter(r => r.model && r.score);
            }""")
            browser.close()
        for row in rows:
            name = str(row.get('model', '')).strip()
            score_raw = str(row.get('score', '')).replace('%', '').strip()
            if not name or not score_raw:
                continue
            try:
                val = float(score_raw)
                if 0 <= val <= 100:
                    gaia_scores[name] = val
            except ValueError:
                pass
        log.info(f"    GAIA: {len(gaia_scores)} models")
        if gaia_scores:
            all_sources.append(gaia_scores)
    except Exception as e:
        log.warning(f"    GAIA failed: {e}")

    # ── 3. tau-bench ─────────────────────────────────────────────
    tau_scores: dict[str, float] = {}
    try:
        log.info("  - tau-bench...")
        html = playwright_get("https://www.taubench.com/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h or "agent" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "pass" in h or "%" in h
                              or "success" in h or "avg" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, score_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                raw  = cells[score_col].get_text(strip=True).replace("%", "").strip()
                try:
                    val = float(raw)
                    if name and 0 <= val <= 100:
                        tau_scores[name] = val
                except ValueError:
                    pass
            if tau_scores:
                break
        log.info(f"    tau-bench: {len(tau_scores)} models")
        if tau_scores:
            all_sources.append(tau_scores)
    except Exception as e:
        log.warning(f"    tau-bench failed: {e}")

    # ── 4. OSWorld ───────────────────────────────────────────────
    osworld_scores: dict[str, float] = {}
    try:
        log.info("  - OSWorld...")
        html = playwright_get("https://os-world.github.io/", wait_ms=8000)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h or "method" in h
                             or "agent" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "success" in h or "score" in h or "%" in h
                              or "result" in h or "overall" in h), 1)
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, score_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                raw  = cells[score_col].get_text(strip=True).replace("%", "").strip()
                try:
                    val = float(raw)
                    if name and 0 <= val <= 100:
                        osworld_scores[name] = val
                except ValueError:
                    pass
            if osworld_scores:
                break
        log.info(f"    OSWorld: {len(osworld_scores)} models")
        if osworld_scores:
            all_sources.append(osworld_scores)
    except Exception as e:
        log.warning(f"    OSWorld failed: {e}")

    # ── Aggregate: average of available sources per model ─────────
    scores: dict[str, float] = {}
    all_models: set[str] = set()
    for src in all_sources:
        all_models.update(src.keys())
    for model in all_models:
        vals = [src[model] for src in all_sources if model in src]
        if vals:
            scores[model] = round(sum(vals) / len(vals), 2)

    log.info(f"  ✅ Task Completion: {len(scores)} models from {len(all_sources)} sources")
    return scores


def scrape_cost_efficiency() -> dict[str, float]:
    """
    Cost Efficiency pillar.
    Aggregates: ARC-AGI-2 performance + Artificial Analysis quality (normalized)
    Returns {model_name: pillar_score_0_to_100}
    """
    log.info("Scraping Cost Efficiency pillar...")
    all_sources = []

    # ── 1. ARC-AGI-2 (proven scraper) ────────────────────────────
    arc_scores: dict[str, float] = {}
    try:
        log.info("  - ARC-AGI-2...")
        html = playwright_get("https://arcprize.org/leaderboard", wait_ms=10000)
        rows = parse_first_table(html)
        for row in rows:
            raw_name = row.get("AI System", "")
            if not raw_name:
                vals = list(row.values())
                raw_name = vals[0] if vals else ""
            if not raw_name:
                continue
            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            name = re.sub(r'\s*[²³¹⁴⁵]\s*$', '', name).strip()
            arc2_raw = row.get("ARC-AGI-2", "")
            if not arc2_raw:
                continue
            clean = arc2_raw.replace("%", "").strip()
            try:
                pct = float(clean)
                if 0 <= pct <= 100:
                    if name not in arc_scores or pct > arc_scores[name]:
                        arc_scores[name] = pct
            except ValueError:
                pass
        log.info(f"    ARC-AGI-2: {len(arc_scores)} models")
        if arc_scores:
            all_sources.append(arc_scores)
    except Exception as e:
        log.warning(f"    ARC-AGI-2 failed: {e}")

    # ── 2. Artificial Analysis — quality scores ───────────────────
    aa_scores: dict[str, float] = {}
    try:
        log.info("  - Artificial Analysis (quality)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
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
                // col0=Model name, col1=Quality (normalized score)
                return allRows.slice(2).map(row => {
                    const cells = Array.from(row.querySelectorAll('td'))
                        .map(td => td.textContent.trim());
                    return {model: cells[0] || '', quality: cells[1] || ''};
                }).filter(r => r.model && r.quality);
            }""")
            browser.close()
        for row in rows:
            name = str(row.get("model", ""))
            name = re.sub(r'\s*\([^)]+\)\s*$', '', name).strip()
            if not name:
                continue
            quality_raw = str(row.get("quality", ""))
            try:
                val = float(quality_raw.replace(",", "").strip())
                if val > 0:
                    aa_scores[name] = val
            except ValueError:
                pass
        log.info(f"    Artificial Analysis: {len(aa_scores)} models")
        if aa_scores:
            all_sources.append(aa_scores)
    except Exception as e:
        log.warning(f"    Artificial Analysis failed: {e}")

    # ── Aggregate: normalize each source 0→100, then average ──────
    scores: dict[str, float] = {}
    if not all_sources:
        return scores

    normalized: list[dict[str, float]] = []
    for src in all_sources:
        if not src:
            continue
        max_val = max(src.values())
        if max_val > 0:
            normalized.append({k: round((v / max_val) * 100, 2) for k, v in src.items()})

    all_models: set[str] = set()
    for src in normalized:
        all_models.update(src.keys())
    for model in all_models:
        vals = [src[model] for src in normalized if model in src]
        if vals:
            scores[model] = round(sum(vals) / len(vals), 2)

    log.info(f"  ✅ Cost Efficiency: {len(scores)} models from {len(all_sources)} sources")
    return scores


def scrape_tool_reliability() -> dict[str, float]:
    """
    Tool Reliability pillar.
    Aggregates: SEAL Agentic Tool Use, Galileo agent leaderboard
    Returns {model_name: pillar_score_0_to_100}
    """
    log.info("Scraping Tool Reliability pillar...")
    all_sources = []

    # ── 1. SEAL Agentic Tool Use (innerText) ─────────────────────
    seal_scores: dict[str, float] = {}
    try:
        log.info("  - SEAL Agentic Tool Use...")
        text = playwright_get_innertext(
            "https://scale.com/leaderboard/agentic_tool_use", wait_ms=12000)
        seal_scores = _parse_seal_innertext(text)
        log.info(f"    SEAL Agentic Tool Use: {len(seal_scores)} models")
        if seal_scores:
            all_sources.append(seal_scores)
    except Exception as e:
        log.warning(f"    SEAL failed: {e}")

    # ── 2. Galileo agent leaderboard (HF Space) ──────────────────
    galileo_scores: dict[str, float] = {}
    try:
        log.info("  - Galileo agent leaderboard...")
        html = playwright_get_hfspace(
            "https://huggingface.co/spaces/galileo-ai/agent-leaderboard",
            wait_ms=15000)
        rows = parse_first_table(html)
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            trows = table.find_all("tr")
            if len(trows) < 2:
                continue
            headers = [th.get_text(strip=True).lower()
                       for th in trows[0].find_all(["th", "td"])]
            name_col = next((i for i, h in enumerate(headers)
                             if "model" in h or "name" in h or "agent" in h), 0)
            score_col = next((i for i, h in enumerate(headers)
                              if "score" in h or "%" in h or "pass" in h
                              or "success" in h or "overall" in h or "avg" in h), 1)
            for row in trows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(name_col, score_col):
                    continue
                name = cells[name_col].get_text(strip=True)
                raw  = cells[score_col].get_text(strip=True).replace("%", "").strip()
                try:
                    val = float(raw)
                    if name and 0 <= val <= 100:
                        galileo_scores[name] = val
                except ValueError:
                    pass
            if galileo_scores:
                break
        log.info(f"    Galileo: {len(galileo_scores)} models")
        if galileo_scores:
            all_sources.append(galileo_scores)
    except Exception as e:
        log.warning(f"    Galileo failed: {e}")

    # ── Aggregate ─────────────────────────────────────────────────
    scores: dict[str, float] = {}
    all_models: set[str] = set()
    for src in all_sources:
        all_models.update(src.keys())
    for model in all_models:
        vals = [src[model] for src in all_sources if model in src]
        if vals:
            scores[model] = round(sum(vals) / len(vals), 2)

    log.info(f"  ✅ Tool Reliability: {len(scores)} models from {len(all_sources)} sources")
    return scores


def scrape_safety_security() -> dict[str, float]:
    """
    Safety & Security pillar.
    Source: SEAL MASK (scale.com/leaderboard/mask) — higher = safer/more honest
    Returns {model_name: pillar_score_0_to_100}
    """
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Safety & Security pillar (SEAL MASK)...")
        text = playwright_get_innertext(
            "https://scale.com/leaderboard/mask", wait_ms=12000)
        scores = _parse_seal_innertext(text)
        log.info(f"  ✅ Safety & Security: {len(scores)} models (SEAL MASK)")
    except Exception as e:
        log.error(f"  ❌ Safety & Security: {e}")
    return scores


def scrape_accessibility() -> dict[str, float]:
    """
    Accessibility pillar.
    Source: Ollama library — models runnable locally score 100.
    Returns {model_name: pillar_score_0_to_100}
    """
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Accessibility pillar (Ollama library)...")
        html = playwright_get("https://ollama.com/library", wait_ms=10000)
        soup = BeautifulSoup(html, "html.parser")
        # Collect model names from h2/h3 tags and /library/* links
        model_names: set[str] = set()
        for elem in soup.find_all(['h2', 'h3']):
            name = elem.get_text(strip=True)
            if name and 2 < len(name) < 50:
                model_names.add(name)
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if re.match(r'^/[a-z][a-z0-9._-]+$', href) and '/' not in href[1:]:
                model_names.add(href.lstrip('/'))
            elif '/library/' in href:
                part = href.split('/library/')[-1].split('/')[0]
                if part:
                    model_names.add(part)
        for name in model_names:
            if name and len(name) > 2:
                scores[name] = 100.0
        log.info(f"  ✅ Accessibility: {len(scores)} models from Ollama library")
    except Exception as e:
        log.error(f"  ❌ Accessibility: {e}")
    return scores


def scrape_multi_model() -> dict[str, float]:
    """
    Multi-Model Support pillar.
    Source: OpenRouter rankings (most-used models by developers)
    Returns {model_name: pillar_score_0_to_100}
    """
    scores: dict[str, float] = {}
    try:
        log.info("Scraping Multi-Model Support pillar (OpenRouter rankings)...")
        text = playwright_get_innertext("https://openrouter.ai/rankings", wait_ms=10000)
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
        log.info(f"  ✅ Multi-Model Support: {len(scores)} models from OpenRouter")
    except Exception as e:
        log.error(f"  ❌ Multi-Model Support: {e}")
    return scores


# ══ SCORING ENGINE ════════════════════════════════════════════════

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
    s_stripped = s.split("/")[-1]   # strip org prefix: "openai/gpt-4o" → "gpt-4o"
    for name in existing:
        n = name.lower()
        if n == s or n == s_stripped:
            return name
    for name in existing:
        n = name.lower()
        if s in n or n in s or s_stripped in n or n in s_stripped:
            return name
    s_tok = set(s_stripped.replace("-", " ").replace("_", " ").split())
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
            "emoji":            "🤖",
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
        subprocess.run(["git", "add", "tragent-data.json", "status.json", "index.html"],
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
        notify("✅ <b>TRAgents DDP online</b>\nTelegram works! Ready to run.")
        print("Telegram test sent. Check your phone.")
        return

    mode = "DRY RUN 🔍" if DRY_RUN else "LIVE 🚀"
    log.info(f"TRAgents DDP | {TODAY} | {mode}")
    notify(f"🤖 <b>TRAgents DDP starting</b>\n📅 {TODAY}\n⚙️ {mode}\n6 pillars (22+ sources) → tragent-data.json")

    # ── Load data ──
    if not DATA_FILE.exists():
        msg = f"tragent-data.json not found at {DATA_FILE}"
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

    # ── Scrape all 6 pillars ──
    log.info("Scraping 6 pillars...")

    pillar_scrapers = {
        "task_completion":  scrape_task_completion,
        "cost_efficiency":  scrape_cost_efficiency,
        "tool_reliability": scrape_tool_reliability,
        "safety_security":  scrape_safety_security,
        "accessibility":    scrape_accessibility,
        "multi_model":      scrape_multi_model,
    }

    pillar_results: dict[str, dict[str, float]] = {}
    source_summary: list[str] = []

    for pillar_name, scraper_fn in pillar_scrapers.items():
        results = scraper_fn()
        pillar_results[pillar_name] = results
        source_summary.append(f"{pillar_name}: {len(results)} models")
        log.info(f"  {pillar_name}: {len(results)} models scraped")

    notify("📊 <b>Scraping complete</b>\n" + "\n".join(source_summary))

    # ── Match scraped names → canonical names, assign pillar scores ──
    model_pillar_scores: dict[str, dict[str, float]] = {name: {} for name in names}

    for pillar, results in pillar_results.items():
        matched = 0
        for scraped_name, score in results.items():
            canonical = match_name(scraped_name, names)
            if canonical:
                model_pillar_scores[canonical][pillar] = score
                matched += 1
        log.info(f"  {pillar}: {matched}/{len(results)} matched to canonical names")

    # ── Score each model ──
    for model in models:
        n = model["name"]
        pillar_scores = model_pillar_scores[n]

        # Count non-null pillars
        non_null_count = sum(1 for s in pillar_scores.values() if s is not None)

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

    # ── Qualification filter (3+ pillars) ──
    def today_score(m):
        s = m["scores"][today_idx] if today_idx < len(m["scores"]) else None
        return s if s is not None else -1.0

    model_pillar_counts = {
        m["name"]: sum(1 for s in model_pillar_scores[m["name"]].values() if s is not None)
        for m in models
    }

    qualified    = [m for m in models if model_pillar_counts.get(m["name"], 0) >= QUALIFICATION_MIN_PILLARS]
    disqualified = [m for m in models if model_pillar_counts.get(m["name"], 0) < QUALIFICATION_MIN_PILLARS]
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
    notify(f"🏆 <b>TRAgents Top 5 — {TODAY}</b>\n{top5_lines}")

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

    ok = git_push(f"TRAgents daily update {TODAY} ({len(qualified)} models)")
    if ok:
        notify(f"✅ <b>TRAgents DDP done!</b>\n📅 {TODAY}\n📊 {len(qualified)} models\n🌐 → trainingrun.ai/tragents")
    else:
        notify(f"⚠️ JSON updated but push failed. cd {REPO_PATH} && git push")


if __name__ == "__main__":
    main()
