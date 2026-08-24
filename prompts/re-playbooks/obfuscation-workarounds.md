# Obfuscation Workarounds — Dealing with Resistant Binaries

When a binary resists standard analysis, here's the menu of techniques to fall back to. Each has a cost and a payoff; pick the cheapest one that answers the question.

## The escalation ladder

```
Static analysis → fails
   ↓
Try unpack (UPX, etc.) → may succeed
   ↓
Try dynamic unpack (dump memory at OEP) → usually succeeds for packers
   ↓
Try emulation (Unicorn / Qiling) → for anti-debug-heavy binaries
   ↓
Try symbolic execution (angr) → for complex logic / VM-based
   ↓
Try dynamic analysis (instrumented execution) → for behavior discovery
   ↓
Accept BLOCKED → mark in report, explain what would unblock
```

## Tier 1: Standard unpacking

### UPX

```bash
upx -d <target>                    # in-place
upx -d -o out.bin <target>          # to new file
```

If `upx -d` fails with "NotPacked" or "CantUnpackFile":

1. Check if it's actually UPX (look for `UPX!` magic)
2. Headers may have been modified. Try restoring:
   ```bash
   # The UPX! magic is at a fixed offset in the file
   # Find it, restore the surrounding header bytes from a known UPX binary
   ```
3. Or unpack dynamically (run, dump memory at OEP)

### ASPack / MPRESS / Petite / mPress

Most old-school packers have unpackers in `PE Explorer`, `ASPack2Unpacker`, or similar tools. Try them first.

### Themida / VMProtect

No automatic unpacker exists. Must do dynamic unpack:

1. Run in isolated VM under x64dbg or gdb
2. Find the OEP (original entry point):
   - Set breakpoint on memory access to the unpacked region
   - The unpacker writes the original code to memory, then jumps to it
   - The jump target is the OEP
3. At OEP, dump the process:
   - **Scylla** (Windows) — best, also rebuilds IAT
   - **LordPE** — alternative
   - `gcore <pid>` then convert the core to PE/ELF (Linux)
   - `dump memory out.bin 0x400000 0x500000` (gdb)
4. Rebuild PE/ELF headers if needed
5. Re-run static analysis on the dump

## Tier 2: Emulation

When anti-debug / anti-VM prevents dynamic analysis, emulate.

### Unicorn for single functions

If you just need to decrypt strings or resolve API hashes:

```python
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RIP, UC_X86_REG_RSP, UC_X86_REG_RDI, UC_X86_REG_RSI

# Map memory regions
emu = Uc(UC_ARCH_X86, UC_MODE_64)
emu.mem_map(0x400000, 0x10000)        # code
emu.mem_map(0x100000, 0x10000)        # stack
emu.mem_map(0x600000, 0x10000)        # heap

# Load code
with open('<target>', 'rb') as f:
    data = f.read()
emu.mem_write(0x400000, data[code_offset:code_offset+code_size])

# Set up stack
emu.reg_write(UC_X86_REG_RSP, 0x110000)

# Set args (calling convention: System V AMD64)
emu.reg_write(UC_X86_REG_RDI, 0x600000)  # arg1 = encrypted string ptr
emu.mem_write(0x600000, encrypted_string_bytes)

# Run from function start
emu.emu_start(0x401000, 0x401050)  # from func_start to func_end

# Read result
plaintext = emu.mem_read(0x600000, plaintext_length)
```

This runs the function in isolation — the full binary never executes, so anti-debug checks inside other functions don't trigger.

### Qiling for full binary emulation

When you need the whole binary (cross-platform, no real execution):

```python
from qiling import Qiling

ql = Qiling(["./target.elf"], {"rootfs": "/path/to/rootfs"}, multithread=True)

# Hook syscalls, intercept network, etc.
ql.set_syscall(0x101, my_hook)        # replace syscall 0x101 (write) with custom

ql.run()
```

Qiling handles libc, syscalls, even some framework code. Good for:
- Running binaries that won't run natively (cross-arch, cross-platform)
- Capturing dynamic behavior without a real VM
- Bypassing anti-debug (no real debugger to detect)

## Tier 3: Symbolic execution

When the binary's logic is too complex to read manually but you need to understand it (e.g., CTF challenges, VM-based code):

### angr

```python
import angr

proj = angr.Project('./target', auto_load_libs=False)

# Find a state where "correct" is printed, avoid states where "wrong" is printed
state = proj.factory.entry_state()
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=lambda s: b'correct' in s.posix.dumps(1),
                avoid=lambda s: b'wrong' in s.posix.dumps(1))

if simgr.found:
    found = simgr.found[0]
    print(found.posix.dumps(0))   # input that triggers "correct"
```

angr explores all possible paths symbolically. It can solve:
- CTF challenges where you need to find the input that passes the check
- Functions with complex conditionals where you want all paths
- VM-based challenges (sometimes — depends on the VM complexity)

Limitations:
- State explosion (exponential in branches) — limited to short functions / small programs
- Doesn't handle syscalls / I/O well
- Slow — minutes to hours per analysis

### manticore

Alternative symbolic executor. Similar trade-offs. Use when angr is too slow or when you need a different approach to the same problem.

## Tier 4: Dynamic analysis (instrumented execution)

When static, emulation, and symbolic all fail or aren't worth the effort:

### The analysis VM stack

