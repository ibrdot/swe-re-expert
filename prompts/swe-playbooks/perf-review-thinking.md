# Performance Review Thinking

A mental model for finding perf issues. The trick is: most "perf problems" aren't, and most real perf problems aren't where you think.

## The 3 questions

1. **Is the code on a hot path?** (called often / under load)
2. **Is the work O(N²), O(N³), or worse when it could be O(N) or O(1)?**
3. **Are there allocations / I/O in the hot loop that could be hoisted out?**

If all three are yes → finding. If any is no → observation, not finding.

## The "measure first" rule

Never recommend a perf fix without measurement:

- **Benchmark** — `timeit`, `criterion` (Rust), `pytest-benchmark`, `go test -bench`
- **Profile** — `cProfile`, `perf`, `py-spy`, `pyroscope`, Go `pprof`, Rust `cargo flamegraph`

Without measurement, you're guessing. The guess is usually wrong because:
- Most code isn't on the hot path
- Of code on the hot path, the expensive operation is rarely what you'd expect
- Compiler optimizations often make "obviously slow" patterns fast

## Where perf problems live

### Algorithmic complexity

The classic: O(N²) where O(N log N) or O(N) would work.

| Operation | Bad (O(N²)) | Good (O(N log N) or O(N)) |
|-----------|--------------|-----------------------------|
| Find duplicates | nested loop | set / map |
| Group by key | nested loop | map reduce |
| Sort | bubble sort | stdlib sort |
| Search | linear scan | binary search (sorted) / hash (unordered) |
| Find min/max | nested scan | single pass or heap |

Detection: read the loops. Nested loops over the same collection = O(N²). Loops with `for x in xs: if x == target: return x` over sorted data = should be binary search.

### N+1 queries

The classic ORM problem:

```python
for user in User.query.all():        # 1 query
    print(user.profile.bio)            # 1 query PER user → N+1 total
```

Detection: read ORM calls inside loops. Look for attribute access that triggers lazy loading.

Fix:
```python
# Eager load relations
users = User.query.options(joinedload(User.profile)).all()
# Or batch fetch:
profiles = {p.user_id: p for p in Profile.query.filter(Profile.user_id.in_(user_ids))}
```

### Unnecessary allocations in hot loops

```python
# BAD — new list every iteration
total = 0
for x in data:
    total += sum([y * 2 for y in x.subitems])  # allocates new list each call

# GOOD — generator, no allocation
total = 0
for x in data:
    total += sum(y * 2 for y in x.subitems)
```

Detection: `[x for x in ...]` inside a tight loop where `(... for x in ...)` would do.

Same for:
- Creating new strings in a loop (use StringBuilder / `"".join(parts)`)
- Creating new dicts/lists when modifying in place would do
- Re-allocating buffers that could be reused

### Unnecessary I/O in hot loops

```python
# BAD — stat call every iteration
for path in paths:
    if os.path.exists(path):  # syscall
        ...

# GOOD — batch if possible, or accept the cost
existing = {p: os.path.exists(p) for p in paths}  # still N syscalls, but explicit
```

I/O in a loop multiplies the latency. Network I/O is the worst — each call is 1-100ms.

Detection: `open()`, `requests.get()`, `os.path.exists()`, DB queries inside loops.

