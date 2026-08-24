# Anti-Debug, Anti-VM & Anti-Analysis Evasion — Recognition and Bypass

The techniques malware authors and commercial protectors use to detect debuggers, virtual machines, sandboxes, and analysis tools — and how to bypass each one to enable static and dynamic analysis. This playbook is a catalog: technique → signature → bypass.

This is a reference, not a how-to for writing malware. The techniques are listed because an analyst who doesn't recognize them will waste hours on a binary that "won't run" or "crashes for no reason" in the debugger. Every technique here is well-documented in public malware research (Microsoft, Mandiant, ESET, Kaspersky, AVAST) and in academic RE literature.

---

## 1. The four evasion categories

Evasion techniques cluster into four buckets:

1. **Debugger detection** — `IsDebuggerPresent`, `NtQueryInformationProcess`, PEB checks, timing, hardware breakpoints
2. **VM/sandbox detection** — `cpuid` vendor check, MAC prefix check, registry/file check, port I/O
3. **Analysis tool detection** — process scan (Process Explorer, Wireshark, x64dbg running), window class check, driver check
4. **Timing-based evasion** — `rdtsc` deltas, `Sleep` followed by `GetTickCount` deltas, deferred execution

Each technique has a known bypass. The bypass is usually a one-instruction patch or a context manipulation.

---

## 2. Debugger detection techniques

### 2.1 Direct API checks

| Technique | Call / pattern | Detection signature in disasm |
|---|---|---|
| `IsDebuggerPresent` | `call KERNEL32!IsDebuggerPresent` | `mov eax, fs:[0x30]; movzx eax, byte ptr [eax+2]` (direct PEB.BeingDebugged read) |
| `CheckRemoteDebuggerPresent` | `call KERNEL32!CheckRemoteDebuggerPresent` | `push handle; lea rcx, [out_ptr]; call ...` |
| `NtQueryInformationProcess(ProcessDebugPort)` | `push 7 (ProcessDebugPort); ...` | `mov edx, 7; ... call ntdll!NtQueryInformationProcess` |
| `NtQueryInformationProcess(ProcessDebugFlags)` | `push 0x1F` | `mov edx, 1Fh; ... call ...` |
| `NtQueryInformationProcess(ProcessDebugObjectHandle)` | `push 0x1E` | `mov edx, 1Eh; ... call ...` |
| `NtSetInformationThread(ThreadHideFromDebugger)` | `push 0x11; push 0; push -2; ...` | `mov edx, 11h; xor r8d, r8d; mov r9, -2; call ntdll!NtSetInformationThread` |
| `OutputDebugString` retrieval | `call KERNEL32!OutputDebugStringA` followed by `GetLastError` check | LastError is 0 if no debugger attached (pre-Vista) |

### 2.2 PEB direct checks

The Process Environment Block (PEB) is accessible from `fs:[0x30]` (32-bit) or `gs:[0x60]` (64-bit) on Windows. The PEB contains:

| Field | Offset | Detection technique |
|---|---|---|
| `BeingDebugged` | +0x02 (byte) | `mov eax, fs:[30h]; movzx ecx, byte ptr [eax+2]; test ecx, ecx; jne dbg_detected` |
| `NtGlobalFlag` | +0x68 (32-bit) / +0xBC (64-bit) | FLG_HEAP_ENABLE_TAIL_CHECK (0x10) + FLG_HEAP_ENABLE_FREE_CHECK (0x20) + FLG_HEAP_VALIDATE_PARAMETERS (0x40) = 0x70 if debugger-created process |
| `Heap ForceFlags` | +0x18 in PEB.ProcessHeap (32-bit), +0x44 in 64-bit | Set to non-zero when process was created by debugger |
| `Heap Flags` | +0x0C (32-bit), +0x70 (64-bit) | Same pattern as NtGlobalFlag |
| `NtGlobalFlag` emitter (kernel side) | +0xBF in TEB | `mov eax, fs:[30h]; mov eax, [eax+0BCh]; ...` |

### 2.3 Hardware breakpoint checks (DR0-DR7)

Debuggers set hardware breakpoints via `DR0-DR3` (address), `DR7` (control). Malware can read these via:

- `mov eax, dr0` / `mov eax, dr7` (privileged — requires ring 0, but `NtGetContextThread` exposes them to ring 3 with `CONTEXT_DEBUG_REGISTERS`)
- `GetThreadContext(thread, &ctx); check ctx.Dr0..Dr7` — uses `CONTEXT_DEBUG_REGISTERS` flag

