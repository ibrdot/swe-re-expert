# Modify Scenarios

Insert, delete, reorder, or restyle slides in an existing deck.

---

## Core Mechanism

`pack` assembles slides in `slide-NN.png` filename order. The CLI has no dedicated insert/delete/reorder commands — **directly manipulate files in `outputs/{deck}/`, then repack.**

After every modification, repack:

```bash
ppt pack {deck}
```

---

## Edit a Slide's Content

The most common scenario. Overwrite the same slot:

```bash
ppt edit {deck} "{new prompt}" --ref {N} --slot {N}
ppt pack {deck}
```

- `--ref N --slot N`: use the slide itself as reference, change only what's specified
- In the prompt, write `REPLACE ... with: "..."` and `Do not change anything else`
- Keep edit chains under 3 layers — beyond that, drift accumulates; use `gen --slot N` to regenerate from scratch

---

## Delete a Slide

```bash
rm outputs/{deck}/slide-{NN}.png
rm outputs/{deck}/prompts/slide-{NN}.md   # optional, keeps prompts/ clean
ppt pack {deck}
```

After deletion, the remaining numbers may not be contiguous (e.g., 01 02 04 05). `pack` assembles in existing file order — gaps don't affect sequence. Rename files to close the gap if needed, then repack.

---

## Insert a New Slide

**Append at the end**: just gen/edit the next slot; pack will append it automatically.

**Insert in the middle** (e.g., between slide-02 and slide-03):
1. Shift slide-03 and later files back by one number (move matching `.md` files too)
2. gen/edit the new slide-03
3. ppt pack

```bash
# Shift 03 04 05 back by one
for i in 05 04 03; do
  mv outputs/{deck}/slide-0${i}.png outputs/{deck}/slide-0$((i+1)).png
done
# Generate new content at slot 3
ppt gen {deck} "{new slide prompt}" --slot 3
ppt pack {deck}
```

---

## Reorder Slides

Rename files directly; pack sorts by the new numbers:

```bash
# Example: swap slide-04 and slide-05
mv outputs/{deck}/slide-04.png outputs/{deck}/slide-04-tmp.png
mv outputs/{deck}/slide-05.png outputs/{deck}/slide-04.png
mv outputs/{deck}/slide-04-tmp.png outputs/{deck}/slide-05.png
ppt pack {deck}
```

---

## Restyle the Entire Deck

Switching the whole deck to a new visual language:

1. Regenerate slide-01 with a new STYLE + COLOR
2. Re-edit all other slides with `--ref 1` to inherit the new style
3. ppt pack

```bash
ppt gen {deck} "{new style cover prompt}" --slot 1
# Re-edit the rest in batches of 2–3, waiting between batches
# (see workflow.md "Concurrency cap" — do not fork the whole deck at once).
ppt edit {deck} "{slide-2 prompt, STYLE: keep same as ref}" --ref 1 --slot 2 &
ppt edit {deck} "{slide-3 prompt}" --ref 1 --slot 3 &
wait
# next batch of 2–3, then:
ppt pack {deck}
```

---

## Check Current State

Before making changes, use `ppt info` to see what slots exist:

```bash
ppt info {deck}
# Output: slides: 5 (01, 02, 03, 04, 05)
```
