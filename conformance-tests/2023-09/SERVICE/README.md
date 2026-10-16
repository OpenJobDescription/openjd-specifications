# SERVICE Conformance Tests

Conformance tests for the `SERVICE` extension defined in
[RFC 0009 — Services](../../../rfcs/0009-service.md).

## What this extension does

`SERVICE` adds a new entity, the `<Service>` (Template Schemas §9): a long-lived
process that a scheduler starts before scheduling the Tasks in its scope, keeps
running for the lifetime of its scope, and stops once the scope no longer needs
it. A Step depends on a Service by listing `service: <name>` in its
`dependencies` (§3.2), beside the Steps it lists with `dependsOn`, and a
Service depends on Steps and other Services the same way. A Service publishes
one or more named ports, each TCP (the default) or UDP, whose endpoint the
entities that depend on it read through the `Service.*` format-string scope.

```yaml
# Job Template (§1.1)
services: [ <Service>, ... ]                   # NEW — scope from dependencies (§9.1)
externalServices: [ <ServiceRequirement>, ... ] # NEW — external Services used directly (§9.8)
# <StepDependency> (§3.2), in a Step's, a Service's, or a Job Environment's `dependencies`
dependsOn: "<StepName>" | service: "<ServiceName>"  # one key; `service` is NEW
# Environment Template (§1.2)
services: [ <Service>, ... ]                   # NEW — external Services, scoped like inline ones
# <Environment> (§4)
dependencies: [ <StepDependency>, ... ]        # NEW — `service` entries only;
                                               #       on jobEnvironments and an
                                               #       Environment Template's environment,
                                               #       never on stepEnvironments
runScope: [ TASK | SERVICE, ... ]              # NEW — which kinds of Session enter it;
                                               #       [TASK] by default when it lists a
                                               #       Service; never on stepEnvironments
# <EnvironmentActions> (§4.3), with WRAP_ACTIONS
onWrapServiceEnter / onWrapServiceRun / onWrapServiceHealthCheck / onWrapServiceExit
```

```yaml
<Service> ::= the object:
  name: <ServiceName>                         # an <Identifier>, not `File`
  description: <Description>                  # optional
  let: <LetBindings>                          # optional (job creation)
  dependencies: [ <StepDependency>, ... ]     # optional; Steps (complete) and Services (READY) first
  hostRequirements: <HostRequirements>        # optional
  ports: [ <ServicePort>, ... ]               # 1–10, unique names; { name, port?, protocol?: TCP | UDP }
  healthCheck: <ServiceHealthCheck>           # TCP_CONNECT (default, TCP ports only) | COMMAND | STDOUT
                                              #   readinessIntervalSeconds, readinessTimeoutSeconds,
                                              #   healthIntervalSeconds, failureThreshold
  restartPolicy: <ServiceRestartPolicy>       # maxAttempts (0), completedTasks (KEEP | RERUN;
                                              #   required when maxAttempts > 0)
  variables: <EnvironmentVariables>           # optional
  script:
    let: <LetBindings>                        # optional (service execution)
    actions: { onEnter?, onRun, onHealthCheck?, onExit? }
    embeddedFiles: [ <EmbeddedFile>, ... ]    # optional, Service.File.<name>
```

```yaml
<ServiceRequirement> ::= the object:          # Job Template only
  name: <ServiceName>                         # not also declared in `services`
  ports: [ { name: <Identifier>, protocol?: TCP | UDP }, ... ]   # 1–10, unique names
```

The **scope** of a Service declared in a Job Template is the set of Steps whose
Tasks depend on it, declared in the template's `dependencies` lists (§9.1): a
Step that lists `service: X` is in X's scope; a Service that lists `service: X`
contributes its own scope, transitively; a Job Environment that lists
`service: X` puts every Step in its scope, because every Step's Session enters
it; a Service that no Step, Service, or Job Environment lists is unused and
rejected. External Services are scoped by the same rules over the combined Job;
one that nothing lists is never started. The `dependencies`
of a template's Steps, Services, and Job Environments form one graph
(Step→Step, Step→Service, Service→Step, Service→Service), which must be
acyclic; a Job Environment that lists X adds an edge from every Step to X, so a
Service a Job Environment lists, directly or transitively, cannot depend on a
Step.

A Step, Service, or Job Environment may reference `Service.X.<port>.port` and
`.connectAddress` if and only if it lists `service: X` in its `dependencies`; a
Step's Step Environments share the Step's list, and X itself sees all three
values. The rule has no exceptions.

| Value | Type | In scope |
|---|---|---|
| `Service.<name>.<port>.port` | `int` | the declaring Service; Services, Steps (script and Step Environments), and Job Environments that list `service: <name>` in `dependencies`; a required Service follows the same rule, minus the declaring Service |
| `Service.<name>.<port>.connectAddress` | `string` | as `port` |
| `Service.<name>.<port>.bindAddress` | `string` | the declaring Service **only**; never for a required Service |
| `Service.File.<name>` | `path` | the declaring Service's script |
| `WrappedService.Name` / `.PortNames` / `.Ports` / `.BindAddresses` / `.Protocols` | `string` / `list[string]` / `list[int]` / `list[string]` / `list[string]` | the four `onWrapService*` hooks |

## RFC rules these tests verify

- **Extension gating**: `services`, `externalServices`, `runScope`,
  `dependencies` on an Environment, and the string functions
  `join_host_port`, `split_host_port`, `is_ipv4`, and `is_ipv6` require
  `SERVICE`; the `onWrapService*` hooks require both
  `WRAP_ACTIONS` and `SERVICE`; `SERVICE` requires `EXPR` (§9.9 item 7).
- **List shape and names** (§1.1 items 8–9, §1.2 item 6, §9 item 6, §9.2,
  §9.3, §9.8): 1–10 elements, unique names, identifiers that are not `File`; a
  requirement's name is not also declared inline. A `<Service>` has a closed
  set of properties; `serviceEnvironments` is rejected as an unknown property,
  and so are the keys `jobServices` (on either root) and `stepServices` (on a
  Step), which are not part of the schema.
- **`<StepDependency>` with `service`** (§3 item 4, §3.1, §3.2): a Step's
  `dependencies` may name Steps (`dependsOn`) and Services (`service`) in one
  list; an entry gives exactly one of the two keys (both, or neither, is
  rejected); a `service` entry must name a Service in `services` or
  `externalServices` (an unknown one is rejected), may not repeat within a
  list, and may name a required Service (satisfied when it is READY, scope
  unchanged; the listing is what lets the Step reference the required
  Service). Without SERVICE the `service` key is an unknown field. A Step's
  `name` may contain `:` as in the base specification; nothing is reserved
  (`Layer: Beauty` is a valid Step name beside a Service dependency).
- **Scope from dependencies** (§9.1): a Service listed by one Step, by two
  Steps, transitively through a Service that lists it, or by a Job
  Environment (every Step) is valid, as is a Step that lists a Service it
  never references; a Service that no Step, Service, or Job Environment lists
  is unused and rejected, whether or not it has dependencies of its own; list
  order carries no meaning, so a Service may depend on one listed after it.
- **Reference without dependency** (§9 scope rules 2–5, §9.9 item 1): a
  Step script, a Step Environment, a Service, a Job Environment, or an
  Environment Template's Environment that references `Service.X.*` without
  listing `service: X` is rejected, whether `X` is an inline or a required
  Service; the reference is not an implicit dependency.
