# Evidence vs Assertion — What Counts as Proof

The single biggest quality gap between a junior and senior analyst is **the discipline of evidence**. Juniors assert; seniors prove. The report you write should be unreadable to a skeptic — every claim should have a citation, an offset, a line number, a call site that the reader can verify.

## The rule

> Every claim in the report must point to a specific, verifiable artifact.

If the reader cannot open the file at the line you cite, or disassemble the binary at the offset you cite, and see what you claim is there — **the claim is not a finding**. It's a hypothesis, and hypotheses get marked as such.

## Three classes of claims — and the evidence each requires

| Class | Definition | Required evidence | If missing |
|-------|------------|---------------------|-----------|
| **Finding** | A concrete statement about behavior, structure, or defect | Byte/offset (RE) or file:line (SWE) + the artifact the reader can independently verify | Becomes a hypothesis — moves to "Suspected" section |
| **Hypothesis** | A best guess grounded in partial evidence | The partial evidence + a stated test that would confirm/refute | Becomes speculation — omit or mark explicitly |
| **Observation** | A non-actionable observation worth noting | The artifact the observation refers to | Stays in "Observations" section — no recommendation attached |

A report that confuses these three classes is unreadable. A finding that's actually a hypothesis erodes trust in the rest of the report.

## What counts as evidence

| Claim type | Evidence | Example |
|------------|----------|---------|
| "This buffer overflows" | Source line + the unsafe API + the size mismatch | `file.c:47: strcpy(dst, src); dst is 16 bytes, src is user input` |
| "This binary uses AES" | Offset of the S-box in `.rodata` | `.rodata:0x4040: 63 7c 77 7b f2 6b 6f c5 ...` (AES S-box) |
| "This binary calls socket()" | Disasm of the call instruction | `0x401234: call socket@plt` |
| "The C2 is 1.2.3.4" | Offset of the string + extraction command | `.rodata:0x4080F0: "1.2.3.4" (strings -a binary \| grep ...)` |
| "This is a Lumma variant" | Mutex name match + import set match + string set match | Mutex `Global\Lumma_v2_...` matches known Lumma pattern; 7 of 9 known Lumma imports present; 3 of 4 known Lumma C2 URI patterns in strings |
| "This refactor would help" | Recent commits showing repeated changes to the same code | `git log --oneline -- file.py` shows 14 commits in last 20 PRs touching this file's switch statement |
| "This is dead code" | grep result showing zero references (after alias / re-export check) | `rg "functionName"` returns 1 hit (the definition); checked aliases, re-exports, reflection — none found |
| "This is a SQLi" | Source line + the unsafe pattern + the user-controlled input path | `file.py:23: cursor.execute(f"SELECT ... WHERE id = {user_id}")`; `user_id` from `request.args.get('id')` at line 12 |
| "This is a race condition" | Both threads' access paths + the unprotected shared state + the interleaving that triggers it | `account.go:47` goroutine A reads `balance`; `account.go:53` goroutine B writes `balance`; no mutex covers both; interleaving produces lost update |
| "This is an anti-debug" | The instruction sequence + the API check + the conditional branch on the result | `0x401020: call IsDebuggerPresent; 0x401025: test eax,eax; 0x401027: jnz 0x402000` |
| "This function is O(n²)" | The loop nesting + the per-iteration cost | `file.py:12-19: for i in items: for j in items: ...` (n × n iterations) |

## What does NOT count as evidence

| Claim type | Why it's not evidence | Fix |
|-----------|------------------------|-----|
| "This looks fragile" | Subjective — no concrete consequence | Find the bug class, point to the line, name the consequence |
| "This is bad practice" | Pattern preference — no material cost | Find the cost (correctness, maintenance, perf) and cite it |
| "I think it does X" | Hypothesis without proof | Mark as hypothesis; propose a test to confirm |
| "Common pattern" | No specific reference | Cite the specific source (function name, import, offset) |
| "Probably malware" | Vague — what specifically? | List the specific indicators that point to malware |
| "Should be refactored" | No bounded recommendation | Specify the extraction / change, LOC estimate, PR shape |
| "Looks like ransomware" | Family attribution without specifics | Cite the specific family signals (extension list, ransom note template, mutex name, encryption API sequence) |
| "This is inefficient" | No measured or theoretical cost | Profile or reason from the algorithm; cite the loop or the allocation pattern |
| "Likely vulnerable" | Speculation about exploitability | Show the input path + the sink + the missing check; mark exploitability as separate hypothesis if you can't PoC |
| "May have a memory leak" | Hedged claim with no path | Show the allocation + the missing free path; cite the call chain |

## The "show me the bytes" / "show me the lines" rule

