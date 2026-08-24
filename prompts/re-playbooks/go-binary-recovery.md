# Go Binary Recovery — Reversing Stripped Go Binaries

Go binaries are large (often 5-15 MB for a simple program), look stripped, but contain rich metadata that makes them surprisingly analyzable. The trick is using the right tools and understanding Go's runtime conventions.

## Why Go binaries are different

- **Static linking by default** — most Go binaries bundle the entire runtime, so they're huge
- **No standard C calling convention** — Go has its own ABI ("regabi" since 1.17)
- **Embedded function/line table** — `.gopclntab` section survives stripping
- **Garbage collector** — runtime introspection adds visible metadata
- **Goroutine scheduling** — every function begins with a stack check
- **String layout** — Go strings are not null-terminated; they're `(ptr, len)` pairs

## The 5-step Go recovery loop

1. **Confirm Go** — `.gopclntab` section, `runtime.` prefix strings, `go:build` in `.comment`
2. **Recover functions** — use `gopclntab` to get all function names + source paths
3. **Recover strings** — Go strings are pointer+length, not null-terminated; need to scan differently
4. **Recover types** — `.typelink` section contains type descriptors; interfaces have itab tables
5. **Disassemble with Go-aware tooling** — `go tool objdump`, Ghidra GoBinaryAnalyzer, IDAGolangHelper

## Confirming Go

```bash
# Check sections
objdump -h <target> | grep -E "gopclntab|gosymtab|typelink|itablink"

# Check .comment for Go version
readelf -p .comment <target> 2>/dev/null   # may be missing if stripped
strings -a <target> | grep "^go1\."       # version string

# Check for runtime strings
strings -a <target> | grep "^runtime\." | head
```

If `.gopclntab` exists or you see `runtime.*` strings — it's Go.

## Recovering functions from gopclntab

`gopclntab` is a function and line-number table that Go embeds even in stripped binaries. It contains:
- Function name → start address mapping
- Source file paths
- Line numbers per PC

Tools to use:
```bash
# Easiest
go tool nm <target>        # Lists all functions with addresses
go tool objdump <target>   # Disasm with Go-aware annotations

# Ghidra (best for deep work)
# Install: https://github.com/mellertine/ghidra-golang-loader (or similar)
# Or use built-in Ghidra Go analyzer in recent versions

# IDA
# Use IDAGolangHelper: https://github.com/sibears/IDAGolangHelper

# Python-only parser
# https://github.com/0xjiyu/gopclntab-parser
```

Even if everything else is stripped, you'll get function names like:
```
main.main
main.handleRequest
runtime.main
runtime.morestack
runtime.chanrecv1
runtime.mapaccess1
```

## Go calling convention (regabi, 1.17+)

- Int args in registers: rax, rbx, rcx, rdi, rsi, r8, r9, r10, r11 (then stack)
- Float args in: xmm0–xmm14 (then stack)
- Return value: rax
- Stack grows down; **no frame pointer** by default (rsp is the frame)
- Stack must be checked for space at function entry — Go can grow the stack dynamically

## Function prologue — the stack check

Every non-leaf Go function begins with:
```
mov    rax, QWORD PTR gs:[0x30]      ; goroutine's stack bound
cmp    rsp, rax
jbe    runtime.morestack              ; need to grow stack
sub    rsp, N                          ; reserve locals
...
```

If you see `gs:[0x30]` access at function start, that's Go stack check. Skip past it for the real prologue.

## Go-specific instruction idioms

