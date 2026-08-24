# Static vs Dynamic — When Each Layer Pays Off

The pipeline is static → dynamic, but the **proportion** matters. A senior analyst knows when each layer pays off and when it doesn't. Misjudging this wastes hours.

## Static is the default

Static analysis is **always first**. It's:
- Reproducible (same input → same output, every time)
- Side-effect-free (no VMs, no network, no risk)
- High signal per minute (entropy, imports, strings all answer questions in seconds)
- Independent of environment (works on any machine with the binary)

A senior analyst gets 60-80% of the understanding from static alone. Dynamic is reserved for confirming hypotheses and resolving ambiguities.

## When static hits its limits

Static has known walls. Recognize them and don't fight them — escalate to dynamic.

### Packed / encrypted code

Static sees the packer's stub. The actual payload is encrypted in `.text` or a resource; runtime unpacks it. Static cannot recover the original logic without unpacking.

**Signal:** high-entropy `.text` section (> 7.5), small entry stub, no readable strings, jump to memory region that wasn't in the original layout.

**Escalation:** run in isolated VM, dump memory after unpack, re-analyze the dump statically. (The dump becomes a new static target.)

### Dynamically-resolved APIs

The binary doesn't import `LoadLibrary`/`GetProcAddress` directly visible — it walks the PEB to find `kernel32.dll`, then resolves APIs by hash. Static can't see which APIs are called without recovering the hash function and the hash table.

**Signal:** no imports beyond `kernel32!LoadLibraryA` or none at all (PE with empty IAT), but the binary obviously does network / file / registry work (visible in strings or behavior).

**Escalation:** run in debugger, breakpoint on `GetProcAddress`, log every API resolved. Or emulate the hash function in Python (Unicorn) and run it against a list of common API names.

### String encryption

No readable strings despite reasonable size. The strings exist but are XOR'd / RC4'd / AES'd at rest, decrypted on demand.

**Signal:** string count low for binary size, but `xor` / `mov byte ptr [rbp-N], imm` patterns in disasm (stack string construction).

**Escalation:** find the decryption routine (look for `xor` loops, `sub` loops with constants), set a breakpoint after decryption, dump the decrypted buffer. Or emulate the routine in Unicorn / Python.

### VM-based obfuscation (Themida, VMProtect, custom)

Static disassembly shows a dispatcher loop that fetches bytecode from a data section and switches on opcode. The original logic is in the bytecode, not in x86.

**Signal:** small `.text` (just the dispatcher), large `.data` or `.vmp0`, indirect jumps through a state variable, no recognizable function structure.

**Escalation:** this is a research-grade problem. Either (a) symbolically execute (angr) to explore paths, (b) write a custom lifter that maps VM opcodes to native IR, or (c) trace dynamic execution and build a state→target map. Each takes days to weeks. Don't try to do this in a single audit; mark BLOCKED.

### Self-modifying code

The binary rewrites its own `.text` section at runtime (via `VirtualProtect(PAGE_EXECUTE_READWRITE)` then `mov` to `.text`).

**Signal:** `VirtualProtect` call with PAGE_EXECUTE_READWRITE (0x40) on a `.text` address; writes to `.text` after the protect.

**Escalation:** set a memory write breakpoint on `.text` in the debugger, dump the modified bytes after each write, re-disassemble. The modified bytes are the "real" code.

### Indirect syscalls

