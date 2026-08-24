# Code Audit Report — {{TARGET_NAME}}

> Canonical output template for SWE code review / refactoring engagements. Replace `{{...}}` placeholders with concrete values; do not leave any placeholder unfilled. Maintain the section order; deviate only by adding sections specific to the engagement (do not omit any of the listed sections).

**Verdict:** PASS | CONCERNS | FAIL | BLOCKED
**Audited by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Audit type:** {{PR review / module audit / full codebase audit}}
**Scope:** {{files / modules / packages reviewed — list with line counts}}
**Time spent:** {{N hours}}
**Coverage:** {{N of M files reviewed — X%}}

---

## Executive summary

{{3-5 sentences. State the verdict in plain English. Why is the code PASS / CONCERNS / FAIL / BLOCKED? What's the headline issue if any? What was the most surprising finding? What's the recommended immediate action?}}

Example (good):
> CONCERNS. The orders module is functionally correct but has a P0 SQL injection at `user_search.py:23` — the user-supplied search term is concatenated directly into a query string, allowing auth bypass. A second P1 issue: the domain layer imports from controllers at `domain/user.py:5`, creating a cycle that will block future modularization. Recommend: fix the SQLi before next release (one-line change, 30 minutes), address the architecture in the following sprint (2 PRs, 1 day each).

## Scope reviewed

| File / module | LOC | Function count | Coverage | Notes |
|---------------|-----|-------------------|----------|-------|
| {{path/to/file}} | {{N}} | {{N}} | {{N% / unknown}} | {{triage note — e.g., "high churn, pain point"}} |
| {{path/to/file}} | {{N}} | {{N}} | {{N% / unknown}} | {{triage note}} |
| ... | ... | ... | ... | ... |

| Total reviewed | {{N}} files / {{N}} LOC | | | |
| Total in scope | {{N}} files / {{N}} LOC | | | Coverage: {{N%}} |
| Out of scope | {{N}} files | | | Reason: {{user request / time / etc.}} |

## Findings

| Priority | Area | Problem | Evidence | Recommended next step |
|----------|-------|---------|----------|----------------------|
| P0 | {{Correctness / Security}} | {{Buffer overflow at line N}} | {{file:L:N: `memcpy(dst, src, strlen(src)+1)`}} | {{Bound the copy: `strncpy(dst, src, sizeof(dst)-1); dst[sizeof(dst)-1]=0;`}} |
| P0 | {{Security}} | {{SQL injection}} | {{file:L:N: `cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")`}} | {{Parameterize: `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`}} |
| P0 | {{Security}} | {{Command injection}} | {{file:L:N: `os.system(f"echo {user_input}")`}} | {{Use `subprocess.run(["echo", user_input], shell=False)`}} |
| P0 | {{Security}} | {{Path traversal}} | {{file:L:N: `open(f"/data/{filename}")`}} | {{Validate filename against whitelist; use `pathlib.Path` and check `resolved().is_relative_to(base)`}} |
| P0 | {{Security}} | {{Insecure deserialization}} | {{file:L:N: `pickle.loads(data)`}} | {{Use `json.loads` or signed pickle with HMAC}} |
| P0 | {{Security}} | {{Weak crypto}} | {{file:L:N: `hashlib.md5(password).hexdigest()`}} | {{Use `bcrypt` or `argon2-cffi`}} |
| P0 | {{Concurrency}} | {{Race on shared map}} | {{file:L:N: goroutine writes without mutex}} | {{Add `sync.Mutex` or use `sync.Map`}} |
| P0 | {{Concurrency}} | {{TOCTOU on file check}} | {{file:L:N: `access()` then `open()`}} | {{Use `open(O_CREAT|O_EXCL)` to atomically check-and-create}} |
| P1 | {{Architecture}} | {{Domain imports from controller}} | {{domain/user.go:1: import "../controllers"}} | {{Invert: controller orchestrates domain}} |
| P1 | {{Maintainability}} | {{God module: 850 LOC}} | {{services/processor.go}} | {{Split into 3 by responsibility: parser, validator, executor}} |
| P1 | {{Concurrency}} | {{Async blocking I/O}} | {{file:L:N: `requests.get()` inside `async def`}} | {{Use `httpx.AsyncClient` or `loop.run_in_executor`}} |
| P2 | {{Test quality}} | {{Test mocks too much, breaks on refactor}} | {{tests/user_test.go:42}} | {{Test through public API only; remove implementation mocks}} |
| P2 | {{Performance}} | {{N+1 query pattern}} | {{file:L:N: `for user in users: db.get_user(user.id)`}} | {{Batch fetch: `db.get_users([u.id for u in users])`}} |
| P2 | {{Maintainability}} | {{Dead code}} | {{file:L:N: `def unused_function(): ...` (no callers found)}} | {{Remove}} |
| P3 | {{Style}} | {{Inconsistent naming}} | {{file:L:N: `userName` vs `user_name` mixed}} | {{Add `ruff` / `black` / `prettier` to CI}} |

