#!/usr/bin/env python3
"""
Daily News Agent — Main Orchestrator
======================================
The execution engine for TrainingRun.AI's autonomous journalist.

This agent:
  1. Listens for Content Scout's morning briefing (via local file or Telegram)
  2. Selects the best story using Grok + David's 5-filter test
  3. Writes a full article in David's voice using Grok
  4. Stages the HTML and sends David a Telegram review request
  5. Waits for David's approval (push it / edit / kill it)
  6. Publishes to GitHub on approval
  7. Logs everything for the learning engine

Run:    python3 main.py
Test:   python3 main.py --test
Dry:    python3 main.py --dry-run
Status: python3 main.py --check

Reads instructions from context-vault files:
  SOUL.md, CONFIG.md, PROCESS.md, CADENCE.md, STYLE-EVOLUTION.md, USER.md
"""

import sys
import json
import time
import asyncio
import logging
import datetime
import argparse
from pathlib import Path

# Agent modules
from config import (
    TRNEWZ_BOT_TOKEN, DAVID_CHAT_ID, XAI_API_KEY, GITHUB_TOKEN,
    SCOUT_BRIEFING_PATH, STAGING_DIR, LOG_FILE, POLL_INTERVAL_SECONDS,
    APPROVAL_TIMEOUT_MINUTES,
)
from context_loader import load_all_context, load_scout_briefing, get_stories_from_briefing
from story_selector import select_story
from article_writer import write_article, revise_article
from html_stager import stage_article, get_next_paper_number, build_news_card
from github_publisher import publish_article, commit_vault_file
from learning_logger import log_to_run_log, log_to_learning_log, commit_logs
from telegram_handler import (
    send_review_request, send_publish_confirmation, send_error,
    parse_david_response, format_status_message, send_message,
)

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ──────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("DailyNewsAgent")


# ──────────────────────────────────────────────────────────
# AGENT STATE
# ──────────────────────────────────────────────────────────

class AgentState:
    """Tracks the agent's current workflow state."""

    IDLE = "IDLE"
    SELECTING = "SELECTING"
    WRITING = "WRITING"
    STAGING = "STAGING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EDITING = "EDITING"
    PUBLISHING = "PUBLISHING"
    LOGGING = "LOGGING"

    def __init__(self):
        self.state = self.IDLE
        self.context = {}           # Loaded vault files
        self.briefing = {}          # Content Scout's briefing
        self.stories = []           # Parsed story list
        self.selection = {}         # Selected story + reasoning
        self.article = {}           # Written article data
        self.staged = {}            # Staged HTML data
        self.paper_number = 0
        self.edit_count = 0
        self.edit_notes = []
        self.cycle_start = None
        self.phase_times = {}       # Timing per phase
        self.dry_run = False
        self.pending_response = None  # Asyncio future for David's response

    def reset(self):
        """Reset state for a new cycle."""
        self.__init__()


# Global agent state
agent = AgentState()


# ──────────────────────────────────────────────────────────
# WORKFLOW — The 15-step PROCESS.md as code
# ──────────────────────────────────────────────────────────

