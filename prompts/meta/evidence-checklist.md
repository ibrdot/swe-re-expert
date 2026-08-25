# Evidence Checklist \u2014 What Counts as Proof, Verifiably

The 12-point checklist for evidence quality. Run every claim through this before publishing. This checklist is the foundation of credible analysis - without it, findings are opinion, not fact. Every analyst, regardless of experience level, must apply this discipline to every finding.

---

## The 12-point checklist

For every claim in the report, verify ALL 12 points. Failure on any point means the claim is not ready for publication. This is non-negotiable - weak evidence produces weak reports, and weak reports get ignored.

### Core Verification Points

#### 1. \u2610 **Specific location** \u2014 file:line for SWE, offset/address for RE

**Requirement**: Every finding MUST have a precise, verifiable location.

**SWE Requirements**:
- Must include filename (relative path from repo root)
- Must include line number
- Optional: column number for multi-line statements
- Format: `path/to/file:line` or `path/to/file:line:column`
- Example: `src/auth/service.py:42` or `src/auth/service.py:42:8`

**RE Requirements**:
- Must include section name (`.text`, `.data`, `.rdata`, etc.)
- Must include offset (file offset or RVA)
- Optional: function name if recovered
- Format: `section:offset` or `function+offset`
- Examples: `.text:0x401234`, `sub_401000+0x234`

**Architecture Requirements**:
- Must include module/component name
- Must include relationship type (imports, calls, depends on)
- Format: `ModuleA -> ModuleB (relationship)`
- Example: `auth_service -> user_repository (direct import)`

**Verification Test**:
```bash
# For SWE: Can the reader open the file and see the issue?
vim +42 src/auth/service.py

# For RE: Can the reader disassemble and see the instruction?
objdump -d -M intel target | grep -A5 -B5 '0x401234'
```

**Anti-Patterns**:
- \u274c "In the user module..."
- \u274c "Somewhere in the auth code..."
- \u274c "Around line 40..."
- \u274c "In the binary..."

**Correct Examples**:
- \u2705 `user_service.py:42 \u2014 cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")`
- \u2705 `.text:0x401234 \u2014 call rax ; rax = CreateRemoteThread from IAT`
- \u2705 `auth_service.py:15 \u2014 from domain.user import User`

**Pro Tip**: Use absolute line numbers, not relative descriptions. "Line 42" is verifiable; "the function at the top of the file" is not.

---

#### 2. \u2610 **Verifiable artifact** \u2014 quoted code, instruction, or string

**Requirement**: Every finding MUST include the exact artifact that proves the claim.

**For Code Findings**:
- Must quote the actual code (minimum 1 complete line)
- Must preserve whitespace and formatting
- Must include surrounding context if the issue spans multiple lines
- Must use proper escaping for special characters

**For Binary Findings**:
- Must show disassembly (minimum 1 instruction)
- Or show hex bytes (minimum 4 bytes for meaningful analysis)
- Or show exact string match
- Must include architecture (x86, x86-64, ARM, etc.)

**For String Findings**:
- Must quote the exact string
- Must include context (surrounding strings, section)
- Must note if string is null-terminated or length-prefixed

**Minimum Evidence Standards**:
| Finding Type | Minimum Evidence | Example |
|--------------|------------------|---------|
| SQL Injection | Full query string | `cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")` |
| Buffer Overflow | Function call + types | `strcpy(dst, src)` where `dst` is `char[16]` |
| Suspicious Import | Import statement | `from ctypes import windll` |
| Shellcode | Hex bytes | `\xfc\xe8\x00\x00\x00\x00\x60\x89` |
| C2 URL | Full URL | `https://evil[.]com/api/data` |

**Verification Test**:
```bash
# For code: Can the reader grep for the exact string?
rg "cursor.execute\(f\"SELECT \* FROM users WHERE id = " src/

# For binary: Can the reader see the same bytes?
xxd -s 0x401234 -l 16 target | head -1
```

**Anti-Patterns**:
- \u274c "The code has a vulnerability."
- \u274c "There's a suspicious call."
- \u274c "The binary contains malware-like strings."

**Correct Examples**:
- \u2705 "The `strcpy(dst, src)` call at line 47 \u2014 `dst` is `char[16]`, `src` is `char*` from user input, no bounds check."
- \u2705 "The `.rodata:0x4080` contains the string `MZP\x00\x00\x00` (PE header signature)."
- \u2705 "The import table at 0x402000 contains `CreateRemoteThread` from kernel32.dll."

**Pro Tip**: Always include enough context for the reader to understand the issue without seeing the full file. If the finding is a single line, quote 3-5 lines around it.

---

#### 3. \u2610 **Concrete consequence** \u2014 bug class, behavior, cost

