# Proposed conformance fixtures (expected failures) — base/jobs

Every fixture in this directory is parked because it **fails against at least
one current reference implementation**. Placement is kind-level
(`<component>/<kind>/proposed/`) so promotion is a mechanical move up one
directory. The conformance runner does not scan `proposed/` directories.

## A merged default is not checked against the merged constraint (§1.2.1, openjd-rs only)

| Fixture | Construct | Observed |
|---|---|---|
| `1.2.1--merged-default-below-merged-minvalue.invalid.test.yaml` | env `[10,100]`, job template `[0,1000]` with `default: 5` | openjd-rs: **accepts, runs, prints `COUNT[5]`**; python: rejects at job generation |
| `1.2.1--merged-default-below-merged-minlength.invalid.test.yaml` | env `minLength: 5`, job template `minLength: 2` with `default: abc` | openjd-rs: **accepts, runs, prints `VALUE[abc]`**; python: rejects at job generation |

In each, the default satisfies the job template's own bound, so the merged
bound is the only thing that makes it invalid.

Cause, measured in openjd-rs at `951358be`: `preprocess_job_parameters`
(`crates/openjd-model/src/job/create_job/parameters.rs`) calls
`param.check_constraints` in its supplied-value branch and never in its default
branch, which coerces the default and inserts it. A default is therefore only
ever checked against the bounds of the template that declared it, at decode.
Three cases isolate it:

| Case | openjd-rs | python |
|---|---|---|
| default below its own `minValue`, no environment | rejects at template validation | rejects at template validation |
| default below its own `minValue`, wider environment | rejects at template validation | rejects at template validation |
| default satisfies its own `minValue`, below the merged one | **runs** | rejects at job generation |

The third case is the gap, and it is why the existing live fixture
`jobs/1.2.1--merged-default-violates-constraint.invalid.test.yaml` passes on
openjd-rs for the wrong reason: its default violates the job template's own
bound, so decode-time validation catches it before any merge is consulted.

Classification: **openjd-rs fix**, one `check_constraints` call in the default
branch. No spec decision is needed. Promote both once it lands.

### These replace the two constraint-widening fixtures

An earlier revision parked
`1.2.1--constraint-widening-int-range.invalid.test.yaml` and
`1.2.1--constraint-widening-minlength.invalid.test.yaml` here, asserting that a
Job Template *widening* an Environment Template's constraint must be refused.
That assertion was wrong.
[openjd-specifications#107](https://github.com/OpenJobDescription/openjd-specifications/issues/107)
records that §1.2.1 constrains the merged *result*, not each definition, so a
wider later definition is allowed and simply has no effect. Both
implementations already do that, and a maintainer review of this PR reached the
same conclusion.

Their replacements assert the intersection rather than the direction, and split
by what they pin. The two above pin that a merged *default* is checked, and
fail on openjd-rs. Four supplied-value and accept fixtures pin that the
intersection binds at all, pass on both implementations, and live in
`base/jobs/`.

## INT 64-bit supplied value (Python-only)

| Fixture | Construct | Observed |
|---|---|---|
| `2.3--int-value-above-int64-max.invalid.test.yaml` | supplied INT parameter value `9223372036854775808` (2^63) | openjd-rs: **rejects at job creation (fixture passes)**; python (openjd-model 0.11.x `create_job`): **accepts** |

Moved here from the base-gaps PR's live `jobs/` directory: the base spec
states no int64 bound on `<integer>` (see the job_templates/proposed README),
and the reference Python implementation accepts the value, so as a live
fixture it failed the reference implementation. Same promotion gate as the
template-side int64 family: a base-spec integer-bounds erratum, plus the
openjd-model fix. Its accept twin (`jobs/2.3--int-value-int64-max.test.yaml`,
supplied 2^63-1 resolves exactly) is in the base-gaps PR and passes both.