async def run_workflow(bot: Bot, dry_run: bool = False):
    """
    Execute the full Daily News Agent workflow.
    Follows PROCESS.md V3.0 steps 1-15.
    """
    agent.dry_run = dry_run
    agent.cycle_start = time.time()

    try:
        # ── Step 1: Content Scout delivers stories ──
        logger.info("═══ DAILY NEWS AGENT — CYCLE START ═══")
        agent.state = AgentState.SELECTING

        # ── Step 2: Load context vault ──
        logger.info("Loading context vault...")
        agent.context = load_all_context()
        logger.info(f"Context loaded: {len(agent.context)} files")

        # ── Step 3: Read Content Scout's briefing ──
        logger.info("Reading Content Scout briefing...")
        agent.briefing = load_scout_briefing()
        agent.stories = get_stories_from_briefing(agent.briefing)

        if not agent.stories:
            logger.warning("No stories found in briefing. Waiting for Content Scout.")
            if not dry_run:
                await send_error(bot, "No stories in today's Content Scout briefing. Skipping cycle.")
            return

        logger.info(f"Found {len(agent.stories)} stories from Content Scout")

        # ── Step 4-5: Select best story (5-filter test + REASONING-CHECKLIST) ──
        phase_start = time.time()
        logger.info("Selecting best story via Grok...")
        agent.selection = select_story(
            stories=agent.stories,
            user_md=agent.context.get("user_md", ""),
            style_md=agent.context.get("style_md", ""),
            reasoning_md=agent.context.get("reasoning_md", ""),
            learning_md=agent.context.get("learning_md", ""),
            run_log_md=agent.context.get("run_log_md", ""),
        )
        agent.phase_times["selection"] = (time.time() - phase_start) / 60

        if agent.selection.get("error"):
            logger.error(f"Story selection failed: {agent.selection['error']}")
            if not dry_run:
                await send_error(bot, f"Story selection failed: {agent.selection['error']}")
            return

        logger.info(f"Selected: {agent.selection.get('title', 'Unknown')} ({agent.phase_times['selection']:.1f} min)")

        # ── Step 6: Write article via Grok ──
        agent.state = AgentState.WRITING
        phase_start = time.time()
        logger.info("Writing article via Grok...")

        selected_story = agent.stories[agent.selection.get("story_index", 0)]
        agent.article = write_article(
            story=selected_story,
            selection=agent.selection,
            user_md=agent.context.get("user_md", ""),
            style_md=agent.context.get("style_md", ""),
            learning_md=agent.context.get("learning_md", ""),
            engagement_md=agent.context.get("engagement_md", ""),
        )
        agent.phase_times["writing"] = (time.time() - phase_start) / 60

        if agent.article.get("error"):
            logger.error(f"Article writing failed: {agent.article['error']}")
            if not dry_run:
                await send_error(bot, f"Article writing failed: {agent.article['error']}")
            return

        logger.info(f"Article written: '{agent.article.get('headline', '')}' ({agent.phase_times['writing']:.1f} min)")

        # ── Step 7: Stage HTML ──
        agent.state = AgentState.STAGING
        phase_start = time.time()
                # -- Step 6b: Generate article image via Grok --
        logger.info("Generating article image via Grok...")
        from image_generator import generate_image, download_image
        image_result = generate_image(
            headline=agent.article.get("headline", ""),
            subtitle=agent.article.get("subtitle", ""),
            category=agent.article.get("category", "AI Research"),
            article_html=agent.article.get("article_html", ""),
        )
        if image_result.get("error"):
            logger.warning(f"Image generation failed (non-fatal): {image_result['error']}")
        else:
            agent.article["image_url"] = image_result["image_url"]
            agent.article["image_caption"] = image_result["image_caption"]
            logger.info("Article image generated successfully")

        # Enrich article data for stager
        agent.article["story_url"] = selected_story.get("url", "")
        agent.article["story_title"] = selected_story.get("title", "")

        agent.paper_number = get_next_paper_number()
        logger.info(f"Staging as Paper {agent.paper_number:03d}...")

        agent.staged = stage_article(agent.article, agent.paper_number)
        agent.phase_times["staging"] = (time.time() - phase_start) / 60

        logger.info(f"Staged: {agent.staged.get('filename', '')} ({agent.phase_times['staging']:.1f} min)")

        # ── Step 8: Send Telegram review to David ──
        agent.state = AgentState.AWAITING_APPROVAL

        if dry_run:
            logger.info("[DRY RUN] Would send Telegram review request")
            logger.info(f"[DRY RUN] Headline: {agent.article.get('headline', '')}")
            logger.info(f"[DRY RUN] Staged at: {agent.staged.get('local_path', '')}")
            logger.info("═══ DRY RUN COMPLETE ═══")
            _print_cycle_summary()
            return

        logger.info("Sending review request to David...")
        await send_review_request(
            bot=bot,
            paper_number=agent.paper_number,
            headline=agent.article.get("headline", ""),
            subtitle=agent.article.get("subtitle", ""),
            category=agent.article.get("category", "AI Research"),
            reasoning=agent.selection.get("reasoning", ""),
            article_preview=agent.article.get("article_html", ""),
            runner_up=agent.selection.get("runner_up", ""),
        )

        # Send image to Telegram if available
        if agent.article.get("image_url"):
            try:
                await bot.send_photo(
                    chat_id=DAVID_CHAT_ID,
                    photo=agent.article["image_url"],
                    caption=f"\ud83d\udcf8 Proposed Figure 1 for Paper {agent.paper_number:03d}"
                )
            except Exception as img_err:
                logger.warning(f"Could not send image to Telegram: {img_err}")

        logger.info("⏳ Waiting for David's response...")
        # Response handling happens in the message handler (handle_message)

    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        if not dry_run:
            try:
                await send_error(bot, f"Workflow error: {str(e)[:200]}")
            except:
                pass


