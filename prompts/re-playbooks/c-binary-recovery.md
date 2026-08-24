# C Binary Recovery — How to Reverse a Stripped C Binary

C binaries are the bread and butter of RE. Even stripped, they expose enough structure to recover most of the original logic in a few hours.

## The 7-step recovery loop

1. **Triage** — `python scripts/re_triage.py --file <target> --all`. Get type, arch, security features, sections, imports.
2. **Entry backtrack** — find `_start`, find `main`. `_start` is the libc entry; `main` is passed as arg to `__libc_start_main`.
3. **Function discovery** — list functions from symbol table (if not stripped) or prologue scan (if stripped).
4. **Cross-reference map** — for each suspicious import, find callers. This is your behavior anchor.
5. **Function-by-function semantic recovery** — disasm, annotate, write pseudocode.
6. **Data structure recovery** — match offsets to struct fields, build types in Ghidra/IDA.
7. **Synthesis** — combine all functions into a behavioral summary.

## Finding main() in a stripped ELF

`_start` (the libc entry) does:
```
xor    ebp, ebp
pop    rsi                    ; argc
mov    rdx, rsp               ; argv
and    rsp, -16               ; align stack
call   __libc_start_main@plt ; passes main, init, fini
hlt
```

The arg to `__libc_start_main` (in `rdi` for System V AMD64) is the address of `main`. Disassemble `_start` and find the `lea rdi, [rip+offset]` or `mov rdi, immediate` before the libc call.

In Ghidra, this is automatic — it labels `main` for you. From `objdump` alone:

```bash
objdump -d -M intel <target> | sed -n '/<_start>:/,/^$/p' | head -20
```

Look for the `mov rdi, 0xNNNNNNN` or `lea rdi, [rip+0xNNN]` — that's `main`.

### Finding main() in stripped PE (Windows)

PE binaries don't use `__libc_start_main`. They use `WinMain` or `main` directly, called from the CRT initialization. The entry point in the PE header is typically `mainCRTStartup` or `WinMainCRTStartup`, which does some setup and then calls `main`/`WinMain`.

```bash
# Get PE entry point
python -c "
import pefile
pe = pefile.PE('sample.exe')
print(f'Entry point RVA: {hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)}')
print(f'Image base: {hex(pe.OPTIONAL_HEADER.ImageBase)}')
"

# Disasm from entry, look for the call to main
objdump -d -M intel --start-address=0xXXXX --stop-address=0xYYYY sample.exe | head -50
```

The CRT startup typically:
1. Initializes the FPU (`fninit`)
2. Sets up security cookies (`__security_init_cookie`)
3. Initializes CRT (`_initterm`)
4. Calls `main` or `WinMain`
5. Calls `exit` with the return value

The 4th call is to `main`/`WinMain`. Find it and you've found the entry.

## Function discovery when stripped

If the symbol table is gone, recover functions by:

### Method 1: PLT scan

Each PLT entry has a corresponding target. `objdump -d` shows `call func@plt`. Collect all `call <addr>` targets — those are function starts.

```bash
# Extract all call targets from disasm
objdump -d <target> | grep "call.*@" | awk '{print $NF}' | sort -u
# Or for calls to local addresses:
objdump -d <target> | grep "^\s*[0-9a-f]*:.*call\s" | awk '{print $NF}' | sort -u
```

### Method 2: Prologue scan

Common x86-64 prologues (GCC -O2, no frame pointer):
- `48 83 ec NN` (sub rsp, N)
- `48 89 5c 24 NN` (mov [rsp+N], rbx) — MSVC style
- `55 48 89 e5` (push rbp; mov rbp, rsp) — older GCC with frame pointer
- `40 53` (push rbx) — leaf with rbx saved
- `f3 0f 1e fa` (endbr64) — modern GCC, marks valid indirect branch targets
- `48 83 ec NN 48 8b NN` (sub rsp + mov to stack slot) — common MSVC

Scan for these byte patterns. Each hit is a candidate function start.

```python
import re
# endbr64 prologue pattern
pattern = b'\xf3\x0f\x1e\xfa'
# Find all occurrences
with open('binary', 'rb') as f:
    data = f.read()
offsets = [m.start() for m in re.finditer(re.escape(pattern), data)]
print(f"Found {len(offsets)} endbr64 markers")
```

### Method 3: Reference scan

For each `call` instruction in the disassembly, the target is a function. Build the set of call targets — those are all function starts.

```bash
# Extract direct call targets (relative addresses)
objdump -d <target> | grep -oP 'call\s+\K0x[0-9a-f]+' | sort -u | head -50
```

### Method 4: Return scan

