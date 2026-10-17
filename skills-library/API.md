# Skill library API and maintenance

## Contract

The API is public, read-only static JSON served by GitHub Pages under `api/v1/`.
It needs no key and has no server-side search or write endpoints. Query strings
are not filters. Download `skills.json` and filter its `skills` array locally.

| File | Response |
| --- | --- |
| `index.json` | Discovery, version, revision, capabilities |
| `skills.json` | All metadata, counts, categories, stable keys, content hashes |
| `skills/{key}.json` | One guide's metadata |
| `stats.json` | Counts, categories, content revision |
| `categories.json` | Category names and counts |
| `collections.json` | Collection IDs, labels, counts |
| `schema.json` | JSON Schema for the skill collection response |

A key is the first 20 hex characters of SHA-256 of the relative SKILL.md path.
It is stable across content edits but changes on moves. `content_sha256` hashes
that guide's exact bytes, not every supporting file. The full revision hashes the
complete indexed metadata including those guide hashes. Consumers must tolerate
additional fields within v1. Breaking contracts belong in a new version directory.
CORS, caching, availability, and rate limits are controlled by the hosting service;
there are no custom authentication or rate-limiting services in this repository.

## Single source of truth

`python3 tools/build.py` runs indexing, Markdown generation, API generation, and
validation in order. Source `SKILL.md` files drive everything. Do not hand-edit
generated SKILLS.md, vendor/SKILL_INDEX.md, docs/data/, or docs/api/.

The compatibility `docs/data/skills.json` remains available for existing consumers.
The explorer uses v1. The API builder removes obsolete per-guide JSON files before
regenerating, so deleting a guide does not leave its old endpoint in the checkout.

## Changes without repeated hand edits

1. Add, update, or remove a skill guide. Preserve upstream license notices.
2. Optionally set `category: Research` (or another category) in a suite guide's frontmatter.
3. Commit and merge. Automation rebuilds and tests all generated content.
4. The main workflow pushes generated changes and requests Pages publication.
5. Check both workflow outcomes; a failed run is not a successful release.

GitHub Actions policy and branch protections can block publication. See
[DEPLOYMENT.md](DEPLOYMENT.md). This automation does not fetch upstream collections,
run their installation scripts, or claim that all third-party workflows work.

## Test locally

```sh
python3 tools/build.py
python3 -m unittest discover -s tests -v
node --check docs/assets/app.js
python3 -m http.server 8000 --directory docs
```

Regression tests check metadata parsing, counts, content hashes, per-guide API
parity, revision hashes, and automatic addition/deletion in an isolated fixture.
For browser UI smoke tests install `playwright`, then run `python3 tools/test_browser.py`.
The browser suite also runs in GitHub Actions on Chromium.