async def handle_approval(bot: Bot, action: str, notes: str = ""):
    """
    Handle David's response to the review request.
    Called from the message handler.
    """
    if action == "approve":
        # ── Step 11-14: Publish ──
        await do_publish(bot)

    elif action == "edit":
        # ── Step 10: Revision cycle ──
        await do_edit(bot, notes)

    elif action == "reject":
        # Kill it
        logger.info("David rejected the article. Cycle ended.")
        await send_message(bot, "❌ Article killed. Back to listening for tomorrow's briefing.")
        agent.state = AgentState.IDLE


async def do_edit(bot: Bot, notes: str):
    """Handle an edit request from David."""
    agent.state = AgentState.EDITING
    agent.edit_count += 1
    agent.edit_notes.append(notes)
    logger.info(f"Edit #{agent.edit_count} requested: {notes}")

    # Revise via Grok
    revision = revise_article(
        original_html=agent.article.get("article_html", ""),
        edit_notes=notes,
        user_md=agent.context.get("user_md", ""),
    )

    if revision.get("error"):
        await send_error(bot, f"Revision failed: {revision['error']}")
        return

    # Update article with revision
    agent.article["article_html"] = revision["article_html"]

    # Re-stage
    agent.staged = stage_article(agent.article, agent.paper_number)

    # Send revised version
    agent.state = AgentState.AWAITING_APPROVAL
    from telegram_handler import format_revision_message
    msg = format_revision_message(agent.paper_number, notes)
    await send_message(bot, msg)
    logger.info("Revised article sent for re-review")