- **Environment `dependencies`** (§4 item 3, §9.9 item 14): a Job Environment or an Environment Template's Environment may list
  Services in `dependencies`, every entry a `service` key naming a Service of
  the same document's `services` or the Job Template's
  `externalServices`, with no duplicates; a Step name, an unknown Service, a
  duplicate, a list on a `stepEnvironments` entry (which follows its Step's
  list), and a list together with an explicit `runScope` that includes
  `SERVICE` are each rejected. An Environment that lists a Service and gives
  no `runScope` defaults to `[TASK]`, whether or not it references the
  Service.
- **One acyclic graph** (§3.2 constraint 3, §9.9 item 10): cycles through
  Services only (two and three), through a Step and a Service (Step → Service
  X → Step), through a Step and two Services, and a Service that lists itself
  are rejected; so is a Service that a Job Environment lists, directly or
  through a Service that depends on it, and that depends on a Step, since the
  Job Environment puts every Step in its scope.
- **Service `dependencies`** (§9 item 4): same shape as a Step's; a Service
  may depend on Steps (complete first) and on Services (READY first, with or
  without referencing their endpoints); an entry must name a Step of the
  template or a Service other than itself; in an Environment Template every
  entry uses the `service` key and names a Service of the same document (a
  Step name is rejected); not empty.
- **`externalServices`** (§1.1 item 9, §9.8, §9.8.1): a requirement makes the
  listed ports' `port` and `connectAddress` available under the inline rule:
  to Steps (script and Step Environments), inline Services, and Job
  Environments that list `service: <name>` in `dependencies` (a Job
  Environment's default `runScope` is then `[TASK]`); a Step, inline Service,
  or Job Environment that references a required Service without listing it is
  rejected; never `bindAddress` or an unlisted port; an entry that nothing
  lists is rejected, like an unused inline Service; `ports` is
  required, 1–10, unique, names not `File`, with a `protocol` of `TCP`
  (default) or `UDP` and no port number; no other property; Job Template only.
- **Environment Template root** (§1.2): `$schema` and `extensions` accepted,
  `environment` optional, at least one of `environment` or `services`.
- **`runScope`** (§4 item 4): recognized names only, no duplicates, not empty;
  an Environment whose explicit `runScope` includes `SERVICE` neither lists
  nor references a Service; an Environment that lists a Service and gives no
  `runScope` defaults to `[TASK]` and is valid, and one that lists nothing
  defaults to every kind of Session. A `stepEnvironments` entry must not give
  `runScope` at all (constraint 4): a Step Environment is entered only by the
  Task Sessions of its Step.
- **Hooks follow `runScope`** (§4.3 `WRAP_ACTIONS` constraint 6): a wrapping
  Environment defines `onWrapEnvEnter`/`onWrapEnvExit` always, `onWrapTaskRun`
  iff `TASK`,
  and all four `onWrapService*` hooks iff `SERVICE`; a hook the `runScope` does
  not call for is rejected. A Service Session's stack (the Job Environments
  whose `runScope` includes `SERVICE`) holds at most one wrap layer.
- **Scope rules** (§7.3.1, §9, §9.9 items 1–2): a Service, inline or
  required, visible to the scripts and Step Environments of the Steps that
  list it, to the Services that list it, and to the Job Environments that
  list it;
  `bindAddress` only in the declaring Service; no `Service.*`
  in `hostRequirements`, `<Service>.let`, a Step's `let`, or an action
  `timeout`; `Task.*`, `Step.Name`, and a Step's `let` bindings never inside a
  Service; `Service.File.*` only in the declaring Service's script; types
  `int` / `string` / `path`.
- **Port protocol** (§9 item 6 constraint 4, §9.3 item 3, §9.9 item 8):
  `protocol` is `TCP` (default) or `UDP`, a case-sensitive literal that is not
  `@fmtstring`; two ports may share a `port` number only when their `protocol`
  differs.
- **Health check and restart** (§9 item 7, §9.4, §9.5, §9.9 item 4):
  `onHealthCheck` defined iff the type is `COMMAND`; every `TCP_CONNECT` port
  declared and TCP, defaulting to every TCP port; a Service none of whose
  ports is TCP must give a `STDOUT` or `COMMAND` check, so omitting
  `healthCheck` or giving `TCP_CONNECT` on it is rejected; a `STDOUT` check
  rejects `readinessIntervalSeconds`, and accepts `failureThreshold` only with
  `healthIntervalSeconds`; `readinessIntervalSeconds` is accepted on
  `TCP_CONNECT` as well as `COMMAND`; the keys `readinessCheck` and
  `timeoutSeconds` are unknown and rejected; ranges of `port`,
  `readinessIntervalSeconds`, `readinessTimeoutSeconds`, `healthIntervalSeconds`,
  `failureThreshold`, `maxAttempts`; `@fmtstring` numeric fields (all four
  health-check fields included) resolved at job creation in the
  `<Service>.let` scope with a whole-field `null` meaning "not provided";
  `completedTasks` is a literal enum, not `@fmtstring`, so a format string
  over a parameter is rejected at validation; `completedTasks` is required
  when `maxAttempts` is greater than 0 and may be omitted when it is 0 (§9.9
  item 12).
- **Extensions are per document** (§1.2 item 3): an Environment Template's
  `extensions` apply to that document only, so an attachment that declares
  `SERVICE` and `EXPR` may use `services`, `runScope`, and the §2.2.4 host/port
  functions while the Job Template it is applied to declares no extensions.
- **Expression Language §2.2.4**: `join_host_port`, `split_host_port`,
  `is_ipv4`, `is_ipv6` and their signatures.
- **Service names are per document** (§1.2.2 item 3): an attached
  Service may share its name with a Service in the Job Template's `services`
  or in another attached Environment Template; the submission is not rejected
  for it unless a requirement names it, the Job Template's `Service.*`
  references resolve to its inline Service, and the runner keeps same-named
  Services from different documents distinct.
- **Submission-time checks** (§1.2.2 items 2 and 4): each requirement matches
  exactly one attached Service of its name declaring every listed port with the
  same protocol (no provider, two providers, a missing port, or a protocol
  mismatch rejects the Job); a wrapping Environment from a document that does
  not declare `SERVICE` placed in `jobEnvironments` of a Job with any Service
  is rejected — the two checks that need the combined Job.
- **Lifecycle** (*How Jobs Are Run* § Services): READY before any Task of a
  Step in the scope, a Service READY before any Service that depends on it
  starts its Session and stopped after that Service is stopped, a Service
  that depends on Steps started only after they complete, a Service's Session
  spans exactly the Steps in its scope and ends when the last of them
  completes, a Service that lists another is stopped and started again in a
  new Service Session when that Service begins a new Service Session, Service
  Sessions
  enter the Job Environments whose `runScope` includes `SERVICE`, `onEnter` once
  per Session, `openjd_env` and `openjd_redacted_env` from `onEnter` reach
  `onRun`, `onHealthCheck`, and `onExit` (the latter setting the variable
  only with `REDACTED_ENV_VARS`, masked in the log regardless),
  `openjd_service_ready` honored only from `onRun`, `completedTasks: RERUN` vs
  `KEEP` on an instance failure, a ready timeout is an instance failure that
  cancels an in-flight `onHealthCheck`, the health check keeps probing after
  READY and `failureThreshold` consecutive failures (a `COMMAND` exiting
  non-zero, a `TCP_CONNECT` refused, a `STDOUT` heartbeat missed) make the
  instance UNHEALTHY, which is an instance failure taking the ordinary restart
  decision, while fewer failures change nothing and a `STDOUT` check without
  `healthIntervalSeconds` expects no heartbeat, a start failure consumes an
  attempt and relaunches in a new Service Session, `maxAttempts` exhaustion
  fails the scope whether before or after the first Task, a FAILED or
  failed-scope Service still runs `onExit` if any of its actions ran and not
  otherwise, a failing `onExit` does not fail the scope, and wrap hooks run in
  place of the Service's actions with `WrappedService.*` populated.

