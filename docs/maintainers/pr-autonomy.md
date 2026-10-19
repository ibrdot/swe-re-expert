# PR automation boundaries

Follow the [maintenance contract](maintenance-contract.md). `merge:batch` is the sole authority for fork-run approval and merge; reports and timing telemetry remain advisory.

The protected-base classifier controls fork safety. `validation_profile` selects the component plan; `impact_profile` remains shadow-only. `source-validation` generates the required preview once and `artifact-preview` verifies its exact-head manifest. Main CI validates ephemeral source state, with no ordinary canonical PR.

Review full `skills/<skill-id>/**` trees. Private authenticated receipts can reuse an identical complete nearest skill-directory fingerprint and context, never a guessed similarity score. Final authorization is for the current full head. The helper does not rewrite PR metadata and does not retry base drift automatically. Sensitive changes retain owner-only authorization.

Protected required checks cannot be skipped, inferred or replaced by local scores. Workflows have no main push/admin bypass. Source completion and release completion are separate: publication consumes a complete trusted immutable candidate. Client reload status is separate from public completion.
