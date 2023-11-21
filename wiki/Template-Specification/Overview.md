
# Open Job Description: Job Template Specification [Version: 2022-09]

A Job in this specification is defined via a *Job Template*. The Job Template describes the shape of a Job, its runtime
environment, and all of the processes that will run as part of it. Some of the key abilities that the Job Template grants to
authors are:

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

The Job Template is expressed as a UTF-8 document in either
[ECMA-404 JavaScript Object Notation (JSON)](https://www.json.org/json-en.html) or
[YAML Ain't Markup Language (YAML) 1.2](https://yaml.org/) interchange format.

For more information, see:

* [Job Structure](Job-Structure.md)
* Version 2023-09:
  * [How Jobs Are Run](2023-09/How-Jobs-Are-Run.md)
  * [Template Schemas](2023-09/Template-Schema.md)
