"""
Daily News Agent — Configuration
=================================
Loads secrets from .env, defines all constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from agent directory
load_dotenv(Path(__file__).parent / ".env")

# ──────────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────────
TRNEWZ_BOT_TOKEN = os.getenv("TRNEWZ_BOT_TOKEN", "")
DAVID_CHAT_ID = int(os.getenv("DAVID_CHAT_ID", "0"))

# ──────────────────────────────────────────────────────────
# GROK (xAI) — OpenAI-compatible API
# ──────────────────────────────────────────────────────────
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
GROK_API_BASE = "https://api.x.ai/v1"
GROK_MODEL = "grok-3"
GROK_FAST_MODEL = "grok-3-mini"

# ──────────────────────────────────────────────────────────
# GITHUB
# ──────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_OWNER = "solosevn"
REPO_NAME = "trainingrun-site"
REPO_BRANCH = "main"
GITHUB_API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"

# ──────────────────────────────────────────────────────────
# PATHS — Local repo on David's Mac
# ──────────────────────────────────────────────────────────
TR_REPO_PATH = Path(os.getenv("TR_REPO_PATH", str(Path.home() / "trainingrun-site")))
SCOUT_BRIEFING_PATH = TR_REPO_PATH / "scout-briefing.json"
AGENT_DIR = Path(__file__).parent
STAGING_DIR = AGENT_DIR / "staging"
CACHE_DIR = AGENT_DIR / ".cache"
LOG_FILE = AGENT_DIR / "agent.log"

# Create directories
STAGING_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────
# CONTEXT VAULT — Files the agent reads for instructions
# ──────────────────────────────────────────────────────────
VAULT_FILES = {
    "user_md":        "shared/USER.md",
    "reasoning_md":   "shared/REASONING-CHECKLIST.md",
    "soul_md":        "agents/daily-news/vault/SOUL.md",
    "config_md":      "agents/daily-news/vault/CONFIG.md",
    "process_md":     "agents/daily-news/vault/PROCESS.md",
    "style_md":       "agents/daily-news/vault/STYLE-EVOLUTION.md",
    "run_log_md":     "agents/daily-news/vault/RUN-LOG.md",
    "learning_md":    "agents/daily-news/vault/LEARNING-LOG.md",
    "engagement_md":  "agents/daily-news/vault/ENGAGEMENT-LOG.md",
}

# ──────────────────────────────────────────────────────────
# ARTICLE CONFIGURATION
# ──────────────────────────────────────────────────────────
ARTICLE_TEMPLATE_PATH = "day-template.html"
NEWS_INDEX_PATH = "news.html"
ARTICLE_PREFIX = "day-"
IMAGE_DIR = "assets/news/"
SIGNATURE_PATH = "assets/signature.png"

# ──────────────────────────────────────────────────────────
# TIMING
# ──────────────────────────────────────────────────────────
APPROVAL_TIMEOUT_MINUTES = 120
POLL_INTERVAL_SECONDS = 5

# ──────────────────────────────────────────────────────────
# ARTICLE CATEGORIES (from CONFIG.md)
# ──────────────────────────────────────────────────────────
CATEGORIES = [
    "AI Safety", "AI Research", "AI Ethics", "AI Tools",
    "AI Policy", "AI Agents", "Machine Learning", "Open Source",
    "AI in Medicine", "AI in Business", "Compute & Infrastructure",
]
