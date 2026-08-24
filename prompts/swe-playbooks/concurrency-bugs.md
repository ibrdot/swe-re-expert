# Concurrency Bugs — Patterns, Detection, and Auditing

How to find race conditions, deadlocks, atomicity violations, livelocks, and other concurrency bugs in multi-threaded/multi-process code across Python (`asyncio`, `threading`, `multiprocessing`), Go (`goroutines`, `channels`, `select`), Rust (`std::sync`, `tokio`, `async`), and C++ (`std::thread`, `std::async`, `pthreads`, `std::atomic`).

This playbook focuses on **the patterns** — what a concurrency bug looks like at the source/disassembly level, what its consequence is, and what the bounded fix is. Most concurrency bugs have a small bounded fix once identified; the hard part is identification.

---

## 1. The seven bug classes

Every concurrency bug falls into one of these seven categories:

| Class | One-line description | Consequence | Detection difficulty |
|---|---|---|---|
| **Race condition** | Two threads access shared state without synchronization; at least one writes | Data corruption, inconsistent state, occasional crashes | Medium-Hard (need to identify shared state + access pattern) |
| **Atomicity violation** | Operation assumed atomic but actually interruptible | Lost updates, double-increment, double-free | Medium (look for compound operations on shared state) |
| **Deadlock** | Circular wait between locks | Process hang, watchdog timeout | Easy (lock acquisition order analysis) |
| **Livelock** | Threads repeatedly release/reacquire locks, no forward progress | Process appears running but makes no progress | Hard (no hang, just no progress) |
| **Starvation** | One thread perpetually denied access to a resource | Uneven load, growing latency, eventual timeout | Medium-Hard (need latency analysis) |
| **Order violation** | Operations assumed to happen in order A then B but may happen B then A | Use-before-init, partial construction visible | Medium (need to identify ordering assumptions) |
| **Single-threaded correctness bug amplified by concurrency** | Bug that's harmless in single-threaded context but severe under concurrency | Crash, corruption only under load | Hard (need to think about visibility/reordering) |

The first four are classical. The fifth (starvation) is often a symptom of the others. The sixth (order violation) covers initialization races. The seventh covers bugs like double-checked locking without proper synchronization.

---

## 2. Race conditions — the canonical bug

### 2.1 The pattern

```python
# Python: classic check-then-act race
cache = {}

def get_or_compute(key):
    if key not in cache:           # Thread A and B both check, both miss
        cache[key] = expensive(key)  # Both compute, one overwrites the other
    return cache[key]
```

```go
// Go: same pattern with maps
var cache = map[string]string{}

func GetOrCompute(key string) string {
    if _, ok := cache[key]; !ok {  // Racy check
        cache[key] = expensive(key) // Racy write — Go maps are NOT concurrent-safe
    }
    return cache[key]
}
```

```rust
// Rust: racy lazy init with Cell (wouldn't compile with safe Rust, but unsafe bypass)
unsafe fn get_or_compute(cache: *mut std::collections::HashMap<String, String>, key: &str) -> &str {
    if !(*cache).contains_key(key) {
        (*cache).insert(key.to_string(), expensive(key));  // Racy insert
    }
    (*cache).get(key).unwrap()
}
```

```cpp
// C++: classic double-checked locking (BROKEN before C++11 memory model)
static Config* config = nullptr;
Config* get_config() {
    if (config == nullptr) {              // Read without lock
        std::lock_guard<std::mutex> lock(m);
        config = new Config();            // Write — but other thread may see partial state
    }
    return config;
}
```

### 2.2 Detection in source

- **Look for `if (cache.contains(x))` or `if (x in cache)` followed by mutation** — this is a check-then-act race.
- **Look for compound operations on shared state not under a lock**: `count += 1`, `cache[key] = compute()`, `if (not_in_dict): add()`.
- **Look for unprotected lazy initialization**: `static T* instance = nullptr; if (instance == nullptr) instance = new T();`

### 2.3 Detection in disassembly

The disassembly of a race condition often shows:

```
mov    rax, [shared_ptr]        ; Load shared state
test   rax, rax
jnz    .already_init
; --- Between the test and the store, another thread can store the same value ---
mov    [shared_ptr], rcx        ; Store
.already_init:
ret
```

The window between `test rax, rax; jnz` and `mov [shared_ptr], rcx` is the race. Any two threads entering this region simultaneously can both miss the check and both store, causing one of the stores to be lost.

### 2.4 Consequence