Each function ends with `ret` (or `jmp` for tail call). Each `ret` is a function end. The next byte after `ret` (often padding `cc` or `90`) is the next function start.

### Method 5: Section boundary scan

Functions don't span section boundaries. The `.text` section's start and end addresses bound all functions. Within `.text`, scan for prologues.

## Recovering function semantics — the basic-block loop

For each function:

1. Identify the prologue (save frame, reserve locals, save callee-saved registers)
2. Identify the epilogue (restore frame, return)
3. Walk basic blocks (linearly until a branch; each branch target starts a new block)
4. For each block:
   - Identify the ABI role of each register (rdi = arg1, rsi = arg2, ...)
   - Trace local variable reads/writes (`mov [rbp-N], rax`)
   - Identify calls and what args are being prepared
   - Identify comparisons / conditional jumps (these are `if` / loop / switch edges)
5. Build the control flow graph (CFG)
6. Write pseudocode from the CFG

### Identifying loop structure

A loop has a back-edge: a jump from a later address to an earlier one. Identify back-edges first:
```bash
objdump -d <target> | grep "jmp.*0x[0-9a-f]" | awk '{print $NF}' | sort -u
```

A jump target less than the current instruction's address is a back-edge — that's a loop. The loop body is between the target and the back-edge.

### Identifying switch statements

Switch with N+1 cases compiles to a jump table:
```asm
mov    eax, [rbp-N]          ; switch variable
cmp    eax, K                ; max case value
ja     .default              ; out of range
lea    rdx, [rip + .table]   ; jump table base
mov    rax, [rdx + rax*8]    ; load target
jmp    rax                   ; jump
```

Find the `lea rdx, [rip + .table]` and dump the table to recover all case targets.

```bash
# Dump the jump table (each entry is 4 or 8 bytes)
objdump -s -j .rodata <target> | head -X
# Or use Python:
python -c "
import struct
with open('target', 'rb') as f:
    f.seek(table_offset)
    for _ in range(N+1):
        print(hex(struct.unpack('<I', f.read(4))[0]))
"
```

## Common pattern → source mapping

| Disasm pattern | Likely source |
|----------------|-----------------|
| `cmp [rbp-N], K; jl/jg/jne L` | `if (var OP K)` |
| `mov eax, 0; test rax, rax; jne L` | `if (var)` or `if (func())` |
| `lea rdi, [rip+str]; call printf@plt` | `printf("...")` |
| `mov rdi, [rbp-N]; call free@plt` | `free(var)` |
| `mov rdi, [rbp-N]; call strlen@plt; cmp rax, K` | `if (strlen(var) > K)` |
| `mov rdi, [rbp-N]; mov rsi, [rbp-M]; call strcmp@plt; test eax, eax; jne L` | `if (strcmp(a, b) != 0)` |
| `lea rdi, [rbp-N]; call gets@plt` | `gets(buf)` — buffer overflow risk |
| `mov rdi, [rbp-N]; call malloc@plt; mov [rbp-M], rax` | `var = malloc(size)` |
| `cmp rax, K; ja default; jmp [rax*8 + table]` | switch with K+1 cases |
| `xor eax, eax; rep stosb` | memset(buf, 0, N) |
| `rep movsq` / `rep movsb` | memcpy(dst, src, N) |
| `lea rdi, [rip+str]; call puts@plt` | `puts("...")` or `printf("...\n")` |
| `mov rdi, [rbp-N]; call pthread_create@plt` | `pthread_create(...)` — thread spawn |
| `call fork@plt` | `fork()` |
| `call execve@plt` | `execve(...)` — process replace |
| `mov rdi, [rbp-N]; call socket@plt` | `socket(...)` — network socket |
| `call connect@plt; mov rdi, [rbp-N]` | `connect(fd, addr, len)` |
| `call send@plt` / `call recv@plt` | network send/recv |
| `call mmap@plt` with `PROT_READ\|PROT_WRITE` | allocate RW memory |
| `call mmap@plt` with `PROT_EXEC` | allocate RWX memory — investigate |
| `call mprotect@plt` with `PROT_EXEC` | make writable memory executable — investigate |
| `call ptrace@plt` with `PTRACE_TRACEME` | anti-debug |
| `rdtsc; sub rax, [rbp-N]; cmp rax, K; jl L` | timing check anti-debug |

## Calling convention cheat sheet

### System V AMD64 (Linux, macOS pre-12)
- Int args: rdi, rsi, rdx, rcx, r8, r9 (then stack)
- Float args: xmm0–xmm7
- Return: rax (or rdx:rax for 128-bit)
- Callee-saved: rbx, rbp, r12, r13, r14, r15
- Caller-saved: rax, rcx, rdx, rsi, rdi, r8–r11, xmm0–xmm15
- Stack: 16-byte aligned at call site

