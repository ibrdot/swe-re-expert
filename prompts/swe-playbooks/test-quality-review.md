# Test Quality Review

Bad tests are worse than no tests — they give false confidence, break on refactor, and erode trust in the suite. Review test quality as carefully as you review production code.

## The 6 attributes of good tests

1. **Correct** — tests what the author intended, not what they accidentally wrote
2. **Readable** — failure message tells you what broke without reading the test
3. **Fast** — fast enough to run frequently
4. **Isolated** — failure points to one cause, not many
5. **Relevant** — tests behavior that matters, not implementation details
6. **Durable** — survives refactors without breaking

Tests that fail any of these are findings.

## The "behavior vs implementation" rule

> Tests should assert what the code does, not how it does it.

Good:
```python
def test_user_can_login_with_valid_credentials():
    user = create_user(email="a@b.com", password="correct")
    result = login(email="a@b.com", password="correct")
    assert result.success
    assert result.user_id == user.id
```

Bad:
```python
def test_login_calls_database_with_email():
    with mock.patch('app.db.query') as mock_query:
        login("a@b.com", "correct")
        mock_query.assert_called_with("SELECT * FROM users WHERE email = 'a@b.com'")
```

The second test asserts the implementation. If you ever refactor the query (e.g., to use a different ORM, to add caching, to change table structure), the test breaks — even though the behavior (login) still works.

Rule: tests that break on every refactor are testing implementation, not behavior. They should be rewritten.

## The "mock when needed, not when convenient" rule

Mocks have a cost: they decouple the test from the real implementation, which means the test no longer verifies that the real implementation works together.

```python
# BAD — over-mocked
def test_send_email():
    with mock.patch('smtplib.SMTP') as smtp, \
         mock.patch('app.config.SMTP_HOST', 'localhost'):
        send_email("user@example.com", "subject", "body")
        smtp.return_value.sendmail.assert_called_once()

# GOOD — use a real SMTP test server (e.g., aiosmtpd)
def test_send_email():
    with SMTPTestServer() as server:
        send_email("user@example.com", "subject", "body", host=server.host, port=server.port)
        assert len(server.messages) == 1
        assert server.messages[0]["To"] == "user@example.com"
```

Rule: prefer real components (in-memory DB, fake SMTP, containerized services) over mocks. Use mocks only for:
- External paid APIs (rate limits, cost)
- Network failures / timeouts (inject via dependency)
- Slow operations in fast tests

## The "name the behavior, not the function" rule

Test name patterns:

❌ `test_login` — what about it?
❌ `test_login_1`, `test_login_2` — what's the difference?
✅ `test_login_succeeds_with_valid_credentials`
✅ `test_login_fails_with_unknown_email`
✅ `test_login_fails_after_5_failed_attempts`
✅ `test_login_rate_limited_after_10_attempts_per_minute`

The test name should describe the behavior under test. When it fails, the failure message tells you what broke without reading the test body.

## The "AAA pattern" rule

Tests should follow Arrange-Act-Assert:

```python
def test_rate_limit_kicks_in_after_threshold():
    # Arrange
    user = create_user()
    client = TestClient(app)
    
    # Act
    for _ in range(10):
        response = client.post("/api/login", json={...})
    response = client.post("/api/login", json={...})  # 11th attempt
    
    # Assert
    assert response.status_code == 429
```

Tests that mix Arrange and Act are harder to read. Tests that have multiple Acts are testing multiple things — split them.

## The "edge cases" checklist

For every function under test, check coverage of:

- [ ] Happy path (valid input, expected output)
- [ ] Empty input (`""`, `[]`, `{}`)
- [ ] Null input (where applicable — Python has None, not null)
- [ ] Boundary values (0, 1, -1, MAX_INT, MIN_INT)
- [ ] Max size (1MB string, 1M items in list)
- [ ] Unicode (emoji, RTL, combining characters, BOM)
- [ ] Concurrent access (where applicable)
- [ ] Error / failure paths (network down, invalid input, permission denied)
- [ ] Idempotency (called twice, gives same result?)

Most tests cover only the happy path. The bugs live in the edge cases.

## The "test isolation" rule

