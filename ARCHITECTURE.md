# Architecture — myc (ROCKSON) (Compiler / Language Tooling)

> Created by: Compiler Reviewer / Antigravity Agent
> Reviewed by: Rockson
> Last updated: 2026-09-07
> Project type: Compiler / language tooling
> Structure reference: `templates/STRUCTURE.compiler.template.md`

---

## Current State

`myc` is a functioning compiler prototype written in Python 3 that compiles object-oriented `.src` programs to GNU C11 backed by the Boehm Garbage Collector (`libgc`). It features classes, single inheritance, virtual dispatch via prefix-compatible VTables, first-class functions, anonymous lambdas, `setjmp`/`longjmp` exceptions, typed arrays, strings, modules, and built-in runtime guards (`__check_null`, `__bounds_check`).

While 46 automated test suites currently pass (53 `.src` files: 46 runnable, 7 reusable modules), an in-depth soundness audit identified critical P0 and P1 vulnerabilities at phase boundaries:
- **C-01 (P0)**: `array.length` is writable as an arbitrary assignment target, allowing bounds checks to be bypassed and causing out-of-allocation writes.
- **C-02 (P0)**: Uninitialized locals emit uninitialized C scalars/pointers, causing indeterminate pointers that defeat null checks and violate non-null string invariants.
- **C-03 (P0)**: Block scopes leak in `TypeChecker.current_scope` across `if`, `while`, and `try` blocks, allowing inner declarations to pollute outer symbol tables and cause C miscompilations.
- **C-04 (P0)**: Function parameter covariance accepts incompatible function-pointer assignments without adapter thunks.
- **C-05 (P0)**: Virtual method overrides are called through casted C function pointers with mismatched receiver signatures, invoking C undefined behavior.
- **C-06 (P0)**: `this = null` is permitted by semantic analysis while codegen deliberately skips null checks on `this`.
- **P1 Findings**: H-01 (non-void functions need not return), H-02 (`setjmp`/`longjmp` modified locals may be clobbered), H-03 (source inherits C signed overflow and div-by-zero UB), H-04 (negative/overflowing array allocation lengths), H-05 (`void` variables and unsupported storage types pass validation), H-06 (multiple constructors parsed but emitted with identical C names), H-07 (unmangled user identifiers colliding with C keywords), H-08 (array index expressions evaluated twice), H-09 (duplicate local/parameter/member symbols allowed), H-10/H-11 (member resolution order mismatch and inherited function fields), H-12 (implicit class upcasts not lowered consistently).
- **M-01 through M-05**: Generated C is GNU C11 rather than ANSI C; string escape decoding is delegated to C; exception state is global and single-threaded; `codegen.py` independently reinfers types; and the compiler driver previously lacked warning/optimization flags.

---

## Target State (Milestone v0.1)

The target release is `myc v0.1.0-soundness`. Every program accepted by semantic analysis must either execute according to defined semantics or terminate through a defined runtime failure; accepted source must not rely on C undefined behavior for ordinary language operations.

---

## Compilation Pipeline

### Current Pipeline
```text
myc Source (.src) → ModuleLoader → Lexer → Parser (AST) → TypeChecker → CodeGenerator (reinfers types) → GCC (-O2) → Binary
```

### Target Pipeline Architecture

```text
myc Source Files (.src)
          │
          ▼
ModuleLoader (module_loader.py)
  - Canonical path resolution & deduplication
  - Circular import cycle detection
          │
          ▼
Lexer & Parser (lexer.py, parser.py)
  - Tokenization with source spans
  - Recursive descent parser
  - Program AST
          │
          ▼
Resolver & TypeChecker (typechecker.py)
  - Lexical Scope Stack (no leakage across blocks)
  - Place/Lvalue mutability validation
  - Full function-type invariance
  - Definite-return analysis
          │
          ▼
[Target HIR: Typed Intermediate Representation]
  - Symbol IDs
  - Structured Type objects
  - Resolved member & constructor IDs
  - Explicit implicit upcast conversions
  - Writable Place metadata
          │
          ▼
Lowering & Code Generator (codegen.py)
  - Consumes resolved typed facts only
  - Zero semantic name lookup or type re-inference
  - Deterministic left-to-right evaluation order
  - Exact-signature adapter thunks for VTable overrides
  - Unique temporary generation (gensym)
          │
          ▼
Generated GNU C11
          │
          ▼
GCC / Clang Backend Driver
  gcc -O2 source.tmp.c -lgc -o binary
          │
          ▼
Native Executable Binary
```

### Architectural Rules
1. **`codegen` must not become a second semantic analyzer**: Code generation consumes resolved, typed semantic information and performs lowering only.
2. **Phase Boundary Separation**: Semantic analysis validates all language invariants; unsupported constructs must fail with clean diagnostics rather than leaking to GCC.

---

## Frontend

### Lexer (`lexer.py`)
- Token model: Regular-expression-based token stream.
- Source tracking: Line numbers recorded on tokens. Column and span tracking targeted for Phase 2.
- String literals: Currently preserves raw quote tokens. Frontend escape decoding targeted for Phase 2.
- MUST NOT perform semantic name resolution.

