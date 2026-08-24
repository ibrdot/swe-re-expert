# Language Depth — C/C++/ASM, Python, Go, Rust

This is the agent's reference for language-specific detail. Read the section that matches the target language. Each section covers: idioms you'll see in disassembly, common bugs, modernization notes, and toolchain quirks.

---

## C / C++ / Assembly

The dominant RE domain. C/C++ compile to native code; understanding ABI, calling conventions, and compiler idioms is the foundation of binary RE.

### Calling conventions by platform/arch

| Platform | Calling convention | First N args in | Stack cleanup |
|----------|---------------------|-------------------|----------------|
| Linux x86-64 (System V AMD64) | SysV AMD64 | rdi, rsi, rdx, rcx, r8, r9 (ints); xmm0–xmm7 (floats) | Caller |
| Windows x86-64 | Microsoft x64 | rcx, rdx, r8, r9 (ints); xmm0–xmm3 (floats) | Caller |
| Linux x86 (32-bit) | cdecl | All on stack, right-to-left | Caller |
| Windows x86 (32-bit) | cdecl / stdcall / fastcall | cdecl/stdcall: stack; fastcall: ecx, edx then stack | stdcall: callee, others: caller |
| Linux ARM64 (AArch64) | AAPCS64 | x0–x7 | Caller |
| Linux ARM32 (AAPCS) | AAPCS | r0–r3 | Caller |
| Linux MIPS | O32 / N32 / N64 | $a0–$a3 (o32); more for n32/n64 | Caller |

Frame layout (System V AMD64):

```
high ┌──────────────────┐
     │ return address   │
     │ saved rbp        │  ← rbp points here
     │ local vars       │
     │ ...              │
low  │ red zone (128B)  │  ← leaf functions can use this without reserving
     └──────────────────┘
```

### Function prologue / epilogue patterns

x86-64 GCC (default with frame pointer):
```
push   rbp            ; save frame pointer
mov    rbp, rsp       ; new frame
sub    rsp, 0xNN      ; reserve locals
...
leave                ; mov rsp, rbp; pop rbp
ret
```

x86-64 GCC (-O2, omit frame pointer, very common):
```
sub    rsp, 0xNN      ; reserve locals directly on rsp
...
add    rsp, 0xNN
ret
```

x86-64 MSVC:
```
mov    [rsp+8], rcx   ; save arg1 to local
sub    rsp, 0x28      ; reserve + alignment
...
add    rsp, 0x28
ret
```

ARM64:
```
stp    x29, x30, [sp, #-0x10]!  ; push frame ptr + link register
mov    x29, sp                    ; new frame
...
ldp    x29, x30, [sp], #0x10     ; pop
ret                                 ; uses x30
```

### Common instruction idioms

| Idiom | Pattern | Meaning |
|-------|---------|---------|
| Stack buffer zero | `xor eax, eax; mov [rbp-N], eax` (repeat) or `rep stosb` | Initialize local buffer to zero |
| `memcpy` inline | `lea rdi, [dst]; lea rsi, [src]; mov rcx, N; rep movsb` | Compiler inlined small memcpy |
| `memset` inline | `mov rdi, dst; mov al, byte; mov rcx, N; rep stosb` | Inlined memset |
| Switch table | `mov rax, [rbp-N]; cmp rax, K; ja default; jmp [rbx+rax*8]` | Switch statement with K+1 cases |
| Inline compare-and-jump | `cmp [rax+N], M; jne L_else` | Branch on struct field |
| Global var access | `mov rax, QWORD PTR [rip+0xNNNN]` | Position-independent global access |
| PIC GOT indirection | `mov rax, QWORD PTR [rip+symbol@GOTPCREL]` | Load address of a global through GOT |
| String in rodata | `lea rdi, [rip+0xNNNN]` then `call puts` | Reference to `.rodata` string |
| Struct field read | `mov eax, [rdi+0x10]` | Read offset 0x10 from struct ptr (rdi) |
| Vtable call | `mov rax, [rdi]; call [rax+0x18]` | Virtual method dispatch — vtable at obj+0x0, method at vtable+0x18 |
| Tail call | `jmp func` after restoring frame | Caller-reused stack for tail-call optimization |
| Leaf function | No prologue, just `ret` | No stack frame, cheap call |

