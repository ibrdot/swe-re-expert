# Security Review Thinking

The mental model for security review. Different from general code review — security issues have specific patterns, and missing them has higher cost.

## The 6 categories of security review

1. **Input validation** — every user input is hostile until proven otherwise
2. **Authentication** — who is the caller? how do we know?
3. **Authorization** — what's the caller allowed to do?
4. **Cryptography** — are we using crypto correctly?
5. **Session / state** — can state be tampered with?
6. **Logging / error handling** — what info leaks via errors?

Review each in turn. Most security findings come from the first three.

## The "trust boundary" model

Draw the trust boundaries:
- Untrusted (internet, raw user input, file uploads)
- Semi-trusted (auth'd users, internal services)
- Trusted (admin, internal services with high privilege)

Every data flow that crosses a boundary needs:
- **Validation** at the boundary
- **Encoding / escaping** at the output (defense in depth)
- **Authorization check** before any privileged action

Bugs happen when these are missing or weak. Review by walking every flow across a boundary.

## Input validation — the rule

> Every input from outside the trust boundary must be validated, every time, before use.

Validate at the boundary (entry point), not scattered through the code. Once data is past the boundary, it's "trusted" — but only if validation happened.

Common patterns:
- Length limits (prevent DoS, prevent log injection)
- Type checks (integer vs string vs UUID)
- Format / regex (email, URL, phone)
- Allowlist (whitelist of allowed values — better than denylist)
- Range (0 ≤ x ≤ 100, not just "is a number")

Validate explicitly:
```python
# BAD — trusts the input
@app.route("/users/<id>")
def get_user(id):
    user = db.query(f"SELECT * FROM users WHERE id = {id}")  # SQLi

# GOOD — validates and parameterizes
@app.route("/users/<int:id>")
def get_user(id: int):
    user = db.query("SELECT * FROM users WHERE id = %s", (id,))
```

## The "10 dangerous sinks" pattern

Audit by looking at calls to dangerous APIs, then tracing back:

| Sink | Bug class |
|------|-----------|
| `os.system`, `subprocess(shell=True)` | Command injection |
| `eval`, `exec` | Code injection |
| `pickle.loads`, `yaml.load(Loader=yaml.Loader)` | Insecure deserialization |
| `cursor.execute(query % args)` or `query + args` | SQL injection |
| `open(user_path)` | Path traversal |
| `requests.get(user_url)` | SSRF |
| `redirect(user_url)` | Open redirect |
| `render_template_string(user_input)` | SSTI (server-side template injection) |
| `XMLParser(resolve_entities=True)` | XXE |
| `subprocess.Popen` with `preexec_fn` | Code exec via preexec |

Grep for these in the codebase. Each hit is a candidate finding. Verify by tracing the input source — if it's user-controlled and unvalidated, it's a real finding.

## The "find the user input" technique

When reviewing a function:

1. **What are the inputs?** (args, request body, env vars, file contents)
2. **Which of those came from the user?** (anything that crossed a trust boundary)
3. **Where do those inputs flow?** (every variable assigned from them)
4. **Do any of those flows reach a dangerous sink?** (the 10 above)

If yes → finding. If no → not a security issue (just a normal code review finding).

## Authentication review

### Password storage

- Never store plaintext
- Never store MD5 / SHA1 of password
- Use bcrypt / scrypt / argon2id (current best practice)
- Use a fresh salt per user (modern algorithms do this automatically)
- Set cost parameter high enough to be slow (~250ms per hash)

Detection: grep for `password`, `hash`, then check the algorithm.

### Session management

- Session IDs: at least 128 bits of entropy, generated with cryptographically secure RNG
- Session storage: server-side (DB / Redis) — don't trust the client
- Session expiry: idle timeout + absolute timeout
- Session invalidation on logout
- Session rotation on privilege change (login → admin)

JWT issues (common):
- `alg: none` accepted
- HS256 with shared secret
- Long expiry, no rotation
- Stateful data in token
- `kid` header injection

### Multi-factor auth

- TOTP secret should be unique per user
- TOTP should not be the only factor for high-privilege operations
- Recovery codes should be high-entropy and one-time-use

## Authorization review

### IDOR (Insecure Direct Object Reference)

Every object lookup by ID must verify ownership:

```python
# BAD
@app.route("/orders/<int:id>")
@login_required
def get_order(id):
    return Order.query.get(id)  # no ownership check

# GOOD
@app.route("/orders/<int:id>")
@login_required
def get_order(id):
    order = Order.query.get(id)
    if order.user_id != current_user.id:
        abort(404)  # 404 not 403 — don't leak existence
    return order
```

Detection: for every route that takes an ID, check for an ownership assertion.

### Privilege escalation

- Vertical: user → admin (check role/permissions)
- Horizontal: user A → user B (check ownership)

Both need checks at the action, not just the route. Example: an admin route that lets you list users — does it filter by your org / tenant?

### Force browsing

- Can unauthenticated users reach `/admin/...`?
- Are sensitive endpoints behind auth middleware?
- Are there hidden parameters that bypass checks?

Detection: list all routes, identify the ones touching privileged data, verify auth on each.

## Cryptography review

### Algorithm choice

Reject:
- MD5, SHA1 for security (collisions practical)
- DES, 3DES (small block, sweet32)
- RC4 (biased)
- ECB mode (deterministic — leaks patterns)
- Custom / homebrew crypto

Accept:
- SHA256 / SHA3 for hashing
- AES-GCM / ChaCha20-Poly1305 for symmetric encryption (AEAD)
- RSA-2048+ / Ed25519 / ECDSA-P256+ for asymmetric
- bcrypt / scrypt / argon2id for password hashing

Detection: grep for `md5`, `sha1`, `DES`, `RC4`, `ECB`, `NewCipher` (custom). Check context.

### Randomness

Reject:
- `random.randint()` for security
- `time.time()`-seeded RNG
- Predictable IDs (incrementing counter, UUIDv1 with MAC)

Accept:
- `secrets.token_bytes(32)` (Python)
- `crypto.randomBytes(32)` (Node)
- `crypto/rand.Read()` (Go)
- `OsRng` / `thread_rng()` (Rust)

Detection: grep for `random.`, then check if used for security.

### Key management

- Keys in source: P0
- Keys in env files committed: P0
- Keys in plaintext config: P0 (use a secrets manager — Vault, AWS Secrets Manager, etc.)
- Keys rotated regularly: check policy

Detection: grep for `password=`, `secret=`, `api_key=`, `BEGIN PRIVATE KEY`, then verify it's not a placeholder.

### TLS / network

- Outbound HTTPS with cert verification (not `verify=False`)
- HSTS header on inbound HTTPS
- TLS 1.2+ minimum
- Certificate pinning for critical clients (mobile apps, payment)

## Session / state review

### Cookies

- `HttpOnly` (prevent JS access) — almost always yes
- `Secure` (HTTPS only) — almost always yes
- `SameSite=Strict` or `Lax` (CSRF defense) — almost always yes
- Cookie expiry reasonable

Detection: read the cookie setup code.

### CSRF

For state-changing requests (POST/PUT/DELETE):
- CSRF token in form, validated server-side
- `SameSite` cookie attribute
- Or: `Origin` / `Referer` header check (weaker)

Detection: identify every state-changing route, check the CSRF defense.

### Open redirect

```python
# BAD
return redirect(request.args.get("next"))

# GOOD
next_url = request.args.get("next", "")
if not is_safe_url(next_url):  # checks domain, scheme, etc.
    return redirect("/")
return redirect(next_url)
```

Detection: grep for `redirect(`, check if URL is user-controlled and validated.

## Logging / error handling

### Information leak via errors

- Stack traces returned to client (P0 — leaks file paths, library versions)
- Detailed error messages ("incorrect password for user 'admin'") — username enumeration
- SQL errors returned verbatim — schema leak

Detection: trace error responses. Should be generic to the client, detailed only to the server log.

### Sensitive data in logs

- Passwords in logs (P0)
- Tokens / API keys in logs (P0)
- Credit card numbers in logs (P0 / PCI violation)
- PII in logs (depends on jurisdiction — GDPR, CCPA)

Detection: grep log statements for `password`, `token`, `secret`, `key`, `ssn`, `card`.

### Audit logs

- Failed login attempts logged
- Privileged actions logged (who did what, when)
- Logs tamper-resistant (append-only, remote-sent)

Detection: identify privileged operations, verify logging.

## The OWASP Top 10 cross-reference

For each finding, map to OWASP category:

| OWASP 2021 category | Common patterns |
|---------------------|-------------------|
| A01: Broken Access Control | IDOR, missing auth, force browsing |
| A02: Cryptographic Failures | Weak algo, hardcoded keys, bad RNG |
| A03: Injection | SQLi, commandi, LDAPi, XPathi |
| A04: Insecure Design | Missing rate limit, missing audit log |
| A05: Security Misconfiguration | Default creds, verbose errors, debug mode |
| A06: Vulnerable Components | Outdated deps with CVEs |
| A07: Auth Failures | Weak password policy, session fixation |
| A08: Data Integrity Failures | Insecure deserialization, unsigned updates |
| A09: Logging Failures | Missing logs for security events |
| A10: SSRF | User-controlled URLs without allowlist |

Each finding should be OWASP-mapped in the report so the team can prioritize based on risk class.

## Output

The security section of the audit report:

| Priority | OWASP | Issue | Evidence | Fix |
|----------|-------|-------|----------|-----|
| P0 | A03 | SQLi at user_search | file.py:23 | parameterized query |
| P0 | A02 | MD5 password hash | file.py:45 | use bcrypt |
| P1 | A05 | Stack trace returned | file.py:67 | generic error to client |
| P1 | A01 | IDOR on /orders/<id> | file.py:90 | ownership check |

Each finding: severity, OWASP category (for prioritization), specific issue, evidence (line), fix (specific).
