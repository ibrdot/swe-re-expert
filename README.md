<div align="center">

# SWE + RE Expert

### Code review meets binary analysis. Evidence, not guesswork.

An MIT-licensed AI agent skill for auditing source code, understanding binaries,
and turning observations into reports you can actually verify.

[Get started](docs/GETTING_STARTED.md) · [See a real example](examples/REPORT.md) · [Capabilities](docs/CAPABILITIES.md) · [Contribute](CONTRIBUTING.md)

**Built by ibrdot** · **Contact: [ibrdot@outlook.com](mailto:ibrdot@outlook.com)**

</div>

---

## Why this exists

A useful analysis should tell you **what was observed, where the evidence is,
what remains uncertain, and what to do next**. This skill gives your agent a
repeatable workflow for both sides of the problem: source code and compiled code.

- **Review source:** map a codebase, find complexity hotspots, examine dependencies,
  and prioritize changes instead of generating a wall of nitpicks.
- **Understand binaries:** collect static triage signals, inspect ELF/PE disassembly,
  and reason about behavior with offsets and instructions as evidence.
- **Make findings reviewable:** use four report templates with evidence, severity,
  limitations, and the smallest useful next step.

**It's a skill + supporting scripts, not an autonomous scanner or a replacement
for Ghidra, IDA, a debugger, or human verification.**

## Try it in 60 seconds

The source-code demo needs only Python 3.10+ and Git. No account or API key.

```sh
git clone https://github.com/ibrdot/swe-re-expert.git
cd swe-re-expert
python3 scripts/swe_audit.py --root examples/demo-project --all --out /tmp/demo-audit.json
python3 -m json.tool /tmp/demo-audit.json
```

You will get a file inventory, complexity hotspots, low-reference-count candidates,
and heuristic refactor priorities. Compare with the [committed output](examples/demo-audit.json)
and [annotated report](examples/REPORT.md). These signals are leads, not confirmed vulnerabilities.

### Use it with your agent

For an agent that supports a skill folder, load this repository's **[SKILL.md](SKILL.md)**
and follow its relative references. For Claude Code's user-level skill directory:

```sh
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/ibrdot/swe-re-expert.git "$HOME/.claude/skills/swe-re-expert"
```

If that destination already exists, update it rather than cloning over it.
For Codex, Cursor, or another agent, follow that product's supported instructions
for skill loading; this repo does not ship a universal installer or `.skill` release.

<details>
<summary><strong>Try these prompts</strong></summary>

```text
Use swe-re-expert to audit this repository. First map the architecture,
then identify the three highest-impact findings. Cite files and lines,
separate evidence from hypotheses, and recommend the smallest safe fix.
```

```text
Use swe-re-expert to triage this ELF binary without executing it.
Report hashes, sections, imports, and suspicious signals. Explain what
static analysis can and cannot establish. Do not infer intent from an API name.
```

```text
Explain this disassembly. Recover the calling convention, inputs,
control flow, and likely pseudocode. Cite instructions and flag ambiguity.
```

</details>

## What's included

| Component | What you get |
| --- | --- |
| [SKILL.md](SKILL.md) | Five-phase scope -> triage -> deep dive -> assess -> report workflow |
| [references/](references/) | SWE, binary analysis, malware analysis, and language playbooks |
| [prompts/](prompts/) | On-demand reasoning patterns and focused analysis playbooks |
| [scripts/](scripts/) | Three standalone Python tools producing JSON |
| [assets/](assets/) | Four Markdown report templates |
| [examples/](examples/) | Small offline fixture, actual output, and annotated report |
| [evals/](evals/) | Agent evaluation prompts, not a benchmark score |

## Binary analysis quick start

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt

# Linux example: static inspection of an existing system binary
python3 scripts/re_triage.py --file /bin/ls --all --out /tmp/triage.json
python3 scripts/re_disasm.py --file /bin/ls --entry --out /tmp/disasm.json
```

| Tool | Actual scope |
| --- | --- |
| `swe_audit.py` | Source inventory; Python AST complexity; heuristic complexity for other languages; reference-count and layer-dependency candidates |
| `re_triage.py` | PE/ELF static triage; partial Mach-O support through platform tools; hashes, strings, entropy, imports, security signals |
| `re_disasm.py` | Capstone-backed ELF/PE disassembly; function discovery depends on symbols/exports |

Linux tools `file` and `readelf` improve metadata/fallbacks. Mach-O paths use
`otool` on macOS. `ssdeep` is optional. See [capability limits](docs/CAPABILITIES.md).
The scripts do not execute the target; the broader playbooks discuss tools that
must be configured separately.

## The analysis loop

```text
SCOPE -> TRIAGE -> DEEP DIVE -> ASSESS -> REPORT
  |         |          |          |         |
question   map      evidence    priority   next step
```

Core guidance focuses on C/C++, assembly, Python, Go, and Rust. Other languages
have inventory/heuristic support or playbook coverage; that is not equivalent to
full semantic analysis of every language.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

CI runs regression tests and Linux binary smoke tests. Passing these tests does
not validate all agent-generated reports or prove cross-platform parity.
[Contributions](CONTRIBUTING.md) with a small reproducer are especially welcome.

## Help it reach the right people

If this saved you time, star the repository and share a concrete result: the
input, a useful finding, and how you verified it. Have a better workflow or a
counterexample? Open an issue. Reproducible examples beat hype.

[Launch copy and demo plan](docs/LAUNCH_KIT.md) · [Roadmap](ROADMAP.md) · [Security contact](SECURITY.md)

**Author:** ibrdot · **Email:** [ibrdot@outlook.com](mailto:ibrdot@outlook.com)
**License:** [MIT](LICENSE)
