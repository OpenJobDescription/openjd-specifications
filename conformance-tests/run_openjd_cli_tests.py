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
  uv run run_openjd_cli_tests.py --implementation rs      # apply the xfail markers for openjd-rs

A test file may mark itself as an expected failure for one implementation with a
comment in its leading comment block (see "Expected failures" in README.md):

  # conformance: xfail(rs, reason="openjd-rs accepts this at check time")
"""

import argparse
import ast
import fnmatch
import io
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

OPERATING_SYSTEM = "windows" if sys.platform == "win32" else "posix"

CONFORMANCE_DIR = Path(__file__).parent


# Test files are UTF-8, and every file the runner reads or writes names the
# encoding, because the default is the locale encoding (cp1252 on Windows).
def load_yaml_or_json(path: Path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if path.suffix == ".json":
        return json.loads(content)
    return yaml.safe_load(content)


# ---------------------------------------------------------------------------
# Expected-failure markers
#
# A test file's leading comment block (the comment and blank lines before its
# first line of YAML) may hold lines of the form
#
#   # conformance: xfail(<impl>[, <impl>...], reason="<why>"[, strict=false])
#
# where <impl> is one of IMPLEMENTATIONS. The test still runs. For a listed
# implementation a failure is reported as XFAIL and does not fail the run, and
# a pass is reported as XPASS, which fails the run unless strict=false, so a
# marker is removed once the implementation is fixed. A marker that cannot be
# read fails the test rather than being ignored.
# ---------------------------------------------------------------------------

# The implementations a marker may name: "py" is openjd-cli (Python), "rs" is
# the openjd-rs CLI.
IMPLEMENTATIONS = ("py", "rs")

_MARKER_RE = re.compile(r"^#\s*conformance:\s*(?P<call>.*?)\s*$")


@dataclass(frozen=True)
class XfailMarker:
    implementations: tuple[str, ...]
    reason: str
    strict: bool = True


class MarkerError(ValueError):
    """A `# conformance:` line that is not a well-formed marker."""


def _parse_marker(call: str) -> XfailMarker:
    try:
        node = ast.parse(call, mode="eval").body
    except SyntaxError as e:
        raise MarkerError(f"not a marker call: {call!r} ({e.msg})") from None
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise MarkerError(f"not a marker call: {call!r}")
    if node.func.id != "xfail":
        raise MarkerError(f"unknown marker {node.func.id!r} (expected 'xfail')")
    impls = []
    for arg in node.args:
        if not isinstance(arg, ast.Name) or arg.id not in IMPLEMENTATIONS:
            raise MarkerError(
                f"xfail takes implementations from {IMPLEMENTATIONS}, got {ast.unparse(arg)!r}"
            )
        impls.append(arg.id)
    if not impls:
        raise MarkerError("xfail names no implementation")
    reason = None
    strict = True
    for kw in node.keywords:
        value = kw.value
        if kw.arg == "reason" and isinstance(value, ast.Constant) and isinstance(value.value, str):
            reason = value.value
        elif kw.arg == "strict" and isinstance(value, ast.Name) and value.id in ("true", "false"):
            strict = value.id == "true"
        else:
            raise MarkerError(
                f"unknown or ill-typed xfail argument {kw.arg}={ast.unparse(value)} "
                '(expected reason="..." or strict=true|false)'
            )
    if not reason or not reason.strip():
        raise MarkerError('xfail needs a non-empty reason="..."')
    return XfailMarker(tuple(impls), reason, strict)


def read_markers(path: Path) -> list[XfailMarker]:
    """The xfail markers in `path`'s leading comment block. JSON test files
    have no comments, so they carry no markers."""
    if path.suffix == ".json":
        return []
    markers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("#"):
                break
            m = _MARKER_RE.match(stripped)
            if m:
                markers.append(_parse_marker(m.group("call")))
    return markers


def marker_for(markers: list[XfailMarker], implementation: str | None) -> XfailMarker | None:
    """The marker that applies to `implementation`, if any."""
    if implementation is None:
        return None
    for marker in markers:
        if implementation in marker.implementations:
            return marker
    return None


def detect_implementation() -> str | None:
    """Which CLI `openjd` on PATH is: "rs" when its help names the Rust CLI,
    "py" when `--version` names openjd-cli, else None."""
    try:
        help_text = subprocess.run(
            ["openjd", "--help"], capture_output=True, encoding="utf-8", errors="replace"
        )
        if "Open Job Description CLI (Rust)" in help_text.stdout + help_text.stderr:
            return "rs"
        version = subprocess.run(
            ["openjd", "--version"], capture_output=True, encoding="utf-8", errors="replace"
        )
        if version.returncode == 0 and "Open Job Description CLI" in version.stdout:
            return "py"
    except OSError:
        pass
    return None


# Set by main(): the implementation whose markers apply, or None.
IMPLEMENTATION: str | None = None


@dataclass
class Outcome:
    status: str  # "PASS", "FAIL", "XFAIL", "XPASS" or "SKIP"
    output: str = ""
    detail: str = ""  # why it failed, or the xfail reason
    strict: bool = True  # for XPASS: whether the marker makes a pass fail the run

    @property
    def counts_as_failure(self) -> bool:
        return self.status == "FAIL" or (self.status == "XPASS" and self.strict)


def evaluate(path: Path) -> Outcome:
    """Run one test file and classify the result, applying its markers."""
    try:
        marker = marker_for(read_markers(path), IMPLEMENTATION)
    except MarkerError as e:
        return Outcome("FAIL", "", f"Bad conformance marker: {e}")
    expect_failure = ".invalid." in path.name
    if ".test." in path.name:
        result = run_job(path)
        if result is None:
            return Outcome("SKIP")
        success, output = result
    else:
        success, output = run_check(path)
    ok = success != expect_failure
    detail = "" if ok else f"Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}"
    if marker is None:
        return Outcome("PASS" if ok else "FAIL", output, detail)
    if ok:
        return Outcome("XPASS", output, marker.reason, marker.strict)
    return Outcome("XFAIL", output, marker.reason)


def run_check(template_path: Path) -> tuple[bool, str]:
    # openjd output is decoded as UTF-8. errors="backslashreplace" shows a byte
    # that isn't UTF-8 as \xNN instead of aborting the whole run.
    result = subprocess.run(
        ["openjd", "check", str(template_path)],
        capture_output=True, encoding="utf-8", errors="backslashreplace",
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

        # Write template. yaml.dump writes non-ASCII characters as YAML escapes,
        # so every file written here is ASCII and reads the same in any encoding.
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

        result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="backslashreplace")
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


def display_name(path: Path) -> str:
    name = path.name
    if ".test.yaml" in name:
        return name.replace(".invalid.test.yaml", "").replace(".test.yaml", "")
    return name


def report(path: Path, outcome: Outcome, output_chars: int) -> None:
    """Print one test's result line, and detail for anything but a plain pass."""
    name = display_name(path)
    if outcome.status == "PASS":
        print(f"  ✓ {name}", flush=True)
    elif outcome.status == "SKIP":
        print(f"  ⊘ {name} (skipped, not for {OPERATING_SYSTEM})", flush=True)
    elif outcome.status == "XFAIL":
        print(f"  x {name} (xfail: {outcome.detail})", flush=True)
    elif outcome.status == "XPASS":
        if outcome.strict:
            print(f"  ✗ {name} (XPASS: marked xfail for {IMPLEMENTATION} but passed; remove the marker)", flush=True)
        else:
            print(f"  ! {name} (XPASS, non-strict marker: consider removing it)", flush=True)
    else:
        print(f"  ✗ {name}", flush=True)
        if outcome.detail:
            print(f"    {outcome.detail}")
        if output_chars and outcome.output:
            print(f"    {outcome.output[:output_chars]}")