### Microsoft x64 (Windows)
- Int args: rcx, rdx, r8, r9 (then stack)
- Float args: xmm0–xmm3
- Return: rax
- Callee-saved: rbx, rbp, rdi, rsi, r12–r15
- Caller-saved: rax, rcx, rdx, r8–r11, xmm0–xmm5
- Shadow space: 32 bytes reserved on stack for callee to spill args
- Stack: 16-byte aligned at call site

### ARM64 (AArch64)
- Int args: x0–x7
- Float args: v0–v7
- Return: x0
- Callee-saved: x19–x28, x29 (FP), x30 (LR)
- Caller-saved: x0–x18, v0–v31
- Frame pointer: x29
- Return address: x30 (LR); `ret` uses it implicitly

### ARM32 (AAPCS)
- Int args: r0–r3 (then stack)
- Float args: depends on ABI (soft or hard float)
- Return: r0 (or r0:r1 for 64-bit)
- Callee-saved: r4–r11, r13 (SP), r14 (LR)
- Frame pointer: r11 (or r7 in thumb mode)

## Crypto constant detection

When you see these byte sequences in `.rodata` or stack, the binary uses the corresponding algorithm:

| Algorithm | First bytes | Hex |
|-----------|-------------|-----|
| AES S-box | 16 bytes | `63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76` |
| AES inverse S-box | 16 bytes | `52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb` |
| AES round constants | 10 bytes | `01 02 04 08 10 20 40 80 1b 36` |
| SHA-256 K[0..3] | First round constants | `42 8a 2f 98 71 37 44 91 b5 c0 fb cf e9 b5 db a5` |
| SHA-256 H0 | Initial hash values | `6a 09 e6 67 bb 67 ae 85 3c 6e f3 72 a5 4f f5 3a` |
| SHA-1 H0 | Initial hash values | `67 45 23 01 ef cd ab 89 98 ba dc fe 10 32 54 76` |
| SHA-1 K[0..3] | Round constants | `5a 82 79 99 6e d9 eb a1 8f 1b bc dc ca 62 c1 d6` |
| MD5 T[0..3] | Sine table first entries | `d7 6a a4 78 e8 c7 b7 56 24 20 70 db c1 c0 e6 e0` |
| MD5 IV | Initial values | `01 23 45 67 89 ab cd ef fe dc ba 98 76 54 32 10` |
| CRC32 table | First 4 entries | `00 00 00 00 96 30 07 77 2c 61 0e ee ba 51 09 99` |
| CRC16-CCITT table | First entries | `00 00 21 10 42 20 63 30 84 40 a5 50 c6 60 e7 70` |
| RC4 identity table | 256 sequential bytes | `00 01 02 03 04 05 06 07 08 09 0a 0b ... ff` |
| DES S-box 1 | First S-box | `0e 04 0d 01 02 0f 0b 08 03 0a 06 0c 05 09 00 07` |
| ChaCha20 constants | "expand 32-byte k" | `65 78 70 61 6e 64 20 33 32 2d 62 79 74 65 20 6b` |
| Blowfish S-box 0 | First entries | `d1 31 0a 02 45 55 17 07 82 a5 40 07 a8 34 52 13` |
| Curve25519 prime | 2^255-19 | `ed ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff` (little-endian) |
| secp256k1 prime | Bitcoin curve p | `ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff` ... |
| Goldilocks (Curve448) | 2^448-2^224-1 | `ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff fe` ... |

Cross-reference the constant to find the function that uses it — that's the crypto implementation. See `re-playbooks/crypto-identification.md` for the full fingerprint catalog and source-code-level detection patterns.

## Common bug patterns to flag

| Pattern | Why it matters |
|---------|----------------|
| `gets@plt` import + use | Always buffer overflow; P0 |
| `strcpy@plt` with user input source | Buffer overflow; P0 |
| `sprintf@plt` with user input format | Buffer overflow + format string; P0 |
| `printf@plt` with user input as format | Format string attack; P0 |
| `memcpy@plt` with size from user input | Buffer overflow if size > dst |
| `memmove@plt` with overlapping ranges + user input | Same risk |
| `system@plt` / `popen@plt` with user input | Command injection; P0 |
| `execl@plt` / `execve@plt` with computed path | Command execution; check path source |
| `dlopen@plt` with computed path | Plugin loading; check if path is user-controlled |
| `mmap@plt` with `PROT_EXEC` | Self-modifying code or JIT — investigate |
| `mprotect@plt` with `PROT_EXEC` on writable memory | RWX memory — investigate |
| `ptrace(PTRACE_TRACEME)` | Anti-debug; flag and note workaround |
| `ptrace(PTRACE_ATTACH)` on others | Process injection |
| `rdtsc` pairs around code | Timing check anti-debug |
| `cpuid` with leaf 0x40000000 | VM detection (hypervisor leaf) |
| `in 0xE4` / `out 0xE4` | VM detection (backdoor port) |
| `int 0x80` (32-bit) or `syscall` (64-bit) | Direct syscall; check syscall number |
| `cs:gs:[0x30]` access (Windows) | PEB access — anti-debug / API resolution |
| `cs:gs:[0x60]` access (Windows) | TEB access — same |
| TOCTOU pattern: `access()` followed by `open()` | Time-of-check time-of-use race; P0 |
| `strcpy(dst, getenv("..."))` | Environment variable + unsafe copy |

