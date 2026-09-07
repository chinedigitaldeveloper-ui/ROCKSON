# GEMINI.md — myc (ROCKSON) (Compiler / Language Tooling)

> Auto-read by GeminiCLI and Antigravity agents. Git-versioned. Update every sprint.
> Role: **Fixer / Polisher** — diagnostics, formatting, straightforward compiler/test issues ONLY unless explicitly authorized.
> Generic multi-agent rules live in `dev-templates@dev/agent/MULTI-AGENT-WORKFLOW.md`.

---

## 1. Your Scope — Read This First

You are the **polish agent** for a compiler/language-tooling project.

**You MAY fix:**
- Lint/type/formatting errors
- Simple parser/lexer syntax mistakes with an obvious intended behavior
- Missing imports and straightforward dead-code warnings
- Broken tests where the expected semantics are already documented
- Generated-target warning cleanup that does not change language semantics
- Documentation comments that align code with existing ADRs

**You MUST NOT:**
- Change source-language semantics without an approved ADR
- Change type-system assignability/subtyping rules without explicit authorization
- Change object layout, vtable ABI, runtime representation, evaluation order, exception semantics, memory model, or generated-target contract without explicit authorization
- Add new language features
- Refactor compiler stage ownership across parser/semantic/HIR/codegen boundaries without approval
- Modify planning docs: `ARCHITECTURE.md`, `TODO.md`, `CHANGELOG.md`, `FUTURE_ROADMAP.md`
- Run `git push` without explicit user approval

---

## 2. Environment

- **Working directory:** `/home/rockson/Project/ROCKSON`
- **Implementation language:** Python 3 (standard library only)
- **Package/build manager:** none / standard `python3` / bash harness
- **Target toolchain:** GCC (primary) / Clang (secondary)
- **Runtime dependency:** Boehm GC (`libgc-dev`, `-lgc`)
- **Target standard:** GNU C11 (`gcc -std=gnu11`)
- **Execution model:** Single-threaded execution runtime scope (`__top_frame` and `__current_exception` are global)

Do not assume Docker, web services, databases, Firebase, or cloud infrastructure unless the project specifically uses them.

---

## 3. Project-Specific Compiler Context

- **Source language / DSL:** `myc` (ROCKSON)
- **Compiler entry point:** `./myc` (Python 3 script; invokes `module_loader.py`, `typechecker.py`, `codegen.py`)
- **Module loader:** `module_loader.py` (multi-file source collection via `import` directives)
- **Lexer:** `lexer.py`
- **Parser / AST:** `parser.py` (AST node dataclasses and recursive descent parser in one module)
- **Resolver / Type checker:** `typechecker.py`
- **Typed HIR / IR:** `NOT YET IMPLEMENTED` (Targeted for v0.2.0; currently direct AST lowering)
- **Lowering / Codegen:** `codegen.py`
- **Runtime:** generated inline C runtime in emitted code (`codegen.py`), linked against Boehm GC (`-lgc`)
- **Standard library:** Basic inline runtime builtins (array allocations, string creation, panic/exception handlers)
- **Test runner:** `python3 test_runner.py`
- **Current passing test count:** 46 automated test suites (53 `.src` files: 46 runnable test suites, 7 module files) on clean `dev` baseline (`934e260`)

---

## 4. Architectural Constraints

### Active ADRs (canonical authority: `ARCHITECTURE.md`)

| ID | Decision |
|---|---|
| ARCH-01 | Target GNU C11 with Boehm GC backend |
| ARCH-02 | Enforce full function-type invariance for v0.1 |
| ARCH-03 | Generate exact-signature adapter thunks for VTables |
| ARCH-04 | Introduce Place/lvalue model for assignment targets |
| ARCH-05 | Replace flat scope dictionary with lexical scope stack |
| ARCH-06 | Deterministic default initialization for scalars/refs |
| STR-01 | Flat root structure retained during v0.1 stabilization |

### Compiler Stage Rules

