# Template Schemas [Version: 2023-09]

This document contains the formal specifications for the Open Job Description Template schemas. There are two schemas
defined in this document:

1. The Job Template describes the shape of a Job, its runtime environment, and all the processes that will run as part
of it. Jobs are created from Job Templates by providing a value for each of the Job Parameters defined in the Template,
and instantiating the template with those values.
2. The Environment Template describes an Environment that is defined outside a Job. This can be used in render management
systems to allow users to define Environments that are automatically applied to Job Templates that are submitted for rendering.

Reading the broad overviews in [How Jobs Are Constructed](How-Jobs-Are-Constructed) and [How Jobs Are Run](How-Jobs-Are-Run)
might provide an easier introduction and broader context prior to reading the schema in entirety.

Both Templates are expressed as UTF-8 documents in either
[ECMA-404 JavaScript Object Notation (JSON)](https://www.json.org/json-en.html) or
[YAML Ain't Markup Language (YAML) 1.2](https://yaml.org/) interchange format.

Throughout this document, a "character" is a single Unicode code point; all length limits expressed in characters
(e.g. "Maximum length: 128 characters") are counts of Unicode code points, not bytes.

Notations used in this document to annotate aspects of the schema definition:

* `@fmtstring` - The value of the annotated property is a Format String. See [Format Strings](#73-format-strings).
  * `@fmtstring[host]` - The value is evaluated at runtime on the worker host on which the job is running. The value is otherwise
     evaluated when the job template is submitted and the render manager is constructing a job.
* `@expr <type>` - The value of the annotated property is an expression field with target type `<type>`. See
  [Expression Fields](#76-expression-fields).
* `@optional` - The annotated property is optional.
* `@extension EXTENSION_NAME` - The annotated property is available only when extension EXTENSION_NAME is requested
  in the `extensions` list of the template. Implementations can choose which extensions to support.
* `@incompatible PROPERTY_NAME` - The annotated property cannot be used in
combination with PROPERTY_NAME.

## 1. Root elements

### 1.1. Job Template

```yaml
specificationVersion: "jobtemplate-2023-09"
$schema: <string> # @optional
extensions: [ <ExtensionName>, ... ] # @optional
name: <JobName> # @fmtstring
description: <Description> # @optional
parameterDefinitions:  [ <JobParameterDefinition>, ... ] # @optional
jobEnvironments: [ <Environment>, ... ] # @optional
steps: [<StepTemplate>, ...]
```

Where:

1. *specificationVersion* — A literal that identifies the document as adhering to this schema.
2. *$schema* — Ignored. This property is allowed for compatibility with JSON-editing IDEs.
3. *extensions* — If provided, is a non-empty list of extensions to the schema. Introduced in [RFC 0002](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0002-model-extensions.md).
      * Extensions available for specification version 2023-09: [TASK_CHUNKING](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md),
         [REDACTED_ENV_VARS](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0003-redacted-env-vars.md),
         [FEATURE_BUNDLE_1](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0004-enhanced-limits-and-capabilities.md),
         [EXPR](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0005-expression-language.md),
         [WRAP_ACTIONS](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0008-environment-wrap-actions.md),
         [ENV_PARAMS](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md)
      * A document that lists `ENV_PARAMS` must also list `EXPR`. A document that does not must be rejected.
4. *name* — The name to give to a Job that is created from the template. See: [&lt;JobName&gt;](#111-jobname).
5. *description* — A description to apply to all Jobs that are created from the template. It has no functional purpose,
   but may appear in UI elements. See: [&lt;Description&gt;](#72-description).
6. *parameterDefinitions* — A list of the Job Parameters that are available within the Job Template. Values
   for Job Parameters are defined when submitting the Job Template to create a Job to a render management system.
   The values of Job Parameters can be referenced in Format Strings.
   See: [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition).
      * Minimum number of elements: If provided, then this list must contain at least one element.
      * Maximum number of elements: The list must not contain more than 50
      elements or 200 elements with the `FEATURE_BUNDLE_1` extension.
7. *jobEnvironments* — An ordered list of the environments that are required to run Tasks in the Jobs created by this
   Job Template. These are entered in the order provided at the start of every Session for Tasks in the Job, and exited
   in the reverse order at the end of those Sessions. The Environments that a render management system attaches to the
   Job from Environment Templates come before these, in the order they are attached. A Session enters them in that
   order, before the Environments of this list, and exits them after. Together they are the Job's Environment order.
   With the `ENV_PARAMS` extension, an Environment's *activation*, *enableIf*, and *exclusiveGroup*, and a Step's
   *environment* entries, decide which of these Sessions enter it.
   See: [&lt;Environment&gt;](#4-environment). Constraints:
      1. No two Environments in this list may have the same value for the `name` property.
      2. The Environments defined in this list must not have the same `name` as an Environment
         defined in any Step within the same Job Template.
8. *steps* — A list of the Steps in the Job. See: [&lt;StepTemplate&gt;](#3-steptemplate).

#### 1.1.1. `<JobName>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Allowed characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 128 characters, after the format string has been resolved.
512 characters, after the format string has been resolved if using the
`FEATURE_BUNDLE_1` extension.

#### 1.1.2. `<ExtensionName>`

A literal string matching the following character regex: `[A-Z_0-9]{3,128}`.

### 1.2. Environment Template

```yaml
specificationVersion: environment-2023-09
$schema: <string> # @optional
extensions: [ <ExtensionName>, ... ] # @optional
parameterDefinitions: [ <JobParameterDefinition>, ... ] # @optional
environment: <Environment>
```

1. *specificationVersion* — A literal that identifies the document as adhering to this schema.
2. *$schema* — Ignored. This property is allowed for compatibility with JSON-editing IDEs.
3. *extensions* — If provided, is a non-empty list of extensions that this document uses, with the same available
   names and prerequisites as the Job Template. An extension listed here applies to the content of this document only.
   A Job Template does not need to list the extensions used by the Environment Templates a scheduler applies to it, and
   vice versa.
4. *parameterDefinitions* — A list of the Job Parameters that are available within the Environment Template. Values
   for Job Parameters are defined when submitting a Job Template to create a Job to a render management system.
   Both the Job Template and Environment Template(s) for a submission are allowed to contain definitions for the same
   job parameter name, but the submission must be rejected if any of the definitions of the same job parameter name
   have unresolvable conflicts
   (See: [Merging Environment Template Parameter Definitions](#121-merging-environment-template-parameter-definitions)).
   The values of Job Parameters can be referenced in Format Strings.
   See: [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition).
      * Minimum number of elements: If provided, then this list must contain at least one element.
      * Maximum number of elements: The list must not contain more than 50 elements.
5. *environment* — The definition of the Environment that the Environment Template defines.
   See [&lt;Environment&gt;](#4-environment).

#### 1.2.1. Merging Environment Template Parameter Definitions

When submitting a job using a Job Template and one or more Environment Templates, then two or more of the given Templates
may contain job parameter definitions with the same job parameter name. This section describes how we determine whether
those definitions are in conflict, and how the constraints that they define are merged to derive the constraints on the
job parameters' values.

Job Parameter Definitions for the same parameter name are in conflict if:

1. They have differing values for the `type` property of the job parameter definition; or
2. The parameter type is "PATH" and either the `objectType` or `dataFlow` properties are defined with different values.

Properties in a Job Parameter Definition such as the `minLength` and `allowedValues` define constraints on
the value for the job parameter. These constraints do not need to be identical in every Job Parameter Definition for the same
parameter name, but each constraint must become more constrained as a subsequent definition is merged with the previous
ones in processing order -- the Environment Templates are processed in an order defined by the render management system
or submission, and the Job Template is always processed last. The exception to this rule is the `default` property of a
Job Parameter Definition; the default value for a job parameter is always the last `default` value defined in the template
processing order. The merged job parameter definition that results from this process must be internally consistent to be considered
valid -- for example, the value of the `default` property must adhere to the constraints in the definition.
For a `RANGE_EXPR` parameter, each definition's *minLength* and *maxLength* keep the rule of the document that
contains it (see [§2.10](#210-jobrangeexprparameterdefinition-extension-expr)).

This merge applies to the top-level `parameterDefinitions` of each template only. The `envParameterDefinitions` of an
[&lt;Environment&gt;](#4-environment) (`@extension ENV_PARAMS`) are never merged. Each Environment's parameters are a
namespace of their own, even when two Environments, or an Environment and a Job Parameter, use the same name. An
Environment parameter's `default` that references `Param.<name>` or `RawParam.<name>` reads the merged Job Parameter's
value. So a Job Template that redefines a Job Parameter's `default` changes the default of every Environment parameter
that refers to it.

## 2. `<JobParameterDefinition>`

```bnf
<JobParameterDefinition> ::= <JobStringParameterDefinition> | <JobPathParameterDefinition> |
                             <JobIntParameterDefinition> | <JobFloatParameterDefinition> |
                             <JobBoolParameterDefinition> |              # @extension EXPR
                             <JobRangeExprParameterDefinition> |         # @extension EXPR
                             <JobListStringParameterDefinition> |        # @extension EXPR
                             <JobListPathParameterDefinition> |          # @extension EXPR
                             <JobListIntParameterDefinition> |           # @extension EXPR
                             <JobListFloatParameterDefinition> |         # @extension EXPR
                             <JobListBoolParameterDefinition> |          # @extension EXPR
                             <JobListListIntParameterDefinition>         # @extension EXPR
```

When the `EXPR` extension is enabled, job parameter and task parameter type names become
case-insensitive. For example, `INT`, `Int`, and `int` are all equivalent, as are
`LIST[STRING]`, `List[String]`, and `list[string]`. See
[RFC 0007](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0007-extend-parameter-types.md)
for the design rationale.

The `userInterface` property on parameter definitions provides hints to user interface implementations. Its fields are suggestions for how to present the parameter, not validation constraints. If a field does not apply to the chosen UI element, it should be ignored. Properties outside of `userInterface`, such as `allowedValues`, `minValue`, and `maxValue`, are constraints that must be enforced during validation.

### 2.1. `<JobStringParameterDefinition>`

Defines a job parameter that allows input of a single string value to a Job Template.

The value of a Job Parameter of this type referenced in format strings as both:

1. `Param.<name>` and
2. `RawParam.<name>`

A `<JobStringParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "STRING"
description: <Description> # @optional
default: <JobParameterStringValue> # @optional
allowedValues: [ <JobParameterStringValue>, ... ] # @optional
minLength: <integer>,# @optional
maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("LINE_EDIT", "MULTILINE_EDIT", "DROPDOWN_LIST", "CHECK_BOX", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
   See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue).
4. *allowedValues* — An array of the values that the parameter is allowed to be. It is an error to provide a value that is
   not in this list, if the list is defined. See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue).
5. *minLength* — The minimum allowable length of the parameter string value.
6. *maxLength* — The maximum allowable length of the parameter string value.
7. *userInterface* — User interface hints for this parameter. See [§2](#2-jobparameterdefinition) for how implementations should treat these fields.
    1. *control* — The user interface control to use when editing this parameter.
       The default, if not provided, is "LINE_EDIT" when *allowedValues* is not provided, "DROPDOWN_LIST" when it is.
        1. "LINE_EDIT" — This is a freeform string line edit control. Cannot be used when *allowedValues* is provided.
        2. "MULTILINE_EDIT" — This is a freeform string multi-line edit control. It uses a fixed width font, intended for
           editing script code. The vertical size of this control is set to grow to fit the available space. Cannot be
           used when *allowedValues* is provided.
        3. "DROPDOWN_LIST" — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is also provided.
        4. "CHECK_BOX" — This is a checkbox control. It requires that *allowedValues* is also provided, and contains two
           values, case-insensitive, one representing true and another representing false.
            * Valid pairs are ["true", "false"], ["yes", "no"], ["on", "off"], and ["1", "0"].
        5. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

With the EXPR extension, the value of a Job Parameter of this type is referenced in format strings as `Param.<name>`, returning a `string` type value.

### 2.2. `<JobPathParameterDefinition>`

Defines a job parameter that allows input to a Job Template of a single string value that represents a file or directory
path on a filesystem, or a URI. This parameter type differs from a
[`<JobStringParameterDefinition>`](#21-jobstringparameterdefinition) in that the value of the parameter automatically has
defined and matching path mapping rules applied to it.

The value of a Job Parameter of this type referenced in format strings as both:

1. `Param.<name>` — the value of the parameter with applicable path mapping applied to it; and
2. `RawParam.<name>` — the value of the parameter after the join described under *default* below, with no path
   mapping applied to it.

**`@extension EXPR` — URI values**: When the EXPR extension is enabled, PATH parameter values
may be URIs (values with a `scheme://` prefix, e.g. `s3://bucket/key`). URI values are not
subject to relative path resolution — they are not joined with the job template directory or
the current working directory. If no path mapping rule matches a URI value, it passes through
to `Param.<name>` unchanged. See the
[Expression Language path type description](2026-02-Expression-Language#121-types) for how
path operations handle URIs.

A `<JobPathParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "PATH"
description: <Description> # @optional
default: <JobParameterStringValue> # @optional
allowedValues: [ <JobParameterStringValue>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
objectType: enum("FILE", "DIRECTORY") # @optional
dataFlow: enum("NONE", "IN", "OUT", "INOUT") # @optional
userInterface: # @optional
   control: enum("CHOOSE_INPUT_FILE", "CHOOSE_OUTPUT_FILE", "CHOOSE_DIRECTORY", "DROPDOWN_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelString> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   fileFilters: [ <JobPathParameterFileFilter>, ... ] # @optional
   fileFilterDefault: <JobPathParameterFileFilter> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
   See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue). When a Job is created from the template,
   a non-empty default that is not a URI is resolved as follows. Template validation does not apply these rules.
    1. The default must be a relative path. An absolute path is an error.
    2. The default is joined with the directory containing the Job Template, and the result is lexically
       normalized: `.` components are removed and `..` components are applied, without resolving symbolic links.
    3. The normalized result must be the Job Template's directory or a path within it. Otherwise it is an error;
       for example, `../x` and `a/../../x` are errors.

   A value supplied for the parameter when submitting a Job is not subject to these rules. It may be absolute or
   relative; a relative value is joined with the current working directory of the submission and lexically
   normalized in the same way. URI values are never joined; see *URI values* above.
4. *allowedValues* — An array of the values that the parameter is allowed to be. It is an error to provide a value that is
   not in this list, if the list is defined. See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue).
   Template validation checks a *default* against this list as written. Job creation checks the value after the
   join described under *default* (with the Job Template's directory for a default, or with the current working
   directory for a submitted relative value), because the join is performed by the submitting client and the
   Job may be created elsewhere from the joined values. A relative *default* can therefore satisfy both checks
   only if the list contains both the default as written and its joined path. In practice, use *allowedValues*
   with absolute paths or URIs, not with a relative *default*.
5. *minLength* — The minimum allowable length of the parameter string value. Checked twice, as for *allowedValues*:
   at template validation against the *default* as written, and at job creation against the joined value.
6. *maxLength* — The maximum allowable length of the parameter string value. Checked twice, as for *allowedValues*:
   at template validation against the *default* as written, and at job creation against the joined value.
7. *objectType* — The type of object the path represents; either a FILE or a DIRECTORY. Default is DIRECTORY.
8. *dataFlow* — Whether the object the path represented serves as input, output or both for the Job. Default is NONE.
9. *userInterface — User interface properties for this parameter*
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, depends on
       *objectType*, *dataFlow*, and *allowedValues*. If *objectType* is FILE, then if *dataFlow* is "OUT", it is
       "CHOOSE_OUTPUT_FILE", otherwise it is "CHOOSE_INPUT_FILE". If *objectType* is not "FILE", then it is
       "CHOOSE_DIRECTORY". If *allowedValues* is provided, then the default is instead "DROPDOWN_LIST".
        1. "CHOOSE_INPUT_FILE" — This is a combination of a line edit and a button that uses the system's input file
           dialog. Cannot be used when *allowedValues* is provided.
        2. "CHOOSE_OUTPUT_FILE" — This is a combination of a line edit and a button that uses the system's output/save
           file dialog. Cannot be used when *allowedValues* is provided.
        3. "CHOOSE_DIRECTORY" — This is a combination of a line edit and a button that uses the system's directory dialog.
           Cannot be used when *allowedValues* is provided.
        4. "DROPDOWN_LIST" — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is also provided.
        5. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. fileFilters — Can be provided when the *uiControl* is "CHOOSE_INPUT_FILE" or "CHOOSE_OUTPUT_FILE". Defines the file
       filters that are shown in the file choice dialog. Maximum of 20 filters.
    5. fileFilterDefault — Can be provided when the *uiControl* is "CHOOSE_INPUT_FILE" or "CHOOSE_OUTPUT_FILE". The
       default file filter that's shown in the file choice dialog.

With the EXPR extension, the value of a Job Parameter of this type is referenced in format strings as `Param.<name>`, returning a `path` type value.

### 2.3 `<JobIntParameterDefinition>`

Defines a job parameter that allows input to a Job Template of a single integer value.

The value of a Job Parameter of this type referenced in format strings as both:

1. `Param.<name>` and
2. `RawParam.<name>`

A `<JobIntParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "INT"
description: <Description> # @optional
default: <integer> | <intstring> # @optional
allowedValues: [ <integer> | <intstring>,... ] # @optional
minValue: <integer> | <intstring> # @optional
maxValue: <integer> | <intstring> # @optional
userInterface:  # @optional
   control: enum("SPIN_BOX", "DROPDOWN_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   singleStepDelta: <positiveint> # @optional

```

Where `<intstring>` is a string whose value is the string representation of an integer value in base-10, with optional
white space around it (see [Numeric strings](#75-numeric-strings)), and:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *allowedValues* — An array of the values that the parameter is allowed to be. It is an error to provide a value that is
   not in this list, if the list is defined.
5. *minValue* — Minimum allowable value for the parameter. It is an error to provide a value for the parameter that is
   less than this.
6. *maxValue* — Maximum allowable value for the parameter. It is an error to provide a value for the parameter that is
   greater than this.
7. *userInterface — User interface properties for this parameter*
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is
      "SPIN_BOX" when *allowedValues* is not provided, "DROPDOWN_LIST" when it is.
        1. "SPIN_BOX" — This is an integer editing control. Cannot be used when *allowedValues* is provided.
        2. "DROPDOWN_LIST" — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is provided.
        3. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *singleStepDelta* — How much the value changes for a single step modification, such as selecting an up or down
       arrow in the user interface control.

With the EXPR extension, the value of a Job Parameter of this type is referenced in format strings as `Param.<name>`, returning an `int` type value.

### 2.4. `<JobFloatParameterDefinition>`

Defines a job parameter that allows input to a Job Template of a single floating point or integer value.

The value of a Job Parameter of this type referenced in format strings as both:

1. `Param.<name>` and
2. `RawParam.<name>`

A `<JobFloatParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "FLOAT"
description: <Description> # @optional
default: <float> | <floatstring> # @optional
allowedValues: [ <float> | <floatstring>,... ] # @optional
minValue: <float> | <floatstring> # @optional
maxValue: <float> | <floatstring> # @optional
userInterface: # @optional
   control: enum(SPIN_BOX, DROPDOWN_LIST, HIDDEN) # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   decimals: <integer> # @optional
   singleStepDelta: <positivefloat> # @optional
```

Where `<floatstring>` is a string whose value is the string representation of a floating point or integer value in
base-10, with optional white space around it (see [Numeric strings](#75-numeric-strings)), and:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *allowedValues* — An array of the values that the parameter is allowed to be. It is an error to provide a value that is
   not in this list, if the list is defined.
5. *minValue* — Minimum allowable value for the parameter. It is an error to provide a value for the parameter that is
   less than this.
6. *maxValue* — Maximum allowable value for the parameter. It is an error to provide a value for the parameter that is
   greater than this.
7. *userInterface — User interface properties for this parameter*
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is
       "SPIN_BOX" when *allowedValues* is not provided, "DROPDOWN_LIST" when it is.
        1. "SPIN_BOX" — This is a floating point editing control. Cannot be used when *allowedValues* is provided.
        2. "DROPDOWN_LIST" — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is provided.
        3. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *decimals* — This is the number of places editable after the decimal point. If *decimals* is not provided then an
       adaptive decimal mode will be used.
    5. *singleStepDelta* — How much the value changes for a single step modification, such as selecting an up or down
       arrow in the user interface control. If *decimals* is provided, this is an absolute value, otherwise it is the
       fraction of the current value to use as an adaptive step.

With the EXPR extension, the value of a Job Parameter of this type is referenced in format strings as `Param.<name>`, returning a `float` type value.

### 2.5. `<JobParameterStringValue>`

*This is a supplemental value type referenced by the parameter definitions in sections 2.1–2.4 and 2.9+.*

A string value subject to the following constraints:

1. Allowable characters: Any.
2. Minimum length: There is no minimum length.
3. Maximum length: 1024 characters.

### 2.6. `<UserInterfaceLabelStringValue>`

*This is a supplemental value type referenced by the parameter definitions in sections 2.1–2.4 and 2.9+.*

A string value subject to the following constraints:

1. Allowable characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 64 characters.

### 2.7. `<JobPathParameterFileFilter>`

*This is a supplemental value type referenced by the parameter definitions in sections 2.1–2.4 and 2.9+.*

Represents one named file type for an input or output file choice dialog. For example:
`{"label": "Image Files", "patterns": ["*.png", "*.jpg", "*.exr"]}` or `{"label": "All Files", "patterns": ["*"]}`.

A `<JobPathParameterFileFilter>` is the object:

```yaml
label: <UserInterfaceLabelStringValue>
patterns: [ <FileDialogFilterPatternStringValue>, ... ]
```

### 2.8. `<FileDialogFilterPatternStringValue>`

*This is a supplemental value type referenced by the parameter definitions in sections 2.1–2.4 and 2.9+.*

A string value subject to the following constraints:

1. Allowable values: "*", "*.*", and "*.[:file-extension-chars:]+". The characters that :file-extension-chars: can take on
   are any unicode character except
    1. The Cc unicode character category.
    2. Path separators "\" and "/".
    3. Wildcard characters "*", "?", "[", "]".
    4. Characters commonly disallowed in paths: "#", "%", "&", "{", "}", "<", ">", "$", "!", "'", "\"", ":", "@", "`", "|",
       and "=".
2. Minimum length: 1 character.
3. Maximum length: 20 characters.

### 2.9. `<JobBoolParameterDefinition>` `@extension EXPR`

Defines a job parameter that accepts a boolean value.

```yaml
name: <Identifier>
type: "BOOL"
description: <Description> # @optional
default: <bool> # @optional
userInterface: # @optional
   control: enum("CHECK_BOX", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Accepted values are:
- JSON/YAML boolean literals: `true`, `false`
- Integer or float `1` or `1.0` (true), `0` or `0.0` (false)
- Case-insensitive strings representing true: `"true"`, `"yes"`, `"on"`, `"1"`
- Case-insensitive strings representing false: `"false"`, `"no"`, `"off"`, `"0"`

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "CHECK_BOX".
        1. "CHECK_BOX" — A checkbox control for boolean input.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

The value of a Job Parameter of this type is referenced in format strings as `Param.<name>`, returning a `bool` type value.

Note: Unlike other parameter types, `BOOL` does not support `allowedValues` because restricting
to only `true` or only `false` does not provide meaningful value.

### 2.10. `<JobRangeExprParameterDefinition>` `@extension EXPR`

Defines a job parameter that accepts a range expression string conforming to the
[`<IntRangeExpr>`](#34111-intrangeexpr) grammar.

```yaml
name: <Identifier>
type: "RANGE_EXPR"
description: <Description> # @optional
default: <string> # @optional, must be valid <IntRangeExpr>
minLength: <integer> # @optional
maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("LINE_EDIT", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
   Must be a valid `<IntRangeExpr>`.
4. *minLength* — Minimum string length of the range expression. Must be >= 1 if provided.
5. *maxLength* — Maximum string length of the range expression. Default is 1024.
6. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "LINE_EDIT".
        1. "LINE_EDIT" — A single-line text input for entering range expressions.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter's edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

In a document that lists the `ENV_PARAMS` extension, *minLength* and *maxLength* are checked against two strings, and
both must satisfy them. The strings are the value as written (the string submitted for the parameter, or the
`default`), and its [canonical form](#34111-intrangeexpr). So with `maxLength: 3`, the value `1,2,3` is rejected
although its canonical form `1-3` fits. With `minLength: 4`, the value `1-3:2` is rejected because its canonical form
`1,3` is too short. In any other document, they are checked against the value as written. When a Job Parameter's
definitions in several templates are merged ([§1.2.1](#121-merging-environment-template-parameter-definitions)), each
definition's *minLength* and *maxLength* are checked under the rule of the document that contains it.

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `range_expr` type value.
2. `RawParam.<name>` — Returns a `range_expr` type value (identical to `Param.<name>`).
3. `list(Param.<name>)` — Returns a `list[int]` with the expanded values.

### 2.11. `<JobListStringParameterDefinition>` `@extension EXPR`

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
   control: enum("LINE_EDIT_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *minLength*/*maxLength* — Constrain the number of items in the list.
5. *item* — Constraints for each item in the list.
    1. *allowedValues* — An array of the values that each item is allowed to be.
    2. *minLength*/*maxLength* — Constrain the string length of each item.
6. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "LINE_EDIT_LIST".
        1. "LINE_EDIT_LIST" — A list of line edit controls.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[string]` type value.
2. `Param.<name>[i]` — Returns the i-th element as `string`.
3. `len(Param.<name>)` — Returns the count of elements.

### 2.12. `<JobListPathParameterDefinition>` `@extension EXPR`

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
   control: enum("CHOOSE_INPUT_FILE_LIST", "CHOOSE_OUTPUT_FILE_LIST",
                 "CHOOSE_DIRECTORY_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   fileFilters: [ <JobPathParameterFileFilter>, ... ] # @optional
   fileFilterDefault: <JobPathParameterFileFilter> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *objectType* — The type of object the paths represent; either FILE or DIRECTORY. Default is DIRECTORY.
4. *dataFlow* — Whether the objects the paths represent serve as input, output or both for the Job. Default is NONE.
5. *default* — Default value to use for the parameter if the submission does not include a value for it.
   Each element is resolved by the rules for the *default* of a
   [`<JobPathParameterDefinition>`](#22-jobpathparameterdefinition), applied to that element. It is an error
   if any element violates them. An empty list is a valid default.
6. *minLength*/*maxLength* — Constrain the number of paths in the list.
7. *item* — Constraints for each item in the list. As for a `<JobPathParameterDefinition>`, template validation
   checks each element of *default* as written, and job creation checks each element after it has been joined
   with the Job Template's directory (for a default) or the current working directory (for a submitted relative
   value).
    1. *allowedValues* — An array of the values that each item is allowed to be.
    2. *minLength*/*maxLength* — Constrain the string length of each path.
8. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use. The default depends on *objectType* and *dataFlow*:
       If *objectType* is FILE and *dataFlow* is "OUT", default is "CHOOSE_OUTPUT_FILE_LIST".
       If *objectType* is FILE otherwise, default is "CHOOSE_INPUT_FILE_LIST".
       If *objectType* is DIRECTORY, default is "CHOOSE_DIRECTORY_LIST".
        1. "CHOOSE_INPUT_FILE_LIST" — A list of input file choice controls.
        2. "CHOOSE_OUTPUT_FILE_LIST" — A list of output file choice controls.
        3. "CHOOSE_DIRECTORY_LIST" — A list of directory choice controls.
        4. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *fileFilters* — File filters for the file choice dialog (only for CHOOSE_INPUT_FILE_LIST/CHOOSE_OUTPUT_FILE_LIST).
    5. *fileFilterDefault* — Default file filter for the file choice dialog.

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[path]` type value with path mapping applied.
2. `RawParam.<name>` — Returns a `list[string]` type value holding each element after it has been joined
   as described under *default*, without path mapping.
3. `Param.<name>[i]` — Returns the i-th element as `path`.
4. `len(Param.<name>)` — Returns the count of elements.

Each element of a `LIST[PATH]` value is processed as the value of a `PATH` parameter is: a relative element of a
submitted value is joined with the current working directory of the submission, a relative element of the
*default* is joined with the Job Template's directory, and path mapping rules are applied to each element
independently.

### 2.13. `<JobListIntParameterDefinition>` `@extension EXPR`

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
   control: enum("SPIN_BOX_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   singleStepDelta: <positiveint> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *minLength*/*maxLength* — Constrain the number of items in the list.
5. *item* — Constraints for each item in the list.
    1. *allowedValues* — An array of the values that each item is allowed to be.
    2. *minValue*/*maxValue* — Constrain the value of each integer item.
6. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "SPIN_BOX_LIST".
        1. "SPIN_BOX_LIST" — A list of integer editing controls.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *singleStepDelta* — How much the value changes for a single step modification.

Each item of a value given for this parameter when a Job is created may be an integer or an `<intstring>` (see
[Numeric strings](#75-numeric-strings)). For example, `[1, " 2 "]` is the list `[1, 2]`.

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[int]` type value.
2. `Param.<name>[i]` — Returns the i-th element as `int`.
3. `len(Param.<name>)` — Returns the count of elements.

### 2.14. `<JobListFloatParameterDefinition>` `@extension EXPR`

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
   control: enum("SPIN_BOX_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
   decimals: <integer> # @optional
   singleStepDelta: <positivefloat> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *minLength*/*maxLength* — Constrain the number of items in the list.
5. *item* — Constraints for each item in the list.
    1. *allowedValues* — An array of the values that each item is allowed to be.
    2. *minValue*/*maxValue* — Constrain the value of each float item.
6. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "SPIN_BOX_LIST".
        1. "SPIN_BOX_LIST" — A list of floating point editing controls.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *decimals* — The number of places editable after the decimal point.
    5. *singleStepDelta* — How much the value changes for a single step modification.

Each item of a value given for this parameter when a Job is created may be a number or a `<floatstring>` (see
[Numeric strings](#75-numeric-strings)). An item given as a `<floatstring>` keeps the text it was written with, without
the white space around it, as in [Float Value Pass-Through](2026-02-Expression-Language#134-float-value-pass-through).
For example, given `[" 1.00 ", "2.50"]`, `{{Param.<name>[0]}}` resolves to `1.00`.

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[float]` type value.
2. `Param.<name>[i]` — Returns the i-th element as `float`.
3. `len(Param.<name>)` — Returns the count of elements.

### 2.15. `<JobListBoolParameterDefinition>` `@extension EXPR`

Defines a job parameter that accepts a list of boolean values.

```yaml
name: <Identifier>
type: "LIST[BOOL]"
description: <Description> # @optional
default: [ <bool>, ... ] # @optional
minLength: <integer> # @optional
maxLength: <integer> # @optional
userInterface: # @optional
   control: enum("CHECK_BOX_LIST", "HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Each list item accepts the same values as [`<JobBoolParameterDefinition>`](#29-jobboolparameterdefinition):
- JSON/YAML boolean literals: `true`, `false`
- Integer or float `1` or `1.0` (true), `0` or `0.0` (false)
- Case-insensitive strings representing true: `"true"`, `"yes"`, `"on"`, `"1"`
- Case-insensitive strings representing false: `"false"`, `"no"`, `"off"`, `"0"`

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *minLength*/*maxLength* — Constrain the number of items in the list.
5. *userInterface* — User interface properties for this parameter.
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, is "CHECK_BOX_LIST".
        1. "CHECK_BOX_LIST" — A list of checkbox controls.
        2. "HIDDEN" — This hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[bool]` type value.
2. `Param.<name>[i]` — Returns the i-th element as `bool`.
3. `len(Param.<name>)` — Returns the count of elements.

### 2.16. `<JobListListIntParameterDefinition>` `@extension EXPR`

Defines a job parameter that accepts a nested list of integer values. This enables use cases
like representing graph adjacency lists for task-task dependencies.

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
   control: enum("HIDDEN") # @optional
   label: <UserInterfaceLabelStringValue> # @optional
   groupLabel: <UserInterfaceLabelStringValue> # @optional
```

Where:

1. *name* — The name by which the parameter is referenced. See: [&lt;Identifier&gt;](#71-identifier).
2. *description* — A description to apply to the parameter. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *default* — Default value to use for the parameter if the submission does not include a value for it.
4. *minLength*/*maxLength* — Constrain the number of inner lists.
5. *item* — Constraints for each inner list.
    1. *minLength*/*maxLength* — Constrain the size of each inner list.
    2. *item* — Constraints for each integer in the inner list.
        1. *allowedValues* — An array of the values that each integer is allowed to be.
        2. *minValue*/*maxValue* — Constrain the value of each integer.
6. *userInterface* — User interface properties for this parameter.
    1. *control* — The only supported control is "HIDDEN", which hides the parameter from the user interface.
    2. *label* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

Each integer in an inner list of a value given for this parameter when a Job is created may be an integer or an
`<intstring>` (see [Numeric strings](#75-numeric-strings)). For example, `[[1, " 2 "], ["3"]]` is `[[1, 2], [3]]`.

The value of a Job Parameter of this type is referenced in format strings as:

1. `Param.<name>` — Returns a `list[list[int]]` type value.
2. `Param.<name>[i]` — Returns the i-th element as `list[int]`.
3. `Param.<name>[i][j]` — Returns the j-th element of the i-th list as `int`.
4. `len(Param.<name>)` — Returns the count of outer list elements.
5. `len(Param.<name>[i])` — Returns the count of inner list elements.

## 3. `<StepTemplate>`

A `<StepTemplate>` defines a single Step in the Job; the action(s) that it takes, its dependencies, the parameter space
that maps to the Step's Tasks, and its runtime environment and requirements.

A `<StepTemplate>` is the object:

```yaml
name: <StepName>
description: <Description> # @optional
let: <LetBindings> # @optional @extension EXPR
dependencies: [ <StepDependency>, ... ] # @optional
stepEnvironments: [ <Environment>, ... ] # @optional
hostRequirements: <HostRequirements> # @optional
parameterSpace: <StepParameterSpaceDefinition> # @optional
script: <StepScript>
```

Where:

1. *name* — The name to identify the Step within the Job. Each Step within a Job Template must have name that differs from
   the names of all other Steps in the same Job Template. See: [&lt;StepName&gt;](#31-stepname).
2. *description* — A description to apply to the step. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *let* — An ordered list of expression bindings evaluated once per step. Bound names are available in
   *stepEnvironments*, *hostRequirements*, *parameterSpace*, and *script* fields, and with the `ENV_PARAMS` extension in
   the *parameters* values and *enableIf* of *dependencies* entries. See: [&lt;LetBindings&gt;](#36-letbindings).
4. *dependencies* — A list of the dependencies of this Step. These dependencies must be resolved before the Tasks of the
   Step run. A dependency on a Step is resolved before the Tasks are scheduled. With the `ENV_PARAMS` extension, an
   entry may instead name an Environment for the Step's Sessions to enter, with the Step's parameter values for it,
   before they run the Step's Tasks. Such an entry is resolved in each Session, so it does not delay scheduling.
   See: [&lt;StepDependency&gt;](#32-stepdependency)
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: There is no maximum defined, though implementations may choose to constrain the number of
    dependencies.
5. *stepEnvironments* — An ordered list of the environments that are required to run Tasks in this Step.
  These are entered in the order provided at the start of every Session for Tasks in the Step, and exited in the reverse
  order at the end of those Sessions. With the `ENV_PARAMS` extension, one whose *enableIf* is `false` for the Step is
  not entered.
  See: [&lt;Environment&gt;](#4-environment).
    * Constraints:
        1. No two Environments in this list may have the same value for the `name` property.
        2. The Environments defined in this list must not have the same `name` as a Job Environment defined in the same
           Job Template.
    * Note: The scope of a Step Environment's `name` is the Step that defines it. Different Steps may each define a
      Step Environment with the same `name`; a Session only ever contains the Step Environments of a single Step, so
      these names never collide.
6. *hostRequirements* — Describes the requirements on Worker host's capabilities that must be satisfied for the Task(s) of
   the Step to be scheduled to the host. See: [&lt;HostRequirements&gt;](#33-hostrequirements).
7. *parameterSpace* — Defines the parameterization of the Step's action; the available parameters, the values that they
   take on, and how those parameters' values are combined to produce the Tasks of the Step. Absent this property the Step
   is run a single time.
8. *script* — The action that is taken by this Step's Tasks when they are run on a Worker host.

### 3.1. `<StepName>`

A string subject to the following constraints:

1. Allowed characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 64 characters. 512 characters if using the
`FEATURE_BUNDLE_1` extension.

### 3.2. `<StepDependency>`

This entity is used by the template author to specify a Step in the same Job that a Step depends upon. With the
`ENV_PARAMS` extension, it may instead specify an Environment that the Step requests, with values that the Step
supplies for the Environment's parameters.

A `<StepDependency>` is one of the objects:

```yaml
dependsOn: "<StepName>"
```

```yaml
# @extension ENV_PARAMS
step: "<StepName>"
```

```yaml
# @extension ENV_PARAMS
environment: "<EnvironmentName>"
required: <bool> # @optional
enableIf: <Expression> # @optional @expr bool
parameters: <EnvironmentParameterValues> # @optional
```

Where:

1. *dependsOn* — Provides the name of another step in the same job upon which this step depends. The Task(s) of this
   Step may be scheduled only when the depended-upon Step has fully completed successfully.
2. *step* — A synonym of *dependsOn*. An entry `step: X` means exactly what `dependsOn: X` means, and every rule for a
   *dependsOn* entry applies to it. A *step* entry and a *dependsOn* entry that name the same Step are two entries that
   name one Step. Available with the `ENV_PARAMS` extension.

   > **NOTE:** A future major version of this specification is planned to remove *dependsOn* in favor of *step*. A Job
   > Template that lists `ENV_PARAMS` should prefer *step*.

3. *environment* — The name of an Environment that this Step requests. The name resolves to the entry of the same Job
   Template's *jobEnvironments* with that `name`, if there is one. Otherwise it resolves to an *external Environment*:
   the `environment` of an Environment Template that the scheduler attaches to the submission, matched by `name` when
   the Job is created (see [Resolving External Environments](#321-resolving-external-environments)). The name of a
   disabled entry resolves in the same way. An enabled entry declares that the Step's Sessions need the Environment,
   entered with the entry's values. The Environment's *activation*, *enableIf*, and *exclusiveGroup* decide whether the
   Step's Sessions enter it (see [&lt;Environment&gt;](#4-environment)). The entry is met when the Step's Sessions enter
   the Environment, before they run the Step's Tasks, so it does not delay scheduling them. It does not change the
   position of the Environment in the order a Session enters its Environments. Available with the `ENV_PARAMS`
   extension. The other fields of this form are:
    1. *required* — Whether the Environment must be present. Default `true`. When `false` and the name resolves to no
       Environment when the Job is created, the entry has no effect, and the Step's Sessions run without that
       Environment. When `false` and the name of an enabled entry resolves to an attached Environment that declares no
       *envParameterDefinitions*, the entry's *parameters* are ignored (see
       [§3.2.1](#321-resolving-external-environments) item 1).
    2. *enableIf* — Whether this entry is in effect. An [expression field](#76-expression-fields) of type `bool`. The
       values it may reference are given in the [`ENV_PARAMS` Scope Summary](#732-env_params-scope-summary). It is
       evaluated when the Job is created, before the entry's name is resolved. A `null` result is an error. If omitted,
       the entry is enabled. Where it is `false`, the entry is *disabled*. A disabled entry requests nothing and
       supplies no values. Its *parameters* are not checked: constraints 5 and 6 do not apply to it, so a key that the
       Environment does not declare, or a value that it would reject, is not an error. A disabled entry whose name
       resolves to no Environment has no effect, whatever *required* says. Nor does one whose name resolves to an
       Environment from a document that does not list `ENV_PARAMS`: every Session of the Job enters that Environment,
       and the entry is not an error (see [&lt;Environment&gt;](#4-environment) *activation*). Otherwise its effect
       depends on the *activation* of the Environment it names:
        * `ON_REQUEST` — The Step does not request the Environment, as if the entry were absent.
        * `BY_DEFAULT` — The Step *declines* the Environment. Its Sessions do not enter it, exactly as for an
          `ON_REQUEST` Environment that the Step does not request. The Environment's *enableIf* is not evaluated for the
          Step. Constraint 7, the checks of the Step's effective values, and the Environment's *hostRequirements* do not
          apply to the Step.
        * `ALWAYS` — An error (see [&lt;Environment&gt;](#4-environment) *activation*).
    3. *parameters* — The values this Step supplies, keyed by the names in the Environment's *envParameterDefinitions*
       (see [&lt;EnvironmentParameterDefinition&gt;](#45-environmentparameterdefinition-extension-env_params)). A
       parameter that the entry omits takes its `default`. If *parameters* is not provided, the entry supplies no
       values, and it still requests the Environment.

`<EnvironmentParameterValues>` is a map from [&lt;Identifier&gt;](#71-identifier) to `<EnvironmentParameterValue>`:

```yaml
<Identifier>: <EnvironmentParameterValue>, # @fmtstring
...
```

An `<EnvironmentParameterValue>` is one of:

* A literal of the parameter's type, written as the `default` of a
  [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition) of the same type is written: a string, an integer or
  `<intstring>`, a float or `<floatstring>`, a boolean, or a list.
* A [Format String](#73-format-strings) resolved when the Job is created. The values it may reference are given in the
  [`ENV_PARAMS` Scope Summary](#732-env_params-scope-summary). A value that is a single `{{ }}`
  expression is evaluated with the parameter's type as its target type. Any other format string resolves to a string.
  The string is converted to the parameter's type as a submitted Job Parameter value of that type would be, except
  that a relative path is not joined with any directory. A list-typed parameter has no string form, so its value must
  be a list literal or a single `{{ }}` expression.

Constraints:

1. Exactly one of *dependsOn*, *step*, or *environment* must be present. *required*, *enableIf*, and *parameters* are
   permitted only with *environment*.
2. *environment* must not name a *stepEnvironments* entry of the same Step.
3. No two *environment* entries of one *dependencies* list may name the same Environment.
4. *parameters*, if provided, must contain at least one entry and at most 50 entries.
5. Every key of *parameters* must name a parameter declared in the named Environment's *envParameterDefinitions*. An
   Environment that declares none, including one from a document that does not list `ENV_PARAMS`, accepts an entry with
   no *parameters* and rejects one with any, except that it ignores the *parameters* of an entry with `required: false`
   (see [§3.2.1](#321-resolving-external-environments) item 1).
6. Every value must be valid for the parameter it supplies: of its type, and within its `allowedValues`, `minLength`,
   `maxLength`, `minValue`, `maxValue`, and `item` constraints.
7. For every Environment that a Step's Sessions would enter, by its *activation* and the Step's entries, and that is not
   disabled for the Step (see [§3.2.2](#322-effective-environment-parameter-values)), the Step must supply every
   parameter that has no `default`.
8. *required* must not be `false` on an entry that names a *jobEnvironments* entry.
9. *enableIf* is an expression field of type `bool` (see [§7.6](#76-expression-fields)).

Constraints 1–4, 8, and 9 are checked at template validation. Constraint 3 applies to entries as written, enabled or
not, so two entries for one Environment with complementary *enableIf* conditions are an error. Constraints 5 and 6
apply only to an enabled entry. They are checked:

1. At template validation, for an entry that names a *jobEnvironments* entry and whose *enableIf* is absent or `true`.
   Constraint 6 is checked there against literal values only.
2. When the Job is created, for every entry whose *enableIf* is absent or resolves to `true`, once format strings are
   resolved and external Environments are known.

An entry whose *enableIf* is any other expression may turn out to be disabled, so its keys and values are not checked
until the Job is created. Constraint 7 is checked at template validation for the *jobEnvironments* entries, and when the
Job is created for every Environment. At template validation, constraint 7 and any other check that depends on whether
an entry is enabled or an Environment is disabled report an error only as [§7.6](#76-expression-fields) rule 5
describes. Otherwise the check is made when the Job is created.

For an entry that names no *jobEnvironments* entry, template validation can check only constraints 1–4, 8, and 9, and
the type of a literal value where its form fixes one (a list is not a STRING). A validator that is given the
Environment Templates a scheduler will attach, as `openjd run` accepts them, can resolve the entry as
[§3.2.1](#321-resolving-external-environments) describes. It can then check constraints 5–7 before the Job is created.

> **NOTE:** Instead of two entries for one Environment with complementary *enableIf* conditions, write one entry whose
> values are conditional.

#### 3.2.1. Resolving External Environments

When a Job is created from a Job Template and zero or more Environment Templates, each *environment* entry that names no
*jobEnvironments* entry of the Job Template is resolved against the attached Environment Templates. Disabled entries
are resolved too (see *enableIf* in [&lt;StepDependency&gt;](#32-stepdependency)). The rules are:

1. If exactly one attached Environment Template's `environment` has the entry's name, the entry refers to it. For an
   enabled entry, constraints 5 and 6 are checked against that Environment's *envParameterDefinitions*, with one
   exception. If the Environment declares no *envParameterDefinitions*, such as one from an Environment Template that
   does not list `ENV_PARAMS`, and the enabled entry has `required: false`, the entry's *parameters* are ignored: the
   entry supplies no values, its values are not resolved, and constraints 5 and 6 do not apply to them. Each value must
   still have one of the forms of an `<EnvironmentParameterValue>`, as for any entry, so a `null` or an object is an
   error. Implementations should warn when they ignore an entry's *parameters*, naming the entry, the Environment, and
   the ignored keys. The entry still refers to the Environment, and has every other effect of an entry, so it requests
   an `ON_REQUEST` Environment. Otherwise constraints 5 and 6 apply as usual, whatever *required* says. In particular:
    * If an enabled entry with `required: true` supplies parameters to an attached Environment that declares none, the
      submission must be rejected, naming the entry and the parameter.
    * If an enabled entry supplies a key that an attached Environment with *envParameterDefinitions* does not declare,
      the submission must be rejected, naming the entry and the key, even with `required: false`.
2. If none does, then for an enabled entry with `required: true`, the submission must be rejected, naming the entry and
   the missing Environment. Any other entry is ignored.
3. If two or more do, the submission must be rejected, naming the entry and the ambiguous name.
4. An attached Environment with the same name as a *jobEnvironments* entry is not reachable by name from the Job
   Template. Implementations should warn when they see one. Constraint 7 still applies to it, and no entry can supply
   its parameters. So with `activation: BY_DEFAULT`, a parameter without a `default` rejects the submission only if
   some Step's Sessions enter the Environment and it is not disabled for that Step. With `activation: ALWAYS`, such a
   parameter always rejects the submission.
5. Likewise, an attached Environment with the same name as a *stepEnvironments* entry of a Step is not reachable by name
   from that Step (constraint 2). Other Steps of the Job reach it as usual.

Each enabled entry that resolves applies independently of the others. When the scheduler attaches several of the
Environments a Step requests, the Step's Sessions enter all of them, each with the values its own entry supplies. The
*activation* and *enableIf* of an attached Environment decide which Sessions enter it, as for a Job Environment (see
[&lt;Environment&gt;](#4-environment)). An Environment from an Environment Template that does not list `ENV_PARAMS` is
entered by every Session of the Job, whatever the Job Template's entries say. After resolution, constraint 7 is checked
over the combined Job.

> **NOTE:** Every Step of the Job whose Sessions enter an attached `ALWAYS` or `BY_DEFAULT` Environment, which is every
> Step for an `ALWAYS` one and every Step that does not decline a `BY_DEFAULT` one, must supply its parameters that have
> no `default`. An Environment Template intended for Job Templates that do not supply its parameters should therefore
> give every parameter a `default`, or use `activation: ON_REQUEST` so that only the Steps that request it must supply
> values.

#### 3.2.2. Effective Environment Parameter Values

For each Step and each Environment its Sessions would enter, the *effective value* of every parameter of that
Environment is determined when the Job is created:

1. If an enabled *environment* entry of the Step names the Environment and supplies the parameter, the resolved value of
   that entry.
2. Otherwise, the resolved `default` of the parameter.

The effective values are part of the Job. They are checked against the parameter's definition when the Job is created,
for each Environment that is not disabled for the Step (see constraint 6, and
[&lt;EnvironmentParameterDefinition&gt;](#45-environmentparameterdefinition-extension-env_params) for PATH values and
for `default`). The Environment's *hostRequirements*, if any, are resolved for the Step with these values (see
[Combined Host Requirements](#333-combined-host-requirements)). Path mapping rules are applied to PATH-typed effective
values on the Worker Host, as they are to PATH Job Parameters.

An Environment is *disabled* for a Step when its *enableIf* is `false` for the Step, or when it is superseded for the
Step by an earlier Environment of its *exclusiveGroup* ([&lt;Environment&gt;](#4-environment) *exclusiveGroup*). These
rules apply:

1. Whether an Environment is disabled is decided before constraint 7 and the checks of the Step's effective values for
   the Environment. A literal `false` is decided at template validation. An expression is decided when the Job is
   created, by evaluating it with what is known then.
2. An effective value is known when it converts to its parameter's type, whether the Step supplies it or it comes from a
   `default`, and whether or not it meets the parameter's other constraints. These values are unknown:
    * a parameter without a `default` that the Step does not supply;
    * a value whose expression fails to resolve, such as an index out of range;
    * a value that does not convert.

   Each unknown value is `unresolved[T]` of its parameter's type. The *enableIf* is evaluated as the Expression
   Language's progressive evaluation defines, so its result is `true`, `false`, or `unresolved[bool]`.
3. Where the result is `false`, the Environment is disabled. The Step's Sessions do not enter it, and constraint 7 does
   not apply to it. The Step's effective values for it are not checked against their parameters' type and constraints.
   That covers constraint 6 of [&lt;StepDependency&gt;](#32-stepdependency), and the rule that a value for a
   list-typed parameter is a list literal or a single `{{ }}` expression, which is part of its type. Where the result
   is `true`, the Environment is not disabled, and constraint 7 and the checks of its effective values apply, unless it
   is superseded.
4. A disabled Environment is still held to the checks of an entry as written: constraint 5, and the rule that each value
   is one of the forms of an `<EnvironmentParameterValue>`. So a `null` or an object is an error.
5. Where the result is unresolved, it depends on a missing, unresolvable, or unconvertible value, and that is an error.
   The error is reported at template validation when two things hold. First, the value is known to be missing: it has
   no `default`, and no entry supplies it whatever an undetermined entry *enableIf* resolves to. Second, the result
   depends on it whatever every value still unknown at that stage resolves to (see [§7.6](#76-expression-fields) rule
   5). Otherwise the error is reported when the Job is created.
6. An Environment whose *activation* is `ALWAYS` cannot be disabled (see [&lt;Environment&gt;](#4-environment)
   *activation*).

Two effective values are *equal* when they have the same type and the same string form. A value's *string form* is
the text that `{{Env.RawParam.<name>}}` gives it in the Environment, so two values are equal exactly when the
Environment cannot tell them apart. Values are compared as resolved when the Job is created, before any path mapping:

* An INT or a BOOL has one string form for each value, so how it was written does not matter. An INT supplied as `1`
  by one Step and as `"1"`, `" 1 "`, or `"01"` by another resolves to the INT 1 for both, so the values are equal. A
  BOOL supplied as `true` and as `"yes"` is `true` for both. This applies to each integer of a LIST[INT] or
  LIST[LIST[INT]] and each element of a LIST[BOOL].
* A FLOAT keeps the text it was written with, without the white space around it
  ([Expression Language §1.3.4](2026-02-Expression-Language#134-float-value-pass-through), [§7.5](#75-numeric-strings)).
  So `"3.10"` and `"3.1"` are not equal, although they are the same number and the Expression Language's
  `3.10 == 3.1` is `true`, while `"3.10"` and `" 3.10 "` are equal. A FLOAT computed by an expression is written in the
  shortest form that gives back its number, and so is a FLOAT given as a YAML or JSON number rather than a string,
  since a number has no text of its own: the number `1.50` is written `1.5`, so it equals `"1.5"` and not `"1.50"`.
  This applies to each element of a LIST[FLOAT].
* A STRING is compared by its sequence of Unicode code points, with no normalization. `"é"` written as the one code
  point U+00E9 and as `e` followed by U+0301 are not equal.
* A PATH value is compared by its unmapped string, as given
  ([§4.5](#45-environmentparameterdefinition-extension-env_params) item 3). `/data/x` and `/data/./x` are not equal.
* A RANGE_EXPR value's string form is its canonical form ([§3.4.1.1.1](#34111-intrangeexpr)), so two values are equal
  when they denote the same integers. `1-3` and `1,2,3` are equal.
* Two lists are equal when they have the same number of elements and equal elements in the same order.

A render management system can therefore compare values, or key Sessions on them, by each value's type together with
its string form, and for a list the string forms of its elements in order. It needs no numeric comparison and no
canonical form of a number.

A **Session** must not run a Task of a Step unless the Environments it has entered, and not yet exited, are exactly the
Environments that Step's Sessions enter, and each of the Step's effective values for each of them is equal to the value
the Session entered it with. The Environment's `onEnter`, every Task run while it is entered, and its `onExit` then all
see the same values. To run Tasks of a Step whose Environments or values differ, a Session exits Environments, in the
reverse of the order it entered them, and enters others, or enters the same Environment again with that Step's values;
or the render management system runs the Step in another Session (see
[How Jobs Are Run](How-Jobs-Are-Run#environment-parameters)).

### 3.3. `<HostRequirements>`

This entity is used by the template author to describe the requirements on Worker host and/or render manager's available
capabilities that must be satisfied for the Task(s) of the Step to be scheduled to the host.

Each requirement corresponds to an attribute of a host or render manager that must be satisfied to allow the Step to
be scheduled to the host. Some examples of concrete attributes include processor architecture (x86_64, arm64, etc), the
number of CPU cores, the amount of system memory, or available floating licenses for an application. We also allow for
user-defined whose meaning is defined by the customer; a "SoftwareConfig" requirement whose values could be "Option1" or "Option2",
for example.

There are two types of requirements: attribute and amount.

A `<HostRequirements>` is the object:

```yaml
amounts: [ <AmountRequirement>, ... ] # @optional
attributes: [ <AttributeRequirement>, ... ] # @optional
```

Where:

1. *amounts* — Defines a set of quantifiable requirements on the host that must be met and reserved for a Session running
   Tasks from this Step to be scheduled to the host. See: [&lt;AmountRequirement&gt;](#331-amountrequirement).
2. *attributes* — Defines a set of attributes that a host must have for a Session running Tasks from this Step to be
   scheduled to the host. See: [&lt;AttributeRequirement&gt;](#332-attributerequirement).

With the constraints:

1. If this object is provided in a Job Template, then at least one of the *amounts* or *attributes* properties must be
   defined. With the `ENV_PARAMS` extension, this constraint does not apply: on a Step or an Environment, an empty
   object, or one whose *amounts* and *attributes* are empty lists, is valid and means no requirements.
2. The sum of the lengths of the *amounts* and *attributes* arrays must not exceed 50 elements.
3. No two elements in the *amounts* array may have the same value for the *name* property, after the *name* format
   strings have been resolved.
4. No two elements in the *attributes* array may have the same value for the *name* property, after the *name* format
   strings have been resolved.

With the `ENV_PARAMS` extension, an Environment may also have *hostRequirements* (see
[Combined Host Requirements](#333-combined-host-requirements)).

With the `ENV_PARAMS` extension, a requirement that resolves to nothing when the Job is created is discarded. This
applies to the *hostRequirements* of a Step and of an Environment alike:

1. An [&lt;AmountRequirement&gt;](#331-amountrequirement) whose *min* and *max* both resolve to `null` is discarded.
   Both are then omitted ([Expression Language
   §1.3.2](2026-02-Expression-Language#132-evaluation-within-template-schemas)). Only a format-string *min* or *max*,
   which needs the `FEATURE_BUNDLE_1` extension, can resolve to `null`.
2. An [&lt;AttributeRequirement&gt;](#332-attributerequirement) is discarded when it is left with neither *anyOf* nor
   *allOf*, because each of them that it has resolves to `null` and is omitted (Expression Language §1.3.2). Only an
   *anyOf* or *allOf* written as one `{{ }}` expression can resolve to `null` (see [§3.3.2](#332-attributerequirement)).
3. An *anyOf* or *allOf* that has no values after resolution is an error when the Job is created, as an empty list is
   under §3.3.2. This holds for one written as one expression whose result is an empty list. It also holds for one
   written as a list whose items all resolve to `null`, once each `null` item is skipped and each list result is
   flattened (Expression Language §1.3.2). The error names the Step or Environment and the attribute.
4. A *hostRequirements* left with no requirements once its requirements are discarded means no requirements.

Constraints 3 and 4 apply to the requirements left after discarding. A discarded requirement takes no part in the
[Combined Host Requirements](#333-combined-host-requirements). Literal text keeps the rules of §3.3.1 and §3.3.2: an
*amounts* entry written with neither *min* nor *max*, and an *anyOf* or *allOf* written as an empty list, are rejected
at template validation. The exception to constraint 1 covers only an empty object and empty *amounts* and *attributes*
lists.

#### 3.3.1. `<AmountRequirement>`

Amount requirements are the mechanism for defining a quantity of something that the Worker host or render manager needs to have
for a Step to run. They represent quantifiable things that need to be reserved to do the work — vCPUs, memory, licenses, etc. They
are always non-negative floating point valued, and a Step can require a certain amount of that capability to be able to run —
"at least 4 CPU cores" for example. Further, a quantity of each amount required are logically allocated to a Session while that
session is running on a host. A Step requiring, say, "at least 4 CPU cores", might result in a Session with 4 CPU cores allocated
to it being created on a host. Those cores are reserved for that Session while that Session is running on the host; effectively
making the number of available cores on the host 4 less for scheduling purposes during the duration of the Session. Logically
allocating amounts to Sessions is the key mechanism by which system resources can be optimally utilized through bin packing
multiple running Sessions onto hosts at the same time.

An `<AmountRequirement>` is the object:

```yaml
name: <AmountCapabilityName> # @fmtstring
min: <nonnegativefloat> # @optional
min: <nonnegativefloat> | <nonnegativefloatstring>  # @optional @fmtstring @extension FEATURE_BUNDLE_1
max: <positivefloat> # @optional
max: <positivefloat> | <positivefloatstring> # @optional @fmtstring @extension FEATURE_BUNDLE_1
```

Where:`<nonnegativefloatstring>` is a string whose value is the string
representation of a non-negative floating point or integer value in
base-10, `<positivefloatstring>` is a string whose value is the string
representation of a positive floating point or integer value in base-10, each with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *name* — Is a dotted name that identifies the specific host capability that is being required.
2. *min* — If provided, then the host must have at least the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host. If not provided, then the default is 0 unless
   the specific host capability defines a minimum. Can only be a
   `<nonnegativefloatstring>` when using the extension `FEATURE_BUNDLE_1`.
3. *max* — If provided, then the host must have at most the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host. Can
   only be a `<positivefloatstring>` when using the extension `FEATURE_BUNDLE_1`.

Subject to the constraint that at least one of *min* or *max* must be provided. With the `ENV_PARAMS` extension, a
requirement whose *min* and *max* both resolve to `null` is discarded instead (see [§3.3](#33-hostrequirements)).

##### 3.3.1.1. `<AmountCapabilityName>`

A [Format String](#73-format-strings) subject to the following constraints, after the format string has been resolved.

1. Minimum length: 1 character.
2. Maximum length: 100 characters.
3. Its format matches the pattern `[<Identifier>:]amount.<Identifier>[.<Identifier>]*` where:
   1. `[<Identifier>:]` denotes an optional vendor-specific prefix.
   2. This specification has reserved specific values of the first `<Identifier>` after "amount." for use in this and
      future revisions. The reserved values are: "worker", "job", "step", and "task"
4. The value is not case-sensitive - All comparisons between strings of this type must be case-insensitive comparisons.

See [&lt;Identifier&gt;](#71-identifier) for information on the `<Identifier>` substring.

This specification defines the following amount capabilities, but an implementation is allowed, and encouraged, to allow
users to define their own custom capabilities.

|**Capability Name**|**Minimum Value**|**Description**|
|---|---|---|
|amount.worker.vcpu        |1|A number of vCPUs/CPU-cores available on the host.|
|amount.worker.memory      |0|An amount of system memory available on the host. Units: MiB. |
|amount.worker.gpu         |0|A number of GPUs available on the host.|
|amount.worker.gpu.memory  |0|The lower bound of total memory provided by each GPU on the host. For example, if a host has one GPU with 4096 and one GPU with 2048, this value would be 2048. Units: MiB.|
|amount.worker.disk.scratch|0|A static amount of disk storage installed on the host for use as scratch space. Units: GiB.|

#### 3.3.2. `<AttributeRequirement>`

Attribute requirements are the mechanism for defining an abstract or concrete attribute/property the host must have for
a Step to run. They are always defined on a host as a set of strings. A Step can assert that it requires that a host have
specific value(s) of the attribute for it to be scheduled to the host.

An `<AttributeRequirement>` is the object:

```yaml
name: <AttributeCapabilityName> # @fmtstring
anyOf: [ <AttributeCapabilityValue>, ... ] # @optional @fmtstring
anyOf: [ <AttributeCapabilityValue>, ... ] | <ListExpressionString> # @optional @fmtstring @extension ENV_PARAMS
allOf: [ <AttributeCapabilityValue>, ... ] # @optional @fmtstring
allOf: [ <AttributeCapabilityValue>, ... ] | <ListExpressionString> # @optional @fmtstring @extension ENV_PARAMS
```

Where `<ListExpressionString>` is a [Format String](#73-format-strings) that is exactly one `{{ }}` expression with no
surrounding text (see also
[Expression Language §1.3.12](2026-02-Expression-Language#1312-task-parameter-range-field-extensions)), and:

1. *name* — Is a dotted name that identifies the specific host capability that is being required.
2. *anyOf* — For the Step to be scheduled to it, the host's value for the named capability must have **at least one** of
   the given values. This comparison is case-insensitive. Can only be a `<ListExpressionString>` when using the
   extension `ENV_PARAMS`.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.
3. *allOf* — For the Step to be scheduled to it, the host's value for the named capability must have **all** the given
   values. This comparison is case-insensitive. Can only be a `<ListExpressionString>` when using the extension
   `ENV_PARAMS`.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.

Subject to the constraint that at least one of *anyOf* or *allOf* must be provided.

With the `ENV_PARAMS` extension, an *anyOf* or *allOf* that is a `<ListExpressionString>` is evaluated when the Job is
created, with the target type `list[string]?`. A `null` result omits the field
([Expression Language §1.3.2](2026-02-Expression-Language#132-evaluation-within-template-schemas)). A list result is
checked as the list form is after resolution. Each element must satisfy
[&lt;AttributeCapabilityValue&gt;](#3322-attributecapabilityvalue), and the list must have between 1 and 50 elements.
A list has no string form, so a format string that is not exactly one `{{ }}` expression, such as `"x{{Param.A}}"`, is
an error at template validation. The expression's static type is checked against `list[string]?` at template
validation, as far as the values known then allow ([§7.4](#74-template-processing-stages)). See
[§3.3](#33-hostrequirements) for when an attribute requirement is discarded and when it is an error.

##### 3.3.2.1. `<AttributeCapabilityName>`

A [Format String](#73-format-strings) subject to the following constraints, after the format string has been resolved.

1. Minimum length: 1 character.
2. Maximum length: 100 characters.
3. Its format matches the pattern `[<Identifier>:]attr.<Identifier>[.<Identifier>]*` where:
   1. `[<Identifier>:]` denotes an optional vendor-specific prefix.
   2. This specification has reserved specific values of the first `<Identifier>` after "amount." for use in this and
      future revisions. The reserved values are: "worker", "job", "step", and "task"
4. The value is not case-sensitive - All comparisons between strings of this type must be case-insensitive comparisons.

See [&lt;Identifier&gt;](#71-identifier) for information on the `<Identifier>` substring.

This specification defines the following attribute capabilities, but an implementation is allowed, and encouraged, to
allow users to define their own custom capabilities.

|**Capability Name**|**Values**|**Description**|
|---|---|---|
|attr.worker.os.family|linux, windows, macos|The family of operating system on the host.|
|attr.worker.cpu.arch |x86_64, arm64|The architecture of the CPUs on the host.|

A host has exactly one value of each of these two capabilities, so an *allOf* for either of them must have at most one
element. An *allOf* written as a list with more than one element is an error at template validation. With the
`ENV_PARAMS` extension, an *allOf* written as a `<ListExpressionString>` whose result has more than one element is an
error when the Job is created. A custom attribute capability may have several values.

##### 3.3.2.2. `<AttributeCapabilityValue>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Minimum length: 1 character.
2. After the format string has been resolved:
    1. Max length: 100 characters
    2. Unicode alphanumeric characters in the latin character set, plus the underscore and hyphen characters.
    3. Must start with either a letter character or the underscore character.

#### 3.3.3. Combined Host Requirements

With the `ENV_PARAMS` extension, an [&lt;Environment&gt;](#4-environment) in a Job Template's *jobEnvironments* or an
Environment Template may have *hostRequirements*. The *combined host requirements* of a Step are the requirements of
the Step's own *hostRequirements* together with those of every Environment that the Step's Sessions enter. Each
Environment's requirements are resolved with the Step's effective values for that Environment (see
[§3.2.2](#322-effective-environment-parameter-values)). A Session that runs the Step's Tasks may be scheduled only to a
host that satisfies every requirement in the combined set. Every *amounts* requirement in it is reserved for the
Session.

The combined requirements are computed when the Job is created, after the Environments each Step's Sessions enter are
known. They are a conjunction: a host satisfies them when it satisfies each requirement from each source. Amounts do
not add: a Step that requires one GPU and enters an Environment that also requires one GPU reserves one GPU, not two.
Requirements from different sources may name the same capability. Names compare after resolution and ignoring case, as
in §3.3.1.1 and §3.3.2.1. For such requirements, the conjunction is equivalent to the requirements below, and an
implementation may present or store it in that form. Each form depends only on the set of requirements from all
sources, not on the order in which they are combined:

1. The [&lt;AmountRequirement&gt;](#331-amountrequirement)s that name one capability combine to one whose *min* is the
   greatest of their *min*s and whose *max* is the least of their *max*es. A bound that no source gives is omitted from
   the result, and then means what §3.3.1 says, as for a Step's own requirement. If the result's *min* exceeds its
   *max*, no host can satisfy it. The submission must then be rejected, naming the Step, the conflicting sources, and
   the capability. The sources may be the Step and an Environment, or two Environments the Step's Sessions enter.
2. The [&lt;AttributeRequirement&gt;](#332-attributerequirement)s that name one attribute combine together, whatever
   their number. A host has a set of values of an attribute (§3.3.2), and values compare ignoring case. An *anyOf*
   with one value is the same requirement as an *allOf* with that value. Let *B* be the union of every *allOf* list
   and the value of every *anyOf* with one value. *B* is the set of values a host must have.
    1. For `attr.worker.os.family` and `attr.worker.cpu.arch`, of which a host has exactly one value, the requirements
       are equivalent to one *anyOf* whose values are those in every *anyOf* and every *allOf* list. If no value is in
       all of them, no host can satisfy the requirements. The submission must then be rejected, naming the Step, the
       sources that name the attribute, and the attribute. No smaller set of sources need be at fault: *anyOf*
       `[a, b]`, `[b, c]`, and `[a, c]` share no value, though every two of them do.
    2. For any other attribute, the requirements are equivalent to one *allOf* of the values of *B*, if *B* is not
       empty, together with each *anyOf* of two or more values that contains no value of *B*. An *anyOf* that does
       contain one is implied by the *allOf*. A host may have any set of values, so these requirements can always be
       satisfied, and combining them is never an error. For example, *anyOf* `[a]` from one source and *anyOf* `[b]`
       from another are *allOf* `[a, b]`, which a host with both values satisfies.

The constraints of [§3.3](#33-hostrequirements) on list length and on duplicate names apply to each source's
*hostRequirements* separately, not to the combined set. Combining them adds no error other than the conflicts in items 1
and 2.1. Requirements that resolve to nothing are discarded from each source before the sources are combined (see
[§3.3](#33-hostrequirements)).

An Environment's *hostRequirements* apply only to the Sessions that enter it. A Step gets none of an Environment's
requirements when its Sessions do not enter the Environment, for any of the reasons that
[&lt;Environment&gt;](#4-environment) *activation*, *enableIf*, and *exclusiveGroup* give, or because a `required:
false` entry resolved to nothing.

### 3.4. `<StepParameterSpaceDefinition>`

The step parameter space defines the task parameters that are substituted into the `<StepScript>`
to produce all the tasks to run. A `<StepParameterSpaceDefinition>` is the object:

```yaml
taskParameterDefinitions: [ <TaskParameterDefinition>, ... ]
combination: <CombinationExpr> # @optional
```

Where:

1. *taskParameterDefinitions* — This is a list that defines the task parameters over which the Step's script is
   parameterized. Each task parameter defines its name, type, and the range of values that it takes.
   When the `TASK_CHUNKING` is used, only one `CHUNK[INT]` parameter may be included.
    1. Minimum number of elements: If provided, then this array must have at least one element in the list.
    2. Maximum number of elements: The list must contain no more than 16 elements in the list.
2. *combination* — An expression that defines how the task parameters are combined to produce the parameter space that
   maps a Step to a set of Tasks. Each Task has a single value for each task parameter that specifies its coordinates in
   the defined space. If not provided, then the default is all possible combinations of task parameter values.

#### 3.4.1. `<TaskParameterDefinition>`

Definition of a single task parameter; its name, type, and the range of values that it takes.

```bnf
<TaskParameterDefinition> ::= <IntTaskParameterDefinition> |
                              <FloatTaskParameterDefinition> |
                              <StringTaskParameterDefinition> |
                              <PathTaskParameterDefinition> |
                              <ChunkIntTaskParameterDefinition> # @extension TASK_CHUNKING
```

##### 3.4.1.1. `<IntTaskParameterDefinition>`

An integer valued task parameter. An `<IntTaskParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "INT"
range: <IntRangeList> | <IntRangeExpr>
```

With:

```bnf
<IntRangeList> ::= [ <integer> | <intstring> | <TaskParameterStringValue>, ... ]
```

Where `<intstring>` is a string whose value is the string representation of an integer value in base-10,
`<TaskParameterStringValue>` (See [&lt;TaskParameterStringValue&gt;](#342-taskparameterstringvalue)) must resolve to the
string representation of an integer value in base-10, each with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *name* — The name of the parameter.
2. *type* — The literal "INT", defining this parameter as integer valued.
3. *range* — The list of values that the parameter takes on to define Tasks of the Step.
4. `<IntRangeList>` is subject to the constraints:
   * Minimum number of elements: If provided, then this list must contain at least one element.
   * Maximum number of elements: The list must not contain more than 1024 elements.

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` and
2. `Task.RawParam.<name>`

###### 3.4.1.1.1. `<IntRangeExpr>`

This is a [Format String](#73-format-strings) with an expression for providing an array of integer values using a succinct
string representation. The motivating use-case for this form is providing a succinct way to describe a frame range, but
this has been generalized to apply to more than simple positive integer frame numbers.

```bnf
<IntRangeExpr> ::= <Element> | <Element>,<IntRangeExpr>
<Element>      ::= <WS>*<Int><WS>* | <WS>*<Range><WS>* | <WS>*<SkipRange><WS>*
<Range>        ::= <Int><WS>*-<WS>*<Int>
<SkipRange>    ::= <Range>:<Skip>
<Int>          ::= Any integer value (positive, negative, or zero)
<Skip>         ::= base-10 non-zero number
<WS>           ::= whitespace character: tabs or spaces
```

With:

1. `<Int>` — The specific number given
2. `<Range>` = `x-y` —  The set of values $`\{x\} \cup\{ x+m: m\in\mathbb{Z}^+, x+m\leq y\}`$
3. `<SkipRange>` = `x-y:n`— The set of values
   $`\{x\}\cup\{x+mn: m\in\mathbb{Z}^+, x+mn\leq y\textrm{ if }n>0, x+mn\geq y\textrm{ if }n<0\}`$

Subject to the constraint that no two elements of the expression overlap. The *span* of an element is the interval
from the smallest to the largest value in its set, not its written endpoints, so the span of "1-10:4" is 1 to 9 and
the span of "19-23:5" is the single value 19. Two elements overlap when their spans share at least one integer, even
when their sets share no value: "1-9:2,2-10:2" is an error, since the spans 1 to 9 and 2 to 10 intersect.

The number of values that an `<IntRangeExpr>` expands to is not constrained by this specification. In particular, the maximum of 1024 elements that §3.4.1.1 places on an `<IntRangeList>` does not apply to this form; expressing a range of more than 1024 values, such as a long frame range, is the motivating use-case for it. An implementation that needs to bound the number of Tasks a Step may define is expected to do so with its own limit on the Task count, not by constraining this expression.

The elements of the range expression are combined to form a list of values in increasing order.

The value of a range expression is this list; the way it is written, including the order of its elements, how its
values are split into elements, and white space, is not part of the value.

For example:

|`<IntRangeExpr>`|**List of values**|
|---|---|
|"1 - 5"|`[1, 2, 3, 4, 5]`|
|"1 - -1"|`[1]`|
|"-1 - 1"|`[-1,0,1]`|
|"1-5:2"|`[1,3,5]`|
|"10-15:2,1-5"|`[1,2,3,4,5,10,12,14]`|
|"1-10:4"|`[1,5,9]`|
|"1-10:4,10-15"|`[1,5,9,10,11,12,13,14,15]`|
|"1-10:4,9-15"|Error: ranges overlap|
|"1-9:2,2-10:2"|Error: ranges overlap|

**Canonical form.** Each range expression value has one *canonical form*, a string determined by its list of values
alone. Wherever this specification writes a range expression value as a string, it is written in its canonical form,
unless the specification gives that value another form (as it does for a `CONTIGUOUS` chunk; see
[&lt;ChunkIntTaskParameterDefinition&gt;](#3415-chunkinttaskparameterdefinition-extension-task_chunking)).

For a list of values $`v_1 < v_2 < \dots < v_n`$, the canonical form is built by splitting the list, from the left,
into runs:

1. A run starts at the first value not yet in a run, $`v_i`$. If $`v_i`$ is the last value, the run is $`v_i`$ alone.
2. Otherwise let $`s = v_{i+1} - v_i`$, and extend the run to the last value $`v_j`$ such that every two consecutive
   values from $`v_i`$ to $`v_j`$ differ by $`s`$.
3. If the run has three or more values ($`j \geq i + 2`$), it is $`v_i, \dots, v_j`$, and the next run starts at
   $`v_{j+1}`$. Otherwise the run is $`v_i`$ alone, and the next run starts at $`v_{i+1}`$.

Each run is written as `x` when it is the single value `x`; as `x-y` when its values are `x` to `y` with step 1; and
as `x-y:s` when they are `x` to `y` with step `s` > 1. Integers are written in base 10, with a leading `-` when
negative, and with no `+` sign and no leading zeros. The runs are joined by `,`, with no white space.

The canonical form is a valid `<IntRangeExpr>` whose list of values is the original list. Parsing it and writing the
result in canonical form again gives the same string, and two range expressions have the same canonical form exactly
when they have the same list of values.

|List of values|**Canonical form**|
|---|---|
|`[5]`|"5"|
|`[1,2]`|"1,2"|
|`[1,2,3]`|"1-3"|
|`[1,3,5,7,9]`|"1-9:2"|
|`[3,7]`|"3,7"|
|`[1,3,4,5]`|"1,3-5"|
|`[1,2,4]`|"1,2,4"|
|`[1,2,3,5,7,9]`|"1-3,5-9:2"|
|`[2,4,6,8,9,10]`|"2-8:2,9,10"|
|`[13,14,15,16,17,18,19]`|"13-19"|
|`[-3,-2,-1]`|"-3--1"|
|`[-2,-1,3,4,5,7,8,9,12,100]`|"-2,-1,3-5,7-9,12,100"|

So "1-10:4" is written "1-9:4", "5-1:-1" is written "1-5", "1,3,5,7,9" is written "1-9:2", and "19-23:5,13-18" and
"13-18,19" are both written "13-19".

A range expression can denote very many values with few elements, and an implementation should compute the canonical
form without listing the values. One way (informative): represent the value as a sequence of arithmetic progressions
in increasing order, each with a start, a positive step, and a count. Each `<Int>`, `<Range>`, or `<SkipRange>`
element of the grammar is one progression. Walk the runs as above. Extending a run along a progression whose step is
$`s`$ jumps to the end of that progression in one move, and crossing to the next progression compares its first value
with the current one. Each progression is visited a bounded number of times, so the work is proportional to the number
of progressions and never to the number of values. The canonical form has at most two runs per progression, so an
implementation that keeps a range expression as the runs of its canonical form, and builds new values from those runs,
does this work in time proportional to the number of runs. Reading an arbitrary `<IntRangeExpr>` is proportional to
its number of elements, which can exceed its number of runs: "1,2,3,4,5,6" has six elements and one run. The step of a
run of three or more values fits in a 64-bit signed integer; the difference between two consecutive values may not, so
an implementation computes $`s`$ in wider arithmetic or checks for overflow first.

##### 3.4.1.2. `<FloatTaskParameterDefinition>`

A floating point valued task parameter. An `<FloatTaskParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "FLOAT"
range: <FloatRangeList>
```

With:

```bnf
<FloatRangeList> ::= [ <float> | <floatstring> | <TaskParameterStringValue>, ... ]
```

Where `<floatstring>` is a string whose value is the string representation of a floating point value in base-10,
`<TaskParameterStringValue>` (See [&lt;TaskParameterStringValue&gt;](#342-taskparameterstringvalue)) must resolve to the
string representation of a floating point value in base-10, each with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *name* — The name of the parameter.
2. *type* — The literal "FLOAT", defining this parameter as floating point valued.
3. *range* — The list of values that the parameter takes on to define Tasks of the Step.
4. `<FloatRangeList>` is subject to the constraints:
   * Minimum number of elements: If provided, then this list must contain at least one element.
   * Maximum number of elements: The list must not contain more than 1024 elements.

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` and
2. `Task.RawParam.<name>`

##### 3.4.1.3. `<StringTaskParameterDefinition>`

A string valued task parameter. A `<StringTaskParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "STRING"
range: [ <TaskParameterStringValue>, ... ] # @fmtstring
```

1. *name* — The name of the parameter.
2. *type* - The literal "STRING", defining this parameter as string valued.
3. *range* — The list of values that the parameter takes on to define tasks of the step.
   See: [&lt;TaskParameterStringValue&gt;](#342-taskparameterstringvalue).
    1. Minimum list length: One element
    2. Maximum list length: 1024 elements

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` and
2. `Task.RawParam.<name>`

##### 3.4.1.4. `<PathTaskParameterDefinition>`

A string valued task parameter that represents an absolute path to a file or directory, and will automatically have any
defined path mapping applied to it. A `<PathTaskParameterDefinition>` is the object:

```yaml
name: <Identifier>
type: "PATH"
range: [ <TaskParameterStringValue>, ... ] # @fmtstring
```

1. *name* — The name of the parameter.
2. *type* — The literal "PATH", defining this parameter as string valued path parameter.
3. *range* — The list of values that the parameter takes on to define tasks of the step.
   See: [&lt;TaskParameterStringValue&gt;](#342-taskparameterstringvalue).
    1. Minimum list length: One element
    2. Maximum list length: 1024 elements

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` — the value of the parameter with relevant path mapping rules applied to it; and
2. `Task.RawParam.<name>` — the value of the parameter as it was defined, with no path mapping rules applied.

##### 3.4.1.5. `<ChunkIntTaskParameterDefinition>` `@extension TASK_CHUNKING`

An integer valued task parameter, processed as chunks instead of as individual elements.
At most one `CHUNK[INT]` parameter can be specified in a step parameter space. When forming
a chunk to run, all the non-chunked dimensions take on a single value, and the chunked dimension
takes a set of values that satisfies the range constraint. A `<ChunkIntTaskParameterDefinition>` is the object:

```yaml
  name: <Identifier>
  type: "CHUNK[INT]"
  range: <IntRangeList> | <IntRangeExpr>
  chunks:
    defaultTaskCount: <integer> | <intstring> # @fmtstring
    targetRuntimeSeconds: <integer> | <intstring> # @optional @fmtstring
    rangeConstraint: "CONTIGUOUS" | "NONCONTIGUOUS"
```

See section `<IntTaskParameterDefinition>` for the definitions of `<IntRangeExpr>` and `<intstring>`.

1. *name* — The name of the parameter.
2. *type* — The literal "CHUNK[INT]", defining this parameter as integer valued and processed
     as chunks.
3. *range* — The list of values that the parameter takes on to define Tasks of the Step.
4. *chunks* — Specifies how to form sets of values into chunks.
    1. *defaultTaskCount* — How many tasks to combine into a single chunk by default.
        1. Minimum value: 1
    2. *targetRuntimeSeconds* — If provided and its value is greater than 0, the number of seconds
        to aim for when forming chunks. A scheduler can ignore this, or dynamically adjust
        the chunk task count to be closer to this value once some chunks have completed.
        When the value is 0, a scheduler should ignore this configuration and use `defaultTaskCount`
        for each chunk.
        1. Minimum value: 0
    3. *rangeConstraint* — If CONTIGUOUS, a chunk must always be a contiguous range
        of integers, written as two integers separated by "-", `<N>-<M>`, like a single "5-5" or interval "1-10",
        even when it has one or two values. This is the only range expression value this specification does not
        write in canonical form.
        If NONCONTIGUOUS, a chunk can be an arbitrary set of integers, written in the canonical form of
        [§3.4.1.1.1](#34111-intrangeexpr) like "1,3,7,9" or "1-3,5-9:2". Frame ranges are inclusive, so "10-20"
        contains 11 frames.
5. `<IntRangeList>` is subject to the constraints:
   * Minimum number of elements: If provided, then this list must contain at least one element.
   * Maximum number of elements: The list must not contain more than 1024 elements.

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` and
2. `Task.RawParam.<name>`

#### 3.4.2. `<TaskParameterStringValue>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Allowed characters: Any
2. Minimum length: 1 character.
3. Maximum length: 1024 characters after the format string has been resolved.

With the EXPR extension, an element of a task parameter's `range` list that is exactly `"{{<expr>}}"` is a list
item, which can resolve to no value or to several. See
[Task Parameter Range Field Extensions](2026-02-Expression-Language#1312-task-parameter-range-field-extensions).

#### 3.4.3. `<CombinationExpr>`

The combination expression defines how to combine the task parameters to define the parameter space of the Step. If not
provided then the expression defaults to the product of all defined task parameters. The string takes the form:

```bnf
<CombinationExpr> ::= <CombinationExpr> '*' <Element> | <Element>
<Element>         ::= <Associative> | <Identifier>
<Associative>     ::= '(' <ExprList> ')'
<ExprList>        ::= <ExprList>,<CombinationExpr> | <CombinationExpr>
```

Subject to the following constraints:

1. Allowed characters: Any allowed in an `<Identifier>` plus the space, `*`, `(`, and `)` characters.
2. Minimum length: 1 character.
3. Maximum length: 1280 characters.
4. Each `<Identifier>` in the expression must be the name of a defined task parameter, and each task parameter must occur
   exactly once in the entire expression.
5. Every comma-separated expression within an associative operator must have the exact same number of values defined
   in their range.
6. If a task parameter is chunked, for example it has type `CHUNK[INT]`, it must not be
   combined with any other task parameter using the associative operator. For example if
   `A` is chunked, then `A * B` is permitted but `(A, B)` is an error.

For example, given the four Task Parameters named "A", "B", "C", and "D" with values:

```python
A=[1,2,3]
B=[10,11,12]
C=[20,21]
D=["a","b","c"]
```

The following table lists some expressions and the resulting parameter space.

|**Expression**|**Parameter Space**|
|---|---|
|A * B     |(A=1,B=10), (A=1,B=11), (A=1,B=12), (A=2,B=10), (A=2,B=11), ...|
|(A,B)     |(A=1,B=10), (A=2,B=11), (A=3,B=12)|
|(A,B) * C |(A=1,B=10,C=20), (A=1,B=10,C=21), (A=2,B=11,C=20), (A=2,B=11,C=21), ...|
|(A,B,D)   |(A=1,B=10,D=a), (A=2,B-11,D=b), (A=3,B=10,D=c)|
|(A,C)     |Error: length mismatch (A and C have differing numbers of values)|
|(A,B,A)   |Error: each parameter may only appear once in the expression.|

If `A` has type `CHUNK[INT]`, the parameter space is the same as if it had type `INT`,
but each chunk provided to the `onRun` action specifies an integer range expression for
`A` instead of a single value. The scheduler might select the following chunks when
`rangeConstraint` is set to `CONTIGUOUS`:

(A="1-1", B=10), (A="2-2", B=10), (A="3-3", B=10),
(A="1-2", B=11), (A="3-3", B=11), (A="1-3", B=12)

### 3.5. `<StepScript>`

The Script of a Step defines the properties of the action that the Step runs on a Worker host.

A `<StepScript>` is the object:

```yaml
let: <LetBindings> # @optional @extension EXPR
actions: <StepActions> # @incompatible python | bash | cmd | powershell | node
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional @incompatible python | bash | cmd | powershell | node
python | bash | cmd | powershell | node: <SimpleAction> # @optional @fmtstring[host] @incompatible command embeddedFiles @extension FEATURE_BUNDLE_1
```

Where:

1. *let* — An ordered list of expression bindings evaluated once per task. Bound names are available in *actions*
   and *embeddedFiles* fields, and can reference `Task.Param.*` values. See: [&lt;LetBindings&gt;](#36-letbindings).
2. *actions* — The Actions that are run by Tasks of the Step.
3. *embeddedFiles* — Files embedded into the Step that are materialized to a Session's working directory as the Step's
   Task is running within the Session. See: [&lt;EmbeddedFile&gt;](#6-embeddedfile).
   1. Minimum number of items: If defined, then there must be at least one element in this list.
   2. Maximum number of items: There is no limit on the number of elements in this list.
4. *bash | cmd | node | powershell | python* - Syntactic sugar for scripts,
   removes some commonly needed boilerplate for the given script interpreter.

The format string scopes available to format strings within a `<StepScript>` are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters.
2. `Session.*` — Values such as the Session's working directory.
3. `Task.*` — Values of embedded file locations defined within the `<StepScript>`, and Task Parameters.
4. Names bound by `let` in the enclosing `<StepTemplate>` and `<StepScript>`. Available with the `EXPR` extension.

#### 3.5.1. `<StepActions>`

The Actions of a Step are the set of commands that are run by the Worker Agent to accomplish the goal(s) of the Step.

```yaml
onRun: <Action>
```

Where:

1. *onRun* — The action that is run when a Task for the Step is run on a host. See: [&lt;Action&gt;](#5-action).

### 3.6. `<LetBindings>`

Available when using the `EXPR` extension.

A `<LetBindings>` is an ordered array of `<LetBinding>` strings:

```yaml
let:
  - <LetBinding>
  - <LetBinding>
  ...
```

Bindings are evaluated in declaration order. Later bindings can reference names from earlier bindings in the same
`let` block. A binding that shadows a previous binding in the same `let` block or any enclosing scope is an error.
For example, a `let` binding in a `<StepScript>` cannot shadow a binding from the enclosing `<StepTemplate>`'s `let`
block, and a `let` binding in a `<StepTemplate>`'s *stepEnvironments* cannot shadow a binding from that step's `let` block.

Constraints:
1. Minimum number of items: If defined, then there must be at least one element in this list.
2. Maximum number of items: 50.

#### 3.6.1. `<LetBinding>`

A `<LetBinding>` is a string containing a Python assignment expression:

```bnf
<LetBinding>     ::= <UserIdentifier><WS>*"="<WS>*<Expression>
<UserIdentifier> ::= [a-z_][A-Za-z0-9_]*
<Expression>     ::= (any valid expression as defined by the EXPR extension)
<WS>             ::= whitespace character: tabs or spaces
```

Where:

1. The `<UserIdentifier>` must start with a lowercase letter or underscore. This ensures user-defined names never
   conflict with spec-defined symbols (`Param`, `Task`, `Session`, `Env`, `RawParam`), which always start with an
   uppercase letter.
2. Minimum length of `<UserIdentifier>`: 1 character.
3. Maximum length of `<UserIdentifier>`: 512 characters.
4. The `<Expression>` is evaluated according to the rules defined by the `EXPR` extension. See:
   [Expression Language Specification](2026-02-Expression-Language).
5. The type of the binding is the natural result type of the expression.

Examples:

```yaml
let:
  - frame_count = Param.EndFrame - Param.StartFrame + 1
  - output_dir = Param.OutputRoot / Param.ProjectName
  - files = [Param.InputDir / f for f in Param.FileNames]
```

#### 3.6.2. Let Binding Scope Summary

The following table summarizes where `let` bindings can appear, what symbols they can reference,
and where the bound names are available:

| Location | Can Reference | Bound Names Available In |
|----------|---------------|--------------------------|
| `<StepTemplate>.let` | `Param.*`, `RawParam.*`, `Job.Name`, `Step.Name`, earlier bindings in same `let`, and with `ENV_PARAMS` `Job.EnvNames` | *stepEnvironments*, *hostRequirements*, *parameterSpace*, *script* (including nested `<StepScript>.let` or `<SimpleAction>.let`), and with `ENV_PARAMS` the *parameters* values and *enableIf* of *dependencies* entries |
| `<StepScript>.let` | `Param.*`, `RawParam.*`, `Task.Param.*`, `Task.RawParam.*`, `Session.*`, `Task.File.*`, `Job.Name`, `Step.Name`, step-level bindings, earlier bindings in same `let` | *actions*, *embeddedFiles* |
| `<SimpleAction>.let` | `Param.*`, `RawParam.*`, `Task.Param.*`, `Task.RawParam.*`, `Session.*`, `Job.Name`, `Step.Name`, step-level bindings, earlier bindings in same `let` | *script*, *args* |
| `<EnvironmentScript>.let` | `Param.*`, `RawParam.*`, `Session.*`, `Env.File.*`, `Job.Name`, earlier bindings in same `let`, and with `ENV_PARAMS` `Job.EnvNames` and the enclosing Environment's `Env.Param.*` and `Env.RawParam.*` | *actions*, *embeddedFiles* |

Note: `Task.Param.*` and `Task.RawParam.*` are only available in `<StepScript>` and `<SimpleAction>` contexts because task parameter
values are not known until task execution time.

Note: `Task.File.*` symbols in `<StepScript>.let` and `Env.File.*` symbols in `<EnvironmentScript>.let` refer to
embedded files defined in the same script. The file path is determined before evaluation, so `let` bindings can
reference the path where the file will be written, even though the file content (which may also contain format
strings) is evaluated separately.

Note: `Job.Name` is concrete at job creation, so it is available in every `let` scope. `Step.Name` is scoped to the
Step Template (see [7.3.1](#731-value-references)), so it is available in the Step-side `let` scopes but not in
`<EnvironmentScript>.let`, which may also appear in a Job-level environment or a standalone environment template where
no enclosing Step exists.

## 4. `<Environment>`

The Environment is a mechanism provided in this specification to enable users to amortize expensive, or time-consuming,
setup and tear-down operations of the worker host's environment over a sequence of Tasks run back-to-back on the worker.
Each Environment defines actions to run on a host when entering or exiting the Environment.

An `<Environment>` is the object:

```yaml
name: <EnvironmentName>
description: <Description> # @optional
envParameterDefinitions: [ <EnvironmentParameterDefinition>, ... ] # @optional @extension ENV_PARAMS
activation: <EnvironmentActivation> # @optional @extension ENV_PARAMS
hostRequirements: <HostRequirements> # @optional @extension ENV_PARAMS
enableIf: <Expression> # @optional @expr bool @extension ENV_PARAMS
exclusiveGroup: <Identifier> # @optional @extension ENV_PARAMS
script: <EnvironmentScript> # @optional
variables: <EnvironmentVariables> # @optional
```

Where:

1. *name* — An identifier given to the environment that is unique within the Environment's defined scope: the Job
   Template for a Job Environment, and the Step Template for a Step Environment.
2. *description* — A description to apply to the environment. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *envParameterDefinitions* — The parameters that a Step whose Sessions enter this Environment may supply values for,
   through an *environment* entry in its *dependencies* (see [&lt;StepDependency&gt;](#32-stepdependency)). Their
   values are available within this Environment as `Env.Param.<name>` and `Env.RawParam.<name>`.
   See: [&lt;EnvironmentParameterDefinition&gt;](#45-environmentparameterdefinition-extension-env_params). Available
   with the `ENV_PARAMS` extension. Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Maximum number of elements: 50.
    3. No two definitions in this list may have the same value for the `name` property. A name may coincide with a Job
       Parameter name or with a parameter of another Environment; they do not conflict.
4. *activation* — Which Sessions of the Job enter this Environment. `<EnvironmentActivation>` is one of:
    * `ALWAYS` — Every Session of the Job enters this Environment, in its position in the Job's Environment order
      ([§1.1](#11-job-template) item 7). No Step can leave it out. A Step's disabled *environment* entry for it is an
      error, and so is its *enableIf* being `false` for a Step. Either error names the Step and the Environment. It is
      reported at the earliest stage at which it is known (see [§7.6](#76-expression-fields) rule 5): at template
      validation for a literal `false`, and otherwise when the Job is created. For a disabled entry, template validation
      reports it only for an entry that names a *jobEnvironments* entry. A `true` *enableIf* is not an error.
    * `BY_DEFAULT` — Every Session of the Job enters this Environment, in its position in the Job's Environment order,
      except the Sessions of a Step that declines it with a disabled *environment* entry, and of a Step for which its
      *enableIf* is `false`. This is the default in a document that lists `ENV_PARAMS`: an Environment there that omits
      *activation* has `BY_DEFAULT`.
    * `ON_REQUEST` — Only the Sessions of a Step that requests this Environment, through an enabled *environment* entry
      in its *dependencies*, enter it, less any Step for which its *enableIf* is `false`.

   An Environment from a document that does not list `ENV_PARAMS` behaves as one with `activation: ALWAYS` and no
   *enableIf*: every Session of the Job enters it. Unlike for an `ALWAYS` Environment, a Step's disabled *environment*
   entry for it has no effect and is not an error (see [&lt;StepDependency&gt;](#32-stepdependency) *enableIf*). So a
   Job Template that lists `ENV_PARAMS` cannot leave out an Environment written before the extension, such as one that
   a render management system attaches to every Job for licensing or auditing, and its `required: false` entries work
   whether or not an attached Environment lists the extension. In a Job Template that does not list `ENV_PARAMS`, no
   Step has an *environment* entry and no Environment has an *enableIf*, so its Environments are entered by every
   Session either way.

   A Session that does not enter an Environment does not enter or exit it, does not have its *variables* set, and does
   not have it in its Environment stack. The Environments a Session does enter keep their relative order. An
   Environment whose *activation* is `ALWAYS` is entered by every Step's Sessions, or the Job is rejected, and one from
   a document that does not list `ENV_PARAMS` is entered by every Step's Sessions. So a check that depends on whether a
   Step's Sessions enter either may treat it as entered. Such checks include
   [&lt;StepDependency&gt;](#32-stepdependency) constraint 7, the `WRAP_ACTIONS` single-layer rule, and the
   [Combined Host Requirements](#333-combined-host-requirements). Available with the `ENV_PARAMS` extension.
   Constraints:
    1. An implementation must reject an `<EnvironmentActivation>` it does not recognize. The values are case-sensitive,
       as are this schema's other enumerated values except parameter type names. `always` and `On_Request` are not
       recognized.
5. *hostRequirements* — Requirements on the Worker Host that every Session entering this Environment must satisfy, in
   addition to those of the Step whose Sessions they are. The object is a
   [&lt;HostRequirements&gt;](#33-hostrequirements) with the same shape and constraints as on a `<StepTemplate>`,
   including the `ENV_PARAMS` rules for empty and discarded requirements. Its format strings may reference only the
   values that the [`ENV_PARAMS` Scope Summary](#732-env_params-scope-summary) gives. They are
   resolved when the Job is created, once for each Step whose Sessions enter the Environment, with that Step's effective
   values (see [§3.2.2](#322-effective-environment-parameter-values)). So one Environment may impose different
   requirements on different Steps. How the requirements combine with the Step's is specified in [Combined Host
   Requirements](#333-combined-host-requirements). Available with the `ENV_PARAMS` extension.
6. *enableIf* — Whether a Step's Sessions enter this Environment. An [expression field](#76-expression-fields) of type
   `bool`. The values it may reference are given in the
   [`ENV_PARAMS` Scope Summary](#732-env_params-scope-summary). It is evaluated when the Job is
   created, once for each Step whose Sessions would otherwise enter the Environment, with that Step's effective values
   (see [§3.2.2](#322-effective-environment-parameter-values)). The Steps whose Sessions would otherwise enter it are
   given by its *activation* and the Steps' *environment* entries, or, for a Step Environment, its own Step. A `null`
   result is an error. If omitted, the Environment is enabled for every such Step. Where it is `false` for a Step,
   that Step's Sessions do not enter the Environment (see *activation*). Available with the `ENV_PARAMS` extension.
7. *exclusiveGroup* — A name shared by Environments of which a Step's Sessions enter at most one, such as Environments
   that each provide software in a different way. See: [&lt;Identifier&gt;](#71-identifier). For each Step, of the
   Environments its Sessions would otherwise enter that have the same *exclusiveGroup* and are not disabled by their
   *enableIf*, only the first in the Job's Environment order ([§1.1](#11-job-template) item 7) is entered. They are
   taken in that order, and once one is entered, the *enableIf* of the later ones is not evaluated for the Step. The
   later ones are *superseded* for the Step: its Sessions do not enter them, and they are disabled for it (see
   [§3.2.2](#322-effective-environment-parameter-values)). Attached Environments come first in the Job's Environment
   order, so an attached Environment can supersede one of the Job Template's *jobEnvironments*. The order in which
   Environments are attached decides which of them a Step uses, and a Step for which the first is disabled uses the
   next. Available with the `ENV_PARAMS` extension. Constraints:
    1. An Environment whose *activation* is `ALWAYS` must not have an *exclusiveGroup*.
8. *script* — The action that is taken by this Environment when it is run on a Worker host.
9. *variables* — A set of environment variable name/value pairs, with the values being
   [Format Strings](#73-format-strings) that are resolved when entering the environment. The specified variables must be
   set prior to running either `onEnter` or `onExit` for the environment, and for all actions that are run with the
   environment active.
10. At least one of "script" or "variables" must be provided.

*envParameterDefinitions*, *activation*, *hostRequirements*, and *exclusiveGroup* are permitted on a Job Template's
*jobEnvironments* entries and on an Environment Template's *environment*. They are not permitted on a
*stepEnvironments* entry.

A check that depends on which Environments a Step's Sessions enter, such as the `WRAP_ACTIONS` single-layer rule
([&lt;EnvironmentActions&gt;](#43-environmentactions) constraint 2), uses what is known at each stage (see
[§7.6](#76-expression-fields) rule 5). Before the Job is created:

* A Step's Sessions may be taken to enter every Environment whose *activation* is `ALWAYS`, and every Environment from
  a document that does not list `ENV_PARAMS`.
* They are known to enter an Environment whose *enableIf* is absent or `true` when the Step would otherwise enter it:
  by `activation: BY_DEFAULT` with no entry for it or with an entry whose *enableIf* is absent or `true`, or through
  such an entry.
* They are known not to enter one whose *enableIf* is `false`, nor a `BY_DEFAULT` or `ON_REQUEST` one for which the
  Step's entry has *enableIf* `false`.
* An Environment with an *exclusiveGroup* is known to be entered only when, in addition, every Environment of the Job
  before it in its group is known not to be entered. A validator that is not given the Environment Templates to be
  attached does not know them, and they come before the Job Template's own Environments, so for it a Job Environment
  with an *exclusiveGroup* is never known to be entered. An Environment with an *exclusiveGroup* is known not to be
  entered when one before it in its group would, by the bullets above, be known to be entered.
* Any other Environment is undetermined.

For example, two wrapping Environments known to be entered violate the single-layer rule whatever a third does.

The format string scopes available to format strings within an Environment are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters.
2. `Session.*` — Values such as the Session's working directory.
3. `Env.*` — Scope of the environment entity itself. Values such as the embedded files defined within the Environment
   entity. With the `ENV_PARAMS` extension, also `Env.Param.*` and `Env.RawParam.*`, the values of this Environment's
   parameters with which the Session entered it (see [§7.3.1](#731-value-references)). A Step's own script cannot
   reference `Env.Param.*`, and no Environment can reference another Environment's parameters.
4. Names bound by `let` in the enclosing `<EnvironmentScript>`. Available with the `EXPR` extension.
5. `WrappedAction.*` — Available within `onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit` only. Carries
   the wrapped `<Action>`'s fields. Available with the `WRAP_ACTIONS` extension.
   See [Wrap hook template variables](#431-wrap-hook-template-variables) for the available fields.
6. `WrappedEnv.Name` — Available within `onWrapEnvEnter` and `onWrapEnvExit` only. The name of the inner
   environment whose action is being wrapped. Available with the `WRAP_ACTIONS` extension.
7. `WrappedStep.Name` — Available within `onWrapTaskRun` only. The name of the step whose task is being
   wrapped. Available with the `WRAP_ACTIONS` extension.

Templates must not reference `WrappedAction.*` outside the three wrap hooks, `WrappedEnv.*` outside
`onWrapEnvEnter` and `onWrapEnvExit`, or `WrappedStep.*` outside `onWrapTaskRun`. Schedulers must reject
templates that violate this scope rule.

Implementations of this specfication must watch STDOUT when running the `onEnter` action for any line matching:

1. The regular expression `^openjd_env: (.*)$`. The captured value must be of the form `<varname>=<value>` where
   `varname` is the name of an environment variable, and `value` is the value to assign to it. The defined value of the
   given variable will be set for all actions that are run with the environment active.
2. The regular expression `^openjd_redacted_env: (.*)$`. The captured value must be interpreted identically to
   openjd_env, and `<value>` shall be redacted with a fixed length string for this and any future occurrences from the
   emitted STDOUT message. Requires the REDACTED_ENV_VARS extension, however supporting applications must honor the
   redaction even when the extension is not specified.
3. The regular expression `^openjd_unset_env: (.*)$`. The captured value must be of the form `<varname>` where
   `varname` is the name of an environment variable. The given environment variable will be unset as long as this
   environment is active. If an environment both sets and unsets a particular environment variable, then the unset takes
   precedence.

### 4.1. `<EnvironmentName>`

A string value subject to the following constraints:

1. Allowable characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 characters.
3. Maximum length: 64 characters. 512 characters if using the
`FEATURE_BUNDLE_1` extension.

### 4.2. `<EnvironmentScript>`

An `<EnvironmentScript>` is the object:

```yaml
let: <LetBindings> # @optional @extension EXPR
actions: <EnvironmentActions>
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional
```

1. *let* — An ordered list of expression bindings evaluated once when the environment is entered. Bound names are
   available in *actions* and *embeddedFiles* fields. See: [&lt;LetBindings&gt;](#36-letbindings).
2. *actions* — The actions to run at different stages of the Environment's lifecycle.
3. *embeddedFiles* — Files embedded into the Environment that are materialized to a Session's working directory as the
   Environment is running within the Session. See: [&lt;EmbeddedFile&gt;](#6-embeddedfile).
   1. Minimum number of items: If defined, then there must be at least one element in this list.
   2. Maximum number of items: There is no limit on the number of elements in this list.

### 4.3. `<EnvironmentActions>`

An `<EnvironmentActions>` is the object:

```yaml
onEnter: <Action> # @optional
onWrapEnvEnter: <Action>    # @optional @extension WRAP_ACTIONS
onWrapTaskRun: <Action>     # @optional @extension WRAP_ACTIONS
onWrapEnvExit: <Action>     # @optional @extension WRAP_ACTIONS
onExit: <Action> # @optional
```

1. *onEnter* — The action run when the environment is being entered on a host.
2. *onWrapEnvEnter* — When provided, runs instead of the `onEnter` action of every *inner* environment that
   enters the session while this environment is active. Available only when using the `WRAP_ACTIONS`
   extension.
3. *onWrapTaskRun* — When provided, runs instead of the task's `onRun` action for every task that runs
   while this environment is active. Available only when using the `WRAP_ACTIONS` extension.
4. *onWrapEnvExit* — When provided, runs instead of the `onExit` action of every *inner* environment that
   exits while this environment is active. Available only when using the `WRAP_ACTIONS` extension.
5. *onExit* — The action run when the environment is being exited on a host.

   > **NOTE:** When *onExit* action does not define a *timeout* the action will default to 300
   seconds, or five minutes. Job schedulers may provide the ability to cancel jobs/steps/tasks. A
   reasonable default expectation should be that OpenJobDescription sessions are able to end and
   cleanup within a bound amount of time.

Subject to the constraint that at least one of *onEnter* or *onExit* must be provided. (With the
`WRAP_ACTIONS` extension, a complete set of wrap hooks also satisfies this requirement.)

> **`WRAP_ACTIONS` extension constraints.**
>
> 1. *All-or-nothing rule.* An environment that defines any of `onWrapEnvEnter`, `onWrapTaskRun`, or
>    `onWrapEnvExit` must define all three. Schedulers must reject templates that define only a subset of
>    the wrap hooks before the session begins.
> 2. *Single-layer rule.* A session must contain at most one environment that defines wrap hooks.
>    Schedulers must reject sessions whose stack contains two or more such environments before
>    entering any environment.
> 3. *EXPR prerequisite.* A template that lists `WRAP_ACTIONS` in `extensions:` must also list `EXPR`.
>    Schedulers must reject templates that list `WRAP_ACTIONS` without also listing `EXPR`.
> 4. The wrapping environment's own `onEnter` and `onExit` are never wrapped; they always run
>    normally.
> 5. *Nothing-to-replace rule.* A wrap hook runs only in place of an action the inner entity
>    defines. When an inner environment defines no `onExit` — or defines no `script` at all (a
>    `variables:`-only environment) — there is nothing to replace, and the corresponding wrap
>    hook must not run for that environment. Every `<StepScript>` defines `onRun`, so
>    `onWrapTaskRun` runs for every task.

#### 4.3.1. Wrap hook template variables

Each wrap hook receives the wrapped `<Action>`'s fields as read-only template variables supplied by the
runtime. The variables have identical names and semantics across all three hooks, so helper scripts can
be reused unchanged.

**Available in `onWrapEnvEnter`, `onWrapTaskRun`, and `onWrapEnvExit`:**

| Variable                          | Type           | Description |
|-----------------------------------|----------------|-------------|
| `WrappedAction.Command`           | `string`       | The `command` from the wrapped action. |
| `WrappedAction.Args`              | `list[string]` | The `args` from the wrapped action. |
| `WrappedAction.Environment`       | `list[string]` | Environment variables defined earlier in the session — `openjd_env` exports and environments' declarative `variables:` maps — as `["KEY=value", ...]`. |
| `WrappedAction.Timeout`           | `int?`         | The timeout in seconds specified on the wrapped action. `null` when the wrapped action specifies no timeout. See the *timeout* defaults table in [&lt;Action&gt;](#5-action). |
| `WrappedAction.Cancelation.Mode`  | `string?`      | The cancelation method of the wrapped action (`TERMINATE` or `NOTIFY_THEN_TERMINATE`). `null` when the wrapped action defines no [&lt;CancelationMethod&gt;](#53-cancelationmethod). |
| `WrappedAction.Cancelation.NotifyPeriodInSeconds` | `int?` | The effective `notifyPeriodInSeconds` of the wrapped action when its cancelation mode is `NOTIFY_THEN_TERMINATE`, with the [&lt;CancelationMethodNotifyThenTerminate&gt;](#532-cancelationmethodnotifythenterminate) defaults applied when the wrapped action omits the field. `null` when the mode is `TERMINATE` or the wrapped action defines no `<Cancelation>`. |

**Additionally available in `onWrapEnvEnter` and `onWrapEnvExit`:**

| Variable          | Type     | Description |
|-------------------|----------|-------------|
| `WrappedEnv.Name` | `string` | The `name` of the inner environment whose action is being wrapped. |

**Additionally available in `onWrapTaskRun`:**

| Variable           | Type     | Description |
|--------------------|----------|-------------|
| `WrappedStep.Name` | `string` | The `name` of the step whose task is being wrapped. |

`WrappedAction.Environment` carries only session-defined variables: variables exported with `openjd_env` —
including by earlier actions that themselves ran via a wrap hook — and entries of entered environments'
declarative `variables:` maps. Host-inherited variables (`HOME`,
`PATH`, `OPENJD_*`, etc.) and host filesystem paths referenced in `WrappedAction.Command` or
`WrappedAction.Args` (for example, `{{Env.File.X}}` resolves to a host path) are not surfaced; the wrapping
environment is responsible for forwarding or path-mapping them into the wrapped execution context.

The `WrappedAction.*` namespace is the single, standardized surface for every field of the wrapped
`<Action>`. When a future specification adds a field to `<Action>`, it must surface under the same
namespace using the field's PascalCased name (e.g., `WrappedAction.LogMessageTimeout`). New fields gated
by an `@extension` activate under this namespace exactly when that extension is active in the template.
Wrap scripts may reference any field they recognize and must tolerate fields they do not.

The wrap hooks and these template variables were introduced in
[RFC 0008](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0008-environment-wrap-actions.md).

### 4.4. `<EnvironmentVariables>`

An `<EnvironmentVariables>` is a map from `<EnvironmentVariableNameString>`s to `<EnvironmentVariableValueString>`s:

```yaml
<EnvironmentVariableNameString>: <EnvironmentVariableValueString>, # @fmtstring[host]
...
```

#### 4.4.1. `<EnvironmentVariableNameString>`

A string value subject to the following constraints:

1. Allowable characters: Alphanumeric characters in the latin character set, and the underscore ('_') character.
   * Note: This is as recommended in
     [Chapter 8 of IEEE Std 1003.1](https://pubs.opengroup.org/onlinepubs/000095399/basedefs/xbd_chap08.html).
2. Minimum length: 1 character.
3. Maximum length: 256 characters.
4. The first character cannot be a digit.

#### 4.4.2. `<EnvironmentVariableValueString>`

A string value subject to the following constraints:

1. Allowable characters: Any
2. Minimum length: 0 characters
3. Maximum length: 2048 characters

### 4.5. `<EnvironmentParameterDefinition>` `@extension ENV_PARAMS`

An `<EnvironmentParameterDefinition>` declares one value that a Step may supply to the Environment that contains it.
It is a [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition) of any type available with the `EXPR` extension,
which `ENV_PARAMS` requires, with the same fields and constraints, except as follows. A field that describes the
parameter to tools, such as *userInterface*, *objectType*, or *dataFlow*, has no effect on Job creation or on how the
Job runs, and does not declare the files that the Job reads or writes.

1. *default* — Optional. A [Format String](#73-format-strings) resolved when the Job is created, which may reference
   the values listed in the [`ENV_PARAMS` Scope Summary](#732-env_params-scope-summary). A literal `default` is written
   as for a `<JobParameterDefinition>` of the same type. A `default` that is a single `{{ }}` expression is evaluated
   with the parameter's type as its target type. Any other `default` resolves to a string, which is converted to the
   parameter's type as a submitted Job Parameter value would be. A list-typed parameter has no string form, so a list
   `default` that is not a literal must be a single `{{ }}` expression. A parameter without a `default` is required
   (see [&lt;StepDependency&gt;](#32-stepdependency) constraint 7).
2. *Constraints* — The parameter's constraints, such as *allowedValues*, *minLength*, and *item*, apply to each Step's
   effective value, whether supplied by the Step or taken from the `default`, except where the Environment is disabled
   for that Step (see [§3.2.2](#322-effective-environment-parameter-values)). A literal `default`, one that contains no
   `{{ }}`, is also checked at template validation, even when every Step supplies the parameter and even when the
   Environment's *enableIf* disables it for every Step that would take the `default`. Any other `default` is checked
   only for the Steps that take it.
3. *PATH values* — A value of a PATH parameter, and each element of a LIST[PATH] value, is used as given. It is never
   joined with a directory, and it need not be absolute: unlike a PATH Job Parameter, whose value the submitting
   workstation resolves and may use to choose files to send with the Job, an Environment parameter value only reaches
   the Environment's own actions, mapped by the path mapping rules on the Worker Host. Its constraints are checked when
   the Job is created, against the unmapped value, and path mapping on the Worker Host does not re-check them.
4. *RANGE_EXPR values* — *minLength* and *maxLength* check both the value as written and its canonical form (see
   [§2.10](#210-jobrangeexprparameterdefinition-extension-expr)). The value as written is the literal's string, a format
   string's resolved string, or the string result of a single `{{ }}` expression. A single expression whose result is
   a `range_expr`, such as `{{Param.Frames}}`, has only its canonical form.

> **NOTE:** Take path values from PATH Job Parameters, through `RawParam.<name>`, so that they have the path format the
> Job's path mapping rules expect. A literal path is portable only across submitters that use its path format. A
> host-local path that an Environment Template owns and that needs no path mapping is better declared as a STRING.

Within the Environment that defines it, an Environment parameter is referenced as `Env.Param.<name>` and
`Env.RawParam.<name>` (see [Value References](#731-value-references)).

Environment parameters were introduced in
[RFC 0010](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0010-environment-parameters.md).

## 5. `<Action>`

An Action is a specific command with arguments that is run on a host. An `<Action>` is the object:

```yaml
command: <CommandString> # @fmtstring[host]
args: [ <ArgString>, ... ] # @optional @fmtstring[host]
timeout: <posinteger> # @optional
timeout: <posinteger> | <posintstring> # @optional @fmtstring @extension FEATURE_BUNDLE_1
cancelation: <CancelationMethod> # @optional
```

Where `<posintstring>` is a string whose value is the string representation of a
positive integer value in base-10, with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *command* — A [Format String](#73-format-strings) containing the name of a runnable command that is run on a Worker
   host.
2. *args* — An array of [Format Strings](#73-format-strings) that will be passed as arguments to the **command** when the
   command is run on the host.
3. *timeout* — The positive number of seconds that the command is given to successfully run to completion. A command that
   does not return before the timeout is canceled and is treated as a failed
   run. Can only be a `<posintstring>` when using the extension `FEATURE_BUNDLE_1`.
   When the value is a single whole-field interpolation expression (`"{{ ... }}"` with no
   surrounding text), its target type is `int?` per the
   [expression evaluation type](2026-02-Expression-Language#expression-evaluation-types) rules:
   a `null` result is treated as if the field were not provided (the defaults below apply), and a
   non-null result MUST be a positive integer.

   The default timeout, if not provided, depends on the action:

   | Action container | Action | Default |
   | --- | --- | --- |
   | `<StepActions>` | `onRun` | *no timeout* |
   | `<EnvironmentActions>` | `onEnter` | *no timeout* |
   | `<EnvironmentActions>` | `onWrapEnvEnter` <sup>2</sup> | *no timeout* |
   | `<EnvironmentActions>` | `onWrapTaskRun` <sup>2</sup> | *no timeout* |
   | `<EnvironmentActions>` | `onWrapEnvExit` <sup>2</sup> | 300 seconds (five minutes) <sup>1</sup> |
   | `<EnvironmentActions>` | `onExit` | 300 seconds (five minutes) <sup>1</sup> |

   <sup>1</sup> Environment exit actions are treated specially. Job schedulers may provide the
   ability to cancel jobs, steps, and tasks. A reasonable default expectation should be that
   OpenJobDescription sessions are able to end and cleanup within a bound duration of time.

   <sup>2</sup> Available with the `WRAP_ACTIONS` extension. The wrap hook's `timeout` field bounds
   the wrap script on the host (infrastructure-side); the `WrappedAction.Timeout` template variable
   carries the wrapped action's timeout (workload-side). When the wrapped action specified no
   timeout, the variable is `null` (it is typed `int?`). Wrap scripts must propagate the wrapped
   timeout to the underlying execution runtime where the runtime exposes a timeout mechanism, and
   should enforce it in-script when the runtime exposes none. Wrap scripts must treat `null` as
   "no timeout" and omit the underlying runtime's timeout flag in that case.

4. *cancelation* — If defined, provides details regarding how this action should be canceled. If not provided, then it is
   treated as though provided with `<CancelationMethodTerminate>`.

The host uses the return code of the **command** run to determine success or failure of the Action. A zero exit code
indicates success, and any non-zero exit code indicates failure. A timeout also indicates failure.

### 5.1. `<CommandString>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Characters allowed: Any unicode character except those in the Cc unicode character category. Note that the specific
   operating system that the command is run on will impose its own additional restrictions on permitted characters.
2. Minimum length: 1 character.
3. Maximum length: There is no maximum string length imposed by this specification. Note that the specific operating
   system that the command is run on will impose its own maximum length.

### 5.2. `<ArgString>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Characters allowed: Any unicode character except those in the Cc unicode character category. Note that the specific
   operating system that the command is run on will impose its own additional restrictions on permitted characters.
2. Minimum length: 0 characters.
3. Maximum length: There is no maximum string length imposed by this specification. Note that the specific operating
   system that the command is run on will impose its own maximum length.

### 5.3. `<CancelationMethod>`

The cancellation method defines the process by which an action is canceled.

```bnf
<CancelationMethod> ::= <CancelationMethodTerminate> | <CancelationMethodNotifyThenTerminate>
```

The *mode* value selects between the two forms. When using the `FEATURE_BUNDLE_1` extension, *mode*
may instead be a [Format String](#73-format-strings):

```yaml
mode: "TERMINATE" | "NOTIFY_THEN_TERMINATE"
mode: "TERMINATE" | "NOTIFY_THEN_TERMINATE" | <fmtstring> # @fmtstring @extension FEATURE_BUNDLE_1
notifyPeriodInSeconds: <posinteger> | <posintstring> # @optional @fmtstring @extension FEATURE_BUNDLE_1
```

When *mode* is a format string, the runtime resolves it when it prepares to run the action:

1. If the resolved value is `"TERMINATE"` or `"NOTIFY_THEN_TERMINATE"`, the object is interpreted as
   the corresponding `<CancelationMethod>` form, and MUST then validate against that form's schema.
   A *notifyPeriodInSeconds* whole-field expression that resolves to `null` is treated as if the
   field were not provided (the schema defaults apply).
2. When the value is a single whole-field interpolation expression (`"{{ ... }}"` with no
   surrounding text), its target type is `string?` per the
   [expression evaluation type](2026-02-Expression-Language#expression-evaluation-types) rules: a
   `null` result causes the entire `<CancelationMethod>` object to be treated as if it were not
   provided — the action is canceled as if by `<CancelationMethodTerminate>`, exactly as when the
   template author declares no *cancelation*.
3. Any other resolved value is an error; the runtime MUST fail the action.

The primary use of a format-string *mode* is RFC 0008 wrap hooks forwarding the wrapped action's
cancelation verbatim (see [wrap hook template variables](#431-wrap-hook-template-variables)):

```yaml
cancelation:
  mode: "{{WrappedAction.Cancelation.Mode}}"
  notifyPeriodInSeconds: "{{WrappedAction.Cancelation.NotifyPeriodInSeconds}}"
```

This forwards every case faithfully: a declared mode is reproduced verbatim; a `null` mode (the
wrapped action declared no `<Cancelation>`) drops the whole *cancelation* object; and a `null`
notify period (mode is `TERMINATE` or undeclared) drops that field so the schema default applies.

#### 5.3.1. `<CancelationMethodTerminate>`

An action defined to cancel by this method cancels the running command by sending it a terminal signal.

A `<CancelationMethodTerminate>` is the object:

```yaml
mode: "TERMINATE"
```

The signal sent to the command is:

1. On Posix systems — Send SIGKILL to the entire process tree when a cancel is requested.
2. On Windows systems — Terminate the entire process tree when a cancel is requested.

#### 5.3.2. `<CancelationMethodNotifyThenTerminate>`

An action defined to cancel by this method cancels the running command by sending it a notification signal that it should
gracefully shut down, waiting for a period of time for the command to exit, and then sending it a terminal signal if it has
not exited by the end of the waiting period.

A `<CancelationMethodNotifyThenTerminate>` is the object:

```yaml
mode: "NOTIFY_THEN_TERMINATE"
notifyPeriodInSeconds: <posinteger> # @optional
notifyPeriodInSeconds: <posinteger> | <posintstring> # @optional @fmtstring @extension FEATURE_BUNDLE_1 # @optional
```

Where `<posintstring>` is a string whose value is the string representation of a
positive integer value in base-10, with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *notifyPeriodInSeconds* — Defines the maximum number of seconds between the two signals. It is possible that the actual
   duration allowed in a particular cancel event will be less than this amount
   if circumstances warrant. Can only be a `<posintstring>` when using the
   extension `FEATURE_BUNDLE_1`.
   1. Maximum value: 600
   2. Defaults:
      * 120 if the Action is the "onRun" action of a `<StepActions>` object.
      * 30 otherwise.
   3. When the value is a single whole-field interpolation expression (`"{{ ... }}"` with no
      surrounding text), its target type is `int?` per the
      [expression evaluation type](2026-02-Expression-Language#expression-evaluation-types) rules:
      a `null` result is treated as if the field were not provided (the defaults above apply), and
      a non-null result MUST be a positive integer within the maximum.

The signals sent to the command are:

1. On Posix systems — Send a SIGTERM, followed by waiting for the notify period in seconds, and then sending SIGKILL to
   the entire process tree if the command is still running.
2. On Windows systems — THIS IS WORK IN PROGRESS. This document will be updated once the Windows implementation has been determined.

Prior to sending the first signal, a file called `cancel_info.json` is written to the Session working directory. The
contents of this file provide an ISO 8601 time in UTC, in the form `<year>-<month>-<day>T<hour>:<minute>:<second>Z`, at
which the notify period will end. This file is in the
[ECMA-404 JavaScript Object Notation (JSON)](https://www.json.org/json-en.html) interchange format with contents:

```json
{
   "NotifyEnd": "<yyyy>-<mm>-<dd>T<hh>:<mm>:<ss>Z"
}
```

Implementation notes:

1. The application that runs the action must watch for the process exit after SIGTERM to detect whether and when the
   cancelation was successful.
2. A process may receive more than one SIGTERM signal with this mode of cancelation. This can occur when the
   application running the action receives a signal of its own that indicates that it must shut down (near)immediately
   while it is waiting for the grace period of a cancel to elapse. These subsequent signals will be accompanied by a
   change to the `cancel_info.json` file in the working directory.

## 6. `<EmbeddedFile>`

A step or environment script can have data attached to it via this mechanism. The embedded data is made available to the
environment/task action(s) as a file within the Session working directory while being run on a host. This file is
written prior to every one of the corresponding actions each time that they are run. The materialized files' permissions
are read-only by only the user under which the task will be run on the worker host.

```bnf
<EmbeddedFile> ::= <EmbeddedFileText>
```

### 6.1. `<EmbeddedFileText>`

Embedding of a plain text file into the template. The *data* provided in the file is written as a plain text file. This
file is written prior to every one of the script's actions each time that they are run.

```yaml
name: <Identifier>
type: "TEXT"
filename: <Filename> # @optional
runnable: <bool> # @optional
data: <DataString> # @fmtstring[host]
endOfLine: enum("AUTO", "LF", "CRLF") # @optional @extension FEATURE_BUNDLE_1
```

* *name* — The name of the embeded file. This value is used in Format String references to this file.
* *filename* — The filename for the written file. This must strictly be the basename of the filename, and not contain any
  directory pathing. (i.e. `foo.txt` not `dir/foo.txt`). Defaults to a random filename if not provided.
* *runnable* — A boolean `True` value indicates that the file written to disk should have its execute-permissions set
  to true. Defaults to `False` if not provided.
* *data* — The string data that will be written to the file exactly as it appears.
* *endOfLine* — The line endings that the embedded file will have when written
to disk. If `AUTO` the embedded file will have the default line endings of the
host operating system. Default is `AUTO`. Requires the `FEATURE_BUNDLE_1` extension.

The fully-qualified path of the file written by the host can be referenced in format strings using the following names:

1. `Task.File.<name>` - If the embedded file is part of a `<StepScript>` object; or
2. `Env.File.<name>`- If the embedded file is part of an `<Environment>` object.

#### 6.1.1. `<Filename>`

A string subject to the following constraints:

* Min length: 1
* Max length: 64. 256 if using extension `FEATURE_BUNDLE_1`.
* Characters allowed: Any characters allowed in filenames on the host operating system.

<a name="data-string"></a>

#### 6.1.2. `<DataString>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Allowed characters: Any
2. Minimum length: 1 character.
3. Maximum length: No length limit is imposed by this specification.

## 7. Strings

### 7.1. `<Identifier>`

A string subject to the following constraints:

1. Allowed characters:
   * Unicode alphanumeric characters in the latin character set.
   * The underscore character ('_').
2. Must start with a letter or underscore character.
3. Minimum length: 1 character
4. Maximum length: 64 characters. 512 characters if using extension `FEATURE_BUNDLE_1`.

### 7.2. `<Description>`

A string value subject to the following constraints:

1. Allowable characters:
   * Any unicode character except those in the Cc unicode character category.
   * Additionally: newline, carriage return, and horizontal tab characters.
2. Minimum length: 1 characters
3. Maximum length: 2048 characters

### 7.3. Format Strings

Some strings within the Job Template are Format Strings which may contain one or
more ***string interpolation expressions***. A string interpolation expression
within a format string is denoted by a double-pair of open and closing curly braces as in:

```
{{ <StringInterpExpr> }}
```

Where:

```bnf
<StringInterpExpr> ::= <ValueReference>
<ValueReference>   ::= <Name>
<Name>             ::= <Name> "." <Identifier> | <Identifier>
```

The `<ValueReference>` in a Format String is the dotted name of a value available
in the system (See: ...). A Format String is resolved by replacing its string
interpolation expressions with the value of the expression. For example, given the
Format String `"The value of Job Parameter 'Name' is: {{ Param.Name }}"` and a value
for the symbol `Param.Name` of "Bob", the resulting resolved string is
`"The value of Job Parameter 'Name' is: Bob"`.

When the `EXPR` extension is enabled, the `<StringInterpExpr>` grammar is extended to support
the full expression language including arithmetic, conditionals, function calls, list operations,
and more. See the [Expression Language](2026-02-Expression-Language#11-extended-format-string-grammar)
specification for the extended grammar, type system, and evaluation semantics.

#### 7.3.1. Value References

|**Value**|**Description**|**Scope**|
|---|---|---|
|`Param.<ParamName>`|Values of the Job parameters are available within the `Param` object. This is the same as `RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it. |All types except PATH are available in every Format String in the Job Template. For PATH type parameters, this is only available within format strings that are within an Environment or StepScript context.|
|`RawParam.<ParamName>`|Values of the Job parameters are available within the `RawParam` object. This is always the exact input value of the job parameter.|Available in every Format String in the Job Template.|
|`Task.Param.<ParamName>`|Values of task parameters are available within the `Task.Param` object. This is the same as `Task.RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it.|Available within the Step Script Actions and Embedded Files.|
|`Task.RawParam.<ParamName>`|Values of task parameters are available within the `Task.Param` object.|Available within the Step Script Actions and Embedded Files.|
|`Task.File.<name>`|The filesystem location to which the Task Embedded File with key `<name>` has been written.| Available within the Step Script Actions and Embedded Files.|
|`Env.File.<name>`|The filesystem location to which the Environment Attachment with key `<name>` has been written.|Available within the Environment Script Actions and Embedded Files.|
|`Env.Param.<ParamName>`|The value of the Environment parameter `<ParamName>` with which the Session entered the Environment, which is the effective value for every Step whose Tasks the Session runs (see [§3.2.2](#322-effective-environment-parameter-values)). Read as `Param.<ParamName>` reads a Job Parameter of its type, with the same types and path mapping. Requires the `ENV_PARAMS` extension.|Available within the Environment that declares the parameter: its `variables`, its `hostRequirements` and `enableIf` (types other than PATH and LIST[PATH]), and its Script's `let`, Actions, and Embedded Files. Not available in any other Environment or in a Step.|
|`Env.RawParam.<ParamName>`|The same value, read as `RawParam.<ParamName>` reads a Job Parameter of its type. Requires the `ENV_PARAMS` extension.|As for `Env.Param.<ParamName>`.|
|`Session.WorkingDirectory`|The agent is expected to create a local temporary scratch directory for the duration of a Session. This builtin provides the location of that temporary directory. This is the working directory that the Worker Agent uses when running the task.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|
|`Job.Name`|The resolved name of the Job. This is a `string` type. Requires the `EXPR` extension.|Available in every Format String in the Job Template, except the `name` field of the Job Template itself.|
|`Job.EnvNames`|The `name` of each Environment of the Job, in the order a Session that entered all of them would enter them. This is a `list[string]` type. Requires the `ENV_PARAMS` extension.|See below the table.|
|`Step.Name`|The name of the current Step. This is a `string` type. Requires the `EXPR` extension.|Available within the Step Template scope: `stepEnvironments`, `hostRequirements`, `parameterSpace`, and `script`, and with the `ENV_PARAMS` extension the *parameters* values and *enableIf* of `dependencies` entries.|
|`Session.HasPathMappingRules`|This value can be used to determine whether path mapping rules are available to the Session. Without the `EXPR` extension, it is string valued, with values "true" or "false". With the `EXPR` extension enabled, it is a `bool` type. "true"/`True` means that the path mapping JSON contains path mapping rules. "false"/`False` means that the contents of the path mapping JSON are the empty object.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|
|`Session.PathMappingRulesFile`|This is a string whose value is the location of a JSON file on the worker node's local disk that contains the path mapping rule substitutions for the Session.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|
|`<name>` (let binding)|Names bound by `let` in `<StepTemplate>`, `<StepScript>`, `<SimpleAction>`, or `<EnvironmentScript>`. Names must start with a lowercase letter or underscore (see `<UserIdentifier>`). The type is determined by the expression. Available with the `EXPR` extension.|See [Let Binding Scope Summary](#362-let-binding-scope-summary) for detailed scoping rules.|

`Job.EnvNames` lists the Environments attached from Environment Templates, in the order they are attached, followed by
the Job Template's `jobEnvironments`, in the order the Job Template lists them (see [§1.1](#11-job-template) item 7). It
lists them whatever their `activation`. Step Environments are not included. A name appears once per Environment, so it
appears twice if two attached Environments share it. An Environment that its `enableIf` disables for some or every Step
is still listed. `Job.EnvNames` is a list, so it is usable only within a `{{ }}` expression or an expression field. It
is available in every format string or expression field of a Job Template or Environment Template that is resolved at
Job creation or later. That includes an Environment's `hostRequirements` and `enableIf` and the `let`, actions, and
embedded files of its script. It is concrete at Job creation once the attached Environments are known. It is not
available in an Environment parameter `default` or in the Job Template's `name`. It names what the Job has, not what a
particular Step's Sessions enter, so it is the same for every Step and does not by itself affect which Steps may share a
Session.

#### 7.3.2. `ENV_PARAMS` Scope Summary

With the `ENV_PARAMS` extension, these fields are resolved when the Job is created, and may reference only the values
listed. The Job Parameters they reference are those defined in the top-level *parameterDefinitions* of the document that
contains the field, with their merged values (see [§1.2.1](#121-merging-environment-template-parameter-definitions)).

| Location | Can Reference |
|----------|---------------|
| `<StepDependency>` *environment* entry: the *parameters* values and *enableIf* | `RawParam.*` of any type, `Param.*` other than PATH and LIST[PATH], `Job.Name`, `Job.EnvNames`, `Step.Name`, and the names bound by the Step's `let` |
| `<Environment>` *hostRequirements*, and the *enableIf* of a *jobEnvironments* entry or of an Environment Template's *environment* | `RawParam.*` of any type, `Param.*` other than PATH and LIST[PATH], `Job.Name`, `Job.EnvNames`, and this Environment's own `Env.RawParam.*` of any type and `Env.Param.*` other than PATH and LIST[PATH] |
| `<Environment>` *enableIf* of a *stepEnvironments* entry | `RawParam.*` of any type, `Param.*` other than PATH and LIST[PATH], `Job.Name`, `Job.EnvNames`, `Step.Name`, and the names bound by the Step's `let` |
| `<EnvironmentParameterDefinition>` *default* | `RawParam.*` of any type and `Param.*` other than PATH and LIST[PATH] |

No other scope is available to these fields. In particular, `Task.*`, `Session.*`, `Env.File.*`, and another
Environment's parameters are not available, and an Environment's *hostRequirements* and *enableIf* in a
*jobEnvironments* entry or an Environment Template cannot read `Step.Name` or a Step's `let` bindings.

### 7.4. Template Processing Stages

A Job Template is processed in stages as more information becomes available. At each stage,
different sets of values are known, which determines which format strings can be fully resolved.

| Stage | When | Known Values | Unknown Values | What Happens |
|-------|------|-------------|----------------|--------------|
| **Template validation** | `openjd check` or equivalent | Literal values, parameter type declarations | `Param.*`, `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*`, `Env.Param.*`, `Job.EnvNames` | Syntax validation, structural checks. With the `EXPR` extension: type checking of expressions using declared parameter types. `Job.Name` and `Step.Name` are available as `unresolved[string]`. With the `ENV_PARAMS` extension: `Env.Param.*` is type-checked against the Environment's *envParameterDefinitions* and `Job.EnvNames` is `unresolved[list[string]]`; literal Environment parameter `default`s, and literal `environment:` values for Job Environments in entries whose *enableIf* is absent or `true`, are checked against their definitions. |
| **Job creation** | Job submission with parameter values | `Param.*`, `RawParam.*`; with `ENV_PARAMS`, at the end of this stage, each Step's Environment parameter effective values | `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*` | Parameter values are bound. Format strings not annotated `@fmtstring[host]` are resolved (e.g., `name`, `parameterSpace` ranges). PATH and `LIST[PATH]` Job Parameter defaults must be relative and are joined with the job template directory (see [§2.2](#22-jobpathparameterdefinition)); relative PATH and `LIST[PATH]` parameter values are joined with the current working directory. With the `EXPR` extension: `let` bindings in `<StepTemplate>` are evaluated; expressions in TEMPLATE scope are fully evaluated; `Job.Name` and `Step.Name` are concrete. With the `ENV_PARAMS` extension, the steps of [§7.4.1](#741-job-creation-with-env_params) are taken. |
| **Task execution** | On the worker host | All values: `Param.*`, `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*`, `Env.Param.*`, path mapping rules | *(none)* | Format strings annotated `@fmtstring[host]` are resolved. Path mapping rules are applied to PATH-type parameters, including PATH and LIST[PATH] Environment parameters (`ENV_PARAMS`). Embedded files are written. With the `EXPR` extension: `let` bindings in `<StepScript>` and `<EnvironmentScript>` are evaluated; all remaining expressions are fully evaluated. |

The `@fmtstring` and `@fmtstring[host]` annotations in this specification indicate which stage
a format string is resolved in. An expression field, marked `@expr <type>` (see [§7.6](#76-expression-fields)),
states its stage in its own definition. A format string annotated `@fmtstring` (without `[host]`) is
resolved at job creation time. A format string annotated `@fmtstring[host]` is resolved at task
execution time on the worker host.

With the `EXPR` extension enabled, expressions that reference values not yet known at a given
stage are type-checked using the declared types of those values, catching type errors as early
as possible. See the [Expression Language](2026-02-Expression-Language) specification for details.

#### 7.4.1. Job Creation with `ENV_PARAMS`

With the `ENV_PARAMS` extension, Job creation takes these steps in order:

1. The Environment Templates attached to the Job are determined. `Job.EnvNames` is concrete before any TEMPLATE-scope
   expression of the Job, including a Step's `let` bindings, is evaluated.
2. Each *environment* entry's *enableIf* is evaluated.
3. Each entry that names no *jobEnvironments* entry, enabled or disabled, is resolved against the attached Environments
   (see [§3.2.1](#321-resolving-external-environments)).
4. The set of Environments each Step's Sessions would enter is fixed from each Environment's *activation* and the
   Step's entries. An enabled entry requests an `ON_REQUEST` Environment. A disabled entry declines a `BY_DEFAULT` one,
   or, for an `ALWAYS` one, causes the Job to be rejected, naming the Step and the Environment (see
   [&lt;StepDependency&gt;](#32-stepdependency) *enableIf*). It has no effect on an Environment from a document that
   does not list `ENV_PARAMS`, which is in every Step's set (see [&lt;Environment&gt;](#4-environment) *activation*).
5. Environment parameter defaults and *environment* entry values are resolved into each Step's effective values. The
   *parameters* of an entry that [§3.2.1](#321-resolving-external-environments) item 1 ignores are not resolved.
6. Each Environment's *enableIf* is evaluated for each such Step, with the effective values that are known (see
   [§3.2.2](#322-effective-environment-parameter-values)), in the Job's Environment order. Where it is `false`, it
   removes the Environment from the Step's set, or, for an Environment whose *activation* is `ALWAYS`, causes the Job to
   be rejected, naming the Step and the Environment (see [&lt;Environment&gt;](#4-environment) *activation*). Once an
   Environment with an *exclusiveGroup* remains in the Step's set, the later Environments of that group are superseded:
   they are removed from the Step's set, and their *enableIf* is not evaluated for the Step (see
   [&lt;Environment&gt;](#4-environment) *exclusiveGroup*).
7. Constraint 7, the other checks of the effective values, and every other check over the Step's set of Environments,
   such as the `WRAP_ACTIONS` single-layer rule, are made for the Environments that remain in each Step's set (see
   [§3.2.2](#322-effective-environment-parameter-values)).
8. Each Environment's *hostRequirements* are resolved with each entering Step's effective values. Requirements that
   resolve to nothing are discarded from them and from the Step's own, and an *anyOf* or *allOf* that resolves to no
   values is an error (see [§3.3](#33-hostrequirements)). They are then combined with the Step's own (see
   [Combined Host Requirements](#333-combined-host-requirements)).

Environment parameter PATH and LIST[PATH] values are used as given, never joined with any directory (see
[§4.5](#45-environmentparameterdefinition-extension-env_params)).

### 7.5. Numeric strings

`<intstring>`, `<posintstring>`, `<floatstring>`, `<nonnegativefloatstring>` and `<positivefloatstring>` are the string
forms of a number. Each may have white space before and after the number, and that white space is ignored:
`" 7 "` is the `<intstring>` 7, and `"2.5\n"` is the `<floatstring>` 2.5. White space inside the number is not allowed,
so `"1 000"` is not an `<intstring>`, and a string that is empty or holds only white space is not a number.

This applies wherever this specification reads a string as one of these forms:

1. a value written in a template, such as a *default* or an element of a *range* list;
2. the string a [Format String](#73-format-strings) resolves to where one of these forms is expected, such as a
   `<TaskParameterStringValue>` element of an `<IntRangeList>` or a `chunks.defaultTaskCount`; and
3. a value given as a string for an INT or FLOAT Job Parameter when a Job is created, and a number given as a string
   inside a value for a LIST[INT], LIST[FLOAT] or LIST[LIST[INT]] Job Parameter
   (see [§2.13](#213-joblistintparameterdefinition-extension-expr),
   [§2.14](#214-joblistfloatparameterdefinition-extension-expr) and
   [§2.16](#216-joblistlistintparameterdefinition-extension-expr)).

The white space is not part of the value. Where the text a number was written with is kept, as the
[Expression Language](2026-02-Expression-Language#134-float-value-pass-through) does for a float value, the white space
is not part of that text.

*White space* is any character with the Unicode `White_Space` property: U+0009 to U+000D, U+0020, U+0085, U+00A0,
U+1680, U+2000 to U+200A, U+2028, U+2029, U+202F, U+205F and U+3000. No other character is white space here. In
particular U+001C to U+001F, U+200B (zero width space) and U+FEFF (zero width no-break space) are not.

### 7.6. Expression Fields

An *expression field* holds one [Expression Language](2026-02-Expression-Language) expression, written without
`{{ }}`. This specification marks one with `@expr <type>`, where `<type>` is the field's *target type* in the
Expression Language's type notation, for example `@expr bool`. A target type may be a choice of types or `any`, as in
`@expr int | string`, for a field that accepts more than one type. An expression field is not a Format String: no text
surrounds the expression and nothing is interpolated. Expression fields are available only in a document that lists the
`EXPR` extension.

The value of an expression field, in YAML or JSON, is one of:

1. A boolean, integer, or float scalar whose type fits the target type (rule 2), which is used as written: `true` or
   `false` for `bool`, `3` for `int`, `3` or `3.0` for `float`. A string is never read this way, so `"true"` is the
   expression `true`, not the literal. For a target type of `string`, every value is an expression, and a constant
   string is written as a string literal inside it (`"'abc'"`).
2. A string, parsed as a single expression. In YAML, quote it where YAML requires, as in
   `"'Docker' not in Job.EnvNames"`.

A null value is an error. It is not read as an omitted field.

Rules:

1. The expression must parse. `{{` is not part of the expression grammar, so a value written as a Format String
   (`"{{x}}"`) is a parse error. An implementation should say in its message that an expression field takes an
   expression without `{{ }}`.
2. The expression's static type must *fit* the target type, as [Expression Language
   §1.2.3](2026-02-Expression-Language#123-implicit-type-coercion) step 1 defines it. That is, it is the target type,
   or one of the target's choices, or the target is `any`, with list element types fitting element-wise. Of the
   conversions of Expression Language §1.2.3 step 2, only the widening of `int` to `float` applies (element-wise for
   lists), as it does for arithmetic operands (Expression Language §2.1.1). An `int` result for a `float` field becomes
   that `float`. No other conversion applies, so a `string` expression is an error for a `bool` field, whatever its
   text. A field that accepts unrelated types says so in its target type, as in `int | string`.

   Where the target type does not admit `nulltype`, an expression of an optional type `U?` whose `U` fits is also
   accepted, and a `null` result is an error when the expression is evaluated. This holds when the field itself is
   optional, too: a `null` result never means the field was omitted. An expression whose static type is `nulltype` is
   an error unless the target admits it. At template validation, `unresolved[U]` is checked as `U`.
3. Each field's definition gives the scopes the expression may reference and the stage at which it is evaluated. The
   `@fmtstring` annotations do not apply to expression fields.
4. Parse errors, type errors, and references to names that are not available are reported at template validation.
5. Until an expression field is evaluated, its value is known only when it is a boolean, integer, or float scalar
   (item 1). Any other value, a constant expression such as `"true"` included, is unknown at an earlier stage. So an
   *environment* entry or an Environment whose *enableIf* is not a literal is undetermined until the Job is created:
   whether the entry is enabled, and whether the Environment is disabled for a Step, is not known before then. A check
   made at an earlier stage that depends on such a field's value reports an error only when the error holds for every
   value the unknown fields could take. Otherwise the check is made again at the stage where the fields are evaluated,
   with the values they then have. An implementation should report an error at the earliest stage at which it holds
   for every such value.

With the `ENV_PARAMS` extension, the *enableIf* of an *environment* entry and of an Environment is evaluated in
template scope, not in a host context. `path` values have POSIX semantics whatever path format the Job's paths have,
and no path mapping applies (see [Expression Language §1.2.1](2026-02-Expression-Language#121-expression-types)). A
`let` binding that it reads has its template-scope value. The format strings of an Environment's *hostRequirements* are
also resolved in template scope, without a host, so they cannot read a path-mapped value.

## 8. `<SimpleAction>`

This object is only available in the extension `FEATURE_BUNDLE_1`

A SimpleAction is syntactic sugar for a command with arguments that is run on
a host. It removes some commonly needed boilerplate for the given script
interpreter. In contrast to `<Action>`, `<SimpleAction>` removes the need for the
`command` property, implicitly prefixes the `args` property, and removes the
need for the `embeddedFiles` property.

The behaviour of the syntactic sugar depends on the key it was specified with:

* *bash* - Implicitly creates a Bash embedded file,
`command` becomes `bash`, and `args` get prefixed with the implicitly
generated file. The file extension is `.sh`. `bash` (all lowercase) is
expected to be available in the runtime environment.

  ```yaml
  steps:
    - name: BashStep
      bash:
        let:  # optional, requires EXPR extension
          - output_file = Param.OutputDir / Param.Pattern.with_number(Task.Param.Frame)
        args: ["--additional-argument"] # optional
        script: |
          # bash code here
          echo Output: {{repr_sh(output_file)}}

  ### syntax sugar equivalent to:

  steps:
    - name: BashStep
      script:
        let:
          - output_file = Param.OutputDir / Param.Pattern.with_number(Task.Param.Frame)
        actions:
          onRun:
            command: bash
            args: ["{{Task.File.<implicitly generated file>}}", "--additional-argument"]
        embeddedFiles:
          - name: <implicitly generated file>
            filename: "<implicitly generated file>.sh"
            type: TEXT
            data: |
              # bash code here
              echo Output: {{repr_sh(output_file)}}
  ```

* *cmd* - Implicitly creates a Batch embedded file,
`command` becomes `cmd`, and `args` get prefixed with
`["/C", "{{Task.File.<implicitly generated file>}}"]`. The file extension is
`.bat`. `cmd` (all lowercase) is expected to be available in the runtime environment.

  ```yaml
  steps:
    - name: CmdStep
      cmd:
        args: ["--additional-argument"] # optional
        script: |
          # batch code here

  ### syntax sugar equivalent to:

  steps:
    - name: CmdStep
      actions:
          onRun:
              command: cmd
              args: ["/C", "{{Task.File.<implicitly generated file>}}", "--additional-argument"]
      embeddedFiles:
          - name: <implicitly generated file>
            filename: "<implicitly generated file>.bat"
            type: TEXT
            data:
                # batch code here
  ```

* *node* - Implicitly creates a JavaScript embedded file,
`command` becomes `node`, and `args` get prefixed with the implicitly
generated file. The file extension is `.js`. `node` (all lowercase) is
expected to be available in the runtime environment.

  ```yaml
  steps:
    - name: NodeStep
      node:
        args: ["--additional-argument"] # optional
        script: |
            # JavaScript code here

  ### syntax sugar equivalent to:

  steps:
    - name: NodeStep
      actions:
          onRun:
              command: node
              args: ["{{Task.File.<implicitly generated file>}}", "--additional-argument"]
      embeddedFiles:
          - name: <implicitly generated file>
            filename: "<implicitly generated file>.js"
            type: TEXT
            data:
                # JavaScript code here
  ```

* *powershell* - Implicitly creates a Powershell embedded file,
`command` becomes `powershell`, and `args` get prefixed with
`["-File", "{{Task.File.<implicitly generated file>}}"]`.
The file extension is `.ps1`. `powershell` (all lowercase) is
expected to be available in the runtime environment.

  ```yaml
  steps:
    - name: PowershellStep
      powershell:
        args: ["--additional-argument"] # optional
        script: |
            # powershell code here

  ### syntax sugar equivalent to:

  steps:
    - name: PowershellStep
      actions:
          onRun:
              command: powershell
              args: ["-File", "{{Task.File.<implicitly generated file>}}", "--additional-argument"]
      embeddedFiles:
          - name: <implicitly generated file>
            filename: "<implicitly generated file>.ps1"
            type: TEXT
            data:
                # Powershell code here
  ```

* *python* - Implicitly creates a Python embedded file,
`command` becomes `python`, and `args` get prefixed with the implicitly
generated file. The file extension is `.py`. `python` (all lowercase) is
expected to be available in the runtime environment.

  ```yaml
  steps:
    - name: PythonStep
      python:
        args: ["--additional-argument"] # optional
            # python code here

  ### syntax sugar equivalent to:

  steps:
    - name: PythonStep
      actions:
          onRun:
              command: python
              args: ["{{Task.File.<implicitly generated file>}}", "--additional-argument"]
      embeddedFiles:
          - name: <implicitly generated file>
            filename: "<implicitly generated file>.py"
            type: TEXT
            data:
                # python code here
  ```

A `<SimpleAction>` is the object:

```yaml
let: <LetBindings> # @optional @extension EXPR
script: <DataString> # @fmtstring[host]
args: [ <ArgString>, ... ] # @optional @fmtstring[host]
timeout: <posinteger> | <posintstring> # @optional @fmtstring
cancelation: <CancelationMethod> # @optional
```

Where `<posintstring>` is a string whose value is the string representation of a
positive integer value in base-10, with optional white space around it
(see [Numeric strings](#75-numeric-strings)), and:

1. *let* — An ordered list of expression bindings evaluated once per task. Bound names are available in *script*
   and *args* fields, and can reference `Task.Param.*` values. See: [&lt;LetBindings&gt;](#36-letbindings).
   Requires both the `FEATURE_BUNDLE_1` and `EXPR` extensions.
2. *script* — The [Data String](#data-string) that will be written to the script
   exactly as it appears.
3. *args* — An array of [Format Strings](#73-format-strings) that will be passed
   as arguments to the **command** when the command is run on the host.
4. *timeout* — The positive number of seconds that the command is given to
   successfully run to completion. A command that does not return before the
   timeout is canceled and is treated as a failed run.

   The default timeout, if not provided, depends on the action:

   | Action container | Action | Default |
   | --- | --- | --- |
   | `<StepActions>` | `onRun` | *no timeout* |
   | `<EnvironmentActions>` | `onEnter` | *no timeout* |
   | `<EnvironmentActions>` | `onWrapEnvEnter` <sup>2</sup> | *no timeout* |
   | `<EnvironmentActions>` | `onWrapTaskRun` <sup>2</sup> | *no timeout* |
   | `<EnvironmentActions>` | `onWrapEnvExit` <sup>2</sup> | 300 seconds (five minutes) <sup>1</sup> |
   | `<EnvironmentActions>` | `onExit` | 300 seconds (five minutes) <sup>1</sup> |

   <sup>1</sup> Environment exit actions are treated specially. Job schedulers
   may provide the ability to cancel jobs, steps, and tasks. A reasonable
   default expectation should be that OpenJobDescription sessions are able to
   end and cleanup within a bound duration of time.

   <sup>2</sup> Available with the `WRAP_ACTIONS` extension. The wrap hook's `timeout` field bounds
   the wrap script on the host (infrastructure-side); the `WrappedAction.Timeout` template variable
   carries the wrapped action's timeout (workload-side). When the wrapped action specified no
   timeout, the variable is `null` (it is typed `int?`). See the *timeout* description in
   [&lt;Action&gt;](#5-action).

5. *cancelation* — If defined, provides details regarding how this action should
   be canceled. If not provided, then it is treated as though provided with `<CancelationMethodTerminate>`.

The host uses the return code of the interpreter run to determine success or
failure of the SimpleAction. A zero exit code indicates success, and any
non-zero exit code indicates failure. A timeout also indicates failure.

## 9. Additional Information

* The Cc unicode character category is all [C0](https://www.unicode.org/charts/PDF/U0000.pdf)
  and [C1](https://www.unicode.org/charts/PDF/U0080.pdf) characters.
  * This is a category of 65 non-printable characters such as NUL, BEL, Backspace, DEL,
     tab, newline, carriage return, and form feed.

## 10. License

Copyright ©2023 Amazon.com Inc. or Affiliates ("Amazon").

This Agreement sets forth the terms under which Amazon is making the Open Job Description
Specification ("the Specification") available to you.

### 10.1. Copyrights

This Specification is licensed under [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/deed.en).

### 10.2. Patents

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

### 10.3. Additional Information

For more info see the [LICENSE file].

[LICENSE FILE]: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/LICENSE