In RE work, every claim about behavior must cite **a byte** (offset in the binary, instruction, call target). In SWE work, every claim about code must cite **a line** (file:line: the actual code).

A report without byte/line citations is not analysis; it's opinion.

### Byte citation format (RE)

Standardize on this format:

```
0x401234: ff 15 18 30 00 00    call   rax   ; rax = CreateRemoteThread (IAT entry at 0x405030)
```

The format is: `offset: bytes    instruction   ; annotation`. The annotation explains what the bytes mean — what `rax` actually holds, which IAT entry, which string. Without the annotation, the reader has to re-do your work.

When citing a string in `.rodata`:

```
.rodata:0x4080F0: "1.2.3.4"   ; C2 IP (string found via `strings -a binary | grep -E '^\d+\.\d+\.\d+\.\d+$'`)
```

When citing a function in disassembly:

```
sub_401000 (0x401000-0x4010F4):
  prologue: push rbp; mov rbp,rsp; sub rsp,0x40
  body:     0x40100A: call sub_401200
            0x40100F: mov [rbp-0x10], rax
            ...
  epilogue: mov rsp,rbp; pop rbp; ret
```

### Line citation format (SWE)

Standardize on this format:

```
file.py:23:    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
file.py:12:    user_id = request.args.get('id')   # source of user-controlled input
```

Always cite the source of input and the sink in the same finding. A SQLi claim that shows only the f-string but not where `user_id` comes from is half-evidenced.

For multi-file flows, list all relevant lines:

```
controllers/user.py:12:  user_id = request.args.get('id')
controllers/user.py:23:  user = db.query(User, user_id)   # flows into ORM
services/user.py:47:     cursor.execute(f"... WHERE id = {user_id}")   # sink
```

## The "before / after" pattern

For SWE findings, show the current code and the proposed change side by side:

```
Current (file.py:23):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

Recommended:
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

This is concrete, reviewable, and easy to verify. "Use parameterized queries" without showing the change is lecture, not analysis.

## The "consequence first" pattern

Lead with the consequence, then the evidence:

❌ "The binary calls CreateRemoteThread (0x401234). It also imports WriteProcessMemory and VirtualAllocEx."
✅ "The binary performs process injection (P0). Evidence: at 0x401234 it calls `CreateRemoteThread` with the target process handle obtained via `OpenProcess` at 0x401200; the payload is written via `WriteProcessMemory` at 0x40125C after `VirtualAllocEx` at 0x40124A allocates RWX memory in the target."

The second version is denser, but it tells the reader: what the finding is (process injection), how severe (P0), and the exact instruction flow that proves it.

## The "uncertainty markers" rule

When you don't have proof, say so explicitly. Use:

- `HYPOTHESIS` — best guess based on partial evidence; needs more work to confirm
- `SUSPECTED` — strong signals but not confirmed
- `UNVERIFIED` — would need external docs / runtime to confirm
- `BLOCKED` — required evidence is unavailable; what would unblock?
- `INCONCLUSIVE` — evidence points both ways; can't call it

Don't bluff. If you say "the binary uses AES" and the reader disassembles it and finds no S-box, you've lost all credibility on the rest of the report.

## The "reject your own finding" rule

Before finalizing a finding, try to refute it:

- Could the offset be misread?
- Could the import be present but unused?
- Could the "dead code" actually be called via reflection?
- Could the "buffer overflow" actually be safe because of an upstream bounds check?
- Could the "missing auth" be enforced by middleware you didn't see?
- Could the "race condition" actually be prevented by an upstream lock?
- Could the "SQLi" actually be blocked by an input validator earlier in the request pipeline?
- Could the "dead code" actually be exported as a public API of a library?
- Could the "memory leak" actually be handled by a cleanup hook you missed?

If you can refute it, fix your analysis. If you can't, ship it. The findings that survive your own scrutiny are the ones that survive the user's.

## The "verifiability" rule

Every claim should be **checkable by the reader in under 5 minutes**. They open the file at the line, or disassemble at the offset, or run the grep command, and see what you claimed. If they can't, your claim is unverifiable.

A finding that can't be verified in 5 minutes is asking the reader to trust you. They shouldn't have to.

### The 5-minute verifiability test

For each finding, ask:

1. Can the reader open the cited file at the cited line and see the cited code?
2. Can the reader run the cited disassembly command and see the cited bytes?
3. Can the reader run the cited grep / strings / objdump command and see the cited output?
4. If the reader needs additional tooling (Ghidra, IDA, Unicorn), is it free or trial-available?
5. Does the cited evidence require specialized knowledge to interpret, or is it self-evident?

If any of these is "no", the finding fails the 5-minute test. Rewrite the evidence to make it verifiable, or downgrade to hypothesis.

## The "no decorative citations" rule

Don't cite URLs that don't directly support the finding. "See OWASP top 10" with a link to the OWASP homepage is decorative — it doesn't help the reader fix the bug. "See OWASP SQL Injection Prevention Cheat Sheet, section 'Use of Prepared Statements'" is specific and useful.

Open the link yourself before citing it. Verify it supports the mechanism you're proposing, not just the general defect category. If it doesn't, find a better source or omit.

A decorative citation signals "I don't actually know, but here's a general reference." That's worse than no citation.

## The "concrete command, concrete output" rule

When you cite evidence from a tool run, include the command and the relevant output:

```
$ objdump -d binary | grep -A2 "call.*CreateRemoteThread"
401234: ff 15 18 30 00 00    call   rax   ; rax = CreateRemoteThread from IAT
40123a: ...
```

This is verifiable — the reader runs the same command, gets the same output. "I ran objdump and found suspicious calls" is unverifiable.

### Standard command templates

| Need | Command |
|------|---------|
| Find imports in PE | `python -c "import pefile; pe=pefile.PE('sample.exe'); [print(e.dll, e.name) for e in pe.DIRECTORY_ENTRY_IMPORT]"` |
| Find imports in ELF | `readelf -d binary \| grep NEEDED` |
| Strings (ASCII) | `strings -a binary \| head -50` |
| Strings (UTF-16) | `strings -el binary \| head -50` |
| Disassemble function | `objdump -d binary \| grep -A 20 "<function_name>:"` |
| Section dump | `objdump -s -j .rodata binary \| head -50` |
| All calls in binary | `objdump -d binary \| grep "call.*@"` |
| All functions in stripped binary | `python -c "import capstone; ..."` (see `scripts/re_disasm.py`) |
| Hash of file | `sha256sum binary` |
| YARA scan | `yara -r rule.yar binary` |
| Find Go buildinfo | `go version -m binary` (if Go) |
| Find Rust panic table | `objdump -s -j .rustc-test-or-similar binary` (Rust-specific; see `rust-binary-recovery.md`) |

When citing, include the command (so the reader can run it) and the output you got. Both. Not just the output.

## The "evidence sufficiency matrix" — by claim severity

| Claim severity | Minimum evidence |
|---------------|-----------------|
| P0 (critical — RCE, data destruction, financial loss) | Two independent evidence types (e.g., disasm + bytes-in-memory, source + input-flow, import-set + behavior-trace) |
| P1 (high — priv-esc, data exfil, authentication bypass) | One strong evidence type + one corroborating signal |
| P2 (medium — info disclosure, DoS, anti-pattern) | One strong evidence type OR two corroborating signals |
| P3 (low — code smell, doc drift, minor inefficiency) | One evidence type; may be a single line or offset |

Higher severity claims need more evidence. A P0 with a single line citation is under-evidenced — find the corroborating input flow, the lack of bounds check, the absence of authentication, and cite all of it.

## The "evidence collection plan" — pre-analysis

Before writing the report, list the evidence you need to collect per finding:

```
Finding: Process injection in sample.exe (P0)
Evidence needed:
  [x] IAT entry for CreateRemoteThread / WriteProcessMemory / VirtualAllocEx / OpenProcess
  [x] Disasm of the call sequence (offset → offset → offset)
  [x] Allocation of RWX memory in target process (PAGE_EXECUTE_READWRITE = 0x40)
  [x] Source of the target PID (command-line arg? hardcoded? parent process?)
  [ ] Confirmation of payload delivery (dynamic run with API monitor) — UNVERIFIED, blocked on dynamic environment
```

Mark each piece as collected (`[x]`) or pending (`[ ]`). When writing the finding, only cite what's collected; mark the rest as `UNVERIFIED` or `BLOCKED` per the uncertainty markers rule.

## The "evidence chain" rule — for multi-step findings

Multi-step findings (process injection, ROP chain, command-and-control sequence) need an evidence chain — not just isolated citations.

```
Finding: Process injection (P0)
Chain:
  1. 0x401200: OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid) → handle hProc
  2. 0x40124A: VirtualAllocEx(hProc, NULL, 0x1000, MEM_COMMIT, PAGE_EXECUTE_READWRITE) → addr
  3. 0x40125C: WriteProcessMemory(hProc, addr, payloadBuf, 0x1000, &bytesWritten)
  4. 0x401234: CreateRemoteThread(hProc, NULL, 0, addr, NULL, 0, &tid)
