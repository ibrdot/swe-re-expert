# CTF Rev Approach — Cracking Reversing Challenges

CTF reversing challenges are different from real-world RE: they're designed to be solvable in a few hours, often have a "flag" hidden behind a check, and use predictable patterns. The trick is recognizing the pattern fast.

## The 4-step CTF rev loop

1. **Triage** — `python scripts/re_triage.py --file <target> --all`. Get type, arch, security features, imports.
2. **Find the flag check** — `strings | grep -i flag`; if not found, look for `main` and trace input flow.
3. **Understand the check** — what transformation is applied to input? what's compared to what?
4. **Invert or brute** — work backward from the expected output to recover the input (flag).

## Common CTF rev patterns

### Pattern 1: Direct comparison

```c
if (strcmp(input, "flag{...}") == 0) {
    puts("correct");
}
```

**Detection:** `strings | grep flag` finds the flag directly. Or: `objdump -d | grep -A2 "call strcmp"` to find the call site, then look at the literal in `lea rdi, [rip+str]`.

**Solve:** read the flag from strings.

### Pattern 2: Byte-by-byte comparison

```c
for (int i = 0; i < len; i++) {
    if (input[i] ^ 0x42 != expected[i]) fail();
}
```

**Detection:** loop with `xor` then `cmp`; `expected` array in `.rodata`.

**Solve:** dump `expected`, XOR with `0x42`, decode the flag.

### Pattern 3: Checksum / hash comparison

```c
if (crc32(input) == 0xdeadbeef) pass();
```

**Detection:** `call crc32` or inline CRC table lookup; `cmp rax, <constant>`.

**Solve:** usually brute-force (z3) or known-plaintext attack on the hash. If CRC, sometimes reversible if you know enough input bytes.

### Pattern 4: Custom cipher

```c
encrypt(input, key);
if (memcmp(input, expected, len) == 0) pass();
```

**Detection:** encrypt function with simple algorithm (XOR, ADD, ROL, custom substitution); `expected` in `.rodata`.

**Solve:** reverse the cipher. Most CTF ciphers are invertible (XOR, ROL, substitution). Apply the inverse to `expected` to recover `input`.

### Pattern 5: VM-based challenge

The binary contains a custom bytecode interpreter. The "program" is in `.data`. The flag is checked by the program.

**Detection:** large `.data` section with byte sequences; main loop has a `switch` on a byte (the opcode); PC variable walks the data section.

**Solve:** 
1. Identify the VM dispatcher (the switch)
2. Map opcodes to semantics (opcode 0x01 = ADD, 0x02 = PUSH, etc.)
3. Disassemble the bytecode using your map
4. Understand what the program does
5. Invert the check or provide input that satisfies it

This is the most time-consuming pattern. Budget 2-4 hours.

### Pattern 6: Math / equation system

```c
// Many constraints on the input bytes
if (input[0] * 17 + input[1] * 3 == 0x1234 && ...)
    pass();
```

**Detection:** many `cmp` instructions with multiplications; looks like a system of equations.

**Solve:** z3 SMT solver. Encode the constraints, let z3 find a model. Or use angr for symbolic execution.

### Pattern 7: Anti-debug wrapper

The challenge has obvious anti-debug (`IsDebuggerPresent`, `ptrace(PTRACE_TRACEME)`, timing checks). The flag is revealed only when the checks pass.

**Detection:** imports include `IsDebuggerPresent` etc.; `rdtsc` pairs in the code.

**Solve:** patch the anti-debug checks to return success; or run with a stealth debugger; or use Unicorn to emulate.

## The "find main" trick for stripped CTF binaries

CTF binaries are often small and stripped. Finding main:

```bash
# 1. Find entry
objdump -d <target> | grep "<_start>:" -A20
# Look for the lea rdi, [rip+offset] before call __libc_start_main@plt
# That offset is main
```

Or in Ghidra, it auto-labels main.

## The "find the check" trick

Once you have main, the check is usually obvious:

```c
int main(int argc, char *argv[]) {
    char input[64];
    scanf("%s", input);          // <-- input read
    if (check(input))            // <-- the check
        puts("correct");
    else
        puts("wrong");
    return 0;
}
```

In disasm, `scanf` or `fgets` reads input, then `call <something>` is the check, then `test eax, eax` branches on result.

Trace into the check function — that's the real challenge.

## Common check function patterns

### XOR table

```asm
mov    rax, [rbp-0x40]     ; rax = input ptr
movzx  ecx, byte [rax+N]   ; input[N]
xor    ecx, 0x42            ; XOR with key
cmp    ecx, [expected+N]   ; compare to expected
jne    .Lfail
```

