# brandslide Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where a user pastes a brand URL, enters a topic, and gets a downloadable Instagram carousel — fully researched, scene-generated, and composited.

**Architecture:** Next.js 15 monolith on Railway. Convex for database + file storage. Anthropic API (claude-sonnet-4-6) with Tavily for research. fal.ai (NanoBanana 2) for scene generation. node-canvas for compositing (port of Python core.py). SSE streaming for real-time progress.

**Tech Stack:** Next.js 15, TypeScript, Convex, @anthropic-ai/sdk, @fal-ai/client, node-canvas, Tailwind, JSZip, Railway

**Important architectural note:** The spec mentions "Claude Agent SDK" but that SDK wraps the Claude Code CLI as a subprocess, requiring Claude Code installed on the server. Instead, we use `@anthropic-ai/sdk` (the raw Anthropic API) with a custom agent loop (~50 lines). Same model, same intelligence, works on any server. The agent loop sends messages with tool definitions, executes tool calls, and loops until the model returns a final response.

---

## File Map

| File | Responsibility |
|------|---------------|
| `convex/schema.ts` | Convex schema: brands, carousels, slides |
| `convex/brands.ts` | Brand CRUD mutations + queries |
| `convex/carousels.ts` | Carousel create/update/get |
| `convex/slides.ts` | Slide storage + retrieval |
| `src/types/brand.ts` | TypeScript types: BrandConfig, SlideConfig, TemplateConfig |
| `src/lib/compositor/gradient.ts` | 2-phase eased gradient (port of Python) |
| `src/lib/compositor/text.ts` | Font registration, wrapText, renderHeadlineBlock |
| `src/lib/compositor/logo.ts` | PNG logo loading with opacity |
| `src/lib/compositor/index.ts` | composeSlide() main entry — template-driven |
| `src/lib/compositor/templates.ts` | loadTemplate(), listTemplates() |
| `src/lib/agent/loop.ts` | Agent loop: sends messages, executes tools, loops |
| `src/lib/agent/tools.ts` | Tavily web search tool definition + handler |
| `src/lib/agent/prompts.ts` | System prompts for brand setup + carousel generation |
| `src/lib/fal.ts` | fal.ai NanoBanana wrapper |
| `src/lib/zip.ts` | ZIP bundling (JSZip) |
| `src/app/layout.tsx` | Root layout + ConvexProvider |
| `src/app/page.tsx` | Single page: 3 states (setup / generate / results) |
| `src/app/api/setup-brand/route.ts` | POST: URL → agent extracts brand → save to Convex |
| `src/app/api/generate/route.ts` | POST: topic + brand → SSE pipeline → carousel |
| `src/components/BrandSetup.tsx` | URL input + logo upload + color preview card |
| `src/components/GenerateForm.tsx` | Topic input + template picker |
| `src/components/ProgressStream.tsx` | SSE consumer + progress checklist |
| `src/components/SlideGrid.tsx` | 2x4 thumbnail grid |
| `src/components/DownloadButton.tsx` | ZIP download |
| `templates/*.json` | 4 built-in visual templates (copied from CLI) |
| `public/fonts/Impact.ttf` | Bundled headline font |
| `public/fonts/HelveticaNeue-Medium.ttf` | Bundled subtext font |
| `railway.toml` | Railway deploy config |

---

## Task 1: Project Scaffold

**Files:**
- Create: `brandslide-app/package.json` (via create-next-app)
- Create: `brandslide-app/railway.toml`
- Create: `brandslide-app/.env.local`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/imaadmalik/Developer
npx create-next-app@latest brandslide-app --typescript --tailwind --eslint --app --src-dir --no-import-alias
cd brandslide-app
```

- [ ] **Step 2: Install dependencies**

```bash
npm install canvas @anthropic-ai/sdk @fal-ai/client convex jszip
npm install -D @types/jszip
```

- [ ] **Step 3: Create .env.local**

```bash
cat > .env.local << 'EOF'
ANTHROPIC_API_KEY=your-key-here
FAL_KEY=your-key-here
TAVILY_API_KEY=your-key-here
CONVEX_DEPLOYMENT=your-deployment-here
EOF
```

- [ ] **Step 4: Create railway.toml**

```toml
[build]
builder = "nixpacks"
buildCommand = "npm run build"

[deploy]
startCommand = "npm run start"
healthcheckPath = "/"
healthcheckTimeout = 300
```

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p src/lib/compositor src/lib/agent src/types src/components templates public/fonts
```

- [ ] **Step 6: Copy fonts from system**

```bash
cp /System/Library/Fonts/Supplemental/Impact.ttf public/fonts/Impact.ttf
```

For HelveticaNeue, extract the Medium weight from the .ttc collection. If extraction is difficult, use the .ttc directly with canvas's index support, or substitute with a similar font. For MVP, we can register the .ttc:

```bash
cp /System/Library/Fonts/HelveticaNeue.ttc public/fonts/HelveticaNeue.ttc
```

- [ ] **Step 7: Copy template JSONs from CLI project**

```bash
cp /Users/imaadmalik/Developer/ContentGenerator/shared/templates/*.json templates/
```

- [ ] **Step 8: Init Convex**

```bash
npx convex dev --once
```

Follow the prompts to create a Convex project. This generates the `convex/` directory.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: scaffold brandslide-app with deps"
```

---

## Task 2: Types

**Files:**
- Create: `src/types/brand.ts`

- [ ] **Step 1: Write all TypeScript types**

```typescript
// src/types/brand.ts

export interface BrandColors {
  background: string;
  headline: string;
  accent: string;
  subtextPrimary: string;
  subtextSecondary: string;
  gradientTarget: string;
  dividerDefault: string;
  dividerAlt: string;
}

export interface BrandFonts {
  headline: { size: number };
  subtext: { size: number };
}

export interface BrandLayout {
  gradientBleed: number;
  gradientMaxAlpha: number;
  textBottomMargin: number;
  textSideMargin: number;
  headlineLineSpacing: number;
  subtextLineSpacing: number;
}

export interface CloserOption {
  headline: string[];
  accent: string;
}

export interface BrandConfig {
  name: string;
  slug: string;
  websiteUrl?: string;
  logoUrl?: string;
  colors: BrandColors;
  fonts: BrandFonts;
  layout: BrandLayout;
  contentStrategy: string;
  closerOptions: CloserOption[];
  handle: string;
}

export interface SlideConfig {
  type: "hook" | "content" | "closer";
  headline: string[];
  accentWord: string;
  subtextPrimary?: string;
  subtextSecondary?: string;
  handle?: string;
  scenePrompt?: string;
}

export interface SlideLayoutConfig {
  sceneMode: "full-bleed" | "none";
  textPosition: "bottom" | "top" | "center";
  textAlign: "center" | "left";
  gradient: {
    direction: "bottom-up" | "top-down" | "full" | "none";
    bleedOverride?: number;
    maxAlphaOverride?: number;
  };
  logo: {
    position: "bottom-right" | "top-right" | "center-divider" | "none";
    sizeKey: "hookSize" | "contentSize";
  };
  showSubtext: boolean;
  showHandle: boolean;
  elements: string[];
}

export interface TemplateConfig {
  name: string;
  description: string;
  slideLayouts: {
    hook: SlideLayoutConfig;
    content: SlideLayoutConfig;
    closer: SlideLayoutConfig;
  };
  fontOverrides?: { headlineSize?: number; subtextSize?: number };
  sceneStyleOverrides?: { basePromptAppend?: string; sceneRequired?: boolean };
}

export interface CarouselScript {
  slides: SlideConfig[];
  caption: string;
}

