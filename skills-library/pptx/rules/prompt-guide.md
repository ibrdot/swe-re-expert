# Prompt Guide

How to write the prompt for each slide. Good prompts are the key to good images.

---

## Seven-Section Structure

Organize every slide prompt in this order — no section can be omitted:

```
SUBJECT
STYLE
COLOR        ← write when establishing a new visual language; omit when inheriting (handled by --ref)
COMPOSITION  ← the core: first describe "what visual elements to render", then where text goes
TEXT TO RENDER
QUALITY      ← must include language/rendering instruction
NEGATIVE
```

**COMPOSITION is the key to unlocking GPT Image 2's capabilities.**
It's not a layout description of "where to put text" — it tells the model **what visual content to render**:
- Data comparison slide → describe bar chart groupings, colors, proportions
- Process slide → describe node shapes, arrow directions, node labels
- Concept slide → describe illustration scene, icons, visual metaphor
- Pure-text conclusion slide → only then describe headline and bullet positions

Before writing, check **visual-types.md** to decide which visual form to use.

---

## Full Prompt Skeleton

Use this skeleton as a checklist — ensure every section is complete.

### Slide 1 skeleton (requires COLOR section)

```
SUBJECT: [One sentence: slide type + purpose of this slide, e.g. "Technical cover slide for an AI presentation"]

STYLE: [Style positioning, 1 sentence] [Reference vibe, 1 sentence, optional] [Explicit exclusion, 1 sentence]

COLOR:
- Background: [color description] ([hex]) [optional texture]
- Primary text: [description] ([hex])
- Secondary text: [description] ([hex])
- Accent: [role] ([hex]) — [usage constraint]

COMPOSITION:
- [Decide visual form first — see visual-types.md]
- [Describe the primary visual elements: shapes, colors, proportions, how data is visualized]
- [Describe how text supports the visual: labels, headlines, captions and their positions]

TEXT TO RENDER (verbatim — do not paraphrase, do not translate):
- [ELEMENT LABEL]: "[Full text, copy exactly as-is, no omissions or rewrites]"
- [ELEMENT LABEL]: "[Full text]"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.
Match the script and language of the TEXT TO RENDER section exactly.

NEGATIVE: [Elements to exclude, comma-separated, e.g. "No 3D objects, no photographs, no neon glow"]
```

### Follow-up slide skeleton (omit COLOR, use edit --ref)

```
SUBJECT: [Slide type + purpose of this slide]

STYLE: [Decide based on this slide's relationship to the reference —
  Continuing the exact style → "Keep the EXACT same visual language, color palette ([key hex values]), typography as the reference. Only change the content."
  Same style but needs more breathing room → "Same visual language as the reference, but more spacious — generous whitespace, lighter information density."
  Intentional visual contrast → re-describe the style, or use gen instead of edit]

COMPOSITION:
- [Decide visual form first — see visual-types.md]
- [Describe the primary visual elements: shapes, colors, proportions, how data is visualized]
- [Describe how text supports the visual: labels, headlines, captions and their positions]

TEXT TO RENDER (verbatim — do not paraphrase, do not translate):
- [ELEMENT LABEL]: "[Full text]"
- [ELEMENT LABEL]: "[Full text]"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.
Match the script and language of the TEXT TO RENDER section exactly.

NEGATIVE: [Elements to exclude]
```

---

## Language Handling

GPT Image 2 follows the language of the TEXT TO RENDER section. If you're rendering non-Latin scripts (CJK, Arabic, Cyrillic, Devanagari, etc.), add a reinforcing line to QUALITY:

```
[Script name] characters rendered crisply, no deformation or stroke distortion.
```

Examples:
- Chinese deck: `Simplified Chinese characters rendered crisply, no deformation.`
- Arabic deck: `Arabic script rendered crisply, correct RTL direction, no stroke distortion.`
- Japanese deck: `Japanese characters (Kanji, Hiragana, Katakana) rendered crisply, no deformation.`

If English technical terms should stay in English (e.g. API, KPI, brand names), list them explicitly:
```
Technical terms (API, KPI, GPT-5.5) may stay in English.
```

---

## Font Description Rules

**Describe the visual appearance, not the font name.** Image models don't recognize font names, only visual descriptions.

