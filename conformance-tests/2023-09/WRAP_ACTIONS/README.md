# WRAP_ACTIONS Conformance Tests

Conformance tests for the `WRAP_ACTIONS` extension defined in
[RFC 0008 — Environment Wrap Actions](../../../rfcs/0008-environment-wrap-actions.md).

## What this extension does

`WRAP_ACTIONS` adds three new fields to `<EnvironmentActions>`:

```yaml
<EnvironmentActions> ::= the object:
  onEnter: <Action>          # optional
  onWrapEnvEnter: <Action>   # NEW — optional
  onWrapTaskRun: <Action>    # NEW — optional
  onWrapEnvExit: <Action>    # NEW — optional
  onExit: <Action>           # optional
```

When an active environment defines the wrap hooks, the runtime runs each
hook *instead of* the corresponding lifecycle action of every inner
environment and task. Each hook receives the wrapped action's fields via
the `WrappedAction.*` template variables:

| Variable                      | Type           | Description                                                         |
|-------------------------------|----------------|---------------------------------------------------------------------|
| `WrappedAction.Command`       | `string`       | The `command` from the wrapped action                               |
| `WrappedAction.Args`          | `list[string]` | The `args` from the wrapped action                                  |
| `WrappedAction.Environment`   | `list[string]` | `openjd_env`-defined variables as `["KEY=value", ...]`              |
| `WrappedAction.Timeout`       | `int?`         | Timeout of the wrapped action in seconds; `null` if none            |
| `WrappedEnv.Name`             | `string`       | Name of the inner environment (only in `onWrapEnvEnter`/`onWrapEnvExit`)  |
| `WrappedStep.Name`            | `string`       | Name of the step whose task is being wrapped (only in `onWrapTaskRun`) |

## RFC rules these tests verify

- **All-or-nothing**: defining any wrap hook requires defining all three
  (`onWrapEnvEnter`, `onWrapTaskRun`, `onWrapEnvExit`).
- **Single wrap layer**: at most one environment in the session stack may
  define wrap hooks.
- **Variable scope**: `WrappedAction.*` may be referenced only inside the
  three wrap hooks; `WrappedEnv.*` only inside `onWrapEnvEnter`/`onWrapEnvExit`;
  `WrappedStep.*` only inside `onWrapTaskRun`.
- **Extension gating**: wrap hooks are only valid when `WRAP_ACTIONS` is
  declared in `extensions:`.
- **Interception**: the wrap hooks run instead of the corresponding
  lifecycle actions of inner environments and tasks.
- **Safe forwarding**: with `repr_sh()` from the EXPR extension, arbitrary
  user input (quotes, metacharacters, globs, Unicode) reaches the wrapped
  process verbatim.

## How these tests are designed

The RFC motivates the wrap hooks with Docker/Apptainer use cases, but
those containers aren't required to *test* the mechanism. These tests use
trivial wrap scripts — typically `echo`, `sh -c`, or `printf` — that
observe the injected `WrappedAction.*` variables and write sentinel
markers to stdout.

A test passes if:
- Each wrap hook runs in place of its corresponding lifecycle action
  (verified by sentinels the original action would never emit).
- The injected `WrappedAction.*` variables carry the exact bytes of the
  wrapped action.
- The original action does **not** execute.

## Layout

