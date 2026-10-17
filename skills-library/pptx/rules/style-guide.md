# Style Guide

How to judge visual style from content, and write it into the STYLE + COLOR sections of your prompt.

---

## Core Principle

**Read the content, infer the vibe — don't pick from a menu.**

Every deck should have its own visual language. The 14 samples in `style_refs/` are there to teach you how to write style descriptions, not to be copied directly.

---

## How to Judge Style

**Step 1: Read the content and ask three questions**

1. What's the tone? Serious / playful / technical / emotional / formal / nerdy
2. Who's the audience? Executives / engineers / consumers / students / investors
3. Where will it be shown? Large-screen keynote / reading report / social share / print

**Step 2: Derive the visual language from your answers**

| Dimension | Directions |
|-----------|-----------|
| Light/Dark | Light base (crisp, professional) / Dark base (cool, premium) |
| Color temperature | Warm (approachable, lifestyle) / Cool (rational, technical) / Neutral (general purpose) |
| Layout density | Generous whitespace (high-end feel) / Dense information (expert feel) |
| Type character | Serif (elegant, traditional) / Sans-serif (modern, clean) / Script (warm, creative) |
| Material | Paper / grid / flat / hand-drawn / dark gradient |

---

## STYLE + COLOR Block Template

After deciding on the style, output this structure (goes into the STYLE + COLOR sections of the slide-1 prompt):

```
STYLE: [Style positioning, 1 sentence, e.g. "Ultra-clean minimal business"]
[Reference vibe, 1 sentence, e.g. "Think McKinsey meets Apple Keynote" — optional]
[Explicitly exclude one thing, 1 sentence, e.g. "No decoration — the data is the design"]

COLOR:
- Background: [color description] ([hex]) [optional texture, e.g. "with subtle #E5E5E5 grid overlay"]
- Primary text: [description] ([hex])
- Secondary text: [description] ([hex])
- Accent: [role] ([hex]) — [usage constraint, e.g. "used sparingly, one element per slide only"]
- [Secondary accent — only add this line for multi-brand-color scenarios] ([hex])
```

**Writing tips**:
- STYLE describes **feel and atmosphere**, not specific elements (those go in COMPOSITION)
- Accent must include a constraint; without it, the model scatters the accent color everywhere
- Omit any color role you don't need — don't pad the list

---

## Style Judgment Examples

### Example 1: Q1 financial review, executive audience

**Analysis**: Serious, formal, data-driven, audience has no time for noise

**Visual language**:
- Minimal white base, generous whitespace
- Deep gray / near-black text, single accent color
- Bold wide sans-serif headline, light serif body
- No decorative elements, key numbers at large scale

**STYLE + COLOR**:
```
STYLE: Ultra-clean minimal business. Maximum whitespace, typography-first.
Think McKinsey report meets Apple Keynote. No decoration — the data is the design.

COLOR:
- Background: pure white (#FFFFFF)
- Primary text: near-black (#111111)
- Secondary text: medium gray (#6B7280)
- Accent: forest green (#065F46) — used sparingly, one highlight element per slide only
```

---

### Example 2: AI architecture tech talk, engineer audience

**Analysis**: Technical, structured, needs precision, engineers prefer clean over flashy

**Visual language**:
- Light base with grid texture, engineering blueprint feel
- Blue-family accent, deep gray text
- Condensed bold sans-serif headline, monospace or light serif body
- Wireframe diagrams and flow boxes are welcome

**STYLE + COLOR**:
```
STYLE: Blueprint engineering aesthetic. Precise, grid-based, analytical.
Like technical documentation meets premium keynote. Clean, no noise.

COLOR:
- Background: blueprint off-white (#FAF8F5) with subtle #E5E5E5 grid overlay
- Primary text: deep slate (#334155)
- Accent: engineering blue (#2563EB)
- Secondary: navy (#1E3A5F)
```

---

### Example 3: Startup pitch deck, investor audience

**Analysis**: Needs professional credibility + personality, shows taste, moderate information density

**Visual language**:
- Dark base or off-white base — either works
- High contrast, heavy serif large headline
- Minimal decoration, data as large-scale visual anchor

**STYLE + COLOR**:
```
STYLE: Premium editorial. Bold confident typography, magazine-grade hierarchy.
High contrast, asymmetric composition, generous negative space. No corporate stiffness.

COLOR:
- Background: near-black (#0F0F0F)
- Primary text: pure white (#FFFFFF)
- Accent: warm gold (#D4A017) — used only for 1–2 emphasis elements
- Body text: light gray (#A3A3A3)
```

---

### Example 4: Children's coding course, student / parent audience

**Analysis**: Light, friendly, approachable, visually lively but not chaotic

**Visual language**:
- Warm base, saturated colors
- Rounded, hand-written-feel type
- Illustrated icons, hand-drawn arrows

**STYLE + COLOR**:
```
STYLE: Flat illustration with hand-drawn warmth. Rounded, approachable,
educational. Every element feels like it was drawn by an enthusiastic teacher.

COLOR:
- Background: warm cream (#FFF8F0)
- Primary text: deep warm brown (#2D1B10)
- Accent 1: coral orange (#E8603C)
- Accent 2: sky blue (#4BBDDF)
- Accent 3: leaf green (#5BAD6F)
```

---

## gen vs edit Decision

- `gen` — generate from scratch, establishes visual language (typically for the first slide, or intentional style breaks)
- `edit --ref N` — build on slide N as reference, automatically inherits its visual language

**Which ref to use**: choose the slide that best represents the visual effect you want to inherit — often the first slide of the same visual block, not necessarily slide 1.

**Keep edit chains under 3 layers**: chained edits accumulate drift; beyond 3, go back to `gen` and regenerate.

For other situations (style switches, user-provided reference images, fine-tuning a single slide…) use your judgment.

---

## How to Use style_refs/

When you know the style you want but struggle to describe it, open the relevant file:

```
style_refs/minimal.md               ← Minimal keynote (Apple / Zen)
style_refs/minimalist.md            ← Minimal business (McKinsey / Stripe / Linear)
style_refs/blueprint.md             ← Technical engineering blueprint
style_refs/corporate.md             ← Business / investor style
style_refs/dark-atmospheric.md      ← Dark tech style
style_refs/sketch-notes.md          ← Hand-drawn educational style
style_refs/editorial.md             ← Magazine layout style
style_refs/bold-editorial.md        ← Bold editorial (high-contrast, heavy type)
style_refs/editorial-infographic.md ← Infographic magazine style
style_refs/watercolor.md            ← Watercolor lifestyle style
style_refs/chinese-elegance.md      ← Chinese aesthetic style
style_refs/glassmorphism.md         ← Glassmorphism style
style_refs/notion.md                ← Notion document style (content-dense)
style_refs/scientific.md            ← Scientific paper style
```

**Use them to learn**: how to define hex values, how to describe type character, how to write Do/Don't.

**Don't**: copy file contents directly into a prompt — every deck should have its own colors and personality.
