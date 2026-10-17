# Uncertainty Markers \u2014 How to Be Honest Without Sounding Weak

The skill of marking uncertainty precisely. Senior analysts don't hedge ("might be, maybe, possibly") \u2014 they mark uncertainty with specific, actionable labels. This discipline separates amateur analysis from professional work. Every uncertain claim must be marked, explained, and actionable.

---

## The Core Principle: Uncertainty is Information

Uncertainty is not a weakness \u2014 it's valuable information for the reader. The goal is not to eliminate uncertainty (impossible in complex analysis) but to:
1. **Label it** \u2014 so the reader knows your confidence level
2. **Explain it** \u2014 so the reader understands what's known and unknown
3. **Action it** \u2014 so the reader knows what would resolve it

Without uncertainty markers, the reader assumes high confidence. When they discover you were wrong, your credibility suffers. With markers, they know exactly where the gaps are and can act accordingly.

---

## The 7 Uncertainty Markers

Use these markers consistently across all analysis. Each has a specific meaning and triggers specific actions.

| Marker | Confidence Range | Meaning | Reader Action | Analyst Action |
|--------|------------------|---------|---------------|----------------|
| `CONFIRMED` | Verified through multiple independent methods | Act immediately | Document verification steps |
| `VERIFIED` | Strong evidence, single verification path | Act with high priority | Note what was verified |
| `SUSPECTED` | Strong signals, confirmation pending | Investigate further | State what would confirm |
| `HYPOTHESIS` | Plausible but unproven | Test the hypothesis | Define a confirm/refute test |
| `UNVERIFIED` | Plausible, not yet checked | Gather evidence | Specify the verification method |
| `BLOCKED` | Required evidence unavailable | Resolve the blocker | Explain the blocking factor |
| `INCONCLUSIVE` | N/A | Conflicting evidence | Resolve conflict | List both sides |

**Marker Ordering**:
```
CONFIRMED  >  VERIFIED  >  SUSPECTED  >  HYPOTHESIS  >  UNVERIFIED  >  BLOCKED
(evidence available; order reflects verification depth, not a percentage scale)
---

## When to Use Each Marker

### 1. CONFIRMED (95-100% Confidence)

**Use When**: You have verified the claim through multiple independent methods and the evidence is overwhelming.

**Evidence Requirements**:
- Minimum 3 independent evidence sources
- Or 1 definitive evidence source (e.g., dynamic execution showing the behavior)
- No contradicting evidence
- All reasonable alternatives have been ruled out

**SWE Examples**:
```
CONFIRMED: SQL injection at user_search.py:23.

Evidence:
1. Static analysis: `cursor.execute(f"SELECT * FROM users WHERE name = '{q}'")` 
   where `q` is from `request.args.get('q')`
2. Dynamic verification: Sent `' OR '1'='1` as `q`, received all user records
3. Code path analysis: No input validation between request and query

Verification methods: Static grep, manual testing, code tracing
```

**RE Examples**:
```
CONFIRMED: Binary uses AES-256-CBC for string decryption.

Evidence:
1. Static: `.rodata:0x4080` contains AES S-box (verified byte sequence)
2. Static: Function at 0x401234 has AES-256 key schedule (240-byte key)
3. Dynamic: Emulated function with Unicorn, verified decryption of string at 0x409000
4. String: "AES-256-CBC" present in `.rdata:0x40A000`

Verification: Multiple static signatures + dynamic confirmation
```

**Architecture Examples**:
```
CONFIRMED: Circular dependency between auth_service and user_repository.

Evidence:
1. auth_service.py:5: `from user_repository import UserRepository`
2. user_repository.py:8: `from auth_service import AuthService`
3. Build fails when either import is removed

Verification: Code inspection + build testing
```

**When NOT to Use**:
- If you have only 1-2 evidence sources
- If there's any contradicting evidence
- If you haven't ruled out reasonable alternatives

**Pro Tip**: CONFIRMED findings should be rare. If you're marking most findings as CONFIRMED, you're either doing trivial analysis or overestimating your confidence.

---

### 2. VERIFIED (90-95% Confidence)

**Use When**: You have strong evidence from one method and the claim is highly plausible, but you haven't verified through multiple independent methods.

**Evidence Requirements**:
- Minimum 1 strong evidence source
- Claim is highly plausible based on the evidence
- No major gaps in the evidence
- Minor verification would increase confidence to CONFIRMED

**SWE Examples**:
```
VERIFIED: Memory leak in data_processor.py:101.

Evidence:
- Static analysis: `cache = {}` is populated in loop but never cleared
- Code inspection: No cache eviction logic anywhere in the module
- Pattern: Classic unbounded cache anti-pattern

To CONFIRMED: Run with memory profiler, verify cache grows unbounded under load
```

**RE Examples**:
```
VERIFIED: Binary is packed with UPX.

Evidence:
- Section names: UPX0, UPX1, UPX2
- Section entropy: All sections have entropy 7.99-8.00
- String: "UPX!" at file offset 0x40
- Import: No meaningful imports (packed stub only)

