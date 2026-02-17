#!/usr/bin/env python3
"""
TRSbench Real Scrapers -- V1.0
Scrapes live data from all 7 TRSbench source platforms.

Categories & Weights (M Bible V2.4):
  Safety (21%)        -- HELM Safety, MLCommons AI Luminate, Enkrypt AI, SafetyBench
  Reasoning (20%)     -- ARC-AGI-2
  Coding (20%)        -- SWE-bench Verified (50%), LiveCodeBench (25%), SciCode (15%), Legacy (10%)
  Human Pref (18%)    -- Chatbot Arena (LMSYS)
  Knowledge (8%)      -- MMLU-Pro (Open LLM Leaderboard)
  Efficiency (7%)     -- Artificial Analysis (tokens/s)
  Usage Adoption (6%) -- OpenRouter token share + SimilarWeb traffic

Discovery-first: Scrape ALL models from ALL platforms, then qualify (5-of-7 rule).
"""

import requests
import json
import re
import time
import traceback
from typing import Dict, Optional, Any, List, Tuple
from bs4 import BeautifulSoup
from datetime import datetime


# ---------------------------------------------------------
# Model Name Normalization
# ---------------------------------------------------------

# Maps raw platform names -> canonical TRSbench names
MODEL_ALIASES = {
    # Anthropic
    "claude-3.5-sonnet": "Claude Sonnet 4.5",
    "claude-3-5-sonnet": "Claude Sonnet 4.5",
    "claude-3-5-sonnet-20241022": "Claude Sonnet 4.5",
    "claude-sonnet-4-5-20250514": "Claude Sonnet 4.5",
    "claude-sonnet-4.5": "Claude Sonnet 4.5",
    "claude 3.5 sonnet": "Claude Sonnet 4.5",
    "claude sonnet 4.5": "Claude Sonnet 4.5",
    "claude-opus-4-5": "Claude Opus 4.5",
    "claude-opus-4.5": "Claude Opus 4.5",
    "claude opus 4.5": "Claude Opus 4.5",
    "claude-4-opus": "Claude Opus 4.5",
    "claude-opus-4-6": "Claude Opus 4.6",
    "claude-opus-4.6": "Claude Opus 4.6",
    "claude opus 4.6": "Claude Opus 4.6",
    # OpenAI
    "gpt-5": "GPT-5",
    "gpt-5.1": "GPT-5.1",
    "gpt-5.2": "GPT-5.2",
    "gpt-4o": "GPT-4o",
    "gpt-4.1": "GPT-4.1",
    "chatgpt-4o-latest": "GPT-4o",
    "o1": "o1",
    "o1-preview": "o1",
    "o3": "o3",
    "o3-mini": "o3-mini",
    "o4-mini": "o4-mini",
    # Google
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-3-pro": "Gemini 3 Pro",
    "gemini 3 pro": "Gemini 3 Pro",
    "gemini-3-flash": "Gemini 3 Flash",
    "gemini 3 flash": "Gemini 3 Flash",
    "gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    # xAI
    "grok-4": "Grok 4",
    "grok-4.1": "Grok 4.1",
    "grok 4.1": "Grok 4.1",
    "grok-3": "Grok 3",
    # DeepSeek
    "deepseek-v3": "DeepSeek V3",
    "deepseek-v3.2": "DeepSeek V3.2",
    "deepseek v3.2": "DeepSeek V3.2",
    "deepseek-r1": "DeepSeek R1",
    "deepseek r1": "DeepSeek R1",
    "deepseek-chat": "DeepSeek V3",
    "deepseek-reasoner": "DeepSeek R1",
    # Meta
    "llama-4-405b": "Llama 4 405B",
    "llama 4 405b": "Llama 4 405B",
    "llama-4-maverick": "Llama 4 Maverick",
    "meta-llama/llama-4-maverick": "Llama 4 Maverick",
    # Alibaba
    "qwen-2.5": "Qwen 2.5",
    "qwen 2.5": "Qwen 2.5",
    "qwen2.5": "Qwen 2.5",
    "qwen3-coder": "Qwen3-Coder",
    "qwen-3-coder": "Qwen3-Coder",
    # Zhipu AI
    "glm-5": "GLM-5",
    "glm-4.7": "GLM-4.7",
    "glm 4.7": "GLM-4.7",
    # Moonshot AI
    "kimi-k2": "Kimi K2",
    "kimi k2": "Kimi K2",
    # MiniMax
    "minimax-m2.1": "MiniMax M2.1",
    "minimax m2.1": "MiniMax M2.1",
    # Mistral
    "mistral-large": "Mistral Large",
    "mistral large": "Mistral Large",
    "mistral-large-latest": "Mistral Large",
}