```

Each link cites an offset. The chain shows the cause-and-effect — what makes this injection, not just "calls to suspicious APIs."

A list of isolated API calls is a survey; a chain is a finding.

## The "comparative evidence" rule — for family attribution

When attributing a binary to a malware family, don't cite a single signal — cite a comparison:

```
Finding: Sample attributed to LummaC2 (SUSPECTED, 78% confidence)
Comparative evidence:
  - Mutex name `Global\Lumma_v2_<8 hex chars>` matches LummaC2 mutex pattern (12/12 chars)
  - Import set: 7/9 known LummaC2 specific imports present
  - 3/4 known LummaC2 C2 URI patterns in strings
  - Missing 2 imports (cannot confirm build completeness) — UNVERIFIED
  - Different C2 IP from known LummaC2 campaigns — could be new infra
Confidence: 78% (3-of-4 signals match, but missing 2 imports)
```

The comparison shows: what the family template expects, what the sample has, what's missing. The reader can verify each line independently.

## The "self-citation" rule — citing your own previous findings

When a finding builds on a previous finding in the same report, cite the earlier finding by number:

```
Finding #3: Process injection (P0) — see Finding #1 for the API chain.
Finding #5: Persistence via Run key (P1) — depends on the injected process (Finding #3) surviving reboot.
```

This makes the report's logical structure scannable. The reader sees the dependency chain without re-reading.

## The "evidence expiration" rule — for runtime traces

Dynamic evidence (memory dumps, API traces, network captures) has a short shelf-life. If the reader can't reproduce the same environment, they can't verify the same trace.

For dynamic evidence, always cite:

1. The environment (VM type, OS version, patch level, tooling versions) — per the static-vs-dynamic `meta` rule
2. The exact command used to capture
3. The hash of the captured artifact (so the reader can verify they have the same data)
4. The time of capture (some behaviors are time-dependent — time bombs, jittered C2 beaconing)

Without these, a dynamic trace is "trust me." With them, it's verifiable.

## The "no evidence laundering" rule

Don't cite a tool's output as evidence if you don't understand what the tool measured.

Example: "VirusTotal reports 47/72 detections — therefore malware." You don't know what those 47 engines flagged. They could be heuristic false positives on the packer, not the payload. Cite the specific detection names if you understand them; otherwise, mark `SUSPECTED` and explain the limitation.

Same for: BehaveLike analyses, ML classifiers, "this looks like" auto-annotations. They are signals, not findings. A signal becomes a finding when you've verified the mechanism yourself.

## The "evidence sufficiency for negative claims" rule

Negative claims ("the binary does NOT connect to network", "this code is NOT vulnerable to SQLi") need the same evidence standard as positive claims.

"This binary doesn't have network capability" requires:
- Empty / minimal network imports (no `ws2_32.dll`, no `socket`, no `connect`)
- No network-related strings (URLs, IPs, user-agents)
- No `connect`/`send`/`recv` calls in disasm
- No dynamic network activity observed

All four. A single "I didn't see network imports" is under-evidenced — the binary could resolve APIs dynamically, or use raw syscalls, or have network code in an unpacked section.

Negative claims are stronger when they say "I checked these 4 evidence sources and found zero matches"; they're weak when they say "I didn't see anything."

## Final hook

> "If the reader can't open the file or disassemble the offset and see what I claim, my finding is a hypothesis, not a finding. Hypotheses don't go in the findings table."

## Verification checklist — for the agent before submitting a report

Before marking the report as final, run this self-check:

- [ ] Every Finding cites a byte (RE) or file:line (SWE)
- [ ] Every P0/P1 finding has at least two independent evidence types
- [ ] Every multi-step finding has an evidence chain (offset → offset → offset), not isolated citations
- [ ] Every family attribution has a comparative evidence table (template fields vs sample fields)
- [ ] Every claim without proof is marked `HYPOTHESIS` / `SUSPECTED` / `UNVERIFIED` / `BLOCKED` / `INCONCLUSIVE` — not left bare
- [ ] Every negative claim ("does NOT do X") has the 4-source evidence checklist
- [ ] No decorative citations — every URL opens to a page that supports the specific mechanism
- [ ] Every cited tool command includes both the command AND the output you got
- [ ] Every dynamic evidence cites the environment (VM, OS, tooling, hash, time)
- [ ] Findings list tried-to-refute — for each, the rejection attempt is documented in the analysis notes (not necessarily in the report itself, but in the work log)
- [ ] No "evidence laundering" — tool outputs cited only when the mechanism they measured is understood
- [ ] 5-minute verifiability test passed on every finding — a stranger with the binary/source and the cited tools can confirm in under 5 minutes

If any checkbox is unchecked, the report is a draft. Fix before submission.