### Parser / AST (`parser.py`)
- Parsing strategy: Precedence-climbing recursive descent.
- AST nodes: Plain dataclasses representing expressions and statements.
- Place grammar: Current AST does not distinguish lvalues from rvalues syntactically; semantic analysis must enforce Place legality.
- MUST NOT perform backend-specific lowering.

---

## Semantic Analysis (`typechecker.py`)

### Resolver & Scope Model
- Scope representation: Stack of lexical scope dictionaries (`ScopeStack`).
- Block isolation: Entering `then`, `else`, `while`, `for`, `try`, and `catch` blocks pushes a new lexical frame; exiting pops it.
- Duplicates & Shadowing: Re-declaring a symbol within the *same* immediate lexical frame is rejected. Shadowing outer scopes is permitted.

### Type System
- Representation: String-based type identifiers for v0.1 (`int`, `string`, `void`, `ClassName`, `T[]`, `ret_t(param_t...)`), migrating to structured `Type` objects in Phase 2.
- Function Type Invariance: For v0.1, function types are strictly invariant across both parameters and return types (`Type A == Type B`).
- Legality: `void` is valid only as a function/method return type or constructor return type. `void` variables, `void` fields, and `void[]` array types are rejected.
- Place / Lvalue Model:
  - **Writable Places**: Identifiers (local variables, parameters excluding `this`), member access (`obj.field` where `field != "length"` and field is not a method), array elements (`arr[idx]`).
  - **Read-Only / Non-Places**: `this`, `arr.length`, literals, function calls, function symbols, binary expressions.

### Control-Flow Analysis
- Definite-Return: Non-void functions, methods, and block lambdas must terminate on all reachable control-flow paths with a `return` or `throw`.

---

## Typed HIR / IR

The planned Typed HIR represents the boundary where semantic checking ends and lowering begins.

Each typed node will carry:
- Expression type
- Resolved symbol/member/constructor ID
- Place/lvalue category and mutability
- Implicit conversion annotations
- VTable slot offsets
- Source span for diagnostic attribution

**Migration Plan**: Current direct AST lowering in `codegen.py` will be refactored to eliminate independent name resolution and type inference before adding new language features.

---

## Backend / Target Lowering (`codegen.py`)

- **Target Standard**: GNU C11 (utilizing `__extension__({ ... })` and flexible array members).
- **Evaluation Order**: Planned deterministic left-to-right expression lowering. Array indexing must evaluate receiver and index once into temporaries.
- **Temporary Generation**: Unique compiler-generated temporaries (`gensym`).
- **Implicit Upcasts**: Explicit C pointer casts `(Base*)` emitted whenever a `Derived` instance is supplied to a `Base` context.

---

## Object Model & Dispatch

### Class Layout
- Struct embedding: Single inheritance embeds the parent struct as the first member (`Base base;`), enabling zero-cost pointer upcasts.

### Virtual Dispatch & VTable ABI
- VTable Layout: Prefix-compatible static VTables with function-pointer slots.
- **Exact-Signature Thunks (C-05 Fix)**: Overridden methods generate static adapter thunks matching the base receiver signature:
  ```c
  static void __thunk_Warrior_take_damage(Entity* self, int amount) {
      Warrior_take_damage((Warrior*) self, amount);
  }
  ```
  The thunk is assigned to the VTable slot, eliminating incompatible C function pointer invocations.

---

## Runtime Model

### Memory Management
- Backed by Boehm GC (`libgc`).
- Pointer structures allocated via `GC_MALLOC`; pointer-free leaf data (strings) allocated via `GC_MALLOC_ATOMIC`.
- Deterministic initialization (target):
  - `int` → `0`
  - `string` → `""`
  - References (`class`, `array`, `function`) → `NULL`

### Arrays
- Representation: `typedef struct { int length; T data[]; } Array_T;`
- Safety: `length` is read-only. Dynamic allocation guards against negative sizes (`size < 0`) and multiplication overflow.
- Access: `__bounds_check(index, length)` validates indices at runtime.

### Exceptions
- Mechanism: Frame stack with `setjmp` / `longjmp`.
- Unwinding: Abandoned allocations are reclaimed by Boehm GC without memory leaks.
- Concurrency scope: Single-threaded v1 runtime using static global frame state (`__top_frame`).

---

## Safety & Semantic Invariants