# Model -> Company mapping
MODEL_COMPANIES = {
    "Claude Opus 4.6": "Anthropic",
    "Claude Opus 4.5": "Anthropic",
    "Claude Sonnet 4.5": "Anthropic",
    "GPT-5": "OpenAI",
    "GPT-5.1": "OpenAI",
    "GPT-5.2": "OpenAI",
    "GPT-4o": "OpenAI",
    "GPT-4.1": "OpenAI",
    "o1": "OpenAI",
    "o3": "OpenAI",
    "o3-mini": "OpenAI",
    "o4-mini": "OpenAI",
    "Gemini 3 Pro": "Google",
    "Gemini 3 Flash": "Google",
    "Gemini 2.5 Pro": "Google",
    "Gemini 2.5 Flash": "Google",
    "Gemini 2.0 Flash": "Google",
    "Grok 4": "xAI",
    "Grok 4.1": "xAI",
    "Grok 3": "xAI",
    "DeepSeek V3": "DeepSeek",
    "DeepSeek V3.2": "DeepSeek",
    "DeepSeek R1": "DeepSeek",
    "Llama 4 405B": "Meta",
    "Llama 4 Maverick": "Meta",
    "Qwen 2.5": "Alibaba",
    "Qwen3-Coder": "Alibaba",
    "GLM-5": "Zhipu AI",
    "GLM-4.7": "Zhipu AI",
    "Kimi K2": "Moonshot AI",
    "MiniMax M2.1": "MiniMax",
    "Mistral Large": "Mistral",
}


def normalize_model_name(raw_name: str) -> str:
    """Normalize a raw model name from any platform to canonical TRSbench name."""
    name = raw_name.strip()
    lower = name.lower()

    # Direct alias match
    if lower in MODEL_ALIASES:
        return MODEL_ALIASES[lower]

    # Check if it already IS a canonical name
    if name in MODEL_COMPANIES:
        return name

    # Try partial matching for common patterns
    for alias, canonical in MODEL_ALIASES.items():
        if alias in lower:
            return canonical

    # Return original if no match (will be logged for review)
    return name


def get_company(model_name: str) -> str:
    """Get company for a canonical model name."""
    return MODEL_COMPANIES.get(model_name, "Unknown")


# ---------------------------------------------------------
# CATEGORY 1: HUMAN PREFERENCE (18%) -- Chatbot Arena
# ---------------------------------------------------------

def scrape_chatbot_arena() -> Dict[str, float]:
    """
    Scrape Chatbot Arena ELO ratings from lmarena.ai.
    Source: Community-maintained JSON at GitHub (nakasyou/lmarena-history).
    Returns: {canonical_model_name: elo_score}
    """
    print("  [1/7] Scraping Chatbot Arena (Human Preference)...")

    url = "https://raw.githubusercontent.com/nakasyou/lmarena-history/main/output/scores.json"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Find the latest date entry
        if not data:
            print("    [WARN]  Empty response from Chatbot Arena history")
            return {}

        # Data is structured as: [{"date": "YYYY-MM-DD", "scores": {"category": {"models": {...}}}}]
        # Get the last entry (most recent)
        latest = data[-1] if isinstance(data, list) else data

        results = {}

        # Try to extract text.overall scores (primary ELO ratings)
        if isinstance(latest, dict):
            scores_data = latest.get("scores", latest)

            # Navigate to text.overall or just overall
            text_scores = scores_data.get("text", scores_data)
            if isinstance(text_scores, dict):
                overall = text_scores.get("overall", text_scores)
            else:
                overall = scores_data

            if isinstance(overall, dict):
                for raw_name, score_info in overall.items():
                    if isinstance(score_info, dict):
                        elo = score_info.get("rating", score_info.get("elo", score_info.get("score")))
                    elif isinstance(score_info, (int, float)):
                        elo = score_info
                    else:
                        continue

                    if elo is not None:
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = float(elo)

        print(f"    [OK] Found {len(results)} models on Chatbot Arena")
        return results

    except requests.RequestException as e:
        print(f"    [FAIL] Chatbot Arena request failed: {e}")
        return {}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"    [FAIL] Chatbot Arena parse error: {e}")
        traceback.print_exc()
        return {}


# ---------------------------------------------------------
# CATEGORY 2: CODING (20%) -- SWE-bench Verified + others
# ---------------------------------------------------------

