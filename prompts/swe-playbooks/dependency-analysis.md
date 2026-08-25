# Dependency Analysis \u2014 Reading the Dependency Graph

The dependency graph is the skeleton of the architecture. Reading it correctly tells you what the code actually is, not what the docs say. Mastering dependency analysis allows you to understand system architecture, identify coupling issues, predict change impact, and plan refactoring with precision.

---

## The Core Principle: Dependencies = Architecture

In software systems, the dependency graph IS the architecture. Not the diagrams, not the documentation, not the intended design - the actual imports, calls, and data flows that exist in the code. Understanding this graph is the foundation of all architectural analysis.

**Why Dependency Analysis Matters**:
1. **Reveals True Architecture**: Shows what the system actually is, not what it was intended to be
2. **Predicts Change Impact**: Identifies which modules will break when you change another
3. **Exposes Coupling**: Finds tight connections that make the system hard to maintain
4. **Detects Cycles**: Finds circular dependencies that cause build, test, and deploy issues
5. **Guides Refactoring**: Shows where to split, merge, or reorganize modules
6. **Identifies Risk**: Finds single points of failure and high-risk dependencies

---

## The 3 Things to Look For

Every dependency analysis should examine these three critical aspects:

### 1. \u2610 **Direction** \u2014 Does data flow / dependencies go in the intended direction?

**What to Check**:
- Layer violations (higher layers depending on lower layers)
- Direction of data flow (who produces, who consumes)
- Direction of control flow (who calls, who is called)
- Direction of inheritance/implementation (base vs derived)

**Why It Matters**: Wrong-direction dependencies create:
- **Change Amplification**: Changes propagate in unexpected directions
- **Circular Dependencies**: A depends on B depends on A
- **Layer Collapse**: All layers become tightly coupled
- **Testing Difficulty**: Hard to mock and isolate components

**Detection Methods**:
```bash
# Python: Check imports by layer
grep -r "^from\|^import" --include="*.py" src/domain/ | grep -E "src/(controllers|services|presentation)"

# Check if domain imports from higher layers
grep -r "from.*controllers" --include="*.py" src/domain/
grep -r "from.*services" --include="*.py" src/domain/

# Go: Check package imports by layer
go list -f '{{.ImportPath}}: {{.Imports}}' ./... | grep -E "domain.*controller|domain.*service"
```

### 2. \u2610 **Coupling** \u2014 How tightly are modules connected?

**Coupling Metrics**:
| Metric | Measurement | Interpretation |
|--------|-------------|----------------|
| **Affinity** | # of dependencies between two modules | High = tightly coupled |
| **Fan-out** | # of modules a module depends on | >7 = suspicious |
| **Fan-in** | # of modules that depend on this module | High = widely used |
| **Instability** | Fan-out / (Fan-in + Fan-out) | >0.7 = unstable |
| **Abstractness** | # of interfaces / # of classes | <0.3 = concrete |

**Coupling Types**:
- **Tight Coupling**: Direct function calls, shared state, direct instantiation
- **Loose Coupling**: Interface-based, message passing, dependency injection
- **Content Coupling**: One module modifies another's internal state
- **Common Coupling**: Modules share global data
- **External Coupling**: Modules share external resource (DB, file, API)

**Why It Matters**:
- High coupling = high change amplification
- High coupling = hard to test
- High coupling = hard to understand
- High coupling = hard to reuse

**Detection Methods**:
```bash
# Python: Find modules with high fan-out
python3 -c "
import ast, os, collections
fanout = collections.defaultdict(set)
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        fanout[rel_path].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    fanout[rel_path].add(node.module)
for module, deps in sorted(fanout.items(), key=lambda x: len(x[1]), reverse=True):
    if len(deps) > 7:
        print(f'{len(deps):3d} {module}')
"

# Use scripts/swe_audit.py --coupling --threshold 7
```

### 3. \u2610 **Cycles** \u2014 Circular dependencies that cause build / deploy / failure coupling

**Cycle Types**:
- **Import Cycles**: A imports B, B imports A (direct)
- **Transitive Cycles**: A imports B, B imports C, C imports A (indirect)
- **Build Cycles**: A needs B to build, B needs A to build
- **Deploy Cycles**: A needs B to deploy, B needs A to deploy
- **Runtime Cycles**: A calls B at runtime, B calls A at runtime

**Why Cycles Matter**:
- **Build Issues**: Can't compile A without B, can't compile B without A
- **Test Issues**: Can't test A in isolation, can't test B in isolation
- **Deploy Issues**: Must deploy A and B together, can't deploy independently
- **Failure Propagation**: Bug in A affects C via B, affects A via C
- **Understanding Issues**: Hard to understand which module owns what

**Detection Methods**:
```bash
# Python: Use pydeps to detect cycles
pip install pydeps
pydeps --max-bacon=2 ./src/ --show-cycles

# JavaScript: Use madge
npm install -g madge
madge --circular ./src/

# Go: Use go-cyclic
go install github.com/amitbet/go-cyclic@latest
go-cyclic ./...

# Custom script: Build dependency graph and detect cycles
python3 -c "
import ast, os, networkx as nx
G = nx.DiGraph()
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        G.add_edge(rel_path, alias.name)
                elif isinstance(node, ast.ImportFrom):
                    G.add_edge(rel_path, node.module)

# Find all cycles
for cycle in nx.simple_cycles(G):
    if len(cycle) > 1:
        print(' -> '.join(cycle))
"

# Use scripts/swe_audit.py --cycles
```

---

## Step-by-Step Dependency Analysis Process

### Step 1: Inventory the Modules

**Goal**: Get a complete list of all modules in the system.

**Methods by Language**:

**Python**:
```bash
# List all Python files
find . -name "*.py" -not -path "./.*" | sort

# Count files by directory
tree -L 2 -i | grep -E "\[[0-9]+\]" | head -20

# List all packages (directories with __init__.py)
find . -name "__init__.py" -printf "%h\n" | sort | uniq
```

**Go**:
```bash
# List all packages
go list ./...

# List all packages with their files
go list -f '{{.ImportPath}}: {{.GoFiles}}' ./...

# Visualize with go-mod-graph
go install github.com/ryancurrah/gomodguard@latest
gomodguard -tree .
```

**JavaScript/TypeScript**:
```bash
# List all files
find . -name "*.js" -o -name "*.ts" | sort

# Use madge to list modules
madge --list ./src/
```

**Java**:
```bash
# List all classes
find . -name "*.java" | xargs grep -l "class\|interface" | sort

# Use jdeps to analyze dependencies
jdeps -verbose:class target/classes | head -50
```

**C/C++**:
```bash
# List all source files
find . -name "*.cpp" -o -name "*.c" -o -name "*.hpp" -o -name "*.h" | sort

# Use include-what-you-use to analyze includes
iwyu-tool -p build/ -- -Xiwyu --verbose=3 2>&1 | grep "^-" | head -20
```

