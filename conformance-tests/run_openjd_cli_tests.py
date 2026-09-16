#!/usr/bin/env python3
# /// script
# dependencies = ["pyyaml"]
# ///
"""
OpenJD Conformance Test Runner - Example for openjd CLI

Run with: uv run run_openjd_cli_tests.py

Examples:
  uv run run_openjd_cli_tests.py                          # run all tests
  uv run run_openjd_cli_tests.py 2023-09                  # run all 2023-09 tests
  uv run run_openjd_cli_tests.py 2023-09/base             # run base spec tests only
  uv run run_openjd_cli_tests.py 2023-09/TASK_CHUNKING    # run TASK_CHUNKING extension tests
  uv run run_openjd_cli_tests.py 2023-09/*/jobs           # run all job tests
  uv run run_openjd_cli_tests.py '*/*/jobs/*param*'       # pattern match test names
  uv run run_openjd_cli_tests.py 2023-09/base/jobs/1.1--basic-job-creation.test.yaml  # run single test
"""

import argparse
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Fixture task commands are python programs that print UTF-8 sentinels. On
# Windows, a child python writing to a pipe uses the locale encoding
# (cp1252) unless told otherwise, which mangles non-ASCII output before it
# reaches the CLI's session log. Propagate UTF-8 mode to every child.
os.environ.setdefault("PYTHONUTF8", "1")

OPERATING_SYSTEM = "windows" if sys.platform == "win32" else "posix"

CONFORMANCE_DIR = Path(__file__).parent


def load_yaml_or_json(path: Path):
    # Explicit UTF-8: fixture files contain non-ASCII (unicode string-function
    # tests) and Windows' default locale encoding (cp1252) cannot decode them.
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if path.suffix == ".json":
        return json.loads(content)
    return yaml.safe_load(content)


def run_check(template_path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["openjd", "check", str(template_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode == 0, result.stderr or result.stdout


# Matches the per-process exit-code line emitted by conforming CLIs. Both the
# Python (`Process pid 1234 exited with code: 42 (unsigned) / 0x2a (hex)`) and
# Rust (`Process exited with code: 42`) CLIs share the `exited with code: <N>`
# substring, so a single regex extracts process exit codes from either.
_EXIT_CODE_RE = re.compile(r"exited with code:\s*(-?\d+)")


def extract_failure_exit_code(output: str) -> int | None:
    """Return the exit code of the failing action in the run output, or None.

    All failures are terminal for a session, so the first non-zero exit code
    is the failing action's code. Later `exited with code:` lines belong to
    teardown actions (onWrapEnvExit, onExit) that run after the failure and
    may exit 0, so matching the last line would mis-attribute the failure.
    """
    for match in _EXIT_CODE_RE.findall(output):
        code = int(match)
        if code != 0:
            return code
    return None


def should_skip_test(test: dict) -> bool:
    """Check if a job test should be skipped on the current platform."""
    run_on = test.get("runOn")
    if run_on is None:
        return False
    return OPERATING_SYSTEM not in run_on


def run_job(test_path: Path) -> tuple[bool, str] | None:
    test = load_yaml_or_json(test_path)

    if should_skip_test(test):
        return None

    expect_failure = ".invalid." in test_path.name

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write template
        template_path = tmpdir / "template.yaml"
        with open(template_path, "w", encoding="utf-8") as f:
            yaml.dump(test["template"], f)

        cmd = ["openjd", "run", str(template_path)]

        # Parameters
        if "parameters" in test:
            params_path = tmpdir / "parameters.yaml"
            with open(params_path, "w", encoding="utf-8") as f:
                yaml.dump(test["parameters"], f)
            cmd.extend(["-p", f"file://{params_path}"])

        # Environment templates
        for i, env in enumerate(test.get("environments", [])):
            env_path = tmpdir / f"env{i}.yaml"
            with open(env_path, "w", encoding="utf-8") as f:
                yaml.dump(env, f)
            cmd.extend(["--env", str(env_path)])

        # Path mapping
        if "pathMapping" in test:
            pm_path = tmpdir / "pathmapping.json"
            with open(pm_path, "w", encoding="utf-8") as f:
                json.dump({"version": "pathmapping-1.0", "path_mapping_rules": test["pathMapping"]}, f)
            cmd.extend(["--path-mapping-rules", f"file://{pm_path}"])

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = result.stdout + result.stderr

        # For invalid tests, any failure (non-zero exit code) is acceptable
        if expect_failure:
            # Return False (job failed) which is what we want for invalid tests
            return result.returncode == 0, output

        # Check expected output
        expected = test.get("expected", {})

        # taskFailure: assert the run surfaced a task failure, and (optionally)
        # that a specific process exit code propagated. This is how exit-status
        # propagation is verified for a non-.invalid. test that must still make
        # assertions about its output.
        task_failure = expected.get("taskFailure")
        if task_failure is not None:
            if result.returncode == 0:
                return False, (
                    "Expected task failure (non-zero run exit) but the run "
                    f"succeeded (exit 0).\n--- Actual output ---\n{output}"
                )
            expected_code = task_failure.get("exitCode")
            if expected_code is not None:
                actual_code = extract_failure_exit_code(output)
                if actual_code is None:
                    return False, (
                        "Expected task exitCode "
                        f"{expected_code} but no non-zero 'exited with code' "
                        f"line was found in the output.\n"
                        f"--- Actual output ---\n{output}"
                    )
                if actual_code != expected_code:
                    return False, (
                        f"Expected task exitCode {expected_code} but the "
                        f"failing action exited with {actual_code}.\n"
                        f"--- Actual output ---\n{output}"
                    )

        expected_output = expected.get("output", []) + expected.get(f"output_{OPERATING_SYSTEM}", [])
        forbidden = expected.get("forbidden", []) + expected.get(f"forbidden_{OPERATING_SYSTEM}", [])
        for line in expected_output:
            # Support anyOf: {"anyOf": ["value1", "value2"]} — at least one must appear
            if isinstance(line, dict) and "anyOf" in line:
                if not any(alt in output for alt in line["anyOf"]):
                    return False, f"Missing expected output (none of anyOf matched): {line['anyOf']}\n--- Actual output ---\n{output}"
            elif line not in output:
                return False, f"Missing expected output: {line}\n--- Actual output ---\n{output}"
        for line in forbidden:
            if line in output:
                return False, f"Found forbidden output: {line}"

        return True, output


def run_template_tests(directory: Path, pattern: str = None) -> tuple[int, int, list[str]]:
    passed = failed = 0
    failed_tests = []

    templates = sorted(list(directory.glob("*.yaml")) + list(directory.glob("*.json")))
    for template in templates:
        if pattern and not fnmatch.fnmatch(template.name, pattern):
            continue
        expect_failure = ".invalid." in template.name
        success, output = run_check(template)
        ok = success != expect_failure

        if ok:
            passed += 1
            print(f"  ✓ {template.name}", flush=True)
        else:
            failed += 1
            failed_tests.append(str(template.relative_to(CONFORMANCE_DIR)))
            print(f"  ✗ {template.name}", flush=True)
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:200]}")

    return passed, failed, failed_tests


def run_job_tests(directory: Path, pattern: str = None) -> tuple[int, int, list[str]]:
    passed = failed = 0
    failed_tests = []

    for test_path in sorted(directory.glob("*.test.yaml")):
        name = test_path.name.replace(".invalid.test.yaml", "").replace(".test.yaml", "")
        if pattern and not fnmatch.fnmatch(test_path.name, pattern):
            continue
        result = run_job(test_path)
        if result is None:
            print(f"  ⊘ {name} (skipped, not for {OPERATING_SYSTEM})", flush=True)
            continue
        expect_failure = ".invalid." in test_path.name
        success, output = result
        ok = success != expect_failure

        if ok:
            passed += 1
            print(f"  ✓ {name}", flush=True)
        else:
            failed += 1
            failed_tests.append(str(test_path.relative_to(CONFORMANCE_DIR)))
            print(f"  ✗ {name}", flush=True)
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:300]}")

    return passed, failed, failed_tests


