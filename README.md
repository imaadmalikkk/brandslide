# brandslide

A multi-brand Instagram carousel production platform powered by Claude Code. Generate professional, on-brand carousel content at scale using AI-generated scenes and programmatic compositing.

**brandslide** separates what AI does well (generating cinematic scenes) from what it does poorly (rendering consistent text), producing pixel-perfect branded slides every time.

---

## What You'll Build

<p align="center">
  <img src="docs/screenshots/amar-hook.jpg" width="220" alt="AMAR hook slide"/>
  <img src="docs/screenshots/mathani-hook.jpg" width="220" alt="Mathani hook slide"/>
  <img src="docs/screenshots/gymshark-hook.jpg" width="220" alt="Gymshark hook slide"/>
</p>

Each brand gets its own visual identity, content strategy, and production pipeline — all powered by one shared engine.

---

## How It Works: The Hybrid System

### The Problem

AI image generation (Gemini, DALL-E, Midjourney) cannot consistently render the same font across multiple images. Research confirms ~94% character accuracy at best, with variable font weight and family every generation. This makes pure AI generation unusable for branded carousel content where every slide must look identical.

### The Solution

**brandslide** uses a hybrid approach:

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  NanoBanana   │     │  shared/core.py  │     │  Final Slide     │
│  (AI Scenes)  │ ──> │  (Compositor)    │ ──> │  (4K PNG)        │
│              │     │                 │     │                  │
│ Scene-only   │     │ + Gradient      │     │ Scene + Brand    │
│ No text      │     │ + Headline font │     │ elements fused   │
│ No gradient  │     │ + Accent color  │     │ perfectly        │
│ No overlay   │     │ + Subtext       │     │                  │
│              │     │ + Logo          │     │ ──> Instagram    │
└──────────────┘     └─────────────────┘     └──────────────────┘
```

**NanoBanana** generates cinematic scene images (no text, no gradient, no overlay). **shared/core.py** composites all brand elements programmatically using real font files, exact hex colors, and mathematically smooth gradients.

This guarantees:
- Identical font on every slide (real `.ttf` file, not AI approximation)
- Exact hex colors every time
- Consistent gradient curve and opacity
- Dynamic logo positioning relative to text bounds
- Pixel-perfect spacing and margins

---

## Architecture

```
brandslide/
├── CLAUDE.md                        # Platform-level instructions for Claude
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
│
├── shared/
│   ├── core.py                      # Brand-agnostic compositing engine
│   └── templates/
│       └── compose_template.py      # Template for new brand scripts
│
├── brands/
│   └── gymshark/                    # Example brand (included)
│       ├── brand.json               # Visual config (colors, fonts, layout)
│       ├── CLAUDE.md                # Content strategy & voice
│       ├── compose_slide.py         # Thin wrapper around core.py
│       ├── logo.png                 # Brand logo
│       ├── scenes/                  # Bundled test scenes
│       └── output/                  # Generated carousels go here
│
├── .claude/
│   ├── settings.example.json        # Reference permissions config
│   └── skills/
│       ├── setup/SKILL.md           # /setup — brand extraction
│       ├── ideate/SKILL.md          # /ideate — content brainstorming
│       ├── generate/SKILL.md        # /generate — carousel production
│       └── tune/SKILL.md            # /tune — visual parameter tuning
│
└── docs/
    ├── brand-config-reference.md    # Every brand.json field documented
    └── screenshots/                 # Sample output for this README
```

### Key Components

**`shared/core.py`** — The compositing engine. Handles gradient rendering, text wrapping, font scaling, headline accent coloring, logo placement, and Instagram export. All brand-specific values are passed via a config dict loaded from `brand.json`. When you improve the engine, all brands benefit.

**`brand.json`** — Declarative visual config for each brand. Defines colors, fonts, layout margins, gradient parameters, scene style prompts, and closer slide options. See [Brand Config Reference](docs/brand-config-reference.md) for every field.

**Brand `CLAUDE.md`** — Content strategy guide that Claude reads when generating carousels. Defines content pillars, voice/tone, research rigor, caption templates, and content ideas. This is what makes each brand's content unique.

**`compose_slide.py`** — A thin wrapper per brand that loads `brand.json` and calls `shared/core.py`. Every brand's compositor is nearly identical; the brand.json drives all visual differences.

### How Brands Work

Each brand is a self-contained folder in `brands/`:

```
brands/your-brand/
├── brand.json           # What it LOOKS like (colors, fonts, layout)
├── CLAUDE.md            # What it SOUNDS like (voice, pillars, strategy)
├── compose_slide.py     # How it BUILDS (imports shared engine)
├── logo.svg             # Brand mark
└── output/              # Generated carousels
    └── topic-slug/
        ├── scenes/      # AI-generated scene images
        ├── 1.png        # Composited final slides (4K)
        ├── carousel.json
        ├── caption.txt
        └── export/      # Instagram-ready JPEGs (1080px)
