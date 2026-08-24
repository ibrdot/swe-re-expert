# Refactor Decisions — When to Refactor, When to Leave Alone

The single most common mistake in code review is **recommending refactors that don't fix a real problem**. Refactoring is not free: it costs review time, it introduces regression risk, it blocks other changes, and it makes `git blame` harder.

## The default answer is "don't"

Start from the position: **the current code is one of several reasonable shapes, and that's fine.** Only override this default when there's a concrete reason.

This is not a habit of caution. It's a discipline of focus. A reviewer who flags every non-textbook pattern as a refactor candidate writes reviews that don't get read. A reviewer who flags only refactors that fix real problems writes reviews that get merged.

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

The pattern in the report:

```
Finding #1 (P0): Buffer overflow at file.c:47 — strcpy writes past 16-byte dst
  Recommendation: Replace strcpy with strlcpy or bounds-checked copy.
  PR shape: 1-line fix, no other changes. Rollback trivial.

Finding #2 (P2, deferred to follow-up PR): The function containing the
  overflow has 3 other unsafe strcpy calls. Recommend refactoring the
  function to use a safe-copy wrapper throughout.
  PR shape: ~30 LOC, single PR after Finding #1 is merged.
  Depends on: Finding #1 merge.
```

The two findings cite each other by number. The reader sees the plan.

## The "smallest safe change" rule

For each refactor, recommend the smallest change that resolves the finding:

- **Extract function** instead of extract class
- **Extract class** instead of introduce framework
- **Introduce interface** instead of introduce DI container
- **Inline** instead of refactor (sometimes the right move is to delete the abstraction)

Each step should be reviewable in 30 minutes or less. If it can't be, break it smaller.

### Inline refactors are valid

Many reviewers treat "inline this" as a smell — but premature abstraction is more common than premature inlining. A function called from one place that wraps 3 lines of code is overhead. A class with one method is a function in a costume. Inline it.

The rule: if you can't articulate the abstraction's purpose in one sentence without using the word "might" (as in "might be reused later"), inline it.

## The "test first" rule

Don't refactor code without tests. If the code has no tests, the refactor recommendation should be:

1. **Add characterization tests** (capture current behavior, even bugs)
2. **Then refactor** (with tests as safety net)

Recommending a refactor without test coverage is recommending Russian roulette.

### Characterization test recipe

For each refactor candidate, the recommended test pattern:

```
1. Identify the function's observable behavior (input → output, side effects)
2. Write a test for each observed behavior — including the bugs
3. Mark each test with @observed_behavior_1, @observed_behavior_2, etc.
4. Run tests — all pass (they capture current behavior)
5. Refactor — tests must still pass
6. After refactor, decide which @observed_behavior tests represent bugs vs intended behavior; fix the bugs in a separate PR with new tests asserting the fixed behavior
```

This separates "we preserved behavior during refactor" from "we fixed a bug." Both are valid; bundling them in one commit muddies `git blame`.

## When NOT to refactor

- **Before a release freeze** — refactor introduces regression risk; do it after the freeze
- **In a PR that's already large** — split the refactor into its own PR
- **When the team is stressed / under deadline** — defer to calmer waters
- **When the code is about to be replaced** — let the replacement handle it
- **When you don't fully understand the code** — read more first; refactoring blind creates bugs
- **When the team doesn't own the code** — flag in observations, let the owning team decide
- **When there's no test coverage and the team can't add tests** — refactor without tests is debt
- **When the code is in a critical path with high regression cost** — needs higher bar (P0/P1 finding only)

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

## Per-language refactor patterns — common candidates and their bounded refactors

### C++

| Candidate (with defect) | Bounded refactor | LOC |
|--------------------------|------------------|-----|
| Raw pointer with manual new/delete, leak in error path | `std::unique_ptr` with custom deleter if needed | 5-15 |
| Raw `new T[]` with manual size tracking | `std::vector<T>` | 10-30 |
| Manual lock/unlock with exception safety gap | `std::lock_guard` / `std::scoped_lock` | 5-10 |
| C-style cast that breaks virtual dispatch | `static_cast` / `dynamic_cast` per use | 1-5 per cast |
| Copy of large object in hot path | Pass by `const&` | 1 per signature |
| Missing virtual destructor in base class (UB on delete) | Add `virtual ~Base() = default;` | 1 line |
| Iterator invalidation in loop (UB) | Pre-compute end iterator, or use indexed access | 5-15 |

### Go

