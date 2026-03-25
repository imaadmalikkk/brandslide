---
name: template
description: Create, manage, and preview carousel visual templates. Use /template inspire to create templates from Instagram posts or screenshots you see online.
---

# /template — Template Management

Templates define the complete visual recipe for a carousel: where text sits, how the gradient works, where the logo goes, and what kind of scenes to generate. Templates are global (any brand can use them).

## Sub-commands

Parse the user's message to determine which sub-command:
- `/template list` or `/template` → list
- `/template inspire` → inspire
- `/template create "name"` → create
- `/template preview "name" [brand]` → preview
- `/template delete "name"` → delete

---

## /template list

List all available templates from `shared/templates/`.

```python
import sys; sys.path.insert(0, 'shared')
from core import list_templates
for t in list_templates():
    print(f"  {t['name']}: {t['description']}")
```

Present as a clean list with name and one-line description. Indicate which are built-in vs user-created (built-in templates have `"source": {"type": "original"}`).

---

## /template inspire

**The core experience.** Create a template from something the user saw online.

### Step 1: Gather inspiration

Ask the user for their inspiration. Accept any combination of:
- **Screenshot/image path** — read the image directly (Claude has vision)
- **Instagram URL** — browse it with browser tools, screenshot the carousel slides
- **Text description** — "like Freshly Grounded's style but cleaner" or "text-heavy, no scene, stacked typography"

### Step 2: Analyze and decompose

Look at the inspiration and identify these template parameters:

| What to identify | Maps to |
|-----------------|---------|
| Where is the text? (top, center, bottom) | `text_position` |
| Is text centered or left-aligned? | `text_align` |
| Is there a gradient? What direction? | `gradient.direction` |
| How strong is the gradient/overlay? | `gradient.max_alpha_override` |
| Where is the logo/branding? | `logo.position` |
| Is there a scene/photo, or just solid color? | `scene_mode` |
| Is the text very large or normal? | `font_overrides.headline_size` |
| Are there special elements (dividers, numbers)? | `elements` |
| What kind of scenes work best? | `scene_style_overrides` |

### Step 3: Present capability assessment

Show the user what CAN and CAN'T be reproduced in Pillow:

```
## What I can reproduce:
- Text centered on dark overlay ✓
- Bottom-up gradient at high opacity ✓
- Logo bottom-right ✓
- Bold condensed ALL-CAPS headline ✓
- Accent word coloring ✓

## What I can't reproduce in Pillow:
- [list anything from the inspiration that Pillow can't do]

## Closest alternatives:
- [for each limitation, suggest what we CAN do instead]
```

**Wait for user approval before building.**

### Step 4: Build the template

Create the template JSON file at `shared/templates/<name>.json`.

Use the existing template files as structural references:
```
shared/templates/cinematic-story.json   (bottom text, scene-heavy)
shared/templates/bold-centered.json     (centered text, full overlay)
shared/templates/editorial-clean.json   (top text, top-down gradient)
shared/templates/text-forward.json      (no scene, solid background)
```

The template must define layouts for all 3 slide types: hook, content, closer.

Set the source to record the inspiration:
```json
"source": {
    "type": "inspiration",
    "reference": "[URL or description of what inspired this]"
}
```

### Step 5: Preview

Generate a test slide using the template with any available brand. Composite at full resolution so the user can evaluate quality.

Use test content:
```python
test_hook = {
    "type": "hook",
    "headline": ["THIS IS A", "TEST HEADLINE"],
    "accent_word": "TEST"
}
test_content = {
    "type": "content",
    "headline": ["CONTENT", "SLIDE"],
    "accent_word": "CONTENT",
    "subtext_amber": "THIS IS THE PRIMARY SUBTEXT LINE",
    "subtext_white": "THIS IS THE SECONDARY SUBTEXT LINE"
}
```

Show both hook and content test slides. Ask user to approve or adjust.

### Step 6: Name and save

Ask the user to name the template (or suggest one based on the style). Confirm it's saved.

Announce: "Template **[name]** saved. Use it with `/generate [brand] [topic] --template [name]`."

---

## /template create "name"

Interactive creation without inspiration. Walk through each parameter:

1. **Scene mode:** Full-bleed scene, no scene (solid color), or split?
2. **Text position:** Bottom, top, or centered?
3. **Text alignment:** Centered or left-aligned?
4. **Gradient:** Bottom-up, top-down, full overlay, or none?
5. **Gradient strength:** Light (180), medium (220), or heavy (255)?
6. **Logo placement:** Bottom-right, top-right, center-divider, or none?
7. **Font size:** Normal (110) or larger (130-140)?
8. **Scene guidance:** What kind of scenes work best with this layout?

After each choice, build the template JSON. At the end, generate a preview slide.

---

## /template preview "name" [brand]

Composite a quick test: one hook slide + one content slide using the named template with the specified brand (or Gymshark if no brand specified).

Use existing scenes from the brand's `scenes/` folder or `output/*/scenes/` folders. If none exist, generate one via NanoBanana.

---

## /template delete "name"

Delete a user-created template. Built-in templates (cinematic-story, bold-centered, editorial-clean, text-forward) cannot be deleted.

```python
import os
path = f"shared/templates/{name}.json"
# Check if built-in
built_ins = ["cinematic-story", "bold-centered", "editorial-clean", "text-forward"]
if name in built_ins:
    print("Cannot delete built-in template.")
else:
    os.remove(path)
    print(f"Deleted template: {name}")
```
