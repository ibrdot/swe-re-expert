# Binary Analysis Playbook — Static → Dynamic → Semantic Recovery

This is the agent's reference whenever the target is a **native binary** (ELF, PE, Mach-O, raw firmware) of unknown behavior. The goal: turn a stack of bytes into a structured understanding of what the binary does, supported by evidence (offsets, instructions, call targets).

The pipeline has three layers. Each layer's output feeds the next: static signals form hypotheses, dynamic traces confirm them, semantic recovery rebuilds the high-level picture.

---

## Layer 1 — Static analysis (no execution)

Static work is the default. It's reproducible, leaves no trace, and gives the strongest evidence-per-minute. Always exhaust static before dynamic.

### 1.1 File identification & metadata

```bash
file <target>                       # Magic bytes, arch, endianness, linkage
md5sum <target>; sha256sum <target>  # Identity
stat <target>                       # Size, timestamps
```

For ELF specifically:
```bash
readelf -a <target>                 # Headers, sections, symbols, relocations, segments
readelf -d <target>                 # Dynamic section: NEEDED libs, RUNPATH, BIND_NOW, FLAGS
objdump -x <target>                 # Headers + disassembly header
```

For PE (Windows):
```bash
python -c "import pefile; pe=pefile.PE('<target>'); print(pe.dump_info())"
# Sections, imports, exports, resources, version info, debug directory
```

For Mach-O (macOS / iOS):
```bash
otool -hv <target>                 # Mach-O header
otool -L <target>                  # Linked libraries
otool -I <target>                  # Imports
otool -l <target>                  # Load commands
```

The bundled `scripts/re_triage.py --file <target> --all` does this across all three formats and produces one JSON.

### 1.2 Security features & compilation profile

```bash
# ELF
checksec --file=<target>            # NX, PIE, RELRO, canary, FORTIFY
readelf -l <target> | grep GNU_STACK
readelf -d <target> | grep -E "BIND_NOW|FLAGS"

# PE
python -c "import pefile; pe=pefile.PE('<target>'); pe.parse_data_directories(); \
  print('NX (DEP):', pe.OPTIONAL_HEADER.DllCharacteristics & 0x100); \
  print('ASLR:', pe.OPTIONAL_HEADER.DllCharacteristics & 0x40); \
  print('CFG:', pe.OPTIONAL_HEADER.DllCharacteristics & 0x4000)"
```

What each tells you:
- **NX/DEP** — non-executable stack. If absent, simple stack overflow → RCE.
- **PIE/ASLR** — position-independent / randomized base. Affects exploit reliability, not analysis.
- **RELRO** — read-only relocations after load. `Full RELRO` resolves all GOT entries at load → no GOT overwrite.
- **Stack canary** — `__stack_chk_fail` in imports / canary check in prologue. Affects overflow exploitation.
- **FORTIFY** — `__*_chk` imports → bounds-checked libc calls.

Compiler / toolchain hints:
- `GCC: (` in `.comment` section → GCC; version string tells you the era
- `Go build ID` or `.gopclntab` section → Go binary (see language-depth.md)
- `.rustc` section → Rust binary
- `Microsoft (R) ... C/C++` in `.comment` → MSVC
- `UPX!` in first bytes → UPX packed (`upx -d` to unpack)
- `Themida`/`VMProtect` markers → commercial packer (heavy work)

### 1.3 Strings & embedded data

```bash
strings -a -n 4 <target> | sort -u > strings.txt
strings -e l -n 4 <target>          # UTF-16LE (Windows-heavy binaries)
strings -e b -n 4 <target>          # UTF-16BE

# Categorize
grep -E "https?://|[0-9]{1,3}(\.[0-9]{1,3}){3}" strings.txt     # Network indicators
grep -E "/(etc|usr|var|tmp|home|root)/" strings.txt             # *nix paths
grep -E "[A-Za-z]:\\\\" strings.txt                             # Windows paths
grep -iE "pass|key|secret|token|admin|login|auth" strings.txt  # Cred hints
grep -E "^[A-Za-z0-9+/]{20,}={0,2}$" strings.txt                # base64 blobs
grep -E "\b[A-Fa-f0-9]{32,}\b" strings.txt                       # hex blobs / hashes
```

For obfuscated strings (no readable strings despite reasonable size):
- Look for `xor` loops in disassembly — classic string decryption
- Look for stack-strings built byte-by-byte (`mov byte ptr [rbp-X], 0xYY`)
- Look for `cmp` chains building strings to evade `strings`

