# RE Thinking — How a Senior Reverse Engineer Approaches a Binary

> The mental model that distinguishes a senior reverse engineer from someone reading bytes. A senior analyst gets 80% of understanding in 20% of the time, then escalates intelligently. They don't read more bytes — they read *the right* bytes.

## 1. The mindset

A senior RE doesn't start by reading every byte. They start by asking: **what is this thing, and what do I need to know about it?** Then they pick the cheapest signal that answers the question, and only escalate to expensive techniques when cheap ones run out.

The fundamental insight: most binaries are 95% boilerplate (CRT startup, libc/libstdc++ glue, generic helpers, dead code from `gcc`/`msvc` templates). The interesting 5% is hidden in a few functions. The senior's job is to locate the 5% fast and ignore the 95%.

A junior opens the binary in IDA, starts at `_start`, scrolls down through `__libc_csu_init`, the CRT setup, then gets bored and confused before reaching `main`. A senior looks at the imports, sees `socket` + `send` + `GetTickCount`, immediately thinks "network beacon, probably C2", and goes straight to the function calling `socket` — skipping the 95% of code that doesn't matter.

## 2. The hierarchy of questions

In order, ask:

1. **What is it?** (file type, arch, format, language, toolchain)
2. **What does it claim to be?** (entry point, main function, declared imports)
3. **What does it actually do?** (strings, calls, behavior — work backward from imports)
4. **What's unusual?** (high entropy, anti-debug, missing strings, odd section layout)
5. **What's the story?** (one-sentence summary of behavior)
6. **What's the proof?** (offsets, instructions, call targets that support the story)
7. **What's missing?** (what couldn't be confirmed statically, what needs dynamic)

These are sequential — don't skip ahead. If you can't answer question 1, you can't answer question 7. If you jump to question 5 without 1-4, you're guessing.

## 3. The cheap-signals-first principle

Always exhaust cheap signals before expensive ones:

| Cost | Signal | What it tells you | Time |
|------|--------|---------------------|------|
| Free | `file`, size, magic bytes | Format, arch, toolchain | <1s |
| Free | Hashes (MD5/SHA256) | Threat intel lookup, identity | <1s |
| Cheap | `strings -a` | C2 endpoints, paths, mutexes, error messages | 1-5s |
| Cheap | Section entropy | Packing, encryption, suspicious regions | 1-2s |
| Cheap | Import table | Behavior categories (injection, persistence, network) | 2-5s |
| Cheap | Symbol table (if not stripped) | Function names → behavior | 2-5s |
| Medium | Disassembly of `main` + entry | Control flow, idioms | 5-15 min |
| Medium | Cross-references from suspicious imports | Behavior confirmation | 5-20 min |
| Expensive | Full disassembly + analysis | Function-by-function semantics | 1-4 hours |
| Expensive | Dynamic execution | Confirms behavior, captures runtime-only state | 30 min - days |

A senior RE gets 80% of the understanding from the first 4 rows. Dynamic analysis is reserved for confirming hypotheses, not forming them.

The corollary: if you find yourself starting with full disassembly, you're being inefficient. The cheap signals would have pointed you at the right 5% in 30 seconds.

## 4. The backward-from-imports trick

The single most powerful RE technique: **don't start at `main`, start at suspicious imports**.

1. Pick a high-signal import (e.g. `CreateRemoteThread`, `socket`, `RegSetValueEx`)
2. Find all call sites that target it (`objdump -d | grep "call.*CreateRemoteThread"`)
3. Walk backward from each call to find the enclosing function prologue
4. Trace what prepares the args — that's the actual behavior

This works because imports are stable anchors. Stripped binaries still expose imports (PE IAT, ELF DT_NEEDED). Anti-debugging might hide strings, but it can't hide that the binary calls `socket()`.

Worked example: you're given a Windows PE. The IAT shows:
- `kernel32!VirtualAllocEx`
- `kernel32!WriteProcessMemory`
- `kernel32!CreateRemoteThread`
- `kernel32!OpenProcess`
- `ntdll!RtlMoveMemory`

These five imports, taken together, are the textbook signature of process injection (DLL injection or process hollowing). The analysis is essentially done — you know the high-level behavior. Now you find the function that calls `CreateRemoteThread`, walk backward to find what `lpStartAddress` was passed (probably pointing to the injected buffer in the target process), and you have the entire behavior in a function-level trace.

