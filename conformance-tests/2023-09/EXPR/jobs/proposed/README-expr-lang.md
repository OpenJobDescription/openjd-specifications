# Proposed EXPR fixtures (expression language) — jobs

Kind-level parking (`<component>/<kind>/proposed/`); promotion is a move up
one directory. The runner does not scan `proposed/`. Named per fixture
family because other expected-failures PRs park fixtures here with their
own READMEs.

### `expr2.1.1--int64-max-task-range.test.yaml`

- Requires: task parameter range element 2^63−1 = 9223372036854775807
  **accepted** (Expression Language §1.2.1: int covers −2⁶³ to 2⁶³−1).
- Observed: **rs rejects** at template validation — `INT parameter 'Big'
  range expression error: Integer overflow: result is outside the 64-bit
  signed range`. Probing shows single-element ranges are accepted at
  4611686018427387903 (2^62−1) and rejected from 4611686018427387904 (2^62)
  upward, suggesting an internal computation (e.g. a length or midpoint
  calculation) overflows before the value itself is range-checked.
  **py passes** (accepts the valid value).
- Classification: openjd-rs implementation bug (false reject inside the
  valid int64 domain). Fixing it widens acceptance only. Promote together
  with `../job_templates/proposed/expr2.1.1--int64-overflow-task-range` —
  until this accept twin is green on rs, that reject twin passes on rs for
  possibly the wrong reason (the same 2^62 cap). The job-parameter accept
  twins at 2^63−1 are `expr2.1.1--int64-max-param-values.test.yaml` in the
  expr-lang-gaps PR.