| ❌ Wrong | ✅ Right |
|---------|---------|
| "Bebas Neue" | "bold condensed geometric sans-serif with tight letter-spacing" |
| "Playfair Display" | "high-contrast display serif with hairline horizontals and thick verticals" |
| "Noto Sans Bold" | "bold geometric sans-serif with uniform stroke width, slightly condensed" |
| "Noto Serif" | "high-contrast serif with elegant thin horizontals and thick verticals" |
| "Inter Regular" | "clean neutral sans-serif with consistent stroke width and open apertures" |

---

## Slide 1: Full Prompt Example (cover)

Slide 1's STYLE + COLOR defines the visual master for the whole deck — the more detailed, the better the consistency across following slides.

```
SUBJECT: Technical cover slide for an engineering presentation about AI Agent capabilities.

STYLE: Blueprint engineering aesthetic — precise, analytical, grid-based. Clean like
technical documentation, premium like a keynote. No decorative noise.

COLOR:
- Background: off-white blueprint paper (#FAF8F5) with very subtle light gray grid
  overlay (#E5E5E5 lines at ~40px spacing)
- Primary text: deep slate (#334155)
- Accent: engineering blue (#2563EB) — used for horizontal rule and label
- Secondary: navy (#1E3A5F) — used for subtitle only

COMPOSITION:
- Large ghost watermark "2026" in very light gray (#EBEBEB), spanning ~40% canvas
  height, positioned center-right as background decoration
- Bold headline overlaid on watermark, left-aligned, deep slate, 2 lines max
- Thin 2px engineering-blue horizontal rule below headline
- Subtitle directly below rule, navy, lighter weight than headline
- Small-caps label bottom-right corner

TEXT TO RENDER (verbatim — do not paraphrase, do not translate):
- WATERMARK: "2026"
- HEADLINE: "5 Core Capabilities of AI Agents"
- SUBTITLE: "Reshaping the Fundamentals of Software Engineering"
- LABEL: "ENGINEERING TEAM · 2026"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.
Match the script and language of the TEXT TO RENDER section exactly.

NEGATIVE: No 3D objects, no glassmorphism, no neon glow, no photographs,
no decorative icons, no drop shadows on text, no gradients on text.
```

---

## Follow-up Slide: Horizontal Bar Chart (edit mode)

Data comparison slide — COMPOSITION focuses on chart structure; text is labels only.

```
SUBJECT: Visual benchmark comparison slide — four AI models compared on three key
metrics using horizontal bar charts.

STYLE: Keep the EXACT same visual language, color palette (#0D1117 background,
#E6EDF3 text, #58A6FF accent) as the reference. But this slide is VISUAL-FIRST:
the bar charts are the main content, text is labels only.

COMPOSITION:
- Headline at top, bold near-white
- Below: three grouped horizontal bar chart sections, one per metric
- Each section: metric name as section label on the left, then four horizontal bars
  (one per model) stacked vertically
- Each bar: model name label left, colored filled bar proportional to the value,
  value number at bar end
- Bar colors: GPT-5.5 electric blue (#58A6FF), Claude Opus 4.7 purple (#A78BFA),
  Gemini teal (#34D399), DeepSeek orange (#FB923C)
- Section 1 bars — Terminal-Bench (higher=better):
  GPT-5.5 82.7%, Opus 4.7 69.4%, Gemini 68.5%, DeepSeek 67.9%
- Section 2 bars — SWE-Bench Pro (higher=better):
  Opus 4.7 64.3%, GPT-5.5 58.6%, DeepSeek 55.4%, Gemini 51.0%
- Section 3 bars — Hallucination Rate (lower=better, shorter bar = better):
  Opus 4.7 36%, GPT-5.5 86%, Gemini 88%, DeepSeek 72%
- Section 3 bars colored red (#F78166) to signal danger
- Small legend top-right showing model color mapping

TEXT TO RENDER (verbatim — do not paraphrase, do not translate):
- HEADLINE: "Core Benchmark Comparison"
- SECTION 1 LABEL: "Agentic Coding  Terminal-Bench 2.0"
- SECTION 2 LABEL: "Real Code Fixes  SWE-Bench Pro"
- SECTION 3 LABEL: "Hallucination Rate  Lower is Better"
- BAR LABELS: "GPT-5.5", "Claude Opus 4.7", "Gemini 3.1 Pro", "DeepSeek V4"
- VALUES: "82.7%", "69.4%", "68.5%", "67.9%", "64.3%", "58.6%", "55.4%", "51.0%",
  "36%", "86%", "88%", "72%"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.

NEGATIVE: No plain text tables, no 2×2 text grid. This must be a real bar chart
visualization. No photographs, no neon glow.
```

