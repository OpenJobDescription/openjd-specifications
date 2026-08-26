# Proposed base job fixtures: post-resolution constraint checks

These fixtures are believed spec-correct and currently fail at least one reference
implementation. They live here rather than in `../` because the runner discovers test
files with a non-recursive glob, so `proposed/` is excluded and the suite stays green.
Promotion is `git mv` up one directory with no edit to the fixture.

| Fixture | Construct | Observed |
|---|---|---|
| `3.3.2--format-string-in-anyof-resolves-to-invalid-value.invalid.test.yaml` | `hostRequirements.attributes[].anyOf` element written as `"{{Param.Software}}"`, resolving to `not valid!`, against the `<AttributeCapabilityValue>` pattern in section 3.3.2.2 | openjd-model Python rejects at job creation with `Value not valid! is not a valid attribute capability value.` The Rust CLI accepts the resolved value and runs the job to completion |

## Classification

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
