# Rust Binary Recovery — Reversing Stripped Rust Binaries

Rust binaries strip most symbols by default, but panic strings, demangled symbols, and trait vtables give enough hooks to recover logic.

## Why Rust binaries are different

- **Heavy monomorphization** — each generic instantiation is a separate function
- **Trait objects use vtables** — similar to C++ virtual classes
- **Panic strings leak source info** — `called Option::unwrap() on a None value` etc.
- **Mangling is Itanium-style with `_R` prefix** — different from C++'s `_Z`
- **Zero-sized types (ZST)** — passed as no arg; can confuse arg-count analysis
- **Iterator chains** — compile to nested loops, hard to read

## The 6-step Rust recovery loop

1. **Confirm Rust** — `.rustc` section, panic strings, `__rust_*` symbols
2. **Recover panic strings** — they're source-level breadcrumbs
3. **Demangle symbols** — `_R...` → `module::function`
4. **Find vtables** — trait object dispatch uses them
5. **Identify monomorphized variants** — same source, different types
6. **Map iterator chains** — `for x in y.filter().map()` compiles to nested loops

## Confirming Rust

```bash
# Section check
objdump -h <target> | grep -E "rustc"

# Panic strings (always present unless panic=abort + stripped)
strings -a <target> | grep -E "called .+ on a|panic|index out of bounds"
strings -a <target> | grep "core::panicking"

# Allocation symbols
strings -a <target> | grep -E "__rust_alloc|__rust_realloc|__rust_dealloc"

# Mangling prefix
nm <target> 2>/dev/null | grep "^_R" | head
```

If `.rustc` exists or you see `core::panicking::panic` — it's Rust.

## Panic strings as source breadcrumbs

Rust panic strings are literal source-level text. They leak:
- Module paths: `core::slice::index::slice_index_positions_failed`
- Function context: `called Option::unwrap() on a None value`
- Source info: `byte index {byte} is out of bounds of {bytes}`

Map each panic string to a likely source location. The presence of `core::panicking::panic` calls in a function tells you that function does something risky (unwrap, indexing, arithmetic with overflow check).

## Demangling

