"""
model_names.py — Central canonical model name registry for Training Run agents.

All 5 agents (agent_trs, agent_truscore, agent_trscode, agent_trfcast, agent_tragents)
import canonicalize() and match_name() from here instead of maintaining their own
logic. This ensures a single source of truth for model identity across all DDPs.

Usage in agents:
    from model_names import canonicalize, match_name
"""

import re

# ── Canonical model names (authoritative display names) ─────────────────────
# These are the names shown on the leaderboard. Scrapers map TO these.
CANONICAL_ROSTER = [
    # Anthropic
    "Claude Opus 4.6",
    "Claude Opus 4.5",
    "Claude Opus 4.1",
    "Claude Sonnet 4.6",
    "Claude Sonnet 4.5",
    "Claude Code",
    "Claude 3 Haiku",
    "Claude 2.1",
    # OpenAI
    "GPT-5.2",
    "GPT-5.1",
    "GPT-5",
    "GPT-5 mini",
    "GPT-4",
    "GPT-4o",
    "GPT-4.5",
    "GPT-3.5 Turbo",
    "O3",
    "o3-mini",
    "o4-mini",
    "o1-preview",
    "o1-mini",
    "gpt-oss-120b",
    # Google / DeepMind
    "Gemini 3 Pro",
    "Gemini 3 Flash",
    "Gemini 2.5 Pro",
    "Gemini Flash 3",
    "Gemma 3 12B",
    "Palmyra X5",
    "Palmyra-X-004",
    "Palmyra Fin",
    "Palmyra Med",
    # xAI
    "Grok 4.20",
    "Grok 4.1",
    "Grok 3 Beta",
    # DeepSeek
    "DeepSeek V3.2",
    "DeepSeek V3.1",
    "DeepSeek-V3",
    "DeepSeek R1",
    "DeepSeek LLM Chat",
    # Zhipu AI
    "GLM-5",
    "GLM-4",
    # Meta
    "Llama 4.08B",
    "Llama 4.05B",
    "Llama 4.0",
    "Llama 4 Maverick",
    "Llama 3.1 Instruct Turbo",
    # Mistral AI
    "Mistral Large 3",
    "Mistral Large",
    "Mistral Voxtral",
    "Devstral 2",
    "Mixtral Instruct",
    "Mistral Instruct v0.3",
    # Alibaba
    "Qwen3-Coder",
    "Qwen3",
    "Qwen2.5",
    "Qwen2 Instruct",
    "Qwen1.5 Chat",
    "qwq-32b",
    # MiniMax
    "MiniMax M2.5",
    "MiniMax M2",
    "MiniMax M1",
    # Moonshot AI
    "Kimi K2.5",
    "Kimi K2 Instruct",
    # Cohere
    "Cohere Command R+",
    "Command R Plus",
    "Cohere Aya",
    # PrimeIntellect / AI2 / others
    "intellect-3",
    "BLACKBOXAI",
    "INTELLECT-3",
    "K-EXAONE",
    "NVARC",
    "IBM Granite 3.3 8B Instruct",
    "Amazon Nova Lite",
    "Gemma 3 12B",
]

