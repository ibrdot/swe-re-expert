# Refactor Prioritization — What to Fix, in What Order

You have 20 findings. You can ship 3 in this sprint. Which 3?

## The priority matrix

Order by **impact × ease**. Highest impact + highest ease first.

| Priority | Impact | Ease | Action |
|----------|--------|------|--------|
| 1 | High (correctness / security) | Any | **Fix immediately.** Blocks release. |
| 2 | High (architectural) | High | **Tackle first.** Small, well-bounded extraction. |
| 3 | Medium (maintainability) | High | **Tackle.** Quick wins build momentum. |
| 4 | High (architectural) | Low | **Plan.** Break into a migration sequence. |
| 5 | Medium | Low | **Defer.** Only if recurring pain. |
| 6 | Low | Any | **Skip.** Not a finding. |

## The 4 decision rules

### Rule 1: Correctness / security always first

P0 correctness or security defects block everything else. Don't bundle them with refactors; fix them first, ship, then propose refactors.

Why: a P0 defect is a live bug. Refactoring around it creates regression risk. Fix the bug, then refactor.

### Rule 2: High-impact easy work next

A high-impact finding that's easy (small, well-bounded, has tests) is the best ROI. Examples:
- Extracting a duplicated function into a shared utility
- Adding a missing ownership check (one if-statement)
- Inverting one import direction

These give immediate value (impact) with low risk (ease, bounded, reversible).

### Rule 3: Plan big migrations separately

A high-impact finding that's hard (multi-quarter, requires coordination) is not a refactor — it's an architecture migration. Treat it differently:

- Sequence by prerequisite
- Each step is bounded (one PR)
- Each step is reversible (rollback path)
- Each step has tests
- Document the migration plan, not just the finding

The audit report flags the issue; the migration plan is a follow-up artifact.

### Rule 4: Skip low-impact work

Style preferences, pattern preferences, "would be nicer" — these don't go in the report at all. If you can't articulate a concrete cost, the candidate isn't a finding.

## Impact estimation

For each finding, estimate impact on a scale:

| Impact | Description |
|--------|-------------|
| Critical (P0) | Blocks release; causes data loss / security hole / crash |
| High (P1) | Will cause recurring pain; one of: correctness bug, security issue, change amplification |
| Medium (P2) | Slows future work; one of: maintainability issue, dead code in active module, fragile tests |
| Low (P3) | Cosmetic; not worth doing now |

Don't conflate "low impact" with "small change". A 1-line fix can be high-impact (SQLi patch). A 100-line change can be low-impact (rename).

## Ease estimation

| Ease | Description |
|------|--------------|
| High (1 PR) | Bounded change, has tests, reversible in <30 min |
| Medium (1 sprint) | Multiple related changes, may need test additions, ~1-2 days |
| Low (1 quarter) | Multi-PR migration, coordination with other teams |

Ease is about how quickly you can ship the fix safely. Not the same as code size.

## Sequencing rules

### Rule A: Fix dependencies before dependents

If finding F1's fix is prerequisite to F2's, do F1 first.

Example: "Extract domain layer" (F1) → "Invert controller imports" (F2). Do F1 first; F2 only makes sense once F1 is in place.

### Rule B: Cheap wins before expensive migrations

Even if impact is similar, do the easy version first:

- "Add input validation" (easy, blocks injection) before "Parameterize all queries" (medium)
- "Add auth check" (easy) before "Refactor auth middleware" (hard)

The cheap wins reduce risk while the bigger work is in progress.

### Rule C: Don't bundle unrelated changes

Two findings in the same area can be in the same PR if they touch the same code. Two findings in different areas should be in different PRs.

Bundling creates:
- Larger PRs (slower review)
- Higher regression risk (one bug rolls back both fixes)
- Harder attribution (which change broke what?)

Split. One finding per PR is the default.

### Rule D: Test before / after each step

Every refactor step should have characterization tests first:
- Capture current behavior (even bugs)
- Refactor (with tests as safety net)
- Verify tests still pass

Without tests, refactoring is gambling. The audit report should note "before refactoring X, add characterization tests" as a prerequisite step.

