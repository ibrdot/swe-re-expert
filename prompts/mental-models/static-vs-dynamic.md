# Static vs Dynamic — When Each Layer Pays Off

The pipeline is static -> dynamic, but the **proportion** matters. A senior analyst knows when each layer pays off and when it doesn't. Misjudging this wastes hours.

## Static is the default

Static analysis is **always first**. It's:
- Reproducible (same input -> same output, every time)
- Side-effect-free (no VM, no network)
- High signal per minute (entropy, imports, strings all answer questions in seconds)
- Independent of environment (works on any machine with the binary)
- Re-sharable (a static finding is reproducible by anyone with the binary)

A senior analyst gets 60-80% of the understanding from static alone. Dynamic is reserved for confirming hypotheses and resolving ambiguities.

## When static hits its limits

Static has known walls. Recognize them and don't fight them — escalate to dynamic.

### Packed / encrypted code

Static sees the packer's stub. The actual payload is encrypted in `.text` or a resource; runtime unpacks it. Static cannot recover the original logic without unpacking.

**Signal:** high-entropy `.text` section (> 7.5), small entry stub, no readable strings, jump to memory region that wasn't in the original layout.

**Escalation:** run in an analysis VM, dump memory after unpack, re-analyze the dump statically. (The dump becomes a new static target.)

**Concrete workflow:**
1. Identify packer via `re-playbooks/packers-handling.md` (look for UPX magic `UPX!`, Themida `.taggant`, VMProtect `.vmp0` section)
2. Spin up analysis VM (VirtualBox + REMnux or Windows sandbox with Sysmon)
3. Launch binary under debugger (x64dbg/WinDbg), set breakpoint on `VirtualProtect` with `PAGE_EXECUTE_READWRITE`
4. When breakpoint hits, dump the affected memory region to disk
5. Re-run static analysis on the dump (treat it as a new binary)
6. Iterate until no more `VirtualProtect` RWX calls

### Dynamically-resolved APIs

The binary doesn't import `LoadLibrary`/`GetProcAddress` directly visible — it walks the PEB to find `kernel32.dll`, then resolves APIs by hash. Static can't see which APIs are called without recovering the hash function and the hash table.

**Signal:** no imports beyond `kernel32!LoadLibraryA` or none at all (PE with empty IAT), but the binary obviously does network / file / registry work (visible in strings or behavior).

**Escalation:** run in debugger, breakpoint on `GetProcAddress`, log every API resolved. Or emulate the hash function in Python (Unicorn) and run it against a list of common API names.

**Concrete workflow:**
1. See `re-playbooks/api-resolution.md` for hash function identification
2. Recover the hash function from disasm (usually ROR-13, CRC32, or FNV-1a)
3. Two paths:
   a. **Emulate:** Load the binary in Unicorn, set PC to hash function entry, run with candidate API names as input; collect matches
   b. **Dynamic trace:** Run in debugger with breakpoint at the call site of `GetProcAddress`, log the resolved API name on each hit
4. Build the resolved IAT; re-run static analysis treating resolved APIs as if they were imports

### String encryption

No readable strings despite reasonable size. The strings exist but are XOR'd / RC4'd / AES'd at rest, decrypted on demand.

**Signal:** string count low for binary size, but `xor` / `mov byte ptr [rbp-N], imm` patterns in disasm (stack string construction).

**Escalation:** find the decryption routine (look for `xor` loops, `sub` loops with constants), set a breakpoint after decryption, dump the decrypted buffer. Or emulate the routine in Unicorn / Python.

**Concrete workflow:**
1. Find the decryption routine via pattern matching:
   - Look for `xor` instruction loops (`xor [reg], val; inc reg; dec counter; jnz loop_start`)
   - Look for `mov byte ptr [rbp-N], imm8` sequences (stack string construction with subsequent XOR)
2. Identify the key (constant, derived from system info, or hardcoded)
3. Two paths:
   a. **Static emulate:** Reproduce the routine in Python; run on encrypted blob; output plaintext
   b. **Dynamic capture:** Set breakpoint after the decryption routine returns; dump `[rbp-N]` buffer; the buffer now contains plaintext
4. Replace encrypted blobs with plaintext in your analysis (in a copy of the binary)

### VM-based obfuscation (Themida, VMProtect, custom)

Static disassembly shows a dispatcher loop that fetches bytecode from a data section and switches on opcode. The original logic is in the bytecode, not in x86.

**Signal:** small `.text` (just the dispatcher), large `.data` or `.vmp0`, indirect jumps through a state variable, no recognizable function structure.

**Escalation:** this is a research-grade problem. Either (a) symbolically execute (angr) to explore paths, (b) write a custom lifter that maps VM opcodes to native IR, or (c) trace dynamic execution and build a state->target map. Each takes days to weeks. Don't try to do this in a single audit; mark BLOCKED.

