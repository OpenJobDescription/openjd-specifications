# Environment Name Conventions

Before reading this we recommend reading [How Jobs Are Run](How-Jobs-Are-Run).

A Job often gets its software from **Environments** that the render management system attaches from Environment
Templates, such as a queue's Conda **Environment**. The Job Template and those Environment Templates are usually written
by different people, and a Job Template doesn't know in advance which **Environments** a given system attaches. They
can only work together through names that both of them use.

This page lists names that Job Templates and Environment Templates should use for common kinds of **Environments**, so
that one Job Template runs unchanged on systems that provide software in different ways. The specification doesn't
require any of these names. They are conventions: a template that follows them works with more of the templates that
other people write.

## Why names matter

Three kinds of names connect a Job Template to an attached **Environment**:

* **Job Parameter names.** When a Job Template and an Environment Template both define a Job Parameter with the same
  name, the two definitions are merged into one parameter
  ([Template Schemas §1.2.1](2023-09-Template-Schemas#121-merging-environment-template-parameter-definitions)). A Job
  Template that defines `CondaPackages` sets the packages that the queue's Conda **Environment** installs, and a
  submitter's tools can show one field for it. This works without any extension.
* **Environment names.** With the ENV_PARAMS extension, introduced in
  [RFC 0010](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md),
  a Step asks for an **Environment** by name, with an `environment:` entry in its `dependencies`. An entry for `Conda`
  doesn't find an **Environment** named `CondaQueueEnv`.
* **Environment parameter names.** With ENV_PARAMS, the entry gives values for the **Environment**'s parameters by
  name, such as `Packages`. A name that the **Environment** doesn't declare is an error, so both sides have to agree on
  it.

An **Environment** that follows these conventions serves both kinds of Job Template at once. Each of its Environment
parameters defaults to the matching Job Parameter, so a Job Template written before ENV_PARAMS configures it for the
whole Job through the Job Parameter, and a Job Template written for ENV_PARAMS configures it for each Step through the
Environment parameter.

## Recommended names

| Environment | Job Parameter | Environment parameter | Type | Meaning |
|-------------|---------------|-----------------------|------|---------|
| `Conda` | `CondaPackages` | `Packages` | STRING | Space-separated package specs. Empty means use the host's software. |
| `Conda` | `CondaChannels` | `Channels` | STRING | Space-separated channels. |
| `Rez` | `RezPackages` | `Packages` | STRING | Space-separated Rez package requests. |
| `Docker` | `DockerImage` | `Image` | STRING | The container image. |
| `Docker` | | `Mounts` | LIST[PATH] | Host paths to make visible at the same path in the container. Default `[]`. |
| `Docker` | | `Gpus` | STRING | The value for `docker run --gpus`. Empty, the default, means no GPUs. |

Each Environment parameter with a Job Parameter in its row defaults to it, as in `default: "{{Param.CondaPackages}}"`.
`CondaPackages`, `CondaChannels`, and `RezPackages` are the Job Parameters that Deadline Cloud's Conda and Rez queue
environments already use.

## Choosing among several

Each of these **Environments** provides software, and a Step normally wants one of them. With ENV_PARAMS, give each one
`exclusiveGroup: SoftwareProvider`. Each Step's **Sessions** then enter only the first of them, in the order they were
attached, that is enabled for that Step. Choose each one's `activation` by who should get it:

* Keep the default, `BY_DEFAULT`, for an **Environment** that Job Templates written before ENV_PARAMS rely on, such as
  Conda, so that they still get the software. Use `enableIf` to skip the Steps that ask for nothing.
* Use `ON_REQUEST` for an **Environment** that only the Steps asking for it should enter, such as Docker, which runs
  every action of a **Session** in a container.

A Conda **Environment** that follows these conventions:

```yaml
environment:
  name: Conda
  enableIf: "Env.Param.Packages != ''"
  exclusiveGroup: SoftwareProvider
  envParameterDefinitions:
    - name: Packages
      type: STRING
      default: "{{Param.CondaPackages}}"
    - name: Channels
      type: STRING
      default: "{{Param.CondaChannels}}"
  script: ...
```

A Job Template then writes an entry for each kind it can use, marks each `required: false`, and leaves the choice to
the system that attaches the **Environments**:

```yaml
steps:
  - name: SolveSfM
    dependencies:
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

The [samples](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples/v2023-09) follow these
conventions: `environment_templates/conda-env-params.yaml`, `environment_templates/docker-env-params.yaml`, and the
pipeline in `job_templates/video-sfm-composite.yaml`.

## Adding a convention

To propose names for another kind of **Environment**, such as Apptainer or Spack, open a pull request that adds rows to
the table. Use the tool's name for the **Environment**, a parameter name that says what the value is, and, for a Job
Parameter, the **Environment**'s name followed by the parameter's name.
