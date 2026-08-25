# Refactor Prioritization \u2014 What to Fix, in What Order

You have 20 findings. You can ship 3 in this sprint. Which 3? This playbook provides the framework to prioritize refactoring work based on impact, ease, and strategic value. Mastering prioritization is the difference between analysis that gets acted on and analysis that gets ignored.

---

## The Core Principle: Prioritization = Impact \u00d7 Ease \u00b7 Strategic Value

The priority of a refactoring task is determined by three factors:

1. **Impact**: How much value does this fix create? (Correctness, security, maintainability, performance)
2. **Ease**: How easy is it to implement safely? (Effort, risk, dependencies)
3. **Strategic Value**: How does this align with team goals? (Roadmap, team capabilities, business priorities)

**Priority Formula**:
```
Priority Score = Impact (1-10) \u00d7 Ease (1-10) \u00d7 Strategic Value (1-5)
```

**Score Interpretation**:
| Score Range | Priority | Action |
|-------------|----------|--------|
| 400-500 | P0/Critical | Do immediately |
| 200-399 | P1/High | Do this sprint |
| 100-199 | P2/Medium | Do next sprint |
| 50-99 | P3/Low | Backlog |
| <50 | P4/None | Skip |

---

## The Priority Matrix

Order by **impact \u00d7 ease \u00d7 strategic value**. Highest score first.

### Impact vs. Ease Matrix

```
                    EASE
                ┌─────────────┬─────────────┬─────────────┐
                │   High       │   Medium     │   Low        │
    ┌───────────┼─────────────┼─────────────┼─────────────┤
    │           │             │             │             │
    │ Critical  │   P0         │   P0         │   P1         │
I   │ (P0)     │   (Fix now) │   (Fix now) │   (Plan)    │
M   │           │             │             │             │
P   ├───────────┼─────────────┼─────────────┼─────────────┤
A   │           │             │             │             │
C   │ High      │   P1         │   P1         │   P2         │
T   │ (P1)     │   (This      │   (This      │   (Next      │
    │           │   sprint)    │   sprint)    │   sprint)    │
    ├───────────┼─────────────┼─────────────┼─────────────┤
    │           │             │             │             │
    │ Medium    │   P2         │   P2         │   P3         │
    │ (P2)     │   (This      │   (Next      │   (Backlog)  │
    │           │   sprint)    │   sprint)    │             │
    └───────────┴─────────────┴─────────────┴─────────────┘
                    EASE
                    High          Medium         Low
```

### Extended Priority Matrix (with Strategic Value)

| Priority | Impact | Ease | Strategic Value | Action | Example |
|----------|--------|------|------------------|--------|---------|
| P0 | Critical | Any | Any | **Fix immediately** | SQL injection, data loss, crash |
| P0 | Critical | High | High | **Fix immediately** | Security vulnerability with easy fix |
| P1 | High | High | High | **Tackle first** | Small, well-bounded extraction |
| P1 | High | High | Medium | **Tackle first** | High-impact easy win |
| P1 | High | Medium | High | **Tackle first** | High-impact with some effort |
| P2 | Medium | High | High | **Tackle** | Quick wins build momentum |
| P2 | Medium | High | Medium | **Tackle** | Medium-impact easy fix |
| P2 | High | Low | High | **Plan** | High-impact but complex |
| P3 | Medium | Medium | Medium | **Defer** | Only if recurring pain |
| P3 | Low | Any | Any | **Defer** | Only if recurring pain |
| P4 | Low | Low | Low | **Skip** | Not a finding |

---

## The 4 Decision Rules

### Rule 1: Correctness / Security Always First

**P0 correctness or security defects block everything else.** Don't bundle them with refactors; fix them first, ship, then propose refactors.

**Why**: A P0 defect is a live bug causing active harm. Refactoring around it:
- Creates regression risk (might make the bug worse)
- Delays the fix (refactoring takes time)
- Complicates root cause analysis (harder to trace in refactored code)

**Process for P0 Findings**:
1. **Isolate**: Create a minimal fix that only addresses the defect
2. **Test**: Add regression tests for the specific defect
3. **Ship**: Deploy the fix immediately
4. **Refactor**: Then, in a separate effort, refactor the code

**Examples of P0 Findings**:
- SQL injection vulnerabilities
- Authentication bypasses
- Data corruption bugs
- Memory leaks causing OOM
- Race conditions causing data loss
- Security vulnerabilities (CVSS >= 7.0)

**P0 Finding Template**:
```
**P0: [Defect Description]**

**Location**: [file:line]
**Impact**: [What happens if unaddressed]
**Evidence**: [Proof of the defect]
**Fix**: [Minimal fix to address the defect]
**Effort**: [Time estimate]
**Rollback**: [How to revert if the fix causes issues]
**Blocked**: [Anything preventing immediate fix]

**Action**: Fix immediately, ship, then refactor
```

**What NOT to Do**:
- \u274c Bundle P0 fixes with refactoring
- \u274c Delay P0 fixes for "the right time"
- \u274c Ignore P0 findings because they're "too hard"
- \u274c Fix P0 findings without tests

**Pro Tip**: If a P0 finding can't be fixed immediately (blocked on resources, access, etc.), escalate it. P0 findings that sit in the backlog are a sign of organizational dysfunction, not analysis quality.

---

### Rule 2: High-Impact Easy Work Next

**A high-impact finding that's easy (small, well-bounded, has tests) is the best ROI.** These are your "quick wins" - fixes that provide immediate value with low risk.

