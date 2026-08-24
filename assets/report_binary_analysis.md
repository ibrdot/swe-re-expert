# Binary Analysis Report — {{TARGET_NAME}}

> Canonical output template for RE binary analysis (non-malware — for malware triage, use `report_malware_triage.md`). Replace `{{...}}` placeholders with concrete values. Maintain the section order.

**Verdict:** CLEAN | SUSPICIOUS | MALICIOUS | INCONCLUSIVE
**Audited by:** Agent using `swe-re-expert` skill
**Date:** {{YYYY-MM-DD}}
**Target:** {{file path or blob ID}}
**Size:** {{N bytes}}
**SHA256:** {{hash}}
**Analysis type:** {{Static / Static + Dynamic / Static + Emulated}}

---

## Executive summary

{{3-5 sentences. State the verdict in plain English. What is the binary? What does it do? What's the headline finding? What's the recommended next step?}}

Example (good):
> CLEAN (benign utility). The binary is a 158KB ELF x86-64 dynamically-linked `ls` executable from GNU coreutils (Build ID `0243f2a3ad64d635299a574bbc8ef951ddde9b21`). Standard glibc/libselinux/libcap imports; full security hardening (NX, PIE, full RELRO, canary, FORTIFY). All strings resolve to GNU license URLs and standard coreutils paths. No malicious behavior identified statically. Recommend: skip threat-intel lookup; verdict is CLEAN with high confidence.

## Sample metadata

| Field | Value |
|---|---|
| File path | {{target}} |
| Size (bytes) | {{N}} |
| Magic bytes | {{`7f 45 4c 46` for ELF, `4d 5a` for PE, `cafe babf` for Mach-O universal, etc.}} |
| Format | {{ELF / PE / Mach-O / other}} |
| Architecture | {{x86_64 / i386 / ARM64 / ARM / MIPS / RISC-V}} |
| Endianness | {{little / big}} |
| Linking | {{dynamic / static}} |
| Compiler hints | {{GCC / Clang / MSVC / Go / Rust / .NET / etc.}} |
| Build ID / PDB path | {{ID or path if present}} |
| Timestamp | {{file header TimeDateStamp; flag if zero or off}} |

### Hashes

| Algorithm | Hash |
|---|---|
| MD5 | {{hash}} |
| SHA1 | {{hash}} |
| SHA256 | {{hash}} |
| ssdeep | {{hash}} |
| TLSH | {{hash}} |
| Import hash (imphash) | {{hash — Windows PE only}} |
| Rich header hash | {{hash — Windows PE / MSVC only}} |

### Mitigations / hardening

| Mitigation | Status | Notes |
|---|---|---|
| NX (DEP) | {{enabled / disabled}} | Stack not executable |
| PIE / ASLR | {{enabled / disabled}} | Position-independent |
| RELRO | {{none / partial / full}} | GOT protection |
| Stack canary | {{present / absent}} | Stack buffer overflow detection |
| FORTIFY | {{enabled / disabled}} | `_chk` variants |
| CFG (Control Flow Guard) | {{enabled / disabled}} | Windows only |
| CET (Control-flow Enforcement) | {{enabled / disabled}} | Linux x86 with `endbr64` |
| seccomp filter | {{present / absent}} | Syscall restriction |

## Section entropy profile

| Section | VAddr | Size | Entropy | Notes |
|---|---|---|---|---|
| {{.text}} | {{0x...}} | {{N}} | {{X.XXX}} | {{code, normal ~6.0-6.7}} |
| {{.rodata}} | {{0x...}} | {{N}} | {{X.XXX}} | {{constants, strings}} |
| {{.data}} | {{0x...}} | {{N}} | {{X.XXX}} | {{mutable globals}} |
| ... | ... | ... | ... | ... |

High-entropy sections (>7.5) are flagged with rationale: packed / encrypted / compressed / normal-for-data.

## Imports / dynamic symbols

Categorized by behavior class. For RE, focus on suspicious categories.