```
WRAP_ACTIONS/
├── README.md                       (this file)
├── env_templates/                  # Env template validation tests
│   ├── 4.2--minimal-wrap-env-template.yaml
│   ├── 4.2--wrap-only-environment.yaml
│   ├── 4.2--wrap-with-timeout.yaml
│   ├── 4.2--empty-actions-no-wrap-no-enter-no-exit.invalid.yaml
│   ├── 4.2--wrap-fmtstring-timeout-no-feature-bundle.invalid.yaml
│   ├── 4.3--wrap-only-onwrap-task-run.invalid.yaml
│   └── 4.3--wrap-missing-onwrap-exit.invalid.yaml
└── jobs/                           # End-to-end execution tests
    │  # Interception — each hook runs in place of its lifecycle action
    ├── wrap-intercepts-simple-echo.test.yaml
    ├── wrap-original-onrun-does-not-run.test.yaml
    ├── wrap-enter-and-exit-three-hooks.test.yaml
    ├── wrap-enter-intercepts-inner-on-enter.test.yaml
    ├── wrap-exit-intercepts-inner-on-exit.test.yaml
    ├── wrap-env-own-lifecycle-not-wrapped.test.yaml
    ├── wrap-three-hooks-python.test.yaml
    ├── wrap-three-hooks-windows.test.yaml
    │  # WrappedAction.* / WrappedEnv.* / WrappedStep.* injection
    ├── wrap-enter-receives-wrapped-action.test.yaml
    ├── wrap-exit-receives-wrapped-action.test.yaml
    ├── wrap-task-command-injected.test.yaml
    ├── wrap-task-args-preserved.test.yaml
    ├── wrap-task-environment-injected.test.yaml
    ├── wrap-task-action-timeout-injected.test.yaml
    ├── wrap-task-action-timeout-null-when-unset.test.yaml
    ├── wrap-timeout-injected-python.test.yaml
    ├── wrap-no-args.test.yaml
    ├── wrap-empty-environment-list.test.yaml
    ├── wrap-cancelation-mode-terminate.test.yaml
    ├── wrap-cancelation-mode-notify-then-terminate.test.yaml
    ├── wrap-cancelation-mode-null-when-no-cancelation.test.yaml
    ├── wrap-cancelation-notify-period-injected.test.yaml
    ├── wrap-cancelation-notify-period-defaults-onrun-120.test.yaml
    ├── wrap-cancelation-notify-period-defaults-onenter-30.test.yaml
    ├── wrap-cancelation-notify-period-defaults-onexit-30.test.yaml
    ├── wrap-cancelation-notify-period-null-when-terminate.test.yaml
    ├── wrap-cancelation-notify-period-null-when-no-cancelation.test.yaml
    ├── wrap-cancelation-roundtrip-notify-then-terminate.test.yaml
    ├── wrap-cancelation-roundtrip-terminate.test.yaml
    ├── wrap-cancelation-roundtrip-no-cancelation.test.yaml
    ├── wrap-cancelation-roundtrip-period-only.test.yaml
    ├── wrap-cancelation-roundtrip-job-environment.test.yaml
    ├── wrap-cancelation-partial-fmtstring-mode.test.yaml
    │  # Run-time cancelation validation (§5.3: "the runtime MUST fail the action")
    ├── wrap-cancelation-mode-resolves-invalid-fails.test.yaml
    ├── wrap-cancelation-terminate-with-period-fails.test.yaml
    ├── wrap-cancelation-period-over-cap-fails.test.yaml
    │  # Environment-template scope carried to wrap hooks
    ├── wrap-env-template-parameters-in-hooks.test.yaml
    ├── wrap-env-let-bindings-in-hooks.test.yaml
    ├── wrap-openjd-env-from-wrapped-onenter-propagates.test.yaml
    ├── wrap-openjd-fail-from-wrapped-process.test.yaml
    ├── wrap-environment-includes-variables-map.test.yaml
    │  # Failure semantics & cleanup guarantees
    ├── wrap-failed-enter-still-runs-wrap-exit.test.yaml
    ├── wrap-inner-env-without-on-exit-skips-exit-hook.test.yaml
    │  # Exit-status propagation
    ├── wrap-exit-status-propagates.test.yaml
    ├── wrap-exit-status-python.test.yaml
    ├── wrap-exit-status-windows.test.yaml
    │  # Composition / coexistence
    ├── wrap-outer-env-without-wrap-ignored.test.yaml
    ├── wrap-runs-for-every-task.test.yaml
    ├── wrap-ignores-wrapped-action-vars.test.yaml
    ├── wrap-job-environment.test.yaml
    ├── wrap-step-environment.test.yaml
    │  # Safe forwarding of arbitrary user input (see Security matrix below)
    ├── wrap-preserves-shell-metacharacters.test.yaml
    ├── wrap-preserves-nested-quotes.test.yaml
    ├── wrap-preserves-unicode-cjk.test.yaml
    ├── wrap-preserves-empty-arg.test.yaml
    ├── wrap-glob-characters-literal.test.yaml
    ├── wrap-path-traversal-literal.test.yaml
    │  # Invalid templates / sessions the runner must reject
    ├── wrap-without-extension-fails.invalid.test.yaml
    ├── wrap-without-expr-extension.invalid.test.yaml
    ├── wrap-cancelation-fmtstring-mode-no-feature-bundle.invalid.test.yaml
    ├── wrap-multiple-wrap-envs-rejected.invalid.test.yaml
    ├── wrap-two-wrap-env-templates-rejected.invalid.test.yaml
    ├── wrap-job-and-step-env-rejected.invalid.test.yaml
    ├── wrap-partial-hooks-rejected.invalid.test.yaml
    └── wrap-wrappedaction-outside-wrap-hook-rejected.invalid.test.yaml
```