Dump `expected` and XOR with `0x42` to get the flag.

### Loop with rolling XOR

```c
char key[] = "secret";
for (int i = 0; i < len; i++) {
    if ((input[i] ^ key[i % 6]) != expected[i]) fail();
}
```

Dump `expected`, XOR with rolling key `secretsecretsecret...`, get flag.

### Permutation

```c
char expected[] = "lrcehetflag";
for (int i = 0; i < len; i++) {
    if (input[i] != expected[perm[i]]) fail();
}
```

Dump `expected` and `perm`, reorder `expected` by `perm` to get flag.

### Substitution table

```c
char sbox[256] = {...};  // 256-byte lookup table
for (int i = 0; i < len; i++) {
    if (sbox[input[i]] != expected[i]) fail();
}
```

Dump `sbox` and `expected`. For each byte in `expected`, find its index in `sbox` — that's the original input.

### Custom math

```c
for (int i = 0; i < len; i++) {
    int v = input[i] * 17 + 13;
    v ^= 0xAA;
    v = (v << 3) | (v >> 5);
    if ((v & 0xFF) != expected[i]) fail();
}
```

Invert the math: `((expected << 5) | (expected >> 3)) ^ 0xAA; (v - 13) / 17`. Watch for overflow and unsigned arithmetic.

## The brute force option

If the check is too complex to invert, but the flag space is constrained:

- **Length known** (usually 30-50 chars in CTF flags)
- **Character set known** (printable ASCII, often `flag{[a-z0-9_]+}`)
- **Check is local** (one call to check)

Use z3:

```python
from z3 import *

s = Solver()
flag = [BitVec(f'b{i}', 8) for i in range(40)]

# Constrain to printable ASCII
for b in flag:
    s.add(b >= 0x20, b <= 0x7e)

# Add the check constraints
# (encode the disasm logic here)
# Example: input[i] ^ 0x42 == expected[i]
expected = [0x4d, 0x42, ...]  # from .rodata
for i in range(40):
    s.add(flag[i] ^ 0x42 == expected[i])

if s.check() == sat:
    m = s.model()
    print(bytes([m[b].as_long() for b in flag]).decode())
```

Or use angr for full symbolic execution:

```python
import angr

proj = angr.Project('./challenge', auto_load_libs=False)
state = proj.factory.entry_state()
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=lambda s: b"correct" in s.posix.dumps(1))
print(simgr.found[0].posix.dumps(0))  # the input that triggers "correct"
```

## The "patch to win" approach

If the check is hard to invert but easy to patch:

```bash
# Find the conditional branch after the check
objdump -d <target> | grep -A2 "call.*check" | head
# Look for je / jne / jz that branches on the result

# Patch the jump:
# - je -> jmp (always take the "correct" path)
# - jne -> nop (skip the failure path)
# Edit the binary in your favorite hex editor or use radare2
r2 -w <target>
# In r2: seek to the je address, patch to jmp, write, quit
```

This gets you "correct" output but not the actual flag. Useful when the flag is printed only on success and you can read it from runtime memory.

## Tools cheat sheet

```bash
# Standard toolkit
file <target>; checksec --file=<target>
strings -a <target> | grep -iE "flag|correct|wrong"
objdump -d -M intel <target>
readelf -a <target>

# Better than objdump
r2 -A <target>
# In r2: aaaa (analyze), afl (list functions), pdf @main (disasm main)

# Ghidra for big or obfuscated challenges
analyzeHeadless /tmp Project <name> -import <target>

# Symbolic execution
python3 -c "import angr; ..."

# Z3 for constraint solving
python3 -c "from z3 import *; ..."

# Emulation (for anti-debug bypass)
# Use Unicorn for single functions
# Use Qiling for whole-binary
```

## Time budget

| Pattern | Time |
|---------|------|
| Direct comparison | 5 min (strings) |
| Byte XOR / ADD | 15 min (dump + invert) |
| Custom cipher | 30-60 min (reverse the math) |
| Math equations | 30 min (encode in z3, run) |
| VM-based | 2-4 hours (handler mapping + bytecode disasm) |
| Obfuscated (control flow flattening) | 4-8 hours (trace + CFG rebuild) |

If you're past 2 hours on a single challenge and not making progress, switch strategies: try angr symbolic execution, or try the "patch to win" approach.

## Output

The deliverable for a CTF rev challenge is the flag. The report should include:
- Challenge name
- Binary type / arch
- Pattern identified (XOR / VM / etc.)
- Solve approach
- The flag
- Brief explanation of how the check worked (for writeup)
