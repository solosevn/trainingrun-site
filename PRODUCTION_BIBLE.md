# TRAINING RUN - Production Bible

**Show:** Training Run - The AI Scoreboard
**Format:** Weekly YouTube show (drops every Thursday)
**Website:** https://trainingrun.ai
**GitHub Repo:** https://github.com/solosevn/trainingrun-site

---

## WHAT IS TRAINING RUN?

A weekly AI news show that tracks and scores AI model performance. We aggregate data from respected benchmarks (LMSYS Arena, SWE-Bench, ARC-AGI, HELM Safety, TrustLLM, MLCommons AILuminate, OpenRouter) and deliver it in an engaging video format with AI-generated avatars.

**Core Philosophy:** Independent, transparent, fact-checked rankings. No hype - just data.

---

## WEEKLY PRODUCTION WORKFLOW

### PHASE 1: Research & Data (Monday-Tuesday)

**1. Gather Current Scores**
- LMSYS Arena: https://huggingface.co/spaces/lmarena-ai/chatbot-arena/ (Elo ratings, human preference)
- SWE-Bench: https://www.swebench.com/ (coding benchmarks)
- ARC Prize: https://arcprize.org/ (reasoning/AGI benchmarks)

**2. Calculate TRS (Training Run Score)**
TRS is a weighted composite (V2.4):
- Safety: 21%
- Reasoning: 20%
- Coding: 20%
- Human Preference: 18%
- Knowledge: 8%
- Efficiency: 7%
- Usage Adoption: 6%

**2b. Calculate TRFcast (Training Run Forecast)**
TRFcast is a weighted composite of 9 sub-metrics from 4 independent platforms, measuring AI forecasting and financial intelligence.

**5 Pillars:**
- Forecasting Accuracy: 30% (ForecastBench baseline 20% + tournament 10%)
- Trading Performance: 25% (Rallies.ai returns 15% + Alpha Arena returns 10%)
- Prediction Calibration: 20% (ForecastBench difficulty-adjusted calibration)
- Financial Reasoning: 15% (FinanceArena QA 8% + comparative ELO 7%)
- Market Intelligence: 10% (Alpha Arena Sharpe 5% + Rallies win rate 5%)

**Formula:**
```
TRFcast = ForecastBench_Baseline (20%) + ForecastBench_Tournament (10%)
        + Rallies_Returns (15%) + AlphaArena_Returns (10%)
        + ForecastBench_Calibration (20%)
        + FinanceArena_QA (8%) + FinanceArena_Compare (7%)
        + AlphaArena_Sharpe (5%) + Rallies_WinRate (5%)
```

**Scoring:** Each model scored 0-100 per sub-metric (top performer = 100, others proportional). Weighted sum = final daily TRFcast score.

**Data Sources:**
- ForecastBench: https://forecastbench.org (baseline Brier, tournament, calibration)
- Rallies.ai: https://rallies.ai (portfolio returns, win rate)
- nof1.ai Alpha Arena: https://nof1.ai (returns, Sharpe ratio)
- FinanceArena: https://huggingface.co/spaces/TheFinAI/FinanceArena (QA accuracy, ELO)

**19 Models Tracked:** Grok 4.20, O3, Gemini 2.5 Pro, Claude 3.5 Sonnet, GPT-4.1, Claude 3.7 Sonnet, Grok 3, DeepSeek R1, DeepSeek V3, Gemini 2.0 Flash, GPT-4o, Llama 4 Maverick, Llama 3.3 70B, Mistral Large, Claude 3.5 Haiku, Gemini 2.5 Flash, GPT-4.1 mini, Grok 3 mini, GPT-4.1 nano

**Data File:** trf-data.json (auto-fetched by trfcast.html and index.html)
- Structure: formula_version, weights, dates[], models[] with daily scores and pillar breakdowns
- Updated daily with latest platform data

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
- index.html (Homepage - live TRS + TRFcast scores)
- scores.html (TRS Scoreboard)
- trfcast.html (TRFcast tracker - chart, leaderboard, 5 pillars)
- trsmethodology.html (How we calculate TRS)
- about.html (About page)
- trf-data.json (TRFcast daily scores for 19 models)
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
- LMSYS Chatbot Arena: https://huggingface.co/spaces/lmarena-ai/chatbot-arena/
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

