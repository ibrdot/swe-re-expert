# Vulnerability Hunting — Where Bugs Live, by Category

A mental model for finding security-relevant bugs in both source code (SWE) and disassembly (RE). Organized by bug class, with the patterns to look for in each.

## Memory safety (C/C++ and asm)

### Stack buffer overflows

**Source pattern:**
```c
char buf[16];
gets(buf);               // classic — no bounds
strcpy(buf, src);        // no bounds
sprintf(buf, "%s", src);  // no bounds
scanf("%s", buf);        // no bounds
```

**Disasm pattern:**
- `sub rsp, 0xNN` (small stack reservation) followed by `call gets@plt` / `call strcpy@plt`
- `lea rdi, [rbp-0xNN]; call strcpy@plt`
- The buffer is at `[rbp-N]`, the source is unbounded

**Severity:** P0 — usually RCE on non-PIE/non-NX, still DoS / info leak on hardened binaries.

### Heap overflows

**Source pattern:**
```c
char *buf = malloc(16);
strcpy(buf, src);  // src > 16 bytes
memcpy(buf, src, src_len);  // src_len > 16
```

**Disasm pattern:** `call malloc@plt` with small size arg, then `call memcpy@plt` with larger size arg derived from input.

**Severity:** P0 — heap metadata corruption, often RCE.

### Format string bugs

**Source pattern:**
```c
printf(user_input);          // no format string literal
fprintf(stderr, user_msg);   // same
syslog(LOG_INFO, user_msg);  // same
```

**Disasm pattern:**
- `lea rdi, [rbp-N]` (user input on stack)
- `xor eax, eax` (zero varargs indicator)
- `call printf@plt`

If the format string is hardcoded (`lea rdi, [rip+0x...]` — in `.rodata`), it's safe.

**Severity:** P0 — info leak (stack/memory dump) → often RCE via `%n` writes.

### Use-after-free / double-free

Hard to spot statically. Look for:
- `free(ptr); ...; <deref ptr>` without intervening `ptr = NULL` or reassignment
- Two `free(ptr)` calls in different branches without coordination
- C++: `delete obj; ...; obj->method()` — destructor doesn't NULL the pointer

**Severity:** P0 — usually RCE via heap metadata manipulation.

### Integer overflow → buffer overflow

**Source pattern:**
```c
size_t n = a * b;            // a, b from input; overflow wraps
char *buf = malloc(n);        // allocates 0 or small
memcpy(buf, src, real_size);  // overflows
```

**Disasm pattern:**
- `mov eax, [user_input]; imul eax, [user_input+4]; mov [rbp-N], eax` (multiplication, no overflow check)
- `mov rdi, [rbp-N]; call malloc@plt`
- `mov rdx, [user_input]; call memcpy@plt` (uses untrusted size)

**Severity:** P0 — classic CVE pattern.

## Injection

### SQL injection

**Source pattern:**
```python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # f-string concat
cursor.execute("SELECT ... WHERE id = " + user_id)             # + concat
cursor.execute("SELECT ... WHERE id = %s" % user_id)           # % format
```

All of these are SQLi. The fix is parameterized queries:
```python
cursor.execute("SELECT ... WHERE id = %s", (user_id,))  # safe
```

**Detection:** grep for `execute(`, `query(`, `exec(`, then check if the SQL is concatenated.

**Severity:** P0 — usually RCE on Postgres (COPY TO PROGRAM), often auth bypass.

### Command injection

**Source pattern:**
```python
os.system(f"curl {url}")                              # RCE
subprocess.run(f"curl {url}", shell=True)              # RCE
subprocess.run(["curl", url])                          # SAFE — list form
subprocess.run("curl " + url, shell=True)             # RCE
```

**Go pattern:**
```go
exec.Command("sh", "-c", "curl " + url)               // RCE
exec.Command("curl", url)                              // SAFE
```

**Detection:** grep for `shell=True`, `os.system`, `exec.Command("sh", "-c", ...)` then trace if any arg is user-controlled.

**Severity:** P0 — direct RCE.

### Path traversal

**Source pattern:**
```python
open(f"/data/{user_filename}")                        # user_filename = "../../etc/passwd"
open(os.path.join("/data", user_filename))             # same — join doesn't sanitize
```

**Safe pattern:**
```python
base = Path("/data").resolve()
target = (base / user_filename).resolve()
if not str(target).startswith(str(base)):
    raise ValueError("path traversal")
```

**Severity:** P0 — arbitrary file read/write, often auth bypass.

### SSRF

**Source pattern:** any HTTP client that takes user-controlled URL.

```python
requests.get(user_url)  # user_url = "http://169.254.169.254/latest/meta-data/"
```

**Detection:** grep for `requests.get`, `http.Get`, `fetch(`, then check if URL is user-controlled without allowlist.

**Severity:** P0/P1 — cloud metadata leak, internal service access.

## Authentication / authorization

### Missing auth check

**Source pattern:** route handlers without auth decorator / middleware.