def scrape_swebench() -> Dict[str, float]:
    """
    Scrape SWE-bench Verified scores from swebench.com.
    Data is embedded in HTML as <script id="leaderboard-data"> JSON.
    Returns: {canonical_model_name: resolved_percentage}
    """
    print("  [2/7] Scraping SWE-bench Verified (Coding)...")

    url = "https://www.swebench.com"

    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TrainingRunBot/1.0"
        })
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find the embedded leaderboard data
        script_tag = soup.find('script', id='leaderboard-data')
        if not script_tag or not script_tag.string:
            # Fallback: search all script tags for leaderboard JSON
            for script in soup.find_all('script'):
                if script.string and 'Verified' in (script.string or ''):
                    script_tag = script
                    break

        if not script_tag or not script_tag.string:
            print("    [WARN]  Could not find leaderboard data in SWE-bench HTML")
            return {}

        data = json.loads(script_tag.string)

        results = {}

        # Data structure: array of leaderboard entries
        # Filter for "Verified" benchmark
        entries = data if isinstance(data, list) else data.get('entries', data.get('leaderboard', []))

        for entry in entries:
            if isinstance(entry, dict):
                # Check if this is the "Verified" split
                benchmark_name = entry.get('name', entry.get('benchmark', entry.get('split', '')))

                # If entries are grouped by benchmark, filter for Verified
                if 'Verified' in str(benchmark_name) or 'verified' in str(benchmark_name).lower():
                    # Extract models from within this benchmark group
                    models = entry.get('models', entry.get('results', []))
                    for model in models:
                        raw_name = model.get('model', model.get('name', ''))
                        resolved = model.get('resolved', model.get('score', model.get('pass_rate')))
                        if raw_name and resolved is not None:
                            canonical = normalize_model_name(raw_name)
                            if canonical in MODEL_COMPANIES:
                                results[canonical] = float(resolved)

                # If flat list with a benchmark/split field
                elif entry.get('split') == 'verified' or entry.get('benchmark') == 'verified':
                    raw_name = entry.get('model', entry.get('name', ''))
                    resolved = entry.get('resolved', entry.get('score', entry.get('pass_rate')))
                    if raw_name and resolved is not None:
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = float(resolved)

                # Flat list -- just model + score (try to get all)
                elif 'model' in entry or 'name' in entry:
                    raw_name = entry.get('model', entry.get('name', ''))
                    resolved = entry.get('resolved', entry.get('score', entry.get('pass_rate', entry.get('% Resolved')
            continue

    print("    [WARN]  LiveCodeBench: No data extracted (will use null)")
    return {}


# ---------------------------------------------------------
# CATEGORY 3: REASONING (20%) -- ARC-AGI-2
# ---------------------------------------------------------

def scrape_arc_agi2() -> Dict[str, float]:
    """
    Scrape ARC-AGI-2 reasoning scores from arcprize.org.
    Clean JSON API: evaluations.json + models.json
    Filter: datasetId == "v2_Semi_Private"
    Returns: {canonical_model_name: score_pct}  (score * 100)
    """
    print("  [3/7] Scraping ARC-AGI-2 (Reasoning)...")

    evals_url = "https://arcprize.org/media/data/leaderboard/evaluations.json"
    models_url = "https://arcprize.org/media/data/leaderboard/models.json"

    try:
        # Fetch both endpoints
        evals_resp = requests.get(evals_url, timeout=30)
        evals_resp.raise_for_status()
        evaluations = evals_resp.json()

        models_resp = requests.get(models_url, timeout=30)
        models_resp.raise_for_status()
        models_data = models_resp.json()

        # Build model ID -> name lookup
        model_lookup = {}
        if isinstance(models_data, list):
            for m in models_data:
                model_lookup[m.get('id', m.get('modelId', ''))] = m.get('name', m.get('modelName', ''))
        elif isinstance(models_data, dict):
            for mid, minfo in models_data.items():
                if isinstance(minfo, dict):
                    model_lookup[mid] = minfo.get('name', mid)
                else:
                    model_lookup[mid] = str(minfo)

        results = {}

        # Filter evaluations for ARC-AGI-2 (v2_Semi_Private)
        if isinstance(evaluations, list):
            for ev in evaluations:
                dataset_id = ev.get('datasetId', ev.get('dataset_id', ''))
                if 'v2' in str(dataset_id).lower() or 'semi_private' in str(dataset_id).lower() or 'arc-agi-2' in str(dataset_id).lower():
                    model_id = ev.get('modelId', ev.get('model_id', ''))
                    score = ev.get('score', ev.get('accuracy'))

                    if score is not None:
                        # Convert to percentage if needed
                        score_pct = float(score) * 100 if float(score) <= 1 else float(score)

                        # Get model name
                        raw_name = model_lookup.get(model_id, model_id)
                        canonical = normalize_model_name(raw_name)

                        if canonical in MODEL_COMPANIES:
                            # Keep best score per model
                            if canonical not in results or score_pct > results[canonical]:
                                results[canonical] = score_pct

        print(f"    [OK] Found {len(results)} models on ARC-AGI-2")
        return results

    except requests.RequestException as e:
        print(f"    [FAIL] ARC-AGI-2 request failed: {e}")
        return {}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"    [FAIL] ARC-AGI-2 parse error: {e}")
        traceback.print_exc()
        return {}


# ---------------------------------------------------------
# CATEGORY 4: KNOWLEDGE (8%) -- MMLU-Pro
# ---------------------------------------------------------

def scrape_mmlu_pro() -> Dict[str, float]:
    """
    Scrape MMLU-Pro scores from Open LLM Leaderboard API.
    Endpoint: /api/leaderboard/formatted
    Returns: {canonical_model_name: mmlu_pro_score}
    """
    print("  [4/7] Scraping MMLU-Pro (Knowledge)...")

    url = "https://open-llm-leaderboard-open-llm-leaderboard.hf.space/api/leaderboard/formatted"

    try:
        resp = requests.get(url, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 TrainingRunBot/1.0"
        })
        resp.raise_for_status()
        data = resp.json()

        results = {}

        # Parse the structured response
        models_list = data if isinstance(data, list) else data.get('models', data.get('data', []))

        for entry in models_list:
            if not isinstance(entry, dict):
                continue

            # Get model name
            model_info = entry.get('model', {})
            if isinstance(model_info, dict):
                raw_name = model_info.get('name', model_info.get('fullname', ''))
            else:
                raw_name = str(model_info)

            if not raw_name:
                raw_name = entry.get('Model', entry.get('fullname', entry.get('name', '')))

            # Get MMLU-Pro score
            evals = entry.get('evaluations', {})
            if isinstance(evals, dict):
                mmlu_info = evals.get('mmlu_pro', evals.get('MMLU-PRO', {}))
                if isinstance(mmlu_info, dict):
                    score = mmlu_info.get('value', mmlu_info.get('score'))
                elif isinstance(mmlu_info, (int, float)):
                    score = mmlu_info
                else:
                    score = None
            else:
                score = entry.get('MMLU-PRO', entry.get('MMLU-PRO Raw', entry.get('mmlu_pro')))

            if raw_name and score is not None:
                canonical = normalize_model_name(raw_name)
                if canonical in MODEL_COMPANIES:
                    results[canonical] = float(score)

        print(f"    [OK] Found {len(results)} models on MMLU-Pro")
        return results

    except requests.RequestException as e:
        print(f"    [FAIL] MMLU-Pro request failed: {e}")
        # Fallback: try Artificial Analysis MMLU-Pro page
        return _scrape_mmlu_pro_fallback()
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"    [FAIL] MMLU-Pro parse error: {e}")
        return _scrape_mmlu_pro_fallback()


