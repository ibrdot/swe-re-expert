# Modernization Gates — When (and When Not) to Upgrade

Modernization is the most over-recommended refactor. "We should use X" is almost never a finding. "The current state has a defect that X fixes" sometimes is.

## The 4-gate test for modernization

Recommend modernization only when all four pass:

### Gate 1: Is there a present defect?

The current tool / version / pattern has a bug, security issue, perf problem, or maintainability cost that the modernization fixes.

❌ "We should use Python 3.13 — better error messages" — no defect
✅ "We're hitting GIL contention at scale; Python 3.13 free-threaded build would unblock" — concrete defect

### Gate 2: Does the modernization actually fix it?

Verify the modernization addresses the specific defect. Don't assume.

- Read the modernization's docs / changelog
- Verify the feature is in the version you'd upgrade to
- Check for known regressions / breaking changes that affect your codebase

### Gate 3: Is the migration bounded?

- One PR / sprint / quarter (max)
- Reversible (can roll back if it breaks)
- Doesn't require coordinated multi-team changes

If the migration is multi-quarter with no rollback, it's an architecture decision, not a modernization recommendation.

### Gate 4: Is the cost < the benefit?

Cost:
- Engineering time (migration + regression testing)
- Risk (production incidents during migration)
- Tooling disruption (CI changes, deploys)
- Learning curve (team unfamiliar with new tool)

Benefit:
- Defect fixed (concrete)
- Capability enabled (specific)
- Maintenance cost removed (measurable)

If cost > benefit, defer.

## Modernization candidates by language

### Python

| Modernization | When justified | When NOT justified |
|---------------|----------------|---------------------|
| Python 3.13 | GIL contention at scale (free-threaded build), REPL improvements | "Newer is better" |
| Type hints | Catch type bugs at static analysis time | "PEP 484 says we should" |
| `pydantic v2` | Runtime validation; v1 perf issues | "v2 is the new version" |
| `ruff` (replaces flake8+black+isort) | Faster linting, single tool | "ruff is the cool new thing" |
| `uv` (replaces pip) | Faster installs, deterministic | Team already standardized on pip |
| `asyncio.TaskGroup` (3.11+) | Structured concurrency, cleaner error handling | "Async looks nicer with TaskGroup" |
| `dataclasses` | Immutable value objects, less boilerplate | "Classical classes feel dated" |

### Go

| Modernization | When justified | When NOT justified |
|---------------|----------------|---------------------|
| Generics (1.18+) | Replaces 6+ type-assert branches with single parametric code | "We should use generics everywhere" |
| `slog` (1.21+) | Structured logging; replacing ad-hoc log calls | "log package is dated" |
| `errors.Join` (1.20+) | Need to wrap multiple errors | "Looks cleaner" |
| `maps`/`slices` packages (1.21+) | Replace bespoke helpers with stdlib | "stdlib has them now" |
| `range-over-int` (1.22+) | Cleaner range syntax | "Old code looks dated" |

### Rust

| Modernization | When justified | When NOT justified |
|---------------|----------------|---------------------|
| Edition 2024 | `let-else` would replace 5+ `if let` + early return | "Edition 2024 is the new one" |
| `async fn` in traits | Removes `async_trait` crate dependency | "Looks cleaner" |
| `let-chains` | Cleaner conditionals | "Modern feature" |
| `Result::Err` inspection | Replaces verbose `match` with one arm | "Idiomatic" |
| Clippy pedantic | Catches real bugs in `unsafe` code | "Clippy says" |
| `cargo-miri` for unsafe | UB detection in unsafe blocks | "Best practice" |

### C / C++