**Scoreboard Graphic (1920x1080):**
```bash
cd ~/Desktop && python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (1920, 1080), (10, 20, 32))
draw = ImageDraw.Draw(img)

try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
    font_subtitle = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    font_rank = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    font_model = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    font_company = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    font_score = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
    font_change = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except:
    font_title = font_subtitle = font_rank = font_model = font_company = font_score = font_change = ImageFont.load_default()

CYAN = (0, 212, 255)
WHITE = (255, 255, 255)
GREEN = (0, 230, 118)
RED = (255, 82, 82)
GOLD = (255, 193, 7)
GREY = (120, 120, 120)
ROW_BG = (18, 30, 42)

TOP1_HIGHLIGHT = (70, 50, 20)
TOP2_HIGHLIGHT = (45, 50, 55)
TOP3_HIGHLIGHT = (50, 40, 30)

draw.text((80, 40), "TRAINING RUN", font=font_subtitle, fill=CYAN)
draw.text((80, 80), "THE SCOREBOARD", font=font_title, fill=WHITE)
draw.text((80, 170), "Week of DATE HERE", font=font_subtitle, fill=CYAN)

models = [
    (1, "Model Name", "Company", 95.4, +0.2),
    (2, "Model Name", "Company", 94.8, +0.2),
    (3, "Model Name", "Company", 94.3, +0.2),
    (4, "Model Name", "Company", 93.2, -0.2),
    (5, "Model Name", "Company", 93.0, +0.2),
    (6, "Model Name", "Company", 91.8, +0.6),
    (7, "Model Name", "Company", 90.9, +0.2),
]

y_start = 230
row_height = 100

for i, (rank, model, company, score, change) in enumerate(models):
    y = y_start + i * row_height

    if rank == 1:
        draw.rounded_rectangle([(60, y), (1860, y + 85)], radius=8, fill=TOP1_HIGHLIGHT)
    elif rank == 2:
        draw.rounded_rectangle([(60, y), (1860, y + 85)], radius=8, fill=TOP2_HIGHLIGHT)
    elif rank == 3:
        draw.rounded_rectangle([(60, y), (1860, y + 85)], radius=8, fill=TOP3_HIGHLIGHT)
    else:
        draw.rounded_rectangle([(60, y), (1860, y + 85)], radius=8, fill=ROW_BG)

    rank_colors = {1: GOLD, 2: (160, 160, 160), 3: (205, 127, 50)}
    box_color = rank_colors.get(rank, (50, 65, 80))
    draw.rounded_rectangle([(90, y + 18), (145, y + 68)], radius=10, fill=box_color)
    draw.text((117, y + 43), str(rank), font=font_rank, fill=(10, 20, 32) if rank <= 3 else WHITE, anchor='mm')

    draw.text((175, y + 25), model, font=font_model, fill=WHITE)
    draw.text((175, y + 58), company, font=font_company, fill=GREY)

    draw.text((1500, y + 43), f"{score}", font=font_score, fill=WHITE, anchor='mm')

    if change > 0:
        change_color = GREEN
        change_text = f"+{change}"
        arrow_x = 1650
        arrow_y = y + 43
        draw.polygon([(arrow_x, arrow_y - 12), (arrow_x - 10, arrow_y + 8), (arrow_x + 10, arrow_y + 8)], fill=GREEN)
    elif change < 0:
        change_color = RED
        change_text = str(change)
        arrow_x = 1650
        arrow_y = y + 43
        draw.polygon([(arrow_x, arrow_y + 12), (arrow_x - 10, arrow_y - 8), (arrow_x + 10, arrow_y - 8)], fill=RED)
    else:
        change_color = GREY
        change_text = "0.0"
        arrow_x = 1650
        arrow_y = y + 43
        draw.ellipse([(arrow_x - 6, arrow_y - 6), (arrow_x + 6, arrow_y + 6)], fill=GREY)

    draw.text((1780, y + 43), change_text, font=font_change, fill=change_color, anchor='mm')

img.save("scoreboard.png")
print("Saved to Desktop: scoreboard.png")
EOF
```

**How to use:**
1. Open Terminal on Mac
2. 2. Copy entire code block
   3. 3. Paste into Terminal and press Enter
      4. 4. Image saves to Desktop
        
         5. ---
        
         6. ## VERSION HISTORY

- **v2.6** (February 12, 2026) - Added TRFcast methodology (5 pillars, 9 sub-metrics, 4 platforms), updated website structure with trfcast.html and trf-data.json
- **v2.4** (February 9, 2026) - Updated TRS weights
- **v1.0** (January 30, 2026) - Initial production bible created after Week 4

---

*Last updated: February 12, 2026*