**Rust**:
```bash
# List all modules
cargo metadata --format-version=1 | jq -r '.packages[].targets[] | select(.kind[] | contains("lib")) | .src_path'

# Use cargo-deps to visualize
cargo install cargo-deps
cargo deps --tree
```

**Universal (for any language)**:
```bash
# Count files by extension
find . -type f -name "*.py" -o -name "*.js" -o -name "*.go" -o -name "*.java" | sed 's/.*\.//' | sort | uniq -c | sort -rn

# List all directories (potential modules)
find . -type d -not -path "./.*" -not -path "./node_modules/*" | sort
```

**Output**: A complete module inventory with:
- Module name/path
- File count
- Line count
- Language

---

### Step 2: Build the Import Graph

**Goal**: Create a graph showing which modules import which other modules.

**Methods by Language**:

**Python**:
```bash
# Simple import extraction
python3 -c "
import ast, os, sys
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') and not f.startswith('__'):
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, '.')
            try:
                tree = ast.parse(open(path).read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            print(f'{rel_path}\tIMPORT\t{alias.name}')
                    elif isinstance(node, ast.ImportFrom):
                        print(f'{rel_path}\tIMPORTFROM\t{node.module}')
            except:
                pass
" | grep -v "^\./\__" | head -50

# Use importlib to get more detailed info
python3 -c "
import sys, os
sys.path.insert(0, '.')
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, '.')
            try:
                # Get module name
                module_name = rel_path.replace('/', '.').replace('.py', '')
                # Try to import and get dependencies
                # This is risky - don't run on untrusted code!
                pass
            except:
                pass
"

# Use pydeps for visualization
pydeps --show-dot ./src/ | dot -Tpng -o deps.png
```

**Go**:
```bash
# List all imports
go list -f '{{.ImportPath}}: {{.Imports}}' ./... | head -50

# List all test imports
go list -f '{{.ImportPath}}: {{.TestImports}}' ./... | head -50

# Get full dependency tree
go mod graph | head -50

# Visualize with go-mod-graph
gomodgraph -tree .
```

**JavaScript**:
```bash
# List all imports
rg "from ['\"]([^'\"]+)['\"]" --type js -o -N | sort | uniq -c | sort -rn | head -50

# List all requires
rg "require\(['\"]([^'\"]+)['\"]\)" --type js -o -N | sort | uniq -c | sort -rn | head -50

# Use madge for visualization
madge --image graph.png ./src/
```

**Java**:
```bash
# List all imports
find . -name "*.java" -exec grep -H "^import" {} \; | head -50

# Use jdeps for dependency analysis
jdeps -verbose:package target/classes | head -50
```

**C/C++**:
```bash
# List all includes
find . -name "*.cpp" -o -name "*.c" -o -name "*.hpp" -o -name "*.h" | xargs grep -h "^#include" | sort | uniq -c | sort -rn | head -50

# Use include-what-you-use
iwyu-tool -p build/ -- -Xiwyu --verbose=3 2>&1 | grep "^-" | head -50
```

**Rust**:
```bash
# List all uses
cargo metadata --format-version=1 | jq -r '.packages[].dependencies[] | .name' | sort | uniq -c | sort -rn

# Get dependency tree
cargo tree | head -50
```

**Universal Graph Format**:
```
# Format: source_module -> target_module
# Example:
src/auth/service.py -> src/domain/user.py
src/domain/user.py -> src/infrastructure/db.py

# Build a graph file
python3 -c "
import ast, os
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        print(f'{rel_path} -> {alias.name}')
                elif isinstance(node, ast.ImportFrom):
                    print(f'{rel_path} -> {node.module}')
" > deps.txt

# Visualize with graphviz
echo "digraph G {" > deps.dot
cat deps.txt | sed 's/->/ -> /' >> deps.dot
echo "}" >> deps.dot
dot -Tpng deps.dot -o deps.png
```

**Use the provided script**:
```bash
# The swe_audit.py script has built-in dependency analysis
python scripts/swe_audit.py --deps --output deps.json
python scripts/swe_audit.py --deps --visualize --output deps.png
```

---

### Step 3: Identify Layer Violations

**Goal**: Find dependencies that violate the intended layered architecture.

**Layered Architecture Principles**:
```
┌─────────────────┐
│   Presentation   │  (UI, API Controllers)
├─────────────────┤
│   Application    │  (Use Cases, Services)
├─────────────────┤
│     Domain       │  (Business Logic, Entities)
├─────────────────┤
│  Infrastructure   │  (DB, External Services, Utils)
└─────────────────┘

Dependencies should flow DOWNWARD only:
Presentation -> Application -> Domain
Infrastructure -> Domain (via interfaces)
```

**Common Layer Violations**:

**1. Domain Imports Presentation**:
```
# WRONG: Domain depends on Presentation
domain/user.py: from controllers.auth import AuthController

# Why it's bad:
- Domain should be framework-agnostic
- Presentation changes force domain changes
- Hard to test domain in isolation
- Hard to reuse domain with different presentation
```

**2. Domain Imports Application**:
```
# WRONG: Domain depends on Application
domain/user.py: from services.email import EmailService

# Why it's bad:
- Domain should contain pure business logic
- Application layer should orchestrate domain + infrastructure
- Creates circular dependency potential
```

**3. Infrastructure Imports Presentation**:
```
# WRONG: Infrastructure depends on Presentation
infrastructure/db.py: from controllers.user import UserController

# Why it's bad:
- Infrastructure should be reusable across presentations
- Presentation changes force infrastructure changes
- Violates separation of concerns
```

**4. Presentation Imports Infrastructure Directly**:
```
# WRONG: Presentation depends directly on Infrastructure
controllers/user.py: from infrastructure.db import UserRepository

# Why it's acceptable but not ideal:
- Should go through Application layer
- Makes testing harder (need real DB)
- Makes swapping implementations harder
```

**Detection Methods**:

```bash
# Python: Check for layer violations
LAYERS=("presentation:src/presentation,src/controllers,src/api" \
        "application:src/application,src/services" \
        "domain:src/domain" \
        "infrastructure:src/infrastructure,src/repositories,src/utils")

for layer in ${LAYERS[@]}; do
    layer_name=${layer%%:*}
    layer_paths=${layer#*:}
    echo "=== Checking ${layer_name} layer ==="
    for path in $(echo $layer_paths | tr ',' ' '); do
        grep -r "^from\|^import" --include="*.py" $path | \
            grep -v "^${path}" | \
            grep -E "presentation|application|domain|infrastructure" | \
            grep -v "^from ${layer_name}" | \
            head -10
    done
done
```

**Automated Layer Check**:
```python
# scripts/swe_audit.py --layers --config layers.yaml

# layers.yaml example:
layers:
  presentation:
    paths:
      - src/presentation
      - src/controllers
      - src/api
    can_depend_on:
      - application
      - domain
  application:
    paths:
      - src/application
      - src/services
    can_depend_on:
      - domain
      - infrastructure
  domain:
    paths:
      - src/domain
    can_depend_on:
      - domain  # same layer
  infrastructure:
    paths:
      - src/infrastructure
      - src/repositories
    can_depend_on:
      - domain
      - infrastructure  # same layer
```

