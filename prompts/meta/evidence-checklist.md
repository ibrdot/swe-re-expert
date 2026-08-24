# Evidence Checklist — What Counts as Proof, Verifiably

The 12-point checklist for evidence quality. Run every claim through this before publishing.

## The 12-point checklist

For every claim in the report, verify:

1. ☐ **Specific location** — file:line for SWE, offset/address for RE
2. ☐ **Verifiable artifact** — quoted code, instruction, or string
3. ☐ **Concrete consequence** — bug class, behavior, cost
4. ☐ **Reproducible command** — reader can run it and see the same thing
5. ☐ **No decorative citations** — only links that directly support the claim
6. ☐ **No hedging** — confidence is stated via markers, not vague words
7. ☐ **Consequence first** — lead with impact, then evidence
8. ☐ **Before/after where applicable** — show the fix, not just the bug
9. ☐ **Filter applied** — passes the materiality gate (concrete cost)
10. ☐ **Acceptable alternative considered** — current shape isn't reasonable
11. ☐ **Bounded recommendation** — fix is one PR or a documented migration sequence
12. ☐ **Uncertainty marked** — HYPOTHESIS / SUSPECTED / UNVERIFIED / BLOCKED / INCONCLUSIVE

If any fails, the claim isn't ready for the report. Fix or remove.

## Point 1: Specific location

❌ "In the user module, there's a bug."
✅ "user_service.py:42 — `cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")`"

The reader opens `user_service.py`, goes to line 42, sees the exact code. Verifiable in 5 seconds.

## Point 2: Verifiable artifact

❌ "The code is unsafe."
✅ "The `strcpy(dst, src)` call at line 47 — `dst` is `char[16]`, `src` is `char*` from user input, no bounds check."

The reader can read the call and verify the types. Specific.

## Point 3: Concrete consequence

❌ "This could be a problem."
✅ "Buffer overflow — when `src` > 15 bytes, writes past `dst` (stack overflow → RCE on non-PIE/non-NX binaries, DoS on hardened binaries)."

Concrete bug class (buffer overflow), concrete trigger (src > 15 bytes), concrete impact (RCE on weak binaries, DoS on hardened).

## Point 4: Reproducible command

For RE specifically:

❌ "I found a suspicious call."
✅ "Run `objdump -d -M intel target | grep -A2 'call.*CreateRemoteThread'`. Output:
```
401234: ff 15 18 30 00 00    call rax  ; rax = CreateRemoteThread from IAT
```
This is the call site. Walk backward from here to find the function that prepares the args."

The reader runs the command, sees the same output. Verifiable in 30 seconds.

For SWE:

❌ "There are SQL injection patterns in the codebase."
✅ "Run `rg \"execute\\(f['\\\"]\" --type py`. Output:
```
src/services/user_search.py:23:    cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")
src/services/admin_search.py:18:    cursor.execute(f\"SELECT * FROM logs WHERE message LIKE '%{q}%'\")
```
Both are SQL injection — `q` is user input, concatenated into the query."

Verifiable. The reader runs the command, gets the same hits.

## Point 5: No decorative citations

❌ "See OWASP Top 10 for more info: https://owasp.org/Top10/" — decorative; doesn't help fix
✅ "See OWASP SQL Injection Prevention Cheat Sheet, 'Use of Prepared Statements (with Parameterized Queries)' section: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html#use-of-prepared-queries-stored-procedures"

The second link goes to a specific section that directly supports the recommended fix. Open it before citing; verify it supports the mechanism, not just the general defect.

## Point 6: No hedging

❌ "This might maybe possibly be a problem."
✅ "P0: SQL injection at line 23. Concrete trigger: user-controlled `q` concatenated into query. To confirm: send `' OR '1'='1` as `q` and verify auth bypass."

The second version uses the P0 severity (confidence marker) and a specific confirm-test.

## Point 7: Consequence first

❌ "Line 23 has `cursor.execute(f'SELECT ... WHERE name = {q}')`. The `q` is from user input. This is SQL injection. Impact: auth bypass."
✅ "P0 SQL injection at line 23. Impact: auth bypass (verify with `' OR '1'='1`). Evidence: `cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")` where `q` is from `request.args.get('q')` at line 12."

Consequence first (P0 SQL injection, auth bypass), then evidence (the code + the input source). Reader scans the top, knows severity, then reads details.

## Point 8: Before/after for SWE

❌ "Use parameterized queries."
✅ "Current (line 23):
```python
cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")
```

Recommended:
```python
cursor.execute(\"SELECT * FROM users WHERE name LIKE %s\", (f'%{q}%',))
```

One-line change. Trivial rollback."

Shows the current code, the proposed code, the size of the change. The reader knows exactly what to do.

## Point 9: Materiality filter

❌ "The code uses old style." — pattern preference, no cost
✅ "The `time.sleep(1)` at line 47 is used for synchronization. When called concurrently under load, this introduces a 1-second latency per request; measured impact: at 100 RPS, average latency 1.04s instead of expected 50ms. Fix: use `threading.Event` for proper sync; measured speedup: 20x on this hot path."

Concrete cost (1.04s vs 50ms), measured impact (20x improvement). Without the measurement, it's not a finding.

## Point 10: Acceptable alternative considered

❌ "Use Repository pattern." — alternative? both are fine
✅ "Domain layer imports controllers (file.py:5). The intended layered architecture has domain independent; the current shape creates a cycle (controllers → domain → controllers). Inverting is the bounded fix; the alternative (full DDD) is overkill for the current complexity."

Considers the alternative (DDD), explains why it's not recommended (overkill), recommends the bounded alternative (invert).

## Point 11: Bounded recommendation

❌ "Refactor the architecture."
✅ "Invert the import in 2 PRs:
1. PR1: Extract domain logic from controllers into domain/ (one file). ~30 LOC, 1 hour, with tests.
2. PR2: Invert the import — controllers import domain, not vice versa. ~10 LOC, 30 minutes.
Rollback: revert the PRs."

Two PRs. Each bounded. Reversible. The reader knows the cost.

## Point 12: Uncertainty marked

❌ "This is probably malware."
✅ "SUSPECTED: Lumma stealer variant. Evidence:
- Mutex name `Global\Lumma_v2_...` matches Lumma pattern
- 6 of 9 known Lumma C2 URI patterns present
- Imports `LsaOpenPolicy` and `CryptUnprotectData` (Lumma-signature imports)

To confirm: submit SHA-256 to MalwareBazaar for family match; run dynamically in an
instrumented VM to verify browser profile enumeration."

SUSPECTED marker. Evidence cited. Confirm-test stated. The reader knows the confidence level.

## Running the checklist

Before publishing the report, walk every claim through these 12 points. Anything that fails:
- Fix it (add evidence, add a marker, add a bounded recommendation)
- Or remove it (if you can't make it specific, it's not a finding)

Most weak findings can be fixed in 5 minutes by adding evidence. Some can't — those should be cut.

## The "reject your own finding" pattern

Before submitting, try to refute each finding:

- "Is the offset wrong?" — re-read the disasm
- "Is the import actually unused?" — check xrefs
- "Is the bug actually safe because of upstream bounds?" — trace the input
- "Is the architecture actually OK in this framework?" — check framework idioms
- "Is the test failure actually expected?" — check if there's a comment

If you can refute it, fix or cut. Findings that survive your own scrutiny are the ones that survive the user's.

## Output

For every finding, the report should be able to answer all 12 points. If you can't answer one, the finding isn't ready.

The deliverable is not "I have 30 findings." It's "I have 15 verifiable, material, bounded findings, and 15 I rejected after running the checklist."

Quality > quantity. Always.
