# brandslide Web App — MVP Design Spec

## Overview

A SaaS web app that generates professional Instagram carousels for any brand. User pastes a website URL, the AI extracts their brand identity, then produces fully researched and composited carousel content on demand.

**Target:** $100/mo prosumer plan, 20 carousels/month.
**MVP goal:** Full pipeline working end-to-end in a weekend. Topic goes in, downloadable carousel comes out.

---

## User Journey

1. **Land on page.** Single page. Paste brand website URL. Upload logo. Enter topic. Pick template. Hit Generate.
2. **Brand setup (first time).** Agent SDK crawls URL, extracts colors/fonts/voice. Shows preview card. User confirms. Saved to Convex.
3. **Generate carousel.** Streaming progress: Researching → Scripting → Generating scenes → Compositing → Exporting.
4. **Review + download.** Slide grid with thumbnails. Caption text. Download ZIP (4K PNGs + 1080px JPEGs + caption.txt).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router) |
| Database | Convex |
| AI Agent | Claude Agent SDK (TypeScript) |
| Image Generation | fal.ai (NanoBanana 2 — Gemini 3.1 Flash) |
| Compositing | node-canvas (server-side Canvas API) |
| Fonts | Bundled Impact.ttf + HelveticaNeue in repo |
| File Storage | Convex file storage |
| Streaming | Server-Sent Events (SSE) |
| Deploy | Railway |
| Styling | Tailwind CSS |

---

## File Structure

```
brandslide-app/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── railway.toml
│
├── convex/
│   ├── schema.ts                         # brands, carousels, slides
│   ├── brands.ts                         # CRUD mutations/queries
│   ├── carousels.ts                      # create, updateStatus, get
│   └── slides.ts                         # store, getByCarousel
│
├── public/
│   └── fonts/
│       ├── Impact.ttf
│       └── HelveticaNeue-Medium.ttf
│
├── src/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout + ConvexProvider
│   │   ├── page.tsx                      # Single-page UI
│   │   └── api/
│   │       ├── setup-brand/route.ts      # POST: URL → brand config
│   │       └── generate/route.ts         # POST: topic + brand → SSE → carousel
│   │
│   ├── components/
│   │   ├── BrandSetup.tsx                # URL input + logo upload + color preview
│   │   ├── GenerateForm.tsx              # Topic + template picker + generate button
│   │   ├── ProgressStream.tsx            # Real-time progress display
│   │   ├── SlideGrid.tsx                 # Carousel preview thumbnails
│   │   └── DownloadButton.tsx            # ZIP download
│   │
│   ├── lib/
│   │   ├── compositor/
│   │   │   ├── index.ts                  # composeSlide() main entry
│   │   │   ├── gradient.ts               # createGradient()
│   │   │   ├── text.ts                   # renderHeadline(), wrapText()
│   │   │   ├── logo.ts                   # loadLogo()
│   │   │   └── templates.ts              # loadTemplate(), listTemplates()
│   │   │
│   │   ├── agent/
│   │   │   ├── index.ts                  # Agent SDK setup
│   │   │   ├── tools/
│   │   │   │   ├── generate-image.ts     # fal.ai tool
│   │   │   │   └── composite-slide.ts    # Compositor tool
│   │   │   └── prompts/
│   │   │       ├── setup-brand.ts        # Brand extraction system prompt
│   │   │       └── generate-carousel.ts  # Carousel production system prompt
│   │   │
│   │   ├── fal.ts                        # fal.ai client wrapper
│   │   └── zip.ts                        # Bundle slides + caption into ZIP
│   │
│   └── types/
│       └── brand.ts                      # BrandConfig, SlideConfig, Template
│
└── templates/                            # Visual template JSONs
    ├── cinematic-story.json
    ├── bold-centered.json
    ├── editorial-clean.json
    └── text-forward.json
```

---

## Data Model (Convex)

### brands
| Field | Type | Description |
|-------|------|-------------|
| name | string | "Gymshark" |
| slug | string | "gymshark" |
| websiteUrl | string? | Source URL |
| logoStorageId | Id<_storage>? | Uploaded logo |
| colors | object | background, headline, accent, subtextPrimary, subtextSecondary, gradientTarget, dividerDefault, dividerAlt |
| fonts | object | headline: { size }, subtext: { size } |
| layout | object | gradientBleed, gradientMaxAlpha, textBottomMargin, textSideMargin, headlineLineSpacing, subtextLineSpacing |
| contentStrategy | string | Full CLAUDE.md equivalent text |
| closerOptions | array | [{ headline: string[], accent: string }] |
| handle | string | "@gymshark" |