def _scrape_mmlu_pro_fallback() -> Dict[str, float]:
    """Fallback: scrape MMLU-Pro from Artificial Analysis."""
    print("    [REFRESH] Trying Artificial Analysis MMLU-Pro fallback...")
    try:
        resp = requests.get("https://artificialanalysis.ai/evaluations/mmlu-pro", timeout=30, headers={
            "User-Agent": "Mozilla/5.0 TrainingRunBot/1.0"
        })
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = {}
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        raw_name = cells[0].get_text(strip=True)
                        try:
                            score = float(cells[-1].get_text(strip=True).replace('%', ''))
                        except ValueError:
                            continue
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = score
            if results:
                print(f"    [OK] Fallback found {len(results)} models")
            return results
    except Exception:
        pass
    return {}


# ---------------------------------------------------------
# CATEGORY 5: EFFICIENCY (7%) -- Artificial Analysis
# ---------------------------------------------------------

def scrape_artificial_analysis() -> Dict[str, float]:
    """
    Scrape Artificial Analysis for efficiency data (tokens/s).
    Source: artificialanalysis.ai/leaderboards/models
    Returns: {canonical_model_name: tokens_per_second}
    """
    print("  [5/7] Scraping Artificial Analysis (Efficiency)...")

    url = "https://artificialanalysis.ai/leaderboards/models"

    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 TrainingRunBot/1.0"
        })
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = {}

        # Look for embedded JSON data first (Next.js __NEXT_DATA__ or similar)
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data and next_data.string:
            try:
                nd = json.loads(next_data.string)
                # Navigate through Next.js data structure to find model data
                props = nd.get('props', {}).get('pageProps', {})
                models = props.get('models', props.get('leaderboard', props.get('data', [])))

                if isinstance(models, list):
                    for m in models:
                        if isinstance(m, dict):
                            raw_name = m.get('name', m.get('model_name', m.get('model', '')))
                            tps = m.get('median_tokens_per_second', m.get('tokens_per_second',
                                       m.get('speed', m.get('output_speed'))))
                            if raw_name and tps is not None:
                                canonical = normalize_model_name(raw_name)
                                if canonical in MODEL_COMPANIES:
                                    results[canonical] = float(tps)

                if results:
                    print(f"    [OK] Found {len(results)} models on Artificial Analysis (JSON)")
                    return results
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse HTML tables
        for table in soup.find_all('table'):
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            # Find the tokens/s column
            speed_col = None
            name_col = 0
            for i, h in enumerate(headers):
                if 'token' in h and ('s' in h or 'speed' in h or 'second' in h):
                    speed_col = i
                elif 'model' in h or 'name' in h:
                    name_col = i

            if speed_col is None:
                # Try to find a column with numeric speed data
                for i, h in enumerate(headers):
                    if 'speed' in h or 'throughput' in h or 'median' in h:
                        speed_col = i

            if speed_col is not None:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > max(name_col, speed_col):
                        raw_name = cells[name_col].get_text(strip=True)
                        try:
                            tps_text = cells[speed_col].get_text(strip=True)
                            tps = float(re.sub(r'[^\d.]', '', tps_text))
                        except (ValueError, IndexError):
                            continue
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = tps

        print(f"    [OK] Found {len(results)} models on Artificial Analysis")
        return results

    except requests.RequestException as e:
        print(f"    [FAIL] Artificial Analysis request failed: {e}")
        return {}
    except Exception as e:
        print(f"    [FAIL] Artificial Analysis parse error: {e}")
        traceback.print_exc()
        return {}


