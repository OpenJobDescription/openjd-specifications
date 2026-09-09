# Proposed conformance fixtures (expected failures) — base/jobs

Every fixture in this directory is parked because it **fails against at least
one current reference implementation**. Placement is kind-level
(`<component>/<kind>/proposed/`) so promotion is a mechanical move up one
directory. The conformance runner does not scan `proposed/` directories.

## Merge widening (§1.2.1)

Spec §1.2.1: "each constraint must become more constrained as a subsequent
definition is merged with the previous ones in processing order" (Job
Template last). These fixtures have a Job Template that *widens* the
Environment Template's constraint while the default satisfies both ranges,
isolating the direction rule from the merged-consistency rule.

| Fixture | Construct | Observed |
|---|---|---|
| `1.2.1--constraint-widening-int-range.invalid.test.yaml` | env `[10,100]`, job template `[0,1000]` | accepted by both; job runs |
| `1.2.1--constraint-widening-minlength.invalid.test.yaml` | env `minLength: 5`, job template `minLength: 2` | accepted by both; job runs |

Cross-check: `openjd.model.merge_job_parameter_definitions` returns the
*intersection* (`minValue=10, maxValue=100`) rather than rejecting — both
implementations merge by intersection and never enforce the narrowing
direction.

Classification: **spec decision needed, then (possibly) implementation fix**.
The stated sentence supports rejection on a literal reading, but both
implementations implement intersection semantics, and enforcing
reject-on-widening is a behavioral change for any scheduler that merges
externally-supplied environment parameter definitions into customer templates
(e.g. queue environments). Until the spec either affirms the narrowing rule
or is revised to define intersection semantics, these stay parked.

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
