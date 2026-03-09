#!/bin/bash
# =============================================================================
# TrainingRun Site — Full Restructure Migration Script
# Date: 2026-03-08
# Purpose: Moves all files to new agents/ hierarchy, updates all code references
# Run from: ~/trainingrun-site (REPO_PATH root)
#
# SAFETY: Uses cp (copy) first, verifies, THEN git rm. Nothing is lost.
#         Full backup created before any changes.
# =============================================================================
set -e  # Exit on any error

echo "============================================"
echo "TrainingRun Site Restructure — Migration Script"
echo "============================================"
echo ""

# Safety check: are we in the right directory?
if [ ! -f "index.html" ] || [ ! -d "web_agent" ]; then
    echo "ERROR: Run this from ~/trainingrun-site (the repo root)"
    echo "Usage: cd ~/trainingrun-site && bash restructure.sh"
    exit 1
fi

# ─── STEP 0: FULL BACKUP ────────────────────────────────────────
echo "Step 0: Creating full backup..."
BACKUP_NAME="pre-restructure-backup-$(date +%Y%m%d-%H%M%S)"
BACKUP_PATH="$HOME/$BACKUP_NAME"
cp -r "$(pwd)" "$BACKUP_PATH"
echo "  ✓ Full backup saved to: $BACKUP_PATH"
echo "  (If anything goes wrong, your entire repo is safe there)"
echo ""

# ─── STEP 0b: Git safety ────────────────────────────────────────
echo "Step 0b: Git safety check..."
git stash 2>/dev/null || true
git checkout main
git pull origin main
echo "  ✓ On main branch, up to date"
echo ""

# ─── STEP 1: Create new directory structure ─────────────────────
echo "Step 1: Creating new directory structure..."
mkdir -p agents/trsitekeeper/vault
mkdir -p agents/trsitekeeper/memory
mkdir -p agents/trsitekeeper/skills
mkdir -p agents/daily-news/vault
mkdir -p agents/daily-news/staging
mkdir -p agents/content-scout/vault
mkdir -p agents/content-scout/.vault-cache
mkdir -p agents/ddp
mkdir -p shared
mkdir -p data
mkdir -p archive/context-vault-docs
echo "  ✓ Directory structure created"
echo ""

# ─── STEP 2: Move TRSitekeeper (web_agent/) ─────────────────────
echo "Step 2: Moving TRSitekeeper (web_agent/ → agents/trsitekeeper/)..."

