# Generated state and CI failures

Follow the [maintenance contract](maintenance-contract.md). Ordinary source main intentionally retains the last distribution snapshots; a diff after `npm run chain` in a scratch checkout is not an instruction to open `automation/canonical-repo-state`.

For source checks, regenerate ephemeral state before reference/catalog tests. Fix source or generator defects in a source PR. For release checks, repair the prepared release PR until snapshots are reproducible and seal the tree. Publication verifies the immutable candidate and never rebuilds changed bytes. Never push generated state directly to main or bypass protection.
