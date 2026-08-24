# YARA Rule Design — Writing Detection Rules That Don't Suck

YARA rules are how your static findings become operational. A bad YARA rule either matches everything (noise) or only matches one sample (useless). The middle ground — family-level rules that catch variants — is the goal.

## The 3-tier rule system

| Tier | Strategy | When to use |
|------|----------|-------------|
| 1 | Hash match (`hash.sha256(0, filesize) == "..."`) | One specific sample; for tracking, not detection |
| 2 | Behavioral strings + structure | Family-level; the default; what you usually write |
| 3 | Network pattern | NIDS rules; for Suricata / Snort, not YARA but related |

Tier 2 is 80% of real detection engineering. Get good at it.

## The 6 principles of good YARA

### 1. Anchor on structure first

Start every rule with a structural anchor that's cheap to evaluate:

```yara
condition:
    uint16(0) == 0x5A4D           // PE file (MZ header)
    and filesize < 2MB
    and uint32(uint32(0x3c)) == 0x00004550  // PE header at e_lfanew
```

Or for ELF:
```yara
condition:
    uint32(0) == 0x464C457F       // \x7fELF
    and filesize < 5MB
```

This narrows the search space cheaply. YARA evaluates conditions left-to-right; cheap predicates first means it skips most files fast.

### 2. Pick strings that are stable across variants

Good strings:
- Hardcoded C2 URLs (`$c2_uri = "/gate.php?id="`)
- Unique mutex names (`$mutex = "Global\\FamilyMutex_v1"`)
- Unique User-Agents (`$c2_ua = "FamilyBot/1.0"`)
- Crypto constants specific to this family's implementation (AES S-box is generic; a specific AES key in `.rodata` is family-specific)
- Specific error messages (`$err = "Failed to inject into explorer.exe"`)
- Specific PDB paths in the binary (`$pdb = "C:\\malware\\v2\\loader.pdb"`)

Bad strings:
- `Mozilla` (matches every browser)
- `User-Agent` (matches every HTTP library)
- `Windows` (matches everything)
- Generic crypto constants (AES S-box alone, RC4 init table alone — too common)
- Standard library function names (`printf`, `malloc` — every binary has these)

### 3. Use `nocase` and `wide` sparingly

- `ascii` (default) — matches the literal bytes; usually what you want
- `nocase` — case-insensitive; useful for registry keys, dangerous for general strings (false positives)
- `wide` — matches UTF-16 (two bytes per char); essential for Windows-specific strings like registry keys, file paths
- `ascii wide` — both; common for Windows binaries that might use either

```yara
$reg_run = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" ascii wide nocase
```

This matches the registry path in ASCII, UTF-16LE, and case-insensitively. Good for persistence indicators.

### 4. Require multiple strings, not just one

The most common YARA mistake: too permissive `any of them`:

```yara
// BAD — too permissive
condition:
    uint16(0) == 0x5A4D and any of ($c2_*)
```

One match fires the rule. If one of your `$c2_*` strings is generic, you get false positives.

Better:

```yara
// GOOD — require multiple signals
condition:
    uint16(0) == 0x5A4D
    and filesize < 2MB
    and (
        (3 of ($c2_*))
        or ($mutex and 2 of ($c2_*))
        or ($mutex and $reg_run)
    )
```

This requires either:
- 3 C2 patterns (strong family signal), OR
- Mutex + 2 C2 patterns (very strong), OR
- Mutex + persistence (strong family + behavior)

Each disjunct is independently meaningful. The rule fires only when there's enough evidence.

### 5. Negate known-good strings to avoid false positives

If your rule accidentally matches a known-good file (say, a particular signed Microsoft binary that happens to have a similar string), add a negation:

```yara
condition:
    uint16(0) == 0x5A4D
    and filesize < 2MB
    and $c2_uri
    and not $legitimate_string    // exclude known-good file
```

This is the pattern for "rule that would be too broad, narrow it with negation."

### 6. Use `private` for rules you don't want to surface

Internal building-block rules that other rules compose from:

```yara
private rule PE_With_High_Entropy_Text {
    condition:
        uint16(0) == 0x5A4D
        and pe.sections[0].entropy >= 7.0
}

rule Packed_PE_Behavior {
    condition:
        PE_With_High_Entropy_Text and $upx_magic
}
```

The `private` keyword means the rule won't be reported in matches — it's only used by other rules. Useful for factoring out common conditions.

## The rule template

