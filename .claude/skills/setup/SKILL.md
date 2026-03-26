---
name: setup
description: Extract brand identity from a codebase or website and generate a complete brand folder (brand.json, compose_slide.py, CLAUDE.md, test slides) with pre-generation validation
---

# /setup — Brand Setup (Full Onboarding)

You are setting up a new brand in brandslide. This handles EVERYTHING: installing dependencies, extracting brand identity, and generating test slides. 3 checkpoints.

## Phase 0: Prerequisites (automatic, no user input needed)

Run these silently before anything else. Fix any failures before proceeding.

### 1. Python dependencies
```bash
pip install -r requirements.txt
```
If pip fails, try `pip3`. If both fail, tell the user to install Python 3.10+.

### 2. Font availability
Check that the default fonts exist:
```bash
python3 -c "from PIL import ImageFont; ImageFont.truetype('/System/Library/Fonts/Supplemental/Impact.ttf', 40); print('Impact: OK')"
python3 -c "from PIL import ImageFont; ImageFont.truetype('/System/Library/Fonts/HelveticaNeue.ttc', 40); print('Helvetica Neue: OK')"
```
If a font is missing, warn the user (macOS required).

### 3. Claude Code permissions
Copy settings if they don't exist:
```bash
if [ ! -f .claude/settings.local.json ]; then cp .claude/settings.example.json .claude/settings.local.json; fi
```

### 4. NanoBanana MCP installation

NanoBanana is the AI image generation server used for scene creation. It must be configured as an MCP server in the user's `~/.claude.json`.

**Step 1: Check if already installed**
```bash
python3 -c "import json; d=json.load(open('$HOME/.claude.json')); print('installed' if 'nanobanana' in d.get('mcpServers',{}) else 'missing')"
```

**Step 2: If missing, install it**

1. Check that `uvx` is available:
   ```bash
   which uvx
   ```
   If missing, tell the user: "NanoBanana requires `uv` (Python package runner). Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` then restart your terminal."

2. Ask the user for their **Gemini API key**. Tell them:
   > NanoBanana uses Google's Gemini image generation. You need a Gemini API key.
   > Get one free at: https://aistudio.google.com/apikey

   Wait for the user to provide the key before proceeding.

3. Add the NanoBanana MCP server to `~/.claude.json`:
   ```python
   import json, os

   config_path = os.path.expanduser("~/.claude.json")
   with open(config_path, "r") as f:
       config = json.load(f)

   if "mcpServers" not in config:
       config["mcpServers"] = {}

   config["mcpServers"]["nanobanana"] = {
       "type": "stdio",
       "command": "uvx",
       "args": ["nanobanana-mcp-server@latest"],
       "env": {
           "GEMINI_API_KEY": "<USER_PROVIDED_KEY>"
       }
   }

   with open(config_path, "w") as f:
       json.dump(config, f, indent=2)
   ```
   Replace `<USER_PROVIDED_KEY>` with the actual key the user provided.

4. Tell the user: "NanoBanana MCP has been installed. **You need to restart Claude Code** (`/exit` then relaunch) for the MCP server to become available."

5. After restart confirmation, verify it works by generating a tiny test image with `mcp__nanobanana__generate_image`. If it fails, troubleshoot (bad API key, uvx not found, etc).

**Step 3: If already installed, verify it works**
Try generating a tiny test image to confirm NanoBanana is responsive. If it fails, warn the user but continue (they can add scenes manually later).

Once all checks pass, print a brief status summary and move to Phase 1.

## Inputs

The user provides one or more of:
- **Codebase path** (local directory with CSS, Tailwind config, theme files, logos)
- **Website URL** (to crawl for visual identity and copy)
- **Brand name** (required)

If neither codebase nor URL is provided, ask the user for at least one.

## Phase 1: Visual Extraction

### If codebase path provided:
1. Search for CSS variables, Tailwind config (`tailwind.config.*`), theme files (`theme.*`, `colors.*`)
2. Extract: primary colors, secondary colors, background colors, accent colors
3. Search for SVG/PNG logos (`*.svg` or `*.png` with "logo" in name or path)
4. Search for font configurations (CSS `font-family`, Google Fonts imports, local font files)

### If website URL provided:
1. Navigate to the website using browser tools
2. Extract the color palette from computed styles (background, text, accent, CTA buttons)
3. Identify fonts from computed styles
4. Screenshot the homepage for visual reference
5. Check for a logo in the header/navbar

### Present to user:
```
## Extracted Visual Identity

**Colors:**
- Background: #XXXXXX (from [source])
- Headline: #XXXXXX
- Accent: #XXXXXX (from CTA / brand accent)
- Subtext primary: #XXXXXX
- Subtext secondary: #XXXXXX
- Gradient target: #XXXXXX (darkened version of background)

**Fonts:**
- Headline: [Font family] (bold/condensed if available)
- Subtext: [Font family] (regular/medium weight)

**Logo:** [path or "not found — please provide"]

**Divider colors:**
- Default: #FFFFFF
- Alt: [accent color]
```

