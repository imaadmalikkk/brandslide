#!/usr/bin/env python3
"""
ContentGenerator Core Engine — Brand-agnostic slide compositor.

Extracted from the AMAR compose_slide.py. All brand-specific values
(colors, fonts, layout, logo) are passed via a brand_config dict
loaded from each brand's brand.json.

Usage:
    from shared.core import load_brand_config, compose_slide, process_config

    brand = load_brand_config("brands/amar/brand.json")
    compose_slide("scene.png", slide_config, "output.png", brand)
"""

import sys
import os
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cairosvg
import io


# ---------------------------------------------------------------------------
# Brand config loading
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_str: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def load_brand_config(json_path: str) -> dict:
    """Load brand.json and return a processed config dict with RGB tuples."""
    json_path = Path(json_path).resolve()
    brand_dir = json_path.parent

    with open(json_path) as f:
        raw = json.load(f)

    # Convert hex colors to RGB tuples
    colors = {}
    for key, val in raw.get("colors", {}).items():
        colors[key] = hex_to_rgb(val) if isinstance(val, str) else tuple(val)

    # Resolve font paths
    fonts = {}
    for role, cfg in raw.get("fonts", {}).items():
        fonts[role] = dict(cfg)
        if "path" in cfg and not os.path.isabs(cfg["path"]):
            fonts[role]["path"] = str(brand_dir / cfg["path"])

    # Handle font inherits subtext path if not specified
    if "handle" in fonts and "path" not in fonts["handle"]:
        fonts["handle"]["path"] = fonts.get("subtext", {}).get("path", "")
    if "handle" in fonts and "index" not in fonts["handle"]:
        fonts["handle"]["index"] = 0

    # Resolve logo SVG path
    logo = dict(raw.get("logo", {}))
    svg_path = logo.get("svg_path", "logo.svg")
    if not os.path.isabs(svg_path):
        logo["svg_path"] = str(brand_dir / svg_path)

    return {
        "name": raw.get("name", ""),
        "colors": colors,
        "fonts": fonts,
        "logo": logo,
        "layout": raw.get("layout", {}),
        "scene_style": raw.get("scene_style", {}),
        "closer": raw.get("closer", {}),
        "text_shadow": raw.get("text_shadow", None),
        "website": raw.get("website", None),
        "_brand_dir": str(brand_dir),
    }


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def load_logo(svg_path: str, size: int, opacity: float = 0.90) -> Image.Image:
    """Load logo (SVG or PNG) and convert to RGBA at given size."""
    ext = Path(svg_path).suffix.lower()
    if ext == ".svg":
        png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
        logo = Image.open(io.BytesIO(png_data)).convert("RGBA")
    else:
        logo = Image.open(svg_path).convert("RGBA")
        logo = logo.resize((size, size), Image.LANCZOS)
    if opacity < 1.0:
        r, g, b, a = logo.split()
        a = a.point(lambda x: int(x * opacity))
        logo = Image.merge("RGBA", (r, g, b, a))
    return logo


def create_gradient(w: int, h: int, text_edge: int, fade_length: int,
                    color: tuple, from_top: bool = False,
                    max_alpha: int = 200) -> Image.Image:
    """Create a two-phase gradient: fade zone + solid zone.

    The fade zone ramps from 0 to max_alpha over fade_length pixels.
    The solid zone holds max_alpha from text_edge to the image edge.
    Text sits within the solid zone for guaranteed legibility.
    """
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    if from_top:
        # Solid from y=0 to text_edge, fade from text_edge to text_edge+fade_length
        fade_end = min(h, text_edge + fade_length)
        for y in range(fade_end):
            if y <= text_edge:
                alpha = max_alpha
            else:
                t = 1.0 - ((y - text_edge) / max(1, fade_end - text_edge))
                alpha = int(max_alpha * (t ** 1.8))
            draw.line([(0, y), (w, y)], fill=(*color, alpha))
    else:
        # Fade from fade_start to text_edge, solid from text_edge to h
        fade_start = max(0, text_edge - fade_length)
        fade_span = max(1, text_edge - fade_start)
        for y in range(fade_start, h):
            if y >= text_edge:
                alpha = max_alpha
            else:
                t = (y - fade_start) / fade_span
                alpha = int(max_alpha * (t ** 1.8))
            draw.line([(0, y), (w, y)], fill=(*color, alpha))

    return gradient


