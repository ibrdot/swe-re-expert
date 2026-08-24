# Packers, Protectors & Unpacking — Recovery Playbook

How to detect, classify, and unpack the common commercial and open-source packers/protectors seen in malware, CTF challenges, and protected commercial software. The goal is always the same: **recover the original code and its imports/strings so static analysis becomes possible**. The packer is a wrapper; the payload is the target.

This playbook assumes the AI has access to `re_triage.py` and `re_disasm.py` plus `objdump`, `readelf`, `radare2`/`r2pipe`, `gdb`, and ideally `unipacker`/`x64dbg`-style dynamic unpackers. If only static tools are available, the playbook still applies for detection and partial recovery — flag the dynamic-only steps as `BLOCKED`.

---

## 1. The packer contract

Every packer implements the same four-step contract. Recognizing it is the first step to unpacking.

```
[Original PE/ELF] --compress/encrypt--> [Packed PE/ELF]
                                          |
                                          | contains:
                                          |  - packer stub (entry point)
                                          |  - encrypted/compressed payload
                                          |  - tiny import table (just the stub's needs)
                                          |  - sometimes: anti-analysis in stub
                                          v
                              [loader runs at startup]
                                          |
                                          v
                  1. ALLOC  : VirtualAlloc / mmap a writable+executable region
                  2. DECODE : decrypt/decompress payload into the new region
                  3. FIXUP : resolve imports, patch relocations, fix IAT
                  4. JUMP   : transfer control to OEP (Original Entry Point)
                                          |
                                          v
                              [Original program runs from OEP]
```

When you see a binary where:
- the only entry-point section is small and contains `VirtualAlloc` + `WriteProcessMemory`-style loops,
- entropy is >7.5 in the largest section,
- imports are minimal (`kernel32!VirtualAlloc`, `kernel32!LoadLibraryA`, `kernel32!GetProcAddress`), and
- strings look meaningless or are absent,

…you are looking at a packer. The actual binary you care about is encrypted inside the payload section.

---

## 2. Detection signatures — fast triage

The triage script (`re_triage.py`) reports the entropy profile and suspicious section names. Cross-reference those signals with the table below to classify.

### 2.1 Section-name fingerprints

| Packer / Protector | Section names typically present | Other signatures |
|---|---|---|
| UPX | `.UPX0`, `.UPX1`, `.UPX2` (sometimes `.upx0` lowercase) | `UPX!` magic at file offset 0 `0x20` of `.UPX1` ; entry point in `.UPX1` ; tiny imports (`kernel32` only) |
| Themida / WinLicense | `.themida`, `.winlice`, `.taggant`, `. CBD` | `Themida` family string in `.rdata` ; heavy anti-debug stub ; often runs `IsDebuggerPresent`, `NtQueryInformationProcess` early |
| VMProtect | `.vmp0`, `.vmp1`, `.vmp2` | Imports resolved via `LoadLibrary`/`GetProcAddress` inside `.vmp0` ; MD5 of stub on disk is a known VMP hash |
| MPRESS | `.MPRESS1`, `.MPRESS2` | `MPRESS1` is the packer code; `MPRESS2` is compressed data ; uses LZMAT compression |
| Enigma Protector | `.enigma1`, `.enigma2`, `.enigma3` | Imports resolved at runtime via `LoadLibraryA`; manifest references `Enigma` namespace |
| ASPack | `.aspack`, `.adata` | `ASPack` string in `.rdata` ; simple unzip + import fixup |
| Petite | `.petite` | Older packer; runs from one section ; pure decompression |
| FSG | `.fsg` | very small stub, often 1-2 KB ; only used in old malware |
| MEW | `.mew` | old, uses `e-type` relocation ; mostly historical |
| PELock | `.pelock` | Import protection via CRC checks |
| PESpin | `.pspin` | Section name reuse ; has anti-VM stub |
| Obsidium | `.obsidium` | strings inside `.obsidium` ; uses RC4 to decrypt inner code |
| PELock, Byteboot, Crunch | family-specific names | varies |
| PyInstaller (Python) | `MEI` marker, `_MEIPASS` strings, `pyiboot` | bundled Python interpreter + bytecode in `.pyz` archive |
| PyArmor | `_pyimod` strings, `pyarmor` string | Python bytecode obfuscation, runs `pytransform.dll` |
| Nuitka | `__pyinstaller` strings absent, has `__file__`-shaped constants | Python compiled to C then to native |
| GoGarble / garble | Go binary with shuffled symbols, `go:build` strings intact but paths mutated | `garble` is the official Go obfuscator |
| ConfuserEx (.NET) | `.text`, `.rsrc`, `.reloc` normal but `.text` is heavy | has `ConfuserEx` metadata in `.text` |
| .NET Reactor | `.text` has Reactor stub | `Eziriz` strings, obfuscation attributes |