## How these tests are designed

The RFC motivates Services with Valkey, coordinators, and caches, but none of
those is needed to *test* the mechanism. The execution tests use small python
TCP listeners (`socket`, `http.server`), and one UDP datagram echo, standing in
for a service process,
Tasks that connect to them and print what they received, and sentinel markers
on stdout. Listeners probed by `TCP_CONNECT` or by an `onHealthCheck`
tolerate a connection that sends nothing and may close abortively, replying
only to a client that sent a request. The health-phase fixtures make a probe
start failing, or a heartbeat stop, from a Task or from the service itself
once Task 1 has been answered, and keep Task 1 running long enough for
`failureThreshold` probes at `healthIntervalSeconds: 1` to elapse before
Task 2 could be scheduled. The few fixtures that need state to
survive a Service Session, or to pass between Steps, use a file in the host's
temp directory (`tempfile.gettempdir()`) keyed by `Job.Name`, deleted by the
Service's `onExit` or by the consuming Task, and written so that a stale file
from an aborted run makes the fixture fail rather than pass; this assumes the
Service Sessions and Task Sessions of one run share a host, as the reference
runner's do. Nothing relies on a relaunch reusing the Service Session, which
the RFC leaves to the scheduler.

Fixtures that carry no `runOn` gate use `python`, the suite's portable
interpreter. The `bash` wrappers (adapted from the `WRAP_ACTIONS` suite) are
gated to `runOn: [posix]`; `service-wrap-service-hooks-python` is the
cross-platform variant.

## Layout