To CONFIRMED: Run `upx -d target` and verify it unpacks successfully
```

**Architecture Examples**:
```
VERIFIED: API version mismatch between frontend and backend.

Evidence:
- Frontend: Calls `/api/v2/users` (frontend/src/api.js:15)
- Backend: Only implements `/api/v1/users` (backend/routes.py:23)
- Error: 404 responses in production logs for `/api/v2/users`

To CONFIRMED: Deploy backend with v2 endpoint and verify frontend works
```

**When NOT to Use**:
- If the evidence is weak or indirect
- If there are major gaps in the evidence
- If the claim is speculative

**Pro Tip**: VERIFIED is the most common marker for well-executed analysis. It indicates "I'm very confident, but here's exactly what would make me certain."

---

### 3. SUSPECTED (70-90% Confidence)

**Use When**: You have strong signals pointing to a conclusion, but haven't confirmed it through direct evidence. The preponderance of evidence supports the claim, but there's room for doubt.

**Evidence Requirements**:
- Minimum 2-3 strong signals
- Signals are consistent with the claim
- No evidence directly contradicts the claim
- Direct confirmation would require additional work

**SWE Examples**:
```
SUSPECTED: Race condition in file_lock.py:17.

Signals:
1. Shared `self._lock = threading.Lock()` but not used in `write_data()`
2. `write_data()` performs file I/O without any synchronization
3. Method is called from multiple threads (thread_pool.py:45)
4. Pattern matches known race condition in similar codebases

To confirm:
- Add logging to track concurrent calls
- Run with ThreadSanitizer: `TSAN_OPTIONS="halt_on_error=0" python -m tsan file_lock.py`
- Or reproduce with concurrent test: 10 threads calling write_data() simultaneously
```

**RE Examples**:
```
SUSPECTED: Lumma stealer variant (v2.3).

Signals:
1. Mutex: `Global\\Lumma_v2_3_...` (matches Lumma v2.3 pattern)
2. Imports: `LsaOpenPolicy`, `CryptUnprotectData`, `LsaGetLogonSessionData` (Lumma signature)
3. Strings: 7/9 known Lumma C2 URI patterns present
4. Section entropy: .text=7.8, .rdata=7.6 (matches Lumma profiles)
5. Compile timestamp: 2024-03-15 (consistent with recent Lumma builds)

Not confirmed:
- No YARA match against published Lumma rules
- SHA-256 not in MalwareBazaar (e6e3f3c3...)
- No dynamic behavior confirmation

To confirm:
1. Submit SHA-256 to MalwareBazaar for family match
2. Run in instrumented VM, verify browser profile enumeration
3. Check for Lumma-specific registry keys (HKCU\Software\Lumma)
```

**RE Examples (Binary Analysis)**:
```
SUSPECTED: Custom packing scheme (not Themida, not UPX).

Signals:
1. High entropy in all sections (.text=7.95, .data=7.89, .rdata=7.92)
2. No standard packer signatures (UPX, Themida, VMProtect)
3. Custom section names: .custom1, .custom2, .custom3
4. Entry point jumps to decryption stub at 0x401000
5. String: "Custom Packer v1.0" in .rdata:0x405000

Not confirmed:
- Haven't successfully unpacked
- Haven't identified decryption algorithm
- Haven't recovered original entry point

To confirm:
1. Dynamic analysis: Run in x64dbg, breakpoint at OEP
2. Memory dump: Dump process memory after decryption
3. Static analysis: Analyze decryption stub at 0x401000
```

**Architecture Examples**:
```
SUSPECTED: Microservice boundary violation.

Signals:
1. user_service imports order_repository directly (user_service.py:8)
2. order_service imports user_repository directly (order_service.py:5)
3. Both services write to the same database tables
4. No API calls between services for shared data

Not confirmed:
- Haven't traced all code paths
- Haven't verified if this is intentional
- Haven't checked with service owners

To confirm:
1. Code review: Trace all cross-service data access
2. Architecture review: Check intended service boundaries
3. Stakeholder interview: Ask service owners about intended design
```

**When NOT to Use**:
- If you have only 1 signal
- If signals are weak or ambiguous
- If there's contradicting evidence

**Pro Tip**: SUSPECTED is your default marker when you have strong circumstantial evidence but lack the smoking gun. Always list what's missing and what would confirm.

---

### 4. HYPOTHESIS (50-70% Confidence)

**Use When**: You have a plausible explanation based on partial evidence, but it's not yet supported by strong signals. It's your best guess, but you acknowledge it might be wrong.

**Evidence Requirements**:
- Minimum 1-2 supporting observations
- Plausible mechanism connecting evidence to claim
- Multiple alternative explanations are possible
- Additional evidence could significantly change the assessment

**SWE Examples**:
```
HYPOTHESIS: The function at utils/crypto.py:42 is attempting AES decryption but has a key derivation bug.

Supporting observations:
1. Function name: `decrypt_aes()`
2. Uses `Cipher(AES.new(key, AES.MODE_CBC))` (PyCryptodome)
3. Key derivation: `key = hashlib.sha256(password).digest()` (only 32 bytes, but AES-256 needs 32-byte key)
4. IV: `iv = b'\x00' * 16` (all zeros IV is insecure)