- Lost update: the value computed by one thread is overwritten by another, wasting CPU
- Inconsistent state: the cache may have a half-constructed object visible to readers
- Crash: if `Config` constructor threw between allocation and assignment, the next reader sees a `nullptr` or a partial object

### 2.5 The bounded fix

Python: use a lock around the check-and-store, or use `functools.lru_cache` (thread-safe).

```python
import threading
lock = threading.Lock()
cache = {}

def get_or_compute(key):
    with lock:
        if key not in cache:
            cache[key] = expensive(key)
        return cache[key]
```

Better: `functools.lru_cache(maxsize=None)` is lock-free and battle-tested.

Go: use `sync.Map` (concurrent-safe map) or `sync.Once` (one-time init pattern):

```go
var (
    cache = sync.Map{}
)

func GetOrCompute(key string) string {
    if v, ok := cache.Load(key); ok {
        return v.(string)
    }
    val := expensive(key)
    v, _ := cache.LoadOrStore(key, val)
    return v.(string)
}
```

Rust: use `std::sync::Mutex<HashMap<...>>` or `dashmap::DashMap`:

```rust
use dashmap::DashMap;
let cache: DashMap<String, String> = DashMap::new();

fn get_or_compute(cache: &DashMap<String, String>, key: &str) -> String {
    cache.entry(key.to_string()).or_insert_with(|| expensive(key)).clone()
}
```

C++ (post-C++11): use `std::call_once` for one-time init:

```cpp
static Config* config = nullptr;
static std::once_flag init_flag;
Config* get_config() {
    std::call_once(init_flag, []{ config = new Config(); });
    return config;
}
```

Or `std::atomic<Config*>` with `std::memory_order_acquire` for the read:

```cpp
static std::atomic<Config*> config{nullptr};
Config* get_config() {
    Config* p = config.load(std::memory_order_acquire);
    if (p == nullptr) {
        std::lock_guard<std::mutex> lock(m);
        p = config.load(std::memory_order_relaxed);
        if (p == nullptr) {
            p = new Config();
            config.store(p, std::memory_order_release);
        }
    }
    return p;
}
```

The double-checked locking pattern is correct here because of the acquire/release memory ordering.

---

## 3. Deadlock — the four necessary conditions (Coffman)

A deadlock requires all four Coffman conditions to hold simultaneously. Break any one, deadlock is impossible:

1. **Mutual exclusion**: at least one resource is held in non-shareable mode
2. **Hold and wait**: a thread holds at least one resource and waits to acquire more
3. **No preemption**: only the holder can release
4. **Circular wait**: there's a cycle in the resource allocation graph

### 3.1 The classic deadlock pattern

```python
# Python: lock-order inversion deadlock
def transfer(account_a, account_b, amount):
    with account_a.lock:
        with account_b.lock:
            account_a.debit(amount)
            account_b.credit(amount)

# Thread 1: transfer(A, B, 100)
# Thread 2: transfer(B, A, 50)
# Thread 1 holds A.lock, waits for B.lock
# Thread 2 holds B.lock, waits for A.lock
# DEADLOCK
```

```go
// Go: same pattern with mutexes
func Transfer(a, b *Account, amount int) {
    a.m.Lock()
    defer a.m.Unlock()
    b.m.Lock()
    defer b.m.Unlock()
    a.balance -= amount
    b.balance += amount
}
```

### 3.2 Detection in source — lock-order analysis

Trace the order in which each function acquires locks. If two functions acquire the same set of locks in different orders, deadlock is possible.

In Python, look for nested `with lock:` blocks. In Go, look for nested `Lock() / defer Unlock()`. In Rust, look for nested `lock.lock().unwrap()`. In C++, look for nested `std::lock_guard` or `std::unique_lock`.

### 3.3 Detection in disassembly

The disassembly of nested lock acquisition looks like:

```
call   qword ptr [rip + offset_to_pthread_mutex_lock]
; --- between these two calls, the thread holds lock A and tries to acquire lock B ---
; if another thread holds B and waits for A, deadlock
call   qword ptr [rip + offset_to_pthread_mutex_lock]
```

Acquire-acquire patterns without intervening unlocks indicate nested locking. Compare ordering across functions.

### 3.4 The bounded fix

Three common fixes:

**Lock ordering** — establish a global order for lock acquisition (e.g., by pointer value or by ID). Always acquire in this order.

```python
def transfer(account_a, account_b, amount):
    first, second = (account_a, account_b) if id(account_a) < id(account_b) else (account_b, account_a)
    with first.lock:
        with second.lock:
            if account_a is first:
                account_a.debit(amount)
                account_b.credit(amount)
            else:
                account_b.credit(amount)  # inverse the operations too
                account_a.debit(amount)
```

