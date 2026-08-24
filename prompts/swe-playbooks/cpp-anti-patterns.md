# C++ Anti-Patterns

C++ has 40 years of language evolution behind it. The compiler catches a lot, but the patterns below still cause real bugs.

## P0 — Memory safety / security

### Raw pointer + manual `new` / `delete`

```cpp
// P0 — leak on exception, use-after-free risk
void process() {
    auto* obj = new Object();
    do_something();  // if this throws, obj leaks
    delete obj;
}

// Fix: smart pointers
#include <memory>
void process() {
    auto obj = std::make_unique<Object>();
    do_something();  // RAII releases on exception
}
```

Rule: never use raw `new` / `delete` in modern C++ code. Use `std::unique_ptr` (single owner) or `std::shared_ptr` (shared ownership).

### `malloc` / `free` for non-POD types

```cpp
// P0 — doesn't call constructor / destructor
auto* obj = static_cast<Object*>(malloc(sizeof(Object)));
// ... never calls obj->Object() ...
free(obj);  // doesn't call destructor

// Fix: use new / delete or smart pointer
auto obj = std::make_unique<Object>();
```

### Buffer overflow

```cpp
// P0 — unbounded copy
char buf[16];
strcpy(buf, user_input);   // overflow if input > 15 chars
gets(buf);                  // never use this
sprintf(buf, "%s", user_input);  // never use this

// Fix: bounds-checked or use std::string
std::string buf;
buf = user_input;  // std::string grows dynamically
// Or for fixed-size:
strncpy(buf, user_input, sizeof(buf) - 1);
buf[sizeof(buf) - 1] = '\0';
// Or better: use std::array + std::format_to
```

### Use-after-free

```cpp
// P0 — pointer reused after free
auto* p = new Object();
delete p;
p->method();  // UB — use after free

// Fix: smart pointer
auto p = std::make_unique<Object>();
// p is released automatically; can't dangle
```

### Double free

```cpp
// P0 — UB, often exploitable
auto* p = new Object();
auto* q = p;
delete p;
delete q;  // double free

// Fix: smart pointer with single owner
auto p = std::make_unique<Object>();
// p.get() returns raw pointer for read-only access
// std::move(p) transfers ownership
```

### Format string vulnerability

```cpp
// P0 — printf with user-controlled format string
printf(user_input);  // %n writes, %s reads stack

// Fix: hardcoded format
printf("%s", user_input);
// Or use std::format (C++20+)
std::cout << user_input;
```

### Integer overflow leading to buffer overflow

```cpp
// P0 — size_t * size_t can wrap; alloc small, copy large
size_t n = a * b;  // overflow if a*b > SIZE_MAX
char* buf = new char[n];
memcpy(buf, src, real_size);  // overflow

// Fix: check before multiplication, use checked arithmetic
size_t n;
if (__builtin_mul_overflow(a, b, &n)) {
    throw std::overflow_error("size overflow");
}
auto buf = std::make_unique<char[]>(n);
```

## P1 — Modern C++ / correctness

### C-style arrays

```cpp
// P1 — no size info, decays to pointer
void process(int values[10]) {
    sizeof(values);  // = sizeof(int*), not 10*sizeof(int)
}

// Fix: std::array
void process(const std::array<int, 10>& values) {
    values.size();  // = 10
}
// Or std::span (C++20+)
void process(std::span<const int> values) {
    values.size();
}
```

### Manual memory management in containers

```cpp
// P1 — leak on exception
std::vector<Object*> objects;
objects.push_back(new Object());
// if push_back throws, the new Object leaks
// (vector doesn't own the pointers)

// Fix: smart pointers
std::vector<std::unique_ptr<Object>> objects;
objects.push_back(std::make_unique<Object>());
// RAII releases on vector destruction
```

### Exceptions caught by value

```cpp
// P1 — slicing (loses derived type info)
try {
    throw Derived();
} catch (Base e) {  // copies only Base part
    e.virtual_method();  // calls Base::virtual_method, not Derived::virtual_method
}

// Fix: catch by reference
try {
    throw Derived();
} catch (const Base& e) {
    e.virtual_method();  // calls Derived::virtual_method
}
```

### `endl` instead of `"\n"`

```cpp
// P1 — endl flushes the buffer; slow
std::cout << "Hello" << std::endl;

// Fix: use \n
std::cout << "Hello\n";
// Or use std::print (C++23+)
std::print("Hello\n");
```

### Virtual function in constructor / destructor

```cpp
// P1 — calls Base::init, not Derived::init
class Base {
public:
    Base() { init(); }  // virtual call during construction
    virtual void init() { std::cout << "Base"; }
};
class Derived : public Base {
public:
    void init() override { std::cout << "Derived"; }
};
Derived d;  // prints "Base", not "Derived"

// Fix: don't call virtual methods from constructors
// Use two-phase initialization
class Base {
public:
    Base() {}
    void initialize() { init(); }  // call after construction
    virtual void init() {}
};
auto d = std::make_unique<Derived>();
d->initialize();
```

### Missing virtual destructor on polymorphic class

```cpp
// P1 — UB when deleting Derived through Base*
class Base {
public:
    ~Base() {}  // not virtual
};
class Derived : public Base {
public:
    ~Derived() { /* cleanup */ }
};
Base* p = new Derived;
delete p;  // doesn't call Derived::~Derived

// Fix: virtual destructor on base class (or make it final + non-virtual)
class Base {
public:
    virtual ~Base() = default;
};
```

