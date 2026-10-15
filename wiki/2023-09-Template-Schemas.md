# Template Schemas [Version: 2023-09]

This document contains the formal specifications for the Open Job Description Template schemas. There are two schemas
defined in this document:

1. The Job Template describes the shape of a Job, its runtime environment, and all the processes that will run as part
of it. Jobs are created from Job Templates by providing a value for each of the Job Parameters defined in the Template,
and instantiating the template with those values.
2. The Environment Template describes an Environment that is defined outside a Job. This can be used in render management
systems to allow users to define Environments that are automatically applied to Job Templates that are submitted for rendering.
With the `SERVICE` extension, an Environment Template may also, or instead, describe Services that are applied in the
same way.

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
services: [ <Service>, ... ] # @optional @extension SERVICE
externalServices: [ <ServiceRequirement>, ... ] # @optional @extension SERVICE
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
         [SERVICE](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0009-service.md)
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
7. *jobEnvironments* — An ordered list of the environments that are required to run Tasks in the Jobs created by this Job
   Template. These are entered in the order provided at the start of every Session for Tasks in the Job, and exited in the
   reverse order at the end of those Sessions. See: [&lt;Environment&gt;](#4-environment). Constraints:
      1. No two Environments in this list may have the same value for the `name` property.
      2. The Environments defined in this list must not have the same `name` as an Environment
         defined in any Step within the same Job Template.
8. *services* — The Services that the Jobs created from this Job Template run, each started before any Task in its scope
   is scheduled and stopped once its scope has no Task left to run (see
   [How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle)). A Service's scope follows from the template's `dependencies`
   lists (see [Service scope](#91-service-scope)); the order of this list carries no meaning. Available only when using
   the `SERVICE` extension. See: [&lt;Service&gt;](#9-service-extension-service). Constraints:
      1. Minimum number of elements: If provided, then this list must contain at least one element.
      2. Maximum number of elements: The list must not contain more than 10 elements.
      3. No two Services in this list may have the same value for the `name` property.
      4. The `dependencies` of the Job Template's Steps and Services form one graph, which must be acyclic (see
         [&lt;StepDependency&gt;](#32-stepdependency)).
      5. See *externalServices* constraint 4.
      6. Every Service in this list has a non-empty scope (see [Service scope](#91-service-scope)).
9. *externalServices* — The external Services (see
   [Services from Environment Templates](#122-services-from-environment-templates)) whose endpoints this Job Template
   reads directly, each with the ports it uses; the scheduler matches each at submission to exactly one Service of that
   name among the attached Environment Templates' `services`. Available only when using the `SERVICE` extension. See:
   [&lt;ServiceRequirement&gt;](#98-servicerequirement). Constraints:
      1. Minimum number of elements: If provided, then this list must contain at least one element.
      2. Maximum number of elements: The list must not contain more than 10 elements.
      3. No two requirements in this list may have the same value for the `name` property.
      4. No requirement in this list may have the same `name` as a Service in *services*: a Service is either declared
         or required.
      5. Permitted only in a Job Template.
10. *steps* — A list of the Steps in the Job. See: [&lt;StepTemplate&gt;](#3-steptemplate).

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
environment: <Environment> # @optional
services: [ <Service>, ... ] # @optional @extension SERVICE
```

1. *specificationVersion* — A literal that identifies the document as adhering to this schema.
2. *$schema* — Ignored. This property is allowed for compatibility with JSON-editing IDEs.
3. *extensions* — If provided, is a non-empty list of extensions to the schema that this document uses. The available
   extension names are the same as for the [Job Template](#11-job-template). An extension listed here applies to the
   content of this document only; a Job Template does not need to list the extensions used by the Environment
   Templates that a scheduler applies to it, and vice versa.
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
   See [&lt;Environment&gt;](#4-environment). When *services* is also provided, the Environment may list those Services
   in its `dependencies`, which makes their endpoints visible to it.
6. *services* — The Services that the Environment Template defines. Available only when using the `SERVICE`
   extension. See [&lt;Service&gt;](#9-service-extension-service) and
   [Services from Environment Templates](#122-services-from-environment-templates). Constraints:
      1. Minimum number of elements: If provided, then this list must contain at least one element.
      2. Maximum number of elements: The list must not contain more than 10 elements.
      3. No two Services in this list may have the same value for the `name` property.
      4. The `dependencies` of the Services in this list form one graph, which must be acyclic.
      5. Every entry of a Service's `dependencies` in this list uses the `service` key and names a Service in this
         list, since the document has no Steps.

Subject to the constraint that at least one of *environment* or *services* must be provided.

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

#### 1.2.2. Services from Environment Templates

Available when using the `SERVICE` extension.

An Environment Template that defines *services* defines Services that the scheduler applies to every Job Template
submitted through it, just as its *environment* defines an Environment applied to every submission. From the Job
Template's point of view these are **external Services**. Each Job that uses an external Service gets its own instance
of it. An external Service's scope is computed over the combined Job by the same rules as an inline Service's (see
[Service scope](#91-service-scope)): typically the Environment defined alongside it lists it, which puts every Step in
its scope, or a Step of the Job Template lists it through `externalServices`. An attached Service that nothing in the
combined Job lists has an empty scope and is never started; this is not an error.

A `Service.*` reference resolves within its own document: in an Environment Template to the document's *services*, in a
Job Template to its *services* or *externalServices* (see [Value References](#731-value-references)). No reference
crosses a document boundary except through a requirement, so every `Service.*` reference in every template can be
validated without knowledge of the scheduler's configuration. A Job Template that reads an external Service's endpoint
declares a requirement for it in `externalServices` (see [&lt;ServiceRequirement&gt;](#98-servicerequirement)).

When a submission combines a Job Template with one or more Environment Templates:

1. Every attached Service is part of the combined Job, and the attached Environments are placed in `jobEnvironments`
   as today (see [How Jobs Are Run](How-Jobs-Are-Run#services)). The limit of 10 applies to each document's list; the
   scheduler bounds the total through how many Environment Templates it attaches.
2. Each entry of `externalServices` must match exactly one Service with the same `name` among the attached Environment
   Templates' *services*, and that Service must declare every port the requirement lists, with the same `protocol`. If
   no attached Service has the name, if two or more do, if the matched Service lacks a listed port, or if a port's
   protocol differs, the submission must be rejected, naming the requirement and the cause. Matching uses the
   requirement alone; the scheduler reads nothing else from the Job Template.
3. Service names are per document. A Job Template's `Service.*` references resolve to its own `services` and
   `externalServices`, and an attached Service that happens to share a name with an inline Service is neither visible
   to the Job Template nor a conflict; it runs if the Environment defined alongside it lists it, and reaches the Job's
   Tasks through that Environment. Two attached Services with the same `name` are an error only when a requirement
   names it. A scheduler must keep same-named Services from different documents distinct (for example, by qualifying
   each with its document).
4. A wrapping Environment (one defining the `WRAP_ACTIONS` hooks) in a document that does not declare `SERVICE`, whether
   an attached Environment Template or the Job Template itself, has the default `runScope` of every kind of Session and
   cannot define the `onWrapService*` hooks. Service Sessions enter the Job's `jobEnvironments` only, so if such an
   Environment is in the combined Job's `jobEnvironments` and the combined Job has any Service, the submission must be
   rejected, identifying the document that defines the Environment as the cause. The remedy is for that document to
   declare `SERVICE` and either define the four hooks or declare a `runScope` that excludes `SERVICE`. A wrapping
   Environment in a Step's `stepEnvironments` is never entered by a Service Session and is not subject to this check.

Items 2 and 4 are the only checks that require the combined Job; everything else is checked when each document is
validated on its own.

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

Where `<intstring>` is a string whose value is the string representation of an integer value in base-10, and:

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
base-10, and:

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
   *stepEnvironments*, *hostRequirements*, *parameterSpace*, and *script* fields. See: [&lt;LetBindings&gt;](#36-letbindings).
4. *dependencies* — A list of the dependencies of this Step. These dependencies must be resolved before the Tasks of the
   Step may be scheduled. Each names a Step of the same Job Template or, with the `SERVICE` extension, a Service that
   must be READY. See: [&lt;StepDependency&gt;](#32-stepdependency)
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: There is no maximum defined, though implementations may choose to constrain the number of
    dependencies.
5. *stepEnvironments* — An ordered list of the environments that are required to run Tasks in this Step.
  These are entered in the order provided at the start of every Session for Tasks in the Step, and exited in the reverse
  order at the end of those Sessions.
  See: [&lt;Environment&gt;](#4-environment).
    * Constraints:
        1. No two Environments in this list may have the same value for the `name` property.
        2. The Environments defined in this list must not have the same `name` as a Job Environment defined in the same
           Job Template.
        3. With the `SERVICE` extension, see [&lt;Environment&gt;](#4-environment) item 3 constraint 4 and item 4
           constraint 4.
    * Note: The scope of a Step Environment's `name` is the Step that defines it. Different Steps may each define a
      Step Environment with the same `name`; a Session only ever contains the Step Environments of a single Step, so
      these names never collide.
6. *hostRequirements* — Describes the requirements on Worker host's capabilities that must be satisfied for the Task(s) of
   the Step to be scheduled to the host. See: [&lt;HostRequirements&gt;](#33-hostrequirements).
7. *parameterSpace* — Defines the parameterization of the Step's action; the available parameters, the values that they
   take on, and how those parameters' values are combined to produce the Tasks of the Step. Absent this property the Step
   is run a single time.
8. *script* — The action that is taken by this Step's Tasks when they are run on a Worker host.

With the `SERVICE` extension, a Step's *dependencies* may also name Services (see
[&lt;StepDependency&gt;](#32-stepdependency)). A Step need not repeat a Step dependency that a Service it lists already
carries.

### 3.1. `<StepName>`

A string subject to the following constraints:

1. Allowed characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 64 characters. 512 characters if using the
`FEATURE_BUNDLE_1` extension.

### 3.2. `<StepDependency>`

This entity is used by the template author to specify a Step in the same Job that a Step depends upon or, with the
`SERVICE` extension, a Service that a Step, a Service, or a Job Environment depends upon. It appears in the
*dependencies* of a [&lt;StepTemplate&gt;](#3-steptemplate), of a [&lt;Service&gt;](#9-service-extension-service), and
of a Job [&lt;Environment&gt;](#4-environment).

A `<StepDependency>` is one of the objects:

```yaml
# <StepDependency> is one of:
dependsOn: "<StepName>"
# or, with the SERVICE extension:
service: "<ServiceName>" # @extension SERVICE
```

Where:

1. *dependsOn* — Provides the name of another step in the same job upon which this step depends. The Task(s) of this
   Step may be scheduled only when the depended-upon Step has fully completed successfully.
2. *service* — The name of a Service of the same document's `services` or, in a Job Template, of its `externalServices`.
   The dependency is satisfied when the Service is READY (see [How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle)).
   Listing a Service puts the listing entity in the Service's scope (see [Service scope](#91-service-scope)) and makes
   the Service's values visible to it (see [Value References](#731-value-references)).

Constraints (with the `SERVICE` extension):

1. *dependsOn* must name a Step of the same Job Template, and *service* a Service of the same document's `services` or,
   in a Job Template, of its `externalServices`; neither may name the entity listing it.
2. No two entries of one *dependencies* list may name the same Step or the same Service.
3. The *dependencies* lists of a Job Template's Steps, Services, and Job Environments form one graph whose nodes are
   the Steps and Services and whose edges run from each entity to each entry in its list (Step to Step, Step to
   Service, Service to Step, and Service to Service), plus an edge from every Step to each Service a Job Environment
   lists (see [Service scope](#91-service-scope) rule 3). That graph must be acyclic; a template with a cycle is
   rejected at template validation, naming the cycle.
4. Exactly one of the two keys must be present; an entry that gives both, or neither, is a validation error.

### 3.3. `<HostRequirements>`

This entity is used by the template author to describe the requirements on Worker host and/or render manager's available
capabilities that must be satisfied for the Task(s) of the Step, or the Service (with the `SERVICE` extension), to be
scheduled to the host.

Each requirement corresponds to an attribute of a host or render manager that must be satisfied to allow the Step or
Service to be scheduled to the host. Some examples of concrete attributes include processor architecture (x86_64, arm64,
etc), the number of CPU cores, the amount of system memory, or available floating licenses for an application. We also
allow for user-defined whose meaning is defined by the customer; a "SoftwareConfig" requirement whose values could be
"Option1" or "Option2", for example.

There are two types of requirements: attribute and amount.

A `<HostRequirements>` is the object:

```yaml
amounts: [ <AmountRequirement>, ... ] # @optional
attributes: [ <AttributeRequirement>, ... ] # @optional
```

Where:

1. *amounts* — Defines a set of quantifiable requirements on the host that must be met and reserved for a Session running
   Tasks from this Step, or the Service Session of this Service, to be scheduled to the host.
   See: [&lt;AmountRequirement&gt;](#331-amountrequirement).
2. *attributes* — Defines a set of attributes that a host must have for a Session running Tasks from this Step, or the
   Service Session of this Service, to be scheduled to the host.
   See: [&lt;AttributeRequirement&gt;](#332-attributerequirement).

With the constraints:

1. If this object is provided, then at least one of the *amounts* or *attributes* properties must be defined.
2. The sum of the lengths of the *amounts* and *attributes* arrays must not exceed 50 elements.
3. No two elements in the *amounts* array may have the same value for the *name* property, after the *name* format
   strings have been resolved.
4. No two elements in the *attributes* array may have the same value for the *name* property, after the *name* format
   strings have been resolved.

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
representation of a non-zero and positive floating point or integer value in
base-10, `<positivefloatstring>` is a string whose value is the string
representation of a positive floating point or integer value in base-10, and:

1. *name* — Is a dotted name that identifies the specific host capability that is being required.
2. *min* — If provided, then the host must have at least the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host. If not provided, then the default is 0 unless
   the specific host capability defines a minimum. Can only be a
   `<nonnegativefloatstring>` when using the extension `FEATURE_BUNDLE_1`.
3. *max* — If provided, then the host must have at least the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host. Can
   only be a `<positivefloatstring>` when using the extension `FEATURE_BUNDLE_1`.

Subject to the constraint that at least one of *min* or *max* must be provided.

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
allOf: [ <AttributeCapabilityValue>, ... ] # @optional @fmtstring
```

Where:

1. *name* — Is a dotted name that identifies the specific host capability that is being required.
2. *anyOf* — For the Step to be scheduled to it, the host's value for the named capability must have **at least one** of
   the given values. This comparison is case-insensitive.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.
3. *allOf* — For the Step to be scheduled to it, the host's value for the named capability must have **all** the given
   values. This comparison is case-insensitive.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.

Subject to the constraint that at least one of *anyOf* or *allOf* must be provided.

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
|attr.worker.preemptible|true, false|Whether the host's capacity may be reclaimed by the infrastructure provider while work is running on it (for example, EC2 Spot Instances). A host that does not advertise this attribute has an unknown value; a requirement of `anyOf: ["false"]` does not match such a host. Introduced in [RFC 0009](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0009-service.md).|

##### 3.3.2.2. `<AttributeCapabilityValue>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Minimum length: 1 character.
2. After the format string has been resolved:
    1. Max length: 100 characters
    2. Unicode alphanumeric characters in the latin character set, plus the underscore and hyphen characters.
    3. Must start with either a letter character or the underscore character.

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
string representation of an integer value in base-10, and:

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

Subject to the constraint no two ranges in the expression are allowed to overlap.

The number of values that an `<IntRangeExpr>` expands to is not constrained by this specification. In particular, the maximum of 1024 elements that §3.4.1.1 places on an `<IntRangeList>` does not apply to this form; expressing a range of more than 1024 values, such as a long frame range, is the motivating use-case for it. An implementation that needs to bound the number of Tasks a Step may define is expected to do so with its own limit on the Task count, not by constraining this expression.

The elements of the range expression are combined to form a list of values in increasing order.

For example:

|`<IntRangeExpr>`|**List of values**|
|---|---|
|"1 - 5"|`[1, 2, 3, 4, 5]`|
|"1 - -1"|`[1]`|
|"-1 - 1"|`[-1,0,1]`|
|"1-5:2"|`[1,3,5]`|
|"10-15:2,1-5"|`[1,2,3,4,5,10,12,14]`|
|"1-10:4"|`[1,5,9]`|
|"1-10:4,10-15"|Error: ranges overlap|

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
string representation of a floating point value in base-10, and:

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
        of integers with two integers separated by "-" like a single "5-5" or interval "1-10".
        If NONCONTIGUOUS, a chunk can be an arbitrary set of integers following the
        `<IntRangeExpr>` syntax like "1,3,7-10:2". Frame ranges are inclusive, so "10-20" contains 11 frames.
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
| `<StepTemplate>.let` | `Param.*`, `RawParam.*`, `Job.Name`, `Step.Name`, earlier bindings in same `let` | *stepEnvironments*, *hostRequirements*, *parameterSpace*, *script* (including nested `<StepScript>.let` or `<SimpleAction>.let`) |
| `<StepScript>.let` | `Param.*`, `RawParam.*`, `Task.Param.*`, `Task.RawParam.*`, `Session.*`, `Task.File.*`, `Job.Name`, `Step.Name`, step-level bindings, earlier bindings in same `let`, in-scope `Service.<name>.<port>.*` (`SERVICE` extension) | *actions*, *embeddedFiles* |
| `<SimpleAction>.let` | `Param.*`, `RawParam.*`, `Task.Param.*`, `Task.RawParam.*`, `Session.*`, `Job.Name`, `Step.Name`, step-level bindings, earlier bindings in same `let`, in-scope `Service.<name>.<port>.*` (`SERVICE` extension) | *script*, *args* |
| `<EnvironmentScript>.let` | `Param.*`, `RawParam.*`, `Session.*`, `Env.File.*`, `Job.Name`, earlier bindings in same `let`, in-scope `Service.<name>.<port>.*` when the Environment's `runScope` excludes `SERVICE` (`SERVICE` extension) | *actions*, *embeddedFiles* |
| `<Service>.let` (`SERVICE` extension) | `Param.*`, `RawParam.*`, `Job.Name`, earlier bindings in same `let` | *hostRequirements*, *variables*, *script* (including nested `<ServiceScript>.let`) |
| `<ServiceScript>.let` (`SERVICE` extension) | `Param.*`, `RawParam.*`, `Session.*`, `Service.File.*`, in-scope `Service.<name>.<port>.*`, `Job.Name`, service-level bindings, earlier bindings in same `let` | *actions*, *embeddedFiles* |

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
dependencies: [ <StepDependency>, ... ] # @optional @extension SERVICE
runScope: [ <RunScopeName>, ... ] # @optional @extension SERVICE
script: <EnvironmentScript> # @optional
variables: <EnvironmentVariables> # @optional
```

Where:

1. *name* — An identifier given to the environment that is unique within the Environment's defined scope: the Job
   Template for a Job Environment, and the Step Template for a Step Environment.
2. *description* — A description to apply to the environment. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *dependencies* — The Services this Environment depends on, each a [&lt;StepDependency&gt;](#32-stepdependency) with
   the `service` key. Available only when using the `SERVICE` extension. Listing a Service puts every Step in its
   scope ([Service scope](#91-service-scope) rule 3). An Environment that lists a Service defaults to
   `runScope: [TASK]`. Constraints:
      1. Minimum number of elements: If provided, then this list must contain at least one element.
      2. Every entry must use the `service` key and name a Service of the same document's `services` or, in a Job
         Template, of its `externalServices`.
      3. No two entries may name the same Service.
      4. Not permitted on a `stepEnvironments` entry, which follows its Step's *dependencies*.
      5. See *runScope* constraint 2.
4. *runScope* — The kinds of Session this Environment is entered in. Available only when using the `SERVICE` extension.
   Every Session has exactly one kind, and an Environment is entered in a Session if and only if that Session's kind is
   in the Environment's *runScope*. `<RunScopeName>` is one of `TASK` (Sessions that run Tasks, the only kind that
   exists without `SERVICE`) or `SERVICE` (Service Sessions, in which a Service's actions run; see
   [&lt;Service&gt;](#9-service-extension-service)). If not provided, an Environment that lists any Service in its
   *dependencies* is entered in Task Sessions only, as if `runScope: [TASK]` were given, and any other Environment is
   entered in every kind of Session. An explicit list is exhaustive. Constraints:
      1. Minimum number of elements: 1. No name may appear more than once.
      2. An Environment whose *runScope* includes `SERVICE` must not list or reference any Service, since a Service
         Session may begin before any Service other than its own has an endpoint.
      3. Implementations must reject a `<RunScopeName>` they do not recognize.
      4. Not permitted on a `stepEnvironments` entry, which is entered only by its Step's Task Sessions.
5. *script* — The action that is taken by this Environment when it is run on a Worker host.
6. *variables* — A set of environment variable name/value pairs, with the values being
   [Format Strings](#73-format-strings) that are resolved when entering the environment. The specified variables must be
   set prior to running either `onEnter` or `onExit` for the environment, and for all actions that are run with the
   environment active.
7. At least one of "script" or "variables" must be provided.

The format string scopes available to format strings within an Environment are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters.
2. `Session.*` — Values such as the Session's working directory.
3. `Env.*` — Scope of the environment entity itself. Values such as the embedded files defined within the Environment
   entity.
4. Names bound by `let` in the enclosing `<EnvironmentScript>`. Available with the `EXPR` extension.
5. `Service.<name>.<port>.port` and `Service.<name>.<port>.connectAddress` — Available for a Service that the
   Environment lists in its *dependencies* (a Job Environment or an Environment Template's Environment) or, for a Step
   Environment, that its Step lists in *dependencies*; see [Section 9](#9-service-extension-service) and
   [Service scope](#91-service-scope). Available with the `SERVICE` extension.
6. `WrappedAction.*` — Available within the wrap hooks only (`onWrapEnvEnter`, `onWrapTaskRun`, `onWrapEnvExit`, and,
   with the `SERVICE` extension, `onWrapServiceEnter`, `onWrapServiceRun`, `onWrapServiceHealthCheck`, and
   `onWrapServiceExit`). Carries the wrapped `<Action>`'s fields. Available with the `WRAP_ACTIONS` extension.
   See [Wrap hook template variables](#431-wrap-hook-template-variables) for the available fields. "Within a hook"
   means throughout the hook's `<Action>`: its *command* and *args*, and its *timeout* and *cancelation* fields, which
   resolve at run time with these variables in scope. The same holds for `WrappedEnv.*`, `WrappedStep.*`, and
   `WrappedService.*` below.
7. `WrappedEnv.Name` — Available within `onWrapEnvEnter` and `onWrapEnvExit` only. The name of the inner
   environment whose action is being wrapped. Available with the `WRAP_ACTIONS` extension.
8. `WrappedStep.Name` — Available within `onWrapTaskRun` only. The name of the step whose task is being
   wrapped. Available with the `WRAP_ACTIONS` extension.
9. `WrappedService.*` — Available within the four `onWrapService*` hooks only. The name of the Service whose action is
   being wrapped and its port names, port numbers, bind addresses, and protocols. Available with the `WRAP_ACTIONS` and
   `SERVICE` extensions. See [Wrap hook template variables](#431-wrap-hook-template-variables).

Templates must not reference `WrappedAction.*` outside the wrap hooks, `WrappedEnv.*` outside `onWrapEnvEnter` and
`onWrapEnvExit`, `WrappedStep.*` outside `onWrapTaskRun`, or `WrappedService.*` outside the `onWrapService*` hooks.
Schedulers must reject templates that violate this scope rule.

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
onWrapServiceEnter: <Action>       # @optional @extension WRAP_ACTIONS SERVICE
onWrapServiceRun: <Action>         # @optional @extension WRAP_ACTIONS SERVICE
onWrapServiceHealthCheck: <Action> # @optional @extension WRAP_ACTIONS SERVICE
onWrapServiceExit: <Action>        # @optional @extension WRAP_ACTIONS SERVICE
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
5. *onWrapServiceEnter*, *onWrapServiceRun*, *onWrapServiceHealthCheck*, *onWrapServiceExit* — When this
   environment is the wrapping environment of a Service Session, these run instead of the Service's `onEnter`,
   `onRun`, `onHealthCheck`, and `onExit` respectively, exactly as `onWrapTaskRun` runs instead of a task's `onRun`.
   Available only when using both the `WRAP_ACTIONS` and `SERVICE` extensions. See
   [Wrap hook template variables](#431-wrap-hook-template-variables) and
   [&lt;ServiceActions&gt;](#97-serviceactions).
6. *onExit* — The action run when the environment is being exited on a host.

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
> 6. *Service hooks* (`SERVICE` extension). When `SERVICE` is declared, the hooks a wrapping environment
>    (one that defines any wrap hook) must define follow from its `runScope`, and rule 1 above is replaced
>    by this rule. Inner environments are entered in every kind of session, so every wrapping environment
>    must define `onWrapEnvEnter` and `onWrapEnvExit`. It must define `onWrapTaskRun` if and only if its
>    `runScope` includes `TASK`, and must define all four `onWrapService*` hooks if and only if its
>    `runScope` includes `SERVICE`. A wrapping environment in a Step's `stepEnvironments`, which has no `runScope`,
>    therefore defines exactly the three hooks of rule 1. Schedulers must reject templates that define a hook the
>    `runScope` does not call for, or omit one it does. A wrapped Service `onEnter`'s `openjd_env` messages
>    and a wrapped `onRun`'s `openjd_service_ready` line are recognized on the wrap script's stdout, as for every
>    `openjd_*` message under `WRAP_ACTIONS`. A failed `onWrapService*` hook has the effect the wrapped action's
>    failure would have, an `onWrapServiceHealthCheck` invocation's exit status being one probe result (see
>    [&lt;ServiceHealthCheck&gt;](#94-servicehealthcheck)). For a wrapping environment in a document that does not
>    declare `SERVICE`, see [Services from Environment Templates](#122-services-from-environment-templates) item 4.

#### 4.3.1. Wrap hook template variables

Each wrap hook receives the wrapped `<Action>`'s fields as read-only template variables supplied by the
runtime. The variables have identical names and semantics across all hooks, so helper scripts can
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

**Additionally available in the four `onWrapService*` hooks** (`SERVICE` extension):

| Variable                       | Type           | Description |
|--------------------------------|----------------|-------------|
| `WrappedService.Name`          | `string`       | The `name` of the Service whose action is being wrapped. |
| `WrappedService.PortNames`     | `list[string]` | The `name` of each of the Service's ports, in declaration order. |
| `WrappedService.Ports`         | `list[int]`    | The allocated port number of each port, in the same order. |
| `WrappedService.BindAddresses` | `list[string]` | The `bindAddress` of each port, in the same order. |
| `WrappedService.Protocols`     | `list[string]` | The `protocol` of each port (`TCP` or `UDP`), in the same order. |

The four lists are parallel: index *i* of each describes the Service's *i*-th declared port. `bindAddress` and
`connectAddress` are determined for the service host's network namespace. A wrap script that runs the service process in
that namespace (a launcher, `ssh`, or a container with host networking) needs no port handling. One that gives the
process its own network namespace must forward each port in `WrappedService.Ports` with the protocol in
`WrappedService.Protocols`, so that a connection to `connectAddress`:`port` from any host in the scope reaches the
process, and must ensure the process can bind `bindAddress` inside that namespace. A wildcard `bindAddress` (`0.0.0.0`,
`::`) works in either case; a loopback `bindAddress` reaches a forwarded port only with host networking. For example, a
Docker wrapper without host networking passes
`{{ flatten([['-p', string(WrappedService.Ports[i]) + ':' + string(WrappedService.Ports[i]) + '/' + lower(WrappedService.Protocols[i])] for i in range(len(WrappedService.Ports))]) }}`.
`WrappedService.Ports` is `list[int]`; `repr_sh` accepts `int` and `list[int]` (see the
[Expression Language](2026-02-Expression-Language#226-script-embedding-and-serialization)), so a wrapper may also pass
the whole list as `repr_sh(WrappedService.Ports)`.

Every `Wrapped*` group is in scope throughout the hook's `<Action>` — its *command* and *args*, and its *timeout* and
*cancelation* fields, which resolve at run time — so an `onWrapService*` hook forwards the wrapped action's timeout
with `timeout: "{{WrappedAction.Timeout}}"` exactly as RFC 0008's hooks do.

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
positive integer value in base-10, and:

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
   | `<ServiceActions>` | `onEnter` <sup>3</sup> | *no timeout* |
   | `<ServiceActions>` | `onRun` <sup>3</sup> | *no timeout* |
   | `<ServiceActions>` | `onHealthCheck` <sup>3</sup> | 30 seconds |
   | `<ServiceActions>` | `onExit` <sup>3</sup> | 300 seconds (five minutes) <sup>1</sup> |

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

   <sup>3</sup> Available with the `SERVICE` extension. A `timeout` on a Service's `onRun` action is
   measured from launch; its expiry is an instance failure of the Service (see
   [&lt;ServiceActions&gt;](#97-serviceactions)).

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
positive integer value in base-10, and:

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

1. `Task.File.<name>` - If the embedded file is part of a `<StepScript>` object;
2. `Env.File.<name>`- If the embedded file is part of an `<Environment>` object; or
3. `Service.File.<name>` - If the embedded file is part of a `<Service>` object (`SERVICE` extension).

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
|`Param.<ParamName>`|Values of the Job parameters are available within the `Param` object. This is the same as `RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it. |All types except PATH are available in every Format String in the Job Template. For PATH type parameters, this is only available within format strings that are within an Environment, StepScript, or (with the `SERVICE` extension) Service *variables* or ServiceScript context.|
|`RawParam.<ParamName>`|Values of the Job parameters are available within the `RawParam` object. This is always the exact input value of the job parameter.|Available in every Format String in the Job Template.|
|`Task.Param.<ParamName>`|Values of task parameters are available within the `Task.Param` object. This is the same as `Task.RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it.|Available within the Step Script Actions and Embedded Files.|
|`Task.RawParam.<ParamName>`|Values of task parameters are available within the `Task.Param` object.|Available within the Step Script Actions and Embedded Files.|
|`Task.File.<name>`|The filesystem location to which the Task Embedded File with key `<name>` has been written.| Available within the Step Script Actions and Embedded Files.|
|`Env.File.<name>`|The filesystem location to which the Environment Attachment with key `<name>` has been written.|Available within the Environment Script Actions and Embedded Files.|
|`Service.File.<name>`|The filesystem location to which the Service Embedded File with key `<name>` has been written. Requires the `SERVICE` extension.|Available within the Service Script Actions and Embedded Files of the declaring Service.|
|`Service.<name>.<port>.port`|The port number allocated (or requested) for port `<port>` of Service `<name>`, in the space of that port's `protocol`. This is an `int` type. Requires the `SERVICE` extension.|Available within the declaring Service, and within every Service, Step (its Script and its Step Environments), and Job Environment whose `dependencies` list `service: <name>`; a Job Environment that lists an inline Service puts every Step in its scope. A Service a Job Template requires follows the same rule, minus the declaring Service. See [&lt;Service&gt;](#9-service-extension-service) for the scoping rules.|
|`Service.<name>.<port>.bindAddress`|The interface address that the service process must bind to so that entities in the Service's scope can reach it: a hostname, an IPv4 literal, or an unbracketed IPv6 literal. This is a `string` type. Requires the `SERVICE` extension.|Available within the declaring Service only; never for a required external Service.|
|`Service.<name>.<port>.connectAddress`|The hostname or IP address that entities in the Service's scope use to reach port `<port>` of Service `<name>`: a hostname, an IPv4 literal, or an unbracketed IPv6 literal. Join it with a port using `join_host_port` (see [Expression Language](2026-02-Expression-Language#224-string-functions)), which adds the brackets an IPv6 literal needs in a URL. This is a `string` type. Requires the `SERVICE` extension.|As `Service.<name>.<port>.port`.|
|`Session.WorkingDirectory`|The agent is expected to create a local temporary scratch directory for the duration of a Session. This builtin provides the location of that temporary directory. This is the working directory that the Worker Agent uses when running the task.|This is available within all Environment Script Actions & Embedded Files, all Step Script Actions and Embedded Files, and, with the `SERVICE` extension, all Service Script Actions and Embedded Files.|
|`Job.Name`|The resolved name of the Job. This is a `string` type. Requires the `EXPR` extension.|Available in every Format String in the Job Template, except the `name` field of the Job Template itself.|
|`Step.Name`|The name of the current Step. This is a `string` type. Requires the `EXPR` extension.|Available within the Step Template scope: `stepEnvironments`, `hostRequirements`, `parameterSpace`, and `script`.|
|`Session.HasPathMappingRules`|This value can be used to determine whether path mapping rules are available to the Session. Without the `EXPR` extension, it is string valued, with values "true" or "false". With the `EXPR` extension enabled, it is a `bool` type. "true"/`True` means that the path mapping JSON contains path mapping rules. "false"/`False` means that the contents of the path mapping JSON are the empty object.|This is available within all Environment Script Actions & Embedded Files, all Step Script Actions and Embedded Files, and, with the `SERVICE` extension, all Service Script Actions and Embedded Files.|
|`Session.PathMappingRulesFile`|This is a string whose value is the location of a JSON file on the worker node's local disk that contains the path mapping rule substitutions for the Session.|This is available within all Environment Script Actions & Embedded Files, all Step Script Actions and Embedded Files, and, with the `SERVICE` extension, all Service Script Actions and Embedded Files.|
|`<name>` (let binding)|Names bound by `let` in `<StepTemplate>`, `<StepScript>`, `<SimpleAction>`, or `<EnvironmentScript>`. Names must start with a lowercase letter or underscore (see `<UserIdentifier>`). The type is determined by the expression. Available with the `EXPR` extension.|See [Let Binding Scope Summary](#362-let-binding-scope-summary) for detailed scoping rules.|

### 7.4. Template Processing Stages

A Job Template is processed in stages as more information becomes available. At each stage,
different sets of values are known, which determines which format strings can be fully resolved.

| Stage | When | Known Values | Unknown Values | What Happens |
|-------|------|-------------|----------------|--------------|
| **Template validation** | `openjd check` or equivalent | Literal values, parameter type declarations | `Param.*`, `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*`, `Service.*` | Syntax validation, structural checks. With the `EXPR` extension: type checking of expressions using declared parameter types. `Job.Name` and `Step.Name` are available as `unresolved[string]`. |
| **Job creation** | Job submission with parameter values | `Param.*`, `RawParam.*` | `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*`, `Service.*` | Parameter values are bound. Format strings not annotated `@fmtstring[host]` are resolved (e.g., `name`, `parameterSpace` ranges). PATH and `LIST[PATH]` parameter defaults must be relative and are joined with the job template directory (see [§2.2](#22-jobpathparameterdefinition)); relative PATH and `LIST[PATH]` parameter values are joined with the current working directory. With the `EXPR` extension: `let` bindings in `<StepTemplate>` and `<Service>` are evaluated; expressions in TEMPLATE scope are fully evaluated; `Job.Name` and `Step.Name` are concrete. |
| **Task execution** | On the worker host | All values: `Param.*`, `Task.Param.*`, `Session.*`, `Task.File.*`, `Env.File.*`, `Service.*`, path mapping rules | *(none)* | Format strings annotated `@fmtstring[host]` are resolved. Path mapping rules are applied to PATH-type parameters. Embedded files are written. With the `EXPR` extension: `let` bindings in `<StepScript>`, `<EnvironmentScript>`, and `<ServiceScript>` are evaluated; all remaining expressions are fully evaluated. |

With the `SERVICE` extension, a Service's own actions are resolved at an analogous **Service execution** stage on the
service host: all `Param.*`, `Session.*`, `Service.File.*`, and in-scope `Service.<name>.<port>.*` values are known.
`Service.<name>.<port>.*` values are annotated `@fmtstring[host]`: they are resolved when the scheduler places the
Service, and may change if the Service is relocated. See [&lt;Service&gt;](#9-service-extension-service).

The `@fmtstring` and `@fmtstring[host]` annotations in this specification indicate which stage
a format string is resolved in. A format string annotated `@fmtstring` (without `[host]`) is
resolved at job creation time. A format string annotated `@fmtstring[host]` is resolved at task
execution time on the worker host.

With the `EXPR` extension enabled, expressions that reference values not yet known at a given
stage are type-checked using the declared types of those values, catching type errors as early
as possible. See the [Expression Language](2026-02-Expression-Language) specification for details.

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
positive integer value in base-10, and:

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

## 9. `<Service>` `@extension SERVICE`

This object is only available in the extension `SERVICE`, introduced in
[RFC 0009](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0009-service.md). A template
that lists `SERVICE` in `extensions:` must also list `EXPR`; schedulers must reject templates that list `SERVICE`
without `EXPR`.

A Service is a long-lived process that a scheduler starts before scheduling the Tasks in its scope, keeps running for
the lifetime of its scope (see [Service scope](#91-service-scope)), and stops once the scope no longer needs it. A
Service publishes one or more named ports that the runtime allocates on the Service's host, and every entity that
depends on the Service can discover the resulting endpoint via the `Service.*` format-string scope. Unlike an
Environment, a Service may be placed on a different Worker Host than the Tasks that use it, in a Session of its own (see
[How Jobs Are Run](How-Jobs-Are-Run#services) for the lifecycle, readiness and health, and failure semantics).

A `<Service>` is the object:

```yaml
name: <ServiceName>
description: <Description> # @optional
let: <LetBindings> # @optional @extension EXPR
dependencies: [ <StepDependency>, ... ] # @optional
hostRequirements: <HostRequirements> # @optional
ports: [ <ServicePort>, ... ]
healthCheck: <ServiceHealthCheck> # @optional
restartPolicy: <ServiceRestartPolicy> # @optional
variables: <EnvironmentVariables> # @optional
script: <ServiceScript>
```

Where:

1. *name* — The Service's identifier, the first component of `Service.*` references to it. See:
   [&lt;ServiceName&gt;](#92-servicename).
2. *description* — A description to apply to the Service. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *let* — An ordered list of expression bindings evaluated once, at job creation, like a `<StepTemplate>`'s *let*.
   Bindings may reference `Param.*`, `RawParam.*`, and `Job.Name`, but not `Session.*` or `Service.*`, which are not
   known until the Service is placed. Bound names are available in *hostRequirements*, *variables*, and *script*, as a
   Step's bindings are in its *stepEnvironments*. See: [&lt;LetBindings&gt;](#36-letbindings).
4. *dependencies* — The Steps and Services this Service depends on, each a [&lt;StepDependency&gt;](#32-stepdependency).
   The Service is started only once every entry is satisfied and is stopped before any Service it lists (see
   [How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle)). A Step dependency orders the Service after the Step and
   nothing more; the Step's output reaches the service host as it reaches any later Step. Constraints:
    1. Minimum number of elements: If provided, then this list must contain at least one element.
    2. Each entry satisfies [&lt;StepDependency&gt;](#32-stepdependency) constraints 1 and 2.
    3. In the graph of [&lt;StepDependency&gt;](#32-stepdependency) constraint 3, a Service that lists a Step in its own
       scope, directly or through other Services, is a cycle; a Service that a Job Environment lists, directly or
       through other Services, has every Step in its scope and so can list no Step.
5. *hostRequirements* — Describes the requirements on the Worker Host's capabilities that must be satisfied for the
   Service to be placed on the host. Amount capabilities are allocated to the Service for its lifetime. This is
   independent of the *hostRequirements* of any Step whose Tasks use the Service.
   See: [&lt;HostRequirements&gt;](#33-hostrequirements).
6. *ports* — The named ports that the Service exposes. See: [&lt;ServicePort&gt;](#93-serviceport).
    1. Minimum number of elements: 1.
    2. Maximum number of elements: 10.
    3. No two elements may have the same value for the *name* property.
    4. No two elements with the same value for the *protocol* property may have the same value for the *port*
       property; a service that speaks TCP and UDP on one number gives it explicitly on both ports, and ports whose
       *port* is not provided are allocated independently in each protocol's space.
7. *healthCheck* — The probe by which the scheduler determines that an instance of the Service is ready to accept
   traffic and, once it is, that it remains healthy. If not provided, defaults to `{ type: TCP_CONNECT }` applied to
   every declared TCP port. A Service none of whose ports is TCP must provide a *healthCheck* of type `STDOUT` or
   `COMMAND`; a `TCP_CONNECT` check, given or defaulted, would have no port to probe.
   See: [&lt;ServiceHealthCheck&gt;](#94-servicehealthcheck).
8. *restartPolicy* — What the scheduler does when the Service's `onRun` action exits before the scope ends. If not
   provided, defaults to `{ maxAttempts: 0 }`: the Service is never relaunched, and its exit fails the scope. See:
   [&lt;ServiceRestartPolicy&gt;](#95-servicerestartpolicy).
9. *variables* — A set of environment variable name/value pairs, with the values being [Format
   Strings](#73-format-strings) that are resolved when the Service is started, that are set in the process environment
   of every action of the Service's *script*. See: [&lt;EnvironmentVariables&gt;](#44-environmentvariables). Neither these variables nor those the Service's *onEnter*
   sets with `openjd_env` (see [&lt;ServiceActions&gt;](#97-serviceactions)) are propagated to the entities in the
   Service's scope.
10. *script* — The actions that the Service runs on its host. See: [&lt;ServiceScript&gt;](#96-servicescript).

The format string scopes available to format strings within a `<Service>` are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters. `PATH`-typed `Param.*` values are available in the Service's
   *variables* and *script*, with the service host's path mapping applied, and not in `<Service>.let` or
   *hostRequirements*, which are resolved at job creation.
2. `Session.*` — Values such as the Service's working directory. `Session.WorkingDirectory` refers to the Service's own
   Session's working directory on the service host, not to the working directory of any Session running Tasks. A Service
   Session receives path mapping rules like any Session; `Session.HasPathMappingRules` and
   `Session.PathMappingRulesFile` describe the rules for the service host.
3. `Service.File.*` — The filesystem location of embedded files defined within this Service's *script*.
4. `Service.<name>.<port>.*` — The endpoint of this Service's own ports and, under the visibility rule below, of the
   Services this Service lists in its *dependencies*.
5. `Job.Name`.
6. Names bound by `let` in the `<Service>` and in the `<ServiceScript>`.

A Step, Service, or Job Environment may reference `Service.<name>.<port>.port` and
`Service.<name>.<port>.connectAddress` if and only if it lists `service: <name>` in its `dependencies`; a Step's Step
Environments share the Step's list, and the Service `<name>` itself sees all three values. For a required Service,
`<port>` must be one the requirement lists. In detail, the `Service.<name>.<port>.*` values of a Service `<name>` declared in the document's `services` or, in a Job Template,
declared by an entry of `externalServices`, are in scope in:

1. The Service `<name>` itself (all three values), when it is declared in `services`.
2. Any Service in the same `services` list that lists `service: <name>` in its `dependencies` (`port` and
   `connectAddress` only): its actions, *variables*, embedded files, and `<ServiceScript>.let`.
3. In a Job Template, any Step that lists `service: <name>` in its `dependencies`: its `script` (actions, embedded
   files, `let`) and each of its `stepEnvironments` entries (*variables*, actions, embedded files, `let`).
4. In a Job Template, any `jobEnvironments` entry that lists `service: <name>` in its `dependencies` (*variables*,
   actions, embedded files, `let`), whether `<name>` is inline or required.
5. In an Environment Template: the document's `environment` when it lists `service: <name>` in its `dependencies`.

A reference from a Step, Service, or Job Environment that does not list the dependency is a validation error, whether
the Service is inline or required, and the message should name the fix: for example, *Step 'Render' references
`Service.Cache.main.port` but does not list `service: Cache` in `dependencies`*. `bindAddress` is in scope only within
the declaring Service, never for a required Service (see [&lt;ServiceRequirement&gt;](#98-servicerequirement)).

`Service.*` is never in scope in a field resolved at job creation, before any Service is placed: a `hostRequirements`
object, neither a Step's nor a Service's; a `<Service>`'s or a `<StepTemplate>`'s `let`; an `<Action>`'s `timeout`; a
cancelation method's `notifyPeriodInSeconds`; and the [numeric `@fmtstring` fields](#951-numeric-fmtstring-fields) of
`<ServicePort>`, `<ServiceHealthCheck>`, and `<ServiceRestartPolicy>`. Nor is it in scope in an Environment whose `runScope` includes
`SERVICE` (see [&lt;Environment&gt;](#4-environment) item 4 constraint 2).

A template that references a `Service.*` value outside these scopes, or that references a Service or port name that it
neither declares nor requires, is invalid and must be rejected before the Job is created.

### 9.1. Service scope

The scope of a Service is the set of Steps whose Tasks depend on it. For a Service declared in a Job Template it is
determined at template validation from the template's `dependencies` lists; the order of the `services` list carries no
meaning:

1. A Step that lists Service `X` in its `dependencies` is in the scope of `X`.
2. When Service `Y` lists Service `X`, every Step in `Y`'s scope is in `X`'s scope. This applies transitively: a Step is
   in `X`'s scope when it depends on `X` through any chain of Services.
3. When any `jobEnvironments` entry lists Service `X` in its `dependencies`, every Step is in `X`'s scope, because
   every Step's Session enters a Job Environment. A Step Environment has no `dependencies` of its own; it follows its
   Step's.
4. A Service in whose scope no Step falls is unused, and the template must be rejected at template validation, naming
   the Service. A Service listed only by Services that are themselves unused is unused.

These rules apply to every Service of the combined Job, inline or external, with one difference: rule 4 rejects an
inline Service with an empty scope at template validation, while an external Service with an empty scope is simply never
started (see [Services from Environment Templates](#122-services-from-environment-templates)). An `externalServices`
entry is subject to rule 4 like an inline Service: one that no Step, Service, or Job Environment of the Job Template
lists is rejected at template validation, naming the entry. A Service is started before any Task of a Step in its scope and stopped once no such Task remains to be run (see
[How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle)): one whose scope is one Step lives as long as that Step, and one
whose scope is every Step as long as the Job.

### 9.2. `<ServiceName>`

An [&lt;Identifier&gt;](#71-identifier) subject to the additional constraint that it must not be `File`, which is
reserved for `Service.File.*` embedded file references.

### 9.3. `<ServicePort>`

A `<ServicePort>` is the object:

```yaml
name: <Identifier>
port: <posinteger> | <posintstring> # @optional @fmtstring
protocol: enum("TCP", "UDP") # @optional
```

Where:

1. *name* — The name of the port. It is the second component of `Service.<service>.<port>.*` references. Must not be
   `File`.
2. *port* — If provided, the Service requires this specific port number on its host, in the space of the port's
   *protocol*; if the scheduler cannot provide it on the chosen host, that is a start failure (see
   [How Jobs Are Run](How-Jobs-Are-Run#service-failure-and-restart)), and relocation to another host may succeed. If
   not provided, the runtime allocates an available port of the port's *protocol*. Range: 1–65535. Authors should omit
   this and let the runtime allocate, so that multiple Services and Sessions can share a host.
3. *protocol* — The transport protocol the service process binds the port with, and which the scheduler uses for any
   publishing or forwarding it performs to make the port reachable (a container port mapping, a firewall rule, a NAT
   entry). One of `TCP` or `UDP`. Default: `TCP`.

Every port, TCP or UDP, is bound and published on the same service host.

`bindAddress` and `connectAddress` are each a hostname, an IPv4 literal, or an IPv6 literal, in bare form: an IPv6
literal is never bracketed. Schedulers should provide a hostname for `connectAddress` when one resolves from every host
in the Service's scope. Wherever an address and a port are joined into one string (a URL authority, a `--listen
host:port` flag) an IPv6 literal must be bracketed, so templates must compose such strings with `join_host_port` (see
[Expression Language](2026-02-Expression-Language#224-string-functions)) rather than `{{ addr }}:{{ port }}`.

### 9.4. `<ServiceHealthCheck>`

A `<ServiceHealthCheck>` is one of the following objects, discriminated by the *type* property:

```yaml
type: "TCP_CONNECT"
ports: [ <Identifier>, ... ] # @optional
readinessIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

```yaml
type: "COMMAND"
readinessIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

```yaml
type: "STDOUT"
readinessTimeoutSeconds: <posinteger> | <posintstring> # @optional @fmtstring
healthIntervalSeconds: <posinteger> | <posintstring> # @optional @fmtstring
failureThreshold: <posinteger> | <posintstring> # @optional @fmtstring
```

A health check is one probe mechanism applied in two phases. Before the instance is READY the probe decides readiness:
the first probe runs as soon as `onRun` is launched, a probe runs every *readinessIntervalSeconds* after it, and the
first success makes the instance READY. After the instance is READY the probe decides health: a probe runs every
*healthIntervalSeconds*, and *failureThreshold* consecutive failures make the instance UNHEALTHY, which is an instance
failure (see [How Jobs Are Run](How-Jobs-Are-Run#service-failure-and-restart)). A single successful probe resets the
count. While the count is below the threshold the instance stays READY and nothing changes. For `TCP_CONNECT` and
`COMMAND`, an interval is measured from the end of the previous probe. For a `STDOUT` heartbeat, the runtime arms a
deadline *healthIntervalSeconds* after the later of READY and the most recent `openjd_service_ready` line; a line
before the deadline is a successful probe and re-arms it, and a deadline that passes without a line is a failed probe
and arms the next.

Where:

1. *type* — The probe mechanism:
    * `TCP_CONNECT` — A probe succeeds when a TCP connection to each of the listed ports (by default, every TCP port
      the Service declares) succeeds. The connection is made from the service host to the allocated `port` on the
      loopback interface, or on `bindAddress` when it is not a wildcard address (`0.0.0.0` or `::`), and is closed
      immediately.
    * `COMMAND` — A probe is one invocation of the Service's *onHealthCheck* action (see
      [&lt;ServiceActions&gt;](#97-serviceactions)), run in the Service Session concurrently with `onRun` (see
      [Concurrency of onHealthCheck with onRun](#971-concurrency-of-onhealthcheck-with-onrun)), and succeeds when the
      invocation exits with status 0 while `onRun` is still running. The action's own `timeout` (default: 30 seconds)
      bounds one invocation; an invocation that exceeds it is canceled and is one failed probe, as is any exit status
      other than 0. Neither is by itself a failure of the Service.
    * `STDOUT` — A probe is a line of the form `openjd_service_ready: <message>` written to stdout by the `onRun`
      action, with the same syntax as the other `openjd_*` messages (see [How Jobs Are
      Run](How-Jobs-Are-Run#stdoutstderr-messages)). The first such line makes the instance READY; `<message>` has no
      functional purpose but may be surfaced in UI elements. Later lines are heartbeat probes when
      *healthIntervalSeconds* is given (see the opening paragraph) and have no effect otherwise, the health of the
      instance then being that its `onRun` process is still running.
2. *ports* (`TCP_CONNECT` only) — The names of the ports to probe. Each must be declared in the Service's *ports* and
   have `protocol: TCP`; naming a UDP port is a validation error, since a UDP port cannot accept a connection. Defaults
   to every TCP port the Service declares.
3. *readinessIntervalSeconds* (`TCP_CONNECT` and `COMMAND` only) — Seconds between probes before the instance is READY.
   Default: 1 for `TCP_CONNECT`, 5 for `COMMAND`. A `STDOUT` check that gives this field must be rejected at template
   validation.
4. *readinessTimeoutSeconds* — The maximum time, measured from the launch of the `onRun` action, that the scheduler
   waits for the instance to become READY. It runs continuously, including while a probe is in progress. If exceeded,
   the instance has failed. Default: 300.
5. *healthIntervalSeconds* — Seconds between probes after the instance is READY. Default: 30 for `TCP_CONNECT` and
   `COMMAND`. For `STDOUT` there is no default: when given, it is the heartbeat interval described under *type*; when
   omitted, no heartbeat is expected.
6. *failureThreshold* — The number of consecutive failed probes after READY (for a `STDOUT` heartbeat, consecutive
   intervals without a line) that make the instance UNHEALTHY. Default: 3. A `STDOUT` check that gives this field
   without *healthIntervalSeconds* must be rejected at template validation, since there is no probe for it to count.

The health check applies to every instance of the Service: after a restart, the new `onRun` must pass a probe before
Tasks in the scope are scheduled again, and is monitored in the same way once it has.

### 9.5. `<ServiceRestartPolicy>`

A `<ServiceRestartPolicy>` is the object:

```yaml
maxAttempts: <integer> | <intstring> # @optional @fmtstring
completedTasks: enum("KEEP", "RERUN") # @optional
```

Where:

1. *maxAttempts* — The maximum number of times the scheduler will relaunch the Service after an instance failure or a
   start failure (see [How Jobs Are Run](How-Jobs-Are-Run#service-failure-and-restart)). The initial launch is not
   counted, so the default of 0 means the Service is launched exactly once and never relaunched. Must be 0 or greater.
2. *completedTasks* — What happens, when a new instance is launched, to Tasks in the Service's scope that completed
   successfully against a previous instance, and to Tasks that were running at the time. Tasks not yet started are
   scheduled once the new instance is READY.
    * `KEEP` — Completed Tasks remain complete, and running Tasks continue, failing and retrying on their own if the
      outage affects them. Use this when the Service holds no state that Tasks depend on, or holds state that Tasks can
      regenerate.
    * `RERUN` — Completed Tasks are returned to the scheduling queue and run again, and running Tasks are canceled and
      requeued without counting as a Task failure. Use this when the Service holds state that makes prior results
      unreliable once lost.

   If *maxAttempts* is greater than 0, *completedTasks* must be provided (for a *maxAttempts* given as a format string,
   checked when it is resolved at job creation). When *maxAttempts* is 0 it may be omitted, and then matters only when a
   Service this one lists begins a new Service Session, where an omitted value is read as `RERUN` (see [How Jobs Are
   Run](How-Jobs-Are-Run#service-failure-and-restart)). A Service may be suspended only if its *completedTasks* is
   `KEEP` (see [How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle)).

#### 9.5.1. Numeric `@fmtstring` fields

The numeric fields marked `@fmtstring` in [&lt;ServicePort&gt;](#93-serviceport),
[&lt;ServiceHealthCheck&gt;](#94-servicehealthcheck), and [&lt;ServiceRestartPolicy&gt;](#95-servicerestartpolicy) —
`port`; `readinessIntervalSeconds`, `readinessTimeoutSeconds`, `healthIntervalSeconds`, and `failureThreshold`; and
`maxAttempts` — may be given as a format string whose result is the integer. They are resolved at job creation, with the
scope of the `<Service>`'s *let* ([Section 9](#9-service-extension-service) item 3). When the value is a single
whole-field expression, its target type is `int?`: a `null` result is treated as if the field were not provided, and a
non-null result must satisfy the field's range.

### 9.6. `<ServiceScript>`

A `<ServiceScript>` is the object:

```yaml
let: <LetBindings> # @optional @extension EXPR
actions: <ServiceActions>
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional
```

1. *let* — An ordered list of expression bindings evaluated once, on the service host, when the Service is started. This
   is the host-context counterpart of the `<Service>`'s *let* and may reference `Session.*`, `Service.File.*`, and
   in-scope `Service.<name>.<port>.*`. Bound names are available in *actions* and *embeddedFiles*.
   See: [&lt;LetBindings&gt;](#36-letbindings).
2. *actions* — The actions to run at the different stages of the Service's lifecycle.
   See: [&lt;ServiceActions&gt;](#97-serviceactions).
3. *embeddedFiles* — Files embedded into the Service that are materialized to the Service's working directory before
   each of the Service's actions is run. See: [&lt;EmbeddedFile&gt;](#6-embeddedfile).
   1. Minimum number of items: If defined, then there must be at least one element in this list.
   2. Maximum number of items: There is no limit on the number of elements in this list.

### 9.7. `<ServiceActions>`

A `<ServiceActions>` is the object:

```yaml
onEnter: <Action> # @optional
onRun: <Action>
onHealthCheck: <Action> # @optional
onExit: <Action> # @optional
```

Where:

1. *onEnter* — A one-time setup action run before the first `onRun` of the Service in a Service Session; it runs once
   per Service Session, not once per launch of *onRun*. It is an ordinary action, like an Environment's `onEnter`: it
   runs to completion and its `timeout` and `cancelation` apply as for any `<Action>`. A non-zero exit status or a
   timeout is a start failure of the Service (see [How Jobs Are Run](How-Jobs-Are-Run#service-failure-and-restart)).
2. *onRun* — The long-lived action whose process is the service. The scheduler starts it, probes it for readiness and
   then for health, and expects it to run until canceled; an exit before then is an instance failure (see
   [How Jobs Are Run](How-Jobs-Are-Run#service-failure-and-restart)). The scheduler stops the Service by canceling
   *onRun* according to its `cancelation` method.
3. *onHealthCheck* — A short action the scheduler runs repeatedly, while *onRun* is running, as the probe of a
   `healthCheck` of type `COMMAND`; its exit status is the probe result (see
   [&lt;ServiceHealthCheck&gt;](#94-servicehealthcheck) and
   [Concurrency of onHealthCheck with onRun](#971-concurrency-of-onhealthcheck-with-onrun)). Must be defined if and only
   if the health check type is `COMMAND`. It should be read-only with respect to the Service Session's working
   directory, which it shares with *onRun*.
4. *onExit* — A cleanup action run after the Service's other actions have stopped for the last time in a Service
   Session, whether the Service stopped normally, failed, or was canceled, and whether or not *onRun* was ever launched.
   It runs to completion. A non-zero exit status is reported but does not change the outcome of the scope.

All four actions run in the Service Session with the format string scopes listed for [&lt;Service&gt;](#9-service-extension-service),
and embedded files are materialized before each of them runs, subject to the rules in
[Concurrency of onHealthCheck with onRun](#971-concurrency-of-onhealthcheck-with-onrun).

   > **NOTE:** When *onExit* does not define a *timeout* the action defaults to 300 seconds, or five minutes, for the
   same reasons as an Environment's *onExit*.

Implementations of this specification must watch the stdout of *onEnter*, *onRun*, and *onExit* for the standard
`openjd_status`, `openjd_progress`, and `openjd_fail` messages, and the stdout of *onRun* for the line
`openjd_service_ready` when the Service's health check *type* is `STDOUT` (for *onHealthCheck*, see
[Concurrency of onHealthCheck with onRun](#971-concurrency-of-onhealthcheck-with-onrun) rule 2). An `openjd_fail`
message on *onRun*'s stdout is itself an instance failure: the runtime must cancel *onRun* at once with its
cancelation method, and the message is the failure's reason. An `openjd_fail` message on *onEnter*'s or *onExit*'s
stdout marks that action failed when it exits, whatever its exit status — a start failure or an *onExit* failure
respectively — and the message is that failure's reason. See
[Service failure and restart](How-Jobs-Are-Run#service-failure-and-restart).

Implementations must additionally watch the stdout of *onEnter* for `openjd_env`, `openjd_redacted_env`, and
`openjd_unset_env`, with the same syntax and redaction rules as for an Environment's `onEnter` (see
[&lt;Environment&gt;](#4-environment)), including that `openjd_redacted_env` sets the variable only when the document
declares the `REDACTED_ENV_VARS` extension, while its value is redacted from the log regardless. A variable set this way
is set in the process environment of every subsequent action of the same Service Session — every instance of *onRun*,
*onHealthCheck*, and *onExit* — and is retained across relaunches of *onRun* within the Session. The process
environment of a Service's actions is built in this order, later entries taking precedence: the variables of the
Environments the Service Session entered (their *variables* and their `openjd_env` messages, in entry order, as in any
Session), then the Service's own *variables*, then variables set by the Service's *onEnter*. These messages are ignored
when emitted by *onRun*, *onHealthCheck*, or *onExit*.

#### 9.7.1. Concurrency of onHealthCheck with onRun

*onHealthCheck* is the only action in this specification that runs while another action of the same Session, *onRun*,
is running. Every other action in a Session runs one at a time. The following rules apply:

1. Materializing embedded files for one action must not modify any file that a still-running action of the same
   Session was given. Implementations may materialize each invocation's files to a distinct location, so that
   `Service.File.<name>` resolves to a different path in each action, or may materialize every invocation's files to
   one path and leave them in place, since their content is constant: a Service Session's format string values do not
   change for its lifetime. Either way, a file materialized for one action must remain in place, unchanged, until the
   Service Session ends: materializing a later action's files never removes or replaces an earlier action's. A path
   that *onEnter* captured (for example by exporting `Service.File.<name>` with `openjd_env`) therefore stays valid
   for *onRun* and *onExit*, even when their own `Service.File.<name>` resolves elsewhere.
2. The stdout of *onHealthCheck* is captured to the log, but no `openjd_*` message on it is honored: its result is its
   exit status.
3. Every line of stdout or stderr captured in a Service Session must be attributable to the action that produced it,
   including the output of wrap scripts under the `WRAP_ACTIONS` extension. How the attribution is recorded is
   implementation-defined. An implementation that produces a single plain-text log should tag each line from
   *onHealthCheck* with the action name (for example, `[onHealthCheck] connection refused`) and may leave the lines
   from *onRun* untagged. An implementation may suppress or collapse the output of invocations that succeed, provided the full output of every
   invocation that fails or exceeds its timeout is retained.
4. Invocations of *onHealthCheck* never overlap one another and never run while *onEnter* or *onExit* is running.
5. An invocation in progress when *onRun* exits is canceled and its result discarded (see
   [How Jobs Are Run](How-Jobs-Are-Run#service-lifecycle), constraint 10); one in progress when the Service Session ends
   is canceled before *onExit* runs.
6. Under the `WRAP_ACTIONS` extension, `onWrapServiceHealthCheck` runs while `onWrapServiceRun` is running. Wrap
   scripts used in a Service Session must tolerate concurrent invocation.

### 9.8. `<ServiceRequirement>`

Available in a Job Template's `externalServices` only.

A `<ServiceRequirement>` declares that the Job Template reads the endpoint of an external Service (see
[Services from Environment Templates](#122-services-from-environment-templates)): a Service that an attached
Environment Template defines, named `name`, with at least the ports listed. It is the Job Template's half of a contract
the scheduler checks at submission, and it makes the Service's endpoint available to the template's format strings
without the template declaring the Service itself.

A `<ServiceRequirement>` is the object:

```yaml
name: <ServiceName>
ports: [ <ServiceRequirementPort>, ... ]
```

Where:

1. *name* — The `name` of the external Service required. See: [&lt;ServiceName&gt;](#92-servicename) and
   [Job Template](#11-job-template) *externalServices* constraint 4.
2. *ports* — The ports of the Service that the Job Template uses. See:
   [&lt;ServiceRequirementPort&gt;](#981-servicerequirementport). Constraints:
    1. Minimum number of elements: 1.
    2. Maximum number of elements: 10.
    3. No two elements may have the same value for the *name* property.

The scheduler matches each requirement at submission
([Services from Environment Templates](#122-services-from-environment-templates) item 2). An entry puts nothing in the
Service's scope by itself; a Step, Service, or Job Environment that uses the Service lists it in `dependencies` as it
would an inline Service, and an entry that nothing lists is rejected at template validation
([Service scope](#91-service-scope) rule 4).

#### 9.8.1. `<ServiceRequirementPort>`

A `<ServiceRequirementPort>` is the object:

```yaml
name: <Identifier>
protocol: enum("TCP", "UDP") # @optional
```

Where:

1. *name* — The `name` of a port the external Service declares. It is the second component of
   `Service.<service>.<port>.*` references. Must not be `File`.
2. *protocol* — The transport protocol the Job Template expects the port to carry, matched against the attached
   Service's port at submission ([Services from Environment Templates](#122-services-from-environment-templates) item
   2). One of `TCP` or `UDP`. Default: `TCP`.

### 9.9. Validation

This section indexes the rules the `SERVICE` extension adds; each is stated in full where the pointer leads. Every rule
is checked at template validation, except that the [numeric `@fmtstring` fields](#951-numeric-fmtstring-fields) are
checked when resolved at job creation and the last two rules need the combined Job and are checked at submission.

| Rule | Stated in |
|---|---|
| Every `Service.*` reference names a declared or required Service and port, appears only where permitted, and the referencing entity lists the Service in its `dependencies` | [Section 9](#9-service-extension-service); [Value References](#731-value-references) |
| No `Service.*` value in a field resolved at job creation, nor in an Environment whose explicit `runScope` includes `SERVICE` | [Section 9](#9-service-extension-service); [&lt;Environment&gt;](#4-environment) item 4 constraint 2 |
| `runScope` holds recognized names without duplicates and is absent from `stepEnvironments` | [&lt;Environment&gt;](#4-environment) item 4 constraints 1, 3, and 4 |
| An Environment's `dependencies` is well formed and absent from `stepEnvironments` | [&lt;Environment&gt;](#4-environment) item 3 constraints 2–4 |
| The wrap hooks an Environment defines are exactly those its `runScope` calls for | [&lt;EnvironmentActions&gt;](#43-environmentactions) `WRAP_ACTIONS` constraint 6 |
| Every `dependencies` entry is well formed | [&lt;StepDependency&gt;](#32-stepdependency) constraints 1, 2, and 4; [Environment Template](#12-environment-template) item 6 constraint 5 |
| The `dependencies` graph is acyclic | [&lt;StepDependency&gt;](#32-stepdependency) constraint 3 |
| Every inline Service, and every `externalServices` entry, is listed by some Step, Service, or Job Environment | [Service scope](#91-service-scope) rule 4 |
| Service, requirement, and port names are identifiers other than `File`, unique within their lists, and no requirement shares a `name` with an inline Service | [&lt;ServiceName&gt;](#92-servicename); [Job Template](#11-job-template) *externalServices* constraint 4 |
| `externalServices` appears only in a Job Template | [Job Template](#11-job-template) *externalServices* constraint 5 |
| `healthCheck` is consistent with `<ServiceActions>`, with `ports`, and with its own `type` | [&lt;Service&gt;](#9-service-extension-service) item 7; [&lt;ServiceHealthCheck&gt;](#94-servicehealthcheck) items 2, 3, and 6; [&lt;ServiceActions&gt;](#97-serviceactions) item 3 |
| No two ports of a Service with the same `protocol` have the same `port` number | [&lt;Service&gt;](#9-service-extension-service) item 6 constraint 4 |
| `completedTasks` is provided when `maxAttempts` is greater than 0 | [&lt;ServiceRestartPolicy&gt;](#95-servicerestartpolicy) item 2 |
| A template that lists `SERVICE` also lists `EXPR` | [Section 9](#9-service-extension-service) |
| A wrapping Environment from a document without `SERVICE` is not combined with a Job that has any Service *(submission)* | [Services from Environment Templates](#122-services-from-environment-templates) item 4 |
| Each `externalServices` entry matches exactly one attached Service *(submission)* | [Services from Environment Templates](#122-services-from-environment-templates) item 2 |

## 10. Additional Information

* The Cc unicode character category is all [C0](https://www.unicode.org/charts/PDF/U0000.pdf)
  and [C1](https://www.unicode.org/charts/PDF/U0080.pdf) characters.
  * This is a category of 65 non-printable characters such as NUL, BEL, Backspace, DEL,
     tab, newline, carriage return, and form feed.

## 11. License

Copyright ©2023 Amazon.com Inc. or Affiliates ("Amazon").

This Agreement sets forth the terms under which Amazon is making the Open Job Description
Specification ("the Specification") available to you.

### 11.1. Copyrights

This Specification is licensed under [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/deed.en).

### 11.2. Patents

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

### 11.3. Additional Information

For more info see the [LICENSE file].

[LICENSE FILE]: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/LICENSE
