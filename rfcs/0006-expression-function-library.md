* Feature Name: Expression Function Library
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/112
* Start Date: 2026-02-02
* Specification Version: 2023-09 extension EXPR
* Accepted On: (pending)

## Summary

This RFC defines the operators and built-in functions for the expression language introduced in
RFC 0005. By separating the function library from the core language specification, we enable
independent evaluation and evolution of these concerns. The library provides arithmetic, string,
list, path, and serialization operations sufficient for common job template use cases.

## Basic Examples

### Arithmetic Operations

```yaml
# Calculate end frame for a chunk
args:
  - "--end"
  - "{{min(Task.Param.Frame + Param.FramesPerTask, Param.FrameEnd) - 1}}"
```

### String Manipulation

```yaml
# Build output filename
args:
  - "{{ Param.InputFile.stem.upper() + '_final' + Param.InputFile.suffix }}"
```

### Path Operations

```yaml
# Construct output path
args:
  - "{{ (Param.OutputDir / Param.InputFile.name).with_suffix('.png') }}"
```

### Path Manipulation

Build output paths from input paths using the `/` operator and path functions:

```yaml
parameterDefinitions:
  - name: InputFile
    type: PATH
  - name: OutputDir
    type: PATH
steps:
  - name: Convert
    script:
      actions:
        onRun:
          command: convert
          args:
            - "{{Param.InputFile}}"
            - "{{ (Param.OutputDir / Param.InputFile.name).with_suffix('_converted.png') }}"
            - "--log"
            - "{{ Param.OutputDir / Param.InputFile.name + '.log' }}"
```

### Shell Quoting

```yaml
# Safe command construction for wrapper scripts
embeddedFiles:
  - name: wrapper
    type: TEXT
    data: |
      #!/bin/bash
      exec {{repr_sh(Task.Command)}}
```

## Motivation

RFC 0005 defines the expression language grammar, type system, and evaluation semantics. This RFC
completes the language by specifying the concrete operators and functions available to template
authors. Separating these concerns allows for independent review of these different concerns,
giving each its due attention.

The function library addresses specific use cases:

1. **Safe string quoting for scripts** - Embedding parameter values into bash or Python scripts
   is error-prone. `echo '{{Param.Input}}'` breaks if Input contains single quotes.
   `print(r'{{Param.Input}}')` breaks similarly. Functions like `repr_sh()` and
   `repr_py()` enable safe embedding: `echo {{repr_sh(Param.Input)}}` and
   `print({{repr_py(Param.Input)}})`.

2. **Wrapping task runs** - The proposed `onWrapTaskRun` action needs to be able to reproduce
   calling the task run in a subprocess environment matching its original definition. It uses
   functions for joining lists, `sh`-quoting strings and joining strings.

### Design Requirement: Function Naming Consistency

Built-in functions should follow consistent naming conventions that are easy to remember.
For example, quoting functions follow a pattern like `repr_sh`/`repr_py`/`repr_json`.
Mixing styles like `shlex_quote`, `py_repr`, `json_dump` is avoided.

## Specification

### Operators

Operators are documented using Python's operator method names with type signatures.

#### Arithmetic Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: int, b: int) -> int` | `a + b` addition |
| `__add__(a: float, b: float) -> float` | `a + b` addition |
| `__sub__(a: int, b: int) -> int` | `a - b` subtraction |
| `__sub__(a: float, b: float) -> float` | `a - b` subtraction |
| `__mul__(a: int, b: int) -> int` | `a * b` multiplication |
| `__mul__(a: float, b: float) -> float` | `a * b` multiplication |
| `__truediv__(a: int, b: int) -> float` | `a / b` division (see also Path Operators) |
| `__truediv__(a: float, b: float) -> float` | `a / b` division |
| `__floordiv__(a: int, b: int) -> int` | `a // b` integer division |
| `__floordiv__(a: float, b: float) -> int` | `a // b` integer division |
| `__mod__(a: int, b: int) -> int` | `a % b` modulo |
| `__mod__(a: float, b: float) -> float` | `a % b` modulo |
| `__pow__(a: int, b: int) -> float | int` | `a ** b` exponentiation |
| `__pow__(a: float, b: float) -> float` | `a ** b` exponentiation |
| `__neg__(a: int) -> int` | `-a` negation (unary) |
| `__neg__(a: float) -> float` | `-a` negation (unary) |
| `__pos__(a: int) -> int` | `+a` identity (unary) |
| `__pos__(a: float) -> float` | `+a` identity (unary) |

When mixing int and float operands, the int is promoted to float and the float overload is used.

For `int ** int`, the result is `int` when the exponent is non-negative, and `float` when the exponent is negative (e.g., `2 ** 3 = 8` but `2 ** -3 = 0.125`).

#### String Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: string, b: string) -> string` | `a + b` concatenation |
| `__add__(a: string, b: range_expr) -> string` | `a + b` concatenation (range_expr converted to canonical string form) |
| `__add__(a: range_expr, b: string) -> string` | `a + b` concatenation (range_expr converted to canonical string form) |
| `__mul__(s: string, n: int) -> string` | `s * n` repetition |
| `__contains__(a: string, b: string) -> bool` | `b in a` substring test |
| `__not_contains__(a: string, b: string) -> bool` | `b not in a` substring test |

#### List Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: list[T1], b: list[T2]) -> list[T3]` | `a + b` concatenation (see type coercion below) |
| `__add__(a: range_expr, b: list[T1]) -> list[T2]` | `a + b` concatenation (range_expr treated as list[int]) |
| `__add__(a: list[T1], b: range_expr) -> list[T2]` | `a + b` concatenation (range_expr treated as list[int]) |
| `__add__(a: range_expr, b: range_expr) -> list[int]` | `a + b` concatenation |
| `__mul__(a: list[T], n: int) -> list[T]` | `a * n` repetition |
| `__contains__(list: list[T], item: T) -> bool` | `item in list` membership test |
| `__not_contains__(list: list[T], item: T) -> bool` | `item not in list` membership test |
| `__contains__(r: range_expr, item: int) -> bool` | `item in r` membership test |
| `__not_contains__(r: range_expr, item: int) -> bool` | `item not in r` membership test |

