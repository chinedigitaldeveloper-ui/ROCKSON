# `myc` (ROCKSON)

> A statically-typed, memory-managed, and runtime-safe object-oriented programming language compiling directly to high-performance C backed by the Boehm-Demers-Weiser Garbage Collector (`libgc`).

---

## Project Type

- **Category:** Compiler / language tooling
- **Implementation language:** Python 3.8+ (zero external package dependencies)
- **Source language:** `myc` (`.src`)
- **Target:** GNU C11 compiled with GCC / Clang
- **Runtime:** Boehm-Demers-Weiser Garbage Collector (`libgc`)

---

## Compiler Pipeline

```text
myc Source Code (.src)
          │
          ▼
ModuleLoader (module_loader.py)
  - Resolves relative imports
  - Dedupes shared imports (diamond)
  - Rejects circular import cycles
          │
          ▼
Lexer & Parser (lexer.py, parser.py)
  - Tokenizes with regex engine
  - Recursive descent parsing
  - Unified Program AST
          │
          ▼
TypeChecker / Resolver (typechecker.py)
  - Static type inference & verification
  - Prefix-compatible VTable validation
  - Non-capturing lambda scope isolation
          │
          ▼
[Target Architecture: Typed HIR]
          │
          ▼
CodeGenerator (codegen.py)
  - Lowers AST to standard GNU C11
  - Desugars inheritance to struct base
  - Static prefix-compatible VTables
  - Lifts lambdas to static C functions
  - setjmp/longjmp exception frames
  - Runtime bounds and null guards
          │
          ▼
GCC / Clang Backend Driver
  gcc source.tmp.c -lgc -o binary
          │
          ▼
Native Executable Binary
```

---

## Quick Start

### Prerequisites
- Python 3.8+
- GCC or Clang (C11 support)
- Boehm Garbage Collector (`libgc-dev` on Ubuntu/Debian, `bdw-gc` on macOS Homebrew)

```bash
# Ubuntu / Debian
sudo apt-get install build-essential libgc-dev

# macOS
brew install bdw-gc
```

### Build and Run

```bash
# 1. Compile a .src file to a native binary
./myc sample.src -o sample_app

# 2. Execute the native binary
./sample_app

# 3. Emit intermediate C code for debugging
./myc sample.src --emit-c
```

---

## Dependencies

| Dependency | Role | Required |
|---|---|---|
| Python 3.8+ | Compiler implementation frontend & backend driver | ✅ |
| GCC / Clang | Target C compiler generating native machine code | ✅ |
| `libgc` (Boehm GC) | Conservative garbage collection runtime (`<gc.h>`) | ✅ |

---

## Supported Language Features

| Feature | Frontend | Semantic Analysis | Backend / Runtime |
|---|---|---|---|
| **Memory Management** | Automatic (`new`) | Reference vs. Value typing | Boehm GC (`GC_MALLOC`, `GC_MALLOC_ATOMIC`) |
| **Classes & OOP** | `class`, `new`, `this` | Field & constructor validation | Struct desugaring, `__new_*` constructors |
| **Inheritance** | `extends` | Cycle detection, root resolution | Offset-0 struct embedding (`Derived.base`) |
| **Polymorphism** | Method declarations | Override signature compatibility | Static prefix-compatible VTables |
| **First-Class Functions** | `ret_t(params...)` types | Function type equivalence | Clean `typedef` synthesis, null guards |
| **Anonymous Lambdas** | `(params) => expr / { ... }` | Scope isolation (`outer_scopes`) | Static function lifting (`__lambda_<id>`) |
| **Exceptions** | `try`, `catch`, `throw` | Catch parameter & throw typing | `setjmp`/`longjmp`, frame stack |
| **Modules & Imports** | `import "path.src";` | Unified AST symbol resolution | Canonical path tracking, cycle aborts |
| **Arrays & Slices** | `T[]`, `new T[size]`, `arr[i]` | Type inference, index validation | Dynamic heap structs, `__bounds_check` |
| **Strings & Concat** | String literals (`"..."`, `\"`) | Assignability, mixed string/int `+` | GC atomic buffers, `__str_concat` |
| **Control Flow** | `if`/`else`, `while`, `for` | Boolean condition enforcement | Native C branching, `break`/`continue` |
| **Standard Library** | Built-in prototypes | Standard signature registration | File I/O, string tools, GC introspection |
| **CLI Arguments** | `int main(string[] args)` | Arity & signature validation | `argc`/`argv` conversion to `Array_string*` |

---

## Safety & Semantic Contract

`myc` is designed as **memory-managed and runtime-safe**. The source language prohibits unsafe pointer arithmetic and emits dynamic safety guards, but operates with known phase-boundary soundness gaps currently being addressed for v0.1:

- **Memory Model**: No manual `malloc` / `free`. Composite pointer structures use `GC_MALLOC`; atomic leaf buffers use `GC_MALLOC_ATOMIC`. Operates as conservative collection over raw C heap memory.
- **Null Safety**: Pointer dereferences (field access, method calls, array indexing, function calls) evaluate through runtime `__check_null()` guards that abort on null. Known soundness gaps: uninitialized locals currently lower to uninitialized C stack values (C-02), and `this` is not yet protected from assignment (C-06).
- **Bounds Safety**: Array accesses evaluate through `__bounds_check()` against array `length`. Known soundness gap: `array.length` is currently writable (C-01), which allows source code to bypass bounds validation.
- **Integer Semantics**: Arithmetic currently lowers directly to native C `int`. Defined bit-width and trapping for division-by-zero / signed overflow remain open target items (H-03).
- **Evaluation Order**: Lowered expressions currently inherit the target C compiler's evaluation order. Strict left-to-right evaluation order and single evaluation of index expressions remain open target items (H-08).
- **Exception Model**: Structured unwinding via `setjmp`/`longjmp`. Active exception frames are balanced on `return`/`break`/`continue`.
- **Concurrency Scope**: Single-threaded v1 runtime. Exception frame state (`__top_frame`) is process-global.

---

## Real-World Showcase: Markdown-to-HTML CLI

A complete Markdown-to-HTML command-line converter written entirely in `.src`:
- [`md2html.src`](md2html.src) — Polymorphic AST blocks, inline token formatting, CLI file I/O.
- [`lib_array.src`](lib_array.src) — Higher-order functional array algorithms (`map`, `filter`, `fold`, `join`).

```bash
./myc md2html.src -o md2html
./md2html test_doc.md output.html
```

---

## Testing

```bash
python3 test_runner.py
```

- Current test suites: **46 automated test suites** (53 `.src` files: 46 runnable, 7 reusable modules).
- Current backend driver: GCC with no explicit optimization or language-standard flags.
- Target verification: GCC/Clang at -O0 and -O2 plus UBSan.

---

## Branch Flow

```text
feature/* → dev → PR → main
```

- Never push directly to `main`.
- Development and planning documentation follow `dev-templates@dev/SOLO_DEV_WORKFLOW.md`.
