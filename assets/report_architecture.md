# Architecture Audit Report — {{TARGET_NAME}}

> Canonical output template for SWE architecture audits. Replace `{{...}}` placeholders with concrete values. Focus on actual behavior (not docs), fitness (not fashion), and bounded recommendations (not rewrites).

**Verdict:** PASS | CONCERNS | FAIL | BLOCKED
**Audited by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Audit scope:** {{full system / specific subsystem — list modules touched}}
**Time spent:** {{N hours}}
**Coverage:** {{N of M modules reviewed — X%}}

---

## Executive summary

{{3-5 sentences. State the verdict in plain English. Describe the actual architecture (not the documented one). Call out the most material drift between docs and behavior. Identify the highest-cost structural risk if any. Suggest the smallest bounded next step.}}

Example (good):
> CONCERNS. The system is a layered monolith (controllers → services → repos → Postgres) with an event bus for async work. The docs describe a hexagonal architecture but the actual code has the domain layer importing infrastructure (Mongo client at `domain/user.py:5`), breaking the port-adapter contract. The highest-cost risk: the order service has a synchronous HTTP call to the inventory service with no timeout, circuit breaker, or retry — under inventory service degradation, the order service blocks indefinitely. Recommend: invert the domain→infrastructure import (2 PRs, 1 day), add timeout + circuit breaker to the inventory call (1 PR, 4 hours).

## Actual architecture map

{{Describe what the system actually executes, not what the docs say. Include:}}

### Modules, packages, layers

| Layer | Modules | Owner | Deploy unit | Notes |
|-------|---------|-------|-------------|-------|
| {{Presentation}} | {{controllers, routes, views}} | {{team}} | {{service / monolith}} | {{triage note}} |
| {{Application}} | {{usecases, services}} | {{team}} | {{...}} | {{...}} |
| {{Domain}} | {{entities, value objects}} | {{team}} | {{...}} | {{...}} |
| {{Infrastructure}} | {{repos, clients, drivers}} | {{team}} | {{...}} | {{...}} |
| {{Cross-cutting}} | {{auth, logging, config}} | {{team}} | {{...}} | {{...}} |

### Critical flows

| Flow | Entry → Exit | Atomicity owner | Notes |
|------|--------------|-------------------|-------|
| {{Order placement}} | {{API → OrderService → OrderRepo → DB + EventBus}} | {{OrderService (saga)}} | {{outbox pattern for cross-store consistency}} |
| {{User auth}} | {{Middleware → AuthService → TokenRepo}} | {{AuthService}} | {{stateless JWT, no transaction needed}} |
| {{Payment retry}} | {{Cron → PaymentRetryService → PaymentProvider + EventBus}} | {{PaymentRetryService}} | {{idempotency keys on retries; 3 attempts max}} |
| {{...}} | ... | ... | ... |

### External systems

| System | Direction | Protocol | Error model | Notes |
|--------|-----------|----------|-------------|-------|
| {{Stripe API}} | {{out}} | {{HTTPS REST}} | {{retry on 5xx, fail on 4xx}} | {{idempotency keys on writes}} |
| {{Postgres}} | {{out}} | {{TCP}} | {{retry with jitter, circuit break}} | {{primary + read replicas}} |
| {{Kafka}} | {{in/out}} | {{TCP}} | {{at-least-once; consumers idempotent}} | {{...}} |
| {{Redis cache}} | {{out}} | {{TCP}} | {{cache miss → DB; TTL: 5 min}} | {{...}} |

### Dependency direction

| Direction | Status | Notes |
|---|---|---|
| Domain → Infrastructure | {{PASS / FAIL}} | {{PASS: domain has no infra imports. FAIL: domain/user.py:5 imports Mongo.}} |
| Domain → Application | {{PASS / FAIL}} | {{...}} |
| Application → Presentation | {{PASS / FAIL}} | {{...}} |
| Cross-cutting → Domain | {{PASS / FAIL}} | {{...}} |

## Fitness summary

For each area, state PASS / CONCERNS / FAIL with concrete evidence:

| Area | Status | Evidence |
|------|--------|----------|
| Pattern fitness and ownership | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "domain layer has no infra imports; controller orchestrates services cleanly"}} |
| Contracts and boundaries | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "service interfaces are explicit; repo interfaces are implicit (duck-typed in Python, no protocol)"}} |
| Dependency topology | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "no cycles; direction is presentation→application→domain→infra"}} |
| Physical structure and configuration | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "config via env vars; secrets via vault; no hardcoded credentials found"}} |
| Error model and failure handling | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "synchronous HTTP calls have no timeout; circuit breaker pattern missing"}} |
| Observability | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "structured logging present; metrics missing on critical paths"}} |
| Test strategy | {{PASS / CONCERNS / FAIL}} | {{concrete evidence: e.g., "unit tests for domain; integration tests for services; no contract tests for external APIs"}} |