Alternative explanations:
- This is intentionally weak crypto for testing
- The key derivation is correct and I'm misunderstanding AES requirements
- This is a different cipher that happens to use AES-like operations

To confirm:
1. Static: Verify key derivation produces valid AES-256 key
2. Dynamic: Test with known plaintext/ciphertext pair
3. Code review: Check if this is production code or test code
```

**RE Examples**:
```
HYPOTHESIS: The function at 0x401234 is the main decryption routine for C2 traffic.

Supporting observations:
1. Called from 7 locations, all in network-related functions
2. Takes 3 arguments: buffer, length, key (consistent with decryption)
3. Contains loop with xor instructions (common in decryption)
4. References .rodata:0x4080 which contains what looks like an S-box
5. Returns decrypted data to caller

Alternative explanations:
- This is a general-purpose crypto function, not specific to C2
- This is for decrypting configuration, not C2 traffic
- The xor loop is for something else (checksum, encoding)

To confirm:
1. Dynamic: Breakpoint at 0x401234, capture arguments during C2 communication
2. Static: Analyze the S-box at 0x4080 to identify algorithm
3. Memory: Dump memory before/after call to see transformation
```

**RE Examples (Anti-Analysis)**:
```
HYPOTHESIS: The binary uses VMProtect 3.x with custom handlers.

Supporting observations:
1. Section names: .vmp0, .vmp1, .vmp2 (VMProtect pattern)
2. Entry point: Jumps to 0x401000 which has VMProtect stub signature
3. String: "VMProtect" not present (custom build?)
4. Behavior: Crashes in non-VM environments (anti-VM?)

Alternative explanations:
- This is Themida with custom section names
- This is a custom packer mimicking VMProtect
- This is a different protection scheme entirely

To confirm:
1. Memory: Check for VMProtect IAT hooks
2. Strings: Search for VMProtect-specific strings in memory
3. Behavior: Test in various VM environments
4. Signature: Check for VMProtect-specific byte patterns
```

**Architecture Examples**:
```
HYPOTHESIS: The performance bottleneck is in the ORM layer's N+1 query problem.

Supporting observations:
1. API endpoint /users takes 2.5s average (slowest in the system)
2. Endpoint fetches user and then fetches all their orders
3. No JOIN in the query (separate queries for user and orders)
4. Pattern matches classic N+1 query anti-pattern

Alternative explanations:
- The slowness is in the database, not the ORM
- The slowness is in network latency
- The slowness is in serialization/deserialization

To confirm:
1. Profiling: Run with Django Debug Toolbar or similar
2. Query logging: Enable SQL query logging, count queries per request
3. Load testing: Test with different data sizes to verify N+1 scaling
```

**When NOT to Use**:
- If you have no supporting observations
- If the hypothesis is wild speculation
- If you can't define a test to confirm/refute

**Pro Tip**: HYPOTHESIS is your "working theory" marker. It's okay to have hypotheses in your analysis, but they must be clearly labeled and testable. Never present a hypothesis as fact.

---

### 5. UNVERIFIED (30-50% Confidence)

**Use When**: You need external information (documentation, runtime data, third-party tools) to verify the claim. The claim is plausible, but you lack the means to verify it yourself.

**Evidence Requirements**:
- Some evidence supporting the claim
- Clear statement of what external information is needed
- Explanation of why you can't verify it yourself

**SWE Examples**:
```
UNVERIFIED: This code uses Python 3.11-specific features.

Evidence:
- Syntax: Uses `exception group` (PEP 654, Python 3.11+)
- Type hints: Uses `Self` type (PEP 673, Python 3.11+)

To verify:
- Check runtime: `python --version` in production environment
- Check requirements: `cat requirements.txt | grep python`
- Check Dockerfile: `FROM python:3.x` version

Blocking: Don't have access to production environment to check Python version
```

**RE Examples**:
```
UNVERIFIED: This binary targets Windows 10 22H2 specifically.

Evidence:
- OS version check: Compares `dwMajorVersion` to 10, `dwMinorVersion` to 0, `dwBuildNumber` to 19045
- String: "Windows 10 22H2" in .rdata:0x40A000

To verify:
- Dynamic: Run on Windows 10 22H2, verify it works
- Static: Analyze the version check logic more carefully

Blocking: Don't have Windows 10 22H2 VM available for testing
```

**RE Examples (Compiler/Build)**:
```
UNVERIFIED: This Go binary was built with Go 1.21.5.

Evidence:
- Build info: `go:build` strings present
- Module path: `github.com/evil/c2` in build info

To verify:
- Run: `go version -m <binary>` to extract exact version
- Check: Build info section for compiler version

Blocking: Don't have Go toolchain installed in analysis environment
```

**Architecture Examples**:
```
UNVERIFIED: This API endpoint is used by the mobile app.

Evidence:
- Endpoint: `/api/mobile/v1/data` exists in backend
- CORS: Configured to allow mobile app origin

To verify:
- Check mobile app source code for API calls
- Check mobile app network traffic
- Ask mobile team for confirmation