def run_single_file(file_path: Path) -> tuple[int, int, list[str]]:
    """Run a single test file directly."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 0, 1, [str(file_path)]

    name = file_path.name
    if ".test.yaml" in name:
        result = run_job(file_path)
        if result is None:
            print(f"  ⊘ {name} (skipped, not for {OPERATING_SYSTEM})")
            return 0, 0, []
        expect_failure = ".invalid." in name
        success, output = result
        display_name = name.replace(".invalid.test.yaml", "").replace(".test.yaml", "")
    else:
        expect_failure = ".invalid." in name
        success, output = run_check(file_path)
        display_name = name

    ok = success != expect_failure
    if ok:
        print(f"  ✓ {display_name}")
    else:
        print(f"  ✗ {display_name}")
        print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")

    print(f"\n--- Output ---\n{output}")
    return (1, 0, []) if ok else (0, 1, [str(file_path)])


def discover_test_dirs(base: Path) -> list[tuple[Path, str]]:
    """Discover all test directories: (path, type) where type is job_templates|env_templates|jobs"""
    results = []
    for spec_version in sorted(base.iterdir()):
        if not spec_version.is_dir() or not spec_version.name[0].isdigit():
            continue
        for component in sorted(spec_version.iterdir()):
            if not component.is_dir():
                continue
            for test_type in ["job_templates", "env_templates", "jobs"]:
                test_dir = component / test_type
                if test_dir.is_dir():
                    results.append((test_dir, test_type))
    return results


def main():
    parser = argparse.ArgumentParser(description="Run OpenJD conformance tests")
    parser.add_argument("pattern", nargs="?", default="*/*/*",
                        help="Pattern: {version}/{component}/{type}/{test} or file path")
    args = parser.parse_args()

    # Check if it's a direct file path
    potential_path = CONFORMANCE_DIR / args.pattern
    if potential_path.is_file():
        passed, failed, failed_tests = run_single_file(potential_path)
        print(f"\nTotal: {passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)

    # Parse pattern: version/component/type/test_pattern
    parts = args.pattern.strip("/").split("/")
    version_pat = parts[0] if len(parts) > 0 else "*"
    component_pat = parts[1] if len(parts) > 1 else "*"
    type_pat = parts[2] if len(parts) > 2 else "*"
    test_pat = parts[3] if len(parts) > 3 else None

    total_passed = total_failed = 0
    all_failed_tests = []

    for test_dir, test_type in discover_test_dirs(CONFORMANCE_DIR):
        rel_path = test_dir.relative_to(CONFORMANCE_DIR)
        version, component, _ = rel_path.parts

        if not fnmatch.fnmatch(version, version_pat):
            continue
        if not fnmatch.fnmatch(component, component_pat):
            continue
        if not fnmatch.fnmatch(test_type, type_pat):
            continue

        print(f"\n{rel_path}:", flush=True)

        if test_type == "jobs":
            passed, failed, failed_tests = run_job_tests(test_dir, test_pat)
        else:
            passed, failed, failed_tests = run_template_tests(test_dir, test_pat)

        total_passed += passed
        total_failed += failed
        all_failed_tests.extend(failed_tests)
        print(f"  {passed} passed, {failed} failed")

    print(f"\nTotal: {total_passed} passed, {total_failed} failed")

    if all_failed_tests:
        print(f"\nFailed tests ({len(all_failed_tests)}):")
        for name in all_failed_tests:
            print(f"  - {name}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
