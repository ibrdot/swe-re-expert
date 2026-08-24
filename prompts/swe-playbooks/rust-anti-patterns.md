# Rust Anti-Patterns

Rust's type system prevents many bugs by design, but the patterns below still cause real issues. The compiler catches the obvious ones — these are the subtler ones.

## P0 — Security / correctness

### `unsafe` without safety comment

```rust
// P0 — manual invariant reasoning, unreviewed
unsafe {
    *std::ptr::null_mut()  // boom
}

// Fix: every unsafe block must have a safety comment
// SAFETY: ptr is non-null because we just allocated it.
unsafe {
    *ptr
}
```

Rule: every `unsafe` block needs a `// SAFETY:` comment explaining why the operation is sound.

### `unsafe impl Send/Sync`

```rust
// P0 — hand-asserted thread safety, often wrong
unsafe impl Send for MyType {}
unsafe impl Sync for MyType {}

// Fix: verify the type is actually Send/Sync; document the reasoning
// Most types are Send/Sync by default if their fields are.
// Custom impl is only needed for types with raw pointers, FFI, etc.
```

### `mem::forget` of resource-owning type

```rust
// P0 — bypasses Drop, can leak resources (file handles, locks, etc.)
std::mem::forget(my_file);

// Fix: let the value drop normally
// Or use ManuallyDrop if you really need to take ownership of the resource
```

### `as` cast for security-sensitive sizes

```rust
// P0 — silent truncation, can cause buffer overflow
let size: usize = user_input;
let buf = vec![0u8; size as u8];  // truncates to 0-255; large size silently becomes small

// Fix: use try_from / try_into
let size: u8 = u8::try_from(user_input).map_err(|_| Overflow)?;
```

### `unwrap()` in production code

```rust
// P0/P1 — panics on None/Err; depends on call site
fn process(input: Option<T>) -> T {
    input.unwrap()  // panics if None
}

// Fix: use ? or explicit match
fn process(input: Option<T>) -> Result<T, Error> {
    input.ok_or(Error::Missing)
}
```

Exception: `unwrap()` is OK in:
- Tests
- Prototyping
- After `if let Some(x) = ... { /* unwrap here is provably safe */ }`

## P1 — Correctness / concurrency

### `Arc<Mutex<T>>` for read-heavy data

```rust
// P1 — readers block each other
let data = Arc::new(Mutex::new(big_map));

// Fix: RwLock allows concurrent reads
let data = Arc::new(RwLock::new(big_map));
// Or, if mostly read-only: Arc<T> (immutable)
```

### `tokio::spawn` without `JoinHandle` management

```rust
// P1 — detached task, can leak
tokio::spawn(async {
    do_work().await;
});

// Fix: track the handle, or use JoinSet
let handle = tokio::spawn(async {
    do_work().await;
});
handle.await.expect("task failed");

// Or for many tasks:
let mut set = tokio::task::JoinSet::new();
for item in items {
    set.spawn(async move { process(item).await });
}
while let Some(res) = set.join_next().await { /* ... */ }
```

### `await` after `?` in async error paths

```rust
// P1 — cancellation safety; if the future is dropped mid-await, partial state
async fn process() -> Result<(), Error> {
    let data = fetch().await?;  // ? maps error
    save(data).await?;          // if cancelled here, partial state
    Ok(())
}

// Fix: ensure each await point is cancellation-safe, or use scopeguard / defer
async fn process() -> Result<(), Error> {
    let data = fetch().await?;
    let _guard = scopeguard::guard((), |_| {
        // cleanup if dropped
    });
    save(data).await?;
    Ok(())
}
```

### Blocking call inside async function

```rust
// P1 — blocks the executor thread
async fn fetch() -> String {
    std::thread::sleep(Duration::from_secs(5));  // blocks!
    "data".to_string()
}

// Fix: use async sleep, or offload to blocking thread
async fn fetch() -> String {
    tokio::time::sleep(Duration::from_secs(5)).await;
    "data".to_string()
}

// Or:
async fn fetch() -> String {
    tokio::task::spawn_blocking(|| {
        std::thread::sleep(Duration::from_secs(5));
        "data".to_string()
    }).await.unwrap()
}
```

### `std::sync::Mutex` in async code

```rust
// P1 — long-held std Mutex can block the async runtime
async fn process(state: Arc<std::sync::Mutex<State>>) {
    let lock = state.lock().unwrap();
    do_async_work(&lock).await;  // holding the lock across await — bad!
}

// Fix: use tokio::sync::Mutex (or restructure to not hold across await)
async fn process(state: Arc<tokio::sync::Mutex<State>>) {
    let mut lock = state.lock().await;
    do_async_work(&lock).await;
}
// Or release before await:
async fn process(state: Arc<std::sync::Mutex<State>>) {
    let data = {
        let lock = state.lock().unwrap();
        lock.clone()
    };
    do_async_work(&data).await;
}
```

### Unhandled `Result`

```rust
// P1 — silent failure
fn process() -> Result<(), Error> {
    fs::write("file", data)?;  // ok
    fs::write("other", data);   // P1 — Result ignored
    Ok(())
}

// Fix: handle, propagate, or explicitly document
fn process() -> Result<(), Error> {
    fs::write("file", data)?;
    let _ = fs::write("other", data);  // explicitly ignored
    Ok(())
}
```

### `Box<dyn Trait>` where generics would do