# ---------------------------------------------------------
# CATEGORY 6: USAGE ADOPTION (6%) -- OpenRouter + SimilarWeb
# ---------------------------------------------------------

def scrape_openrouter() -> Dict[str, float]:
    """
    Scrape OpenRouter for usage/adoption data.
    API: /api/v1/models (model metadata)
    Rankings page: HTML scraping for token usage
    Returns: {canonical_model_name: token_share_pct}
    """
    print("  [6/7] Scraping OpenRouter (Usage Adoption)...")

    results = {}

    # Part 1: Get model list from API
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
        resp.raise_for_status()
        data = resp.json()

        models = data.get('data', [])
        print(f"    [CHART] OpenRouter API returned {len(models)} models")

        # We can't get usage data from the API directly, but we know which models exist
        known_models = set()
        for m in models:
            raw_id = m.get('id', '')
            canonical = normalize_model_name(raw_id)
            if canonical in MODEL_COMPANIES:
                known_models.add(canonical)

    except Exception as e:
        print(f"    [WARN]  OpenRouter API failed: {e}")
        known_models = set()

    # Part 2: Scrape rankings page for actual usage data
    try:
        resp = requests.get("https://openrouter.ai/rankings", timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TrainingRunBot/1.0"
        })
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Look for embedded JSON data
            for script in soup.find_all('script'):
                if script.string and ('ranking' in script.string.lower() or 'token' in script.string.lower()):
                    try:
                        # Try to extract JSON data
                        json_matches = re.findall(r'\{[^{}]*"(?:model|name|id)"[^{}]*"(?:tokens|usage|count)"[^{}]*\}', script.string)
                        for match in json_matches:
                            try:
                                entry = json.loads(match)
                                raw_name = entry.get('model', entry.get('name', entry.get('id', '')))
                                tokens = entry.get('tokens', entry.get('usage', entry.get('count', 0)))
                                canonical = normalize_model_name(raw_name)
                                if canonical in MODEL_COMPANIES and tokens:
                                    results[canonical] = float(tokens)
                            except json.JSONDecodeError:
                                continue
                    except Exception:
                        continue

            # Try Next.js data
            next_data = soup.find('script', id='__NEXT_DATA__')
            if next_data and next_data.string and not results:
                try:
                    nd = json.loads(next_data.string)
                    rankings = nd.get('props', {}).get('pageProps', {}).get('rankings', [])
                    if isinstance(rankings, list):
                        for entry in rankings:
                            if isinstance(entry, dict):
                                raw_name = entry.get('model', entry.get('id', ''))
                                tokens = entry.get('total_tokens', entry.get('tokens', entry.get('usage')))
                                canonical = normalize_model_name(raw_name)
                                if canonical in MODEL_COMPANIES and tokens:
                                    results[canonical] = float(tokens)
                except (json.JSONDecodeError, KeyError):
                    pass

    except Exception as e:
        print(f"    [WARN]  OpenRouter rankings scrape failed: {e}")

    # Part 3: SimilarWeb free API for traffic data (supplementary)
    try:
        ai_domains = {
            "claude.ai": ["Claude Opus 4.6", "Claude Opus 4.5", "Claude Sonnet 4.5"],
            "chatgpt.com": ["GPT-5.2", "GPT-5.1", "GPT-5", "GPT-4o"],
            "gemini.google.com": ["Gemini 3 Pro", "Gemini 3 Flash"],
            "grok.com": ["Grok 4.1"],
            "chat.deepseek.com": ["DeepSeek V3.2", "DeepSeek R1"],
        }

        traffic_data = {}
        for domain, model_list in ai_domains.items():
            try:
                sw_resp = requests.get(
                    f"https://data.similarweb.com/api/v1/data?domain={domain}",
                    timeout=15
                )
                if sw_resp.status_code == 200:
                    sw_data = sw_resp.json()
                    visits = sw_data.get("Engagments", {}).get("Visits", 0)
                    if visits:
                        # Split traffic evenly among models from that domain
                        per_model = visits / len(model_list)
                        for model in model_list:
                            traffic_data[model] = per_model
                time.sleep(1)  # Rate limit
            except Exception:
                continue

        # If we got SimilarWeb data but not OpenRouter, use traffic as proxy
        if traffic_data and not results:
            results = traffic_data
            print(f"    [CHART] Using SimilarWeb traffic data for {len(results)} models")
        elif traffic_data:
            # Blend OpenRouter tokens with SimilarWeb traffic
            for model, traffic in traffic_data.items():
                if model not in results:
                    results[model] = traffic

    except Exception as e:
        print(f"    [WARN]  SimilarWeb fallback failed: {e}")

    print(f"    [OK] Found {len(results)} models with usage data")
    return results