export interface GenerateEvent {
  step: "status" | "script" | "scene" | "slide" | "complete" | "error";
  message?: string;
  index?: number;
  url?: string;
  preview?: string;
  slides?: SlideConfig[];
  caption?: string;
  carouselId?: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/types/brand.ts && git commit -m "feat: add TypeScript types"
```

---

## Task 3: Convex Schema + Mutations

**Files:**
- Create: `convex/schema.ts`
- Create: `convex/brands.ts`
- Create: `convex/carousels.ts`
- Create: `convex/slides.ts`

- [ ] **Step 1: Write schema**

```typescript
// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  brands: defineTable({
    name: v.string(),
    slug: v.string(),
    websiteUrl: v.optional(v.string()),
    logoStorageId: v.optional(v.id("_storage")),
    colors: v.object({
      background: v.string(),
      headline: v.string(),
      accent: v.string(),
      subtextPrimary: v.string(),
      subtextSecondary: v.string(),
      gradientTarget: v.string(),
      dividerDefault: v.string(),
      dividerAlt: v.string(),
    }),
    fonts: v.object({
      headline: v.object({ size: v.number() }),
      subtext: v.object({ size: v.number() }),
    }),
    layout: v.object({
      gradientBleed: v.number(),
      gradientMaxAlpha: v.number(),
      textBottomMargin: v.number(),
      textSideMargin: v.number(),
      headlineLineSpacing: v.number(),
      subtextLineSpacing: v.number(),
    }),
    contentStrategy: v.string(),
    closerOptions: v.array(v.object({
      headline: v.array(v.string()),
      accent: v.string(),
    })),
    handle: v.string(),
  }),

  carousels: defineTable({
    brandId: v.id("brands"),
    topic: v.string(),
    slug: v.string(),
    template: v.string(),
    status: v.string(),
    slideScript: v.optional(v.string()),
    caption: v.optional(v.string()),
    error: v.optional(v.string()),
  }).index("by_brand", ["brandId"]),

  slides: defineTable({
    carouselId: v.id("carousels"),
    position: v.number(),
    type: v.string(),
    headline: v.array(v.string()),
    accentWord: v.string(),
    subtextPrimary: v.optional(v.string()),
    subtextSecondary: v.optional(v.string()),
    sceneStorageId: v.optional(v.id("_storage")),
    compositeStorageId: v.optional(v.id("_storage")),
    exportStorageId: v.optional(v.id("_storage")),
  }).index("by_carousel", ["carouselId"]),
});
```

- [ ] **Step 2: Write brands.ts**

```typescript
// convex/brands.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    name: v.string(),
    slug: v.string(),
    websiteUrl: v.optional(v.string()),
    logoStorageId: v.optional(v.id("_storage")),
    colors: v.object({
      background: v.string(),
      headline: v.string(),
      accent: v.string(),
      subtextPrimary: v.string(),
      subtextSecondary: v.string(),
      gradientTarget: v.string(),
      dividerDefault: v.string(),
      dividerAlt: v.string(),
    }),
    fonts: v.object({
      headline: v.object({ size: v.number() }),
      subtext: v.object({ size: v.number() }),
    }),
    layout: v.object({
      gradientBleed: v.number(),
      gradientMaxAlpha: v.number(),
      textBottomMargin: v.number(),
      textSideMargin: v.number(),
      headlineLineSpacing: v.number(),
      subtextLineSpacing: v.number(),
    }),
    contentStrategy: v.string(),
    closerOptions: v.array(v.object({
      headline: v.array(v.string()),
      accent: v.string(),
    })),
    handle: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("brands", args);
  },
});

export const get = query({
  args: { id: v.id("brands") },
  handler: async (ctx, { id }) => {
    return await ctx.db.get(id);
  },
});

export const list = query({
  handler: async (ctx) => {
    return await ctx.db.query("brands").collect();
  },
});

export const generateUploadUrl = mutation({
  handler: async (ctx) => {
    return await ctx.storage.generateUploadUrl();
  },
});

export const getLogoUrl = query({
  args: { storageId: v.id("_storage") },
  handler: async (ctx, { storageId }) => {
    return await ctx.storage.getUrl(storageId);
  },
});
```

- [ ] **Step 3: Write carousels.ts**

```typescript
// convex/carousels.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    brandId: v.id("brands"),
    topic: v.string(),
    slug: v.string(),
    template: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("carousels", {
      ...args,
      status: "researching",
    });
  },
});

export const updateStatus = mutation({
  args: {
    id: v.id("carousels"),
    status: v.string(),
    slideScript: v.optional(v.string()),
    caption: v.optional(v.string()),
    error: v.optional(v.string()),
  },
  handler: async (ctx, { id, ...fields }) => {
    const updates: Record<string, unknown> = { status: fields.status };
    if (fields.slideScript !== undefined) updates.slideScript = fields.slideScript;
    if (fields.caption !== undefined) updates.caption = fields.caption;
    if (fields.error !== undefined) updates.error = fields.error;
    await ctx.db.patch(id, updates);
  },
});

export const get = query({
  args: { id: v.id("carousels") },
  handler: async (ctx, { id }) => {
    return await ctx.db.get(id);
  },
});

export const listByBrand = query({
  args: { brandId: v.id("brands") },
  handler: async (ctx, { brandId }) => {
    return await ctx.db
      .query("carousels")
      .withIndex("by_brand", (q) => q.eq("brandId", brandId))
      .collect();
  },
});
```

- [ ] **Step 4: Write slides.ts**

```typescript
// convex/slides.ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    carouselId: v.id("carousels"),
    position: v.number(),
    type: v.string(),
    headline: v.array(v.string()),
    accentWord: v.string(),
    subtextPrimary: v.optional(v.string()),
    subtextSecondary: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("slides", args);
  },
});

export const updateImage = mutation({
  args: {
    id: v.id("slides"),
    sceneStorageId: v.optional(v.id("_storage")),
    compositeStorageId: v.optional(v.id("_storage")),
    exportStorageId: v.optional(v.id("_storage")),
  },
  handler: async (ctx, { id, ...fields }) => {
    const updates: Record<string, unknown> = {};
    if (fields.sceneStorageId !== undefined) updates.sceneStorageId = fields.sceneStorageId;
    if (fields.compositeStorageId !== undefined) updates.compositeStorageId = fields.compositeStorageId;
    if (fields.exportStorageId !== undefined) updates.exportStorageId = fields.exportStorageId;
    await ctx.db.patch(id, updates);
  },
});

export const getByCarousel = query({
  args: { carouselId: v.id("carousels") },
  handler: async (ctx, { carouselId }) => {
    return await ctx.db
      .query("slides")
      .withIndex("by_carousel", (q) => q.eq("carouselId", carouselId))
      .collect();
  },
});

export const generateUploadUrl = mutation({
  handler: async (ctx) => {
    return await ctx.storage.generateUploadUrl();
  },
});

export const getImageUrl = query({
  args: { storageId: v.id("_storage") },
  handler: async (ctx, { storageId }) => {
    return await ctx.storage.getUrl(storageId);
  },
});
```

- [ ] **Step 5: Push Convex schema**

```bash
npx convex dev --once
```

- [ ] **Step 6: Commit**

```bash
git add convex/ && git commit -m "feat: convex schema + mutations for brands, carousels, slides"
```

---

## Task 4: Compositor — gradient.ts

**Files:**
- Create: `src/lib/compositor/gradient.ts`

- [ ] **Step 1: Write gradient module**

```typescript
// src/lib/compositor/gradient.ts
import { createCanvas } from "canvas";

/**
 * Create a 2-phase gradient overlay as an RGBA canvas.
 *
 * Fade zone: ramps from 0 to maxAlpha using t^1.8 easing.
 * Solid zone: holds maxAlpha from textEdge to the image edge.
 *
 * Direct port of Python core.py create_gradient().
 */