The presence of one of these section name patterns is **not** proof of packer — commercial binaries legitimately have named sections. Treat it as a **strong HYPOTHESIS**, then verify by:
- entropy check on that section (packer payloads are always high-entropy)
- import count (packer stubs have ≤10-20 imports)
- string count in that section (payloads are near-zero plaintext strings)

### 2.2 Entropy profile

Run `python scripts/re_triage.py --file <target> --all` and read the `sections` array. A packer payload section has entropy in the range `7.5–8.0` (compressed data) or `7.8–8.0` (encrypted data). Code sections in a normal binary sit at `6.0–6.7` (instructions, jump tables, occasional padding). Data sections sit at `4.0–7.0` depending on string density. **A section >7.5 in size >50KB is almost always packer or encrypted.**

If the **lowest-entropy code section is the entry-point section** but it's tiny (`<10KB`) and entropy `>7.0`, that is a packer stub. The real code lives in another section that has entropy `>7.5`.

### 2.3 Import table shape

A packed binary typically imports only the bare minimum to perform runtime decompression + import resolution:

```python
# Common packed-binary imports (Windows)
KERNEL32!LoadLibraryA       # required: load DLLs at runtime
KERNEL32!GetProcAddress     # required: resolve API by name
KERNEL32!VirtualAlloc       # required: allocate the decoded payload region
KERNEL32!WriteProcessMemory # sometimes; older packers, or self-modifying code
KERNEL32!GetTickCount       # anti-debug via timing
KERNEL32!IsDebuggerPresent  # anti-debug
NTDLL!NtQueryInformationProcess  # anti-debug (CheckRemoteDebuggerPresent)
```

If a Windows binary has fewer than 15 imports and you see this exact cluster, you are looking at a packer stub. A normal Windows utility has 50-300 imports.

On Linux, an ELF packer (UPX, Burneye, ELFCophine) is rarer but follows the same pattern: tiny `.dynsym`, just `mmap` / `mprotect` / `__libc_start_main`.

### 2.4 Compiler hints that often co-occur with packing

- PE: rich header absent or stripped (`re_triage.py` reports `rich_header: null` for a non-VS binary or a stripped one — for an unpacked VS build it should be present)
- PE: `TimeDateStamp` of the file header is wildly off from the linker version
- PE: only 1-2 sections instead of the typical `.text/.rdata/.data/.rsrc/.reloc`
- ELF: `.comment` section stripped or generic
- ELF: only `__libc_start_main` + `mmap` in dynamic symbols

---

## 3. UPX — the canonical case

UPX is the most common packer in the wild because it is open-source, fast, and freely available. Malware authors use it to defeat signature detection; legitimate software vendors use it to reduce binary size. The recovery is straightforward.

### 3.1 Static detection

```
$ python scripts/re_triage.py --file target.exe --all
{
  "sections": [
    {"name": "UPX0",   "size": 69632, "entropy": 0.000},  # empty placeholder
    {"name": "UPX1",   "size": 33280, "entropy": 7.92},   # packed code+data
    {"name": ".rdata", "size": 512,   "entropy": 3.21}    # tiny IAT holder
  ],
  "imports": ["kernel32!LoadLibraryA", "kernel32!GetProcAddress", "kernel32!VirtualAlloc"],
  "entry_section": "UPX1",
  "strings_count": 3
}
```

The classic UPX signature:
- 3 sections named `UPX0/UPX1/.rdata` (or `.UPX0/.UPX1/.UPX2` capitalized)
- `UPX1` has the magic `UPX!` at offset 0 of its content
- `UPX0` is the placeholder section where the unpacked code will land (SFB — Size of First Block is 0 in the section header, but `VirtualSize` is large)

### 3.2 The static unpack (always try first)

UPX ships with its own unpacker. If `upx` is installed:

```bash
upx -d target.exe -o target_unpacked.exe
#       -d = decompress
#       -o = output path
```