## Findings

| Priority | Problem | Evidence and justification | Required resolution |
|----------|---------|-----------------------------|---------------------|
| {{P0/P1/P2/P3}} | {{Concrete architectural defect}} | {{boundary and evidence; material consequence at evidenced scale; migration context; why the current tradeoff is not acceptable}} | {{smallest safe outcome or boundary correction; migration and rollback constraints; verified [practice reference](URL) to official or primary engineering guidance; allow equivalent valid target shapes}} |
| {{P0}} | {{Synchronous HTTP call to external service with no timeout}} | {{services/order.py:42: `requests.post(inventory_url, json=payload)`}} | {{Add `timeout=10` to the call; wrap with `tenacity` retry (3 attempts, exponential backoff); add a circuit breaker (`purgatory` / `circuitbreaker` lib). 1 PR, 4 hours, reversible.}} |
| {{P1}} | {{Domain imports infrastructure}} | {{domain/user.py:5: `from infrastructure.mongo import MongoUserRepo`}} | {{Invert: define `UserRepo` protocol in domain; have MongoUserRepo implement it; inject at composition root. 2 PRs (extract protocol + invert), 1 day, reversible.}} |
| {{P1}} | {{No contract tests for external APIs}} | {{No `tests/contracts/` directory}} | {{Add contract tests using `pact` or `schemathesis`; verify external API matches the expected schema on every CI run. 1 sprint, 3-4 PRs.}} |
| {{P2}} | {{Monolith deployment couples release cadence}} | {{Single deployable unit; all teams must coordinate deploy}} | {{Extract the highest-churn module as a separate service. Multi-quarter migration; only if current pain is measurable (deploy coordination takes >2 hours/week).}} |
| ... | ... | ... | ... |

Use `None` when no candidate survives the evidence, materiality, fitness, and acceptable-alternative gates.

## Evolution order and residual risks

{{Order recommendations by prerequisite. Group into:}}

1. **Immediate correctness fixes** — {{P0 / blocking. Estimate: N PRs, N hours.}}
2. **Boundary repair** — {{bounded migrations. Estimate: N PRs, N days.}}
3. **Optional evolution** — {{nice-to-have. Estimate: N sprints.}}
4. **Accepted exceptions** — {{decisions documented elsewhere that we continue to live with. Note why.}}
5. **Blind spots** — {{what we couldn't verify and why. Recommend how to close the gap.}}

For each step: estimated PR count, time, reversibility, prerequisite chain.

## Drift from documented intent

| Artifact | Status | Notes |
|----------|--------|-------|
| {{system-design-baseline.md}} | current / proposed / accepted / superseded / stale / contradictory / UNKNOWN | {{one-line summary}} |
| {{current-state.md}} | ... | ... |
| {{prior-audit.md}} | ... | {{what's resolved / retained / new}} |
| {{target-design.md}} | ... | ... |
| {{api-contracts.yml}} | ... | {{matches implementation?}} |
| {{deployment-diagram.png}} | ... | {{matches actual deploy units?}} |

## Materiality assessment

For each finding, the materiality gate:

- Does this finding have a **concrete cost** (correctness, security, change amplification, deployment coupling, recurring maintenance pain)?
- Is the cost **measurable or observable** (not just "feels wrong")?
- Is the cost **larger than the cost of fixing**?
- Is there **no acceptable alternative** the current shape already satisfies?

If all four pass → material finding. If any fail → observation, not finding.

## Limitations

{{What couldn't be verified, why, what would resolve it. Common:

- "Static-only — read the code but didn't run the system; runtime behavior may differ from static analysis"
- "Didn't review the test suite depth — coverage claims are based on test file count, not actual coverage"
- "Didn't profile under load — performance claims are based on static analysis (N+1 patterns, missing indexes), not measurement"
- "Didn't reconcile docs vs code in detail — spot-checked only"
- "External systems' actual behavior (error rates, latency) not measured — assumed from documented SLAs"
- "Read N of M modules — {{N/M}}% coverage"
- "Team ownership and Conway's law analysis not performed — assumed from folder structure"
}}

## Recommended next step

{{The smallest safe change or follow-up action. Concrete, bounded, ordered by prerequisite. Examples:

1. **Immediate**: Fix P0 issues (timeouts, circuit breakers, missing auth checks). {{Estimate: N PRs, N hours.}}
2. **This quarter**: Address P1 architecture issues (invert imports, add contract tests). {{Estimate: N PRs, N days.}}
3. **Next quarter**: Address P2 evolution (extract high-churn module as separate service). {{Estimate: 1 quarter, conditional on measurable pain threshold.}}
4. **Backlog**: Address P3 observations. {{Estimate: continuous, low priority.}}
}}
