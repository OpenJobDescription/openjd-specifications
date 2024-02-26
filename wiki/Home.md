# Open Job Description Documentation

Open Job Description is a flexible open specification initially developed by the team behind AWS Thinkbox
Deadline for defining render jobs which are portable between studios and render solutions. Making render jobs portable 
across pipelines allows technical pipeline developers to more easily and flexibly test, adapt, and deploy the best
render farm solutions for their projects, eliminating the need for studios and developers to recreate every render
submission variant from scratch.

We created Open Job Description after hearing frequently from AWS Thinkbox Deadline customers that they found the 
choice of render farm management tools to be daunting due to the effort required to update or replace their tooling 
around the render farm. We also heard from software developers that they were unable to realistically release render
farm plugins for their own applications despite being the most qualified to do so, as the render farm landscape was 
fractured and releasing multiple plugins for different render farm solutions would quickly siphon all their
development capacity away from improving their software. A standard way of defining render jobs, or really any type 
of work suited for completion on a render farm, makes tools and plugins portable and increases interoperability. 

Open Job Description is under active development. We're releasing this because we'd like your feedback and 
participation as we move forward, together, in defining and implementing a specification that solves the problems in 
the space. We know that, as currently specified, Open Job Description is not a cure-all for any and all workflows. 

For deeper insight into our thought process and goals, we recommend [this Academy Software Foundation talk](https://www.youtube.com/watch?v=3AM3L6P-cAw&list=PL9dZxafYCWmxDFGc2CEq4SgCkZWKYW1m5&index=14)
by Pauline Koh, Senior Product Manager at Amazon Web Services, titled *Portable Jobs for Open Source Content Production*.
If you want to keep going, [this follow-up talk](https://www.youtube.com/watch?v=2umfqGX844Y), also by Pauline Koh, at 
the subsequent Academy Software Foundation gathering titled *Portable and Open Render Job Specifications* is a gentle 
introduction into what you can accomplish with OpenJD. If you've already watched the first talk, you can [start here](https://www.youtube.com/watch?v=2umfqGX844Y&t=383)
on the second talk.

## Getting Started

The fastest way to understand the bones of Open Job Description is to understand both [How Jobs Are Constructed](How-Jobs-Are-Constructed)
and [How Jobs Are Run](How-Jobs-Are-Run). You may also find it beneficial to look through the provided
[sample templates](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples) in this GitHub
repository.

## Contributing

We want your input! Please see our [Contributing Guidelines](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/CONTRIBUTING.md) for additional information.

* [Discussions](https://github.com/OpenJobDescription/openjd-specifications/discussions): We encourage you to post about what you
   would like to see in future revisions of the specification, share, and brag about how you are using Open Job Description, and
   engage with us and the community.
* [Request for Comment](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/rfcs/README.md): This 
  repository exists because we want your comments on the specification. Please consider submitting an RFC if you have 
  thoughts on how the specification could be improved.
* [Issues](https://github.com/OpenJobDescription/openjd-specifications/issues): We encourage you to use the GitHub issue tracker
  to report bugs. 
* [Pull Requests](https://github.com/OpenJobDescription/openjd-specifications/pulls): We welcome pull requests to improve this wiki
  documentation. Simply make your changes in our [GitHub Repository](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/wiki)
  and post a pull request.

## Open Job Description Projects

*If you have an Open Job Description project that you would like to advertise here then please
submit a pull request.*

### Tools

* [openjd-cli](https://github.com/OpenJobDescription/openjd-cli) - Provides a command-line
  interface for working with Open Job Description templates.

### Libraries

* [openjd-model](https://github.com/OpenJobDescription/openjd-model-for-python) - A Python
  implementation of the data model for Open Job Description's template schemas.
* [openjd-sessions](https://github.com/OpenJobDescription/openjd-sessions-for-python) - A Python
  library that can be used to build a runtime that is able to run Jobs in a Session as defined
  by Open Job Description.