@dataclass
class Tally:
    passed: int = 0
    failed: int = 0
    xfailed: int = 0
    xpassed: int = 0
    failed_tests: list = None

    def __post_init__(self):
        if self.failed_tests is None:
            self.failed_tests = []

    def add(self, path: Path, outcome: Outcome) -> None:
        if outcome.status == "PASS":
            self.passed += 1
        elif outcome.status == "XFAIL":
            self.xfailed += 1
        elif outcome.status == "XPASS":
            self.xpassed += 1
        elif outcome.status == "FAIL":
            self.failed += 1
        if outcome.counts_as_failure:
            try:
                rel = path.relative_to(CONFORMANCE_DIR)
            except ValueError:
                rel = path
            self.failed_tests.append(f"{rel}" + (" (XPASS)" if outcome.status == "XPASS" else ""))

    def extend(self, other: "Tally") -> None:
        self.passed += other.passed
        self.failed += other.failed
        self.xfailed += other.xfailed
        self.xpassed += other.xpassed
        self.failed_tests.extend(other.failed_tests)

    def summary(self) -> str:
        text = f"{self.passed} passed, {self.failed} failed"
        if self.xfailed or self.xpassed:
            text += f", {self.xfailed} xfailed, {self.xpassed} xpassed"
        return text

    @property
    def ok(self) -> bool:
        return not self.failed_tests