The binary avoids `ntdll.dll` by issuing `syscall` instructions directly with hand-prepared args. Static can see the `syscall` instruction but not the syscall number easily (it's in a register, computed at runtime).

**Signal:** `syscall` instruction preceded by `mov eax, <number>` where the number is computed, not literal.

**Escalation:** dynamic trace, breakpoint at `syscall`, log `rax` (syscall number) and args. Map to syscall table.

## When dynamic hits its limits

Dynamic isn't a silver bullet. It has its own walls.

### Anti-debugging

The binary detects the debugger and exits / changes behavior. Static can identify the anti-debug (imports, `IsDebuggerPresent`, PEB checks), but dynamic can't proceed without bypass.

**Bypass:** patch the anti-debug to return 0, or use a stealth debugger (ScyllaHide, TitanHide), or run in an emulator (Unicorn / Qiling) that fakes the absence of a debugger.

### Anti-VM

The binary detects VM artifacts (registry keys, MAC address prefixes, CPUID leaves) and exits. Same problem as anti-debug.

**Bypass:** make the VM look like bare metal (install VMware Tools, set realistic RAM/CPU, add user files), or patch the checks, or run on bare metal if you have a sacrificial machine.

### Time bombs

The binary sleeps to evade sandbox time limits (e.g., `Sleep(60000)` to wait out a 30-second sandbox).

**Bypass:** hook `Sleep` / `nanosleep` to return immediately, or run with sleep-skipping debugger extension, or just wait (long sandbox runs are fine for one-off analysis).

### Code that requires specific input

The binary only reveals behavior with the right magic bytes, command-line args, or environment. Without them, it does nothing.

**Bypass:** static to find the input validation (compare against expected magic, hash, or signature). Construct input that passes. Run dynamic with that input.

## The "confirm, don't discover" principle

Dynamic should confirm hypotheses from static, not discover behavior from scratch. If you don't know what to look for before you run dynamic, you'll generate a pile of sandbox logs and not know what's signal.

Static: form hypotheses ("binary connects to C2 at IP X, sends hostname + screenshot, then waits for command").
Dynamic: confirm or refute each hypothesis ("✅ connects to X; ❌ no screenshot — instead sends clipboard contents; new hypothesis: this is a clipboard stealer").

This back-and-forth is the work. Each pass refines the model.

## The "1 sample = anecdote" principle

A single dynamic detonation is an anecdote, not a finding. Variance in:

- Network conditions (DNS resolution, NAT behavior)
- Timing (sleep bombs, jitter)
- Environmental state (registry, files)
- Random seeds

…can change observed behavior. Run 2-3 detonations and compare. If behavior is consistent, you have a finding. If it varies, mark INCONCLUSIVE and explain what would stabilize it.

## The "environment is part of the report" principle

Document the sandbox config in the report:

- VM type and version (VirtualBox 7.0, VMware 17.5, etc.)
- OS version and patch level
- Installed tooling (Sysmon config, FakeNet-NG version, etc.)
- Network mode (host-only, NAT, fake-network)
- Snapshots taken (before / after)
- Run duration

Without this, the analysis is not reproducible. A senior analyst who omits the env config is telling the reader "trust me" — and the reader shouldn't.

## Decision matrix — static vs dynamic

| Situation | Static? | Dynamic? | Why |
|-----------|--------|----------|-----|
| Standard binary, not packed, not obfuscated | ✅ enough | optional confirm | Static gets you 80%; dynamic confirms |
| Packed binary (UPX, Themida, custom) | ❌ sees stub only | ✅ dump memory after unpack | Static can't recover original logic |
| Dynamically-resolved APIs | ⚠️ partial (hash function) | ✅ breakpoint on GetProcAddress | Dynamic resolves the table |
| Encrypted strings | ❌ sees encryption only | ✅ breakpoint after decrypt | Static can't read encrypted |
| VM-protected (Themida VM, VMP) | ❌ sees dispatcher only | ✅ symbolic / trace | Multi-week effort; consider BLOCKED |
| Network behavior | ⚠️ from strings + imports | ✅ detonate with FakeNet | Static infers; dynamic confirms |
| File / registry behavior | ⚠️ from imports | ✅ Process Monitor | Same |
| Malware family attribution | ✅ enough usually | optional | String / struct / import signals often suffice |
| YARA rule generation | ✅ enough | optional | String + structural patterns are stable across variants |
| CTF rev challenge | ✅ enough usually | optional (gdb for hard cases) | Most CTF rev is static; some need dynamic for anti-debug |

## Final hook

> "What's the cheapest signal that confirms or refutes my current hypothesis?" If static can do it, use static. If static can't, escalate to dynamic with a specific question to answer — not a vague "let's see what it does."