export function createGradient(
  w: number,
  h: number,
  textEdge: number,
  fadeLength: number,
  color: [number, number, number],
  fromTop: boolean = false,
  maxAlpha: number = 200
): ReturnType<typeof createCanvas> {
  const canvas = createCanvas(w, h);
  const ctx = canvas.getContext("2d");

  if (fromTop) {
    const fadeEnd = Math.min(h, textEdge + fadeLength);
    for (let y = 0; y < fadeEnd; y++) {
      let alpha: number;
      if (y <= textEdge) {
        alpha = maxAlpha;
      } else {
        const t = 1.0 - (y - textEdge) / Math.max(1, fadeEnd - textEdge);
        alpha = Math.floor(maxAlpha * Math.pow(t, 1.8));
      }
      ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha / 255})`;
      ctx.fillRect(0, y, w, 1);
    }
  } else {
    const fadeStart = Math.max(0, textEdge - fadeLength);
    const fadeSpan = Math.max(1, textEdge - fadeStart);
    for (let y = fadeStart; y < h; y++) {
      let alpha: number;
      if (y >= textEdge) {
        alpha = maxAlpha;
      } else {
        const t = (y - fadeStart) / fadeSpan;
        alpha = Math.floor(maxAlpha * Math.pow(t, 1.8));
      }
      ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${alpha / 255})`;
      ctx.fillRect(0, y, w, 1);
    }
  }

  return canvas;
}
```

- [ ] **Step 2: Test gradient locally**

```bash
npx tsx -e "
const { createGradient } = require('./src/lib/compositor/gradient');
const fs = require('fs');
const g = createGradient(1080, 1350, 900, 450, [8, 12, 22], false, 255);
fs.writeFileSync('/tmp/gradient-test.png', g.toBuffer('image/png'));
console.log('Gradient test saved to /tmp/gradient-test.png');
"
```

Open `/tmp/gradient-test.png` to verify: should be transparent at top, smoothly fading to near-black at bottom.

- [ ] **Step 3: Commit**

```bash
git add src/lib/compositor/gradient.ts && git commit -m "feat: port gradient renderer to node-canvas"
```

---

## Task 5: Compositor — text.ts

**Files:**
- Create: `src/lib/compositor/text.ts`

- [ ] **Step 1: Write text module**

```typescript
// src/lib/compositor/text.ts
import { registerFont, type CanvasRenderingContext2D } from "canvas";
import path from "path";

// Register fonts at module load (once)
const fontsDir = path.join(process.cwd(), "public", "fonts");
try {
  registerFont(path.join(fontsDir, "Impact.ttf"), { family: "Impact" });
  registerFont(path.join(fontsDir, "HelveticaNeue.ttc"), { family: "HelveticaNeue" });
} catch {
  console.warn("Font registration failed — fonts may not be available");
}

export const HEADLINE_FONT_FAMILY = "Impact";
export const SUBTEXT_FONT_FAMILY = "HelveticaNeue";

/**
 * Word-wrap text to fit within maxWidth pixels.
 * Port of Python wrap_text().
 */
export function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  if (!text) return [];
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    if (ctx.measureText(test).width <= maxWidth) {
      current = test;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [text];
}

/**
 * Render headline lines with accent word coloring.
 * Returns the y position after the last line.
 * Port of Python render_headline_block().
 */
export function renderHeadlineBlock(
  ctx: CanvasRenderingContext2D,
  lines: string[],
  accentWord: string,
  marginSide: number,
  maxTextW: number,
  yStart: number,
  lineSpacing: number,
  headlineColor: string,
  accentColor: string,
  fontSize: number
): number {
  ctx.textBaseline = "top";

  // Pre-pass: find smallest font size that fits ALL lines (uniform headline)
  let effectiveSize = fontSize;
  for (const line of lines) {
    ctx.font = `${fontSize}px ${HEADLINE_FONT_FAMILY}`;
    const w = ctx.measureText(line).width;
    if (w > maxTextW) {
      const scaled = Math.floor(fontSize * (maxTextW / w) * 0.8);
      effectiveSize = Math.min(effectiveSize, scaled);
    }
  }
  ctx.font = `${effectiveSize}px ${HEADLINE_FONT_FAMILY}`;

  let y = yStart;
  const upperAccent = accentWord.toUpperCase();

  for (const line of lines) {
    if (upperAccent && line.includes(upperAccent)) {
      const idx = line.indexOf(upperAccent);
      const before = line.slice(0, idx).trimEnd();
      const accent = line.slice(idx, idx + upperAccent.length);
      const after = line.slice(idx + upperAccent.length).trimStart();

      const parts: Array<{ text: string; color: string }> = [];
      if (before) parts.push({ text: before, color: headlineColor });
      parts.push({ text: accent, color: accentColor });
      if (after) parts.push({ text: after, color: headlineColor });

      const spaceW = ctx.measureText(" ").width;
      const totalW =
        parts.reduce((sum, p) => sum + ctx.measureText(p.text).width, 0) +
        spaceW * Math.max(0, parts.length - 1);
      let cx = marginSide + (maxTextW - totalW) / 2;

      for (let j = 0; j < parts.length; j++) {
        ctx.fillStyle = parts[j].color;
        ctx.fillText(parts[j].text, cx, y);
        cx += ctx.measureText(parts[j].text).width;
        if (j < parts.length - 1) cx += spaceW;
      }
    } else {
      const tw = ctx.measureText(line).width;
      const cx = marginSide + (maxTextW - tw) / 2;
      ctx.fillStyle = headlineColor;
      ctx.fillText(line, cx, y);
    }

    y += effectiveSize + lineSpacing;
  }

  return y;
}

/**
 * Render subtext lines (primary color then secondary color).
 * Returns the y position after the last line.
 */