```
SERVICE/
├── README.md                       (this file)
├── job_templates/                  # Job template validation tests
│   │  # §1.1 services / externalServices, extension gating
│   ├── 1.1--external-services-minimal.yaml
│   ├── 1.1--external-services-ten.yaml
│   ├── 1.1--schema-field-accepted.yaml
│   ├── 1.1--services-minimal.yaml
│   ├── 1.1--services-ten.yaml
│   ├── 1.1--job-services-unknown-property.invalid.yaml
│   ├── 1.1--external-services-duplicate-name.invalid.yaml
│   ├── 1.1--external-services-empty-list.invalid.yaml
│   ├── 1.1--external-services-more-than-ten.invalid.yaml
│   ├── 1.1--external-services-without-service-extension.invalid.yaml
│   ├── 1.1--service-without-expr-no-services.invalid.yaml
│   ├── 1.1--service-without-expr.invalid.yaml
│   ├── 1.1--services-duplicate-name.invalid.yaml
│   ├── 1.1--services-empty-list.invalid.yaml
│   ├── 1.1--services-more-than-ten.invalid.yaml
│   ├── 1.1--services-without-service-extension.invalid.yaml
│   │  # §3 no Service list on a Step; §3.1 `:` in Step names allowed; §3.2 the `service` key
│   │  # §3.3.2 attr.worker.preemptible
│   ├── 3.1--step-name-with-colon-allowed.yaml
│   ├── 3.2--step-depends-on-step-and-service.yaml
│   ├── 3.3.2--attr-worker-preemptible-on-service.yaml
│   ├── 3.3.2--attr-worker-preemptible-on-step.yaml
│   ├── 3--step-services-unknown-property.invalid.yaml
│   ├── 3.2--service-key-without-service-extension.invalid.yaml
│   ├── 3.2--step-dependency-both-keys.invalid.yaml
│   ├── 3.2--step-dependency-no-keys.invalid.yaml
│   ├── 3.2--step-depends-on-same-service-twice.invalid.yaml
│   ├── 3.2--step-depends-on-unknown-service.invalid.yaml
│   │  # §4 Environment dependencies and runScope
│   ├── 4--environment-dependencies-service-form.yaml
│   ├── 4--environment-dependency-defaults-run-scope-task.yaml
│   ├── 4--run-scope-both.yaml
│   ├── 4--run-scope-default-no-reference-is-every-kind.yaml
│   ├── 4--run-scope-default-references-service-value.yaml
│   ├── 4--run-scope-service.yaml
│   ├── 4--run-scope-task-references-service-value.yaml
│   ├── 4--run-scope-task.yaml
│   ├── 4--step-environment-references-service.yaml
│   ├── 4--environment-dependencies-duplicate.invalid.yaml
│   ├── 4--environment-dependencies-step-name.invalid.yaml
│   ├── 4--environment-dependencies-unknown-service.invalid.yaml
│   ├── 4--environment-dependency-with-service-run-scope.invalid.yaml
│   ├── 4--environment-references-service-without-dependency.invalid.yaml
│   ├── 4--run-scope-both-references-service-value.invalid.yaml
│   ├── 4--run-scope-case-sensitive.invalid.yaml
│   ├── 4--run-scope-duplicate.invalid.yaml
│   ├── 4--run-scope-empty.invalid.yaml
│   ├── 4--run-scope-on-step-environment.invalid.yaml
│   ├── 4--run-scope-service-references-service-value.invalid.yaml
│   ├── 4--run-scope-unknown-name.invalid.yaml
│   ├── 4--run-scope-without-service-extension.invalid.yaml
│   ├── 4--step-environment-dependencies.invalid.yaml
│   │  # §4.3 hooks follow runScope; §4.3.1 WrappedService.*
│   ├── 4.3--non-wrapping-environment-not-subject-to-rule.yaml
│   ├── 4.3--wrap-default-run-scope-seven-hooks.yaml
│   ├── 4.3--wrap-run-scope-both-seven-hooks.yaml
│   ├── 4.3--wrap-run-scope-service-six-hooks.yaml
│   ├── 4.3--wrap-run-scope-task-three-hooks.yaml
│   ├── 4.3--wrap-step-environment-three-hooks.yaml
│   ├── 4.3.1--wrapped-action-in-service-hooks.yaml
│   ├── 4.3.1--wrapped-service-in-service-hooks.yaml
│   ├── 4.3.1--wrapped-service-lists-type-check.yaml
│   ├── 4.3--service-hooks-without-service-extension.invalid.yaml
│   ├── 4.3--service-hooks-without-wrap-actions.invalid.yaml
│   ├── 4.3--wrap-default-run-scope-missing-service-hooks.invalid.yaml
│   ├── 4.3--wrap-default-run-scope-missing-task-hook.invalid.yaml
│   ├── 4.3--wrap-run-scope-service-missing-env-hooks.invalid.yaml
│   ├── 4.3--wrap-run-scope-service-missing-one-service-hook.invalid.yaml
│   ├── 4.3--wrap-run-scope-service-with-task-hook.invalid.yaml
│   ├── 4.3--wrap-run-scope-task-with-service-hook.invalid.yaml
│   ├── 4.3--wrap-step-environment-with-service-hooks.invalid.yaml
│   ├── 4.3.1--wrapped-env-in-service-hook.invalid.yaml
│   ├── 4.3.1--wrapped-service-in-env-enter-hook.invalid.yaml
│   ├── 4.3.1--wrapped-service-in-own-on-enter.invalid.yaml
│   ├── 4.3.1--wrapped-service-in-task-hook.invalid.yaml
│   ├── 4.3.1--wrapped-service-ports-not-strings.invalid.yaml
│   ├── 4.3.1--wrapped-step-in-service-hook.invalid.yaml
│   │  # §7.3.1 / §9 scope rules
│   ├── 7.3.1--bind-address-in-own-service.yaml
│   ├── 7.3.1--service-dependency-chain-three.yaml
│   ├── 7.3.1--service-depends-on-earlier-service.yaml
│   ├── 7.3.1--service-depends-on-later-service.yaml
│   ├── 7.3.1--service-file-in-declaring-service.yaml
│   ├── 7.3.1--service-let-sees-params-and-job-name.yaml
│   ├── 7.3.1--service-port-int-arithmetic-type-checks.yaml
│   ├── 7.3.1--service-value-types.yaml
│   ├── 7.3.1--step-environment-sees-services.yaml
│   ├── 7.3.1--step-script-sees-service.yaml
│   ├── 7.3.1--bind-address-in-other-service.invalid.yaml
│   ├── 7.3.1--bind-address-in-step-script.invalid.yaml
│   ├── 7.3.1--bind-address-in-task-scoped-environment.invalid.yaml
│   ├── 7.3.1--service-connect-address-is-string-plus-int-type-error.invalid.yaml
│   ├── 7.3.1--service-file-in-step-script.invalid.yaml
│   ├── 7.3.1--service-file-of-other-service.invalid.yaml
│   ├── 7.3.1--service-in-service-host-requirements.invalid.yaml
│   ├── 7.3.1--service-in-service-let.invalid.yaml
│   ├── 7.3.1--service-in-step-action-timeout.invalid.yaml
│   ├── 7.3.1--service-in-step-host-requirements.invalid.yaml
│   ├── 7.3.1--service-port-is-int-string-method-type-error.invalid.yaml
│   ├── 7.3.1--service-port-plus-string.invalid.yaml
│   ├── 7.3.1--session-in-service-let.invalid.yaml
│   ├── 7.3.1--step-let-not-available-in-service.invalid.yaml
│   ├── 7.3.1--step-let-references-service.invalid.yaml
│   ├── 7.3.1--step-name-in-service.invalid.yaml
│   ├── 7.3.1--task-param-in-service.invalid.yaml
│   ├── 7.3.1--task-values-in-service.invalid.yaml
│   ├── 7.3.1--undeclared-port.invalid.yaml
│   ├── 7.3.1--undeclared-service.invalid.yaml
│   │  # Expression Language §2.2.4 host/port functions
│   ├── expr2.2.4--join-host-port-with-service.yaml
│   ├── expr2.2.4--is-ipv4-requires-service-extension.invalid.yaml
│   ├── expr2.2.4--is-ipv6-on-int.invalid.yaml
│   ├── expr2.2.4--is-ipv6-requires-service-extension.invalid.yaml
│   ├── expr2.2.4--join-host-port-requires-service-extension.invalid.yaml
│   ├── expr2.2.4--join-host-port-string-port.invalid.yaml
│   │  # Expression Language §2.2.6 repr_sh of integers
│   ├── expr2.2.6--repr-sh-int-requires-service-extension.invalid.yaml
│   ├── expr2.2.4--join-host-port-swapped-arguments.invalid.yaml
│   ├── expr2.2.4--split-host-port-requires-service-extension.invalid.yaml
│   │  # §9 <Service> structure and dependencies
│   ├── 9--dependencies-on-service.yaml
│   ├── 9--dependencies-on-step.yaml
│   ├── 9--dependencies-two-steps.yaml
│   ├── 9--ports-ten.yaml
│   ├── 9--service-all-fields.yaml
│   ├── 9--dependencies-cycle-step-service-service-step.invalid.yaml
│   ├── 9--dependencies-cycle-step-service-step.invalid.yaml
│   ├── 9--dependencies-cycle-via-job-environment-scope-transitive.invalid.yaml
│   ├── 9--dependencies-cycle-via-job-environment-scope.invalid.yaml
│   ├── 9--dependencies-empty.invalid.yaml
│   ├── 9--dependencies-on-self.invalid.yaml
│   ├── 9--dependencies-on-unknown-service.invalid.yaml
│   ├── 9--dependencies-unknown-step.invalid.yaml
│   ├── 9--ports-duplicate-name.invalid.yaml
│   ├── 9--ports-empty.invalid.yaml
│   ├── 9--ports-more-than-ten.invalid.yaml
│   ├── 9--service-environments-not-a-property.invalid.yaml
│   ├── 9--service-missing-on-run.invalid.yaml
│   ├── 9--service-missing-ports.invalid.yaml
│   ├── 9--service-unknown-field.invalid.yaml
│   │  # §9.1 scope from dependencies
│   ├── 9.1--scope-one-step-by-dependency.yaml
│   ├── 9.1--scope-via-job-environment-dependency.yaml
│   ├── 9.1--service-depended-on-by-two-steps.yaml
│   ├── 9.1--step-depends-on-service-without-reference.yaml
│   ├── 9.1--transitive-scope-via-dependent-service.yaml
│   ├── 9.1--service-dependency-cycle-three.invalid.yaml
│   ├── 9.1--service-dependency-cycle.invalid.yaml
│   ├── 9.1--service-references-service-without-dependency.invalid.yaml
│   ├── 9.1--step-environment-references-service-without-dependency.invalid.yaml
│   ├── 9.1--step-script-references-service-without-dependency.invalid.yaml
│   ├── 9.1--unused-service-with-own-dependencies.invalid.yaml
│   ├── 9.1--unused-service.invalid.yaml
│   │  # §9.2–§9.7 <ServiceName>, <ServicePort>, health, restart, script, actions
│   ├── 9.2--service-name-underscore-identifier.yaml
│   ├── 9.3--numeric-fields-from-param.yaml
│   ├── 9.3--port-arithmetic-on-literals-in-range.yaml
│   ├── 9.3--port-explicit-number.yaml
│   ├── 9.3--port-protocol-mixed-default-health-check.yaml
│   ├── 9.3--port-protocol-mixed-tcp-connect-names-tcp-port.yaml
│   ├── 9.3--port-protocol-same-number-tcp-and-udp.yaml
│   ├── 9.3--port-protocol-tcp-explicit.yaml
│   ├── 9.3--port-protocol-udp-with-stdout-health-check.yaml
│   ├── 9.4--health-command.yaml
│   ├── 9.4--health-numeric-fields-from-param.yaml
│   ├── 9.4--health-stdout-heartbeat-interval.yaml
│   ├── 9.4--health-stdout.yaml
│   ├── 9.4--health-tcp-connect-default-ports.yaml
│   ├── 9.4--health-tcp-connect-ports.yaml
│   ├── 9.4--health-tcp-connect-with-readiness-interval.yaml
│   ├── 9.5--max-attempts-zero-without-completed-tasks.yaml
│   ├── 9.5--restart-policy-keep.yaml
│   ├── 9.5--restart-policy-max-attempts-zero-explicit.yaml
│   ├── 9.6--script-let-requires-expr.yaml
│   ├── 9.7--service-actions-all-four.yaml
│   ├── 9.2--service-name-file.invalid.yaml
│   ├── 9.2--service-name-leading-digit.invalid.yaml
│   ├── 9.2--service-name-not-identifier.invalid.yaml
│   ├── 9.3--numeric-field-constant-out-of-range.invalid.yaml
│   ├── 9.3--numeric-field-references-service.invalid.yaml
│   ├── 9.3--numeric-field-references-session.invalid.yaml
│   ├── 9.3--port-above-range.invalid.yaml
│   ├── 9.3--port-arithmetic-on-literals-out-of-range.invalid.yaml
│   ├── 9.3--port-let-bound-out-of-range.invalid.yaml
│   ├── 9.3--port-name-file.invalid.yaml
│   ├── 9.3--port-name-not-identifier.invalid.yaml
│   ├── 9.3--port-not-integer.invalid.yaml
│   ├── 9.3--port-protocol-all-udp-default-health-check.invalid.yaml
│   ├── 9.3--port-protocol-all-udp-tcp-connect.invalid.yaml
│   ├── 9.3--port-protocol-lowercase.invalid.yaml
│   ├── 9.3--port-protocol-not-string.invalid.yaml
│   ├── 9.3--port-protocol-same-number-same-protocol.invalid.yaml
│   ├── 9.3--port-protocol-same-number-udp-twice.invalid.yaml
│   ├── 9.3--port-protocol-tcp-connect-names-udp-port.invalid.yaml
│   ├── 9.3--port-protocol-unknown-value.invalid.yaml
│   ├── 9.3--port-zero.invalid.yaml
│   ├── 9.4--health-command-readiness-interval-zero.invalid.yaml
│   ├── 9.4--health-command-without-on-health-check.invalid.yaml
│   ├── 9.4--health-default-with-on-health-check.invalid.yaml
│   ├── 9.4--health-missing-type.invalid.yaml
│   ├── 9.4--health-old-readiness-check-key.invalid.yaml
│   ├── 9.4--health-old-timeout-seconds-key.invalid.yaml
│   ├── 9.4--health-readiness-timeout-zero.invalid.yaml
│   ├── 9.4--health-stdout-failure-threshold-without-interval.invalid.yaml
│   ├── 9.4--health-stdout-readiness-interval.invalid.yaml
│   ├── 9.4--health-stdout-with-on-health-check.invalid.yaml
│   ├── 9.4--health-stdout-with-ports.invalid.yaml
│   ├── 9.4--health-tcp-connect-empty-ports.invalid.yaml
│   ├── 9.4--health-tcp-connect-undeclared-port.invalid.yaml
│   ├── 9.4--health-unknown-type.invalid.yaml
│   ├── 9.5--completed-tasks-format-string.invalid.yaml
│   ├── 9.5--completed-tasks-lowercase.invalid.yaml
│   ├── 9.5--completed-tasks-unknown.invalid.yaml
│   ├── 9.5--max-attempts-negative.invalid.yaml
│   ├── 9.5--max-attempts-not-integer.invalid.yaml
│   ├── 9.5--max-attempts-without-completed-tasks.invalid.yaml
│   ├── 9.6--embedded-files-empty.invalid.yaml
│   ├── 9.6--script-let-duplicate-name.invalid.yaml
│   ├── 9.6--service-let-shadows-script-let.invalid.yaml
│   ├── 9.7--service-action-empty-command.invalid.yaml
│   ├── 9.7--service-actions-unknown-action.invalid.yaml
│   │  # §9.8 <ServiceRequirement>
│   ├── 9.8--job-environment-references-required-service.yaml
│   ├── 9.8--required-port-protocol-udp.yaml
│   ├── 9.8--required-service-in-inline-service.yaml
│   ├── 9.8--required-service-in-job-environment.yaml
│   ├── 9.8--step-depends-on-required-service.yaml
│   ├── 9.8--external-service-unused.invalid.yaml
│   ├── 9.8--required-name-also-declared-inline.invalid.yaml
│   ├── 9.8--required-name-file.invalid.yaml
│   ├── 9.8--required-name-not-identifier.invalid.yaml
│   ├── 9.8--required-port-name-file.invalid.yaml
│   ├── 9.8--required-port-protocol-unknown.invalid.yaml
│   ├── 9.8--required-port-with-number.invalid.yaml
│   ├── 9.8--required-ports-duplicate-name.invalid.yaml
│   ├── 9.8--required-ports-empty.invalid.yaml
│   ├── 9.8--required-ports-missing.invalid.yaml
│   ├── 9.8--required-ports-more-than-ten.invalid.yaml
│   ├── 9.8--required-service-bind-address.invalid.yaml
│   ├── 9.8--required-service-in-host-requirements.invalid.yaml
│   ├── 9.8--required-service-undeclared-port.invalid.yaml
│   ├── 9.8--required-service-unknown-field.invalid.yaml
│   ├── 9.8--service-references-required-service-without-dependency.invalid.yaml
│   └── 9.8--step-references-required-service-without-dependency.invalid.yaml
├── env_templates/                  # Environment template validation tests
│   │  # §1.2 root, §1.2.2 Services from Environment Templates
│   ├── 1.2--environment-default-run-scope-references-service.yaml
│   ├── 1.2--environment-depends-on-service.yaml
│   ├── 1.2--environment-only-no-extensions.yaml
│   ├── 1.2--schema-field-accepted.yaml
│   ├── 1.2--schema-field-with-services.yaml
│   ├── 1.2--service-depends-on-earlier-service.yaml
│   ├── 1.2--service-depends-on-later-service.yaml
│   ├── 1.2--service-depends-on-service.yaml
│   ├── 1.2--service-references-job-name.yaml
│   ├── 1.2--services-and-environment.yaml
│   ├── 1.2--services-only.yaml
│   ├── 1.2--environment-depends-on-step-name.invalid.yaml
│   ├── 1.2--environment-only-references-service.invalid.yaml
│   ├── 1.2--environment-references-bind-address.invalid.yaml
│   ├── 1.2--environment-references-service-without-dependency.invalid.yaml
│   ├── 1.2--environment-references-undeclared-service.invalid.yaml
│   ├── 1.2--environment-service-run-scope-references-service.invalid.yaml
│   ├── 1.2--job-services-unknown-property.invalid.yaml
│   ├── 1.2--neither-environment-nor-services-no-extensions.invalid.yaml
│   ├── 1.2--neither-environment-nor-services.invalid.yaml
│   ├── 1.2--external-services-not-permitted.invalid.yaml
│   ├── 1.2--service-dependency-cycle.invalid.yaml
│   ├── 1.2--service-dependency-on-step-not-permitted.invalid.yaml
│   ├── 1.2--service-depends-on-unknown-service.invalid.yaml
│   ├── 1.2--service-in-environment-template-missing-on-run.invalid.yaml
│   ├── 1.2--service-references-service-without-dependency.invalid.yaml
│   ├── 1.2--service-references-step-name.invalid.yaml
│   ├── 1.2--service-without-expr.invalid.yaml
│   ├── 1.2--services-duplicate-name.invalid.yaml
│   ├── 1.2--services-empty-list-with-environment.invalid.yaml
│   ├── 1.2--services-empty-list.invalid.yaml
│   ├── 1.2--services-more-than-ten.invalid.yaml
│   ├── 1.2--services-without-service-extension.invalid.yaml
│   │  # §4 runScope
│   ├── 4--run-scope-service-environment.yaml
│   ├── 4--run-scope-duplicate.invalid.yaml
│   ├── 4--run-scope-unknown-name.invalid.yaml
│   ├── 4--run-scope-without-service-extension.invalid.yaml
│   │  # §4.3 / §4.3.1 wrap hooks
│   ├── 4.3--rfc0008-three-hooks-without-service-unchanged.yaml
│   ├── 4.3--services-and-wrapping-environment-compose.yaml
│   ├── 4.3--wrap-default-run-scope-seven-hooks.yaml
│   ├── 4.3--wrap-run-scope-service-six-hooks.yaml
│   ├── 4.3--wrap-run-scope-task-three-hooks.yaml
│   ├── 4.3.1--wrapped-service-in-service-hook-timing-fields.yaml
│   ├── 4.3.1--wrapped-service-in-service-hooks.yaml
│   ├── 4.3--service-hooks-without-service-extension.invalid.yaml
│   ├── 4.3--service-hooks-without-wrap-actions.invalid.yaml
│   ├── 4.3--wrap-default-run-scope-missing-service-hooks.invalid.yaml
│   ├── 4.3--wrap-run-scope-service-missing-service-exit.invalid.yaml
│   ├── 4.3--wrap-run-scope-service-with-task-hook.invalid.yaml
│   ├── 4.3--wrap-run-scope-task-with-service-hooks.invalid.yaml
│   ├── 4.3.1--wrapped-service-in-embedded-file.invalid.yaml
│   ├── 4.3.1--wrapped-service-in-env-exit-hook.invalid.yaml
│   ├── 4.3.1--wrapped-step-in-service-hook-timeout.invalid.yaml
│   │  # Expression Language §2.2.4 host/port functions gated on SERVICE
│   └── expr2.2.4--join-host-port-requires-service-extension.invalid.yaml
└── jobs/                           # End-to-end execution tests
    │  # Health checks before READY and the Service.* scope
    ├── service-command-health-check.test.yaml
    ├── service-dependency-chain.test.yaml
    ├── service-file-embedded.test.yaml
    ├── service-join-host-port-url.test.yaml
    ├── service-let-bindings-resolve.test.yaml
    ├── service-repr-sh-int.test.yaml
    ├── service-numeric-fields-from-param.test.yaml
    ├── service-ready-message-only-from-on-run.test.yaml
    ├── service-stdout-health-check.test.yaml
    ├── service-tcp-connect.test.yaml
    ├── service-udp-port-echo.test.yaml
    │  # Scope from dependencies, runScope default
    ├── service-dependencies-starts-after-step.test.yaml
    ├── service-dependency-without-reference.test.yaml
    ├── service-run-scope-default-follows-dependency.test.yaml
    ├── service-scope-one-step-each.test.yaml
    ├── service-scope-stopped-before-dependent-step.test.yaml
    ├── service-scope-transitive-via-dependent-service.test.yaml
    ├── service-scope-two-of-three-steps-state-persists.test.yaml
    ├── service-scope-via-job-environment-dependency.test.yaml
    │  # The Service Session
    ├── service-environments-follow-run-scope.test.yaml
    ├── service-on-enter-openjd-env-reaches-health-check.test.yaml
    ├── service-on-enter-openjd-env-reaches-on-run.test.yaml
    ├── service-on-enter-openjd-fail-exit-zero-is-start-failure.test.yaml
    ├── service-on-enter-openjd-redacted-env-with-extension.test.yaml
    ├── service-on-enter-openjd-redacted-env-without-extension.test.yaml
    ├── service-on-exit-failure-does-not-fail-scope.test.yaml
    ├── service-on-exit-runs-after-task-failure.test.yaml
    ├── service-on-run-openjd-fail-cancels-and-relaunches.test.yaml
    ├── service-session-is-its-own-session.test.yaml
    ├── service-stop-order-dependent-service-stopped-first.test.yaml
    │  # External Services (§1.2.2) and externalServices (§9.8)
    ├── service-external-client-environment-uses-service-functions.test.yaml
    ├── service-external-parameter-override.test.yaml
    ├── service-external-same-name-as-inline-service.test.yaml
    ├── service-external-same-name-both-consumed.test.yaml
    ├── service-external-same-name-in-two-attachments.test.yaml
    ├── service-external-services-only-attachment.test.yaml
    ├── service-external-task-scoped-client-environment.test.yaml
    ├── service-required-in-job-environment.test.yaml
    ├── service-required-satisfied-by-attachment.test.yaml
    │  # Failure and restart
    ├── service-dependent-restarts-when-upstream-gets-new-session.test.yaml
    ├── service-keep-max-attempts-exhausted-mid-scope.test.yaml
    ├── service-keep-relaunch.test.yaml
    ├── service-max-attempts-exhausted-task-never-runs.test.yaml
    ├── service-readiness-timeout-fails-scope.test.yaml
    ├── service-rerun-relaunch.test.yaml
    ├── service-start-failure-no-attempts-on-exit-not-run.test.yaml
    ├── service-start-failure-relaunches-in-new-session.test.yaml
    │  # Health checks after READY
    ├── service-health-command-fails-after-ready-relaunches.test.yaml
    ├── service-health-stdout-heartbeat-missed.test.yaml
    ├── service-health-stdout-no-heartbeat-configured.test.yaml
    ├── service-health-tcp-port-closed-while-process-hangs.test.yaml
    ├── service-health-threshold-tolerates-blips.test.yaml
    │  # WRAP_ACTIONS composition
    ├── service-wrap-env-hooks-wrap-inner-environment-in-service-session.test.yaml
    ├── service-wrap-service-hooks-python.test.yaml
    ├── service-wrap-service-scoped-hooks.test.yaml
    ├── service-wrapper-task-scoped-with-service.test.yaml
    │  # Runs the runner must reject
    ├── service-job-wrapper-with-external-service.invalid.test.yaml
    ├── service-max-attempts-exhausted.invalid.test.yaml
    ├── service-max-attempts-from-param-negative.invalid.test.yaml
    ├── service-port-from-param-out-of-range.invalid.test.yaml
    ├── service-port-from-string-param-not-integer.invalid.test.yaml
    ├── service-required-no-provider.invalid.test.yaml
    ├── service-required-protocol-mismatch.invalid.test.yaml
    ├── service-required-provider-missing-port.invalid.test.yaml
    ├── service-required-two-providers.invalid.test.yaml
    ├── service-scope-unused-service.invalid.test.yaml
    ├── service-without-expr.invalid.test.yaml
    ├── service-without-extension.invalid.test.yaml
    └── service-wrapper-without-service-declaration.invalid.test.yaml
```