**Concrete workflow (best-effort):**
1. Confirm VM presence (dispatcher pattern + bytecode fetch loop)
2. Identify VM entry and exit points (look for native -> VM and VM -> native transitions)
3. Try symbolic execution with angr:
   ```python
   import angr
   p = angr.Project('sample.exe', auto_load_libs=False)
   s = p.factory.entry_state()
   sm = p.factory.simgr(s)
   sm.explore(find=lambda s: s.solver.eval(s.regs.rip) == target_addr)
   ```
4. If symbolic execution times out (likely for large VMs), fall back to dynamic tracing
5. Mark as BLOCKED with the partial findings you did extract (e.g., "VM dispatcher at 0x401000; bytecode section at .vmp0=0x600000; entry native->VM transition at 0x401100; cannot recover original logic without custom lifter — research effort estimated at 2-3 weeks")

### Self-modifying code

The binary rewrites its own `.text` section at runtime (via `VirtualProtect(PAGE_EXECUTE_READWRITE)` then `mov` to `.text`).

**Signal:** `VirtualProtect` call with PAGE_EXECUTE_READWRITE (0x40) on a `.text` address; writes to `.text` after the protect.

**Escalation:** set a memory write breakpoint on `.text` in the debugger, dump the modified bytes after each write, re-disassemble. The modified bytes are the "real" code.

**Concrete workflow:**
1. Find `VirtualProtect` calls; check the target address (third arg) and protection flag (fourth arg = 0x40)
2. Confirm target address is within `.text` section (compare to section header)
3. In debugger (x64dbg): set memory write breakpoint on the `.text` region
4. When breakpoint hits, dump the modified bytes
5. Re-disassemble the modified region

### Indirect syscalls