This is the cleanest unpack. Result: `target_unpacked.exe` with the original imports, sections, and entry point restored. Often yields the original `TimeDateStamp` too. **Try this before any dynamic unpacking.**

If `upx -d` fails with "NotPackededException" or "CRC error", the packer has been modified (mutated UPX, header anti-tamper). Fall through to dynamic unpacking.

### 3.3 UPX header modification (when `-d` fails)

Malware authors modify UPX to break `upx -d`. Common mutations:

1. **Magic byte change**: `UPX!` → `UPX.` or `XXX!` at the section start
2. **Section name change**: `UPX0` → `UPX.` or `random`
3. **Version field tampering**: change `UPX_MAGIC_LE32` from `0x21585055` to something else
4. **LZMA marker stripping**: removes the `UPX_LZMA` header, breaking `upx -d`

Fix each mutation by hex-editing the file back to canonical UPX:

```bash
# Find the mutated magic
xxd target.exe | grep -i "upx"   # check current state
# Patch back to canonical using dd or a Python script
python3 - <<'PY'
import struct
with open('target.exe','rb') as f: d = bytearray(f.read())
# Fix magic
i = d.find(b'UPX.')
if i>=0: d[i:i+4] = b'UPX!'
# Fix section names
d = d.replace(b'.UPX0', b'UPX0').replace(b'.UPX1', b'UPX1')
with open('target_fixed.exe','wb') as f: f.write(d)
PY
upx -d target_fixed.exe -o target_unpacked.exe
```

If mutation is at the LZMA layer or the unpacker still rejects the file, **abandon static unpack** and go dynamic.

### 3.4 Dynamic UPX unpack (manual)

When `upx -d` won't work:

1. Load in `x64dbg` (Windows) or `gdb` (Linux with UPX-GDB)
2. Set a hardware breakpoint on `VirtualAlloc` (Windows) or `mprotect` (Linux)
3. Run; the packer will allocate a region for the decoded payload
4. After the allocation returns, set a **memory access breakpoint** on the allocated region (write access)
5. Continue; the packer writes decoded bytes to that region
6. Once writes stop, set an **execution breakpoint** on the start of the allocated region
7. Continue; when execution hits that address — that is the **OEP** (Original Entry Point)
8. Dump the memory region with Scylla (Windows) / `gcore` (Linux)
9. Reconstruct the IAT using Scylla's IAT autodetect → "Get Imports" → "Fix Dump"

The result is a runnable unpacked PE. If IAT reconstruction fails, the unpacked dump will still disassemble correctly — you just won't see resolved imports.

---

## 4. Themida / WinLicense

Themida is a commercial protector with anti-VM, anti-debug, and code virtualization. **Full unpacking of virtualized functions is not feasible statically** — you can recover the unvirtualized portion and the imports, but virtualized functions are interpreted by a VM dispatcher and require either Devirtualize-style tooling or VM tracing.

### 4.1 Detection

- Section name `.themida` or `.winlice`
- Entry point in `.themida`
- Massive `.themida` section (>1MB typical)
- Imports heavily obfuscated, resolved at runtime
- Anti-debug: `NtQueryInformationProcess(ProcessDebugPort)` / `ProcessDebugFlags` / `ProcessDebugObjectHandle` checks
- Anti-VM: `cpuid` instruction checks for `VMware`/`VirtualBox` vendor strings; `in` instruction on `0x5658` (VBox) or `0x568` (VMware backdoor)
- Anti-timing: `rdtsc` deltas exceeding thresholds

### 4.2 Partial unpacking (non-virtualized code)

1. Attach `x64dbg` to the running process (do not load statically — Themida detects debuggers at load)
2. Wait for the OEP to be reached. The OEP marker is a `call` to a near address in the original `.text` section (look for the byte pattern `E8 ?? ?? ?? ??` followed by well-formed prologues `55 8B EC` or `48 89 5C 24`)
3. Use **Scylla** plug-in to dump the process and reconstruct the IAT
4. The dump will contain all original unvirtualized code + correct imports
5. Virtualized functions remain as calls into the Themida VM dispatcher; they cannot be recovered without VM tracing

If the binary was protected with **VM mode** (visible via `.themida` section size >1.5MB and presence of `VMProtect`-style bytecode handlers — look for a long `jmp` to a `dispatch` block followed by `movzx` + `jmp [table + register*4]`), mark those functions as `BLOCKED` — VM recovery is a manual, multi-week effort per binary.

