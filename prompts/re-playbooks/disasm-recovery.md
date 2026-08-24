# Disasm Recovery — Reading and Reconstructing from Assembly

The core skill of reverse engineering: reading disassembly and reconstructing the high-level source. This file is the practical guide.

## The 6-step per-function recovery loop

For each function you need to understand:

1. **Identify the calling convention** — which registers hold args, return
2. **Identify the frame layout** — saved registers, locals, where each lives
3. **Walk the basic blocks** — linear until a branch; each branch starts a new block
4. **Identify calls and arg preparation** — what's loaded into arg registers
5. **Identify conditionals and loops** — `cmp`/`test` + `jcc` patterns
6. **Write pseudocode** — combine blocks into high-level flow

## Identifying the calling convention

Without knowing the calling convention, you can't read args. Check:

| Platform | Int args (in order) | Return |
|----------|----------------------|--------|
| Linux x86-64 (SysV) | rdi, rsi, rdx, rcx, r8, r9 | rax |
| Windows x86-64 | rcx, rdx, r8, r9 | rax |
| Linux ARM64 | x0–x7 | x0 |
| Linux ARM32 | r0–r3 | r0 |
| Linux MIPS o32 | $a0–$a3 | $v0 |

Quick check: in the function, look for the first `mov` to one of these registers before a `call`. That's arg 1.

## Identifying the frame layout

Frame layout for System V AMD64 with frame pointer:

```
high ┌────────────────────┐
     │ return address     │  ← pushed by call
     │ saved rbp          │  ← pushed by prologue; rbp points here
     │ local var 1        │  ← [rbp-8]
     │ local var 2        │  ← [rbp-16]
     │ ...                │
low  │ (red zone, 128B)   │  ← leaf functions use without reserving
     └────────────────────┘
```

Without frame pointer (GCC -O2+):
```
high ┌────────────────────┐
     │ return address     │
     │ local var 1        │  ← [rsp+0]
     │ local var 2        │  ← [rsp+8]
     │ ...                │
low  │ (rsp moves as the function runs) │
     └────────────────────┘
```

To identify locals: look for `sub rsp, N` in prologue, then track `[rsp+N]` (or `[rbp-N]`) writes.

## Walking basic blocks

A basic block is a maximal sequence of instructions with:
- No branches out (except the last instruction)
- No branches in (except to the first instruction)

To walk blocks:
1. Start at function entry
2. Read linearly until a branch instruction (`jmp`, `jcc`, `ret`, `call`)
3. The branch instruction is the last instruction of the current block
4. The branch target starts a new block
5. Repeat

For each block, record:
- Start address
- End address (last instruction)
- Branches out (target addresses)
- Side effects (register writes, memory writes, calls)

## The "trace the arg" technique

When you can't understand a function, trace the args:

```asm
; Function starts here
push   rbp
mov    rbp, rsp
sub    rsp, 0x20
mov    [rbp-0x18], rdi     ; arg1 (rdi) saved to local at [rbp-0x18]
mov    [rbp-0x14], esi    ; arg2 (esi, 32-bit) saved to [rbp-0x14]
mov    [rbp-0x4], 0       ; int i = 0
jmp    .L2
.L3:
mov    eax, [rbp-0x4]      ; load i
cdqe
movzx  eax, byte [rbp-0x18+rax]  ; load arg1[i]
sub    eax, 0x20
movsx  edx, al
mov    rax, [rbp-0x18]
mov    ecx, [rbp-0x4]
cdqe
mov    [rax], dl            ; arg1[i] = (arg1[i] - 0x20)
add    [rbp-0x4], 1         ; i++
.L2:
cmp    [rbp-0x4], 0x9
jle    .L3                  ; while i <= 9
leave
ret
```

