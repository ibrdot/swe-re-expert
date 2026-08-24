# Dead Code Confirmation — How to Verify Code Is Actually Unused

Calling code "dead" without verifying is the #1 way to embarrass yourself in code review. Reflection, runtime loading, dynamic dispatch, and aliases all hide references. Here's the rigorous process.

## The 6-step verification

Before flagging code as dead, verify through all 6:

1. **Grep** — search for symbol name across the codebase
2. **Alias check** — search for known aliases (e.g., `as foo`, `from bar import foo as baz`)
3. **Re-export check** — file may re-export the symbol; downstream callers see the re-exported name
4. **Reflection check** — `getattr(module, "foo")`, `importlib.import_module`, dynamic string usage
5. **Plugin / runtime loading** — config files, plugin discovery, entry points
6. **External use** — the symbol is part of a public API used by other packages (PyPI / npm / crates.io)

If all 6 come back empty → likely dead. Even then, mark as SUSPECTED until verified at runtime.

## Step 1: Grep

```bash
# Python
rg "functionName" --type py
rg "from .* import .*functionName" --type py
rg "\bfunctionName\b" --type py        # word boundary to avoid false matches

# Go
rg "FunctionName" --type go
rg "\.FunctionName\(" --type go         # method call

# Rust
rg "function_name" --type rust

# C/C++
rg "function_name" --type c --type cpp
rg "#include" --type c --type cpp | grep -i function_name
```

If grep returns 0 hits beyond the definition itself → likely unused. But continue checking.

## Step 2: Alias check

```python
# Direct
from foo import bar

# Aliased
from foo import bar as baz
import foo.bar as baz
```

If `bar` is aliased to `baz`, grep for `bar` won't find `baz`. Search for both:

```bash
rg "import .*\bas\b" --type py   # find "import X as Y" patterns
rg "from.*import.*functionName" --type py  # might miss "as otherName"
```

Better: parse the AST:

```python
import ast
for path in find_python_files():
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "functionName":
                    print(f"{path}: uses functionName")
                    if alias.asname:
                        print(f"  → aliased to {alias.asname}")
```

## Step 3: Re-export check

```python
# foo/__init__.py
from .submodule import functionName  # exposes functionName as foo.functionName
```

Downstream code:
```python
import foo
foo.functionName()  # uses the re-exported name
```

Grep for `functionName` would find the re-export in `__init__.py` but might miss the downstream caller if it's using the dotted form.

Detection: read `__init__.py` files and re-export lists. If the symbol is exported, it's not dead even if no one in this package calls it directly — it might be called by external packages.

## Step 4: Reflection check

```python
# Direct reflection
mod = importlib.import_module("foo.submodule")
func = getattr(mod, "functionName")
func()  # called via attribute, grep won't find it

# String-based
func_name = "function" + "Name"  # concatenated string
getattr(mod, func_name)()

# Dictionaries of callables
HANDLERS = {
    "functionName": real_function,
}
HANDLERS["functionName"]()  # called via dict lookup
```

Detection: grep for `getattr`, `importlib`, `__import__`, `getattr` with strings that might be the function name:

```bash
rg "getattr.*\".*functionName" --type py
rg "importlib.import_module" --type py
rg "__import__" --type py
```

If any of these are present, the symbol may be called dynamically — can't conclude it's dead.

## Step 5: Plugin / runtime loading

Config-driven loading:
```yaml
# config.yaml
handlers:
  - type: functionName  # this name is loaded at runtime
    args: {...}
```

Code:
```python
for handler_config in load_config()["handlers"]:
    handler = getattr(handlers_module, handler_config["type"])
    handler(**handler_config["args"])
```

Grep for `functionName` won't find the config file (depending on file types searched).

Detection: read config files. Search YAML / JSON / TOML for the symbol name.

## Step 6: External use (for public packages)

If your package is published (PyPI / npm / crates.io), other packages use your symbols. They're not in your codebase but they're real uses.