### carousels
| Field | Type | Description |
|-------|------|-------------|
| brandId | Id<brands> | Parent brand |
| topic | string | "exercises you're doing wrong" |
| slug | string | "exercises-youre-doing-wrong" |
| template | string | "cinematic-story" |
| status | union | researching, scripting, generating_scenes, compositing, exporting, complete, failed |
| slideScript | string? | JSON of slide configs |
| caption | string? | Instagram caption |
| error | string? | Error message if failed |

### slides
| Field | Type | Description |
|-------|------|-------------|
| carouselId | Id<carousels> | Parent carousel |
| position | number | 1-8 |
| type | string | hook, content, closer |
| headline | string[] | ["EXERCISES YOU ARE", "DOING WRONG"] |
| accentWord | string | "WRONG" |
| subtextPrimary | string? | Amber subtext line |
| subtextSecondary | string? | White subtext line |
| sceneStorageId | Id<_storage>? | Raw fal.ai scene |
| compositeStorageId | Id<_storage>? | Final 4K PNG |
| exportStorageId | Id<_storage>? | 1080px JPEG |

Index: `by_carousel` on carouselId.

---

## API Routes

### POST /api/setup-brand

**Input:** `{ websiteUrl: string, logoFile?: File }`

**Process:**
1. Create Agent SDK session with brand-extraction system prompt
2. Agent crawls websiteUrl via built-in WebFetch
3. Agent extracts: colors (from CSS variables, computed styles), fonts, tone, content pillars, target audience
4. Agent returns structured JSON: colors, layout defaults, contentStrategy, closerOptions, handle
5. Store in Convex `brands` table
6. Return brand config for frontend preview

**Response:** `{ brandId, name, colors, contentStrategy (summary), ... }`

### POST /api/generate

**Input:** `{ brandId: string, topic: string, template: string }`

**Response:** Server-Sent Events stream.

**Event types:**
```
data: { "step": "status", "message": "Researching topic..." }
data: { "step": "script", "slides": [...], "caption": "..." }
data: { "step": "scene", "index": 0, "url": "https://..." }
data: { "step": "slide", "index": 0, "preview": "base64..." }
data: { "step": "complete", "carouselId": "..." }
data: { "step": "error", "message": "..." }
```

**Pipeline (all sequential, streaming progress):**
1. Load brand from Convex
2. Agent SDK: research topic (5-7 web searches) + write slide script + write caption
3. fal.ai: generate scenes in parallel (8 images, NanoBanana 2, 4K, 4:5)
4. Compositor: composite each slide (node-canvas)
5. Export: resize to 1080x1350 JPEG
6. Store all images in Convex file storage
7. Send complete event with carouselId

---

## Compositor Port (core.py → TypeScript)

Port splits into 4 focused modules:

