#!/usr/bin/env python3
"""
trainingrun.ai — Master Daily Runner
=====================================
Orchestrates all 5 leaderboard agents in sequence.
Each agent scrapes real benchmark data, updates its JSON file,
and pushes to GitHub independently.

Agents are enabled/disabled via the ENABLED dict below.
Set an agent to True only after its scraper is tested and verified.

Run modes:
    python3 daily_runner.py              # run all enabled agents
    python3 daily_runner.py --dry-run    # scrape but don't push
    python3 daily_runner.py --score trs  # run one score only
    python3 daily_runner.py --score trs --dry-run

Scores:
    trs      = TRSbench (main overall score)  -> trs-data.json
    truscore = TRUscore (truth & neutrality)  -> truscore-data.json
    trscode  = TRScode (coding)               -> trscode-data.json
    trfcast  = TRFcast (forecasting & trading) -> trf-data.json
    tragents = TRAgents (autonomous agents)    -> tragent-data.json
"""

import subprocess
import sys
import argparse
from datetime import datetime
import json
import os

# Resolve script directory so runner works regardless of cwd
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ———————————————————————————————————————
# Agent enable/disable switches
# Set to True ONLY after the agent is tested
# ———————————————————————————————————————
ENABLED = {
    "trscode":  True,   # agent_trscode.py  -> trscode-data.json
    "trfcast":  True,   # agent_trfcast.py  -> trf-data.json
    "trs":      True,   # agent_trs.py      -> trs-data.json
    "truscore": True,   # agent_truscore.py -> truscore-data.json
    "tragents": True,   # agent_tragents.py -> tragent-data.json
}

AGENT_SCRIPTS = {
    "trscode":  "agent_trscode.py",
    "trfcast":  "agent_trfcast.py",
    "trs":      "agent_trs.py",
    "truscore": "agent_truscore.py",
    "tragents": "agent_tragents.py",
}

SCORE_NAMES = {
    "trscode":  "TRScode",
    "trfcast":  "TRFcast",
    "trs":      "TRSbench",
    "truscore": "TRUscore",
    "tragents": "TRAgents",
}

STATUS_FILE = os.path.join(SCRIPT_DIR, "..", "..", "status.json")

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def update_status(score_key: str, success: bool, dry_run: bool):
    """Update status.json with run results for Mission Control."""
    try:
        status_path = os.path.normpath(STATUS_FILE)
        if os.path.exists(status_path):
            with open(status_path, "r") as f:
                status = json.load(f)
        else:
            status = {}

        if "ddp" not in status:
            status["ddp"] = {}

        status["ddp"][score_key] = {
            "last_run": datetime.now().isoformat(),
            "success": success,
            "dry_run": dry_run,
        }

        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        log(f"  WARNING: Could not update status.json: {e}")

def run_agent(score_key: str, dry_run: bool) -> bool:
    script = AGENT_SCRIPTS[score_key]
    name = SCORE_NAMES[score_key]
    script_path = os.path.join(SCRIPT_DIR, script)

    if not os.path.exists(script_path):
        log(f"  SKIP {name}: {script_path} not found.")
        return False

    cmd = [sys.executable, script_path]
    if dry_run:
        cmd.append("--dry-run")

    log(f"  START {name} ({script})")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SCRIPT_DIR,
        )
        if result.returncode == 0:
            log(f"  DONE  {name} ✓")
            return True
        else:
            log(f"  FAIL  {name} (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    log(f"        {line}")
            return False
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT {name} (>300s)")
        return False
    except Exception as e:
        log(f"  ERROR {name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="TrainingRun Daily Runner")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but don't push")
    parser.add_argument("--score", type=str, help="Run one score only (trs, truscore, trscode, trfcast, tragents)")
    args = parser.parse_args()

    log("=" * 50)
    log("TrainingRun Daily Runner — starting")
    log(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    log(f"  Script dir: {SCRIPT_DIR}")
    log("=" * 50)

    if args.score:
        if args.score not in AGENT_SCRIPTS:
            log(f"Unknown score: {args.score}")
            log(f"Valid scores: {', '.join(AGENT_SCRIPTS.keys())}")
            sys.exit(1)
        if not ENABLED.get(args.score, False):
            log(f"{args.score} is DISABLED in ENABLED dict")
            sys.exit(1)
        success = run_agent(args.score, args.dry_run)
        update_status(args.score, success, args.dry_run)
        sys.exit(0 if success else 1)

    results = {}
    for key in AGENT_SCRIPTS:
        if ENABLED.get(key, False):
            success = run_agent(key, args.dry_run)
            results[key] = success
            update_status(key, success, args.dry_run)
        else:
            log(f"  SKIP {SCORE_NAMES[key]}: disabled")
            results[key] = None

    log("")
    log("=" * 50)
    log("SUMMARY")
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    log(f"  Passed: {passed}  Failed: {failed}  Skipped: {skipped}")
    for key, result in results.items():
        status = "✓" if result is True else ("✗" if result is False else "—")
        log(f"  {status} {SCORE_NAMES[key]}")
    log("=" * 50)

if __name__ == "__main__":
    main()
