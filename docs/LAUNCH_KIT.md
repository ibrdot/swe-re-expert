# Launch kit

Prepared copy for the maintainer to review and publish. These posts have not been
sent to social networks, communities, or mailing lists by this repository update.
No fabricated stars, paid engagement, mass mentions, or unsolicited submissions.

## Positioning

**Code review meets binary analysis. Evidence, not guesswork.**

SWE + RE Expert is an MIT-licensed AI agent skill with source-audit and binary
analysis playbooks, three inspectable Python tools, and structured report templates.
The quick source demo needs no account or API key.

## Short launch post

I built SWE + RE Expert: an open-source skill that helps AI agents review source
code and investigate binaries with evidence-backed reports, not confident guesses.

Three Python tools, source + binary playbooks, and a runnable offline demo.
Start here: https://github.com/ibrdot/swe-re-expert

Try it on a small project and tell me where the workflow breaks.
Contact: ibrdot@outlook.com

## Technical community post

Title: Show HN: SWE + RE Expert - evidence-driven source review and binary analysis for AI agents

I wanted an agent workflow that distinguishes what a tool actually observed from
what the model inferred. This repo combines source-review and RE playbooks with
JSON-producing scripts and four report templates.

The source audit uses Python AST complexity and lightweight multi-language
heuristics. Binary tools cover ELF/PE triage and Capstone disassembly, with partial
Mach-O triage. It is not an autonomous vulnerability scanner or a decompiler.

There's a tiny offline demo, actual output, and an annotated explanation of what
those signals do and do not mean. I'd especially appreciate feedback on false
positives, report usefulness, and the first-run experience.

https://github.com/ibrdot/swe-re-expert

## 45-second demo storyboard

1. Show the problem: a finding with no evidence is hard to trust.
2. Clone the repo and run the exact source demo from the README.
3. Show one complexity lead, its source, and the difference between a signal and a finding.
4. Open SKILL.md and one report template.
5. End with a single request: try the fixture and report one confusing step.

## Distribution sequence

- Day 1: Publish a real screen recording and a specific technical post on your own account.
- Day 2: Share in one relevant community that permits project posts; tailor the example.
- Days 3-4: Respond to feedback, fix first-run issues, and publish a before/after case study.
- Days 5-7: Propose relevant directory entries only where submission rules and fit are clear.

Avoid identical cross-post floods. Do not submit without a working demo or claim
benchmark wins without measurements. Virality cannot be guaranteed.

## Measure usefulness

Record a baseline, then compare weekly: repository visits, clones, demo completions
where voluntarily reported, useful issues, merged contributions, and stars. GitHub
traffic access and retention depend on the repository owner's available analytics.
