# Merging PRs

Use the canonical maintainer skill and [maintenance contract](maintenance-contract.md). No local-integration exception: source PRs merge through `npm run merge:batch` with strict up-to-date protection, administrator enforcement and current required checks.

Review the complete `skills/<skill-id>/**` subtree before exact-head attestation. Safe analysis may precede semantic review; it does not authorize merge. Signed private receipts may reuse only identical content and evaluator context. Do not use admin bypass, raw merge commands or GitHub auto-merge. Source PRs exclude generated distribution snapshots; the protected release PR refreshes them together.