| Modernization | When justified | When NOT justified |
|---------------|----------------|---------------------|
| C++20/23 features | `std::span` replaces raw pointer + size pairs; concepts remove SFINAE | "Newer standard" |
| `std::filesystem` | Cross-platform path handling | "Boost is dated" |
| Smart pointers | Replaces manual new/delete | "Old style" |
| Modules | Faster builds (measurable) | "Modules are the future" |
| `constexpr` more broadly | Compile-time validation that catches bugs | "Modern" |
| `clang-tidy modernize` | Mechanical upgrade with no behavior change | "For consistency" |

## The "toolchain constraint" rule

Before recommending a version / feature upgrade:

1. **Verify the team's toolchain supports it.** Check:
   - Compiler / interpreter version in CI
   - Deployment target OS / runtime version
   - Dependency compatibility (e.g., does pydantic v2 work with this FastAPI version?)
2. **Verify the team can upgrade the toolchain.** Sometimes the toolchain is locked (embedded, regulated industries, customer constraints).
3. **Estimate the toolchain upgrade cost separately.** "Upgrade to Python 3.13" might require upgrading the base Docker image, updating CI runners, updating linters, updating deployment scripts. That's a separate project.

If the toolchain can't be upgraded, the modernization recommendation is moot. Mark it as a future opportunity, not a current finding.

## The "regression risk" rule

Every modernization has regression risk:

- API behavior changes (subtle)
- Performance characteristics change (faster or slower, in different cases)
- Bug-for-bug compatibility (some bugs become features)

Mitigate:
- **Characterization tests first** — capture current behavior, even bugs
- **Migration in stages** — one module at a time, with monitoring
- **Rollback path** — feature flags, version-pinned deps
- **Diff testing** — for behavioral changes, run old and new in parallel, diff outputs

Without these, the modernization is high-risk. Mention the risk in the report.

## The "schedule the migration" rule

If modernization passes all gates but is multi-PR:

1. Sequence the migration by prerequisite
2. Each step is bounded (one PR)
3. Each step is reversible (rollback path)
4. Each step has tests
5. Document the migration plan in the report

Example migration plan for "extract domain layer from controllers":

```
Phase 1 (1 PR): Add `domain/` package. Move pure logic functions there. Controllers call them. (~1 day, ~200 LOC)
Phase 2 (1 PR): Invert the imports — controllers import domain, not vice versa. (~1 day, ~50 LOC)
Phase 3 (1 PR): Remove the now-unused controller imports from domain. Verify no cycle. (~0.5 day, ~20 LOC)
Phase 4 (1 PR): Add tests for the new domain layer. (~1 day)
```

Each phase is bounded, reversible, and testable. Total: 4 PRs over a sprint. Reasonable.

## The "deprecation" rule

If the current tool / version is deprecated by the vendor:
- Vendor EOL date known → modernization is finding
- Vendor still supports but recommends new → observation
- Vendor hasn't deprecated → observation

Examples:
- Python 3.7 reached EOL June 2023 → modernization to 3.8+ is a finding (security patches stopped)
- Flask 2.x is still supported → modernization to 3.x is observation
- npm 8 is supported → modernization to 9 is observation

## The "second system effect" rule

When modernizing, the team often wants to also "fix everything else at the same time":
- "While we're upgrading Python, let's also switch to async"
- "While we're at FastAPI v2, let's also add OAuth"
- "While we're migrating to Rust, let's also redesign the API"

Don't bundle. Each change is its own risk; bundling multiplies risk exponentially. Recommend:
1. Do the modernization
2. Verify it works
3. THEN consider next changes

The second-system effect is the #1 cause of failed modernizations.

## The "don't rewrite" rule

Some modernizations look like rewrites:
- "Migrate from REST to gRPC"
- "Migrate from monolith to microservices"
- "Migrate from Postgres to MongoDB"

These are architecture migrations, not modernizations. They have different stakeholders, different risk profiles, different time horizons. The audit report should flag them as architecture decisions, not as modernization recommendations.

The exception: a specific defect that requires the architecture change (e.g., "we're hitting Postgres write limits; the migration to a distributed DB is required"). Even then, the report should present this as a decision the team needs to make, with the trade-offs explicit, not as a recommendation.