### gradient.ts
- `createGradient(w, h, textEdge, fadeLength, color, fromTop, maxAlpha)` → Canvas Buffer
- Same 2-phase gradient: fade zone (t^1.8 easing) + solid zone
- Uses `ctx.fillRect(0, y, w, 1)` with rgba per scanline (same as Pillow's `draw.line()`)

### text.ts
- `registerFont()` at module load for Impact + HelveticaNeue
- `wrapText(ctx, text, maxWidth)` → string[] (same word-wrap algorithm)
- `renderHeadlineBlock(ctx, lines, accentWord, ...)` → y position
  - Pre-pass: find smallest font fitting all lines (uniform size)
  - Per-line: split around accent word, render parts in different colors
  - Center each line horizontally within margins

### logo.ts
- `loadLogo(logoBuffer, size, opacity)` → Canvas
  - Load PNG via `loadImage(buffer)`
  - Resize via `ctx.drawImage(img, 0, 0, size, size)`
  - Apply opacity via `ctx.globalAlpha`

### index.ts (composeSlide)
- Main entry: `composeSlide(sceneBuffer, slideConfig, brand, template)` → `{ full: Buffer, export: Buffer }`
- Template-driven: reads text position, gradient direction, logo placement from template config
- Steps: load scene → gradient → headline → subtext → handle → logo → export
- Returns 4K PNG buffer + 1080px JPEG buffer

**Key translation rules:**
| Pillow | node-canvas |
|--------|------------|
| `Image.open(buffer)` | `loadImage(buffer)` |
| `Image.alpha_composite(a, b)` | `ctx.drawImage(b, 0, 0)` with alpha |
| `ImageDraw.text((x,y), text, fill, font)` | `ctx.fillStyle = color; ctx.fillText(text, x, y)` |
| `ImageFont.truetype(path, size)` | `ctx.font = "${size}px FontFamily"` |
| `font.getbbox(text)` | `ctx.measureText(text).width` + font size for height |
| `image.save("output.png")` | `canvas.toBuffer("image/png")` |

---

## Agent SDK Configuration

### Brand Setup Agent
- Model: `claude-sonnet-4-6`
- Tools: WebFetch (built-in)
- System prompt: Instructions for extracting visual identity and content strategy from a website
- Output: Structured JSON matching the `brands` schema

### Carousel Generation Agent
- Model: `claude-sonnet-4-6`
- Tools: WebSearch (built-in, for topic research)
- System prompt: Brand's `contentStrategy` text (equivalent to CLAUDE.md) + instructions for writing slide scripts
- Output: Structured JSON with slides array + caption
- Max turns: 15 (enough for 5-7 searches + synthesis)

The agent does NOT call fal.ai or the compositor. Those are orchestrated by the API route after the agent returns the script. The agent's job is purely research + writing.

---

## Frontend Components

### page.tsx
Single page with 3 states:
1. **Setup state:** Show BrandSetup if no brand configured
2. **Ready state:** Show GenerateForm (topic + template + button)
3. **Generating state:** Show ProgressStream → SlideGrid → DownloadButton

### BrandSetup.tsx
- URL input field + "Extract Brand" button
- Logo upload dropzone
- After extraction: color swatch preview, brand name, tone summary
- "Confirm" button → saves to Convex

### GenerateForm.tsx
- Topic text input
- Template picker: 4 thumbnail cards (cinematic-story, bold-centered, editorial-clean, text-forward)
- "Generate Carousel" button

### ProgressStream.tsx
- Connects to SSE endpoint
- Shows checklist with animated spinners:
  - ✓ Researching topic
  - ● Generating scenes (3/8)
  - ○ Compositing slides
- Transitions to SlideGrid when complete

### SlideGrid.tsx
- 2x4 grid of slide thumbnails (from export JPEGs)
- Click to expand full-size preview
- Caption text displayed below grid

### DownloadButton.tsx
- Bundles all slides + caption into ZIP (client-side using JSZip)
- Downloads: 4K PNGs, 1080px JPEGs, caption.txt

---

## Cost Per Carousel

| Component | Cost |
|-----------|------|
| Claude Sonnet 4.6 (research + script, with caching) | ~$1.18 |
| fal.ai NanoBanana 2 (8 × 4K images) | ~$1.28 |
| Tavily/WebSearch (6 queries) | ~$0.05 |
| Compositing (server CPU) | $0.00 |
| **Total** | **~$2.51** |

At $100/mo with 20 carousels: $50.20 cost, $49.80 margin (50%).

---

## Deploy (Railway)

**railway.toml:**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "npm run start"
healthcheckPath = "/"
healthcheckTimeout = 300
```

Railway's Nixpacks auto-detects `canvas` in package.json and installs Cairo/Pango. No Dockerfile needed. Environment variables: `ANTHROPIC_API_KEY`, `FAL_KEY`, `CONVEX_DEPLOYMENT`, `CONVEX_DEPLOY_KEY`.

---

## Weekend Build Sequence

### Saturday Morning: Foundation (4 hrs)
1. `npx create-next-app@latest brandslide-app` with TypeScript, Tailwind, App Router
2. `npx convex dev` — set up Convex, write schema.ts
3. Install: `canvas`, `@anthropic-ai/claude-agent-sdk`, `@fal-ai/client`
4. Write brand types (types/brand.ts)
5. Write Convex mutations/queries (brands.ts, carousels.ts, slides.ts)

### Saturday Afternoon: Compositor (4 hrs)
6. Port gradient.ts (createGradient — same math, Canvas API)
7. Port text.ts (wrapText, renderHeadlineBlock — font registration, text measurement)
8. Port logo.ts (loadLogo — PNG loading, opacity)
9. Write index.ts (composeSlide — full pipeline)
10. Test: composite a test slide using a hardcoded scene image + config

### Saturday Evening: Agent + Pipeline (3 hrs)
11. Write agent/prompts/setup-brand.ts (system prompt)
12. Write agent/prompts/generate-carousel.ts (system prompt)
13. Write agent/index.ts (Agent SDK setup)
14. Write fal.ts (fal.ai client wrapper)
15. Write api/generate/route.ts (full pipeline with SSE)

### Sunday Morning: Frontend (3 hrs)
16. Write page.tsx (single page with 3 states)
17. Write BrandSetup.tsx (URL input + preview)
18. Write GenerateForm.tsx (topic + template picker)
19. Write ProgressStream.tsx (SSE consumer)
20. Write SlideGrid.tsx + DownloadButton.tsx

### Sunday Afternoon: Integration + Deploy (2 hrs)
21. End-to-end test: topic → carousel
22. Fix bugs from integration
23. Push to Railway
24. Test in production

---

## Out of Scope (for MVP)

- Auth / user accounts (hardcode to one user)
- Stripe billing
- Slide regeneration (regenerate individual slides)
- Text editing (edit headlines in-browser)
- Multiple brands per session (one brand at a time)
- Template creation in the web app (use CLI templates)
- Saved carousel history beyond current session
