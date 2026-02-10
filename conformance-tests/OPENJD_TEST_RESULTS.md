# OpenJD Conformance Test Results

Test run: 2026-02-10

**Total: 651 passed, 14 failed**

## Failure Analysis

### Template Validation Failures (14)

| Test | Fix | Spec Reference | Analysis |
|------|-----|----------------|----------|
| `2.1--minlength-zero.yaml` | openjd | §2.1: "minLength: \<integer\>" | CLI rejects `minLength: 0` but spec allows any integer. A minLength of 0 means "no minimum" which is valid. **Fix openjd** to accept 0. |
| `2.4--decimals-on-dropdown.invalid.yaml` | both | §2.4: decimals under SPIN_BOX control | Spec defines `decimals` under FLOAT's userInterface but doesn't explicitly restrict it to SPIN_BOX. The description says "places editable" which implies SPIN_BOX only. **Fix spec** to add explicit constraint "Can only be provided when *control* is SPIN_BOX", **fix openjd** to validate. |
| `2.4--decimals-on-hidden.invalid.yaml` | both | §2.4: decimals under SPIN_BOX control | Same as above - `decimals` makes no sense for HIDDEN controls. **Fix spec** and **fix openjd**. |
| `3.3--duplicate-amount-names.invalid.yaml` | both | §3.3: amounts list | Spec doesn't explicitly forbid duplicates, but duplicate amount names are nonsensical (which value wins?). **Fix spec** to add uniqueness constraint, **fix openjd** to validate. |
| `3.3--duplicate-attribute-names.invalid.yaml` | both | §3.3: attributes list | Same reasoning - duplicate attribute names are ambiguous. **Fix spec** and **fix openjd**. |
| `3.3.2--value-case-insensitive.yaml` | openjd | §3.3.2: attribute values | Spec says attribute values follow capability naming which is case-insensitive. CLI treats them case-sensitively. **Fix openjd** to normalize case. |
| `3.4--too-many-range-items.invalid.yaml` | openjd | §3.4: "Maximum number of elements: 1024" | Spec explicitly limits range to 1024 items. CLI doesn't enforce. **Fix openjd**. |
| `3.4.2--empty-path-value.invalid.yaml` | openjd | §3.4.2: TaskParameterStringValue | Empty string is not a valid path on any OS. **Fix openjd** to reject empty PATH values. |
| `6.1--embedded-filename-with-path.invalid.yaml` | openjd | §6.1: "must strictly be the basename of the filename, and not contain any directory pathing" | Spec explicitly forbids path separators in embedded filenames with example `dir/foo.txt` as invalid. CLI accepts them. **Fix openjd**. |
| `7--job-name-control-char-1f.invalid.yaml` | openjd | §1.1.1: "Any unicode character except those in the Cc unicode character category" | Spec explicitly forbids control characters (Cc category). CLI doesn't check. **Fix openjd**. |
| `7--job-name-control-char-7f.invalid.yaml` | openjd | Same as above | DEL character (0x7F) is in Cc category. **Fix openjd**. |
| `7--job-name-control-char-9f.invalid.yaml` | openjd | Same as above | 0x9F is in Cc category. **Fix openjd**. |
| `7--job-name-control-chars.invalid.yaml` | openjd | Same as above | Multiple control chars test. **Fix openjd**. |
| `ext-TASK_CHUNKING--missing-extension.invalid.yaml` | openjd | Extensions must be declared | Using `CHUNK[INT]` type without declaring TASK_CHUNKING extension. CLI should require extension declaration. **Fix openjd**. |
