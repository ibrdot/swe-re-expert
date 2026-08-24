# C++ STL Type Recovery — Reverse Engineering Stripped C++ Binaries

How to recover C++ types (`std::string`, `std::vector`, `std::map`, `std::shared_ptr`, etc.) in a stripped binary. The compiler generates recognizable metadata for C++ even when symbol tables are stripped — RTTI, vtables, exception unwinding tables, and the layout of STL containers themselves carry the type information. This playbook shows how to recover these types and use them to name functions and trace data structures.

This applies to MSVC (`cl.exe`, Windows), GCC (Linux/Mingw), and Clang (Apple, Linux). The metadata formats differ; the recovery techniques are similar.

---

## 1. Why C++ binaries are special

C++ adds several pieces of metadata that C does not have:

1. **Vtables** — virtual function tables, one per class with at least one virtual function. Each vtable is a contiguous array of function pointers, laid out in `.rodata` or `.data.rel.ro`. The order of pointers in a vtable matches the declaration order of the virtual functions.
2. **RTTI (Run-Time Type Information)** — `std::type_info` structures for each polymorphic class, plus `class hierarchy descriptor`, `base class array`, and `base class descriptor` structures. RTTI allows `dynamic_cast` and `typeid`.
3. **Exception unwinding tables** (`.eh_frame` for GCC/Clang, `.pdata` for MSVC) — describe how to unwind the stack when an exception propagates. Each function with unwind info has an entry.
4. **Construction vtables** — for virtual base classes, additional vtables are generated for the construction phase.
5. **Mangled names** — even in stripped binaries, exception unwinding sections may retain mangled names (`_ZNSt6vectorIiSaIiEE9push_backEOi` for `std::vector<int>::push_back(int&&)`).
6. **Type descriptors** — the `type_info` for `std::vector<int, std::allocator<int>>` would appear as a string like `St6vectorIiSaIiEE` (Itanium ABI mangling).

When `strip` is run on a GCC/Clang binary, it removes `.symtab` and `.strtab`. It **does not** remove:
- `.rodata` (contains vtables, RTTI strings)
- `.data.rel.ro` (contains vtables for non-const construction)
- `.eh_frame` (exception unwinding, includes mangled names of personality routines)
- `.gcc_except_table` (exception handling tables with type_info references)

When MSVC strips symbols, it removes the COFF symbol table and CodeView info, but **does not** remove `.rdata` (which holds vtables and RTTI structures).

So even stripped C++ binaries have rich type information recoverable from data sections.

---

## 2. Itanium ABI (GCC, Clang on Linux/macOS) — RTTI structure

The Itanium C++ ABI specifies a standard layout for RTTI. The relevant structures:

### 2.1 The `type_info` object (class type_info)

Each `type_info` is a struct:
```c
class type_info {
    ptr vtable_of_type_info;       // ptr to type_info's own vtable
    ptr name_string;               // ptr to mangled name string
};
```

For class types, the actual type is `__class_type_info` (single inheritance) or `__vmi_class_type_info` (multiple/virtual inheritance). The mangled name is what makes the type identifiable.

### 2.2 The mangled name

A name like `St6vectorIiSaIiEE` decodes to:
- `St` → `std::` (substitution shortcut)
- `6vector` → literal name "vector" of length 6
- `I` → template start
- `i` → `int`
- `Sa` → `std::allocator`
- `IiE` → `std::allocator<int>`
- `E` → end template

Tools:
- `c++filt` — Itanium demangler
- `libcxxabi`'s `__cxa_demangle` — programmatic demangling

### 2.3 Vtable layout (Itanium)

For a class `Derived : public Base` with virtual functions `f1`, `f2` inherited from `Base` and `g1` introduced in `Derived`:

```
vtable_for_Derived:
    [0] 0                       // null (offset to top)
    [1] 0                       // typeinfo offset (single inheritance: 0)
    [2] &typeinfo_for_Derived   // ptr to type_info
    [3] &Derived::f1            // virtual function pointers begin here
    [4] &Derived::f2            // (these may equal &Base::f1 etc. if not overridden)
    [5] &Derived::g1
```

If `Derived` overrides `f2`:
```
    [3] &Base::f1               // inherited
    [4] &Derived::f2            // overridden
    [5] &Derived::g1
```

The 2 header words (`offset_to_top`, `typeinfo_offset`) are part of the standard ABI.

### 2.4 Recovery procedure (Itanium)