## Coverage assessment

For each dimension, state PASS / CONCERNS / FAIL and what was checked:

- **Logical correctness**: {{PASS / CONCERNS / FAIL}} — {{what's strong / what's missing. E.g., "happy path verified through tests; edge cases (empty input, large input, unicode) not covered."}}
- **Edge cases**: {{PASS / CONCERNS / FAIL}} — {{what edge cases were checked? what were missed?}}
- **Error handling**: {{PASS / CONCERNS / FAIL}} — {{where errors get swallowed / where they propagate correctly. Specifically: are timeouts handled? are retries bounded? are partial failures accounted for?}}
- **Security**: {{PASS / CONCERNS / FAIL}} — {{what was checked: input validation, injection, auth, crypto, secrets handling. List the bug classes searched.}}
- **Concurrency**: {{PASS / CONCERNS / FAIL}} — {{race conditions, deadlocks, atomicity violations, async-blocking patterns}}
- **Performance**: {{PASS / CONCERNS / FAIL}} — {{N+1 queries? unnecessary allocations? hot path issues? measured or static-only?}}
- **Maintainability**: {{PASS / CONCERNS / FAIL}} — {{coupling, cohesion, naming, dead code, god modules, layer violations}}
- **Test quality**: {{PASS / CONCERNS / FAIL}} — {{coverage, behavior testing, brittle mocks, flaky tests}}
- **Documentation**: {{PASS / CONCERNS / FAIL}} — {{does the code match the docs? are public APIs documented? are non-obvious decisions commented?}}

## Positive observations

{{What's done well. Be specific — not just "good code" but "the lock-free queue in `queue.go` correctly handles the spurious wake-up case via CAS retry". Praise encourages the right patterns.}}

- {{specific good pattern 1 with location and why it's good}}
- {{specific good pattern 2 with location and why it's good}}
- {{specific good pattern 3 with location and why it's good}}
- ...

## Limitations

{{What couldn't be verified, why, what would resolve it. Common limitations:

- "Static-only — didn't run integration tests; the SQLi finding is based on static analysis, recommend confirming with a `' OR '1'='1` payload"
- "Didn't review the test/ directory — coverage claims are based on test file count, not actual coverage reports"
- "Couldn't verify {{behavior}} — needs runtime profiling to confirm the N+1 query actually fires under load"
- "Toolchain limitations: {{which tool wasn't available}} — fell back to manual inspection"
- "Read N out of M files — {{N/M}}% coverage"
- "Didn't check dependency vulnerabilities (`pip-audit` / `npm audit`) — supply chain not assessed"
- "Didn't review CI/CD pipeline — deployment-time issues not captured"
- "Didn't review infrastructure-as-code (Terraform, etc.) — infra-level issues not captured"
- "Didn't review secrets management — secrets-at-rest not assessed"
}}

## Recommended next step

{{The smallest safe change or follow-up action. Concrete, bounded, ordered by prerequisite. Examples:

1. **Immediate** (before next release): Fix P0 correctness/security issues. {{Estimate: N PRs, N hours each, reversible.}}
2. **This sprint**: Address P1 architecture issues. {{Estimate: 2 PRs (extract + invert), 1 day, reversible.}}
3. **Next sprint**: Address P2 issues — improve test isolation, batch queries. {{Estimate: 1 sprint, 3-4 PRs.}}
4. **Backlog**: Address P3 style findings via `ruff`/`black`/`prettier` in CI. {{Estimate: 1 PR, 1 hour.}}

For each step: estimated PR count, time, reversibility, prerequisite chain.
}}