### 4.3 What you can still report

Even without full unpacking, you can extract from a Themida binary:
- **Strings** in non-encrypted sections (often `.rdata` retains the original strings)
- **Import resolution patterns** (which DLLs and APIs it ultimately needs)
- **Mutex names** if present in non-encrypted sections (these are often the family signature)
- **C2 URLs** if the binary stores them decrypted at runtime — capture via memory scanning post-OEP

---

## 5. VMProtect

VMProtect virtualizes selected functions into a custom bytecode interpreter. Non-virtualized code is plain x86/x64. The recovery depends on whether you can identify which functions were virtualized.

### 5.1 Detection

- Section names `.vmp0`, `.vmp1`, `.vmp2`
- The `.vmp0` section contains the VM dispatcher
- `.vmp1` is the encrypted payload
- Imports resolved via `LoadLibrary`/`GetProcAddress` at runtime — the IAT in the file is mostly `kernel32` only
- Some functions in `.text` are intact x86; some are replaced with `push <imm>; call vm_entry` patterns

### 5.2 Non-virtualized function recovery

1. Load in `x64dbg`
2. Find the OEP by setting a **memory access breakpoint** on `.text` and waiting for the packer to transfer control there
3. Use Scylla to dump
4. The dump will contain:
   - All non-virtualized functions intact (runnable x86 code)
   - Virtualized functions replaced with `push <stub_id>; call vm_entry`
   - IAT partially reconstructed (VMProtect resolves imports at OEP)
5. Mark virtualized functions as `BLOCKED` — VMProtect VM tracing requires devirtualization research frameworks like `vmprotect-devirtualization` (research prototypes, not production-ready)

### 5.3 The `.vmp0` stub id pattern

When the binary calls a virtualized function, the call site looks like:

```
push 0x00001234          ; stub id
call vm_entry            ; .vmp0 entry
```

You can identify which functions were virtualized by scanning for this pattern (`68 ?? ?? ?? ?? E8 ?? ?? ?? ??`). Each `stub_id` corresponds to a virtualized function. Recovering the function requires decoding the VM bytecode using the dispatcher's opcode table — non-trivial but doable for small functions.

---

## 6. MPRESS

MPRESS uses LZMAT compression and is reasonably easy to unpack because the protection layer is thin.

### 6.1 Detection

- `.MPRESS1` section: packer code (low entropy, ~6.0)
- `.MPRESS2` section: compressed payload (entropy ~7.8)
- Entry point in `.MPRESS1`

### 6.2 Unpacking

1. Static unpack: `upx -d` won't work, but `MPRESS` ships an unpacker? No, MPRESS has no public unpacker.
2. Dynamic unpack with `x64dbg`:
   - Hardware breakpoint on `VirtualAlloc`
   - When it returns, set a write-access breakpoint on the allocated region
   - When writes stop, set an execution breakpoint
   - When execution hits, that's OEP
   - Scylla dump + IAT autodetect → fix dump

MPRESS doesn't virtualize, so the unpacked dump is full fidelity.

---

## 7. Enigma Protector

### 7.1 Detection

- `.enigma1`, `.enigma2`, `.enigma3` sections
- Heavy anti-debug: `NtSetInformationThread(ThreadHideFromDebugger)`, `SetUnhandledExceptionFilter` used as a debugger trap
- Sometimes uses hardware breakpoints as anti-debug (checks `DR0-DR7` registers for non-zero values)
- Often bundles licensing logic — the binary may refuse to run without proper license

### 7.2 Unpacking

Similar to Themida: attach after OEP, dump with Scylla, reconstruct IAT. License checks may need patching (`je → jmp` or `cmp eax,1 → xor eax,eax` after the license check call).

---

## 8. .NET packers (ConfuserEx, .NET Reactor, Eazfuscator)

### 8.1 Detection

- Normal PE structure but `.text` section is unusually large and high-entropy
- `#Strings` heap in the metadata is mangled or string-encrypted
- `ConfuserEx`: specific patterns in `.text` like `ConfuserEx` namespace markers
- `.NET Reactor`: `Eziriz` strings, obfuscation attributes
- Eazfuscator: lazy string decryption at first use

### 8.2 De-obfuscation

