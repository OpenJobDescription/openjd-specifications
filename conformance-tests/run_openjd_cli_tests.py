#!/usr/bin/env python3
# /// script
# dependencies = ["pyyaml"]
# ///
"""
OpenJD Conformance Test Runner - Example for openjd CLI

Run with: uv run run_openjd_cli_tests.py

Test naming conventions:
- *.yaml in job_templates/ - should pass `openjd check`
- *.invalid.yaml in job_templates/ - should FAIL `openjd check`
- *.yaml in env_templates/ - should pass `openjd check`
- *.invalid.yaml in env_templates/ - should FAIL `openjd check`
- *.test.yaml in jobs/ - unified job execution tests
- *.invalid.test.yaml in jobs/ - should FAIL `openjd run`
"""

import argparse
import fnmatch
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PLATFORM = "windows" if sys.platform == "win32" else "posix"

CONFORMANCE_DIR = Path(__file__).parent


def load_yaml_or_json(path: Path):
    with open(path) as f:
        content = f.read()
    if path.suffix == ".json":
        return json.loads(content)
    return yaml.safe_load(content)


def run_check(template_path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["openjd", "check", str(template_path)],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stderr or result.stdout


def run_job(test_path: Path) -> tuple[bool, str]:
    test = load_yaml_or_json(test_path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Write template
        template_path = tmpdir / "template.yaml"
        with open(template_path, "w") as f:
            yaml.dump(test["template"], f)
        
        cmd = ["openjd", "run", str(template_path)]
        
        # Parameters
        if "parameters" in test:
            params_path = tmpdir / "parameters.yaml"
            with open(params_path, "w") as f:
                yaml.dump(test["parameters"], f)
            cmd.extend(["-p", f"file://{params_path}"])
        
        # Environment templates
        for i, env in enumerate(test.get("environments", [])):
            env_path = tmpdir / f"env{i}.yaml"
            with open(env_path, "w") as f:
                yaml.dump(env, f)
            cmd.extend(["--env", str(env_path)])
        
        # Path mapping
        if "pathMapping" in test:
            pm_path = tmpdir / "pathmapping.json"
            with open(pm_path, "w") as f:
                json.dump({"version": "pathmapping-1.0", "path_mapping_rules": test["pathMapping"]}, f)
            cmd.extend(["--path-mapping-rules", f"file://{pm_path}"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        
        # Check expected output
        expected = test.get("expected", {})
        expected_output = expected.get("output", []) + expected.get(f"output_{PLATFORM}", [])
        forbidden = expected.get("forbidden", []) + expected.get(f"forbidden_{PLATFORM}", [])
        for line in expected_output:
            if line not in output:
                return False, f"Missing expected output: {line}\n--- Actual output (last 500 chars) ---\n{output[-500:]}"
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
            print(f"  ✓ {template.name}")
        else:
            failed += 1
            failed_tests.append(f"{directory.name}/{template.name}")
            print(f"  ✗ {template.name}")
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:200]}")
    
    return passed, failed, failed_tests


def run_job_tests(directory: Path, pattern: str = None) -> tuple[int, int, list[str]]:
    passed = failed = 0
    failed_tests = []
    
    for test_path in sorted(directory.glob("*.test.yaml")):
        name = test_path.name.replace(".invalid.test.yaml", "").replace(".test.yaml", "")
        if pattern and not fnmatch.fnmatch(name, pattern):
            continue
        expect_failure = ".invalid." in test_path.name
        success, output = run_job(test_path)
        ok = success != expect_failure
        
        if ok:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            failed_tests.append(f"{directory.name}/{test_path.name}")
            print(f"  ✗ {name}")
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:300]}")
    
    return passed, failed, failed_tests


def main():
    parser = argparse.ArgumentParser(description="Run OpenJD conformance tests")
    parser.add_argument("pattern", nargs="?", default="*/*", help="Glob pattern (e.g. 'job_templates-2023-09/*', 'jobs-2023-09/ext-*')")
    args = parser.parse_args()
    
    total_passed = total_failed = 0
    all_failed_tests = []
    dir_pattern, _, test_pattern = args.pattern.rpartition("/")
    test_pattern = test_pattern if test_pattern != "*" else None
    
    test_dirs = sorted(d for d in CONFORMANCE_DIR.iterdir() if d.is_dir() and "-" in d.name)
    
    for directory in test_dirs:
        if not fnmatch.fnmatch(directory.name, dir_pattern or "*"):
            continue
        
        print(f"\n{directory.name}:")
        
        if directory.name.startswith("jobs"):
            passed, failed, failed_tests = run_job_tests(directory, test_pattern)
        else:
            passed, failed, failed_tests = run_template_tests(directory, test_pattern)
        
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