Detection signature: `call KERNEL32!GetThreadContext` followed by `cmp` on the DR fields of the context struct.

### 2.4 Timing checks (rdtsc, GetTickCount, QueryPerformanceCounter)

Debuggers slow execution dramatically (1000x for single-step). Malware measures elapsed time and rejects if too long.

| Technique | Code pattern | Bypass |
|---|---|---|
| `rdtsc` deltas | `rdtsc; sub eax, ebx; cmp eax, 1000000; ja dbg_detected` | Patch the `cmp` / `ja` to NOPs or invert the condition |
| `GetTickCount` deltas | `call KERNEL32!GetTickCount; sub eax, [saved_tick]; cmp eax, 1000; ja dbg_detected` | Same — patch the comparison |
| `QueryPerformanceCounter` deltas | `call KERNEL32!QueryPerformanceCounter; ... sub; cmp; ja` | Same |
| `NtQuerySystemTime` deltas | `call ntdll!NtQuerySystemTime` | Same |

Detection in disasm: look for `rdtsc`/`QueryPerformanceCounter` calls paired with `sub` + `cmp` against a constant threshold (often `0x100000` or larger). Two `rdtsc` calls back-to-back with subtraction is the signature.

### 2.5 `int 2d` (debug service interrupt)

`int 2d` is the kernel debugger service interrupt. When executed under a debugger, it triggers a breakpoint. When executed natively, it raises an exception that the malware's VEH (vectored exception handler) catches — and uses the catch as a "no debugger attached" signal.

```
int     2Dh             ; raises EXCEPTION_SINGLE_STEP if debugger
; if debugger: debugger stops here
; if no debugger: VEH catches, execution continues here
mov     eax, "not_debugged"
```

Detection: `int 2Dh` near entry point. Bypass: NOP the instruction.

### 2.6 `int 3` self-check (debugger trap)

Malware compares its own code byte at a known offset with `0xCC` (int 3). If a debugger set a breakpoint there, the byte becomes `0xCC`. If not, it's the original instruction byte.

```
mov     eax, [rip+offset_to_self_check_addr]
cmp     al, 0CCh              ; is there a breakpoint installed?
je      dbg_detected
```

Detection: `cmp al, 0CCh` near entry point. Bypass: patch the `je` to `jmp dbg_detected+5` (skip the check) or NOP the `cmp`.

### 2.7 Software breakpoint scan

Same as above but scans an entire function body for `0xCC`:

```
mov     esi, [rip+offset_to_function_start]
mov     ecx, [rip+offset_to_function_size]
loop:
    cmp     byte ptr [esi], 0CCh
    je      dbg_detected
    inc     esi
    dec     ecx
    jnz     loop
```

Detection: byte-scan loop with `0xCC` comparison. Bypass: use hardware breakpoints instead of software breakpoints, or patch the `je dbg_detected` to `nop`.

### 2.8 `NtCreateThreadEx`-based self-check

Malware creates a thread at the same address as the current thread's RIP. If debugger is attached, the new thread is created in a "broken" state and `GetThreadContext` reveals different DR registers. If no debugger, the new thread is clean.

Detection: `NtCreateThreadEx` calls immediately followed by `GetThreadContext` and comparison.

### 2.9 `VEH` (vectored exception handler) trap

Malware registers a VEH that catches exceptions, then deliberately raises one (divide by zero, invalid memory access). If VEH runs, "no debugger". If the exception propagates to the unhandled exception filter (and a debugger catches it), "debugger attached".

```c
AddVectoredExceptionHandler(1, my_veh);
int zero = 0;
int x = 1 / zero;   // raises EXCEPTION_INT_DIVIDE_BY_ZERO
// if VEH caught it: no debugger
// if propagated: debugger
```

Detection: `AddVectoredExceptionHandler` near entry, followed by a `div` by zero or `mov` to invalid address.

### 2.10 `SEH` (structured exception handler) chain abuse

Similar to VEH but uses SEH. Malware installs an SEH handler that catches the exception. If debugger is attached, the debugger's handler takes precedence.

Detection: `push offset handler; push fs:[0]; mov fs:[0], esp` (install SEH) followed by a deliberate exception.

### 2.11 `NtYieldExecution`-based check

`NtYieldExecution` relinquishes the current thread's time slice. If a debugger is attached, the call returns immediately (debugger doesn't switch away). If not, the OS scheduler switches to another thread.

