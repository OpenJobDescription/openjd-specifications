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

### File Naming Rules

Test filenames follow strict conventions that encode metadata used by test runners.

```
[<doc>-][<section>]--<description>[.invalid][.test].<ext>
```

| Component | Required | Description |
|---|---|---|
| `<doc>` | No | Document prefix, required for extension specs. Omitted for the base [Template Schema](../wiki/2023-09-Template-Schemas.md) (a leading number implies it). |
| `<section>` | No | Section reference within the document (e.g., `1.1`, `3.4.1.5`). Omitted when the test isn't tied to a specific numbered section. |
| `--` | Yes | Double-hyphen separator before the description. |
| `<description>` | Yes | Lowercase kebab-case description of what is being tested. |
| `.invalid` | No | Present when the test should FAIL validation or execution. |
| `.test` | No | Present for job execution tests (files in `jobs/` directories). |
| `<ext>` | Yes | `.yaml` or `.json`. |

When both `.invalid` and `.test` are present, `.invalid` comes first: `1.1--desc.invalid.test.yaml`

Each extension spec should use a short, consistent prefix (e.g., `chunk` for TASK_CHUNKING, `redact` for REDACTED_ENV_VARS). The base [Template Schema](../wiki/2023-09-Template-Schemas.md) needs no prefix — a leading number implies it.

Examples:
- `1.1--minimal-job-template.yaml` — base spec section 1.1, valid template
- `7.3--nested-braces.invalid.test.yaml` — base spec section 7.3, job execution test that should fail
- `chunk-3.4.1.5--noncontiguous.yaml` — TASK_CHUNKING section 3.4.1.5, valid template
- `redact--mixed-env-vars.test.yaml` — REDACTED_ENV_VARS, no specific section, job execution test

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
```

Platform-specific assertions (`output_posix`, `output_windows`, `forbidden_posix`, `forbidden_windows`) are merged with the base `output` and `forbidden` lists at runtime based on the current platform. Use these when tests involve filesystem paths or other platform-dependent behavior.

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
```
