# How Jobs Are Constructed

Concepts introduced: **Job**, **Step**, **Task**, **Job Template**, **Job Parameters**, **Parameter Space**,
**Format String**, and **String Interpolation Expression**

A ***Job*** in Open Job Description is the description of a workflow that is submitted to a render management system. 
The workflow is, ultimately, a set of commmand-line commands that are run on Worker Hosts subject to ordering, parallelism,
and other hardware and scheduling constraints. A Job in this specification is defined via a ***Job Template***. The Job Template
describes the shape of a Job, its runtime environment, and all of the processes that will run as part of it. Benefits of using a
templated approach to creating jobs include:

1. **User-facing Parameters**
   * You can author a single Job Template and use it to create many Jobs in a render management
     system that all perform the same actions, but on different input values.
2. **Model complex workflows** 
   * The Job Template defines a set of *Steps* that each define a particular parameterized process to
     run; like an image render, file conversion, or video file encoding.
   * By default, all Steps can run in parallel but you can add dependencies between Steps to ensure that, for example,
     all the images of a video clip are rendered before the step to encode the video is run.
   * Each *Step* is stamped out in to many *Tasks* through the Step's parameterization; Tasks are the unit of work
     that a render management system schedules to its Worker hosts. For example, a stereo render step will typically
     be parameterized on the frame number and the left/right camera choice; each combination of a frame number with
     a camera choice produces a Task.
3. **Host Scheduling Requirements**
   * Constrain which hosts Tasks can be scheduled to by specifying host resources and properties that each Step requires. Such as:
      * Quantifiable requirements such as amount of memory, and number of CPU cores.
      * Attribute requirements such as operating system, CPU architecture, or abstracted software configurations.
4. **Runtime Environments**
    * Dynamicaly modify the environment that Tasks run within on the Worker host.
    * Amortize expensive setup operations over multiple Tasks from the same Job that are run on the same host.

## Job Structure

The ***Job*** is what a work-submission creates within a render management system. It is defined as a nested hierarchy of
structures: it contains a directed acyclic graph of ***Steps*** with the edges of the graph defining dependencies - which Steps
must be completed before which -- and each Step defining a collection of parameterized ***Tasks***. The Job
itself can also be parameterized, so that you can define the shape of the Job once and then use that shape to
create multiple Jobs with different inputs.

Consider the following diagram that demonstrates the relationship between the components of a Job. The lefthand side of the
diagram shows a **Job Template**, and the righthand side shows a **Job** that is created from that Job Template. 

![Job Structure](./images/job_structure.png)

A Job is created via a ***Job Template*** which is a [JSON](https://www.json.org/json-en.html) or [YAML](https://yaml.org/) document
that describes the shape of the Job — what the parameterization of the Job is, and what its Steps are. The parameterization available
to a Job Template allows you to author a single Job Template that can be used to create many Jobs in a render management system that
all perform the same actions, but on different input values. To create a Job you provide both a Job Template and a set of values for
all of the **Job Parameters** defined in the Job Template; this example has a single integer valued Job Parameter named `End` that is
given the value 400 when creating a Job, but would default to the value 1000 if a value is not provided. The render management system
then uses the provided Job Parameter values to instantiate the Job Template to create a Job.

Each ***Step*** in a Job defines a specific parameterized action to perform — rendering the frames of a shot, encoding a
video, or something else -- that is run by all of its Tasks, the parameter
space of values over which that command will be run, and the contraints under which the Step may run. Constraints include
required host properties and which, if any, Step(s) in the same Job must be completed before the Step's Tasks can be run. All
Steps have a unique name within the Job ("HelloWorld" in this example) that is used within the Job Template to refer to the Step.
For instance, a Step is refered to by name when declaring it as a dependency of a Step.

The parameterized action performed by a Step is called its ***Step Script***. The Step Script consists of a command-line command
to run, and a set of optional embedded files that can include the contents of a text file (shell script, python script,
json document, etc) within the definition of the Step rather than on a shared medium such as a filesystem. 

The ***Task*** is the unit of schedule-able work run on worker hosts within the render management system. Each Task 
runs the parameterized action that is defined for its Step, but with a specific value for each of the ***Task Parameters***.
These specific parameter values are defined by the Step's ***Parameter Space***; the names, types, and values of each of the
Task Parameters, in addition to how those task parameters are combined in to a multidimensional parameter space. In this
example, we have a parameter space that consists of the values `{"Frame": 1, "Camera": "top"}`, `{"Frame": 1, "Camera": "left"}`,
`{"Frame": 1, "Camera": "right"}`, `{"Frame": 1, "Camera": "bottom"}`, `{"Frame": 11, "Camera": "top"}`, ... and so on, with 
"Frame" and "Camera" being the names of the two Task Parameters.

## Format Strings

Format Strings are templated strings that can reference values such as job parameter values, the location of the Session working
directory, and so on. These strings may contain one or more ***String Interpolation Expressions*** that are resolved before
the string's value is used. A string interpolation expression within a format string is denoted by a double-pair of open and closing
curly braces as in: `"The location of the Session Working directory is {{ Session.WorkingDirectory }}"`. You can also see examples
of format strings within in the example in the previous section. 

The string interpolation expression must contain a single value reference (see [Value References](#value-references)), but a
Format String may contain many string interpolation expressions. The Format String is resolved by replacing the open & closing
curly braces and everything within them with the referenced value. For example, the range value, "1-{{ Param.End}}:10", for the
"Frame" task parameter in the previous section's example resolves to "1-400:10" when the Job Template is evaluated with `End=400`. 

The time when a format string in a Job Template is evaluated is determined by what value from the job template is being defined.
For example, the string "1-{{Param.End}}:10" in the previous section's example is evaluated by the render management system when
the job template is submitted to create a job, and the string "{{ Task.File.Foo }}" is evaluted on the Worker Host when running a
Task. You can see when a format string is evaluated in the [job template specification](2023-09:-Template-Schemas), but the general
rule of thumb is that values that are used on the Worker Host to run a command are evaluated on the Worker Host and all others are
evaluated in the render management system.

### Value References

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