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
- *.template.yaml in jobs/ - should pass `openjd run`
- *.invalid.template.yaml in jobs/ - should FAIL `openjd run`
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

import yaml

CONFORMANCE_DIR = Path(__file__).parent


def load_yaml_or_json(path: Path):
    """Load a YAML or JSON file."""
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


def run_job(template_path: Path) -> tuple[bool, str]:
    base = template_path.name.replace(".invalid.template.yaml", "").replace(".template.yaml", "")
    base_path = template_path.parent / base
    
    cmd = ["openjd", "run", str(template_path)]
    
    # Support both YAML and JSON parameters (prefer YAML)
    params_yaml = base_path.with_suffix(".parameters.yaml")
    params_json = base_path.with_suffix(".parameters.json")
    if params_yaml.exists():
        cmd.extend(["-p", f"file://{params_yaml}"])
    elif params_json.exists():
        cmd.extend(["-p", f"file://{params_json}"])
    
    # Support multiple env files: base.env.yaml, base.env2.yaml, base.env3.yaml, etc.
    env_path = base_path.with_suffix(".env.yaml")
    if env_path.exists():
        cmd.extend(["--env", str(env_path)])
    for i in range(2, 10):
        env_path_n = template_path.parent / f"{base}.env{i}.yaml"
        if env_path_n.exists():
            cmd.extend(["--env", str(env_path_n)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    # Support both YAML and JSON expected files (prefer YAML)
    expected_yaml = base_path.with_suffix(".expected.yaml")
    expected_json = base_path.with_suffix(".expected.json")
    expected_path = expected_yaml if expected_yaml.exists() else expected_json
    
    if expected_path.exists():
        expected = load_yaml_or_json(expected_path)
        
        for line in expected.get("expected_output", []):
            if line not in output:
                return False, f"Missing expected output: {line}"
        
        for line in expected.get("forbidden_output", []):
            if line in output:
                return False, f"Found forbidden output: {line}"
        
        return True, output
    
    return result.returncode == 0, output


def run_template_tests(directory: Path, pattern: str = None) -> tuple[int, int]:
    passed = failed = 0
    
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
            print(f"  ✗ {template.name}")
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:200]}")
    
    return passed, failed


def run_job_tests(directory: Path, pattern: str = None) -> tuple[int, int]:
    passed = failed = 0
    
    for template in sorted(directory.glob("*.template.yaml")):
        name = template.name.replace(".template.yaml", "")
        if pattern and not fnmatch.fnmatch(name, pattern):
            continue
        expect_failure = ".invalid." in template.name
        success, output = run_job(template)
        ok = success != expect_failure
        
        if ok:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}")
            print(f"    Expected {'failure' if expect_failure else 'success'}, got {'success' if success else 'failure'}")
            print(f"    {output[:300]}")
    
    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="Run OpenJD conformance tests")
    parser.add_argument("pattern", nargs="?", default="*/*", help="Glob pattern (e.g. 'job_templates-2023-09/*', 'jobs-2023-09/ext-*')")
    args = parser.parse_args()
    
    total_passed = total_failed = 0
    dir_pattern, _, test_pattern = args.pattern.rpartition("/")
    test_pattern = test_pattern if test_pattern != "*" else None
    
    test_dirs = sorted(d for d in CONFORMANCE_DIR.iterdir() if d.is_dir() and "-" in d.name)
    
    for directory in test_dirs:
        if not fnmatch.fnmatch(directory.name, dir_pattern or "*"):
            continue
        
        print(f"\n{directory.name}:")
        
        if directory.name.startswith("jobs"):
            passed, failed = run_job_tests(directory, test_pattern)
        else:
            passed, failed = run_template_tests(directory, test_pattern)
        
        total_passed += passed
        total_failed += failed
        print(f"  {passed} passed, {failed} failed")
    
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