**Requirement**: Every finding MUST state the bug class, trigger condition, and impact.

**Bug Class Taxonomy**:

**Security Bugs**:
- Injection: SQLi, XSS, Command Injection, LDAP Injection
- Memory Corruption: Buffer Overflow, Use-After-Free, Double Free, Heap Overflow
- Authentication: Broken Auth, Weak Credentials, Session Fixation
- Authorization: IDOR, Privilege Escalation, Missing ACL
- Information Disclosure: Info Leak, Path Disclosure, Source Code Leak
- Denial of Service: Crash, Hang, Resource Exhaustion
- Logic Flaws: Race Condition, TOCTOU, Business Logic Bypass

**Code Quality Bugs**:
- Performance: N+1 Query, Inefficient Algorithm, Blocking I/O
- Reliability: Unhandled Exception, Resource Leak, Deadlock
- Maintainability: Duplicate Code, Long Method, Complex Nesting
- Testability: Untestable Code, Hardcoded Values, Magic Numbers

**Architecture Bugs**:
- Coupling: Tight Coupling, Circular Dependency
- Cohesion: Low Cohesion, God Class
- Design: Violated SOLID, Anti-Pattern
- Integration: Incompatible APIs, Version Mismatch

**RE/RE Bugs**:
- Packing: Packed Binary, Obfuscated Code
- Anti-Analysis: Anti-Debug, Anti-VM, Anti-Sandbox
- Suspicious: Suspicious Imports, Suspicious Strings
- Malicious: Malware Behavior, Exploit Code

**Impact Classification**:
| Severity | Business Impact | Technical Impact | Response Time |
|----------|-----------------|------------------|---------------|
| P0/Critical | >$100K loss | RCE, Data Breach | Immediate (24h) |
| P1/High | $10K-$100K loss | Auth Bypass, DoS | Urgent (1 week) |
| P2/Medium | $1K-$10K loss | Info Leak, Crash | Next Sprint |
| P3/Low | <$1K loss | Style Issue, Tech Debt | Backlog |

**Consequence Structure**:
```
[Severity]: [Bug Class] at [Location]
Trigger: [Input/State that activates the issue]
Impact: [What happens when triggered]
Cost: [Estimated business impact]
```

**Anti-Patterns**:
- \u274c "This could be a problem."
- \u274c "This is unsafe."
- \u274c "There might be an issue here."

**Correct Examples**:
- \u2705 "Buffer overflow \u2014 when `src` > 15 bytes, writes past `dst` (stack overflow \u2192 RCE on non-PIE/non-NX binaries, DoS on hardened binaries)."
- \u2705 "P0: SQL injection at user_search.py:23 \u2014 user-controlled `q` concatenated into query allows auth bypass (verified with `' OR '1'='1`)."
- \u2705 "P1: Race condition in file_lock.py:17 \u2014 concurrent writes to shared file can corrupt data (reproduced with 10 concurrent threads)."

**Pro Tip**: Always state the worst-case impact, then qualify with mitigating factors. "RCE on vulnerable systems, DoS on hardened systems" is better than "might cause a crash".

---

#### 4. \u2610 **Reproducible command** \u2014 reader can run it and see the same thing

**Requirement**: Every finding MUST include a command the reader can run to verify the issue.

**SWE Commands**:
```bash
# Find SQL injection patterns
rg "execute\(f['\\\"]" --type py src/

# Find hardcoded secrets
rg "password\s*=\s*['\"]" --type py src/

# Find TODO comments
rg "# TODO" src/

# Run specific test
python -m pytest tests/test_auth.py::test_login -v

# Build the project
make build 2>&1 | grep -i error
```

**RE Commands**:
```bash
# Disassemble specific function
objdump -d -M intel target --disassemble=sub_401234

# Find suspicious imports
objdump -p target | grep -i "CreateRemoteThread\|VirtualAlloc\|WriteProcessMemory"

# Extract strings
strings -n 8 target | grep -i "http\|\.com\|\.net"

# Check section entropy
radare2 -q -c 'iS; af' target

# Find cross-references
radare2 -q -c 'axt sub_401234' target
```

**Command Requirements**:
- Must be copy-paste executable
- Must include expected output or output snippet
- Must work on standard tools (grep, rg, objdump, strings, etc.)
- Must not require proprietary tools unless specified

**Verification Test**:
```bash
# The reader should be able to run your command and see similar output
# If they can't, your command is not reproducible
```

**Anti-Patterns**:
- \u274c "I found a suspicious pattern."
- \u274c "There are issues in the code."
- \u274c "The binary has suspicious characteristics."