## Recovering struct layouts

C structs are laid out sequentially with natural alignment (unless `#pragma pack(N)` or `__attribute__((packed))`).

Find struct layouts by:
1. Looking at field accesses (`mov rax, [rdi+0x10]` — field at offset 0x10)
2. Looking at offsets passed to `free` (the offset 0 field of a heap-allocated struct)
3. Looking at `memset` calls with the struct size
4. Looking at `memcpy` from a static initializer (`lea rsi, [rip+init_data]`)
5. Looking at `sizeof` arguments in `malloc`/`calloc` calls

For each struct, list fields with offset + size + inferred type:
```
struct user_t {            // size = 0x48 (72 bytes)
    char    name[32];      // offset 0x00, size 0x20
    uint32_t uid;          // offset 0x20, size 0x04
    // 4 bytes padding
    uint64_t created_at;   // offset 0x28, size 0x08
    char*   email;        // offset 0x30, size 0x08
    uint32_t flags;        // offset 0x38, size 0x04
    // 4 bytes padding
    uint64_t hash;         // offset 0x40, size 0x08
};
```

For C++, also see `re-playbooks/stl-recovery.md` for Itanium ABI RTTI structure and STL container size lookup tables.

## When to escalate to dynamic

Escalate when:
- Packed binary (high entropy `.text`, small stub) — static can't see payload
- Dynamically-resolved APIs (no imports but obvious network/file behavior) — need to log resolved APIs
- Encrypted strings (no readable strings) — need to dump post-decrypt
- Self-modifying code — need to dump post-modify
- VM-protected (dispatcher pattern) — symbolic exec or trace

Otherwise, static is enough. Recover the logic, write the pseudocode, generate the report.

## Output

After recovering the function semantics, you should be able to write:

```
main(argc=rdi, argv=rsi):
    if argc != 2:                    # cmp edi, 2; jne .Lerr
        puts("usage: prog <input>");  # lea rdi, [rip+s1]; call puts@plt
        return 1;
    fd = open(argv[1], 0);           # mov rdi, [rsi+8]; mov rsi, 0; call open@plt
    if fd < 0:                       # test eax, eax; js .Lerr
        perror("open");
        return 1;
    buf[256];
    n = read(fd, buf, 256);          # mov rdi, eax; lea rsi, [rbp-256]; mov rdx, 256; call read@plt
    write(1, buf, n);                # mov edi, 1; lea rsi, [rbp-256]; mov rdx, rax; call write@plt
    close(fd);                       # call close@plt
    return 0;
```

This is the deliverable. It's specific, verifiable (the reader can check each line against the disasm), and ready for the report.

## Verification checklist — for the agent before finalizing C binary RE report

- [ ] Binary triaged via `scripts/re_triage.py` (format, arch, security features, sections, imports all recorded)
- [ ] `main` identified via `_start` backtrack (ELF) or CRT startup chain (PE)
- [ ] All functions enumerated (via symbol table, PLT scan, prologue scan, or call-reference scan)
- [ ] Cross-reference map built for all imports (each import -> caller functions)
- [ ] Each "interesting" function has pseudocode written
- [ ] Crypto constants identified (cross-reference `crypto-identification.md`)
- [ ] Struct layouts inferred (offsets + types) for all data structures used by interesting functions
- [ ] Bug patterns catalogued (each entry cites offset + import + why it's a bug)
- [ ] Anti-debug / anti-VM techniques identified (cross-reference `anti-debug-evasion.md`)
- [ ] Decision made on static-vs-dynamic (cross-reference `mental-models/static-vs-dynamic.md`)
- [ ] All findings cite byte offsets (per `mental-models/evidence-vs-assertion.md`)
- [ ] Pseudocode marked with disasm comments citing offsets
- [ ] Synthesis section written — behavioral summary combining all functions
- [ ] Cross-references to sibling playbooks added where relevant

If any checkbox is unchecked, the C RE report is incomplete — go back and finish the missing layer before submission.
