#!/usr/bin/env python3
"""
TRSbench Orchestrator â V1.0
Computes TRS composite scores and updates trs-data.json.

Follows M Bible V2.4/V2.6 and TRSbench Bible V1.1 exactly:
  - Discovery-first model scanning
  - 5-of-7 qualification rule
  - Proportional normalization for null categories
  - SHA-256 checksum using canonical string format
  - Rank recalculation
  - New model backfilling
"""

import json
import hashlib
import os
import sys
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from trs_scrapers import scrape_all, MODEL_COMPANIES


# TRS Category Weights (M Bible V2.4)
WEIGHTS = {
    "safety":           0.21,
    "reasoning":        0.20,
    "coding":           0.20,
    "human_preference": 0.18,
    "knowledge":        0.08,
    "efficiency":       0.07,
    "usage_adoption":   0.06,
}

CATEGORIES = list(WEIGHTS.keys())
MIN_CATEGORIES = 5  # 5-of-7 qualification rule


def normalize_scores(raw_data: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Normalize all category scores to 0-100 scale.
    Top performer in each category = 100, others proportional.
    """
    normalized = {}

    for cat in CATEGORIES:
        # Find max value for this category across all models
        values = []
        for model, data in raw_data.items():
            val = data.get(cat)
            if val is not None:
                values.append((model, float(val)))

        if not values:
            continue

        max_val = max(v for _, v in values)
        if max_val == 0:
            continue

        for model, val in values:
            if model not in normalized:
                normalized[model] = {c: None for c in CATEGORIES}
                normalized[model]["company"] = raw_data[model].get("company", "Unknown")
            normalized[model][cat] = (val / max_val) * 100

    # Ensure all discovered models are included even if they had no normalizable scores
    for model, data in raw_data.items():
        if model not in normalized:
            normalized[model] = {c: None for c in CATEGORIES}
            normalized[model]["company"] = data.get("company", "Unknown")

    return normalized


def compute_trs(normalized_data: Dict[str, Optional[float]]) -> Optional[float]:
    """
    Compute TRS composite score for a single model.
    Uses proportional normalization for null categories:
      weights of available categories are scaled up proportionally.
    Returns None if fewer than 5 categories have data.
    """
    available = []
    for cat in CATEGORIES:
        val = normalized_data.get(cat)
        if val is not None:
            available.append((cat, val))

    if len(available) < MIN_CATEGORIES:
        return None

    # Proportional weight redistribution
    total_weight = sum(WEIGHTS[cat] for cat, _ in available)
    if total_weight == 0:
        return None

    trs = 0.0
    for cat, val in available:
        adjusted_weight = WEIGHTS[cat] / total_weight
        trs += val * adjusted_weight

    return round(trs, 1)


def generate_checksum(models: List[Dict]) -> str:
    """
    Generate SHA-256 checksum using the canonical string format from M Bible.

    Format: model_names_joined_by_"|" + ":" + all_scores_comma_separated
    Rules:
      - Model names in the order they appear in the models array (NOT sorted)
      - ALL scores for ALL dates, flattened: model1_score1,model1_score2,...,model2_score1,...
      - Whole numbers use toFixed(1): 88 â "88.0"
      - Null values â "null"
    """
    model_names = [m["name"] for m in models]
    names_str = "|".join(model_names)

    all_scores = []
    for model in models:
        for score in model["scores"]:
            if score is None:
                all_scores.append("null")
            else:
                # toFixed(1) equivalent
                all_scores.append(f"{float(score):.1f}")

    scores_str = ",".join(all_scores)
    canonical = f"{names_str}:{scores_str}"

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def update_trs_data(data_path: str, today: str = None) -> bool:
    """
    Main orchestrator: scrape â normalize â compute â update â checksum.

    Args:
        data_path: Path to trs-data.json
        today: Date string YYYY-MM-DD (defaults to today)

    Returns: True on success
    """
    if today is None:
        today = date.today().strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  TRSbench Daily Update â {today}")
    print(f"{'='*60}\n")

    # ââ STEP 1: DISCOVER ââ
    print("STEP 1: DISCOVER â Scraping all platforms...")
    raw_data = scrape_all()

    if not raw_data:
        print("â FATAL: No data returned from any scraper. Aborting.")
        return False

    # ââ STEP 2: NORMALIZE ââ
    print("\nSTEP 2: NORMALIZE â Scaling to 0-100...")
    normalized = normalize_scores(raw_data)

    # ââ STEP 3: QUALIFY & COMPUTE ââ
    print("\nSTEP 3: QUALIFY & COMPUTE â Applying 5-of-7 rule...")
    trs_scores = {}
    for model, data in normalized.items():
        trs = compute_trs(data)
        if trs is not None:
            trs_scores[model] = trs

    print(f"  Qualified models: {len(trs_scores)}")
    for model, score in sorted(trs_scores.items(), key=lambda x: -x[1]):
        print(f"    {model}: {score}")

    if not trs_scores:
        print("â FATAL: No models qualified (5-of-7 rule). Aborting.")
        return False

    # ââ STEP 4: LOAD CURRENT DATA ââ
    print(f"\nSTEP 4: LOAD â Reading {data_path}...")
    if not os.path.exists(data_path):
        print(f"â FATAL: {data_path} not found")
        return False

    with open(data_path, 'r') as f:
        trs_data = json.load(f)

    existing_dates = trs_data.get("dates", [])
    existing_models = {m["name"]: m for m in trs_data.get("models", [])}

    # ââ STEP 5: APPEND DATE ââ
    print(f"\nSTEP 5: APPEND â Adding {today}...")

    if today in existing_dates:
        print(f"  â ï¸  Date {today} already exists â replacing last entry")
        date_index = existing_dates.index(today)
        # We'll replace scores at this index
        replacing = True
    else:
        existing_dates.append(today)
        replacing = False

    num_dates = len(existing_dates)
    trs_data["dates"] = existing_dates

    # ââ STEP 6: UPDATE MODELS ââ
    print("\nSTEP 6: UPDATE â Updating model scores...")

    # Update existing models
    for model_name, model_obj in existing_models.items():
        new_score = trs_scores.get(model_name)

        if replacing:
            # Replace score at existing date index
            while len(model_obj["scores"]) < num_dates:
                model_obj["scores"].append(None)
            model_obj["scores"][date_index] = new_score
        else:
            # Append new score
            model_obj["scores"].append(new_score)

        # Validate array length
        if len(model_obj["scores"]) != num_dates:
            print(f"  â ï¸  Score count mismatch for {model_name}: {len(model_obj['scores'])} vs {num_dates} dates")
            while len(model_obj["scores"]) < num_dates:
                model_obj["scores"].append(None)
            model_obj["scores"] = model_obj["scores"][:num_dates]

    # Add NEW models (discovered but not yet in trs-data.json)
    new_models = []
    for model_name, score in trs_scores.items():
        if model_name not in existing_models:
            company = MODEL_COMPANIES.get(model_name, "Unknown")
            # Backfill with nulls for all previous dates, then today's score
            scores = [None] * (num_dates - 1) + [score]
            new_model = {
                "name": model_name,
                "company": company,
                "rank": 0,  # Will be recalculated
                "scores": scores
            }
            new_models.append(new_model)
            print(f"  ð New model discovered: {model_name} ({company}) â TRS: {score}")

    # Merge new models into data
    all_models = trs_data.get("models", []) + new_models
    trs_data["models"] = all_models

    # ââ STEP 7: RECALCULATE RANKS ââ
    print("\nSTEP 7: RANKS â Recalculating...")

    # Get latest score for each model
    ranked = []
    for model in trs_data["models"]:
        latest = model["scores"][-1] if model["scores"] else None
        if latest is not None:
            ranked.append((float(latest), model))

    ranked.sort(key=lambda x: -x[0])  # Descending by score

    for i, (score, model) in enumerate(ranked):
        model["rank"] = i + 1
        print(f"    #{i+1}: {model['name']} â {score}")

    # Models with null latest score get rank = 0 (inactive)
    for model in trs_data["models"]:
        latest = model["scores"][-1] if model["scores"] else None
        if latest is None:
            model["rank"] = 0

    # ââ STEP 8: REGENERATE CHECKSUM ââ
    print("\nSTEP 8: CHECKSUM â Regenerating SHA-256...")

    checksum = generate_checksum(trs_data["models"])
    trs_data["checksum"] = checksum
    print(f"  Checksum: {checksum}")

    # ââ STEP 9: SAVE ââ
    print(f"\nSTEP 9: SAVE â Writing {data_path}...")

    # Final validation: all score arrays must match dates length
    for model in trs_data["models"]:
        if len(model["scores"]) != num_dates:
            print(f"  â VALIDATION FAIL: {model['name']} has {len(model['scores'])} scores, expected {num_dates}")
            return False

    with open(data_path, 'w') as f:
        json.dump(trs_data, f, separators=(',', ':'))

    print(f"\n  â Saved {data_path}")
    print(f"  ð Models: {len(trs_data['models'])}")
    print(f"  ð Dates: {num_dates} (latest: {today})")
    print(f"  ð Checksum: {checksum[:16]}...")

    # ââ STEP 10: VERIFY ââ
    print("\nSTEP 10: VERIFY â Re-reading and validating...")

    with open(data_path, 'r') as f:
        verify_data = json.load(f)

    verify_checksum = generate_checksum(verify_data["models"])
    if verify_checksum != checksum:
        print(f"  â CHECKSUM MISMATCH after save!")
        print(f"     Expected: {checksum}")
        print(f"     Got:      {verify_checksum}")
        return False

    print(f"  â Checksum verified: {verify_checksum[:16]}...")
    print(f"  â Date count: {len(verify_data['dates'])}")
    print(f"  â Model count: {len(verify_data['models'])}")

    for model in verify_data["models"]:
        if len(model["scores"]) != len(verify_data["dates"]):
            print(f"  â Score/date mismatch: {model['name']}")
            return False

    print(f"\n{'='*60}")
    print(f"  â TRSbench UPDATE COMPLETE â {today}")
    print(f"{'='*60}")

    return True


if __name__ == "__main__":
    # Default path â override via command line
    data_path = sys.argv[1] if len(sys.argv) > 1 else "./trainingrun-site/trs-data.json"
    today = sys.argv[2] if len(sys.argv) > 2 else None

    success = update_trs_data(data_path, today)

    if success:
        print("\nð¯ READY: Commit and push to GitHub")
    else:
        print("\nâ UPDATE FAILED â DO NOT PUSH")
        sys.exit(1)
