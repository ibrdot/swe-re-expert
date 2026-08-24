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
│   ├── python-anti-patterns.md
│   ├── rust-anti-patterns.md
│   ├── go-anti-patterns.md
│   └── cpp-anti-patterns.md
└── meta/                  # Output discipline
    ├── report-writing-discipline.md
    ├── uncertainty-markers.md
    └── evidence-checklist.md
```

## How to use

When the agent is working on a task, it loads the relevant prompts as needed — never all at once. The agent's outer planner decides which prompts to consult based on the task type:

- User gave a binary → load `mental-models/re-thinking.md` + the language-specific playbook
- User gave a suspicious sample → load `re-playbooks/malware-triage-mental-model.md` + `ioc-extraction-checklist.md`
- User asks for PR review → load `mental-models/swe-thinking.md` + the relevant language anti-patterns file
- User asks for architecture review → load `mental-models/architecture-fitness.md` + `swe-playbooks/dependency-analysis.md`
- User asks about performance → load `swe-playbooks/perf-review-thinking.md`
- User asks about tests → load `swe-playbooks/test-quality-review.md`
- CTF challenge → load `re-playbooks/ctf-rev-approach.md` or `ctf-pwn-approach.md`
- Generating YARA → load `re-playbooks/yara-rule-design.md`

Each file is 50-200 lines of dense, expert content. No fluff, no policy, no legal/refuse language — just the reasoning patterns that make the agent an expert.
