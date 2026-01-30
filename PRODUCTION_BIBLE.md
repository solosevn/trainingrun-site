# TRAINING RUN - Production Bible

**Show:** Training Run - The AI Scoreboard
**Format:** Weekly YouTube show (drops every Thursday)
**Website:** https://trainingrun.ai
**GitHub Repo:** https://github.com/solosevn/trainingrun-site

---

## WHAT IS TRAINING RUN?

A weekly AI news show that tracks and scores AI model performance. We aggregate data from respected benchmarks (LMSYS Arena, SWE-Bench, ARC-AGI) and deliver it in an engaging video format with AI-generated avatars.

**Core Philosophy:** Independent, transparent, fact-checked rankings. No hype - just data.

---

## WEEKLY PRODUCTION WORKFLOW

### PHASE 1: Research & Data (Monday-Tuesday)

**1. Gather Current Scores**
- LMSYS Arena: https://chat.lmsys.org/ (Elo ratings, human preference)
- SWE-Bench: https://www.swebench.com/ (coding benchmarks)
- ARC Prize: https://arcprize.org/ (reasoning/AGI benchmarks)

**2. Calculate TRS (Training Run Score)**
TRS is a weighted composite:
- Reasoning: 25%
- Coding: 25%
- Human Preference: 20%
- Knowledge: 15%
- Efficiency: 10%
- Safety: 5%

**3. Track Week-over-Week Changes**
- Note which models moved up/down
- Identify "Rookie of the Week" (biggest mover)
- Track any new model entries

**4. Gather News Stories**
Look for 3 major AI stories of the week:
- Company news (earnings, crashes, acquisitions)
- Policy/regulation (tariffs, laws, government action)
- Model releases/announcements

**5. Jobs Data**
Track AI job market:
- Jobs eliminated (with AI as contributing factor)
- Jobs created (AI-related positions)
- Net change

---

### PHASE 2: Scriptwriting (Tuesday-Wednesday)

**Show Structure (36 Scenes):**

| Scene | Avatar | Content |
|-------|--------|---------|
| 1-3 | Kennedy | Cold open, intro |
| 4A-4C | Frank | Co-host intro |
| 5-8 | Frank | Scoreboard rundown |
| 9 | Kennedy | Intro for Scout |
| 10-11 | Scout | Rookie of the Week |
| 12 | Kennedy | Intro for Dev |
| 13-16 | Dev | Category Leaders |
| 17-18 | Kennedy | Daily Download (news) |
| 19 | Kennedy | Intro for Dr. Arc |
| 20-21 | Dr. Arc | Frontier/ARC-AGI |
| 22 | Kennedy | Intro for Harper |
| 23-24 | Harper | Jobs/Human Factor |
| 25 | Kennedy | Intro for Atlas |
| 26-27 | Atlas | Global AI Race |
| 28 | Kennedy | Intro for Volt |
| 29-30 | Volt | Power/Megawatts |
| 31 | Kennedy | Intro for Ace |
| 32-33 | Ace | Predictions |
| 34 | Frank | Sign-off |
| 35 | Kennedy | Sign-off |
| 36 | Frank | Final sign-off |

**Avatar Roster:**
- **Kennedy** - Main host (human-style avatar)
- **Frank** - Co-host, close-up Pixar style
- **Scout** - Rookie segment
- **Dev** - Category Leaders/Coding
- **Dr. Arc** - Frontier/Reasoning
- **Harper** - Jobs/Human Factor
- **Atlas** - Global Race
- **Volt** - Power consumption
- **Ace** - Predictions

**Script Style Guide:**
- Short sentences. Punchy delivery.
- Numbers spoken naturally ("seventy-five point nine percent")
- No hype words - just facts
- Each avatar has distinct personality/voice

---

### PHASE 3: Video Production (Wednesday-Thursday)

**1. HeyGen Avatar Generation**
- Platform: https://heygen.com
- Create video for each scene
- Use consistent avatar settings
- Export as MP4

**2. Premiere Pro Assembly**
- Import all HeyGen clips
- Add B-roll for news segments
- Add scoreboard graphics
- Add lower thirds
- Add music/sound design

