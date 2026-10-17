# Visual Types Reference

A slide's visual design is built from multiple stacked layers. When planning COMPOSITION, think through each layer and take what you need — they combine freely.

---

## Layer 1: Primary Visual (the dominant visual form of this slide)

### Data Charts
- **Horizontal bar chart** — multi-object same-metric comparison; color distinguishes objects, bar length represents value, numbers at bar ends
- **Vertical bar chart** — time series or category comparison; can be grouped or stacked
- **Line chart** — trend over time; multiple lines in different colors
- **Radar chart** — multi-dimension composite scoring
- **Big number** — single key figure dominates the visual center, with delta annotation and caption
- **Heatmap** — matrix density/intensity, color depth represents value

### Structure & Relationship Diagrams
- **Flowchart** — directed steps; rectangle/diamond nodes + arrows, supports branching and decisions
- **Hub-spoke** — central concept radiating to multiple branches; nodes can carry illustrations or icons
- **Timeline** — horizontal or vertical milestone sequence; nodes can carry dates and event descriptions
- **Tree diagram** — hierarchical structure; parent-child relationships, suitable for org charts and taxonomies
- **Matrix / quadrant** — two-dimension cross-mapping, positions multiple objects

### Comparison Layouts
- **Left-right columns** — two columns side by side; each with label + items, ideal for A vs B
- **Card grid** — multiple equal-weight cards (3×2, 2×2, etc.); each with title + content
- **Table** — multi-row multi-column; can have alternating row colors, highlighted rows

### Illustrations & Scenes
- **Isometric illustration** — three-dimensional scenes; workstations, devices, people, buildings; ideal for showing products, systems, or workflows
- **Flat illustration** — simple geometric shapes combined; ideal for concept visualization and step-by-step explanations
- **Icon cluster** — multiple thematic icons with text labels; ideal for feature lists and capability overviews

### Pure Typography
- **Large centered type** — quote slides, closing slides; headline takes 40–60% canvas height, generous whitespace
- **Hierarchical type** — headline + subtitle + body text; moderate information density, text is the sole protagonist

---

## Layer 2: Containers & Backgrounds

Background is not just a base color — it can actively participate in the design:

- **Solid dark/light base** — cleanest option; lets foreground content stand out
- **Grid texture** — fine grid overlaid on base color, adds engineering blueprint or precision feel (e.g., `#E5E5E5` lines, low opacity)
- **Gradient background** — dark-to-light or radial gradient, adds depth and spatial dimension
- **Noise/grain texture** — adds material feel, avoids overly digital look
- **Watermark / ghost text** — oversized pale text or shape pressed into the background layer (e.g., year "2026", brand name), doesn't interfere with readability
- **Color block zones** — canvas split into two or three distinct color regions, visually separating content areas
- **Dark cards** — content containers floating above the page background (e.g., `#161B22` card on `#0D1117` base); can have rounded corners, drop shadow, or glowing border

---

## Layer 3: Decorative & Emphasis Elements

Used to guide the eye, establish rhythm, and differentiate information hierarchy:

- **Color bar** — thin vertical or horizontal strip (2–4px), flush against left/top of a card or paragraph, as color accent
- **Divider line** — thin line (1–2px) separating headline from body, or different content zones
- **Corner label / page number** — small text top-right or top-left: "01 / 08", "Q1 · 2026"
- **Badge / tag** — small rounded rectangle with text, for annotating status, type, or source
- **Callout box / highlight box** — text box with background fill or border, makes a key number or conclusion pop
- **Connector lines / radial lines** — connecting lines in hub-spoke or flowchart diagrams; can add glow, dashes, or arrowhead styles
- **Accent icon** — single icon as a zone marker, not the primary visual (distinct from "icon cluster")

---

## Layer 4: Color Semantics

Color carries meaning beyond aesthetics:

- **Accent color** — one primary accent applied to the most important elements (numbers, key words, buttons)
- **Positive (green)** — signals growth, goal met, advantage
- **Warning (red / orange)** — signals risk, decline, needs attention (e.g., hallucination rate bars all red)
- **Muted (gray)** — secondary information, supporting captions, reduced visual weight
- **Brand color per object** — in multi-object comparisons, assign each object a consistent color throughout all charts (e.g., GPT-5.5 blue, Opus purple, Gemini teal, DeepSeek orange)

---

## Layer 5: Typography as Visual Element

Type itself can be a design component, not just an information carrier:

- **Oversized number** — key data at extreme scale (100px+), making the number itself the visual anchor
- **Weight contrast** — ultra-bold oversized headline vs. thin small body text; strong weight contrast creates rhythm
- **Small caps** — used for corner labels, tags, dates, and other secondary elements; refined feel
- **Watermark text** — same as Layer 2 ghost text; extra-pale large type pressed into background
- **Tracked-out lettering** — wide letter-spacing on headlines or labels; adds airiness and a premium feel

---

## How to Use This Reference

**A typical slide uses elements from 3–5 layers, stacked together — that's what gives it design depth.**

Example (benchmark comparison slide):
- Layer 1: horizontal bar chart (primary visual)
- Layer 2: dark solid base + dark card groupings
- Layer 3: color bars to separate each metric group + legend corner label
- Layer 4: warning red for hallucination bars; brand colors for all others
- Layer 5: value numbers at large scale, flush to bar ends

Example (closing slide):
- Layer 1: large centered typography (primary visual)
- Layer 2: dark solid base, no texture
- Layer 3: thin divider line below headline
- Layer 4: headline in accent color, body text in muted gray
- Layer 5: oversized headline weight vs. light small subtitle — strong contrast

**Start with Layer 1 to decide the primary visual form, then add supporting elements from other layers.** Not every layer needs to be used — stop when it's enough.
