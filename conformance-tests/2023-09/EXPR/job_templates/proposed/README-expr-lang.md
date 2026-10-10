# Proposed EXPR fixtures (expression language) — job_templates

Fixtures listed here are spec-correct but parked instead of live, either
because a reference implementation has a known divergence that would fail
the suite, or because the normative spec text they test needs to be
restored first. Placement is kind-level (`<component>/<kind>/proposed/`)
so promotion is a mechanical move up one directory; the runner does not
scan `proposed/` directories. This README is named per fixture family
(`README-expr-lang.md`) because other expected-failures PRs park fixtures
in this same directory with their own READMEs.

Observations below are per-implementation: `rs` = openjd-rs CLI, `py` =
openjd-model/cli for Python. Dual-implementation results are from the
2026-08-12 sweep.

## Integer overflow on the parameter-value axis (blocked on spec restoration)

RFC 0005's normative "64-bit Signed Integer Type" section — the only text
stating that integer overflow is an error for literals, arithmetic, and
conversions — was dropped from the published `2026-02-Expression-Language.md`.
Only the type-table row in §1.2.1 ("int | 64-bit signed integer values (−2⁶³
to 2⁶³−1)") survives. These reject fixtures test behavior the published spec
arguably no longer requires, so they are parked until the spec text is
restored.

### `expr2.1.1--int64-overflow-param-default.invalid.yaml`

- Requires: INT job parameter `default: 9223372036854775808` (2^63) rejected
  at template validation.
- Observed: **accepted by BOTH rs and py** — `openjd check` exits 0. The
  YAML parser yields an arbitrary-precision integer and no range check is
  applied to parameter defaults.
- Classification: implementation bug in both (out-of-range acceptance),
  plus blocked on spec text restoration. Near-duplicate of the base
  expected-failures PR's `2.3--int-default-above-int64-max` — kept because
  the EXPR declaration could plausibly route through a different (typed)
  validation path; if the fix turns out to share one code path, drop this
  copy.

### expr2.1.1--int64-overflow-param-supplied (promoted)

- Verified green on BOTH implementations (each rejects a supplied
  job-parameter value of 2^63 at job creation), so this fixture ships as a
  live `jobs/` fixture in the expr-lang-gaps PR: it pins behavior both
  implementations already agree on, independent of spec-text restoration.

### `expr2.1.1--int64-overflow-task-range.invalid.yaml`

- Requires: task parameter range element 2^63 rejected.
- Observed: **rs rejects / py ACCEPTS** (2026-08-12 sweep) — this is a live
  Python defect, not a spec-blocked pass. (An earlier revision of this
  README claimed the fixture "passes today"; that was true only of rs, and
  rs's rejection may itself fire via its 2^62 over-rejection bug — see the
  jobs/proposed accept twin — i.e. possibly for the wrong reason.)
- Classification: implementation bug (py accepts out-of-range), plus
  blocked on spec restoration; promote together with the int64-max accept
  twin so the rejection is attributable to a real bounds check.

## Implementation divergences

### `expr2.1.3--membership-element-type-mismatch.invalid.yaml`

- Requires: `"a" in [1, 2]` rejected. Expression Language §2.1.3 defines list
  membership only as `__contains__(list: list[T], item: T)` — there is no
  signature for a string item against `list[int]`, and the implicit
  string→int coercion of `"a"` errors (§1.2.3), so no resolution exists.
- Observed: **rs accepts** (evaluates to `false` at runtime — apparent
  fallback to §1.2.5 cross-type equality semantics); **py rejects**
  (spec-conformant).
- Classification: openjd-rs implementation bug (missing type check). The
  fixture is spec-correct as written. Two caveats for promotion: (a) the
  spec does not explicitly require the error at TEMPLATE VALIDATION time —
  a runtime-error implementation would arguably conform yet fail this
  .invalid fixture; (b) the fix converts silently-false membership tests in
  existing templates into hard errors — schedulers should scan before
  adopting.

### `3.6.1--let-identifier-513.invalid.yaml`

- Requires: a 513-character let-binding `<UserIdentifier>` rejected
  (Template Schemas §3.6.1: "Maximum length of `<UserIdentifier>`: 512
  characters").
- Observed: **accepted by BOTH rs and py** (2026-08-12 sweep) — the
  identifier length limit is not enforced by either implementation.
- Classification: implementation bug in both (missing limit check). The
  512-character accept twin is `3.6--let-boundary-edges.yaml`, added by the
  expr-lang-gaps PR.
