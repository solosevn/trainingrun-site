"""
Daily News Agent — Story Selector
===================================
Uses Grok API to select the best story from Content Scout's briefing.
Applies David's 5-filter test + REASONING-CHECKLIST.
"""

from openai import OpenAI
from config import XAI_API_KEY, GROK_API_BASE, GROK_FAST_MODEL


def build_selection_prompt(stories: list, user_md: str, style_md: str, reasoning_md: str) -> str:
    """
    Build the Grok prompt for story selection.
    Includes David's 5-filter test, style evolution rules, and story data.
    """
    story_block = ""
    for i, story in enumerate(stories, 1):
        story_block += f"""
STORY #{i}: {story.get('title', 'Untitled')}
  Source: {story.get('source', 'unknown')} | URL: {story.get('url', '')}
  Truth Score: {story.get('truth_score', 0)}/100
  AI Verdict: {story.get('ai_verdict', 'UNVERIFIED')}
  Category: {story.get('category_label', story.get('tr_category', 'general'))}
  Summary: {story.get('summary', 'No summary available')}
"""

    prompt = f"""You are the story selection engine for David Solomon's Daily News Agent.
David writes a daily AI news article for trainingrun.ai. Your job: pick the ONE best story.

═══════════════════════════════════════════
WHO DAVID IS (read carefully — this shapes everything):
═══════════════════════════════════════════
{user_md[:2000]}

═══════════════════════════════════════════
CURRENT STYLE RULES (learned from past articles):
═══════════════════════════════════════════
{style_md[:1500] if style_md.strip() else "No style rules yet — this is early. Use David's voice from USER.md."}

═══════════════════════════════════════════
TODAY'S STORIES FROM CONTENT SCOUT:
═══════════════════════════════════════════
{story_block}

═══════════════════════════════════════════
YOUR TASK — Apply David's 5-Filter Test:
═══════════════════════════════════════════
For EACH story, score these filters (1-5 scale):

1. TRUTH: Is this substantive research or sensationalism? (arXiv > blog hype)
2. RELEVANCE: Can David explain this to a non-technical person? Does it matter to real people?
3. PROBLEM-SOLVING: Does it address a real problem? Clear problem→solution framing?
4. CREDIBILITY: Is the source reputable? Peer-reviewed? Multiple confirmations?
5. TIMELINESS: Is this breaking/fresh, or already everywhere?

Also consider:
- Content Scout's truth score (higher = more verified)
- AI verification status (AI_VERIFIED > LIKELY_TRUE > WARNING)
- Would David's kids understand why this matters?

═══════════════════════════════════════════
REASONING DISCIPLINE:
═══════════════════════════════════════════
{reasoning_md[:1000]}

═══════════════════════════════════════════
OUTPUT FORMAT (follow exactly):
═══════════════════════════════════════════
SELECTED: [story number]
TITLE: [exact title]
URL: [exact URL]
CATEGORY: [one of: AI Safety, AI Research, AI Ethics, AI Tools, AI Policy, AI Agents, Machine Learning, Open Source, AI in Medicine, AI in Business, Compute & Infrastructure]
REASONING: [2-3 sentences — why this story, through David's lens]
RUNNER_UP: [story number] — [title] — [one line why it was close]
"""
    return prompt


def select_story(stories: list, user_md: str, style_md: str, reasoning_md: str) -> dict:
    """
    Call Grok API to select the best story.
    Returns dict with: story_index, title, url, category, reasoning, runner_up.
    """
    if not stories:
        return {"error": "No stories to select from"}

    if not XAI_API_KEY:
        return {"error": "XAI_API_KEY not set"}

    client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)
    prompt = build_selection_prompt(stories, user_md, style_md, reasoning_md)

    try:
        response = client.chat.completions.create(
            model=GROK_FAST_MODEL,
            messages=[
                {"role": "system", "content": "You are a story selection agent. Be decisive. Pick ONE story."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,      # Lower temp for analytical decisions
            max_tokens=600,
        )

        reply = response.choices[0].message.content.strip()
        result = parse_selection_response(reply, stories)
        result["raw_response"] = reply
        result["model"] = GROK_FAST_MODEL
        return result

    except Exception as e:
        return {"error": f"Grok API call failed: {e}"}


def parse_selection_response(reply: str, stories: list) -> dict:
    """
    Parse Grok's selection response into structured data.
    """
    result = {
        "story_index": 0,
        "title": "",
        "url": "",
        "category": "",
        "reasoning": "",
        "runner_up": "",
    }

    for line in reply.split("\n"):
        line = line.strip()
        if line.startswith("SELECTED:"):
            try:
                idx = int(line.replace("SELECTED:", "").strip()) - 1
                result["story_index"] = idx
                if 0 <= idx < len(stories):
                    result["title"] = stories[idx].get("title", "")
                    result["url"] = stories[idx].get("url", "")
            except ValueError:
                pass
        elif line.startswith("TITLE:"):
            result["title"] = line.replace("TITLE:", "").strip()
        elif line.startswith("URL:"):
            result["url"] = line.replace("URL:", "").strip()
        elif line.startswith("CATEGORY:"):
            result["category"] = line.replace("CATEGORY:", "").strip()
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.replace("REASONING:", "").strip()
        elif line.startswith("RUNNER_UP:"):
            result["runner_up"] = line.replace("RUNNER_UP:", "").strip()

    # Fallback: if parsing missed the story, grab from stories list
    idx = result["story_index"]
    if not result["title"] and 0 <= idx < len(stories):
        result["title"] = stories[idx].get("title", "")
        result["url"] = stories[idx].get("url", "")

    return result


# ──────────────────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────────────────

def test_grok_connection():
    """Quick test: verify Grok API works."""
    if not XAI_API_KEY:
        print("[StorySelector] ❌ XAI_API_KEY not set")
        return False
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)
        response = client.chat.completions.create(
            model=GROK_FAST_MODEL,
            messages=[{"role": "user", "content": "Say 'connection verified' in 3 words or less."}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content.strip()
        print(f"[StorySelector] ✅ Grok API connected: '{reply}'")
        return True
    except Exception as e:
        print(f"[StorySelector] ❌ Grok API failed: {e}")
        return False


if __name__ == "__main__":
    test_grok_connection()
