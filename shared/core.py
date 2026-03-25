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


def load_template(name_or_path: str, brand: dict = None) -> dict:
    """Load a template JSON by name or file path.

    Search order:
    1. Exact file path (if name_or_path is a file)
    2. Brand-specific templates: brands/<brand>/templates/<name>.json
    3. Global templates: shared/templates/<name>.json
    """
    if os.path.isfile(name_or_path):
        p = Path(name_or_path)
    else:
        # Check brand-specific templates first
        if brand and "_brand_dir" in brand:
            brand_p = Path(brand["_brand_dir"]) / "templates" / f"{name_or_path}.json"
            if brand_p.exists():
                with open(brand_p) as f:
                    return json.load(f)
        # Fall back to global templates
        templates_dir = Path(__file__).parent / "templates"
        p = templates_dir / f"{name_or_path}.json"
        if not p.exists():
            raise FileNotFoundError(f"Template not found: {name_or_path}")
    with open(p) as f:
        return json.load(f)


def list_templates(brand: dict = None) -> list:
    """Return list of available templates (global + brand-specific).

    Brand-specific templates are listed first with a [brand] tag.
    """
    seen = set()
    templates = []

    # Brand-specific templates (higher priority)
    if brand and "_brand_dir" in brand:
        brand_tmpl_dir = Path(brand["_brand_dir"]) / "templates"
        if brand_tmpl_dir.exists():
            for p in sorted(brand_tmpl_dir.glob("*.json")):
                try:
                    with open(p) as f:
                        data = json.load(f)
                    name = data.get("name", p.stem)
                    seen.add(name)
                    templates.append({"name": name, "description": data.get("description", ""),
                                      "path": str(p), "scope": "brand"})
                except Exception:
                    pass

    # Global templates
    templates_dir = Path(__file__).parent / "templates"
    for p in sorted(templates_dir.glob("*.json")):
        try:
            with open(p) as f:
                data = json.load(f)
            name = data.get("name", p.stem)
            if name not in seen:
                templates.append({"name": name, "description": data.get("description", ""),
                                  "path": str(p), "scope": "global"})
        except Exception:
            pass

    return templates


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
# Template-driven compositor
# ---------------------------------------------------------------------------