Fix:
- Batch (single query for all rows)
- Cache (if the value doesn't change during the loop)
- Hoist (if the value is the same every iteration)
- Parallelize (if independent, use async or threads)

### Locking / contention

```python
# BAD — global lock, serializes all requests
lock = threading.Lock()
def handle_request(req):
    with lock:
        # all work happens under the lock
        process(req)
```

Detection: global locks that wrap entire operations. Often visible as "perf cliff at moderate load" — single-threaded up to N requests/sec, then sudden degradation.

Fix:
- Use finer-grained locks (per-resource, not global)
- Use lock-free structures (`asyncio.Queue`, `concurrent.futures`)
- Use `RLock` only when re-entrancy needed; otherwise `Lock`
- Use reader-writer locks if reads dominate

### Async gone wrong

```python
async def fetch_all(urls):
    for url in urls:
        await fetch(url)  # serial — defeats the point of async

# Fix:
async def fetch_all(urls):
    await asyncio.gather(*[fetch(url) for url in urls])  # concurrent
```

Detection: `await` in a loop without `gather` or `TaskGroup`.

Other async perf issues:
- `asyncio.sleep(0)` for yielding (often unnecessary; modern asyncio yields automatically)
- Missing `await` on coroutines (silent — coroutine object is created but not awaited; common Python bug)
- Blocking I/O inside async functions (`time.sleep`, sync `requests.get`, `open()`) — blocks the event loop

### Memory waste

```python
# BAD — loads entire file into memory
with open("huge.csv") as f:
    data = f.read()
    rows = data.split("\n")

# GOOD — streaming
import csv
with open("huge.csv") as f:
    for row in csv.reader(f):
        process(row)
```

Detection: `.read()` on potentially large files; building huge in-memory lists when streaming would do.

### Cache misses (subtle)

For high-throughput code, L1/L2/L3 cache misses dominate. Patterns:
- Random memory access (cache-unfriendly)
- Linked lists (every node is a cache miss)
- Pointer-chasing (every deref is a potential miss)

Fix:
- Use contiguous arrays instead of linked lists
- Access data in sequential order (not random)
- Pack data tightly (use `__slots__` in Python, `#[repr(C)]` packed structs in Rust)
- Consider SoA (Structure of Arrays) over AoS (Array of Structures) for big-data workloads

This is rarely a top-tier finding unless the code is genuinely perf-critical (game engine, HFT, scientific computing).

## What's NOT a perf finding

### Micro-optimizations on cold paths

```python
# Don't flag this:
def main():
    name = input("Name: ")
    print(f"Hello, {name}")

# Even though:
# - f-string is "slower" than % formatting by 10ns
# - print() is "slower" than sys.stdout.write by 100ns
# The function is called once; the perf difference is invisible
```

Cold-path code doesn't need optimization. Linter / profiler will tell you if it does.

### Premature parallelization

```python
# Don't recommend this unless the function is provably slow and parallelizable:
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as ex:
    results = list(ex.map(process_item, items))
```

If the function takes 10ms and you have 100 items, serial is 1 second, parallel is 100ms — save 900ms. But:
- Thread pool setup has overhead (~50ms)
- GIL contention (Python) may negate the parallelism
- Code complexity goes up
- Test coverage gets harder

Only parallelize when:
- The serial version is provably too slow (you've measured)
- The work is actually parallelizable (no shared mutable state)
- The parallelism overhead is less than the savings

### Speculative optimization

> "What if we have 10x more users?" — not a finding. Recommend when they have 10x more users.

Recommend changes for problems the team has today. Not hypothetical future problems.

## The "big O dominates constant" rule

```python
# Option A: O(N) with high constant
result = [x * 2 for x in range(1000)]

# Option B: O(N²) with low constant
result = []
for i in range(1000):
    for j in range(1000):
        if i == j:
            result.append(i * 2)
```

Option A is faster despite the higher constant — at scale, O(N) wins.

When you see O(N²), it's almost always a finding (unless N is provably small).

## The "benchmark before / after" rule

When you recommend a perf change, include a benchmark estimate:

```
Current: ~50ms per call (measured with cProfile on 1000 iterations)
Recommended: ~5ms per call (estimate; the loop body is now O(1) instead of O(N))
Expected speedup: 10x on this hot path
Overall impact: ~5% on end-to-end (this is 50% of the request time, but only 10% of total)
```

Without measurement and estimate, the recommendation is unfalsifiable. With it, the team can prioritize.

## Where to spend your time

In a 1-hour perf review:

| Phase | Time |
|-------|------|
| Identify hot paths (read code, check profiler output) | 15 min |
| Trace 2-3 hot paths for O(N²) / N+1 / unnecessary allocations | 30 min |
| Write findings with benchmarks | 15 min |

Don't try to perf-review everything. Focus on the code that actually runs under load. Most code doesn't.

## Output

The perf section of the audit report should have:

| Priority | Hot path | Issue | Measured cost | Recommended fix | Estimated speedup |
|----------|----------|-------|---------------|------------------|---------------------|
| P1 | `process_order` | N+1 query in line 23 | 50ms / 1000 rows | Eager load | 5x |
| P2 | `format_report` | String concat in loop | 200ms / 10MB report | Use `"".join()` | 3x |

Each row: the path (so the team can find it), the issue (specific), the measured cost (so the team can prioritize), the fix (specific), the estimate (so the team can plan).

Without measurement → not a perf finding. It's a hypothesis.
