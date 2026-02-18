#!/usr/bin/env python3
"""Validates that all conformance test filenames follow the naming convention documented in README.md.

The naming scheme is:
    [<doc>-][<section>]--<description>[.invalid][.test].<ext>

- Base spec tests (under base/): no doc prefix, section required (leading number).
- Extension tests: doc prefix required (chunk, redact, etc.), section optional.
- If an extension test is testing a base spec rule, it uses base spec naming (leading number, no doc prefix).
"""

import re
import sys
from pathlib import Path

CONFORMANCE_DIR = Path(__file__).parent

# Map extension directory names to their doc prefix
EXTENSION_DOC_PREFIX = {
    "TASK_CHUNKING": "chunk",
    "REDACTED_ENV_VARS": "redact",
}

# Base spec pattern: starts with a digit (section number)
#   <section>--<description>[.invalid][.test].<ext>
BASE_RE = re.compile(
    r"^(?P<section>\d+(?:\.\d+)*)--(?P<desc>[a-z0-9]+(?:-[a-z0-9]+)*)(?P<invalid>\.invalid)?(?P<test>\.test)?\.(?P<ext>yaml|json)$"
)

# Extension pattern: starts with a doc prefix
#   <doc>[-<section>]--<description>[.invalid][.test].<ext>
def extension_re(prefix: str) -> re.Pattern:
    return re.compile(
        rf"^{re.escape(prefix)}(?:-(?P<section>\d+(?:\.\d+)*))?--(?P<desc>[a-z0-9]+(?:-[a-z0-9]+)*)(?P<invalid>\.invalid)?(?P<test>\.test)?\.(?P<ext>yaml|json)$"
    )


def validate_filename(name: str, component: str, test_type: str) -> list[str]:
    """Returns a list of error strings (empty if valid)."""
    errors = []

    if component == "base":
        m = BASE_RE.match(name)
        if not m:
            errors.append(f"does not match base naming pattern: [<section>]--<description>[.invalid][.test].<ext>")
            return errors
    else:
        prefix = EXTENSION_DOC_PREFIX.get(component)
        if prefix is None:
            errors.append(f"unknown extension directory '{component}', add it to EXTENSION_DOC_PREFIX")
            return errors
        ext_pattern = extension_re(prefix)
        m = BASE_RE.match(name) or ext_pattern.match(name)
        if not m:
            errors.append(
                f"does not match naming pattern: "
                f"<section>--<desc>... (base spec rule) or "
                f"{prefix}[-<section>]--<desc>... (extension)"
            )
            return errors

    if test_type == "jobs" and not m.group("test"):
        errors.append("files in jobs/ must have .test suffix")
    if test_type in ("job_templates", "env_templates") and m.group("test"):
        errors.append(f"files in {test_type}/ must not have .test suffix")

    return errors


def main() -> int:
    failures = []

    for spec_dir in sorted(CONFORMANCE_DIR.iterdir()):
        if not spec_dir.is_dir() or not spec_dir.name[0].isdigit():
            continue
        for component_dir in sorted(spec_dir.iterdir()):
            if not component_dir.is_dir():
                continue
            component = component_dir.name
            for test_type in ("job_templates", "env_templates", "jobs"):
                type_dir = component_dir / test_type
                if not type_dir.is_dir():
                    continue
                for f in sorted(type_dir.iterdir()):
                    if not f.is_file():
                        continue
                    errs = validate_filename(f.name, component, test_type)
                    for e in errs:
                        failures.append(f"{f.relative_to(CONFORMANCE_DIR)}: {e}")

    if failures:
        print(f"FAIL: {len(failures)} file(s) with invalid names:\n")
        for msg in failures:
            print(f"  {msg}")
        return 1

    print("OK: all conformance test filenames are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