**Characteristics of High-Impact Easy Work**:
- **Small Scope**: < 100 LOC changed
- **Well-Bounded**: Single file or small set of related files
- **Reversible**: Can be rolled back in < 30 minutes
- **Tested**: Has existing tests or easy to add tests
- **Independent**: Doesn't depend on other changes
- **High Value**: Addresses a real pain point

**Examples of High-Impact Easy Work**:
| Finding | Impact | Ease | Why It's Easy |
|---------|--------|------|---------------|
| Extract duplicated function | High (DRY violation) | High | Single PR, copy-paste refactor |
| Add missing ownership check | High (security) | High | One if-statement |
| Invert one import direction | High (architecture) | High | Single line change |
| Add input validation | High (correctness) | High | Simple validation logic |
| Fix N+1 query | High (performance) | High | Add .select_related() |
| Remove dead code | Medium (maintainability) | High | Delete only |

**High-Impact Easy Work Template**:
```
**P1: [Finding Description]**

**Location**: [file:line]
**Impact**: [Why this matters]
**Evidence**: [Proof of the issue]
**Fix**: [What to change]
**Effort**: [Time estimate, usually < 2 hours]
**PRs**: [Number of PRs, usually 1]
**Tests**: [Testing strategy]
**Rollback**: [How to revert]
**Dependencies**: [Any prerequisites]

**Action**: Tackle this sprint
```

**Finding High-Impact Easy Work**:
1. Look for **duplication**: Same code in multiple places
2. Look for **simple violations**: Missing validation, wrong import direction
3. Look for **low-hanging fruit**: Issues that can be fixed with small changes
4. Look for **test gaps**: Missing tests that are easy to add
5. Look for **dead code**: Unused code that can be removed

**Pro Tip**: These findings build momentum. Each quick win:
- Improves the codebase
- Builds team confidence
- Creates psychological safety for bigger changes
- Provides immediate ROI on the audit

---

### Rule 3: Plan Big Migrations Separately

**A high-impact finding that's hard (multi-quarter, requires coordination) is not a refactor \u2014 it's an architecture migration.** Treat it differently from regular refactoring.

**Characteristics of Big Migrations**:
- **Multi-PR**: Requires 5+ PRs
- **Multi-Team**: Requires coordination with other teams
- **Multi-Week**: Takes 2+ weeks to complete
- **High Risk**: Significant regression risk
- **Complex**: Requires careful planning and sequencing

**Migration Planning Process**:
1. **Define the Goal**: What are you trying to achieve?
2. **Assess Current State**: What exists now?
3. **Design Target State**: What should exist at the end?
4. **Identify Migration Path**: How to get from current to target?
5. **Break into Steps**: Each step should be:
   - Bounded (one PR or a small set of related PRs)
   - Reversible (can roll back if something goes wrong)
   - Tested (has tests or can be tested)
   - Independent (doesn't depend on other steps, or dependencies are clear)
6. **Estimate Each Step**: Time, effort, risk
7. **Sequence Steps**: Order steps by dependencies
8. **Document the Plan**: Create a migration plan document

**Migration Plan Template**:
```markdown
# Migration Plan: [Migration Name]

**Goal**: [What you're trying to achieve]
**Owner**: [Who is responsible]
**Timeline**: [Expected duration]
**Priority**: [P1/P2/P3]

## Current State
[Description of current state with evidence]

## Target State
[Description of target state]

## Migration Steps

### Step 1: [Step Name]
- **Description**: [What this step does]
- **Scope**: [Files/modules affected]
- **Effort**: [Time estimate]
- **PRs**: [Number of PRs]
- **Tests**: [Testing strategy]
- **Rollback**: [How to revert]
- **Dependencies**: [Prerequisites]
- **Risk**: [Low/Medium/High]

### Step 2: [Step Name]
... (same structure)

## Rollback Plan
[Overall rollback strategy if migration fails]

## Success Criteria
[How you know the migration is complete and successful]

## Monitoring
[How to monitor the migration for issues]
```

**Examples of Big Migrations**:
| Migration | Impact | Ease | Why It's Hard |
|-----------|--------|------|---------------|
| Extract domain layer | High (architecture) | Low | Requires 20+ file changes, coordination |
| Migrate to new framework | High (modernization) | Low | Requires retraining, new infrastructure |
| Split monolith to microservices | High (scalability) | Low | Requires new deployment pipeline, monitoring |
| Replace ORM | High (performance) | Low | Requires rewriting all queries, testing |
| Refactor auth system | High (security) | Low | Requires coordination with all teams |

**What NOT to Do**:
- \u274c Include big migrations in the audit report as "refactor this"
- \u274c Expect big migrations to be done in one sprint
- \u274c Start big migrations without a plan
- \u274c Underestimate the effort of big migrations

**Pro Tip**: Big migrations should be:
- **Separate from audits**: The audit identifies the issue; the migration plan addresses it
- **Owned by architects**: Not just developers
- **Planned with the team**: Not imposed from above
- **Monitored closely**: With clear success criteria

---

### Rule 4: Skip Low-Impact Work

**Style preferences, pattern preferences, "would be nicer" \u2014 these don't go in the report at all.** If you can't articulate a concrete cost, the candidate isn't a finding.

**What is NOT a Finding**:
| Not a Finding | Why | What to Do Instead |
|---------------|-----|---------------------|
| Style preferences | Subjective | Add to linter config |
| Pattern preferences | Subjective | Document in style guide |
| "Would be nicer" | No concrete cost | Skip |
| "Modern best practice" | No current defect | Skip |
| "Should use X" | No current problem | Skip |
| "Not idiomatic" | No concrete cost | Add to style guide |

**The Materiality Test**:
For a potential finding, ask:
1. **What is the concrete cost of NOT fixing this?**
   - If answer is "nothing" or "minor inconvenience" \u2192 Not a finding
2. **What is the effort to fix this?**
   - If effort > benefit \u2192 Not a finding (yet)
3. **Is this causing active pain?**
   - If no \u2192 Not a finding (yet)

**When Low-Impact Work BECOMES a Finding**:
- It's causing **recurring pain** (e.g., merge conflicts in the same file)
- It's **blocking other work** (e.g., can't add feature because of tech debt)
- It's **creating risk** (e.g., dead code that might be used accidentally)
- It's **violating a team standard** (e.g., style that the team has agreed to enforce)