# ---------------------------------------------------------
# CATEGORY 7: SAFETY (21%) -- Multiple sources
# ---------------------------------------------------------

def scrape_safety() -> Dict[str, float]:
    """
    Scrape safety benchmark data from multiple sources:
    - HELM Safety (crfm.stanford.edu)
    - MLCommons AI Luminate (ailuminate.mlcommons.org)
    - Enkrypt AI (leaderboard.enkryptai.com)
    - SafetyBench (llmbench.ai/safety)

    Sub-weights per M Bible V2.4:
      Harm Avoidance (40%) -- HELM Safety
      Fairness (30%) -- TrustLLM (approximated from available data)
      Misuse Prevention (20%) -- MLCommons AI Luminate
      Governance (10%) -- AI Safety Index, Enkrypt AI

    Returns: {canonical_model_name: composite_safety_score}
    """
    print("  [7/7] Scraping Safety Benchmarks...")

    # Collect scores from multiple sources
    helm_scores = _scrape_helm_safety()
    luminate_scores = _scrape_mlcommons_luminate()
    enkrypt_scores = _scrape_enkrypt_ai()
    safetybench_scores = _scrape_safetybench()

    # Combine all safety sources into composite
    all_models = set()
    all_models.update(helm_scores.keys())
    all_models.update(luminate_scores.keys())
    all_models.update(enkrypt_scores.keys())
    all_models.update(safetybench_scores.keys())

    results = {}
    for model in all_models:
        if model not in MODEL_COMPANIES:
            continue

        scores = []
        weights = []

        # Harm Avoidance (40%) -- HELM Safety
        if model in helm_scores:
            scores.append(helm_scores[model])
            weights.append(0.40)

        # Fairness (30%) -- SafetyBench as proxy for TrustLLM
        if model in safetybench_scores:
            scores.append(safetybench_scores[model])
            weights.append(0.30)

        # Misuse Prevention (20%) -- MLCommons AI Luminate
        if model in luminate_scores:
            scores.append(luminate_scores[model])
            weights.append(0.20)

        # Governance (10%) -- Enkrypt AI
        if model in enkrypt_scores:
            scores.append(enkrypt_scores[model])
            weights.append(0.10)

        if scores:
            # Proportional normalization for missing sub-sources
            total_weight = sum(weights)
            composite = sum(s * w for s, w in zip(scores, weights)) / total_weight
            results[model] = composite

    print(f"    [OK] Found {len(results)} models with safety data")
    return results


def _scrape_helm_safety() -> Dict[str, float]:
    """Scrape HELM Safety scores from Stanford CRFM."""
    print("    [7a] Probing HELM Safety...")

    # Try the static JSON endpoint
    urls_to_try = [
        "https://crfm.stanford.edu/helm/safety/v1.0.0/benchmark_output/runs/safety/groups.json",
        "https://crfm.stanford.edu/helm/safety/latest/benchmark_output/runs/safety/groups.json",
    ]

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                results = {}
                # Parse HELM groups.json format
                if isinstance(data, list):
                    for group in data:
                        if isinstance(group, dict):
                            rows = group.get('rows', [])
                            for row in rows:
                                if isinstance(row, dict):
                                    raw_name = row.get('model', row.get('name', ''))
                                    # HELM uses various metric names
                                    score = row.get('safety_score', row.get('score', row.get('mean')))
                                    if raw_name and score is not None:
                                        canonical = normalize_model_name(raw_name)
                                        if canonical in MODEL_COMPANIES:
                                            # Normalize to 0-100 (HELM sometimes uses 0-1)
                                            s = float(score)
                                            results[canonical] = s * 100 if s <= 1 else s

                if results:
                    print(f"      [OK] HELM Safety: {len(results)} models")
                    return results
        except Exception:
            continue

    print("      [WARN]  HELM Safety: Could not access (will use other safety sources)")
    return {}


