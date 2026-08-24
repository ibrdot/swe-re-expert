# Python Anti-Patterns

The high-signal Python-specific patterns that catch real bugs. Pattern-matched from `ruff`, `pylint`, `bandit`, `vulture`, or hand review.

## P0 — Security

### `eval` / `exec` on user input

```python
# P0 — RCE
result = eval(user_input)
exec(request.json["payload"])

# Fix: use ast.literal_eval for literal-only, or a real parser
from ast import literal_eval
result = literal_eval(user_input)  # only allows literals (strings, numbers, lists, dicts of literals)
```

### `pickle.loads` / `yaml.load` (unsafe loader)

```python
# P0 — RCE
import pickle
obj = pickle.loads(user_bytes)

import yaml
obj = yaml.load(user_yaml)  # default is unsafe

# Fix
import yaml
obj = yaml.safe_load(user_yaml)
# For pickle: don't accept pickles from users. Use JSON.
```

### `subprocess` with `shell=True`

```python
# P0 — command injection
subprocess.run(f"curl {url}", shell=True)

# Fix: shell=False, args as list
subprocess.run(["curl", url])
```

### SQL string concatenation

```python
# P0 — SQLi
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT ... WHERE id = " + user_id)

# Fix: parameterized
cursor.execute("SELECT ... WHERE id = %s", (user_id,))
```

### `os.system` with user input

```python
# P0 — command injection
os.system(f"echo {user_message}")

# Fix: subprocess with shell=False
subprocess.run(["echo", user_message])
```

### `random` for security

```python
# P0 — predictable token
import random
token = "".join(random.choice("abcdef0123456789") for _ in range(32))

# Fix: secrets module
import secrets
token = secrets.token_hex(16)
```

### Weak crypto

```python
# P0 — collision attacks practical
import hashlib
h = hashlib.md5(password.encode()).hexdigest()

# Fix
import hashlib, bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

### Path traversal

```python
# P0 — arbitrary file read
with open(f"/data/{user_filename}") as f:
    data = f.read()

# Fix: explicit base, normalize, check
from pathlib import Path
base = Path("/data").resolve()
target = (base / user_filename).resolve()
if not str(target).startswith(str(base) + "/"):
    raise ValueError("path traversal attempt")
```

## P1 — Correctness / maintainability

### Mutable default args

```python
# P1 — state leaks across calls
def add_user(name, users=[]):
    users.append(name)
    return users

# Fix
def add_user(name, users=None):
    if users is None:
        users = []
    users.append(name)
    return users
```

### Bare `except`

```python
# P1 — swallows everything, including SystemExit / KeyboardInterrupt
try:
    do_something()
except:
    pass

# Fix
try:
    do_something()
except SpecificException as e:
    logger.warning("...")
```

### `assert` for runtime checks

```python
# P1 — stripped with python -O
assert user.is_admin, "not authorized"

# Fix
if not user.is_admin:
    raise PermissionError("not authorized")
```

### Class-level mutable state

```python
# P1 — shared across instances, often wrong
class User:
    cache = {}  # shared by all User instances
    
# Fix: instance-level
class User:
    def __init__(self):
        self.cache = {}
```

### `is` for value comparison

```python
# P1 — works for None, breaks for strings/ints due to interning
if x is "hello":  # might be False even when x == "hello"
    
# Fix
if x == "hello":
# Or for None specifically (the only correct use of `is`):
if x is None:
```

### Modifying while iterating

```python
# P1 — RuntimeError / wrong behavior
for item in items:
    if item.invalid:
        items.remove(item)

# Fix: build new list
items = [item for item in items if not item.invalid]
# Or iterate over a copy
for item in list(items):
    if item.invalid:
        items.remove(item)
```

### `time.sleep` for synchronization

```python
# P1 — race condition; sleep doesn't sync
def wait_for_resource():
    time.sleep(1)
    return get_resource()

# Fix: event / condition / proper sync
import threading
event = threading.Event()
resource_producer.notify_when_ready(event)
event.wait()
return get_resource()
```

### Thread-unsafe global state

```python
# P1 — race condition
cache = {}
def get(key):
    if key not in cache:
        cache[key] = expensive_compute(key)
    return cache[key]

# Fix: lock, or use a thread-safe structure
from threading import Lock
cache_lock = Lock()
cache = {}
def get(key):
    with cache_lock:
        if key not in cache:
            cache[key] = expensive_compute(key)
        return cache[key]
```

### Async: blocking I/O in async function

```python
# P1 — blocks the event loop
async def fetch_data():
    time.sleep(5)  # blocks!
    return data

# Fix: use async sleep, or offload to thread
async def fetch_data():
    await asyncio.sleep(5)
    return data

# Or:
async def fetch_data():
    return await asyncio.to_thread(blocking_call, 5)
