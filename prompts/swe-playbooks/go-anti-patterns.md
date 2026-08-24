# Go Anti-Patterns

Go is opinionated about style (gofmt, go vet). The patterns below aren't covered by linters and catch real bugs.

## P0 — Security / correctness

### SQL string concatenation

```go
// P0 — SQLi
db.Query(fmt.Sprintf("SELECT * FROM users WHERE id = %s", userID))

// Fix: parameterized
db.Query("SELECT * FROM users WHERE id = $1", userID)
// Or with sqlx:
db.Get(&user, "SELECT * FROM users WHERE id = $1", userID)
```

### `os/exec` with user input

```go
// P0 — command injection
cmd := exec.Command("sh", "-c", "curl "+url)

// Fix: don't use sh -c, pass args directly
cmd := exec.Command("curl", url)
```

### Path traversal

```go
// P0 — arbitrary file read
data, _ := os.ReadFile(filepath.Join("/data", userFilename))

// Fix: clean and check
target := filepath.Clean(filepath.Join("/data", userFilename))
if !strings.HasPrefix(target, "/data/") {
    return errors.New("path traversal")
}
data, _ := os.ReadFile(target)
```

### Weak crypto

```go
// P0 — collision attacks
h := md5.New()

// Fix
import "golang.org/x/crypto/bcrypt"
hashed, _ := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)

// For hashing (not passwords):
import "crypto/sha256"
h := sha256.New()
```

### Predictable randomness for security

```go
// P0 — predictable token
import "math/rand"
token := make([]byte, 16)
rand.Read(token)

// Fix: crypto/rand
import "crypto/rand"
token := make([]byte, 16)
rand.Read(token)
// (yes, the API looks similar; crypto/rand is the secure one)
```

## P1 — Correctness / concurrency

### Unhandled error

```go
// P1 — silent failure
result, _ := someFunc()

// Fix: handle or explicitly document
result, err := someFunc()
if err != nil {
    return fmt.Errorf("someFunc failed: %w", err)
}
```

Rule: don't discard errors with `_`. Either handle, propagate, or wrap, or document why it's safe to ignore.

### Unhandled `error` after `defer Close()`

```go
// P1 — silent close error, can lose data
defer file.Close()

// Fix: explicit close with error check
defer func() {
    if err := file.Close(); err != nil {
        log.Printf("close failed: %v", err)
    }
}()
```

### Race condition: shared map without sync

```go
// P1 — concurrent map access panics
var cache = map[string]string{}

func get(key string) string {
    return cache[key]  // panic if another goroutine writes
}

// Fix: sync.Mutex or sync.Map
var (
    cacheMu sync.Mutex
    cache = map[string]string{}
)

func get(key string) string {
    cacheMu.Lock()
    defer cacheMu.Unlock()
    return cache[key]
}
// Or use sync.Map for high-contention scenarios
```

### `interface{}` everywhere

```go
// P1 — loses type safety, runtime panics
func process(data interface{}) interface{} {
    switch v := data.(type) {
    case string:
        return strings.ToUpper(v)
    case int:
        return v * 2
    }
    return nil
}

// Fix (1.18+): use generics
func process[T Stringer](data T) T {
    return data.ToUpper()
}

// Or use a typed interface
type Processable interface {
    Process() Processable
}
func process(p Processable) Processable {
    return p.Process()
}
```

### Goroutine leak (no shutdown path)

```go
// P1 — goroutine runs forever, holds resources
func worker() {
    for {
        time.Sleep(time.Second)
        doWork()
    }
}
go worker()  // never stops

// Fix: context for cancellation
func worker(ctx context.Context) {
    ticker := time.NewTicker(time.Second)
    defer ticker.Stop()
    for {
        select {
        case <-ticker.C:
            doWork()
        case <-ctx.Done():
            return
        }
    }
}
ctx, cancel := context.WithCancel(context.Background())
defer cancel()
go worker(ctx)
```

### `time.Sleep` for sync

```go
// P1 — race condition
func waitForReady() {
    time.Sleep(time.Second)
    return getReady()
}

// Fix: channel or WaitGroup
ready := make(chan struct{})
go func() {
    prepare()
    close(ready)
}()
<-ready
return getReady()
```

### `context.Background()` propagated deep

```go
// P1 — loses cancellation, no timeout
func handler(w http.ResponseWriter, r *http.Request) {
    callDeeply(r.Context())  // good — propagates request context
}

// Bad:
func handler(w http.ResponseWriter, r *http.Request) {
    callDeeply(context.Background())  // request can be cancelled but the work continues
}
```

Rule: pass the request's context downstream. Only use `context.Background()` for top-level setup (CLI, main).

### Closing over loop variable (pre-1.22)