**Manual Layer Check**:
1. For each module in the domain layer:
   - Check all its imports
   - Flag any import from presentation, application, or infrastructure
2. For each module in the infrastructure layer:
   - Check all its imports
   - Flag any import from presentation or application
3. For each module in the presentation layer:
   - Check if it imports infrastructure directly (should go through application)

**Output**: List of all layer violations with:
- Source module (the violator)
- Target module (what it's importing)
- Layer of source
- Layer of target
- Why it's a violation

---

### Step 4: Find Cycles

**Goal**: Identify circular dependencies in the graph.

**Cycle Detection Methods**:

**Using pydeps (Python)**:
```bash
# Install pydeps
pip install pydeps

# Detect cycles
pydeps --max-bacon=2 ./src/ --show-cycles

# More detailed cycle detection
pydeps --max-bacon=5 ./src/ --show-cycles --show-dot | grep -A5 "Cycle:"
```

**Using madge (JavaScript)**:
```bash
# Install madge
npm install -g madge

# Detect cycles
madge --circular ./src/

# Detailed cycle info
madge --circular --image graph.png ./src/
```

**Using go-cyclic (Go)**:
```bash
# Install go-cyclic
go install github.com/amitbet/go-cyclic@latest

# Detect cycles
go-cyclic ./...
```

**Using jdeps (Java)**:
```bash
# Detect cycles in Java
jdeps -verbose:package target/classes | grep -i cycle
```

**Manual Cycle Detection**:
```python
import ast, os, networkx as nx
from collections import defaultdict

# Build the dependency graph
G = nx.DiGraph()
all_modules = set()

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            all_modules.add(rel_path)
            
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name
                        if target.startswith('src.'):
                            G.add_edge(rel_path, target.replace('.', '/'))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        target = node.module
                        if target.startswith('src.'):
                            G.add_edge(rel_path, target.replace('.', '/'))

# Find all simple cycles
print("=== Simple Cycles ===")
for cycle in nx.simple_cycles(G):
    if len(cycle) > 1:
        print(" -> ".join(cycle))

# Find strongly connected components (cycles of any length)
print("\n=== Strongly Connected Components ===")
for component in nx.strongly_connected_components(G):
    if len(component) > 1:
        print(f"Component ({len(component)} modules):")
        for module in sorted(component):
            print(f"  - {module}")
```

**Cycle Analysis**:
For each cycle found, analyze:
1. **Length**: Number of modules in the cycle
2. **Type**: Import cycle, build cycle, runtime cycle
3. **Impact**: Build, test, deploy, or runtime impact
4. **Severity**: P0 (blocks build), P1 (blocks test), P2 (blocks deploy), P3 (runtime only)

**Cycle Severity Matrix**:
| Cycle Length | Build Impact | Test Impact | Deploy Impact | Severity |
|--------------|--------------|-------------|--------------|----------|
| 2 | High | High | High | P0 |
| 3-5 | High | High | Medium | P1 |
| 6-10 | Medium | Medium | Medium | P2 |
| 10+ | Low | Low | Low | P3 |

**Cycle Resolution Strategies**:

**1. Extract Interface (Most Common)**:
```
# Before: A -> B, B -> A (cycle)
# After: A -> I, B -> I, I is interface
```

**2. Merge Modules**:
```
# Before: A -> B, B -> A
# After: AB (merged module)
```

**3. Invert Dependency**:
```
# Before: A -> B, B -> A
# After: A <- B, B -> A (one direction only)
```

**4. Introduce Mediator**:
```
# Before: A -> B, B -> C, C -> A
# After: A -> M, B -> M, C -> M, M coordinates
```

**5. Use Dependency Injection**:
```
# Before: A creates B directly, B creates A directly
# After: A receives B via constructor, B receives A via constructor
```

---

### Step 5: Analyze Fan-in and Fan-out

**Goal**: Identify modules with abnormal dependency patterns.

**Fan-in**: Number of modules that depend on this module (how many import it)
**Fan-out**: Number of modules this module depends on (how many it imports)

**Fan-in/Fan-out Interpretation**:

| Fan-in | Fan-out | Pattern | Interpretation | Action |
|--------|---------|---------|----------------|--------|
| High | Low | Utility | Widely used, focused | Monitor for changes |
| Low | Low | Leaf | Specialized, isolated | Usually fine |
| High | High | Hub | Coupling magnet | Refactor target |
| Low | High | Black Hole | Depends on many, used by few | Wrong abstraction |
| Medium | Medium | Normal | Balanced | Usually fine |

**Detection**:
```python
import ast, os, networkx as nx
from collections import defaultdict

# Build the graph
G = nx.DiGraph()
fan_in = defaultdict(int)
fan_out = defaultdict(int)

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            
            tree = ast.parse(open(path).read())
            deps = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.add(node.module)
            
            fan_out[rel_path] = len(deps)
            for dep in deps:
                if dep.startswith('src.'):
                    target = dep.replace('.', '/')
                    G.add_edge(rel_path, target)
                    fan_in[target] += 1

# Calculate instability
instability = {}
for module in set(fan_in.keys()) | set(fan_out.keys()):
    fi = fan_in.get(module, 0)
    fo = fan_out.get(module, 0)
    if fi + fo > 0:
        instability[module] = fo / (fi + fo)
    else:
        instability[module] = 0

# Print results
print("=== Fan-in / Fan-out Analysis ===")
print(f"{'Module':<50} {'Fan-in':>8} {'Fan-out':>8} {'Instability':>12}")
print("-" * 80)
for module in sorted(instability.keys(), key=lambda x: instability[x], reverse=True):
    fi = fan_in.get(module, 0)
    fo = fan_out.get(module, 0)
    inst = instability.get(module, 0)
    pattern = ""
    if fi > 10 and fo < 3:
        pattern = "Utility"
    elif fi < 3 and fo > 7:
        pattern = "Black Hole"
    elif fi > 5 and fo > 5:
        pattern = "Hub"
    elif fi < 3 and fo < 3:
        pattern = "Leaf"
    else:
        pattern = "Normal"
    print(f"{module:<50} {fi:>8} {fo:>8} {inst:>12.2f}  {pattern}")

# Find hubs
print("\n=== Hub Modules (High Fan-in + High Fan-out) ===")
for module in sorted(instability.keys()):
    fi = fan_in.get(module, 0)
    fo = fan_out.get(module, 0)
    if fi > 5 and fo > 5:
        print(f"{module}: fan-in={fi}, fan-out={fo}, instability={instability[module]:.2f}")

# Find black holes
print("\n=== Black Hole Modules (Low Fan-in + High Fan-out) ===")
for module in sorted(instability.keys()):
    fi = fan_in.get(module, 0)
    fo = fan_out.get(module, 0)
    if fi < 3 and fo > 7:
        print(f"{module}: fan-in={fi}, fan-out={fo}, instability={instability[module]:.2f}")
```

**Hub Module Analysis**:
Hub modules (high fan-in + high fan-out) are:
- **Good**: If they're truly shared utilities (logging, config, etc.)
- **Bad**: If they're doing too much (god modules, kitchen sink modules)

**Hub Module Refactoring**:
1. **Identify Responsibilities**: What does the hub actually do?
2. **Group by Function**: Split into logical groups
3. **Extract Interfaces**: For each group, define a clear interface
4. **Create New Modules**: Move each group to its own module
5. **Update Dependencies**: Point all consumers to the new modules

**Black Hole Module Analysis**:
Black hole modules (low fan-in + high fan-out) are:
- **Good**: If they're infrastructure modules that many things depend on
- **Bad**: If they're application modules that depend on too much (wrong abstraction level)

**Black Hole Module Refactoring**:
1. **Check Abstraction Level**: Is this module at the right layer?
2. **Identify Dependencies**: What does it depend on and why?
3. **Push Down Dependencies**: Move some dependencies to lower layers
4. **Split Module**: If it's doing too much, split it up

---

### Step 6: The "build order" check

**Goal**: Verify that the dependency graph can be topologically sorted (no cycles).

**Topological Sort**: An ordering of modules such that for every dependency A -> B, A comes before B in the ordering.

**Methods**:

**Using NetworkX**:
```python
import ast, os, networkx as nx

# Build the graph (same as before)
G = nx.DiGraph()
# ... (build graph)

# Try topological sort
try:
    build_order = list(nx.topological_sort(G))
    print("=== Build Order ===")
    for i, module in enumerate(build_order):
        print(f"{i+1:3d}. {module}")
    print("\n✓ Graph is acyclic - topological sort successful")
except nx.NetworkXError as e:
    print(f"✗ Graph has cycles - topological sort failed: {e}")
    # Find cycles
    for cycle in nx.simple_cycles(G):
        print(f"  Cycle: {' -> '.join(cycle)}")
```

**Using Make**:
```bash
# If the project uses Make, check for circular dependencies
make --debug -n | grep -i "circular\|cycle"
```

**Using Bazel**:
```bash
# Check for circular dependencies in Bazel
bazel query --notool_deps --noimplicit_deps 'allpaths(//..., //...)' 2>&1 | grep -i "cycle\|circular"
```

**Build Order Interpretation**:
1. **Leaf Modules**: Modules with no dependencies (come first in build order)
2. **Middle Modules**: Modules that depend on leaves and are depended on by others
3. **Root Modules**: Modules that everything else depends on (come last)
4. **Entry Points**: The final modules that get built (main, API, CLI)

**Build Order Problems**:
- **Circular Dependencies**: Can't build, topological sort fails
- **Missing Dependencies**: Modules that should be in the graph but aren't
- **Incorrect Order**: Dependencies that should exist but don't in the code

---

### Step 7: The "deployable unit" check

**Goal**: Identify which modules must deploy together.

**Deployable Unit**: A set of modules that must be deployed together because they are tightly coupled.

**Coupling Criteria**:
1. **Build Coupling**: Share a build artifact (same JAR, same Python package)
2. **Runtime Coupling**: Run in the same process
3. **Database Coupling**: Share a database (schema changes require coordination)
4. **Contract Coupling**: Share an API (breaking changes require coordination)

**Detection Methods**:

**Build Coupling**:
```bash
# Python: Check setup.py or pyproject.toml for packages
cat setup.py | grep -A20 "packages="

# Check if modules are in the same package
python3 -c "
import os
packages = {}
for root, dirs, files in os.walk('src'):
    for f in files:
        if f == '__init__.py':
            path = os.path.join(root, f)
            pkg = os.path.relpath(path, 'src').replace('/', '.')
            packages[pkg] = packages.get(pkg, 0) + 1
for pkg, count in sorted(packages.items(), key=lambda x: x[1], reverse=True):
    print(f'{pkg}: {count} modules')
"
```

**Runtime Coupling**:
```bash
# Check for modules that are always used together
# (This requires runtime analysis or careful code review)

# Find modules that are imported together frequently
grep -r "^from\|^import" --include="*.py" src/ | \
    sed 's/.*:from //; s/ import .*//; s/^import //' | \
    sort | uniq -c | sort -rn | head -20
```

**Database Coupling**:
```bash
# Find modules that access the same database tables
rg "SELECT.*FROM\|INSERT.*INTO\|UPDATE.*SET" --type py src/ | \
    sed 's/.*FROM //; s/ .*//; s/INSERT.*INTO //; s/ .*//; s/UPDATE.*SET //; s/ .*//' | \
    sort | uniq -c | sort -rn | head -20

# Find modules with database models
rg "class.*\(.*Model\|class.*\(.*db\.Model" --type py src/ | \
    sed 's/.*:class //; s/ .*//' | sort | uniq -c | sort -rn
```

**Contract Coupling**:
```bash
# Find modules that define or use the same API endpoints
rg "@app\.route\|@router\.\w+\|def.*\w+\(.*request" --type py src/ | \
    sed 's/.*://; s/(.*//' | sort | uniq -c | sort -rn | head -20

# Find modules that share the same message/event types
rg "class.*Message\|class.*Event\|class.*Command" --type py src/ | \
    sed 's/.*:class //; s/ .*//' | sort | uniq -c | sort -rn
```

**Deployable Unit Identification**:
```python
# Analyze coupling to identify deployable units
import ast, os, networkx as nx
from collections import defaultdict

# Build dependency graph
G = nx.DiGraph()
# ... (build graph as before)

# Identify strongly connected components (potential deployable units)
components = list(nx.strongly_connected_components(G))

print("=== Deployable Units (Strongly Connected Components) ===")
for i, component in enumerate(components):
    if len(component) > 1:
        print(f"\nUnit {i+1} ({len(component)} modules):")
        for module in sorted(component):
            print(f"  - {module}")
    else:
        # Check if single module has external coupling
        module = list(component)[0]
        # Check for database, API, or other external coupling
        # ... (implementation depends on your analysis needs)
        pass
```

**Deployable Unit Analysis**:
For each deployable unit, document:
1. **Modules**: List of modules in the unit
2. **Coupling Type**: Build, runtime, database, contract
3. **Deployment Frequency**: How often this unit deploys
4. **Change Frequency**: How often modules in this unit change
5. **Risk**: Impact of deploying this unit

**Deployable Unit Problems**:
- **Oversized Units**: Too many modules that don't need to deploy together
- **Frequent Changes**: Units that change often should be small
- **High Risk**: Units with high impact should be well-tested
- **Circular Dependencies**: Units that can't be deployed independently

---

### Step 8: The "ownership boundary" check

**Goal**: Verify that module ownership is clear and dependencies respect ownership boundaries.

**Ownership Principles**:
1. **Clear Ownership**: Every module should have a clear owner
2. **Respect Boundaries**: Modules should not cross ownership boundaries without good reason
3. **Minimize Cross-Team Dependencies**: Dependencies between teams should be minimized
4. **Stable Contracts**: Cross-team dependencies should have stable, versioned contracts

**Detection Methods**:

**Ownership Mapping**:
```bash
# Create a ownership map (this is typically manual or from external data)
# Format: module_path -> owner_team
cat > ownership.yaml << 'EOF'
ownership:
  src/presentation/*: frontend-team
  src/api/*: api-team
  src/application/*: backend-team
  src/domain/*: backend-team
  src/infrastructure/db/*: db-team
  src/infrastructure/*: backend-team
  src/utils/*: shared-team
EOF
```

**Cross-Team Dependencies**:
```python
import yaml, ast, os, networkx as nx

# Load ownership map
with open('ownership.yaml') as f:
    ownership = yaml.safe_load(f)['ownership']

# Get owner for a module
def get_owner(module_path):
    for pattern, owner in ownership.items():
        if module_path.startswith(pattern.replace('*', '')):
            return owner
    return 'unknown'

# Build graph and check cross-team dependencies
G = nx.DiGraph()
cross_team_deps = []

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            source_owner = get_owner(rel_path)
            
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name
                        if target.startswith('src.'):
                            target_path = target.replace('.', '/')
                            target_owner = get_owner(target_path)
                            if source_owner != target_owner and source_owner != 'unknown' and target_owner != 'unknown':
                                cross_team_deps.append({
                                    'source': rel_path,
                                    'target': target_path,
                                    'source_owner': source_owner,
                                    'target_owner': target_owner
                                })
                                G.add_edge(f"{rel_path} ({source_owner})", f"{target_path} ({target_owner})")

print("=== Cross-Team Dependencies ===")
for dep in cross_team_deps:
    print(f"{dep['source']} ({dep['source_owner']}) -> {dep['target']} ({dep['target_owner']})")

# Visualize
nx.drawing.nx_pydot.write_dot(G, 'cross-team-deps.dot')
```

**Ownership Boundary Violations**:
1. **Direct Cross-Team Import**: Team A imports Team B's internal module directly
2. **Dependency on Unowned Module**: Any module imports a module with no clear owner
3. **Circular Cross-Team Dependency**: Team A depends on Team B depends on Team A
4. **Unstable Cross-Team Contract**: Cross-team dependency without versioning

**Ownership Analysis**:
For each cross-team dependency, document:
1. **Source Team**: Team that owns the source module
2. **Target Team**: Team that owns the target module
3. **Dependency Type**: Import, API call, database access, etc.
4. **Stability**: Is the contract stable and versioned?
5. **Risk**: What happens if the target changes?

---

### Step 9: The "API contract" check

**Goal**: Verify that cross-module APIs have proper contracts.

**API Contract Requirements**:
1. **Stable**: Contract doesn't change unexpectedly
2. **Documented**: Contract is documented (OpenAPI, protobuf, etc.)
3. **Tested**: Contract is tested (consumer-driven tests)
4. **Versioned**: Contract has versioning (v1, v2, etc.)

**Contract Types**:
1. **Function/Method Contracts**: Input types, output types, exceptions
2. **API Endpoint Contracts**: HTTP methods, paths, request/response schemas
3. **Message Contracts**: Event schemas, message formats
4. **Database Contracts**: Table schemas, query interfaces

**Detection Methods**:

**Function Contracts**:
```bash
# Find functions with no type hints
rg "^\s*def\s+\w+\([^)]*\):" --type py src/ | grep -v "->" | head -20

# Find functions with no docstrings
python3 -c "
import ast, os
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        print(f'{path}:{node.lineno}: {node.name} has no docstring')
" | head -20
```

**API Endpoint Contracts**:
```bash
# Find API endpoints
rg "@app\.route\|@router\.\w+\|@RestController\|@GetMapping\|@PostMapping" --type py -A 1 src/ | head -40

# Check for OpenAPI/Swagger documentation
find . -name "*.yaml" -o -name "*.yml" -o -name "*.json" | xargs grep -l "openapi\|swagger" 2>/dev/null | head -10
```

**Message Contracts**:
```bash
# Find message/event classes
rg "class.*Message\|class.*Event\|class.*Command\|@message" --type py src/ | head -20

# Check for schema definitions
find . -name "*.proto" -o -name "*.avsc" -o -name "*.json" | xargs grep -l "schema\|message\|event" 2>/dev/null | head -10
```

**Database Contracts**:
```bash
# Find database models
rg "class.*\(.*Model\|class.*\(.*db\.Model\|@entity" --type py src/ | head -20

# Find migration files
find . -name "*migration*" -o -name "*migrate*" | head -10
```

**Contract Analysis**:
For each API, document:
1. **Contract Type**: Function, endpoint, message, database
2. **Stability**: Is it stable or frequently changing?
3. **Documentation**: Is it documented?
4. **Testing**: Is it tested?
5. **Versioning**: Is it versioned?

**Contract Problems**:
- **Unstable Contracts**: APIs that change frequently
- **Undocumented Contracts**: APIs with no documentation
- **Untested Contracts**: APIs with no tests
- **Unversioned Contracts**: APIs with no versioning
- **Breaking Changes**: Changes that break consumers

---

### Step 10: The "hidden dependency" check

**Goal**: Find dependencies that aren't visible through static import analysis.

**Hidden Dependency Types**:

**1. Reflection / Runtime Loading**:
```python
# Python examples
importlib.import_module(module_name)  # Dynamic import
__import__(module_name)              # Built-in dynamic import
getattr(module, function_name)()      # Dynamic attribute access

# Java examples
Class.forName(className)             # Dynamic class loading

# JavaScript examples
require(dynamicPath)                 # Dynamic require
new Function(code)                   # eval-like
```

**Detection**:
```bash
# Python: Find dynamic imports
rg "importlib\.import_module\|__import__\|getattr.*\(.*\)" --type py src/ | head -20

# Java: Find Class.forName
rg "Class\.forName" --type java src/ | head -20

# JavaScript: Find dynamic requires
rg "require\([^']" --type js src/ | head -20
```

**2. Configuration-Driven Dependencies**:
```python
# Configuration that determines which module to load
config = {
    'handler': 'module.submodule.HandlerClass'
}
handler = getattr(importlib.import_module(config['handler']), 'handle')
```

**Detection**:
```bash
# Find config files with module paths
find . -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" | \
    xargs grep -l "\.py\|\.js\|\.java" 2>/dev/null | head -10

# Check for config-based module loading
rg "import.*config\|from.*config" --type py src/ -A 5 | grep -E "import_module|__import__|getattr" | head -20
```

**3. Database Coupling**:
Two modules that share a database table are coupled, even if they don't import each other.

**Detection**:
```bash
# Find modules that access the same tables
rg "SELECT.*FROM\|INSERT.*INTO\|UPDATE.*\|DELETE.*FROM" --type py src/ | \
    sed 's/.*FROM //; s/ .*//; s/INSERT.*INTO //; s/ .*//; s/UPDATE //; s/ .*//; s/DELETE.*FROM //; s/ .*//' | \
    sort | uniq -c | sort -rn | head -20

# Find database models that are used by multiple modules
rg "class.*Model\|from.*models.*import" --type py src/ | \
    sed 's/.*import //; s/ .*//; s/.*:class //; s/ .*//' | \
    sort | uniq -c | sort -rn | head -20
```

**4. Network/HTTP Coupling**:
Modules that call each other's HTTP APIs are coupled.

**Detection**:
```bash
# Find HTTP client calls
rg "requests\.(get|post|put|delete|patch)\|httpx\.(get|post|put|delete|patch)\|fetch\(" --type py src/ | head -20

# Find hardcoded URLs
rg "http://[^'\"]+\|https://[^'\"]+" --type py src/ | head -20

# Find service-to-service calls
rg "service.*url\|api.*url\|endpoint.*url" --type py src/ -B 2 -A 2 | head -40
```

**5. Event/Message Coupling**:
Modules that publish and consume the same events are coupled.

**Detection**:
```bash
# Find event publishers
rg "publish\|emit\|send.*event\|send.*message" --type py src/ | head -20

# Find event subscribers
rg "subscribe\|on.*event\|on.*message\|consume" --type py src/ | head -20

# Find event types
rg "class.*Event\|class.*Message" --type py src/ | head -20
```

**Hidden Dependency Analysis**:
For each hidden dependency, document:
1. **Type**: Reflection, configuration, database, network, event
2. **Source**: Module that creates the dependency
3. **Target**: Module or resource being depended on
4. **Mechanism**: How the dependency is created
5. **Risk**: Impact if the target changes

---

### Step 11: The "dead dependency" check

**Goal**: Find imports that are no longer used.

**Dead Dependency Types**:
1. **Unused Imports**: Imported but never used
2. **Unused Classes/Functions**: Defined but never used
3. **Unused Variables**: Assigned but never used

**Detection Methods**:

**Python**:
```bash
# Use ruff to find unused imports
ruff check --select F401 src/

# Use vulture to find dead code
vulture src/ --min-confidence 80

# Manual check with AST
python3 -c "
import ast, os
from collections import defaultdict

# Collect all defined names
all_defined = defaultdict(set)
all_used = defaultdict(set)

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            
            try:
                tree = ast.parse(open(path).read())
                
                # Collect defined names
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        all_defined[rel_path].add(node.name)
                    elif isinstance(node, ast.ClassDef):
                        all_defined[rel_path].add(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            all_defined[rel_path].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            all_defined[rel_path].add(node.module)
                
                # Collect used names
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        all_used[rel_path].add(node.id)
                        
            except:
                pass

# Find unused imports
for path in all_defined:
    defined = all_defined[path]
    used = all_used.get(path, set())
    unused = defined - used
    if unused:
        print(f'{path}:')
        for name in sorted(unused):
            if not name.startswith('_'):
                print(f'  Unused: {name}')
" | head -50
```

**Go**:
```bash
# Use go vet to find unused imports
go vet ./...

# Use staticcheck
go install honnef.co/go/tools/cmd/staticcheck@latest
staticcheck ./...
```

**JavaScript**:
```bash
# Use ESLint
npx eslint --rule 'no-unused-vars: ["error"]' src/

# Use TypeScript compiler
tsc --noEmit | grep -i "unused\|not used"
```

**Java**:
```bash
# Use SpotBugs (FindBugs)
spotbugs -textui -effort:max -medium src/
```

**Dead Dependency Analysis**:
For each dead dependency, document:
1. **Type**: Unused import, unused class, unused function, unused variable
2. **Location**: File and line number
3. **Name**: The unused name
4. **Risk**: Impact of leaving it (usually low)
5. **Action**: Remove or document why it's kept

**Dead Dependency Severity**:
- **P3**: Unused imports, variables, functions
- **P2**: Unused classes, modules
- **P1**: Unused dependencies that cause issues (e.g., security vulnerabilities)

---

### Step 12: The "duplicate dependency" check

**Goal**: Find modules that do the same thing (duplication).

**Duplicate Detection Methods**:

**1. By Functionality**:
```bash
# Find similar functions across modules
# (This requires semantic analysis or careful manual review)

# Simple: Find functions with similar names
rg "^\s*def\s+\w+_util\|^\s*def\s+utility_\|^\s*def\s+helper_" --type py src/ | \
    sed 's/.*def //; s/(.*//' | sort | uniq -c | sort -rn | head -20
```

**2. By Code Similarity**:
```bash
# Use jscpd to find duplicate code
npx jscpd --format python --min-tokens 50 --output ./jscpd-results src/

# Use simian
simian -threshold=5 --ignore='.*test.*' src/
```

**3. By Import Pattern**:
```bash
# Find modules with similar import sets
python3 -c "
import ast, os
from collections import defaultdict

# Collect imports for each module
module_imports = defaultdict(set)

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, 'src')
            
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_imports[rel_path].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_imports[rel_path].add(node.module)

# Find similar import sets (Jaccard similarity > 0.7)
from itertools import combinations
modules = list(module_imports.keys())
for m1, m2 in combinations(modules, 2):
    s1 = module_imports[m1]
    s2 = module_imports[m2]
    if s1 and s2:
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        similarity = intersection / union if union > 0 else 0
        if similarity > 0.7:
            print(f'{m1} <-> {m2}: {similarity:.2f}')
" | head -20
```

**4. By File Content**:
```bash
# Use fdupes to find duplicate files
fdupes -r src/ | head -20

# Use md5sum to find files with same content
find src/ -name "*.py" -type f -exec md5sum {} \; | sort | uniq -w32 -dD | head -20
```

**Duplicate Dependency Analysis**:
For each duplicate, document:
1. **Type**: Function, class, module, file
2. **Location**: Files involved
3. **Similarity**: How similar they are (percentage or description)
4. **Divergence**: How they differ
5. **Recommendation**: Merge, keep both, or remove one

**Duplicate Resolution Strategies**:
1. **Merge**: Combine into a single module/function
2. **Extract Common**: Extract shared code to a common module
3. **Keep Both**: If the duplication is intentional and beneficial
4. **Remove One**: If one is clearly superior

---

### Step 13: The "transitive dependency" check

**Goal**: Analyze the full transitive dependency graph, not just direct dependencies.

**Transitive Dependency**: If A depends on B, and B depends on C, then A transitively depends on C.

**Why It Matters**:
- **Supply Chain Risk**: Vulnerabilities in transitive dependencies affect you
- **Version Conflicts**: Different versions of the same dependency
- **Bloat**: Unnecessary transitive dependencies increase size and attack surface
- **Licensing**: Transitive dependencies may have incompatible licenses

**Detection Methods**:

**Python**:
```bash
# Use pipdeptree to see transitive dependencies
pip install pipdeptree
pipdeptree | head -50

# Check for version conflicts
pipdeptree | grep -E "^\[conflict\]" | head -20
```

**JavaScript**:
```bash
# Use npm ls to see dependency tree
npm ls --all | head -50

# Check for duplicates
npm ls --depth=0 | grep -E "^\S+@" | sort | uniq -c | sort -rn | head -20
```

**Go**:
```bash
# Use go mod graph to see full dependency tree
go mod graph | head -50

# Use go list to see dependencies
go list -m -json all | jq -r '.Path + "@" + .Version' | sort | uniq -c | sort -rn | head -20
```

**Java**:
```bash
# Use Maven dependency tree
mvn dependency:tree | head -50

# Check for conflicts
mvn dependency:tree | grep -E "\[ERROR\]\|Conflict" | head -20
```

**Rust**:
```bash
# Use cargo tree to see full dependency tree
cargo tree | head -50

# Check for duplicates
cargo tree | grep -E "^\S+ v" | sort | uniq -c | sort -rn | head -20
```

**Transitive Dependency Analysis**:
For each transitive dependency, document:
1. **Name**: Package/module name
2. **Version**: Version in use
3. **Depth**: How many levels deep in the dependency tree
4. **Direct Dependents**: Which direct dependencies pull it in
5. **Risk**: Security, licensing, stability risks

**Transitive Dependency Problems**:
1. **Version Conflicts**: Different versions of the same package
2. **Security Vulnerabilities**: Known CVEs in transitive dependencies
3. **License Incompatibility**: Licenses that conflict with your project
4. **Abandoned Packages**: Packages no longer maintained
5. **Bloat**: Unnecessarily large dependency trees

**Transitive Dependency Management**:
1. **Audit Regularly**: Check for new vulnerabilities and updates
2. **Pin Versions**: Use lockfiles to pin exact versions
3. **Minimize Dependencies**: Remove unused dependencies
4. **Monitor**: Set up alerts for new vulnerabilities
5. **Document**: Document why each dependency is needed

---

### Step 14: The "version drift" check

**Goal**: Find different versions of the same dependency being used.

**Version Drift**: When different modules depend on different versions of the same package.

**Why It Matters**:
- **Behavior Differences**: Different versions may behave differently
- **Compatibility Issues**: Code written for one version may break with another
- **Security Issues**: Older versions may have known vulnerabilities
- **Maintenance Burden**: Harder to update when versions are inconsistent

**Detection Methods**:

**Python**:
```bash
# Check pip freeze for duplicate packages
pip freeze | grep -E "^\S+==" | sort | uniq -c | sort -rn | head -20

# Use pipdeptree to see version conflicts
pipdeptree | grep -E "^\[conflict\]" -A 5 | head -40

# Check requirements files
find . -name "requirements*.txt" -exec cat {} \; | grep -E "^\S+==" | sort | uniq -c | sort -rn | head -20
```

**JavaScript**:
```bash
# Check package.json files
find . -name "package.json" -exec jq -r '.dependencies | to_entries[] | "\(.key)@\(.value)"' {} \; | sort | uniq -c | sort -rn | head -20

# Check for version conflicts
npm ls --depth=0 | grep -E "^\S+@" | sort | uniq -c | sort -rn | head -20
```

**Go**:
```bash
# Check go.mod for dependencies
grep -E "^\s+\S+\s+\S+" go.mod | sort | uniq -c | sort -rn | head -20

# Check for indirect dependencies with different versions
go list -m -json all | jq -r '[.Path, .Version] | @tsv' | sort | uniq -c | sort -rn | head -20
```

**Java**:
```bash
# Check pom.xml files
find . -name "pom.xml" -exec grep -E '<artifactId>|<version>' {} \; | grep -B1 '<version>' | grep -E '<artifactId>|<version>' | paste -d " " - | sort | uniq -c | sort -rn | head -20

# Use Maven to check for conflicts
mvn dependency:tree | grep -E "\[ERROR\]" -A 3 | head -40
```

**Rust**:
```bash
# Check Cargo.toml
find . -name "Cargo.toml" -exec grep -E '^\s+name\s*=\s*|^\s+version\s*=' {} \; | paste -d " " - | sort | uniq -c | sort -rn | head -20

# Use cargo tree to see version conflicts
cargo tree | grep -E "^\S+ v" | sort | uniq -c | sort -rn | head -20
```

**Version Drift Analysis**:
For each version conflict, document:
1. **Package**: The package with version drift
2. **Versions**: Which versions are being used
3. **Modules**: Which modules depend on which versions
4. **Impact**: What problems this causes
5. **Resolution**: How to resolve the conflict

**Version Drift Resolution Strategies**:
1. **Upgrade All**: Upgrade all dependents to the latest version
2. **Downgrade All**: Downgrade all dependents to the oldest version
3. **Isolate**: Use dependency isolation (e.g., npm nested node_modules)
4. **Fork**: Fork the dependency and maintain a compatible version
5. **Remove**: Remove the dependency if possible

---

## The Dependency Analysis Report Template

Use this template to document your dependency analysis findings:

```markdown
# Dependency Analysis Report \u2014 [Project Name]

**Analyst**: [Your Name]
**Date**: [YYYY-MM-DD]
**Scope**: [What was analyzed]
**Methodology**: [Static analysis, code review, etc.]

---

## Executive Summary

**Verdict**: [PASS/CONCERNS/FAIL/BLOCKED]

[3-5 sentence summary of what was found and what to do]

---

## Architecture Overview

### Module Inventory
| Module | Files | LOC | Language | Layer |
|--------|-------|-----|----------|-------|
| src/domain | 25 | 12,450 | Python | Domain |
| src/application | 18 | 8,720 | Python | Application |
| ... | ... | ... | ... | ... |

### Dependency Graph Metrics
| Metric | Value | Interpretation |
|--------|-------|----------------|
| Total Modules | 62 | - |
| Total Dependencies | 456 | - |
| Average Fan-out | 7.35 | High (target < 5) |
| Max Fan-out | 23 | Too high |
| Cycles Detected | 3 | Needs resolution |
| Layer Violations | 8 | Needs resolution |

---

## Findings

### P0 \u2014 Critical Issues

| # | Issue | Location | Evidence | Impact | Recommendation |
|---|-------|----------|----------|--------|----------------|
| 1 | Circular dependency between domain/user and controllers/auth | domain/user.py:1, controllers/auth.py:5 | [Evidence] | Blocks build | Extract interface |
| 2 | ... | ... | ... | ... | ... |

### P1 \u2014 High Priority Issues

| # | Issue | Location | Evidence | Impact | Recommendation |
|---|-------|----------|----------|--------|----------------|
| 1 | Hub module: services/common.py has fan-out of 23 | services/common.py | [Evidence] | High coupling | Split into smaller modules |
| 2 | ... | ... | ... | ... | ... |

### P2 \u2014 Medium Priority Issues

| # | Issue | Location | Evidence | Impact | Recommendation |
|---|-------|----------|----------|--------|----------------|
| 1 | Duplicate date formatting in utils/dates.py and helpers/datetime.py | Both files | [Evidence] | Maintenance burden | Consolidate |
| 2 | ... | ... | ... | ... | ... |

### P3 \u2014 Low Priority Issues

| # | Issue | Location | Evidence | Impact | Recommendation |
|---|-------|----------|----------|--------|----------------|
| 1 | Unused import in utils/legacy.py:5 | utils/legacy.py:5 | [Evidence] | Minor cleanup | Remove |
| 2 | ... | ... | ... | ... | ... |

---

## Layer Violations

| Source | Target | Source Layer | Target Layer | Type | Recommendation |
|--------|--------|--------------|--------------|------|----------------|
| domain/user.py | controllers/auth.py | Domain | Presentation | Import | Extract interface |
| domain/order.py | services/email.py | Domain | Application | Import | Move to application |
| ... | ... | ... | ... | ... | ... |

---

## Cycles

| # | Modules in Cycle | Length | Type | Impact | Recommendation |
|---|------------------|--------|------|--------|----------------|
| 1 | domain/user.py -> controllers/auth.py -> domain/user.py | 2 | Import | Build failure | Extract interface |
| 2 | services/a.py -> services/b.py -> services/c.py -> services/a.py | 3 | Import | Test failure | Merge or extract |
| ... | ... | ... | ... | ... | ... |

---

## Hub Modules

| Module | Fan-in | Fan-out | Instability | Pattern | Recommendation |
|--------|-------|---------|-------------|---------|----------------|
| services/common.py | 15 | 23 | 0.61 | Hub | Split into focused modules |
| utils/helpers.py | 22 | 8 | 0.27 | Utility | Monitor for changes |
| ... | ... | ... | ... | ... | ... |

---

## Black Hole Modules

| Module | Fan-in | Fan-out | Instability | Issue | Recommendation |
|--------|-------|---------|-------------|-------|----------------|
| services/data_processor.py | 2 | 15 | 0.88 | Depends on too much | Push dependencies down |
| ... | ... | ... | ... | ... | ... |

---

## Cross-Team Dependencies

| Source | Target | Source Team | Target Team | Type | Risk | Recommendation |
|--------|--------|-------------|-------------|------|------|----------------|
| frontend/api.py | backend/service.py | Frontend | Backend | API call | Medium | Document contract |
| ... | ... | ... | ... | ... | ... | ... |

---

## Hidden Dependencies

| Type | Source | Target | Mechanism | Risk | Recommendation |
|------|--------|--------|-----------|------|----------------|
| Reflection | src/plugins/loader.py | Dynamic modules | importlib.import_module() | High | Use plugin registry |
| Database | src/services/a.py, src/services/b.py | users table | Direct SQL | Medium | Use shared repository |
| ... | ... | ... | ... | ... | ... |

---

## Transitive Dependencies

| Package | Version | Depth | Direct Dependents | Risk | Recommendation |
|---------|---------|-------|-------------------|------|----------------|
| requests | 2.28.0 | 1 | src/services/* | Medium | Upgrade to 2.31.0 |
| lodash | 4.17.21 | 2 | src/utils/* | High (CVE-2021-23337) | Upgrade to 4.17.22 |
| ... | ... | ... | ... | ... | ... |

---

## Version Drift

| Package | Versions | Modules | Impact | Recommendation |
|---------|----------|---------|--------|----------------|
| requests | 2.28.0, 2.31.0 | src/a.py, src/b.py | Behavior difference | Upgrade all to 2.31.0 |
| ... | ... | ... | ... | ... |

---

## Limitations

This analysis:
- [X] Covered all Python modules in src/
- [ ] Covered JavaScript modules (no JS code in scope)
- [ ] Covered runtime dependencies (static analysis only)
- [ ] Covered production configuration (no access to production)
- [ ] Covered third-party services (no access to external services)

Assumptions:
1. The code analyzed is the production version
2. No additional input validation exists upstream
3. The analysis environment is representative of production

---

## Recommended Next Steps

### Immediate (Before Next Release)
1. **Fix P0 cycles**: Extract interfaces to break circular dependencies
   - Effort: 2 PRs, 4 hours
   - Owner: Backend team
   - Deadline: This sprint

2. **Fix P0 layer violations**: Remove domain imports from presentation layer
   - Effort: 1 PR, 2 hours
   - Owner: Backend team
   - Deadline: This sprint

### This Sprint
1. **Split hub modules**: Split services/common.py into focused modules
   - Effort: 3 PRs, 1 day
   - Owner: Backend team
   - Deadline: End of sprint

2. **Resolved version conflicts**: Upgrade all requests to 2.31.0
   - Effort: 1 PR, 1 hour
   - Owner: Backend team
   - Deadline: End of sprint

### Next Sprint
1. **Consolidate duplicates**: Merge utils/dates.py and helpers/datetime.py
   - Effort: 1 PR, 2 hours
   - Owner: Backend team

2. **Document contracts**: Add OpenAPI documentation for all API endpoints
   - Effort: 2 PRs, 3 days
   - Owner: Backend team

### Backlog
1. **Remove dead dependencies**: Clean up unused imports
   - Effort: 1 PR, 1 hour
   - Owner: Backend team

2. **Audit transitive dependencies**: Review all transitive dependencies for vulnerabilities
   - Effort: 2 days
   - Owner: Security team

---

## Appendices

### Dependency Graph Visualization
[Include graph.png or link to interactive visualization]

### Full Dependency List
[Include full list of all dependencies]

### Tool Versions
| Tool | Version | Command |
|------|---------|---------|
| pydeps | 1.15.4 | `pydeps --show-dot ./src/` |
| ruff | 0.1.6 | `ruff check --select F401 src/` |
| ... | ... | ... |
```

---

## Output

For dependency findings:

| Priority | Issue | Evidence | Recommendation |
|----------|-------|----------|----------------|
| P0 | Cycle: domain \u2194 controllers | domain/user.py:1 imports controllers/auth.py; controllers/auth.py:5 imports domain/user | Extract interface; controllers depend on domain |
| P0 | Layer violation: domain imports presentation | domain/user.py:1 imports controllers/auth.py | Invert dependency; move to application layer |
| P1 | Hub module: services/common.py imports 14 modules | services/common.py imports list... | Split into smaller focused modules |
| P2 | Duplicate date formatter | utils/dates.py:23 and helpers/datetime.py:8 both have format_iso() | Consolidate into utils/dates.py |
| P3 | Unused import | utils/legacy.py:5 imports removed_function | Remove |

Each finding: specific issue, evidence (file:line), recommendation (bounded, reversible).

**Quality > quantity. Always.**

The best dependency analysis identifies the 5-10 critical issues that, if fixed, would significantly improve the system's maintainability, testability, and deployability. Focus on high-impact findings, not on finding every possible issue.