def run_template_tests(directory: Path, pattern: str = None) -> Tally:
    tally = Tally()
    templates = sorted(list(directory.glob("*.yaml")) + list(directory.glob("*.json")))
    for template in templates:
        if pattern and not fnmatch.fnmatch(template.name, pattern):
            continue
        outcome = evaluate(template)
        report(template, outcome, 200)
        tally.add(template, outcome)
    return tally


def run_job_tests(directory: Path, pattern: str = None) -> Tally:
    tally = Tally()
    for test_path in sorted(directory.glob("*.test.yaml")):
        if pattern and not fnmatch.fnmatch(test_path.name, pattern):
            continue
        outcome = evaluate(test_path)
        report(test_path, outcome, 300)
        tally.add(test_path, outcome)
    return tally


def run_single_file(file_path: Path) -> Tally:
    """Run a single test file directly."""
    tally = Tally()
    if not file_path.exists():
        print(f"File not found: {file_path}")
        tally.failed += 1
        tally.failed_tests.append(str(file_path))
        return tally
    outcome = evaluate(file_path)
    report(file_path, outcome, 0)
    tally.add(file_path, outcome)
    if outcome.status != "SKIP":
        print(f"\n--- Output ---\n{outcome.output}")
    return tally


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
    global IMPLEMENTATION
    parser = argparse.ArgumentParser(description="Run OpenJD conformance tests")
    parser.add_argument("pattern", nargs="?", default="*/*/*",
                        help="Pattern: {version}/{component}/{type}/{test} or file path")
    parser.add_argument("--implementation", choices=[*IMPLEMENTATIONS, "auto", "none"], default="auto",
                        help="Which implementation's xfail markers apply: py (openjd-cli), rs (openjd-rs), "
                             "auto (detect from `openjd` on PATH, the default) or none (ignore markers)")
    args = parser.parse_args()

    if args.implementation == "auto":
        IMPLEMENTATION = detect_implementation()
        if IMPLEMENTATION is None:
            print("Note: could not tell which openjd CLI is on PATH; xfail markers are not applied. "
                  "Pass --implementation py|rs to apply them.")
    elif args.implementation != "none":
        IMPLEMENTATION = args.implementation
    if IMPLEMENTATION:
        print(f"Applying xfail markers for implementation: {IMPLEMENTATION}")

    # Check if it's a direct file path
    potential_path = CONFORMANCE_DIR / args.pattern
    if potential_path.is_file():
        tally = run_single_file(potential_path)
        print(f"\nTotal: {tally.summary()}")
        sys.exit(0 if tally.ok else 1)

    # Parse pattern: version/component/type/test_pattern
    parts = args.pattern.strip("/").split("/")
    version_pat = parts[0] if len(parts) > 0 else "*"
    component_pat = parts[1] if len(parts) > 1 else "*"
    type_pat = parts[2] if len(parts) > 2 else "*"
    test_pat = parts[3] if len(parts) > 3 else None

    total = Tally()

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
            tally = run_job_tests(test_dir, test_pat)
        else:
            tally = run_template_tests(test_dir, test_pat)

        total.extend(tally)
        print(f"  {tally.summary()}")

    print(f"\nTotal: {total.summary()}")

    if total.failed_tests:
        print(f"\nFailed tests ({len(total.failed_tests)}):")
        for name in total.failed_tests:
            print(f"  - {name}")

    sys.exit(0 if total.ok else 1)


if __name__ == "__main__":
    main()
