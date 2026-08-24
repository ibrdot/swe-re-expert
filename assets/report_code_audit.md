# Code Audit Report — {{TARGET_NAME}}

**Verdict:** PASS | CONCERNS | FAIL | BLOCKED
**Audited by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Audit type:** {{PR review / module audit / full codebase audit}}
**Scope:** {{files / modules / packages reviewed}}

---

## Executive summary

{{3-5 sentences. State the verdict in plain English. Why is the code PASS / CONCERNS / FAIL / BLOCKED? What's the headline issue if any? What was the most surprising finding?}}

## Scope reviewed

| File / module | LOC | Function count | Coverage | Notes |
|---------------|-----|-------------------|----------|-------|
| {{path/to/file}} | {{N}} | {{N}} | {{N% / unknown}} | {{triage note}} |
| ... | ... | ... | ... | ... |

| Total reviewed | {{N}} files / {{N}} LOC | | | |

## Findings

| Priority | Area | Problem | Evidence | Recommended next step |
|----------|-------|---------|----------|----------------------|
| P0 | {{Correctness / Security}} | {{Buffer overflow at line N}} | {{file:L:N: `memcpy(dst, src, strlen(src)+1)`}} | {{Bound the copy: `strncpy(dst, src, sizeof(dst)-1); dst[sizeof(dst)-1]=0;`}} |
| P0 | {{Concurrency}} | {{Race on shared map}} | {{file:L:N: goroutine writes without mutex}} | {{Add `sync.Mutex` or use `sync.Map`}} |
| P1 | {{Architecture}} | {{Domain imports from controller}} | {{domain/user.go:1: import "../controllers"}} | {{Invert: controller orchestrates domain}} |
| P1 | {{Maintainability}} | {{God module: 850 LOC}} | {{services/processor.go}} | {{Split into 3 by responsibility}} |
| P2 | {{Test quality}} | {{Test mocks too much, breaks on refactor}} | {{tests/user_test.go:42}} | {{Test through public API only}} |
| P3 | {{Style}} | {{...}} | ... | ... |

## Coverage assessment

- **Logical correctness**: {{PASS / CONCERNS / FAIL}} — {{what's strong / what's missing}}
- **Edge cases**: {{PASS / CONCERNS / FAIL}} — {{what edge cases were checked? what were missed?}}
- **Error handling**: {{PASS / CONCERNS / FAIL}} — {{where errors get swallowed / where they propagate correctly}}
- **Security**: {{PASS / CONCERNS / FAIL}} — {{what was checked: input validation, injection, auth, crypto}}
- **Performance**: {{PASS / CONCERNS / FAIL}} — {{N+1 queries? unnecessary allocations? hot path issues?}}
- **Maintainability**: {{PASS / CONCERNS / FAIL}} — {{coupling, cohesion, naming, dead code}}
- **Test quality**: {{PASS / CONCERNS / FAIL}} — {{coverage, behavior testing, brittle mocks}}

## Positive observations

{{What's done well. Be specific — not just "good code" but "the lock-free queue in `queue.go` correctly handles the spurious wake-up case via CAS retry". Praise encourages the right patterns.}}

- {{specific good pattern 1 with location}}
- {{specific good pattern 2 with location}}
- ...

## Limitations

{{What couldn't be verified, why, what would resolve it. Common:
- "Static-only — didn't run integration tests"
- "Didn't review {{module}} — out of scope per user request"
- "Couldn't verify {{behavior}} — needs runtime profiling"
- "Toolchain limitations: {{which tool wasn't available}} — fell back to manual inspection"
}}

## Recommended next step

{{The smallest safe change or follow-up action. Concrete, bounded, ordered by prerequisite. Examples:
- "Fix P0 correctness/security issues first — these block release"
- "Plan P1 architecture migration: extract domain layer first, then invert imports"
- "For P2, batch with next sprint — non-blocking but accumulates"
- "Skip P3 — defer to linters"
}}
