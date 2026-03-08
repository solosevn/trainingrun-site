#!/usr/bin/env python3
"""
TRSbench Scraper Test Suite â V1.0
Tests each scraper independently to validate real data extraction.

Run: python3 test_scrapers.py
"""

import sys
import json
import time
import traceback
from datetime import datetime

# Import scrapers
from trs_scrapers import (
    scrape_chatbot_arena,
    scrape_swebench,
    scrape_livecodebench,
    scrape_arc_agi2,
    scrape_mmlu_pro,
    scrape_artificial_analysis,
    scrape_openrouter,
    scrape_safety,
    scrape_all,
    MODEL_COMPANIES,
    normalize_model_name,
)
from trs_orchestrator import (
    normalize_scores,
    compute_trs,
    generate_checksum,
    WEIGHTS,
    CATEGORIES,
)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def test_scraper(name: str, func, min_expected: int = 1) -> dict:
    """Test a single scraper function."""
    print(f"\n{'â'*60}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: {name}{Colors.END}")
    print(f"{'â'*60}")

    start = time.time()
    try:
        result = func()
        elapsed = time.time() - start

        if not isinstance(result, dict):
            print(f"  {Colors.RED}FAIL: Expected dict, got {type(result)}{Colors.END}")
            return {"name": name, "status": "FAIL", "reason": f"Wrong type: {type(result)}", "count": 0}

        # Validate all keys are canonical model names
        invalid_names = [k for k in result.keys() if k not in MODEL_COMPANIES]
        if invalid_names:
            print(f"  {Colors.YELLOW}WARNING: {len(invalid_names)} non-canonical names:{Colors.END}")
            for n in invalid_names[:5]:
                print(f"    - '{n}'")

        # Validate all values are numeric
        non_numeric = [(k, v) for k, v in result.items() if not isinstance(v, (int, float))]
        if non_numeric:
            print(f"  {Colors.RED}FAIL: Non-numeric values found{Colors.END}")
            for k, v in non_numeric[:5]:
                print(f"    - {k}: {v} ({type(v)})")
            return {"name": name, "status": "FAIL", "reason": "Non-numeric values", "count": len(result)}

        # Check model count
        if len(result) < min_expected:
            print(f"  {Colors.YELLOW}WARNING: Only {len(result)} models (expected >= {min_expected}){Colors.END}")

        # Print results
        canonical_count = sum(1 for k in result if k in MODEL_COMPANIES)
        print(f"\n  Results ({elapsed:.1f}s):")
        print(f"    Total entries: {len(result)}")
        print(f"    Canonical models: {canonical_count}")

        # Show sample data
        for model, score in sorted(result.items(), key=lambda x: -x[1])[:10]:
            marker = "â" if model in MODEL_COMPANIES else "â ï¸"
            print(f"    {marker} {model}: {score}")

        if len(result) >= min_expected:
            print(f"\n  {Colors.GREEN}PASS{Colors.END} â {canonical_count} canonical models found")
            return {"name": name, "status": "PASS", "count": canonical_count, "data": result}
        else:
            print(f"\n  {Colors.YELLOW}WARN{Colors.END} â Below expected count ({len(result)} < {min_expected})")
            return {"name": name, "status": "WARN", "count": canonical_count, "data": result}

    except Exception as e:
        elapsed = time.time() - start
        print(f"  {Colors.RED}ERROR ({elapsed:.1f}s): {e}{Colors.END}")
        traceback.print_exc()
        return {"name": name, "status": "ERROR", "reason": str(e), "count": 0}


def test_normalization():
    """Test the normalization and TRS computation logic."""
    print(f"\n{'â'*60}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: Normalization & TRS Computation{Colors.END}")
    print(f"{'â'*60}")

    # Create synthetic test data
    test_data = {
        "Model A": {
            "safety": 95, "reasoning": 90, "coding": 85,
            "human_preference": 80, "knowledge": 75,
            "efficiency": 70, "usage_adoption": 65,
            "company": "TestCo"
        },
        "Model B": {
            "safety": 80, "reasoning": 85, "coding": 90,
            "human_preference": 75, "knowledge": 70,
            "efficiency": None, "usage_adoption": None,
            "company": "TestCo"
        },
        "Model C": {
            "safety": 50, "reasoning": None, "coding": None,
            "human_preference": None, "knowledge": None,
            "efficiency": None, "usage_adoption": None,
            "company": "TestCo"
        },
    }

    # Test normalization
    normalized = normalize_scores(test_data)

    print("\n  Normalized scores:")
    for model, scores in normalized.items():
        cats = {k: v for k, v in scores.items() if k != "company"}
        non_null = sum(1 for v in cats.values() if v is not None)
        print(f"    {model}: {non_null}/7 categories")
        for cat, val in cats.items():
            if val is not None:
                print(f"      {cat}: {val:.1f}")

    # Test TRS computation
    print("\n  TRS scores:")
    for model, data in normalized.items():
        trs = compute_trs(data)
        if trs is not None:
            print(f"    {Colors.GREEN}{model}: {trs}{Colors.END}")
        else:
            print(f"    {Colors.YELLOW}{model}: Not qualified (< 5 categories){Colors.END}")

    # Model A should have all 7, Model B should have 5, Model C should fail
    trs_a = compute_trs(normalized.get("Model A", {}))
    trs_b = compute_trs(normalized.get("Model B", {}))
    trs_c = compute_trs(normalized.get("Model C", {}))

    assert trs_a is not None, "Model A should qualify (7/7)"
    assert trs_b is not None, "Model B should qualify (5/7)"
    assert trs_c is None, "Model C should NOT qualify (1/7)"
    assert trs_a > trs_b, "Model A should score higher than Model B"

    print(f"\n  {Colors.GREEN}PASS{Colors.END} â Normalization and TRS computation correct")
    return True


