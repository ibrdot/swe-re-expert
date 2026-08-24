---
name: swe-re-expert
description: "Expert-level Software Engineering + Reverse Engineering for AI agents. Triggers whenever the agent must analyze, audit, refactor, or reverse-engineer code or binaries across C/C++/ASM, Python, Go, and Rust. Use this skill for: reading a binary and reconstructing its logic; malware triage and IOC extraction; static + dynamic analysis of ELF/PE/Mach-O; PR review, refactoring, architecture audit, or modernization of a codebase; vulnerability hunting in disassembly; explaining what a function or executable does; CTF-style pwn/rev reasoning; producing deep structured analysis reports. Trigger it whenever the user mentions any of: reverse engineering, binary analysis, disassembly, decompilation, malware triage, IOC extraction, YARA rules, code review, refactoring, architecture audit, performance review, code modernization, or asks 'what does this binary/function/module do' — even if they don't explicitly name SWE or RE. A powerful, research-grade expert skill that does the actual work — analysis, audit, refactor, recover semantics — at senior level."
---

# SWE + RE Expert — Software Engineering & Reverse Engineering for AI Agents

This skill turns the agent into a **balanced expert** across two complementary disciplines:

- **SWE** — read a codebase like a senior reviewer: map real architecture, find material defects, prioritize refactors, modernize, audit tests. Patterns over purity; fitness over fashion.
- **RE** — read a binary like a malware analyst: triage, disassemble, recover semantics, extract IOCs, map behavior, classify families.

Both halves share a single output discipline: **deep, structured analysis reports**, where every finding cites evidence (offsets, paths, instructions, line numbers), classifies severity, and recommends the smallest safe next step.

---

## When to trigger

**Strong signals — fire immediately:**

- "analyze this binary / .exe / .elf / .so / .dll / .dylib / firmware"
- "what does this function do" (with disasm or decompilation pasted)
- "reverse engineer this protocol / file format / sample"
- "malware analysis / triage this sample / extract IOCs / YARA"
- "code review / refactor this PR / audit this module"
- "architecture audit / dependency analysis / dead code"
- "find the vulnerability in this disassembly"
- "CTF rev / CTF pwn / crack this binary"
- pasted disassembly, Ghidra/IDA output, or hex dumps

**Weak signals — ask one clarifying question, then proceed:**

- "this code is messy" → "is this a refactor request or an audit?"
- "look at this" + binary blob → "do you want a triage report or a deep RE pass?"

Do not trigger for: pure text writing, dashboards, slide decks, or trivial one-file edits with no engineering question.

---

## Workflow — the universal 5-phase loop

Both SWE and RE work runs through the same loop. The phase *names* are shared; the *content* differs by domain. Treat the phases as a Definition of Done — work through them in order, and only declare the task complete when every applicable item has a recorded outcome (PASS / CONCERNS / FAIL / N/A with reason).

```
1. SCOPE       — what is the user actually asking? what's the target? what's "done"?
2. TRIAGE      — fast first pass: identify, list, map. Cheap signals first.
3. DEEP DIVE   — the patient pass: read, trace, verify. Evidence over intuition.
4. ASSESS      — classify findings by severity and materiality. Filter nitpicks.
5. REPORT      — produce the structured analysis report. Recommend the smallest safe next step.
```

### Phase 1 — SCOPE

Before any tool call, nail down what the user wants. Ask (do not assume):

- **Target**: file path? binary blob? function name? codebase root? git ref?
- **Goal**: full report? one specific question? patch? just understand?
- **Depth**: quick triage (minutes) or deep dive (hours)?
- **Constraints**: time, environment, sensitivity (CTF? prod incident?), and what's off-limits
- **Format**: markdown report? inline answer? patched diff? extracted IOCs?

If the user gave a binary without much context, ask one quick clarifying question about the goal (triage vs deep dive) rather than assuming.

### Phase 2 — TRIAGE

Fast first pass to orient yourself. Pick the cheap, high-signal moves first.

**For a binary (RE triage):**

```bash
python scripts/re_triage.py --file <target> --all
```

This produces JSON with: file type, arch, endianness, linking, security features (NX/PIE/RELRO/canary), section entropy, suspicious strings, imported functions of interest, entry point. Use it to decide whether the binary is packed, stripped, Go/Rust, obfuscated, etc.

**For a codebase (SWE triage):**

```bash
python scripts/swe_audit.py --root <root> --triage
```

