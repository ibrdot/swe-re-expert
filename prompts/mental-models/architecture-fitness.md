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

## The "pattern compliance is not a goal" rule

Patterns exist to absorb volatility. If the volatility is real (the codebase actually changes in this dimension), the pattern is justified. If the volatility is speculative ("we might need to swap databases someday"), the pattern is overhead.

- **Repository pattern** is justified if you actually swap databases or run two in parallel. Not justified if you've been on Postgres for 5 years and have no migration plans.
- **Service layer** is justified if business logic is reused across multiple entry points (HTTP, CLI, queue). Not justified if there's one HTTP handler per use case.
- **Plugin architecture** is justified if you actually ship multiple plugins. Not justified if there's one implementation and "we might add more later."

Pattern-for-pattern's-sake is technical debt with extra steps.

## The "framework conventions are not leakage" rule

Auto-wired dependency injection in NestJS / Spring / Django is not "hidden coupling" — it's the framework's idiomatic way of doing things. Calling it out as a finding shows you don't understand the framework. Verify framework conventions before flagging them.

Same for:
- Generated code (don't flag the generated code; flag the generator config if it's wrong)
- Test-only architecture (don't flag test doubles as "parallel mechanisms")
- Documented exceptions (the team knows; the comment explains why)

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

## The "cycle is a finding only with concrete cost" rule

Cyclic dependencies are not inherently bad. They're a finding only when:

- They cause build/test coupling (one module change forces rebuilding/testing another)
- They cause deployment coupling (one module's release blocks another's)
- They cause failure propagation (one module's bug cascades to another)
- They cause ownership ambiguity (no one knows who's responsible for the boundary)

If the cycle is between two functions in the same file, in the same module, owned by the same team — not a finding. If it's between modules owned by different teams, with different release cadences — finding.

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

If the current shape is one of several reasonable choices, that's not a finding. The recommendation should be specific about the **constraint** the current shape violates, not the **pattern** it should adopt.

## The "materiality gate"

For every candidate, require a concrete cost at the system's evidenced scale:

- Correctness defect (a bug, an inconsistency)
- Security hole (an attack vector)
- Change amplification (a change requires touching N files)
- Deployment coupling (a release requires coordinating M teams)
- Recurring maintenance pain (the team has incident reports / sprint tickets about it)
- Test fragility (tests break on every refactor)

Pattern preference, theoretical purity, "I would have written it differently" — these are NOT material costs. They are not findings.

## The "smallest safe outcome" rule

For every finding, recommend the smallest change that resolves it:

- Invert the dependency direction (one import change)
- Extract the shared logic into a new module (one PR)
- Add a boundary type (one interface)
- Document the constraint (one ADR)

Multi-step migrations are valid for large findings, but should be ordered by prerequisite with rollback paths. "Rewrite" is almost never the right recommendation.

## The "evidence at evidenced scale" rule

Don't recommend changes for problems the team doesn't have. If the codebase serves 100 users and you're recommending sharding because "at 10M users this won't scale" — that's not a finding. The team will refactor when they hit the wall; until then, the complexity you're recommending is premature.

The exception is when the team has stated a growth target ("we expect to be at 1M users next year"). Then the future scale is evidenced, and recommendations can target it.

## How to write the architecture finding

In the report:

```
| P1 | Domain layer imports from controller layer |
| `domain/user.go:12: import "../controllers"` |
| Creates cycle: domain → controller → domain. Forces
| controller changes to ship with domain changes;
| breaks the team's intended independent deploy. |
| Recommended: invert — controller imports domain;
| domain exposes interface, controller injects impl.
| ~50 LOC change, single PR, rollback trivial. |
```

Notice: the finding cites the import (evidence), the consequence (deployment coupling — material cost), the recommended change (bounded, reversible), and the LOC estimate (so the reader can gauge effort). No pattern names dropped just to sound smart. No "you should use DDD" lecturing.

## Final hook

> "If I can't name the concrete cost at the team's actual scale, this isn't an architecture finding — it's a preference. Preferences don't go in the report."
