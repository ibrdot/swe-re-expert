# SWE Thinking — How a Senior Engineer Reads a Codebase

> The mental model that distinguishes a senior reviewer from someone reading code top-to-bottom. A senior gets to the material defects in 1-2 hours where a junior spends a day reading every file. The senior doesn't read more — they read *with a purpose*.

## 1. The mindset

A senior engineer doesn't read code top-to-bottom. They read with a **purpose**: answering a specific question, finding a specific bug, or making a specific change. The codebase is a map, not a novel — you don't read every street, you read the streets between where you are and where you're going.

The fundamental insight: most codebases are 80% glue (CRUD, serialization, validation, framework boilerplate, type definitions, config plumbing). The interesting 20% is in the core domain logic, the boundaries, and the hot paths. The senior's job is to find that 20% fast and not waste time on the 80%.

A junior opens `main.py` or `index.ts` and starts reading top-to-bottom. They get bored reading framework setup, confused by tangential helper functions, and reach the actual logic 4 hours later with no clear understanding. A senior opens the package manifest, looks at the entry point's signature, glances at the test directory's structure, and immediately asks "what does the most-changed file do?" — going straight to the heart of the system.

## 2. The hierarchy of questions

In order, ask:

1. **What is this?** (project type, language, framework, build system)
2. **How is it organized?** (folder structure, layers, entry points)
3. **What does it claim to do?** (README, docs, architecture diagrams)
4. **What does it actually do?** (entry points → critical flows → behavior)
5. **Where's the drift?** (docs vs reality, intended vs actual)
6. **Where's the pain?** (hot files, repeated change sets, fragile tests)
7. **What's worth fixing?** (material defects with concrete cost)

These are sequential. You can't assess drift (question 5) without knowing both the docs (question 3) and the actual behavior (question 4). You can't find the pain (question 6) without knowing where the changes happen (question 2 + git log).

## 3. Reading order — the 4-pass pattern

### Pass 1: Inventory (5-10 minutes)

