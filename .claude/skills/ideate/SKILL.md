---
name: ideate
description: Brainstorm carousel ideas for a brand, checking existing content for dedup and researching trending topics
---

# /ideate — Content Ideation

You are brainstorming carousel ideas for a specific brand. The goal is to produce 5 ranked ideas the user can choose from.

## Inputs

- **Brand name** (required) — must match a folder in `brands/`
- **Pillar filter** (optional) — limit ideas to a specific content pillar

Parse from the user's message: `/ideate gymshark` or `/ideate gymshark fitness`

## Flow

### 1. Load Brand Context

Read the brand's CLAUDE.md to understand:
- Content pillars and topics
- Target audience
- Brand voice and tone
- Conversion paths (which product each pillar funnels to)
- Any seasonal content opportunities

```
brands/<brand>/CLAUDE.md
```

### 2. Check Existing Content

Scan the brand's output folder to see what carousels already exist:
```
brands/<brand>/output/
```

List existing carousel slugs. These are topics to avoid duplicating (unless the user wants a "part 2" or fresh angle).

### 3. Research Trending Topics

Run 3-5 web searches relevant to the brand's niche:
- "[niche] trending topics [current month] [current year]"
- "[niche] common questions reddit"
- "[niche] Instagram carousel ideas"
- "[niche] myths and misconceptions"
- "[specific pillar] beginner mistakes" (if pillar filter provided)

Look for: questions people are asking, misconceptions being shared, trending debates, seasonal relevance.

### 4. Generate Ideas

Produce exactly 5 carousel ideas. For each:

```
### [Number]. [Carousel Title]

**Pillar:** [Which content pillar]
**Why it performs:** [1-2 sentences on why this would get saves/shares]
**Conversion path:** [Which product/programme this funnels to]
**Slide count:** [Estimated number of slides, 5-10]
**Already covered?** [Yes/No — if similar content exists in output/]
**Hook angle:** [The specific hook slide headline idea]
```

### 5. Ranking

Rank ideas by estimated engagement potential. Consider:
- **Saves** — educational content people want to reference later
- **Shares** — "I didn't know this" surprise factor, relatable struggles
- **Follows** — content that establishes authority and makes people want more
- **Dedup** — penalize ideas too close to existing carousels

### 6. Present and Wait

Present all 5 ideas ranked. Ask the user to pick 1-3 to produce.

When the user picks, announce: "Use `/generate <brand> <topic>` to produce each carousel, or I can start generating now."

If the user says to start generating, proceed directly into the /generate flow for each selected idea.
