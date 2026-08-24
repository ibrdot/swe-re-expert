# SWE Thinking — How a Senior Engineer Reads a Codebase

## The mindset

A senior engineer doesn't read code top-to-bottom. They read with a **purpose**: answering a specific question, finding a specific bug, or making a specific change. The codebase is a map, not a novel — you don't read every street, you read the streets between where you are and where you're going.

## The hierarchy of questions

In order, ask:

1. **What is this?** (project type, language, framework, build system)
2. **How is it organized?** (folder structure, layers, entry points)
3. **What does it claim to do?** (README, docs, architecture diagrams)
4. **What does it actually do?** (entry points → critical flows → behavior)
5. **Where's the drift?** (docs vs reality, intended vs actual)
6. **Where's the pain?** (hot files, repeated change sets, fragile tests)
7. **What's worth fixing?** (material defects with concrete cost)

## Reading order — the 4-pass pattern

### Pass 1: Inventory (5-10 minutes)

- Read the README, package.json / pyproject.toml / Cargo.toml / go.mod
- `git log --oneline -20` (recent activity tells you what's actively changing)
- `git log --since=30.days.ago --numstat | sort -k3 -nr | head -20` (most-changed files = hot spots)
- Run `scripts/swe_audit.py --root . --triage` for a quick map

Don't read any source code yet. Just orient.

### Pass 2: Critical path (10-30 minutes)

Pick ONE critical flow (the main user action, the highest-traffic endpoint, the most-changed module). Read it end to end:

- Entry point (route / handler / main)
- Orchestration (service / usecase)
- Domain behavior (entity methods)
- Persistence / external calls
- Return path

For each step, ask: **what would break this?** Race conditions, partial failures, missing input validation, error swallowing, slow queries. Note them but don't fix yet.

### Pass 3: Pain points (10-30 minutes)

Look at the most-changed files from Pass 1. Read them. Ask:

- **Why is this file changed so often?** (volatility — is the abstraction wrong?)
- **What's the bug-prone pattern?** (stringly-typed flags, repeated copy-paste, missing error handling)
- **Where's the dead code?** (functions with no callers, conditionals that never fire)
- **What's the test signal?** (do tests cover the critical path or just the happy case?)

### Pass 4: Findings filter (5-10 minutes)

You should now have ~10-20 candidate findings. Filter ruthlessly:

- Does this predict a concrete cost? (correctness, security, change amplification, maintenance pain)
- Is there an acceptable alternative the current code already satisfies? (then it's not a finding)
- Is the evidence specific (line numbers, offsets, call sites)? (or is it "looks fragile"?)
- Is the fix bounded? (one PR? one sprint? a multi-quarter migration?)

Only findings that pass all four gates make the report. The rest are observations.

## The "follow the data" trick

When the code is hard to follow, follow the data instead. Pick a piece of data (a user input, a request, a row from the DB) and trace it:

- Where does it enter? (route handler, stdin, file read)
- What transformation happens at each step? (parse → validate → enrich → store)
- Where does it cross a boundary? (controller → service → repo → DB)
- Where could it be lost, corrupted, or leaked?

Data flow is often clearer than control flow, especially in async / event-driven code.

## The "what would break this" question

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

The bugs you find by asking this question are the bugs that matter. The bugs you find by pattern-matching ("this looks like a Singleton, that's bad") are usually not real bugs.

## The "fitness over fashion" rule

Don't recommend changes because the current code doesn't match a pattern you like. The current code is one of several reasonable shapes. Ask:

- Does it have a present defect? (a bug, a security hole, a perf problem)
- Is there measurable simplification? (fewer lines, fewer concepts, fewer moving parts)
- Does the change remove real volatility, or just pattern-displeasure?

If yes to any — recommend. If no — note as observation, not finding.

Modernization for novelty's sake is technical debt with extra steps.

## The "smallest safe next step" output

For every finding, recommend the smallest change that resolves it:

- One function extraction? → one PR
- One pattern removal? → bounded change with tests
- Layer inversion? → multi-PR migration sequence
- Framework migration? → only if there's a present defect the migration fixes

Multi-step migrations are valid but should be ordered by prerequisite, with rollback paths. "Rewrite the whole thing" is almost never the right recommendation.

## The "evidence over assertion" output

In the report, every finding must cite:

- File path + line number
- The actual code (quoted)
- The concrete consequence (a bug class, a coupling cost, a maintenance burden)
- The fix (specific, bounded)

"This looks fragile" is not a finding. "At line 47, `memcpy(dst, src, strlen(src)+1)` overflows the 16-byte stack buffer `dst` when `src` exceeds 15 bytes; bound it with `strnlen(src, sizeof(dst)-1)`" is a finding.

## The "what I don't know" honesty

End every audit with a Limitations section. List what you didn't read, what you couldn't verify, what tool you wish you had. This is the most underrated part of the report — it tells the reader how much to trust the rest.

Static-only reviews should say "I didn't run the tests, didn't profile, didn't verify runtime behavior". Architecture reviews should say "I read the executable behavior; the design docs may say different and I didn't reconcile". Honesty compounds trust over time.

## Final mental hook

> "I have N files. I want to answer question Q. What's the cheapest read that answers Q?"

If you can answer that question repeatedly, you're doing SWE review. If you can't, you're reading code — and reading code is not review.