**Acquire both atomically** — `std::lock(m1, m2)` in C++14+, `sync.Mutex.Lock` + `sync.Mutex.Lock` with `sync.WaitGroup` trickery in Go.

C++ has `std::scoped_lock` (C++17):

```cpp
std::scoped_lock lock(a.m, b.m);  // acquires both atomically (using deadlock-avoidance algorithm)
```

**Avoid the lock entirely** — use message passing instead of shared state. Go's "share memory by communicating" idiom:

```go
// Instead of locking both accounts, send a transfer message to a single goroutine
// that owns account state
type Transfer struct {
    From, To *Account
    Amount   int
}
transfers := make(chan Transfer, 100)
go func() {
    for t := range transfers {
        t.From.balance -= t.Amount
        t.To.balance += t.Amount
    }
}()
transfers <- Transfer{a, b, 100}
```

No locks → no deadlock.

---

## 4. Atomicity violation

### 4.1 The pattern

```python
# Python: counter increment looks atomic but is actually read-modify-write
counter = 0
def increment():
    global counter
    counter += 1  # bytecode: LOAD counter, LOAD_CONST 1, BINARY_ADD, STORE counter
    # Between LOAD and STORE, another thread can increment and we'll lose our update
```

```go
// Go: same — `counter++` on int is not atomic
var counter int
func Increment() {
    counter++  // racy
}
```

```cpp
// C++: same — non-atomic counter
int counter = 0;
void Increment() {
    counter++;  // not atomic
}
```

### 4.2 Detection in source

- Look for `++` or `+=` on shared integers without `std::atomic` (C++), `sync/atomic` (Go), `threading.Lock` (Python).
- Look for compound operations: `count--; if (count == 0) cleanup();` — the test and decrement are not atomic together.
- Look for `dict[key] = dict[key] + 1` patterns — Python's GIL doesn't make this atomic.

### 4.3 Detection in disassembly

```
mov    eax, [counter]        ; LOAD
add    eax, 1                ; ADD
mov    [counter], eax        ; STORE
; --- between LOAD and STORE, another thread can load the same value, increment it, and store ---
; the result: one increment is lost
```

Three instructions, two non-atomic ops between them. The race window is the entire sequence.

### 4.4 The bounded fix

