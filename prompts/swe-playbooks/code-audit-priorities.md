# Code Audit Priorities

The decision tree for what to spend time on during a code review. Order matters — do the high-value things first.

## The audit sequence

In a typical 1-2 hour code review:

### Phase 1: Quick pattern scan (15 minutes)

Run cheap pattern matches across the codebase:

```bash
# Security patterns (highest signal)
rg "eval\(|exec\(" --type py              # Python code injection
rg "os\.system|subprocess.*shell=True"      # Command injection
rg "SELECT.*FROM.*\+.*\|execute\(.*\+"      # SQL injection (rough heuristic)
rg "pickle\.loads|yaml\.load\("             # Insecure deserialization
rg "MD5|SHA1|DES|RC4|ECB"                   # Weak crypto
rg "Math\.random|random\.randint"           # Insecure randomness for security
rg "password.*=.*['\"]"                     # Hardcoded passwords (rough)

# Resource patterns
rg "TODO|FIXME|XXX|HACK"                    # Tech debt markers
rg "console\.log|print\(" --type py         # Debug logging left in
```

Each hit is a candidate finding. Verify each one before adding to the report — many will be false positives (test code, safe usage, etc.).

### Phase 2: Critical flow trace (30 minutes)

Pick the highest-traffic or most-changed flow. Read it end to end:

- Entry point (HTTP route, CLI handler, message consumer)
- Orchestration (service layer)
- Domain logic
- Persistence / external calls
- Return path

For each step, ask:
- **What could go wrong here?** (failure modes)
- **What's the input source?** (user / external / trusted)
- **Where's the validation?** (before or after this point?)
- **Where's the error handling?** (swallowed? propagated? leaked?)

### Phase 3: Test quality assessment (10 minutes)

Look at the test files for the modules you reviewed:

- Do tests cover the happy path? (almost always yes)
- Do tests cover edge cases? (empty input, null, max-size, concurrent, etc.)
- Do tests cover failure modes? (DB down, network timeout, invalid input)
- Do tests assert behavior or just structure?
- Are tests brittle? (mock too much, break on refactor)

### Phase 4: Filter & prioritize (10 minutes)

You should have ~15-30 candidate findings. Apply the 4-gate filter:

1. Concrete cost? (correctness, security, maintenance, perf)
2. Acceptable alternative violated? (current shape is wrong, not just different)
3. Evidence specific? (line numbers, not "feels bad")
4. Fix bounded? (one PR or sequence, not a rewrite)

What survives is your findings table. The rest is observations — note them in the report but not as findings.

### Phase 5: Write the report (15 minutes)

Use the code audit template. Order findings P0 first, then P1, P2, P3. Be specific in every cell — line numbers, code quotes, concrete consequences, bounded fixes.

## Priority ordering by category

When you have many findings, order them like this:

### P0 — must fix before merge / release

- **Correctness defects** — wrong behavior, race conditions, logic errors
- **Security vulnerabilities** — injection, auth bypass, crypto misuse, secrets in code
- **Resource leaks** — file handles, connections, memory (long-running processes)
- **Crash bugs** — null deref, divide by zero, OOM from unbounded input

These block. Recommend "fix before merge".

### P1 — should fix soon

- **Material architecture issues** — boundary violations, ownership ambiguity
- **Missing tests on critical paths** — happy path covered, edge cases not
- **Error handling gaps** — swallowed errors on critical paths
- **Performance issues on hot paths** — N+1 queries, unnecessary allocations in tight loops
- **Maintainability** — god classes, dead code in active modules, fragile tests

These don't block merge but should be tracked. Recommend "fix in next sprint".

### P2 — non-blocking improvements

- **Test coverage gaps on non-critical paths**
- **Performance issues on cold paths**
- **Style inconsistencies that hurt readability**
- **Dead code in rarely-touched modules**
- **Documentation drift**

These go in the backlog. Recommend "schedule for next refactor window".

### P3 — nitpicks

- **Formatting** — defer to linters
- **Import ordering** — same
- **Minor naming preferences** — defer to author
- **Comments-as-spec drift** — note but don't act on

These don't go in the report. If you must mention, use a `[nit]` prefix.

## The "don't review formatting" rule

Use linters. Prettier, Black, rustfmt, gofmt — they handle 95% of style issues automatically. Don't waste review time on:

- Indentation
- Brace style
- Import ordering
- Line length
- Trailing whitespace
- Spelling

If the linter catches it, the linter catches it. If it doesn't, the style choice is opinion and not worth discussing.

The exception: style that actively hurts readability (e.g., a 200-character line that wraps badly). Those are readability findings, not style findings.

## The "test before merge" rule

Critical paths need tests. If a PR adds behavior to a critical path (auth, payment, user input handling) and doesn't include tests, that's a P0 finding.

Tests should:
- Cover the happy path
- Cover 2-3 edge cases (empty, null, max, min)
- Cover at least one failure mode (network down, invalid input)
- Assert behavior, not implementation
- Survive refactors (test through public API, not internals)

Tests that fail any of these gates are P1/P2 findings.

## The "ask for context" rule

When you find something that looks wrong, ask the author before flagging:

> "Line 47: `setTimeout(() => doStuff(), 0)` looks like a race — is there a reason it's not awaited? Maybe related to the worker thread?"

Sometimes there's context you don't have. Sometimes the author will say "oh you're right, that's a bug" — then it's a finding. The question form respects the author; the assertion form doesn't.

## The "don't rewrite" rule

Don't recommend rewrites. Ever. If the current code has a defect, recommend fixing the defect. If the architecture is wrong, recommend an incremental migration sequence. If the framework is bad, recommend evaluating alternatives.

"Rewrite this" is asking for:
- Weeks of work
- High regression risk
- High review burden
- High test re-creation cost

Almost always the wrong call. The exception: the system is so broken that incremental fixes cost more than a rewrite — and that decision is the team's, not the reviewer's.

## Time budget per finding

| Phase | Per finding |
|-------|-------------|
| Identify candidate | 30 seconds (pattern match) |
| Verify it's real | 2-5 minutes (read code, check context) |
| Classify severity | 30 seconds |
| Write the report entry | 2 minutes |
| Total | ~5-8 minutes per finding |

In a 1-hour review, that's 7-12 findings — about right for a focused review on a single PR or a focused audit on a single module.

## Output

The deliverable is the code audit report (see `assets/report_code_audit.md`). Findings table with P0/P1/P2/P3 priorities, each with line numbers and recommended next steps.

Skip:
- Stylistic nitpicks (defer to linters)
- Pattern preferences (not findings)
- Speculative concerns (no concrete cost)
- "Should be refactored" without specifics

Include:
- Correctness / security defects with line citations
- Architecture violations with evidence
- Missing tests on critical paths
- Performance issues on hot paths
- Maintenance costs with concrete examples