```
Analysis VM:
├── OS: Windows 10/11 or Ubuntu 22.04
├── RAM: 4 GB+
├── CPU: 2+ cores
├── Network: Host-only adapter (NO real internet)
│   └── FakeNet-NG or INetSim on the host (fake services)
├── Snapshot: taken BEFORE sample execution
├── Tools installed:
│   ├── Process Monitor (Windows) / strace (Linux)
│   ├── Process Explorer / top
│   ├── Autoruns (Windows)
│   ├── Regshot (Windows) — for registry diff
│   ├── Sysmon (Windows) — config: process, network, file, registry, driver
│   ├── Wireshark / tcpdump
│   ├── Sysinternals Suite
│   └── Cuckoo / CAPE Agent (for automated collection)
└── Account: limited user (matches typical target user context)
```

### Execution procedure

1. Restore snapshot (clean state)
2. Start the monitoring tools
3. Take a Regshot baseline (Windows)
4. Copy the sample in (no network during copy)
5. Execute the sample (the way the target user would invoke it)
6. Wait 30-60 seconds (or longer if it's a slow-moving sample)
7. Stop monitoring, capture logs
8. Take a Regshot diff (Windows)
9. Restore snapshot

Analyze logs for:
- Process tree (Process Monitor / strace)
- File system changes (Process Monitor / ltrace)
- Registry changes (Regshot / Process Monitor)
- Network activity (Wireshark / FakeNet-NG logs)
- Sysmon events (1=process, 3=network, 7=image load, 8=remote thread, 10=process cross-pid, 11=file create, 13=registry value set, 22=DNS)

## Tier 5: Anti-debug bypass techniques

When the binary detects the debugger and exits:

### Software breakpoints vs hardware

- **Software breakpoints (`int3`)** modify the code — easy to detect (binary can checksum itself)
- **Hardware breakpoints (DR0-DR7)** don't modify code — harder to detect, but limited to 4

Use hardware breakpoints for anti-debug-aware binaries.

### ScyllaHide (Windows)

Plugins for x64dbg / OllyDbg that hook the APIs the binary uses to detect the debugger:
- `IsDebuggerPresent` → returns 0
- `NtQueryInformationProcess` → returns 0 for ProcessDebugPort
- `CheckRemoteDebuggerPresent` → returns 0
- Hide debug registers
- Hide thread handles
- etc.

### TitanHide (kernel-level)

Driver that hides the debugger at the kernel level. More robust than ScyllaHide (which is user-mode).

### Patching the checks

Find the check (look for `IsDebuggerPresent` / `ptrace` / `rdtsc` patterns in disasm), patch:
- `je <fail>` → `nop` (skip the fail branch)
- `jne <fail>` → `jmp <success>` (always take success)
- The call to `IsDebuggerPresent` → `mov eax, 0; nop` (force the return value)

### Stealth debuggers

- **x64dbg with ScyllaHide** — most common setup
- **TitanHide + x64dbg** — more robust
- **Unicorn emulation** — no debugger to detect
- **dbx / dbgv** — alternative debuggers with stealth features

## Tier 6: Anti-VM bypass

When the binary detects the VM and exits:

### Make the VM look real

- Install VMware Tools / VirtualBox Guest Additions (some samples check for missing tools)
- Set RAM ≥ 4 GB, CPU ≥ 2 cores
- Set realistic screen resolution (1920×1080)
- Add user files, browser history, recent documents
- Rename the VM to something neutral (samples sometimes fingerprint the VM name)
- Remove obvious VM registry keys (under `HKLM\HARDWARE\DESCRIPTION\System\BIOS`)
- Patch VM-specific MAC addresses (change to a non-VM OUI)

### Patch the checks

Same as anti-debug: find the check (`cpuid`, string scans), patch to bypass.

### Run on bare metal

If you have a sacrificial machine (cheap laptop, disposable VM host), use it. Bare metal is undetectable as VM.

## Tier 7: String decryption

When strings are encrypted at rest:

### Find the decryption routine

Look for:
- Small functions (10-50 instructions)
- `xor` loops, `sub` / `add` chains
- Called from many places (the strings are decrypted on demand)
- Takes a pointer arg (the encrypted blob), returns a pointer (the decrypted string)

### Emulate the decryption

```python
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import *

# Load the binary's text section into Unicorn
# Set up the args (encrypted blob address in rdi)
# Call the decryption function
# Read the decrypted string from the returned address
```

### Dynamic dump

Run in debugger, breakpoint after the decryption call, dump the plaintext buffer:
```gdb
b *decrypt_func+end_offset
r
# When breakpoint hits:
x/s $rax    # print string at rax (assuming rax is the return ptr)
```

### Bulk extract with a script

For malware with many encrypted strings, write a Ghidra script that:
1. Finds all xrefs to the decryption function
2. For each call site, identifies the encrypted blob address (loaded into rdi before the call)
3. Emulates the call (Unicorn)
4. Replaces the encrypted blob in the Ghidra listing with the decrypted string

This recovers all strings in the binary automatically. Saves hours of manual work.

## When to give up

Recognize when the binary is too obfuscated for reasonable analysis:

- **VM-protected code** (Themida VM, VMProtect VM, custom VM with hundreds of opcodes) — multi-week effort
- **Control flow flattening across many functions** — similar
- **Custom encryption everywhere with no obvious decrypt routine** — sometimes impossible

For these, dynamic execution in an instrumented VM with good telemetry is more cost-effective than static recovery. The report should mark `BLOCKED` and explain:
- What was tried
- Why it failed
- What would unblock (specific technique, tool, time investment)
- What was still learned despite the limitation

Don't fabricate understanding. "I couldn't recover the inner logic; here's what I learned from behavior" is a valid conclusion.