```

### `requests.get` in async (sync HTTP in async)

```python
# P1 — blocks event loop
async def fetch(url):
    return requests.get(url).json()  # sync call

# Fix: use aiohttp or httpx
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Missing `await` on coroutine

```python
# P1 — coroutine object created but not awaited; function silently returns the coroutine
async def process():
    result = some_async_function()  # forgot await!
    return result

# Fix
async def process():
    result = await some_async_function()
    return result
```

## P2 — Maintainability

### God class / long module

```python
# P2 — single file with 10+ classes and 500+ LOC
class User: ...
class Order: ...
class Payment: ...
class Email: ...
# (in one file)

# Fix: split by domain — user.py, order.py, payment.py, email.py
```

### God function

```python
# P2 — single function 200+ LOC, multiple responsibilities
def process_order(order):
    # validate
    # ...
    # compute pricing
    # ...
    # apply discounts
    # ...
    # persist
    # ...
    # send email
    # ...

# Fix: extract into smaller functions
def process_order(order):
    validate_order(order)
    pricing = compute_pricing(order)
    apply_discounts(order, pricing)
    save_order(order)
    send_confirmation(order)
```

### Magic numbers

```python
# P2 — what does 86400 mean?
timeout = 86400

# Fix: named constant
SECONDS_PER_DAY = 86400
timeout = SECONDS_PER_DAY
```

### Stringly-typed modes

```python
# P2 — typo at call site = silent wrong behavior
def process(data, mode="fast"):
    if mode == "fast": ...
    elif mode == "slow": ...
    elif mode == "safe": ...

# Fix: enum or keyword-only args
from enum import Enum
class Mode(Enum):
    FAST = "fast"
    SLOW = "slow"
    SAFE = "safe"

def process(data, mode: Mode = Mode.FAST):
    ...
```

### Inconsistent error handling

```python
# P2 — sometimes raises, sometimes returns None, sometimes returns False
def find_user(id):
    if id < 0: return None
    if id > MAX: return False
    if not exists(id): raise UserNotFoundError
    return User

# Fix: pick one pattern (raise or sentinel), document it
def find_user(id):
    """Raises UserNotFoundError if not found."""
    if not exists(id):
        raise UserNotFoundError(id)
    return User
```

### Reimplemented stdlib

```python
# P2 — buggy custom version
def parse_iso_date(s):
    parts = s.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))

# Fix: use stdlib
from datetime import date
d = date.fromisoformat(s)
```

### `print` for logging

```python
# P2 — no log levels, no structured fields, can't redirect
print("User logged in", user_id)

# Fix: use logging
import logging
logger = logging.getLogger(__name__)
logger.info("User logged in", extra={"user_id": user_id})
```

### Tests that don't assert

```python
# P2 — coverage but no behavior
def test_login():
    login("a@b.com", "password")  # no assert!

# Fix
def test_login():
    result = login("a@b.com", "password")
    assert result.success
```

## P3 — Style

- Importing inside functions when not necessary for circular dep fix
- Wildcard imports (`from foo import *`)
- Long parameter lists (5+ args)
- Inconsistent naming (`userId`, `user_id`, `user_name` in same codebase)
- Type hints missing on public APIs
- Docstrings missing on public APIs

These are usually P3 because linters catch them automatically (`ruff`, `black`, `mypy`). Don't review manually — let tools handle them.

## The "modern Python" checklist

For modernization recommendations (each needs a concrete defect to justify):

- [ ] Type hints on public APIs
- [ ] `pydantic v2` for runtime validation (if v1 in use)
- [ ] `ruff` for linting (replaces flake8 + black + isort)
- [ ] `uv` for package management (replaces pip + venv)
- [ ] `dataclasses` for value objects
- [ ] `pathlib.Path` instead of `os.path` strings
- [ ] `f-strings` instead of `.format()` or `%` (readability)
- [ ] `typing.Protocol` for duck typing (replaces ABCs in some cases)
- [ ] `functools.cached_property` for memoization
- [ ] `__slots__` for memory-tight classes
- [ ] `asyncio.TaskGroup` (3.11+) for structured concurrency

Each is justified only when there's a present defect to fix, not just "newer is better".

## Tool reference

```bash
# Linting — fast and configurable
ruff check .                          # lint
ruff format .                         # format

# Type checking
mypy .                                # basic
basedpyright .                        # stricter alternative

# Security scanning
bandit -r .                           # Python security scanner

# Dead code
vulture .                             # unused imports, vars, functions

# Complexity
radon cc .                            # cyclomatic complexity
radon mi .                            # maintainability index

# Test coverage
pytest --cov=. --cov-report=html

# Dependency audit
pip-audit                             # CVE check on deps
```

Use these in CI. They catch most P2/P3 findings automatically.
