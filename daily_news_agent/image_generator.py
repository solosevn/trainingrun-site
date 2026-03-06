"""
Daily News Agent — Image Generator
=====================================
Uses xAI's Grok image generation API to create article visuals.
Produces clean, simple infographic-style images that represent each story.

The generated image is:
1. Sent to David via Telegram for review alongside the article
2. Published as Figure 1 in the article HTML on approval
3. Committed to the GitHub repo in the assets/images/ directory
"""

import base64
import logging
import requests
from openai import OpenAI

from config import XAI_API_KEY, GROK_API_BASE, GITHUB_TOKEN, GITHUB_API_BASE, REPO_BRANCH, IMAGE_DIR

logger = logging.getLogger("DailyNewsAgent.ImageGen")

# -- Image generation model --
GROK_IMAGE_MODEL = "grok-imagine-image"


def build_image_prompt(headline: str, subtitle: str, category: str, article_summary: str = "") -> str:
    """
    Build a prompt for Grok image generation.
    Produces clean, infographic-style visuals - not photorealistic.
    Matches the style of Paper 007's Figure 1.
    """
    prompt = f"""Create a clean, minimal infographic-style illustration for a news article.

ARTICLE:
Title: {headline}
Subtitle: {subtitle}
Category: {category}

STYLE REQUIREMENTS:
- Dark background (deep navy/dark blue, matching #0a0a1a)
- Cyan (#00d4ff) and white as primary accent colors
- Clean, modern, minimalist design
- NO photorealism - use flat design, icons, simple shapes
- Think: tech dashboard or data visualization aesthetic
- Include a clear visual metaphor for the topic
- Large, readable text labels if comparing concepts
- Similar to a simple comparison diagram or key-stat visual
- NO stock photo look - this should feel designed and intentional
- Safe for all audiences, professional tone

{f"CONTEXT: {article_summary[:300]}" if article_summary else ""}

The image should make the article's core concept immediately understandable at a glance.
"""
    return prompt


def generate_image(headline: str, subtitle: str, category: str, article_html: str = "") -> dict:
    """
    Generate an article image via xAI's image generation API.

    Returns dict with:
        - image_url: URL of generated image (hosted by xAI, temporary)
        - image_caption: Suggested caption
        - prompt_used: The prompt sent to Grok
        - error: Error message if failed (None on success)
    """
    if not XAI_API_KEY:
        return {"error": "XAI_API_KEY not set"}

    # Build a short summary from article HTML for context
    article_summary = ""
    if article_html:
        import re
        clean = re.sub(r'<[^>]+>', '', article_html)
        article_summary = clean[:500]

    prompt = build_image_prompt(headline, subtitle, category, article_summary)

    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url=GROK_API_BASE)

        response = client.images.generate(
            model=GROK_IMAGE_MODEL,
            prompt=prompt,
            n=1,
        )

        image_url = response.data[0].url
        caption = f"Visual overview: {subtitle}" if subtitle else f"Visual for {headline}"

        logger.info(f"Image generated successfully: {image_url[:80]}...")

        return {
            "image_url": image_url,
            "image_caption": caption,
            "prompt_used": prompt,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return {
            "image_url": "",
            "image_caption": "",
            "prompt_used": prompt,
            "error": f"Image generation failed: {e}",
        }


def download_image(image_url: str) -> bytes:
    """
    Download the generated image from the temporary xAI URL.
    Returns image bytes.
    """
    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return b""


def commit_image_to_github(image_bytes: bytes, paper_number: int) -> dict:
    """
    Commit the article image to GitHub at assets/images/paper-NNN.png

    Returns dict with:
        - image_path: repo path of committed image
        - image_github_url: raw URL for the image
        - error: error message if failed
    """
    if not image_bytes:
        return {"error": "No image data to commit"}

    if not GITHUB_TOKEN:
        return {"error": "GITHUB_TOKEN not set"}

    # Determine path
    image_filename = f"paper-{paper_number:03d}.png"
    image_path = f"{IMAGE_DIR}{image_filename}"

    # Encode to base64
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    # Check if file already exists (to get sha for update)
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"{GITHUB_API_BASE}/contents/{image_path}?ref={REPO_BRANCH}"
    existing = requests.get(url, headers=headers, timeout=15)
    sha = None
    if existing.status_code == 200:
        sha = existing.json().get("sha")

    # Commit
    payload = {
        "message": f"Add image for Paper {paper_number:03d}",
        "content": encoded,
        "branch": REPO_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    put_url = f"{GITHUB_API_BASE}/contents/{image_path}"
    try:
        resp = requests.put(put_url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        image_github_url = f"https://raw.githubusercontent.com/solosevn/trainingrun-site/main/{image_path}"

        logger.info(f"Image committed to GitHub: {image_path}")

        return {
            "image_path": image_path,
            "image_github_url": image_github_url,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Failed to commit image: {e}")
        return {"error": f"Failed to commit image: {e}"}


# ----------------------------------------------------------------
# TEST
# ----------------------------------------------------------------
def test_image_generation():
    """Quick test: verify image generation works."""
    if not XAI_API_KEY:
        print("[ImageGen] \u274c XAI_API_KEY not set")
        return False

    try:
        result = generate_image(
            headline="Test: AI Makes Code More Reliable",
            subtitle="A new approach improves coding accuracy by 15%",
            category="AI Research",
        )
        if result.get("error"):
            print(f"[ImageGen] \u274c {result['error']}")
            return False

        print(f"[ImageGen] \u2705 Image generated: {result['image_url'][:60]}...")
        return True
    except Exception as e:
        print(f"[ImageGen] \u274c Test failed: {e}")
        return False


if __name__ == "__main__":
    test_image_generation()