```rust
// P1 — dynamic dispatch + heap alloc + loses inlining
fn sum(values: Vec<Box<dyn Addable>>) -> i64 {
    values.iter().map(|v| v.value()).sum()
}

// Fix: use generics
fn sum<T: Addable>(values: Vec<T>) -> i64 {
    values.iter().map(|v| v.value()).sum()
}
// Or use impl Trait
fn sum(values: impl IntoIterator<Item = impl Addable>) -> i64 {
    values.into_iter().map(|v| v.value()).sum()
}
```

## P2 — Maintainability

### `.clone()` in hot path

```rust
// P2 — unnecessary allocation
fn process(items: Vec<String>) -> Vec<String> {
    items.iter().map(|s| s.clone().to_uppercase()).collect()
    //                          ^^^^^^^^^^^ unnecessary
}

// Fix: use references where possible
fn process(items: Vec<String>) -> Vec<String> {
    items.iter().map(|s| s.to_uppercase()).collect()
}
// Or use Cow<str> if sometimes owned, sometimes borrowed
```

### God module / long file

```rust
// P2 — single file with 10+ types and 1000+ LOC
// (e.g., models.rs contains User, Order, Payment, Email, ...)

// Fix: split by domain — models/user.rs, models/order.rs, etc.
```

### Excessive type parameters

```rust
// P2 — combinatorial explosion of generic instantiations, slow compiles
fn process<T, U, V, W>(a: T, b: U, c: V, d: W)
where T: ..., U: ..., V: ..., W: ...,
      T::Item: ..., U::Item: ..., ...

// Fix: use trait objects if monomorphization isn't needed, or split function
```

### Manual implementation of stdlib traits

```rust
// P2 — manual Debug impl
impl std::fmt::Debug for MyType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MyType({})", self.field)
    }
}

// Fix: use #[derive(Debug)]
#[derive(Debug)]
struct MyType {
    field: i32,
}
```

### Manual implementations of common patterns

```rust
// P2 — manual new function
struct User { name: String }
impl User {
    fn new(name: String) -> Self {
        Self { name }
    }
}

// Fix: often not needed — use struct literal or Default
struct User { name: String }
// At call site:
let u = User { name: "foo".to_string() };

// Or derive Default + use builder if many fields:
#[derive(Default)]
struct User {
    name: String,
    age: u32,
}
let u = User { name: "foo".to_string(), ..Default::default() };
```

### `String` where `&str` would do

```rust
// P2 — unnecessary allocation
fn greet(name: String) -> String {
    format!("Hello, {}", name)
}

// Fix: accept &str
fn greet(name: &str) -> String {
    format!("Hello, {}", name)
}
```

### `Vec<T>` where iterator would do

```rust
// P2 — allocates unnecessary intermediate
fn process(items: Vec<String>) -> Vec<String> {
    let filtered: Vec<String> = items.into_iter().filter(|s| s.len() > 3).collect();
    let upper: Vec<String> = filtered.into_iter().map(|s| s.to_uppercase()).collect();
    upper
}

// Fix: chain iterators, collect once
fn process(items: Vec<String>) -> Vec<String> {
    items.into_iter()
        .filter(|s| s.len() > 3)
        .map(|s| s.to_uppercase())
        .collect()
}
```

### Tests with `unwrap()` everywhere

```rust
// P2 — panic on first failure, hard to debug
#[test]
fn test_user() {
    let u = create_user().unwrap();
    let id = u.id;
    let name = u.name.unwrap();
    assert_eq!(name, "Alice");
}

// Fix: use ? in test functions (Rust 1.0+ supports Result return)
#[test]
fn test_user() -> Result<(), Error> {
    let u = create_user()?;
    let name = u.name.ok_or(Error::MissingName)?;
    assert_eq!(name, "Alice");
    Ok(())
}
```

## P3 — Style

- Long parameter lists (5+ args)
- Inconsistent naming (snake_case vs camelCase mix — should be all snake_case in Rust)
- Public items without doc comments
- Missing `#[must_use]` on functions returning important values
- Using `Vec<Box<T>>` where `Vec<T>` would work
- Manual implementations of common derives

These usually get caught by `clippy`. Don't review manually.

## The "modern Rust" checklist

For modernization (each needs a concrete defect to justify):

- [ ] Edition 2024 (free upgrades for most code)
- [ ] `let-else` (replaces many `if let Some(...) else return`)
- [ ] `let-chains` (cleaner conditionals)
- [ ] `async fn` in traits (removes `async_trait` crate dep)
- [ ] `Result::Err` inspection (`if let Err(e) = ...` over `match` with one arm)
- [ ] `clippy::pedantic` lints enabled in CI
- [ ] `cargo-miri` for unsafe verification
- [ ] `cargo-audit` for dependency CVEs
- [ ] `cargo-udeps` for unused deps

## Tool reference

```bash
# Linting — catches most P2/P3 findings
cargo clippy --all-targets -- -W clippy::pedantic

# Format
cargo fmt

# Test with coverage
cargo tarpaulin
# Or:
cargo llvm-cov

# Find unused dependencies
cargo udeps

# Audit dependencies for CVEs
cargo audit

# Memory safety in unsafe code
cargo miri test

# Documentation
cargo doc --open
# Ensure `cargo doc` produces no warnings

# Performance benchmarking
cargo bench
# Or with criterion: cargo bench --bench <name>
```

Use these in CI. `clippy` catches most of the findings in this file automatically.
