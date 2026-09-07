# Future Roadmap — myc (ROCKSON)

---

## Phase 1 — Stabilize (Milestone v0.1)

> Goal: Eliminate all known P0 and P1 soundness vulnerabilities; ensure no accepted source program invokes C undefined behavior.

- [ ] **P0-01: Place / Lvalue Model** — Validate assignment targets in `TypeChecker`; make `array.length`, `this`, literals, and calls non-assignable (C-01, C-06).
- [ ] **P0-02: Lexical Scope Stack** — Implement true lexical scope frames for `if`, `else`, `while`, `for`, `try`, `catch`; reject duplicate declarations in the same scope (C-03, H-09).
- [ ] **P0-03: Deterministic Initialization** — Default initialize all scalars, references, and strings (`int: 0`, `string: ""`, pointers: `NULL`); enforce non-null string elements in arrays (C-02).
- [ ] **P0-04: Full Function-Type Invariance** — Require structural invariance for both parameters and return types on function-value assignment (C-04).
- [ ] **P0-05: VTable ABI Thunks** — Generate exact-signature wrapper thunks for virtual method overrides to eliminate function-pointer cast UB (C-05).
- [ ] **P1-01: Definite-Return Analysis** — Verify non-void functions and methods terminate on all reachable control-flow paths (H-01).
- [ ] **P1-02: Safe Array Allocation** — Validate `length >= 0` and guard against allocation byte-size integer overflow in `NewArrayExpr` (H-04).
- [ ] **P1-03: Single-Evaluation Array Indexing** — Lower array indexing expressions through temporaries to evaluate side-effecting indices exactly once (H-08).
- [ ] **P1-04: Single-Constructor Restriction** — Explicitly reject multiple constructors per class until constructor overloading is supported (H-06).
- [ ] **P1-05: Division-by-Zero Trapping** — Guard integer division and modulo against division-by-zero (H-03).
- [ ] **P1-06: setjmp Local Preservation** — Ensure automatic variables modified in `try` blocks are declared `volatile` or lowered safely (H-02).
- [ ] **P1-07: Symbol Mangling** — Prevent user identifiers from colliding with C keywords or generated runtime names (H-07).
- [ ] **P1-08: Remove Codegen Semantic Re-inference** — Unify member and type resolution so backend does not re-infer or diverge from semantic analysis (H-10, H-11).
- [ ] **P1-09: Contextual Type Legality** — Reject contextually invalid types and unsupported storage forms: `void` variables, fields, parameters where forbidden, and `void[]` arrays (H-05).
- [ ] **Compiler Hardening** — Validate test suite across GCC `-O0`, GCC `-O2`, Clang `-O2`, and UBSan once driver flag selection is wired.

---

## Phase 2 — Modernize

> Goal: Introduce structured compiler data structures, Typed HIR, and source span tracking.

- [ ] **Structured Type System** — Replace string-encoded types with first-class `Type` object hierarchy (`IntType`, `StringType`, `ClassType`, `ArrayType`, `FunctionType`).
- [ ] **Typed HIR (High-Level Intermediate Representation)** — Establish an explicit intermediate representation between `TypeChecker` and `CodeGenerator` carrying symbol IDs, place mutability, and conversions.
- [ ] **Source Spans & Diagnostic Reporting** — Track file, line, and column spans across all AST nodes for rich compiler error formatting.
- [ ] **Explicit Implicit Conversion Nodes** — Lower class upcasts through explicit AST/HIR conversion nodes.
- [ ] **Frontend String Escape Decoding** — Parse and validate string escape sequences (`\n`, `\t`, `\"`, `\\`) in the frontend rather than passing raw strings to C.
- [ ] **Directory Layout Restructuring** — Migrate flat repository root to canonical `src/frontend`, `src/semantic`, `src/codegen`, `tests/` structure per `STRUCTURE.compiler.template.md`.

---

## Phase 3 — Scale

> Goal: Language expressiveness, concurrency, and performance optimization.

- [ ] **Capturing Closures** — Support lambda lexical closures with heap-allocated environment frames.
- [ ] **Method & Constructor Overloading** — Implement arity and type-based overload resolution.
- [ ] **Interfaces / Multiple Subtyping** — Introduce interface definitions and interface table dispatch.
- [ ] **Thread-Safe Runtime** — Transition exception runtime to thread-local storage (`_Thread_local`) with multi-threaded Boehm GC initialization.
- [ ] **Standard Library Expansion** — Add rich collections (hash maps, lists), networking, and process management.
- [ ] **Formal Language Specification** — Author complete syntax and semantic grammar reference manual.

---

## Icebox (no timeline)

- [ ] Self-hosting `myc` compiler written in `myc`.
- [ ] LLVM backend code generator.
- [ ] Generics / parameterized types.