**3. Graphics Needed Each Week**
- Scoreboard graphic (top 10 models with TRS scores)
- Individual model cards
- News story B-roll
- Lower thirds for each avatar
- End screen with trainingrun.ai

**4. Thumbnail Creation**
- 1280x720 pixels
- High contrast, readable text
- Include week number
- Highlight biggest story

**Export Settings (Premiere Pro):**
- Format: H.264
- Preset: YouTube 1080p Full HD
- Bitrate: 16 Mbps (VBR 2-pass)
- Audio: AAC 320kbps
- Check: "Use Maximum Render Quality"

---

### PHASE 4: Website Update (Thursday)

**GitHub Repository:** solosevn/trainingrun-site

**Files to Update:**

1. **scores.html** - Update TRS scores
   - Find each model's trs-score span
   - Update the score value
   - Update the change indicator (+/- amount)
   - Update the "Week of [DATE]" text

2. **index.html** - Update if needed
   - "Watch Now" button links to latest YouTube video
   - Date badge is now dynamic (auto-updates)

**How to Edit via GitHub:**
1. Go to: https://github.com/solosevn/trainingrun-site
2. Click on file to edit (scores.html or index.html)
3. Click pencil icon (Edit)
4. Make changes
5. Click "Commit changes"
6. Site auto-deploys in 1-2 minutes

**Current YouTube Link Location:**
- File: index.html
- Line ~161: href="https://www.youtube.com/watch?v=VIDEO_ID"
- Update VIDEO_ID each week

---

### PHASE 5: Publish (Thursday)

**1. Upload to YouTube**
- Title format: "[Headline] | AI Scoreboard Week [X]"
- Description: Include timestamps, sources, links
- Tags: AI, artificial intelligence, GPT, Claude, Gemini, etc.
- Thumbnail: Custom 1280x720

**2. Update Website**
- Add new YouTube link to "Watch Now" button
- Verify scores page is current

**3. Promote**
- Social media posts
- Newsletter if applicable

---

## WEBSITE STRUCTURE

trainingrun.ai/
- index.html (Homepage)
- scores.html (TRS Scoreboard)
- trsmethodology.html (How we calculate TRS)
- about.html (About page)
- styles.css (Styling)
- CNAME (Domain config)

**Key Website Features:**
- Dynamic date on homepage (JavaScript auto-updates)
- Responsive design
- Dark theme with cyan/orange accents
- Links to data sources (LMSYS, ARC Prize, SWE-Bench)

---

## CURRENT TRS SCORES (Week 4 - January 26, 2026)

| Rank | Model | Company | TRS | Change |
|------|-------|---------|-----|--------|
| 1 | Gemini 3 Pro | Google | 95.4 | +0.1 |
| 2 | Grok 4.1 | xAI | 94.8 | +0.3 |
| 3 | Claude Opus 4.5 | Anthropic | 94.3 | +0.2 |
| 4 | GPT-5.1 | OpenAI | 93.2 | -0.2 |
| 5 | Gemini 3 Flash | Google | 93.0 | +0.4 |
| 6 | Ernie 5.0 | Baidu | 91.8 | +1.8 |
| 7 | Claude Sonnet 4.5 | Anthropic | 90.9 | +0.2 |
| 8 | DeepSeek V3.2 | DeepSeek | 89.7 | +0.5 |
| 9 | Qwen 3 Max | Alibaba | 88.5 | +0.2 |
| 10 | Llama 4 Maverick | Meta | 86.2 | -0.2 |

---

## DATA SOURCES

**Primary Benchmarks:**
- LMSYS Chatbot Arena: https://chat.lmsys.org/
- SWE-Bench Verified: https://www.swebench.com/
- ARC-AGI-2: https://arcprize.org/

**Secondary Sources:**
- Company earnings reports
- Official model announcements
- Verified news sources (Bloomberg, Reuters, TechCrunch)

---

## BRAND GUIDELINES