## Semantics tested by the execution fixtures

- **Readiness gating** (*How Jobs Are Run* constraint 3): no Task of a Step
  that lists `service: <name>` in its `dependencies` runs before that Service
  is READY, under each of the three checks — `TCP_CONNECT` (`service-tcp-connect`), `STDOUT`
  (`service-stdout-health-check`), and `COMMAND` with `onHealthCheck`
  running concurrently with `onRun` (`service-command-health-check`).
  `openjd_service_ready` is honored only from `onRun`
  (`service-ready-message-only-from-on-run`). A `protocol: UDP` port is bound
  by a datagram listener that signals readiness through `STDOUT`, and the Task
  reaches it through the same `connectAddress` and `port` values a TCP port
  carries (`service-udp-port-echo`).
- **Start ordering** (constraint 2): a Service that depends on another
  (`service: Back`) starts only once that Service is READY, and may
  read its endpoint (`service-dependency-chain`).
- **Stop ordering** (constraint 4): a Service that depends on another is
  stopped first, so its `onExit` can still reach the upstream Service
  (`service-stop-order-dependent-service-stopped-first`).
- **Scope from dependencies** (§9.1, constraints 3, 4, 6, and 7): a Service
  that one Step lists is stopped, and its `onExit` run, once that Step
  completes, while a dependent Step outside the scope runs without the
  Service and is not ordered after its `onExit`
  (`service-scope-stopped-before-dependent-step`); two Services each listed
  by one Step are each scoped to their Step (`service-scope-one-step-each`);
  a Service listed by two of three Steps persists across them, holding state
  written by one for the other to read, and is stopped before the third Step,
  which does not list it, runs
  (`service-scope-two-of-three-steps-state-persists`); a Service listed only
  by a Job Environment's `dependencies` is up for every Step through that
  dependency alone, with the Tasks reading the variables the Environment set,
  and outlives them all (`service-scope-via-job-environment-dependency`); a
  Service listed
  only by another Service has that Service's scope, is READY before it
  starts, and is stopped after it
  (`service-scope-transitive-via-dependent-service`); a Step that lists a
  Service it never references is in its scope, so the Service is READY before
  the Task and stopped after it (`service-dependency-without-reference`); a
  Service that no Step, Service, or Job Environment lists is rejected before
  the Job is created (`service-scope-unused-service`).