def wrap_text(text: str, font: ImageFont.FreeTypeFont,
              max_width: int) -> list:
    """Word-wrap text to fit within max_width. Returns list of lines."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines if lines else [text]


def get_font_for_line(line: str, base_font: ImageFont.FreeTypeFont,
                      base_size: int, max_width: int,
                      font_path: str, font_index: int = 0) -> ImageFont.FreeTypeFont:
    """Return a font that fits the line within max_width, scaling down if needed."""
    bbox = base_font.getbbox(line)
    line_w = bbox[2] - bbox[0]
    if line_w <= max_width:
        return base_font
    new_size = int(base_size * (max_width / line_w) * 0.80)
    return ImageFont.truetype(font_path, new_size, index=font_index)


def render_headline_block(draw: ImageDraw.Draw, all_lines: list,
                          accent_word: str, headline_font: ImageFont.FreeTypeFont,
                          margin_side: int, max_text_w: int, y_start: int,
                          line_spacing_px: int, headline_color: tuple,
                          accent_color: tuple,
                          font_path: str = "", font_index: int = 0,
                          alpha: int = 255) -> int:
    """Render headline lines with accent coloring. Returns y position after last line."""
    y = y_start
    base_size = headline_font.size

    # Pre-pass: find the smallest font needed across ALL lines
    # so every line renders at the same size (uniform headline block)
    effective_font = headline_font
    for line in all_lines:
        test_font = get_font_for_line(line, headline_font, base_size, max_text_w,
                                      font_path, font_index)
        if test_font.size < effective_font.size:
            effective_font = test_font

    for line in all_lines:
        font = effective_font
        upper_accent = accent_word.upper() if accent_word else ""

        if upper_accent and upper_accent in line:
            idx = line.index(upper_accent)
            before = line[:idx].rstrip()
            accent = line[idx:idx + len(upper_accent)]
            after = line[idx + len(upper_accent):].lstrip()

            parts = []
            if before:
                parts.append((before, headline_color))
            parts.append((accent, accent_color))
            if after:
                parts.append((after, headline_color))

            space_w = font.getbbox(" ")[2] - font.getbbox(" ")[0]
            total_w = sum(font.getbbox(t)[2] - font.getbbox(t)[0] for t, _ in parts)
            total_w += space_w * max(0, len(parts) - 1)

            cx = margin_side + (max_text_w - total_w) // 2
            for j, (text, color) in enumerate(parts):
                draw.text((cx, y), text, fill=(*color, alpha), font=font)
                tw = font.getbbox(text)[2] - font.getbbox(text)[0]
                cx += tw
                if j < len(parts) - 1:
                    cx += space_w
        else:
            bbox = font.getbbox(line)
            tw = bbox[2] - bbox[0]
            cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, y), line, fill=(*headline_color, alpha), font=font)

        # Use ascent for line height from the ACTUAL rendered font
        ascent, _ = effective_font.getmetrics()
        y += ascent + line_spacing_px

    return y


def render_text_shadow(img, shadow_cfg, scale_fn, draw_callback):
    """Render blurred text shadow layer.

    Args:
        img: Base image (used for dimensions).
        shadow_cfg: Dict with blur, opacity keys. None to skip.
        scale_fn: Scale function for converting base px to actual px.
        draw_callback: Function(draw, alpha) that draws all text on the shadow layer.

    Returns:
        img with shadow composited, or original img if no shadow_cfg.
    """
    if not shadow_cfg:
        return img
    w, h = img.size
    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    s_alpha = shadow_cfg.get("opacity", 180)
    draw_callback(shadow_draw, s_alpha)
    blur_radius = scale_fn(shadow_cfg.get("blur", 20))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return Image.alpha_composite(img, shadow_layer)


# ---------------------------------------------------------------------------
# Main compositor
# ---------------------------------------------------------------------------

def compose_slide(scene_path: str, slide_config: dict, output_path: str,
                  brand: dict, line_color: str = "default") -> str:
    """Compose a complete branded slide from a scene-only image.

    Args:
        scene_path: Path to scene-only PNG from NanoBanana.
        slide_config: Dict with type, headline, accent_word, subtext, handle.
        output_path: Where to save the composited slide.
        brand: Brand config dict from load_brand_config().
        line_color: "default" or "alt" — selects divider line color from brand config.

    Returns:
        output_path
    """
    slide_type = slide_config.get("type", "content")

    colors = brand["colors"]
    fonts_cfg = brand["fonts"]
    logo_cfg = brand["logo"]
    layout = brand["layout"]

    img = Image.open(scene_path).convert("RGBA")
    w, h = img.size
    base_width = layout.get("base_width", 1080)
    scale = w / base_width
    s = lambda px: int(px * scale)

    # --- Scrim overlay (dark layer between image and text for legibility) ---
    scrim_cfg = brand.get("scrim")
    if scrim_cfg:
        scrim_alpha = scrim_cfg.get("opacity", 30)
        scrim = Image.new("RGBA", (w, h), (0, 0, 0, scrim_alpha))
        img = Image.alpha_composite(img, scrim)

    # --- Load fonts ---
    hl_cfg = fonts_cfg["headline"]
    st_cfg = fonts_cfg["subtext"]
    hd_cfg = fonts_cfg.get("handle", {})

    headline_font = ImageFont.truetype(
        hl_cfg["path"], s(hl_cfg["size"]), index=hl_cfg.get("index", 0))
    subtext_font = ImageFont.truetype(
        st_cfg["path"], s(st_cfg["size"]), index=st_cfg.get("index", 0))
    handle_font = ImageFont.truetype(
        hd_cfg.get("path", st_cfg["path"]),
        s(hd_cfg.get("size", 26)),
        index=hd_cfg.get("index", 0))

    # --- Layout metrics ---
    margin_bottom = s(layout.get("text_bottom_margin", 100))
    # Logo boundary — used to dynamically avoid overlap per slide
    _logo_top_y = h - s(logo_cfg.get("content_size", 60)) - s(logo_cfg.get("padding", 18))
    margin_top = s(layout.get("text_top_margin", 50))
    margin_side = s(layout.get("text_side_margin", 60))
    max_text_w = w - 2 * margin_side
    bleed = s(layout.get("gradient_bleed", 350))
    max_alpha = layout.get("gradient_max_alpha", 200)
    grad_color = colors.get("gradient_target", (8, 12, 22))

    # --- Prepare text data ---
    headline_lines = slide_config.get("headline", [])
    accent_word = slide_config.get("accent_word", "")
    subtext_amber = slide_config.get("subtext_amber", "").upper()
    subtext_white = slide_config.get("subtext_white", "").upper()
    handle_text = slide_config.get("handle", "")
    has_subtext = bool(subtext_amber or subtext_white)

    all_lines = [line.upper() for line in headline_lines]
    if accent_word and not any(accent_word.upper() in l.upper() for l in headline_lines):
        all_lines.append(accent_word.upper())

    # Calculate headline height using ascent (optimal for ALL CAPS)
    hl_ascent, _ = headline_font.getmetrics()
    hl_natural_line_h = hl_ascent
    hl_line_sp = s(layout.get("headline_line_spacing", 0))
    headline_total_h = len(all_lines) * hl_natural_line_h
    if len(all_lines) > 1:
        headline_total_h += (len(all_lines) - 1) * hl_line_sp

    headline_color = colors.get("headline", (255, 255, 255))
    accent_color = colors.get("accent", (237, 140, 68))
    subtext_primary = colors.get("subtext_primary", (237, 140, 68))
    subtext_secondary = colors.get("subtext_secondary", (231, 231, 231))
    shadow_cfg = brand.get("text_shadow")

    # --- CONTENT slides: all text at BOTTOM in one block ---
    if slide_type == "content" and has_subtext:
        line_sp = s(layout.get("subtext_line_spacing", 10))
        hl_line_sp = s(layout.get("headline_line_spacing", 10))
        headline_subtext_gap = s(layout.get("subtext_top_gap", 30))

        # Wrap and measure subtext
        amber_lines = wrap_text(subtext_amber, subtext_font, max_text_w) if subtext_amber else []
        white_lines = wrap_text(subtext_white, subtext_font, max_text_w) if subtext_white else []
        single_line_h = subtext_font.getbbox("A")[3] - subtext_font.getbbox("A")[1]
        total_sub_lines = len(amber_lines) + len(white_lines)
        subtext_total_h = 0
        if total_sub_lines > 0:
            subtext_total_h = total_sub_lines * single_line_h + (total_sub_lines - 1) * line_sp

        # Total block height: headline + gap + subtext + bottom margin
        total_block_h = headline_total_h + headline_subtext_gap + subtext_total_h + margin_bottom
        text_top_y = h - total_block_h

        # Auto-shrink if block exceeds 55% of image height
        max_text_zone = int(h * 0.55)
        if total_block_h > max_text_zone:
            shrink = max_text_zone / total_block_h
            new_hl_size = max(s(40), int(headline_font.size * shrink))
            headline_font = ImageFont.truetype(
                hl_cfg["path"], new_hl_size, index=hl_cfg.get("index", 0))
            headline_total_h = 0
            for i, line in enumerate(all_lines):
                bbox = headline_font.getbbox(line)
                headline_total_h += bbox[3] - bbox[1]
                if i < len(all_lines) - 1:
                    headline_total_h += hl_line_sp

            new_st_size = max(s(15), int(subtext_font.size * shrink))
            subtext_font = ImageFont.truetype(
                st_cfg["path"], new_st_size, index=st_cfg.get("index", 0))
            amber_lines = wrap_text(subtext_amber, subtext_font, max_text_w) if subtext_amber else []
            white_lines = wrap_text(subtext_white, subtext_font, max_text_w) if subtext_white else []
            single_line_h = subtext_font.getbbox("A")[3] - subtext_font.getbbox("A")[1]
            total_sub_lines = len(amber_lines) + len(white_lines)
            subtext_total_h = total_sub_lines * single_line_h + (total_sub_lines - 1) * line_sp if total_sub_lines > 0 else 0

            total_block_h = headline_total_h + headline_subtext_gap + subtext_total_h + margin_bottom
            text_top_y = h - total_block_h

        # Single bottom gradient — solid behind text, fade above
        gradient = create_gradient(w, h, text_edge=text_top_y, fade_length=bleed,
                                   color=grad_color, from_top=False, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)

        draw = ImageDraw.Draw(img)

        # Headline at top of text block
        y_after = render_headline_block(draw, all_lines, accent_word, headline_font,
                              margin_side, max_text_w, text_top_y,
                              hl_line_sp, headline_color, accent_color,
                              hl_cfg["path"], hl_cfg.get("index", 0))

        # Subtext below headline (top-down)
        y = y_after + headline_subtext_gap
        for al in amber_lines:
            bbox = subtext_font.getbbox(al)
            tw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, y), al, fill=(*subtext_primary, 255), font=subtext_font)
            y += lh + line_sp

        for wl in white_lines:
            bbox = subtext_font.getbbox(wl)
            tw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, y), wl, fill=(*subtext_secondary, 255), font=subtext_font)
            y += lh + line_sp

        # Logo bottom-right (skip if content_size is 0)
        if logo_cfg.get("content_size", 60) > 0:
            logo_px = s(logo_cfg.get("content_size", 60))
            pad = s(logo_cfg.get("padding", 18))
            available = h - y - s(10) - pad
            if available < logo_px:
                logo_px = max(s(30), available)
            logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - pad, y + s(10)), logo)

    # --- CLOSER: vertically centered text ---
    elif slide_type == "closer":
        handle_h = 0
        handle_gap = s(layout.get("handle_gap", 40))
        if handle_text:
            bbox = handle_font.getbbox(handle_text)
            handle_h = bbox[3] - bbox[1]

        total_block_h = headline_total_h
        if handle_text:
            total_block_h += handle_gap + handle_h

        text_top_y = h - margin_bottom - total_block_h

        gradient = create_gradient(w, h, text_edge=text_top_y, fade_length=bleed,
                                   color=grad_color, from_top=False, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)

        draw = ImageDraw.Draw(img)

        render_headline_block(draw, all_lines, accent_word, headline_font,
                              margin_side, max_text_w, text_top_y,
                              s(layout.get("headline_line_spacing", 10)),
                              headline_color, accent_color,
                              hl_cfg["path"], hl_cfg.get("index", 0))

        if handle_text:
            handle_y = text_top_y + headline_total_h + handle_gap
            bbox = handle_font.getbbox(handle_text)
            tw = bbox[2] - bbox[0]
            cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, handle_y), handle_text,
                      fill=(*headline_color, 230), font=handle_font)

        # Logo bottom-right (skip if content_size is 0)
        if logo_cfg.get("content_size", 60) > 0:
            text_end_y = text_top_y + total_block_h
            logo_px = s(logo_cfg.get("content_size", 60))
            pad = s(logo_cfg.get("padding", 18))
            available = h - text_end_y - s(10) - pad
            if available < logo_px:
                logo_px = max(s(30), available)
            logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - pad, text_end_y + s(10)), logo)

    # --- HOOK: everything at BOTTOM ---
    elif slide_type == "hook":
        text_top_y = h - margin_bottom - headline_total_h

        gradient = create_gradient(w, h, text_edge=text_top_y, fade_length=bleed,
                                   color=grad_color, from_top=False, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)

        draw = ImageDraw.Draw(img)

        render_headline_block(draw, all_lines, accent_word, headline_font,
                              margin_side, max_text_w, text_top_y,
                              s(layout.get("headline_line_spacing", 10)),
                              headline_color, accent_color,
                              hl_cfg["path"], hl_cfg.get("index", 0))

        # Logo centered with divider
        logo_px = s(logo_cfg.get("hook_size", 95))
        logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
        lw, lh = logo.size
        divider_y = text_top_y - s(layout.get("divider_gap_above_text", 50))
        logo_x = (w - lw) // 2
        logo_y = divider_y - (lh // 2)

        divider_color_key = "divider_alt" if line_color == "alt" else "divider_default"
        div_color = colors.get(divider_color_key, headline_color)

        line_thick = max(1, s(layout.get("divider_thickness", 3)))
        gap = s(layout.get("divider_gap", 20))
        left_end = logo_x - gap
        right_start = logo_x + lw + gap
        if left_end > 0:
            draw.rectangle([0, divider_y, left_end, divider_y + line_thick],
                           fill=(*div_color, 180))
        if right_start < w:
            draw.rectangle([right_start, divider_y, w, divider_y + line_thick],
                           fill=(*div_color, 180))
        img.paste(logo, (logo_x, logo_y), logo)

    # --- CONTENT without subtext: headline at bottom like hook, but bottom-right logo ---
    else:
        text_top_y = h - margin_bottom - headline_total_h

        gradient = create_gradient(w, h, text_edge=text_top_y, fade_length=bleed,
                                   color=grad_color, from_top=False, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)

        draw = ImageDraw.Draw(img)

        render_headline_block(draw, all_lines, accent_word, headline_font,
                              margin_side, max_text_w, text_top_y,
                              s(layout.get("headline_line_spacing", 10)),
                              headline_color, accent_color,
                              hl_cfg["path"], hl_cfg.get("index", 0))

        # Logo bottom-right (skip if content_size is 0)
        if logo_cfg.get("content_size", 60) > 0:
            text_end_y = h - margin_bottom
            logo_px = s(logo_cfg.get("content_size", 60))
            pad = s(logo_cfg.get("padding", 18))
            available = h - text_end_y - s(10) - pad
            if available < logo_px:
                logo_px = max(s(30), available)
            logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - pad, text_end_y + s(10)), logo)

    # --- Website URL (brand-level, rendered only when slide requests it) ---
    website_url = brand.get("website")
    show_website = slide_config.get("show_website", False)
    if website_url and show_website:
        website_color = colors.get("website", (110, 193, 214))
        website_font = ImageFont.truetype(
            hd_cfg.get("path", st_cfg["path"]),
            s(hd_cfg.get("size", 26)),
            index=hd_cfg.get("index", 0))
        website_text = website_url.upper()
        if not hasattr(img, 'im'):
            draw = ImageDraw.Draw(img)
        bbox = website_font.getbbox(website_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        cx = (w - tw) // 2
        cy = h - s(40) - th
        draw.text((cx, cy), website_text, fill=(*website_color, 255), font=website_font)

    # --- Save ---
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=False)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  [{slide_type:7s}] {Path(output_path).name} ({size_mb:.1f}MB)")
    return output_path


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_config(config_path: str, brand: dict) -> list:
    """Process a carousel JSON config file. Returns list of output paths."""
    with open(config_path) as f:
        config = json.load(f)

    output_dir = Path(config.get("output_dir", "."))
    output_dir.mkdir(parents=True, exist_ok=True)
    line_color = config.get("line_color", "default")

    # Map legacy color names to new keys
    if line_color == "white":
        line_color = "default"
    elif line_color == "blue":
        line_color = "alt"

    print(f"Compositing {len(config['slides'])} slides to {output_dir}:\n")

    outputs = []
    for i, slide in enumerate(config["slides"]):
        scene_path = slide["scene"]
        if not os.path.isabs(scene_path):
            scene_path = str(Path(config_path).parent / scene_path)

        output_name = slide.get("output", f"{i + 1}.png")
        output_path = str(output_dir / output_name)

        compose_slide(scene_path, slide, output_path, brand, line_color)
        outputs.append(output_path)

    print(f"\nDone! Composited {len(config['slides'])} slides.")

    # Export Instagram-ready versions
    export_for_instagram(outputs, output_dir)

    return outputs


# ---------------------------------------------------------------------------
# Instagram export
# ---------------------------------------------------------------------------

def export_for_instagram(slide_paths: list, output_dir: Path,
                         target_width: int = 1080) -> list:
    """Resize composited 4K slides to Instagram-ready dimensions.

    Outputs high-quality JPEGs at 1080x1350 (4:5 portrait) to an export/
    subfolder. The 4K PNGs are kept for archival.
    """
    export_dir = Path(output_dir) / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting {len(slide_paths)} slides for Instagram to {export_dir}:\n")

    exported = []
    for path in slide_paths:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        scale = target_width / w
        target_height = int(h * scale)
        img = img.resize((target_width, target_height), Image.LANCZOS)

        export_name = Path(path).stem + ".jpg"
        export_path = str(export_dir / export_name)
        img.save(export_path, "JPEG", quality=95, subsampling=0)

        size_kb = os.path.getsize(export_path) / 1024
        print(f"  {export_name} ({target_width}x{target_height}, {size_kb:.0f}KB)")
        exported.append(export_path)

    print(f"\nExported {len(exported)} slides to {export_dir}/")
    return exported
