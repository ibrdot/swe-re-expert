# Prompts — Expert Reasoning Files

This directory contains focused, expert-level reasoning patterns for SWE and RE work. Each file is a self-contained prompt-style checklist or mental model the agent loads when the task calls for it.

## Structure

```
prompts/
├── mental-models/         # Cross-cutting reasoning patterns
│   ├── re-thinking.md            # How a senior RE approaches a binary
│   ├── swe-thinking.md           # How a senior engineer reads a codebase
│   ├── vuln-hunting.md           # Where bugs live, by category
│   ├── refactor-decisions.md     # When to refactor, when to leave alone
│   ├── architecture-fitness.md   # Judging architecture without pattern bias
│   ├── static-vs-dynamic.md      # When each layer pays off
│   └── evidence-vs-assertion.md  # What counts as proof
├── re-playbooks/          # Binary-analysis-specific mental tools
│   ├── c-binary-recovery.md
│   ├── go-binary-recovery.md
│   ├── rust-binary-recovery.md
│   ├── ctf-rev-approach.md
│   ├── ctf-pwn-approach.md
│   ├── disasm-recovery.md
│   ├── anti-pattern-recognition.md
│   ├── anti-debug-evasion.md
│   ├── api-resolution.md
│   ├── crypto-identification.md
│   ├── packers-handling.md
│   ├── stl-recovery.md
│   ├── exploit-development.md
│   ├── malware-triage-mental-model.md
│   ├── yara-rule-design.md
│   ├── ioc-extraction-checklist.md
│   └── obfuscation-workarounds.md
├── swe-playbooks/         # Code-analysis mental tools
│   ├── code-audit-priorities.md
│   ├── perf-review-thinking.md
│   ├── security-review-thinking.md
│   ├── test-quality-review.md
│   ├── modernization-gates.md
│   ├── dependency-analysis.md
│   ├── dead-code-confirmation.md
│   ├── refactor-prioritization.md
│   ├── concurrency-bugs.md
│   ├── python-anti-patterns.md
│   ├── rust-anti-patterns.md
│   ├── go-anti-patterns.md
│   └── cpp-anti-patterns.md
└── meta/                  # Output discipline
    ├── report-writing-discipline.md
    ├── uncertainty-markers.md
    └── evidence-checklist.md
```

## Mental-models index — when each applies, the one-line takeaway

| File | Load when | One-line takeaway |
|------|-----------|-------------------|
| `re-thinking.md` | A binary hits the table and you don't know what it does | Static first, 60-80% of understanding from there; dynamic only to confirm/refute hypotheses. |
| `swe-thinking.md` | You're dropped into a codebase you didn't write | Map the executable behavior before reading the docs; the README lies, the code doesn't. |
| `vuln-hunting.md` | Looking for bugs in source or binary | Bugs cluster by class and by code region; chase clusters, not random lines. |
| `refactor-decisions.md` | Reviewing a PR or audit and considering "should I recommend this refactor?" | Default is "don't"; 4-gate test (defect? maintenance cost? acceptable alternative? bounded?). |
| `architecture-fitness.md` | Judging a system's shape, or about to drop a "should use DDD" finding | Pattern compliance is not a goal; only present defect + measurable cost + bounded change = finding. |
| `static-vs-dynamic.md` | Choosing analysis layer for a binary | Static is the default; escalate to dynamic with a specific question, never "let's see what it does." |
| `evidence-vs-assertion.md` | Writing the report, classifying claims | Every claim cites a byte (RE) or a line (SWE); un-citeable claims are hypotheses. |

## RE-playbook index — task-specific