| Category | Imports | Behavioral interpretation |
|---|---|---|
| Process / memory | {{VirtualAlloc, WriteProcessMemory, CreateRemoteThread, OpenProcess}} | {{injection, hollowing}} |
| File system | {{CreateFile, WriteFile, ReadFile, DeleteFile, MoveFile}} | {{file manipulation, persistence}} |
| Registry | {{RegSetValueEx, RegCreateKeyEx}} | {{persistence (Windows)} |
| Network | {{socket, connect, send, recv, WSAGetLastError}} | {{network communication}} |
| Process info | {{GetCurrentProcessId, GetModuleHandle, GetProcAddress}} | {{runtime API resolution}} |
| Dynamic resolution | {{LoadLibraryA, GetProcAddress}} | {{runtime import loading — common in packers}} |
| Crypto | {{CryptAcquireContext, CryptEncrypt, BCryptEncrypt}} | {{data encryption}} |
| Anti-debug / anti-VM | {{IsDebuggerPresent, NtQueryInformationProcess, cpuid, rdtsc}} | {{anti-analysis}} |
| Other (libstdc++, libc, etc.) | {{...}} | {{standard library, benign}} |

## Strings of interest

Categorized. Only include non-boilerplate strings (boilerplate = GNU license text, std library paths, etc.).

| Category | String | Offset | Notes |
|---|---|---|---|
| Network (URLs / IPs) | {{http://1.2.3.4/api}} | {{0x...}} | {{C2 endpoint}} |
| Network (User-Agent) | {{Mozilla/5.0...}} | {{0x...}} | {{HTTP fingerprint}} |
| File paths | {{C:\\Users\\*\\AppData\\Local\\Temp\\}} | {{0x...}} | {{staging location}} |
| Registry keys | {{HKLM\\...\\Run}} | {{0x...}} | {{persistence}} |
| Mutex names | {{Global\\MyMalware_v2_Inst}} | {{0x...}} | {{family signature}} |
| Browser paths | {{%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Login Data}} | {{0x...}} | {{browser credential theft}} |
| Crypto wallet paths | {{%APPDATA%\\Bitcoin\\wallet.dat}} | {{0x...}} | {{crypto wallet theft}} |
| Email / SMTP | {{smtp://mail.evil.com}} | {{0x...}} | {{spam / exfil via email}} |
| Error messages | {{Failed to decrypt config}} | {{0x...}} | {{confirms decryption routine}} |
| Build paths (PDB) | {{C:\\Users\\author\\projects\\malware\\Release\\malware.pdb}} | {{0x...}} | {{author environment}} |
| Library version strings | {{OpenSSL 3.0.7}} | {{0x...}} | {{embedded libraries}} |
| Mangled C++ names | {{St6vectorIiSaIiEE}} | {{0x...}} | {{std::vector<int> instantiation}} |

## Behavioral analysis

### Identified behaviors

| Behavior | Evidence | Confidence | MITRE ATT&CK |
|---|---|---|---|
| {{Behavior name}} | {{offset + instruction + interpretation}} | {{CONFIRMED / SUSPECTED / HYPOTHESIS}} | {{TXXXX Technique Name}} |
| Process injection | `call VirtualAllocEx@plt` at 0x401234; `call WriteProcessMemory@plt` at 0x401250; `call CreateRemoteThread@plt` at 0x40127A | CONFIRMED | T1055 Process Injection |
| Persistence (registry) | `call RegSetValueExA` at 0x4010F0 with `HKLM\...\Run` arg | SUSPECTED | T1547.001 Boot or Logon Autostart Execution: Registry Run Keys |
| C2 communication | `call socket` at 0x401100, `call connect` at 0x401120, IP string at 0x4080F0 | CONFIRMED | T1071 Application Layer Protocol |
| ... | ... | ... | ... |

### Crypto identification

If the binary uses crypto, identify the algorithm and mode:

| Algorithm | Mode | Evidence | Key length (if inferred) |
|---|---|---|---|
| {{AES-128}} | {{CBC}} | {{AES S-box at 0x4040; AES inverse S-box at 0x4440; 10 rounds in cipher loop → 128-bit; IV passed as 2nd arg}} | {{128 bits}} |
| {{MD5}} | {{N/A}} | {{MD5 IV at 0x4080; 64-entry sine table at 0x40A0}} | {{N/A}} |
| {{RC4}} | {{stream}} | {{256-byte array init loop + swap loop at 0x401030; no constants in .rodata}} | {{runtime-derived}} |
| ... | ... | ... | ... |

If no crypto found: state "No standard crypto constants found. If the binary appears to do encryption, suspect custom/hand-rolled crypto and recommend reviewing the suspicious function at {{offset}}."

## Limitations

{{What couldn't be verified, why, what would resolve it. Common:

- "Static-only — dynamic execution not performed; behavioral findings are inferred from imports/strings, not confirmed at runtime"
- "Stripped binary — function names not recovered; addresses used instead"
- "No threat intel lookup — sample SHA-256 not submitted to MalwareBazaar / VirusTotal"
- "Packed binary — payload not unpacked statically; only packer stub analyzed. Inner behavior BLOCKED."
- "Go binary — gopclntab function name recovery not run; function names are addresses only"
- "Rust binary — panic strings extracted but full type recovery not performed"
- "VM-protected functions — {{N}} virtualized functions marked BLOCKED; behavior inferred from non-virtualized functions only"
- "No sandbox/CAPE environment available — dynamic confirmation BLOCKED"
- "YARA CLI not installed in analysis environment — YARA rule written but not validated against target"
}}

## Recommended next step

{{The smallest safe action for the user. Concrete, bounded, ordered by prerequisite. Examples:

1. **If verdict CLEAN with high confidence**: No further action needed. Skip threat-intel lookup.
2. **If verdict SUSPICIOUS**: Submit SHA-256 to MalwareBazaar for family confirmation; run dynamically in instrumented VM for behavioral capture.
3. **If verdict MALICIOUS**: Share YARA rule with detection team; update blocklists with C2 IOCs; submit to VirusTotal for community coverage.
4. **If verdict INCONCLUSIVE**: Escalate to dynamic analysis with full instrumentation; collect runtime imports, network traffic, file system changes.
5. **If BLOCKED (packed/VM-protected)**: Run in dynamic analysis environment with unpacker; re-analyze the unpacked dump statically.
}}

For each step: estimated effort, what's needed (tools, environment, time).
