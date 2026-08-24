# SWE Playbook — Code Review, Refactoring, Architecture Audit

This file is the agent's reference whenever the target is **source code** rather than a binary. It covers tool routing, evidence rules, the anti-pattern catalog with severity, the refactor priority matrix, and a modernization decision tree.

The goal throughout is **fitness**, not purity. The current architecture is one of several reasonable shapes given the constraints; do not recommend a rewrite unless there's a present defect the rewrite fixes.

---

## Tool routing

| Need | Preferred tool | Fallback |
|------|-----------------|----------|
| File & module inventory | `ls`, `find`, `git ls-files` | `Glob` patterns |
| Symbol & call graph | Language server, `ctags`, `cscope`, `tree-sitter` + custom query | `Grep` + targeted inspection |
| Code smell detection | `ruff` (Python), `golangci-lint` (Go), `clippy` (Rust), `clang-tidy` (C/C++) | Manual `Grep` for patterns |
| Dead code | `vulture` (Python), `deadcode` (Go), `cargo udeps` (Rust), `cppdepend` or build with `-Wusage` | `git grep` + import graph |
| Cyclomatic complexity | `radon cc` (Python), `gocyclo` (Go), `rust-code-analysis` (Rust), `lizard` (any) | Manual inspection |
| Dependency direction | Build files + AST-level import scan | `grep "^import\|^#include\|^use"` |
| Test signal | `pytest --cov`, `go test -cover`, `cargo tarpaulin` | Run tests, count paths |

When a tool isn't installed, fall back rather than block. The script `scripts/swe_audit.py` bundles the most common ones; use it for triage.

---

## Evidence rules

These define what counts as proof. The agent must hold itself to them, not just the user.

- **Executable behavior outranks documentation.** A module's real exports are its public API, regardless of what `README` says. Drift is a finding only when it causes a concrete cost.
- **A cycle is a finding only when it predicts a cost.** Build/test coupling, ownership ambiguity, or failure propagation. Otherwise, it's just how the code is shaped.
- **Pattern compliance is not a goal.** Patterns exist to absorb volatility. If there's no volatility, the pattern may be overhead. Judge by fitness, not by pattern-match.
- **Framework conventions require framework-aware verification.** Auto-wired DI in NestJS / Spring / Django doesn't count as "hidden coupling" if it's idiomatic.
- **Modernization is justified only by a present defect or measurable simplification.** "We could use newer feature X" is not a finding.
- **Folder-name inference is low-confidence.** A folder called `services` doesn't prove the code follows a service-oriented design. Read the code.
- **Prior audit baselines separate new, resolved, and accepted debt.** They don't make active defects disappear. Resolved items in the baseline should be removed from the new report.
- **Shared design docs are intent evidence, never authoritative for the current state.** Their absence is not a defect. Their presence never outranks executable behavior.

---

## Anti-pattern catalog (with severity)

For each, the **trigger** (what to look for), **why it matters** (the concrete cost), and **default severity** (P0-P3) are listed. The default may be promoted or demoted based on context — that's the agent's judgment.

### Correctness / security (P0 candidates)

| Pattern | Trigger | Why it matters |
|---------|---------|----------------|
| Buffer misuse in C/C++ | `memcpy`/`strcpy`/`sprintf` without bounds; `gets()`; manual pointer arithmetic on user input | Memory corruption, RCE |
| SQL string concatenation | `"SELECT ... WHERE x = " + user_input` | SQLi |
| Command injection | `os.system`, `subprocess.run(shell=True)`, `exec.Command` with concatenated user input | RCE |
| Path traversal | User input joined into filesystem paths without normalization | Arbitrary file read/write |
| Insecure deserialization | `pickle.loads`, `yaml.load` (unsafe), `ObjectInputStream`, `Marshal.Load` | RCE |
| TOCTOU | Time-of-check to time-of-use on filesystem / permissions | Privilege escalation |
| Crypto misuse | ECB mode, homebrew crypto, predictable RNG for keys, hard-coded keys | Confidentiality loss |
| Race condition | Shared mutable state across goroutines/threads without sync | Data corruption, intermittent bugs |
| Off-by-one in loop bounds | `<` vs `<=`, `i = 0; i <= len` | Silent wrong behavior |
| Integer overflow in safety-critical paths | Unchecked arithmetic on user-controlled sizes | Memory corruption |

### Architectural (P1 candidates — promote to P0 if release-blocking)

