* Feature Name: Service
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: (pending)
* Start Date: 2026-09-17
* Specification Version: 2023-09 extension SERVICE
* Accepted On: (pending)
* Depends On:
  * RFC 0002, Model Extensions (https://github.com/OpenJobDescription/openjd-specifications/issues/57)
* Related:
  * Discussion #145, the idea thread for this RFC (https://github.com/OpenJobDescription/openjd-specifications/discussions/145)
  * Discussion #136 / Issue #133, Environment [Monitor] extension (https://github.com/OpenJobDescription/openjd-specifications/issues/133)

## Summary

This RFC proposes a new `<Service>` entity that runs a server process for one or more Steps of a
Job to connect to over the network. This lets a Job Template declare services that cache data or
coordinate concurrent workers while the Job is running.

A Job Template declares its Services in a `services` list alongside its Environments, and a Step
that uses one lists it in `dependencies`. The scheduler starts a Service before the Steps that
depend on it, waits for its health check to pass, and stops it when those Steps are done. A restart
policy says what happens if the server process dies.

A Step script uses format string substitution, through a new `Service.*` scope, to get the host
address and port numbers it needs to connect to a Service. The template names the ports; the
scheduler chooses the host and the numbers when it places the Service.

Services run inside the Job's Environments, so the same Conda, Rez, or container Environments that
provision the Tasks provision the Services too. A queue can supply a Service to every Job submitted
through it by defining the Service in an Environment Template.

## Overview

The `SERVICE` extension adds the following, each specified in the section linked:

* **Declaring a Service.** The `<Service>` entity and the `services` list that holds it, with its
  ports, health check, restart policy, and actions: [`<Service>`](#service).
* **Depending on a Service.** `dependencies` with the `service` key on Steps, Services, and Job
  Environments, which determines a Service's scope: [`<StepDependency>`](#stepdependency) and
  [Service scope](#service-scope).
* **Reading the endpoint.** The `Service.*` format-string scope and the `join_host_port` family of
  functions: [The `Service.*` scope](#the-service-scope) and
  [Modifications to the Expression Language](#modifications-to-the-expression-language).
* **Running a Service.** Lifecycle, failure, and restart rules, and how Services run inside the
  Job's Environments: [How Jobs Are Run](#modifications-to-how-jobs-are-run).
* **Environments and Services.** `runScope`, the kinds of Session an Environment is entered in, and
  the `onWrapService*` wrap hooks under `WRAP_ACTIONS`: [`<Environment>`](#environment).
* **Queue-supplied Services.** `services` in an Environment Template, and `externalServices` for a
  Job Template that reads such a Service's endpoint: [Environment Template](#environment-template)
  and [`<ServiceRequirement>`](#servicerequirement).
* **Validation.** An index of every rule the extension adds: [Validation](#validation).
* **`attr.worker.preemptible`**, a standard attribute capability not gated by the extension:
  [Host requirements](#host-requirements).

## Basic Examples

### A Valkey store shared across a Job's Tasks

This Job starts a single [Valkey](https://valkey.io/) in-memory data store before scheduling any
Task, and every Task connects to it to cache and coordinate intermediate results. The template
names one port, `main`, and lets the scheduler choose its number and host; the service process binds
`Service.Cache.main.bindAddress`, and Tasks on any host connect to `Service.Cache.main.connectAddress`.
Because a cache can be repopulated, a relaunch keeps completed Tasks' results.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [SERVICE, EXPR]
name: "Frame Processing With Shared Valkey Store"
parameterDefinitions:
  - name: FrameEnd
    type: INT
    default: 100

services:
  - name: Cache
    description: "A Valkey store the Job's Tasks share to cache and coordinate."
    hostRequirements:
      attributes:
        # Keep the service off capacity that could be reclaimed mid-Job.
        - name: attr.worker.preemptible
          anyOf: ["false"]
      amounts:
        - name: amount.worker.memory
          min: 8192
    ports:
      - name: main  # No number: the scheduler allocates one.
    healthCheck:
      # The TCP probe that proves readiness keeps running every 10 seconds; three
      # consecutive refused connections mark the instance UNHEALTHY and relaunch it.
      type: TCP_CONNECT
      readinessTimeoutSeconds: 60
      healthIntervalSeconds: 10
      failureThreshold: 3
    restartPolicy:
      maxAttempts: 3
      completedTasks: KEEP  # A cache can be repopulated; completed Tasks stand.
    script:
      actions:
        # onEnter runs once per Service Session; the Tasks never see this Conda environment.
        onEnter:
          command: bash
          args: ["-c", "conda create -y -p ./valkey-env -c conda-forge valkey && echo openjd_env: PATH=$PWD/valkey-env/bin:$PATH"]
        # onRun is the long-lived action: its process IS the service.
        onRun:
          command: valkey-server
          args:
            - "--port"
            - "{{ Service.Cache.main.port }}"
            - "--bind"
            - "{{ Service.Cache.main.bindAddress }}"
            - "--save"
            - ""
          cancelation:
            mode: NOTIFY_THEN_TERMINATE
            notifyPeriodInSeconds: 30

steps:
  - name: ProcessFrames
    dependencies:
      - service: Cache  # Puts the Step in the Service's scope and makes Service.Cache.* visible.
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "1-{{ Param.FrameEnd }}"
    script:
      actions:
        onRun:
          command: bash
          args: ["{{ Task.File.Run }}"]
      embeddedFiles:
        - name: Run
          type: TEXT
          data: |
            #!/usr/bin/env bash
            set -euo pipefail
            process-frame \
              --frame {{ Task.Param.Frame }} \
              --valkey-host '{{ Service.Cache.main.connectAddress }}' \
              --valkey-port {{ Service.Cache.main.port }}
```

### A coordinator that owns one Step's state

This Job prepares a scene in one Step and renders it in a second, where a pool of worker Tasks pull
tiles from a coordinator Service until none remain. The coordinator is told how many tiles there
are; the Step's parameter space sizes the pool.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [SERVICE, EXPR]
name: "Tiled Render With Coordinator"
parameterDefinitions:
  - name: SceneDir
    type: PATH
    objectType: DIRECTORY
    dataFlow: INOUT  # PrepareScene writes the scene here; the coordinator and workers read it.
    default: scene
  - name: TileCount
    type: INT
    default: 256
  - name: WorkerCount
    type: INT
    default: 16

services:
  - name: Coordinator
    dependencies:
      - dependsOn: PrepareScene  # Not started until the scene it hands out exists.
    ports:
      - name: api
      - name: metrics
    healthCheck:
      # Each probe is one run of onHealthCheck: every 5 seconds until READY, then every 30.
      type: COMMAND
      readinessTimeoutSeconds: 120
    restartPolicy:
      maxAttempts: 1
      completedTasks: RERUN  # In-memory state is lost on relaunch; prior results cannot be trusted.
    script:
      actions:
        # One-time initialization survives a relaunch of onRun.
        onEnter:
          command: coordinator
          args:
            - "init-db"
            - "--data-dir"
            - "{{ Session.WorkingDirectory }}/db"
            - "--scene"
            - "{{ Param.SceneDir }}"
            - "--tiles"
            - "{{ Param.TileCount }}"
        onRun:
          command: coordinator
          args:
            - "serve"
            - "--data-dir"
            - "{{ Session.WorkingDirectory }}/db"
            - "--listen"
            - "{{ join_host_port(Service.Coordinator.api.bindAddress, Service.Coordinator.api.port) }}"
            - "--metrics"
            - "{{ join_host_port(Service.Coordinator.metrics.bindAddress, Service.Coordinator.metrics.port) }}"
        onHealthCheck:
          command: python
          args:
            - "-c"
            - |
              import urllib.request
              urllib.request.urlopen("http://{{ join_host_port(Service.Coordinator.api.connectAddress, Service.Coordinator.api.port) }}/healthz", timeout=5)
        onExit:
          command: coordinator
          args: ["export-report", "--data-dir", "{{ Session.WorkingDirectory }}/db"]

steps:
  - name: PrepareScene
    script:
      actions:
        onRun:
          command: prepare-scene
          args: ["--out", "{{ Param.SceneDir }}"]
  - name: RenderTiles
    dependencies:
      - dependsOn: PrepareScene  # Must complete first.
      - service: Coordinator     # Must be READY first.
    parameterSpace:
      taskParameterDefinitions:
        # One Task per worker; each pulls tiles from the coordinator until none remain.
        - name: WorkerId
          type: INT
          range: "1-{{ Param.WorkerCount }}"
    script:
      actions:
        onRun:
          command: render-worker
          args:
            - "--coordinator"
            - "http://{{ join_host_port(Service.Coordinator.api.connectAddress, Service.Coordinator.api.port) }}"
            - "--scene"
            - "{{ Param.SceneDir }}"
            - "--worker-id"
            - "{{ Task.Param.WorkerId }}"
```

### A queue-supplied cache with client configuration

A scheduler can supply Services to every Job submitted through a queue by attaching an Environment
Template that defines a `services:` list. Here a queue administrator attaches a Valkey store and an
Environment that publishes its address through environment variables, so Tasks are configured for
the store without any Job Template knowing it exists.

```yaml
specificationVersion: "environment-2023-09"
extensions: [SERVICE, EXPR]
parameterDefinitions:
  - name: CacheMemoryMiB
    type: INT
    default: 8192
services:
  - name: Cache
    description: "A per-Job Valkey store shared by all of the Job's Tasks."
    hostRequirements:
      amounts:
        - name: amount.worker.memory
          min: 8192
    ports:
      - name: main
    restartPolicy:
      maxAttempts: 3
      completedTasks: KEEP
    script:
      actions:
        onRun:
          command: valkey-server
          args:
            - "--port"
            - "{{ Service.Cache.main.port }}"
            - "--bind"
            - "{{ Service.Cache.main.bindAddress }}"
            - "--maxmemory"
            - "{{ Param.CacheMemoryMiB }}mb"
environment:
  name: CacheClient
  description: "Tells every Task where the Job's Valkey store is."
  # Depending on the Service is what lets this Environment reference Service.Cache.*.
  dependencies:
    - service: Cache
  # An Environment that depends on a Service is entered in Task Sessions only.
  # This is the default for such an Environment; it is written out here only.
  runScope: [TASK]
  variables:
    VALKEY_HOST: "{{ Service.Cache.main.connectAddress }}"
    VALKEY_PORT: "{{ Service.Cache.main.port }}"
```

Every Task in every Job submitted through the queue starts with `VALKEY_HOST` and `VALKEY_PORT` set,
whether or not its Job Template has heard of the Service. This Job Template does not use the
`SERVICE` extension at all.

```yaml
specificationVersion: "jobtemplate-2023-09"
name: "Frame Processing With Queue Cache"

steps:
  - name: ProcessFrames
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "1-100"
    script:
      actions:
        onRun:
          command: bash
          args: ["{{ Task.File.Run }}"]
      embeddedFiles:
        - name: Run
          type: TEXT
          data: |
            #!/usr/bin/env bash
            set -euo pipefail
            # VALKEY_HOST and VALKEY_PORT are set by the queue's CacheClient environment.
            process-frame --frame {{ Task.Param.Frame }} \
              --valkey-host "$VALKEY_HOST" --valkey-port "$VALKEY_PORT"
```

A Job Template can instead read the queue's Service directly by declaring the Service's name and the
ports it uses in `externalServices`. `Service.Cache.*` is then available under the same rule as for
an inline Service, and the scheduler rejects a submission to a queue that does not attach a matching
Service. Only the parts that differ from the Valkey example's Job Template are shown.

```yaml
# The queue runs the Service; the template states only the contract.
externalServices:
  - name: Cache
    ports:
      - name: main

steps:
  - name: ProcessFrames
    dependencies:
      - service: Cache  # Makes Service.Cache.* visible to the Step, as for an inline Service.
    # parameterSpace and script as in the Valkey example; the script reads
    # {{ Service.Cache.main.connectAddress }} and {{ Service.Cache.main.port }}
```

### A spatial index served to a large query Step

A 1 TB aerial LIDAR scan is indexed once, by a Step on a host large enough to hold it, and the
index is served by a Service that loads it into memory and answers spatial queries over HTTP. The
query Step depends on the Service and not on the indexing Step, so its ten thousand small Tasks
never need the scan or the index on their hosts; they reach the index only through the API.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [SERVICE, EXPR]
name: "LIDAR Scan Queries"
parameterDefinitions:
  - name: ScanDir
    description: "The aerial LIDAR scan, about 1 TB of point cloud tiles."
    type: PATH
    objectType: DIRECTORY
    dataFlow: IN
  - name: IndexDir
    description: "Where BuildIndex writes the spatial index and the Service reads it."
    type: PATH
    objectType: DIRECTORY
    dataFlow: INOUT
    default: index
  - name: ResultsDir
    type: PATH
    objectType: DIRECTORY
    dataFlow: OUT
    default: results
  - name: GridSize
    description: "Queries run over a GridSize x GridSize grid of cells covering the scan."
    type: INT
    default: 100

services:
  - name: SpatialIndex
    description: "Answers spatial queries over the indexed scan."
    dependencies:
      - dependsOn: BuildIndex  # Holds no host until the index exists.
    hostRequirements:
      amounts:
        - name: amount.worker.memory
          min: 131072  # Holds the index in memory.
    ports:
      - name: api
    healthCheck:
      # Loading the index takes a while. The server prints "openjd_service_ready: loaded"
      # once it is answering queries; until then no query Task is scheduled.
      type: STDOUT
      readinessTimeoutSeconds: 3600
    restartPolicy:
      maxAttempts: 2
      completedTasks: KEEP  # The index on disk is unchanged by a relaunch; completed queries stand.
    script:
      actions:
        onRun:
          command: pointcloud-server
          args:
            - "--index"
            - "{{ Param.IndexDir }}"
            - "--listen"
            - "{{ join_host_port(Service.SpatialIndex.api.bindAddress, Service.SpatialIndex.api.port) }}"

steps:
  - name: BuildIndex
    hostRequirements:
      amounts:
        - name: amount.worker.memory
          min: 262144
        - name: amount.worker.disk.scratch
          min: 2048
    script:
      actions:
        onRun:
          command: pointcloud-index
          args: ["--scan", "{{ Param.ScanDir }}", "--out", "{{ Param.IndexDir }}"]
  - name: RunQueries
    dependencies:
      # The Service, not BuildIndex: these Tasks never touch the scan or the index.
      - service: SpatialIndex
    parameterSpace:
      taskParameterDefinitions:
        - name: CellX
          type: INT
          range: "1-{{ Param.GridSize }}"
        - name: CellY
          type: INT
          range: "1-{{ Param.GridSize }}"
    script:
      actions:
        onRun:
          command: pointcloud-query
          args:
            - "--server"
            - "http://{{ join_host_port(Service.SpatialIndex.api.connectAddress, Service.SpatialIndex.api.port) }}"
            - "--cell"
            - "{{ Task.Param.CellX }},{{ Task.Param.CellY }}"
            - "--grid"
            - "{{ Param.GridSize }}"
            - "--out"
            - "{{ Param.ResultsDir }}/cell_{{ Task.Param.CellX }}_{{ Task.Param.CellY }}.laz"
```

### Execution order

For a Job with one Service `S`, one `jobEnvironment` `E`, and one Step, which depends on `S`, with
Tasks `T1..Tn` running in two Sessions on two Worker Hosts, the scheduler proceeds:

```
Service host                   Worker host A            Worker host B
------------                   -------------            -------------
E.onEnter
  S.onEnter
  S.onRun (starts)
  S health probe -> READY
                               E.onEnter                E.onEnter
                                 T1.onRun                 T3.onRun
                                 T2.onRun                 T4.onRun
                               E.onExit                 E.onExit
  S.onRun (canceled)
  S.onExit
E.onExit
```

The Service runs in a Session of its own on the service host, inside the same Environment `E` that
the Tasks run in. No Task of a Step that depends on `S` is scheduled until `S` is READY.

## Motivation

Many parallel workloads depend on a shared, long-lived process that is not itself a unit of work:
an in-memory store that Tasks read from and write to, a coordinator that hands out work or
implements a barrier between phases, or an application "server mode" process (a DCC or renderer
listening on a port) that is expensive to start and is reused by many Tasks.

Today the only way to provide such a process is to deploy it as infrastructure outside the job:
stand up a host, run the daemon, and hard-code (or pass as a Job Parameter) its address. This puts a
dependency of the Tasks outside the job template, which is then no longer a self-contained, [tooling
parseable](https://github.com/OpenJobDescription/openjd-specifications/wiki/Design-Tenets)
description of the work. It also cannot be started and stopped with the Job, so it either runs
permanently or requires bespoke orchestration around every submission.

An `<Environment>` almost fits but differs in four ways that a schema needs to make first-class:

1. **Placement.** An Environment is entered on the host that runs the Tasks. A Service may run on a
   different host and be shared by Tasks spread across many hosts and Sessions.
2. **Lifetime.** An Environment's actions run to completion at Session start and end. A Service's
   main action runs for the *whole* lifetime of its scope, which is a set of Steps rather than one
   Session, and the scheduler must keep it alive across all of the scope's Sessions.
3. **Endpoint publication.** A Service exposes one or more ports. The runtime allocates a concrete
   address and port and makes them discoverable, on any host, both to the service process (so it
   knows what to bind) and to every entity in its scope (so they know where to connect).
4. **Readiness, health, and failure.** A scheduler must know when the service is accepting
   connections before it schedules the Tasks in the Service's scope, must notice when a running
   service stops answering, and must react when it dies or hangs: relaunch it, or fail the scope.
   Because a service can hold state that Tasks depend on, a service author must be able to say
   whether Tasks that completed against the old instance are still valid.

A Service borrows the rest of its shape from existing entities: `description`, `variables`, `let`,
embedded files, and the `<Action>` model with its cancelation methods from `<Environment>`, and
`hostRequirements` from `<StepTemplate>`.

A Service also needs what the Tasks need. The Valkey binary, the coordinator's Python environment,
or the renderer in server mode is provisioned today by the Job's Environments (a Conda or Rez
Environment, or a container under `WRAP_ACTIONS`), and a Service that could not use them would force
every Service author to reimplement that provisioning. Services therefore run inside the Job's
Environments, and wrapping Environments wrap Service actions as they wrap Task actions. An
Environment that configures Tasks to *use* a Service must then stay out of the Service's own
Session; `runScope` provides that, defaulting to Task Sessions for any Environment that depends on a
Service.

### Use cases

1. **Shared cache / data store.** A Valkey or Redis-compatible store that Tasks use to memoize
   expensive intermediate results (e.g. shared geometry or texture bakes) within a Job.
2. **Work coordination.** A service that divides a large, irregular work list among the Tasks of a
   Step, collects results, or implements a barrier so that a "gather" phase begins only when all
   "scatter" Tasks have checked in.
3. **Application server mode.** A renderer, DCC, or simulation engine started once in server mode on
   a large host, with many light Tasks submitting commands to it over its port. This amortizes
   scene load across Tasks in the same way an Environment does, but across hosts.
4. **Job-local infrastructure.** A license proxy, a metrics sink, or a small object store that
   exists only for the duration of one Job, so that the whole pipeline is described by the
   template and torn down with it.
5. **Queue-supplied infrastructure.** A studio attaches a Service to a queue so that *every* Job
   submitted there gets, for example, a per-Job license proxy or asset cache, without any Job
   Template author having to know how it is provisioned. An Environment in the same attachment can
   publish the endpoint to Tasks as environment variables or a configuration file, so even Job
   Templates written before the Service existed can use it.
6. **Rendezvous for distributed compute.** Frameworks such as MPI and Dask consist of worker
   processes that find each other through a small coordinator: a PMIx server for MPI ranks, the
   scheduler process for Dask workers. The coordinator is a Service; the workers are the Tasks of a
   Step, each connecting to the coordinator's endpoint and taking its identity (its rank) from a
   Task parameter. Running these workloads well also requires that the scheduler launch the Step's
   Tasks only once a threshold number of hosts is available for them, and that the Tasks' hosts can
   reach one another; both are outside this RFC (see [Future Work](#future-work)).

### Backward compatibility

This RFC is additive and gated by the `SERVICE` extension name declared under RFC 0002:

- `SERVICE` requires `EXPR`: a template that lists `SERVICE` MUST also list `EXPR`, and a scheduler
  MUST reject one that does not.
- No existing field changes meaning. One combination is newly rejected at submission: a wrapping
  Environment (RFC 0008) from a document without `SERVICE`, in a Job that has any Service
  ([Environment Template](#environment-template) item 4).
- The `$schema` and `extensions` keys on the Environment Template are not gated by `SERVICE`; they
  formalize what `openjd-model` already accepts. Environment Templates that omit both are unaffected.

## Specification

### Terminology

| Term | Definition |
|------|------------|
| **Scheduler** | The system that accepts Job and Environment Templates, creates Jobs from them, and dispatches Sessions and Services to Worker Hosts. |
| **Service** | An entity declared in a `services` list: a long-lived process that publishes one or more network ports and is kept alive by the scheduler for the lifetime of its scope. |
| **Scope** | The set of Steps whose Tasks depend on a Service, determined at template validation from the `dependencies` lists. See [Service scope](#service-scope). |
| **Service Session** | The Session on the service host in which a Service's actions run: a working directory, the Job's Environments whose `runScope` includes `SERVICE` entered around the Service's actions, and the Service's actions themselves. It is a Session as described in *How Jobs Are Run*, containing one Service instead of Tasks. |
| **Service host** | The Worker Host the scheduler places a Service on. It may or may not be a host that also runs Tasks. |
| **UNREADY / READY / UNHEALTHY / FAILED** | The four Service states the scheduler tracks. See [Service lifecycle](#service-lifecycle). |
| **Instance** | One launch of a Service's `onRun` action. A Service has one instance at a time; a restart creates a new instance. |
| **External Service** | A Service supplied to a Job by the scheduler from an Environment Template, rather than declared in the Job Template. A Job Template that reads an external Service's endpoint declares a **requirement** for it in `externalServices`. |
| **Inline Service** | A Service declared in the Job Template's own `services` list, as opposed to an external Service. |

### Schema modifications

> Changes to [the template schema](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas).

#### Job Template

> A modification to [`1.1. Job Template`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#11-job-template)

```diff
  specificationVersion: "jobtemplate-2023-09"
  $schema: <string> # @optional
  extensions: [ <ExtensionName>, ... ] # @optional
  name: <JobName> # @fmtstring
  description: <Description> # @optional
  parameterDefinitions:  [ <JobParameterDefinition>, ... ] # @optional
  jobEnvironments: [ <Environment>, ... ] # @optional
+ services: [ <Service>, ... ] # @optional @extension SERVICE
+ externalServices: [ <ServiceRequirement>, ... ] # @optional @extension SERVICE
  steps: [<StepTemplate>, ...]
```

New properties:

* *services* — The Services that the Jobs created from this Job Template run. See
  [`<Service>`](#service). Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Maximum number of elements: 10.
    3. No two Services in this list may have the same value for the `name` property.
    4. The `dependencies` of the Job Template's Steps and Services form one graph, which must be
       acyclic (see [`<StepDependency>`](#stepdependency)).
    5. See *externalServices* constraint 4.
    6. Every Service in this list has a non-empty scope (see [Service scope](#service-scope)).
* *externalServices* — The external Services (see [Environment Template](#environment-template))
  whose endpoints this Job Template reads directly, each with the ports it uses; the scheduler
  matches each at submission to exactly one attached Service of that name. See
  [`<ServiceRequirement>`](#servicerequirement). Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Maximum number of elements: 10.
    3. No two requirements in this list may have the same value for the `name` property.
    4. No requirement in this list may have the same `name` as a Service in *services*: a Service
       is either declared or required.
    5. Permitted only in a Job Template.

Extension list addition to item 3 (*extensions*): `SERVICE` (this RFC).

#### Environment Template

> A modification to [`1.2. Environment Template`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#12-environment-template)

```diff
  specificationVersion: environment-2023-09
+ $schema: <string> # @optional
+ extensions: [ <ExtensionName>, ... ] # @optional
  parameterDefinitions: [ <JobParameterDefinition>, ... ] # @optional
- environment: <Environment>
+ environment: <Environment> # @optional
+ services: [ <Service>, ... ] # @optional @extension SERVICE
```

New and changed properties:

* *$schema* — Ignored, as on the Job Template. Allowed for compatibility with JSON-editing IDEs.
* *extensions* — If provided, a non-empty list of extensions that this document uses, with the
  same available names as the Job Template. An extension listed here applies to the content of
  this document only; a Job Template does not need to list the extensions used by the Environment
  Templates a scheduler applies to it, and vice versa.
* *environment* — Now optional. The definition of an Environment that the Environment Template
  defines. When *services* is also provided, the Environment may list those Services in its
  `dependencies`, which makes their endpoints visible to it (see [`<Environment>`](#environment)).
* *services* — The Services that the Environment Template defines (see below). Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Maximum number of elements: 10.
    3. No two Services in this list may have the same value for the `name` property.
    4. The `dependencies` of the Services in this list form one graph, which must be acyclic.
    5. Every entry of a Service's `dependencies` uses the `service` key and names a Service in this
       list, since the document has no Steps.

At least one of *environment* or *services* must be provided.

**Services from Environment Templates.** An Environment Template that defines *services* defines
Services that the scheduler applies to every Job Template submitted through it, just as its
*environment* defines an Environment applied to every submission. From the Job Template's point of
view these are **external Services**. Each Job that uses an external Service gets its own instance
of it. An external Service's scope is computed over the combined Job by the same rules as an inline
Service's (see [Service scope](#service-scope)): typically the Environment defined alongside it lists
it, which puts every Step in its scope, or a Step of the Job Template lists it through
`externalServices`. An attached Service that nothing in the combined Job lists has an empty scope and
is never started; this is not an error, since the queue cannot know which Jobs will use it.

A `Service.*` reference resolves within its own document: in an Environment Template to the
document's *services*, in a Job Template to its *services* or *externalServices* (see
[The `Service.*` scope](#the-service-scope)). No reference crosses a document boundary except
through a requirement, so every `Service.*` reference in every template is checkable without
knowledge of the scheduler's configuration. A Job Template that reads an external Service's endpoint
declares a requirement for it in `externalServices` (see
[`<ServiceRequirement>`](#servicerequirement)).

When a submission combines a Job Template with one or more Environment Templates:

1. Every attached Service is part of the combined Job, and the attached Environments are placed in
   `jobEnvironments` as today. The limit of 10 applies to each document's list; the scheduler bounds
   the total through how many Environment Templates it attaches.
2. Each entry of `externalServices` MUST match exactly one Service with the same `name` among the
   attached Environment Templates' *services*, and that Service MUST declare every port the
   requirement lists, with the same `protocol`. If no attached Service has the name, if two or more
   do, if the matched Service lacks a listed port, or if a port's protocol differs, the submission
   MUST be rejected, naming the requirement and the cause. Matching uses the requirement alone; the
   scheduler reads nothing else from the Job Template.
3. Service names are per document. A Job Template's `Service.*` references resolve to its own
   `services` and `externalServices`, and an attached Service that happens to share a name with an
   inline Service is neither visible to the Job Template nor a conflict; it runs if the Environment
   defined alongside it lists it, and reaches the Job's Tasks through that Environment. Two attached
   Services with the same `name` are an error only when a requirement names it. A scheduler MUST
   keep same-named Services from different documents distinct (for example, by qualifying each with
   its document).
4. A wrapping Environment (RFC 0008) in a document that does not declare `SERVICE`, whether an
   attached Environment Template or the Job Template itself, has the default `runScope` and cannot
   define the `onWrapService*` hooks. Service Sessions enter the Job's `jobEnvironments` only, so if
   such an Environment is in the combined Job's `jobEnvironments` and the combined Job has any
   Service, the submission MUST be rejected, naming the document that defines the Environment as the
   cause. The remedy is for that document to declare `SERVICE` and either define the
   `onWrapService*` hooks or declare a `runScope` that excludes `SERVICE`. A wrapping Environment in
   a Step's `stepEnvironments` is never entered by a Service Session and is not subject to this
   check.

#### `<StepTemplate>`

> A modification to
> [`3. <StepTemplate>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#3-steptemplate)

The `<StepTemplate>` object is unchanged. One of its items changes under `SERVICE`:

* *dependencies* — The Steps and, with `SERVICE`, the Services this Step depends on; each entry is a
  [`<StepDependency>`](#stepdependency). The Step's Tasks may be scheduled only when every listed
  Step has completed successfully and every listed Service is READY. A Step need not repeat a Step
  dependency that a Service it lists already carries.

##### `<StepDependency>`

> A modification to
> [`3.2. <StepDependency>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#32-stepdependency)

A `<StepDependency>` names a Step or, with `SERVICE`, a Service that the entity listing it depends
on. It appears in the `dependencies` of a `<StepTemplate>`, of a [`<Service>`](#service), and of a
Job [`<Environment>`](#environment). It is one of:

```diff
  # <StepDependency> is one of:
  dependsOn: "<StepName>"
+ # or, with the SERVICE extension:
+ service: "<ServiceName>" # @extension SERVICE
```

Where:

1. *dependsOn* — The name of a Step in the same Job Template, as today. The dependency is satisfied
   when that Step has completed successfully.
2. *service* — The name of a Service of the same document's `services` or, in a Job Template, of its
   `externalServices`. The dependency is satisfied when the Service is READY. Listing a Service puts
   the listing entity in the Service's scope (see [Service scope](#service-scope)) and makes the
   Service's values visible to it (see [The `Service.*` scope](#the-service-scope)).

Constraints:

1. *dependsOn* MUST name a Step of the same Job Template, and *service* a Service of the same
   document's `services` or, in a Job Template, of its `externalServices`; neither may name the
   entity listing it.
2. No two entries of one `dependencies` list may name the same Step or the same Service.
3. The `dependencies` lists of a Job Template's Steps, Services, and Job Environments form one graph
   whose nodes are the Steps and Services and whose edges run from each entity to each entry in its
   list (Step to Step, Step to Service, Service to Step, and Service to Service), plus an edge from
   every Step to each Service a Job Environment lists (see [Service scope](#service-scope) rule 3).
   That graph MUST be acyclic; a template with a cycle is rejected at template validation, naming
   the cycle.
4. Exactly one of the two keys MUST be present; an entry that gives both, or neither, is a
   validation error.

#### `<Environment>`

> A modification to [`4. <Environment>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#4-environment)

```diff
  name: <EnvironmentName>
  description: <Description> # @optional
+ dependencies: [ <StepDependency>, ... ] # @optional @extension SERVICE
+ runScope: [ <RunScopeName>, ... ] # @optional @extension SERVICE
  script: <EnvironmentScript> # @optional
  variables: <EnvironmentVariables> # @optional
```

New properties:

* *dependencies* — The Services this Environment depends on, each a
  [`<StepDependency>`](#stepdependency) with the `service` key. Listing a Service puts every Step in
  its scope ([Service scope](#service-scope) rule 3). An Environment that lists a Service
  defaults to `runScope: [TASK]`. Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Every entry MUST use the `service` key and name a Service of the same document's
       `services` or, in a Job Template, of its `externalServices`.
    3. No two entries may name the same Service.
    4. Not permitted on a `stepEnvironments` entry, which follows its Step's *dependencies*.
    5. See *runScope* constraint 2.
* *runScope* — The kinds of Session this Environment is entered in. Every Session has exactly one
  kind, and an Environment is entered in a Session if and only if that Session's kind is in the
  Environment's *runScope*. `<RunScopeName>` is one of:
    * `TASK` — Sessions that run Tasks, the only kind that exists without the `SERVICE` extension.
    * `SERVICE` — Service Sessions, in which a Service's actions run (see
      [Services run inside Environments](#services-run-inside-environments)).

  If not provided, an Environment that lists any Service in its *dependencies* is entered in Task
  Sessions only, as if `runScope: [TASK]` were given, and any other Environment is entered in every
  kind of Session. An explicit list is exhaustive. Constraints:
    1. Minimum number of elements: 1. No name may appear more than once.
    2. An Environment whose *runScope* includes `SERVICE` MUST NOT list or reference any Service,
       since a Service Session may begin before any Service other than its own has an endpoint.
    3. An implementation MUST reject a `<RunScopeName>` it does not recognize.
    4. Not permitted on a `stepEnvironments` entry, which is entered only by its Step's Task
       Sessions.

> A modification to [`4.3. <EnvironmentActions>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#43-environmentactions)

```diff
  onEnter: <Action> # @optional
  onWrapEnvEnter: <Action>    # @optional @extension WRAP_ACTIONS
  onWrapTaskRun: <Action>     # @optional @extension WRAP_ACTIONS
  onWrapEnvExit: <Action>     # @optional @extension WRAP_ACTIONS
+ onWrapServiceEnter: <Action>       # @optional @extension WRAP_ACTIONS SERVICE
+ onWrapServiceRun: <Action>         # @optional @extension WRAP_ACTIONS SERVICE
+ onWrapServiceHealthCheck: <Action> # @optional @extension WRAP_ACTIONS SERVICE
+ onWrapServiceExit: <Action>        # @optional @extension WRAP_ACTIONS SERVICE
  onExit: <Action> # @optional
```

New properties, available only when both `WRAP_ACTIONS` (RFC 0008) and `SERVICE` are in use:

* *onWrapServiceEnter*, *onWrapServiceRun*, *onWrapServiceHealthCheck*, *onWrapServiceExit* — When
  this Environment is a wrapping Environment in a Service Session, these run instead of the
  Service's *onEnter*, *onRun*, *onHealthCheck*, and *onExit* respectively, exactly as
  `onWrapTaskRun` runs instead of a Task's `onRun`. Each receives the wrapped action's fields
  through the same `WrappedAction.*` variables RFC 0008 defines, plus a `WrappedService.*` group
  (the analogue of `WrappedEnv.Name` and `WrappedStep.Name`). As RFC 0008 established for
  `WrappedAction.*`, every one of these groups is in scope throughout the hook's `<Action>` — its
  `command` and `args`, and its `timeout` and `cancelation` fields, which resolve at run time (so a
  hook may forward `timeout: "{{WrappedAction.Timeout}}"`):

  | Variable | Type | Description |
  |---|---|---|
  | `WrappedService.Name` | `string` | The `name` of the Service being wrapped. |
  | `WrappedService.PortNames` | `list[string]` | The `name` of each of the Service's ports, in declaration order. |
  | `WrappedService.Ports` | `list[int]` | The allocated port number of each port, in the same order. |
  | `WrappedService.BindAddresses` | `list[string]` | The `bindAddress` of each port, in the same order. |
  | `WrappedService.Protocols` | `list[string]` | The `protocol` of each port (`TCP` or `UDP`), in the same order. |

  The four lists are parallel: index *i* of each describes the Service's *i*-th declared port. A
  wrapper that launches the service process in its own network namespace (a container without host
  networking) uses them to forward every port with its protocol; a Docker wrapper that restricts the
  host-side binding to the allocated interface passes
  `{{ flatten([['-p', join_host_port(WrappedService.BindAddresses[i], WrappedService.Ports[i]) + ':' + string(WrappedService.Ports[i]) + '/' + lower(WrappedService.Protocols[i])] for i in range(len(WrappedService.Ports))]) }}`
  in its `args`; the simpler form that binds every interface is shown in the wiki's §4.3.1.
  `WrappedService.Ports` is `list[int]`, and this RFC extends `repr_sh` to `int` and `list[int]`
  under `SERVICE` (see
  [Modifications to the Expression Language](#modifications-to-the-expression-language)), so a
  wrapper may pass the list as `repr_sh(WrappedService.Ports)` without converting each entry.

RFC 0008's rules extend to the new hooks as follows:

1. *The required hooks follow from `runScope`.* A wrapping Environment (one that defines any wrap
   hook) MUST define `onWrapEnvEnter` and `onWrapEnvExit`, since inner Environments are entered in
   every kind of Session; MUST define `onWrapTaskRun` if and only if its *runScope* includes `TASK`;
   and MUST define all four `onWrapService*` hooks if and only if its *runScope* includes `SERVICE`.
   A wrapping Environment in a Step's `stepEnvironments`, which has no *runScope*, therefore defines
   exactly RFC 0008's three hooks. A hook the *runScope* does not call for, or one it calls for that
   is missing, is a template validation error. For a wrapping Environment in a document that does
   not declare `SERVICE`, see [Environment Template](#environment-template) item 4.
2. *Stdout.* As in RFC 0008, the runtime scans the wrap script's stdout, so a wrapped *onEnter*'s
   `openjd_env` messages and a wrapped *onRun*'s `openjd_service_ready` message are honored when the
   wrap script forwards the wrapped process's stdout verbatim. `onWrapServiceHealthCheck` runs
   concurrently with `onWrapServiceRun` (see [Concurrency with `onRun`](#concurrency-with-onrun)).
3. *Failure.* A failed `onWrapServiceRun` is an instance failure, a failed `onWrapServiceEnter` is a
   start failure, and a failed `onWrapServiceExit` is an *onExit* failure, exactly as the wrapped
   action's failure would be. The exit status of an `onWrapServiceHealthCheck` invocation is one
   probe result, exactly as the wrapped *onHealthCheck*'s would be (see
   [`<ServiceHealthCheck>`](#servicehealthcheck)).
4. *Networking.* `bindAddress` and `connectAddress` are determined for the service host's network
   namespace. A wrapper that runs the service process in that namespace (a launcher, `ssh`, or a
   container with host networking) needs no port handling. A wrapper that gives the process its own
   network namespace MUST forward each port in `WrappedService.Ports` with the protocol in
   `WrappedService.Protocols`, so that a connection to `connectAddress`:`port` from any host in the
   scope reaches the process, and MUST ensure the process can bind `bindAddress` inside that
   namespace. A wildcard `bindAddress` (`0.0.0.0`, `::`) works in either case; a loopback
   `bindAddress` reaches a forwarded port only with host networking.

#### `<Service>`

> A new top-level section, inserted after
> [`8. <SimpleAction>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#8-simpleaction),
> renumbering *Additional Information* and *License* to sections 10 and 11.

Available when using the `SERVICE` extension.

A Service is a long-lived process that a scheduler starts before scheduling the Tasks in its
scope, keeps running for the lifetime of its scope, and stops once the scope no longer needs it.
A Service publishes one or more named network ports that the runtime allocates, and every
entity that depends on the Service can discover the resulting endpoint via the `Service.*`
format-string scope.

A `<Service>` is the object:

```yaml
name: <ServiceName>
description: <Description> # @optional
let: <LetBindings> # @optional @extension EXPR
dependencies: [ <StepDependency>, ... ] # @optional
hostRequirements: <HostRequirements> # @optional
ports: [ <ServicePort>, ... ]
healthCheck: <ServiceHealthCheck> # @optional
restartPolicy: <ServiceRestartPolicy> # @optional
variables: <EnvironmentVariables> # @optional
script: <ServiceScript>
```

Where:

1. *name* — The Service's identifier, the first component of `Service.*` references to it. See
   [`<ServiceName>`](#servicename).
2. *description* — A description to apply to the Service. It has no functional purpose, but may
   appear in UI elements.
3. *let* — An ordered list of expression bindings evaluated once, at job creation, like a
   `<StepTemplate>`'s *let*. Bindings may reference `Param.*`, `RawParam.*`, and `Job.Name`, but
   not `Session.*` or `Service.*`, which are not known until the Service is placed. Bound names are
   available in *hostRequirements*, *variables*, and *script*, as a Step's bindings are in its
   `stepEnvironments`. Available with the `EXPR` extension.
4. *dependencies* — The Steps and Services this Service depends on, each a
   [`<StepDependency>`](#stepdependency). The Service is started only once every entry is satisfied
   and is stopped before any Service it lists (lifecycle constraints 2 and 4). List a Step for a
   Service that consumes the output of a batch Step, so that it does not hold a host while the batch
   runs; the dependency orders the Service after the Step, and the Step's output reaches the service
   host as it reaches any later Step, through a `PATH` Job Parameter or other shared storage the
   scheduler provides. List a Service for one whose endpoint this Service reads. Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Each entry satisfies [`<StepDependency>`](#stepdependency) constraints 1 and 2.
    3. In the graph of [`<StepDependency>`](#stepdependency) constraint 3, a Service that lists a
       Step in its own scope, directly or through other Services, is a cycle; a Service that a Job
       Environment lists, directly or through other Services, has every Step in its scope and so can
       list no Step.
5. *hostRequirements* — Requirements on the Worker Host's capabilities that must be satisfied for
   the Service to be placed on the host. Amount capabilities are allocated to the Service Session
   for the lifetime of the Service. This is independent of the *hostRequirements* of any Step
   whose Tasks use the Service.
6. *ports* — The named ports that the Service exposes. See [`<ServicePort>`](#serviceport).
    1. Minimum number of elements: 1.
    2. Maximum number of elements: 10.
    3. No two ports may have the same `name`.
    4. No two ports with the same `protocol` may have the same `port` number; a service that speaks
       TCP and UDP on one number gives it explicitly on both ports, and ports whose `port` is not
       provided are allocated independently in each protocol's space.
7. *healthCheck* — The probe by which the scheduler determines that an instance of the Service is
   ready to accept traffic and, once it is, that it remains healthy. If not provided, defaults to
   `{ type: TCP_CONNECT }` applied to every TCP port. A Service none of whose ports is TCP MUST
   provide a *healthCheck* of type `STDOUT` or `COMMAND`; a `TCP_CONNECT` check, given or
   defaulted, would have no port to probe. See [`<ServiceHealthCheck>`](#servicehealthcheck).
8. *restartPolicy* — What the scheduler does when the Service's `onRun` action exits before the
   scope ends. If not provided, defaults to `{ maxAttempts: 0 }`: the Service is never relaunched,
   and its exit fails the scope. See [`<ServiceRestartPolicy>`](#servicerestartpolicy).
9. *variables* — A set of environment variable name/value pairs, with the values being Format
   Strings resolved when the Service is started, that are set in the process environment of every
   action of the Service's *script*, including *onHealthCheck*. It has the same schema as the
   *variables* property of
   [`<Environment>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#4-environment).
   Neither these variables nor those the Service's *onEnter* sets with `openjd_env` (see
   [`<ServiceActions>`](#serviceactions)) are propagated to the entities in the Service's scope.
10. *script* — The actions that the Service runs on its host. See
    [`<ServiceScript>`](#servicescript).

The format string scopes available to format strings within a `<Service>` are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters. `PATH`-typed `Param.*` values are
   available in the Service's *variables* and *script* (actions, embedded files, and
   `<ServiceScript>.let`), where they carry the service host's path mapping applied, exactly as in
   an Environment or Step Script; they are not available in `<Service>.let` or *hostRequirements*,
   which are resolved at job creation before a host is chosen.
2. `Session.*` — Values such as the Service Session's working directory. `Session.WorkingDirectory`
   refers to the Service Session's own working directory on the service host, not to the Session of
   any Task. A Service Session receives path mapping rules like any Session:
   `Session.HasPathMappingRules` and `Session.PathMappingRulesFile` describe the rules for the
   service host, and the rules file is written to the Service Session's working directory.
3. `Service.File.<name>` — The filesystem location of an embedded file defined within this
   Service's *script*. See [`<ServiceScript>`](#servicescript).
4. `Service.<name>.<port>.*` — The endpoint of this Service's own ports and, under the visibility
   rule in [The `Service.*` scope](#the-service-scope), of the Services this Service lists in its
   *dependencies*.
5. `Job.Name`.
6. Names bound by `let` in the `<Service>` and in the `<ServiceScript>`.

##### Service scope

The scope of a Service is the set of Steps whose Tasks depend on it. For a Service declared in a
Job Template it is determined at template validation from the template's `dependencies` lists; the
order of the `services` list carries no meaning:

1. A Step that lists Service `X` in its `dependencies` is in the scope of `X`.
2. When Service `Y` lists Service `X`, every Step in `Y`'s scope is in `X`'s scope. This applies
   transitively: a Step is in `X`'s scope when it depends on `X` through any chain of Services.
3. When any `jobEnvironments` entry lists Service `X` in its `dependencies`, every Step is in `X`'s
   scope, because every Step's Session enters a Job Environment. A Step Environment has no
   `dependencies` of its own; it follows its Step's.
4. A Service in whose scope no Step falls is unused, and the template MUST be rejected at template
   validation, naming the Service. A Service listed only by Services that are themselves unused is
   unused.

These rules apply to every Service of the combined Job, inline or external, with one difference:
rule 4 rejects an inline Service with an empty scope at template validation, while an external
Service with an empty scope is simply never started (see
[Environment Template](#environment-template)). An `externalServices` entry is subject to rule 4
like an inline Service: one that no Step, Service, or Job Environment of the Job Template lists is
rejected at template validation, naming the entry. A Service is started before any Task of a Step
in its scope and stopped once no such Task remains to be run (see
[Service lifecycle](#service-lifecycle)): one whose scope is one Step lives as long as that Step,
and one whose scope is every Step as long as the Job.

##### `<ServiceName>`

An [`<Identifier>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#71-identifier)
subject to the additional constraint that it MUST NOT be `File`, which is reserved for the
`Service.File.*` embedded-file references.

##### `<ServicePort>`

A `<ServicePort>` is the object:

```yaml
name: <Identifier>
port: <posinteger> | <posintstring> # @optional @fmtstring
protocol: enum("TCP", "UDP") # @optional
```

Where:

1. *name* — The name of the port. It is the second component of `Service.<service>.<port>.*`
   references. Must not be `File`.
2. *port* — If provided, the Service requires this specific port number on its host, in the space
   of the port's *protocol*; if the scheduler cannot provide it on the chosen host, that is a start
   failure (see [Failure and restart](#failure-and-restart)), and relocation to another host may
   succeed. If not provided, the runtime allocates an available port of the port's *protocol*.
   Range: 1–65535. Authors SHOULD omit this and let the runtime allocate, so that multiple Services
   and Sessions can share a host.
3. *protocol* — The transport protocol the service process binds the port with, and which the
   scheduler uses for any publishing or forwarding it performs to make the port reachable (a
   container port mapping, a firewall rule, a NAT entry). One of `TCP` or `UDP`. Default: `TCP`.

Every port, TCP or UDP, is bound and published on the same service host.

##### `<ServiceHealthCheck>`

A `<ServiceHealthCheck>` is one of the following objects, discriminated by *type*:

```yaml
type: "TCP_CONNECT"
ports: [ <Identifier>, ... ] # @optional
readinessIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

```yaml
type: "COMMAND"
readinessIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

```yaml
type: "STDOUT"
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

A health check is one probe mechanism applied in two phases. Before the instance is READY the probe
decides readiness: the first probe runs as soon as `onRun` is launched, a probe runs every
*readinessIntervalSeconds* after it, and the first success makes the instance READY. After the
instance is READY the probe decides health: a probe runs every *healthIntervalSeconds*, and
*failureThreshold* consecutive failures make the instance UNHEALTHY, which is an instance failure
(see [Failure and restart](#failure-and-restart)). A single successful probe resets the count. While
the count is below the threshold the instance stays READY and nothing changes. For `TCP_CONNECT` and
`COMMAND`, an interval is measured from the end of the previous probe. For a `STDOUT` heartbeat, the
runtime arms a deadline *healthIntervalSeconds* after the later of READY and the most recent
`openjd_service_ready` line; a line before the deadline is a successful probe and re-arms it, and a
deadline that passes without a line is a failed probe and arms the next.

Where:

1. *type* — The probe mechanism:
    * `TCP_CONNECT` — A probe succeeds when a TCP connection to each of the listed ports (by
      default, every TCP port the Service declares) succeeds. The connection is made from the
      service host to the allocated `port` on the loopback interface, or on `bindAddress` when it
      is not a wildcard address (`0.0.0.0` or `::`, which cannot be connected to on every operating
      system), and is closed immediately.
    * `COMMAND` — A probe is one invocation of the Service's *onHealthCheck* action (see
      [`<ServiceActions>`](#serviceactions)), run in the Service Session concurrently with `onRun`
      (see [Concurrency with `onRun`](#concurrency-with-onrun)), and succeeds when the invocation
      exits with status 0 while `onRun` is still running. The action's own `timeout` (default: 30
      seconds) bounds one invocation; an invocation that exceeds it is canceled and is one failed
      probe, as is any exit status other than 0. Neither is by itself a failure of the Service.
    * `STDOUT` — A probe is a line of the form `openjd_service_ready: <message>` written to stdout
      by the `onRun` action, with the same syntax as the other `openjd_*` messages. The first such
      line makes the instance READY; `<message>` has no functional purpose but MAY be surfaced in
      UIs. Later lines are heartbeat probes when *healthIntervalSeconds* is given (see the opening
      paragraph) and have no effect otherwise, the health of the instance then being that its
      `onRun` process is still running.
2. *ports* (`TCP_CONNECT` only) — The names of the ports to probe. Each must be declared in the
   Service's *ports* and have `protocol: TCP`; naming a UDP port is a validation error, since a
   UDP port cannot accept a connection. Defaults to every TCP port the Service declares.
3. *readinessIntervalSeconds* (`TCP_CONNECT` and `COMMAND` only) — Seconds between probes before
   the instance is READY. Default: 1 for `TCP_CONNECT`, 5 for `COMMAND`. A `STDOUT` check that
   gives this field MUST be rejected at template validation.
4. *readinessTimeoutSeconds* — The maximum time, measured from the launch of the `onRun` action,
   that the scheduler waits for the instance to become READY. It runs continuously, including while
   a probe is in progress. If exceeded, the instance has failed (see [Failure and
   restart](#failure-and-restart)). Default: 300.
5. *healthIntervalSeconds* — Seconds between probes after the instance is READY. Default: 30 for
   `TCP_CONNECT` and `COMMAND`. For `STDOUT` there is no default: when given, it is the heartbeat
   interval described under *type*; when omitted, no heartbeat is expected.
6. *failureThreshold* — The number of consecutive failed probes after READY (for a `STDOUT`
   heartbeat, consecutive intervals without a line) that make the instance UNHEALTHY. Default: 3.
   A `STDOUT` check that gives this field without *healthIntervalSeconds* MUST be rejected at
   template validation, since there is no probe for it to count.

The health check applies to every instance: after a restart, the new `onRun` must pass a probe
before Tasks in the scope are (re)scheduled, and is monitored in the same way once it has.

##### `<ServiceRestartPolicy>`

A `<ServiceRestartPolicy>` is the object:

```yaml
maxAttempts: <integer> | <intstring> # @optional @fmtstring
completedTasks: enum("KEEP", "RERUN") # @optional
```

Where:

1. *maxAttempts* — The maximum number of times the scheduler will relaunch the Service after an
   instance failure or a start failure (see [Failure and restart](#failure-and-restart)). The
   initial launch is not counted, so the default of 0 means the Service is launched exactly once
   and never relaunched. Must be 0 or greater.
2. *completedTasks* — What happens, when a new instance is launched, to Tasks in the Service's
   scope that completed successfully against a previous instance, and to Tasks that were running
   at the time. (Tasks not yet started are simply scheduled once the new instance is READY.)
    * `KEEP` — Completed Tasks remain complete, and running Tasks continue, failing and retrying
      on their own if the outage affects them. Use this when the Service holds no state that Tasks
      depend on, or state that Tasks can regenerate (a cache).
    * `RERUN` — Completed Tasks are returned to the scheduling queue and run again, and running
      Tasks are canceled and requeued without counting as a Task failure. Use this when the Service
      holds state that makes prior results unreliable once lost (a coordinator).

   If *maxAttempts* is greater than 0, *completedTasks* MUST be provided (for a *maxAttempts* given
   as a format string, checked when it is resolved at job creation). When *maxAttempts* is 0 it MAY
   be omitted, and then matters only when a Service this one lists begins a new Service Session (see
   [Failure and restart](#failure-and-restart), step 8). A Service may be suspended only if its
   *completedTasks* is `KEEP` (lifecycle constraint 9).

##### Numeric `@fmtstring` fields

> A new subsection of `9.5. <ServiceRestartPolicy>` in the wiki, since it governs the three objects above.

The numeric fields marked `@fmtstring` in the three objects above — `<ServicePort>.port`; the
`<ServiceHealthCheck>` fields `readinessIntervalSeconds`, `readinessTimeoutSeconds`,
`healthIntervalSeconds`, and `failureThreshold`; and `<ServiceRestartPolicy>.maxAttempts` — may be
given as a format string whose result is the integer, so that a Job Parameter or a `<Service>.let`
binding can supply them. They are resolved at job creation, with the scope of the `<Service>`'s *let*
([`<Service>`](#service) item 3). When the value is a single whole-field expression (`"{{ ... }}"`
with no surrounding text) its target type is `int?`: a `null` result is treated as if the field were
not provided, and a non-null result MUST satisfy the field's range.

##### `<ServiceScript>`

A `<ServiceScript>` is the object:

```yaml
let: <LetBindings> # @optional @extension EXPR
actions: <ServiceActions>
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional
```

1. *let* — An ordered list of expression bindings evaluated once, on the service host, when the
   Service is started; this is the host-context counterpart of the `<Service>`'s *let*, and may
   reference `Session.*`, `Service.File.*`, and in-scope `Service.<name>.<port>.*`. Bound names are
   available in *actions* and *embeddedFiles*.
2. *actions* — The actions to run at the different stages of the Service's lifecycle.
3. *embeddedFiles* — Files embedded into the Service that are materialized to the Service
   Session's working directory before each of the Service's actions runs. The path of an embedded
   file is available as `Service.File.<name>`.

##### `<ServiceActions>`

A `<ServiceActions>` is the object:

```yaml
onEnter: <Action> # @optional
onRun: <Action>
onHealthCheck: <Action> # @optional
onExit: <Action> # @optional
```

Where:

1. *onEnter* — A one-time setup action run before the first `onRun` of the Service in a Service
   Session; it runs once per Service Session, not once per instance. It is an ordinary action, like
   an Environment's `onEnter`: it runs to completion and its `timeout` and `cancelation` apply as
   for any `<Action>`. A non-zero exit or a timeout is a start failure (see [Failure and
   restart](#failure-and-restart)). Setup that must survive a relaunch of *onRun* belongs here.
2. *onRun* — The long-lived action whose process *is* the service. The scheduler starts it, probes
   it for readiness and then for health, and expects it to run until canceled; an exit before then
   is an instance failure (see [Failure and restart](#failure-and-restart)). The scheduler stops the
   Service by canceling *onRun* according to its `cancelation` method.
3. *onHealthCheck* — A short action the scheduler runs repeatedly, while *onRun* is running, as the
   probe of a `healthCheck` of type `COMMAND`; its exit status is the probe result (see
   [`<ServiceHealthCheck>`](#servicehealthcheck) and
   [Concurrency with `onRun`](#concurrency-with-onrun)). MUST be defined if and only if the health
   check type is `COMMAND`. It SHOULD be read-only with respect to the Service Session's working
   directory, which it shares with *onRun*.
4. *onExit* — A cleanup action run after the Service's other actions have stopped for the last
   time in a Service Session, whether the Service stopped normally, failed, or was canceled, and
   whether or not *onRun* was ever launched. It runs to completion. A non-zero exit is reported but
   does not change the outcome of the scope.

###### Concurrency with `onRun`

*onHealthCheck* is the only action in the specification that runs while another action of the
same Session, *onRun*, is running. Several existing rules silently assume one action at a time; the
following rules say where that assumption holds and where it does not:

1. **Embedded files.** Materializing embedded files for one action MUST NOT modify any file that a
   still-running action of the same Session was given. Implementations may either materialize each
   invocation's files to a distinct location, so that `Service.File.<name>` resolves to a different
   path in each invocation, or materialize them once to one path and leave them in place, which is
   safe because their content is constant: a Service Session's format-string values do not change
   for its lifetime. Either way, a file materialized for one action MUST remain in place, unchanged,
   until the Service Session ends: materializing a later action's files never removes or replaces
   an earlier action's. A path that *onEnter* captured (for example by exporting
   `Service.File.<name>` with `openjd_env`) therefore stays valid for *onRun* and *onExit*, even
   when their own `Service.File.<name>` resolves elsewhere.
2. **Stdout.** The stdout of *onHealthCheck* is captured to the log but no `openjd_*` message on
   it is honored: its result is its exit status.
3. **Log attribution.** Every line of stdout or stderr captured in a Service Session MUST be
   attributable to the action that produced it. How attribution is recorded is
   implementation-defined: a structured log may carry the action name as a field, and an
   implementation producing a single plain-text log SHOULD tag each *onHealthCheck* line with the
   action name (for example, `[onHealthCheck] connection refused`) while leaving *onRun*'s lines
   untagged. The same applies under `WRAP_ACTIONS`, where the wrap script's own output is also part
   of each stream. An implementation MAY suppress or collapse the output of invocations that succeed,
   provided the full output of every invocation that fails or is canceled for exceeding its
   `timeout` is retained.
4. **At most one invocation at a time.** *onHealthCheck* invocations never overlap one another and
   never run while *onEnter* or *onExit* is running.
5. **`onRun` exit wins.** An invocation in progress when *onRun* exits is canceled and its result
   discarded (lifecycle constraint 10); one in progress when the Service Session ends is canceled
   before *onExit* runs.
6. **Wrap hooks.** Under `WRAP_ACTIONS`, `onWrapServiceHealthCheck` runs while `onWrapServiceRun`
   is running. Wrap scripts used in a Service Session MUST tolerate concurrent invocation. Wrappers
   that execute into an existing context (`docker exec`, `ssh`) do; a wrapper that creates a
   per-invocation exclusive resource does not.

Default timeouts for these actions (extending the table in `<Action>`):

| Action container | Action | Default |
|---|---|---|
| `<ServiceActions>` | `onEnter` | *no timeout* |
| `<ServiceActions>` | `onRun` | *no timeout* (a timeout, if given, is measured from launch and its expiry is an instance failure) |
| `<ServiceActions>` | `onHealthCheck` | 30 seconds |
| `<ServiceActions>` | `onExit` | 300 seconds (five minutes) |

Implementations MUST watch the stdout of *onEnter*, *onRun*, and *onExit* for the standard
`openjd_status`, `openjd_progress`, and `openjd_fail` messages, and the stdout of *onRun* for
`openjd_service_ready` when the health check's *type* is `STDOUT` (for *onHealthCheck*, see
[Concurrency with `onRun`](#concurrency-with-onrun) rule 2). An `openjd_fail` message on *onRun*'s
stdout is itself an instance failure: the runtime MUST cancel *onRun* at once with its `cancelation`
method, as it does an UNHEALTHY instance, and the message is the failure's reason (see
[Failure and restart](#failure-and-restart) step 2). An `openjd_fail` message on *onEnter*'s or
*onExit*'s stdout marks that action failed when it exits, whatever its exit status — a start failure
or an *onExit* failure respectively — and the message is that failure's reason. (The base
specification says only that `openjd_fail` "indicates why an Action has failed"; existing runtimes
already fail an action that emits it regardless of exit status, and this RFC states the rule for
Service actions so that the three actions behave alike.)

The environment variables that *How Jobs Are Run* defines for every Session, currently
`OPENJD_SESSION_WORKING_DIR`, are set in the process environment of every action of a Service
Session with their usual meanings; the working directory is the Service Session's own.

**Environment variables within a Service.** Implementations MUST additionally watch the stdout of
*onEnter* for `openjd_env`, `openjd_redacted_env`, and `openjd_unset_env`, with the same syntax and
redaction rules as for an Environment's `onEnter`, including that `openjd_redacted_env` sets the
variable only when the document declares the `REDACTED_ENV_VARS` extension, while its value is
redacted from the log regardless. A variable set this way is set in the process environment of every
subsequent action of the same Service Session — every instance of *onRun*, *onHealthCheck*, and
*onExit* — and is retained across relaunches of *onRun* within the Session (for precedence, see
[Services run inside Environments](#services-run-inside-environments)). These messages are ignored
when emitted by *onRun*, *onHealthCheck*, or *onExit*.

##### `<ServiceRequirement>`

> A new section under `9. <Service>`, with `<ServiceRequirementPort>` as its subsection.

Available when using the `SERVICE` extension, in a Job Template's `externalServices` only.

A `<ServiceRequirement>` declares that the Job Template reads the endpoint of an external Service
(see [Environment Template](#environment-template)): a Service that an attached Environment
Template defines, named `name`, with at least the ports listed. It is the Job Template's half of a
contract the scheduler checks at submission, and it makes the Service's endpoint available to the
template's format strings without the template declaring the Service itself.

A `<ServiceRequirement>` is the object:

```yaml
name: <ServiceName>
ports: [ <ServiceRequirementPort>, ... ]
```

Where:

1. *name* — The `name` of the external Service required. See [`<ServiceName>`](#servicename) and the
   Job Template's *externalServices* constraint 4.
2. *ports* — The ports of the Service that the Job Template uses. See
   [`<ServiceRequirementPort>`](#servicerequirementport). Constraints:
    1. Minimum number of elements: 1.
    2. Maximum number of elements: 10.
    3. No two ports may have the same `name`.

The scheduler matches each requirement at submission ([Environment Template](#environment-template)
item 2). An entry puts nothing in the Service's scope by itself; a Step, Service, or Job Environment
that uses the Service lists it in `dependencies` as it would an inline Service, and an entry that
nothing lists is rejected at template validation ([Service scope](#service-scope) rule 4).

###### `<ServiceRequirementPort>`

A `<ServiceRequirementPort>` is the object:

```yaml
name: <Identifier>
protocol: enum("TCP", "UDP") # @optional
```

Where:

1. *name* — The `name` of a port the external Service declares. It is the second component of
   `Service.<service>.<port>.*` references. Must not be `File`.
2. *protocol* — The transport protocol the Job Template expects the port to carry, matched against
   the attached Service's port at submission ([Environment Template](#environment-template) item 2).
   One of `TCP` or `UDP`. Default: `TCP`.

#### Host requirements

> A modification to the attribute capability table in
> [`3.3.2.1. <AttributeCapabilityName>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#3321-attributecapabilityname)

```diff
  |**Capability Name**|**Values**|**Description**|
  |---|---|---|
  |attr.worker.os.family|linux, windows, macos|The family of operating system on the host.|
  |attr.worker.cpu.arch |x86_64, arm64|The architecture of the CPUs on the host.|
+ |attr.worker.preemptible|true, false|Whether the host's capacity may be reclaimed by the infrastructure provider while work is running on it (for example, EC2 Spot Instances). A host that does not advertise this attribute has an unknown value; a requirement of `anyOf: ["false"]` does not match such a host.|
```

This attribute is not gated by the `SERVICE` extension; it is a reserved standard name that any Step
may require, and Workers SHOULD advertise it. This RFC introduces it because a long-lived Service is
the first entity in the specification whose correctness depends on not being preempted mid-scope.

#### Format strings

> A modification to
> [`7.3.1. Value References`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#731-value-references)

##### The `Service.*` scope

New value references, all annotated `@fmtstring[host]` because a Service's endpoint is not known
until the scheduler places the Service, and may change if the Service is relocated:

| Value | Type | Description | Scope |
|---|---|---|---|
| `Service.<name>.<port>.port` | `int` | The port number allocated (or requested) for port `<port>` of Service `<name>`, in the space of that port's `protocol`. The same number is used for binding and for connecting. | Within the declaring Service, and within every entity that depends on it, per the rules below. |
| `Service.<name>.<port>.bindAddress` | `string` | The interface address the service process MUST bind to so that entities in the Service's scope can reach it. Typically `0.0.0.0` (or `::`) for a distributed scheduler and `127.0.0.1` for a single-host runner. | Within the declaring Service only; never for a required external Service. |
| `Service.<name>.<port>.connectAddress` | `string` | The hostname or IP address that entities in the Service's scope use to reach it. See [Address forms](#address-forms). | Within every entity that depends on the Service, per the rules below. Also within the declaring Service, for self-reference (e.g. to print its own URL). |
| `Service.File.<name>` | `path` | The filesystem location to which the Service embedded file with key `<name>` has been written. | Within the Service Script actions and embedded files of the declaring Service. |

A Step, Service, or Job Environment may reference `Service.<name>.<port>.port` and
`Service.<name>.<port>.connectAddress` if and only if it lists `service: <name>` in its
`dependencies`; a Step's Step Environments share the Step's list, and the Service `<name>` itself
sees all three values. For a required Service, `<port>` must be one the requirement lists. In
detail, `Service.<name>.<port>.*` for a Service `<name>` declared in the document's `services` or,
in a Job Template, declared by an entry of `externalServices`, is in scope in:

1. The Service `<name>` itself (all three values), when it is declared in `services`.
2. Any Service in the same `services` list that lists `service: <name>` in its `dependencies`
   (`port` and `connectAddress` only): its actions, *variables*, embedded files, and
   `<ServiceScript>.let`.
3. In a Job Template, any Step that lists `service: <name>` in its `dependencies`: its `script`
   (actions, embedded files, `let`) and each of its `stepEnvironments` entries (*variables*,
   actions, embedded files, `let`).
4. In a Job Template, any `jobEnvironments` entry that lists `service: <name>` in its `dependencies`
   (*variables*, actions, embedded files, `let`), whether `<name>` is inline or required.
5. In an Environment Template: the document's `environment` when it lists `service: <name>` in its
   `dependencies`.

A reference from a Step, Service, or Job Environment that does not list the dependency is a
validation error, whether the Service is inline or required, and the message SHOULD name the fix:
for example, *Step 'Render' references `Service.Cache.main.port` but does not list `service: Cache`
in `dependencies`*.

`Service.*` is never in scope in a field resolved at job creation, before any Service is placed: a
`hostRequirements` object, neither a Step's nor a Service's; a `<Service>`'s or a `<StepTemplate>`'s
`let`; an `<Action>`'s `timeout`; a cancelation method's `notifyPeriodInSeconds`; and the
[numeric `@fmtstring` fields](#numeric-fmtstring-fields) of `<ServicePort>`, `<ServiceHealthCheck>`,
and `<ServiceRestartPolicy>`.

A template that references a `Service.*` value outside the scopes above, or that references a
Service or port name that it neither declares nor requires, is invalid and MUST be rejected before
the Job is created.

###### Address forms

`bindAddress` and `connectAddress` are each a hostname, an IPv4 literal, or an IPv6 literal, in bare
form: an IPv6 literal is never bracketed. Schedulers SHOULD provide a hostname for `connectAddress`
when one resolves from every host in the Service's scope. Wherever an address and a port are joined
into one string (a URL authority, a `--listen host:port` flag) an IPv6 literal must be bracketed, so
templates MUST compose such strings with `join_host_port` (see [Modifications to the Expression
Language](#modifications-to-the-expression-language)) rather than `{{ addr }}:{{ port }}`.

##### Template processing stages

> A modification to
> [`7.4. Template Processing Stages`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#74-template-processing-stages)

`Service.*` values are unknown at template validation and at job creation, and known at task
execution (and at service execution, for the Service's own actions). They type-check as
`unresolved[int]`, `unresolved[string]`, and `unresolved[path]` at the earlier stages. A
`<Service>`'s *let* is evaluated at job creation, with `<StepTemplate>` bindings; a
`<ServiceScript>`'s *let* is evaluated at service execution on the service host, as
`<EnvironmentScript>` and `<StepScript>` bindings are at task execution.

### Modifications to the Expression Language

> Additions to
> [Expression Language](https://github.com/OpenJobDescription/openjd-specifications/wiki/2026-02-Expression-Language),
> §1.2.2 (built-in symbol types) and §2.2.4 (string functions)

**Service symbols.** `Service.File.<name>` (`path`) joins the file-location symbols, and a "Service
Symbols" table lists `Service.<name>.<port>.port` (`int`), `bindAddress` (`string`), and
`connectAddress` (`string`), all resolved at task or service execution and typed `unresolved[...]`
at earlier stages, with the scopes in [The `Service.*` scope](#the-service-scope).

**Host and port functions.** Four string functions are added. They are available only in documents
that declare `SERVICE`; `EXPR` alone does not provide them:

| Signature | Description |
|---|---|
| `join_host_port(host: string, port: int) -> string` | Join a host and a port as `host:port`, enclosing `host` in square brackets when it is an IPv6 literal (contains a colon and is not already bracketed). Suitable as a URL authority or a `host:port` flag value. |
| `split_host_port(s: string) -> list[string]?` | The inverse: split `host:port` or `[host]:port` into `[host, port]`, with the brackets removed from an IPv6 literal. Returns `null` when `s` has no port, including an unbracketed IPv6 literal such as `2001:db8::5`. Malformed brackets (`[::1`, `[::1]x:80`) are an evaluation error. The port is a string; convert it with `int()`. |
| `is_ipv4(s: string) -> bool` | True if `s` is an IPv4 literal. |
| `is_ipv6(s: string) -> bool` | True if `s` is an IPv6 literal, bracketed or not, with or without a zone identifier (`fe80::1%eth0`). |

`join_host_port("cache.example", 6379)` is `"cache.example:6379"`;
`join_host_port("2001:db8::5", 6379)` is `"[2001:db8::5]:6379"`;
`split_host_port("[2001:db8::5]:6379")` is `["2001:db8::5", "6379"]`. A zone identifier is carried
through verbatim: `join_host_port("fe80::1%eth0", 80)` is `"[fe80::1%eth0]:80"`. These follow Go's
`net.JoinHostPort` and `net.SplitHostPort`, except that a bare IPv6 literal splits to `null` rather
than an error and an already-bracketed host is not bracketed again. Under method syntax,
`addr.join_host_port(port)`.

**`repr_sh` of integers.** §2.2.6 gains two signatures, available — like the four functions above —
only in documents that declare `SERVICE`:

| Signature | Description |
|---|---|
| `repr_sh(n: int) -> string` | The integer's decimal string form (`repr_sh(6379)` is `6379`; an integer never needs quoting). |
| `repr_sh(args: list[int]) -> string` | The decimal forms joined with single spaces (`repr_sh([80, 443])` is `80 443`). |

These exist so that a port number, or `WrappedService.Ports`, can be passed to a shell command
without a `string()` conversion first.

### Modifications to How Jobs Are Run

> Additions to [How Jobs Are Run](https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Run)

#### Service lifecycle

A Service is in exactly one of four states, tracked by the scheduler:

| State | Meaning |
|---|---|
| **UNREADY** | No instance is READY. Either no instance has been launched yet, an instance is launched but has not yet passed a health-check probe, or the previous instance failed and a relaunch is pending or in progress. |
| **READY** | The current instance has passed a health-check probe, has not since failed `failureThreshold` consecutive probes, and has not exited. |
| **UNHEALTHY** | The current instance has failed `failureThreshold` consecutive health-check probes and is being stopped: the scheduler has canceled *onRun* and is waiting for it to exit, after which the restart decision applies. A transient state; for every other purpose, including Task scheduling, the Service is not READY. |
| **FAILED** | The Service will not be relaunched, and its scope fails. |

A Service is UNREADY from Job creation. A Service's actions run in a **Service Session** on a
service host. Starting a Service means opening a Service Session and, within it, entering the Job's
Environments whose `runScope` includes `SERVICE` in order, running *onEnter* if defined, launching
*onRun*, and probing it with its health check. When a probe succeeds the Service is READY, and the
health check keeps probing it for as long as *onRun* runs.

A scheduler MUST satisfy the following constraints; how it satisfies them is its own concern.

**Ordering.**

1. All of a Service's ports are allocated, and `bindAddress` and `connectAddress` determined,
   before any action of its Service Session runs.
2. No action of a Service Session (including the `onEnter` of an Environment it enters) begins until
   every entry in the Service's `dependencies` is satisfied: every listed Step has completed and
   every listed Service is READY. Services neither of which depends on the other, directly or
   transitively, MAY start concurrently.
3. No Task of a Step is scheduled until every Service whose scope includes that Step is READY. Once
   they are, Tasks are scheduled exactly as today, with no change to how Sessions are formed.
4. A Service is *stopped* before any Service it depends on is stopped; Services neither of which
   depends on the other MAY be stopped concurrently.

**Sessions.**

5. A Service has at most one live Service Session at a time, and at most one running *onRun*
   within it. Before *onRun* is launched again in the same Session, the previous *onRun* process
   MUST have exited, whether on its own or because the scheduler canceled it.
6. A Service Session ends when the Service's scope completes (no Step in the scope has a Task that
   could still run, whether because every Task completed or because the scope failed or was
   canceled), when the Service is relocated, or when the Session fails to start (see
   [Failure and restart](#failure-and-restart)). A Service whose scope completes MUST have its
   Session ended whatever its state, including UNREADY, UNHEALTHY, and FAILED, so that partial state
   is cleaned up. A Service is stopped once nothing in its scope can still use it: when a scope
   completes with a Step, the scheduler exits that Step's Environments in the Task Sessions that
   ran it before stopping the Service, so an Environment's `onExit` that reaches the Service (a
   client flushing to a store) still finds it READY — the order the [execution order
   example](#execution-order) shows.
7. Before a Service Session ends: any running action is canceled with its own `cancelation`
   method; *onExit* runs if it is defined and any action of the Service has run; and every
   Environment entered is exited in reverse order, as at the end of any Session. Then the working
   directory is deleted and the host's allocated amounts and ports are released. Nothing orders a
   Step outside the scope after this; whether a Step that depends on a Step in the scope, but not on
   the Service, can see files the Service wrote is implementation-defined.
8. A Service that is started again after its Session has ended begins a new Service Session: new
   host selection, new ports, new working directory, Environments re-entered, *onEnter* re-run.

**Timing.**

9. A scheduler MAY start a Service at any time consistent with the ordering constraints, including
   lazily, when it is first prepared to schedule a Task in the Service's scope, and MAY decline to
   start a Service whose scope will schedule no Task (for example, a Job canceled before any Task
   could be scheduled). Once started, a Service is kept READY until its scope completes or it
   fails, with one exception. A scheduler MAY **suspend** a Service while no Task in its scope is
   running or can be scheduled (a paused Job, or a Job waiting on a resource). A suspension is not
   a failure: the Service Session ends as constraint 7 requires, the Service becomes UNREADY, no
   restart attempt is consumed, completed Tasks keep their results, and the Service is started
   again in a new Service Session (constraint 8) when the scheduler is next prepared to schedule a
   Task in the scope. A Service MUST NOT be suspended unless its `completedTasks` is `KEEP`, nor
   while any Service that lists it has a Service Session; a Service that other Services depend on
   is therefore suspended only after they are, which requires them to be `KEEP` Services too.

**Health.**

10. A health-check probe in flight when *onRun* exits is canceled, with its `cancelation` method
    when it is an action, and its result is discarded, whether the instance was READY or not. No
    probe result observed after *onRun* has exited makes an instance READY or keeps it READY; the
    instance has failed (see [Failure and restart](#failure-and-restart)).

#### Services run inside Environments

A Service Session enters the Job's `jobEnvironments` whose `runScope` includes `SERVICE`, including
any attached from Environment Templates in the scheduler's order, in the same order a Task Session
enters them. A Service belongs to no Step, so no Step's `stepEnvironments` are entered, whatever the
Service's scope. All are entered before the Service's *onEnter* and exited, in reverse, after its
*onExit*. Environment variables set by an Environment's `variables` or `openjd_env` apply to every
action of the Service, later Environments taking precedence over earlier ones, with the Service's
own *variables* taking precedence over all of them and variables set by the Service's *onEnter*
taking precedence over both.

Under the `WRAP_ACTIONS` extension, a wrapping Environment whose `runScope` includes `SERVICE`
wraps the Service's actions with its `onWrapService*` hooks, and the inner Environments of the
Service Session with `onWrapEnvEnter` and `onWrapEnvExit` as in any Session (see
[`<Environment>`](#environment)). The Service's process then runs inside the container or under
the remote launcher that the wrapping Environment provides, without the Service knowing it.

An Environment entered for a Service runs its `onEnter` once per Service Session, on the service
host, in addition to once per Task Session.

#### Failure and restart

Two kinds of failure lead to the restart decision:

* An **instance failure** occurs when *onRun* exits (with any status) while the Service's scope
  still has work — a Task that has not completed, or that could still run — other than because the
  scheduler canceled it; when *onRun* emits an `openjd_fail` message (the runtime cancels it, step
  2, and the message is the failure's reason); when `readinessTimeoutSeconds` elapses before the
  instance is READY; when the instance becomes UNHEALTHY (see
  [`<ServiceHealthCheck>`](#servicehealthcheck)); or when the scheduler loses the service host
  (step 6). An exit observed after the scope has completed is not a
  failure, whether or not the scheduler's cancelation had yet reached the process; the Service
  Session simply ends.
* A **start failure** occurs when a Service Session fails before *onRun* is launched: a requested
  *port* cannot be allocated on the chosen host, an Environment's `onEnter` fails, or the Service's
  *onEnter* exits non-zero, times out, or emits `openjd_fail`. The Session ends (constraint 7
  applies: *onExit* runs if *onEnter* ran, Environments are exited).

On either failure the Service becomes UNREADY (an UNHEALTHY instance, once its *onRun* has exited)
and the scheduler takes steps 1–4; steps 5–8 govern the outcomes those steps can produce.

1. If `restartPolicy.completedTasks` is `RERUN`, cancels every running Task in the Service's scope;
   each is returned to the queue to run again once the Service is READY, and this is not counted as
   a Task failure. If it is `KEEP`, running Tasks continue. A Task that needs the Service while it
   is not READY, or that holds the endpoint of a relocated instance, fails on its own and is retried
   under the scheduler's ordinary Task retry rules, re-resolving `Service.*` when it runs again; a
   Task that no longer needs the Service completes normally.
2. Cancels *onRun* if it is still running (the readiness-timeout, UNHEALTHY, and `openjd_fail`
   cases) and waits for it to exit; constraint 5 forbids a second *onRun* in the Session before
   then.
3. If the number of relaunches so far is less than `restartPolicy.maxAttempts`:
    1. If `restartPolicy.completedTasks` is `RERUN`, returns every successfully completed Task in
       the scope to the queue.
    2. Relaunches the Service. After a start failure or host loss it MUST begin a new Service
       Session (constraint 8). After an instance failure on a host that is still available, it MAY
       relaunch *onRun* within the existing Service Session (same working directory, same ports,
       *onEnter* not re-run), preserving the state *onEnter* established; it SHOULD begin a new
       Service Session, which allocates new ports, when the failure may be a port conflict (*onRun*
       exited without ever becoming READY); or it MAY relocate (step 5).
4. Otherwise, the Service becomes FAILED and its scope fails: every Step in the scope fails, and
   with it the Job when the scope is every Step. The Service Session is then ended per constraint 6.
5. **Relocation.** Relaunching in a new Service Session on a different host is relocation. It counts
   as one relaunch, is governed by `restartPolicy` including `completedTasks`, and changes every
   `Service.<name>.*` value. When relocating away from a host that is still available, constraint 7
   applies to the old Session in full.
6. **Host loss.** A scheduler loses a service host when it determines, by its own means (a missed
   heartbeat, a preemption notice, an instance termination), that the host is gone or unreachable.
   This is an instance failure. The scheduler MUST NOT wait for *onExit*, Environment exits, or
   working-directory cleanup there; it releases the host's allocations and proceeds to steps 1–4. If
   the host later reappears, the scheduler SHOULD terminate any surviving service process and remove
   the working directory, but the Service's state is not affected either way.
7. **`RERUN` and Step dependencies.** `RERUN` returns the completed Tasks of every Step in the
   Service's scope to the queue (step 3.1), so each of those Steps returns to a pending state. A
   Step that depends on a returned Step, directly or transitively, returns to pending as well, since
   the work it consumed is produced again; Step dependencies are then resolved again from scratch. A
   Service that had been stopped because its scope completed, and whose scope includes a returned
   Step, is started again, in a new Service Session, when that Step next becomes schedulable.
8. **Dependents of a relaunched Service.** When a Service begins a new Service Session (after a
   start failure, host loss, suspected port conflict, suspension, or relocation), every Service that
   lists it, directly or transitively, holds endpoint values that are no longer valid. The scheduler
   MUST stop each such dependent in the order of constraint 4 (dependents before the Services they
   list) and start each again in a new Service Session once every Service it lists is READY. This
   stop does not consume the dependent's restart attempts, and the dependent's `completedTasks`
   applies to its own scope exactly as for any instance that is stopped and started again (its Tasks
   that completed against the old instance are returned under `RERUN`, kept under `KEEP`). A
   relaunch within the same Service Session keeps the same ports and requires nothing of dependents.
   A dependent whose `restartPolicy` gives no `completedTasks` is stopped and started again as a
   `RERUN` Service here, since it has not said that its state survives a new instance; a dependent
   that wants its completed Tasks kept gives `completedTasks: KEEP` whatever its `maxAttempts`.

A Task failure never fails a Service. Because a lost host takes the
Service's state with it, authors of stateful Services SHOULD require non-preemptible capacity with
`attr.worker.preemptible`, and SHOULD choose `completedTasks: RERUN` unless the state can be
regenerated; authors SHOULD prefer a `COMMAND` or `STDOUT` health check when a plain TCP connect is
not a sufficient indicator that the service can do useful work.

#### Validation

This section indexes the rules this RFC adds; each is stated in full where the pointer leads. Every
rule is checked at template validation, except that the
[numeric `@fmtstring` fields](#numeric-fmtstring-fields) are checked when resolved at job creation
and the last two rules need the combined Job and are checked at submission.

| Rule | Stated in |
|---|---|
| Every `Service.*` reference names a declared or required Service and port, appears only where permitted, and the referencing entity lists the Service in its `dependencies` | [The `Service.*` scope](#the-service-scope) |
| No `Service.*` value in a field resolved at job creation, nor in an Environment whose explicit `runScope` includes `SERVICE` | [The `Service.*` scope](#the-service-scope); [`<Environment>`](#environment) *runScope* constraint 2 |
| `runScope` holds recognized names without duplicates and is absent from `stepEnvironments` | [`<Environment>`](#environment) *runScope* constraints 1, 3, and 4 |
| An Environment's `dependencies` is well formed and absent from `stepEnvironments` | [`<Environment>`](#environment) *dependencies* constraints 2–4 |
| The wrap hooks an Environment defines are exactly those its `runScope` calls for | [`<Environment>`](#environment) wrap hook rule 1 |
| Every `dependencies` entry is well formed | [`<StepDependency>`](#stepdependency) constraints 1, 2, and 4; [Environment Template](#environment-template) *services* constraint 5 |
| The `dependencies` graph is acyclic | [`<StepDependency>`](#stepdependency) constraint 3 |
| Every inline Service, and every `externalServices` entry, is listed by some Step, Service, or Job Environment | [Service scope](#service-scope) rule 4 |
| Service, requirement, and port names are `<Identifier>`s other than `File`, unique within their lists, and no requirement shares a `name` with an inline Service | [`<ServiceName>`](#servicename); [Job Template](#job-template) *externalServices* constraint 4 |
| `externalServices` appears only in a Job Template | [Job Template](#job-template) *externalServices* constraint 5 |
| `healthCheck` is consistent with `<ServiceActions>`, with `ports`, and with its own `type` | [`<Service>`](#service) item 7; [`<ServiceHealthCheck>`](#servicehealthcheck) items 2, 3, and 6; [`<ServiceActions>`](#serviceactions) item 3 |
| No two ports of a Service with the same `protocol` have the same `port` number | [`<Service>`](#service) item 6 constraint 4 |
| `completedTasks` is provided when `maxAttempts` is greater than 0 | [`<ServiceRestartPolicy>`](#servicerestartpolicy) item 2 |
| A template that lists `SERVICE` also lists `EXPR` | [Backward compatibility](#backward-compatibility) |
| A wrapping Environment from a document without `SERVICE` is not combined with a Job that has any Service *(submission)* | [Environment Template](#environment-template) item 4 |
| Each `externalServices` entry matches exactly one attached Service *(submission)* | [Environment Template](#environment-template) item 2 |

These checks appear in the wiki as §9.9.

#### Placement

Placement is entirely up to the scheduler, subject to the Service's *hostRequirements*. A
single-host runner such as `openjd run` starts the Service alongside the Tasks on the same host with
`bindAddress` and `connectAddress` both on loopback.

Whatever the placement, `connectAddress` and `port`, over the port's `protocol`, MUST reach the
service process from every host in the scope. How the scheduler achieves that (a shared network, an
overlay, port forwarding, a proxy) is not visible in the template.

#### Stdout/Stderr messages

> Addition to the list in *Stdout/Stderr Messages*, and a note on `openjd_fail` in a Service Session
> (see [`<ServiceActions>`](#serviceactions)): from a Service's *onRun* the message is an instance
> failure in itself, on which the runtime cancels *onRun* and reports the message as the reason; from
> *onEnter* or *onExit* it marks the action failed when it exits, whatever the exit status.

* `openjd_service_ready: <message>` where `<message>` is any string — Interpreted only when emitted
  by the `onRun` action of a Service whose health check *type* is `STDOUT`, as that type's probe. It
  indicates that the service is accepting traffic on all of its declared ports: the first line makes
  the instance READY, and later lines are heartbeats when the check gives `healthIntervalSeconds`
  (see [`<ServiceHealthCheck>`](#servicehealthcheck)).

## Design Choice Rationale

### A new entity rather than extending `<Environment>`

An Environment is defined by *where* it runs: on the host of the Session, entered and exited around
that Session's Tasks. Every one of the four differences in [Motivation](#motivation) contradicts
that model. Adding `ports:` and a long-lived `onRun:` to `<Environment>` would produce an entity
whose lifecycle depends on which optional fields are present, which is hard to read and harder to
implement. A distinct `<Service>` that reuses Environment's sub-schemas (`variables`, `let`,
embedded files, `<Action>`) gets the familiarity without the ambiguity.

### `onEnter` / `onRun` / `onExit` rather than a single `onRun`

Separating `onEnter` from `onRun` lets the scheduler relaunch `onRun` without repeating setup that
touches disk or other state outside the process: initializing a database, creating a Conda
environment, writing a configuration file.

### `onRun` exiting is always a failure

A service has no "finished" state while its scope still has work, so any exit is an instance
failure. The rule is tied to the scope having work rather than to the scheduler's cancelation so
that a service which exits on its own once its clients are gone does not fail a Job whose work has
all succeeded.

`openjd_fail` from *onRun* is treated the same way, and proactively: a service that has detected it
cannot serve (a corrupt store, a lost license) need not hang around until something notices. It
prints the reason and the runtime cancels it, so the restart decision runs with that reason attached
rather than with a bare exit code later.

### Health is declared, not inferred

A scheduler cannot know when an arbitrary process is ready, nor whether a process that still holds
its port is answering. The three probe types cover the three places either is observable: the
network (`TCP_CONNECT`), an external check (`COMMAND`), and the process itself (`STDOUT`). One probe
serves both readiness and health, since the probe that proves readiness is the one that proves
continued health.

`COMMAND` runs an action while *onRun* is running, which nothing else in the specification does. The
alternative is a wrapper script that backgrounds the binary and polls it, which is the boilerplate
OpenJD exists to remove; the rules in [Concurrency with `onRun`](#concurrency-with-onrun) are the
cost of avoiding it.
[Issue #133](https://github.com/OpenJobDescription/openjd-specifications/issues/133), monitoring for
Environment actions in general, should adopt the same vocabulary.

### Why the protocol is declared on the port

A distributed scheduler publishes or forwards each port through a container mapping, a firewall
rule, or a NAT entry, and every one of those is defined per protocol. The `protocol` field tells it
which, in the place the port is declared.

### `restartPolicy.completedTasks` is per-Service and required when relaunch is allowed

The two motivating examples pull in opposite directions: a cache loses nothing of consequence when
it restarts, while a coordinator that loses its state has invalidated every result produced against
it. No single behavior is correct, so the policy is per-Service, and because neither answer is safe
to assume the field has no default: an author who allows a relaunch must say what a relaunch means
for completed Tasks. When `maxAttempts` is 0 no relaunch can happen and the field is not needed.

The same distinction decides what happens to Tasks running at the moment of failure (requeued under
`RERUN`, left to finish or fail on their own under `KEEP`) and whether a scheduler may suspend an
idle Service (only under `KEEP`, since under `RERUN` suspension would discard every completed Task).

### Endpoint as three scalar values

`bindAddress` and `connectAddress` differ in nearly every deployment (a process binds `0.0.0.0`;
clients connect to a hostname), and `port` is separate from both so the three compose with any URL
scheme or `--host` / `--port` pair. Bracketing an IPv6 literal, the one composition that needs
logic, is the `join_host_port` function.

### Dependencies are declared, and one list names both kinds

A Step that uses a Service depends on it, and the template says so where it says everything else
about what a Step waits for: in `dependencies`, with `service: <name>` beside
`dependsOn: <StepName>`. A Service's own `dependencies` names the Steps and Services it waits for
the same way, and a Job Environment's names the Services it uses. Three things follow from making
the dependency a declaration rather than inferring it from `Service.*` references. The graph is
visible in one place: a reader, a UI, or a scheduler learns which Steps need which Services from the
`dependencies` lists alone, without walking every format string in the template. An opaque consumer
is expressible: a Step whose Tasks reach a Service through a configuration file, a wrapper script,
or an environment variable set outside the template never references `Service.*`, yet it depends on
the Service all the same. And a reference without a dependency is a diagnosable mistake instead of
an implicit edge: a template that reads `Service.Cache.main.port` in a Step that does not list
`service: Cache` is rejected with a message that names the missing entry.

One list holds both kinds of entry because a dependency on a Service is the same kind of fact as a
dependency on a Step, differing only in what satisfies it: completion for a Step, READY for a
Service. One vocabulary means one cycle check over one graph.

### External Services are declared with their ports

Listing the ports in an `externalServices` entry makes every `Service.<name>.<port>.*` reference in
the template checkable against the entry alone, exactly as references to an inline Service are, and
lets the scheduler match the entry to an attached Service without reading the template's format
strings.

### External Services via the Environment Template, not a new template type

A separate `servicetemplate-2023-09` root element was rejected for its deployment surface. Every
scheduler that supports Environment Templates already has the plumbing to attach a document to a
queue, order the attachments, merge their parameter definitions, and apply them to each submission.
Expressing a Service as a variant of that same document means Services work everywhere Environment
Templates do with no new integration; a second root element would require every implementation to
add a second attachment type, UI, and API, and a rule for interleaving the two lists. Letting the
same document also define the client Environment keeps a Job Template's requirement optional: a
template written before the Service existed uses it through environment variables, and only one
that reads the endpoint itself declares a requirement.

### Service names are per document

An Environment Template and a Job Template may each define a Service named `Cache` without
conflict: they are two separate Services, and each document's `Service.Cache.*` means its own. A
Job Template reaches an attached Service only by naming it in `externalServices`, so that is the one
place a name must match across documents, and the one place a Job Template may not also declare a
Service of the same name.

### `runScope` is written on the Environment

Which Sessions an Environment is entered in could be inferred from what it references, but the
effect lands far from the cause: in the Service Sessions the Environment is excluded from, which a
reader of the template never sees listed. A field on the Environment puts the answer where the
reader is looking. The default is still inferred, from the one fact that is local and certain: an
Environment that lists a Service cannot run in a Service Session, where that Service has no endpoint
yet, so it defaults to `[TASK]`. Everything else defaults to every Session, so existing provisioning
Environments apply to Services unchanged.

### `onHealthCheck` is an action of the Service

The alternative is an `<Action>` inside `healthCheck`. That leaves it outside `script:`, with no
principled claim on `let` bindings, embedded files, or the same format-string scopes as the other
actions. Making it a fourth `<ServiceActions>` entry gives every action of a Service one scope rule.
The `healthCheck` object keeps the policy; the action keeps the command.

### Start failures consume a restart attempt

A failure before *onRun* launches (an Environment's `onEnter`, or the Service's `onEnter`) is
usually as transient as an *onRun* crash: a package mirror hiccup, a container pull timeout.
Treating it as terminal while retrying an *onRun* crash would fail a Job for exactly the fault
`restartPolicy` exists to absorb.

## Prior Art

* **Kubernetes** — `Service` + `Deployment` with `readinessProbe` and `livenessProbe`
  (`tcpSocket`, `exec`, `httpGet`; `periodSeconds`, `failureThreshold`) and `restartPolicy`. Our
  three probe types map directly onto `tcpSocket`, `exec`, and a stdout signal in place of `httpGet`
  (which would require HTTP semantics in the specification); one `healthCheck` with two intervals
  does the work of Kubernetes' two probes. Kubernetes services are not scoped to a batch of work,
  which is the gap this RFC fills.
* **Docker Compose** — `depends_on: { condition: service_healthy }` plus `healthcheck` with
  `interval`, `retries`, and `start_period`, which `healthIntervalSeconds`, `failureThreshold`, and
  `readinessTimeoutSeconds` correspond to. Its start-until-healthy ordering along the `depends_on`
  graph is the model for ours, declared in `dependencies` as Compose declares it in `depends_on`.
* **GitHub Actions service containers** — `services:` in a job, started before steps and stopped
  after, with ports published to the runner. Scoped to one job on one host; the closest
  batch-oriented precedent for a Service whose scope is one Step.
* **Slurm heterogeneous jobs / `srun --overlap`** — Users commonly launch a coordinator (e.g. a Ray
  head or a Dask scheduler) as one component and workers as another, passing the head's address by
  hand through environment variables or a shared file. This RFC is the tooling-parseable version of
  that pattern. Slurm's `srun` also demonstrates the direct-launch model for MPI that the
  co-scheduled Step in [Future Work](#future-work) relies on: every rank is a process the scheduler
  launched itself, wired up through a PMI server rather than through `mpirun` and ssh.
* **Nomad** — `service` stanzas with `check` blocks (`tcp`, `script`, `http`) and `restart`
  stanzas with `attempts`. The `KEEP`/`RERUN` distinction has no direct analogue; it is specific to
  batch systems where completed work has a value that a service restart can invalidate.

## Implementation Impact

- **Rust (openjd-rs)**: A prototype on the [`service-extension`
  branch](https://github.com/mwiebe/openjd-rs/tree/service-extension) of the `mwiebe/openjd-rs` fork
  is developed against the `SERVICE` conformance suite that accompanies this RFC and the rest of
  the 2023-09 suite. It implements the schema, validation, and job-creation rules in
  `openjd-model`, the host and port functions in `openjd-expr`, the Service Session in
  `openjd-sessions`, and a single-host scheduler for `openjd run` in `openjd-cli`. The prototype's
  largest single piece was the Service Session: the existing Session held one current action, one
  log stream, and one cancellation target, and running `onHealthCheck` alongside `onRun` needed a
  second action slot with its own cancellation and per-action attribution on captured output. The
  health phase adds a probe loop that outlives readiness, counts consecutive failures, and turns
  the threshold into a cancellation of `onRun`.
- **Python (openjd-model, openjd-sessions)**: The Python packages are intended to become bindings
  over openjd-rs. The `v0` releases of `openjd-model-for-python` and `openjd-sessions-for-python`
  would therefore not gain this extension; a `v1` built on the bindings would inherit it, exposing
  the new models, the Service Session, and the `Service.*` scope.
- **Schedulers**: This is where most of the work lives. A scheduler must place Services, allocate
  ports, guarantee cross-host reachability over each port's protocol, gate Task scheduling on
  readiness, keep probing after READY, track instance failures, implement `KEEP`/`RERUN`, and stop
  Services at scope end. A
  single-host runner can implement all of this with loopback addresses and a process table, as the
  prototype does; a distributed scheduler needs a networking answer.

No feature here is significantly harder in one language than another. There are no evaluation
performance implications; `Service.*` adds a handful of symbols resolved at task execution time.

## Rejected Ideas

### Passing the endpoint through environment variables

Exporting `OPENJD_SERVICE_<NAME>_<PORT>_ADDRESS` into every Session is rejected on the
Tooling-parseable tenet: environment variables hide data flow from tools that read the template,
whereas `{{ Service.Cache.main.connectAddress }}` is visible. This is the same reasoning recorded
for `OPENJD_SESSION_WORKING_DIR` in *How Jobs Are Run*.

### Services as a kind of Step

A Service could be a Step whose single long-running Task other Steps depend on, given a dependency
satisfied when the upstream Step is *running and ready* rather than finished, a `ports:` list on the
Step, a completion condition that stops the Task once its dependents finish, and a health check
beside `onRun`.

This RFC rejects that for two reasons. First, each of those changes the Step and Task state
machines that every scheduler and every UI already implements: a Step that is "ready" but not
"completed", a Task that is stopped on purpose without failing, a dependency satisfied by a state
other than completion. A new entity is extension surface that an implementation without `SERVICE`
never sees. Second, readiness for a multi-Task Step would have to be "READY when every Task has
passed its probe", which couples one Task's relaunch to the completed Tasks of every dependent Step;
a Service has one instance, and `completedTasks` says what its relaunch means. The sub-features
that are valuable on Steps in their own right, a health check on batch Tasks or ports on the Tasks
of a worker Step, deserve their own proposals (see [Future Work](#future-work)), and `<Service>`
should adopt their vocabulary when they land.

### Scope inferred from `Service.*` references

A Service's scope could be computed from the template's format strings: a Step that references
`Service.X.*` is in `X`'s scope, a Service that references another depends on it, and a Service
nothing references serves the whole Job, with no `dependencies` entry to write. Rejected: it hides
the dependency graph in format strings, cannot express an opaque consumer, and turns a stray
reference into an undiagnosable implicit edge, for the reasons given in
[Dependencies are declared](#dependencies-are-declared-and-one-list-names-both-kinds).

An earlier draft gave external Services an implicit scope of every Step, so that a queue's Service
ran for every Job whether or not the Job used it. Rejected for the same reason: it was an edge no
document declared. Under the one rule, a queue Service runs for a Job exactly when the Environment
defined alongside it, or the Job Template, lists it.

### `serviceEnvironments`, a Service-scoped Environment list

A `<Service>` could carry its own list of Environments, the analogue of `stepEnvironments`, entered
only in its Session. Rejected because it offers nothing *onEnter* does not: `stepEnvironments` earn
their place by amortizing setup across the many Tasks a Session runs, but a Service Session runs one
*onEnter*, once per Session, before *onRun*, so there is nothing to amortize. A per-Service list
could return as future work if a per-Service *external* wrapper is ever needed.

## Future Work

* **Co-located Services.** A Service that runs on the same host as the Task Session that uses it,
  started alongside that Session rather than shared across the scope. Such a Service is not shared
  by Tasks on other hosts, so it could reach its clients through a Unix domain socket or a shared
  directory and might declare no port at all. It needs a different lifecycle (one instance per
  Session, started and stopped with it) and a different endpoint model from the one in this RFC.
* **Co-scheduled Steps, for systems like MPI and Dask.** For use case 6, Tasks already run
  concurrently when capacity allows; what is missing is a *reservation*: an MPI job with a fixed
  world of 30 ranks deadlocks in `MPI_Init` if the scheduler launches 10 Tasks and the other 20 wait
  for hosts, and a Dask client needs at least some workers alive while it runs. A follow-up RFC
  should add three things: a Step-level reservation (a minimum number of the Step's Tasks, or all of
  them, for which hosts must be available before any launches, allocated all-or-nothing); a gang
  failure policy (cancel the sibling Tasks when one fails, and retry as a group); and a way to
  require network connectivity between the Tasks' hosts, since ranks talk peer-to-peer once they
  have found each other and this RFC guarantees reachability only from a Task's host to a Service
  host. That primitive is useful independently of Services, so it is not part of this RFC.
* **Replicated Services.** A `replicas:` count producing `Service.<name>.<port>.connectAddresses`
  as a `list[string]`, for a pool of identical daemons serving a single driver (a distributed
  cache, for example). Deferred until the single-instance model has been exercised; the
  co-scheduled Step above covers the cases where the replicas are themselves the work.
* **Values published by a Service to its consumers.** A Service's `onEnter` can hand values to its
  own actions through `openjd_env`, but nothing a Service computes (a generated credential, a
  discovered device, a path) reaches the Steps that depend on it except over its endpoint. A
  follow-up could add a `Service.<name>.Var.*` scope or an `openjd_service_var` message, with the
  same visibility rule as the endpoint values. This RFC leaves it out because the endpoint suffices
  for the use cases it targets and the scheduler-mediated channel needs a design of its own.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is
more permissive.