def _scrape_mlcommons_luminate() -> Dict[str, float]:
    """Scrape MLCommons AI Luminate safety grades."""
    print("    [7b] Probing MLCommons AI Luminate...")

    try:
        resp = requests.get("https://ailuminate.mlcommons.org/benchmarks/", timeout=20, headers={
            "User-Agent": "Mozilla/5.0 TrainingRunBot/1.0"
        })
        if resp.status_code != 200:
            print(f"      [WARN]  MLCommons returned {resp.status_code}")
            return {}

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = {}

        # Try __NEXT_DATA__ first
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data and next_data.string:
            try:
                nd = json.loads(next_data.string)
                props = nd.get('props', {}).get('pageProps', {})
                # Navigate to benchmark data
                benchmarks = props.get('benchmarks', props.get('results', props.get('models', [])))

                if isinstance(benchmarks, list):
                    for entry in benchmarks:
                        if isinstance(entry, dict):
                            raw_name = entry.get('model', entry.get('name', ''))
                            grade = entry.get('grade', entry.get('overall_grade', entry.get('score', '')))

                            # Convert letter grade to numeric
                            grade_map = {
                                'Excellent': 95, 'Very Good': 85, 'Good': 75,
                                'Fair': 60, 'Poor': 40,
                                'A+': 97, 'A': 93, 'A-': 90,
                                'B+': 87, 'B': 83, 'B-': 80,
                                'C+': 77, 'C': 73, 'C-': 70,
                                'D+': 67, 'D': 63, 'D-': 60,
                                'F': 50
                            }

                            if raw_name and grade:
                                score = grade_map.get(str(grade), None)
                                if score is None and isinstance(grade, (int, float)):
                                    score = float(grade)
                                if score is not None:
                                    canonical = normalize_model_name(raw_name)
                                    if canonical in MODEL_COMPANIES:
                                        results[canonical] = score

                if results:
                    print(f"      [OK] MLCommons: {len(results)} models")
                    return results
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse HTML
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    raw_name = cells[0].get_text(strip=True)
                    grade_text = cells[-1].get_text(strip=True)
                    grade_map = {'Excellent': 95, 'Very Good': 85, 'Good': 75, 'Fair': 60, 'Poor': 40}
                    score = grade_map.get(grade_text)
                    if raw_name and score is not None:
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = score

        print(f"      {'[OK]' if results else '[WARN]'} MLCommons: {len(results)} models")
        return results

    except Exception as e:
        print(f"      [WARN]  MLCommons failed: {e}")
        return {}