async def do_publish(bot: Bot):
    """Publish the approved article."""
    agent.state = AgentState.PUBLISHING
    phase_start = time.time()
    logger.info(f"Publishing Paper {agent.paper_number:03d}...")

    # Publish to GitHub
    pub_result = publish_article(
        article_filename=agent.staged["filename"],
        article_html=agent.staged["html_content"],
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
    )

    agent.phase_times["approval"] = (time.time() - (agent.phase_times.get("_approval_start", phase_start))) / 60

    if pub_result.get("errors"):
        for err in pub_result["errors"]:
            logger.error(err)
        await send_error(bot, f"Publish errors: {'; '.join(pub_result['errors'])}")
        return

    for step in pub_result.get("steps", []):
        logger.info(step)

    # ── Step 13: Send confirmation ──
        # Commit image to GitHub if we have one
        if agent.article.get("image_url"):
            from image_generator import download_image, commit_image_to_github
            image_bytes = download_image(agent.article["image_url"])
            if image_bytes:
                img_result = commit_image_to_github(image_bytes, agent.paper_number)
                if img_result.get("error"):
                    logger.warning(f"Image commit failed (non-fatal): {img_result['error']}")
                else:
                    logger.info(f"Image committed: {img_result['image_path']}")

    article_url = pub_result.get("article_url", f"https://trainingrun.ai/{agent.staged['filename']}")
    await send_publish_confirmation(bot, agent.paper_number, agent.article.get("headline", ""), article_url)

    # ── Step 14-15: Log to learning engine ──
    agent.state = AgentState.LOGGING
    logger.info("Logging to learning engine...")

    total_cycle = (time.time() - agent.cycle_start) / 60
    first_pass = agent.edit_count == 0

    run_log = log_to_run_log(
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
        source_url=agent.selection.get("url", ""),
        category=agent.article.get("category", "AI Research"),
        cycle_time_minutes=total_cycle,
        edit_count=agent.edit_count,
        first_pass=first_pass,
    )

    learning_log = log_to_learning_log(
        paper_number=agent.paper_number,
        title=agent.article.get("headline", ""),
        selection_time=agent.phase_times.get("selection", 0),
        writing_time=agent.phase_times.get("writing", 0),
        staging_time=agent.phase_times.get("staging", 0),
        approval_time=agent.phase_times.get("approval", 0),
        edit_count=agent.edit_count,
        first_pass=first_pass,
        edit_notes=agent.edit_notes,
    )

    log_result = commit_logs(run_log, learning_log, agent.paper_number)
    for step in log_result.get("steps", []):
        logger.info(step)
    for err in log_result.get("errors", []):
        logger.error(err)

    # Done
    logger.info(f"═══ CYCLE COMPLETE — Paper {agent.paper_number:03d} published in {total_cycle:.1f} min ═══")
    _print_cycle_summary()
    # Mark today as processed (prevents handle_scout_check from re-triggering)
    last_file = STAGING_DIR / ".last_processed_date"
    last_file.write_text(datetime.date.today().isoformat())
    logger.info("Marked today as processed")

    agent.state = AgentState.IDLE


def _print_cycle_summary():
    """Print timing summary to log."""
    logger.info("── Cycle Summary ──")
    for phase, minutes in agent.phase_times.items():
        if not phase.startswith("_"):
            logger.info(f"  {phase}: {minutes:.1f} min")
    logger.info(f"  edits: {agent.edit_count}")


# ──────────────────────────────────────────────────────────
# TELEGRAM BOT — Message handlers
# ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages from David."""
    if not update.message or not update.message.text:
        return

    # Only respond to David
    if update.message.chat_id != DAVID_CHAT_ID:
        return

    text = update.message.text.strip()
    logger.info(f"Message from David: {text[:100]}")

    # Status check
    if text.lower() in ("status", "/status"):
        await update.message.reply_text(format_status_message(), parse_mode="Markdown")
        return

    # Manual trigger
    if text.lower() in ("run", "/run", "go", "start"):
        if agent.state == AgentState.IDLE:
            logger.info("Manual trigger received — starting workflow")
            bot = context.bot
            asyncio.create_task(run_workflow(bot))
        else:
            await update.message.reply_text(f"Agent is busy (state: {agent.state}). Wait for current cycle to finish.")
        return

    # If we're waiting for approval, parse the response
    if agent.state == AgentState.AWAITING_APPROVAL:
        agent.phase_times["_approval_start"] = agent.phase_times.get("_approval_start", time.time())
        response = parse_david_response(text)
        bot = context.bot

        if response["action"] == "unknown":
            # Treat as edit notes if they look like feedback
            if len(text) > 10:
                response["action"] = "edit"
                response["notes"] = text
                await update.message.reply_text("📝 Treating your message as edit feedback. Revising...")
            else:
                await update.message.reply_text(
                    "I didn't understand that. Reply with:\n"
                    "  ✅ push it\n  ✏️ edit: [notes]\n  ❌ kill it"
                )
                return

        await handle_approval(bot, response["action"], response["notes"])
        return