```yara
rule {{FAMILY}}_Generic {
    meta:
        author      = "ibrdot"
        date        = "{{YYYY-MM-DD}}"
        description = "Detects {{FAMILY}} family by behavioral strings and structure"
        tlp         = "GREEN"
        reference   = "{{source URL or analysis report}}"
        sha256      = "{{sample sha256}}"   // for traceability

    strings:
        // C2 patterns — verify these are stable across variants
        $c2_ua    = "{{unique C2 User-Agent}}" ascii
        $c2_uri  = "{{unique C2 path}}" ascii
        $c2_host = "{{C2 hostname if hardcoded}}" ascii

        // Mutex / event names (family-specific)
        $mutex    = "Global\\{{mutex name}}" ascii wide

        // Persistence indicators
        $reg_run  = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" ascii wide nocase
        $svc_name = "{{service name}}" ascii wide

        // Crypto constants — only if family-specific
        $rc4_key  = { 52 43 34 5F 4B 45 59 }   // hex bytes

        // Behavioral strings
        $err_inject = "Failed to inject" ascii wide nocase

    condition:
        uint16(0) == 0x5A4D           // MZ header (PE file)
        and filesize < 2MB
        and (
            (2 of ($c2_*))
            or ($mutex and 1 of ($reg_run, $rc4_key, $svc_name))
            or (3 of ($c2_*, $mutex, $reg_run, $err_inject))
        )
        and not $legitimate_string     // optional FP suppression
}
```

## Testing your rule

```bash
# Positive test — must match the sample
yara {{rule}}.yar {{sample}}     # should print "{{FAMILY}}_Generic {{sample}}"

# Negative test — must NOT match clean files
yara -r {{rule}}.yar /usr/bin/ 2>/dev/null | wc -l   # should be 0
yara -r {{rule}}.yar /usr/lib/ 2>/dev/null | wc -l   # should be 0
yara -r {{rule}}.yar C:\\Windows\\System32\\ 2>/dev/null | wc -l   # should be 0 (on Windows)

# Coverage test — match known sibling samples (if available)
yara -r {{rule}}.yar ./siblings/ | wc -l   # count matches; aim for >70% of known variants
```

If positive test fails → your rule has a bug.
If negative test fails → your rule is too broad; tighten conditions or add negations.
If coverage test fails (<70%) → your rule is too narrow; relax conditions or add more strings.

## Common YARA mistakes

### Mistake 1: Over-broad `any of them`

```yara
// BAD
condition: uint16(0) == 0x5A4D and any of them
```

If any string is generic, you'll get FPs. Always require specific combinations.

### Mistake 2: Single-byte anchors

```yara
// BAD — matches any PE with bytes 4D 5A at offset 0, which is all PEs
condition: uint16(0) == 0x5A4D
```

PE anchor alone is fine as a precondition, but it's not a finding. You need actual content strings.

### Mistake 3: Not testing against benign files

A rule that fires on `/usr/bin/*` or `C:\Windows\System32\*` is broken. Always test against a clean corpus.

### Mistake 4: Not testing across variants

A rule that only matches your one sample is too narrow. Either find more samples to test against, or relax to make the rule family-level.

### Mistake 5: Inappropriate use of `nocase`

```yara
// BAD
$url = "http" nocase
// Matches every binary that has http anywhere, case-insensitively
```

Use `nocase` only for things where case really doesn't matter (registry key paths, mutex names sometimes). URLs and User-Agents are case-sensitive in practice.

### Mistake 6: Hex strings that are too short

```yara
// BAD — 4 bytes matches many things
$magic = { DE AD BE EF }

// BETTER — 8+ bytes are family-specific
$magic = { DE AD BE EF CA FE BA BE 13 37 42 00 }
```

Minimum 6-8 bytes for hex strings to be useful.

## When NOT to write YARA

- Sample is too generic (no unique strings)
- Sample is heavily obfuscated (no stable strings)
- Sample uses reflection / dynamic loading (no static strings to anchor on)
- Sample is one-off (no sibling variants expected — just use hash)

For these, behavioral detection (EDR rules, Sysmon events) is more useful than YARA.

## Output

For each malware sample, the report should include 1-3 YARA rules:

1. **Tier 2 (family-level)** — the main detection rule, tested and validated
2. **Tier 1 (hash)** — for the specific sample, useful for tracking (not for general detection)
3. **Optional tier 3 (network)** — for Suricata/Snort, capturing C2 protocol patterns

Include the validation results:
- Positive test: ✅ / ❌
- Negative test (clean files): N matches (should be 0)
- Coverage test (if siblings available): N/M matches

Without validation, the rule is an assertion, not a finding.
