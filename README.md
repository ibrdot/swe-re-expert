# SWE + RE Expert — AI Agent Skill

> Expert-level Software Engineering + Reverse Engineering skill for AI agents (Claude, GLM, Codex, Cursor, etc.). Triggers whenever the agent must analyze, audit, refactor, or reverse-engineer code or binaries across C/C++/ASM, Python, Go, and Rust.

## What this skill does

A balanced expert across two complementary disciplines:

- **SWE** — read a codebase like a senior reviewer: map real architecture, find material defects, prioritize refactors, modernize, audit tests. Patterns over purity; fitness over fashion.
- **RE** — read a binary like a malware analyst: triage, disassemble, recover semantics, extract IOCs, map behavior, classify families.

Both halves share a single output discipline: deep, structured analysis reports where every finding cites evidence (offsets, paths, instructions, line numbers), classifies severity, and recommends the smallest safe next step.

## Skill structure

```
swe-re-expert/
├── SKILL.md                          # Main entry — 5-phase workflow + triggers
├── references/                       # Core playbooks (load on demand)
│   ├── swe-playbook.md               # Code review, refactoring, architecture audit
│   ├── binary-analysis.md           # Static → dynamic → semantic recovery
│   ├── malware-analysis.md          # Triage, IOCs, YARA, family classification
│   └── language-depth.md            # C/C++/ASM, Python, Go, Rust deep notes
├── prompts/                          # Expert reasoning patterns (the agent's "thinking tools")
│   ├── mental-models/               # 7 files: how senior RE/SWE approach problems
│   ├── re-playbooks/                # 11 files: per-language binary recovery, CTF, obfuscation, YARA, IOC
│   ├── swe-playbooks/               # 12 files: audit priorities, perf, security, tests, modernization, anti-patterns
│   └── meta/                        # 3 files: report discipline, uncertainty markers, evidence checklist
├── scripts/                          # Deterministic analysis scripts
│   ├── re_triage.py                 # PE/ELF/Mach-O triage (no execution)
│   ├── re_disasm.py                 # Capstone function-level disasm summary
│   └── swe_audit.py                 # Multi-lang codebase audit (complexity, dead code, deps)
├── assets/                           # Report templates (4 markdown files)
│   ├── report_binary_analysis.md
│   ├── report_malware_triage.md
│   ├── report_code_audit.md
│   └── report_architecture.md
└── evals/
    └── evals.json                    # Test cases for skill eval
```

**Total**: ~35 files of expert content. The agent loads only what each task needs.

## Install

### Claude Code / GLM Code / Codex / Cursor

Copy or symlink this folder to your agent's skills directory:

```bash
# Claude Code
cp -r swe-re-expert ~/.claude/skills/

# Or symlink
ln -s "$(pwd)/swe-re-expert" ~/.claude/skills/swe-re-expert
```

### Skill file (packaged)

If you have a `.skill` package, double-click to install, or:

```bash
# GLM Code / Claude Code via skill install
claude-skill install swe-re-expert.skill
```

## Trigger examples

The skill fires when the user (or another agent) asks about:

- "analyze this binary / .exe / .elf / .so / .dll / .dylib / firmware"
- "what does this function do" (with disasm or decompilation pasted)
- "reverse engineer this protocol / file format / sample"
- "malware analysis / triage this sample / extract IOCs / YARA"
- "code review / refactor this PR / audit this module"
- "architecture audit / dependency analysis / dead code"
- "find the vulnerability in this disassembly"
- "CTF rev / CTF pwn / crack this binary"
- pasted disassembly, Ghidra/IDA output, or hex dumps

## The 5-phase loop

```
1. SCOPE       — what is the user actually asking? what's the target? what's "done"?
2. TRIAGE      — fast first pass: identify, list, map. Cheap signals first.
3. DEEP DIVE   — the patient pass: read, trace, verify. Evidence over intuition.
4. ASSESS      — classify findings by severity and materiality. Filter nitpicks.
5. REPORT      — produce the structured analysis report. Recommend the smallest safe next step.
```

## Bundled scripts

| Script | Purpose |
|--------|---------|
| `scripts/re_triage.py` | PE/ELF/Mach-O triage: type, arch, security features, entropy, suspicious strings, suspicious imports |
| `scripts/re_disasm.py` | Capstone-based function-level disasm summary with call/jump targets |
| `scripts/swe_audit.py` | Multi-language codebase audit: complexity hotspots, dead code candidates, dependency direction |

All scripts are deterministic. They do not execute target binaries, do not make network calls, and do not write outside the agent's working directory.

## Languages covered

| Tier | Languages | What's covered |
|------|-----------|----------------|
| Tier 1 (deep) | C, C++, x86/x64/ARM assembly | ABI, calling conventions, idiom detection in disasm, memory model, UB, modern C++ |
| Tier 1 (deep) | Python, Go, Rust | Modern features, async correctness, ownership, GIL/goroutine model, toolchain |

Tier 2 (covered when surfaced): Java/JVM, JavaScript/TypeScript, C#/.NET.

## Output

The skill produces structured markdown reports using one of four templates depending on task type:

- `assets/report_code_audit.md` — SWE code review / refactoring engagements
- `assets/report_architecture.md` — SWE architecture audits
- `assets/report_binary_analysis.md` — RE binary analysis (non-malware)
- `assets/report_malware_triage.md` — Malware triage

Every report includes: verdict, summary, evidence table, findings table with severities, limitations, recommended next step.

## License

MIT — see [LICENSE](LICENSE).

## Author

ibrdot — ibrdot@outlook.com