| File | Load when | Key sections |
|------|-----------|---------------|
| `c-binary-recovery.md` | Stripped C/C++ ELF or PE on the table | RTTI recovery, vtable layout, libc symbol fingerprints |
| `go-binary-recovery.md` | Go binary, need function names | `pclntab` parsing, `gopclntab` version matrix, `buildinfo` extraction |
| `rust-binary-recovery.md` | Rust binary, need panic strings + module paths | `__rust_alloc` signature, panic table layout, demangle rules |
| `ctf-rev-approach.md` | CTF reverse-engineering challenge | 7-step solve loop, common challenge archetypes |
| `ctf-pwn-approach.md` | CTF pwn challenge | Mitigation checklist, libc leak recipes, ORW for seccomp |
| `disasm-recovery.md` | Disassembly is messy, need to recover function boundaries | Heuristics table, prologue/epilogue fingerprints |
| `anti-pattern-recognition.md` | Identifying what the binary is doing at a high level | Behavior fingerprint table (process injection, credential theft, C2, etc.) |
| `anti-debug-evasion.md` | Sample detects debugger / VM | 30+ technique catalog + 8 universal bypass patterns |
| `api-resolution.md` | Imports look empty / sample resolves APIs by hash | Hash-function recovery workflow, ROR-13/CRC32/FNV-1a inversion tables |
| `crypto-identification.md` | Need to identify crypto used by binary | Symmetric/asymmetric/KDF/MAC fingerprint tables, constant tables |
| `packers-handling.md` | Sample is packed (UPX/Themida/VMProtect/etc.) | Per-packer detection + unpacking workflow decision tree |
| `stl-recovery.md` | Need to recover C++ STL containers from a stripped binary | Itanium + MSVC ABI RTTI structure, vtable + type_info recovery |
| `exploit-development.md` | Building a PoC for a vulnerability class | 10 vuln classes, modern libc attack surfaces (post-2.34), pwntools patterns |
| `malware-triage-mental-model.md` | Unknown suspicious binary | 5-question triage, benign-binary fast path, family attribution ladder |
| `yara-rule-design.md` | Writing YARA rules from sample set | 4-criterion rule quality test, false-positive discipline |
| `ioc-extraction-checklist.md` | Extracting indicators from sample | 8 IOC classes with extraction commands, confidence scoring |
| `obfusc-workarounds.md` | Code is obfuscated, need to recover original logic | Per-technique workaround (control-flow flattening, MBA, opaque predicates) |

## SWE-playbook index — task-specific

| File | Load when | Key sections |
|------|-----------|---------------|
| `code-audit-priorities.md` | Reviewing a codebase for issues | P0-P3 priority matrix, ROI ranking |
| `perf-review-thinking.md` | Performance review | Where perf lives (algorithm, allocation, contention, IO), profiling discipline |
| `security-review-thinking.md` | Security review | Threat-model-first review, OWASP-mapped bug classes, exploitability assessment |
| `test-quality-review.md` | Reviewing test suite quality | 5 axes (coverage, behavior, isolation, determinism, mutation score) |
| `modernization-gates.md` | Considering a framework/language version upgrade | 4-gate justification (defect fix? capability? bounded? reversible?) |
| `dependency-analysis.md` | Reviewing dependency tree | License, vulnerability, maintenance status, transitive pinning audit |
| `dead-code-confirmation.md` | Identifying dead code | 5-gate confirmation (grep / alias / re-export / reflection / runtime) |
| `refactor-prioritization.md` | Prioritizing refactor backlog | Impact × ease × risk matrix, sequencing by prerequisite |
| `concurrency-bugs.md` | Auditing concurrent code | 7 bug classes (race/atomicity/deadlock/livelock/starvation/order/amplified), per-language triggers |
| `python-anti-patterns.md` | Python codebase audit | Mutable default args, late-binding closures, GIL pitfalls, asyncio footguns |
| `rust-anti-patterns.md` | Rust codebase audit | `unwrap` vs `expect`, unsafe discipline, `Box<dyn Error>` anti-pattern, async pitfalls |
| `go-anti-patterns.md` | Go codebase audit | Loop variable capture, nil-channel, goroutine leak, `interface{}` overuse |
| `cpp-anti-patterns.md` | C++ codebase audit | RAII violations, virtual destructors, smart pointer misuse, UB catalog |

## Meta index — output discipline

| File | Load when | Key sections |
|------|-----------|---------------|
| `report-writing-discipline.md` | Before finalizing any report | Consequence-first ordering, no decorative citations, no lecture mode |
| `uncertainty-markers.md` | Mark claims you can't fully verify | HYPOTHESIS / SUSPECTED / UNVERIFIED / BLOCKED / INCONCLUSIVE — definitions + when each |
| `evidence-checklist.md` | Self-check before submitting report | 12-point checklist, "show me the bytes / lines" gate |

## How to use — combination patterns

When the agent is working on a task, it loads the relevant prompts as needed — never all at once. The agent's outer planner decides which prompts to consult based on the task type. Below are the most common combinations.

### Pattern A — Triage a suspicious binary (unknown family)

Load in order:
1. `mental-models/re-thinking.md` — outer reasoning frame
2. `re-playbooks/malware-triage-mental-model.md` — 5-question triage loop
3. `re-playbooks/anti-pattern-recognition.md` — behavior fingerprint table to identify what category of activity is present
4. `re-playbooks/ioc-extraction-checklist.md` — extract indicators as you go
5. `meta/evidence-checklist.md` — before finalizing, verify every claim cites a byte

