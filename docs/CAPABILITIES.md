# Capabilities and limits

## Skill versus runtime

The skill provides workflows, prompts, and report discipline. It does not add tool
access to an agent, replace a reverse-engineering workstation, or guarantee that
an agent will make correct conclusions. Scripts provide inspectable JSON signals.

| Component | Supported approach | Important limit |
| --- | --- | --- |
| Source inventory | Extension-based, multi-language file counts | Not semantic language support |
| Python complexity | AST branch-count heuristic | Nested function counts can affect enclosing scores |
| Other complexity | Regex-based approximation | Comments and syntax can produce false positives |
| Dead-code candidates | Whole-word reference counts | Dynamic calls and external consumers are not resolved |
| Dependencies | Naming/layer heuristics | Not a compiler-grade import graph |
| Binary triage | PE/ELF parsing, strings, entropy, imports | Suspicious signals do not prove malicious behavior |
| Mach-O triage | Partial platform-tool support | Not feature parity with ELF/PE |
| Disassembly | ELF/PE with Capstone and parsers | Not a decompiler; stripped/packed samples lose coverage |
| Agent playbooks | Source review, debugging, RE reasoning | Results depend on model, tools, context, and verification |

## Evidence quality

Cite offsets, source lines, instructions, or commands. Distinguish observation
from inference. Do not label every weakness P0 or infer exploitability without
context. Evaluation prompts are scenarios, not measured benchmark results.

## Tested scope

CI exercises Linux ELF triage/disassembly and source-audit regression tests on
Python 3.11. It does not establish Windows/macOS parity or malware classification
accuracy. Report unsupported cases and failures through an issue with a reproducer.
