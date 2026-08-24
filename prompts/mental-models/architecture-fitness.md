# Architecture Fitness — Judging Architecture Without Pattern Bias

The hardest thing in architecture review is **not** recommending changes just because the code doesn't match a pattern you like. The current architecture is one of several reasonable shapes. Judge it on whether it serves the product, not on whether it matches your preferred textbook.

## The 5 questions

For every architecture candidate (a layer, a boundary, a pattern, a module structure), ask:

1. **Does it serve the current product complexity?**
2. **Does it have a present defect?**
3. **Is there an acceptable alternative the current shape already satisfies?**
4. **Does the defect create a concrete, measurable cost?**
5. **Is the recommended change bounded and reversible?**

If all five pass, it's a finding. If any fails, it's an observation.

## The "executable behavior outranks documentation" rule

Don't audit the README. Audit the code. The README says it's a microservices architecture; the code shows five services that all share a database, all deploy together, and all fail together. The executable behavior is what runs.

Drift between docs and code is a finding only when it causes a concrete cost (someone makes a wrong assumption based on the docs, ships a bug, escalates an incident). Otherwise it's an observation.

### What "executable behavior" includes

- Build graph: what gets compiled with what
- Deployment graph: what gets released together
- Data graph: what reads/writes what data store
- Call graph: what calls what (across module / package / service boundaries)
- Failure graph: when X fails, what else breaks
- Owner graph: who is on-call for what (this may be in the org chart, not the code)

If the call graph says "modules A and B are independent" but the deployment graph says "A and B ship in the same container," they're not independent. The deployment graph wins.

## The "pattern compliance is not a goal" rule

Patterns exist to absorb volatility. If the volatility is real (the codebase actually changes in this dimension), the pattern is justified. If the volatility is speculative ("we might need to swap databases someday"), the pattern is overhead.

- **Repository pattern** is justified if you actually swap databases or run two in parallel. Not justified if you've been on Postgres for 5 years and have no migration plans.
- **Service layer** is justified if business logic is reused across multiple entry points (HTTP, CLI, queue). Not justified if there's one HTTP handler per use case.
- **Plugin architecture** is justified if you actually ship multiple plugins. Not justified if there's one implementation and "we might add more later."
- **Event sourcing** is justified if you need the audit log or time-travel queries. Not justified if you have CRUD needs and "might want event sourcing later."
- **CQRS** is justified if read and write have different scaling or consistency needs. Not justified if your read load is 5x your write load at small absolute numbers.

Pattern-for-pattern's-sake is technical debt with extra steps.

## The "framework conventions are not leakage" rule

Auto-wired dependency injection in NestJS / Spring / Django is not "hidden coupling" — it's the framework's idiomatic way of doing things. Calling it out as a finding shows you don't understand the framework. Verify framework conventions before flagging them.

