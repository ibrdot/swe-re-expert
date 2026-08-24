# Rust Binary Recovery — Reversing Stripped Rust Binaries

Rust binaries strip most symbols by default, but panic strings, demangled symbols, and trait vtables give enough hooks to recover logic.

## Why Rust binaries are different

- **Heavy monomorphization** — each generic instantiation is a separate function
- **Trait objects use vtables** — similar to C++ virtual classes
- **Panic strings leak source info** — `called Option::unwrap() on a None value` etc.
- **Mangling is Itanium-style with `_R` prefix** — different from C++'s `_Z`
- **Zero-sized types (ZST)** — passed as no arg; can confuse arg-count analysis
- **Iterator chains** — compile to nested loops, hard to read
- **Async state machines** — each `await` becomes a state in a generated state machine
- **Drop glue everywhere** — even simple scope exits call `drop_in_place<T>` for any owned value

## The 6-step Rust recovery loop

1. **Confirm Rust** — `.rustc` section, panic strings, `__rust_*` symbols
2. **Recover panic strings** — they're source-level breadcrumbs
3. **Demangle symbols** — `_R...` -> `module::function`
4. **Find vtables** — trait object dispatch uses them
5. **Identify monomorphized variants** — same source, different types
6. **Map iterator chains** — `for x in y.filter().map()` compiles to nested loops

## Confirming Rust

```bash
# Section check (best single signal)
objdump -h <target> | grep -E "rustc"

# Panic strings (always present unless panic=abort + stripped)
strings -a <target> | grep -E "called .+ on a|panic|index out of bounds"
strings -a <target> | grep "core::panicking"

# Allocation symbols (present in nearly every Rust binary)
strings -a <target> | grep -E "__rust_alloc|__rust_realloc|__rust_dealloc"

# Mangling prefix
nm <target> 2>/dev/null | grep "^_R" | head

# Panic-related runtime strings
strings -a <target> | grep -E "byte index .+ is out of bounds|capacity overflow"
```

If `.rustc` exists or you see `core::panicking::panic` — it's Rust.

### Discriminating Rust vs C++ (both use Itanium ABI)

| Signal | Rust | C++ |
|--------|------|-----|
| Mangling prefix | `_R` | `_Z` |
| Section | `.rustc` | (none equivalent) |
| Allocation symbols | `__rust_alloc`, `__rust_dealloc` | `operator new`, `operator delete` |
| Panic strings | `core::panicking::panic` | (none equivalent) |
| Trait dispatch vtable layout | drop_in_place + size + align + methods | methods only (no size/align) |
| Static initializer | `<_..>::{constant#N}` | `_GLOBAL__sub_I_..` |

## Panic strings as source breadcrumbs

Rust panic strings are literal source-level text. They leak:
- Module paths: `core::slice::index::slice_index_positions_failed`
- Function context: `called Option::unwrap() on a None value`
- Source info: `byte index {byte} is out of bounds of {bytes}`

Map each panic string to a likely source location. The presence of `core::panicking::panic` calls in a function tells you that function does something risky (unwrap, indexing, arithmetic with overflow check).

### Panic string -> source behavior mapping

| Panic string | Source-level operation |
|--------------|-------------------------|
| `called Option::unwrap() on a None value` | `.unwrap()` on None Option |
| `called Result::unwrap() on an Err value` | `.unwrap()` on Err Result |
| `called Option::expect() on a None value` with custom msg | `.expect("msg")` |
| `index out of bounds: the len is N but the index is M` | `slice[M]` or `array[M]` with M >= len |
| `capacity overflow` | `Vec::push` or similar growth overflow |
| `attempt to add with overflow` | `a + b` in debug build with overflow |
| `attempt to subtract with overflow` | `a - b` underflow in debug |
| `attempt to shift left with overflow` | `a << b` with b >= type width |
| `internal error: entered unreachable code` | `unreachable!()` macro |
| `not yet implemented` | `todo!()` macro |
| `not implemented` | `unimplemented!()` macro |
| `Ran out of free stack space` | Stack overflow (heavy recursion) |

These are diagnostic — they tell you what operations the source did, even after stripping.

## Demangling

