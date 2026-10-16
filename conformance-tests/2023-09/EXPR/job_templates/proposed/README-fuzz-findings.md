# Expected failures from fuzzing openjd-rs

Spec-correct fixtures for bugs that fuzzing openjd-rs found
([openjd-rs#442](https://github.com/OpenJobDescription/openjd-rs/pull/442)) and
that openjd-rs has not fixed yet. They live in `proposed/` directories, which the
runner does not discover, so the suite stays green. Promote a fixture unchanged
into its parent directory when the fix lands in openjd-rs and, where noted below,
the spec states the rule it relies on.

Each fixture's header comment cites the spec text it relies on and says how
openjd-rs fails it.

## Fixtures

| Fixture | openjd-rs today | Needs spec text |
|---------|-----------------|-----------------|
| `base/job_templates/proposed/3.4.1.2--float-range-undefined-symbol.invalid.yaml` | Accepts an undefined `Param.*` in a FLOAT range | No |
| `EXPR/job_templates/proposed/expr2.1.8--range-expr-slice-negative-step.yaml` | Types `r[::-1]` as `range_expr`, so it rejects `r[::-1] * 2` | No |
| `EXPR/jobs/proposed/expr2.2.2--sum-empty-float-list.test.yaml` | `sum` of an empty `LIST[FLOAT]` returns the int `0` | No |
| `EXPR/jobs/proposed/expr2.1.8--empty-range-expr-slice-in-let.test.yaml` | An empty `range_expr` from a step `let` fails to reach the session | Clarify (see below) |
| `EXPR/job_templates/proposed/expr2.2.3--flatten-conditional-empty-branch.yaml` | Rejects `flatten(x if c else [])[0] + 1` | Union operands |
| `EXPR/job_templates/proposed/expr2.1.3--mul-conditional-union-operand.yaml` | Rejects `((n if c else ["a"]) * 2)[0]` | Union operands |
| `EXPR/job_templates/proposed/expr2.1.8--range-expr-slice-unknown-step.yaml` | Rejects `r[::Param.Step] * 2` | Union operands |
| `EXPR/jobs/proposed/expr2.1.5--path-plus-path-is-path.test.yaml` | Types `path + path` as `string` | Overload ranking |
| `EXPR/jobs/proposed/expr1.2.5--range-expr-equality-by-value.test.yaml` | Compares two `range_expr`s by structure | `range_expr` equality |
| `EXPR/job_templates/proposed/expr2.1.4--ordering-path-with-int.invalid.yaml` | Accepts `Param.Dir < 1` at validation | Validation-time detection |
| `EXPR/job_templates/proposed/expr1.2.1--host-scope-path-format-is-the-workers.yaml` | Folds host-scope path operations in the validating machine's format (POSIX only) | Host-scope folding |

## Spec questions

- **Union operands.** The spec says what an `if`/`else` with an unknown condition
  evaluates to (`unresolved[T | S]`), and that target-type coercion of a union
  "succeeds if at least one member can coerce". It does not say how an operator or
  function call dispatches on a union-typed operand. These fixtures assume the call is
  resolved per member, failing members are dropped, and it fails only if every member
  fails. That is the same rule the spec gives for an unknown condition's branches.
- **Overload ranking.** `path + path` matches `__add__(path, string)` by coercing one
  argument and `__add__(string, string)` by coercing both. The fixture assumes the
  overload needing fewer coercions wins. An explicit `__add__(p: path, suffix: path) ->
  path` row in §2.1.5 would also settle it.
- **`range_expr` equality.** §1.2.5 covers `list` vs `range_expr`, element by element,
  but not `range_expr` vs `range_expr`. The fixture assumes value equality.
- **Empty `range_expr`.** §2.2.1 says range expressions "must contain at least one
  value", but a clamped slice (§2.1.8) can select none. The fixture asserts only
  `len(...) == 0`. The spec should say whether such a slice is an empty `range_expr` or a
  `list[int]`.
- **Validation-time detection of ordering errors.** §2.1.4 makes mismatched ordering
  pairs an error. "Progressive Expression Evaluation" promises validation only for
  "type errors in constant subexpressions", so it does not say validation must catch
  this one. The fixture assumes it must, because the error does not depend on the
  parameter's value.
- **Host-scope folding.** Host scopes use the worker's path format, and validation
  fully evaluates the concrete parts of an expression. The fixture assumes that a
  path-format-dependent operation on literals in a host scope stays unresolved during
  validation. The spec says neither.
