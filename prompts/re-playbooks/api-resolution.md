# Dynamic API Resolution — PEB Walks, Hash Resolution, and Syscall Stubbing

How malware and protectors hide their API usage by not having imports visible in the IAT. The binary instead resolves API addresses at runtime via the Process Environment Block (PEB), by hashing function names and comparing against precomputed hashes, or by issuing syscalls directly (bypassing `ntdll` entirely).

This playbook covers recognition of each pattern, why it's used, what it tells you about the binary, and how to recover the resolved API set (so you can re-construct what the binary actually does).

---

## 1. Why dynamic resolution

A normal binary imports its APIs through the IAT (Import Address Table). The Windows loader populates these pointers at load time. The IAT is **plainly visible** in the PE headers and lists every API the binary uses.

For malware, this is a problem because:
- AV scanners flag based on API sets (e.g., `CreateRemoteThread` + `WriteProcessMemory` + `VirtualAllocEx` = injection pattern)
- Sandboxes pre-process the IAT and hook those APIs
- Reverse engineers see the full API surface at a glance

Dynamic resolution mitigates all three by deferring the API lookup to runtime, so the IAT shows only `kernel32!LoadLibraryA` + `kernel32!GetProcAddress` (or sometimes nothing at all). The malware then walks the PEB to find `kernel32.dll`, parses its export table, and resolves functions itself.

Three resolutions patterns, in increasing stealth:

| Pattern | IAT shows | Stealth | Bypass complexity |
|---|---|---|---|
| `LoadLibrary` + `GetProcAddress` by name | `LoadLibraryA`, `GetProcAddress`, maybe `kernel32` | Low | trivial — read the strings |
| Hash-based PEB walk | nothing useful in IAT (or just `ntdll!LdrLoadDll`) | Medium | need the hash function + a hash lookup table |
| Direct syscalls (`syscall` instruction with computed numbers) | nothing | High | need to know syscall numbers per Windows version |

---

## 2. Pattern 1 — `LoadLibrary` + `GetProcAddress` by name

### 2.1 The shape

```c
HMODULE k32 = LoadLibraryA("kernel32.dll");
pCreateRemoteThread = GetProcAddress(k32, "CreateRemoteThread");
pVirtualAllocEx     = GetProcAddress(k32, "VirtualAllocEx");
pWriteProcessMemory = GetProcAddress(k32, "WriteProcessMemory");
// ... resolve more APIs ...
// Later:
HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
LPVOID addr = pVirtualAllocEx(hProcess, NULL, 4096, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
pWriteProcessMemory(hProcess, addr, shellcode, sizeof(shellcode), NULL);
HANDLE hThread = pCreateRemoteThread(hProcess, NULL, 0, addr, NULL, 0, NULL);
```

### 2.2 Detection

- IAT has `LoadLibraryA` and `GetProcAddress` (or `LoadLibraryW` / `LdrLoadDll`)
- `.rdata` contains plain-text strings of the API names ("CreateRemoteThread", "VirtualAllocEx", "WriteProcessMemory", etc.)
- A loop walks the string list and resolves each

```asm
lea     rsi, [rip + api_names_table]   ; e.g., "CreateRemoteThread\0VirtualAllocEx\0..."
mov     rbx, qword ptr [rip + module_handle_k32]   ; HMODULE of kernel32
loop:
    mov     rcx, rsi                    ; lpProcName
    mov     rdx, rbx                    ; hModule
    call    qword ptr [rip + GetProcAddress_iat]
    mov     qword ptr [rip + api_ptr_table], rax  ; store resolved ptr
    ; advance rsi to next string
    add     rsi, [string_length + 1]   ; +1 for null terminator
    add     api_ptr_table, 8
    cmp     api_ptr_table, end_table
    jne     loop
```

### 2.3 Recovery

Trivial: extract the API name strings from `.rdata`. They're plain ASCII. The order in the table corresponds to the order of resolution. Match each string with its resolved pointer slot (the address where the malware stores the resolved API).

---