```

---

## Prerequisites

- **macOS** (system fonts: Impact, Helvetica Neue are required)
- **Python 3.10+**
- **Claude Code** ([install guide](https://docs.anthropic.com/en/docs/claude-code))
- **NanoBanana MCP server** (for AI scene generation)

### NanoBanana Setup

NanoBanana is an MCP server that wraps Gemini's image generation models. To install it:

1. Follow the NanoBanana setup instructions to add it as an MCP server in Claude Code
2. Verify it works: ask Claude Code to generate a test image
3. The `/generate` command uses NanoBanana automatically via the `mcp__nanobanana__generate_image` tool

---

## Tutorial: Your First Brand in 10 Minutes

### Step 1: Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/brandslide.git
cd brandslide
pip install -r requirements.txt
```

### Step 2: Configure Claude Code Permissions

Copy the example settings to enable the required permissions:

```bash
cp .claude/settings.example.json .claude/settings.local.json
```

This allows Claude Code to run Python scripts, generate images via NanoBanana, and perform web searches for content research.

### Step 3: Explore the Gymshark Example

The repo includes a fully configured **Gymshark** example brand with bundled test scenes. Open it in Claude Code:

```bash
cd brandslide
claude
```

Try compositing the example scenes manually:

```bash
python3 brands/gymshark/compose_slide.py \
  --scene brands/gymshark/scenes/1.png \
  --type hook \
  --headline "EXERCISES YOU ARE,DOING WRONG" \
  --accent WRONG \
  --output /tmp/test-hook.png
```

This produces a complete branded slide from a raw scene image — gradient, text, logo, all composited programmatically.

### Step 4: Create Your Brand with /setup

In Claude Code, run:

```
/setup my-brand
```

Provide either a **website URL** or **codebase path** (or both). The setup flow has 3 checkpoints:

1. **Visual Identity** — Claude extracts colors, fonts, and logo from your source. You confirm or adjust.
2. **Content Strategy** — Claude infers brand voice, content pillars, and target audience. You confirm or adjust.
3. **Test Slides** — Claude generates 3 test slides (hook, content, closer) using your brand config. You approve or request changes.

After setup, your brand folder is ready at `brands/my-brand/`.

### Step 5: Fine-Tune with /tune

If the test slides need visual refinement (gradient too strong, font too large, margins too tight):

```
/tune my-brand
```

This generates **3 side-by-side variations** of the same slide with different parameter values. Pick the winner, and `/tune` updates your `brand.json`. Repeat for each parameter until the look is perfect.

Tunable parameters include:
- Gradient strength and fade distance
- Headline and subtext font sizes
- Margins (bottom, top, side)
- Logo size, opacity, and padding
- Accent and subtext colors

### Step 6: Brainstorm Content with /ideate

```
/ideate my-brand
```

Claude reads your brand's content strategy, checks what carousels you've already made (to avoid duplicates), researches trending topics in your niche, and presents **5 ranked carousel ideas** with:
- Why each would perform well (saves, shares, follows)
- Which content pillar it fits
- A suggested hook headline

Pick 1-3 ideas to produce.

### Step 7: Produce a Carousel with /generate

```
/generate my-brand "exercises you're doing wrong"
```

This runs the full production pipeline:
1. **Research** — 5-7 web searches on the topic
2. **Script** — Headlines, accent words, subtext, scene descriptions for every slide
3. **Confirmation** — You review and approve the script (one checkpoint)
4. **Scene Generation** — NanoBanana generates all scenes in parallel at 4K
5. **Compositing** — Brand elements composited programmatically onto every scene
6. **Export** — 4K PNGs archived, 1080px JPEGs exported for Instagram
7. **Caption** — Instagram caption written following your brand's template

Output lands in `brands/my-brand/output/exercises-youre-doing-wrong/`.

---

## Command Reference

### `/setup [brand-name]`

**Purpose:** Create a new brand from scratch by extracting visual identity and content strategy from a website or codebase.

**Inputs:**
- Brand name (required)
- Website URL and/or codebase path (at least one)

**Flow:** 3 interactive checkpoints (visual identity, content strategy, test slides). Includes pre-generation validation that checks font paths, logo loading, color parsing, and layout sanity.

**Output:** Complete brand folder with `brand.json`, `CLAUDE.md`, `compose_slide.py`, logo, and test slides.

---

### `/ideate [brand] [pillar]`

**Purpose:** Brainstorm 5 carousel ideas ranked by engagement potential.

**Inputs:**
- Brand name (required)
- Content pillar filter (optional, e.g., "nutrition" or "training")

