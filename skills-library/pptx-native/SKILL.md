---
name: pptx-native
description: >-
  Default PowerPoint skill. Use it whenever the user asks to create, read, inspect, import, render, edit, restyle, reconstruct, or export a PPT, PPTX, PowerPoint presentation, or slide deck, unless the user explicitly requests the output to be intentionally raster, flattened, full-slide-image, or GPT Image slides. The user does not need to say editable or native: when image mode is not explicit, default to native element-based PowerPoint with OfficeCLI so text, shapes, tables, charts, pictures, media, animations, transitions, masters, and layouts remain editable. An image-based input does not opt into image-based output: use this skill when screenshots, exported slide images, image directories, or a fully flattened PPTX must be edited or reconstructed without an explicit request to keep the output image-backed. Also use it when editable slides need AI-generated background artwork behind native elements; when an existing .pptx must be converted to replayable JSON or HTML; or when element-level CRUD, round-trip fidelity, SmartArt/Morph preservation, or OOXML passthrough is required. Use the sibling pptx skill only for explicitly requested raster or image-backed output.
---

# Native PPTX with OfficeCLI

Use OfficeCLI for native PowerPoint work. Keep the existing `pptx` skill as the
raster-image mode; do not mix its generated-slide packaging workflow into this
skill. A native deck may reuse that skill's image generator for background
artwork only, then embed the result as a normal OfficeCLI `picture` behind
editable text, charts, tables, and shapes.

## Route before work

- Treat this as the default route for all PowerPoint and slide-deck work. The
  user does not need to request editability. Only an explicit request for
  raster, flattened, full-slide-image, or GPT Image slides selects the sibling
  `pptx` skill; ambiguity remains on `pptx-native`.
- When images or a fully flattened PPTX are the source and the requested output
  must be editable, use the reconstruction branch and read
  [references/image-reconstruction.md](references/image-reconstruction.md).
- When the input PPTX already contains native or mixed editable elements, keep
  that PPTX as the fidelity source and use the normal OfficeCLI editing flow.
  Do not reverse-reconstruct or flatten it.
- When the requested output is intentionally raster or image-backed, use the
  sibling `pptx` skill.

For reconstruction, treat the source slide image as the design authority. Do
not redesign, summarize, reinterpret, or apply another template unless the user
asks for that as a separate change.

## Runtime prerequisite

The product runtime should provide `officecli` as a pinned binary. Verify it
before doing document work:

```bash
command -v officecli
officecli --version
```

If it is absent inside a managed runtime, report a runtime packaging error
instead of downloading and executing an installer during the user task. Local
developers may install it from the official instructions at
`https://officecli.ai/SKILL.md`.

## Authority and help-first rule

The installed binary's machine-readable help is authoritative for supported
elements, properties, values, aliases, and verbs. Do not guess a property.

```bash
officecli help pptx
officecli help pptx <element>
officecli help pptx <verb> <element>
officecli help pptx <element> --json
officecli help all --json
```

The upstream skill at `https://officecli.ai/SKILL.md` is a useful workflow
reference. When it disagrees with the installed binary, follow the installed
binary and record its version in generated artifacts.

Before creating a presentation from scratch, load exactly one OfficeCLI design
skill for the artifact. Use `pptx` for generic decks, `pitch-deck` only for
fundraising, `morph-ppt` for cinematic 2D Morph, or `morph-ppt-3d` for 3D Morph.
Do not stack multiple design skills or reload the same one every turn. Do not
load a design skill for image reconstruction because the source pixels already
define the design.

```bash
officecli load_skill <pptx|pitch-deck|morph-ppt|morph-ppt-3d>
```

## Intent-to-command compiler

Do not memorize or invent a complete command catalogue. Compile each user intent
through the installed capability schema:

1. Map the intent to an OfficeCLI element: slide -> `slide`; text/title/label ->
   `shape`; chart -> `chart`; table -> `table`; image -> `picture`; line/arrow ->
   `connector`; grouped objects -> `group`; notes -> `notes`; motion ->
   `animation`; slide effect -> `transition`; generated background artwork ->
   sibling `pptx` image generation followed by a full-slide `picture`.
2. Query the exact verb schema before generating the command:

   ```bash
   officecli help pptx add <element> --json
   ```

3. Use only properties whose schema marks `add: true`. Treat required inputs,
   enum values, aliases, parent types, and add-only properties as versioned data.
4. Execute the smallest command or atomic batch with `--json` and capture the
   canonical stable path returned by `add`.
5. Re-read that path with `get --json` before emitting follow-up `set`, child,
   animation, or connector commands.
6. Fall back to `raw`, `raw-set`, or `add-part` only when structured help does
   not expose the requested operation.

Read [references/element-recipes.md](references/element-recipes.md) whenever a
user asks to create a deck or add native content. It contains verified PPTX
intent routing and minimal command recipes. Read
[references/contracts.md](references/contracts.md) for import/export or Web
editing contracts; it does not define authoring commands. Read
[references/background-images.md](references/background-images.md) only when
the user asks to generate a background image or the approved visual plan calls
for generated background artwork. It reuses the existing `pptx` skill's image
generation command without turning the slide into an image-backed deck.
For image reconstruction, read
[references/image-reconstruction.md](references/image-reconstruction.md) in
full. It defines the direct Agent-to-OfficeCLI command-plan prompt, build gate,
and review contract. Do not introduce a second Scene schema or compiler.

