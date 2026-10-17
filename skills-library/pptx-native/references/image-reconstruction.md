# Image-to-editable reconstruction

## Default contract

Use this branch for screenshots, exported slide images, image directories, or a
fully flattened PPTX that must become editable.

The default Agent interface is deliberately small:

```text
source images -> Agent vision -> officecli-commands.json -> reconstruct.py build -> editable.pptx
```

The Agent writes one ordered native OfficeCLI command array. The runner assigns
missing drawing IDs, validates the installed OfficeCLI schema, executes one
atomic batch, audits editability, renders every slide, and applies the visual
fidelity gate. There is no Scene, manifest, copied schema, explicit assembler
step, or required workspace layout.

## 1. Route and inspect the source

For a PPTX, audit before reconstruction:

```bash
SKILL_DIR=/opt/kernel/skills/pptx-native
python3 "$SKILL_DIR/scripts/reconstruct.py" audit-pptx source.pptx
```

- `route: reconstruct`: the deck is fully flattened; reconstruct it. Fully
  transparent PNG placeholders do not change this route.
- `route: edit-existing`: the deck already contains native or mixed editable
  content; preserve that PPTX and use normal OfficeCLI editing.

Never flatten a native or mixed deck merely to use this workflow.

Render every flattened source page to a reviewed PNG before visual analysis:

```bash
officecli view source.pptx screenshot --page 1 --out source/slide-01.png \
  --screenshot-width 2048 --screenshot-height 1152 --render html
```

For direct images, inspect the original pixels at full size. The source pixels
are the design authority; do not redesign, summarize, or substitute a template
unless the user asks for a separate redesign.

## 2. Choose editable and fidelity-preserving regions

Use Agent vision to identify meaningful editing units rather than every contour:

| Source object | Default representation |
| --- | --- |
| Verified readable title, body, label, date, number, percentage, or unit | Native text `shape` |
| Stable card, divider, rule, arrow, or connection | Native `shape` or `connector` |
| Photo, screenshot, map, illustration, detailed logo, or complex icon | Tight `picture` island |
| Chart or table whose underlying data is not verified | Tight `picture` island |
| Unreadable copy, uncertain boundary, or unsupported effect | Fidelity base or focused review |

Default to a fidelity-floor hybrid reconstruction:

1. Add the original source render as a full-slide fidelity-base picture so no
   small icon, decoration, illustration, or uncertain effect disappears.
2. Promote reliable text and simple geometry to native elements.
3. Before promoting a region, cover its old pixels with the tightest accurate
   native occlusion shape whose fill matches the local background.
4. If clean occlusion is not possible, leave that region image-backed. Do not
   layer a duplicate native object over the original pixels.

The fidelity base must not be the only meaningful slide object. Do not replace
uncertain visuals with generic icons, invented charts, simplified
approximations, or empty space.

Select the Office slide canvas before measuring objects and use one consistent
source-to-slide scale for all coordinates and sizes.

## 3. Write one native OfficeCLI command plan

Query the installed binary for element types used by the slide. Query exact help
when a property, enum, or verb is uncertain instead of guessing:

```bash
officecli --version
officecli help pptx add slide --json
officecli help pptx add shape --json
officecli help pptx add picture --json
officecli help pptx add connector --json
```

Write `officecli-commands.json` as a plain ordered JSON array, not an envelope:

```json
[
  {
    "command": "set",
    "path": "/",
    "props": {
      "slideWidth": "960pt",
      "slideHeight": "540pt"
    }
  },
  {
    "command": "add",
    "parent": "/",
    "type": "slide",
    "props": {
      "name": "slide-01"
    }
  }
]
```

Add objects back to front: slide, fidelity base, occlusion patches, picture
islands, native geometry, then native text. Use unique semantic `props.name`
values and absolute local asset paths. Drawing `props.id` may be omitted; the
runner assigns missing IDs deterministically. Add connector endpoints before
connectors and reference endpoints by stable `@name` paths. Reconstructed
single-line text boxes should set `"wrap": false` so Office renderers do not
reflow tightly measured CJK titles, labels, or chart text. The current wrapper
handles the known OfficeCLI help omission with a fail-closed runtime add probe
and readback; do not replace structured `wrap` with repeated `raw-set`
commands when the probe passes.