| Candidate (with defect) | Bounded refactor | LOC |
|--------------------------|------------------|-----|
| Loop variable captured by goroutine (data race) | Pass as parameter or use `go func(i int){...}(i)` | 1-3 per loop |
| `interface{}` that loses type safety | Concrete type or generic (Go 1.18+) | 5-30 per function |
| Goroutine without context cancellation (leak) | Add `ctx context.Context` parameter, `select` on `ctx.Done()` | 10-30 per goroutine |
| Global mutable state (data race) | Pass as struct field or method receiver | 5-20 |
| Error wrapping lost (`return err` without context) | `fmt.Errorf("doing X: %w", err)` | 1 per return |
| `sync.Mutex` covering too much (false contention) | Split into per-field mutexes or use `sync.RWMutex` | 5-15 |

### Rust

| Candidate (with defect) | Bounded refactor | LOC |
|--------------------------|------------------|-----|
| `unwrap()` on user input path (panic) | `?` with proper error type, or `unwrap_or_else` with fallback | 1-5 per unwrap |
| `Box<dyn Error>` losing typed error | Custom error enum implementing `std::error::Error` | 20-50 |
| `unsafe` block without safety comment | Add safety comment or replace with safe abstraction | 1-10 per unsafe block |
| `String::clone()` in hot path | Pass `&str` or `Cow<str>` | 1 per signature |
| `Mutex<T>` covering too much (contention) | Split into per-field mutexes or use `RwLock` for read-heavy | 5-20 |
| `Vec::clone()` when only read access needed | Pass `&[T]` or `&Vec<T>` | 1 per signature |
| Manual `Drop` impl for resource | Use `Drop` trait properly or use ` owning_ref` patterns | 10-30 |

### Python

| Candidate (with defect) | Bounded refactor | LOC |
|--------------------------|------------------|-----|
| Mutable default argument (state leak across calls) | `None` sentinel + assignment in body | 1-5 per function |
| `except Exception:` swallowing all errors | Specific exception types + re-raise for unexpected | 1-10 per try |
| `import *` polluting namespace | Explicit imports | 1 per import |
| String formatting with `%` or concat | f-strings (Python 3.6+) | 1 per format |
| Manual dict iteration with key lookup | `.items()` | 1-3 per loop |
| Late-binding closure in loop (lambda capturing loop var) | Default argument binding or use `functools.partial` | 1-3 per lambda |
| `time.sleep()` blocking the event loop | `await asyncio.sleep()` | 1 per call (if in async function) |

## Per-language anti-refactors — DO NOT recommend

These look like refactors but actively harm code quality:

### C++
- ❌ "Replace raw pointer with `shared_ptr` everywhere" — shared_ptr everywhere is just GC with extra steps; use unique_ptr where possible
- ❌ "Use `std::endl` instead of `\n`" — `std::endl` flushes, slower; prefer `\n`
- ❌ "Convert all C-style arrays to `std::array`" — only for fixed-size; `std::vector` for dynamic
- ❌ "Make every destructor virtual" — only for base classes; virtual destructors in non-polymorphic types add overhead

### Go
- ❌ "Replace `errors.New` with `fmt.Errorf` everywhere" — only when wrapping is needed
- ❌ "Use generics for every collection" — only when type safety is a real benefit; pre-generics code is fine
- ❌ "Convert all channels to buffered" — only when the producer/consumer rate mismatch is measured
- ❌ "Use `context.Context` for everything" — only when crossing goroutine or API boundaries

### Rust
- ❌ "Replace `Vec` with `array::IntoIter` everywhere" — premature optimization
- ❌ "Use `tokio` for everything" — only when async is actually needed; sync code is fine
- ❌ "Convert all `&str` to `String`" — `&str` is correct for read-only views
- ❌ "Add `Clone` derive to everything" — only when cloning is the right semantic; otherwise redesign ownership

### Python
- ❌ "Replace all `for` loops with `map`/`filter`" — readability loss without perf benefit
- ❌ "Use `asyncio` for everything" — only when IO-bound; CPU-bound code benefits from `multiprocessing`
- ❌ "Convert all classes to `dataclass`" — only for data containers; behavior-heavy classes are fine
- ❌ "Use `pathlib` everywhere" — only when path manipulation is non-trivial; `os.path` is fine

## Code smell → anti-pattern mapping

Use this table to identify the underlying anti-pattern before recommending a refactor:

