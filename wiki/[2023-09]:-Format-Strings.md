# Open Job Description: Format Strings [Version: 2023-09]

Concepts introduced: **Format String**, **String Interpolation Expression**

Format Strings are templated strings that can reference values such as job parameter values, the location of the Session working
directory, and so on. These strings may contain one or more ***String Interpolation Expressions*** that are resolved before
the string's value is used. A string interpolation expression within a format string is denoted by a double-pair of open and closing curly braces as in: `"The location of the Session Working directory is {{ Session.WorkingDirectory }}"`

The curly braces must contain a single value reference (see [Value References](#value-references)). The Format String
is resolved by replacing the open & closing curly braces and everything within them with the referenced value. For
example, if a Job Template has a Job Parameter named "Scene" and a Job is submitted with "myscene.blend" as the value for "Scene",
then the Format String "The file {{ Param.Scene }} can be rendered in Blender" is resolved to "The file myscene.blend can be rendered in Blender".

## Value References

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