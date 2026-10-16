* Feature Name: json_embedded_files
* Author(s): Stephen Crowe
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/124
* Start Date: 2026-04-07
* Specification Version: 2023-09 extension EXPR
* Accepted On: (pending)

## Summary

This RFC adds a new `type: "JSON"` variant of embedded files where `data` is a structured
object rather than raw text. The runtime resolves format string expressions at the value level
within the parsed data structure, then serializes the result to JSON when writing the file.
This eliminates an entire class of quoting and escaping bugs that arise when parameter values
containing special characters (apostrophes, quotes, colons, etc.) are substituted into
hand-written YAML/JSON text blobs.

## Basic Examples

### Current approach (broken by special characters)

```yaml
embeddedFiles:
  - name: initData
    filename: init-data.yaml
    type: TEXT
    data: |
      scene_file: '{{Param.Cinema4DFile}}'
      output_path: '{{Param.OutputPath}}'
```

If `Param.Cinema4DFile` is `/Users/artist's work/scene.c4d`, the substituted result is:

```yaml
scene_file: '/Users/artist's work/scene.c4d'
```

Broken YAML — the apostrophe terminates the single-quoted string early.

### With `type: JSON` (correct by default)

```yaml
embeddedFiles:
  - name: initData
    filename: init-data.json
    type: JSON
    data:
      scene_file: "{{Param.Cinema4DFile}}"
      output_path: "{{Param.OutputPath}}"
      take: Main
      frames:
        start: "{{Param.FrameStart}}"
        end: "{{Param.FrameEnd}}"
      error_checking: "{{Param.ActivateErrorChecking}}"
```

The runtime parses `data` as a structured object, resolves each format string expression
within the values, then serializes the entire structure to JSON. The JSON serializer handles
all quoting and escaping correctly because substitution happens on the parsed data structure,
not inside a serialized text blob.

The written file `init-data.json` would contain:

```json
{
  "scene_file": "/Users/artist's work/scene.c4d",
  "output_path": "/renders/output",
  "take": "Main",
  "frames": {
    "start": 1,
    "end": 100
  },
  "error_checking": true
}
```

### Nested structures and lists

```yaml
embeddedFiles:
  - name: renderConfig
    filename: config.json
    type: JSON
    data:
      renderer: "{{Param.Renderer}}"
      resolution: ["{{Param.Width}}", "{{Param.Height}}"]
      passes:
        - name: beauty
          enabled: true
        - name: depth
          enabled: "{{Param.EnableDepthPass}}"
```

## Motivation

### The quoting problem

`type: TEXT` embedded files are the primary way Deadline Cloud integrations pass structured
configuration data (init-data, run-data) to adaptors. Template authors write YAML or JSON as
raw text with `{{Param.*}}` placeholders, and the runtime performs text substitution *after*
the template has been parsed. If the substituted value contains characters that break the
quoting chosen at serialization time, the worker gets a parse error.

This issue has caused real bugs:
- [Cinema 4D: Path names with single quotes do not work](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/397)
- The fix required a custom `_yaml_utils.py` module that splits values into "safe for
  yaml_dump" vs "must be unquoted plain scalars" — every plugin would need to replicate this.

Characters that can break TEXT embedded files include: `'`, `"`, `\`, `:`, `#`, `{`, `}`,
`[`, `]`, and various whitespace patterns. File paths on macOS and Windows commonly contain
apostrophes, spaces, and other problematic characters.

### Why `repr_json()` from RFC 0006 isn't sufficient

`repr_json()` can wrap individual values safely — JSON double-quoted strings are valid YAML:

```yaml
data: |
  scene_file: {{repr_json(Param.Cinema4DFile)}}
  output_path: {{repr_json(Param.OutputPath)}}
```

This handles apostrophes, double quotes, backslashes, etc. correctly. But it has two drawbacks:

1. **Opt-in per value** — every template author must remember to wrap every value.
2. **Can only serialize values, not structure** — you're still hand-writing the YAML/JSON
   structure as text and wrapping individual leaf values. The keys, indentation, and colons
   are all unprotected raw text.

## Specification

### 6.2. `<EmbeddedFileJSON>` `@extension EXPR`

Embedding of a JSON file into the template. The `data` provided is a structured object that
is serialized to JSON when written to disk. Format string expressions within the values of
the data structure are resolved prior to serialization.

```
<EmbeddedFileJSON>:
  name: <Identifier>
  type: "JSON"
  filename: <Filename>           # @optional
  data: <JSONData>               # @fmtstring[host]
```

Where:

1. *name* — The name of the embedded file. This value is used in Format String references
   to this file. See: [`<Identifier>`].
2. *type* — The literal `"JSON"`, identifying this as a JSON embedded file.
3. *filename* — The filename for the written file. This must strictly be the basename of the
   filename, and not contain any directory pathing (i.e. `config.json` not `dir/config.json`).
   Defaults to a random filename with a `.json` extension if not provided. See: [`<Filename>`].
4. *data* — A JSON-compatible value (mapping, sequence, or scalar) that is serialized to JSON.
   See: [`<JSONData>`].

The fully-qualified path of the file written by the host can be referenced in format strings
using the same names as `<EmbeddedFileText>`:

1. `Task.File.<name>` — If the embedded file is part of a `<StepScript>` object; or
2. `Env.File.<name>` — If the embedded file is part of an `<Environment>` object.

