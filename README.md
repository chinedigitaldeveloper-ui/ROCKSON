# `myc` — A Memory-Safe, Object-Oriented Language Compiled to C

`myc` is a statically-typed, memory-safe, object-oriented programming language that compiles directly into high-performance, portable C backed by the **Boehm-Demers-Weiser Garbage Collector (`libgc`)**.

It blends the syntax and expressiveness of high-level languages like Java and C# (classes, single inheritance, virtual method dispatch, first-class functions, anonymous lambdas, exceptions, and automatic memory management) with the execution speed, portability, and simplicity of C.

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Language Capability Matrix](#language-capability-matrix)
- [Core Language Features](#core-language-features)
  - [1. Automatic Memory Management (Boehm GC)](#1-automatic-memory-management-boehm-gc)
  - [2. Classes, Inheritance & Virtual Dispatch](#2-classes-inheritance--virtual-dispatch)
  - [3. First-Class Functions & Anonymous Lambdas](#3-first-class-functions--anonymous-lambdas)
  - [4. Exception Handling (`try` / `catch` / `throw`)](#4-exception-handling-try--catch--throw)
  - [5. Module System & Circular Import Detection](#5-module-system--circular-import-detection)
  - [6. Arrays & Runtime Safety (NPE & Bounds Protection)](#6-arrays--runtime-safety-npe--bounds-protection)
  - [7. Standard Library & CLI Arguments](#7-standard-library--cli-arguments)
- [Real-World Showcase: Markdown-to-HTML CLI (`md2html.src`)](#real-world-showcase-markdown-to-html-cli-md2htmlsrc)
- [Compiler Internals & Pipeline](#compiler-internals--pipeline)
- [Test Suite & Verification](#test-suite--verification)
- [Quickstart & Usage Guide](#quickstart--usage-guide)

---

## Overview & Architecture

The `myc` compilation pipeline processes source files through five distinct stages:

```
                            ┌─────────────────────────────────────────┐
                            │          myc Source Code (.src)         │
                            └─────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │    ModuleLoader (module_loader.py)      │
                            │  - Resolves relative imports            │
                            │  - Dedupes shared imports (diamond)     │
                            │  - Rejects circular import cycles       │
                            └─────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │     Lexer & Parser (lexer.py, parser.py)│
                            │  - Tokenizes with regex engine          │
                            │  - Precedence recursive descent parser  │
                            │  - Builds unified Program AST           │
                            └─────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │      TypeChecker (typechecker.py)       │
                            │  - Strict static type inference         │
                            │  - VTable override verification         │
                            │  - Non-capturing lambda scope isolation │
                            │  - Safe type assignability checks       │
                            └─────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │      CodeGenerator (codegen.py)         │
                            │  - Lowers AST to standard ANSI C        │
                            │  - Desugars inheritance to struct base  │
                            │  - Static prefix-compatible VTables     │
                            │  - Lifts lambdas to static C functions  │
                            │  - setjmp/longjmp exception frames      │
                            │  - Bounds & Null-Pointer guards         │
                            └─────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │            GCC Compiler Driver          │
                            │  gcc -O2 output.c -lgc -o binary        │
                            └─────────────────────────────────────────┘
```

---

## Language Capability Matrix

| Feature | Frontend (Lexer & Parser) | Semantics (TypeChecker) | Backend (Code Generator & Runtime) |
| :--- | :--- | :--- | :--- |
| **Memory Management** | Automatic (`new`) | Reference vs. Value typing | Boehm GC (`GC_MALLOC`, `GC_MALLOC_ATOMIC`) |
| **Classes & OOP** | `class`, `new`, `this` | Field/Constructor validation | Struct desugaring, `__new_*` constructors |
| **Inheritance** | `extends` | Cycle detection, root resolution | Offset-0 struct embedding (`Derived.base`) |
| **Polymorphism** | Method declarations | Override signature compatibility | Static prefix-compatible VTables |
| **First-Class Functions** | `ret_t(params...)` types | Function type equivalence | Clean `typedef` synthesis, null guards |
| **Anonymous Lambdas** | `(params) => expr / { ... }` | Scope isolation (`outer_scopes`) | Static function lifting (`__lambda_<id>`) |
| **Exceptions** | `try`, `catch`, `throw` | Catch parameter & throw typing | `setjmp`/`longjmp`, control flow frame popping |
| **Modules & Imports** | `import "path.src";` | Unified AST symbol resolution | Canonical path tracking, cycle aborts |
| **Arrays & Slices** | `T[]`, `new T[size]`, `arr[i]` | Type inference, index validation | Dynamic heap structs, `__bounds_check` |
| **Strings & Concat** | String literals (`"..."`, `\"`) | Assignability, mixed string/int `+` | GC atomic buffers, `__str_concat` |
| **Control Flow** | `if`/`else`, `while`, `for` | Boolean condition enforcement | Native C branching, `break`/`continue` |
| **Standard Library** | Built-in prototypes | Standard signature registration | File I/O, string tools, GC introspection |
| **CLI Arguments** | `int main(string[] args)` | Arity & signature validation | `argc`/`argv` conversion to `Array_string*` |

---

## Core Language Features

### 1. Automatic Memory Management (Boehm GC)
`myc` eliminates manual memory management (`malloc` / `free`). All allocations are tracked by Boehm GC:
- **`GC_MALLOC`**: Used for composite structures containing pointers (classes, array headers, function closures).
- **`GC_MALLOC_ATOMIC`**: Used for leaf data containing no pointers (character buffers for strings).
- **Introspection**: Code can query and drive the collector at runtime:
  ```c
  gc_collect();                   // Triggers immediate garbage collection
  int heap = gc_heap_size();      // Returns resident heap size in bytes
  int free_b = gc_free_bytes();   // Returns estimated reclaimable bytes
  ```

### 2. Classes, Inheritance & Virtual Dispatch
Classes support single inheritance with dynamic virtual method dispatch.

```c
class Shape {
    int x;
    int y;

    Shape(int x, int y) {
        this.x = x;
        this.y = y;
    }

    int area() {
        return 0;
    }
}

class Rectangle extends Shape {
    int width;
    int height;

    Rectangle(int x, int y, int w, int h) {
        this.x = x;
        this.y = y;
        this.width = w;
        this.height = h;
    }

    int area() {
        return this.width * this.height;
    }
}
```

#### How it compiles to C:
- **Offset-0 Struct Embedding**: A subclass embeds its parent as the very first member (`struct Rectangle { Shape base; int width; int height; };`). An upcast `(Shape*) rect` is a completely zero-cost pointer cast.
- **Prefix-Compatible VTables**: Every class instance holds a `vptr` pointing to a statically allocated VTable. Overridden methods overwrite their slot in the table, guaranteeing $O(1)$ dynamic dispatch.

### 3. First-Class Functions & Anonymous Lambdas
Functions are first-class values and can be passed as arguments, assigned to variables, or returned.

```c
// Typed function pointer variable
int(int, int) op = (int a, int b) => a + b;
print("Result: " + op(10, 20));

// Inline arrow lambdas passed to higher-order combinators
int[] nums = new int[3];
nums[0] = 1; nums[1] = 2; nums[2] = 3;

int[] doubled = map_int(nums, (int x) => x * 2);
int[] evens   = filter_int(nums, (int x) => x > 1);
```

#### Lambdas & Static Function Lifting:
- Non-capturing lambdas are lifted at compile time into static C functions (`static int __lambda_0(int x) { return x * 2; }`).
- Call sites are lowered directly to bare C function pointers with **zero runtime overhead**.
- `outer_scopes` compile-time checking guarantees lexical isolation by rejecting references to outer local variables.

### 4. Exception Handling (`try` / `catch` / `throw`)
`myc` implements structured exception handling using a frame stack and `setjmp`/`longjmp`.

```c
try {
    if (file_exists("config.json") == 0) {
        throw "Configuration file is missing!";
    }
} catch (string err) {
    print("Handled error: " + err);
}
```

#### Zero-Leak Unwinding via Boehm GC:
In standard C, `longjmp()` skips stack frames and leaks memory. Because `myc` uses Boehm GC, intermediate allocations abandoned during a long jump are automatically swept up on subsequent GC cycles.

#### Frame Balance Protection:
The code generator tracks active exception frames. If a `return`, `break`, or `continue` executes from inside a `try` block, active exception frames are popped before returning or jumping, preventing stack corruption.

### 5. Module System & Circular Import Detection
Programs can be split across multiple files using `import "path.src";`:
- **Relative Path Resolution**: Paths are resolved relative to the importing file's directory.
- **Diamond Import Deduplication**: Shared dependencies are loaded and parsed only once.
- **Cycle Detection**: Circular dependency graphs (`a.src -> b.src -> a.src`) are detected during loading and abort with a compiler error before infinite recursion can occur.

### 6. Arrays & Runtime Safety (NPE & Bounds Protection)
Arrays are typed heap objects:
```c
string[] names = new string[3];
names[0] = "Alice";
print("Length: " + names.length);
```

`myc` guards every pointer dereference and array access:
- **Null Pointer Protection**: Every method call, field access, array indexing, or function pointer call evaluates through `__check_null()`. Accessing a `null` reference cleanly aborts with:
  `NullPointerException: Cannot index null array`
- **Array Bounds Checking**: Array indices are validated against `length` through `__bounds_check()`. Out-of-bounds accesses safely abort with:
  `Error: Array index 5 out of bounds (length 3)`

### 7. Standard Library & CLI Arguments
`myc` includes a built-in runtime standard library:
- **File I/O**: `read_file(path)`, `write_file(path, content)`, `file_exists(path)`, `remove_file(path)`
- **String Utilities**: `str_sub(str, start, end)`, `str_len(str)`, `str_to_int(str)`
- **String Concatenation**: `+` seamlessly concatenates `string + string`, `string + int`, and `int + string`
- **CLI Arguments**: `int main(string[] args)` receives command-line parameters converted into a safe `string[]` array

---

## Real-World Showcase: Markdown-to-HTML CLI (`md2html.src`)

To demonstrate the power and stability of `myc`, a complete, real-world command-line tool was built entirely in `.src`:

**[`md2html.src`](file:///home/rockson/Downloads/ROCKSON/md2html.src)**
- **Architecture**:
  - Abstract `Block` base class with virtual `to_html()` method.
  - Polymorphic subclasses: `HeaderBlock`, `ParagraphBlock`, `CodeBlock`, `QuoteBlock`, `ListBlock`, `HorizontalRuleBlock`.
  - Inline formatting parser for `**bold**`, `*italic*`, `` `code` ``, `[link](url)`, and HTML escaping (`&`, `<`, `>`, `"`).
- **Subsystems Exercised**:
  - Dynamic VTable dispatch across polymorphic block lists.
  - Higher-order array functional algorithms via [`lib_array.src`](file:///home/rockson/Downloads/ROCKSON/lib_array.src).
  - CLI argument handling and file reading/writing.
  - Garbage collector under continuous allocation of thousands of string nodes.

```bash
$ ./myc md2html.src -o md2html
[myc] Build successful -> ./md2html

$ ./md2html test_doc.md output.html
Converted test_doc.md -> output.html
```

---

## Compiler Internals & Pipeline

The compiler is implemented cleanly in Python 3 with zero external dependencies:

```
├── myc                 # Executable compiler CLI driver
├── module_loader.py    # Multi-file module loader & cycle detector
├── lexer.py            # Tokenizer specification & token generation
├── parser.py           # AST definitions & recursive descent parser
├── typechecker.py      # Semantic analysis, type inference & checks
├── codegen.py          # ANSI C code generation & runtime synthesis
├── test_runner.py      # Automated test runner with timing & reporting
├── lib_array.src       # Standard array library (map, filter, fold, join)
└── md2html.src         # Showcase Markdown-to-HTML CLI converter
```

---

## Test Suite & Verification

The repository includes **53 test files** comprising **46 automated test suites** and **7 reusable modules**. Tests validate both positive execution behavior and negative compiler diagnostics.

```bash
$ ./test_runner.py
Running Compiler Test Suite (53 tests)
──────────────────────────────────────────────────
  [PASS] bad_break.src             (37.8 ms)
  [PASS] bad_catch_type.src        (28.6 ms)
  [PASS] bad_concat.src            (35.9 ms)
  [PASS] bad_continue.src          (30.6 ms)
  [PASS] bad_fn_call_non_fn.src    (30.9 ms)
  [PASS] bad_fn_ptr_type.src       (30.9 ms)
  [PASS] bad_import_missing.src    (32.7 ms)
  [PASS] bad_lambda_capture.src    (28.0 ms)
  [PASS] bad_lambda_capture_func.src (33.0 ms)
  [PASS] bad_lambda_capture_this.src (30.9 ms)
  [PASS] bad_lambda_type.src       (28.9 ms)
  [PASS] bad_main_ret.src          (39.0 ms)
  [PASS] bad_main_sig.src          (30.3 ms)
  [PASS] bad_method.src            (28.4 ms)
  [PASS] bad_null_int.src          (30.0 ms)
  [PASS] bad_null_string.src       (28.6 ms)
  [PASS] bad_override.src          (31.5 ms)
  [PASS] bad_stdlib_args.src       (35.2 ms)
  [PASS] bad_throw_type.src        (32.1 ms)
  [PASS] bad_type.src              (28.9 ms)
  [PASS] branch.src                (63.3 ms)
  [PASS] circ_a.src                (31.0 ms)
  [SKIP] circ_b.src                (module)
  [SKIP] common_point.src          (module)
  [PASS] game.src                  (66.7 ms)
  [SKIP] lib_array.src             (module)
  [SKIP] lib_entity.src            (module)
  [SKIP] lib_math.src              (module)
  [PASS] md2html.src               (94.4 ms)
  [SKIP] mod_a.src                 (module)
  [SKIP] mod_b.src                 (module)
  [PASS] sample.src                (81.8 ms)
  [PASS] test_args.src             (63.7 ms)
  [PASS] test_args_array.src       (80.8 ms)
  [PASS] test_array_lib.src        (72.9 ms)
  [PASS] test_bounds.src           (57.0 ms)
  [PASS] test_diamond.src          (63.7 ms)
  [PASS] test_exceptions.src       (71.5 ms)
  [PASS] test_features.src         (65.1 ms)
  [PASS] test_file_io.src          (59.9 ms)
  [PASS] test_fn_ptr.src           (61.1 ms)
  [PASS] test_for_gc.src           (59.0 ms)
  [PASS] test_import.src           (70.0 ms)
  [PASS] test_lambda.src           (75.8 ms)
  [PASS] test_npe_array.src        (59.8 ms)
  [PASS] test_npe_field.src        (65.3 ms)
  [PASS] test_npe_fn.src           (61.1 ms)
  [PASS] test_npe_method.src       (63.2 ms)
  [PASS] test_null.src             (57.8 ms)
  [PASS] test_stdlib_str.src       (62.8 ms)
  [PASS] test_string.src           (60.0 ms)
  [PASS] test_unhandled_exception.src (70.4 ms)
  [PASS] test_vtable.src           (70.0 ms)
──────────────────────────────────────────────────
ALL 46 TESTS PASSED (7 modules skipped) in 2.34s
```

---

## Quickstart & Usage Guide

### Prerequisites
- Python 3.8+
- GCC (GNU C Compiler)
- Boehm Garbage Collector (`libgc-dev` on Debian/Ubuntu, `gc` on macOS Homebrew)

```bash
# Ubuntu / Debian
sudo apt-get install build-essential libgc-dev

# macOS Homebrew
brew install bdw-gc
```

### Compiling and Running Programs

```bash
# 1. Compile a .src file into a native binary
./myc my_program.src -o my_program

# 2. Run the compiled executable
./my_program

# 3. View the generated intermediate C code
./myc my_program.src --emit-c
```

### Running the Test Suite

```bash
python3 test_runner.py
```