**Examples of What NOT to Include**:
- \u274c "This function should use a list comprehension instead of a for loop"
- \u274c "This module should be split into smaller files" (without concrete issues)
- \u274c "This code isn't idiomatic Python"
- \u274c "We should adopt the Repository pattern"
- \u274c "This should use TypeScript instead of JavaScript"

**Examples of What TO Include (When It Becomes a Finding)**:
- \u2705 "This function has 50 lines of duplicate code in 3 other files" (DRY violation with concrete cost)
- \u2705 "This module has 1500 LOC and causes merge conflicts weekly" (concrete pain)
- \u2705 "This code uses eval() which is a security risk" (concrete risk)
- \u2705 "This dead code references a deprecated API that will be removed" (future risk)

**Pro Tip**: When in doubt, ask: "Would the team thank me for this finding, or would they roll their eyes?" If the latter, it's probably not a finding (or not presented correctly).

---

## Impact Estimation

For each finding, estimate impact on a scale. Be specific and concrete.

### Impact Scale

| Impact Level | Score | Description | Examples |
|--------------|-------|-------------|----------|
| Critical (P0) | 10 | Blocks release; causes data loss, security hole, crash | SQLi, auth bypass, data corruption, memory leak causing OOM |
| High (P1) | 7-9 | Will cause recurring pain; one of: correctness bug, security issue, change amplification | Race condition, missing validation, tight coupling |
| Medium (P2) | 4-6 | Slows future work; one of: maintainability issue, dead code in active module, fragile tests | Duplicate code, long methods, no tests, style violations with team agreement |
| Low (P3) | 1-3 | Cosmetic; not worth doing now | Style preferences, minor inconsistencies |

**Impact Estimation Questions**:
1. **What happens if we don't fix this?**
   - Security breach? (P0)
   - Data loss/corruption? (P0)
   - System crash? (P0)
   - Incorrect behavior? (P1)
   - Performance degradation? (P1)
   - Development slowdown? (P2)
   - Minor annoyance? (P3)
   - Nothing? (Not a finding)

2. **How many people are affected?**
   - All users? (P0/P1)
   - Many users? (P1/P2)
   - Some users? (P2)
   - Few users? (P3)

3. **How often does it occur?**
   - Always? (P0/P1)
   - Frequently? (P1/P2)
   - Occasionally? (P2)
   - Rarely? (P3)

4. **What is the business impact?**
   - Revenue loss? (P0)
   - Compliance violation? (P0)
   - Reputation damage? (P1)
   - Productivity loss? (P2)
   - Minor inconvenience? (P3)

**Don't conflate "low impact" with "small change".** A 1-line fix can be high-impact (SQLi patch). A 100-line change can be low-impact (rename).

**Impact Estimation Examples**:

| Finding | Impact | Why |
|---------|--------|-----|
| SQL injection in user_search.py:23 | P0 (10) | Allows auth bypass, affects all users |
| Race condition in cache.py:45 | P1 (8) | Causes data corruption, affects many users |
| Missing input validation in api.py:10 | P1 (7) | Could allow invalid data, affects some users |
| Duplicate code in utils/dates.py and helpers/datetime.py | P2 (5) | Maintenance burden, affects developers |
| Long method in services/processor.py:100 | P2 (4) | Hard to maintain, affects developers |
| Style: mixed naming conventions | P3 (2) | Minor annoyance, affects developers |
| Unused import in legacy.py:5 | P3 (1) | Cosmetic, no real impact |

**Pro Tip**: Use the "So What?" test. After stating a finding, ask "So what? Why should anyone care?" If you can't answer with a concrete impact, the impact level is too low (or it's not a finding at all).

---

## Ease Estimation

Estimate how easy it is to implement the fix safely. Ease is about risk and effort, not just code size.

### Ease Scale

| Ease Level | Score | Description | Characteristics |
|------------|-------|-------------|----------------|
| High (Easy) | 9-10 | Bounded change, has tests, reversible in <30 min | Single PR, <100 LOC, clear scope, good tests |
| Medium | 5-8 | Multiple related changes, may need test additions | 1-3 PRs, 100-500 LOC, some complexity |
| Low (Hard) | 1-4 | Multi-PR migration, coordination with other teams | 5+ PRs, 500+ LOC, high risk, many dependencies |

**Ease is about how quickly you can ship the fix safely.** Not the same as code size.

**Ease Estimation Questions**:
1. **How many files need to change?**
   - 1 file? (High)
   - 2-5 files? (Medium)
   - 5+ files? (Low)