If packed, insert before step 2: `re-playbooks/packers-handling.md`.
If anti-debug detected, insert before step 4: `re-playbooks/anti-debug-evasion.md`.
If empty IAT, insert before step 4: `re-playbooks/api-resolution.md`.

### Pattern B — RE a benign stripped binary

Load in order:
1. `mental-models/re-thinking.md`
2. `mental-models/static-vs-dynamic.md` — confirm static is sufficient (benign binaries usually are)
3. Language-specific playbook: `c-binary-recovery.md` / `go-binary-recovery.md` / `rust-binary-recovery.md`
4. `re-playbooks/disasm-recovery.md` — if function boundaries are messy
5. `re-playbooks/stl-recovery.md` — if C++ STL containers in play

### Pattern C — CTF rev challenge

Load in order:
1. `re-playbooks/ctf-rev-approach.md` — 7-step solve loop
2. `mental-models/re-thinking.md` — framing
3. Language-specific playbook (most CTF rev is C/C++ or Rust)
4. `re-playbooks/obfuscation-workarounds.md` — if obfuscation detected
5. `re-playbooks/crypto-identification.md` — if crypto primitives in play

### Pattern D — CTF pwn challenge

Load in order:
1. `re-playbooks/ctf-pwn-approach.md` — outer frame, mitigation checklist
2. `re-playbooks/exploit-development.md` — per-vuln-class recipes
3. `re-playbooks/disasm-recovery.md` — for reading the target
4. `mental-models/vuln-hunting.md` — for finding the bug class

### Pattern E — Codebase audit (multi-language)

Load in order:
1. `mental-models/swe-thinking.md` — how to read a codebase you didn't write
2. `swe-playbooks/code-audit-priorities.md` — what to look for first
3. Language-specific anti-patterns: `python-anti-patterns.md` / `rust-anti-patterns.md` / `go-anti-patterns.md` / `cpp-anti-patterns.md`
4. `swe-playbooks/security-review-thinking.md` — if security is in scope
5. `swe-playbooks/dead-code-confirmation.md` — if dead code is flagged
6. `meta/evidence-checklist.md` — every claim cites a line

### Pattern F — Performance review

Load in order:
1. `swe-playbooks/perf-review-thinking.md` — outer frame
2. Language-specific anti-patterns (perf issues are language-specific)
3. `swe-playbooks/concurrency-bugs.md` — if contention suspected
4. `meta/report-writing-discipline.md` — consequence-first findings

### Pattern G — Architecture review

Load in order:
1. `mental-models/architecture-fitness.md` — outer frame, 5 questions
2. `swe-playbooks/dependency-analysis.md` — map the actual dependency graph
3. `swe-playbooks/modernization-gates.md` — if modernization being considered
4. `mental-models/refactor-decisions.md` — for each refactor candidate
5. `meta/evidence-checklist.md` — every architecture claim cites a concrete cost at the team's scale

### Pattern H — Refactor proposal review

Load in order:
1. `mental-models/refactor-decisions.md` — 4-gate test
2. `swe-playbooks/refactor-prioritization.md` — impact × ease × risk matrix
3. `swe-playbooks/test-quality-review.md` — verify tests exist before refactor
4. Language-specific anti-patterns — to ensure the refactor doesn't introduce a known anti-pattern
5. `meta/uncertainty-markers.md` — mark parts of the refactor plan that are hypotheses

### Pattern I — Test suite review

Load in order:
1. `swe-playbooks/test-quality-review.md` — 5 axes
2. `mental-models/evidence-vs-assertion.md` — every test claim cites a line
3. Language-specific anti-patterns (e.g., Python tests with `pytest` fixtures, Rust with `tokio::test`)

### Pattern J — Generate YARA rules from sample set

Load in order:
1. `re-playbooks/yara-rule-design.md` — 4-criterion rule quality test
2. `re-playbooks/ioc-extraction-checklist.md` — extract strings + structs first
3. `re-playbooks/crypto-identification.md` — if crypto constants present (high-value YARA material)
4. `meta/evidence-checklist.md` — every byte/offset claim verifiable

### Pattern K — Concurrency audit

Load in order:
1. `swe-playbooks/concurrency-bugs.md` — 7 bug classes
2. Language-specific anti-patterns (Python asyncio / Go channels / Rust Send-Sync / C++ atomics)
3. `mental-models/vuln-hunting.md` — to map the bug classes to specific code patterns
4. `meta/report-writing-discipline.md` — concurrency bugs need a concrete reproduction, not just "this might race"

## Cross-reference matrix — mental models ↔ playbooks