export function renderSubtext(
  ctx: CanvasRenderingContext2D,
  primaryLines: string[],
  secondaryLines: string[],
  marginSide: number,
  maxTextW: number,
  yStart: number,
  lineSpacing: number,
  primaryColor: string,
  secondaryColor: string,
  fontSize: number,
  align: "center" | "left" = "center"
): number {
  ctx.font = `${fontSize}px ${SUBTEXT_FONT_FAMILY}`;
  ctx.textBaseline = "top";
  let y = yStart;

  const renderLine = (text: string, color: string) => {
    const tw = ctx.measureText(text).width;
    const cx = align === "left" ? marginSide : marginSide + (maxTextW - tw) / 2;
    ctx.fillStyle = color;
    ctx.fillText(text, cx, y);
    y += fontSize + lineSpacing;
  };

  for (const line of primaryLines) renderLine(line, primaryColor);
  for (const line of secondaryLines) renderLine(line, secondaryColor);

  return y;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/compositor/text.ts && git commit -m "feat: port text rendering to node-canvas"
```

---

## Task 6: Compositor — logo.ts + templates.ts

**Files:**
- Create: `src/lib/compositor/logo.ts`
- Create: `src/lib/compositor/templates.ts`

- [ ] **Step 1: Write logo module**

```typescript
// src/lib/compositor/logo.ts
import { createCanvas, loadImage, type CanvasRenderingContext2D } from "canvas";

/**
 * Load a PNG logo, resize to given dimensions, and apply opacity.
 * Returns a canvas with the logo (use as source for drawImage).
 */
export async function loadLogo(
  logoSource: Buffer | string,
  size: number,
  opacity: number = 0.9
): Promise<ReturnType<typeof createCanvas>> {
  const img = await loadImage(logoSource);
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext("2d");
  ctx.globalAlpha = opacity;
  ctx.drawImage(img, 0, 0, size, size);
  return canvas;
}

/**
 * Place logo on the main canvas at the specified position.
 */
export function placeLogo(
  ctx: CanvasRenderingContext2D,
  logoCanvas: ReturnType<typeof createCanvas>,
  position: string,
  canvasW: number,
  canvasH: number,
  padding: number,
  dividerConfig?: {
    dividerY: number;
    dividerColor: string;
    lineThickness: number;
    gap: number;
  }
) {
  const lw = logoCanvas.width;
  const lh = logoCanvas.height;

  if (position === "bottom-right") {
    ctx.drawImage(logoCanvas, canvasW - lw - padding, canvasH - lh - padding);
  } else if (position === "top-right") {
    ctx.drawImage(logoCanvas, canvasW - lw - padding, padding);
  } else if (position === "center-divider" && dividerConfig) {
    const { dividerY, dividerColor, lineThickness, gap } = dividerConfig;
    const logoX = (canvasW - lw) / 2;
    const logoY = dividerY - lh / 2;

    // Draw divider lines (left and right of logo)
    ctx.fillStyle = dividerColor;
    const leftEnd = logoX - gap;
    const rightStart = logoX + lw + gap;
    if (leftEnd > 0) {
      ctx.globalAlpha = 0.7;
      ctx.fillRect(0, dividerY, leftEnd, lineThickness);
    }
    if (rightStart < canvasW) {
      ctx.globalAlpha = 0.7;
      ctx.fillRect(rightStart, dividerY, canvasW - rightStart, lineThickness);
    }
    ctx.globalAlpha = 1.0;
    ctx.drawImage(logoCanvas, logoX, logoY);
  }
}
```

- [ ] **Step 2: Write templates module**

```typescript
// src/lib/compositor/templates.ts
import fs from "fs";
import path from "path";
import type { TemplateConfig } from "@/types/brand";

const TEMPLATES_DIR = path.join(process.cwd(), "templates");

export function loadTemplate(name: string): TemplateConfig {
  const filePath = path.join(TEMPLATES_DIR, `${name}.json`);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Template not found: ${name}`);
  }
  const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  return {
    name: raw.name,
    description: raw.description,
    slideLayouts: {
      hook: raw.slide_layouts.hook,
      content: raw.slide_layouts.content,
      closer: raw.slide_layouts.closer,
    },
    fontOverrides: raw.font_overrides,
    sceneStyleOverrides: raw.scene_style_overrides,
  };
}

export function listTemplates(): Array<{ name: string; description: string }> {
  const files = fs.readdirSync(TEMPLATES_DIR).filter((f) => f.endsWith(".json"));
  return files.map((f) => {
    const raw = JSON.parse(fs.readFileSync(path.join(TEMPLATES_DIR, f), "utf-8"));
    return { name: raw.name, description: raw.description };
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lib/compositor/logo.ts src/lib/compositor/templates.ts && git commit -m "feat: logo placement + template loading"
```

---

## Task 7: Compositor — composeSlide (main entry)

**Files:**
- Create: `src/lib/compositor/index.ts`

- [ ] **Step 1: Write main compositor**

```typescript
// src/lib/compositor/index.ts
import { createCanvas, loadImage } from "canvas";
import { createGradient } from "./gradient";
import { renderHeadlineBlock, renderSubtext, wrapText, HEADLINE_FONT_FAMILY, SUBTEXT_FONT_FAMILY } from "./text";
import { loadLogo, placeLogo } from "./logo";
import { loadTemplate } from "./templates";
import type { SlideConfig, BrandConfig, TemplateConfig } from "@/types/brand";

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

export async function composeSlide(
  sceneBuffer: Buffer,
  slide: SlideConfig,
  brand: BrandConfig,
  templateName: string = "cinematic-story",
  logoBuffer?: Buffer
): Promise<{ full: Buffer; export: Buffer }> {
  const template = loadTemplate(templateName);
  const layout = template.slideLayouts[slide.type] ?? template.slideLayouts.content;

  const BASE_WIDTH = 1080;
  const LOGO_HOOK_SIZE = 95;
  const LOGO_CONTENT_SIZE = 60;
  const LOGO_PADDING = 18;

  // Load scene or create solid background
  let scene;
  if (layout.sceneMode === "none") {
    scene = createCanvas(3712, 4608);
    const sctx = scene.getContext("2d");
    sctx.fillStyle = brand.colors.background;
    sctx.fillRect(0, 0, 3712, 4608);
  } else {
    scene = await loadImage(sceneBuffer);
  }

  const w = scene.width;
  const h = scene.height;
  const scale = w / BASE_WIDTH;
  const s = (px: number) => Math.floor(px * scale);

  const canvas = createCanvas(w, h);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(scene, 0, 0, w, h);

  // Colors
  const gradColor = hexToRgb(brand.colors.gradientTarget);
  const headlineColor = brand.colors.headline;
  const accentColor = brand.colors.accent;
  const subtextPrimaryColor = brand.colors.subtextPrimary;
  const subtextSecondaryColor = brand.colors.subtextSecondary;

  // Layout metrics
  const marginBottom = s(brand.layout.textBottomMargin);
  const marginSide = s(brand.layout.textSideMargin);
  const maxTextW = w - 2 * marginSide;
  const bleed = s(layout.gradient.bleedOverride ?? brand.layout.gradientBleed);
  const maxAlpha = layout.gradient.maxAlphaOverride ?? brand.layout.gradientMaxAlpha;

  // Font sizes
  const hlSize = s(template.fontOverrides?.headlineSize ?? brand.fonts.headline.size);
  const stSize = s(template.fontOverrides?.subtextSize ?? brand.fonts.subtext.size);
  const hlLineSpacing = s(brand.layout.headlineLineSpacing);
  const stLineSpacing = s(brand.layout.subtextLineSpacing);
  const subtextGap = s(30);
  const handleGap = s(40);

  // Prepare text
  const headlines = slide.headline.map((l) => l.toUpperCase());
  const accentWord = slide.accentWord.toUpperCase();
  const subtextPrimary = layout.showSubtext ? (slide.subtextPrimary ?? "").toUpperCase() : "";
  const subtextSecondary = layout.showSubtext ? (slide.subtextSecondary ?? "").toUpperCase() : "";
  const handleText = layout.showHandle ? (slide.handle ?? "") : "";

  // Measure headline
  ctx.font = `${hlSize}px ${HEADLINE_FONT_FAMILY}`;
  const headlineTotalH = headlines.length * hlSize + Math.max(0, headlines.length - 1) * hlLineSpacing;

  // Measure subtext
  ctx.font = `${stSize}px ${SUBTEXT_FONT_FAMILY}`;
  const primaryLines = subtextPrimary ? wrapText(ctx, subtextPrimary, maxTextW) : [];
  const secondaryLines = subtextSecondary ? wrapText(ctx, subtextSecondary, maxTextW) : [];
  const totalSubLines = primaryLines.length + secondaryLines.length;
  const subtextTotalH = totalSubLines > 0 ? totalSubLines * stSize + (totalSubLines - 1) * stLineSpacing : 0;

  // Measure handle
  const handleH = handleText ? stSize : 0;

  // Total text block height
  let totalTextH = headlineTotalH;
  if (subtextTotalH > 0) totalTextH += subtextGap + subtextTotalH;
  if (handleText) totalTextH += handleGap + handleH;

  // Calculate text top Y based on template position
  let textTopY: number;
  if (layout.textPosition === "bottom") {
    textTopY = h - marginBottom - totalTextH;
  } else if (layout.textPosition === "top") {
    textTopY = s(50);
  } else {
    textTopY = (h - totalTextH) / 2;
  }

  // Gradient
  const gradDir = layout.gradient.direction;
  if (gradDir === "bottom-up") {
    const grad = createGradient(w, h, textTopY, bleed, gradColor, false, maxAlpha);
    ctx.drawImage(grad, 0, 0);
  } else if (gradDir === "top-down") {
    const textBottomEdge = textTopY + totalTextH;
    const grad = createGradient(w, h, textBottomEdge, bleed, gradColor, true, maxAlpha);
    ctx.drawImage(grad, 0, 0);
  } else if (gradDir === "full") {
    ctx.fillStyle = `rgba(${gradColor[0]},${gradColor[1]},${gradColor[2]},${maxAlpha / 255})`;
    ctx.fillRect(0, 0, w, h);
  }

  // Headline
  const yAfterHeadline = renderHeadlineBlock(
    ctx, headlines, accentWord, marginSide, maxTextW,
    textTopY, hlLineSpacing, headlineColor, accentColor, hlSize
  );

  // Subtext
  if (primaryLines.length > 0 || secondaryLines.length > 0) {
    renderSubtext(
      ctx, primaryLines, secondaryLines, marginSide, maxTextW,
      yAfterHeadline + subtextGap, stLineSpacing,
      subtextPrimaryColor, subtextSecondaryColor, stSize,
      layout.textAlign as "center" | "left"
    );
  }

  // Handle
  if (handleText) {
    ctx.font = `${s(26)}px ${SUBTEXT_FONT_FAMILY}`;
    ctx.fillStyle = headlineColor;
    ctx.globalAlpha = 0.9;
    const handleW = ctx.measureText(handleText).width;
    const handleX = marginSide + (maxTextW - handleW) / 2;
    const handleY = textTopY + headlineTotalH + (subtextTotalH > 0 ? subtextGap + subtextTotalH : 0) + handleGap;
    ctx.fillText(handleText, handleX, handleY);
    ctx.globalAlpha = 1.0;
  }

  // Logo
  if (layout.logo.position !== "none" && logoBuffer) {
    const logoSize = layout.logo.sizeKey === "hookSize" ? s(LOGO_HOOK_SIZE) : s(LOGO_CONTENT_SIZE);
    if (logoSize > 0) {
      const logoCanvas = await loadLogo(logoBuffer, logoSize, 0.9);
      const pad = s(LOGO_PADDING);

      if (layout.logo.position === "center-divider") {
        const dividerY = textTopY - s(50);
        placeLogo(ctx, logoCanvas, "center-divider", w, h, pad, {
          dividerY,
          dividerColor: brand.colors.dividerDefault,
          lineThickness: Math.max(1, s(3)),
          gap: s(20),
        });
      } else {
        placeLogo(ctx, logoCanvas, layout.logo.position, w, h, pad);
      }
    }
  }

  // Export both sizes
  const fullBuffer = canvas.toBuffer("image/png");

  const exportCanvas = createCanvas(1080, 1350);
  const exportCtx = exportCanvas.getContext("2d");
  exportCtx.drawImage(canvas, 0, 0, 1080, 1350);
  const exportBuffer = exportCanvas.toBuffer("image/jpeg", { quality: 0.95 });

  return { full: fullBuffer, export: exportBuffer };
}
```

- [ ] **Step 2: Test compositor end-to-end**

Use a test scene image to verify compositing works:

```bash
npx tsx -e "
const { composeSlide } = require('./src/lib/compositor');
const fs = require('fs');

const scene = fs.readFileSync('/Users/imaadmalik/Developer/ContentGenerator/brands/gymshark/scenes/1.png');
const logo = fs.readFileSync('/Users/imaadmalik/Developer/ContentGenerator/brands/gymshark/logo.png');

const brand = {
  name: 'Gymshark', slug: 'gymshark',
  colors: {
    background: '#1B1B1B', headline: '#FFFFFF', accent: '#00A8E8',
    subtextPrimary: '#00A8E8', subtextSecondary: '#BBBCBC',
    gradientTarget: '#000000', dividerDefault: '#FFFFFF', dividerAlt: '#00A8E8',
  },
  fonts: { headline: { size: 110 }, subtext: { size: 30 } },
  layout: {
    gradientBleed: 450, gradientMaxAlpha: 255,
    textBottomMargin: 100, textSideMargin: 60,
    headlineLineSpacing: 10, subtextLineSpacing: 10,
  },
  contentStrategy: '', closerOptions: [], handle: '@gymshark',
};

const slide = {
  type: 'hook', headline: ['EXERCISES YOU ARE', 'DOING WRONG'],
  accentWord: 'WRONG',
};

composeSlide(scene, slide, brand, 'cinematic-story', logo).then(result => {
  fs.writeFileSync('/tmp/compositor-test.png', result.full);
  fs.writeFileSync('/tmp/compositor-test.jpg', result.export);
  console.log('Full:', result.full.length, 'bytes');
  console.log('Export:', result.export.length, 'bytes');
  console.log('Saved to /tmp/compositor-test.png and .jpg');
});
"
```

Verify the output visually. It should match the Python compositor output.

- [ ] **Step 3: Commit**

```bash
git add src/lib/compositor/index.ts && git commit -m "feat: main composeSlide compositor (node-canvas)"
```

---

## Task 8: Agent Loop + Web Search

**Files:**
- Create: `src/lib/agent/tools.ts`
- Create: `src/lib/agent/loop.ts`
- Create: `src/lib/agent/prompts.ts`

- [ ] **Step 1: Write Tavily web search tool**

```typescript
// src/lib/agent/tools.ts
import type Anthropic from "@anthropic-ai/sdk";

export const webSearchToolDef: Anthropic.Tool = {
  name: "web_search",
  description: "Search the web for current information on a topic. Returns search results with titles, URLs, and content snippets.",
  input_schema: {
    type: "object" as const,
    properties: {
      query: { type: "string", description: "The search query" },
    },
    required: ["query"],
  },
};

export async function executeWebSearch(query: string): Promise<string> {
  const res = await fetch("https://api.tavily.com/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: process.env.TAVILY_API_KEY,
      query,
      max_results: 5,
      include_answer: true,
    }),
  });
  const data = await res.json();
  if (data.answer) {
    return `Answer: ${data.answer}\n\nSources:\n${data.results
      ?.map((r: { title: string; url: string; content: string }) => `- ${r.title} (${r.url}): ${r.content}`)
      .join("\n") ?? "No sources"}`;
  }
  return data.results
    ?.map((r: { title: string; url: string; content: string }) => `- ${r.title} (${r.url}): ${r.content}`)
    .join("\n") ?? "No results found";
}
```

- [ ] **Step 2: Write agent loop**

```typescript
// src/lib/agent/loop.ts
import Anthropic from "@anthropic-ai/sdk";
import { webSearchToolDef, executeWebSearch } from "./tools";

const client = new Anthropic();

interface AgentResult {
  text: string;
  toolCalls: number;
}

/**
 * Run an agent loop: send message → handle tool calls → repeat until final text.
 * Calls onProgress for each tool execution to enable streaming UX.
 */
export async function runAgent(
  systemPrompt: string,
  userMessage: string,
  onProgress?: (message: string) => void,
  maxTurns: number = 15
): Promise<AgentResult> {
  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: userMessage },
  ];

  let totalToolCalls = 0;

  for (let turn = 0; turn < maxTurns; turn++) {
    const response = await client.messages.create({
      model: "claude-sonnet-4-6-20250514",
      max_tokens: 8192,
      system: systemPrompt,
      messages,
      tools: [webSearchToolDef],
    });

    // Collect text and tool_use blocks
    const textBlocks: string[] = [];
    const toolUseBlocks: Anthropic.ToolUseBlock[] = [];

    for (const block of response.content) {
      if (block.type === "text") {
        textBlocks.push(block.text);
      } else if (block.type === "tool_use") {
        toolUseBlocks.push(block);
      }
    }

    // If no tool calls, we're done
    if (toolUseBlocks.length === 0 || response.stop_reason === "end_turn") {
      return { text: textBlocks.join("\n"), toolCalls: totalToolCalls };
    }

    // Execute tool calls
    messages.push({ role: "assistant", content: response.content });

    const toolResults: Anthropic.ToolResultBlockParam[] = [];
    for (const toolUse of toolUseBlocks) {
      totalToolCalls++;
      const input = toolUse.input as { query: string };

      if (toolUse.name === "web_search") {
        onProgress?.(`Searching: "${input.query}"`);
        const result = await executeWebSearch(input.query);
        toolResults.push({
          type: "tool_result",
          tool_use_id: toolUse.id,
          content: result,
        });
      } else {
        toolResults.push({
          type: "tool_result",
          tool_use_id: toolUse.id,
          content: `Unknown tool: ${toolUse.name}`,
          is_error: true,
        });
      }
    }

    messages.push({ role: "user", content: toolResults });
  }

  return { text: "Max turns reached", toolCalls: totalToolCalls };
}
```

- [ ] **Step 3: Write prompts**

```typescript
// src/lib/agent/prompts.ts
import type { BrandConfig } from "@/types/brand";

export function brandSetupPrompt(): string {
  return `You are a brand identity extraction agent. Given a website URL, you will:

1. Analyze the website's visual identity (colors, fonts, imagery style)
2. Analyze the brand's voice and content strategy
3. Return a structured JSON object

Use the web_search tool to research the brand's website, social media, and public information.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "name": "Brand Name",
  "slug": "brand-name",
  "colors": {
    "background": "#1B1B1B",
    "headline": "#FFFFFF",
    "accent": "#00A8E8",
    "subtextPrimary": "#00A8E8",
    "subtextSecondary": "#BBBCBC",
    "gradientTarget": "#000000",
    "dividerDefault": "#FFFFFF",
    "dividerAlt": "#00A8E8"
  },
  "fonts": {
    "headline": { "size": 110 },
    "subtext": { "size": 30 }
  },
  "layout": {
    "gradientBleed": 450,
    "gradientMaxAlpha": 255,
    "textBottomMargin": 100,
    "textSideMargin": 60,
    "headlineLineSpacing": 10,
    "subtextLineSpacing": 10
  },
  "contentStrategy": "Full content strategy text: brand position, tone, target audience, content pillars with topics and engagement drivers, carousel narrative arc, caption template with hashtags, research accuracy rules, non-negotiable rules.",
  "closerOptions": [
    { "headline": ["BRAND", "TAGLINE"], "accent": "BRAND" }
  ],
  "handle": "@brandhandle"
}

For colors: use the brand's actual website colors. Background should be dark (the carousel backdrop). Accent should be the brand's primary CTA/highlight color. GradientTarget should be a near-black tint matching the background tone.

For contentStrategy: write a comprehensive guide (500+ words) covering the brand's voice, 5 content pillars with topics and engagement drivers, carousel structure, caption template with relevant hashtags, and accuracy rules. This text will be used as instructions for future carousel generation.`;
}