2. **How many lines of code need to change?**
   - < 100 LOC? (High)
   - 100-500 LOC? (Medium)
   - 500+ LOC? (Low)

3. **Are there existing tests?**
   - Yes, good coverage? (High)
   - Some tests? (Medium)
   - No tests? (Low)

4. **How easy is it to add tests?**
   - Easy (can write in <1 hour)? (High)
   - Medium (1-4 hours)? (Medium)
   - Hard (>4 hours or complex)? (Low)

5. **How reversible is the change?**
   - Can revert in <30 minutes? (High)
   - Can revert in <2 hours? (Medium)
   - Hard to revert? (Low)

6. **How many teams need to coordinate?**
   - 1 team? (High)
   - 2 teams? (Medium)
   - 3+ teams? (Low)

7. **What is the regression risk?**
   - Low (change is isolated)? (High)
   - Medium (change affects some areas)? (Medium)
   - High (change affects many areas)? (Low)

8. **Are there dependencies on other changes?**
   - No dependencies? (High)
   - Few dependencies? (Medium)
   - Many dependencies? (Low)

**Ease Estimation Examples**:

| Finding | Ease | Why |
|---------|------|-----|
| Add input validation at api.py:10 | High (10) | Single line, existing tests, easy to revert |
| Extract duplicated function | High (9) | Single PR, copy-paste refactor, low risk |
| Invert one import direction | High (9) | Single line change, clear impact |
| Add missing test for auth flow | Medium (7) | Need to write tests, but clear what to test |
| Split god class (850 LOC) | Low (3) | Many files affected, high risk, needs coordination |
| Migrate to new framework | Low (1) | Multi-quarter, all teams, high risk |

**Pro Tip**: When estimating ease, always consider the **worst-case scenario**. What could go wrong? How hard would it be to recover? The ease score should reflect the risk-adjusted effort.

---

## Strategic Value Estimation

Estimate how well this finding aligns with team goals and strategic priorities.

### Strategic Value Scale

| Strategic Value | Score | Description | Examples |
|-----------------|-------|-------------|----------|
| High | 5 | Aligns with current team goals, roadmap priorities | Migration to new platform, security improvements, scalability fixes |
| Medium | 3-4 | Somewhat aligned with team goals | Code quality improvements, maintainability fixes |
| Low | 1-2 | Minimal alignment with team goals | Style fixes, minor cleanups |

**Strategic Value Questions**:
1. **Does this align with the team's current goals?**
   - Yes, it's a top priority? (High)
   - Yes, it's on the roadmap? (Medium)
   - No? (Low)

2. **Does this enable future work?**
   - Yes, unblocks major feature? (High)
   - Yes, makes future work easier? (Medium)
   - No? (Low)

3. **Does this reduce technical debt that's blocking progress?**
   - Yes, major blocker? (High)
   - Yes, minor blocker? (Medium)
   - No? (Low)

4. **Does this improve a system that's critical to the business?**
   - Yes, core system? (High)
   - Yes, important system? (Medium)
   - No, peripheral system? (Low)

5. **Does the team have capacity for this?**
   - Yes, and it's a priority? (High)
   - Yes, but it's not urgent? (Medium)
   - No capacity? (Low)

**Strategic Value Examples**:

| Finding | Strategic Value | Why |
|---------|-----------------|-----|
| SQL injection in payment service | High (5) | Security is a top priority, affects core system |
| Extract domain layer for new microservice | High (5) | Enables migration to microservices (roadmap priority) |
| Fix performance issue in checkout flow | High (5) | Affects revenue (business-critical) |
| Add tests for auth flow | Medium (4) | Improves quality, but not urgent |
| Remove duplicate code | Medium (3) | Improves maintainability |
| Fix style violations | Low (2) | Minimal business value |

**Pro Tip**: Strategic value can change over time. A finding that was low strategic value last quarter might be high this quarter (or vice versa). Always consider the current context.

---

## Sequencing Rules

### Rule A: Fix Dependencies Before Dependents

**If finding F1's fix is prerequisite to F2's, do F1 first.**

**Why**: Dependencies must be in place before dependents can be fixed.

**Examples**:
- "Extract domain layer" (F1) \u2192 "Invert controller imports" (F2)
  - Do F1 first; F2 only makes sense once F1 is in place
- "Add characterization tests" (F1) \u2192 "Refactor complex function" (F2)
  - Do F1 first; need tests as safety net for F2
- "Upgrade Python version" (F1) \u2192 "Use new Python features" (F2)
  - Do F1 first; F2 requires F1

**Dependency Graph**:
```
F1 (prerequisite)
  \u2192 F2 (depends on F1)
    \u2192 F3 (depends on F2)
```

**Sequencing**: F1, then F2, then F3

**What NOT to Do**:
- \u274c Try to do F2 before F1
- \u274c Bundle F1 and F2 in the same PR (if F2 is large)
- \u274c Start F2 without confirming F1 is complete

**Pro Tip**: Document dependencies explicitly in the report:
```
**Dependencies**:
- Requires: F1 (Extract domain layer)
- Blocks: F3 (Add new feature)
```

---

### Rule B: Cheap Wins Before Expensive Migrations

**Even if impact is similar, do the easy version first.**

**Why**: 
- Quick wins provide immediate value
- Build momentum for bigger changes
- Reduce risk while bigger work is in progress
- Provide psychological safety

**Examples**:
- "Add input validation" (easy, blocks injection) before "Parameterize all queries" (medium)
- "Add auth check" (easy) before "Refactor auth middleware" (hard)
- "Extract duplicated function" (easy) before "Split god class" (hard)
- "Remove dead code" (easy) before "Refactor module structure" (hard)

