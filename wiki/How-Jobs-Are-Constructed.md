# How Jobs Are Constructed

A **Job** in Open Job Description is a delineation of a workflow that is submitted to a render management system. 
The **Job** is, ultimately, a set of commands that are run on **Worker Hosts** subject to ordering, parallelism,
and other hardware and scheduling constraints. A **Job** in this specification is defined via a **Job Template**. The 
**Job Template** describes the shape of a **Job**, its runtime environment, and the processes that will run. The 
benefits of using a templated approach to creating jobs include:

1. **User-facing Parameters**
   * A single **Job Template** with user-facing parameters can be used to create multiple Jobs in a render management
     system that all perform the same actions on different inputs.
2. **Model complex workflows** 
   * The **Job Template** defines a set of **Steps** that each define a parameterized process to run; like an image 
     render, file conversion, or video file encoding.
   * Dependencies added between **Steps** can control the execution order. For example, adding dependencies can ensure 
     that all the frames of an image sequence have been rendered before the video file encoding **Step** is run. If
     dependencies are not added, **Steps** are free to run in parallel.
   * Each **Step** is stamped out to one or more **Tasks** through the **Step**'s parameterization. **Tasks** are the 
     exact unit of work that a render management system schedules to its **Worker Hosts**. For example, a stereoscopic 
     render **Step** can be parameterized on the frame number and the left/right camera choice. Each combination of a 
     frame number with a camera choice produces a single **Task**.
3. **Host Scheduling Requirements**
   * Which **Worker Hosts** **Tasks** can be scheduled to can be controlled by specifying **Worker Host** resources and 
     properties that each **Step** requires.
      * Quantifiable requirements such as amount of memory, and the number of CPU cores.
      * Attribute requirements such as the operating system, CPU architecture, or software.
4. **Runtime Environments**
    * Dynamically modify the Environment that **Tasks** run within on the **Worker Host**.
    * Run multiple **Tasks** from the same **Job** in a single Environment, front-loading expensive setup operations for
      **Steps** or **Tasks** run on the same **Worker Host**.

## Job Structure

Consider the following diagram of a **Job** that demonstrates the relationships between the components described above.
The lefthand side of the diagram shows a **Job Template**, and the right-hand side shows a **Job** that is created from 
that **Job Template**. 

![Job Structure](./images/job_structure.png)

A **Job** is created via a **Job Template** which is a [JSON](https://www.json.org/json-en.html) or [YAML](https://yaml.org/) 
document that outlines the shape of the **Job**; what the parameterization of the **Job** is, and what its **Steps** are. 
To create a **Job** you provide both a **Job Template** and a set of values for the **Job Parameters** defined in the 
**Job Template**. This example has a single integer valued **Job Parameter** named `End` that was given the value 400 
when the **Job** was created, but would otherwise have defaulted to the value of `1000` if not provided. The render 
management system then uses the provided **Job Parameter** values to instantiate the **Job** from the **Job Template**.

Each **Step** in a **Job** defines a specific action to perform, the parameter space of values over which the command 
will be run, and the constraints under which the **Step** may run. Constraints include required **Worker Host** 
properties and which, if any, **Step(s)** in the same **Job** must be completed before the **Step**'s **Tasks** can be 
run. All **Steps** have a unique name within the **Job** (`"HelloWorld"` in this example) that is used within the 
**Job Template** to refer to the Step. For example, a **Step** is referred to by name when declaring it as a dependency 
of another **Step**.

The parameterized action performed by a **Step** is called the **Step Script**. The **Step Script** consists of a 
command-line command to run, and a set of optional embedded files that can include the contents of a text file (shell 
script, python script, json document, etc.) within the definition of the **Step** rather than on a shared medium such 
as a filesystem. 

The **Task** is the unit of schedulable work run on **Worker Hosts** within the render management system. **Tasks** are
broken out from the **Step** according to their specific values for each of the **Task Parameters**, and each **Task**
then runs the action that is defined in the **Step** it belongs to. These specific parameter values are defined by the 
**Step**'s **Parameter Space**; the names, types, and values of each of the **Task Parameters**, in addition to how 
those **Task Parameters** are combined in to a multidimensional parameter space. In this example, we have a 
**Parameter Space** that consists of the values such as `{"Frame": 1, "Camera": "top"}`, `{"Frame": 1, "Camera": "left"}`,
`{"Frame": 1, "Camera": "right"}`, `{"Frame": 1, "Camera": "bottom"}`, `{"Frame": 11, "Camera": "top"}`, with `"Frame"` 
and `"Camera"` being the names of the two **Task Parameters**.

## Format Strings

**Format Strings** are templated strings that can reference values such as job parameter values, the location of the 
**Session** working directory, etc. These strings may contain one or more **String Interpolation Expressions** that are 
resolved before the string's value is used. A **String Interpolation Expression** within a **Format String** is denoted 
by a double-pair of open and closing curly braces as in: `"The location of the Session Working directory is {{ Session.WorkingDirectory }}"`. 
You can also see usages of **Format Strings** within the example in the previous section. 

The **String Interpolation Expression** must contain a single value reference (see [Value References](#value-references)), 
but a **Format String** may contain many **String Interpolation Expressions**. The **Format String** is resolved by 
replacing the open & closing curly braces and everything within them with the referenced value. For example, the range 
value, `"1-{{ Param.End}}:10"`, for the "Frame" **Task Parameter** in the previous section's example resolves to 
`"1-400:10"` when the **Job Template** is evaluated with `End=400`. 

The time when a **Format String** in a **Job Template** is evaluated is determined by what value from the **Job Template** 
is being defined. For example, the string `"1-{{Param.End}}:10"` in the previous section's example is evaluated by the 
render management system when the **Job Template** is submitted to create a **Job**, and the string 
`"{{ Task.File.Foo }}"` is evaluated on the **Worker Host** when running a **Task**. You can see when a **Format String** is 
evaluated in the [job template specification](2023-09:-Template-Schemas), but the general rule of thumb is that values 
that are used on the **Worker Host** to run a command are evaluated on the **Worker Host** and all others are evaluated 
in the render management system.

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