# Vault files — merge from BOTH locations (web_agent/vault/ is primary)
if [ -d "web_agent/vault" ]; then
    cp -n web_agent/vault/*.md agents/trsitekeeper/vault/ 2>/dev/null || true
    echo "  - Copied vault from web_agent/vault/"
fi
if [ -d "context-vault/trainingrun/agents/trsitekeeper" ]; then
    for f in context-vault/trainingrun/agents/trsitekeeper/*.md; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        if [ ! -f "agents/trsitekeeper/vault/$fname" ]; then
            cp "$f" "agents/trsitekeeper/vault/$fname"
            echo "  - Added $fname from context-vault (not in web_agent/vault)"
        fi
    done
fi

# Memory files (all of them — .jsonl, .json, AND .md)
if [ -d "web_agent/memory" ]; then
    cp web_agent/memory/* agents/trsitekeeper/memory/ 2>/dev/null || true
    echo "  - Copied all memory files"
fi

# Skills (all .md files)
if [ -d "web_agent/skills" ]; then
    cp web_agent/skills/* agents/trsitekeeper/skills/ 2>/dev/null || true
    echo "  - Copied skills: $(ls web_agent/skills/ 2>/dev/null | tr '\n' ' ')"
fi

# Core Python + config files
cp web_agent/agent.py agents/trsitekeeper/
cp web_agent/brain.md agents/trsitekeeper/
cp web_agent/sitekeeper_audit.py agents/trsitekeeper/
cp web_agent/sitekeeper_context_loader.py agents/trsitekeeper/
cp web_agent/sitekeeper_learning_logger.py agents/trsitekeeper/

# Additional files that exist in web_agent/
[ -f "web_agent/README_AGENT.md" ] && cp web_agent/README_AGENT.md agents/trsitekeeper/
[ -f "web_agent/audit_history.json" ] && cp web_agent/audit_history.json agents/trsitekeeper/
[ -f "web_agent/memory_log.jsonl" ] && cp web_agent/memory_log.jsonl agents/trsitekeeper/memory/

echo "  ✓ TRSitekeeper: all files moved ($(ls agents/trsitekeeper/ | wc -l | tr -d ' ') items)"
echo ""

# ─── STEP 3: Move Daily News Agent ──────────────────────────────
echo "Step 3: Moving Daily News Agent (daily_news_agent/ → agents/daily-news/)..."

# Vault files from context-vault
if [ -d "context-vault/agents/trainingrun/daily-news" ]; then
    for f in context-vault/agents/trainingrun/daily-news/*.md; do
        [ -f "$f" ] && cp "$f" agents/daily-news/vault/
    done
    echo "  - Copied vault files from context-vault"
fi

# ALL files from daily_news_agent/ (preserving everything)
for f in daily_news_agent/*; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    cp "$f" "agents/daily-news/$fname"
done

# Staging directory contents
if [ -d "daily_news_agent/staging" ]; then
    cp -r daily_news_agent/staging/* agents/daily-news/staging/ 2>/dev/null || true
    # Also copy hidden files like .last_processed_date
    cp -r daily_news_agent/staging/.* agents/daily-news/staging/ 2>/dev/null || true
    echo "  - Copied staging directory"
fi

echo "  ✓ Daily News: all files moved ($(ls agents/daily-news/ | wc -l | tr -d ' ') items)"
echo ""

# ─── STEP 4: Move Content Scout ─────────────────────────────────
echo "Step 4: Moving Content Scout (content_scout/ → agents/content-scout/)..."

# Vault files from context-vault
if [ -d "context-vault/agents/trainingrun/daily-news/content-scout" ]; then
    for f in context-vault/agents/trainingrun/daily-news/content-scout/*.md; do
        [ -f "$f" ] && cp "$f" agents/content-scout/vault/
    done
    echo "  - Copied vault files from context-vault"
fi

# ALL files from content_scout/
for f in content_scout/*; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    cp "$f" "agents/content-scout/$fname"
done

echo "  ✓ Content Scout: all files moved ($(ls agents/content-scout/ | wc -l | tr -d ' ') items)"
echo ""

# ─── STEP 5: Move DDP scrapers ──────────────────────────────────
echo "Step 5: Moving DDP scrapers → agents/ddp/..."
[ -f "daily_runner.py" ] && cp daily_runner.py agents/ddp/
[ -f "agent_trscode.py" ] && cp agent_trscode.py agents/ddp/
[ -f "agent_truscore.py" ] && cp agent_truscore.py agents/ddp/
[ -f "agent_trfcast.py" ] && cp agent_trfcast.py agents/ddp/
[ -f "agent_tragents.py" ] && cp agent_tragents.py agents/ddp/
[ -f "agent_trs.py" ] && cp agent_trs.py agents/ddp/
[ -f "model_names.py" ] && cp model_names.py agents/ddp/
[ -f "models.json" ] && cp models.json agents/ddp/
echo "  ✓ DDP scrapers moved ($(ls agents/ddp/ | wc -l | tr -d ' ') files)"
echo ""

# ─── STEP 6: Move data files ────────────────────────────────────
echo "Step 6: Moving data files → data/..."
[ -f "trscode-data.json" ] && cp trscode-data.json data/
[ -f "truscore-data.json" ] && cp truscore-data.json data/
[ -f "trf-data.json" ] && cp trf-data.json data/
[ -f "tragent-data.json" ] && cp tragent-data.json data/
[ -f "trs-data.json" ] && cp trs-data.json data/
[ -f "status.json" ] && cp status.json data/
echo "  ✓ Data files moved"
echo ""

# ─── STEP 7: Move shared files ──────────────────────────────────
echo "Step 7: Moving shared context → shared/..."
[ -f "OPERATING_INSTRUCTIONS.md" ] && cp OPERATING_INSTRUCTIONS.md shared/
[ -f "PRODUCTION_BIBLE.md" ] && cp PRODUCTION_BIBLE.md shared/
[ -f "context-vault/org/USER.md" ] && cp "context-vault/org/USER.md" shared/
[ -f "context-vault/org/shared-context/REASONING-CHECKLIST.md" ] && cp "context-vault/org/shared-context/REASONING-CHECKLIST.md" shared/
[ -f "context-vault/org/shared-context/TSArena_Master_Checklist_V7.md" ] && cp "context-vault/org/shared-context/TSArena_Master_Checklist_V7.md" shared/
echo "  ✓ Shared files moved"
echo ""

# ─── STEP 8: Archive context-vault docs (don't lose anything) ───
echo "Step 8: Archiving context-vault reference docs (not losing these)..."

# TSArena docs and DDP pipeline vault — archive for future use
[ -f "context-vault/TSArena_Agent_Build_Checklist.md" ] && cp "context-vault/TSArena_Agent_Build_Checklist.md" archive/context-vault-docs/
[ -f "context-vault/TSArena_Full_Structure_V4.md" ] && cp "context-vault/TSArena_Full_Structure_V4.md" archive/context-vault-docs/

# DDP pipeline vault files (future: may become agents/ddp/vault/)
if [ -d "context-vault/agents/trainingrun/trs-site-manager/ddp-pipeline" ]; then
    mkdir -p archive/context-vault-docs/ddp-pipeline-vault
    cp context-vault/agents/trainingrun/trs-site-manager/ddp-pipeline/*.md archive/context-vault-docs/ddp-pipeline-vault/ 2>/dev/null || true
    echo "  - Archived DDP pipeline vault files"
fi

# TSArena battle-generator vault files (future tsarena-site)
if [ -d "context-vault/agents/tsarena/battle-generator" ]; then
    mkdir -p archive/context-vault-docs/tsarena-battle-generator
    cp context-vault/agents/tsarena/battle-generator/*.md archive/context-vault-docs/tsarena-battle-generator/ 2>/dev/null || true
    echo "  - Archived TSArena battle-generator vault files"
fi

# Scripts directory (keep as-is, just in case)
if [ -d "scripts" ]; then
    mkdir -p archive/scripts
    cp scripts/* archive/scripts/ 2>/dev/null || true
    echo "  - Archived scripts/"
fi

echo "  ✓ Reference docs archived (nothing lost)"
echo ""

# ─── STEP 9: HTML files stay at root (GitHub Pages) ─────────────
echo "Step 9: HTML/CSS/JS files..."
echo "  ✓ HTML, CSS, JS, assets/ staying at repo root (GitHub Pages serves from root)"
echo "  No changes to site-serving files."
echo ""

# ─── STEP 10: Update Python code references ─────────────────────
echo "Step 10: Updating Python code references..."

# --- TRSitekeeper audit.py ---
echo "  - Updating sitekeeper_audit.py..."
# Fix check_006 vault path
sed -i '' 's|"context-vault" / "trainingrun" / "agents" / "trsitekeeper"|"agents" / "trsitekeeper" / "vault"|g' agents/trsitekeeper/sitekeeper_audit.py

# Fix data file paths (checks 002, 003)
sed -i '' 's|Path(REPO_PATH) / "trscode-data.json"|Path(REPO_PATH) / "data" / "trscode-data.json"|g' agents/trsitekeeper/sitekeeper_audit.py
sed -i '' 's|Path(REPO_PATH) / "truscore-data.json"|Path(REPO_PATH) / "data" / "truscore-data.json"|g' agents/trsitekeeper/sitekeeper_audit.py
sed -i '' 's|Path(REPO_PATH) / "trf-data.json"|Path(REPO_PATH) / "data" / "trf-data.json"|g' agents/trsitekeeper/sitekeeper_audit.py
sed -i '' 's|Path(REPO_PATH) / "tragent-data.json"|Path(REPO_PATH) / "data" / "tragent-data.json"|g' agents/trsitekeeper/sitekeeper_audit.py
sed -i '' 's|Path(REPO_PATH) / "trs-data.json"|Path(REPO_PATH) / "data" / "trs-data.json"|g' agents/trsitekeeper/sitekeeper_audit.py

# Fix tried_fixes path
sed -i '' 's|Path(REPO_PATH) / "web_agent" / "memory"|Path(REPO_PATH) / "agents" / "trsitekeeper" / "memory"|g' agents/trsitekeeper/sitekeeper_audit.py

# Fix web_agent directory reference in check_001
sed -i '' 's|Path(REPO_PATH) / "web_agent"|Path(REPO_PATH) / "agents" / "trsitekeeper"|g' agents/trsitekeeper/sitekeeper_audit.py

# --- TRSitekeeper agent.py ---
echo "  - Updating agent.py..."
# Fix DDP runner path
sed -i '' 's|"daily_runner.py"|"agents/ddp/daily_runner.py"|g' agents/trsitekeeper/agent.py

# --- Daily News config.py ---
echo "  - Updating daily-news/config.py..."
sed -i '' 's|context-vault/org/USER.md|shared/USER.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/org/shared-context/REASONING-CHECKLIST.md|shared/REASONING-CHECKLIST.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/SOUL.md|agents/daily-news/vault/SOUL.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/CONFIG.md|agents/daily-news/vault/CONFIG.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/PROCESS.md|agents/daily-news/vault/PROCESS.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/STYLE-EVOLUTION.md|agents/daily-news/vault/STYLE-EVOLUTION.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/RUN-LOG.md|agents/daily-news/vault/RUN-LOG.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/LEARNING-LOG.md|agents/daily-news/vault/LEARNING-LOG.md|g' agents/daily-news/config.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/ENGAGEMENT-LOG.md|agents/daily-news/vault/ENGAGEMENT-LOG.md|g' agents/daily-news/config.py

# --- Content Scout context_loader.py ---
echo "  - Updating content-scout/scout_context_loader.py..."
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/SOUL.md|agents/content-scout/vault/SOUL.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/CONFIG.md|agents/content-scout/vault/CONFIG.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/PROCESS.md|agents/content-scout/vault/PROCESS.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/CADENCE.md|agents/content-scout/vault/CADENCE.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/RUN-LOG.md|agents/content-scout/vault/RUN-LOG.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/LEARNING-LOG.md|agents/content-scout/vault/LEARNING-LOG.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/STYLE-EVOLUTION.md|agents/content-scout/vault/STYLE-EVOLUTION.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/SOURCES.md|agents/content-scout/vault/SOURCES.md|g' agents/content-scout/scout_context_loader.py
sed -i '' 's|context-vault/agents/trainingrun/daily-news/content-scout/TRUTH-FILTER.md|agents/content-scout/vault/TRUTH-FILTER.md|g' agents/content-scout/scout_context_loader.py

# --- Content Scout learning_logger.py ---
echo "  - Updating content-scout/scout_learning_logger.py..."
sed -i '' 's|VAULT_BASE = "context-vault/agents/trainingrun/daily-news/content-scout"|VAULT_BASE = "agents/content-scout/vault"|g' agents/content-scout/scout_learning_logger.py

# --- DDP scrapers: update data output paths ---
echo "  - Updating DDP scraper data output paths..."
for scraper in agents/ddp/agent_trscode.py agents/ddp/agent_truscore.py agents/ddp/agent_trfcast.py agents/ddp/agent_tragents.py agents/ddp/agent_trs.py agents/ddp/daily_runner.py; do
    if [ -f "$scraper" ]; then
        sed -i '' 's|/ "trscode-data.json"|/ "data" / "trscode-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|/ "truscore-data.json"|/ "data" / "truscore-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|/ "trf-data.json"|/ "data" / "trf-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|/ "tragent-data.json"|/ "data" / "tragent-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|/ "trs-data.json"|/ "data" / "trs-data.json"|g' "$scraper" 2>/dev/null || true
        # Also handle string concatenation patterns like "trscode-data.json" at line start
        sed -i '' 's|"trscode-data.json"|"data/trscode-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|"truscore-data.json"|"data/truscore-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|"trf-data.json"|"data/trf-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|"tragent-data.json"|"data/tragent-data.json"|g' "$scraper" 2>/dev/null || true
        sed -i '' 's|"trs-data.json"|"data/trs-data.json"|g' "$scraper" 2>/dev/null || true
    fi
done

# --- GitHub raw URLs in fallback loaders ---
echo "  - Updating GitHub raw fallback URLs..."
sed -i '' 's|raw.githubusercontent.com/solosevn/trainingrun-site/main/context-vault/agents/trainingrun/daily-news/|raw.githubusercontent.com/solosevn/trainingrun-site/main/agents/daily-news/vault/|g' agents/daily-news/context_loader.py 2>/dev/null || true
sed -i '' 's|raw.githubusercontent.com/solosevn/trainingrun-site/main/context-vault/agents/trainingrun/daily-news/content-scout/|raw.githubusercontent.com/solosevn/trainingrun-site/main/agents/content-scout/vault/|g' agents/content-scout/scout_context_loader.py 2>/dev/null || true

echo "  ✓ All Python code references updated"
echo ""

# ─── STEP 11: Verify before removing old files ──────────────────
echo "Step 11: Verification — checking new structure..."
ERRORS=0

# Check TRSitekeeper
for f in SOUL.md CONFIG.md PROCESS.md RUN-LOG.md LEARNING-LOG.md STYLE-EVOLUTION.md; do
    if [ ! -f "agents/trsitekeeper/vault/$f" ]; then
        echo "  ✗ MISSING: agents/trsitekeeper/vault/$f"
        ERRORS=$((ERRORS+1))
    fi
done
[ -f "agents/trsitekeeper/agent.py" ] || { echo "  ✗ MISSING: agents/trsitekeeper/agent.py"; ERRORS=$((ERRORS+1)); }
[ -f "agents/trsitekeeper/sitekeeper_audit.py" ] || { echo "  ✗ MISSING: agents/trsitekeeper/sitekeeper_audit.py"; ERRORS=$((ERRORS+1)); }

# Check Daily News
[ -f "agents/daily-news/main.py" ] || { echo "  ✗ MISSING: agents/daily-news/main.py"; ERRORS=$((ERRORS+1)); }
[ -f "agents/daily-news/config.py" ] || { echo "  ✗ MISSING: agents/daily-news/config.py"; ERRORS=$((ERRORS+1)); }
[ -f "agents/daily-news/vault/SOUL.md" ] || { echo "  ✗ MISSING: agents/daily-news/vault/SOUL.md"; ERRORS=$((ERRORS+1)); }

# Check Content Scout
[ -f "agents/content-scout/scout.py" ] || { echo "  ✗ MISSING: agents/content-scout/scout.py"; ERRORS=$((ERRORS+1)); }
[ -f "agents/content-scout/vault/SOUL.md" ] || { echo "  ✗ MISSING: agents/content-scout/vault/SOUL.md"; ERRORS=$((ERRORS+1)); }

# Check DDP
[ -f "agents/ddp/daily_runner.py" ] || { echo "  ✗ MISSING: agents/ddp/daily_runner.py"; ERRORS=$((ERRORS+1)); }

# Check data
[ -f "data/trscode-data.json" ] || { echo "  ✗ MISSING: data/trscode-data.json"; ERRORS=$((ERRORS+1)); }

# Check shared
[ -f "shared/USER.md" ] || { echo "  ✗ MISSING: shared/USER.md"; ERRORS=$((ERRORS+1)); }

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "  ✗ $ERRORS files missing! Aborting before removing old files."
    echo "  Your backup is safe at: $BACKUP_PATH"
    exit 1
fi
echo "  ✓ All critical files verified in new locations"
echo ""

# ─── STEP 12: Git operations ────────────────────────────────────
echo "Step 12: Staging new structure..."
git add agents/
git add shared/
git add data/
git add archive/
echo "  ✓ New files staged"
echo ""

echo "Step 13: Removing old directories from git..."
git rm -r web_agent/ 2>/dev/null || true
git rm -r daily_news_agent/ 2>/dev/null || true
git rm -r content_scout/ 2>/dev/null || true
git rm -r context-vault/ 2>/dev/null || true
git rm -r scripts/ 2>/dev/null || true

# Remove old root-level DDP files
git rm daily_runner.py 2>/dev/null || true
git rm agent_trscode.py 2>/dev/null || true
git rm agent_truscore.py 2>/dev/null || true
git rm agent_trfcast.py 2>/dev/null || true
git rm agent_tragents.py 2>/dev/null || true
git rm agent_trs.py 2>/dev/null || true
git rm model_names.py 2>/dev/null || true
git rm models.json 2>/dev/null || true

# Remove old root-level data files
git rm trscode-data.json 2>/dev/null || true
git rm truscore-data.json 2>/dev/null || true
git rm trf-data.json 2>/dev/null || true
git rm tragent-data.json 2>/dev/null || true
git rm trs-data.json 2>/dev/null || true
git rm status.json 2>/dev/null || true

# Remove old shared files from root (copies in shared/)
git rm OPERATING_INSTRUCTIONS.md 2>/dev/null || true
git rm PRODUCTION_BIBLE.md 2>/dev/null || true

echo "  ✓ Old files removed from git tracking"
echo ""

# ─── STEP 14: Commit ────────────────────────────────────────────
echo "Step 14: Committing..."
git commit -m "Restructure: agents/ hierarchy — unified vault per agent, eliminate context-vault

WHAT CHANGED:
- web_agent/ → agents/trsitekeeper/ (vault + memory + skills + code together)
- daily_news_agent/ → agents/daily-news/ (vault + code together)
- content_scout/ → agents/content-scout/ (vault + code together)
- Root DDP scrapers → agents/ddp/
- Root data JSONs → data/
- context-vault/ eliminated — each agent owns its vault in agents/*/vault/
- Shared docs → shared/ (USER.md, REASONING-CHECKLIST, OPERATING_INSTRUCTIONS)
- Reference docs → archive/ (TSArena, DDP pipeline vault, old scripts)