Rust uses Itanium ABI mangling with `_R` prefix (vs C++'s `_Z`).

Examples:
| Mangled | Demangled |
|---------|-----------|
| `_RNvCs42Nns_4demo3foo` | `demo::foo` |
| `_RNvNtCs1234_4core3str5charsE` | `<core::str::chars>` |
| `_RINvNtCs_4core5slice4iterB2_` | `core::slice::iter::...` |

Demangle with:
```bash
rustfilt <mangled>          # CLI tool
# Or Python:
python3 -c "import rust_demangle; print(rust_demangle.demangle('_R...'))"
```

## Rust calling convention

Rust uses the platform's standard C ABI:
- **Linux x86-64**: System V AMD64 (rdi, rsi, rdx, rcx, r8, r9)
- **Windows x86-64**: Microsoft x64 (rcx, rdx, r8, r9)
- **ARM64**: AAPCS64 (x0–x7)

Same as C. The differences are in how the compiler uses the convention, not the convention itself.

Key Rust-specific quirks:
- **ZST (zero-sized types)** are passed as no argument. If you see a function call with fewer args than expected, one might be a ZST.
- **Slices** are passed as `(ptr, len)` — two args, not one.
- **Strings** (`&str`) are also `(ptr, len)`.
- **Option<T>** is typically passed as the value + a discriminant flag (in a separate register or packed with the value depending on the type).
- **Result<T, E>** similar — value + discriminant.

## Finding vtables (trait objects)

Trait objects (`&dyn Trait`, `Box<dyn Trait>`) are `(ptr, vtable_ptr)` pairs. The vtable contains:
- Offset 0x0: drop_in_place<T>
- Offset 0x8: size
- Offset 0x10: align
- Offset 0x18: method 1
- Offset 0x20: method 2
- ...

Disasm pattern:
```asm
mov    rdi, [rbp-0x18]      ; obj ptr (rdi = arg1)
mov    rax, [rbp-0x10]      ; vtable ptr
mov    rcx, [rax+0x18]      ; method 1
call   rcx
```

To find which concrete type backs the trait object, look at the vtable address. The vtable is in `.data.rel.ro` and has a name like `<Foo as Trait>::{vtable}` if symbols are present, or you can find it by:
1. Looking at what writes the vtable ptr to the object slot
2. Following the vtable ptr to its address in `.data.rel.ro`
3. The methods in the vtable point back to the concrete impl

## Common Rust patterns in disasm

| Pattern | Likely source |
|---------|----------------|
| `call core::panicking::panic` | `unwrap()` / `expect()` / indexing / overflow |
| `call core::option::Option<T>::unwrap` | `.unwrap()` |
| `call core::slice::index::SliceIndex` | `slice[a..b]` |
| `call alloc::raw_vec::grow` | `Vec::push` triggering reallocation |
| `call core::fmt::Arguments::new_v1` | `format!()` / `println!()` |
| `call <T as Drop>::drop` | Drop trait method (destructor) |
| `mov rax, [rcx]` then `call [rax+0x18]` | Trait method dispatch |
| `call core::ptr::drop_in_place` | Destructor invocation (monomorphized) |

## Iterator chains

Rust iterators compile to nested loops. `for x in y.filter(pred).map(f)` becomes:
```rust
let mut iter = y.into_iter();
while let Some(v) = iter.next() {
    if pred(v) {
        let mapped = f(v);
        // body
    }
}
```

In disasm, this looks like multiple `call next` instructions with conditionals between them. The function called (`next`) is the iterator's `next` method — monomorphized for the specific iterator type.

Recovering the source level from this is hard. Just identify the iterator state struct and the operations, then describe behavior.

## Common Rust bug patterns to flag

| Pattern | Why it matters |
|---------|----------------|
| `unsafe` block without safety comment | Manual invariant reasoning; review each |
| `mem::forget` of resource-owning type | Bypasses Drop; can leak |
| `unsafe impl Send/Sync` | Hand-asserted thread safety |
| `as` cast (e.g., `i64 as i32`) | Truncation; can panic on overflow only in debug |
| `unwrap()` in non-prototype code | Panic on None/Err; use `?` or `match` |
| `.clone()` in hot path | Allocation; consider borrow or `Cow` |
| `Arc<Mutex<T>>` for read-heavy data | `RwLock` or `Arc<T>` often better |
| `tokio::spawn` without JoinHandle | Detached task; can leak |
| `await` after `?` in async error paths | Cancellation safety — verify future can be safely dropped |

## Async Rust

Async functions are compiled to **state machines**. Each `await` point becomes a state in the machine. The compiled function takes a state argument (`rcx` for Microsoft, `rdx` for System V) and dispatches on it.

To analyze:
1. Find the function (it'll be named `<func>::{closure#0}` if symbols are present, or just be a normal-looking function if stripped)
2. Find the state dispatch (typically a `match` on the state field, which compiles to a jump table)
3. Each state corresponds to a code path between awaits
4. State 0 is the initial entry; state N is after the Nth await

This is hard work. Most Rust RE doesn't go deep into async — just identify the async functions and their await points.

## Recovering struct layouts

Rust structs are laid out sequentially unless `#[repr(C)]` or `#[repr(packed)]`. Anonymous structs from `enum` variants and `#[repr(C)]` ad-hoc structs can confuse this.

Find struct layouts by:
1. Looking at how fields are accessed (`mov rax, [rdi+0x10]` — field at offset 0x10)
2. Looking at Drop impls (they touch every field)
3. Looking at `Debug` / `Display` impls (they read every field)

## Output

After Rust recovery:
```
demo::main (0x401234) — entry, parses args, calls demo::run
demo::run (0x401500) — async fn; state machine with 3 await points (HTTP fetch, parse, write)
demo::Config::parse (0x401a00) — parses CLI args; unwraps on missing required fields (panic at 0x401b50: "missing field `input_path`")
demo::process (0x401c00) — takes &[u8], calls demo::decrypt
demo::decrypt (0x401e00) — uses AES-GCM (S-box at 0x490000); key from demo::Config::key
```

Each function has: address, source-level name (recovered), behavior notes, panic locations if present.
