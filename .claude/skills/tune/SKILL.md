---
name: tune
description: Rapidly iterate on brand.json visual parameters with side-by-side comparison slides at preview resolution
---

# /tune — Brand Visual Tuning

You are helping the user fine-tune their brand's visual parameters by generating side-by-side comparison slides. This is an iterative loop with fast visual feedback.

## Inputs

- **Brand name** (required) — must match a folder in `brands/`

Parse from the user's message: `/tune gymshark` or `/tune <brand>`

## Step 1: Load Brand and Find a Test Scene

1. Load the brand's `brand.json`
2. Find a test scene to composite against:
   - Check `brands/<brand>/scenes/` for bundled test scenes
   - Check `brands/<brand>/output/*/scenes/` for existing carousel scenes
   - If no scenes exist, generate one via NanoBanana using the brand's scene_style config at 1080px resolution (fast)
3. Pick the first available scene

## Step 2: Present Current State

Composite one test slide at 1080px resolution using the current brand.json values. Show it to the user.

Present the tunable parameter categories:
```
What would you like to tune?

1. Gradient — bleed distance, max alpha, target color
2. Typography — headline size, subtext size, line spacing
3. Margins — bottom, top, side margins
4. Logo — size, opacity, padding
5. Colors — accent, subtext primary/secondary, divider
6. Advanced — scrim opacity, text shadow
```

Ask the user which category (or specific parameter) they want to adjust.

## Step 3: Generate Side-by-Side Variations

Based on the user's choice, generate **3 variations** of the same test slide, each with a different value for the parameter being tuned.

### Variation Strategy by Parameter

**Gradient bleed:**
- Variation A: current value - 100px
- Variation B: current value (baseline)
- Variation C: current value + 100px

**Gradient max alpha:**
- Variation A: 180 (lighter, more scene visible)
- Variation B: 220 (moderate)
- Variation C: 255 (solid, maximum legibility)

**Headline font size:**
- Variation A: current - 15px
- Variation B: current (baseline)
- Variation C: current + 15px

**Subtext font size:**
- Variation A: current - 5px
- Variation B: current (baseline)
- Variation C: current + 5px

**Colors:** Show 3 color options. For accent colors, offer:
- Variation A: current color
- Variation B: a warmer alternative
- Variation C: a cooler alternative

For other parameters, follow the same pattern: one step down, current, one step up.

### Compositing

All variations are composited at **1080px width** (not 4K) for speed. Use a content-type slide with test text:

```python
test_slide = {
    "type": "content",
    "headline": ["THIS IS A", "TEST HEADLINE"],
    "accent_word": "TEST",
    "subtext_amber": "THIS IS THE PRIMARY SUBTEXT LINE FOR TESTING",
    "subtext_white": "THIS IS THE SECONDARY SUBTEXT LINE FOR COMPARISON"
}
```

Save variations to a temp directory:
```
/tmp/brandslide-tune/
├── A.png
├── B.png
└── C.png
```

## Step 4: Present Comparison

Show all 3 variations to the user. Label them clearly:
- **A:** [parameter] = [value]
- **B:** [parameter] = [value] (current)
- **C:** [parameter] = [value]

Ask the user to pick the winner, or request a custom value.

## Step 5: Apply and Iterate

1. Update brand.json with the chosen value
2. Ask if the user wants to tune another parameter
3. If yes, return to Step 2 (show updated baseline, pick next parameter)
4. If done, offer to recomposite at full 4K resolution with the final values:
   - Composite one hook + one content + one closer as final verification
   - Save to `brands/<brand>/scenes/tune-test/`

## Notes

- Always composite at 1080px during tuning for speed
- Label every variation with the exact parameter value so the user can see what changed
- When the user picks a winner, confirm the change before writing to brand.json
- Keep a mental note of all changes made in the session and summarize at the end
- The test text should be neutral and work for any brand (don't use brand-specific content)