Detection: `call ntdll!NtYieldExecution` followed by checking some side effect.

---

## 3. VM / sandbox detection techniques

### 3.1 `cpuid` vendor check (VMware, VirtualBox, Hyper-V)

```
mov     eax, 0x40000000
cpuid                        ; returns vendor string in ebx:ecx:edx
cmp     ebx, 'VMXh'         ; VMware
je      vm_detected
cmp     ebx, 'VBox'         ; VirtualBox (older)
je      vm_detected
cmp     ebx, 'Micr'         ; Microsoft Hyper-V
je      vm_detected
cmp     ebx, 'KVMK'         ; KVM
je      vm_detected
cmp     ebx, 'XenV'         ; Xen
je      vm_detected
```

Detection: `mov eax, 40000000h; cpuid` followed by string comparisons on `ebx`/`ecx`/`edx`.

Bypass: patch the `cpuid` instruction's return values, or NOP the comparison. Under VMware/VBox, you can also disable the VM extensions or fake the cpuid response via the VM's settings.

### 3.2 Port I/O check (VMware backdoor)

```
mov     eax, 564D5868h      ; 'VMXh' magic
mov     dx, 5658h           ; VMware backdoor port
in     eax, dx              ; if VMware, returns a non-zero value in ebx
; if not VMware, raises an exception
```

Detection: `in eax, dx` where `dx` is `0x5658` (VMware) or `0x568` (older VBox).

Bypass: NOP the `in` instruction, or hook the VEH to catch the resulting exception and fake the return.

### 3.3 MAC address check

```
; GetAdaptersInfo or NDIS request to read MAC
; First 3 bytes are OUI (vendor)
cmp     word ptr [mac+0], 0005_69h  ; VMware VMnet0
cmp     word ptr [mac+0], 000C_29h  ; VMware ESX
cmp     word ptr [mac+0], 0800_27h  ; VirtualBox
cmp     word ptr [mac+0], 001C_42h  ; Parallels
cmp     word ptr [mac+0], 0015_5Dh  ; Hyper-V
```

Detection: `GetAdaptersInfo`/`getifaddrs` call followed by byte comparisons on the first 3 bytes.

Bypass: change the VM's MAC in the VM config; or patch the comparison in the malware.

### 3.4 Process / window class scan

Malware enumerates running processes and window classes:

```
Processes to look for:
- vmtoolsd.exe, vmwaretrat.exe, vmwareuser.exe (VMware Tools)
- VBoxService.exe, VBoxTray.exe (VirtualBox Guest Additions)
- prl_cc.exe, prl_tools.exe (Parallels)
- xenservice.exe (Citrix Xen)
- SBIEMUX.exe (Sandboxie)
- cuckoomon.dll / cuckoomon-x64.dll (Cuckoo Sandbox)

Window classes:
- VBoxTrayToolClass
- VBoxTrayToolShadowClass
- VMToolClipboardClass

Window titles:
- "Process Explorer" (Sysinternals)
- "Process Monitor"
- "Wireshark"
- "OLLYDBG" (OllyDbg)
- "x64dbg" / "x32dbg"
- "IDA" (Interactive Disassembler)
- "WinDbg"
- "Fiddler"
- "HTTPDebugger"
- "OSScope"
```

Detection: `EnumWindows` + `GetClassName` / `EnumProcessModules` + module name comparisons.

Bypass: rename tools, hide processes, or patch the enumeration.

### 3.5 Registry / file existence checks

```
Registry keys to look for:
- HKLM\SOFTWARE\VMware, Inc.\VMware Tools
- HKLM\SOFTWARE\Oracle\VirtualBox Guest Additions
- HKLM\SYSTEM\CurrentControlSet\Services\VBoxGuest
- HKLM\HARDWARE\DEVICEMAP\Scsi\Scsi Port 0\Scsi Bus 0\Target Id 0\Logical Unit Id 0\Identifier
  (the value often contains "VBOX" or "VMWARE")

Files to look for:
- C:\Windows\System32\drivers\vboxguest.sys
- C:\Windows\System32\drivers\vmhgfs.sys
- C:\Windows\System32\drivers\vmmouse.sys
- C:\Program Files\VMware\*
- C:\Program Files\Oracle\VirtualBox Guest Additions\*
- C:\Windows\System32\VBoxControl.exe
- C:\Windows\System32\VBoxService.exe

Special file paths (low-level check):
- \\.\VBoxGuest (VirtualBox driver device name)
- \\.\VBoxTrayIPC
- \\.\pipe\VBoxTrayIPC
- \\.\VBoxMouse
- \\.\VBoxVideo
```