Use **de4dot** (open-source .NET deobfuscator) — it auto-detects and unpacks ConfuserEx, .NET Reactor, Eazfuscator, Babel, and a dozen other .NET obfuscators:

```bash
de4dot target.exe -o target_clean.exe
```

The output is a clean .NET assembly that `dnSpy`/`ILSpy` can decompile to readable C#.

If `de4dot` doesn't recognize the obfuscator, fall back to:
1. Load in `dnSpy` (debugger)
2. Set breakpoints on string-decryption methods (look for methods called early in execution)
3. Run; capture decrypted strings from memory
4. Patch the binary to bypass license checks (often a single `ret` from the license check method)

---

## 9. Python packers (PyInstaller, PyArmor, Nuitka)

### 9.1 PyInstaller

**Detection**: `MEI` marker, `_MEIPASS` string, `pyiboot01` string in the binary.

**Unpack**:
```bash
pip install pyinstxtractor
pyinstxtractor target.exe     # produces target.exe_extracted/
# Inside the extracted dir:
#   - .pyc files for each compiled module
#   - PYZ-00.pyz_extracted/ — Python bytecode archives
#   - pyiboot01.pyc — boot logic
# Then decompile the .pyc files:
pip install decompyle3        # or uncompyle6 for older Python
decompyle3 some_module.pyc
```

### 9.2 PyArmor

PyArmor encrypts Python bytecode and uses `pytransform.dll`/`.so` to decrypt at runtime.

**Recovery**:
1. Run the binary under `gdb`/`windbg`
2. Find the moment when the decrypted bytecode is passed to the Python interpreter (the call to `PyMarshal_ReadObjectFromString` or `PyEval_EvalCode`)
3. Dump the decrypted bytecode from the buffer
4. Decompile with `decompyle3`/`uncompyle6`

This is moderate-effort. If you can run the binary, you can also patch `pytransform` to log every decrypted bytecode to disk.

### 9.3 Nuitka

Nuitka compiles Python to C then to native machine code. The result is **not reversible to Python source** — there is no bytecode to recover. You can still RE the binary like any C binary; the function names often retain their Python origin (e.g., `module_function_impl`) which helps with semantic recovery.

---

## 10. Go binary obfuscation (garble)

`garble` is the official Go obfuscator. It:
- Hashes package paths (`github.com/user/project` → `yKW4vA`)
- Hashes function names
- Encrypts string literals (decoded lazily at runtime)
- Strips `go:build` info and debug symbols

**Detection**: `garble` string in build info, missing `go:build` info, symbols look like base64-encoded hashes (e.g., `yKW4vA.xyz`).

**Recovery**:
- Run `go tool buildid <binary>` to extract any remaining build id
- Strings are decrypted lazily: use `gdb` to set a breakpoint on `runtime.concatstrings` or `runtime.stringconcat` and dump decrypted strings
- For function names: there is no recovery without the original source. Use behavior to name functions.

---

## 11. Anti-debug + anti-VM patterns commonly bundled with packers

Many packers add anti-debug / anti-VM on top of packing. Recognize the patterns to know what to bypass:

| Technique | Instruction / API pattern | Bypass |
|---|---|---|
| `IsDebuggerPresent` | `call KERNEL32!IsDebuggerPresent` near entry | Patch return value: `mov eax, 0; ret` at the call site |
| `CheckRemoteDebuggerPresent` | `push handle; push &out; call kernel32!CheckRemoteDebuggerPresent` | Same — patch return |
| `NtQueryInformationProcess(ProcessDebugPort)` | `push 7 (DebugPort); push handle; ... call ntdll!NtQueryInformationProcess` | Patch the out pointer to 0 after the call |
| `NtQueryInformationProcess(ProcessDebugFlags)` | `push 0x1F (DebugFlags); ...` | Same |
| `NtQueryInformationProcess(ProcessDebugObjectHandle)` | `push 0x1E; ...` | Same |
| `PEB.BeingDebugged` direct read | `mov eax, fs:[0x30]` (TEB->PEB), then `movzx ecx, byte ptr [eax+2]` | Patch the byte at PEB+2 to 0 |
| `PEB.NtGlobalFlag` check | `mov eax, fs:[0x30]`, `[eax+0x68]` | Patch to 0 (or 0x70 for normal) |
| `NtSetInformationThread(ThreadHideFromDebugger)` | `push 0x11; push 0; push -2; call ntdll!NtSetInformationThread` | NOP the call |
| `rdtsc`-based timing | two `rdtsc` separated by a few instructions, then a `sub` + `cmp` against a threshold | NOP the comparison |
| `cpuid` vendor check (VMware) | `mov eax, 0x40000000; cpuid; cmp [ebx], 'VMXh'` | Patch `cpuid` to return host vendor |
| `in al, 0x5658` (VBox) | `mov eax, 'VBox'; in al, 0x5658; cmp ebx, 'VBox'` | NOP the `in` instruction |
| `int 2d` (kernel-mode debugger) | `int 0x2d` | NOP |
| `int 3` self-checks | comparison of `__debugbreak()` semantics | NOP the comparison |
| Hardware breakpoint DR check | `mov eax, dr0; test eax, eax; jne detected` | Patch the `test` or `jne` |
| `SetUnhandledExceptionFilter` abuse | registers a handler that re-enters on first exception (PIF) | NOP the registration or skip the raise |