async def handle_scout_check(context: ContextTypes.DEFAULT_TYPE):
    """
    Periodic check: has Content Scout delivered a fresh briefing?
    Runs every 5 minutes. If a fresh briefing is found and agent is idle, trigger workflow.
    """
    if agent.state != AgentState.IDLE:
        return

    # Check if briefing file is fresh (today's date)
    today = datetime.date.today().isoformat()

    briefing = load_scout_briefing()
    brief_date = briefing.get("date", "")

    if brief_date == today and get_stories_from_briefing(briefing):
        # Check if we already processed today
        last_file = STAGING_DIR / ".last_processed_date"
        if last_file.exists() and last_file.read_text().strip() == today:
            return  # Already processed today

        logger.info(f"Fresh Content Scout briefing detected for {today}!")
        last_file.write_text(today)

        bot = context.bot
        await run_workflow(bot)


# ──────────────────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────────────────

def check_config():
    """Verify all required config is present."""
    issues = []
    if not TRNEWZ_BOT_TOKEN:
        issues.append("TRNEWZ_BOT_TOKEN not set")
    if not DAVID_CHAT_ID:
        issues.append("DAVID_CHAT_ID not set")
    if not XAI_API_KEY:
        issues.append("XAI_API_KEY not set")
    if not GITHUB_TOKEN:
        issues.append("GITHUB_TOKEN not set")
    return issues


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Daily News Agent for TrainingRun.AI")
    parser.add_argument("--test", action="store_true", help="Test all connections and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run full workflow without publishing or sending Telegram")
    parser.add_argument("--check", action="store_true", help="Check config and exit")
    args = parser.parse_args()

    # Banner
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║   Daily News Agent — TrainingRun.AI      ║")
    logger.info("║   Powered by Grok (xAI)                  ║")
    logger.info("╚══════════════════════════════════════════╝")

    # Config check
    issues = check_config()
    if issues:
        for issue in issues:
            logger.error(f"CONFIG ERROR: {issue}")
        if not args.check:
            logger.error("Fix .env file and restart.")
            sys.exit(1)
        return

    logger.info("Config OK ✅")

    if args.check:
        logger.info("Config check passed. All required variables are set.")
        return

    # Connection tests
    if args.test:
        logger.info("── Running Connection Tests ──")
        from telegram_handler import test_bot_token
        from story_selector import test_grok_connection
        from github_publisher import test_github_connection
        from context_loader import test_context_loader

        results = []
        results.append(("Telegram", asyncio.run(test_bot_token())))
        results.append(("Grok API", test_grok_connection()))
        results.append(("GitHub API", test_github_connection()))
        results.append(("Context Vault", test_context_loader()))

        logger.info("── Test Results ──")
        all_pass = True
        for name, ok in results:
            status = "✅ PASS" if ok else "❌ FAIL"
            logger.info(f"  {name}: {status}")
            if not ok:
                all_pass = False

        if all_pass:
            logger.info("All tests passed! Agent is ready to run.")
        else:
            logger.error("Some tests failed. Fix issues above before running.")
        return

    # Dry run
    if args.dry_run:
        logger.info("── DRY RUN MODE ──")
        bot = Bot(token=TRNEWZ_BOT_TOKEN)
        asyncio.run(run_workflow(bot, dry_run=True))
        return

    # ── LIVE MODE: Start Telegram bot polling ──
    logger.info("Starting Telegram bot polling...")
    logger.info(f"Listening for Content Scout briefings and David's messages...")
    logger.info(f"Chat ID: {DAVID_CHAT_ID}")

    app = Application.builder().token(TRNEWZ_BOT_TOKEN).build()

    # Message handler — catches all text messages from David
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Command handlers
    app.add_handler(CommandHandler("status", handle_message))
    app.add_handler(CommandHandler("run", handle_message))

    # Periodic job: check for fresh Content Scout briefing every 5 minutes
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(handle_scout_check, interval=300, first=30)
        logger.info("Scout briefing checker: every 5 minutes")

    logger.info("═══ AGENT LIVE — Listening... ═══")

    # Start polling (blocks until Ctrl+C)
    app.run_polling(poll_interval=POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
