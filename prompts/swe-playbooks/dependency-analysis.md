# Dependency Analysis — Reading the Dependency Graph

The dependency graph is the skeleton of the architecture. Reading it correctly tells you what the code actually is, not what the docs say.

## The 3 things to look for

1. **Direction** — does data flow / dependencies go in the intended direction?
2. **Coupling** — how tightly are modules connected? (High coupling = change amplification)
3. **Cycles** — circular dependencies that cause build / deploy / failure coupling

## Reading the dependency graph

### Step 1: Inventory the modules

```bash
# Python
find . -name "*.py" | head -50          # List files
grep -r "^from\|^import" --include="*.py" | wc -l  # Count imports

# Go
go list ./...                            # List packages

# Rust
ls src/                                  # Or use cargo modules

# C/C++
find . -name "CMakeLists.txt" -o -name "Makefile"  # Build files reveal module structure
```

### Step 2: Build the import graph

For each module, list what it imports:

```bash
# Python
python3 -c "
import ast, os, sys
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        print(f'{path}\t{alias.name}')
                elif isinstance(node, ast.ImportFrom):
                    print(f'{path}\t{node.module}')
"

# Or use scripts/swe_audit.py --deps
```

### Step 3: Identify layer violations

The classic layered architecture:

```
Presentation  →  Application  →  Domain  ←  Infrastructure
```

Presentation depends on Application. Application depends on Domain. Infrastructure depends on Domain (inverts via interfaces). Domain depends on nothing (in the ideal).

Real violations:
- Domain imports from Presentation (`domain/user.py` imports `controllers/auth.py`)
- Domain imports from Application (`domain/user.py` imports `services/email.py`)
- Infrastructure imports from Presentation (`infrastructure/db.py` imports `controllers/auth.py`)

These create cycles and force-coupling. When presentation changes, domain must too — which is wrong direction.

Detection: for each import in a domain file, check the target's layer. Same or lower layer = OK. Higher layer = violation.

### Step 4: Find cycles