### Crypto constant detection in disassembly

Common AES, SHA, MD5, RC4 constants — when you see these byte patterns in `.rodata` or stack, the binary uses the corresponding crypto:

| Algorithm | Constant pattern | Hex |
|-----------|-------------------|-----|
| AES S-box | First 16 bytes of the S-box | `63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76` |
| AES inverse S-box | First 16 bytes | `52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb` |
| SHA-256 K[0..3] | First round constants | `42 8a 2f 98 71 37 44 91 b5 c0 fb cf e9 b5 db a5` |
| SHA-1 H0 | Initial hash values | `67 45 23 01 ef cd ab 89 98 ba dc fe 10 32 54 76` |
| MD5 T[0..3] | Sine table | `d7 6a a4 78 e8 c7 b7 56 24 20 70 db c1 cdd e6 e0` |
| CRC32 table | First 4 entries | `00 00 00 00 96 30 07 77 2c 61 0e ee ba 51 09 99` |
| RC4 init table | Sequential `00 01 02 ... ff` | Identity permutation |

For each, also check the code references — finding the table in `.rodata` + a KSA-like loop nearby confirms the algorithm.

### Common memory bugs to look for

| Bug class | Source pattern | Detection |
|-----------|----------------|------------|
| Stack buffer overflow | `char buf[N]; strcpy(buf, src);` | `strcpy` import + `sub rsp, N` nearby |
| Heap overflow | `malloc(N); memcpy(ptr, src, M);` with `M > N` | Size mismatch in args |
| Format string | `printf(user_input)` (no format string literal) | `lea rdi, [user_input]; xor eax, eax; call printf@plt` |
| Use-after-free | `free(ptr); ...; deref ptr` | Hard static — needs flow analysis |
| Double free | Two `free(ptr)` without intervening `malloc` | Same |
| Off-by-one | `for (i = 0; i <= N; i++)` instead of `< N` | Loop bound check |
| Integer overflow | `(int)x * (int)y` on attacker-controlled ints, used as size | Multiplication result used as `malloc` size |
| Type confusion | C++: virtual call on object of wrong dynamic type | Look at vtable pointer at offset 0; compare to expected vtable address |

### Modern C++ patterns

C++ binaries often have these in their layout:

| Pattern | Where | Notes |
|---------|-------|-------|
| vtables | `.data.rel.ro` (GCC) or `.rdata` (MSVC) | Array of function pointers; first non-static field of polymorphic class points here |
| RTTI | `.rodata` | Type info strings (`NSt...`, class names mangled) — strip with `-fno-rtti` |
| Exception tables | `.eh_frame`, `.gcc_except_table` | Used by stack unwinder; usually red herrings for RE |
| C++ name mangling | All symbol sections | `__ZN3Foo4funcEv` = `Foo::func(void)`; demangle with `c++filt` or `__cxa_demangle` |
| TLS init | `.tdata`, `.tbss` | Thread-local storage |
| Static initializers | `.init_array` (GCC), `.CRT$XCU` (MSVC) | Functions called before `main` |

### Stripped binaries — function recovery

Stripped = no `.symtab` / `.strtab`. Recover functions by:

1. **Prologue scan**: search for `55 48 89 e5` (push rbp; mov rbp, rsp) or `48 83 ec NN` (sub rsp) followed by `c3` (ret) somewhere later
2. **Reference scan**: find `call <addr>` instructions — those addrs are function starts
3. **PLT scan**: each PLT entry has a corresponding target. `objdump -d` shows `call func@plt`
4. **Entry point backtrack**: `_start` → `__libc_start_main` → `main`. Find the `lea rdi, [main]` before the libc call.