- Read the README, package.json / pyproject.toml / Cargo.toml / go.mod
- `git log --oneline -20` (recent activity tells you what's actively changing)
- `git log --since=30.days.ago --numstat | sort -k3 -nr | head -20` (most-changed files = hot spots)
- Run `scripts/swe_audit.py --root . --triage` for a quick map

Don't read any source code yet. Just orient.

The output of Pass 1 should be a mental list:
- "This is a Flask REST API for orders"
- "Hot files: routes/orders.py, services/payment.py, models/order.py"
- "Tests are in tests/, look sparse based on file count"
- "Most recent commits are about payment retries — that's the active area"

### Pass 2: Critical path (10-30 minutes)

Pick ONE critical flow (the main user action, the highest-traffic endpoint, the most-changed module). Read it end to end:

- Entry point (route / handler / main)
- Orchestration (service / usecase)
- Domain behavior (entity methods)
- Persistence / external calls
- Return path

For each step, ask: **what would break this?** Race conditions, partial failures, missing input validation, error swallowing, slow queries. Note them but don't fix yet.

The point of Pass 2 is to understand ONE flow deeply. Not all flows — one. Once you understand one flow well, you can apply the same pattern to recognize the others fast.

### Pass 3: Pain points (10-30 minutes)

Look at the most-changed files from Pass 1. Read them. Ask:

- **Why is this file changed so often?** (volatility — is the abstraction wrong?)
- **What's the bug-prone pattern?** (stringly-typed flags, repeated copy-paste, missing error handling)
- **Where's the dead code?** (functions with no callers, conditionals that never fire)
- **What's the test signal?** (do tests cover the critical path or just the happy case?)

Pain-point files are where the next bug will land. They have high churn because the abstraction doesn't fit the problem; people keep patching around the edges. Recommend the abstraction fix, not the individual patches.

### Pass 4: Findings filter (5-10 minutes)

You should now have ~10-20 candidate findings. Filter ruthlessly:

- Does this predict a concrete cost? (correctness, security, change amplification, maintenance pain)
- Is there an acceptable alternative the current code already satisfies? (then it's not a finding)
- Is the evidence specific (line numbers, offsets, call sites)? (or is it "looks fragile"?)
- Is the fix bounded? (one PR? one sprint? a multi-quarter migration?)

Only findings that pass all four gates make the report. The rest are observations.

## 4. The "follow the data" trick

When the code is hard to follow, follow the data instead. Pick a piece of data (a user input, a request, a row from the DB) and trace it:

- Where does it enter? (route handler, stdin, file read)
- What transformation happens at each step? (parse → validate → enrich → store)
- Where does it cross a boundary? (controller → service → repo → DB)
- Where could it be lost, corrupted, or leaked?

Data flow is often clearer than control flow, especially in async / event-driven code.

This is especially powerful for security review: trace the user-controlled input through the system. Where does it reach a SQL query? A shell command? A path concatenation? A template render? Those are the injection points.

## 5. The "what would break this" question

For every line of code, every architectural decision, every API, ask: **what would break this?**

- A null input?
- A concurrent request?
- A network timeout?
- A malformed payload?
- A user with a different role?
- A massive input (10MB vs 1KB)?
- An empty collection?
- A negative number?
- Unicode?
- A leap second?
- Daylight saving time transition?
- A clock that goes backward (NTP adjustment)?
- A dependent service that's down?
- A dependent service that's slow (not down)?
- A duplicate request (idempotency)?
- A request that arrives during a deployment (mixed old/new code paths)?

The bugs you find by asking this question are the bugs that matter. The bugs you find by pattern-matching ("this looks like a Singleton, that's bad") are usually not real bugs.

## 6. The "fitness over fashion" rule

Don't recommend changes because the current code doesn't match a pattern you like. The current code is one of several reasonable shapes. Ask:

- Does it have a present defect? (a bug, a security hole, a perf problem)
- Is there measurable simplification? (fewer lines, fewer concepts, fewer moving parts)
- Does the change remove real volatility, or just pattern-displeasure?
- Does the team have the bandwidth for the change, or will it block more important work?
- Is there a documented or measurable pain caused by the current shape?

If yes to any — recommend. If no — note as observation, not finding.

Modernization for novelty's sake is technical debt with extra steps.

## 7. The "smallest safe next step" output

For every finding, recommend the smallest change that resolves it:

- One function extraction? → one PR
- One pattern removal? → bounded change with tests
- Layer inversion? → multi-PR migration sequence
- Framework migration? → only if there's a present defect the migration fixes

Multi-step migrations are valid but should be ordered by prerequisite, with rollback paths. "Rewrite the whole thing" is almost never the right recommendation.

The smallest safe next step has these properties:
- **Bounded** — one PR, one sprint, one quarter — never "ongoing"
- **Reversible** — if it breaks, you can roll back in <1 hour
- **Prerequisite-aware** — step 2 doesn't start until step 1 is verified
- **Measurable** — you can tell when it's done (tests pass, metric improves, etc.)

## 8. The "evidence over assertion" output

In the report, every finding must cite:

- File path + line number
- The actual code (quoted)
- The concrete consequence (a bug class, a coupling cost, a maintenance burden)
- The fix (specific, bounded)

"This looks fragile" is not a finding. "At line 47, `memcpy(dst, src, strlen(src)+1)` overflows the 16-byte stack buffer `dst` when `src` exceeds 15 bytes; bound it with `strnlen(src, sizeof(dst)-1)`" is a finding.

The difference: the first is opinion. The second is verifiable — the reader can open the file at line 47, see the `memcpy`, count the buffer size, and confirm the overflow.

## 9. The "blast radius" heuristic for refactors

Before recommending a refactor, calculate the blast radius:

| Blast radius | Size | Examples | Risk |
|---|---|---|---|
| Single function | <10 LOC | Extract a helper; rename a local | Low — single PR |
| Single file | 10-100 LOC | Extract a class; invert a local pattern | Low-Medium — single PR + tests |
| Single module | 100-1000 LOC | Replace a service with a new implementation | Medium — multi-PR migration |
| Cross-module | 1000-10000 LOC | Change a shared interface; migrate a protocol | High — multi-sprint migration |
| Architectural | >10000 LOC | Replace a database; switch from monolith to microservices | Very high — multi-quarter, may fail |

For each level, the cost grows non-linearly. A "small" refactor that touches 5 modules can take 3 sprints; an "architectural" change can take a year and not even succeed.

When recommending, prefer the smallest blast radius that resolves the finding. If the smallest blast radius is "architectural" (year+), that's a signal the finding is either too vague or genuinely a strategic-level decision — escalate to the user, don't just recommend.

## 10. The "1-line change test" for refactors

Before recommending a refactor, ask: **could the finding be fixed by changing 1 line?**

- "This file has 5 functions with similar code" — could you extract a helper? Yes — multi-line. But if the helper is shared and the variants are small, maybe a parameter is enough.
- "This controller has business logic in it" — could you move the 3 lines of business logic to the service? Yes — 1 line change (move the 3 lines).
- "This module has high cyclomatic complexity" — could you replace the nested `if` with a guard clause? Yes — 1 line change.

If 1 line works, do 1 line. If 1 line doesn't work but 10 lines do, do 10 lines. Never escalate to 1000 lines when 10 would do.

## 11. The "smell test" for testing

Bad test patterns to look for:

- Tests that assert on implementation (mock called with specific args, internal state checked)
- Tests that don't test the failure path (only happy case)
- Tests with massive setup (50-line arrange blocks — sign of poor test isolation)
- Tests that share state (one test's setup affects another's result)
- Tests that depend on test order
- Tests that mock what they don't own (mocking `requests.get`, `time.time`, `os.environ`)
- Tests with `time.sleep(N)` instead of polling / waiting on events
- Tests that have low assertion density (1 assertion per 100 lines — likely testing too much per test)
- Tests that fail intermittently (flaky = race condition or external dependency)

Good test patterns:
- Tests that assert on public API behavior (input → output)
- Tests that test the failure path (what happens when the DB is down? when the input is malformed?)
- Tests with minimal setup (5-line arrange blocks)
- Tests that are independent (no shared state)
- Tests that mock only what they own (fakes for their own interfaces, not third-party)
- Tests that poll/wait instead of sleep
- Tests with high assertion density (1 assertion per 10-20 lines)

When reviewing tests, the question to ask is: **if I refactor the implementation but keep the API, will these tests still pass?** If yes — good tests. If no — they're testing implementation, not behavior.

## 12. The "dependency direction" trick

Draw the import graph. Healthy codebases have:
- Domain layer (no imports outward)
- Application layer (imports domain)
- Presentation layer (imports application)
- Infrastructure layer (imports application or domain)

Unhealthy codebases have:
- Domain imports infrastructure (couples the business rules to a specific DB)
- Infrastructure imports presentation (couples the storage to a specific API)
- Circular imports (a→b→a — strong sign of bad layering)

`scripts/swe_audit.py` produces the import direction summary. If it shows cycles, that's a P1 architectural finding with a bounded fix: invert one of the imports.

## 13. The "where does the bug hide" map

Different bug classes hide in different places:

| Bug class | Where it hides | How to find it |
|---|---|---|
| SQL injection | String-formatted queries | `rg "execute\(f['\"]" --type py` |
| Command injection | `os.system`, `subprocess.call(shell=True)`, `exec.Command` with concatenation | `rg "os\.system|subprocess\.call.*shell=True"` |
| Path traversal | String concatenation with user input + file paths | `rg "open\(f['\"]|Path\(.*\+.*\)"` |
| SSRF | HTTP requests with user-controlled URL | `rg "requests\.(get|post)\(.*user" --type py` |
| XXE | XML parsing without disabling external entities | `rg "ET.*\|xml\.etree|lxml\.etree"` then check `resolve_entities=False` |
| Deserialization | `pickle.loads`, `yaml.load` (unsafe), `marshal.loads`, `json.loads` with custom decoders | `rg "pickle\.loads|yaml\.load\(|marshal\.loads"` |
| XSS | Template rendering with unescaped user input | `rg "render_template_string|dangerouslySetInnerHTML"` |
| Auth bypass | Missing `@login_required`, missing permission check in route | grep for routes that don't call auth middleware |
| Race condition | `if (key not in cache): cache[key] = ...` patterns | Look for check-then-act on shared state |
| Integer overflow | Arithmetic on user input without bounds check | Look for `size_t` math near `malloc` |
| Type confusion | `void*` casts, `dynamic_cast` failures | Look for unsafe casts in C++ |
| Memory leak | Missing `free` after `malloc`, missing `delete` after `new` | Look for early returns that skip cleanup |
| Use-after-free | Use of pointer after `free`/`delete` | Look for `delete x; ... x->field` patterns |

Each bug class has a search pattern. Run all of them in parallel during the audit.

## 14. The "what I don't know" honesty

End every audit with a Limitations section. List what you didn't read, what you couldn't verify, what tool you wish you had. This is the most underrated part of the report — it tells the reader how much to trust the rest.

Static-only reviews should say "I didn't run the tests, didn't profile, didn't verify runtime behavior". Architecture reviews should say "I read the executable behavior; the design docs may say different and I didn't reconcile". Honesty compounds trust over time.

Specific limitations to call out:
- "Didn't review the test/ directory" — coverage analysis incomplete
- "Didn't run `mypy` / `pylint` / `ruff`" — type/linter findings not captured
- "Didn't check dependency vulnerabilities (`pip-audit` / `npm audit`)" — supply chain not assessed
- "Didn't profile" — performance claims are static-analysis based, not measured
- "Didn't review CI/CD pipeline" — deployment-time issues not captured
- "Didn't review infrastructure-as-code (Terraform, etc.)" — infra-level issues not captured
- "Didn't review secrets management" — secrets-at-rest not assessed
- "Read N out of M files" — coverage: N/M percent
- "Spent X hours total" — depth-of-review disclosure

## 15. The "audience framing" output

Same findings, different framing per audience:

- **Engineering team**: detailed findings, code diffs, time estimates. They'll act on it.
- **Engineering manager**: executive summary + verdict + estimated effort. They'll prioritize.
- **Security team**: full security section with OWASP mapping. They'll track it.
- **Compliance / audit**: scope confirmation + verdict + limitations. They'll file it.
- **Open source maintainer**: PR-ready diffs with test coverage. They'll merge.

The data is the same; the emphasis changes. A senior tailors the report to who will read it.

## 16. The "review your own report" final pass

Before submitting, re-read your report as if you were the reader:

- Does the executive summary tell me what to do?
- Can I verify each finding in 5 minutes?
- Are the recommendations bounded and reversible?
- Are the limitations honest?
- Is the next step concrete?
- Did I include any "this looks fragile" claims without evidence?
- Did I include any "this is bad practice" claims without explaining the concrete cost?
- Did I recommend a multi-quarter migration when a 1-PR fix would suffice?
- Did I assume the team has more bandwidth than they do?

If any answer is "no", revise.

## 17. Final mental hook

> "I have N files. I want to answer question Q. What's the cheapest read that answers Q?"

If you can answer that question repeatedly, you're doing SWE review. If you can't, you're reading code — and reading code is not review.

The senior reviewer's superpower is not reading more code faster. It's asking better questions, picking cheaper signals, and recognizing when an issue is material vs. when it's pattern-displeasure. The 10x productivity gap between a senior and a junior isn't 10x speed — it's 10x *signal per line of code*.
