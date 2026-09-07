# TODO — myc (ROCKSON) v0.1.0-dev

> Last updated: 2026-09-07

---

## Blockers
- [ ] None

---

## P0 — Must ship now
- [ ] [TODAY] Run `/graphify .` on repo root and commit `graphify-out/` to dev branch
- [ ] [TODAY] Run `graphify hook install` — enables free AST auto-rebuild on every git commit
- [ ] [TODAY] Copy `dev-templates@dev/guides/GRAPHIFY.skill.md` → `.agents/skills/graphify/ORG_RULES.md` in this repo
- [ ] Add Place/lvalue validation and make array.length and this non-assignable (C-01, C-06)
- [ ] Replace flat semantic scope tracking with lexical scope frames (C-03, H-09)
- [ ] Add deterministic defaults for uninitialized locals and strings (C-02)
- [ ] Enforce full function-type invariance across parameters and return types (C-04)
- [ ] Implement exact-signature adapter thunks for virtual method overrides in VTables (C-05)
- [ ] Add regression tests: bad_assign_length.src, bad_assign_this.src, bad_assign_literal.src, bad_assign_call.src
- [ ] Add regression tests: bad_scope_leak.src, bad_duplicate_local.src, bad_duplicate_param.src, bad_duplicate_field.src, bad_duplicate_method.src, test_shadow_scope.src
- [ ] Add regression tests: test_uninitialized_object.src, test_uninitialized_string.src, test_default_string_field.src, test_default_string_array.src
- [ ] Add regression tests: bad_fn_variance_param.src, bad_fn_variance_return.src

---

## P1 — Next sprint
- [ ] Implement definite-return analysis for non-void functions and methods (H-01)
- [ ] Add negative-length and size-overflow validation to array allocations (H-04)
- [ ] Lower array indexing with unique temporaries to evaluate index expressions once (H-08)
- [ ] Reject multiple constructors per class with clear diagnostic (H-06)
- [ ] Guard integer division and modulo against division-by-zero (H-03)
- [ ] Add volatile annotations or explicit frame propagation for setjmp-clobbered locals (H-02)
- [ ] Implement symbol mangling for user identifiers colliding with C keywords (H-07)
- [ ] Align member resolution order between TypeChecker and CodeGenerator (H-10, H-11)
- [ ] Emit consistent implicit upcasts for class arguments and returns (H-12)
- [ ] Reject contextually invalid types and unsupported storage forms, including `void` variables, fields, parameters where forbidden, `void[]`, and unsupported function-array/storage forms (H-05)
- [ ] Add regression tests: bad_missing_return.src, bad_partial_return.src, test_negative_array_size.src, test_huge_array_size.src, test_index_eval_once.src, test_setjmp_modified_local.src
- [ ] Add regression tests: bad_void_variable.src, bad_void_field.src, bad_void_array.src, bad_void_param.src

---

## P2 — Later / Backlog
- [ ] Design structured Type object hierarchy replacing string type names
- [ ] Implement Typed HIR intermediate representation between TypeChecker and CodeGenerator
- [ ] Remove independent type inference from codegen.py
- [ ] Decode string escape sequences in lexer/frontend
- [ ] Configure CI test matrix for GCC/Clang with UBSan

---

## Done
<!-- Move completed tasks here once merged into dev -->

---

> **Agent rule:** Every task MUST start with a verb: Create / Add / Fix / Remove / Configure / Write / Update
> Tag today's tasks with `[TODAY]` at morning standup. Max 3 per day.
