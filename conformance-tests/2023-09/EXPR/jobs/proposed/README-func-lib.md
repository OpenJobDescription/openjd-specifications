# Proposed EXPR fixtures (function library) — jobs

Fixtures listed here are parked instead of live, because a reference
implementation fails them or because the spec is silent on the behaviour
they pin. Placement is kind-level (`<component>/<kind>/proposed/`);
promotion is a mechanical move up one directory. The runner does not scan
`proposed/`. This README is named per fixture family
(`README-func-lib.md`) because other expected-failures PRs park fixtures
in this same directory with their own READMEs.

Observations are per-implementation (`rs` = openjd-rs, `py` = the Python
openjd CLI); dual results from the 2026-08-12 sweep, re-verified against
the current upstream/main rs build where noted.

## `expr2.2.4--center-odd-padding.test.yaml` — spec silence, py outlier

§2.2.4 does not say which side of `center()` receives the extra space for
odd padding. Measured for `center("hi", 7)`:

| Engine | Output | Extra space |
|---|---|---|
| CPython `str.center` | `'   hi  '` | LEFT (verified by execution) |
| openjd-rs (current upstream/main) | `'   hi  '` | LEFT — matches CPython (changed by upstream #305 + RFC 0005 coercion sync; re-verified this session) |
| Python openjd CLI | `'  hi   '` | RIGHT — now the outlier |

The fixture asserts the CPython/rs behaviour — the de facto answer.
Classification: **spec decision needed** ("follow CPython" would make this
promotable and the Python CLI's split a plain bug). An earlier revision of
this README claimed both implementations were right-heavy and that the
fixture's expectation was wrong; both claims were incorrect (rs changed,
and CPython is left-heavy).

## `expr2.2.4--isdigit-unicode.test.yaml` — spec ambiguity, no divergence

§2.2.4 never defines "digit". Both openjd implementations agree on
ASCII-only (`isdigit("٣")` is false on rs AND py); CPython's host
`str.isdigit` says True; §2.2.5 gives `\d` explicit Unicode semantics.
The fixture asserts the Unicode reading as a strawman — the OPPOSITE of
the current de facto agreement. Classification: **spec decision needed**
(define "digit"; ASCII-only is the likely ratification given both
implementations agree, in which case flip the expectation rather than
promote as-is).

## `expr2.2.6--repr-py-newline-roundtrip.test.yaml` — bug in BOTH

§2.2.6: repr_py "follows the behavior of Python's repr", whose example
escapes `\n`. BOTH implementations emit a raw newline inside the quoted
literal, producing invalid Python (`ast.literal_eval` raises
SyntaxError). Classification: **implementation bug in both**; the spec is
explicit. Promote once fixed. End-to-end twin through WRAP_ACTIONS
forwarding: `WRAP_ACTIONS/jobs/proposed/
wrap-repr-py-escapes-newline-in-wrapped-args.test.yaml` (wrap-actions
expected-failures PR) — note that twin is additionally gated on the §5.2
ArgString newline question.