```python
@app.route("/admin/users")
def list_users():  # no @auth_required
    ...
```

**Detection:** list all routes, identify the ones that touch privileged data, check for auth wrapper. Cross-reference with the framework's standard pattern.

**Severity:** P0 — direct auth bypass.

### IDOR (insecure direct object reference)

**Source pattern:**
```python
@app.route("/api/orders/<int:order_id>")
@auth_required
def get_order(order_id):
    order = Order.query.get(order_id)  # no check that this order belongs to user
    return order.to_dict()
```

**Detection:** trace every object lookup by ID; verify ownership check.

**Severity:** P0 — direct data leak.

### JWT issues

- `alg: none` accepted (decoder should reject)
- HS256 with weak / shared secret
- RS256 with public key as HMAC secret (algorithm confusion)
- `kid` header injection (path traversal in key lookup)
- Long expiry, no rotation
- Storing sessions in JWT (stateful data in stateless token)

**Detection:** grep for `jwt`, `verify`, `decode`, then check verification options.

**Severity:** P0 — auth bypass.

## Crypto misuse

### Weak algorithms

- MD5, SHA1 for security (collision attacks practical)
- DES, 3DES (small block, vulnerable to sweet32)
- RC4 (biased keystream)
- ECB mode (deterministic — leaks patterns)
- Custom / homebrew crypto (always broken)

**Detection:** grep for `md5(`, `sha1(`, `DES`, `RC4`, `ECB`, `NewCipher` (custom), then check context.

**Severity:** P0/P1 — depends on use.

### Predictable randomness

- `random.randint()` for tokens, keys, IDs
- `math.random()` in JS for the same
- Time-seeded PRNG (predictable)

**Detection:** grep for `random.`, `Math.random`, then check if used for security.

**Fix:** `secrets.token_bytes(32)`, `crypto.randomBytes(32)`.

**Severity:** P0 — token prediction.

### Hardcoded secrets

- API keys, DB passwords, JWT secrets in source
- Private keys in repos
- AWS keys in env files

**Detection:** grep for `password=`, `secret=`, `api_key=`, `BEGIN PRIVATE KEY`, then verify they're not placeholders.

**Severity:** P0 — direct credential exposure.

## Race conditions

### TOCTOU (time-of-check to time-of-use)

**Source pattern:**
```python
if os.path.exists(filename):  # check
    with open(filename) as f:  # use — file could be replaced
        data = f.read()
```

**Fix:** open with O_NOFOLLOW, use the fd, not the path.

**Severity:** P0/P1 — privilege escalation.

### Shared mutable state without sync

**Go:**
```go
var cache = map[string]string{}  // shared, no mutex
func get(key string) string {
    return cache[key]  // race — concurrent map read/write panics
}
```

**Detection:** grep for global `var` declarations of mutable types, then check if access is synchronized.

**Severity:** P1 — intermittent bugs, hard to repro.

### Async race in cancellation

```python
async def fetch_and_save(url):
    data = await fetch(url)
    save(data)  # if cancelled here, partial state
```

**Detection:** look for async code without try/finally cleanup, or `asyncio.gather` without `return_exceptions=True`.

**Severity:** P1 — partial state on cancellation.

## Logic bugs

### Off-by-one

- `for i in range(0, N+1)` — includes N (off by one)
- `for i = 0; i <= N; i++` — includes N
- `array[length]` — out of bounds (last valid is length-1)
- `if (x < 10)` when boundary is `< 11`

**Detection:** manual review of loop bounds and array indices.

**Severity:** P1 — silent wrong behavior, memory safety if it leads to OOB.

### Trusting client-side validation

```python
@app.route("/api/transfer", methods=["POST"])
def transfer():
    amount = request.json["amount"]  # client validates >= 0
    # server doesn't re-check
    transfer(amount)  # negative amount = withdraw to attacker
```

**Detection:** trace user input — does it pass through server-side validation, or is the client's value trusted?

**Severity:** P0 — direct fraud.

### Auth check on wrong method

```python
@app.route("/api/users/<id>", methods=["GET", "DELETE"])
@auth_required
def get_or_delete(id):
    user = current_user()
    if user.id != id:
        # but: admin should be able to DELETE, not GET
        return 403
    ...
```

**Detection:** check that the auth logic accounts for the HTTP method, not just the route.

**Severity:** P0 — privilege escalation.

## Where to spend your time

In a typical code review (1-2 hours):

1. **First 30 minutes**: grep for the high-signal patterns above (injection, hardcoded secrets, weak crypto, missing auth). These are fast wins.
2. **Next 30 minutes**: trace one critical flow end-to-end, looking for logic bugs and trust-boundary violations.
3. **Next 20 minutes**: look at error handling — where errors are swallowed, where they propagate, where they leak info.
4. **Last 10 minutes**: write up findings, prioritized P0/P1/P2.

Don't try to read every line. Pattern-matching on the high-signal bugs is 80% of the value.
