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

## Per-language audit patterns — quick reference

The Phase 1 pattern scan works best when adapted per language. Use these per-language cheat sheets:

### Python
```bash
# Security (highest signal)
rg "eval\(|exec\(" --type py -g '!tests/**'    # Code injection
rg "os\.system|subprocess\..*shell=True"        # Command injection
rg "pickle\.loads|yaml\.load\((?!Loader)"      # Insecure deserialization
rg "MD5|SHA1\b|DES|RC4|ECB"                      # Weak crypto
rg "Math\.random|random\.randint.*auth|secret"  # Insecure RNG for security
rg "password.*=.*[\"'].*[\"']"                   # Hardcoded credentials
rg "secret.*=.*[\"'].*[\"']"                     # Same
rg "api[_-]?key.*=.*[\"']"                      # Same
rg "DEBUG.*=.*True"                              # Debug mode in production path
rg "allow_origin.*\*"                            # CORS open
rg "verify.*=.*False"                            # SSL verification disabled

# Concurrency
rg "Lock\(\)|threading\.Lock"                   # Verify usage pattern
rg "asyncio\.create_task"                        # Verify task tracking
rg "global\s+\w+"                                # Global mutable state

# Code smells
rg "TODO|FIXME|XXX|HACK"                          # Tech debt markers
rg "print\(" --type py                            # Debug logging left in
rg "^\s*#.*defunct|deprecated"                   # Commented-out code
rg "except\s*:"                                   # Bare except
rg "except\s+Exception\s*:"                       # Over-broad except
rg "^\s*pass$"                                    # Stubs / placeholders
```

### Go
```bash
# Security
rg "exec\.Command.*\+|exec\.Command.*Sprintf"    # Command injection
rg "fmt\.Sprintf.*sql|query.*\+"                  # SQL injection (Go doesn't have parameterized via Sprintf)
rg "MD4|MD5|SHA1\b|DES|RC4|ECB"                  # Weak crypto
rg "math/rand.*auth|secret|token|password"       # Insecure RNG for security
rg "password.*=.*[\"']"                           # Hardcoded credentials

# Concurrency
rg "go func\(\)"                                  # Verify goroutine lifecycle
rg "sync\.Mutex|sync\.RWMutex"                   # Verify usage
rg "global\s+map\["                              # Global mutable map (race risk)
rg "select\s*\{.*case.*<-.*:"                    # Verify channel direction
rg "interface\{\}"                                # Loses type safety
rg "\.Default\(\)"                                # HTTP client with default timeout (often no timeout)

# Code smells
rg "TODO|FIXME|XXX|HACK"                          # Tech debt
rg "panic\("                                      # Should usually be error return
rg "_ = .*err"                                    # Error swallowing
rg "if err != nil \{ return err \}"               # Lost context; use fmt.Errorf %w
```

### Rust
```bash
# Security
rg "unsafe"                                       # Manual memory unsafety; review each
rg "unwrap\(\)" --type rust                       # Panic on None/Err
rg "expect\("                                      # Same (but with message)
rg "as\s+(u8|i8|u16|i16|u32|i32|u64|i64|usize|isize)" # Truncation cast
rg "MD5|SHA1\b|DES|RC4|ECB"                       # Weak crypto
rg "password.*=.*[\"']"                            # Hardcoded credentials

# Concurrency
rg "Arc<Mutex"                                    # Verify contention
rg "Arc<RwLock"                                   # Verify read/write ratio
rg "unsafe impl Send"                             # Manual thread-safety claim
rg "unsafe impl Sync"                             # Same
rg "tokio::spawn"                                 # Verify task lifecycle
rg "\.await"                                       # Async code; verify cancellation safety

# Code smells
rg "todo!\("                                       # Stubs
rg "unimplemented!\("                              # Stubs
rg "panic!\("                                      # Should usually be Result
rg "\.clone\(\)"                                   # Often unnecessary; check
rg "Box<dyn .*Error"                              # Loses error type info
rg "Option<Option"                                 # Nested Option (usually a smell)
rg "_: &.*&.*&"                                    # Triple-reference (rare and confusing)
```

### C / C++
```bash
# Security (high signal)
rg "gets\(|strcpy\(|sprintf\(|strcat\("            # Buffer overflow sinks
rg "memcpy\("                                      # Verify size
rg "system\(|popen\(|execl\(|execve\("             # Command exec
rg "printf\(|fprintf\(.*\w"                        # Format string if arg is user input
rg "MD5|SHA1\b|DES|RC4|ECB"                        # Weak crypto
rg "password\s*=\s*\""                             # Hardcoded credentials

# Memory
rg "new\s+\w+"                                     # Verify delete path
rg "malloc\("                                      # Verify free path
rg "free\("                                        # Verify not double-free
rg "\*\(.*\*\)"                                    # Pointer-to-pointer-to-pointer (smell)

# Concurrency
rg "pthread_create"                                # Verify thread join
rg "std::thread"                                   # Same
rg "atomic<|std::atomic"                           # Verify memory order
rg "std::mutex"                                    # Verify lock scope

# Code smells
rg "TODO|FIXME|XXX|HACK"                           # Tech debt
rg "reinterpret_cast"                              # Type punning; review
rg "const_cast"                                    # Usually a smell
rg "dynamic_cast"                                  # Often a sign of design issue
rg "delete\s+\w+;"                                 # Manual delete (smell in C++)
```

