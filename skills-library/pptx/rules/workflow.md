# Workflow

The complete execution flow from user input to final PPTX.

---

## Overview

```
Collect input → Output deck_spec (user confirms) → Build all prompts → Generate images in small batches → Pack
```

---

## Phase 1: Collect Input

Information to confirm:

| Field | Description | Default |
|-------|-------------|---------|
| Content | User pastes text or provides a file | — |
| Slide count | How many slides | Determined by content volume, typically 5–10 |
| Deck name | Short English name, e.g. `q1-review` | — |
| Audience | Executives / engineers / consumers… | general |
| Size | WxH (both must be multiples of 16) | 2048x1152 |

Do not ask the user "what style do you want" — infer it from the content (see style-guide.md).

---

## Phase 2: Output Full deck_spec ⚠️ Must be confirmed by user

**Before calling any API**, finalize all content for every slide and output it in Markdown for the user to confirm.

### deck_spec skeleton

```markdown
## Style Decisions
- Style: [style name]
- Rationale: [1 sentence, inferred from content/audience]
- Color palette: base [hex] / primary text [hex] / accent [hex] [/ secondary hex]
- Type character: [headline description] / [body description]

---

### Slide 1 — [type]
Visual design:
  - Visual elements: [description of all visual content on this slide — primary visual (chart/illustration/graphic), background treatment, decorative elements, color emphasis, material, etc. — open description]
  - Layout: [position and proportion relationship between visual content and text]
Text content:
- [ELEMENT LABEL]: "[full text]"

### Slide N — [type]
Visual design:
  - Visual elements: [...]
  - Layout: [...]
Text content:
- [ELEMENT LABEL]: "[full text]"
```

### ⛔ No placeholders

| Forbidden ❌ | Write instead ✅ |
|-------------|-----------------|
| "3 bullet points" | Write out all 3 bullets in full |
| "data chart" | Specify the data: GPT-5.5 82.7%, Opus 4.7 69.4%… |
| "see content" | Put the content inline |
| "core advantages overview" | "30% cost reduction, 2× efficiency, zero learning curve" |

Reason: GPT Image 2 renders text verbatim — placeholders that make it into a prompt will appear literally on the slide.

---

### Full deck_spec example (8 slides, AI model selection theme)