### 1.4 Imports & exports

```bash
# ELF
readelf --dyn-syms <target>          # Dynamic symbols (imports for ELF)
nm -D <target>                       # Dynamic symbols, alt format
objdump -T <target>                  # Dynamic symbol table

# PE
python -c "import pefile; pe=pefile.PE('<target>'); \
  [print(e.name.decode() if e.name else ord(e.ordinal_lookup) for e in pe.DIRECTORY_ENTRY_IMPORT[0].imports)]"

# Mach-O
otool -Iv <target>                   # Indirect symbol table (imports)
```

High-signal imports by category:

| Category | Functions |
|----------|-----------|
| Process injection | `CreateRemoteThread`, `VirtualAllocEx`, `WriteProcessMemory`, `NtMapViewOfSection`, `QueueUserAPC`, `RtlCreateUserThread` |
| Persistence | `RegSetValueEx`, `CreateService`, `WinExec`, `ShellExecute`, scheduled task APIs |
| Anti-analysis | `IsDebuggerPresent`, `CheckRemoteDebuggerPresent`, `NtQueryInformationProcess`, `GetTickCount`, `QueryPerformanceCounter`, `rdtsc` patterns |
| Network | `WSAStartup`, `socket`, `connect`, `InternetOpenUrl`, `HttpSendRequest`, `WinHttpOpen`, `URLDownloadToFile` |
| Credential access | `LsaOpenPolicy`, `SamConnect`, `LogonUser`, `RevertToSelf`, `RegOpenCurrentUser` |
| Keylogging | `SetWindowsHookEx`, `GetAsyncKeyState`, `GetKeyState`, `GetForegroundWindow` |
| Evasion | `VirtualProtect`, `NtProtectVirtualMemory`, `Wow64DisableWow64FsRedirection`, `NtSetInformationThread` (hide from debugger) |
| Crypto | `CryptEncrypt`, `BCryptEncrypt`, `CryptHashData`, `EVP_EncryptInit_ex` (OpenSSL) |

### 1.5 Entropy & packing detection

```bash
python scripts/re_triage.py --file <target> --entropy
```

Per-section entropy interpretation:

| Entropy | Meaning |
|---------|---------|
| 0.0–1.0 | Empty or all-zero section |
| 1.0–5.0 | Normal code or ASCII data |
| 5.0–7.0 | Compressed data; could be normal for `.rodata` with media |
| 7.0–7.9 | Encrypted or packed — investigate |
| 7.9–8.0 | Almost certainly encrypted/compressed payload |

High-entropy `.text` (in a non-Go/Rust binary) suggests packing. Cross-check with section names: UPX0/UPX1, `.themida`, `.vmp0`, `.enigma1` are packer signatures.

### 1.6 Disassembly

```bash
# ELF
objdump -d -M intel <target>                  # Disassemble, Intel syntax
objdump -d -M intel <target> | grep -E "^[0-9a-f]+ <"   # Function list
objdump -d -M intel <target> | awk '/^[0-9a-f]+ </{f=$0} /call/{print f, $0}'  # Calls per function

# PE — useobjdump via wine, or python + capstone (bundled in scripts/re_disasm.py)
python scripts/re_disasm.py --file <target> --entry

# Stripped binaries — find functions by prologue patterns
objdump -d -M intel <target> | grep -B1 "push   rbp" | grep -E "^[0-9a-f]+:"
```

Ghidra headless for the heavy lifting:
```bash
$GHIDRA_INSTALL_DIR/support/analyzeHeadless /tmp Project1 <target_name> \
    -import <target> \
    -postScript ExportFunctionList.java \
    -scriptPath /path/to/scripts
```

The bundled `scripts/re_disasm.py` produces a JSON with: entry point, functions (start, end, name, call/jump targets), per-function basic block count, suspicious instruction patterns. It uses capstone and supports x86, x64, ARM, ARM64, MIPS.

### 1.7 Cross-referencing

Build a mental model by cross-referencing:
1. Pick a high-signal import (e.g. `CreateRemoteThread`)
2. Find its callers (objdump `call` lines or Ghidra xrefs)
3. Walk backward from the call to find the function prologue
4. Identify what prepares the args (the `WriteProcessMemory` + `VirtualAllocEx` chain)
5. Annotate the function with its reconstructed purpose

This is the heart of static RE: follow the imports backward until you understand the behavior.

