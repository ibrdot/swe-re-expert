# AAS maintenance

Invoke the canonical [maintainer skill](../skills/antigravity-maintainer-batch-release/SKILL.md) before triage or mutation. Follow the [maintenance contract](../docs/maintainers/maintenance-contract.md) for the full sequence and [component validation](../docs/maintainers/component-validation.md) for test selection.

## Current-base guard

Mandatory tools must exist on the current task base. Never import missing procedures from another branch, worktree, stash, installed copy, or historical commit. Read the exact-base instructions after creating an isolated checkout. Preserve unrelated dirty work.

## Invariants

- Main is PR-only with strict protection and administrator enforcement. `merge:batch` is the only fork-run approval and merge authority. No admin bypass or auto-merge.
- Review complete `skills/<skill-id>/**` trees. Safe analysis can precede review; merge requires real Tessl review or exact-head maintainer attestation. Private authenticated receipts reuse only unchanged content and context.
- Source PRs exclude generated snapshots. Main CI validates ephemeral state; distribution snapshots, mirrors and generated contributor credits refresh only in the release PR.
- Unknown/policy/shared changes receive full checks. Missing or skipped required evidence cannot pass.
- Use the scripted protected release path, build the immutable candidate once, publish its exact tested bytes, and run the mandatory full-release-alignment gate. Main may advance beyond the released commit.
- Catalog-only revisions are independently pinned and compatible with an explicit runtime; no runtime bump is required.
- Report public completion and personal environment alignment separately. Measure real whole-cycle times, not inferred percentage gains.

Warning limits remain in `tools/config/validation-budget.json`; never raise the budget to hide regressions.