# ── Explicit alias map ───────────────────────────────────────────────────────
# Keys are lowercase. Values are canonical names.
# Covers: emoji prefixes, short Claude names, casing variants, raw API names,
# version-number formats, and source-specific quirks.
ALIASES: dict[str, str] = {
    # ── Claude: missing "Claude " prefix (Rallies, ForecastBench) ──
    "opus 4.6":                               "Claude Opus 4.6",
    "opus 4.5":                               "Claude Opus 4.5",
    "opus 4.1":                               "Claude Opus 4.1",
    "sonnet 4.6":                             "Claude Sonnet 4.6",
    "sonnet 4.5":                             "Claude Sonnet 4.5",
    "haiku 4.5":                              "Claude 3 Haiku",
    # ── Claude: raw API model IDs ──
    "claude-opus-4-6":                        "Claude Opus 4.6",
    "claude-opus-4-5":                        "Claude Opus 4.5",
    "claude-sonnet-4-6":                      "Claude Sonnet 4.6",
    "claude-sonnet-4-5":                      "Claude Sonnet 4.5",
    "claude-haiku-4-5-20251001 (zero shot)":  "Claude 3 Haiku",
    "claude-haiku-4-5-20251001":              "Claude 3 Haiku",
    "claude-haiku-4.5-20251001":              "Claude 3 Haiku",
    # ── OpenAI: spacing / dash variants ──
    "gpt 5.2":                                "GPT-5.2",
    "gpt5.2":                                 "GPT-5.2",
    "gpt 5.1":                                "GPT-5.1",
    "gpt5.1":                                 "GPT-5.1",
    "gpt 5 mini":                             "GPT-5 mini",
    "gpt-5 mini":                             "GPT-5 mini",
    "gpt5 mini":                              "GPT-5 mini",
    "gpt 5.2 codex":                          "GPT-5.2",
    "gpt-5.2 codex":                          "GPT-5.2",
    "gpt-5-codex":                            "GPT-5.2",
    "chatgpt-4o-latest":                      "GPT-4o",
    "gpt-4o-2024-11-20":                      "GPT-4o",
    "gpt-4.5-preview-2025-02-27 (scratchpad)":"GPT-4.5",
    "gpt-4.5-preview":                        "GPT-4.5",
    "gpt-4.1 (2025-04-14)":                   "GPT-4",
    "gpt-4 turbo":                            "GPT-4",
    "gpt-4-turbo":                            "GPT-4",
    "gpt 4.1 mini":                           "GPT-4",
    "gpt-4.1 mini":                           "GPT-4",
    "gpt-oss-120b":                           "gpt-oss-120b",
    "gpt oss 120b":                           "gpt-oss-120b",
    "gpt-oss-120b (2506)":                    "gpt-oss-120b",
    "gpt oss 120b (2506)":                    "gpt-oss-120b",
    # ── OpenAI: o-series ──
    "o3":                                     "O3",
    "openai o3":                              "O3",
    "openai-o3":                              "O3",
    "o3 mini":                                "o3-mini",
    "openai o3-mini":                         "o3-mini",
    "o4 mini":                                "o4-mini",
    "openai o4-mini":                         "o4-mini",
    "openai o1 mini":                         "o1-mini",
    "openai o1-mini":                         "o1-mini",
    "openai o1 preview":                      "o1-preview",
    "openai o1-preview":                      "o1-preview",
    # ── Google Gemini ──
    "gemini-3-pro":                           "Gemini 3 Pro",
    "gemini-3-flash":                         "Gemini 3 Flash",
    "gemini-2.5-pro":                         "Gemini 2.5 Pro",
    "gemini-flash-3":                         "Gemini Flash 3",
    "gemini flash 3.0":                       "Gemini Flash 3",
    "gemini-3.0-flash":                       "Gemini Flash 3",
    # ── xAI Grok ──
    "grok-4":                                 "Grok 4.20",
    "grok 4":                                 "Grok 4.20",
    "grok4":                                  "Grok 4.20",
    "grok-4.20":                              "Grok 4.20",
    "grok 4.1":                               "Grok 4.1",
    "grok 3":                                 "Grok 3 Beta",
    "grok-3":                                 "Grok 3 Beta",
    "grok3":                                  "Grok 3 Beta",
    "grok-3-beta":                            "Grok 3 Beta",
    # ── DeepSeek ──
    "deepseek-v3":                            "DeepSeek-V3",
    "deepseek v3":                            "DeepSeek-V3",
    "deepseekv3":                             "DeepSeek-V3",
    "deepseek-r1 (scratchpad)":               "DeepSeek R1",
    "deepseek-r1":                            "DeepSeek R1",
    "deepseek r1":                            "DeepSeek R1",
    "deepseek-r1-zero":                       "DeepSeek R1",
    # ── Qwen / Alibaba ──
    "qwen3-max":                              "Qwen3",
    "qwen 3":                                 "Qwen3",
    "qwen3 30b a3b":                          "Qwen3",
    "qwen3-coder 480b/a35b instruct":         "Qwen3-Coder",
    "qwq-32b":                                "qwq-32b",
    "qwq 32b":                                "qwq-32b",
    # ── MiniMax ──
    "minimax m1 40k":                         "MiniMax M1",
    "minimax-m1-40k":                         "MiniMax M1",
    # ── Kimi ──
    "kimi-k2-thinking":                       "Kimi K2.5",
    "kimi k2 thinking":                       "Kimi K2.5",
    "kimi k2.5":                              "Kimi K2.5",
    "kimi-k2.5":                              "Kimi K2.5",
    # ── Mistral ──
    "devstral (2512)":                        "Devstral 2",
    "devstral":                               "Devstral 2",
    "mistral-large":                          "Mistral Large",
    # ── Cohere ──
    "command r+":                             "Cohere Command R+",
    "command-r+":                             "Cohere Command R+",
    "command a":                              "Command R Plus",
    # ── Llama ──
    "llama 4 maverick instruct":              "Llama 4 Maverick",
    "llama-4-maverick":                       "Llama 4 Maverick",
    "meta-llama/llama-4-maverick":            "Llama 4 Maverick",
    # ── Misc scraped format quirks ──
    "magistral medium":                       "Mistral Large",   # Magistral is Mistral
    "intellect 3":                            "intellect-3",
    "intellect-3":                            "intellect-3",
    # ── GPT-4.5 long raw API names ──
    "gpt-4.5-preview-2025-02-27":             "GPT-4.5",
    "gpt-4.5-preview":                        "GPT-4.5",
    # ── Qwen large instruct variants → base name ──
    "qwen3-coder 480b/a35b instruct":         "Qwen3-Coder",
    "qwen3 coder 480b/a35b instruct":         "Qwen3-Coder",
    # ── Claude Haiku variants ──
    "claude 4.5 haiku":                       "Claude 3 Haiku",
    "claude haiku 4.5":                       "Claude 3 Haiku",
    "claude 4.5 haiku (high reasoning)":      "Claude 3 Haiku",
    # ── Amazon ──
    "nova-pro-v1:0":                          "Amazon Nova Lite",
    "amazon/nova-pro-v1:0":                   "Amazon Nova Lite",
}


