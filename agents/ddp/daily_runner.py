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
  python3 daily_runner.py                # run all enabled agents
  python3 daily_runner.py --dry-run      # scrape but don't push
  python3 daily_runner.py --score trs    # run one score only
  python3 daily_runner.py --score trs --dry-run

Scores:
  trs       = TRSbench (main overall score)   -> trs-data.json
  truscore  = TRUscore (truth & neutrality)   -> truscore-data.json
  trscode   = TRScode (coding)                -> trscode-data.json
  trfcast   = TRFcast (forecasting & trading) -> trf-data.json
  tragents  = TRAgents (autonomous agents)    -> tragent-data.json
"""

import subprocess
import sys
import argparse
from datetime import datetime
import json
import os

# ─────────────────────────────────────────────
# Agent enable/disable switches
# Set to True ONLY after the agent is tested
# ─────────────────────────────────────────────
ENABLED = {
    "trscode":   True,    # agent_trscode.py    -> trscode-data.json
    "trfcast":   True,    # agent_trfcast.py    -> trf-data.json
    "trs":       True,    # agent_trs.py        -> trs-data.json
    "truscore":  True,    # agent_truscore.py   -> truscore-data.json
    "tragents":  True,    # agent_tragents.py   -> tragent-data.json
}

# Agent script filenames (all live in repo root alongside this file)
AGENT_SCRIPTS = {
    "trscode":   "agent_trscode.py",
    "trfcast":   "agent_trfcast.py",
    "trs":       "agent_trs.py",
    "truscore":  "agent_truscore.py",
    "tragents":  "agent_tragents.py",
}

SCORE_NAMES = {
    "trscode":   "TRScode",
    "trfcast":   "TRFcast",
    "trs":       "TRSbench",
    "truscore":  "TRUscore",
    "tragents":  "TRAgents",
}


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_agent(score_key: str, dry_run: bool) -> bool:
    """Run one agent script. Returns True on success."""
    script = AGENT_SCRIPTS[score_key]
    name = SCORE_NAMES[score_key]

    if not os.path.exists(script):
        log(f"  SKIP {name}: {script} not found yet.")
        return False

    cmd = [sys.executable, script]
    if dry_run:
        cmd.append("--dry-run")

    log(f"  Running {name} ({script})...")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        log(f"  OK {name} complete.")
        return True
    else:
        log(f"  FAILED {name} (exit code {result.returncode}).")
        return False


def main():
    parser = argparse.ArgumentParser(description="trainingrun.ai daily runner")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and calculate but do NOT push to GitHub")
    parser.add_argument("--score", choices=list(AGENT_SCRIPTS.keys()),
                        help="Run only one specific score agent")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    log(f"=== trainingrun.ai Daily Runner === {mode} ===")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    log("")

    if args.score:
        scores_to_run = [args.score]
    else:
        scores_to_run = list(ENABLED.keys())

    results = {}
    any_enabled = False

    for score_key in scores_to_run:
        name = SCORE_NAMES[score_key]

        if not ENABLED.get(score_key, False):
            log(f"  PAUSED {name}: disabled (set ENABLED['{score_key}'] = True to activate)")
            results[score_key] = "disabled"
            continue

        any_enabled = True
        ok = run_agent(score_key, args.dry_run)
        results[score_key] = "ok" if ok else "failed"
        log("")

    log("")
    log("=== Summary ===")
    for score_key, status in results.items():
        name = SCORE_NAMES[score_key]
        icon = {"ok": "OK", "failed": "FAILED", "disabled": "DISABLED"}.get(status, "?")
        log(f"  {icon} {name}: {status}")

    if not any_enabled:
        log("")
        log("No agents are enabled yet.")
        log("Edit ENABLED dict in daily_runner.py to activate an agent.")
        log("Build order: TRScode -> TRFcast -> TRSbench -> TRUscore -> TRAgents")

    failed = [k for k, v in results.items() if v == "failed"]
    if failed:
        log("")
        log(f"WARNING: {len(failed)} agent(s) failed. Check output above.")
        sys.exit(1)

    log("")
    log("Done.")


if __name__ == "__main__":
    main()