**Sequencing**:
```
Easy wins first (high impact, high ease)
  \u2192 Medium effort (high impact, medium ease)
    \u2192 Big migrations (high impact, low ease)
```

**What NOT to Do**:
- \u274c Start with big migrations when there are easy wins available
- \u274c Ignore easy wins because they seem "too small"
- \u274c Bundle easy wins with big migrations

**Pro Tip**: Celebrate quick wins. They build credibility and momentum for bigger changes.

---

### Rule C: Don't Bundle Unrelated Changes

**Two findings in the same area can be in the same PR if they touch the same code. Two findings in different areas should be in different PRs.**

**Why Bundling is Bad**:
- **Larger PRs**: Slower review, harder to understand
- **Higher Regression Risk**: One bug rolls back both fixes
- **Harder Attribution**: Which change broke what?
- **Slower Feedback**: Harder to iterate on specific changes
- **Harder to Revert**: If one change causes issues, need to revert everything

**When to Bundle**:
- Changes are in the **same file**
- Changes are **tightly coupled** (one doesn't make sense without the other)
- Changes have the **same purpose**
- Changes have the **same risk profile**

**When NOT to Bundle**:
- Changes are in **different files/modules**
- Changes have **different purposes**
- Changes have **different risk profiles**
- Changes have **different owners**

**Bundling Examples**:

\u2705 **Good Bundling**:
- Fix SQLi and add input validation in the same function
- Extract duplicated code from the same file
- Add tests for the same module

\u274c **Bad Bundling**:
- Fix SQLi in auth module + refactor user module
- Add input validation + split god class
- Extract domain layer + migrate to new framework

**PR Sizing Guidelines**:
| PR Size | LOC Changed | Files Changed | Review Time | Risk |
|---------|-------------|---------------|-------------|------|
| Small | < 100 | 1-3 | < 1 hour | Low |
| Medium | 100-500 | 3-10 | 1-4 hours | Medium |
| Large | 500-1000 | 10-20 | 4-8 hours | High |
| XL | 1000+ | 20+ | 8+ hours | Very High |

**What NOT to Do**:
- \u274c Create PRs larger than 1000 LOC
- \u274c Bundle changes from different areas
- \u274c Bundle changes with different risk profiles

**Pro Tip**: Use the "Can I review this in 30 minutes?" test. If a PR takes longer than 30 minutes to review thoroughly, it's probably too big.

---

### Rule D: Test Before / After Each Step

**Every refactor step should have characterization tests first.**

**Characterization Test**: A test that captures the current behavior (even if it's buggy) so you can verify the refactor doesn't change behavior.

**Why Tests First**:
- **Safety Net**: Tests catch regressions
- **Confidence**: Tests give confidence to make changes
- **Documentation**: Tests document expected behavior
- **Feedback**: Tests provide fast feedback

**Testing Process**:
1. **Capture Current Behavior**: Write tests that capture what the code does now
2. **Refactor**: Make the changes
3. **Verify**: Run tests to ensure behavior hasn't changed
4. **Improve**: Add tests for edge cases, improve test quality

**Test Types for Refactoring**:
1. **Characterization Tests**: Capture current behavior
2. **Regression Tests**: Prevent old bugs from reappearing
3. **Unit Tests**: Test individual functions/classes
4. **Integration Tests**: Test interactions between components
5. **Contract Tests**: Test API contracts

**What NOT to Do**:
- \u274c Refactor without tests
- \u274c Refactor with only happy-path tests
- \u274c Refactor and hope for the best
- \u274c Delete tests during refactoring

**Pro Tip**: If a module has no tests, **adding tests is the first refactoring step**. Don't refactor untested code.

---

## The "anti-priority" list

Don't recommend in this order. These are not findings, or are very low priority:

| Anti-Priority | Why It's Bad | What to Do Instead |
|---------------|--------------|---------------------|
| 1. Modernize the framework | No concrete defect, high effort | Skip unless there's a specific need |
| 2. Refactor for "readability" | Subjective, hard to measure | Add to style guide, enforce with linter |
| 3. Adopt new pattern | No current problem, learning curve | Skip unless it solves a specific issue |
| 4. Rewrite the module | Too vague, high risk | Identify specific issues to fix |
| 5. Add tests for "coverage" | No behavior to verify | Add tests for specific risks or behaviors |
| 6. Clean up "technical debt" | Too vague | Identify specific debt items |
| 7. Improve "code quality" | Too vague | Identify specific quality issues |
| 8. Make it "more object-oriented" | Subjective | Skip unless there's a concrete benefit |
| 9. Use "best practices" | Too vague | Identify specific practices and their benefits |
| 10. Make it "more maintainable" | Too vague | Identify specific maintainability issues |

**Remember**: If you can't articulate a **concrete cost** of NOT doing something, it's not a priority.

---

## The "10% rule" for Refactors

**In a typical sprint, allocate capacity as follows:**
- 80% of capacity = feature work
- 10% = technical debt / refactor
- 10% = bug fixes

**What This Means for Prioritization**:
- If you have **20 findings** and the team has capacity for **3 fixes** this sprint:
  - Pick the **P0 correctness/security finding** (must)
  - Pick the **highest-impact easy finding** (best ROI)
  - Pick **one more easy finding** if budget allows (momentum)

- The remaining **17 findings** go in the backlog, ordered by the priority matrix
- Each sprint picks the **next batch** of findings

**Capacity Planning**:
| Team Size | Sprint Capacity | Refactor Capacity | Findings per Sprint |
|-----------|-----------------|-------------------|----------------------|
| 1 dev | 40 hours | 4 hours | 1-2 |
| 3 devs | 120 hours | 12 hours | 2-4 |
| 5 devs | 200 hours | 20 hours | 3-6 |
| 10 devs | 400 hours | 40 hours | 5-10 |

**Pro Tip**: Be realistic about capacity. Overloading the team with refactoring work leads to:
- Burnout
- Resistance to future audits
- Poor quality work
- Unfinished tasks

---

## The "tech debt ledger"

**Keep a running list of findings not yet addressed.** This is your tech debt ledger.

**Why a Ledger?**:
1. **Survives between audits**: Don't re-find the same thing
2. **Shows debt trend**: Is debt increasing or decreasing over time?
3. **Helps prioritize**: When "we have a free sprint", what should we do?
4. **Builds accountability**: Every audit adds new debt, every sprint removes some
5. **Communicates with stakeholders**: Shows the state of technical debt

**Ledger Template**:
```markdown
# Tech Debt Ledger

**Last Updated**: [Date]
**Total Debt**: [Number] findings
**Debt Value**: $[Estimated cost to fix all]

## P0 \u2014 Critical (Must Fix)
- [ ] SQL injection in user_search.py:23 (audit 2024-08-24) \u2014 **BLOCKED** on resources
- [ ] Memory leak in data_processor.py:101 (audit 2024-08-24)

## P1 \u2014 High (This Quarter)
- [ ] Domain layer imports from controllers (audit 2024-08-24)
- [ ] Missing tests on auth flow (audit 2024-08-24)
- [ ] Circular dependency between A and B (audit 2024-08-24)

## P2 \u2014 Medium (Next Quarter)
- [ ] N+1 queries in order service (audit 2024-08-24)
- [ ] God class: services/processor.py 850 LOC (audit 2024-08-24)
- [ ] Duplicate date formatting in utils/dates.py and helpers/datetime.py (audit 2024-08-24)

## P3 \u2014 Low (Backlog)
- [ ] Dead code: utils/legacy.py (audit 2024-08-24)
- [ ] Style: mixed naming conventions in models/ (audit 2024-08-24)
- [ ] Unused imports in various files (audit 2024-08-24)

## Resolved
- [x] SQLi in user_search.py:23 (fixed in PR #123, deployed 2024-08-25)
- [x] Domain layer imports from controllers (fixed in PR #124, deployed 2024-08-26)

## Metrics
| Metric | Value |
|--------|-------|
| Total Findings | 12 |
| P0 | 2 |
| P1 | 3 |
| P2 | 3 |
| P3 | 4 |
| Resolved | 2 |
| Debt Trend | \u2192 (decreasing) |
```

**Ledger Management**:
1. **Add new findings** from each audit
2. **Update status** (P0/P1/P2/P3) as priorities change
3. **Mark as resolved** when fixed
4. **Review quarterly** with the team
5. **Prioritize** based on current context

**Ledger Best Practices**:
- **Be specific**: Each entry should be a specific, actionable finding
- **Include metadata**: Date, audit, priority, status
- **Link to issues**: Reference Jira/GitHub issues where applicable
- **Track effort**: Estimate and actual effort for each finding
- **Celebrate wins**: When debt is resolved, celebrate it

**Pro Tip**: The ledger is a **living document**. It should be updated after every audit and every sprint. Out-of-date ledgers lose their value.

---

## The "second-order effects" rule

**A refactor finding may have second-order effects** - benefits or costs that go beyond the immediate change.

**Second-Order Effects to Consider**:

**Positive Effects**:
- **Enables Future Work**: Does this unblock other work?
- **Improves Maintainability**: Does this make the code easier to maintain?
- **Reduces Risk**: Does this reduce the risk of future bugs?
- **Improves Performance**: Does this improve performance?
- **Enhances Security**: Does this improve security?
- **Builds Team Skills**: Does this help the team learn new skills?

**Negative Effects**:
- **Breaking Changes**: Does this break existing functionality?
- **Test Maintenance**: Does this require updating many tests?
- **Documentation Updates**: Does this require updating documentation?
- **Team Retraining**: Does this require retraining the team?
- **Temporary Slowdown**: Does this slow down development temporarily?
- **Merge Conflicts**: Does this cause merge conflicts?

**Estimating Second-Order Effects**:
For each finding, estimate:
1. **Direct Benefit**: The immediate value of the fix
2. **Second-Order Benefits**: Additional value from side effects
3. **Direct Cost**: The immediate cost of the fix
4. **Second-Order Costs**: Additional costs from side effects

**Net Value** = (Direct Benefit + Second-Order Benefits) - (Direct Cost + Second-Order Costs)

**Examples**:

| Finding | Direct Benefit | Second-Order Benefits | Direct Cost | Second-Order Costs | Net Value |
|---------|----------------|-----------------------|-------------|-------------------|-----------|
| Extract domain layer | High | Enables microservices, improves testability | Medium | Test updates, team learning | High |
| Add input validation | High | Prevents bugs, improves security | Low | None | High |
| Split god class | Medium | Improves maintainability | High | Many test updates | Medium |
| Remove dead code | Low | Reduces confusion | Low | None | Low |

**Documenting Second-Order Effects**:
```
**Finding**: Extract domain layer

**Direct Benefit**: Improves architecture, clearer separation of concerns

**Second-Order Benefits**:
- Enables migration to microservices (roadmap priority)
- Makes domain logic easier to test
- Reduces coupling between layers
- Makes code easier to understand

**Direct Cost**: 3 PRs, 2 days of work

**Second-Order Costs**:
- Need to update ~20 tests that import domain directly
- Team needs to learn new patterns
- Temporary slowdown during transition

**Net Value**: High \u2014 the benefits outweigh the costs
```

**Pro Tip**: Second-order effects can **change the priority** of a finding. A finding with modest direct benefit but high second-order benefits might be prioritized over a finding with high direct benefit but high second-order costs.

---

## The "smaller is better" rule

**When in doubt, split smaller.** Two small PRs ship faster than one big one.

**Why Smaller is Better**:
1. **Faster Reviews**: Smaller PRs are faster to review
2. **Lower Regression Risk**: Less code changed = less chance of bugs
3. **Easier Rollback**: If something breaks, easier to revert
4. **Faster Feedback**: Get feedback sooner, iterate faster
5. **Easier to Understand**: Smaller changes are easier to understand
6. **Better Attribution**: Easier to see which change caused what

**The Exception**: Tightly coupled changes that don't make sense individually should be bundled.

**Splitting Strategies**:
1. **By File**: Each file gets its own PR
2. **By Function**: Each function gets its own PR
3. **By Module**: Each module gets its own PR
4. **By Layer**: Each layer gets its own PR
5. **By Feature**: Each feature gets its own PR

**When to Bundle**:
- Changes are **tightly coupled** (one doesn't work without the other)
- Changes have the **same purpose**
- Changes have the **same risk profile**
- Changes are in the **same area**

**Splitting Example**:

**Bad (Bundled)**:
```
PR: "Refactor user module"
- Extract domain layer
- Invert dependencies
- Add input validation
- Update tests
- Fix style issues
```

**Good (Split)**:
```
PR 1: "Extract user domain layer"
- Extract user domain models
- Move user business logic

PR 2: "Invert user module dependencies"
- Invert import directions
- Update consumers

PR 3: "Add input validation to user API"
- Add validation logic
- Add tests

PR 4: "Update user module tests"
- Update existing tests
- Add new tests

PR 5: "Fix style issues in user module"
- Fix linter warnings
- Format code
```

**Pro Tip**: Use the "Can I describe this PR in one sentence?" test. If you can't describe a PR in one clear sentence, it's probably too big or doing too many things.

---

## The "respect the team's bandwidth" rule

**Don't recommend a 6-month refactor when the team has 1 week of capacity.** Match recommendations to bandwidth.

**Why This Matters**:
- **Realistic recommendations get shipped**
- **Unrealistic recommendations get ignored**
- **Respecting bandwidth builds trust**
- **Ignoring bandwidth destroys credibility**

**Bandwidth Assessment**:
1. **Team Size**: How many developers?
2. **Sprint Length**: How long is the sprint?
3. **Current Load**: What else is the team working on?
4. **Deadlines**: Are there upcoming deadlines?
5. **Other Priorities**: What other priorities does the team have?

**Capacity Estimation**:
| Team Size | Sprint Length | Total Capacity | Refactor Capacity |
|-----------|---------------|----------------|-------------------|
| 2 devs | 2 weeks | 160 hours | 16 hours |
| 5 devs | 2 weeks | 400 hours | 40 hours |
| 10 devs | 2 weeks | 800 hours | 80 hours |
| 2 devs | 1 week | 80 hours | 8 hours |
| 5 devs | 1 week | 200 hours | 20 hours |

**Recommendation Sizing**:
| Refactor Capacity | Recommendation Size |
|-------------------|---------------------|
| 8 hours | 1-2 small findings |
| 16 hours | 2-4 small findings |
| 20 hours | 3-5 small findings |
| 40 hours | 1 medium + 2-3 small findings |
| 80 hours | 2 medium + 3-4 small findings |

**What NOT to Do**:
- \u274c Recommend more work than the team can handle
- \u274c Ignore the team's current priorities
- \u274c Assume the team has infinite capacity
- \u274c Recommend work that doesn't align with team goals

**Pro Tip**: Always ask: "Does the team have capacity for this?" If the answer is no, either:
1. **Reduce the scope** of the recommendation
2. **Defer the recommendation** to a later time
3. **Find a smaller version** of the recommendation

---

## Output

The refactor section of the audit report should use this template:

```markdown
## Refactor Recommendations

**Analyst**: [Your Name]
**Date**: [YYYY-MM-DD]
**Team Capacity**: [Estimated hours for refactoring this sprint]

### Priority Summary

| Priority | Count | Estimated Effort | Notes |
|----------|-------|------------------|-------|
| P0 | 2 | 4 hours | Must fix before release |
| P1 | 5 | 12 hours | This sprint |
| P2 | 8 | 20 hours | Next sprint |
| P3 | 15 | 10 hours | Backlog |

### P0 (Must Fix Before Release)

**Criteria**: Correctness or security issues that block release

| # | Finding | Location | Impact | Ease | Effort | PRs | Tests | Rollback | Dependencies | Owner |
|---|---------|----------|--------|------|--------|-----|-------|----------|--------------|-------|
| 1 | SQLi in user_search.py:23 | user_search.py:23 | Critical | High | 30 min | 1 | Existing | Revert PR | None | Backend |
| 2 | Memory leak in data_processor.py | data_processor.py:101 | Critical | Medium | 2 hours | 1 | Add | Revert PR | None | Backend |

**Action**: Fix immediately, ship, then refactor

### P1 (This Sprint)

**Criteria**: High-impact, high-ease findings that provide immediate value

| # | Finding | Location | Impact | Ease | Effort | PRs | Tests | Rollback | Dependencies | Owner |
|---|---------|----------|--------|------|--------|-----|-------|----------|--------------|-------|
| 1 | Domain imports from controllers | domain/user.py:1, controllers/auth.py:5 | High | High | 1 hour | 2 | Existing | Revert PRs | None | Backend |
| 2 | Missing tests on auth flow | auth/service.py | High | Medium | 2 hours | 1 | Add | Revert PR | None | Backend |
| 3 | Extract duplicated date formatting | utils/dates.py, helpers/datetime.py | Medium | High | 30 min | 1 | Existing | Revert PR | None | Backend |

**Action**: Tackle this sprint

### P2 (Next Sprint)

**Criteria**: Medium-impact findings or high-impact findings that require more effort

| # | Finding | Location | Impact | Ease | Effort | PRs | Tests | Rollback | Dependencies | Owner |
|---|---------|----------|--------|------|--------|-----|-------|----------|--------------|-------|
| 1 | N+1 queries in order service | services/order.py:45 | Medium | Medium | 4 hours | 1 | Add | Revert PR | None | Backend |
| 2 | God class: services/processor.py (850 LOC) | services/processor.py | Medium | Low | 2 days | 4 | Add | Complex | F1 | Backend |
| 3 | Circular dependency A->B->C->A | services/a.py, services/b.py, services/c.py | High | Low | 1 day | 3 | Existing | Revert PRs | None | Backend |

**Action**: Plan for next sprint

### P3 (Backlog)

**Criteria**: Low-impact findings or findings with low ease

| # | Finding | Location | Impact | Ease | Effort | Notes |
|---|---------|----------|--------|------|--------|-------|
| 1 | Dead code: utils/legacy.py | utils/legacy.py | Low | High | 30 min | Remove after monitoring |
| 2 | Style: mixed naming in models/ | models/* | Low | High | 2 hours | Add to linter |
| 3 | Unused imports in various files | Multiple files | Low | High | 1 hour | Cleanup |

**Action**: Defer to backlog, address when capacity allows

---

## Sequencing Plan

### Immediate (This Week)
1. **Fix P0 SQLi** (30 min)
   - Owner: Alice
   - PR: #123
   - Deadline: EOD Tuesday

2. **Fix P0 memory leak** (2 hours)
   - Owner: Bob
   - PR: #124
   - Deadline: EOD Wednesday

### This Sprint (Week 1-2)
1. **Invert domain/controller dependencies** (1 hour)
   - Owner: Alice
   - PRs: #125, #126
   - Deadline: EOD Friday Week 1

2. **Add tests for auth flow** (2 hours)
   - Owner: Charlie
   - PR: #127
   - Deadline: EOD Wednesday Week 2

3. **Extract duplicated date formatting** (30 min)
   - Owner: Alice
   - PR: #128
   - Deadline: EOD Friday Week 1

### Next Sprint (Week 3-4)
1. **Fix N+1 queries** (4 hours)
   - Owner: Bob
   - PR: #129
   - Deadline: EOD Friday Week 3

2. **Split processor.py god class** (2 days)
   - Owner: Team
   - PRs: #130, #131, #132, #133
   - Deadline: EOD Friday Week 4
   - Dependencies: Need to update tests first

### Migration Plans

#### Migration: Extract Domain Layer
- **Goal**: Separate domain logic from application logic
- **Owner**: Alice
- **Timeline**: 2 sprints
- **Steps**:
  1. Extract domain models (PR #134, 1 day)
  2. Extract domain services (PR #135, 1 day)
  3. Invert dependencies (PR #136, 1 day)
  4. Update tests (PR #137, 1 day)
- **Rollback**: Revert all PRs

---

## Tech Debt Ledger Update

**Added This Audit**:
- [ ] SQLi in user_search.py:23 (P0)
- [ ] Memory leak in data_processor.py:101 (P0)
- [ ] Domain imports from controllers (P1)
- [ ] Missing tests on auth flow (P1)
- [ ] Extract duplicated date formatting (P1)
- [ ] N+1 queries in order service (P2)
- [ ] God class: services/processor.py (P2)
- [ ] Circular dependency A->B->C->A (P2)
- [ ] Dead code: utils/legacy.py (P3)
- [ ] Style: mixed naming in models/ (P3)
- [ ] Unused imports in various files (P3)

**Resolved This Sprint**:
- [x] SQLi in user_search.py:23 (fixed in PR #123)
- [x] Memory leak in data_processor.py:101 (fixed in PR #124)

**Metrics**:
- Total debt: 11 findings
- P0: 0 (all resolved)
- P1: 3
- P2: 3
- P3: 5
- Trend: \u2192 (decreasing)
```

Each entry: specific finding, impact level, ease level, PR count estimate, owner, dependencies.

**Quality > quantity. Always.**

The best refactor recommendations are:
1. **Specific**: Clear what to do
2. **Prioritized**: Ordered by importance
3. **Realistic**: Matches team capacity
4. **Actionable**: Clear next steps
5. **Bounded**: Each recommendation is scoped and reversible

**Remember**: A good refactor recommendation is one that the team will actually do. A perfect recommendation that gets ignored is worthless.