- **Service `dependencies`** (§9 item 4, constraint 2): a Service that depends
  on a Step is not started until the Step has completed, and then serves the
  Step's output to the Step that depends on it
  (`service-dependencies-starts-after-step`).
- **`runScope` default** (§4 item 4): an Environment that lists a Service in
  `dependencies` without a `runScope` is entered in Task Sessions only, while
  one that lists nothing is entered in the Service Session too
  (`service-run-scope-default-follows-dependency`).
- **`Service.File.*` and `let`**: embedded files materialize into the Service
  Session and resolve through `<ServiceScript>.let`; `<Service>.let` resolves
  `Param.*` and `Job.Name` (`service-file-embedded`,
  `service-let-bindings-resolve`).
- **`join_host_port`** composes a URL authority from `connectAddress` and
  `port` (`service-join-host-port-url`); **`repr_sh`** of an `int` or
  `list[int]` is the decimal form, space-joined for a list, so a port or
  `WrappedService.Ports` needs no `string()` (`service-repr-sh-int`; without
  `SERVICE` the call is a type error,
  `expr2.2.6--repr-sh-int-requires-service-extension.invalid`).
- **Numeric `@fmtstring` fields** resolve at job creation; a whole-field `null`
  leaves the port to the runtime; out-of-range or non-integer resolutions are
  rejected at job creation (`service-numeric-fields-from-param`,
  `service-port-from-param-out-of-range`,
  `service-port-from-string-param-not-integer`,
  `service-max-attempts-from-param-negative`).
