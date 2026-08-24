# Binary Analysis Report — {{TARGET_NAME}}

**Verdict:** CLEAN | SUSPICIOUS | MALICIOUS | INCONCLUSIVE
**Analyzed by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Analysis type:** Static-only | Static + dynamic (env: {{ENV_DESC}})

---

## Binary metadata

| Field | Value |
|-------|-------|
| File path | {{TARGET_PATH}} |
| Size | {{N}} bytes |
| Format | {{ELF / PE / Mach-O / raw}} |
| Architecture | {{x86_64 / ARM64 / ...}} |
| Endianness | {{little / big}} |
| Linking | {{static / dynamic}} |
| Compiler / toolchain | {{GCC 11.4.0 / MSVC 19.37 / Go 1.21 / Rust 1.75 / ...}} |
| Entry point | {{0xADDRESS}} |
| MD5 | {{HASH}} |
| SHA1 | {{HASH}} |
| SHA256 | {{HASH}} |
| SSDeep | {{HASH}} |

## Security features

| Feature | Status | Evidence |
|---------|--------|----------|
| NX / DEP | {{true / false}} | {{section or PE flag evidence}} |
| PIE / ASLR | {{true / false}} | {{ET_DYN / DYNAMIC_BASE}} |
| RELRO | {{full / partial / none}} | {{PT_GNU_RELRO + DT_BIND_NOW}} |
| Stack canary | {{true / false}} | {{__stack_chk_fail in symtab}} |
| FORTIFY | {{true / false}} | {{*_chk imports}} |
| CFG (PE) | {{true / false}} | {{DllCharacteristics & 0x4000}} |

## Behavioral summary

{{3-5 sentences in plain English describing what the binary does. Include: what entry point does, what main behavior is, what's unusual/suspicious. Use evidence from static analysis as the basis.}}

## Evidence table

| # | Offset / addr | Instruction / symbol / string | Interpretation |
|---|---------------|---------------------------------|----------------|
| 1 | {{0x...}} | {{`mov rdi, [rip+0x...]`}} | {{Reference to .rodata string}} |
| 2 | {{0x...}} | {{`call 0x...`}} | {{Calls function X, presumably for Y}} |
| 3 | {{...}} | {{`MZ` magic in `.data` at 0x...}} | {{Embedded PE — possible payload}} |
| 4 | {{...}} | {{string: "Mozilla/5.0..."}} | {{C2 User-Agent}} |
| 5 | {{...}} | {{entropy of `.text` = 7.91}} | {{High entropy — possible packing}} |

## Sections inventory

| Name | Virt addr | Size | Entropy | Notes |
|------|-----------|------|---------|-------|
| {{.text}} | {{0x...}} | {{N}} | {{0.0-8.0}} | {{normal / packed / encrypted}} |
| {{.rodata}} | ... | ... | ... | ... |
| {{.data}} | ... | ... | ... | ... |

## Imports / library dependencies

{{For PE: list of imported DLLs + high-signal functions. For ELF: list of NEEDED libs. For Mach-O: linked dylibs.}}

| Category | Functions |
|----------|-----------|
| {{injection}} | {{CreateRemoteThread, WriteProcessMemory, ...}} |
| {{network}} | {{socket, connect, ...}} |
| {{...}} | ... |

## Findings

| Priority | Problem | Evidence | Recommended next step |
|----------|---------|----------|----------------------|
| {{P0/P1/P2/P3}} | {{Buffer overflow at line/offset}} | {{evidence addr/insn}} | {{Bound the copy or use safe API}} |
| {{...}} | ... | ... | ... |

## Anti-analysis techniques observed

| Technique | Indicator | Workaround |
|-----------|-----------|------------|
| {{UPX packing}} | {{UPX0 section}} | {{upx -d to unpack}} |
| {{IsDebuggerPresent}} | {{import in IAT}} | {{patch to return 0}} |
| {{...}} | ... | ... |

## Limitations

{{What couldn't be confirmed, why, what would resolve it. Common cases:
- "Stripped — function names not recovered; use Ghidra GoBinaryAnalyzer / IDAFLIRT sigs"
- "Packed — main payload not analyzed statically; dump memory after unpack"
- "Static-only — no dynamic confirmation of network behavior"
- "VM-based obfuscation — handlers not fully mapped"
}}

## Recommended next step

{{The smallest safe change or follow-up action. Concrete and bounded. Examples:
- "Re-run with `python scripts/re_disasm.py --file <target> --function main` to get full main() disasm"
- "Unpack with `upx -d <target>` and re-run triage on the unpacked binary"
- "Set up an isolated VM and capture dynamic behavior with Cuckoo"
- "Hand off to senior RE for VM-based obfuscation analysis"
}}