Rust uses Itanium ABI mangling with `_R` prefix (vs C++'s `_Z`).

Examples:
| Mangled | Demangled |
|---------|-----------|
| `_RNvCs42Nns_4demo3foo` | `demo::foo` |
| `_RNvNtCs1234_4core3str5charsE` | `<core::str::chars>` |
| `_RINvNtCs_4core5slice4iterB2_` | `core::slice::iter::...` |
| `_RINvNtNtCsb_4core3ops8function4callv...` | `core::ops::function::call::...` (Fn::call impl) |
| `_RNvNtNtNtCs...4core3ptr13drop_in_place...E` | `core::ptr::drop_in_place::<...>` |

Demangle with:
```bash
rustfilt <mangled>          # CLI tool
# Or Python:
python3 -c "import rust_demangle; print(rust_demangle.demangle('_R...'))"
# Or via the Rust toolchain:
rustc --crate-name=_ --print=... <(echo "_R...") 2>&1 | head
```

### Mangling structure (so you can read it manually)

```
_R              # Rust prefix
N               # Nesting marker (Nested name)
v               #... discriminator encoding (e.g., vCs42Nns_)
t Cs42Nns_      # crate-id-prefixed path component
4 demo          # length-prefixed name ('demo', 4 chars)
3 foo           # length-prefixed name ('foo', 3 chars)
```

When `rustfilt` is unavailable, you can at least extract path components by reading length-prefixed names from the mangled string.

## Rust calling convention

Rust uses the platform's standard C ABI:
- **Linux x86-64**: System V AMD64 (rdi, rsi, rdx, rcx, r8, r9)
- **Windows x86-64**: Microsoft x64 (rcx, rdx, r8, r9)
- **ARM64**: AAPCS64 (x0-x7)

Same as C. The differences are in how the compiler uses the convention, not the convention itself.

Key Rust-specific quirks:
- **ZST (zero-sized types)** are passed as no argument. If you see a function call with fewer args than expected, one might be a ZST.
- **Slices** are passed as `(ptr, len)` — two args, not one.
- **Strings** (`&str`) are also `(ptr, len)`.
- **Option<T>** is typically passed as the value + a discriminant flag (in a separate register or packed with the value depending on the type).
- **Result<T, E>** similar — value + discriminant.
- **`&dyn Trait`** (trait object) is `(data_ptr, vtable_ptr)` — two args.
- **`Box<T>`** is just a pointer (the data is on the heap).
- **`Vec<T>`** is `(ptr, len, cap)` — three fields.
- **`String`** is the same as `Vec<u8>` — `(ptr, len, cap)`.
- **Closures** compile to anonymous structs holding captured variables; the closure's `FnOnce::call_once` takes the struct by value (or by ref, depending on capture mode).

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

### Vtable layout vs C++

| Field | Rust vtable | C++ vtable |
|-------|-------------|------------|
| Offset 0x0 | drop_in_place<T> | first virtual method |
| Offset 0x8 | size | second virtual method |
| Offset 0x10 | alignment | third virtual method |
| Offset 0x18 | first method | ... |
| Offset 0x20 | second method | ... |

This is the easiest way to distinguish a Rust trait-object vtable from a C++ vtable when looking at `.data.rel.ro` contents.

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
| `call core::str::Convert<Vec_u8>>` | `String::from_utf8` / `str::from_utf8` |
| `call <[u8] as Index>::index` | `slice[i]` on `&[u8]` |
| `call core::slice::iter::Iterator::next` | `for x in y` or `y.iter().next()` |
| `call alloc::alloc::ExchangeMalloc` | `Box::new` / `Vec::new` heap allocation |
| `call std::sys::thread::Thread::new` | `std::thread::spawn` |
| `call tokio::task::*::spawn` | `tokio::spawn` (async runtime) |

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

### Iterator chain -> source reconstruction

The chain `y.into_iter().filter(pred).map(f).collect::<Vec<_>>()` compiles to:

```rust
let iter1 = y.into_iter();
let iter2 = Filter { iter: iter1, pred };     // struct
let iter3 = Map { iter: iter2, f };            // struct
let mut out = Vec::new();
while let Some(v) = iter3.next() {              // calls Map::next -> Filter::next -> iter1::next
    Vec::push(&mut out, v);
}
```

So in disasm you'll see `call <Map as Iterator>::next` which internally calls `<Filter as Iterator>::next` which calls `<InputIter as Iterator>::next`. Identify the iterator state struct (often on the stack as a series of pointers + closures) to recover the chain.

### Common iterator types in disasm

| Disasm call | Source-level iterator |
|-------------|-------------------------|
| `core::slice::Iter::next` | `slice.iter()` or `&slice.into_iter()` |
| `core::slice::IterMut::next` | `slice.iter_mut()` |
| `core::slice::Chunks::next` | `slice.chunks(N)` |
| `core::slice::Windows::next` | `slice.windows(N)` |
| `core::iter::Filter::next` | `.filter(pred)` |
| `core::iter::Map::next` | `.map(f)` |
| `core::iter::Enumerate::next` | `.enumerate()` |
| `core::iter::Zip::next` | `.zip(other)` |
| `core::iter::FlatMap::next` | `.flat_map(f)` |
| `core::ops::Range::next` | `range.start..range.end` |
| `core::ops::RangeInclusive::next` | `range.start..=range.end` |
| `std::collections::HashMap<K,V>::Iter::next` | `hashmap.iter()` |
| `std::collections::HashMap<K,V>::Keys::next` | `hashmap.keys()` |
| `std::collections::HashMap<K,V>::Values::next` | `hashmap.values()` |

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
| `unwrap_or` with side-effecting default | Default evaluated eagerly; use `unwrap_or_else` |
| `Box<dyn Error>` losing type info | Custom error enum implementing `Error` is better |
| `as` cast between `*const T` and `*mut T` | Aliasing UB; use `UnsafeCell` or proper interior mutability |
| `static mut` for mutable global | UB in multi-threaded; use `Lazy`/`OnceLock` or `Mutex` |
| `Vec<T>::with_capacity(N)` followed by N `push`es | Often fine, but check N isn't user-controlled (DoS) |
| `await` across `std::mem::replace` | Borrow held across await; can deadlock |

## Async Rust

Async functions are compiled to **state machines**. Each `await` point becomes a state in the machine. The compiled function takes a state argument (`rcx` for Microsoft, `rdx` for System V) and dispatches on it.

To analyze:
1. Find the function (it'll be named `<func>::{closure#0}` if symbols are present, or just be a normal-looking function if stripped)
2. Find the state dispatch (typically a `match` on the state field, which compiles to a jump table)
3. Each state corresponds to a code path between awaits
4. State 0 is the initial entry; state N is after the Nth await

This is hard work. Most Rust RE doesn't go deep into async — just identify the async functions and their await points.

### Async function pattern

```asm
async_fn:
    push rbp
    ; ... prologue
    mov rax, [rdi+0x0]      ; load state field
    cmp rax, 0x4            ; number of states
    ja .default             ; safety
    jmp [QWORD PTR .LJUMP_TABLE + rax*8]
.LJUMP_TABLE:
    .quad .state0
    .quad .state1
    .quad .state2
    .quad .state3
    .quad .state4
.state0:
    ; ... initial code, before first await
.state1:
    ; ... after first await resumes
```

The number of states = number of await points + 1 (for the initial state).

## Recovering struct layouts

Rust structs are laid out sequentially unless `#[repr(C)]` or `#[repr(packed)]`. Anonymous structs from `enum` variants and `#[repr(C)]` ad-hoc structs can confuse this.

Find struct layouts by:
1. Looking at how fields are accessed (`mov rax, [rdi+0x10]` — field at offset 0x10)
2. Looking at Drop impls (they touch every field)
3. Looking at `Debug` / `Display` impls (they read every field)
4. Looking at the `PartialEq` impl (it compares every field)
5. Looking at `Clone` impl (it clones every field)

The order of field accesses in Drop tells you the layout order (Rust drops fields in declaration order).

### Enum layout

Rust enums are a discriminant + payload. The discriminant size depends on the variant count:
- Up to 255 variants: 1 byte discriminant
- 256-65535: 2 bytes
- 65536-4B: 4 bytes

The discriminant is at offset 0 of the enum (for the common case). Payload fields follow.

For `Option<&T>` and similar niche-optimized enums, the discriminant is encoded in the pointer itself (null = None). This is called "niche optimization" — common cases:
- `Option<&T>`: null pointer = None, valid pointer = Some
- `Option<Box<T>>`: same
- `Option<NonZeroU32>`: 0 = None, nonzero = Some

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

## Verification checklist — for the agent before finalizing Rust RE report

- [ ] Rust confirmed via `.rustc` section OR `core::panicking` strings OR `_R` mangling
- [ ] Panic strings extracted and mapped to source-level operations
- [ ] All `_R` symbols demangled (use `rustfilt` or `rust_demangle`)
- [ ] Trait-object vtables identified, with concrete types recovered where possible
- [ ] Async functions identified (look for jump-table state dispatch)
- [ ] Monomorphized variants grouped (same source name, different type params)
- [ ] Iterator chains identified (look for nested `::next` calls)
- [ ] Drop / DropInPlace calls mapped to source-level destructors
- [ ] Allocation patterns identified (`__rust_alloc`, `__rust_realloc`, `__rust_dealloc`)
- [ ] Each function's calling convention documented (args = which registers)
- [ ] Panic locations cited with offset and the panic string
- [ ] Unsafe blocks identified if symbols present (search for `unsafe` in symbol names or known patterns)
- [ ] Cross-references to `re-playbooks/stl-recovery.md` for shared vtable insights
- [ ] Cross-references to `re-playbooks/crypto-identification.md` if Rust crypto crates (e.g., `aes`, `sha2`, `ring`) detected

If any checkbox is unchecked, the Rust RE report is incomplete — go back and finish the missing layer before submission.
