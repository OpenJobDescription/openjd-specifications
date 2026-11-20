* Feature Name: Service
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/193
* Start Date: 2026-09-17
* Specification Version: 2023-09 extension SERVICE
* Accepted On: (pending)
* Depends On:
  * RFC 0002, Model Extensions (https://github.com/OpenJobDescription/openjd-specifications/issues/57)
  * RFC 0010, Environment Parameters (`ENV_PARAMS`), for the `environment:` dependency entry and an Environment's
    `activation` and `enableIf` (https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md)
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

## Basic Examples

### A Valkey store shared across a Job's Tasks

This Job starts a single [Valkey](https://valkey.io/) in-memory data store before scheduling any
Task, and every Task connects to it to cache and coordinate intermediate results. The template
names one port, `main`, and lets the scheduler choose its number and host; the service process binds
`Service.Cache.main.bindAddress`, and Tasks on any host connect to `Service.Cache.main.connectAddress`.
Because a cache can be repopulated, a relaunch keeps completed Tasks' results.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions: [SERVICE, ENV_PARAMS, EXPR]
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
      maxRestarts: 3
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
extensions: [SERVICE, ENV_PARAMS, EXPR]
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
      - step: PrepareScene  # Not started until the scene it hands out exists.
    ports:
      - name: api
      - name: metrics
    healthCheck:
      # Each probe is one run of onHealthCheck: every 5 seconds until READY, then every 30.
      type: COMMAND
      readinessTimeoutSeconds: 120
    restartPolicy:
      maxRestarts: 1
      completedTasks: RERUN  # In-memory state is lost on relaunch; prior results cannot be trusted.
    script:
      actions:
        # One-time initialization survives a relaunch of onRun in the same Service Session.
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
      - step: PrepareScene  # Must complete first.
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
extensions: [SERVICE, ENV_PARAMS, EXPR]
parameterDefinitions:
  - name: CacheMemoryMiB
    type: INT
    default: 8192
services:
  - name: Cache
    description: "A per-Job Valkey store shared by all of the Job's Tasks."
    dependencies:
      # CacheClient waits for this Service to be READY, so this Service's own
      # Sessions decline it. Entering it would be a cycle, which is rejected.
      - environment: CacheClient
        enableIf: false
    hostRequirements:
      amounts:
        - name: amount.worker.memory
          min: 8192
    ports:
      - name: main
    restartPolicy:
      maxRestarts: 3
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
  # Every Session that does not decline this Environment enters it. The Cache
  # Service's own Sessions decline it above.
  dependencies:
    - service: Cache
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

A Job Template can instead read the queue's Service directly by declaring the Service's name and the ports it uses in
`externalServices`. `Service.Cache.*` is then available under the same rule as for an inline Service, and the scheduler
rejects a submission to a queue that does not attach a matching Service. Starting from the Valkey example's Job
Template, its `services` list is replaced by the requirement below, and only the parts that differ are shown.

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
extensions: [SERVICE, ENV_PARAMS, EXPR]
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
      - step: BuildIndex  # Holds no host until the index exists.
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
      maxRestarts: 2
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

### A Service that asks for its own software

A queue that attaches a parameterized Conda Environment, as in RFC 0010's first example, provisions
Services the way it provisions Steps. Each requests its packages with an `environment:` entry in its
`dependencies`, and each Session enters the Environment with its own entity's values. Only the parts
that differ from the Valkey example are shown.

```yaml
services:
  - name: Cache
    dependencies:
      # The queue's Conda Environment, configured for this Service's Session only.
      - environment: Conda
        parameters:
          Packages: "valkey=8"
    # ports, healthCheck, and restartPolicy as in the Valkey example. No onEnter is
    # needed: valkey-server is on PATH in every action of the Service Session.
    script:
      actions:
        onRun:
          command: valkey-server
          args: ["--port", "{{ Service.Cache.main.port }}", "--bind", "{{ Service.Cache.main.bindAddress }}"]

steps:
  - name: ProcessFrames
    dependencies:
      - service: Cache
      - environment: Conda
        parameters:
          Packages: "python=3.12 valkey-py"
```

The Service Session and the Task Sessions enter the same Environment with different values, so
they get different software. A Job Template that does not say what a Service needs gets the
Environment's defaults for it, exactly as a Step that says nothing does.

### Execution order

For a Job with one Service `S`, one `jobEnvironment` `E`, and one Step, which depends on `S`, with Tasks `T1..Tn`
running in two Sessions on two Worker Hosts, one order the rules permit is:

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
the Tasks run in. No Task of a Step that depends on `S` is scheduled until `S` is READY. The worker hosts may
enter `E` earlier, since `E` does not list `S`, but they run no Task until then.

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
3. **Endpoint publication.** A Service exposes one or more ports. The runtime allocates a concrete address and port and
   makes them discoverable, on any host, both to the service process (so it knows what to bind) and to every entity that
   lists it in its `dependencies` (so they know where to connect).
4. **Readiness, health, and failure.** A scheduler must know when the service is accepting
   connections before it schedules the Tasks in the Service's scope, must notice when a running
   service stops answering, and must react when it dies or hangs: relaunch it, or fail the scope.
   Because a service can hold state that Tasks depend on, a service author must be able to say
   whether Tasks that completed against the old instance are still valid.

A Service borrows the rest of its shape from existing entities: `description`, `variables`, `let`,
embedded files, and the `<Action>` model with its cancelation methods from `<Environment>`, and
`hostRequirements` from `<StepTemplate>`.

A Service also needs what the Tasks need. The Valkey binary, the coordinator's Python environment, or the renderer in
server mode is provisioned today by the Job's Environments (a Conda or Rez Environment, or a container under
`WRAP_ACTIONS`), and a Service that could not use them would force every Service author to reimplement that
provisioning. Services therefore run inside the Job's Environments, and wrapping Environments wrap Service actions as
they wrap Task actions. A Service Session chooses its Environments exactly as a Task Session does, by RFC 0010's rules,
among those of its own document and of the documents attached before it. An Environment that configures clients of a
Service reads that Service's endpoint, so it waits for the Service to be READY, and the Service's own Sessions must stay
out of it: the template author makes it opt-in for the Steps that need it, or has the Service decline it, and a template
that lets the Service enter it is rejected as a dependency cycle. Where a Job Template's Service needs software the
Steps do not, it supplies its own values to a parameterized Environment, or requests one that RFC 0010's
`activation: ON_REQUEST` makes opt-in, with an `environment:` entry in its `dependencies`, exactly as a Step does. This is why
`SERVICE` builds on `ENV_PARAMS`: a Service's software configuration is its own to choose, written the same way as a
Step's.

### Use cases

1. **Shared cache / data store.** A Valkey or Redis-compatible store that Tasks use to memoize
   expensive intermediate results (e.g. shared geometry or texture bakes) within a Job.
2. **Work coordination.** A service that divides a large, irregular work list among the Tasks of a
   Step, collects results, or implements a barrier so that a "gather" phase begins only when all
   "scatter" Tasks have checked in.
3. **Application server mode.** A renderer, DCC, simulation engine, or inference server started
   once in server mode, with Tasks on other hosts submitting requests to it over its port. This
   fits when the server holds something scarce that the Tasks cannot each have: a large GPU and a
   model loaded into its memory, a scene that takes minutes to load, or a license limited to one
   seat. The Tasks then use their own hosts' resources for the rest of the work. When the Tasks can
   share the server's host, a Step Environment that starts the application once per Session
   amortizes the load more simply, and needs no Service.
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

## Specification

The normative text of this extension is the wiki edits in this pull request: [Template
Schemas](../wiki/2023-09-Template-Schemas.md), [Expression Language](../wiki/2026-02-Expression-Language.md), and [How
Jobs Are Run](../wiki/How-Jobs-Are-Run.md). This section summarizes each change and links to the wiki section that holds
the formal text; where the two differ, the wiki governs. A section number (§) in this RFC refers to Template Schemas
unless another page is named.

`SERVICE` builds on RFC 0010 (`ENV_PARAMS`), whose wiki edits are in its own pull request. Where this RFC says that a
Service follows RFC 0010 as a Step does, it means the rules of
[RFC 0010](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md)
and the wiki sections it links, with "Step" read as "Service".

### Terminology

| Term | Definition |
|------|------------|
| **Scheduler** | The system that accepts Job and Environment Templates, creates Jobs from them, and dispatches Sessions and Services to Worker Hosts. |
| **Service** | An entity declared in a `services` list: a long-lived process that publishes one or more network ports and is kept alive by the scheduler for the lifetime of its scope. |
| **Scope** | The set of Steps whose Tasks depend on a Service, determined from the `dependencies` lists ([§9.1](../wiki/2023-09-Template-Schemas.md#91-service-scope)). |
| **Service Session** | The Session on the service host in which a Service's actions run: a working directory, the Job Environments that the Service's Sessions enter (see [Services run inside Environments](#services-run-inside-environments)) entered around the Service's actions, and the Service's actions themselves. It is a Session as described in How Jobs Are Run, containing one Service instead of Tasks. |
| **Service host** | The Worker Host the scheduler places a Service on. It may or may not be a host that also runs Tasks. |
| **UNREADY / READY / UNHEALTHY / FAILED** | The four Service states the scheduler tracks ([Service lifecycle](../wiki/How-Jobs-Are-Run.md#service-lifecycle)). |
| **Instance** | One launch of a Service's `onRun` action. A Service has one instance at a time; a restart creates a new instance. |
| **External Service** | A Service supplied to a Job by the scheduler from an Environment Template, rather than declared in the Job Template. A Job Template that reads an external Service's endpoint declares a **requirement** for it in `externalServices`. |
| **Inline Service** | A Service declared in the Job Template's own `services` list, as opposed to an external Service. |
| **Environment selection** | Which Environments a Session enters, as RFC 0010 decides it from each Environment's `activation`, `enableIf`, and `exclusiveGroup` and from the entity's `environment:` entries (RFC 0010, [Which Sessions enter an Environment](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md#which-sessions-enter-an-environment)). A Service's Sessions are selected exactly as a Step's are, among the Environments that [Services run inside Environments](#services-run-inside-environments) makes available to the Service. |
| **Request, decline, applies** | As RFC 0010 defines them for a Step, extended to Services: a Service requests an Environment with an enabled `environment:` entry in its `dependencies`, declines a `BY_DEFAULT` one with a disabled entry, and an Environment applies to it by its `activation` and those entries. |

### Extension name and the documents that list it

[§1.1](../wiki/2023-09-Template-Schemas.md#11-job-template) item 3 adds `SERVICE` to the extension names.
[§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service) says that a template that lists `SERVICE` must
also list `EXPR` and `ENV_PARAMS`: a Service requests and configures Environments with RFC 0010's `environment:`
entries, and its host requirements combine with theirs by RFC 0010's rules.

An Environment Template needs the `extensions` key to list `SERVICE`.
[§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) items 2 and 3 add `$schema` and `extensions` to it,
as RFC 0010's wiki edit does (its [Changes that apply without the
extension](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md#changes-that-apply-without-the-extension)
item 4), so that this pull request reads correctly on its own. An extension listed there applies to that document only,
so a Job Template need not list `SERVICE` for its Steps to enter an attached Environment that lists an attached Service.
This pull request also relies on the Job's Environment order that RFC 0010 states in §1.1 *jobEnvironments* (its Changes
that apply without the extension, item 3): the attached Environments come first, in the order they are attached, then
the Job Template's. "Attached before" in this RFC and its wiki edits refers to that order. Reading the endpoint itself
needs `externalServices`, which requires `SERVICE`.

### Backward compatibility

This RFC is additive and gated by the `SERVICE` extension name declared under RFC 0002:

- A template that lists `SERVICE` must also list `EXPR` and `ENV_PARAMS`, and a scheduler must reject one that does
  not. `ENV_PARAMS` supplies the `environment:` entry by which a Service requests an Environment and supplies its
  parameter values, an Environment's `activation`, `enableIf`, and `exclusiveGroup`, and the rule that combines a
  Service's host requirements with those of the Environments its Sessions enter. RFC 0010 specifies those for Steps,
  and this RFC applies them to Services unchanged (see [Services run inside
  Environments](#services-run-inside-environments)).
- No existing field changes meaning. One combination is newly rejected at submission: a wrapping Environment (RFC 0008)
  that a Service Session enters but that does not define the `onWrapService*` hooks, such as one from a document
  without `SERVICE`, in a Job that has any Service
  ([§1.2.2](../wiki/2023-09-Template-Schemas.md#122-services-from-environment-templates) item 4). A queue wrapper that
  lists neither `SERVICE` nor `ENV_PARAMS`, such as one written before both extensions, behaves as `activation: ALWAYS`
  under RFC 0010, and no Service can decline it. Such a queue rejects every Job whose Job Template has a Service that
  runs, and every Job that uses a Service of an Environment Template attached after the wrapper, until the wrapper's
  author defines the hooks, or lists `ENV_PARAMS` and makes the wrapper `ON_REQUEST` or keeps that extension's
  default, `BY_DEFAULT`, for each Service to decline. Each of these lists `ENV_PARAMS`: the hooks need `SERVICE`, which
  requires it, and `activation` is part of it. So a wrapper that must still be entered by every Session that may enter
  it also sets `activation: ALWAYS`.
- `attr.worker.preemptible` is a new standard attribute name that any Step may require, with or without the extension
  (see [`attr.worker.preemptible`](#attrworkerpreemptible)).

### Declaring a Service

[§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service) is a new top-level section, inserted after §8,
that defines the `<Service>` object, so *Additional Information* and *License* become
[§10](../wiki/2023-09-Template-Schemas.md#10-additional-information) and
[§11](../wiki/2023-09-Template-Schemas.md#11-license). A Service has a name, a `let`, `dependencies`,
`hostRequirements`, named `ports`, a `healthCheck`, a `restartPolicy`, `variables`, and a `script` of four actions. It
reuses the sub-schemas of an Environment and a Step (`<LetBindings>`, `<EnvironmentVariables>`, `<EmbeddedFile>`,
`<Action>`, `<HostRequirements>`), so authors meet nothing new except what a long-lived process needs (see [A new
entity rather than extending `<Environment>`](#a-new-entity-rather-than-extending-environment)). Its subsections define
the new parts:

* [§9.2](../wiki/2023-09-Template-Schemas.md#92-servicename) `<ServiceName>`: an identifier other than `File`, which
  `Service.File.*` reserves.
* [§9.3](../wiki/2023-09-Template-Schemas.md#93-serviceport) `<ServicePort>`: a name, an optional fixed number, and a
  protocol, plus the form of `bindAddress` and `connectAddress`. Ports are named so that the scheduler can choose the
  numbers (see [Ports are named](#ports-are-named)), and an IPv6 address is never bracketed, so templates join an
  address and a port with `join_host_port`.
* [§9.4](../wiki/2023-09-Template-Schemas.md#94-servicehealthcheck) `<ServiceHealthCheck>`: one probe, `TCP_CONNECT`,
  `COMMAND`, or `STDOUT`, that decides readiness and then health (see [Health is declared, not
  inferred](#health-is-declared-not-inferred)).
* [§9.5](../wiki/2023-09-Template-Schemas.md#95-servicerestartpolicy) `<ServiceRestartPolicy>`: `maxRestarts`, and
  `completedTasks`, which says whether the Tasks' results depend on the instance and is required when a relaunch is
  allowed (see [`restartPolicy.completedTasks` is per-Service and required when relaunch is
  allowed](#restartpolicycompletedtasks-is-per-service-and-required-when-relaunch-is-allowed)).
  [§9.5.1](../wiki/2023-09-Template-Schemas.md#951-numeric-fmtstring-fields) lets the numeric fields of these three
  objects be format strings resolved at job creation, so that a Job Parameter or a `<Service>.let` binding can supply
  them.
* [§9.6](../wiki/2023-09-Template-Schemas.md#96-servicescript) `<ServiceScript>` and
  [§9.7](../wiki/2023-09-Template-Schemas.md#97-serviceactions) `<ServiceActions>`: `onEnter` for setup that survives a
  relaunch within the same Service Session, the long-lived `onRun`, `onHealthCheck` for a `COMMAND` probe, and `onExit`
  (see [`onEnter` / `onRun` / `onExit` rather than a single `onRun`](#onenter--onrun--onexit-rather-than-a-single-onrun)
  and [`onHealthCheck` is an action of the Service](#onhealthcheck-is-an-action-of-the-service)). §9.7 also says which
  `openjd_*` messages each action may emit, and that `openjd_env` from `onEnter` reaches only the Service's own later
  actions. [§9.7.1](../wiki/2023-09-Template-Schemas.md#971-concurrency-of-onhealthcheck-with-onrun) gives the rules for
  `onHealthCheck` running while `onRun` runs, the only two actions of one Session that run at once: embedded files,
  stdout, log attribution, when invocations may run, what happens to one in flight when `onRun` exits, and wrap scripts.
* [§9.8](../wiki/2023-09-Template-Schemas.md#98-servicerequirement) `<ServiceRequirement>` and
  [§9.8.1](../wiki/2023-09-Template-Schemas.md#981-servicerequirementport) `<ServiceRequirementPort>`: how a Job
  Template names an external Service and the ports it reads (see [External Services are declared with their
  ports](#external-services-are-declared-with-their-ports)).

[§1.1](../wiki/2023-09-Template-Schemas.md#11-job-template) items 8 and 9 add `services` and `externalServices` to the
Job Template, and *steps* becomes item 10. Item 7 says that the Job Environments are also entered and exited in their
order by every Service Session that enters them. [§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template)
items 5 and 6 make an Environment Template's `environment` optional and add `services`, with at least one of the two
required, and the [opening paragraph](../wiki/2023-09-Template-Schemas.md#template-schemas-version-2023-09) of Template
Schemas says that an Environment Template may describe Services. Item 6 constraint 4 makes the `dependencies` of an
Environment Template's Services one acyclic graph, which includes an edge from each of them whose Sessions enter the
document's own Environment to each Service that Environment lists. Item 6 constraint 5 limits an Environment Template's
Service to `service:` entries and disabled `environment:` entries (see [Services run inside
Environments](#services-run-inside-environments)). The new
[§1.2.2](../wiki/2023-09-Template-Schemas.md#122-services-from-environment-templates) says how the scheduler applies
such Services to every Job submitted through it, matches each `externalServices` entry to exactly one attached Service,
keeps same-named Services of different documents apart, and checks attached wrapping Environments. It also says that
each Job gets its own instance of an external Service and that the limit of 10 Services applies to each document, and it
lists the only checks that need the combined Job (see [External Services via the Environment Template, not a new
template type](#external-services-via-the-environment-template-not-a-new-template-type) and [Service names are per
document](#service-names-are-per-document)).

The [§5](../wiki/2023-09-Template-Schemas.md#5-action) table of default timeouts gains the four Service actions, with a
note that a `timeout` on `onRun` is measured from launch and that its expiry is an instance failure, and
[§6.1](../wiki/2023-09-Template-Schemas.md#61-embeddedfiletext) adds `Service.File.<name>` for a Service's embedded
files.

### Depending on a Service

RFC 0010's pull request also adds numbered constraints to §3.2 and numbered items to the §4 item list, starting from the
same numbers this pull request uses. RFC 0010 merges first. When this pull request is rebased onto it, this pull
request's §3.2 constraints and its §4 item 3, `dependencies`, will be numbered after RFC 0010's, and every reference to
them in this RFC and the wiki, such as "§3.2 constraint 3" and "§4 item 3", will be updated to match.

A Step, a Service, or a Job Environment that uses a Service lists it in its `dependencies`, in the same list as the
Steps it depends on (see [Dependencies are declared, and one list names both
kinds](#dependencies-are-declared-and-one-list-names-both-kinds)).

* [§3.2](../wiki/2023-09-Template-Schemas.md#32-stepdependency) adds the `service` key to `<StepDependency>`, satisfied
  when the Service is READY, and lets a Service list a Step, satisfied when the Step completes. It says how the key
  combines with RFC 0010's `step` and `environment` forms, which an `ENV_PARAMS` document may use, and gives the
  constraints: what each key may name, no two entries naming one Step or one Service, exactly one key per entry
  (replacing RFC 0010's constraint 1), and, in constraint 3, the one acyclic graph over a Job Template's Steps and
  Services. That graph has an edge from each entity to each Step and Service entry it lists, and from each Step and
  Service whose Sessions enter a Job Environment to each Service that Environment lists, with no exception. Constraint 3
  also says at which stage a cycle is reported.
* [§3](../wiki/2023-09-Template-Schemas.md#3-steptemplate) item 4 says that a Step's `dependencies` may name Services,
  and the paragraph after the item list that a Step need not repeat a Step dependency that a Service it lists already
  carries. *stepEnvironments* constraint 3 points to the rule that a Step Environment has no `dependencies` of its own.
* [§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 3 adds `dependencies` to an Environment: the Services
  whose clients it configures. Every entity whose Sessions enter the Environment depends on each Service it lists.
* [§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service) item 4 gives a Service's own `dependencies`: the
  Steps it waits for, the Services whose endpoints it reads, and the Environments it requests or declines, and which
  values its `environment:` entries may read.
* [§9.1](../wiki/2023-09-Template-Schemas.md#91-service-scope) defines a Service's scope from these lists, says when it
  is determined, and rejects an inline Service whose scope is empty and an `externalServices` entry that nothing in the
  Job Template lists. A scope is normally determined at template validation, and when the Job is created only where it
  depends on which Environments a Step's Sessions enter and that is not known before then; an inline Service whose scope
  is empty is rejected at the same stage. An external Service whose scope is empty is never started.

### Services run inside Environments

A Service Session enters Environments by RFC 0010's rules for a Step's Sessions, so the Conda, Rez, or container
Environments that provision a Job's Tasks provision its Services too. A Service that needs different software, or none
of an Environment, says so with `environment:` entries as a Step does (see [Service Sessions enter the Job's
Environments by the Steps' rule](#service-sessions-enter-the-jobs-environments-by-the-steps-rule)).
[§4](../wiki/2023-09-Template-Schemas.md#4-environment) item 3 and the [Services](../wiki/How-Jobs-Are-Run.md#services)
section of How Jobs Are Run state this, with one difference from a Step: a Service chooses among the Environments of
its own document and of the Environment Templates attached before it. A Job Template's Service chooses among all of the
Job's Environments, and an Environment Template's Service among none of the Job Template's or a later attachment's. A
Service belongs to no Step, so it enters no Step Environment. How Jobs Are Run also gives the order of environment
variables in a Service's actions: the Environments' in order, then the Service's own `variables`, then those its
`onEnter` sets.

An Environment that lists a Service waits for that Service to be READY, so the Service's own Sessions must not enter it.
There is no exception for this: a template in which they would is rejected as a cycle by §3.2 constraint 3 (see [An
exception for an Environment that lists the Service](#an-exception-for-an-environment-that-lists-the-service)). The
author keeps the Service out with RFC 0010's means: an `ON_REQUEST` client Environment that the Steps request, or a
disabled entry by which the Service declines a `BY_DEFAULT` one.

An Environment Template has no Steps, and its author writes its Environment directly, so
[§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) item 6 constraint 5 allows its Services only
disabled `environment:` entries, each with a literal `enableIf: false` and no *parameters*. A disabled entry declines
the document's own `BY_DEFAULT` Environment, which would otherwise be a cycle when it lists the Service, or an earlier
attachment's `BY_DEFAULT` Environment that the Service does not need. Its name resolves by RFC 0010's rules for a
Step's entry, with the Service's own document in place of the Job Template and the earlier attachments in place of the
attached ones. Declining an `ALWAYS` Environment is an error, and an entry for an Environment from a document that does
not list `ENV_PARAMS` has no effect, as RFC 0010 gives for a Step. Requesting an earlier attachment's Environment, or
supplying values to it, is not provided for: a request would make the Service depend on another document's Environment
being attached, and values would depend on its parameter definitions, while a decline depends only on the
Environment's name and `activation`. The [Services from Environment
Templates](../wiki/How-Jobs-Are-Run.md#services-from-environment-templates) section of How Jobs Are Run explains these
rules for queue administrators.

[§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service) item 5 combines a Service's `hostRequirements`
with those of the Environments its Sessions enter, by RFC 0010's rules for a Step's combined host requirements, and
places the Service Session only on a host that satisfies them. Item 5 also says that RFC 0010's rules for empty,
discarded, and one-expression host requirements (its [Host
requirements](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md#host-requirements))
apply to a Service's own `hostRequirements` as they do to a Step's, so that implementations read them the same way.
[§3.3](../wiki/2023-09-Template-Schemas.md#33-hostrequirements) now describes requirements for a Service as well as a
Step. Its constraint 1, that at least one of *amounts* or *attributes* is given, does not apply to a Service: §9 item 5
applies RFC 0010's rule for an empty `hostRequirements`, and every document that lists `SERVICE` also lists
`ENV_PARAMS`. When this pull request is rebased onto RFC 0010, a Service is added to that constraint's exception.

### Wrap hooks

Under `WRAP_ACTIONS`, a wrapping Environment that a Service Session enters wraps the Service's actions, so a Service
runs inside the container or under the remote launcher that wraps the Tasks.
[§4.3](../wiki/2023-09-Template-Schemas.md#43-environmentactions) item 5 adds the four `onWrapService*` hooks, and its
`WRAP_ACTIONS` constraint 6 replaces RFC 0008's rule 1 when `SERVICE` is declared: a wrapper must define the hook for
every kind of action that a kind of Session entering it may run. Constraint 6 gives the table of actions and hooks and
says when the check is made, that a failed `onWrapService*` hook has the effect the wrapped action's failure would have,
and that the wrapped `openjd_env` and `openjd_service_ready` lines are read from the wrap script's stdout. §4.3's rule
that an Environment defines `onEnter` or `onExit` is also met by an Environment that defines at least one wrap hook and
every hook that the `WRAP_ACTIONS` constraints require of it, which with `SERVICE` may be the hooks for Service Sessions
without `onWrapTaskRun`. [§4.3.1](../wiki/2023-09-Template-Schemas.md#431-wrap-hook-template-variables) adds the
`WrappedService.*` variables, the port names, numbers, bind addresses, and protocols that a wrapper needs to forward the
Service's ports, and what a wrapper that gives the process its own network namespace must do. The list of format string
scopes in [§4](../wiki/2023-09-Template-Schemas.md#4-environment) adds `Service.*` and `WrappedService.*`, and says that
every `Wrapped*` group is in scope throughout a hook's `<Action>`, including its `timeout` and `cancelation`, and it
extends to `WrappedService.*` the rule that rejects a `Wrapped*` reference outside its hooks. `WrappedAction.*` is
available in the `onWrapService*` hooks as in RFC 0008's, and §4.3.1 gives a Docker example that forwards each port,
with a variant that binds only `bindAddress`. The [Sessions](../wiki/How-Jobs-Are-Run.md#sessions) section of How Jobs
Are Run says that a wrapper that a Service Session enters defines the `onWrapService*` hooks as well. For a wrapper
attached from an Environment Template, constraint 6 and the check of the `onWrapService*` hooks are both made when the
Job is created, from the combined Job
([§1.2.2](../wiki/2023-09-Template-Schemas.md#122-services-from-environment-templates) item 4; see [Backward
compatibility](#backward-compatibility)).

### Reading the endpoint

A Step script reads a Service's endpoint through the `Service.*` scope, which the scheduler fills in when it places the
Service (see [Endpoint as three scalar values](#endpoint-as-three-scalar-values) and [Passing the endpoint through
environment variables](#passing-the-endpoint-through-environment-variables)).

* [§7.3.1](../wiki/2023-09-Template-Schemas.md#731-value-references) adds `Service.<name>.<port>.port`, `bindAddress`,
  and `connectAddress`, and `Service.File.<name>`. It also extends PATH `Param.*` values to a Service's *variables* and
  script, and `Session.WorkingDirectory` and the path mapping values to its script.
* [§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service), after its item list, gives the format string
  scopes of a Service and the visibility rule: an entity sees a Service's `port` and `connectAddress` only if it lists
  the Service in its `dependencies`, only the Service itself sees `bindAddress`, and `Service.*` is never in scope in a
  field resolved at job creation. A Service's own `variables`, and those its `onEnter` sets, are not passed to the
  entities in its scope ([§9](../wiki/2023-09-Template-Schemas.md#9-service-extension-service) item 9); they read the
  endpoint, not the Service's environment.
* [§3.6.2](../wiki/2023-09-Template-Schemas.md#362-let-binding-scope-summary) adds rows for `<Service>.let` and
  `<ServiceScript>.let` (and §7.3.1's let binding row names them), and lets the `let` of a Step script, a simple action,
  and an Environment script read the `Service.*` values in scope.
* [§7.4](../wiki/2023-09-Template-Schemas.md#74-template-processing-stages) adds `Service.*` to the values unknown
  before task execution, evaluates `<Service>.let` at job creation, and adds a paragraph on service execution, the stage
  at which a Service's own actions are resolved on the service host.
* The Expression Language adds `Service.File.<name>` and a [Service
  Symbols](../wiki/2026-02-Expression-Language.md#service-symbols) table to
  [§1.2.2](../wiki/2026-02-Expression-Language.md#122-built-in-symbol-types).
  [§2.2.4](../wiki/2026-02-Expression-Language.md#224-string-functions) adds `join_host_port`, `split_host_port`,
  `is_ipv4`, and `is_ipv6`, with examples, because an IPv6 address must be bracketed wherever an address and a port are
  joined. [§2.2.6](../wiki/2026-02-Expression-Language.md#226-script-embedding-and-serialization) adds `repr_sh` of an
  `int` and of a `list[int]`, so that a port number or `WrappedService.Ports` can be passed to a shell command without a
  `string()` conversion. Their results are exact: an `int`'s decimal form, or a `list[int]`'s decimal forms joined by
  single spaces, because a decimal integer needs no quoting for a shell to read it back as one word. These functions
  and signatures are available only in a document that lists `SERVICE`.

### Running a Service

[How Jobs Are Run](../wiki/How-Jobs-Are-Run.md#services) gains a Services section for authors and implementers:

* [Services](../wiki/How-Jobs-Are-Run.md#services) explains what a Service and its Service Session are, how a Service
  Session enters Environments, that an Environment's `onEnter` also runs once per Service Session, that a Service
  Session receives path mapping rules for the service host, and that placement is up to the scheduler, provided that
  `connectAddress` and `port` reach the service process from every host in the scope.
* [Service lifecycle](../wiki/How-Jobs-Are-Run.md#service-lifecycle) defines the four states and the constraints a
  scheduler must satisfy: ports and addresses fixed before any action runs, ordering against `dependencies`, Tasks held
  until their Services are READY, stop order, one Session and one `onRun` at a time, when a Service Session ends and
  what happens before it does, a new Service Session after one ends, lazy start, suspension of a `KEEP` Service, and
  probes in flight when `onRun` exits. The Basic Example [Execution order](#execution-order) shows the order.
* [Service failure and restart](../wiki/How-Jobs-Are-Run.md#service-failure-and-restart) defines instance failures and
  start failures and the scheduler's steps after one: canceling or keeping running Tasks, relaunching under the restart
  policy, FAILED, relocation, host loss, `RERUN` and Step dependencies, and the Services that list a relaunched one. It
  ends with advice for authors of stateful Services (see [`onRun` exiting is always a
  failure](#onrun-exiting-is-always-a-failure) and [Start failures consume a
  restart](#start-failures-consume-a-restart)).
* [Services from Environment Templates](../wiki/How-Jobs-Are-Run.md#services-from-environment-templates) describes
  queue-supplied Services and their client Environments, as in the [queue-supplied
  cache](#a-queue-supplied-cache-with-client-configuration) example.
* [Stdout/Stderr Messages](../wiki/How-Jobs-Are-Run.md#stdoutstderr-messages) adds `openjd_service_ready`, says that
  `openjd_fail` from a Service's `onRun` is itself an instance failure, lets a Service's `onEnter` emit `openjd_env` and
  `openjd_unset_env` for the Service's own later actions, says which messages are honored in a Service Session and that
  the Session environment variables are set there, and adds the `onWrapService*` hooks to the wrap scripts whose stdout
  is scanned. The base specification says only that `openjd_fail` "indicates why an Action has failed"; existing
  runtimes already fail an action that emits it whatever its exit status, and this RFC states the rule for Service
  actions so that `onEnter`, `onRun`, and `onExit` behave alike.

### `attr.worker.preemptible`

[§3.3.2.1](../wiki/2023-09-Template-Schemas.md#3321-attributecapabilityname) adds the standard attribute
`attr.worker.preemptible`, `true` or `false`. It is not gated by any extension: any Step may require it, and Workers
should advertise it. A host that does not advertise it does not match `anyOf: ["false"]`. This RFC introduces it
because a long-lived Service is the first entity in the specification whose correctness depends on not being preempted
mid-scope, and How Jobs Are Run advises authors of stateful Services to require it.

### Validation

[§9.9](../wiki/2023-09-Template-Schemas.md#99-validation) indexes the rules the extension adds and the section that
states each, and says which rules are checked when the Job is created or at submission rather than at template
validation. The conformance suite's [README](../conformance-tests/2023-09/SERVICE/README.md) describes the rules its
tests verify and lists every test.

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

`COMMAND` runs an action while *onRun* is running, which nothing else in the specification does. The alternative is a
wrapper script that backgrounds the binary and polls it, which is the boilerplate OpenJD exists to remove; the rules in
[§9.7.1](../wiki/2023-09-Template-Schemas.md#971-concurrency-of-onhealthcheck-with-onrun) are the cost of avoiding it.
[Issue #133](https://github.com/OpenJobDescription/openjd-specifications/issues/133), monitoring for Environment actions
in general, should adopt the same vocabulary.

### Why the protocol is declared on the port

A distributed scheduler publishes or forwards each port through a container mapping, a firewall
rule, or a NAT entry, and every one of those is defined per protocol. The `protocol` field tells it
which, in the place the port is declared.

### Ports are named

A port has a name, and a number only if the author fixes one. Dockerfiles and Compose files can
expose bare numbers because each container has a network namespace of its own, so two copies of
`6379` never collide. Services of different Jobs, or two Services of one Job, can share a host
namespace, so the scheduler has to be free to choose the number. A port whose number is chosen at
placement still needs a handle in the template, and the name is that handle:
`Service.Cache.main.port`. The name also carries the contract of an external Service. A Job
Template's `externalServices` entry and the queue's Service match on port names, because each queue
may choose its numbers, or let the scheduler choose them. An author who needs a fixed number
writes it as `port: 6379`, or takes it from a Job Parameter with `port: "{{ Param.CachePort }}"`;
the name stays the same either way, so nothing that references the port changes.

### `restartPolicy.completedTasks` is per-Service and required when relaunch is allowed

The two motivating examples pull in opposite directions: a cache loses nothing of consequence when it restarts, while a
coordinator that loses its state has invalidated every result produced against it. No single behavior is correct, so the
policy is per-Service, and because neither answer is safe to assume the field has no default: an author who allows a
relaunch must say what a relaunch means for completed Tasks. When `maxRestarts` is 0 no relaunch can happen and the
field is needed only when a Service this one lists begins a new Service Session, where an omitted value is read as
`RERUN`, or when a scheduler would suspend the Service, which needs `KEEP`.

The same distinction decides what happens to Tasks running at the moment of failure (requeued under
`RERUN`, left to finish or fail on their own under `KEEP`) and whether a scheduler may suspend an
idle Service (only under `KEEP`, since under `RERUN` suspension would discard every completed Task).

The values name what the author knows, whether the Tasks' results depend on the instance, rather
than what the scheduler does with them. Naming them by Task outcome would not fit: under either
value a Task that completed against the last instance keeps its result when the Service finally
fails (step 4 of [Service failure and restart](../wiki/How-Jobs-Are-Run.md#service-failure-and-restart)), and under
either value a Task whose
Service cannot be restarted fails.

A `RERUN` requeue does not count against a Task's retries because the Task did nothing wrong. The
Service's instance was lost, and charging that to every Task in the scope would fail a Job whose
Tasks each succeed, for a fault that `maxRestarts` already bounds. Failing every Task the moment
its Service fails is what `maxRestarts: 0` does.

The field limiting relaunches is `maxRestarts`, not `maxAttempts`, because it counts restarts: 0
means the Service runs once. A count of attempts would need 1 for the same meaning, and a minimum
of 1, and would read differently from the name of the `restartPolicy` that holds it.

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
Service. One vocabulary means one cycle check over one graph. RFC 0010's `environment:` entry joins
the same list for the same reason: it says what a Step or Service needs in order to run. It orders
nothing by itself, but it decides which Environments a Session enters, and so which Services the
entity depends on through them.

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

### Service Sessions enter the Job's Environments by the Steps' rule

A Service Session chooses its Environments by RFC 0010's rules, exactly as a Task Session does, so
that existing provisioning Environments apply to Services unchanged and a Service that needs
different software, or none of an Environment, says so the same way a Step does. Restating those
rules for Services would only give two copies that could drift apart. Every entity whose Sessions
enter an Environment that lists Service `X` depends on `X`, because the Environment reads `X`'s
endpoint and cannot be entered until `X` is READY. That one rule covers Steps and Services alike: a
Step joins `X`'s scope, and a Service waits for `X` as if it listed it.

A Service chooses only among the Environments of its own document and of the Environment Templates
attached before it. For a Job Template's Service that is every Environment, as for a Step. A
queue's Service, though, must work with Job Templates its author has never seen, and an
Environment a later document adds could list a Service and so close a cycle that no single author
wrote. With the rule, every edge from entering an Environment points to a Service of the same
document or an earlier one, so a cycle never spans documents, and each author can keep their own
document acyclic.

Applied to `X` itself, the rule makes `X` wait for itself, and that is rejected as a cycle. The
template author keeps `X`'s Sessions out of its client Environment with the means RFC 0010 already
gives: an `ON_REQUEST` client Environment that the Steps request, or a disabled entry by which `X`
declines a `BY_DEFAULT` one (see [Services run inside Environments](#services-run-inside-environments),
and RFC 0010's [Requesting an Environment from a
Step](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md#requesting-an-environment-from-a-step)
for the disabled entry).

An Environment Template's Service may also decline an earlier attachment's `BY_DEFAULT` Environment.
A decline adds no edge to another document: it can let the Service's Sessions enter a later member
of an `exclusiveGroup`, but that member is of the Service's own document or an earlier one, so any
cycle that results is one its author can see, and it is rejected as usual. Without the decline, two
of a queue's Environment Templates could be incompatible only because of the order in which they are
attached. The decline does not reach an Environment from a document that does not list
`ENV_PARAMS`, which RFC 0010 keeps in every Session that may enter it, so that an Environment
written before that extension cannot be left out by a later document; a Service is held to that
exactly as a Step is.

### `onHealthCheck` is an action of the Service

The alternative is an `<Action>` inside `healthCheck`. That leaves it outside `script:`, with no
principled claim on `let` bindings, embedded files, or the same format-string scopes as the other
actions. Making it a fourth `<ServiceActions>` entry gives every action of a Service one scope rule.
The `healthCheck` object keeps the policy; the action keeps the command.

### Start failures consume a restart

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

## Prototype

The prototype is commit `e856d80a`, the head of the `service-extension` branch of
[mwiebe/openjd-rs](https://github.com/mwiebe/openjd-rs/tree/service-extension), developed alongside this RFC and built
on RFC 0010's `env-params-prototype` branch at commit `23ba98f`. With that base the prototype passes the ENV_PARAMS
conformance tests of RFC 0010 at `74f8733`. It implements the extension in `openjd-model`, `openjd-expr`,
`openjd-sessions`, and `openjd-cli`, where `openjd run` is a single-host scheduler for Services. Its `openjd check` and
`openjd run` pass all 374 tests under `conformance-tests/2023-09/SERVICE` at this RFC's head.

These parts of the proposal changed while the prototype was developed alongside it:

1. **No `runScope`.** Earlier drafts gave an Environment a `runScope`, the kinds of Session (`TASK`, `SERVICE`) that
   enter it. Building SERVICE on the ENV_PARAMS prototype meant two mechanisms deciding which Sessions enter an
   Environment, by kind and by request. The RFC dropped `runScope`, and a Service Session now chooses its Environments
   by RFC 0010's rules, as a Task Session does (see [`runScope` as a list of Session
   kinds](#runscope-as-a-list-of-session-kinds)).
2. **No exception for a client Environment.** Earlier drafts, and the prototype until it was brought up to date, kept a
   Service's Sessions out of an Environment that lists the Service. Each later rule about which Sessions enter an
   Environment needed its own text for that exception: RFC 0010's split of `ALWAYS` from `BY_DEFAULT`, a disabled entry,
   an `exclusiveGroup`. The RFC dropped the exception, so entering such an Environment is a cycle that §3.2 constraint 3
   rejects, naming the Environment, and the template says how the Service stays out (see [An exception for an
   Environment that lists the Service](#an-exception-for-an-environment-that-lists-the-service)).
3. **Services follow RFC 0010 exactly as Steps do.** Rebasing the prototype onto newer ENV_PARAMS prototypes kept
   raising the same question for each new ENV_PARAMS rule: does it apply to a Service? The RFC now defers to RFC 0010
   with "Step" read as "Service" instead of restating its rules. In the prototype, a Service is one more requester in
   the same pass at Job creation as the Steps: an `exclusiveGroup` supersedes its Environments, the limit on
   `environment:` entries applies per Service, and each Service has its own list of Environment statuses
   (`CreatedJob::service_environment_statuses`). The order in which Job creation reports a Service's errors relative to
   the Steps' is left to implementations; the prototype reports them after the Steps' in each §7.4.1 step of RFC 0010.
4. **A Service enters only Environments of its own and earlier documents.** When a queue's Service could enter every
   Environment of the Job, an Environment that a later document added could list a Service and close a cycle that no
   single document contains. With this rule, every cycle is within one document (see [Service Sessions enter the Job's
   Environments by the Steps' rule](#service-sessions-enter-the-jobs-environments-by-the-steps-rule)).
5. **An Environment Template's Service may decline an earlier attachment's Environment.** An audit of the
   earlier-documents rule found that an earlier attachment's `BY_DEFAULT` Environment with a parameter that has no
   default, or a `BY_DEFAULT` wrapper without the `onWrapService*` hooks, failed every Job that used a later
   attachment's Service, so two Environment Templates could be incompatible only because of their attachment order.
   [§1.2](../wiki/2023-09-Template-Schemas.md#12-environment-template) item 6 constraint 5 now lets the Service decline
   such an Environment with a disabled entry. An `ALWAYS` wrapper, or one from a document that does not list
   `ENV_PARAMS`, still cannot be declined.
6. **Smaller rules the prototype made explicit.** `openjd_fail` from `onRun` is itself an instance failure; every
   `Wrapped*` group is in scope in a hook's `timeout` and `cancelation`; a Step's Environments are exited before a
   Service whose scope ends with the Step is stopped; a Service's embedded files stay in place until its Session ends;
   the `STDOUT` heartbeat deadline is re-armed by each line; the Services that list a Service that begins a new Service
   Session are stopped and restarted in dependency order; `repr_sh` accepts `int` and `list[int]`; and RFC 0010's rules
   for empty, discarded, and one-expression host requirements apply to a Service's own `hostRequirements`.

These were hard to implement or are left open:

1. **Two actions at once.** The existing Session runs one action at a time, with one log stream and one cancelation
   target. Running `onHealthCheck` while `onRun` runs needed a second action slot with its own cancelation, and the
   attribution rules of [§9.7.1](../wiki/2023-09-Template-Schemas.md#971-concurrency-of-onhealthcheck-with-onrun).
2. **Stop order on failure.** When a listed Service fails or begins a new Session, the prototype can end its Session
   before it stops the READY Services that list it, so a dependent's `onExit` can run after the listed Service's. The
   specification's order is clear; the prototype's scheduler would need restructuring to follow it in every case.
3. **Questions the specification leaves to implementations.** Whether a port released by one Service Session may be
   given to a later one in the same Job, and what a runner without Task retries, such as `openjd run`, does with a Task
   that fails against an UNREADY `KEEP` Service. For ports, the prototype never gives a released number to a different
   Service within a run, though a Service's own fixed `port` is granted again to its later Sessions. A Task that fails
   against an UNREADY `KEEP` Service fails the run.

## Implementation Impact

- **Rust (openjd-rs)**: The [prototype](#prototype) implements the schema, validation, and job-creation rules in
  `openjd-model`, the host and port functions in `openjd-expr`, the Service Session in `openjd-sessions`, and a
  single-host scheduler for `openjd run` in `openjd-cli`. Its largest single piece was the Service Session: the
  existing Session held one current action, one log stream, and one cancelation target, and running `onHealthCheck`
  alongside `onRun` needed a second action slot with its own cancelation and per-action attribution on captured
  output. The health phase adds a probe loop that outlives readiness, counts consecutive failures, and turns the
  threshold into a cancelation of `onRun`.
- **Python (openjd-model, openjd-sessions)**: The Python packages are intended to become bindings
  over openjd-rs. The `v0` releases of `openjd-model-for-python` and `openjd-sessions-for-python`
  would therefore not gain this extension; a `v1` built on the bindings would inherit it, exposing
  the new models, the Service Session, and the `Service.*` scope.
- **Schedulers**: This is where most of the work lives. A scheduler must place Services, allocate
  ports, guarantee cross-host reachability over each port's protocol, gate Task scheduling on
  readiness, keep probing after READY, track instance failures, implement `KEEP`/`RERUN`, and stop
  Services at scope end. Because `SERVICE` requires `ENV_PARAMS`, it also decides which Environments
  each Service Session enters and combines a Service's host requirements with theirs, using the
  machinery RFC 0010 already requires for Steps. A
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

An earlier draft gave external Services an implicit scope of every Step, so that a queue's Service ran for every Job
whether or not the Job used it. Rejected for the same reason: it was an edge no document declared. Under the scope
rules, a queue Service runs for a Job exactly when some Step falls in its scope by the rules of
[§9.1](../wiki/2023-09-Template-Schemas.md#91-service-scope): for example, the Step lists it, the Step's Sessions enter
an Environment that lists it, or the Step is in the scope of a Service that depends on it.

### `runScope` as a list of Session kinds

Earlier drafts of this RFC added `runScope: [ <RunScopeName>, ... ]` to `<Environment>`, a list of the kinds of Session
(`TASK`, `SERVICE`) the Environment is entered in, defaulting to `[TASK]` for an Environment that lists a Service and to
every kind otherwise. This RFC replaced it with RFC 0010's `activation` and `enableIf` on an Environment and its
`environment:` dependency entry, which it depends on. Selection by kind was mostly a stand-in for selection by who
asked: an Environment "for Services only" is one that each Service requests and no Step does. A list of kinds would also
grow with every extension that adds a kind of Session. The one rule that was about kinds, that an Environment reading a
Service's endpoint cannot run in that Service's Session, is not a rule of its own either: it is the cycle check of
[`<StepDependency>`](../wiki/2023-09-Template-Schemas.md#32-stepdependency) constraint 3. RFC 0010 rejects a list of
Session kinds for `activation` for the same reason; see its [`activation` as a list of Session
kinds](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md#activation-as-a-list-of-session-kinds).

### An exception for an Environment that lists the Service

An earlier draft of this RFC said that a Service's Sessions do not enter an Environment whose
`activation` has every Session enter it when that Environment lists the Service, so that a client
Environment needed only its `dependencies` entry. Rejected because it makes a Service's Sessions
differ from a Step's for a reason the template does not state: listing a Service would also, out of
sight, change where the Environment runs. It interacts with every later rule about which Sessions
enter an Environment, such as RFC 0010's split of `ALWAYS` from `BY_DEFAULT`, a disabled entry, and
an `exclusiveGroup`, and each interaction needs its own text. Without it, the rule is one cycle
check with a message that names the cycle and the Environment that closes it, and the author states
the intent with an `ON_REQUEST` client Environment or a disabled entry on the Service. The cost is
one entry in a template that defines a Service and its client Environment together, such as the
[queue-supplied cache](#a-queue-supplied-cache-with-client-configuration).

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