**Flow:** Reads brand strategy, checks existing output for dedup, runs trending topic research, presents 5 ranked ideas.

**Output:** 5 ideas with pillar, engagement rationale, slide count estimate, and hook headline suggestion.

---

### `/generate [brand] "topic"`

**Purpose:** Full autonomous carousel production from research to finished slides.

**Inputs:**
- Brand name (required)
- Topic (required)

**Flow:** 10 steps with 1 confirmation checkpoint (script approval). Research, script, scene generation, compositing, QA, caption writing.

**Output:** Complete carousel folder with scenes, composited 4K PNGs, Instagram-ready JPEGs, carousel.json, and caption.txt.

---

### `/tune [brand]`

**Purpose:** Rapidly iterate on brand.json visual parameters with side-by-side comparisons.

**Inputs:**
- Brand name (required)

**Flow:** Interactive loop. Pick a parameter category, see 3 variations of the same slide, pick the winner, repeat.

**Parameter Categories:**
- Gradient (bleed distance, max alpha, target color)
- Typography (headline size, subtext size, line spacing)
- Margins (bottom, top, side)
- Logo (size, opacity, padding)
- Colors (accent, subtext primary/secondary, divider)
- Advanced (scrim opacity, text shadow)

---

## Brand Configuration Reference

See [docs/brand-config-reference.md](docs/brand-config-reference.md) for comprehensive documentation of every `brand.json` field.

Quick overview of the sections:

| Section | What It Controls |
|---------|------------------|
| `colors` | Headline, accent, subtext, gradient target, divider colors |
| `fonts` | Headline font (path, size), subtext font (path, size, weight index) |
| `logo` | Logo file path, opacity, sizes for hook/content layouts, padding |
| `layout` | All margins, line spacing, gradient bleed/alpha, divider params |
| `scene_style` | NanoBanana prompt template, negative prompt, model tier, resolution |
| `closer` | Closer headline options with accent words, social handle |
| `scrim` | (Optional) Dark overlay for extra text legibility |
| `text_shadow` | (Optional) Blurred shadow behind text |
| `website` | (Optional) Brand URL displayed on slides |

---

## The Core Engine

`shared/core.py` provides these functions:

| Function | Purpose |
|----------|---------|
| `load_brand_config(path)` | Parse brand.json, convert hex to RGB, resolve relative paths |
| `load_logo(svg_path, size, opacity)` | Load SVG or PNG logo at given size |
| `create_gradient(w, h, ...)` | Render smooth eased gradient (fade zone + solid zone) |
| `wrap_text(text, font, max_width)` | Word-wrap text to fit within pixel width |
| `get_font_for_line(line, ...)` | Auto-scale font down for lines that exceed max width |
| `render_headline_block(draw, ...)` | Render ALL-CAPS headline with accent word coloring |
| `render_text_shadow(img, ...)` | (Optional) Render blurred shadow layer under text |
| `compose_slide(scene, config, ...)` | Main compositor: gradient + text + logo onto scene |
| `process_config(json_path, brand)` | Batch process a carousel.json config file |
| `export_for_instagram(paths, dir)` | Resize 4K slides to 1080px Instagram-ready JPEGs |

**To modify the engine:** Edit `shared/core.py`. All brands inherit changes automatically since each brand's `compose_slide.py` is just a thin wrapper that imports from core.

---

## FAQ

**Q: Do I need NanoBanana to use this?**
A: NanoBanana is used for AI scene generation. You can also use manually sourced images (stock photos, your own photography) as scenes — just place them in the scenes/ folder and the compositor works the same.

**Q: Can I use fonts other than Impact and Helvetica Neue?**
A: Yes. Update the font paths in your brand.json. Any `.ttf` or `.ttc` font file on your system works. Use `fc-list` to see available fonts.

**Q: Why are slides 4K if Instagram compresses them?**
A: Instagram compresses heavily. Starting at 4K (3712x4608) ensures text remains sharp after compression. The `export_for_instagram()` function produces 1080x1350 JPEGs optimized for upload.

**Q: Can two brands share the same visual style with different content?**
A: Yes. Copy a brand.json and modify only the CLAUDE.md (content strategy). The visual identity and content voice are fully decoupled.

**Q: What if /setup extracts the wrong colors from my website?**
A: The setup flow has a confirmation checkpoint. Adjust any values before proceeding. After setup, use `/tune` to fine-tune specific parameters with visual comparison.

**Q: Can I use this without Claude Code?**
A: The compositor (`compose_slide.py`) works standalone — you can run it directly with Python. The slash commands (`/setup`, `/ideate`, `/generate`, `/tune`) require Claude Code since they orchestrate research, AI generation, and compositing together.