Detection: `RegOpenKeyEx`/`RegQueryValueEx` followed by string compares; `CreateFile` with `\\.\VBoxGuest` paths.

### 3.6 ACPI / firmware strings

```
; Read from BIOS / ACPI
; Look for:
- "VBOX" in DMI/SMBIOS strings
- "VMWARE" in DMI strings
- "VirtualBox" in firmware version strings
- "QEMU" in firmware
- "Bochs" in BIOS ROM
- "Hyper-V" in BIOS strings
```

Detection: `GetSystemFirmwareTable('RSMB')` call followed by byte scans.

### 3.7 CPU feature checks (modern)

```
; Modern CPUs have RDTSCP which forces "aux" register
; VMs may not properly implement it
rdtscp                       ; raises #GP if not supported
; If #GP raised and caught by VEH/SEH → CPU is too old OR running in a limited VM
```

Or:

```
; Check for certain hypervisor-present bit
mov     eax, 1
cpuid
test    ecx, 1 shl 31       ; hypervisor present bit (CPUID.1:ECX[31])
jnz     vm_detected
```

If bit 31 of ECX after CPUID(1) is set, a hypervisor is present.

### 3.8 Timing checks for VMs

```
; Loop with a long sequence of instructions
; Measure elapsed time
; Real CPU: fast (e.g., 50,000 cycles)
; VM under instrumentation: slow (e.g., 5,000,000 cycles)
; Threshold: > 1,000,000 cycles → VM_detected
```

Detection: `rdtsc; mov ebx, eax; [long loop]; rdtsc; sub eax, ebx; cmp eax, 1000000`.

---

## 4. Bypass techniques — the universal patterns

### 4.1 NOP the check instruction

For most detection checks, the simplest bypass is to NOP the comparison or the conditional jump:

```
Before:
mov     eax, fs:[30h]
movzx   eax, byte ptr [eax+2]  ; read PEB.BeingDebugged
test    eax, eax
jne     dbg_detected            ; if debugger, jump to detected path
; ... continue normal execution ...

After (patched):
mov     eax, fs:[30h]
movzx   eax, byte ptr [eax+2]
test    eax, eax
nop                            ; was: jne dbg_detected
nop
nop
nop
nop
nop
; ... continue normal execution ...
```

The detection check now has no effect. The malware runs as if no debugger were present.

### 4.2 Invert the conditional

For one-instruction `je`/`jne` checks, swap them:

```
je      dbg_detected  →  jne     dbg_detected
```

If the check expected "no debugger" (`je dbg_detected` means "if equal, jump to detected"), inverting means the malware only triggers if a debugger IS attached (so it now correctly continues when no debugger). Wait — that's the wrong semantics. Let me re-examine.

Original: `test eax, eax; je dbg_detected`. If eax is 0 (no debugger), `je` is taken and goes to dbg_detected — that's the *opposite* of what we want. Let me redo:

Original: `test eax, eax; jne dbg_detected`. If eax is 0 (no debugger), `jne` not taken, continues. If eax is 1 (debugger), jumps to dbg_detected.

Patch: change `jne dbg_detected` to `nop` or `jmp dbg_detected+N` (skip the detection branch).

Better patch: invert: `je dbg_detected` means "if no debugger, jump to detected path" — which is wrong. So just NOPing is safer.

### 4.3 Patch the API return value

If the malware calls `IsDebuggerPresent` and the result is non-zero, it's detected. Patch the API at its entry point to always return 0:

```
Original KERNEL32!IsDebuggerPresent:
    mov     eax, fs:[30h]
    movzx   eax, byte ptr [eax+2]
    ret

Patched:
    xor     eax, eax          ; always return 0
    ret
```

This works for API-based checks. In a debugger, set a breakpoint at the API entry, and use the "patch" feature to overwrite the first bytes.

### 4.4 Hook the VEH/SEH to return desired values

For exception-based checks (int 2d, int 3 self-check), install a VEH that always returns `EXCEPTION_CONTINUE_EXECUTION` and sets the context's EAX to the "no debugger" value:

```c
LONG WINAPI my_veh(PEXCEPTION_POINTERS ep) {
    if (ep->ExceptionRecord->ExceptionCode == EXCEPTION_SINGLE_STEP) {
        ep->ContextRecord->Eax = 0;  // "no debugger"
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
```