## The "anti-priority" list

Don't recommend in this order:

1. ❌ Modernize the framework (no concrete defect)
2. ❌ Refactor for "readability" (subjective)
3. ❌ Adopt new pattern (no concrete defect)
4. ❌ Rewrite the module (too vague)
5. ❌ Add tests for "coverage" (no behavior to verify)

These are not findings; they're preferences. They don't belong in the audit report.

## The "10% rule" for refactors

In a typical sprint:
- 80% of capacity = feature work
- 10% = technical debt / refactor
- 10% = bug fixes

If you have 20 findings and the team has capacity for 3 fixes this sprint, pick:
1. The P0 correctness/security finding (must)
2. The highest-impact easy finding (best ROI)
3. One more easy finding if budget allows (momentum)

The remaining 17 findings go in the backlog, ordered by the priority matrix. Each sprint picks the next batch.

## The "tech debt ledger"

Keep a running list of findings not yet addressed:

```markdown
## Tech Debt Ledger

### P1 — to address this quarter
- [ ] Domain layer imports from controllers (audit 2024-08-24)
- [ ] Missing tests on auth flow (audit 2024-08-24)
- [ ] SQLi in user search (audit 2024-08-24) — quick fix, blocked on refactor

### P2 — to address next quarter
- [ ] N+1 queries in order service (audit 2024-08-24)
- [ ] God class: services/processor.py 850 LOC (audit 2024-08-24)

### P3 — backlog
- [ ] Dead code: utils/legacy.py (audit 2024-08-24)
- [ ] Style: mixed naming conventions in models/ (audit 2024-08-24)
```

The ledger:
- Survives between audits (don't re-find the same thing)
- Shows the team's debt trend over time
- Helps prioritize when "we have a free sprint"
- Builds accountability — every audit adds new debt, every sprint removes some

## The "second-order effects" rule

A refactor finding may have second-order effects:

- Extracting a function may make 10 other functions clearer → high value
- Inverting a dependency may enable testing in isolation → enables more refactors
- Splitting a god class may break tests that relied on the god class → test work needed

Estimate these in the report:
- "Extracting `validate_user_input` (1 PR, 30 LOC) would also unblock the auth refactor (P1 below)"
- "Splitting `services/processor.py` will require updating ~15 tests; budget 2 extra days for test maintenance"

This helps the team plan realistically.

## The "smaller is better" rule

When in doubt, split smaller. Two small PRs ship faster than one big one:
- Smaller reviews (faster)
- Lower regression risk
- Easier rollback if something breaks
- Faster feedback

The exception: tightly coupled changes that don't make sense individually. Those bundle.

## Output

The refactor section of the audit report:

```markdown
## Refactor recommendations

### P0 (must fix before release)
| Finding | Impact | Ease | Estimated PRs |
|---------|--------|------|----------------|
| SQLi in user_search (file.py:23) | Critical | High | 1 |

### P1 (this sprint)
| Finding | Impact | Ease | Estimated PRs |
|---------|--------|------|----------------|
| Domain imports from controllers | High | High | 1 (extract) + 1 (invert) |
| Missing tests on auth flow | High | Medium | 1 (add tests) |

### P2 (next sprint)
| Finding | Impact | Ease | Estimated PRs |
|---------|--------|------|----------------|
| N+1 queries in order service | Medium | Medium | 1 |
| God class processor.py (850 LOC) | Medium | Low | 4 (split into 3 modules) |

### P3 (backlog)
- Dead code: utils/legacy.py (after one release of monitoring)
- Style: mixed naming in models/ (defer to linter)
```

Each entry: specific finding, impact level, ease level, PR count estimate.

## The "respect the team's bandwidth" rule

Don't recommend a 6-month refactor when the team has 1 week of capacity. Match recommendations to bandwidth:

- Team has 1 sprint → recommend the easy wins (3-5 PRs)
- Team has 1 quarter → can include 1 medium migration
- Team has multi-quarter roadmap → can recommend architecture migrations

Out-of-bandwidth recommendations are demoralizing — they imply the team should drop everything to address the audit. They won't. Realistic recommendations get shipped.