---

## Layer 2 — Dynamic analysis (when static is inconclusive)

Dynamic confirms what static hypothesizes. Use it to:
- Resolve dynamically-resolved APIs (GetProcAddress loops, PEB walk)
- Decrypt strings that the static pass identified as encrypted
- Trace execution to map a VM-based obfuscator
- Capture network behavior

### 2.1 Debuggers

| Tool | Best for | Notes |
|------|----------|-------|
| `gdb` + `pwndbg`/`gef`/`peda` | ELF on Linux | Most versatile; pwndg adds context menus |
| `windbg` (WinDbgX / WinDbg Preview) | PE on Windows | Kernel + user mode; `!peb`, `!teb` handy |
| `lldb` | Mach-O on macOS | Apple's debugger; scriptable with Python |
| `x64dbg` | PE on Windows (GUI) | Good for manual stepping |
| `radare2` / `r2` | Any | Scriptable, decent for static+dynamic mix |

Useful GDB/pwndbg patterns:
```
info functions                       # List functions
disas main                           # Disassemble main
disas 0x401000,0x401050               # Range
b *0x401234                          # Break at address
b *main+42                           # Break at offset
r < input.txt                        # Run with stdin
watch *(int*)0x601040                # Hardware watchpoint on memory
set *(int*)0x601040 = 0xdeadbeef     # Patch memory at runtime
x/20wx 0x601040                      # Examine memory
set disassembly-flavor intel
set disassemble-next-line on         # Show next instr as you step
context                              # pwndbg: full context panel
```

### 2.2 Tracing

```bash
strace -f -e trace=network,open,read,write,execve <target>  # Syscalls
ltrace -f <target>                                            # Library calls
lsof -p <pid>                                                 # Open files
ss -tunap | grep <pid>                                        # Network connections
tcpdump -i any -w trace.pcap host <suspected-c2>              # Traffic capture
```

On Windows: **Process Monitor** (sysinternals) for FS/registry/network, **API Monitor** for per-API args, **Wireshark** for network.

### 2.3 Emulation (when you can't or won't run it)

Emulation lets you trace execution without exposing real resources. Use it to:
- Decrypt strings by running the decryption routine in isolation
- Resolve API hashes by running the resolver function
- Explore VM-protected code by feeding bytecode to the VM

```python
# Unicorn for single-function emulation
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RIP, UC_X86_REG_RSP

# Map code, stack, set registers, run from entry, hook reads/writes
# Capstone for disasm of executed instructions

# Qiling for full-binary emulation (handles libc / syscalls)
from qiling import Qiling
ql = Qiling(["./target.elf"], {"rootfs": "/"}, multithread=True)
ql.run()
```

For symbolic execution of CTF-style logic:
- `angr` — symbolic exploration; load binary, find addr, avoid addr
- `manticore` — alternative symbolic engine

---

## Layer 3 — Semantic recovery

After static and dynamic, reconstruct the high-level picture. The output is human-readable pseudocode + data structure recovery + behavior mapping.

### 3.1 Pseudocode reconstruction

From Ghidra decompiler or IDA Hex-Rays, or hand-written from disasm. The rules:

- One function at a time. Annotate, then move on.
- Identify the calling convention first (see language-depth.md for per-arch).
- Name registers by their argument role: `rdi` → `arg1`, `rsi` → `arg2`, etc. (System V AMD64).
- Look for loops (`cmp`, `jge`, `jl` back to top) and convert to `for`/`while`.
- Switch tables: `jmp [rax*8 + table]` — dump the table, map cases.
- String operations: `rep movsb` → `memcpy`; `rep stosb` → `memset`.

Example reconstruction (x86-64, GCC, System V):

```asm
push   rbp
mov    rbp, rsp
sub    rsp, 0x20
mov    QWORD PTR [rbp-0x18], rdi    ; arg1 → local buffer ptr
mov    DWORD PTR [rbp-0x4], 0x0     ; int i = 0
jmp    .L2
.L3:
mov    eax, DWORD PTR [rbp-0x4]
cdqe
lea    rdx, [rax+rax]               ; i*2
mov    rax, QWORD PTR [rbp-0x18]
add    rax, rdx
movzx  eax, BYTE PTR [rax]
sub    eax, 0x20
movsx  edx, al
mov    rax, QWORD PTR [rbp-0x18]
mov    eax, DWORD PTR [rbp-0x4]
cdqe
lea    rcx, [rax+rax]
add    rax, rcx
mov    BYTE PTR [rax], dl           ; buf[i] = buf[i] - 0x20
add    DWORD PTR [rbp-0x4], 1
.L2:
cmp    DWORD PTR [rbp-0x4], 0x9
jle    .L3
leave
ret
```