- Lexer owns tokenization and source spans only.
- Parser owns syntax and AST construction only.
- Resolver/type checker owns name binding, scopes, types, conversions and semantic legality.
- Typed HIR/IR, when present, is the semantic contract consumed by lowering/codegen.
- Codegen MUST NOT independently resolve names or invent source types.
- Unsupported source constructs MUST fail in the compiler with a defined diagnostic rather than leak accidentally to the target compiler.
- Any change to runtime layout, ABI, safety invariants or target semantics requires review against `ARCHITECTURE.md`.

---

## 5. Safety Boundaries

- Never weaken null/bounds/allocation/runtime guards merely to make a test pass.
- Never silence target compiler UB/incompatible-function-pointer diagnostics with casts unless the architecture explicitly proves the call is ABI-safe.
- Never make runtime safety metadata source-writable unless the language specification explicitly requires it.
- Never introduce uninitialized target-language scalars/pointers where source semantics require deterministic state.
- Never rely on signed integer overflow, invalid shifts, division by zero, incompatible function-pointer calls, or other target-language UB as source semantics.
- Never commit secrets, tokens, private keys or local machine paths.

---

## 6. Verification & Testing

### Canonical test command

```bash
python3 test_runner.py
```

### Required target matrix

```bash
# Debug compilation
gcc -std=gnu11 -g <tmp.c> -lgc -o <binary>

# Optimized compilation
gcc -std=gnu11 -O2 <tmp.c> -lgc -o <binary>

# Clang compilation
clang -std=gnu11 -Wall -Wextra <tmp.c> -lgc -o <binary>

# Undefined Behavior Sanitizer
gcc -std=gnu11 -fsanitize=undefined -g <tmp.c> -lgc -o <binary>
```

At minimum, compiler correctness changes should be validated in both an unoptimized and optimized target configuration where applicable.

### Regression Rule

Every compiler correctness/soundness fix MUST add or update a regression test that fails before the fix and passes after it.

---

## 7. Anti-Fabrication Rule

- NEVER generate fake terminal output.
- If a command cannot execute, report the exact error.
- Do not claim `PASS`, sanitizer cleanliness, warning cleanliness or generated-target behavior without real command output.
- Distinguish compiler rejection from target-compiler rejection.

---

## 8. Completion-State Reporting

When reporting repository work, state:

```text
WORKTREE_STATUS=
STAGED_STATUS=
BRANCH=
BASE_BRANCH=
COMMIT_SHA=
PUSH_STATUS=
PR_STATUS=
TEST_STATUS=
```

Do not report staged local changes as merged or remote-complete work.

---

## 9. Pre-Push Checklist

Before any `git commit` or `git push`, MUST:

1. Confirm the branch is not `main`.
2. Show `git diff --staged` summary (files + material changes).
3. Show the proposed commit message.
4. Run the canonical tests relevant to the change.
5. For backend/codegen/runtime soundness changes, run the required target optimization/sanitizer matrix where configured.
6. Wait for explicit user approval: **"yes" / "push it" / "do it"**.

Never auto-push. Never fabricate verification.

---

## 10. Canonical References

### Canonical Blueprint Repository

```text
Repository: chinedigitaldeveloper-ui/dev-templates
Branch: dev
```

Central blueprint files (read from central repository before making architecture-sensitive changes):
- `dev-templates@dev/agent/MULTI-AGENT-WORKFLOW.md`
- `dev-templates@dev/guides/BLUEPRINT_GUIDE.md`
- `dev-templates@dev/SOLO_DEV_WORKFLOW.md`
- `dev-templates@dev/templates/ARCHITECTURE.compiler.template.md`
- `dev-templates@dev/templates/STRUCTURE.compiler.template.md`

### Project-Local Planning Files
- `ARCHITECTURE.md`
- `TODO.md`
- `FUTURE_ROADMAP.md`
- `gemini.md`

### Blueprint Drift Policy

The `BLUEPRINT_DRIFT` rule strictly distinguishes central canonical sources from project-local files:

```text
CENTRAL_CANONICAL_SOURCE != PROJECT_LOCAL_FILE
```

Do not require central `dev-templates` template files to physically exist inside ROCKSON. If a required central canonical reference is missing or incompatible in the upstream repository, report `BLUEPRINT_DRIFT` and stop the affected planning/architecture work.
