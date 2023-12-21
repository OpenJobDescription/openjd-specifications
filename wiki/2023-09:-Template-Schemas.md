# Template Schemas [Version: 2023-09]

This document contains the formal specifications for the Open Job Description Template schemas. There are two schemas
defined in this document:

1. The Job Template describes the shape of a Job, its runtime environment, and all of the processes that will run as part
of it. Jobs are created from Job Templates by providing a value for each of the Job Parameters defined in the Template,
and instantiating the template with those values.
2. The Environment Template describes an Environment that is defined outside of a Job. This can be used in render management
systems to allow users to define Environments that are automatically applied to Job Templates that are submitted for rendering.

Both Templates are expressed as UTF-8 documents in either
[ECMA-404 JavaScript Object Notation (JSON)](https://www.json.org/json-en.html) or
[YAML Ain't Markup Language (YAML) 1.2](https://yaml.org/) interchange format.

Notations used in this document to annotate aspects of the schema definition:

* `@fmtstring` - The value of the annotated property is a Format String. See [Format Strings](#73-format-strings).
   * `@fmtstring[host]` - The value is evaluated at runtime on the worker host on which the job is running. The value is otherwise
     evaluated when the job template is submitted and the render manager is constructing a job.
* `@optional` - The annotated property is optional.

## 1. Root elements

### 1.1. Job Template

```yaml
specificationVersion: "jobtemplate-2023-09"
$schema: <string> # @optional
name: <JobName> # @fmtstring
description: <Description> # @optional
parameterDefinitions:  [ <JobParameterDefinition>, ... ] # @optional
jobEnvironments: [ <Environment>, ... ] # @optional
steps: [<StepTemplate>, ...]
```

Where:

1. *specificationVersion* - A literal that identifies the document as adhering to this schema.
2. *$schema* - Ignored. This property is allowed for compatibility with JSON-editing IDEs.
3. *name* - The name to give to a Job that is created from the template. See: [&lt;JobName&gt;](#111-jobname).
4. *description* - A description to apply to all Jobs that are created from the template. It has no functional purpose,
   but may appear in UI elements. See: [&lt;Description&gt;](#72-description).
5. *parameterDefinitions* -  A list of the Job Parameters that are available within the Job Template. Values
   for Job Parameters are defined when submitting the Job Template to create a Job to a render management system.
   The values of Job Parameters can be referenced in Format Strings.
   See: [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition).
      * Minimum number of elements: If provided, then this list must contain at least one element.
      * Maximum number of elements: The list must not contain more than 50 elements.
6. *jobEnvironments* — An ordered list of the environments that are required to run Tasks in the Jobs created by this Job
   Template. These are entered in the order provided at the start of every Session for Tasks in the Job, and exited in the
   reverse order at the end of those Sessions. See: [&lt;Environment&gt;](#4-environment). Constraints:
      1. No two Environments in this list may have the same value for the `name` property.
      2. The Environments defined in this list must not have the same `name` as an Environment
         defined in any Step within the same Job Template.
7. *steps* — A list of the Steps in the Job. See: [&lt;StepTemplate&gt;](#3-steptemplate).

#### 1.1.1. `<JobName>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Allowed characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 128 characters, after the format string has been resolved.

### 1.2. Environment Template

```yaml
specificationVersion: environment-2023-09
parameterDefinitions: [ <JobParameterDefinition>, ... ] # @optional
environment: <Environment>
```

1. *specificationVersion* - A literal that identifies the document as adhering to this schema.
2. *parameterDefinitions* -  A list of the Job Parameters that are available within the Environment Template. Values
   for Job Parameters are defined when submitting a Job Template to create a Job to a render management system.
   When submitting a job using a Job Template when one or more Environment Templates are applied, the job parameter
   definitions defined in the Job Template are compared against those defined in the Environment Template(s). Both the
   Job Template and Environment Template(s) are allowed to contain definitions for the same job parameter, but the
   submission is rejected if any of the definitions of the same job parameter are in conflict (e.g. they define different
   default values, different minimum lengths/values, or different userInterfaces).
   The values of Job Parameters can be referenced in Format Strings.
   See: [&lt;JobParameterDefinition&gt;](#2-jobparameterdefinition).
      * Minimum number of elements: If provided, then this list must contain at least one element.
      * Maximum number of elements: The list must not contain more than 50 elements.
3. *environment* - The definition of the Environment that the Environment Template defines. 
   See [&lt;Environment&gt;](#4-environment).

## 2. `<JobParameterDefinition>`

```bnf
<JobParameterDefinition> ::= <JobStringParameterDefinition> | <JobPathParameterDefinition> | 
                             <JobIntParameterDefinition> | <JobFloatParameterDefinition> 
```

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
   control: enum("LINE_EDIT", "MULTILINE_EDIT", "DROPDOWN_LIST", "CHECK_BOX", "HIDDEN")
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
7. *userInterface* — User interface properties for this parameter. This metadata defines how a user interface element
   should be constructed to allow a user to input a value for the parameter.
    1. *control* — The user interface control to use when editing this parameter.
       The default, if not provided, is "LINE_EDIT" when *allowedValues* is not provided, “DROPDOWN_LIST” when it is.
        1. “LINE_EDIT“ — This is a freeform string line edit control. Cannot be used when *allowedValues* is provided.
        2. “MULTILINE_EDIT” — This is a freeform string multi-line edit control. It uses a fixed width font, intended for
           editing script code. The vertical size of this control is set to grow to fit the available space. Cannot be
           used when *allowedValues* is provided.
        3. “DROPDOWN_LIST” — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is also provided.
        4. “CHECK_BOX” — This is a checkbox control. It requires that *allowedValues* is also provided, and contains two
           values, case insensitive, one representing true and another representing false.
            * Valid pairs are [“true”, “false”], [“yes”, “no”], [“on”, “off”], and [“1”, “0”].
        5. “HIDDEN” — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter’s edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).

### 2.2. `<JobPathParameterDefinition>`

Defines a job parameter that allows input to a Job Template of a single string value that represents a file or directory
path on a filesystem. This parameter type differs from a
[`<JobStringParameterDefinition>`](#21-jobstringparameterdefinition) in that the value of the parameter automatically has
defined and matching path mapping rules applied to it.

The value of a Job Parameter of this type referenced in format strings as both:

1. `Param.<name>` — the value of the parameter with applicable path mapping applied to it; and
2. `RawParam.<name>` — the value of the parameter exactly as it was input to the job, with no path mapping applied to it.

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
   control: enum("CHOOSE_INPUT_FILE", "CHOOSE_OUTPUT_FILE", "CHOOSE_DIRECTORY", "DROPDOWN_LIST", "HIDDEN")
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
   See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue).
4. *allowedValues* — An array of the values that the parameter is allowed to be. It is an error to provide a value that is
   not in this list, if the list is defined. See: [&lt;JobParameterStringValue&gt;](#25-jobparameterstringvalue).
5. *minLength* — The minimum allowable length of the parameter string value.
6. *maxLength* — The maximum allowable length of the parameter string value.
7. *objectType* — The type of object the path represents; either a FILE or a DIRECTORY. Default is DIRECTORY.
8. *dataFlow* — Whether the object the path represented serves as input, output or both for the Job. Default is NONE.
9. *userInterface — User interface properties for this parameter*
    1. *control* — The user interface control to use when editing this parameter. The default, if not provided, depends on
       *objectType*, *dataFlow*, and *allowedValues*. If *objectType* is FILE, then if *dataFlow* is "OUT", it is
       "CHOOSE_OUTPUT_FILE", otherwise it is "CHOOSE_INPUT_FILE". If *objectType* is not "FILE", then it is
       "CHOOSE_DIRECTORY". If *allowedValues* is provided, then the default is instead "DROPDOWN_LIST".
        1. “CHOOSE_INPUT_FILE“ — This is a combination of a line edit and a button that uses the system’s input file
           dialog. Cannot be used when *allowedValues* is provided.
        2. “CHOOSE_OUTPUT_FILE” — This is a combination of a line edit and a button that uses the system’s output/save
           file dialog. Cannot be used when *allowedValues* is provided.
        3. “CHOOSE_DIRECTORY” — This is a combination of a line edit and a button that uses the system’s directory dialog.
           Cannot be used when *allowedValues* is provided.
        4. “DROPDOWN_LIST” — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is also provided.
        5. “HIDDEN” — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter’s edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. fileFilters — Can be provided when the *uiControl* is “CHOOSE_INPUT_FILE” or “CHOOSE_OUTPUT_FILE”. Defines the file
       filters that are shown in the file choice dialog. Maximum of 20 filters.
    5. fileFilterDefault — Can be provided when the *uiControl* is “CHOOSE_INPUT_FILE” or “CHOOSE_OUTPUT_FILE”. The
       default file filter that’s shown in the file choice dialog.

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
   control: enum("SPIN_BOX", "DROPDOWN_LIST", "HIDDEN")
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
      “SPIN_BOX” when *allowedValues* is not provided, “DROPDOWN_LIST” when it is.
        1. “SPIN_BOX“ — This is an integer editing control. Cannot be used when *allowedValues* is provided.
        2. “DROPDOWN_LIST” — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is provided.
        3. “HIDDEN” — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter’s edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *singleStepDelta* — How much the value changes for a single step modification, such as selecting an up or down
       arrow in the user interface control.

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
   control: enum(SPIN_BOX, DROPDOWN_LIST, HIDDEN)
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
       “SPIN_BOX” when *allowedValues* is not provided, “DROPDOWN_LIST” when it is.
        1. “SPIN_BOX“ — This is a floating point editing control. Cannot be used when *allowedValues* is provided.
        2. “DROPDOWN_LIST” — This is a dropdown list, for selecting from a fixed set of values. It requires that
           *allowedValues* is provided.
        3. “HIDDEN” — This hides the parameter from the user interface.
    2. *label* — The user interface label to use when displaying the parameter’s edit control. If not provided, the
       implementation should default to using the parameter *name*.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    3. *groupLabel* — Parameters with the same *groupLabel* value should be placed together in a grouping control with the
       value of *groupLabel* as its label.
       See: [&lt;UserInterfaceLabelStringValue&gt;](#26-userinterfacelabelstringvalue).
    4. *decimals* — This is the number of places editable after the decimal point. If d*ecimals* is not provided then an
       adaptive decimal mode will be used.
    5. *singleStepDelta* — How much the value changes for a single step modification, such as selecting an up or down
       arrow in the user interface control. If d*ecimals* is provided, this is an absolute value, otherwise it is the
       fraction of the current value to use as an adaptive step.

### 2.5. `<JobParameterStringValue>`

A string value subject to the following constraints:

1. Allowable characters: Any.
2. Minimum length: There is no minimum length.
3. Maximum length: 1024 characters.

### 2.6. `<UserInterfaceLabelStringValue>`

A string value subject to the following constraints:

1. Allowable characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 64 characters.

### 2.7. `<JobPathParameterFileFilter>`

Represents one named file type for an input or output file choice dialog. For example:
`{“label”: “Image Files”, “patterns”: [“*.png”, “*.jpg”, “*.exr”]}` or `{“label”: “All Files”, “patterns”: [“*”]}`.

A `<JobPathParameterFileFilter>` is the object:

```yaml
label: <UserInterfaceLabelStringValue>
patterns: [ <FileDialogFilterPatternStringValue>, ... ]
```

### 2.8. `<FileDialogFilterPatternStringValue>`

A string value subject to the following constraints:

1. Allowable values: “*”, “*.*”, and “*.[:file-extension-chars:]+”. The characters that :file-extension-chars: can take on
   are any unicode character except
    1. The Cc unicode character category.
    2. Path separators “\” and “/”.
    3. Wildcard characters “*”, “?”, “[”, “]”.
    4. Characters commonly disallowed in paths: “#”, “%”, “&”, “{”, “}”, “<”, “>”, “$”, “!”, “‘”, “\"", ":", "@", "`", "|",
       and "=".
2. Minimum length: 1 character.
3. Maximum length: 20 characters.

## 3. `<StepTemplate>`

A `<StepTemplate>` defines a single Step in the Job; the action(s) that it takes, its dependencies, the parameter space
that maps to the Step's Tasks, and its runtime environment and requirements.

A `<StepTemplate>` is the object:

```yaml
name: <StepName>
description: <Description> # @optional
dependencies: [ <StepDependency>, ... ] # @optional
stepEnvironments: [ <Environment>, ... ] # @optional
hostRequirements: <HostRequirements> # @optional
parameterSpace: <StepParameterSpaceDefinition> # @optional
script: <StepScript>
```

Where:

1. *name* - The name to identify the Step within the Job. Each Step within a Job Template must have name that differs from
   the names of all other Steps in the same Job Template. See: [&lt;StepName&gt;](#31-stepname).
2. *description* — A description to apply to the step. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *dependencies* - A list of the dependencies of this Step. These dependencies must be resolved before the Tasks of the
   Step may be scheduled. See: [&lt;StepDependency&gt;](#32-stepdependency)
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: There is no maximum defined, though implementations may choose to constrain the number of
    dependencies.
4. *stepEnvironments* — An ordered list of the environments that are required to run Tasks in this Step.
  These are entered in the order provided at the start of every Session for Tasks in the Step, and exited in the reverse
  order at the end of those Sessions.
  See: [&lt;Environment&gt;](#4-environment).
    * Constraints:
        1. No two Environments in this list may have the same value for the `name` property.
        2. The Environments defined in this list must not have the same `name` as a Job Environment defined in the same
           Job Template.
5. *hostRequirements* — Describes the requirements on Worker host's capabilities that must be satisfied for the Task(s) of
   the Step to be scheduled to the host. See: [&lt;HostRequirements&gt;](#33-hostrequirements).
6. *parameterSpace* - Defines the parameterization of the Step's action; the available parameters, the values that they
   take on, and how those parameters' values are combined to produce the Tasks of the Step. Absent this property the Step
   is run a single time.
7. *script* - The action that is taken by this Step's Tasks when they are run on a Worker host.

### 3.1. `<StepName>`

A string subject to the following constraints:

1. Allowed characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 character.
3. Maximum length: 64 characters.

### 3.2. `<StepDependency>`

This entity is used by the template author to specify a Step in the same Job that a Step depends upon.

A `<StepDependency>` is the object:

```yaml
dependsOn: "<StepName>"
```

Where:

1. *dependsOn* — Provides the name of another step in the same job upon which this step depends. The Task(s) of this Step
   may be scheduled only when the depended-upon Step has fully completed successfully.

### 3.3. `<HostRequirements>`

This entity is used by the template author to describe the requirements on Worker host and/or render manager's available
capabilities that must be satisfied for the Task(s) of the Step to be scheduled to the host.

Each requirement corresponds to an attribute of a host or render manager that must be satisfied to allow the Step to
be scheduled to the host. Some examples of concrete attributes include processor architecture (x86_64, arm64, etc), the
number of CPU cores, the amount of system memory, or available floating licenses for an application. We also allow for
user-defined whose meaning is defined by the customer; a “SoftwareConfig” requirement whose values could be “Option1” or “Option2”,
for example.

There are two types of requirements: attribute and amount.

A `<HostRequirements>` is the object:

```yaml
amounts: [ <AmountRequirement>, ... ] # @optional
attributes: [ <AttributeRequirement>, ... ] # @optional
```

Where:

1. *amounts* - Defines a set of quantifiable requirements on the host that must be met and reserved for a Session running
   Tasks from this Step to be scheduled to the host. See: [&lt;AmountRequirement&gt;](#331-amountrequirement).
2. *attributes* - Defines a set of attributes that a host must have for a Session running Tasks from this Step to be
   scheduled to the host. See: [&lt;AttributeRequirement&gt;](#332-attributerequirement).

With the constraints:

1. If this object is provided in a Job Template, then at least one of the *amounts* or *attributes* properties must be
   defined.
2. The sum of the lengths of the *amounts* and *attributes* arrays must not exceed 50 elements.

#### 3.3.1. `<AmountRequirement>`

Amount requirements are the mechanism for defining a quantity of something that the Worker host or render manager needs to have
for a Step to run. They represent quantifiable things that need to be reserved to do the work — vCPUs, memory, licenses, etc. They
are always non-negative floating point valued, and a Step can require a certain amount of that capability to be able to run —
“at least 4 CPU cores” for example. Further, a quantity of each amount required are logically allocated to a Session while that
session is running on a host. A Step requiring, say, “at least 4 CPU cores”, might result in a Session with 4 CPU cores allocated
to it being created on a host. Those cores are reserved for that Session while that Session is running on the host; effectively
making the number of available cores on the host 4 less for scheduling purposes during the duration of the Session. Logically
allocating amounts to Sessions is the key mechanism by which system resources can be optimally utilized through bin packing
multiple running Sessions onto hosts at the same time.

An `<AmountRequirement>` is the object:

```yaml
name: <AmountCapabilityName>
min: <nonnegativefloat> # @optional
max: <positivefloat> # @optional
```

Where:

1. *name* - Is a dotted name that identifies the specific host capability that is being required.
2. *min* - If provided, then the host must have at least the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host. If not provided, then the default is 0 unless
   the specific host capability defines a minimum.
3. *max* - If provided, then the host must have at least the given amount of the named capability available and reserved
   for a Session running Tasks from this Step to be scheduled to the host.

Subject to the constraint that at least one of *min* or *max* must be provided.

##### 3.3.1.1. `<AmountCapabilityName>`

A string subject to the following constraints.

1. Minimum length: 1 character.
2. Maximum length: 100 characters.
3. Its format matches the pattern `[<Identifier>:]amount.<Identifier>[.<Identifier>]*` where:
   1. `[<Identifier>:]` denotes an optional vendor-specific prefix.
   2. This specification has reserved specific values of the first `<Identifier>` after "amount." for use in this and
      future revisions. The reserved values are: "worker", "job", "step", and "task"
4. The value is not case sensitive - All comparisons between strings of this type must be case insensitive comparisons.

See [&lt;Identifier&gt;](#71-identifier) for information on the `<Identifier>` substring.

This specification defines the following amount capabilities, but an implementation is allowed, and encouraged, to allow
users to define their own custom capabilities.

|**Capability Name**|**Minimum Value**|**Description**|
|---|---|---|
|amount.worker.vcpu        |1|A number of vCPUs/CPU-cores available on the host.|
|amount.worker.memory      |0|An amount of system memory available on the host. Units: MiB. |
|amount.worker.gpu         |0|A number of GPUs available on the host.|
|amount.worker.gpu.memory  |0|An amount of memory available in GPUs on the host. Units: MiB.|
|amount.worker.disk.scratch|0|A static amount of disk storage installed on the host for use as scratch space. Units: GiB.|

#### 3.3.2. `<AttributeRequirement>`

Attribute requirements are the mechanism for defining an abstract or concrete attribute/property the host must to have for
a Step to run. They are always defined on a host as a set of strings. A Step can assert that it requires that a host have
specific value(s) of the attribute for it to be scheduled to the host.

An `<AttributeRequirement>` is the object:

```yaml
name: <AttributeCapabilityName>
anyOf: [ <AttributeCapabilityValue>, ... ] # @optional @fmtstring
allOf: [ <AttributeCapabilityValue>, ... ] # @optional @fmtstring
```

Where:

1. *name* - Is a dotted name that identifies the specific host capability that is being required.
2. *anyOf* - For the Step to be scheduled to it, the host's value for the named capability must have **at least one** of
   the given values. This comparison is case insensitive.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.
3. *allOf* - For the Step to be scheduled to it, the host's value for the named capability must have **all** of the given
   values. This comparison is case insensitive.
    * Minimum number of elements: If provided, then this list must contain at least one element.
    * Maximum number of elements: The list must not contain more than 50 elements.

Subject to the constraint that at least one of *anyOf* or *allOf* must be provided.

##### 3.3.2.1. `<AttributeCapabilityName>`

A string subject to the following constraints.

1. Minimum length: 1 character.
2. Maximum length: 100 characters.
3. Its format matches the pattern `[<Identifier>:]attr.<Identifier>[.<Identifier>]*` where:
   1. `[<Identifier>:]` denotes an optional vendor-specific prefix.
   2. This specification has reserved specific values of the first `<Identifier>` after "amount." for use in this and
      future revisions. The reserved values are: "worker", "job", "step", and "task"
4. The value is not case sensitive - All comparisons between strings of this type must be case insensitive comparisons.

See [&lt;Identifier&gt;](#71-identifier) for information on the `<Identifier>` substring.

This specification defines the following attribute capabilities, but an implementation is allowed, and encouraged, to
allow users to define their own custom capabilities.

|**Capability Name**|**Values**|**Description**|
|---|---|---|
|attr.worker.os.family|linux, windows, macos|The family of operating system on the host.|
|attr.worker.cpu.arch |x86_64, arm64|The architecture of the CPUs on the host.|

##### 3.3.2.2. `<AttributeCapabilityValue>`

A [Format String](#73-format-strings) subject to the following constraints:

1. Minimum length: 1 character.
2. After the format string has been resolved:
    1. Max length: 100 characters
    2. Unicode alphanumeric characters in the latin character set, plus the underscore and hyphen characters.
    3. Must start with either a letter character or the underscore character.

### 3.4. `<StepParameterSpaceDefinition>`

A `<StepParameterSpaceDefinition>` is the object:

```yaml
taskParameterDefinitions: [ <TaskParameterDefinition>, ... ]
combination: <CombinationExpr> # @optional
```

Where:

1. *taskParameterDefinitions* — This is a list that defines the task parameters over which the Step's script is
   parameterized. Each task parameter defines its name, type, and the range of values that it takes.
    1. Minimum number of elements: If provided, then this array must have at least one element in the list.
    2. Maximum number of elements: The list must contain no more than 16 elements in the list.
2. *combination* — An expression that defines how the task parameters are combined to produce the parameter space that
   maps a Step to a set of Tasks. Each Task has a single value for each task parameter that specifies its coordinates in
   the defined space. If not provided, then the default is all possible combinations of task parameter values.

#### 3.4.1. `<TaskParameterDefinition>`

Definition of a single task parameter; its name, type, and the range of values that it takes.

```bnf
<TaskParameterDefinition> ::= <IntTaskParameterDefinition> | <FloatTaskParameterDefinition> |
                              <StringTaskParameterDefinition> | <PathTaskParameterDefinition>
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
2. *type* - The literal "INT", defining this parameter as integer valued.
3. *range* — The list of values that the parameter takes on to define Tasks of the Step.
4. `<IntRangeList>` is subject to the constraints:
   * Minimum number of elements: If provided, then this list must contain at least one element.
   * Maximum number of elements: The list must not contain more than 1024 elements.

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>`; and
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

An floating point valued task parameter. An `<FloatTaskParameterDefinition>` is the object:

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
2. *type* - The literal "FLOAT", defining this parameter as floating point valued.
3. *range* — The list of values that the parameter takes on to define Tasks of the Step.
4. `<FloatRangeList>` is subject to the constraints:
   * Minimum number of elements: If provided, then this list must contain at least one element.
   * Maximum number of elements: The list must not contain more than 1024 elements.

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>`; and
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

1. `Task.Param.<name>`; and
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
2. *type* - The literal "PATH", defining this parameter as string valued path parameter.
3. *range* — The list of values that the parameter takes on to define tasks of the step.
   See: [&lt;TaskParameterStringValue&gt;](#342-taskparameterstringvalue).
    1. Minimum list length: One element
    2. Maximum list length: 1024 elements

The value of a task parameter of this type can be referenced in format strings that will be evaluated when running a Task
using the following names:

1. `Task.Param.<name>` — the value of the parameter with relevant path mapping rules applied to it; and
2. `Task.RawParam.<name>` — the value of the parameter as it was defined, with no path mapping rules applied.

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
5. Every comma-separated expression within an associative operator must All of the listed task parameters must have the
   exact same number of values defined in their range.

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

### 3.5. `<StepScript>`

The Script of a Step defines the properties of the action that the Step runs on a Worker host.

A `<StepScript>` is the object:

```yaml
actions: <StepActions>
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional
```

Where:

1. *actions* — The Actions that are run by Tasks of the Step.
2. *embeddedFiles* — Files embedded into the Step that are materialized to a Session's working directory as the Step's
   Task is running within the Session. See: [&lt;EmbeddedFile&gt;](#6-embeddedfile).
   1. Minimum number of items: If defined, then there must be at least one element in this list.
   2. Maximum number of items: There is no limit on the number of elements in this list.

The format string scopes available to format strings within a `<StepScript>` are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters.
2. `Session.*` — Values such as the Session’s working directory.
3. `Task.*` — Values of embedded file locations defined within the `<StepScript>`, and Task Parameters.

#### 3.5.1. `<StepActions>`

The Actions of a Step are the set of commands that are run by the Worker Agent to accomplish the goal(s) of the Step.

```yaml
onRun: <Action>
```

Where:

1. *onRun* - The action that is run when a Task for the Step is run on a host. See: [&lt;Action&gt;](#5-action).

## 4. `<Environment>`

The Environment is a mechanism provided in this specification to enable users to amortize expensive, or time-consuming,
setup and tear-down operations of the worker host's environment over a sequence of Tasks run back-to-back on the worker.
Each Environment defines actions to run on a host when entering or exiting the Environment.

An `<Environment>` is the object:

```yaml
name: <EnvironmentName>
description: <Description> # @optional
script: <EnvironmentScript> # @optional
variables: <EnvironmentVariables> # @optional
```

Where:

1. *name* - An identifier given to the environment that is unique within the Environment's defined scope.
2. *description* — A description to apply to the environment. It has no functional purpose, but may appear in UI elements.
   See: [&lt;Description&gt;](#72-description).
3. *script* — The action that is taken by this Environment when it is run on a Worker host.
4. *variables* — A set of environment variable name/value pairs, with the values being
   [Format Strings](#73-format-strings) that are resolved when entering the environment. The specified variables must be
   set prior to running either `onEnter` or `onExit` for the environment, and for all actions that are run with the
   environment active.
5. At least one of "script" or "variables" must be provided.

The format string scopes available to format strings within an Environment are:

1. `Param.*` and `RawParam.*` — Values of Job Parameters.
2. `Session.*` — Values such as the Session’s working directory.
3. `Env.*` — Scope of the environment entity itself. Values such as the embedded files defined within the Environment
   entity.

Implementations of this specfication must watch STDOUT when running the `onEnter` action for any line matching:

1. The regular expression `^openjd_env: (.*)$`. The captured value must be of the form `<varname>=<value>` where
   `varname` is the name of an environment variable, and `value` is the value to assign to it. The defined value of the
   given variable will be set for all actions that are run with the environment active.
2. The regular expression `^openjd_unset_env: (.*)$`. The captured value must be of the form `<varname>` where
   `varname` is the name of an environment variable. The given environment variable will be unset as long as this
   environment is active. If an environment both sets and unsets a particular environment variable, then the unset takes
   precedence.

### 4.1. `<EnvironmentName>`

A string value subject to the following constraints:

1. Allowable characters: Any unicode character except those in the Cc unicode character category.
2. Minimum length: 1 characters.
3. Maximum length: 64 characters.

### 4.2. `<EnvironmentScript>`

An `<EnvironmentScript>` is the object:

```yaml
actions: <EnvironmentActions>
embeddedFiles: [ <EmbeddedFile>, ... ] # @optional
```

1. *actions* — The actions to run at different stages of the Environment’s lifecycle.
2. *embeddedFiles* — Files embedded into the Environment that are materialized to a Session's working directory as the
   Environment is running within the Session. See: [&lt;EmbeddedFile&gt;](#6-embeddedfile).
   1. Minimum number of items: If defined, then there must be at least one element in this list.
   2. Maximum number of items: There is no limit on the number of elements in this list.

### 4.3. `<EnvironmentActions>`

An `<EnvironmentActions>` is the object:

```yaml
onEnter: <Action>
onExit: <Action> # optional
```

1. *onEnter* — The action run when the environment is being entered on a host.
2. *onExit* — The action run when the environment is being exited on a host.

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
cancelation: <CancelationMethod> # @optional
```

1. *command* — A [Format String](#73-format-strings) containing the name of a runnable command that is run on a Worker
   host.
2. *args* — An array of [Format Strings](#73-format-strings) that will be passed as arguments to the **command** when the
   command is run on the host.
3. *timeout* — The positive number of seconds that the command is given to successfully run to completion. A command that
   does not return before the timeout is canceled and is treated as a failed run. Default, if not provided, is that the
   command does not have a limited timeout.
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

The cancelation method defines the process by which an action is canceled.

```bnf
<CancelationMethod> ::= <CancelationMethodTerminate> | <CancelationMethodNotifyThenTerminate>
```

#### 5.3.1. `<CancelationMethodTerminate>`

An action defined to cancel by this method cancels the running command by sending it a terminal signal.

A `<CancelationMethodTerminate>` is the object:

```yaml
mode: "TERMINATE"
```

The signal sent to the command is:

1. On Posix systems — Send SIGKILL to the entire process tree when a cancel is requested.
2. On Windows systems - Terminate the entire process tree when a cancel is requested.

#### 5.3.2. `<CancelationMethodNotifyThenTerminate>`

An action defined to cancel by this method cancels the running command by sending it a notification signal that it should
gracefully shutdown, waiting for a period of time for the command to exit, and then sending it a terminal signal if it has
not exited by the end of the waiting period.

A `<CancelationMethodNotifyThenTerminate>` is the object:

```yaml
mode: "NOTIFY_THEN_TERMINATE"
notifyPeriodInSeconds: <posinteger> # @optional
```

Where:

1. *notifyPeriodInSeconds* — Defines the maximum number of seconds between the two signals. It is possible that the actual
   duration allowed in a particular cancel event will be less than this amount if circumstances warrant.
   1. Maximum value: 600
   2. Defaults:
      * 120 if the Action is the "onRun" action of a `<StepActions>` object.
      * 30 otherwise.

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
   application running the action receives a signal of its own that indicates that it must shutdown (near)immediately
   while it is waiting for the grace period of a cancel to elapse. These subsequent signals will be accompanied by a
   change to the `cancel_info.json` file in the working directory.

## 6. `<EmbeddedFile>`

A step or environment script can have data attached to it via this mechanism. The embedded data is made available to the
environment/task action(s) as a file within the Session working directory while being run on a host. This file is
written prior to every one of the corresponding actions each time that they are run. The materialized files’ permissions
are read-only by only the user under which the task will be run on the worker host.

```bnf
<EmbeddedFiles> ::= <EmbeddedFileText>
```

### 6.1. `<EmbeddedFileText>`

Embedding of a plain text file into the template. The *data* provided in the file is written as a plain text file. This
file is written prior to every one of the script’s actions each time that they are run.

```yaml
name: <Identifier>
type: "TEXT"
filename: <Filename> # @optional
runnable: <bool> # @optional
data: <DataString> # @fmtstring[host]
```

* *name* — The name of the embeded file. This value is used in Format String references to this file.
* *filename* — The filename for the written file. This must strictly be the basename of the filename, and not contain any
  directory pathing. (i.e. `foo.txt` not `dir/foo.txt`). Defaults to a random filename if not provided.
* *runnable* — A boolean `True` value indicates that the file written to disk should be have its execute-permissions set
  to true. Defaults to `False` if not provided.
* *data* — The string data that will be written to the file exactly as it appears.

The fully-qualified path of the file written by the host can be referenced in format strings using the following names:

1. `Task.File.<name>` - If the embedded file is part of a `<StepScript>` object; or
2. `Env.File.<name>`- If the embedded file is part of an `<Environment>` object.

#### 6.1.1. `<Filename>`

A string subject to the following constraints:

* Min length: 1
* Max length: 64
* Characters allowed: Any characters allowed in filenames on the host operating system.

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
4. Maximum length: 64 character

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

#### 7.3.1. Value References

|**Value**|**Description**|**Scope**|
|---|---|---|
|`Param.<ParamName>`|Values of the Job parameters are available within the `Param` object. This is the same as `RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it. |All types except PATH are available in every Format String in the Job Template. For PATH type parameters, this is only available within format strings that are within an Environment or StepScript context.|
|`RawParam.<ParamName>`|Values of the Job parameters are available within the `RawParam` object. This is always the exact input value of the job parameter.|Available in every Format String in the Job Template.|
|`Task.Param.<ParamName>`|Values of task parameters are available within the `Task.Param` object. This is the same as `Task.RawParam.<ParamName>` for all parameter types except PATH. For PATH type the value is the input value with applicable path mapping rules applied to it.|Available within the Step Script Actions and Embedded Files.|
|`Task.RawParam.<ParamName>`|Values of task parameters are available within the `Task.Param` object.|Available within the Step Script Actions and Embedded Files.|
|`Task.File.<name>`|The filesystem location to which the Task Embedded File with key `<name>` has been written.| Available within the Step Script Actions and Attachments.|
|`Env.File.<name>`|The filesystem location to which the Environment Attachment with key `<name>` has been written.|Available within the Environment Script Actions and Embedded Files.|
|`Session.WorkingDirectory`|The agent is expected to create a local temporary scratch directory for the duration of a Session. This builtin provides the location of that temporary directory. This is the working directory that the Worker Agent uses when running the task.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|
|`Session.HasPathMappingRules`|This value can be used to determine whether path mapping rules are available to the Session. It is string valued, with values "true" or "false". "true" means that the path mapping JSON contains path mapping rules. "false" means that the contents of the path mapping JSON are the empty object.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|
|`Session.PathMappingRulesFile`|This is a string whose value is the location of a JSON file on the worker node's local disk that contains the path mapping rule substitutions for the Session.|This is available within all Environment Script Actions & Embedded Files, and all Step Script Actions and Embedded Files.|

## 8. Additional Information

* The Cc unicode character category is all [C0](https://www.unicode.org/charts/PDF/U0000.pdf)
  and [C1](https://www.unicode.org/charts/PDF/U0080.pdf) characters.
  * This is a category of 65 non-printable characters such as NUL, BEL, Backspace, DEL,
     tab, newline, carriage return, and form feed.

## 9. License

This work is licensed under CC BY-ND 4.0. To view a copy of this license, visit [http://creativecommons.org/licenses/by-nd/4.0/](http://creativecommons.org/licenses/by-nd/4.0/).

For more info see the [LICENSE file].

[LICENSE FILE]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/blob/mainline/LICENSE