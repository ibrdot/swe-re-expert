# Agent setup and catalog description review — 2026-10-12

## Scope and base

This source batch starts from protected main `88a8ccb6a4973c6f68ffbff0a744d2f8df66edd6` (19.5.0). It completes the Codex and Claude Code setup guides, corrects 18 exact template descriptions, and fixes skill-page reading and return navigation. It does not add skill IDs, change selection policy, release a package, or configure the maintainer's real clients.

The remaining open PR #1863 changes a different skill's provenance URL and has failed changed-skill evidence. It is outside this batch and is not merged or repaired here. Issues were empty; CodeQL, Dependabot and secret-scanning open-alert lists were empty at inspection. Discussion titles were inspected for overlapping onboarding work; none was modified.

## Skill review

Each of the 18 affected canonical trees contains only its regular, non-executable SKILL.md. The complete instructions were inspected for task scope, required context, outputs, ethical guardrails, examples and limitations. Replacement descriptions state those actual tasks, include invocation context, remain below 200 characters, and make no efficacy or safety-certification claim. Existing body text, provenance, dates and declared risk values are preserved. The validation contract now rejects empty descriptions and the exact known template text, with case, whitespace and dash variants; legitimate descriptions about templates remain allowed.

The maintainer skill's complete tree (SKILL.md plus agents/openai.yaml) was also inspected. Its single added rule documents the existing validator's new deterministic description check. Maintenance documentation and negative regressions are updated in the same source PR. No merge, CI or branch-protection bypass is added.

This is a scoped maintainer content review, not a Tessl result or a scientific verification of the legacy psychological citations. Generic community provenance, broad inherited limitations and efficacy claims in historical bodies remain corpus debt. The official review outcome and exact-head attestation are checked at merge time.

| Canonical skill | Reviewed SKILL.md SHA-256 |
| --- | --- |
| `awareness-stage-mapper` | `8df49ce31ed2e92e5a29b31102e09bf6890b7985d3c47fc79399fd314bbb236d` |
| `brand-perception-psychologist` | `9a26b3e761447e7aa9b84a738ffbd15b516d69aad5c749e94333758adf14c2f7` |
| `copywriting-psychologist` | `093ceff2b7dbd71964ed8201302165d84f716dff57211ae4325301721877087e` |
| `customer-psychographic-profiler` | `e94948fde8971e81343ce87651792d8c2b6d121121639604c558e6fec203ffba` |
| `emotional-arc-designer` | `1cd2ad5da122da9d0db1681cd4dec46be40c85b00a1010cedde86a8647d31456` |
| `headline-psychologist` | `781f616a00c4e886ba51170406aabc00a839b8dfcd412ad430ac0e8a9dbef7ef` |
| `identity-mirror` | `c6a347144ce8d29e3907993156b6401ed76b831775aebb34808b337be1ee1c4f` |
| `loss-aversion-designer` | `acf928606c4ddd2fad90a52f5eed14ba9292ead4e64307655a41aef0a9d4d4fe` |
| `objection-preemptor` | `830d7de1cd7cf197baa5f4fcc550286c11ffd0887e9ec509f68d36556986b120` |
| `pitch-psychologist` | `5b001439b168100267ee9d693a78d1287d0ff6c4600f9deeb0e6942969cc0cec` |
| `price-psychology-strategist` | `ed8aa285238001492cf4af7e2c54274e55a629630cbbcfbc60e00fbb01cb9468` |
| `scarcity-urgency-psychologist` | `9aeceb6850417d771add2b2e5bb9b194f4b0af4047b9d99c3a6e260db7c9d497` |
| `sequence-psychologist` | `b40a67ef4cc4eb221a959660509c9e0751aa8147dd438f962c0c4f0b90e1ace6` |
| `social-proof-architect` | `2fc14e98e886d23137e2e193ee0d9af053829b2c25e7ebe8a6fe1a5968c79131` |
| `subject-line-psychologist` | `93fe26b1f373f6cb97691b9463c5908b5d13d7d1f49d32d42a41398c67bdec38` |
| `trust-calibrator` | `6a74d919250aad10bc33d17ec03167088a99a04c064c37c2819412a103041c2b` |
| `ux-persuasion-engineer` | `8cbd24d667c4e53368554b876dc4ade20bc7a1cd6a1babb18543eb73ca99ad14` |
| `visual-emotion-engineer` | `d6731abd61ae3189e162aa9aaa42d564c50c6790c24ba60291f009f3cf3ccd4d` |

## Setup and page behavior

Both guides now contain prerequisites, exact-version configuration preview, digest-bound approval with backup paths, a client connection check, a full-capability selection request, manifest persistence, validation, plan preview and a separate direct-installer handoff. Their four command blocks come from the same renderer in sync_repo_metadata.py and remain version-aligned and idempotent. Codex uses the current .agents/skills project destination; Claude uses .claude/skills. The README, Getting Started and FAQ point to these complete guides.

Skill instructions precede related topics and similar skills. Copy SKILL.md returns the original complete Markdown file; the optional prompt context remains attached only to Copy @Skill. Catalog query and filters travel through card, workflow, discovery, shortlist and similar-skill navigation using validated local route state; direct visits fall back to /core. Public topic prose uses the editorial summary rather than internal primaryIntent.

## Observed validation

- chain and standard validation: 2,687 skills, no errors; warning budget 0/0.
- references, documentation security and changed-source lint passed; root dependency audit found zero vulnerabilities.
- Full unsharded repository suite: 132 local test groups passed; optional network suite was not run.
- Web suite: 312 tests across 53 files, coverage thresholds passed; typecheck, production build/prerender and 27-guide verification passed.
- New regressions cover empty/template descriptions, valid template-related prose, shared command version refresh, original-file copying, content ordering, catalog-return preservation and rejection of invalid return routes.
- Browser check opened awareness-stage-mapper from its filtered catalog, observed the corrected description and Copy SKILL.md label, and returned to the same query.
- Published 19.5.0 smoke used isolated user-scoped Codex TOML and Claude JSON fixtures: preview left each file unchanged, approved configuration preserved unrelated settings and created backups, actual stdio exposed nine tools, read systematic-debugging, composed a schema 2 manifest, validated it and planned without materializing target skills. install-preview returned only a dry-run command. This is CLI/direct-stdio proof, not a native Codex/Claude agent session or a semantic selection benchmark.

Derived catalogs and plugin mirrors were regenerated as validation evidence and are excluded from the source commit. The protected canonical-sync lane owns their publication after source merge.
