# Getting started

## What a skill is

A `SKILL.md` is a guide that tells an AI agent when and how to perform a workflow.
It does not automatically install packages, authorize accounts, or enable a tool.
Some folders also contain scripts, references, templates, fonts, or license files.

## Find the right guide

1. Open the [explorer](https://ibrdot.github.io/ai-agent-skills/skills.html).
2. Search for a task such as `code review`, `PDF`, or `calendar`.
3. Filter by collection or category. Copy the exact path or open the guide.
4. Read the description, prerequisites, and license before use.
5. Load only relevant instructions into your agent, using its supported setup.

The offline-friendly [Markdown catalogue](SKILLS.md) lists every guide and path.
Duplicate names can be legitimate across collections; file paths are unique IDs.

## Example: persistent planning

```sh
git clone https://github.com/ibrdot/ai-agent-skills.git
cd ai-agent-skills
cat planning-with-files/SKILL.md
```

Ask your agent to follow that guide for a multi-step project. Inspect any suggested
scripts before running them. It may create planning files according to its instructions.

## Example: browser debugging

Read `chrome-devtools/skills/chrome-devtools/SKILL.md` and the suite's setup
instructions. Install and configure only its required runtime. Browser access and
MCP availability depend on your agent environment, not on cloning this library.

## Example: app integration

Search for the app and read its connector guide. Confirm that your agent actually
supports the named integration and authenticate using its secure connection flow.
Do not copy credentials into skill files or enable all integrations at once.

## Keeping the library current

Review upstream changes and license terms before replacing vendored files. Regenerate
catalogues after any addition, removal, or description update. See
[vendor/README.md](vendor/README.md) for a safe update checklist.