For Go binaries, use the `gopclntab` section (it's a function & line-number table Go embeds even when "stripped"). See Go section below.

### Compiler-specific quirks

- **GCC** tends to keep frame pointers in debug builds, omit in `-O2`. Default is `-O2` for most distros.
- **MSVC** often uses `__GS_COOKIE` checks (stack canary); look for `mov rax, QWORD PTR [rip+__security_cookie]` and `xor rax, rsp` in prologue, `__security_check_cookie` call in epilogue.
- **Clang** matches GCC closely on Linux; on macOS it's the default and follows Apple ABI specifics.
- **TCC (Tiny C Compiler)** generates very simple, unoptimized code; functions are easy to spot but patterns differ.
- **Rust** uses Itanium-style C++ ABI mangling with prefix `_R`; demangle with `rust-demangle` or `rustfilt`.

---

## Python

Python RE is rare (mostly source-level work via `.pyc`), but Python SWE is dominant. Notes focus on review / refactor.

### `.pyc` analysis

```bash
# Disassemble .pyc to bytecode
python -m dis <module>.pyc
python -m dis module.py    # Easier — dis the source

# Decompile .pyc to source (best tool: pycdc)
# https://github.com/zrax/pycdc
pycdc <module>.pyc > module.py

# Or with uncompyle6 (works up to Python 3.8 only)
uncompyle6 <module>.pyc > module.py
```

`.pyc` files contain a magic number (Python version), timestamp, source size, and marshalled code object. Each Python version has a different magic — version compatibility is a real pain.

### Python-specific anti-patterns (P0/P1)

| Pattern | Why it's bad | Fix |
|---------|--------------|-----|
| `pickle.loads(user_data)` | RCE | Use `json` or schema-validated deserializer |
| `eval(user_input)`, `exec(user_input)` | RCE | Don't accept Python literals from users; use `ast.literal_eval` for literal-only |
| `subprocess.run(cmd, shell=True)` with concat | Command injection | Use `shell=False`, pass args as list |
| `os.system(...)` | Same as above; also no error capture | Use `subprocess.run([...], check=True)` |
| `yaml.load(stream)` (unsafe loader) | RCE | `yaml.safe_load(stream)` |
| Mutable default args `def f(items=[])` | State leaks across calls | `def f(items=None): items = items or []` |
| Bare `except:` | Swallows KeyboardInterrupt, SystemExit; hides bugs | `except Exception:` minimum; better, catch specific |
| `assert x == y, "msg"` in production | `python -O` strips asserts | Use `if not x == y: raise AssertionError(...)` |
| Path concat with `+` | Platform differences, traversal | `pathlib` or `os.path.join` with explicit base |
| `random.randint` for crypto | Predictable | `secrets.randbelow` or `os.urandom` |
| `passlib` SHA-1 etc. | Weak hash | `argon2`, `bcrypt`, `pbkdf2_hmac` with high iterations |
| `request.GET.get('id')` then raw SQL | SQLi | Parameterized queries / ORM |

### Python modernization

- **Python 3.13+**: free-threaded build (`--disable-gil`), better error messages, `--app` mode for embedded, REPL multiline editing improvements
- **Type hints**: `mypy`/`basedpyright` for strict checking, `pydantic v2` for runtime validation
- **Tooling**: `ruff` replaces `flake8` + `black` + `isort`; `uv` replaces `pip`+`venv`+`pip-tools`
- **Performance**: `__slots__` for memory-tight classes; dataclasses for immutable value objects; `functools.cached_property` / `lru_cache` for memoization
- **Async**: 3.11+ `asyncio.TaskGroup` for structured concurrency; 3.12 `asyncio.eager_task_factory` for faster task creation; 3.13 `asyncio.QueueShutDown`

### Python idiom detection in bytecode

In `.pyc` disassembly, these instruction patterns hint at source-level constructs:

| Idiom | Bytecode |
|-------|----------|
| List comprehension | `LOAD_CONST <code object>`; `MAKE_FUNCTION`; `GET_ITER`; `FOR_ITER`; ... `LIST_APPEND` |
| Dict comprehension | similar; `MAP_ADD` |
| Generator | `MAKE_FUNCTION` with `generator` flag; `GET_ITER`; `YIELD_VALUE` |
| f-string | `FORMAT_VALUE 0` after `LOAD_ATTR`/`LOAD_METHOD` chains |
| `with` statement | `WITH_CLEANUP_START`; `WITH_CLEANUP_FINISH` (pre-3.9) or `WITH_EXCEPT_START` (3.9+) |
| Decorator | `MAKE_FUNCTION`; `LOAD_NAME decorator`; `CALL`; `STORE_NAME func` |

---

## Go

Go binaries are large, often stripped, but contain rich metadata (`gopclntab`) that makes them surprisingly analyzable.

### Go binary structure

| Section | Purpose |
|---------|---------|
| `.gopclntab` | Function & line-number table — recovers all function names + source lines even when "stripped" |
| `.gopclntab.pcheader` (1.20+) | Embedded PC->line header |
| `.symtab` | Symbol table (often stripped) |
| `.gosymtab` | Go-specific symbol section |
| `.rodata` | Strings, type info |
| `.typelink` | Type descriptors (interface types) |
| `.itablink` | Interface tables — concrete type → interface impls |

Tools:
```bash
# Recover function names from gopclntab
go tool nm <binary>      # Lists functions, including source paths
go tool objdump <binary> # Disasm with Go annotations
# Or use Ghidra's Go analyzer extension (gosym + gopclntab parser)

# Symbol recovery
python -c "import gopclntab_parser"  # See github.com/0xjiyu/gopclntab-parser
# Or use:
# - github.com/williballenthin/Ghidra_GoBinaryAnalyzer
# - IDAGolangHelper for IDA
```

### Go calling convention

Go has its own ABI (different from C). Important for hand-RE:

- **Go 1.17+ (regabi)**: args in registers (rax, rbx, rcx, rdi, rsi, r8, r9, r10, r11), then stack. Stack grows down, no frame pointer by default.
- **Pre-1.17**: all args on the stack. Easier to read but slower.
- **Stack check prologue**: every function begins with a check for stack space:
  ```
  mov    rax, QWORD PTR gs:[0x30]    ; goroutine stack bound
  cmp    rsp, rax
  jbe    runtime.morestack           ; need to grow stack
  ...
  ```

### Go-specific idioms in disasm

| Idiom | Pattern |
|-------|---------|
| Goroutine spawn | `mov rax, QWORD PTR [function_ptr]; mov rcx, [argptr]; call runtime.newproc` |
| Channel send | `mov rax, [chan_ptr]; call runtime.chansend1` |
| Channel receive | `call runtime.chanrecv1` (discard) or `runtime.chanrecv2` (with ok) |
| Map access | `call runtime.mapaccess1` / `mapaccess2` (with ok) |
| Slice grow | `call runtime.growslice` |
| Type assertion | `call runtime.assertE2T` / `assertI2T` |
| Interface call | `mov rax, [itab_ptr]; mov rcx, [rax+0xNN]; call rcx` |
| String concatenation | `call runtime.concatstrings` |
| `defer` registration | `call runtime.deferproc`; later `runtime.deferreturn` |

### Go code review focus

| Pattern | Why it matters |
|---------|-----------------|
| Unhandled `error` return (`_, err := f(); err != nil`) ignored | Silent failure, real bug |
| `panic` in library code | Should be `error` instead |
| Globals mutated across goroutines without sync | Race condition; verify with `go test -race` |
| `interface{}` everywhere | Loses type safety — prefer generics (Go 1.18+) |
| Long `if err != nil` chains | Consider wrapping; the Go community accepts this idiom but watch for nesting > 3 |
| Map/slice pre-allocation missing | `make([]T, 0, N)` is faster than repeated `append` growth |
| `time.Sleep` used for synchronization | Always wrong — use channel or `sync.WaitGroup` |
| `context.Background()` propagated into deep code | Loses cancellation; should be request-scoped |
| Goroutine leak (no shutdown path) | Goroutine runs forever, holds resources |

### Go modernization

- **Generics** (1.18+): replace `interface{}` + type-assert patterns with type parameters where it reduces code
- **`slog`** (1.21+): structured logging; replaces `log` package for new code
- **`errors.Join`** (1.20+): wrap multiple errors
- **`maps`/`slices` packages** (1.21+): standard-library generic helpers; replaces bespoke utilities
- **`range-over-int`** (1.22+): cleaner range syntax
- **`for v := range channel`** (1.22+): range over channels; cleaner concurrency
- **`go vet -shadow`** enabled by default (1.22+)

---

## Rust

Rust binaries are stripped of most metadata by default, but panic strings embed useful hints.

### Rust binary signatures

| Signature | What it tells you |
|-----------|---------------------|
| `.rustc` section | Rust binary; version info may be present |
| Panics like `called Option::unwrap() on a None value` | Source-level panic info available |
| `core::panicking::panic`, `core::panicking::panic_fmt` | Library panic entry points |
| `__rust_alloc`, `__rust_realloc`, `__rust_dealloc` | Allocator hooks (might be hooked for analysis) |
| `__rust_no_alloc_shim_is_unstable` | Internal alloc shim; can ignore |
| `core::ptr::drop_in_place<T>` | Destructor invocation; monomorphized for each T |

### Rust name mangling

Rust uses Itanium ABI with prefix `_R`. Examples:

| Mangled | Demangled |
|---------|-----------|
| `_RNvCs42Nns_4demo3foo` | `demo::foo` |
| `_RNvNtCs1234_4core3str5charsE` | `<core::str::chars as ...>` |
| `_RINvNtCs_4core5slice4iterB2_` | `core::slice::iter::<...>` |

Demangle with `rust-demangle` (Python lib) or `rustfilt` CLI.

### Rust calling convention

- Same as C on each platform (System V AMD64 on Linux x86-64, etc.)
- Generics are monomorphized — each instantiation is a separate function
- Trait objects use vtables (similar to C++), stored separately in `.data.rel.ro`
- ZST (zero-sized types) are passed as no arg — beware zero-sized locals that look like missing args

### Rust code review focus

| Pattern | Why it matters |
|---------|-----------------|
| `unsafe` block without safety comment | Review each `unsafe` for soundness; the invariant should be documented |
| `unwrap()` / `expect()` in non-prototype code | Panics on None/Err; prefer `?` or `match` |
| `.clone()` on hot path | Allocation; consider `Cow<str>` or `&str` |
| `Box<dyn Trait>` where generic would do | Dynamic dispatch + heap alloc; consider `impl Trait` |
| `Arc<Mutex<T>>` for read-heavy data | `RwLock` or `Arc<T>` (immutable) often better |
| `tokio::spawn` without `JoinHandle` management | Detached task; can leak; consider `tokio::task::JoinSet` |
| `await` after `?` in async error paths | Cancellation safety — verify the future can be safely dropped mid-await |
| `unsafe impl Send/Sync` | Cross-thread safety hand-asserted; review invariants carefully |
| `mem::forget` of resource-owning types | Bypasses Drop; can leak resources |

### Rust modernization

- **Edition 2024**: `let-else`, `let-chains`, async fn in traits (without `async_trait` crate), `gen` blocks (experimental)
- **`Result::Err` inspection**: `if let Err(e) = result` is now idiomatic; avoid `match` with one arm
- **`clippy`**: catches most modernization opportunities — run with `-W clippy::pedantic` for thorough pass
- **`cargo-bench`** + **`criterion`**: better benchmarks than ad-hoc timing
- **`cargo-miri`**: interpreter for UB detection in unsafe code
- **`cargo-audit`**: CVE check on dependencies
- **`cargo-feature`** / `cargo-udeps`**: detect unused feature flags and dependencies

---

## Cross-language notes

### Mixed-language binaries

When a binary has more than one language (e.g., Rust with C FFI, Go with cgo, Python with C extension):

- The C portions usually have full symbol info if not stripped
- The Rust/Go portions have their own conventions; treat as separate analysis
- FFI boundaries are the highest-value targets for bug hunting (assumptions about ownership/lifetime often violated)

### Sample language fingerprint

To quickly fingerprint a stripped binary's language, look at:

| Signal | Language |
|---------|-----------|
| `.comment` contains `GCC: (GNU) ...` | C/C++ (GCC) |
| `.comment` contains `clang version ...` | C/C++ (Clang) |
| `.comment` contains `Microsoft (R) ...` | C/C++ (MSVC) |
| `.rustc` section exists | Rust |
| `.gopclntab` section exists | Go |
| `.nv_fatb` / CUDA sections | CUDA |
| Symbols start with `_Z` (C++ Itanium ABI) | C++ |
| Symbols start with `_R` | Rust |
| Symbols start with `__imp_` | PE imported function |
| `.debug_*` sections present | Not stripped; debug info available |

Quick script:

```bash
for section in .rustc .gopclntab .comment .GCC_command_line; do
    if objdump -h <target> | grep -q "$section"; then
        echo "Found $section"
    fi
done
```
