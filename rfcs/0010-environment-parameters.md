* Feature Name: Environment Parameters
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/209
* Start Date: 2026-10-17
* Specification Version: 2023-09 extension ENV_PARAMS
* Accepted On: (pending)
* Depends On:
  * RFC 0002, Model Extensions (https://github.com/OpenJobDescription/openjd-specifications/issues/57)
  * RFC 0005, Expression Language (`EXPR`) (https://github.com/OpenJobDescription/openjd-specifications/issues/112),
    which `ENV_PARAMS` requires
* Related:
  * Discussion #198, the idea thread for this RFC
    (https://github.com/OpenJobDescription/openjd-specifications/discussions/198)
  * RFC 0008, Environment Wrap Actions (`WRAP_ACTIONS`)
    (https://github.com/OpenJobDescription/openjd-specifications/issues/132)
  * RFC 0009, Service (`SERVICE`) (https://github.com/OpenJobDescription/openjd-specifications/pull/194)
  * RFC 0011, Control Flow (`CONTROL_FLOW`)
    (https://github.com/mwiebe/openjd-specifications/blob/rfc-control-flow/rfcs/0011-control-flow.md)

## Summary

A Job often needs different software in different Steps, such as ffmpeg to decode a video into frames and COLMAP to
solve the camera path through them. Open Job Description lets external Environments, such as a Conda or Docker
Environment that a scheduler attaches, provide software to Jobs, but today they take their configuration from Job
Parameters, so every Step of a Job gets the same software. This RFC lets each Step configure the Environments that wrap
it: an `<Environment>` declares parameters in `envParameterDefinitions` and reads them as `{{Env.Param.<name>}}`, and a
Step supplies values in an `environment:` entry of its `dependencies`. An Environment can also say which Sessions enter
it (`activation`), skip the Steps it has nothing to do for (`enableIf`), form a group with alternatives so that each
Step uses the first one attached (`exclusiveGroup`), and state the hosts it needs (`hostRequirements`). One Job Template
then gets per-Step software from whichever of these Environments a system provides, and runs unchanged where none is
provided, while existing Environment Templates and Job Templates keep working.

## Basic Examples

### An external Conda Environment that each Step configures

The scheduler attaches this Environment Template to every Job. Its `Packages` parameter defaults to the `CondaPackages`
Job Parameter, so Job Templates that know nothing about this extension keep working.

```yaml
specificationVersion: "environment-2023-09"
extensions: [ENV_PARAMS, EXPR]
parameterDefinitions:
  - name: CondaPackages
    type: STRING
    default: ""
  - name: CondaChannels
    type: STRING
    default: "conda-forge"
environment:
  name: Conda
  enableIf: "Env.Param.Packages != ''"
  envParameterDefinitions:              # new: values a Step may supply
    - name: Packages
      type: STRING
      default: "{{Param.CondaPackages}}"
    - name: Channels
      type: STRING
      default: "{{Param.CondaChannels}}"
  script:
    actions:
      onEnter:
        command: bash
        # Values reach the script as argv, never as script text.
        args: ["{{Env.File.Enter}}", "{{Env.Param.Packages}}", "{{Env.Param.Channels}}"]
    embeddedFiles:
      - name: Enter
        type: TEXT
        data: ...
```

Its `enableIf` is decided for each Step, so a Step left with no packages does not enter the Environment.

### A Job Template whose Steps each ask for their own software

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [ENV_PARAMS, EXPR]
name: "Video To Composite"
steps:
  - name: DecodeFrames
    dependencies:
      - environment: Conda
        required: false
        parameters:
          Packages: "ffmpeg=7"
      - environment: Docker
        required: false
        parameters:
          Image: "docker.io/linuxserver/ffmpeg:latest"
    script: ...
  - name: SolveSfM
    dependencies:
      - step: DecodeFrames
      - environment: Conda
        required: false
        parameters:
          Packages: "colmap=3.11"
      - environment: Docker
        required: false
        parameters:
          Image: "docker.io/colmap/colmap:latest"
    script: ...
```

Each Step's Sessions enter `Conda` with that Step's `Packages`. Where the scheduler attaches `Docker` instead, the
`Docker` entries apply, and where neither is attached, the Job runs unchanged. The complete pipeline is in
[`samples/v2023-09`](../samples/v2023-09).

### One parameterized Job Environment serving several Steps

An `environment:` entry can name a Job Environment of the same template, so one Environment
definition replaces several near-identical Step Environments. With `activation: ON_REQUEST`, only
the Steps that request the Environment enter it.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [ENV_PARAMS, EXPR]
name: "Plugin-Selected Renders"
jobEnvironments:
  - name: RenderLicense
    activation: ON_REQUEST
    envParameterDefinitions:
      - name: Product
        type: STRING
        allowedValues: ["arnold", "redshift", "vray"]
      - name: Seats
        type: INT
        default: 1
        minValue: 1
    script:
      actions:
        onEnter:
          command: license-checkout
          args: ["--product", "{{Env.Param.Product}}", "--seats", "{{Env.Param.Seats}}"]
        onExit:
          command: license-release
          args: ["--product", "{{Env.Param.Product}}"]
steps:
  - name: BeautyPass
    dependencies:
      - environment: RenderLicense
        parameters: { Product: "arnold" }
    script: ...
  - name: VolumePass
    dependencies:
      - environment: RenderLicense
        parameters: { Product: "redshift", Seats: 2 }
    script: ...
  - name: Composite
    dependencies:
      - step: BeautyPass
      - step: VolumePass
    script: ...
```

`Product` has no default, so every Step that requests `RenderLicense` must supply it. The two render Steps supply
different values, so a Session that runs Tasks of both exits `RenderLicense` and enters it again between them.

### Choosing between attached Environments

A scheduler may attach both `Conda` and `Docker`. The Job Template above stays as it is. Instead, the two Environment
Templates share an `exclusiveGroup`, and each Step's Sessions enter only the first Environment of the group, in the
order they are attached, that the Step would enter and whose `enableIf` is not `false`:

```yaml
environment:
  name: Conda
  enableIf: "Env.Param.Packages != ''"
  exclusiveGroup: SoftwareProvider        # new; the Docker Environment has the same line
  ...
```

Attaching `Conda` before `Docker` gives every Step conda, and attaching them the other way round gives every Step a
container. A Step that leaves `Packages` empty is not enabled for `Conda`, so it falls through to `Docker`. Rez and
Singularity Environments can join the same group without changing any Job Template.

### An Environment that states what hosts it needs

An Environment may declare `hostRequirements`, and they may read its parameters. A Session that enters the Environment
must satisfy them in addition to its Step's own requirements, so a Docker Environment can require a GPU only for Steps
that ask for one, and a Linux host for every Step that requests it:

```yaml
specificationVersion: "environment-2023-09"
extensions: [ENV_PARAMS, EXPR, FEATURE_BUNDLE_1]   # FEATURE_BUNDLE_1 for a format-string `min`
environment:
  name: Docker
  activation: ON_REQUEST
  envParameterDefinitions:
    - name: Image
      type: STRING
    - name: Gpus
      type: STRING
      default: ""
  hostRequirements:
    attributes:
      - name: attr.worker.os.family
        anyOf: [linux]
    amounts:
      - name: amount.worker.gpu
        min: "{{ 1 if Env.Param.Gpus != '' else None }}"
  script: ...
```

### Execution

For the Video To Composite Job with the `Conda` Environment attached, on two Worker Hosts:

```
Worker host A                                Worker host B
-------------                                -------------
Session 1 (DecodeFrames)                     Session 2 (SolveSfM, after DecodeFrames)
  Conda.onEnter  Packages="ffmpeg=7"           Conda.onEnter  Packages="colmap=3.11"
    DecodeFrames task                            SolveSfM task
  Conda.onExit                                 Conda.onExit
```

A later Step that supplies the same values, such as an `EncodeVideo` Step with `Packages: "ffmpeg=7"`, may run its
Tasks in Session 1 if it is still open. Steps that supply different values do not share one entry of `Conda`.

## Motivation

### One Job, several applications

For example, a Job might decode a video into frames with ffmpeg, solve structure-from-motion with COLMAP, place 3D
objects into the solved scene with Maya, render the composite, and encode the result with ffmpeg. Each Step uses
different software and consumes the output of the Step before it, so the pipeline belongs in one Job with dependencies
between its Steps.

Each of those Steps needs its own software from the same external Environment, which today does the same thing in every
Session of the Job.

### Other workflows

1. **Per-Step resource tuning of a shared Environment.** An external Environment that mounts a dataset or warms a cache
   can take a size or a subset per Step (`Subset: "train"` for one Step, `"eval"` for another), so each Session prepares
   only what its Tasks read.
2. **A menu of external Environments.** An operator wants to make Conda, Docker, and a GPU driver setup
   available without imposing all three on every Session. Today each such Environment must be written to do nothing
   unless a Job Parameter asks for it, and every Session still enters and exits it. With `activation: ON_REQUEST` the
   scheduler attaches all of them and each Step enters only the ones it requests.
3. **An Environment that only works on some hosts.** An external Docker Environment needs a host with a container
   runtime, and on a mixed fleet a Conda Environment may need Linux. Today an Environment Template cannot say so, and
   the Steps it serves fail at `onEnter` on the wrong host. With `hostRequirements` on the Environment, every Session
   that enters it is placed where it can run, and when the requirement depends on a parameter (a GPU only when `Gpus` is
   set) it applies only to the Steps that set it.

[Prior Art](#prior-art) describes workflow systems that let each unit of work choose its own software environment.

### How common these needs are

Per-Step software is a standard feature of workflow systems. Every workflow system in [Prior Art](#prior-art) has it,
while an OpenJD external Environment, such as Deadline Cloud's Conda queue environment, gives every Step of a Job the
same software. Nextflow and Snakemake let each process or rule name its own Conda environment or container, Argo
Workflows' container and script templates each name their own image, and NVIDIA OSMO requires an `image` on every task.
The need is not specific to one company's way of working: any pipeline that chains applications has it. Users rarely ask
for the feature in this form. The need tends to reach a render management system restated as something else, such as a
request for one queue per application or for a larger shared environment, or users rule the system out for such
pipelines without saying why.

### Why the values come from the Step

A Session enters its Environments and then runs Tasks, which may come from one Step or from several whose Environments
are identical. The Step is the unit that knows what software its Tasks need, so the Step says what an Environment should
do for them.

### Backward compatibility

This RFC is additive and gated by the `ENV_PARAMS` extension name declared under RFC 0002.

- A document that uses any of the syntax this RFC adds MUST list `ENV_PARAMS` and `EXPR` in its `extensions`, and a
  scheduler that does not implement `ENV_PARAMS` rejects it under RFC 0002. That syntax is an Environment's
  `envParameterDefinitions`, `activation`, `hostRequirements`, `enableIf`, or `exclusiveGroup`; an `environment:` or
  `step:` entry; `Job.EnvNames`, `Env.Param.*`, or `Env.RawParam.*`; an `anyOf` or `allOf` written as one expression;
  and a `hostRequirements` that is empty or has empty lists. A document
  that lists `ENV_PARAMS` without `EXPR` is rejected, and a document that lists neither keeps its current meaning.
  `step:` is a synonym for `dependsOn:`, which keeps its meaning and stays valid with or without `ENV_PARAMS`; the plan
  to remove `dependsOn:` applies to a future major version of the specification, not to `jobtemplate-2023-09`.
- An extension applies only to the document that lists it (see
  [Extension name and the documents that list it](#extension-name-and-the-documents-that-list-it) for a submission in
  which only some documents list it). A Job Template that does not list `ENV_PARAMS` runs with an Environment Template
  that does: every Environment parameter takes its default, which is how an Environment Template author keeps existing
  Job Templates working while adding per-Step configuration. Such a Job Template cannot request anything, so its
  Sessions never enter an attached `ON_REQUEST` Environment. An author who wants existing Job Templates to keep getting
  an Environment leaves its `activation` at the default, `BY_DEFAULT`, or sets `ALWAYS`.
- An Environment Template that does not list `ENV_PARAMS` runs with a Job Template that does. Its Environment behaves as
  one with `activation: ALWAYS` and no `enableIf`, so every Session enters it, and a disabled `environment:` entry that
  names it has no effect and is not an error (see [Environments from documents without `ENV_PARAMS` are
  `ALWAYS`](#environments-from-documents-without-env_params-are-always)). It has no parameters, so an enabled
  `environment:` entry that names it and supplies parameters is an error only if it has `required: true`. A
  `required: false` entry's parameters are ignored, and implementations should warn (see
  [`<StepDependency>`](../wiki/2023-09-Template-Schemas.md#32-stepdependency) constraint 5 and
  [§3.2.1](../wiki/2023-09-Template-Schemas.md#321-resolving-external-environments) item 1).
- An Environment Template written before this extension under a [recommended name](#recommended-names-non-normative)
  accepts Job Templates that supply its recommended parameters with `required: false`, and ignores those parameters.
  Deadline Cloud's console Conda queue environment (`Conda`) is such a case today. Its Sessions then install what the
  Job Parameters (`CondaPackages`, `CondaChannels`) say, for the whole Job, as they did before this extension. For each
  Step to get its own packages, the Environment Template's author adds `ENV_PARAMS` and the recommended
  `envParameterDefinitions`, with defaults that read the existing Job Parameters, as `conda-env-params.yaml` does; see
  [Parameters for an Environment that declares none are
  ignored](#parameters-for-an-environment-that-declares-none-are-ignored).
- No existing field changes meaning. A Job with no `environment:` entries, no Environment `envParameterDefinitions`, no
  `activation`, and no Environment `enableIf` behaves as today, including which Environments each Session enters and how
  Sessions are shared between Steps. An Environment written before this extension behaves as `activation: ALWAYS` with
  no `enableIf`, so every Session enters it, as today, whatever the entries of a Job Template that lists `ENV_PARAMS`
  say. A Job Template that lists `ENV_PARAMS` but no `environment:` entries, run with an Environment Template that
  declares parameters and keeps the default `activation`, also shares Sessions as today: every Step takes the same
  defaults, so every Step's values are equal.
- Adding `ENV_PARAMS` to a document changes how the *minLength* and *maxLength* of its existing RANGE_EXPR Job
  Parameters are checked: both the value as written and its canonical form must satisfy them
  ([§2.10](../wiki/2023-09-Template-Schemas.md#210-jobrangeexprparameterdefinition-extension-expr)). So a value that a
  Job Template accepted before can be rejected after (see [Lengths of a RANGE_EXPR
  value](#lengths-of-a-range_expr-value)).
- A few changes state or correct rules of the base specification and apply with or without the extension. They are
  listed in [Changes that apply without the extension](#changes-that-apply-without-the-extension).

## Specification

The normative text of this extension is the wiki edits in this pull request: [Template
Schemas](../wiki/2023-09-Template-Schemas.md), [Expression Language](../wiki/2026-02-Expression-Language.md), and [How
Jobs Are Run](../wiki/How-Jobs-Are-Run.md). It also adds a non-normative page, [Environment Name
Conventions](../wiki/Environment-Name-Conventions.md). This section summarizes each change and links to the wiki section
that holds the formal text; where the two differ, the wiki governs. A section number (§) in this RFC refers to Template
Schemas unless another page is named.

### Terminology

| Term | Meaning |
|------|---------|
| **Environment parameter** | A value declared in an `<Environment>`'s `envParameterDefinitions` and read only inside that Environment, as `Env.Param.<name>`. A Job Parameter is declared in a template's top-level `parameterDefinitions` and read as `Param.<name>`. |
| **Job Environment** | An entry of a Job Template's `jobEnvironments`. |
| **External Environment** | An Environment that the scheduler attaches to a Job from an Environment Template, also called an attached Environment. A Deadline Cloud queue environment is an example. |
| **Request** | A Step requests an Environment with an enabled `environment:` entry in its `dependencies` that names it. |
| **Disabled entry** | An `environment:` entry whose own `enableIf` is `false`. It requests nothing and supplies no values. |
| **Decline** | A Step declines a `BY_DEFAULT` Environment with a disabled entry naming it, and its Sessions then do not enter it. |
| **Applies** | An Environment applies to a Step when its `activation` is `ALWAYS`, when it is `BY_DEFAULT` and the Step does not decline it, or when it is `ON_REQUEST` and the Step requests it. The Step must supply each of the Environment's parameters that has no `default`, whatever the Environment's *enableIf*. |
| **Disabled Environment** | An Environment whose own `enableIf` is `false` for a Step, or that is superseded for it. That Step's Sessions do not enter it. |
| **Superseded** | An Environment is superseded for a Step when an earlier Environment of its `exclusiveGroup`, in the Job's Environment order, is one the Step's Sessions enter. |
| **Effective values** | For one Step and one Environment that applies to it, the value of each of the Environment's parameters: the one the Step's enabled entry supplies, or else the parameter's resolved `default`. |
| **Combined host requirements** | A Step's own `hostRequirements` together with those of every Environment its Sessions enter. |
| **Expression field** | A field whose value is one Expression Language expression written without `{{ }}`, with the target type its `@expr <type>` annotation gives. Both `enableIf` fields of this RFC are expression fields. |

### Extension name and the documents that list it

[§1.1](../wiki/2023-09-Template-Schemas.md#11-job-template) adds `ENV_PARAMS`, which requires `EXPR` (see [`ENV_PARAMS`
requires `EXPR`](#env_params-requires-expr)). [§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) gives
an Environment Template the `$schema` and `extensions` keys. An extension applies
only to the document that lists it, so an Environment Template can adopt parameters while Job Templates that do not
list `ENV_PARAMS` keep running with it (see [Backward compatibility](#backward-compatibility)).

When only some documents of a submission list `ENV_PARAMS`, Job creation still takes the steps of
[§7.4.1](../wiki/2023-09-Template-Schemas.md#741-job-creation-with-env_params), and each rule the extension adds for a
document's content applies only to the documents that list it. An Environment from a document that does not list it
behaves as `ALWAYS`, and a Step's own host requirements in a Job Template that does not list it keep the base rules.

The item descriptions of *jobEnvironments*, *stepEnvironments*, *let*, and *dependencies* each gain a sentence so that
they stay true with the extension. §1.1 item 7 also states the Job's Environment order, which applies with or without
the extension: attached Environments first, in the order they are attached, then the `jobEnvironments`.

### Changes that apply without the extension

These changes apply to every 2023-09 document, whether or not it lists `ENV_PARAMS`, so core reviewers should agree to
them as changes to the base specification:

1. **`<nonnegativefloatstring>`.** [§3.3.1](../wiki/2023-09-Template-Schemas.md#331-amountrequirement) defined it as
   "non-zero and positive", which contradicts its name and an amount's `min` of 0. It now says "non-negative".
2. **One value of `attr.worker.os.family` and `attr.worker.cpu.arch`.**
   [§3.3.2.1](../wiki/2023-09-Template-Schemas.md#3321-attributecapabilityname) now states that a host has exactly one
   value of each, so an *allOf* written as a list for either has at most one element. A template the old text allowed,
   such as `allOf: [linux, windows]`, is now invalid. No host could run it, and the base conformance suite already
   rejects it.
3. **The Job's Environment order.** [§1.1](../wiki/2023-09-Template-Schemas.md#11-job-template) item 7 now states that
   a Session enters the Environments attached from Environment Templates before the Job Template's `jobEnvironments`,
   in the order they are attached. The base specification did not say. `openjd run` and Deadline Cloud already behave
   this way, and render management systems must now do so.
4. **`$schema` and `extensions` in an Environment Template.**
   [§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) adds both keys to the Environment Template
   schema, and states that an extension listed there applies to that document only, so a Job Template need not list the
   extensions of the Environment Templates attached to it. RFC 0008 already required an Environment Template to list
   `WRAP_ACTIONS`, but the schema had neither key.
5. **A conditional whose branches give the same value.** With `EXPR`, the Expression Language's [Progressive
   Expression Evaluation](../wiki/2026-02-Expression-Language.md#progressive-expression-evaluation) now gives
   `c if U else c` the value `c` when the condition `U` is not yet known. So template validation can reject a template
   that only Job creation rejected before: `timeout: "{{ 0 if Param.F else 0 }}"` fails `openjd check` because the
   timeout is `0` either way. Job creation rejects the same templates as before.

The prototype also changes the order in which `openjd-rs` reports several Job-creation errors, for Job Templates with
or without the extension (see [Prototype](#prototype) change 5). That is not a specification change:
[§7.4.1](../wiki/2023-09-Template-Schemas.md#741-job-creation-with-env_params) says when each check is made, and that
which of several errors an implementation reports, and in what order, is not specified.

### Environment parameters

[§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 3, *envParameterDefinitions*, lets an Environment declare
up to 50 parameters, read only inside it as `Env.Param.<name>` and `Env.RawParam.<name>`. The new
[§4.5](../wiki/2023-09-Template-Schemas.md#45-environmentparameterdefinition-extension-env_params) defines each as a
`<JobParameterDefinition>` of any type available with `EXPR`, except that:

* The `default` is a format string resolved when the Job is created, and may read the same document's Job Parameters.
  A parameter without one must be supplied by every Step that the Environment applies to, whatever its *enableIf*.
* A PATH or LIST[PATH] value is used as given: never joined with a directory, and not required to be absolute.
* A RANGE_EXPR value's *minLength* and *maxLength* apply to the value as written and to its canonical form.

Environment parameters are never merged with Job Parameters
([§1.2.1](../wiki/2023-09-Template-Schemas.md#121-merging-environment-template-parameter-definitions)).
[§2.10](../wiki/2023-09-Template-Schemas.md#210-jobrangeexprparameterdefinition-extension-expr) applies the same
RANGE_EXPR length rule to Job Parameters in a document that lists `ENV_PARAMS`.

### Requesting an Environment from a Step

[§3.2](../wiki/2023-09-Template-Schemas.md#32-stepdependency) gives `<StepDependency>` three forms:

```yaml
dependencies:
  - dependsOn: DecodeFrames      # unchanged
  - step: SolveSfM               # a synonym of dependsOn
  - environment: Conda           # requests an Environment
    required: false              # default true
    enableIf: "Param.SolveCameras"
    parameters:
      Packages: "colmap=3.11"
```

An *environment* entry names a Job Environment of that name if there is one, and otherwise an external Environment. It
is met when the Step's Sessions enter the Environment, so it does not delay scheduling. *required* says whether the name
must resolve to an Environment. An enabled `required: true` entry whose Environment its own *enableIf* disables, or an
earlier member of its *exclusiveGroup* supersedes, is not an error, and implementations may warn. *enableIf* is
evaluated when the Job is created, and a value known before then, such as a literal `false`, also decides what template
validation checks. A `false` entry requests and supplies nothing, declines a `BY_DEFAULT` Environment, is an error for
an `ALWAYS` one, and has no effect on one from a document that does not list `ENV_PARAMS`. *parameters* supplies values,
each a literal or a format string resolved when the Job is created.

The constraints keep an entry to one form and one Environment to one entry, require each key to be declared and each
value to be valid (except that an attached Environment that declares no parameters ignores a `required: false` entry's
values), require every Step that an Environment applies to, by its `activation` and the Step's entries, to supply each
parameter without a `default` whatever the Environment's *enableIf* is (constraint 7), and forbid `required: false` on
an entry that names a Job Environment. The section says at which stage each constraint is checked.

### Resolving external Environments

The new [§3.2.1](../wiki/2023-09-Template-Schemas.md#321-resolving-external-environments) resolves an entry that names
no Job Environment against the attached Environment Templates when the Job is created. No match is an error only for an
enabled entry with `required: true`, and two matches are an error. A resolved entry is checked against the Environment,
except that a `required: false` entry's parameters are ignored by an attached Environment that declares none (see
[Parameters for an Environment that declares none are
ignored](#parameters-for-an-environment-that-declares-none-are-ignored)).

### Which Sessions enter an Environment

[§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 4, *activation*, is one of:

* `ALWAYS`: every Session. Declining it or disabling it for a Step is an error.
* `BY_DEFAULT`, the default for a Job Environment or Environment Template in a document that lists `ENV_PARAMS`:
  every Session, except a Step's that declines it or for which its *enableIf* is `false`.
* `ON_REQUEST`: the Sessions of the Steps that request it, less any for which its *enableIf* is `false`.

A Step Environment has no *activation*: only its own Step's Sessions enter it, less those for which its *enableIf* is
`false`. An Environment from a document that does not list `ENV_PARAMS` behaves as `ALWAYS` with no *enableIf*, except
that a Step's disabled entry for it has no effect rather than being an error.

§4 item 6, *enableIf*, is evaluated when the Job is created, once per Step with that Step's effective values. It comes
after constraint 7, which does not depend on it: a Step that an Environment applies to supplies every parameter without
a `default`. [§3.2.2](../wiki/2023-09-Template-Schemas.md#322-effective-environment-parameter-values) then evaluates the
*enableIf* with concrete values, before the value checks, which do not apply to a Step for which it is `false`. An
*enableIf* that reads a value that fails to resolve or does not convert is not evaluated, and the value is an error. §4
item 7, *exclusiveGroup*, names a group of Environments of which each Step's Sessions enter only the first, in the Job's
Environment order, that they would otherwise enter and that its *enableIf* does not disable. The later ones are
superseded, which disables them for the Step, and their *enableIf* is not evaluated. Attached Environments come first,
so one can supersede a Job Environment, and a validator given only the Job Template never treats a grouped Job
Environment as known to be entered. An `ALWAYS` Environment cannot have a group (see
[`exclusiveGroup`](#exclusivegroup)). A Step Environment may have *enableIf* but none of the other new fields (see
[Not on Step Environments](#not-on-step-environments)).

Being disabled for a Step changes which Sessions enter an Environment, not its definition. Its other fields resolved
at Job creation, such as an action's *timeout*, read no effective values, and are resolved and checked as without the
extension, whether or not any Step enters it (see [A disabled Environment's other fields are
resolved](#a-disabled-environments-other-fields-are-resolved)).

### Effective values and Session sharing

§3.2.2 defines a Step's effective value for each parameter: the value its enabled entry supplies, or else the resolved
`default`. Two values are equal when they have the same type and the same string form, which is the text that
`{{Env.RawParam.<name>}}` gives the value, before path mapping. A FLOAT keeps the text it was written with, so `"3.10"`
and `"3.1"` are not equal; an INT `1` and `"1"` are; a STRING compares by code points, with no normalization; a
RANGE_EXPR's string form is its canonical form; and lists compare element by element. §3.2.2 also states that a Session
runs a Step's Tasks only when it entered the Step's Environments with the Step's values, and
[How Jobs Are Run](../wiki/How-Jobs-Are-Run.md#environment-parameters) explains it.

Effective values are fixed per Step, so with `TASK_CHUNKING` every chunk of a Step's Tasks runs in Environments entered
with the same values. They are part of the Job, and `REDACTED_ENV_VARS` does not hide them, so they are not a place for
secrets (see [Security Considerations](#security-considerations)).

### Limits

* An Environment declares at most 50 parameters, also with `FEATURE_BUNDLE_1`
  ([§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 3).
* A STRING or PATH effective value, and each element of a LIST[STRING] or LIST[PATH] one, is at most 1024 characters
  ([§4.5](../wiki/2023-09-Template-Schemas.md#45-environmentparameterdefinition-extension-env_params) item 5).
* The specification sets no maximum number of a Step's *dependencies*, but an implementation that sets one must accept
  at least 50 `environment:` entries ([§3](../wiki/2023-09-Template-Schemas.md#3-steptemplate) *dependencies*).
* Each source's *hostRequirements* keep the limit of 50 requirements. An implementation may reject a Step whose combined
  requirements name more capabilities than a limit it documents, which must be at least 50
  ([§3.3.3](../wiki/2023-09-Template-Schemas.md#333-combined-host-requirements)).

See [The limits chosen](#the-limits-chosen) for why.

### Host requirements

§4 item 5 gives an Environment *hostRequirements*, resolved per entering Step with that Step's values. The new
[§3.3.3](../wiki/2023-09-Template-Schemas.md#333-combined-host-requirements) combines them with the Step's own by
conjunction, and gives a normalized form that does not depend on the order of the sources.
[§3.3.2.1](../wiki/2023-09-Template-Schemas.md#3321-attributecapabilityname) now states that a host has one value of
`attr.worker.os.family` and of `attr.worker.cpu.arch`, so their lists combine by intersection.

With `ENV_PARAMS`, [§3.3](../wiki/2023-09-Template-Schemas.md#33-hostrequirements) allows an empty *hostRequirements*
and discards a requirement that resolves to nothing, and
[§3.3.2](../wiki/2023-09-Template-Schemas.md#332-attributerequirement) lets *anyOf* and *allOf* be one expression (see
[Empty and resolved-empty host requirements](#empty-and-resolved-empty-host-requirements)).

### Value references and scopes

[§7.3.1](../wiki/2023-09-Template-Schemas.md#731-value-references) adds `Env.Param.<name>` and `Env.RawParam.<name>`,
read only inside the Environment that declares the parameter, and `Job.EnvNames`, the names of the Job's Environments in
the Job's Environment order. It also makes `Step.Name` available in an entry's values and *enableIf*. The new
[§7.3.2](../wiki/2023-09-Template-Schemas.md#732-env_params-scope-summary) lists what each field resolved at Job
creation may read. All of it is known then, so effective values are a static property of the Job.

### Processing stages and expression fields

The [§7.4](../wiki/2023-09-Template-Schemas.md#74-template-processing-stages) stage table adds what the extension checks
at each stage, and the new [§7.4.1](../wiki/2023-09-Template-Schemas.md#741-job-creation-with-env_params) orders the
work done at Job creation. The new [§7.6](../wiki/2023-09-Template-Schemas.md#76-expression-fields) defines expression
fields, which both *enableIf* fields are: one typed expression with no `{{ }}` and no implicit conversion other than
widening `int` to `float`. Before it is evaluated, its value is known when it is a boolean, integer, or float scalar, or
when the Expression Language's rules for unknown operands give a result with the values not yet known. A check whose
fields are known is made then; one that depends on a field that is not known reports an error only when the error holds
for every value it could take.

### Expression Language

The [Expression Language](../wiki/2026-02-Expression-Language.md) adds the new symbols to
[§1.2.2](../wiki/2026-02-Expression-Language.md#122-built-in-symbol-types), defines expression fields in
[§1.3.2](../wiki/2026-02-Expression-Language.md#132-evaluation-within-template-schemas), and says in [Progressive
Expression Evaluation](../wiki/2026-02-Expression-Language.md#progressive-expression-evaluation) that an Environment's
*enableIf* reads only concrete values at Job creation.
[§2.1.6](../wiki/2026-02-Expression-Language.md#216-logical-operators) gives the results of `and`, `or`, and `not` with
an unknown operand, such as `U and false = false`, and a conditional whose branches give the same value is that value,
which template validation uses to decide which errors it reports early.

### How Jobs Are Run

[How Jobs Are Run](../wiki/How-Jobs-Are-Run.md) gains an [Environment
Parameters](../wiki/How-Jobs-Are-Run.md#environment-parameters) section for template authors, and its Sessions and Host
Requirements sections describe the per-Step Environment set and an Environment's host requirements. A new page alongside
it, [Environment Name Conventions](../wiki/Environment-Name-Conventions.md), recommends the Environment, Job Parameter,
and Environment parameter names that Environment Templates and Job Templates should share.

### Extensions specified after this one (non-normative)

This RFC is specified against mainline. Every value it adds is fixed when the Job is created: effective values, each
Step's Environment set, each Environment's *enableIf*, and combined host requirements. An RFC accepted after this one
that adds a kind of Session or a later stage of evaluation specifies how it extends these rules.

### Recommended names (non-normative)

The portability of a Job Template that writes `environment: Conda` depends on Environment Templates using the same
Environment, Job Parameter, and Environment parameter names. The specification does not mandate names. This pull request
adds a wiki page, [Environment Name Conventions](../wiki/Environment-Name-Conventions.md), that explains why shared
names matter and recommends names for Conda, Rez, and Docker Environments, which the samples use. Each Environment
parameter defaults to the Job Parameter that Deadline Cloud's Conda and Rez queue environments already use, so existing
Job Templates keep working, and each such Environment has `exclusiveGroup: SoftwareProvider`, so that where several are
attached each Step uses the first one attached.

### Validation

[Template Schemas](../wiki/2023-09-Template-Schemas.md) states each rule this extension adds and the stage that checks
it, and [Processing stages and expression fields](#processing-stages-and-expression-fields) summarizes the stages. The
conformance suite's README indexes the rules: its
[Validation index](../conformance-tests/2023-09/ENV_PARAMS/README.md#validation-index) lists each rule, the stage that
checks it, and the tests that cover it, and its
[coverage matrix](../conformance-tests/2023-09/ENV_PARAMS/README.md#coverage-matrix) lists every test.

## Design Choice Rationale

### Parameters declared on the Environment

The Environment's author decides what the Environment accepts, so the parameters are declared there. A validator can
then check every `Env.Param.*` reference and every supplied value against a definition, as it checks `Param.*` against
Job Parameters. The definitions are exactly `<JobParameterDefinition>`s, so an author who can write a Job Parameter can
write an Environment parameter, and a tool such as a template editor can present them with the same `userInterface`.

The key is `envParameterDefinitions` because the bare `parameterDefinitions` declares Job Parameters everywhere in the
specification, and the other kind already carries its scope in the key (`taskParameterDefinitions` for `Task.Param.*`).
It also keeps an Environment Template from having one key at two levels with two meanings.

### A `default` that refers to a Job Parameter

External Environments already take their configuration from Job Parameters, and existing Job Templates set them. A
`default` of `"{{Param.CondaPackages}}"` keeps every such Job Template working: a Step that says nothing gets the
job-wide value, and a submitter can still set it at submission. Limiting a `default` to its own document's Job
Parameters keeps it resolvable at Job creation and checkable without other documents.

Such a `default` is checked only for the Steps that take it, so a Job whose Steps all supply their own value is not
rejected over a Job Parameter that changes nothing. Environment parameters are never merged, so a Conda and a Pip
Environment can both call their input `Packages` without sharing a value.

### The `environment:` form of `<StepDependency>`

Each entry in `dependencies` names something that must be in place before the Step's Tasks run: a completed Step, or,
with this RFC, an Environment entered with the Step's parameter values. The forms differ
in how that is met. A Step dependency is met by waiting for another Step, and an Environment dependency is met in each
of the Step's Sessions before it runs the Step's Tasks, so it does not delay scheduling. `required: true` still rejects
a submission in which the Environment is missing.

Putting the values beside the name groups everything a Step says about one Environment in one entry, and the name keeps
the values unambiguous when two Environments use the same parameter name (see [Rejected
Ideas](#a-flat-per-step-map-of-values)).

### `step:` as a synonym of `dependsOn:`

With this RFC, `dependencies` holds more than one kind of entry for the first time. The new form is keyed by the kind
of thing it names, `environment:`, while the existing form is keyed by a verb, and inside a list named `dependencies`,
"depends on" says nothing the list does not already say. `step:` gives Step entries the same shape as Environment
entries:

```yaml
dependencies:
  - step: DecodeFrames          # waits for the Step to complete
  - environment: Conda          # entered in each Session; does not delay scheduling
    parameters: {Packages: "colmap=3.11"}
```

This has two concrete uses. A reader sees from each entry's key what it names, which matters now that some entries
order Steps and others do not (see [The `environment:` form of
`<StepDependency>`](#the-environment-form-of-stepdependency)). And a tool that processes `dependencies`, such as a
template editor, a linter, or a scheduler's dependency graph, reads one key per kind of entry.

It is added in this RFC because this is the RFC that mixes the kinds. Templates written against it set the style that
later ones copy, and with only `dependsOn:` available, each of them would mix a verb key with noun keys. Renaming the
key would break every existing Job Template, so `step:` is a synonym, `dependsOn:` keeps its meaning and stays valid in
`jobtemplate-2023-09`, and a future major version can remove `dependsOn:`. `step:` is gated by `ENV_PARAMS` only
because this RFC adds it.

### `required` defaults to `true`

The safe reading of an entry in `dependencies` is that the Step needs what it names. The opposite default would let a
typo in an Environment name silently do nothing. A Job Template that targets several kinds of Environment states
`required: false` on each alternative.

### `activation`

Without `ON_REQUEST`, every Step would have to supply each Environment's required parameters, or decline it, even a
Step with no use for it. With it, only the Steps that request the Environment are held to that.

### The values and their names

The field is named for what it decides: when a Session enters the Environment. `runScope` was not kept because "scope"
already names value-reference scopes throughout the specification. `ON_REQUEST` names the mechanism: an `environment:`
entry is the request.

`BY_DEFAULT` and `ALWAYS` both have every Session enter the Environment, and differ in whether a Step can avoid it. A
Conda Environment has nothing to do for a Step with no packages, so a Step may decline it. An operator's Environment for
licensing, auditing, or security setup must be entered whatever a Job supplies.

In a document that lists `ENV_PARAMS`, a Job Environment or Environment Template that omits `activation` is
`BY_DEFAULT`, so that an author who writes an *enableIf* gets what it says without also writing `activation`. A Step
Environment has no `activation`, since only its own Step's Sessions can enter it. An Environment from a document that
does not list the extension is `ALWAYS` (see [Environments from documents without `ENV_PARAMS` are
`ALWAYS`](#environments-from-documents-without-env_params-are-always)). Both keep today's behavior, in which every
Session enters the Environment.

### Environments from documents without `ENV_PARAMS` are `ALWAYS`

An operator who attaches an Environment to every Job, for example for licensing or auditing, wrote it before this
extension existed and relies on every Session entering it. A Job Template that lists `ENV_PARAMS` must not be able to
change that. If such an Environment were `BY_DEFAULT`, a Step could decline it with `enableIf: false` on an entry that
names it, and a new Job Template would skip an Environment that no Job Template could skip before. So an Environment
from a document that does not list `ENV_PARAMS` behaves as `ALWAYS` with no *enableIf*, and the guarantee the operator
had before the extension still holds after it. A Step can leave out only an Environment whose author listed
`ENV_PARAMS` and left it `BY_DEFAULT` or made it `ON_REQUEST`.

A disabled entry that names such an Environment has no effect, instead of the error it is for an `ALWAYS` Environment.
The entry's author could not have known whether the attached Environment lists the extension, and a Job Template with
`required: false` entries is meant to work on every queue (see [Parameters for an Environment that declares none are
ignored](#parameters-for-an-environment-that-declares-none-are-ignored)). The error for an `ALWAYS` Environment tells
an author that a Step asked to leave out an Environment whose author chose to forbid it. An Environment written before
the extension made no such choice.

In a Job Template that does not list `ENV_PARAMS`, no Step has an entry and no Environment has an *enableIf*, so its own
Environments are entered by every Session whichever `activation` they are read as.

### `enableIf` on the Environment

An entry's *enableIf* lets the Step's author say when an Environment is wanted. The Environment's *enableIf* lets its
own author say when it applies, which with parameters is often a question about the Step's values: a Conda Environment
has nothing to do for a Step with no packages. It keeps a `BY_DEFAULT` Environment that existing Job Templates rely on
out of the Sessions that would enter it only to do nothing.

It is decided at Job creation, once per Step, so Session sharing and combined host requirements see a fixed set of
Environments. On a Job Environment or an attached Environment it reads the same scopes as the Environment's
*hostRequirements*, and not the Step's name or `let` bindings, so it means the same in an Environment Template as in a
Job Template. On a Step Environment, which only its own Step's Sessions enter, it may also read `Step.Name` and the
Step's `let` bindings.

A disabled Environment's values are not checked against their types and constraints, since a Step that never enters it
has no reason to configure them. A parameter without a `default` must still be supplied by every Step the Environment
applies to (see [Required parameters are allowed](#required-parameters-are-allowed)), and the *enableIf* reads only
concrete values (see [`enableIf` sees only concrete values](#enableif-sees-only-concrete-values)).

`Job.EnvNames` lists an Environment even for the Steps for which it is disabled. Otherwise `Job.EnvNames` would depend
on *enableIf* results that can be computed from `Job.EnvNames`.

### `enableIf` sees only concrete values

An earlier draft decided the Environment's *enableIf* before checking that the Step supplied its required parameters,
and evaluated it with a missing or unconvertible value as unknown. Whether `"Env.Param.X == 'a' and false"` rejected a
Step that did not supply `X` then depended on how `and` treats an unknown operand, which the Expression Language did not
define, so two implementations could accept different Jobs.

Now a missing value is an error of the Step, whatever the *enableIf* is, and an *enableIf* that reads a value that does
not resolve or convert is not evaluated, and the value is an error. Whether a value is read is a property of the text,
so it does not depend on evaluation order. At Job creation the *enableIf* is then an ordinary evaluation of concrete
values. Unknown values remain only at template validation, where Job Parameters are not yet known, and there they only
decide which errors are reported early. The Expression Language now defines their results, such as `U and false =
false`, so validators agree on what they report.

A value that the *enableIf* does not read still need not convert when the Environment is disabled: an entry
`Seats: "{{Param.N}}"` for an INT parameter, with the Job Parameter `N` set to `"many"`, is not an error for a Step for
which the *enableIf* is `false`. Converting every value before the *enableIf* would be stricter, but it would reject a
value that no Session uses, so values are converted after the decision.

### The name `enableIf`

Most of the systems surveyed name such a field `when`: Argo Workflows, Tekton, CWL, Nextflow, Ansible, CircleCI, and
Jenkins. GitHub Actions, Buildkite, and GitLab CI use `if`, and Azure Pipelines uses `condition`. This RFC uses
`enableIf`, the name discussion #81 proposed. It says what `false` does: a disabled Environment is not entered, and a
disabled entry requests nothing. `when` is shorter and familiar, but it can read as "wait until this is true", and
OpenJD Steps do wait. A field name is permanent once implementations ship it, so the name was settled before this RFC's
Final Comment Period.

### Expression fields rather than format strings

Both *enableIf* fields hold one boolean expression. As a Format String, `"{{Env.Param.Packages != ''}}"`, the braces say
"interpolate here" where there is nothing to interpolate, admit errors that exist only because of them (`"x{{true}}"`),
and bring implicit conversions under which `"{{'yes'}}"` becomes `true`. As an expression field, the value is
`"Env.Param.Packages != ''"` and its type must fit `bool` without conversion, as a `let` binding already reads.

Existing single-expression fields such as `timeout` stay as they are, since changing their kind would break accepted
templates. At template validation an expression's value is known when the Expression Language's rules for unknown
operands give one, so a constant expression such as `"false"` is known there, and implementations agree on what template
validation reports.

### Parameters for an Environment that declares none are ignored

A Job Template written for this extension is often submitted to several queues, and their operators upgrade their
Environment Templates at different times. One queue's `Conda` Environment may declare `Packages`, while another's is
still the one written before this extension, with the recommended name but no parameters. That older Environment
installs what the Job Parameters say for the whole Job, so a Job Template that sets `CondaPackages` and gives each Step
`required: false` entries works on both queues. Rejecting the submission on the older queue would make the author keep
a second Job Template until every queue is upgraded, and no expression can tell the two apart, because `Job.EnvNames`
lists names, not parameters.

Only the entry's *parameters* are ignored. The entry still names the Environment, so it is not treated as matching
nothing, and it still requests an `ON_REQUEST` Environment. The same entry, when disabled, has no effect on an
Environment from a document that does not list `ENV_PARAMS`, which every Session enters, and declines a `BY_DEFAULT` one
that lists it, as any disabled entry does. Ignoring the whole entry would differ only for an `ON_REQUEST` Environment
from an Environment Template that lists `ENV_PARAMS` but declares no parameters: the Step asked for it, and its Sessions
would not enter it. Implementations should warn, because the Step does not get the values it asked for.

The rule is narrow on purpose. An Environment that declares parameters has adopted this extension, so a key it does not
declare is a typo, or a parameter of a later version of the Environment. Either is a mistake that the Job Template's
author should see before anything runs, and ignoring it would run the Step with the wrong software. An entry with
`required: true` states that the Step needs the Environment as it asks for it, so supplying values to an Environment
that cannot take them stays an error.

### A disabled Environment's other fields are resolved

Disabling an Environment for a Step decides which Sessions enter it. It does not make the Environment's definition
optional. Its other fields resolved at Job creation, such as an action's *timeout*, read only values known then and no
effective values, so they can be checked whether or not any Step enters the Environment, as they are without the
extension. Skipping them would leave an error in a Job Environment unreported until some Job enables it, so the same
Job Template would fail for some Job Parameters and not others.

### `required` with an `exclusiveGroup`

An entry with `required: true` says that the name must resolve to an Environment, which catches a typo or a missing
attachment before anything runs. Whether the Step's Sessions then enter the Environment is the Environment's decision,
through its *enableIf* and *exclusiveGroup*. A Job Template cannot know which member of a group a system attaches first,
so rejecting a `required: true` entry whose Environment is superseded would reject the Jobs the group exists for.
Implementations may warn, since a Step that asked for Docker and runs in Conda may surprise its author.

### Names resolve to the Job Template first

An entry that names one of the template's own `jobEnvironments` can be checked at template validation, and resolving
those names first means an attached Environment can never change what such an entry refers to.

### External Environments are named implicitly

A Job Template could be required to declare each external Environment it names, as it declares its Job Parameters.
A declaration is useful where expressions read what it declares, so that they can be type-checked. A Job Template never
reads `Env.Param.*`; it only writes values, so no expression in it depends on an external Environment's shape. A
declaration would be a second place to write the name, would add no information, and still could not be checked
without the Environment Templates. Every mistake in a `required: true` entry is caught at Job creation with an error
that names the entry, and a validator given the Environment Templates, as `openjd run` is, catches them before
submission.

### Values fixed per Step

Once a Session enters an Environment, the Environment serves every Task the Session runs. Values that varied per Task
would force one Session per Task, and Tasks that need different software belong in different Steps. Values fixed per
Step are known at Job creation, so tooling can display them and Steps with equal values can still share Sessions.

### Sessions that serve several Steps

Sessions may already run Tasks of several Steps whose Environments are identical. Requiring the Steps' values to match
too is all that keeps `Env.Param.*` to one meaning for as long as an Environment is entered. The rule is checked as a
Step's Tasks are added, so a scheduler that adds Tasks of a newly ready Step to a running Session can keep doing so.

Values compare by type and string form, the text the Environment sees, before path mapping. What is compared is then
exactly what `onEnter`, the Tasks, and `onExit` see, so two Steps share an entered Environment only when it could not
tell them apart. A FLOAT keeps the text it was written with, so comparing FLOATs as numbers would let a Step written
`"3.1"` run in an Environment entered with `"3.10"`, and version numbers are a realistic way to write both. A scheduler
needs no numeric comparison or canonical form of a number: it can key Sessions on each value's type and text. Hosts
with different mapping rules agree because the comparison is before path mapping, and an INT written `1` still equals
one written `"1"` because an INT has one string form.

### `Step.Name` in values

`Step.Name` and the Step's `let` bindings are available everywhere else in a Step that is resolved at Job creation, and
a binding is how a Step uses one value both in an entry and in its script. A value that uses `Step.Name` differs per
Step, which suits values such as a cache key but prevents sharing Sessions.

### `Job.EnvNames`

A Job Template sometimes needs to know which Environments the Job has, beyond what `exclusiveGroup` decides. The main
case is an Environment written before this extension, such as Deadline Cloud's console Conda queue environment. It
cannot be in an `exclusiveGroup`, because the field needs `ENV_PARAMS`, so a Job Environment that should give way to it
tests for it by name:

```yaml
jobEnvironments:
  - name: InstallTools                    # the Job Template's own fallback
    enableIf: "'Conda' not in Job.EnvNames"
    script: ...                           # provides the tools some other way
```

The same test lets an entry's value or a Step's script depend on what is attached, for example to log which
Environments a Job ran with. A list of names answers these, and `EXPR` can already test it with `in`. It is in the
`Job.*` scope because it is a property of the Job, and it is concrete at Job creation, as `Job.Name` is. It lists every
Environment whatever its `activation`, because its purpose is to show what can be requested, and omits Step
Environments, which no Step can request.

### `enableIf` on the entry

An entry's *enableIf* lets a Step make a request conditional, for example on a Job Parameter. Declining a `BY_DEFAULT`
Environment lets a Step avoid one it has nothing to ask of, and an `ALWAYS` Environment exists so that no Step can. No
Step can decline an Environment from a document that does not list `ENV_PARAMS` either.

It is evaluated at Job creation, so a disabled entry costs nothing at run time. A disabled entry that matches no
attached Environment has no effect, so a `required: true` entry with a `false` condition is not an error. `required` is
about what the scheduler attaches, which the template cannot know; *enableIf* is about what the template wants.

### `exclusiveGroup`

A Job Template that can use several kinds of provisioning Environment writes one entry for each, and a system may attach
more than one of them. Something must then decide which one a Step uses. The Job Template cannot know what will be
attached, and the operator who attaches the Environments can, so the choice belongs to the Environments. Without a
group, each would have to name all its peers in its *enableIf* through `Job.EnvNames`, repeating the list in every
Environment Template, and could only choose per Job.

A shared name keeps each *enableIf* about the Environment's own values, and the order of attachment, which the operator
already controls, decides precedence. The group is applied as each *enableIf* is evaluated, so a Step that gives the
first Environment nothing to do falls through to the next, and an Environment that is superseded is not evaluated, so
its *enableIf* need not be resolvable for Steps it never serves. A group can include a Job Template's own Environment,
which an attached one then supersedes; a validator without the Environment Templates cannot know that, so it treats such
an Environment as undetermined. An `ALWAYS` Environment cannot be in a group, because the group could leave it out of a
Step's Sessions.

### `hostRequirements` on the Environment

An Environment knows what it needs from a host, such as a container runtime or a GPU. Today only a Step can say so, and
the Steps an Environment serves fail at `onEnter` on hosts that lack it. The requirement often depends on what the Step
asked for, which is why it belongs in this RFC: resolving it with the Step's values at Job creation adds no new stage.

Requirements combine by conjunction, so neither author can loosen the other's. The normalized form does not depend on
the order of the sources, so tooling can show it. Attribute lists are not intersected in general, because a host can
have several values of an attribute and intersecting would reject Jobs that some host can run. A conflict is rejected
at Job creation, because it is static and the error can name the authors who disagree.

### Empty and resolved-empty host requirements

A conditional requirement, such as a GPU only when a Step asks for one, needs a way to resolve to no requirement.
`min: "{{ 1 if Env.Param.Gpus != '' else None }}"` leaves an amount with neither bound, which the base rules reject, and
`else 0` leaves a GPU requirement on every Step. Discarding a requirement that resolves to nothing lets the expression
decide whether it exists. *anyOf* and *allOf* may be one expression for the same reason, since a list of format strings
cannot omit the field. An empty object is valid so that a template that builds its lists from expressions needs no
special case.

Literal empties stay errors, because no value can change them and they can only be mistakes. The rules are the same for
Job Environments and Environment Templates; base §3.3 constraint 1 applies "in a Job Template", which left open whether
it applied to an Environment Template.

### Values resolved at Job creation

Everything a value or `default` may read is known at Job creation, which makes effective values a static property of
the Job that a scheduler can compare. Values that depended on host state would differ per host. For the same reason a
value reads `RawParam.*` of a PATH Job Parameter and not `Param.*`, which is the host-mapped path; the Environment's
own `Env.Param.*` applies the mapping on the host.

### Path values are used as given

A PATH Job Parameter's value is resolved on the submitting workstation: a relative value is joined with a directory
there, and a submitter may use the value to choose files to send with the Job, so its form matters. An Environment
parameter value has no such role. It only reaches the Environment's own actions, mapped on the Worker Host by the Job's
path mapping rules, so the specification does not check whether it is absolute or which path format it has. A value that
matches no mapping rule passes through unchanged. A literal path is portable only between submitters that use its
format, and a host-local path owned by the Environment Template is better a STRING.

### Not on Step Environments

A Step writes its own Step Environment, so it can write any value there directly. `activation` would mean nothing, since
only that Step's Sessions enter it, and `hostRequirements` would repeat the Step's own. `enableIf` is permitted, so a
Step Environment shared through YAML anchors can still disable itself.

### Every Job Parameter type is permitted

One set of types means one thing to learn. RANGE_EXPR is a compact set of integers that an Environment can use, such as
frames to pre-fetch, and needs nothing new. LIST[PATH] lets a Docker Environment mount every host path a Step uses,
after mapping, which a LIST[STRING] of `RawParam` values could not.

### Lengths of a RANGE_EXPR value

Effective values compare by canonical form, so a length rule on one string would treat equal values differently: under
`minLength: 4`, `1,2,3` passes and the equal `1-3` fails. Checking both forms gives equal values one outcome. For a Job
Parameter the rule is gated on `ENV_PARAMS`, so an existing `EXPR` template keeps its meaning. Where a Job Parameter's
definitions are merged, each definition's lengths keep the rule of the document that contains it, so adding `ENV_PARAMS`
to a Job Template never changes how an Environment Template's constraints are checked.

### Required parameters are allowed

A parameter without a `default` makes each Step that the Environment applies to say what it wants, which suits a Job
Environment like `RenderLicense`. In an `ALWAYS` or `BY_DEFAULT` Environment Template it would break every Job Template
that does not know the parameter, so the choice is the Environment Template author's, who normally gives a default or
uses `ON_REQUEST`.

Which Steps must supply it depends only on the Environment's `activation` and the Steps' entries, not on its *enableIf*
or its *exclusiveGroup*. A missing value is then an error in the Step's definition, which template validation can report
from the Job Template alone, and the *enableIf* never sees a missing value.

### `required: false` is an error on a Job Environment entry

A Job Environment is always present, so `required: false` on its entry can only be a mistake, most likely an entry
meant for an external Environment whose name collides with a Job Environment.

### The limits chosen

A render management system stores each Step's Environment set, effective values, and combined host requirements, and
keys Sessions on the values, so each needs a bound that a template author can rely on. The bounds reuse existing ones.
An Environment has at most 50 parameters, as a Job Template has without `FEATURE_BUNDLE_1`. That extension raised the
limit for templates with many submitter inputs, which an Environment's parameters are not, so it leaves this limit at
50. A STRING or PATH value is at most 1024 characters, the length of a Job Parameter's `default` and `allowedValues`.
The specification sets no maximum number of `dependencies`, and a `required: false` entry may name nothing, so a floor
of 50 `environment:` entries tells authors how many alternatives a portable template may list. Combined host
requirements join sources that each have at most 50 requirements, so rather than a fixed cap, an implementation may
document a limit of at least 50, which every Step's own requirements already fit.

### `ENV_PARAMS` requires `EXPR`

Environment parameters flow into expressions: *enableIf* reads them, `let` bindings and `Job.EnvNames` feed them, and
several parameter types exist only with `EXPR`. Without the requirement, every rule would need a case for a Job
Template and an Environment Template that disagree about `EXPR`. RFC 0008 (`WRAP_ACTIONS`) makes the same requirement.

## Security Considerations

### Trust model

Environment parameter values are written by the author of the Job Template (in `environment:` entries) or come from Job
Parameters (through a `default`), and the submitter already controls both. They are executed by Environment scripts that
the Environment Template's owner controls. An external Environment that reads `{{Param.CondaPackages}}` today has the
same trust relationship. This extension grants the submitter no new privilege. It only lets the same
submitter-controlled input differ per Step, and lets a Step leave out an Environment whose author allowed it. An
Environment Template owner who does not want submitters to choose, for example, arbitrary container images restricts the
parameter with `allowedValues`, which a scheduler checks at Job creation before any Worker Host runs anything.

A Job Template cannot use the extension to skip an Environment that an operator attaches to every Job. An Environment
from a document that does not list `ENV_PARAMS` behaves as `ALWAYS`, so every Session enters it whatever a Job Template
writes, as before the extension (see [Environments from documents without `ENV_PARAMS` are
`ALWAYS`](#environments-from-documents-without-env_params-are-always)). An operator who adopts the extension keeps that
guarantee by setting `activation: ALWAYS`, under which a Step's disabled entry or an *enableIf* that is `false` for a
Step rejects the Job. A Step can decline only a `BY_DEFAULT` Environment, which its author left for Steps to decline.

Environment Template authors must still treat `Env.Param.*` as untrusted input in their scripts, as they should treat
`Param.*` today: the values are chosen by whoever submits the Job, which on a shared system is not the Environment
Template's author.

Do not pass secrets as Environment parameter values. Effective values are part of the Job, which a render management
system stores and may show to anyone who can see the Job, and `REDACTED_ENV_VARS` redacts only what an action prints
after setting a variable with `openjd_redacted_env`, not the values themselves. An Environment that needs a secret
should fetch it on the Worker Host, as it would without this extension.

### Do not substitute values into script source

A format string substitutes text, and an embedded file's `data` is script source. A script line such as
`PACKAGES='{{Env.Param.Packages}}'` breaks when the value contains `'`, and a crafted value such as
`x'; curl ... | sh; '` runs arbitrary commands as the job user. Quoting in the template does not help,
since the value can contain any quote character.

Pass values to scripts in one of these ways instead:

* **As `args` of the action.** Each `args` element reaches the process as one argv entry, with no shell parsing. The
  samples and Basic Examples do this: `args: ["{{Env.File.Enter}}", "{{Env.Param.Packages}}"]`, and the script reads
  `"$1"`. A list-typed parameter such as the Docker sample's `Mounts` expands to one argv entry per element.
* **Through `variables`.** An Environment's `variables` set environment variables before its actions
  run, and a script reads `"$NAME"`, again without parsing the value as code.
* **With `repr_sh`, `repr_cmd`, or `repr_pwsh`** (RFC 0006, requires `EXPR`) when a value must appear in
  a shell command line, as RFC 0008 recommends for wrapped commands.

A script that intentionally word-splits a value, as the Conda sample does with its package list, should
disable pathname expansion (`set -f`), so that a value containing `*` is not expanded against the
Session directory.

### Values in `onExit`

An Environment's `onExit` sees the same values as its `onEnter`, so cleanup driven by a parameter (for
example `license-release --product {{Env.Param.Product}}`) acts on what `onEnter` set up, and a value
cannot change between the two.

## Prior Art

* **Nextflow** — Every `process` can carry its own `conda`, `container`, `module`, and `spack` directives, and a
  pipeline's configuration selects which of them is honored with `conda.enabled = true` or `docker.enabled = true`. The
  same pipeline thus runs with Conda, Docker, Singularity, or preinstalled software, and each process gets only its own
  tools. This is the closest precedent: per-unit software requirements, written once per kind of provisioning, with the
  execution platform choosing which kind applies. This RFC's `required: false` entries are the same pattern, with the
  attached external Environments playing the role of the enabled directive. Nextflow builds the provisioning mechanisms
  into the engine; OpenJD keeps them in Environment Templates that the scheduler's operator owns.
* **Snakemake** — Each `rule` can declare `conda:` (an environment file), `container:`, and `envmodules:`, and the
  command line selects which is used: since Snakemake 8 with `--software-deployment-method` (`--sdm conda`, `--sdm
  apptainer`, `--sdm env-modules`), and before it with `--use-conda`, `--use-singularity`, or `--use-envmodules`.
  Snakemake caches each distinct Conda environment by the hash of its definition, which is the reuse a scheduler can
  achieve by grouping Sessions by effective values.
* **Deadline Cloud queue environments** — Deadline Cloud's Conda queue environment and its sample Rez queue environment,
  which are Environment Templates attached as external Environments, take the `CondaPackages` and `CondaChannels` Job
  Parameters and the `RezPackages` Job Parameter, each applied to every Session of a Job. This RFC generalizes them: the
  same Environment Templates gain a per-Step value that defaults to those Job Parameters, which is the shape of this
  RFC's samples. Deadline Cloud's improved-caching Conda sample names each environment by a hash of its package list and
  reuses it across Sessions on a host, which is the reuse that grouping Sessions by effective values makes more
  frequent.
* **Kubernetes `RuntimeClass`** — A `RuntimeClass` carries `scheduling.nodeSelector` and `tolerations` that are merged
  with the pod's own by conjunction, so a pod that asks for a runtime is placed only where that runtime exists. An
  Environment's `hostRequirements` combine with a Step's in the same way: the platform-owned layer states its placement
  needs and the unit of work inherits them by using it.
* **Argo Workflows** — Every `template` in a workflow specifies its own `container` (image, command, resources), and
  `inputs.parameters` let a step pass values into a template. A parameterized template invoked from several steps with
  different `arguments` is the shape of this RFC's parameterized Job Environment. Argo has no notion of an externally
  supplied environment around a template, since every step is its own container.
* **NVIDIA OSMO** — Every task of a workflow runs in a container, and its `image` is a required field
  ([specification](https://nvidia.github.io/OSMO/main/user_guide/workflows/specification/index.html)). A workflow whose
  tasks use different tools names a different image for each. As in Argo, there is no externally supplied environment
  around a task.
* **Slurm and Environment Modules** — A batch script runs `module load colmap/3.11` per job step, or `srun
  --container-image=...` (with Pyxis/Enroot) per step. The selection lives in the script text, so no tool can see which
  software a step needs without parsing shell, which the [Tooling parseable](../wiki/Design-Tenets.md) tenet asks OpenJD
  to avoid.

## Prototype

The prototype is the `env-params-prototype` branch of
[mwiebe/openjd-rs](https://github.com/mwiebe/openjd-rs/tree/env-params-prototype), developed alongside this RFC. It
implements the extension in `openjd-model`, `openjd-sessions`, `openjd-cli`, and `openjd-for-js`, and its `openjd
check`, `openjd summary`, and `openjd run` pass every 2023-09 conformance test at this RFC's head, including the 445
under `conformance-tests/2023-09/ENV_PARAMS`. The `env-params` branch of
[mwiebe/openjd-model-for-python](https://github.com/mwiebe/openjd-model-for-python/tree/env-params) exposes it to Python
through the Rust-backed bindings.

These parts of the proposal changed because of the prototype:

1. **Exclusive groups are decided across documents.** The first implementation of `exclusiveGroup` decided each
   document's Environments separately, which gave the wrong result when a group spans the Job Template and an attached
   Environment Template. [§7.4.1](../wiki/2023-09-Template-Schemas.md#741-job-creation-with-env_params)
   now decides every Environment of a Step in the Job's Environment order, and its step 6 says that a superseded
   Environment's *enableIf* is not evaluated for the Step.
2. **What a validator knows before Job creation.** Without the Environment Templates, a validator cannot know whether a
   grouped Job Environment is entered, because an attached member of its group may come first.
   [§4](../wiki/2023-09-Template-Schemas.md#4-environment) now says when an Environment is known to be entered or not
   entered. Differential tests of the prototype found no submission that `openjd check` rejects and Job creation
   accepts.
3. **PATH values are used as given.** An earlier draft checked a PATH value against the submission's path format. The
   prototype showed that the result could still depend on that format for a value written as a single expression,
   while the Expression Language already gives template-scope expressions POSIX semantics.
   [§4.5](../wiki/2023-09-Template-Schemas.md#45-environmentparameterdefinition-extension-env_params) item 3 now uses
   PATH and LIST[PATH] values as given (see [Path values are used as given](#path-values-are-used-as-given)).
4. **Joining onto an empty path.** Joining onto an empty PATH value gave a root path. In a change already made on
   mainline, the Expression Language now follows `pathlib`, where an empty path joined with another gives the other.
5. **Job-creation errors in step order.** With several failures, deciding one document at a time reported errors in an
   order unrelated to §7.4.1. The prototype reports them in one pass, ordered by the §7.4.1 step, then the Step, then
   the Job's Environment order. This also changes the order in which `openjd-rs` reports errors for a Job Template
   without `ENV_PARAMS` that has Environment Templates attached, a change to review on its own.
6. **Effective values are equal only with the same text.** An earlier draft compared FLOAT values as numbers. The
   prototype keeps a FLOAT's text, as the Expression Language does, and a Step that supplied `"3.1"` ran its Tasks in an
   Environment that a Step supplying `"3.10"` had entered, which printed `3.10`. Its serialized values also kept the
   text, so `1.5` and `"1.50"` were equal but serialized differently, and a scheduler that keyed Sessions on them
   needed a canonical encoding of numbers.
   [§3.2.2](../wiki/2023-09-Template-Schemas.md#322-effective-environment-parameter-values) now makes two values equal
   only when they have the same type and string form, so the Environment sees what was compared, and the type with the
   text is the key (see [Sessions that serve several Steps](#sessions-that-serve-several-steps)).
7. **Required parameters are checked before `enableIf`.** The prototype decided an Environment's *enableIf* first and
   treated a missing value as unknown, so `"not Param.F and Env.Param.X == 'a'"` disabled the Environment for a Step
   that did not supply `X`, and the Job ran. Whether it should was not defined. Constraint 7 now applies to every
   Environment that applies to the Step, whatever its *enableIf*, and the *enableIf* reads only concrete values (see
   [`enableIf` sees only concrete values](#enableif-sees-only-concrete-values)).

These were unclear or hard to implement:

1. **The number of `environment:` entries.** An entry with `required: false` may name nothing, so a Step's
   `dependencies` are not bounded by the number of Environments. The specification leaves the maximum to
   implementations, and the prototype adds a caller limit, `CallerLimits::max_step_environment_entries`.
2. **Why an Environment is not entered.** An implementation that shows a Step's Environments to users needs the reason
   one was not entered: declined, disabled, superseded, or named by an optional entry that resolved to nothing. Job
   creation knows it, but a Job's Steps do not carry it, so the prototype adds per-Step Environment statuses to the
   result of Job creation.

## Implementation Impact

- **Rust (openjd-rs)**: `openjd-model` gains the new `<Environment>` fields, including `exclusiveGroup`, the
  `environment:` and `step:` forms of `StepDependency`, `Job.EnvNames`, and the `Env.Param.*` and `Env.RawParam.*`
  scopes, reusing the existing parameter-definition and host-requirement types. Job creation computes each Step's
  Environment set (evaluating the Environments' *enableIf* in the Job's Environment order and applying each
  `exclusiveGroup` as it goes, so a superseded Environment's *enableIf* is not evaluated), effective values, and
  combined host requirements, in the order §7.4.1 gives, and stores them on the Job's Steps. `openjd-sessions` takes the
  effective values when it enters an Environment, as it takes Job Parameter values today, and `openjd run` passes the
  values of the Step being run.
- **Python (openjd-model-for-python, openjd-sessions-for-python)**: openjd-model-for-python includes Rust-backed
  bindings to openjd-rs, and openjd-sessions-for-python a Session that runs on them. The prototype's `env-params`
  branches extend the bindings to the new fields, Job creation, and effective values, and pass the values when the
  Session enters an Environment, so Python gets the feature from the Rust implementation rather than from a second one.
  The pure-Python pydantic model would need the same changes as `openjd-model` to support the extension itself.
- **Other languages**: Nothing in the extension is harder to implement in one language than another. It adds model
  fields, checks at Job creation, and values passed when a Session enters an Environment, and needs no new run-time
  mechanism.
- **Schedulers**: Store each Step's Environment set, effective values, and combined host requirements, which the Job
  carries, and pass the values to the Worker when a Session enters each Environment. Place Sessions by the combined host
  requirements, which have the shape of a Step's. A scheduler that shares Sessions across Steps must also compare their
  effective values ([How Jobs Are Run](../wiki/How-Jobs-Are-Run.md#environment-parameters)); one that never shares a
  Session across Steps needs no grouping change. Using the values for host affinity is an optional optimization.
- **Conformance tests**: The PR includes a conformance suite under `conformance-tests/2023-09/ENV_PARAMS`, whose README
  indexes each rule the extension adds and the tests that cover it (see [Validation](#validation)).

The effective values are a small map per Step and Environment, computed once at Job creation. At run
time they are passed when a Session enters an Environment and compared when a scheduler shares a
Session.

## Rejected Ideas

### A `stepOverridable` flag on template-level Job Parameters

The discussion's first sketch marked a Job Parameter such as `CondaPackages` as overridable and let a Step set it. It is
rejected because:

1. A Job Parameter has one value per Job by definition. Every format string that reads `Param.CondaPackages` (in a Step
   script, a name, a host requirement) would then have a value that depends on where it is read, which breaks the
   meaning of `Param.*` everywhere.
2. The Job Parameter is declared by whichever template wins §1.2.1 merging, so the flag would have to be merged too, and
   a Job Template could make an Environment Template's parameter overridable or not without that template's agreement.
3. It gives the Environment no say in what a Step may change: every overridable parameter becomes Step-settable for
   every Environment that reads it.

An Environment parameter is declared by the Environment, read only by it, and defaults to the Job Parameter, which gets
the same compatibility without any of these effects.

### A flat per-Step map of values

A Step could carry `environmentParameters: { Packages: "colmap=3.11", Image: "..." }` for every Environment to read.
Rejected because names collide: a Conda and a Pip Environment can both call their input `Packages`, and a flat map would
send the same value to both. It also gives `required` no place, and a typo no Environment to be checked against.

### Letting a Step's script read `Env.Param.*`

A Step might want to read the value it supplied, for example to log the Conda packages it asked for. Rejected because
the reference is ambiguous: two Environments wrapping the Step may declare the same parameter name, and `Env.*` inside
an Environment already means "this Environment". A Step that needs the value already has it, since it wrote it; it can
bind it once with a Step `let` and use the binding in both the `environment:` entry and its script.

### Matching external Environments by something other than name

An Environment Template could carry a separate "kind" (`conda`, `docker`) that entries match on, so a Job Template could
say "any Conda-like Environment". Rejected for now: Environment names are already how external Environments are
identified and ordered, and a kind registry would need a vocabulary the specification does not have. The `required:
false` pattern with one entry per expected name covers the motivating cases, and `exclusiveGroup` decides which of the
attached ones a Step uses.

### A separate key for Environment requests

A Step could request Environments in a key of its own, such as `environments:` beside `dependencies`, since an entry
for an Environment does not delay scheduling the way a Step dependency does. This RFC keeps the requests in
`dependencies` because each entry there names something the Step needs in place before its Tasks run: a completed Step,
or an Environment entered with the Step's values. `required: true` rejects
a submission in which the Environment is missing, as a missing Step is rejected. A separate key would sit beside
`stepEnvironments`, which defines Environments, and readers would have to learn which of two lists defines Environments
and which requests them. The difference in ordering is real, and [The `environment:` form of
`<StepDependency>`](#the-environment-form-of-stepdependency) states it. With `step:` and `environment:` keys, each entry
says what kind of thing it names.

### Split the Job into several Jobs with job-to-job dependencies

A pipeline whose Steps need different software could be split into one Job per application, each setting the queue's
Conda Job Parameters for itself, and chained by a scheduler's job-to-job dependencies. This is rejected because it
loses:

1. **Step dependencies and parallelism within one Job.** In one Job, independent Steps run their Tasks in parallel and
   a dependent Step starts when the Steps it depends on complete. Job-to-job dependencies are not part of Open Job
   Description, so the chain is specific to one scheduler, and the pipeline is no longer one portable template.
2. **One submission and one set of Job Parameters.** The user submits, monitors, retries, and cancels one Job, and sets
   a frame range or an output directory once, rather than keeping several Jobs' parameters consistent.
3. **What other systems do.** No system in [Prior Art](#prior-art) requires a workflow to be split by software. Each
   lets one workflow give each unit of work its own environment.

Splitting remains possible, and this RFC does not prevent it.

### `activation` as a list of Session kinds

Its vocabulary would grow with each kind of Session that a later extension adds, and a list naming only some kinds of
Session says the same as an `ON_REQUEST` Environment that only the entities that need it request.

### `activation` on the entry instead of the Environment

A Step could write `environment: Conda, exclusive: true` to mean "enter this for me and not for Steps that do not ask".
Rejected because whether an Environment is opt-in is a property of the Environment, decided by its author: an auditing
Environment must not become opt-in because one Step's entry says so, and two Steps could disagree.

## Open Questions

There are no open questions. The last one, whether to name *enableIf* `when`, was decided as `enableIf`, an expression
field (see [The name `enableIf`](#the-name-enableif)).

## Future Work

* **`WrappedEnv.Param.*` for wrap hooks**, so a wrapping Environment can read the effective values of the inner
  Environment whose action it wraps, if a use case appears. A wrapping Environment reads its own parameters today.
* **Matching external Environments by a standard kind** (see [Rejected
  Ideas](#matching-external-environments-by-something-other-than-name)).
* **A Job-level default for a whole `environment:` entry**, so a Job Template can set a value once for all its Steps
  without a Job Parameter.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is
more permissive.
