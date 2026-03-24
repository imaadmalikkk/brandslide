# ContentGenerator — Multi-Brand Content Production Platform

A platform for producing Instagram carousel content across multiple brands. Each brand has its own visual identity, content strategy, and compositor, all powered by a shared core engine.

---

## Architecture

```
ContentGenerator/
├── shared/core.py           # Brand-agnostic compositing engine
├── shared/templates/        # Templates for /setup to generate new brand files
├── brands/<brand>/
│   ├── brand.json           # Visual config (colors, fonts, layout, scene style)
│   ├── CLAUDE.md            # Content strategy, pillars, voice, editorial rules
│   ├── compose_slide.py     # Thin wrapper that imports shared/core.py
│   ├── logo.svg             # Brand logo
│   └── output/              # Generated carousels
└── skills/                  # Slash command skills
    ├── setup.md             # /setup — brand identity extraction
    ├── ideate.md            # /ideate — content brainstorming
    └── generate.md          # /generate — carousel production
```

### How It Works

1. **NanoBanana** generates scene-only images (no text, no gradient, no overlay)
2. **shared/core.py** composites brand elements programmatically (gradient, text, logo)
3. Each brand's **brand.json** defines all visual parameters
4. Each brand's **CLAUDE.md** defines content strategy and editorial voice

This hybrid approach guarantees pixel-perfect font consistency across all slides. AI generates visuals; code handles typography.

---

## Working with Brands

### Switching Brands

Every command takes a brand name. The brand name must match a folder in `brands/`:

```
/ideate amar              → brainstorm for AMAR
/generate amar "topic"    → produce carousel for AMAR
/generate mathani "topic" → produce carousel for Mathani
```

### Brand Config (brand.json)

Visual config loaded by the compositor. Key sections:

| Section | What It Controls |
|---------|------------------|
| `colors` | Headline, accent, subtext primary/secondary, gradient target, divider |
| `fonts` | Headline font (path, size), subtext font (path, size, index), handle font |
| `logo` | SVG path, opacity, hook/content sizes, padding |
| `layout` | Margins, line spacing, gradient bleed/alpha, divider thickness/gap |
| `scene_style` | NanoBanana prompt base, negative prompt, model tier, resolution, aspect ratio |
| `closer` | Closer headline options with accent words, social handle |

### Brand CLAUDE.md

Content strategy read by Claude when generating carousels. Contains:
- What the brand is and who it serves
- Content pillars and conversion paths
- Carousel narrative structure
- Research and authenticity rules
- Caption template
- Content ideas bank

---

## Skills

### /setup [brand-name]
Extract brand identity from a codebase or website. Interactive 3-checkpoint flow:
1. Visual extraction (colors, fonts, logo)
2. Voice extraction (pillars, tone, audience)
3. Generate brand folder with test slides

### /ideate [brand]
Brainstorm 5 carousel ideas ranked by engagement potential. Checks existing output for dedup, researches trending topics.

### /generate [brand] [topic]
Full production pipeline: research, script, NanoBanana scenes, compositing, QA. One confirmation checkpoint (slide script approval), then autonomous through compositing.

---

## Shared Core Engine

`shared/core.py` provides:

| Function | Purpose |
|----------|---------|
| `load_brand_config(json_path)` | Parse brand.json, convert hex to RGB, resolve paths |
| `load_logo(svg_path, size, opacity)` | SVG to RGBA PNG |
| `create_gradient(w, h, text_edge, fade_length, color, ...)` | Smooth eased gradient overlay |
| `wrap_text(text, font, max_width)` | Word wrapping |
| `get_font_for_line(line, base_font, base_size, max_width, ...)` | Auto-scale font for long lines |
| `render_headline_block(draw, lines, accent_word, ...)` | Headline with accent coloring |
| `compose_slide(scene_path, slide_config, output_path, brand, ...)` | Main compositor |
| `process_config(config_path, brand)` | Batch process carousel.json |

When modifying the engine, edit `shared/core.py`. All brands inherit changes automatically.

---

## Production Workflow

### Scene Generation (NanoBanana)

Scene prompts contain NO text, NO gradient, NO overlay. Just the visual scene.

```
{brand.scene_style.base_prompt}
[Scene-specific description].
The scene fills the ENTIRE image from edge to edge. No empty space. Full bleed composition.
No text. No gradient. No overlay. Pure scene only.
```

NanoBanana settings come from `brand.scene_style` in brand.json:
- `model_tier`: always "pro" for production
- `resolution`: always "4k" for production
- `aspect_ratio`: "4:5" (Instagram portrait)
- `negative_prompt`: blocks text, gradients, faces, etc.

### Compositing

```bash
# Full carousel via JSON config
python3 brands/<brand>/compose_slide.py --config carousel.json

# Single slide
python3 brands/<brand>/compose_slide.py \
  --scene scene.png --type hook \
  --headline "TEXT HERE,LINE TWO" --accent WORD \
  --output 1.png
```

### Output Organization

```
brands/<brand>/output/<carousel-slug>/
├── scenes/          (NanoBanana scene-only images)
├── 1.png - N.png    (composited final slides)
├── carousel.json    (compositor config)
└── caption.txt      (Instagram caption)
```

---

## Quality Standards

These apply to ALL brands:

1. **Gradient must be seamless.** Blends naturally into the scene. No hard edges, no banding, no colored blocks.
2. **Text must be legible.** Real fonts from brand config, correctly spelled, readable against background.
3. **Full bleed scenes.** No empty space. Scene fills entire canvas edge to edge.
4. **4K resolution for production.** Instagram compresses heavily; 4K ensures text survives.
5. **No AI-generated text in scenes.** All text is composited programmatically.
6. **NO TEXT SHADOWS.** No drop shadows, outlines, or glow. Clean flat text only.
7. **Scene variety within a carousel.** Each slide should be visually distinct.

---

## Adding a New Brand

Use `/setup <brand-name>` for the guided flow, or manually:

1. Create `brands/<brand-slug>/`
2. Create `brand.json` (use `brands/amar/brand.json` as reference)
3. Create `CLAUDE.md` with content strategy
4. Copy `shared/templates/compose_template.py` to `compose_slide.py`
5. Add logo as `logo.svg`
6. Create `output/` directory
7. Test with a hook, content, and closer slide