**List Concatenation Type Coercion**

When concatenating lists with different element types, the result type is determined by
finding a common type that both element types can be coerced to:

- `list[int] + list[int]` → `list[int]`
- `list[float] + list[float]` → `list[float]`
- `list[int] + list[float]` → `list[float]` (int elements coerced to float)
- `list[float] + list[int]` → `list[float]` (int elements coerced to float)
- `list[nulltype] + list[T]` → `list[T]` (empty list takes the other's type)
- `list[T] + list[nulltype]` → `list[T]` (empty list takes the other's type)

This coercion also applies when concatenating with `range_expr` values, which are treated
as `list[int]` for concatenation purposes:

- `list[int] + range_expr` → `list[int]`
- `list[float] + range_expr` → `list[float]` (range_expr ints coerced to float)
- `range_expr + list[int]` → `list[int]`
- `range_expr + range_expr` → `list[int]`

List comprehensions produce lists, so they participate in concatenation naturally:

```yaml
# Combine explicit list with comprehension result
{{ [0] + [x * 2 for x in range_expr('1-5')] }}  # [0, 2, 4, 6, 8, 10]

# Combine two comprehensions
{{ [x for x in range_expr('1-3')] + [x for x in range_expr('10-12')] }}  # [1, 2, 3, 10, 11, 12]
```

Concatenation of incompatible list types (e.g., `list[string] + list[int]`) is an error.

#### Path Operators

| Signature | Description |
|-----------|-------------|
| `__truediv__(p: path, child: string) -> path` | `p / child` join path components |
| `__truediv__(p: path, child: path) -> path` | `p / child` join path components |
| `__add__(p: path, suffix: string) -> path` | `p + suffix` append string to last component |

The `/` operator creates child paths by joining components. If the right operand is an
absolute path, it replaces the left operand entirely (matching Python's `pathlib` behavior).
For URI paths, joining a relative child is equivalent to `path(p.parts + child.parts)`,
ensuring forward-slash separators are used regardless of the evaluator's `path_format`.
A trailing slash on the left operand is consumed by the join (matching `pathlib` behavior),
so `path("s3://bucket/dir/") / "file"` produces `s3://bucket/dir/file`:

```yaml
{{ Param.OutputDir / 'renders' / Param.SceneName }}
{{ Param.BaseDir / Param.Override }}  # Override can be relative or absolute
```

The `+` operator appends a string directly to the path (no separator):

```yaml
{{ Param.OutputDir / Param.InputFile.stem + '_converted.png' }}
```

#### Comparison Operators

| Signature | Description |
|-----------|-------------|
| `__eq__(a: T1, b: T2) -> bool` | `a == b` equal |
| `__ne__(a: T1, b: T2) -> bool` | `a != b` not equal |
| `__lt__(a: T1, b: T2) -> bool` | `a < b` less than |
| `__gt__(a: T1, b: T2) -> bool` | `a > b` greater than |
| `__le__(a: T1, b: T2) -> bool` | `a <= b` less than or equal |
| `__ge__(a: T1, b: T2) -> bool` | `a >= b` greater than or equal |

##### Cross-Type Equality Comparison

Equality (`==`) and inequality (`!=`) operators handle cross-type comparisons as follows:

- `string` vs `path`: The path is converted to string for comparison
- `int` vs `float`: Numeric comparison (e.g., `5 == 5.0` is `true`)
- `list` vs `range_expr`: The range_expr is expanded and compared element-by-element
  (e.g., `[1, 2, 3] == range_expr("1-3")` is `true`)
- `string` vs (`int` | `float`): Always unequal (e.g., `"5" == 5` is `false`)
- `bool` vs any non-`bool`: Always unequal (e.g., `true == 1` is `false`)
- scalar vs `list`: Always unequal (e.g., `1 == [1]` is `false`)
- Other cross-type comparisons: Always unequal

List equality is recursive: two lists are equal if they have the same length and all
corresponding elements are equal. Cross-type element comparisons follow the same rules,
so `[5] == [5.0]` is `true` and `[[5]] == [[5.0]]` is `true`.

This differs from Python where `True == 1` and `False == 0`. The stricter behavior prevents
subtle bugs from implicit type coercion in boolean contexts.

##### Ordering Comparison

Ordering comparison operators (`<`, `<=`, `>`, `>=`) work on `int`, `float`, `string`, `path`,
`list`, and `bool` types. Comparing different types (except `int`/`float` and `string`/`path`)
is an error. Path comparison is lexicographic on the string representation. String and path can
be compared with each other (path is converted to string). Bool comparison treats `False < True`.

List ordering uses lexicographic comparison: elements are compared pairwise from the start, and
the first unequal pair determines the result. If all compared elements are equal, the shorter
list is considered less than the longer one. Nested lists are compared recursively.

#### Logical Operators

| Signature | Description |
|-----------|-------------|
| `a and b` | If `a` is `null` or `false`, return `a`; otherwise evaluate and return `b` (short-circuit) |
| `a or b` | If `a` is `null` or `false`, evaluate and return `b`; otherwise return `a` (short-circuit) |
| `__not__(a: bool) -> bool` | `not a` logical NOT |

The `and` and `or` operators are value-returning with null-coalescing semantics. See
[RFC 0005](0005-expression-language.md) AST Transformation rule 6 for the full specification.

Note: `not` remains strictly boolean — it requires a `bool` operand and returns `bool`.

#### Subscript Operator

| Signature | Description |
|-----------|-------------|
| `__getitem__(list: list[T], index: int) -> T` | `list[index]` access by zero-based index |
| `__getitem__(r: range_expr, index: int) -> int` | `r[index]` access by zero-based index |
| `__getitem__(s: string, index: int) -> string` | `s[index]` access single character by index |

Negative indices count from the end: `list[-1]` is the last element. Index out of bounds is an error.

#### Slice Operator

Slicing uses Python semantics with `[start:stop:step]` syntax. All bounds are optional.

| Signature | Description |
|-----------|-------------|
| `__getitem__(list: list[T], start: int?, stop: int?, step: int?) -> list[T]` | `list[start:stop:step]` slice |
| `__getitem__(r: range_expr, start: int?, stop: int?, step: int?) -> list[int]` | `r[start:stop:step]` slice |
| `__getitem__(s: string, start: int?, stop: int?, step: int?) -> string` | `s[start:stop:step]` slice |

Note: The `path` type does not support subscript or slice operations, matching Python's `pathlib.Path`
behavior. Use `p.parts` to get path components as a list, which can then be sliced.

Slice semantics follow Python:
- `start` defaults to 0 (or end if step < 0)
- `stop` defaults to length (or before start if step < 0)
- `step` defaults to 1; step of 0 is an error
- Negative indices count from end
- Out-of-bounds indices are clamped to valid range (no error)

Examples:
- `[1, 2, 3, 4, 5][1:4]` → `[2, 3, 4]`
- `[1, 2, 3, 4, 5][::-1]` → `[5, 4, 3, 2, 1]`
- `"hello"[1:4]` → `"ell"`
- `path("/a/b/c/d").parts[1:]` → `["a", "b", "c", "d"]` (slice the parts list, not the path)

### Built-in Functions

#### General Functions

| Signature | Description |
|-----------|-------------|
| `len(list: list[T]) -> int` | Length of list |
| `len(s: string) -> int` | Length of string (number of unicode codepoints) |
| `len(p: path) -> int` | Length of path's string representation |
| `len(r: range_expr) -> int` | Number of values in range expression |
| `bool(value: bool) -> bool` | Pass-through |
| `bool(value: nulltype) -> bool` | Returns `false` |
| `bool(value: int) -> bool` | `0` is `false`, all others `true` |
| `bool(value: float) -> bool` | `0.0` is `false`, all others `true` |
| `bool(value: string) -> bool` | See string-to-bool conversion below |
| `string(value: bool \| int \| float \| string \| path \| range_expr \| nulltype) -> string` | Convert to string (`nulltype` returns `"null"`) |
| `string(value: list[T]) -> string` | Convert list to JSON string representation |
| `int(value: int \| float \| string) -> int` | Convert to integer |
| `float(value: int \| float \| string) -> float` | Convert to float |
| `list(value: range_expr) -> list[int]` | Convert range expression to list |
| `range_expr(s: string) -> range_expr` | Parse string as range expression (e.g., `"1-10"`, `"1,3,5-7"`) |
| `range_expr(l: list[int]) -> range_expr` | Convert integer list to range expression |

Calling `bool()` on `path` or `list[T]` values is an error. This prevents accidental implicit
coercion to bool in conditional contexts. Implementations must raise a clear error message such as
"Cannot convert path to bool" or "Cannot convert list to bool".

**Note about bool conversion from string**: The following case-insensitive string values are
accepted: `"1"`, `"true"`, `"on"`, `"yes"` become `true`; `"0"`, `"false"`, `"off"`, `"no"`
become `false`. All other string values are rejected with an error.

**Note about int and float conversion**: If the value cannot be nondestructively converted,
it's an error. E.g. `int(3.75)` is an error, the functions `floor`, `ceil`, and `round` are for
this case.

**Note about range_expr**: Parsing an empty string with `range_expr("")` is an error,
`range_expr(" ")` (whitespace-only) is an error, and
`range_expr([])` (empty list) is also an error. Range expressions must contain at least one value.

#### Validation Functions

| Signature | Description |
|-----------|-------------|
| `fail(message: string) -> noreturn` | Fail with error message |

The `fail` function immediately terminates expression evaluation with an error, communicating
the provided message to the user.

The `fail` function is useful for validation and providing clear error messages:

```python
# Validate parameter value
Param.Count if Param.Count > 0 else fail("Count must be positive")

# With short-circuit evaluation - fail() only called if condition is false
Param.Mode in ["fast", "slow"] or fail("Mode must be 'fast' or 'slow'")

# Validate file extension
Param.InputFile.suffix == ".exr" or fail("Input must be an EXR file")
```

The return type `noreturn` indicates that `fail()` never returns a value—it always raises an error.
In union types, `noreturn` collapses to nothing (`T | noreturn` simplifies to `T`), which means
expressions using `fail()` for validation have precise types:

```python
# Type is float, not float?
frame_rate = Param.FrameRate if Param.FrameRate > 0 else fail("must be positive")
```

#### Math Functions

| Signature | Description |
|-----------|-------------|
| `abs(x: T) -> T` | Absolute value (`T` in `int`, `float`) |
| `min(a: T, b: T) -> T` | Minimum of two values (`T` in `int`, `float`) |
| `min(a: T, b: T, c: T) -> T` | Minimum of three values (`T` in `int`, `float`) |
| `min(values: list[T]) -> T` | Minimum of list (`T` in `int`, `float`); error if empty |
| `min(values: list[nulltype]) -> noreturn` | Error: "min() requires a non-empty list" |
| `min(r: range_expr) -> int` | Minimum value in range expression; error if empty |
| `max(a: T, b: T) -> T` | Maximum of two values (`T` in `int`, `float`) |
| `max(a: T, b: T, c: T) -> T` | Maximum of three values (`T` in `int`, `float`) |
| `max(values: list[T]) -> T` | Maximum of list (`T` in `int`, `float`); error if empty |
| `max(values: list[nulltype]) -> noreturn` | Error: "max() requires a non-empty list" |
| `max(r: range_expr) -> int` | Maximum value in range expression; error if empty |
| `sum(values: list[nulltype]) -> int` | Sum of empty list, returns `0` |
| `sum(values: list[int]) -> int` | Sum of integer list |
| `sum(values: list[float]) -> float` | Sum of float list |
| `sum(r: range_expr) -> int` | Sum of all values in range expression |
| `floor(x: int) -> int` | Floor of integer (identity) |
| `floor(x: float) -> int` | Largest integer less than or equal to x |
| `ceil(x: int) -> int` | Ceiling of integer (identity) |
| `ceil(x: float) -> int` | Smallest integer greater than or equal to x |
| `round(x: float) -> int` | Round to nearest integer, tie rounds to even (e.g., `round(0.5)` = `0`, `round(1.5)` = `2`, `round(2.5)` = `2`) |
| `round(x: float, ndigits: int) -> float \| int` | Round to number of decimals; returns `int` when `ndigits` ≤ 0, `float` when `ndigits` > 0 |
| `round(x: int, ndigits: int) -> int` | Round integer to given decimal position |

**Special note about `round`**: `round(x, ndigits)` with positive `ndigits` preserves trailing
zeros in the decimal representation. For example, `round(3.5, 2)` produces a value that converts
to the string `"3.50"`, not `"3.5"`. With non-positive `ndigits`, the result is an integer (e.g.,
`round(1234.5, -1)` returns `1230`).

#### List Functions

| Signature | Description |
|-----------|-------------|
| `range(stop: int) -> list[int]` | Integers from 0 to stop-1 |
| `range(start: int, stop: int) -> list[int]` | Integers from start to stop-1 |
| `range(start: int, stop: int, step: int) -> list[int]` | Integers from start to stop-1 with step |
| `flatten(lists: list[list[T]]) -> list[T]` | Flatten nested lists |
| `flatten(values: list[T]) -> list[T]` | Identity for already-flat lists |
| `flatten(values: list[nulltype]) -> list[nulltype]` | Identity for empty list |
| `sorted(values: list[T]) -> list[T]` | Return new list with elements sorted in ascending order |
| `reversed(values: list[T]) -> list[T]` | Return new list with elements in reverse order |
| `unique(values: list[T]) -> list[T]` | Return new list with duplicates removed, preserving first occurrence order |
| `any(values: list[nulltype]) -> bool` | False (empty list) |
| `any(values: list[bool]) -> bool` | True if any element is true |
| `all(values: list[nulltype]) -> bool` | True (empty list) |
| `all(values: list[bool]) -> bool` | True if all elements are true |

Examples:
- `range(5)` returns `[0, 1, 2, 3, 4]`
- `range(1, 5)` returns `[1, 2, 3, 4]`
- `range(0, 10, 2)` returns `[0, 2, 4, 6, 8]`
- `range(5, 0, -1)` returns `[5, 4, 3, 2, 1]`
- `flatten([[1, 2], [3]])` returns `[1, 2, 3]`
- `sorted([3, 1, 2])` returns `[1, 2, 3]`
- `sorted(["b", "a", "c"])` returns `["a", "b", "c"]`
- `reversed([1, 2, 3])` returns `[3, 2, 1]`

The `list[nulltype]` overloads handle empty lists, matching Python semantics.

#### String Functions

| Signature | Description |
|-----------|-------------|
| `upper(s: string) -> string` | Convert to uppercase |
| `lower(s: string) -> string` | Convert to lowercase |
| `capitalize(s: string) -> string` | Capitalize first character, lowercase rest |
| `title(s: string) -> string` | Capitalize first character of each word |
| `strip(s: string) -> string` | Remove leading/trailing whitespace |
| `strip(s: string, chars: string) -> string` | Remove leading/trailing characters in `chars` |
| `lstrip(s: string) -> string` | Remove leading whitespace |
| `lstrip(s: string, chars: string) -> string` | Remove leading characters in `chars` |
| `rstrip(s: string) -> string` | Remove trailing whitespace |
| `rstrip(s: string, chars: string) -> string` | Remove trailing characters in `chars` |
| `removeprefix(s: string, prefix: string) -> string` | Remove prefix if present, otherwise return unchanged |
| `removesuffix(s: string, suffix: string) -> string` | Remove suffix if present, otherwise return unchanged |
| `startswith(s: string, prefix: string) -> bool` | Test if string starts with prefix |
| `endswith(s: string, suffix: string) -> bool` | Test if string ends with suffix |
| `isdigit(s: string) -> bool` | True if all characters are digits and string is non-empty |
| `isalpha(s: string) -> bool` | True if all characters are alphabetic and string is non-empty |
| `isalnum(s: string) -> bool` | True if all characters are alphanumeric and string is non-empty |
| `isspace(s: string) -> bool` | True if all characters are whitespace and string is non-empty |
| `isupper(s: string) -> bool` | True if all cased characters are uppercase and there is at least one cased character |
| `islower(s: string) -> bool` | True if all cased characters are lowercase and there is at least one cased character |
| `isascii(s: string) -> bool` | True if all characters are ASCII (U+0000–U+007F), or string is empty |
| `count(s: string, sub: string) -> int` | Count non-overlapping occurrences of substring. The `sub` argument must be non-empty; an empty `sub` is an error. |
| `find(s: string, sub: string) -> int` | Return lowest index of substring, or -1 if not found. The `sub` argument must be non-empty; an empty `sub` is an error. |
| `rfind(s: string, sub: string) -> int` | Return highest index of substring, or -1 if not found. The `sub` argument must be non-empty; an empty `sub` is an error. |
| `index(s: string, sub: string) -> int` | Return lowest index of substring. Raises an error if not found. The `sub` argument must be non-empty; an empty `sub` is an error. |
| `rindex(s: string, sub: string) -> int` | Return highest index of substring. Raises an error if not found. The `sub` argument must be non-empty; an empty `sub` is an error. |
| `replace(s: string, old: string, new: string) -> string` | Replace all occurrences of old with new. The `old` argument must be non-empty; an empty `old` is an error. |
| `split(s: string) -> list[string]` | Split string on whitespace runs, stripping leading/trailing whitespace |
| `split(s: string, sep: string) -> list[string]` | Split string by separator |
| `rsplit(s: string) -> list[string]` | Split string on whitespace runs, stripping leading/trailing whitespace |
| `rsplit(s: string, sep: string) -> list[string]` | Split string by separator, starting from the right |
| `split(s: string, sep: string, maxsplit: int) -> list[string]` | Split string by separator, at most maxsplit times |
| `rsplit(s: string, sep: string, maxsplit: int) -> list[string]` | Split string by separator from the right, at most maxsplit times |
| `join(items: list[nulltype], sep: string) -> string` | Join empty list, returns `""` |
| `join(items: list[string], sep: string) -> string` | Join list elements with separator |
| `join(items: list[path], sep: string) -> string` | Join path list elements with separator |
| `ljust(s: string, width: int) -> string` | Left-justify, pad with spaces to width |
| `rjust(s: string, width: int) -> string` | Right-justify, pad with spaces to width |
| `center(s: string, width: int) -> string` | Center, pad with spaces to width |
| `zfill(s: string, width: int) -> string` | Pad with leading zeros to width; a leading sign (`+`/`-`) is preserved before the padding |
| `zfill(n: int, width: int) -> string` | Convert int to string, pad with leading zeros; negative integers preserve the sign before padding |
| `zfill(x: float, width: int) -> string` | Convert float to string, pad with leading zeros; negative floats preserve the sign before padding |

Examples:
- `split("a,b,c", ",")` and `"a,b,c".split(",")` return `["a", "b", "c"]`
- `join(["a", "b", "c"], ",")` and `["a", "b", "c"].join(",")` return `"a,b,c"`
- `zfill(42, 5)` and `(42).zfill(5)` return `"00042"`
- `zfill(-1, 3)` returns `"-01"` (sign preserved, zeros pad after sign)
- `zfill("-10", 4)` returns `"-010"`
- `"frame_".rjust(10) + zfill(Task.Param.Frame, 4)` returns `"    frame_0001"`

Note: Method calls on integer and float literals require parentheses around the literal
(e.g., `(42).zfill(5)` not `42.zfill(5)`) because the Python grammar parses `42.` as the
start of a float literal.

Note: The `sep` argument to `split` and `rsplit` must be non-empty. An empty separator is an error.
To split a string into individual characters, use `[s[i] for i in range(len(s))]`.

Note: Splitting an empty string returns a list containing one empty string, not an empty list
(e.g., `''.split(',')` returns `['']`). This matches Python's `str.split()` behavior.

Note: The `join` function intentionally differs from Python's `str.join()`. In Python,
`join` is a string method (`",".join(list)`), but OpenJD uses `list.join(sep)` instead.
This design enables natural method chaining like `items.split(';').join(',')` and matches
the convention used by JavaScript and Ruby.

#### Regular Expression Functions

| Signature | Description |
|-----------|-------------|
| `re_match(s: string, pattern: string) -> list[string]?` | Match at START of string, return captured groups or null |
| `re_search(s: string, pattern: string) -> list[string]?` | Match ANYWHERE in string, return captured groups or null |
| `re_findall(s: string, pattern: string) -> list[string] \| list[list[string]]` | Find all non-overlapping matches; returns full matches if no groups, list of captured group values (not full matches) if one group, list of group lists if multiple groups |
| `re_sub(s: string, pattern: string, repl: string) -> string` | Replace all regex matches with replacement. The `repl` string is literal text — group references (`\1`, `\g<1>`, `$1`, `${1}`) are not supported and are errors. |
| `re_escape(s: string) -> string` | Escape regex metacharacters for literal matching |
| `re_split(s: string, pattern: string) -> list[string]` | Split string by regex pattern |
| `re_split(s: string, pattern: string, maxsplit: int) -> list[string]` | Split string by regex pattern, at most maxsplit times |

The regex syntax is the intersection of Python's `re` module and Rust's `regex` crate,
ensuring cross-platform compatibility. Supported features:
- Character classes: `[abc]`, `[^abc]`, `[a-z]`, `\d`, `\w`, `\s` (and negations)
- Anchors: `^`, `$`, `\b`
- Quantifiers: `*`, `+`, `?`, `{n}`, `{n,m}`, and non-greedy variants
- Groups: `(...)`, `(?:...)` (non-capturing)
- Alternation: `|`

Character classes `\d`, `\w`, `\s` (and their negations `\D`, `\W`, `\S`) use Unicode
semantics — for example, `\d` matches any Unicode digit, not just `[0-9]`. Implementations
using Rust's `regex` crate must enable the Unicode flag for these classes.

The `pattern` argument to all regex functions must be non-empty. An empty pattern is an error.

Not supported (Python `re` features not in Rust `regex`):
- Backreferences (`\1`, `\2`, etc.)
- Lookahead (`(?=...)`, `(?!...)`)
- Lookbehind (`(?<=...)`, `(?<!...)`)
- Conditional patterns (`(?(id)yes|no)`)
- Named backreferences (`(?P=name)`)
- `\Z` end-of-string anchor (use `$` instead; Rust uses `\z` with different semantics)

Not supported (Rust `regex` features not in Python `re`):
- `\z` end-of-string anchor (use `$` or `\Z` in Python)
- `\x{HHHH}` Unicode brace syntax (use `\xHH`, `\uHHHH`, or `\UHHHHHHHH` in Python)
- `\u{HHHH}` Unicode brace syntax (use `\uHHHH` in Python)
- `\U{HHHH}` Unicode brace syntax (use `\UHHHHHHHH` in Python)

Note: Both Python and Rust support `\xHH` (2 hex digits), `\uHHHH` (4 hex digits), and
`\UHHHHHHHH` (8 hex digits) for Unicode escapes. The brace syntax variants are Rust-only.

`re_match` matches only at the start of the string (like Python's `re.match`).
`re_search` matches anywhere in the string (like Python's `re.search`).

Both functions return a list where index 0 is the full match, and indices 1+ are the captured groups.

Examples:

```python
# Extract version number from filename
re_search("asset_v042_final.abc", r"_v(\d+)")  # returns ["_v042", "042"]

# Match at start only
re_match("v042_final", r"v(\d+)")              # returns ["v042", "042"]
re_match("asset_v042", r"v(\d+)")              # returns null (not at start)

# Check if pattern exists (use null comparison)
re_search("render_001.exr", r"_\d+\.exr$") != null  # returns true

# No capture groups - returns just the full match
re_search("hello123", r"\d+")                  # returns ["123"]

# Multiple capture groups
re_search("shot010_v003", r"shot(\d+)_v(\d+)") # returns ["shot010_v003", "010", "003"]

# Extract UDIM tile number (access group at index 1)
re_search("diffuse.1023.tx", r"\.(10\d{2})\.")[1]  # returns "1023"

# Find all shot numbers in a comp filename (with capture group - returns groups)
re_findall("shot010_shot020_shot035_comp.nk", r"shot(\d+)")  # returns ["010", "020", "035"]

# Find all matches (no capture group - returns full matches)
re_findall("shot010_shot020_shot035_comp.nk", r"shot\d+")    # returns ["shot010", "shot020", "shot035"]

# Multiple capture groups - returns list of group lists
re_findall("v1.2.3 and v4.5.6", r"v(\d+)\.(\d+)\.(\d+)")     # returns [["1", "2", "3"], ["4", "5", "6"]]

# Replace frame numbers
re_sub("frame_001", r"\d+", "002")          # returns "frame_002"

# Escape user input for literal matching
re_escape("file[1].txt")                        # returns "file\\[1\\]\\.txt"
```

#### Script Embedding and Serialization

| Signature | Description |
|-----------|-------------|
| `repr_sh(s: string) -> string` | Shell-escape a string for POSIX shells |
| `repr_sh(p: path) -> string` | Shell-escape a path for POSIX shells |
| `repr_sh(args: list[string]) -> string` | Join list into space-separated shell-escaped strings |
| `repr_sh(args: list[path]) -> string` | Join path list into space-separated shell-escaped strings |
| `repr_cmd(s: string) -> string` | Escape a string for Windows CMD |
| `repr_cmd(args: list[string]) -> string` | Join list into space-separated CMD-escaped strings |
| `repr_pwsh(s: string) -> string` | Escape a string for PowerShell |
| `repr_pwsh(n: int) -> string` | Integer literal for PowerShell |
| `repr_pwsh(f: float) -> string` | Float literal for PowerShell |
| `repr_pwsh(b: bool) -> string` | Boolean literal (`$true`/`$false`) for PowerShell |
| `repr_pwsh(p: path) -> string` | Escape a path for PowerShell |
| `repr_pwsh(r: range_expr) -> string` | String representation of range (e.g., `'1-10'`) |
| `repr_pwsh(args: list[T]) -> string` | PowerShell array literal `@(...)` |
| `repr_py(value: nulltype) -> string` | Returns `"None"` |
| `repr_py(r: range_expr) -> string` | String representation (e.g., `'1-10'`) |
| `repr_py(p: path) -> string` | Python string repr of path's string representation |
| `repr_py(value: T) -> string` | Convert to Python representation (`T` in `bool`, `int`, `float`, `string`, `list`) |
| `repr_json(value: nulltype) -> string` | Returns `"null"` |
| `repr_json(r: range_expr) -> string` | String representation (e.g., `"1-10"`) |
| `repr_json(p: path) -> string` | JSON string representation of path's string value |
| `repr_json(value: T) -> string` | Convert to JSON representation (`T` in `bool`, `int`, `float`, `string`, `list`) |

`repr_py` follows the behavior of Python's [repr](https://docs.python.org/3/library/functions.html#repr).

`repr_sh` follows the behavior of Python's
[shlex.quote](https://docs.python.org/3/library/shlex.html#shlex.quote) and
[shlex.join](https://docs.python.org/3/library/shlex.html#shlex.join).

Example: `repr_sh(["echo", "hello world"])` returns `"echo 'hello world'"`.

`repr_cmd` produces Windows CMD-safe strings suitable for use in `.bat` files:

- Strings containing special characters (`& | < > ^ " ( ) % !` or whitespace) are wrapped in double quotes.
- Inside double quotes, `^` and `"` are escaped with a caret prefix, and `%` is doubled to `%%` (required for `.bat` file contexts). Other special characters are literal within quotes.
- Simple strings without special characters are returned unquoted.
- `repr_cmd("hello")` returns `hello`.
- `repr_cmd("a & b")` returns `"a & b"` (`&` is literal inside quotes).
- `repr_cmd("a ^ b")` returns `"a ^^ b"` (`^` escaped inside quotes).
- `repr_cmd("100%")` returns `"100%%"` (`%` doubled for `.bat` files).
- `repr_cmd('say "hi"')` returns `"say ^"hi^""`.

Example: `repr_cmd(["echo", "hello & world"])` returns `echo "hello & world"`.

Like `repr_sh`, `path` values passed to `repr_cmd` are implicitly converted to string before escaping.

To safely set a CMD environment variable with a path that may contain special characters,
concatenate the variable name with the path value inside `repr_cmd`:

```yaml
# Safe: OUTPUT_DIR is within the quotes and special characters in path are escaped
set {{repr_cmd('OUTPUT_DIR=' + Param.OutputDirectory)}}
```

`repr_pwsh` produces PowerShell literals with proper escaping:

- **Strings and paths**: Wrapped in single quotes with embedded single quotes doubled.
  `repr_pwsh("it's")` returns `'it''s'`.
- **Integers and floats**: Passed through as-is. `repr_pwsh(42)` returns `42`.
- **Booleans**: Converted to PowerShell boolean literals. `repr_pwsh(true)` returns `$true`.
- **Range expressions**: String representation of the range. `repr_pwsh(Param.Frames)` where
  Frames is `1-10` returns `'1-10'`. Use `repr_pwsh(list(r))` to get an expanded array.
- **Lists**: Converted to PowerShell array syntax. `repr_pwsh(["a", "b"])` returns `@('a', 'b')`.

Example usage in a batch script:

```yaml
embeddedFiles:
  - name: render
    type: TEXT
    data: |
      @echo off
      powershell -Command "& { $frames = {{repr_pwsh(list(Task.Param.Frame))}}; ... }"
```

### Path Type Properties and Functions

The `path` type represents filesystem paths and URIs, and provides properties and functions
inspired by Python's `pathlib.PurePath`. Job parameters of type `PATH` evaluate to the `path`
type.

For filesystem paths, the behavior matches `PurePosixPath` or `PureWindowsPath` depending on
the evaluator's `path_format` setting. For URI paths (those with a `scheme://` prefix matching
`^[a-zA-Z][a-zA-Z0-9+.-]*://`), the scheme and authority are preserved as an opaque prefix
and the path portion is parsed with forward slashes and no normalization — consecutive slashes,
`.`, and `..` segments are preserved verbatim. This is necessary because URI path components
(such as S3 object keys) are opaque identifiers where `a//b` and `a/b` may refer to different
resources. The evaluator's `path_format` setting does not affect URI paths.

#### Path Properties

Properties are accessed using dot notation via UFCS (see RFC 0005).

| Signature | Description |
|-----------|-------------|
| `__property_name__(p: path) -> string` | `p.name` final path component (filename with extension) |
| `__property_stem__(p: path) -> string` | `p.stem` final component without the last suffix |
| `__property_suffix__(p: path) -> string` | `p.suffix` last file extension including dot, or empty string |
| `__property_suffixes__(p: path) -> list[string]` | `p.suffixes` list of file extensions (e.g., `['.tar', '.gz']`) |
| `__property_parent__(p: path) -> path` | `p.parent` parent directory path |
| `__property_parts__(p: path) -> list[string]` | `p.parts` path components as a list |

These properties match Python's `pathlib.PurePath` behavior for filesystem paths. For URI
paths, the scheme+authority prefix is treated as an opaque root — `parts` returns the
scheme+authority as the first element, followed by the path portion split by `/`:

```python
path("s3://bucket/dir/file.obj").parts     # ["s3://bucket", "dir", "file.obj"]
path("s3://bucket/dir/file.obj").name      # "file.obj"
path("s3://bucket/dir/file.obj").parent    # path("s3://bucket/dir")
path("s3://bucket/a//b/c").parts           # ["s3://bucket", "a", "", "b", "c"]
```

The path portion is not normalized, so consecutive slashes and `.`/`..` segments are
preserved. Empty strings in `parts` from consecutive slashes are preserved because URI path
components (such as S3 object keys) are opaque — `a//b` and `a/b` may refer to different
resources.

Examples:

```yaml
# Given Param.InputFile = "/projects/shot01/render.exr"
{{ Param.InputFile.name }}      # "render.exr"
{{ Param.InputFile.stem }}      # "render"
{{ Param.InputFile.suffix }}    # ".exr"
{{ Param.InputFile.parent }}    # path("/projects/shot01")

# Given Param.Archive = "/data/backup.tar.gz"
{{ Param.Archive.suffix }}      # ".gz"
{{ Param.Archive.suffixes }}    # [".tar", ".gz"]
{{ Param.Archive.stem }}        # "backup.tar"

# To get all extensions combined or the bare stem:
{{ Param.Archive.suffixes.join("") }}                              # ".tar.gz"
{{ Param.Archive.name.removesuffix(Param.Archive.suffixes.join("")) }}  # "backup"
```

#### Path Functions

| Signature | Description |
|-----------|-------------|
| `path(s: string) -> path` | Convert string to path |
| `path(parts: list[string]) -> path` | Construct path from components (like `Path(*parts)` in Python) |
| `with_name(p: path, name: string) -> path` | `p.with_name(name)` return path with the filename changed |
| `with_stem(p: path, stem: string) -> path` | `p.with_stem(stem)` return path with the stem changed |
| `with_suffix(p: path, suffix: string) -> path` | `p.with_suffix(suffix)` return path with the suffix changed |
| `with_number(p: path, num: int) -> path` | `p.with_number(num)` return path with the frame number replaced (see formats below) |
| `with_number(s: string, num: int) -> string` | Return string with the frame number replaced (same formats as path version) |
| `as_posix(p: path) -> string` | `p.as_posix()` return string with forward slashes |
| `is_absolute(p: path) -> bool` | `p.is_absolute()` true if path is absolute. URI paths are always absolute. |
| `is_relative_to(p: path, other: path) -> bool` | `p.is_relative_to(other)` true if path is relative to other. For URIs, checks prefix match on the full URI. |
| `relative_to(p: path, other: path) -> path` | `p.relative_to(other)` return the relative path from other to p. Error if p is not relative to other. For URIs, strips the matching prefix. |
| `apply_path_mapping(s: string) -> path` | `s.apply_path_mapping()` apply session path mapping rules (host context only) |

The `path(list[string])` overload enables reconstructing a path from its parts, supporting
patterns like `path(p.parts) == p` for roundtrip operations.

The `apply_path_mapping` function applies the session's path mapping rules to a path string and
returns a `path` value. This is the same transformation that occurs when accessing `Param.<name>`
for PATH-type job parameters.

This function is only available in `@fmtstring[host]` contexts (evaluated at runtime on the
worker host) where path mapping rules are available. Using it in submission-time contexts is
an error.

**Why `string -> path` instead of `path -> path`?**

The input is `string` rather than `path` because path mapping often involves cross-platform
scenarios where the source path originates from a different operating system than the worker.
For example, a job submitted from Windows with path `C:\projects\shot01\render.exr` may run
on a Linux worker where that path should map to `/mnt/studio/shot01/render.exr`. The source
path string may not be valid path syntax on the worker's OS, so it must remain a string until
path mapping transforms it into a valid local path.

This is why `RawParam.<name>` for PATH parameters returns `string` (the original submitted
value, which may be foreign path syntax), while `Param.<name>` returns `path` (after mapping
has been applied, yielding a valid local path).

Examples using UFCS method syntax:

```yaml
# Given Param.InputFile = "/projects/shot01/render.exr"
{{ Param.InputFile.with_name('output.png') }}     # path("/projects/shot01/output.png")
{{ Param.InputFile.with_stem('final') }}          # path("/projects/shot01/final.exr")
{{ Param.InputFile.with_suffix('.png') }}         # path("/projects/shot01/render.png")
{{ Param.InputFile.with_suffix('') }}             # path("/projects/shot01/render")

# Convert Windows path to POSIX for shell scripts
{{ Param.OutputDir.as_posix() }}                  # "C:/renders/project" (from "C:\renders\project")

# Apply path mapping to a modified path string
# Given RawParam.InputFile = "C:\studio\project\scene.ma" (submitted from Windows)
# and path mapping rule "C:\studio" -> "/mnt/studio" on Linux worker
{{ RawParam.InputFile.replace('scene.ma', 'output').apply_path_mapping() }}  # path("/mnt/studio/project/output")
```

##### Frame Number Substitution with `with_number`

The `with_number` function replaces frame number placeholders in path filenames. It recognizes
several common formats used by rendering applications:

| Format | Example Input | `with_number(72)` Output |
|--------|---------------|--------------------------|
| Digits | `file_003.exr` | `file_072.exr` |
| Printf `%d` | `file_%d.exr` | `file_72.exr` |
| Printf `%0Nd` | `file_%04d.exr` | `file_0072.exr` |
| Hash padding | `file_####.exr` | `file_0072.exr` |
| Hash padding | `file_######.exr` | `file_000072.exr` |

The function searches the filename stem from the end for these patterns and replaces the last match found.
The stem is determined by the last dot in the filename (matching pathlib's `.stem` property), so
`render.0001.exr` has stem `render.0001` and suffix `.exr`.
This preserves shot numbers or other numeric prefixes (e.g., `shot01_####.exr` replaces only the `####`).
For digit sequences and hash patterns, the output is zero-padded to match the original width.
For printf-style patterns, the format specifier determines the padding.
If the number exceeds the padding width, the full number is used without truncation
(e.g., `file_###.exr` with `with_number(10000)` produces `file_10000.exr`).
If no pattern is found, `_NNNN` (4-digit zero-padded) is appended to the stem.
The maximum padding width is 32 characters; wider printf or hash patterns are an error.

For negative numbers, the sign is included in the output. With digit and hash formats, the sign
precedes the zero-padded digits and counts toward the width (e.g., `file_003.exr` with
`with_number(-1)` produces `file_-01.exr`). With printf formats, standard printf sign handling
applies.

```yaml
# Frame number substitution examples
{{ path("/renders/shot_003.exr").with_number(72) }}       # path("/renders/shot_072.exr")
{{ path("/renders/shot_%04d.exr").with_number(72) }}      # path("/renders/shot_0072.exr")
{{ path("/renders/shot_%d.exr").with_number(72) }}        # path("/renders/shot_72.exr")
{{ path("/renders/shot_####.exr").with_number(72) }}      # path("/renders/shot_0072.exr")
{{ path("/renders/shot_######.exr").with_number(72) }}    # path("/renders/shot_000072.exr")

# Typical usage: construct output path for current frame
{{ Param.OutputPattern.with_number(Task.Param.Frame) }}
```

## Design Choices

### Function Naming Conventions

Built-in functions follow consistent naming conventions:
- Lowercase names matching Python conventions (`upper`, `lower`, `strip`)
- Serialization functions use `repr_` prefix (`repr_sh`, `repr_py`, `repr_json`)
- Path functions match Python's `pathlib` API (`with_suffix`, `with_stem`, `as_posix`)

This consistency makes the library easier to learn and remember.

### PATH Parameter Type Semantics

For job parameters of type `PATH`:
- `RawParam.<name>` returns `string` — the original submitted value, which may use path syntax
  from a different operating system
- `Param.<name>` returns `path` — the value after path mapping has been applied, which is
  valid path syntax for the worker's operating system

This distinction exists because jobs may be submitted from one OS (e.g., Windows) and run on
workers with a different OS (e.g., Linux). The raw value preserves the original syntax for
string manipulation, while the mapped value provides a proper `path` type for path operations.

### Minimal Function Set

The function library is intentionally minimal, covering common use cases. Additional functions
can be proposed in future RFCs as needs are identified.

## Prior Art

### Python pathlib

The path type properties and functions are directly inspired by Python's
[pathlib.PurePath](https://docs.python.org/3/library/pathlib.html#pure-paths). This provides
a well-tested API design for path manipulation. For URI paths, the implementation cannot
delegate to `pathlib` because `PurePath` normalizes consecutive slashes (e.g., `s3://bucket`
becomes `s3:/bucket`) and `PureWindowsPath` converts forward slashes to backslashes. URI path
components such as S3 object keys are opaque identifiers where `a//b` and `a/b` may refer to
different resources, so the implementation uses URI-aware string parsing that preserves the
path portion verbatim.

### Python shlex

The `repr_sh` function follows Python's
[shlex.quote](https://docs.python.org/3/library/shlex.html#shlex.quote) semantics for safe
shell escaping.

### Standard Library Math Functions

The math functions (`abs`, `min`, `max`, `floor`, `ceil`, `round`) follow conventions common
across programming languages, making them immediately familiar to users.

## Open Questions

### `with_number` Behavior When No Pattern Is Found

When `with_number` finds no frame number pattern in the filename, it appends `_NNNN` (4-digit
zero-padded) to the stem. This silently modifies the filename in a way the user may not expect.
Would raising an error be safer, requiring the user to ensure their filename contains a
recognized pattern?

## Rejected Ideas

### Format String Functions

A `format` function similar to Python's `str.format` was considered but rejected:
- The expression language already provides string interpolation
- Would duplicate functionality
- Complex format specifications add implementation burden

### Additional Math Functions

Trigonometric functions (`sin`, `cos`, `tan`) and logarithms were considered but rejected:
- Rare use cases in job templates
- Can be computed in task scripts if needed
- Keeps the function library focused

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
