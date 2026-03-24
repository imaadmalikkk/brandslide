#!/usr/bin/env python3
"""
{{BRAND_NAME}} Slide Compositor — Thin wrapper around shared/core.py.

Loads {{BRAND_NAME}}'s brand.json and delegates to the core engine.

Usage:
    python3 compose_slide.py --config carousel.json
    python3 compose_slide.py --scene scene.png --type hook --headline "TEXT" --accent "WORD" --output 1.png
"""

import sys
import os

# Add shared/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from pathlib import Path
from core import load_brand_config, compose_slide, process_config

BRAND_JSON = str(Path(__file__).parent / "brand.json")


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python3 compose_slide.py --config carousel.json")
        print("  python3 compose_slide.py --scene scene.png --type hook \\")
        print("    --headline 'TEXT HERE,SECOND LINE' --accent WORD --output 1.png")
        sys.exit(1)

    brand = load_brand_config(BRAND_JSON)

    if "--config" in args:
        idx = args.index("--config")
        process_config(args[idx + 1], brand)
    else:
        scene = args[args.index("--scene") + 1] if "--scene" in args else None
        slide_type = args[args.index("--type") + 1] if "--type" in args else "content"
        headline_raw = args[args.index("--headline") + 1] if "--headline" in args else ""
        accent = args[args.index("--accent") + 1] if "--accent" in args else ""
        output = args[args.index("--output") + 1] if "--output" in args else "output.png"
        amber = args[args.index("--amber") + 1] if "--amber" in args else ""
        white_sub = args[args.index("--white") + 1] if "--white" in args else ""
        handle = args[args.index("--handle") + 1] if "--handle" in args else ""
        line_color = args[args.index("--line-color") + 1] if "--line-color" in args else "default"

        slide_config = {
            "type": slide_type,
            "headline": headline_raw.split(","),
            "accent_word": accent,
            "subtext_amber": amber,
            "subtext_white": white_sub,
            "handle": handle,
        }

        compose_slide(scene, slide_config, output, brand, line_color)


if __name__ == "__main__":
    main()
