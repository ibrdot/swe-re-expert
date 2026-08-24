# Uncertainty Markers — How to Be Honest Without Sounding Weak

The skill of marking uncertainty precisely. Senior analysts don't hedge ("might be, maybe, possibly") — they mark uncertainty with specific, actionable labels.

## The 5 uncertainty markers

Use these consistently:

| Marker | Meaning | What to do |
|--------|---------|-------------|
| `HYPOTHESIS` | Best guess based on partial evidence; needs more work to confirm | State the hypothesis + the test that would confirm |
| `SUSPECTED` | Strong signals but not confirmed | List the signals + what would confirm |
| `UNVERIFIED` | Would need external docs / runtime to confirm | Note what external info is needed |
| `BLOCKED` | Required evidence is unavailable | Explain what would unblock |
| `INCONCLUSIVE` | Evidence points both ways; can't call it | List both sides + why it's a tie |

## When to use each

### HYPOTHESIS

You have a guess based on partial evidence. Not enough to confirm, but plausible.

> "HYPOTHESIS: The function at 0x401234 appears to be a config parser based on:
> - It reads from `.data:0x4050` (a byte sequence that looks like a header)
> - It writes to a 256-byte stack buffer (config struct?)
> - It calls `atoi@plt` (parsing numbers)
>
> To confirm: trace the function with the binary's expected input format, verify the
> output structure matches a known config schema."

The hypothesis states: the claim, the supporting evidence, the test that would confirm.

### SUSPECTED

Strong signals but no smoking gun. You're 70%+ confident.

> "SUSPECTED: This is a Lumma stealer variant based on:
> - Mutex name `Global\Lumma_v2_...` matches Lumma pattern
> - Imports include `LsaOpenPolicy` and `CryptUnprotectData` (Lumma imports)
> - String set includes 6 of 9 known Lumma C2 URI patterns
> - Section entropy profile matches known Lumma samples
>
> Not confirmed because: no YARA match against published Lumna rules; SHA-256 not in
> MalwareBazaar. Recommend submitting to MalwareBazaar for confirmation."

The suspected marker: what's strong about the evidence, what's missing, what would close the gap.

### UNVERIFIED

You'd need to consult external sources (docs, runtime, other tools) to confirm.

> "UNVERIFIED: This binary uses Go 1.21 based on `go:build` strings. However, the exact
> patch version (1.21.x where x is unknown) couldn't be determined from static analysis
> alone. The exact version would matter for CVE assessment — recommend running
> `go version -m <binary>` to confirm."

The unverified marker: what you know, what you don't, what would verify it.

### BLOCKED

Required evidence is unavailable. The analysis can't proceed without it.

> "BLOCKED: Cannot determine the C2 protocol for this sample. The binary is packed
> (Themida, `.themida` section, entropy 7.95), so static analysis only sees the packer's
> stub. The main payload is encrypted at rest and decrypted at runtime.
>
> To unblock: dynamic unpack — run in isolated VM under x64dbg, breakpoint at OEP,
> dump memory, re-analyze the dump statically. Estimated effort: 4 hours."

The blocked marker: what stopped you, what would unblock, the cost to unblock.

### INCONCLUSIVE

Evidence points both ways. Can't call it confidently either direction.

> "INCONCLUSIVE: Whether this binary is malware. Static signals:
> - High-entropy `.text` (7.6) → suspicious (suggests packing)
> - No imports beyond `kernel32` → suspicious (suggests dynamic resolution)
> - But: small file size (12KB) → unusual for malware
> - But: PDB path `C:\\projects\\test_app\\release\\test_app.pdb` → suggests legitimate
>   development artifact
>
> Cannot determine statically. Recommend: submit to VirusTotal for multi-AV scan;
> detonate in isolated VM for behavioral confirmation."

The inconclusive marker: the conflicting evidence, why it's a tie, what would resolve it.

## The "no hedging" rule

Don't use vague hedges:

❌ "This might be, possibly, a buffer overflow, but I'm not sure."
✅ "P1: Buffer overflow at file.c:47. The `strcpy(dst, src)` writes unbounded `src`
into a 16-byte stack buffer `dst`. Triggered when `src` > 15 bytes."

The second version:
- States the finding with confidence (P1)
- Cites evidence (file:line, the actual code)
- States the trigger condition