Two additional env-template validation fixtures cover the variable scope
rule beyond action args (`env_templates/`):

```
    ├── 4--wrappedaction-in-cancelation-outside-hook.invalid.yaml
    └── 4--wrappedaction-in-embedded-file.invalid.yaml
```

A second audit round added fixtures for the remaining coverage gaps
(RFC 0008 test-coverage review):

```
WRAP_ACTIONS/
├── env_templates/
│   │  # Variable scope negatives (RFC §Template variables)
│   ├── 4--wrappedenv-name-in-onwraptaskrun.invalid.yaml
│   ├── 4--wrappedstep-name-in-onwrapenventer.invalid.yaml
│   ├── 4--wrappedstep-name-in-onwrapenvexit.invalid.yaml
│   ├── 4--wrappedaction-in-expr-funcall-outside-hook.invalid.yaml
│   ├── 4--wrappedaction-in-let-outside-hook.invalid.yaml
│   │  # All-or-nothing rule — remaining reject subsets
│   ├── 4.3--wrap-only-onwrap-env-enter.invalid.yaml
│   ├── 4.3--wrap-only-onwrap-env-exit.invalid.yaml
│   ├── 4.3--wrap-enter-and-exit-missing-task-run.invalid.yaml
│   ├── 4.3--wrap-run-and-exit-missing-enter.invalid.yaml
│   │  # FEATURE_BUNDLE_1 accept-side twin of the gated-form rejects
│   └── 4.2--wrap-fmtstring-timeout-and-mode-with-feature-bundle.yaml
├── jobs/
│   │  # Absent-by-design: host env vars excluded (RFC §Host environment
│   │  # variables and embedded file paths)
│   ├── wrap-environment-excludes-host-vars.test.yaml
│   │  # Macro propagation × emitter (RFC §Stdout forwarding)
│   ├── wrap-openjd-env-from-wrap-script-itself.test.yaml
│   ├── wrap-openjd-env-task-grand-child-visible-next-task.test.yaml
│   ├── wrap-openjd-env-grand-child-under-exit-hook.test.yaml
│   ├── wrap-progress-status-macros-forwarded.test.yaml
│   ├── wrap-stderr-forwarded-from-grand-child.test.yaml
│   ├── wrap-discarded-grand-child-stdout-loses-macro.test.yaml
│   │  # Nesting depth 2 and the nothing-to-replace rule
│   ├── wrap-two-inner-envs-wrappedenv-name-per-invocation.test.yaml
│   ├── wrap-variables-only-inner-env-skips-hooks.test.yaml
│   │  # Failure-path breadth (RFC §Failure semantics, §Lifecycle)
│   ├── wrap-failed-exit-hook-own-onexit-still-runs.test.yaml
│   ├── wrap-grand-child-fails-under-enter-hook.test.yaml
│   ├── wrap-unwrapped-parity-task-failure.test.yaml
│   │  # Session composition (How Jobs Are Run)
│   ├── wrap-two-steps-wrappedstep-name-per-step.test.yaml
│   ├── wrap-job-env-wraps-step-env.test.yaml
│   └── wrap-no-wrap-control.test.yaml
```

(A `jobs/proposed/` directory of spec-correct fixtures that fail against the
current reference implementations is added separately by the
expected-failures PR; it is documented there.)

Most execution tests use POSIX shell commands (`sh`, `bash`, `echo`,
`printf`) and are gated to `runOn: [posix]`. Fixtures that carry no
`runOn` gate use `python`, the suite's portable interpreter — including
the cross-platform `*-python` variants — and the `*-windows` variants
use `cmd` and are gated to `runOn: [windows]`.

## Security test matrix — RFC §"Security Considerations"