def _scrape_enkrypt_ai() -> Dict[str, float]:
    """Scrape Enkrypt AI safety leaderboard."""
    print("    [7c] Probing Enkrypt AI...")

    try:
        resp = requests.get("https://leaderboard.enkryptai.com/", timeout=20, headers={
            "User-Agent": "Mozilla/5.0 TrainingRunBot/1.0"
        })
        if resp.status_code != 200:
            print(f"      [WARN]  Enkrypt AI returned {resp.status_code}")
            return {}

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = {}

        # Try embedded JSON data
        for script in soup.find_all('script'):
            if script.string and ('rating' in script.string.lower() or 'nist' in script.string.lower()):
                try:
                    # Look for JSON arrays with model data
                    json_match = re.search(r'(\[{.*?}\])', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        for entry in data:
                            if isinstance(entry, dict):
                                raw_name = entry.get('model', entry.get('name', ''))
                                # Enkrypt AI rating is 0-5 (higher = safer)
                                rating = entry.get('enkrypt_rating', entry.get('rating', entry.get('score')))
                                if raw_name and rating is not None:
                                    # Normalize 0-5 to 0-100
                                    score = (float(rating) / 5.0) * 100
                                    canonical = normalize_model_name(raw_name)
                                    if canonical in MODEL_COMPANIES:
                                        results[canonical] = score
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Try Next.js data
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data and next_data.string and not results:
            try:
                nd = json.loads(next_data.string)
                leaderboard = nd.get('props', {}).get('pageProps', {}).get('leaderboard', [])
                for entry in leaderboard:
                    if isinstance(entry, dict):
                        raw_name = entry.get('model', entry.get('name', ''))
                        rating = entry.get('enkrypt_rating', entry.get('rating'))
                        if raw_name and rating is not None:
                            score = (float(rating) / 5.0) * 100
                            canonical = normalize_model_name(raw_name)
                            if canonical in MODEL_COMPANIES:
                                results[canonical] = score
            except (json.JSONDecodeError, KeyError):
                pass

        print(f"      {'[OK]' if results else '[WARN]'} Enkrypt AI: {len(results)} models")
        return results

    except Exception as e:
        print(f"      [WARN]  Enkrypt AI failed: {e}")
        return {}


def _scrape_safetybench() -> Dict[str, float]:
    """Scrape SafetyBench scores from llmbench.ai/safety."""
    print("    [7d] Probing SafetyBench...")

    try:
        resp = requests.get("https://llmbench.ai/safety", timeout=20, headers={
            "User-Agent": "Mozilla/5.0 TrainingRunBot/1.0"
        })
        if resp.status_code != 200:
            print(f"      [WARN]  SafetyBench returned {resp.status_code}")
            return {}

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = {}

        # Try to find leaderboard data in script tags
        for script in soup.find_all('script'):
            if script.string and ('safety' in script.string.lower() or 'model' in script.string.lower()):
                try:
                    json_match = re.search(r'(?:data|results|models)\s*[:=]\s*(\[.*?\])', script.string, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        for entry in data:
                            if isinstance(entry, dict):
                                raw_name = entry.get('model', entry.get('name', ''))
                                score = entry.get('score', entry.get('avg', entry.get('safety_score')))
                                if raw_name and score is not None:
                                    canonical = normalize_model_name(raw_name)
                                    if canonical in MODEL_COMPANIES:
                                        results[canonical] = float(score)
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Fallback: parse HTML tables
        if not results:
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        raw_name = cells[0].get_text(strip=True)
                        try:
                            score = float(cells[-1].get_text(strip=True).replace('%', ''))
                        except ValueError:
                            # Try second column
                            try:
                                score = float(cells[1].get_text(strip=True).replace('%', ''))
                            except ValueError:
                                continue
                        canonical = normalize_model_name(raw_name)
                        if canonical in MODEL_COMPANIES:
                            results[canonical] = score

        print(f"      {'[OK]' if results else '[WARN]'} SafetyBench: {len(results)} models")
        return results

    except Exception as e:
        print(f"      [WARN]  SafetyBench failed: {e}")
        return {}


# ---------------------------------------------------------
# MASTER SCRAPE FUNCTION
# ---------------------------------------------------------

def scrape_all() -> Dict[str, Dict[str, Optional[float]]]:
    """
    Run all 7 category scrapers and return combined results.
    Returns: {
        model_name: {
            "human_preference": float|None,
            "coding": float|None,
            "reasoning": float|None,
            "knowledge": float|None,
            "efficiency": float|None,
            "usage_adoption": float|None,
            "safety": float|None,
            "company": str
        }
    }
    """
    print("=" * 60)
    print(f"  TRSbench Daily Scrape -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Run all scrapers
    arena_data = scrape_chatbot_arena()
    swebench_data = scrape_swebench()
    livecodebench_data = scrape_livecodebench()
    arc_data = scrape_arc_agi2()
    mmlu_data = scrape_mmlu_pro()
    aa_data = scrape_artificial_analysis()
    usage_data = scrape_openrouter()
    safety_data = scrape_safety()

    # Compute blended coding score per M Bible:
    # SWE-bench Verified (50%) + LiveCodeBench (25%) + SciCode (15%) + Legacy (10%)
    # For now: SWE-bench primary, LiveCodeBench supplementary
    coding_data = {}
    all_coding_models = set(swebench_data.keys()) | set(livecodebench_data.keys())
    for model in all_coding_models:
        swe = swebench_data.get(model)
        lcb = livecodebench_data.get(model)

        if swe is not None and lcb is not None:
            # Blend: SWE-bench 67% + LiveCodeBench 33% (proportional since SciCode/Legacy missing)
            coding_data[model] = swe * 0.67 + lcb * 0.33
        elif swe is not None:
            coding_data[model] = swe
        elif lcb is not None:
            coding_data[model] = lcb

    # Combine into master model dictionary
    all_models = set()
    all_models.update(arena_data.keys())
    all_models.update(coding_data.keys())
    all_models.update(arc_data.keys())
    all_models.update(mmlu_data.keys())
    all_models.update(aa_data.keys())
    all_models.update(usage_data.keys())
    all_models.update(safety_data.keys())

    combined = {}
    for model in all_models:
        if model not in MODEL_COMPANIES:
            continue

        combined[model] = {
            "human_preference": arena_data.get(model),
            "coding": coding_data.get(model),
            "reasoning": arc_data.get(model),
            "knowledge": mmlu_data.get(model),
            "efficiency": aa_data.get(model),
            "usage_adoption": usage_data.get(model),
            "safety": safety_data.get(model),
            "company": MODEL_COMPANIES[model],
        }

    # Summary
    print("\n" + "=" * 60)
    print("  DISCOVERY SUMMARY")
    print("=" * 60)

    for model, cats in sorted(combined.items()):
        non_null = sum(1 for k, v in cats.items() if k != "company" and v is not None)
        qualified = "[OK]" if non_null >= 5 else "[FAIL]"
        print(f"  {qualified} {model} ({cats['company']}) -- {non_null}/7 categories")

    print(f"\n  Total models discovered: {len(combined)}")
    qualified_count = sum(1 for cats in combined.values()
                         if sum(1 for k, v in cats.items() if k != "company" and v is not None) >= 5)
    print(f"  Qualified (5+ categories): {qualified_count}")
    print("=" * 60)

    return combined


if __name__ == "__main__":
    results = scrape_all()

    # Print detailed results
    print("\n[CHART] DETAILED RESULTS:")
    print("-" * 80)
    for model, data in sorted(results.items()):
        print(f"\n{model} ({data['company']}):")
        for cat in ["safety", "reasoning", "coding", "human_preference", "knowledge", "efficiency", "usage_adoption"]:
            val = data[cat]
            print(f"  {cat:20s}: {val if val is not None else 'NULL'}")