Blocking: Don't have access to mobile app source code or team
```

**When NOT to Use**:
- If you have no evidence at all
- If the verification method is trivial (just do it)
- If you're just being lazy

**Pro Tip**: UNVERIFIED is for when you genuinely can't verify something with your available tools/access. Always state what would verify it and why you can't do it yourself.

---

### 6. BLOCKED (0-30% Confidence)

**Use When**: Required evidence is unavailable, and you cannot proceed with the analysis without it. The claim might be true or false, but you can't determine which.

**Evidence Requirements**:
- Clear statement of what evidence is needed
- Explanation of why it's unavailable
- Explanation of what would unblock the analysis
- Effort estimate to unblock

**SWE Examples**:
```
BLOCKED: Cannot determine if the SQL injection at user_search.py:23 is exploitable.

Blocking factor:
- No access to database schema to verify if the query is parameterizable
- No access to test environment to verify exploitability
- No knowledge of input validation in upstream layers

To unblock:
1. Get database schema (estimated effort: 1 hour, requires DBA access)
2. Set up test environment (estimated effort: 2 hours, requires devops)
3. Review upstream code (estimated effort: 30 minutes, requires code access)

Total effort to unblock: ~4 hours
```

**RE Examples**:
```
BLOCKED: Cannot determine the C2 protocol for this sample.

Blocking factor:
- Binary is packed with Themida (section .themida, entropy 7.95)
- Static analysis only sees the packer's stub
- Main payload is encrypted at rest, decrypted at runtime

To unblock:
1. Dynamic unpack: Run in isolated VM under x64dbg
2. Breakpoint: Set breakpoint at OEP (Original Entry Point)
3. Dump: Dump memory after decryption
4. Re-analyze: Run static analysis on the dump

Estimated effort: 4-6 hours
Required tools: x64dbg, isolated VM, memory dumping tools
```

**RE Examples (Obfuscation)**:
```
BLOCKED: Cannot analyze the .NET assembly due to ConfuserEx obfuscation.

Blocking factor:
- Assembly is obfuscated with ConfuserEx (detected by dnlib)
- Method names are random strings (e.g., `a.b()`)
- Control flow is obfuscated (junk code, opaque predicates)
- Strings are encrypted

To unblock:
1. De4dot: Run de4dot to deobfuscate (may not work for latest ConfuserEx)
2. Manual: Manually rename methods based on behavior
3. Dynamic: Run in dnSpy, use dynamic analysis
4. Memory: Dump memory after JIT compilation

Estimated effort: 6-8 hours
Success rate: ~60% (ConfuserEx is hard to fully deobfuscate)
```

**Architecture Examples**:
```
BLOCKED: Cannot assess the security of the authentication flow.

Blocking factor:
- No access to the authentication service source code
- No access to the identity provider configuration
- No access to production logs to verify behavior

To unblock:
1. Get source code access (estimated effort: 1 day, requires security clearance)
2. Get config access (estimated effort: 1 hour, requires ops access)
3. Get log access (estimated effort: 30 minutes, requires ops access)

Total effort to unblock: ~1.5 days
Alternative: Black-box testing (estimated effort: 2 days, lower confidence)
```

**When NOT to Use**:
- If you can proceed with partial information
- If the blocking factor is temporary (just wait)
- If you're just missing a tool (install it)

**Pro Tip**: BLOCKED findings are stoppers. They prevent you from completing the analysis. Always provide a clear path to unblock, including effort estimates and required resources.

---

### 7. INCONCLUSIVE (Conflicting Evidence)

**Use When**: Evidence points both ways, and you can't call it confidently either direction. The evidence is genuinely contradictory.

**Evidence Requirements**:
- Evidence supporting the claim
- Evidence contradicting the claim
- Explanation of why it's a tie
- What would resolve the conflict

**SWE Examples**:
```
INCONCLUSIVE: Whether the race condition in cache.py:45 is exploitable.