The RFC's [Security Considerations](../../../rfcs/0008-environment-wrap-actions.md#security-considerations)
section requires that arbitrary user-supplied command/argument bytes reach
the wrapped process verbatim, with shell metacharacters quoted (not
interpreted) by `repr_sh()`. This matrix maps those concerns to the job
bundles in this directory:

| # | Scenario                          | Test file                                       |
|---|-----------------------------------|-------------------------------------------------|
| 1 | Nested quoting                    | `wrap-preserves-nested-quotes.test.yaml`        |
| 2 | Shell metacharacters              | `wrap-preserves-shell-metacharacters.test.yaml` |
| 3 | Path traversal                    | `wrap-path-traversal-literal.test.yaml`         |
| 4 | Shell globbing                    | `wrap-glob-characters-literal.test.yaml`        |
| 5 | Unicode paths                     | `wrap-preserves-unicode-cjk.test.yaml`          |
| 6 | Empty / whitespace-only arguments | `wrap-preserves-empty-arg.test.yaml`            |
| 7 | Newlines in arguments             | Rejected by the 2023-09 `ArgString` regex —     |
|   |                                   | no dedicated conformance test needed.           |
| 8 | Near-limit command length         | Covered by unit tests in the implementation.    |
|   |                                   | Conformance runners vary in stdout buffer       |
|   |                                   | limits, so this is left to implementation tests |
|   |                                   | rather than conformance.                        |

## Additional semantics tested

- **Three-hook interception**: each hook runs in place of its
  corresponding lifecycle action
  (`wrap-enter-intercepts-inner-on-enter`,
  `wrap-exit-intercepts-inner-on-exit`,
  `wrap-enter-and-exit-three-hooks`, plus the cross-platform
  `wrap-three-hooks-python` and `wrap-three-hooks-windows` variants).
- **Wrapping env's own lifecycle is never wrapped**: a wrapping
  environment's own `onEnter`/`onExit` are not intercepted by its own wrap
  hooks (`wrap-env-own-lifecycle-not-wrapped`).
- **Variable injection**: `WrappedAction.Command/Args/Environment/Timeout`
  reach the wrap script with the right values
  (`wrap-task-command-injected`, `wrap-task-args-preserved`,
  `wrap-task-environment-injected`, `wrap-task-action-timeout-injected`,
  `wrap-timeout-injected-python`, `wrap-no-args`,
  `wrap-empty-environment-list`), and `WrappedAction.*` is
  in scope in the env-lifecycle hooks too
  (`wrap-enter-receives-wrapped-action`,
  `wrap-exit-receives-wrapped-action`).
- **Timeout nullability**: `WrappedAction.Timeout` (typed `int?`) is `null`
  when the wrapped action specifies no timeout — rendering empty in
  interpolation and observable via EXPR null-coalescing
  (`wrap-task-action-timeout-null-when-unset`).
- **Cancelation mode injection**: `WrappedAction.Cancelation.Mode` (typed
  `string?`) carries `TERMINATE` (`wrap-cancelation-mode-terminate`),
  `NOTIFY_THEN_TERMINATE` (`wrap-cancelation-mode-notify-then-terminate`),
  or `null` when the wrapped action defines no `<Cancelation>` — rendering
  empty in interpolation and observable via EXPR null-coalescing
  (`wrap-cancelation-mode-null-when-no-cancelation`).
- **Cancelation notify-period injection**:
  `WrappedAction.Cancelation.NotifyPeriodInSeconds` (typed `int?`) carries
  the effective grace period when the wrapped action's mode is
  `NOTIFY_THEN_TERMINATE` — including the runtime-supplied schema default
  when the wrapped action omits the field (120 on a task's `onRun`, 30
  otherwise) — and is `null` otherwise:
  - `wrap-cancelation-notify-period-injected` (explicit value)
  - `wrap-cancelation-notify-period-defaults-onrun-120` (schema default on a task)
  - `wrap-cancelation-notify-period-defaults-onenter-30` (schema default on an env `onEnter`)
  - `wrap-cancelation-notify-period-defaults-onexit-30` (schema default on an env `onExit`)
  - `wrap-cancelation-notify-period-null-when-terminate` (null when `TERMINATE`)
  - `wrap-cancelation-notify-period-null-when-no-cancelation` (null when no `<Cancelation>`)