**Correct Examples**:
- \u2705 "Run `rg \"execute\\(f['\\\"]\" --type py`. Output:
  ```
  src/services/user_search.py:23:    cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")
  src/services/admin_search.py:18:    cursor.execute(f\"SELECT * FROM logs WHERE message LIKE '%{q}%'\")
  ```
  Both are SQL injection \u2014 `q` is user input, concatenated into the query."

- \u2705 "Run `objdump -d -M intel target | grep -A2 'call.*CreateRemoteThread'`. Output:
  ```
  401234: ff 15 18 30 00 00    call rax  ; rax = CreateRemoteThread from IAT
  ```
  This is the call site. Walk backward from here to find the function that prepares the args."

**Pro Tip**: Always test your commands before including them. If a command takes >30 seconds to run, note the expected runtime and suggest optimizations (e.g., `head -20` for large outputs).

---

### Quality Assurance Points

#### 5. \u2610 **No decorative citations** \u2014 only links that directly support the claim

**Requirement**: Every citation MUST directly support the specific claim, not just the general topic.

**Citation Rules**:
- Must point to specific section, not homepage
- Must verify link content before citing
- Must quote the relevant text from the source
- Must explain how the citation supports the claim

**Acceptable Citations**:
- Specific OWASP Cheat Sheet sections
- CVE entries with technical details
- Vendor documentation for specific APIs
- RFC sections for protocol details
- Academic papers with specific findings

**Unacceptable Citations**:
- Homepages (owasp.org, cve.mitre.org)
- General documentation (docs.python.org without path)
- Wikipedia pages (unless very specific)
- Blog posts without technical depth

**Verification Test**:
1. Open the link
2. Find the specific section cited
3. Verify it supports the exact mechanism you're claiming
4. If it doesn't, find a better source or remove the citation

**Anti-Patterns**:
- \u274c "See OWASP Top 10 for more info: https://owasp.org/Top10/"
- \u274c "Check CVE database: https://cve.mitre.org/"
- \u274c "Refer to Python docs: https://docs.python.org/3/"

**Correct Examples**:
- \u2705 "See OWASP SQL Injection Prevention Cheat Sheet, 'Use of Prepared Statements (with Parameterized Queries)' section: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html#use-of-prepared-queries-stored-procedures"
- \u2705 "CVE-2021-44228 (Log4Shell) details: https://nvd.nist.gov/vuln/detail/CVE-2021-44228#vulnCurrentDescriptionTitle"
- \u2705 "Python `subprocess` security documentation: https://docs.python.org/3/library/subprocess.html#security-considerations"

**Pro Tip**: Use archive.today or web.archive.org links for critical citations to prevent link rot. Note the access date: `[Accessed: 2024-01-15]`.

---

#### 6. \u2610 **No hedging** \u2014 confidence is stated via markers, not vague words

**Requirement**: Never use vague language to express uncertainty. Use specific markers instead.

**Hedging Words to Avoid**:
- might, maybe, possibly, could, may, perhaps
- seems, appears, looks like, probably
- potentially, potentially could, might potentially
- some, many, several, various
- etc., and so on

**Confidence Markers** (use these instead):
- **Severity**: P0, P1, P2, P3 (for priority)
- **Certainty**: CONFIRMED, VERIFIED (for high confidence)
- **Uncertainty**: HYPOTHESIS, SUSPECTED, UNVERIFIED, BLOCKED, INCONCLUSIVE

**Confidence Levels**:
| Marker | Confidence | Evidence Required | Action Required |
|--------|------------|-------------------|-----------------|
| CONFIRMED | 95-100% | Multiple strong signals, verified | Act immediately |
| VERIFIED | 90-95% | Strong evidence, one verification | Act with high priority |
| SUSPECTED | 70-90% | Strong signals, needs confirmation | Investigate further |
| HYPOTHESIS | 50-70% | Plausible but unproven | Test hypothesis |
| UNVERIFIED | 30-50% | Needs external verification | Gather more evidence |
| BLOCKED | 0-30% | Evidence unavailable | Unblock analysis |
| INCONCLUSIVE | N/A | Conflicting evidence | Resolve conflict |

**Anti-Patterns**:
- \u274c "This might be a SQL injection."
- \u274c "There could possibly be a buffer overflow."
- \u274c "This appears to be malware."

**Correct Examples**:
- \u2705 "P0: SQL injection at line 23. Concrete trigger: user-controlled `q` concatenated into query. To confirm: send `' OR '1'='1` as `q` and verify auth bypass."
- \u2705 "SUSPECTED: Lumma stealer variant. Evidence: Mutex name matches, 6/9 C2 patterns present. To confirm: submit SHA-256 to MalwareBazaar."
- \u2705 "HYPOTHESIS: The function at 0x401234 is AES decryption. Evidence: Contains S-box, xor loop. To confirm: emulate with Unicorn."

