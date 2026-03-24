# brandslide

Turn any brand into professional Instagram carousels using Claude Code.

AI generates cinematic scenes. Code handles typography. Every slide is pixel-perfect and on-brand.

<p align="center">
  <img src="docs/screenshots/amar-hook.jpg" width="200"/>
  <img src="docs/screenshots/mathani-hook.jpg" width="200"/>
  <img src="docs/screenshots/gymshark-hook.jpg" width="200"/>
</p>

## Get Started

```bash
git clone https://github.com/imaadmalikkk/brandslide.git
cd brandslide
```

Open in Claude Code and run:

```
/setup my-brand
```

That's it. `/setup` installs dependencies, extracts your brand identity from a website or codebase, and generates test slides. Everything else is handled through slash commands.

## Commands

| Command | What it does |
|---------|-------------|
| `/setup [brand]` | Create a new brand. Installs deps, extracts colors/fonts/logo, generates test slides. |
| `/tune [brand]` | Fine-tune visual parameters with side-by-side comparisons. |
| `/ideate [brand]` | Brainstorm 5 carousel ideas ranked by engagement potential. |
| `/generate [brand] "topic"` | Produce a full carousel: research, scenes, compositing, captions. |

## Requirements

- macOS
- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [NanoBanana MCP server](https://github.com) (for AI scene generation)

`/setup` checks and installs Python dependencies automatically.

## How It Works

**The problem:** AI image generators can't render the same font consistently across slides.

**The solution:** NanoBanana generates scene-only images (no text). `shared/core.py` composites all brand elements (gradient, headline, subtext, logo) programmatically using real font files.

Each brand has two config files:
- **`brand.json`** — What it looks like (colors, fonts, layout, logo). See [full reference](docs/brand-config-reference.md).
- **`CLAUDE.md`** — What it sounds like (voice, content pillars, research rules, caption template).

## Example Brand

The repo includes a fully configured **Gymshark** example in `brands/gymshark/` with bundled test scenes you can composite immediately.

## Project Structure

```
brandslide/
├── shared/core.py              # Compositing engine (all brands share this)
├── brands/
│   └── gymshark/               # Example brand (your brands go here too)
│       ├── brand.json          # Visual config
│       ├── CLAUDE.md           # Content strategy
│       ├── compose_slide.py    # Thin wrapper around core.py
│       └── scenes/             # Test scenes
├── .claude/skills/             # /setup, /ideate, /generate, /tune
└── docs/                       # Brand config reference + screenshots
```
