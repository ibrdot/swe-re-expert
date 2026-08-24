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

## Recovering Go module paths from buildinfo

Go 1.18+ embeds the module path, version, and dependency list in the binary. Extract via:

```bash
# Use Go toolchain if available
go version -m <target> | head -50
# Output: path, version, dep path, dep version

# Or via Python (for cross-platform, no Go toolchain needed)
python3 -c "
import sys
data = open(sys.argv[1], 'rb').read()
# Find the buildinfo marker
marker = b'\\xff Go buildinf:'
idx = data.find(marker)
if idx > 0:
    # Parse the buildinfo structure
    ptr_size = data[idx + len(marker)]
    endian = data[idx + len(marker) + 1]
    print(f'Found buildinfo at offset {hex(idx)}')
    print(f'Pointer size: {ptr_size}, Endian: {endian}')
" target
```

The `buildinfo` reveals:
- Main module path (e.g., `github.com/ibrdot/example-app`)
- Go version (e.g., `go1.21.0`)
- Build settings (CGO enabled, build tags, etc.)
- All dependency module paths + versions
- Build flags (`-trimpath`, `-ldflags`, etc.)

This is gold for attribution: the module path tells you the project, and dependencies tell you what libraries the binary uses (which gives you the function-name lookup table — e.g., if `github.com/spf13/cobra` is in deps, the command-line argument parser is Cobra).

## Recovering the Go version (when .comment is stripped)

Even without `.comment`, the version is embedded in `runtime.buildVersion`:

```bash
# Find the build version string
strings -a <target> | grep "^go1\." | head -5
# Or look for runtime.buildVersion symbol (if symbols present)
nm <target> 2>/dev/null | grep "buildVersion"
# Or look for the version string pattern in .rodata
strings -a <target> | grep -E "^go1\.[0-9]+\.[0-9]+"
```

The Go version determines:
- ABI (pre-1.17 = stack-based, 1.17+ = regabi)
- `gopclntab` format (1.2, 1.16, 1.18, 1.20 each have slight differences)
- Available stdlib functions (e.g., `slices`, `maps`, `cmp` packages added in 1.21)

## Recovering interface implementations (itab analysis)

Go interfaces use itab tables. Each itab links an interface type to a concrete type + method table. Find itabs via the `.itablink` section or via runtime initialization calls.

```bash
# List itabs (if symbols present)
nm <target> 2>/dev/null | grep "itab"
# Or scan the .itablink section
objdump -s -j .itablink <target> | head
```

For each itab:
1. Identify the interface type (from `.typelink`)
2. Identify the concrete type (from `.typelink`)
3. The method table maps to the actual implementations

This is how you discover that, e.g., a `fmt.Stringer` interface is implemented by `User` struct — by finding the itab that connects them.

## Common Go runtime panic patterns

Go panics have distinctive patterns in the binary:

| Panic string | Source-level operation |
|--------------|-------------------------|
| `runtime error: index out of range` | Slice index out of bounds |
| `runtime error: slice bounds out of range` | Slice with bad start/end |
| `runtime error: integer divide by zero` | `/0` or `%0` |
| `runtime error: invalid memory address or nil pointer dereference` | Dereferencing nil pointer |
| `send on closed channel` | Sending to a closed channel |
| `concurrent map writes` | Map mutation race detected |
| `concurrent map read and map write` | Map read/write race |
| `sync: negative WaitGroup counter` | WaitGroup misuse |
| `close of closed channel` | Closing an already-closed channel |
| `close of nil channel` | Closing nil channel |
| `runtime: goroutine stack exceeds X` | Stack overflow (deep recursion or unbounded) |

Each of these tells you what risky operations the binary does. Map them to source-level concerns.

## When to escalate to dynamic

For Go, static usually gets you 90% there because `gopclntab` exposes so much. Escalate to dynamic when:
- Encrypted strings (rare in Go but possible — custom XOR or AES wrappers)
- Reflective API calls (`reflect.Value.Call`) — the function being called is computed at runtime
- Plugin loading (`plugin.Open`) — the loaded code is external
- Network behavior needs confirmation — FakeNet-NG to capture C2/HTTP calls
- Goroutine scheduling behavior (rarely needed; only for concurrency-bug analysis)

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

## Cross-references

- `re-playbooks/crypto-identification.md` — for crypto primitive fingerprinting when AES S-box or similar found
- `re-playbooks/disasm-recovery.md` — for general disasm heuristics that apply beyond Go
- `re-playbooks/anti-debug-evasion.md` — if the Go binary uses anti-debug (rare but possible via direct syscalls or PEB checks)
- `re-playbooks/api-resolution.md` — if the Go binary makes raw syscalls (uncommon; Go usually wraps via `syscall` package)
- `mental-models/static-vs-dynamic.md` — for the decision matrix on when to escalate
- `mental-models/evidence-vs-assertion.md` — every function-name recovery from gopclntab should cite the gopclntab entry offset

## Verification checklist — for the agent before finalizing Go binary RE report

- [ ] Go confirmed via `.gopclntab` section OR `runtime.*` strings OR `go1.*` version string
- [ ] Go version extracted (from `.comment` or `runtime.buildVersion`)
- [ ] All function names + addresses extracted via `go tool nm` or `gopclntab` parser
- [ ] Module path + dependencies extracted from `buildinfo` (if Go 1.18+)
- [ ] Itab tables analyzed for interface-to-impl mappings
- [ ] Type descriptors from `.typelink` applied to disasm
- [ ] Stack-check prologues recognized (gs:[0x30] access) and skipped in semantic recovery
- [ ] Go-specific instruction idioms (channels, maps, slices, goroutines) mapped to source-level operations
- [ ] String literals recovered (Go strings are (ptr, len) — use Go-aware extraction, not `strings`)
- [ ] Bug patterns flagged (unsafe.Pointer, cgo calls, global mutable maps, etc.)
- [ ] Panic strings mapped to risky source-level operations
- [ ] Decision made on static-vs-dynamic
- [ ] Cross-references added to sibling playbooks
- [ ] All findings cite byte offsets + gopclntab entry indices

If any checkbox is unchecked, the Go RE report is incomplete — go back and finish the missing layer before submission.