| Mental model | Pairs with these playbooks |
|--------------|----------------------------|
| `re-thinking.md` | All RE playbooks (outer frame) |
| `swe-thinking.md` | All SWE playbooks (outer frame) |
| `vuln-hunting.md` | `exploit-development.md`, `security-review-thinking.md`, `concurrency-bugs.md`, language-specific anti-patterns |
| `refactor-decisions.md` | `refactor-prioritization.md`, `modernization-gates.md`, `dead-code-confirmation.md`, `test-quality-review.md` |
| `architecture-fitness.md` | `dependency-analysis.md`, `modernization-gates.md`, `code-audit-priorities.md` |
| `static-vs-dynamic.md` | `packers-handling.md`, `anti-debug-evasion.md`, `obfuscation-workarounds.md`, `crypto-identification.md` |
| `evidence-vs-assertion.md` | All playbooks (universal output discipline) |

## The "do not load everything" rule

Loading every prompt before starting a task is a quality-failure mode. The agent loses the ability to prioritize; every signal becomes equally weighted; the report becomes a survey rather than a finding.

The correct pattern:
1. Read the user's request once.
2. Pick the outer mental model (re-thinking or swe-thinking).
3. Pick 1-2 playbooks specific to the task.
4. Start work. Load additional playbooks only if the task reveals a need (e.g., started triage, found packer, now load `packers-handling.md`).

The prompts are tools, not a syllabus. You don't read the whole toolbox; you grab the wrench when you see a bolt.

## The "meta is always loaded last" rule

`meta/` files (`report-writing-discipline.md`, `uncertainty-markers.md`, `evidence-checklist.md`) are output-discipline files. They apply to every report. Load them after analysis is complete, before writing the report — to discipline the output, not to drive the analysis.

Loading meta first leads to over-cautious analysis. Loading meta last leads to disciplined reporting of bold analysis. The latter is what you want.

## Output discipline — universal reminders

Regardless of which playbook was active, every report must:

- Cite a byte (RE) or a file:line (SWE) for every claim
- Use the uncertainty markers (`HYPOTHESIS`, `SUSPECTED`, `UNVERIFIED`, `BLOCKED`, `INCONCLUSIVE`) for claims without proof
- Lead with consequence, not with evidence ("This performs process injection (P0). Evidence: ..." — not "This calls CreateRemoteThread. ...")
- Have a severity classification per finding (P0/P1/P2/P3 or equivalent)
- Have a bounded recommendation per finding (what to change, where, how big, how risky)
- Reject its own findings before submitting (try to refute; if you can, fix; if you can't, ship)
- End naturally — no "End of report" markers, no meta-commentary

If any of these are missing, the report is a draft, not a deliverable.

## Reading order — for a new agent loading this skill for the first time

If you've never loaded this skill before and want to internalize it before working:

1. `mental-models/swe-thinking.md` and `mental-models/re-thinking.md` — the two outer frames
2. `mental-models/evidence-vs-assertion.md` — the discipline that separates junior from senior
3. `mental-models/static-vs-dynamic.md` — for RE work specifically
4. `mental-models/refactor-decisions.md` and `mental-models/architecture-fitness.md` — for SWE work specifically
5. `meta/evidence-checklist.md` and `meta/uncertainty-markers.md` — output discipline
6. Two or three playbooks relevant to the immediate task

This is enough to start. The remaining playbooks load on-demand as the task reveals needs.

## File length expectations

Each file is sized for a single load context:

- `mental-models/`: 200-400 lines each — outer frames, read in full
- `re-playbooks/` and `swe-playbooks/`: 300-700 lines each — task-specific, read in full when loaded
- `meta/`: 100-250 lines each — short, dense, read in full
- This README: ~350 lines — index + combination patterns, scan once

If a file grows past ~800 lines, split it. The whole point of the prompts/ directory is that each file is one mental context — one thing the agent holds in mind at a time. Loading a 2000-line file is the same as loading nothing, because the agent can't hold it all.

## Final hook

> "Every prompt in this directory exists to make the agent's output more correct, more concrete, and more useful to the reader. If a prompt doesn't serve that goal — delete it. If a prompt does serve it — make sure the agent loads it at the right moment, not all moments."

## Using this library with the wider skill ecosystem

For adjacent workflows outside software engineering and reverse engineering,
browse **[ai-agent-skills](https://github.com/ibrdot/ai-agent-skills)**: 941 indexed
guides with names, paths, purposes, and licenses, plus a searchable explorer and
read-only JSON API. Keep the referenced guides together with these prompts so
relative links resolve. Questions or improvements: [ibrdot@outlook.com](mailto:ibrdot@outlook.com).