This produces a one-page map: file inventory by language, top complexity hotspots, dependency direction summary, suspected dead code, test coverage signal if detectable. Use it to pick deep-dive targets rather than reading every file.

If the agent has the tools, also try: `git log --oneline -20`, `git diff main...HEAD --stat`, `rg -c "TODO|FIXME|XXX"`, `wc -l`, language detection by extension. The point is **breadth first**, not depth.

### Phase 3 — DEEP DIVE

This is where the agent earns its keep. Read carefully, trace flows, and record evidence with **addresses / line numbers / call sites**.

**For RE**, this means: disassemble the interesting functions, annotate each basic block, recover high-level pseudocode, and follow calls. Use `scripts/re_disasm.py` for a structured function-level summary. Cross-reference strings, imports, and constants to build a hypothesis about behavior. Read `references/binary-analysis.md` for the full playbook (static → dynamic → semantic recovery).

**For SWE**, this means: read the suspect modules, trace the critical flows end-to-end, look for the material anti-patterns listed in `references/swe-playbook.md` (parameter sprawl, leaky abstractions, hidden writes, dead code, parallel mechanisms, fragile tests). Don't just read for style — read for **fitness**: does this structure serve the current product complexity, or is it pattern-for-pattern's-sake?

**For malware**, the deep dive is the static → dynamic → behavioral pipeline. Read `references/malware-analysis.md` for the full triage workflow.

### Phase 4 — ASSESS

Filter ruthlessly. A finding is only material if it predicts a **concrete cost**: correctness bug, security hole, change amplification, deployment coupling, recurring maintenance pain, or — for RE — a behavior worth reporting. Pattern preference, theoretical purity, and "I would have written it differently" are **not** findings. Classify:

| Severity | SWE meaning | RE meaning |
|----------|------------|------------|
| P0 | Correctness/security defect, blocks release | Confirmed malicious behavior with active IOCs |
| P1 | Material defect, will cause recurring pain | Likely malicious, partial IOCs |
| P2 | Non-blocking improvement | Suspicious but unconfirmed |
| P3 | Nitpick / future consideration | Curiosity / informational |

Apply an **acceptable-alternative gate**: if the current shape is one of several reasonable choices given the constraints, that's not a finding — only flag it if there's no acceptable alternative.

### Phase 5 — REPORT

Use the templates in `assets/`. Every report must include:

- **Verdict** (PASS / CONCERNS / FAIL / BLOCKED for SWE; CLEAN / SUSPICIOUS / MALICIOUS / INCONCLUSIVE for RE)
- **Summary** (3-5 sentences, plain English)
- **Evidence** table (offsets / line numbers / function names / call sites)
- **Findings** table (severity, problem, evidence, recommended next step)
- **Limitations** (what couldn't be verified, why, what would resolve it)
- **Recommended next step** (the smallest safe change or follow-up action)

Never add artificial "End of Report" markers. Let the last finding's recommendation close the document.

---

## Reference files — progressive disclosure

Read **only** what the current task needs. Each file is self-contained and can be read on demand.

| When to read | File | What's inside |
|--------------|------|---------------|
| Any SWE task: review, refactor, architecture audit | `references/swe-playbook.md` | Tool routing, evidence rules, anti-pattern catalog with severity, refactor priority matrix, modernization decision tree |
| Any RE task on a native binary | `references/binary-analysis.md` | Static (file/strings/imports/entropy/disasm) → dynamic (gdb/strace/Qiling) → semantic recovery (pseudocode, structs, calling conventions) |
| User-supplied suspicious sample | `references/malware-analysis.md` | Triage pipeline, IOC extraction, MITRE ATT&CK mapping, YARA generation, family classification |
| Need language-specific detail (C/C++/ASM, Python, Go, Rust) | `references/language-depth.md` | Per-language gotchas, idiom detection in disasm, modernization notes, toolchain quirks |

---

## Prompts — expert reasoning files

The `prompts/` directory contains focused, expert-level reasoning patterns that strengthen the agent's analysis. Read **only** what the task calls for. Each file is self-contained (50-200 lines, dense).

| When to read | Directory | What's inside |
|--------------|-----------|---------------|
| Need the mental model for the task type | `prompts/mental-models/` | How a senior RE approaches a binary, how a senior engineer reads a codebase, vuln-hunting patterns, refactor decision gates, architecture fitness, static vs dynamic trade-offs, evidence vs assertion |
| RE-specific deep techniques | `prompts/re-playbooks/` | C/Go/Rust binary recovery, CTF rev & pwn approaches, disasm recovery, anti-pattern recognition (packers, anti-debug, obfuscation), malware triage mental model, YARA rule design, IOC extraction, obfuscation workarounds |
| SWE-specific deep techniques | `prompts/swe-playbooks/` | Code audit priorities, perf review, security review, test quality review, modernization gates, dependency analysis, dead code confirmation, refactor prioritization, per-language anti-patterns (Python/Rust/Go/C++) |
| Output discipline | `prompts/meta/` | Report writing discipline, uncertainty markers (HYPOTHESIS/SUSPECTED/UNVERIFIED/BLOCKED/INCONCLUSIVE), evidence checklist (12-point verification) |

These files are the agent's "thinking tools" — when the task needs expert-level reasoning on a specific dimension, the agent loads the relevant prompt file rather than reasoning from scratch. They make the agent consistently apply senior-level patterns instead of ad-hoc reasoning.

---

## Bundled scripts

All scripts are deterministic. They do **not** execute target binaries, do **not** make network calls, and do **not** write outside the agent's working directory. Run them from this skill's root.

| Script | Purpose | When to use |
|--------|---------|-------------|
| `scripts/re_triage.py` | PE/ELF/Mach-O triage: type, arch, security features, entropy, suspicious strings, suspicious imports | Phase 2 for any binary |
| `scripts/re_disasm.py` | Capstone-based function-level disasm summary with call/jump targets | Phase 3 for RE deep dive |
| `scripts/swe_audit.py` | Multi-language codebase audit: complexity hotspots, dead code candidates, dependency direction, refactor priorities | Phase 2 & 3 for any SWE task |

Each script writes JSON to stdout (or `--out <file>`). The agent should call the script, read the JSON, and reason from it — not just rerun commands the user could run themselves. The value-add is interpretation, not invocation.

If a script's dependency is missing, the script should fail gracefully with a one-line message and the agent should fall back to inline shell commands (`file`, `strings`, `objdump`, `readelf` for RE; `rg`, `wc`, `git` for SWE). Don't block the workflow on a missing Python module.

---

## Output standards — the four report templates

Use these as the canonical output shapes. They are deliberately similar so the user learns one pattern.

- `assets/report_code_audit.md` — for SWE code review / refactoring engagements
- `assets/report_architecture.md` — for SWE architecture audits
- `assets/report_binary_analysis.md` — for RE binary analysis (non-malware)
- `assets/report_malware_triage.md` — for malware triage

The agent may abridge or extend, but **must** preserve: verdict, summary, evidence table, findings table with severities, limitations, and recommended next step.

---

## Cross-cutting principles

1. **Evidence over assertion.** Every finding cites the offset, line, function, or call site that proves it. "This looks fragile" is not a finding; "at line 47, `memcpy(dst, src, strlen(src)+1)` overflows the 16-byte stack buffer `dst` when `src` exceeds 15 bytes" is.

2. **Fitness over fashion.** The current architecture is one of several reasonable shapes. Don't recommend a rewrite unless there's a present defect that the rewrite fixes. Don't recommend a pattern unless the volatility it absorbs is real.

3. **Smallest safe next step.** Recommendations should be the minimum change that resolves the finding without creating new risk. Multi-step migrations only when the recommendation genuinely cannot be applied as one bounded change.

4. **Read before recommending.** Never recommend a fix for code you haven't read end-to-end. Never recommend a behavior change for a binary you've only triaged. State the limitation explicitly: "static-only — dynamic confirmation needed".

5. **Filter nitpicks.** Style, formatting, and personal preference are not findings. If the agent cannot articulate a concrete cost, the candidate is not a finding.

6. **Be honest about uncertainty.** Mark hypotheses as hypotheses. Mark `UNVERIFIED` when external docs would be needed to confirm. Use `BLOCKED` when required evidence is unavailable.

---

## Skill composition

This skill is designed to be **invoked by AI agents** that have file/bash/grep access. It does not need to be triggered by a human typing a magic phrase — agents can call into it when their workflow lands in SWE or RE territory. The agent's outer planner decides when to consult this skill; this skill's job is to guide the agent through the 5-phase loop once invoked.

When the agent needs to chain tasks: a malware triage finding ("sample is suspicious, imports look like a loader") naturally flows to the binary-analysis playbook for deeper static work, which may flow to the SWE playbook if the user asks to refactor the detection code that came out of it. The references are designed to compose — they don't duplicate each other.