The binary avoids `ntdll.dll` by issuing `syscall` instructions directly with hand-prepared args. Static can see the `syscall` instruction but not the syscall number easily (it's in a register, computed at runtime).

**Signal:** `syscall` instruction preceded by `mov eax, <number>` where the number is computed, not literal.

**Escalation:** dynamic trace, breakpoint at `syscall`, log `rax` (syscall number) and args. Map to syscall table.

**Concrete workflow:**
1. Find `syscall` instructions: `objdump -d binary | grep syscall`
2. Check the instruction preceding each `syscall` — look for `mov eax, <reg>` or `mov eax, [rsp+N]`
3. Trace back where the number is computed (often via XOR or table lookup)
4. Two paths:
   a. **Emulate:** Reproduce the computation in Unicorn; identify which syscall numbers are reachable
   b. **Dynamic trace:** Run in debugger, breakpoint at `syscall`, log `rax` per hit; map to syscall name via the syscall table for the OS version

## When dynamic hits its limits

Dynamic isn't a silver bullet. It has its own walls.

### Anti-debugging

The binary detects the debugger and exits / changes behavior. Static can identify the anti-debug (imports, `IsDebuggerPresent`, PEB checks), but dynamic can't proceed without bypass.

**Bypass:** patch the anti-debug to return 0, or use a stealth debugger (ScyllaHide, TitanHide), or run in an emulator (Unicorn / Qiling) that fakes the absence of a debugger.

See `re-playbooks/anti-debug-evasion.md` for the full 30+ technique catalog.

### Anti-VM

The binary detects VM artifacts (registry keys, MAC address prefixes, CPUID leaves) and exits. Same problem as anti-debug.

**Bypass:** make the VM look like bare metal (install VMware Tools, set realistic RAM/CPU, add user files), or patch the checks, or run on bare metal if you have a sacrificial machine.

### Time bombs

The binary sleeps to evade automated analysis time limits (e.g., `Sleep(60000)` to wait out a 30-second dynamic window).

**Bypass:** hook `Sleep` / `nanosleep` to return immediately, or run with sleep-skipping debugger extension, or just wait (long dynamic runs are fine for one-off analysis).

### Code that requires specific input

The binary only reveals behavior with the right magic bytes, command-line args, or environment. Without them, it does nothing.

**Bypass:** static to find the input validation (compare against expected magic, hash, or signature). Construct input that passes. Run dynamic with that input.

## The "confirm, don't discover" principle

Dynamic should confirm hypotheses from static, not discover behavior from scratch. If you don't know what to look for before you run dynamic, you'll generate a pile of capture logs and not know what's signal.

Static: form hypotheses ("binary connects to C2 at IP X, sends hostname + screenshot, then waits for command").
Dynamic: confirm or refute each hypothesis ("Y connects to X; N no screenshot — instead sends clipboard contents; new hypothesis: this is a clipboard stealer").

This back-and-forth is the work. Each pass refines the model.

## The "1 sample = anecdote" principle

A single dynamic run is an anecdote, not a finding. Variance in:

- Network conditions (DNS resolution, NAT behavior)
- Timing (sleep bombs, jitter)
- Environmental state (registry, files)
- Random seeds

...can change observed behavior. Run 2-3 executions and compare. If behavior is consistent, you have a finding. If it varies, mark INCONCLUSIVE and explain what would stabilize it.

## The "environment is part of the report" principle

Document the analysis environment config in the report:

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
| Standard binary, not packed, not obfuscated | Y enough | optional confirm | Static gets you 80%; dynamic confirms |
| Packed binary (UPX, Themida, custom) | N sees stub only | Y dump memory after unpack | Static can't recover original logic |
| Dynamically-resolved APIs | partial (hash function) | Y breakpoint on GetProcAddress | Dynamic resolves the table |
| Encrypted strings | N sees encryption only | Y breakpoint after decrypt | Static can't read encrypted |
| VM-protected (Themida VM, VMP) | N sees dispatcher only | Y symbolic / trace | Multi-week effort; consider BLOCKED |
| Network behavior | from strings + imports | Y run dynamically with FakeNet | Static infers; dynamic confirms |
| File / registry behavior | from imports | Y Process Monitor | Same |
| Malware family attribution | Y enough usually | optional | String / struct / import signals often suffice |
| YARA rule generation | Y enough | optional | String + structural patterns are stable across variants |
| CTF rev challenge | Y enough usually | optional (gdb for hard cases) | Most CTF rev is static; some need dynamic for anti-debug |
| Behavior only triggered by specific input | partial (input validation) | Y with constructed input | Static reveals the input shape; dynamic confirms behavior |
| Self-modifying code | N sees original only | Y breakpoint on .text writes | Static can't predict runtime modifications |
| Indirect syscalls | partial (syscall instr visible) | Y breakpoint at syscall | Static can't see computed syscall numbers |
| Anti-debug present | Y identify techniques | Y with bypass | Static identifies; dynamic bypasses then observes |

## Per-situation escalation scripts — concrete commands

### For "binary is packed" escalation

```bash
# 1. Identify packer
python -c "
import pefile, sys
pe = pefile.PE('sample.exe')
for section in pe.sections:
    name = section.Name.rstrip(b'\\x00').decode('latin-1')
    print(f'{name}: entropy={section.get_entropy():.2f}, size={section.SizeOfRawData:#x}')
"

# 2. If UPX — unpack statically
upx -d sample.exe -o sample_unpacked.exe

# 3. If Themida/VMProtect — dynamic unpack in VM
#    See re-playbooks/packers-handling.md for VM-based unpacking workflow
```

### For "empty IAT" escalation

```bash
# 1. Confirm IAT is sparse
python -c "
import pefile
pe = pefile.PE('sample.exe')
try:
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        print(f'{entry.dll.decode()}: {len(entry.imports)} functions')
        for imp in entry.imports:
            print(f'  {imp.name}')
except AttributeError:
    print('No imports found — likely PEB-walk API resolution')
"

# 2. Find hash-comparison strings or constants in disasm
objdump -d sample.exe | grep -E "(cmp|test).*0x[0-9a-f]{8}" | head -20

# 3. Try common hash functions (ROR-13 first; most common in shellcode)
python -c "
def ror13(s):
    h = 0
    for c in s:
        h = ((h >> 13) | (h << 19)) & 0xFFFFFFFF
        h = (h + ord(c)) & 0xFFFFFFFF
    return h
# Common API names to test
for api in ['LoadLibraryA', 'GetProcAddress', 'VirtualAlloc', 'CreateThread', 'WriteProcessMemory']:
    print(f'{api}: {hex(ror13(api))}')
"
```

### For "encrypted strings" escalation

```bash
# 1. Find XOR loop in disasm
objdump -d sample.exe | grep -B1 -A5 "xor.*byte" | head -30

# 2. Identify stack-string construction (mov byte ptr [rbp-N], imm8 sequences)
objdump -d sample.exe | grep "mov.*byte.*ptr.*\[rbp-" | head -20

# 3. Extract encrypted blob addresses, dump them
objdump -s -j .data sample.exe | head -20
```

### For "self-modifying code" escalation

```bash
# 1. Find VirtualProtect calls
objdump -d sample.exe | grep -B1 "call.*VirtualProtect" | head -10

# 2. Check the protection flag (4th arg, often pushed or in register)
#    PAGE_EXECUTE_READWRITE = 0x40
#    Look for "mov ecx, 0x40" or "push 0x40" before the VirtualProtect call

# 3. In x64dbg / WinDbg:
#    - Set memory write breakpoint on .text region
#    - When hit, dump modified bytes
#    - Re-disassemble from the modified region
```

## Tool chain matrix

| Need | Static tool | Dynamic tool |
|------|-------------|--------------|
| Triage PE | `pefile`, `re_triage.py` (this skill's script) | Process Monitor (ProcMon) |
| Triage ELF | `pyelftools`, `readelf` | strace, ltrace |
| Strings | `strings`, `floss` (decompressor) | x64dbg memory dump + strings |
| Disasm | `objdump`, `radare2`, `Ghidra`, `IDA` | x64dbg / WinDbg live disasm |
| Decompilation | Ghidra, IDA Hex-Rays | (limited; mostly a static layer) |
| API trace | (none — static can't trace) | API Monitor, Frida |
| Network | (none — static can only infer) | FakeNet-NG, Wireshark, INetSim |
| Filesystem | (none — static can only infer) | Process Monitor |
| Registry | (none — static can only infer) | Process Monitor, RegShot |
| Emulation (sandboxed) | Unicorn (straight-line, single-instruction) | Qiling (full-system emulation) |
| Symbolic execution | angr (heavyweight, days to set up) | (limited) |
| Debugger | (static debuggers don't exist) | x64dbg, WinDbg, gdb, lldb |
| Memory dump | (static only sees file on disk) | Scylla, pe-sieve, process dump tools |
| Anti-debug bypass | (static identifies the techniques) | ScyllaHide, TitanHide, Scylla |

## The "evidence at each layer" rule

Static findings cite bytes (offsets, instructions, IAT entries). Dynamic findings cite runtime artifacts (memory addresses at runtime, captured API calls, network packets). Don't mix — the reader can't verify a static-only claim with dynamic evidence, and vice versa.

When a finding has both static and dynamic evidence, structure it:

```
Finding: Process injection (P0)
Static evidence:
  - 0x401200: call OpenProcess
  - 0x40124A: call VirtualAllocEx (PAGE_EXECUTE_READWRITE)
  - 0x40125C: call WriteProcessMemory
  - 0x401234: call CreateRemoteThread

Dynamic evidence (run #1, 2026-08-24, VM=VirtualBox 7.0 + Win10 22H2):
  - OpenProcess called on explorer.exe (PID 1234)
  - VirtualAllocEx allocated 0x1000 bytes at 0x20000000 in target
  - WriteProcessMemory wrote 0x1000 bytes from 0x400000 to 0x20000000
  - CreateRemoteThread spawned thread at 0x20000000 in target PID 1234
  - (API Monitor log: api_log_2026-08-24_001.bin, sha256=...)

Both layers confirm. The static evidence is necessary (proves the
capability is in the binary); the dynamic evidence is sufficient
(proves the behavior occurred on execution).
```

This structure tells the reader: static proves what the binary *can* do; dynamic proves what it *did* do. Both layers together = a strong finding. Only one = a weaker finding.

## The "static is necessary, dynamic is sufficient" rule

In malware analysis:
- Static evidence proves capability (the binary CAN do X)
- Dynamic evidence proves behavior (the binary DID do X on execution)
- A strong finding has both

Static-only findings (this binary CAN do X) are valid — some behavior only triggers under specific conditions you can't reproduce. Mark them as static-only and explain why dynamic couldn't confirm.

Dynamic-only findings (this binary DID do X on this run) are weaker — without static evidence, you can't say the behavior is in the binary itself, vs the environment (e.g., a code path triggered only because the VM had a specific registry key). Mark them as dynamic-only and explain what static evidence you couldn't find.

## Verification checklist — for the agent before deciding analysis layer

Before committing to an analysis layer (static-only vs static + dynamic), check:

- [ ] Binary is not packed (or packing is identified and unpacking is feasible)
- [ ] IAT is not sparse (or hash function is recoverable)
- [ ] Strings are not encrypted (or decryption routine is identifiable)
- [ ] No VM-based obfuscation detected (or marked BLOCKED with partial findings)
- [ ] No self-modifying code detected (or dynamic dump workflow planned)
- [ ] Static has produced a hypothesis list (specific behaviors to confirm/refute)
- [ ] Dynamic environment is documented (or planned, with VM/OS/tooling specified)
- [ ] 5-minute verifiability test passes for static findings
- [ ] Reproducibility test passes for dynamic findings (env + command + hash documented)
- [ ] If findings are dynamic-only, the env-specific nature is called out
- [ ] If findings are static-only, the reason dynamic couldn't confirm is documented

If any checkbox is unchecked, the analysis isn't ready for the report — go back and complete the layer that's incomplete.

## Final hook

> "What's the cheapest signal that confirms or refutes my current hypothesis?" If static can do it, use static. If static can't, escalate to dynamic with a specific question to answer — not a vague "let's see what it does."