**Colors:**
- Primary: Cyan (#00D4FF)
- Accent: Orange (#FF6400)
- Background: Dark navy (#0A1420)
- Text: White (#FFFFFF)

**Fonts:**
- Headlines: Inter (bold/black weight)
- Body: Inter (regular)

**Tone:**
- Authoritative but accessible
- Data-driven, not hype-driven
- Slight wit, never sarcastic
- "Your weekly AI conditioning"

---

## QUICK START FOR NEW WEEK

When starting a new week, tell Claude:

"Let's start Training Run Week [X]. Pull up the Production Bible at:
https://github.com/solosevn/trainingrun-site/blob/main/PRODUCTION_BIBLE.md

I need to:
1. Research current benchmark scores
2. Write scripts for all segments  
3. Update the website with new scores
4. Add the new YouTube link when ready"

---

## TROUBLESHOOTING

**Website not updating after GitHub commit:**
- GitHub Pages cache takes 1-5 minutes
- Try hard refresh: Ctrl+Shift+R
- Try adding ?v=2 to URL to bust cache

**HeyGen avatar issues:**
- Keep scripts under 60 seconds per scene
- Avoid complex words that might mispronounce
- Use phonetic spelling if needed

**Score discrepancies:**
- Always cite primary source
- Note date of benchmark data
- If sources conflict, use most recent

---

## GENERATING GRAPHICS (Terminal/Python)

The simplest way to create graphics (thumbnails, title cards, end cards) is to run Python directly in Mac Terminal.

**Requirements:** Python 3 with Pillow (`pip3 install Pillow`)

**TikTok Title Card (1080x1920):**
```bash
cd ~/Desktop && python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (1080, 1920), (10, 20, 40))
draw = ImageDraw.Draw(img)

try:
    font_huge = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
    font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except:
    font_huge = font_large = font_medium = font_small = ImageFont.load_default()

CYAN = (0, 212, 255)
WHITE = (255, 255, 255)
ORANGE = (255, 100, 0)
GREY = (180, 180, 180)

draw.rounded_rectangle([(380, 500), (700, 550)], radius=25, outline=CYAN, width=2)
draw.text((540, 525), "DATE HERE", font=font_small, fill=CYAN, anchor='mm')
draw.text((540, 700), "Training", font=font_huge, fill=CYAN, anchor='mm')
draw.text((540, 830), "Run", font=font_huge, fill=CYAN, anchor='mm')
draw.text((540, 950), "YOUR WEEKLY AI CONDITIONING", font=font_medium, fill=GREY, anchor='mm')
draw.text((540, 1100), "WEEK X", font=font_large, fill=ORANGE, anchor='mm')
draw.text((540, 1300), "AI SCOREBOARD", font=font_large, fill=WHITE, anchor='mm')
draw.text((540, 1450), "Headline 1", font=font_medium, fill=CYAN, anchor='mm')
draw.text((540, 1510), "Headline 2", font=font_medium, fill=CYAN, anchor='mm')
draw.text((540, 1570), "Headline 3", font=font_medium, fill=CYAN, anchor='mm')

img.save("tiktok_title.png")
print("Saved to Desktop: tiktok_title.png")
EOF
```

**TikTok End Card (1080x1920):**
```bash
cd ~/Desktop && python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (1080, 1920), (10, 20, 40))
draw = ImageDraw.Draw(img)

try:
    font_huge = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
    font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
except:
    font_huge = font_large = ImageFont.load_default()

CYAN = (0, 212, 255)
WHITE = (255, 255, 255)

draw.text((540, 860), "trainingrun.ai", font=font_huge, fill=CYAN, anchor='mm')
draw.text((540, 1000), "FULL EPISODE EVERY THURSDAY", font=font_large, fill=WHITE, anchor='mm')

img.save("tiktok_endcard.png")
print("Saved to Desktop: tiktok_endcard.png")
EOF
```

**How to use:**
1. Open Terminal on Mac
2. 2. Copy entire code block
   3. 3. Paste into Terminal and press Enter
      4. 4. Image saves to Desktop
        
         5. ---
        
         6. ## VERSION HISTORY

- **v1.0** (January 30, 2026) - Initial production bible created after Week 4

---

*Last updated: January 30, 2026*