`raw-set` is rejected by default. Use it only when current structured help
cannot preserve a required feature and the caller explicitly enables
`--allow-raw-set`.

### Reconstruction prompt

```text
Reconstruct the supplied slide images as an editable PowerPoint with the
installed OfficeCLI binary.

Treat the source pixels as the visual authority. Preserve every visible detail;
do not redesign, summarize, invent content, infer unverified chart data, or
silently omit small icons, decoration, labels, numbers, or uncertain regions.

Query `officecli help pptx <verb> <element> --json` when an OfficeCLI property or
value is uncertain. Write only one ordered native OfficeCLI JSON array to
officecli-commands.json. Do not create a Scene, schema copy, manifest, markdown
explanation, or workspace structure.

Use an explicit slide canvas and one consistent coordinate scale. Build each
slide back to front. Start with the original full-slide render as a fidelity
base, then promote verified text and simple geometry to native elements. Cover
the old pixels of each promoted region with a tight background-matched native
shape first. If that cannot be done cleanly, keep the region image-backed
instead of duplicating or omitting it.

Use native text for verified readable copy, native shapes/connectors for
recoverable simple geometry, and tight picture islands for complex or uncertain
visuals. Give created objects unique semantic names, use absolute asset paths,
and add connector endpoints before connectors. You may omit drawing IDs because
the runner assigns them. Set `wrap` to `false` for text reconstructed as an
intentional single line. Do not emit raw-set unless explicitly requested.

Before finishing, account for every visible source region and verify every word,
date, number, percentage, and unit against the source.
```

## 4. Build and review

The normal build is one command:

```bash
python3 "$SKILL_DIR/scripts/reconstruct.py" build \
  --source-renders work/source \
  --commands officecli-commands.json \
  --out editable.pptx
```

The diagnostics workspace defaults to
`.editable.pptx.reconstruction/` beside the output. Pass `--workspace <path>`
only when the caller needs a specific location.

The runner submits the prepared array as one atomic batch, validates the OOXML,
audits native objects, captures `get`/`stats`/`issues`, renders every slide, and
compares those renders with `slide-NN.png`. It publishes the requested output
only after all hard gates pass. The initial visual gate requires average
normalized MAE at or below 8% and every slide at or below 15%. This is a
regression floor, not proof that small details are correct.

Inspect every slide at full size. Check for missing or duplicated content,
incorrect text and numbers, crop or z-order drift, wrapping and clipping, and
whether native foreground objects are actually editable. Temporarily edit at
least one named text object on each applicable slide and confirm the old source
glyphs do not remain underneath.

OfficeCLI HTML screenshots are same-stack evidence. Open the final file in the
target PowerPoint or WPS viewer before claiming cross-viewer, font, animation,
media, or playback fidelity.

During initial reconstruction, update `officecli-commands.json` and rebuild.
After delivery or an external edit, the PPTX becomes the source of truth and
normal stable-path OfficeCLI editing takes over.

## Optional fallback for very large plans

Use fragments only when one command array is too large to generate or repair
reliably. This is an internal scaling fallback, not the default Agent contract
and not a second representation.

```text
commands/
├── 00-presentation.json
├── slide-01.json
├── slide-02.json
└── ...
```

Each file remains a plain native OfficeCLI array. `00-presentation.json`
contains root presentation `set` commands. Each `slide-NN.json` starts with one
slide named `slide-NN` and remains scoped to `/slide[N]`.

Build directly from fragments:

```bash
python3 "$SKILL_DIR/scripts/reconstruct.py" build \
  --source-renders work/source \
  --fragments work/commands \
  --out editable.pptx
```

The runner orders fragments, rejects gaps and cross-slide references, assigns
IDs, and executes the same validation and visual gates as the single-file path.