def _compose_slide_templated(scene_path: str, slide_config: dict, output_path: str,
                              brand: dict, template: dict,
                              line_color: str = "default") -> str:
    """Compose a slide using a template layout configuration.

    Handles all template-defined layouts: text positioning (top/center/bottom),
    gradient direction, logo placement, scene modes, and alignment.
    """
    slide_type = slide_config.get("type", "content")
    colors = brand["colors"]
    fonts_cfg = brand["fonts"]
    logo_cfg = brand["logo"]
    layout = brand["layout"]

    # Resolve template layout for this slide type
    slide_layouts = template.get("slide_layouts", {})
    tmpl = slide_layouts.get(slide_type, slide_layouts.get("content", {}))

    # Font overrides from template
    font_ov = template.get("font_overrides", {})

    base_width = layout.get("base_width", 1080)

    # --- Scene loading ---
    scene_mode = tmpl.get("scene_mode", "full-bleed")
    if scene_mode == "none":
        bg_color = colors.get("background", (0, 0, 0))
        # Create solid background at 4K (4:5 ratio)
        w, h = 3712, 4608
        img = Image.new("RGBA", (w, h), (*bg_color, 255))
    else:
        img = Image.open(scene_path).convert("RGBA")
        w, h = img.size

    scale = w / base_width
    s = lambda px: int(px * scale)

    # --- Scrim ---
    scrim_cfg = brand.get("scrim")
    if scrim_cfg:
        scrim = Image.new("RGBA", (w, h), (0, 0, 0, scrim_cfg.get("opacity", 30)))
        img = Image.alpha_composite(img, scrim)

    # --- Load fonts ---
    hl_cfg = fonts_cfg["headline"]
    st_cfg = fonts_cfg["subtext"]
    hd_cfg = fonts_cfg.get("handle", {})

    hl_size = font_ov.get("headline_size", hl_cfg["size"])
    st_size = font_ov.get("subtext_size", st_cfg["size"])

    headline_font = ImageFont.truetype(
        hl_cfg["path"], s(hl_size), index=hl_cfg.get("index", 0))
    subtext_font = ImageFont.truetype(
        st_cfg["path"], s(st_size), index=st_cfg.get("index", 0))
    handle_font = ImageFont.truetype(
        hd_cfg.get("path", st_cfg["path"]),
        s(hd_cfg.get("size", 26)),
        index=hd_cfg.get("index", 0))

    # --- Layout metrics ---
    margin_bottom = s(layout.get("text_bottom_margin", 100))
    margin_top = s(layout.get("text_top_margin", 50))
    margin_side = s(layout.get("text_side_margin", 60))
    max_text_w = w - 2 * margin_side

    grad_cfg = tmpl.get("gradient", {})
    bleed = s(grad_cfg.get("bleed_override") or layout.get("gradient_bleed", 350))
    max_alpha = grad_cfg.get("max_alpha_override") or layout.get("gradient_max_alpha", 200)
    grad_color = colors.get("gradient_target", (8, 12, 22))

    # --- Prepare text ---
    headline_lines = slide_config.get("headline", [])
    accent_word = slide_config.get("accent_word", "")
    subtext_amber = slide_config.get("subtext_amber", "").upper() if tmpl.get("show_subtext", False) else ""
    subtext_white = slide_config.get("subtext_white", "").upper() if tmpl.get("show_subtext", False) else ""
    handle_text = slide_config.get("handle", "") if tmpl.get("show_handle", False) else ""

    all_lines = [line.upper() for line in headline_lines]
    if accent_word and not any(accent_word.upper() in l.upper() for l in headline_lines):
        all_lines.append(accent_word.upper())

    headline_color = colors.get("headline", (255, 255, 255))
    accent_color = colors.get("accent", (237, 140, 68))
    subtext_primary = colors.get("subtext_primary", (237, 140, 68))
    subtext_secondary = colors.get("subtext_secondary", (231, 231, 231))

    # --- Measure text blocks ---
    hl_ascent, _ = headline_font.getmetrics()
    hl_line_sp = s(layout.get("headline_line_spacing", 10))
    headline_total_h = len(all_lines) * hl_ascent
    if len(all_lines) > 1:
        headline_total_h += (len(all_lines) - 1) * hl_line_sp

    subtext_gap = s(layout.get("subtext_top_gap", 30))
    sub_line_sp = s(layout.get("subtext_line_spacing", 10))
    amber_lines = wrap_text(subtext_amber, subtext_font, max_text_w) if subtext_amber else []
    white_lines = wrap_text(subtext_white, subtext_font, max_text_w) if subtext_white else []
    single_sub_h = subtext_font.getbbox("A")[3] - subtext_font.getbbox("A")[1] if (amber_lines or white_lines) else 0
    total_sub_lines = len(amber_lines) + len(white_lines)
    subtext_total_h = (total_sub_lines * single_sub_h + (total_sub_lines - 1) * sub_line_sp) if total_sub_lines > 0 else 0

    handle_h = 0
    handle_gap = s(layout.get("handle_gap", 40))
    if handle_text:
        handle_h = handle_font.getbbox(handle_text)[3] - handle_font.getbbox(handle_text)[1]

    # Total text block height
    total_text_h = headline_total_h
    if subtext_total_h > 0:
        total_text_h += subtext_gap + subtext_total_h
    if handle_text:
        total_text_h += handle_gap + handle_h

    # --- Calculate text position ---
    text_pos = tmpl.get("text_position", "bottom")
    text_align = tmpl.get("text_align", "center")

    if text_pos == "bottom":
        text_top_y = h - margin_bottom - total_text_h
    elif text_pos == "top":
        text_top_y = margin_top
    elif text_pos == "center":
        text_top_y = (h - total_text_h) // 2
    else:
        text_top_y = h - margin_bottom - total_text_h

    # Auto-shrink if text block too large (> 55% of image)
    max_text_zone = int(h * 0.55)
    if total_text_h > max_text_zone:
        shrink = max_text_zone / total_text_h
        new_hl_size = max(s(40), int(headline_font.size * shrink))
        headline_font = ImageFont.truetype(hl_cfg["path"], new_hl_size, index=hl_cfg.get("index", 0))
        hl_ascent, _ = headline_font.getmetrics()
        headline_total_h = len(all_lines) * hl_ascent + max(0, len(all_lines) - 1) * hl_line_sp

        new_st_size = max(s(15), int(subtext_font.size * shrink))
        subtext_font = ImageFont.truetype(st_cfg["path"], new_st_size, index=st_cfg.get("index", 0))
        amber_lines = wrap_text(subtext_amber, subtext_font, max_text_w) if subtext_amber else []
        white_lines = wrap_text(subtext_white, subtext_font, max_text_w) if subtext_white else []
        single_sub_h = subtext_font.getbbox("A")[3] - subtext_font.getbbox("A")[1] if (amber_lines or white_lines) else 0
        total_sub_lines = len(amber_lines) + len(white_lines)
        subtext_total_h = (total_sub_lines * single_sub_h + (total_sub_lines - 1) * sub_line_sp) if total_sub_lines > 0 else 0

        total_text_h = headline_total_h
        if subtext_total_h > 0:
            total_text_h += subtext_gap + subtext_total_h
        if handle_text:
            total_text_h += handle_gap + handle_h

        if text_pos == "bottom":
            text_top_y = h - margin_bottom - total_text_h
        elif text_pos == "top":
            text_top_y = margin_top
        elif text_pos == "center":
            text_top_y = (h - total_text_h) // 2

    # --- Gradient ---
    grad_dir = grad_cfg.get("direction", "bottom-up")
    if grad_dir == "bottom-up":
        gradient = create_gradient(w, h, text_edge=text_top_y, fade_length=bleed,
                                   color=grad_color, from_top=False, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)
    elif grad_dir == "top-down":
        text_bottom_edge = text_top_y + total_text_h
        gradient = create_gradient(w, h, text_edge=text_bottom_edge, fade_length=bleed,
                                   color=grad_color, from_top=True, max_alpha=max_alpha)
        img = Image.alpha_composite(img, gradient)
    elif grad_dir == "full":
        overlay = Image.new("RGBA", (w, h), (*grad_color, max_alpha))
        img = Image.alpha_composite(img, overlay)
    # "none" = no gradient

    draw = ImageDraw.Draw(img)

    # --- Render headline ---
    # For left-align, adjust margin_side param to render_headline_block
    if text_align == "left":
        # render_headline_block centers text within max_text_w by default
        # For left-align, we render each line at margin_side directly
        y = text_top_y
        effective_font = headline_font
        base_size = headline_font.size
        for line in all_lines:
            test_font = get_font_for_line(line, headline_font, base_size, max_text_w,
                                          hl_cfg["path"], hl_cfg.get("index", 0))
            if test_font.size < effective_font.size:
                effective_font = test_font
        for line in all_lines:
            upper_accent = accent_word.upper() if accent_word else ""
            if upper_accent and upper_accent in line:
                idx = line.index(upper_accent)
                before = line[:idx].rstrip()
                accent = line[idx:idx + len(upper_accent)]
                after = line[idx + len(upper_accent):].lstrip()
                cx = margin_side
                space_w = effective_font.getbbox(" ")[2] - effective_font.getbbox(" ")[0]
                if before:
                    draw.text((cx, y), before, fill=(*headline_color, 255), font=effective_font)
                    cx += effective_font.getbbox(before)[2] - effective_font.getbbox(before)[0] + space_w
                draw.text((cx, y), accent, fill=(*accent_color, 255), font=effective_font)
                cx += effective_font.getbbox(accent)[2] - effective_font.getbbox(accent)[0]
                if after:
                    cx += space_w
                    draw.text((cx, y), after, fill=(*headline_color, 255), font=effective_font)
            else:
                draw.text((margin_side, y), line, fill=(*headline_color, 255), font=effective_font)
            ascent, _ = effective_font.getmetrics()
            y += ascent + hl_line_sp
        y_after = y
    else:
        y_after = render_headline_block(draw, all_lines, accent_word, headline_font,
                                        margin_side, max_text_w, text_top_y, hl_line_sp,
                                        headline_color, accent_color,
                                        hl_cfg["path"], hl_cfg.get("index", 0))

    # --- Render subtext ---
    if amber_lines or white_lines:
        y = y_after + subtext_gap
        for al in amber_lines:
            bbox = subtext_font.getbbox(al)
            tw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            if text_align == "left":
                cx = margin_side
            else:
                cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, y), al, fill=(*subtext_primary, 255), font=subtext_font)
            y += lh + sub_line_sp
        for wl in white_lines:
            bbox = subtext_font.getbbox(wl)
            tw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            if text_align == "left":
                cx = margin_side
            else:
                cx = margin_side + (max_text_w - tw) // 2
            draw.text((cx, y), wl, fill=(*subtext_secondary, 255), font=subtext_font)
            y += lh + sub_line_sp

    # --- Render handle ---
    if handle_text:
        handle_y = text_top_y + headline_total_h + (subtext_gap + subtext_total_h if subtext_total_h > 0 else 0) + handle_gap
        bbox = handle_font.getbbox(handle_text)
        tw = bbox[2] - bbox[0]
        if text_align == "left":
            cx = margin_side
        else:
            cx = margin_side + (max_text_w - tw) // 2
        draw.text((cx, handle_y), handle_text, fill=(*headline_color, 230), font=handle_font)

    # --- Logo ---
    logo_tmpl = tmpl.get("logo", {})
    logo_pos = logo_tmpl.get("position", "bottom-right")
    logo_size_key = logo_tmpl.get("size_key", "content_size")
    logo_px = s(logo_cfg.get(logo_size_key, 60))

    if logo_pos != "none" and logo_px > 0:
        logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
        lw, lh = logo.size
        pad = s(logo_cfg.get("padding", 18))

        if logo_pos == "bottom-right":
            img.paste(logo, (w - lw - pad, h - lh - pad), logo)
        elif logo_pos == "top-right":
            img.paste(logo, (w - lw - pad, pad), logo)
        elif logo_pos == "top-left":
            img.paste(logo, (pad, pad), logo)
        elif logo_pos == "center-divider":
            divider_y = text_top_y - s(layout.get("divider_gap_above_text", 50))
            logo_x = (w - lw) // 2
            logo_y = divider_y - (lh // 2)
            div_color_key = "divider_alt" if line_color == "alt" else "divider_default"
            div_color = colors.get(div_color_key, headline_color)
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

    # --- Website URL ---
    website_url = brand.get("website")
    if website_url and slide_config.get("show_website", False):
        website_color = colors.get("website", (110, 193, 214))
        website_font = ImageFont.truetype(
            hd_cfg.get("path", st_cfg["path"]), s(hd_cfg.get("size", 26)),
            index=hd_cfg.get("index", 0))
        website_text = website_url.upper()
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
    print(f"  [{slide_type:7s}] {Path(output_path).name} ({size_mb:.1f}MB) [template: {template.get('name', '?')}]")
    return output_path


# ---------------------------------------------------------------------------
# Main compositor
# ---------------------------------------------------------------------------

def compose_slide(scene_path: str, slide_config: dict, output_path: str,
                  brand: dict, line_color: str = "default",
                  template: dict = None) -> str:
    """Compose a complete branded slide from a scene-only image.

    Args:
        scene_path: Path to scene-only PNG from NanoBanana.
        slide_config: Dict with type, headline, accent_word, subtext, handle.
        output_path: Where to save the composited slide.
        brand: Brand config dict from load_brand_config().
        line_color: "default" or "alt" — selects divider line color from brand config.
        template: Optional template dict from load_template(). If provided and not
                  cinematic-story, uses the template-driven compositor.

    Returns:
        output_path
    """
    # Route to template compositor for non-legacy templates
    if template and template.get("name") != "cinematic-story":
        return _compose_slide_templated(scene_path, slide_config, output_path,
                                         brand, template, line_color)
    # Legacy path: original compositor (cinematic-story / no template)
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

        # Fixed logo dimensions (never changes size)
        logo_content_px = s(logo_cfg.get("content_size", 60))
        logo_pad = s(logo_cfg.get("padding", 18))
        logo_reserve = logo_content_px + logo_pad + s(10) if logo_content_px > 0 else 0

        # Bottom margin must clear the logo
        effective_bottom = max(margin_bottom, logo_reserve)

        # Total block height: headline + gap + subtext + bottom margin
        total_block_h = headline_total_h + headline_subtext_gap + subtext_total_h + effective_bottom
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

            total_block_h = headline_total_h + headline_subtext_gap + subtext_total_h + effective_bottom
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

        # Logo bottom-right — FIXED size, always same position
        if logo_content_px > 0:
            logo = load_logo(logo_cfg["svg_path"], logo_content_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - logo_pad, h - lh - logo_pad), logo)

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

        # Logo bottom-right — FIXED size
        logo_px = s(logo_cfg.get("content_size", 60))
        if logo_px > 0:
            pad = s(logo_cfg.get("padding", 18))
            logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - pad, h - lh - pad), logo)

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

        # Logo bottom-right — FIXED size
        logo_px = s(logo_cfg.get("content_size", 60))
        if logo_px > 0:
            pad = s(logo_cfg.get("padding", 18))
            logo = load_logo(logo_cfg["svg_path"], logo_px, logo_cfg.get("opacity", 0.90))
            lw, lh = logo.size
            img.paste(logo, (w - lw - pad, h - lh - pad), logo)

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

    # Load template if specified (checks brand-specific first, then global)
    template = None
    template_name = config.get("template")
    if template_name:
        template = load_template(template_name, brand)
        print(f"Using template: {template.get('name', template_name)}\n")

    print(f"Compositing {len(config['slides'])} slides to {output_dir}:\n")

    outputs = []
    for i, slide in enumerate(config["slides"]):
        scene_path = slide["scene"]
        if not os.path.isabs(scene_path):
            scene_path = str(Path(config_path).parent / scene_path)

        output_name = slide.get("output", f"{i + 1}.png")
        output_path = str(output_dir / output_name)

        compose_slide(scene_path, slide, output_path, brand, line_color, template)
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