## Layer selection

Use the highest structured layer that preserves the requested behavior:

1. Read and inspect with `view`, `get`, `query`, and `validate`.
2. Modify public elements with `add`, `set`, `move`, `swap`, and `remove`.
3. Preserve the source render as a fidelity-base `picture`, then promote
   reliable regions to native elements or tight picture islands. In the
   OfficeCLI-only V1, cover each promoted source region with an exact native
   occlusion shape before adding its replacement. The fidelity base is a visual
   floor, not the delivered editing model by itself.
4. Use `raw`, `raw-set`, and `add-part` only for OOXML not covered by the
   structured interface.

For the reconstruction branch, have the Agent write one ordered native
`officecli-commands.json` array. The Agent owns visual understanding and native
OfficeCLI commands; the bundled `scripts/reconstruct.py` owns deterministic
drawing IDs, schema validation, atomic execution, audit, and render comparison.
Do not ask the Agent for a Scene, manifest, copied schema, assembler step, or
workspace layout. Per-slide command fragments remain an optional fallback only
when one JSON array is too large to generate or repair reliably.

The safety wrapper checks every `add`/`set` property against the installed
OfficeCLI help schema, then submits the final array as one atomic batch,
validates, rereads the OOXML package, renders every output slide, and compares
those renders with the reviewed source renders before replacing the requested
file. For the known `shape.wrap` help omission, the wrapper performs a
fail-closed temporary-PPTX `add shape` atomic-batch probe and readback against
the installed binary; it accepts the property only when that runtime proves the
exact behavior. `raw-set` is rejected by default; opt in only after structured
help and the supported runtime probe prove no structured operation can
preserve the feature. Unsupported features or unacceptable visual drift must
fail before output mutation.

For SmartArt, Morph, extended transitions, OLE, 3D, or future OOXML, preserve
unmodified package parts and relationships. Never rebuild unknown content from
an incomplete structured projection.

## Contract routing

Before importing an existing deck, consuming replay JSON, integrating JSON/HTML
with a product, extracting image payloads, or building Web editing, read
[references/contracts.md](references/contracts.md) in full. It is the single
source of truth for artifact roles, dump warnings, picture payload semantics,
atomic batch behavior, HTML preview, and revision compatibility. The default
PPTX delivery flow does not require loading it. Do not restate its contract in
this file.

## Default delivery

After creating or materially editing a native deck, validate and save the final
PPTX:

```bash
officecli save deck.pptx
```

Do not generate replay JSON as part of the default creation or editing flow.
Generate it only when the user explicitly requests JSON export or the task
explicitly requires the JSON/Web editing contract in `references/contracts.md`.
For an imported deck, keep the source PPTX as the fidelity source defined by
that contract.

During initial image reconstruction, `officecli-commands.json` is the source of
truth. Regenerate that plan and rebuild when source analysis changes instead of
patching the generated PPTX. If the optional fragment fallback is active,
regenerate only the affected fragment and let the runner reassemble the plan.
After delivery or any external PowerPoint/WPS edit, the PPTX becomes the source
of truth; continue with the normal OfficeCLI editing workflow and never rebuild
from a stale command plan.

After validation and save succeed, publish the final PPTX before the final
response when the runtime exposes the `publish_artifact` tool. Use its
workspace-relative path. Publish replay JSON or HTML only when the user
explicitly requests that file as a deliverable. Do not call `publish_artifact`
for previews, drafts, temporary files, or intermediate revisions.

`publish_artifact` is a runtime tool, not an OfficeCLI command. If it is absent,
or if publication fails, keep the completed files in the workspace, state that
durable artifact publication is unavailable or failed, and do not claim that
the files were uploaded or delivered as file cards.

## Editing workflow

1. Inspect the deck with `view outline`, `get`, and `validate`.
2. Retain the source PPTX as the fidelity baseline before material changes.
3. Resolve allowed elements and properties from machine-readable help.
4. Apply small atomic batches. Quote every path containing brackets.
5. Re-read affected stable paths and refresh only the affected preview scope.
6. Validate and render HTML or screenshots before delivery.
7. Open in the target Office viewer when animations, fonts, charts, or media
   playback are part of acceptance.

## Shell safety

- Quote paths such as `'/slide[1]/shape[@id=7]'`.
- Prefer `--input file.json` over large inline JSON or shell interpolation.
- Keep currency and other `$` text out of double-quoted shell expansion.
- Do not edit the ZIP package with ad-hoc text replacement.

## Completion checks

- `officecli validate deck.pptx` reports no new structural errors.
- When `publish_artifact` is available, the final PPTX is published successfully
  before the final response.
- Structured edits preserve untouched raw parts and relationships.
- Generated backgrounds are embedded as `picture` elements below native
  foreground content; visible text, charts, tables, and controls are not baked
  into the background unless the user explicitly requests raster content.
- Reconstructed decks contain native text and recoverable simple geometry.
  Irreducible or unresolved visuals remain visible in a reviewed fidelity base
  or tight picture islands; visible source content is never silently omitted.
- A full-slide residual fidelity base is allowed beneath native foreground
  elements. An unchanged full-slide source picture with no meaningful native
  foreground still fails the editability audit.
- Source and output screenshot comparison covers every slide and passes the
  reconstruction visual thresholds before publication.
- The target Office viewer is checked for runtime-only behavior.
- Import/export and Web tasks pass every check in `references/contracts.md`.
