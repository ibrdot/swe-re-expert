# GPT Image 2 PPT Skill

Generate PPT slide images via **GPT Image 2** through the AI Gateway, focused on typographic quality. A clean, deck-driven CLI.

## Design Philosophy

**Provide atomic commands; let the AI decide how to compose them.**

- `gen` / `edit` — call the AI Gateway to generate / edit images
- `pack` — locally bundle images into `.pptx` and `index.html`

No hardcoded "mode A / B / C" workflow — Claude decides per-slide based on context.

## Core Concept: deck

**A deck = one directory under `/home/user/.workspace/outputs/`**.
- Slides are auto-numbered as `slide-01.png`, `slide-02.png`, ...
- `deck.json` records size / quality / style defaults plus operation history
- The `pack` command produces a shareable `.pptx` and `index.html`

## Quick Start

```bash
# 1. Install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# requirements.txt pins python-pptx to the Maxgent fork commit containing the
# Keynote speaker-notes package compatibility fix.

# 2. (Inside a sandbox: skip — APP_SERVER_URL and SANDBOX_MCP_TOKEN are auto-injected.)
#    For local dev, copy .env.example to .env and point at a running app-server.
# cp .env.example .env

# 3. Generate the first slide (sets the deck defaults)
#    Style is not a CLI argument — the AI picks it from the content and writes it into the prompt
.venv/bin/python ppt.py gen q1-demo \
  "Editorial magazine cover, huge serif title 'Q1 Product Review', off-white bg, thin hairline divider, small sans-serif subtitle '2026 · Product Team'. Crisp exact typography." \
  --size 2048x1152 --quality high

# 4. Subsequent slides reference slide 1 as the master (size/quality auto-inherited)
.venv/bin/python ppt.py edit q1-demo \
  "Keep layout identical. REPLACE title WITH: 'Key Results'. REPLACE subtitle WITH: 'Users +32% · Retention 78% · NPS 62'." \
  --ref 1

.venv/bin/python ppt.py edit q1-demo \
  "Keep layout identical. REPLACE title WITH: 'Thank you'. REPLACE subtitle WITH: 'See you in Q2'." \
  --ref 1

# 5. Check status
.venv/bin/python ppt.py info q1-demo

# 6. Pack everything
.venv/bin/python ppt.py pack q1-demo
# → /home/user/.workspace/outputs/q1-demo/deck.pptx     (open in Keynote / PowerPoint)
# → /home/user/.workspace/outputs/q1-demo/index.html    (keyboard ← → navigation player)
open /home/user/.workspace/outputs/q1-demo/index.html
```

## Four Commands

| Command | Purpose | Example |
|------|------|------|
| `gen <deck> <prompt>` | Text-to-image, auto-numbered | `ppt gen my "..."` |
| `edit <deck> <prompt> --ref N` | Image-to-image, references slot N | `ppt edit my "..." --ref 1` |
| `pack <deck>` | Bundle into .pptx + .html | `ppt pack my` |
| `info <deck>` | Show deck status | `ppt info my` |

### Model choice and timeout

`gen` defaults to `gpt-image-2`; `edit` defaults to `gpt-image-2/edit`.
GPT Image 2 generation can legitimately take several minutes at HD/4K and
`quality=high`. When invoking through a sandbox shell tool, set the tool timeout
longer than the CLI's 600s polling cap, and do not wrap `gen` / `edit` in a
short shell `timeout`.

After a queue submit, the CLI saves the fal `request_id` under
`/home/user/.workspace/outputs/<deck>/queue-jobs/slide-NN.json`. If the outer
shell tool times out, rerun the same command with the same deck, slot, prompt,
model, size, and quality to resume that queue job instead of submitting a
duplicate render.

### `--ref` for `edit`

Three accepted forms:
- `--ref 1` — reference slot 1 of the same deck; if `deck.json` records a
  remote `source_url` for that slot, the skill uses that URL directly instead
  of re-uploading the local slide image
- `--ref /path/to/brand.png` — local file
- `--ref https://...png` — URL
- Multiple allowed: `--ref 1 --ref brand.png`

### Refining a single slide

```bash
ppt edit mydeck "Change title to 'XX'." --ref 3 --slot 3   # overwrite slide 3
ppt pack mydeck                                             # repack
```

## Use as a skill

This ships as a kernel skill and is auto-discovered by the runtime — no install or symlink step is needed.

If you ever copy it into a workspace as a user skill, place it at `/home/user/.workspace/skills/<name>/`.

Then ask the agent to plan according to `SKILL.md` and invoke the CLI.

## Project Structure

```
pptx/
├── ppt.py                    # CLI entrypoint
├── ppt_skill/                # core package
│   ├── env.py                #   loads .env
│   ├── deck.py               #   Deck class
│   ├── api.py                #   gen_image / edit_image (calls AI Gateway)
│   └── pack.py               #   to_pptx / to_html
├── templates/viewer.html     # HTML player
├── style_refs/               # style reference samples (for inspiration, not a fixed menu)
├── .env.example
└── requirements.txt
```

Generated decks are written outside the skill tree under
`/home/user/.workspace/outputs/<deck>/`.

## About Sizes

For GPT Image 2, both sides must be multiples of 16, longest side ≤ 3840, and total pixels 655,360–8,294,400.

- SD: `1280x720`
- **HD (default): `2048x1152`** ⭐
- 4K: `3840x2160`

⚠️ `1920x1080` is invalid (1080 is not a multiple of 16).

## Pricing Reference

Image generation is billed against the user's credit wallet through the
AI Gateway, using the official GPT Image 2 size + quality pricing table (see
`server/ai-gateway/gateway/services/fal_gpt_image_pricing.py`). At HD
(2048×1152), one slide is roughly $0.01 (low) / $0.06 (medium) / $0.22 (high).
`quality=high` is the default; switch to `medium`/`low` to save credits when
typography precision is less critical.

The gateway caps `num_images` at 4 per request and applies the same concurrency
and balance checks that govern chat-side image generation.