def _strip_noise(name: str) -> str:
    """Remove emoji prefixes, org-path prefixes (org/model), and common
    raw-API suffixes like '(zero shot)', '(scratchpad)', '(thinking)'."""
    # Strip leading emoji / non-ASCII decoration (e.g. 🆕, ✅)
    s = re.sub(r'^[\U00010000-\U0010ffff\U00002600-\U000027BF\U0001F300-\U0001FAFF]+\s*', '', name)
    # Strip org prefix ONLY when it looks like a pure lowercase slug
    # e.g. "anthropic/claude-opus-4-6" → "claude-opus-4-6"
    # but NOT "Qwen3-Coder 480B/A35B Instruct" (has uppercase / spaces before /)
    if '/' in s:
        before, after = s.split('/', 1)
        if re.match(r'^[a-z0-9\-_]+$', before):   # org-slug pattern only
            s = after
    # Strip trailing raw-API suffixes
    s = re.sub(r'\s*\((zero shot|scratchpad|thinking|high reasoning)\)\s*$', '', s, flags=re.IGNORECASE)
    return s.strip()


def _normalize(name: str) -> str:
    """Lowercase, collapse whitespace, normalize dashes/underscores for fuzzy
    token-overlap matching. Does NOT alter the displayed name."""
    s = _strip_noise(name).lower()
    s = s.replace('_', ' ').replace('-', ' ')
    # Normalize version separators: "4-5" → "4.5", "v3" → "3"
    s = re.sub(r'(\d)\s*-\s*(\d)', r'\1.\2', s)
    s = re.sub(r'\bv(\d)', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def canonicalize(name: str) -> str:
    """
    Normalize a scraped model name to its canonical display form.

    Steps:
      1. Strip emoji / org prefixes / raw-API suffixes.
      2. Expand known short Claude names: "Opus 4.6" → "Claude Opus 4.6".
      3. Look up in ALIASES (case-insensitive).
      4. Check CANONICAL_ROSTER for exact match.
      5. Return the cleaned name if no canonical match found.
    """
    if not name or not name.strip():
        return name

    cleaned = _strip_noise(name)
    cl = cleaned.lower()

    # Step 2: Expand short Claude model names missing the "Claude " prefix
    _CLAUDE_SHORT = [
        ("opus ",    "Claude Opus "),
        ("sonnet ",  "Claude Sonnet "),
        ("haiku ",   "Claude Haiku "),
    ]
    for short_prefix, full_prefix in _CLAUDE_SHORT:
        if cl.startswith(short_prefix) and not cl.startswith("claude"):
            expanded = full_prefix + cleaned[len(short_prefix):]
            cl_exp = expanded.lower()
            if cl_exp in ALIASES:
                return ALIASES[cl_exp]
            for c in CANONICAL_ROSTER:
                if c.lower() == cl_exp:
                    return c
            return expanded  # best-effort

    # Step 3: ALIASES lookup
    if cl in ALIASES:
        return ALIASES[cl]

    # Step 4: CANONICAL_ROSTER exact match
    for c in CANONICAL_ROSTER:
        if c.lower() == cl:
            return c

    # Step 5: Return cleaned name (emoji / suffix stripped)
    return cleaned


def match_name(scraped: str, existing: list[str]) -> str | None:
    """
    Find the best match for `scraped` within the `existing` name list.

    Matching tiers (first hit wins):
      1. Canonicalize both sides → exact match
      2. Substring containment (normalized)
      3. ≥2 token overlap (normalized)

    Returns the matched name from `existing`, or None if no match.
    """
    if not scraped:
        return None

    canon = canonicalize(scraped)
    canon_norm = _normalize(canon)

    # Tier 1: exact canonical match
    for name in existing:
        if canonicalize(name).lower() == canon.lower():
            return name
        if name.lower() == canon.lower():
            return name

    # Tier 2: substring containment (normalized)
    for name in existing:
        n = _normalize(name)
        if canon_norm in n or n in canon_norm:
            return name

    # Tier 3: ≥2 token overlap (normalized)
    c_tok = set(canon_norm.split())
    for name in existing:
        n_tok = set(_normalize(name).split())
        if len(c_tok & n_tok) >= 2:
            return name

    return None
