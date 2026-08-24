# Refactor Decisions — When to Refactor, When to Leave Alone

The single most common mistake in code review is **recommending refactors that don't fix a real problem**. Refactoring is not free: it costs review time, it introduces regression risk, it blocks other changes, and it makes `git blame` harder.

## The default answer is "don't"

Start from the position: **the current code is one of several reasonable shapes, and that's fine.** Only override this default when there's a concrete reason.

## The 4-gate test

A refactor candidate is worth recommending only if it passes **all four gates**:

### Gate 1: Is there a present defect?

The current code has a bug, security hole, perf problem, or correctness issue that the refactor fixes. Not "could have" — does have, and you can point to it.

❌ "This could be more readable" — fail
✅ "The current loop has an off-by-one bug at line 47 (loop runs one extra time, writing past the buffer)" — pass

### Gate 2: Is there a maintenance cost?

The current code requires repeated work that the refactor eliminates. Not "would be nicer" — does require, and you can show the recent commits / incident reports that prove it.

❌ "This pattern is dated" — fail
✅ "This god class has been touched in 14 of the last 20 PRs, each adding another branch to the same switch. Extracting a strategy pattern would localize future changes" — pass

### Gate 3: Is there an acceptable alternative?

If the current shape is one of several reasonable choices given the constraints (team size, deployment model, framework conventions), there's no finding. The refactor would just trade one acceptable shape for another.

❌ "Use Repository pattern instead of direct ORM calls" — fail (both are fine)
✅ "Domain layer imports from controller layer (line 12) — this is an inverted dependency that creates a cycle" — pass (the inversion is a real defect)

### Gate 4: Is the change bounded?

The refactor can be done in one PR (or a small sequence with rollback paths). If it requires a quarter-long migration, it's not a refactor recommendation — it's an architecture migration, which is a different decision with different stakeholders.

❌ "Migrate from REST to gRPC across all services" — fail (not bounded)
✅ "Extract the `formatUser` function out of the controller and into the User class — it's used in 3 places, all of which can be updated in one PR" — pass

## Refactor priority matrix

When candidates pass all four gates, prioritize by impact × ease:

| Priority | Impact | Ease | Action |
|----------|--------|------|--------|
| 1 | High (correctness / security) | Any | Fix immediately. P0 blocks release. |
| 2 | High (architectural) | High | Tackle — usually small, well-bounded extraction. |
| 3 | Medium (maintainability) | High | Tackle — quick wins build momentum. |
| 4 | High (architectural) | Low | Plan — break into a migration sequence, deliver in bounded changes. |
| 5 | Medium | Low | Defer — only if recurring pain. |
| 6 | Low | Any | Don't refactor — not a finding. |

## The "fix correctness first" rule

P0 correctness/security issues block everything else. Don't bundle a refactor with a bug fix — fix the bug first, then propose the refactor as a follow-up. Bundling makes the bug fix harder to review and harder to revert if the refactor introduces a regression.

## The "smallest safe change" rule

For each refactor, recommend the smallest change that resolves the finding:

- **Extract function** instead of extract class
- **Extract class** instead of introduce framework
- **Introduce interface** instead of introduce DI container
- **Inline** instead of refactor (sometimes the right move is to delete the abstraction)

Each step should be reviewable in 30 minutes or less. If it can't be, break it smaller.

## The "test first" rule

Don't refactor code without tests. If the code has no tests, the refactor recommendation should be:

1. **Add characterization tests** (capture current behavior, even bugs)
2. **Then refactor** (with tests as safety net)

Recommending a refactor without test coverage is recommending Russian roulette.

## When NOT to refactor

- **Before a release freeze** — refactor introduces regression risk; do it after the freeze
- **In a PR that's already large** — split the refactor into its own PR
- **When the team is stressed / under deadline** — defer to calmer waters
- **When the code is about to be replaced** — let the replacement handle it
- **When you don't fully understand the code** — read more first; refactoring blind creates bugs

## Modernization vs refactor

Modernization (upgrading language version, adopting new stdlib features, switching tooling) is a special case. It's justified only when:

- The current state has a defect the modernization fixes
- The modernization enables a capability the team actually needs
- The migration risk is bounded and reversible

"Python 3.13 has better error messages" is not a justification for upgrading. "We're hitting a GIL contention issue at scale and 3.13 free-threaded build would help" is.

## How to phrase the recommendation

In the report, be specific:

❌ "Refactor this for clarity"
✅ "Extract the validation logic at lines 12-47 into a `validate_input()` function. Currently duplicated in 3 files (link, link, link); each copy has a slightly different bug. Extracting would centralize the fix and prevent future drift. ~30 LOC change, single PR, rollback trivial."

The good version has: what to extract, where, why (concrete cost), how big, how risky.

## The "ask, don't command" pattern

In review comments on someone else's code, phrase refactors as questions:

❌ "Extract this into a function"
✅ "This logic appears in 3 places (link, link, link) with slightly different bugs. Would it make sense to extract it into a shared function?"

The question form respects the author's context — they may know something you don't about why it's structured this way. If they push back, defer.

## Final hook

> "Does this fix a real problem? Show me the bug, the cost, or the repeated pain. If you can't, it's not a refactor — it's a preference."