Evidence FOR exploitation:
1. Shared dict `self._cache = {}` is written by multiple threads
2. No locking mechanism is used
3. Dict operations are not atomic in Python (GIL doesn't help)
4. Pattern matches classic race condition

Evidence AGAINST exploitation:
1. GIL in CPython prevents true parallel execution
2. Dict operations are atomic at the C level in CPython
3. No observed race conditions in production (1 year of logs)
4. Load testing with 1000 concurrent requests showed no issues

Why it's a tie:
- Theoretical vulnerability exists (race condition)
- Practical exploitation may be prevented by GIL
- No evidence of actual exploitation

To resolve:
1. Test with PyPy (no GIL) to verify exploitability
2. Test with Jython/IronPython (no GIL) to verify exploitability
3. Review Python documentation on dict atomicity guarantees
4. Check if this is a CPython-specific implementation detail
```

**RE Examples**:
```
INCONCLUSIVE: Whether this binary is malware or legitimate software.

Evidence FOR malware:
1. High-entropy .text section (7.8) \u2192 suggests packing/obfuscation
2. No imports beyond kernel32 \u2192 suggests dynamic resolution (anti-analysis)
3. String: "http://evil[.]com/api/data" \u2192 known C2 domain pattern
4. Behavior: Creates persistence via Run key (HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run)

Evidence FOR legitimate:
1. Signed: Valid Authenticode signature from "Acme Corp"
2. PDB path: C:\\build\\acme_app\\release\\acme_app.pdb \u2192 suggests development artifact
3. Small file size: 15KB \u2192 unusual for malware (typically larger)
4. No AV detections: 0/60 on VirusTotal (scanned 2024-01-15)

Why it's a tie:
- Has malware-like characteristics (stealth, C2)
- Has legitimate characteristics (signature, PDB, size)
- Could be legitimate software with suspicious features
- Could be malware using stolen signature

To resolve:
1. Submit to VirusTotal with all engines enabled
2. Run in instrumented sandbox for behavioral analysis
3. Check certificate validity and signing chain
4. Contact Acme Corp to verify if this is their software
```

**RE Examples (Binary Type)**:
```
INCONCLUSIVE: Whether this is a 32-bit or 64-bit binary.

Evidence FOR 32-bit:
1. PE header: Machine = 0x014C (IMAGE_FILE_MACHINE_I386)
2. Section alignment: 0x1000 (typical for 32-bit)
3. Entry point: 0x401000 (32-bit address range)

Evidence FOR 64-bit:
1. Some instructions: `mov rax, rbx` (64-bit registers)
2. Address size: References above 4GB (0x100000000)
3. String: "x64" in .rdata:0x40A000

Why it's a tie:
- PE header says 32-bit but contains 64-bit instructions
- Could be a mixed-mode binary
- Could be a corrupted header
- Could be a custom format

To resolve:
1. Run `file <binary>` to check Linux file command
2. Run `objdump -f <binary>` to check objdump's assessment
3. Check if it runs on 32-bit and 64-bit systems
4. Analyze the actual instructions more carefully
```

**Architecture Examples**:
```
INCONCLUSIVE: Whether to use microservices or monolith for the new feature.

Evidence FOR microservices:
1. Team size: 15 developers \u2192 can handle microservice complexity
2. Existing: Current system is already microservices \u2192 consistent architecture
3. Scalability: Feature expected to scale independently \u2192 microservices better
4. Technology: Different tech stacks needed \u2192 microservices enable this

Evidence FOR monolith:
1. Feature size: Small feature (estimated 2 weeks) \u2192 monolith is simpler
2. Data: Heavy inter-service communication \u2192 monolith avoids network overhead
3. Team experience: Team has no microservice experience \u2192 learning curve
4. Deadline: Tight deadline (4 weeks) \u2192 monolith is faster to deliver

Why it's a tie:
- Both architectures have valid pros and cons
- Decision depends on long-term vs short-term priorities
- Team capabilities are a factor

To resolve:
1. Prototype: Build proof-of-concept in both architectures
2. Measure: Benchmark performance, development speed
3. Survey: Get team input on preference and capabilities
4. Decide: Make decision based on data, not opinion
```

**When NOT to Use**:
- If the evidence clearly supports one side
- If you're just missing information (use UNVERIFIED or BLOCKED)
- If you're being wishy-washy

**Pro Tip**: INCONCLUSIVE is for genuine ties. Don't use it as an excuse to avoid making a call. If the evidence slightly favors one side, use SUSPECTED or HYPOTHESIS instead.

---

## The "claim \u2192 marker \u2192 evidence \u2192 test" pattern

For every uncertain claim, use this four-part structure:

1. **State the claim** clearly (don't bury it)
2. **Mark the uncertainty** (use one of the 7 markers)
3. **Cite the evidence** that supports the claim
4. **State the test** that would confirm or refute

**Template**:
```
**[MARKER]**: [Claim]

**Evidence**:
- [Supporting evidence point 1]
- [Supporting evidence point 2]
- [Supporting evidence point 3]

**To confirm/refute**: [Specific test or action]
```

**Complete Examples**:

**SWE Example**:
```
**HYPOTHESIS**: The memory leak in data_processor.py is caused by the unbounded LRU cache.

**Evidence**:
- Cache initialized with `maxsize=None` (unbounded) at line 101
- Cache is populated in a loop that runs for every request
- No cache eviction logic exists in the codebase
- Memory usage grows linearly with request count (observed in staging)

**To confirm**: Run with memory profiler, verify cache size grows unbounded; then set maxsize=1000 and verify memory stabilizes.
```

**RE Example**:
```
**SUSPECTED**: This binary is Emotet malware.

**Evidence**:
- Mutex: `Global\\Emotet_...` (matches Emotet pattern)
- Imports: `InternetConnectA`, `HttpOpenRequestA`, `InternetReadFile` (Emotet network stack)
- Strings: 5/7 known Emotet C2 URI patterns
- Section entropy: .text=7.85 (matches Emotet)

**To confirm**: Submit SHA-256 (a1b2c3d4...) to MalwareBazaar; run in sandbox and verify Emotet-specific behavior (outlook email harvesting).
```

**Architecture Example**:
```
**BLOCKED**: Cannot determine if the database migration will cause downtime.

**Evidence**:
- Migration adds a column with a default value
- Table has 10M rows
- No index on the column being added

**To unblock**: Test migration on staging database with production-scale data; measure downtime during migration.
```

**Pro Tip**: This pattern ensures every uncertain claim is:
- **Clear**: The claim is stated upfront
- **Honest**: The uncertainty is marked
- **Supported**: Evidence is provided
- **Actionable**: The reader knows what to do next

---

## The "no hedging" rule

Don't use vague hedges. They make you sound uncertain and unprofessional. Instead, use the uncertainty markers.

**Hedging Words to Eliminate**:
| Don't Use | Use Instead | Example |
|-----------|-------------|---------|
| might | MARKER | SUSPECTED: ... |
| maybe | MARKER | HYPOTHESIS: ... |
| possibly | MARKER | UNVERIFIED: ... |
| could be | MARKER | BLOCKED: ... |
| seems like | MARKER | INCONCLUSIVE: ... |
| appears to be | MARKER | SUSPECTED: ... |
| probably | MARKER + % | SUSPECTED (80%): ... |
| perhaps | MARKER | HYPOTHESIS: ... |
| potentially | MARKER | SUSPECTED: ... |
| some | Specific | 3 of 5 modules |
| many | Specific | 15 instances |
| several | Specific | 7 locations |
| etc. | Complete list | A, B, C |
| and so on | Complete list | X, Y, Z |

**Bad vs Good**:

\u274c "This might be a SQL injection."
\u2705 "SUSPECTED SQL injection at user_search.py:23. Evidence: User input concatenated into query."

\u274c "There could possibly be a buffer overflow."
\u2705 "HYPOTHESIS: Buffer overflow in parse_input.c:47. Evidence: `strcpy(dst, src)` with unbounded `src`."

\u274c "This appears to be malware."
\u2705 "SUSPECTED malware. Evidence: 8/10 malware indicators present. To confirm: Submit to VirusTotal."

**Pro Tip**: Read your analysis out loud. If it sounds wishy-washy, you're probably hedging. Replace the hedging words with markers.

---

## The "confidence percentages" rule

Avoid percentage estimates ("90% confidence") unless you have data. They're usually fabricated and sound unprofessional.

**Bad**:
- \u274c "90% confidence this is malware"
- \u274c "75% sure there's a SQL injection"
- \u274c "This is probably (80%) a buffer overflow"

**Good**:
- \u2705 "SUSPECTED malware (strong signals but needs confirmation)"
- \u2705 "P0 SQL injection (verified through static and dynamic analysis)"
- \u2705 "HYPOTHESIS: Buffer overflow (plausible but needs testing)"

**When Percentages ARE Acceptable**:
- When you have statistical data: "95% of samples with this mutex are Lumma"
- When you have measured data: "80% of requests to this endpoint fail"
- When you have survey data: "70% of developers reported this issue"

Even then, pair percentages with markers: "SUSPECTED (80% of similar samples match): ..."

---

## The "say what you don't know" rule

Explicit limitations build trust. Don't pretend to know things you don't. The reader will find out eventually, and your credibility will suffer.

**What to Document**:
- What you didn't verify
- What you couldn't access
- What you didn't test
- What assumptions you made
- What external information you relied on

**Limitations Section Template**:
```
## Limitations

This analysis is based on:
- [X] Static analysis of the code/binary
- [ ] Dynamic analysis in a sandbox
- [ ] Dynamic analysis in a full VM
- [ ] Manual code review
- [ ] Automated scanning

This analysis did NOT include:
- Dynamic behavior verification (no execution environment provided)
- Full codebase review (only critical paths analyzed)
- Dependency analysis (external libraries not reviewed)
- Production environment testing (only staging tested)

Assumptions made:
1. The code/binary provided is the production version
2. No additional input validation exists upstream
3. The analysis environment is representative of production

External information relied upon:
- VirusTotal scan results (SHA-256: a1b2c3...)
- OWASP Cheat Sheets for best practices
- Vendor documentation for API behavior

To strengthen this analysis:
1. Provide a dynamic analysis environment
2. Grant access to the full codebase
3. Provide production configuration details
4. Share any available threat intelligence
```

**Pro Tip**: The limitations section is not a sign of weakness. It's a sign of professionalism. Good analysts know their limits; great analysts document them.

---

## The "no false confidence" rule

Worst sin: high confidence on weak evidence. This destroys credibility faster than anything else.

**False Confidence Examples**:

\u274c "This binary is definitely ransomware." (no evidence cited)
\u2705 "SUSPECTED ransomware based on:
> - `vssadmin delete shadows` string in `.rodata:0x4080`
> - File extension enumeration loop at 0x401234
> - RSA-2048 public key at 0x4090A0
>
> To confirm: dynamic execution \u2014 verify shadow copies are deleted and files are encrypted with the observed public key."

The first is bluff. The second is the same conclusion with evidence and uncertainty.

**Why False Confidence is Bad**:
1. **Credibility Loss**: When you're wrong, the reader loses trust in ALL your findings
2. **Decision Risk**: Readers act on high-confidence findings; bad decisions result
3. **Reputation Damage**: Word spreads that your analysis is unreliable
4. **Career Impact**: Repeated false confidence can end careers

**How to Avoid False Confidence**:
1. Always ask: "What evidence do I have?"
2. Always ask: "What evidence am I missing?"
3. Always ask: "What would change my assessment?"
4. Always use uncertainty markers when in doubt
5. Always document your limitations

**Pro Tip**: Use the "Bet Test". If you wouldn't bet $100 on your finding being correct, you shouldn't mark it as CONFIRMED or VERIFIED.

---

## The "verifiable test" rule

The "test that would confirm" should be verifiable \u2014 the reader should be able to run it and get the same result.

**Bad Tests**:
- \u274c "To confirm: more analysis needed."
- \u274c "To confirm: investigate further."
- \u274c "To confirm: check it out."

**Good Tests**:
- \u2705 "To confirm: run `python scripts/re_disasm.py --file <target> --function sub_401234` and verify the call to `decrypt_aes` at offset 0x40125C."
- \u2705 "To confirm: submit SHA-256 (a1b2c3d4e5f6...) to VirusTotal and verify 3+ AV detections as Lumma."
- \u2705 "To confirm: set breakpoint at 0x401234 in x64dbg, run the binary, and verify it receives encrypted C2 traffic."

**Test Requirements**:
- Specific command or action
- Expected output or result
- Estimated time to complete
- Required tools/access

**Pro Tip**: Always test your tests. If you provide a command, run it yourself first to make sure it works. If you provide a method, try it yourself if possible.

---

## The "don't bury limitations" rule

Limitations go in a section of their own, not buried in footnotes or scattered throughout the report.

**Bad**:
```
Some findings might not be accurate because I didn't have access to the production environment.
```

**Good**:
```
## Limitations

**Access Limitations**:
- No access to production environment
- No access to database schema
- No access to third-party service configurations

**Methodology Limitations**:
- Static analysis only (no dynamic verification)
- Automated scanning only (no manual review)
- Sample analysis only (no full codebase review)

**Assumptions**:
- Code provided is production version
- No additional input validation exists
- Analysis environment is representative

**Impact on Findings**:
- Security findings may miss upstream mitigations
- Performance findings may not reflect production behavior
- Architecture findings may not account for all constraints
```

**Placement**: Limitations section should come:
1. After the findings
2. Before the recommended next steps
3. As a top-level section (not a subsection)

**Pro Tip**: The limitations section is your "get out of jail free" card. If a finding turns out to be wrong, you can point to the limitations that prevented you from catching it. But this only works if the limitations are honest and comprehensive.

---

## Uncertainty Marker Decision Tree

Use this decision tree to choose the right marker:

```
Is the claim verified through multiple independent methods?
│
├─ Yes \u2192 CONFIRMED
│
No \u2192 Is there strong evidence from one method?
│
├─ Yes \u2192 VERIFIED
│
No \u2192 Do you have multiple strong signals?
│
├─ Yes \u2192 SUSPECTED
│
No \u2192 Do you have some supporting evidence?
│
├─ Yes \u2192 HYPOTHESIS
│
No \u2192 Do you need external information?
│
├─ Yes \u2192 UNVERIFIED
│
No \u2192 Is evidence unavailable?
│
├─ Yes \u2192 BLOCKED
│
No \u2192 Is evidence conflicting?
│
├─ Yes \u2192 INCONCLUSIVE
│
No \u2192 You shouldn't be making this claim
```

---

## Uncertainty Marker Cheat Sheet

| Situation | Marker | Example |
|-----------|--------|---------|
| Multiple verifications | CONFIRMED | CONFIRMED: SQLi at line 23 (static + dynamic + code review) |
| Strong single verification | VERIFIED | VERIFIED: Packed with UPX (section names + entropy + strings) |
| Strong signals, needs confirmation | SUSPECTED | SUSPECTED: Emotet malware (mutex + imports + strings) |
| Plausible, partial evidence | HYPOTHESIS | HYPOTHESIS: AES decryption at 0x401234 (S-box + xor loop) |
| Needs external info | UNVERIFIED | UNVERIFIED: Go 1.21.5 (need `go version -m`) |
| Evidence unavailable | BLOCKED | BLOCKED: C2 protocol (packed binary) |
| Conflicting evidence | INCONCLUSIVE | INCONCLUSIVE: Malware vs legitimate (signals both ways) |

---

## Common Uncertainty Scenarios and How to Handle Them

### Scenario 1: You Found Something Suspicious But Aren't Sure

**Bad**: "This looks like it might be malware."

**Good**: "SUSPECTED malware. Evidence: [list signals]. To confirm: [specific test]."

**Why**: The marker (SUSPECTED) conveys your confidence level. The evidence supports your assessment. The test tells the reader what to do next.

### Scenario 2: You Can't Verify Something Important

**Bad**: "I couldn't check if this is exploitable."

**Good**: "UNVERIFIED: Exploitability of SQLi at user_search.py:23. To verify: Test with `' OR '1'='1` in staging environment. Blocking: No staging access."

**Why**: The marker (UNVERIFIED) is honest. The test is specific. The blocking factor is documented.

### Scenario 3: You're Completely Stuck

**Bad**: "I don't know what this does."

**Good**: "BLOCKED: Cannot determine function purpose at 0x401234. Blocking: Function is in packed section, no xrefs found. To unblock: Unpack binary and re-analyze."

**Why**: The marker (BLOCKED) is clear. The blocking factor is specific. The path forward is actionable.

### Scenario 4: Evidence Points Both Ways

**Bad**: "This could be malware or it could be legitimate."

**Good**: "INCONCLUSIVE: Malware vs legitimate software. Evidence FOR: [list]. Evidence AGAINST: [list]. Why tie: [explain]. To resolve: [specific actions]."

**Why**: The marker (INCONCLUSIVE) is accurate. Both sides are presented. The conflict is explained. The resolution path is clear.

### Scenario 5: You Have a Theory But No Proof

**Bad**: "I think this is what's happening."

**Good**: "HYPOTHESIS: [theory]. Evidence: [supporting observations]. Alternative explanations: [list]. To confirm: [test]."

**Why**: The marker (HYPOTHESIS) signals this is unproven. The evidence shows your reasoning. The alternatives show you've considered other possibilities. The test is actionable.

---

## Uncertainty Marker Anti-Patterns

### Anti-Pattern 1: Overusing CONFIRMED/VERIFIED

**Problem**: Marking everything as high confidence when you haven't verified it.

**Signs**:
- Most findings are CONFIRMED or VERIFIED
- Little to no evidence provided
- No uncertainty markers used

**Fix**: Be more honest about your confidence levels. Use SUSPECTED and HYPOTHESIS more often.

### Anti-Pattern 2: Underusing Uncertainty Markers

**Problem**: Not marking uncertainty at all, or using vague language instead.

**Signs**:
- Use of hedging words (might, maybe, possibly)
- No uncertainty markers in the report
- Findings that sound wishy-washy

**Fix**: Replace hedging words with specific markers. Mark every uncertain claim.

### Anti-Pattern 3: Using Markers Incorrectly

**Problem**: Using CONFIRMED when you only have SUSPECTED-level evidence.

**Signs**:
- CONFIRMED findings with only 1 evidence source
- SUSPECTED findings with strong, verified evidence
- HYPOTHESIS findings with no supporting evidence

**Fix**: Re-evaluate your evidence. Use the decision tree to choose the right marker.

### Anti-Pattern 4: Not Explaining the Marker

**Problem**: Using a marker without explaining what it means or why you chose it.

**Signs**:
- Marker used without evidence
- Marker used without explanation of what would confirm
- Reader doesn't understand your confidence level

**Fix**: Always pair markers with evidence and next steps.

### Anti-Pattern 5: Ignoring Contradictory Evidence

**Problem**: Presenting only the evidence that supports your claim, ignoring evidence that contradicts it.

**Signs**:
- No mention of alternative explanations
- No discussion of evidence that doesn't fit
- Findings that seem one-sided

**Fix**: Acknowledge all evidence, even if it contradicts your assessment. Use INCONCLUSIVE if the evidence is genuinely conflicting.

---

## The Uncertainty Marker Review Process

Before finalizing any analysis, review your uncertainty markers:

1. **Check every marker**: Does it accurately reflect your confidence level?
2. **Check every evidence list**: Is it complete? Are there gaps?
3. **Check every test**: Is it specific and actionable?
4. **Check for missing markers**: Are there uncertain claims without markers?
5. **Check for overconfidence**: Are you using CONFIRMED/VERIFIED too much?

**Marker Review Checklist**:
- [ ] Every uncertain claim has a marker
- [ ] Every marker has supporting evidence
- [ ] Every marker has a confirm/refute test
- [ ] Markers are used consistently
- [ ] No hedging words are used
- [ ] Limitations are documented
- [ ] Confidence levels seem appropriate

---

## Output

Every uncertain claim in the report should be marked with one of the 7 markers and include:
1. The marker (CONFIRMED, VERIFIED, SUSPECTED, HYPOTHESIS, UNVERIFIED, BLOCKED, INCONCLUSIVE)
2. The claim
3. The evidence supporting the claim
4. The test that would confirm or refute the claim

Without the marker, the reader assumes high confidence. Without the test, the reader can't act on the uncertainty.

The disciplined version:

> "**SUSPECTED**: AES-128 used by the binary.
>
> **Evidence**: `.rodata:0x4040` contains the AES S-box (verified: bytes 63 7c 77 7b f2 6b 6f c5 ...). The function at 0x401234 references this address and contains an `xor` loop consistent with AES MixColumns.
>
> **To confirm**: emulate the function with Unicorn using a known AES test vector; verify the output matches the expected ciphertext."

Three parts. Clean. Honest. Actionable.

**Remember**: Uncertainty is not a sign of weakness. It's a sign of intellectual honesty. The best analysts are not those who are always right, but those who are honest about when they might be wrong.
