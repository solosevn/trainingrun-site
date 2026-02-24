#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  trainingrun.ai — DDP Master Runner
#  Runs all 5 Daily Data Pipeline scrapers via daily_runner.py
#  Designed to be called by cron or manually.
# ─────────────────────────────────────────────────────────────

REPO="$HOME/trainingrun-site"
LOG="$REPO/ddp.log"
PYTHON=$(which python3)

echo "" >> "$LOG"
echo "======================================" >> "$LOG"
echo "DDP RUN STARTED: $(date)" >> "$LOG"
echo "======================================" >> "$LOG"

cd "$REPO" || { echo "ERROR: Cannot cd to $REPO" >> "$LOG"; exit 1; }

"$PYTHON" daily_runner.py >> "$LOG" 2>&1
EXIT_CODE=$?

echo "DDP RUN FINISHED: $(date) | exit=$EXIT_CODE" >> "$LOG"
exit $EXIT_CODE