| Smell | Likely anti-pattern | Look at |
|-------|---------------------|---------|
| Function > 200 lines | God function | Split by responsibility; check if state is shared between halves |
| Class with > 10 fields | God class | Split by cohesion — fields used together stay together |
| Switch with > 5 cases | Missing polymorphism | Only if cases grow over time (Gate 2: maintenance cost) |
| Deeply nested conditionals (>4 levels) | Arrow code | Extract guard clauses; or use early returns |
| Same code block duplicated 3+ times | DRY violation | Extract — but verify the duplications aren't accidentally different (3 similar ≠ 3 identical) |
| Long parameter list (>5) | Data clump or missing object | Group into a struct, or pass the object the data came from |
| Commented-out code | Dead code (low confidence) | Verify with grep; if dead, delete in a separate commit |
| Method named `doXAndY` | Mixed responsibility | Split into `doX` and `doY` |
| Hidden side effect (function name doesn't suggest mutation) | Command-query separation violation | Split into `getX` (pure) and `setX` (mutation) |
| Inconsistent error handling (try/catch in some paths, ignore in others) | Error handling inconsistency | Pick one strategy, apply uniformly |

## Refactor sequence planning — for multi-step refactors

Some refactors can't be done in one PR. Sequence them:

```
Goal: Replace ad-hoc config parsing with `pydantic`-validated config

Sequence:
  PR 1: Add `pydantic` config class alongside existing config. Don't
        replace callers yet. (~100 LOC, no behavior change)
  PR 2: Update 1 of N callers to use new config. Keep old config path
        working. (~20 LOC, behavior unchanged for old callers)
  PR 3: Migrate remaining callers (one PR per module if modules are
        independent, or one PR if all callers are in one place).
  PR 4: Delete old config path. Verify no callers remain via grep.
        (~50 LOC deletion, no behavior change)

Each PR is reviewable in 30 minutes. Rollback is trivial — each PR
reverts independently.
```

The sequence has rollback paths at each step. If PR 3 introduces a bug, revert PR 3 — PR 2 still works (old config still active). The user isn't stuck on a broken head.

## The "rollback cost" assessment

For each refactor, assess rollback cost in the report:

- **Trivial** — single commit revert, no migration needed (most extract function / inline refactors)
- **Low** — multi-commit revert, but each commit is independent (sequence planning above)
- **Medium** — requires coordination (e.g., API change with multiple consumers)
- **High** — requires data migration or feature flags (defer; this is architecture, not refactor)

If rollback cost is "High", it's not a refactor — it's a migration. Different stakeholders, different timeline, different report section.

## The "no rewrite refactors" rule

A refactor recommendation that says "rewrite this module" is not a refactor recommendation. It's a project plan. Refactor recommendations have:

- A bounded scope (file + line range, or function + module)
- A specific change (extract X, inline Y, introduce Z)
- A LOC estimate
- A rollback path

If you can't fill in all four, you don't have a refactor — you have a vibe. Vibes don't go in the report.

## How to phrase the recommendation — the template

Every refactor finding should follow this template:

```
[Finding #N (P-priority)]
  Refactor: <verb> <what> <where>
  Reasoning: <concrete defect or cost>
  Evidence: <git log / line range / duplicated function locations>
  Recommendation:
    <specific change description, with code if possible>
  PR shape: <LOC range, single PR or sequence, rollback cost>
  Dependencies: <other findings this depends on, or "none">
  Risk: <what could go wrong, what tests cover it>
```

Example filled in:

```
[Finding #4 (P2)]
  Refactor: Extract validation logic from controllers/user.py:12-47
  Reasoning: Same logic duplicated in controllers/order.py:8-43
    and controllers/admin.py:15-50. Each copy has a slightly different
    bug (the admin copy doesn't check role escalation; the order copy
    has the role check but misses the org-id check).
  Evidence: `git log --oneline -- controllers/` shows 14 commits in
    last 20 PRs touching the validation logic, each modifying a
    different copy. Each commit fixed a different bug.
  Recommendation:
    Extract `validate_user_request(request, required_roles, required_org_id)`
    into `services/auth.py`. Replace the three copies with calls to this
    function. The extracted function should include all checks from the
    admin copy (which is the most complete).
  PR shape: ~80 LOC, single PR, rollback trivial (revert restores
    three copies).
  Dependencies: none.
  Risk: The admin copy's check for role escalation must be preserved
    in the extracted version. Add a regression test (test_admin_role_
    escalation_blocked) before merging.
```

## Verification checklist — before submitting the refactor finding

- [ ] Passes all 4 gates (defect, maintenance cost, acceptable alternative, bounded)
- [ ] Has specific verb (extract / inline / introduce / replace / split / merge)
- [ ] Has specific target (function name, file:line range)
- [ ] Has concrete evidence (git log output, duplicated line ranges, commit count)
- [ ] Has LOC estimate
- [ ] Has rollback cost (trivial / low / medium / high)
- [ ] Has dependency list (other findings this depends on, or "none")
- [ ] Has risk assessment (what could go wrong)
- [ ] Has test coverage (existing tests, or characterization tests to add first)
- [ ] Doesn't recommend a "rewrite" (rewrites are not refactors)
- [ ] Doesn't recommend an anti-refactor (per per-language anti-refactor table)
- [ ] Doesn't bundle with correctness fix (correctness first, refactor second)
- [ ] Doesn't touch code the team doesn't own (or flagged as observation, not finding)

If any checkbox is unchecked, the refactor is a draft — not a recommendation.

## Final hook

> "Does this fix a real problem? Show me the bug, the cost, or the repeated pain. If you can't, it's not a refactor — it's a preference."
