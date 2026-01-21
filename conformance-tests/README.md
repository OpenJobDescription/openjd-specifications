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
├── job_templates/           # Job template validation tests
├── env_templates/           # Environment template validation tests
├── jobs/                    # Job execution tests
├── run_openjd_cli_tests.py
└── README.md
```

### Naming Convention

Filenames encode the spec section they test:

```
<spec-section>--<description>[.invalid][.suffix].yaml
```

- `<spec-section>` - Reference to the [Template Schema](../wiki/2023-09-Template-Schemas.md) section (e.g., `1.1`, `3.3.2`, `7.3`)
- `ext-<EXTENSION_NAME>` - For extension tests (e.g., `ext-TASK_CHUNKING`, `ext-REDACTED_ENV_VARS`)
- `.invalid` - Test should FAIL validation
- `.template` - Job execution test (in `jobs/` directory)

Examples:
- `1.1--minimal-job-template.yaml` - Section 1.1 (Job Template root)
- `3.3.2--allof.yaml` - Section 3.3.2 (AttributeRequirement)
- `5--cancelation-notify-then-terminate.yaml` - Section 5 (Action)
- `2.1--missing-name.invalid.yaml` - Invalid test for Section 2.1
- `ext-TASK_CHUNKING--contiguous-even.template.yaml` - TASK_CHUNKING extension execution test

### Auxiliary Files

Job tests support these optional auxiliary files (YAML or JSON):
- `*.parameters.yaml` or `*.parameters.json` - Job parameters
- `*.expected.yaml` or `*.expected.json` - Output assertions
- `*.env.yaml` - Environment template

### Expected Output Format

For job tests, create a `.expected.yaml` file:

```yaml
expected_output:
  - LINE1
  - LINE2
forbidden_output:
  - SHOULD_NOT_APPEAR
```

## Writing Your Own Test Runner

To validate your OpenJD library against these tests:

1. Parse the test files and naming conventions
2. For `*.yaml` files (without `.invalid`): verify your library accepts them
3. For `*.invalid.yaml` files: verify your library rejects them
4. For job execution tests: verify outputs match `.expected.yaml` assertions

### Example Test Runner for openjd CLI

The included `run_openjd_cli_tests.py` demonstrates how to run these tests using the `openjd` CLI. Implementers can adapt this approach or write their own runner targeting their library's API.

```bash
uv run run_openjd_cli_tests.py                        # Run all tests
uv run run_openjd_cli_tests.py 'job_templates/*'      # Run job template tests only
uv run run_openjd_cli_tests.py 'jobs/ext-*'           # Run extension execution tests
uv run run_openjd_cli_tests.py 'job_templates/3.3*'   # Run host requirements tests
```

### Known openjd CLI Deviations

The example test runner uses the `openjd` CLI. The CLI implementation fails several tests either because of missing validations (e.g. duplicate host requirement names) or because of intentional choices (e.g. not allowing absolute paths as defaults for PATH parameters):

- Parameter merge validation (type mismatches, constraint widening/narrowing, default validation)
- Descending range expressions without explicit negative step
- Absolute path defaults in PATH parameters
- Job name length limit (128 chars) and control character validation
- Range item limit (1024) enforcement
- Nested associative parameter length validation
- Duplicate host requirement name detection