Detection: 
- For PyPI: search PyPI for packages depending on yours
- For npm: `npm-search` for dependents
- For GitHub: search code search for `import yourpackage`

When in doubt, mark the symbol as "Public API — assume external use" and don't flag as dead.

## The "test code counts" rule

Test files reference production symbols. If `functionName` is called from `tests/test_foo.py`, it's not dead — it's used by tests.

But: if the only caller is a test that's been disabled (`@pytest.mark.skip`) or in a deprecated test module, that's a weak signal. Flag as "tests are the only callers; verify the tests still run."

## The "conditional compilation" rule

Code may be conditionally compiled:

```rust
#[cfg(feature = "experimental")]
pub fn experimental_function() { ... }
```

This function is dead unless the `experimental` feature is enabled. Check `Cargo.toml` for the feature and how it's enabled in builds / CI.

```python
# Python — runtime conditional
if sys.platform == "win32":
    def windows_only_function(): ...
```

This is dead on non-Windows. Check `if sys.platform`, `if TYPE_CHECKING`, `if DEBUG`, etc.

## The "documentation code" rule

Symbol may be referenced in docstrings, doc examples, README. These aren't runtime uses, but they document the API. Removing the symbol breaks the docs.

Detection: grep docs / README / docstrings:

```bash
rg "functionName" --type md
rg "functionName" docs/
rg "functionName" README.md
```

## The "macro / generated code" rule

In C/C++ especially:
```c
#define HANDLE_CASE(name) \
    case name: handle_##name(); break;

SWITCH_CASES(HANDLE_CASE)  // macro expands to function calls
```

Grep won't find `handle_foo`, `handle_bar`, etc. — they're constructed by macro.

Detection: search for macros that might generate the function name:
```bash
rg "#define.*handle_" --type c --type cpp
```

Same for codegen — sometimes functions are called from generated code (gRPC stubs, protobuf, ORM mappings). Look in `*.gen.py`, `*_pb2.py`, generated directories.

## The "SUSPECTED" marker

When you've done all 6 checks and the symbol has no caller, mark as SUSPECTED dead:

```
| P3 | Dead code candidate: `functionName` in utils/old.py:42 | SUSPECTED — no static caller found, but cannot exclude dynamic usage | Comment out for one release; remove if no breakage |
```

The recommendation is conservative: comment out first, ship, observe. If no breakage in one release cycle, remove for real.

## The "clean-up PR" rule

Don't bundle dead-code removal with feature work. Split it:

1. PR for the feature (no dead code)
2. PR for dead code removal (just dead code)

Bundling makes review harder and creates regression risk if the dead code wasn't actually dead.

## The "monorepo wide check" rule

In a monorepo:
- Module A in package `foo` may be called by module B in package `bar`
- Grep must span the whole monorepo, not just the package

Detection: run grep from monorepo root, not from package root.

## The "versioned API" rule

If your package exposes public APIs (e.g., `package.v1.User`), removing them is a breaking change for downstream users. Even if no caller in your repo:

- Check semver policy
- Mark as deprecated first (one release)
- Remove in next major version

Not a "dead code" finding; a "deprecation policy" finding.

## Output

For dead code findings:

| Priority | Symbol | Location | Confidence | Recommendation |
|----------|--------|----------|-------------|----------------|
| P3 | `old_helper` | utils/legacy.py:42 | VERIFIED dead — 0 grep hits, no aliases, no reflection in codebase, not exported | Remove in cleanup PR |
| P3 | `experimental_fn` | utils/exp.py:12 | SUSPECTED — no static callers, but module uses `getattr` with config-driven names; cannot exclude dynamic usage | Comment out, monitor one release cycle, then remove if no breakage |
| P3 | `legacy_handler` | handlers/old.py:5 | LIKELY dead — only caller is `@pytest.mark.skip`-ed test | Verify the skipped test is intentionally disabled; if so, remove both |

Each finding: location, confidence level (the 6-step verification result), conservative recommendation.
