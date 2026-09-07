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
- [ ] Implement deterministic left-to-right expression evaluation: lower all side-effecting multi-expression constructs (binary operands, function arguments, method receiver then arguments, constructor arguments, array receiver/index, and other multi-expression lowering contexts) through unique compiler temporaries so source evaluation order is deterministic and each sub-expression is evaluated exactly once. Current codegen inherits C evaluation order; array index expressions may currently be evaluated twice. (H-08)
- [ ] Reject multiple constructors per class with clear diagnostic (H-06)
- [ ] Define and implement source-language integer arithmetic semantics that prevent ordinary accepted programs from invoking signed-C UB. Cover explicitly: signed addition overflow, signed subtraction overflow, signed multiplication overflow, unary negation overflow (`-INT_MIN`), division by zero, modulo by zero, `INT_MIN / -1`, and `INT_MIN % -1`. The final overflow policy (trap / wrap / saturate) must be resolved in an ADR before implementation. (H-03)
- [ ] Add volatile annotations or explicit frame propagation for setjmp-clobbered locals (H-02)
- [ ] Implement symbol safety covering the full compiler-owned and runtime namespace: C keywords, C reserved identifiers, compiler-generated function/constructor/method names (`myc_gen_*`, `myc_gen_new_<Class>`, `myc_gen_init_<Class>`), compiler-generated temporaries (`myc_tmp_*`), runtime helper names (`myc_rt_*`), hidden object fields (`vptr`, `base`), and lambda/closure helper symbols. The compiler-owned namespace prefix must not itself violate C reserved-identifier rules. Contract: `RAW USER C SYMBOLS = NO`. (H-07)
- [ ] Align member resolution order between TypeChecker and CodeGenerator (H-10, H-11)
- [ ] Remove independent type inference and semantic re-resolution from codegen.py (H-10, H-11, M-04)
- [ ] Emit consistent implicit upcasts for class arguments and returns (H-12)
- [ ] Reject contextually invalid types and unsupported storage forms, including `void` variables, fields, parameters where forbidden, `void[]`, and unsupported function-array/storage forms (H-05)
- [ ] Add regression tests for evaluation order (planning only — do not create .src files in docs PRs): test_binary_eval_order.src, test_function_arg_eval_order.src, test_method_eval_order.src, test_constructor_arg_eval_order.src, test_index_eval_once.src
- [ ] Add regression tests for integer arithmetic UB (planning only — do not create .src files in docs PRs): test_int_add_overflow.src, test_int_sub_overflow.src, test_int_mul_overflow.src, test_int_neg_overflow.src, test_int_div_zero.src, test_int_mod_zero.src, test_int_min_div_neg1.src
- [ ] Add regression tests for symbol safety (planning only — do not create .src files in docs PRs): bad_symbol_c_keyword.src, bad_symbol_vptr.src, bad_symbol_base.src, bad_symbol_runtime_helper.src, bad_symbol_generated_ctor.src
- [ ] Add regression tests: bad_missing_return.src, bad_partial_return.src, test_negative_array_size.src, test_huge_array_size.src, test_setjmp_modified_local.src, test_implicit_upcast.src
- [ ] Add regression tests: bad_void_variable.src, bad_void_field.src, bad_void_array.src, bad_void_param.src

---

## P2 — Later / Backlog
- [ ] Design structured Type object hierarchy replacing string type names
- [ ] Implement Typed HIR intermediate representation between TypeChecker and CodeGenerator
- [ ] Decode string escape sequences in lexer/frontend
- [ ] Configure CI test matrix for GCC/Clang with UBSan

---

## Done
<!-- Move completed tasks here once merged into dev -->

---

> **Agent rule:** Every task MUST start with a verb: Create / Add / Fix / Remove / Configure / Write / Update
> Tag today's tasks with `[TODAY]` at morning standup. Max 3 per day.