```markdown
## Style Decisions
- Style: Dark Technical Editorial
- Rationale: AI builder audience, benchmark-data-heavy; dark base makes numbers pop, precision and weight are essential
- Color palette: base #0D1117 / primary text #E6EDF3 / accent blue #58A6FF / positive green #3FB950 / warning red #F78166 / muted gray #8B949E
- Type character: bold condensed sans-serif headline / oversized numbers for emphasis / lightweight sans-serif body

---

### Slide 1 — cover
Visual design:
  - Visual elements: pure typography-led layout, deep background with no decoration, a single electric-blue thin line below the headline as visual divider
  - Layout: left-aligned large headline occupies upper half, thin line separator, subtitle (four model names) immediately below, one line of body text, date annotation bottom-right
Text content:
- HEADLINE: "4 Models, 12 Task Types"
- SUBHEAD: "GPT-5.5 · Opus 4.7 · Gemini 3.1 · DeepSeek V4"
- BODY: "Which model for which scenario — and the pitfalls you need to avoid"
- DATE: "2026 · 04"

### Slide 2 — dual card (pitfall scenarios)
Visual design:
  - Visual elements: two dark cards (#161B22 base), each with a 3px electric-blue vertical color bar on the left; core numbers in oversized type rendered in warning red for visual impact; italic conclusion line at card bottom in muted gray as de-emphasized text
  - Layout: two equal-width cards side by side; inside each card: title at top, large-scale data in middle, conclusion at bottom; full-width headline at top
Text content:
- HEADLINE: "Two Common Pitfalls First"
- LEFT TITLE: "Opus Upgrade: Long Docs Actually Regressed"
- LEFT DATA: "1M needle-in-haystack: 4.6 → 91.9%, 4.7 → 59.2%"
- LEFT CONCLUSION: "Anthropic traded retrieval capacity for agentic reasoning ability"
- RIGHT TITLE: "GPT-5.5 Computer Use: Not Available via API"
- RIGHT DATA: "OSWorld 78.7% only works in macOS Codex desktop app"
- RIGHT CONCLUSION: "Responses API still at GPT-5.4 level; EU/UK users cannot access"

### Slide 3 — horizontal bar chart (benchmark comparison)
Visual design:
  - Visual elements: three groups of horizontal bar charts, one group per metric; four models in distinct colors per group (blue/purple/teal/orange); hallucination rate group bars all changed to warning red, implying "shorter = better"; color legend top-right; value numbers at bar ends
  - Layout: headline at top, three chart groups stacked vertically filling the main body, metric label on the left of each group
Text content:
- HEADLINE: "Core Benchmark Comparison Across Four Models"
- SECTION 1: "Agentic Coding  Terminal-Bench 2.0"
- SECTION 2: "Real Code Fixes  SWE-Bench Pro"
- SECTION 3: "Hallucination Rate  Lower is Better"
- BAR LABELS: "GPT-5.5", "Claude Opus 4.7", "Gemini 3.1 Pro", "DeepSeek V4"
- VALUES: "82.7%", "69.4%", "68.5%", "67.9%", "64.3%", "58.6%", "55.4%", "51.0%", "36%", "86%", "88%", "72%"

### Slide 4 — card grid (integration pitfalls)
Visual design:
  - Visual elements: 6 dark cards (3 columns × 2 rows), each with a 2px electric-blue top border as accent; warning numbers (prices, error codes) inside cards highlighted in red
  - Layout: headline at top, card grid fills main body, cards equal height and width
Text content:
- HEADLINE: "Key Integration Pitfalls"
- CARD 1 TITLE: "Opus 4.7: Price Doubles Over 200K"
- CARD 1 TEXT: "prompt > 200K tokens, unit price $5 → $10/M. Tokenizer inflation ×1.35 — budget +20% for long docs"
- CARD 2 TITLE: "Opus 4.7: Extended Thinking API Breaking Change"
- CARD 2 TEXT: "Original type: enabled + budget_tokens returns 400 error. Migrate to type: adaptive + effort parameter"
- CARD 3 TITLE: "Gemini: 200K Cost Cliff"
- CARD 3 TEXT: "≤200K $2/$12, >200K jumps to $4/$18. Agent self-feeding context often exceeds threshold by round 4"
- CARD 4 TITLE: "GPT-5.5: Computer Use Locked to Desktop App"
- CARD 4 TEXT: "78.7% only in macOS Codex App; EU/UK unavailable"
- CARD 5 TITLE: "DeepSeek: Three Access Paths, Different Risks"
- CARD 5 TEXT: "Official API data resides in China; third-party inference bypasses this; self-hosting cleanest (V4-Flash runs on single H200)"
- CARD 6 TITLE: "Copilot Multiplier Jumps to 7.5×"
- CARD 6 TEXT: "GPT-5.5 and Opus 4.7 in Copilot jump from 1× to 7.5×; actual consumption far exceeds sticker price"

### Slide 5 — dispatch matrix (table)
Visual design:
  - Visual elements: 7-row borderless table, alternating row background colors (#0D1117 / #161B22) for readability; recommended model names highlighted in electric blue; metric numbers retain original colors; electric-blue arrow → as visual separator
  - Layout: headline at top, table fills main body, three columns: task type (left) / recommended model (center) / key rationale (right)
Text content:
- HEADLINE: "Dispatch by Task"
- ROW 1: "Agentic coding loop → GPT-5.5 → Terminal-Bench 82.7% vs Opus 4.7's 69.4%"
- ROW 2: "Real GitHub issue fixes → Opus 4.7 → SWE-Bench Pro 64.3%, market leader"
- ROW 3: "Fact-sensitive reports → Opus 4.7 → Hallucination 36%, only one below 50%"
- ROW 4: "Multimodal / video / PDF → Gemini 3.1 Pro → Video-MMMU 87.6%, ScreenSpot-Pro 72.7%"
- ROW 5: "High-throughput batch processing → DeepSeek V4-Flash → $0.14/M, 1/36th of GPT-5.5"
- ROW 6: "Computer use / RPA → Opus 4.7 → Equivalent OSWorld score, but API-accessible"
- ROW 7: "Compliance (finance/medical) → Opus 4.7 (Bedrock) / GPT-5.5 (Azure) → DeepSeek official API fails audit"

### Slide 6 — isometric illustration hub-spoke
Visual design:
  - Visual elements: isometric-style illustration — four "specialist stations" arranged around a central hub; each station has a matching scene illustration (code editor screen / terminal command line / camera + documents / dashboard + coins); glowing connector lines radiating from center; dark background, illustration elements with soft glow halos
  - Layout: left side two paragraphs of body text, right side large illustration occupying 60%, model label cards below each station
Text content:
- HEADLINE: "Build a Team, Don't Bet on One Model"
- BODY: "In spring 2026, no single model is optimal across all scenarios. Each model's tradeoffs point in different directions — this is intentional design, not temporary market noise."
- CENTER: "Your Tasks"
- SPOKE 1: "Opus 4.7  Long-horizon code"
- SPOKE 2: "GPT-5.5  Agentic shell"
- SPOKE 3: "Gemini 3.1  Multimodal + search"
- SPOKE 4: "DeepSeek V4-Flash  High-throughput batch"
- CAPTION: "The jagged frontier won't converge anytime soon"

### Slide 7 — two-column action cards
Visual design:
  - Visual elements: top principle text with electric-blue highlight on key phrase; two large dark cards (#161B22), each with an oversized electric-blue number (01/02) top-left as visual anchor; electric-blue thin line spanning full width, separating principle zone from card zone
  - Layout: headline at top, principle text one line, thin line separator, two cards side by side filling bottom half
Text content:
- HEADLINE: "One Architectural Decision"
- PRINCIPLE: "Leave room to swap models — have an explicit routing layer between task types and models that can be evaluated and switched independently"
- LABEL 1: "01"
- ACTION 1 TITLE: "Cost by Task Layer"
- ACTION 1 TEXT: "High-frequency low-complexity calls at $0.01 vs long-agent calls at $5 — they can't share a budget"
- LABEL 2: "02"
- ACTION 2 TITLE: "Evaluation Built-In"
- ACTION 2 TEXT: "Define 5–10 representative cases per task type; run a comparison before every model switch"

### Slide 8 — closing
Visual design:
  - Visual elements: pure minimal typography, oversized centered text, electric-blue 1px thin line separating headline from subtitle, generous whitespace is the protagonist
  - Layout: full-page vertical centering, large headline occupies 40% height, thin line below, subtitle beneath, one line of key words below that, tiny footer
Text content:
- HEADLINE: "Dispatch by Task"
- SUBTITLE: "Is the Foundational Skill for AI Selection in 2026"
- BODY: "Evaluate → Dispatch → Monitor → Re-evaluate"
- FOOTER: "Superlinear Academy · 2026"
```

