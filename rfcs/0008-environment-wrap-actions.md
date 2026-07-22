---

* Feature Name: Environment Wrap Actions
* Author(s): David Leong <[leongdl](https://github.com/leongdl)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/132
* Start Date: 2026-04-16
* Specification Version: 2023-09 extension WRAP_ACTIONS
* Accepted On: (pending)
* Depends On:
  * RFC 0002, Model Extensions (https://github.com/OpenJobDescription/openjd-specifications/issues/57)
  * RFC 0005, Expression Language (https://github.com/OpenJobDescription/openjd-specifications/pull/93)
  * RFC 0006, Expression Function Library (https://github.com/OpenJobDescription/openjd-specifications/pull/104)

## Summary

This RFC proposes extending `<Environment>` with three new session actions
(`onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit`) that let an environment
template intercept and wrap the lifecycle actions of *inner* environments
and tasks. The
runtime supplies each wrap action with the wrapped action's fields (command, args,
timeout, environment) via template variables.

The RFC defines a general-purpose wrapping mechanism. Container execution is the
motivating use case and the focus of the examples, but the same mechanic supports
remote execution, session-wide instrumentation, privilege shifts, and any other form
of redirecting *how* an action runs without modifying the action itself.

## Basic Example

This environment template runs inner environments and tasks inside a Docker
container. The container starts once in `onEnter`, every inner action is forwarded
into the container via the three wrap hooks, and the container stops in `onExit`.
The example is intentionally short. A production-ready version with registry
authentication, image pull policies, and bind-mount parity, along with
Apptainer, dry-run, SSH, and profiling variants, is checked in as conformance-test
fixtures in future examples.

```yaml
specificationVersion: "environment-2023-09"
extensions:
  - WRAP_ACTIONS
  - EXPR
parameterDefinitions:
  - name: ContainerImage
    type: STRING
    default: "ubuntu:latest"

environment:
  name: Docker
  script:
    actions:
      onEnter:
        command: bash
        args: ["{{Env.File.Enter}}"]
      onWrapEnvEnter:
        command: bash
        args: ["{{Env.File.Wrap}}"]
      onWrapTaskRun:
        command: bash
        args: ["{{Env.File.Wrap}}"]
      onWrapEnvExit:
        command: bash
        args: ["{{Env.File.Wrap}}"]
      onExit:
        command: bash
        args: ["{{Env.File.Exit}}"]

    embeddedFiles:
      - name: Enter
        filename: enter.sh
        type: TEXT
        data: |
          #!/usr/bin/env bash
          set -euo pipefail
          DOCKER_CONTAINER_ID=$(docker container run --rm --detach \
              --mount {{ repr_sh("type=bind,src=" + Session.WorkingDirectory + ",dst=" + Session.WorkingDirectory) }} \
              {{ repr_sh(Param.ContainerImage) }} \
              bash -c 'sleep infinity')
          echo "openjd_env: DOCKER_CONTAINER_ID=$DOCKER_CONTAINER_ID"

      # Shared wrap script for all three hooks: repr_sh() produces safely
      # quoted argv tokens for every wrapped field.
      - name: Wrap
        filename: wrap.sh
        type: TEXT
        data: |
          #!/usr/bin/env bash
          set -euo pipefail
          docker container exec \
              "$DOCKER_CONTAINER_ID" \
              {{ repr_sh(flatten([['-e', e] for e in WrappedAction.Environment])) }} \
              {{ repr_sh(WrappedAction.Command) }} \
              {{ repr_sh(WrappedAction.Args) }}

      - name: Exit
        filename: exit.sh
        type: TEXT
        data: |
          #!/usr/bin/env bash
          set -euo pipefail
          docker container stop --timeout 30 "$DOCKER_CONTAINER_ID"
```

The wrap hooks declare no `timeout`, so each inherits the default for its hook
position (see [Timeout behavior](#timeout-behavior)). With the `FEATURE_BUNDLE_1`
extension a hook may instead forward the wrapped action's timeout as its own
via `timeout: "{{WrappedAction.Timeout}}"` — the variable is `int?`, so a
declared timeout forwards verbatim and a `null` (no timeout on the wrapped
action) drops the field, keeping the hook default. This example enforces the
wrapped action's timeout from inside the wrap script instead (see
[Timeout behavior](#timeout-behavior)).

The job template that runs under this wrapping environment is unchanged from one
that runs without wrapping. See the existing
[samples repository](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples/job_templates)
for portable job templates.

### Execution order with a wrapping environment

For a session with a wrapping Docker environment `A` and a non-wrapping inner
environment `B`, execution proceeds:

```
A.onEnter                            (wrapping env's own onEnter is never wrapped)
  B.onEnter                          (via A.onWrapEnvEnter)
    Task 1: onRun                    (via A.onWrapTaskRun)
    Task 2: onRun                    (via A.onWrapTaskRun)
  B.onExit                           (via A.onWrapEnvExit)
A.onExit                             (wrapping env's own onExit is never wrapped)
```

The wrapping environment is not required to be the outermost. If `B` were the
wrapping environment instead, `A` would run normally and `B` would wrap its
own inner actions and tasks.

When no wrapping environment is present, every action runs normally. The job
template and the inner environments are unchanged.

## Motivation

Environment templates today can prepare the context in which a job runs:
installing software, setting environment variables, starting background daemons.
They cannot change *how* the actions within the session are executed. The existing
[bash-in-docker sample](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples/job_templates/bash-in-docker)
demonstrates a workaround: the step environment starts a container and the task
execs a script inside it. This approach requires the job template to be written
specifically for Docker, and inner step environments cannot install software inside
the container. Swap the environment from Docker to Conda, and the job template
breaks.

The [Design Tenets](https://github.com/OpenJobDescription/openjd-specifications/wiki/Design-Tenets)
call for portability:

Job templates should be portable in a way to run them, unmodified, with either a
Conda, Rez, Docker, or Apptainer environment template that provides the software
environment to run in.

The three wrap hooks close this gap. Two composability properties make the mechanic
work without new coupling:

1. An outer environment template can modify the execution of inner
   environments that it does not know about. The wrap hooks operate on
   whatever `<Action>` fields the inner environment supplies.
2. An inner environment template does not need to know a wrapper exists. The
   same inner template runs unchanged with or without a wrapping environment.

### Use cases

1. **Container execution.** Apply a Docker or Apptainer container as the outer
   environment, and let inner environments install plugins, activate Conda
   environments, or stage dependencies inside it. The job template and the
   inner environments are unchanged when the wrapping environment is swapped
   or removed.

2. **Remote execution.** An environment template can SSH into a remote host, or
   submit actions to a cloud API, via the three wrap hooks. Inner environment setup
   and task runs then execute on the remote host rather than locally.

3. **Session-wide instrumentation.** Wrap every action with profiling, tracing, or
   resource-accounting tools without modifying the job template or inner
   environments. Task-only profiling (which exists via onRun substitution today)
   misses the setup phases that often contain performance issues.

4. **Privilege shifts.** Run inner actions as a different user or with reduced
   capabilities by wrapping the command with `sudo -u`, `unshare`, or similar.

### Backward compatibility

This RFC is additive and gated by the `WRAP_ACTIONS` extension name declared under
RFC 0002. Specifically:

- Schedulers that do not implement `WRAP_ACTIONS` MUST reject templates that list
  it in `extensions:`, per RFC 0002's extension-handling rules.
- The wrap hooks are gated by the `WRAP_ACTIONS` declaration of the environment
  template that *defines* them. An environment template that uses `onWrapEnvEnter`,
  `onWrapTaskRun`, or `onWrapEnvExit` MUST list `WRAP_ACTIONS` in its own
  `extensions:`, and a scheduler MUST reject an environment template that uses the
  hooks without declaring the extension.
- Job templates and inner environment templates do NOT need to list `WRAP_ACTIONS`.
  When a wrapping environment that declares the extension is active in a session, it
  wraps the lifecycle actions of inner environments and the `onRun` of tasks even
  though those inner templates and jobs know nothing about the extension. A classic
  job with no extensions runs unchanged when no wrapping environment is present, and
  has its tasks wrapped when one is.
- No existing field changes meaning; `onEnter` and `onExit` continue to behave as
  they do today when no wrap hook is active.

**`EXPR` is a hard prerequisite of `WRAP_ACTIONS`.** Templates that list
`WRAP_ACTIONS` MUST also list `EXPR` (RFC 0005). Schedulers MUST reject
templates that list `WRAP_ACTIONS` without also listing `EXPR`. The
function library defined in RFC 0006 (including `repr_sh`/`repr_cmd`/
`repr_pwsh` and `flatten`) is part of the same `EXPR` extension, so no
separate extension name is required.

The rationale: safe reconstruction of a wrapped command line from
`WrappedAction.*` requires shell-aware quoting (see
[Security Considerations](#security-considerations)), and `EXPR` plus its
function library is the specification-provided mechanism for that.

## Specification

### Terminology

The following terms are used throughout this specification.

| Term                    | Definition                                                                                                                                               |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Host**                | The OS environment of the worker where the OpenJD session runtime runs and launches actions.                                                             |
| **Session runtime**     | The OpenJD implementation running on the worker that launches actions, scans their stdout for `openjd_*` macros, enforces timeouts, and delivers signals. Distinct from the (cloud-side) scheduler that accepts templates and dispatches sessions. |
| **Wrap hook**           | One of the three new `<EnvironmentActions>` fields: `onWrapEnvEnter`, `onWrapTaskRun`, `onWrapEnvExit`.                                                        |
| **Wrap script**         | The program supplied by a wrap hook's `<Action>`, and the process the session runtime launches to execute it. The wrap script itself runs normally; it chooses what to do with the wrapped action's fields. |
| **Wrapping environment**| The environment that defines wrap hooks. Its own `onEnter` and `onExit` run normally and are never wrapped.                                              |
| **Inner environment**   | Any environment in the session stack that is inner to the wrapping environment. Its lifecycle actions (`onEnter`, `onExit`) are intercepted by wrap hooks. |
| **Wrapped action**      | An inner environment's `onEnter`/`onExit`, or a task's `onRun`, whose execution is intercepted by a wrap hook. The wrap script receives the action's fields via `WrappedAction.*` template variables. |
| **Wrapped process**     | The OS process the wrap script invokes to perform the wrapped action (e.g., `docker container exec ...`, `ssh ...`). A grand-child of the session runtime. |

### Schema modifications

> Changes to [the template schema](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas).

> A modification to [`<EnvironmentActions>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#43-environmentactions)

```diff
  <EnvironmentActions> ::= the object:
    onEnter: <Action>
+   onWrapEnvEnter: <Action>    # @optional @extension WRAP_ACTIONS
+   onWrapTaskRun: <Action>     # @optional @extension WRAP_ACTIONS
+   onWrapEnvExit: <Action>     # @optional @extension WRAP_ACTIONS
    onExit: <Action> # @optional
```

1. *onEnter*: the action to run when entering the environment.
2. *onWrapEnvEnter*: if provided, runs instead of the `onEnter` action of every
   *inner* environment that enters the session while this environment is
   active.
3. *onWrapTaskRun*: if provided, runs instead of the task's `onRun` action
   for every task that runs while this environment is active.
4. *onWrapEnvExit*: if provided, runs instead of the `onExit` action of every
   *inner* environment that exits while this environment is active.
5. *onExit*: the action to run when exiting the environment.

Each wrap hook receives the wrapped action's context via the
`WrappedAction.*` template variables (see
[Template variables](#template-variables)).

**All-or-nothing rule.** An environment that defines any of `onWrapEnvEnter`,
`onWrapTaskRun`, or `onWrapEnvExit` MUST define all three, ensuring execution
context parity across every wrapped lifecycle phase. Schedulers MUST reject
templates that define only a subset of the wrap hooks before the session
begins.

**No changes to `<Action>`.** This RFC does *not* modify the `<Action>` schema. All
changes are additive at the `<EnvironmentActions>` level, and the new template
variables are read-only context supplied to wrap actions by the runtime.

### Wrap ordering with multiple environments

A session MUST have at most one wrapping environment. Schedulers MUST reject
sessions whose stack contains two or more environments that define any wrap
hook, before entering any environment.

A wrapping environment's wrap hooks intercept only the actions of inner
environments and tasks. The wrapping environment's own `onEnter` and `onExit`
are never wrapped.

**Nothing-to-replace rule.** A wrap hook runs only in place of an action the
inner entity actually defines. When an inner environment defines no `onExit`
— or defines no `script` at all (a `variables:`-only environment) — there is
nothing to replace, and the runtime MUST NOT run the corresponding wrap hook
for that environment. A hook is a *replacement*, not a lifecycle
notification: running `onWrapEnvExit` against a nonexistent `onExit` would
execute wrapper teardown logic (for example, a container exec) for an action
that was never going to run, with `WrappedAction.Command`/`Args` having no
meaningful values. Every `<StepScript>` defines `onRun`, so `onWrapTaskRun`
runs for every task.

### Template variables

The following variables are read-only context supplied by the runtime to wrap
actions. They have identical names and semantics across all three hooks, so
helper scripts can be reused unchanged.

**Available in `onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit`:**

| Variable                          | Type           | Description |
|-----------------------------------|----------------|-------------|
| `WrappedAction.Command`           | `string`       | The `command` from the wrapped action. |
| `WrappedAction.Args`              | `list[string]` | The `args` from the wrapped action. |
| `WrappedAction.Environment`       | `list[string]` | Environment variables defined earlier in the session — `openjd_env` exports and environments' declarative `variables:` maps — as `["KEY=value", ...]`. See [Host environment variables and embedded file paths](#host-environment-variables-and-embedded-file-paths). |
| `WrappedAction.Timeout`           | `int?`         | The timeout in seconds specified on the wrapped action. `null` when the wrapped action specifies no timeout — no bound is meaningful in that case. See [Timeout behavior](#timeout-behavior). |
| `WrappedAction.Cancelation.Mode`  | `string?`      | The cancelation method of the wrapped action (`TERMINATE` or `NOTIFY_THEN_TERMINATE`). `null` when the wrapped action defines no `<Cancelation>` — the author declared nothing, so no method name is meaningful. See [Cancelation behavior](#cancelation-behavior). |
| `WrappedAction.Cancelation.NotifyPeriodInSeconds` | `int?` | The effective `notifyPeriodInSeconds` of the wrapped action when its cancelation mode is `NOTIFY_THEN_TERMINATE`, with schema defaults applied when the wrapped action omits the field. `null` when the mode is `TERMINATE` or the wrapped action defines no `<Cancelation>` — a notify period does not apply to those cases, so no numeric value is meaningful. See [Cancelation behavior](#cancelation-behavior). |

**Additionally available in `onWrapEnvEnter` and `onWrapEnvExit`:**

| Variable                          | Type           | Description |
|-----------------------------------|----------------|-------------|
| `WrappedEnv.Name`                 | `string`       | The `name` of the inner environment whose action is being wrapped. |

**Additionally available in `onWrapTaskRun`:**

| Variable                          | Type           | Description |
|-----------------------------------|----------------|-------------|
| `WrappedStep.Name`                | `string`       | The `name` of the step whose task is being wrapped. |

Templates MUST NOT reference `WrappedAction.*` outside the three wrap hooks,
`WrappedEnv.*` outside `onWrapEnvEnter` and `onWrapEnvExit`, or `WrappedStep.*`
outside `onWrapTaskRun`. Schedulers MUST reject templates that violate
this scope rule.

### Host environment variables and embedded file paths

`WrappedAction.Environment` carries only session-defined variables: variables
exported with `openjd_env` and entries of entered environments' declarative
`variables:` maps. Host-inherited variables (`HOME`, `PATH`, `OPENJD_*`,
etc.) and host filesystem paths referenced in `WrappedAction.Command` or
`WrappedAction.Args` (for example, `{{Env.File.X}}` resolves to a host path)
are not surfaced and are the wrap environment's responsibility to forward or
path-map into the wrapped execution context. Failure manifests as
`command not found` or `No such file or directory` from the wrapped
process.

### Forwarding `<Action>` fields, current and future

The `WrappedAction.*` namespace is the single, standardized surface for
every field of the wrapped `<Action>`. The fields listed in
[Template variables](#template-variables) (`Command`, `Args`, `Environment`,
`Timeout`) cover today's `<Action>` schema. When a future specification
adds a field to `<Action>` — for example, the `logMessageTimeout` idea from
[Discussion #118](https://github.com/OpenJobDescription/openjd-specifications/discussions/118)
— it MUST surface under the same namespace using the field's PascalCased
name (e.g., `WrappedAction.LogMessageTimeout`) without modification to this
RFC. New fields gated by an `@extension` activate under this namespace
exactly when that extension is active in the template.

This keeps the contract between the runtime and wrap scripts stable across
schema evolution: a wrap script written today references existing
`WrappedAction.*` fields; a wrap script written for a later spec version
references the same namespace, with new entries available when the
corresponding extension is in use.

Wrap scripts MAY reference any field they recognize and MUST tolerate
fields they do not. A wrapped action that relies on a field whose wrap
script does not propagate it behaves as if the field were absent.

### Modifications to How Jobs Are Run

> Modifications to [How Jobs Are Run](https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Run)

```diff
  Once the Environments have been created and entered for a Session, a series of Tasks are
  run within that Session and the Environments. Tasks from any Step in a Job can run within
  the same Session provided that the set of Environments that are required to run those
  Tasks are identical.

+ If exactly one Environment in the session stack defines the wrap hooks (onWrapEnvEnter,
+ onWrapTaskRun, onWrapEnvExit), then the lifecycle actions of inner Environments and
+ tasks are intercepted:
+
+ - An inner Environment's onEnter is replaced by the wrapping Environment's onWrapEnvEnter.
+ - A task's onRun is replaced by the wrapping Environment's onWrapTaskRun.
+ - An inner Environment's onExit is replaced by the wrapping Environment's onWrapEnvExit.
+
+ The wrapping Environment's own onEnter and onExit are never wrapped; they always run
+ normally. A wrap hook runs only in place of an action the inner Environment defines:
+ if an inner Environment defines no onExit (or defines no script at all), there is
+ nothing to replace and the corresponding wrap hook does not run for it. If more than
+ one Environment in the session stack defines any wrap hook,
+ the session is invalid and the scheduler must reject it before entering any
+ Environment. If an environment defines any wrap hook, it must define all three.
```

### Stdout forwarding and macro propagation

- Wrap scripts MUST forward the wrapped process's stdout and stderr to their
  own stdout and stderr verbatim, without buffering, filtering, or
  transformation. `docker container exec`, `apptainer exec`, and `ssh`
  satisfy this by default; authors of custom wrappers MUST preserve it.
- OpenJD session runtimes MUST scan the wrap script's stdout for OpenJD stdout macros
  (`openjd_env`, `openjd_fail`, `openjd_progress`, `openjd_status`, and any
  future macros) and MUST NOT scan the grand-child's stdout directly. A
  macro emitted by a wrapped process is recognized identically to one
  emitted by the wrap script itself.
- OpenJD session runtimes MUST include in `WrappedAction.Environment` every
  `openjd_env`-defined variable emitted by any earlier action in the same
  session — regardless of whether that action ran normally or via a wrap
  hook — and every entry of each entered environment's declarative
  `variables:` map. This is what makes wrap composition useful: an inner Conda
  environment's `onWrapEnvEnter` can emit
  `openjd_env: CONDA_PREFIX=/opt/conda/env`, and the wrap script for every
  subsequent wrapped task can forward it into the wrapped execution
  context.
- A wrap script MAY emit stdout macros directly. The
  [Basic Example](#basic-example) uses this to publish
  `openjd_env: DOCKER_CONTAINER_ID=...` from `onEnter` for subsequent wrap
  hooks.

This model was chosen over having the runtime scan the wrapped process's stdout directly (which would require locating the grand-child across heterogeneous runtimes) or requiring wrap scripts to re-emit `openjd_env` lines explicitly (which duplicates work the runtime already performs).

### Failure semantics

A wrap hook is treated as the action it replaces. A failed `onWrapEnvEnter` is
an inner `onEnter` failure; a failed `onWrapTaskRun` is a task `onRun`
failure; a failed `onWrapEnvExit` is an inner `onExit` failure. The session
handles each failure exactly as it would in the unwrapped case.

**Exit status propagation.** Wrap scripts MUST propagate the wrapped
process's exit status as their own. Idioms that satisfy this:

- Shell: `set -euo pipefail` with the wrapped command as the last statement,
  or `exec` of the wrapped command in hooks that run exactly one child.
- Programmatic wrappers: return the wrapped process's exit code directly
  (e.g., `sys.exit(proc.returncode)` in Python).

### Lifecycle and cleanup guarantees

OpenJD already guarantees that when a session fails or is canceled, every
environment the session entered (or attempted to enter) has its `onExit` run
before the session terminates (see
[How Jobs Are Run](https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Run)).
Wrap hooks extend this guarantee symmetrically: if `onWrapEnvEnter` starts for
an inner environment, that inner environment's `onWrapEnvExit` MUST run, and
the wrapping environment's own `onExit` MUST run on top of that.

| Scenario                                      | What runs                                                                |
|-----------------------------------------------|--------------------------------------------------------------------------|
| `onWrapEnvEnter` fails for inner env B           | `onWrapEnvExit` for B; wrapping environment's `onExit`.                     |
| `onWrapTaskRun` fails or is canceled          | `onWrapEnvExit` for every inner env entered; wrapping environment's `onExit`. |
| `onWrapEnvExit` fails                            | Wrapping environment's `onExit` still runs.                              |
| Wrapping environment's `onEnter` fails        | Wrapping environment's `onExit` runs (existing OpenJD guarantee).        |

Resources allocated by the wrapping environment's `onEnter` (e.g., the
container) MUST remain available until every `onWrapEnvExit` returns.

### Cancelation behavior

The wrap hook's own `<Cancelation>` governs how the session runtime cancels
the wrap script. The wrapped action's own cancelation semantics are surfaced
to the wrap script via two template variables:

- `WrappedAction.Cancelation.Mode` — the wrapped action's cancelation method
  (`TERMINATE` or `NOTIFY_THEN_TERMINATE`), or `null` if the wrapped action
  defines no `<Cancelation>`. Note this differs from the runtime's default
  cancelation semantics: an action with no `<Cancelation>` is canceled as if
  by `<CancelationMethodTerminate>`, but the variable carries `null` — the
  "not declared" value for optional data — so wrap scripts can distinguish
  "author explicitly asked for `TERMINATE`" from "author declared nothing".
  Interpolated into a format string, `null` renders as the empty string;
  scripts can apply EXPR's null-coalescing `or` to substitute a fallback
  (for example `{{ WrappedAction.Cancelation.Mode or 'TERMINATE' }}`).
- `WrappedAction.Cancelation.NotifyPeriodInSeconds` — the wrapped action's
  effective grace period between the notify and terminate signals. When the
  wrapped action's mode is `NOTIFY_THEN_TERMINATE` and it omits
  `notifyPeriodInSeconds`, the runtime supplies the schema default for the
  wrapped action's position (120 for a task's `onRun`, 30 otherwise), so the
  wrap script always sees the value the runtime would have enforced in the
  unwrapped case. The variable is `null` when the mode is `TERMINATE` or
  when the wrapped action defines no `<Cancelation>` — a notify period is
  not meaningful in those cases, and typing it as `int?` avoids conflating
  "no notify period applies" with a zero-length notify period.

Together these let the wrap script faithfully reproduce the inner action's
cancelation semantics when it propagates the termination signal: honoring a
graceful notification period when the wrapped action requested
`NOTIFY_THEN_TERMINATE` (for example,
`docker container stop --timeout {{WrappedAction.Cancelation.NotifyPeriodInSeconds}}`),
or terminating immediately when it requested `TERMINATE`.

Because the variable is `int?`, a `null` value interpolated into a format
string renders as the empty string — the example above would produce a
malformed `--timeout` flag if evaluated outside a mode check. Wrap scripts
that reference the variable unconditionally should either branch on
`WrappedAction.Cancelation.Mode` first, or apply EXPR's null-coalescing
`or` to supply a fallback:
`docker container stop --timeout {{ WrappedAction.Cancelation.NotifyPeriodInSeconds or 30 }}`.

Beyond referencing the variables inside script text, a wrap hook can adopt
the wrapped action's cancelation semantics as its *own* `<Cancelation>` by
forwarding both fields as whole-field expressions (requires the
FEATURE_BUNDLE_1 extension, which gates the format-string `mode` form —
see Template Schemas §5.3):

```yaml
onWrapTaskRun:
  command: echo
  args: ["{{WrappedAction.Command}}"]
  timeout: "{{WrappedAction.Timeout}}"
  cancelation:
    mode: "{{WrappedAction.Cancelation.Mode}}"
    notifyPeriodInSeconds: "{{WrappedAction.Cancelation.NotifyPeriodInSeconds}}"
```

Whole-field expression evaluation (RFC 0005 "Expression Evaluation Types")
forwards each variable's type and null-ness into the field, so this
round-trip MUST work for every state of the wrapped action:

| Wrapped action declares      | `mode:` resolves to        | `notifyPeriodInSeconds:` resolves to | Effective wrap-hook cancelation           |
|------------------------------|----------------------------|--------------------------------------|-------------------------------------------|
| `NOTIFY_THEN_TERMINATE`, period *P* (or schema default) | `"NOTIFY_THEN_TERMINATE"` | *P*                    | `NOTIFY_THEN_TERMINATE` with period *P*   |
| `TERMINATE`                  | `"TERMINATE"`              | `null` → field dropped               | `TERMINATE`                               |
| no `<Cancelation>`           | `null` → whole object dropped | `null`                            | undeclared (runtime default: terminate)   |

`timeout:` forwards the same way: `WrappedAction.Timeout` is `int?`, so a
declared timeout forwards verbatim and a `null` result (the wrapped action
specified no timeout) drops the field, leaving the hook position's schema
default in effect (see [Timeout behavior](#timeout-behavior)).

A `null` `mode` drops the entire `cancelation` object — `mode` is the
object's required discriminator, so an "omitted" mode cannot leave a
partial object behind; the wrap action behaves exactly as if its author
had declared no `<Cancelation>`. The runtime resolves these expressions
when it prepares to run the wrap action and MUST fail the action if
`mode` resolves to anything other than the two method names or `null`.

These two variables surface every field of today's `<CancelationMethod>`
schema. A structured alternative — forwarding the whole `<Cancelation>`
object under a single variable — was considered and rejected for ergonomics:
it would introduce another level of depth in the `WrappedAction.Cancelation`
chain without carrying more information, and scalar variables compose
directly with `repr_sh()`/`repr_py()` and EXPR arithmetic in wrap scripts.
If a future specification adds fields to `<CancelationMethod>`, they surface
as additional scalars under `WrappedAction.Cancelation.*` using the field's
PascalCased name, per
[Forwarding `<Action>` fields, current and future](#forwarding-action-fields-current-and-future).

When the wrap script receives a termination signal (SIGTERM on POSIX,
platform-equivalent on Windows), it MUST cause the wrapped process to
receive a termination signal within the `<Cancelation>` grace period.
The simplest way to satisfy this is to `exec` the wrapped command so the
wrapped process inherits the wrap script's signal lineage; container
runtimes that proxy signals by default (`docker container exec`,
`apptainer exec`) inherit propagation automatically. Detached patterns
(`docker container run --rm --detach`, backgrounded SSH) do not share the
wrap script's signal lineage and MUST implement explicit propagation.

After the grace period the session runtime delivers SIGKILL, which cannot
be trapped; any resources still owned by the wrap script at that point
may be orphaned.

### Timeout behavior

Two independent timeouts apply to a wrapped action:

| Timeout                                                            | Field source                          | Bounds                                     | Purpose                                                              |
|--------------------------------------------------------------------|---------------------------------------|--------------------------------------------|----------------------------------------------------------------------|
| **Hook timeout**                                                   | `timeout` on the wrap `<Action>`      | The wrap script itself                     | Limits the wrapper's own execution (infrastructure-side).            |
| **Wrapped timeout**                                                | `WrappedAction.Timeout`               | The wrapped process (in container, on remote host, etc.) | Limits the inner workload's logic (workload-side). |

Wrap scripts MUST propagate the wrapped timeout to the underlying execution
runtime where the runtime exposes a timeout mechanism (e.g.,
`docker container stop --timeout {{WrappedAction.Timeout}}`), and SHOULD
enforce it in-script (`timeout {{WrappedAction.Timeout}}s ...`) when the
runtime exposes none.

When the wrapped action specified no timeout, `WrappedAction.Timeout` is
`null` — following the EXPR semantics for optional data, as with the
`WrappedAction.Cancelation.*` variables. Interpolated into a format string,
`null` renders as the empty string, so wrap scripts that reference the
variable unconditionally MUST either branch on it first or apply EXPR's
null-coalescing `or` to supply a fallback; and they MUST omit the
underlying runtime's timeout flag when the value is `null` (for example,
omit `--timeout` from `docker container stop` rather than passing
`--timeout 0`, which Docker interprets as "kill immediately"). Typing the
variable `int?` rather than using a `0` sentinel lets whole-field
expression forwarding (`timeout: "{{WrappedAction.Timeout}}"`) work in
every case: a declared timeout forwards verbatim, and a `null` result
drops the field so the hook position's schema default applies — a `0`
sentinel would be out of range for the `<posinteger>` field.

Templates that omit `timeout` on a wrap hook inherit OpenJD's default for
that hook position. The session runtime enforces the hook timeout by
applying the wrap hook's `<Cancelation>` policy (see
[Cancelation behavior](#cancelation-behavior)).

## Design Choice Rationale

### Three separate hooks rather than a single unified hook

An alternative design uses a single `onWrapAction` hook with a
`WrappedAction.Type` discriminator (`TASK_RUN`, `ENV_ENTER`, `ENV_EXIT`). It is
more DRY and lets the wrapper express action-type-specific logic via EXPR
conditionals. However:

1. **Schema explicitness.** Three hooks make the environment's capabilities
   visible directly in the schema. A template reader sees at a glance that
   `onWrapEnvEnter` is defined, which means inner-environment `onEnter` actions are
   intercepted. With a single `onWrapAction`, the same information is buried
   inside the wrap script.
2. **Per-phase logic without a discriminator.** Three hooks let authors write
   dedicated scripts per action type without needing a `WrappedAction.Type`
   switch inside a single hook. Under the three-hook model, the phase is
   already determined by which hook is being invoked.
3. **Debug story.** A stack trace or log line citing `onWrapTaskRun` is
   unambiguous. A stack trace citing `onWrapAction` requires the reader to know
   which branch the script took.

A future extension could add `onWrapAction` as an alternative to the three-hook
model that relaxes the all-or-nothing rule (an environment could define
`onWrapAction` alone and skip the three separate hooks). See
[Future Work](#single-unified-onwrapaction-shorthand).

### Three hooks on `<Environment>` rather than a new template type

Adding the wrap hooks to existing `<EnvironmentActions>` keeps the environment template model intact; a new template type would fragment the model and require new plumbing in every implementation with no offsetting benefit.

### All-or-nothing rule for wrap hooks

Requiring all three hooks to be defined together prevents partial wrapping,
where some inner-action phases are intercepted and others run normally.
The schema-level cost is a small amount of additional YAML; the gain is
explicit, mechanically-checkable execution context parity.

Wrap environments whose enter or exit phases have no meaningful work MAY set
them to shell no-ops (for example, `bash -c "true"`); the rule requires the
hooks to be *defined*, not to do substantive work. The
[`onWrapAction` shorthand in Future Work](#single-unified-onwrapaction-shorthand)
is the anticipated relaxation for wrappers whose three phases share identical
logic.

### Unified `WrappedAction.*` namespace across all hooks

All three wrap hooks see the same `WrappedAction.*` variables with identical
semantics. This has three concrete benefits:

1. **Helper script reuse.** A single wrap script can be written once and
   referenced from `onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit` without
   per-hook variable substitutions. The [Basic Example](#basic-example)
   demonstrates this with a single `Wrap` embedded file shared by all three
   hooks.
2. **Forward compatibility with `<Action>` evolution.** Any new field added
   to `<Action>` in a later RFC surfaces automatically under the same
   namespace — no bespoke per-field plumbing.
3. **Forward compatibility with action self-introspection.** A future
   extension that lets an action reference its own fields would naturally
   live at `Action.*`; `WrappedAction.*` reads as "the `Action` being
   wrapped" and composes cleanly with that.

`WrappedEnv.Name` and `WrappedStep.Name` cover the lifecycle context that
the action itself does not carry: the name of the inner environment whose
`onEnter`/`onExit` is being wrapped, and the name of the step whose task is
being wrapped, respectively. Both share the `Wrapped*` prefix with
`WrappedAction.*` so the wrap-hook context surface is discoverable in one
namespace family.

### Template variables rather than environment variables

Each wrap hook receives its context as template variables rather than
environment variables. Template variables are type-safe (with the EXPR
extension, `WrappedAction.Args` is `list[string]` that can be shell-quoted
with `repr_sh()`), available at template expansion time, and consistent
with how other context is provided in OpenJD. Environment variables would
require parsing and escaping in every wrap script.

### `list[string]` for environment variables

Environment variables are provided as a flat list of `"KEY=value"` strings rather
than a dictionary. This matches the format expected by container runtimes
(`docker exec -e KEY=VALUE`, `apptainer exec --env KEY=VALUE`) and is
straightforward to iterate over in a list comprehension:

```yaml
{{ repr_sh(flatten([['-e', e] for e in WrappedAction.Environment])) }}
```

A dictionary type would require additional syntax for iteration and would not map
directly to CLI-flag conventions. When a wrap script needs the key and value
separately, the EXPR `split` function (RFC 0006) recovers them:
`e.split('=', 1)` returns `["KEY", "value"]`, splitting on the first `=` only so
values containing `=` are preserved.

### Command escaping via `repr_sh` rather than raw interpolation

The wrap script must reconstruct the wrapped action's command line inside a shell
script. This is inherently dangerous: if `WrappedAction.Command` or
`WrappedAction.Args` contain shell metacharacters (`"`, `'`, `` ` ``, `&`,
`|`, `>`, `<`, `*`, `?`, `(`, `)`, `\`, newlines), raw interpolation
breaks the script or, worse, executes unintended commands.

The RFC requires the EXPR extension and its `repr_sh()` function (from RFC 0006)
for safe command construction. `repr_sh(string)` applies `shlex.quote` semantics:
it wraps the value in single quotes and escapes embedded single quotes.
`repr_sh(list[string])` applies this per element and joins with spaces, so each
element becomes exactly one argv entry when the shell parses the line.

For Windows shells, the equivalent functions are `repr_cmd()` and `repr_pwsh()`
from RFC 0006, which handle each shell's different escaping rules.

## Security Considerations

### Quoting wrapped commands is the template author's responsibility

The wrap script reconstructs the wrapped action's command line inside the
wrap action's `command`/`args` (or, more commonly, inside an embedded shell
script). The template author is responsible for quoting `WrappedAction.*`
values correctly so that shell metacharacters (`"`, `'`, `` ` ``, `&`, `|`,
`>`, `<`, `*`, `?`, `(`, `)`, `\`, newlines) in user-supplied commands do
not break the script or, worse, cause the shell to execute unintended
commands.

The specification provides the primitives needed to do this correctly:

- **`repr_sh()`** (RFC 0006): applies `shlex.quote` semantics to a string or
  to each element of a `list[string]`, producing safely quoted argv tokens
  that the POSIX shell parses as exactly one argument each.
- **`repr_cmd()`** and **`repr_pwsh()`** (RFC 0006): the Windows
  equivalents, which handle `cmd.exe` and PowerShell's distinct escaping
  rules.

The dependency on `EXPR` (and therefore on this function library) is
declared in [Backward compatibility](#backward-compatibility) so that every
template that uses wrap hooks has these functions available.

Patterns like `bash -c "{{WrappedAction.Command}} {{WrappedAction.Args}}"`,
which interpolate raw values into a shell-parsed string, are unsafe and
should be replaced with the `repr_sh`-based forms shown in the
[Basic Example](#basic-example). Wrap scripts written in a language that
exposes a native argv-array API (Python's
`subprocess.Popen([cmd, *args])`, Rust's `std::process::Command::args`,
etc.) avoid the shell-quoting problem by sidestepping the shell entirely.

### Wrapping overhead and command length

Wrap hooks are subject to the host OS maximum command-line length. A wrap
hook effectively doubles the command string (once in the wrapper's
invocation and once in the wrapped action). A job with many `openjd_env`-set
variables plus a `docker exec` prefix can exceed `ARG_MAX` on a command that
would fit directly. An `onRun` near the 256 KB macOS `ARG_MAX`, for example,
may fail only when wrapped.

**Template authors** writing wrapping environments should account for this
when forwarding `WrappedAction.Environment` and other arbitrarily-sized
fields. Common mitigations: forward only the variables the wrapped context
actually needs, write large data to disk in the wrap script and reference
the file path in the wrapped command, or invoke the wrapped binary
directly via the runtime's argv-array interface where one is available
(e.g., `docker exec` with `-e KEY=VALUE` per variable rather than a single
concatenated argument).

**Implementations** SHOULD validate command-line length before exec and
produce an error that names the limit and the wrap-hook context, rather
than letting the OS return `E2BIG` from the underlying syscall. The error
should make clear which action's expansion exceeded the limit so the
template author can locate and fix the source.

## Rejected Ideas

### Container-specific session action or runtime fields

We rejected mechanisms that bake container semantics into the specification:
a dedicated `onRunInContainer` action, a `containerImage` field that the
runtime acts on automatically, or a global `docker.enabled` /
`apptainer.enabled` toggle. All three hard-code one runtime, remove the
template author's control over the invocation (mount points, network mode,
GPU flags, security options), and cannot express per-environment runtime
choices. The general wrap-hook mechanism keeps the specification runtime-
agnostic and supports use cases beyond containers.

### Nested wrap composition

An earlier iteration allowed multiple environments to define wrap hooks, composing as nested wrappers; this RFC restricts the session stack to a single wrap layer for implementation simplicity. See [Future Work › Nested wrap composition](#nested-wrap-composition).

## Future Work

The following ideas are deferred to follow-up RFCs when concrete demand emerges.

### Escape hatches for inner actions to bypass wrapping

Some inner actions cannot run inside a wrapped context: mounting an NFS
share that the container will bind-mount, fetching short-lived host
credentials, or cleaning up after a crashed container. The idiomatic solution
is to nest these as a separate environment outside the wrap environment. Two
candidate escape hatches are deferred for the less idiomatic case:

1. **`runOnHost: true` on `<Action>`.** A declarative field that bypasses
   the active wrap hook for a specific action. Visible in the schema; clear
   intent. Tradeoff: lets an inner-template author override the wrapping
   environment's policy.
2. **`openjd_cmd: <directive>` stdout line emitted by a wrap hook.**
   Symmetric with `openjd_env: KEY=value`. A wrap hook could emit
   `openjd_cmd: run-on-host` to instruct the session runtime to run a
   specific action normally, bypassing the wrap. This places the decision
   inside the wrap environment rather than the inner action.

A future RFC should pick one or both and specify their interaction with
cancelation, timeout, and environment-variable propagation.

### Single unified `onWrapAction` shorthand

A future extension could add `onWrapAction` (with a `WrappedAction.Type`
discriminator) as an alternative to the three-hook model. Defining
`onWrapAction` alone would satisfy the wrap-hook requirement and relax the
current all-or-nothing rule, benefiting wrap environments whose three phases
share identical logic (e.g., a profiling wrapper applying the same tool to
every action). The three-hook form would remain available for authors who
want per-phase schema explicitness; the two forms would be mutually exclusive
per environment. Reasons for rejecting it from the initial RFC are in
[Design Choice Rationale](#three-separate-hooks-rather-than-a-single-unified-hook).

### Nested wrap composition

Stacking multiple wrap environments (e.g., a profiling wrapper outside a
container wrapper, or `sudo -u` outside a container) is the natural next
step beyond the single-wrap-layer rule. A future RFC should specify
composition order, per-layer scoping of `WrappedAction.*`/`WrappedEnv.*`/
`WrappedStep.*`, signal propagation across layers, `openjd_env` visibility
between layers, and how the all-or-nothing rule relaxes for pass-through
intermediate layers. Nothing in the schema or namespace adopted here
precludes the layered model.

### Distinguishing wrapper failures from workload failures

A future extension could reserve a sentinel exit status (e.g., `125`,
following the Docker CLI convention) so wrap scripts can signal that the
wrapping substrate failed (Docker daemon unreachable, image pull failed,
SSH connection refused) as distinct from the wrapped action itself
exiting non-zero — useful if schedulers want to retry infrastructure
failures on a different worker without retrying genuine workload
failures.

### Session health monitoring

Periodic health-checking of wrapped processes is cleanly separable from the wrap mechanic and belongs in a dedicated environment-health-monitoring RFC.

### EXPR f-strings for wrap-script ergonomics

Reconstructing structured strings from `WrappedAction.*` is verbose under
EXPR's current expression set, which excludes f-strings. A future EXPR
extension adding f-string syntax would let `repr_sh()` calls drop explicit
`+` concatenation. This is purely an EXPR-side improvement; the wrap-action
specification does not depend on it.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
