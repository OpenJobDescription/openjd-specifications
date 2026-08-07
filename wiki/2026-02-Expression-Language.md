# Expression Language [Extension: EXPR]

This document contains the formal specification for the Open Job Description Expression Language,
available to templates as the `EXPR` extension to the [2023-09 Template Schemas](2023-09-Template-Schemas).

The expression language extends the [Format Strings](2023-09-Template-Schemas#73-format-strings) defined in the
Template Schemas with a domain-specific expression language that provides arithmetic, conditional logic,
string and path manipulation, list operations, and more. It is defined as a subset of the
[Python](https://www.python.org/) expression grammar with compatibility extensions for JSON/YAML contexts.

This specification is organized into two parts:

1. **Language** — The grammar, type system, and evaluation semantics.
2. **Function Library** — The operators and built-in functions.

Reading the broad overviews in [How Jobs Are Constructed](How-Jobs-Are-Constructed) and [How Jobs Are Run](How-Jobs-Are-Run)
provides a good starting introduction and broader context prior to reading this specification.

## Motivation

Open Job Description templates need a flexible way to customize job structure and express glue
transformations between different interfaces. The current template substitution syntax is limited to
direct value references, which creates friction for common use cases:

1. **Arithmetic on job parameters** — Users frequently need to derive values from job parameters,
   for example computing the end of a frame range from a start value and a count. Currently this
   requires external scripting or embedding calculations in shell scripts.

2. **Conditional logic** — Selecting different values based on parameter settings requires
   workarounds like implementing a wrapper script whose sole purpose is to act as glue between
   the job parameter interface and a command.

3. **Conditional omission of fields/elements** — There is no way to conditionally omit an
   optional field or array element. Users must either pass empty strings (which may not be
   valid for the target command) or maintain multiple template variants.

4. **Inter-dependent job parameter defaults** — Computing default values for one parameter
   based on another requires expression evaluation in job submission UIs across multiple
   platforms (web, desktop, CLI).

## Design Constraints

The expression language is designed for evaluation within the constrained context of a template.
Schedulers must understand job structure without running tasks to determine it, so they need the
ability to evaluate expressions in an isolated, secure, and bounded context. These constraints
shape the language:

1. **No filesystem, network, or environment variable access** — Expressions have no access to the
   filesystem, network, or environment variables. The evaluation context is fully defined by the
   template's parameters and runtime context variables. There are no functions for these purposes,
   and none will be added. This ensures that a scheduler can evaluate expressions without reference
   to the environments that tasks run in, and that expressions do not depend on any outside state.

2. **Memory-bounded evaluation** — Expression evaluation must operate within bounded memory.
   Implementations accept a configurable memory limit (default: 100 million bytes recommended) and track the
   memory size of live values during evaluation. If current memory exceeds the limit, evaluation
   fails with an error. This supports implementations that allocate fixed resources to evaluate
   expressions, and prevents unbounded resource consumption from expressions like `"a" * 10000000`
   or large list comprehensions.

3. **Operation-bounded evaluation** — Expression evaluation must operate within a bounded number
   of operations. Implementations accept a configurable operation limit (default: 10 million
   recommended) and count operations during evaluation. Each function call counts as 1 operation,
   iterating through a list (in a list comprehension or within a function implementation) adds
   the number of elements to the count, and processing a string or path value adds the length
   of the value divided by 256 (rounded up) to the count. If the count exceeds the limit,
   evaluation fails with an error. This prevents unbounded computation from deeply nested or
   combinatorially explosive expressions.

4. **Deterministic evaluation** — Expressions must evaluate deterministically with no side
   effects. The same inputs must always produce the same outputs.

5. **No user-defined functions** — All functions, operators, and type properties are defined by
   the specification. There is no mechanism for users to define custom functions or extend the
   language within templates. This ensures templates are portable and evaluation is bounded and
   predictable.

6. **Backward compatibility** — All existing valid templates must continue to work identically
   with no changes. The extended expression syntax is only enabled when the `EXPR` extension is
   explicitly requested.

6. **Fail-fast errors** — Invalid expressions must be rejected at template validation/submission
   time, not at task runtime.

7. **Reuse existing Python parsers** — The language is specified as a subset of Python expression
   syntax so that implementations can rely on existing Python parsers rather than writing custom
   parsers. Python implementations can use the [`ast`](https://docs.python.org/3/library/ast.html)
   standard library module, Rust implementations can use the
   [ruff Python parser](https://github.com/astral-sh/ruff/tree/main/crates/ruff_python_parser),
   and JavaScript implementations can use
   [dt-python-parser](https://github.com/DTStack/dt-python-parser).

## Notations

* `@fmtstring` - The value of the annotated property is a Format String. See [Format Strings](2023-09-Template-Schemas#73-format-strings).
  * `@fmtstring[host]` - The value is evaluated at runtime on the worker host.
* `@optional` - The annotated property is optional.

## Related RFCs

* [RFC 0005: Expression Language](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0005-expression-language.md)
* [RFC 0006: Expression Function Library](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0006-expression-function-library.md)

## Enabling the Extension

The `EXPR` extension is enabled by including it in the `extensions` list of a Job Template:

```yaml
specificationVersion: 'jobtemplate-2023-09'
extensions:
  - EXPR
name: My Job
```

When `EXPR` is enabled:

1. Format strings accept the extended expression grammar defined in this document.
2. Extended job parameter types become available. See the
   [Template Schemas](2023-09-Template-Schemas#2-jobparameterdefinition) for the full definitions.
3. The `ArgString` type is amended to allow CR (U+000D), LF (U+000A), and TAB (U+0009) characters
   to support multi-line expressions in YAML literal block scalars.

Templates not using the `EXPR` extension continue to use the existing simple value reference syntax
defined in the [Template Schemas](2023-09-Template-Schemas#73-format-strings). All existing valid templates
continue to work identically with no changes.

---

## Recommended Library Interface

This section describes a recommended programming interface for implementations of the expression
language. Implementations should follow these patterns to the extent that the implementation
language supports them. The reference implementation is in the `openjd.expr` namespace of the
[openjd-model](https://github.com/OpenJobDescription/openjd-model-for-python) Python package.

### Types

#### ExprType

Represents a type in the expression language type system.

```
class ExprType:
    type_code: TypeCode           # The base type (BOOL, INT, FLOAT, STRING, PATH, LIST, etc.)
    type_params: list[ExprType]  # Type parameters (e.g., element type for LIST)
```

Construction:
- `ExprType(type_code, type_params=None)` — Create a type with the given code and optional parameters.
- `ExprType(type_string)` — Create a type from a string like `"int"`, `"list[string]"`, `"int?"`, `"int | string"`.

Type constants as class attributes:
- `ExprType.BOOL`, `ExprType.INT`, `ExprType.FLOAT`, `ExprType.STRING`, `ExprType.PATH`
- `ExprType.RANGE_EXPR`, `ExprType.NULLTYPE`, `ExprType.NORETURN`
- `ExprType.LIST_INT`, `ExprType.LIST_FLOAT`, `ExprType.LIST_STRING`, `ExprType.LIST_PATH`, `ExprType.LIST_BOOL`
- `ExprType.LIST_LIST_INT`, `ExprType.EMPTY_LIST`
- `ExprType.TYPEVAR_T`, `ExprType.TYPEVAR_T1`, `ExprType.TYPEVAR_T2`, `ExprType.TYPEVAR_T3`

**Type Codes:**

| Type Code | Type | Description |
|-----------|------|-------------|
| `NULLTYPE` | `nulltype` | The null type |
| `BOOL` | `bool` | Boolean |
| `INT` | `int` | Integer |
| `FLOAT` | `float` | Floating-point |
| `STRING` | `string` | String |
| `PATH` | `path` | Filesystem path |
| `RANGE_EXPR` | `range_expr` | Range expression |
| `LIST` | `list[T]` | List with element type in `type_params[0]` |
| `ANY` | `any` | Unconstrained type (matches anything) |
| `UNION` | `S \| T` | Union of types in `type_params` |
| `NORETURN` | `noreturn` | Bottom type for functions that never return |
| `UNRESOLVED` | `unresolved[T]` | Value not yet resolved, but satisfies constraint `T` in `type_params[0]` |
| `TYPEVAR_T` | `T` | Type variable for polymorphic function signatures |
| `TYPEVAR_T1` | `T1` | Type variable |
| `TYPEVAR_T2` | `T2` | Type variable |
| `TYPEVAR_T3` | `T3` | Type variable |

Type variables `T`, `T1`, `T2`, `T3` are used in function signatures (see [section 2](#2-function-library))
to represent polymorphic type parameters that are bound at call time. For example,
`__getitem__(list: list[T], index: int) -> T` means the return type matches the list's
element type. When a signature uses multiple type variables (e.g., `T1`, `T2`, `T3`), each
may bind to a different concrete type. Type variables do not appear as the type of a concrete
`ExprValue` at runtime — they exist only in `FunctionSignature` type parameters and are
resolved to concrete types during function dispatch.

**Union Type Normalization:**

Union types are automatically normalized when constructed:
- Nested unions are flattened: `(int | string) | bool` becomes `int | string | bool`
- Type parameters are sorted alphabetically with `nulltype` at the end
- Duplicate types are removed
- Single-element unions are unwrapped: a union with one member becomes that member
- `ANY` absorbs everything: `int | any` becomes `any`
- `NORETURN` collapses to nothing: `int | noreturn` becomes `int`

Optional types like `int?` are represented as unions: `int?` = `int | nulltype` (union of `int` and `NULLTYPE`).

The `noreturn` type is used for functions like `fail()` that never return. Because it collapses
in unions, expressions like `x if cond else fail("error")` have type `x`, not `x?`.

The `unresolved[T]` type represents a value whose concrete value is not known, but whose type
satisfies the constraint `T`. For example, `unresolved[int]` means "some value that is an `int`,
but we don't know which one." This is used during static type checking for expressions that
reference symbols whose values are not available until runtime. Unlike `any`, which is
unconstrained, `unresolved[T]` carries type information: `unresolved[int]` matches `int` but not
`string`. The constraint `T` can be any type including unions (e.g., `unresolved[int | float]`).
When the constraint is `any`, the shorthand `unresolved` is used (i.e., `unresolved` is equivalent
to `unresolved[any]`).

**Unknown Type Normalization:**

The `unresolved` type is always the outermost type constructor. When constructing types,
`unresolved` is hoisted outward using the following normalization rules:

- `list[unresolved[T]]` → `unresolved[list[T]]` — A list of unresolved elements is an unresolved list.
- `T | unresolved[S]` → `unresolved[T | S]` — If any branch of a union is unresolved, the whole
  result is unresolved. Non-unresolved members join the constraint.
- `unresolved[T] | unresolved[S]` → `unresolved[T | S]` — Multiple unresolved branches merge their
  constraints.
- `unresolved[unresolved[T]]` → `unresolved[T]` — Nested unresolved types flatten.

These rules apply recursively during type construction, ensuring that `unresolved` never appears
inside a `list` or `union` type parameter. The result is a canonical form where `unresolved` is
either absent or wraps the entire type.

#### ExprValue

Holds a typed value during expression evaluation.

```
class ExprValue:
    type: ExprType    # The value's type
    is_null: bool     # True if this is a null value
```

Note: `ANY`, `UNION`, and `UNRESOLVED` are type-level constructs used during type checking. They do not
appear as the type of a concrete `ExprValue` at runtime—values always have a specific
concrete type.

**Construction** — From Python values with automatic type inference:

```python
ExprValue(42)                      # int
ExprValue(3.14)                    # float
ExprValue("hello")                 # string
ExprValue(True)                    # bool
ExprValue(None)                    # null
ExprValue([1, 2, 3])               # list[int]
ExprValue(Decimal("3.140"))        # float (preserves decimal string)
```

**Construction** — With explicit type coercion:

```python
ExprValue("42", type="int")        # coerce string to int
ExprValue("3.14", type="float")    # coerce string to float
ExprValue("true", type="bool")     # coerce string to bool
ExprValue("/tmp", type="path")     # string as path
ExprValue("1-10", type="range_expr")  # string as range_expr
ExprValue([1, 2], type="list[int]")   # explicit list type
```

The `type` parameter accepts either an `ExprType` instance or a type string.

**Class methods**:

- `ExprValue.null()` — Create a null value.
- `ExprValue.from_float(value, original_str=None)` — Create a float, optionally preserving
  the original string representation for pass-through.

**Value extraction**:

- `item()` — Extract the native Python value:
  - `bool` for BOOL
  - `int` for INT
  - `float` for FLOAT
  - `str` for STRING
  - `str` for PATH
  - `IntRangeExpr` for RANGE_EXPR
  - `list` for LIST (recursively extracts items)
  - `None` for null values

- `to_string()` — Convert to string representation. Preserves original decimal representation
  for floats that were constructed with an original string representation. Lists are converted
  to JSON.

- `to_expr_value_list()` — Return list contents as `list[ExprValue]`. Raises `TypeError`
  if the value is not a list type.

**Representation**:

```python
repr(ExprValue(42))                    # ExprValue(42)
repr(ExprValue(3.14))                  # ExprValue(3.14)
repr(ExprValue("hello"))               # ExprValue('hello')
repr(ExprValue([1, 2, 3]))             # ExprValue([1, 2, 3], type='list[int]')
repr(ExprValue(Decimal("3.140")))      # ExprValue('3.140', type='float')
repr(ExprValue(None))                  # ExprValue(None)
```

The repr is designed to be copy-pasteable for reconstruction.

### Symbol Table

#### SymbolTable

Maps names to values or nested symbol tables for expression evaluation.

```
class SymbolTable:
    def __init__(self, source: dict | SymbolTable = None)
    def __getitem__(self, name: str) -> SymbolTable | ExprValue
    def __setitem__(self, name: str, value: Any)
    def __contains__(self, name: str) -> bool
    def get(self, name: str) -> SymbolTable | ExprValue | None
```

Supports dotted key paths for convenient construction:
```python
values = SymbolTable({
    "Param.Frame": 42,
    "Param.Name": "test",
    "Task.File": ExprValue("/render/output.exr", type="path")
})
```

Native Python values are automatically converted to `ExprValue`. Use
`ExprValue(str_value, type="path")` for path-typed values — `pathlib.PurePath` is not
automatically converted because the `path` type's semantics (POSIX vs Windows) are
determined by the evaluator's `path_format` configuration, not by the Python path object.

#### Static Type Checking via Unresolved Values

Static type checking is performed by evaluating expressions with `unresolved[T]` values
in a regular `SymbolTable`. For symbols whose concrete values are not yet available, the caller
places `ExprValue.unresolved(T)` in the symbol table, where `T` is the declared type. The
expression is then evaluated normally — operations on unresolved values propagate the `unresolved`
type through the expression. If evaluation succeeds, the result is an `unresolved[T]` value where
`T` is the inferred result type. If it fails, a type error is reported.

```python
# Type check a host-context expression at submission time
values = SymbolTable({"Param.Count": ExprValue.unresolved(ExprType.INT)})
result = evaluate_expression("Param.Count + 1", values=values)
# result.type == unresolved[int] — type checking succeeded, result type is int
```

This approach unifies type checking and evaluation into a single mechanism, using the same
evaluator for both concrete and type-level evaluation. It is effective because the expression
language is side-effect free — evaluating with placeholder values cannot cause any observable
changes, so it is always safe to evaluate for type checking alone. Because parts of expressions
that involve only concrete values are fully evaluated even when other parts are unresolved, this
catches many errors during template validation — before parameter values are even selected.

**Conditional Expressions with Unknown Conditions:**

When the condition of an `if`/`else` expression evaluates to `unresolved[bool]`, the evaluator
does not know which branch will be taken at runtime. Both branches are evaluated:

- If both branches succeed, the result is `unresolved[T | S]` where `T` and `S` are the result
  types of the two branches (since either could be the runtime result).
- If one branch succeeds and the other fails, the result is the type from the succeeding
  branch (wrapped in `unresolved` since the condition is unresolved). The failing branch's error
  is suppressed — that branch would always fail at runtime, so it can never produce a value.
- If both branches fail, evaluation fails with an error describing both failures.

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

### Parsing and Evaluation

#### parse_expression

Parse an expression string and return a parsed representation with symbol references.

```
def parse_expression(
    expr: str,
) -> ParsedExpression
```

- **expr**: The expression string to parse.
- **Returns**: A `ParsedExpression` object with the AST and set of accessed symbols.
- **Raises**: `ExpressionError` if the expression has a syntax error.

#### ParsedExpression

A parsed expression that can be evaluated and inspected.

```
class ParsedExpression:
    expr: str                     # The original expression string
    accessed_symbols: set[str]    # Set of symbol names referenced
    called_functions: set[str]    # Set of function/method names called (e.g., {"upper", "len"})
    peak_memory_usage: int        # Peak memory usage in bytes during last evaluate() call

    def evaluate(
        self,
        *,
        values: SymbolTable = None,
        library: FunctionLibrary = None,
        target_type: ExprType = None,
        path_format: PathFormat = None
    ) -> ExprValue
```

The `accessed_symbols` set contains the external symbols referenced by the expression as
full dotted paths including properties (e.g., `Param.File.stem` collects `{"Param.File.stem"}`).

The `called_functions` set enables static analysis to identify which functions are used,
such as detecting calls to `apply_path_mapping()`.

The `peak_memory_usage` attribute is set after each `evaluate()` call and contains the
peak memory usage in bytes during that evaluation.

Static type checking is performed by calling `evaluate()` with `unresolved[T]` values in the
symbol table (see [Static Type Checking via Unresolved Values](#static-type-checking-via-unresolved-values)).
The result type of the expression can be inspected from the returned `ExprValue`'s type.

#### evaluate_expression

Parse and evaluate an expression in one step.

```
def evaluate_expression(
    expr: str,
    *,
    values: SymbolTable = None,
    library: FunctionLibrary = None,
    target_type: ExprType = None,
    memory_limit: int = None,
    operation_limit: int = None,
    path_format: PathFormat = None
) -> ExprValue
```

- **expr**: The expression string to evaluate.
- **values**: Symbol table with variable bindings.
- **library**: Function library (uses default if not provided).
- **target_type**: Optional expected result type for coercion (can be `any` or union of types).
- **memory_limit**: Maximum memory (bytes) for intermediate values. Default: 100 million bytes.
- **operation_limit**: Maximum number of operations. Default: 10 million. Each function call
  counts as 1 operation, and iterating through a list adds the number of elements.
- **path_format**: Output format for `path` type values. See [Path Format](#path-format) below.
- **Returns**: The result `ExprValue`.
- **Raises**: `ExpressionError` if the expression is invalid or evaluation fails.

Peak memory usage during evaluation is available via `ParsedExpression.peak_memory_usage`
after calling `evaluate()`. Operation count is available via `ParsedExpression.operation_count`.

#### Path Format

The `path_format` parameter controls the behavior of the `path` type during evaluation:

- **`PathFormat.POSIX`**: The `path` type behaves like Python's `PurePosixPath` class.
  Use this for TEMPLATE scope contexts to ensure consistent behavior regardless of
  the submission machine's OS.
- **`PathFormat.WINDOWS`**: The `path` type behaves like Python's `PureWindowsPath` class.
  UNC paths (e.g., `\\server\share`) are preserved as-is.
- **`None`** (default): The `path` type behaves like Python's `PurePath` class,
  using the system's native path semantics. This is appropriate for host contexts
  (SESSION and TASK scopes) where paths should match the worker's OS.

The `path_format` setting only affects filesystem paths. URI paths (those with a `scheme://`
prefix) always use URI-aware parsing with forward-slash separators and no normalization,
regardless of the `path_format` setting. See the [path type description](#121-types) for
details.

### Function Library

#### FunctionLibrary

Registry of functions and operators available in expressions.

```
class FunctionLibrary:
    def register(self, name, param_types, return_type, impl)
    def get_signatures(self, name: str) -> list[FunctionSignature]
    def get_call_return_types(self, name: str, arg_types: list[set[ExprType]]) -> set[ExprType]
    def get_property_type(self, base_type: ExprType, property_name: str) -> ExprType | None
    def with_host_context(self, *, path_mapping_rules=None) -> FunctionLibrary
```

- `get_default_library()` — Returns the standard function library with all built-in functions.
- `get_call_return_types(name, arg_types)` — Returns possible return types for a function call
  given argument type sets. Used for static type checking.
- `get_property_type(base_type, property_name)` — Returns the type of a property access, or None
  if the property doesn't exist for the base type. Used for static type checking.
- `with_host_context()` — Returns a copy of the library with host-only functions like
  `apply_path_mapping()` enabled. Used for type checking and evaluation in host contexts.

#### FunctionSignature

A function signature with parameter types and return type.

```
class FunctionSignature:
    param_types: list[ExprType]
    return_type: ExprType
    impl: Callable[..., ExprValue]
```

### Errors

#### ExpressionError

Base exception for expression parsing and evaluation errors. Includes formatted error messages
with source location and caret pointers when available.

#### ExprTypeError

Subclass of `ExpressionError` for type-related errors during evaluation.

### Path Mapping

#### PathMappingRule

A rule for mapping paths from one location to another, used by `apply_path_mapping()`.

```
class PathMappingRule:
    source_path_format: PathFormat    # POSIX, WINDOWS, or URI
    source_path: PurePath | str       # PurePath for POSIX/WINDOWS, str for URI
    destination_path: PurePath        # The destination path prefix to substitute

    @staticmethod
    def from_dict(rule: dict[str, str]) -> PathMappingRule
    def to_dict(self) -> dict[str, str]
    def apply(self, *, path: str) -> tuple[bool, str]
```

For `POSIX` and `WINDOWS` rules, matching uses `PurePath.is_relative_to()`. For `URI` rules,
matching uses string prefix comparison on path boundaries — the input must start with the
source URI and the next character (if any) must be `/`. This preserves the exact URI content
without normalization.

#### PathFormat

Enumeration of path formats: `POSIX`, `WINDOWS`, or `URI`. The `URI` format requires the
EXPR extension and is used for mapping URI prefixes (e.g. `s3://bucket/assets`) to local
filesystem paths.

---

## 1. Language

### 1.1. Extended Format String Grammar

When the `EXPR` extension is enabled, the grammar for `<StringInterpExpr>` within
[Format Strings](2023-09-Template-Schemas#73-format-strings) is extended from:

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
<PrimaryExpr>       ::= <ValueReference> | <Literal> | <ListExpr> | <ListComp>
                       | "(" <ConditionalExpr> ")"
<ValueReference>    ::= <Name>
<Name>              ::= <Name> "." <Identifier> | <Identifier>
```

#### 1.1.1. Literals

```bnf
<Literal>           ::= <IntLiteral> | <FloatLiteral> | <StringLiteral>
                       | <BoolLiteral> | <NoneLiteral>
<IntLiteral>        ::= <DecimalInt> | <HexInt> | <OctalInt> | <BinaryInt>
<DecimalInt>        ::= [0-9] ("_"? [0-9])*
<HexInt>            ::= "0" ("x" | "X") "_"? [0-9a-fA-F] ("_"? [0-9a-fA-F])*
<OctalInt>          ::= "0" ("o" | "O") "_"? [0-7] ("_"? [0-7])*
<BinaryInt>         ::= "0" ("b" | "B") "_"? [01] ("_"? [01])*
<FloatLiteral>      ::= <PointFloat> | <ExponentFloat>
<PointFloat>        ::= <DecimalInt>? "." [0-9] ("_"? [0-9])* <Exponent>?
                       | <DecimalInt> "." <Exponent>?
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
```

#### 1.1.2. List Expressions

```bnf
<ListExpr>          ::= "[" (<ConditionalExpr> ("," <ConditionalExpr>)* ","?)? "]"
<ListComp>          ::= "[" <ConditionalExpr> "for" <Identifier> "in" <ConditionalExpr>
                            ("if" <ConditionalExpr>)? "]"
```

#### 1.1.3. Contextual Keywords

Keywords (`if`, `else`, `and`, `or`, `not`, `for`, `in`, `True`, `False`, `None`) are contextual.
They are only recognized as keywords in their syntactic positions, not as attribute names
following `.` in a `<Name>`. This ensures backward compatibility so that expressions like
`Param.if` or `Param.True` remain valid.

#### 1.1.4. JSON/YAML-Compatible Literals

The following aliases are accepted to reduce friction with the surrounding JSON/YAML template syntax:

|**Alias**|**Equivalent**|
|---|---|
|`null`|`None`|
|`true`|`True`|
|`false`|`False`|

#### 1.1.5. String Literal Formats

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

#### 1.1.6. Numeric Literal Formats

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
Use the `0o` prefix for octal integers (e.g., `0o7` or `0o123`). The literal `0` and `00` are
valid as they unambiguously represent zero.

#### 1.1.7. Implicit Line Continuation

Expressions can span multiple lines without any special continuation syntax.

```yaml
args:
  - |-
    {{ [
        Param.OutputDir / Param.FilePattern.with_number(frame)
        for frame in Task.Param.Frame
    ] }}
```

### 1.2. Type System

#### 1.2.1. Expression Types

| Type | Description |
|------|-------------|
| `bool` | Boolean values (`True`, `true`, `False`, or `false`) |
| `int` | 64-bit signed integer values (−2⁶³ to 2⁶³−1) |
| `float` | Floating-point values (64-bit IEEE) |
| `string` | String values |
| `path` | Filesystem path values |
| `range_expr` | Range expression string conforming to the [`<IntRangeExpr>`](2023-09-Template-Schemas#34111-intrangeexpr) grammar |
| `T?` | Optional type: the value is `T` or `None`/`null` |
| `nulltype` | The null type; its value can only be `None`/`null` |
| `list[T]` | Ordered list of values of type `T` |
| `list[nulltype]` | Empty list `[]`, compatible with any `list[T]` |
| `S \| T` | Union type: the value may be either `S` or `T` |
| `unresolved[T]` | Value not yet resolved, but satisfies constraint `T` (type-checking only) |

The `path` type can have either POSIX or Windows path semantics depending on the evaluation
context. This affects path separator handling (`/` vs `\`) and case sensitivity. In TEMPLATE
scope contexts, POSIX semantics are used for consistency. In host contexts (SESSION and TASK
scopes), the semantics match the host's operating system.

**URI paths**: When a `path` value contains a URI (detected by a `scheme://` prefix matching
the pattern `^[a-zA-Z][a-zA-Z0-9+.-]*://`), path operations use URI-aware string parsing
instead of filesystem path semantics. The scheme and authority portion (everything up to the
path, e.g. `s3://my-bucket`) is preserved as an opaque prefix, and the path portion uses
forward-slash separators without any normalization — consecutive slashes, `.`, and `..`
segments are preserved verbatim. This is necessary because URI path components (such as S3
object keys) are opaque identifiers where `a//b` and `a/b` may refer to different resources.
The evaluator's `path_format` setting does not affect URI paths.

Constraints on `T` in `list[T]`:

1. `T` cannot be `S?`. A `None`/`null` value inside a list literal is an error.
2. `T` can be `list[S]`, but cannot be nested a third time (`S` cannot be `list[U]`).

#### 1.2.2. Built-in Symbol Types

Expressions have access to symbols provided by the runtime context. The expression type of each
symbol corresponds to its declared type.

##### Job Parameter Types

Job parameters defined in `parameterDefinitions` are available via `Param.<name>` and
`RawParam.<name>`:

| Parameter Type | `Param.<name>` Type | `RawParam.<name>` Type |
|----------------|---------------------|------------------------|
| `STRING` | `string` | `string` |
| `INT` | `int` | `int` |
| `FLOAT` | `float` | `float` |
| `PATH` | `path` | `string` |
| `BOOL` | `bool` | `bool` |
| `RANGE_EXPR` | `range_expr` | `range_expr` |
| `LIST[STRING]` | `list[string]` | `list[string]` |
| `LIST[INT]` | `list[int]` | `list[int]` |
| `LIST[FLOAT]` | `list[float]` | `list[float]` |
| `LIST[PATH]` | `list[path]` | `list[string]` |
| `LIST[BOOL]` | `list[bool]` | `list[bool]` |
| `LIST[LIST[INT]]` | `list[list[int]]` | `list[list[int]]` |

The `BOOL`, `RANGE_EXPR`, and `LIST[*]` parameter types are defined in the
[Template Schemas](2023-09-Template-Schemas#2-jobparameterdefinition) as part of the `EXPR` extension.

For `PATH` parameters, `Param.<name>` has type `path` with path mapping rules applied, while
`RawParam.<name>` has type `string` containing the original unmapped value. The raw value is
a string because it may be a path for a different operating system that cannot be parsed as
a local path. Similarly for `LIST[PATH]`, `Param.<name>` is `list[path]` while `RawParam.<name>`
is `list[string]`.

PATH parameter values may be URIs (e.g. `s3://bucket/key`). URI values are not subject to
relative path resolution during job parameter preprocessing — they pass through unchanged.
If no path mapping rule matches a URI, `Param.<name>` retains the original URI as a `path`
value with URI-aware semantics (see [path type description](#121-types)).

##### Task Parameter Types

Task parameters defined in `taskParameterDefinitions` are available via `Task.Param.<name>`
and `Task.RawParam.<name>`:

| Task Parameter Type | Expression Type |
|---------------------|-----------------|
| `INT` | `int` |
| `FLOAT` | `float` |
| `STRING` | `string` |
| `PATH` | `path` |
| `CHUNK[INT]` | `range_expr` |

Note: `CHUNK[INT]` produces a `range_expr` type, not `list[int]`, enabling efficient
representation of frame ranges. Use `list(Task.Param.Frame)` to convert to a list if needed.

##### Session Symbols

| Symbol | Type | Description |
|--------|------|-------------|
| `Job.Name` | `string` | The resolved job name |
| `Step.Name` | `string` | The name of the current step |
| `Session.WorkingDirectory` | `path` | The session's temporary working directory |
| `Session.PathMappingRulesFile` | `path` | Path to the JSON file containing path mapping rules |
| `Session.HasPathMappingRules` | `bool` | Whether path mapping rules are available |

##### Embedded File Symbols

| Symbol | Type | Description |
|--------|------|-------------|
| `Task.File.<name>` | `path` | Location of the embedded file within a Step Script |
| `Env.File.<name>` | `path` | Location of the embedded file within an Environment |

#### 1.2.3. Implicit Type Coercion

As a glue expression language intended for convenience, implicit non-destructive type
coercion is performed where the intent is obvious. The following implicit conversions are supported:

- `int` → `float` when the target types do not include `int`
- `path` → `string` when the target types do not include `path`
- `range_expr` → `string` when the target types do not include `range_expr` (produces canonical form like `"1-5"`)
- `range_expr` → `list[int]` when the target types include `list[int]` but not `range_expr`
- `list[T]` → `list[U]` when each element `T` can be coerced to `U` (e.g., `list[path]` → `list[string]`)
- `list[nulltype]` → `list[T]` for any `T` (empty list literal is compatible with any list type)
- Any scalar value when the target types have a single scalar type. The value is coerced
  non-destructively to that type:
  - `bool`/`int`/`float`/`path` → `string`
  - `string` → `path`
  - `float`/`string` → `int` (error if value cannot be represented exactly, e.g. `3.75`, `""`, `"3.1"`)
  - `int`/`string` → `float` (error if string cannot be parsed, e.g. `""`, `"nothing"`)
- `[v1, v2, ...]` any values when the target types have a single `list` type. Every value is
  coerced non-destructively to `T` where that type is `list[T]`. This applies recursively for nested lists.

#### 1.2.4. Method Call Coercion Restriction

This specification uses uniform function call syntax (UFCS) to support method calls on types (see
[section 1.3.3](#133-uniform-function-call-syntax)). When calling a function as a method,
implicit type coercion does not apply to the first parameter (the receiver). This ensures type
safety for method-style calls.

```yaml
# Function call - coercion applies to all arguments
startswith(path('/foo/bar'), '/foo')  # OK: path coerced to string

# Method call - no coercion on receiver
path('/foo/bar').startswith('/foo')   # ERROR: no startswith(path, string) signature
'/foo/bar'.startswith('/foo')         # OK: receiver is already string
```

Other parameters in a method call are still subject to normal implicit coercion rules.

#### 1.2.5. Cross-Type Equality Comparison

Equality (`==`) and inequality (`!=`) operators handle cross-type comparisons as follows:

- `string` vs `path`: The path is converted to string for comparison
- `int` vs `float`: Numeric comparison (e.g., `5 == 5.0` is `true`)
- `list` vs `range_expr`: The range_expr is expanded and compared element-by-element
- `string` vs (`int` | `float`): Always unequal (e.g., `"5" == 5` is `false`)
- `bool` vs any non-`bool`: Always unequal (e.g., `true == 1` is `false`)
- scalar vs `list`: Always unequal (e.g., `1 == [1]` is `false`)
- Other cross-type comparisons: Always unequal

List equality is recursive: two lists are equal if they have the same length and all
corresponding elements are equal.

List ordering (`<`, `<=`, `>`, `>=`) uses lexicographic comparison: elements are compared
pairwise from the start, and the first unequal pair determines the result. If all compared
elements are equal, the shorter list is considered less than the longer one.

#### 1.2.6. List Literal Type Inference

List literals infer their element type from context and contents.

With a target type context containing exactly one `list[T]` type, elements are coerced
non-destructively to `T`.

Without a target type context:

1. If all elements have the same type `T`, the result is `list[T]`.
2. If elements are a mix of `int` and `float`, the result is `list[float]`.
3. If elements are a mix of `path` and `string`, the result is `list[string]`.
4. If elements are `list[int]` and `list[float]`, the result is `list[list[float]]`.
5. If elements are `list[path]` and `list[string]`, the result is `list[list[string]]`.
6. The empty list `[]` evaluates to `list[nulltype]`, which is implicitly convertible to `list[T]` for any `T`.
7. If elements have incompatible types (e.g., `int` and `string`), evaluation fails with an error.

A `null`/`None` value cannot be an element of a list literal. Including `null` in a list is always an error.

### 1.3. Evaluation Semantics

#### 1.3.1. Target Type Evaluation

Expressions are evaluated with respect to a target type that represents the type(s) expected
by the calling context. The target type guides implicit type coercion (see
[section 1.2.3](#123-implicit-type-coercion)) and list literal type inference (see
[section 1.2.6](#126-list-literal-type-inference)). When the target type is `T`, the expression
must produce a value of type `T` or a type that can be implicitly coerced to `T`. When the
target type is `T?`, the expression may also produce `None`/`null`.

The target type is a statement about the expression's *result*: it guides
which coercions are applied to values, but it never changes what the
expression computes. Operands of operators, subscript receivers and indices,
and function arguments are evaluated without inheriting the caller's target
(see RFC 0005 §"Target Type Propagation Rules" for the per-node rules), and
function overloads are selected by the argument types alone — a function's
return type and the caller's target play no part in selecting the
implementation. For example, `sorted([10, 2])` sorts numerically regardless
of the target type; a `list[string]` target coerces the sorted result to
`["2", "10"]` rather than coercing the input and sorting lexicographically.

The expression language does not define how target types are determined — that is the
responsibility of the embedding context. [Section 1.3.2](#132-evaluation-within-template-schemas)
defines the target type rules for the [Template Schemas](2023-09-Template-Schemas).

#### 1.3.2. Evaluation Within Template Schemas

When expressions are used within the [Template Schemas](2023-09-Template-Schemas), the target
type is determined by the schema context in which the expression appears:

- For a required field of type `T`, the target type is `T`.
- For an optional field of type `T`, the target type is `T?`. If the expression evaluates
  to `None`/`null`, the field is omitted as if it were not specified.
- For list items (e.g., in `args`), the target type is `T? | list[T]` where `T` is
  the item type. This enables three behaviors:
  1. If the result is a value of type `T`, it is added as a single item.
  2. If the result is `None`/`null`, the item is skipped and the list is one shorter.
  3. If the result is a `list[T]`, the list is flattened inline.

  For example:

  ```yaml
  args:
    - "--input"
    - "{{Param.InputFile}}"
    - "{{ '--verbose' if Param.Verbose else null }}"  # Dropped when false
    - "{{ ['--quality', Param.Quality] if Param.Quality > 0 else null }}"  # Flattened or dropped
  ```

When a format string is exactly `"{{<expr>}}"` with no surrounding text, the target type is
inherited from the field context — the format string is transparent and the expression can
produce any type the field accepts. If the expression result does not match the target type,
non-destructive coercion is attempted (see [section 1.2.3](#123-implicit-type-coercion)).
If coercion fails, evaluation produces an error.

When a format string contains text surrounding the expression (e.g., `"The {{<expr>}} value."`),
the overall result is a string. Each interpolated expression is evaluated without type
constraints to obtain its natural result, then converted to a string. A `None`/`null` result
is treated as the empty string. This allows any expression result to be embedded in a format
string:

- `"Items: {{ [1, 2, 3] }}"` produces `"Items: [1, 2, 3]"`
- `"Count: {{ len(myList) }}"` produces `"Count: 5"`

#### 1.3.3. Uniform Function Call Syntax

Functions and properties can be accessed using method syntax:

- For any function `f(x, ...)` where `x` has type `T`, the expression `x.f(...)` is
  equivalent to `f(x, ...)`.
- All operators are defined by functions like `__add__` for the `+` operator, using the
  same double-underscore names as Python.
- Properties like `x.p` are defined using the naming convention `__property_p__`.

This enables chaining like `Param.Name.upper().strip()` instead of `strip(upper(Param.Name))`,
and allows properties like `Param.File.stem` to be defined uniformly alongside functions.

Note: The `__*__` names are specification conventions and are not directly callable.

#### 1.3.4. Float Value Pass-Through

When a float value is only copied without modification, the original string representation
is preserved in output string interpolation. When an operation is performed on a float value,
it becomes a 64-bit IEEE floating point number, and string interpolation uses the shortest
decimal string representation.

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

#### 1.3.5. Conditional Expression Semantics

The conditional expression `<true_value> if <condition> else <false_value>`:

1. Evaluates `<condition>` first. The `<condition>` must be a `bool`; there is no "truthy" concept.
2. If `<condition>` is `True`, evaluates and returns `<true_value>`.
3. Otherwise, evaluates and returns `<false_value>`.

#### 1.3.6. Chained Comparisons

Like Python, chained comparisons are supported. The expression `1 < 2 < 3` is equivalent
to `1 < 2 and 2 < 3`, with each intermediate value evaluated only once.

#### 1.3.7. List Comprehensions

Simple list comprehensions are supported for transforming and filtering lists:

```
[expr for var in iterable]
[expr for var in iterable if condition]
```

The loop variable (`var`) must be a `<UserIdentifier>`: it must start with a lowercase letter
or underscore, followed by alphanumeric characters or underscores. This ensures loop variables
cannot shadow spec-defined symbols like `Param` or `Task`. A loop variable that shadows an
existing binding is an error.

Python's nested comprehension syntax is not supported.

Examples:
- `[['-e', e] for e in Task.Environment]` transforms `["A=1", "B=2"]` into
  `[["-e", "A=1"], ["-e", "B=2"]]`.
- `flatten([['-e', e] for e in Task.Environment])` transforms `["A=1", "B=2"]` into
  `["-e", "A=1", "-e", "B=2"]`, suitable for command `args`.
- `[x for x in Param.Values if x > 0]` filters to only positive values.

#### 1.3.8. Slicing

Slicing extracts a subset of elements from lists, strings, or range expressions using Python-style
slice notation `[start:stop:step]`. All three components are optional:

- `start`: Starting index (inclusive), defaults to 0 (or end if step is negative)
- `stop`: Ending index (exclusive), defaults to length (or -length-1 if step is negative)
- `step`: Step between elements, defaults to 1

Negative indices count from the end: `-1` is the last element, `-2` is second-to-last, etc.

| Expression | Description |
|------------|-------------|
| `v[1:4]` | Elements at indices 1, 2, 3 |
| `v[:3]` | First 3 elements |
| `v[2:]` | All elements from index 2 to end |
| `v[::2]` | Every other element |
| `v[::-1]` | Reversed |
| `v[-3:]` | Last 3 elements |

Note: The `path` type does not support subscript or slice operations. Use `p.parts` to get
path components as a list, which can then be sliced.

#### 1.3.9. Memory-Bounded Evaluation

As described in [Design Constraints](#design-constraints), expression evaluation must operate within
bounded memory. Implementations accept an optional `memory_limit` parameter (default: 100 million bytes recommended).
During evaluation, the evaluator tracks the memory size of live values — incrementing when values are
created, decrementing when intermediate values are consumed. If current memory exceeds the limit,
evaluation fails with an error.

Value size calculations are implementation-defined. Implementations should try to match the
actual memory usage of each value as closely as practical in their language and runtime.

#### 1.3.10. Operation-Bounded Evaluation

As described in [Design Constraints](#design-constraints), expression evaluation must operate within
a bounded number of operations. Implementations accept an optional `operation_limit` parameter
(default: 10 million recommended). During evaluation, the evaluator maintains a running operation
count. If the count exceeds the limit, evaluation fails with an error.

**Operation counting rules:**

1. Every function call counts as 1 operation. This includes operators (which are transformed to
   function calls), property accesses, and explicit function calls.

2. When a function or the evaluator iterates through every element of a list, the number of
   elements is added to the operation count. This applies to list comprehensions, and built-in
   functions that iterate lists such as `sum()`, `min()`, `max()`, `any()`, `all()`, `sorted()`,
   `reversed()`, `flatten()`, `join()`, `contains()`, `range()`, `repr_sh()`, `repr_py()`,
   `repr_json()`, `repr_pwsh()`, `repr_cmd()`, list concatenation (`+`), list repetition (`*`),
   and list/range equality comparisons.

3. When a function processes a string or path value, the length of the value divided by 256
   (rounded up) is added to the operation count. This applies to functions that do work roughly
   proportional to the string length, such as `upper()`, `lower()`, `replace()`, `split()`,
   `join()`, `strip()`, regex functions, `repr_sh()`, string concatenation (`+`), string
   repetition (`*`), and similar. Simple lookups like `len()` that do not process the string
   content do not add to the count.

#### 1.3.11. Error Handling

Expression evaluation errors result in a job failure with a descriptive error message. Errors include:

- Type errors (e.g., adding string to int)
- Division by zero
- Index out of bounds
- Unknown function or variable reference
- Syntax errors
- Memory limit exceeded
- Operation limit exceeded

#### 1.3.12. Task Parameter Range Field Extensions

When the `EXPR` extension is enabled, the `range` field for task parameter
definitions is extended to accept a `<ListExpressionString>` in addition to list literals.
For INT, the `RangeString` is also extended — since it is a format string, it can now contain
an expression that evaluates to either a range expression string or a `list[int]`:

| Parameter Type | Original `range` Type | Extended `range` Type |
|---------------|----------------------|----------------------|
| INT | `list[int \| FormatString] \| RangeString` | (unchanged, but see `RangeString` note below) |
| FLOAT | `list[Decimal \| FormatString]` | `list[Decimal \| FormatString] \| ListExpressionString` |
| STRING | `list[FormatString]` | `list[FormatString] \| ListExpressionString` |
| PATH | `list[FormatString]` | `list[FormatString] \| ListExpressionString` |

Where `RangeString` is a format string that, with EXPR enabled, can contain an expression
evaluating to a `range_expr` or `list[int]` in addition to the original `<IntRangeExpr>` grammar.

A `<ListExpressionString>` is a format string containing an expression that evaluates to a list:

```yaml
steps:
  - name: Process
    parameterSpace:
      taskParameterDefinitions:
        - name: Factor
          type: FLOAT
          range: "{{ [Param.Scale * 2, Param.Scale + 0.5] }}"
```

---

## 2. Function Library

All operators and built-in functions are specified using type signatures. Operators use Python's
double-underscore naming convention (e.g., `__add__` for `+`). Through uniform function call syntax
(see [section 1.3.3](#133-uniform-function-call-syntax)), any function `f(x, ...)` can also be called
as `x.f(...)`, and properties `x.p` are defined as `__property_p__(x)`.

### 2.1. Operators

#### 2.1.1. Arithmetic Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: int, b: int) -> int` | `a + b` addition |
| `__add__(a: float, b: float) -> float` | `a + b` addition |
| `__sub__(a: int, b: int) -> int` | `a - b` subtraction |
| `__sub__(a: float, b: float) -> float` | `a - b` subtraction |
| `__mul__(a: int, b: int) -> int` | `a * b` multiplication |
| `__mul__(a: float, b: float) -> float` | `a * b` multiplication |
| `__truediv__(a: int, b: int) -> float` | `a / b` division (see also [Path Operators](#215-path-operators)) |
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

The `//` and `%` operators use floored division (rounding toward negative infinity), matching
Python semantics. This differs from C/Rust/JavaScript which use truncated division (rounding
toward zero). For example, `-7 % 3` is `2` (not `-1`) and `-7 // 3` is `-3` (not `-2`).

Raising zero to a negative power (e.g., `0 ** -1`) is an error. Raising a negative number to
a fractional power (e.g., `(-2.0) ** 0.5`) is an error (would produce a complex number).

#### 2.1.2. String Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: string, b: string) -> string` | `a + b` concatenation |
| `__add__(a: string, b: range_expr) -> string` | `a + b` concatenation (range_expr converted to canonical string form) |
| `__add__(a: range_expr, b: string) -> string` | `a + b` concatenation (range_expr converted to canonical string form) |
| `__mul__(s: string, n: int) -> string` | `s * n` repetition |
| `__contains__(a: string, b: string) -> bool` | `b in a` substring test |
| `__not_contains__(a: string, b: string) -> bool` | `b not in a` substring test |

#### 2.1.3. List Operators

| Signature | Description |
|-----------|-------------|
| `__add__(a: list[T1], b: list[T2]) -> list[T3]` | `a + b` concatenation (see type coercion below) |
| `__add__(a: range_expr, b: list[T1]) -> list[T2]` | `a + b` concatenation (range_expr treated as list[int]) |
| `__add__(a: list[T1], b: range_expr) -> list[T2]` | `a + b` concatenation (range_expr treated as list[int]) |
| `__add__(a: range_expr, b: range_expr) -> list[int]` | `a + b` concatenation |
| `__mul__(a: list[T], n: int) -> list[T]` | `a * n` repetition |
| `__contains__(list: list[T], item: T) -> bool` | `item in list` membership test |
| `__contains__(r: range_expr, item: int) -> bool` | `item in r` membership test |
| `__not_contains__(list: list[T], item: T) -> bool` | `item not in list` membership test |
| `__not_contains__(r: range_expr, item: int) -> bool` | `item not in r` membership test |

When concatenating lists with different element types, the result type is determined by
finding a common type:

- `list[int] + list[float]` → `list[float]` (int elements coerced to float)
- `list[path] + list[string]` → `list[string]` (path elements coerced to string)
- `list[nulltype] + list[T]` → `list[T]` (empty list takes the other's type)
- `list[int] + range_expr` → `list[int]` (range_expr treated as `list[int]`)
- `range_expr + list[T]` → `list[T]` (range_expr treated as `list[int]`, then coerced if needed)
- `range_expr + range_expr` → `list[int]`
- Concatenation of incompatible list types (e.g., `list[string] + list[int]`) is an error.

#### 2.1.4. Comparison Operators

| Signature | Description |
|-----------|-------------|
| `__eq__(a: T1, b: T2) -> bool` | `a == b` equal |
| `__ne__(a: T1, b: T2) -> bool` | `a != b` not equal |
| `__lt__(a: T1, b: T2) -> bool` | `a < b` less than |
| `__gt__(a: T1, b: T2) -> bool` | `a > b` greater than |
| `__le__(a: T1, b: T2) -> bool` | `a <= b` less than or equal |
| `__ge__(a: T1, b: T2) -> bool` | `a >= b` greater than or equal |

Equality operators work on all types. `T1` and `T2` may differ — see
[section 1.2.5](#125-cross-type-equality-comparison) for cross-type comparison rules.

Ordering operators work on `int`, `float`, `string`, `path`, and `bool` types. `T1` and `T2`
may differ for compatible pairs (`int`/`float` and `string`/`path`); comparing other
cross-type pairs is an error. Bool comparison treats `False < True`.

#### 2.1.5. Path Operators

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
```

The `+` operator appends a string directly to the path (no separator):

```yaml
{{ Param.OutputDir / Param.InputFile.stem + '_converted.png' }}
```

#### 2.1.6. Logical Operators

| Signature | Description |
|-----------|-------------|
| `a and b` | If `a` is `null` or `false`, return `a`; otherwise evaluate and return `b` (short-circuit) |
| `a or b` | If `a` is `null` or `false`, evaluate and return `b`; otherwise return `a` (short-circuit) |
| `__not__(a: bool) -> bool` | `not a` logical NOT |

The `and` and `or` operators are value-returning: they return one of their operands, not
necessarily a `bool`. Only `null` and `false` are considered falsy — unlike Python, values
like `0`, `""`, and `[]` are not falsy. This makes `or` useful as a null-coalescing operator:

```python
Param.X or "fallback"              # returns Param.X if not null/false, else "fallback"
Param.X and Param.X.stem           # returns null/false if X is null/false, else X.stem
Param.Mode in ["a","b"] or fail("bad mode")  # validation pattern
```

This behavior is similar to Ruby's `||`/`&&` operators (where only `nil` and `false` are
falsy), and serves a similar role to null-coalescing operators in other languages: C# (`??`),
JavaScript (`??`), Kotlin (`?:`), and Swift (`??`).

Note: `not` remains strictly boolean — it requires a `bool` operand and returns `bool`.

#### 2.1.7. Subscript Operator

| Signature | Description |
|-----------|-------------|
| `__getitem__(list: list[T], index: int) -> T` | `list[index]` access by zero-based index |
| `__getitem__(r: range_expr, index: int) -> int` | `r[index]` access by zero-based index |
| `__getitem__(s: string, index: int) -> string` | `s[index]` access single character by index |

Negative indices count from the end: `list[-1]` is the last element. Index out of bounds is an error.

Note: Indexing a `range_expr` treats it as an integer list, not as a string. `r[0]` returns
the first integer in the range, not the first character of the range string.

#### 2.1.8. Slice Operator

| Signature | Description |
|-----------|-------------|
| `__getitem__(list: list[T], start: int?, stop: int?, step: int?) -> list[T]` | `list[start:stop:step]` |
| `__getitem__(r: range_expr, start: int?, stop: int?, step: int?) -> range_expr \| list[int]` | `r[start:stop:step]` |
| `__getitem__(s: string, start: int?, stop: int?, step: int?) -> string` | `s[start:stop:step]` |

Slice semantics follow Python. Out-of-bounds indices are clamped to valid range (no error).
A step of 0 is an error.

Note: Slicing a `range_expr` treats it as an integer list, not as a string. `r[1:3]` returns
the second and third integers in the range, not a substring of the range string. With a positive
step (including the default step of 1), the result is a `range_expr`. With a negative step
(e.g., `r[::-1]`), the result is a `list[int]` because `range_expr` cannot represent descending
sequences.

### 2.2. Built-in Functions

#### 2.2.1. General Functions

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
| `int(value: int \| float \| string) -> int` | Convert to integer (error if not exact) |
| `float(value: int \| float \| string) -> float` | Convert to float |
| `list(value: range_expr) -> list[int]` | Convert range expression to list |
| `range_expr(s: string) -> range_expr` | Parse string as range expression (e.g., `"1-10"`, `"1,3,5-7"`) |
| `range_expr(l: list[int]) -> range_expr` | Convert integer list to range expression |
| `fail(message: string) -> noreturn` | Fail with error message |

Note: `int(3.75)` is an error. Use `floor`, `ceil`, or `round` for lossy conversions.

Note: `bool()` string conversion accepts the following case-insensitive values:
`"1"`, `"true"`, `"on"`, `"yes"` become `true`; `"0"`, `"false"`, `"off"`, `"no"` become `false`.
All other string values are rejected with an error.

Note: Calling `bool()` on `path` or `list[T]` values is an error. This prevents accidental implicit
coercion to bool in conditional contexts. Implementations must raise a clear error message such as
"Cannot convert path to bool" or "Cannot convert list to bool".

Note: `range_expr("")` (empty string) is an error, `range_expr(" ")` (whitespace-only) is an error, and `range_expr([])` (empty list) is also an error.
Range expressions must contain at least one value.

The `fail` function immediately terminates expression evaluation with an error. The `noreturn` type collapses in unions (`T | noreturn` → `T`),
so validation expressions have precise types:

```python
Param.Count > 0 or fail("Count must be positive")
Param.Mode in ["fast", "slow"] or fail("Invalid mode")

# Type is float, not float?
rate = Param.Rate if Param.Rate > 0 else fail("must be positive")
```

#### 2.2.2. Math Functions

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

Note: `round(x, ndigits)` with positive `ndigits` preserves trailing zeros in the decimal
representation. For example, `round(3.5, 2)` produces a value that converts to the string
`"3.50"`, not `"3.5"`. With non-positive `ndigits`, the result is an integer (e.g.,
`round(1234.5, -1)` returns `1230`).

#### 2.2.3. List Functions

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
| `any(values: list[bool]) -> bool` | True if any element is true (false for empty list) |
| `all(values: list[bool]) -> bool` | True if all elements are true (true for empty list) |

Examples:
- `range(5)` returns `[0, 1, 2, 3, 4]`
- `range(1, 5)` returns `[1, 2, 3, 4]`
- `range(0, 10, 2)` returns `[0, 2, 4, 6, 8]`
- `range(5, 0, -1)` returns `[5, 4, 3, 2, 1]`
- `flatten([[1, 2], [3]])` returns `[1, 2, 3]`
- `sorted([3, 1, 2])` returns `[1, 2, 3]`
- `sorted(["b", "a", "c"])` returns `["a", "b", "c"]`
- `reversed([1, 2, 3])` returns `[3, 2, 1]`

#### 2.2.4. String Functions

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
- `zfill(3.14, 8)` returns `"00003.14"`

Note: The `sep` argument to `split` and `rsplit` must be non-empty. An empty separator is an error.
To split a string into individual characters, use `[s[i] for i in range(len(s))]`.

Note: Splitting an empty string returns a list containing one empty string, not an empty list
(e.g., `''.split(',')` returns `['']`). This matches Python's `str.split()` behavior.

Note: The `join` function uses `list.join(sep)` syntax rather than Python's `sep.join(list)`.
This enables natural method chaining like `items.split(';').join(',')`.

Note: Method calls on integer and float literals require parentheses around the literal
(e.g., `(42).zfill(5)` not `42.zfill(5)`) because the parser interprets `42.` as the start
of a float literal.

#### 2.2.5. Regular Expression Functions

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

#### 2.2.6. Script Embedding and Serialization

| Signature | Description |
|-----------|-------------|
| `repr_sh(s: string) -> string` | Shell-escape a string for POSIX shells |
| `repr_sh(p: path) -> string` | Shell-escape a path for POSIX shells |
| `repr_sh(args: list[string]) -> string` | Join list into space-separated shell-escaped strings |
| `repr_sh(args: list[path]) -> string` | Join path list into space-separated shell-escaped strings |
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

`repr_sh` follows the behavior of Python's
[shlex.quote](https://docs.python.org/3/library/shlex.html#shlex.quote) and
[shlex.join](https://docs.python.org/3/library/shlex.html#shlex.join).

`repr_cmd` produces Windows CMD-safe strings suitable for use in `.bat` files.
Strings containing special characters (`& | < > ^ " ( ) % !` or whitespace) are wrapped in
double quotes. Inside double quotes, `^` and `"` are escaped with `^`, `%` is doubled
to `%%` (required for `.bat` file contexts where `%` triggers variable expansion even inside
quotes), and `!` is escaped as `^^!` (required for contexts where `EnableDelayedExpansion` is
active — the `^` must be doubled because `cmd.exe` processes `^` escapes before delayed
expansion). Other special characters are literal within quotes. Newline characters (`\n` and
`\r`) are stripped from the string before quoting, because `cmd.exe` has no escape sequence for
embedding a literal newline in an argument and an unescaped newline inside double quotes would
cause `cmd.exe` to treat the remainder as a new command. Simple strings without special
characters are returned unquoted.

**Limitations of `cmd.exe` quoting.** Unlike POSIX shells and PowerShell, `cmd.exe` does not
support fully general string quoting. Modes such as `EnableDelayedExpansion` change how quoting
and escaping are interpreted, and there is no single escaping strategy that is correct in all
`cmd.exe` configurations simultaneously. `repr_cmd` escapes for default `cmd.exe` parsing rules
as used in `.bat` files, and applies `^^!` escaping for `!` as a best-effort defense against
delayed expansion. The transformations performed by `repr_cmd` do not preserve every input
string in all `cmd.exe` modes. Template authors who need quoting guarantees beyond what
`repr_cmd` provides should use a different script language such as PowerShell or Python, which
have well-defined string escaping.

`repr_pwsh` produces PowerShell literals with proper escaping. Strings and paths are wrapped in
single quotes with embedded single quotes doubled. Booleans become `$true`/`$false`. Lists become
PowerShell array syntax `@(...)`.

`repr_py` follows the behavior of Python's
[repr](https://docs.python.org/3/library/functions.html#repr).

Examples:
- `repr_sh(["echo", "hello world"])` returns `"echo 'hello world'"`
- `repr_cmd("a & b")` returns `"\"a & b\""` (quoted, `&` is literal inside quotes)
- `repr_cmd("a ^ b")` returns `"\"a ^^ b\""` (`^` escaped inside quotes)
- `repr_cmd("hello!")` returns `"\"hello^^!\""` (`!` escaped as `^^!` for the delayed expansion context)
- `repr_cmd("a\nb")` returns `"\"ab\""` (newlines stripped)
- `repr_pwsh(["a", "b"])` returns `@('a', 'b')`
- `repr_py("hello\nworld")` returns `"'hello\\nworld'"`
- `repr_json([1, 2, 3])` returns `"[1, 2, 3]"`

### 2.3. Path Type Properties and Functions

The `path` type represents filesystem paths and URIs, and provides properties and functions
inspired by Python's [pathlib.PurePath](https://docs.python.org/3/library/pathlib.html#pure-paths).
Job parameters of type `PATH` evaluate to the `path` type.

For filesystem paths, the behavior matches `PurePosixPath` or `PureWindowsPath` depending on
the evaluator's `path_format` setting. For URI paths (those with a `scheme://` prefix), the
scheme and authority are preserved as an opaque prefix and the path portion is parsed with
forward slashes and no normalization. See the [path type description](#121-types) for details.

#### 2.3.1. Path Properties

Properties are accessed using dot notation via UFCS.

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

#### 2.3.2. Path Functions

| Signature | Description |
|-----------|-------------|
| `path(s: string) -> path` | Convert string to path |
| `path(parts: list[string]) -> path` | Construct path from components |
| `with_name(p: path, name: string) -> path` | Return path with the filename changed |
| `with_stem(p: path, stem: string) -> path` | Return path with the stem changed |
| `with_suffix(p: path, suffix: string) -> path` | Return path with the suffix changed |
| `with_number(p: path, num: int) -> path` | Return path with the frame number replaced |
| `with_number(s: string, num: int) -> string` | Return string with the frame number replaced |
| `as_posix(p: path) -> string` | Return string with forward slashes |
| `is_absolute(p: path) -> bool` | True if path is absolute. URI paths are always absolute. |
| `is_relative_to(p: path, other: path) -> bool` | True if path is relative to other. For URIs, checks prefix match on the full URI. |
| `relative_to(p: path, other: path) -> path` | Return the relative path from other to p. Error if p is not relative to other. For URIs, strips the matching prefix. |
| `apply_path_mapping(s: string) -> path` | Apply session path mapping rules to a path string |

The `apply_path_mapping` function is only available in `@fmtstring[host]` contexts (evaluated at
runtime on the worker host) where path mapping rules are available. Using it in submission-time
contexts is an error. The input is `string` rather than `path` because path mapping often involves
cross-platform scenarios where the source path may not be valid path syntax on the worker's OS.

##### Frame Number Substitution with `with_number`

The `with_number` function replaces frame number placeholders in path filenames. It recognizes
several common formats:

| Format | Example Input | `with_number(72)` Output |
|--------|---------------|--------------------------|
| Digits | `file_003.exr` | `file_072.exr` |
| Printf `%d` | `file_%d.exr` | `file_72.exr` |
| Printf `%0Nd` | `file_%04d.exr` | `file_0072.exr` |
| Hash padding | `file_####.exr` | `file_0072.exr` |
| Hash padding | `file_######.exr` | `file_000072.exr` |

The function searches the filename stem from the end for these patterns and replaces the last match.
The stem is determined by the last dot in the filename (matching pathlib's `.stem` property), so
`render.0001.exr` has stem `render.0001` and suffix `.exr`.
If the number exceeds the padding width, the full number is used without truncation
(e.g., `file_###.exr` with `with_number(10000)` produces `file_10000.exr`).
If no pattern is found, `_NNNN` (4-digit zero-padded) is appended to the stem.
The maximum padding width is 32 characters; wider printf or hash patterns are an error.

For negative numbers, the sign is included in the output. With digit and hash formats, the sign
precedes the zero-padded digits and counts toward the width (e.g., `file_003.exr` with
`with_number(-1)` produces `file_-01.exr`). With printf formats, standard printf sign handling
applies.

```yaml
{{ Param.OutputPattern.with_number(Task.Param.Frame) }}
```

---

## 3. License

Copyright ©2026 Amazon.com Inc. or Affiliates ("Amazon").

This Agreement sets forth the terms under which Amazon is making the Open Job Description
Specification ("the Specification") available to you.

### 3.1. Copyrights

This Specification is licensed under [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/deed.en).

### 3.2. Patents

Subject to the terms and conditions of this Agreement, Amazon hereby grants to
you a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
(except as stated in this section) patent license to make, have made, use, offer
to sell, sell, import, and otherwise transfer implementations of the
Specification that implement and are compliant with all relevant portions of the
Specification ("Compliant Implementations"). Notwithstanding the foregoing, no
patent license is granted to any technologies that may be necessary to make or
use any product or portion thereof that complies with the Specification but are
not themselves expressly set forth in the Specification.

If you institute patent litigation against any entity (including a cross-claim
or counterclaim in a lawsuit) alleging that Compliant Implementations of the
Specification constitute direct or contributory patent infringement, then any
patent licenses granted to You under this Agreement shall terminate as of the
date such litigation is filed.

### 3.3. Additional Information

For more info see the [LICENSE file].

[LICENSE FILE]: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/LICENSE
