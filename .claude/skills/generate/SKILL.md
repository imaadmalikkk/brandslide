---
name: generate
description: Full carousel production pipeline — research, script, scene generation, compositing, and QA for any brand
---

# /generate — Carousel Production Pipeline

You are producing a complete Instagram carousel for a specific brand. This is a mostly autonomous pipeline with one confirmation checkpoint.

## Inputs

- **Brand name** (required) — must match a folder in `brands/`
- **Topic** (required) — the carousel subject
- **Template** (optional) — `--template <name>` to use a specific visual template

Parse from the user's message: `/generate gymshark "exercises you're doing wrong"` or `/generate <brand> "topic" --template bold-centered`

## Step 1: Load Brand Config + Template

Load brand config files:
```
brands/<brand>/brand.json    → visual config, scene style, closer options
brands/<brand>/CLAUDE.md     → content strategy, pillars, voice, research rules
```

Use `load_brand_config()` from shared/core.py to parse brand.json.

**Template selection:**
- If `--template <name>` specified, load it with `load_template(name)`
- If no template specified, show available templates with `list_templates()` and ask the user which to use. Default to "cinematic-story" if they want the standard look.
- If the template has `scene_style_overrides`, apply them automatically to NanoBanana prompts in Step 5.
- If the template has `scene_required: false` (like text-forward), skip scene generation entirely in Step 5.

Determine the output directory:
```
brands/<brand>/output/<topic-slug>/
```

Create both `scenes/` and the output directory.

## Step 2: Research

Run 5-7 web searches on the topic:
1. Core topic research (what are the key points?)
2. Common misconceptions about the topic
3. What competitors/similar accounts have posted (differentiate)
4. Any recent news or trending angles
5-7. **Brand-specific research** — read the brand's CLAUDE.md for topic-specific research instructions and follow them exactly.

### Brand-Defined Research Rigor

Different brands have different accuracy requirements. Read the "Research & Accuracy" section of the brand's CLAUDE.md and follow whatever rules it defines. Examples:

- **Islamic education brands:** Verify hadith authenticity, cite Quran with surah:ayah references, attribute scholarly opinions
- **Fitness brands:** Cite scientific studies for health claims, don't promote dangerous practices
- **DTC/E-commerce brands:** Verify product claims, check sourcing accuracy
- **Tech/SaaS brands:** Verify technical accuracy, cite documentation

If the brand's CLAUDE.md doesn't define specific research rules, apply general best practices: verify claims, cite sources, acknowledge uncertainty.

## Step 3: Write Slide Script

**IMPORTANT — Hook Slide:** Before writing the hook, read the brand's CLAUDE.md "Hook Framework" section. Score your hook against the 7-point checklist (must score 5+/7). Use the brand's hook archetypes and accent word rules. Different brands have different emotional palettes — follow theirs, not a generic template.

Based on research, write the complete slide script:

```
Slide 1 (Hook): [HEADLINE] — accent: [WORD] — archetype: [which of the 8 types] — score: [X/7]
Slide 2: [HEADLINE] — accent: [WORD] / primary subtext: [text] / secondary subtext: [text]
Slide 3: [HEADLINE] — accent: [WORD] / primary subtext: [text] / secondary subtext: [text]
...
Slide N (Closer): [HEADLINE from brand closer options] — accent: [WORD]
```

Rules:
- Headlines: 5-8 words max, ALL CAPS
- 1-2 accent words per headline (the keyword that carries the most weight)
- Primary subtext: the key insight, fact, or claim (max 15 words)
- Secondary subtext: elaboration, source, or context (max 15 words)
- Slide count: 5-10, determined by how many strong points the research yields
- Hook: provocative or curiosity-driven, no subtext
- Closer: chosen from brand's closer options in brand.json

### Scene Descriptions

For each slide, write a detailed scene description for NanoBanana. Be hyper-specific:
- Specific objects, materials, textures
- Lighting direction and quality
- Atmosphere and mood
- What fills the frame

Use the brand's `scene_style.base_prompt` as the foundation and append scene-specific details. Refer to the "Scene Ideas Bank" in the brand's CLAUDE.md for inspiration.

## Step 4: Confirm Scene Style

Present the slide script and ask the user to confirm or adjust. Show:
- All headlines with accent words highlighted
- All subtext pairs
- Scene descriptions (summarized)
- The closer option selected

**This is the only mandatory checkpoint.** If the user approves, proceed autonomously through the rest.

## Step 5: Generate Scenes

Generate all scene images in parallel (3-4 at a time) via NanoBanano.

For each scene, the prompt structure is:
```
{brand.scene_style.base_prompt}
[Scene-specific description from Step 3].
The scene fills the ENTIRE image from edge to edge. No empty space. Full bleed composition.
No text. No gradient. No overlay. Pure scene only.
```

NanoBanana settings from brand.json:
- `model_tier`: brand.scene_style.model_tier
- `resolution`: brand.scene_style.resolution
- `aspect_ratio`: brand.scene_style.aspect_ratio
- `negative_prompt`: brand.scene_style.negative_prompt
- `output_path`: `brands/<brand>/output/<topic-slug>/scenes/N.png`

After generating the first good scene, use it as `input_image_path_1` for subsequent scenes to maintain visual consistency.

## Step 6: Write carousel.json

Create the carousel config for the compositor:

```json
{
    "output_dir": "brands/<brand>/output/<topic-slug>/",
    "line_color": "default",
    "template": "<template-name>",
    "slides": [
        {
            "scene": "scenes/1.png",
            "type": "hook",
            "headline": ["LINE 1", "LINE 2"],
            "accent_word": "WORD"
        }
    ]
}
```

The `"template"` field is read by `process_config()` which loads and passes the template to each `compose_slide()` call.

Save to `brands/<brand>/output/<topic-slug>/carousel.json`.

## Step 7: Composite

Run the brand's compositor:
```bash
python3 brands/<brand>/compose_slide.py --config brands/<brand>/output/<topic-slug>/carousel.json
```

## Step 8: Cleanup

Delete NanoBanana thumbnail files:
```bash
rm brands/<brand>/output/<topic-slug>/scenes/*_thumb.jpeg 2>/dev/null
```

## Step 9: QA & Present

### Scene QA (for each slide)
- Full bleed: scene fills entire canvas, no empty space
- Correct mood/color grading: matches brand's scene style
- No text/gradient in scene: clean, compositor handles overlays
- No full faces (unless brand allows): partial faces OK

### Composited QA (for each slide)
- Font consistent: real fonts from brand config, not AI-generated
- Accent word colored correctly
- Subtext colors correct (primary + secondary)
- Gradient smooth: blends naturally, no hard edges
- Logo placed correctly (hook: centered divider, content: bottom-right)
- Text legible against background

Show the user: hook slide, 2 content slides, and the closer slide (4 screenshots). If all look good, announce completion.

## Step 10: Caption

Write the Instagram caption following the brand's caption template from CLAUDE.md. Save to:
```
brands/<brand>/output/<topic-slug>/caption.txt
```

## Output

When complete:
```
brands/<brand>/output/<topic-slug>/
├── scenes/          (NanoBanana scene-only images)
│   ├── 1.png
│   └── ...
├── 1.png            (composited final slides)
├── ...
├── N.png
├── carousel.json
├── caption.txt
└── export/          (Instagram-ready 1080px JPEGs)
    ├── 1.jpg
    └── ...
```

Announce: "Carousel complete: **[topic]** for **[brand]**. [N] slides ready for review at `brands/<brand>/output/<topic-slug>/`."
