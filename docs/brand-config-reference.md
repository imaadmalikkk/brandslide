# Brand Configuration Reference

Complete documentation for every field in `brand.json`. Each brand in `brands/<name>/` has its own `brand.json` that controls all visual parameters.

---

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name of the brand (e.g., "Gymshark") |
| `website` | string | No | Brand website URL. Can be rendered on slides when `show_website: true` is set in slide config. |
| `scrim` | object/null | No | Dark overlay between scene and text for extra legibility. Set to `null` to disable. |
| `text_shadow` | object/null | No | Blurred shadow behind text. Set to `null` to disable. |

---

## `colors`

All values are hex color strings (e.g., `"#FFFFFF"`).

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `background` | Yes | Brand's primary background color. Used for reference; not directly rendered. | `"#1B1B1B"` |
| `headline` | Yes | Headline text color. Usually white for dark backgrounds. | `"#FFFFFF"` |
| `accent` | Yes | Accent color for highlighted words in headlines and primary subtext. | `"#00A8E8"` |
| `subtext_primary` | Yes | Color for the first subtext line (key insight). Usually matches accent. | `"#00A8E8"` |
| `subtext_secondary` | Yes | Color for the second subtext line (elaboration). Usually a muted grey/white. | `"#BBBCBC"` |
| `gradient_target` | Yes | The color the gradient fades TO at the image edge. Should be near-black matching the brand's dark tone. | `"#000000"` |
| `divider_default` | No | Default color for the hook slide divider line. Falls back to headline color. | `"#FFFFFF"` |
| `divider_alt` | No | Alternate divider color (selectable via `line_color: "alt"` in config). | `"#00A8E8"` |
| `website` | No | Color for the website URL text when displayed on slides. | `"#00A8E8"` |

### Color Tips
- The **accent** color should contrast strongly against both the gradient and the scene. Warm amber works against cool blue scenes; cool blue works against warm/dark scenes.
- The **gradient_target** should be the darkest tone in your brand palette. Pure black (`#000000`) works universally; tinted blacks (like `#080C16` for navy) add subtle brand character.
- Keep **subtext_secondary** lighter than `subtext_primary` to create clear hierarchy.

---

## `fonts`

Font configuration for headlines, subtext, and handle text.

### `fonts.headline`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | Yes | — | Absolute path to the font file (`.ttf` or `.ttc`). |
| `size` | int | Yes | — | Font size in pixels at 1080px base width. Scales proportionally for 4K. |
| `index` | int | No | `0` | Font index within a `.ttc` collection file. Use `0` for `.ttf` files. |

**Recommended headline fonts (macOS):**
- `/System/Library/Fonts/Supplemental/Impact.ttf` — Bold condensed ALL-CAPS. Classic carousel headline font.
- `/System/Library/Fonts/Supplemental/Futura.ttc` — Geometric sans-serif. Index 4 = Condensed ExtraBold.

### `fonts.subtext`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | Yes | — | Absolute path to the font file. |
| `size` | int | Yes | — | Font size in pixels at 1080px base width. |
| `index` | int | No | `0` | Font index within a `.ttc` collection file. |

**Recommended subtext fonts (macOS):**
- `/System/Library/Fonts/HelveticaNeue.ttc` — Clean sans-serif. Index 1 = Regular, Index 10 = Medium.
- `/System/Library/Fonts/Supplemental/Avenir Next.ttc` — Modern geometric. Index 3 = Medium.

### `fonts.handle`

Optional. Configuration for the `@handle` text on closer slides.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | No | Subtext font path | Falls back to subtext font if not specified. |
| `size` | int | No | `26` | Font size at 1080px base width. |
| `index` | int | No | `0` | Font index. |

---

## `logo`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `svg_path` | string | Yes | — | Path to the logo file (SVG or PNG). Relative paths resolve from the brand folder. |
| `opacity` | float | No | `0.90` | Logo opacity (0.0 to 1.0). Slight transparency helps logos blend into scenes. |
| `hook_size` | int | Yes | — | Logo size in pixels at 1080px base width for hook slides (centered with divider). |
| `content_size` | int | Yes | — | Logo size for content/closer slides (bottom-right). Set to `0` to hide the logo on content slides. |
| `padding` | int | No | `18` | Padding from image edges in pixels at 1080px base width. |

### Logo Tips
- **SVG** logos scale perfectly at any size. Prefer SVG over PNG when available.
- **PNG** logos should be high-resolution with transparency.
- Set `content_size: 0` if you want logo only on hook slides (some brands prefer minimal branding on content slides).

---

## `layout`

