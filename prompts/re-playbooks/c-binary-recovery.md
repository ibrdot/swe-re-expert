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

## Function discovery when stripped

If the symbol table is gone, recover functions by:

### Method 1: PLT scan

Each PLT entry has a corresponding target. `objdump -d` shows `call func@plt`. Collect all `call <addr>` targets — those are function starts.

### Method 2: Prologue scan

Common x86-64 prologues (GCC -O2, no frame pointer):
- `48 83 ec NN` (sub rsp, N)
- `48 89 5c 24 NN` (mov [rsp+N], rbx) — MSVC style
- `55 48 89 e5` (push rbp; mov rbp, rsp) — older GCC with frame pointer
- `40 53` (push rbx) — leaf with rbx saved
- `f3 0f 1e fa` (endbr64) — modern GCC, marks valid indirect branch targets

Scan for these byte patterns. Each hit is a candidate function start.

### Method 3: Reference scan

For each `call` instruction in the disassembly, the target is a function. Build the set of call targets — those are all function starts.

### Method 4: Return scan

Each function ends with `ret` (or `jmp` for tail call). Each `ret` is a function end. The next byte after `ret` (often padding `cc` or `90`) is the next function start.

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

## Crypto constant detection

When you see these byte sequences in `.rodata` or stack, the binary uses the corresponding algorithm:

| Algorithm | First bytes | Hex |
|-----------|-------------|-----|
| AES S-box | 16 bytes | `63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76` |
| AES inverse S-box | 16 bytes | `52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb` |
| SHA-256 K[0..3] | First round constants | `42 8a 2f 98 71 37 44 91 b5 c0 fb cf e9 b5 db a5` |
| SHA-1 H0 | Initial hash values | `67 45 23 01 ef cd ab 89 98 ba dc fe 10 32 54 76` |
| MD5 T[0..3] | Sine table first entries | `d7 6a a4 78 e8 c7 b7 56 24 20 70 db c1 c0 e6 e0` |
| CRC32 table | First 4 entries | `00 00 00 00 96 30 07 77 2c 61 0e ee ba 51 09 99` |
| RC4 identity table | 256 sequential bytes | `00 01 02 03 04 05 06 07 08 09 0a 0b ... ff` |

Cross-reference the constant to find the function that uses it — that's the crypto implementation.

## Common bug patterns to flag

| Pattern | Why it matters |
|---------|----------------|
| `gets@plt` import + use | Always buffer overflow; P0 |
| `strcpy@plt` with user input source | Buffer overflow; P0 |
| `sprintf@plt` with user input format | Buffer overflow + format string; P0 |
| `printf@plt` with user input as format | Format string attack; P0 |
| `memcpy@plt` with size from user input | Buffer overflow if size > dst |
| `system@plt` / `popen@plt` with user input | Command injection; P0 |
| `dlopen@plt` with computed path | Plugin loading; check if path is user-controlled |
| `mmap@plt` with `PROT_EXEC` | Self-modifying code or JIT — investigate |
| `ptrace(PTRACE_TRACEME)` | Anti-debug; flag and note workaround |
| `rdtsc` pairs around code | Timing check anti-debug |
| `int 0x80` (32-bit) or `syscall` (64-bit) | Direct syscall; check syscall number |

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
