"""
Daily News Agent — Telegram Handler
======================================
Manages all Telegram communication:
  - Detects Content Scout's briefing delivery
  - Sends David review requests
  - Handles approval / edit / kill responses
  - Sends publish confirmations
"""

import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from config import TRNEWZ_BOT_TOKEN, DAVID_CHAT_ID

logger = logging.getLogger("DailyNewsAgent.Telegram")


# ──────────────────────────────────────────────────────────
# MESSAGE TEMPLATES (from CONFIG.md)
# ──────────────────────────────────────────────────────────

def format_review_message(paper_number: int, headline: str, subtitle: str,
                          category: str, reasoning: str, runner_up: str = "") -> str:
    """Format the Telegram message sent to David for review."""
    msg = (
        f"📰 *Paper {paper_number:03d} — Ready for Review*\n\n"
        f"*{headline}*\n"
        f"_{subtitle}_\n\n"
        f"🏷 Category: {category}\n"
        f"📝 Why this story: {reasoning}\n"
    )
    if runner_up:
        msg += f"\n🥈 Runner-up: {runner_up}\n"

    msg += (
        f"\n─────────────────────\n"
        f"Reply with:\n"
        f"  ✅ *push it* — publish as-is\n"
        f"  ✏️ *edit: [your notes]* — revise and re-send\n"
        f"  ❌ *kill it* — discard this story\n"
    )
    return msg


def format_draft_preview(article_html: str, max_chars: int = 800) -> str:
    """Create a readable Telegram preview of the article draft."""
    import re
    # Strip HTML tags for preview
    text = re.sub(r'<[^>]+>', '', article_html)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return f"📄 *Draft Preview:*\n\n{text}"


def format_revision_message(paper_number: int, changes: str) -> str:
    """Format the message sent after a revision."""
    return (
        f"✏️ *Paper {paper_number:03d} — Revised*\n\n"
        f"Changes made: {changes}\n\n"
        f"Reply:\n"
        f"  ✅ *push it* — publish revised version\n"
        f"  ✏️ *edit: [more notes]* — another round\n"
        f"  ❌ *kill it* — discard\n"
    )


def format_publish_confirmation(paper_number: int, title: str, url: str) -> str:
    """Format the publish confirmation message."""
    return (
        f"✅ *Paper {paper_number:03d} Published!*\n\n"
        f"📰 {title}\n"
        f"🔗 {url}\n\n"
        f"RUN-LOG and LEARNING-LOG updated.\n"
        f"GitHub Pages deploying now — live in ~60 seconds."
    )


def format_error_message(error: str) -> str:
    """Format an error notification."""
    return f"⚠️ *Daily News Agent Error*\n\n{error}\n\nAgent is still running. Check logs for details."


def format_status_message() -> str:
    """Format a status check response."""
    import datetime
    now = datetime.datetime.now().strftime("%I:%M %p CST")
    return (
        f"🤖 *Daily News Agent Status*\n\n"
        f"⏰ Time: {now}\n"
        f"📡 Status: Listening for Content Scout\n"
        f"✅ All systems operational"
    )


# ──────────────────────────────────────────────────────────
# RESPONSE PARSING
# ──────────────────────────────────────────────────────────

def parse_david_response(text: str) -> dict:
    """
    Parse David's Telegram response.
    Returns: {"action": "approve"|"edit"|"reject"|"unknown", "notes": "..."}
    """
    text_lower = text.strip().lower()

    # Approve
    if text_lower in ("push it", "push", "approve", "approved", "yes", "go", "send it", "publish"):
        return {"action": "approve", "notes": ""}

    # Edit
    if text_lower.startswith("edit:") or text_lower.startswith("edit "):
        notes = text.strip()
        if notes.lower().startswith("edit:"):
            notes = notes[5:].strip()
        elif notes.lower().startswith("edit "):
            notes = notes[5:].strip()
        return {"action": "edit", "notes": notes}

    # Reject
    if text_lower in ("kill it", "kill", "no", "reject", "skip", "pass", "nope", "drop it"):
        return {"action": "reject", "notes": ""}

    # Unknown — treat as edit notes if we're in approval state
    return {"action": "unknown", "notes": text.strip()}


# ──────────────────────────────────────────────────────────
# BOT SEND FUNCTIONS
# ──────────────────────────────────────────────────────────

async def send_message(bot: Bot, text: str, parse_mode: str = "Markdown") -> None:
    """Send a message to David via Telegram."""
    try:
        await bot.send_message(
            chat_id=DAVID_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        # Retry without parse mode (in case of markdown issues)
        try:
            await bot.send_message(chat_id=DAVID_CHAT_ID, text=text)
        except Exception as e2:
            logger.error(f"Retry also failed: {e2}")


async def send_review_request(bot: Bot, paper_number: int, headline: str,
                               subtitle: str, category: str, reasoning: str,
                               article_preview: str, runner_up: str = "") -> None:
    """Send the full review request (review message + draft preview)."""
    review_msg = format_review_message(paper_number, headline, subtitle, category, reasoning, runner_up)
    await send_message(bot, review_msg)

    # Send preview as separate message (can be long)
    if article_preview:
        preview = format_draft_preview(article_preview)
        await send_message(bot, preview)


async def send_publish_confirmation(bot: Bot, paper_number: int, title: str, url: str) -> None:
    """Send publish confirmation to David."""
    msg = format_publish_confirmation(paper_number, title, url)
    await send_message(bot, msg)


async def send_error(bot: Bot, error: str) -> None:
    """Send error notification to David."""
    msg = format_error_message(error)
    await send_message(bot, msg)


# ──────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────

async def test_bot_token():
    """Quick test: verify Telegram bot token works."""
    if not TRNEWZ_BOT_TOKEN:
        print("[TelegramHandler] ❌ TRNEWZ_BOT_TOKEN not set")
        return False
    try:
        bot = Bot(token=TRNEWZ_BOT_TOKEN)
        me = await bot.get_me()
        print(f"[TelegramHandler] ✅ Bot connected: @{me.username} ({me.first_name})")
        return True
    except Exception as e:
        print(f"[TelegramHandler] ❌ Bot connection failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_bot_token())