- **A Session of its own**: `Session.WorkingDirectory` is the Service
  Session's, distinct from the Task's; `OPENJD_SESSION_WORKING_DIR` is set
  (`service-session-is-its-own-session`).
- **Environments by `runScope`** ("Services run inside Environments"): the
  Service Session enters the Job Environments whose `runScope` includes
  `SERVICE`;
  Environment `variables` reach the Service's actions with the Service's own
  `variables` taking precedence (`service-environments-follow-run-scope`).
- **`openjd_env` within a Service** (§9.7): variables set by `onEnter` reach
  `onRun` and `onExit`, override declarative `variables`, and never propagate to
  Tasks (`service-on-enter-openjd-env-reaches-on-run`); they reach every
  `onHealthCheck` invocation of a `COMMAND` check too
  (`service-on-enter-openjd-env-reaches-health-check`).
  `openjd_redacted_env` from `onEnter` sets the variable for `onRun` and
  `onExit` only when the document declares `REDACTED_ENV_VARS`, and its value
  is masked in the log either way
  (`service-on-enter-openjd-redacted-env-with-extension`,
  `service-on-enter-openjd-redacted-env-without-extension`).
- **Session end** (constraints 6–7): a Service's Session is ended, and its
  `onExit` run, when the scope fails (`service-on-exit-runs-after-task-failure`,
  `service-max-attempts-exhausted-task-never-runs`); a failing `onExit` does not
  fail the scope (`service-on-exit-failure-does-not-fail-scope`); `onExit` is
  not run when no action of the Service ran, as when a SERVICE-scoped
  Environment's `onEnter` fails with no attempts left
  (`service-start-failure-no-attempts-on-exit-not-run`).
- **External Services** (§1.2.2): a services-plus-environment attachment
  publishes an endpoint to a Job Template that knows nothing of `SERVICE`; the
  attachment's parameters are Job Parameters; a services-only attachment whose
  Service nothing in the Job lists is accepted but the Service never starts
  (`service-external-task-scoped-client-environment`,
  `service-external-parameter-override`,
  `service-external-services-only-attachment`); the attachment's `extensions`
  gate the §2.2.4 host/port functions for its own `variables` while the Job
  Template declares none
  (`service-external-client-environment-uses-service-functions`).
- **Service names are per document** (§1.2.2 item 3): an attached
  Service named like an inline Service, or like another attachment's Service
  when nothing requires the name, is accepted; each document's Environment
  lists its own, so both start, each resolving its own `Service.<name>.*`
  (`service-external-same-name-as-inline-service`,
  `service-external-same-name-in-two-attachments`); with the RFC's Valkey Job
  Template and queue-cache attachment both declaring `Cache`, the Task's
  `Service.Cache.*` reaches the Job Template's Cache while the attached client
  Environment's `VALKEY_HOST` / `VALKEY_PORT` reach the queue's, on different
  ports, and neither answer leaks to the other consumer
  (`service-external-same-name-both-consumed`).
- **`externalServices`** (§1.1 item 9, §1.2.2 item 2, §9.8): a requirement
  satisfied by one attachment makes `Service.Ext.main.port` and
  `.connectAddress` resolve in the Task of a Step that lists `service: Ext`,
  and in a Job Environment of the Job Template that lists `service: Ext`, whose
  `runScope` then defaults to `[TASK]`, to the attached Service's endpoint
  (`service-required-satisfied-by-attachment`,
  `service-required-in-job-environment`); a Job whose requirement has no
  provider, two providers, a provider lacking the port, or a provider with the
  other protocol is rejected at submission (`service-required-no-provider`,
  `service-required-two-providers`,
  `service-required-provider-missing-port`,
  `service-required-protocol-mismatch`).
- **Failure and restart**: on an instance failure, `RERUN` cancels the running
  Task without counting a failure, relaunches `onRun`, and reruns completed
  Tasks against the new instance; `KEEP` lets the running Task finish and keeps
  completed results, gating only not-yet-started Tasks on the new instance
  (`service-rerun-relaunch`, `service-keep-relaunch`). Exhausting
  `maxAttempts` makes the Service FAILED and fails its scope, whether before
  any Task runs (`service-max-attempts-exhausted*`) or after some Tasks have
  completed, in which case the remaining Tasks never start and `onExit` runs
  (`service-keep-max-attempts-exhausted-mid-scope`). A ready timeout is an
  instance failure: the in-flight `onHealthCheck` is canceled, no Task runs,
  and `onExit` runs (`service-readiness-timeout-fails-scope`). An `openjd_fail`
  message from `onRun` is an instance failure in itself: the runtime cancels
  `onRun` — the instance never gets to print past it — and relaunches with the
  message as the reason (`service-on-run-openjd-fail-cancels-and-relaunches`);
  from `onEnter` the message fails the action whatever its exit status, a start
  failure that with `maxAttempts` 0 fails the scope while `onExit` still runs
  (`service-on-enter-openjd-fail-exit-zero-is-start-failure`). A start failure
  — a SERVICE-scoped Environment's `onEnter` exiting non-zero — consumes an
  attempt and the relaunch begins a new Service Session with a new working
  directory, re-entering the Environments and re-running `onEnter`
  (`service-start-failure-relaunches-in-new-session`). When an upstream
  Service begins a new Service Session, every Service that lists it is stopped
  and started again in a new Service Session once the upstream is READY;
  whether a relaunch after an instance failure reuses the Session is the
  scheduler's choice, so the fixture asserts that the dependent's `onEnter`
  ran as many times as the upstream's and that the Task served after the
  relaunch reached the upstream's new instance through the dependent
  (`service-dependent-restarts-when-upstream-gets-new-session`).
