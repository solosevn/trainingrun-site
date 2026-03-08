"""
Daily News Agent — Article Writer
===================================
Uses Grok API to write a full article in David Solomon's voice.
Reads personality from USER.md, style rules from STYLE-EVOLUTION.md.
"""

import datetime
from openai import OpenAI
from config import XAI_API_KEY, GROK_API_BASE, GROK_MODEL


def build_writing_prompt(story: dict, selection: dict, user_md: str, style_md: str, learning_md: str = "", engagement_md: str = "") -> str:
    """
    Build the Grok prompt for article writing.
    Includes David's voice, style rules, and the selected story.
    """
    today = datetime.date.today().strftime("%B %d, %Y")
    category = selection.get("category", "AI Research")

    prompt = f"""You are writing today's Daily News article for David Solomon's trainingrun.ai.

═══════════════════════════════════════════
DAVID'S VOICE (you ARE David writing this):
═══════════════════════════════════════════
{user_md[:2500]}

═══════════════════════════════════════════
STYLE RULES (learned from past articles — follow these):
═══════════════════════════════════════════
{style_md[:2000] if style_md.strip() else "No learned rules yet. Use David's natural voice: warm, direct, confident. Problem → Solution → Why it matters."}

═══════════════════════════════════════════
WHAT WORKED BEFORE (learn from past articles):
═══════════════════════════════════════════
{learning_md[-6000:] if learning_md.strip() else "No learning data yet — this is early."}

═══════════════════════════════════════════
AUDIENCE RESPONSE DATA (what readers actually engaged with):
═══════════════════════════════════════════
{engagement_md[-5000:] if engagement_md.strip() else "No engagement data yet — this is early."}

USE THIS TO:
- Match the tone/format of articles that got strong engagement
- Avoid patterns readers didn't respond to
- Write for the topics/angles that resonate most
- Apply David's editorial feedback from past cycles

═══════════════════════════════════════════
THE STORY TO WRITE ABOUT:
═══════════════════════════════════════════
Title: {story.get('title', 'Untitled')}
Source: {story.get('source', '')}
URL: {story.get('url', '')}
Summary: {story.get('summary', '')}
Truth Score: {story.get('truth_score', 0)}/100
AI Verdict: {story.get('ai_verdict', 'UNVERIFIED')}
Category: {category}
Selection Reasoning: {selection.get('reasoning', '')}

═══════════════════════════════════════════
ARTICLE REQUIREMENTS:
═══════════════════════════════════════════
1. STRUCTURE: Problem first → Solution second → Why it matters third
2. LENGTH: 600-1000 words (tight, no padding)
3. VOICE: Warm, direct, confident — like David talking to a smart friend
4. AUDIENCE: Intelligent non-technical person (David's family, friends, professionals)
5. TERMS: Layman's terms throughout. If you use a technical term, explain it immediately.
6. OPENING: Hook the reader in 2 sentences. State the problem.
7. NO CLICKBAIT: No "mind-blowing", "game-changing", or hype language
8. CREDIT: Always cite the original authors and their institution
9. FIRST PERSON: Use "I" where natural (David's perspective)
10. SIGN-OFF: End with David's perspective on why this matters

═══════════════════════════════════════════
CITATION FORMAT (required at end of article):
═══════════════════════════════════════════
Source Paper: [Full paper title]
Authors: [All authors, institution(s)]
Published: [Date] | [Venue/Journal if applicable]
Link: [URL]

═══════════════════════════════════════════
OUTPUT FORMAT:
═══════════════════════════════════════════
Return the article in this exact structure:

HEADLINE: [Your headline — clear, factual, not clickbait]
SUBTITLE: [One-line summary, 10-15 words]
CATEGORY: {category}
DATE: {today}

---ARTICLE START---
[Full article text in HTML paragraphs]
[Use <p> tags for paragraphs]
[Use <h2> for section headers if needed (max 2)]
[Use <strong> sparingly for emphasis]
[Include at least one place where an image would go: <!-- IMAGE: description of ideal image -->]
---ARTICLE END---

---CITATION START---
[Full citation block]
---CITATION END---
"""
    return prompt