## 3. Pattern 2 — PEB walk (find `kernel32` without `LoadLibrary`)

Malware that doesn't want `LoadLibraryA` in its IAT can find `kernel32.dll` (and any other loaded DLL) by walking the PEB.

### 3.1 The PEB chain

```
TEB (Thread Environment Block, at fs:[0] / gs:[0])
  +0x30 / +0x60   PEB pointer
PEB (Process Environment Block)
  +0x18  PEB_LDR_DATA* (Ldr)
    Ldr:
      +0x10  InLoadOrderModuleList          (doubly-linked list)
      +0x20  InMemoryOrderModuleList
      +0x30  InInitializationOrderModuleList
    Each LDR_DATA_TABLE_ENTRY contains:
      +0x18  DllBase
      +0x20  EntryPoint
      +0x28  SizeOfImage
      +0x30  FullDllName (UNICODE_STRING)
      +0x40  BaseDllName (UNICODE_STRING)
```

The first three modules in `InLoadOrderModuleList` are typically:
1. The current executable itself
2. `ntdll.dll` (loaded second)
3. `kernel32.dll` (loaded third on Windows 7+, or sometimes after `kernelbase.dll` on Windows 10+)

So a PEB walk goes:

```asm
; 32-bit (Windows x86)
mov     eax, dword ptr fs:[30h]         ; PEB
mov     eax, dword ptr [eax+0Ch]        ; PEB->Ldr
mov     esi, dword ptr [eax+14h]         ; InMemoryOrderModuleList.Flink
lodsd                                    ; eax = first entry (the exe itself)
lodsd                                    ; eax = second entry (ntdll)
lodsd                                    ; eax = third entry (kernel32 or kernelbase)
mov     ebx, dword ptr [eax+10h]         ; DllBase of kernel32

; 64-bit (Windows x64)
mov     rax, qword ptr gs:[60h]          ; PEB
mov     rax, qword ptr [rax+18h]         ; PEB->Ldr
mov     rax, qword ptr [rax+20h]         ; InMemoryOrderModuleList.Flink
mov     rax, qword ptr [rax+20h]         ; 2nd entry's DllBase? (ntdll)
mov     rax, qword ptr [rax+20h]         ; 3rd entry's DllBase (kernel32)
mov     rbx, rax                         ; kernel32 base
```

Variations: some malware walks `InInitializationOrderModuleList` (offset +0x30) instead, which has a different order — kernel32 is usually second there.

### 3.2 Detection

- The signature bytes `64 A1 30 00 00 00` (32-bit, `mov eax, fs:[30h]`) or `65 48 8B 04 25 60 00 00 00` (64-bit, `mov rax, gs:[60h]`) near the entry point.
- A chain of `mov` operations walking `PEB->Ldr->List->next->next->next` followed by accessing offset `0x18` or `0x20` of the resulting LDR_DATA_TABLE_ENTRY.

### 3.3 After the PEB walk — export table parsing

Once the malware has `kernel32`'s DllBase, it parses the PE export table:

```
PE Header:
  DllBase + 0x3C              -> e_lfanew (offset to PE header)
  DllBase + e_lfanew + 0x88    -> export table RVA (32-bit)
  DllBase + e_lfanew + 0x90    -> export table RVA (64-bit, but offset may differ)
  
Export Directory (IMAGE_EXPORT_DIRECTORY):
  +0x20  AddressOfNames        -> RVA to array of name pointers
  +0x24  NumberOfNames
  +0x1C  AddressOfNameOrdinals -> RVA to array of ordinals
  +0x1C  AddressOfFunctions    -> RVA to array of function RVAs
```

The walk:
1. Iterate over `AddressOfNames`
2. For each name, compute its hash (using a known hash function)
3. Compare against the target hash (precomputed at compile time)
4. If match, use the index to look up the ordinal in `AddressOfNameOrdinals`
5. Use the ordinal to look up the function RVA in `AddressOfFunctions`
6. Final address = `DllBase + function_RVA`