Trace:
- arg1 = `rdi` (a pointer — used in `mov [rax], dl` which writes through it)
- arg2 = `esi` (a 32-bit int — saved but never used; flag that as suspicious, or maybe it's a length we ignore)
- Local at `[rbp-0x4]` = loop counter `i`
- Loop body: `arg1[i] -= 0x20` (subtract 32 from each byte — `0x20` is space; 0x20 below lowercase ASCII = uppercase; `0x61` ('a') - 0x20 = 0x41 ('A'))
- Loop runs while `i <= 9` (10 iterations)

So this function is:
```c
void lowercase_to_uppercase(char *buf /*, int unused */) {
    for (int i = 0; i <= 9; i++) {
        buf[i] -= 0x20;  // 'a'-'z' → 'A'-'Z'
    }
}
```

The trace told us:
- The arg types (ptr + int)
- The loop body
- The loop bound
- The likely source-level intent (case conversion)

## Recognizing high-level patterns in disasm

### `if` statement

```asm
cmp    [rbp-N], 0          ; test var
je     .Lelse              ; if equal to 0, go to else
; then-block
.Lelse:
; else-block (or continue after if)
```

Or:
```asm
test   eax, eax
jne    .Lthen
; else-block
jmp    .Lend
.Lthen:
; then-block
.Lend:
```

### `if-else`

Recognized by the `jcc` to one label and `jmp` to another.

### `while` loop

```asm
.Lstart:
cmp    [rbp-N], M
jge    .Lend               ; exit condition
; body
add    [rbp-N], 1          ; or similar counter increment
jmp    .Lstart
.Lend:
```

### `for` loop

Same as `while`, but with explicit init (before .Lstart) and explicit increment (before the jmp).

### `do-while`

```asm
.Lstart:
; body (always runs at least once)
cmp    ...
jcc    .Lstart            ; loop back if condition
```

### `switch`

```asm
mov    eax, [rbp-N]        ; load value
cmp    eax, K              ; max case
ja     .Ldefault
jmp    [table + eax*8]    ; jump table
.Lcase0:
...
.Lcase1:
...
.Ldefault:
...
```

Identified by `jmp [table + eax*8]` pattern. Dump the table at `table` address for K+1 entries.

### Function call

```asm
mov    rdi, [rbp-N]        ; arg1
mov    rsi, [rbp-M]        ; arg2
mov    rdx, [rbp-P]        ; arg3
call   func@plt
mov    [rbp-Q], rax        ; save return value
```

Recognized by sequence of arg register writes followed by `call`.

### Memory copy / string op

```asm
lea    rdi, [dst]
lea    rsi, [src]
mov    rcx, N              ; length
rep movsb                  ; memcpy
```

Or:
```asm
lea    rdi, [dst]
mov    al, 0               ; fill byte
mov    rcx, N
rep stosb                  ; memset(dst, 0, N)
```

## The "follow the data" technique

When control flow is too complex, follow data instead:

1. Pick a piece of data (input byte, struct field)
2. Find every place it's read or written
3. Connect the reads to the writes
4. Understand the data lifecycle

For example, to understand what happens to user input:
1. Find where it enters (scanf, fgets, read)
2. Find every `mov` that uses the buffer address
3. Trace transformations (XOR, ADD, lookup table)
4. Find the comparison (the "check")
5. Now you know what transformation the input goes through

This works when CFG is obfuscated (control flow flattening, VM-based) because data flow is harder to obfuscate.

## The "cross-reference" technique

Use the binary's own xref info:

```bash
# Ghidra: xrefs are auto-computed
# In the listing view, every label shows "XREF" comments showing where it's referenced from

# IDA: View → Open subviews → Xrefs (or Shift+X)

# objdump:
objdump -d <target> | grep "call.*<target_function>"
# All call sites of target_function

# radare2:
r2 -A <target>
[0x...]> axt @ sym.imp.printf     # xrefs to printf
```

Cross-references let you answer "where is this function called from?" without reading the entire binary.

## Writing pseudocode

After walking a function, write the source-level equivalent. Format:

```c
// Function: process_input
// Address: 0x401234
// Calling convention: System V AMD64 (rdi=arg1, rsi=arg2)
// Args:
//   arg1 (rdi) = char* input
//   arg2 (esi) = int len
// Returns: int (in rax)
int process_input(char *input, int len) {
    int count = 0;
    for (int i = 0; i < len; i++) {
        if (input[i] == 'A') {  // 0x41
            count++;
        }
    }
    return count;
}
```

Notes:
- Always include the calling convention
- Always include the original address
- Annotate args with their inferred types
- Add comments explaining inferred intent (not just the literal disasm)
- Mark uncertain inferences (use `// ???` or `// HYPOTHESIS`)

## The "complex function decomposition" technique

For long functions (>200 instructions):

1. **Identify loops** first (the `jmp` back to an earlier label)
2. **Identify branches** (`jcc` instructions)
3. **Group instructions into logical sections** (initialization, loop body, post-processing)
4. **Write pseudocode per section** rather than the whole function at once

This makes the work tractable. Trying to write pseudocode for a 500-instruction function in one pass is impossible; doing it section by section takes 30 minutes.

## Anti-patterns to watch for

When the disasm looks "weird":

- **Random-looking `xor` instructions** (`xor reg, reg` is zeroing; `xor reg, [mem]` may be decryption)
- **Long runs of `nop`** — likely padding for alignment; sometimes patch space for hooks
- **`mov` to `.text` addresses** — self-modifying code; investigate
- **`syscall` not preceded by libc call** — direct syscall; check syscall number in `rax`
- **`int 0x80` on x86-64** — 32-bit syscall on 64-bit; unusual, investigate
- **Stack canary check** (`__stack_chk_fail` import + canary in prologue) — normal but worth noting for exploit planning
- **`lea` without `mov`** — calculating addresses without dereferencing; often string pointers

## When to give up on a function

A function may be too complex to recover manually if:
- It's > 1000 instructions (likely an autogenerated state machine)
- It's VM-protected (dispatcher loop with hundreds of cases)
- It uses heavy control flow obfuscation (jumps everywhere, no clear flow)
- It uses hand-rolled crypto (a million `xor`/`add`/`rol` chains)

For these, escalate to:
- Ghidra's decompiler (much faster than hand-recovery)
- Symbolic execution (angr) — explore paths
- Dynamic tracing (Unicorn or gdb) — observe behavior

Don't try to brute-force understanding a 5000-instruction VM dispatcher by hand. That's weeks of work for one function.