| Disasm pattern | Go source |
|----------------|------------|
| `mov rax, [func_ptr]; mov rcx, [argptr]; call runtime.newproc` | `go func_name(arg)` |
| `mov rax, [chan_ptr]; call runtime.chansend1` | `chan <- value` |
| `call runtime.chanrecv1` | `<- chan` (discard) |
| `call runtime.chanrecv2` | `v, ok := <- chan` |
| `call runtime.mapaccess1` | `m[k]` |
| `call runtime.mapaccess2` | `v, ok := m[k]` |
| `call runtime.growslice` | append that grows slice capacity |
| `call runtime.assertE2T` | type assertion (concrete type) |
| `call runtime.assertI2T` | type assertion (interface to concrete) |
| `mov rax, [itab_ptr]; mov rcx, [rax+0xNN]; call rcx` | interface method call |
| `call runtime.concatstrings` | `s1 + s2` |
| `call runtime.deferproc` | `defer f()` registration |
| `call runtime.deferreturn` | run deferred functions |
| `call runtime.panicdivide` | divide by zero panic |
| `call runtime.makeslice` | `make([]T, n)` |
| `call runtime.makemap` | `make(map[K]V)` |
| `call runtime.makechan` | `make(chan T)` |

## Recovering Go strings

Go strings are **not null-terminated**. They're a `(ptr, len)` struct passed in two registers.

To find strings:
- `strings -a` still works because Go strings in `.rodata` are followed by other data (often more strings), but you'll miss their boundaries
- For exact extraction, use a Go-aware tool (gopclntab parsers often extract strings too)
- Look for `runtime.concatstrings` calls — they take string structs as args

## Recovering Go types

The `.typelink` section contains type descriptors. Each type has:
- Name (mangled, e.g., `*os.File`, `[]byte`)
- Size, alignment
- Method set (for interfaces) or pointer methods (for structs)

Ghidra's Go analyzer auto-applies types. Without it, find `.typelink`, walk it manually.

For interface dispatch:
```asm
mov    rax, [rdi]          ; rdi = interface value; [rdi] = itab ptr
mov    rcx, [rax+0x18]     ; method at offset 0x18
call   rcx                  ; dispatch
```

The itab at `rax` has a method table; offset 0x18 is the 4th method (or whatever, depending on the interface). Cross-reference the itab address to find which concrete type is implementing the interface.

## Common Go bug patterns to flag

| Pattern | Why it matters |
|---------|----------------|
| `unsafe.Pointer` arithmetic | Memory unsafety; review carefully |
| `cgo` calls (`runtime.cgocall`) | FFI boundary; usually safe but check for use-after-free |
| `go func()` without recover in goroutine | Panic in goroutine crashes the process |
| Global `map` mutated across goroutines without sync | Data race; `go test -race` will catch |
| `interface{}` everywhere | Loses type safety; runtime panics possible |
| `time.Sleep` used as synchronization | Always wrong — use channel or WaitGroup |
| `context.Background()` propagated deep | Loses cancellation; should be request-scoped |
| `os.Exit` in non-main code | Skips defers; can leak resources |

## Identifying goroutines in disasm

`runtime.newproc` spawns a goroutine. Its first arg is the function pointer (in `rax` for regabi). Follow that pointer to find the goroutine entry function.

```asm
lea    rax, [rip+funcPtr]     ; rax = function pointer
mov    rcx, [rbp+argptr]      ; rcx = pointer to args struct
call   runtime.newproc         ; spawn goroutine
; size arg (small) is in rdi for regabi
```

## When to escalate to dynamic

For Go, static usually gets you 90% there because `gopclntab` exposes so much. Escalate to dynamic when:
- Encrypted strings (rare in Go but possible)
- Reflective API calls (`reflect.Value.Call`)
- Plugin loading (`plugin.Open`)
- Network behavior needs confirmation

## Output

After Go recovery, you should be able to produce a function inventory like:

```
main.main (0x401234) — entry point, calls main.parseArgs, main.runServer
main.parseArgs (0x401500) — parses CLI args, returns config struct
main.runServer (0x401800) — starts HTTP server on port, calls http.HandleFunc
main.handleRequest (0x401a00) — reads request body, calls main.process
main.process (0x401d00) — decrypts request using AES (S-box at 0x490000), calls main.respond
main.respond (0x402100) — writes encrypted response
```

Each function has: address, source-level name (recovered from gopclntab), behavior summary (recovered from disasm). This is your evidence table.
