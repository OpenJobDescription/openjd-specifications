
* Feature Name: Model Extensions
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/66
* Start Date: 2024-12-09
* Accepted On: in draft

## Summary

This RFC proposes a method of enabling additional approved functionality that is not included in 
 a specific version of the model release through a new top level job template key `Extensions`.  
Each extension is similar to the `from __future__` import system in Python <sup>[python.org](https://docs.python.org/3/library/__future__.html)</sup> .

Because these extensions are optional, each scheduler can support any or all of these features. 
This allows for schedulers to add support and prepare for future openjd-specification releases gradually.
  
## Basic Examples

### Example Job Template

The following job template is built on the 2023-09 version of the specification but requests support for 
Task Chunking (from [RFC-0001](https://github.com/OpenJobDescription/openjd-specifications/pull/54)).  
  
The `extensions` key is a list of extensions that the job template author has determined are required. 

```yaml
specificationVersion: 'jobtemplate-2023-09'
# This key here is an instruction to the scheduler that we require `TASK_CHUNKING`
extensions:
- TASK_CHUNKING
name: Task Chunking Job
parameterDefinitions:
  - name: SceneFile
    type: PATH
    objectType: FILE
    dataFlow: IN
  - name: Frames
    type: STRING
    default: 1,100
  - name: ChunkSize
    type: INT
    default: 10
steps:
  - name: Render
    parameterSpace:
      taskParameterDefinitions:
        - name: FrameRange
          type: CHUNK[INT]
          range: "{{Param.Frames}}"
          chunks:
            defaultTaskCount: "{{Param.ChunkSize}}"
            targetRuntimeSeconds: 900
            rangeConstraint: CONTIGUOUS
    script:
      actions:
        onRun:
          command: bash
          args: ["{{Task.File.RenderChunk}}"]
      embeddedFiles:
        - name: RenderChunk
          filename: render.sh
          type: TEXT
          data: |
            START_FRAME="$(echo '{{Task.Param.FrameRange}}' | cut -d- -f1)"
            END_FRAME="$(echo '{{Task.Param.FrameRange}}' | cut -d- -f2)"
            render -scenefile '{{Param.SceneFile}}' \
                -start "$START_FRAME" \
                -end "$END_FRAME"
```


## Motivation
During a discussion on [RFC-0001](https://github.com/OpenJobDescription/openjd-specifications/pull/54), it was determined that a 
way was required to publish any new functionality that an RFC may provide.  


Initial discussions centered around the idea of incrementing the job template specification version each time an RFC was approved, 
however that rapid release schedule posed a few issues.  
When an OpenJD Specification release is approved, there is a level of continued support that is expected. If a OpenJD Specification is 
released every time an RFC is approved, there may be dozens of individual versions that all need to be fully supported by schedulers. 
If releases of OpenJD specifications are planned and scheduled, extensions can be treated as requesting an optional feature. 
That should allow less churn and code management for the OpenJD implementations.  
Another issue came up when the code implementation was considered. Currently there exists a single version of the OpenJD for Python 
implementation. As new OpenJD Specifications are released this implementation, both the model and the sessions libraries, will have 
to either branch supported releases or manage multiple versions of the codebase in a single repository.   
Anything that the OpenJD Specification team can do to lessen their management burden will be appreciated.  

The idea of treating these RFC functionality as [Python \_\_future__](https://docs.python.org/3/library/__future__.html) 
imports was determined to be the best way forward so that this newly approved functionality can be utilized on schedulers as 
they add support for it without requiring a full specification release to be approved and implemented.
  
### Supported Extensions
Valid values for the `extensions` key must still be approved and implemented through the standard RFC process in the 
openjd-specifications repository.  
These approved RFCs can define breaking functionality as an extension and have schedulers add support for them before a 
new formal specification release.  

These extensions should be treated as requests to the scheduler and job template authors should be aware that a 
specific scheduler may reject a job template submission if it does not support all of the required extensions.    

Each individual scheduler may want to enable extensions either as early access preview features or behind feature flags.
The scheduler may also want to roll out support for individual extensions after they have been fully testing and support has been verified.

### Merging Extensions
This proposal also defines the process for merging Extensions into the next version of the model release.

A new subsection of the RFC template is defined under `Specification` called `Extension Name`.  
If a specific RFC adds or breaks functionality in the base model, it should define an Extension Name that can be used 
to reference the functionality in openjd implementations.  
This name should match the regex: `[A-Z0-9_]{3,128}`.  

#### Updating Extensions
There may be scenarios where an extension that is destined for release in a future specification release needs 
additional modifications before merging in to the release.  
Reasons for this may include:
   - After widespread adoption the feature doesn't fulfill its design goals
 - A separate RFC implements the functionality in a more succinct way

   
You may name the extension with a numerical suffix, for example `TASK_CHUNKING_2` to indicate it supercedes an already approved extension.  
Schedulers can choose to continue support for the original extension, or only support the new implementation.  

These "superceding extensions" are expected to get merged into a future specification release instead of the initial one.  
  
If an extension is updating functionality that already exists in a version of the specification, the numerical suffixing is not required..  
> Extension names are only required to be unique within a specification version, however it is best practice to keep them globally unique to reduce confusion.  



### Anatomy Of An Extension
An extension consists of the following information:
- A valid `<ExtensionName>`
- An array of Literal `specificationVersion` strings that the extension states that it works with, ie [`jobtemplate-2023-09`, `jobtemplate-2025-03`]


### Releasing A Specification Version  
When a new version of the specification is released, all accepted extension names from the previous release are labeled as 
deprecated and may still be used but are treated as a NoOp.
Schedulers are encouraged to notify their users that they are using a deprecated extension which is enabled by default.  

Any extensions that were not accepted in the release are considered obsolete and schedulers should return an error if a 
job template is using an obsoleted extension 

Any deprecated extensions from the previous specification release are now also considered obsolete and should be 
treated the same as non-accepted extensions.  

A released specification will have the following:
- A list of extensions that were merged into the release (deprecated extensions).  
- A list of extensions that were marked as deprecated in the previous release (which are now obsolete and return an error if used).  
- A list of currently known extensions inherited from the previous release. This list will grow as new RFCs are approved.  



## Specification

> Changes to [the template schema](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas).

> A modification to [`Job Template - Root Elements`](../wiki/2023-09-Template-Schemas#11-Job-Template)
```diff
  specificationVersion: "jobtemplate-2023-09"
  $schema: <string> # @optional
+ extensions: [ <ExtensionName>, ... ] # @optional
  name: <JobName> # @fmtstring
  description: <Description> # @optional
  parameterDefinitions:  [ <JobParameterDefinition>, ... ] # @optional
  jobEnvironments: [ <Environment>, ... ] # @optional
  steps: [<StepTemplate>, ...]
```

> A new section `<ExtensionName>` after
> [section 1.1.1. `<JobName>`](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#111-jobname).

```diff
+ #### 1.1.2. `<ExtensionName>`
+ 
+ A literal string matching the following character regex: [A-Z_0-9]{3,128}.
```

## Design Choice Rationale

### Gradual Feature Support

By enabling functionality as feature flag style options, schedulers can adopt functionality that is aim for future 
specification releases and increase adoption and testing of these features before they get ratified in specification 
versions that need to have continued support.  


### Reduced Specification Release Overhead

By introducing a way to get functionality deployed and tested before ratifying it in a specification release, the hope is that there 
will be less need for immediate specification version releases.
When a new version is released, the newly merged in functionality is fully baked and has been tested by a wider audience.

## Prior Art

This RFC takes inspiration from the `__future__` import system in Python <sup>[python.org](https://docs.python.org/3/library/__future__.html)</sup> and the [`AWS::LanguageExtensions`](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/transform-aws-languageextensions.html) feature in Cloudformation.  

The [OpenGL_Extension](https://www.khronos.org/opengl/wiki/OpenGL_Extension) system is also a good piece of prior art to look at for inspiration.  
They implement define vendor extensions and a review board to help merge extensions into OpenGL core

## Rejected Ideas

### Release a new specification release for each RFC

Initial thoughts around releasing a new specification version for each RFC approved quickly became overwhelming.
This became obvious when determining the strategies we would use to manage codebases, supported versions etc.  

Some questions that came up during industry discussions were:
- When submitting to a scheduler, would a user expect every specification release to be supported? Only the latest number of versions?
Or is that up to the scheduler?
- For code based implementations of OpenJD, do they need to support multiple major version releases corresponding to each specification
release and would that conflict with the semVer versioning requirements by these implementations?
- What would happen if a user submitted a job template with an older specification version, is it expected that the scheduler will try
running it in a newer model or would a user expect it to fail on submission? 

Many of these questions become easier if OpenJD Specification release schedules are slowed down.  
In those cases the OpenJD specification team could recommend support for "the last X releases" which may end up supporting several years
of specification version as opposed to a potentially shorter window if release schedules become ad-hoc.  


## Further Discussion

Further discussion is needed on OpenJD Specification release schedules, processes for merging RFC extensions into newer releases of the specification, and actual implementation of RFC extensions.  
These discussions can be started in the pull-request comment section and the RFC will be updated accordingly.  

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
