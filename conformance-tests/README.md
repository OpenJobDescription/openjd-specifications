# OpenJD Conformance Tests

A conformance test suite for validating any OpenJD implementation against the specification. These tests define expected behavior that all compliant libraries should exhibit.

## Purpose

The test cases in this suite are implementation-agnostic. They specify:
- Templates that should pass or fail validation
- Jobs that should succeed or fail execution
- Expected outputs and behaviors

Any OpenJD library can use these tests to verify spec compliance.

## Structure

```
conformance-tests/
└── {spec_version}/
    ├── base/                    # Base specification tests
    │   ├── job_templates/       # Job template validation tests
    │   ├── env_templates/       # Environment template validation tests
    │   └── jobs/                # Job execution tests
    └── {EXTENSION_NAME}/        # Extension-specific tests
        ├── job_templates/
        └── jobs/
```

Example:
```
conformance-tests/
└── 2023-09/
    ├── base/
    │   ├── job_templates/
    │   ├── env_templates/
    │   └── jobs/
    ├── TASK_CHUNKING/
    │   ├── job_templates/
    │   └── jobs/
    └── REDACTED_ENV_VARS/
        └── jobs/
```

### Naming Convention

Filenames encode the spec section they test:

```
<spec-section>--<description>[.invalid][.suffix].yaml
```

- `<spec-section>` - Reference to the [Template Schema](../wiki/2023-09-Template-Schemas.md) section (e.g., `1.1`, `3.3.2`, `7.3`)
- `.invalid` - Test should FAIL validation/execution
- `.invalid.test` - Job execution test that should FAIL at runtime (in `jobs/` directory). Use this when the template passes static validation but the error only fires during evaluation.
- `.test` - Job execution test (in `jobs/` directory)

For the `EXPR` extension, tests may reference either the Template Schema or the
[Expression Language](../wiki/2026-02-Expression-Language.md) specification. Tests referencing
the Expression Language use the `expr` prefix:

```
expr<section>--<description>[.invalid][.suffix].yaml
```

- `expr<section>` - Reference to the Expression Language section (e.g., `expr1.1`, `expr2.2.4`)

Examples:
- `1.1--minimal-job-template.yaml` - Section 1.1 (Job Template root)
- `3.3.2--allof.yaml` - Section 3.3.2 (AttributeRequirement)
- `5--cancelation-notify-then-terminate.yaml` - Section 5 (Action)
- `2.1--missing-name.invalid.yaml` - Invalid test for Section 2.1
- `contiguous-even.test.yaml` - TASK_CHUNKING extension execution test (in `TASK_CHUNKING/jobs/`)
- `2.9--bool-param-default-true.yaml` - EXPR: Template Schema §2.9 (JobBoolParameterDefinition)
- `3.6--let-step-level.yaml` - EXPR: Template Schema §3.6 (LetBindings)
- `expr1.1--arithmetic-expr.yaml` - EXPR: Expression Language §1.1 (Extended Format String Grammar)
- `expr2.2.4--upper.test.yaml` - EXPR: Expression Language §2.2.4 (String Functions)

### Extension Tests

Extension tests are organized in their own directories (e.g., `2023-09/TASK_CHUNKING/`). Extensions must be explicitly enabled in templates via the `extensions` field:

```yaml
specificationVersion: jobtemplate-2023-09
extensions:
  - REDACTED_ENV_VARS
name: MyJob
# ...
```

Some tests (like `redaction-without-extension.test.yaml` in `REDACTED_ENV_VARS/jobs/`) intentionally omit the `extensions` field to verify behavior when extension syntax is used without enabling the extension.

### Job Execution Test Format

Job execution tests use a unified single-file format (`.test.yaml`):

```yaml
# The job template to test (required)
template:
  specificationVersion: jobtemplate-2023-09
  name: MyJob
  steps:
    - name: Step1
      script:
        actions:
          onRun:
            command: echo
            args: ["{{Param.Value}}"]

# Optional: parameters to pass when running the job
parameters:
  MyParam: "override-value"

# Optional: environment templates (supports multiple)
environments:
  - specificationVersion: environment-2023-09
    environment:
      name: Env1
      variables:
        FOO: bar

# Optional: path mapping rules
pathMapping:
  - source_path_format: POSIX
    source_path: /mnt/shared
    destination_path: /local/shared

# Optional: restrict which operating systems this test runs on (default: all)
# Valid values: "posix", "windows"
runOn:
  - posix
  - windows

# Optional: expected output assertions
expected:
  output:
    - LINE1
    - LINE2
  forbidden:
    - SHOULD_NOT_APPEAR
  # Platform-specific assertions (optional)
  output_posix:
    - PATH:/unix/style
  output_windows:
    - PATH:D:\windows\style
  forbidden_posix:
    - /wrong/path
  forbidden_windows:
    - D:\wrong\path
  # Optional: assert the run ended in a task failure, and (optionally) that a
  # specific process exit code propagated to the task.
  taskFailure:
    exitCode: 42
```