Same for:
- Generated code (don't flag the generated code; flag the generator config if it's wrong)
- Test-only architecture (don't flag test doubles as "parallel mechanisms")
- Documented exceptions (the team knows; the comment explains why)
- Framework-specific patterns (Spring's `@Transactional`, Nest's `@Module`, Django's `Meta` — these are framework, not architecture)

## The "modernization is justified by present defect" rule

"Modernize to X" is justified only if:

- The current state has a defect the modernization fixes (concrete, not theoretical)
- The modernization enables a capability the team actually needs (named, not speculative)
- The migration is bounded and reversible

"We should use generics" is not a justification. "This code has 6 type-assert branches that would collapse to 1 with generics, and we just hit a runtime panic at line 47 because of an unexpected type" is.

## The "folder names are low-confidence evidence" rule

A folder called `services` doesn't prove the code follows a service-oriented design. A folder called `domain` doesn't prove DDD. Read the code. The folder is a hint about intent; the code is the truth.

Same for:
- File names (`user_service.py` might just be a bag of functions)
- Class names (`UserRepository` might bypass the database)
- Module structure (`packages/core/` might depend on `packages/web/`)

### How to verify architecture claims from code

For each architecture claim, verify by reading the actual code:

| Claim | Verification |
|-------|--------------|
| "The system has clean layered architecture" | Check `import` statements in each layer — does `domain/` import from `controllers/`? If yes, the layers aren't clean. |
| "The system is microservices" | Check the deploy graph — do services deploy independently? Check the data graph — do they share a database? If either is shared, they're distributed monolith. |
| "The system uses event-driven architecture" | Check the actual transport — are events flowing? Or is there a synchronous "event bus" that's just a fancy function call? |
| "The system is hexagonal architecture" | Check the dependency direction — do adapters point inward to the domain? Or does the domain import the adapter? |
| "The system follows repository pattern" | Check if Repository actually abstracts the data source — or is it `class UserRepository { def find(id) = SQL("SELECT ...") }` with no abstraction boundary? |
| "The system is serverless" | Check the cold-start budget and the runtime — if it's serverless-shaped but with long-lived connections, it's not serverless in operation. |

## The "cycle is a finding only with concrete cost" rule

Cyclic dependencies are not inherently bad. They're a finding only when:

- They cause build/test coupling (one module change forces rebuilding/testing another)
- They cause deployment coupling (one module's release blocks another's)
- They cause failure propagation (one module's bug cascades to another)
- They cause ownership ambiguity (no one knows who's responsible for the boundary)

If the cycle is between two functions in the same file, in the same module, owned by the same team — not a finding. If it's between modules owned by different teams, with different release cadences — finding.

### Cycle detection commands

| Tool | Command |
|------|---------|
| Python | `pydeps --max-bacon=0 --show-deps src/ \| dot -Tpng -o deps.png` (visual) |
| Python (text) | `pydeps --show-deps src/ 2>&1 \| sort -u` |
| Go | `go mod graph` for module-level; `go-calldeps` (third-party) for package-level |
| JavaScript/TypeScript | `madge --circular --extensions ts,js src/` |
| C/C++ | `cpp-dependencies` or hand-rolled `#include` graph |
| Rust | `cargo modules generate graph` or `cargo-deps` |

When reporting a cycle, include the actual cycle path (the chain of imports), not just "modules A and B form a cycle."

## The "parallel mechanism is a finding only if duplicated" rule

Two ways to do the same thing (manual config + DI; old REST + new gRPC for the same service) is a finding only if both are actively used. If one is being phased out, it's a migration in progress, not a finding. If both have been used for years without convergence, that's a finding.

## The "dead code is a finding only with consumer check" rule

Don't call code dead without verifying no consumer. Aliases, re-exports, generated code, reflection, runtime loading, plugin discovery — all can reference code that grep doesn't find. Check before flagging.

If unsure, mark as `SUSPECTED` and explain how to verify (e.g., "set up the runtime and observe whether X is invoked").

## The "acceptable alternative gate"

For every candidate finding, ask: **is the current shape one of several reasonable choices?**

- Monolith vs microservices: both can be right depending on team size, deployment model, scale
- Direct ORM calls vs Repository pattern: both can be right depending on testability needs and reuse
- REST vs gRPC: both can be right depending on consumer needs
- Layered vs feature-folder: both can be right depending on team preference
- Sync vs async messaging: both can be right depending on latency and decoupling needs
- Direct call vs event bus: both can be right depending on consumer count and consistency needs

If the current shape is one of several reasonable choices, that's not a finding. The recommendation should be specific about the **constraint** the current shape violates, not the **pattern** it should adopt.

## The "materiality gate"

For every candidate, require a concrete cost at the system's evidenced scale:

- Correctness defect (a bug, an inconsistency)
- Security hole (an attack vector)
- Change amplification (a change requires touching N files)
- Deployment coupling (a release requires coordinating M teams)
- Recurring maintenance pain (the team has incident reports / sprint tickets about it)
- Test fragility (tests break on every refactor)
- Performance degradation (measured, not theoretical)
- Scaling ceiling (the architecture can't serve the next 10x without rewrite — and the team has a 10x target)

Pattern preference, theoretical purity, "I would have written it differently" — these are NOT material costs. They are not findings.

## The "smallest safe outcome" rule

For every finding, recommend the smallest change that resolves it:

- Invert the dependency direction (one import change)
- Extract the shared logic into a new module (one PR)
- Add a boundary type (one interface)
- Document the constraint (one ADR)
- Break a cycle by extracting the shared dependency (one PR)

Multi-step migrations are valid for large findings, but should be ordered by prerequisite with rollback paths. "Rewrite" is almost never the right recommendation.

## The "evidence at evidenced scale" rule

Don't recommend changes for problems the team doesn't have. If the codebase serves 100 users and you're recommending sharding because "at 10M users this won't scale" — that's not a finding. The team will refactor when they hit the wall; until then, the complexity you're recommending is premature.

The exception is when the team has stated a growth target ("we expect to be at 1M users next year"). Then the future scale is evidenced, and recommendations can target it.

## Per-architecture-shape assessment templates

### Monolith assessment

For a monolith, the typical findings (or non-findings):

| Symptom | Is it a finding? | Why |
|---------|------------------|-----|
| Single deployable, all in one process | No | This is the definition; not a defect by itself |
| Module boundaries unclear | Finding if change amplification measured | Cite the PRs that touch multiple modules unexpectedly |
| God classes with implicit coupling | Finding if maintenance pain evidenced | Cite git log showing the same files changed together repeatedly |
| Tests are slow because everything loads | Finding if it blocks CI | Cite the CI run time; if > 10 min, finding |
| Single database, no service boundaries | No | Monolith with single DB is normal |
| "Should split into microservices" | No — unless concrete cost evidenced | Premature split is worse than monolith |

### Microservices assessment

For a microservices architecture, the typical findings:

| Symptom | Is it a finding? | Why |
|---------|------------------|-----|
| Services share a database | Finding (data coupling) | Breaks the service boundary; cite the shared tables |
| Services share a deploy pipeline | Finding (deployment coupling) | Defeats independent deployment; cite the CI pipeline |
| One service failure cascades to others | Finding (failure propagation) | Cite the incident report |
| Service-to-service synchronous calls with no timeout | Finding (availability risk) | Cite the call graph; recommend timeout + circuit breaker |
| No service ownership (no team owns service X) | Finding (ownership ambiguity) | Check the on-call rotation; if "everyone" owns X, finding |
| Service boundaries follow org chart, not domain | Observation (Conway's Law is fine) | Not a finding unless the domain is mismatched to the org |
| Inter-service communication over internal HTTP without retry | Finding (reliability) | Cite the failure scenario; recommend retry-with-backoff or async transport |

### Event-driven assessment

For an event-driven architecture:

| Symptom | Is it a finding? | Why |
|---------|------------------|-----|
| Events are fire-and-forget without retry | Finding (reliability) | Cite the data-loss scenario |
| No event schema versioning | Finding (evolvability) | Cite the consumer breakage on schema change |
| Synchronous "event bus" (just a function call) | Finding (architecture mismatch) | Either rename or make async; cite the latency impact |
| Events have side effects beyond their name | Finding (semantic mismatch) | `UserCreated` event triggers email send AND billing AND... — split or rename |
| No dead-letter queue for failed consumers | Finding (operability) | Cite the silent failure scenario |
| Single producer, single consumer | Observation (over-engineered) | If there's no fan-out, message bus is overhead; direct call is fine |
| Event storm (hundreds of event types) | Finding if no catalog | Cite the consumer onboarding cost; recommend event catalog tool |

### Layered architecture assessment

For a layered architecture:

| Symptom | Is it a finding? | Why |
|---------|------------------|-----|
| Layer N+1 imports from layer N-1 (skipping N) | Finding (layer violation) | Cite the import line |
| Domain layer imports from UI layer | Finding (inverted dependency) | Cite the import line; recommend dependency inversion |
| Layer N+1 leaks abstractions from N-1 | Finding (leaky abstraction) | Cite the leaked type in the higher layer's public API |
| Every layer has a "utils" package | Observation (common, low confidence) | If utils are used across layers without ownership, finding |
| Tests can only run with all layers loaded | Finding (test isolation) | Cite test setup time; recommend interface mocks |

## How to write the architecture finding

In the report:

```
| P1 | Domain layer imports from controller layer |
| `domain/user.go:12: import "../controllers"` |
| Creates cycle: domain -> controller -> domain. Forces
| controller changes to ship with domain changes;
| breaks the team's intended independent deploy. |
| Recommended: invert — controller imports domain;
| domain exposes interface, controller injects impl.
| ~50 LOC change, single PR, rollback trivial. |
```

Notice: the finding cites the import (evidence), the consequence (deployment coupling — material cost), the recommended change (bounded, reversible), and the LOC estimate (so the reader can gauge effort). No pattern names dropped just to sound smart. No "you should use DDD" lecturing.

## The "anti-pattern cases" catalog — to recognize and not recommend

These are NOT findings — they're acceptable shapes often misread as defects:

- **Service Locator pattern** — fine for plugin-style architectures where DI is overkill
- **Anemic domain model** — fine if the domain has no behavior (CRUD apps)
- **Singleton** — fine for stateless utility singletons; only flag if stateful + mutable
- **Active Record** — fine for simple CRUD; only flag if the model grows behavior that doesn't belong
- **God class** — finding only if it has high change frequency (Gate 2); otherwise it's a structural observation
- **Long function** — finding only if it has a defect or excessive duplication; otherwise it's a structural observation
- **Inconsistent naming** — finding only if it causes confusion evidenced in PRs / incidents

## Verification checklist — for the agent before flagging an architecture finding

- [ ] Passes the 5-question test (serves complexity? present defect? acceptable alternative? measurable cost? bounded change?)
- [ ] Materiality gate passed (concrete cost at evidenced scale, not theoretical)
- [ ] Cycle/parallel-mechanism/dead-code claim verified with concrete evidence (not just grep result)
- [ ] Folder/file/class name is not the primary evidence (code is)
- [ ] Framework convention verified before flagging (not "Spring DI is leakage")
- [ ] Recommendation is bounded (one PR or small sequence with rollback paths)
- [ ] Recommendation is reversible (trivial/low/medium rollback cost)
- [ ] No "rewrite" or "migrate to X" in the recommendation (those are architecture migrations, different stakeholders)
- [ ] No "should use DDD/CQRS/event-sourcing/microservices" without concrete defect
- [ ] No pattern preference dressed up as finding
- [ ] Acceptable alternatives explicitly considered and dismissed with specific constraint violation
- [ ] No future-scale claims without stated team growth target

If any checkbox is unchecked, the architecture claim is a preference — not a finding. Preferences go in observations, not findings.

## Final hook

> "If I can't name the concrete cost at the team's actual scale, this isn't an architecture finding — it's a preference. Preferences don't go in the report."
