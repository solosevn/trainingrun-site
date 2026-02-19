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

# Maps raw platform names...(truncated 43972 characters)... sorted(combined.items()):
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