A cycle is when module A imports B, B imports C, C imports A. Causes:
- Build coupling (can't build A without B, B without C, C without A)
- Test coupling (can't test A in isolation)
- Deploy coupling (must deploy A, B, C together)
- Failure propagation (bug in A affects C via B)

Detection:
```bash
# Use madge (JS), pydeps (Python), dep (Go), or dot (Rust)
madge --circular ./src/                # JavaScript
pydeps --max-bacon=2 ./                # Python
go mod graph | cycle_detector          # Go (custom)
```

Or build the graph manually and look for back-edges.

## The "fan-in / fan-out" heuristic

- **Fan-in** (how many modules import this one): high is fine for utilities, low for unique modules
- **Fan-out** (how many modules does this one import): > 7 is suspicious (module is doing too much)

| Pattern | Meaning |
|---------|---------|
| High fan-in, low fan-out | Utility / library module — good |
| Low fan-in, low fan-out | Leaf module — usually fine |
| High fan-in, high fan-out | "Hub" module — coupling magnet, often refactoring target |
| Low fan-in, high fan-out | "Black hole" — depends on everything, depended on by little. Often the wrong abstraction. |

## The "build order" check

Topologically sort the dependency graph. The build order is:
1. Leaf modules (no deps)
2. Modules that depend only on leaves
3. Modules that depend on (1) and (2)
4. ...
5. Entry point (depends on everything)

If the sort fails (cycle exists), that's a finding.

## The "deployable unit" check

Which modules must deploy together? Two modules are coupled if:
- They share a build artifact (e.g., same JAR, same Python package, same Docker image)
- They share a runtime (same process)
- They share a database (changes to schema require coordinated deploy)
- They share a contract (API version; breaking changes need coordination)

This is the real architecture, not the file-folder structure. Two services in separate folders that share a DB are coupled; two services in different repos that share nothing are decoupled.

## The "ownership boundary" check

Who owns each module? If module A is owned by team X and module B by team Y:
- If A imports B, team X depends on team Y's release cadence
- If both own each other's code → no clear ownership → architectural drift
- If ownership is unclear → "no one's" code, often technical debt zone

Detection: cross-reference with the team's known org structure. (Often not in the codebase — check the README or the company wiki.)

## The "API contract" check

For each cross-module API:
- Is the contract stable? (breaking changes vs additive changes)
- Is the contract documented? (OpenAPI, gRPC proto, etc.)
- Is the contract tested? (consumer-driven contract tests)
- Is there versioning? (v1, v2 endpoints; major version on package)

A module that exposes a contract to other teams needs more discipline than one used internally. Findings here usually show up as "this internal API changed in a breaking way and broke consumers" — recurring pain.

## The "hidden dependency" check

Not all dependencies are imports:

- **Reflection / runtime loading** — `importlib.import_module(user_string)`, `plugin.load()` — invisible to static analysis
- **Configuration** — environment variables, config files that say which module to load
- **Database / queue contracts** — two modules sharing a DB table or queue are coupled even without imports
- **Network calls** — service A calls service B's HTTP API; they're coupled
- **Event names** — service A publishes event "UserCreated"; service B consumes it; renaming the event breaks B

These are harder to detect. Look for:
- `importlib` / `__import__` calls
- Config files with module paths
- Shared DB table names in migrations
- HTTP client instantiations with hardcoded URLs
- Event names in publisher + consumer code

## The "dead dependency" check

Sometimes modules import things they don't actually use:

```python
# old code, removed but import left behind
from deprecated_module import some_function  # not called anywhere in this file
```

Detection: lint with `ruff --select F401` (unused imports), or `vulture` (Python), or language-specific dead-import linters.

These are usually P3 (cleanup), not P0. But they accumulate.

## The "duplicate dependency" check

When two modules do the same thing:

- `utils/dates.py` and `helpers/datetime.py` both have date formatting
- `services/email.py` and `clients/mailer.py` both send email

Detection: cluster functions by behavior, not by name. Two date-formatting functions in different files = duplicate.

Findings: usually P2 (consolidation would reduce maintenance). Recommend the merge only if the duplication is causing drift (the two copies have different bugs).

## The "transitive dependency" check

Module A imports B; B imports C. If C breaks, A might break.

For npm/pip/cargo: use the lock file to see the full transitive graph.

Detection: for each direct dep, look at its transitive deps. Big-name transitive deps are usually fine; obscure transitive deps with few maintainers are risk (supply chain).

For supply chain concerns:
- Use `npm audit` / `pip-audit` / `cargo audit` for known CVEs
- Use `socket.dev` or similar for malicious package detection
- Pin deps with lockfiles
- Review new transitive deps when they appear in PRs

## The "version drift" check

Two modules depending on different versions of the same package:
- `moduleA` requires `requests==2.28`
- `moduleB` requires `requests==2.31`

In Python (pip): usually can't have both; one wins. In npm: can have nested versions (each package has its own node_modules). In Rust: cargo unifies to one version per major.

Detection: `pip freeze | sort` and look for duplicates. Or use `pipdeptree`.

Findings: version drift causes subtle bugs (different behavior between versions). Usually P2.

## Output

For dependency findings:

| Priority | Issue | Evidence | Recommendation |
|----------|-------|----------|----------------|
| P1 | Cycle: domain ↔ controllers | domain/user.py:1 imports controllers/auth.py; controllers/auth.py:5 imports domain/user | Invert the import; controllers depend on domain |
| P1 | Hub module: services/common.py imports 14 modules | services/common.py imports list... | Split into smaller focused modules |
| P2 | Duplicate date formatter | utils/dates.py:23 and helpers/datetime.py:8 both have format_iso() | Consolidate into utils/dates.py |
| P3 | Unused import | utils/legacy.py:5 imports removed_function | Remove |

Each finding: specific issue, evidence (file:line), recommendation (bounded, reversible).