- **Health after READY** (§9.4, *How Jobs Are Run* constraint 11): the probe
  that proved readiness keeps running every `healthIntervalSeconds`, and
  `failureThreshold` consecutive failures make the instance UNHEALTHY, an
  instance failure that takes the ordinary restart decision. A `COMMAND` probe
  that starts exiting non-zero after Task 1 gets instance 1 canceled and, under
  `maxAttempts: 1` and `KEEP`, a second instance that serves the remaining Tasks
  (`service-health-command-fails-after-ready-relaunches`); a probe that fails
  twice and recovers under `failureThreshold: 3` changes nothing
  (`service-health-threshold-tolerates-blips`); a `TCP_CONNECT` probe refused
  by a process that closed its listener but is still running makes the
  instance UNHEALTHY, and with no attempts left the Job fails and `onExit` runs
  (`service-health-tcp-port-closed-while-process-hangs`); a `STDOUT` check with
  `healthIntervalSeconds` treats `openjd_service_ready` as a heartbeat and
  fails the instance when it stops (`service-health-stdout-heartbeat-missed`),
  while one without expects no heartbeat and a single ready line serves the
  whole Job (`service-health-stdout-no-heartbeat-configured`).
- **Wrap hooks** (§4.3 `WRAP_ACTIONS` constraint 6, §4.3.1): a SERVICE-scoped
  wrapping Environment's four `onWrapService*` hooks run in place of the
  Service's actions with `WrappedAction.*` and the parallel `WrappedService.*`
  lists; the
  wrapped `onRun`'s `openjd_service_ready` and the health check's exit status
  are recognized through the wrap script; `onWrapEnvEnter`/`onWrapEnvExit` wrap
  the inner Environments the Service Session enters; the wrapper is not entered
  for the Task (`service-wrap-service-scoped-hooks`,
  `service-wrap-env-hooks-wrap-inner-environment-in-service-session`,
  `service-wrap-service-hooks-python`). A TASK-scoped wrapper coexists with a
  Service (`service-wrapper-task-scoped-with-service`).
- **Submission-time wrapper check** (§1.2.2 item 4): a wrapping Environment
  from a document without `SERVICE`, placed in `jobEnvironments`, is rejected
  when the Job has any Service — attached to a Job declaring a Service, or in
  a Job submitted alongside an external Service
  (`service-wrapper-without-service-declaration`,
  `service-job-wrapper-with-external-service`).

## Running the tests

From the repo root:

```bash
# Run just the SERVICE extension tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/SERVICE

# Run only the job execution tests
uv run conformance-tests/run_openjd_cli_tests.py 2023-09/SERVICE/jobs

# Pattern-match a single scenario
uv run conformance-tests/run_openjd_cli_tests.py '*service*relaunch*'
```

## Writing your own runner

See the top-level [conformance README](../../README.md) for the standard
runner contract. The behavior specific to `SERVICE`:

1. When a template declares `extensions: [SERVICE, EXPR]`, the runner must
   accept `services`, `externalServices`, `runScope` on Job Environments,
   `dependencies` on a Job Environment (`service` entries only), and the
   `service: <name>` entry in every `dependencies` list, each entry giving
   exactly one of `dependsOn` and `service`; compute each Service's scope from
   those lists (§9.1: the Steps that list it, directly or through other
   Services, plus every Step when a Job Environment lists it); reject an unused
   Service or `externalServices` entry, a `Service.*` reference from a Step, Service, or Job Environment
   that does not list the dependency, a `dependencies` list or a `runScope` on
   a Step Environment, a `dependencies` entry on an Environment naming a Step,
   and a cycle in the combined Step/Service graph, in which a Job Environment
   that lists a Service adds an edge from every Step to it; and validate every
   `<Service>` and `<ServiceRequirement>` per Template Schemas §9.9. Without
   `SERVICE` it must reject those fields, the `service` key included; with
   `SERVICE` but without `EXPR` it must reject the template. `jobServices` and
   `stepServices` are unknown properties.
2. `openjd run` with `--env` must add an Environment Template's `services` to
   the Job as external Services, scoped by the same rules as inline ones over
   the combined Job and never started when nothing lists them, match each
   `externalServices` entry to exactly one attached Service of that name
   declaring the listed ports with the same protocols (§1.2.2 item 2,
   rejecting the run otherwise), apply the submission-time wrapper check of
   §1.2.2 item 4, treat the attachment's `parameterDefinitions` as Job
   Parameters, and keep a Service of one document distinct from a same-named
   Service of another (§1.2.2 item 3): a Job Template's `Service.*` references
   resolve to its own `services` and `externalServices`, and an Environment
   Template's within that document.
3. Before any Task of a Step runs, every Service whose scope includes the Step
   must be started in a Service Session of its own — after the Steps in its
   `dependencies` have completed and the Services in it are READY,
   entering the Job Environments whose `runScope` includes `SERVICE` (an
   Environment that lists a Service and gives no `runScope` is `[TASK]`),
   allocating its ports in each port's own `protocol` space,
   running `onEnter`, launching `onRun`, and probing it with its health check
   every `readinessIntervalSeconds` — and be READY.
   `Service.<name>.<port>.port` and `.connectAddress` must resolve in the
   Task's actions to an endpoint that reaches the process.
4. Once READY, the runner must keep probing every `healthIntervalSeconds`
   (`TCP_CONNECT` and `COMMAND`; `STDOUT` only when the field is given, as a
   heartbeat deadline for `openjd_service_ready`), count consecutive failures,
   reset the count on a success, and on `failureThreshold` failures mark the
   instance UNHEALTHY, cancel `onRun` by its cancelation method, wait for it to
   exit, and take the restart decision below.
5. An `onRun` exit while the scope has work, a ready timeout, or an UNHEALTHY
   instance is an instance failure governed by `restartPolicy`: relaunch up to
   `maxAttempts` times, applying `completedTasks`; otherwise fail the scope. A
   failure before `onRun` is launched (an Environment's or the Service's
   `onEnter` exiting non-zero) is a start failure that consumes an attempt and
   must be relaunched in a new Service Session. In every case the Service
   Session must be ended (`onRun` and any in-flight `onHealthCheck` canceled,
   `onExit` run if any action of the Service ran, Environments exited) when the
   scope completes or fails — that is, when no Step in the Service's scope has
   a Task left to run — a Service being stopped before any Service it depends
   on.
6. Under `WRAP_ACTIONS`, a wrapping Environment whose `runScope` includes
   `SERVICE` must run its `onWrapService*` hooks in place of the Service's
   actions with `WrappedAction.*` and `WrappedService.*` populated, scanning
   the wrap script's stdout for `openjd_*` messages.
