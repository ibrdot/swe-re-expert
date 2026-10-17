<div align="center">

[![License guidance](https://img.shields.io/badge/license-per--guide-informational.svg)](THIRD_PARTY_NOTICES.md)
[![Guides](https://img.shields.io/badge/guides-941-blue.svg)](SKILLS.md)
[![API](https://img.shields.io/badge/API-v1-stable-success.svg)](https://ibrdot.github.io/ai-agent-skills/api/v1/skills.json)
[![GitHub stars](https://img.shields.io/github/stars/ibrdot/ai-agent-skills?style=social)](https://github.com/ibrdot/ai-agent-skills/stargazers)

</div>

# AI Agent Skills

A clean, searchable library of practical skill guides for AI agents.
Curated by **[MrTramble (@themrtramble)](https://github.com/themrtramble)** with the
repository maintainers. No contribution rankings or work-allocation claims.

[Browse the website](https://ibrdot.github.io/ai-agent-skills/) |
[Search skills](https://ibrdot.github.io/ai-agent-skills/skills.html) |
[Complete catalogue](SKILLS.md) | [Getting started](GETTING_STARTED.md)

## 📦 What's inside

**941 actual `SKILL.md` guides:** 39 suite guides, 864 community guides, and 38 engineering guides. The old 942 figure included a suite directory that was not a
separate `SKILL.md` guide. The generator now indexes actual guide files once each.

| Workflow | What you can find |
| --- | --- |
| Browser automation | Page inspection, browser workflows, accessibility, performance debugging |
| Engineering | Review, testing, specifications, architecture, debugging |
| Research and planning | Multi-source research and persistent task planning |
| Documents and media | PDFs, slides, document workflows, video and creative tools |
| Workspace | Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks guides |
| Integrations | Connector setup and app-specific workflow instructions |

Every entry in [SKILLS.md](SKILLS.md) includes its name, exact folder path,
purpose, and license guidance. The web explorer searches descriptions and paths,
filters by collection or category, copies file paths, and preserves filters in its URL.

## 🚀 Start with one guide

```sh
git clone https://github.com/ibrdot/ai-agent-skills.git
cd ai-agent-skills
cat planning-with-files/SKILL.md
```

Bring the selected guide into your agent's context using the mechanism your agent
supports. Skill files are instructions, not installed runtimes. Read their required
CLIs, packages, accounts, and MCP configuration before executing their workflows.
Never paste access tokens into issues, documentation, or public configuration.

See [GETTING_STARTED.md](GETTING_STARTED.md) for examples and setup expectations.

## 📁 Layout

```text
<skill>/SKILL.md                   Suite guides
chrome-devtools/skills/*/SKILL.md  Browser specialist guides
vendor/awesome-claude-skills/      Community collection, original notices preserved
vendor/mattpocock-skills/          Engineering collection, original notices preserved
docs/                             Static, light-only GitHub Pages site
tools/                            Deterministic catalogue generation and validation
SKILLS.md                         Complete generated guide catalogue
THIRD_PARTY_NOTICES.md             Source revisions and license guidance
```

## 🌐 Website and documentation

The website is deliberately pure-white and light-only, with a responsive layout,
subtle motion, keyboard search, reduced-motion support, accessible labels, and no
frontend framework or external font dependency.

```sh
python3 tools/build.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. Don't open the explorer through `file://`; its catalogue
loads through HTTP. See [DEPLOYMENT.md](DEPLOYMENT.md) for GitHub Pages setup,
admin-only settings, and troubleshooting. The existing `main` + `/docs` deployment
layout is preserved; no new workflow is needed to publish the static site.

## 🔑 Maintainers and licensing

[Maintainers](AUTHORS.md) are listed without contribution rankings.
Third-party content is organized under this project's UI but keeps its original
authorship and required notices. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and each guide's license. There is no root license covering all content; do not
assume every file is MIT or production-tested.

## 🧠 Automatic maintenance and API

Run `python3 tools/build.py` for one-command regeneration and validation. The
`Build and validate skill library` workflow runs on pushes to main, pull requests,
and manual dispatch. It checks JavaScript syntax, API integrity, add/remove
behavior, and deterministic generation. Main builds commit generated changes and
explicitly request a branch-based Pages rebuild because bot commits do not trigger
that deployment automatically. No personal access token is stored in this workflow.

- [API reference](https://ibrdot.github.io/ai-agent-skills/api.html)
- [Version 1 skill data](https://ibrdot.github.io/ai-agent-skills/api/v1/skills.json)
- [API maintenance guide](API.md)

Add or edit a `SKILL.md` and merge it. Counts, names, descriptions, paths, indexes,
and JSON endpoints regenerate together. Optional `category` frontmatter assigns a
suite guide's workflow category; unknown guides default to Utilities. Saved guides
are browser-local, and the explorer also offers sorting and a license-aware detail
panel. None of this auto-installs tools or pulls unreviewed upstream changes.

