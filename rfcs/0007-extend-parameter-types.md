* Feature Name: Extended Parameter Types
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/112
* Start Date: 2026-02-02
* Specification Version: 2023-09 extension EXPR
* Accepted On: (pending)

## Summary

This RFC extends the job parameter type system with boolean and list types, and makes type names
case-insensitive. These additions enable template authors to express common patterns more naturally
and align type syntax with surrounding YAML/JSON conventions.

## Basic Examples

### Boolean Parameter

```yaml
parameterDefinitions:
  - name: UseGpu
    type: bool
    default: false
steps:
  - name: Render
    script:
      actions:
        onRun:
          command: render
          args:
            - "{{ '--gpu' if Param.UseGpu else null }}"
    hostRequirements:
      amounts:
        - name: amount.worker.gpu
          min: "{{ 1 if Param.UseGpu else null }}"
```

When `UseGpu` is `true`, the step requires at least one GPU and passes the `--gpu` flag.
When `UseGpu` is `false`, the `null` value causes that array element to be omitted entirely,
and the GPU requirement is set to 0.

### List Parameter

```yaml
parameterDefinitions:
  - name: Cameras
    type: list[string]
    default: ["main", "closeup"]
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Camera
          type: string
          range: "{{Param.Cameras}}"
```

### Case-Insensitive Types

```yaml
parameterDefinitions:
  - name: FrameStart
    type: int          # lowercase now valid
  - name: OutputDir
    type: Path         # mixed case now valid
```

## Motivation

The current parameter type system has limitations:

1. **No boolean type** - Users must use `STRING` with `allowedValues: ["true", "false"]` to
   represent boolean values, losing semantic clarity.

2. **No list types** - Providing a dynamic list of items (cameras, render layers, etc.) as a
   job parameter is not possible. Users must hardcode lists in templates.

3. **Case-sensitive type names** - The uppercase-only requirement (`INT`, `STRING`, `PATH`)
   doesn't match conventions in YAML/JSON contexts where lowercase is common.

## Specification

### Case-Insensitive Type Names

Job parameter and task parameter type names become case-insensitive. All type names,
including compound types like `LIST[T]`, are matched without regard to case. For example,
the following are all equivalent:

- `INT`, `Int`, `int`
- `FLOAT`, `Float`, `float`
- `STRING`, `String`, `string`
- `PATH`, `Path`, `path`
- `BOOL`, `Bool`, `bool`
- `RANGE_EXPR`, `Range_Expr`, `range_expr`
- `LIST[STRING]`, `List[String]`, `list[string]`
- `LIST[INT]`, `List[Int]`, `list[int]`
- `LIST[LIST[INT]]`, `List[List[Int]]`, `list[list[int]]`

This allows template authors to match the conventions of their environment.

### New Job Parameter Types

#### `<JobBoolParameterDefinition>`

Defines a job parameter that accepts a boolean value.