### **CHECKPOINT 1: User confirms or adjusts visual identity**

Wait for the user to approve or modify the extracted values before proceeding.

## Phase 2: Voice Extraction

### If website URL provided:
1. Read the About page, homepage hero copy, tagline
2. Read any blog posts or content for tone analysis
3. Check social media bios linked from the site

### Infer and present:
```
## Proposed Content Strategy

**Brand position:** [one sentence]
**Tone of voice:** [scholarly / casual / inspirational / professional / etc.]
**Target audience:** [who]

**Content pillars:**
1. [Pillar] — [topics] → [engagement driver]
2. [Pillar] — [topics] → [engagement driver]
3. [Pillar] — [topics] → [engagement driver]
4. [Pillar] — [topics] → [engagement driver]
5. [Pillar] — [topics] → [engagement driver]

**Closer messages (rotate):**
1. [Brand statement + accent word]
2. [Brand statement + accent word]
3. [Brand statement + accent word]

**Handle:** @[social handle]
```

### **CHECKPOINT 2: User confirms or adjusts voice/strategy**

Wait for the user to approve or modify before generating files.

## Phase 3: Generation (with validation)

Using the confirmed visual identity and content strategy:

### Pre-generation Validation

Before generating any files, validate the configuration:

1. **Font check:** Verify font files exist at the specified paths
   ```python
   import os
   for font_role in ['headline', 'subtext']:
       path = config['fonts'][font_role]['path']
       if not os.path.exists(path):
           print(f"FAIL: {font_role} font not found at {path}")
   ```

2. **Logo check:** Verify logo file loads correctly
   ```python
   from PIL import Image
   try:
       if logo_path.endswith('.svg'):
           import cairosvg
           cairosvg.svg2png(url=logo_path, output_width=100)
       else:
           Image.open(logo_path)
       print("PASS: Logo loads correctly")
   except Exception as e:
       print(f"FAIL: Logo error: {e}")
   ```

3. **Color check:** Verify all required color fields are valid hex
   ```python
   required_colors = ['headline', 'accent', 'subtext_primary', 'subtext_secondary', 'gradient_target']
   for color in required_colors:
       if color not in config['colors']:
           print(f"FAIL: Missing required color: {color}")
   ```

4. **Layout check:** Verify layout values are reasonable
   - All margins > 0
   - gradient_bleed between 100 and 800
   - gradient_max_alpha between 100 and 255
   - font sizes between 15 and 200

If any check fails, report the issue and fix it before proceeding to file generation.

### File Generation

1. **Create brand directory:** `brands/<brand-slug>/`

2. **Generate `brand.json`** from confirmed visual values. Use an existing brand.json as structural reference:
   ```
   brands/gymshark/brand.json  (example with all fields documented)
   ```

3. **Generate brand `CLAUDE.md`** with the confirmed content strategy. Include:
   - Brand context (what it is, what it offers, who it serves)
   - Content strategy (goal, content model, pillars table)
   - Voice and tone guidelines
   - Carousel structure (narrative arc)
   - **Hook Framework** — MUST include:
     - 7-point scoring checklist (specificity, curiosity gap, personal stakes, emotional trigger, authority/science signal, scannability, accent clarity)
     - 8 hook archetypes adapted to the brand's niche and emotional palette (see brands/gymshark/CLAUDE.md for an example)
     - Accent word rules specific to the brand's tone (threat verbs for authority brands, discovery verbs for empowerment brands)
     - Hook red lines (what to never do for this brand)
   - Scene direction and scene ideas bank
   - Research and accuracy rules (brand-specific rigor)
   - Closer slide options
   - Caption template adapted for the brand
   - Content ideas bank (5-10 starter ideas)
   - Non-negotiable rules specific to this brand

4. **Generate `compose_slide.py`** by copying the template:
   ```bash
   cp shared/templates/compose_template.py brands/<brand-slug>/compose_slide.py
   ```
   Replace `{{BRAND_NAME}}` with the actual brand name in the docstring.

5. **Copy logo** to brand folder as `logo.svg` or `logo.png`.

6. **Create `output/` directory** for carousel output.

7. **Generate 3 test slides** to verify the brand config works:
   - Hook slide (test headline + accent word + divider)
   - Content slide (test headline + subtext in both colors)
   - Closer slide (test brand message + handle)

   Use a generic scene (generate via NanoBanana with the brand's scene_style) or use an existing scene for speed.

### **CHECKPOINT 3: User approves test slides or requests adjustments**

If adjustments needed, modify brand.json values and regenerate test slides. Repeat until approved.

Suggest: "If you want to fine-tune specific visual parameters, run `/tune <brand>` for side-by-side comparisons."

## Output

When complete, the brand folder should contain:
```
brands/<brand-slug>/
├── brand.json
├── CLAUDE.md
├── compose_slide.py
├── logo.svg (or logo.png)
└── output/
```

Announce: "Brand **[name]** is set up. Use `/ideate [brand]` to brainstorm content, `/generate [brand] [topic]` to produce a carousel, or `/tune [brand]` to fine-tune visual parameters."