This catches every exception-based check uniformly.

### 4.5 Use hardware breakpoints instead of software

Software breakpoints (`0xCC` bytes) are detectable via the int-3-scan technique. Hardware breakpoints (set via DR0-DR3) are not visible in code bytes.

Use x64dbg's "Hardware Breakpoint" option, or WinDbg's `ba` (break on access) command. The malware can still detect DR registers via `GetThreadContext`, but the byte-scan won't fire.

### 4.6 Use a stealth debugger

ScyllaHide (x64dbg plugin) hooks most detection APIs and returns "no debugger" results. TitanHide (kernel driver) hides from ring-0 checks. These hide:
- `IsDebuggerPresent` → returns 0
- `NtQueryInformationProcess(DebugPort)` → returns 0
- `NtQueryInformationProcess(DebugFlags)` → returns 1 (no debugger)
- PEB.BeingDebugged → 0
- PEB.NtGlobalFlag → 0
- Heap ForceFlags → 0
- DR registers in `GetThreadContext` → 0
- `NtSetInformationThread(ThreadHideFromDebugger)` → silently succeeds

For deep analysis, ScyllaHide + TitanHide is the standard stealth stack.

### 4.7 Patch the `cpuid` instruction

For VM detection via cpuid vendor check, hook the cpuid instruction:

```
Original cpuid_handler (host CPU):
mov     eax, 0x40000000
cpuid
; ebx = "VMXh" if VMware

Patched cpuid_handler (interposed):
; install a #GP handler that catches cpuid and returns the host's vendor string
; (e.g., return "GenuineIntel" or "AuthenticAMD")
```

Under VMware, you can edit the `.vmx` config to add `cpuid.40000000.ebx = "GenuineIntel"` (and similar for ecx and edx). This makes cpuid(0x40000000) return the host's vendor, defeating the check.

### 4.8 Hide the VMware/VBox tools

