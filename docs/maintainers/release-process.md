# Release process

Read the [maintenance contract](maintenance-contract.md) for provenance, candidate validation and the full-release-alignment gate.

1. From clean current main, prepare truthful changelog notes and run `npm run release:prepare -- X.Y.Z`. The release PR alone refreshes distribution snapshots, Codex/Claude plugin mirrors, bundles, metadata and credits.
2. Review and merge the release PR through `merge:batch`. Exactly one owner-authored merged release PR must identify the version.
3. Check out the immutable merged release commit and run `npm run release:publish -- X.Y.Z`. Main may advance; the candidate must remain in protected-main ancestry and match its sealed tree.
4. Wait for `distribution-candidate.yml` to validate and build once, then test the packed product on Linux/Windows with Node 22/24. npm consumes that exact tarball, with explicit `latest` or `next`; it does not rebuild.
5. Dispatch Pages at the same tag with `deployment_target=release`. It verifies candidate provenance/digests and deploys the same site bytes.
6. Complete the mandatory full-release-alignment gate with `release:verify`, including fresh npm install/integrity, CI/CodeQL, live canonical site and legacy bridge. A public artifact mismatch or stale public surface keeps the public release incomplete.

Report personal environment alignment separately. Pin authorized existing MCP host entries to the exact runtime version and distinguish a standalone handshake from an actual running-client reload.

For compatible catalog-only changes, dispatch `catalog-distribution.yml` on protected main with a unique revision. Verify published `catalog-release.json`, archive SRI and live descriptor. This path does not bump/publish runtime npm. Legacy runtime releases retain embedded catalogs; explicit independent revisions require the compatible runtime described in the descriptor.