- **Cancelation + timeout round-trip forwarding** (Template Schemas §5.3
  and §5, FEATURE_BUNDLE_1): a wrap hook adopts the wrapped action's
  cancelation and timeout as its own via whole-field expressions
  (`mode: "{{WrappedAction.Cancelation.Mode}}"` /
  `notifyPeriodInSeconds: "{{WrappedAction.Cancelation.NotifyPeriodInSeconds}}"` /
  `timeout: "{{WrappedAction.Timeout}}"`),
  with null-forwarding per RFC 0005 expression evaluation types (a null
  timeout or notify period drops the field; a null mode drops the whole
  `cancelation` object):
  - `wrap-cancelation-roundtrip-notify-then-terminate` (both fields forwarded verbatim)
  - `wrap-cancelation-roundtrip-terminate` (null period drops the field)
  - `wrap-cancelation-roundtrip-no-cancelation` (null mode drops the whole `cancelation` object)
  - `wrap-cancelation-roundtrip-period-only` (literal mode, forwarded period —
    already legal under FEATURE_BUNDLE_1's `@fmtstring` notify period)
  - `wrap-cancelation-fmtstring-mode-no-feature-bundle` (invalid: the
    format-string `mode` form requires FEATURE_BUNDLE_1)
  - `wrap-cancelation-partial-fmtstring-mode` (a format-string `mode` gets
    normal format string behavior — partial interpolation like
    `"{{ ... }}_THEN_TERMINATE"` is valid; the resolved value is checked
    against the two mode names at run time)
- **Run-time cancelation validation** (Template Schemas §5.3: after a
  format-string `mode` resolves, "the object MUST then validate against
  that form's schema" and "Any other resolved value is an error; the
  runtime MUST fail the action"; §5.3.2 caps the notify period at 600).
  Constant expressions could be folded and rejected during validation, so
  each fixture derives its invalid value from `WrappedAction.*` — seeded
  per-action at host evaluation time, unknowable statically or at job
  creation — forcing the check to happen where the spec requires it. The
  wrapped action's script must never run:
  - `wrap-cancelation-mode-resolves-invalid-fails` (forwarded mode plus a
    literal suffix resolves to a non-mode string)
  - `wrap-cancelation-terminate-with-period-fails` (forwarded mode
    resolves `TERMINATE` with a non-null period)
  - `wrap-cancelation-period-over-cap-fails` (forwarded period plus an
    offset resolves over the 600-second cap)
- **Round-trip forwarding through job instantiation**: the same
  forwarding pattern with the wrap env declared in `jobEnvironments`, so
  the template passes through job creation where `WrappedAction.*`
  cannot exist yet — resolution of the forwarded `timeout` /
  `notifyPeriodInSeconds` must defer to run time
  (`wrap-cancelation-roundtrip-job-environment`).
- **Environment-template scope in hooks**: a wrap environment template's
  own `parameterDefinitions` and script-level `let` bindings resolve
  inside all three hooks (`wrap-env-template-parameters-in-hooks`,
  `wrap-env-let-bindings-in-hooks`) — the wrapped step's symbol table
  knows nothing about them, so the runtime must carry the environment's
  own scope to its hooks.
- **`WrappedAction.Environment` carries all session-defined variables**
  (§4.3.1): `openjd_env` exports and an inner environment's declarative
  `variables:` map both surface in the forwarded list
  (`wrap-environment-includes-variables-map`).
- **Session-level single-layer rule**: two wrap-defining environments
  supplied as *separate* environment templates — no single template is
  invalid, so only the session/runner can reject the stack
  (`wrap-two-wrap-env-templates-rejected`).
- **Cleanup guarantee** (RFC 0008 "Lifecycle and cleanup guarantees"):
  a failed `onWrapEnvEnter` still runs the inner environment's
  `onWrapEnvExit` and the wrapping environment's own `onExit`, and the
  failing hook's exit code is the surfaced task failure
  (`wrap-failed-enter-still-runs-wrap-exit`).
- **Exit-hook skip**: an inner environment with no `onExit` has nothing
  to replace, so `onWrapEnvExit` must not fire for it
  (`wrap-inner-env-without-on-exit-skips-exit-hook`).
- **`openjd_env` propagation**: variables emitted by a wrapped `onEnter`
  surface in `WrappedAction.Environment` for subsequent wrapped actions
  (`wrap-openjd-env-from-wrapped-onenter-propagates`).
- **`openjd_fail` propagation**: a failure macro emitted by the wrapped
  process is recognized through the wrap script's forwarded stdout, and
  the wrapped exit status propagates
  (`wrap-openjd-fail-from-wrapped-process`).
- **Exit-status propagation**: a non-zero wrapped process fails the wrap
  action and therefore the task (`wrap-exit-status-propagates`, plus the
  `-python` and `-windows` variants).
- **Environment placement**: wrap hooks work in `jobEnvironments`
  (`wrap-job-environment`) and `stepEnvironments` (`wrap-step-environment`).
- **Outer-non-wrap-env coexistence**: a non-wrapping environment can
  appear in the stack alongside the single wrapping environment
  (`wrap-outer-env-without-wrap-ignored`).
- **Per-task repeat**: variables re-inject cleanly per task
  (`wrap-runs-for-every-task`).
- **Wrap may ignore injected variables**: a wrap action that references no
  `WrappedAction.*` still runs (`wrap-ignores-wrapped-action-vars`).
- **Original action does not run**: the wrapped lifecycle action is
  replaced, not also executed (`wrap-original-onrun-does-not-run`).
- **Invalid templates / sessions**:
  - `wrap-without-extension-fails`: hooks require the `WRAP_ACTIONS` extension.
  - `wrap-without-expr-extension`: `WRAP_ACTIONS` requires `EXPR`.
  - `wrap-multiple-wrap-envs-rejected`: at most one wrap env per session.
  - `wrap-two-wrap-env-templates-rejected`: the same rule across two
    separately-supplied environment templates (session-level check).
  - `wrap-job-and-step-env-rejected`: single-wrap-layer rule across job and
    step environments.
  - `wrap-partial-hooks-rejected`: all-or-nothing rule (job side).
  - `wrap-wrappedaction-outside-wrap-hook-rejected`: variable scope rule (job side).
  - `4--wrappedaction-in-cancelation-outside-hook`: scope rule applies to an
    action's cancelation fields, not just command/args/timeout (env side).
  - `4--wrappedaction-in-embedded-file`: scope rule applies to embedded file
    `data` — embedded files are shared by all of the script's actions,
    including the env's own `onEnter`/`onExit` where `WrappedAction.*`
    never exists (env side).
  - `4.3--wrap-only-onwrap-task-run`: all-or-nothing rule (env side).
  - `4.3--wrap-missing-onwrap-exit`: all-or-nothing rule (env side).
  - `4.2--empty-actions-no-wrap-no-enter-no-exit`: an `actions` block must
    define at least one action.
  - `4.2--wrap-fmtstring-timeout-no-feature-bundle`: a format-string `timeout`
    on a wrap hook requires `FEATURE_BUNDLE_1`; without it the hook `timeout`
    must be a plain positive integer.

## Running the tests

From the repo root:

```bash
# Run just the WRAP_ACTIONS extension tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/WRAP_ACTIONS

# Run only the job execution tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/WRAP_ACTIONS/jobs

# Pattern-match a single scenario
uv run conformance-tests/run_openjd_cli_tests.py '*wrap*unicode*'
```

## Writing your own runner

See the top-level [conformance README](../../README.md) for the standard
runner contract. The behavior specific to `WRAP_ACTIONS`:

1. When the env template declares `extensions: [WRAP_ACTIONS]`, the
   runner must accept `onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit`
   under `environment.script.actions`, and must reject the template if
   any one of the three is defined without all three.
2. When an environment with wrap hooks is entered, every subsequent
   inner-environment lifecycle action and task `onRun` must execute the
   corresponding wrap hook in place of the original action, with
   `WrappedAction.*` variables populated from the wrapped action's fields.
3. When two or more environments in the session stack define any wrap
   hook, the runner must reject the session before entering any
   environment.
4. When wrap-hook fields are used without `WRAP_ACTIONS` in the
   `extensions` list, the runner must reject the template at validation
   time.
5. When a template lists `WRAP_ACTIONS` without also listing `EXPR`, the
   runner must reject the template at validation time.
