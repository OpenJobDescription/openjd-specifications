# Proposed WRAP_ACTIONS fixtures (parked) — jobs

Fixtures in this directory are believed spec-correct but FAIL against the
current reference implementations. They are parked here so the main suite
stays green; promotion is a mechanical move up one directory
(kind-level `<component>/<kind>/proposed/` placement). The conformance
runner does not scan `proposed/` directories.

## wrap-repr-py-escapes-newline-in-wrapped-args

**Classification: spec conflict to resolve first; then an implementation
bug in BOTH implementations.**

Expression Language §2.2.6 documents `repr_py` as following Python's
`repr`, with the explicit example `repr_py("hello\nworld")` →
`'hello\\nworld'`. Both reference implementations (openjd-rs AND the
Python CLI — 2026-08-12 sweep, fails on both) instead embed the newline
raw into the emitted literal, so round-tripping a multi-line `python -c`
program through `repr_py(WrappedAction.Args)` produces broken Python:

```
File "<string>", line 1
  print(repr(['-c', 'import sys
                               ^
SyntaxError: EOL while scanning string literal
```

Reproduce: run this fixture through the conformance runner, or wrap any
action whose args contain U+000A and forward with the reference
`repr_py` pattern.

**The promotion gate is a spec decision, not just the repr_py fix:**
Template Schemas §5.2 restricts `<ArgString>` to characters outside the
Cc unicode category, which excludes newlines — so this fixture's own
onRun args are arguably spec-INVALID as written, and a conforming
validator could reject the template before repr_py is ever exercised.
Neither implementation enforces §5.2 today, and several merged fixtures
(plus the common multi-line `python -c` convention, which container
queue environments also rely on) depend on the acceptance. Either §5.2
is relaxed to permit newlines (making this fixture promotable once
repr_py is fixed), or the validator rejects them (making this fixture,
and the multi-line convention suite-wide, invalid). The two cannot both
stand; resolve the spec question first.

Unit-level twin: `EXPR/jobs/proposed/expr2.2.6--repr-py-newline-roundtrip`
(func-lib expected-failures PR) pins the same repr_py defect without the
WRAP_ACTIONS forwarding layer; this fixture adds the end-to-end path.