```yaml
name: <Identifier>
type: "BOOL"
description: <Description> # @optional
default: <bool> # @optional
userInterface: # @optional
   control: enum("CHECK_BOX", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Accepted values are:
- JSON/YAML boolean literals: `true`, `false`
- Integer or float `1` or `1.0` (true), `0` or `0.0` (false)
- Case-insensitive strings representing true: `"true"`, `"yes"`, `"on"`, `"1"`
- Case-insensitive strings representing false: `"false"`, `"no"`, `"off"`, `"0"`

The value is referenced in format strings as:
- `Param.<name>` - Returns a bool type value

Note: Unlike other parameter types, `BOOL` does not support `allowedValues` because restricting
to only `true` or only `false` does not provide meaningful value.

#### `<JobListStringParameterDefinition>`

Defines a job parameter that accepts a list of string values.

```yaml
name: <Identifier>
type: "LIST[STRING]"
description: <Description> # @optional
default: [ <string>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
item: # @optional
  allowedValues: [ <string>, ... ] # @optional
  minLength: <integer> # @optional
  maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("LINE_EDIT_LIST", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where *minLength*/*maxLength* constrain the number of items in the list, and
*item.allowedValues*, *item.minLength*/*item.maxLength* constrain each string item.

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[string] type value
- `Param.<name>[i]` - Returns the i-th element as string
- `len(Param.<name>)` - Returns the count of elements

#### `<JobListPathParameterDefinition>`

Defines a job parameter that accepts a list of path values.

```yaml
name: <Identifier>
type: "LIST[PATH]"
description: <Description> # @optional
objectType: enum("FILE", "DIRECTORY") # @optional
dataFlow: enum("IN", "OUT", "INOUT", "NONE") # @optional
default: [ <string>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
item: # @optional
  allowedValues: [ <string>, ... ] # @optional
  minLength: <integer> # @optional
  maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("CHOOSE_INPUT_FILE_LIST", "CHOOSE_OUTPUT_FILE_LIST", "CHOOSE_DIRECTORY_LIST", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   fileFilters: [ <JobPathParameterFileFilter>, ... ] # @optional
   fileFilterDefault: <JobPathParameterFileFilter> # @optional
```

Where:

1. *objectType* — The type of object the paths represent; either FILE or DIRECTORY. Default is DIRECTORY.
2. *dataFlow* — Whether the objects the paths represent serve as input, output or both for the Job. Default is NONE.
3. *minLength*/*maxLength* — Constrain the number of paths in the list.
4. *item.allowedValues*, *item.minLength*/*item.maxLength* — Constrain each path string.
5. *userInterface.control* — The user interface control to use. The default depends on *objectType* and *dataFlow*:
   - If *objectType* is FILE and *dataFlow* is "OUT", default is "CHOOSE_OUTPUT_FILE_LIST"
   - If *objectType* is FILE otherwise, default is "CHOOSE_INPUT_FILE_LIST"
   - If *objectType* is DIRECTORY, default is "CHOOSE_DIRECTORY_LIST"
6. *fileFilters* — File filters for the file choice dialog (only for CHOOSE_INPUT_FILE_LIST/CHOOSE_OUTPUT_FILE_LIST).
7. *fileFilterDefault* — Default file filter for the file choice dialog.

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[path] type value with path mapping applied
- `RawParam.<name>` - Returns a list[string] type value without path mapping
- `Param.<name>[i]` - Returns the i-th element as path
- `len(Param.<name>)` - Returns the count of elements

#### `<JobListIntParameterDefinition>`

Defines a job parameter that accepts a list of integer values.

```yaml
name: <Identifier>
type: "LIST[INT]"
description: <Description> # @optional
default: [ <integer>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
item: # @optional
  allowedValues: [ <integer>, ... ] # @optional
  minValue: <integer> # @optional
  maxValue: <integer> # @optional
userInterface: # @optional
   control: enum("SPIN_BOX_LIST", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   singleStepDelta: <positiveint> # @optional
```

Where *minLength*/*maxLength* constrain the number of items in the list, and
*item.allowedValues*, *item.minValue*/*item.maxValue* constrain each integer item.

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[int] type value
- `Param.<name>[i]` - Returns the i-th element as int
- `len(Param.<name>)` - Returns the count of elements

#### `<JobListFloatParameterDefinition>`

Defines a job parameter that accepts a list of floating-point values.

```yaml
name: <Identifier>
type: "LIST[FLOAT]"
description: <Description> # @optional
default: [ <float>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
item: # @optional
  allowedValues: [ <float>, ... ] # @optional
  minValue: <float> # @optional
  maxValue: <float> # @optional
userInterface: # @optional
   control: enum("SPIN_BOX_LIST", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   decimals: <integer> # @optional
   singleStepDelta: <positivefloat> # @optional
```

Where *minLength*/*maxLength* constrain the number of items in the list, and
*item.allowedValues*, *item.minValue*/*item.maxValue* constrain each float item.

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[float] type value
- `Param.<name>[i]` - Returns the i-th element as float
- `len(Param.<name>)` - Returns the count of elements

#### `<JobListBoolParameterDefinition>`

Defines a job parameter that accepts a list of boolean values.

```yaml
name: <Identifier>
type: "LIST[BOOL]"
description: <Description> # @optional
default: [ <bool>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("CHECK_BOX_LIST", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where *minLength*/*maxLength* constrain the number of items in the list.

Each list item accepts the same values as `<JobBoolParameterDefinition>`:
- JSON/YAML boolean literals: `true`, `false`
- Integer or float `1` or `1.0` (true), `0` or `0.0` (false)
- Case-insensitive strings representing true: `"true"`, `"yes"`, `"on"`, `"1"`
- Case-insensitive strings representing false: `"false"`, `"no"`, `"off"`, `"0"`

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[bool] type value
- `Param.<name>[i]` - Returns the i-th element as bool
- `len(Param.<name>)` - Returns the count of elements

#### `<JobRangeExprParameterDefinition>`

Defines a job parameter that accepts a range expression string conforming to the
`<IntRangeExpr>` grammar from the specification. Currently, job templates use string
parameters for frame ranges, but this doesn't clearly represent the parameter's intent.
By defining a specific `RANGE_EXPR` type, tools that parse job templates can understand
that a parameter specifically accepts range expressions, enabling better validation,
UI controls, and documentation.

```yaml
name: <Identifier>
type: "RANGE_EXPR"
description: <Description> # @optional
default: <string> # @optional, must be valid <IntRangeExpr>
minLength: <integer> # @optional
maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("LINE_EDIT", "HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where:

1. *minLength* — Minimum string length of the range expression. Must be >= 1 if provided.
2. *maxLength* — Maximum string length of the range expression. Must be >= minLength if both provided. Default is 1024.
3. *userInterface.control* — The user interface control to use when editing this parameter.
   The default, if not provided, is "LINE_EDIT".
   - "LINE_EDIT" — A single-line text input for entering range expressions.
   - "HIDDEN" — This hides the parameter from the user interface.

The value must conform to the `<IntRangeExpr>` grammar:

```bnf
<IntRangeExpr> ::= <Element> | <Element>,<IntRangeExpr>
<Element>      ::= <WS>*<Int><WS>* | <WS>*<Range><WS>* | <WS>*<SkipRange><WS>*
<Range>        ::= <Int><WS>*-<WS>*<Int>
<SkipRange>    ::= <Range>:<Skip>
```

Examples: `"1-100"`, `"1-100:10"`, `"1,3,5,7"`, `"1-10,20-30:2"`

The value is referenced in format strings as:
- `Param.<name>` - Returns a `range_expr` type value
- `RawParam.<name>` - Returns a `range_expr` type value (identical to `Param.<name>`)
- `list(Param.<name>)` - Returns a `list[int]` with the expanded values

This type is particularly useful for task parameter ranges:

```yaml
parameterDefinitions:
  - name: FrameRange
    type: RANGE_EXPR
    default: "1-100"
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "{{Param.FrameRange}}"
```

#### `<JobListListIntParameterDefinition>`

Defines a job parameter that accepts a nested list of integer values. This enables use cases
like representing graph adjacency lists for task-task dependencies
(see [Discussion #82](https://github.com/OpenJobDescription/openjd-specifications/discussions/82)).
We are not defining a user interface control for this parameter type, as the identified
use case is for programmatically providing the adjacency list.

```yaml
name: <Identifier>
type: "LIST[LIST[INT]]"
description: <Description> # @optional
default: [ [ <integer>, ... ], ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
item: # @optional
  minLength: <integer> # @optional
  maxLength: <integer> # @optional
  item: # @optional
    allowedValues: [ <integer>, ... ] # @optional
    minValue: <integer> # @optional
    maxValue: <integer> # @optional
userInterface: # @optional
   control: enum("HIDDEN")
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where *minLength*/*maxLength* constrain the number of inner lists,
*item.minLength*/*item.maxLength* constrain the size of each inner list, and
*item.item.allowedValues*, *item.item.minValue*/*item.item.maxValue* constrain each integer.

The value is referenced in format strings as:
- `Param.<name>` - Returns a list[list[int]] type value
- `Param.<name>[i]` - Returns the i-th element as list[int]
- `Param.<name>[i][j]` - Returns the j-th element of the i-th list as int
- `len(Param.<name>)` - Returns the count of outer list elements
- `len(Param.<name>[i])` - Returns a count of inner list elements

## Design Choice Rationale

### Case Insensitivity

Making type names case-insensitive reduces friction for template authors who work in
environments where lowercase is conventional. It also aligns better with the surrounding
YAML syntax.

### Nested Item Constraints

List parameter constraints use a nested `item:` structure that mirrors the type nesting.
This allows each level to use the same property names as the corresponding scalar type
(`minLength`/`maxLength` for strings, `minValue`/`maxValue` for numbers), and scales
naturally to nested list types like `LIST[LIST[INT]]`.

### List Type Constraints

List types are limited to prevent excessive complexity:
- `list[T]` where `T` is a scalar type
- `list[list[T]]` for one level of nesting (no deeper)

### Boolean Type

A dedicated boolean type provides clearer semantics than string parameters with allowed
values. It enables proper UI controls (checkboxes) and type-safe expression evaluation.

## Prior Art

### JSON Schema

JSON Schema supports boolean and array types natively. This RFC aligns OpenJD's type system
more closely with JSON's native types.

### Other Workflow Languages

Most workflow languages (WDL, CWL, Nextflow) support boolean and array/list parameter types
as fundamental building blocks.

## Rejected Ideas

### Flat Item Constraint Properties

An earlier design used flat property names with prefixes to distinguish list-level and
item-level constraints:

```yaml
minLength: 1           # list size
maxLength: 10
minItemLength: 1       # item string length (for STRING/PATH)
maxItemLength: 100
minItemValue: 0        # item value (for INT/FLOAT)
maxItemValue: 100
```

For nested types like `LIST[LIST[INT]]`, this required increasingly awkward names like
`minItemIntValue`. The nested `item:` structure was chosen instead because it mirrors
the type nesting, reuses the same property names at each level, and scales cleanly to
any nesting depth.

### Map/Dictionary Types

A `map[K, V]` type was considered but rejected as too complex for initial implementation.
Most use cases can be handled with parallel lists or structured strings.

### Deeply Nested Lists

Supporting `list[list[list[T]]]` or deeper nesting was rejected to keep the type system
tractable and avoid complex validation logic.

## Open Questions

### Optional Parameter Types

Should we extend job parameter types to support optional variants? This would use syntax like
`INT?`, `STRING?`, `FLOAT?`, etc. The specification would accept both `INT` and `INT?` for
`JobIntParameterDef`, with behavior changing based on whether the type is optional:

- Clients could submit `null` as the job parameter value to indicate no value was provided
- Templates could use `Param.Value != null` to check if a value was supplied
- This would enable patterns like `['--quality', Param.Quality] if Param.Quality != null else null`

This would provide a cleaner alternative to using sentinel values (like `0` or `-1`) to indicate
"no value" for numeric parameters.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