Reconstructed:
```c
// Calling convention: System V AMD64 — rdi = arg1
void lowercase_to_upper(char *buf) {
    for (int i = 0; i <= 9; i++) {
        buf[i] = buf[i] - 0x20;
    }
}
```

Note: `0x20` subtracted from a lowercase ASCII char (`a`=0x61) gives uppercase (`A`=0x41). So this is actually `lowercase_to_upper` (a common CTF-style trick). Verify the loop bound — `<= 9` means 10 chars; flag is often 10 chars in CTF.

### 3.2 Data structure recovery

Look for:
- Repeated `mov [base+0xN], val` patterns → struct field writes; infer offsets
- `mov rax, [rbx+0x18]` then `mov [rax+0x8], rcx` → nested struct, vtable, or linked list
- `cmp [rbx+0x4], 0x1` followed by a jump → enum/tag field
- Vtables: array of function pointers at struct offset 0; first field accessed through `[obj+0x0]` is the vtable ptr

Name them in your notes (`struct_conn_state`, `struct_packet_hdr`) so the pseudocode reads naturally.

### 3.3 Behavior mapping (for malware specifically)

For each function you understand, record:
- Trigger (called from where, under what condition)
- Inputs (registers / stack at entry)
- Outputs (return value, memory writes, syscalls)
- Side effects (file writes, registry changes, network sends)

This feeds the behavior → MITRE ATT&CK mapping. See `references/malware-analysis.md` for the full pipeline.

---

## Anti-analysis techniques & workarounds

When the binary resists, here's what to look for:

| Technique | Indicator | Workaround |
|-----------|-----------|------------|
| UPX packing | `UPX!` magic; `UPX0`/`UPX1` sections | `upx -d <target>` (may need to fix headers if modified) |
| Custom packing | High-entropy `.text`, small entry stub, jump to allocated region | Run in emulator, dump memory after unpack, re-analyze the dump |
| `IsDebuggerPresent` | Import present; check `peb.BeingDebugged` | Patch to return 0; or unset PEB flag in debugger |
| `NtQueryInformationProcess` with `ProcessDebugPort` | Import + magic class 7 | Patch query result to 0 |
| `ptrace(PTRACE_TRACEEME)` | Linux anti-debug; fails under tracer | `LD_PRELOAD` a fake ptrace; or patch the call to return 0 |
| Timing checks | `rdtsc` pairs around a code region, compare delta | Patch the comparison; or run in a VM with deterministic timing |
| VM detection | String scans (`VMware`, `VirtualBox`), CPUID leaf 0x40000000 | Patch strings; or run on bare metal |
| String encryption | No readable strings; XOR/ADD loops on stack | Find the decryption function; emulate it; dump decrypted strings |
| Control flow flattening | Switch dispatcher with state variable | Trace execution, build state→target map, rewrite CFG |
| Code virtualization | Custom VM interpreter, bytecode section | Recover VM dispatch loop, map handlers to semantics (slow, deep work) |
| Self-modifying code | `VirtualProtect(PAGE_EXECUTE_READWRITE)` on `.text` | Breakpoint on write; dump modified code; re-disassemble |
| Indirect syscalls | `syscall` instruction not preceded by libc call | Resolve args from registers; map to syscall number table |
| API hashing | No imports; runtime resolution by hash | Run the hash function against common API names; or set breakpoint on resolved pointer |

For each, the principle is the same: identify the technique, find the smallest patch or emulation step that resolves it, and continue with the analysis. Don't fight the obfuscation — work around it.

---

## Output contract

Use `assets/report_binary_analysis.md` for the final report. The report must include:

- **Verdict**: CLEAN / SUSPICIOUS / MALICIOUS / INCONCLUSIVE
- **Binary metadata**: hashes, type, arch, security features, toolchain
- **Behavioral summary**: 3-5 sentences on what the binary does
- **Evidence table**: per-finding offsets, instructions, call targets
- **Findings table**: severity, problem, evidence, recommended next step
- **Limitations**: what couldn't be confirmed, why, what would resolve it

Never end the report with artificial "End of Report" markers. Let the last finding's recommendation close it.
