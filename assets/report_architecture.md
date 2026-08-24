# Architecture Audit Report — {{TARGET_NAME}}

**Verdict:** PASS | CONCERNS | FAIL | BLOCKED
**Audited by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Audit scope:** {{full system / specific subsystem}}

---

## Executive summary

{{3-5 sentences. State the verdict in plain English. Describe the actual architecture (not the documented one). Call out the most material drift between docs and behavior. Identify the highest-cost structural risk if any.}}

## Actual architecture map

{{Describe what the system actually executes, not what the docs say. Include:}}

### Modules, packages, layers

| Layer | Modules | Owner | Deploy unit | Notes |
|-------|---------|-------|-------------|-------|
| {{Presentation}} | {{controllers, routes, views}} | {{team}} | {{service / monolith}} | {{...}} |
| {{Application}} | {{usecases, services}} | {{team}} | {{...}} | {{...}} |
| {{Domain}} | {{entities, value objects}} | {{team}} | {{...}} | {{...}} |
| {{Infrastructure}} | {{repos, clients, drivers}} | {{team}} | {{...}} | {{...}} |

### Critical flows

| Flow | Entry → Exit | Atomicity owner | Notes |
|------|--------------|-------------------|-------|
| {{Order placement}} | {{API → OrderService → OrderRepo → DB + EventBus}} | {{OrderService (saga)}} | {{outbox pattern for cross-store consistency}} |
| {{User auth}} | {{Middleware → AuthService → TokenRepo}} | {{AuthService}} | {{stateless JWT, no transaction needed}} |
| {{...}} | ... | ... | ... |

### External systems

| System | Direction | Protocol | Error model | Notes |
|--------|-----------|----------|-------------|-------|
| {{Stripe API}} | {{out}} | {{HTTPS REST}} | {{retry on 5xx, fail on 4xx}} | {{idempotency keys on writes}} |
| {{Postgres}} | {{out}} | {{TCP}} | {{retry with jitter, circuit break}} | {{primary + read replicas}} |
| {{Kafka}} | {{in/out}} | {{TCP}} | {{at-least-once; consumers idempotent}} | {{...}} |

## Fitness summary

| Area | Status | Evidence |
|------|--------|----------|
| Pattern fitness and ownership | {{PASS / CONCERNS / FAIL}} | {{concrete evidence}} |
| Contracts and boundaries | {{PASS / CONCERNS / FAIL}} | {{concrete evidence}} |
| Dependency topology | {{PASS / CONCERNS / FAIL}} | {{concrete evidence}} |
| Physical structure and configuration | {{PASS / CONCERNS / FAIL}} | {{concrete evidence}} |

## Findings

| Priority | Problem | Evidence and justification | Required resolution |
|----------|---------|-----------------------------|---------------------|
| {{P0/P1/P2/P3}} | {{Concrete architectural defect}} | {{boundary and evidence; material consequence at evidenced scale; migration context; why the current tradeoff is not acceptable}} | {{smallest safe outcome or boundary correction; migration and rollback constraints; verified [practice reference](URL) to official or primary engineering guidance; allow equivalent valid target shapes}} |
| ... | ... | ... | ... |

Use `None` when no candidate survives the evidence, materiality, fitness, and acceptable-alternative gates.

## Evolution order and residual risks

{{Order recommendations by prerequisite. Group into:}}

1. **Immediate correctness fixes** — {{P0 / blocking}}
2. **Boundary repair** — {{bounded migrations}}
3. **Optional evolution** — {{nice-to-have}}
4. **Accepted exceptions** — {{decisions documented elsewhere that we continue to live with}}
5. **Blind spots** — {{what we couldn't verify and why}}

## Drift from documented intent

| Artifact | Status | Notes |
|----------|--------|-------|
| {{system-design-baseline.md}} | current / proposed / accepted / superseded / stale / contradictory / UNKNOWN | {{one-line summary}} |
| {{current-state.md}} | ... | ... |
| {{prior-audit.md}} | ... | {{what's resolved / retained / new}} |
| {{target-design.md}} | ... | ... |

## Limitations

{{What couldn't be verified, why, what would resolve it.}}

## Recommended next step

{{The smallest safe change or follow-up action. Concrete, bounded, ordered by prerequisite.}}
