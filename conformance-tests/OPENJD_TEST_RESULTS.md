# OpenJD Conformance Test Results

Test run: 2026-02-10 (openjd-cli 0.7.5)

**Total: 647 passed, 18 failed**

## Failure Analysis

### Template Validation Failures (18)

| Test | Fix | Spec Reference | Analysis |
|------|-----|----------------|----------|
| `2--too-many-parameters.invalid.yaml` | openjd | §1.1: "Maximum number of elements: 50 or 200 with FEATURE_BUNDLE_1 extension" | CLI applies relaxed limit (200) without requiring extension declaration. **Fix openjd** to enforce 50 limit unless FEATURE_BUNDLE_1 is declared. |
| `2.1--minlength-zero.yaml` | openjd | §2.1: "minLength: \<integer\>" | CLI rejects `minLength: 0` but spec allows any integer. A minLength of 0 means "no minimum" which is valid. **Fix openjd** to accept 0. |
| `2.4--decimals-on-dropdown.invalid.yaml` | both | §2.4: decimals under SPIN_BOX control | Spec defines `decimals` under FLOAT's userInterface but doesn't explicitly restrict it to SPIN_BOX. The description says "places editable" which implies SPIN_BOX only. **Fix spec** to add explicit constraint "Can only be provided when *control* is SPIN_BOX", **fix openjd** to validate. |
| `2.4--decimals-on-hidden.invalid.yaml` | both | §2.4: decimals under SPIN_BOX control | Same as above - `decimals` makes no sense for HIDDEN controls. **Fix spec** and **fix openjd**. |
| `3.3--duplicate-amount-names.invalid.yaml` | both | §3.3: amounts list | Spec doesn't explicitly forbid duplicates, but duplicate amount names are nonsensical (which value wins?). **Fix spec** to add uniqueness constraint, **fix openjd** to validate. |
| `3.3--duplicate-attribute-names.invalid.yaml` | both | §3.3: attributes list | Same reasoning - duplicate attribute names are ambiguous. **Fix spec** and **fix openjd**. |
| `3.3.2--value-case-insensitive.yaml` | openjd | §3.3.2: attribute values | Spec says attribute values follow capability naming which is case-insensitive. CLI treats them case-sensitively. **Fix openjd** to normalize case. |
| `3.4--too-many-range-items.invalid.yaml` | openjd | §3.4: "Maximum number of elements: 1024" | Spec explicitly limits range to 1024 items. CLI doesn't enforce. **Fix openjd**. |
| `3.4.2--empty-path-value.invalid.yaml` | openjd | §3.4.2: TaskParameterStringValue | Empty string is not a valid path on any OS. **Fix openjd** to reject empty PATH values. |
| `3.5--embedded-filename-too-long.invalid.yaml` | openjd | §6.1: "Max length: 64. 256 if using extension FEATURE_BUNDLE_1" | CLI applies relaxed limit (256) without requiring extension declaration. **Fix openjd** to enforce 64 limit unless FEATURE_BUNDLE_1 is declared. |
| `6.1--embedded-filename-with-path.invalid.yaml` | openjd | §6.1: "must strictly be the basename of the filename, and not contain any directory pathing" | Spec explicitly forbids path separators in embedded filenames with example `dir/foo.txt` as invalid. CLI accepts them. **Fix openjd**. |
| `7--identifier-too-long.invalid.yaml` | openjd | §7.1: "Maximum length: 64 characters. 512 if using extension FEATURE_BUNDLE_1" | CLI applies relaxed limit (512) without requiring extension declaration. **Fix openjd** to enforce 64 limit unless FEATURE_BUNDLE_1 is declared. |
| `7--job-name-control-char-1f.invalid.yaml` | openjd | §1.1.1: "Any unicode character except those in the Cc unicode character category" | Spec explicitly forbids control characters (Cc category). CLI doesn't check. **Fix openjd**. |
| `7--job-name-control-char-7f.invalid.yaml` | openjd | Same as above | DEL character (0x7F) is in Cc category. **Fix openjd**. |
| `7--job-name-control-char-9f.invalid.yaml` | openjd | Same as above | 0x9F is in Cc category. **Fix openjd**. |
| `7--job-name-control-chars.invalid.yaml` | openjd | Same as above | Multiple control chars test. **Fix openjd**. |
| `7--step-name-too-long.invalid.yaml` | openjd | §3.1: "Maximum length: 64 characters. 512 if using extension FEATURE_BUNDLE_1" | CLI applies relaxed limit (512) without requiring extension declaration. **Fix openjd** to enforce 64 limit unless FEATURE_BUNDLE_1 is declared. |
| `ext-TASK_CHUNKING--missing-extension.invalid.yaml` | openjd | Extensions must be declared | Using `CHUNK[INT]` type without declaring TASK_CHUNKING extension. CLI should require extension declaration. **Fix openjd**. |

### FEATURE_BUNDLE_1 Extension Failures (6)

Test run: 2026-03-27 (openjd-cli 0.7.5)

**FEATURE_BUNDLE_1 total: 36 passed, 5 failed**

All 5 failures are the same root cause: the CLI applies FEATURE_BUNDLE_1 relaxed limits and features without requiring the extension to be declared. This is the same class of bug as the existing base test failures for `2--too-many-parameters.invalid.yaml`, `3.5--embedded-filename-too-long.invalid.yaml`, `7--identifier-too-long.invalid.yaml`, and `7--step-name-too-long.invalid.yaml`.

| Test | Fix | Spec Reference | Analysis |
|------|-----|----------------|----------|
| `3.3.1--amount-min-format-string-without-extension.invalid.yaml` | openjd | §3.3.1: "Can only be a \<nonnegativefloatstring\> when using the extension FEATURE_BUNDLE_1" | CLI accepts format string in amount `min` without extension. **Fix openjd** to reject format strings unless FEATURE_BUNDLE_1 is declared. |
| `5--timeout-format-string-without-extension.invalid.yaml` | openjd | §5: "Can only be a \<posintstring\> when using the extension FEATURE_BUNDLE_1" | CLI accepts format string in `timeout` without extension. **Fix openjd** to reject format strings unless FEATURE_BUNDLE_1 is declared. |
| `5--notify-period-format-string-without-extension.invalid.yaml` | openjd | §5: "Can only be a \<posintstring\> when using the extension FEATURE_BUNDLE_1" | CLI accepts format string in `notifyPeriodInSeconds` without extension. **Fix openjd**. |
| `6.1--end-of-line-without-extension.invalid.yaml` | openjd | §6.1: "Requires the FEATURE_BUNDLE_1 extension" | CLI accepts `endOfLine` property without extension declaration. **Fix openjd** to reject unless FEATURE_BUNDLE_1 is declared. |
| `8--simple-action-without-extension.invalid.yaml` | openjd | §8: "This object is only available in the extension FEATURE_BUNDLE_1" | CLI accepts SimpleAction syntax sugar without extension declaration. **Fix openjd** to reject unless FEATURE_BUNDLE_1 is declared. |