If you'd started at `_start` → `mainCRTStartup` → `__security_init_cookie` → `main`, you would have spent 20 minutes reading CRT boilerplate before reaching the actual behavior. Starting from imports is 10x faster.

## 5. The "one-sentence story" rule

Before writing the report, force yourself to summarize the binary's behavior in **one sentence**. If you can't, you don't understand it yet — go back to the cheap signals.

Bad: "The binary does various things including network communication and file operations."
Good: "Lumma stealer variant that enumerates browser profiles, exfils to a hardcoded C2 via HTTP POST with base64-encoded body, and uses process hollowing to persist in `explorer.exe`."

The good version has: family, target, exfil method, persistence. That's the minimum bar.

If you can't write the one-sentence story, you don't have enough evidence yet — go back and find more anchors (more imports, more strings, more constants). The story emerges from evidence; you can't fabricate it from intuition.

## 6. The "show me the bytes" rule

Every claim in the report must point to a byte. If you say "the binary uses AES", point to the S-box in `.rodata` at offset `0x4040`. If you say "it calls socket", point to the `call socket@plt` instruction at `0x401234`. If you say "the C2 is 1.2.3.4", point to the string at `0x4080F0`.

No bytes → not a finding. It's a hypothesis. Mark it as such.

This rule has two effects:
1. **It forces honesty.** If you can't find the bytes, you can't claim the finding. You have to either search more or downgrade to SUSPECTED.
2. **It enables verification.** The reader can `xxd -s 0x4040 -l 16 target` and see the bytes themselves. If your claim is right, they confirm in 10 seconds. If wrong, they catch it in 10 seconds. Trust compounds.

## 7. The five-pass pattern

A senior doesn't read linearly. They do multiple passes, each with a specific purpose:

### Pass 1: Triage (5 minutes)

