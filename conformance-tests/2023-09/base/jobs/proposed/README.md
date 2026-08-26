# Proposed base job fixtures: post-resolution constraint checks

These fixtures are believed spec-correct and currently fail at least one reference
implementation. They live here rather than in `../` because the runner discovers test
files with a non-recursive glob, so `proposed/` is excluded and the suite stays green.
Promotion is `git mv` up one directory with no edit to the fixture.

| Fixture | Construct | Observed |
|---|---|---|
| `3.3.2--format-string-in-anyof-resolves-to-invalid-value.invalid.test.yaml` | `attributes[].anyOf` element written as `"{{Param.Software}}"`, resolving to `not valid!`, against the `<AttributeCapabilityValue>` pattern in section 3.3.2.2 | Python rejects at job creation with `Value not valid! is not a valid attribute capability value.` The Rust CLI accepts the resolved value and runs the job |
| `3.3.2--format-string-in-allof-resolves-to-invalid-value.invalid.test.yaml` | Same, for `allOf` at L1015 | Same. Swept across four invalid resolved values, a space, an exclamation mark, 120 characters and a leading digit: Python rejects all four, Rust runs all four |
| `3.4.1.1--int-range-intstring-elements-normalized.test.yaml` | `<IntRangeList>` elements in the `<intstring>` string form, `['1', '02', '003']` | Rust substitutes `1`, `2`, `3`. Python substitutes `1`, `02`, `003`, so a task command line receives `--frame 02` |
| `3.4.1.2--float-range-floatstring-elements-normalized.test.yaml` | `<FloatRangeList>` elements in the `<floatstring>` string form, `['1.5', '02.50']` | Rust substitutes `1.5`, `2.5`. Python substitutes `1.5`, `02.50` |

## Classification: the two capability-value fixtures

Implementation fix.

`anyOf` is annotated `@fmtstring` in base 2023-09 at Template Schemas L1014, with no
extension gate, and its element type is constrained to the identifier-like pattern in
section 3.3.2.2. That pattern cannot be checked at decode when the element is a format
string, so it must be re-checked after resolution at job creation. The Python path does
this; the Rust path defers the check and never resumes it.

The value used here, `not valid!`, violates the pattern twice, on the space and on the
exclamation mark, so no reading of the pattern admits it.

This is the same defect shape as
`../../../TASK_CHUNKING/jobs/proposed/default-task-count-format-string-resolves-to-zero.invalid.test.yaml`:
validation correctly deferred for a format string, never resumed. Reviewers may prefer
to treat the two as one issue.

Not covered by any fixture, here or in `../`: the positive case asserting that a
resolved `anyOf` value is *correct*. No `openjd` CLI surfaces resolved host
requirements, in `summary --output json` or anywhere else, and the runner asserts only
on stdout and task status, so the resolved value has no observable effect on a
single-host run. The negative case above is the reachable half.


## Classification: the two range-element fixtures

Spec decision needed, then an implementation fix on one side or the other.

`<intstring>` and `<floatstring>` are defined only as "a string whose value is the string
representation of an integer / floating point value in base-10". Nothing is said about
whether the string form normalizes, so `['02']` yielding `2` and yielding `02` are both
defensible readings of the text as written.

Two facts make this worth a ruling rather than a shrug. First, the value reaches a task
command line, so the two readings produce different renderer invocations for the same
template. Second, the implementations do not merely disagree, they disagree in opposite
directions on different fields: for range-list elements Python preserves the literal and
Rust normalizes, while for a FLOAT parameter `default` Python normalizes and Rust preserves.

There is also a conflict with a landed fixture. `EXPR/jobs/expr1.3.4--float-passthrough.test.yaml`
asserts `PARAM:3.500` from `default: "3.500"`, which pins the verbatim reading for a parameter
default. If the spec rules that `<floatstring>` normalizes, that fixture and
`3.4.1.2--...` here cannot both be correct.

These two fixtures state the normalizing reading. They should not be promoted out of
`proposed/` until the spec says which reading is conformant.