#### 6.2.1. `<JSONData>`

The `data` property of an `<EmbeddedFileJSON>` is a JSON-compatible value. It may be:

- **Mappings** (objects) with string keys
- **Sequences** (arrays)
- **Scalar values**: strings, integers, floats, booleans, and null

String values within the data structure are [Format Strings] annotated `@fmtstring[host]`.
Non-string scalar values (integers, floats, booleans, null) are preserved as-is in the
serialized output.

##### Format String Resolution in `<JSONData>`

Format string expressions within string values are resolved at task execution time on the
worker host, the same as `@fmtstring[host]` strings in `<EmbeddedFileText>`.

After resolution, the resulting value's type determines its JSON serialization:

| Expression result type | JSON serialization |
|---|---|
| `string` | JSON string |
| `int` | JSON number (integer) |
| `float` | JSON number (floating-point) |
| `bool` | JSON `true` or `false` |
| `path` | JSON string (the path's string representation) |
| `list[T]` | JSON array |
| `nulltype` | JSON `null` |
| `range_expr` | JSON string (the canonical range expression string) |

When a string value in `data` consists entirely of a single format string expression
(e.g., `"{{Param.FrameStart}}"`), the resolved value's native type is used directly.
For example, if `Param.FrameStart` is an `INT` parameter with value `1`, the JSON output
contains the number `1`, not the string `"1"`.

When a string value contains a mix of literal text and expressions (e.g.,
`"frame_{{Param.Frame}}.exr"`), the result is always a JSON string, following the same
rules as format string resolution in `<EmbeddedFileText>`.

When a string value contains no format string expressions, it is serialized as a JSON string
literal.

##### Constraints

1. Mapping keys must be strings and are [Format Strings] annotated `@fmtstring[host]`,
   following the same resolution rules as string values.

##### Serialization

The file is written as UTF-8 encoded JSON ([ECMA-404]). Implementations should produce
compact JSON (no unnecessary whitespace) by default. The output must be valid JSON that
can be parsed by any conforming JSON parser.

### Updated `<EmbeddedFile>` Union

The `<EmbeddedFile>` union type is extended to include the new variant:

```
<EmbeddedFile> ::= <EmbeddedFileText> |
                   <EmbeddedFileJSON>    # @extension EXPR
```

## Design Choice Rationale

### Why JSON and not YAML output

JSON was chosen as the serialization format because:

1. **JSON is a subset of YAML 1.2** — any consumer that reads YAML can also read JSON, so
   this covers both use cases.
2. **Unambiguous serialization** — JSON has exactly one way to represent each value type.
   YAML has multiple quoting styles (plain, single-quoted, double-quoted, literal block,
   folded block) which is the root cause of the quoting bugs this RFC addresses.

### Why `data` accepts any JSON-compatible value

The `data` property accepts mappings, sequences, and scalars at the top level. While the
most common use case is a mapping (structured configuration data), there is no reason to
artificially restrict the top level — a list of file paths or a single computed value are
both valid use cases.

### Why mapping keys are format strings

Mapping keys support format string resolution for expressiveness — e.g., per-AOV render
pass settings keyed by pass name. The implementation cost is negligible since the data
structure is already being walked to resolve values.

### Why duplicate keys are not rejected

RFC 8259 (JSON) states that keys SHOULD be unique but does not forbid duplicates — it is
valid JSON. Implementations must not reject duplicate keys. Most JSON parsers accept them
using last-value-wins semantics, and there is no reason to be stricter than the format
itself.

### Why this requires the EXPR extension

The type-aware serialization (e.g., writing `INT` parameter values as JSON numbers rather
than strings) depends on the EXPR extension's type system. Without EXPR, all format string
values resolve to strings, which would make the type-preserving behavior impossible.

### Compact JSON output

Compact JSON (no pretty-printing) is the default because embedded file data is typically
machine-consumed by adaptors, not human-read. This minimizes file size. Implementations
may optionally support pretty-printed output in the future.

## Prior Art

### GitHub Actions

GitHub Actions expressions (`${{ }}`) within YAML are resolved at the value level in
structured contexts, preserving type information.

### AWS CloudFormation

CloudFormation's `Fn::Sub` performs substitution within structured YAML/JSON templates
at the value level, avoiding text-substitution quoting issues.

## Rejected Ideas

### `type: YAML` embedded files

A YAML output format was considered but rejected because JSON is a subset of YAML 1.2,
so JSON output already serves YAML consumers. Adding YAML output would introduce the
same quoting ambiguity problems (multiple valid serializations) that this RFC aims to
eliminate.

### Extending `type: TEXT` with a structured mode

Adding a flag to `<EmbeddedFileText>` (e.g., `structured: true`) was considered but
rejected because it would overload the semantics of an existing type. A new type value
makes the intent clear and keeps the schema clean.

### Making `repr_json()` the recommended solution

While `repr_json()` from RFC 0006 works for individual values, it requires opt-in per
value and doesn't protect the document structure. It remains useful as a complementary
tool for TEXT embedded files, but doesn't address the fundamental problem of text-level
substitution in structured data.

### Supporting arbitrary serialization formats (TOML, INI, etc.)

Only JSON is proposed because it covers the primary use cases (JSON and YAML consumers)
with a single format. Additional formats can be proposed in future RFCs if needed.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