### 3.4 Common hash functions

Malware uses various hash functions to obscure API names. Knowing the function lets you invert the lookup (compute hashes for all API names, build a table, find which API each hash corresponds to).

**ROR-13 hash (Metasploit, classic shellcode)**:
```c
DWORD ror13_hash(const char* name) {
    DWORD hash = 0;
    while (*name) {
        hash = (hash >> 13) | (hash << (32 - 13));  // ROR 13
        hash += *name;
        name++;
    }
    return hash;
}
```

Common hashes:
- `kernel32.dll!LoadLibraryA`     = 0x0726774C
- `kernel32.dll!GetProcAddress`   = 0x077A6343 (varies; check impl)
- `kernel32.dll!CreateProcessA`   = 0x0930C0F0
- `kernel32.dll!VirtualAlloc`     = 0x0E130DC6
- `ntdll.dll!NtCreateFile`        = 0x09C9CC52

**ROR-7 (used in older PoSeidon / Carberp)**:
- Same shape, ROR by 7.

**CRC32 (used in many packers)**:
- Standard CRC32 of the API name. Precomputed CRC32s of all Windows APIs are easy to generate.

**FNV-1a (used in modern malware)**:
- `hash = FNV_OFFSET_32; for each byte: hash = (hash ^ byte) * FNV_PRIME_32`
- FNV_OFFSET_32 = 0x811c9dc5, FNV_PRIME_32 = 0x01000193

**Simple additive with case-fold (used in some tutorials)**:
```c
DWORD hash = 0;
while (*name) {
    hash += toupper(*name);
    name++;
}
```

### 3.5 Recovery

Once you've identified the hash function (by reading the disassembly), generate the hash of every API name in every Windows DLL the malware might use. This is `GetProcAddress`'s target list — ~2000 functions across `kernel32`, `ntdll`, `user32`, `advapi32`, `ws2_32`, `crypt32`, etc.

Build a lookup table `hash -> api_name`. For every hash the malware compares against, you now know which API it's resolving. Re-insert these names into the binary (rename the resolved pointers at runtime in your debugger / dump).

Tools:
- `pefile` (Python) for enumerating exports
- `unicorn` for emulating the hash function against candidate names
- IDA Pro's `api_hash_database` (community plugin with ~50,000 precomputed hashes)

---

## 4. Pattern 3 — `LdrLoadDll` / `LdrGetProcedureAddress` for direct loader calls

Instead of `LoadLibraryA`/`GetProcAddress` (which go through `kernel32`), some malware calls `ntdll!LdrLoadDll` and `ntdll!LdrGetProcedureAddress` directly. These are the underlying NT API that the `kernel32` wrappers call.

### 4.1 Detection

- IAT shows `ntdll!LdrLoadDll` and `ntdll!LdrGetProcedureAddress` (or just `ntdll!RtlInitString` + the Ldr calls)
- The binary uses `UNICODE_STRING` structs (length, max length, buffer pointer — 3 fields) to pass arguments

### 4.2 Recovery

Strings are passed as `UNICODE_STRING` — the `Buffer` field is a `wchar_t*` to the API name. Inspect the binary for these struct allocations; the strings are plain UTF-16 and visible in the binary as wide-char arrays.

---

## 5. Pattern 4 — Direct syscalls (Hell's Gate, Halo's Gate, Tartarus' Gate)

The most stealthy approach: bypass `ntdll` entirely and issue `syscall` instructions directly. The malware computes syscall numbers dynamically (since they vary between Windows versions).

### 5.1 Hell's Gate

```c
// Find ntdll!NtCreateFile in memory
HMODULE ntdll = find_ntdll();
BYTE* pNtCreateFile = (BYTE*)GetProcAddress(ntdll, "NtCreateFile");
// Read the syscall number from the second byte
// NtCreateFile's first instructions are typically:
//   mov r10, rcx       ; 4C 8B D1
//   mov eax, <num>     ; B8 XX XX 00 00   <- syscall number is here
//   syscall            ; 0F 05
DWORD syscall_num = *(DWORD*)(pNtCreateFile + 4);

// Issue the syscall directly
__asm__ __volatile__(
    "mov r10, rcx\n"
    "mov eax, %1\n"
    "syscall\n"
    : "=a"(status)
    : "r"(syscall_num), "c"(SyscallArgs)
);
```

