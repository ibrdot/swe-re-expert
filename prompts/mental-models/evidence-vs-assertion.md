# Evidence vs Assertion — What Counts as Proof

The single biggest quality gap between a junior and senior analyst is **the discipline of evidence**. Juniors assert; seniors prove. The report you write should be unreadable to a skeptic — every claim should have a citation, an offset, a line number, a call site that the reader can verify.

## The rule

> Every claim in the report must point to a specific, verifiable artifact.

If the reader cannot open the file at the line you cite, or disassemble the binary at the offset you cite, and see what you claim is there — **the claim is not a finding**. It's a hypothesis, and hypotheses get marked as such.

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

## What does NOT count as evidence

| Claim type | Why it's not evidence | Fix |
|-----------|------------------------|-----|
| "This looks fragile" | Subjective — no concrete consequence | Find the bug class, point to the line, name the consequence |
| "This is bad practice" | Pattern preference — no material cost | Find the cost (correctness, maintenance, perf) and cite it |
| "I think it does X" | Hypothesis without proof | Mark as hypothesis; propose a test to confirm |
| "Common pattern" | No specific reference | Cite the specific source (function name, import, offset) |
| "Probably malware" | Vague — what specifically? | List the specific indicators that point to malware |
| "Should be refactored" | No bounded recommendation | Specify the extraction / change, LOC estimate, PR shape |

## The "show me the bytes" / "show me the lines" rule

In RE work, every claim about behavior must cite **a byte** (offset in the binary, instruction, call target). In SWE work, every claim about code must cite **a line** (file:line: the actual code).

A report without byte/line citations is not analysis; it's opinion.

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

If you can refute it, fix your analysis. If you can't, ship it. The findings that survive your own scrutiny are the ones that survive the user's.

## The "verifiability" rule

Every claim should be **checkable by the reader in under 5 minutes**. They open the file at the line, or disassemble at the offset, or run the grep command, and see what you claimed. If they can't, your claim is unverifiable.

A finding that can't be verified in 5 minutes is asking the reader to trust you. They shouldn't have to.

## The "no decorative citations" rule

Don't cite URLs that don't directly support the finding. "See OWASP top 10" with a link to the OWASP homepage is decorative — it doesn't help the reader fix the bug. "See OWASP SQL Injection Prevention Cheat Sheet, section 'Use of Prepared Statements'" is specific and useful.

Open the link yourself before citing it. Verify it supports the mechanism you're proposing, not just the general defect category. If it doesn't, find a better source or omit.

## The "concrete command, concrete output" rule

When you cite evidence from a tool run, include the command and the relevant output:

```
$ objdump -d binary | grep -A2 "call.*CreateRemoteThread"
401234:	ff 15 18 30 00 00    call   rax   ; rax = CreateRemoteThread from IAT
40123a:	...
```

This is verifiable — the reader runs the same command, gets the same output. "I ran objdump and found suspicious calls" is unverifiable.

## Final hook

> "If the reader can't open the file or disassemble the offset and see what I claim, my finding is a hypothesis, not a finding. Hypotheses don't go in the findings table."