- **C++**: use `std::atomic<int>` and `counter.fetch_add(1, std::memory_order_relaxed)` or just `counter++` (overloaded for atomics).
- **Go**: use `sync/atomic.AddInt64(&counter, 1)` or `sync/atomic.AddUint64`.
- **Python**: use `threading.Lock` (the GIL doesn't help; counter++ still does multiple bytecodes).
- **Rust**: use `AtomicU64` and `counter.fetch_add(1, Ordering::Relaxed)`.

---

## 5. Order violation — initialization races

### 5.1 The pattern

```go
// Go: racy init pattern
var (
    config *Config
    wg     sync.WaitGroup
)

func init_async() {
    wg.Add(1)
    go func() {
        defer wg.Done()
        config = loadConfig()  // racy write
    }()
}

func use() {
    wg.Wait()
    fmt.Println(config.field)  // safe now (wg.Wait provides happens-before)
    // but if anyone forgets wg.Wait(), they see nil
}
```

```cpp
// C++: static init order fiasco across translation units
// file1.cpp
extern Config global_config;
// file2.cpp
Config global_config = Config();  // depends on something in file1?
// order of init between TUs is unspecified → if file2's init uses file1's data, may see zero-init state
```

### 5.2 Detection

- Look for `var X *Type` followed by `X = ...` in a goroutine (no `sync.Once`).
- Look for `static T x = init();` in C++ (correct since C++11; check if older dialect).
- Look for cross-translation-unit dependencies in global constructors.

### 5.3 The bounded fix

Go: use `sync.Once`:

```go
var (
    config *Config
    once   sync.Once
)

func GetConfig() *Config {
    once.Do(func() {
        config = loadConfig()
    })
    return config
}
```

C++: use function-local statics (Meyers Singleton):

```cpp
Config& GetConfig() {
    static Config instance = loadConfig();  // thread-safe init since C++11
    return instance;
}
```

Python: use module-level singletons (modules are init'd once at import, thread-safe by GIL).

---

## 6. Single-threaded bugs amplified by concurrency

Some bugs are harmless in single-threaded code but become severe under concurrency:

### 6.1 Use-after-free amplified

```cpp
// Single-threaded: fine — caller doesn't free
const char* get_name() {
    return config->name.c_str();  // returns ptr to internal buffer
}

// Caller stores the ptr, uses it later — if `config` is reassigned (concurrent reload),
// the string is destroyed and the caller has a dangling ptr
```

Detection: trace the lifetime of returned pointers. If the underlying state can be modified concurrently, the pointer is dangling.

### 6.2 Iterator invalidation

```cpp
std::vector<int> vec = {1, 2, 3};
auto it = vec.begin();
// another thread: vec.push_back(4);  // may reallocate, invalidates it
// `it` is now dangling
*it;  // UB — crash or wrong value
```

Python: same with `list`.

Detection: look for iterators/refs to containers that are concurrently modified.

### 6.3 ABA problem in lock-free stacks

```cpp
// Lock-free stack with compare-and-swap
// Thread 1: pop(); sees top=A, about to CAS top from A to A.next
// Thread 2: pop() (top A → B); push(A') (top B → A'); now top = A'
// Thread 1: CAS succeeds (top is "A" by value), sets top = A.next = B
// But A' is still in the stack — now unreachable
```

Detection: look for `compare-and-swap` loops without version numbers / hazard pointers.

### 6.4 Publication without synchronization (safe in some ISAs, not others)

```cpp
int data = 0;
bool ready = false;

// Thread 1:
data = 42;
ready = true;  // no synchronization — Thread 2 may see ready=true but data=0 on weak memory models

// Thread 2:
if (ready) {
    print(data);  // could print 0 on ARM/POWER, 42 on x86
}
```

Detection: look for `bool ready` flags between threads without `std::atomic` or memory barriers.

---

## 7. Async / event-loop bugs (Python `asyncio`, Rust `tokio`)

Async code is concurrent but single-threaded — no race conditions on shared state, but other bugs emerge:

### 7.1 Forgetting to await

```python
async def fetch_and_save(url):
    data = await fetch(url)
    save_to_disk(data)  # blocking I/O without await — blocks the event loop
    return data
```

Consequence: the entire event loop stalls during the disk write. Other coroutines don't run; server appears unresponsive.

Detection: look for blocking I/O calls (file I/O, `time.sleep`, sync HTTP libraries) inside async functions without offloading to `asyncio.to_thread()` or `loop.run_in_executor()`.

### 7.2 Starvation by long-running coroutine

```python
async def handler():
    await long_computation()  # takes 5 seconds
    return "ok"

# If many requests come in, all coroutines queue up. The 5-second computation
# blocks the event loop. Other requests wait.
```

Detection: look for `await` calls on functions that don't yield back quickly. Profile with `asyncio` debug mode (`PYTHONASYNCIODEBUG=1`).

### 7.3 Cancellation not respected

```python
async def worker():
    try:
        await asyncio.shield(long_op())  # immune to cancellation
    except asyncio.CancelledError:
        # cleanup
        ...
```

If `worker` doesn't propagate `CancelledError`, the caller's `task.cancel()` has no effect.

Detection: look for `except asyncio.CancelledError: pass` (silently swallows cancellation) or `except Exception: ...` that catches CancelledError (which is a BaseException in 3.8+).

### 7.4 Tokio / Rust async equivalents

`tokio::spawn` without proper cancellation, `tokio::select!` that loses pending futures (cancellation safety), `await`ing a future inside a `Drop` implementation (panics).

---

## 8. Go-specific concurrency patterns

### 8.1 Closing a channel from the receiver side

```go
ch := make(chan int)
go func() {
    ch <- 1   // sender
}()
// receiver closes ch
close(ch)  // PANIC if sender is still trying to send
```

Detection: look for `close(ch)` where `ch` is also written to by other goroutines.

### 8.2 Forgetting to close a channel — goroutine leak

```go
func worker(jobs <-chan int) {
    for job := range jobs {  // ranges until channel is closed
        process(job)
    }
}

// caller forgets to close jobs → worker goroutine never exits → leak
```

Detection: look for `for x := range ch` patterns and verify the channel is closed somewhere.

### 8.3 `select` with default that loses messages

```go
select {
case msg := <-ch:
    handle(msg)
default:
    // channel was empty — drop and continue
    // if this branch is hit under load, messages are lost
}
```

Detection: look for `select { case ...: default: ... }` patterns and verify whether dropping is intentional.

### 8.4 `sync.WaitGroup` misuse

```go
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    go func() {
        defer wg.Done()
        work()
    }()  // BUG: forgot wg.Add(1) before the goroutine
}
wg.Wait()  // returns immediately — WaitGroup counter never incremented
```

Detection: every `wg.Add(n)` should be paired with `n` `wg.Done()` calls; the `Add` should be before the goroutine starts (otherwise race on counter).

---

## 9. Rust concurrency — the `Send`/`Sync` story

Rust's ownership model prevents data races at compile time:
- `Send`: type can be transferred between threads
- `Sync`: type can be shared between threads (via `&T`)

If a type is not `Send`, you can't move it across threads. If not `Sync`, you can't have `&T` shared. This eliminates most data races — but bugs remain:

### 9.1 Deadlock with `Mutex`

```rust
let data = std::sync::Arc::new(std::sync::Mutex::new(0));
let data2 = data.clone();
std::thread::spawn(move || {
    let _g1 = data.lock().unwrap();
    let _g2 = data2.lock().unwrap();  // deadlock — same mutex acquired twice
});
```

Detection: same as Python — nested lock acquisition.

### 9.2 `unsafe` blocks bypassing the borrow checker

```rust
let mut x = 0;
let r1 = &mut x as *mut i32;
let r2 = r1;
unsafe {
    *r1 = 1;
    *r2 = 2;  // data race if r1 is shared across threads
}
```

Detection: `unsafe` blocks should be reviewed carefully. Look for raw pointers shared across threads.

### 9.3 `Arc<Mutex<T>>` vs `Arc<RwLock<T>>`

`RwLock` allows multiple readers but one writer. If readers hold the lock for a long time, writers starve. Detection: look for read-heavy workloads with `RwLock` and verify reader holding time.

---

## 10. Audit checklist

For every multi-threaded/multi-process code under audit:

1. **Identify all shared state**: globals, singletons, static fields, heap objects passed between threads.
2. **For each shared state, identify all access points**: which functions read? which write?
3. **For each access, verify the synchronization**: lock held? atomic used? channel message passed?
4. **Check-then-act patterns**: any `if (X in dict): dict[X] = ...` is suspicious.
5. **Lock acquisition order**: list all functions that acquire multiple locks; verify they acquire in consistent order.
6. **`async` blocking**: any sync I/O inside `async def` functions?
7. **Channel close**: sender closes, not receiver?
8. **`WaitGroup` discipline**: every `Add(n)` paired with `Done()` count; `Add` before goroutine start.
9. **Atomicity on shared counters**: any `++` / `+=` on shared int without atomic / lock?
10. **`unsafe` blocks in Rust**: review each one; verify no raw pointers shared.
11. **Lock-free data structures**: hazard pointers / epoch-based reclamation used? ABA possible?
12. **`std::async` / future / promise in C++**: `future.wait()` or `future.get()` called before future's destructor? (C++ future's destructor does NOT wait — easy bug.)
13. **Lock holding time**: any lock held across I/O? Across `await`? Across `system call`?
14. **`Send` / `Sync` markers in Rust**: any `impl Send for MyType` that's wrong (e.g., contains `Rc`)? Should be `unsafe impl Send` with safety comment.
15. **Cancellation safety**: long-running coroutines respect cancellation? `select!` branches are cancellation-safe (no pending I/O lost)?

---

## 11. Severity classification

| Class | Severity | Description |
|---|---|---|
| Race condition with rare corruption | P1 | Intermittent under heavy load; hard to reproduce |
| Race condition with high-impact corruption | P0 | E.g., double-free, balance corruption |
| Deadlock that affects primary flow | P0 | Service hangs |
| Deadlock that affects optional flow | P1 | E.g., metrics collection |
| Atomicity on shared counter | P2 | Lost increment; usually minor |
| Atomicity on flag/state | P1 | Lost signal, missed event |
| Order violation (init race) | P0 | Crashes on startup |
| Async blocking | P1 | Latency spike, throughput collapse |
| Goroutine/thread leak | P2 | Slow memory growth |
| `WaitGroup` misuse | P0 | Hang or premature exit |

---

## 12. Output

For every concurrency bug found:

1. Class (race / atomicity / deadlock / order / blocking / leak)
2. Severity (P0/P1/P2)
3. Code location (file:line)
4. Concrete consequence (what breaks if hit)
5. Trigger condition (when does it manifest)
6. Bounded fix (specific code change)
7. Verification (how to confirm the fix works)

The deliverable: "P0 race in `auth/session.py:42-45` — `if user not in cache: cache[user] = compute(user)` allows two concurrent requests to compute the same user, both write, one overwrites. Trigger: burst of 100+ concurrent logins for the same user. Fix: use `cachetools.func.ttl_cache` or wrap in `threading.Lock`. Verify: spawn 100 threads all calling `get_user(u)`; assert cache computed once (instrument with counter)."
