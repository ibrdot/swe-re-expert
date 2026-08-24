# Anti-Pattern Recognition — Spotting Obfuscation, Packers, Anti-Debug

When a binary resists standard analysis, recognize the technique fast. Each technique has tell-tale indicators in static analysis. Here's how to spot each.

## The tell-tale indicator table

| Technique | Static indicator | Quick test |
|-----------|-------------------|-------------|
| UPX packing | `UPX!` magic, `UPX0`/`UPX1` sections | `upx -d <target>` (usually works) |
| Themida packing | `.themida` section, VM-based | Need dynamic unpack |
| VMProtect | `.vmp0`/`.vmp1` sections | Need dynamic unpack |
| Custom packing | High-entropy `.text`, small entry stub | Need dynamic unpack |
| Anti-debug: PEB | `IsDebuggerPresent` in imports | Patch to return 0 |
| Anti-debug: ptrace | `ptrace(PTRACE_TRACEME)` (Linux) | LD_PRELOAD fake ptrace |
| Anti-debug: timing | `rdtsc` pairs around code | Patch jumps |
| Anti-VM: strings | Strings like "VMware", "VirtualBox" | Patch strings |
| Anti-VM: CPUID | `cpuid` with eax=0x40000000 | Patch result |
| Anti-analysis: timing-based evasion | `Sleep` calls with long durations | Hook to return immediately |
| String encryption | No readable strings, XOR loops in disasm | Find decrypt routine, emulate |
| Control flow flattening | Switch dispatcher with state variable | Trace execution, map state→target |
| Code virtualization | Custom VM interpreter | Multi-week recovery |
| Self-modifying code | `VirtualProtect(PAGE_EXECUTE_READWRITE)` on `.text` | Breakpoint on write, dump |
| Indirect syscalls | `syscall` not preceded by libc call | Trace rax, map to syscall table |
| API hashing | No imports, runtime resolution by hash | Run hash function against API names |
| Reflective DLL loading | Custom loader, no PE entry stub | Dump after load |

## UPX packing — the easy case

UPX is the most common packer and the easiest to deal with.

### Detection

```bash
# Strings / section names
strings -a <target> | grep UPX
objdump -h <target> | grep -E "UPX0|UPX1"

# Or via the magic bytes in the file header
xxd <target> | head -5    # Look for "UPX!" near the start
```

### Unpack

```bash
upx -d <target>            # Decompresses in place (overwrites the file!)
upx -d -o <unpacked> <target>  # Decompresses to a new file
```

If `upx -d` fails (common if the binary was modified after packing), you may need to:
1. Restore the original UPX headers (find `UPX!` magic at offset N, restore header)
2. Or unpack dynamically: run under gdb, breakpoint at the OEP (original entry point), dump memory

### After unpacking

Re-run triage on the unpacked binary. Strings, imports, disasm should now reflect the original code.

## Custom packing / Themida / VMProtect

These packers are harder. They use VM-based protection or runtime decryption.

### Detection

- Themida: `.themida` section, often large
- VMProtect: `.vmp0`/`.vmp1` sections
- Custom: high-entropy `.text` section (>7.5 entropy), small entry stub that does some setup then jumps to allocated memory

### Unpack

You need dynamic unpacking. The pattern is:

1. Run the binary under a debugger (or Unicorn/Qiling)
2. Wait for the unpacker to finish (it'll jump to the OEP — original entry point)
3. At the OEP, dump the process memory
4. Fix up the dump (rebuild PE/ELF headers, IAT)
5. Analyze the dump statically

Tools:
- **Scylla** (Windows) — dumps a process and reconstructs IAT
- **LordPE** — alternative
- **gdb** + manual dump (Linux): `dump memory out.bin 0x400000 0x500000`
- **Unicorn** + custom script — emulate the unpacker, dump memory at OEP

### After unpacking

The unpacked memory is your real target. Re-run all static analysis on it.

## Anti-debugging techniques

### PEB-based (Windows)

The binary checks the Process Environment Block for `BeingDebugged` flag.

**Detection in imports:**
- `IsDebuggerPresent` (direct)
- `CheckRemoteDebuggerPresent` (more thorough)
- `NtQueryInformationProcess` (very flexible — can check `ProcessDebugPort`, `ProcessDebugFlags`, `ProcessDebugObjectHandle`)

**Detection in disasm:**
```asm
mov    rax, QWORD PTR gs:[0x60]    ; PEB
movzx  eax, BYTE PTR [rax+0x2]     ; BeingDebugged
test   eax, eax
jne    .Lexit
```

**Bypass:** patch the `jne` to `nop` or `je`. Or use ScyllaHide / TitanHide (stealth debugger).

### ptrace-based (Linux)

On Linux, a process can only be traced by one tracer. Malware calls `ptrace(PTRACE_TRACEME, 0, 0, 0)` on itself; if it returns -1, a debugger is attached.

**Detection in disasm:**
```asm
mov    rax, 101          ; syscall number for ptrace (x86-64)
mov    rdi, 0             ; PTRACE_TRACEME
mov    rsi, 0
mov    rdx, 0
mov    r10, 0
syscall
test   rax, rax
js     .Lexit              ; if negative, debugger attached
```

**Bypass:** LD_PRELOAD a fake ptrace that always returns 0:
```c
long ptrace(int request, ...) {
    return 0;
}
```

Or patch the `js` to `nop` / `jns`.

### Timing checks

The binary measures time between two points; if the delta is too large, a debugger is slowing it down.

**Detection in disasm:**
```asm
rdtsc                       ; read timestamp counter
mov    [rbp-N], eax          ; save low
mov    [rbp-N+4], edx        ; save high
; ... code being measured ...
rdtsc
sub    eax, [rbp-N]
sbb    edx, [rbp-N+4]
cmp    eax, 0x100000          ; threshold
jg     .Lexit                 ; if delta > threshold, exit
```

**Bypass:** patch the `jg` to `nop`. Or run in a deterministic VM (Unicorn with deterministic instruction counts).

### Hardware breakpoint detection

The binary checks debug registers (DR0–DR7) for hardware breakpoints.

**Detection:** uses `NtQueryInformationThread` or direct `mov` from debug registers (`mov rax, dr0`).

**Bypass:** don't use hardware breakpoints. Use software breakpoints (`int3`) instead, or patch the check.

## Anti-VM techniques

### String-based VM detection

Strings like `VMware`, `VirtualBox`, `VBox`, `QEMU`, `Xen`, `Hyper-V` are scanned in:
- Registry keys (`HKLM\HARDWARE\DESCRIPTION\System\BIOS`)
- File paths (`C:\Windows\System32\drivers\VBoxMouse.sys`)
- Process names (`vboxservice.exe`, `vmtoolsd.exe`)
- MAC address prefixes (`00:05:69` = VMware, `08:00:27` = VirtualBox)

**Bypass:** rename the VM, remove guest additions, patch strings in the binary.

### CPUID-based

```asm
mov    eax, 0x40000000    ; hypervisor leaf
cpuid
cmp    ecx, 0x61774d56    ; "VMwa" — VMware
je     .Lexit
```

Or for the brand string:
```asm
mov    eax, 0x40000001    ; hypervisor feature leaf
cpuid
```

**Bypass:** patch the `cpuid` instruction or its result. Some hypervisors allow you to set the CPUID brand string.

### Timing-based

VMs are slower than bare metal. Timing checks (similar to anti-debug) detect the slowdown.

**Bypass:** same as anti-debug timing — patch the check.

## String encryption

When strings are encrypted at rest and decrypted on demand, `strings` returns nothing useful.

### Detection

- Binary is reasonable size (e.g., 100KB+) but `strings -a` returns few readable strings
- Disasm has many `xor` loops, or `sub`/`add` chains on stack buffers
- Stack strings: `mov byte ptr [rbp-N], 0xXX` repeated many times (building strings byte-by-byte)

### Bypass

Find the decryption routine. It's typically:
- A small function (10-50 instructions)
- Takes a pointer (the encrypted blob) and returns a pointer (the decrypted string)
- Has `xor` / `add` / `rol` instructions
- Called from many places (the strings are decrypted as needed)

Approach 1: **Emulate the function** with Unicorn / Python — pass encrypted blobs, get plaintext back.

Approach 2: **Dynamic dump** — run under gdb, breakpoint after the decryption call, dump the plaintext buffer.

Approach 3: **Ghidra script** — write a script that finds the decryption routine, applies it to all callers, replaces the encrypted blob with the decrypted string in the listing.

## Control flow flattening

The binary's control flow is destroyed and replaced with a state machine:

```asm
mov    [rbp-N], 0x12345      ; initial state
.Ldispatcher:
mov    eax, [rbp-N]
jmp    [table + eax*8]       ; jump to handler for state
.Lhandler1:
; ... actual code ...
mov    [rbp-N], 0x67890      ; transition to next state
jmp    .Ldispatcher
.Lhandler2:
...
```

### Detection

- Main function has a `jmp [table + eax*8]` dispatcher pattern
- Many handlers that all `jmp` back to the dispatcher
- State variable (often on the stack) being constantly updated
- Few `call` instructions (calls are flattened too)

### Bypass

This is hard. Options:

1. **Trace dynamic execution** — run under tracer (Unicorn, gdb), record every state transition, build a state→target map
2. **Symbolic execution** — angr can sometimes trace through CFF
3. **Recover the CFG manually** — for each handler, find what state it transitions to; build the original CFG

Plan on 4-8 hours per function for full recovery.

## Code virtualization (VMProtect, Themida VM, custom)

The original code is compiled to a custom bytecode; the binary contains a VM interpreter that executes the bytecode.

### Detection

- Large `.text` with a single dispatcher function
- Large `.data` section with byte sequences (the bytecode)
- The "main" function does:
  ```asm
  .Ldispatch:
  mov    rax, [rbp+pc]       ; PC
  movzx  rax, byte [rax]    ; opcode
  jmp    [jump_table + rax*8]  ; jump to handler
  .Lhandler_add:
  ; handler for ADD opcode
  inc    [rbp+pc]
  jmp    .Ldispatch
  ```

### Bypass

This is research-grade. Options:

1. **Map VM opcodes to native semantics** — write a "lifter" that converts VM bytecode to a higher-level IR
2. **Trace dynamic execution** — record every opcode execution, build execution traces
3. **Symbolic execution** — angr or manticore with VM-aware execution

Plan on 1-4 weeks for full recovery. For most practical purposes, you'd mark BLOCKED and look for the behavior via dynamic execution instead.

## Self-modifying code

The binary writes to its own `.text` section at runtime, modifying the code that executes.

### Detection

PE: `VirtualProtect` with `PAGE_EXECUTE_READWRITE` (0x40) on an address in `.text`'s range.
ELF: `mprotect` with `PROT_EXEC | PROT_WRITE` on an address in `.text`'s range.

### Bypass

Set a memory write breakpoint on the modified `.text` address:
- gdb: `watch *(char*)0x401234`
- IDA / Ghidra / x64dbg: similar

When the breakpoint hits, dump the modified bytes; that's the "real" code that will execute. Disassemble those bytes statically.

## Indirect syscalls

The binary avoids `ntdll.dll` (which is hooked by EDRs) by issuing `syscall` instructions directly with the syscall number in `rax`.

### Detection

`syscall` instruction not preceded by `call ntdll!NtXxx`. The syscall number is in `rax`, often loaded from a computed value (so you can't easily tell which syscall it is without runtime analysis).

### Bypass

Dynamic trace: breakpoint on `syscall`, log `rax` and other arg registers. Map `rax` to syscall number → name.

Common syscall numbers (Linux x86-64):
- 0 = read, 1 = write, 2 = open, 3 = close
- 9 = mmap, 11 = munmap
- 39 = getpid, 41 = socket, 42 = connect, 44 = sendto, 45 = recvfrom
- 57 = fork, 59 = execve

## API hashing

The binary doesn't import APIs by name — it resolves them at runtime by hash.

### Detection

- PE IAT is empty or only has `kernel32!LoadLibraryA` / `kernel32!GetProcAddress`
- Disasm has loops with `ror` / `rol` / `xor` followed by `cmp` against constants (the API name hashes)

### Bypass

1. Find the hash function (the loop with `ror`/`xor`)
2. Reimplement it in Python
3. Run it against a list of common Windows API names
4. Match the hashes to known APIs

Common hash algorithms in malware:
- ROR-13 (used by Metasploit, Carbanak, many C++ malware)
- CRC32
- FNV-1a
- Custom (just `xor` of bytes with a magic constant)

## When to give up

Some binaries are too obfuscated to reverse in reasonable time. Recognize when to stop:

- VM-protected code (multi-week effort)
- Control flow flattening across many functions (similar)
- Encrypted everything with no obvious decrypt routine (custom crypto)

For these, dynamic execution in an instrumented VM with good telemetry (Process Monitor, Sysmon, FakeNet-NG, Wireshark) is more cost-effective than static recovery. Mark the report as `BLOCKED` and explain what would unblock it.