1. **Find the type_info name strings**: in `.rodata`, search for the byte patterns of mangled names. Common patterns:
   - `St6vector` → `std::vector`
   - `St3map` → `std::map`
   - `St6string` (older ABI) or `Ss` (newer) → `std::string`
   - `St10shared_ptr` → `std::shared_ptr`
   - `St11unique_ptr` → `std::unique_ptr`
   - `St16initializer_list` → `std::initializer_list`

2. **For each found type_info string**, find its `type_info` struct: scan `.rodata` for `ptr_to_vtable_of_type_info, ptr_to_name_string` patterns.

3. **Find vtables referencing the type_info**: scan `.data.rel.ro` and `.rodata` for a sequence of pointers where the third entry matches a known type_info pointer. That sequence is the vtable for that class.

4. **Identify virtual functions**: the function pointers in slots [3+] of the vtable are virtual functions. Use the type name to give them names like `Derived_vfunc_3_unknown`.

5. **Recover constructor**: the constructor (e.g., `std::vector<int>::vector()`) writes the vtable pointer to `this->vptr`. Find functions that store the vtable address to `[rdi]` (the first arg in System V AMD64 is `this`). These are constructors.

6. **Recover destructors**: similarly, functions that load the vtable pointer from `this` and call the second slot (destructor chain).

### 2.5 Example: `std::vector<int, std::allocator<int>>`

In a stripped GCC-compiled binary, the `.rodata` will contain:
- The string `St6vectorIiSaIiEE` (or `St6vectorIiSaIiEE` if `allocator` uses the `std` shortcut)
- A type_info struct: `{ptr_to_vtable_of_class_type_info, ptr_to_string}`
- A vtable: `{0, 0, ptr_to_type_info, ...vtable_functions...}`

But `std::vector` has no virtual functions, so there's actually **no vtable** — `std::vector`'s methods are not virtual. The recovery here is via the **structure layout** rather than via RTTI.

Hmm — so for STL containers without virtual functions, RTTI is absent. Recovery relies on:
- The structure of the container itself
- The personality routine names (which are kept in `.eh_frame` for exception handling)
- The destructor and constructor function shapes