If you don't have the evidence, use a marker (HYPOTHESIS / SUSPECTED / etc.) instead of hedging. Hedging is unprofessional; markers are professional.

## The "confidence percentages" rule

Avoid percentage estimates ("90% confidence") unless you have data. They're usually fabricated.

Better:
- "High confidence" — multiple strong signals, no contradicting evidence
- "Medium confidence" — strong signal but one missing piece
- "Low confidence" — single weak signal, or conflicting evidence

Each marker maps to a confidence level, and the report explains what's strong / weak.

## The "say what you don't know" rule

Explicit limitations build trust:

> "This report covers static analysis only. Dynamic behavior was not confirmed because
> the user did not provide a sandbox environment. The behavioral findings are
> inferred from imports and strings; the actual runtime behavior may differ."

Without this, the reader might assume the report says more than it does. With it, the reader knows exactly what to trust and what to take with salt.

## The "claim → marker → evidence → test" pattern

For every uncertain claim:

1. **State the claim** clearly (don't bury it)
2. **Mark the uncertainty** (HYPOTHESIS / SUSPECTED / UNVERIFIED / BLOCKED / INCONCLUSIVE)
3. **Cite the evidence** that supports the claim
4. **State the test** that would confirm or refute

Example:

> "**HYPOTHESIS**: The function at 0x401234 is the AES decryption routine.
>
> Evidence:
> - `.rodata:0x4040` contains the AES S-box
> - The function calls `__stack_chk_fail` (has locals)
> - Loop with `xor` instructions (consistent with AES MixColumns)
> - Called from 7 locations (consistent with on-demand string decryption)
>
> To confirm: emulate the function with Unicorn, pass encrypted blob at 0x4050,
> verify the output matches a known AES-128 decryption with the key at 0x4080."

Four parts. Clean. The reader knows what you think, what you have, what you'd need.

## The "no false confidence" rule

Worst sin: high confidence on weak evidence.

❌ "This binary is definitely ransomware." (no evidence cited)
✅ "SUSPECTED ransomware based on:
> - `vssadmin delete shadows` string in `.rodata:0x4080`
> - File extension enumeration loop at 0x401234
> - RSA-2048 public key at 0x4090A0
>
> To confirm: dynamic detonation — verify shadow copies are deleted and files are
> encrypted with the observed public key."

The first is bluff. The second is the same conclusion with evidence.

If the reader disassembles and finds no AES S-box (when you said the binary uses AES), you've lost credibility on the entire report. The second version protects against that — if the evidence isn't there, you say so.

## The "verifiable test" rule

The "test that would confirm" should be verifiable — the reader should be able to run it.

❌ "To confirm: more analysis needed."
✅ "To confirm: run `python scripts/re_disasm.py --file <target> --function sub_401234`
and verify the call to `decrypt_aes` at offset 0x40125C."

The second version: a specific command the reader can run, with a specific expected output.

## The "don't bury limitations" rule

Limitations go in a section of their own, not buried in footnotes.

```
## Limitations

This report is based on:
- Static analysis only (no dynamic confirmation)
- Stripped binary (function names not recovered; addresses used instead)
- No threat intel lookup (sample SHA-256 not submitted to VirusTotal)

To strengthen:
- Submit SHA-256 to MalwareBazaar for family confirmation
- Detonate in isolated VM for behavioral capture
- Run Ghidra GoBinaryAnalyzer for function name recovery
```

Limitations section at the end of the report, before "Recommended next step". Honest, specific, actionable.

## Output

Every uncertain claim in the report should be marked:
- HYPOTHESIS / SUSPECTED / UNVERIFIED / BLOCKED / INCONCLUSIVE
- Plus the evidence
- Plus the test that would confirm

Without the marker, the reader assumes high confidence. Without the test, the reader can't act on the uncertainty.

The disciplined version:

> "**SUSPECTED**: AES-128 used by the binary.
>
> **Evidence**: `.rodata:0x4040` contains the AES S-box (verified: bytes 63 7c 77 7b
> f2 6b 6f c5 ...). The function at 0x401234 references this address and contains an
> `xor` loop consistent with AES MixColumns.
>
> **To confirm**: emulate the function with Unicorn using a known AES test vector;
> verify the output matches the expected ciphertext."

Three parts. Clean. Honest. Actionable.