def write_article(story: dict, selection: dict, user_md: str, style_md: str, learning_md: str = "", engagement_md: str = "") -> dict:
    """
    Call Grok API to write the full article.
    Returns dict with: headline, subtitle, category, date, article_html, citation, raw_response.
    """
    if not XAI_API_KEY:
        return {"error": "XAI_API_KEY not set"}

    client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)
    prompt = build_writing_prompt(story, selection, user_md, style_md, learning_md, engagement_md)

    try:
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are David Solomon, writing your daily AI news article. "
                    "Write in first person. Be warm, direct, and factual. "
                    "Your readers are smart people who don't speak AI jargon."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.75,     # Slightly creative for writing
            max_tokens=3000,
        )

        reply = response.choices[0].message.content.strip()
        result = parse_article_response(reply)
        result["raw_response"] = reply
        result["model"] = GROK_MODEL

        # Fallback: if category wasn't parsed, use selection's
        if not result.get("category"):
            result["category"] = selection.get("category", "AI Research")

        return result

    except Exception as e:
        return {"error": f"Grok article writing failed: {e}"}


def parse_article_response(reply: str) -> dict:
    """
    Parse Grok's article output into structured data.
    """
    result = {
        "headline": "",
        "subtitle": "",
        "category": "",
        "date": "",
        "article_html": "",
        "citation": "",
    }

    lines = reply.split("\n")

    # Extract header fields
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("HEADLINE:"):
            result["headline"] = line_stripped.replace("HEADLINE:", "").strip()
        elif line_stripped.startswith("SUBTITLE:"):
            result["subtitle"] = line_stripped.replace("SUBTITLE:", "").strip()
        elif line_stripped.startswith("CATEGORY:"):
            result["category"] = line_stripped.replace("CATEGORY:", "").strip()
        elif line_stripped.startswith("DATE:"):
            result["date"] = line_stripped.replace("DATE:", "").strip()

    # Extract article body
    article_start = reply.find("---ARTICLE START---")
    article_end = reply.find("---ARTICLE END---")
    if article_start != -1 and article_end != -1:
        result["article_html"] = reply[article_start + len("---ARTICLE START---"):article_end].strip()

    # Extract citation
    cite_start = reply.find("---CITATION START---")
    cite_end = reply.find("---CITATION END---")
    if cite_start != -1 and cite_end != -1:
        result["citation"] = reply[cite_start + len("---CITATION START---"):cite_end].strip()

    # Fallback: if markers weren't used, try to extract content after headers
    if not result["article_html"]:
        # Find the first <p> tag or substantial text block
        in_content = False
        content_lines = []
        for line in lines:
            if line.strip().startswith("<p>") or line.strip().startswith("<h2>"):
                in_content = True
            if in_content:
                if line.strip().startswith("---CITATION") or line.strip().startswith("Source Paper:"):
                    break
                content_lines.append(line)
        if content_lines:
            result["article_html"] = "\n".join(content_lines).strip()

    # Fallback citation: find "Source Paper:" block
    if not result["citation"]:
        cite_idx = reply.find("Source Paper:")
        if cite_idx != -1:
            result["citation"] = reply[cite_idx:].strip()

    return result


def revise_article(original_html: str, edit_notes: str, user_md: str) -> dict:
    """
    Revise an article based on David's edit feedback.
    Called during the edit cycle (Step 10 in PROCESS.md).
    """
    if not XAI_API_KEY:
        return {"error": "XAI_API_KEY not set"}

    client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)

    prompt = f"""You wrote this article for David Solomon and he wants revisions.

ORIGINAL ARTICLE:
{original_html}

DAVID'S FEEDBACK:
{edit_notes}

DAVID'S VOICE (reminder):
{user_md[:1500]}

INSTRUCTIONS:
- Apply David's specific feedback
- Keep the overall structure and voice
- Only change what David asked to change
- Return the FULL revised article (not just the changed parts)

Return the revised article between ---ARTICLE START--- and ---ARTICLE END--- markers.
"""

    try:
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": "You are revising an article based on editorial feedback. Apply the changes precisely."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=3000,
        )

        reply = response.choices[0].message.content.strip()

        # Extract revised article
        start = reply.find("---ARTICLE START---")
        end = reply.find("---ARTICLE END---")
        if start != -1 and end != -1:
            revised = reply[start + len("---ARTICLE START---"):end].strip()
        else:
            revised = reply  # Fallback: use whole response

        return {
            "article_html": revised,
            "raw_response": reply,
            "model": GROK_MODEL,
        }

    except Exception as e:
        return {"error": f"Grok revision failed: {e}"}


if __name__ == "__main__":
    print("[ArticleWriter] Module loaded. Use write_article() or revise_article().")