export function carouselGenerationPrompt(brand: BrandConfig): string {
  return `You are a carousel content producer for ${brand.name} (${brand.handle}).

${brand.contentStrategy}

---

TASK: Research the given topic thoroughly, then produce a carousel script.

Use the web_search tool 5-7 times to research:
1. Core topic facts and key points
2. Common misconceptions
3. Evidence, studies, or authoritative sources
4. What competitors have posted (to differentiate)
5. Trending angles or recent developments

Then write the carousel script.

Return ONLY valid JSON (no markdown, no explanation):
{
  "slides": [
    {
      "type": "hook",
      "headline": ["LINE ONE", "LINE TWO"],
      "accentWord": "KEYWORD",
      "scenePrompt": "Detailed scene description for AI image generation. Be specific about objects, lighting, atmosphere. The scene fills the entire image edge to edge. Dark moody cinematic color grading. No text, no gradient, no overlay. Pure scene only."
    },
    {
      "type": "content",
      "headline": ["HEADLINE"],
      "accentWord": "WORD",
      "subtextPrimary": "Key insight or fact (max 15 words)",
      "subtextSecondary": "Elaboration or source (max 15 words)",
      "scenePrompt": "Scene description..."
    },
    ...more content slides (5-7 total)...,
    {
      "type": "closer",
      "headline": ${JSON.stringify(brand.closerOptions[0]?.headline ?? ["FOLLOW", "FOR MORE"])},
      "accentWord": "${brand.closerOptions[0]?.accent ?? "FOLLOW"}",
      "handle": "${brand.handle}",
      "scenePrompt": "Scene description..."
    }
  ],
  "caption": "Full Instagram caption with opening hook, key points, closing line, and hashtags."
}

Rules:
- Headlines: 5-8 words max, ALL CAPS
- 1-2 accent words per headline (the keyword carrying emotional/educational weight)
- Subtext: max 15 words per line, ALL CAPS
- Scene prompts: hyper-specific (objects, materials, textures, lighting direction, atmosphere)
- 7-9 slides total (1 hook + 5-7 content + 1 closer)
- Each slide must teach something genuinely new and valuable`;
}
```

- [ ] **Step 4: Commit**

```bash
git add src/lib/agent/ && git commit -m "feat: agent loop with Tavily web search + prompts"
```

---

## Task 9: fal.ai + ZIP Utilities

**Files:**
- Create: `src/lib/fal.ts`
- Create: `src/lib/zip.ts`

- [ ] **Step 1: Write fal.ai wrapper**

```typescript
// src/lib/fal.ts
import { fal } from "@fal-ai/client";

