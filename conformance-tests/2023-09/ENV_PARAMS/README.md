# ENV_PARAMS Conformance Tests

Conformance tests for the `ENV_PARAMS` extension defined in
[RFC 0010 — Environment Parameters](../../../rfcs/0010-environment-parameters.md).

This README is also the plan for the suite: the [coverage matrix](#coverage-matrix) lists every test file,
and [Validation table coverage](#validation-table-coverage) maps each row of the RFC's
[Validation](../../../rfcs/0010-environment-parameters.md#validation) table to the tests that verify it. Rules for
which no definite test can be written are listed in
[Rules without a definite test](#rules-without-a-definite-test), and what the suite leaves out on purpose in
[What the suite does not test](#what-the-suite-does-not-test).

## What this extension does

`ENV_PARAMS` lets each Step tell an Environment what it needs. An `<Environment>` declares parameters, a Step requests
the Environment and supplies values through a new `environment:` form of `<StepDependency>`, and the Environment reads
the values as `{{Env.Param.<name>}}`. The Environment may be one of the Job Template's own `jobEnvironments` or one
that the scheduler attaches from an Environment Template, matched by name when the Job is created.

```yaml
# Environment Template (§1.2)
extensions: [ <ExtensionName>, ... ]                  # NEW — per document; may list ENV_PARAMS

# <Environment> (§4), on jobEnvironments and an Environment Template's environment only
envParameterDefinitions: [ <EnvironmentParameterDefinition>, ... ]  # NEW — 1–50, unique names (§4.5)
activation: ALWAYS | BY_DEFAULT | ON_REQUEST            # NEW — default BY_DEFAULT; ALWAYS without ENV_PARAMS
hostRequirements: <HostRequirements>                   # NEW — may read Env.Param.* (§3.3.3)
enableIf: <Expression>                                 # NEW — @expr bool (§7.6); per Step at job creation
exclusiveGroup: <Identifier>                           # NEW — a Step's Sessions enter only the first of a group

# <StepDependency> (§3.2), in a Step's dependencies
dependsOn: "<StepName>"
# or, NEW, a synonym of dependsOn (dependsOn is planned for removal in the next major version):
step: "<StepName>"
# or, NEW:
environment: "<EnvironmentName>"   # a jobEnvironments entry first, else an attached Environment (§3.2.1)
required: <bool>                   # optional, default true; not false for a jobEnvironments entry
enableIf: <Expression>             # optional, @expr bool (§7.6); resolved at job creation
parameters:                        # optional, 1–50 keys
  <Identifier>: <EnvironmentParameterValue>   # literal or format string, resolved at job creation
```

```yaml
<EnvironmentParameterDefinition> ::= a <JobParameterDefinition> of the same type, except:
  type:           # any Job Parameter type
  userInterface:  # permitted; informational
  objectType:     # permitted (PATH, LIST[PATH]); informational
  dataFlow:       # permitted (PATH, LIST[PATH]); informational
  default:        # optional; may read only Param.* (not PATH) / RawParam.* of the same document
                  # a parameter without a default is required (constraint 7)
```

| Value | Type | Available in |
|---|---|---|
| `Env.Param.<name>` | the `Param.<name>` type of the parameter's type | the declaring Environment only: `variables`, script `let`, actions, embedded files, and `hostRequirements` and `enableIf` (not PATH / LIST[PATH]); PATH values are path-mapped |
| `Env.RawParam.<name>` | as `Env.Param.<name>`, but `string` / `list[string]` for PATH / LIST[PATH] | as `Env.Param.<name>`; never path-mapped |
| `Job.EnvNames` | `list[string]` | every format string resolved at job creation or later, in a document that lists `ENV_PARAMS`; not an Environment parameter `default` or the Job `name` |

Values are fixed per Step when the Job is created. For each Step and each Environment its Sessions enter, a parameter's
**effective value** is the value the Step's enabled entry supplies, or else the parameter's resolved `default`
(§3.2.2). A Session enters an Environment with `activation: ALWAYS` or `BY_DEFAULT` always, and one with
`activation: ON_REQUEST` only when its Step requests it, unless the Environment's `enableIf` is false for the Step. For
an `ALWAYS` Environment, an `enableIf` that is false for a Step is an error instead. An Environment from a document
that does not list `ENV_PARAMS` behaves as `ALWAYS`, except that a Step's disabled entry for it has no effect.

## RFC rules these tests verify

- **Extension gating** (RFC §Backward compatibility, §4, §3.2, §3.3, §7.3.1): Environment `envParameterDefinitions`,
  `activation`, `hostRequirements`, and `enableIf`; `environment:` and `step:` entries; `Job.EnvNames`, `Env.Param.*`,
  and `Env.RawParam.*`; an `anyOf` or `allOf` written as one expression; and an empty `hostRequirements` require
  `ENV_PARAMS` in the document that uses them, and a document that lists `ENV_PARAMS` must also list `EXPR` (§1.1 item
  3).
- **Extensions are per document** (§1.2 item 3): a Job Template without `ENV_PARAMS` runs with an Environment
  Template that lists it, taking every default and never entering its `ON_REQUEST` Environments; an Environment
  Template without `ENV_PARAMS` behaves as an `ALWAYS` Environment with no parameters and no `enableIf`, which every
  Session enters, and a Step's disabled entry for it has no effect and is not an error (§4 item 4).
- **Environment `envParameterDefinitions`** (§4 item 3, §4.5): 1–50 entries, unique names that may coincide with Job
  Parameters and other Environments' parameters, not on `stepEnvironments`; permitted types and fields; `default`
  scope; a literal `default` checked at template validation, a non-literal one only where a Step takes it.
- **`activation`** (§4 item 4): `ALWAYS`, `BY_DEFAULT`, or `ON_REQUEST`, default `BY_DEFAULT`, not on
  `stepEnvironments`; an `ON_REQUEST` Environment is entered, and its `variables` set, only in the Sessions of Steps
  that request it, and entered Environments keep their order. An `ALWAYS` Environment cannot be disabled: its
  `enableIf` being false for a Step is an error, at template validation for a literal `false` and at job creation
  otherwise (§4 item 6, §3.2.2 item 6).
- **Environment `enableIf`** (§4 item 6): requires `ENV_PARAMS`; an expression field of type `bool`
  (§7.6) with the scopes of the Environment's `hostRequirements` (or, on a Step Environment, `Step.Name` and the
  Step's `let`); decided per Step at job creation from its effective values, never `null`; a disabled Environment is
  not entered, sets no `variables`, adds no host requirements, and is still listed in `Job.EnvNames`. A disabled Environment is also
  not held to constraint 7 and its values are not checked; the `enableIf` is decided with the values that are known,
  and one that depends on a missing or unconvertible value is an error at the earliest stage it is known (§3.2.2).
- **Environment `hostRequirements`** (§4 item 5, §3.3.3): §3.3 shape per source, restricted scope, resolved per Step
  with its effective values, combined with the Step's by conjunction, conflicts (an unsatisfiable amount or single-valued attribute) rejected at job
  creation, and applied only to Sessions that enter the Environment.
- **Empty host requirements** (§3.3): in a document that lists `ENV_PARAMS`, an empty `hostRequirements` object or
  empty `amounts` and `attributes` lists on a Step or an Environment mean no requirements; at job creation an amount
  whose `min` and `max` both resolve to `null` is discarded, and the duplicate-name check applies to the requirements
  left after discarding, while an `anyOf` or `allOf` whose items all resolve to
  `null` is rejected, naming the Step or Environment and the attribute; a literal amount with neither `min` nor `max`,
  or a literal empty `anyOf`, is still rejected.
- **`anyOf` and `allOf` as one expression** (§3.3.2, §3.3 items 2 and 3): in a document that lists `ENV_PARAMS`, an
  `anyOf` or `allOf` may be a format string that is exactly one `{{ }}` expression, typed `list[string]?`; any other
  format string, or an expression whose static type cannot be a list, is rejected at template validation; at job
  creation a `null` result omits the field, an attribute left with neither field is discarded, and an empty list is
  rejected. An `allOf` result with more than one element for `attr.worker.os.family` or `attr.worker.cpu.arch` is
  rejected (§3.3.2.1).
- **`<StepDependency>` `environment:` entries** (§3.2 constraints 1–9): one key per entry; no entry for the Step's own
  Step Environment; no duplicates, even with complementary `enableIf`; 1–50 `parameters`; keys declared; values valid
  for their parameter; required parameters supplied by every Step that would enter the Environment; `required: false` not
  on a `jobEnvironments` entry; `enableIf` an expression field of type `bool` (§7.6), written without `{{ }}` and never
  `null`.
- **Value scope** (§3.2): a `parameters` value or `enableIf` reads `RawParam.*`, non-PATH `Param.*`, and
  `Job.Name`, `Job.EnvNames`, `Step.Name`, and the Step's `let`; never `Task.*`, `Session.*`, or `Env.*`.
- **`Env.Param.*` / `Env.RawParam.*` scope** (§4, §7.3.1): only inside the declaring Environment, only for declared
  names; a Step's own script cannot read them; a wrapping Environment's hooks read its own parameters.
- **External resolution** (§3.2.1): a name resolves to the Job Template's `jobEnvironments` first, else to exactly
  one attached Environment; missing with `required: true` and ambiguous names are rejected; `required: false`
  tolerates a missing Environment, and an attached Environment that declares no parameters ignores a
  `required: false` entry's `parameters`, without resolving them, while the entry still requests an `ON_REQUEST`
  one; a `required: true` entry's parameters to such an Environment, and
  a key that an Environment with parameters does not declare, are rejected; each resolved entry applies
  independently.
- **Effective values** (§3.2.2, §1.2.1): supplied value or `default`; a `default` reads the merged Job Parameter
  value; format strings convert to the parameter's type; Environment parameters are never merged with Job
  Parameters; values reach `onEnter`, Tasks (through `variables`), and `onExit` unchanged.
- **Path values** (§4.5): PATH and LIST[PATH] values are used as given, never joined with a directory and not required to be absolute, checked unmapped, path-mapped in `Env.Param.*` and not in `Env.RawParam.*`.
- **`Job.EnvNames`** (§7.3.1): the names of every Job Environment, own and attached, whatever its `activation`, in
  the Job's Environment order (the attached ones first, in the order they are attached; §1.1 item 7), excluding Step
  Environments, with a name repeated when two attached Environments share it.
- **`enableIf` on the entry** (§3.2 item 3.2): a disabled entry requests and supplies nothing, and a missing
  `required: true` Environment is not an error. Its name is still resolved: it declines a `BY_DEFAULT` Environment, so
  the Step's Sessions do not enter it, for an `ALWAYS` Environment it is an error, and for an Environment from a
  document that does not list `ENV_PARAMS` it has no effect.

## How these tests are designed

The RFC motivates the extension with Conda, Docker, and license Environments, but none of them is needed to test the
mechanism. The tests use Environments whose `onEnter` and `onExit` print sentinel lines built from their parameters
(`ENTER Conda Packages=ffmpeg=7`), and Steps whose Tasks print a marker (`TASK A`). A value reached an action when its
sentinel appears; an Environment was not entered when a sentinel it would print with its `default` is `forbidden`.
Each sentinel is `echo` with several arguments (`args: [ENTER, Conda, "Packages={{Env.Param.Packages}}"]`), so the
line that `echo` prints never appears in the template text, and a forbidden line cannot match a template that a
runner happens to log. A Task that reports an environment variable builds its line by concatenation
(`print('TASK_PKG='+os.environ['PKG'])`) for the same reason.

`openjd run` runs each Step of the Job in its own Session, one after another, so a test with two Steps observes each
Step's Environment entry separately, and the output of both Steps is in one log. Output assertions are substring
matches with no order, so order is observed within one line: `Job.EnvNames` is printed as
`{{ Job.EnvNames.join(',') }}`, and the order in which a Session enters Environments is observed through a variable
that each `onEnter` appends to with `openjd_env` and the Task prints (POSIX `bash` only).

Rules about which Sessions may share Steps (§3.2.2 equality) are scheduling rules. `openjd run` never puts two Steps
in one Session, so equality is observable only as "both values are accepted" (see
[Rules without a definite test](#rules-without-a-definite-test)).

Directory rules, from the task plan:

- A rule checked at template validation over one document is a `job_templates/` or `env_templates/` test, run with
  `openjd check`.
- A rule checked at job creation or later is a `jobs/` test; `.invalid.test.yaml` when the run must be rejected.
  Every rule that needs both a Job Template and an attached Environment Template is a `jobs/` test.
- The `template` of a `jobs/*.invalid.test.yaml` file MUST pass `openjd check` on its own, and so MUST each
  Environment Template in `environments`, so that the rejection can only come from job creation. The runner cannot
  distinguish a validation failure from a job-creation failure, so a test author verifies this by hand when writing
  the test. The exceptions are JB-105–JB-107, whose failure the specification permits but does not require template
  validation to report ([item 18](#rules-without-a-definite-test)); they pass whichever stage rejects them.

Commands: tests that only print values use `echo` with `runOn: [posix, windows]`. Tests that inspect exact argv or
build a variable across Environments use `bash` and `runOn: [posix]`. Tests that print an environment variable from
a Task use `python -c`, the suite's portable interpreter. PATH tests that check path mapping have `-posix` and
`-windows` variants, because `openjd run` maps paths to the host's path format.

Each test file starts with a comment naming the RFC or wiki section and the one rule it checks.

## Layout

```
ENV_PARAMS/
├── README.md        (this file)
├── job_templates/   # Job Template validation (openjd check)
├── env_templates/   # Environment Template validation (openjd check)
└── jobs/            # Job creation and execution (openjd run, with --env for each attached Environment)
```

Filenames follow `<section>--<description>[.invalid][.test].yaml`, where `<section>` is a section of
[2023-09-Template-Schemas](../../../wiki/2023-09-Template-Schemas.md): `1.1`/`1.2` (document roots and per-document
extensions), `1.2.1` (merging), `3.2`/`3.2.1`/`3.2.2` (`<StepDependency>`, resolution, effective values), `3.3.3`
(combined host requirements), `3.3`/`3.3.1`/`3.3.2` (empty and resolved-empty host requirements), `4` (`<Environment>` `envParameterDefinitions`, `activation`, `hostRequirements`), `4.5`
(`<EnvironmentParameterDefinition>`), and `7.3.1` (`Env.Param.*`, `Env.RawParam.*`, `Job.EnvNames`).

## Coverage matrix

Columns: **ID** is the identifier used in [Validation table coverage](#validation-table-coverage); **File** is the
planned filename in that directory (`.invalid` in the name means the document or run must be rejected); **Exts**
lists the extensions the document under test declares, where it matters (`EP` = `ENV_PARAMS`, `EX` = `EXPR`,
`WA` = `WRAP_ACTIONS`, `FB1` = `FEATURE_BUNDLE_1`, `—` = none; `EP` implies `EX`, which `ENV_PARAMS` requires, so a row that lists `EP` without `EX` lists both; `env` marks the attached Environment Template's list where it differs); **Assertion** is the one thing the test checks.

### `job_templates/` — Job Template validation

#### Extension gating

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-01 | `4--parameter-definitions-without-extension.invalid.yaml` | — | A `jobEnvironments` entry with `envParameterDefinitions` is rejected without `ENV_PARAMS`. |
| JT-02 | `4--activation-without-extension.invalid.yaml` | — | `activation` is rejected without `ENV_PARAMS`. |
| JT-03 | `4--host-requirements-without-extension.invalid.yaml` | — | `hostRequirements` on an Environment is rejected without `ENV_PARAMS`. |
| JT-04 | `3.2--environment-entry-without-extension.invalid.yaml` | — | An `environment:` entry is rejected without `ENV_PARAMS`. |
| JT-160 | `1.1--env-params-without-expr.invalid.yaml` | EP only | A Job Template that lists `ENV_PARAMS` without `EXPR` is rejected (§1.1 item 3). |
| JT-161 | `1.1--env-params-without-expr-unused.invalid.yaml` | EP only | The same with no `ENV_PARAMS` field in use: the requirement is on listing the extension. |
| JT-10 | `7.3.1--env-names-without-env-params.invalid.yaml` | EX | `Job.EnvNames` is rejected without `ENV_PARAMS`. |
| JT-13 | `1.1--minimal-env-params.yaml` | EP | A Job Environment with one parameter and a Step entry that supplies it is valid. |

#### `<Environment>` `envParameterDefinitions` (§4 item 3) and `<EnvironmentParameterDefinition>` (§4.5)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-15 | `4--parameter-definitions-empty.invalid.yaml` | EP | An empty `envParameterDefinitions` list is rejected. |
| JT-16 | `4--parameter-definitions-51.invalid.yaml` | EP | 51 parameters are rejected. |
| JT-17 | `4--parameter-definitions-50.yaml` | EP | 50 parameters are valid. |
| JT-18 | `4--parameter-definitions-duplicate-name.invalid.yaml` | EP | Two parameters of one Environment with the same name are rejected. |
| JT-19 | `4--parameter-name-same-as-job-parameter.yaml` | EP | An Environment parameter may share its name with a Job Parameter. |
| JT-20 | `4--parameter-name-in-two-environments.yaml` | EP | Two Environments may each declare a parameter of the same name. |
| JT-21 | `4--parameter-definitions-on-step-environment.invalid.yaml` | EP | `envParameterDefinitions` on a `stepEnvironments` entry is rejected. |
| JT-22 | `4.5--expr-types.yaml` | EP, EX | BOOL and every LIST type available to Job Parameters, including LIST[PATH], are valid. |
| JT-23 | `4.5--range-expr-type.yaml` | EP, EX | Type RANGE_EXPR, with a literal range `default`, is valid. |
| JT-24 | `4.5--user-interface.yaml` | EP | `userInterface` on an Environment parameter is valid. |
| JT-25 | `4.5--path-object-type.yaml` | EP | `objectType` on a PATH Environment parameter is valid. |
| JT-26 | `4.5--path-data-flow.yaml` | EP | `dataFlow` on a PATH Environment parameter is valid. |
| JT-27 | `4.5--default-reads-job-parameter.yaml` | EP | `default: "{{Param.X}}"` for a STRING Job Parameter of the same template is valid. |
| JT-28 | `4.5--default-reads-path-param.invalid.yaml` | EP | `default: "{{Param.P}}"` for a PATH Job Parameter is rejected. |
| JT-29 | `4.5--default-reads-raw-path-param.yaml` | EP | `default: "{{RawParam.P}}"` for a PATH Job Parameter is valid. |
| JT-30 | `4.5--default-reads-undefined-param.invalid.yaml` | EP | A `default` reading an undefined Job Parameter is rejected. |
| JT-31 | `4.5--default-reads-job-name.invalid.yaml` | EP, EX | A `default` reading `Job.Name` is rejected. |
| JT-32 | `4.5--default-reads-env-param.invalid.yaml` | EP | A `default` reading another parameter's `Env.Param.*` is rejected. |
| JT-33 | `4.5--default-reads-env-names.invalid.yaml` | EP, EX | A `default` reading `Job.EnvNames` is rejected. |
| JT-34 | `4.5--literal-default-below-min-value.invalid.yaml` | EP | An INT literal `default: 0` with `minValue: 1` is rejected even though every Step supplies the parameter. |
| JT-35 | `4.5--literal-default-not-in-allowed-values.invalid.yaml` | EP | A STRING literal `default` outside `allowedValues` is rejected even though every Step supplies it. |
| JT-36 | `4.5--literal-default-wrong-type.invalid.yaml` | EP | An INT literal `default: "abc"` is rejected. |
| JT-37 | `4.5--list-default-not-single-expression.invalid.yaml` | EP, EX | A LIST[STRING] `default` that is a format string other than one `{{ }}` expression is rejected. |
| JT-38 | `4.5--list-default-single-expression.yaml` | EP, EX | A LIST[STRING] `default` that is one `{{ }}` expression is valid. |
| JT-39 | `4.5--typed-expression-default.yaml` | EP, EX | An INT `default: "{{ Param.N + 1 }}"` is valid. |
| JT-120 | `4.5--list-path-object-type.yaml` | EP, EX | `objectType` on a LIST[PATH] Environment parameter is valid. |
| JT-121 | `4.5--default-reads-list-path-param.invalid.yaml` | EP, EX | A `default: "{{ Param.Dirs }}"` reading a LIST[PATH] Job Parameter is rejected. |

#### `activation` (§4 item 4)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-40 | `4--activation-always.yaml` | EP | `activation: ALWAYS` on a Job Environment is valid. |
| JT-41 | `4--activation-on-request.yaml` | EP | `activation: ON_REQUEST` on a Job Environment is valid. |
| JT-42 | `4--activation-unknown.invalid.yaml` | EP | `activation: SOMETIMES` is rejected. |
| JT-43 | `4--activation-on-step-environment.invalid.yaml` | EP | `activation` on a `stepEnvironments` entry is rejected. |
| JT-170 | `4--activation-always-enable-if-false.invalid.yaml` | EP, EX | `activation: ALWAYS` with the literal `enableIf: false` is rejected: an `ALWAYS` Environment cannot be disabled, and a literal `false` is known at template validation (§4 item 6, §3.2.2 item 6). |
| JT-171 | `4--activation-by-default.yaml` | EP, EX | `activation: BY_DEFAULT` on a Job Environment is valid. |
| JT-172 | `4--activation-always-enable-if-expression.yaml` | EP, EX | `activation: ALWAYS` with an expression `enableIf` is valid at template validation: the expression is not known until the Job is created (§7.6 rule 5). JB-128 and JB-129 run Environments like it. |

#### Environment `hostRequirements` (§4 item 5)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-44 | `4--host-requirements-on-job-environment.yaml` | EP | Literal `hostRequirements` on a Job Environment are valid. |
| JT-45 | `4--host-requirements-read-env-param.yaml` | EP | An attribute `anyOf: ["{{Env.Param.Flavor}}"]` reading the Environment's STRING parameter is valid. |
| JT-46 | `4--host-requirements-read-job-name.yaml` | EP, EX | Environment `hostRequirements` may read `Job.Name`. |
| JT-47 | `4--host-requirements-read-env-names.yaml` | EP, EX | Environment `hostRequirements` may read `Job.EnvNames`. |
| JT-48 | `4--host-requirements-on-step-environment.invalid.yaml` | EP | `hostRequirements` on a `stepEnvironments` entry are rejected. |
| JT-49 | `4--host-requirements-env-path-param.invalid.yaml` | EP | Environment `hostRequirements` reading `Env.Param.<PATH>` are rejected. |
| JT-50 | `4--host-requirements-param-path.invalid.yaml` | EP | Environment `hostRequirements` reading `Param.<PATH>` are rejected. |
| JT-51 | `4--host-requirements-step-name.invalid.yaml` | EP, EX | Environment `hostRequirements` reading `Step.Name` are rejected. |
| JT-52 | `4--host-requirements-session.invalid.yaml` | EP | Environment `hostRequirements` reading `Session.WorkingDirectory` are rejected. |
| JT-53 | `4--host-requirements-other-env-param.invalid.yaml` | EP | Environment `hostRequirements` reading a parameter of a different Environment are rejected. |
| JT-54 | `4--host-requirements-duplicate-amount-name.invalid.yaml` | EP | Two `amounts` of one Environment's `hostRequirements` with the same literal name are rejected (§3.3 applies per source). |
| JT-117 | `4--host-requirements-empty.yaml` | EP | `hostRequirements: {}` on a Job Environment is valid and means no requirements (§3.3 constraint 1 does not apply with `ENV_PARAMS`). |
| JT-118 | `4--host-requirements-env-raw-path-param.yaml` | EP | Environment `hostRequirements` may read `Env.RawParam.<PATH>`, the unmapped string (§7.3.2: `Env.RawParam.*` of any type). |
| JT-119 | `4--host-requirements-env-list-path-param.invalid.yaml` | EP, EX | Environment `hostRequirements` reading `Env.Param.<LIST[PATH]>` are rejected. |
| JT-155 | `4--host-requirements-reads-raw-path-job-param.yaml` | EP | Environment `hostRequirements` may read `RawParam.<PATH>` of a Job Parameter (§7.3.2: `RawParam.*` of any type). |

#### Empty host requirements (§3.3)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-173 | `3.3--step-host-requirements-empty.yaml` | EP | `hostRequirements: {}` on a Step is valid (§3.3 constraint 1 does not apply with `ENV_PARAMS`). |
| JT-174 | `3.3--step-host-requirements-empty-lists.yaml` | EP | A Step's `hostRequirements` with `amounts: []` and `attributes: []` are valid. |
| JT-175 | `3.3.1--amount-neither-min-nor-max.invalid.yaml` | EP | A literal amount with neither `min` nor `max` is still rejected. |
| JT-176 | `3.3.2--literal-empty-any-of.invalid.yaml` | EP | A literal `anyOf: []` is still rejected. |

#### `anyOf` and `allOf` as one expression (§3.3.2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-177 | `3.3.2--any-of-one-expression.yaml` | EP, EX | A Job Environment's `anyOf: "{{ [Env.Param.Model] if Env.Param.Model != '' else None }}"`, one expression of static type `list[string]?`, is valid. |
| JT-178 | `3.3.2--any-of-format-string-not-one-expression.invalid.yaml` | EP, EX | A Step's `anyOf: "x{{Param.A}}"` is a format string that is not exactly one expression; a list has no string form, so it is rejected. |
| JT-179 | `3.3.2--any-of-expression-int.invalid.yaml` | EP, EX | A Job Environment's `anyOf: "{{ Env.Param.Count }}"` with `Count` of type INT: static type `int` does not fit `list[string]?`; rejected. |
| JT-186 | `3.3.2--any-of-expression-without-extension.invalid.yaml` | EX | A Step's `anyOf: "{{ [Param.Flavor] }}"` in a Job Template that lists `EXPR` but not `ENV_PARAMS` is rejected: only `ENV_PARAMS` admits one expression in place of the list. |
| JT-180 | `4--activation-lowercase.invalid.yaml` | EP | `activation: always` is rejected: values are case-sensitive. |
| JT-181 | `3.2--always-entry-disabled-literal.invalid.yaml` | EP, EX | A Step's entry with `enableIf: false` for an `ALWAYS` Job Environment is rejected at template validation: no Step can leave an `ALWAYS` Environment out (§3.2 item 3.2). |
| JT-182 | `3.2--always-entry-enable-if-expression.yaml` | EP, EX | A Step's entry with an expression `enableIf` for an `ALWAYS` Job Environment is valid at template validation, since it is not known to be disabled until the Job is created (§7.6 rule 5). JB-44 runs one that resolves to `false`. |
| JT-183 | `3.2--disabled-entry-parameters-not-checked.yaml` | EP, EX | An entry with `enableIf: false` supplies an undeclared key and a value outside `allowedValues`; a disabled entry's parameters are not checked, so the template is valid (§3.2 item 3.2). |
| JT-184 | `3.2--expression-entry-parameters-deferred.yaml` | EP, EX | The same keys and values on an entry whose `enableIf` is an expression are not errors at template validation, since the entry may be disabled (§7.6 rule 5). |
| JT-185 | `7.6--enable-if-null-literal.invalid.yaml` | EP, EX | An entry's `enableIf: null` is rejected: a null value for an expression field is an error, not an omitted field (§7.6). |

#### Environment `enableIf` (§4 item 6)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-135 | `4--env-enable-if-literal.yaml` | EP, EX | `enableIf: false` on a Job Environment is valid. |
| JT-136 | `4--env-enable-if-reads-own-env-param.yaml` | EP, EX | A Job Environment's `enableIf` may read its own `Env.Param.*`. |
| JT-137 | `4--env-enable-if-reads-job-param-and-env-names.yaml` | EP, EX | It may read non-PATH `Param.*`, `Job.Name`, and `Job.EnvNames`. |
| JT-139 | `4--env-enable-if-without-env-params.invalid.yaml` | EX | `enableIf` on an Environment is rejected without `ENV_PARAMS`. |
| JT-140 | `4--env-enable-if-not-bool.invalid.yaml` | EP, EX | An `int` expression is rejected (§7.6 rule 2). |
| JT-141 | `4--env-enable-if-braces.invalid.yaml` | EP, EX | `"{{true}}"` is rejected: an expression field is written without `{{ }}` (§7.6 rule 1). |
| JT-142 | `4--env-enable-if-reads-step-name.invalid.yaml` | EP, EX | A Job Environment's `enableIf` reading `Step.Name` is rejected. |
| JT-143 | `4--env-enable-if-reads-other-env-param.invalid.yaml` | EP, EX | Reading another Environment's parameter is rejected. |
| JT-144 | `4--env-enable-if-reads-path-env-param.invalid.yaml` | EP, EX | Reading `Env.Param.*` of a PATH parameter is rejected. |
| JT-145 | `4--env-enable-if-reads-session.invalid.yaml` | EP, EX | Reading `Session.*` is rejected. |
| JT-146 | `4--step-env-enable-if-reads-step-name-and-let.yaml` | EP, EX | A Step Environment's `enableIf` may read `Step.Name` through the Step's `let`. |
| JT-147 | `4--step-env-enable-if-reads-task-param.invalid.yaml` | EP, EX | A Step Environment's `enableIf` reading `Task.Param.*` is rejected. |
| JT-148 | `3.2--required-param-env-enable-if-false-not-required.yaml` | EP, EX | A `BY_DEFAULT` Job Environment with `enableIf: false` and a parameter without `default` that no Step supplies is valid: a disabled Environment is not held to constraint 7 (§3.2.2). |
| JT-150 | `4--env-enable-if-expression-second-wrapper-undetermined.yaml` | EP, WA, EX | One wrapping Job Environment without `enableIf` and one with an expression `enableIf`: whether the stack holds two wrappers depends on the expression, so template validation reports nothing (§4 item 6 tail, §7.6 rule 5). JB-103 runs it. |
| JT-151 | `4--entry-enable-if-expression-wrapper-undetermined.yaml` | EP, WA, EX | A `BY_DEFAULT` wrapper and an `ON_REQUEST` wrapper requested by an entry with an expression `enableIf`: the entry is undetermined, so template validation reports nothing. |
| JT-153 | `4--env-enable-if-reads-raw-path-param.yaml` | EP, EX | A Job Environment's `enableIf` may read `RawParam.<PATH>` of a Job Parameter (§7.3.2: `RawParam.*` of any type). |
| JT-154 | `4--step-env-enable-if-reads-raw-path-param.yaml` | EP, EX | A Step Environment's `enableIf` may read `RawParam.<PATH>` (constraint 2). |

#### `Env.Param.*` / `Env.RawParam.*` and `Job.EnvNames` scope (§4, §7.3.1)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-55 | `7.3.1--env-param-in-variables.yaml` | EP | `Env.Param.X` in the declaring Environment's `variables` is valid. |
| JT-56 | `7.3.1--env-param-in-let.yaml` | EP, EX | `Env.Param.X` in the declaring Environment's script `let` is valid. |
| JT-57 | `7.3.1--env-param-in-embedded-file.yaml` | EP | `Env.Param.X` in the declaring Environment's embedded file `data` is valid. |
| JT-58 | `7.3.1--env-raw-param-in-on-exit.yaml` | EP | `Env.RawParam.X` in the declaring Environment's `onExit` is valid. |
| JT-59 | `7.3.1--env-param-undeclared.invalid.yaml` | EP | `Env.Param.Y` where the Environment declares no `Y` is rejected. |
| JT-60 | `7.3.1--env-param-of-other-environment.invalid.yaml` | EP | Environment A reading Environment B's parameter is rejected. |
| JT-61 | `7.3.1--env-param-in-step-script.invalid.yaml` | EP | A Step's `onRun` reading `Env.Param.X` of an Environment it requests is rejected. |
| JT-62 | `7.3.1--env-param-in-step-environment.invalid.yaml` | EP | A Step Environment reading `Env.Param.X` is rejected. |
| JT-63 | `7.3.1--env-param-in-step-host-requirements.invalid.yaml` | EP | A Step's own `hostRequirements` reading `Env.Param.X` are rejected. |
| JT-64 | `7.3.1--env-param-int-type-error.invalid.yaml` | EP, EX | `{{ Env.Param.Seats.upper() }}` on an INT parameter is a type error. |
| JT-65 | `7.3.1--env-names-in-step-script.yaml` | EP, EX | `{{ Job.EnvNames.join(',') }}` in a Step's `onRun` is valid. |
| JT-66 | `7.3.1--env-names-in-step-let.yaml` | EP, EX | A Step `let` binding reading `Job.EnvNames` is valid. |
| JT-67 | `7.3.1--env-names-in-job-name.invalid.yaml` | EP, EX | `Job.EnvNames` in the Job Template's `name` is rejected. |
| JT-68 | `7.3.1--env-names-is-list.invalid.yaml` | EP, EX | `{{ Job.EnvNames.upper() }}` is a type error (`list[string]`). |
| JT-123 | `7.3.1--env-raw-param-in-step-script.invalid.yaml` | EP | A Step's `onRun` reading `Env.RawParam.X` of an Environment it requests is rejected. |

#### `<StepDependency>` `environment:` entries (§3.2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-69 | `3.2--environment-and-depends-on.invalid.yaml` | EP | An entry with both `environment` and `dependsOn` is rejected (constraint 1). |
| JT-70 | `3.2--entry-without-key.invalid.yaml` | EP | An entry with only `parameters` is rejected (constraint 1). |
| JT-71 | `3.2--required-with-depends-on.invalid.yaml` | EP | `required` on a `dependsOn` entry is rejected (constraint 1). |
| JT-72 | `3.2--parameters-with-depends-on.invalid.yaml` | EP | `parameters` on a `dependsOn` entry is rejected (constraint 1). |
| JT-73 | `3.2--enable-if-with-depends-on.invalid.yaml` | EP, EX | `enableIf` on a `dependsOn` entry is rejected (constraint 1). |
| JT-74 | `3.2--depends-on-and-environment-entries.yaml` | EP | One `dependencies` list may hold `dependsOn` and `environment` entries. |
| JT-75 | `3.2--names-own-step-environment.invalid.yaml` | EP | An entry naming the Step's own Step Environment is rejected (constraint 2). |
| JT-76 | `3.2--duplicate-environment-entries.invalid.yaml` | EP | Two entries naming one Environment are rejected (constraint 3). |
| JT-77 | `3.2--duplicate-entries-complementary-enable-if.invalid.yaml` | EP, EX | Two entries naming one Environment with `enableIf` true and false are still rejected (constraint 3). |
| JT-78 | `3.2--parameters-empty.invalid.yaml` | EP | `parameters: {}` is rejected (constraint 4). |
| JT-79 | `3.2--parameters-51-keys-external.invalid.yaml` | EP | 51 `parameters` keys on an entry naming an external Environment are rejected (constraint 4). |
| JT-80 | `3.2--parameters-50-keys-external.yaml` | EP | 50 `parameters` keys on an entry naming an external Environment are valid at template validation. |
| JT-81 | `3.2--entry-without-parameters.yaml` | EP | An entry with no `parameters` is valid; every parameter takes its `default`. |
| JT-82 | `3.2--unknown-parameter-key.invalid.yaml` | EP | A key the named Job Environment does not declare is rejected (constraint 5). |
| JT-83 | `3.2--parameters-to-environment-without-definitions.invalid.yaml` | EP | Supplying a parameter to a Job Environment that declares none is rejected (constraint 5). |
| JT-84 | `3.2--no-parameters-to-environment-without-definitions.yaml` | EP | An entry without `parameters` naming a Job Environment that declares none is valid (constraint 5). |
| JT-85 | `3.2--literal-wrong-type.invalid.yaml` | EP | A STRING literal `"abc"` for an INT parameter is rejected (constraint 6). |
| JT-86 | `3.2--literal-not-in-allowed-values.invalid.yaml` | EP | A literal outside `allowedValues` is rejected (constraint 6). |
| JT-87 | `3.2--literal-below-min-value.invalid.yaml` | EP | An INT literal below `minValue` is rejected (constraint 6). |
| JT-88 | `3.2--literal-exceeds-max-length.invalid.yaml` | EP | A STRING literal longer than `maxLength` is rejected (constraint 6). |
| JT-89 | `3.2--int-literal-as-intstring.yaml` | EP | `"1"` for an INT parameter is valid (an `<intstring>`). |
| JT-90 | `3.2--list-literal-value.yaml` | EP, EX | A list literal for a LIST[STRING] Job Environment parameter is valid. |
| JT-91 | `3.2--list-value-not-single-expression.invalid.yaml` | EP, EX | A format string other than one `{{ }}` expression for a LIST[STRING] Job Environment parameter is rejected. |
| JT-92 | `3.2--required-false-on-job-environment.invalid.yaml` | EP | `required: false` on an entry naming a Job Environment is rejected (constraint 8). |
| JT-93 | `3.2--required-true-on-job-environment.yaml` | EP | `required: true` on an entry naming a Job Environment is valid. |
| JT-94 | `3.2--required-false-external.yaml` | EP | `required: false` on an entry naming no Job Environment is valid. |
| JT-95 | `3.2--enable-if-literal.yaml` | EP, EX | `enableIf: false` is valid. |
| JT-96 | `3.2--enable-if-expression.yaml` | EP, EX | `enableIf: "'Docker' not in Job.EnvNames"` is valid. |
| JT-97 | `3.2--enable-if-not-bool.invalid.yaml` | EP, EX | `enableIf: "Param.Count"` for an INT Job Parameter is rejected (constraint 9); an expression field converts nothing to `bool` (§7.6 rule 2). |
| JT-98 | `3.2--enable-if-braces.invalid.yaml` | EP, EX | `enableIf: "{{ true }}"` is rejected: an expression field is written without `{{ }}` (constraint 9, §7.6 rule 1). |
| JT-149 | `3.2--enable-if-string.invalid.yaml` | EP, EX | `enableIf: "Param.Mode"` for a STRING Job Parameter is rejected: an expression field does not convert `string` to `bool` (§7.6 rule 2). |
| JT-156 | `3.2--literal-value-violation-env-enable-if-false.yaml` | EP, EX | A literal value outside `allowedValues` for a Job Environment whose `enableIf` is the literal `false` is valid: values are checked only for an Environment whose `enableIf` is not `false` (§3.2.2). |
| JT-157 | `3.2--literal-value-violation-env-enable-if-undetermined.yaml` | EP, EX | The same with an expression `enableIf`: the check depends on it, so template validation reports nothing (§7.6 rule 5). JB-108 and JB-109 run it. |

#### `<StepDependency>` `step:` entries (§3.2 item 2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-124 | `3.2--step-entry.yaml` | EP | A `step:` entry naming an earlier Step is valid. |
| JT-125 | `3.2--step-entry-without-extension.invalid.yaml` | — | A `step:` entry is rejected without `ENV_PARAMS`. |
| JT-126 | `3.2--step-and-depends-on.invalid.yaml` | EP | An entry with both `step` and `dependsOn` is rejected, even naming one Step (constraint 1). |
| JT-127 | `3.2--step-and-environment.invalid.yaml` | EP | An entry with both `step` and `environment` is rejected (constraint 1). |
| JT-128 | `3.2--parameters-with-step.invalid.yaml` | EP | `parameters` on a `step:` entry is rejected (constraint 1). |
| JT-129 | `3.2--required-with-step.invalid.yaml` | EP | `required` on a `step:` entry is rejected (constraint 1). |
| JT-130 | `3.2--step-and-depends-on-duplicate.invalid.yaml` | EP | A `step:` and a `dependsOn:` entry naming one Step are a duplicate and rejected. |
| JT-131 | `3.2--step-unknown.invalid.yaml` | EP | A `step:` entry naming no Step is rejected. |
| JT-132 | `3.2--step-self.invalid.yaml` | EP | A Step naming itself with `step:` is rejected. |
| JT-133 | `3.2--step-and-depends-on-cycle.invalid.yaml` | EP | A cycle of one `step:` and one `dependsOn:` edge is rejected. |
| JT-134 | `3.2--step-depends-on-and-environment-entries.yaml` | EP | One `dependencies` list may mix `step:`, `dependsOn:`, and `environment:` entries. |

#### Constraint 7 for Job Environments (§3.2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-99 | `3.2--by-default-required-param-not-supplied.invalid.yaml` | EP | A Step with no entry for a `BY_DEFAULT` Job Environment with a parameter without `default` is rejected. |
| JT-100 | `3.2--by-default-required-param-supplied-by-every-step.yaml` | EP | The same Environment is valid when every Step supplies the parameter. |
| JT-101 | `3.2--on-request-required-param-non-requesting-step.yaml` | EP | A Step that does not request an `ON_REQUEST` Job Environment need not supply its required parameter. |
| JT-102 | `3.2--on-request-required-param-not-supplied.invalid.yaml` | EP | A Step that requests an `ON_REQUEST` Job Environment without supplying its required parameter is rejected. |
| JT-103 | `3.2--by-default-entry-disabled-literal-declines.yaml` | EP, EX | An entry with `enableIf: false` for a `BY_DEFAULT` Job Environment declines it, so constraint 7 does not apply and the Environment's required parameter need not be supplied; valid. |
| JT-104 | `3.2--on-request-entry-disabled-literal.yaml` | EP, EX | An entry with `enableIf: false` for an `ON_REQUEST` Job Environment requests nothing, so its required parameter is not needed. |
| JT-152 | `3.2--constraint-7-constant-expression-enable-if-deferred.yaml` | EP, EX | An entry with `enableIf: "true"`, a constant expression, requests an `ON_REQUEST` Job Environment without supplying its required parameter. The entry is undetermined at template validation (§7.6 rule 5), and disabled it would request nothing, so template validation reports nothing; JB-102 rejects it at job creation. |
| JT-158 | `3.2--required-param-env-enable-if-expression-undetermined.yaml` | EP, EX | The same with an expression `enableIf` over a Job Parameter: whether constraint 7 applies is undetermined, so template validation reports nothing (§7.6 rule 5). JB-113 runs it. |
| JT-162 | `3.2.2--env-enable-if-reads-missing-param.invalid.yaml` | EP, EX | The `enableIf` reads the unsupplied parameter itself. The value is known to be missing at template validation and the result depends on it, so the template is rejected (§3.2.2). Replaces JB-114. |
| JT-163 | `3.2.2--disabled-env-undeclared-key.invalid.yaml` | EP, EX | An entry for a Job Environment whose `enableIf` is the literal `false` supplies an undeclared key: constraint 5 checks the entry as written and still applies, so the template is rejected (§3.2.2). |
| JT-164 | `3.2.2--disabled-env-null-value.invalid.yaml` | EP, EX | The same with a `null` value: not a form of `<EnvironmentParameterValue>`, which is checked for a disabled Environment too; rejected (§3.2.2). |
| JT-165 | `3.2.2--disabled-env-list-format-string.yaml` | EP, EX | The same with a LIST[STRING] value that is a format string, not a single `{{ }}` expression: that rule is part of the value's type, which is not checked for a disabled Environment, so the template is valid (§3.2.2). |
| JT-166 | `4.5--range-expr-max-length-as-written.invalid.yaml` | EP, EX | A literal RANGE_EXPR value `1,2,3` breaks `maxLength: 3` as written, although its canonical form `1-3` fits; rejected (§4.5 item 4, §2.10). |
| JT-167 | `4.5--range-expr-min-length-canonical.invalid.yaml` | EP, EX | A literal `1-3:2` meets `minLength: 4` as written, but its canonical form `1,3` does not; rejected (§4.5 item 4, §2.10). |
| JT-168 | `4.5--literal-default-checked-when-disabled.invalid.yaml` | EP, EX | An INT literal `default: 0` with `minValue: 1` on a Job Environment whose `enableIf` is the literal `false` is rejected: a literal `default` is checked whatever any `enableIf` decides (§4.5). |
| JT-169 | `4--env-enable-if-reads-env-raw-path-param.yaml` | EP, EX | A Job Environment's `enableIf` may read its own `Env.RawParam.<PATH>` (§7.3.2). |

#### Value and `enableIf` scope (§3.2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JT-105 | `3.2--value-reads-job-parameter.yaml` | EP | A value `"{{Param.X}}"` for a STRING Job Parameter is valid. |
| JT-106 | `3.2--value-reads-path-param.invalid.yaml` | EP | A value `"{{Param.P}}"` for a PATH Job Parameter is rejected. |
| JT-107 | `3.2--value-reads-raw-path-param.yaml` | EP | A value `"{{RawParam.P}}"` for a PATH Job Parameter is valid. |
| JT-108 | `3.2--value-reads-task-param.invalid.yaml` | EP | A value reading `Task.Param.*` is rejected. |
| JT-109 | `3.2--value-reads-session.invalid.yaml` | EP | A value reading `Session.WorkingDirectory` is rejected. |
| JT-110 | `3.2--value-reads-env-scope.invalid.yaml` | EP | A value reading `Env.File.Spec`, an embedded file the requested Environment defines, is rejected. |
| JT-111 | `3.2--value-reads-step-name.yaml` | EP, EX | A value reading `Step.Name` is valid. |
| JT-112 | `3.2--value-reads-step-let.yaml` | EP, EX | A value reading a Step `let` binding is valid. |
| JT-113 | `3.2--value-reads-job-name.yaml` | EP, EX | A value reading `Job.Name` is valid. |
| JT-114 | `3.2--value-reads-env-names.yaml` | EP, EX | A value reading `Job.EnvNames` is valid. |
| JT-115 | `3.2--enable-if-reads-task-param.invalid.yaml` | EP, EX | An `enableIf` reading `Task.Param.*` is rejected. |
| JT-116 | `3.2--enable-if-reads-step-name-and-let.yaml` | EP, EX | An `enableIf` reading `Step.Name` and a Step `let` binding is valid. |
| JT-122 | `3.2--enable-if-reads-path-param.invalid.yaml` | EP, EX | An `enableIf` reading `Param.<PATH>` is rejected. |
| JT-187 | `4--exclusive-group-on-step-environment.invalid.yaml` | EP, EX | `exclusiveGroup` on a `stepEnvironments` entry is rejected. |
| JT-188 | `4--exclusive-group-not-identifier.invalid.yaml` | EP, EX | An `exclusiveGroup` that is not an `<Identifier>` is rejected. |
| JT-189 | `4--exclusive-group-job-environment-undetermined.yaml` | EP, EX | A `BY_DEFAULT` Job Environment with an `exclusiveGroup` is undetermined at template validation, so its unsupplied required parameter is not a constraint 7 error then. |

### `env_templates/` — Environment Template validation

| ID | File | Exts | Assertion |
|---|---|---|---|
| ET-01 | `1.2--extensions-env-params.yaml` | EP | An Environment Template with `extensions: [ENV_PARAMS, EXPR]` and Environment parameters is valid. |
| ET-02 | `1.2--extensions-empty.invalid.yaml` | — | `extensions: []` is rejected (§1.2 item 3, non-empty). |
| ET-03 | `4--parameter-definitions-without-extension.invalid.yaml` | — | `envParameterDefinitions` on the `environment` is rejected without `ENV_PARAMS`. |
| ET-04 | `4--activation-without-extension.invalid.yaml` | — | `activation` is rejected without `ENV_PARAMS`. |
| ET-05 | `4--host-requirements-without-extension.invalid.yaml` | — | `hostRequirements` is rejected without `ENV_PARAMS`. |
| ET-43 | `1.2--env-params-without-expr.invalid.yaml` | EP only | An Environment Template that lists `ENV_PARAMS` without `EXPR` is rejected (§1.2 item 3: the Job Template's prerequisites). |
| ET-07 | `4--parameter-definitions-empty.invalid.yaml` | EP | An empty `envParameterDefinitions` list is rejected. |
| ET-08 | `4--parameter-definitions-51.invalid.yaml` | EP | 51 parameters are rejected. |
| ET-09 | `4--parameter-definitions-duplicate-name.invalid.yaml` | EP | Duplicate parameter names are rejected. |
| ET-10 | `4--parameter-name-same-as-job-parameter.yaml` | EP | A parameter may share its name with the template's own Job Parameter. |
| ET-11 | `4.5--range-expr-type.yaml` | EP, EX | Type RANGE_EXPR is valid. |
| ET-12 | `4.5--user-interface.yaml` | EP | `userInterface` is valid. |
| ET-13 | `4--activation-on-request.yaml` | EP | `activation: ON_REQUEST` is valid. |
| ET-14 | `4--activation-unknown.invalid.yaml` | EP | An unknown `activation` value is rejected. |
| ET-44 | `4--activation-always-enable-if-false.invalid.yaml` | EP, EX | `activation: ALWAYS` with the literal `enableIf: false` is rejected, as for a Job Environment (JT-170). |
| ET-45 | `4--activation-by-default.yaml` | EP, EX | `activation: BY_DEFAULT` with an `enableIf` that may be false is valid. |
| ET-15 | `4--host-requirements-read-env-param.yaml` | EP | `hostRequirements` reading the Environment's STRING parameter are valid. |
| ET-16 | `4--host-requirements-env-path-param.invalid.yaml` | EP | `hostRequirements` reading `Env.Param.<PATH>` are rejected. |
| ET-17 | `4--host-requirements-step-name.invalid.yaml` | EP, EX | `hostRequirements` reading `Step.Name` are rejected. |
| ET-18 | `4.5--default-reads-own-job-parameter.yaml` | EP | A `default` reading a Job Parameter the Environment Template defines is valid. |
| ET-19 | `4.5--default-reads-undefined-param.invalid.yaml` | EP | A `default` reading a Job Parameter the Environment Template does not define is rejected, even if a Job Template might define it ("of the same document"). |
| ET-20 | `4.5--default-reads-path-param.invalid.yaml` | EP | A `default` reading `Param.<PATH>` is rejected. |
| ET-21 | `4.5--default-reads-raw-path-param.yaml` | EP | A `default` reading `RawParam.<PATH>` is valid. |
| ET-22 | `4.5--default-reads-env-names.invalid.yaml` | EP, EX | A `default` reading `Job.EnvNames` is rejected. |
| ET-23 | `4.5--literal-default-violates-constraint.invalid.yaml` | EP | A literal `default` outside `allowedValues` is rejected. |
| ET-24 | `4.5--list-default-not-single-expression.invalid.yaml` | EP, EX | A list `default` that is a format string other than one `{{ }}` expression is rejected. |
| ET-25 | `4.5--list-path-default-empty.yaml` | EP, EX | `type: LIST[PATH]` with `default: []` is valid, as in the Docker sample. |
| ET-26 | `4.5--required-parameter-activation-by-default.yaml` | EP | A parameter without `default` on a `BY_DEFAULT` Environment is valid in the template alone; constraint 7 is a job-creation check (JB-32). |
| ET-27 | `7.3.1--env-param-undeclared.invalid.yaml` | EP | `Env.Param.Y` for an undeclared `Y` is rejected. |
| ET-28 | `7.3.1--env-param-in-variables-let-and-files.yaml` | EP, EX | `Env.Param.X` in `variables`, script `let`, and embedded files is valid. |
| ET-29 | `7.3.1--env-names-in-on-enter.yaml` | EP, EX | `Job.EnvNames` in `onEnter` args is valid. |
| ET-31 | `7.3.1--wrap-hook-reads-own-param.yaml` | EP, WA, EX | A wrapping Environment's `onWrapTaskRun` reading its own `Env.Param.Image` is valid. |
| ET-32 | `1.2--schema-field.yaml` | EP | An Environment Template with a `$schema` property is valid (§1.2 item 2). |
| ET-33 | `1.2--unknown-extension.invalid.yaml` | — | An extension name the specification does not define is rejected (§1.2 item 3, same names as the Job Template). |
| ET-34 | `4.5--path-object-type.yaml` | EP | `objectType` on a PATH Environment parameter is valid. |
| ET-35 | `4.5--path-data-flow.yaml` | EP | `dataFlow` on a PATH Environment parameter is valid. |
| ET-37 | `4--parameter-definitions-50.yaml` | EP | 50 parameters are valid. |
| ET-38 | `4--host-requirements-session.invalid.yaml` | EP | `hostRequirements` reading `Session.WorkingDirectory` are rejected. |
| ET-46 | `4--host-requirements-empty.yaml` | EP | `hostRequirements: {}` in an Environment Template is valid and means no requirements, as on a Job Environment (JT-117). |
| ET-47 | `4--activation-lowercase.invalid.yaml` | EP | `activation: always` in an Environment Template is rejected: values are case-sensitive. |
| ET-48 | `4--exclusive-group.yaml` | EP, EX | An Environment Template's Environment may have an `exclusiveGroup`. |
| ET-49 | `4--exclusive-group-always.invalid.yaml` | EP, EX | `exclusiveGroup` on an `ALWAYS` Environment is rejected (§4 item 7 constraint 1). |
| ET-50 | `4--exclusive-group-without-extension.invalid.yaml` | — | `exclusiveGroup` is rejected without `ENV_PARAMS`. |

#### Environment `enableIf` in an Environment Template (§4 item 6)

| ID | File | Exts | Assertion |
|---|---|---|---|
| ET-39 | `4--env-enable-if-reads-own-env-param.yaml` | EP, EX | An Environment Template's `enableIf` may read its own `Env.Param.*`. |
| ET-40 | `4--env-enable-if-reads-own-job-parameter.yaml` | EP, EX | It may read the Environment Template's own Job Parameters. |
| ET-41 | `4--env-enable-if-reads-step-name.invalid.yaml` | EP, EX | `Step.Name` is rejected. |

### `jobs/` — job creation and execution

Attached Environment Templates are given in the test's `environments` list.

#### Values reach the Environment (§4.5, §3.2.2, §1.2.1)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-01 | `4.5--value-reaches-on-enter-args.test.yaml` | EP | A supplied value appears in `onEnter` argv (`echo`). |
| JB-02 | `4.5--value-reaches-on-exit-args.test.yaml` | EP | The same value appears in `onExit` argv. |
| JB-03 | `4.5--value-argv-exact.test.yaml` | EP | `runOn: [posix]`. A value with spaces, quotes, and `$` arrives as one argv element, byte for byte (`printf '[%s]\n' "$@"`). |
| JB-04 | `4.5--value-reaches-task-through-variables.test.yaml` | EP | `variables: {PKG: "{{Env.Param.Packages}}"}`; the Task prints `PKG` with the supplied value. |
| JB-05 | `4.5--omitted-parameter-takes-default.test.yaml` | EP | An entry that omits a parameter yields its literal `default`. |
| JB-06 | `4.5--default-reads-merged-job-parameter.test.yaml` | EP | Attached `default: "{{Param.CondaPackages}}"`; the Job Template redefines `CondaPackages`'s `default`; `onEnter` sees the Job Template's default. |
| JB-07 | `4.5--default-reads-submitted-job-parameter.test.yaml` | EP | As JB-06 with `parameters: {CondaPackages: ...}`; `onEnter` sees the submitted value. |
| JB-08 | `1.2.1--env-parameters-not-merged.test.yaml` | EP | A Job Parameter `Packages` and two Environments' `Packages` parameters keep three distinct values. |
| JB-09 | `3.2.2--format-string-value-converted-to-int.test.yaml` | EP | `"{{Param.N}}"` for an INT parameter with `minValue: 1`, `N=3`, prints `3`. |
| JB-10 | `3.2.2--int-one-and-string-one-both-accepted.test.yaml` | EP | One Step supplies INT `1`, another `"1"`; both run and both print `1` (a second parameter `Tag` tells the two lines apart). |
| JB-11 | `4.5--resolved-default-unused-violates-constraint.test.yaml` | EP | A `default` reading a Job Parameter that resolves outside `allowedValues` is not an error when every Step supplies the parameter. |
| JB-12 | `4.5--resolved-default-taken-violates-constraint.invalid.test.yaml` | EP | The same `default` is rejected when one Step takes it. |
| JB-13 | `3.2--format-string-value-violates-constraint.invalid.test.yaml` | EP | A Job Environment value `"{{Param.N}}"` that resolves below `minValue` is rejected at job creation. |
| JB-14 | `3.2--value-from-step-let-and-step-name.test.yaml` | EP, EX | Two Steps supply `"{{ Step.Name + '-' + tag }}"` from a Step `let`; each `onEnter` prints its own Step's value. |
| JB-117 | `4.5--range-expr-value-reaches-env.test.yaml` | EP, EX | A RANGE_EXPR value `1,2,3,7` and the default `1-10` reach `onEnter` as `range_expr` values (`len`, `max`). |
| JB-122 | `4.5--range-expr-computed-length-canonical.test.yaml` | EP, EX | A value `{{Param.Frames}}` is a `range_expr` with no other spelling, so only its canonical form `1-3` is checked against `maxLength: 3`, though the Job Parameter was submitted as `1,2,3`; the Job runs. |
| JB-123 | `3.2.1--unreachable-attached-disabled-not-required.test.yaml` | EP; env EP, EX | An attached `BY_DEFAULT` Environment named like a Job Environment, so unreachable, with a parameter without `default` and an `enableIf` that resolves `false`: disabled for every Step, it needs no values, and the Job runs (§3.2.1 item 4). |
| JB-124 | `3.2.1--unreachable-attached-enabled-required.invalid.test.yaml` | EP; env EP, EX | The same with the `enableIf` resolving `true`: Step A's Sessions enter it and its parameter cannot be supplied, so the submission is rejected. |
| JB-125 | `3.2.2--env-enable-if-false-unresolvable-value-not-read.test.yaml` | EP, EX | A value `{{ Param.L[5] }}` that fails to resolve is unknown, but the `enableIf` reads only a Job Parameter and is `false`: the Environment is disabled, the value's error is not reported, and the Job runs (§3.2.2). |
| JB-126 | `3.2.2--env-enable-if-reads-unresolvable-value.invalid.test.yaml` | EP, EX | The `enableIf` reads a value that fails to resolve, so its result depends on it and the Job is rejected (§3.2.2). |
| JB-127 | `4--env-enable-if-reads-env-raw-path-param.test.yaml` | EP, EX | `runOn: [posix]`. An `enableIf` over `Env.RawParam.<PATH>` disables the Environment for the Step that supplies `/none` and enters it for the one that takes `/data`. |

#### External resolution (§3.2.1)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-15 | `3.2.1--external-environment-receives-values.test.yaml` | EP | An entry naming an attached Environment supplies its value to that Environment's `onEnter`. |
| JB-16 | `3.2.1--external-required-missing.invalid.test.yaml` | EP | An entry (default `required: true`) naming an Environment nothing attaches is rejected. |
| JB-17 | `3.2.1--external-required-false-missing-ignored.test.yaml` | EP, EX | The same entry with `required: false` is ignored; the Step's Task runs, and `Job.EnvNames` lists only the Job Environment `J`. |
| JB-18 | `3.2.1--external-lacks-parameter.invalid.test.yaml` | EP | A `required: false` entry supplying a parameter the attached Environment, which declares others, does not declare is rejected. |
| JB-19 | `3.2.1--external-without-env-params-supplied.test.yaml` | EP | Attached Environment Template without `ENV_PARAMS` (the pre-extension `Conda` case); a `required: false` entry's `parameters` are ignored, and the Environment is entered with its Job Parameter's value. |
| JB-165 | `3.2.1--external-without-env-params-supplied-required.invalid.test.yaml` | EP | The same Environment with a `required: true` entry that supplies a parameter is rejected. |
| JB-166 | `3.2.1--external-only-undeclared-key.invalid.test.yaml` | EP | A `required: false` entry whose only key the attached Environment, which declares parameters, does not declare is rejected. |
| JB-167 | `3.2.1--external-on-request-without-definitions-supplied.test.yaml` | EP; env EP, EX | An attached `ON_REQUEST` Environment that lists `ENV_PARAMS` and declares no parameters ignores a `required: false` entry's `parameters`, and the entry still requests it, so the Step's Session enters it. |
| JB-168 | `3.2.1--external-without-env-params-unresolvable-value-ignored.test.yaml` | EP, EX | The JB-19 entry's ignored value `{{ Param.L[5] }}` would fail to resolve, but ignored values are not resolved (§7.4.1 step 5), so the Job runs. |
| JB-169 | `3.2.1--external-without-env-params-disabled-entered.test.yaml` | EP, EX | The JB-19 entry with `enableIf: false`: the Environment, from a document without `ENV_PARAMS`, behaves as `ALWAYS`, so the disabled entry has no effect and is not an error, and the Step's Session enters it (§4 item 4). |
| JB-170 | `3.2.1--external-without-env-params-disabled-required-entered.test.yaml` | EP, EX | The same with `required: true` and no `parameters`: still no effect and no error, unlike for an attached `ALWAYS` Environment (JB-141). |
| JB-171 | `3.2.1--external-without-env-params-disabled-by-expression-entered.test.yaml` | EP, EX | As JB-140, but the attached Environment's document does not list `ENV_PARAMS`: the entry's `enableIf` resolves to `false` at job creation, and the Step's Session still enters it (§7.4.1 step 4). |
| JB-172 | `3.2.1--external-without-env-params-enabled-by-expression-supplied.test.yaml` | EP, EX | The JB-19 entry with an `enableIf` that resolves to `true`: its `parameters` are ignored and the Environment is entered with its Job Parameter's value. |
| JB-20 | `3.2.1--external-without-env-params-no-parameters.test.yaml` | EP | Attached Environment Template without `ENV_PARAMS`; an entry without `parameters` is valid, and the Environment is entered. |
| JB-21 | `3.2.1--external-ambiguous-name.invalid.test.yaml` | EP | Two attached Environments with the entry's name are rejected. |
| JB-22 | `3.2.1--job-environment-shadows-attached.test.yaml` | EP | A Job Environment and an attached Environment share name `X`; the entry's value reaches the Job Environment, and the attached one (which declares no parameter) does not cause a rejection. |
| JB-23 | `3.2.1--attached-reachable-from-other-step.test.yaml` | EP | Step S has a Step Environment `X`; Step T's entry for `X` resolves to the attached `X` and its value reaches it. |
| JB-24 | `3.2.1--external-value-wrong-type.invalid.test.yaml` | EP | A STRING `"abc"` for an attached INT parameter is rejected. |
| JB-25 | `3.2.1--external-value-not-allowed.invalid.test.yaml` | EP | A value outside the attached parameter's `allowedValues` is rejected. |
| JB-26 | `3.2.1--external-list-literal-for-string.invalid.test.yaml` | EP, EX | A list literal for an attached STRING parameter is rejected. |
| JB-29 | `3.2.1--external-list-value-not-single-expression.invalid.test.yaml` | EP, EX | A format string other than one `{{ }}` expression for an attached LIST[STRING] parameter is rejected. |
| JB-30 | `3.2.1--several-attached-each-own-values.test.yaml` | EP | One Step requests two attached Environments; each `onEnter` prints the value of its own entry. |
| JB-87 | `3.2.1--external-required-false-present-receives-values.test.yaml` | EP | A `required: false` entry that resolves to an attached `ON_REQUEST` Environment enters it with the entry's value. |

#### Constraint 7 over the combined Job (§3.2, §3.2.1)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-31 | `3.2.1--attached-always-required-supplied-by-every-step.test.yaml` | EP | An attached `ALWAYS` Environment with a parameter without `default`, supplied by every Step, runs. |
| JB-32 | `3.2.1--attached-always-required-not-supplied.invalid.test.yaml` | EP | The same Environment with one Step not supplying it is rejected. |
| JB-33 | `3.2.1--attached-on-request-required-not-requested.test.yaml` | EP | An attached `ON_REQUEST` Environment with a required parameter, requested by no Step, runs. |
| JB-34 | `3.2.1--attached-on-request-required-not-supplied.invalid.test.yaml` | EP | The same Environment requested without the parameter is rejected. |
| JB-35 | `3.2--by-default-entry-disabled-by-expression-declines.test.yaml` | EP, EX | Step A's entry for a `BY_DEFAULT` Job Environment with a required parameter resolves `enableIf` to `false`, so A declines it and constraint 7 does not apply to A; Step B's entry is enabled and supplies the value. The Job runs. |
| JB-92 | `3.2.1--attached-always-required-entry-disabled.invalid.test.yaml` | EP, EX | A Step's entry for an attached `ALWAYS` Environment has an `enableIf` that resolves to `false`; the disabled entry's name is resolved, and the submission is rejected because no Step can leave an `ALWAYS` Environment out (§3.2 item 3.2, §3.2.1). |
| JB-116 | `3.2.1--attached-by-default-required-disabled-not-required.test.yaml` | EP; env EP, EX | An attached `BY_DEFAULT` Environment with a parameter without `default` and an `enableIf` over its own Job Parameter that resolves `false`: disabled, so no Step need supply it; the Job runs without entering it. |
| JB-102 | `3.2--constraint-7-constant-expression-enable-if.invalid.test.yaml` | EP, EX | The template of JT-152, which passes template validation; at job creation the entry resolves `true` and constraint 7 rejects the Job. |
| JB-107 | `3.2--constraint-7-fails-whatever-enable-if.invalid.test.yaml` | EP, EX | An `ALWAYS` Job Environment with two parameters without `default`; the only entry has an expression `enableIf` and supplies one. Enabled, constraint 7 fails; disabled, the entry is an error for an `ALWAYS` Environment. Rejected, at template validation or job creation (item 18). |
| JB-113 | `3.2--required-param-env-enable-if-expression-false-not-required.test.yaml` | EP, EX | The template of JT-158 with the `enableIf` resolving `false`: the Environment is disabled, constraint 7 does not apply, and the Job runs without entering it. |

#### `activation` at run time (§4 item 4)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-36 | `4--on-request-entered-by-requesting-step.test.yaml` | EP | The requesting Step's Session prints the `ON_REQUEST` Environment's `onEnter` sentinel with its value. |
| JB-37 | `4--on-request-not-entered-by-other-step.test.yaml` | EP | A second Step that does not request it never prints the sentinel with the `default` value (`forbidden`). |
| JB-38 | `4--on-request-variables-not-set-for-other-step.test.yaml` | EP | The Environment's `variables` are not set in the non-requesting Step's Task. |
| JB-39 | `4--always-entered-by-step-without-entry.test.yaml` | EP | A Step with no entry still enters an `ALWAYS` Environment, with its `default`. |
| JB-40 | `4--attached-on-request-not-entered-without-request.test.yaml` | EP | An attached `ON_REQUEST` Environment that no Step requests is never entered. |
| JB-128 | `4--always-enable-if-false-for-step.invalid.test.yaml` | EP, EX | An `ALWAYS` Job Environment's expression `enableIf` is `false` for Step B, which takes the default; an `ALWAYS` Environment cannot be disabled, so the Job is rejected at job creation (§4 item 6, §3.2.2 item 6). |
| JB-129 | `4--always-enable-if-true-every-step.test.yaml` | EP, EX | The same Environment with an `enableIf` that is `true` for every Step: not an error, and both Steps' Sessions enter it, A with its own value and B with the `default`. |
| JB-130 | `4--by-default-enable-if-false-not-entered.test.yaml` | EP, EX | An explicit `activation: BY_DEFAULT` behaves as an omitted one (JB-93): the Step for which the `enableIf` is `false` does not enter the Environment, and the Job runs. |
| JB-131 | `4--attached-always-enable-if-false.invalid.test.yaml` | EP; env EP, EX | An attached `ALWAYS` Environment whose `enableIf` over its own `Env.Param.*` is `false` for Step B; the submission is rejected. |
| JB-41 | `4--on-request-keeps-order.test.yaml` | EP | `runOn: [posix]`. `BY_DEFAULT` J1, `ON_REQUEST` J2, `BY_DEFAULT` J3; a requesting Step's Task prints `J1J2J3`, built by each `onEnter` appending to a variable. |

#### `enableIf` on the entry (§3.2 item 3.2)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-42 | `3.2--enable-if-true-enters.test.yaml` | EP, EX | An entry whose `enableIf` resolves `true` causes its `ON_REQUEST` Environment to be entered with the value. |
| JB-43 | `3.2--enable-if-false-not-entered.test.yaml` | EP, EX | An entry whose `enableIf` resolves `false` leaves its `ON_REQUEST` Environment unentered. |
| JB-44 | `3.2--always-entry-disabled-by-expression.invalid.test.yaml` | EP, EX | A Step's entry for an `ALWAYS` Job Environment has an expression `enableIf` that resolves to `false` when the Job is created; rejected, naming the Step and the Environment (§3.2 item 3.2). |
| JB-45 | `3.2--enable-if-false-skips-missing-required.test.yaml` | EP, EX | A disabled `required: true` entry naming an Environment nothing attaches is not an error; the Task runs. |
| JB-46 | `3.2--enable-if-null.invalid.test.yaml` | EP, EX | An `enableIf` that resolves to `null` at job creation is rejected. |

#### Environment `enableIf` at run time (§4 item 6)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-93 | `4--env-enable-if-per-step.test.yaml` | EP, EX | A Job Environment's `enableIf` over `Env.Param.Packages` is entered by the Step that supplies packages and not by the Step that takes the default. |
| JB-94 | `4--attached-env-enable-if-per-step.test.yaml` | EP, EX | The same for an attached Environment. |
| JB-95 | `4--env-enable-if-false-variables-not-set.test.yaml` | EP, EX | A disabled Environment's `variables` are not set for the Step. |
| JB-96 | `4--step-env-enable-if-false-not-entered.test.yaml` | EP, EX | A Step Environment whose `enableIf` reads the Step's `let` and is false is not entered. |
| JB-97 | `4--env-enable-if-null.invalid.test.yaml` | EP, EX | An Environment `enableIf` that resolves to `null` is rejected at job creation. |
| JB-98 | `3.3.3--env-enable-if-false-requirements-not-applied.test.yaml` | EP, EX | A disabled Environment adds none of its `hostRequirements`; a conflicting pair is not a conflict. |
| JB-99 | `7.3.1--env-names-includes-disabled-environment.test.yaml` | EP, EX | `Job.EnvNames` lists a disabled Environment. |
| JB-100 | `4--env-enable-if-false-second-wrapper-allowed.test.yaml` | EP, WA, EX | Two wrapping Job Environments, one with `enableIf: false`: one wrapper in the stack, so the Job runs, wrapped by the enabled one. |
| JB-101 | `4--env-enable-if-expression-second-wrapper-rejected.invalid.test.yaml` | EP, WA, EX | The same with an expression `enableIf` that resolves `true`: two wrappers in the stack, rejected at job creation. |
| JB-103 | `4--env-enable-if-expression-false-second-wrapper-allowed.test.yaml` | EP, WA, EX | The template of JT-150 with the expression resolving `false`: one wrapper in the stack, so the Job runs, wrapped by the enabled one. |
| JB-104 | `4--enable-if-path-posix-semantics.test.yaml` | EP, EX | An entry's, a Job Environment's, and a Step Environment's `enableIf` (the last through a Step `let`) each treat `path('C:\x\leaf')` as one component, which holds only under POSIX semantics; all three Environments are entered (§3.2 item 3.2, §4 item 6: template scope). See item 17. |
| JB-105 | `4--env-enable-if-two-certain-wrappers-third-undetermined.invalid.test.yaml` | EP, WA, EX | Two wrapping Job Environments without `enableIf` and a third with an expression `enableIf`: the single-layer rule fails whatever the third resolves to; rejected, at template validation or job creation (item 18). |
| JB-106 | `4--entry-certain-wrapper-second-layer.invalid.test.yaml` | EP, WA, EX | As JT-151 with the entry's `enableIf: true`: both wrappers are certainly entered; rejected, at template validation or job creation (item 18). |
| JB-108 | `3.2.2--env-enable-if-false-values-not-checked.test.yaml` | EP, EX | The template of JT-157 with the `enableIf` resolving `false`: the out-of-range value is not checked, the Environment is not entered, and the Job runs (§3.2.2). |
| JB-109 | `3.2.2--env-enable-if-true-values-checked.invalid.test.yaml` | EP, EX | The same with the `enableIf` resolving `true`: the value is checked, and the Job is rejected (constraint 6). |
| JB-110 | `3.2.2--env-enable-if-false-unconvertible-value-not-read.test.yaml` | EP, EX | An INT value resolves to `many`, which does not convert, but the `enableIf` reads only a Job Parameter and is `false`: the Environment is disabled, the value is not checked, and the Job runs (§3.2.2). |
| JB-111 | `4--env-enable-if-reads-raw-path-param.test.yaml` | EP, EX | A Job Environment's `enableIf` over `RawParam.<PATH>` reads the unmapped absolute path; the Environment is entered. |
| JB-112 | `3.2.2--env-enable-if-reads-unconvertible-value.invalid.test.yaml` | EP, EX | The `enableIf` reads the unconvertible value, which is known only at job creation, so its result depends on it and the Job is rejected then (§3.2.2). |
| JB-115 | `4--wrappers-never-enabled-together.test.yaml` | EP, WA, EX | Two wrapping `BY_DEFAULT` Job Environments, each with a parameter without `default`, whose `enableIf` conditions are never true together; the disabled one is held neither to constraint 7 nor to the single-layer rule, and the Job runs wrapped by the other. |

#### `Job.EnvNames` (§7.3.1)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-47 | `7.3.1--env-names-job-environments-in-order.test.yaml` | EP, EX | No attached Environments; Job Environments `B`, `A`; the Task prints `B,A`. |
| JB-48 | `7.3.1--env-names-excludes-step-environments.test.yaml` | EP, EX | A Step Environment's name does not appear. |
| JB-49 | `7.3.1--env-names-includes-attached.test.yaml` | EP, EX | Attached `Q`, then `R`, and Job Environments `J1`, `J2`; the line is `Q,R,J1,J2`: the attached Environments come first, in the order they are attached (§1.1 item 7). |
| JB-50 | `7.3.1--env-names-includes-unrequested-on-request.test.yaml` | EP, EX | An `ON_REQUEST` Environment the Step does not request is listed. |
| JB-51 | `7.3.1--env-names-repeats-shared-attached-name.test.yaml` | EP, EX | Two attached Environments named `X` and no entry naming `X`; the line is `X,X`. |
| JB-52 | `7.3.1--env-names-in-environment-script.test.yaml` | EP, EX | An attached Environment `E`'s `onEnter` prints `Job.EnvNames`, `E,J`, which includes the Job Template's Environment `J` after it. |
| JB-53 | `7.3.1--env-names-in-step-let-feeds-value.test.yaml` | EP, EX | A Step `let` reading `Job.EnvNames` feeds a `parameters` value that `onEnter` prints. |
| JB-86 | `7.3.1--env-names-expands-to-argv.test.yaml` | EP, EX | `runOn: [posix]`. An `args` item `"{{Job.EnvNames}}"` in a Step script expands to one argv element per name (Expression Language §1.3.2 flattens a list result in an `args` item). |

#### Path values (§4.5)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-54 | `4.5--path-value-mapped-in-env-param-posix.test.yaml` | EP | `runOn: [posix]`. A PATH value from `"{{RawParam.Dir}}"` is path-mapped in `Env.Param.Dir`. |
| JB-55 | `4.5--path-value-mapped-in-env-param-windows.test.yaml` | EP | `runOn: [windows]`. As JB-54 with Windows paths. |
| JB-56 | `4.5--path-value-unmapped-in-env-raw-param-posix.test.yaml` | EP | `runOn: [posix]`. A PATH parameter whose `default` is `"{{RawParam.Dir}}"`, taken by a Step with no entry, is unmapped in `Env.RawParam.Dir`. |
| JB-57 | `4.5--path-value-unmapped-in-env-raw-param-windows.test.yaml` | EP | `runOn: [windows]`. As JB-56 with Windows paths. |
| JB-58 | `4.5--list-path-elements-mapped-posix.test.yaml` | EP, EX | `runOn: [posix]`. Each element of a LIST[PATH] value is mapped in `Env.Param.*`. |
| JB-59 | `4.5--list-path-elements-mapped-windows.test.yaml` | EP, EX | `runOn: [windows]`. As JB-58 with Windows paths. |
| JB-60 | `4.5--relative-path-value.test.yaml` | EP | A supplied relative PATH value `relative/dir` for an attached Environment's parameter is accepted and read unchanged (§4.5 item 3). |
| JB-61 | `4.5--relative-literal-path-default.test.yaml` | EP | A relative literal PATH `default: relative/dir` is accepted and taken by a Step that supplies nothing. |
| JB-62 | `4.5--path-allowed-values-checked-unmapped-posix.test.yaml` | EP | `runOn: [posix]`. `allowedValues` lists the unmapped path; a mapping rule changes it on the host; the Job runs and `Env.Param` prints the mapped path. |
| JB-63 | `4.5--path-uri-value.test.yaml` | EP, EX | A PATH value `s3://bucket/key` is accepted, and `Env.RawParam` prints it unchanged. Both documents list `EXPR` (see ambiguity 10). |
| JB-157 | `4.5--path-absolute-posix.test.yaml` | EP, EX | A POSIX PATH value `/mnt/proj` is accepted on any host and read unchanged. |
| JB-158 | `4.5--path-absolute-windows-drive.test.yaml` | EP, EX | A Windows drive PATH value `C:\proj` is accepted on any host, including a POSIX one. |
| JB-159 | `4.5--path-absolute-windows-drive-forward-slash.test.yaml` | EP, EX | `C:/proj` is accepted on any host. |
| JB-160 | `4.5--path-absolute-windows-unc.test.yaml` | EP, EX | A UNC PATH value `\\server\share\proj` is accepted on any host. |
| JB-161 | `4.5--list-path-mixed-formats.test.yaml` | EP, EX | A LIST[PATH] value mixing POSIX, Windows drive, UNC, and relative paths is accepted. |
| JB-162 | `4.5--path-relative-windows-backslash.test.yaml` | EP, EX | `relative\dir` is accepted. |
| JB-163 | `4.5--path-relative-windows-drive.test.yaml` | EP, EX | The drive-relative `C:dir` is accepted. |
| JB-164 | `4.5--path-relative-windows-rooted.test.yaml` | EP, EX | The drive-less rooted `\dir` is accepted. |

#### Host requirements (§3.3.3, §4 item 5)

Capability names use a custom prefix (`conformance:attr.flavor`, `conformance:amount.widgets`) so that no runner
matches them against the local host.

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-64 | `3.3.3--non-conflicting-requirements-run.test.yaml` | EP | Step `anyOf: [a, b]`, Environment `anyOf: ["{{Env.Param.Flavor}}"]` with `Flavor: a`; the Job runs. |
| JB-65 | `3.3.3--amount-min-exceeds-max.invalid.test.yaml` | EP | Step amount `max: 1`, Environment amount `min: 2`; rejected. |
| JB-66 | `3.3.3--attribute-any-of-empty-intersection.invalid.test.yaml` | EP | Step `anyOf: [linux]`, Environment `anyOf: [windows]` on `attr.worker.os.family`; no common value; rejected (§3.3.3 item 2.1). |
| JB-67 | `3.3.3--conflict-resolved-from-env-param.invalid.test.yaml` | EP | Environment `anyOf: ["{{Env.Param.Os}}"]` on `attr.worker.os.family` resolves to `windows`, outside the Step's `[linux, macos]`; the conflict appears only after resolution; rejected. |
| JB-68 | `3.3.3--conflict-between-two-environments.invalid.test.yaml` | EP | Two Environments the Step enters require disjoint `anyOf` of `attr.worker.os.family`; rejected. |
| JB-69 | `3.3.3--attached-environment-conflict.invalid.test.yaml` | EP | An attached Environment's `attr.worker.os.family` requirement conflicts with the Step's; rejected. |
| JB-70 | `3.3.3--same-capability-in-step-and-environment.test.yaml` | EP | Step and Environment each require amount `min: 1` of the same capability; not a duplicate-name error; the Job runs. |
| JB-71 | `3.3.3--any-of-and-all-of-not-combined.test.yaml` | EP | Step `anyOf` and Environment `allOf` on one attribute; not an error; the Job runs. |
| JB-72 | `3.3.3--on-request-requirements-not-applied.test.yaml` | EP | An `ON_REQUEST` Environment's requirements conflict with a non-requesting Step's own; the Job runs. |
| JB-73 | `4--resolved-host-requirements-duplicate-name.invalid.test.yaml` | EP | Two attribute names `"{{Env.Param.First}}"` and `"{{Env.Param.Second}}"` resolve to the same name for a Step; rejected (§3.3 constraint 4, within one source, per Step). |
| JB-88 | `3.3.3--any-of-intersection-ignores-case.test.yaml` | EP | Step `anyOf: [A]` and Environment `anyOf: [a]` intersect, since values compare ignoring case; the Job runs. |
| JB-89 | `3.3.3--capability-name-compared-ignoring-case.invalid.test.yaml` | EP | Step `attr.worker.OS.family` `anyOf: [linux]` and Environment `attr.worker.os.family` `anyOf: [windows]` are one capability; rejected. |
| JB-90 | `3.3.3--disabled-entry-requirements-not-applied.test.yaml` | EP, EX | A disabled entry for an `ON_REQUEST` Environment whose requirements conflict with the Step's; no conflict, the Job runs, the Environment is not entered. |
| JB-91 | `4--resolved-host-requirements-negative-min.invalid.test.yaml` | EP; env EP, FB1 | An attached Environment's amount `min: "{{Env.Param.N}}"` resolves to `-1` for the Step; rejected (§3.3.1). |
| JB-119 | `3.3.3--disjoint-any-of-multi-valued-run.test.yaml` | EP | Step `anyOf: [a]` and Environment `anyOf: [b]` on a custom attribute are `allOf: [a, b]`, not a conflict; the Job runs (§3.3.3 item 2.2). |
| JB-120 | `3.3.3--attribute-combination-order-independent.test.yaml` | EP | `anyOf: [a]`, `anyOf: [b, c]`, and `allOf: [x]` on a custom attribute from three sources combine without conflict, whatever the order; the Job runs. |
| JB-121 | `3.3.3--os-family-all-of-and-any-of-conflict.invalid.test.yaml` | EP | Step `allOf: [linux]` and Environment `anyOf: [windows, macos]` on `attr.worker.os.family`; no common value; rejected. |
| JB-132 | `3.3--amount-resolves-empty-discarded.test.yaml` | EP, EX, FB1 | A Step's only amount, `min: "{{ 1 if Param.Gpus != '' else None }}"` with no `max`, resolves to neither bound and is discarded; the Job runs (§3.3). |
| JB-133 | `3.3--attribute-any-of-resolves-empty.invalid.test.yaml` | EP, EX | A Step's only attribute, whose only `anyOf` value resolves to `null`, leaves `anyOf` empty; the Job is rejected, not run with the attribute discarded (§3.3 item 2). |
| JB-134 | `3.3--environment-requirements-resolve-empty.test.yaml` | EP; env EP, EX, FB1 | An attached Environment's only requirement, an amount whose `min` resolves to `null` for the Step and which has no `max`, is discarded; the Environment is entered and the Job runs (§3.3, §3.3.3). |
| JB-135 | `3.3.2--any-of-expression-null-discarded.test.yaml` | EP, EX | A Job Environment's only attribute has only an `anyOf` written as one expression, which resolves to `null`; the field is omitted, the attribute is discarded, and the Job runs (§3.3 item 2). |
| JB-136 | `3.3.2--any-of-expression-empty-list.invalid.test.yaml` | EP, EX | A Step's `anyOf: "{{ [f for f in [Param.Flavor] if f != ''] }}"` resolves to `[]` with `Flavor` empty; rejected (§3.3 item 3). |
| JB-137 | `3.3.3--all-of-expression-combined.test.yaml` | EP, EX | A Step's `allOf: "{{ [Param.Flavor, 'x'] }}"` resolves to `[a, x]` and combines with a Job Environment's `allOf: [b]` on the same custom attribute; the Job runs (§3.3.3 item 2.2). |
| JB-138 | `3.3--duplicate-amount-name-one-discarded.test.yaml` | EP, EX, FB1 | A Job Environment's `hostRequirements` name `conformance:amount.widgets` twice; the second amount's format-string `min` and `max` both resolve to `null`, so it is discarded, one amount with the name remains, and the Job runs (§3.3 constraint 3, applied after discarding). |
| JB-139 | `3.2--by-default-entry-disabled-literal-not-entered.test.yaml` | EP, EX | A Step's entry with `enableIf: false` for a `BY_DEFAULT` Job Environment declines it: the Step's Sessions do not enter it, with the entry's value or the `default` (§3.2 item 3.2). |
| JB-140 | `3.2.1--attached-by-default-entry-disabled-declines.test.yaml` | EP, EX | A disabled entry naming an attached `BY_DEFAULT` Environment is resolved and declines it, so the Step's Sessions do not enter it (§3.2 item 3.2, §3.2.1). |
| JB-141 | `3.2.1--attached-always-entry-disabled-literal.invalid.test.yaml` | EP, EX | A literal `enableIf: false` entry naming an attached `ALWAYS` Environment cannot be judged at template validation; when the Job is created the name resolves to it and the submission is rejected (§3.2 item 3.2, §3.2.1). |
| JB-142 | `3.3.3--by-default-declined-requirements-not-applied.test.yaml` | EP, EX | A Step that declines a `BY_DEFAULT` Job Environment gets none of its `hostRequirements`, so its conflicting `anyOf` does not reject the Job (§3.3.3). |
| JB-143 | `3.2--expression-entry-disabled-parameters-not-checked.test.yaml` | EP, EX | The entry of JT-184 resolves `enableIf` to `false` at job creation; its parameters are not checked, and the Job runs without entering the declined Environment (§3.2 item 3.2). |
| JB-144 | `3.2--expression-entry-enabled-parameters-checked.invalid.test.yaml` | EP, EX | The entry of JT-184 resolves `enableIf` to `true`; its undeclared key and its value outside `allowedValues` are rejected at job creation (constraints 5, 6). |
| JB-145 | `2.10--range-expr-min-length-canonical.invalid.test.yaml` | EP, EX | In a document that lists `ENV_PARAMS`, a RANGE_EXPR Job Parameter's `minLength: 4` is checked against the canonical form of `1-3:2`, which is `1,3`; rejected (§2.10). EXPR's `2.10--range-expr-min-length-written-only` runs the same Job without `ENV_PARAMS`. |
| JB-155 | `2.10--range-expr-merged-length-written-only.test.yaml` | EP, EX; env EX | A merged RANGE_EXPR Job Parameter: `minLength: 4` from an Environment Template without `ENV_PARAMS` is checked against `1-3:2` as written only; the Job runs (§2.10, §1.2.1). |
| JB-156 | `2.10--range-expr-merged-length-canonical.invalid.test.yaml` | EP, EX; env EX | The same with `minLength: 4` in the Job Template, which lists `ENV_PARAMS`: the canonical form `1,3` is too short; rejected. |
| JB-146 | `3.2.1--unreachable-attached-always-required.invalid.test.yaml` | EP; env EP, EX | An attached `ALWAYS` Environment named like a Job Environment, so unreachable, with a parameter without `default`: every Step's Sessions enter it and none can supply the value, so the submission is rejected (§3.2.1 item 4). |
| JB-147 | `3.3.2--all-of-expression-os-family-two-values.invalid.test.yaml` | EP, EX | A Step's `allOf: "{{ ['linux', Param.Second] }}"` on `attr.worker.os.family` passes template validation and resolves to two values when the Job is created; a host has one value of that attribute, so the submission is rejected (§3.3.2.1). The literal `allOf: [linux, windows]` is the base suite's `3.3--allof-multiple-single-value-attr.invalid`. |

#### Extensions per document and backward compatibility (§1.2, RFC §Backward compatibility)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-74 | `1.2--job-template-without-extension-takes-defaults.test.yaml` | — | A Job Template without `ENV_PARAMS` runs with an attached `ALWAYS` Environment that lists it; `onEnter` prints the `default`. |
| JB-75 | `1.2--job-template-without-extension-skips-on-request.test.yaml` | — | The same with `ON_REQUEST`; the Environment is never entered. |

#### With `WRAP_ACTIONS` (§4, §7.3.1; How Jobs Are Run, wrap hooks per Session stack)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-76 | `7.3.1--wrap-hook-reads-wrapper-env-param.test.yaml` | EP, WA, EX | A wrapping Environment's `onWrapTaskRun` prints its own `Env.Param.Image` supplied by the Step. |
| JB-77 | `4--on-request-wrapper-not-applied-to-other-step.test.yaml` | EP, WA, EX | An `ON_REQUEST` wrapping Environment wraps the requesting Step's Task and not the other Step's (the wrap sentinel is absent from the other Step's output). |
| JB-173 | `4--pre-extension-wrapper-disabled-entry-second-layer.invalid.test.yaml` | EP, WA, EX; env WA, EX | `runOn: [posix]`. An attached wrapping Environment whose document lists `WRAP_ACTIONS` but not `ENV_PARAMS` behaves as `ALWAYS`, so a Step's disabled entry for it does not remove it, and with a wrapping Job Environment the Step has two layers; rejected (§4 item 4, RFC 0008). |
| JB-174 | `4--attached-by-default-wrapper-disabled-entry-declined.test.yaml` | EP, WA, EX; env EP, WA, EX | `runOn: [posix]`. The same with `ENV_PARAMS` in the attached Environment's document, so it is `BY_DEFAULT` and the entry declines it: one layer, and the Job runs wrapped by the Job Environment. |

#### Exclusive groups (§4 item 7)

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-148 | `4--exclusive-group-first-attached-wins.test.yaml` | EP, EX | Conda and Docker share an `exclusiveGroup`, attached Conda first, both enabled: the Step enters only Conda. |
| JB-149 | `4--exclusive-group-reverse-order.test.yaml` | EP, EX | The same with Docker attached first: the Step enters only Docker. |
| JB-150 | `4--exclusive-group-falls-through.test.yaml` | EP, EX | Conda is first but its `enableIf` is false for the Step, so the Step enters Docker. |
| JB-151 | `4--exclusive-group-superseded-not-held-to-constraint-7.test.yaml` | EP, EX | A superseded `BY_DEFAULT` Environment whose required parameter the Step does not supply does not reject the Job. |
| JB-152 | `4--exclusive-group-job-environments.test.yaml` | EP, EX | Two Job Environments in one group: only the first in `jobEnvironments` order is entered. |
| JB-153 | `4--exclusive-group-separate-groups.test.yaml` | EP, EX | Environments in different groups are both entered. |
| JB-154 | `4--exclusive-group-superseded-enable-if-not-evaluated.test.yaml` | EP, EX | A superseded Environment's `enableIf`, which would depend on a missing value, is not evaluated. |

#### Basic Examples (RFC §Basic Examples)

Each example becomes one or two runnable tests that replace `conda`, `docker`, and `license-checkout` with `echo`
sentinels.

| ID | File | Exts | Assertion |
|---|---|---|---|
| JB-78 | `4.5--example-queue-conda-step-configures.test.yaml` | EP | *A queue Conda Environment that each Step configures*: a Step with no entry gets `CondaPackages`; a Step with an entry gets its own `Packages`. |
| JB-79 | `3.2.1--example-steps-own-software-conda-queue.test.yaml` | EP | *A Job Template whose Steps each ask for their own software*, with only `Conda` attached: each Step's `onEnter` prints its own `Packages`; the `Docker` entries are ignored. |
| JB-80 | `3.2.1--example-steps-own-software-no-queue-environment.test.yaml` | EP | The same Job Template with nothing attached runs unchanged. |
| JB-81 | `4--example-parameterized-job-environment.test.yaml` | EP | *One parameterized Job Environment serving several Steps*: `BeautyPass` prints `arnold 1`, `VolumePass` prints `redshift 2`, `Composite` never enters `RenderLicense`. |
| JB-82 | `3.2--example-choose-docker-when-both.test.yaml` | EP, EX | An entry whose `enableIf` reads `Job.EnvNames`: with `Conda` and `Docker` attached (both `ON_REQUEST`), the `Conda` entry is disabled and `Conda` is not entered. No longer a Basic Example. |
| JB-83 | `3.2--example-choose-conda-when-alone.test.yaml` | EP, EX | The same Job Template with only `Conda` attached enters it with `colmap=3.11`. No longer a Basic Example. |
| JB-84 | `3.3.3--example-environment-host-requirements.test.yaml` | EP; env EP, EX, FB1 | *An Environment that states what hosts it needs*: one Step requests `Docker` with `Gpus: all` and one without; both run (requirements resolve per Step without conflict, and the GPU amount, whose `min` resolves to `None`, is discarded for the Step without `Gpus`). |
| JB-85 | `3.2.2--example-execution-per-step-values.test.yaml` | EP | *Execution*: `DecodeFrames` and `SolveSfM` each enter `Conda` once with their own `Packages`, and `onExit` follows each. |

## Validation table coverage

The rows map the RFC's [Validation](../../../rfcs/0010-environment-parameters.md#validation) table to tests. Row numbers
are stable: a row added later is listed at the end with a note on where it falls in the RFC's table, and a row the RFC
has since dropped or merged keeps its number with a note. So the counts differ, and one RFC row may map to several rows
here (the constraints 5 and 6 row is V19 and V45).

| # | Validation rule (abridged) | Checked at | Tests |
|---|---|---|---|
| V1 | `ENV_PARAMS` listed by any document using Environment `envParameterDefinitions`, `activation`, `hostRequirements`, `enableIf`, or `exclusiveGroup`; `environment:` or `step:` entries; `Job.EnvNames`, `Env.Param.*`, or `Env.RawParam.*`; an `anyOf` or `allOf` written as one expression; or an empty `hostRequirements` | Template validation | JT-01–JT-04, JT-125, JT-139, ET-03–ET-05, ET-50; `Job.EnvNames`: JT-10; one expression: JT-186; empty `hostRequirements`: base `3.3--empty-host-requirements.invalid`; per-document: ET-01, JB-74, JB-75, JB-19, JB-20; Environment Template `extensions` and `$schema` keys: ET-01, ET-02, ET-32, ET-33 |
| V2 | Environment `envParameterDefinitions`: 1–50, unique names, not on `stepEnvironments`, permitted types and fields | Template validation | JT-15–JT-26, JT-120, ET-07–ET-12, ET-34, ET-35, ET-37 |
| V3 | `activation` is `ALWAYS`, `BY_DEFAULT`, or `ON_REQUEST`, not on `stepEnvironments` | Template validation | JT-40–JT-43, JT-171, JT-180, ET-13, ET-14, ET-45, ET-47; run time: JB-36–JB-41, JB-130 |
| V4 | Environment `hostRequirements`: §3.3 shape, not on `stepEnvironments`; references only the document's `RawParam.*`, non-PATH `Param.*`, `Job.Name`, `Job.EnvNames`, and the enclosing Environment's own `Env.RawParam.*` of any type and non-PATH `Env.Param.*` | Template validation | JT-44–JT-54, JT-117–JT-119, JT-155, JT-169, ET-15–ET-17, ET-38 |
| V5 | An Environment's resolved `hostRequirements` satisfy §3.3.1 and §3.3.2 per Step, once an amount whose `min` and `max` both resolve to `null`, or an attribute whose `anyOf` and `allOf` resolve to `null`, is discarded, as from a Step's own (§3.3); the duplicate-name check of §3.3 constraints 3 and 4 applies to the requirements left after discarding | Job creation | JB-73, JB-91; discarded: JB-132, JB-134, JB-135; a discarded amount is not a duplicate: JB-138 |
| V6 | Combined host requirements are satisfiable: `min` ≤ `max` for each amount, and a common value for `attr.worker.os.family` and `attr.worker.cpu.arch` (§3.3.3 items 1, 2.1) | Job creation | JB-65–JB-69, JB-89, JB-121; non-conflicts: JB-64, JB-70–JB-72, JB-84, JB-88, JB-90, JB-119, JB-120 |
| V7 | Removed: the RFC no longer specifies composition with `CONTROL_FLOW` (see its *Extensions specified after this one*) | — | — |
| V8 | `default` references only `Param.*` / `RawParam.*` of the same document's Job Parameters | Template validation | JT-27–JT-33, JT-121, ET-18–ET-22; merged value: JB-06, JB-07 |
| V9 | A literal `default` satisfies its type and constraints, whether or not any Step uses it, and whatever any `enableIf` decides | Template validation | JT-34–JT-36, JT-168, ET-23 |
| V10 | `Env.Param.*` / `Env.RawParam.*` name a parameter of the enclosing Environment, and appear only inside it | Template validation | JT-55–JT-64, JT-123, ET-27, ET-28, ET-31; run time: JB-01–JB-04, JB-76 |
| V11 | A `parameters` value or `enableIf` references only `RawParam.*`, non-PATH `Param.*`, and `Job.Name`, `Job.EnvNames`, `Step.Name`, Step `let`; never `Task.*`, `Session.*`, `Env.*` | Template validation | JT-105–JT-116, JT-122; run time: JB-14, JB-53 |
| V12 | Merged into V4: the RFC table now has one row for Environment `hostRequirements` | — | — |
| V13 | `Job.EnvNames` only inside `{{ }}` or an expression field, not in an Environment parameter `default` | Template validation | JT-10, JT-33, JT-65–JT-68, ET-22, ET-29; contents: JB-47–JB-53, JB-86 (see ambiguity 7 for "inside `{{ }}`") |
| V14 | `<StepDependency>` has exactly one of `dependsOn` / `step` / `environment`; `required`, `enableIf`, `parameters` only with `environment` (constraint 1) | Template validation | JT-69–JT-74, JT-126–JT-129, JT-134 |
| V15 | `enableIf` is an expression field of type `bool` (constraint 9, §7.6) | Template validation | JT-95–JT-98, JT-149 |
| V16 | `enableIf` does not resolve to `null` | Job creation | JB-46 |
| V17 | Not the Step's own Step Environment; no duplicates; 1–50 `parameters` (constraints 2–4) | Template validation | JT-75–JT-80 |
| V18 | `required: false` not on an entry naming a Job Environment (constraint 8) | Template validation | JT-92–JT-94 |
| V19 | Keys and literal values of `parameters` for a Job Environment (constraints 5, 6) | Template validation | JT-81–JT-91; resolved format strings at job creation: JB-13; constraint 6 and the value's type skipped for an Environment whose `enableIf` is `false`: JT-156, JT-157, JT-165; constraint 5 and the value's form still checked: JT-163, JT-164 |
| V20 | Required parameters of `ALWAYS` Environments supplied by every Step, of `BY_DEFAULT` ones by every Step that does not decline them, of `ON_REQUEST` ones by every requester, except Steps for which the Environment is disabled; Job Environments and, after resolution, attached Environments (constraint 7, §3.2.1, §3.2.2) | Job creation; for a Job Environment, also template validation when the failure holds however every undetermined entry or Environment `enableIf` resolves (§7.6 rule 5) | JT-99–JT-102, JT-104, JT-152, JB-31–JB-34, JB-102, JB-107; declined by a disabled entry: JT-103, JB-35, JB-115; disabled Environments: JT-148, JT-158, JT-162, JB-113, JB-115, JB-116 |
| V21 | External resolution: missing with `required: true`, or ambiguous (§3.2.1) | Job creation | JB-16, JB-21; accepted forms: JB-15, JB-17, JB-22, JB-23, JB-30, JB-45, JB-87 |
| V22 | Keys and values for an external Environment; a key the resolved Environment lacks is an error even with `required: false`, unless the Environment declares no parameters: then a `required: false` entry's `parameters` are ignored, and a `required: true` entry's are an error | Job creation | JB-18, JB-24–JB-26, JB-165, JB-166; accepted: JB-20; ignored: JB-19, JB-167, JB-168 |
| V23 | Removed: `ENV_PARAMS` requires `EXPR`, so no requesting document lacks `EXPR`; see V36 | — | — |
| V24 | A format-string value or `default` for a list-typed parameter is one `{{ }}` expression | Template validation for `default`s and Job Environment entries; job creation for external | JT-37, JT-38, JT-91, ET-24, JB-29 |
| V25 | A resolved, non-literal `default` satisfies its type and constraints for each Step that takes it | Job creation | JB-11, JB-12 |
| V26 | PATH / LIST[PATH] values used as given, not required to be absolute; string constraints on the unmapped value, including an unused literal `default` | Job creation | JB-60–JB-63, JB-157–JB-164; mapping: JB-54–JB-59 |
| V27 | Merged into V20: the RFC table now has one row for constraint 7 | — | — |
| V28 | Removed: the RFC no longer specifies composition with `SERVICE` | — | — |
| V29 | Removed: the RFC no longer specifies composition with `SERVICE`. RFC 0008's wrap-hook rules apply per Session stack, which with `activation` and `enableIf` is per Step's Environment set | Job creation | JB-77 |
| V30 | Removed: Environment `enableIf` is now part of this RFC; see V32, V33 | — | — |
| V31 | A `step:` entry obeys every rule of the `dependsOn:` entry it is a synonym of; a `step:` and a `dependsOn:` entry naming one Step are duplicates (§3.2 item 2). Listed after V30 so that existing row numbers are stable; in the RFC table it follows V14 | Template validation | JT-124, JT-130–JT-133 |
| V32 | Environment `enableIf` (listed after V31 so that existing row numbers are stable, as V33 and V34 are): `ENV_PARAMS`; an expression field of type `bool` (§7.6); the scopes of §7.3.2 | Template validation | JT-135–JT-137, JT-139–JT-147, ET-39–ET-41, JT-153, JT-154; run time: JB-111 |
| V33 | Environment `enableIf` does not resolve to `null`, per Step | Job creation | JB-97; run-time effect: JB-93–JB-96, JB-98, JB-99 |
| V34 | A check over a Step's Environment set, such as the `WRAP_ACTIONS` single-layer rule, where an Environment's `enableIf` decides membership | Job creation; before then only when the violation holds however every undetermined `enableIf` resolves (§7.6 rule 5) | JT-150, JT-151, JB-100, JB-101, JB-103, JB-105, JB-106 |
| V35 | An Environment disabled for a Step (its `enableIf` is `false` with the values that are known, or it is superseded) is not held to constraint 7, and the Step's effective values for it are not checked; one whose `enableIf` depends on a missing, unresolvable, or unconvertible value is an error, at template validation when that is known then (§3.2.2). Listed after V34 so that existing row numbers are stable | Template validation for a literal `false` and for a value known then to be missing; job creation otherwise | JT-148, JT-156–JT-158, JT-162, JB-108–JB-110, JB-112, JB-113, JB-115, JB-125, JB-126; superseded: JB-151 |
| V36 | A document that lists `ENV_PARAMS` also lists `EXPR` (§1.1 item 3, §1.2 item 3). Listed after V35 so that existing row numbers are stable | Template validation | JT-160, JT-161, ET-43 |
| V37 | The `enableIf` of an `ALWAYS` Environment is not the literal `false` (§4 item 6, §3.2.2 item 6). Listed after V36 so that existing row numbers are stable; in the RFC table it follows V33 | Template validation | JT-170, ET-44; an expression is not rejected then: JT-172 |
| V38 | The `enableIf` of an `ALWAYS` Environment does not resolve to `false` for any Step, for Job Environments and attached Environments (§4 item 6, §3.2.2 item 6). Listed after V37; in the RFC table it follows V37 | Job creation, per Step | JB-128, JB-131; not an error when `true` for every Step: JB-129 |
| V39 | In a document that lists `ENV_PARAMS`, a Step's or an Environment's `hostRequirements` may be `{}` or have empty `amounts` and `attributes` (§3.3 constraint 1); a literal amount with neither `min` nor `max`, or a literal empty `anyOf` or `allOf`, is still rejected (§3.3). Listed after V38 so that existing row numbers are stable; in the RFC table it follows V4 | Template validation | JT-117, JT-173, JT-174, ET-46; still rejected: JT-175, JT-176 |
| V40 | At job creation, an `anyOf` or `allOf` of a Step's or an Environment's `hostRequirements` that has no values after resolution, an expression whose result is an empty list or a list whose items all resolve to `null`, is rejected, naming the Step or Environment and the attribute (§3.3 item 3, §3.3.2). Listed after V39 so that existing row numbers are stable; in the RFC table it follows V5 | Job creation, per Step | JB-133, JB-136 |
| V41 | In a document that lists `ENV_PARAMS`, an `anyOf` or `allOf` written as a string is exactly one `{{ }}` expression, and its static type fits `list[string]?` (§3.3.2). Listed after V40; in the RFC table it follows V39 | Template validation | JT-177; rejected: JT-178, JT-179 |
| V42 | An `anyOf` or `allOf` written as one expression that resolves to `null` is omitted, and an attribute requirement left with neither is discarded; each element of a list result satisfies `<AttributeCapabilityValue>` (§3.3 item 2, §3.3.2). Listed after V41; in the RFC table it follows V40 | Job creation, per Step | JB-135; a list result: JB-137 |
| V43 | A Step's disabled `environment:` entry for an `ALWAYS` Environment is an error naming the Step and the Environment (§3.2 item 3.2). Listed after V42; in the RFC table it follows V38 | Template validation for a literal `false` on an entry naming a Job Environment; otherwise job creation | JT-181, JB-44, JB-92, JB-141; an expression is not rejected at template validation: JT-182 |
| V44 | A Step's disabled `environment:` entry for a `BY_DEFAULT` Environment declines it: its Sessions do not enter it, and constraint 7, its effective-value checks, and the Environment's `hostRequirements` do not apply to the Step (§3.2 item 3.2, §3.3.3). Listed after V43; in the RFC table it follows V43 | Template validation for a literal `false` as far as known then; job creation | JT-103, JB-35, JB-139, JB-140, JB-142 |
| V45 | Constraints 5 and 6 apply only to an enabled entry; a disabled entry's `parameters` are not checked (§3.2 item 3.2). Listed after V44; in the RFC table it is part of the constraints 5 and 6 row | Template validation for an entry whose `enableIf` is absent or `true`; job creation for an expression that resolves to `true` | JT-183, JT-184, JB-143, JB-144 |
| V46 | A RANGE_EXPR value satisfies *minLength* and *maxLength* both as written and in canonical form: every Environment parameter, and a Job Parameter in a document that lists `ENV_PARAMS` (§2.10, §4.5). Listed after V45 | Template validation for literals; job creation | JT-166, JT-167, JB-122, JB-145; merged definitions, each under its own document's rule: JB-155, JB-156; without `ENV_PARAMS`, EXPR `2.10--range-expr-min-length-written-only` |
| V47 | An attached `ALWAYS` Environment named like a Job Environment has every parameter supplied by a `default` (§3.2.1 item 4). Listed after V46 | Job creation | JB-146; `BY_DEFAULT`: JB-123, JB-124 |
| V48 | An expression field (§7.6): parses as one expression without `{{ }}`, its static type fits the target type with only `int` to `float` widening, and a `null` value is an error. Listed after V47 | Template validation | JT-95–JT-98, JT-149, JT-185 |
| V49 | An `allOf` for `attr.worker.os.family` or `attr.worker.cpu.arch` has at most one element: a list as written, and a `<ListExpressionString>` result (§3.3.2.1). Listed after V48; in the RFC table it follows V6 | Template validation for a list; job creation for an expression | base `3.3--allof-multiple-single-value-attr.invalid`; JB-147 |
| V50 | `exclusiveGroup` is an `<Identifier>`, not on `stepEnvironments`, and not on an `ALWAYS` Environment (§4 item 7). Listed after V49; in the RFC table it follows V3 | Template validation | ET-48, ET-49, JT-187, JT-188; undetermined before job creation: JT-189 |
| V51 | Of the Environments a Step's Sessions would enter that share an `exclusiveGroup`, only the first in the Job's Environment order whose `enableIf` is not `false` for the Step is entered; the others are superseded and disabled (§4 item 7, §3.2.2). Listed after V50; in the RFC table it follows V50 | Job creation, per Step | JB-148–JB-154 |
| V52 | An Environment from a document that does not list `ENV_PARAMS` behaves as `activation: ALWAYS` with no `enableIf`: every Step's Sessions enter it, and a disabled `environment:` entry that names it has no effect and is not an error (§4 item 4, §3.2 item 3.2). Listed after V51; in the RFC table it follows V43 | Job creation | JB-169–JB-171, JB-173; enabled entries: JB-19, JB-20, JB-172; the `BY_DEFAULT` contrast: JB-140, JB-174 |

The rule that a Session runs Tasks of a Step only when its Environments and values match (§3.2.2) is a scheduling rule
with no Validation row. Its observable parts are JB-10 and JB-85.

Runtime behaviors in the suite's scope that are not Validation rows are covered as follows: values in `onEnter`,
`onExit`, and `variables` (JB-01–JB-04); defaults from merged Job Parameters (JB-05–JB-08); `ON_REQUEST` entry
(JB-36–JB-41); entry `enableIf` true, false, and `null` (JB-42–JB-46), and a disabled entry declining a `BY_DEFAULT` Environment (JB-139, JB-140) and having no effect on one from a document without `ENV_PARAMS` (JB-169–JB-171); every `enableIf` evaluated in template scope (JB-104); `Job.EnvNames` contents and order (JB-47–JB-53, JB-86);
path mapping in `Env.Param.*` and not `Env.RawParam.*` (JB-54–JB-59); INT `1` vs `"1"` (JB-10); per-document
extensions (JB-74, JB-75); wrap hooks (JB-76, JB-77); host requirements of a disabled entry and case-insensitive combination (JB-88–JB-90). The Basic Examples are JB-78–JB-81, JB-84, JB-85, and JB-148–JB-150, and the pre-extension
`Conda` case of the second example (reduced to one Step with only a `Conda` entry), whose `required: false` entry's
`parameters` are ignored, is JB-19.

## Running the tests

From the repo root:

```bash
# Run just the ENV_PARAMS extension tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/ENV_PARAMS

# Run only the job execution tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/ENV_PARAMS/jobs
```

## Writing your own runner

See the top-level [conformance README](../../README.md) for the standard runner contract. The behavior specific to
`ENV_PARAMS`:

1. Each entry of a test's `environments` list is an Environment Template the scheduler attaches to the Job, in list
   order. The runner must resolve `environment:` entries against them at job creation as §3.2.1 describes, and reject
   the run (non-zero exit) for every job-creation error the RFC lists.
2. `pathMapping` rules apply to PATH and LIST[PATH] Environment parameter values in `Env.Param.*`, mapping them to the
   host's path format. A value is accepted whatever its form; one that matches no rule is unchanged.
3. The runner need not place Sessions by host requirements, but it must compute the combined host requirements of
   each Step at job creation and reject a conflict.

## Rules without a definite test

These rules, or parts of rules, have no planned test with a definite expected outcome. Each says why.

1. **Where attached Environments fall in `Job.EnvNames`, relative to the Job Template's own.** Resolved: §1.1 item 7
   now says that the Environments attached from Environment Templates come before the `jobEnvironments`, in the order
   they are attached, and that a Session enters them in that order. §7.3.1 lists `Job.EnvNames` in the same order.
   JB-49 and JB-52 assert it, and the base suite's `1.1--attached-environments-entered-first` tests the order in which
   a Session enters them.
2. **Whether a template validator may reject a relative literal PATH `default` early.** Resolved: §4.5 item 3 no
   longer requires a PATH value to be absolute, so a relative `default` is valid. JB-61 tests that it is accepted.
3. **§3.2.2 equality and Session sharing.** Whether two Steps with equal values share a Session is up to the
   scheduler, so no test can require it. That a Step never runs Tasks under an Environment entered with other values
   is a requirement, but an implementation may meet it by exiting and entering the Environment again within one
   Session or by starting a new Session, so the output differs between conforming implementations. The suite shows
   only that `1` and `"1"` are both accepted for an INT and print the same value (JB-10).
4. **Placement and reservation by combined host requirements.** That a Session is placed only on a host satisfying the
   combined set, that `amounts` are reserved for the Session, and that amounts "do not add" (one GPU, not two) are
   scheduler behaviors with no output in `openjd run`. Only conflict and resolution rejection (JB-65–JB-69, JB-73,
   JB-89, JB-91) and acceptance of non-conflicts (JB-64, JB-70–JB-72, JB-88, JB-90) are tested.
5. **Warnings.** §3.2.1 item 4 says implementations should warn when an attached Environment shares a name with a Job
   Environment, and §3.2.1 item 1 that they should warn when they ignore a `required: false` entry's `parameters`. The
   test format has no way to assert a warning, and both are "should". JB-22, JB-19, and JB-167 test the behavior
   itself.
6. **The external-entry literal type check at template validation.** §3.2 says that for an entry naming no Job
   Environment, template validation can check "the type of a literal value where its form fixes one (a list is not a
   STRING)". Without the attached Environment, a validator does not know that the parameter is a STRING, so it is
   unclear what this check can reject. The list-for-STRING case is tested at job creation
   (JB-26).
7. **"`Job.EnvNames` ... inside a `{{ }}` expression".** The Validation row requires `Job.EnvNames` to appear inside a
   `{{ }}` expression or an expression field, and §7.3.1 says it is "usable only within a `{{ }}` expression or an
   expression field". Every value reference is inside one of those, so the rule forbids nothing that the grammar
   allows, and no invalid test is planned for it. The `args` case is definite: Expression Language §1.3.2 flattens a list result in an `args` item,
   so `args: ["{{Job.EnvNames}}"]` passes one argument per name (JB-86). Interpolating the list into surrounding text
   (`"x{{Job.EnvNames}}"`) is also defined (§1.3.2 converts it to its string form), so it is valid, not an error.
8. **`activation` case.** Resolved: §4 item 4 constraint 1 says the values are case-sensitive, as are the 2023-09
   schema's other enumerated values except parameter type names, so `always` is rejected (JT-180, ET-47).
9. **Two attached Environment Templates with one Environment name.** §3.2.1 item 3 (ambiguous names) and the
   `Job.EnvNames` row ("it appears twice if two attached Environments share it") imply a submission may attach two
   Environments with the same name, but the base specification does not say whether attaching them is itself
   allowed. JB-21 passes either way. JB-51 assumes the attachment is accepted when no entry names the shared name; a
   runner that rejects duplicate attached names outright would fail it.
10. **Which document's `EXPR` admits a URI PATH value.** Resolved: `ENV_PARAMS` requires `EXPR`, so every document
    involved lists it. JB-63 tests a URI PATH value.
11. **Whether `enableIf` coerces to `bool`.** Resolved: both *enableIf* fields are expression fields (§7.6), whose
    rule 2 applies no conversion except widening `int` to `float`. A `string` expression is rejected (JT-149), as an `int` one is
    (JT-97, JT-140).
12. **An empty `hostRequirements` on an Environment Template.** Resolved: with `ENV_PARAMS`, §3.3 constraint 1 does
    not apply in a document that lists the extension, so `hostRequirements: {}` means no requirements on a Step
    (JT-173), on a Job Environment (JT-117), and in an Environment Template (ET-46) alike. An amount that resolves
    to nothing at job creation is discarded (JB-132, JB-134), as is an attribute whose `anyOf`, written as one
    expression, resolves to `null` (JB-135); an `anyOf` whose items all resolve to `null`, or whose expression
    resolves to `[]`, is rejected (JB-133, JB-136), and literal empties stay errors (JT-175, JT-176).
13. **An `enableIf` that can resolve to `null`.** Resolved: §7.6 rule 2 accepts an expression of static type `bool?`
    for a `bool` field and makes a `null` result an error when it is evaluated, so JB-46 and JB-97 are rejected at job
    creation, as the job-creation rule intends.

14. **`RawParam.<PATH>` of a Job Parameter in an Environment's `hostRequirements` or `enableIf`.** Resolved: the §7.3.2
    scope table gives `RawParam.*` of any type for both. JT-153–JT-155 and JB-111 test it; `Param.<PATH>` stays excluded
    (JT-50, JT-122).
15. **Constraints 5 and 6 on a disabled entry.** Resolved: §3.2 item 3.2 says a disabled entry's `parameters` are not
    checked, and the checked-at paragraph defers the check for an entry whose `enableIf` is an expression to job
    creation (JT-183, JT-184, JB-143, JB-144). Constraint 2 still applies to every entry as written.
16. **A missing `min` in §3.3.3 versus a capability's defined minimum.** Resolved: §3.3.3 item 1 omits from the
    combined requirement a bound that no source gives, which then means what §3.3.1 says (for `amount.worker.vcpu`, a
    minimum of 1), as for a Step's own requirements. The suite uses only custom `conformance:`
    capabilities, whose minimum is 0, so no test depends on it.
17. **`enableIf` in template scope on a POSIX runner.** §7.6 evaluates every `enableIf` with POSIX path semantics and
    template-scope `let` values, whatever the submission path format. On a POSIX runner every interpretation agrees, so
    JB-104 passes whether or not an implementation follows the rule; it distinguishes the rule only on a runner whose
    host or submission path format is Windows. Path mapping is not tested separately: an `enableIf` cannot read
    `Param.<PATH>` (JT-122), and `RawParam.*` is unmapped in every scope.
18. **When a certain failure is reported.** §7.6 rule 5 says an early check reports an error *only when* it holds
    for every value the undetermined fields could take, and that an implementation *should* report it at the earliest
    stage where it does. The first part forbids an early error that depends on those values, so JT-150–JT-152, JT-157,
    and JT-158 must pass template validation. The second is a preference, not a requirement, so JB-105–JB-107
    are `jobs/` tests, which pass whichever stage rejects them. An `enableIf` that depends on a missing value is
    different: §3.2.2 item 5 requires that error at template validation when the value is known then to be missing,
    so JT-162 is a `job_templates/` test.
19. **Environments from documents without `ENV_PARAMS` in combinations that cannot be written.** §4 item 4 makes such
    an Environment behave as `ALWAYS`. Two combinations it might seem to need tests for cannot occur. Such an
    Environment cannot have an `exclusiveGroup`, because the field requires `ENV_PARAMS` (ET-50, V1), so it never takes
    part in the group rule. A Job Environment of a Job Template that does not list
    `ENV_PARAMS` cannot be named by a Step whose template lists it, because a Job Template's Steps are in the same
    document, and without the extension no Step has an `environment:` entry and no Environment has an `enableIf`; its
    Environments are entered by every Session whichever `activation` they are read as.

## What the suite does not test

Deliberately, and why:

- **Composition with `SERVICE` and `CONTROL_FLOW`.** The RFC no longer specifies either composition; those RFCs will
  extend it (RFC *Extensions specified after this one*). No test uses either extension.
- **Scheduling behavior.** Session sharing and §3.2.2 equality, placement on a host that satisfies the combined host
  requirements, reservation of `amounts`, and "amounts do not add" are scheduler decisions with no definite output in
  `openjd run` (items 3 and 4 above). The suite tests only what job creation decides:
  conflicts are rejected and non-conflicts run.
- **Warnings** (item 5 above), since the test format cannot assert one.
- **The forms listed above as ambiguous** (items 2, 6, 7, and 9) whose outcome the text does not decide. Where a form is
  definite under every reading, it is tested and the item names the test.
- **Repeat variants of a tested rule.** A rule that applies to several types or fields is tested where an
  implementation could plausibly differ, for example `objectType` on both PATH and LIST[PATH] (JT-25, JT-120). A literal
  `default` against `maxLength` is not tested separately from `minValue`, `allowedValues` and type (JT-34–JT-36), and a
  value reading `Param.<LIST[PATH]>` is not tested separately from `Param.<PATH>` (JT-106) and the `default` form
  (JT-121).