All values are in pixels at 1080px base width. They scale proportionally for 4K output (multiply by ~3.44x).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `base_width` | int | `1080` | Reference width for all pixel values. Don't change unless you know what you're doing. |
| `text_bottom_margin` | int | `100` | Space between bottom text and image edge. |
| `text_top_margin` | int | `50` | Space between top text and image edge (content slides with top-positioned headlines). |
| `text_side_margin` | int | `60` | Horizontal padding from left/right edges. Text area = image width - 2x this value. |
| `headline_line_spacing` | int | `10` | Vertical space between headline lines. |
| `subtext_top_gap` | int | `30` | Space between headline block and subtext block. |
| `subtext_line_spacing` | int | `10` | Vertical space between subtext lines. |
| `divider_gap_above_text` | int | `50` | Space between the divider line and the headline on hook slides. |
| `gradient_bleed` | int | `350`-`450` | How far the gradient fade extends beyond the text edge into the scene. Larger = more gradual fade. |
| `gradient_max_alpha` | int | `200`-`255` | Maximum opacity of the gradient (0-255). 200 = scene bleeds through slightly. 255 = fully opaque behind text. |
| `divider_thickness` | int | `3` | Thickness of the hook slide divider line. |
| `divider_gap` | int | `20` | Gap between the divider line and the centered logo on hook slides. |
| `handle_gap` | int | `40` | Space between the headline and @handle text on closer slides. |

### Layout Diagram

```
Hook Slide:                    Content Slide:
┌──────────────────────┐       ┌──────────────────────┐
│                      │       │                      │
│      SCENE           │       │      SCENE           │
│                      │       │                      │
│                      │       │                      │
│  ── LOGO ──  divider │       │                      │
│  ↕ divider_gap       │       │▓▓▓ gradient_bleed ▓▓▓│
│  ┌────────────────┐  │       │                      │
│  │   HEADLINE     │  │       │  ┌────────────────┐  │
│  │   TEXT BLOCK   │  │       │  │   HEADLINE     │  │
│  └────────────────┘  │       │  │   TEXT BLOCK   │  │
│  ↕ text_bottom_margin│       │  │   ↕ subtext_gap│  │
└──────────────────────┘       │  │   SUBTEXT      │  │
                               │  └────────────────┘  │
← text_side_margin →          │  ↕ text_bottom_margin│
                               └──────────────────────┘
```

---

## `scene_style`

Configuration for NanoBanana AI scene generation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_prompt` | string | Yes | Foundation prompt prepended to every scene description. Defines the visual style. |
| `negative_prompt` | string | Yes | Things to avoid in generated scenes. Always include "text, gradient, overlay, watermark, logo." |
| `model_tier` | string | No | NanoBanana model tier: `"pro"` (best quality, 4K), `"nb2"` (fast, 4K), `"flash"` (fastest, 1K). Default: `"pro"`. |
| `resolution` | string | No | Output resolution: `"4k"`, `"2k"`, `"1k"`, `"high"`. Default: `"4k"`. |
| `aspect_ratio` | string | No | Image aspect ratio. Default: `"4:5"` (Instagram portrait). |

### Scene Style Tips
- Always include "slightly stylized hyperrealistic" in your base prompt — it produces the engaging not-quite-real look that performs well on Instagram.
- Include "No text. No gradient. No overlay. Pure scene only." in your scene descriptions (not in base_prompt — it's added by /generate automatically).
- Tune color grading in the base prompt: "cool blue-teal undertones" for scholarly brands, "warm undertones" for lifestyle brands, "emerald tones" for nature/growth brands.

---

## `closer`

Configuration for the final slide (brand CTA).

### `closer.options`

Array of closer slide options. /generate rotates through these.

```json
{
    "headline": ["WE DO", "GYM"],
    "accent": "GYM"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `headline` | string[] | Headline text split into lines (each string = one line). |
| `accent` | string | The word to highlight in the accent color. |

### `closer.handle`

| Field | Type | Description |
|-------|------|-------------|
| `handle` | string | Social media handle displayed below the headline on closer slides (e.g., `"@gymshark"`). |

---

## Optional: `scrim`

A dark semi-transparent overlay applied between the scene and all text/gradients. Improves text legibility on bright or busy scenes.

```json
"scrim": {
    "opacity": 30
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `opacity` | int | — | Scrim darkness (0-255). 30 is subtle; 60 is noticeable. |

Set to `null` to disable (default).

---

## Optional: `text_shadow`

A blurred shadow rendered behind all text for extra legibility.

```json
"text_shadow": {
    "blur": 20,
    "opacity": 180
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `blur` | int | `20` | Gaussian blur radius in pixels at 1080px base width. |
| `opacity` | int | `180` | Shadow opacity (0-255). |

Set to `null` to disable (default). Note: text shadows can look tacky on clean designs. Use sparingly.

---

## Complete Example

See `brands/gymshark/brand.json` for a fully populated example with all fields.
