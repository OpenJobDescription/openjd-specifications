* Feature Name: Environment Parameters
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/209
* Start Date: 2026-10-17
* Specification Version: 2023-09 extension ENV_PARAMS
* Accepted On: (pending)
* Depends On:
  * RFC 0002, Model Extensions (https://github.com/OpenJobDescription/openjd-specifications/issues/57)
  * RFC 0005, Expression Language (`EXPR`) (https://github.com/OpenJobDescription/openjd-specifications/pull/93), which
    `ENV_PARAMS` requires
* Related:
  * Discussion #198, the idea thread for this RFC
    (https://github.com/OpenJobDescription/openjd-specifications/discussions/198)
  * RFC 0008, Environment Wrap Actions (`WRAP_ACTIONS`)
    (https://github.com/OpenJobDescription/openjd-specifications/pull/130)
  * RFC 0009, Service (`SERVICE`) (draft), whose `service:` dependency form this RFC's `environment:` form follows, and
    whose earlier drafts defined a `runScope` field that this RFC replaces with `activation`
  * RFC 0011, Control Flow (`CONTROL_FLOW`) (draft), whose draft also proposes `enableIf` on an Environment, which this
    RFC defines

## Summary

Consider a Job that uses different software together, like decoding a video and then processing each frame. Each Step
consumes the output of the one before it, so the Steps belong in one Job. Open Job Description is structured to let
external Environments, such as a Conda or Docker environment, provide software to Jobs, but currently this only works
with Job Parameters that have one value for the whole Job. The Environment then provides the same software to every
Step.

This RFC lets each Step configure the Environments that wrap it. An `<Environment>` declares the parameters a Step may
set in `envParameterDefinitions` and reads them as `{{Env.Param.<name>}}`. A Step supplies values in an `environment:`
entry of its `dependencies`, so the decoding Step and the processing Step can each ask the Conda Environment for their
own packages.

One Job Template can then get its software from whichever of these Environments a system provides, such as Conda on one
and Docker on another, and run unchanged where none is provided. Where a system provides several, the Environments
themselves decide which one each Step uses. Existing Environment Templates can adopt parameters without breaking the Job
Templates that use them today.

Not every Environment belongs in every Session. An Environment can choose whether every Session enters it or only the
Sessions of Steps that ask for it, and can skip the Steps it has nothing to do for, such as a Step that asks Conda for
no packages.

An Environment can also say where it can run, so a Docker Environment places its Steps on Linux hosts, and on GPU hosts
only for the Steps that ask for a GPU.

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

### Why the values come from the Step

A Session enters its Environments and then runs Tasks, which may come from one Step or from several whose Environments
are identical. The Step is the unit that knows what software its Tasks need, so the Step says what an Environment should
do for them.

### Backward compatibility

This RFC is additive and gated by the `ENV_PARAMS` extension name declared under RFC 0002.

- A document that uses any of the syntax listed in the first row of [Validation](#validation) MUST list `ENV_PARAMS` and
  `EXPR` in its `extensions`, and a scheduler that does not implement `ENV_PARAMS` rejects it under RFC 0002. A document
  that lists `ENV_PARAMS` without `EXPR` is rejected, and a document that lists neither keeps its current meaning.
  `step:` is a synonym for `dependsOn:`, which keeps its meaning and stays valid with or without `ENV_PARAMS`; the plan
  to remove `dependsOn:` applies to a future major version of the specification, not to `jobtemplate-2023-09`.
- An extension applies only to the document that lists it. A Job Template that does not list `ENV_PARAMS` runs with an
  Environment Template that does: every Environment parameter takes its default, which is how an Environment Template
  author keeps existing Job Templates working while adding per-Step configuration. Such a Job Template cannot request
  anything, so its Sessions never enter an attached `ON_REQUEST` Environment. An author who wants existing Job Templates
  to keep getting an Environment leaves its `activation` at the default, `BY_DEFAULT`, or sets `ALWAYS`.
- An Environment Template that does not list `ENV_PARAMS` runs with a Job Template that does. Its Environment has the
  default `activation: BY_DEFAULT` and no parameters, so an `environment:` entry that names it is an error only if the
  entry supplies parameters (see [`<StepDependency>`](../wiki/2023-09-Template-Schemas.md#32-stepdependency) constraint
  5).
- An Environment Template written before this extension under a [recommended name](#recommended-names-non-normative)
  rejects Job Templates that supply its recommended parameters, even with `required: false`
  ([§3.2.1](../wiki/2023-09-Template-Schemas.md#321-resolving-external-environments) item 1). Deadline Cloud's console
  Conda queue environment (`Conda`) is such a case today. The remedy is for the Environment Template's author to add
  `ENV_PARAMS` and the recommended `envParameterDefinitions`, with defaults that read the existing Job Parameters, as
  `conda-env-params.yaml` does; see [An Environment without the supplied parameter is an
  error](#an-environment-without-the-supplied-parameter-is-an-error).
- No existing field changes meaning. A Job with no `environment:` entries, no Environment `envParameterDefinitions`, no
  `activation`, and no Environment `enableIf` behaves as today, including which Environments each Session enters and how
  Sessions are shared between Steps. An Environment written before this extension has `activation: BY_DEFAULT` and no
  `enableIf`, so every Session enters it, as today. A Job Template that lists `ENV_PARAMS` but no `environment:`
  entries, run with an Environment Template that declares parameters and keeps the default `activation`, also shares
  Sessions as today: every Step takes the same defaults, so every Step's values are equal.
- Three changes state or correct rules of the base specification, and apply with or without the extension. The
  definition of `<nonnegativefloatstring>` in §3.3.1 said "non-zero and positive", which contradicts its name and an
  amount's `min` of 0, and now says "non-negative". §3.3.2.1 now states that an *allOf* written as a list for
  `attr.worker.os.family` or `attr.worker.cpu.arch` has at most one element, which the base conformance suite already
  tests. §1.1 item 7 now states that a Session enters the Environments attached from Environment Templates before the
  Job Template's `jobEnvironments`, in the order they are attached, where the base specification did not say.

## Specification

The normative text of this extension is the wiki edits in this pull request: [Template
Schemas](../wiki/2023-09-Template-Schemas.md), [Expression Language](../wiki/2026-02-Expression-Language.md), and [How
Jobs Are Run](../wiki/How-Jobs-Are-Run.md). This section summarizes each change and links to the wiki section that holds
the formal text; where the two differ, the wiki governs. A section number (§) in this RFC refers to Template Schemas
unless another page is named.

### Terminology

| Term | Meaning |
|------|---------|
| **Environment parameter** | A value declared in an `<Environment>`'s `envParameterDefinitions` and read only inside that Environment, as `Env.Param.<name>`. A Job Parameter is declared in a template's top-level `parameterDefinitions` and read as `Param.<name>`. |
| **Job Environment** | An entry of a Job Template's `jobEnvironments`. |
| **External Environment** | An Environment that the scheduler attaches to a Job from an Environment Template, also called an attached Environment. A Deadline Cloud queue environment is an example. |
| **Request** | A Step requests an Environment with an enabled `environment:` entry in its `dependencies` that names it. |
| **Disabled entry** | An `environment:` entry whose own `enableIf` is `false`. It requests nothing and supplies no values. |
| **Decline** | A Step declines a `BY_DEFAULT` Environment with a disabled entry naming it, and its Sessions then do not enter it. |
| **Disabled Environment** | An Environment whose own `enableIf` is `false` for a Step, or that is superseded for it. That Step's Sessions do not enter it. |
| **Superseded** | An Environment is superseded for a Step when an earlier Environment of its `exclusiveGroup`, in the Job's Environment order, is one the Step's Sessions enter. |
| **Effective values** | For one Step and one Environment its Sessions would enter, the value of each of the Environment's parameters: the one the Step's enabled entry supplies, or else the parameter's resolved `default`. |
| **Combined host requirements** | A Step's own `hostRequirements` together with those of every Environment its Sessions enter. |
| **Expression field** | A field whose value is one Expression Language expression written without `{{ }}`, with the target type its `@expr <type>` annotation gives. Both `enableIf` fields of this RFC are expression fields. |

### Extension name and the documents that list it

[§1.1](../wiki/2023-09-Template-Schemas.md#11-job-template) adds `ENV_PARAMS`, which requires `EXPR` (see [`ENV_PARAMS`
requires `EXPR`](#env_params-requires-expr)). [§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) gives
an Environment Template the `$schema` and `extensions` keys, as the RFC 0009 draft also proposes. An extension applies
only to the document that lists it, so an Environment Template can adopt parameters while Job Templates that do not
list `ENV_PARAMS` keep running with it (see [Backward compatibility](#backward-compatibility)).

The item descriptions of *jobEnvironments*, *stepEnvironments*, *let*, and *dependencies* each gain a sentence so that
they stay true with the extension. §1.1 item 7 also states the Job's Environment order, which applies with or without
the extension: attached Environments first, in the order they are attached, then the `jobEnvironments`.

### Environment parameters

[§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 3, *envParameterDefinitions*, lets an Environment declare
up to 50 parameters, read only inside it as `Env.Param.<name>` and `Env.RawParam.<name>`. The new
[§4.5](../wiki/2023-09-Template-Schemas.md#45-environmentparameterdefinition-extension-env_params) defines each as a
`<JobParameterDefinition>` of any type available with `EXPR`, except that:

* The `default` is a format string resolved when the Job is created, and may read the same document's Job Parameters.
  A parameter without one must be supplied by every Step whose Sessions enter the Environment.
* A PATH or LIST[PATH] value is in the Job's submission path format and must be absolute or a URI.
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
does not delay scheduling. *required* says whether the Environment must be present. *enableIf* is evaluated when the
Job is created; a `false` entry requests and supplies nothing, declines a `BY_DEFAULT` Environment, and is an error for
an `ALWAYS` one. *parameters* supplies values, each a literal or a format string resolved when the Job is created.

The constraints keep an entry to one form and one Environment to one entry, require each key to be declared and each
value to be valid, require every Step whose Sessions enter an Environment to supply each parameter without a `default`
(constraint 7), and forbid `required: false` on an entry that names a Job Environment. The section says at which stage
each constraint is checked.

### Resolving external Environments

The new [§3.2.1](../wiki/2023-09-Template-Schemas.md#321-resolving-external-environments) resolves an entry that names
no Job Environment against the attached Environment Templates when the Job is created. No match is an error only for an
enabled entry with `required: true`, and two matches are an error. A resolved entry is checked against the Environment
whatever *required* says (see [An Environment without the supplied parameter is an
error](#an-environment-without-the-supplied-parameter-is-an-error)).

### Which Sessions enter an Environment

[§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 4, *activation*, is one of:

* `ALWAYS`: every Session. Declining it or disabling it for a Step is an error.
* `BY_DEFAULT`, the default: every Session, except a Step's that declines it or for which its *enableIf* is `false`.
* `ON_REQUEST`: the Sessions of the Steps that request it, less any for which its *enableIf* is `false`.

§4 item 6, *enableIf*, is evaluated when the Job is created, once per Step with that Step's effective values.
[§3.2.2](../wiki/2023-09-Template-Schemas.md#322-effective-environment-parameter-values) decides it before constraint 7
and the value checks, which do not apply to a Step for which it is `false`. A result that depends on a missing or
unconvertible value is an error. §4 item 7, *exclusiveGroup*, names a group of Environments of which each Step's
Sessions enter only the first, in the Job's Environment order, that they would otherwise enter and that its *enableIf*
does not disable. The later ones are superseded, which disables them for the Step, and their *enableIf* is not
evaluated. Attached Environments come first, so one can supersede a Job Environment, and a validator given only the Job
Template treats a grouped Job Environment as undetermined. An `ALWAYS` Environment cannot have a group (see
[`exclusiveGroup`](#exclusivegroup)). A Step Environment may have *enableIf* but none of the other new fields (see [Not
on Step Environments](#not-on-step-environments)).

### Effective values and Session sharing

§3.2.2 defines a Step's effective value for each parameter: the value its enabled entry supplies, or else the resolved
`default`. Two values are equal when they have the same type and resolved value before path mapping, and RANGE_EXPR
values compare by canonical form. [How Jobs Are Run](../wiki/How-Jobs-Are-Run.md#environment-parameters) lets a Session
run a Step's Tasks only when it entered the Step's Environments with the Step's values.

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
work done at Job creation. The new [§7.5](../wiki/2023-09-Template-Schemas.md#75-expression-fields) defines expression
fields, which both *enableIf* fields are: one typed expression with no `{{ }}` and no implicit conversion other than
widening `int` to `float`. Until it is evaluated, a check that depends on one reports an error only when the error holds
for every value it could take.

### Expression Language

The [Expression Language](../wiki/2026-02-Expression-Language.md) adds the new symbols to
[§1.2.2](../wiki/2026-02-Expression-Language.md#122-built-in-symbol-types), defines expression fields in
[§1.3.2](../wiki/2026-02-Expression-Language.md#132-evaluation-within-template-schemas), and names an Environment's
*enableIf* as an exception in [Progressive Expression
Evaluation](../wiki/2026-02-Expression-Language.md#progressive-expression-evaluation).

### How Jobs Are Run

[How Jobs Are Run](../wiki/How-Jobs-Are-Run.md) gains an [Environment
Parameters](../wiki/How-Jobs-Are-Run.md#environment-parameters) section for template authors, and its Sessions and Host
Requirements sections describe the per-Step Environment set and an Environment's host requirements.

### Extensions specified after this one (non-normative)

This RFC is specified against mainline. Every value it adds is fixed when the Job is created: effective values, each
Step's Environment set, each Environment's *enableIf*, and combined host requirements. An RFC accepted after this one
that adds a kind of Session or a later stage of evaluation specifies how it extends these rules.

### Recommended names (non-normative)

The portability of a Job Template that writes `environment: Conda` depends on Environment Templates using the same
Environment and parameter names. The specification does not mandate names. This RFC recommends the following, which the
samples use, for Environment Templates that provision software. Each parameter defaults to the template-level Job
Parameter that Deadline Cloud's Conda and Rez queue environments already use, so existing Job Templates keep working.
Such an Environment keeps the default `activation`, `BY_DEFAULT`, or uses `ON_REQUEST`, uses its `enableIf` to skip a
Step with nothing to install, and has `exclusiveGroup: SoftwareProvider`, so that where several are attached each Step
uses the first one attached.

| Environment | Parameter | Type | Default | Meaning |
|-------------|-----------|------|---------|---------|
| `Conda` | `Packages` | STRING | `{{Param.CondaPackages}}` | Space-separated package specs. Empty means use the host's software. |
| `Conda` | `Channels` | STRING | `{{Param.CondaChannels}}` | Space-separated channels. |
| `Rez` | `Packages` | STRING | `{{Param.RezPackages}}` | Space-separated Rez package requests. |
| `Docker` | `Image` | STRING | `{{Param.DockerImage}}` | The container image. |
| `Docker` | `Mounts` | LIST[PATH] | `[]` | Host paths to make visible at the same path in the container. |
| `Docker` | `Gpus` | STRING | `""` | The value for `docker run --gpus`. |

### Validation

This section is a non-normative index of the rules this extension adds, by the stage that checks them. Each row cites
the section of Template Schemas that states the rule. That section is normative, and where a row and its section differ,
the section governs. Constraint numbers refer to
[`<StepDependency>`](../wiki/2023-09-Template-Schemas.md#32-stepdependency).

| Rule | Checked at |
|------|-----------|
| `ENV_PARAMS` listed by any document that uses Environment *envParameterDefinitions*, `activation`, `hostRequirements`, `enableIf`, or `exclusiveGroup`; `environment:` or `step:` entries; `Job.EnvNames`, `Env.Param.*`, or `Env.RawParam.*`; an `anyOf` or `allOf` written as one expression; or a `hostRequirements` that is empty or has empty lists | Template validation |
| A document that lists `ENV_PARAMS` also lists `EXPR` | Template validation |
| Environment *envParameterDefinitions*: 1–50 entries, unique names, not on *stepEnvironments*, permitted types and fields | Template validation |
| `activation` is `ALWAYS`, `BY_DEFAULT`, or `ON_REQUEST`, and not on *stepEnvironments* | Template validation |
| `exclusiveGroup` is an `<Identifier>`, not on *stepEnvironments*, and not on an Environment whose `activation` is `ALWAYS` (§4 *exclusiveGroup*) | Template validation |
| Of the Environments a Step's Sessions would enter that share an `exclusiveGroup`, only the first in the Job's Environment order whose *enableIf* is not `false` for the Step is entered; the later ones are superseded and disabled for the Step, and their *enableIf* is not evaluated (§4 *exclusiveGroup*, §3.2.2, §7.4.1) | Job creation, per Step. Before then only as far as known; a Job Environment with an `exclusiveGroup` is undetermined unless the validator is given the Environment Templates (§4) |
| Environment *hostRequirements*: §3.3 shape and constraints, and not on *stepEnvironments*. They reference only the scopes §7.3.2 lists for them | Template validation |
| In a document that lists `ENV_PARAMS`, a Step's or an Environment's *hostRequirements* may be `{}` or have empty *amounts* and *attributes* (§3.3 constraint 1); a literal amount with neither `min` nor `max`, or a literal empty `anyOf` or `allOf`, is still rejected (§3.3) | Template validation |
| In a document that lists `ENV_PARAMS`, an `anyOf` or `allOf` written as a string is exactly one `{{ }}` expression, and its static type fits `list[string]?` (§3.3.2) | Template validation |
| Environment *enableIf*: an expression field of type `bool` (§7.5) that references only the scopes §7.3.2 lists for it, which differ between a Step Environment and other Environments | Template validation |
| A check over a Step's Environment set, such as the `WRAP_ACTIONS` single-layer rule, where an Environment's *enableIf* decides membership | Job creation; before then only when the violation holds whatever every undetermined *enableIf* resolves to (§7.5 rule 5) |
| Environment *enableIf* does not resolve to `null`, for each Step whose Sessions would enter the Environment | Job creation, per Step |
| The *enableIf* of an Environment whose `activation` is `ALWAYS` is not the literal `false` (§4 *activation*) | Template validation |
| The *enableIf* of an Environment whose `activation` is `ALWAYS` does not resolve to `false` for any Step; the error names the Step and the Environment. This covers *jobEnvironments* entries and attached Environments (§4 *activation*) | Job creation, per Step |
| A disabled `environment:` entry (its *enableIf* is `false`) for an Environment whose `activation` is `ALWAYS` is an error naming the Step and the Environment (§3.2 item 3.2) | Template validation for a literal `false` on an entry that names a *jobEnvironments* entry; otherwise Job creation |
| A Step's disabled `environment:` entry for a `BY_DEFAULT` Environment declines it: the Step's Sessions do not enter it, and constraint 7, the checks of the Step's effective values for it, and its *hostRequirements* do not apply to the Step (§3.2 item 3.2) | Template validation for a literal `false`, as far as the check is known then (§7.5 rule 5); Job creation otherwise |
| An Environment's *hostRequirements*, resolved for a Step, satisfy §3.3.1 and §3.3.2 (for example, a non-negative `min`, and no two names in one source equal after resolution) once requirements that resolve to `null` are discarded, as from a Step's own (§3.3) | Job creation, per Step |
| An *anyOf* or *allOf* of a Step's or an Environment's *hostRequirements* that has no values after resolution (an empty list result, or list items that all resolve to `null`) is rejected, naming the Step or Environment and the attribute (§3.3 item 3, §3.3.2) | Job creation, per Step |
| An *anyOf* or *allOf* written as one expression that resolves to `null` is omitted, and an attribute requirement left with neither is discarded (§3.3 item 2, §3.3.2); each element of a list result satisfies `<AttributeCapabilityValue>` and the list has at most 50 elements | Job creation, per Step |
| Combined host requirements are satisfiable: `min` ≤ `max` for each amount, and for `attr.worker.os.family` and `attr.worker.cpu.arch` a value in every list (§3.3.3 items 1, 2.1) | Job creation |
| An *allOf* for `attr.worker.os.family` or `attr.worker.cpu.arch` has at most one element (§3.3.2.1) | Template validation for a list; Job creation for a `<ListExpressionString>` result |
| `default` references only `RawParam.*` and `Param.*` other than PATH and LIST[PATH] of the same document's Job Parameters | Template validation |
| A literal `default` satisfies its parameter's type and constraints, whether or not any Step uses it, and whatever any `enableIf` decides | Template validation |
| A RANGE_EXPR value satisfies *minLength* and *maxLength* both as written and in canonical form: every Environment parameter, and a Job Parameter in a document that lists `ENV_PARAMS` (§2.10, §4.5) | Template validation for literals; Job creation |
| `Env.Param.*` / `Env.RawParam.*` name a parameter of the enclosing Environment, and appear only inside it | Template validation |
| An entry's *parameters* value or *enableIf* references only `RawParam.*`, non-PATH `Param.*`, `Job.Name`, `Job.EnvNames`, `Step.Name`, and the Step's `let`; never `Task.*`, `Session.*`, or `Env.*` (§3.2) | Template validation |
| `Job.EnvNames` appears only inside a `{{ }}` expression or an expression field, and not in an Environment parameter `default` | Template validation |
| An expression field (§7.5): parses as one expression, with no `{{ }}`; its static type fits its target type (Expression Language §1.2.3 step 1), or is that made optional, with no implicit conversion other than widening `int` to `float`; a boolean, integer, or float scalar that fits is a literal; a `null` or omitted-value field is an error | Template validation; a `null` result at evaluation |
| `<StepDependency>` has exactly one of *dependsOn* / *step* / *environment*; *required*, *enableIf*, and *parameters* only with *environment* (constraint 1) | Template validation |
| A *step* entry obeys every rule of the *dependsOn* entry it is a synonym of; a *step* and a *dependsOn* entry naming one Step are duplicates (§3.2 item 2) | Template validation |
| An entry's *enableIf* is an expression field of type `bool` (constraint 9, §7.5) | Template validation |
| An entry's *enableIf* does not resolve to `null` | Job creation |
| *environment* does not name the Step's own *stepEnvironments* entry; no duplicates per list; 1–50 *parameters* (constraints 2–4) | Template validation |
| `required: false` not used on an entry naming a *jobEnvironments* entry (constraint 8) | Template validation |
| Keys and literal values of *parameters* for a *jobEnvironments* entry (constraints 5, 6), only for an enabled entry; a disabled entry's *parameters* are not checked (§3.2 item 3.2) | Template validation for an entry whose *enableIf* is absent or `true`; Job creation for one whose *enableIf* is an expression that resolves to `true` |
| Each parameter without a `default` is supplied by every Step whose Sessions enter the Environment: every Step for `ALWAYS`, every Step that does not decline it for `BY_DEFAULT`, every requesting Step for `ON_REQUEST`, except Steps for which the Environment is disabled. This covers *jobEnvironments* entries and, after resolution, attached Environments (constraint 7, §3.2.1) | Job creation. For a *jobEnvironments* entry, also template validation when constraint 7 fails whatever every undetermined entry or Environment *enableIf* resolves to (§7.5 rule 5) |
| External name resolution: missing with `required: true`, or ambiguous (§3.2.1) | Job creation |
| Keys and values for an external Environment; resolved format-string values (constraints 5, 6). A key the resolved Environment does not declare is an error even with `required: false` (§3.2.1 item 1) | Job creation |
| An attached `ALWAYS` Environment with the name of a *jobEnvironments* entry, which no entry can reach, has every parameter supplied by a `default` (§3.2.1 item 4) | Job creation |
| A format-string value or `default` for a list-typed parameter is a single `{{ }}` expression (§3.2, §4.5) | Template validation for `default`s and *jobEnvironments* entries; Job creation for external Environments |
| A resolved, non-literal `default` satisfies its parameter's type and constraints, for each Step that takes it (§4.5) | Job creation |
| An Environment disabled for a Step (its *enableIf* is `false` with the values that are known, or it is superseded) is not held to constraint 7, and the Step's effective values for it are not checked; the entry's keys (constraint 5) and value forms still are (§3.2.2 items 3, 4) | Template validation for a literal `false`; Job creation otherwise |
| An Environment *enableIf* whose result depends on a missing, unresolvable, or unconvertible value is an error (§3.2.2) | The earliest stage at which it is known: template validation for a value known then to be missing, whatever every value still unknown resolves to; Job creation otherwise |
| PATH and LIST[PATH] values absolute in the submission path format, or URIs; their string constraints, against the unmapped value. This includes a literal `default` that no Step uses (§4.5) | Job creation |

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

`dependencies` is where a Step says what it needs, and RFC 0009 adds `service:` there for the same reason. Putting the
values beside the name groups everything a Step says about one Environment in one entry, and the name keeps the values
unambiguous when two Environments use the same parameter name (see [Rejected Ideas](#a-flat-per-step-map-of-values)).
The entry does not delay scheduling, but it is still a dependency: a `required: true` entry rejects a submission without
the Environment.

### `step:` as a synonym of `dependsOn:`

Every other form of `<StepDependency>` is keyed by the kind of thing it names, and inside a list named `dependencies`,
"depends on" says nothing the list does not already say:

```yaml
dependencies:
  - step: DecodeFrames
  - environment: Conda
    parameters: {Packages: "colmap=3.11"}
```

Renaming the key would break every existing Job Template, so `step:` is a synonym and `dependsOn:` keeps its meaning
until a future major version. `step:` is gated by `ENV_PARAMS` only because this RFC adds it.

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

An Environment that omits `activation` must keep today's behavior, in which every Session enters it. Both values do,
since a template written before this extension can neither decline an Environment nor give it an *enableIf*.
`BY_DEFAULT` is the default so that an author who writes an *enableIf* gets what it says without also writing
`activation`.

### `enableIf` on the Environment

An entry's *enableIf* lets the Step's author say when an Environment is wanted. The Environment's *enableIf* lets its
own author say when it applies, which with parameters is often a question about the Step's values: a Conda Environment
has nothing to do for a Step with no packages. It keeps a `BY_DEFAULT` Environment that existing Job Templates rely on
out of the Sessions that would enter it only to do nothing.

It is decided at Job creation, once per Step, so Session sharing and combined host requirements see a fixed set of
Environments. It reads the same scopes as the Environment's *hostRequirements*, and not the Job Template's Step names or
bindings, so it means the same in an Environment Template as in a Job Template.

A disabled Environment is not held to constraint 7, and its values are not checked, since a Step that never enters it
has no reason to configure it. An *enableIf* whose result depends on a missing or unconvertible value is an error, so
the mistake is reported rather than hidden.

`Job.EnvNames` lists an Environment even for the Steps for which it is disabled. Otherwise `Job.EnvNames` would depend
on *enableIf* results that can be computed from `Job.EnvNames`.

### The name `enableIf`

It is the name discussion #81 proposed and RFC 0011 uses for Steps. It says what `false` does: a disabled Environment is
not entered and a disabled entry requests nothing. A name such as `when:` invites the reading "wait until this is true",
and OpenJD Steps do wait.

### Expression fields rather than format strings

Both *enableIf* fields hold one boolean expression. As a Format String, `"{{Env.Param.Packages != ''}}"`, the braces say
"interpolate here" where there is nothing to interpolate, admit errors that exist only because of them (`"x{{true}}"`),
and bring implicit conversions under which `"{{'yes'}}"` becomes `true`. As an expression field, the value is
`"Env.Param.Packages != ''"` and its type must fit `bool` without conversion, as a `let` binding already reads.

Existing single-expression fields such as `timeout` stay as they are, since changing their kind would break accepted
templates. A constant expression such as `"false"` is undetermined at template validation like any other expression, so
implementations agree on what template validation reports without each deciding which expressions are constant.

### An Environment without the supplied parameter is an error

`required: false` makes an absent Environment acceptable, not an entry that supplies a parameter the Environment lacks.
The case arises during migration: an existing `Conda` Environment has the recommended name but no `Packages` parameter.
Rejecting the submission fails before anything runs, and the fix belongs to the Environment Template's author.

### Names resolve to the Job Template first

An entry that names one of the template's own `jobEnvironments` can be checked at template validation, and resolving
those names first means an attached Environment can never change what such an entry refers to.

### External Environments are named implicitly

RFC 0009 requires a Job Template to declare each external Service in `externalServices`, so that its `Service.*`
references can be type-checked. A Job Template never reads `Env.Param.*`; it only writes values, so no expression in it
depends on an external Environment's shape. A declaration would be a second place to write the name, would add no
information, and still could not be checked without the Environment Templates. Every mistake in a `required: true`
entry is caught at Job creation with an error that names the entry, and a validator given the Environment Templates, as
`openjd run` is, catches them before submission.

### Values fixed per Step

Once a Session enters an Environment, the Environment serves every Task the Session runs. Values that varied per Task
would force one Session per Task, and Tasks that need different software belong in different Steps. Values fixed per
Step are known at Job creation, so tooling can display them and Steps with equal values can still share Sessions.

### Sessions that serve several Steps

Sessions may already run Tasks of several Steps whose Environments are identical. Requiring the Steps' values to match
too is all that keeps `Env.Param.*` to one meaning for as long as an Environment is entered. The rule is checked as a
Step's Tasks are added, so a scheduler that adds Tasks of a newly ready Step to a running Session can keep doing so.

Values compare as typed and before path mapping, so that hosts with different mapping rules agree, and so that an INT
written `1` equals one written `"1"`.

### `Step.Name` in values

`Step.Name` and the Step's `let` bindings are available everywhere else in a Step that is resolved at Job creation, and
a binding is how a Step uses one value both in an entry and in its script. A value that uses `Step.Name` differs per
Step, which suits values such as a cache key but prevents sharing Sessions.

### `Job.EnvNames`

A template sometimes needs to know which Environments the Job has, for example to supply a value only when a particular
Environment is attached. A list of names answers that, and `EXPR` can already test it with `in`. It is in the `Job.*`
scope because it is a property of the Job, and it is concrete at Job creation, as `Job.Name` is. It lists every
Environment whatever its `activation`, because its purpose is to show what can be requested, and omits Step
Environments, which no Step can request.

### `enableIf` on the entry

An entry's *enableIf* lets a Step make a request conditional, for example on a Job Parameter. Declining a `BY_DEFAULT`
Environment lets a Step avoid one it has nothing to ask of, and an `ALWAYS` Environment exists so that no Step can.

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

### Path values use the submission path format

Path mapping rules are keyed on the submitter's path format, and "absolute" depends on the format. Interpreting every
path value in that format is what lets it be mapped. A literal path is portable only between submitters on one
operating system, and a host-local path owned by the Environment Template is better a STRING.

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

A parameter without a `default` makes each Step that enters the Environment say what it wants, which suits a Job
Environment like `RenderLicense`. In an `ALWAYS` or `BY_DEFAULT` Environment Template it would break every Job Template
that does not know the parameter, so the choice is the Environment Template author's, who normally gives a default or
uses `ON_REQUEST`.

### `required: false` is an error on a Job Environment entry

A Job Environment is always present, so `required: false` on its entry can only be a mistake, most likely an entry
meant for an external Environment whose name collides with a Job Environment.

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
submitter-controlled input differ per Step. An Environment Template owner who does not want submitters to choose, for
example, arbitrary container images restricts the parameter with `allowedValues`, which a scheduler checks at Job
creation before any Worker Host runs anything.

Environment Template authors must still treat `Env.Param.*` as untrusted input in their scripts, as they should treat
`Param.*` today: the values are chosen by whoever submits the Job, which on a shared system is not the Environment
Template's author.

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
* **Slurm and Environment Modules** — A batch script runs `module load colmap/3.11` per job step, or `srun
  --container-image=...` (with Pyxis/Enroot) per step. The selection lives in the script text, so no tool can see which
  software a step needs without parsing shell, which the [Tooling parseable](../wiki/Design-Tenets.md) tenet asks OpenJD
  to avoid.

## Implementation Impact

- **Rust (openjd-rs)**: `openjd-model` gains the new `<Environment>` fields, including `exclusiveGroup`, the
  `environment:` and `step:` forms of `StepDependency`, `Job.EnvNames`, and the `Env.Param.*` and `Env.RawParam.*`
  scopes, reusing the existing parameter-definition and host-requirement types. Job creation computes each Step's
  Environment set (applying each `exclusiveGroup` after the Environments' *enableIf*), effective values, and combined
  host requirements, in the order §7.4.1 gives, and stores them on the Job's Steps. `openjd-sessions` takes the
  effective values when it enters an Environment, as it takes Job Parameter values today, and `openjd run` passes the
  values of the Step being run.
- **Python (openjd-model, openjd-sessions)**: The same changes in the pydantic models and the session's symbol table. As
  RFC 0009 notes, the Python packages are intended to become bindings over openjd-rs, in which case they inherit the
  feature.
- **Schedulers**: Store each Step's Environment set, effective values, and combined host requirements, which the Job
  carries, and pass the values to the Worker when a Session enters each Environment. Place Sessions by the combined host
  requirements, which have the shape of a Step's. A scheduler that shares Sessions across Steps must also compare their
  effective values ([How Jobs Are Run](../wiki/How-Jobs-Are-Run.md#environment-parameters)); one that never shares a
  Session across Steps needs no grouping change. Using the values for host affinity is an optional optimization.
- **Conformance tests**: The PR includes a conformance suite under `conformance-tests/2023-09/ENV_PARAMS`, whose README
  maps each row of the [Validation](#validation) table to the tests that cover it.

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

### `activation` as a list of Session kinds

Its vocabulary would grow with each kind of Session, and each of its useful combinations (`[TASK]` for Steps only,
`[SERVICE]` for Services only) is one `ON_REQUEST` Environment that the right entities request.

### `activation` on the entry instead of the Environment

A Step could write `environment: Conda, exclusive: true` to mean "enter this for me and not for Steps that do not ask".
Rejected because whether an Environment is opt-in is a property of the Environment, decided by its author: an auditing
Environment must not become opt-in because one Step's entry says so, and two Steps could disagree.

## Open Questions

Question 3 should be settled before acceptance. The others do not block it.

1. **Standard names for external Environments.** The portability of a Job Template that writes `environment: Conda`
   depends on Environment Templates naming their Conda Environment `Conda` and its input `Packages`, and on their
   sharing one `exclusiveGroup`. [Recommended names](#recommended-names-non-normative) proposes a table, which the
   samples follow. Whether it should become a wiki conventions page on acceptance, and which further Environments it
   should cover, is open.
2. **Interaction with `WRAP_ACTIONS` beyond the wrapper's own values.** A wrapping Environment reads its own parameters
   (the image to run) but not those of the Environments it wraps. No use case for the latter is known;
   `WrappedEnv.Param.*` is listed under [Future Work](#future-work).
3. **The extension name.** `ENV_PARAMS` covers more than parameters: it also gates `activation`, `enableIf` on
   Environments and entries, an Environment's `hostRequirements`, and the `step:` form of `<StepDependency>`. It is the
   extension under which a Step requests an Environment. The name is kept for continuity with the discussion thread, and
   a reviewer may prefer one that names the request. An extension name is permanent once implementations ship it, so
   this should be settled during the final comment period.
4. **`enableIf` on `<Environment>` and RFC 0011.** This RFC defines *enableIf* on every `<Environment>`, decided at Job
   creation, which RFC 0011 (`CONTROL_FLOW`) also defines in its current draft. If this RFC is accepted first, RFC 0011
   should drop its definition and extend this one with what needs its own stages, such as a Step Environment's
   *enableIf* reading `Steps.*`.

## Future Work

* **`WrappedEnv.Param.*` for wrap hooks**, so a wrapping Environment can read the effective values of the inner
  Environment whose action it wraps.
* **Matching external Environments by a standard kind** (see [Rejected
  Ideas](#matching-external-environments-by-something-other-than-name)).
* **A Job-level default for a whole `environment:` entry**, so a Job Template can set a value once for all its Steps
  without a Job Parameter.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is
more permissive.