```go
// P1 — loop variable captured; all goroutines see last value (pre-1.22)
for _, i := range items {
    go func() {
        process(i)  // i is always the last item!
    }()
}

// Fix (pre-1.22): shadow or pass as arg
for _, i := range items {
    i := i  // shadow
    go func() {
        process(i)
    }()
}
// Or:
for _, i := range items {
    go func(i Item) {
        process(i)
    }(i)
}
```

Note: Go 1.22+ fixes this — loop variable is scoped per-iteration. But check your Go version.

## P2 — Maintainability

### God function

```go
// P2 — 200+ LOC, multiple responsibilities
func processOrder(order *Order) error {
    // validate
    // pricing
    // discounts
    // persist
    // email
    // ...
}

// Fix: split into smaller functions
func processOrder(order *Order) error {
    if err := validateOrder(order); err != nil { return err }
    pricing := computePricing(order)
    applyDiscounts(order, pricing)
    if err := saveOrder(order); err != nil { return err }
    return sendConfirmation(order)
}
```

### Magic numbers

```go
// P2 — what is 86400?
timeout := 86400

// Fix: named constant
const SecondsPerDay = 86400
timeout := SecondsPerDay
```

### Stringly-typed modes

```go
// P2 — typo at call site = silent wrong behavior
func process(data []byte, mode string) error {
    switch mode {
    case "fast": ...
    case "slow": ...
    case "safe": ...
    }
}

// Fix: typed enum (use iota)
type Mode int
const (
    ModeFast Mode = iota
    ModeSlow
    ModeSafe
)

func process(data []byte, mode Mode) error {
    switch mode {
    case ModeFast: ...
    // ...
    }
}
```

### Manual implementations of stdlib

```go
// P2 — buggy custom version
func contains(s []string, target string) bool {
    for _, v := range s {
        if v == target {
            return true
        }
    }
    return false
}

// Fix: use stdlib
import "slices"
slices.Contains(s, target)
```

### Long function with deep nesting

```go
// P2 — pyramid of doom
func process(items []Item) {
    for _, item := range items {
        if item.Valid {
            if item.Type == "A" {
                if item.Priority > 5 {
                    // ...
                }
            }
        }
    }
}

// Fix: guard clauses
func process(items []Item) {
    for _, item := range items {
        if !item.Valid {
            continue
        }
        if item.Type != "A" {
            continue
        }
        if item.Priority <= 5 {
            continue
        }
        // ...
    }
}
```

### `panic` in library code

```go
// P2 — library should return error, not panic
func Parse(data []byte) Config {
    if len(data) == 0 {
        panic("empty input")
    }
    // ...
}

// Fix: return error
func Parse(data []byte) (Config, error) {
    if len(data) == 0 {
        return Config{}, errors.New("empty input")
    }
    // ...
}
```

### `if err != nil` chains without context

```go
// P2 — error loses context
result, err := step1()
if err != nil { return err }
result2, err := step2(result)
if err != nil { return err }

// Fix: wrap with context
result, err := step1()
if err != nil { return fmt.Errorf("step1: %w", err) }
result2, err := step2(result)
if err != nil { return fmt.Errorf("step2: %w", err) }
```

## P3 — Style

- Inconsistent naming (mixed camelCase and snake_case — should be all camelCase in Go)
- Exported items without doc comments
- Receiver name inconsistent (`func (this *Foo)` vs `func (f *Foo)`)
- Long parameter lists (5+ args)
- Manual implementations where stdlib has it (search `bytes`, `strings`, `slices`, `maps`)

These usually get caught by `golangci-lint`. Don't review manually.

## The "modern Go" checklist

For modernization (each needs a concrete defect to justify):

- [ ] Generics (1.18+) — replace `interface{}` + type assertions with type parameters
- [ ] `slog` (1.21+) — structured logging
- [ ] `errors.Join` (1.20+) — wrap multiple errors
- [ ] `slices` / `maps` packages (1.21+) — generic helpers
- [ ] `range-over-int` (1.22+) — cleaner range syntax
- [ ] `for v := range channel` (1.22+)
- [ ] `go vet -shadow` enabled (default in 1.22+)
- [ ] Standard library `testing/testing` improvements

## Tool reference

```bash
# Format
gofmt -w .

# Vet
go vet ./...

# Lint (comprehensive)
golangci-lint run

# Race detector (must run tests with -race)
go test -race ./...

# Test coverage
go test -cover ./...
go test -coverprofile=coverage.out ./... && go tool cover -html=coverage.out

# Dead code
go run github.com/uudashr/dead-code/cmd/dead-code@latest

# Unused dependencies
go mod tidy  # removes unused
go run github.com/DVvk/unused-package@latest  # checks imports
# Or:
go list -deps ./... | sort -u  # see all deps

# Benchmark
go test -bench=. ./...

# Profile
go test -cpuprofile=cpu.out -bench=. ./...
go tool pprof cpu.out
```

Use these in CI. `golangci-lint` with default linters catches most P2/P3 findings.
