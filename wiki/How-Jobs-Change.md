# How Jobs Change

A **Job** is built from a **Job Template** and a set of **Job Parameter** values (see
[How Jobs Are Constructed](How-Jobs-Are-Constructed)). Change the template, or change a value, and the Job built from
it changes too. This page walks through what each kind of change does to a Job: which **Steps** change, which **Tasks**
are kept, added, removed or replaced, what a **Worker Host** sees, and which changes affect only the template.

Open Job Description does not define how a render management system updates a Job that is already running. This page
describes the difference between two Jobs, which any such system has to work out first.

The examples use `openjd diff`, the [openjd-rs](https://github.com/OpenJobDescription/openjd-rs) command that compares
two Jobs built from templates. It is marked unstable, so its flags and output may change. Each output on this page was
printed by it.

## The rules

These are the rules the examples below follow. Each links to the section that shows it.

- **Steps are matched by name.** A Step with the same name in both Jobs is the same Step. Renaming a Step removes it
  and adds a new one, and its Tasks are not kept ([§7](#7-steps)).
- **A Task is identified by its Task parameter values**, such as `Frame=7, Eye=left`. A Task with the same values in
  both Jobs is the same Task, so a system can keep its state. A Task in only one Job is added or removed
  ([§1](#1-changing-a-parameter-value), [§2](#2-changing-the-template-and-its-parameters)).
- **Adding or removing a Task parameter replaces every Task of the Step**, even when no argument reads it: every
  Task's values change, so no Task matches ([§4](#4-when-tasks-cant-be-kept)).
- **Some Steps can't match Tasks one to one.** When a Step's Tasks are chunked (`CHUNK[INT]`) or combined by
  association (`combination: "(A, B)"`), a change to its parameter space replaces every Task
  ([§4](#4-when-tasks-cant-be-kept)).
- **A Step's Tasks have no order.** The [Template Schemas](2023-09-Template-Schemas#34-stepparameterspacedefinition) map a Step to a set of Tasks. When only the order
  of the Task parameter definitions changes, `openjd diff` reports that the order of the Tasks changed. Whether that
  matters, and whether to keep or replace the Tasks, is for the system applying the change to decide
  ([§4](#4-when-tasks-cant-be-kept)).
- **A change reaches only what reads it.** A parameter change affects the Job name, the Steps and the Environments
  whose resolved values read the parameter. A Step's Tasks change only when its parameter space reads it
  ([§5](#5-what-a-worker-host-sees)).
- **Some changes are only in the template**, such as a description or a `let` binding that nothing reads. The Job built
  from it is the same ([§6](#6-changes-only-the-template-shows)).
- **A dependency belongs to the dependent Step.** Making `B` depend on `A` changes `B` only
  ([§7](#7-steps)).

The examples run `openjd diff` on one template under two sets of parameter values, or on an old and a new template.
Its flags and output format are described in the openjd-rs [`diff` specification](https://github.com/OpenJobDescription/openjd-rs/blob/main/specs/cli/diff.md).

## 1. Changing a parameter value

The template stays the same. Only the frame range changes.

`frames.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
parameterDefinitions:
  - {name: Frames, type: STRING, default: "1-100"}
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
    script: {actions: {onRun: {command: render, args: ["{{Task.Param.Frame}}"]}}}
```

**More frames.** The 100 Tasks the old Job has are kept, and 100 Tasks are added.

```console
$ openjd diff frames.yaml --old-parameter Frames=1-100 --new-parameter Frames=1-200 --plan
frames.yaml: old parameters -> new parameters
~ parameter Frames: 1-100 -> 1-200  [parameters]
~ step Render
    ~ Frame: 1-100 -> 1-200  [parameters]
    tasks: 100 -> 200
      keep   100   Frame 1-100
      add    100   Frame 101-200

1 step changed. Tasks: 100 kept, 100 added, 0 removed.

apply plan:
  1. parameter modify Frames  [ParameterValue]
  2. tasks of Render: keep 100, add 100, remove 0  [TaskAppend]
kinds: ParameterValue, TaskAppend
```

**Fewer frames.** Tasks 51 to 100 are removed. A system that refuses to remove work it already did can refuse the
`TaskRemove` kind.

```console
$ openjd diff frames.yaml --old-parameter Frames=1-100 --new-parameter Frames=1-50 --plan
frames.yaml: old parameters -> new parameters
~ parameter Frames: 1-100 -> 1-50  [parameters]
~ step Render
    ~ Frame: 1-100 -> 1-50  [parameters]
    tasks: 100 -> 50
      keep   50    Frame 1-50
      remove 50    Frame 51-100

1 step changed. Tasks: 50 kept, 0 added, 50 removed.

apply plan:
  1. parameter modify Frames  [ParameterValue]
  2. tasks of Render: keep 50, add 0, remove 50  [TaskRemove]
kinds: ParameterValue, TaskRemove
```

**No change.** With `--exit-code`, the command exits with 0 when the Jobs are the same and 4 when they differ.

```console
$ openjd diff frames.yaml -p Frames=1-100 --exit-code
frames.yaml: old parameters -> new parameters
no changes
$ echo $?
0
```

## 2. Changing the template and its parameters

`render_v2.yaml` adds a second `Eye` value, and the new side also renders frames 101 to 200. Each line says what caused
it: the `Eye` change comes from the template, and the `Frames` change from the parameters. The Task change combines
both, and keeps the 100 Tasks the two Jobs share.

`render_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Render
parameterDefinitions:
  - {name: Frames, type: STRING, default: "1-100"}
  - {name: Scene, type: PATH}
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
        - {name: Eye, type: STRING, range: [left]}
    script:
      actions:
        onRun:
          command: render
          args: ["{{Param.Scene}}", "{{Task.Param.Frame}}", "{{Task.Param.Eye}}"]
```

`render_v2.yaml` changes this from `render_v1.yaml`:

```diff
-        - {name: Eye, type: STRING, range: [left]}
+        - {name: Eye, type: STRING, range: [left, right]}
```

```console
$ openjd diff render_v1.yaml render_v2.yaml -p Scene=//srv/shot010.blend --old-parameter Frames=1-100 --new-parameter Frames=1-200 --plan
render_v1.yaml -> render_v2.yaml
~ parameter Frames: 1-100 -> 1-200  [parameters]
~ step Render
    ~ Frame: 1-100 -> 1-200  [parameters]
    ~ Eye: [left] -> [left, right]  [template]
    tasks: 100 -> 400
      keep   100   Frame 1-100 × Eye left
      add    200   Frame 101-200 × Eye left, right
      add    100   Frame 1-100 × Eye right

1 step changed. Tasks: 100 kept, 300 added, 0 removed.

apply plan:
  1. parameter modify Frames  [ParameterValue]
  2. tasks of Render: keep 100, add 300, remove 0  [TaskAppend]
kinds: ParameterValue, TaskAppend
```

**One change, two causes.** Here the template appends frame 50 to the range, and the new parameters extend `Frames`.
The range change is tagged `[both]`.

`origin_both_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
parameterDefinitions:
  - {name: Frames, type: STRING, default: "1-10"}
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
    script: {actions: {onRun: {command: render, args: ["{{Task.Param.Frame}}"]}}}
```

`origin_both_v2.yaml` changes this from `origin_both_v1.yaml`:

```diff
-        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
+        - {name: Frame, type: INT, range: "{{Param.Frames}},50"}
```

```console
$ openjd diff origin_both_v1.yaml origin_both_v2.yaml --new-parameter Frames=1-20
origin_both_v1.yaml -> origin_both_v2.yaml
~ parameter Frames: 1-10 -> 1-20  [parameters]
~ step Render
    ~ Frame: 1-10 -> 1-20,50  [both]
    tasks: 10 -> 21
      keep   10    Frame 1-10
      add    11    Frame 11-20,50

1 step changed. Tasks: 10 kept, 11 added, 0 removed.
```

## 3. Two different templates

`shot_v2.yaml` renames the Job, adds a `Codec` parameter, adds `--denoise` to the render command, and adds an `Encode`
Step that depends on `Render`. `params.json` gives both sides their values, and `new_params.yaml` raises `Frames` on the
new side.

`shot_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Shot 42
parameterDefinitions:
  - {name: Frames, type: STRING, default: "1-100"}
  - {name: Scene, type: PATH}
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
    script:
      actions:
        onRun:
          command: render
          args: ["{{Param.Scene}}", "--frame", "{{Task.Param.Frame}}"]
```

`shot_v2.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Shot 42 (final)
parameterDefinitions:
  - {name: Frames, type: STRING, default: "1-100"}
  - {name: Scene, type: PATH}
  - {name: Codec, type: STRING, default: h264}
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "{{Param.Frames}}"}
    script:
      actions:
        onRun:
          command: render
          args: ["{{Param.Scene}}", "--frame", "{{Task.Param.Frame}}", "--denoise"]
  - name: Encode
    dependencies:
      - dependsOn: Render
    script:
      actions:
        onRun:
          command: encode
          args: ["--frames", "{{Param.Frames}}", "--codec", "{{Param.Codec}}"]
```

`params.json`:

```json
{"Frames": "1-100", "Scene": "//srv/shot042.blend"}
```

`new_params.yaml`:

```yaml
Frames: "1-150"
```

The plan writes the Job and its parameters first, then the changed Step and its new Tasks, then the new Step.

```console
$ openjd diff shot_v1.yaml shot_v2.yaml -p file://params.json --new-parameter file://new_params.yaml --plan
shot_v1.yaml -> shot_v2.yaml
~ name: Shot 42 -> Shot 42 (final)  [template]
+ parameter Codec: h264, defined as {default: h264, type: STRING}  [template]
~ parameter Frames: 1-100 -> 1-150  [parameters]
~ step Render
    ~ Frame: 1-100 -> 1-150  [parameters]
    ~ script.onRun.args: [{{Param.Scene}}, --frame, {{Task.Param.Frame}}] -> [{{Param.Scene}}, --frame, {{Task.Param.Frame}}, --denoise]  [template]
    tasks: 100 -> 150
      keep   100   Frame 1-100
      add    50    Frame 101-150
+ step Encode
    tasks: 1 added

1 step changed, 1 added. Tasks: 100 kept, 51 added, 0 removed.

apply plan:
  1. job modify  [JobMetadata]
  2. parameter modify Frames  [ParameterValue]
  3. parameter add Codec  [ParameterAdd]
  4. step modify Render  [StepScript]
  5. tasks of Render: keep 100, add 50, remove 0  [TaskAppend]
  6. step add Encode  [StepAdd]
  7. tasks of Encode: all  [TaskAppend]
kinds: JobMetadata, ParameterValue, ParameterAdd, StepScript, StepAdd, TaskAppend
```

**A `null` value.** The new side's `Frames` is not given, so it takes its default, `1-100`. The old side rendered 200
frames, so 100 Tasks are removed. `--stat` prints one line per Step.

```console
$ openjd diff shot_v1.yaml shot_v2.yaml -p file://params.json --old-parameter Frames=1-200 --new-parameter '{"Frames": null}' --stat
shot_v1.yaml -> shot_v2.yaml
~ Render  tasks 200 -> 100  (+0 -100)
+ Encode  tasks 0 -> 1  (+1 -0)
1 step changed, 1 added. Tasks: 100 kept, 1 added, 100 removed.
```

## 4. When Tasks can't be kept

A Task is identified by its Task parameter values, such as `Frame=7, Eye=left`. When a change keeps those values, the
Task is kept. When it changes them, no Task matches, and every Task of the Step is replaced.

**A new Task parameter.** No argument reads `Eye`, but each Task now has a value for it. No Task matches.

`new_dimension_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "1-10"}
    script: {actions: {onRun: {command: render, args: ["{{Task.Param.Frame}}"]}}}
```

`new_dimension_v2.yaml` changes this from `new_dimension_v1.yaml`:

```diff
+        - {name: Eye, type: STRING, range: [left, right]}
```

```console
$ openjd diff new_dimension_v1.yaml new_dimension_v2.yaml --plan
new_dimension_v1.yaml -> new_dimension_v2.yaml
~ step Render
    + Eye: [left, right]  [template]
    tasks: 10 -> 20, all replaced (task parameter added or removed)

1 step changed. Tasks: 0 kept, 0 added, 0 removed, 20 replaced.

apply plan:
  1. tasks of Render: replace all  [TaskReplace]
kinds: TaskReplace
```

**Task parameters in a different order.** The same six Tasks exist in both Jobs, listed in a different order.
`openjd diff` reports the order change as a replacement of every Task. A Step's Tasks have no order in the
specification, so a system that doesn't depend on the order can keep these Tasks instead: the diff reports what
changed, and the system applying it decides.

`dimension_order_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "1-3"}
        - {name: Eye, type: STRING, range: [left, right]}
    script: {actions: {onRun: {command: render, args: ["{{Task.Param.Frame}}", "{{Task.Param.Eye}}"]}}}
```

`dimension_order_v2.yaml` changes this from `dimension_order_v1.yaml`:

```diff
+        - {name: Eye, type: STRING, range: [left, right]}
-        - {name: Eye, type: STRING, range: [left, right]}
```

```console
$ openjd diff dimension_order_v1.yaml dimension_order_v2.yaml --plan
dimension_order_v1.yaml -> dimension_order_v2.yaml
~ step Render
    ~ parameterSpace.taskParameterDefinitions.order: [Frame, Eye] -> [Eye, Frame]  [template]
    tasks: 6 -> 6, all replaced (task parameter definition order changed, so task order changed)

1 step changed. Tasks: 0 kept, 0 added, 0 removed, 6 replaced.

apply plan:
  1. tasks of Render: replace all  [TaskReplace]
kinds: TaskReplace
```

**A different chunk size.** With the `TASK_CHUNKING` extension, a Task covers a chunk of frames. Chunks of 5 and chunks
of 10 cover different frames, so no chunk matches.

`chunk_size_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
extensions: [TASK_CHUNKING]
name: Demo
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: "CHUNK[INT]", range: "1-20", chunks: {defaultTaskCount: 5, rangeConstraint: CONTIGUOUS}}
    script: {actions: {onRun: {command: render, args: ["{{Task.Param.Frame}}"]}}}
```

`chunk_size_v2.yaml` changes this from `chunk_size_v1.yaml`:

```diff
-        - {name: Frame, type: "CHUNK[INT]", range: "1-20", chunks: {defaultTaskCount: 5, rangeConstraint: CONTIGUOUS}}
+        - {name: Frame, type: "CHUNK[INT]", range: "1-20", chunks: {defaultTaskCount: 10, rangeConstraint: CONTIGUOUS}}
```

```console
$ openjd diff chunk_size_v1.yaml chunk_size_v2.yaml --plan
chunk_size_v1.yaml -> chunk_size_v2.yaml
~ step Render
    ~ Frame: 1-20 chunks of 5 -> 1-20 chunks of 10  [template]
    tasks: 4 -> 2, all replaced (not an exact plain product: association, chunking, a repeated range value or name, or a task count overflow)

1 step changed. Tasks: 0 kept, 0 added, 0 removed, 2 replaced.

apply plan:
  1. tasks of Render: replace all  [TaskReplace]
kinds: TaskReplace
```

## 5. What a Worker Host sees

A Step's script keeps its format strings, such as `{{Param.Scene}}`, until a Worker Host runs it (see
[How Jobs Are Run](How-Jobs-Are-Run)). With the `EXPR` extension, each Step and Job Environment carries the values of
the symbols it reads, resolved when the Job is created ([Expression Language](2026-02-Expression-Language)).
`openjd diff` compares those values, shown as `resolvedSymTab`. A parameter change then marks exactly the Steps and
Environments that read the parameter.

`shot_expr.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
extensions: [EXPR]
name: "Shot {{Param.Shot}}"
parameterDefinitions:
  - {name: Shot, type: STRING, default: "010"}
  - {name: Count, type: INT, default: 10}
  - {name: Quality, type: INT, default: 2}
jobEnvironments:
  - name: Setup
    variables:
      SHOT_LABEL: "shot-{{Param.Shot}}"
steps:
  - name: Render
    let:
      - last = Param.Count * 10
      - samples = Param.Quality * 64
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "1-{{last}}"}
    script:
      actions:
        onRun:
          command: render
          args: ["--frame", "{{Task.Param.Frame}}", "--samples", "{{samples}}"]
  - name: Encode
    dependencies:
      - dependsOn: Render
    script:
      actions:
        onRun:
          command: encode
          args: ["--shot", "{{Param.Shot}}"]
```

**A parameter that the Job name, a Job Environment and one Step read.** `Render` doesn't read `Shot`, and it is
unchanged.

```console
$ openjd diff shot_expr.yaml --old-parameter Shot=010 --new-parameter Shot=020 --plan
shot_expr.yaml: old parameters -> new parameters
~ name: Shot 010 -> Shot 020  [parameters]
~ jobEnvironments[Setup].resolvedSymTab: Param.Shot=010 -> Param.Shot=020  [parameters]
~ parameter Shot: 010 -> 020  [parameters]
~ step Encode
    ~ resolvedSymTab: Param.Shot=010 -> Param.Shot=020  [parameters]
    tasks: 1 unchanged

1 step changed. Tasks: 101 kept, 0 added, 0 removed.

apply plan:
  1. job modify  [JobMetadata]
  2. parameter modify Shot  [ParameterValue]
  3. job environment modify Setup  [EnvSymbols]
  4. step modify Encode  [StepSymbols]
kinds: JobMetadata, ParameterValue, EnvSymbols, StepSymbols
```

**A parameter that a `let` binding reads.** The binding's value is part of what the Worker Host sees, so `samples`
changes from 128 to 192. The Tasks don't change, because the frame range doesn't read `Quality`.

```console
$ openjd diff shot_expr.yaml --old-parameter Quality=2 --new-parameter Quality=3 --plan
shot_expr.yaml: old parameters -> new parameters
~ parameter Quality: 2 -> 3  [parameters]
~ step Render
    ~ resolvedSymTab: Param.Count=10, Param.Quality=2, samples=128 -> Param.Count=10, Param.Quality=3, samples=192  [parameters]
    tasks: 100 unchanged

1 step changed. Tasks: 101 kept, 0 added, 0 removed.

apply plan:
  1. parameter modify Quality  [ParameterValue]
  2. step modify Render  [StepSymbols]
kinds: ParameterValue, StepSymbols
```

**A change to an argument a Worker Host resolves.** `{{Task.Param.Frame}}` is resolved on the Worker Host for each
Task. The Tasks stay the same, and only the script changes. Tasks that already ran used the old script.

`runtime_task_param_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - {name: Frame, type: INT, range: "1-3"}
    script: {actions: {onRun: {command: render, args: ["frame-{{Task.Param.Frame}}"]}}}
```

`runtime_task_param_v2.yaml` changes this from `runtime_task_param_v1.yaml`:

```diff
-    script: {actions: {onRun: {command: render, args: ["frame-{{Task.Param.Frame}}"]}}}
+    script: {actions: {onRun: {command: render, args: ["--frame", "{{Task.Param.Frame}}"]}}}
```

```console
$ openjd diff runtime_task_param_v1.yaml runtime_task_param_v2.yaml --plan
runtime_task_param_v1.yaml -> runtime_task_param_v2.yaml
~ step Render
    ~ script.onRun.args: [frame-{{Task.Param.Frame}}] -> [--frame, {{Task.Param.Frame}}]  [template]
    tasks: 3 unchanged

1 step changed. Tasks: 3 kept, 0 added, 0 removed.

apply plan:
  1. step modify Render  [StepScript]
kinds: StepScript
```

## 6. Changes only the template shows

Some changes are in the template but not in the Job built from it. The plan has nothing to apply.

**A `let` binding that nothing reads.**

`let_step_unused_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
extensions: [EXPR]
name: Demo
steps:
  - name: Render
    let: ["unused = 1"]
    script: {actions: {onRun: {command: render}}}
```

`let_step_unused_v2.yaml` changes this from `let_step_unused_v1.yaml`:

```diff
-    let: ["unused = 1"]
+    let: ["unused = 2"]
```

```console
$ openjd diff let_step_unused_v1.yaml let_step_unused_v2.yaml --plan
let_step_unused_v1.yaml -> let_step_unused_v2.yaml
~ step Render
    ~ let: [unused = 1] -> [unused = 2]  [template]
    tasks: 1 unchanged

1 step changed. Tasks: 1 kept, 0 added, 0 removed.

apply plan:
  nothing to apply
kinds: none
```

**A parameter's description.**

`param_description_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
parameterDefinitions:
  - {name: Quality, type: STRING, default: low, description: first cut}
steps:
  - name: Render
    script: {actions: {onRun: {command: render}}}
```

`param_description_v2.yaml` changes this from `param_description_v1.yaml`:

```diff
-  - {name: Quality, type: STRING, default: low, description: first cut}
+  - {name: Quality, type: STRING, default: low, description: final}
```

```console
$ openjd diff param_description_v1.yaml param_description_v2.yaml --plan
param_description_v1.yaml -> param_description_v2.yaml
~ parameter definition Quality.description: first cut -> final  [template]

0 steps changed. Tasks: 1 kept, 0 added, 0 removed.

apply plan:
  nothing to apply
kinds: none
```

## 7. Steps

Steps are matched by name, so renaming a Step removes it and adds a new one. Its Tasks are not kept.

`step_renamed_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
steps:
  - name: Render
    script: {actions: {onRun: {command: render}}}
```

`step_renamed_v2.yaml` changes this from `step_renamed_v1.yaml`:

```diff
-  - name: Render
+  - name: Beauty
```

```console
$ openjd diff step_renamed_v1.yaml step_renamed_v2.yaml --plan
step_renamed_v1.yaml -> step_renamed_v2.yaml
- step Render
    tasks: 1 removed
+ step Beauty
    tasks: 1 added

0 steps changed, 1 added, 1 removed. Tasks: 0 kept, 1 added, 1 removed.

apply plan:
  1. step add Beauty  [StepAdd]
  2. tasks of Beauty: all  [TaskAppend]
  3. step remove Render  [StepRemove]
kinds: StepAdd, StepRemove, TaskAppend
```

**A new dependency.** `Composite` now waits for `Render`. Its Tasks don't change.

`step_dependencies_v1.yaml`:

```yaml
specificationVersion: jobtemplate-2023-09
name: Demo
steps:
  - name: Render
    script: {actions: {onRun: {command: render}}}
  - name: Composite
    script: {actions: {onRun: {command: comp}}}
```

`step_dependencies_v2.yaml` changes this from `step_dependencies_v1.yaml`:

```diff
+    dependencies: [{dependsOn: Render}]
```

```console
$ openjd diff step_dependencies_v1.yaml step_dependencies_v2.yaml --plan
step_dependencies_v1.yaml -> step_dependencies_v2.yaml
~ step Composite
    ~ dependencies: [] -> [Render]  [template]
    tasks: 1 unchanged

1 step changed. Tasks: 2 kept, 0 added, 0 removed.

apply plan:
  1. step modify Composite  [StepDependencies]
kinds: StepDependencies
```

## 8. Conditional Steps

This section describes Steps with an `enableIf` field, which
[RFC 0010](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md) defines for
Environments and [RFC 0011, Control Flow](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0011-control-flow.md) puts on
Steps. `openjd diff` doesn't support the field yet, so this section has no output. It describes how a change to a
conditional Step is expected to look.

RFC 0011 says that "A statically disabled Step is still part of the Job and is shown as `SKIPPED`, so every Job created
from a template has the same Steps, whatever its parameter values." That keeps Steps matched by name when a parameter
turns a Step on or off:

```yaml
parameterDefinitions:
  - {name: EncodeVideo, type: BOOL, default: false}
steps:
  - name: Encode
    enableIf: "Param.EncodeVideo"
    ...
```

| change | what happens to the Step | to its Tasks |
|---|---|---|
| `EncodeVideo` false to true | enabled | every Task of the Step is added, as for a new Step |
| `EncodeVideo` true to false | disabled (`SKIPPED`) | every Task is removed; Steps that read its outputs get `null` |
| the `enableIf` text changes but gives the same result | none; only the template shows it | none |
| an `enableIf` that reads another Step's output (`Steps.<Name>.Output.*`) | decided after the Job is created, at RFC 0011's step input binding, so two Jobs can't be compared on it until both are bound | unknown until then |

Not yet decided:
- What disabling a Step means for Tasks that already ran, and for Steps that already read its outputs.
- Whether a system that updates a Job evaluates a changed late-bound `enableIf` with the outputs it already stores.

## More examples

openjd-rs has a short set of [`openjd diff` examples](https://github.com/OpenJobDescription/openjd-rs/blob/main/crates/openjd-cli/examples/diff/README.md)
with their templates, and its test suite has one case for each field `openjd diff` can report, with each command
and its output: [`specs/cli/diff-cases.md`](https://github.com/OpenJobDescription/openjd-rs/blob/main/specs/cli/diff-cases.md).
