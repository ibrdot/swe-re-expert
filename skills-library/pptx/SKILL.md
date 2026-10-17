---
name: pptx
description: |
  Create intentionally raster or image-backed slide decks with GPT Image 2, then package the generated slide images into a PPTX and HTML viewer. This is an opt-in image mode: use it only when the user explicitly asks for the output to be image-mode, raster, flattened, full-slide-image, or GPT Image slides; explicitly asks to keep an existing image-backed deck image-backed; or asks to package slide images as PowerPoint. Do not infer image mode merely because the input is screenshots, exported slides, an image directory, or a flattened PPTX. Do not use this skill for a generic request to create, read, inspect, edit, restyle, or export a PPT, PPTX, PowerPoint presentation, or slide deck. When the user does not explicitly request image-backed output, use pptx-native by default, even if they do not mention editability; pptx-native also owns reconstruction of image inputs into native slides.
  Trigger phrases: image-mode PPT, raster PPT output, keep this deck flattened, full-slide-image output, generate slide images, GPT Image slides, keep these rendered slides image-backed, edit a slide image as an image, package images as PowerPoint.
---

# GPT Image 2 PPT Skill

Uses GPT Image 2 (via the AI Gateway) to generate PPT slide images. GPT Image 2 excels at precise text rendering, making it ideal for presentations that require accurate typography in any language.

## Opt-in routing

This skill is not the default PowerPoint workflow. Use it only when the user
explicitly chooses raster or image-backed output, including an explicit request
to keep an existing image-backed deck in that mode. The input format alone does
not opt in. A generic request such as “make a PPT”, “create a presentation”,
“edit this deck”, or “restyle these slides” routes to `pptx-native`. Ambiguity
also routes to `pptx-native`; the absence of an editability requirement is not
permission to flatten the deck.

---

## Four Commands

```bash
ppt gen  <deck> "<prompt>" [--size WxH] [--quality high|medium|low] [--model gpt-image-2] [--slot N]
ppt edit <deck> "<prompt>" --ref <N|filepath|URL>... [--model gpt-image-2/edit] [--slot N]
ppt pack <deck> [--title "Title"]
ppt info <deck>
```

- `gen` — text-to-image, appends a new slide
- `edit` — image-to-image, uses an existing slide as reference (`--ref 1`
  = reference slot 1; recorded remote slide URLs are reused when available)
- `pack` — packages into deck.pptx + index.html
- `info` — view deck status

GPT Image 2 generation can legitimately take several minutes at HD/4K and
`quality=high` — longer than the **default 300s** sandbox shell-tool timeout.
The CLI polls for up to 600s, so **always pass an explicit tool timeout of at
least `660000` ms when running `gen` / `edit`**, and never wrap them in a short
shell `timeout`. If you leave the 300s default, a slow render is aborted
mid-flight — the tool call fails hard and the turn can end with no reply.

After a queue submit, the CLI saves the fal `request_id` under
`/home/user/.workspace/outputs/<deck>/queue-jobs/slide-NN.json`. If a `gen` /
`edit` fails or its shell tool times out, rerun the same command with the same
deck, slot, prompt, model, size, and quality — it resumes that queue job instead
of submitting (and re-billing) a duplicate render.

Output directory: `/home/user/.workspace/outputs/<deck>/`, slides auto-numbered as `slide-01.png`, `slide-02.png`, …

---

## Size Constraints (API hard limits)

Both width and height must be **multiples of 16**, max side ≤ 3840.

| Tier | Size | Use |
|------|------|-----|
| Preview | 1280×720 | Quick draft |
| **HD (default)** | 2048×1152 | Standard presentation ⭐ |
| 4K | 3840×2160 | Print / large screen |

⚠️ `1920×1080` won't work (1080 is not a multiple of 16).

---

## Rules Index

| File | Content | When to read |
|------|---------|-------------|
| [rules/workflow.md](rules/workflow.md) | 6-phase process, deck_spec format, batched concurrent generation | Before starting any task |
| [rules/prompt-guide.md](rules/prompt-guide.md) | Seven-section structure, language handling, font rules, full examples | When writing prompts |
| [rules/style-guide.md](rules/style-guide.md) | Style judgment, STYLE+COLOR templates, gen vs edit | When planning visual style |
| [rules/visual-types.md](rules/visual-types.md) | Design layers (charts / diagrams / illustrations / backgrounds / decorations) | When planning each slide's visual content |
| [rules/modify-scenarios.md](rules/modify-scenarios.md) | Edit page / insert page / delete page / reorder / restyle | When modifying an existing deck |

---

## Environment

Inside a sandbox the skill is wired up automatically — `APP_SERVER_URL`
and `SANDBOX_MCP_TOKEN` are injected by the runtime. Image generation goes
through the AI Gateway under the agent's user account, so it shares billing,
num_images caps, and observability with the chat-side `Generate` tool.

```bash
pip install -r requirements.txt   # httpx, python-dotenv, python-pptx
```

`requirements.txt` pins `python-pptx` to the Maxgent fork commit that includes
the Keynote speaker-notes package compatibility fix.

For local development outside the sandbox, copy `.env.example` to `.env` and
point `APP_SERVER_URL` at a running app-server with a real sandbox MCP token.

---

## Project Structure

```
├── ppt.py                  # CLI entry point
├── ppt_skill/
│   ├── api.py              # gen_image / edit_image (with retry)
│   ├── deck.py             # Deck class (numbering, metadata, file lock)
│   ├── pack.py             # to_pptx (PNG validation + speaker notes) / to_html
│   └── env.py              # load .env
├── rules/                  # AI execution rules
│   ├── workflow.md
│   ├── prompt-guide.md
│   ├── style-guide.md
│   ├── visual-types.md
│   └── modify-scenarios.md
├── style_refs/             # 14 style samples (for reference, not templates)
└── templates/viewer.html   # HTML viewer template
```

Generated content is written under `/home/user/.workspace/outputs/<deck>/`:

```
├── deck.json           # Metadata + history
├── slide-NN.png
├── prompts/slide-NN.md # Full prompt per slide (also used as speaker notes)
├── deck.pptx
└── index.html
```