// fal.ai auto-reads FAL_KEY from environment

export async function generateScene(
  scenePrompt: string,
  basePrompt: string = "A slightly stylized hyperrealistic portrait image. Dark moody cinematic color grading. Dramatic directional lighting with deep shadows. Rich detailed textures. High-end cinematic CGI quality, trending on artstation."
): Promise<Buffer> {
  const fullPrompt = `${basePrompt} ${scenePrompt} The scene fills the ENTIRE image from edge to edge. No empty space. Full bleed composition. No text. No gradient. No overlay. Pure scene only.`;

  const result = await fal.subscribe("fal-ai/nano-banana-2", {
    input: {
      prompt: fullPrompt,
      aspect_ratio: "4:5",
      resolution: "4K",
      num_images: 1,
      output_format: "png",
    },
  });

  const imageUrl = result.data.images[0].url;
  const response = await fetch(imageUrl);
  const buffer = Buffer.from(await response.arrayBuffer());
  return buffer;
}
```

- [ ] **Step 2: Write ZIP utility**

```typescript
// src/lib/zip.ts
import JSZip from "jszip";

export async function createCarouselZip(
  slides: Array<{ position: number; full: Buffer; export: Buffer }>,
  caption: string
): Promise<Buffer> {
  const zip = new JSZip();

  for (const slide of slides) {
    zip.file(`${slide.position}.png`, slide.full);
    zip.file(`export/${slide.position}.jpg`, slide.export);
  }

  zip.file("caption.txt", caption);

  const buffer = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  return buffer;
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lib/fal.ts src/lib/zip.ts && git commit -m "feat: fal.ai image gen + ZIP bundling"
```

---

## Task 10: API Route — Brand Setup

**Files:**
- Create: `src/app/api/setup-brand/route.ts`

- [ ] **Step 1: Write the brand setup endpoint**

```typescript
// src/app/api/setup-brand/route.ts
import { NextResponse } from "next/server";
import { ConvexHttpClient } from "convex/browser";
import { api } from "../../../../convex/_generated/api";
import { runAgent } from "@/lib/agent/loop";
import { brandSetupPrompt } from "@/lib/agent/prompts";

const convex = new ConvexHttpClient(process.env.NEXT_PUBLIC_CONVEX_URL!);

export async function POST(req: Request) {
  try {
    const { websiteUrl } = await req.json();

    if (!websiteUrl) {
      return NextResponse.json({ error: "websiteUrl is required" }, { status: 400 });
    }

    // Run agent to extract brand identity
    const result = await runAgent(
      brandSetupPrompt(),
      `Extract the brand identity from this website: ${websiteUrl}`,
    );

    // Parse the JSON from agent response
    const jsonMatch = result.text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ error: "Failed to parse brand config" }, { status: 500 });
    }

    const brandData = JSON.parse(jsonMatch[0]);

    // Save to Convex
    const brandId = await convex.mutation(api.brands.create, {
      name: brandData.name,
      slug: brandData.slug,
      websiteUrl,
      colors: brandData.colors,
      fonts: brandData.fonts,
      layout: brandData.layout,
      contentStrategy: brandData.contentStrategy,
      closerOptions: brandData.closerOptions,
      handle: brandData.handle,
    });

    return NextResponse.json({ brandId, ...brandData });
  } catch (error) {
    console.error("Brand setup error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/api/setup-brand/ && git commit -m "feat: brand setup API endpoint"
```

---

## Task 11: API Route — Generate Carousel (SSE Pipeline)

**Files:**
- Create: `src/app/api/generate/route.ts`

- [ ] **Step 1: Write the generation pipeline with SSE**

```typescript
// src/app/api/generate/route.ts
import { ConvexHttpClient } from "convex/browser";
import { api } from "../../../../convex/_generated/api";
import { runAgent } from "@/lib/agent/loop";
import { carouselGenerationPrompt } from "@/lib/agent/prompts";
import { generateScene } from "@/lib/fal";
import { composeSlide } from "@/lib/compositor";
import { createCarouselZip } from "@/lib/zip";
import type { BrandConfig, CarouselScript } from "@/types/brand";

const convex = new ConvexHttpClient(process.env.NEXT_PUBLIC_CONVEX_URL!);

export async function POST(req: Request) {
  const { brandId, topic, template = "cinematic-story" } = await req.json();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (event: Record<string, unknown>) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      };

      try {
        // 1. Load brand
        send({ step: "status", message: "Loading brand..." });
        const brand = await convex.query(api.brands.get, { id: brandId });
        if (!brand) throw new Error("Brand not found");

        const brandConfig: BrandConfig = {
          name: brand.name,
          slug: brand.slug,
          colors: brand.colors,
          fonts: brand.fonts,
          layout: brand.layout,
          contentStrategy: brand.contentStrategy,
          closerOptions: brand.closerOptions,
          handle: brand.handle,
        };

        // Get logo buffer if available
        let logoBuffer: Buffer | undefined;
        if (brand.logoStorageId) {
          const logoUrl = await convex.query(api.brands.getLogoUrl, {
            storageId: brand.logoStorageId,
          });
          if (logoUrl) {
            const logoRes = await fetch(logoUrl);
            logoBuffer = Buffer.from(await logoRes.arrayBuffer());
          }
        }

        // 2. Create carousel record
        const slug = topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        const carouselId = await convex.mutation(api.carousels.create, {
          brandId,
          topic,
          slug,
          template,
        });

        // 3. Research + Script (Agent)
        send({ step: "status", message: "Researching topic..." });
        const agentResult = await runAgent(
          carouselGenerationPrompt(brandConfig),
          `Research and create a carousel about: ${topic}`,
          (msg) => send({ step: "status", message: msg }),
        );

        const jsonMatch = agentResult.text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) throw new Error("Failed to parse carousel script");
        const script: CarouselScript = JSON.parse(jsonMatch[0]);

        send({ step: "script", slides: script.slides, caption: script.caption });

        await convex.mutation(api.carousels.updateStatus, {
          id: carouselId,
          status: "generating_scenes",
          slideScript: JSON.stringify(script.slides),
          caption: script.caption,
        });

        // 4. Generate scenes in parallel
        send({ step: "status", message: "Generating scenes..." });
        const sceneBuffers = await Promise.all(
          script.slides.map(async (slide, i) => {
            const buffer = await generateScene(slide.scenePrompt ?? "");
            send({ step: "scene", index: i, message: `Scene ${i + 1}/${script.slides.length}` });
            return buffer;
          })
        );

        // 5. Composite each slide
        send({ step: "status", message: "Compositing slides..." });
        await convex.mutation(api.carousels.updateStatus, {
          id: carouselId,
          status: "compositing",
        });

        const composited: Array<{ position: number; full: Buffer; export: Buffer }> = [];

        for (let i = 0; i < script.slides.length; i++) {
          const result = await composeSlide(
            sceneBuffers[i],
            script.slides[i],
            brandConfig,
            template,
            logoBuffer
          );
          composited.push({ position: i + 1, ...result });

          // Send preview (base64 of export JPEG)
          const previewBase64 = result.export.toString("base64");
          send({ step: "slide", index: i, preview: `data:image/jpeg;base64,${previewBase64}` });
        }

        // 6. Create ZIP
        send({ step: "status", message: "Packaging download..." });
        const zipBuffer = await createCarouselZip(composited, script.caption);

        // Store ZIP in Convex (as a file)
        // For MVP, we'll send the ZIP as base64 in the complete event
        const zipBase64 = zipBuffer.toString("base64");

        await convex.mutation(api.carousels.updateStatus, {
          id: carouselId,
          status: "complete",
        });

        send({
          step: "complete",
          carouselId,
          caption: script.caption,
          downloadUrl: `data:application/zip;base64,${zipBase64}`,
        });
      } catch (error) {
        send({
          step: "error",
          message: error instanceof Error ? error.message : "Generation failed",
        });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add src/app/api/generate/ && git commit -m "feat: carousel generation pipeline with SSE streaming"
```

---

## Task 12: Frontend — Layout + Page

**Files:**
- Modify: `src/app/layout.tsx`
- Create: `src/app/page.tsx`

- [ ] **Step 1: Set up Convex provider in layout**

```typescript
// src/app/layout.tsx
"use client";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import "./globals.css";

const convex = new ConvexReactClient(process.env.NEXT_PUBLIC_CONVEX_URL!);

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-neutral-950 text-white min-h-screen">
        <ConvexProvider client={convex}>{children}</ConvexProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Write main page (3 states)**

```typescript
// src/app/page.tsx
"use client";
import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import BrandSetup from "@/components/BrandSetup";
import GenerateForm from "@/components/GenerateForm";
import ProgressStream from "@/components/ProgressStream";
import SlideGrid from "@/components/SlideGrid";
import type { Id } from "../../convex/_generated/dataModel";
import type { GenerateEvent } from "@/types/brand";

export default function Home() {
  const [brandId, setBrandId] = useState<Id<"brands"> | null>(null);
  const [generating, setGenerating] = useState(false);
  const [events, setEvents] = useState<GenerateEvent[]>([]);
  const [slidePreviews, setSlidePreviews] = useState<string[]>([]);
  const [caption, setCaption] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const brands = useQuery(api.brands.list);

  const handleBrandCreated = (id: Id<"brands">) => {
    setBrandId(id);
  };

  const handleGenerate = async (topic: string, template: string) => {
    if (!brandId) return;
    setGenerating(true);
    setEvents([]);
    setSlidePreviews([]);
    setDownloadUrl(null);

    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brandId, topic, template }),
    });

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const event: GenerateEvent = JSON.parse(line.slice(6));
            setEvents((prev) => [...prev, event]);

            if (event.step === "slide" && event.preview) {
              setSlidePreviews((prev) => [...prev, event.preview!]);
            }
            if (event.step === "complete") {
              setCaption(event.caption ?? "");
              setDownloadUrl((event as any).downloadUrl ?? null);
              setGenerating(false);
            }
            if (event.step === "error") {
              setGenerating(false);
            }
          } catch {}
        }
      }
    }
  };

  // State 1: No brand — show setup
  if (!brandId && (!brands || brands.length === 0)) {
    return (
      <main className="max-w-2xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-2">brandslide</h1>
        <p className="text-neutral-400 mb-10">Instagram carousels, generated.</p>
        <BrandSetup onBrandCreated={handleBrandCreated} />
      </main>
    );
  }

  // Auto-select first brand if not selected
  if (!brandId && brands && brands.length > 0) {
    setBrandId(brands[0]._id);
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold mb-2">brandslide</h1>
      <p className="text-neutral-400 mb-10">Instagram carousels, generated.</p>

      {/* State 2: Has brand — show generate form */}
      {!generating && slidePreviews.length === 0 && (
        <GenerateForm onGenerate={handleGenerate} />
      )}

      {/* State 3: Generating — show progress */}
      {generating && <ProgressStream events={events} />}

      {/* State 4: Done — show results */}
      {slidePreviews.length > 0 && !generating && (
        <SlideGrid
          previews={slidePreviews}
          caption={caption}
          downloadUrl={downloadUrl}
          onReset={() => {
            setSlidePreviews([]);
            setCaption("");
            setDownloadUrl(null);
            setEvents([]);
          }}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/app/ && git commit -m "feat: main page with 3-state flow"
```

---

## Task 13: Frontend Components

**Files:**
- Create: `src/components/BrandSetup.tsx`
- Create: `src/components/GenerateForm.tsx`
- Create: `src/components/ProgressStream.tsx`
- Create: `src/components/SlideGrid.tsx`

- [ ] **Step 1: BrandSetup component**

```typescript
// src/components/BrandSetup.tsx
"use client";
import { useState } from "react";
import type { Id } from "../../convex/_generated/dataModel";

export default function BrandSetup({
  onBrandCreated,
}: {
  onBrandCreated: (id: Id<"brands">) => void;
}) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSetup = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/setup-brand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ websiteUrl: url }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      onBrandCreated(data.brandId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <label className="block text-sm text-neutral-400">Your brand&apos;s website</label>
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://gymshark.com"
        className="w-full px-4 py-3 bg-neutral-900 border border-neutral-800 rounded-lg text-white placeholder-neutral-600 focus:outline-none focus:border-neutral-600"
      />
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <button
        onClick={handleSetup}
        disabled={!url || loading}
        className="w-full py-3 bg-white text-black font-semibold rounded-lg hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Extracting brand identity..." : "Set up brand"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: GenerateForm component**

```typescript
// src/components/GenerateForm.tsx
"use client";
import { useState } from "react";

const TEMPLATES = [
  { name: "cinematic-story", label: "Cinematic Story", desc: "Scene + bottom text" },
  { name: "bold-centered", label: "Bold Centered", desc: "Full overlay, centered" },
  { name: "editorial-clean", label: "Editorial Clean", desc: "Top text, editorial" },
  { name: "text-forward", label: "Text Forward", desc: "No scene, giant text" },
];

export default function GenerateForm({
  onGenerate,
}: {
  onGenerate: (topic: string, template: string) => void;
}) {
  const [topic, setTopic] = useState("");
  const [template, setTemplate] = useState("cinematic-story");

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm text-neutral-400 mb-2">Carousel topic</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="exercises you're doing wrong"
          className="w-full px-4 py-3 bg-neutral-900 border border-neutral-800 rounded-lg text-white placeholder-neutral-600 focus:outline-none focus:border-neutral-600"
        />
      </div>

      <div>
        <label className="block text-sm text-neutral-400 mb-3">Template</label>
        <div className="grid grid-cols-2 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.name}
              onClick={() => setTemplate(t.name)}
              className={`p-4 rounded-lg border text-left transition ${
                template === t.name
                  ? "border-white bg-neutral-900"
                  : "border-neutral-800 bg-neutral-950 hover:border-neutral-700"
              }`}
            >
              <div className="font-semibold text-sm">{t.label}</div>
              <div className="text-xs text-neutral-500">{t.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => onGenerate(topic, template)}
        disabled={!topic}
        className="w-full py-3 bg-white text-black font-semibold rounded-lg hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Generate Carousel
      </button>
    </div>
  );
}
```

- [ ] **Step 3: ProgressStream component**

```typescript
// src/components/ProgressStream.tsx
"use client";
import type { GenerateEvent } from "@/types/brand";

const STEPS = ["Researching", "Writing script", "Generating scenes", "Compositing", "Packaging"];

export default function ProgressStream({ events }: { events: GenerateEvent[] }) {
  const latestStatus = [...events].reverse().find((e) => e.step === "status");
  const sceneCount = events.filter((e) => e.step === "scene").length;
  const slideCount = events.filter((e) => e.step === "slide").length;
  const hasScript = events.some((e) => e.step === "script");
  const hasError = events.some((e) => e.step === "error");

  const currentStep = hasError
    ? -1
    : slideCount > 0
    ? 3
    : sceneCount > 0
    ? 2
    : hasScript
    ? 2
    : events.length > 0
    ? 0
    : -1;

  return (
    <div className="space-y-4">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center gap-3">
          <div className="w-5 text-center">
            {i < currentStep ? (
              <span className="text-green-400">&#10003;</span>
            ) : i === currentStep ? (
              <span className="animate-pulse text-white">&#9679;</span>
            ) : (
              <span className="text-neutral-700">&#9675;</span>
            )}
          </div>
          <span className={i <= currentStep ? "text-white" : "text-neutral-600"}>
            {step}
            {i === 2 && sceneCount > 0 ? ` (${sceneCount} scenes)` : ""}
            {i === 3 && slideCount > 0 ? ` (${slideCount} slides)` : ""}
          </span>
        </div>
      ))}

      {latestStatus?.message && (
        <p className="text-sm text-neutral-500 mt-4">{latestStatus.message}</p>
      )}

      {hasError && (
        <p className="text-red-400 text-sm mt-4">
          {events.find((e) => e.step === "error")?.message}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: SlideGrid component**

```typescript
// src/components/SlideGrid.tsx
"use client";

export default function SlideGrid({
  previews,
  caption,
  downloadUrl,
  onReset,
}: {
  previews: string[];
  caption: string;
  downloadUrl: string | null;
  onReset: () => void;
}) {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-4 gap-3">
        {previews.map((src, i) => (
          <img
            key={i}
            src={src}
            alt={`Slide ${i + 1}`}
            className="rounded-lg border border-neutral-800 w-full aspect-[4/5] object-cover"
          />
        ))}
      </div>

      {caption && (
        <div>
          <h3 className="text-sm text-neutral-400 mb-2">Caption</h3>
          <pre className="whitespace-pre-wrap text-sm text-neutral-300 bg-neutral-900 p-4 rounded-lg max-h-48 overflow-y-auto">
            {caption}
          </pre>
        </div>
      )}

      <div className="flex gap-3">
        {downloadUrl && (
          <a
            href={downloadUrl}
            download="carousel.zip"
            className="flex-1 py-3 bg-white text-black font-semibold rounded-lg text-center hover:bg-neutral-200"
          >
            Download ZIP
          </a>
        )}
        <button
          onClick={onReset}
          className="flex-1 py-3 border border-neutral-700 text-white font-semibold rounded-lg hover:bg-neutral-900"
        >
          Generate Another
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add src/components/ && git commit -m "feat: all frontend components"
```

---

## Task 14: Integration Test + Deploy

- [ ] **Step 1: Add environment variables to .env.local**

Fill in real API keys:
```
ANTHROPIC_API_KEY=sk-ant-...
FAL_KEY=...
TAVILY_API_KEY=tvly-...
NEXT_PUBLIC_CONVEX_URL=https://...convex.cloud
```

- [ ] **Step 2: Run locally**

```bash
npx convex dev &
npm run dev
```

Open `http://localhost:3000`. Test the full flow:
1. Paste a URL (e.g., gymshark.com) → brand setup
2. Type a topic → select template → generate
3. Watch progress stream
4. Review slides → download ZIP

- [ ] **Step 3: Fix any issues found during testing**

Common issues to watch for:
- Font registration path (may need absolute path on server vs relative in dev)
- Convex HTTP client URL configuration
- SSE stream parsing edge cases
- Image buffer handling between fal.ai → compositor

- [ ] **Step 4: Push to Railway**

```bash
git push
```

In Railway dashboard:
1. Create new project from GitHub repo
2. Add environment variables (ANTHROPIC_API_KEY, FAL_KEY, TAVILY_API_KEY, NEXT_PUBLIC_CONVEX_URL)
3. Deploy

- [ ] **Step 5: Test in production**

Open the Railway URL. Run through the same flow as local testing.

- [ ] **Step 6: Final commit**

```bash
git add -A && git commit -m "feat: integration fixes + production ready"
```