**Pro Tip**: Pair severity with uncertainty markers for maximum clarity: "P0 SUSPECTED: ..." or "P2 HYPOTHESIS: ...". This gives the reader both priority and confidence level.

---

#### 7. \u2610 **Consequence first** \u2014 lead with impact, then evidence

**Requirement**: Structure every finding with consequence first, then supporting details.

**Finding Structure**:
```
[Severity] [Bug Class] at [Location]
Impact: [What happens]
Trigger: [How it's activated]
Evidence: [Proof]
```

**Why Consequence First?**:
- Readers scan reports, not read them word-for-word
- The first 5-10 words determine if they keep reading
- Impact drives prioritization and action
- Evidence supports the claim, but impact sells it

**Anti-Patterns**:
- \u274c "Line 23 has `cursor.execute(f'SELECT ... WHERE name = {q}')`. The `q` is from user input. This is SQL injection. Impact: auth bypass."
- \u274c "In the auth module, there's a function that doesn't properly validate input, which could lead to security issues."

**Correct Examples**:
- \u2705 "P0 SQL injection at line 23. Impact: auth bypass (verify with `' OR '1'='1`). Evidence: `cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")` where `q` is from `request.args.get('q')` at line 12."
- \u2705 "P1 buffer overflow in parse_config.c:47. Impact: RCE on non-NX systems, DoS on NX. Evidence: `strcpy(dst, src)` where `dst` is 16-byte stack buffer, `src` is user-controlled."
- \u2705 "P2 race condition in cache.py:101. Impact: stale data served to users. Evidence: concurrent writes to shared dict without locking."

**Pro Tip**: Use the "So what?" test. After writing a finding, ask: "So what? Why should the reader care?" If you can't answer in one sentence, the consequence isn't clear enough.

---

#### 8. \u2610 **Before/after where applicable** \u2014 show the fix, not just the bug

**Requirement**: For every actionable finding, show both the current (bad) state and the proposed (good) state.

**For Code Findings**:
- Show current code (minimum 1 line, preferably 3-5 with context)
- Show proposed code (same scope)
- Show diff if helpful
- Include estimated effort

**For Architecture Findings**:
- Show current diagram or relationship
- Show proposed diagram or relationship
- Explain migration path
- Include rollback plan

**For Configuration Findings**:
- Show current config
- Show proposed config
- Explain change rationale
- Include testing requirements

**Before/After Format**:
```
Current (file:line):
```language
[bad code]
```

Recommended:
```language
[good code]
```