Each test should:
- Set up its own state (not depend on prior test runs)
- Clean up after itself (don't pollute global state)
- Not depend on test order

```python
# BAD — depends on test_db being clean
def test_create_user():
    create_user("a@b.com")
    assert User.query.count() == 1  # only true if test_db is empty

# GOOD — independent
def test_create_user(clean_db):
    create_user("a@b.com")
    assert User.query.filter_by(email="a@b.com").first() is not None
```

Detection: tests fail when run alone, or fail when run in different orders → not isolated.

## The "no shared mutable fixtures" rule

```python
# BAD — fixture mutates, breaks subsequent tests
@pytest.fixture
def user():
    return create_user()

def test_a(user):
    user.deactivate()

def test_b(user):  # user is already deactivated!
    user.do_something()  # unexpected behavior
```

Fix: use function-scoped fixtures, ensure each test gets a fresh state.

## The "test should be readable" rule

```python
# BAD — clever but unreadable
def test_x():
    a = [1, 2, 3]
    b = list(map(lambda x: x*2, a))
    assert reduce(lambda x, y: x+y, b) == 12

# GOOD — explicit
def test_doubling_list_and_summing():
    numbers = [1, 2, 3]
    doubled = [n * 2 for n in numbers]
    total = sum(doubled)
    assert total == 12
```

Tests are documentation. If they're hard to read, they don't document.

## The "no logic in tests" rule

```python
# BAD — logic in the test, may have bugs itself
def test_filter_active_users():
    users = [User(active=True), User(active=False), User(active=True)]
    active = [u for u in users if u.active]  # this is the code under test, inlined!
    assert len(active) == 2

# BETTER — call the actual function under test
def test_filter_active_users():
    users = [User(active=True), User(active=False), User(active=True)]
    active = filter_active(users)
    assert len(active) == 2
    assert all(u.active for u in active)
```

If the test reimplements the logic, it tests nothing — both implementations can be wrong in the same way.

## The "test data" rule

Test data should be:
- **Realistic** (not `User(name="asdf", email="qwer")` — use real-looking data)
- **Minimal** (only the fields the test needs; don't build a full user when you need just an email)
- **Deterministic** (don't use `random` for test data — or seed it)
- **Anonymized** (no real customer data — use Faker for fake data)

## The "fast tests" rule

Tests should run in <1 second each. The whole suite should run in <30 seconds.

If they're slower:
- Network calls in tests → mock / use fakes
- Real DB → use in-memory SQLite or testcontainers
- Heavy setup → reuse fixtures, but verify isolation

Slow tests aren't run. Tests that aren't run don't catch regressions. They're dead code.

## The "property-based testing" rule

For functions with complex invariants, use property-based testing (Hypothesis, QuickCheck, jqwik):

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_is_idempotent(lst):
    sorted_once = sorted(lst)
    sorted_twice = sorted(sorted_once)
    assert sorted_once == sorted_twice  # sort is idempotent

@given(st.lists(st.integers()))
def test_sort_preserves_length(lst):
    assert len(sorted(lst)) == len(lst)
```

Property-based tests catch edge cases humans forget. For math / parsing / data transformation, they're worth the setup cost.

## The "test the bug, not just the fix" rule

When fixing a bug, write a test that would have caught it. The test should:
- Fail before the fix
- Pass after the fix
- Stay in the suite forever (regression test)

```python
def test_login_with_unicode_password():
    # Bug: unicode passwords were silently truncated at the DB layer
    password = "Pässwörd"
    user = create_user(password=password)
    assert login(email=user.email, password=password).success
```

Without this test, the bug may regress.

## The "coverage is a smell, not a goal" rule

100% coverage doesn't mean 100% tested. Coverage tells you what was executed, not what was asserted.

```python
def test_something():
    do_something()
    # No assertions — coverage 100%, but tests nothing
```

Coverage is a starting point: look at uncovered lines, decide if they need tests. If yes, add a test that asserts the behavior. If no, the code is probably dead.

Don't chase coverage metrics. Chase behavior coverage.

## The "failure message" rule

```python
# BAD — failure message is "AssertionError"
assert result == expected

# GOOD — failure message is informative
assert result == expected, f"Expected {expected}, got {result}"

# BEST — using testing framework's assertion
self.assertEqual(result, expected)  # pytest gives a useful diff
```

When the test fails at 3am, the message should tell you what broke without reading the test.

## Output

For test quality findings:

| Priority | Issue | Evidence | Fix |
|----------|-------|----------|-----|
| P0 | No tests on auth flow | tests/ has no test_auth_* | Add tests covering login success/failure, MFA, rate limit |
| P1 | Tests mock too much | tests/services/test_user.py:42 — mocks UserRepo | Use in-memory repo |
| P1 | Tests not isolated | tests/test_a.py:10 — assumes test_db clean | Use function-scoped fixture |
| P2 | Tests don't cover edge cases | tests/test_login.py only covers happy path | Add empty/null/unicode cases |

Findings should be specific: file, line, what's wrong, what to fix.