The syscall number is read at runtime by parsing `ntdll`'s export stubs. The stub format is always:
```
4C 8B D1          mov r10, rcx
B8 XX XX 00 00    mov eax, <syscall_num>
0F 05             syscall
C3                ret
```

### 5.2 Detection

- The byte pattern `4C 8B D1 B8 XX XX 00 00 0F 05` appears in the binary's `.text` section (the malware has its own syscall stub)
- The binary doesn't import any `ntdll!Nt*` functions
- The binary may scan `ntdll`'s `.text` section looking for `B8 XX XX 00 00` patterns to learn syscall numbers

### 5.3 Recovery

1. Find the malware's syscall stubs by pattern matching (`4C 8B D1 B8 ?? ?? 00 00 0F 05 C3`).
2. Read the syscall number from the `mov eax, XX XX 00 00` instruction.
3. Look up the syscall number in a per-Windows-version table:
   - Windows 10 1809: `NtCreateFile = 0x55`
   - Windows 10 1903: `NtCreateFile = 0x55` (same)
   - Windows 11 21H2: `NtCreateFile = 0x55`
   - Windows 11 22H2: `NtCreateFile = 0x55` (still)
   - But some syscalls shift by 1-2 between major versions

The syscall number stability is per-API. `NtCreateFile` has been `0x55` since Windows 7. `NtCreateThreadEx` has shifted several times.

### 5.4 Halo's Gate

If `ntdll` is hooked (EDR has modified its syscall stubs), the malware can't read the syscall number directly. Instead, it walks to the *next* unhooked syscall stub (usually `Nt`-numbered functions are sequential in memory) and uses that number ± a small delta to find the target syscall.

### 5.5 Tartarus' Gate

If the next stub is also hooked (all stubs are patched), the malware uses the previous unhooked stub's number and adds a delta. The number of patched stubs to skip is empirically determined.

### 5.6 SysWhispers / SysWhispers2 / SysWhispers3

These are open-source tools that generate C header files with the syscall stubs for a given Windows version. The generated code can be linked directly into malware, removing the need to dynamically find syscall numbers (at the cost of Windows-version lock-in).

Detection: the malware has a fixed syscall number hardcoded, which won't work on a different Windows version. The number itself is a fingerprint of which Windows version the malware was built for.

---

## 6. Pattern 5 — Indirect syscalls (modern)