| Pattern | Trigger | Why it matters |
|---------|---------|----------------|
| Hidden writes in read-named functions | `getUser(id)` that also writes to a log table or fires events | Surprising side effects, test brittleness |
| Leaky abstraction | Framework types (HttpRequest, ORM Session) in domain layer | Coupling, hard to test domain |
| Parallel mechanisms | Two ways to do the same thing — e.g., manual config + DI; old REST + new gRPC for same service | Confusion, drift, duplicated maintenance |
| Dead code with no consumer | Exported but unreferenced (after alias/reflection check) | Maintenance cost, confusion |
| God object / module | One file/class > 500 LOC and > 10 public methods, mixing concerns | Change amplification, test fragility |
| Cross-layer transaction | DB transaction started in controller, committed in service, with hops in between | Partial-failure correctness |
| Booleans-as-modes | `process(data, is_async, is_retries, is_dry_run, ...)` | Combinatorial test explosion, API confusion |
| Parameter sprawl | > 5 positional args on a frequently-called function | Call-site errors, refactor pain |
| Stringly-typed | `if mode == "fast"` scattered across files | No compile-time safety |
| Speculative generality | Interfaces with one impl, factories with one product, "for future use" code | YAGNI violation, dead weight |

### Maintainability (P2 candidates)

| Pattern | Trigger | Why it matters |
|---------|---------|----------------|
| Nested conditionals > 3 levels | `if if if if` in same function | Readability, bug-prone |
| Magic numbers | Unexplained literals in business logic | Readability, drift |
| Long method | > 80 LOC with multiple responsibilities | Hard to test, hard to read |
| Duplicated blocks | Same logic in 3+ places (after AST comparison) | Drift, double-maintenance |
| Fragile test | Tests that break on any refactor; tests that mock too much | Erodes trust in test suite |
| Comment-as-spec | Outdated comments that contradict code | Misleading future readers |
| Inconsistent naming | Same concept with multiple names (userId, uid, user_id, id) | Readability, search failure |

### Style / nitpicks (P3 — usually don't report unless blocking review)

- Import ordering, formatting, brace style → defer to linters (Prettier, Black, rustfmt, gofmt)
- Trivial typos
- "I would have named it differently"

---

## Refactor priority matrix

When the user asks for refactoring, prioritize by **impact × ease**. Don't refactor everything; pick the moves that pay back fastest.

| Priority | Impact | Ease | Action |
|----------|--------|------|--------|
| 1 | High (correctness / security) | Any | Fix immediately. P0 defects block everything else. |
| 2 | High (architectural) | High | Tackle — usually small, well-bounded extraction. |
| 3 | Medium (maintainability) | High | Tackle — quick wins build momentum. |
| 4 | High (architectural) | Low | Plan — break into a migration sequence, deliver in bounded changes. |
| 5 | Medium | Low | Defer — only if recurring pain. |
| 6 | Low | Any | Don't refactor — not a finding. |

The default cadence: **fix correctness first, extract small wins second, plan big migrations third, ignore the rest.**

---

## Modernization decision tree

Modernization is justified only when **the present state has a defect the modernization fixes**. "Newer is better" is not a justification.

```
Is there a concrete defect in the current state?
├── No  → DO NOT MODERNIZE. Note as observation, not finding.
├── Yes → Can the defect be fixed in-place (bounded change)?
│   ├── Yes → Fix in-place. Keep current tooling/version.
│   └── No  → Does a modernization exist that fixes the defect with bounded migration risk?
│       ├── Yes → Plan the migration. Sequence changes. Keep rollback path. Verify with tests.
│       └── No  → Document the defect and the constraint. Don't speculative-migrate.
```

Modernization candidates by language (verify before recommending):

- **Python**: 3.13+ features (better error messages, free-threaded builds), `uv` for tooling, type hints + `mypy`/`basedpyright`, `pydantic v2`, `ruff` replacing `flake8`+`black`+`isort`
- **Go**: generics adoption (where it removes code duplication without harming readability), `slog` for structured logging, context-aware APIs
- **Rust**: 2024 edition, `async fn` in traits, `let-else`, `Result::Err` inspection patterns
- **C/C++**: C++20/23 features (`std::span`, ranges, concepts, modules where supported), `std::filesystem`, smart pointers everywhere, `clang-tidy` modernize checks

For each, verify the toolchain in use supports the feature before recommending. "Upgrade your compiler" is sometimes the right finding, sometimes not — depends on the project's deployment constraints.

---

## Reviewer mindset (when giving feedback)

Code review feedback should be:

- **Specific and actionable**: "line 47: this `memcpy` can overflow when `src > 15` bytes — bound it with `strnlen(src, sizeof(dst)-1)`"
- **Educational, not judgmental**: explain why, so the author learns
- **Prioritized**: 🔴 blocking / 🟡 important / 🟢 nit / 💡 suggestion / 📚 learning / 🎉 praise
- **Collaborative**: "have you considered X?" beats "use X"

Don't review formatting (use linters). Don't review import ordering. Don't nitpick names unless they actively hurt readability.

---

## Output contract — for code audit and architecture audit

Use the templates in `assets/report_code_audit.md` and `assets/report_architecture.md`. The agent may abridge, but must preserve: verdict, summary, evidence table, findings table with severities, limitations, recommended next step. Never add "End of Report" markers.