| Invariant | Current State | Target State | Verification Method |
|---|---|---|---|
| Assignment targets resolve to writable places only | **NOT MET** (C-01, C-06 open) | PASS | `bad_assign_length.src`, `bad_assign_this.src`, `bad_assign_literal.src` |
| Array metadata (`length`) cannot be mutated from source | **NOT MET** (C-01 open) | PASS | `bad_assign_length.src` |
| No indeterminate target-language locals/fields/elements | **NOT MET** (C-02 open) | PASS | `test_uninitialized_object.src`, `test_uninitialized_string.src` |
| Function values use ABI-compatible signatures (invariance) | **NOT MET** (C-04 open) | PASS | `bad_fn_variance_param.src`, `bad_fn_variance_return.src` |
| VTable calls use exact-signature thunks (no C UB) | **NOT MET** (C-05 open) | PASS | Generated C code review + UBSan test pass |
| Non-void functions return/throw on all paths | **NOT MET** (H-01 open) | PASS | `bad_missing_return.src`, `bad_partial_return.src` |
| Array allocation rejects negative/overflow lengths | **NOT MET** (H-04 open) | PASS | `test_negative_array_size.src`, `test_huge_array_size.src` |
| Array indexing evaluates index expressions exactly once | **NOT MET** (H-08 open) | PASS | `test_index_eval_once.src` |
| Integer division by zero is safely trapped | **NOT MET** (H-03 open) | PASS | `test_div_zero.src` |
| Backend does not repeat semantic name resolution | **NOT MET** (H-10, M-04 open) | PASS | Architecture & code review |

---

## Generated-Target Contract

- Target standard: GNU C11
- Required runtime: Boehm GC (`<gc.h>`)
- Undefined behavior policy: Accepted source MUST NOT depend on target-language UB for ordinary language semantics.
- Target compiler flags: `-O2 -std=gnu11`

---

## Project Structure

> Canonical reference: `templates/STRUCTURE.compiler.template.md`.
> Active Structure Decision: **STR-01** (flat repository root retained during v0.1 stabilization).

### Layer Ownership

| Layer | Owns | MUST NOT |
|---|---|---|
| Lexer | Tokenization, source lines/spans | Resolve names or infer types |
| Parser / AST | Syntax tree construction | Perform target lowering or emit C |
| Resolver / TypeChecker | Symbols, scopes, types, Place mutability, conversions | Emit target C code |
| Typed HIR / IR | Resolved typed nodes, semantic contract | Re-parse source or repeat name lookup |
| Codegen / Lowering | Target C representation | Invent semantic facts or re-resolve symbols |
| Runtime | Memory allocation, bounds checks, exceptions | Depend on user source names |
| Tests | Semantic, runtime, and ABI regression coverage | Rely only on happy-path output |

---

## Architecture Decision Records (ADRs)

| ID | Date | Decision | Rationale |
|---|---|---|---|
| **ARCH-01** | 2026-09-07 | Target GNU C11 with Boehm GC Backend | Leverages conservative GC and native C performance. |
| **ARCH-02** | 2026-09-07 | Enforce Full Function Type Invariance for v0.1 | Prevents unsound function calls and C ABI UB. |
| **ARCH-03** | 2026-09-07 | Generate Exact-Signature Adapter Thunks for VTables | Eliminates incompatible function pointer calls in C. |
| **ARCH-04** | 2026-09-07 | Introduce Place/Lvalue Model for Assignment Targets | Protects `arr.length` and `this` from being overwritten. |
| **ARCH-05** | 2026-09-07 | Replace Flat Scope Dictionary with Lexical Scope Stack | Isolates variables to block scopes (`if`, `while`, etc.). |
| **ARCH-06** | 2026-09-07 | Deterministic Default Initialization for Scalars/Refs | Eliminates uninitialized C stack garbage. |

### Structure ADRs

| ID | Date | Decision | Rationale |
|---|---|---|---|
| **STR-01** | 2026-09-07 | Flat Root Structure Retained During v0.1 Stabilization | Keeps existing 53 test files and modules stable during critical P0/P1 soundness fixes before migrating to canonical `src/` directory layout in Phase 2. |

---

## Target Release & Soundness Gate (Milestone v0.1)

> **Target Gate**: All items below must be satisfied before `myc v0.1.0` is released.

```text
SOURCE UNSOUNDNESS         = NONE KNOWN
WRITABLE ARRAY METADATA    = NO
UNINITIALIZED C VALUES     = NO
FUNCTION POINTER TYPE UB   = NO
VTABLE CALL TYPE UB        = NO
MISSING RETURN UB          = NO
INTEGER UB                 = NO
ARRAY SIZE OVERFLOW        = GUARDED
BLOCK SCOPE DIVERGENCE     = NO
CODEGEN TYPE REINFERENCE   = NO
RAW USER C SYMBOLS         = NO
SETJMP LOCAL CLOBBER       = HANDLED
GCC -O2 TESTS              = PASS
CLANG -O2 TESTS            = PASS
UBSAN                      = PASS
```

---

## Verification Matrix

| Configuration | Target Requirement | Verification Command |
|---|---|---|
| Canonical test runner | PASS | `python3 test_runner.py` |
| GCC Debug Config (-O0) | PASS | `./myc sample.src -o sample_bin` |
| Clang Optimized Config (-O2) | PASS | `CC=clang python3 test_runner.py` |
| Undefined Behavior Sanitizer | PASS | `gcc -fsanitize=undefined -O2 ...` |

---

## Constraints

- Planning docs and architecture changes follow `guides/BLUEPRINT_GUIDE.md`.
- Branch/approval flow follows `SOLO_DEV_WORKFLOW.md`.
- Source-language safety claims MUST match implemented and verified invariants.
- Unsupported language constructs MUST be rejected cleanly rather than delegated accidentally to the target compiler.
- Generated target code MUST be tested under optimization, not only debug builds.
