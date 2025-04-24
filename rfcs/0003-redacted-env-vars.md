- Feature Name: Redacted Environment Variables
- RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/85
- Start Date: 2025-04-09
- Specification Version: 2023-09 extension REDACTED_ENV_VARS
- Accepted On: (fill in with the date that the proposal was accepted: YYYY-MM-DD)

## Summary

Setting environment variables in an openjd Environment such that they are persisted in subsequent actions run while the Environment is still
active currently requires [echoing them to stdout with the openjd_env: key=value format](https://github.com/OpenJobDescription/openjd-specifications/blob/711dab30382579d060863581b56f5266c16430da/wiki/2023-09-Template-Schemas.md#4-environment)
which exposes potentially sensitive information such as credentials to logs. This RFC proposes a new token, openjd_redacted_env, which sets
environment variables exactly like openjd_env but defaults to redacting the potentially sensitive information from logs for the initial and
any future occurrences.

The feature is only used to redact the environment variable in log output. Environment variables for a process can be observed by other
processes on the same machine. Secure handling of secrets is still the responsibility of those authoring job templates.

## Basic Examples

This example shows a very basic (somewhat contrived) example where a job environment is responsible for initially retrieving and setting
credentials in an environment variable and then a step is run which consumes the credentials.

```yaml
specificationVersion: "jobtemplate-2023-09"
extensions:
  - REDACTED_ENV_VARS
name: Env Enter Setting Vars
description: |
  Setting environment variables in a way which won't expose secret values to logs

jobEnvironments:
  - name: JobEnvVars
    variables:
      PYTHONUNBUFFERED: "True"
    script:
      actions:
        onEnter:
          command: python
          args: ["{{Env.File.Enter}}"]
        onExit:
          command: python
          args: ["{{Env.File.Exit}}"]
      embeddedFiles:
        - name: Enter
          type: TEXT
          data: |
            print("Entering environment and setting var..")
            print(f"openjd_redacted_env: SECRETVAR=SECRETVAL")
        - name: Exit
          type: TEXT
          data: |
            import os
            # SECRETVAR is SECRETVAL here
            print(f"SECRETVAR is {os.environ.get('SECRETVAR')}")
steps:
  - name: ProcessWithPython
    script:
      actions:
        onRun:
          command: python
          args: ["{{Task.File.Run}}"]
      embeddedFiles:
        - name: Run
          type: TEXT
          data: |
            import os

            # SECRETVAR is SECRETVAL here
            print(f"SECRETVAR is {os.environ.get('SECRETVAR')}")
            # Run Application Consuming SECRETVAR..
```

Running this template with the currently proposed changes produces the following output.

```
0:00:00.000047  Open Job Description CLI: Session start 2025-04-11T21:50:33.781398+00:00
0:00:00.000109  Open Job Description CLI: Running job 'Env Enter Setting Vars'
0:00:00.000180
0:00:00.000218  ==============================================
0:00:00.000253  --------- Entering Environment: JobEnvVars
0:00:00.000285  ==============================================
0:00:00.000336  Setting: PYTHONUNBUFFERED=True
0:00:00.000647  ----------------------------------------------
0:00:00.000722  Phase: Setup
0:00:00.000761  ----------------------------------------------
0:00:00.000803  Writing embedded files for Environment to disk.
0:00:00.001017  Mapping: Env.File.Enter -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpfdql519m
0:00:00.001072  Mapping: Env.File.Exit -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpuhsmb_sg
0:00:00.001198  Wrote: Enter -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpfdql519m
0:00:00.001327  Wrote: Exit -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpuhsmb_sg
0:00:00.001613  ----------------------------------------------
0:00:00.001663  Phase: Running action
0:00:00.001697  ----------------------------------------------
0:00:00.001974  Running command /tmp/OpenJD/CLI-sessionj6z1b_nc/tmp8v1johcc.sh
0:00:00.002736  Command started as pid: 10327
0:00:00.002871  Output:
0:00:00.015208  Entering environment and setting var..
0:00:00.015296  openjd_redacted_env: SECRETVAR=********
0:00:00.017612  Process pid 10327 exited with code: 0 (unsigned) / 0x0 (hex)
0:00:00.017780  Open Job Description CLI: Running step 'ProcessWithPython'
0:00:00.017872
0:00:00.017914  ==============================================
0:00:00.017951  --------- Running Task
0:00:00.017983  ==============================================
0:00:00.018336  ----------------------------------------------
0:00:00.018390  Phase: Setup
0:00:00.018424  ----------------------------------------------
0:00:00.018467  Writing embedded files for Task to disk.
0:00:00.018607  Mapping: Task.File.Run -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpzne3spj4
0:00:00.018740  Wrote: Run -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpzne3spj4
0:00:00.019003  ----------------------------------------------
0:00:00.019052  Phase: Running action
0:00:00.019085  ----------------------------------------------
0:00:00.019278  Running command /tmp/OpenJD/CLI-sessionj6z1b_nc/tmpb5oq6jb_.sh
0:00:00.019996  Command started as pid: 10330
0:00:00.020098  Output:
0:00:00.031973  SECRETVAR is ********
0:00:00.035305  Process pid 10330 exited with code: 0 (unsigned) / 0x0 (hex)
0:00:00.035516
0:00:00.035570  ==============================================
0:00:00.035605  --------- Exiting Environment: JobEnvVars
0:00:00.035636  ==============================================
0:00:00.035933  ----------------------------------------------
0:00:00.036004  Phase: Setup
0:00:00.036045  ----------------------------------------------
0:00:00.036084  Writing embedded files for Environment to disk.
0:00:00.036274  Mapping: Env.File.Enter -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpxu9i4mh0
0:00:00.036328  Mapping: Env.File.Exit -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmplpkitulg
0:00:00.036449  Wrote: Enter -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmpxu9i4mh0
0:00:00.036570  Wrote: Exit -> /tmp/OpenJD/CLI-sessionj6z1b_nc/embedded_files1d4q40xw/tmplpkitulg
0:00:00.036944  ----------------------------------------------
0:00:00.036996  Phase: Running action
0:00:00.037030  ----------------------------------------------
0:00:00.037211  Running command /tmp/OpenJD/CLI-sessionj6z1b_nc/tmpeabs_4ig.sh
0:00:00.037885  Command started as pid: 10334
0:00:00.037987  Output:
0:00:00.049866  SECRETVAR is ********
0:00:00.053168  Process pid 10334 exited with code: 0 (unsigned) / 0x0 (hex)
0:00:00.053353
0:00:00.053418  Open Job Description CLI: All actions completed successfully!
0:00:00.053455  Open Job Description CLI: Local Session ended! Now cleaning up Session resources.

--- Results of local session ---

Session ended successfully

Job: Env Enter Setting Vars
Step: ProcessWithPython
Duration: 0.05513031499867793 seconds
Chunks run: 1
```

## Motivation

Customers currently have a method of setting environments in a way that persists in actions run while the environment is still active, however
it requires exposing those environment variable names and values to session logs. These variables will occasionally contain sensitive
information which customers may not wish to be exposed to their logs and visible with anyone who has access to those logs by default.
Workarounds such as applying data protection policies exist, but customers have [requested simpler methods](https://github.com/OpenJobDescription/openjd-specifications/issues/62)
of optionally hiding these values.

## Specification

```diff
diff --git a/wiki/2023-09-Template-Schemas.md b/wiki/2023-09-Template-Schemas.md
--- a/wiki/2023-09-Template-Schemas.md
+++ b/wiki/2023-09-Template-Schemas.md
@@ -989,7 +989,11 @@ Implementations of this specfication must watch STDOUT when running the `onEnter
 1. The regular expression `^openjd_env: (.*)$`. The captured value must be of the form `<varname>=<value>` where
    `varname` is the name of an environment variable, and `value` is the value to assign to it. The defined value of the
    given variable will be set for all actions that are run with the environment active.
-2. The regular expression `^openjd_unset_env: (.*)$`. The captured value must be of the form `<varname>` where
+2. The regular expression `^openjd_redacted_env: (.*)$`. The captured value must be interpreted identically to
+   openjd_env, and `<value>` shall be redacted with a fixed length string for this and any future occurrences from the
+   emitted STDOUT message. Requires the REDACTED_ENV_VARS extension, however supporting applications must honor the
+   redaction even when the extension is not specified.
+3. The regular expression `^openjd_unset_env: (.*)$`. The captured value must be of the form `<varname>` where
    `varname` is the name of an environment variable. The given environment variable will be unset as long as this
    environment is active. If an environment both sets and unsets a particular environment variable, then the unset takes
    precedence.

diff --git a/wiki/How-Jobs-Are-Run.md b/wiki/How-Jobs-Are-Run.md
--- a/wiki/How-Jobs-Are-Run.md
+++ b/wiki/How-Jobs-Are-Run.md
@@ -84,6 +84,10 @@ messages to convey information about the **Action** to the render management sys
 * `openjd_env: <var>=<value>` where `<var>` is the string name of an environment variable, and `<value>` is a string. This
   can only be emitted by the **Action** for entering an **Environment**. It defines the value of an environment variable for
   all subsequent **Action**s in the **Session** until the defining **Environment** is exited.
+* `openjd_redacted_env: <var>=<value>` has identical behavior to openjd_env except `<value>` shall be redacted by the
+  application running the action in the emitted stdout line and in any future lines. Requires the REDACTED_ENV_VARS
+  extension, however supporting applications must honor the redaction even when the extension is not specified.
 * `openjd_unset_env: <var>` where `<var>` is the string name of an environment variable. This can only be emitted by the
   **Action** for entering an **Environment**. This unsets the given environment variable for all subsequent **Action**s
   in the **Session** until the **Environment** that emitted it is exited.
```

## Design Choice Rationale

### openjd_env substitution

There are a number of different ways we could provide customers to go about redacting sensitive strings. openjd_redacted_env allows customers
to write templates nearly identically to how they do today. Solutions such as lists of keys for value redaction which needed to be maintained
elsewhere would likely be more error prone due to typos or simply forgetting to add the key to the list. Asking customers to actually include
the values themselves elsewhere would be asking them to further expose the very values they're trying to protect. We could also give
customers toggle commands to enable/disable redaction, though that would require more effort on the customer's part and might force them to
redact more than they intend.

### Behavior when REDACTED_ENV_VARS supported but not specified

In order to maintain as high a security bar as possible, this document proposes that the redaction behavior of openjd_redacted_env be honored
in supporting applications even when the extension is not specified, though the environment variable would not be set. This is a deviation
from standard extension behavior where without the extension none of the custom behavior would be followed.

## Prior Art

This feature is intended to provide nearly identical behavior to `openjd_env` except with protection of redacting `<value>` to give
customers a drop in replacement for cases handling sensitive environment variables.

The goal of this proposal is to protect secrets in a manner similar to [GitHub Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/about-secrets#using-your-secrets-in-workflows)
where the system will continue to redact them in the session logs once declared as redacted through openjd_redacted_env.

## Rejected Ideas

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