## Output

For modernization findings:

| Priority | Current state | Defect | Recommendation | Cost | Benefit |
|----------|---------------|--------|-----------------|------|---------|
| P1 | Python 3.7 | EOL, no security patches | Upgrade to 3.11+ | 1 sprint | Continued security support |
| P2 | flask 1.1.x | Bug in `make_response` (line 47 workaround) | Upgrade to 2.3+ | 1 PR | Removes workaround |

Each finding: current state, defect (specific), recommendation (bounded), cost (PR count, time), benefit (specific).

## Migration sequence examples — concrete patterns

For modernization findings that pass all 4 gates, sequence the migration by prerequisite. Each phase must be bounded (single PR), reversible, and testable.

### Example 1: Python 3.11+ upgrade (with `asyncio.TaskGroup`)

```
Phase 1 (1 PR): Update base Docker image from python:3.9-slim to
  python:3.11-slim. Update CI matrix to test against 3.11. No code
  changes yet — verify all existing tests pass on 3.11. (~50 LOC
  infra changes, 0 LOC code changes, rollback trivial)

Phase 2 (1 PR): Replace ad-hoc asyncio.gather() calls with
  asyncio.TaskGroup where the structured concurrency benefit applies.
  Run unit tests; add a test that verifies task cancellation propagates.
  (~80 LOC, single PR, rollback trivial)

Phase 3 (1 PR): Replace remaining asyncio.gather() calls that benefit
  from structured concurrency; leave the ones that don't (e.g., fan-out
  with all-results-needed semantics). (~30 LOC, single PR, rollback
  trivial)

Phase 4 (1 PR): Drop Python 3.9 support from pyproject.toml. Remove
  version checks (`if sys.version_info >= (3, 9)`). (~20 LOC deletions)

Total: 4 PRs over 1 sprint. Each is independent, reversible, testable.
```

### Example 2: Go 1.21+ upgrade (with `slog`)

```
Phase 1 (1 PR): Update go.mod to require Go 1.21. Update CI matrix.
  Run go test ./... — verify all pass. No code changes. (~10 LOC
  go.mod, 0 LOC code)

Phase 2 (1 PR): Introduce slog in a single package (e.g., internal/auth)
  alongside existing log package calls. Both loggers active. Verify
  structured logging works in production via a feature flag.
  (~100 LOC, single PR, rollback: flip the feature flag)

Phase 3 (1 PR per package): Migrate remaining packages to slog, one
  package at a time. Each PR replaces log.Printf calls with slog.Info
  calls, preserving the message text. (~50 LOC per PR, rollback trivial)

Phase 4 (1 PR): Remove the old log package from imports. Verify no
  callers remain via grep. (~30 LOC deletions)

Total: 4-N PRs (where N is the package count) over 1 sprint. Each PR
is bounded and reversible.
```

### Example 3: Rust edition 2024 upgrade

```
Phase 1 (1 PR): Update Cargo.toml: edition = "2024". Run `cargo check`
  and `cargo test`. Fix any breaking changes (rare for edition bumps —
  most are additive). (~10 LOC Cargo.toml, possibly 0-50 LOC code
  fixes, single PR, rollback trivial)

Phase 2 (1 PR per pattern): Adopt edition 2024 features where they
  improve the code:
  - Replace `if let Some(x) = ... { } else { return ... }` with
    `let Some(x) = ... else { return ... }` (let-else)
  - Replace `async_trait` crate dependency with native `async fn` in
    traits (if used)
  - Adopt let-chains in conditionals where readability improves
  (~30-80 LOC per pattern, single PR each, rollback trivial)

Total: 1 + N PRs over a sprint. Each is bounded, reversible, testable.
```

## Risk assessment template

For each modernization finding, assess risk before recommending:

| Risk dimension | Low (proceed) | Medium (mitigate) | High (defer) |
|----------------|---------------|---------------------|----------------|
| Regression risk | Has comprehensive tests; no behavior change expected | Has tests but behavior may shift subtly (perf, ordering) | Limited tests; behavior change is expected |
| Migration scope | Single PR, one module | Multi-PR, one team | Multi-team, multi-quarter |
| Rollback cost | Trivial (revert commit) | Medium (data migration may be needed) | High (data migration required; can't roll back) |
| Tooling impact | No CI/deploy changes | Minor CI config update | Major toolchain upgrade (separate project) |
| Team familiarity | Team knows the new tool | Team has used similar tools | Team is new to the paradigm |
| Customer impact | Internal only | Customer-visible but reversible | Customer-visible and irreversible (e.g., data format change) |

If any dimension is "High", the modernization is a project, not a finding. Document it as a future opportunity, not a current recommendation.

## Common modernization mistakes — DO NOT recommend

These look like modernizations but are actually rewrites or bad calls:

- ❌ "Migrate from REST to gRPC across all services" — architecture migration, not modernization
- ❌ "Migrate from monolith to microservices" — same
- ❌ "Migrate from Postgres to MongoDB" — same (and almost always a bad idea; relational data fits Postgres)
- ❌ "Switch from React to Vue" or any UI framework swap — rewrite, not modernization
- ❌ "Switch from Kubernetes to Nomad" — infrastructure migration, separate decision
- ❌ "Adopt event sourcing" — architecture pattern adoption, separate decision
- ❌ "Move to serverless" — deployment model change, separate decision
- ❌ "Switch to GraphQL" — API paradigm change, separate decision
- ❌ "Rewrite in Rust for memory safety" — rewrite, not modernization; if memory safety is the goal, recommend specific unsafe code audits instead
- ❌ "Migrate to microservices for scalability" — without concrete scaling target, premature
- ❌ "Adopt DDD" — architecture pattern adoption, separate decision

These are all valid *projects* a team might undertake, but they don't belong in an audit report as findings — they're decisions for the team to make with their own stakeholders, not recommendations from an audit.

## Cross-references

- `mental-models/refactor-decisions.md` — modernization is a special case of refactor; same 4-gate test applies
- `mental-models/architecture-fitness.md` — for modernizations that touch architecture (apply 5-question test)
- `swe-playbooks/dependency-analysis.md` — for modernizations driven by dependency EOL or vulnerability
- `swe-playbooks/refactor-prioritization.md` — for sequencing modernization with other refactors
- `swe-playbooks/test-quality-review.md` — modernization risk depends on test quality; assess tests first
- `assets/report_code_audit.md` — the output template (modernization findings go in the same audit report)
- `meta/evidence-checklist.md` — every modernization finding cites the defect, the migration plan, and the risk

## Verification checklist — for the agent before submitting modernization findings

- [ ] All 4 gates passed (present defect? fixes it? bounded? cost < benefit?)
- [ ] Defect is specific (not "newer is better", "modern", "cleaner")
- [ ] Migration plan is bounded (single PR or short sequence)
- [ ] Each PR in the sequence has a rollback path
- [ ] Each PR in the sequence is independently testable
- [ ] Toolchain constraint verified (CI supports it, deploy target supports it, deps are compatible)
- [ ] Regression risk assessed (per the risk assessment template)
- [ ] No bundled changes (no "while we're at it, also do X" — each modernization is its own finding)
- [ ] No architecture migrations dressed as modernizations (REST to gRPC, monolith to microservices, etc.)
- [ ] No "rewrite" recommendations
- [ ] Each finding has current state, defect, recommendation, cost, benefit
- [ ] Deprecation status verified (vendor EOL date is cited if relevant)
- [ ] Cross-references to sibling playbooks added where relevant
- [ ] If risk is "High" on any dimension, finding is downgraded to "future opportunity", not current recommendation

If any checkbox is unchecked, the modernization finding is a draft — fix before submission.
