---
name: deep-research
description: "Iterative deep research for competitive analysis, trend tracking, phenomenon investigation, and multi-source intelligence synthesis. Trigger when the task involves understanding root causes, tracing how something evolved, comparing alternatives, or producing a well-sourced research report."
---

# Deep Research

## Core Architecture: Iterative Knowledge-Gap Filling

**Core idea**: Not a linear "search, read, write" pipeline — instead, **loop iteratively until knowledge gaps are closed**.

```
┌──────────────────────────────────────────────────┐
│                 Research Loop                     │
│                                                   │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│   │ Identify │ → │ Choose   │ → │ Execute  │    │
│   │   Gaps   │   │ Strategy │   │ Search / │    │
│   └──────────┘   └──────────┘   │  Read    │    │
│        ↑                        └──────────┘    │
│        │        ┌──────────┐        │           │
│        └─────── │ Reflect  │ ←──────┘           │
│                 │ & Update │                    │
│                 └──────────┘                    │
│                      │                          │
│                      ↓                          │
│             All gaps closed?                    │
│             ├─ No  → next iteration             │
│             └─ Yes → proceed to writing         │
└──────────────────────────────────────────────────┘
```

---

## Prerequisite

**This skill must be used together with `planning-with-files`.**

1. Read the `planning-with-files` skill first.
2. Create `task_plan.md` / `findings.md` / `progress.md`.
3. Then return here and follow the phases below.

---

## Phase 0: Initialization

```
[ ] Create task directory: research/<task-name>/
[ ] Create files:
    - notes.md       (raw notes)
    - findings.md    (curated findings)
    - sources.md     (source registry)
    - gaps.md        (knowledge gap tracker)
[ ] At the top of notes.md, write:
    - What is the core question?
    - Who is the audience? What output format?
    - What are the initial sub-questions?
```

---

## Phase 1: Initial Gap Identification

Populate `gaps.md` with what you currently do not know:

```markdown
# Knowledge Gaps

## Core Question
[Primary research question]

## Open Gaps (priority order)
1. [ ] [Gap 1: specific description of what is unknown]
2. [ ] [Gap 2: ...]
3. [ ] [Gap 3: ...]

## Closed Gaps
(Move items here as research progresses)
```

**Key mindset**: Honestly admitting what you don't know matters more than pretending you do.

---

## Phase 2: Iterative Research Loop

### Each iteration has 4 steps:

#### Step 1 — Pick targets
Select 1-3 gaps from `gaps.md` for this iteration. Do not overcommit.

#### Step 2 — Choose strategy and tools

| Gap Type | Recommended Strategy |
|----------|---------------------|
| Factual (data, dates, people) | Search + verify against authoritative sources |
| Explanatory (why, how) | Deep-read 2-3 long-form articles |
| Contested (multiple viewpoints) | Compare sources from different perspectives |
| Recent developments | Time-bounded search |

#### Step 3 — Execute and record
- After each source: immediately log key takeaways in `notes.md`.
- After discovering a new source: add it to `sources.md`.
- Rate source reliability: `[HIGH]` primary / academic, `[MED]` professional media, `[LOW]` secondary / opinion.

#### Step 4 — Reflect and update gaps
After each iteration, ask:
- Which gaps did this iteration close? Mark them in `gaps.md` and move to "Closed Gaps."
- Were any **new** gaps discovered? Add them.
- Does anything need **backtracking**? (Earlier understanding proved wrong.)

### Backtracking

If you discover:
- A previously used source is unreliable
- An earlier understanding was flawed
- Stronger evidence is needed

**Backtrack immediately**: re-search that area. Do not build on incorrect foundations.

### Loop Exit Criteria

All of the following must be true before exiting the research loop:

```
[ ] Core gaps in gaps.md are >=80% closed
[ ] sources.md has >=15 entries, with >=8 marked "read in full"
[ ] notes.md has >=2000 words of raw notes
[ ] You can clearly answer the core question in 3 sentences
[ ] At least 3 iterations completed
```

---

## Checkpoints

### After 3 iterations

```
[ ] Are core gaps in gaps.md decreasing?
    - Yes → continue
    - No  → pause and reflect: is the search strategy wrong? Is the question poorly defined?
[ ] Have you discovered unexpected important information?
    - Yes → good sign; consider adjusting research direction
    - No  → search may be too narrow; try broadening scope
```

### Before writing the report

```
[ ] Can you explain this topic clearly without looking at your notes?
[ ] Are there unresolved "uncertain" markers? How will you handle them?
[ ] Is information cross-verified? Are contradictions flagged?
```

---

## Phase 3: Writing

### Recommended structure

```markdown
# [Title]

## Summary (3-5 sentences, core findings)

## Background (why this question matters)

## Body
### [Sub-topic 1]
### [Sub-topic 2]
...

## Key Findings / Conclusions

## Uncertainties and Limitations (honest about what remains unclear)

## Sources
```

### Writing principles
- **Separate facts from interpretation**: state facts first, then analysis.
- **Flag uncertainty**: use phrases like "according to X", "unconfirmed", "disputed".
- **Every key claim needs a source.**
- **No decorative emoji in reports**: keep formatting clean and professional.

---

## Guiding Principles

### 1. Understand, don't just deliver
The goal is not "produce a report fast" — it is "do I truly understand this?"

### 2. Maintain narrative coherence
Ask: "If I had 5 minutes to explain this to a non-expert, how would I tell the story?"

### 3. Respect "I don't know"
When sources conflict, do not arbitrarily pick one. Flagging uncertainty makes the report more trustworthy.

### 4. Be skeptical of "why"
Distinguish: facts vs. post-hoc rationalization vs. survivorship bias.

### 5. Iterate over perfection
Run a quick first pass, identify gaps, then fill them. Do not try to get everything right on the first attempt.

---

## Output Checklist

```
[ ] Can you summarize the core findings in one paragraph?
[ ] Is the timeline / logical flow clear?
[ ] Do key data points have sources?
[ ] Are facts and interpretations separated?
[ ] Are uncertainties flagged?
[ ] Are core gaps from gaps.md closed?
```

---

## Visualization and Formatting

- Data trends: line charts
- Quantity comparisons: bar charts
- Timelines: tables or visual timelines
- Key comparisons: tables

**Chart generation**: Do not rely solely on ASCII / text charts. Use real tools to produce images for the final report:
- **Mermaid**: flowcharts, timelines, relationship diagrams — render to SVG/PNG.
- **Python (matplotlib / plotly)**: data comparisons, trend charts, pie charts — generate PNG.
- Embed generated images directly into the final report for clarity.

---

## Analytical Frameworks

When applicable, use structured frameworks to strengthen analysis:

- **Source Quality Hierarchy** — Rank sources by reliability: primary legal/official documents > first-party statements > analyst reports > news coverage.
