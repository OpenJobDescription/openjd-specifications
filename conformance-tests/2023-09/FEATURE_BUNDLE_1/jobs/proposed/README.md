# Proposed FEATURE_BUNDLE_1 job fixtures: post-resolution bound checks

These fixtures are believed spec-correct and currently fail at least one reference
implementation. They live here rather than in `../` because the runner discovers test
files with a non-recursive glob, so `proposed/` is excluded and the suite stays green.
Promotion is `git mv` up one directory with no edit to the fixture.

| Fixture | Construct | Observed |
|---|---|---|
| `3.3.1--amount-max-format-string-resolves-to-zero.invalid.test.yaml` | `amounts[].max: "{{Param.CpuMax}}"` where the parameter default is `0`, against the `<positivefloat>` type at L959 | openjd-model Python rejects at job creation. The Rust CLI accepts the resolved `0` and runs the job to completion |

## Classification

Implementation fix.

`max` is `<positivefloat>` while `min` is `<nonnegativefloat>`, so `0` is legal for one and
not the other. A literal `max: 0` is already rejected at decode by
`../../job_templates/3.3.1--amount-max-zero.invalid.yaml`. Under FEATURE_BUNDLE_1 the value
may be a format string, in which case the positivity constraint cannot be checked at decode
and must be re-checked after resolution. The Python path does this; the Rust path defers the
check and never resumes it.

This is the same defect shape as the two fixtures in
`../../../TASK_CHUNKING/jobs/proposed/` and `../../../base/jobs/proposed/`: validation
correctly deferred for a format string, never resumed. Reviewers may prefer to treat all of
them as one issue.

The green twin,
`../3.3.1--amount-max-format-string-resolves-to-non-number.invalid.test.yaml`, covers a
`max` that resolves to a non-numeric string. Both implementations reject that, which is why
it sits in the live suite. The divergence recorded here is specific to the positivity bound
rather than to numeric parsing.

Not covered by any fixture, here or in `../`: the positive case asserting a resolved `max`
is the correct number. No `openjd` CLI surfaces resolved host requirements, and the runner
asserts only on stdout and task status, so a host requirement has no observable effect on a
single-host run. The negative cases are the reachable half.
