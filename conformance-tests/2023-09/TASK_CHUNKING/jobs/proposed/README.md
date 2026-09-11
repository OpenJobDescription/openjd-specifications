# Proposed TASK_CHUNKING job fixtures: post-resolution bound checks

These fixtures are believed spec-correct and currently fail at least one reference
implementation. They live here rather than in `../` because the runner discovers test
files with a non-recursive glob, so `proposed/` is excluded and the suite stays green.
Promotion is `git mv` up one directory with no edit to the fixture.

| Fixture | Construct | Observed |
|---|---|---|
| `default-task-count-format-string-resolves-to-zero.invalid.test.yaml` | `chunks.defaultTaskCount: "{{Param.ChunkSize}}"` where the parameter default is `0`, against the documented minimum of 1 (§3.4.1.5 L1276) | openjd-model Python rejects at job creation. The Rust CLI reports `Template ... passes validation checks` and then runs, logging `Frame(CHUNK[INT]) = 1-1`, so the resolved `0` is treated as `1` |

## Classification

Implementation fix.

The minimum-of-1 bound cannot be checked at decode when the value is a format string,
because the value is not yet known, and `TASK_CHUNKING/job_templates/default-task-count-zero.invalid.yaml`
already covers the literal `0` case at decode. The bound must therefore be re-checked
after resolution at job creation. The Python path does this; the Rust path defers the
check and never resumes it.

Cross-check: in `openjd-model/src/template/validate_v2023_09/task_chunking.rs` the
`>= 1` comparison is guarded on the chunk count being a literal integer, which is
correct for decode-time validation. No equivalent check appears on the job-creation
path, so a format-string value reaches the scheduler unvalidated.

A green twin ships in `../default-task-count-format-string.test.yaml`, which asserts
that a format-string `defaultTaskCount` resolves and produces the expected chunk
boundaries. That case passes both implementations, so the divergence recorded here is
specific to the bound check rather than to resolution itself.

## Spec references, Template Schemas 2023-09

- [§3.4.1.5 L1263](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/wiki/2023-09-Template-Schemas.md?plain=1#L1263) chunks.defaultTaskCount is @fmtstring, so the bound defers past decode
- [§3.4.1.5 L1276](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/wiki/2023-09-Template-Schemas.md?plain=1#L1276) defaultTaskCount minimum value: 1, the bound not re-checked after resolution
- [§7.4 L2017](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/wiki/2023-09-Template-Schemas.md?plain=1#L2017) format strings not annotated @fmtstring[host] resolve at job creation

Line numbers are a locator for where each claim was verified. The section numbers are the
durable reference if the spec is re-flowed.