---

## Follow-up Slide: Isometric Illustration Hub-Spoke (edit mode)

Concept visualization — the illustration is the protagonist, text is annotation only. COMPOSITION describes scene elements, not text layout.

```
SUBJECT: Conceptual illustration slide — the idea that you need a specialized team
of AI models, each expert at different tasks.

STYLE: Keep the EXACT same dark color palette (#0D1117 background, #E6EDF3 text,
#58A6FF accent) as the reference. This slide is ILLUSTRATION-FIRST — the visual
metaphor carries the message.

COMPOSITION:
- Headline at top, bold near-white, left-aligned
- Below: a rich isometric-style illustration showing four distinct specialist
  stations arranged in a circle
- Each station represents one AI model with a visual icon that matches its specialty:
  Station 1 (Opus 4.7, purple tones): code editor screen with complex code,
    surgical precision tools — represents deep coding expertise
  Station 2 (GPT-5.5, blue tones): terminal with rapidly running commands,
    shell scripts — represents agentic automation
  Station 3 (Gemini, teal tones): camera/video frame and document stacks
    — represents multimodal
  Station 4 (DeepSeek, orange tones): speed gauge and stack of coins
    — represents cost efficiency
- A central hub with glowing connecting lines radiating to all four stations
- Each station has a small label card below it
- Caption text at the bottom

TEXT TO RENDER (verbatim — do not paraphrase, do not translate):
- HEADLINE: "Build a Team, Don't Bet on One Model"
- STATION 1 LABEL: "Opus 4.7  Long-horizon code"
- STATION 2 LABEL: "GPT-5.5  Agentic shell"
- STATION 3 LABEL: "Gemini 3.1  Multimodal + search"
- STATION 4 LABEL: "DeepSeek V4-Flash  High-throughput batch"
- CENTER LABEL: "Your Tasks"
- CAPTION: "The jagged frontier won't converge anytime soon"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.

NEGATIVE: No plain hub-spoke line diagram. Must have real illustrated visual
elements, not just circles and lines. No photographs, no neon.
```

---

## Follow-up Slide: Closing (edit mode)

```
SUBJECT: Closing slide — memorable one-liner with supporting text.

STYLE: Keep the EXACT same visual language, color palette, typography, and grid
background as the reference. This slide should feel more spacious than content pages.

COMPOSITION:
- Centered layout with generous whitespace
- Large bold headline centered, takes ~50% canvas width
- Thin 2px accent-color horizontal rule below headline
- Subtitle below rule, centered, lighter weight
- Body text below subtitle, centered, small, one line
- Small-caps footer at bottom-center

TEXT TO RENDER (verbatim):
- HEADLINE: "Agents Are Not Tools"
- SUBTITLE: "They're Your First Digital Colleague"
- BODY: "Plan · Remember · Use Tools · Collaborate · Self-correct"
- FOOTER: "ENGINEERING TEAM · 2026"

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.

NEGATIVE: No 3D, no photographs, no neon, no decorative clutter.
Closing slide must breathe — generous whitespace is essential.
```

---

## Fine-Tuning an Existing Slide (change headline / update numbers)

```
SUBJECT: Revised version of slide 3 — only the headline changes.

STYLE: Keep the EXACT same visual language, color palette, typography, layout,
and all decorative elements as the reference. Do NOT change anything except
the specified text.

COMPOSITION: Identical to reference — do not alter any layout element.

TEXT TO RENDER:
- REPLACE the main headline with: "New headline text here"
- All other text remains exactly as in the reference

QUALITY: Crisp typography, no misspellings, exact text as written above.
Render all characters crisply — no distortion, no substitution, no blurring.
Match the script and language of the TEXT TO RENDER section exactly.

NEGATIVE: [Same NEGATIVE content as the slide being refined]
```

---

## Common Errors & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Text rewritten by model | Missing "verbatim" emphasis | Add "do not paraphrase, do not translate" to TEXT TO RENDER |
| Wrong script/language rendered | No language guidance in QUALITY | Add script-specific rendering instruction to QUALITY |
| edit didn't change the specified content | Instruction not strong enough | Use uppercase "REPLACE the main title with: 'XX'" |
| Follow-up slide style drifts | STYLE section not explicit enough | Write "Keep the EXACT same visual language" + list key hex values |
| Blurry text | quality parameter too low | `--quality high` + add "crisp typography" to QUALITY |
