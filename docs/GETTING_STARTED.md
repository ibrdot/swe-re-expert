# Getting started

## Source audit: no third-party packages

Clone the repository and run the included demo:

```sh
git clone https://github.com/ibrdot/swe-re-expert.git
cd swe-re-expert
python3 scripts/swe_audit.py --root examples/demo-project --all --out /tmp/demo-audit.json
python3 -m json.tool /tmp/demo-audit.json
```

Use Python 3.10 or later. `--root` can point outside the current working directory.
See the [demo report](../examples/REPORT.md) before interpreting heuristic results.

## Binary tools

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/re_triage.py --file /bin/ls --all --out /tmp/triage.json
python3 scripts/re_disasm.py --file /bin/ls --entry --out /tmp/disasm.json
```

The `/bin/ls` example is for Linux. Replace it with an existing file on your system.
`file`, `readelf`, and macOS `otool` provide platform-dependent metadata. The scripts
inspect files; they do not execute the analysis target. See [capabilities](CAPABILITIES.md).

## Load the skill and operating prompt

[SKILL.md](../SKILL.md) is the entry point. [prompt.txt](../prompt.txt) is the focused
operating prompt. Relative references and templates should remain alongside them.
For Claude Code, clone into `~/.claude/skills/swe-re-expert`. Other agents have their
own supported mechanisms; there is no universal installer shipped here.

Ask for a concrete outcome, target, and acceptance criteria. For example: "Audit
this repository and patch the highest-confidence correctness bug with a regression
test. Cite the relevant files and report what checks you ran."
