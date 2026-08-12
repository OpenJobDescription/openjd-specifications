* Feature Name: Expression Language
* Author(s): Mark Wiebe <[mwiebe](https://github.com/mwiebe)>
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/112
* Start Date: 2026-01-30
* Specification Version: 2023-09 extension EXPR
* Accepted On: (pending)

## Summary

Open Job Description templates need a flexible way to customize job structure and express glue transformations between
different interfaces. Schedulers must understand job structure without running tasks to determine it, so need
the ability to evaluate it in an isolated, secure, and bounded context. We propose a domain-specific
expression language to provide this flexibility. The language we define has a type system
and set of operations rich enough to cover the diverse use cases identified in community discussions,
with well-defined, bounded expression evaluation semantics.

During implementation of the `path` expression language type, we found it worthwhile to extend
its behavior following the direction proposed in
[discussion #84](https://github.com/OpenJobDescription/openjd-specifications/discussions/84)
and have also extended the parameter type for URI handling.

## Overview

This section provides a high-level orientation to the EXPR extension before diving into
examples and detailed specification.

### What EXPR Adds

The EXPR extension replaces the simple `{{ Param.Name }}` value references in format strings
with a Python-subset expression language supporting arithmetic, conditionals, function calls,
list comprehensions, and path manipulation. It is activated by adding `EXPR` to the template's
`extensions` list. All existing templates continue to work unchanged.

### Key Concepts

**Expression types** — Values in expressions have types like job and task parameters.
The expression type system is richer, including type unions, an optional type, and more.

**Variables** — Expressions can access values provided by the template using their names.
For example `Param.FrameRate` is the value of a job parameter called `FrameRate` and
`Job.Name` is the job's name

**Functions and operators** — A fixed library of operations including arithmetic (`+`, `-`,
`*`, `/`), comparison (`==`, `<`, `in`), string methods (`.upper()`, `.split()`, `.join()`),
path operations (`.name`, `.parent`, `/`, `.with_suffix()`), and utility functions (`len()`,
`min()`, `max()`, `repr_sh()`, `path()`). There are no user-defined functions.

### How Expressions Are Processed

Expressions appear inside `{{ }}` in format strings and in `let` bindings. Processing follows
these steps:

```
Template format string: "render --frames {{Param.Start}}-{{Param.Start + Param.Count - 1}}"
                                         ├─────────────┘ ├─────────────────────────────────┘
                                         expression 1     expression 2

  ┌──────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐
  │  Parse   │────>│   AST   │────>│ Evaluate │────>│ Result │
  │ (Python  │     │  (tree  │     │ (walk    │     │ (typed │
  │  syntax  │     │   of    │     │  tree w/ │     │  value │
  │  subset) │     │  nodes) │     │  symbol  │     │  e.g.  │
  │          │     │         │     │  table)  │     │  42)   │
  └──────────┘     └─────────┘     └──────────┘     └────────┘
```

1. **Parse** — The expression text is parsed using a standard Python parser (e.g., Python's
   `ast` module, Rust's ruff parser, or JS's dt-python-parser). Only a subset of the
   Python AST is accepted to support its role as glue between interfaces.

2. **AST** — The parser produces an abstract syntax tree. For example, `Param.Start + 1`
   becomes an `Add` node with an `Attribute` node and a `Constant` node as children.

3. **Evaluate** — The evaluator walks the AST, looking up symbols in a symbol table and
   dispatching operations to a function library. Each value carries its type, enabling
   type checking and implicit coercion (e.g., `int` → `float`). The evaluation rules are
   not a subset of Python semantics, but are intended to be simple and familiar.

4. **Result** — A typed value that is converted to a string for insertion into the format
   string, or used directly in `let` bindings and parameter space definitions.

### Evaluation Stages

Not all values are known at the same time. When values are not yet known, the evaluator
uses a token value with type `unresolved[T]`, where `T` represents what we know about
the type of the value. E.g. that it's an `int`, or a union `float | int | nulltype`.
This design let's it use one code path for both type checking and evaluation.

There are three stages of template processing, with fewer unresolved values as we go:

```
  Template          Job Creation         Task Execution
  Validation        (submit time)        (worker host)
  ─────────────     ─────────────        ──────────────
  Param.*:          Param.*:             Param.*:
    unresolved[T]     CONCRETE             CONCRETE
  Task.Param.*:     Task.Param.*:        Task.Param.*:
    unresolved[T]     unresolved[T]        CONCRETE
  Session.*:        Session.*:           Session.*:
    unresolved[T]     unresolved[T]        CONCRETE

  ► Type-check      ► Evaluate           ► Evaluate
    all exprs         TEMPLATE scope       all remaining
                      expressions          expressions
```

## Basic Examples

### Arithmetic Operations

Calculate frame ranges dynamically:

```yaml
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: int
          range: "{{Param.FrameStart}}-{{Param.FrameEnd}}:{{Param.FramesPerTask}}"
    script:
      actions:
        onRun:
          command: render
          args:
            - "--start"
            - "{{Task.Param.Frame}}"
            - "--end"
            - "{{min(Task.Param.Frame + Param.FramesPerTask, Param.FrameEnd) - 1}}"
```

### Conditional Expressions

Select values based on parameters:

```yaml
parameterDefinitions:
  - name: Quality
    type: STRING
    allowedValues: ["draft", "final"]
steps:
  - name: Render
    script:
      actions:
        onRun:
          command: render
          args:
            - "--samples"
            - "{{ 16 if Param.Quality == 'final' else 4 }}"
```

### Slicing

Extract subsets of lists, strings, and paths using Python-style slicing:

```yaml
parameterDefinitions:
  - name: Files
    type: STRING
    default: "file1.exr;file2.exr;file3.exr;file4.exr;file5.exr"
steps:
  - name: Process
    script:
      actions:
        onRun:
          command: process
          args:
            # First three files
            - "{{ Param.Files.split(';')[:3].join(';') }}"
            # Every other file
            - "{{ Param.Files.split(';')[::2].join(';') }}"
            # Last two files
            - "{{ Param.Files.split(';')[-2:].join(';') }}"
```

### Multi-line Expressions

Complex expressions can span multiple lines for readability. This example shows a list
comprehension that generates output file paths for each frame in a chunk:

```yaml
specificationVersion: jobtemplate-2023-09
name: Chunked Frame Processing
extensions: ["FEATURE_BUNDLE_1", "TASK_CHUNKING", "EXPR"]
parameterDefinitions:
  - name: Frames
    type: RANGE_EXPR
    default: "1-10,12,17-19,40-42,50-70,78,90,100"
  - name: OutputDir
    type: PATH
    default: "renders"
  - name: FilePattern
    type: STRING
    default: "frame_####.exr"
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: CHUNK[INT]
          range: "{{Param.Frames}}"
          chunks:
            defaultTaskCount: 10
            rangeConstraint: NONCONTIGUOUS
    bash:
      script: |
        echo "Chunk: {{Task.Param.Frame}} ({{len(Task.Param.Frame)}} frames)"
        echo "Files:"
        for FILE in {{ repr_sh([
            Param.OutputDir / Param.FilePattern.with_number(frame)
            for frame in Task.Param.Frame
        ]) }}; do
          echo "Processing $FILE"
        done
```

## Motivation

The current template substitution syntax is limited to direct value references. This creates
friction for common use cases:

1. **Arithmetic on job parameters** - Users frequently need to provide values to commands derived from
   job parameters in addition to their raw value, for example to determine a range of
   values to process. Currently this requires external scripting or embedding calculations
   in shell scripts.

2. **Conditional logic** - Selecting different values based on parameter settings requires
   workarounds like implementing a wrapper script whose sole purpose is to act as glue between
   the job parameter interface and a command.

3. **Conditional omission of fields/elements** - There is no way to conditionally omit an
   optional field or array element. Users must either pass empty strings (which may not be
   valid for the target command) or maintain multiple template variants.

4. **Inter-dependent job parameter defaults** - The proposal to conditionally show job parameter UI
   elements involves using one parameter value to affect another. In order to do this, the code that
   is controlling the UI must be able to evaluate expressions to perform the show/hide or other potential
   operations. This requires that the expression language be available in all the UI framework languages,
   e.g. in ECMAScript for web UIs as well as in Python and native code for desktop UIs.

These motivations are in community discussions including:
- [Extend types and the template substitution language #79](https://github.com/OpenJobDescription/openjd-specifications/discussions/79)
- [Allowing simple math operations on parameters #49](https://github.com/OpenJobDescription/openjd-specifications/discussions/49)
- [Container support with onWrapTaskRun #83](https://github.com/OpenJobDescription/openjd-specifications/discussions/83)
- [Conditionally show job parameter UI elements #42](https://github.com/OpenJobDescription/openjd-specifications/discussions/42)
- [Task-task dependencies with adjacency graphs #82](https://github.com/OpenJobDescription/openjd-specifications/discussions/82)
- [Include/exclude parts of a template #81](https://github.com/OpenJobDescription/openjd-specifications/discussions/81)

## Technical Requirements

1. **Backward Compatibility** - All existing valid templates must continue to work identically
   with no changes. See [Appendix A: Backward Compatibility Analysis](#appendix-a-backward-compatibility-analysis).

2. **Opt-in Activation** - The extended expression syntax is only enabled when the
   `EXPR` extension is requested in the template. Groundwork for this was laid in
   [openjd-model-for-python#182](https://github.com/OpenJobDescription/openjd-model-for-python/pull/182).

3. **Reuse Existing Parser** - Avoid writing a custom parser from scratch. Use an existing
   language parser and accept a subset of its grammar/AST. This reduces implementation effort
   and leverages well-tested parsing infrastructure.

4. **Deterministic Evaluation** - Expressions must evaluate deterministically with no side
   effects. The same inputs must always produce the same outputs.

5. **Fail-Fast Errors** - Invalid expressions must be rejected at template validation/submission
   time, not at task runtime. This includes syntax errors, undefined symbol references, and type
   errors. See [Static Type Checking](#static-type-checking) about catching type errors early,
   even for expressions that won't be evaluated until task runtime.

6. **No Filesystem, Network, or Environment Variable Access** - Expressions have no access to
   the filesystem, network, or environment variables. The evaluation context is fully defined
   by the template's parameters and runtime context variables. This ensures expressions do not
   depend on any outside state.

7. **Memory-Bounded Evaluation** - Expression evaluation must operate within bounded memory.
   Implementations accept a configurable memory limit and track the memory size of live values
   during evaluation. This prevents unbounded resource consumption from expressions like
   `"a" * 10000000` or large list comprehensions.

8. **Operation-Bounded Evaluation** - Expression evaluation must operate within a bounded
   number of operations. Implementations accept a configurable operation limit and count
   operations during evaluation. Each function call counts as 1 operation, iterating
   through a list (in a list comprehension or within a function implementation) adds the
   number of elements to the count, and processing a string or path value adds the length
   of the value divided by 256 (rounded up) to the count. This prevents unbounded computation
   from deeply nested or combinatorially explosive expressions.

9. **No User-Defined Functions** - All functions, operators, and type properties are defined by
   the specification. There is no mechanism for users to define custom functions or extend the
   language within templates. This ensures templates are portable and evaluation is bounded and
   predictable.

## Design Choices

### 1. Language Syntax: Python Subset with Compatibility Extensions

The expression language uses a **Python expression subset** to satisfy
[Technical Requirement #3](#technical-requirements). Python implementations can use the
[`ast`](https://docs.python.org/3/library/ast.html) standard library module, Rust implementations
can use the [ruff Python parser](https://github.com/astral-sh/ruff/tree/main/crates/ruff_python_parser),
and JavaScript implementations can use
[dt-python-parser](https://github.com/DTStack/dt-python-parser).

Three compatibility extensions are added:

- **Contextual keywords** for backward compatibility - `if`, `else`, `and`, `or`, `not`, `for`,
  `in`, `True`, `False`, `None` are only keywords in operator positions, not after `.` in
  attribute access (e.g., `Param.if` remains valid).

- **JSON/YAML-compatible literals** - Accept `null`, `true`, `false` as aliases for `None`,
  `True`, `False` to reduce friction with the surrounding template syntax.

- **Implicit line continuation** - Multi-line expressions are supported without requiring
  backslash (`\`) continuation or enclosing parentheses. See
  [Appendix D: Implicit Line Continuation](#appendix-d-implicit-line-continuation) for
  implementation details.

See [Appendix B: Language Syntax Choice](#appendix-b-language-syntax-choice) and
[Appendix A: Backward Compatibility Analysis](#appendix-a-backward-compatibility-analysis) for rationale.

### 2. Float Value Pass-Through

When a float value is only copied without modification, the original string representation
is preserved in output string interpolation. When an operation is performed on a float value,
it becomes a 64-bit IEEE floating point number, and string interpolation uses the shortest
decimal string representation. This is an extension of existing float job parameter
handling to the full expression language semantics.

For example, if a job submission provides the value `"3.500"` to a float parameter:
- `{{Param.V}}` outputs `"3.500"` (original form preserved)
- `{{Param.V + 1}}` outputs `"4.5"` (shortest representation after computation)

Note: Float values use 64-bit IEEE 754 representation and are subject to standard floating-point
precision (e.g., `0.1 + 0.2` produces `0.30000000000000004`, not `0.3`). The expression language
does not produce negative zero, infinity, or NaN:

- Negative zero (`-0.0`) is normalized to `0.0` after every operation.
- Operations that would produce infinity (e.g., `1e300 * 1e300`) are errors.
- Operations that would produce NaN (e.g., `0.0 / 0.0`) are errors.
- `float('inf')`, `float('nan')`, and `float('-inf')` are errors.

### 3. 64-bit Signed Integer Type

Integer values use 64-bit two's complement representation, with a range of −2⁶³ (−9223372036854775808)
to 2⁶³−1 (9223372036854775807). Any operation that produces an integer value outside this range
is an error.

This applies to:
- Integer literals (e.g., `9999999999999999999` is an error)
- Arithmetic operations (e.g., `9223372036854775807 + 1` is an error)
- Type conversions (e.g., `int(9.3e18)` is an error if the result exceeds the range)

This choice ensures consistent behavior across all implementation languages. Languages with
arbitrary-precision integers (like Python) must check bounds after every integer operation.
Languages with fixed-width integers (like Rust, C++) must detect overflow and report it as
an error rather than silently wrapping.

### 4. Uniform Function Call Syntax

Functions and properties can be accessed using method syntax:

- For any function `f(x, ...)` where `x` has type `T`, the expression `x.f(...)` is
  equivalent to `f(x, ...)`.
- All operators are defined by functions like `__add__` for the `+` operator, using the
  same double-underscore names as Python does.
- Properties like `x.p` are defined using the naming convention `__property_p__` in RFC 0006.

This enables chaining like `Param.Name.upper().strip()` instead of `strip(upper(Param.Name))`,
and allows properties like `Param.File.stem` to be defined uniformly alongside functions.
Using the uniform function call syntax allows RFC 0006 to define functions, methods, and properties
of all the supported types by specifying a single set of functions in a uniform way.

Note: The `__*__` names are specification conventions and are not directly callable.

**Important:** When calling a function as a method, implicit type coercion does not apply
to the receiver (first parameter). See [Method Call Coercion Restriction](#method-call-coercion-restriction)
for details.

### 5. Minimal Explicit Type Casts

As a glue expression language intended for convenience, implicit non-destructive type
coercion is performed where the intent is obvious. Requiring explicit conversions like
`string(Param.Quality)` when embedding an int in a string context adds noise without
adding clarity. The detailed coercion rules are specified in
[Implicit Type Coercion](#implicit-type-coercion).

### 6. None/null Semantics and List Flattening

When evaluating expressions in templates, the evaluation engine is given a target type:

- For a required field of type `T`, the target type is `T`.
- For an optional field of type `T`, the target type is `T?`.

If an expression evaluates to `None`/`null` for an optional field, the field is omitted
from the output as if it were not specified.

For list items (e.g., in `args`), each item's target type is `T? | list[T]` where `T` is
the item type. This enables three behaviors:

1. If the result is a value of type `T`, it is added as a single item.
2. If the result is `None`/`null`, the item is skipped and the list is one shorter.
3. If the result is a `list[T]`, the list is flattened inline.

This implicit dropping and flattening simplifies constructing command arguments:

```yaml
args:
  - "--input"
  - "{{Param.InputFile}}"
  - "{{ '--verbose' if Param.Verbose else null }}"  # Dropped when false
  - "{{ ['--quality', Param.Quality] if Param.Quality > 0 else null }}"  # Flattened or dropped
```

### 7. Let Bindings for Common Sub-expressions

To avoid repeating complex expressions across multiple fields, `let` bindings can be added
to `StepTemplate` and `ScriptTemplate`. Bindings use Python assignment syntax with optional
type annotations, evaluated in declaration order.

**Step-level bindings** (`let` in `StepTemplate`) are evaluated once per step and available
to `parameterSpace` and `script`:

```yaml
steps:
  - name: ProcessTiles
    let:
      - proto_udim = int(re_search(Param.ProtoTile.stem, r'\.(10\d{2})')[1])
      - max_u = (proto_udim - 1001) % 10
      - max_v = (proto_udim - 1001) // 10
    parameterSpace:
      taskParameterDefinitions:
        - name: TileU
          type: INT
          range: "0-{{ max_u }}"
        - name: TileV
          type: INT
          range: "0-{{ max_v }}"
```

**Task-level bindings** (`let` in `ScriptTemplate`) are evaluated once per task and can
reference `Task.Param`:

```yaml
    script:
      let:
        - udim = 1001 + Task.Param.TileV * 10 + Task.Param.TileU
        - tile_file = Param.ProtoTile.parent / (Param.ProtoTile.stem + '.' + string(udim) + '.tx')
      actions:
        onRun:
          command: process
          args: ["--input", "{{ tile_file }}"]
```

**Environment bindings** (`let` in `EnvironmentScript`) are evaluated once when the environment
is entered and are available in `actions` and `embeddedFiles`:

```yaml
environments:
  - name: Setup
    script:
      let:
        - work_dir = Param.OutputDir / 'work'
      actions:
        onEnter:
          command: mkdir
          args: ["-p", "{{ work_dir }}"]
```

### 8. Differences from Python Expression Semantics

The expression language uses Python syntax but differs from Python semantics in the following ways.
This list is useful for checking design choices and as a checklist for implementations.

**Type system:**

- **64-bit signed integers** — Python integers have arbitrary precision. EXPR integers are 64-bit
  two's complement (−2⁶³ to 2⁶³−1). Operations that overflow are errors, not silent wrapping.
- **No negative zero, infinity, or NaN** — Python floats can be `-0.0`, `inf`, `-inf`, or `nan`.
  EXPR normalizes `-0.0` to `0.0` and treats infinity/NaN-producing operations as errors.
- **Float pass-through** — Python always stores floats as 64-bit IEEE values. EXPR preserves the
  original string representation of float values that are only copied, not computed on.
- **`bool` is not a subtype of `int`** — In Python, `True == 1` and `False == 0`. In EXPR,
  `bool` and `int` are distinct types; `True == 1` is `false` and `True == True` is `true`.
- **`path` type** — EXPR has a `path` type for filesystem paths and URIs (e.g., `s3://bucket/key`).
  Python's `pathlib.Path` does not handle URIs.
- **`range_expr` type** — EXPR has a `range_expr` type for integer range expressions like `"1-10,15"`.
  Python has no equivalent built-in type.
- **No `dict`, `set`, `tuple`, or `complex` types** — EXPR supports only `bool`, `int`, `float`,
  `string`, `path`, `range_expr`, `list[T]`, and `nulltype`.

**Truthiness and logical operators:**

- **No truthy/falsy concept** — In Python, `0`, `""`, `[]`, `None` are all falsy. In EXPR, only
  `false` and `null` are falsy. `0`, `""`, and `[]` are not falsy.
- **`and`/`or` are null-coalescing** — While both Python and EXPR return operand values (not
  necessarily `bool`), the falsy set differs (see above), making `and`/`or` behave as
  null-coalescing operators rather than general truthiness operators.
- **`not` requires `bool`** — In Python, `not` works on any value via truthiness. In EXPR,
  `not` requires a `bool` operand and returns `bool`.
- **`if`/`else` condition requires `bool`** — In Python, any value can be a condition. In EXPR,
  the condition must be a `bool`.

**Operators and functions:**

- **No bitwise operators** — Python supports `&`, `|`, `^`, `~`, `<<`, `>>`. EXPR does not.
- **Multiple dispatch, not single dispatch** — In Python, `a + b` dispatches via `a.__add__(b)`
  (single dispatch on the left operand's class, with `__radd__` fallback). In EXPR, operators
  and functions use multiple dispatch: all argument types are matched simultaneously against a
  table of signatures to select the implementation.
- **Cross-type equality returns `false`, cross-type ordering is an error** — In Python,
  `5 == "5"` is `False` (no error). EXPR also returns `false` for cross-type `==`/`!=`, but
  cross-type ordering (`<`, `>`, `<=`, `>=`) between incompatible types is a type error.
  Exceptions: `int`/`float` and `string`/`path` pairs can be both compared and ordered.

**Syntax restrictions:**

- **No assignment or statements** — Only expressions are allowed; no `=`, `+=`, `import`, `def`, etc.
- **No keyword arguments** — Function calls use positional arguments only; `f(x=1)` is not supported.
- **No f-strings** — Python f-strings (`f"value: {x}"`) are not supported. Use string concatenation
  or format string interpolation instead.
- **No `*args` or `**kwargs`** — Unpacking operators are not supported in function calls.
- **No walrus operator** — Python's `:=` assignment expression is not supported.
- **No `lambda`** — Anonymous functions are not supported.
- **No user-defined functions** — All functions are provided by the specification. There is no
  `def`, `class`, or any mechanism to define custom functions.
- **No nested comprehensions** — Only single `for` clause is allowed in list comprehensions.
- **No `dict`/`set` comprehensions or displays** — Only list literals and list comprehensions.
- **No `await`, `yield`** — Async and generator expressions are not supported.

**Scoping and names:**

- **Contextual keywords** — Python keywords (`if`, `else`, `and`, `or`, `not`, `for`, `in`,
  `True`, `False`, `None`) can be used as attribute names after `.` (e.g., `Param.if`). In
  Python, this is a syntax error.
- **`null`, `true`, `false` aliases** — EXPR accepts JSON-compatible `null`, `true`, `false`
  as aliases for `None`, `True`, `False`. These are not valid Python.
- **User identifiers must be lowercase** — Let binding names and comprehension variables must
  start with a lowercase letter or underscore, to avoid conflicts with spec-defined symbols.

**Evaluation model:**

- **Memory-bounded evaluation** — EXPR enforces a configurable memory limit on live values
  during evaluation. Python has no such limit.
- **Operation-bounded evaluation** — EXPR enforces a configurable operation count limit.
  Python has no such limit.
- **Deterministic, side-effect free** — EXPR expressions cannot access the filesystem, network,
  environment variables, or produce side effects. Python expressions can.
- **Implicit line continuation** — Multi-line EXPR expressions don't need backslash continuation
  or enclosing parentheses. Python requires one or the other.

## Specification

### Extension Name

`EXPR`

### Extended Format String Grammar

The grammar for `<StringInterpExpr>` is extended from:

```bnf
<StringInterpExpr> ::= <ValueReference>
<ValueReference>   ::= <Name>
<Name>             ::= <Name> "." <Identifier> | <Identifier>
```

To:

```bnf
<StringInterpExpr>  ::= <ConditionalExpr>
<ConditionalExpr>   ::= <OrExpr> ("if" <OrExpr> "else" <ConditionalExpr>)?
<OrExpr>            ::= <AndExpr> ("or" <AndExpr>)*
<AndExpr>           ::= <NotExpr> ("and" <NotExpr>)*
<NotExpr>           ::= "not" <NotExpr> | <CompareExpr>
<CompareExpr>       ::= <AddExpr> (("<" | ">" | "<=" | ">=" | "==" | "!=" | "in" | "not" "in") <AddExpr>)*
<AddExpr>           ::= <MulExpr> (("+" | "-") <MulExpr>)*
<MulExpr>           ::= <UnaryExpr> (("*" | "/" | "//" | "%") <UnaryExpr>)*
<UnaryExpr>         ::= ("-" | "+") <UnaryExpr> | <PowerExpr>
<PowerExpr>         ::= <PostfixExpr> ("**" <UnaryExpr>)?
<PostfixExpr>       ::= <PrimaryExpr> (<Subscript> | <Call>)*
<Subscript>         ::= "[" <SliceExpr> "]"
<SliceExpr>         ::= <ConditionalExpr> | <Slice>
<Slice>             ::= <ConditionalExpr>? ":" <ConditionalExpr>? (":" <ConditionalExpr>?)?
<Call>              ::= "(" <ArgList>? ")"
<ArgList>           ::= <ConditionalExpr> ("," <ConditionalExpr>)*
<PrimaryExpr>       ::= <ValueReference> | <Literal> | <ListExpr> | <ListComp> | "(" <ConditionalExpr> ")"
<ValueReference>    ::= <Name>
<Name>              ::= <Name> "." <Identifier> | <Identifier>
<Literal>           ::= <IntLiteral> | <FloatLiteral> | <StringLiteral> | <BoolLiteral> | <NoneLiteral>
<IntLiteral>        ::= <DecimalInt> | <HexInt> | <OctalInt> | <BinaryInt>
<DecimalInt>        ::= [0-9] ("_"? [0-9])*
<HexInt>            ::= "0" ("x" | "X") "_"? [0-9a-fA-F] ("_"? [0-9a-fA-F])*
<OctalInt>          ::= "0" ("o" | "O") "_"? [0-7] ("_"? [0-7])*
<BinaryInt>         ::= "0" ("b" | "B") "_"? [01] ("_"? [01])*
<FloatLiteral>      ::= <PointFloat> | <ExponentFloat>
<PointFloat>        ::= <DecimalInt>? "." [0-9] ("_"? [0-9])* <Exponent>? | <DecimalInt> "." <Exponent>?
<ExponentFloat>     ::= <DecimalInt> <Exponent>
<Exponent>          ::= ("e" | "E") ("+" | "-")? [0-9] ("_"? [0-9])*
<StringLiteral>     ::= <StringPrefix>? (<ShortString> | <LongString>)
<StringPrefix>      ::= "r" | "R"
<ShortString>       ::= "'" <ShortStringChar>* "'" | '"' <ShortStringChar>* '"'
<LongString>        ::= "'''" <LongStringChar>* "'''" | '"""' <LongStringChar>* '"""'
<ShortStringChar>   ::= <StringEscape> | any character except "\" or newline or the quote
<LongStringChar>    ::= <StringEscape> | any character except "\"
<StringEscape>      ::= "\" any character
<BoolLiteral>       ::= "True" | "False"
<NoneLiteral>       ::= "None"
<ListExpr>          ::= "[" (<ConditionalExpr> ("," <ConditionalExpr>)* ","?)? "]"
<ListComp>          ::= "[" <ConditionalExpr> "for" <Identifier> "in" <ConditionalExpr> ("if" <ConditionalExpr>)? "]"
```

Note: Keywords (`if`, `else`, `and`, `or`, `not`, `for`, `in`, `True`, `False`, `None`) are contextual.
They are only recognized as keywords in their syntactic positions, not as attribute names
following `.` in a `<Name>`.

Note: Chained comparisons are supported. The expression `1 < 2 < 3` is equivalent
to `1 < 2 and 2 < 3`, with each intermediate value evaluated only once.

#### String Literal Formats

The grammar supports Python's string literal formats:

| Format | Example | Description |
|--------|---------|-------------|
| Single-quoted | `'hello'` | String with single quotes |
| Double-quoted | `"hello"` | String with double quotes |
| Triple single-quoted | `'''hello'''` | Multi-line string with single quotes |
| Triple double-quoted | `"""hello"""` | Multi-line string with double quotes |
| Raw single-quoted | `r'hello\n'` | Raw string (backslashes are literal) |
| Raw double-quoted | `r"hello\n"` | Raw string (backslashes are literal) |
| Raw triple-quoted | `r'''hello'''` or `r"""hello"""` | Raw multi-line string |

All Python escape sequences are supported in non-raw strings:

| Escape | Meaning |
|--------|---------|
| `\\` | Backslash |
| `\'` | Single quote |
| `\"` | Double quote |
| `\n` | Newline |
| `\r` | Carriage return |
| `\t` | Tab |
| `\xhh` | Character with hex value hh |
| `\uhhhh` | Unicode character with 16-bit hex value |
| `\Uhhhhhhhh` | Unicode character with 32-bit hex value |
| `\N{name}` | Unicode character by name |

In raw strings (prefixed with `r` or `R`), backslashes are treated as literal characters
and escape sequences are not processed. This is useful for regular expressions and
Windows-style paths.

#### Numeric Literal Formats

The grammar supports Python's numeric literal formats for convenience:

| Format | Example | Value | Description |
|--------|---------|-------|-------------|
| Decimal | `42` | 42 | Standard decimal integer |
| Hexadecimal | `0x2A` or `0X2a` | 42 | Base-16 with `0x` prefix |
| Octal | `0o52` or `0O52` | 42 | Base-8 with `0o` prefix |
| Binary | `0b101010` or `0B101010` | 42 | Base-2 with `0b` prefix |
| Underscore separator | `1_000_000` | 1000000 | Underscores for readability |
| Decimal float | `3.14` | 3.14 | Standard decimal float |
| Scientific notation | `1.5e-3` or `1.5E-3` | 0.0015 | Exponential notation |
| Integer exponent | `1e10` | 10000000000.0 | Integer with exponent (produces float) |

Underscores can appear between digits in any numeric literal for readability (e.g., `0xFF_FF`,
`0b1010_1010`, `1_000.000_001`). They cannot appear at the start or end of a number, or
adjacent to the decimal point or exponent marker.

Leading zeros on decimal integers are not permitted (e.g., `007` or `0123` are syntax errors).
This prevents confusion with C-style octal notation. Use the `0o` prefix for octal integers
(e.g., `0o7` or `0o123`). The literal `0` and `00` are valid as they unambiguously represent zero.

### Schema Changes for Multi-line Expressions

To support multi-line expressions in format strings, the character constraints for certain
string types must be relaxed to allow line feed (LF, U+000A), carriage return (CR, U+000D),
and horizontal tab (TAB, U+0009) characters.

The base specification defines string constraints that exclude all Unicode Cc (control)
characters (U+0000-U+001F and U+007F-U+009F). When the EXPR extension is enabled, the
following types are amended to allow CR, LF, and TAB:

| Type | Change |
|------|--------|
| `ArgString` | Allow CR (U+000D), LF (U+000A), and TAB (U+0009) |

This change allows format strings in `args` lists to contain multi-line expressions using
YAML literal block scalars (`|` or `|-`):

```yaml
args:
  - |
    {{ [
        Param.OutputDir / Param.FilePattern.with_number(frame)
        for frame in Task.Param.Frame
    ] }}
```

Other string types (e.g., `CommandString`, `JobName`) retain their original constraints
as multi-line values are not typically needed in those contexts.

### Expression Evaluation Types

Expressions are evaluated with a target type determined by context:

- For a required field of type `T`, the target type is `T`.
- For an optional field of type `T`, the target type is `T?`. If the expression evaluates
  to `None`/`null`, the field is omitted.
- Within a format string like `"The {{<expr>}} value."`, the target type is `string?`.
  A `None`/`null` result is treated as the empty string.
- For list items (e.g., in `args`), the target type is `T? | list[T]`. A `None`/`null`
  result skips the item; a `list[T]` result is flattened inline.

#### Format String Coercion to String

When an expression within a format string (e.g., `"prefix {{<expr>}} suffix"`) evaluates to
a non-string type, the format string processor applies the following logic:

1. First, attempt to evaluate the expression with `string` as the target type. If the
   expression can produce a string directly (e.g., string literals, string parameters,
   or expressions that naturally return strings), this succeeds.

2. If step 1 fails due to a type mismatch (e.g., the expression returns `list[int]`),
   evaluate the expression without type constraints to get its natural result type,
   then convert that result to a string using the `string()` function.

This allows any expression result to be embedded in a format string. For example:
- `"Items: {{ [1, 2, 3] }}"` produces `"Items: [1, 2, 3]"`
- `"Frames: {{ list(Param.RangeExpr) }}"` produces `"Frames: [1, 2, 3, 4, 5]"`
- `"Count: {{ len(myList) }}"` produces `"Count: 5"`

| Type | Description |
|------|-------------|
| `bool` | Boolean values (`True`, `true`, `False`, or `false`) |
| `int` | 64-bit signed integer values (−2⁶³ to 2⁶³−1) |
| `float` | Floating-point values |
| `string` | String values (name matches the job parameter type, not Python `str`) |
| `path` | Filesystem path values |
| `range_expr` | Range expression string conforming to `<IntRangeExpr>` grammar |
| `T?` | The type is `T`, but can also be `None`/`null` |
| `nulltype` | The type is like Python `NoneType`, its value can only be `None`/`null` |
| `list[T]` | Ordered list of values of type `T` (see below for constraints on `T`) |
| `list[nulltype]` | Empty list of values `[]`, where we don't know what `T` should be. |
| `T1 \| T2` | The type may be either `T1` or `T2` |
| `noreturn` | Bottom type for functions that never return a value (e.g., `fail()`). In unions, collapses to nothing: `T \| noreturn` simplifies to `T`. |
| `unresolved[T]` | Value not yet resolved, but satisfies constraint `T` (type-checking only) |

The `T` type for a `list[T]` must satisfy:

1. `T1` cannot be `T2?`. A `None`/`null` value inside a list literal is an error.
2. `T1` can be `list[T2]`, but cannot be nested a third time, so `T2` cannot be `list[T3]`.

### Implicit Type Coercion

Implicit non-destructive type coercion is performed where the intent is obvious. The caller
provides the target type it expects, which need not be a single concrete type: it may be
`any`, a union such as `string?` or `string? | list[string]`, or a list whose element type
is either of those. Coercion asks two questions about the expression result, in this order.

**1. Satisfaction.** Does the result's type already satisfy the target? If so, the value is
used unchanged and no conversion is attempted. A type satisfies a target when:

- the target is `any`, which every type satisfies;
- the target is a union and *any* one of its members is satisfied, so an `int` satisfies
  `int | string` and a `null` satisfies `T?`;
- both are lists and the result's element type satisfies the target's element type, so a
  `list[int]` satisfies `list[any]` and `list[int | string]`;
- or the two types are equal.

A result's type is never itself a union: concrete values have a single runtime type, and
for the not-yet-known values checked during validation, a union constraint is decomposed
into its members before these steps apply (see
[Coercion of Unresolved Values](#coercion-of-unresolved-values)).

Satisfaction is directional: `int` satisfies `any`, but `any` does not satisfy `int`. It is
therefore not the same relation as the symmetric matching used to bind type variables during
signature matching, and an implementation must not use one for the other — the symmetric
relation would accept a `list[T1]` target by binding `T1` and discarding the binding.

Because satisfaction is checked first, a result whose type the target already admits is
never converted: an `int` against `int | string` stays an `int` rather than becoming a
string. Consequently, a conversion is only ever attempted toward a type the result does
not already have.

**2. Conversion.** Otherwise the result is converted toward one of the target's
*destinations*. A destination is a single non-union type toward which one of the
conversions below can be attempted. A non-union target is its own only destination. A union
target contributes each of its members, because producing any one of them satisfies the
union. Destinations are attempted in order and the first that converts gives the result; a
destination that fails is not an error so long as a later one succeeds, and the coercion
fails only if none converts.

Destinations are attempted in a fixed order with two levels. **Non-list destinations come
before list destinations**: converting to a scalar produces a single value whose cost does
not depend on the source, while converting to a list materializes its elements and may
exceed an implementation's size limits, so this ordering keeps the outcome independent of
how large the value is. Within each of the two groups, the order is determined by the
result's type, following two principles: a value prefers to stay within its own kind — a
number remains a number before it becomes text — and a conversion that can fail is
attempted before one that always succeeds, because a universal fallback attempted first
would make every destination after it unreachable.

| Result type | Destinations, in order | Notes |
|-------------|------------------------|-------|
| `bool` | `string` | only conversion |
| `int` | `float`, then `string` | stays a number first; text is the universal fallback |
| `float` | `int`, then `string` | `int` succeeds only for exact whole values, so `3.0` against `int \| string` gives `3` while `3.5` gives `"3.5"` |
| `string` | `int`, then `float`, then `bool`, then `range_expr`, then `path` | every string that parses as `int` also parses as `float`, so `int` must come first; `bool` and `range_expr` are selective parses, tried after the numeric ones; every string is a valid `path`, so `path` comes last |
| `path` | `string` | only conversion |
| `range_expr` | `string`, then `list[int]` | the non-list-first rule; when a target offers both, the `list[int]` destination is unreachable, and a template that wants the list uses the explicit `list()` conversion (RFC 0006) |
| `list[S]` | list destinations in `S`'s order, applied to their element types | `list[float]` against `list[int] \| list[string]` attempts `list[int]` first |

So `5` against `float | string` becomes `5.0`, and `"5"` against `int | float` becomes `5`
while `"5.0"` becomes `5.0` — the stricter parse is attempted first, and the string's own
lexical form routes it. An empty list (`list[nulltype]`) converts to every list type and
the result is the empty list regardless; the nominal element type it carries follows the
first list destination in the union's normalized member order.

`nulltype` is never a destination, because no conversion produces `null`. A `null` result
reaches a `T?` target by satisfying it, and a `nulltype` member is otherwise ignored when
converting; in particular, a `string` whose text happens to be `"null"` does not become
`null`. Likewise a type variable, `noreturn`, `unresolved[T]`, or a `list` parameterized by
any of those contributes no destination, so a target composed only of such types cannot be
coerced to at all.

Because destinations are considered one at a time, a union target accepts at least
everything each of its members accepts on its own. Adding an alternative to a target never
takes away a conversion that was previously accepted, though it can change which
destination is chosen, and with it the resulting value.

The non-destructive conversions are:

- `bool`/`int`/`float`/`path`/`range_expr` → `string` (a `range_expr` produces its canonical
  form, like `"1-5"`)
- `string` → `path`
- `float`/`string` → `int` (error if the value cannot be represented exactly, e.g. `3.75`,
  `""`, `"nothing"`, `"3.1"`)
- `int`/`string` → `float` (error if the string cannot be parsed, e.g. `""`, `"nothing"`)
- `string` → `bool`, accepting the same case-insensitive spellings as the explicit `bool()`
  conversion (RFC 0006): `"true"`/`"yes"`/`"on"`/`"1"` become `true` and
  `"false"`/`"no"`/`"off"`/`"0"` become `false` (error otherwise)
- `string` → `range_expr` (error if the string does not parse as a range expression, e.g.
  `""`, `"1-"`)
- `range_expr` → `list[int]`. This is the only list type a `range_expr` implicitly coerces
  to, so the destination is accepted exactly when a `list[int]` value would satisfy it —
  `list[int]`, `list[any]`, and `list[int | string]` — and rejected for any other element
  type, such as `list[float]` or `list[string]`. Implicit rules do not chain, so the
  materialized `list[int]` is not further widened element-wise toward the destination.
  A template that wants the widened list can chain the explicit conversion
  `list(value: range_expr) -> list[int]` (RFC 0006) — e.g. `list(r)` in a `list[string]`
  context — where the `list[T]` → `list[U]` rule below then applies to the conversion's result.
- `list[T]` → `list[U]` when each element `T` can be coerced to `U` (e.g., `list[path]` → `list[string]`).
  This applies recursively for nested lists.
- `list[nulltype]` → `list[T]` for any `T` (empty list literal is compatible with any list type)

For example, in a format string context where the target type is `string?`, an `int` result
is coerced to `string`: it does not satisfy `string?`, whose destinations are just `string`
once the `nulltype` member is set aside, and `int` → `string` is in the table above.

A **type variable** target (`T`, `T1`, `T2`, `T3`) has no coercion rule, for concrete and
unresolved values alike. Type variables are placeholders in generic function signatures,
resolved to concrete types by signature matching before any value is coerced (see the
Target Type Propagation Rules in [Expression Evaluation](#expression-evaluation)), so reaching coercion with
one still unbound is always an error. Accepting a type-variable target for unresolved values
would let validation pass an expression that can only fail once the value is known.

This holds at any nesting depth: a `list[T1]` target is no more usable than a `T1` target,
since a list cannot be produced without knowing its element type. An implementation must
reject a `list` destination whose element type mentions an unbound type variable, rather
than binding the variable and discarding the binding.

#### Coercion of Unresolved Values

Target-type coercion applies the same two steps to `unresolved[T]` values at the type level:
the payload remains unresolved, but its constraint is narrowed to the coercion result. For
example, `unresolved[int]` against a `string` target becomes `unresolved[string]`, and a
`range_expr` → `list[int]` coercion of an unresolved value yields `unresolved[list[int]]`.

The narrowed constraint is the type the applicable step produces, which is not always the
target. Satisfaction leaves the value alone, so its constraint keeps the source type: an
`unresolved[list[int]]` against a `list[any]` target stays `unresolved[list[int]]` rather than
widening to `unresolved[list[any]]`, matching the concrete `list[int]` value that would be
returned unchanged. Conversion yields the type its own rule produces, so an
`unresolved[range_expr]` against `list[any]` becomes `unresolved[list[int]]`, because
materializing a range only ever produces a `list[int]`.

The narrowed constraint always satisfies the target, and it always describes the concrete
result: the concrete result's type satisfies the narrowed constraint. The type level cannot
see the payload that decides which destination of a union target wins, so conversion narrows
to the union of every destination with a type-level rule, rather than betting on any one of
them — anything narrower would misdescribe some resolved value. Against an `int | string`
target an `unresolved[float]` narrows to `unresolved[int | string]`: a `3.0` payload takes
the `float` → `int` rule while a `3.5` payload fails it and falls through to `string`, and
both outcomes lie within the constraint. For a non-union target exactly one destination
exists, so the constraint is exactly the type evaluation will produce.

When the constraint is a union, coercion is existential: it succeeds if at least one member of
the union can coerce to the target, and the possibilities that cannot are discarded. Coercing
`unresolved[int | string]` to an `int` target yields `unresolved[int]`, and
`unresolved[int | list[int]]` to `int` also yields `unresolved[int]` — the `int` possibility
succeeds even though `list[int]` cannot. Only when no member can coerce does the coercion fail.

Checks that require a concrete payload are deferred until the value resolves. For example,
`unresolved[string]` narrows to `unresolved[int]` against an `int` target, but once resolved,
the string must still parse as an integer. Similarly, any `unresolved[list[S]]` is accepted
against any `list[U]` target, even when `S` has no coercion rule to `U`: the value could
resolve to the empty list, which coerces to every list type, so element compatibility can
only be checked once the payload is known. A source and target with no type-level coercion
rule at all, such as `unresolved[list[int]]` against `int`, is rejected during validation.

The two evaluation paths are deliberately asymmetric, and only in one direction. Type-level
coercion may accept a pair that the concrete value later rejects, because the deciding
information is a payload the placeholder does not carry. It must never reject a pair the
concrete value would accept: doing so fails a template at validation time that would have run
correctly, which no later stage can recover from. Any such case is a defect in the type-level
rules, not a deliberate narrowing — the `range_expr` → `list[int]` and type-variable-target
rules above apply identically on both paths for this reason.

#### Method Call Coercion Restriction

When using uniform function call syntax (UFCS) to call a function as a method, implicit type
coercion does **not** apply to the first parameter (the receiver). This ensures type safety
for method-style calls.

For example, given a function `startswith(string, string) -> bool`:

```yaml
# Function call - coercion applies to all arguments
startswith(path('/foo/bar'), '/foo')  # OK: path coerced to string

# Method call - no coercion on receiver
path('/foo/bar').startswith('/foo')   # ERROR: no startswith(path, string) signature
'/foo/bar'.startswith('/foo')         # OK: receiver is already string
```

This distinction exists because method syntax implies the receiver has a specific type that
supports the method. Allowing implicit coercion would silently convert the receiver to a
different type, potentially masking type errors and producing unexpected behavior.

The restriction only applies to the first parameter. Other parameters in a method call
are still subject to normal implicit coercion rules:

```yaml
# Second parameter can still be coerced
'hello'.replace('l', 'L')  # OK: all args are strings
```

### List Literal Type Inference

List literals infer their element type from context and contents. Since there is no `list[Any]`
type, the evaluation must determine a concrete `list[T]`.

#### With Target Type Context

When the target type set contains exactly one `list[T]` type (excluding `list[nulltype]`), elements
are coerced non-destructively to `T` as described in [Implicit Type Coercion](#implicit-type-coercion). This applies recursively for
nested list literals.

#### Without Target Type Context

When no unambiguous target type is available, the element type is inferred from the values:

1. **Homogeneous elements**: If all elements have the same type `T`, the result is `list[T]`.

2. **int/float mix**: If elements are a mix of `int` and `float`, the result is `list[float]`.
   Integer values are promoted to float.

3. **path/string mix**: If elements are a mix of `path` and `string`, the result is `list[string]`.
   Path values are converted to their string representation.

4. **Nested list int/float mix**: If elements are `list[int]` and `list[float]`, the result
   is `list[list[float]]`.

5. **Nested list path/string mix**: If elements are `list[path]` and `list[string]`, the result
   is `list[list[string]]`.

6. **Empty list**: The empty list `[]` evaluates to `list[nulltype]`, which is implicitly convertible
   to `list[T]` for any `T`.

7. **Incompatible types**: If elements have incompatible types (e.g., `int` and `string`,
   `bool` and `int`, scalar and `list`), evaluation fails with an error listing the
   conflicting types.

#### Null Values in List Literals

A `null`/`None` value cannot be an element of a list literal. Including `null` in a list
is always an error:

```yaml
# Error: null cannot be an element of a list literal
args: "{{ [1, null, 2] }}"
```

This restriction exists because:
- Lists have a concrete element type `T`, not `T?`
- The intent of `null` in a list is ambiguous (skip the element? include a null value?)
- Use conditional expressions or list comprehensions to conditionally include elements

## Expression Parsing and Symbol Collection

Implementations must provide two operations on expressions:

1. **Parse and collect symbols** - Parse an expression and return the set of external symbols
   it references, without evaluating it.
2. **Evaluate** - Parse and evaluate an expression given a symbol table.

### Motivation for Symbol Collection

Symbol collection enables static analysis of data flow through job templates. By knowing which
symbols each expression references, schedulers and tools can:

- **Validate references** - Verify that all referenced variables exist at submission time, before
  any tasks run.
- **Type check expressions** - When symbol types are known, verify that operations are valid for
  those types. See [Static Type Checking](#static-type-checking).
- **Analyze data dependencies** - Track how values flow between parameters, environments, steps,
  and other template blocks. This enables understanding which outputs from one step become inputs
  to another.
- **Optimize data transfer** - When tasks run on different hosts, determine which computed values
  must be transferred between hosts based on expression dependencies.
- **Enable incremental updates** - When a parameter changes, identify which expressions and
  downstream computations are affected, enabling selective re-evaluation rather than full
  recomputation.
- **Support visualization** - Build dependency graphs showing how data flows through a job,
  helping users understand and debug complex templates.

### Symbol Collection

When parsing an expression, implementations collect all external symbol references. This enables
validation that referenced variables exist before evaluation. The collected symbols:

- Include variable references like `Param.InputFile` or `Task.Param.Frame`
- Include property access chains like `Param.InputFile.stem` or `Param.File.parent.name`
- Exclude method names from calls (e.g., `Param.Name.upper()` collects `Param.Name`, not `Param.Name.upper`)
- Exclude loop variables defined in list comprehensions (e.g., `[x for x in Param.Items]` collects
  `Param.Items`, not `x`)
- Exclude built-in function names like `min`, `max`, `len`

**Examples:**

| Expression | Collected Symbols |
|------------|-------------------|
| `Param.InputFile` | `{Param.InputFile}` |
| `Param.Start + Param.End` | `{Param.Start, Param.End}` |
| `Param.File.stem.upper()` | `{Param.File.stem}` |
| `Param.File.parent.parent.name` | `{Param.File.parent.parent.name}` |
| `[x * 2 for x in Param.Values]` | `{Param.Values}` |
| `[x for x in Param.Items if x > Param.Min]` | `{Param.Items, Param.Min}` |
| `min(Param.A, Param.B)` | `{Param.A, Param.B}` |

### Function Call Collection

When parsing an expression, implementations also collect all function and method calls. This enables
static analysis to determine which operations are performed, particularly for identifying whether
path mapping functions like `apply_path_mapping()` are called.

The collected calls include:

- Function calls like `min(x, y)` → `min`
- Method calls like `s.upper()` → `upper`
- Chained method calls like `s.split(',').join(';')` → `{split, join}`

**Examples:**

| Expression | Collected Calls |
|------------|-----------------|
| `Param.A + Param.B` | `{}` |
| `min(Param.A, Param.B)` | `{min}` |
| `Param.Name.upper()` | `{upper}` |
| `Param.File.stem.replace('a', 'b')` | `{replace}` |
| `RawParam.File.apply_path_mapping()` | `{apply_path_mapping}` |
| `Param.Items.split(',').join(';')` | `{split, join}` |
| `[str(x) for x in Param.Values]` | `{str}` |

### Validation with Symbol Collection

Template processors use symbol collection to validate expressions at submission time. For each
collected symbol, the validator checks if the symbol or any prefix of it exists in the available
symbol table. This allows property access like `Param.File.stem` to validate successfully when
`Param.File` is defined, even though `Param.File.stem` itself is not a defined variable.

### Static Type Checking

Beyond validating that symbols exist, implementations perform static type checking on expressions
at template validation time. Note that the type system is dynamic, but we can catch many
type errors early—before any tasks run—providing faster feedback and clearer error messages
that point to the exact location of the problem.

**Benefits of Early Type Checking:**

- **Fail-fast validation** - Type errors are caught at submission time, not when a task fails
  hours into a job. This satisfies the "Fail-Fast Errors" technical requirement.
- **Precise error locations** - Error messages include caret pointers showing exactly where the
  type mismatch occurs within the expression.
- **Complete coverage** - All expressions are type-checked, including those in host-context
  scopes that are not evaluated until task runtime.

**Type Checking via Evaluation with Unknown Values:**

Static type checking is performed by evaluating expressions with `unresolved[T]` values in the
symbol table for symbols whose concrete values are not yet available. This unifies type
checking and evaluation into a single mechanism.

For example, when type-checking a host-context expression at submission time:

1. The validator knows the types of all symbols from their declarations (e.g., a `PATH` parameter
   has type `path`, a task parameter with `type: INT` has type `int`).
2. For each symbol, the validator places an `unresolved[T]` value in the symbol table, where `T`
   is the declared type (e.g., `ExprValue.unresolved(ExprType.INT)` for an `INT` parameter).
3. The expression is evaluated normally. Operations on unresolved values propagate the `unresolved`
   type through the expression — if any operand is unresolved, the result is unresolved.
4. If the evaluation succeeds, the result is an `unresolved[T]` value where `T` is the inferred
   result type. If it fails, a type error is reported at submission time.

The `T` in the resulting `unresolved[T]` serves as the inferred result type of the expression,
replacing the need for a separate type inference pass. This approach is effective because the
expression language is side-effect free — evaluating an expression with placeholder values
cannot cause any observable changes, so it is always safe to evaluate for type checking alone.
Because parts of expressions that involve only concrete values are fully evaluated even when
other parts are unresolved, this catches many errors during template validation — before parameter
values are even selected — satisfying the [Fail-Fast Errors](#technical-requirements) requirement.

**Conditional Expressions with Unknown Conditions:**

When the condition of an `if`/`else` expression evaluates to `unresolved[bool]`, the evaluator
does not know which branch will be taken at runtime. Both branches are evaluated:

- If both branches succeed, the result is `unresolved[T | S]` where `T` and `S` are the result
  types of the two branches (since either could be the runtime result).
- If one branch succeeds and the other fails, the result is the type from the succeeding
  branch (wrapped in `unresolved` since the condition is unresolved). The failing branch's error
  is suppressed — that branch would always fail at runtime, so it can never produce a value.
- If both branches fail, evaluation fails with an error describing both failures.

**Example:**

```yaml
parameterDefinitions:
  - name: Count
    type: INT
steps:
  - name: Process
    script:
      actions:
        onRun:
          command: echo
          args:
            - "{{ Param.Count.upper() }}"  # Type error: 'upper' is a string method, not int
```

This expression references `Param.Count` which has type `int`. The validator evaluates the
expression with `Param.Count = unresolved[int]`. The method `upper()` is only defined for
strings, so evaluation fails with a type error at submission time:

```
Method 'upper' not found
  Param.Count.upper()
  ~~~~~~~~~~~~^~~~~
```

**Host-Context Function Availability:**

Certain functions are only available in host-context scopes (SESSION and TASK) where they can
access runtime resources. For example, `apply_path_mapping()` requires access to the session's
path mapping rules, which are not available at submission time.

The type checker uses the appropriate function library based on the expression's scope:
- **Submission context (TEMPLATE scope)**: Default function library
- **Host context (SESSION/TASK scope)**: Extended library including `apply_path_mapping()`

This allows the type checker to correctly validate that `apply_path_mapping()` is only used
in contexts where it will be available at runtime.

### Progressive Expression Evaluation

Expressions are checked and evaluated progressively as more information becomes available.
At each stage, known values are evaluated concretely while unresolved values propagate as
`unresolved[T]`, catching as many errors as possible with the information available:

1. **Template parse time** (e.g., `openjd check`). Job parameters (`Param.*`) are `unresolved[T]`
   based on their declared types, because the template is not yet bound to particular parameter
   values. Task parameters (`Task.Param.*`) and session symbols (`Session.*`) are also unresolved.
   Let bindings that depend only on literals may evaluate concretely. Catches syntax errors,
   type errors in constant subexpressions, and structural issues like undefined symbols.

2. **Job parameter binding** ("submit time"). Job parameter values are now known, so `Param.*`
   symbols are concrete. Expressions in TEMPLATE scope can be fully evaluated. Expressions in
   host-context scopes (SESSION/TASK) still have `Task.Param.*`, `Session.*`, `Task.File.*`,
   and `Env.File.*` as unresolved, but can now type-check operations on the known `Param.*`
   values combined with the unresolved task/session symbols.

3. **Worker host execution**. All symbols are known — `Task.Param.*`, `Session.*`, file paths,
   and path mapping rules are all concrete. Every expression is fully evaluated with no
   unknowns remaining.

At each stage, the same evaluator is used. The only difference is which symbols in the symbol
table are concrete values vs `unresolved[T]` placeholders. This means there is no separate type
checking pass — type checking is a natural consequence of evaluation with partial information.

## Built-in Symbols and Types

Expressions have access to symbols provided by the runtime context. This section documents the
types of these symbols when used in expressions.

### Job Parameter Types

Job parameters defined in `parameterDefinitions` are available via `Param.<name>` and
`RawParam.<name>`. The lower-case form of the job parameter type is also the expression type.
For example string, int, float, or path, and with [RFC 7](0007-extend-parameter-types) also
bool, range_expr, and the list types.

For `PATH` parameters, `Param.<name>` has type `path` with path mapping rules applied, while
`RawParam.<name>` has type `string` containing the original unmapped value. The raw value is
a string because it may be a path for a different operating system that cannot be parsed as
a local path. Similarly for `LIST[PATH]`, `Param.<name>` is `list[path]` while `RawParam.<name>`
is `list[string]`.

PATH parameter values may be URIs (e.g. `s3://bucket/key`). URI values are not subject to
relative path resolution during job parameter preprocessing — they pass through unchanged.
If no path mapping rule matches a URI, `Param.<name>` retains the original URI as a `path`
value with URI-aware semantics.

### Task Parameter Types

Task parameters defined in `taskParameterDefinitions` are available via `Task.Param.<name>`
and `Task.RawParam.<name>`. The lower-case form of the job parameter type is also the expression type,
except for `CHUNK[INT]` which  produces a `range_expr` type, not `list[int]`, enabling efficient
representation of frame ranges. Use `list(Task.Param.Frame)` to convert to a list if needed.

### Session Symbols

Session-scoped symbols are available within Environment and Step Script contexts:

| Symbol | Type | Description |
|--------|------|-------------|
| `Job.Name` | `string` | The resolved job name |
| `Step.Name` | `string` | The name of the current step |
| `Session.WorkingDirectory` | `path` | The session's temporary working directory |
| `Session.PathMappingRulesFile` | `path` | Path to the JSON file containing path mapping rules |
| `Session.HasPathMappingRules` | `bool` | Whether path mapping rules are available |

### Embedded File Symbols

Embedded files are available as paths to their written locations:

| Symbol | Type | Description |
|--------|------|-------------|
| `Task.File.<name>` | `path` | Location of the embedded file within a Step Script |
| `Env.File.<name>` | `path` | Location of the embedded file within an Environment |

### Type Implications for Path Operations

Since `Session.WorkingDirectory`, `Task.File.<name>`, and `Env.File.<name>` are `path` typed,
they support path operations:

```yaml
# Path concatenation with /
mkdir -p {{repr_sh(Session.WorkingDirectory / 'output')}}

# Path properties
echo "Script: {{Task.File.Run.name}}"
```

## Expression Evaluation Algorithm

### Memory-Bounded Evaluation

Expression evaluation must operate within bounded memory to support constrained execution
environments and predictable resource usage when evaluating many expressions concurrently
across threads.

Implementations accept an optional `memory_limit` parameter (default: 100 million bytes recommended).
During evaluation, the evaluator tracks the memory size of live values—incrementing when
values are created, decrementing when intermediate values are consumed by operations.
If current memory exceeds the limit at any point, evaluation fails with an error.

**Value Size Calculation:**

The size of a value is implementation-defined. Implementations should try to match the
actual memory usage of each value as closely as practical in their language and runtime.

**Memory Tracking During Evaluation:**

When evaluating a binary operation like `left + right`:
1. Evaluate `left` → add `size(left)` to current memory
2. Evaluate `right` → add `size(right)` to current memory
3. Compute `result`
4. Release `left` and `right` → subtract their sizes
5. Add `size(result)` to current memory
6. Check if current memory exceeds limit

This models actual memory pressure—what is live at any moment—rather than cumulative
allocations. The limit reflects real resource usage during evaluation.

**Example:**

For `"a" * 10000000`, the result string would be ~10MB. With a 100 million byte limit, this succeeds,
but `"a" * 200000000` (~200MB) would fail at step 5 when the result size is added.

For `[x for x in range(10000000)]`, the list grows element by element. The limit is
checked as each element is added, failing once the accumulated list size exceeds it.

### Operation-Bounded Evaluation

Expression evaluation must operate within a bounded number of operations to prevent
unbounded computation from deeply nested or combinatorially explosive expressions.

Implementations accept an optional `operation_limit` parameter (default: 10 million
recommended). During evaluation, the evaluator maintains a running operation count.
If the count exceeds the limit at any point, evaluation fails with an error.

**Operation Counting Rules:**

1. Every function call counts as 1 operation. This includes operators (which are
   transformed to function calls), property accesses, and explicit function calls.

2. When a function or the evaluator iterates through every element of a list, the
   number of elements is added to the operation count. This applies to:
   - List comprehensions: the number of items in the iterable
   - Built-in functions that iterate lists: `sum()`, `min()`, `max()`, `any()`,
     `all()`, `sorted()`, `reversed()`, `flatten()`, `join()`, `contains()`,
     `range()`, `repr_sh()`, `repr_py()`, `repr_json()`, `repr_pwsh()`,
     `repr_cmd()`, list concatenation (`+`), list repetition (`*`), and
     list/range equality comparisons

3. When a function processes a string or path value, the length of the value
   divided by 256 (rounded up) is added to the operation count. This applies
   to functions that do work roughly proportional to the string length, such as
   `upper()`, `lower()`, `replace()`, `split()`, `join()`, `strip()`, regex
   functions, `repr_sh()`, string concatenation (`+`), string repetition (`*`),
   and similar. Simple lookups like `len()` that do not process the string
   content do not add to the count.

**Example:**

For `sum(range(1000))`:
- `range(1000)` is 1 function call + 1000 iterations = 1001 operations
- `sum(...)` is 1 function call + 1000 iterations = 1001 operations
- Total: 2002 operations

For `[x * 2 for x in range(100)]`:
- `range(100)` is 1 function call + 100 iterations = 101 operations
- The list comprehension adds 100 iterations
- Each `x * 2` is 1 function call
- Total: 301 operations

For `"a" * 100000`:
- `__mul__` is 1 function call + ceil(100000 / 256) = 392 string processing operations
- Total: 393 operations

With the default limit of 10 million, normal template expressions complete easily.
The limit prevents pathological cases like deeply nested comprehensions that would
produce combinatorial explosion.

### Value Data Structure

A value during expression evaluation is a discriminated union holding one value of a specific type.
The type is identified by an integer type code enumeration:

| Type Code | Type | Type Parameter |
|-----------|------|----------------|
| `NULLTYPE` | `nulltype` | - |
| `BOOL` | `bool` | - |
| `INT` | `int` | - |
| `FLOAT` | `float` | - |
| `STRING` | `string` | - |
| `PATH` | `path` | - |
| `RANGE_EXPR` | `range_expr` | - |
| `LIST` | `list[T]` | The element type `T` |
| `ANY` | `any` | - |
| `UNION` | `S \| T` | The member types |
| `NORETURN` | `noreturn` | Bottom type for functions that never return |
| `UNRESOLVED` | `unresolved[T]` | The constraint type `T` |
| `TYPEVAR_T` | `T` | Type variable for polymorphic function signatures |
| `TYPEVAR_T1` | `T1` | Type variable |
| `TYPEVAR_T2` | `T2` | Type variable |
| `TYPEVAR_T3` | `T3` | Type variable |

Type variables `T`, `T1`, `T2`, `T3` are used in function signatures (see RFC 0006) to represent
polymorphic type parameters that are bound at call time. For example, `__getitem__(list: list[T], index: int) -> T`
means the return type matches the list's element type. When a signature uses multiple type
variables (e.g., `T1`, `T2`, `T3`), each may bind to a different concrete type. Type variables
do not appear as the type of a concrete `ExprValue` at runtime — they exist only in
`FunctionSignature` type parameters and are resolved to concrete types during function dispatch.

The `NULLTYPE` type code represents the type of a null value (`nulltype`). Optional types like `T?`
are represented as `UNION` types with `NULLTYPE` as one member (e.g., `int?` = `int | nulltype`).
The `list[nulltype]` type (empty list) uses `NULLTYPE` for the element type parameter.

The `ANY` type code represents an unconstrained type during type checking. It matches any
concrete type and is used when type information is unavailable. In union normalization,
`ANY` absorbs all other types (e.g., `int | any` normalizes to `any`).

The `NORETURN` type code represents the bottom type for functions that never return a value,
such as `fail()`. In union normalization, `NORETURN` collapses to nothing: `int | noreturn`
becomes `int`. This means expressions like `x if cond else fail("error")` have type `x`,
not a union type.

The `UNRESOLVED` type code represents a value whose concrete value is not known, but whose type
satisfies the constraint `T`. For example, `unresolved[int]` means "some value that is an `int`,
but we don't know which one." This is used during static type checking for expressions that
reference symbols whose values are not available until runtime (e.g., task parameters in
host-context expressions). Unlike `ANY`, which is unconstrained, `unresolved[T]` carries type
information: `unresolved[int]` matches `int` but not `string`. The constraint `T` can be any
type including unions (e.g., `unresolved[int | float]`). When the constraint is `any`,
the shorthand `unresolved` is used (i.e., `unresolved` is equivalent to `unresolved[any]`).

**Unknown Type Normalization:**

The `unresolved` type is always the outermost type constructor. When constructing types,
`unresolved` is hoisted outward using the following normalization rules:

- `list[unresolved[T]]` → `unresolved[list[T]]` — A list of unresolved elements is an unresolved list.
- `T | unresolved[S]` → `unresolved[T | S]` — If any branch of a union is unresolved, the whole
  result is unresolved. Non-unresolved members join the constraint.
- `unresolved[T] | unresolved[S]` → `unresolved[T | S]` — Multiple unresolved branches merge their
  constraints.
- `unresolved[unresolved[T]]` → `unresolved[T]` — Nested unknowns flatten.

These rules apply recursively during type construction, ensuring that `unresolved` never appears
inside a `list` or `union` type parameter. The result is a canonical form where `unresolved` is
either absent or wraps the entire type.

The `UNION` type code represents a union of possible types. Unions are normalized:
- Nested unions are flattened: `(int | string) | bool` becomes `int | string | bool`
- Type parameters are sorted alphabetically with `nulltype` at the end
- Duplicate types are removed
- Single-element unions are unwrapped: `int | ` (one element) becomes `int`
- `ANY` absorbs everything: `int | any` becomes `any`
- `NORETURN` collapses to nothing: `int | noreturn` becomes `int`

The `ExprType` structure represents a type:

```
ExprType:
    type_code: TypeCodeEnum
    type_params: list[ExprType]
```

The `ExprValue` structure holds a value. The fields shown are the internal representation;
implementations may expose these through accessor methods rather than direct field access:

```yaml
ExprValue:
    type: ExprType
    is_null: bool
    _bool_value: bool
    _int_value: 64-bit signed integer
    _float_value: 64-bit IEEE floating point
    _string_value: unicode string
    _range_expr_value: IntRangeExpr
    _list_value: list[ExprValue]
```

The `IntRangeExpr` type represents a parsed range expression as a sorted list of integer
ranges. See the [openjd-model IntRangeExpr implementation](https://github.com/OpenJobDescription/openjd-model-for-python/blob/mainline/src/openjd/model/_range_expr.py)
for an example. It must support:
- Parsing from a string, converting to a string
- Iteration over the integer list it represents
- Random-access indexing into the integer list it represents
- Getting its length

Valid states for an `ExprValue` `ev` based on `ev.type.type_code`:

| Type | Type Code | `is_null` | Active Field | `type_params` |
|------|-----------|-----------|--------------|---------------|
| `nulltype` | `NULLTYPE` | `true` | - | `[]` |
| `bool` | `BOOL` | `false` | `_bool_value` | `[]` |
| `int` | `INT` | `false` | `_int_value` | `[]` |
| `float` | `FLOAT` | `false` | `_float_value`, `_string_value` | `[]` |
| `string` | `STRING` | `false` | `_string_value` | `[]` |
| `path` | `PATH` | `false` | `_string_value` | `[]` |
| `range_expr` | `RANGE_EXPR` | `false` | `_range_expr_value` | `[]` |
| `list[T]` | `LIST` | `false` | `_list_value` | `[T]` |

Note: `ANY`, `UNION`, and `UNRESOLVED` are type-level constructs used during type checking. They do not
appear as the type of a concrete `ExprValue` at runtime—values always have a specific
concrete type.

For `FLOAT`, `_float_value` contains the value used for calculations. The `_string_value` is
either empty (ignored) or contains the original representation before conversion to IEEE
64-bit float, implementing the "Float Value Pass-Through" design choice.

### Expression AST

The expression AST uses the same node names as Python's `ast` module, limited to the subset
required by the grammar. Each node type is listed with its fields. This is intended to
support implementation by using a Python AST parser such as [ast.parse](https://docs.python.org/3/library/ast.html#ast.parse)
in Python, the [ruff Python parser](https://github.com/astral-sh/ruff/tree/main/crates/ruff_python_parser) in Rust,
or [dt-python-parser](https://github.com/DTStack/dt-python-parser) in JS.

`Expr` is the union of all expression node types:
`IfExp | BoolOp | UnaryOp | Compare | BinOp | Subscript | Call | Attribute | Name | Constant | List | ListComp`

**Expression Nodes:**

```yaml
IfExp:
    test: Expr
    body: Expr
    orelse: Expr

BoolOp:
    op: BoolOp_Op
    values: list[Expr]

UnaryOp:
    op: UnaryOp_Op
    operand: Expr

Compare:
    left: Expr
    ops: list[Compare_Op]
    comparators: list[Expr]

BinOp:
    left: Expr
    op: BinOp_Op
    right: Expr

Subscript:
    value: Expr
    slice: Expr | Slice  # Single index or slice expression

Slice:
    lower: Expr?  # Start index (None if omitted)
    upper: Expr?  # Stop index (None if omitted)
    step: Expr?   # Step value (None if omitted)

Call:
    func: Expr
    args: list[Expr]  # Python has keywords; we don't support keyword arguments

Attribute:
    value: Expr
    attr: string

Name:
    id: string

Constant:
    value: ExprValue  # Python uses raw Python values; we use ExprValue

List:
    elts: list[Expr]

ListComp:
    elt: Expr
    generator: Comprehension  # Python has list[comprehension]; we allow only one

Comprehension:
    target: string  # Python allows arbitrary patterns; we only allow a single identifier
    iter: Expr
    ifs: list[Expr]  # Python has is_async; we don't support async
```

**Operator Enumerations:**

```
BoolOp_Op: And | Or
UnaryOp_Op: Not | UAdd | USub
Compare_Op: Lt | Gt | LtE | GtE | Eq | NotEq | In | NotIn
BinOp_Op: Add | Sub | Mult | Div | FloorDiv | Mod | Pow
```

### AST Transformation to Uniform Function Calls

Before evaluation, the AST is transformed to convert operators and method calls into uniform
function call syntax. This simplifies the evaluator by reducing all operations to function calls.

**Transformation Rules**

1. **Binary operators** `BinOp(left, op, right)` become `Call(Name("__op__"), [left, right])`
   where `__op__` is the operator name:
   - `Add` → `__add__`, `Sub` → `__sub__`, `Mult` → `__mul__`, `Div` → `__truediv__`
   - `FloorDiv` → `__floordiv__`, `Mod` → `__mod__`, `Pow` → `__pow__`

2. **Unary operators** `UnaryOp(op, operand)` become `Call(Name("__op__"), [operand])`:
   - `UAdd` → `__pos__`, `USub` → `__neg__`, `Not` → `__not__`

3. **Comparison operators** `Compare(left, [op], [right])` become `Call(Name("__op__"), [left, right])`:
   - `Lt` → `__lt__`, `Gt` → `__gt__`, `LtE` → `__le__`, `GtE` → `__ge__`
   - `Eq` → `__eq__`, `NotEq` → `__ne__`
   - `In` → `__contains__`, `NotIn` → `__not_contains__` — note the argument order is
     reversed: `x in y` becomes `__contains__(y, x)` (the container is the first argument).

4. **Subscript** `Subscript(value, index)` where `index` is an `Expr` becomes `Call(Name("__getitem__"), [value, index])`

5. **Subscript with slice** `Subscript(value, Slice(lower, upper, step))` becomes
   `Call(Name("__getitem__"), [value, lower_or_none, upper_or_none, step_or_none])`
   where omitted bounds are passed as `Constant(None)`.

6. **Boolean operators** `BoolOp(op, [a, b, ...])` are handled directly by the evaluator
   (not transformed to function calls) to support value-returning and short-circuit semantics:

   - `a and b`: If `a` is `null` or `false`, return `a`; otherwise evaluate and return `b`.
   - `a or b`: If `a` is `null` or `false`, evaluate and return `b`; otherwise return `a`.

   The `and` and `or` operators are value-returning: they return one of their operands, not
   necessarily a `bool`. Only `null` and `false` are considered falsy — unlike Python, values
   like `0`, `""`, and `[]` are not falsy. This makes `or` useful as a null-coalescing operator
   (e.g., `Param.X or "fallback"`), similar to Ruby's `||`/`&&` operators and null-coalescing
   operators in C# (`??`), JavaScript (`??`), Kotlin (`?:`), and Swift (`??`).

   For chained operators, `a and b and c` evaluates left to right: if `a` is falsy return `a`,
   else if `b` is falsy return `b`, else return `c`. Similarly for `or`.

   Note: `not` remains strictly boolean — it is transformed to `__not__(a)` which requires a
   `bool` operand and returns `bool`.

7. **Method calls** `Call(Attribute(value, method), args)` become `Call(Name(method), [value] + args)`

**Error Message Quality**

When transforming nodes, implementations should preserve the original AST node or relevant
source information (e.g., attribute name, operator symbol, source location) in the transformed
node. This allows error messages to reference the original syntax rather than internal names.
For example, an error about `p.stem` should mention "property 'stem'" rather than
"`__property_stem__`".

### Expression Evaluation

**Overview**

Expression evaluation is a recursive traversal of the AST that propagates type constraints
downward and returns `ExprValue` results upward.

1. Start at the root with a target TypeSet from context (e.g., `{INT}` for a required integer
   field, `{?, STRING, LIST[STRING]}` for a list item in args)
2. For each node, transform the TypeSet appropriately for child nodes
3. Recursively evaluate children
4. At leaf nodes, look up the value (constant or variable from symbol table)
5. When a node has all child `ExprValue` results, evaluate it:
   - If child types are directly compatible, perform the operation
   - Otherwise, compute coercible types for each child and resolve the best match
6. Return the final `ExprValue`

**Target Type Propagation Rules**

Target types guide type inference and coercion, but should not constrain operand evaluation
for operators with fixed signatures. The rules for propagating target types to child nodes:

| Node Type | Target Type Propagation |
|-----------|------------------------|
| `IfExp` | `test`: `{BOOL}`, `body`/`orelse`: inherit parent target types |
| `BoolOp` (`and`/`or`) | Left: `None` (unconstrained), right: `None` (unconstrained). Value-returning; see RFC 0006 Logical Operators. |
| `Compare` | All operands: `None` (unconstrained) |
| `BinOp` | All operands: `None` (unconstrained) |
| `UnaryOp` | Operand: `None` (unconstrained) |
| `Call` (function) | Arguments: computed from candidate signatures' parameter types as written. A parameter type containing a type variable names a family of types (`list[T1]` is any list type), not one to coerce toward, so it leaves its position unconstrained; signature resolution still enforces it. The caller's target filters which signatures contribute; it is never bound through a signature's return type into its parameters. If no signature survives the filter, arguments are evaluated unconstrained (the target-type mismatch then surfaces as a coercion error on the call's result). |
| `Call` (method) | Receiver: `None`, other args: `None` (unconstrained) |
| `Subscript` | Value: `None`, index/slice: `{INT}` or `{INT?}` |
| `List` | Elements: element type extracted from parent target types |
| `ListComp` | Element expr: element type from parent, iter: `None`, conditions: `{BOOL}` |
| `Attribute`/`Name` | Not propagated (leaf nodes return their stored type) |
| `Constant` | Not propagated (literals have intrinsic types) |

**Rationale:** Arithmetic operators like `+`, `-`, `*`, `/` have fixed signatures operating on
numeric types. Propagating a `{STRING}` target type to arithmetic operands would incorrectly
constrain the operand evaluation. Instead, operands are evaluated without type constraints,
the operation is performed, and the result is coerced to the target type if needed.

For example, in `"{{ Param.Count - 1 }}"` where the target type is `{STRING}`:
1. `Param.Count` is evaluated unconstrained → returns `int`
2. `1` is evaluated unconstrained → returns `int`
3. `__sub__(int, int)` is called → returns `int`
4. Result `int` is coerced to `string` for the target context

The same principle governs function-call arguments. The caller's target
describes the call's *result*, so it may select which signatures are
plausible (by return type), but it must never alter how the arguments
themselves evaluate beyond what the signatures' own parameter types say. In
particular, for a generic signature such as `sorted(list: list[T1]) ->
list[T1]`, the target is **not** unified with the return type to bind `T1`:
`sorted([10, 2])` with target `{LIST[STRING]}` evaluates its argument
unconstrained, sorts numerically, and coerces the *result* to
`["2", "10"]`. Binding `T1 = string` into the argument would instead coerce
the list first and sort lexicographically (`["10", "2"]`) — the target
would have changed the computation, not just the type of its result.

A parameter type containing a type variable constrains an argument to a
family of types — `list[T1]` to any list type — which is not a type to
coerce toward, so such positions are evaluated unconstrained. Signature
resolution still enforces the constraint: `sorted("abc")` fails whether or
not a target is supplied, and an argument a signature accepts by coercion
(`range_expr` where `list[int]` is required) is still coerced there.

**Signature resolution is independent of the target type.** Once arguments
are evaluated, the implementation is selected by multiple dispatch over the
argument types alone (see `resolve_and_call` below); a signature's return
type never participates in resolution. The candidate filter above is a
best-effort aid for evaluating arguments, not a resolution step: when no
signature survives the filter, the arguments are evaluated unconstrained
and the call is resolved and executed normally, with the target-type
mismatch reported by the final result coercion. This ordering produces the
more precise diagnostic — e.g. `min([1, 2])` with target `{LIST[STRING]}`
reports that the `int` result cannot coerce to `list[string]`, rather than
a generic "no matching signature" error.

**Symbol Table**

It requires a symbol table mapping names to either child tables or values:

```
SymbolTable: dict[string, SymbolTableEntry]
SymbolTableEntry: SymbolTable | ExprValue
```

For example, a symbol table with parameters `Param.InputFile: path` and `Param.OutputFile: path`:
```python
{"Param": {"InputFile": ExprValue(PATH, ...), "OutputFile": ExprValue(PATH, ...)}}
```

To support scoping for the list comprehension evaluation, recursive evaluation accepts a list
of symbol tables in local to global order.

**Pseudo-code**

```python
TypeSet = Optional[set[ExprType]]  # None means unconstrained

def evaluate_expression(
    node: Expr,
    ts: TypeSet,
    symtabs: list[SymbolTable]
) -> ExprValue:
    match node:
        case IfExp(test, body, orelse):
            test_val = evaluate_expression(test, {BOOL}, symtabs)
            if test_val.item():
                return evaluate_expression(body, ts, symtabs)
            else:
                return evaluate_expression(orelse, ts, symtabs)

        case Call(Name(func), args):
            # Function call: f(x, y, ...)
            # Operators (transformed from BinOp/UnaryOp/Compare) evaluate operands unconstrained
            is_operator = func.startswith("__") and func.endswith("__")

            if is_operator:
                # Evaluate operands without target type constraints
                arg_values = [evaluate_expression(arg, None, symtabs) for arg in args]
            else:
                # Regular function: compute arg typesets from the signatures
                # whose arity matches and whose return type is compatible
                # with the caller's target. The target filters which
                # signatures contribute — it is never unified with a
                # signature's return type to bind type variables into the
                # parameters.
                candidates = [sig for sig in FUNCTION_SIGNATURES[func]
                              if len(sig.param_types) == len(args)
                                 and (ts is None or sig.return_type in ts
                                      or can_coerce(sig.return_type, ts))]

                # Compute TypeSet for each argument position from the
                # parameter types as written. A symbolic parameter type
                # (one containing a type variable) names a family of
                # types rather than one to coerce toward — list[T1] means
                # any list type — so it makes the position unconstrained;
                # resolve_and_call still enforces it below. If no
                # signature survived the filter, all positions are
                # unconstrained: the call still resolves and executes
                # normally, and the target-type mismatch surfaces as a
                # coercion error on the call's result (a more precise
                # diagnostic than failing here).
                arg_typesets = []
                for i in range(len(args)):
                    pos_types = {sig.param_types[i] for sig in candidates}
                    if not pos_types or any(is_symbolic(t) for t in pos_types):
                        arg_typesets.append(None)  # unconstrained
                    else:
                        arg_typesets.append(pos_types)

                # Evaluate arguments with computed TypeSets
                arg_values = [evaluate_expression(args[i], arg_typesets[i], symtabs)
                              for i in range(len(args))]

            # Find best matching signature and call (coercion allowed on
            # all args). Resolution considers every arity-matching
            # signature for the function — not just the target-filtered
            # candidates above — and matches on argument types only:
            # return types and the caller's target play no part in it.
            all_sigs = [sig for sig in FUNCTION_SIGNATURES[func]
                        if len(sig.param_types) == len(args)]
            return resolve_and_call(func, all_sigs, arg_values,
                                    is_method_call=False)

        case Call(Attribute(value, attr), args):
            # Method call: x.f(y, ...) -> f(x, y, ...)
            # Evaluate receiver and remaining arguments
            receiver = evaluate_expression(value, None, symtabs)
            all_args = [receiver] + [evaluate_expression(arg, None, symtabs) for arg in args]

            # Find candidate signatures
            candidates = [sig for sig in FUNCTION_SIGNATURES[attr]
                          if len(sig.param_types) == len(all_args)]
            if not candidates:
                raise TypeError(f"No matching signature for {attr}")

            # Find best matching signature (no coercion on receiver)
            return resolve_and_call(attr, candidates, all_args, is_method_call=True)

        case Attribute() | Name():
            value = lookup_variable(node, symtabs)
            check_type_compatible(value.type, ts)
            return value

        case Constant(value):
            check_type_compatible(value.type, ts)
            return value

        case List(elts):
            elem_ts = extract_element_typeset(ts)
            elem_values = [evaluate_expression(e, elem_ts, symtabs) for e in elts]
            elem_type = resolve_list_element_type(elem_values)
            return ExprValue(LIST[elem_type], coerce_all(elem_values, elem_type))

        case ListComp(elt, generator):
            elem_ts = extract_element_typeset(ts)
            iter_val = evaluate_expression(generator.iter, None, symtabs)
            if iter_val.type.type_code not in (LIST, RANGE_EXPR):
                raise TypeError("List comprehension requires list or range_expr")

            # Get iterable items
            if iter_val.type.type_code == LIST:
                items = iter_val.to_expr_value_list()
            else:  # RANGE_EXPR
                items = [ExprValue(i) for i in iter_val.item()]

            results = []
            for item in items:
                # Create new scope with loop variable
                local_symtab = {generator.target: item}
                local_symtabs = [local_symtab] + symtabs

                # Check filter conditions
                skip = False
                for cond in generator.ifs:
                    cond_val = evaluate_expression(cond, {BOOL}, local_symtabs)
                    if not cond_val.item():
                        skip = True
                        break
                if skip:
                    continue

                # Evaluate element expression
                results.append(evaluate_expression(elt, elem_ts, local_symtabs))

            elem_type = resolve_list_element_type(results)
            return ExprValue(LIST[elem_type], coerce_all(results, elem_type))

def lookup_variable(node: Attribute | Name, symtabs: list[SymbolTable]) -> ExprValue:
    path = collect_attribute_path(node)  # e.g., ["Param", "InputFile", "stem"]

    # Try full path first
    value = lookup_path(path, symtabs)
    if value is not None:
        return value

    # Try all-but-last as variable, last as property
    if len(path) > 1:
        base_value = lookup_path(path[:-1], symtabs)
        if base_value is not None:
            prop_name = path[-1]
            prop_func = f"__property_{prop_name}__"
            return call_function(prop_func, [base_value])

    raise NameError(f"Undefined variable: {'.'.join(path)}")

def lookup_path(path: list[str], symtabs: list[SymbolTable]) -> Optional[ExprValue]:
    for symtab in symtabs:
        result = symtab
        for name in path:
            if isinstance(result, dict) and name in result:
                result = result[name]
            else:
                result = None
                break
        if isinstance(result, ExprValue):
            return result
    return None

def resolve_and_call(
    func: str,
    candidates: list[Signature],
    arg_values: list[ExprValue],
    is_method_call: bool = False
) -> ExprValue:
    # Try direct match first
    for sig in candidates:
        if all(arg_values[i].type == sig.param_types[i] for i in range(len(arg_values))):
            return call_function(func, arg_values, sig)

    # Try with coercion
    # For method calls, skip coercion on first argument (receiver)
    for sig in candidates:
        can_match = True
        coerced = []
        for i in range(len(arg_values)):
            if is_method_call and i == 0:
                # Receiver must match exactly for method calls
                if arg_values[i].type != sig.param_types[i]:
                    can_match = False
                    break
                coerced.append(arg_values[i])
            elif can_coerce(arg_values[i].type, sig.param_types[i]):
                coerced.append(coerce(arg_values[i], sig.param_types[i]))
            else:
                can_match = False
                break
        if can_match:
            return call_function(func, coerced, sig)

    raise TypeError(f"No matching signature for {func} with given argument types")

def extract_element_typeset(ts: TypeSet) -> TypeSet:
    if ts is None:
        return None
    return {t.type_params[0] for t in ts if t.type_code == LIST}

def is_symbolic(t: ExprType) -> bool:
    # True if the type contains a type variable (T, T1, T2, T3),
    # e.g. list[T1] in "sorted(list: list[T1]) -> list[T1]".
    return t.type_code in (TYPEVAR_T, TYPEVAR_T1, TYPEVAR_T2, TYPEVAR_T3) \
        or any(is_symbolic(p) for p in t.type_params)

def can_coerce(from_type: ExprType, to_type: ExprType) -> bool:
    if from_type == to_type:
        return True
    # int -> float
    if from_type.type_code == INT and to_type.type_code == FLOAT:
        return True
    # int, float, bool, path -> string (in string contexts)
    if to_type.type_code == STRING and from_type.type_code in (INT, FLOAT, BOOL, PATH):
        return True
    return False
```

### Operators, Built-in Functions, and Property Access

The operators and built-in functions available in expressions are defined in
[RFC 0006: Expression Function Library](0006-expression-function-library.md). Uniform
function call syntax, and the operator naming scheme documented there enable this.

### List Comprehensions

Simple list comprehensions are supported for transforming and filtering lists. Python's nesting within
a list comprehension is not supported.

```
[expr for var in list]
[expr for var in list if condition]
```

The loop variable (`var`) must start with a lowercase letter or underscore, matching the
`<UserIdentifier>` rule. This ensures it cannot shadow spec-defined symbols like `Param` or `Task`.
A list comprehension binding that shadows an existing binding is an error.

Examples:
- `[['-e', e] for e in Task.Environment]` transforms `["A=1", "B=2"]` into
  `[["-e", "A=1"], ["-e", "B=2"]]`.
- `[x for x in Param.Values if x > 0]` filters to only positive values.

### Slicing

Slicing extracts a subset of elements from lists, strings, or range expressions using Python-style slice
notation `[start:stop:step]`. All three components are optional:

- `start`: Starting index (inclusive), defaults to 0 (or end if step is negative)
- `stop`: Ending index (exclusive), defaults to length (or -length-1 if step is negative)
- `step`: Step between elements, defaults to 1

Negative indices count from the end: `-1` is the last element, `-2` is second-to-last, etc.

Note: The `path` type does not support subscript or slice operations, matching Python's `pathlib.Path`
behavior. Use `p.parts` to get path components as a list, which can then be sliced.

| Expression | Description |
|------------|-------------|
| `v[1:4]` | Elements at indices 1, 2, 3 |
| `v[:3]` | First 3 elements |
| `v[2:]` | All elements from index 2 to end |
| `v[::2]` | Every other element |
| `v[::-1]` | Reversed |
| `v[-3:]` | Last 3 elements |
| `v[1:-1]` | All except first and last |

Examples:
- `[1, 2, 3, 4, 5][1:4]` returns `[2, 3, 4]`
- `"hello"[1:4]` returns `"ell"`
- `path("/a/b/c/d").parts[1:]` returns `["a", "b", "c", "d"]`
- `range_expr("1-10")[::2]` returns `[1, 3, 5, 7, 9]`

### Conditional Expression Semantics

The conditional expression `<true_value> if <condition> else <false_value>`:

1. Evaluates `<condition>` first. The `<condition>` value must be a `bool`, there is no "truthy" concept like in Python.
2. If `<condition>` is `True`, then return `<true_value>`.
3. If Otherwise, evaluates and returns `<false_value>`

### Error Handling

Expression evaluation errors result in a job failure with a descriptive error message.
Because expressions can be evaluated at different times, e.g. during submission or
while evaluating the state of a step or task, these errors can happen at various phases
of running a job. Errors include:

- Type errors (e.g., adding string to int)
- Division by zero
- Index out of bounds
- Unknown function or variable reference
- Syntax errors
- Memory limit exceeded
- Operation limit exceeded

### Backward Compatibility

Templates not using the `EXPR` extension continue to use the existing simple
value reference syntax. The extension must be explicitly requested:

```yaml
specificationVersion: 'jobtemplate-2023-09'
extensions:
  - EXPR
```

### Specification Model Changes

The EXPR extension introduces changes to the specification model to support expressions
in additional contexts.

#### ListExpressionString Type

A new format string type `ListExpressionString` is introduced for fields that accept
expressions evaluating to lists. This type:

- Accepts a format string containing an expression (e.g., `"{{ [1.0, 2.0, 3.0] }}"`)
- Evaluates to a list of values when the EXPR extension is enabled
- Is used in contexts where a list literal was previously required

#### Task Parameter Range Field Extensions

The `range` field for FLOAT, STRING, and PATH task parameter definitions is extended
to accept `ListExpressionString` in addition to list literals:

| Parameter Type | Original `range` Type | Extended `range` Type |
|---------------|----------------------|----------------------|
| INT | `list[int \| FormatString] \| RangeString` | (unchanged) |
| FLOAT | `list[Decimal \| FormatString]` | `list[Decimal \| FormatString] \| ListExpressionString` |
| STRING | `list[FormatString]` | `list[FormatString] \| ListExpressionString` |
| PATH | `list[FormatString]` | `list[FormatString] \| ListExpressionString` |

This enables expressions that compute lists dynamically:

```yaml
parameterDefinitions:
  - name: Scale
    type: FLOAT
    default: "2.5"
steps:
  - name: Process
    parameterSpace:
      taskParameterDefinitions:
        - name: Factor
          type: FLOAT
          # Expression evaluates to [5.0, 3.0]
          range: "{{ [Param.Scale * 2, Param.Scale + 0.5] }}"
```

When the EXPR extension is enabled, the `ListExpressionString` is evaluated at job
creation time, producing a list that populates the task parameter range.

#### Let Bindings

The EXPR extension adds an optional `let` field to `StepTemplate`, `StepScript`, `SimpleAction`,
and `EnvironmentScript` for binding expressions to names. This avoids repeating complex expressions
across multiple fields.

##### `<LetBindings>`

```yaml
let: [ <LetBinding>, ... ]  # @optional
```

An ordered array of let bindings. Bindings are evaluated in declaration order; later
bindings can reference names from earlier bindings. A binding that shadows a previous
binding in the same `let` block is an error.

##### `<LetBinding>`

Each binding is a string using Python assignment syntax:

```bnf
<LetBinding>     ::= <UserIdentifier><WS>*"="<WS>*<Expression>
<UserIdentifier> ::= [a-z_][A-Za-z0-9_]*
<WS>             ::= whitespace character: tabs or spaces
```

The `<UserIdentifier>` must start with a lowercase letter or underscore. This ensures
user-defined names never conflict with spec-defined symbols (`Param`, `Task`, `Session`,
`Env`, `RawParam`), which always start with an uppercase letter. The same constraint
applies to loop variables in list comprehensions.

Constraints on `<UserIdentifier>`:
- Minimum length: 1 character
- Maximum length: 512 characters

The type of the binding is inferred from the expression's result type.

Examples:
- `x = Param.Value + 1` - `x` has type `int` if `Param.Value` is `int`
- `files = [Param.Dir / f for f in Param.Names]` - `files` has type `list[path]`

##### Type Checking of Let Bindings

Let binding expressions are type-checked at template validation time (e.g., during
`decode_job_template`), not deferred to evaluation time. This provides early detection
of type errors with precise error messages.

Type checking is performed sequentially: each binding's expression is type-checked
against the types of symbols available at that point, and the inferred result type
is then made available for subsequent bindings. This enables type propagation through
chained bindings:

```yaml
let:
  - x = Param.Count        # x inferred as int (from INT parameter)
  - y = x + 1              # y inferred as int (int + int = int)
  - z = string(y)          # z inferred as string
  - bad = y + "hello"      # TYPE ERROR: int + string
```

The error message includes the binding context and a caret pointing to the error:

```
Cannot use '+' with int and string
  bad = y + "hello"
        ~~^~~~~~~~~
```

##### StepTemplate Extension

When `let` appears in a `StepTemplate`, bindings are evaluated once per step. The bound
names are available in `stepEnvironments`, `parameterSpace`, `hostRequirements`, and `script` fields:

```yaml
steps:
  - name: ProcessTiles
    let:
      - max_u = (proto_udim - 1001) % 10
      - max_v = (proto_udim - 1001) // 10
    parameterSpace:
      taskParameterDefinitions:
        - name: TileU
          type: INT
          range: "0-{{ max_u }}"
        - name: TileV
          type: INT
          range: "0-{{ max_v }}"
```

##### ScriptTemplate Extension

When `let` appears in a `ScriptTemplate`, bindings are evaluated once per task (or once
per environment action). The bound names are available in `actions` and `embeddedFiles`,
and can reference `Task.Param.*` as well as the embedded file path symbols of the same
script (`Task.File.*` in a step script, `Env.File.*` in an environment script) — the
file path is determined before the bindings are evaluated, even though the file content
is evaluated separately:

```yaml
script:
  let:
    - output_file = Param.OutputDir / Param.Pattern.with_number(Task.Param.Frame)
  actions:
    onRun:
      command: render
      args: ["--output", "{{ output_file }}"]
```

Environment scripts use the same mechanism:

```yaml
environments:
  - name: Setup
    script:
      let:
        - work_dir = Param.OutputDir / 'work'
      actions:
        onEnter:
          command: mkdir
          args: ["-p", "{{ work_dir }}"]
```

##### SimpleAction Extension

When using the `FEATURE_BUNDLE_1` syntax sugar for scripts (`bash`, `python`, `cmd`, `powershell`,
`node`), `let` bindings can be included directly in the `<SimpleAction>`. The bindings are
evaluated once per task and can reference `Task.Param.*`:

```yaml
steps:
  - name: RenderFrame
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "{{Param.Frames}}"
    bash:
      let:
        - output_file = Param.OutputDir / Param.Pattern.with_number(Task.Param.Frame)
      script: |
        render --output {{repr_sh(output_file)}}
```

This is equivalent to using `let` in the expanded `<StepScript>` form:

```yaml
steps:
  - name: RenderFrame
    parameterSpace:
      taskParameterDefinitions:
        - name: Frame
          type: INT
          range: "{{Param.Frames}}"
    script:
      let:
        - output_file = Param.OutputDir / Param.Pattern.with_number(Task.Param.Frame)
      embeddedFiles:
        - name: Script
          type: TEXT
          data: |
            render --output {{repr_sh(output_file)}}
      actions:
        onRun:
          command: bash
          args: ["{{Task.File.Script}}"]
```

## Design Choice Rationale

### Python Expression Subset

The expression syntax is a subset of Python expressions. This choice:

1. Provides familiar syntax for users
2. Enables implementation using Python's `ast` module for parsing
3. Allows potential implementations in other languages using Python grammar parsers
4. Avoids inventing new syntax that users must learn

The subset is intentionally limited to prevent:
- Arbitrary code execution
- Side effects
- Complex control flow

### Contextual Keywords

Keywords are contextual to ensure backward compatibility. A parameter named `if` can still
be accessed as `Param.if` because `if` is only a keyword in operator position, not after `.`.

### No Assignment or Statements

The expression language is purely functional with no assignment or statements. This:

1. Keeps templates declarative
2. Prevents complex logic that belongs in scripts
3. Simplifies implementation and validation

## Prior Art

### Jinja2

[Jinja2](https://jinja.palletsprojects.com/) is a full-featured templating engine for Python.
Open Job Description's `{{ }}` syntax is inspired by Jinja2. This RFC extends toward Jinja2's
expression capabilities while remaining a strict subset.

### AWS CloudFormation Intrinsic Functions

[CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html)
uses intrinsic functions like `!Sub`, `!If`, `!Equals` for template logic. This RFC takes a
more expression-oriented approach rather than function-based.

### GitHub Actions Expressions

[GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/expressions) uses
`${{ }}` syntax with expressions supporting operators, functions, and conditionals. This RFC
follows a similar philosophy.

### Workflow Description Language (WDL)

[WDL](https://github.com/openwdl/wdl) is a workflow language for bioinformatics. EXPR
shares similar primitive types and math functions, but excludes WDL's file I/O functions and
complex types (`Pair`, `Map`, `Struct`).

### Common Workflow Language (CWL)

[CWL](https://www.commonwl.org/) uses simple parameter references (`$(inputs.foo)`) with optional
JavaScript expressions, that it recommends minimizing. EXPR aligns with
this philosophy, defining an expression DSL and leaving complex code to run as tasks.

### Nextflow

[Nextflow](https://nextflow.io/docs/latest/) is a Groovy-based workflow language. EXPR
proposes a much more limited expression language, compared to the generality of Groovy.

### Argo Workflows

[Argo Workflows](https://argo-workflows.readthedocs.io/) uses a dual-mode expression system with
simple tags and [Expr](https://expr-lang.org/)-powered expressions. EXPR shares this
philosophy but opts to define a DSL tailored to fit the job template specification.

## Rejected Ideas

### Full Jinja2 Support

Using the complete Jinja2 language was considered but rejected because:

1. Jinja2 includes control flow (for loops, macros) that would complicate job templates
2. Security concerns with sandboxing arbitrary template logic
3. Implementation complexity across different languages/platforms

### Custom Expression Language

Designing a completely new expression syntax was rejected in favor of Python subset because:

1. Python syntax is widely known
2. Existing parsing tools are available
3. Reduces learning curve for users

### Lossy Implicit Type Coercion

Automatic lossy type coercion (e.g., `"5" + 3` = `8`) was rejected because:

1. Can lead to subtle bugs
2. Makes template behavior less predictable
3. Explicit conversion functions (`int()`, `string()`) are clearer

### Walrus Operator for Variable Binding

Python's assignment expression operator (`:=`) was considered for binding intermediate values
within expressions:

```yaml
- "{{ m[1] if (m := re_search(Param.Filename, r'_v(\d+)')) != null else 'v001' }}"
```

This was rejected because:

1. Only helps within a single expression—doesn't solve sharing values across multiple fields
2. The schema-level `let` bindings provide a cleaner, more explicit approach

## Appendix A: Backward Compatibility Analysis

This section provides detailed analysis supporting Technical Requirement #1.

### Current Format String Syntax

```bnf
{{ <ValueReference> }}
<ValueReference> ::= <Name>
<Name>           ::= <Name> "." <Identifier> | <Identifier>
<Identifier>     ::= [A-Za-z_][A-Za-z0-9_]*
```

Examples: `{{Param.Name}}`, `{{Task.Param.Frame}}`, `{{Session.WorkingDirectory}}`

### Grammar Compatibility

The proposed extended grammar is a strict superset. Every valid expression under the current
grammar remains valid and produces the same result through the parse path:
`<ValueReference>` → `<PrimaryExpr>` → `<PostfixExpr>` → ... → `<ConditionalExpr>`

### Potential Concerns

1. **Whitespace handling**: `{{ Param.Name }}` and `{{Param.Name}}` must remain equivalent.
   The extended grammar preserves this.

2. **Error messages**: May differ for invalid input. Acceptable as long as invalid input
   is still rejected.

3. **Reserved words**: Keywords like `if` and `None` could conflict with parameter names.

### Keyword Conflict Analysis

| Expression | Current Behavior | Naive Extended Behavior | Breaking? |
|------------|------------------|-------------------------|-----------|
| `{{Param.if}}` | Valid, returns value | Parse error: `if` is keyword | **YES** |
| `{{Param.True}}` | Valid, returns value | Parse error: `True` is keyword | **YES** |

### Mitigation: Contextual Keywords

See Appendix C for an implementation of contextual keywords parsing Python
expressions using the `ast.parse` standard function available in Python.

## Appendix B: Language Syntax Choice

The expression language syntax must be chosen carefully. Two natural candidates are Python
and ECMAScript (JavaScript), each with distinct tradeoffs.

### Python Syntax

**Advantages:**
- Reference implementation of OpenJD is in Python
- Many job template authors use Python for scripting
- Python's `ast` module provides robust parsing
- Familiar to the VFX/animation industry (Python is dominant)

**Disadvantages:**
- Syntax mismatch with JSON/YAML templates:
  - `None` vs `null`
  - `True`/`False` vs `true`/`false`
  - Single quotes `'string'` common in Python, double quotes `"string"` in JSON
- Keywords are not contextual (see Backward Compatibility Analysis)

**Example mismatch:**
```yaml
# YAML template with Python expression - mixed conventions
field: "{{ None if Param.Skip else 'value' }}"
default: null  # YAML/JSON style outside expression
```

### ECMAScript Syntax

**Advantages:**
- JSON is a subset of ECMAScript - syntactic consistency
- `null`, `true`, `false` match JSON exactly
- Double-quoted strings match JSON convention
- Widely known language

**Disadvantages:**
- Reference implementation is Python - would need a JS expression parser in Python
- Less familiar to VFX Python developers
- `===` vs `==` semantics could confuse users
- No built-in Python parser (would need `esprima`, `pyjsparser`, or similar)

**Example consistency:**
```yaml
# YAML template with ECMAScript expression - consistent conventions
field: "{{ null if Param.Skip else 'value' }}"  # Hypothetical Python-like syntax with JS literals
default: null
```

### Comparison Table

| Aspect | Python | ECMAScript |
|--------|--------|------------|
| Null value | `None` | `null` |
| Boolean true | `True` | `true` |
| Boolean false | `False` | `false` |
| Logical AND | `and` | `&&` |
| Logical OR | `or` | `\|\|` |
| Logical NOT | `not x` | `!x` |
| Integer division | `//` | `Math.floor(/)` |
| String quotes | `'` or `"` | `'` or `"` |
| Conditional | `x if cond else y` | `cond ? x : y` |
| List literal | `[1, 2, 3]` | `[1, 2, 3]` |
| Attribute access | `obj.attr` | `obj.attr` |
| Parser availability (Python impl) | `ast` (stdlib) | `esprima`, `pyjsparser` |
| Parser availability (Rust impl) | `rustpython-parser` | `swc`, `oxc` |

### Other Languages Considered

**Jinja2 Expression Syntax:**
- Already inspired OpenJD's `{{ }}` delimiters
- Subset of Python with some differences
- Would still have `None`/`True`/`False` mismatch with JSON
- No significant advantage over pure Python subset

**JSON Expression Languages (JSONPath, JMESPath, JSONata):**
- Designed for JSON querying, not general expressions
- Limited arithmetic and conditional support
- Would require learning a new syntax

**CEL (Common Expression Language):**
- Designed by Google for configuration expressions
- Type-safe, sandboxed by design
- `null`, `true`, `false` match JSON
- Less familiar to users than Python or JS
- Would require embedding a CEL evaluator

### Hybrid Approach

A pragmatic option is **Python syntax with JSON-compatible literals**:

- Use Python's grammar and `ast` module for parsing
- Accept both `None` and `null` as the null value
- Accept both `True`/`False` and `true`/`false` as booleans
- This provides parser reuse while reducing cognitive friction with JSON/YAML

**Implementation:** After `ast.parse()`, a simple AST transform can normalize:
- `Name(id='null')` → `Constant(value=None)`
- `Name(id='true')` → `Constant(value=True)`
- `Name(id='false')` → `Constant(value=False)`

### Recommendation

**Python syntax with JSON-compatible literal aliases** offers the best balance:

1. Leverages Python's `ast` module (Technical Requirement #3)
2. Familiar to OpenJD's primary user base
3. Reduces friction with JSON/YAML by accepting `null`, `true`, `false`
4. Conditional expression syntax (`x if cond else y`) reads naturally in templates

The specification should document that `null`/`None`, `true`/`True`, `false`/`False` are
interchangeable within expressions.

## Appendix C: Context-Sensitive Keyword Parsing in Python

The expression grammar treats Python keywords (`if`, `else`, `and`, `or`, `not`, `for`, `in`,
`True`, `False`, `None`) as contextual—they are only keywords in operator positions, not as
attribute names after `.`. This allows expressions like `Param.if` to remain valid for backward
compatibility.

Python's `ast.parse()` does not support contextual keywords, so a workaround is needed. The
approach is to iteratively parse, and when a syntax error occurs immediately after a `.`,
substitute the keyword with a unique identifier, then restore it in the resulting AST.

### Implementation

```python
import ast
import secrets
import string
from keyword import kwlist

class FixupRenamedKeywordsVisitor(ast.NodeTransformer):
    """Restores original keyword names in attribute positions after parsing."""
    def __init__(self, keywords_renamed: dict[str, str]):
        self._rename = {value: key for key, value in keywords_renamed.items()}
        super().__init__()

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        value = self.visit(node.value)
        attr = self._rename.get(node.attr, node.attr)
        return ast.Attribute(value=value, attr=attr, ctx=node.ctx)

def ast_parse_keyword_context(source: str) -> ast.AST:
    """Parse with context-sensitive keywords: Python keywords are allowed after '.'."""
    keywords_renamed: dict[str, str] = {}
    sub_chars = string.ascii_letters + string.digits
    while True:
        try:
            ast_node = ast.parse(source, mode="eval")
            if keywords_renamed:
                ast_node = FixupRenamedKeywordsVisitor(keywords_renamed).visit(ast_node)
            return ast_node
        except SyntaxError as exc:
            # Convert line/offset to absolute position in source (for multi-line support)
            abs_offset = None
            if exc.lineno is not None and exc.offset is not None:
                lines = source.split("\n")
                abs_offset = sum(len(lines[i]) + 1 for i in range(exc.lineno - 1)) + exc.offset

            # Check for keyword after '.' at either offset or end_offset
            kw_start = None
            if abs_offset is not None and abs_offset >= 2 and source[abs_offset - 2] == ".":
                kw_start = abs_offset - 1
            else:
                # Try end_offset (added in Python 3.10)
                end_lineno = getattr(exc, "end_lineno", None)
                end_offset = getattr(exc, "end_offset", None)
                if end_lineno is not None and end_offset is not None:
                    lines = source.split("\n")
                    abs_end = sum(len(lines[i]) + 1 for i in range(end_lineno - 1)) + end_offset
                    if abs_end >= 1 and source[abs_end - 1] == ".":
                        kw_start = abs_end

            if kw_start is not None:
                kw_end = kw_start
                while kw_end < len(source) and (source[kw_end].isalnum() or source[kw_end] == '_'):
                    kw_end += 1
                keyword = source[kw_start:kw_end]

                if keyword in kwlist:
                    keyword_sub = keywords_renamed.get(keyword)
                    if not keyword_sub:
                        while True:
                            keyword_sub = secrets.choice(string.ascii_letters) + \
                                ''.join(secrets.choice(sub_chars) for _ in range(len(keyword) - 1))
                            if keyword_sub not in source:
                                break
                        keywords_renamed[keyword] = keyword_sub
                    source = source[:kw_start] + keyword_sub + source[kw_end:]
                    continue
            raise
```

### How It Works

1. Attempt to parse the expression with `ast.parse(source, mode="eval")`.
2. If a `SyntaxError` occurs, convert the line number and column offset to an absolute
   position in the source string. This is necessary for multi-line expressions where
   `exc.offset` is relative to the line, not the entire source.
3. Check for a `.` followed by a keyword at two positions:
   - `source[abs_offset - 2]`: the character before the error start (checking for `.`)
   - `source[abs_end - 1]`: the character at the error span end (checking for `.`)

   Both positions must be checked because Python's parser reports errors differently
   depending on context. For `Param.if`, the error points directly at `if`, so the `.`
   is at `abs_offset - 2`. For `x if Param.if else y`, the parser sees a malformed
   conditional and reports "expected 'else' after 'if' expression" with the error span
   ending at the `.` (`abs_end - 1`), not pointing to the keyword itself.
4. If a `.keyword` pattern is found, generate a unique substitute identifier of the same
   length and replace it in the source. Preserving length ensures line numbers and column
   offsets in the resulting AST match the original source.
5. Retry parsing with the modified source.
6. After successful parsing, use `FixupRenamedKeywordsVisitor` to restore the original
   keyword names in `Attribute` nodes.

### Test Cases

Recommended test expressions for validating an implementation:

```python
# Keywords as attribute names (should parse successfully)
"Param.if"
"Param.def"
"Param.else"
"Param.and"
"Param.or"
"Param.not"
"Param.for"
"Param.in"
"Param.True"
"Param.False"
"Param.None"

# Chained keyword attributes
"Param.Value.if.else.and"

# Keywords as attributes combined with keyword operators
"Param.if and Param.or"
"x if Param.if else y"
"x if Param.flag else Param.else"
"Param.if if Param.flag else Param.else"
"result if Param.and else default"

# Keywords in operator positions still work normally
"True if x else False"
"x and y or z"
"not x"
"[i for i in items]"
"x in items"

# Multi-line expressions with keyword attributes
"""[
    Param.if,
    Param.else
]"""
"""(
    Param.if +
    Param.else
)"""
```

## Appendix D: Implicit Line Continuation

Python requires explicit line continuation for multi-line expressions—either a backslash (`\`)
at the end of each continued line, or enclosing the expression in parentheses, brackets, or
braces. This is inconvenient for expressions embedded in YAML templates, where the expression
may naturally span multiple lines for readability.

The expression language supports implicit line continuation: expressions can span multiple
lines without any special syntax.

### Examples

```yaml
# Multi-line arithmetic without continuation characters
args:
  - "{{ Param.Start +
        Param.Count *
        Param.Step }}"

# Multi-line conditional
field: "{{ 'high'
           if Param.Quality > 80
           else 'low' }}"

# Multi-line list (works in Python too, but shown for completeness)
values: "{{ [
    Param.A,
    Param.B,
    Param.C
] }}"
```

### Implementation

When parsing an expression that contains newlines, the parser wraps the expression in
parentheses before passing it to the underlying Python parser:

```python
def parse_expression(source: str) -> ast.AST:
    if "\n" in source:
        # Wrap to enable implicit line continuation
        wrapped = f"(\n{source}\n)"
        ast_node = ast.parse(wrapped, mode="eval")
        # Adjust line numbers back by 1 to account for added opening paren line
        adjust_line_numbers(ast_node, offset=-1)
        return ast_node
    else:
        return ast.parse(source, mode="eval")
```

The wrapping format `(\n{source}\n)` is chosen so that:
- Line numbers in the AST are offset by exactly 1 (easy to adjust back)
- Column offsets remain unchanged
- Error messages can reference the correct line in the original expression

Single-line expressions are not wrapped, avoiding any impact on error messages for the
common case.

### Error Reporting

When an error occurs in a multi-line expression, the error message shows only the relevant
line with a caret pointing to the error location:

```
Cannot use '+' operator with int and string
    Param.Count +
    ~~~~~~~~~~~~^
```

For single-line expressions, the full expression is shown as before.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