Platform-specific assertions (`output_posix`, `output_windows`, `forbidden_posix`, `forbidden_windows`) are merged with the base `output` and `forbidden` lists at runtime based on the current platform. Use these when tests involve filesystem paths or other platform-dependent behavior.

The `taskFailure` assertion is for non-`.invalid.` job tests that succeed at the CLI level (the `openjd run` invocation itself does not error) but must still verify that a task *failed* — for example, that a wrapped process' non-zero exit status propagated through a wrap script. When present:

- The run MUST exit non-zero (the session reported a task failure). A run that succeeds fails the assertion.
- If `exitCode` is given, the first non-zero `exited with code: <N>` line in the run output MUST report that code. All failures are terminal for a session, so the first non-zero code is the failing action's; later lines belong to teardown actions (`onWrapEnvExit`, `onExit`) that run after the failure and may legitimately exit `0`. The `exited with code:` substring is emitted by conforming CLIs (`Process exited with code: 42`, `Process pid 1234 exited with code: 42 (unsigned) / ...`), so the assertion is portable across implementations.

Use `taskFailure` instead of the `.invalid.test.yaml` suffix when you also want to assert specific `output`/`forbidden` lines on a failing run, or when you need to pin the propagated exit code.

The `runOn` field restricts a test to run only on the listed operating systems. If omitted, the test runs on all platforms. Use this when a test requires a platform-specific command (e.g., `cmd` or `powershell` on Windows, `bash` on POSIX).

### Expected failures

A test that is correct but that an implementation does not pass yet can say so, in the way
pytest's `xfail` marker does, with a line in the file's leading comment block (the comment and
blank lines before its first line of YAML):

```yaml
# Expression Language §2.1.7 defines no subscript of a path.
# conformance: xfail(rs, reason="openjd-rs accepts the subscript at check time and fails at run time")
specificationVersion: jobtemplate-2023-09
```

- The arguments before `reason` name the implementations the marker applies to: `py` for
  [openjd-cli](https://github.com/OpenJobDescription/openjd-cli) (Python) and `rs` for the
  [openjd-rs](https://github.com/OpenJobDescription/openjd-rs) CLI. `xfail(py, rs, reason="...")`
  names both. An implementation may be named by at most one marker in a file.
- `reason` is required, and should say what the implementation does wrong and, where there is
  one, link the issue or pull request that tracks the fix. `strict` is `true` or `false`.
- The test still runs. For a named implementation a failure of any kind is reported as `XFAIL`
  and does not fail the run. A pass is reported as `XPASS`, counted as failed, and fails the
  run, so the marker is removed in the change that fixes the implementation. Add `strict=false`
  to report an `XPASS` (counted as xpassed) without failing the run, for a test whose outcome on
  that implementation varies.
- A comment line in the leading block whose text starts with `conformance`, followed by a colon
  or later by the word `xfail`, in any case and after any number of `#`, is read as a marker line.
  Text that does not start with `conformance` (`# TODO xfail rs`) is an ordinary comment.
  One that does not start with exactly `# conformance: ` followed by a valid `xfail(...)` (an
  unknown marker name or implementation, no `reason`, an argument given twice) fails the test,
  whichever implementation runs it, so a typo after the leading `conformance` cannot silently
  turn a marker off.
- A marker never changes what the test asserts: a test is correct against the specification or
  it does not belong in the suite. Markers are for implementation defects only.
- JSON test files cannot carry comments, so they cannot carry markers.

The runner applies the markers for the implementation given by `--implementation py|rs`. By
default (`--implementation auto`) it detects which `openjd` is on `PATH` from the CLI's own banner
(the Rust CLI's `--help` heading, openjd-cli's `--version` line), and when it cannot tell it says
so and applies none. `--implementation none` applies none. A malformed marker fails its test in
every mode.

## Writing Your Own Test Runner

To validate your OpenJD library against these tests:

1. Parse the test files and naming conventions
2. For `*.yaml` files (without `.invalid`): verify your library accepts them
3. For `*.invalid.yaml` files: verify your library rejects them
4. For job execution tests (`.test.yaml`): extract template/parameters/environments, run the job, verify outputs match `expected` assertions

### Example Test Runner for openjd CLI

The included `run_openjd_cli_tests.py` demonstrates how to run these tests using the `openjd` CLI. Implementers can adapt this approach or write their own runner targeting their library's API.

```bash
uv run run_openjd_cli_tests.py                          # Run all tests
uv run run_openjd_cli_tests.py 2023-09                  # Run all 2023-09 tests
uv run run_openjd_cli_tests.py 2023-09/base             # Run base spec tests only
uv run run_openjd_cli_tests.py 2023-09/TASK_CHUNKING    # Run TASK_CHUNKING extension tests
uv run run_openjd_cli_tests.py 2023-09/*/jobs           # Run all job execution tests
uv run run_openjd_cli_tests.py '*/*/jobs/*param*'       # Pattern match test names
uv run run_openjd_cli_tests.py --implementation rs      # Apply the xfail markers for openjd-rs
```