Effort: [LOC changed] lines, [time estimate]
Rollback: [how to revert]
```

**Anti-Patterns**:
- \u274c "Use parameterized queries."
- \u274c "Fix the buffer overflow."
- \u274c "Refactor the architecture."

**Correct Examples**:
- \u2705 "Current (line 23):
  ```python
  cursor.execute(f\"SELECT * FROM users WHERE name LIKE '%{q}%'\")
  ```
  
  Recommended:
  ```python
  cursor.execute(\"SELECT * FROM users WHERE name LIKE %s\", (f'%{q}%',))
  ```
  
  One-line change. Trivial rollback."

- \u2705 "Current architecture:
  ```
  controllers/ -> domain/ (wrong direction)
  domain/ -> controllers/ (cycle)
  ```
  
  Recommended:
  ```
  controllers/ -> domain/ (correct direction)
  domain/ -> no controllers/ (no cycle)
  ```
  
  Effort: 2 PRs (extract + invert), 1 day, reversible."

**Pro Tip**: Always include a rollback plan. "Revert the PR" is acceptable for simple changes, but document it explicitly. For complex changes, document the exact steps to revert.

---

#### 9. \u2610 **Filter applied** \u2014 passes the materiality gate (concrete cost)

**Requirement**: Every finding MUST have measurable impact or clear risk that justifies the effort to fix.

**Materiality Gate**: A finding must meet ONE of these criteria:
- **Business Impact**: Estimated cost > $1,000 if unaddressed
- **Security Risk**: Exploitable with severe consequences (RCE, data breach, auth bypass)
- **Compliance Risk**: Violation of regulatory requirements (GDPR, HIPAA, PCI-DSS)
- **Technical Debt**: >1 hour of dev time to fix
- **Performance Impact**: >10% degradation in key metrics
- **Reliability Impact**: >1 crash per 1,000 requests

**Materiality Assessment**:
| Criterion | Threshold | Example |
|-----------|-----------|---------|
| Revenue Impact | >$10K/year | Payment processing bug |
| Security Impact | CVSS >= 7.0 | SQLi, RCE, Auth Bypass |
| Compliance Impact | Regulatory violation | GDPR data leak |
| Dev Time Impact | >8 hours | Major refactor |
| Performance Impact | >20% slowdown | N+1 query |
| Reliability Impact | >1% error rate | Unhandled exception |

**Cost-Benefit Analysis**:
For each finding, estimate:
- **Fix Cost**: Time to implement and test (hours/days)
- **Fix Risk**: Probability of introducing new bugs (low/medium/high)
- **Fix Value**: Business value of fixing (low/medium/high/critical)
- **Net Benefit**: Fix Value - Fix Cost - Fix Risk

**Anti-Patterns**:
- \u274c "The code uses old style." (no measurable impact)
- \u274c "This could be improved." (no specific benefit)
- \u274c "Best practice violation." (no concrete cost)

**Correct Examples**:
- \u2705 "The `time.sleep(1)` at line 47 is used for synchronization. When called concurrently under load, this introduces a 1-second latency per request; measured impact: at 100 RPS, average latency 1.04s instead of expected 50ms. Fix: use `threading.Event` for proper sync; measured speedup: 20x on this hot path."
- \u2705 "P0: SQL injection at user_search.py:23. Business impact: Complete auth bypass allows unauthorized access to any user account. Fix cost: 30 minutes. Fix value: Critical (prevents data breach)."
- \u2705 "P2: Missing error handling in file_utils.py:15. Impact: Unhandled IOError crashes the application (observed 3 times in production logs). Fix cost: 2 hours. Fix value: Medium (improves reliability)."

**Pro Tip**: Use the "Would I fix this on my own time?" test. If you wouldn't spend your own time fixing it, it probably doesn't pass the materiality gate. Document it but don't prioritize it.

---

#### 10. \u2610 **Acceptable alternative considered** \u2014 current shape isn't reasonable

**Requirement**: For every recommendation, consider and document alternative solutions.

**Alternative Analysis Framework**:
1. **Current State**: What exists now
2. **Recommended Solution**: What you propose
3. **Alternative Solutions**: Other viable approaches
4. **Comparison**: Why recommended > alternatives
5. **Trade-offs**: What you gain and lose with each

**Evaluation Criteria**:
- **Correctness**: Does it solve the problem?
- **Performance**: What's the performance impact?
- **Complexity**: How complex is the implementation?
- **Maintainability**: How easy to maintain?
- **Compatibility**: Does it work with existing systems?
- **Cost**: Time, money, resources required?

**Anti-Patterns**:
- \u274c "Use Repository pattern." (no consideration of alternatives)
- \u274c "This is the best approach." (no justification)
- \u274c "Just do this." (no analysis)

**Correct Examples**:
- \u2705 "Domain layer imports controllers (file.py:5). The intended layered architecture has domain independent; the current shape creates a cycle (controllers \u2192 domain \u2192 controllers). Inverting is the bounded fix; the alternative (full DDD) is overkill for the current complexity. Trade-off: Inverting takes 1 day, DDD would take 2 weeks with unclear ROI."
- \u2705 "Current: Hardcoded API keys in config.py. Recommended: Environment variables. Alternative: Secret management service (AWS Secrets Manager, HashiCorp Vault). Trade-off: Env vars are simpler (1 hour to implement), secret management is more secure but adds complexity and external dependency (2 days + ongoing costs)."
- \u2705 "Current: Synchronous file I/O in data_processor.py. Recommended: Thread pool. Alternative: Async I/O (asyncio). Trade-off: Thread pool works with existing sync code (2 hours to implement), async requires refactoring all I/O calls (1 week) but provides better scalability under high load."

**Pro Tip**: Always document the "do nothing" alternative. Explicitly state why the current state is unacceptable and what the cost of inaction is.

---

#### 11. \u2610 **Bounded recommendation** \u2014 fix is one PR or a documented migration sequence

**Requirement**: Every recommendation MUST be scoped, estimated, and reversible.

**Recommendation Structure**:
```
Fix: [What to do]
Scope: [Files/modules affected]
Effort: [Time estimate] (minutes, hours, days)
PRs: [Number of PRs required]
Testing: [What tests are needed]
Rollback: [How to revert]
Dependencies: [What must be done first]
```

**Effort Estimation Guidelines**:
| Complexity | Time Estimate | LOC Changed | PR Count |
|------------|---------------|-------------|----------|
| Trivial | <30 minutes | <10 LOC | 1 |
| Small | 30-60 minutes | 10-50 LOC | 1 |
| Medium | 1-4 hours | 50-200 LOC | 1-2 |
| Large | 4-8 hours | 200-500 LOC | 2-3 |
| XL | 1-2 days | 500-1000 LOC | 3-5 |
| XXL | 2+ days | 1000+ LOC | 5+ |

**Rollback Requirements**:
- Must be documented for every recommendation
- Must be executable in <5 minutes for trivial/small changes
- Must be tested before deployment for medium+ changes
- Must preserve data and state where possible

**Anti-Patterns**:
- \u274c "Refactor the architecture." (no scope, no estimate)
- \u274c "Fix the bug." (no details)
- \u274c "Improve the code." (no actionable steps)

**Correct Examples**:
- \u2705 "Invert the import in 2 PRs:
  1. PR1: Extract domain logic from controllers into domain/ (one file). ~30 LOC, 1 hour, with tests.
  2. PR2: Invert the import \u2014 controllers import domain, not vice versa. ~10 LOC, 30 minutes.
  Rollback: revert the PRs. Testing: existing tests should pass."
- \u2705 "Fix: Parameterize query at user_search.py:23.
  Scope: 1 file, 1 line change.
  Effort: 30 minutes.
  PRs: 1.
  Testing: Run `pytest tests/test_user_search.py` to verify no regressions.
  Rollback: `git revert <commit-hash>`.
  Dependencies: None."

**Pro Tip**: Use the "Can a junior dev implement this?" test. If the recommendation requires senior-level expertise to implement safely, either simplify it or add more guidance and safeguards.

---

#### 12. \u2610 **Uncertainty marked** \u2014 HYPOTHESIS / SUSPECTED / UNVERIFIED / BLOCKED / INCONCLUSIVE

**Requirement**: Every uncertain finding MUST use one of the five uncertainty markers and explain what would confirm or refute it.

**Uncertainty Markers Definition**:

| Marker | Confidence | When to Use | What to Include |
|--------|------------|-------------|-----------------|
| `HYPOTHESIS` | 50-70% | Best guess based on partial evidence | Hypothesis, supporting evidence, confirm test |
| `SUSPECTED` | 70-90% | Strong signals but not confirmed | Signals, missing pieces, confirm test |
| `UNVERIFIED` | 30-50% | Needs external verification | What's known, what's unknown, verification method |
| `BLOCKED` | 0-30% | Evidence unavailable | Blocking factor, unblock method, effort estimate |
| `INCONCLUSIVE` | N/A | Conflicting evidence | Both sides, why it's a tie, resolution method |

**Marker Usage Examples**:

**HYPOTHESIS**:
```
HYPOTHESIS: The function at 0x401234 is a config parser.

Evidence:
- Reads from .data:0x4050 (byte sequence resembling a header)
- Writes to 256-byte stack buffer (config struct?)
- Calls atoi@plt (parsing numbers)

To confirm: Trace the function with expected input format, verify output structure matches known config schema.
```

**SUSPECTED**:
```
SUSPECTED: Lumma stealer variant.

Evidence:
- Mutex name Global\\Lumma_v2_... matches Lumma pattern
- Imports include LsaOpenPolicy and CryptUnprotectData (Lumma imports)
- String set includes 6 of 9 known Lumma C2 URI patterns
- Section entropy profile matches known Lumma samples

Not confirmed because: No YARA match against published Lumma rules; SHA-256 not in MalwareBazaar.

To confirm: Submit SHA-256 to MalwareBazaar for family match; run dynamically in instrumented VM to verify browser profile enumeration.
```

**UNVERIFIED**:
```
UNVERIFIED: This binary uses Go 1.21.

Evidence: go:build strings present.

Unknown: Exact patch version (1.21.x where x is unknown).

To verify: Run `go version -m <binary>` to confirm exact version.
```

**BLOCKED**:
```
BLOCKED: Cannot determine C2 protocol.

Blocking factor: Binary is packed (Themida, .themida section, entropy 7.95).

To unblock: Dynamic unpack \u2014 run in isolated VM under x64dbg, breakpoint at OEP, dump memory, re-analyze. Estimated effort: 4 hours.
```

**INCONCLUSIVE**:
```
INCONCLUSIVE: Whether this binary is malware.

Static signals FOR:
- High-entropy .text (7.6) \u2192 suspicious (suggests packing)
- No imports beyond kernel32 \u2192 suspicious (suggests dynamic resolution)

Static signals AGAINST:
- Small file size (12KB) \u2192 unusual for malware
- PDB path C:\\projects\\test_app\\release\\test_app.pdb \u2192 suggests development artifact

Cannot determine statically.

To resolve: Submit to VirusTotal for multi-AV scan; run dynamically in instrumented VM for behavioral confirmation.
```

**Anti-Patterns**:
- \u274c "This is probably malware."
- \u274c "I think this might be a buffer overflow."
- \u274c "There could be issues I haven't found yet."

**Pro Tip**: Always pair uncertainty markers with actionable next steps. The reader should know exactly what to do to resolve the uncertainty. Never leave them hanging.

---

## Running the checklist

Before publishing the report, walk every claim through these 12 points. Use this systematic approach:

### The 12-Point Verification Process

1. **Create a checklist table** for each finding:
   ```
   | Point | Status | Notes |
   |-------|--------|-------|
   | 1. Specific location | \u2610 | user_search.py:23 |
   | 2. Verifiable artifact | \u2610 | Quoted query string |
   | ... | ... | ... |
   | 12. Uncertainty marked | \u2610 | CONFIRMED |
   ```

2. **Check each point sequentially** - don't skip ahead
3. **If any point fails**, either:
   - Fix it (add missing evidence, clarify location, etc.)
   - Or remove the finding (if it can't be made specific)
4. **Re-verify** after making changes

### The "reject your own finding" pattern

Before submitting, actively try to refute each finding:

**For SWE Findings**:
- "Is the offset wrong?" \u2014 re-read the code
- "Is the bug actually safe because of upstream validation?" \u2014 trace the input flow
- "Is the test actually covering this case?" \u2014 check test coverage
- "Is this actually the intended behavior?" \u2014 check comments, commit history
- "Is there a compensating control?" \u2014 check middleware, decorators

**For RE Findings**:
- "Is the offset wrong?" \u2014 re-read the disasm
- "Is the import actually unused?" \u2014 check xrefs
- "Is the string actually from a library?" \u2014 check library signatures
- "Is the function actually called?" \u2014 check xrefs to the function
- "Is the analysis environment affecting the binary?" \u2014 check for anti-analysis

**For Architecture Findings**:
- "Is the current design actually acceptable for this use case?" \u2014 check requirements
- "Is the complexity actually a problem?" \u2014 measure cyclomatic complexity
- "Is the coupling actually causing issues?" \u2014 check change history, bug reports
- "Is the alternative actually better?" \u2014 prototype and measure
- "Is the team actually ready for this change?" \u2014 check team skills, bandwidth

**Refutation Test**: If you can successfully refute a finding, it must be:
1. **Fixed** - if the issue exists but your evidence was weak
2. **Cut** - if the issue doesn't actually exist

Findings that survive your own scrutiny are the ones that will survive the user's scrutiny.

---

## The Evidence Quality Scoring System

Use this scoring system to evaluate the overall quality of a finding's evidence:

| Criterion | Weight | Excellent (3) | Good (2) | Fair (1) | Poor (0) |
|-----------|--------|---------------|----------|----------|----------|
| Specificity | 20% | Exact location + artifact | Specific location | General location | No location |
| Verifiability | 20% | Copy-paste command + output | Verifiable artifact | Described artifact | No artifact |
| Concreteness | 15% | Bug class + trigger + impact | Bug class + impact | Bug class only | Vague description |
| Reproducibility | 15% | Command + expected output | Reproducible command | Described method | No method |
| Completeness | 10% | All 12 points covered | 8-11 points | 4-7 points | <4 points |
| Actionability | 10% | Bounded + reversible | Bounded | Described | No recommendation |
| Clarity | 10% | Clear, concise, well-structured | Mostly clear | Somewhat unclear | Unclear |

**Scoring**:
- 90-100%: Excellent - Publish as-is
- 80-89%: Good - Minor improvements needed
- 70-79%: Fair - Significant improvements needed
- <70%: Poor - Do not publish, fix or cut

**Minimum Threshold**: 80% for all findings in a professional report.

---

## Common Evidence Failures and How to Fix Them

### Failure 1: Vague Location

**Problem**: "There's a bug in the auth module."

**Fix**: Add exact file and line: "auth/service.py:42 \u2014 `cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")`"

**Verification**: Can the reader open the file and see the issue in <10 seconds?

### Failure 2: Missing Artifact

**Problem**: "The code has a SQL injection vulnerability."

**Fix**: Quote the exact code: "`cursor.execute(f\"SELECT * FROM users WHERE name = '{q}'\")` where `q` is user input."

**Verification**: Can the reader grep for the exact string?

### Failure 3: No Consequence

**Problem**: "This function has a buffer overflow."

**Fix**: Add impact: "Buffer overflow when `src` > 15 bytes, writes past `dst` (stack overflow \u2192 RCE on non-NX systems, DoS on NX systems)."

**Verification**: Does the reader understand what happens and why they should care?

### Failure 4: No Reproducible Command

**Problem**: "I found suspicious strings in the binary."

**Fix**: Add command: "Run `strings -n 8 target | grep -i 'http'` to see the C2 URLs."

**Verification**: Can the reader run the command and see similar output?

### Failure 5: Decorative Citations

**Problem**: "See OWASP Top 10 for more info."

**Fix**: Add specific citation: "See OWASP SQL Injection Prevention Cheat Sheet, 'Use of Prepared Statements' section: [link]"

**Verification**: Does the link point to a specific section that directly supports your claim?

### Failure 6: Hedging Language

**Problem**: "This might be a problem."

**Fix**: Use marker: "P2 HYPOTHESIS: Potential race condition in cache.py:101. Evidence: Concurrent writes without locking."

**Verification**: Is the confidence level clear from the marker, not the language?

### Failure 7: Evidence After Conclusion

**Problem**: "This is a buffer overflow. Line 47 has `strcpy(dst, src)`."

**Fix**: Reorder: "P0 buffer overflow at line 47. `strcpy(dst, src)` where `dst` is 16-byte stack buffer."

**Verification**: Does the reader see the impact within the first 5 words?

### Failure 8: No Fix Shown

**Problem**: "Use parameterized queries."

**Fix**: Show before/after:
```
Current:
cursor.execute(f"SELECT ... WHERE name = '{q}'")

Recommended:
cursor.execute("SELECT ... WHERE name = %s", (q,))
```

**Verification**: Does the reader know exactly what to change?

### Failure 9: No Materiality

**Problem**: "The code uses old style."

**Fix**: Add impact: "The `time.sleep(1)` at line 47 introduces 1s latency per request; at 100 RPS, average latency is 1.04s instead of 50ms (20x slower)."

**Verification**: Does the reader understand the business impact?

### Failure 10: No Alternatives Considered

**Problem**: "Use Repository pattern."

**Fix**: Add analysis: "Recommended: Invert the import. Alternative: Full DDD refactor. Trade-off: Invert takes 1 day, DDD takes 2 weeks with unclear ROI for current complexity."

**Verification**: Does the reader understand why you chose this approach?

### Failure 11: Unbounded Recommendation

**Problem**: "Refactor the architecture."

**Fix**: Add scope: "Invert import in 2 PRs: PR1 extract domain logic (1 hour), PR2 invert import (30 minutes). Rollback: revert PRs."

**Verification**: Does the reader know the cost and scope?

### Failure 12: No Uncertainty Marker

**Problem**: "This is probably malware."

**Fix**: Use marker: "SUSPECTED malware. Evidence: Mutex name matches, 6/9 C2 patterns. To confirm: Submit to MalwareBazaar."

**Verification**: Does the reader know your confidence level and how to verify?

---

## The Evidence Checklist Workflow

### Step 1: Draft the Finding
Write the finding as it comes to you, without worrying about the checklist.

### Step 2: Apply the Checklist
Go through each of the 12 points and verify your finding meets the requirement.

### Step 3: Fix Weaknesses
For any point that fails, either fix it or cut the finding.

### Step 4: Re-verify
After making changes, re-apply the checklist to ensure all points pass.

### Step 5: Peer Review
Have another analyst review your findings using the checklist. Fresh eyes catch things you miss.

### Step 6: Final Verification
Before publishing, do a final pass:
1. Run the reproducible commands yourself
2. Verify all links work and support your claims
3. Check that all evidence is quoted correctly
4. Ensure all recommendations are bounded and reversible

---

## Output

For every finding, the report should be able to answer all 12 points. If you can't answer one, the finding isn't ready.

The deliverable is not "I have 30 findings." It's "I have 15 verifiable, material, bounded findings that pass all 12 evidence checklist points, and 15 I rejected after running the checklist."

**Quality > quantity. Always.**

### The 80/20 Rule of Evidence
- 20% of findings will provide 80% of the value
- Focus your effort on making those 20% bulletproof
- The other 80% should meet the minimum standard, but don't over-invest
- Cut the bottom 20% that can't meet the standard

### The Credibility Multiplier
- One strong finding with excellent evidence builds credibility
- One weak finding with poor evidence destroys credibility
- The net effect: 10 strong findings + 1 weak finding = 5 strong findings (credibility halved)
- Moral: It's better to have 5 strong findings than 10 findings with 1 weak one

### Final Checklist Before Publishing

- [ ] Every finding has a specific location
- [ ] Every finding has a verifiable artifact
- [ ] Every finding has a concrete consequence
- [ ] Every finding has a reproducible command
- [ ] No decorative citations
- [ ] No hedging language
- [ ] Consequence comes first
- [ ] Before/after shown where applicable
- [ ] Materiality gate passed
- [ ] Alternatives considered
- [ ] Recommendations are bounded
- [ ] Uncertainty is marked
- [ ] All commands have been tested
- [ ] All links have been verified
- [ ] Report has been peer-reviewed

**When in doubt, cut it out.**