Rename `vmtoolsd.exe` to `system32.exe`. Hide the `C:\Program Files\VMware\` directory (move it). Disable the `VBoxGuest` driver. These hide the existence of guest tools.

For deeper hiding: rename the window classes via registry patches, hide the device objects.

---

## 5. The "scan and patch" workflow

When you encounter a packed/protected binary that won't run in your debugger:

1. **Static pass first**: dump the binary's `.text` section, search for the detection patterns in this catalog:
   - `mov eax, fs:[30h]` / `mov eax, gs:[60h]` (PEB access)
   - `mov edx, 7` / `mov edx, 1Fh` / `mov edx, 1Eh` (NtQueryInformationProcess)
   - `cpuid` near entry (vendor check)
   - `rdtsc` paired with `cmp eax` (timing check)
   - `int 2Dh` (debug service)
   - `cmp al, 0CCh` (breakpoint scan)
   - `in eax, dx` where `dx` is `5658h` or `568h` (VMware backdoor)

2. **For each hit, note the address** and the bypass:
   - API check → patch API to return clean value
   - Direct PEB check → NOP the conditional jump
   - Timing check → NOP the comparison or extend the threshold
   - cpuid → patch return value (or hook the instruction)
   - in/out → NOP the in/out instruction

3. **Apply all patches in x64dbg's "Patches" dialog**. Save the patched binary (Scylla or "Dump" → save to new file).

4. **Run the patched binary** in the debugger. It should now bypass the detection and reach OEP.

5. **Re-verify** by static scanning the patched binary for any missed detections. Some malware runs multiple passes of detection.

---

## 6. The catalog — single-page reference

| Technique | Signature (bytes / instruction pattern) | Bypass |
|---|---|---|
| `IsDebuggerPresent` (PEB.BeingDebugged read) | `64 A1 30 00 00 00 0F B6 40 02` | NOP the `jne` after the read |
| `CheckRemoteDebuggerPresent` API | import in IAT + call site | Patch API to return 0 |
| `NtQueryInformationProcess(ProcessDebugPort=7)` | `mov edx, 7` near `NtQueryInformationProcess` | Patch the API to return 0 in out ptr |
| `NtQueryInformationProcess(ProcessDebugFlags=0x1F)` | `mov edx, 1Fh` | Same |
| `NtQueryInformationProcess(ProcessDebugObjectHandle=0x1E)` | `mov edx, 1Eh` | Same |
| `NtSetInformationThread(ThreadHideFromDebugger=0x11)` | `mov edx, 11h` | NOP the call |
| `rdtsc` deltas | `rdtsc; mov ebx, eax; ...; rdtsc; sub eax, ebx; cmp eax, threshold; ja detected` | NOP the `cmp`/`ja` |
| `int 2Dh` | `CD 2D` byte sequence | NOP the `int 2Dh` (replace with `90 90`) |
| `int 3` self-check | `cmp al, 0CCh` | NOP the comparison or the `je` after |
| SW breakpoint scan | `repnz scasb` with `al=0CCh` or explicit byte loop | Use hardware breakpoints |
| `cpuid` vendor check | `B8 00 00 00 40; 0F A2` then string compares | Patch cpuid return via VM config |
| `in eax, dx` VMware backdoor | `BA 58 56 00 00; ED 58 56 00 00; EC` (in al, dx) | NOP the `in` instruction |
| MAC prefix check | byte comparison `cmp [mac+0], 0005_69h` | Change VM MAC in VM config |
| `GetAdaptersInfo` then MAC compare | API call + byte compare | Same |
| Process scan for analysis tools | `EnumProcesses` + name compare | Rename tools, hide via kernel hook |
| Window class scan | `FindWindow` + class name compare | Hide window classes |
| File existence checks (`C:\Program Files\VMware\*`) | `CreateFile` or `GetFileAttributes` | Move/rename the directory |
| Registry checks | `RegOpenKeyEx` + `RegQueryValueEx` | Patch the API to return success without checking |
| `NtQuerySystemTime`/`GetSystemTime` deltas | API call pair + subtraction + comparison | NOP the comparison |
| Hardware breakpoint check | `GetThreadContext` + `cmp [ctx+4], 0` on DR fields | Use ScyllaHide or NOP the comparison |
| Heap ForceFlags check | `mov eax, fs:[30h]; mov eax, [eax+18h]; mov eax, [eax+44h]; test eax, eax` | Patch via ScyllaHide |
| `NtGlobalFlag` check | `mov eax, fs:[30h]; mov eax, [eax+68h]` (32-bit) or `[eax+0BCh]` (64-bit); `test eax, 70h` | ScyllaHide |

---

## 7. Reporting evasion techniques

For every evasion technique detected, include in the report:

1. **Category** (debugger / VM / sandbox / timing / API-scan)
2. **Specific technique** (e.g., `IsDebuggerPresent`, `cpuid` vendor check)
3. **Address** in the binary where the check is located
4. **Bypass** (instruction-level patch description)
5. **Severity** — usually P2 (informational; doesn't break the binary's function, just blocks analysis)
6. **Recommended action** — apply patch in debugger, run patched binary to reach OEP

Example finding:

```
SUSPECTED anti-debug: rdtsc-based timing check.
Evidence:
- 0x401234: rdtsc
- 0x401236: mov ebx, eax           ; save start time
- 0x401238: (15 instructions of computation, ~50 cycles)
- 0x401250: rdtsc
- 0x401252: sub eax, ebx            ; compute elapsed
- 0x401254: cmp eax, 10000h        ; threshold: 1M cycles
- 0x401259: ja 0x401300             ; if exceeded, jump to "detected" branch

Bypass: NOP 0x401259-0x40125E (6 bytes: `0F 87 XX XX XX XX` → 6 × 0x90).
Recommended: apply patch in x64dbg, dump patched binary, run to reach OEP.
```

---

## 8. The detection-avoidance arms race

Many protectors now use **multi-stage evasion**:
- Stage 1: simple `IsDebuggerPresent` check (looks for the obvious)
- Stage 2: `rdtsc` deltas (looks for the analyst who bypassed stage 1)
- Stage 3: `cpuid` + `in` ports (looks for the VM-based analyst)
- Stage 4: behavioral check (does the binary think it has human interaction — e.g., mouse movement, random window focus changes)

For each stage, a different bypass applies. The general principle: **patch every detection you find in static analysis, then verify the binary reaches OEP**. If OEP is still not reached, scan the deeper code (post-OEP) for additional checks.

Some protectors (Themida, VMProtect) install **runtime checks** that run inside the unpacked code itself. These require dynamic instrumentation: hook the detection APIs, patch their returns, and continue.

The analyst's edge: the malware has a finite budget for detection (each check costs bytes and cycles). The catalog of techniques is bounded. Patience + systematic scan finds all of them.