Cheap signals only: file type, hashes, strings, sections, imports. Form a 1-paragraph hypothesis. Decide: is this interesting enough to continue? (Most binaries aren't.)

### Pass 2: Anchor (10-20 minutes)

Pick 1-3 high-signal anchors (a suspicious import, a suspicious string, an obvious function entry point). Read the disasm around each anchor. Refine the hypothesis.

### Pass 3: Verify (30-60 minutes)

For the hypothesis from Pass 2, find the supporting evidence in the binary. If hypothesis is "this is a keylogger", find: the `SetWindowsHookEx` call, the hook procedure function, the file write loop, the exfil mechanism. Each must be cited with an offset.

### Pass 4: Refute (15 minutes)

Try to refute your own hypothesis. Did I miss something? Is there a counter-indicator? (e.g., "I said it's a keylogger but the strings include browser-specific data — is it actually a form-grabber, not a generic keylogger?") Update the hypothesis.

### Pass 5: Confirm (variable)

If dynamic analysis is available, run the binary in a sandbox and confirm the static findings. If not, mark limitations and submit the report with HYPOTHESIS/SUSPECTED/UNVERIFIED markers as appropriate.

Most RE work is 4-5 passes. Trying to deep-dive on the first pass is a classic beginner mistake — you spend 30 minutes on a function that turns out to be the C runtime startup, not the actual behavior.

## 8. The "follow the strings" trick

Strings are the most underused cheap signal. A senior doesn't just grep for strings — they categorize them:

| Category | Examples | What it tells you |
|---|---|---|
| URLs / IPs | `http://1.2.3.4/api`, `https://c2.evil.com/report` | C2 endpoints |
| File paths | `C:\Users\*\AppData\Local\Temp\`, `/tmp/.lock` | Persistence, staging locations |
| Registry keys | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` | Persistence |
| Mutex names | `Global\MyMalware_v2_Inst` | Family signature, multi-instance prevention |
| Database connection strings | `postgres://user:pass@host:5432/db` | Database access |
| Browser paths | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data` | Browser credential theft |
| Crypto wallet paths | `%APPDATA%\Bitcoin\wallet.dat`, `%APPDATA%\Electron\*\wallet` | Crypto wallet theft |
| Email / SMTP strings | `smtp://mail.evil.com`, `MAIL FROM:`, `RCPT TO:` | Spam / exfil via email |
| HTTP headers | `User-Agent: Mozilla/5.0...`, `Content-Type: application/json` | Network behavior fingerprint |
| Error messages | `Failed to decrypt config`, `Unable to connect to C2` | Confirms functionality by error message |
| PDB paths | `C:\Users\author\projects\malware\Release\malware.pdb` | Author build environment, sometimes real username |
| Build timestamps | `Compiled on 2024-08-15 14:32:11` | Sometimes present in error strings |
| Library version strings | `OpenSSL 3.0.7`, `libcurl 7.88.0` | Embedded libraries and versions |
| Compiler-generated identifiers | `_ZNSt6vectorIiSaIiEE9push_backEOi` (mangled C++) | C++ binary, specific STL types used |

When you categorize strings, the binary's behavior often becomes obvious before you read any disassembly.

## 9. The "vtable + RTTI" recovery trick

For C++ binaries, even stripped, the RTTI (Run-Time Type Information) survives. The mangled class names are stored as plain text in `.rodata`. From these names you can recover:

- The full class hierarchy (inheritance graph)
- All STL template instantiations used (`std::vector<int>`, `std::map<std::string, std::vector<int>>`)
- The exception types thrown (from the LSDA / `.gcc_except_table`)
- The constructors and destructors (paired by their call patterns — write vtable ptr to `[this]`)

This works on GCC/Clang (Itanium ABI) and MSVC (different RTTI layout). For details, see the `prompts/re-playbooks/stl-recovery.md` playbook.

The big idea: a stripped C++ binary is much less stripped than it looks. The class hierarchy is sitting in `.rodata`, plain-text mangled. Read it.

## 10. The "section entropy" trick

Entropy is the cheapest signal for "this section has high information density":

| Entropy range | Typical content | Notes |
|---|---|---|
| 0.0 - 1.0 | Mostly zero bytes (padding, alignment) | Normal |
| 1.0 - 3.0 | Sparse data (relocation tables, jump tables) | Normal |
| 3.0 - 5.0 | Strings (text) | Normal |
| 4.5 - 6.5 | Code (instructions, opcodes, immediates mixed) | Normal |
| 5.0 - 7.0 | Data tables, compressed data | Normal-ish |
| 7.0 - 7.5 | Possible encryption (no compression artifacts visible) | Suspicious |
| 7.5 - 8.0 | Packed, encrypted, or compressed data | Almost certainly packer or encrypted blob |

A section >7.5 entropy over >50KB is almost always packer or encrypted. The function in `.text` that reads from this section is your unpacker / decryptor — start there.

## 11. The "follow the call graph" trick

For stripped binaries with no RTTI, the call graph itself reveals structure:

- A function called by 50+ others is a utility (printf, malloc, strcpy, ...)
- A function called by 1-2 others is a specific behavior (handler for a specific API endpoint, parser for a specific format)
- A function that calls many functions but is called by few is a dispatcher (main, request router, command handler)
- A function that calls nothing but is called by many is a leaf behavior (logger, serializer, crypto primitive)

Build the call graph first (Capstone + simple analysis), then identify the "shape" of each function. The shapes tell you what each function does before you read it.

## 12. The "constants fingerprint" trick

Binaries that use crypto almost always leak the algorithm via constants. The AES S-box (`63 7c 77 7b ...`), MD5 IV (`01 23 45 67 ...`), ChaCha20 sigma (`expand 32-byte k`), TEA delta (`b9 79 37 9e`) — each is a unique signature. Search for these constants in `.rodata` and the crypto is identified.

See `prompts/re-playbooks/crypto-identification.md` for the full table.

## 13. When to give up and escalate

Static analysis has limits. Recognize them:

- **Packed binary** — static sees the packer's stub, not the payload. Need to unpack (run + memory dump) before the analysis becomes useful. Mark as BLOCKED on the inner behavior; report on the packer stub.
- **VM-protected binary** — disassembly shows the VM dispatcher, not the original logic. Need handler-by-handler analysis (days of work) or symbolic execution. Mark as BLOCKED on the original logic; report on the VM structure.
- **Encrypted strings** — strings extraction returns nothing useful. Need to find the decryption routine (look for `xor` loops, `imul` for keys) and emulate it (Unicorn / Qiling). Mark as BLOCKED on the strings until you can emulate the decryption.
- **Reflective loading** — the binary is just a loader; the real payload is in a resource or registry blob. Need to extract the payload first. Mark as BLOCKED on the payload; report on the loader.
- **Stripped Go binary** — surprisingly analyzable (gopclntab exists). Use Ghidra Go analyzer; function names recoverable.
- **Stripped Rust binary** — harder; panic strings (`panicked at`, file paths) are the main hook. Often the binary still has std library function names visible via FLIRT.
- **Stripped C++ binary** — vtables in `.rodata` are the main hook. RTTI strings in `.rodata` are recoverable to mangled class names.
- **Anti-debug heavy binary** — static is fine; dynamic is hard. Use static to identify the anti-debug routines, then patch them out for dynamic.

When you hit a wall, say so. The report should mark `BLOCKED` and explain what would unblock it, not pretend you understood what you didn't.

## 14. The "ask the stupid question" rule

Before assuming the binary is malicious, ask:
- Could this be a game trainer? (Often uses `WriteProcessMemory` + `OpenProcess` to modify game memory.)
- Could this be a legitimate updater? (Often downloads and executes code.)
- Could this be a development tool? (Often uses `CreateRemoteThread` for legitimate hooking.)
- Could this be a security tool? (Often uses injection techniques for EDR/AV.)

Many false positives come from assuming "injection == malware". The injection technique is a tool; the intent matters. Cite the technique, infer the intent from the surrounding behavior (what's injected? where? with what payload?), and label accordingly.

## 15. The "two hypotheses minimum" rule

A senior doesn't commit to one hypothesis early. They maintain at least two competing hypotheses and let evidence discriminate:

- Hypothesis A: this is a Lumma stealer variant
- Hypothesis B: this is a generic infostealer using similar techniques

Then look for discriminating evidence:
- Lumma-specific mutex name? → A
- Lumma C2 URL pattern? → A
- Generic mutex name? → B
- Custom C2 protocol? → B

When one hypothesis has more supporting evidence than the other, mark it as the leading hypothesis. Until then, present both as competing possibilities.

This avoids the trap of premature commitment — when the analyst commits to one hypothesis early and ignores disconfirming evidence.

## 16. The "know your toolchain" rule

A senior RE knows the disassembly fingerprints of common compilers:

| Compiler | Signatures in disasm |
|---|---|
| GCC x64 Linux | `endbr64` at function entry (CET); `movaps xmm0, [rsp+X]` aligned stack; `sub rsp, 0xXX` with red zone usage |
| Clang x64 Linux | Similar to GCC but often uses different register allocation; `mov rax, qword ptr [rip + symbol]` for globals |
| MSVC x64 Windows | `sub rsp, 0x48` typical prologue; uses `__chkstk` for large frames; SEH-based exception handling |
| MinGW | MSVC-style but with GCC prologues; often has `___main` call near entry |
| Rust (release) | Heavy use of `Option<T>` and `Result<T, E>` patterns in disasm; panic paths with `core::panicking::panic` calls |
| Go (release) | Huge stack frames; goroutine scheduling calls; runtime type tables in `.gopclntab` |
| Swift | Heavy retain/release calls (`swift_retain`, `swift_release`); witness tables for protocol conformance |
| Zig | `add error_return_trace, ...` patterns; `panic` calls; allocator passing |

Knowing the compiler tells you what idioms to expect — and lets you read the disasm faster because you recognize the patterns.

## 17. The "don't trust the decompiler" rule

Decompilers (Ghidra, IDA Hex-Rays) are useful for getting a high-level view, but they get many things wrong:

- They can produce code that doesn't compile.
- They invent variables that aren't there (decompiler artifacts).
- They miss inline assembly (especially `cpuid`, `rdtsc`, `syscall`).
- They sometimes present obfuscated code as simpler than it is (because the obfuscation collapses when expressed in C).
- They don't see C++ types (unless you annotate).

Treat the decompiler output as a hypothesis, not as ground truth. Verify by reading the actual disasm at the offsets it claims.

## 18. Final mental hook

> "I have X bytes. I want to know Y. What's the cheapest signal that tells me Y?"

If you can answer that question repeatedly, you're doing RE. If you can't, you're reading bytes — and reading bytes is not analysis.

The senior analyst's superpower is not reading more bytes faster. It's asking better questions, choosing cheaper signals, and recognizing when to escalate. The 100x productivity gap between a senior and a junior isn't 100x speed — it's 100x *signal per byte*.