def test_checksum():
    """Test the checksum algorithm matches the Bible specification."""
    print(f"\n{'â'*60}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: Checksum Algorithm{Colors.END}")
    print(f"{'â'*60}")

    # Test with known data
    test_models = [
        {"name": "Model A", "scores": [95.0, 96.1, None]},
        {"name": "Model B", "scores": [88.0, None, 90.5]},
    ]

    checksum = generate_checksum(test_models)
    print(f"  Input: Model A [95.0, 96.1, None], Model B [88.0, None, 90.5]")
    print(f"  Canonical: Model A|Model B:95.0,96.1,null,88.0,null,90.5")
    print(f"  Checksum: {checksum}")

    # Verify by computing manually
    import hashlib
    expected_canonical = "Model A|Model B:95.0,96.1,null,88.0,null,90.5"
    expected_checksum = hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest()

    assert checksum == expected_checksum, f"Checksum mismatch!\n  Expected: {expected_checksum}\n  Got:      {checksum}"

    # Test toFixed(1) behavior
    test_models_2 = [
        {"name": "Test", "scores": [88, 90.0, 91.23456]},
    ]
    checksum_2 = generate_checksum(test_models_2)
    expected_2 = hashlib.sha256("Test:88.0,90.0,91.2".encode("utf-8")).hexdigest()
    assert checksum_2 == expected_2, f"toFixed(1) mismatch!\n  Expected: {expected_2}\n  Got:      {checksum_2}"

    print(f"\n  {Colors.GREEN}PASS{Colors.END} â Checksum algorithm matches Bible specification")
    return True


def test_model_name_normalization():
    """Test model name normalization."""
    print(f"\n{'â'*60}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: Model Name Normalization{Colors.END}")
    print(f"{'â'*60}")

    test_cases = [
        ("claude-opus-4.6", "Claude Opus 4.6"),
        ("gpt-5.2", "GPT-5.2"),
        ("gemini-3-pro", "Gemini 3 Pro"),
        ("deepseek-r1", "DeepSeek R1"),
        ("Claude Sonnet 4.5", "Claude Sonnet 4.5"),  # Already canonical
        ("grok-4.1", "Grok 4.1"),
        ("mistral-large-latest", "Mistral Large"),
    ]

    all_pass = True
    for raw, expected in test_cases:
        result = normalize_model_name(raw)
        status = "â" if result == expected else "â"
        if result != expected:
            all_pass = False
        print(f"  {status} '{raw}' â '{result}' (expected: '{expected}')")

    if all_pass:
        print(f"\n  {Colors.GREEN}PASS{Colors.END} â All name normalizations correct")
    else:
        print(f"\n  {Colors.RED}FAIL{Colors.END} â Some normalizations incorrect")

    return all_pass


def main():
    """Run all tests."""
    print(f"\n{'â'*60}")
    print(f"{Colors.BOLD}  TRSbench Scraper Test Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'â'*60}")

    results = []

    # Unit tests first (no network)
    test_model_name_normalization()
    test_checksum()
    test_normalization()

    # Individual scraper tests
    scrapers = [
        ("Chatbot Arena (Human Preference)", scrape_chatbot_arena, 3),
        ("SWE-bench Verified (Coding)", scrape_swebench, 3),
        ("LiveCodeBench (Coding sub)", scrape_livecodebench, 0),  # May not always be available
        ("ARC-AGI-2 (Reasoning)", scrape_arc_agi2, 3),
        ("MMLU-Pro (Knowledge)", scrape_mmlu_pro, 3),
        ("Artificial Analysis (Efficiency)", scrape_artificial_analysis, 3),
        ("OpenRouter (Usage Adoption)", scrape_openrouter, 1),
        ("Safety (Composite)", scrape_safety, 1),
    ]

    for name, func, min_expected in scrapers:
        result = test_scraper(name, func, min_expected)
        results.append(result)
        time.sleep(1)  # Rate limiting between scrapers

    # Summary
    print(f"\n{'â'*60}")
    print(f"{Colors.BOLD}  TEST SUMMARY{Colors.END}")
    print(f"{'â'*60}")

    passes = sum(1 for r in results if r["status"] == "PASS")
    warns = sum(1 for r in results if r["status"] == "WARN")
    fails = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))

    for r in results:
        color = Colors.GREEN if r["status"] == "PASS" else (Colors.YELLOW if r["status"] == "WARN" else Colors.RED)
        print(f"  {color}{r['status']:5s}{Colors.END} {r['name']} ({r['count']} models)")

    print(f"\n  {Colors.GREEN}PASS: {passes}{Colors.END}  {Colors.YELLOW}WARN: {warns}{Colors.END}  {Colors.RED}FAIL: {fails}{Colors.END}")

    if fails > 0:
        print(f"\n  {Colors.RED}Some scrapers failed. Check output above.{Colors.END}")
        return 1
    elif warns > 0:
        print(f"\n  {Colors.YELLOW}Some scrapers returned fewer results than expected.{Colors.END}")
        return 0
    else:
        print(f"\n  {Colors.GREEN}All scrapers working!{Colors.END}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