### `static_cast` for downcasting

```cpp
// P1 — UB if the object isn't actually Derived
Base* p = get_object();
Derived* d = static_cast<Derived*>(p);  // UB if p isn't Derived

// Fix: dynamic_cast (polymorphic types only)
Derived* d = dynamic_cast<Derived*>(p);
if (!d) {
    // not a Derived
}
// Or: use visitor pattern
// Or: redesign to avoid downcasting
```

### Const-correctness violations

```cpp
// P1 — defeats optimization, allows mutation
void process(int* data) {
    // what if data points to const?
}

// Fix: const where appropriate
void process(const int* data) {  // data is read-only
    // ...
}
void process(int* data) {  // data is writable
    *data = 5;
}
```

## P2 — Maintainability

### Macro abuse

```cpp
// P2 — type-unsafe, hard to debug
#define MAX(a, b) ((a) > (b) ? (a) : (b))
int x = MAX(i++, j++);  // i++ evaluated twice!

// Fix: template inline
template<typename T>
inline T max(T a, T b) {
    return a > b ? a : b;
}
// Or use std::max
auto x = std::max(i, j);
```

### Manual memory management in APIs

```cpp
// P2 — caller doesn't know who owns what
Object* create_object();  // who deletes?

// Fix: return smart pointer
std::unique_ptr<Object> create_object();  // caller owns
// Or return by value
Object create_object();  // copy or move
```

### `#include` of full headers where forward decl suffices

```cpp
// P2 — slow compile
#include "BigHeader.h"
class MyClass {
    BigClass* m_member;  // pointer only — forward decl would do
};

// Fix: forward declare
class BigClass;
class MyClass {
    BigClass* m_member;
};
// In .cpp:
#include "BigHeader.h"
// ...
```

### Single-function header file with massive dependencies

```cpp
// P2 — includes everything
// util.h
#include "Network.h"
#include "Database.h"
#include "UI.h"
#include "Logger.h"
void log_message(const std::string&);

// Fix: include only what's needed in the header
// util.h
#include <string>
void log_message(const std::string&);
// In .cpp:
#include "Network.h"
#include "Database.h"
// ...
```

### Singletons (anti-pattern)

```cpp
// P2 — global state, hard to test, init order issue
class Logger {
public:
    static Logger& instance() {
        static Logger inst;
        return inst;
    }
};

// Fix: dependency injection
class Logger { /* ... */ };
class Service {
    Logger& m_logger;
public:
    Service(Logger& logger) : m_logger(logger) {}
};
```

### Long namespace chains in API

```cpp
// P2 — verbose at call site
my::company::product::feature::do_something();

// Fix: alias in source files (not headers)
namespace mcpf = my::company::product::feature;
mcpf::do_something();
```

### Manual implementations of stdlib

```cpp
// P2 — buggy custom version
bool contains(const std::vector<int>& v, int target) {
    for (auto x : v) {
        if (x == target) return true;
    }
    return false;
}

// Fix: use std::find
#include <algorithm>
bool found = std::find(v.begin(), v.end(), target) != v.end();
// Or C++20:
bool found = std::ranges::contains(v, target);
```

## P3 — Style

- Use of C-style casts `(int)x` over `static_cast<int>(x)`
- `using namespace std;` in headers (pollutes downstream)
- Mixed tabs / spaces
- Long functions
- Missing `const`/`constexpr` where appropriate
- Public members that should be private

These get caught by `clang-tidy`. Don't review manually.

## The "modern C++" checklist

For modernization (each needs a concrete defect to justify):

- [ ] C++20/23 features (`std::span`, `std::format`, `std::ranges`, `std::expected`)
- [ ] `std::filesystem` (replaces `boost::filesystem` or POSIX)
- [ ] Smart pointers everywhere (`std::unique_ptr`, `std::shared_ptr`)
- [ ] `std::array` / `std::vector` instead of C arrays
- [ ] `std::string_view` for non-owning string parameters
- [ ] Range-based for loops
- [ ] `auto` for type deduction where it improves readability
- [ ] `constexpr` for compile-time computations
- [ ] `[[nodiscard]]` on functions returning important values
- [ ] `[[maybe_unused]]` instead of `(void)var`
- [ ] Concepts instead of SFINAE
- [ ] Modules (where supported — faster builds)
- [ ] `std::format` / `std::print` (C++20/23) instead of iostream or printf

## Tool reference

```bash
# Format
clang-format -i $(find . -name "*.cpp" -o -name "*.h")

# Lint — modernize checks catch most P2/P3
clang-tidy --checks="-*,modernize-*,readability-*,bugprone-*,performance-*" \
    -p build/ source.cpp

# Static analysis
clang-tidy --checks="clang-analyzer-*" source.cpp
# Or:
cppcheck --enable=all .

# Memory safety
valgrind --tool=memcheck ./program
# Or modern: AddressSanitizer, MemorySanitizer
g++ -fsanitize=address -g -o program source.cpp
./program  # reports memory bugs at runtime

# UBSan (undefined behavior)
g++ -fsanitize=undefined -g -o program source.cpp

# Thread sanitizer
g++ -fsanitize=thread -g -o program source.cpp

# Profile
g++ -pg -g -o program source.cpp
./program
gprof program gmon.out

# Or perf (Linux)
perf record ./program
perf report
```

Use these in CI. AddressSanitizer + clang-tidy modernize catch most of the findings in this file automatically.
