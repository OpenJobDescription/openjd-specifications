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
├── job_templates-2023-09/   # Job template validation tests
├── env_templates-2023-09/   # Environment template validation tests
├── jobs-2023-09/            # Job execution tests (unified format)
├── run_openjd_cli_tests.py
└── README.md
```

Directory names include the specification revision (e.g., `-2023-09`) to support multiple spec versions.

### Naming Convention

Filenames encode the spec section they test:

```
<spec-section>--<description>[.invalid][.suffix].yaml
```

- `<spec-section>` - Reference to the [Template Schema](../wiki/2023-09-Template-Schemas.md) section (e.g., `1.1`, `3.3.2`, `7.3`)
- `ext-<EXTENSION_NAME>` - For extension tests (e.g., `ext-TASK_CHUNKING`, `ext-REDACTED_ENV_VARS`)
- `.invalid` - Test should FAIL validation/execution
- `.test` - Job execution test (in `jobs/` directory)

Examples:
- `1.1--minimal-job-template.yaml` - Section 1.1 (Job Template root)
- `3.3.2--allof.yaml` - Section 3.3.2 (AttributeRequirement)
- `5--cancelation-notify-then-terminate.yaml` - Section 5 (Action)
- `2.1--missing-name.invalid.yaml` - Invalid test for Section 2.1
- `ext-TASK_CHUNKING--contiguous-even.test.yaml` - TASK_CHUNKING extension execution test

### Extension Tests

Extensions must be explicitly enabled in templates via the `extensions` field:

```yaml
specificationVersion: jobtemplate-2023-09
extensions:
  - REDACTED_ENV_VARS
name: MyJob
# ...
```

Tests prefixed with `ext-<NAME>` verify extension behavior. Some tests (like `ext-REDACTED_ENV_VARS--redaction-without-extension`) intentionally omit the `extensions` field to verify behavior when extension syntax is used without enabling the extension.

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
```

## Writing Your Own Test Runner

To validate your OpenJD library against these tests:

1. Parse the test files and naming conventions
2. For `*.yaml` files (without `.invalid`): verify your library accepts them
3. For `*.invalid.yaml` files: verify your library rejects them
4. For job execution tests (`.test.yaml`): extract template/parameters/environments, run the job, verify outputs match `expected` assertions

### Example Test Runner for openjd CLI

The included `run_openjd_cli_tests.py` demonstrates how to run these tests using the `openjd` CLI. Implementers can adapt this approach or write their own runner targeting their library's API.

```bash
uv run run_openjd_cli_tests.py                              # Run all tests
uv run run_openjd_cli_tests.py 'job_templates-2023-09/*'    # Run job template tests only
uv run run_openjd_cli_tests.py 'jobs-2023-09/ext-*'         # Run extension execution tests
uv run run_openjd_cli_tests.py 'job_templates-2023-09/3.3*' # Run host requirements tests
```

### Known openjd CLI Deviations

The example test runner uses the `openjd` CLI. The CLI implementation fails several tests due to missing validations or intentional implementation choices:

**Template Validation** - CLI doesn't enforce:
- Job name max length (128 chars) or control character restrictions
- STRING `minLength=0` (CLI requires > 0)
- Empty `args` array (CLI requires at least 1 arg)
- `decimals` property restricted to SPINBOX controls
- Duplicate host requirement names
- Max 1024 range items, empty string/path values in ranges
- Embedded filename path separator validation
- TASK_CHUNKING extension declaration requirement

**Job Execution** - Many tests expect errors at runtime, but CLI catches them earlier:
- Parameter validation errors (type mismatches, constraint violations) fail at generation time instead of runtime
- Format string scope errors fail at validation time instead of runtime
- Descending ranges like `5-1` require explicit negative step
- Path mapping not applied to `Param.*` references
- Some extension behaviors differ (REDACTED_ENV_VARS, TASK_CHUNKING noncontiguous)