When you see one of these in a packer stub, you know what to patch. Always patch the **check** site, not the API call — patching the API call changes global state and may break the legitimate code path.

---

## 12. After unpacking — re-run the triage

Once you have the unpacked binary, **re-run `re_triage.py` on it**. The unpacked binary should show:

- Normal entropy (code sections ~6.0-6.7, data ~4.0-7.0)
- Full import table (50+ imports for typical Windows app)
- Strings count goes from single digits to thousands
- Section names normalize to `.text`, `.rdata`, `.data`, `.rsrc`, `.reloc`
- Compiler hints become accurate (rich header restored for UPX-unpacked VS binaries)

If any of these is still off, the unpacker didn't fully resolve imports (IAT reconstruction failed) or the binary was partially re-packed. Run the unpacked binary through `re_disasm.py` for the function-level view.

---

## 13. Reporting

When the AI runs into a packer, the report should include:

1. **Packer identification** (HYPOTHESIS/SUSPECTED, with the signatures that point to it)
2. **Unpacking attempt** (static unpack result; if dynamic was needed, BLOCKED if no VM available)
3. **Post-unpack binary metadata** (the re-run triage JSON)
4. **Limitations** — what's still virtualized, what imports weren't recovered, whether the unpacked dump runs
5. **Recommended next step** — either run the unpacked binary through deep RE, or escalate to dynamic VM unpacking

The deliverable is **not** "I detected Themida". It's "I detected Themida, partially unpacked (recovered 73% of original imports, 0% of virtualized functions), identified family markers via unencrypted strings, and recommend dynamic unpacking in an instrumented VM to recover the remaining 27%".

---

## 14. The unpacking decision tree

```
DETECTED PACKER?
├── UPX-style (UPX0/UPX1, MPRESS1/MPRESS2, ASPack)
│   ├── Try static unpacker first (upx -d / MPRESS native / ASPack native)
│   └── If mutated → hex-edit fix → retry; if still fails → dynamic unpack
│
├── Themida / VMProtect (with VM)
│   ├── Attach post-OEP, dump with Scylla
│   ├── IAT autodetect
│   ├── Recover non-virtualized functions
│   └── Mark virtualized functions as BLOCKED
│
├── .NET (ConfuserEx / Reactor / Eazfuscator)
│   └── de4dot — auto-recovery in seconds
│
├── Python (PyInstaller / PyArmor / Nuitka)
│   ├── PyInstaller → pyinstxtractor + decompyle3
│   ├── PyArmor → dynamic capture of decrypted bytecode
│   └── Nuitka → treat as native C binary (no bytecode recovery)
│
└── Unknown / custom packer
    ├── Dynamic unpack via x64dbg + Scylla
    ├── If VM-protected → BLOCKED, report family markers from strings
    └── If runtime stub has clear decode loop → emulate with Unicorn
```

---

## 15. Output

For every packed binary the AI encounters:

- Packer identified (`SUSPECTED` if based on entropy + section names alone; `CONFIRMED` if magic bytes match)
- Unpacking attempt documented (`SUCCESS` / `PARTIAL` / `BLOCKED` with reason)
- Re-triage JSON on the unpacked dump included in the report
- Limitations explicit (which virtualized functions remain blocked, which imports weren't recovered)
- Recommended next step concrete (e.g., "submit unpacked dump to deep RE playbook for function-level analysis", "submit to dynamic VM for behavioral capture")