The latest evolution: instead of `syscall` directly in `.text`, use `int 2eh` or `syscall` instruction placed in `ntdll` itself (jump to `ntdll!Nt*`'s syscall instruction). This evades EDRs that hook on `.text` syscall instructions.

Detection: the malware's `.text` doesn't contain `0F 05` (syscall) bytes directly; instead it has `call ntdll!Nt*` or `jmp ntdll!syscall` patterns.

---

## 7. The recovery workflow

When you encounter a binary that uses dynamic API resolution:

1. **Static analysis**: dump `.text` and `.rdata` to identify the pattern:
   - Pattern 1 (LoadLibrary by name): plain strings in `.rdata` — easy
   - Pattern 2 (PEB walk): signature bytes for `mov eax, fs:[30h]` or `mov rax, gs:[60h]` near entry
   - Pattern 3 (LdrLoadDll): IAT shows `LdrLoadDll` / `LdrGetProcedureAddress`
   - Pattern 4 (syscalls): `4C 8B D1 B8 ?? ?? 00 00 0F 05` pattern in `.text`
   - Pattern 5 (indirect syscalls): jump tables to `ntdll` syscall stubs

2. **Hash identification**: if hash-based, identify the hash function from the disasm:
   - Look for `ror`/`rol` instructions with constant shift → ROR-N hash
   - Look for `xor` + `imul` chains → FNV
   - Look for `crc32` intrinsic call → CRC32

3. **Hash inversion**: compute the hash function against every Windows API name (~5000 across all common DLLs). Build a `hash -> name` table.

4. **Match against the binary's hash table**: in `.rdata`, the malware stores a list of target hashes (often as `DWORD` array). Each hash in that array corresponds to one API. Look them up in your table.

5. **Reconstruct resolved API pointers**: identify where the malware stores the resolved addresses (typically a global array in `.data`). After runtime resolution, this array contains the function pointers. In a static dump, you won't see the resolved values — but you can rename the array slots based on the hash list (which is at a known order).

6. **If still uncertain**: emulate the resolution with Unicorn. Load `kernel32` and `ntdll` into the emulator's address space, walk the PEB following the malware's code, and capture the resolved addresses.

---

## 8. Reporting

For every binary using dynamic API resolution:

1. **Pattern identified** (LoadLibrary-by-name / PEB-walk-hash / Ldr-load / syscall / indirect-syscall)
2. **Hash function** (if hash-based): the algorithm, the constant, the rotation amount
3. **Hash lookup table**: list every hash the binary uses, and the API name it corresponds to
4. **Syscall numbers** (if syscall-based): the numbers, the Windows version they correspond to
5. **Limitations** — couldn't recover X because the hash function was custom, the syscall number isn't in published tables, etc.
6. **Recommended next step** — typically "feed recovered API names into IDA/Ghidra to rename resolved pointers" or "submit the binary to dynamic instrumentation to capture the runtime-resolved addresses"

Example finding:

```
SUSPECTED: PEB-walk + ROR-13 hash resolution.
Evidence:
- 0x401000: mov eax, fs:[30h]            ; PEB access
- 0x401005: mov eax, [eax+0Ch]            ; PEB->Ldr
- 0x401008: mov esi, [eax+14h]            ; InMemoryOrderModuleList
- 0x40100B: lodsd                          ; skip exe (1st entry)
- 0x40100C: lodsd                          ; skip ntdll (2nd)
- 0x40100D: mov ebx, [eax+10h]            ; kernel32 DllBase
- 0x401010: ... (export table parse)
- 0x401050: call hash_func                  ; hash the export name
- 0x401055: cmp eax, 0726774Ch             ; target hash for "LoadLibraryA"
- 0x40105A: jne next_export

Hash table in .rdata (8 entries):
- 0x4040: 0726774Ch   "LoadLibraryA"
- 0x4044: 077A6343h   "GetProcAddress"   (variant hash)
- 0x4048: 0930C0F0h   "CreateProcessA"
- 0x404C: 0E130DC6h   "VirtualAlloc"
- 0x4050: 0E04324Eh   "WriteProcessMemory"
- 0x4054: 0F4FDA4Bh   "CreateRemoteThread"
- 0x4058: 0930C0F0h   "CreateProcessA"  (duplicate)
- 0x405C: 0BAD0DA50h   "ExitProcess"

Hash function (verified by emulation):
- ROR-13 + add character. Standard Metasploit hash.

Recovered API set: 7 unique APIs across kernel32.
Behavioral inference: VirtualAlloc + WriteProcessMemory + CreateRemoteThread
indicates classic process injection. Recommend checking for the target
process name string in .rdata to identify the injection target.

To confirm: emulate the hash loop with Unicorn against a virtual
kernel32 export table; verify the resolved addresses match known
export RVAs.
```

---

## 9. Tools that automate this

- **API Hash DB** (community IDA plugin): database of ~50k precomputed hashes for common hash functions
- **HALOS HALL (research)**: detects and resolves Halo's Gate-style syscall stubs
- **Unicorn emulator**: load `ntdll`/`kernel32` from a real Windows install, walk the PEB, capture resolved addresses
- **Capstone disasm + pefile**: scriptable pipeline for batch analysis

The hard work is identifying the hash function. Once known, the inversion is mechanical.
