* Feature Name: Feature Bundle 1
* RFC Tracking Issue: <https://github.com/OpenJobDescription/openjd-specifications/issues/92>
* Start Date: 2025-10-03
* Specification Version: 2023-09 extension FEATURE_BUNDLE_1
* Accepted On: 2026-01-09

## Summary

This RFC proposes a collection of enhancements to the OpenJD specification that
address practical limitations met in production use cases. The changes include:

* Increased limits for parameter counts and name lengths
* Enhanced format string support for
  * `timeout` property in `<Action>`
  * `min` and `max` properties in `<AmountRequirement>`
  * `notifyPeriodInSeconds` property in `<CancelationMethodNotifyThenTerminate>`
* Improved control over embedded file line endings
* Syntax sugar for common script interpreters in `<Action>` objects

## Basic Examples

### Increased Name Length Limits

```yaml
specificationVersion: jobtemplate-2023-09
name: LONGPROJECTNAME_EPISODE23_SEQUENCE54_SHOT23_REV12_BACKGROUND_CAMERA001
```

### Enhanced Timeout Format Strings

#### Timeout Property in \<Action\>

```yaml
parameterDefinitions:
- name: OnRunTimeoutSeconds
  type: INT
  minValue: 1
  description: The number of seconds the onRun action can operate before encountering a timeout.
  userInterface:
      label: Run Timeout Seconds
      control: SPIN_BOX


steps:
- name: CliScript
  script:
    actions:
      onRun:
        timeout: "{{Param.OnRunTimeoutSeconds}}"
        command: bash
        args: ['{{Task.File.Run}}']
```

#### Min and Max Properties in \<AmountRequirement\>

```yaml
parameterDefinitions:
- name: CpuMinAmount
  type: INT
  minValue: 1
  description: The minimum number of vCpus that a worker needs to pick up this job.
- name: CpuMaxAmount
  type: INT
  minValue: 1
  description: The maximum number of vCpus that a worker needs to pick up this job.
- name: MemoryMinAmount
  type: INT
  minValue: 4
  description: The minimum amount of memory in GiB that a worker needs to pick up this job.
- name: MemoryMaxAmount
  type: INT
  minValue: 64
  description: The maximum amount of memory in GiB that a worker needs to pick up this job.

steps:
- name: StepOne
  script:
    actions:
      onRun:
        command: python
        args: [ "-c", "print('This is StepOne - it is light on resources')" ]
  hostRequirements:
    amounts:
    - name: amount.worker.vcpu
      min: "{{Param.CpuMinAmount}}"
      max: "{{Param.CpuMaxAmount}}"
    - name: amount.worker.memory
      min: "{{Param.MemoryMinAmount}}"
      max: "{{Param.MemoryMaxAmount}}"
```

#### notifyPeriodInSeconds Property in \<CancelationMethodNotifyThenTerminate\>

```yaml
parameterDefinitions:
- name: NotifyPeriod
  type: INT
  minValue: 1
  maxValue: 600
  default: 120
  description: How long to wait for a graceful shutdown before a terminal signal is sent

steps:
- name: PythonScript
  script:
    actions:
      onRun:
        command: python
        args: ['{{Task.File.Run}}']
        cancelation:
          mode: NOTIFY_THEN_TERMINATE
          notifyPeriodInSeconds: "{{Param.NotifyPeriod}}"
```

### EOL Control in Embedded Files

```yaml
steps:
- name: RunBashOnWindows
  hostRequirements:
    attributes:
    - name: attr.worker.os.family
      anyOf:
      - windows
  script:
    actions:
      onRun:
        args:
        - '{{ Task.File.run }}'
        command: bash
      embeddedFiles:
      - name: run
        type: TEXT
        runnable: true
        data: |
          #!/bin/bash
          echo 'Running'
        endOfLine: LF
```

### Script Interpreter Syntax Sugar

```yaml
steps:
- name: RunPythonScript
  python:
    args: ["--additional-argument"]
    timeout: 5
    cancelation:
        mode: "NOTIFY_THEN_TERMINATE"
        notifyPeriodInSeconds: 30
    script: |
      print('Hello from Python!')
```

Compare to

```yaml
steps:
- name: RunPythonScript
  script:
    actions:
      onRun:
        command: python
        args: ["{{Task.File.hello}}", "--additional-argument"]
        timeout: 5
        cancelation:
            mode: "NOTIFY_THEN_TERMINATE"
            notifyPeriodInSeconds: 30
    embeddedFiles:
      - name: hello
        filename: "hello.py"
        type: TEXT
        data: |
          print('Hello from Python!')
```

## Motivation

These enhancements address real-world limitations encountered in production
OpenJD deployments. The current specification imposes
constraints that have led to friction when applications require
extensive parameterization, cross-platform script compatibility, and simplified
workflow authoring.

These changes are bundled together as creating separate RFCs for each
of these improvements would be disproportionate to their individual scope.
Each addresses issues identified through real-world usage,
and while individually minor, together they improve the
developer experience and operational flexibility of OpenJD templates.

### Use Cases Supported

1. **Automated Naming**: When a template is generated programmatically, it's
natural to concatenate identifiers from the input to get a unique name. The
current length limits prevent that from working naturally. Identifier names can
similarly be generated by concatenating identifiers, so we want to treat
them similarly.

2. **Cross-Platform Compatibility**: Explicit EOL control ensures consistent
behavior across different operating systems, particularly important for
embedded scripts and configuration files.

3. **Simplified Template Authoring**: Syntax sugar for common interpreters
reduces boilerplate and makes templates more readable and maintainable.

4. **Dynamic Configuration**: Increased parameterization combined with enhanced
format string support enables configuration values to depend on scene-specific
inputs or other job parameters rather than being hardcoded in templates. Format
strings in timeout, amount requirements, and cancelation settings allow these
values to adapt based on job inputs. This flexibility is valuable both during
experimentation, where modifying a parameter and resubmitting is faster than
editing source files, and in production workflows where parameters vary based
on job inputs.

## Prior Art

### Parameter Limits

* **Deadline 10**: No upper limit, most plugins have ~20 options. With outliers
such as VRED with 61 options and 3dsMax with 2185 options.

### Script Interpreter Support

* **GitHub Actions**: Provides `shell` property with predefined options

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