For `std::vector<T>` specifically:
- Layout: `{ptr_begin, ptr_end, ptr_capacity_end}`
- 3 pointers, each 8 bytes on 64-bit = 24 bytes total
- The constructor sets all three to `nullptr` (or to the stack if it's a `vector` with `stack_storage`)
- `push_back` increases size by 1, reallocates if `ptr_end == ptr_capacity_end`
- The destructor frees the buffer (calls `operator delete` on `ptr_begin`)

Recognize `std::vector<T>` by:
- A 24-byte (or 12-byte on 32-bit) struct passed by pointer as the first argument
- Constructor initializes 3 pointers to `nullptr`
- A method (likely `push_back`) that calls `operator new` (or `operator delete`) on the buffer when `ptr_end == ptr_capacity_end`
- A method (likely `size`) that returns `ptr_end - ptr_begin` (subtraction of two pointers)

### 2.6 Example: `std::string` (libstdc++ SSO)

libstdc++'s `std::string` uses Small String Optimization (SSO):

```c
class basic_string {
    // 64-bit, 32 bytes total
    ptr _M_dataplus._M_p;         // data pointer (8 bytes)
    size_type _M_string_length;   // length (8 bytes)
    union {
        char _M_local_buf[16];    // SSO buffer (16 bytes)
        size_type _M_allocated_capacity; // when heap-allocated
    };
};
```

Total size: 32 bytes. When string length ≤ 15, `_M_p` points to `_M_local_buf` (data is in-place). When length > 15, `_M_p` points to heap memory.

**Detection**:
- 32-byte struct passed by pointer
- Constructor writes the SSO buffer's address into the data pointer
- `c_str()` returns `_M_p` unchanged
- `size()` returns `_M_string_length`
- Destructor calls `operator delete` on `_M_p` if `_M_p != &_M_local_buf` (i.e., not SSO)

MSVC's `std::string` is similar but slightly different layout (uses a union more explicitly with `_Bx`).

### 2.7 Example: `std::map<K, V, Compare, Allocator>`

`std::map` is a Red-Black Tree. The structure:
```c
class map {
    // simplified
    struct _Rb_tree {
        struct _Rb_tree_node_base {
            int         _M_color;          // 0=red, 1=black
            ptr         _M_parent;
            ptr         _M_left;
            ptr         _M_right;
        };
        _Rb_tree_node_base _M_header;
        size_type           _M_node_count;
    };
    // Compare and Allocator are usually empty (EBO)
};
```

Total: 48 bytes on 64-bit (header = 32 bytes with color/pad + node_count = 8 bytes).

**Detection**:
- 48-byte struct
- Constructor writes the header's `_M_parent` and `_M_left` and `_M_right` to itself (sentinel pattern)
- The insert operation does standard RB tree rotations (color flips, left/right rotations)
- The destructor walks the tree in-order and deletes each node

### 2.8 `std::shared_ptr<T>`

```c
class shared_ptr {
    ptr  _M_ptr;          // pointer to managed object
    ptr  _M_refcount;     // pointer to control block
};
// control block layout (libc++):
//   ptr       vtable;       // for shared_count
//   atomic_int strong_count;
//   atomic_int weak_count;
//   ptr       managed_obj;  // sometimes
//   T         custom_deleter; // if present
//   T         allocator;
```

Total size: 16 bytes on 64-bit.

**Detection**:
- 16-byte struct
- Constructor: writes `nullptr` to both pointers (default constructor) or allocates a control block and increments strong_count atomically (`lock inc [rax+8]`)
- Destructor: `lock dec [rax+8]` + `jnz skip_delete` + (if 0) call deleter and free control block

The atomic increment/decrement patterns (`lock inc`/`lock dec` + `jz`/`jnz` checks) are unique to `shared_ptr`.

---

## 3. MSVC ABI (Windows) — RTTI structure

MSVC uses a different RTTI format (CAPI — Common Type Information). The structures:

### 3.1 `_TypeDescriptor`

```c
struct _TypeDescriptor {
    ptr   vtable_of_type_info;       // points to a "type_info" vtable
    ptr   spare;                     // usually 0
    char  name[];                    // mangled name like ".?AVvector@@"
};
```

The MSVC name mangling for `std::vector<int>` is something like `?AVvector@std@@` (with template params expanded).

### 3.2 `_RTTICompleteObjectLocator`

```c
struct _RTTICompleteObjectLocator {
    unsigned  signature;            // 0x00000000 for x86, 0x00000001 for x64
    unsigned  offset;                // offset of this vtable in complete object
    unsigned  cdOffset;              // constructor displacement offset
    ptr       pTypeDescriptor;       // -> _TypeDescriptor
    ptr       pClassDescriptor;      // -> _RTTIClassHierarchyDescriptor
    ptr       pSelf;                 // -> self (x64 only; for relative addressing)
};
```

### 3.3 Vtable (MSVC)

The MSVC vtable has a different layout:
```
vtable_for_Derived:
    [-1]  ptr_to_RTTICompleteObjectLocator   // RTTI locator, BEFORE the vtable[0]
    [0]   &Derived::f1
    [1]   &Derived::f2
    [2]   &Derived::g1
```

The first entry of the vtable (at offset 0) is the first virtual function pointer. The entry at offset `-8` is the RTTI locator pointer.

### 3.4 Recovery procedure (MSVC)

1. **Find type descriptor strings**: in `.rdata`, search for `.?A` patterns (MSVC's class type mangling). Examples:
   - `.?AV?$vector@HV?$allocator@H@std@@@std@@` → `std::vector<int, std::allocator<int>>`
   - `.?AV?$basic_string@...@std@@` → `std::string`
   - `.?AV?$map@...@std@@` → `std::map`
   - `.?AU?$shared_ptr@...@std@@` → `std::shared_ptr`

2. **Find the `_RTTICompleteObjectLocator`**: scan `.rdata` for entries whose `pTypeDescriptor` field matches a type descriptor address.

3. **Find vtables**: scan `.rdata` for entries that point to an RTTICompleteObjectLocator (at offset `-8` of a vtable). The next bytes are the virtual function pointers.

4. **For each vtable found, name the virtual functions**: `Class_vfunc_0`, `Class_vfunc_1`, etc. Then look at what each virtual function does to refine names (e.g., if `vfunc_0` returns a string, it's likely `Class::name()` or `Class::what()` for exception classes).

---

## 4. Exception unwinding — the mangled-name cache

For GCC/Clang, `.eh_frame` contains Frame Description Entries (FDEs) that describe how to unwind each function. Each function has an associated personality routine (often `__gxx_personality_v0` for C++ exceptions).

The `.gcc_except_table` section contains:
- **LSDA** (Language-Specific Data Area) for each function — includes pointers to type_info objects for catch clauses
- The type_info pointers are mangled names

So even if `.symtab` is stripped, the LSDA still references type_info objects in `.rodata` which carry the mangled name. **A binary's catch clauses tell you the types it works with.**

### 4.1 Extracting type_info from LSDA

```bash
# Use readelf to dump exception tables
readelf -x .gcc_except_table target
# Look for byte sequences that look like pointers into .rodata
# Each pointer references a type_info object whose name string contains the mangled name
```

The mangled name string is plain text in `.rodata`. So even in a stripped binary, you can recover:
- The exception types used (`St9exception`, `St13runtime_error`, `St12out_of_range`, etc.)
- The classes used as exception types
- The functions that throw exceptions (because their LSDA references them)

### 4.2 MSVC equivalent — `.pdata` + `.xdata`

MSVC stores exception info as:
- `.pdata`: array of `RUNTIME_FUNCTION` entries (3 32-bit fields: BeginAddress, EndAddress, UnwindInfoAddress)
- `.xdata`: unwind info tables; C++ exception info is in the `__CxxFrameHandler3` callback

The `.rdata` section contains `CxxThrowType` structures with type_info references.

---

## 5. Constructors, destructors, and the "complete vs. deleting" pattern

C++ compilers emit two destructors for each class:
- The **complete destructor** (e.g., `_ZN5ClassD1Ev` = `Class::~Class()` in Itanium, freeing all bases)
- The **deleting destructor** (e.g., `_ZN5ClassD0Ev` = `Class::~Class() + operator delete(this)`, called when `delete obj` is invoked)

The two destructors share most code; the deleting variant just calls the complete variant and then `operator delete`. In a stripped binary, you can recognize them as a pair: one function (D2/D1 — base/complete object destructor) called by another (D0 — deleting destructor) which then calls `operator delete`.

Similarly, constructors come in three flavors:
- Complete constructor (D1 in Itanium, calls all base constructors)
- Base constructor (D2 in Itanium, called by D1)
- Allocating constructor (D0 in Itanium, calls D1 + operator new) — only for classes with `new` operators

Recognizing these patterns helps name functions. In a stripped binary, you can identify a constructor by:
- It writes a vtable address to `[rdi]` (or `[ecx]` in MSVC `__thiscall`)
- It calls other constructors (base classes)
- It doesn't return a value (or returns `this` unchanged)
- It's called from many sites (object instantiation)

---

## 6. The template instantiation signature

A class template like `std::vector<int>` and `std::vector<std::string>` share most code but the compiler emits separate copies. The two copies will be very similar in structure but differ in:
- The element size (4 bytes for `int`, 32 bytes for `std::string`)
- The element constructor/destructor called inside `push_back` / `vector()` / `~vector()`

You can identify which instantiation a function belongs to by:
- Look at the element type's constructor/destructor that's called inside
- Look at the multiplier used in `i * sizeof(T)` (e.g., `imul rax, 4` for `int`, `imul rax, 32` for `std::string`)

---

## 7. Personality routines and `operator new` / `operator delete`

C++ programs that allocate dynamically will call `operator new` and `operator delete`. These are:
- In libstdc++ (Linux): `_Znwm` / `_Znam` for `operator new(size_t)` and `operator new[](size_t)` (array form)
- In libc++ (macOS): same mangling
- In MSVC: `??2@YAPEAX_K@Z` for `operator new(unsigned __int64)` and `??_V@YAXPEAX@Z` for `operator delete(void*)`

In stripped binaries, these may be available as PLT entries (`call qword ptr [rip + offset]` → resolves to `operator new`). If the PLT stub is stripped, recognize `operator new` by:
- It calls `malloc` underneath
- The caller typically passes a constant size argument (the size of the type)
- The return is checked for null; if null, it calls `__cxa_throw_bad_alloc` (libstdc++) or throws `std::bad_alloc`

`operator delete` is recognized by:
- It calls `free` underneath
- The argument is the pointer that was previously returned by `operator new`
- It's typically called from destructors and the deleting destructor

By tracing `operator new` calls back to the call site, you can find object instantiation points and infer the class size (from the size argument).

---

## 8. STL container size lookup table (64-bit)

A quick reference for STL container sizes — useful for identifying which container a function manipulates:

| Container | libstdc++ size | libc++ size | MSVC size |
|---|---|---|---|
| `std::string` | 32 | 24 | 32 |
| `std::wstring` | 32 | 24 | 32 |
| `std::vector<T>` | 24 | 24 | 24 |
| `std::list<T>` | 16 | 16 | 16 |
| `std::deque<T>` | 80 | 80 | 56 |
| `std::forward_list<T>` | 8 | 8 | 8 |
| `std::array<T, N>` | N * sizeof(T) | same | same |
| `std::map<K,V>` | 48 | 48 | 16 (just header) + node |
| `std::set<K>` | 48 | 48 | 16 + node |
| `std::unordered_map<K,V>` | 56 | 56 | varies |
| `std::unordered_set<K>` | 56 | 56 | varies |
| `std::stack<T>` (adapts deque) | 80 | 80 | 56 |
| `std::queue<T>` (adapts deque) | 80 | 80 | 56 |
| `std::priority_queue<T>` | 80 + 24 | 80 + 24 | 56 + 8 |
| `std::shared_ptr<T>` | 16 | 16 | 16 |
| `std::unique_ptr<T>` | 8 | 8 | 8 |
| `std::weak_ptr<T>` | 16 | 16 | 16 |
| `std::function<Sig>` | 32 | 48 | 64 |
| `std::any` | 16 | 24 | 24 |
| `std::optional<T>` | sizeof(T) + 1 (padded) | same | same |
| `std::variant<Ts...>` | max(sizeof(Ts)) + 1 (padded) | same | same |
| `std::tuple<Ts...>` | sum (with padding) | same | same |

When a function takes a 32-byte struct by pointer, you can guess `std::string`. A 24-byte struct by pointer → likely `std::vector`. A 48-byte struct → likely `std::map` or `std::set`. Combined with constructor behavior, this is high-confidence identification.

---

## 9. Workflow — the C++ recovery pipeline

Given a stripped C++ binary:

1. **Identify it's C++**: check for the presence of `.gcc_except_table` (Itanium), `.pdata`+`.xdata` (MSVC), or `__gxx_personality_v0` / `__CxxFrameHandler3` references.

2. **Extract type_info strings**: scan `.rodata` for mangled name strings (Itanium: `St`, `_Z`, `N`, patterns; MSVC: `.?A` patterns). Run each through `c++filt` (Itanium) or `undname.exe` (MSVC) to demangle.

3. **Map type_info objects to vtables**: for each type_info, find vtables whose RTTI locator points to it.

4. **Recover virtual functions**: name them by class name (e.g., `vector_int_push_back` if it's the third slot in `vector`'s vtable; though `std::vector` has no virtual functions, classes derived from it might).

5. **Identify constructors and destructors**: scan for functions that write vtable pointers to `[this]`. Pair them as complete/deleting destructors.

6. **Recognize STL container access patterns**: based on container sizes (Section 8) and access patterns (constructor initializing 3 pointers to nullptr = `std::vector`; atomic increment + `operator new` = `std::shared_ptr`; etc.).

7. **Recover element types of templates**: look at element-size multipliers in member functions (`imul rax, 4` for `int`, `imul rax, 32` for `std::string`).

8. **Use exception unwinding tables to discover all thrown exception types**: this tells you what error types the binary uses.

9. **Report**: include a section "C++ type recovery" with the recovered class hierarchy, vtable layouts, and identified STL container instantiations. Limitations: list the types that couldn't be demangled (rare without context) or that you couldn't match to a vtable.

---

## 10. Common pitfalls

1. **Multiple ABIs in one binary**: a macOS binary may have both Itanium (C++) and Swift runtimes intermixed. Don't conflate the two.

2. **PIE binaries on Linux**: relative addressing makes pointer-matching trickier. Use `objdump -d -R` or `readelf -r` to resolve relocations first.

3. **C++ exception tables in stripped binaries**: stripping removes `.symtab` and `.strtab`, but `.gcc_except_table` is preserved because the runtime needs it. **Always check `.gcc_except_table` for type info**.

4. **Type-info inlining**: small `type_info` objects might be inlined into other functions; the name string in `.rodata` is the most stable reference.

5. **Old vs new libstdc++ ABI**: pre-GCC 5 uses a different `std::string` layout (`_M_p` only). Post-GCC 5 uses SSO. Detect by checking the size: if the string is 8 bytes (just a pointer), it's the old ABI; if 32 bytes, the new ABI.

6. **`__cxa_demangle` quirks**: some mangled names include vendor extensions (`U` prefixes for vendor extensions). `c++filt` may not decode these; fall back to manual parsing.

---

## 11. Output

For every C++ binary analyzed, the report should include:

1. **Confirmed C++ ABI** (Itanium / MSVC / other)
2. **Class hierarchy recovered** — list of classes with their names, sizes, base classes (if multiple inheritance detected from `__vmi_class_type_info`)
3. **Vtable layout** — for each class with virtual functions, the function pointer table with proposed names
4. **STL container instantiations** — `std::vector<int>`, `std::map<std::string, std::vector<int>>`, etc., with how they were identified (size + access pattern)
5. **Constructor / destructor pairs** — for each class, the constructor and destructor entry points with how they were identified
6. **Exception types used** — from the LSDA / `.pdata` analysis
7. **Limitations** — which types couldn't be identified, why
8. **Recommended next step** — typically "feed recovered names back into IDA/Ghidra to enable deeper analysis of the now-renamed functions"