WHY:
- TRSitekeeper was reading from web_agent/vault/ but audit checked context-vault/
- Daily News and Content Scout read from context-vault/ — agents were isolated
- No sync mechanism existed between the two vault locations
- Now each agent has ONE vault location for read + write + audit

CODE UPDATES:
- sitekeeper_audit.py: check_006 → agents/trsitekeeper/vault/, data paths → data/
- daily-news/config.py: vault paths → agents/daily-news/vault/
- scout_context_loader.py: vault paths → agents/content-scout/vault/
- scout_learning_logger.py: VAULT_BASE → agents/content-scout/vault
- agent.py: DDP runner path updated
- GitHub raw fallback URLs updated
- HTML/CSS/JS remain at repo root (GitHub Pages)"
echo ""

# ─── STEP 15: Push ──────────────────────────────────────────────
echo "Step 15: Pushing to GitHub..."
git push origin main
echo ""

# ─── DONE ────────────────────────────────────────────────────────
echo "============================================"
echo "RESTRUCTURE COMPLETE ✓"
echo "============================================"
echo ""
echo "New structure:"
echo "  agents/trsitekeeper/  — Site Manager (vault/ memory/ skills/ + Python)"
echo "  agents/daily-news/    — Daily News Agent (vault/ + Python)"
echo "  agents/content-scout/ — Content Scout (vault/ + Python)"
echo "  agents/ddp/           — 5 DDP scrapers + runner"
echo "  shared/               — USER.md, REASONING-CHECKLIST, OPERATING_INSTRUCTIONS"
echo "  data/                 — DDP output JSON files"
echo "  archive/              — TSArena docs, old scripts (reference only)"
echo ""
echo "HTML/CSS/JS at root     — GitHub Pages (unchanged)"
echo ""
echo "Backup at: $BACKUP_PATH"
echo "  (Delete it once you've verified everything works)"
echo ""
echo "NEXT: Test the agent:"
echo "  cd ~/trainingrun-site && python3 agents/trsitekeeper/agent.py"