---

## Phase 3: Build All Prompts

After the user confirms the deck_spec, build complete prompts for **all slides** at once, then proceed to Phase 4.

Do not send API requests while building prompts.

Each slide's prompt format: see **prompt-guide.md**.

---

## Phase 4: Batched Concurrent Generation

### Phase 4a: Generate the reference slide first (serial)

Whichever slide will be referenced by later slides via `--ref` must be generated first. This is typically slide-01 (cover), but if the deck has multiple visual blocks, each block's "master slide" must be generated before the others in its block begin.

```bash
ppt gen {deck} "{cover prompt}" --size 2048x1152 --quality high --slot 1
```

Wait for the command to return before starting Phase 4b.

### Phase 4b: Remaining slides in small batches (2–3 at a time)

**Every slide must explicitly specify `--slot`** — this prevents multiple processes from claiming the same number and overwriting each other (hard technical constraint).

`--ref` points to whichever slide's visual language you want to inherit — use your judgment, it doesn't have to be slide 1.

Fork **2–3 slides per batch**, then `wait` for the whole batch before starting the next one:

```bash
# Batch 1 — 2–3 slides
ppt edit {deck} "{slide-2 prompt}" --ref {ref_slot} --slot 2 &
ppt edit {deck} "{slide-3 prompt}" --ref {ref_slot} --slot 3 &
wait

# Batch 2 — next 2–3 slides
# Slide with intentional style break → use gen instead of edit
ppt gen  {deck} "{slide-4 prompt}" --slot 4 &
ppt edit {deck} "{slide-5 prompt}" --ref {ref_slot} --slot 5 &
wait
```

**Speed comparison**: 5 slides all serial ≈ 75s, in 2–3-wide batches ≈ 40s.

> **Concurrency cap — do not over-fan-out.** The AI Gateway enforces a per-user
> concurrent-billable limit (typically 3), and that budget is **shared** between
> image result fetches and the model calls running the chat. It does **not**
> queue overflow: a 4th+ concurrent billable request is rejected with 429, and
> that slide can fail if the retries do not clear in time. Keep each batch to
> **2–3 slides** and `wait` between batches. Forking 6–8 at once does not make
> the deck faster — it makes slides fail mid-run.

### If a slide fails or its shell tool times out

Re-run the **same** command (same deck, slot, prompt, model, size, quality). The CLI saved the queue `request_id`, so it **resumes** the in-flight render instead of submitting — and re-billing — a new one. Do **not** respond to a failure by launching more slides in parallel; that piles more load onto the same saturated budget. Regenerate the failed slide(s) one at a time, then continue.

---

## Phase 5: Output

```bash
ppt pack {deck}
# → outputs/{deck}/deck.pptx   (includes speaker notes)
# → outputs/{deck}/index.html  (keyboard-navigable viewer)
```

---

## Phase 6: Fine-Tune a Slide

```bash
ppt edit {deck} "Keep layout identical. REPLACE the main title with: 'New title text'. Do not change anything else." \
    --ref {N} --slot {N}
ppt pack {deck}
```

**Edit chains must not exceed 3 layers**: chained edits accumulate error; beyond 3, output drifts. Go back to `gen` and regenerate from scratch.