## Audit priority matrix — by codebase type

Different codebases have different priorities. Adapt your audit order accordingly:

| Codebase type | Audit first | Audit later | Skip |
|----------------|-------------|--------------|------|
| Web service (HTTP entry) | Auth, input validation, SQL queries, ORM usage, file upload, SSRF | Logging, metrics, config | Internal utilities |
| CLI tool | Arg parsing, file I/O, env var usage | Logging | Tests |
| Library / SDK | Public API surface, input validation, error returns | Internal helpers | Examples |
| Daemon / service | IPC, file perms, env var usage, signal handling | Logging | CLI subcommand handlers |
| Embedded | Memory safety, interrupt safety, hardware register access | Logging | Tests |
| Game / graphics | Render loop correctness, asset loading | Logging | Build scripts |
| Batch job | Input parsing, file I/O, error handling on failure paths | Logging | Tests |

## The "audit the data path" rule

For any codebase, the audit's highest-ROI focus is the data path:
- Where does user input enter?
- Where does it get transformed?
- Where does it reach a sink (DB, shell, file, network)?
- Where are the validation checkpoints?
- Where are the error handling gaps?

Trace one full data path end-to-end per audit. Even if you only flag 2 findings from that trace, they'll be high-confidence (because you saw the whole path) — better than 10 isolated pattern matches.

## The "audit the failure paths" rule

Codebases have happy paths (well-tested, well-reviewed) and failure paths (often untested, often buggy). Spend disproportionate time on failure paths:
- Error handling branches
- Timeout / retry / cancellation logic
- Cleanup / rollback logic
- Partial-failure scenarios (3-of-5 subsystems succeed; what happens?)
- Resource exhaustion (OOM, disk full, too many open files)

These are where P0 bugs hide. Happy paths rarely have undiscovered bugs.

## Time budget per finding

| Phase | Per finding |
|-------|-------------|
| Identify candidate | 30 seconds (pattern match) |
| Verify it's real | 2-5 minutes (read code, check context) |
| Classify severity | 30 seconds |
| Write the report entry | 2 minutes |
| Total | ~5-8 minutes per finding |

In a 1-hour review, that's 7-12 findings — about right for a focused review on a single PR or a focused audit on a single module.

For a multi-module audit (2-4 hours), expect 20-40 findings. Order by priority; the top 10 carry 80% of the value.

## Cross-references

- `mental-models/evidence-vs-assertion.md` — every audit finding cites a file:line
- `mental-models/refactor-decisions.md` — for findings that are refactor candidates (apply 4-gate test before flagging)
- `mental-models/architecture-fitness.md` — for findings that are architectural (apply 5-question test)
- `swe-playbooks/refactor-prioritization.md` — for sequencing refactor findings from the audit
- `swe-playbooks/dead-code-confirmation.md` — for findings that are "this code is dead"
- `swe-playbooks/test-quality-review.md` — for findings about test coverage
- `swe-playbooks/security-review-thinking.md` — for security-specific findings
- `swe-playbooks/perf-review-thinking.md` — for performance-specific findings
- `swe-playbooks/concurrency-bugs.md` — for concurrency-specific findings
- `swe-playbooks/modernization-gates.md` — for findings that are "upgrade to X"
- `swe-playbooks/dependency-analysis.md` — for findings about dependency issues
- `assets/report_code_audit.md` — the output template
- `meta/evidence-checklist.md` — self-check before submitting the audit report

## Verification checklist — for the agent before submitting the audit report

- [ ] Phase 1 pattern scan completed across the codebase (per-language cheat sheets)
- [ ] Phase 2 critical flow trace completed on at least one data path end-to-end
- [ ] Phase 3 test quality assessed on the modules under audit
- [ ] Phase 4 filter applied — every finding passes the 4-gate test
- [ ] Findings ordered P0 first, then P1, P2, P3
- [ ] Every finding cites a file:line
- [ ] Every finding has a concrete consequence (not "looks bad")
- [ ] Every finding has a bounded recommendation (not "refactor this")
- [ ] Every P0 finding has at least 2 independent evidence types (per `evidence-vs-assertion.md`)
- [ ] No style nitpicks in the report (defer to linters)
- [ ] No pattern preferences dressed as findings
- [ ] No "should use X" architectural recommendations without concrete defect
- [ ] No "rewrite this" recommendations
- [ ] Failure paths audited disproportionately (per "audit the failure paths" rule)
- [ ] Data path traced end-to-end at least once (per "audit the data path" rule)
- [ ] Cross-references to sibling playbooks added where relevant

If any checkbox is unchecked, the audit report is a draft — fix before submission.
